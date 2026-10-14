"""Vergelijk HARMONIE-wind en het stationsmodel voor Windpark Fryslân per dag.

    python3 -m windprofiel.compare 2026-01-08 2026-02-03 --production 2026-01-08=4.5

Alle windreeksen (zie compare_day) gaan door hetzelfde kubische model met 5 %
zogverlies. Productie in GWh is optioneel en komt uit de app van Windpark Fryslân.
"""

import argparse
import json
from math import log
from datetime import date, datetime, timedelta
from pathlib import Path

from .application import PARKS, interpolate_minutes, park_power_mw, parse_wind, shear_exponent
from .harmonie import HarmonieClient, hub_speed, local_day_hours, shear_factor
from .knmi import KNMIClient, KNMIError, load_env_file
from .profile import local_minutes

ROOT = Path(__file__).resolve().parent.parent
FRYSLAN = PARKS["fryslan"]


def hourly_minutes(points: list[tuple[datetime, float | None]], moments) -> list[float | None]:
    """Uurwaarden lineair naar minuten; geen overbrugging van gaten."""
    points = [p for p in points if p[1] is not None]
    result = []
    for moment in moments:
        before = [p for p in points if p[0] <= moment]
        after = [p for p in points if p[0] >= moment]
        if not before or not after or after[0][0] - before[-1][0] > timedelta(hours=1):
            result.append(None)
            continue
        (t0, v0), (t1, v1) = before[-1], after[0]
        result.append(v0 if t0 == t1 else v0 + (v1 - v0) * ((moment - t0) / (t1 - t0)))
    return result


def harmonie_minutes(samples: list[dict | None], moments, value=hub_speed) -> list[float | None]:
    """HARMONIE-momentopnames per uur, omgezet met `value`, lineair naar minuten."""
    return hourly_minutes([(datetime.fromisoformat(s["valid"]), value(s["speed_ms"]))
                           for s in samples if s is not None], moments)


def station_mean(observations: list[tuple[datetime, float | None]], moment: datetime) -> float | None:
    """Gemiddelde stationswind binnen een half uur rond een HARMONIE-uur.

    Aan de daggrenzen zijn alleen de waarden binnen de opgevraagde dag beschikbaar;
    minstens drie tienminutengemiddelden zijn vereist.
    """
    values = [v for t, v in observations if abs((t - moment).total_seconds()) <= 1800 and v is not None]
    return None if len(values) < 3 or sum(values) <= 0 else sum(values) / len(values)


def energy(hub: list[float | None]) -> tuple[float | None, list[float | None]]:
    power = [park_power_mw(v, "fryslan", None, wake=True) for v in hub]
    hourly = []
    for h in range(0, len(power), 60):
        chunk = power[h:h + 60]
        hourly.append(None if None in chunk else sum(chunk) / 60)
    return (None if None in power else sum(power) / 60), hourly


def compare_day(day: date, harmonie: HarmonieClient, knmi: KNMIClient, lead: int = 1) -> dict:
    """Vier windreeksen op 115 m voor één dag, alle door hetzelfde vermogensmodel.

    station:  stationswind × seizoens-α (huidig model)
    harmonie: HARMONIE per uur, lineair naar minuten
    shear:    stationswind × HARMONIE-verhouding v115/v10 boven het park
    level:    stationswind × v115(HARMONIE) / uurgemiddelde stationswind
    """
    moments = local_minutes(day)
    start, hours = local_day_hours(day)
    samples = harmonie.hourly_series(start, hours + 1, lead=lead)
    station = FRYSLAN["station"]
    observations = parse_wind(knmi.observations(station, day), station)
    s_wind = interpolate_minutes(observations, moments)
    alpha = shear_exponent(FRYSLAN, day)
    times = [(datetime.fromisoformat(s["valid"]), s["speed_ms"]) for s in samples if s is not None]
    level = []
    for moment, speeds in times:
        mean_wind = station_mean(observations, moment)
        level.append((moment, None if mean_wind is None else hub_speed(speeds) / mean_wind))
    scale = lambda factors: [None if v is None or f is None else v * f for v, f in zip(s_wind, factors)]
    series = {
        "station": [None if v is None else v * (FRYSLAN["hub_height"] / 10) ** alpha for v in s_wind],
        "harmonie": harmonie_minutes(samples, moments),
        "shear": scale(harmonie_minutes(samples, moments, shear_factor)),
        "level": scale(hourly_minutes(level, moments)),
    }
    mean = lambda xs: None if None in xs else sum(xs) / len(xs)
    result = {"date": day.isoformat(), "alpha_station": round(alpha, 3),
              "alpha_harmonie": [round(log(shear_factor(s)) / log(FRYSLAN["hub_height"] / 10), 3) for _, s in times],
              "missing_harmonie_hours": samples.count(None)}
    for name, hub in series.items():
        total, hourly = energy(hub)
        result[name] = {"gwh": None if total is None else total / 1000, "hub_ms": mean(hub), "hourly_mwh": hourly}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dates", nargs="+", type=date.fromisoformat)
    parser.add_argument("--production", nargs="*", default=[], help="DATUM=GWh uit de WPF-app")
    parser.add_argument("--lead", type=int, default=1, help="voorspellingstermijn in uren (standaard 1)")
    parser.add_argument("--json", type=Path, help="schrijf alle uitkomsten ook als JSON")
    args = parser.parse_args()
    load_env_file(ROOT / ".env")
    production = {date.fromisoformat(k): float(v) for k, v in (p.split("=") for p in args.production)}
    try:
        harmonie = HarmonieClient(ROOT / ".cache" / "harmonie")
        knmi = KNMIClient(ROOT / ".cache" / "knmi")
        results = [compare_day(day, harmonie, knmi, args.lead) for day in args.dates]
    except KNMIError as exc:
        print(str(exc))
        return 1
    fmt = lambda x, n=2: "—" if x is None else f"{x:.{n}f}"
    names = ("station", "harmonie", "shear", "level")
    print("datum       productie" + "".join(f"{n:>10}" for n in names) + "   (GWh)")
    errors = {n: [] for n in names}
    for r in results:
        p = production.get(date.fromisoformat(r["date"]))
        print(f"{r['date']}  {fmt(p):>8}" + "".join(f"{fmt(r[n]['gwh']):>10}" for n in names))
        if p is not None:
            r["production_gwh"] = p
            for n in names:
                if r[n]["gwh"] is not None:
                    errors[n].append(abs(r[n]["gwh"] - p))
    if any(errors.values()):
        print("gem. |fout|          " + "".join(f"{fmt(sum(e) / len(e) if e else None):>10}" for e in errors.values()))
    if args.json:
        args.json.write_text(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
