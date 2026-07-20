#!/usr/bin/env python3
"""Tests for the bounded Masque retained-WAV ASR-only repair."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_masque_kokoro_asr_repair.py")
SPEC = importlib.util.spec_from_file_location("masque_kokoro_asr_repair", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MasqueASRRepairTests(unittest.TestCase):
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

    def test_input_binds_exact_evidence_wavs_and_prior_transcripts(self) -> None:
        evidence, samples, passages = MODULE.validate_input(MODULE.DEFAULT_INPUT)
        self.assertEqual(
            MODULE.PROFILE.BASE.sha256_file(MODULE.DEFAULT_INPUT),
            MODULE.EXPECTED_INPUT_SHA256,
        )
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
        evaluated, applied = MODULE.apply_equivalences(
            "black_room_blood_light", "color and color around firelight"
        )
        self.assertEqual(evaluated, "colour and colour around fire light")
        self.assertEqual(len(applied), 2)
        evaluated, applied = MODULE.apply_equivalences(
            "final_confrontation_and_dominion", "revelers and revelers"
        )
        self.assertEqual(evaluated, "revellers and revellers")
        self.assertEqual(len(applied), 1)
        with self.assertRaisesRegex(MODULE.MasqueASRRepairError, "count mismatch"):
            MODULE.apply_equivalences("black_room_blood_light", "one color")
        with self.assertRaisesRegex(MODULE.MasqueASRRepairError, "count mismatch"):
            MODULE.apply_equivalences(
                "final_confrontation_and_dominion", "one revelers"
            )

    def test_harken_and_trailing_you_are_never_normalized(self) -> None:
        missing_harken = "to to the sound"
        evaluated, applied = MODULE.apply_equivalences(
            "ebony_clock_tension", missing_harken
        )
        self.assertEqual(evaluated, missing_harken)
        self.assertEqual(applied, [])
        trailing_you = "the incidents of half an hour. you"
        evaluated, applied = MODULE.apply_equivalences(
            "opening_plague_and_prospero", trailing_you
        )
        self.assertEqual(evaluated, trailing_you)
        self.assertEqual(applied, [])

    def test_fingerprint_binds_two_unprompted_arms_and_exact_policy(self) -> None:
        fingerprint = MODULE.repair_fingerprint()
        self.assertEqual(
            fingerprint,
            "f727d85f6d50cf99038f56b2fe826260dc205bf691d3ac65689c32f46f30f133",
        )
        self.assertNotEqual(fingerprint, MODULE.EXPECTED_PRIOR_ASR_FINGERPRINT)
        self.assertEqual(
            [arm["id"] for arm in MODULE.DECODING_ARMS],
            ["unprompted_beam_2", "unprompted_greedy"],
        )
        self.assertTrue(
            all(arm["initial_prompt"] is None for arm in MODULE.DECODING_ARMS)
        )
        self.assertEqual(
            MODULE.FORBIDDEN_NORMALIZATIONS,
            (
                "missing harken",
                "trailing unexpected you",
                "unexpected speech deletion",
            ),
        )

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

    def test_exact_transcripts_pass_and_all_candidates_are_retained(self) -> None:
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
        self.assertEqual(
            {
                key: len(value)
                for key, value in result["asr_repair"]["all_candidates"].items()
            },
            {key: 2 for key in MODULE.EXPECTED_SAMPLE_BINDINGS},
        )
        self.assertTrue(result["asr_repair"]["fingerprint_closed"])

    def test_only_allowed_equivalences_can_pass(self) -> None:
        def decoder(model, arm, sample):
            transcript = self.exact_decoder(model, arm, sample)
            if sample["passage_id"] == "black_room_blood_light":
                transcript = transcript.replace("colour", "color").replace(
                    "fire light", "firelight"
                )
            if sample["passage_id"] == "final_confrontation_and_dominion":
                transcript = transcript.replace("revellers", "revelers")
            return transcript

        code, result = self.execute_isolated(decoder)
        self.assertEqual(code, 0)
        self.assertTrue(all(item["pass"] for item in result["asr"]["reports"]))
        self.assertTrue(
            all(
                not item["missing_harken_normalized"]
                and not item["trailing_unexpected_you_deleted_or_normalized"]
                for item in result["asr"]["reports"]
            )
        )

    def test_missing_harken_and_trailing_you_fail_closed(self) -> None:
        def decoder(model, arm, sample):
            transcript = self.exact_decoder(model, arm, sample)
            if sample["passage_id"] == "opening_plague_and_prospero":
                return transcript + " you"
            if sample["passage_id"] == "ebony_clock_tension":
                return transcript.replace("harken ", "")
            return transcript

        code, result = self.execute_isolated(decoder)
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
        self.assertEqual(
            set(failed), {"opening_plague_and_prospero", "ebony_clock_tension"}
        )
        self.assertFalse(failed["opening_plague_and_prospero"]["no_unexpected_content"])
        self.assertIn("harken", failed["ebony_clock_tension"]["missing_tokens"])
        self.assertFalse(result["asr_repair"]["missing_harken_normalized"])
        self.assertFalse(
            result["asr_repair"]["trailing_unexpected_you_deleted_or_normalized"]
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
                MODULE.MasqueASRRepairError, "already completed"
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
                MODULE.MasqueASRRepairError, "fingerprint already exists"
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
        with self.assertRaisesRegex(MODULE.MasqueASRRepairError, "public output"):
            MODULE.execute(
                MODULE.DEFAULT_INPUT,
                MODULE.ROOT / "frontend/public/audio/masque-repair.json",
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
            MODULE, "EXPECTED_INPUT_SHA256", MODULE.PROFILE.BASE.sha256_file(local_input)
        ):
            with self.assertRaisesRegex(
                MODULE.MasqueASRRepairError, "sample audio_sha256"
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
                MODULE.MasqueASRRepairError, "paid lock SHA-256 after repair"
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
