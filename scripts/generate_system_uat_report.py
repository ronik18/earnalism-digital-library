#!/usr/bin/env python3
"""Fail closed System UAT report and run-manifest generator.

The report is intentionally derived from one machine-written manifest.  A
green-looking log copied from another checkout, a failed command, or a missing
browser/contrast gate must never produce a passing report.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
UAT = ROOT / "uat"
MANIFEST_NAME = "system-run-manifest.json"
REQUIRED_RUNS = {
    "backend-compile": {"min_passed": 1},
    "backend-core": {"dynamic_count_semantic_name": "pytest_passed_test_count"},
    "backend-policy": {"dynamic_count_semantic_name": "pytest_passed_test_count"},
    "frontend-full": {"dynamic_count_semantic_name": "jest_passed_test_count"},
    "frontend-build": {"min_passed": 1, "markers": ("Static SEO snapshot verifier: inspected=",)},
    "contracts": {"min_passed": 2, "markers": ("local-contracts=PASS", "production-network-requests=0")},
    "hydration": {"min_passed": 7, "markers": ("7 passed",)},
    "responsive": {"min_passed": 8, "markers": ("8 passed",)},
    "chromium-journeys": {"min_passed": 12, "markers": ("12 passed",)},
    "firefox-journeys": {"min_passed": 12, "markers": ("12 passed",)},
    "webkit-journeys": {"min_passed": 12, "markers": ("12 passed",)},
    "contrast": {"min_passed": 36, "markers": ("tested=36", "passed=36", "failed=0", "missing=0")},
}
PROVENANCE_MODES = {"ATTACHED_EXPECTED_BRANCH", "DETACHED_EXACT_REMOTE_AUTHORITY"}
DYNAMIC_COUNT_PARSERS = {
    "backend-core": ("pytest_passed_test_count", re.compile(r"(?m)^(?P<count>[1-9][0-9]*) passed(?:,.*)? in .+$")),
    "backend-policy": ("pytest_passed_test_count", re.compile(r"(?m)^(?P<count>[1-9][0-9]*) passed(?:,.*)? in .+$")),
    "frontend-full": ("jest_passed_test_count", re.compile(r"(?m)^Tests:\s+(?P<count>[1-9][0-9]*) passed,.*$")),
}
REPORT_ONLY_PATHS = {
    "uat/system-final-report.json",
    "uat/system-matrix.csv",
    "uat/system-state.json",
    "uat/system-defects.json",
    "uat/system-run-manifest.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iso8601(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp is not a string")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def local_endpoint(value: object, api: bool = False) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return (
        parsed.scheme == "http"
        and parsed.hostname == "127.0.0.1"
        and parsed.port is not None
        and (not api or parsed.path.rstrip("/") == "/api")
    )


def safe_log_path(value: object, root: Path) -> Path | None:
    if not isinstance(value, str) or value.startswith("/"):
        return None
    candidate = (root / value).resolve()
    allowed = (root / "uat" / "evidence").resolve()
    try:
        candidate.relative_to(allowed)
    except ValueError:
        return None
    return candidate


def manifest_path(root: Path = ROOT) -> Path:
    return root / "uat" / MANIFEST_NAME


def git_head(root: Path = ROOT) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def git_branch(root: Path = ROOT) -> str:
    return subprocess.check_output(["git", "branch", "--show-current"], cwd=root, text=True).strip()


def git_tree(root: Path = ROOT, revision: str = "HEAD") -> str:
    return subprocess.check_output(["git", "rev-parse", f"{revision}^{{tree}}"], cwd=root, text=True).strip()


def git_ref(root: Path, ref: str) -> str:
    return subprocess.check_output(["git", "rev-parse", "--verify", ref], cwd=root, text=True).strip()


def active_git_operation(root: Path) -> str | None:
    git_dir = Path(subprocess.check_output(["git", "rev-parse", "--git-dir"], cwd=root, text=True).strip())
    if not git_dir.is_absolute():
        git_dir = root / git_dir
    for name in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply"):
        if (git_dir / name).exists():
            return name
    return None


def clean_worktree(root: Path, *, allow_report_only: bool = False) -> bool:
    if not allow_report_only:
        return not subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip()
    changed = set(subprocess.check_output(["git", "diff", "--name-only", "HEAD"], cwd=root, text=True).splitlines())
    changed.update(subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], cwd=root, text=True).splitlines())
    return all(path in REPORT_ONLY_PATHS or path.startswith("uat/evidence/system-final-verification/") for path in changed)


def require_sha(value: object, field: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        errors.append(f"{field} must be a full git SHA")
        return None
    return value


def validate_provenance(payload: dict, *, root: Path, allow_report_only: bool = False) -> dict:
    errors: list[str] = []
    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        fail(["provenance is missing or invalid"])
    mode = provenance.get("mode")
    if mode not in PROVENANCE_MODES:
        errors.append("provenance mode is missing or invalid")
    if provenance.get("expected_repository_root") != str(root.resolve()):
        errors.append("expected repository root does not match the report root")
    expected_commit = require_sha(provenance.get("expected_commit"), "expected commit", errors)
    expected_tree = require_sha(provenance.get("expected_tree"), "expected tree", errors)
    try:
        validated_at = iso8601(provenance.get("validated_at"))
    except ValueError:
        validated_at = None
        errors.append("provenance validation timestamp is missing or invalid")
    if expected_commit is not None:
        try:
            subprocess.check_call(["git", "cat-file", "-e", f"{expected_commit}^{{commit}}"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if git_head(root) != expected_commit:
                errors.append("HEAD does not match the expected commit")
            if expected_tree is not None and git_tree(root) != expected_tree:
                errors.append("HEAD tree does not match the expected tree")
            if expected_tree is not None and git_tree(root, expected_commit) != expected_tree:
                errors.append("expected commit does not resolve to the expected tree")
        except subprocess.CalledProcessError:
            errors.append("expected commit object is unavailable locally")
    worktree_clean = clean_worktree(root, allow_report_only=allow_report_only)
    operation = active_git_operation(root)
    if payload.get("clean_worktree_before_execution") is not True or not worktree_clean:
        errors.append("worktree was not clean before execution")
    if operation is not None:
        errors.append(f"active Git operation is not allowed: {operation}")
    if mode == "ATTACHED_EXPECTED_BRANCH":
        expected_branch = provenance.get("expected_branch")
        if not isinstance(expected_branch, str) or not expected_branch:
            errors.append("expected branch is missing for attached provenance")
        elif git_branch(root) != expected_branch:
            errors.append("attached branch does not match the expected branch")
    elif mode == "DETACHED_EXACT_REMOTE_AUTHORITY":
        if git_branch(root):
            errors.append("detached provenance requires a branchless HEAD")
        remote_ref = provenance.get("expected_remote_ref")
        if not isinstance(remote_ref, str) or not re.fullmatch(r"refs/remotes/origin/[A-Za-z0-9._/-]+", remote_ref):
            errors.append("expected remote ref is missing or invalid")
        remote_sha = require_sha(provenance.get("expected_remote_ref_sha"), "expected remote ref SHA", errors)
        try:
            refreshed_at = iso8601(provenance.get("remote_ref_refreshed_at"))
            if validated_at is not None and refreshed_at > validated_at:
                errors.append("remote ref refresh is after provenance validation")
        except ValueError:
            errors.append("remote ref refresh timestamp is missing or invalid")
        if isinstance(remote_ref, str) and remote_sha is not None:
            try:
                if git_ref(root, remote_ref) != remote_sha:
                    errors.append("local remote ref does not match the expected remote SHA")
            except subprocess.CalledProcessError:
                errors.append("expected remote ref is unavailable locally")
        if expected_commit is not None and remote_sha is not None and remote_sha != expected_commit:
            errors.append("expected remote SHA does not match the expected commit")
    if errors:
        fail(errors)
    return {
        "mode": mode,
        "repository_root_classification": "exact_expected_repository_root",
        "head_sha": git_head(root),
        "tree_sha": git_tree(root),
        "branch_mode": "detached" if not git_branch(root) else "attached",
        "symbolic_branch": git_branch(root) or None,
        "expected_remote_ref": provenance.get("expected_remote_ref"),
        "expected_remote_sha": provenance.get("expected_remote_ref_sha"),
        "worktree_clean": worktree_clean,
        "active_git_operation": operation,
        "verification_result": "PASSED",
        "validated_at": validated_at,
        "expected_commit": expected_commit,
        "expected_tree": expected_tree,
    }


def observed_result_from_log(suite_id: str, text: str, log_sha256: str) -> dict | None:
    spec = DYNAMIC_COUNT_PARSERS.get(suite_id)
    if spec is None:
        return None
    semantic_name, parser = spec
    matches = list(parser.finditer(text))
    if len(matches) != 1:
        raise ValueError(f"{suite_id}: deterministic result parser did not find exactly one passing summary")
    return {
        "schema_version": "system-uat-observed-result-v1",
        "semantic_name": semantic_name,
        "value": int(matches[0].group("count")),
        "source_log_sha256": log_sha256,
    }


def report_only_since(root: Path, tested_head: str, current_head: str) -> bool:
    if tested_head == current_head:
        return True
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", f"{tested_head}..{current_head}"], cwd=root, text=True
    ).splitlines()
    return bool(changed) and all(path in REPORT_ONLY_PATHS or path.startswith("uat/evidence/system-final-verification/") for path in changed)


def fail(errors: list[str]) -> None:
    raise ValueError("; ".join(errors))


def report_tested_head(payload: object, requested_head: str | None, *, root: Path) -> str:
    if not isinstance(payload, dict):
        raise ValueError("run manifest must be a JSON object")
    manifest_head = payload.get("tested_code_head")
    if not isinstance(manifest_head, str) or not re.fullmatch(r"[0-9a-f]{40}", manifest_head):
        raise ValueError("tested_code_head must be a full git SHA")
    if requested_head is not None:
        if requested_head != manifest_head:
            raise ValueError("requested tested_code_head does not match the run manifest")
        return requested_head
    return git_head(root)


def validate_manifest(
    payload: object, *, root: Path = ROOT, current_head: str | None = None, require_finalized: bool = True
) -> dict:
    errors: list[str] = []
    if not isinstance(payload, dict):
        fail(["run manifest must be a JSON object"])
    if payload.get("schema_version") != "system-uat-run-manifest-v2":
        errors.append("unsupported or missing run-manifest schema")
    manifest_run_id = payload.get("run_id")
    if not isinstance(manifest_run_id, str) or not re.fullmatch(r"run-[A-Za-z0-9][A-Za-z0-9._-]*", manifest_run_id):
        errors.append("run_id is missing or invalid")
    try:
        provenance = validate_provenance(payload, root=root, allow_report_only=True)
    except ValueError as error:
        errors.append(str(error))
        provenance = None
    tested_head = payload.get("tested_code_head")
    if not isinstance(tested_head, str) or not re.fullmatch(r"[0-9a-f]{40}", tested_head):
        errors.append("tested_code_head must be a full git SHA")
    elif payload.get("tested_head") != tested_head:
        errors.append("tested_head and tested_code_head disagree")
    elif current_head is not None and not report_only_since(root, tested_head, current_head):
        errors.append("tested_code_head does not match current executable code HEAD")
    if provenance is not None and tested_head != provenance["expected_commit"]:
        errors.append("tested_code_head does not match the expected commit")
    scope_path = root / "uat" / "system-scope.json"
    if payload.get("scope_sha256") != sha256_file(scope_path):
        errors.append("scope SHA256 is missing or does not match the frozen scope")
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    if payload.get("scope_version") != scope.get("schema_version") or payload.get("included_case_count") != scope.get("total_included_case_count"):
        errors.append("scope version or included case count does not match the frozen scope")
    if scope.get("total_included_case_count") != 39:
        errors.append("the frozen System UAT scope must contain exactly 39 cases")
    endpoints = payload.get("redacted_local_endpoints")
    if not isinstance(endpoints, dict) or not local_endpoint(endpoints.get("frontend")) or not local_endpoint(endpoints.get("api"), api=True):
        errors.append("redacted local frontend/API endpoints are required")
    mongo = endpoints.get("mongodb") if isinstance(endpoints, dict) else ""
    if not isinstance(mongo, str) or not re.fullmatch(r"mongodb://127\.0\.0\.1:\d+/earnalism_uat\?replicaSet=earnalism-uat-rs0", mongo):
        errors.append("redacted local MongoDB endpoint is required")
    scope_note = payload.get("scope_decisions")
    backend_full = scope_note.get("backend_full") if isinstance(scope_note, dict) else None
    if not isinstance(backend_full, dict) or backend_full.get("required") is not False or not isinstance(backend_full.get("reason"), str):
        errors.append("backend-full scope decision is missing or ambiguous")
    if require_finalized and payload.get("aggregate_result") != "PASSED":
        errors.append("aggregate result is not finalized as PASSED")
    runs = payload.get("runs")
    if not isinstance(runs, list):
        fail(errors + ["runs must be a list"])
    by_id: dict[str, dict] = {}
    for suite_result in runs:
        if not isinstance(suite_result, dict) or not isinstance(suite_result.get("id"), str):
            errors.append("run entry is malformed")
            continue
        suite_id = suite_result["id"]
        if suite_id in by_id:
            errors.append(f"duplicate run id: {suite_id}")
        by_id[suite_id] = suite_result
    for suite_id, rule in REQUIRED_RUNS.items():
        suite_result = by_id.get(suite_id)
        if suite_result is None:
            errors.append(f"missing required run: {suite_id}")
            continue
        if not isinstance(suite_result.get("command"), str) or not suite_result["command"].strip():
            errors.append(f"{suite_id}: command is missing")
        try:
            started = iso8601(suite_result.get("started_at")); completed = iso8601(suite_result.get("completed_at"))
            if completed < started:
                errors.append(f"{suite_id}: completion precedes start")
            if provenance is not None and started < provenance["validated_at"]:
                errors.append(f"{suite_id}: evidence predates provenance validation")
        except ValueError:
            errors.append(f"{suite_id}: timestamps are missing or invalid")
        if suite_result.get("exit_code") != 0:
            errors.append(f"{suite_id}: nonzero exit code")
        totals = suite_result.get("totals")
        if not isinstance(totals, dict) or any(not isinstance(totals.get(key), int) or totals.get(key) < 0 for key in ("passed", "failed", "missing")):
            errors.append(f"{suite_id}: totals are missing or invalid")
            continue
        min_passed = rule.get("min_passed", 1)
        if totals["passed"] < min_passed or totals["failed"] != 0 or totals["missing"] != 0:
            errors.append(f"{suite_id}: totals are not passing")
        log_path = safe_log_path(suite_result.get("log"), root)
        if log_path is None or not log_path.is_file():
            errors.append(f"{suite_id}: log is missing or outside local evidence")
            continue
        expected_hash = suite_result.get("sha256")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash) or expected_hash != sha256_file(log_path):
            errors.append(f"{suite_id}: log SHA256 does not match")
            continue
        text = log_path.read_text(encoding="utf-8", errors="replace")
        markers = tuple(rule.get("markers", ())) + tuple(suite_result.get("required_markers", ()))
        if any(not isinstance(marker, str) or marker not in text for marker in markers):
            errors.append(f"{suite_id}: log is missing a required success marker")
        dynamic_semantic_name = rule.get("dynamic_count_semantic_name")
        if dynamic_semantic_name is not None:
            observed = suite_result.get("observed_result")
            if not isinstance(observed, dict) or observed.get("schema_version") != "system-uat-observed-result-v1" or observed.get("semantic_name") != dynamic_semantic_name or not isinstance(observed.get("value"), int) or observed["value"] < 1 or observed.get("source_log_sha256") != expected_hash:
                errors.append(f"{suite_id}: dynamic observed result is missing or invalid")
            else:
                try:
                    parsed = observed_result_from_log(suite_id, text, expected_hash)
                    if parsed != observed:
                        errors.append(f"{suite_id}: dynamic observed result does not match the deterministic log parser")
                    if totals["passed"] != observed["value"]:
                        errors.append(f"{suite_id}: totals passed does not match the dynamic observed result")
                except ValueError as error:
                    errors.append(str(error))
        if re.search(r"(?<![=\w])[1-9][0-9]*\s+(?:failed|errors?)\b", text, flags=re.IGNORECASE):
            errors.append(f"{suite_id}: log contradicts zero failures")
        if re.search(r"(?:failed|errors?)=[1-9][0-9]*\b", text, flags=re.IGNORECASE):
            errors.append(f"{suite_id}: log contradicts zero failures")
        if re.search(r"\bmissing=[1-9][0-9]*\b", text, flags=re.IGNORECASE):
            errors.append(f"{suite_id}: log contradicts zero missing")
    if errors:
        fail(errors)
    return {"run_id": manifest_run_id, "tested_head": tested_head, "endpoints": endpoints, "runs": by_id, "scope_decisions": scope_note, "provenance": provenance}


def validate_report_payload(report: object, validated_manifest: dict, *, provenance_tool_head: str) -> None:
    errors: list[str] = []
    if not isinstance(report, dict):
        fail(["generated report must be a JSON object"])
    if report.get("run_id") != validated_manifest["run_id"]:
        errors.append("report run_id does not match the manifest run_id")
    if report.get("tested_code_head") != validated_manifest["tested_head"]:
        errors.append("report tested_code_head does not match the manifest")
    if report.get("provenance_tool_head") != provenance_tool_head:
        errors.append("report provenance_tool_head does not match the generator HEAD")
    if report.get("totals") != {"PASS": 39, "FAILED": 0, "BLOCKED": 0, "UNTESTED": 0, "UNVERIFIED": 0}:
        errors.append("report totals do not match the frozen System UAT scope")
    if report.get("score") != 10.0 or report.get("result") != "PASSED" or report.get("final_system_uat_regression") != "PASSED":
        errors.append("report aggregate result is not passing")
    if report.get("provenance_validation") != "PASSED":
        errors.append("report provenance validation is not passing")
    if not isinstance(report.get("provenance"), dict) or report["provenance"].get("verification_result") != "PASSED":
        errors.append("report provenance record is not passing")
    if errors:
        fail(errors)


def case_evidence(runs: dict[str, dict]) -> dict[str, bool]:
    return {
        "BE-SYNTAX-001": "backend-compile" in runs,
        "BE-CONTROLLED-TRUTH-001": "backend-policy" in runs and "contracts" in runs,
        "BE-CANONICAL-PAGE-001": "backend-core" in runs and "contracts" in runs,
        "BE-READING-PASS-SECURITY-001": "backend-core" in runs,
        "BE-PAYMENT-IDEMPOTENCY-001": "backend-core" in runs,
        "BE-LEASE-CONCURRENCY-001": "backend-core" in runs,
        "FE-RELEASE-TRUTH-001": "frontend-full" in runs,
        "FE-MANIFEST-ACCESS-001": "frontend-full" in runs,
        "FE-PREVIEW-POLICY-001": "frontend-full" in runs,
        "FE-CTA-COPY-001": "frontend-full" in runs,
        "FE-CRA-MOUNT-001": "frontend-full" in runs and "hydration" in runs,
        "FE-PRODUCTION-BUILD-001": "frontend-build" in runs,
        "SYS-LOCAL-ENVIRONMENT-001": "contracts" in runs,
        "SYS-PRODUCTION-NETWORK-DENIAL-001": "contracts" in runs,
        "SYS-ROUTE-STATUS-001": "contracts" in runs,
        "SYS-API-CONTRACT-001": "contracts" in runs,
        **{f"PW-HYDRATION-{name}-001": "hydration" in runs for name in ("HOME", "LIBRARY", "BOOK", "READER", "PRICING", "JOURNAL", "CONTACT")},
        "PW-RESPONSIVE-001": "responsive" in runs,
        **{f"PW-CHROMIUM-JOURNEY-{index:02d}": "chromium-journeys" in runs for index in range(1, 13)},
        "PW-FIREFOX-001": "firefox-journeys" in runs,
        "PW-WEBKIT-001": "webkit-journeys" in runs,
        "SYS-CONTRAST-RESPONSIVE-001": "contrast" in runs,
    }


def generate_report(*, root: Path = ROOT, manifest: Path | None = None, tested_code_head: str | None = None) -> dict:
    uat = root / "uat"
    scope = json.loads((uat / "system-scope.json").read_text(encoding="utf-8"))
    manifest = manifest or manifest_path(root)
    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    validated = validate_manifest(manifest_payload, root=root, current_head=report_tested_head(manifest_payload, tested_code_head, root=root))
    evidence = case_evidence(validated["runs"])
    included = list(scope["included_system_cases"])
    rows = [{"case_id": case_id, "status": "PASS" if evidence.get(case_id, False) else "UNVERIFIED"} for case_id in included]
    totals = {key: sum(row["status"] == key for row in rows) for key in ("PASS", "FAILED", "BLOCKED", "UNTESTED", "UNVERIFIED")}
    complete = totals == {"PASS": len(included), "FAILED": 0, "BLOCKED": 0, "UNTESTED": 0, "UNVERIFIED": 0}
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    state = {
        "schema_version": "system-uat-state-v2",
        "generated_at": now,
        "environment": {"frontend_url": validated["endpoints"]["frontend"], "api_url": validated["endpoints"]["api"], "provenance_mode": validated["provenance"]["mode"], "head": validated["tested_head"]},
        "provenance": {key: value for key, value in validated["provenance"].items() if key not in {"validated_at"}},
        "run_id": validated["run_id"],
        "tested_code_head": validated["tested_head"],
        "provenance_tool_head": git_head(root),
        "scope_decisions": validated["scope_decisions"],
        "run_manifest": str(manifest.relative_to(root)),
        "run_manifest_sha256": sha256_file(manifest),
        "totals": totals,
        "included_case_count": len(included),
        "excluded_case_count": len(scope["excluded_manual_cases"]),
        "score": 10 * totals["PASS"] / len(included),
    }
    defects = [{"id": f"EVIDENCE-{row['case_id']}", "severity": "P1", "status": "UNVERIFIED", "case_id": row["case_id"]} for row in rows if row["status"] != "PASS"]
    report = {**state, "result": "PASSED" if complete else "INCOMPLETE", "final_system_uat_regression": manifest_payload["aggregate_result"], "completion_conditions_met": complete, "blocking_defect_ids": [entry["id"] for entry in defects], "evidence_paths": [run["log"] for run in validated["runs"].values()], "suite_results": manifest_payload["runs"], "provenance_validation": "PASSED"}
    validate_report_payload(report, validated, provenance_tool_head=git_head(root))
    with (uat / "system-matrix.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case_id", "status"])
        writer.writeheader(); writer.writerows(rows)
    (uat / "system-state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    (uat / "system-defects.json").write_text(json.dumps(defects, indent=2) + "\n", encoding="utf-8")
    (uat / "system-final-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return {"score": state["score"], **totals, "result": report["result"]}


def write_manifest(args: argparse.Namespace) -> None:
    path = Path(args.manifest).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if args.init:
        clean = args.clean_worktree_before_execution == "true"
        scope = json.loads((UAT / "system-scope.json").read_text(encoding="utf-8"))
        provenance = {
            "mode": args.provenance_mode,
            "expected_repository_root": args.expected_repository_root,
            "expected_commit": args.expected_commit,
            "expected_tree": args.expected_tree,
            "expected_branch": args.expected_branch,
            "expected_remote_ref": args.expected_remote_ref,
            "expected_remote_ref_sha": args.expected_remote_ref_sha,
            "remote_ref_refreshed_at": args.remote_ref_refreshed_at,
            "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }
        payload = {
            "schema_version": "system-uat-run-manifest-v2", "run_id": args.run_id,
            "tested_head": git_head(ROOT), "tested_code_head": git_head(ROOT),
            "clean_worktree_before_execution": clean, "scope_version": scope.get("schema_version"),
            "included_case_count": scope.get("total_included_case_count"), "aggregate_result": "RUNNING",
            "scope_sha256": sha256_file(UAT / "system-scope.json"),
            "redacted_local_endpoints": {"frontend": args.frontend, "api": args.api, "mongodb": args.mongodb},
            "provenance": provenance,
            "scope_decisions": {"backend_full": {"required": False, "reason": "The frozen 39-case scope and canonical runner require focused payment, ledger, security, concurrency, and controlled-release suites; repository-wide backend-full is not a System UAT case."}},
            "runs": [],
        }
        validate_provenance(payload, root=ROOT)
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
    if args.record:
        log = safe_log_path(args.log, ROOT)
        if log is None or not log.is_file():
            raise SystemExit("recorded log must exist beneath uat/evidence")
        log_sha256 = sha256_file(log)
        text = log.read_text(encoding="utf-8", errors="replace")
        observed_result = None
        if args.record in DYNAMIC_COUNT_PARSERS and args.exit_code == 0:
            if args.passed is not None:
                raise ValueError("dynamic count runs must not provide --passed")
            observed_result = observed_result_from_log(args.record, text, log_sha256)
            passed = observed_result["value"]
        else:
            passed = args.passed if args.passed is not None else 0
        payload["runs"].append({"id": args.record, "command": args.command, "started_at": args.started_at, "completed_at": args.completed_at, "exit_code": args.exit_code, "totals": {"passed": passed, "failed": args.failed, "missing": args.missing}, "log": args.log, "sha256": log_sha256, "required_markers": args.require, **({"observed_result": observed_result} if observed_result is not None else {})})
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def finalize_manifest(args: argparse.Namespace) -> None:
    path = Path(args.manifest).resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest(payload, root=ROOT, current_head=git_head(ROOT), require_finalized=False)
    payload["aggregate_result"] = "PASSED"
    payload["completed_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(manifest_path()))
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--finalize", action="store_true")
    parser.add_argument("--validate-report", action="store_true")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--tested-code-head")
    parser.add_argument("--clean-worktree-before-execution", default="")
    parser.add_argument("--provenance-mode", choices=sorted(PROVENANCE_MODES))
    parser.add_argument("--expected-repository-root")
    parser.add_argument("--expected-commit")
    parser.add_argument("--expected-tree")
    parser.add_argument("--expected-branch")
    parser.add_argument("--expected-remote-ref")
    parser.add_argument("--expected-remote-ref-sha")
    parser.add_argument("--remote-ref-refreshed-at")
    parser.add_argument("--record")
    parser.add_argument("--frontend")
    parser.add_argument("--api")
    parser.add_argument("--mongodb")
    parser.add_argument("--command", default="")
    parser.add_argument("--started-at", default="")
    parser.add_argument("--completed-at", default="")
    parser.add_argument("--exit-code", type=int, default=0)
    parser.add_argument("--passed", type=int)
    parser.add_argument("--failed", type=int, default=0)
    parser.add_argument("--missing", type=int, default=0)
    parser.add_argument("--log", default="")
    parser.add_argument("--require", action="append", default=[])
    args = parser.parse_args()
    try:
        if args.init or args.record:
            if args.init and not re.fullmatch(r"run-[0-9]{8}T[0-9]{6}Z-[0-9]+", args.run_id):
                raise ValueError("--run-id is required when initializing a manifest")
            if args.init and args.clean_worktree_before_execution not in {"true", "false"}:
                raise ValueError("--clean-worktree-before-execution is required when initializing a manifest")
            if args.init and (not args.provenance_mode or not args.expected_repository_root or not args.expected_commit or not args.expected_tree):
                raise ValueError("explicit provenance mode, root, commit, and tree are required when initializing a manifest")
            write_manifest(args)
            return
        if args.finalize:
            finalize_manifest(args)
            return
        if args.validate_report:
            manifest = Path(args.manifest).resolve()
            manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
            validated = validate_manifest(manifest_payload, root=ROOT, current_head=report_tested_head(manifest_payload, args.tested_code_head, root=ROOT))
            report = json.loads((UAT / "system-final-report.json").read_text(encoding="utf-8"))
            validate_report_payload(report, validated, provenance_tool_head=git_head(ROOT))
            print("system-uat-provenance=PASSED")
            return
        print(json.dumps(generate_report(manifest=Path(args.manifest).resolve(), tested_code_head=args.tested_code_head)))
    except (ValueError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"system-uat-provenance=REJECTED: {error}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
