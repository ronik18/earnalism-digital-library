#!/usr/bin/env python3
"""Tests for the bounded Gift VoxCPM2 v3.90 representative runner."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


SCRIPT = Path(__file__).with_name("sprint1_gift_voxcpm2_v390_representative.py")
SPEC = importlib.util.spec_from_file_location("gift_voxcpm2_v390", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class GiftVoxCPM2V390Tests(unittest.TestCase):
    def test_default_is_one_adversarial_section(self) -> None:
        self.assertEqual(MODULE.DEFAULT_SECTION_INDICES, (13,))
        self.assertIn(13, MODULE.REPRESENTATIVE_SECTION_INDICES)

    def test_non_representative_section_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            MODULE.GiftVoxCPM2Error,
            "non-representative section",
        ):
            MODULE.parse_section_indices("2")

    def test_reference_only_command_has_no_instruction_or_prompt(self) -> None:
        command = MODULE.speech_command(
            speech_bin=Path("/opt/homebrew/bin/speech"),
            reference_audio=Path("/private/tmp/reference.wav"),
            output=Path("/private/tmp/output.wav"),
            text="Exact controlled text.",
        )
        rendered = " ".join(command)
        self.assertIn("--engine voxcpm2", rendered)
        self.assertIn("--voxcpm2-variant int8", rendered)
        self.assertIn("--voxcpm2-ref-audio", rendered)
        self.assertNotIn("--voxcpm2-instruct", rendered)
        self.assertNotIn("--voxcpm2-prompt-text", rendered)
        self.assertNotIn("--voxcpm2-prompt-audio", rendered)

    def test_fingerprint_changes_with_source_hash(self) -> None:
        reference = Path("/private/tmp/reference.wav")
        first = {
            "passage_id": "section-013",
            "section_index": 13,
            "text_sha256": "a" * 64,
        }
        second = {**first, "text_sha256": "b" * 64}
        self.assertNotEqual(
            MODULE.attempt_fingerprint([first], reference),
            MODULE.attempt_fingerprint([second], reference),
        )


if __name__ == "__main__":
    unittest.main()
