#!/usr/bin/env python3
"""Focused tests for the retained-WAV Secret Garden ASR repair contract."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sprint1_secret_garden_kokoro_asr_repair.py")
SPEC = importlib.util.spec_from_file_location("secret_garden_asr_repair", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SecretGardenASRRepairTests(unittest.TestCase):
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
            all(item["condition_on_previous_text"] is False for item in MODULE.DECODING_ARMS)
        )

    def test_only_two_acoustic_token_splits_are_normalized(self) -> None:
        evaluated, applications = MODULE.CORE.apply_equivalences(
            "yorkshire_dialogue", "Can a tha dress thy sen; they said thee."
        )
        self.assertEqual(evaluated, "canna tha dress thysen; they said thee.")
        self.assertEqual(len(applications), 2)
        self.assertNotIn("they", " ".join(item["replacement"] for item in applications))
        self.assertNotIn("thee", " ".join(item["replacement"] for item in applications))

    def test_substantive_dialect_or_trailing_speech_is_not_rewritten(self) -> None:
        transcript = "Was going to dress me; they said the. Please. Thank you."
        evaluated, applications = MODULE.CORE.apply_equivalences(
            "yorkshire_dialogue", transcript
        )
        self.assertEqual(evaluated, transcript)
        self.assertEqual(applications, [])

    def test_exact_source_passes_and_unexpected_speech_fails(self) -> None:
        _source, passages = MODULE.PROFILE.controlled_source(
            MODULE.ROOT, MODULE.PROFILE.SLUG
        )
        passage = next(item for item in passages if item["passage_id"] == "ending_return")
        sample = {
            "audio_sha256": MODULE.EXPECTED_SAMPLE_BINDINGS["ending_return"][
                "audio_sha256"
            ]
        }
        exact = MODULE.evaluate_transcript(passage, sample, passage["text"], "test")
        self.assertTrue(exact["pass"])
        trailing = MODULE.evaluate_transcript(
            passage, sample, passage["text"] + " Thank you.", "test"
        )
        self.assertFalse(trailing["pass"])
        self.assertFalse(trailing["unexpected_speech_deleted_or_normalized"])

    def test_input_and_private_wavs_are_exactly_bound_when_present(self) -> None:
        first_audio = Path(
            str(
                MODULE.CORE.read_json(MODULE.DEFAULT_INPUT)["samples"][0][
                    "audio_path"
                ]
            )
        )
        if not first_audio.is_file():
            self.skipTest("private retained WAVs are intentionally not in the repo")
        evidence, samples, passages = MODULE.validate_input(MODULE.DEFAULT_INPUT)
        self.assertEqual(evidence["status"], MODULE.EXPECTED_INPUT_STATUS)
        self.assertEqual(len(samples), 4)
        self.assertEqual(len(passages), 4)
        self.assertTrue(all(item["objective_format_pass"] for item in samples))


if __name__ == "__main__":
    unittest.main()
