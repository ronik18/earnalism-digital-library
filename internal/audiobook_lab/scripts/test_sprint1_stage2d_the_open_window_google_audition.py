#!/usr/bin/env python3
"""Focused tests for The Open Window bounded Google audition wrapper."""

from __future__ import annotations

import importlib.util
import os
import unittest
from contextlib import contextmanager
from pathlib import Path


SCRIPT = Path(__file__).with_name("sprint1_stage2d_the_open_window_google_audition.py")
SPEC = importlib.util.spec_from_file_location("stage2d_open_window", SCRIPT)
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


class OpenWindowGoogleAuditionTests(unittest.TestCase):
    def valid_env(self) -> dict:
        return {
            **stage2d.shared.EXPECTED_ENV,
            "OPENAI_API_KEY": "set",
            "GOOGLE_APPLICATION_CREDENTIALS": "set",
            "GOOGLE_CLOUD_PROJECT": "set",
        }

    def test_passages_cover_opening_middle_and_ending(self):
        source = (
            "“My aunt will be down presently, Mr. Nuttel,” said a very self-possessed young lady of fifteen; "
            "“in the meantime you must try and put up with me.” “Out through that window, three years ago, "
            "they went shooting. They crossed a treacherous piece of bog. A tired brown spaniel followed. "
            "A voice said, Bertie, why do you bound?” He was once hunted by dogs. Enough to make anyone "
            "lose their nerve. Romance at short notice was her speciality."
        )
        passages = stage2d.source_passages(source)
        self.assertEqual(
            [item["passage_id"] for item in passages],
            ["opening_dialogue", "shooting_party_tragedy", "twilight_return", "spaniel_explanation_ending"],
        )
        self.assertTrue(passages[0]["text"].startswith("“My aunt"))
        self.assertIn("treacherous piece of bog", passages[1]["text"])
        self.assertIn("Bertie, why do you bound", passages[2]["text"])
        self.assertTrue(passages[3]["text"].endswith("Romance at short notice was her speciality."))

    def test_budget_gate_uses_existing_sprint_spend(self):
        with temporary_env(**self.valid_env()):
            estimate = stage2d.budget_estimate([{"characters": 300}] * 4)
        self.assertEqual(estimate["status"], "PASS")
        self.assertEqual(estimate["estimated_current_usd"], 0.224)
        self.assertEqual(estimate["estimated_sprint_total_usd"], 4.2924)

    def test_retry_budget_includes_prior_title_and_sprint_attempt(self):
        with temporary_env(**self.valid_env()):
            estimate = stage2d.budget_estimate(
                [{"characters": 300}] * 4,
                prior_sprint_estimated_spend_usd=3.8506,
                prior_title_estimated_spend_usd=0.2178,
            )
        self.assertEqual(estimate["estimated_title_total_usd"], 0.4418)
        self.assertEqual(estimate["estimated_sprint_total_usd"], 4.0746)

    def test_missing_google_cap_blocks_before_provider(self):
        env = self.valid_env()
        env["EARNALISM_GOOGLE_TTS_MAX_ESTIMATED_USD"] = None
        with temporary_env(**env):
            errors = stage2d.runtime_gate_errors()
        self.assertIn("EARNALISM_GOOGLE_TTS_MAX_ESTIMATED_USD must equal 1", errors)

    def test_prosody_retry_requires_separate_approval(self):
        env = self.valid_env()
        env["EARNALISM_APPROVE_THE_OPEN_WINDOW_STUDIO_B_PROSODY_REPAIR"] = None
        with temporary_env(**env):
            errors = stage2d.runtime_gate_errors(prosody_repair=True)
        self.assertIn(
            "EARNALISM_APPROVE_THE_OPEN_WINDOW_STUDIO_B_PROSODY_REPAIR must equal true",
            errors,
        )

    def test_source_hash_mismatch_blocks(self):
        chapter = {
            "content": "changed",
            "processing_status": "ready",
            "processing_warnings": [],
            "sanitizedSha256": stage2d.EXPECTED_SANITIZED_SHA256,
        }
        with self.assertRaisesRegex(RuntimeError, "controlled content hash changed"):
            stage2d.validated_manuscript(chapter)

    def test_sample_duration_is_bounded(self):
        stage2d.validate_sample_duration(30.0, "opening")
        with self.assertRaisesRegex(RuntimeError, "exceeded 30s cap"):
            stage2d.validate_sample_duration(30.001, "opening")

    def test_lock_scope_is_title_specific(self):
        payload = stage2d.acquired_lock_payload(
            {"status": "active", "current_holder": "none", "allowed_next_holders": []},
            voice="en-GB-Studio-B",
            estimate={"estimated_current_usd": 0.204},
            prosody_repair=False,
        )
        self.assertEqual(payload["current_holder"], "sprint1_publication_stage2e_the_open_window")
        self.assertEqual(payload["allowed_slugs"], ["the-open-window"])
        self.assertEqual(payload["allowed_next_holders"], [])
        self.assertEqual(payload["run_id"], "sprint1-stage2e-the-open-window-en-gb-studio-b")
        self.assertIn("Stage 2E final", payload["approved_scope"])

    def test_stage2e_authorization_is_studio_b_only(self):
        self.assertEqual(
            stage2d.OWNER_DECISION,
            "AUTHORIZE_STAGE_2E_THE_OPEN_WINDOW_STUDIO_B_AUDITION_AND_PUBLICATION_IF_PASS",
        )
        self.assertEqual(stage2d.SUPPORTED_VOICES, {"en-GB-Studio-B"})
        self.assertEqual(stage2d.LISTENING_POLICY, "schema3_universal_9_7")
        self.assertIn(
            "the-open-window_stage2e_google_audition_en_gb_studio_b.json",
            str(stage2d.result_path("en-GB-Studio-B", False)),
        )

    def test_fingerprint_changes_for_prosody_repair(self):
        passages = [{"text_hash": "abc"}]
        baseline = stage2d.attempt_fingerprint(voice="en-GB-Studio-B", passages=passages, prosody_repair=False)
        repaired = stage2d.attempt_fingerprint(voice="en-GB-Studio-B", passages=passages, prosody_repair=True)
        self.assertNotEqual(baseline, repaired)


if __name__ == "__main__":
    unittest.main()
