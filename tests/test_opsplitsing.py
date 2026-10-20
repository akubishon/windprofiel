import unittest
from dataclasses import replace
from datetime import datetime, timezone

from windprofiel.application import load_curve

from windprofiel.opsplitsing import (AANNAMES_META, TECHNOLOGIES, Aannames, break_even, combine_wind, desired_count, draw_mw, economics,
                                     park_mw, parse_aannames, power_price, simulate, stack_kg_h, summarise, wind_steps)

STILL = Aannames(onderhoud_dagen=0, storingen_per_jaar=0, startvertraging_min=0, min_aan_min=0, min_uit_min=0)


def supply(values, year=2024):
    return {"jaar": year, "t": [1704067200 + i * 600 for i in range(len(values))], "mw": values}


class OpsplitsingTests(unittest.TestCase):
    def test_no_hydrogen_below_minimum_load(self):
        a = Aannames(minimumlast=0.2)
        self.assertEqual(stack_kg_h(0.19 * 11, 11, a), 0)
        self.assertGreater(stack_kg_h(0.2 * 11, 11, a), 0)

    def test_bop_is_ten_percent_at_full_load_like_the_website(self):
        self.assertAlmostEqual(draw_mw(44, 44, Aannames()), 48.4)

    def test_new_stack_at_full_load_matches_eu_tool_consumption(self):
        for name, a in TECHNOLOGIES.values():
            fresh = replace(a, degradatie_1000h=0)
            self.assertAlmostEqual(draw_mw(44, 44, fresh) * 1000 / stack_kg_h(44, 44, fresh), a.systeemverbruik_vol, msg=name)
        self.assertEqual(TECHNOLOGIES["alkaline"][1].capex_eur_kw, 2075)
        self.assertAlmostEqual(power_price(Aannames()), 110.91)

    def test_dispatch_respects_minimum_and_capacity(self):
        a = Aannames(minimumlast=0.2)
        minimum = draw_mw(0.2 * 11, 11, a)
        self.assertEqual(desired_count(4 * minimum - 0.01, 4, 11, a, "samen", {}), 0)
        self.assertEqual(desired_count(60, 4, 11, a, "verdelen", {}), 4)
        self.assertEqual(desired_count(draw_mw(11, 11, a) + minimum - 0.01, 4, 11, a, "bijschakelen", {}), 1)
        self.assertEqual(desired_count(0, 4, 11, a, "verdelen", {}), 0)

    def test_splitting_captures_low_wind_that_one_module_misses(self):
        a = replace(STILL, minimumlast=0.4)
        low = supply([10.0] * 60)        # onder de drempel van 44 MW, boven die van 11 MW
        self.assertEqual(simulate(low, 1, a, "verdelen")["waterstof_t"], 0)
        self.assertGreater(simulate(low, 4, a, "verdelen")["waterstof_t"], 0)

    def test_starts_warm_and_cold(self):
        a = replace(STILL, koud_na_uur=4)
        result = simulate(supply([48.4] * 6 + [0.0] * 6 + [48.4] * 6), 1, a, "verdelen")
        per_year = 8760 / 3
        self.assertAlmostEqual(result["starts_koud_per_module"] / per_year, 1)
        self.assertAlmostEqual(result["starts_warm_per_module"] / per_year, 1)

    def test_start_delay_skips_short_gusts(self):
        gusty = supply(([0.0] * 3 + [48.4]) * 30)
        quick = simulate(gusty, 1, STILL, "verdelen")
        patient = simulate(gusty, 1, replace(STILL, startvertraging_min=20), "verdelen")
        self.assertGreater(quick["starts_warm_per_module"] + quick["starts_koud_per_module"], 0)
        self.assertEqual(patient["starts_warm_per_module"] + patient["starts_koud_per_module"], 0)

    def test_minimum_on_time_keeps_a_started_module_running(self):
        dip = supply([48.4, 12.0, 12.0, 12.0])
        running = lambda a: [sum(x > 0 for x in s["stack"]) for s in simulate(dip, 2, a, "verdelen", trace=range(4))["stappen"]]
        self.assertEqual(running(STILL), [2, 1, 1, 1])                       # zonder minimum: direct terug naar één
        self.assertEqual(running(replace(STILL, min_aan_min=30)), [2, 2, 2, 1])

    def test_outage_stops_one_large_module_but_not_all_small_ones(self):
        a = replace(STILL, onderhoud_dagen=10)
        spring = {"jaar": 2024, "t": [1704067200 + 110 * 86400 + i * 600 for i in range(144)], "mw": [20.0] * 144}
        self.assertEqual(simulate(spring, 1, a, "verdelen")["waterstof_t"], 0)
        self.assertGreater(simulate(spring, 4, a, "verdelen")["waterstof_t"], 0)

    def test_economics_and_break_even(self):
        a = STILL
        flat = supply([30.0] * 600)
        rows = [summarise([simulate(flat, n, a, "verdelen")], a) for n in (1, 8)]
        break_even(rows, a)
        self.assertGreater(rows[1]["capex_meur"], a.capex_eur_kw * 44 / 1000)   # kleinere modules duurder per kW
        self.assertAlmostEqual(rows[0]["capex_break_even_meur"], rows[0]["capex_meur"])
        self.assertGreater(economics(rows[0], a)["lcoh_eur_kg"], 0)

    def test_subsidies_and_revenues(self):
        flat = supply([30.0] * 600)
        base = summarise([simulate(flat, 1, STILL, "verdelen")], STILL)
        helped = replace(STILL, capex_subsidie_eur_kw=500, waterstofpremie_eur_kg=1, zuurstofprijs_eur_t=50)
        row = summarise([simulate(flat, 1, helped, "verdelen")], helped)
        saved = 500 * 44_000 * 0.06 / (1 - 1.06 ** -20) / (row["waterstof_t"] * 1000)
        self.assertAlmostEqual(base["lcoh_eur_kg"] - row["lcoh_eur_kg"], saved)
        self.assertAlmostEqual(row["lcoh_eur_kg"] - row["netto_eur_kg"], 1 + 50 * 8 / 1000)
        self.assertEqual(power_price(replace(STILL, korting_net_belasting_eur_mwh=200)), STILL.stroomprijs_eur_mwh)

    def test_break_even_with_capex_subsidy_reproduces_single_module_cost(self):
        helped = replace(STILL, capex_subsidie_eur_kw=500)
        flat = supply([30.0] * 600)
        rows = [summarise([simulate(flat, n, helped, "verdelen")], helped) for n in (1, 4)]
        break_even(rows, helped)
        priced = replace(helped, capex_eur_kw=helped.capex_eur_kw * rows[1]["capex_break_even_meur"] / rows[1]["capex_meur"])
        again = summarise([simulate(flat, 4, priced, "verdelen")], priced)
        self.assertAlmostEqual(again["lcoh_eur_kg"], rows[0]["lcoh_eur_kg"], places=6)

    def test_trace_parts_add_up(self):
        quick = replace(STILL, opstart_warm_min=0, opstart_koud_min=0)
        result = simulate(supply([3.0, 12.0, 30.0, 48.4, 20.0]), 4, quick, "verdelen", trace=range(5))
        for step in result["stappen"]:
            self.assertAlmostEqual(sum(step["kg"]), sum(stack_kg_h(x, 11, quick) / 6 for x in step["stack"]), places=2)
            self.assertLessEqual(step["verbruik"], step["aanbod"] + 1e-6)
        total = sum(sum(step["kg"]) for step in result["stappen"])
        self.assertAlmostEqual(total, result["waterstof_t"] * 1000 * 5 / 52560, places=1)

    def test_wind_steps_match_supply_model(self):
        stamp = 1720000000
        for park_id in ("fryslan", "beabuorren"):
            curve = load_curve(park_id)
            step = wind_steps(park_id, 7.5, stamp, curve)
            self.assertAlmostEqual(step["mw"], park_mw(park_id, 7.5, datetime.fromtimestamp(stamp, timezone.utc), curve), places=3)
            self.assertAlmostEqual(step["v_as"], 7.5 * (step["ashoogte"] / 10) ** step["alpha"], places=2)

    def test_combined_wind_takes_the_highest_station_and_fills_gaps(self):
        moments, speeds, sources = combine_wind({"houtribdijk": {1: 6.0, 2: 3.0, 3: None}, "stavoren": {1: 4.0, 2: 5.0, 4: 2.0}})
        self.assertEqual(moments, [1, 2, 4])
        self.assertEqual(speeds, [6.0, 5.0, 2.0])
        self.assertEqual(sources, ["houtribdijk", "stavoren", "stavoren"])

    def test_parse_aannames_uses_displayed_units_and_bounds(self):
        self.assertAlmostEqual(parse_aannames({"minimumlast": 30}).minimumlast, 0.30)
        with self.assertRaises(ValueError):
            parse_aannames({"minimumlast": 95})
        with self.assertRaises(ValueError):
            parse_aannames({"rente": "7"})
        keys = {item[0] for _, items in AANNAMES_META for item in items}
        self.assertEqual(keys, set(Aannames.__dataclass_fields__))


if __name__ == "__main__":
    unittest.main()
