#!/usr/bin/env python3
"""Provider-free tests for Bengali ASR calibration."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("bengali_asr_model_calibration.py")
SPEC = importlib.util.spec_from_file_location("bengali_asr_calibration", SCRIPT)
cal = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(cal)


class BengaliASRCalibrationTests(unittest.TestCase):
    def test_cost_uses_selected_duration_and_arm_count(self) -> None:
        self.assertEqual(cal.estimated_cost([{"duration_seconds": 120}], 2, 0.008), 0.032)

    def test_script_ratio_separates_bengali_and_devanagari(self) -> None:
        self.assertEqual(cal.script_ratio({"bengali": 9, "devanagari": 1, "latin": 0}), 0.9)

    def test_best_arm_prefers_release_pass(self) -> None:
        best = cal.best_arm(
            [
                {"status": "BELOW_THRESHOLD", "source_score": 9.9, "bengali_script_ratio": 1.0},
                {"status": "PASS", "source_score": 9.7, "bengali_script_ratio": 1.0},
            ]
        )
        self.assertEqual(best["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
