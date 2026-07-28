#!/usr/bin/env python3
"""Focused tests for The Secret Garden chapter-one retained-WAV repair."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name(
    "sprint1_secret_garden_chapter1_asr_repair.py"
)
SPEC = importlib.util.spec_from_file_location(
    "secret_garden_chapter1_asr_repair", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SecretGardenChapter1ASRRepairTests(unittest.TestCase):
    def test_input_binds_exact_private_audio_and_failed_checkpoint(self) -> None:
        evidence, samples, sections, reports = MODULE.validate_input(
            MODULE.DEFAULT_INPUT
        )
        self.assertEqual(evidence["status"], MODULE.EXPECTED_INPUT_STATUS)
        self.assertEqual(len(samples), 18)
        self.assertEqual(len(sections), 18)
        self.assertEqual(len(reports), 18)
        self.assertEqual(
            set(MODULE.REPAIR_SECTION_IDS),
            {
                section_id
                for section_id, report in reports.items()
                if report["pass"] is not True
            },
        )

    def test_fingerprint_is_exact_and_closed_by_execution_evidence(self) -> None:
        _evidence, samples, sections, _reports = MODULE.validate_input(
            MODULE.DEFAULT_INPUT
        )
        self.assertEqual(
            MODULE.repair_fingerprint(samples, sections),
            "8f7221a8d5a5f5a2e446e8f0725eab00f93efbc8695b6f5967111739af7a68a8",
        )
        completed = MODULE.read_json(MODULE.DEFAULT_OUTPUT)
        self.assertEqual(
            completed["status"],
            "SECRET_GARDEN_CHAPTER_001_ASR_REPAIR_FAIL_LANE_CLOSED",
        )
        self.assertTrue(completed["asr_repair"]["fingerprint_closed"])
        self.assertFalse(completed["safety"]["publication_performed"])
        self.assertFalse(completed["safety"]["release_gate_mutated"])

    def test_equivalences_are_spelling_only_and_exact_count(self) -> None:
        evaluated, applied = MODULE.apply_equivalences(
            "chapter-001-section-005",
            "Her ire waited on the verandah for Sadie.",
        )
        self.assertEqual(
            evaluated, "Her ayah waited on the veranda for saidie."
        )
        self.assertEqual(len(applied), 3)
        with self.assertRaisesRegex(
            MODULE.ChapterASRRepairError, "equivalence count changed"
        ):
            MODULE.apply_equivalences(
                "chapter-001-section-012", "One ire only."
            )

    def test_unexpected_speech_is_never_removed(self) -> None:
        for section_id, transcript in (
            ("chapter-001-section-004", "source words is"),
            ("chapter-001-section-005", "source words The End"),
            (
                "chapter-001-section-008",
                "source words Thanks for watching and see you next time",
            ),
            ("chapter-001-section-017", "neither father"),
        ):
            evaluated, _applied = MODULE.apply_equivalences(
                section_id, transcript
            )
            self.assertEqual(evaluated, transcript)

    def test_dry_run_is_private_and_cannot_mutate_release(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "repair.json"
            with mock.patch.object(
                MODULE, "EXPECTED_PAID_LOCK_SHA256",
                MODULE.sha256_file(MODULE.DEFAULT_PAID_LOCK),
            ):
                code, result = MODULE.execute(
                    MODULE.DEFAULT_INPUT,
                    output,
                    MODULE.DEFAULT_WHISPER_CACHE,
                    MODULE.DEFAULT_PAID_LOCK,
                    dry_run=True,
                )
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "DRY_RUN_PASS")
        self.assertTrue(result["retained_audio_immutable"])
        self.assertFalse(result["synthesis_performed"])
        self.assertFalse(result["upload_performed"])
        self.assertFalse(result["publication_performed"])
        self.assertFalse(result["release_gate_mutated"])


if __name__ == "__main__":
    unittest.main()
