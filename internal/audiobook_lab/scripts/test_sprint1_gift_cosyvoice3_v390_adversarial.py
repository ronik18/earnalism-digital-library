#!/usr/bin/env python3
"""Truth and no-repeat tests for the bounded Gift CosyVoice3 pilot."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR))

import sprint1_gift_cosyvoice3_v390_adversarial as pilot  # noqa: E402


class GiftCosyVoice3ContractTests(unittest.TestCase):
    def test_command_uses_exact_model_and_no_reference_voice(self) -> None:
        command = pilot.command_for(
            speech_bin=Path("/opt/homebrew/bin/speech"),
            model_dir=Path("/private/tmp/cosy-model"),
            output=Path("/private/tmp/sample.wav"),
            text="Exact source text.",
        )
        self.assertEqual(command[:3], ["/opt/homebrew/bin/speech", "speak", "--engine"])
        self.assertIn("cosyvoice", command)
        self.assertIn(pilot.MODEL_ID, command)
        self.assertIn("--cosy-bundle-dir", command)
        self.assertNotIn("--voice-sample", command)
        self.assertNotIn("--cosy-reference-transcript", command)

    def test_reopening_is_one_sample_private_and_non_human(self) -> None:
        path = (
            ROOT
            / "internal/audiobook_lab/sprint1_publication/title_runs/"
            "the-gift-of-the-magi_cosyvoice3_reopening_v1.json"
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            payload["decision"],
            "AUTHORIZE_ONE_PRIVATE_COSYVOICE3_BF16_ADVERSARIAL_SAMPLE",
        )
        self.assertEqual(payload["exact_scope"]["maximum_generated_samples"], 1)
        self.assertTrue(payload["exact_scope"]["private_only"])
        self.assertFalse(payload["rights"]["human_voice_reference_used"])
        self.assertEqual(payload["public_audio_status"], "AUDIO_HIDDEN")

    def test_completed_evidence_failed_closed_before_listening(self) -> None:
        path = (
            ROOT
            / "internal/audiobook_lab/sprint1_publication/title_runs/"
            "the-gift-of-the-magi_cosyvoice3_bf16_v390_section13_20260728.json"
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        aggregate = payload["objective_qa"]["full_title_aggregate"]
        self.assertEqual(
            payload["status"],
            "PRIVATE_COSYVOICE3_ADVERSARIAL_OBJECTIVE_FAIL_AUDIO_HIDDEN",
        )
        self.assertGreaterEqual(aggregate["score"], 9.7)
        self.assertGreaterEqual(aggregate["coverage"], 0.98)
        self.assertFalse(aggregate["first_words_match"])
        self.assertFalse(aggregate["ordered_content_integrity_pass"])
        self.assertEqual(payload["cost"]["listening_provider_calls"], 0)
        self.assertFalse(payload["release_eligible"])
        self.assertEqual(payload["safety"]["public_audio_status"], "AUDIO_HIDDEN")
        self.assertTrue(payload["safety"]["paid_tts_lock_unchanged"])
        self.assertFalse(payload["safety"]["uploaded"])
        self.assertFalse(payload["safety"]["published"])
        self.assertFalse(payload["safety"]["release_gate_mutated"])

    def test_completed_fingerprint_cannot_repeat(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "unused.json"
            with self.assertRaisesRegex(
                pilot.GiftCosyVoiceError,
                "attempt fingerprint already exists",
            ):
                pilot.ensure_not_repeated(
                    "559d94ef386b741ee489d5dcbfd9df71686cbe9ac634801879d2978afbdcad25",
                    output,
                )


if __name__ == "__main__":
    unittest.main()
