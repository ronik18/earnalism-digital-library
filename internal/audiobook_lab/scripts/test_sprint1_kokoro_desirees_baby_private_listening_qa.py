#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import wave


MODULE_PATH = Path(__file__).with_name("sprint1_kokoro_desirees_baby_private_listening_qa.py")
SPEC = importlib.util.spec_from_file_location("desiree_listening", MODULE_PATH)
assert SPEC and SPEC.loader
qa = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qa)


class DesireeListeningQATests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        private_root = qa.ROOT / "internal/audiobook_lab/private_runs"
        private_root.mkdir(parents=True, exist_ok=True)
        self.private_tmp = tempfile.TemporaryDirectory(prefix="test-desiree-listening-", dir=private_root)
        self.addCleanup(self.private_tmp.cleanup)
        private = Path(self.private_tmp.name)
        samples, reports, bindings = [], [], {}
        for index, passage_id in enumerate(qa.EXPECTED_SAMPLE_BINDINGS):
            audio = private / f"{passage_id}.wav"
            with wave.open(str(audio), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(24_000)
                handle.writeframes((index + 1).to_bytes(2, "little", signed=True) * 2_400)
            audio_hash = qa.sha256_file(audio)
            source_hash = hashlib.sha256(passage_id.encode()).hexdigest()
            binding = {
                "source_text_sha256": source_hash,
                "audio_sha256": audio_hash,
                "size_bytes": audio.stat().st_size,
                "duration_seconds": 0.1,
            }
            bindings[passage_id] = binding
            samples.append({"passage_id": passage_id, "audio_path": str(audio), **binding})
            reports.append(
                {
                    "passage_id": passage_id,
                    "audio_sha256": audio_hash,
                    "source_text_sha256": source_hash,
                    "score": 10.0,
                    "coverage": 1.0,
                    "first_words_match": True,
                    "last_words_match": True,
                    "ordered_content_integrity_pass": True,
                    "no_missing_content": True,
                    "no_duplicate_content": True,
                    "no_reordered_content": True,
                    "no_unexpected_content": True,
                    "pass": True,
                }
            )
        self.evidence = root / "evidence.json"
        self.payload = {
            "status": qa.EXPECTED_STATUS,
            "catalog_binding": {
                "slug": qa.SLUG,
                "title": qa.TITLE,
                "author": qa.AUTHOR,
                "language": qa.LANGUAGE,
                "reader_live": True,
                "audio_hidden": True,
                "normalized_source_sha256": "s" * 64,
            },
            "attempt": {"fingerprint": "a" * 64},
            "execution": {
                "execution_fingerprint": "e" * 64,
                "samples": samples,
                "asr_repair": {
                    "status": "PASS",
                    "audio_derived": True,
                    "repair_fingerprint": "r" * 64,
                    "reports": reports,
                },
            },
        }
        self.evidence.write_text(json.dumps(self.payload), encoding="utf-8")
        self.output = root / "output.json"
        self.lock = root / "paid_tts.lock"
        self.lock.write_text(json.dumps({"status": "active", "current_holder": "none", "allowed_next_holders": []}) + "\n")
        self.lock_before = self.lock.read_bytes()
        self.env = {**qa.EXPECTED_ENV, "OPENAI_API_KEY": "not-used"}
        patches = [
            mock.patch.object(qa, "EXPECTED_EVIDENCE_SHA256", qa.sha256_file(self.evidence)),
            mock.patch.object(qa, "EXPECTED_SOURCE_SHA256", "s" * 64),
            mock.patch.object(qa, "EXPECTED_ATTEMPT_FINGERPRINT", "a" * 64),
            mock.patch.object(qa, "EXPECTED_EXECUTION_FINGERPRINT", "e" * 64),
            mock.patch.object(qa, "EXPECTED_ASR_REPAIR_FINGERPRINT", "r" * 64),
            mock.patch.object(qa, "EXPECTED_SAMPLE_BINDINGS", bindings),
            mock.patch.object(qa, "ffprobe_duration", return_value=0.1),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    @staticmethod
    def judgment(score: float = 9.2, confidence: float = 0.9, fatal: bool = False):
        def judge(_client, _args, sample):
            scores = {
                field: (confidence if field == "confidence_score" else score)
                for field in qa.LISTENING_THRESHOLDS
            }
            return {
                **sample,
                "scores": scores,
                "judge_flags": {
                    field: fatal and field == "robotic_texture_detected"
                    for field in qa.BINARY_LISTENING_FLAGS
                },
                "frontmatter_present": False,
                "blocker_reason": "",
            }

        return judge

    def test_transport_invalid_zeroes_are_not_reported_as_quality_scores(self) -> None:
        valid = self.judgment(score=8.0, confidence=0.9, fatal=True)(
            None,
            None,
            {"sample_label": "maternal_dialogue", "passage_id": "maternal_dialogue"},
        )
        invalid = [
            {
                "sample_label": passage_id,
                "passage_id": passage_id,
                "scores": {field: 0.0 for field in qa.LISTENING_THRESHOLDS},
                "judge_flags": {},
                "blocker_reason": "No audio provided for evaluation.",
            }
            for passage_id in ("opening_names", "accusation_dialogue", "final_revelation")
        ]
        gate = qa.evaluate_judgments([invalid[0], valid, invalid[1], invalid[2]])
        self.assertEqual(gate["transport_valid_sample_count"], 1)
        self.assertEqual(gate["transport_invalid_sample_count"], 3)
        self.assertFalse(gate["transport_invalid_zeroes_are_quality_scores"])
        self.assertEqual(gate["minimum_scores"]["overall_listening_score"], 8.0)
        self.assertIn("robotic_texture_detected", gate["fatal_flags"])
        self.assertFalse(gate["platform_screen_pass"])

    def test_dry_run_binds_four_samples_without_provider_or_lock_write(self) -> None:
        code, result = qa.execute(self.evidence, self.output, self.lock, dry_run=True, env=self.env)
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "DRY_RUN_PASS")
        self.assertEqual(result["sample_count"], 4)
        self.assertFalse(result["provider_calls_ran"])
        self.assertEqual(self.lock.read_bytes(), self.lock_before)

    def test_missing_approval_or_api_key_blocks_before_evidence_call(self) -> None:
        env = dict(self.env)
        env.pop("OPENAI_API_KEY")
        calls = []
        code, result = qa.execute(
            self.evidence,
            self.output,
            self.lock,
            env=env,
            judge=lambda *args: calls.append(args),
        )
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "BLOCKED_RUNTIME_GATES")
        self.assertEqual(calls, [])

    def test_budget_above_twenty_cents_blocks(self) -> None:
        env = dict(self.env)
        env["MAX_TTS_BUDGET_USD"] = "0.21"
        code, result = qa.execute(self.evidence, self.output, self.lock, env=env)
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "BLOCKED_RUNTIME_GATES")

    def test_platform_cutoff_passes_without_exact_ten(self) -> None:
        code, result = qa.execute(
            self.evidence,
            self.output,
            self.lock,
            env=self.env,
            judge=self.judgment(),
            client_factory=object,
        )
        self.assertEqual(code, 0)
        self.assertTrue(result["listening_gate"]["platform_screen_pass"])
        self.assertFalse(result["listening_gate"]["owner_exact_10_observed"])
        self.assertTrue(result["listening_gate"]["next_private_stage_authorized"])
        self.assertEqual(self.lock.read_bytes(), self.lock_before)

    def test_fatal_flag_blocks_even_above_cutoff(self) -> None:
        code, result = qa.execute(
            self.evidence,
            self.output,
            self.lock,
            env=self.env,
            judge=self.judgment(10.0, 0.99, fatal=True),
            client_factory=object,
        )
        self.assertEqual(code, 3)
        self.assertFalse(result["listening_gate"]["platform_screen_pass"])
        self.assertEqual(self.lock.read_bytes(), self.lock_before)

    def test_repeat_fingerprint_blocks_before_provider(self) -> None:
        _, _, fingerprint = qa.load_evidence(self.evidence)
        self.output.write_text(json.dumps({"sample_fingerprint": fingerprint, "provider_calls_ran": True}))
        calls = []
        code, result = qa.execute(
            self.evidence,
            self.output,
            self.lock,
            env=self.env,
            judge=lambda *args: calls.append(args),
        )
        self.assertEqual(code, 4)
        self.assertEqual(result["status"], "BLOCKED_REPEAT_ATTEMPT")
        self.assertEqual(calls, [])

    def test_public_audio_path_is_rejected(self) -> None:
        with self.assertRaisesRegex(qa.DesireeListeningQAError, "outside private_runs|public"):
            qa.assert_private_audio(qa.ROOT / "frontend/public/sample.wav")


if __name__ == "__main__":
    unittest.main()
