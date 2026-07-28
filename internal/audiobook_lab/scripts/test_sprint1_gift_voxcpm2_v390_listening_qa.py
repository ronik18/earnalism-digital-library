#!/usr/bin/env python3
"""Tests for the Gift VoxCPM2 v3.90 adversarial listening gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


SCRIPT = Path(__file__).with_name("sprint1_gift_voxcpm2_v390_listening_qa.py")
SPEC = importlib.util.spec_from_file_location("gift_voxcpm2_v390_listening", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def passing_judgment() -> dict[str, object]:
    value: dict[str, object] = {
        field: threshold
        for field, threshold in MODULE.LISTENING_THRESHOLDS.items()
    }
    value.update({field: False for field in MODULE.BINARY_FLAGS})
    value.update(
        {
            "frontmatter_present": False,
            "notes": "Threshold-quality literary narration.",
            "blocker_reason": "",
        }
    )
    return value


class GiftVoxCPM2V390ListeningTests(unittest.TestCase):
    def test_exact_thresholds_pass(self) -> None:
        gate = MODULE.evaluate(passing_judgment())
        self.assertTrue(gate["listening_pass"])
        self.assertEqual(gate["fatal_flags"], [])
        self.assertEqual(gate["threshold_failures"], {})

    def test_fatal_flag_fails_even_with_scores(self) -> None:
        judgment = passing_judgment()
        judgment["robotic_texture_detected"] = True
        gate = MODULE.evaluate(judgment)
        self.assertFalse(gate["listening_pass"])
        self.assertEqual(gate["fatal_flags"], ["robotic_texture_detected"])

    def test_low_dimension_fails_despite_overall(self) -> None:
        judgment = passing_judgment()
        judgment["overall_listening_score"] = 9.8
        judgment["emotional_expression_score"] = 8.8
        gate = MODULE.evaluate(judgment)
        self.assertFalse(gate["listening_pass"])
        self.assertIn("emotional_expression_score", gate["threshold_failures"])

    def test_one_sample_budget_is_strict(self) -> None:
        env = {
            "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
            "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "0.05",
            "MAX_TTS_BUDGET_USD": "0.05",
        }
        self.assertEqual(MODULE.budget_guard(env)["status"], "PASS")
        env["MAX_TTS_BUDGET_USD"] = "1.00"
        self.assertEqual(MODULE.budget_guard(env)["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
