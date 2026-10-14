import json
import os
import tempfile
import unittest
from datetime import date
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

from windprofiel.knmi import BASE_URL, KNMIClient, KNMIError, day_query


class KNMITests(unittest.TestCase):
    def test_query_handles_local_day_and_clock_change(self):
        self.assertEqual(day_query(date(2025, 1, 15))["datetime"],
                         "2025-01-14T22:50:00Z/2025-01-15T23:10:00Z")
        self.assertEqual(day_query(date(2025, 3, 30))["datetime"],
                         "2025-03-29T22:50:00Z/2025-03-30T22:10:00Z")

    def test_missing_key_stops_before_request(self):
        with patch.dict(os.environ, {"KNMI_EDR_API_KEY": ""}):
            with self.assertRaises(KNMIError):
                KNMIClient()

    def test_request_and_cache(self):
        # Synthetisch transportantwoord; geen live KNMI-validatie.
        with patch.dict(os.environ, {"KNMI_EDR_API_KEY": "test-only"}), tempfile.TemporaryDirectory() as folder:
            client = KNMIClient(Path(folder))
            client.opener = Mock()
            client.opener.open.return_value = BytesIO(json.dumps({"type": "Coverage"}).encode())
            result = client.observations("0-20000-0-06270", date(2025, 1, 15))
            request = client.opener.open.call_args.args[0]
            self.assertTrue(request.full_url.startswith(BASE_URL + "/locations/0-20000-0-06270?"))
            self.assertEqual(parse_qs(urlsplit(request.full_url).query)["parameter-name"], ["ff,dd"])
            self.assertNotIn("test-only", request.full_url)
            self.assertEqual(result, client.observations("0-20000-0-06270", date(2025, 1, 15)))
            self.assertEqual(client.opener.open.call_count, 1)
            self.assertNotIn("test-only", next(Path(folder).glob("*.json")).read_text())

    def test_failed_requests_are_not_cached(self):
        with patch.dict(os.environ, {"KNMI_EDR_API_KEY": "test-only"}), tempfile.TemporaryDirectory() as folder:
            client = KNMIClient(Path(folder))
            client.opener = Mock()
            client.opener.open.side_effect = HTTPError(BASE_URL, 429, "Too many requests", {}, None)
            with self.assertRaisesRegex(KNMIError, "limiet"):
                client.metadata()
            self.assertEqual(list(Path(folder).iterdir()), [])
