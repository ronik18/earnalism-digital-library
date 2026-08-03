#!/usr/bin/env python3
"""Fail-closed canonical publication-workflow migration.

Filesystem mode is a dry-run. Mongo mode performs a complete preflight first;
``--apply`` is allowed only when every record has controlled artifacts,
authoritative evidence, zero conflicts, and a valid canonical result.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any


REQUIRED = ("public_book.json", "reader_manifest.json", "source_evidence.json", "approval_evidence.json", "checksum_manifest.json")

from backend.publication_workflow_schema import (
    SCHEMA_NAME,
    SCHEMA_VERSION,
    migrate_books_dry_run,
    normalize_publication_workflow,
    validate_publication_workflow,
)
from backend.catalog_truth import controlled_artifact_validation_issues


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def artifact_for(roots: list[Path], slug: str) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    candidates = [root / slug for root in roots if (root / slug).is_dir()]
    directory = max(candidates, key=lambda path: sum((path / name).is_file() for name in REQUIRED), default=roots[0] / slug)
    issues: list[str] = []
    if not directory.is_dir():
        return {}, {}, [f"missing controlled artifact directory: {slug}"]
    public_book = load_json(directory / "public_book.json")
    approval = load_json(directory / "approval_evidence.json")
    if not public_book:
        issues.append(f"missing or invalid public_book.json: {slug}")
    if not approval:
        issues.append(f"missing or invalid approval_evidence.json: {slug}")
    if public_book.get("slug") != slug:
        issues.append(f"artifact slug mismatch: {slug}")
    if approval.get("slug") not in (None, slug):
        issues.append(f"evidence slug mismatch: {slug}")
    if public_book.get("approved_to_publish") is not True or approval.get("approved_to_publish") is not True:
        issues.append(f"publication approval is not proven: {slug}")
    return public_book, approval, issues


def mongo_report(*, root: Path, apply: bool, report_path: Path, skip_slugs: set[str]) -> int:
    mongo_url = os.environ.get("MONGODB_URL") or os.environ.get("MONGO_URL")
    if not mongo_url:
        raise SystemExit("BLOCKED: MONGODB_URL or MONGO_URL is required for --mongo")
    try:
        from pymongo import MongoClient
    except ImportError as exc:
        raise SystemExit(f"BLOCKED: pymongo is required for --mongo: {exc}") from exc
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=15000, uuidRepresentation="standard")
    client.admin.command("ping")
    db_name = os.environ.get("MONGODB_DB_NAME") or os.environ.get("DB_NAME")
    if not db_name:
        db_name = mongo_url.rsplit("/", 1)[-1].split("?", 1)[0] or "earnalism"
    collection = client[db_name][os.environ.get("MONGODB_BOOKS_COLLECTION", "books")]
    books = list(collection.find({}, {"_id": 0}))
    results: list[dict[str, Any]] = []
    for book in books:
        slug = str(book.get("slug") or "").strip()
        if slug in skip_slugs:
            continue
        artifact, evidence, artifact_issues = artifact_for(
            [root, root.parent.parent.parent / "data" / "controlled_publications"], slug
        ) if slug else ({}, {}, ["book is missing slug"])
        result = normalize_publication_workflow(book, approved_artifact=artifact, release_evidence=evidence)
        issues = artifact_issues + validate_publication_workflow(result.workflow)
        if artifact.get("audio_enabled") is True or artifact.get("audiobook_enabled") is True or evidence.get("audiobook_enabled") is True:
            artifact_dir = next((candidate for candidate in (root / slug, root.parent.parent.parent / "data" / "controlled_publications" / slug) if candidate.is_dir()), root / slug)
            issues.extend(controlled_artifact_validation_issues(slug, str(artifact_dir)))
        if not result.workflow.get("publication", {}).get("reader_exposed") and book.get("is_published"):
            issues.append("reader exposure is not explicitly proven; PUBLISHED was not used as proof")
        if result.workflow.get("publication", {}).get("audio_exposed"):
            required = ("release_status", "qa_status", "sidecars_complete", "synchronization_verified", "checksum_verified", "endpoint_verified")
            if any(not result.workflow.get("audio", {}).get(field) for field in required):
                issues.append("audio exposure lacks complete release-gate evidence")
        results.append({
            "slug": slug,
            "before_sha256": digest(book.get("publication_workflow")),
            "after_sha256": digest(result.workflow),
            "changed": result.changed,
            "conflicts": result.conflicts,
            "issues": sorted(set(issues)),
            "workflow": result.workflow,
            "audit_event": result.audit_event,
        })
    # Conflicts are retained in the report, but precedence resolves them. Only
    # artifact/evidence/validation issues are unresolved and can block writes.
    unresolved = sum(bool(item["issues"]) for item in results)
    report: dict[str, Any] = {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "mode": "apply" if apply else "preflight",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "book_count": len(results),
        "changed_count": sum(item["changed"] for item in results),
        "conflict_count": sum(len(item["conflicts"]) for item in results),
        "unresolved_count": unresolved,
        "writes_performed": 0,
        "results": results,
    }
    if apply and unresolved:
        report["status"] = "BLOCKED_UNRESOLVED_CONFLICTS"
    elif apply:
        for item in results:
            if not item["changed"]:
                continue
            slug = item["slug"]
            event = dict(item["audit_event"])
            event["event_id"] = digest({"slug": slug, "workflow_sha256": item["after_sha256"]})
            update = {"$set": {"publication_workflow": item["workflow"]}, "$addToSet": {"publication_workflow_audit": event}}
            collection.update_one({"slug": slug}, update)
            reread = collection.find_one({"slug": slug}, {"_id": 0}) or {}
            observed = digest(reread.get("publication_workflow"))
            item["reread_sha256"] = observed
            if observed != item["after_sha256"]:
                item["issues"].append("post-write hash mismatch")
                break
            report["writes_performed"] += 1
        report["status"] = "APPLIED" if not any(item["issues"] for item in results) else "APPLIED_WITH_VERIFICATION_FAILURE"
    else:
        report["status"] = "PREFLIGHT_BLOCKED" if unresolved else "PREFLIGHT_READY"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"books={report['book_count']} changed={report['changed_count']} conflicts={report['conflict_count']} unresolved={report['unresolved_count']} status={report['status']}")
    print(f"wrote={report_path}")
    return 0 if report["status"] in {"PREFLIGHT_READY", "APPLIED"} else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, nargs="?", help="JSON file or controlled-publications directory")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mongo", action="store_true")
    parser.add_argument("--artifact-root", type=Path, default=Path("backend/data/controlled_publications"))
    parser.add_argument("--apply", action="store_true", help="write only after a clean Mongo preflight")
    parser.add_argument("--skip-slug", action="append", default=[], help="exclude explicitly deferred slugs")
    args = parser.parse_args()
    if args.mongo:
        return mongo_report(root=args.artifact_root, apply=args.apply, report_path=args.output, skip_slugs=set(args.skip_slug))
    if args.input is None:
        raise SystemExit("input is required unless --mongo is used")
    if args.input.is_dir():
        books = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(args.input.glob("**/public_book.json"))
        ]
    else:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        books = payload if isinstance(payload, list) else payload.get("books", [])
    if not isinstance(books, list):
        raise SystemExit("input must be a JSON list or an object with a books list")
    report = migrate_books_dry_run(books)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"books={report['book_count']} changed={report['changed_count']} conflicts={report['conflict_count']}")
    print(f"wrote={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
