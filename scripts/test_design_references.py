#!/usr/bin/env python3
"""Focused tests for the immutable reference contract."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DesignReferenceContractTests(unittest.TestCase):
    def test_reference_manifest_matches_immutable_files(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/verify_design_references.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(completed.stdout.count("PASS "), 3)


if __name__ == "__main__":
    unittest.main()
