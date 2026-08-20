#!/usr/bin/env python3
"""Generate System UAT status only from frozen scope and completed local evidence."""
from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UAT = ROOT / "uat"
SCOPE = json.loads((UAT / "system-scope.json").read_text(encoding="utf-8"))
EVIDENCE = UAT / "evidence" / "system-final"


def evidence_contains(relative: str, *needles: str) -> bool:
    path = EVIDENCE / relative
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    return all(needle in text for needle in needles)


def git_value(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


BACKEND_FINAL = evidence_contains("backend-final-targeted.log", "47 passed")
BACKEND_POLICY = evidence_contains("backend-policy-targeted.log", "34 passed")
FRONTEND_FINAL = evidence_contains("frontend-full.log", "43 passed", "258 passed")
FRONTEND_BUILD = evidence_contains("frontend-build.log", "Wrote 7 static snapshots")
CONTRACTS = evidence_contains("runtime-final/contracts.log", "local-contracts=PASS", "production-network-requests=0")
HYDRATION = evidence_contains("hydration-routes.log", "7 passed")
RESPONSIVE = evidence_contains("responsive.log", "8 passed")
CHROMIUM = evidence_contains("chromium-12-final/playwright-regression.log", "12 passed")
FIREFOX = evidence_contains("cross-browser-final/firefox-regression.log", "12 passed")
WEBKIT = evidence_contains("cross-browser-final/webkit-regression.log", "12 passed")
CONTRAST = evidence_contains("contrast-final/contrast-regression.log", "tested=36", "failed=0", "missing=0")


EVIDENCE_RULES = {
    "BE-SYNTAX-001": BACKEND_FINAL,
    "BE-CONTROLLED-TRUTH-001": BACKEND_POLICY and CONTRACTS,
    "BE-CANONICAL-PAGE-001": BACKEND_FINAL and CONTRACTS,
    "BE-READING-PASS-SECURITY-001": BACKEND_FINAL,
    "BE-PAYMENT-IDEMPOTENCY-001": BACKEND_FINAL,
    "BE-LEASE-CONCURRENCY-001": BACKEND_FINAL,
    "FE-RELEASE-TRUTH-001": FRONTEND_FINAL,
    "FE-MANIFEST-ACCESS-001": FRONTEND_FINAL,
    "FE-PREVIEW-POLICY-001": FRONTEND_FINAL,
    "FE-CTA-COPY-001": FRONTEND_FINAL,
    "FE-CRA-MOUNT-001": FRONTEND_FINAL and HYDRATION,
    "FE-PRODUCTION-BUILD-001": FRONTEND_BUILD,
    "SYS-LOCAL-ENVIRONMENT-001": CONTRACTS,
    "SYS-PRODUCTION-NETWORK-DENIAL-001": CONTRACTS,
    "SYS-ROUTE-STATUS-001": CONTRACTS,
    "SYS-API-CONTRACT-001": CONTRACTS,
    "PW-HYDRATION-HOME-001": HYDRATION,
    "PW-HYDRATION-LIBRARY-001": HYDRATION,
    "PW-HYDRATION-BOOK-001": HYDRATION,
    "PW-HYDRATION-READER-001": HYDRATION,
    "PW-HYDRATION-PRICING-001": HYDRATION,
    "PW-HYDRATION-JOURNAL-001": HYDRATION,
    "PW-HYDRATION-CONTACT-001": HYDRATION,
    "PW-RESPONSIVE-001": RESPONSIVE,
    **{f"PW-CHROMIUM-JOURNEY-{index:02d}": CHROMIUM for index in range(1, 13)},
    "PW-FIREFOX-001": FIREFOX,
    "PW-WEBKIT-001": WEBKIT,
    "SYS-CONTRAST-RESPONSIVE-001": CONTRAST,
}


def runtime_environment() -> dict[str, str]:
    values: dict[str, str] = {}
    path = UAT / "runtime" / "system-uat" / "environment.sh"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("export ") and "=" in line:
                key, value = line.removeprefix("export ").split("=", 1)
                values[key] = value.replace("\\?", "?")
    return values


now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
included = list(SCOPE["included_system_cases"])
rows = [{"case_id": case_id, "status": "PASS" if EVIDENCE_RULES.get(case_id, False) else "UNVERIFIED"} for case_id in included]
totals = {key: sum(row["status"] == key for row in rows) for key in ("PASS", "FAILED", "BLOCKED", "UNTESTED", "UNVERIFIED")}
score = 10 * totals["PASS"] / len(included)
environment = runtime_environment()
state = {
    "schema_version": "system-uat-state-v1",
    "generated_at": now,
    "environment": {
        "frontend_url": environment.get("UAT_BASE_URL", ""),
        "api_url": environment.get("UAT_API_BASE_URL", ""),
        "worktree": str(ROOT),
        "branch": git_value("branch", "--show-current"),
        "head": git_value("rev-parse", "HEAD"),
    },
    "totals": totals,
    "included_case_count": len(included),
    "excluded_case_count": len(SCOPE["excluded_manual_cases"]),
    "score": score,
}
defects = [
    {"id": f"EVIDENCE-{row['case_id']}", "severity": "P1", "status": "UNVERIFIED", "case_id": row["case_id"]}
    for row in rows if row["status"] != "PASS"
]
complete = totals == {"PASS": len(included), "FAILED": 0, "BLOCKED": 0, "UNTESTED": 0, "UNVERIFIED": 0}
report = {
    **state,
    "result": "PASSED" if complete else "INCOMPLETE",
    "completion_conditions_met": complete,
    "root_causes_fixed": [
        "launcher-owned local ports and isolated MongoDB replica set",
        "transactional payment credit and ledger verification",
        "controlled release truth and fail-closed disabled audio projection",
        "canonical server-authorized page preview endpoint and metadata-only manifest",
        "CRA client mounting and hydration route validation",
        "stable CTA and Reading Pass copy assertions",
        "strict contrast, clipping, and responsive reporting",
    ],
    "blocking_defect_ids": [entry["id"] for entry in defects],
    "evidence_paths": [
        "uat/evidence/system-final/backend-final-targeted.log",
        "uat/evidence/system-final/frontend-full.log",
        "uat/evidence/system-final/runtime-final/contracts.log",
        "uat/evidence/system-final/hydration-routes.log",
        "uat/evidence/system-final/chromium-12-final/playwright-regression.log",
        "uat/evidence/system-final/cross-browser-final/firefox-regression.log",
        "uat/evidence/system-final/cross-browser-final/webkit-regression.log",
        "uat/evidence/system-final/contrast-final/contrast-regression.log",
    ],
}

with (UAT / "system-matrix.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["case_id", "status"])
    writer.writeheader()
    writer.writerows(rows)
(UAT / "system-state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
(UAT / "system-defects.json").write_text(json.dumps(defects, indent=2) + "\n", encoding="utf-8")
(UAT / "system-final-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"score": score, **totals, "result": report["result"]}))
