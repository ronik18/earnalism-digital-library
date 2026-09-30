"""Regression coverage for a green action with no executed implementation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.catalogue_compliance_worker_receipt import validate_receipt


class WorkerReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.batch = Path(self.temp.name) / "batch.json"
        self.receipt = Path(self.temp.name) / "receipt.json"
        self.head = "1" * 40
        self.batch.write_text(json.dumps({"schema_version": 1, "max_titles_to_modify": 5,
                                         "candidate_count": 2,
                                         "candidates": [{"slug": "a"}, {"slug": "b"}]}))
        self.record = {"execution_status": "COMPLETED", "source_head": self.head,
                       "batch_sha256": hashlib.sha256(self.batch.read_bytes()).hexdigest(),
                       "examined_slugs": ["a"]}

    def write_receipt(self):
        self.receipt.write_text(json.dumps(self.record))

    def validate(self):
        return validate_receipt(self.receipt, self.batch, self.head)

    def test_completed_exact_candidate_assessment_passes(self):
        self.write_receipt()
        self.assertEqual(self.validate(), self.record)

    def test_action_success_without_worker_receipt_is_rejected(self):
        result = subprocess.run([sys.executable, "-m", "scripts.catalogue_compliance_worker_receipt",
                                 "--receipt", str(self.receipt), "--batch", str(self.batch),
                                 "--expected-head", self.head], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("execution receipt is missing", result.stderr)

    def test_started_and_blocked_workers_cannot_publish_no_progress(self):
        for status in ["STARTED", "BLOCKED"]:
            with self.subTest(status=status):
                self.record["execution_status"] = status
                self.write_receipt()
                with self.assertRaisesRegex(ValueError, "did not complete"):
                    self.validate()

    def test_stale_source_and_changed_batch_are_rejected(self):
        self.record["source_head"] = "2" * 40
        self.write_receipt()
        with self.assertRaisesRegex(ValueError, "source head"):
            self.validate()
        self.record["source_head"] = self.head
        self.write_receipt()
        self.batch.write_text(self.batch.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "different batch"):
            self.validate()

    def test_empty_outside_and_duplicate_assessments_are_rejected(self):
        for slugs in [[], ["outside"], ["a", "a"]]:
            with self.subTest(slugs=slugs):
                self.record["examined_slugs"] = slugs
                self.write_receipt()
                with self.assertRaisesRegex(ValueError, "candidate assessment"):
                    self.validate()

    def test_symlink_receipt_is_rejected(self):
        target = Path(self.temp.name) / "target.json"
        target.write_text(json.dumps(self.record))
        self.receipt.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.validate()


if __name__ == "__main__":
    unittest.main()
