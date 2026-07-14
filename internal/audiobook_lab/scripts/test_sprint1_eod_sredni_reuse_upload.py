from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_eod_sredni_reuse_upload.py")
SPEC = importlib.util.spec_from_file_location("sredni_upload", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class SredniReuseUploadTests(unittest.TestCase):
    def test_runtime_gates_fail_closed(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            errors = MODULE.runtime_gate_errors()
        self.assertIn("SPRINT1_TOTAL_AUDIO_BUDGET_USD must equal 175", errors)
        self.assertIn("B2_BUCKET is required", errors)

    def test_lock_requires_idle_state(self):
        raw = json.dumps({"status": "active", "current_holder": "none", "allowed_next_holders": []}).encode()
        self.assertEqual(MODULE.load_lock(raw)["current_holder"], "none")
        with self.assertRaises(RuntimeError):
            MODULE.load_lock(json.dumps({"status": "active", "current_holder": "other", "allowed_next_holders": []}).encode())

    def test_vtt_validator_accepts_measured_cues_and_rejects_bad_bounds(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "highlight.vtt"
            path.write_text("WEBVTT\n\n1\n00:00:00.000 --> 00:00:00.500\nHello\n", encoding="utf-8")
            self.assertEqual(MODULE.validate_vtt(path, 1.0, 1), [])
            self.assertTrue(MODULE.validate_vtt(path, 0.1, 1))

    def test_aggregate_reuse_result_is_selected_by_slug(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            aggregate = root / "qa.json"
            aggregate.write_text(json.dumps({"results": [{"slug": "other"}]}), encoding="utf-8")
            args = type("Args", (), {"full_qa": aggregate, "artifact_dir": root})()
            result = MODULE.validate_release_evidence(args)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("exactly one Sredni result", result["blockers"][0])


if __name__ == "__main__":
    unittest.main()
