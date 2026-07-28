#!/usr/bin/env python3
"""Fail-closed regression tests for the Sprint 1 listening cutoff of 9.0."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HOOK_DIR = ROOT / "internal" / "audiobook_lab" / "scripts" / "factory_hooks"
sys.path.insert(0, str(HOOK_DIR))

from asr_sync_hook import (  # noqa: E402
    BENGALI_AUDIOBOOK_92_POLICY,
    BINARY_LISTENING_FLAGS,
    SPRINT1_AUDIOBOOK_90_POLICY,
    audio_derived_asr_gate,
    evaluate_listening_evidence,
)


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def passing_scores() -> dict:
    return {
        "naturalness_score": 8.9,
        "pronunciation_score": 8.9,
        "emotional_expression_score": 8.9,
        "punctuation_pause_score": 8.9,
        "pacing_score": 8.9,
        "continuity_score": 8.9,
        "anti_robotic_texture_score": 9.2,
        "anti_choppy_join_score": 9.2,
        "listener_enjoyment_score": 8.9,
        "overall_listening_score": 9.0,
        "confidence_score": 0.90,
    }


def clean_flags() -> dict:
    return {name: False for name in BINARY_LISTENING_FLAGS}


class Sprint1Audiobook90PolicyTests(unittest.TestCase):
    def evaluate(self, scores: dict | None = None, flags: dict | None = None, language: str = "eng"):
        return evaluate_listening_evidence(
            scores or passing_scores(),
            flags or clean_flags(),
            language=language,
            release_policy=SPRINT1_AUDIOBOOK_90_POLICY,
        )

    def test_exact_listening_boundary_passes_for_bengali_and_english(self) -> None:
        for language in ("ben", "eng"):
            with self.subTest(language=language):
                valid, blockers, policy = self.evaluate(language=language)
                self.assertTrue(valid, blockers)
                self.assertEqual(policy["name"], SPRINT1_AUDIOBOOK_90_POLICY)

    def test_overall_confidence_dimensions_and_fatal_flags_remain_strict(self) -> None:
        cases = (
            ("overall_listening_score", 8.99),
            ("confidence_score", 0.899),
            ("naturalness_score", 8.89),
            ("anti_robotic_texture_score", 9.19),
            ("anti_choppy_join_score", 9.19),
        )
        for field, value in cases:
            with self.subTest(field=field):
                scores = passing_scores()
                scores[field] = value
                valid, blockers, _ = self.evaluate(scores=scores)
                self.assertFalse(valid)
                self.assertTrue(any(field in blocker for blocker in blockers), blockers)

        for flag_name in BINARY_LISTENING_FLAGS:
            with self.subTest(flag=flag_name):
                flags = clean_flags()
                flags[flag_name] = True
                valid, blockers, _ = self.evaluate(flags=flags)
                self.assertFalse(valid)
                self.assertTrue(any(flag_name in blocker for blocker in blockers), blockers)

    def test_historical_92_policy_remains_immutable(self) -> None:
        scores = passing_scores()
        valid, blockers, policy = evaluate_listening_evidence(
            scores,
            clean_flags(),
            language="ben",
            release_policy=BENGALI_AUDIOBOOK_92_POLICY,
        )
        self.assertFalse(valid)
        self.assertEqual(policy["thresholds"]["overall_listening_score"], 9.2)
        self.assertTrue(any("overall_listening_score" in blocker for blocker in blockers), blockers)

    def test_objective_asr_gate_did_not_move(self) -> None:
        metrics = {
            "score": 9.7,
            "coverage": 0.98,
            "token_order_similarity": 0.97,
            "first_words_match": True,
            "last_words_match": True,
            "frontmatter_absent": True,
        }
        valid, blockers = audio_derived_asr_gate(metrics, word_timestamp_count=1)
        self.assertTrue(valid, blockers)

        mutations = (
            ("score", 9.69),
            ("coverage", 0.979),
            ("token_order_similarity", 0.969),
            ("first_words_match", False),
            ("last_words_match", False),
            ("frontmatter_absent", False),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                failed = {**metrics, field: value}
                valid, blockers = audio_derived_asr_gate(failed, word_timestamp_count=1)
                self.assertFalse(valid)
                self.assertTrue(blockers)
        valid, blockers = audio_derived_asr_gate(metrics, word_timestamp_count=0)
        self.assertFalse(valid)
        self.assertTrue(any("timestamps" in blocker for blocker in blockers), blockers)

    def test_historical_policy_remains_immutable_but_is_superseded(self) -> None:
        decision = load_json(
            "internal/earnalism_intelligence/"
            "sprint1_audiobook_acceptance_v3_90_policy_decision.json"
        )
        policy = load_json(
            "internal/earnalism_intelligence/audiobook_acceptance_policy.json"
        )
        self.assertEqual(decision["policy_name"], SPRINT1_AUDIOBOOK_90_POLICY)
        self.assertEqual(decision["listening_gate"]["overall_listening_score_min"], 9.0)
        self.assertEqual(
            decision["objective_gates_unchanged"]["asr_manuscript_score_min"], 9.7
        )
        self.assertEqual(decision["release_ready_delta_at_policy_activation"], 0)
        self.assertFalse(decision["public_state_mutated"])
        self.assertIn("full-title", decision["publication_rule"])

        historical = policy[SPRINT1_AUDIOBOOK_90_POLICY]
        self.assertEqual(historical["representative_or_full_book_listening_score_min"], 9.0)
        self.assertEqual(historical["confidence_score_min"], 0.9)
        self.assertTrue(historical["objective_gates_remain_strict"])
        self.assertEqual(historical["status"], "SUPERSEDED_FOR_NEW_EVALUATIONS")
        self.assertEqual(
            policy[BENGALI_AUDIOBOOK_92_POLICY]["status"],
            "SUPERSEDED_FOR_NEW_EVALUATIONS",
        )


if __name__ == "__main__":
    unittest.main()
