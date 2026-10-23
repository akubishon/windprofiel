import unittest
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from windprofiel import windbron
from windprofiel.application import day_intervals
from windprofiel.vergelijking import common_days, fryslan_power, summarise, variant_days

LOCAL = ZoneInfo("Europe/Amsterdam")
NEW = windbron.METHODS["onafhankelijk"]["fryslan"]


def stations_for(day: date, speed: float = 8.0, missing: int | None = None) -> dict:
    slots = day_intervals(day)
    values = {t: speed for i, t in enumerate(slots) if i != missing}
    return {day.year: {"houtribdijk": dict(values), "stavoren": dict(values)}}


class TimeAggregationTests(unittest.TestCase):
    def test_intervals_per_dutch_calendar_day(self):
        self.assertEqual(len(day_intervals(date(2025, 1, 15))), 144)
        self.assertEqual(len(day_intervals(date(2025, 3, 30))), 138)
        self.assertEqual(len(day_intervals(date(2025, 10, 26))), 150)
        first, last = day_intervals(date(2025, 1, 15))[0], day_intervals(date(2025, 1, 15))[-1]
        # Intervalmiddens: 00:05 en 23:55 Nederlandse tijd.
        self.assertEqual(first.astimezone(LOCAL).strftime("%d %H:%M"), "15 00:05")
        self.assertEqual(last.astimezone(LOCAL).strftime("%d %H:%M"), "15 23:55")

    def test_day_energy_is_the_sum_of_ten_minute_intervals(self):
        for day in (date(2025, 1, 15), date(2025, 3, 30), date(2025, 10, 26)):
            result = variant_days(stations_for(day), NEW, 0.05, 11.5, None, (day, day))[day]
            hub = 8.0 * windbron.factor("fryslan", NEW, datetime.combine(day, datetime.min.time(), LOCAL))
            expected = fryslan_power(hub, 0.05, 11.5, None) * len(day_intervals(day)) / 6
            self.assertAlmostEqual(result["model_mwh"], expected)
            self.assertEqual(result["intervallen"], result["met_wind"])

    def test_one_missing_interval_makes_the_day_incomplete(self):
        day = date(2025, 1, 15)
        result = variant_days(stations_for(day, missing=70), NEW, 0.05, 11.5, None, (day, day))[day]
        self.assertIsNone(result["model_mwh"])
        self.assertEqual(result["met_wind"], 143)
        self.assertIsNotNone(result["wind_ashoogte_ms"])   # wind blijft zichtbaar, de energie niet

    def test_one_missing_station_is_not_filled_in(self):
        day = date(2025, 1, 15)
        data = stations_for(day)
        del data[2025]["stavoren"][day_intervals(day)[3]]
        self.assertIsNone(variant_days(data, NEW, 0.05, 11.5, None, (day, day))[day]["model_mwh"])
        old = windbron.METHODS["productie_hoogste"]["fryslan"]
        self.assertIsNotNone(variant_days(data, old, 0.05, 11.5, None, (day, day))[day]["model_mwh"])

    def test_common_days_and_days_where_the_model_is_lower(self):
        d1, d2, d3 = date(2024, 5, 1), date(2024, 5, 2), date(2024, 5, 3)
        results = {"nieuw": {d1: {"model_mwh": 100.0}, d2: {"model_mwh": 300.0}, d3: {"model_mwh": 50.0}},
                   "oud": {d1: {"model_mwh": 120.0}, d2: {"model_mwh": None}, d3: {"model_mwh": 60.0}}}
        measured = {d1: 150.0, d2: 200.0, d3: 40.0}
        selection = common_days(results, measured)
        self.assertEqual(selection, [d1, d3])
        summary = summarise(results["nieuw"], measured, selection)
        self.assertEqual(summary["dagen"], 2)
        self.assertEqual((summary["dagen_model_lager"], summary["dagen_model_hoger"]), (1, 1))
        self.assertAlmostEqual(summary["gemeten_gwh"], 0.19)
        self.assertAlmostEqual(summary["gemiddeld_verschil_mwh"], (-50 + 10) / 2)


if __name__ == "__main__":
    unittest.main()
