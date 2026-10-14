import copy
import unittest
from datetime import datetime, timedelta, timezone

from windprofiel.application import interpolate_minutes, parse_wind, validate_curve
from windprofiel.knmi import KNMIError


def payload(values):
    return {"type": "CoverageCollection", "coverages": [{
        "eumetnet:locationId": "station",
        "domain": {"domainType": "PointSeries", "axes": {"t": {"values": [
            "2025-01-01T00:00:00Z", "2025-01-01T00:10:00Z", "2025-01-01T00:20:00Z"]}}},
        "ranges": {"ff": {"axisNames": ["t", "y", "x"], "shape": [3, 1, 1], "values": values}},
    }], "parameters": {"ff": {"unit": {"symbol": {"value": "m/s"}},
                                "measurementType": {"method": "mean", "duration": "-PT10M"}}}}


class ApplicationTests(unittest.TestCase):
    def test_interval_midpoint_and_wind_interpolation(self):
        observations = parse_wind(payload([2, 4, 8]), "station")
        minute = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(observations[0][0], minute-timedelta(minutes=5))
        self.assertEqual(interpolate_minutes(observations, [minute, minute+timedelta(minutes=10)]), [3, 6])

    def test_missing_values_and_gaps_not_filled(self):
        observations = parse_wind(payload([2, None, 8]), "station")
        minute = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(interpolate_minutes(observations, [minute, minute+timedelta(minutes=10)]), [None, None])
        self.assertEqual(interpolate_minutes([observations[0], observations[2]], [minute]), [None])
        self.assertEqual(interpolate_minutes(observations, [minute-timedelta(hours=1)]), [None])

    def test_units_station_and_shape_rejected(self):
        original = payload([2, 4, 8])
        with self.assertRaises(KNMIError): parse_wind(original, "different-station")
        bad = copy.deepcopy(original);bad["parameters"]["ff"]["unit"]["symbol"]["value"]="knots"
        with self.assertRaises(KNMIError): parse_wind(bad, "station")
        bad = copy.deepcopy(original);bad["coverages"][0]["ranges"]["ff"]["shape"]=[3, 2, 1]
        with self.assertRaises(KNMIError): parse_wind(bad, "station")

    def test_invalid_wind_is_missing(self):
        values = parse_wind(payload([-1, float("nan"), 3]), "station")
        self.assertEqual([value for _, value in values], [None, None, 3])

    def test_wrong_curve_model_or_units_rejected(self):
        # Alleen een synthetische testcurve voor validatie, geen productiedata.
        curve = {"model": "Siemens SWT-1.3-62", "source": "https://example.org/curve",
                 "cut_out": 25, "points": [[3, 0], [14, 1300]]}
        self.assertEqual(validate_curve(curve, "beabuorren")["cut_out"], 25)
        with self.assertRaises(ValueError): validate_curve(curve, "fryslan")
        curve["points"][-1][1] = 1_300_000
        with self.assertRaises(ValueError): validate_curve(curve, "beabuorren")
        with self.assertRaises(ValueError): validate_curve([], "beabuorren")
