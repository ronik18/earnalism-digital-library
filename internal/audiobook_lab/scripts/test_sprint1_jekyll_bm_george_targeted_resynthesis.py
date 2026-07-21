#!/usr/bin/env python3
"""Focused tests for Jekyll's one-passage targeted repair."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import subprocess
import unittest


SCRIPT = Path(__file__).with_name("sprint1_jekyll_bm_george_targeted_resynthesis.py")
SPEC = importlib.util.spec_from_file_location("jekyll_targeted", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class JekyllTargetedResynthesisTests(unittest.TestCase):
    def test_prior_projection_binds_one_target_and_three_reused_passes(self) -> None:
        _evidence, reports, samples = MODULE.validate_prior(MODULE.DEFAULT_INPUT)
        self.assertEqual(len(reports), 4)
        self.assertEqual(len(samples), 4)
        self.assertEqual(
            {
                item["passage_id"]
                for item in reports
                if item["pass"] is not True
            },
            set(MODULE.TARGET_PASSAGE_IDS),
        )
        self.assertEqual(
            {item["passage_id"] for item in reports if item["pass"] is True},
            set(MODULE.REUSED_PASSAGE_IDS),
        )

    def test_preparation_preserves_every_lexical_token(self) -> None:
        _passages, indexed = MODULE.canonical_passages()
        source = indexed[MODULE.TARGET_PASSAGE_IDS[0]]["text"]
        prepared, transformations = MODULE.prepare_text(source)
        self.assertEqual(
            MODULE.sha256_text(prepared), MODULE.PREPARED_TEXT_BINDING["sha256"]
        )
        self.assertEqual(len(transformations), 2)
        self.assertEqual(
            MODULE.BASE.lexical_tokens(source), MODULE.BASE.lexical_tokens(prepared)
        )
        self.assertIn("Sometimes—wondering", prepared)

    @unittest.skipUnless(PINNED_PYTHON.is_file(), "pinned audio runtime missing")
    def test_prepared_g2p_is_british_fallback_free_and_pinned(self) -> None:
        _passages, indexed = MODULE.canonical_passages()
        prepared, _ = MODULE.prepare_text(indexed[MODULE.TARGET_PASSAGE_IDS[0]]["text"])
        report = MODULE.validate_prepared_g2p(prepared)
        self.assertEqual(report["status"], "PASS")
        self.assertIs(report["british"], True)
        self.assertIsNone(report["fallback"])
        self.assertEqual(report["unresolved_tokens"], [])
        self.assertEqual(
            report["phoneme_sha256"], MODULE.PREPARED_TEXT_BINDING["phoneme_sha256"]
        )

    def test_attempt_fingerprint_is_exact(self) -> None:
        self.assertEqual(
            MODULE.attempt_fingerprint(), MODULE.EXPECTED_ATTEMPT_FINGERPRINT
        )

    def test_exact_transcript_passes_and_substantive_miss_fails(self) -> None:
        _passages, indexed = MODULE.canonical_passages()
        canonical = indexed[MODULE.TARGET_PASSAGE_IDS[0]]
        sample = {
            "audio_sha256": "a" * 64,
            "source_text_sha256": MODULE.PREPARED_TEXT_BINDING["sha256"],
        }
        exact = MODULE.evaluate(canonical, sample, canonical["text"], "test")
        self.assertTrue(exact["pass"])
        wrong = MODULE.evaluate(
            canonical,
            sample,
            canonical["text"].replace("wondering", "wandering", 1),
            "test",
        )
        self.assertFalse(wrong["pass"])

    def test_cli_has_no_listening_upload_or_publication_surface(self) -> None:
        source = inspect.getsource(MODULE)
        self.assertNotIn('"/audio/', source)
        self.assertNotIn("speechSynthesis", source)
        self.assertNotIn("def upload", source)
        self.assertNotIn("def publish", source)
        result = subprocess.run(
            [str(PINNED_PYTHON), str(SCRIPT), "--help"],
            cwd=MODULE.ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--preflight", result.stdout)
        self.assertIn("--execute", result.stdout)
        self.assertNotIn("--upload", result.stdout)
        self.assertNotIn("--publish", result.stdout)


if __name__ == "__main__":
    unittest.main()
