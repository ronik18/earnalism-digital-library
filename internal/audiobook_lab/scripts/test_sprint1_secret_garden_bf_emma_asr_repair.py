#!/usr/bin/env python3
"""Focused tests for the Secret Garden bf_emma retained-WAV repair."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name(
    "sprint1_secret_garden_bf_emma_asr_repair.py"
)
SPEC = importlib.util.spec_from_file_location("secret_garden_bf_repair", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SecretGardenBfEmmaASRRepairTests(unittest.TestCase):
    def test_repair_fingerprint_and_three_arms_are_pinned(self) -> None:
        self.assertEqual(
            MODULE.repair_fingerprint(), MODULE.EXPECTED_REPAIR_FINGERPRINT
        )
        self.assertEqual(len(MODULE.DECODING_ARMS), 3)
        self.assertTrue(
            all(item["condition_on_previous_text"] is False for item in MODULE.DECODING_ARMS)
        )

    def test_input_wavs_and_prior_transcripts_are_exactly_bound(self) -> None:
        evidence, samples, passages = MODULE.CORE.validate_input(MODULE.DEFAULT_INPUT)
        self.assertEqual(evidence["status"], MODULE.EXPECTED_INPUT_STATUS)
        self.assertEqual(len(samples), 4)
        self.assertEqual(len(passages), 4)
        self.assertTrue(all(item["objective_format_pass"] for item in samples))

    def test_only_context_bound_token_splits_are_allowed(self) -> None:
        evaluated, applications = MODULE.CORE.apply_equivalences(
            "yorkshire_dialogue", "Can a tha dress thy sen and wait on thy sen."
        )
        self.assertEqual(evaluated, "canna tha dress thysen and wait on thysen.")
        self.assertEqual(len(applications), 3)
        unsafe = "Was going; they said the. Thanks for watching."
        observed, applications = MODULE.CORE.apply_equivalences(
            "yorkshire_dialogue", unsafe
        )
        self.assertEqual(observed, unsafe)
        self.assertEqual(applications, [])

    def test_completed_repair_is_closed_and_evidence_preserves_safety(self) -> None:
        with self.assertRaisesRegex(
            MODULE.CORE.GiftEmmaASRRepairError,
            "exact ASR-only repair already completed|fingerprint already exists",
        ):
            MODULE.execute(
                MODULE.DEFAULT_INPUT,
                MODULE.DEFAULT_OUTPUT,
                MODULE.DEFAULT_WHISPER_CACHE,
                MODULE.DEFAULT_PAID_LOCK,
                dry_run=True,
            )
        result = MODULE.CORE.read_json(MODULE.DEFAULT_OUTPUT)
        self.assertEqual(
            result["status"],
            "PRIVATE_REPRESENTATIVE_ASR_REPAIR_FAILED_FINGERPRINT_CLOSED",
        )
        self.assertTrue(result["asr_repair"]["retained_audio_immutable"])
        self.assertFalse(result["safety"]["upload_performed"])
        self.assertFalse(result["safety"]["publication_performed"])


if __name__ == "__main__":
    unittest.main()
