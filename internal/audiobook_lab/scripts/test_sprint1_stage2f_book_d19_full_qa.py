#!/usr/bin/env python3
"""Provider-free tests for the D19 full-QA wrapper."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_stage2f_book_d19_full_qa.py")
SPEC = importlib.util.spec_from_file_location("stage2f_d19_qa", SCRIPT)
qa = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(qa)


class Stage2FD19QATests(unittest.TestCase):
    def test_runtime_gate_accepts_tighter_positive_stage_caps(self) -> None:
        env = dict(qa.EXPECTED_ENV)
        env.update(
            {
                "EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD": "1",
                "EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD": "1",
                "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "1",
                "OPENAI_API_KEY": "redacted-test-key",
            }
        )
        with mock.patch.dict(qa.os.environ, env, clear=True):
            self.assertEqual(qa.runtime_gate_errors(), [])

    def test_runtime_gate_rejects_missing_or_nonpositive_stage_caps(self) -> None:
        env = dict(qa.EXPECTED_ENV)
        env.update(
            {
                "EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD": "0",
                "EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD": "not-a-number",
                "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "nan",
                "OPENAI_API_KEY": "redacted-test-key",
            }
        )
        with mock.patch.dict(qa.os.environ, env, clear=True):
            errors = qa.runtime_gate_errors()
        self.assertTrue(any("EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD" in error for error in errors))
        self.assertTrue(any("EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD" in error for error in errors))
        self.assertTrue(any("EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD" in error for error in errors))

    def test_tts_cost_uses_sarvam_metric_without_default_drift(self) -> None:
        self.assertEqual(qa.tts_cost_from_metrics({"metrics": {"tts_estimated_cost": 0.0389}}), 0.0389)
        self.assertEqual(qa.tts_cost_from_metrics({"metrics": {"estimated_tts_usd": 0.02}}), 0.02)

    def test_lock_requires_closed_active_state(self) -> None:
        raw = json.dumps({"status": "active", "current_holder": "none", "allowed_next_holders": []}).encode()
        self.assertEqual(qa.load_lock(raw)["current_holder"], "none")
        with self.assertRaises(RuntimeError):
            qa.load_lock(json.dumps({"status": "active", "current_holder": "other", "allowed_next_holders": []}).encode())

    def test_owner_gate_requires_every_sample_to_pass(self) -> None:
        samples = [
            {
                "scores": {"overall_listening_score": score, "confidence_score": 0.95},
                "judge_flags": {field: False for field in qa.FATAL_FLAGS},
            }
            for score in (9.4, 9.5, 9.4, 9.6)
        ]
        self.assertTrue(qa.owner_listening_gate(samples)["passes"])
        samples[2]["scores"]["overall_listening_score"] = 9.3
        self.assertFalse(qa.owner_listening_gate(samples)["passes"])

    def test_owner_gate_blocks_fatal_flag(self) -> None:
        samples = [
            {
                "scores": {"overall_listening_score": 9.5, "confidence_score": 0.95},
                "judge_flags": {field: False for field in qa.FATAL_FLAGS},
            }
            for _ in range(4)
        ]
        samples[0]["judge_flags"]["robotic_texture_detected"] = True
        self.assertFalse(qa.owner_listening_gate(samples)["passes"])

    def test_construction_source_gate_cannot_replace_weak_raw_asr(self) -> None:
        hook = {"metrics": {"source_match_score": 10.0, "source_verification_method": "clean_tts_source_provenance_static_audit"}}
        diagnosis = {"score": 1.5, "first_words_match": False, "last_words_match": False}
        construction = {"tts_by_construction_verified": True, "first_last_tts_input_boundary_pass": True}
        result = qa.effective_source_gate(hook, diagnosis, construction)
        self.assertFalse(result["passes"])
        self.assertEqual(result["score"], 1.5)
        self.assertEqual(result["construction_source_match_score"], 10.0)
        self.assertTrue(result["construction_verified"])

    def test_raw_asr_and_audio_boundaries_can_pass_with_construction_support(self) -> None:
        hook = {"metrics": {"source_match_score": 10.0, "source_verification_method": "clean_tts_source_provenance_static_audit"}}
        diagnosis = {"score": 9.8, "first_words_match": True, "last_words_match": True}
        construction = {"tts_by_construction_verified": True, "first_last_tts_input_boundary_pass": True}
        result = qa.effective_source_gate(hook, diagnosis, construction)
        self.assertTrue(result["passes"])
        self.assertEqual(result["method"], "asr_transcript")

    def test_google_manifest_materializes_hash_checked_compatibility_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            source = "প্রথম বাক্যটি পরিষ্কার। দ্বিতীয় বাক্যটিও পরিষ্কার।\n"
            source_path = run_dir / "sanitized_manuscript.txt"
            source_path.write_text(source, encoding="utf-8")
            chunks = qa.chunk_text(source, max_chars=1200)
            records = []
            for chunk in chunks:
                audio = run_dir / "chunks" / f"chunk_{chunk['index']:04d}.mp3"
                audio.parent.mkdir(parents=True, exist_ok=True)
                audio.write_bytes(f"mock-audio-{chunk['index']}".encode())
                records.append(
                    {
                        "index": chunk["index"],
                        "file": str(audio.relative_to(run_dir)),
                        "text_sha256": qa.sha256_text(chunk["text"]),
                        "tts_text_sha256": qa.sha256_text(qa.google_safe_tts_text(chunk["text"])),
                        "audio_sha256": qa.sha256_file(audio),
                    }
                )
            final_audio = run_dir / "private_full.mp3"
            final_audio.write_bytes(b"mock-final-audio")
            manifest = {
                "slug": qa.SLUG,
                "provider": "google",
                "model": "google-cloud-texttospeech",
                "voice": "bn-IN-Chirp3-HD-Aoede",
                "source": {"file": source_path.name, "sha256": qa.sha256_text(source)},
                "chunking": {"max_characters": 1200},
                "chunks": records,
                "final_audio": {"file": final_audio.name, "sha256": qa.sha256_file(final_audio)},
                "budget": {"estimated_google_tts_usd": 0.01},
            }
            (run_dir / "google_bengali_full_tts_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with mock.patch.object(qa, "audio_duration_seconds", return_value=1.25):
                result = qa.materialize_google_compatibility(run_dir)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["metrics"]["provider"], "google")
            chunk_manifest = json.loads((run_dir / "tts_chunk_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(chunk_manifest["group_repair"]["status"], "NOT_REQUESTED")
            self.assertEqual(chunk_manifest["chunks"][0]["duration_seconds"], 1.25)
            self.assertEqual((run_dir / "clean_manuscript.txt").read_text(encoding="utf-8"), source)


if __name__ == "__main__":
    unittest.main()
