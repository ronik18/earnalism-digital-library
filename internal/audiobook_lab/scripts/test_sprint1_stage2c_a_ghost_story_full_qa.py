#!/usr/bin/env python3
"""No-provider tests for the Stage 2C ASR/listening wrapper."""

from __future__ import annotations

import os
import sys
import unittest
from contextlib import contextmanager
from unittest import mock


from internal.audiobook_lab.scripts import sprint1_stage2c_a_ghost_story_full_qa as wrapper


@contextmanager
def temporary_env(**updates):
    previous = {name: os.environ.get(name) for name in updates}
    try:
        for name, value in updates.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def passing_env() -> dict[str, str]:
    return {**wrapper.EXPECTED_ENV, "OPENAI_API_KEY": "test-key-not-used"}


class FullQAGuardTests(unittest.TestCase):
    def test_missing_asr_cap_blocks_runtime_gate(self) -> None:
        values = passing_env()
        values["EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD"] = None
        with temporary_env(**values):
            errors = wrapper.runtime_gate_errors()
        self.assertTrue(any("EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD" in item for item in errors))

    def test_budget_uses_audio_duration_and_six_qa_samples(self) -> None:
        with temporary_env(**passing_env()):
            estimate = wrapper.budget_estimate(839.256)
        self.assertEqual(estimate["status"], "PASS")
        self.assertEqual(estimate["estimated_asr_usd"], 0.1119)
        self.assertEqual(estimate["estimated_listening_qa_usd"], 0.3)
        self.assertEqual(estimate["estimated_current_run_usd"], 0.4119)
        self.assertEqual(estimate["estimated_stage2b_and_stage2c_cumulative_usd"], 1.253)

    def test_budget_blocks_asr_over_cap(self) -> None:
        values = passing_env()
        values["EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD"] = "0.10"
        with temporary_env(**values):
            estimate = wrapper.budget_estimate(839.256)
        self.assertEqual(estimate["status"], "BLOCKED")
        self.assertTrue(any("ASR estimate" in item for item in estimate["blockers"]))

    def test_runtime_gate_blocks_before_provider_subprocess(self) -> None:
        values = passing_env()
        values["OPENAI_API_KEY"] = None
        with temporary_env(**values), mock.patch.object(sys, "argv", ["full_qa.py"]), mock.patch.object(
            wrapper.subprocess, "run"
        ) as run:
            code = wrapper.main()
        self.assertEqual(code, 2)
        run.assert_not_called()

    def test_repeat_guard_is_audio_hash_bound(self) -> None:
        result_path = mock.Mock()
        result_path.is_file.return_value = True
        result_path.read_text.return_value = '{"audio_hash":"same","provider_calls_ran":true}'
        with mock.patch.object(wrapper, "RESULT_PATH", result_path):
            self.assertIn("REPEAT_FULL_QA_ATTEMPT_BLOCKED", wrapper.completed_attempt_blocker("same"))
            self.assertEqual(wrapper.completed_attempt_blocker("different"), "")


if __name__ == "__main__":
    unittest.main()
