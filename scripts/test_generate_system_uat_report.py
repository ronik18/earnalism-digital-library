#!/usr/bin/env python3
"""Focused fail-closed tests for System UAT provenance validation."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).with_name("generate_system_uat_report.py")
SPEC = importlib.util.spec_from_file_location("system_uat_report", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SystemUatProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "uat" / "evidence" / "system-final" / "run").mkdir(parents=True)
        (self.root / "uat" / "system-scope.json").write_text('{"scope":"frozen"}\n', encoding="utf-8")
        self.head = "a" * 40
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        self.payload = {
            "schema_version": "system-uat-run-manifest-v1",
            "tested_head": self.head,
            "scope_sha256": self.digest(self.root / "uat" / "system-scope.json"),
            "redacted_local_endpoints": {
                "frontend": "http://127.0.0.1:13000",
                "api": "http://127.0.0.1:18000/api",
                "mongodb": "mongodb://127.0.0.1:27018/earnalism_uat?replicaSet=earnalism-uat-rs0",
            },
            "scope_decisions": {"backend_full": {"required": False, "reason": "not in frozen scope"}},
            "runs": [],
        }
        markers = {
            "backend-compile": "compileall complete",
            "backend-core": "47 passed",
            "backend-policy": "8 passed",
            "frontend-full": "258 passed",
            "frontend-build": "Wrote 7 static snapshots",
            "contracts": "local-contracts=PASS\nproduction-network-requests=0",
            "hydration": "7 passed",
            "responsive": "8 passed",
            "chromium-journeys": "12 passed",
            "firefox-journeys": "12 passed",
            "webkit-journeys": "12 passed",
            "contrast": "tested=36\npassed=36\nfailed=0\nmissing=0",
        }
        for run_id, rule in MODULE.REQUIRED_RUNS.items():
            path = self.root / "uat" / "evidence" / "system-final" / "run" / f"{run_id}.log"
            path.write_text(markers[run_id] + "\n", encoding="utf-8")
            self.payload["runs"].append({
                "id": run_id, "command": f"local {run_id}", "started_at": now, "completed_at": now,
                "exit_code": 0, "totals": {"passed": rule["min_passed"], "failed": 0, "missing": 0},
                "log": str(path.relative_to(self.root)), "sha256": self.digest(path),
            })

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def assert_rejected(self, payload: dict, message: str) -> None:
        with self.assertRaisesRegex(ValueError, message):
            MODULE.validate_manifest(payload, root=self.root, current_head=self.head)

    def test_accepts_complete_current_manifest(self) -> None:
        MODULE.validate_manifest(self.payload, root=self.root, current_head=self.head)

    def test_rejects_stale_tested_head(self) -> None:
        payload = deepcopy(self.payload); payload["tested_head"] = "b" * 40
        self.assert_rejected(payload, "tested_head does not match")

    def test_rejects_missing_browser_evidence(self) -> None:
        payload = deepcopy(self.payload)
        payload["runs"] = [run for run in payload["runs"] if run["id"] != "webkit-journeys"]
        self.assert_rejected(payload, "missing required run: webkit-journeys")

    def test_rejects_nonzero_exit_even_with_green_log(self) -> None:
        payload = deepcopy(self.payload)
        next(run for run in payload["runs"] if run["id"] == "backend-core")["exit_code"] = 1
        self.assert_rejected(payload, "backend-core: nonzero exit code")

    def test_rejects_hash_drift_and_contradictory_log(self) -> None:
        payload = deepcopy(self.payload)
        run = next(run for run in payload["runs"] if run["id"] == "contrast")
        path = self.root / run["log"]
        path.write_text(path.read_text(encoding="utf-8") + "1 failed\n", encoding="utf-8")
        run["sha256"] = self.digest(path)
        self.assert_rejected(payload, "contrast: log contradicts zero failures")
        run["sha256"] = "0" * 64
        self.assert_rejected(payload, "contrast: log SHA256 does not match")


if __name__ == "__main__":
    unittest.main()
