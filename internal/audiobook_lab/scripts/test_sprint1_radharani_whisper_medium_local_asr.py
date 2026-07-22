#!/usr/bin/env python3
"""Provider-free tests for the Radharani local Whisper-medium diagnostic."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sprint1_radharani_whisper_medium_local_asr.py")
SPEC = importlib.util.spec_from_file_location("radharani_local_whisper", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(module)


class RadharaniLocalWhisperTests(unittest.TestCase):
    def test_command_is_fixed_to_multilingual_medium_and_explicit_bengali(self) -> None:
        command = module.build_whisper_command(Path("sample.wav"), Path("private"))

        def value_after(flag: str) -> str:
            return command[command.index(flag) + 1]

        self.assertEqual(value_after("--model"), "medium")
        self.assertNotIn("medium.en", command)
        self.assertEqual(value_after("--language"), "bn")
        self.assertEqual(value_after("--task"), "transcribe")
        self.assertEqual(value_after("--word_timestamps"), "True")
        self.assertEqual(value_after("--temperature"), "0")
        self.assertEqual(value_after("--temperature_increment_on_fallback"), "None")
        self.assertNotIn("--initial_prompt", command)

    def test_time_metrics_parse_bsd_time_output(self) -> None:
        metrics = module.parse_time_metrics(
            "  12.34 real  40.50 user  2.25 sys\n"
            "  123456 maximum resident set size\n"
            "  2 page faults\n"
            "  0 swaps\n"
            "  789 peak memory footprint\n"
        )
        self.assertEqual(metrics["wall_seconds"], 12.34)
        self.assertEqual(metrics["user_cpu_seconds"], 40.5)
        self.assertEqual(metrics["maximum_resident_set_bytes"], 123456)
        self.assertEqual(metrics["peak_memory_footprint_bytes"], 789)

    def test_objective_gate_requires_score_order_boundaries_script_and_timestamps(self) -> None:
        passed = module.evaluate_transcript(
            "আমি বই পড়ি",
            "আমি বই পড়ি",
            word_timestamp_count=3,
        )
        self.assertTrue(passed["pass"])
        failed = module.evaluate_transcript(
            "আমি বই পড়ি",
            "আমি বই",
            word_timestamp_count=2,
        )
        self.assertFalse(failed["pass"])
        self.assertTrue(failed["blockers"])


if __name__ == "__main__":
    unittest.main()
