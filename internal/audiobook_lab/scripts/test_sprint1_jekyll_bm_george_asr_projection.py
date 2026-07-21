#!/usr/bin/env python3
"""Focused tests for the offline Jekyll bm_george ASR projection."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).with_name("sprint1_jekyll_bm_george_asr_projection.py")
SPEC = importlib.util.spec_from_file_location("jekyll_projection", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class JekyllBmGeorgeProjectionTests(unittest.TestCase):
    def test_projection_fingerprint_is_pinned(self) -> None:
        self.assertEqual(
            MODULE.projection_fingerprint(), MODULE.EXPECTED_PROJECTION_FINGERPRINT
        )

    def test_projection_uses_only_exact_source_equivalences(self) -> None:
        evaluated, applications = MODULE.apply_projection_rules(
            "carew_murder", "recognize him underfoot"
        )
        self.assertEqual(evaluated, "recognise him under foot")
        self.assertEqual(len(applications), 2)
        evaluated, applications = MODULE.apply_projection_rules(
            "lanyon_transformation", "O God and Oh God"
        )
        self.assertEqual(evaluated, "O God and O God")
        self.assertEqual(len(applications), 1)

    def test_substantive_wondering_wandering_is_not_projected(self) -> None:
        evaluated, _applications = MODULE.apply_projection_rules(
            "opening_character", "human beakened and wandering"
        )
        self.assertEqual(evaluated, "human beaconed and wandering")
        self.assertIn("wondering/wandering", MODULE.FORBIDDEN_PROJECTIONS)

    def test_input_binds_four_immutable_private_wavs(self) -> None:
        payload, passages, samples = MODULE.validate_input(MODULE.DEFAULT_INPUT)
        self.assertEqual(payload["status"], MODULE.EXPECTED_INPUT_STATUS)
        self.assertEqual(len(passages), 4)
        self.assertEqual(len(samples), 4)


if __name__ == "__main__":
    unittest.main()
