import json
import os
import tempfile
import unittest
from unittest import mock

from pipeline import config, review


class ReviewAlertsTest(unittest.TestCase):
    def test_findings_above_threshold_alert_every_recipient(self):
        with tempfile.TemporaryDirectory() as tmp:
            spool = os.path.join(tmp, "spool")
            cfg = config.Config(
                findings_dir=os.path.join(tmp, "findings"),
                severity_threshold=2,
                no_notify=False,
                ping=["a@example.com", "b@example.com"],
                page=["c@example.com"],
            )
            with mock.patch.dict(os.environ, {"NOTIFY_SPOOL": spool}):
                result = review.run("2026-11-04", cfg)
            self.assertGreaterEqual(result["findings"], 1)
            sent = [json.load(open(os.path.join(spool, f))) for f in os.listdir(spool)]
            self.assertEqual(sorted(m["to"] for m in sent),
                             ["a@example.com", "b@example.com", "c@example.com"])

    def test_findings_are_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = config.Config(os.path.join(tmp, "findings"), 2, True, [], [])
            review.run("2026-11-04", cfg)
            self.assertTrue(os.path.exists(os.path.join(tmp, "findings", "2026-11-04.jsonl")))


if __name__ == "__main__":
    unittest.main()
