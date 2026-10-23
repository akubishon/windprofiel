import math
import unittest
from dataclasses import replace
from datetime import datetime, timezone

from windprofiel import application, ashoogte, opsplitsing, windbron
from windprofiel.application import PARKS, load_curve


JANUARY = datetime(2025, 1, 15, 12, tzinfo=timezone.utc)
JULY = datetime(2025, 7, 15, 12, tzinfo=timezone.utc)


class HeightTranslationTests(unittest.TestCase):
    def test_factor_per_month_from_the_table(self):
        table = windbron.table()["parken"]
        for park_id, pm in windbron.METHODS["onafhankelijk"].items():
            self.assertEqual(len(table[park_id]["factor"]), 12)
            self.assertAlmostEqual(windbron.factor(park_id, pm, JANUARY), table[park_id]["factor"][0])
            self.assertAlmostEqual(windbron.factor(park_id, pm, JULY), table[park_id]["factor"][6])
            self.assertAlmostEqual(windbron.hub_wind(park_id, pm, 6.0, JULY), 6.0 * table[park_id]["factor"][6])
            self.assertIsNone(windbron.hub_wind(park_id, pm, None, JULY))

    def test_month_follows_dutch_calendar(self):
        # 31 december 23:30 UTC is 1 januari in Nederland.
        pm = windbron.METHODS["onafhankelijk"]["fryslan"]
        late = datetime(2024, 12, 31, 23, 30, tzinfo=timezone.utc)
        self.assertAlmostEqual(windbron.factor("fryslan", pm, late), windbron.table()["parken"]["fryslan"]["factor"][0])

    def test_equivalent_alpha_round_trip_and_custom_alpha(self):
        pm = windbron.METHODS["onafhankelijk"]["fryslan"]
        value = windbron.factor("fryslan", pm, JANUARY)
        alpha = windbron.alpha_equivalent("fryslan", value)
        self.assertAlmostEqual((115 / 10) ** alpha, value)
        self.assertAlmostEqual(windbron.factor("fryslan", pm, JANUARY, alpha=0.25), 11.5 ** 0.25)

    def test_old_seasonal_alpha_is_kept_for_comparison(self):
        old = windbron.METHODS["productie_houtribdijk"]
        self.assertAlmostEqual(windbron.factor("fryslan", old["fryslan"], datetime(2025, 1, 1, 12, tzinfo=timezone.utc)), 11.5 ** 0.18)
        self.assertAlmostEqual(windbron.seasonal_alpha(old["fryslan"], datetime(2025, 7, 2, 12, tzinfo=timezone.utc)), 0.05, places=3)
        self.assertAlmostEqual(windbron.factor("beabuorren", old["beabuorren"], JULY), 6.0 ** 0.20)

    def test_interpolation_between_wins50_levels(self):
        row = {"fryslan_100": 10.0, "fryslan_120": 11.0, "fryslan_60": 9.0, "fryslan_10": 6.0}
        self.assertEqual(ashoogte.level_wind(row, "fryslan", 100), 10.0)
        value = ashoogte.level_wind(row, "fryslan", 115)
        self.assertTrue(10.0 < value < 11.0)
        exponent = math.log(1.1) / math.log(1.2)
        self.assertAlmostEqual(value, 10.0 * 1.15 ** exponent)
        self.assertIsNone(ashoogte.level_wind({**row, "fryslan_120": None}, "fryslan", 115))

    def test_ratio_of_means_per_month(self):
        t1 = datetime(2020, 1, 10, tzinfo=timezone.utc)
        t2 = datetime(2020, 2, 10, tzinfo=timezone.utc)
        data = [(t1, 5.0, 7.5), (t1, 10.0, 12.0), (t2, 4.0, 4.0)]
        self.assertEqual(ashoogte.ratios(data, ashoogte.month_key), {1: 19.5 / 15.0, 2: 1.0})

    def test_table_values_are_plausible_and_documented(self):
        data = windbron.table()
        self.assertIn("WINS50", data["bron"])
        for entry in data["parken"].values():
            self.assertTrue(all(0.8 < f < 2.0 for f in entry["factor"]))
            self.assertTrue(all(0.8 < f < 2.0 for f in entry["schering"]))
            self.assertEqual(entry["regel"], "gemiddelde")
            self.assertTrue(any(item["naam"] == entry["bron"] for item in entry["bronvergelijking"]))


class SourceTests(unittest.TestCase):
    def test_average_needs_both_stations_and_fills_nothing(self):
        pm = windbron.METHODS["onafhankelijk"]["fryslan"]
        self.assertEqual(windbron.select(pm, {"houtribdijk": 6.0, "stavoren": 4.0}), (5.0, "gemiddelde"))
        self.assertEqual(windbron.select(pm, {"houtribdijk": 6.0, "stavoren": None}), (None, None))
        self.assertEqual(windbron.select(pm, {"stavoren": 4.0}), (None, None))

    def test_old_highest_rule_takes_the_other_station_when_one_is_missing(self):
        pm = windbron.METHODS["productie_hoogste"]["fryslan"]
        self.assertEqual(windbron.select(pm, {"houtribdijk": 6.0, "stavoren": 4.0}), (6.0, "houtribdijk"))
        self.assertEqual(windbron.select(pm, {"houtribdijk": None, "stavoren": 4.0}), (4.0, "stavoren"))

    def test_both_routes_and_both_parks_use_the_same_source(self):
        new = windbron.METHODS[windbron.DEFAULT]
        self.assertEqual(new["fryslan"].stations, new["beabuorren"].stations)
        self.assertEqual(new["fryslan"].rule, new["beabuorren"].rule)
        table = windbron.table()["parken"]
        for park_id, pm in new.items():
            self.assertEqual(sorted(windbron.station_id(k) for k in pm.stations), sorted(table[park_id]["stations"]))
            self.assertEqual(PARKS[park_id]["station"], windbron.station_id(pm.stations[0]))
            self.assertEqual(table[park_id]["bron"], ashoogte.CHOICE[park_id])
        self.assertIs(opsplitsing.STATIONS, windbron.STATIONS)

    def test_supply_and_day_profile_give_the_same_power(self):
        for method in windbron.METHODS:
            for park_id, pm in windbron.METHODS[method].items():
                curve = load_curve(park_id)
                hub = 7.0 * windbron.factor(park_id, pm, JULY)
                self.assertEqual(opsplitsing.park_mw(park_id, 7.0, JULY, curve, pm),
                                 application.park_power_mw(hub, park_id, curve, wake=True))

    def test_user_station_gets_its_own_factor_or_only_the_shear(self):
        pm = windbron.with_station(windbron.METHODS["onafhankelijk"]["fryslan"], "0-20000-0-06242")   # Vlieland
        factors, origin = windbron.month_factors("fryslan", pm)
        vlieland = next(i for i in windbron.table()["parken"]["fryslan"]["bronvergelijking"] if i["naam"] == "Vlieland")
        self.assertEqual(factors, vlieland["factor"])
        unknown = windbron.with_station(windbron.METHODS["onafhankelijk"]["fryslan"], "0-20000-0-06380")
        self.assertEqual(windbron.month_factors("fryslan", unknown)[0], windbron.table()["parken"]["fryslan"]["schering"])
        self.assertIn("niet gecorrigeerd", windbron.month_factors("fryslan", unknown)[1])

    def test_unknown_method_is_refused(self):
        with self.assertRaises(ValueError):
            windbron.method("productie")

    def test_overridden_factors_are_used_for_sensitivity(self):
        pm = replace(windbron.METHODS["onafhankelijk"]["fryslan"], factors=tuple([1.5] * 12))
        self.assertEqual(windbron.factor("fryslan", pm, JULY), 1.5)


if __name__ == "__main__":
    unittest.main()
