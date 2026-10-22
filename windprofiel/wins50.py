"""WINS50: HARMONIE-AROME-wind op meerdere hoogtes bij de parken en stations, 2019–2021.

WINS50 is een heranalyse van KNMI met HARMONIE-AROME Cy43 (2,5 km, genest in ERA5), uur-
waarden op 17 hoogtes boven het oppervlak (10 tot 600 m). De KNMI EDR-collectie `wins50`
hoort bij de run zonder windparken (`wins50_ctl_nl_daily_3d`): de ongestoorde wind, zonder
zog van bestaande parken. Het is een modelreeks, geen meting en geen productiegegeven.

Gebruik: de verhouding tussen wind op ashoogte en op 10 m op de parklocatie, en de
vergelijking van KNMI-stations met de modelwind op de parklocatie (`ashoogte.py`). De
periode overlapt niet met de opgeslagen productie (2022–2025); dat is hier ook niet nodig.

    python3 -m windprofiel.wins50   # haalt 2019–2021 op (één aanvraag per dag) en schrijft data/wins50_punten.csv.gz

De EDR-cube staat per aanvraag hoogstens 100 hoogte × uur-waarden toe; vier hoogtes × 24 uur
past, dus één aanvraag per dag. Antwoorden komen in `.cache/wins50/`.
"""

import argparse
import csv
import gzip
import io
import json
import math
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from .knmi import KNMIError, NoRedirects, load_env_file

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://api.dataplatform.knmi.nl/edr/v1/collections/wins50/cube"
CACHE = ROOT / ".cache" / "wins50"
SERIES = Path(__file__).parent / "data" / "wins50_punten.csv.gz"
FIRST, LAST = date(2019, 1, 1), date(2021, 12, 31)
LEVELS = (10, 60, 100, 120)      # m boven het oppervlak; 60 m is Beabuorren, 100–120 m omsluit 115 m
BBOX = (5.15, 52.62, 5.55, 53.08)  # lon/lat: park, Beabuorren, Stavoren en Houtribdijk
# Locaties. Het park is een gebied: alle roosterpunten binnen `radius_km` van het geschatte
# midden tellen gelijk mee. Stations en Beabuorren krijgen het dichtstbijzijnde roosterpunt.
SITES = {
    # Planbeschrijving: aan de Afsluitdijk tussen Breezanddijk en Kornwerderzand, circa 6,5 km uit
    # de Friese kust en 7,7 km het IJsselmeer in; Wikipedia: 53°00′N 5°16′E. Onzekerheid enkele km.
    "fryslan": {"latitude": 53.010, "longitude": 5.290, "radius_km": 4.0},
    "beabuorren": {"latitude": 53.052, "longitude": 5.493, "radius_km": 0.0},
    "houtribdijk": {"latitude": 52.6481, "longitude": 5.4006, "radius_km": 0.0},
    "stavoren": {"latitude": 52.8967, "longitude": 5.3833, "radius_km": 0.0},
}


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def grid_points(xs: list[float], ys: list[float]) -> dict[str, list[tuple[int, int]]]:
    """Roosterindexen (y, x) per locatie: binnen de straal, of anders het dichtstbijzijnde punt."""
    out = {}
    for name, site in SITES.items():
        cells = [(distance_km(site["latitude"], site["longitude"], y, x), j, i) for j, y in enumerate(ys) for i, x in enumerate(xs)]
        inside = [(j, i) for d, j, i in cells if d <= site["radius_km"]]
        out[name] = inside or [min(cells)[1:]]
    return out


def parse_day(payload: dict) -> list[dict]:
    """Uurwaarden per locatie en hoogte uit één CoverageJSON-dag; ontbrekende waarden blijven None."""
    try:
        axes = payload["domain"]["axes"]
        xs, ys, zs, ts = (axes[k]["values"] for k in ("x", "y", "z", "t"))
        wind = payload["ranges"]["wspeed"]
        if wind["axisNames"] != ["t", "z", "y", "x"] or wind["shape"] != [len(ts), len(zs), len(ys), len(xs)]:
            raise ValueError("vorm")
        if [round(z) for z in zs] != list(LEVELS):
            raise ValueError("hoogtes")
        values = wind["values"]
    except (KeyError, TypeError, ValueError):
        raise KNMIError("Onverwachte structuur van het WINS50-antwoord.") from None
    points = grid_points(xs, ys)
    rows = []
    for t, stamp in enumerate(ts):
        row = {"t": stamp}
        for name, cells in points.items():
            for k, level in enumerate(LEVELS):
                found = []
                for j, i in cells:
                    v = values[((t * len(zs) + k) * len(ys) + j) * len(xs) + i]
                    if isinstance(v, (int, float)) and math.isfinite(v) and v >= 0:
                        found.append(v)
                row[f"{name}_{level}"] = sum(found) / len(found) if len(found) == len(cells) else None
        rows.append(row)
    return rows


class WINS50Client:
    def __init__(self, cache_dir: Path = CACHE):
        self.key = os.environ.get("KNMI_EDR_API_KEY", "").strip()
        if not self.key:
            raise KNMIError("KNMI_EDR_API_KEY ontbreekt.")
        self.cache_dir = cache_dir
        self.opener = build_opener(NoRedirects())

    def day(self, day: date) -> dict:
        cache = self.cache_dir / f"{day.isoformat()}.json"
        if cache.exists():
            return json.loads(cache.read_text())
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        query = {"bbox": ",".join(map(str, BBOX)), "parameter-name": "wspeed", "z": ",".join(map(str, LEVELS)),
                 "datetime": f"{start:%Y-%m-%dT%H:%M:%SZ}/{start + timedelta(hours=23):%Y-%m-%dT%H:%M:%SZ}",
                 "f": "CoverageJSON"}
        request = Request(BASE_URL + "?" + urlencode(query), headers={"Authorization": self.key, "Accept": "application/json"})
        for attempt in range(4):
            try:
                with self.opener.open(request, timeout=120) as response:
                    data = json.load(response)
                break
            except HTTPError as exc:
                if exc.code not in (429, 500, 502, 503, 504) or attempt == 3:
                    raise KNMIError(f"WINS50: KNMI geeft HTTP {exc.code}.") from None
            except (URLError, TimeoutError):
                if attempt == 3:
                    raise KNMIError("WINS50: KNMI is niet bereikbaar.") from None
            time.sleep(2 ** (attempt + 1))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=self.cache_dir, delete=False, encoding="utf-8") as file:
            json.dump(data, file)
        Path(file.name).replace(cache)
        return data


COLUMNS = ["t"] + [f"{name}_{level}" for name in SITES for level in LEVELS]


def build_series(first: date = FIRST, last: date = LAST, workers: int = 4, path: Path = SERIES) -> int:
    client = WINS50Client()
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    with ThreadPoolExecutor(workers) as pool:
        # Direct per dag uitlezen: de volledige antwoorden samen passen slecht in het geheugen.
        rows = [row for day_rows in pool.map(lambda day: parse_day(client.day(day)), days) for row in day_rows]
    text = io.StringIO()
    writer = csv.writer(text, lineterminator="\n")
    writer.writerow(COLUMNS)
    for row in rows:
        writer.writerow([row["t"]] + ["" if row[c] is None else f"{row[c]:.3f}" for c in COLUMNS[1:]])
    path.parent.mkdir(parents=True, exist_ok=True)
    # Vaste mtime: hetzelfde resultaat geeft hetzelfde bestand.
    with gzip.GzipFile(path, "wb", mtime=0) as file:
        file.write(text.getvalue().encode())
    return len(rows)


def load_series(path: Path = SERIES) -> list[dict]:
    """Uurreeks per locatie en hoogte (m/s); lege waarden worden None."""
    with gzip.open(path, "rt", encoding="utf-8") as file:
        return [{key: (value if key == "t" else float(value) if value else None) for key, value in row.items()}
                for row in csv.DictReader(file)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Haal WINS50-wind op 10, 60, 100 en 120 m op bij park en stations.")
    parser.add_argument("--processen", type=int, default=4)
    args = parser.parse_args()
    load_env_file(ROOT / ".env")
    try:
        count = build_series(workers=args.processen)
    except KNMIError as exc:
        print(str(exc))
        return 1
    print(f"{SERIES}: {count} uren")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
