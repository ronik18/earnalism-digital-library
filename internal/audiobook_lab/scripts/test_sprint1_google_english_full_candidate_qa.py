#!/usr/bin/env python3
"""Provider-free tests for generic private Google English full-candidate QA."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sprint1_google_english_full_candidate_qa as qa


class GoogleEnglishFullCandidateQATests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.run_dir = Path(self.temporary.name) / "private_full"
        self.run_dir.mkdir(parents=True)
        self.source_path = self.run_dir / "sanitized_source.txt"
        sentences = []
        for index in range(8):
            dialogue = (
                ' "Will the hidden door open?" she asked; the answer came slowly.'
                if index == 4
                else ""
            )
            sentences.append(
                f"Section {index + 1} begins with a distinct observation about the old house "
                + "and carries its careful literary detail across the quiet room " * 5
                + dialogue
                + f" This is the measured ending of section {index + 1}."
            )
        self.source = "\n\n".join(sentences) + "\n"
        self.source_path.write_text(self.source, encoding="utf-8")
        self.input_manifest_path = self.run_dir / "input_manifest.json"
        input_manifest = {
            "schema_version": 1,
            "slug": "private-test-title",
            "title": "Private Test Title",
            "author": "Test Author",
            "language": "en",
            "sanitized_source_sha256": qa.sha256_file(self.source_path),
            "sanitization_status": "PASS",
            "rights_status": "PASS",
            "commercial_use_allowed": True,
        }
        self.input_manifest_path.write_text(
            json.dumps(input_manifest, indent=2) + "\n", encoding="utf-8"
        )
        chunks = qa.pipeline.full_generation_chunks(self.source, max_chars=500)
        self.assertGreaterEqual(len(chunks), qa.LISTENING_SAMPLE_COUNT)
        records = []
        audio_dir = self.run_dir / "audio"
        audio_dir.mkdir()
        for chunk in chunks:
            audio_path = audio_dir / f"{chunk['chunk_id']}.mp3"
            audio_path.write_bytes(b"ID3" + f"mock-audio-{chunk['index']}".encode())
            records.append(
                {
                    "unit_id": chunk["chunk_id"],
                    "text_sha256": chunk["text_sha256"],
                    "characters": chunk["characters"],
                    "audio_path": str(audio_path),
                    "audio_sha256": qa.sha256_file(audio_path),
                    "audio_size_bytes": audio_path.stat().st_size,
                }
            )
        self.manifest_path = self.run_dir / "full_generation_manifest.json"
        self.manifest = {
            "schema_version": 1,
            "status": "FULL_GENERATION_PRIVATE_QA_PENDING",
            "mode": "full",
            "slug": input_manifest["slug"],
            "title": input_manifest["title"],
            "author": input_manifest["author"],
            "provider": "google",
            "voice": "en-GB-Studio-C",
            "language_code": "en-GB",
            "source_sha256": input_manifest["sanitized_source_sha256"],
            "input_manifest_sha256": qa.sha256_file(self.input_manifest_path),
            "unit_count": len(records),
            "unit_hashes": [record["text_sha256"] for record in records],
            "provider_calls_ran": True,
            "synthesis_calls": len(records),
            "result_manifest_path": str(self.manifest_path),
            "sanitized_source_copy": str(self.source_path),
            "input_manifest_copy": str(self.input_manifest_path),
            "generated_audio": records,
            "private_output_only": True,
            "public_release_approved": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_mutation_performed": False,
            "paid_lock_restored_byte_for_byte": True,
            "errors": [],
        }
        self.write_manifest()
        self.output_path = self.run_dir / "full_candidate_qa.json"
        self.env = {
            "EARNALISM_ENABLE_OPENAI_LISTENING_QA": "true",
            "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
            "EARNALISM_OPENAI_LISTENING_QA_MODEL": "gpt-audio-test",
            "EARNALISM_LISTENING_POLICY_VERSION": "tiered_audiobook_acceptance_v1",
            "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
            "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "1.00",
            "MAX_TTS_BUDGET_USD": "10.00",
            "EARNALISM_PRIOR_ESTIMATED_SPEND_USD": "0.25",
            "OPENAI_API_KEY": "test-only-key",
        }

    def write_manifest(self) -> None:
        self.manifest_path.write_text(
            json.dumps(self.manifest, indent=2) + "\n", encoding="utf-8"
        )

    @staticmethod
    def duration_probe(path: Path) -> float:
        index = int(path.stem.rsplit("_", 1)[-1])
        return 10.0 + index

    @staticmethod
    def passing_judge(_client, _args, sample):
        return {
            **sample,
            "scores": {
                field: (0.96 if field == "confidence_score" else 9.8)
                for field in qa.LISTENING_THRESHOLDS
            },
            "judge_flags": {field: False for field in qa.BINARY_LISTENING_FLAGS},
            "frontmatter_present": False,
            "notes": "provider-free structured fixture",
            "blocker_reason": "",
        }

    def evaluate(self, *, env=None, judge=None):
        return qa.evaluate(
            self.manifest_path,
            self.output_path,
            env=self.env if env is None else env,
            judge=self.passing_judge if judge is None else judge,
            client=object(),
            duration_probe=self.duration_probe,
        )

    def test_passing_candidate_uses_schema3_and_measured_section_sync(self) -> None:
        code, result = self.evaluate()
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "FULL_CANDIDATE_QA_PASS_PRIVATE_ONLY")
        self.assertTrue(result["objective_qa"]["construction"]["first_words_match"])
        self.assertTrue(result["objective_qa"]["construction"]["last_words_match"])
        sync = result["objective_qa"]["measured_sync"]
        self.assertEqual(sync["sync_granularity"], "section")
        self.assertFalse(sync["auto_estimated_sync"])
        self.assertEqual(sync["coverage_percent"], 100.0)
        listening = result["listening_quality_report"]
        self.assertEqual(listening["qa_schema_version"], 3)
        self.assertEqual(
            len(listening["listening_quality"]["samples"]),
            qa.LISTENING_SAMPLE_COUNT,
        )
        self.assertEqual(
            len(
                {
                    sample["sample_audio_hash"]
                    for sample in listening["listening_quality"]["samples"]
                }
            ),
            qa.LISTENING_SAMPLE_COUNT,
        )
        self.assertEqual(result["provider_call_count"], qa.LISTENING_SAMPLE_COUNT)
        self.assertFalse(result["public_release_approved"])

    def test_source_hash_tamper_blocks_before_judge(self) -> None:
        self.source_path.write_text(self.source + "tampered", encoding="utf-8")
        calls = []

        def judge(*args):
            calls.append(args)
            return {}

        code, result = self.evaluate(judge=judge)
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "BLOCKED_OBJECTIVE_QA")
        self.assertIn("SOURCE_HASH_MISMATCH", result["blockers"][0])
        self.assertEqual(calls, [])

    def test_audio_hash_tamper_blocks_before_judge(self) -> None:
        Path(self.manifest["generated_audio"][2]["audio_path"]).write_bytes(
            b"ID3tampered"
        )
        calls = []

        def judge(*args):
            calls.append(args)
            return {}

        code, result = self.evaluate(judge=judge)
        self.assertEqual(code, 2)
        self.assertIn("AUDIO_SIZE_MISMATCH", result["blockers"][0])
        self.assertEqual(calls, [])

    def test_reordered_construction_blocks_before_judge(self) -> None:
        first = self.manifest["generated_audio"][0]
        second = self.manifest["generated_audio"][1]
        first["text_sha256"], second["text_sha256"] = (
            second["text_sha256"],
            first["text_sha256"],
        )
        first["characters"], second["characters"] = (
            second["characters"],
            first["characters"],
        )
        self.manifest["unit_hashes"] = [
            record["text_sha256"] for record in self.manifest["generated_audio"]
        ]
        self.write_manifest()
        calls = []

        def judge(*args):
            calls.append(args)
            return {}

        code, result = self.evaluate(judge=judge)
        self.assertEqual(code, 2)
        self.assertIn("CONSTRUCTION_ORDER_FAILED", result["blockers"][0])
        self.assertEqual(calls, [])

    def test_missing_measured_duration_blocks_before_judge(self) -> None:
        calls = []

        def judge(*args):
            calls.append(args)
            return {}

        code, result = qa.evaluate(
            self.manifest_path,
            self.output_path,
            env=self.env,
            judge=judge,
            client=object(),
            duration_probe=lambda _path: 0.0,
        )
        self.assertEqual(code, 2)
        self.assertIn("MEASURED_SYNC_UNAVAILABLE", result["blockers"][0])
        self.assertEqual(calls, [])

    def test_cap_gate_blocks_before_judge(self) -> None:
        env = {**self.env, "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "0.10"}
        calls = []

        def judge(*args):
            calls.append(args)
            return {}

        code, result = self.evaluate(env=env, judge=judge)
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "BLOCKED_BEFORE_LISTENING_QA")
        self.assertIn("LISTENING_QA_BUDGET_EXCEEDED", result["blockers"][0])
        self.assertEqual(calls, [])

    def test_public_output_path_is_rejected_without_writing(self) -> None:
        public_output = self.run_dir.parent / "public" / "full_candidate_qa.json"
        code, result = qa.evaluate(
            self.manifest_path,
            public_output,
            env=self.env,
            judge=self.passing_judge,
            client=object(),
            duration_probe=self.duration_probe,
        )
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "BLOCKED_OUTPUT_PATH")
        self.assertFalse(public_output.exists())

    def test_low_or_fatal_listening_evidence_fails_closed(self) -> None:
        def failing_judge(_client, _args, sample):
            result = self.passing_judge(_client, _args, sample)
            result["scores"]["overall_listening_score"] = 9.2
            result["judge_flags"]["robotic_texture_detected"] = True
            return result

        code, result = self.evaluate(judge=failing_judge)
        self.assertEqual(code, 3)
        self.assertEqual(result["status"], "BLOCKED_LISTENING_QA")
        self.assertTrue(
            any("robotic_texture_detected" in blocker for blocker in result["blockers"])
        )

    def test_passing_cached_binding_does_not_call_judge_again(self) -> None:
        first_code, _ = self.evaluate()
        self.assertEqual(first_code, 0)
        calls = []

        def judge(*args):
            calls.append(args)
            return {}

        second_code, second = self.evaluate(judge=judge)
        self.assertEqual(second_code, 0)
        self.assertTrue(second["cached_result_reused"])
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
