#!/usr/bin/env python3

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sprint1_google_english_listening_qa as qa


class EnglishListeningQATests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.manifest = self.root / "audition_manifest.json"
        self.manifest.write_text(json.dumps({"slug": "sample", "source_sha256": "a" * 64, "author": "Author"}), encoding="utf-8")
        samples = []
        for passage_id in ("opening", "middle", "dialogue_or_risk", "ending"):
            audio = self.root / f"{passage_id}.mp3"
            audio.write_bytes(b"audio-" + passage_id.encode())
            samples.append({"passage_id": passage_id, "audio_path": str(audio), "audio_sha256": qa.sha256_file(audio)})
        self.evidence = self.root / "pending.json"
        self.evidence.write_text(
            json.dumps(
                {
                    "status": "PENDING_LISTENING_REVIEW",
                    "slug": "sample",
                    "title": "Sample",
                    "source_sha256": "a" * 64,
                    "audition_manifest_path": str(self.manifest),
                    "audition_manifest_sha256": qa.sha256_file(self.manifest),
                    "required_passages": [item["passage_id"] for item in samples],
                    "minimum_listening_score": 8.9,
                    "minimum_listening_confidence": 0.9,
                    "per_dimension_score_min": 8.9,
                    "anti_robotic_texture_score_min": 8.9,
                    "anti_choppy_join_score_min": 8.9,
                    "samples": samples,
                }
            ),
            encoding="utf-8",
        )
        self.output = self.root / "result.json"
        self.paid_lock = self.root / "paid_tts.lock"
        self.paid_lock.write_text(
            json.dumps(
                {
                    "status": "active",
                    "current_holder": "none",
                    "allowed_next_holders": [],
                    "allowed_slugs": ["sample"],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        self.env = {
            "EARNALISM_ENABLE_OPENAI_LISTENING_QA": "true",
            "EARNALISM_OPENAI_LISTENING_QA_MODEL": "gpt-audio",
            "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
            "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "2",
            "OPENAI_API_KEY": "test",
        }

    @staticmethod
    def judge(
        score: float,
        fatal: bool = False,
        *,
        emotional_expression: float | None = None,
        anti_robotic: float | None = None,
    ):
        def _judge(_client, _args, sample):
            scores = {
                "overall_listening_score": score,
                "confidence_score": 0.95,
                "naturalness_score": score,
                "pronunciation_score": score,
                "emotional_expression_score": (
                    score if emotional_expression is None else emotional_expression
                ),
                "punctuation_pause_score": score,
                "pacing_score": score,
                "continuity_score": score,
                "listener_enjoyment_score": score,
                "anti_robotic_texture_score": (
                    max(score, 9.2) if anti_robotic is None else anti_robotic
                ),
                "anti_choppy_join_score": max(score, 8.9),
            }
            return {
                **sample,
                "scores": scores,
                "confidence": 0.95,
                "judge_flags": {name: fatal and name == "robotic_texture_detected" for name in qa.BINARY_LISTENING_FLAGS},
                "notes": "mock",
                "blocker_reason": "",
            }

        return _judge

    def test_missing_budget_blocks_before_judge(self) -> None:
        env = dict(self.env)
        env.pop("EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD")
        calls = []

        def judge(*args):
            calls.append(args)
            return {}

        code, result = qa.evaluate(self.evidence, self.output, env=env, judge=judge, client=object())
        self.assertEqual(code, 2)
        self.assertFalse(result["provider_calls_ran"])
        self.assertEqual(calls, [])

    def test_all_samples_must_pass(self) -> None:
        code, result = qa.evaluate(self.evidence, self.output, env=self.env, judge=self.judge(8.89), client=object())
        self.assertEqual(code, 3)
        self.assertEqual(result["status"], "BLOCKED_LISTENING_QA")

    def test_fatal_flag_blocks(self) -> None:
        code, result = qa.evaluate(self.evidence, self.output, env=self.env, judge=self.judge(9.5, True), client=object())
        self.assertEqual(code, 3)
        self.assertIn("robotic_texture_detected", result["fatal_flags"])

    def test_pass_writes_full_evidence(self) -> None:
        code, result = qa.evaluate(self.evidence, self.output, env=self.env, judge=self.judge(9.5), client=object())
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["samples"]), 4)
        self.assertEqual(json.loads(self.output.read_text())["status"], "PASS")

    def test_ordinary_dimension_floor_blocks(self) -> None:
        code, result = qa.evaluate(
            self.evidence,
            self.output,
            env=self.env,
            judge=self.judge(9.3, emotional_expression=8.8),
            client=object(),
        )
        self.assertEqual(code, 3)
        self.assertTrue(
            any("emotional_expression_score" in item for item in result["dimension_failures"])
        )

    def test_anti_robotic_floor_blocks(self) -> None:
        code, result = qa.evaluate(
            self.evidence,
            self.output,
            env=self.env,
            judge=self.judge(9.3, anti_robotic=8.8),
            client=object(),
        )
        self.assertEqual(code, 3)
        self.assertTrue(
            any("anti_robotic_texture_score" in item for item in result["dimension_failures"])
        )

    def test_paid_lock_restores_byte_for_byte(self) -> None:
        before = self.paid_lock.read_bytes()
        code, result = qa.evaluate(
            self.evidence,
            self.output,
            paid_lock_path=self.paid_lock,
            env=self.env,
            judge=self.judge(9.5),
            client=object(),
        )
        self.assertEqual(code, 0)
        self.assertTrue(result["paid_lock_touched"])
        self.assertTrue(result["paid_lock_restored_byte_for_byte"])
        self.assertEqual(self.paid_lock.read_bytes(), before)

    def test_paid_lock_rejects_wrong_slug_before_judge(self) -> None:
        payload = json.loads(self.paid_lock.read_text(encoding="utf-8"))
        payload["allowed_slugs"] = ["other"]
        self.paid_lock.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        calls = []

        def judge(*args):
            calls.append(args)
            return {}

        code, result = qa.evaluate(
            self.evidence,
            self.output,
            paid_lock_path=self.paid_lock,
            env=self.env,
            judge=judge,
            client=object(),
        )
        self.assertEqual(code, 2)
        self.assertFalse(result["provider_calls_ran"])
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
