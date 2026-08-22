#!/usr/bin/env python3
"""Focused tests proving cleanup inventory generation is dry-run only."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RedesignInventoryTests(unittest.TestCase):
    def test_generator_writes_all_dry_run_inventories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "cleanup"
            completed = subprocess.run(
                [sys.executable, "scripts/generate_redesign_inventory.py", "--output-dir", str(output)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            expected = {
                "repository-inventory.json", "database-inventory.json", "media-reference-inventory.json",
                "orphan-candidates.json", "quarantine-manifest.json", "cost-baseline.json",
            }
            self.assertEqual({path.name for path in output.iterdir()}, expected)
            repository = json.loads((output / "repository-inventory.json").read_text(encoding="utf-8"))
            quarantine = json.loads((output / "quarantine-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(repository["mode"], "dry-run")
            self.assertGreater(repository["candidate_count"], 0)
            self.assertFalse(quarantine["deletion_allowed"])
            self.assertEqual(quarantine["entries"], [])
            self.assertEqual(quarantine["approved_candidate_count"], 0)
            self.assertEqual(
                quarantine["destructive_cleanup_status"],
                "DEFERRED_NO_APPROVED_CANDIDATES",
            )
            self.assertEqual(quarantine["destructive_actions_executed"], 0)
            self.assertEqual(quarantine["production_mutations"], 0)
            self.assertEqual(quarantine["quarantine_started_at"], "2026-08-22T09:46:55Z")
            self.assertEqual(quarantine["next_review_at"], "2026-09-21T09:46:55Z")


if __name__ == "__main__":
    unittest.main()
