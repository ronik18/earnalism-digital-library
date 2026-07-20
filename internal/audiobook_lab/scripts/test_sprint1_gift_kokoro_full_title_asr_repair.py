#!/usr/bin/env python3
"""Focused tests for the retained-WAV Gift full-title ASR-only repair."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_gift_kokoro_full_title_asr_repair.py")
SPEC = importlib.util.spec_from_file_location("gift_full_asr_repair", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GiftFullTitleASRRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name) / "repair.json"
        _chapter, _manuscript, sections = MODULE.FULL.controlled_source(MODULE.ROOT)
        self.sections = {str(item["passage_id"]): item for item in sections}

    def result_for(self, sample, transcript=None, invalid_word_index=None):
        text = transcript
        if text is None:
            text = str(self.sections[str(sample["passage_id"])]["text"])
        raw_words = text.split()
        duration = float(sample["duration_seconds"])
        step = min(0.2, max(0.02, duration / (len(raw_words) + 2)))
        words = []
        for index, word in enumerate(raw_words):
            start = round(index * step, 6)
            end = round(start + step * 0.8, 6)
            if invalid_word_index == index:
                end = start
            words.append(
                {"word": f" {word}", "start": start, "end": end, "probability": 0.99}
            )
        return {"text": text, "segments": [{"words": words}]}

    def exact_decoder(self, _model, _arm, sample):
        return self.result_for(sample)

    def test_input_binds_rejected_report_and_all_retained_audio(self) -> None:
        evidence, samples, sections = MODULE.validate_input(MODULE.DEFAULT_INPUT)
        self.assertEqual(evidence["status"], MODULE.EXPECTED_INPUT_STATUS)
        self.assertEqual(len(samples), 19)
        self.assertEqual(len(sections), 19)
        self.assertEqual(
            evidence["engine"]["attempt_fingerprint"],
            MODULE.EXPECTED_GENERATION_FINGERPRINT,
        )
        self.assertEqual(MODULE.sha256_file(MODULE.DEFAULT_INPUT), MODULE.EXPECTED_INPUT_SHA256)
        self.assertTrue(all(Path(item["audio_path"]).is_file() for item in samples))

    def test_repair_fingerprint_is_new_and_binds_distinct_unprompted_arms(self) -> None:
        evidence = MODULE.read_json(MODULE.DEFAULT_INPUT)
        fingerprint = MODULE.repair_fingerprint(evidence)
        self.assertEqual(len(fingerprint), 64)
        self.assertNotEqual(fingerprint, MODULE.EXPECTED_GENERATION_FINGERPRINT)
        beam, greedy = MODULE.DECODING_ARMS
        self.assertIsNone(beam["initial_prompt"])
        self.assertEqual(beam["beam_size"], 10)
        self.assertIsNone(greedy["initial_prompt"])
        self.assertIsNone(greedy["beam_size"])
        self.assertEqual(greedy["best_of"], 1)

    def test_owner_authorized_equivalences_require_exact_counts(self) -> None:
        source = (
            "letter box airshaft some day Sofronie practised chaste stair away "
            "discreet Dell jewelled forty 22 a hundred"
        )
        transcript = (
            "letterbox air shaft someday Sifroni practiced chased stairway "
            "discrete Del jeweled 40 twenty-two 100"
        )
        evaluated_source, evaluated_transcript, applied, rejected = (
            MODULE.apply_exact_count_equivalences(source, transcript)
        )
        self.assertEqual(rejected, [])
        self.assertEqual(
            MODULE.FULL.representative.ordered_token_integrity(
                evaluated_source, evaluated_transcript
            )["score"],
            10.0,
        )
        self.assertEqual(len(applied), 13)

        _source, _transcript, _applied, rejected = (
            MODULE.apply_exact_count_equivalences(
                "letter box beside another letter box", "one letterbox"
            )
        )
        self.assertEqual(rejected[0]["reason"], "EXACT_COUNT_MISMATCH")

    def test_substantive_pairs_are_never_normalized(self) -> None:
        cases = (
            ("appertaining thereunto", "appurting thereunto", "appertaining_appurting"),
            ("a pier glass", "a pure glass", "pier_pure"),
            ("I'm me without my hair", "I mean without my hair", "im_me_i_mean"),
            ("I want to see it", "I wanna see it", "want_to_wanna"),
            ("keep 'em a while", "keep them a while", "em_them"),
        )
        for source, transcript, expected in cases:
            with self.subTest(expected):
                metrics = MODULE.alignment_metrics(source, transcript)
                self.assertFalse(metrics["alignment_pass"])
                self.assertEqual(
                    metrics["forbidden_equivalences_detected"][0]["equivalence"],
                    expected,
                )
                self.assertFalse(metrics["forbidden_equivalences_normalized"])

    def test_unrelated_substitute_word_does_not_trigger_false_forbidden_pair(self) -> None:
        source = "Keep 'em over there and leave them alone."
        detected = MODULE.detect_forbidden_equivalences(source, source)
        self.assertEqual(detected, [])

    def test_trailing_hallucination_and_timestamp_anomaly_fail(self) -> None:
        _evidence, samples, sections = MODULE.validate_input(MODULE.DEFAULT_INPUT)
        sample = samples[1]
        section = sections[1]
        hallucinated = self.result_for(
            sample, f"{section['text']} Thank you for watching."
        )
        report = MODULE.evaluate_result(section, sample, hallucinated, "test")
        self.assertTrue(report["trailing_hallucination_detected"])
        self.assertFalse(report["pass"])

        sample = samples[2]
        section = sections[2]
        anomalous = self.result_for(sample, invalid_word_index=2)
        report = MODULE.evaluate_result(section, sample, anomalous, "test")
        self.assertFalse(report["word_timestamp_evidence_valid"])
        self.assertFalse(report["pass"])

    def test_dry_run_does_not_load_model_or_write(self) -> None:
        # The production ledger correctly closes this completed fingerprint.
        # Isolate the dry-run mechanics here; the dedicated no-repeat test
        # below exercises the real guard explicitly.
        with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
            code, result = MODULE.execute(
                MODULE.DEFAULT_INPUT,
                self.output,
                MODULE.DEFAULT_WHISPER_CACHE,
                MODULE.DEFAULT_PAID_LOCK,
                dry_run=True,
                model_loader=lambda _path: self.fail("dry-run loaded Whisper"),
            )
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "DRY_RUN_PASS")
        self.assertFalse(result["asr_performed"])
        self.assertFalse(self.output.exists())

    def test_exact_decoder_pass_preserves_initial_reports_and_recomputes_sync(self) -> None:
        input_before = MODULE.DEFAULT_INPUT.read_bytes()
        initial = json.loads(input_before)
        with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
            code, result = MODULE.execute(
                MODULE.DEFAULT_INPUT,
                self.output,
                MODULE.DEFAULT_WHISPER_CACHE,
                MODULE.DEFAULT_PAID_LOCK,
                model_loader=lambda _path: object(),
                decoder=self.exact_decoder,
            )
        self.assertEqual(code, 0)
        self.assertEqual(
            result["status"], "PRIVATE_FULL_TITLE_ASR_REPAIR_PASS_LISTENING_PENDING"
        )
        self.assertEqual(result["initial_objective_qa"]["asr"], initial["asr"])
        self.assertEqual(result["initial_objective_qa"]["measured_sync"], initial["measured_sync"])
        self.assertTrue(result["measured_sync"]["sync_pass"])
        self.assertTrue(all(item["pass"] for item in result["asr"]["reports"]))
        self.assertTrue(result["asr_repair"]["audio_hashes_unchanged"])
        self.assertTrue(result["scope"]["full_title_generated"])
        self.assertTrue(result["asr_repair"]["fingerprint_closed"])
        self.assertFalse(result["asr_repair"]["resynthesis_performed"])
        self.assertEqual(MODULE.DEFAULT_INPUT.read_bytes(), input_before)

    def test_greedy_arm_can_repair_beam_hallucination_without_text_deletion(self) -> None:
        calls = []

        def decoder(_model, arm, sample):
            calls.append((arm["id"], sample["passage_id"]))
            section = self.sections[str(sample["passage_id"])]
            if (
                sample["passage_id"] == "section-002"
                and arm["id"] == MODULE.DECODING_ARMS[0]["id"]
            ):
                return self.result_for(
                    sample, f"{section['text']} Thank you for watching."
                )
            return self.result_for(sample)

        with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
            code, result = MODULE.execute(
                MODULE.DEFAULT_INPUT,
                self.output,
                MODULE.DEFAULT_WHISPER_CACHE,
                MODULE.DEFAULT_PAID_LOCK,
                model_loader=lambda _path: object(),
                decoder=decoder,
            )
        self.assertEqual(code, 0)
        selected = result["asr_repair"]["selected_decoder_by_section"]
        self.assertEqual(selected["section-002"], MODULE.DECODING_ARMS[1]["id"])
        self.assertIn((MODULE.DECODING_ARMS[1]["id"], "section-002"), calls)
        self.assertFalse(result["asr_repair"]["manual_transcript_deletion_performed"])

    def test_repeated_closed_fingerprint_is_rejected_before_model_load(self) -> None:
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
            with self.assertRaisesRegex(MODULE.GiftASRRepairError, "fingerprint is closed"):
                MODULE.execute(
                    MODULE.DEFAULT_INPUT,
                    self.output,
                    MODULE.DEFAULT_WHISPER_CACHE,
                    MODULE.DEFAULT_PAID_LOCK,
                    model_loader=lambda _path: self.fail("repeat loaded model"),
                    decoder=self.exact_decoder,
                )

    def test_input_hash_drift_and_public_output_fail_closed(self) -> None:
        mutated = copy.deepcopy(MODULE.read_json(MODULE.DEFAULT_INPUT))
        mutated["samples"][0]["audio_sha256"] = "0" * 64
        drifted = Path(self.temporary.name) / "drifted.json"
        drifted.write_text(json.dumps(mutated), encoding="utf-8")
        with self.assertRaisesRegex(MODULE.GiftASRRepairError, "input evidence SHA-256"):
            MODULE.validate_input(drifted)
        with self.assertRaisesRegex(MODULE.GiftASRRepairError, "public output"):
            MODULE.execute(
                MODULE.DEFAULT_INPUT,
                MODULE.ROOT / "frontend/public/audio/gift-repair.json",
                MODULE.DEFAULT_WHISPER_CACHE,
                MODULE.DEFAULT_PAID_LOCK,
                dry_run=True,
            )


if __name__ == "__main__":
    unittest.main()
