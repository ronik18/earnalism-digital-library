#!/usr/bin/env python3
"""Focused tests for Jekyll retained-WAV ASR repair."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sprint1_jekyll_kokoro_asr_repair.py")
SPEC = importlib.util.spec_from_file_location("jekyll_asr_repair", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class JekyllASRRepairTests(unittest.TestCase):
    def test_contract_fingerprints_and_decoder_arms_are_pinned(self) -> None:
        observed: dict[str, str] = {}
        for voice in sorted(MODULE.VOICE_REPAIR_PROFILES):
            MODULE.configure(voice)
            observed[voice] = MODULE.repair_fingerprint()
            self.assertEqual(
                observed[voice],
                MODULE.VOICE_REPAIR_PROFILES[voice]["expected_repair_fingerprint"],
            )
        self.assertEqual(len(set(observed.values())), 2)
        self.assertEqual(
            [item["id"] for item in MODULE.DECODING_ARMS],
            ["unprompted_beam_2", "unprompted_greedy"],
        )

    def test_only_exact_acoustic_equivalences_are_allowed(self) -> None:
        MODULE.configure("bm_george")
        evaluated, applications = MODULE.CORE.apply_equivalences(
            "opening_character", "beakened in the theater"
        )
        self.assertEqual(evaluated, "beaconed in the theatre")
        self.assertEqual(len(applications), 2)
        evaluated, applications = MODULE.CORE.apply_equivalences(
            "carew_murder", "underfoot"
        )
        self.assertEqual(evaluated, "under foot")
        self.assertEqual(len(applications), 1)

    def test_substantive_words_and_unexpected_speech_are_not_rewritten(self) -> None:
        MODULE.configure("am_michael")
        transcript = "beacon in the acts features melt thank you"
        evaluated, applications = MODULE.CORE.apply_equivalences(
            "opening_character", transcript
        )
        self.assertEqual(evaluated, transcript)
        self.assertEqual(applications, [])

    def test_exact_source_passes_and_unexpected_speech_fails(self) -> None:
        MODULE.configure("am_michael")
        _source, passages = MODULE.PROFILE.controlled_source(
            MODULE.ROOT, MODULE.PROFILE.SLUG
        )
        passage = next(
            item for item in passages if item["passage_id"] == "carew_murder"
        )
        sample = {
            "audio_sha256": MODULE.EXPECTED_SAMPLE_BINDINGS["carew_murder"]["audio_sha256"]
        }
        exact = MODULE.evaluate_transcript(passage, sample, passage["text"], "test")
        self.assertTrue(exact["pass"])
        trailing = MODULE.evaluate_transcript(
            passage, sample, passage["text"] + " Thank you.", "test"
        )
        self.assertFalse(trailing["pass"])
        self.assertFalse(trailing["unexpected_speech_deleted_or_normalized"])

    def test_both_inputs_and_private_wavs_are_exactly_bound(self) -> None:
        for voice in sorted(MODULE.VOICE_REPAIR_PROFILES):
            MODULE.configure(voice)
            evidence, samples, passages = MODULE.validate_input(
                MODULE.default_input(voice)
            )
            self.assertEqual(evidence["status"], MODULE.EXPECTED_INPUT_STATUS)
            self.assertEqual(len(samples), 4)
            self.assertEqual(len(passages), 4)
            self.assertTrue(all(item["objective_format_pass"] for item in samples))


if __name__ == "__main__":
    unittest.main()
