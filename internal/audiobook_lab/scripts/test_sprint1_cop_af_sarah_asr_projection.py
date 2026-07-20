#!/usr/bin/env python3
"""Focused tests for the offline Cop af_sarah transcript projection."""

from __future__ import annotations

import importlib.util
import inspect
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sprint1_cop_af_sarah_asr_projection.py")
SPEC = importlib.util.spec_from_file_location("cop_sarah_projection", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CopAfSarahProjectionTests(unittest.TestCase):
    def test_input_is_hash_bound_to_four_immutable_wavs(self) -> None:
        payload, passages = MODULE.validate_input(MODULE.DEFAULT_INPUT)
        self.assertEqual(len(passages), 4)
        self.assertEqual(
            {item["passage_id"]: item["audio_sha256"] for item in payload["samples"]},
            MODULE.PROFILE.EXPECTED_EXISTING_AUDIO_HASHES,
        )

    def test_waiter_projection_repairs_only_bound_text_equivalents(self) -> None:
        payload, passages = MODULE.validate_input(MODULE.DEFAULT_INPUT)
        source = {item["passage_id"]: item["text"] for item in passages}
        waiter = next(
            item for item in payload["asr"]["reports"] if item["passage_id"] == "waiter_dialogue"
        )
        evaluated, applications = MODULE.apply_projection_rules(
            "waiter_dialogue", waiter["raw_transcript"]
        )
        metrics = MODULE.BASE.ordered_token_integrity(
            source["waiter_dialogue"], evaluated
        )
        self.assertEqual(metrics["score"], 10.0)
        self.assertIs(metrics["ordered_content_integrity_pass"], True)
        self.assertEqual(len(applications), 5)
        self.assertTrue(all(item["match_count"] == 1 for item in applications))

    def test_projection_fingerprint_is_pinned_and_lifecycle_guarded(self) -> None:
        fingerprint = MODULE.projection_fingerprint()
        self.assertEqual(fingerprint, MODULE.EXPECTED_PROJECTION_FINGERPRINT)
        if MODULE.DEFAULT_OUTPUT.is_file():
            self.assertIn(
                fingerprint, MODULE.DEFAULT_OUTPUT.read_text(encoding="utf-8")
            )
            with self.assertRaises(MODULE.CopAfSarahProjectionError):
                MODULE.ensure_not_repeated(fingerprint)
        else:
            MODULE.ensure_not_repeated(fingerprint)

    def test_dry_run_does_not_write_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "projection.json"
            original_no_repeat = MODULE.NO_REPEAT_FILES
            try:
                MODULE.NO_REPEAT_FILES = ()
                code, payload = MODULE.execute(
                    MODULE.DEFAULT_INPUT,
                    output,
                    MODULE.DEFAULT_PAID_LOCK,
                    dry_run=True,
                )
            finally:
                MODULE.NO_REPEAT_FILES = original_no_repeat
            self.assertEqual(code, 0)
            self.assertEqual(payload["status"], "DRY_RUN_PASS")
            self.assertEqual(payload["new_asr_decoder_calls"], 0)
            self.assertIs(payload["resynthesis_performed"], False)
            self.assertFalse(output.exists())

    def test_source_has_no_synthesis_decoder_upload_or_publication(self) -> None:
        source = inspect.getsource(MODULE)
        self.assertNotIn("def synthesize", source)
        self.assertNotIn("transcribe(", source)
        self.assertNotIn("--upload", source)
        self.assertNotIn("--publish", source)
        self.assertNotIn("speechSynthesis", source)


if __name__ == "__main__":
    unittest.main()
