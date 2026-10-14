import unittest
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from windprofiel.profile import combined_mw, cubic_power_kw, day_minutes, power_kw, today


class ProfileTests(unittest.TestCase):
    def test_normal_day_and_local_boundary(self):
        minutes = day_minutes(date(2025, 1, 15))
        self.assertEqual(len(minutes), 1440)
        self.assertEqual(minutes[0].astimezone(ZoneInfo("Europe/Amsterdam")).hour, 0)
        self.assertEqual(minutes[-1].astimezone(ZoneInfo("Europe/Amsterdam")).hour, 23)

    def test_clock_changes(self):
        self.assertEqual(len(day_minutes(date(2025, 3, 30))), 1380)
        self.assertEqual(len(day_minutes(date(2025, 10, 26))), 1500)

    def test_range_from_2025_until_today(self):
        with self.assertRaises(ValueError):
            day_minutes(date(2024, 12, 31))
        with self.assertRaises(ValueError):
            day_minutes(today() + timedelta(days=1))
        self.assertIn(len(day_minutes(today())), (1380, 1440, 1500))
        self.assertEqual(len(day_minutes(date(2026, 3, 29))), 1380)

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

    def test_cubic_scenario_boundaries(self):
        self.assertEqual(cubic_power_kw(2.999), 0)
        self.assertEqual(cubic_power_kw(3), 0)
        self.assertEqual(cubic_power_kw(11.5), 4300)
        self.assertEqual(cubic_power_kw(25), 4300)
        self.assertEqual(cubic_power_kw(25.001), 0)
        self.assertAlmostEqual(cubic_power_kw(8), 4300 * 485 / 1493.875)

    def test_cubic_ramp_is_monotonic_bounded_and_continuous(self):
        speeds = [3 + i / 100 for i in range(851)]
        powers = [cubic_power_kw(v) for v in speeds]
        self.assertTrue(all(0 <= p <= 4300 for p in powers))
        self.assertTrue(all(a <= b for a, b in zip(powers, powers[1:])))
        self.assertAlmostEqual(cubic_power_kw(11.5 - 1e-8), 4300, places=4)
        for invalid in [-1, float("nan"), float("inf")]:
            with self.assertRaises(ValueError): cubic_power_kw(invalid)


if __name__ == "__main__":
    unittest.main()
