#!/usr/bin/env python3
"""Provider-free tests for the Radharani full Saaras ASR runner."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sprint1_radharani_saaras_full_asr.py")
SPEC = importlib.util.spec_from_file_location("radharani_saaras_full_asr", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(runner)


class RadharaniSaarasFullASRTests(unittest.TestCase):
    def test_group_gate_requires_projection_boundaries_and_timestamps(self) -> None:
        projection = {
            "raw_asr_score": 9.75,
            "normalized_asr_score": 9.71,
            "phonetic_projection_score": 9.85,
            "coverage": 0.99,
            "projection_confidence": 0.98,
            "first_words_match": True,
            "last_words_match": True,
            "missing_spans": [],
            "extra_spans": [],
            "frontmatter_absent": True,
        }
        self.assertTrue(runner.group_pass(projection, 10))
        self.assertFalse(runner.group_pass(projection, 0))
        projection["missing_spans"] = [{"chars": 4}]
        self.assertFalse(runner.group_pass(projection, 10))

    def test_group_gate_rejects_projection_when_raw_score_is_low(self) -> None:
        projection = {
            "raw_asr_score": 8.9,
            "normalized_asr_score": 9.9,
            "phonetic_projection_score": 9.9,
            "coverage": 1.0,
            "projection_confidence": 1.0,
            "first_words_match": True,
            "last_words_match": True,
            "missing_spans": [],
            "extra_spans": [],
            "frontmatter_absent": True,
        }
        self.assertFalse(runner.group_pass(projection, 10))

    def test_projection_summary_preserves_raw_similarity_result(self) -> None:
        source = "রাধারাণী রথ দেখিতে গেল।"
        projection = runner.projection_summary(
            slug="projection-summary",
            source=source,
            transcript=source,
            audio_hash="audio-hash",
        )
        self.assertEqual(projection["raw_asr_score"], 10.0)
        self.assertTrue(projection["content_match_proven"])

    def test_lock_authorizes_only_idle_radharani_scope(self) -> None:
        raw = json.dumps(
            {
                "status": "active",
                "current_holder": "none",
                "allowed_next_holders": [],
                "allowed_slugs": ["radharani"],
            }
        ).encode()
        self.assertEqual(runner.validate_lock(raw, "radharani")["current_holder"], "none")
        with self.assertRaisesRegex(RuntimeError, "does not authorize"):
            runner.validate_lock(raw, "nishkriti")

    def test_cost_is_duration_bound(self) -> None:
        self.assertEqual(runner.cost_estimate([{"duration_seconds": 120}], 0.008), 0.016)

    def test_output_path_must_remain_internal(self) -> None:
        internal = runner.validate_internal_path(runner.ROOT / "internal/test/evidence.json", label="output")
        self.assertIn("/internal/", str(internal))
        with self.assertRaisesRegex(RuntimeError, "must remain"):
            runner.validate_internal_path(runner.ROOT / "frontend/public/evidence.json", label="output")


if __name__ == "__main__":
    unittest.main()
