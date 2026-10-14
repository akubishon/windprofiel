import copy
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from windprofiel.application import PARKS, build_profile, interpolate_minutes, parse_wind, park_power_mw, validate_curve
from windprofiel.knmi import KNMIError


def payload(values):
    return {"type": "CoverageCollection", "coverages": [{
        "eumetnet:locationId": "station",
        "domain": {"domainType": "PointSeries", "axes": {"t": {"values": [
            "2025-01-01T00:00:00Z", "2025-01-01T00:10:00Z", "2025-01-01T00:20:00Z"]}}},
        "ranges": {"ff": {"axisNames": ["t", "y", "x"], "shape": [3, 1, 1], "values": values}},
    }], "parameters": {"ff": {"unit": {"symbol": {"value": "m/s"}},
                                "measurementType": {"method": "mean", "duration": "-PT10M"}}}}


class ApplicationTests(unittest.TestCase):
    def test_fryslan_scenario_and_uploaded_curve_priority(self):
        self.assertEqual(park_power_mw(12, "fryslan", None), 382.7)
        self.assertIsNone(park_power_mw(None, "fryslan", None))
        curve = {"points": [(3, 0), (14, 4300)], "cut_out": 25}
        self.assertLess(park_power_mw(12, "fryslan", curve), 382.7)

    def test_combined_profile_reference_times_and_missing_wind(self):
        class Client:
            def locations(self):
                return {"features": [{"id": p["station"], "properties": {"name": k}} for k,p in PARKS.items()]}
            def observations(self, station, day):
                data = payload([8, None, 8] if station == PARKS["fryslan"]["station"] else [8, 8, 8])
                data["coverages"][0]["eumetnet:locationId"] = station
                return data
        with patch("windprofiel.application.load_curve", return_value=None):
            profile = build_profile(date(2025,1,1), client=Client())
        self.assertEqual(profile["parks"]["fryslan"]["curve"]["kind"], "cubic_scenario")
        self.assertIsNone(profile["parks"]["fryslan"]["energy_mwh"])
        self.assertIsNone(profile["combined_energy_mwh"])
        points = profile["parks"]["fryslan"]["reference_points"]
        self.assertEqual([p["timestamp"] for p in points], ["2025-01-01T00:55:00+01:00", "2025-01-01T01:05:00+01:00", "2025-01-01T01:15:00+01:00"])
        self.assertIsNone(points[1]["power_mw"])
        self.assertTrue(all(p["power_mw"] is None for p in profile["combined_reference_points"]))

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
