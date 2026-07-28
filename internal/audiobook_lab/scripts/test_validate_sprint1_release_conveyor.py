#!/usr/bin/env python3
"""Tests for the deterministic Sprint 1 release conveyor."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys
import unittest


SCRIPT = Path(__file__).with_name("validate_sprint1_release_conveyor.py")
SPEC = importlib.util.spec_from_file_location("validate_sprint1_release_conveyor", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ReleaseConveyorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = MODULE.load(MODULE.DEFAULT_CONVEYOR)

    def test_authoritative_conveyor_passes(self) -> None:
        result = MODULE.validate(self.payload)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["unique_sprint1_slugs"], 32)
        self.assertEqual(result["production_live"], 4)
        self.assertEqual(result["audio_hidden"], 28)
        self.assertEqual(result["selected_attempts_consumed"], 0)

    def test_duplicate_slug_fails(self) -> None:
        changed = copy.deepcopy(self.payload)
        changed["routes"]["one_bounded_targeted_repair_then_source_bound_delivery"].append(
            "the-gift-of-the-magi"
        )
        with self.assertRaisesRegex(RuntimeError, "appears in both"):
            MODULE.validate(changed)

    def test_attempt_cap_cannot_be_widened(self) -> None:
        changed = copy.deepcopy(self.payload)
        changed["finite_attempt_contract"][
            "new_synthetic_model_families_per_title_max"
        ] = 2
        with self.assertRaisesRegex(RuntimeError, "must be exactly one"):
            MODULE.validate(changed)

    def test_release_floor_cannot_be_relaxed(self) -> None:
        changed = copy.deepcopy(self.payload)
        changed["release_gates"]["asr_manuscript_score_min"] = 9.0
        with self.assertRaisesRegex(RuntimeError, "release gate changed"):
            MODULE.validate(changed)

    def test_preprovider_failure_cannot_consume_or_spend_attempt(self) -> None:
        changed = copy.deepcopy(self.payload)
        changed["active_title"]["provider_calls_ran"] = True
        with self.assertRaisesRegex(RuntimeError, "cannot record provider calls"):
            MODULE.validate(changed)

        changed = copy.deepcopy(self.payload)
        changed["active_title"]["actual_provider_spend_usd"] = 0.01
        with self.assertRaisesRegex(RuntimeError, "cannot record provider spend"):
            MODULE.validate(changed)


if __name__ == "__main__":
    unittest.main()
