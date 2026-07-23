#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sprint1_paid_stage_runner as runner


class PaidStageRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.lock = self.root / "paid_tts.lock"
        self.original = (
            json.dumps(
                {
                    "lock": "paid_tts",
                    "status": "active",
                    "current_holder": "none",
                    "allowed_next_holders": [],
                    "allowed_slugs": ["test-slug"],
                    "approved_scope": "one bounded test call",
                },
                indent=2,
            )
            + "\n"
        ).encode()
        self.lock.write_bytes(self.original)
        self.report = self.root / "report.json"
        self.env = {
            "SPRINT1_TOTAL_AUDIO_BUDGET_USD": "175",
            "SPRINT1_MAX_USD_PER_TITLE": "30",
            "MAX_TTS_BUDGET_USD": "175",
            "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
        }

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def args(self, **changes: object) -> argparse.Namespace:
        values = {
            "lock_path": self.lock,
            "holder": "sprint1_test_holder",
            "slug": "test-slug",
            "scope": "one bounded test call",
            "estimated_usd": 0.25,
            "prior_spend_usd": 4.0,
            "report": self.report,
            "workdir": self.root,
            "timeout_seconds": 10,
            "command": ["--", "provider-command"],
        }
        values.update(changes)
        return argparse.Namespace(**values)

    @mock.patch.object(runner.subprocess, "run")
    def test_missing_budget_gate_blocks_before_subprocess(self, run: mock.Mock) -> None:
        env = dict(self.env)
        env.pop("MAX_TTS_BUDGET_USD")
        returncode, report = runner.run_paid_stage(self.args(), env=env)
        self.assertEqual(returncode, 2)
        self.assertFalse(report["provider_command_started"])
        run.assert_not_called()
        self.assertEqual(self.lock.read_bytes(), self.original)

    @mock.patch.object(runner.subprocess, "run")
    def test_budget_excess_blocks_before_subprocess(self, run: mock.Mock) -> None:
        returncode, report = runner.run_paid_stage(self.args(estimated_usd=31.0), env=self.env)
        self.assertEqual(returncode, 2)
        self.assertFalse(report["provider_command_started"])
        run.assert_not_called()

    @mock.patch.object(runner.subprocess, "run")
    def test_success_holds_narrow_lock_and_restores_exact_bytes(self, run: mock.Mock) -> None:
        def inspect_lock(*_args: object, **_kwargs: object) -> mock.Mock:
            held = json.loads(self.lock.read_text())
            self.assertEqual(held["current_holder"], "sprint1_test_holder")
            self.assertEqual(held["allowed_next_holders"], [])
            self.assertEqual(held["allowed_slugs"], ["test-slug"])
            return mock.Mock(returncode=0)

        run.side_effect = inspect_lock
        returncode, report = runner.run_paid_stage(self.args(), env=self.env)
        self.assertEqual(returncode, 0)
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["provider_command_started"])
        self.assertTrue(report["lock_restored"])
        self.assertEqual(self.lock.read_bytes(), self.original)

    @mock.patch.object(runner.subprocess, "run", side_effect=runner.subprocess.TimeoutExpired("provider", 10))
    def test_timeout_restores_lock_and_records_closeout(self, _run: mock.Mock) -> None:
        returncode, report = runner.run_paid_stage(self.args(), env=self.env)
        self.assertEqual(returncode, 124)
        self.assertEqual(report["status"], "PROVIDER_TIMEOUT")
        self.assertTrue(report["timed_out"])
        self.assertTrue(report["lock_restored"])
        self.assertEqual(self.lock.read_bytes(), self.original)

    @mock.patch.object(runner.subprocess, "run")
    def test_open_or_broad_lock_blocks_before_subprocess(self, run: mock.Mock) -> None:
        self.lock.write_text(
            json.dumps({"status": "active", "current_holder": "none", "allowed_next_holders": ["broad"]}) + "\n"
        )
        returncode, report = runner.run_paid_stage(self.args(), env=self.env)
        self.assertEqual(returncode, 2)
        self.assertIn("allowed_next_holders", " ".join(report["blockers"]))
        run.assert_not_called()

    @mock.patch.object(runner.subprocess, "run")
    def test_slug_scope_mismatch_blocks_before_subprocess(self, run: mock.Mock) -> None:
        payload = json.loads(self.original)
        payload["allowed_slugs"] = ["different-slug"]
        self.lock.write_text(json.dumps(payload, indent=2) + "\n")
        returncode, report = runner.run_paid_stage(self.args(), env=self.env)
        self.assertEqual(returncode, 2)
        self.assertFalse(report["provider_command_started"])
        self.assertIn("slug scope mismatch", " ".join(report["blockers"]))
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
