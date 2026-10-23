"""Hoogtevertaling van KNMI-stationswind naar wind op ashoogte, afgeleid uit WINS50.

Productiegegevens worden hier niet gebruikt. Per park wordt bepaald:

1. Welke stationsbron het best de modelwind op de parklocatie volgt (`compare_sources`):
   uurwaarden 2019–2021 van losse stations en van gemiddelden van stations tegen WINS50 op
   ashoogte, met kruisvalidatie per jaar. De keuze (`CHOICE`) volgt een vooraf gestelde regel:
   alleen stations aan of in het IJsselmeer, hetzelfde wateroppervlak als Windpark Fryslân.
2. Een vertaalfactor F per kalendermaand: F = Σ v_ashoogte(WINS50, park) / Σ ff(bron), over
   dezelfde uren (`derive`). Zo is v_as = F × ff. F bevat de toename met de hoogte én het verschil
   tussen de stations en de parklocatie; `alpha_equivalent` toont F als exponent vanaf 10 m.

WINS50 is een modelheranalyse, geen meting op ashoogte. Zonder onafhankelijke meting op
ashoogte is F een onderbouwde aanname; `vergelijking.py` toont de gevoeligheid.

    python3 -m windprofiel.ashoogte   # schrijft data/ashoogte.json (KNMI_EDR_API_KEY of de cache)
"""

import argparse
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .application import PARKS, ROOT, load_curve, park_power_mw, parse_wind
from .knmi import KNMIClient, KNMIError, load_env_file
from . import wins50

TABLE = Path(__file__).parent / "data" / "ashoogte.json"
LOCAL = ZoneInfo("Europe/Amsterdam")
YEARS = (2019, 2020, 2021)
# Kandidaten binnen ongeveer 50 km van de parken, met hun ligging (KNMI-stationslijst en kaart).
STATIONS = {
    "0-20000-0-06258": ("Houtribdijk", "dijk midden in IJsselmeer en Markermeer: vrijwel alle richtingen open water"),
    "0-20000-0-06267": ("Stavoren", "Friese IJsselmeerkust: west en zuid water, oost land; 13 km van het park"),
    "0-20000-0-06242": ("Vlieland", "Vliehors, zandvlakte aan Noordzee en Waddenzee, aan de andere kant van de Afsluitdijk"),
    "0-20000-0-06229": ("Texelhors", "zuidpunt Texel aan Noordzee en Marsdiep"),
    "0-20000-0-06251": ("Hoorn Terschelling", "Waddeneiland, deels land"),
    "0-20000-0-06235": ("De Kooy", "vliegveld Den Helder, land"),
    "0-20000-0-06270": ("Leeuwarden", "vliegveld, Fries grasland"),
}
H, S, V = "0-20000-0-06258", "0-20000-0-06267", "0-20000-0-06242"
# Bronnen: één station, of het gemiddelde per tien minuten van meerdere (alle stations moeten meten).
SOURCES = {**{STATIONS[sid][0]: (sid,) for sid in STATIONS},
           "Houtribdijk + Stavoren": (H, S), "Houtribdijk + Vlieland": (H, V), "Houtribdijk + Stavoren + Vlieland": (H, S, V)}
# Regel vooraf: de stations op het IJsselmeer zelf. Hun gemiddelde volgt de parkwind in WINS50 beter
# dan elk station alleen; stations aan de Noordzee of Waddenzee vallen af, ook al verlagen ze de fout verder.
CHOICE = {"fryslan": "Houtribdijk + Stavoren", "beabuorren": "Houtribdijk + Stavoren"}
SITES = {"fryslan": "fryslan", "beabuorren": "beabuorren"}   # parknaam → WINS50-locatie


def level_wind(row: dict, site: str, height: float) -> float | None:
    """Wind op `height` m uit de WINS50-niveaus: exact niveau, of machtwet tussen de omliggende niveaus."""
    if height in wins50.LEVELS:
        return row[f"{site}_{int(height)}"]
    below = max(z for z in wins50.LEVELS if z < height)
    above = min(z for z in wins50.LEVELS if z > height)
    low, high = row[f"{site}_{below}"], row[f"{site}_{above}"]
    if not low or not high:
        return None
    return low * (height / below) ** (math.log(high / low) / math.log(above / below))


def station_series(client: KNMIClient, station: str, years=YEARS) -> dict[datetime, float]:
    """Tienminutenwind (ff) op intervalmidden in UTC; dezelfde aanvragen als het jaaraanbod."""
    out = {}
    for year in years:
        start = datetime(year, 1, 1, tzinfo=LOCAL).astimezone(timezone.utc)
        end = datetime(year + 1, 1, 1, tzinfo=LOCAL).astimezone(timezone.utc)
        out.update({t: v for t, v in parse_wind(client.observations_range(station, start, end), station) if v is not None})
    return out


def source_series(series: dict[str, dict[datetime, float]], stations: tuple[str, ...]) -> dict[datetime, float]:
    """Gemiddelde per tien minuten; alleen momenten waarop alle stations meten."""
    common = set.intersection(*(set(series[sid]) for sid in stations))
    return {t: sum(series[sid][t] for sid in stations) / len(stations) for t in common}


def around_hour(series: dict[datetime, float], hour: datetime) -> float | None:
    """Stationswind rond een heel uur: gemiddelde van de twee intervallen met midden 5 minuten ervoor en erna."""
    a, b = series.get(hour - timedelta(minutes=5)), series.get(hour + timedelta(minutes=5))
    return None if a is None or b is None else (a + b) / 2


def pairs(rows: list[dict], station: dict[datetime, float], site: str, height: float) -> list[tuple[datetime, float, float]]:
    out = []
    for row in rows:
        hour = datetime.fromisoformat(row["t"].replace("Z", "+00:00"))
        observed, modelled = around_hour(station, hour), level_wind(row, site, height)
        if observed is not None and modelled is not None:
            out.append((hour, observed, modelled))
    return out


def month_key(moment: datetime) -> int:
    return moment.astimezone(LOCAL).month


STRUCTURES = {
    "constant": lambda t: 0,
    "maand": month_key,
    "maand×dagdeel": lambda t: (month_key(t), t.astimezone(LOCAL).hour // 6),
}


def ratios(data, key) -> dict:
    num, den = defaultdict(float), defaultdict(float)
    for t, observed, modelled in data:
        num[key(t)] += modelled
        den[key(t)] += observed
    return {k: num[k] / den[k] for k in num if den[k] > 0}


def correlation(x: list[float], y: list[float]) -> float:
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    return sxy / math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))


def cross_validate(data, key, power) -> dict:
    """Per jaar weglaten: F uit de andere jaren, toets op het weggelaten jaar.

    `energie_relatief` vergelijkt het modelvermogen (turbinecurve zonder zog) uit F × ff met dat uit
    de WINS50-wind zelf: een vaste factor geeft minder spreiding dan de modelwind.
    """
    sq = n = total = bias = energy_model = energy_est = 0.0
    for year in YEARS:
        train = [x for x in data if x[0].year != year]
        test = [x for x in data if x[0].year == year]
        if not train or not test:
            continue
        table, overall = ratios(train, key), sum(x[2] for x in train) / sum(x[1] for x in train)
        for t, observed, modelled in test:
            estimate = table.get(key(t), overall) * observed
            sq += (estimate - modelled) ** 2
            bias += estimate - modelled
            total += modelled
            n += 1
            energy_model += power(modelled)
            energy_est += power(estimate)
    return {"uren": int(n), "rmse_relatief": round(math.sqrt(sq / n) / (total / n), 4), "bias_relatief": round(bias / total, 4),
            "energie_relatief": round(energy_est / energy_model - 1, 4)}


def month_table(data) -> list[float]:
    table = ratios(data, month_key)
    return [round(table[m], 4) for m in range(1, 13)]


def compare_sources(rows: list[dict], series: dict, park_id: str, height: float, power) -> list[dict]:
    """Elke kandidaat-bron tegen WINS50 op ashoogte bij het park, met eigen maandfactoren."""
    out = []
    for name, stations in SOURCES.items():
        data = pairs(rows, source_series(series, stations), SITES[park_id], height)
        out.append({"naam": name, "stations": list(stations), "ligging": [STATIONS[sid][1] for sid in stations],
                    "uren": len(data), "ff_gemiddeld": round(sum(x[1] for x in data) / len(data), 4),
                    "model_gemiddeld": round(sum(x[2] for x in data) / len(data), 4),
                    "correlatie": round(correlation([x[1] for x in data], [x[2] for x in data]), 4),
                    "factor": month_table(data),
                    "structuren": {k: cross_validate(data, key, power) for k, key in STRUCTURES.items()}})
    return out


def shear(rows: list[dict], site: str, height: float) -> list[float]:
    """Alleen de toename met de hoogte op de parklocatie: Σ v_as / Σ v_10 in WINS50, per maand."""
    num, den = defaultdict(float), defaultdict(float)
    for row in rows:
        top, bottom = level_wind(row, site, height), row[f"{site}_10"]
        if top is not None and bottom is not None:
            month = month_key(datetime.fromisoformat(row["t"].replace("Z", "+00:00")))
            num[month] += top
            den[month] += bottom
    return [round(num[m] / den[m], 4) for m in range(1, 13)]


def derive(rows: list[dict], source: dict[datetime, float], park_id: str, height: float) -> dict:
    """Maandfactoren F met de spreiding tussen de jaren."""
    data = pairs(rows, source, SITES[park_id], height)
    factors = month_table(data)
    per_year = {year: ratios([x for x in data if x[0].year == year], month_key) for year in YEARS}
    counts = defaultdict(int)
    for t, _, _ in data:
        counts[month_key(t)] += 1
    return {"hoogte_m": height, "factor": factors,
            "alpha_equivalent": [round(math.log(f) / math.log(height / 10), 4) for f in factors],
            "factor_per_jaar": {str(y): [None if per_year[y].get(m) is None else round(per_year[y][m], 4) for m in range(1, 13)]
                                for y in YEARS},
            "uren_per_maand": [counts[m] for m in range(1, 13)],
            "factor_jaar": round(sum(x[2] for x in data) / sum(x[1] for x in data), 4)}


def build(choice: dict[str, str] = CHOICE, out: Path = TABLE) -> dict:
    client = KNMIClient(ROOT / ".cache" / "knmi")
    rows = wins50.load_series()
    series = {sid: station_series(client, sid) for sid in STATIONS}
    result = {"bron": "KNMI WINS50 (HARMONIE-AROME Cy43, 2,5 km, run zonder windparken), EDR-collectie wins50, "
                      "uurwaarden; KNMI 10-minute-in-situ-meteorological-observations (ff, representatief voor 10 m)",
              "wins50_sha256": hashlib.sha256(wins50.SERIES.read_bytes()).hexdigest(),
              "periode": [rows[0]["t"], rows[-1]["t"]], "uren": len(rows), "locaties": wins50.SITES,
              "regel": "Stations op het IJsselmeer; gemiddelde per tien minuten, alleen als alle stations meten.",
              "parken": {}}
    for park_id, name in choice.items():
        height = PARKS[park_id]["hub_height"]
        curve = None if park_id == "fryslan" else load_curve(park_id)
        power = lambda v, p=park_id, c=curve: park_power_mw(v, p, c, wake=False)
        stations = SOURCES[name]
        source = source_series(series, stations)
        entry = {"bron": name, "stations": list(stations), "regel": "gemiddelde" if len(stations) > 1 else "een",
                 **derive(rows, source, park_id, height), "schering": shear(rows, SITES[park_id], height)}
        # Gevoeligheid: andere ashoogte (alleen Fryslân heeft een tweede gepubliceerde waarde).
        if park_id == "fryslan":
            entry["alternatieven"] = {"ashoogte_109_m": derive(rows, source, park_id, 109.0)["factor"]}
        entry["bronvergelijking"] = compare_sources(rows, series, park_id, height, power)
        result["parken"][park_id] = entry
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Leid de hoogtevertaling af uit WINS50 en KNMI-stations (2019–2021).")
    parser.parse_args()
    load_env_file(ROOT / ".env")
    try:
        result = build()
    except KNMIError as exc:
        print(str(exc))
        return 1
    for park_id, entry in result["parken"].items():
        print(f"{park_id}: {entry['bron']}, F per maand {entry['factor']}")
        for item in entry["bronvergelijking"]:
            s = item["structuren"]["maand"]
            print(f"  {item['naam']:34} r={item['correlatie']:.3f}  rmse {s['rmse_relatief']:.3f}  energie {s['energie_relatief']:+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
