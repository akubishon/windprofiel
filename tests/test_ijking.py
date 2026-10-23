import unittest
from datetime import date

from windprofiel import windbron
from windprofiel.ijking import CURRENT, METHOD, load_production, model


class IjkingTests(unittest.TestCase):
    def test_stored_production_covers_2022_to_2025_daily_in_gwh(self):
        production = load_production()
        self.assertEqual(len(production), 1461)
        self.assertEqual(min(production), date(2022, 1, 1))
        self.assertEqual(max(production), date(2025, 12, 31))
        self.assertAlmostEqual(production[date(2022, 1, 1)], 7.608)
        self.assertTrue(all(0 <= v <= 382.7 * 24 / 1000 for v in production.values()))   # nooit boven vollast

    def test_old_calibration_reproduces_the_old_opsplitsing_method(self):
        # De oude ijking blijft herhaalbaar; de standaardmethode gebruikt haar uitkomst niet.
        old = windbron.METHODS[METHOD]["fryslan"]
        self.assertEqual(CURRENT, (0.115, 0.065))
        self.assertEqual((old.alpha, old.alpha_seasonal, old.rule), (0.115, 0.065, "hoogste"))
        self.assertNotEqual(windbron.METHODS[windbron.DEFAULT]["fryslan"].height, "alpha")

    def test_model_interpolates_between_alpha_steps(self):
        row = (date(2024, 1, 1), 1.0, 0.0, [float(i) for i in range(91)])
        self.assertAlmostEqual(model(row, 0.0125, 0.0), 2.5)


if __name__ == "__main__":
    unittest.main()
