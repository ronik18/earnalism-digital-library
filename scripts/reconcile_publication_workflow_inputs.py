#!/usr/bin/env python3
"""Read-only inventory of inputs required for publication-workflow migration."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


REQUIRED = ("public_book.json", "reader_manifest.json", "source_evidence.json", "approval_evidence.json", "checksum_manifest.json")


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def inspect_slug(roots: list[Path], slug: str, mongo_book: dict[str, Any]) -> dict[str, Any]:
    dirs = [root / slug for root in roots if (root / slug).is_dir()]
    directory = max(dirs, key=lambda path: sum((path / name).is_file() for name in REQUIRED), default=None)
    files = {name: bool(directory and (directory / name).is_file()) for name in REQUIRED}
    public = load(directory / "public_book.json") if directory else {}
    approval = load(directory / "approval_evidence.json") if directory else {}
    reader_proof = bool(
        public.get("isPublic") is True
        and public.get("isLive") is True
        and public.get("allowPublicReading") is True
        and public.get("approved_to_publish") is True
        and approval.get("approved_to_publish") is True
    )
    audio_proof = bool(
        approval.get("audiobook_enabled") is True
        and approval.get("audio_public_release") in {"PUBLIC_AUDIO_RELEASE_APPROVED", "APPROVED"}
        and approval.get("audio_qa_status", approval.get("qa_status")) in {"QA_PASSED", "PASS", "PASSED"}
    )
    missing = [name for name, present in files.items() if not present]
    blockers: list[str] = []
    if missing:
        blockers.append("missing_controlled_artifact")
    if not reader_proof:
        blockers.append("reader_exposure_unproven")
    if audio_proof and not all(files.values()):
        blockers.append("audio_evidence_incomplete")
    return {
        "slug": slug,
        "mongo_is_published": mongo_book.get("is_published") is True,
        "artifact_directory": str(directory) if directory else "",
        "files": files,
        "missing_files": missing,
        "reader_exposure_proven": reader_proof,
        "audio_exposure_proven": audio_proof,
        "blockers": blockers,
        "action": "RECONCILE_ARTIFACTS" if "missing_controlled_artifact" in blockers else ("REVIEW_READER_EVIDENCE" if "reader_exposure_unproven" in blockers else "READY_FOR_MIGRATION"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, default=Path("backend/data/controlled_publications"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    mongo_url = os.environ.get("MONGODB_URL") or os.environ.get("MONGO_URL")
    if not mongo_url:
        raise SystemExit("BLOCKED: MONGODB_URL or MONGO_URL is required")
    try:
        from pymongo import MongoClient
    except ImportError as exc:
        raise SystemExit(f"BLOCKED: pymongo is required: {exc}") from exc
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=15000, uuidRepresentation="standard")
    client.admin.command("ping")
    db_name = os.environ.get("MONGODB_DB_NAME") or os.environ.get("DB_NAME") or mongo_url.rsplit("/", 1)[-1].split("?", 1)[0] or "earnalism"
    collection = client[db_name][os.environ.get("MONGODB_BOOKS_COLLECTION", "books")]
    books = list(collection.find({}, {"_id": 0}))
    roots = [args.artifact_root, args.artifact_root.parent.parent.parent / "data" / "controlled_publications"]
    rows = [inspect_slug(roots, str(book.get("slug") or ""), book) for book in books]
    report = {
        "mode": "read_only_reconciliation",
        "book_count": len(rows),
        "artifact_missing_count": sum("missing_controlled_artifact" in row["blockers"] for row in rows),
        "reader_unproven_count": sum("reader_exposure_unproven" in row["blockers"] for row in rows),
        "audio_unproven_count": sum(not row["audio_exposure_proven"] for row in rows),
        "ready_count": sum(not row["blockers"] for row in rows),
        "roots": [str(root) for root in roots],
        "rows": rows,
    }
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("books={book_count} missing_artifacts={artifact_missing_count} reader_unproven={reader_unproven_count} ready={ready_count}".format(**report))
    print(f"wrote={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
