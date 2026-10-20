import unittest

from windprofiel.opsplitsing import Aannames, dispatch, economics, module_kg_h, simulate


class OpsplitsingTests(unittest.TestCase):
    def test_no_hydrogen_below_minimum_load(self):
        a = Aannames(minimumlast=0.2)
        self.assertEqual(module_kg_h(0.19, 11, a), 0)
        self.assertGreater(module_kg_h(0.2, 11, a), 0)

    def test_dispatch_strategies_respect_minimum_and_capacity(self):
        a = Aannames(minimumlast=0.2)
        self.assertEqual(dispatch(5, 4, 11, a, "samen", {}), [])          # 5 < 4 × 2,2 MW
        self.assertEqual(dispatch(13, 4, 11, a, "bijschakelen", {}), [1.0])  # rest 2 MW < 2,2 MW
        self.assertEqual(dispatch(14, 4, 11, a, "bijschakelen", {}), [1.0, 3 / 11])
        loads = dispatch(30, 4, 11, a, "verdelen", {})
        self.assertAlmostEqual(sum(loads) * 11, 30)
        self.assertTrue(all(0.2 <= x <= 1 for x in loads))
        self.assertEqual(dispatch(60, 4, 11, a, "verdelen", {}), [1.0] * 4)

    def test_splitting_captures_low_wind_that_one_module_misses(self):
        a = Aannames(minimumlast=0.4)
        supply = [10.0] * 60             # onder 40 % van 44 MW, boven 40 % van 11 MW
        self.assertEqual(simulate(supply, 1, a, "verdelen")["waterstof_t"], 0)
        self.assertGreater(simulate(supply, 4, a, "verdelen")["waterstof_t"], 0)

    def test_starts_are_counted_once_per_switch_on(self):
        a = Aannames()
        result = simulate([44.0] * 6 + [0.0] * 6 + [44.0] * 6, 1, a, "verdelen")
        self.assertAlmostEqual((result["starts_warm_per_module"] + result["starts_koud_per_module"])
                               * 18 * (1 / 6) / 8760, 2)

    def test_economics_break_even_and_scale(self):
        a = Aannames()
        result = simulate([30.0] * 600, 8, a, "verdelen")
        cost = economics(result, a)
        self.assertGreater(cost["capex_meur"], a.capex_eur_kw * 44 / 1000)  # kleinere modules duurder per kW
        self.assertGreater(cost["lcoh_eur_kg"], 0)


if __name__ == "__main__":
    unittest.main()
