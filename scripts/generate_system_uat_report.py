#!/usr/bin/env python3
"""Emit System UAT artifacts from a frozen scope and observed local evidence."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UAT = ROOT / "uat"
SCOPE = json.loads((UAT / "system-scope.json").read_text(encoding="utf-8"))
EVIDENCE = "uat/evidence/system-final"
PASS = {
    "BE-SYNTAX-001", "BE-CONTROLLED-TRUTH-001", "BE-CANONICAL-PAGE-001",
    "BE-READING-PASS-SECURITY-001", "BE-LEASE-CONCURRENCY-001",
    "FE-RELEASE-TRUTH-001", "FE-MANIFEST-ACCESS-001", "FE-CTA-COPY-001",
    "FE-CRA-MOUNT-001", "FE-PRODUCTION-BUILD-001", "SYS-ROUTE-STATUS-001",
}
BLOCKED = {"SYS-LOCAL-ENVIRONMENT-001"}
BLOCKER = {
    "id": "ENV-LOCAL-PORT-8000-001",
    "severity": "P1",
    "scope": "local-uat-environment",
    "status": "BLOCKED_EXTERNAL",
    "command": "UAT_BASE_URL=http://127.0.0.1:3000 UAT_API_BASE_URL=http://127.0.0.1:8000/api bash scripts/start_local_uat.sh",
    "exit_code": 1,
    "error": "Uvicorn could not start the canonical backend because TCP 127.0.0.1:8000 is already occupied by an unrelated Python process (PID 9289).",
    "remediation_attempted": "Installed pinned backend dependencies in .venv-uat, repaired launcher child-liveness checks, local JWT, and test payment mode; did not terminate the unrelated process.",
    "evidence": f"{EVIDENCE}/local-launcher.log",
}


def status(case_id: str) -> str:
    if case_id in PASS:
        return "PASS"
    if case_id in BLOCKED:
        return "BLOCKED"
    return "UNTESTED"


now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
included = list(SCOPE["included_system_cases"])
rows = [{"case_id": case_id, "status": status(case_id)} for case_id in included]
totals = {key: sum(row["status"] == key for row in rows) for key in ("PASS", "FAILED", "BLOCKED", "UNTESTED", "UNVERIFIED")}
score = 10 * totals["PASS"] / len(included)

with (UAT / "system-matrix.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["case_id", "status"])
    writer.writeheader()
    writer.writerows(rows)

state = {
    "schema_version": "system-uat-state-v1",
    "generated_at": now,
    "environment": {
        "frontend_url": "http://127.0.0.1:3000",
        "api_url": "http://127.0.0.1:8000/api",
        "worktree": str(ROOT),
    },
    "totals": totals,
    "included_case_count": len(included),
    "excluded_case_count": len(SCOPE["excluded_manual_cases"]),
    "score": score,
}
(UAT / "system-state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
(UAT / "system-defects.json").write_text(json.dumps([BLOCKER], indent=2) + "\n", encoding="utf-8")
report = {
    **state,
    "result": "BLOCKED_EXTERNAL",
    "completion_conditions_met": False,
    "root_causes_fixed": [
        "local-only UAT endpoint enforcement", "CRA hydration misuse", "controlled audio release truth",
        "frontend manifest fail-closed merge", "canonical preview copy", "route status/noindex behavior",
        "launcher own-child liveness verification",
    ],
    "blocking_defect_ids": [BLOCKER["id"]],
    "evidence_paths": [
        f"{EVIDENCE}/backend-policy-targeted.log", f"{EVIDENCE}/frontend-targeted.log",
        f"{EVIDENCE}/frontend-build.log", f"{EVIDENCE}/local-launcher.log",
    ],
}
(UAT / "system-final-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"score": score, **totals, "result": report["result"]}))
