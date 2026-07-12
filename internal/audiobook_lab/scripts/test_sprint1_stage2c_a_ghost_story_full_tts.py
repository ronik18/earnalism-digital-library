#!/usr/bin/env python3
"""No-provider tests for the Stage 2C full-TTS wrapper."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from internal.audiobook_lab.scripts import sprint1_stage2c_a_ghost_story_full_tts as full_tts


class Stage2CFullTTSTests(unittest.TestCase):
    def test_selector_evidence_requires_owner_minimum(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            original = full_tts.BEST_AUDITION_PATH
            full_tts.BEST_AUDITION_PATH = Path(raw) / "selector.json"
            try:
                full_tts.BEST_AUDITION_PATH.write_text(
                    json.dumps(
                        {
                            "voice": "verse",
                            "profile": "mystery_suspense_narrator",
                            "scores": {"overall_listening_score": 9.5},
                            "confidence": 0.95,
                            "fatal_flags": [],
                        }
                    ),
                    encoding="utf-8",
                )
                evidence = full_tts.selector_evidence()
                self.assertEqual(evidence["voice"], "verse")
            finally:
                full_tts.BEST_AUDITION_PATH = original

    def test_selector_evidence_rejects_fatal_flag(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            original = full_tts.BEST_AUDITION_PATH
            full_tts.BEST_AUDITION_PATH = Path(raw) / "selector.json"
            try:
                full_tts.BEST_AUDITION_PATH.write_text(
                    json.dumps(
                        {
                            "voice": "verse",
                            "profile": "mystery_suspense_narrator",
                            "scores": {"overall_listening_score": 9.5},
                            "confidence": 0.95,
                            "fatal_flags": ["robotic_texture_detected"],
                        }
                    ),
                    encoding="utf-8",
                )
                with self.assertRaises(RuntimeError):
                    full_tts.selector_evidence()
            finally:
                full_tts.BEST_AUDITION_PATH = original

    def test_segmentation_repair_rejects_missing_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            original = full_tts.FULL_QA_RESULT_PATH
            full_tts.FULL_QA_RESULT_PATH = Path(raw) / "missing.json"
            try:
                allowed, reason = full_tts.segmentation_repair_allowed(
                    Path(raw),
                    "A complete sentence.",
                )
            finally:
                full_tts.FULL_QA_RESULT_PATH = original
        self.assertFalse(allowed)
        self.assertIn("evidence is missing", reason)


if __name__ == "__main__":
    unittest.main()
