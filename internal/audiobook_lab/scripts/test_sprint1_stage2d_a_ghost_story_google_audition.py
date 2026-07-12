#!/usr/bin/env python3
"""Focused tests for the Stage 2D Google audition wrapper."""

from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path


SCRIPT = Path(__file__).with_name("sprint1_stage2d_a_ghost_story_google_audition.py")
SPEC = importlib.util.spec_from_file_location("stage2d_google", SCRIPT)
stage2d = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(stage2d)


@contextmanager
def temporary_env(**updates):
    before = {name: os.environ.get(name) for name in updates}
    try:
        for name, value in updates.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        yield
    finally:
        for name, value in before.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


class Stage2DGoogleAuditionTests(unittest.TestCase):
    def valid_env(self) -> dict:
        return {**stage2d.EXPECTED_ENV, "OPENAI_API_KEY": "set", "GOOGLE_APPLICATION_CREDENTIALS": "set", "GOOGLE_CLOUD_PROJECT": "set"}

    def test_missing_google_cap_blocks(self):
        env = self.valid_env()
        env["EARNALISM_GOOGLE_TTS_MAX_ESTIMATED_USD"] = None
        with temporary_env(**env):
            self.assertIn("EARNALISM_GOOGLE_TTS_MAX_ESTIMATED_USD must equal 1", stage2d.runtime_gate_errors())

    def test_source_passages_cover_opening_middle_and_ending(self):
        manuscript = (
            "Opening one. Opening two. Then I heard the rustle and watched with fascinated eyes. "
            "Ending one. Ending two."
        )
        passages = stage2d.source_passages(manuscript)
        self.assertEqual([item["passage_id"] for item in passages], ["opening", "failed_middle", "ending"])
        self.assertTrue(passages[0]["text"].startswith("Opening one"))
        self.assertIn("Then I heard the rustle", passages[1]["text"])
        self.assertTrue(passages[2]["text"].endswith("Ending two."))

    def test_budget_blocks_before_provider_when_subcap_is_too_low(self):
        env = self.valid_env()
        env["EARNALISM_GOOGLE_TTS_MAX_ESTIMATED_USD"] = "0.01"
        with temporary_env(**env):
            estimate = stage2d.budget_estimate([{"characters": 1000}] * 3)
        self.assertEqual(estimate["status"], "BLOCKED")

    def test_lock_holder_is_narrow(self):
        payload = stage2d.acquired_lock_payload(
            {"status": "active", "current_holder": "none", "allowed_next_holders": []},
            voice="en-GB-Studio-B",
            estimate={"estimated_current_usd": 0.2},
        )
        self.assertEqual(payload["current_holder"], "sprint1_publication_stage2d")
        self.assertEqual(payload["allowed_slugs"], ["a-ghost-story"])
        self.assertEqual(payload["allowed_next_holders"], [])

    def test_release_rubric_rejects_owner_minimum_only_score(self):
        scores = {field: 9.4 for field in stage2d.LISTENING_THRESHOLDS}
        scores["confidence_score"] = 0.95
        judgment = {
            "sample_label": "middle",
            "scores": scores,
            "judge_flags": dict(stage2d.BINARY_LISTENING_FLAGS),
        }
        passed, blockers = stage2d.audition_pass([judgment])
        self.assertFalse(passed)
        self.assertTrue(blockers)

    def test_release_rubric_accepts_universal_pass(self):
        scores = {field: 9.8 for field in stage2d.LISTENING_THRESHOLDS}
        scores["confidence_score"] = 0.98
        judgment = {
            "sample_label": "middle",
            "scores": scores,
            "judge_flags": dict(stage2d.BINARY_LISTENING_FLAGS),
        }
        passed, blockers = stage2d.audition_pass([judgment])
        self.assertTrue(passed)
        self.assertEqual(blockers, [])

    def test_local_validation_retry_is_exact_and_artifact_bound(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            voice_dir = root / "en-GB-Studio-B"
            voice_dir.mkdir()
            (voice_dir / "opening.mp3").write_bytes(b"valid-audio-placeholder")
            prior = {
                "errors": ["RuntimeError: Google returned invalid audio for opening"],
                "judgments": [],
                "lock_restored": True,
            }
            original = stage2d.ffprobe_with_retry
            stage2d.ffprobe_with_retry = lambda _path, attempts=3: 41.0
            try:
                allowed, reason = stage2d.local_validation_retry_allowed(prior, root, "en-GB-Studio-B")
            finally:
                stage2d.ffprobe_with_retry = original
            self.assertTrue(allowed)
            self.assertEqual(reason, "VALID_OPENING_ARTIFACT_REUSE_AFTER_FFPROBE_REPAIR")

    def test_local_validation_retry_rejects_other_error(self):
        prior = {"errors": ["different"], "judgments": [], "lock_restored": True}
        allowed, _ = stage2d.local_validation_retry_allowed(prior, Path("/tmp"), "en-GB-Studio-B")
        self.assertFalse(allowed)

    def test_prosody_repair_ssml_preserves_words_and_adds_breaks(self):
        source = "One, two; three. Four & five."
        ssml = stage2d.source_preserving_ssml(source)
        self.assertIn("<prosody rate=\"88%\">", ssml)
        self.assertIn("<break time=\"180ms\"/>", ssml)
        spoken = stage2d.html.unescape(stage2d.re.sub(r"<[^>]+>", "", ssml))
        self.assertEqual(spoken, source)

    def test_prosody_repair_has_distinct_fingerprint(self):
        passages = [{"text_hash": "abc"}]
        baseline = stage2d.attempt_fingerprint(voice="en-GB-Studio-C", passages=passages)
        repaired = stage2d.attempt_fingerprint(voice="en-GB-Studio-C", passages=passages, prosody_repair=True)
        self.assertNotEqual(baseline, repaired)


if __name__ == "__main__":
    unittest.main()
