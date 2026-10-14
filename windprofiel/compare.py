"""Vergelijk HARMONIE-wind en het stationsmodel voor Windpark Fryslân per dag.

    python3 -m windprofiel.compare 2026-01-08 2026-02-03 --production 2026-01-08=4.5

Beide bronnen gaan door hetzelfde kubische model met 5 % zogverlies. Productie
in GWh is optioneel en komt uit de app van Windpark Fryslân.
"""

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from .application import PARKS, interpolate_minutes, park_power_mw, parse_wind, shear_exponent
from .harmonie import HarmonieClient, hub_speed, local_day_hours
from .knmi import KNMIClient, KNMIError, load_env_file
from .profile import local_minutes

ROOT = Path(__file__).resolve().parent.parent
FRYSLAN = PARKS["fryslan"]


def harmonie_minutes(samples: list[dict | None], moments) -> list[float | None]:
    """Uurwaarden (momentopnames) lineair naar minuten; geen overbrugging van gaten."""
    points = [(datetime.fromisoformat(s["valid"]), hub_speed(s["speed_ms"]))
              for s in samples if s is not None]
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


def energy(hub: list[float | None], moments) -> tuple[float | None, list[float | None]]:
    power = [park_power_mw(v, "fryslan", None, wake=True) for v in hub]
    hourly = []
    for h in range(0, len(power), 60):
        chunk = power[h:h + 60]
        hourly.append(None if None in chunk else sum(chunk) / 60)
    return (None if None in power else sum(power) / 60), hourly


def compare_day(day: date, harmonie: HarmonieClient, knmi: KNMIClient, lead: int = 1) -> dict:
    moments = local_minutes(day)
    start, hours = local_day_hours(day)
    samples = harmonie.hourly_series(start, hours + 1, lead=lead)
    h_hub = harmonie_minutes(samples, moments)
    station = FRYSLAN["station"]
    s_wind = interpolate_minutes(parse_wind(knmi.observations(station, day), station), moments)
    alpha = shear_exponent(FRYSLAN, day)
    s_hub = [None if v is None else v * (FRYSLAN["hub_height"] / 10) ** alpha for v in s_wind]
    h_energy, h_hourly = energy(h_hub, moments)
    s_energy, s_hourly = energy(s_hub, moments)
    mean = lambda xs: None if None in xs else sum(xs) / len(xs)
    return {"date": day.isoformat(), "alpha_station": round(alpha, 3),
            "harmonie_hub_ms": mean(h_hub), "station_hub_ms": mean(s_hub),
            "harmonie_gwh": None if h_energy is None else h_energy / 1000,
            "station_gwh": None if s_energy is None else s_energy / 1000,
            "harmonie_hourly_mwh": h_hourly, "station_hourly_mwh": s_hourly,
            "missing_harmonie_hours": samples.count(None)}


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
    print("datum       productie  HARMONIE  station   v115 H/S (m/s)")
    for r in results:
        p = production.get(date.fromisoformat(r["date"]))
        print(f"{r['date']}  {fmt(p):>8}  {fmt(r['harmonie_gwh']):>8}  {fmt(r['station_gwh']):>7}"
              f"   {fmt(r['harmonie_hub_ms'], 1)} / {fmt(r['station_hub_ms'], 1)}")
        if p is not None:
            r["production_gwh"] = p
    if args.json:
        args.json.write_text(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
