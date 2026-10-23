import copy
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from windprofiel import windbron
from windprofiel.application import (PARKS, build_profile, csv_rows, day_energy, day_intervals, nl_number, nl_time, parse_alpha,
                                     interpolate_minutes, parse_wind, park_power_mw, validate_curve)
from windprofiel.knmi import KNMIError


def payload(values):
    return {"type": "CoverageCollection", "coverages": [{
        "eumetnet:locationId": "station",
        "domain": {"domainType": "PointSeries", "axes": {"t": {"values": [
            "2025-01-01T00:00:00Z", "2025-01-01T00:10:00Z", "2025-01-01T00:20:00Z"]}}},
        "ranges": {"ff": {"axisNames": ["t", "y", "x"], "shape": [3, 1, 1], "values": values}},
    }], "parameters": {"ff": {"unit": {"symbol": {"value": "m/s"}},
                                "measurementType": {"method": "mean", "duration": "-PT10M"}}}}


STATION_IDS = [sid for _, sid in windbron.STATIONS.values()]


class Client:
    """Nagebootste KNMI-client: drie tienminutenwaarden per station, rond middernacht."""
    def __init__(self, values):
        self.values = values

    def locations(self):
        return {"features": [{"id": sid, "properties": {"name": sid}} for sid in STATION_IDS]}

    def observations(self, station, day):
        data = payload(self.values.get(station, [5, 5, 5]))
        data["coverages"][0]["eumetnet:locationId"] = station
        return data


class ApplicationTests(unittest.TestCase):
    def test_fryslan_scenario_and_uploaded_curve_priority(self):
        self.assertEqual(park_power_mw(12, "fryslan", None), 382.7)
        self.assertIsNone(park_power_mw(None, "fryslan", None))
        curve = {"points": [(3, 0), (14, 4300)], "cut_out": 25}
        self.assertLess(park_power_mw(12, "fryslan", curve), 382.7)

    def test_wake_reduces_partial_load_but_not_cut_in_cut_out_or_plateau(self):
        free = park_power_mw(8, "fryslan", None)
        self.assertAlmostEqual(park_power_mw(8, "fryslan", None, wake=True),
                               park_power_mw(8 * 0.95, "fryslan", None))
        self.assertLess(park_power_mw(8, "fryslan", None, wake=True), free)
        self.assertEqual(park_power_mw(14, "fryslan", None, wake=True), 382.7)
        self.assertEqual(park_power_mw(25.5, "fryslan", None, wake=True), 0)
        self.assertEqual(park_power_mw(2.9, "fryslan", None, wake=True), 0)
        self.assertEqual(park_power_mw(3.05, "fryslan", None, wake=True), 0)
        self.assertIsNone(park_power_mw(None, "fryslan", None, wake=True))
        curve = {"points": [(3, 0), (14, 1300)], "cut_out": 25}
        self.assertAlmostEqual(park_power_mw(10, "beabuorren", curve, wake=True),
                               park_power_mw(9.8, "beabuorren", curve))
        self.assertEqual(park_power_mw(24.9, "beabuorren", curve, wake=True), 10.4)

    def test_combined_profile_reference_times_and_missing_wind(self):
        # Eén station mist een meting: het gemiddelde ontbreekt dan, er wordt niets ingevuld.
        client = Client({windbron.station_id("houtribdijk"): [8, None, 8], windbron.station_id("stavoren"): [8, 8, 8]})
        with patch("windprofiel.application.load_curve", return_value=None):
            profile = build_profile(date(2025,1,1), client=client)
        self.assertEqual(profile["parks"]["fryslan"]["curve"]["kind"], "cubic_scenario")
        self.assertIsNone(profile["parks"]["fryslan"]["energy_mwh"])
        self.assertIsNone(profile["combined_energy_mwh"])
        points = profile["parks"]["fryslan"]["reference_points"]
        self.assertEqual([p["timestamp"] for p in points], ["2025-01-01T00:55:00+01:00", "2025-01-01T01:05:00+01:00", "2025-01-01T01:15:00+01:00"])
        self.assertIsNone(points[1]["power_mw"])
        self.assertTrue(all(p["power_mw"] is None for p in profile["combined_reference_points"]))

    def test_profile_wake_switch(self):
        with patch("windprofiel.application.load_curve", return_value=None):
            on = build_profile(date(2025,1,1), client=Client({}))
            off = build_profile(date(2025,1,1), client=Client({}), wake=False)
        self.assertTrue(on["wake"]); self.assertFalse(off["wake"])
        index = on["parks"]["fryslan"]["wind_ms"].index(5)
        self.assertLess(on["parks"]["fryslan"]["power_mw"][index], off["parks"]["fryslan"]["power_mw"][index])
        self.assertIn("Zogverlies uitgeschakeld", off["method"])

    def test_custom_alpha(self):
        with patch("windprofiel.application.load_curve", return_value=None):
            standard = build_profile(date(2025,1,1), client=Client({}))
            custom = build_profile(date(2025,1,1), client=Client({}), alphas={"fryslan": 0.3, "beabuorren": None})
        f, s = custom["parks"]["fryslan"], standard["parks"]["fryslan"]
        self.assertEqual((f["alpha"], f["alpha_custom"]), (0.3, True))
        january = windbron.table()["parken"]["fryslan"]["factor"][0]
        self.assertAlmostEqual(f["factor_default"], january)
        self.assertAlmostEqual(f["alpha_default"], windbron.alpha_equivalent("fryslan", january))
        index = f["wind_ms"].index(5)
        self.assertAlmostEqual(f["hub_wind_ms"][index], 5 * 11.5 ** 0.3)
        self.assertAlmostEqual(s["hub_wind_ms"][index], 5 * january)
        self.assertGreater(f["power_mw"][index], s["power_mw"][index])
        self.assertFalse(custom["parks"]["beabuorren"]["alpha_custom"])
        self.assertAlmostEqual(custom["parks"]["beabuorren"]["factor"], windbron.table()["parken"]["beabuorren"]["factor"][0])
        self.assertIn("Eigen hoogte-exponent voor Windpark Fryslân", custom["method"])

    def test_explicit_station_means_only_that_station(self):
        houtribdijk = windbron.station_id("houtribdijk")
        with patch("windprofiel.application.load_curve", return_value=None):
            default = build_profile(date(2025,1,1), client=Client({}))
            single = build_profile(date(2025,1,1), client=Client({}), stations={"fryslan": houtribdijk, "beabuorren": None})
        self.assertEqual(len(default["parks"]["fryslan"]["stations"]), 2)
        self.assertEqual(default["parks"]["fryslan"]["station_rule"], "gemiddelde")
        f = single["parks"]["fryslan"]
        self.assertEqual(([s["id"] for s in f["stations"]], f["station_rule"]), ([houtribdijk], "een"))
        own = next(i for i in windbron.table()["parken"]["fryslan"]["bronvergelijking"] if i["naam"] == "Houtribdijk")
        self.assertAlmostEqual(f["factor"], own["factor"][0])
        self.assertEqual(single["parks"]["beabuorren"]["station_rule"], "gemiddelde")

    def test_old_methods_stay_reproducible(self):
        with patch("windprofiel.application.load_curve", return_value=None):
            old = build_profile(date(2025,1,1), client=Client({}), method="productie_houtribdijk")
        f = old["parks"]["fryslan"]
        self.assertAlmostEqual(f["alpha"], 0.18)           # 0,115 + 0,065 · cos(0)
        self.assertEqual([s["id"] for s in f["stations"]], [windbron.station_id("houtribdijk")])
        self.assertAlmostEqual(old["parks"]["beabuorren"]["alpha"], 0.20)

    def test_profile_separates_wind_model_measured_and_hydrogen_share(self):
        with patch("windprofiel.application.load_curve", return_value=None):
            profile = build_profile(date(2025,1,1), client=Client({}))
        self.assertIn("hub_wind_ms", profile["parks"]["fryslan"])
        self.assertEqual(profile["measured"]["energy_mwh"], 6803.0)   # gemeten dagtotaal 1 januari 2025
        self.assertEqual(profile["measured"]["park"], "fryslan")
        # Drie tienminutenwaarden rond middernacht: geen volledige dag, dus geen modeldagtotaal en geen verschil.
        self.assertIsNone(profile["parks"]["fryslan"]["energy_mwh"])
        self.assertIsNone(profile["measured"]["model_minus_measured_mwh"])
        self.assertEqual(profile["hydrogen"]["share"], {"fryslan": 0.10, "beabuorren": 1.0})
        self.assertIsNone(profile["hydrogen"]["total_mwh"])

    def test_parse_alpha(self):
        self.assertIsNone(parse_alpha(None))
        self.assertIsNone(parse_alpha("  "))
        self.assertEqual(parse_alpha("0,25"), 0.25)
        self.assertEqual(parse_alpha("0.1"), 0.1)
        for bad in ("-0,1", "0,7", "abc", "nan"):
            with self.assertRaises(ValueError):
                parse_alpha(bad)

    def test_interval_midpoint_and_wind_interpolation(self):
        observations = parse_wind(payload([2, 4, 8]), "station")
        minute = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(observations[0][0], minute-timedelta(minutes=5))
        self.assertEqual(interpolate_minutes(observations, [minute, minute+timedelta(minutes=10)]), [3, 6])

    def test_missing_values_and_gaps_not_filled(self):
        observations = parse_wind(payload([2, None, 8]), "station")
        minute = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(interpolate_minutes(observations, [minute, minute+timedelta(minutes=10)]), [None, None])
        self.assertEqual(interpolate_minutes([observations[0], observations[2]], [minute]), [None])
        self.assertEqual(interpolate_minutes(observations, [minute-timedelta(hours=1)]), [None])

    def test_units_station_and_shape_rejected(self):
        original = payload([2, 4, 8])
        with self.assertRaises(KNMIError): parse_wind(original, "different-station")
        bad = copy.deepcopy(original);bad["parameters"]["ff"]["unit"]["symbol"]["value"]="knots"
        with self.assertRaises(KNMIError): parse_wind(bad, "station")
        bad = copy.deepcopy(original);bad["coverages"][0]["ranges"]["ff"]["shape"]=[3, 2, 1]
        with self.assertRaises(KNMIError): parse_wind(bad, "station")

    def test_invalid_wind_is_missing(self):
        values = parse_wind(payload([-1, float("nan"), 3]), "station")
        self.assertEqual([value for _, value in values], [None, None, 3])

    def test_wrong_curve_model_or_units_rejected(self):
        # Alleen een synthetische testcurve voor validatie, geen productiedata.
        curve = {"model": "Siemens SWT-1.3-62", "source": "https://example.org/curve",
                 "cut_out": 25, "points": [[3, 0], [14, 1300]]}
        self.assertEqual(validate_curve(curve, "beabuorren")["cut_out"], 25)
        with self.assertRaises(ValueError): validate_curve(curve, "fryslan")
        curve["points"][-1][1] = 1_300_000
        with self.assertRaises(ValueError): validate_curve(curve, "beabuorren")
        with self.assertRaises(ValueError): validate_curve([], "beabuorren")


class DayEnergyTests(unittest.TestCase):
    def test_running_day_counts_until_last_measurement(self):
        stamps = ["00:00", "00:01", "00:02", "00:03"]
        self.assertEqual(day_energy([60, 120, 60, 60], stamps, False), (5, None))
        self.assertEqual(day_energy([6, 12, 6, 6], stamps, False, per_hour=6), (5, None))   # tienminutenwaarden
        self.assertEqual(day_energy([60, 120, None, None], stamps, True), (3, "00:01"))
        self.assertEqual(day_energy([60, 120, None, None], stamps, False), (None, None))
        self.assertEqual(day_energy([60, None, 60, None], stamps, True), (None, None))
        self.assertEqual(day_energy([None] * 4, stamps, True), (None, None))


class DutchCsvTests(unittest.TestCase):
    def test_dates_and_decimal_comma(self):
        self.assertEqual(nl_time("2026-10-11T13:05:00+02:00"), "11-10-2026 13:05")
        self.assertEqual(nl_time("2025-10-26T02:30:00+02:00", True), "26-10-2025 02:30 zomertijd")
        self.assertEqual(nl_time("2025-10-26T02:30:00+01:00", True), "26-10-2025 02:30 wintertijd")
        self.assertEqual([nl_number(v) for v in (None, 0, 3.2000000000000006, 382.7, 1e-9)], ["", "0", "3,2", "382,7", "0"])

    def test_csv_rows(self):
        park = lambda v: {"wind_ms": [v], "hub_wind_ms": [v], "power_mw": [None]}
        profile = {"minutes": 1440, "timestamps": ["2026-01-08T00:00:00+01:00"], "combined_mw": [None],
                   "parks": {"fryslan": park(5.5), "beabuorren": park(4.0)}}
        rows = csv_rows(profile)
        self.assertEqual(rows[1], ["08-01-2026 00:00", "5,5", "4", "5,5", "4", "", "", ""])
        self.assertIn("fryslan_model_mogelijk_MW", rows[0])
        self.assertIn("fryslan_wind_ashoogte_ms", rows[0])
