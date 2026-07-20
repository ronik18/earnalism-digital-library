#!/usr/bin/env python3
"""Tests for the bounded Last Leaf retained-WAV ASR repair."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_last_leaf_kokoro_asr_repair.py")
SPEC = importlib.util.spec_from_file_location("last_leaf_asr_repair", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LastLeafASRRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / "repair.json"

    def exact_decoder(self, _model, _arm, sample):
        _chapter, passages = MODULE.PROFILE.controlled_source(MODULE.ROOT, MODULE.SLUG)
        by_id = {str(item["passage_id"]): str(item["text"]) for item in passages}
        return by_id[str(sample["passage_id"])]

    def execute_isolated(self, decoder):
        with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
            return MODULE.execute(
                MODULE.DEFAULT_INPUT,
                self.output,
                MODULE.DEFAULT_WHISPER_CACHE,
                model_loader=lambda _path: object(),
                decoder=decoder,
            )

    def test_input_is_bound_to_exact_retained_wavs_and_prior_transcripts(self) -> None:
        evidence, samples, passages = MODULE.validate_input(MODULE.DEFAULT_INPUT)
        self.assertEqual(
            evidence["asr"]["config_fingerprint"],
            MODULE.EXPECTED_PRIOR_ASR_FINGERPRINT,
        )
        self.assertEqual(len(samples), 4)
        self.assertEqual(len(passages), 4)
        self.assertEqual(
            {item["passage_id"]: item["audio_sha256"] for item in samples},
            {
                key: value["audio_sha256"]
                for key, value in MODULE.EXPECTED_SAMPLE_BINDINGS.items()
            },
        )

    def test_equivalences_are_source_bound_and_exact_count(self) -> None:
        dialect, applied = MODULE.apply_equivalences(
            "behrman_dialect_emotion",
            (
                "der people watched as leafs de drop. I haff not heard. "
                "Vy de you allow dot silly pizness? Ock dot poor little Miss Johnsy."
            ),
        )
        self.assertEqual(
            dialect,
            (
                "dere people watched as leafs dey drop. I haf not heard. "
                "Vy de you allow dot silly pusiness? ach dot poor lettle Miss Johnsy."
            ),
        )
        self.assertEqual(len(applied), 6)
        final, final_applied = MODULE.apply_equivalences(
            "final_masterpiece_reveal", "Mr. Behrman died of pneumonia today in the hospital."
        )
        self.assertEqual(
            final, "Mr. Behrman died of pneumonia to day in the hospital."
        )
        self.assertEqual(len(final_applied), 1)
        with self.assertRaisesRegex(MODULE.LastLeafASRRepairError, "count mismatch"):
            MODULE.apply_equivalences(
                "final_masterpiece_reveal",
                "pneumonia today in one version; pneumonia today in another",
            )

    def test_forbidden_differences_are_never_normalized_or_deleted(self) -> None:
        dialogue = "Didn't the doctor tell you? Thank you."
        evaluated, rules = MODULE.apply_equivalences(
            "johnsy_leaf_dialogue", dialogue
        )
        self.assertEqual(evaluated, dialogue)
        self.assertEqual(rules, [])

        dialect = "Vy de you allow it to come and der prain?"
        evaluated, rules = MODULE.apply_equivalences(
            "behrman_dialect_emotion", dialect
        )
        self.assertEqual(evaluated, dialect)
        self.assertEqual(rules, [])

        duplicated = "colors mixed on it. it, and look out the window"
        evaluated, rules = MODULE.apply_equivalences(
            "final_masterpiece_reveal", duplicated
        )
        self.assertEqual(evaluated, duplicated)
        self.assertEqual(rules, [])

    def test_fingerprint_binds_unprompted_decoders_and_forbidden_policy(self) -> None:
        self.assertEqual(
            MODULE.repair_fingerprint(),
            "6af4f78de1ff7aef48d178d3ae46d535ce9ad968cde190e4257c0cff16742312",
        )
        self.assertNotEqual(
            MODULE.repair_fingerprint(), MODULE.EXPECTED_PRIOR_ASR_FINGERPRINT
        )
        self.assertEqual(
            [arm["id"] for arm in MODULE.DECODING_ARMS],
            ["unprompted_beam_2", "unprompted_greedy_fallback"],
        )
        self.assertTrue(all(arm["initial_prompt"] is None for arm in MODULE.DECODING_ARMS))

    def test_dry_run_never_loads_whisper_or_writes_output(self) -> None:
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
        self.assertFalse(result["audio_edit_or_trim_performed"])
        self.assertFalse(self.output.exists())

    def test_exact_audio_derived_transcripts_pass_without_mutating_wavs(self) -> None:
        before = MODULE._audio_hashes(MODULE.validate_input(MODULE.DEFAULT_INPUT)[1])
        code, result = self.execute_isolated(self.exact_decoder)
        after = MODULE._audio_hashes(MODULE.validate_input(MODULE.DEFAULT_INPUT)[1])
        self.assertEqual(code, 0)
        self.assertEqual(
            result["status"],
            "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA",
        )
        self.assertTrue(all(item["score"] == 10.0 for item in result["asr"]["reports"]))
        self.assertTrue(all(item["pass"] for item in result["asr"]["reports"]))
        self.assertEqual(before, after)
        self.assertTrue(result["asr_repair"]["retained_audio_immutable"])
        self.assertFalse(result["asr_repair"]["resynthesis_performed"])
        self.assertFalse(result["asr_repair"]["audio_edit_or_trim_performed"])

    def test_forbidden_extra_speech_fails_and_all_candidates_are_retained(self) -> None:
        def bad_decoder(model, arm, sample):
            transcript = self.exact_decoder(model, arm, sample)
            if sample["passage_id"] == "johnsy_leaf_dialogue":
                return transcript + " Thank you."
            return transcript

        code, result = self.execute_isolated(bad_decoder)
        self.assertEqual(code, 4)
        self.assertEqual(
            result["status"],
            "PRIVATE_REPRESENTATIVE_ASR_REPAIR_FAILED_FINGERPRINT_CLOSED",
        )
        report = next(
            item
            for item in result["asr"]["reports"]
            if item["passage_id"] == "johnsy_leaf_dialogue"
        )
        self.assertFalse(report["no_unexpected_content"])
        self.assertFalse(report["pass"])
        self.assertEqual(
            len(result["asr_repair"]["all_candidates"]["johnsy_leaf_dialogue"]),
            2,
        )
        self.assertFalse(
            result["asr_repair"]["unexpected_speech_deleted_or_normalized"]
        )

    def test_completed_output_fingerprint_cannot_repeat(self) -> None:
        with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
            code, _result = MODULE.execute(
                MODULE.DEFAULT_INPUT,
                self.output,
                MODULE.DEFAULT_WHISPER_CACHE,
                model_loader=lambda _path: object(),
                decoder=self.exact_decoder,
            )
            self.assertEqual(code, 0)
            with self.assertRaisesRegex(
                MODULE.LastLeafASRRepairError, "already completed"
            ):
                MODULE.execute(
                    MODULE.DEFAULT_INPUT,
                    self.output,
                    MODULE.DEFAULT_WHISPER_CACHE,
                    model_loader=lambda _path: self.fail("repeat loaded model"),
                    decoder=self.exact_decoder,
                )

    def test_isolated_no_repeat_ledger_blocks_before_model_load(self) -> None:
        ledger = self.root / "ledger.json"
        ledger.write_text(
            json.dumps(
                {"history": [{"asr_repair_fingerprint": MODULE.repair_fingerprint()}]}
            ),
            encoding="utf-8",
        )
        with mock.patch.object(MODULE, "NO_REPEAT_FILES", (ledger,)):
            with self.assertRaisesRegex(
                MODULE.LastLeafASRRepairError, "fingerprint already exists"
            ):
                MODULE.execute(
                    MODULE.DEFAULT_INPUT,
                    self.output,
                    MODULE.DEFAULT_WHISPER_CACHE,
                    model_loader=lambda _path: self.fail("repeat loaded model"),
                    decoder=self.exact_decoder,
                )

    def test_public_output_is_rejected(self) -> None:
        with self.assertRaisesRegex(MODULE.LastLeafASRRepairError, "public output"):
            MODULE.execute(
                MODULE.DEFAULT_INPUT,
                MODULE.ROOT / "frontend/public/audio/last-leaf-repair.json",
                MODULE.DEFAULT_WHISPER_CACHE,
                dry_run=True,
            )

    def test_audio_hash_drift_fails_before_decoder(self) -> None:
        payload = json.loads(MODULE.DEFAULT_INPUT.read_text(encoding="utf-8"))
        mutated = copy.deepcopy(payload)
        mutated["samples"][0]["audio_sha256"] = "0" * 64
        local_input = self.root / "input.json"
        local_input.write_text(json.dumps(mutated), encoding="utf-8")
        with mock.patch.object(
            MODULE,
            "EXPECTED_INPUT_SHA256",
            MODULE.PROFILE.BASE.sha256_file(local_input),
        ):
            with self.assertRaisesRegex(
                MODULE.LastLeafASRRepairError, "sample audio_sha256"
            ):
                MODULE.validate_input(local_input)

    @unittest.skipUnless(
        MODULE.DEFAULT_OUTPUT.is_file(), "real repair evidence not generated yet"
    )
    def test_real_repair_evidence_is_closed_and_fail_closed(self) -> None:
        result = json.loads(MODULE.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertIn(
            result["status"],
            {
                "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA",
                "PRIVATE_REPRESENTATIVE_ASR_REPAIR_FAILED_FINGERPRINT_CLOSED",
            },
        )
        self.assertEqual(
            result["asr_repair"]["repair_fingerprint"], MODULE.repair_fingerprint()
        )
        self.assertTrue(result["asr_repair"]["fingerprint_closed"])
        self.assertTrue(result["asr_repair"]["retained_audio_immutable"])
        if result["asr"]["status"] == "FAIL":
            self.assertEqual(
                result["next_stage_contract"]["status"],
                "ASR_REPAIR_FINGERPRINT_CLOSED_OBJECTIVE_FAIL",
            )
            self.assertIsNone(result["next_stage_contract"]["exact_execute_command"])
            self.assertFalse(result["next_stage_contract"]["listening_qa_allowed"])
        self.assertFalse(result["safety"]["audio_generated_during_repair"])
        self.assertFalse(result["safety"]["upload_performed"])
        self.assertFalse(result["safety"]["publication_performed"])
        self.assertFalse(result["safety"]["release_gate_mutated"])


if __name__ == "__main__":
    unittest.main()
