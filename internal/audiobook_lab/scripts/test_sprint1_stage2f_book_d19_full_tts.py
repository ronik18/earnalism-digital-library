#!/usr/bin/env python3
"""Provider-free tests for the book-d19e96859f Stage 2F wrapper."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_stage2f_book_d19_full_tts.py")
SPEC = importlib.util.spec_from_file_location("stage2f_d19", SCRIPT)
stage2f = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(stage2f)


class Stage2FD19Tests(unittest.TestCase):
    def test_runtime_gate_check_reports_missing_without_values(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            status = stage2f.required_runtime_gates()
        self.assertTrue(status)
        self.assertTrue(all(value == "MISSING_OR_INVALID" for value in status.values()))

    def test_source_preflight_strips_source_year_and_uses_exact_pass(self) -> None:
        result = stage2f.source_preflight(stage2f.ROOT)
        self.assertEqual(result["blockers"], [])
        self.assertEqual(result["prepared_sha256"], "79b0deba6032c36ab919e4ef4786fc62aa55c9c53c328dfbcf49f03a0f7d05fe")
        self.assertEqual(result["representative_score"], 9.4)
        self.assertEqual(result["selected_arm"]["voice"], "pooja")
        self.assertEqual(result["reuse_decision"], "FRESH_FULL_TITLE_REGENERATION_REQUIRED_MISSING_VERIFIABLE_GROUP_CHUNKS")

    def test_lock_preflight_blocks_occupied_holder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "paid_tts.lock"
            path.write_text(json.dumps({"status": "active", "current_holder": "other", "allowed_next_holders": []}))
            result = stage2f.validate_lock(path)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("already has a holder", " ".join(result["blockers"]))

    def test_budget_guard_blocks_before_provider_when_title_cap_is_too_low(self) -> None:
        source = stage2f.source_preflight(stage2f.ROOT)
        env = {
            "SPRINT1_TOTAL_AUDIO_BUDGET_USD": "175",
            "SPRINT1_MAX_USD_PER_TITLE": "0.10",
            "MAX_TTS_BUDGET_USD": "175",
            "EARNALISM_BENGALI_FULL_PILOT_MAX_ESTIMATED_USD": "1",
            "EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD": "1",
            "EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD": "1",
            "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "1",
            "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            blockers = stage2f.budget_blockers(source)
        self.assertIn("ESTIMATED_REPAIR_EXCEEDS_PER_TITLE_CAP", blockers)

    def test_lock_acquire_and_restore_protocol_is_byte_exact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "paid_tts.lock"
            original = b'{"status":"active","current_holder":"none","allowed_next_holders":[]}\n'
            path.write_bytes(original)
            with mock.patch.dict(os.environ, {"SPRINT1_MAX_USD_PER_TITLE": "30"}):
                snapshot = stage2f.acquire_lock(path, 0.0389)
            acquired = json.loads(path.read_text())
            self.assertEqual(acquired["current_holder"], stage2f.HOLDER)
            self.assertEqual(acquired["allowed_next_holders"], [])
            path.write_bytes(snapshot)
            self.assertEqual(path.read_bytes(), original)

    def test_zero_exit_blocked_hook_is_not_tts_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "stage_result.json").write_text(
                json.dumps({"status": "BLOCKED", "ready_for_next_stage": False, "blockers": ["content required"]})
            )
            result = stage2f.evaluate_tts_hook_result(0, run_dir)
        self.assertFalse(result["passed"])
        self.assertFalse(result["provider_calls_ran"])
        self.assertEqual(result["hook_status"], "BLOCKED")

    def test_passed_hook_requires_ready_for_next_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "stage_result.json").write_text(
                json.dumps(
                    {
                        "status": "PASS",
                        "ready_for_next_stage": True,
                        "blockers": [],
                        "metrics": {"audio_regenerated": True},
                    }
                )
            )
            result = stage2f.evaluate_tts_hook_result(0, run_dir)
        self.assertTrue(result["passed"])
        self.assertTrue(result["provider_calls_ran"])


if __name__ == "__main__":
    unittest.main()
