#!/usr/bin/env python3
"""Focused tests for The Time Machine retained-WAV ASR repair."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sprint1_time_machine_bm_george_asr_repair.py")
SPEC = importlib.util.spec_from_file_location("time_machine_asr_repair", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TimeMachineASRRepairTests(unittest.TestCase):
    def test_contract_fingerprint_and_decoder_arms_are_pinned(self) -> None:
        self.assertEqual(
            MODULE.repair_fingerprint(), MODULE.EXPECTED_REPAIR_FINGERPRINT
        )
        self.assertEqual(
            [item["id"] for item in MODULE.DECODING_ARMS],
            [
                "unprompted_beam_2",
                "unprompted_greedy",
                "canonical_vocabulary_beam_2",
            ],
        )
        self.assertTrue(
            all(
                item["condition_on_previous_text"] is False
                for item in MODULE.DECODING_ARMS
            )
        )

    def test_only_spelling_and_compound_equivalences_are_allowed(self) -> None:
        evaluated, applications = MODULE.CORE.apply_equivalences(
            "epilogue_tenderness", "civilization and shriveled"
        )
        self.assertEqual(evaluated, "civilisation and shrivelled")
        self.assertEqual(len(applications), 2)
        evaluated, applications = MODULE.CORE.apply_equivalences(
            "eloi_first_contact", "like nine pins but I and this"
        )
        self.assertEqual(evaluated, "like ninepins but I and this")
        self.assertEqual(len(applications), 1)

    def test_missing_or_substituted_words_are_not_rewritten(self) -> None:
        transcript = "ironing this fragile thing on an Oolitic coral reef"
        evaluated, applications = MODULE.CORE.apply_equivalences(
            "epilogue_tenderness", transcript
        )
        self.assertEqual(evaluated, transcript)
        self.assertEqual(applications, [])

    def test_exact_source_passes_and_unexpected_speech_fails(self) -> None:
        _source, passages = MODULE.PROFILE.controlled_source(
            MODULE.ROOT, MODULE.PROFILE.SLUG
        )
        passage = next(
            item for item in passages if item["passage_id"] == "opening_exposition"
        )
        sample = {
            "audio_sha256": MODULE.EXPECTED_SAMPLE_BINDINGS[
                "opening_exposition"
            ]["audio_sha256"]
        }
        exact = MODULE.evaluate_transcript(passage, sample, passage["text"], "test")
        self.assertTrue(exact["pass"])
        trailing = MODULE.evaluate_transcript(
            passage, sample, passage["text"] + " Thank you.", "test"
        )
        self.assertFalse(trailing["pass"])
        self.assertFalse(trailing["unexpected_speech_deleted_or_normalized"])

    def test_input_and_private_wavs_are_exactly_bound(self) -> None:
        first_audio = Path(
            str(MODULE.CORE.read_json(MODULE.DEFAULT_INPUT)["samples"][0]["audio_path"])
        )
        self.assertTrue(first_audio.is_file())
        evidence, samples, passages = MODULE.validate_input(MODULE.DEFAULT_INPUT)
        self.assertEqual(evidence["status"], MODULE.EXPECTED_INPUT_STATUS)
        self.assertEqual(len(samples), 4)
        self.assertEqual(len(passages), 4)
        self.assertTrue(all(item["objective_format_pass"] for item in samples))


if __name__ == "__main__":
    unittest.main()
