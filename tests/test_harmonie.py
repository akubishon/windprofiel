import io
import tarfile
import unittest
from datetime import datetime, timedelta, timezone

from windprofiel.compare import harmonie_minutes, hourly_minutes, station_mean
from windprofiel.harmonie import (GribError, HarmonieClient, extract_wind, hub_speed, local_day_hours,
                                  member_name, shear_factor)


def ibm(value: float) -> bytes:
    """Positieve IBM-float; voldoende voor synthetische testvelden."""
    if value == 0:
        return bytes(4)
    exponent = 64
    while value >= 1:
        value /= 16
        exponent += 1
    while value < 1 / 16:
        value *= 16
        exponent -= 1
    return bytes([exponent]) + int(value * 16**6).to_bytes(3, "big")


def signed(value: int, size: int) -> bytes:
    return ((1 << (8 * size - 1)) | -value if value < 0 else value).to_bytes(size, "big")


def message(parameter: int, level: int, values: list[int], *, bitmap: bool = False, lead: int = 1,
            ni: int = 3, nj: int = 2, la1: float = 53.0, lo1: float = 5.2) -> bytes:
    """Synthetisch GRIB1-bericht: waarde = 1 + x × 2^-1 met 8 bits per punt."""
    pds = bytearray(28)
    pds[0:3] = (28).to_bytes(3, "big")
    pds[7] = 0x80 | (0x40 if bitmap else 0)
    pds[8], pds[9] = parameter, 105
    pds[10:12] = level.to_bytes(2, "big")
    pds[12:17] = bytes([26, 1, 8, 0, 0])
    pds[17], pds[18], pds[24] = 1, lead, 21
    gds = bytearray(32)
    gds[0:3] = (32).to_bytes(3, "big")
    gds[6:8], gds[8:10] = ni.to_bytes(2, "big"), nj.to_bytes(2, "big")
    gds[10:13], gds[13:16] = signed(round(la1 * 1000), 3), signed(round(lo1 * 1000), 3)
    gds[23:25], gds[25:27], gds[27] = (29).to_bytes(2, "big"), (18).to_bytes(2, "big"), 64
    bms = (6 + ni * nj // 8 + 1).to_bytes(3, "big") + bytes(3 + ni * nj // 8 + 1) if bitmap else b""
    bds = bytearray(11) + bytes(values)
    bds[0:3] = len(bds).to_bytes(3, "big")
    bds[4:6], bds[6:10], bds[10] = signed(-1, 2), ibm(1.0), 8
    body = bytes(pds) + bytes(gds) + bms + bytes(bds)
    return b"GRIB" + (8 + len(body) + 4).to_bytes(3, "big") + b"\x01" + body + b"7777"


BOX = {"lat": (52.99, 53.01), "lon": (5.19, 5.27)}  # zuidelijke rij, eerste drie kolommen


def wind_file(lead: int = 1) -> bytes:
    data = b""
    # Velden op 50 m en met bitmap moeten genegeerd worden.
    data += message(33, 50, [200] * 6, lead=lead)
    data += message(33, 100, [99] * 6, bitmap=True, lead=lead)
    for level, u, v in ((10, 3, 4), (100, 4, 6), (200, 6, 8)):
        # u = 1 + x/2: x = 2u − 2 op de zuidelijke rij, noordelijke rij afwijkend.
        data += message(33, level, [2 * u - 2] * 3 + [0] * 3, lead=lead)
        data += message(34, level, [2 * v - 2] * 3 + [0] * 3, lead=lead)
    return data


class GribTests(unittest.TestCase):
    def test_extract_park_mean_speed(self):
        result = extract_wind(wind_file(), box=BOX)
        self.assertEqual(result["points"], 3)
        self.assertEqual(result["valid"], "2026-01-08T01:00:00+00:00")
        self.assertAlmostEqual(result["speed_ms"][100], 7.2111, places=3)  # √(4²+6²)
        self.assertAlmostEqual(result["speed_ms"][200], 10.0)
        self.assertAlmostEqual(result["speed_ms"][10], 5.0)

    def test_hub_interpolation_accepts_json_keys(self):
        self.assertAlmostEqual(hub_speed({"100": 8.0, "200": 10.0}), 8.3)
        self.assertAlmostEqual(hub_speed({100: 8.0, 200: 10.0}, height=150), 9.0)

    def test_missing_component_and_corruption(self):
        with self.assertRaises(GribError):
            extract_wind(message(33, 100, [1] * 6) + message(33, 200, [1] * 6), box=BOX)
        with self.assertRaises(GribError):
            extract_wind(wind_file()[:-10], box=BOX)
        with self.assertRaises(GribError):
            extract_wind(wind_file(), box={"lat": (60, 61), "lon": (0, 1)})


class FakeClient(HarmonieClient):
    def __init__(self, tar_bytes: bytes):
        self.tar, self.cache_dir, self.requests = tar_bytes, None, 0

    def download_url(self, run):
        return "https://example.invalid/run.tar"

    def _range(self, url, start, end):
        self.requests += 1
        return self.tar[start:end + 1]


class TarTests(unittest.TestCase):
    def test_reads_only_the_wanted_member(self):
        run = datetime(2026, 1, 8, tzinfo=timezone.utc)
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
            for lead in (0, 6, 1):
                content = wind_file(lead)
                info = tarfile.TarInfo("./" + member_name(run, lead))
                info.size, info.pax_headers = len(content), {"mtime": "1767839487.12"}
                tar.addfile(info, io.BytesIO(content))
        client = FakeClient(buffer.getvalue())
        self.assertEqual(client.read_member(run, 1), wind_file(1))
        self.assertEqual(client.requests, 4)  # drie headers en één bestand


class SeriesTests(unittest.TestCase):
    def test_local_day_and_interpolation_without_gaps(self):
        start, hours = local_day_hours(datetime(2026, 10, 25).date())
        self.assertEqual((start.hour, hours), (22, 25))
        t0 = datetime(2026, 1, 8, tzinfo=timezone.utc)
        samples = [{"valid": (t0 + timedelta(hours=h)).isoformat(), "speed_ms": {"100": s, "200": s}}
                   for h, s in ((0, 6.0), (1, 9.0))] + [None]
        moments = [t0 + timedelta(minutes=m) for m in (0, 20, 60, 61)]
        self.assertEqual(harmonie_minutes(samples, moments), [6.0, 7.0, 9.0, None])
        self.assertEqual(hourly_minutes([(t0, 1.0), (t0 + timedelta(hours=1), None)], moments[:2]), [1.0, None])

    def test_shear_factor_and_station_hour_mean(self):
        self.assertAlmostEqual(shear_factor({"10": 5.0, "100": 8.0, "200": 10.0}), 8.3 / 5)
        t0 = datetime(2026, 1, 8, 12, tzinfo=timezone.utc)
        observations = [(t0 + timedelta(minutes=m), v) for m, v in
                        ((-35, 50.0), (-25, 4.0), (-15, None), (-5, 6.0), (5, 8.0), (35, 50.0))]
        self.assertAlmostEqual(station_mean(observations, t0), 6.0)
        self.assertIsNone(station_mean(observations[:3], t0))


if __name__ == "__main__":
    unittest.main()
