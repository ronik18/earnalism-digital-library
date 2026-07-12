#!/usr/bin/env python3
"""Focused tests for the Stage 2D Google full-TTS wrapper."""

from __future__ import annotations

import importlib.util
import os
import unittest
from contextlib import contextmanager
from pathlib import Path


SCRIPT = Path(__file__).with_name("sprint1_stage2d_a_ghost_story_google_full_tts.py")
SPEC = importlib.util.spec_from_file_location("stage2d_full_tts", SCRIPT)
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


class Stage2DGoogleFullTTSTests(unittest.TestCase):
    def test_missing_full_tts_cap_blocks(self):
        env = {**stage2d.EXPECTED_ENV, "GOOGLE_APPLICATION_CREDENTIALS": "set", "GOOGLE_CLOUD_PROJECT": "set"}
        env["EARNALISM_GOOGLE_TTS_FULL_MAX_ESTIMATED_USD"] = None
        with temporary_env(**env):
            self.assertIn("EARNALISM_GOOGLE_TTS_FULL_MAX_ESTIMATED_USD must equal 1", stage2d.runtime_gate_errors())

    def test_budget_is_bounded(self):
        with temporary_env(**stage2d.EXPECTED_ENV):
            estimate = stage2d.budget_estimate("a" * 13284)
        self.assertEqual(estimate["status"], "PASS")
        self.assertEqual(estimate["estimated_full_tts_usd"], 0.2657)

    def test_ssml_round_trip_preserves_chunk_text(self):
        source = "One, two; three. Four & five."
        ssml = stage2d.audition.source_preserving_ssml(source)
        self.assertEqual(stage2d.normalized_spoken_text(ssml), source)

    def test_full_fingerprint_changes_with_text(self):
        first = stage2d.full_fingerprint("one", [{"text_hash": "a"}])
        second = stage2d.full_fingerprint("two", [{"text_hash": "b"}])
        self.assertNotEqual(first, second)

    def test_lock_scope_is_narrow(self):
        payload = stage2d.acquired_lock_payload(
            {"status": "active", "current_holder": "none", "allowed_next_holders": []},
            {"estimated_full_tts_usd": 0.3},
        )
        self.assertEqual(payload["current_holder"], "sprint1_publication_stage2d")
        self.assertEqual(payload["allowed_slugs"], ["a-ghost-story"])
        self.assertEqual(payload["allowed_next_holders"], [])


if __name__ == "__main__":
    unittest.main()
