#!/usr/bin/env python3
"""Fail-safe controlled-publication precheck.

This script does not publish, deploy, call providers, or mutate production data.
It only verifies that the explicit publication approval artifact exists and
contains the minimum evidence required to begin a separate controlled
publication phase.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APPROVED_FILE = ROOT / "APPROVED_TO_PUBLISH.md"
OUTPUT_DIR = ROOT / "output" / "launch"
OUTPUT_FILE = OUTPUT_DIR / "controlled_publication_precheck.json"
REQUIRED_FIELDS = [
    "work_title",
    "work_slug",
    "rights_tier",
    "verification_status",
    "source_url",
    "source_name",
    "source_license",
    "source_hash",
    "content_hash",
    "provenance_hash",
    "rights_basis",
    "qa_status",
    "rollback_owner",
    "publication_cap",
    "rollback_plan",
    "production_parity_status",
    "production_parity_evidence",
    "payment_smoke_status",
    "payment_smoke_evidence",
]


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def parse_items(text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading = re.match(r"^#{2,6}\s+(.+)$", line)
        if heading:
            if current:
                items.append(current)
            current = {"work_title": heading.group(1).strip()}
            continue
        field = re.match(r"^(?:[-*]\s*)?([A-Za-z][A-Za-z0-9 _-]+)\s*:\s*(.+)$", line)
        if field:
            if not current:
                current = {}
            current[normalize_key(field.group(1))] = field.group(2).strip()
    if current:
        items.append(current)
    return [item for item in items if any(item.get(field) for field in REQUIRED_FIELDS)]


def value_present(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return bool(text) and text.upper() not in {
        "TBD",
        "TODO",
        "UNKNOWN",
        "SOURCE_METADATA_REQUIRED",
        "QA_REQUIRED",
    }


def evaluate_item(item: dict[str, str]) -> list[str]:
    issues: list[str] = []
    missing = [field for field in REQUIRED_FIELDS if not value_present(item.get(field))]
    if missing:
        issues.append(f"missing required fields: {', '.join(missing)}")
    if str(item.get("rights_tier", "")).strip().upper() != "A":
        issues.append("rights_tier must be Tier A")
    if str(item.get("verification_status", "")).strip().lower() != "approved":
        issues.append("verification_status must be approved")
    if str(item.get("qa_status", "")).strip().lower() not in {"pass", "passed", "qa_passed"}:
        issues.append("qa_status must pass")
    if str(item.get("production_parity_status", "")).strip().upper() != "PASS":
        issues.append("production_parity_status must be PASS")
    if str(item.get("payment_smoke_status", "")).strip().upper() not in {"PASS", "PASS_TEST_MODE", "PRODUCTION_TEST_MODE_PASS"}:
        issues.append("payment_smoke_status must be PASS, PASS_TEST_MODE, or PRODUCTION_TEST_MODE_PASS")
    for blocked_field in ("tier_b", "tier_c", "blocked_reason"):
        if value_present(item.get(blocked_field)):
            issues.append(f"{blocked_field} must be empty")
    return issues


def evaluate() -> dict[str, Any]:
    issues: list[str] = []
    items: list[dict[str, str]] = []
    if not APPROVED_FILE.exists():
        issues.append("APPROVED_TO_PUBLISH.md does not exist.")
    else:
        text = APPROVED_FILE.read_text(encoding="utf-8")
        items = parse_items(text)
        if not items:
            issues.append("APPROVED_TO_PUBLISH.md contains no parseable approved items.")

    item_results: list[dict[str, Any]] = []
    for item in items:
        item_issues = evaluate_item(item)
        item_results.append(
            {
                "work_slug": item.get("work_slug", ""),
                "work_title": item.get("work_title", ""),
                "pass": not item_issues,
                "issues": item_issues,
            }
        )
        issues.extend(f"{item.get('work_slug') or item.get('work_title')}: {issue}" for issue in item_issues)

    publication_cap_present = any(
        value_present(item.get("publication_cap")) or value_present(item.get("publication_cap_per_run"))
        for item in items
    )
    rollback_plan_present = any(value_present(item.get("rollback_plan")) for item in items)
    production_parity_pass = any(
        value_present(item.get("production_parity_evidence")) and str(item.get("production_parity_status", "")).upper() == "PASS"
        for item in items
    )
    payment_smoke_pass = any(
        value_present(item.get("payment_smoke_evidence"))
        and str(item.get("payment_smoke_status", "")).upper() in {"PASS", "PASS_TEST_MODE", "PRODUCTION_TEST_MODE_PASS"}
        for item in items
    )
    if items and not publication_cap_present:
        issues.append("publication cap is missing.")
    if items and not rollback_plan_present:
        issues.append("rollback plan is missing.")
    if items and not production_parity_pass:
        issues.append("production parity PASS evidence is missing.")
    if items and not payment_smoke_pass:
        issues.append("payment smoke PASS evidence is missing.")

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "PASS" if not issues else "BLOCKED",
        "approved_file": str(APPROVED_FILE),
        "items": item_results,
        "issues": issues,
        "required_fields": REQUIRED_FIELDS,
        "publication_cap_present": publication_cap_present,
        "rollback_plan_present": rollback_plan_present,
        "production_parity_pass": production_parity_pass,
        "payment_smoke_pass": payment_smoke_pass,
        "mutation_performed": False,
    }


def main() -> int:
    report = evaluate()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if report["status"] != "PASS":
        print("Controlled publication precheck BLOCKED.")
        for issue in report["issues"]:
            print(f"- {issue}")
        print(f"Report: {OUTPUT_FILE}")
        return 1
    print(f"Controlled publication precheck PASS. Report: {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
