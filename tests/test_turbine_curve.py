import json
import unittest
from pathlib import Path
from windprofiel.application import load_curve, park_power_mw
from windprofiel.profile import power_kw

ROOT = Path(__file__).resolve().parent.parent

class DefaultCurveTests(unittest.TestCase):
    def test_default_and_browser_use_identical_source_data(self):
        data = json.loads((ROOT / 'windprofiel/data/fryslan.json').read_text())
        self.assertEqual(data, json.loads((ROOT / 'src/opsplitsing/python/data/fryslan.json').read_text()))
        self.assertEqual(data, json.loads((ROOT / 'docs/curves/fryslan-swt-dd-130-4.3-107db.json').read_text()))
        curve = load_curve('fryslan')
        self.assertEqual(curve['cut_out'], 28.01)
        self.assertIn('technische bereikgrens', curve['status'])
        for speed, kw in [(0, 0), (3, 20), (8, 1920), (11.5, 4070), (14, 4300),
                          (23.5, 3955), (25, 2930), (28, 860), (28.01, 0)]:
            self.assertAlmostEqual(power_kw(speed, curve['points'], cut_out=curve['cut_out']), kw)
            self.assertAlmostEqual(park_power_mw(speed, 'fryslan', curve), kw * 89 / 1000)
        self.assertEqual(park_power_mw(28.01, 'fryslan', curve, wake=True), 0)
        self.assertIsNone(park_power_mw(None, 'fryslan', curve))
