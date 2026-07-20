#!/usr/bin/env python3
"""Tests for the bounded Gift bf_emma retained-WAV ASR repair."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_gift_bf_emma_asr_repair.py")
SPEC = importlib.util.spec_from_file_location("gift_bf_emma_asr_repair", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GiftEmmaASRRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / "repair.json"

    def exact_decoder(self, _model, _arm, sample):
        _chapter, passages = MODULE.PROFILE.controlled_source(
            MODULE.ROOT, MODULE.PROFILE.SLUG
        )
        by_id = {str(item["passage_id"]): str(item["text"]) for item in passages}
        return by_id[str(sample["passage_id"])]

    def execute_isolated(self, decoder):
        with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
            return MODULE.execute(
                MODULE.DEFAULT_INPUT,
                self.output,
                MODULE.DEFAULT_WHISPER_CACHE,
                MODULE.DEFAULT_PAID_LOCK,
                model_loader=lambda _path: object(),
                decoder=decoder,
            )

    def test_input_binds_exact_retained_wavs_and_prior_transcripts(self) -> None:
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

    def test_equivalences_are_exact_count_and_source_bound(self) -> None:
        opening, applied = MODULE.apply_equivalences(
            "opening_money", "$1.87 then $1.87"
        )
        self.assertEqual(
            opening,
            "one dollar and eighty-seven cents then one dollar and eighty-seven cents",
        )
        self.assertEqual(len(applied), 1)
        hair, applied = MODULE.apply_equivalences(
            "hair_sale_dialogue", "Take your hat off. She was chilli."
        )
        self.assertEqual(hair, "Take yer hat off. She was chilly.")
        self.assertEqual(len(applied), 2)
        with self.assertRaisesRegex(MODULE.GiftEmmaASRRepairError, "count mismatch"):
            MODULE.apply_equivalences("opening_money", "Only $1.87 once")
        with self.assertRaisesRegex(MODULE.GiftEmmaASRRepairError, "count mismatch"):
            MODULE.apply_equivalences(
                "hair_sale_dialogue", "chilli once and chilli twice; take your hat"
            )

    def test_substantive_and_unexpected_speech_are_never_normalized(self) -> None:
        ending = "these two are the wisest"
        evaluated, applications = MODULE.apply_equivalences("magi_ending", ending)
        self.assertEqual(evaluated, ending)
        self.assertEqual(applications, [])
        opening = "And next day would be Christmas. this."
        evaluated, applications = MODULE.apply_equivalences("opening_money", opening)
        self.assertEqual(evaluated, opening)
        self.assertEqual(applications, [])
        hair = "Give it to me quick. The end."
        evaluated, applications = MODULE.apply_equivalences(
            "hair_sale_dialogue", hair
        )
        self.assertEqual(evaluated, hair)
        self.assertEqual(applications, [])

    def test_fingerprint_binds_both_unprompted_arms_and_forbidden_policy(self) -> None:
        self.assertEqual(
            MODULE.repair_fingerprint(),
            "804d06f2f84ce24a2af4a5e92039d8c28019a782dbe11df958fef91c16647193",
        )
        self.assertNotEqual(
            MODULE.repair_fingerprint(), MODULE.EXPECTED_PRIOR_ASR_FINGERPRINT
        )
        self.assertEqual(
            [arm["id"] for arm in MODULE.DECODING_ARMS],
            ["unprompted_beam_2", "unprompted_greedy"],
        )
        self.assertTrue(
            all(arm["initial_prompt"] is None for arm in MODULE.DECODING_ARMS)
        )
        self.assertIn("were/are", MODULE.FORBIDDEN_NORMALIZATIONS)

    def test_dry_run_does_not_load_whisper_or_write_output(self) -> None:
        with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
            code, result = MODULE.execute(
                MODULE.DEFAULT_INPUT,
                self.output,
                MODULE.DEFAULT_WHISPER_CACHE,
                MODULE.DEFAULT_PAID_LOCK,
                dry_run=True,
                model_loader=lambda _path: self.fail("dry run loaded Whisper"),
            )
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "DRY_RUN_PASS")
        self.assertTrue(result["both_arms_will_run_for_every_passage"])
        self.assertFalse(result["asr_performed"])
        self.assertFalse(self.output.exists())

    def test_exact_audio_derived_transcripts_pass_and_run_all_eight_decodes(self) -> None:
        calls: list[tuple[str, str]] = []

        def decoder(model, arm, sample):
            calls.append((str(arm["id"]), str(sample["passage_id"])))
            return self.exact_decoder(model, arm, sample)

        before = MODULE._audio_hashes(MODULE.validate_input(MODULE.DEFAULT_INPUT)[1])
        code, result = self.execute_isolated(decoder)
        after = MODULE._audio_hashes(MODULE.validate_input(MODULE.DEFAULT_INPUT)[1])
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 8)
        self.assertEqual(
            result["status"],
            "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA",
        )
        self.assertTrue(all(item["score"] == 10.0 for item in result["asr"]["reports"]))
        self.assertEqual(before, after)
        self.assertTrue(result["asr_repair"]["retained_audio_immutable"])
        self.assertFalse(result["asr_repair"]["resynthesis_performed"])
        self.assertFalse(result["asr_repair"]["audio_edit_or_trim_performed"])
        self.assertEqual(
            {key: len(value) for key, value in result["asr_repair"]["all_candidates"].items()},
            {key: 2 for key in MODULE.EXPECTED_SAMPLE_BINDINGS},
        )

    def test_forbidden_hallucinations_and_were_are_fail_closed(self) -> None:
        def bad_decoder(model, arm, sample):
            transcript = self.exact_decoder(model, arm, sample)
            passage_id = sample["passage_id"]
            if passage_id == "opening_money":
                return transcript + " this."
            if passage_id == "hair_sale_dialogue":
                return transcript + " The end."
            if passage_id == "magi_ending":
                return transcript.replace("these two were the wisest", "these two are the wisest")
            return transcript

        code, result = self.execute_isolated(bad_decoder)
        self.assertEqual(code, 4)
        self.assertEqual(
            result["status"],
            "PRIVATE_REPRESENTATIVE_ASR_REPAIR_FAILED_FINGERPRINT_CLOSED",
        )
        failed = {
            report["passage_id"]: report
            for report in result["asr"]["reports"]
            if not report["pass"]
        }
        self.assertEqual(set(failed), {"opening_money", "hair_sale_dialogue", "magi_ending"})
        self.assertFalse(failed["opening_money"]["no_unexpected_content"])
        self.assertFalse(failed["hair_sale_dialogue"]["no_unexpected_content"])
        self.assertIn("were", failed["magi_ending"]["missing_tokens"])
        self.assertFalse(result["asr_repair"]["substantive_were_are_normalized"])
        self.assertFalse(
            result["asr_repair"]["unexpected_speech_deleted_or_normalized"]
        )

    def test_completed_output_fingerprint_cannot_repeat(self) -> None:
        with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
            code, _result = MODULE.execute(
                MODULE.DEFAULT_INPUT,
                self.output,
                MODULE.DEFAULT_WHISPER_CACHE,
                MODULE.DEFAULT_PAID_LOCK,
                model_loader=lambda _path: object(),
                decoder=self.exact_decoder,
            )
            self.assertEqual(code, 0)
            with self.assertRaisesRegex(
                MODULE.GiftEmmaASRRepairError, "already completed"
            ):
                MODULE.execute(
                    MODULE.DEFAULT_INPUT,
                    self.output,
                    MODULE.DEFAULT_WHISPER_CACHE,
                    MODULE.DEFAULT_PAID_LOCK,
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
                MODULE.GiftEmmaASRRepairError, "fingerprint already exists"
            ):
                MODULE.execute(
                    MODULE.DEFAULT_INPUT,
                    self.output,
                    MODULE.DEFAULT_WHISPER_CACHE,
                    MODULE.DEFAULT_PAID_LOCK,
                    model_loader=lambda _path: self.fail("repeat loaded model"),
                    decoder=self.exact_decoder,
                )

    def test_public_output_is_rejected(self) -> None:
        with self.assertRaisesRegex(MODULE.GiftEmmaASRRepairError, "public output"):
            MODULE.execute(
                MODULE.DEFAULT_INPUT,
                MODULE.ROOT / "frontend/public/audio/gift-emma-repair.json",
                MODULE.DEFAULT_WHISPER_CACHE,
                MODULE.DEFAULT_PAID_LOCK,
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
                MODULE.GiftEmmaASRRepairError, "sample audio_sha256"
            ):
                MODULE.validate_input(local_input)

    def test_paid_lock_change_during_decode_fails_closed(self) -> None:
        local_lock = self.root / "paid_tts.lock"
        local_lock.write_bytes(MODULE.DEFAULT_PAID_LOCK.read_bytes())
        changed = False

        def decoder(model, arm, sample):
            nonlocal changed
            if not changed:
                local_lock.write_bytes(local_lock.read_bytes() + b"\n")
                changed = True
            return self.exact_decoder(model, arm, sample)

        with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
            with self.assertRaisesRegex(
                MODULE.GiftEmmaASRRepairError, "paid lock SHA-256 after repair"
            ):
                MODULE.execute(
                    MODULE.DEFAULT_INPUT,
                    self.output,
                    MODULE.DEFAULT_WHISPER_CACHE,
                    local_lock,
                    model_loader=lambda _path: object(),
                    decoder=decoder,
                )

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
        self.assertEqual(
            result["safety"]["paid_tts_lock_before_sha256"],
            result["safety"]["paid_tts_lock_after_sha256"],
        )
        self.assertFalse(result["safety"]["audio_generated_during_repair"])
        self.assertTrue(result["safety"]["asr_run"])
        self.assertFalse(result["safety"]["upload_performed"])
        self.assertFalse(result["safety"]["publication_performed"])
        self.assertFalse(result["safety"]["release_gate_mutated"])


if __name__ == "__main__":
    unittest.main()
