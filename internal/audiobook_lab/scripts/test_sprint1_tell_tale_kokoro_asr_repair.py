#!/usr/bin/env python3
"""Tests for the bounded Tell-Tale Heart retained-WAV ASR-only repair."""

from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_tell_tale_kokoro_asr_repair.py")
SPEC = importlib.util.spec_from_file_location("tell_tale_kokoro_asr_repair", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPO = MODULE.ROOT
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class TellTaleASRRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name) / "repair.json"

    def exact_decoder(self, _model, _arm, sample):
        _chapter, passages = MODULE.EXECUTOR.PREFLIGHT.controlled_source(
            MODULE.ROOT, MODULE.EXECUTOR.SLUG
        )
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

    def test_input_binds_exact_execution_evidence_and_retained_wavs(self) -> None:
        evidence, samples, passages = MODULE.validate_input(MODULE.DEFAULT_INPUT)
        self.assertEqual(
            MODULE.EXECUTOR.PREFLIGHT.sha256_file(MODULE.DEFAULT_INPUT),
            MODULE.EXPECTED_INPUT_SHA256,
        )
        self.assertEqual(evidence["schema"], MODULE.EXPECTED_INPUT_SCHEMA)
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

    def test_source_equivalence_policy_is_empty_for_every_passage(self) -> None:
        self.assertEqual(
            MODULE.SOURCE_EQUIVALENCE_POLICY,
            {key: () for key in MODULE.EXPECTED_SAMPLE_BINDINGS},
        )
        _chapter, passages = MODULE.EXECUTOR.PREFLIGHT.controlled_source(
            MODULE.ROOT, MODULE.EXECUTOR.SLUG
        )
        by_id = {str(item["passage_id"]): item for item in passages}
        bedroom = by_id["bedroom_suspense_dialogue"]
        sample = MODULE.EXPECTED_SAMPLE_BINDINGS["bedroom_suspense_dialogue"]
        report = MODULE.evaluate_transcript(
            bedroom,
            sample,
            str(bedroom["text"]) + " you",
            "test",
        )
        self.assertEqual(report["source_equivalences_applied"], [])
        self.assertFalse(report["pass"])
        self.assertFalse(report["no_unexpected_content"])

    def test_fingerprint_binds_two_unprompted_arms_and_empty_policy(self) -> None:
        fingerprint = MODULE.repair_fingerprint()
        self.assertEqual(
            fingerprint,
            "6377ce48f1d97e9f8e5cfdd602dce256332c6a6ced7767877a20774578d72533",
        )
        self.assertNotEqual(fingerprint, MODULE.EXPECTED_PRIOR_ASR_FINGERPRINT)
        self.assertEqual(
            [arm["id"] for arm in MODULE.DECODING_ARMS],
            ["unprompted_beam_2", "unprompted_greedy"],
        )
        self.assertTrue(
            all(arm["initial_prompt"] is None for arm in MODULE.DECODING_ARMS)
        )
        self.assertTrue(
            all(
                arm["condition_on_previous_text"] is False
                for arm in MODULE.DECODING_ARMS
            )
        )

    def test_dry_run_does_not_load_whisper_or_write_output(self) -> None:
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
        self.assertTrue(result["both_arms_will_run_for_every_passage"])
        self.assertFalse(result["asr_performed"])
        self.assertFalse(result["paid_coordination_lock_inspected"])
        self.assertFalse(result["paid_coordination_lock_touched"])
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
        self.assertFalse(result["safety"]["paid_coordination_lock_inspected"])

    def test_alternate_exact_decoder_can_resolve_prior_trailing_hallucinations(self) -> None:
        def decoder(model, arm, sample):
            transcript = self.exact_decoder(model, arm, sample)
            if arm["id"] == "unprompted_beam_2":
                if sample["passage_id"] == "bedroom_suspense_dialogue":
                    return transcript + " you"
                if sample["passage_id"] == "final_confession":
                    return transcript + " Thanks for watching."
            return transcript

        code, result = self.execute_isolated(decoder)
        self.assertEqual(code, 0)
        self.assertEqual(
            result["asr_repair"]["selected_decoder_by_passage"]
            ["bedroom_suspense_dialogue"],
            "unprompted_greedy",
        )
        self.assertEqual(
            result["asr_repair"]["selected_decoder_by_passage"]["final_confession"],
            "unprompted_greedy",
        )
        self.assertEqual(
            len(
                result["asr_repair"]["all_candidates"]
                ["bedroom_suspense_dialogue"]
            ),
            2,
        )

    def test_trailing_hallucinations_fail_closed_when_both_arms_retain_them(self) -> None:
        def decoder(model, arm, sample):
            transcript = self.exact_decoder(model, arm, sample)
            if sample["passage_id"] == "bedroom_suspense_dialogue":
                return transcript + " you"
            if sample["passage_id"] == "final_confession":
                return transcript + " Thanks for watching."
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
            set(failed), {"bedroom_suspense_dialogue", "final_confession"}
        )
        self.assertIn("you", failed["bedroom_suspense_dialogue"]["unexpected_tokens"])
        self.assertIn("thanks", failed["final_confession"]["unexpected_tokens"])
        self.assertFalse(result["asr_repair"]["unexpected_speech_deleted_or_normalized"])

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
                MODULE.TellTaleASRRepairError, "already completed"
            ):
                MODULE.execute(
                    MODULE.DEFAULT_INPUT,
                    self.output,
                    MODULE.DEFAULT_WHISPER_CACHE,
                    model_loader=lambda _path: self.fail("repeat loaded model"),
                    decoder=self.exact_decoder,
                )

    def test_isolated_no_repeat_ledger_blocks_before_model_load(self) -> None:
        ledger = Path(self.temporary.name) / "ledger.json"
        ledger.write_text(
            json.dumps(
                {"history": [{"asr_repair_fingerprint": MODULE.repair_fingerprint()}]}
            ),
            encoding="utf-8",
        )
        with mock.patch.object(MODULE, "NO_REPEAT_FILES", (ledger,)):
            with self.assertRaisesRegex(
                MODULE.TellTaleASRRepairError, "fingerprint already exists"
            ):
                MODULE.execute(
                    MODULE.DEFAULT_INPUT,
                    self.output,
                    MODULE.DEFAULT_WHISPER_CACHE,
                    model_loader=lambda _path: self.fail("ledger repeat loaded model"),
                    decoder=self.exact_decoder,
                )

    def test_audio_mutation_is_detected_after_decoding(self) -> None:
        expected = {
            key: value["audio_sha256"]
            for key, value in MODULE.EXPECTED_SAMPLE_BINDINGS.items()
        }
        changed = dict(expected)
        changed["opening_unreliable_sanity"] = "0" * 64
        with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()), mock.patch.object(
            MODULE, "_audio_hashes", side_effect=[expected, changed]
        ):
            with self.assertRaisesRegex(
                MODULE.TellTaleASRRepairError,
                "retained WAV hashes after ASR changed",
            ):
                MODULE.execute(
                    MODULE.DEFAULT_INPUT,
                    self.output,
                    MODULE.DEFAULT_WHISPER_CACHE,
                    model_loader=lambda _path: object(),
                    decoder=self.exact_decoder,
                )

    def test_public_paths_and_cli_paid_lock_surface_are_absent(self) -> None:
        with self.assertRaisesRegex(
            MODULE.TellTaleASRRepairError, "public output path"
        ):
            MODULE.assert_nonpublic(
                REPO / "frontend/public/audio/the-tell-tale-heart-repair.json"
            )
        result = subprocess.run(
            [str(PINNED_PYTHON), str(SCRIPT), "--help"],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("paid-lock", result.stdout)
        self.assertIn("--execute", result.stdout)
        source = inspect.getsource(MODULE.execute)
        self.assertNotIn("paid_lock", source)
        self.assertNotIn("synthesize", source)

    def test_pinned_cli_dry_run_writes_no_evidence_or_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "repair.json"
            program = f"""
import importlib.util
from pathlib import Path
script=Path({str(SCRIPT)!r})
spec=importlib.util.spec_from_file_location('tell_tale_repair_dry',script)
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
module.NO_REPEAT_FILES=()
raise SystemExit(module.main(['--dry-run','--output',{str(output)!r}]))
"""
            result = subprocess.run(
                [str(PINNED_PYTHON), "-c", program],
                cwd=REPO,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "DRY_RUN_PASS")
            self.assertFalse(payload["paid_coordination_lock_inspected"])
            self.assertFalse(output.exists())

    def test_closed_execution_evidence_preserves_exact_fail_safe_result(self) -> None:
        evidence = MODULE.read_json(MODULE.DEFAULT_OUTPUT)
        self.assertEqual(evidence["schema"], MODULE.SCHEMA)
        self.assertEqual(
            evidence["status"],
            "PRIVATE_REPRESENTATIVE_ASR_REPAIR_FAILED_FINGERPRINT_CLOSED",
        )
        self.assertEqual(
            evidence["asr_repair"]["repair_fingerprint"],
            MODULE.repair_fingerprint(),
        )
        self.assertTrue(evidence["asr_repair"]["fingerprint_closed"])
        self.assertTrue(evidence["asr_repair"]["retained_audio_immutable"])
        self.assertEqual(
            {
                key: len(value)
                for key, value in evidence["asr_repair"]["all_candidates"].items()
            },
            {key: 2 for key in MODULE.EXPECTED_SAMPLE_BINDINGS},
        )
        selected = {
            item["passage_id"]: item for item in evidence["asr"]["reports"]
        }
        self.assertTrue(selected["opening_unreliable_sanity"]["pass"])
        self.assertTrue(selected["bedroom_suspense_dialogue"]["pass"])
        self.assertTrue(selected["heartbeat_crescendo"]["pass"])
        self.assertFalse(selected["final_confession"]["pass"])
        self.assertEqual(selected["final_confession"]["score"], 9.8605)
        self.assertEqual(selected["final_confession"]["coverage"], 1.0)
        self.assertEqual(
            selected["final_confession"]["unexpected_tokens"],
            {"for": 1, "thanks": 1, "watching": 1},
        )
        self.assertFalse(evidence["safety"]["paid_coordination_lock_inspected"])
        self.assertFalse(evidence["safety"]["paid_coordination_lock_touched"])
        self.assertFalse(evidence["safety"]["upload_performed"])
        self.assertFalse(evidence["safety"]["publication_performed"])
        self.assertFalse(evidence["safety"]["release_gate_mutated"])


if __name__ == "__main__":
    unittest.main()
