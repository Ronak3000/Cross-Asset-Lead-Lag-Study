from io import BytesIO
import json
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from study import BASELINE, request, wait_for_coverage


class DatabentoRequestTests(unittest.TestCase):
    @patch("study.urlopen")
    def test_coverage_uses_get_for_each_missing_dataset(self, urlopen):
        coverage = {"schema": {"mbp-1": {"start": BASELINE.start, "end": BASELINE.end}}}
        urlopen.side_effect = lambda *args, **kwargs: BytesIO(json.dumps(coverage).encode())
        wait_for_coverage("test-key", BASELINE, list(BASELINE.feeds))
        self.assertEqual(urlopen.call_count, len(BASELINE.feeds))
        for call, dataset in zip(urlopen.call_args_list, BASELINE.feeds.values()):
            req = call.args[0]
            url = urlsplit(req.full_url)
            self.assertEqual(req.get_method(), "GET")
            self.assertEqual(url.path, "/v0/metadata.get_dataset_range")
            self.assertEqual(parse_qs(url.query), {"dataset": [dataset]})
            self.assertIsNone(req.data)

    @patch("study.urlopen")
    def test_cost_and_download_use_form_posts(self, urlopen):
        for endpoint in ("metadata.get_cost", "timeseries.get_range"):
            with self.subTest(endpoint=endpoint):
                request(endpoint, "test-key", "SPY")
                req = urlopen.call_args.args[0]
                self.assertEqual(req.get_method(), "POST")
                self.assertEqual(urlsplit(req.full_url).path, f"/v0/{endpoint}")
                self.assertEqual(parse_qs(req.data.decode())["symbols"], ["SPY"])
