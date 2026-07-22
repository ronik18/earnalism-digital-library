#!/usr/bin/env python3
"""Provider-free tests for Bengali ASR calibration."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("bengali_asr_model_calibration.py")
SPEC = importlib.util.spec_from_file_location("bengali_asr_calibration", SCRIPT)
cal = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(cal)

from bengali_asr_normalization import analyze_bengali_asr  # noqa: E402


class BengaliASRCalibrationTests(unittest.TestCase):
    def test_google_runtime_dependency_is_available(self) -> None:
        self.assertIs(cal.subprocess, subprocess)

    def test_cost_uses_selected_duration_and_arm_count(self) -> None:
        self.assertEqual(cal.estimated_cost([{"duration_seconds": 120}], 2, 0.008), 0.032)

    def test_script_ratio_separates_bengali_and_devanagari(self) -> None:
        self.assertEqual(cal.script_ratio({"bengali": 9, "devanagari": 1, "latin": 0}), 0.9)

    def test_best_arm_prefers_release_pass(self) -> None:
        best = cal.best_arm(
            [
                {"status": "BELOW_THRESHOLD", "source_score": 9.9, "bengali_script_ratio": 1.0},
                {"status": "PASS", "source_score": 9.7, "bengali_script_ratio": 1.0},
            ]
        )
        self.assertEqual(best["status"], "PASS")

    def test_arm_summary_requires_every_selected_chunk_to_pass(self) -> None:
        results = [
            {
                "provider": "sarvam",
                "model": "saaras:v3",
                "language": "bn-IN",
                "chunk_id": "group_0000",
                "status": "PASS",
                "source_score": 9.8,
                "coverage": 0.99,
                "token_order_similarity": 0.98,
                "bengali_script_ratio": 1.0,
                "first_words_match": True,
                "last_words_match": True,
            },
            {
                "provider": "sarvam",
                "model": "saaras:v3",
                "language": "bn-IN",
                "chunk_id": "group_0013",
                "status": "BELOW_THRESHOLD",
                "source_score": 9.6,
                "coverage": 0.99,
                "token_order_similarity": 0.98,
                "bengali_script_ratio": 1.0,
                "first_words_match": True,
                "last_words_match": True,
            },
        ]
        summary = cal.summarize_arms(results, ["group_0000", "group_0013"])[0]
        self.assertEqual(summary["status"], "BELOW_THRESHOLD")
        self.assertEqual(summary["source_score_min"], 9.6)

    def test_same_attempt_survives_evidence_schema_upgrade(self) -> None:
        prior = {"slug": "radharani", "provider": "sarvam", "chunks": [], "models": ["saaras:v3"], "languages": ["bn-IN"]}
        current = {**prior, "modes": ["transcribe"], "source_manifest_sha256": "new", "provider_configuration": {"mode": "transcribe"}}
        self.assertTrue(cal.same_attempt(prior, current))
        self.assertFalse(cal.same_attempt(prior, {**current, "modes": ["verbatim"]}))

    def test_lock_must_explicitly_authorize_requested_slug(self) -> None:
        raw = json.dumps(
            {
                "status": "active",
                "current_holder": "none",
                "allowed_next_holders": [],
                "allowed_slugs": ["radharani"],
            }
        ).encode()
        self.assertEqual(cal.load_lock(raw, slug="radharani")["current_holder"], "none")
        with self.assertRaisesRegex(RuntimeError, "does not authorize slug"):
            cal.load_lock(raw, slug="nishkriti")

    def test_output_path_must_remain_internal(self) -> None:
        internal = cal.validate_internal_path(cal.ROOT / "internal/test/evidence.json", label="output")
        self.assertIn("/internal/", str(internal))
        with self.assertRaisesRegex(RuntimeError, "must remain"):
            cal.validate_internal_path(cal.ROOT / "frontend/build/evidence.json", label="output")

    def test_sarvam_transcription_is_explicit_bengali_and_secret_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            cal,
            "transcribe_sarvam_rest",
            return_value={"text": "রাধারাণী কথা বলিল", "words": []},
        ) as transcribe:
            clip = Path(tmp) / "clip.wav"
            clip.write_bytes(b"RIFFaudio")
            transcript = cal.transcribe_sarvam(clip, model="saaras:v3", language="bn-IN", timeout=30)
        self.assertEqual(transcript, "রাধারাণী কথা বলিল")
        kwargs = transcribe.call_args.kwargs
        self.assertEqual(kwargs["model"], "saaras:v3")
        self.assertEqual(kwargs["language"], "bn-IN")
        self.assertEqual(kwargs["mode"], "transcribe")
        self.assertFalse(kwargs["with_timestamps"])

    def test_sarvam_http_error_does_not_expose_response_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            cal, "transcribe_sarvam_rest", side_effect=RuntimeError("Sarvam ASR HTTP 403")
        ):
            clip = Path(tmp) / "clip.wav"
            clip.write_bytes(b"RIFFaudio")
            with self.assertRaisesRegex(RuntimeError, "Sarvam ASR HTTP 403") as raised:
                cal.transcribe_sarvam(clip, model="saaras:v3", language="bn-IN", timeout=30)
        self.assertNotIn("secret provider body", str(raised.exception))

    def test_ordered_bengali_projection_accepts_spacing_and_historical_orthography(self) -> None:
        manuscript = "বড়মানুষের মেয়ে। রাধারাণী প্রিবিকৌন্সিলে একটি আপীল করিল।"
        transcript = "বড় মানুষের মেয়ে। রাধারানী প্রিভি কাউন্সিলে একটি আপিল করিল।"
        with tempfile.TemporaryDirectory() as tmp:
            report = analyze_bengali_asr(
                slug="projection-pass",
                title="projection pass",
                author="",
                language="ben",
                manuscript=manuscript,
                transcript=transcript,
                run_dir=Path(tmp),
                raw_asr_score=8.0,
            )
        self.assertGreaterEqual(report["phonetic_projection_score"], 9.7)
        self.assertTrue(report["projection_match_proven"])
        self.assertFalse(report["content_match_proven"])

    def test_ordered_bengali_projection_cannot_replace_raw_release_score(self) -> None:
        manuscript = "রাধারাণী প্রিবিকৌন্সিলে একটি আপীল করিল।"
        transcript = "রাধারানী প্রিভি কাউন্সিলে একটি আপিল করিল।"
        with tempfile.TemporaryDirectory() as tmp:
            report = analyze_bengali_asr(
                slug="projection-raw-gate",
                title="projection raw gate",
                author="",
                language="ben",
                manuscript=manuscript,
                transcript=transcript,
                run_dir=Path(tmp),
                raw_asr_score=8.0,
            )
        self.assertTrue(report["projection_match_proven"])
        self.assertFalse(report["content_match_proven"])

    def test_ordered_bengali_projection_rejects_missing_or_reordered_content(self) -> None:
        manuscript = "রাধারাণী রথ দেখিতে গেল। তাহার মা অসুস্থ ছিলেন। সে পথ্য কিনিতে চাহিল।"
        transcripts = [
            "রাধারাণী রথ দেখিতে গেল। সে পথ্য কিনিতে চাহিল।",
            "সে পথ্য কিনিতে চাহিল। তাহার মা অসুস্থ ছিলেন। রাধারাণী রথ দেখিতে গেল।",
        ]
        for index, transcript in enumerate(transcripts):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as tmp:
                report = analyze_bengali_asr(
                    slug=f"projection-fail-{index}",
                    title="projection fail",
                    author="",
                    language="ben",
                    manuscript=manuscript,
                    transcript=transcript,
                    run_dir=Path(tmp),
                    raw_asr_score=8.0,
                )
                self.assertFalse(report["content_match_proven"])

    def test_ordered_bengali_projection_rejects_even_short_unexplained_gap(self) -> None:
        manuscript = "রাধারাণী মা রথ দেখিতে গেল।"
        transcript = "রাধারাণী রথ দেখিতে গেল।"
        with tempfile.TemporaryDirectory() as tmp:
            report = analyze_bengali_asr(
                slug="projection-short-gap",
                title="projection short gap",
                author="",
                language="ben",
                manuscript=manuscript,
                transcript=transcript,
                run_dir=Path(tmp),
                raw_asr_score=9.9,
            )
        self.assertFalse(report["content_match_proven"])
        self.assertTrue(report["missing_spans"])


if __name__ == "__main__":
    unittest.main()
