#!/usr/bin/env python3
"""Focused tests for the Stage 2D Google full-QA wrapper."""

from __future__ import annotations

import importlib.util
import os
import unittest
from contextlib import contextmanager
from pathlib import Path


SCRIPT = Path(__file__).with_name("sprint1_stage2d_a_ghost_story_google_full_qa.py")
SPEC = importlib.util.spec_from_file_location("stage2d_full_qa", SCRIPT)
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


def sample(score: float = 9.4, confidence: float = 0.95, **flags) -> dict:
    return {
        "scores": {"overall_listening_score": score, "confidence_score": confidence},
        "judge_flags": flags,
    }


class Stage2DGoogleFullQATests(unittest.TestCase):
    def test_missing_asr_cap_blocks(self):
        env = {**stage2d.EXPECTED_ENV, "OPENAI_API_KEY": "set"}
        env["EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD"] = None
        with temporary_env(**env):
            self.assertIn("EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD must equal 10", stage2d.runtime_gate_errors())

    def test_budget_is_within_cap(self):
        with temporary_env(**stage2d.EXPECTED_ENV):
            estimate = stage2d.budget_estimate(880.944)
        self.assertEqual(estimate["status"], "PASS")
        self.assertEqual(estimate["estimated_asr_usd"], 0.1175)
        self.assertEqual(estimate["estimated_listening_qa_usd"], 0.3)

    def test_owner_gate_requires_six_samples(self):
        self.assertFalse(stage2d.owner_listening_gate([sample()] * 5)["passes"])

    def test_owner_gate_requires_every_sample_at_9_4(self):
        samples = [sample()] * 5 + [sample(9.3)]
        self.assertFalse(stage2d.owner_listening_gate(samples)["passes"])

    def test_owner_gate_rejects_fatal_flag(self):
        samples = [sample()] * 5 + [sample(list_reading_rhythm_detected=True)]
        self.assertFalse(stage2d.owner_listening_gate(samples)["passes"])

    def test_owner_gate_accepts_complete_minimum(self):
        self.assertTrue(stage2d.owner_listening_gate([sample()] * 6)["passes"])

    def test_lock_scope_is_narrow(self):
        payload = stage2d.acquired_lock_payload(
            {"status": "active", "current_holder": "none", "allowed_next_holders": []},
            {"estimated_current_qa_usd": 0.42},
        )
        self.assertEqual(payload["current_holder"], "sprint1_publication_stage2d")
        self.assertEqual(payload["allowed_slugs"], ["a-ghost-story"])


if __name__ == "__main__":
    unittest.main()
