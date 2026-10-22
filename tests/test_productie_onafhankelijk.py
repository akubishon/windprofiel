"""Gemeten productie mag de windreeks en de modelopbrengst niet veranderen."""

import ast
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from windprofiel import application, opsplitsing, productie, windbron

PACKAGE = Path(application.__file__).parent


def knmi_payload(station, values, start):
    stamps = [f"{start}T00:{m:02d}:00Z" for m in range(10, 10 * (len(values) + 1), 10)]
    return {"type": "CoverageCollection", "parameters": {"ff": {"unit": {"symbol": {"value": "m/s"}},
                                                                "measurementType": {"method": "mean", "duration": "-PT10M"}}},
            "coverages": [{"eumetnet:locationId": station,
                           "domain": {"domainType": "PointSeries", "axes": {"t": {"values": stamps}}},
                           "ranges": {"ff": {"axisNames": ["t"], "shape": [len(values)], "values": values}}}]}


class Client:
    def locations(self):
        return {"features": [{"id": sid, "properties": {"name": sid}} for _, sid in windbron.STATIONS.values()]}

    def observations(self, station, day):
        return knmi_payload(station, [4.0, 9.0, 13.0, 6.0, 7.5], "2025-01-01")

    def observations_range(self, station, start, end):
        return knmi_payload(station, [4.0, 9.0, 13.0, 6.0, 7.5], "2025-01-01")


def altered_production(folder: Path) -> Path:
    path = folder / "productie.csv"
    rows = ["datum,productie_kwh"] + [f"{d.isoformat()},{int(v * 1000 * 0.3 + 12345000)}" for d, v in productie.load().items()]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


class ProductionIndependenceTests(unittest.TestCase):
    def test_wind_and_model_modules_do_not_read_production(self):
        # Statisch: windbron, ashoogte, wins50 en opsplitsing importeren productie of ijking niet.
        for name in ("windbron.py", "ashoogte.py", "wins50.py", "opsplitsing.py", "profile.py", "knmi.py"):
            tree = ast.parse((PACKAGE / name).read_text(encoding="utf-8"))
            imported = {alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
                        for alias in node.names} | {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
            self.assertFalse({"productie", "ijking"} & imported, name)
            self.assertNotIn("productie_fryslan", (PACKAGE / name).read_text(encoding="utf-8"), name)

    def test_changed_production_does_not_change_the_day_profile(self):
        with patch("windprofiel.application.load_curve", return_value=None):
            before = application.build_profile(date(2025, 1, 1), client=Client())
            with tempfile.TemporaryDirectory() as folder:
                path = altered_production(Path(folder))
                with patch("windprofiel.productie.load", lambda p=path: _load(p)):
                    after = application.build_profile(date(2025, 1, 1), client=Client())
        for park_id in windbron.HUB_HEIGHT:
            for key in ("wind_ms", "hub_wind_ms", "power_mw", "interval_power_mw", "energy_mwh", "factor"):
                self.assertEqual(before["parks"][park_id][key], after["parks"][park_id][key], (park_id, key))
        self.assertEqual(before["hydrogen"], after["hydrogen"])
        # Alleen de gemeten waarde zelf verandert.
        self.assertNotEqual(before["measured"]["energy_mwh"], after["measured"]["energy_mwh"])

    def test_changed_production_does_not_change_the_yearly_supply(self):
        results = []
        with tempfile.TemporaryDirectory() as cache, tempfile.TemporaryDirectory() as folder:
            path = altered_production(Path(folder))
            for production in (productie.PRODUCTION, path):
                with patch.object(opsplitsing, "CACHE", Path(cache) / production.name), \
                        patch("windprofiel.productie.load", lambda p=production: _load(p)):
                    results.append(opsplitsing.supply_year(2025, client=Client()))
        self.assertEqual(results[0], results[1])
        self.assertTrue(results[0]["mw"])


def _load(path):
    """Gemeten productie uit een vervangend bestand (zelfde formaat als productie_fryslan.csv)."""
    with open(path, encoding="utf-8") as file:
        next(file)
        return {date.fromisoformat(a): int(b) / 1000 for a, b in (line.strip().split(",") for line in file if line.strip())}


if __name__ == "__main__":
    unittest.main()
