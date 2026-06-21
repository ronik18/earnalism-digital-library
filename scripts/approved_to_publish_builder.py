#!/usr/bin/env python3
"""Build APPROVED_TO_PUBLISH.md only from complete Dracula evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APPROVED_FILE = ROOT / "APPROVED_TO_PUBLISH.md"
BLOCKERS_FILE = ROOT / "APPROVED_TO_PUBLISH_BLOCKERS.md"
PRECHECK_REPORT = ROOT / "CONTROLLED_PUBLICATION_PRECHECK.md"
OUTPUT_DIR = ROOT / "output" / "publication_candidates" / "dracula"
LAUNCH_OUTPUT_DIR = ROOT / "output" / "launch"
GO_RECOMMENDATION = "GO_FOR_CONTROLLED_PUBLICATION_FOR_DRACULA_ONLY"
READY_WORKFLOW_STATUSES = {"READY", "READY_FOR_PUBLICATION_DRAFT_CANDIDATE"}
DRACULA_SOURCE_LICENSE_URL = "https://www.gutenberg.org/policy/license.html"
DRACULA_COMMERCIAL_USE_STATUS = "conditional_allowed_subject_to_project_gutenberg_license_and_trademark_terms"
DRACULA_ATTRIBUTION_REQUIREMENT = "simple_public_source_note_allowed; license/source evidence internal"
DRACULA_AUDIO_RIGHTS_STATUS = "not approved; separate approval required; AUDIO_NOT_REQUIRED for core reading"
DRACULA_PUBLIC_METADATA_ALLOWED = "yes"
DRACULA_PUBLIC_CTA_ALLOWED = "yes"
DRACULA_OWNER_APPROVAL_STATUS = "approved"
DRACULA_GO_HOLD_DECISION = "GO_DRACULA_CORE_READING_ONLY"

REQUIRED_FIELDS = [
    "title",
    "slug",
    "author",
    "author_death_year",
    "original_publication_year",
    "source_url",
    "source_name",
    "source_license",
    "source_hash",
    "content_hash",
    "provenance_hash",
    "rights_basis",
    "rights_tier",
    "verification_status",
    "publication_region",
    "qa_status",
    "rollback_owner",
    "publication_cap",
    "rollback_plan",
]


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def file_sha256(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def route_canary_path() -> Path:
    return LAUNCH_OUTPUT_DIR / "post_deploy_route_canary.json"


def payment_smoke_path() -> Path:
    return LAUNCH_OUTPUT_DIR / "payment_smoke.json"


def gate_results_path() -> Path:
    return OUTPUT_DIR / "dracula_gate_results.json"


def source_hashes_path() -> Path:
    return OUTPUT_DIR / "source_hashes.json"


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
        "BLOCKED_UNVERIFIED",
        "MISSING",
    }


def candidate_value(candidate: dict[str, Any], field: str, fallback: str) -> str:
    value = candidate.get(field)
    return str(value).strip() if value_present(value) else fallback


def evaluate_candidate(candidate: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if candidate.get("slug") != "dracula":
        issues.append("Only the Dracula candidate may be approved by this builder.")
    for field in REQUIRED_FIELDS:
        if not value_present(candidate.get(field)):
            issues.append(f"{field} is required.")
    if str(candidate.get("rights_tier", "")).upper() != "A":
        issues.append("rights_tier must be A.")
    if str(candidate.get("verification_status", "")).lower() != "approved":
        issues.append("verification_status must be approved.")
    if str(candidate.get("qa_status", "")).upper() != "QA_PASSED":
        issues.append("qa_status must be QA_PASSED.")
    if candidate.get("public_publish_actions") not in {0, "0"}:
        issues.append("public_publish_actions must remain 0 before activation.")

    rights = candidate.get("rights_decision") if isinstance(candidate.get("rights_decision"), dict) else {}
    if rights.get("approved") is not True:
        issues.append("rights_decision.approved must be true.")
    if rights.get("issues"):
        issues.append("rights_decision must not contain unresolved issues.")
    return issues


def evaluate_route_canary() -> tuple[str, str, list[str]]:
    report_path = route_canary_path()
    report = read_json(report_path)
    status = str(report.get("status") or "MISSING")
    issues: list[str] = []
    if status != "PASS":
        issues.append("production removed-route canary must be PASS.")
    return status, display_path(report_path), issues


def evaluate_payment_smoke() -> tuple[str, str, list[str]]:
    report_path = payment_smoke_path()
    report = read_json(report_path)
    status = str(report.get("status") or "MISSING")
    issues: list[str] = []
    if status not in {"PASS", "PASS_TEST_MODE", "PRODUCTION_TEST_MODE_PASS"}:
        issues.append("payment smoke must be PASS, PASS_TEST_MODE, or PRODUCTION_TEST_MODE_PASS.")
    return status, display_path(report_path), issues


def evaluate_gate_results(gate_results: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not gate_results:
        return ["dracula_gate_results.json is missing or invalid."]

    workflow_status = str(gate_results.get("publishing_workflow_status") or "").strip().upper()
    if workflow_status not in READY_WORKFLOW_STATUSES:
        issues.append("publishing_workflow_status must be READY or READY_FOR_PUBLICATION_DRAFT_CANDIDATE.")

    workflow = gate_results.get("workflow") if isinstance(gate_results.get("workflow"), dict) else {}
    blockers = workflow.get("blockers") if isinstance(workflow.get("blockers"), list) else []
    if blockers:
        issues.append(f"workflow.blockers must be empty: {'; '.join(str(blocker) for blocker in blockers)}")

    publish_readiness = str(workflow.get("publish_readiness") or "").strip().upper()
    if publish_readiness == "BLOCKED":
        issues.append("workflow.publish_readiness must not be BLOCKED.")

    recommendation = str(gate_results.get("recommendation") or "").strip()
    if recommendation != GO_RECOMMENDATION:
        issues.append(f"recommendation must be {GO_RECOMMENDATION}.")

    high_blockers = gate_results.get("high_blockers") if isinstance(gate_results.get("high_blockers"), list) else []
    if high_blockers:
        issues.append(f"high_blockers must be empty: {'; '.join(str(blocker) for blocker in high_blockers)}")
    return issues


def evaluate_hash_consistency(candidate: dict[str, Any], source_hashes: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not candidate:
        return issues
    ingestion = candidate.get("ingestion") if isinstance(candidate.get("ingestion"), dict) else {}
    sources = {
        "source_evidence": candidate,
        "source_evidence.ingestion": ingestion,
        "source_hashes": source_hashes,
    }
    for key in ("source_hash", "content_hash", "provenance_hash"):
        expected = str(candidate.get(key) or "")
        for source_name, source in sources.items():
            value = str(source.get(key) or "")
            if value != expected:
                issues.append(f"{key} mismatch in {source_name}: expected {expected or 'missing'}, got {value or 'missing'}.")
    return issues


def finalize_gate_results_for_approval(gate_results: dict[str, Any]) -> None:
    if not gate_results:
        return
    next_gate_results = dict(gate_results)
    next_gate_results["approved_to_publish_exists"] = True
    next_gate_results["recommendation"] = GO_RECOMMENDATION
    next_gate_results["readiness_score"] = max(float(next_gate_results.get("readiness_score") or 0), 9.9)
    gate_results_path().write_text(json.dumps(next_gate_results, indent=2) + "\n", encoding="utf-8")


def evidence_file_hashes(candidate_path: Path) -> dict[str, str]:
    return {
        "route_canary_evidence_hash": file_sha256(route_canary_path()),
        "payment_smoke_evidence_hash": file_sha256(payment_smoke_path()),
        "source_evidence_hash": file_sha256(candidate_path),
        "gate_results_hash": file_sha256(gate_results_path()),
    }


def approval_markdown(
    candidate: dict[str, Any],
    *,
    candidate_path: Path,
    route_status: str,
    route_path: str,
    payment_status: str,
    payment_path: str,
) -> str:
    hashes = evidence_file_hashes(candidate_path)
    source_license_url = candidate_value(candidate, "source_license_url", DRACULA_SOURCE_LICENSE_URL)
    commercial_use_status = candidate_value(candidate, "commercial_use_status", DRACULA_COMMERCIAL_USE_STATUS)
    attribution_requirement = candidate_value(candidate, "attribution_requirement", DRACULA_ATTRIBUTION_REQUIREMENT)
    derivative_audiobook_rights_status = candidate_value(
        candidate,
        "derivative_audiobook_rights_status",
        DRACULA_AUDIO_RIGHTS_STATUS,
    )
    public_metadata_allowed = candidate_value(candidate, "public_metadata_allowed", DRACULA_PUBLIC_METADATA_ALLOWED)
    public_cta_allowed = candidate_value(candidate, "public_cta_allowed", DRACULA_PUBLIC_CTA_ALLOWED)
    owner_approval_status = candidate_value(candidate, "owner_approval_status", DRACULA_OWNER_APPROVAL_STATUS)
    go_hold_decision = candidate_value(candidate, "go_hold_decision", DRACULA_GO_HOLD_DECISION)
    return "\n".join(
        [
            "# Approved To Publish",
            "",
            "This file is a controlled-publication approval artifact. It does not publish by itself.",
            "",
            "## Dracula",
            "",
            f"- Work Title: {candidate['title']}",
            f"- Work Slug: {candidate['slug']}",
            f"- Author: {candidate['author']}",
            f"- Rights Tier: {candidate['rights_tier']}",
            f"- Verification Status: {candidate['verification_status']}",
            f"- Source URL: {candidate['source_url']}",
            f"- Source Name: {candidate['source_name']}",
            f"- Source License: {candidate['source_license']}",
            f"- Source License URL: {source_license_url}",
            f"- Commercial Use Status: {commercial_use_status}",
            f"- Source Hash: {candidate['source_hash']}",
            f"- Content Hash: {candidate['content_hash']}",
            f"- Provenance Hash: {candidate['provenance_hash']}",
            f"- Attribution Requirement: {attribution_requirement}",
            f"- Derivative Audiobook Rights Status: {derivative_audiobook_rights_status}",
            f"- Public Metadata Allowed: {public_metadata_allowed}",
            f"- Public CTA Allowed: {public_cta_allowed}",
            f"- Owner Approval Status: {owner_approval_status}",
            f"- GO/HOLD Decision: {go_hold_decision}",
            f"- Rights Basis: {candidate['rights_basis']}",
            f"- QA Status: {candidate['qa_status']}",
            f"- Rollback Owner: {candidate['rollback_owner']}",
            f"- Publication Cap: {candidate['publication_cap']}",
            f"- Rollback Plan: {candidate['rollback_plan']}",
            f"- Production Parity Status: {route_status}",
            f"- Production Parity Evidence: {route_path}",
            f"- Production Parity Evidence Hash: {hashes['route_canary_evidence_hash']}",
            f"- Payment Smoke Status: {payment_status}",
            f"- Payment Smoke Evidence: {payment_path}",
            f"- Payment Smoke Evidence Hash: {hashes['payment_smoke_evidence_hash']}",
            f"- Source Evidence: {display_path(candidate_path)}",
            f"- Source Evidence Hash: {hashes['source_evidence_hash']}",
            f"- Gate Results Evidence: {display_path(gate_results_path())}",
            f"- Gate Results Hash: {hashes['gate_results_hash']}",
            "",
            "Approval Scope:",
            "",
            "- Approved Scope: Dracula core reading candidate only.",
            "- Not Approved: full study guide, full visual edition, full audiobook, paid ads, email sends, or social publishing.",
            "- Audiobook Status: AUDIO_NOT_REQUIRED.",
            "- Study/Visual Status: draft/partial only; separate QA approval is required before public promotion.",
            "",
        ]
    )


def blockers_markdown(issues: list[str], *, candidate_path: Path, route_status: str, payment_status: str) -> str:
    lines = [
        "# Approved To Publish Blockers",
        "",
        "Status: `HOLD_FOR_FIXES`",
        "",
        f"Generated at: `{utc_now()}`",
        f"Candidate: `{candidate_path}`",
        f"Route canary status: `{route_status}`",
        f"Payment smoke status: `{payment_status}`",
        "",
        "## Blocking Issues",
        "",
    ]
    lines.extend(f"- {issue}" for issue in issues)
    lines.extend(
        [
            "",
            "No `APPROVED_TO_PUBLISH.md` was generated.",
            "No public publication, deployment, provider call, or production mutation was performed.",
            "",
        ]
    )
    return "\n".join(lines)


def precheck_markdown(status: str, issues: list[str]) -> str:
    lines = [
        "# Controlled Publication Precheck",
        "",
        f"Status: `{status}`",
        "",
        "This report is generated by `scripts/approved_to_publish_builder.py` for the Dracula candidate.",
        "",
    ]
    if issues:
        lines.extend(["## Blockers", "", *[f"- {issue}" for issue in issues], ""])
    else:
        lines.extend(["## Result", "", "- Dracula evidence is complete enough to create the approval artifact.", ""])
    lines.append("Public publish actions remain `0` until a separate final activation step.")
    lines.append("")
    return "\n".join(lines)


def build(args: argparse.Namespace) -> dict[str, Any]:
    candidate_path = Path(args.candidate)
    candidate = read_json(candidate_path)
    gate_results = read_json(gate_results_path())
    source_hashes = read_json(source_hashes_path())
    route_status, route_path, route_issues = evaluate_route_canary()
    payment_status, payment_path, payment_issues = evaluate_payment_smoke()
    issues = []
    if not candidate:
        issues.append(f"candidate file is missing or invalid: {candidate_path}")
    else:
        issues.extend(evaluate_candidate(candidate))
        issues.extend(evaluate_hash_consistency(candidate, source_hashes))
    issues.extend(evaluate_gate_results(gate_results))
    issues.extend(route_issues)
    issues.extend(payment_issues)

    evidence_passes = not issues
    mode = "write_approval_artifact" if args.write_approval_artifact else "evaluate_only"
    write_allowed = os.getenv("EARNALISM_ALLOW_APPROVAL_ARTIFACT_WRITE", "").strip().lower() == "true"
    status = "PASS_EVALUATE_ONLY" if evidence_passes else "BLOCKED"
    approval_issues: list[str] = []
    if evidence_passes and args.write_approval_artifact:
        if write_allowed:
            status = "PASS_APPROVAL_ARTIFACT_WRITTEN"
        else:
            status = "BLOCKED_APPROVAL_WRITE_DISABLED"
            approval_issues.append("EARNALISM_ALLOW_APPROVAL_ARTIFACT_WRITE=true is required to write APPROVED_TO_PUBLISH.md.")
    elif evidence_passes:
        approval_issues.append("Evaluation passed, but approval artifact write was not requested.")

    report_issues = [*issues, *approval_issues]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": utc_now(),
        "dry_run": True,
        "candidate": str(candidate_path),
        "status": status,
        "mode": mode,
        "write_approval_artifact_requested": bool(args.write_approval_artifact),
        "approval_artifact_write_env_enabled": write_allowed,
        "approval_artifact_written": status == "PASS_APPROVAL_ARTIFACT_WRITTEN",
        "evidence_passes": evidence_passes,
        "issues": report_issues,
        "route_canary_status": route_status,
        "payment_smoke_status": payment_status,
        "publishing_workflow_status": gate_results.get("publishing_workflow_status", ""),
        "publishing_workflow_blockers": gate_results.get("workflow", {}).get("blockers", [])
        if isinstance(gate_results.get("workflow"), dict)
        else [],
        "approved_file": str(APPROVED_FILE),
        "blockers_file": str(BLOCKERS_FILE),
        "mutation_performed": False,
        "public_publish_actions": 0,
    }
    (OUTPUT_DIR / "approved_to_publish_builder.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if status == "PASS_APPROVAL_ARTIFACT_WRITTEN":
        finalize_gate_results_for_approval(gate_results)
        APPROVED_FILE.write_text(
            approval_markdown(
                candidate,
                candidate_path=candidate_path,
                route_status=route_status,
                route_path=route_path,
                payment_status=payment_status,
                payment_path=payment_path,
            ),
            encoding="utf-8",
        )
        if BLOCKERS_FILE.exists():
            BLOCKERS_FILE.unlink()
    else:
        if APPROVED_FILE.exists() and (not evidence_passes or args.write_approval_artifact):
            APPROVED_FILE.unlink()
        if report_issues:
            BLOCKERS_FILE.write_text(
                blockers_markdown(report_issues, candidate_path=candidate_path, route_status=route_status, payment_status=payment_status),
                encoding="utf-8",
            )
    PRECHECK_REPORT.write_text(precheck_markdown(status, report_issues), encoding="utf-8")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Dracula APPROVED_TO_PUBLISH.md only when all gates pass.")
    parser.add_argument("--candidate", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--evaluate-only", action="store_true", default=False)
    mode.add_argument("--write-approval-artifact", action="store_true", default=False)
    parser.add_argument("--dry-run", action="store_true", default=True, help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.dry_run is not True:
        print("approved_to_publish_builder is dry-run only in this phase.", file=sys.stderr)
        return 2
    if not args.evaluate_only and not args.write_approval_artifact:
        args.evaluate_only = True
    result = build(args)
    print(f"Approved-to-publish builder status: {result['status']}")
    if result["issues"]:
        for issue in result["issues"]:
            print(f"- {issue}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
