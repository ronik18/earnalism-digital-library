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
                    "minimum_listening_score": 9.4,
                    "minimum_listening_confidence": 0.9,
                    "samples": samples,
                }
            ),
            encoding="utf-8",
        )
        self.output = self.root / "result.json"
        self.env = {
            "EARNALISM_ENABLE_OPENAI_LISTENING_QA": "true",
            "EARNALISM_OPENAI_LISTENING_QA_MODEL": "gpt-audio",
            "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
            "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "2",
            "OPENAI_API_KEY": "test",
        }

    @staticmethod
    def judge(score: float, fatal: bool = False):
        def _judge(_client, _args, sample):
            return {
                **sample,
                "scores": {"overall_listening_score": score, "confidence_score": 0.95},
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
        code, result = qa.evaluate(self.evidence, self.output, env=self.env, judge=self.judge(9.3), client=object())
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


if __name__ == "__main__":
    unittest.main()
