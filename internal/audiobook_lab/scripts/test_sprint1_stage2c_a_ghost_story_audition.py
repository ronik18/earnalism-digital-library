#!/usr/bin/env python3
"""No-provider tests for the Stage 2C A Ghost Story audition."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from internal.audiobook_lab.scripts import sprint1_stage2c_a_ghost_story_audition as audition


class Stage2CAuditionTests(unittest.TestCase):
    def test_passage_is_exact_failed_middle_span(self) -> None:
        manuscript = "prefix Then I heard the rustle of a garment. I watched it with fascinated eyes. suffix"
        passage = audition.extract_passage(manuscript)
        self.assertEqual(
            passage,
            "Then I heard the rustle of a garment. I watched it with fascinated eyes.",
        )

    def test_fingerprint_changes_by_voice_or_profile(self) -> None:
        first = audition.attempt_fingerprint(text="text", model="model", voice="verse", profile="classic_literary_narrator")
        second = audition.attempt_fingerprint(text="text", model="model", voice="coral", profile="classic_literary_narrator")
        third = audition.attempt_fingerprint(text="text", model="model", voice="verse", profile="mystery_suspense_narrator")
        self.assertNotEqual(first, second)
        self.assertNotEqual(first, third)

    def test_attempt_guard_scans_all_prior_arms(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            original = audition.RESULT_DIR
            audition.RESULT_DIR = Path(raw)
            try:
                audition.result_path("verse", "classic_literary_narrator").write_text(
                    json.dumps({"attempt_fingerprint": "same", "provider_calls_ran": True}),
                    encoding="utf-8",
                )
                self.assertTrue(audition.completed_attempt_exists("same"))
                self.assertFalse(audition.completed_attempt_exists("different"))
            finally:
                audition.RESULT_DIR = original

    def test_audition_pass_uses_strict_repo_policy(self) -> None:
        scores = {field: threshold for field, threshold in audition.LISTENING_THRESHOLDS.items()}
        judgment = {
            "scores": scores,
            "judge_flags": {field: False for field in audition.BINARY_LISTENING_FLAGS},
            "frontmatter_present": False,
            "blocker_reason": "",
        }
        passed, blockers = audition.audition_pass(judgment)
        self.assertTrue(passed, blockers)

    def test_audition_rejects_owner_minimum_without_repo_threshold(self) -> None:
        scores = {field: 9.4 for field in audition.LISTENING_THRESHOLDS}
        scores["confidence_score"] = 0.90
        judgment = {
            "scores": scores,
            "judge_flags": {field: False for field in audition.BINARY_LISTENING_FLAGS},
            "frontmatter_present": False,
            "blocker_reason": "",
        }
        passed, blockers = audition.audition_pass(judgment)
        self.assertFalse(passed)
        self.assertTrue(blockers)


if __name__ == "__main__":
    unittest.main()
