#!/usr/bin/env python3
"""Focused regression tests for the non-paid Sprint 1 preflight."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from internal.audiobook_lab.scripts.sprint1_stage2a_a_ghost_story_listening_qa import hook_exit_code


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "internal/audiobook_lab/scripts/sprint1_publication_preflight.py"
STAGE2A_SCRIPT = ROOT / "internal/audiobook_lab/scripts/sprint1_stage2a_a_ghost_story_listening_qa.py"
LOCK_PATH = ROOT / "internal/earnalism_intelligence/locks/paid_tts.lock"


class Sprint1PublicationPreflightTests(unittest.TestCase):
    def test_stage2a_wrapper_returns_nonzero_for_blocked_hook(self) -> None:
        self.assertEqual(hook_exit_code(0, "BLOCKED"), 3)
        self.assertEqual(hook_exit_code(0, "PASS"), 0)
        self.assertEqual(hook_exit_code(7, "PASS"), 7)

    def test_external_output_root_is_supported_without_provider_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory) / "preflight"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--slugs",
                    "a-ghost-story",
                    "--output-root",
                    str(output_root),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["status"], "NON_PAID_PREFLIGHT_COMPLETE")

            cost_report = json.loads((output_root / "sprint1_cost_report.json").read_text(encoding="utf-8"))
            sanitation_report = json.loads(
                (output_root / "sanitized_text_reports/a-ghost-story.json").read_text(encoding="utf-8")
            )
            self.assertFalse(cost_report["provider_calls_ran"])
            self.assertTrue(Path(sanitation_report["sanitized_text_path"]).is_absolute())

    def test_stage2a_dry_run_preserves_paid_lock(self) -> None:
        env = {
            **dict(os.environ),
            "SPRINT1_TOTAL_AUDIO_BUDGET_USD": "175",
            "SPRINT1_MAX_USD_PER_TITLE": "30",
            "MAX_TTS_BUDGET_USD": "175",
            "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
            "EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD": "10",
            "EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD": "10",
            "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "2",
            "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
            "EARNALISM_ENABLE_OPENAI_LISTENING_QA": "true",
            "EARNALISM_OPENAI_LISTENING_QA_MODEL": "gpt-audio",
            "OPENAI_API_KEY": "test-key-not-used",
        }
        lock_before = LOCK_PATH.read_bytes()
        result = subprocess.run(
            [sys.executable, str(STAGE2A_SCRIPT), "--dry-run"],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "DRY_RUN_PASS")
        self.assertEqual(LOCK_PATH.read_bytes(), lock_before)


if __name__ == "__main__":
    unittest.main()
