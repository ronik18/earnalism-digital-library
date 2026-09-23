#!/usr/bin/env python3
"""Regression coverage for final-status detection in focused-review evidence."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_book_commerce_final_review.py")
SPEC = importlib.util.spec_from_file_location("validate_book_commerce_final_review", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FinalStatusTests(unittest.TestCase):
    def test_machine_nonfinal_status_fails(self) -> None:
        self.assertTrue(MODULE.contains_nonfinal_status({"status": "PENDING"}))

    def test_evidence_prose_does_not_override_machine_results(self) -> None:
        self.assertFalse(MODULE.contains_nonfinal_status({"status": "PASS", "reason": "A historical action was NOT RUN."}))


if __name__ == "__main__":
    unittest.main()
