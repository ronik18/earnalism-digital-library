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


MODULE_PATH = Path(__file__).with_name("sprint1_gift_kokoro_private_listening_qa.py")
SPEC = importlib.util.spec_from_file_location("sprint1_gift_kokoro_private_listening_qa", MODULE_PATH)
assert SPEC and SPEC.loader
qa = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qa)


class GiftKokoroPrivateListeningQATests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.temp_root = Path(self.temporary.name)
        private_test_root = qa.ROOT / "internal/audiobook_lab/private_runs"
        private_test_root.mkdir(parents=True, exist_ok=True)
        self.private_temporary = tempfile.TemporaryDirectory(
            prefix="test-gift-kokoro-listening-",
            dir=private_test_root,
        )
        self.addCleanup(self.private_temporary.cleanup)
        self.private = Path(self.private_temporary.name)

        self.source_sha256 = "a" * 64
        self.attempt_fingerprint = "b" * 64
        self.asr_config_fingerprint = "c" * 64
        self.bindings: dict[str, dict] = {}
        samples = []
        reports = []
        for index, passage_id in enumerate(
            ("opening_money", "hair_sale_dialogue", "sacrifice_dialogue", "magi_ending")
        ):
            audio = self.private / f"sample-{index}.wav"
            with wave.open(str(audio), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(24_000)
                handle.writeframes((index + 1).to_bytes(2, "little", signed=True) * 2_400)
            audio_hash = qa.sha256_file(audio)
            source_hash = hashlib.sha256(f"source-{index}".encode()).hexdigest()
            binding = {
                "source_text_sha256": source_hash,
                "audio_sha256": audio_hash,
                "size_bytes": audio.stat().st_size,
                "duration_seconds": 0.1,
            }
            self.bindings[passage_id] = binding
            samples.append(
                {
                    "passage_id": passage_id,
                    "source_text_sha256": source_hash,
                    "audio_path": str(audio),
                    "audio_sha256": audio_hash,
                    "size_bytes": audio.stat().st_size,
                    "duration_seconds": 0.1,
                }
            )
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
        self.evidence = self.temp_root / "evidence.json"
        self.evidence_payload = {
            "schema": qa.EXPECTED_SCHEMA,
            "status": qa.EXPECTED_STATUS,
            "scope": {
                "slug": qa.SLUG,
                "title": qa.TITLE,
                "author": qa.AUTHOR,
                "language": qa.LANGUAGE,
                "passage_count": 4,
                "representative_only": True,
                "full_title_generated": False,
            },
            "source": {"source_sha256": self.source_sha256},
            "engine": {
                "package": "kokoro",
                "model_revision": qa.EXPECTED_MODEL_REVISION,
                "voice": "af_bella",
                "voice_sha256": qa.EXPECTED_VOICE_SHA256,
                "attempt_fingerprint": self.attempt_fingerprint,
            },
            "samples": samples,
            "asr": {
                "status": "PASS",
                "audio_derived": True,
                "config_fingerprint": self.asr_config_fingerprint,
                "reports": reports,
            },
        }
        self._write_evidence()
        self.output = self.temp_root / "result.json"
        self.lock = self.temp_root / "paid_tts.lock"
        self.lock.write_text(
            json.dumps({"status": "active", "current_holder": "none", "allowed_next_holders": []}) + "\n",
            encoding="utf-8",
        )
        self.original_lock = self.lock.read_bytes()
        self.env = {**qa.EXPECTED_ENV, "OPENAI_API_KEY": "test-not-used"}

        patches = [
            mock.patch.object(qa, "EXPECTED_EVIDENCE_SHA256", qa.sha256_file(self.evidence)),
            mock.patch.object(qa, "EXPECTED_SOURCE_SHA256", self.source_sha256),
            mock.patch.object(qa, "EXPECTED_ATTEMPT_FINGERPRINT", self.attempt_fingerprint),
            mock.patch.object(qa, "EXPECTED_ASR_CONFIG_FINGERPRINT", self.asr_config_fingerprint),
            mock.patch.object(qa, "EXPECTED_SAMPLE_BINDINGS", self.bindings),
            mock.patch.object(qa, "ffprobe_duration", return_value=0.1),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def _write_evidence(self) -> None:
        self.evidence.write_text(json.dumps(self.evidence_payload), encoding="utf-8")

    @staticmethod
    def judgment(
        quality_score: float = 10.0,
        *,
        overall_score: float | None = None,
        confidence: float = 0.95,
        fatal: bool = False,
    ):
        def _judge(_client, _args, sample):
            scores = {
                field: (confidence if field == "confidence_score" else quality_score)
                for field in qa.LISTENING_THRESHOLDS
            }
            if overall_score is not None:
                scores["overall_listening_score"] = overall_score
            return {
                **sample,
                "scores": scores,
                "confidence": confidence,
                "judge_flags": {
                    field: fatal and field == "robotic_texture_detected"
                    for field in qa.BINARY_LISTENING_FLAGS
                },
                "frontmatter_present": False,
                "raw_judgment": scores,
                "notes": "mock independent judgment",
                "blocker_reason": "",
            }

        return _judge

    def test_default_contract_is_bound_to_exact_current_gift_evidence(self) -> None:
        self.assertEqual(qa.SLUG, "the-gift-of-the-magi")
        self.assertEqual(
            qa.EXPECTED_MODEL_REVISION,
            "f3ff3571791e39611d31c381e3a41a3af07b4987",
        )
        self.assertEqual(
            qa.EXPECTED_VOICE_SHA256,
            "8cb64e02fcc8de0327a8e13817e49c76c945ecf0052ceac97d3081480e8e48d6",
        )
        self.assertEqual(qa.PLATFORM_THRESHOLDS["overall_listening_score"], 9.3)
        self.assertEqual(qa.PLATFORM_THRESHOLDS["confidence_score"], 0.90)

    def test_mismatched_approved_slug_or_scope_blocks_before_judge(self) -> None:
        for name, value in (
            ("EARNALISM_APPROVED_AUDIOBOOK_SLUG", "the-open-window"),
            ("EARNALISM_APPROVED_AUDIOBOOK_SCOPE", "wrong-scope"),
        ):
            with self.subTest(name=name):
                env = dict(self.env)
                env[name] = value
                calls = []
                code, result = qa.execute(
                    self.evidence,
                    self.output,
                    self.lock,
                    env=env,
                    judge=lambda *args: calls.append(args),
                    client_factory=object,
                )
                self.assertEqual(code, 2)
                self.assertEqual(result["status"], "BLOCKED_RUNTIME_GATES")
                self.assertEqual(calls, [])
                self.assertEqual(self.lock.read_bytes(), self.original_lock)

    def test_dry_run_pins_every_sample_without_judge_or_lock_mutation(self) -> None:
        code, result = qa.execute(
            self.evidence,
            self.output,
            self.lock,
            dry_run=True,
            env=self.env,
        )
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "DRY_RUN_PASS")
        self.assertEqual(result["sample_count"], 4)
        self.assertEqual(result["source_sha256"], self.source_sha256)
        self.assertEqual(result["attempt_fingerprint"], self.attempt_fingerprint)
        self.assertEqual(result["asr_config_fingerprint"], self.asr_config_fingerprint)
        self.assertFalse(result["provider_calls_ran"])
        self.assertEqual(self.lock.read_bytes(), self.original_lock)

    def test_asr_score_or_order_drift_fails_closed(self) -> None:
        self.evidence_payload["asr"]["reports"][0]["score"] = 9.9
        self.evidence_payload["asr"]["reports"][0]["ordered_content_integrity_pass"] = False
        self._write_evidence()
        with mock.patch.object(qa, "EXPECTED_EVIDENCE_SHA256", qa.sha256_file(self.evidence)):
            with self.assertRaisesRegex(qa.GiftKokoroListeningQAError, "ASR score"):
                qa.load_evidence(self.evidence)

    def test_platform_pass_without_exact_ten_blocks_next_stage(self) -> None:
        code, result = qa.execute(
            self.evidence,
            self.output,
            self.lock,
            env=self.env,
            judge=self.judgment(9.0, overall_score=9.3, confidence=0.90),
            client_factory=object,
        )
        self.assertEqual(code, 5)
        self.assertTrue(result["listening_gate"]["platform_screen_pass"])
        self.assertFalse(result["listening_gate"]["owner_exact_10_pass"])
        self.assertFalse(result["listening_gate"]["next_private_stage_authorized"])
        self.assertEqual(result["status"], "PRIVATE_GIFT_PLATFORM_PASS_OWNER_EXACT_10_NOT_MET")
        self.assertEqual(self.lock.read_bytes(), self.original_lock)

    def test_exact_ten_pass_still_is_not_release_evidence(self) -> None:
        code, result = qa.execute(
            self.evidence,
            self.output,
            self.lock,
            env=self.env,
            judge=self.judgment(),
            client_factory=object,
        )
        self.assertEqual(code, 0)
        self.assertTrue(result["listening_gate"]["owner_exact_10_pass"])
        self.assertTrue(result["listening_gate"]["next_private_stage_authorized"])
        self.assertFalse(result["full_title_generated"])
        self.assertFalse(result["publication_performed"])
        self.assertIn("FULL_TITLE_NOT_GENERATED", result["release_blockers_preserved"])
        self.assertEqual(self.lock.read_bytes(), self.original_lock)

    def test_fatal_flag_blocks_even_with_exact_scores(self) -> None:
        code, result = qa.execute(
            self.evidence,
            self.output,
            self.lock,
            env=self.env,
            judge=self.judgment(fatal=True),
            client_factory=object,
        )
        self.assertEqual(code, 3)
        self.assertIn("robotic_texture_detected", result["listening_gate"]["fatal_flags"])
        self.assertFalse(result["listening_gate"]["next_private_stage_authorized"])
        self.assertEqual(self.lock.read_bytes(), self.original_lock)

    def test_frontmatter_blocks_even_with_exact_scores(self) -> None:
        judged = self.judgment()(
            None,
            None,
            {"sample_label": "opening_money"},
        )
        judged["frontmatter_present"] = True
        gate = qa.evaluate_judgments([judged, judged, judged, judged])
        self.assertFalse(gate["platform_screen_pass"])
        self.assertIn("opening_money: FRONTMATTER_PRESENT", gate["sample_blockers"])

    def test_budget_cap_must_be_exact_and_provider_error_restores_lock(self) -> None:
        env = dict(self.env)
        env["MAX_TTS_BUDGET_USD"] = "0.21"
        code, result = qa.execute(self.evidence, self.output, self.lock, env=env)
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "BLOCKED_RUNTIME_GATES")
        self.assertEqual(self.lock.read_bytes(), self.original_lock)

        def fail_judge(*_args):
            raise RuntimeError("mock judge failure")

        code, result = qa.execute(
            self.evidence,
            self.output,
            self.lock,
            env=self.env,
            judge=fail_judge,
            client_factory=object,
        )
        self.assertEqual(code, 3)
        self.assertEqual(result["status"], "PRIVATE_GIFT_LISTENING_QA_ERROR")
        self.assertTrue(result["lock_restored"])
        self.assertEqual(self.lock.read_bytes(), self.original_lock)

    def test_completed_sample_fingerprint_cannot_repeat(self) -> None:
        code, first = qa.execute(
            self.evidence,
            self.output,
            self.lock,
            env=self.env,
            judge=self.judgment(),
            client_factory=object,
        )
        self.assertEqual(code, 0)
        code, second = qa.execute(
            self.evidence,
            self.output,
            self.lock,
            env=self.env,
            judge=lambda *_args: self.fail("repeat reached judge"),
            client_factory=object,
        )
        self.assertEqual(code, 4)
        self.assertEqual(second["status"], "BLOCKED_REPEAT_ATTEMPT")
        self.assertEqual(second["sample_fingerprint"], first["sample_fingerprint"])
        self.assertEqual(self.lock.read_bytes(), self.original_lock)

    def test_public_output_path_is_rejected(self) -> None:
        with self.assertRaisesRegex(qa.GiftKokoroListeningQAError, "public output path"):
            qa.execute(
                self.evidence,
                qa.ROOT / "frontend/public/audio/gift.json",
                self.lock,
                dry_run=True,
                env=self.env,
            )


if __name__ == "__main__":
    unittest.main()
