#!/usr/bin/env python3
"""Provider-free guardrails for the persisted Bengali campaign continuation."""

from __future__ import annotations

import json
import shlex
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
STATE = ROOT / "internal/earnalism_intelligence/bengali_audiobook_campaign_state.json"


class BengaliCampaignContinuationSafetyTests(unittest.TestCase):
    def test_paid_continuation_is_approved_budgeted_and_lock_serialized(self) -> None:
        command = json.loads(STATE.read_text(encoding="utf-8"))["next_exact_command"]
        required_fragments = (
            "EARNALISM_APPROVE_SARVAM_CORRECTIVE_AUDITIONS=true",
            "EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF=true",
            "EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS=true",
            "EARNALISM_APPROVE_BENGALI_31_AUDIO_CAMPAIGN=true",
            "EARNALISM_BENGALI_CAMPAIGN_MAX_ESTIMATED_USD=75",
            "EARNALISM_BENGALI_MAX_ESTIMATED_USD_PER_TITLE=8",
            "SPRINT1_TOTAL_AUDIO_BUDGET_USD=75",
            "SPRINT1_MAX_USD_PER_TITLE=8",
            "MAX_TTS_BUDGET_USD=75",
            "EARNALISM_STOP_ON_BUDGET_EXCEEDED=true",
            "sprint1_paid_stage_runner.py",
            "--lock-path internal/earnalism_intelligence/locks/paid_tts.lock",
            "--slug nishkriti",
            "--scope listening-qa-quota-probe",
        )
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, command)
        self.assertEqual(shlex.split(command).count("--"), 1)


if __name__ == "__main__":
    unittest.main()
