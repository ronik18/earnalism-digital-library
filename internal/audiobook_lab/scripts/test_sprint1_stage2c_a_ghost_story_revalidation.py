#!/usr/bin/env python3
"""No-provider tests for Stage 2C sentence-aligned revalidation."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from internal.audiobook_lab.scripts import sprint1_stage2c_a_ghost_story_revalidation as stage2c


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


class Stage2CTests(unittest.TestCase):
    def test_middle_window_is_sentence_aligned_not_midword(self) -> None:
        middle = stage2c.sample_specs()[1]
        self.assertEqual(middle["start_time"], 353.66)
        self.assertEqual(middle["start_word"], "Then")
        self.assertEqual(middle["end_time"], 409.68)
        self.assertEqual(middle["end_word"], "eyes")
        self.assertNotEqual(middle["start_time"], 352.787)

    def test_sample_fingerprint_changes_with_boundaries(self) -> None:
        first = stage2c.sample_fingerprint("hash", stage2c.sample_specs(), "gpt-audio")
        changed = stage2c.sample_specs()
        changed[1]["start_time"] += 0.01
        second = stage2c.sample_fingerprint("hash", changed, "gpt-audio")
        self.assertNotEqual(first, second)

    def test_runtime_gates_fail_closed(self) -> None:
        with temporary_env(**{name: None for name in stage2c.EXPECTED_ENV}, OPENAI_API_KEY=None):
            errors = stage2c.runtime_gate_errors()
        self.assertEqual(len(errors), len(stage2c.EXPECTED_ENV) + 1)

    def test_owner_minimum_rejects_8_3_sample(self) -> None:
        samples = [
            {"scores": {"overall_listening_score": 9.5, "confidence_score": 0.95}},
            {"scores": {"overall_listening_score": 8.3, "confidence_score": 0.90}},
        ]
        result = stage2c.owner_minimum_result(samples, {field: False for field in stage2c.BINARY_LISTENING_FLAGS})
        self.assertFalse(result["passes"])
        self.assertEqual(result["minimum_overall_score"], 8.3)

    def test_owner_minimum_accepts_clean_9_4_samples(self) -> None:
        samples = [
            {"scores": {"overall_listening_score": 9.4, "confidence_score": 0.90}},
            {"scores": {"overall_listening_score": 9.8, "confidence_score": 0.95}},
        ]
        result = stage2c.owner_minimum_result(samples, {field: False for field in stage2c.BINARY_LISTENING_FLAGS})
        self.assertTrue(result["passes"])

    def test_repeat_attempt_guard_uses_sample_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            original = stage2c.RESULT_PATH
            stage2c.RESULT_PATH = Path(raw) / "runtime.json"
            try:
                stage2c.RESULT_PATH.write_text(
                    json.dumps({"sample_fingerprint": "same", "provider_calls_ran": True}),
                    encoding="utf-8",
                )
                self.assertTrue(stage2c.completed_attempt_exists("same"))
                self.assertFalse(stage2c.completed_attempt_exists("different"))
            finally:
                stage2c.RESULT_PATH = original


if __name__ == "__main__":
    unittest.main()
