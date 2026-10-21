import tempfile
import unittest
from pathlib import Path

from windprofiel.opsplitsing import Aannames, break_even, simulate, summarise
from windprofiel.scenarios import listing, load, parse_counts, save, slug, write_overview

STILL = Aannames(onderhoud_dagen=0, storingen_per_jaar=0, startvertraging_min=0, min_aan_min=0, min_uit_min=0)


def result(counts=(1, 2, 4)):
    supply = {"jaar": 2024, "t": [1704067200 + i * 600 for i in range(600)], "mw": [3.0] * 200 + [8.0] * 200 + [30.0] * 200}
    rows = [summarise([simulate(supply, n, STILL, "verdelen")], STILL) for n in counts]
    break_even(rows, STILL)
    return {"strategie": "verdelen", "jaren": [2024], "rijen": rows, "aannames": {}, "uit_cache": False, "rekentijd_s": 1.0}


class ScenarioTests(unittest.TestCase):
    def test_parse_counts_accepts_ranges_and_lists(self):
        self.assertEqual(parse_counts("1-4"), [1, 2, 3, 4])
        self.assertEqual(parse_counts("1,2, 4,8"), [1, 2, 4, 8])
        self.assertEqual(parse_counts("1-3,6,10-11"), [1, 2, 3, 6, 10, 11])
        for bad in ("0-4", "1-65", "a", "1-b", ""):
            with self.assertRaises(ValueError):
                parse_counts(bad)

    def test_slug_is_a_safe_file_name(self):
        self.assertEqual(slug("Alkaline, hoge minimumlast · verdelen · 2025 · 1–16 modules"),
                         "alkaline-hoge-minimumlast-verdelen-2025-1-16-modules")
        self.assertEqual(slug("../../etc"), "etc")
        self.assertEqual(slug("···"), "scenario")

    def test_save_list_load_and_overview(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            path = save("Test · verdelen", "pem", {"minimumlast": 40}, result(), folder)
            self.assertEqual(path.name, "test-verdelen.json")
            stored = load("test-verdelen", folder)
            self.assertNotIn("uit_cache", stored["resultaat"])
            [item] = listing(folder)
            best = min(stored["resultaat"]["rijen"], key=lambda r: r["lcoh_eur_kg"])
            self.assertEqual(item["beste"]["modules"], best["modules"])
            self.assertEqual(item["modules"], [1, 2, 4])
            self.assertEqual(item["eigen_aannames"], {"minimumlast": 40})
            # Opnieuw opslaan onder dezelfde naam overschrijft.
            save("Test · verdelen", "pem", {}, result((1, 2)), folder)
            self.assertEqual(len(listing(folder)), 1)
            (folder / "kapot.json").write_text("{")   # half geschreven bestand wordt overgeslagen
            self.assertEqual(len(listing(folder)), 1)
            lines = write_overview(folder).read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1 + 2)
            self.assertTrue(lines[1].startswith("Test · verdelen,pem,2024,verdelen,1,"))

    def test_load_refuses_paths_outside_the_folder(self):
        with tempfile.TemporaryDirectory() as name:
            for bad in ("../geheim", "a/b", "", "Test", "x" * 81):
                with self.assertRaises(ValueError):
                    load(bad, Path(name))
            with self.assertRaises(ValueError):
                load("bestaat-niet", Path(name))


if __name__ == "__main__":
    unittest.main()
