"""HARMONIE-AROME (KNMI Open Data) als windbron voor Windpark Fryslân.

Dataset `harmonie_arome_cy43_p1`: elke uurlijkse run is een tar met per
voorspellingsuur een GRIB1-bestand. Met HTTP-range-verzoeken wordt alleen het
benodigde GRIB-bestand gelezen; daarvan worden u en v op 10, 100 en 200 m gedecodeerd
voor de roosterpunten in het parkgebied. Alleen die kleine uitsnede wordt gecachet.
"""

import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from math import hypot, isfinite
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, build_opener

from .knmi import KNMIError, NoRedirects

DATASET = "harmonie_arome_cy43_p1"
FILES_URL = f"https://api.dataplatform.knmi.nl/open-data/v1/datasets/{DATASET}/versions/1.0/files"
FIRST_RUN = datetime(2026, 1, 7, tzinfo=timezone.utc)
# Parkgebied Windpark Fryslân rond 53,03 N 5,27 E (circa 9 x 8 km), aanname.
PARK_BOX = {"lat": (52.995, 53.065), "lon": (5.20, 5.34)}
HUB_HEIGHT = 115
LEVELS = (10, 100, 200)
U, V, HEIGHT_LEVEL = 33, 34, 105


class GribError(ValueError):
    pass


def _signed(raw: bytes) -> int:
    """GRIB1 gebruikt teken-en-grootte: hoogste bit is het teken."""
    value = int.from_bytes(raw, "big")
    sign_bit = 1 << (8 * len(raw) - 1)
    return -(value - sign_bit) if value & sign_bit else value


def _ibm_float(raw: bytes) -> float:
    value = int.from_bytes(raw, "big")
    sign = -1 if value >> 31 else 1
    exponent = (value >> 24) & 0x7F
    return sign * (value & 0xFFFFFF) / 16**6 * 16.0 ** (exponent - 64)


def grib_messages(data: bytes):
    """Doorloop GRIB1-berichten; geeft (pds, gds, bds, bitmap aanwezig) per bericht."""
    offset = 0
    while offset < len(data):
        if data[offset:offset + 4] != b"GRIB" or data[offset + 7] != 1:
            raise GribError("Geen GRIB1-bericht op verwachte positie.")
        length = int.from_bytes(data[offset + 4:offset + 7], "big")
        message = data[offset:offset + length]
        if len(message) != length or message[-4:] != b"7777":
            raise GribError("Afgebroken GRIB1-bericht.")
        position = 8
        pds = message[position:position + int.from_bytes(message[position:position + 3], "big")]
        position += len(pds)
        gds = b""
        if pds[7] & 0x80:
            gds = message[position:position + int.from_bytes(message[position:position + 3], "big")]
            position += len(gds)
        has_bitmap = bool(pds[7] & 0x40)
        if has_bitmap:
            position += int.from_bytes(message[position:position + 3], "big")
        bds = message[position:position + int.from_bytes(message[position:position + 3], "big")]
        yield pds, gds, bds, has_bitmap
        offset += length


def parse_grid(gds: bytes) -> dict:
    if len(gds) < 28 or gds[5] != 0:
        raise GribError("Alleen een regelmatig lat/lon-rooster wordt ondersteund.")
    grid = {"ni": int.from_bytes(gds[6:8], "big"), "nj": int.from_bytes(gds[8:10], "big"),
            "la1": _signed(gds[10:13]) / 1000, "lo1": _signed(gds[13:16]) / 1000,
            "di": int.from_bytes(gds[23:25], "big") / 1000, "dj": int.from_bytes(gds[25:27], "big") / 1000,
            "scan": gds[27]}
    if grid["scan"] != 64:
        raise GribError("Verwacht scanmodus 64 (west→oost, zuid→noord).")
    return grid


def box_indices(grid: dict, box: dict = PARK_BOX) -> list[tuple[int, float, float]]:
    """Roosterpunten (index, lat, lon) binnen het parkgebied."""
    points = []
    for j in range(grid["nj"]):
        lat = grid["la1"] + j * grid["dj"]
        if not box["lat"][0] <= lat <= box["lat"][1]:
            continue
        for i in range(grid["ni"]):
            lon = grid["lo1"] + i * grid["di"]
            if box["lon"][0] <= lon <= box["lon"][1]:
                points.append((j * grid["ni"] + i, round(lat, 4), round(lon, 4)))
    if not points:
        raise GribError("Parkgebied valt buiten het rooster.")
    return points


def unpack_points(bds: bytes, decimal_scale: int, indices: list[int]) -> list[float]:
    """Decodeer alleen de gevraagde punten uit een simple-packed rasterveld."""
    if bds[3] & 0xF0:
        raise GribError("Alleen simple packing van rasterpunten wordt ondersteund.")
    binary_scale = _signed(bds[4:6])
    reference = _ibm_float(bds[6:10])
    bits = bds[10]
    values = []
    for index in indices:
        if bits == 0:
            packed = 0
        else:
            start = index * bits
            first = 11 + start // 8
            chunk = int.from_bytes(bds[first:first + (start % 8 + bits + 7) // 8], "big")
            total = ((start % 8 + bits + 7) // 8) * 8
            packed = (chunk >> (total - start % 8 - bits)) & ((1 << bits) - 1)
        values.append((reference + packed * 2.0**binary_scale) / 10**decimal_scale)
    return values


def extract_wind(data: bytes, levels=LEVELS, box: dict = PARK_BOX) -> dict:
    """Parkgemiddelde windsnelheid per hoogte uit één GRIB1-bestand.

    Snelheid wordt per roosterpunt uit u en v berekend en daarna gemiddeld.
    Velden met een bitmap worden overgeslagen.
    """
    fields, valid, grid_points = {}, None, None
    for pds, gds, bds, has_bitmap in grib_messages(data):
        parameter, level_type, level = pds[8], pds[9], int.from_bytes(pds[10:12], "big")
        if has_bitmap or parameter not in (U, V) or level_type != HEIGHT_LEVEL or level not in levels:
            continue
        if pds[17] != 1:
            raise GribError("Voorspellingstermijn is niet in uren.")
        reference = datetime(100 * (pds[24] - 1) + pds[12], pds[13], pds[14], pds[15], pds[16], tzinfo=timezone.utc)
        moment = reference + timedelta(hours=pds[18])
        if valid not in (None, moment):
            raise GribError("Velden in één bestand hebben verschillende geldigheidstijden.")
        valid = moment
        grid = parse_grid(gds)
        if grid_points is None:
            grid_points = box_indices(grid, box)
        fields[(parameter, level)] = unpack_points(bds, _signed(pds[26:28]), [p[0] for p in grid_points])
    speeds = {}
    for level in levels:
        if (U, level) not in fields or (V, level) not in fields:
            raise GribError(f"u of v op {level} m ontbreekt.")
        point_speeds = [hypot(u, v) for u, v in zip(fields[(U, level)], fields[(V, level)])]
        if not all(isfinite(s) for s in point_speeds):
            raise GribError("Niet-eindige windwaarde.")
        speeds[level] = sum(point_speeds) / len(point_speeds)
    return {"valid": valid.isoformat(), "points": len(grid_points), "speed_ms": speeds}


def hub_speed(speeds: dict, height: float = HUB_HEIGHT) -> float:
    """Lineaire interpolatie tussen 100 en 200 m; sleutels mogen tekst zijn (JSON)."""
    speeds = {int(k): v for k, v in speeds.items()}
    low, high = speeds[100], speeds[200]
    return low + (high - low) * (height - 100) / 100


def shear_factor(speeds: dict, height: float = HUB_HEIGHT) -> float:
    """Verhouding wind op ashoogte / wind op 10 m in HARMONIE boven het park."""
    return hub_speed(speeds, height) / {int(k): v for k, v in speeds.items()}[10]


def member_name(run: datetime, lead: int) -> str:
    return f"HA43_N20_{run:%Y%m%d%H}00_{lead:03d}00_GB"


def tar_name(run: datetime) -> str:
    return f"HARM43_V1_P1_{run:%Y%m%d%H}.tar"


class HarmonieClient:
    """Open Data API-client; de sleutel gaat alleen naar de KNMI-API-host."""

    def __init__(self, cache_dir: Path | None = None):
        self.key = os.environ.get("KNMI_OPEN_DATA_API_KEY", "").strip()
        if not self.key:
            raise KNMIError("KNMI_OPEN_DATA_API_KEY ontbreekt.")
        self.cache_dir = cache_dir
        self.opener = build_opener(NoRedirects())

    def _open(self, request: Request, timeout: int = 60) -> bytes:
        for attempt in range(3):
            try:
                with self.opener.open(request, timeout=timeout) as response:
                    return response.read()
            except HTTPError as exc:
                if exc.code == 404:
                    raise KNMIError("HARMONIE-bestand niet gevonden.") from None
                if exc.code in (401, 403):
                    raise KNMIError("KNMI Open Data weigert de sleutel of het bestand.") from None
                if attempt == 2:
                    raise KNMIError(f"KNMI Open Data geeft HTTP {exc.code}.") from None
            except (URLError, TimeoutError):
                if attempt == 2:
                    raise KNMIError("KNMI Open Data is niet bereikbaar.") from None
        raise AssertionError

    def download_url(self, run: datetime) -> str:
        request = Request(f"{FILES_URL}/{quote(tar_name(run))}/url",
                          headers={"Authorization": self.key, "Accept": "application/json"})
        url = json.loads(self._open(request))["temporaryDownloadUrl"]
        if urlsplit(url).scheme != "https":
            raise KNMIError("Onverwachte download-URL.")
        return url

    def _range(self, url: str, start: int, end: int) -> bytes:
        # Vooraf ondertekende S3-URL: geen Authorization-header meesturen.
        return self._open(Request(url, headers={"Range": f"bytes={start}-{end}"}))

    def read_member(self, run: datetime, lead: int) -> bytes:
        """Zoek het GRIB-bestand in de tar via headers en lees alleen dat bestand."""
        url, wanted, offset = self.download_url(run), member_name(run, lead), 0
        for _ in range(200):
            header = self._range(url, offset, offset + 1535)
            if len(header) < 512 or not header[:512].strip(b"\0"):
                break
            kind, size = header[156:157], int(header[124:136].strip(b"\0 ") or b"0", 8)
            if kind == b"x":
                # PAX-uitbreidingsheader; het eigenlijke bestand volgt daarna.
                offset += 512 + (size + 511) // 512 * 512
                header = header[512 + (size + 511) // 512 * 512:]
                if len(header) < 512:
                    header = self._range(url, offset, offset + 511)
                kind, size = header[156:157], int(header[124:136].strip(b"\0 ") or b"0", 8)
            name = header[:100].rstrip(b"\0").decode(errors="replace").removeprefix("./")
            if name == wanted:
                data = self._range(url, offset + 512, offset + 511 + size)
                if len(data) != size:
                    raise KNMIError("Onvolledige HARMONIE-download.")
                return data
            offset += 512 + (size + 511) // 512 * 512
        raise KNMIError(f"{wanted} niet gevonden in {tar_name(run)}.")

    def park_wind(self, run: datetime, lead: int) -> dict:
        cache = None
        if self.cache_dir is not None:
            cache = self.cache_dir / f"{run:%Y%m%d%H}_{lead:02d}.json"
            if cache.exists():
                cached = json.loads(cache.read_text())
                if all(str(level) in cached["speed_ms"] for level in LEVELS):
                    return cached
        result = extract_wind(self.read_member(run, lead))
        result.update(run=run.isoformat(), lead=lead)
        if result["valid"] != (run + timedelta(hours=lead)).isoformat():
            raise KNMIError("Geldigheidstijd in GRIB past niet bij run en termijn.")
        if cache is not None:
            cache.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile("w", dir=cache.parent, delete=False) as file:
                json.dump(result, file)
            Path(file.name).replace(cache)
        return result

    def hourly_series(self, start: datetime, hours: int, lead: int = 1, workers: int = 6) -> list[dict | None]:
        """Wind per heel uur uit opeenvolgende runs, steeds met dezelfde korte termijn.

        Ontbreekt een run, dan volgt een eerdere run met een termijn tot drie uur langer.
        """
        def fetch(valid: datetime) -> dict | None:
            for extra in range(4):
                run = valid - timedelta(hours=lead + extra)
                if run < FIRST_RUN:
                    break
                try:
                    return self.park_wind(run, lead + extra)
                except (KNMIError, GribError):
                    continue
            return None
        moments = [start + timedelta(hours=h) for h in range(hours)]
        with ThreadPoolExecutor(workers) as pool:
            return list(pool.map(fetch, moments))


def local_day_hours(day: date) -> tuple[datetime, int]:
    from zoneinfo import ZoneInfo
    local = ZoneInfo("Europe/Amsterdam")
    start = datetime.combine(day, datetime.min.time(), local).astimezone(timezone.utc)
    end = datetime.combine(day + timedelta(days=1), datetime.min.time(), local).astimezone(timezone.utc)
    return start, int((end - start).total_seconds() // 3600)
