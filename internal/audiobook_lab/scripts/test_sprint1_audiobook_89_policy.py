#!/usr/bin/env python3
"""Fail-closed regression tests for the active Sprint 1 listening cutoff of 8.9."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HOOK_DIR = ROOT / "internal" / "audiobook_lab" / "scripts" / "factory_hooks"
sys.path.insert(0, str(HOOK_DIR))

from asr_sync_hook import (  # noqa: E402
    BINARY_LISTENING_FLAGS,
    SPRINT1_AUDIOBOOK_89_POLICY,
    LEGACY_UNIVERSAL_LISTENING_POLICY,
    UNIVERSAL_LISTENING_POLICY,
    audio_derived_asr_gate,
    evaluate_listening_evidence,
)


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def scores(overall: float = 8.9) -> dict:
    return {
        "naturalness_score": 8.9,
        "pronunciation_score": 8.9,
        "emotional_expression_score": 8.9,
        "punctuation_pause_score": 8.9,
        "pacing_score": 8.9,
        "continuity_score": 8.9,
        "anti_robotic_texture_score": 8.9,
        "anti_choppy_join_score": 8.9,
        "listener_enjoyment_score": 8.9,
        "overall_listening_score": overall,
        "confidence_score": 0.90,
    }


def clean_flags() -> dict:
    return {name: False for name in BINARY_LISTENING_FLAGS}


class Sprint1Audiobook89PolicyTests(unittest.TestCase):
    def evaluate(self, candidate_scores: dict | None = None, flags: dict | None = None):
        return evaluate_listening_evidence(
            candidate_scores or scores(),
            flags or clean_flags(),
            language="eng",
            release_policy=SPRINT1_AUDIOBOOK_89_POLICY,
        )

    def test_exact_8_9_boundary_passes(self) -> None:
        valid, blockers, policy = self.evaluate()
        self.assertTrue(valid, blockers)
        self.assertEqual(policy["name"], SPRINT1_AUDIOBOOK_89_POLICY)
        self.assertEqual(policy["thresholds"]["overall_listening_score"], 8.9)

    def test_platform_default_uses_8_9_and_legacy_policy_remains_explicit(self) -> None:
        valid, blockers, policy = evaluate_listening_evidence(
            scores(),
            clean_flags(),
            language="eng",
        )
        self.assertTrue(valid, blockers)
        self.assertEqual(policy["name"], UNIVERSAL_LISTENING_POLICY)
        self.assertEqual(policy["thresholds"]["anti_robotic_texture_score"], 8.9)
        valid, blockers, policy = evaluate_listening_evidence(
            scores(),
            clean_flags(),
            language="eng",
            release_policy=LEGACY_UNIVERSAL_LISTENING_POLICY,
        )
        self.assertFalse(valid)
        self.assertEqual(policy["thresholds"]["overall_listening_score"], 9.7)
        self.assertTrue(blockers)

    def test_below_boundary_dimensions_confidence_and_fatal_flags_fail(self) -> None:
        for field, value in (
            ("overall_listening_score", 8.89),
            ("naturalness_score", 8.89),
            ("anti_robotic_texture_score", 8.89),
            ("anti_choppy_join_score", 8.89),
            ("confidence_score", 0.899),
        ):
            with self.subTest(field=field):
                candidate = scores()
                candidate[field] = value
                valid, blockers, _ = self.evaluate(candidate)
                self.assertFalse(valid)
                self.assertTrue(any(field in blocker for blocker in blockers), blockers)
        for flag in BINARY_LISTENING_FLAGS:
            with self.subTest(flag=flag):
                candidate_flags = clean_flags()
                candidate_flags[flag] = True
                valid, blockers, _ = self.evaluate(flags=candidate_flags)
                self.assertFalse(valid)
                self.assertTrue(any(flag in blocker for blocker in blockers), blockers)

    def test_objective_asr_boundary_remains_9_7(self) -> None:
        base = {
            "score": 9.7,
            "coverage": 0.98,
            "token_order_similarity": 0.97,
            "first_words_match": True,
            "last_words_match": True,
            "frontmatter_absent": True,
        }
        valid, blockers = audio_derived_asr_gate(base, word_timestamp_count=1)
        self.assertTrue(valid, blockers)
        valid, blockers = audio_derived_asr_gate(
            {**base, "score": 9.69}, word_timestamp_count=1
        )
        self.assertFalse(valid)
        self.assertTrue(any("9.7" in blocker for blocker in blockers), blockers)

    def test_canonical_and_runtime_policy_surfaces_are_consistent(self) -> None:
        decision = load_json(
            "internal/earnalism_intelligence/"
            "sprint1_audiobook_acceptance_v3_89_policy_decision.json"
        )
        policy = load_json(
            "internal/earnalism_intelligence/audiobook_acceptance_policy.json"
        )
        state = load_json(
            "internal/earnalism_intelligence/bengali_audiobook_campaign_state.json"
        )
        queue = load_json(
            "internal/earnalism_intelligence/bengali_audiobook_campaign_queue.json"
        )
        platform_decision = load_json(
            "internal/earnalism_intelligence/"
            "platform_audiobook_acceptance_v4_89_policy_decision.json"
        )
        impact = load_json(
            "internal/earnalism_intelligence/"
            "platform_audiobook_89_cutoff_impact_report.json"
        )
        self.assertEqual(decision["policy_name"], SPRINT1_AUDIOBOOK_89_POLICY)
        self.assertEqual(decision["listening_gate"]["overall_listening_score_min"], 8.9)
        self.assertEqual(
            decision["listening_gate"]["anti_robotic_texture_score_min"], 8.9
        )
        self.assertEqual(
            decision["listening_gate"]["anti_choppy_join_score_min"], 8.9
        )
        self.assertEqual(
            decision["objective_gates_unchanged"]["asr_manuscript_score_min"], 9.7
        )
        self.assertEqual(decision["release_ready_delta_at_policy_activation"], 0)
        self.assertFalse(decision["public_state_mutated"])
        self.assertEqual(
            policy[SPRINT1_AUDIOBOOK_89_POLICY][
                "representative_or_full_book_listening_score_min"
            ],
            8.9,
        )
        self.assertEqual(
            state["policy_version"], "platform_audiobook_acceptance_v4_89"
        )
        self.assertEqual(state["release_gates"]["goal_score"], 8.9)
        self.assertEqual(
            queue["policy_version"], "platform_audiobook_acceptance_v4_89"
        )
        self.assertEqual(
            policy[UNIVERSAL_LISTENING_POLICY][
                "representative_or_full_book_listening_score_min"
            ],
            8.9,
        )
        self.assertEqual(platform_decision["policy_name"], UNIVERSAL_LISTENING_POLICY)
        self.assertEqual(
            platform_decision["listening_gate"]["anti_choppy_join_score_min"],
            8.9,
        )
        self.assertEqual(
            platform_decision["objective_gates_unchanged"][
                "asr_manuscript_score_min"
            ],
            9.7,
        )
        self.assertEqual(impact["outcome"]["newly_full_title_release_ready"], 0)
        self.assertEqual(impact["outcome"]["newly_published"], 0)

    def test_active_pipeline_surfaces_use_89_policy(self) -> None:
        expected = {
            "internal/audiobook_lab/scripts/sprint1_next_two_audiobook_fastpath.py": (
                "LISTENING_MINIMUM = 8.9",
                '"platform_audiobook_acceptance_v4_89"',
            ),
            "internal/audiobook_lab/scripts/sprint1_google_bengali_full_tts.py": (
                "LISTENING_MINIMUM = 8.9",
            ),
            "internal/audiobook_lab/scripts/build_narration_import_packet.py": (
                "ACTIVE_LISTENING_SCORE_MIN = 8.9",
                "ACTIVE_ANTI_ROBOTIC_TEXTURE_SCORE_MIN = 8.9",
                "ACTIVE_ANTI_CHOPPY_JOIN_SCORE_MIN = 8.9",
            ),
            "internal/audiobook_lab/scripts/release_catalog_factory.py": (
                '"platform_audiobook_acceptance_v4_89"',
            ),
            "internal/audiobook_lab/scripts/sprint1_google_english_private_pipeline.py": (
                "POLICY_MIN_ANTI_ROBOTIC_SCORE = 8.9",
                "POLICY_MIN_ANTI_CHOPPY_SCORE = 8.9",
            ),
            "internal/audiobook_lab/scripts/sprint1_release_packet_builder.py": (
                "listening_minimum = 8.9",
            ),
            "internal/audiobook_lab/scripts/"
            "sprint1_factory_release_evidence_normalizer.py": (
                "listening_minimum = 8.9",
            ),
        }
        for relative_path, fragments in expected.items():
            with self.subTest(path=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8")
                for fragment in fragments:
                    self.assertIn(fragment, source)


if __name__ == "__main__":
    unittest.main()
