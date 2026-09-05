#!/usr/bin/env python3
"""Focused fail-closed tests for System UAT provenance and result evidence."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
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
        (self.root / ".gitignore").write_text("uat/evidence/\nuat/system-scope.json\n", encoding="utf-8")
        (self.root / "tracked.txt").write_text("baseline\n", encoding="utf-8")
        self.git("init", "-q")
        self.git("config", "user.email", "uat@example.test")
        self.git("config", "user.name", "System UAT")
        self.git("add", ".gitignore", "tracked.txt")
        self.git("commit", "-qm", "fixture")
        self.git("checkout", "-qb", "codex/test")
        self.head = self.git("rev-parse", "HEAD")
        self.tree = self.git("rev-parse", "HEAD^{tree}")
        (self.root / "uat" / "system-scope.json").write_text(
            json.dumps({"schema_version": "system-uat-scope-v1", "total_included_case_count": 39}) + "\n",
            encoding="utf-8",
        )
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        self.payload = {
            "schema_version": "system-uat-run-manifest-v2", "run_id": "run-20260821T000000Z-123",
            "tested_head": self.head, "tested_code_head": self.head,
            "clean_worktree_before_execution": True, "scope_version": "system-uat-scope-v1",
            "included_case_count": 39, "aggregate_result": "PASSED",
            "scope_sha256": self.digest(self.root / "uat" / "system-scope.json"),
            "redacted_local_endpoints": {
                "frontend": "http://127.0.0.1:13000",
                "api": "http://127.0.0.1:18000/api",
                "mongodb": "mongodb://127.0.0.1:27018/earnalism_uat?replicaSet=earnalism-uat-rs0",
            },
            "provenance": {
                "mode": "ATTACHED_EXPECTED_BRANCH", "expected_repository_root": str(self.root.resolve()),
                "expected_commit": self.head, "expected_tree": self.tree, "expected_branch": "codex/test",
                "expected_remote_ref": None, "expected_remote_ref_sha": None, "remote_ref_refreshed_at": None,
                "validated_at": now,
            },
            "scope_decisions": {"backend_full": {"required": False, "reason": "not in frozen scope"}},
            "runs": [],
        }
        markers = {
            "backend-compile": "compileall complete",
            "backend-core": "11 passed in 0.1s",
            "backend-policy": "4 passed in 0.1s",
            "frontend-full": "Tests:       17 passed, 17 total",
            "frontend-build": "Static SEO snapshot verifier: inspected=142",
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
            log_sha256 = self.digest(path)
            observed = MODULE.observed_result_from_log(run_id, markers[run_id], log_sha256)
            passed = observed["value"] if observed else rule["min_passed"]
            run = {
                "id": run_id, "command": f"local {run_id}", "started_at": now, "completed_at": now,
                "exit_code": 0, "totals": {"passed": passed, "failed": 0, "missing": 0},
                "log": str(path.relative_to(self.root)), "sha256": log_sha256,
            }
            if observed:
                run["observed_result"] = observed
            self.payload["runs"].append(run)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=self.root, text=True).strip()

    @staticmethod
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def assert_rejected(self, payload: dict, message: str) -> None:
        with self.assertRaisesRegex(ValueError, message):
            MODULE.validate_manifest(payload, root=self.root, current_head=self.head)

    def suite(self, run_id: str, payload: dict | None = None) -> dict:
        payload = payload or self.payload
        return next(run for run in payload["runs"] if run["id"] == run_id)

    def test_accepts_complete_attached_manifest(self) -> None:
        MODULE.validate_manifest(self.payload, root=self.root, current_head=self.head)

    def test_accepts_detached_exact_remote_authority(self) -> None:
        self.git("update-ref", "refs/remotes/origin/main", self.head)
        self.git("checkout", "--detach", "-q", self.head)
        payload = deepcopy(self.payload)
        payload["provenance"].update({
            "mode": "DETACHED_EXACT_REMOTE_AUTHORITY", "expected_branch": None,
            "expected_remote_ref": "refs/remotes/origin/main", "expected_remote_ref_sha": self.head,
            "remote_ref_refreshed_at": payload["provenance"]["validated_at"],
        })
        MODULE.validate_manifest(payload, root=self.root, current_head=self.head)

    def test_rejects_wrong_branch_sha_tree_or_repository_root(self) -> None:
        for key, value, message in (
            ("expected_branch", "codex/other", "attached branch does not match"),
            ("expected_commit", "b" * 40, "expected commit object is unavailable"),
            ("expected_tree", "b" * 40, "HEAD tree does not match the expected tree"),
            ("expected_repository_root", "/sanitized/wrong-root", "expected repository root does not match"),
        ):
            payload = deepcopy(self.payload)
            payload["provenance"][key] = value
            self.assert_rejected(payload, message)

    def test_rejects_dirty_worktree(self) -> None:
        (self.root / "tracked.txt").write_text("changed\n", encoding="utf-8")
        self.assert_rejected(self.payload, "worktree was not clean")

    def test_rejects_missing_or_stale_remote_authority(self) -> None:
        self.git("update-ref", "refs/remotes/origin/main", self.head)
        self.git("checkout", "--detach", "-q", self.head)
        payload = deepcopy(self.payload)
        payload["provenance"].update({
            "mode": "DETACHED_EXACT_REMOTE_AUTHORITY", "expected_branch": None,
            "expected_remote_ref": "refs/remotes/origin/main", "expected_remote_ref_sha": self.head,
            "remote_ref_refreshed_at": None,
        })
        self.assert_rejected(payload, "remote ref refresh timestamp is missing")
        payload = deepcopy(payload)
        payload["provenance"]["remote_ref_refreshed_at"] = payload["provenance"]["validated_at"]
        payload["provenance"]["expected_remote_ref_sha"] = "b" * 40
        self.assert_rejected(payload, "local remote ref does not match")

    def test_rejects_missing_expected_sha_tree_and_remote_authority(self) -> None:
        for key, message in (
            ("expected_commit", "expected commit must be a full git SHA"),
            ("expected_tree", "expected tree must be a full git SHA"),
        ):
            payload = deepcopy(self.payload)
            payload["provenance"][key] = None
            self.assert_rejected(payload, message)
        self.git("update-ref", "refs/remotes/origin/main", self.head)
        self.git("checkout", "--detach", "-q", self.head)
        payload = deepcopy(self.payload)
        payload["provenance"].update({
            "mode": "DETACHED_EXACT_REMOTE_AUTHORITY", "expected_branch": None,
            "expected_remote_ref": None, "expected_remote_ref_sha": self.head,
            "remote_ref_refreshed_at": payload["provenance"]["validated_at"],
        })
        self.assert_rejected(payload, "expected remote ref is missing")

    def test_rejects_detached_ancestor_and_unpushed_descendant(self) -> None:
        self.git("update-ref", "refs/remotes/origin/main", self.head)
        (self.root / "tracked.txt").write_text("descendant\n", encoding="utf-8")
        self.git("add", "tracked.txt")
        self.git("commit", "-qm", "descendant")
        descendant = self.git("rev-parse", "HEAD")
        self.git("checkout", "--detach", "-q", descendant)
        payload = deepcopy(self.payload)
        payload["provenance"].update({
            "mode": "DETACHED_EXACT_REMOTE_AUTHORITY", "expected_branch": None,
            "expected_remote_ref": "refs/remotes/origin/main", "expected_remote_ref_sha": self.head,
            "remote_ref_refreshed_at": payload["provenance"]["validated_at"],
        })
        self.assert_rejected(payload, "HEAD does not match the expected commit")
        self.git("update-ref", "refs/remotes/origin/main", descendant)
        self.git("checkout", "--detach", "-q", self.head)
        payload["provenance"].update({"expected_commit": descendant, "expected_tree": self.git("rev-parse", f"{descendant}^{{tree}}"), "expected_remote_ref_sha": descendant})
        self.assert_rejected(payload, "HEAD does not match the expected commit")

    def test_rejects_active_git_operation(self) -> None:
        git_dir = self.root / self.git("rev-parse", "--git-dir")
        (git_dir / "MERGE_HEAD").write_text(self.head + "\n", encoding="utf-8")
        self.assert_rejected(self.payload, "active Git operation is not allowed")

    def test_provenance_mode_is_recorded_without_repository_path(self) -> None:
        provenance = MODULE.validate_manifest(self.payload, root=self.root, current_head=self.head)["provenance"]
        self.assertEqual(provenance["mode"], "ATTACHED_EXPECTED_BRANCH")
        self.assertEqual(provenance["repository_root_classification"], "exact_expected_repository_root")
        self.assertNotIn("expected_repository_root", provenance)

    def test_dynamic_counts_are_derived_from_current_log_summaries(self) -> None:
        validated = MODULE.validate_manifest(self.payload, root=self.root, current_head=self.head)
        self.assertEqual(self.suite("backend-core")["observed_result"]["semantic_name"], "pytest_passed_test_count")
        self.assertEqual(self.suite("frontend-full")["observed_result"]["semantic_name"], "jest_passed_test_count")
        self.assertEqual(validated["runs"]["backend-policy"]["totals"]["passed"], self.suite("backend-policy")["observed_result"]["value"])

    def test_rejects_missing_malformed_or_mismatched_dynamic_count(self) -> None:
        payload = deepcopy(self.payload)
        self.suite("backend-core", payload).pop("observed_result")
        self.assert_rejected(payload, "dynamic observed result is missing")
        payload = deepcopy(self.payload)
        self.suite("backend-core", payload)["totals"]["passed"] += 1
        self.assert_rejected(payload, "totals passed does not match")
        payload = deepcopy(self.payload)
        run = self.suite("frontend-full", payload)
        path = self.root / run["log"]
        path.write_text("Tests:       no total available\n", encoding="utf-8")
        run["sha256"] = self.digest(path)
        run["observed_result"]["source_log_sha256"] = run["sha256"]
        self.assert_rejected(payload, "deterministic result parser")

    def test_accepts_a_second_synthetic_dynamic_count_set(self) -> None:
        payload = deepcopy(self.payload)
        for run_id, summary in (
            ("backend-core", "23 passed in 0.2s\n"),
            ("backend-policy", "6 passed in 0.2s\n"),
            ("frontend-full", "Tests:       31 passed, 31 total\n"),
        ):
            run = self.suite(run_id, payload)
            path = self.root / run["log"]
            path.write_text(summary, encoding="utf-8")
            run["sha256"] = self.digest(path)
            run["observed_result"] = MODULE.observed_result_from_log(run_id, summary, run["sha256"])
            run["totals"]["passed"] = run["observed_result"]["value"]
        MODULE.validate_manifest(payload, root=self.root, current_head=self.head)

    def test_rejects_dynamic_type_schema_hash_duplicate_and_log_noise_defects(self) -> None:
        payload = deepcopy(self.payload)
        self.suite("backend-core", payload)["observed_result"]["value"] = "11"
        self.assert_rejected(payload, "dynamic observed result is missing")
        payload = deepcopy(self.payload)
        self.suite("backend-core", payload)["observed_result"]["value"] = -1
        self.assert_rejected(payload, "dynamic observed result is missing")
        payload = deepcopy(self.payload)
        self.suite("backend-core", payload)["observed_result"]["schema_version"] = "unsupported"
        self.assert_rejected(payload, "dynamic observed result is missing")
        payload = deepcopy(self.payload)
        self.suite("backend-core", payload)["observed_result"]["source_log_sha256"] = "0" * 64
        self.assert_rejected(payload, "dynamic observed result is missing")
        payload = deepcopy(self.payload)
        payload["runs"].append(deepcopy(self.suite("backend-core", payload)))
        self.assert_rejected(payload, "duplicate run id")
        payload = deepcopy(self.payload)
        run = self.suite("backend-core", payload)
        path = self.root / run["log"]
        path.write_text("noise: 999 passed without a terminal summary\n11 passed in 0.1s\n", encoding="utf-8")
        run["sha256"] = self.digest(path)
        run["observed_result"] = MODULE.observed_result_from_log(run["id"], path.read_text(encoding="utf-8"), run["sha256"])
        MODULE.validate_manifest(payload, root=self.root, current_head=self.head)

    def test_rejects_report_run_id_different_from_manifest(self) -> None:
        validated = MODULE.validate_manifest(self.payload, root=self.root, current_head=self.head)
        report = {
            "run_id": "contrast", "tested_code_head": self.head, "provenance_tool_head": self.head,
            "totals": {"PASS": 39, "FAILED": 0, "BLOCKED": 0, "UNTESTED": 0, "UNVERIFIED": 0},
            "score": 10.0, "result": "PASSED", "final_system_uat_regression": "PASSED", "provenance_validation": "PASSED",
        }
        with self.assertRaisesRegex(ValueError, "report run_id does not match"):
            MODULE.validate_report_payload(report, validated, provenance_tool_head=self.head)

    def test_rejects_scope_and_run_evidence_failures(self) -> None:
        payload = deepcopy(self.payload)
        payload["runs"] = [run for run in payload["runs"] if run["id"] != "webkit-journeys"]
        self.assert_rejected(payload, "missing required run: webkit-journeys")
        payload = deepcopy(self.payload)
        self.suite("contrast", payload)["exit_code"] = 1
        self.assert_rejected(payload, "contrast: nonzero exit code")


if __name__ == "__main__":
    unittest.main()
