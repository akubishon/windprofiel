"""Toets de hoogte-exponent voor Windpark Fryslân op de opgeslagen dagproductie.

Afregelen en stilstand verlagen de productie alleen. Dagen die onder een grens
maal het model blijven (en minstens 0,5 GWh lager) gelden daarom als verdacht en
tellen niet mee; daarna wordt opnieuw gefit tot de selectie stabiel is. Zie
docs/rekenmodel.md, sectie 7, voor de uitkomst en de beperkingen.

De dagproductie staat in data/productie_fryslan.csv, zodat deze toets zonder
nieuwe aanvragen bij de app van Windpark Fryslân opnieuw kan draaien. De wind
komt uit de jaarcache van de opsplitsing (één KNMI-aanvraag per station per jaar).
"""

import argparse
import csv
import math
from datetime import date, datetime
from pathlib import Path

from .application import PARKS, ROOT, load_curve, park_power_mw
from .knmi import KNMIError, load_env_file
from .opsplitsing import LOCAL, available_years, supply_year

PRODUCTION = Path(__file__).parent / "data" / "productie_fryslan.csv"
ALPHA_STEP = 0.005
ALPHAS = [i * ALPHA_STEP for i in range(91)]   # 0 tot 0,45
CURRENT = (0.115, 0.065)                       # application.PARKS["fryslan"]: alpha + alpha_seasonal


def load_production(path: Path = PRODUCTION) -> dict[date, float]:
    """Dagproductie in GWh; lege waarden ontbreken, nul blijft nul."""
    with path.open(encoding="utf-8") as file:
        return {date.fromisoformat(row["datum"]): int(row["productie_kwh"]) / 1e6
                for row in csv.DictReader(file) if row["productie_kwh"] not in ("", "None")}


def wind_per_day(years: list[int]) -> dict[str, dict[date, list[float]]]:
    """KNMI-wind per dag: Houtribdijk alleen, en per tien minuten de hoogste van beide stations."""
    days = {"houtribdijk": {}, "hoogste": {}}
    for year in years:
        supply = supply_year(year)
        for stamp, high, low in zip(supply["t"], supply["stations"]["houtribdijk"], supply["stations"]["stavoren"]):
            day = datetime.fromtimestamp(stamp, LOCAL).date()
            if high is not None:
                days["houtribdijk"].setdefault(day, []).append(high)
            days["hoogste"].setdefault(day, []).append(max(v for v in (high, low) if v is not None))
    return days


def prepare(production: dict[date, float], wind: dict[date, list[float]]) -> list[tuple]:
    """Per bruikbare dag: productie, seizoensfase en modelenergie voor elke α op het raster."""
    park, curve = PARKS["fryslan"], load_curve("fryslan")
    rows = []
    for day, speeds in sorted(wind.items()):
        if len(speeds) < 138 or production.get(day, 0) <= 0:   # bijna volledige dag en echte productie
            continue
        phase = math.cos(2 * math.pi * (day.timetuple().tm_yday - 1) / 365)
        energy = []
        for alpha in ALPHAS:
            factor = (park["hub_height"] / 10) ** alpha
            energy.append(sum(park_power_mw(v * factor, "fryslan", curve, wake=True) for v in speeds) / 6000)
        rows.append((day, production[day], phase, energy))
    return rows


def model(row: tuple, a: float, b: float) -> float:
    alpha = min(max(a + b * row[2], 0.0), ALPHAS[-1])
    index = alpha / ALPHA_STEP
    low = int(index)
    high = min(low + 1, len(ALPHAS) - 1)
    weight = index - low
    return row[3][low] * (1 - weight) + row[3][high] * weight


def fit(rows: list[tuple], keep: list[bool]) -> tuple[float, float]:
    best = None
    for a in (i * ALPHA_STEP for i in range(61)):
        for b in (i * ALPHA_STEP for i in range(31)):
            error = sum((model(r, a, b) - r[1]) ** 2 for r, k in zip(rows, keep) if k)
            if best is None or error < best[0]:
                best = (error, a, b)
    return best[1], best[2]


def robust_fit(rows: list[tuple], limit: float | None) -> dict:
    """Fit zonder verdachte dagen; limit None gebruikt alle dagen."""
    keep = [True] * len(rows)
    for _ in range(10):
        a, b = fit(rows, keep)
        if limit is None:
            break
        new = [not (r[1] < limit * model(r, a, b) and model(r, a, b) - r[1] > 0.5) for r in rows]
        if new == keep:
            break
        keep = new
    kept = [r for r, k in zip(rows, keep) if k]
    rms = lambda ab: math.sqrt(sum((model(r, *ab) - r[1]) ** 2 for r in kept) / len(kept))
    return {"a": a, "b": b, "dagen": len(rows), "behouden": len(kept), "rms_gwh": rms((a, b)),
            "rms_huidige_gwh": rms(CURRENT)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Toets α voor Windpark Fryslân op de opgeslagen dagproductie.")
    parser.add_argument("--jaren", type=int, nargs="+", default=available_years())
    parser.add_argument("--grenzen", type=float, nargs="+", default=[0.65, 0.75, 0.85])
    args = parser.parse_args()
    load_env_file(ROOT / ".env")
    production = load_production()
    try:
        wind = wind_per_day(args.jaren)
    except KNMIError as exc:
        print(str(exc))
        return 1
    for option, days in wind.items():
        rows = prepare(production, days)
        for limit in [*args.grenzen, None]:
            r = robust_fit(rows, limit)
            name = f"{limit:.0%}" if limit else "geen"
            print(f"{option:12} grens {name:>4}: α = {r['a']:.3f} + {r['b']:.3f}·cos "
                  f"(winter {r['a'] + r['b']:.3f}, zomer {r['a'] - r['b']:.3f}), behouden {r['behouden']}/{r['dagen']}, "
                  f"RMS {r['rms_gwh']:.2f} GWh (huidige formule {r['rms_huidige_gwh']:.2f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
