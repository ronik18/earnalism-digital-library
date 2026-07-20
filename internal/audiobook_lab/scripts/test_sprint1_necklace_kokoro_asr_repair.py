#!/usr/bin/env python3
"""Tests for the bounded Necklace retained-WAV ASR repair."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_necklace_kokoro_asr_repair.py")
SPEC = importlib.util.spec_from_file_location("necklace_asr_repair", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class NecklaceASRRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / "repair.json"

    def exact_decoder(self, _model, _arm, sample):
        _chapter, passages = MODULE.PROFILE.controlled_source(MODULE.ROOT, MODULE.SLUG)
        by_id = {str(item["passage_id"]): str(item["text"]) for item in passages}
        return by_id[str(sample["passage_id"])]

    def test_input_is_bound_to_exact_retained_wavs_and_prior_raw_transcripts(self) -> None:
        evidence, samples, passages = MODULE.validate_input(MODULE.DEFAULT_INPUT)
        self.assertEqual(evidence["asr"]["config_fingerprint"], MODULE.EXPECTED_PRIOR_ASR_FINGERPRINT)
        self.assertEqual(len(samples), 4)
        self.assertEqual(len(passages), 4)
        self.assertEqual(
            {item["passage_id"]: item["audio_sha256"] for item in samples},
            {key: value["audio_sha256"] for key, value in MODULE.EXPECTED_SAMPLE_BINDINGS.items()},
        )

    def test_equivalences_are_exact_count_and_owner_bounded(self) -> None:
        invitation, applied = MODULE.apply_equivalences(
            "invitation_dialogue", "the theater was empty"
        )
        self.assertEqual(invitation, "the theatre was empty")
        self.assertEqual(len(applied), 1)
        final, applied = MODULE.apply_equivalences(
            "final_ironic_reveal", "Matilde said it was paced and worth 500 francs"
        )
        self.assertEqual(final, "Mathilde said it was paste and worth five hundred francs")
        self.assertEqual(len(applied), 3)
        with self.assertRaisesRegex(MODULE.NecklaceASRRepairError, "count mismatch"):
            MODULE.apply_equivalences(
                "invitation_dialogue", "the theater beside another theater"
            )

    def test_unexpected_women_missing_i_and_has_is_cannot_be_normalized(self) -> None:
        opening, opening_rules = MODULE.apply_equivalences(
            "opening_social_cadence", "source words women source words"
        )
        self.assertEqual(opening, "source words women source words")
        self.assertEqual(opening_rules, [])
        final, final_rules = MODULE.apply_equivalences(
            "final_ironic_reveal", "Brought you back. At last it has ended."
        )
        self.assertEqual(final, "Brought you back. At last it has ended.")
        self.assertEqual(final_rules, [])

    def test_fingerprint_is_new_and_binds_no_prompt_beam_contract(self) -> None:
        fingerprint = MODULE.repair_fingerprint()
        self.assertEqual(
            fingerprint,
            "127ebeb2c482a3c7d316e80570b2a6fe39f95d2c1783e185908795c8b7b169c6",
        )
        self.assertNotEqual(fingerprint, MODULE.EXPECTED_PRIOR_ASR_FINGERPRINT)
        self.assertIsNone(MODULE.DECODING_ARMS[0]["initial_prompt"])
        self.assertEqual(MODULE.DECODING_ARMS[0]["beam_size"], 2)
        self.assertIsNone(MODULE.DECODING_ARMS[1]["initial_prompt"])

    def test_completed_real_repair_remains_fail_closed(self) -> None:
        result = json.loads(MODULE.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "PRIVATE_REPRESENTATIVE_ASR_REPAIR_FAILED")
        self.assertEqual(
            result["asr_repair"]["repair_fingerprint"], MODULE.repair_fingerprint()
        )
        reports = {item["passage_id"]: item for item in result["asr"]["reports"]}
        self.assertTrue(reports["invitation_dialogue"]["pass"])
        self.assertTrue(reports["necklace_loss_panic"]["pass"])
        self.assertFalse(reports["opening_social_cadence"]["pass"])
        self.assertEqual(reports["opening_social_cadence"]["missing_tokens"], {"had": 1})
        self.assertFalse(reports["final_ironic_reveal"]["pass"])
        self.assertEqual(reports["final_ironic_reveal"]["missing_tokens"], {"i": 1, "is": 1})
        self.assertEqual(reports["final_ironic_reveal"]["unexpected_tokens"], {"has": 1})
        self.assertIn("INDEPENDENT_LISTENING_QA_NOT_RUN", result["blockers_to_release"])

    def test_dry_run_never_loads_whisper_or_writes_output(self) -> None:
        # The production ledger correctly closes this repair fingerprint.
        # Isolate that input for the dry-run mechanics; explicit no-repeat
        # tests below retain production-guard coverage.
        with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
            code, result = MODULE.execute(
                MODULE.DEFAULT_INPUT,
                self.output,
                MODULE.DEFAULT_WHISPER_CACHE,
                dry_run=True,
                model_loader=lambda _path: self.fail("dry run loaded Whisper"),
            )
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "DRY_RUN_PASS")
        self.assertFalse(result["asr_performed"])
        self.assertFalse(result["synthesis_performed"])
        self.assertFalse(self.output.exists())

    def test_exact_transcripts_pass_and_preserve_prior_history(self) -> None:
        input_before = MODULE.DEFAULT_INPUT.read_bytes()
        with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
            code, result = MODULE.execute(
                MODULE.DEFAULT_INPUT,
                self.output,
                MODULE.DEFAULT_WHISPER_CACHE,
                model_loader=lambda _path: object(),
                decoder=self.exact_decoder,
            )
        self.assertEqual(code, 0)
        self.assertEqual(
            result["status"],
            "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA",
        )
        self.assertEqual(result["asr_prior_prompted_run"]["status"], "FAIL")
        self.assertTrue(all(item["score"] == 10.0 for item in result["asr"]["reports"]))
        self.assertTrue(all(item["pass"] for item in result["asr"]["reports"]))
        self.assertFalse(result["asr_repair"]["resynthesis_performed"])
        self.assertFalse(result["asr_repair"]["unexpected_speech_deleted_or_normalized"])
        self.assertEqual(MODULE.DEFAULT_INPUT.read_bytes(), input_before)

    def test_extra_word_fails_every_strict_objective_gate(self) -> None:
        def bad_decoder(model, arm, sample):
            transcript = self.exact_decoder(model, arm, sample)
            if sample["passage_id"] == "opening_social_cadence":
                return transcript.replace("She dressed plainly", "women She dressed plainly")
            return transcript

        with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
            code, result = MODULE.execute(
                MODULE.DEFAULT_INPUT,
                self.output,
                MODULE.DEFAULT_WHISPER_CACHE,
                model_loader=lambda _path: object(),
                decoder=bad_decoder,
            )
        self.assertEqual(code, 4)
        self.assertEqual(result["status"], "PRIVATE_REPRESENTATIVE_ASR_REPAIR_FAILED")
        opening = next(
            item for item in result["asr"]["reports"] if item["passage_id"] == "opening_social_cadence"
        )
        self.assertFalse(opening["no_unexpected_content"])
        self.assertFalse(opening["pass"])

    def test_completed_fingerprint_cannot_repeat(self) -> None:
        with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
            code, _result = MODULE.execute(
                MODULE.DEFAULT_INPUT,
                self.output,
                MODULE.DEFAULT_WHISPER_CACHE,
                model_loader=lambda _path: object(),
                decoder=self.exact_decoder,
            )
            self.assertEqual(code, 0)
            with self.assertRaisesRegex(MODULE.NecklaceASRRepairError, "already completed"):
                MODULE.execute(
                    MODULE.DEFAULT_INPUT,
                    self.output,
                    MODULE.DEFAULT_WHISPER_CACHE,
                    model_loader=lambda _path: self.fail("repeat loaded model"),
                    decoder=self.exact_decoder,
                )

    def test_public_output_is_rejected(self) -> None:
        with self.assertRaisesRegex(MODULE.NecklaceASRRepairError, "public output"):
            MODULE.execute(
                MODULE.DEFAULT_INPUT,
                MODULE.ROOT / "frontend/public/audio/necklace-repair.json",
                MODULE.DEFAULT_WHISPER_CACHE,
                dry_run=True,
            )

    def test_audio_hash_drift_fails_before_decoder(self) -> None:
        input_payload = json.loads(MODULE.DEFAULT_INPUT.read_text(encoding="utf-8"))
        mutated = copy.deepcopy(input_payload)
        mutated["samples"][0]["audio_sha256"] = "0" * 64
        local_input = self.root / "input.json"
        local_input.write_text(json.dumps(mutated), encoding="utf-8")
        with mock.patch.object(MODULE, "EXPECTED_INPUT_SHA256", MODULE.PROFILE.BASE.sha256_file(local_input)):
            with self.assertRaisesRegex(MODULE.NecklaceASRRepairError, "sample audio_sha256"):
                MODULE.validate_input(local_input)


if __name__ == "__main__":
    unittest.main()
