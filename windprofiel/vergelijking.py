"""Gemodelleerde mogelijke opbrengst van Windpark Fryslân naast de gemeten dagproductie, 2022–2025.

Drie grootheden blijven gescheiden:

1. wind op ashoogte (m/s), uit KNMI-stationswind en de hoogtevertaling (`windbron.py`);
2. gemodelleerde mogelijke elektrische opbrengst (MWh): turbinecurve, zogverlies, 100 %
   beschikbaarheid, geen afregeling of netbeperking;
3. gemeten productie (MWh per dag) uit de app van Windpark Fryslân.

Het model rekent per oorspronkelijk KNMI-tienminuteninterval en telt op naar dezelfde
kalenderdagen (Europe/Amsterdam) als de productie. Een dag telt alleen mee als alle intervallen
wind hebben (144, of 138/150 bij de klokwissel); er wordt niets ingevuld. Uit de dagtotalen wordt
geen tienminutenproductie gereconstrueerd.

De periode ligt vooraf vast: alle dagen van 2022 tot en met 2025 met gemeten productie en volledige
wind in álle varianten (oud, nieuw en de gevoeligheden), zodat elke variant op precies dezelfde dagen
wordt vergeleken. Er worden geen dagen weggelaten op grond van het verschil. Het verschil heet ‘verschil
tussen model en gemeten productie’; een oorzaak wordt niet toegeschreven.

    python3 -m windprofiel.vergelijking              # schrijft uitvoer/vergelijking/
    python3 -m windprofiel.vergelijking --waterstof  # ook de gevolgen voor de opsplitsing (enkele minuten)
"""

import argparse
import csv
import json
import math
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import productie, windbron
from .application import FRYSLAN_SCENARIO, PARKS, ROOT, day_intervals, load_curve, parse_wind, turbine_kw
from .knmi import KNMIClient, KNMIError, load_env_file
from .profile import cubic_power_kw

LOCAL = ZoneInfo("Europe/Amsterdam")
PERIOD = (date(2022, 1, 1), date(2025, 12, 31))
OUT = ROOT / "uitvoer" / "vergelijking"
EXTRA_STATIONS: dict[str, tuple[str, str]] = {}   # alleen IJsselmeerstations, zie ashoogte.CHOICE


def year_stations(client: KNMIClient, keys: list[str], year: int) -> dict[str, dict[datetime, float]]:
    """Tienminutenwind per station op intervalmidden (UTC), zelfde aanvraag als het jaaraanbod."""
    start = datetime(year, 1, 1, tzinfo=LOCAL).astimezone(timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=LOCAL).astimezone(timezone.utc)
    out = {}
    for key in keys:
        station = windbron.station_id(key) if key in windbron.STATIONS else EXTRA_STATIONS[key][1]
        samples = parse_wind(client.observations_range(station, start, end), station)
        out[key] = {t: v for t, v in samples if v is not None}
    return out


DRIFT_REFERENCE = (2019, 2021)   # dezelfde jaren als WINS50
DRIFT_STATIONS = {"Houtribdijk": "0-20000-0-06258", "Stavoren": "0-20000-0-06267", "Vlieland": "0-20000-0-06242",
                  "Leeuwarden": "0-20000-0-06270"}


def station_drift(client: KNMIClient, years: range) -> dict:
    """Jaargemiddelde verhoudingen tussen stations, over momenten waarop alle vier meten.

    Een station waarvan de verhouding tot de andere verschuift, meet in de vergelijkingsjaren anders dan in
    de WINS50-jaren; dan klopt de factor F niet meer precies. Alleen stationsdata, geen productie.
    """
    out = {}
    for year in years:
        data = {name: year_stations_by_id(client, sid, year) for name, sid in DRIFT_STATIONS.items()}
        common = set.intersection(*(set(d) for d in data.values()))
        mean = {name: sum(d[t] for t in common) / len(common) for name, d in data.items()}
        out[year] = {"momenten": len(common), **{f"{a}/{b}": round(mean[a] / mean[b], 4) for a, b in
                                                  (("Houtribdijk", "Stavoren"), ("Houtribdijk", "Vlieland"),
                                                   ("Stavoren", "Vlieland"), ("Stavoren", "Leeuwarden"))}}
    return out


def year_stations_by_id(client: KNMIClient, station: str, year: int) -> dict[datetime, float]:
    start = datetime(year, 1, 1, tzinfo=LOCAL).astimezone(timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=LOCAL).astimezone(timezone.utc)
    return {t: v for t, v in parse_wind(client.observations_range(station, start, end), station) if v is not None}


def fryslan_power(speed: float, wake: float, rated_speed: float, curve: dict | None) -> float:
    """Parkvermogen (MW) zoals `application.park_power_mw`, met instelbaar zog en nominale wind (gevoeligheid)."""
    if curve is not None:
        kw = turbine_kw(speed, "fryslan", curve)
        if wake and kw > 0:
            kw = turbine_kw(speed * (1 - wake), "fryslan", curve)
    else:
        limits = {k: FRYSLAN_SCENARIO[k] for k in ("rated_kw", "cut_in", "cut_out")}
        kw = cubic_power_kw(speed, rated_speed=rated_speed, **limits)
        if wake and kw > 0:
            kw = cubic_power_kw(speed * (1 - wake), rated_speed=rated_speed, **limits)
    return kw * PARKS["fryslan"]["count"] / 1000


def variant_days(stations: dict[int, dict], pm: windbron.ParkMethod, wake: float, rated_speed: float, curve: dict | None,
                 period=PERIOD) -> dict[date, dict]:
    """Per kalenderdag: dekking, gemiddelde wind op ashoogte en modelenergie uit de tienminutenintervallen."""
    out = {}
    day = period[0]
    while day <= period[1]:
        values = stations[day.year]
        slots = day_intervals(day)
        hub, power = [], []
        for t in slots:
            speed, _ = windbron.select(pm, {key: series.get(t) for key, series in values.items()})
            if speed is None:
                continue
            v = speed * windbron.factor("fryslan", pm, t)
            hub.append(v)
            power.append(fryslan_power(v, wake, rated_speed, curve))
        out[day] = {"intervallen": len(slots), "met_wind": len(hub),
                    "wind_ashoogte_ms": sum(hub) / len(hub) if hub else None,
                    "model_mwh": sum(power) / 6 if len(power) == len(slots) else None}
        day += timedelta(days=1)
    return out


def variants(table: dict) -> dict[str, tuple[str, windbron.ParkMethod, float, float]]:
    """Naam → (uitleg, methode, zogverlies, nominale wind). De eerste is de nieuwe standaard."""
    new = windbron.METHODS["onafhankelijk"]["fryslan"]
    entry = table["parken"]["fryslan"]
    per_year = entry["factor_per_jaar"]
    low = tuple(min(per_year[y][m] for y in per_year if per_year[y][m] is not None) for m in range(12))
    high = tuple(max(per_year[y][m] for y in per_year if per_year[y][m] is not None) for m in range(12))
    wake, rated = PARKS["fryslan"]["wake_deficit"], FRYSLAN_SCENARIO["rated_speed"]
    out = {
        "nieuw": ("Productie-onafhankelijk: " + entry["bron"] + ", WINS50-maandfactor", new, wake, rated),
        "oud_dagprofiel": (windbron.LABELS["productie_houtribdijk"], windbron.METHODS["productie_houtribdijk"]["fryslan"], wake, rated),
        "oud_opsplitsing": (windbron.LABELS["productie_hoogste"], windbron.METHODS["productie_hoogste"]["fryslan"], wake, rated),
        "factor_laagste_jaar": ("F per maand van het laagste WINS50-jaar (2019–2021)", replace(new, factors=low), wake, rated),
        "factor_hoogste_jaar": ("F per maand van het hoogste WINS50-jaar (2019–2021)", replace(new, factors=high), wake, rated),
        "ashoogte_109_m": ("Ashoogte 109 m (persbericht 2018) in plaats van 115 m",
                           replace(new, factors=tuple(entry["alternatieven"]["ashoogte_109_m"])), wake, rated),
        "alleen_hoogtetoename": ("Ontleding: alleen de WINS50-hoogtetoename op de parklocatie, zonder correctie voor de stationsligging",
                                 replace(new, factors=tuple(entry["schering"])), wake, rated),
        "drift_houtribdijk": ("Houtribdijk per jaar gecorrigeerd naar zijn verhouding met Stavoren in 2019–2021",
                              replace(new, stations=("houtribdijk_drift", "stavoren"), factors=tuple(entry["factor"])), wake, rated),
        "zog_0": ("Geen zogverlies", new, 0.0, rated),
        "zog_10": ("Zogverlies 10 % minder wind", new, 0.10, rated),
        "nominale_wind_10_5": ("Kubische curve met nominale wind 10,5 m/s", new, wake, 10.5),
        "nominale_wind_12_5": ("Kubische curve met nominale wind 12,5 m/s", new, wake, 12.5),
    }
    known = {sid: key for key, (_, sid) in {**windbron.STATIONS, **EXTRA_STATIONS}.items()}
    for item in entry["bronvergelijking"]:
        if len(item["stations"]) == 1 and item["stations"][0] in known:
            key = known[item["stations"][0]]
            out[f"station_{key}"] = (f"Alleen station {item['naam']}, met eigen WINS50-maandfactor",
                                     windbron.ParkMethod((key,), factors=tuple(item["factor"])), wake, rated)
    return out


def common_days(results: dict[str, dict[date, dict]], measured: dict[date, float]) -> list[date]:
    """Vergelijkingsdagen: gemeten productie en volledige wind in elke variant. Hangt niet af van het verschil."""
    return sorted(d for d in measured if all(d in days and days[d]["model_mwh"] is not None for days in results.values()))


def summarise(days: dict[date, dict], measured: dict[date, float], selection: list[date] | None = None) -> dict:
    """Totalen en verschillen over de gekozen dagen (standaard: elke dag met volledige wind en gemeten productie)."""
    chosen = selection if selection is not None else [d for d, v in days.items() if v["model_mwh"] is not None and d in measured]
    pairs = [(d, days[d]["model_mwh"], measured[d]) for d in chosen if d in days]
    diff = [m - p for _, m, p in pairs]
    total_model, total_measured = sum(m for _, m, _ in pairs), sum(p for _, _, p in pairs)
    return {"dagen": len(pairs), "model_gwh": total_model / 1000, "gemeten_gwh": total_measured / 1000,
            "gemeten_gedeeld_door_model": total_measured / total_model if total_model else None,
            "gemiddeld_verschil_mwh": sum(diff) / len(diff), "rms_verschil_mwh": math.sqrt(sum(x * x for x in diff) / len(diff)),
            "dagen_model_lager": sum(x < 0 for x in diff), "dagen_model_hoger": sum(x > 0 for x in diff),
            "correlatie": correlation([m for _, m, _ in pairs], [p for _, _, p in pairs])}


def correlation(x: list[float], y: list[float]) -> float:
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    return sxy / math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))


def timezone_check(stations: dict[int, dict], pm: windbron.ParkMethod, measured: dict[date, float]) -> dict:
    """Welke dagindeling past bij de productie: Amsterdamse kalenderdag, UTC-dag of een dag verschoven.

    Dit controleert alleen de tijdas van de gegevens; er wordt niets op afgesteld.
    """
    wake, rated = PARKS["fryslan"]["wake_deficit"], FRYSLAN_SCENARIO["rated_speed"]
    energy = {}
    for year, values in stations.items():
        for t in sorted(set().union(*(series.keys() for series in values.values()))):
            v, _ = windbron.select(pm, {key: series.get(t) for key, series in values.items()})
            if v is not None:
                energy[t] = fryslan_power(v * windbron.factor("fryslan", pm, t), wake, rated, None) / 6
    out = {}
    for name, to_day in (("Europe/Amsterdam", lambda t: t.astimezone(LOCAL).date()),
                         ("UTC", lambda t: t.date()),
                         ("Europe/Amsterdam, dag later", lambda t: t.astimezone(LOCAL).date() + timedelta(days=1)),
                         ("Europe/Amsterdam, dag eerder", lambda t: t.astimezone(LOCAL).date() - timedelta(days=1))):
        sums, counts = {}, {}
        for t, e in energy.items():
            d = to_day(t)
            sums[d] = sums.get(d, 0.0) + e
            counts[d] = counts.get(d, 0) + 1
        days = [d for d in sums if d in measured and PERIOD[0] <= d <= PERIOD[1] and counts[d] >= 138]
        out[name] = round(correlation([sums[d] for d in days], [measured[d] for d in days]), 4)
    return out


def coverage(days: dict[date, dict], measured: dict[date, float]) -> dict:
    by_year = {}
    for d, v in days.items():
        item = by_year.setdefault(d.year, {"dagen": 0, "volledig": 0, "onvolledig": 0, "zonder_productie": 0,
                                           "productie_nul": 0, "klokwisseldagen": 0})
        item["dagen"] += 1
        item["volledig" if v["model_mwh"] is not None else "onvolledig"] += 1
        item["zonder_productie"] += d not in measured
        item["productie_nul"] += measured.get(d) == 0
        item["klokwisseldagen"] += v["intervallen"] != 144
    return by_year


def nl(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".").replace(".", ",") or "0"
    return str(value)


def compare(client: KNMIClient | None = None) -> dict:
    client = client or KNMIClient(ROOT / ".cache" / "knmi")
    table = windbron.table()
    options = variants(table)
    keys = sorted({k for _, pm, _, _ in options.values() for k in pm.stations} - {"houtribdijk_drift"})
    stations = {year: year_stations(client, keys, year) for year in range(PERIOD[0].year, PERIOD[1].year + 1)}
    # Gevoeligheid: Houtribdijk per jaar terugschalen naar zijn verhouding met Stavoren in de WINS50-jaren.
    drift = station_drift(client, range(DRIFT_REFERENCE[0], PERIOD[1].year + 1))
    reference = sum(drift[y]["Houtribdijk/Stavoren"] for y in range(DRIFT_REFERENCE[0], DRIFT_REFERENCE[1] + 1)) / 3
    for year, values in stations.items():
        correction = reference / drift[year]["Houtribdijk/Stavoren"]
        values["houtribdijk_drift"] = {t: v * correction for t, v in values["houtribdijk"].items()}
    measured = productie.load()
    curve = load_curve("fryslan")
    results = {name: variant_days(stations, pm, wake, rated, curve) for name, (_, pm, wake, rated) in options.items()}
    selection = common_days(results, measured)
    summary = {name: {"uitleg": options[name][0], "eigen_volledige_dagen": summarise(days, measured)["dagen"],
                      **summarise(days, measured, selection)} for name, days in results.items()}
    per_year = {name: {year: summarise(results[name], measured, [d for d in selection if d.year == year])
                       for year in range(PERIOD[0].year, PERIOD[1].year + 1)}
                for name in ("nieuw", "oud_dagprofiel", "oud_opsplitsing")}
    monthly = {name: {month: summarise(results[name], measured, [d for d in selection if d.month == month])
                      for month in range(1, 13)}
               for name in ("nieuw", "oud_dagprofiel", "oud_opsplitsing")}
    return {"periode": [PERIOD[0].isoformat(), PERIOD[1].isoformat()], "vergelijkingsdagen": len(selection),
            "dagen": results, "samenvatting": summary, "per_jaar": per_year, "per_maand": monthly,
            "selectie": [d.isoformat() for d in selection], "dekking": coverage(results["nieuw"], measured),
            "dagindeling_correlatie": timezone_check({y: {k: v for k, v in d.items() if k in options["nieuw"][1].stations}
                                                      for y, d in stations.items()}, options["nieuw"][1], measured),
            "stationsdrift": drift,
            "gemeten": measured, "bron_productie": productie.SOURCE,
            "methode": {"onafhankelijk": windbron.describe("fryslan", options["nieuw"][1], datetime(2024, 1, 15, tzinfo=LOCAL))}}


def write(result: dict, out: Path = OUT) -> None:
    out.mkdir(parents=True, exist_ok=True)
    measured = result["gemeten"]
    days = result["dagen"]
    with (out / "dagen.csv").open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["datum", "in_vergelijking", "intervallen", "intervallen_met_wind", "wind_ashoogte_gemiddeld_ms",
                         "model_mogelijk_mwh", "gemeten_productie_mwh", "verschil_model_min_gemeten_mwh", "model_lager_dan_gemeten",
                         "oud_dagprofiel_model_mwh", "oud_opsplitsing_model_mwh", "opmerking"])
        selection = set(result["selectie"])
        for d, v in days["nieuw"].items():
            m, p = v["model_mwh"], measured.get(d)
            difference = None if m is None or p is None else m - p
            note = ("onvolledige wind: niet vergeleken" if m is None else "gemeten productie 0" if p == 0
                    else "geen gemeten productie" if p is None
                    else "" if d.isoformat() in selection else "onvolledige wind in een andere variant")
            writer.writerow([d.isoformat(), "ja" if d.isoformat() in selection else "nee", v["intervallen"], v["met_wind"],
                             nl(v["wind_ashoogte_ms"]), nl(m), nl(p),
                             nl(difference), "" if difference is None else ("ja" if difference < 0 else "nee"),
                             nl(days["oud_dagprofiel"][d]["model_mwh"]), nl(days["oud_opsplitsing"][d]["model_mwh"]), note])
    with (out / "gevoeligheid.csv").open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file, delimiter=";")
        fields = ["dagen", "eigen_volledige_dagen", "model_gwh", "gemeten_gwh", "gemeten_gedeeld_door_model", "gemiddeld_verschil_mwh",
                  "rms_verschil_mwh", "dagen_model_lager", "dagen_model_hoger", "correlatie"]
        writer.writerow(["variant", "uitleg", *fields])
        for name, item in result["samenvatting"].items():
            writer.writerow([name, item["uitleg"], *(nl(item[f]) for f in fields)])
    slim = {k: v for k, v in result.items() if k not in ("dagen", "gemeten", "selectie")}
    (out / "samenvatting.json").write_text(json.dumps(slim, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def hydrogen(years: list[int], counts: list[int]) -> dict:
    """Waterstofuitkomsten van de opsplitsing met de nieuwe en de oude windmethode, zelfde aannames."""
    from .opsplitsing import TECHNOLOGIES, run
    out = {}
    for tech in ("pem", "alkaline_hoog"):
        a = TECHNOLOGIES[tech][1]
        for method in ("onafhankelijk", "productie_hoogste"):
            result = run(a, years, counts, "verdelen", method=method)
            best = min(result["rijen"], key=lambda r: r["lcoh_eur_kg"])
            out[f"{tech}|{method}"] = {
                "aanbod_mwh_per_jaar": sum(v["mwh"] for v in result["aanbod"].values()) / len(years),
                "rijen": [{k: r[k] for k in ("modules", "waterstof_t", "lcoh_eur_kg", "benutting", "productie_uur")}
                          for r in result["rijen"]],
                "goedkoopst": {"modules": best["modules"], "lcoh_eur_kg": best["lcoh_eur_kg"]}}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Vergelijk de modelopbrengst van Windpark Fryslân met de gemeten dagproductie.")
    parser.add_argument("--uit", type=Path, default=OUT)
    parser.add_argument("--waterstof", action="store_true", help="Reken ook de opsplitsing door met oude en nieuwe wind.")
    args = parser.parse_args()
    load_env_file(ROOT / ".env")
    try:
        result = compare()
        if args.waterstof:
            result["waterstof"] = hydrogen([2022, 2023, 2024, 2025], [1, 2, 3, 4, 6, 8])
    except KNMIError as exc:
        print(str(exc))
        return 1
    write(result, args.uit)
    for name, item in result["samenvatting"].items():
        print(f"{name:24} {item['dagen']:5} dagen  model {item['model_gwh']:7.1f} GWh  gemeten {item['gemeten_gwh']:7.1f} GWh  "
              f"gemeten/model {item['gemeten_gedeeld_door_model']:.3f}  RMS {item['rms_verschil_mwh']:6.0f} MWh  "
              f"model lager {item['dagen_model_lager']:4}  r {item['correlatie']:.3f}")
    print("Dagindeling (correlatie):", result["dagindeling_correlatie"])
    print(f"Uitvoer: {args.uit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
