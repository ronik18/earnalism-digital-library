#!/usr/bin/env python3
"""Tests for the strict one-sample Pride Chatterbox listening wrapper."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import sprint1_pride_chatterbox_v3_one_sample_listening_qa as qa


def passing_judgment() -> dict[str, object]:
    value: dict[str, object] = {
        field: threshold for field, threshold in qa.LISTENING_THRESHOLDS.items()
    }
    value.update({field: False for field in qa.FATAL_FLAGS})
    value.update(
        {
            "frontmatter_present": False,
            "notes": "Strict threshold-quality literary narration.",
            "blocker_reason": "",
        }
    )
    return value


def valid_env() -> dict[str, str]:
    return {
        **qa.EXPECTED_ENV,
        "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
        "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "0.20",
        "MAX_TTS_BUDGET_USD": "0.20",
        "OPENAI_API_KEY": "test-only-not-called",
    }


class PrideChatterboxOneSampleListeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.audio = self.root / "sample.wav"
        self.audio.write_bytes(b"RIFF-objective-pass-private-audio")
        self.audio_hash = hashlib.sha256(self.audio.read_bytes()).hexdigest()
        self.lock = self.root / "paid_tts.lock"
        self.lock_payload = {
            "status": "active",
            "current_holder": "none",
            "allowed_next_holders": [],
            "allowed_slugs": [qa.SLUG],
            "requested_slug": qa.SLUG,
            "approved_scope": qa.LOCK_SCOPE,
        }
        self.lock.write_text(json.dumps(self.lock_payload), encoding="utf-8")
        self.lock_before = self.lock.read_bytes()
        self.pilot = self.root / "pilot_report.json"
        pilot_lock_hash = "a" * 64
        self.pilot_payload = {
            "schema_version": qa.PILOT_SCHEMA,
            "status": qa.PILOT_STATUS,
            "slug": qa.SLUG,
            "title": qa.TITLE,
            "author": qa.AUTHOR,
            "policy_sha256": qa.PILOT_POLICY_SHA256,
            "attempt_fingerprint": "b" * 64,
            "source": {
                "source_sha256": qa.EXPECTED_SOURCE_SHA256,
                "passage_text_sha256": qa.EXPECTED_PASSAGE_SHA256,
                "passage_id": qa.PASSAGE_ID,
            },
            "scope": {
                "sample_count": 1,
                "upload_allowed": False,
                "publication_allowed": False,
                "release_gate_mutation_allowed": False,
                "full_title_generation_allowed": False,
            },
            "audio": {
                "audio_path": str(self.audio),
                "audio_sha256": self.audio_hash,
                "audio_size_bytes": self.audio.stat().st_size,
                "objective_format_pass": True,
                "channels": 1,
                "duration_seconds": 12.5,
                "sample_rate_hz": 24_000,
            },
            "objective_asr": {
                "status": "PASS",
                "audio_derived": True,
                "required_score": qa.ASR_SCORE_MIN,
                "required_coverage": qa.ASR_COVERAGE_MIN,
                "report": {
                    "status": "PASS",
                    "score": 9.8,
                    "coverage": 0.99,
                    "first_words_match": True,
                    "last_words_match": True,
                    "ordered_content_integrity_pass": True,
                    "no_missing_content": True,
                    "no_duplicate_content": True,
                    "no_reordered_content": True,
                    "no_unexpected_content": True,
                    "word_timestamp_evidence_valid": True,
                    "audio_derived_word_timestamps": [
                        {
                            "word": "My",
                            "start_seconds": 0.0,
                            "end_seconds": 0.1,
                            "probability": 0.99,
                        }
                    ],
                    "word_timestamp_anomalies": [],
                    "pass": True,
                },
            },
            "paid_tts_lock": {
                "access": "READ_ONLY",
                "touched": False,
                "unchanged": True,
                "sha256_before": pilot_lock_hash,
                "sha256_after": pilot_lock_hash,
            },
            "release_ready": False,
            "public_audio_status": "AUDIO_HIDDEN_NOT_APPROVED",
            "next_transition": "BOUNDED_LISTENING_REVIEW_ONLY",
        }
        self.write_pilot()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_pilot(self) -> str:
        self.pilot.write_text(
            json.dumps(self.pilot_payload, sort_keys=True),
            encoding="utf-8",
        )
        return hashlib.sha256(self.pilot.read_bytes()).hexdigest()

    def load(self) -> tuple[dict[str, object], dict[str, object], str]:
        return qa.load_objective_pass(
            self.pilot,
            expected_pilot_report_sha256=self.write_pilot(),
            expected_audio_sha256=self.audio_hash,
        )

    def test_accepts_only_hash_bound_objective_pass_report_and_audio(self) -> None:
        _pilot, binding, fingerprint = self.load()
        self.assertEqual(binding["audio_sha256"], self.audio_hash)
        self.assertEqual(binding["objective_asr_score"], 9.8)
        self.assertTrue(qa.is_sha256(fingerprint))

        self.pilot_payload["status"] = "SOURCE_BOUND_DELIVERY_REQUIRED"
        with self.assertRaisesRegex(qa.PrideChatterboxListeningError, "pilot status"):
            self.load()

    def test_rejects_missing_audio_or_hash_mismatch(self) -> None:
        with self.assertRaisesRegex(
            qa.PrideChatterboxListeningError, "pilot audio hash"
        ):
            qa.load_objective_pass(
                self.pilot,
                expected_pilot_report_sha256=self.write_pilot(),
                expected_audio_sha256="c" * 64,
            )
        self.audio.unlink()
        with self.assertRaisesRegex(qa.PrideChatterboxListeningError, "missing"):
            self.load()

    def test_rejects_any_objective_integrity_failure(self) -> None:
        report = self.pilot_payload["objective_asr"]["report"]
        report["ordered_content_integrity_pass"] = False
        with self.assertRaisesRegex(
            qa.PrideChatterboxListeningError,
            "ordered_content_integrity_pass",
        ):
            self.load()

    def test_every_score_is_strictly_gated_at_9_2(self) -> None:
        gate = qa.evaluate(passing_judgment())
        self.assertTrue(gate["listening_pass"])
        self.assertEqual(gate["threshold_failures"], {})

        for field in (
            *qa.ORDINARY_SCORE_FIELDS,
            *qa.ANTI_SCORE_FIELDS,
            "overall_listening_score",
        ):
            judgment = passing_judgment()
            judgment[field] = 9.19
            failed = qa.evaluate(judgment)
            self.assertFalse(failed["listening_pass"], field)
            self.assertIn(field, failed["threshold_failures"])

    def test_confidence_and_fatal_flags_fail_closed(self) -> None:
        judgment = passing_judgment()
        judgment["confidence_score"] = 0.899
        self.assertFalse(qa.evaluate(judgment)["listening_pass"])

        judgment = passing_judgment()
        judgment["overall_listening_score"] = float("nan")
        gate = qa.evaluate(judgment)
        self.assertFalse(gate["listening_pass"])
        self.assertIn("overall_listening_score", gate["invalid_fields"])

        for flag in qa.FATAL_FLAGS:
            judgment = passing_judgment()
            judgment[flag] = True
            gate = qa.evaluate(judgment)
            self.assertFalse(gate["listening_pass"], flag)
            self.assertIn(flag, gate["fatal_flags"])

    def test_budget_never_exceeds_existing_point_two_scope(self) -> None:
        self.assertEqual(qa.budget_guard(valid_env())["status"], "PASS")
        env = valid_env()
        env["EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD"] = "0.21"
        self.assertEqual(qa.budget_guard(env)["status"], "BLOCKED")
        env = valid_env()
        env["EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD"] = "0.20"
        env["MAX_TTS_BUDGET_USD"] = "0.19"
        self.assertEqual(qa.budget_guard(env)["status"], "BLOCKED")

    def test_lock_scope_is_exact_and_bytes_are_never_mutated(self) -> None:
        before, parsed = qa.read_pride_listening_lock(self.lock)
        self.assertEqual(parsed["approved_scope"], qa.LOCK_SCOPE)
        qa.assert_lock_unchanged(self.lock, before)
        self.assertEqual(self.lock.read_bytes(), self.lock_before)

        wrong = {**self.lock_payload, "requested_slug": "another-title"}
        self.lock.write_text(json.dumps(wrong), encoding="utf-8")
        with self.assertRaisesRegex(
            qa.PrideChatterboxListeningError, "requested slug"
        ):
            qa.read_pride_listening_lock(self.lock)

    def test_dry_run_validates_real_audio_without_api_or_release_paths(self) -> None:
        calls = 0

        def forbidden_client() -> object:
            nonlocal calls
            calls += 1
            raise AssertionError("dry-run must not construct an API client")

        output = self.root / "dry-run.json"
        code, result = qa.execute(
            pilot_report_path=self.pilot,
            expected_pilot_report_sha256=self.write_pilot(),
            expected_audio_sha256=self.audio_hash,
            output_path=output,
            lock_path=self.lock,
            dry_run=True,
            env=valid_env(),
            client_factory=forbidden_client,
        )
        self.assertEqual(code, 0)
        self.assertEqual(calls, 0)
        self.assertFalse(result["provider_calls_ran"])
        self.assertFalse(result["release_eligible"])
        self.assertEqual(result["lock"]["access"], "READ_ONLY")
        self.assertTrue(result["lock"]["unchanged"])
        self.assertEqual(self.lock.read_bytes(), self.lock_before)
        self.assertEqual(
            result["safety"],
            {
                "audio_generated": False,
                "uploaded": False,
                "published": False,
                "catalog_mutated": False,
                "release_gate_mutated": False,
                "public_audio_status": "AUDIO_HIDDEN_NOT_APPROVED",
            },
        )

    def test_fake_judge_pass_still_cannot_release_and_lock_is_unchanged(self) -> None:
        output = self.root / "result.json"
        calls = 0

        def fake_judge(_client: object, binding: dict[str, object]) -> dict[str, object]:
            nonlocal calls
            calls += 1
            self.assertEqual(binding["audio_sha256"], self.audio_hash)
            return passing_judgment()

        code, result = qa.execute(
            pilot_report_path=self.pilot,
            expected_pilot_report_sha256=self.write_pilot(),
            expected_audio_sha256=self.audio_hash,
            output_path=output,
            lock_path=self.lock,
            dry_run=False,
            env=valid_env(),
            client_factory=lambda: object(),
            judge=fake_judge,
        )
        self.assertEqual(code, 0)
        self.assertEqual(calls, 1)
        self.assertTrue(result["listening_gate"]["listening_pass"])
        self.assertFalse(result["release_eligible"])
        self.assertIn(
            "THREE_ADDITIONAL_INDEPENDENT_SAMPLES_NOT_RUN",
            result["blockers_to_release"],
        )
        self.assertTrue(result["lock"]["unchanged"])
        self.assertEqual(self.lock.read_bytes(), self.lock_before)


if __name__ == "__main__":
    unittest.main()
