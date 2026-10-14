import unittest
from datetime import date
from zoneinfo import ZoneInfo

from windprofiel.profile import combined_mw, day_minutes, power_kw


class ProfileTests(unittest.TestCase):
    def test_normal_day_and_local_boundary(self):
        minutes = day_minutes(date(2025, 1, 15))
        self.assertEqual(len(minutes), 1440)
        self.assertEqual(minutes[0].astimezone(ZoneInfo("Europe/Amsterdam")).hour, 0)
        self.assertEqual(minutes[-1].astimezone(ZoneInfo("Europe/Amsterdam")).hour, 23)

    def test_clock_changes(self):
        self.assertEqual(len(day_minutes(date(2025, 3, 30))), 1380)
        self.assertEqual(len(day_minutes(date(2025, 10, 26))), 1500)

    def test_other_year_rejected(self):
        with self.assertRaises(ValueError):
            day_minutes(date(2024, 1, 1))

    def test_curve_boundaries_and_interpolation(self):
        # Synthetische testcurve, geen curve van een van de windparken.
        curve = [(3.0, 0.0), (5.0, 100.0), (10.0, 500.0)]
        self.assertEqual(power_kw(2, curve, cut_out=25), 0)
        self.assertEqual(power_kw(4, curve, cut_out=25), 50)
        self.assertEqual(power_kw(24, curve, cut_out=25), 500)
        self.assertEqual(power_kw(25, curve, cut_out=25), 0)
        with self.assertRaises(ValueError):
            power_kw(float("nan"), curve, cut_out=25)

    def test_missing_park_is_not_zero(self):
        self.assertEqual(combined_mw([1, None, 2], [3, 4, None]), [4, None, None])
        with self.assertRaises(ValueError):
            combined_mw([1], [])


if __name__ == "__main__":
    unittest.main()
