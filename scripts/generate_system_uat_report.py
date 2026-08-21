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
    "backend-core": {"min_passed": 47, "markers": ("47 passed",)},
    "backend-policy": {"min_passed": 8, "markers": ("8 passed",)},
    "frontend-full": {"min_passed": 258, "markers": ("258 passed",)},
    "frontend-build": {"min_passed": 1, "markers": ("Wrote 7 static snapshots",)},
    "contracts": {"min_passed": 2, "markers": ("local-contracts=PASS", "production-network-requests=0")},
    "hydration": {"min_passed": 7, "markers": ("7 passed",)},
    "responsive": {"min_passed": 8, "markers": ("8 passed",)},
    "chromium-journeys": {"min_passed": 12, "markers": ("12 passed",)},
    "firefox-journeys": {"min_passed": 12, "markers": ("12 passed",)},
    "webkit-journeys": {"min_passed": 12, "markers": ("12 passed",)},
    "contrast": {"min_passed": 36, "markers": ("tested=36", "passed=36", "failed=0", "missing=0")},
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


def fail(errors: list[str]) -> None:
    raise ValueError("; ".join(errors))


def validate_manifest(payload: object, *, root: Path = ROOT, current_head: str | None = None) -> dict:
    errors: list[str] = []
    if not isinstance(payload, dict):
        fail(["run manifest must be a JSON object"])
    if payload.get("schema_version") != "system-uat-run-manifest-v1":
        errors.append("unsupported or missing run-manifest schema")
    tested_head = payload.get("tested_head")
    if not isinstance(tested_head, str) or not re.fullmatch(r"[0-9a-f]{40}", tested_head):
        errors.append("tested_head must be a full git SHA")
    elif current_head is not None and tested_head != current_head:
        errors.append("tested_head does not match current code HEAD")
    scope_path = root / "uat" / "system-scope.json"
    if payload.get("scope_sha256") != sha256_file(scope_path):
        errors.append("scope SHA256 is missing or does not match the frozen scope")
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
    runs = payload.get("runs")
    if not isinstance(runs, list):
        fail(errors + ["runs must be a list"])
    by_id: dict[str, dict] = {}
    for run in runs:
        if not isinstance(run, dict) or not isinstance(run.get("id"), str):
            errors.append("run entry is malformed")
            continue
        run_id = run["id"]
        if run_id in by_id:
            errors.append(f"duplicate run id: {run_id}")
        by_id[run_id] = run
    for run_id, rule in REQUIRED_RUNS.items():
        run = by_id.get(run_id)
        if run is None:
            errors.append(f"missing required run: {run_id}")
            continue
        if not isinstance(run.get("command"), str) or not run["command"].strip():
            errors.append(f"{run_id}: command is missing")
        try:
            if iso8601(run.get("completed_at")) < iso8601(run.get("started_at")):
                errors.append(f"{run_id}: completion precedes start")
        except ValueError:
            errors.append(f"{run_id}: timestamps are missing or invalid")
        if run.get("exit_code") != 0:
            errors.append(f"{run_id}: nonzero exit code")
        totals = run.get("totals")
        if not isinstance(totals, dict) or any(not isinstance(totals.get(key), int) or totals.get(key) < 0 for key in ("passed", "failed", "missing")):
            errors.append(f"{run_id}: totals are missing or invalid")
            continue
        if totals["passed"] < rule["min_passed"] or totals["failed"] != 0 or totals["missing"] != 0:
            errors.append(f"{run_id}: totals are not passing")
        log_path = safe_log_path(run.get("log"), root)
        if log_path is None or not log_path.is_file():
            errors.append(f"{run_id}: log is missing or outside local evidence")
            continue
        expected_hash = run.get("sha256")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash) or expected_hash != sha256_file(log_path):
            errors.append(f"{run_id}: log SHA256 does not match")
            continue
        text = log_path.read_text(encoding="utf-8", errors="replace")
        markers = tuple(rule.get("markers", ())) + tuple(run.get("required_markers", ()))
        if any(not isinstance(marker, str) or marker not in text for marker in markers):
            errors.append(f"{run_id}: log is missing a required success marker")
        if re.search(r"\b[1-9][0-9]* (?:failed|errors?)\b", text, flags=re.IGNORECASE):
            errors.append(f"{run_id}: log contradicts zero failures")
        if re.search(r"(?:failed|errors?)=[1-9][0-9]*\b", text, flags=re.IGNORECASE):
            errors.append(f"{run_id}: log contradicts zero failures")
        if re.search(r"\bmissing=[1-9][0-9]*\b", text, flags=re.IGNORECASE):
            errors.append(f"{run_id}: log contradicts zero missing")
    if errors:
        fail(errors)
    return {"tested_head": tested_head, "endpoints": endpoints, "runs": by_id}


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


def generate_report(*, root: Path = ROOT, manifest: Path | None = None) -> dict:
    uat = root / "uat"
    scope = json.loads((uat / "system-scope.json").read_text(encoding="utf-8"))
    manifest = manifest or manifest_path(root)
    validated = validate_manifest(json.loads(manifest.read_text(encoding="utf-8")), root=root, current_head=git_head(root))
    evidence = case_evidence(validated["runs"])
    included = list(scope["included_system_cases"])
    rows = [{"case_id": case_id, "status": "PASS" if evidence.get(case_id, False) else "UNVERIFIED"} for case_id in included]
    totals = {key: sum(row["status"] == key for row in rows) for key in ("PASS", "FAILED", "BLOCKED", "UNTESTED", "UNVERIFIED")}
    complete = totals == {"PASS": len(included), "FAILED": 0, "BLOCKED": 0, "UNTESTED": 0, "UNVERIFIED": 0}
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    state = {
        "schema_version": "system-uat-state-v2",
        "generated_at": now,
        "environment": {"frontend_url": validated["endpoints"]["frontend"], "api_url": validated["endpoints"]["api"], "worktree": str(root), "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=root, text=True).strip(), "head": validated["tested_head"]},
        "run_manifest": str(manifest.relative_to(root)),
        "run_manifest_sha256": sha256_file(manifest),
        "totals": totals,
        "included_case_count": len(included),
        "excluded_case_count": len(scope["excluded_manual_cases"]),
        "score": 10 * totals["PASS"] / len(included),
    }
    defects = [{"id": f"EVIDENCE-{row['case_id']}", "severity": "P1", "status": "UNVERIFIED", "case_id": row["case_id"]} for row in rows if row["status"] != "PASS"]
    report = {**state, "result": "PASSED" if complete else "INCOMPLETE", "completion_conditions_met": complete, "blocking_defect_ids": [entry["id"] for entry in defects], "evidence_paths": [run["log"] for run in validated["runs"].values()]}
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
        payload = {
            "schema_version": "system-uat-run-manifest-v1", "tested_head": git_head(ROOT),
            "scope_sha256": sha256_file(UAT / "system-scope.json"),
            "redacted_local_endpoints": {"frontend": args.frontend, "api": args.api, "mongodb": args.mongodb},
            "scope_decisions": {"backend_full": {"required": False, "reason": "The frozen 39-case scope and canonical runner require focused payment, ledger, security, concurrency, and controlled-release suites; repository-wide backend-full is not a System UAT case."}},
            "runs": [],
        }
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
    if args.record:
        log = safe_log_path(args.log, ROOT)
        if log is None or not log.is_file():
            raise SystemExit("recorded log must exist beneath uat/evidence")
        payload["runs"].append({"id": args.record, "command": args.command, "started_at": args.started_at, "completed_at": args.completed_at, "exit_code": args.exit_code, "totals": {"passed": args.passed, "failed": args.failed, "missing": args.missing}, "log": args.log, "sha256": sha256_file(log), "required_markers": args.require})
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(manifest_path()))
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--record")
    parser.add_argument("--frontend")
    parser.add_argument("--api")
    parser.add_argument("--mongodb")
    parser.add_argument("--command", default="")
    parser.add_argument("--started-at", default="")
    parser.add_argument("--completed-at", default="")
    parser.add_argument("--exit-code", type=int, default=0)
    parser.add_argument("--passed", type=int, default=0)
    parser.add_argument("--failed", type=int, default=0)
    parser.add_argument("--missing", type=int, default=0)
    parser.add_argument("--log", default="")
    parser.add_argument("--require", action="append", default=[])
    args = parser.parse_args()
    try:
        if args.init or args.record:
            write_manifest(args)
            return
        print(json.dumps(generate_report(manifest=Path(args.manifest).resolve())))
    except (ValueError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"system-uat-provenance=REJECTED: {error}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
