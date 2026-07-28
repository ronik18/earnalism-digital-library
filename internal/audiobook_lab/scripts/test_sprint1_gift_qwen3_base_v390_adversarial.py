#!/usr/bin/env python3
"""Tests for the Gift Qwen3 Base v3.90 adversarial runner."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("sprint1_gift_qwen3_base_v390_adversarial.py")
SPEC = importlib.util.spec_from_file_location("gift_qwen3_base_v390", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class GiftQwen3BaseV390Tests(unittest.TestCase):
    def test_command_is_base_voice_clone_without_instruction(self) -> None:
        command = MODULE.qwen_command(
            speech_bin=Path("/opt/homebrew/bin/speech"),
            reference_audio=Path("/private/tmp/reference.wav"),
            output=Path("/private/tmp/output.wav"),
            text="Exact controlled text.",
        )
        rendered = " ".join(command)
        self.assertIn("--engine qwen3", rendered)
        self.assertIn("--model base-8bit", rendered)
        self.assertIn("--voice-sample", rendered)
        self.assertNotIn("--instruct", rendered)
        self.assertNotIn("customVoice", rendered)

    def test_configuration_is_materially_distinct_from_voice_design(self) -> None:
        self.assertEqual(MODULE.MODEL_ID, "aufklarer/Qwen3-TTS-12Hz-0.6B-Base-MLX-8bit")
        self.assertEqual(MODULE.SETTINGS["voice_sample_only"], True)
        self.assertIsNone(MODULE.SETTINGS["instruction"])

    def test_fingerprint_changes_with_source(self) -> None:
        section = {
            "passage_id": "section-013",
            "text_sha256": "a" * 64,
        }
        changed = {**section, "text_sha256": "b" * 64}
        reference = Path("/private/tmp/reference.wav")
        self.assertNotEqual(
            MODULE.attempt_fingerprint(section, reference),
            MODULE.attempt_fingerprint(changed, reference),
        )

    def test_clipped_pcm_is_not_objective_format_pass(self) -> None:
        import numpy as np
        import soundfile as sf

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "clipped.wav"
            samples = np.full(24_000, 32_767, dtype=np.int16)
            sf.write(path, samples, MODULE.SAMPLE_RATE, subtype="PCM_16")
            metrics = MODULE.wav_metrics(path)
        self.assertFalse(metrics["objective_format_pass"])
        self.assertGreater(metrics["clipped_sample_fraction"], 0)

    def test_recovery_is_bound_to_exact_failed_output_hash(self) -> None:
        self.assertEqual(
            MODULE.RECOVERABLE_OUTPUT_SHA256,
            "da573f24abea837e30a5a8b2ac9d1082f692c66661f17a2e3589840bd29729bf",
        )


if __name__ == "__main__":
    unittest.main()
