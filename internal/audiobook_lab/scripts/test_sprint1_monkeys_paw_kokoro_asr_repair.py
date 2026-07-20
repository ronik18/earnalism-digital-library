#!/usr/bin/env python3
"""Focused tests for the retained-WAV Monkey's Paw ASR repair."""

from __future__ import annotations

import importlib.util
import inspect
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_monkeys_paw_kokoro_asr_repair.py")
SPEC = importlib.util.spec_from_file_location("monkeys_paw_asr_repair", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPO = MODULE.ROOT
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class MonkeysPawASRRepairTests(unittest.TestCase):
    def test_input_binds_evidence_samples_and_sources(self) -> None:
        evidence, samples, passages = MODULE.validate_input(MODULE.DEFAULT_INPUT)
        self.assertEqual(evidence["status"], MODULE.EXPECTED_INPUT_STATUS)
        self.assertEqual(len(samples), 4)
        self.assertEqual(len(passages), 4)
        self.assertEqual(
            {item["passage_id"]: item["audio_sha256"] for item in samples},
            {
                key: value["audio_sha256"]
                for key, value in MODULE.EXPECTED_SAMPLE_BINDINGS.items()
            },
        )

    def test_repair_fingerprint_is_exact_and_recorded_closed(self) -> None:
        fingerprint = MODULE.repair_fingerprint()
        self.assertEqual(
            fingerprint,
            "7adae43127011aa84218f79a9a4042f9f3e4b723825d04fea2d7ad519fcc7588",
        )
        recorded = set()
        for path in MODULE.NO_REPEAT_FILES:
            if path.is_file():
                recorded.update(
                    MODULE.CORE._find_fingerprints(MODULE.CORE.read_json(path))
                )
        self.assertIn(fingerprint, recorded)

    def test_decoder_matrix_is_bounded_and_retains_all_candidates(self) -> None:
        self.assertEqual(len(MODULE.DECODING_ARMS), 3)
        self.assertEqual(
            {arm["id"] for arm in MODULE.DECODING_ARMS},
            {
                "unprompted_beam_2",
                "unprompted_greedy",
                "canonical_vocabulary_beam_2",
            },
        )
        self.assertTrue(
            all(arm["condition_on_previous_text"] is False for arm in MODULE.DECODING_ARMS)
        )

    def test_only_to_night_tokenization_equivalence_is_allowed(self) -> None:
        evaluated, applications = MODULE.apply_equivalences(
            "opening_domestic_tension", "he would come tonight"
        )
        self.assertEqual(evaluated, "he would come to night")
        self.assertEqual(len(applications), 1)
        for passage_id in (
            "paw_warning_and_fate",
            "factory_news_and_grief",
            "final_knocking_and_third_wish",
        ):
            evaluated, applications = MODULE.apply_equivalences(
                passage_id, "Maw Meggins fuselage ages want"
            )
            self.assertEqual(evaluated, "Maw Meggins fuselage ages want")
            self.assertEqual(applications, [])

    def test_equivalence_count_mismatch_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            MODULE.MonkeysPawASRRepairError, "equivalence count mismatch"
        ):
            MODULE.apply_equivalences(
                "opening_domestic_tension", "tonight tonight"
            )

    def test_exact_transcript_passes_without_substantive_normalization(self) -> None:
        _chapters, passages = MODULE.PROFILE.controlled_source(
            REPO, MODULE.PROFILE.SLUG
        )
        passage = passages[0]
        transcript = passage["text"].replace("to-night", "tonight")
        report = MODULE.evaluate_transcript(
            passage,
            {
                "audio_sha256": MODULE.EXPECTED_SAMPLE_BINDINGS[
                    passage["passage_id"]
                ]["audio_sha256"]
            },
            transcript,
            "mock",
        )
        self.assertIs(report["pass"], True)
        self.assertIs(report["substantive_normalization_performed"], False)
        self.assertIs(report["unexpected_speech_deleted_or_normalized"], False)

    def test_dry_run_checks_lock_and_wavs_without_asr(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "repair.json"
            with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
                code, result = MODULE.execute(
                    MODULE.DEFAULT_INPUT,
                    output,
                    MODULE.DEFAULT_WHISPER_CACHE,
                    MODULE.DEFAULT_PAID_LOCK,
                    dry_run=True,
                    model_loader=lambda _cache: self.fail("model must not load"),
                    decoder=lambda *_args: self.fail("decoder must not run"),
                )
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "DRY_RUN_PASS")
        self.assertIs(result["retained_audio_immutable"], True)
        self.assertIs(result["synthesis_performed"], False)
        self.assertEqual(result["paid_lock_sha256"], MODULE.EXPECTED_PAID_LOCK_SHA256)

    def test_mocked_exact_decoders_advance_only_to_listening(self) -> None:
        _chapters, passages = MODULE.PROFILE.controlled_source(
            REPO, MODULE.PROFILE.SLUG
        )
        source = {item["passage_id"]: item["text"] for item in passages}

        def decoder(_model, _arm, sample):
            return source[sample["passage_id"]]

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "repair.json"
            with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
                code, result = MODULE.execute(
                    MODULE.DEFAULT_INPUT,
                    output,
                    MODULE.DEFAULT_WHISPER_CACHE,
                    MODULE.DEFAULT_PAID_LOCK,
                    model_loader=lambda _cache: object(),
                    decoder=decoder,
                )
        self.assertEqual(code, 0)
        self.assertEqual(
            result["status"],
            "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA",
        )
        self.assertEqual(result["go_no_go"], "GO_PRIVATE_LISTENING_QA_ONLY")
        self.assertEqual(
            sum(len(items) for items in result["asr_repair"]["all_candidates"].values()),
            12,
        )
        self.assertIs(result["next_stage_contract"]["listening_qa_allowed"], True)
        self.assertIs(result["next_stage_contract"]["full_title_generation_allowed"], False)
        self.assertIs(result["safety"]["paid_tts_lock_touched_during_repair"], False)
        self.assertIs(result["safety"]["upload_performed"], False)
        self.assertIs(result["safety"]["publication_performed"], False)

    def test_mocked_substantive_mismatch_fails_closed(self) -> None:
        _chapters, passages = MODULE.PROFILE.controlled_source(
            REPO, MODULE.PROFILE.SLUG
        )
        source = {item["passage_id"]: item["text"] for item in passages}

        def decoder(_model, _arm, sample):
            text = source[sample["passage_id"]]
            return text.replace("fusillade", "fuselage")

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "repair.json"
            with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
                code, result = MODULE.execute(
                    MODULE.DEFAULT_INPUT,
                    output,
                    MODULE.DEFAULT_WHISPER_CACHE,
                    MODULE.DEFAULT_PAID_LOCK,
                    model_loader=lambda _cache: object(),
                    decoder=decoder,
                )
        self.assertEqual(code, 4)
        self.assertEqual(
            result["status"],
            "PRIVATE_REPRESENTATIVE_ASR_REPAIR_FAILED_FINGERPRINT_CLOSED",
        )
        self.assertEqual(
            result["go_no_go"], "NO_GO_REPRESENTATIVE_ASR_REPAIR_FAILED"
        )
        self.assertIn("REPRESENTATIVE_ASR_REPAIR_FAILED", result["blockers_to_release"])
        self.assertIs(result["next_stage_contract"]["listening_qa_allowed"], False)

    def test_module_has_no_synthesis_upload_or_publication_path(self) -> None:
        source = inspect.getsource(MODULE)
        self.assertNotIn("def synthesize", source)
        self.assertNotIn("--upload", source)
        self.assertNotIn("--publish", source)
        self.assertNotIn("speechSynthesis", source)

    def test_cli_surface_is_asr_only(self) -> None:
        result = subprocess.run(
            [str(PINNED_PYTHON), str(SCRIPT), "--help"],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--execute", result.stdout)
        self.assertIn("--dry-run", result.stdout)
        self.assertNotIn("--upload", result.stdout)
        self.assertNotIn("--publish", result.stdout)


if __name__ == "__main__":
    unittest.main()
