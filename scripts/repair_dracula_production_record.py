#!/usr/bin/env python3
"""Dry-run-by-default repair helper for the controlled Dracula production record."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.catalog_truth import (  # noqa: E402
    dracula_artifact_status,
    load_dracula_artifact_book,
)


DEFAULT_OUTPUT_DIR = ROOT / "output" / "production" / "dracula_repair"
UNSAFE_AUDIO_FIELDS = {
    "audio_assets",
    "audio_files",
    "audiobook_url",
    "audiobook",
    "audiobook_assets",
    "audiobook_assets_updated_at",
    "audiobook_provider",
    "audiobook_voice",
    "audio_asset_slug",
    "b2_url",
    "cloudinary_audio",
    "generate_audiobook",
    "has_audio",
    "listen_url",
    "narration_url",
    "voice_url",
    "waveform_url",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def database_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    db_name = parsed.path.lstrip("/").split("/", 1)[0]
    return os.environ.get("DB_NAME") or db_name or "earnalism"


def safe_dracula_document() -> dict[str, Any] | None:
    artifact = load_dracula_artifact_book(include_content=True)
    if not artifact:
        return None
    if artifact.get("slug") != "dracula":
        return None
    if len(artifact.get("chapters") or []) != 27:
        return None
    return {
        **artifact,
        "slug": "dracula",
        "is_published": True,
        "approved_to_publish": True,
        "publication_status": "LIVE_APPROVED",
        "rights_tier": "A",
        "verification_status": "approved",
        "qa_status": "QA_PASSED",
        "audio_enabled": False,
        "audiobook_enabled": False,
        "generate_audiobook": False,
        "audiobook_assets": {},
        "audiobook": {},
        "updated_at": now_iso(),
    }


def comparable_changes(current: dict[str, Any] | None, desired: dict[str, Any]) -> list[str]:
    current = current or {}
    keys = [
        "slug",
        "title",
        "author",
        "category_slug",
        "is_published",
        "approved_to_publish",
        "publication_status",
        "rights_tier",
        "verification_status",
        "qa_status",
        "source_url",
        "source_name",
        "source_license",
        "source_hash",
        "content_hash",
        "provenance_hash",
        "audio_enabled",
        "audiobook_enabled",
        "generate_audiobook",
    ]
    changed = [key for key in keys if current.get(key) != desired.get(key)]
    if len(current.get("chapters") or []) != 27:
        changed.append("chapters")
    for key in UNSAFE_AUDIO_FIELDS:
        if key in current and current.get(key):
            changed.append(f"unset:{key}")
    return sorted(set(changed))


def connect_books_collection():
    mongo_url = os.environ.get("MONGODB_URL") or os.environ.get("MONGO_URL")
    if not mongo_url:
        return None, "MONGODB_URL/MONGO_URL not set"
    try:
        from pymongo import MongoClient  # type: ignore
    except Exception as exc:  # pragma: no cover - environment-specific dependency issue.
        return None, f"pymongo unavailable: {exc}"
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
    db = client[database_name_from_url(mongo_url)]
    client.admin.command("ping")
    return db.books, ""


def write_reports(report: dict[str, Any], output_dir: Path, *, applied: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = "dracula_repair_apply" if applied else "dracula_repair_dry_run"
    (output_dir / f"{prefix}.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / f"{prefix}.md").write_text(markdown_report(report), encoding="utf-8")


def markdown_report(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Dracula Production Record Repair",
            "",
            f"- Generated At: `{report['generated_at']}`",
            f"- Mode: `{report['mode']}`",
            f"- Mutation Performed: `{report['mutation_performed']}`",
            f"- Operator Approval Required: `{report['operator_approval_required']}`",
            f"- Artifact Valid: `{report['artifact_valid']}`",
            f"- Would Insert Dracula: `{report['would_insert']}`",
            f"- Would Update Dracula: `{report['would_update']}`",
            f"- Audio Remains Disabled: `{report['audio_remains_disabled']}`",
            f"- Reader Manifest Would Become Available: `{report['reader_manifest_would_be_available']}`",
            f"- Changed Fields: `{report['changed_fields']}`",
            f"- Blockers: `{report['blockers']}`",
            "",
            "This script never deletes records, never mutates non-Dracula books, and never enables audiobook fields.",
            "",
        ]
    )


def run_repair(*, apply: bool, output_dir: Path) -> dict[str, Any]:
    status = dracula_artifact_status()
    desired = safe_dracula_document()
    blockers: list[str] = []
    if not status.get("available") or not desired:
        blockers.append("Approved Dracula artifact pack is invalid or missing.")
    if desired and len(desired.get("chapters") or []) != 27:
        blockers.append("Approved Dracula artifact pack does not contain 27 chapters.")
    if desired and (desired.get("audio_enabled") or desired.get("audiobook_enabled")):
        blockers.append("Approved Dracula artifact pack has audio enabled.")

    current: dict[str, Any] | None = None
    collection = None
    db_error = ""
    if not blockers:
        try:
            collection, db_error = connect_books_collection()
            if collection is not None:
                current = collection.find_one({"slug": "dracula"}, {"_id": 0})
        except Exception as exc:
            db_error = str(exc)
    if db_error:
        blockers.append(db_error)

    changed_fields = comparable_changes(current, desired) if desired else []
    would_insert = current is None and bool(desired) and not blockers
    would_update = current is not None and bool(changed_fields) and bool(desired) and not blockers
    mutation_performed = False
    if apply:
        if blockers:
            blockers.append("--apply refused because blockers are present.")
        elif collection is None or desired is None:
            blockers.append("--apply refused because the database or desired document is unavailable.")
        else:
            collection.update_one(
                {"slug": "dracula"},
                {
                    "$set": desired,
                    "$unset": {field: "" for field in UNSAFE_AUDIO_FIELDS if field not in {"audiobook", "audiobook_assets", "generate_audiobook"}},
                },
                upsert=True,
            )
            mutation_performed = True

    report = {
        "generated_at": now_iso(),
        "mode": "apply" if apply else "dry-run",
        "mutation_performed": mutation_performed,
        "operator_approval_required": not apply,
        "artifact_valid": bool(status.get("available")),
        "artifact_issues": status.get("issues", []),
        "db_error": db_error,
        "current_dracula_present": current is not None,
        "would_insert": would_insert,
        "would_update": would_update,
        "changed_fields": changed_fields,
        "audio_remains_disabled": bool(desired and desired.get("audio_enabled") is False and desired.get("audiobook_enabled") is False),
        "reader_manifest_would_be_available": bool(desired and len(desired.get("chapters") or []) == 27),
        "blockers": blockers,
    }
    write_reports(report, output_dir, applied=apply)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Plan only. This is the default.")
    mode.add_argument("--apply", action="store_true", help="Apply the Dracula-only repair after operator review.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    report = run_repair(apply=bool(args.apply), output_dir=Path(args.output_dir))
    print(
        "Dracula repair "
        f"{report['mode']} complete: mutation_performed={report['mutation_performed']} "
        f"would_insert={report['would_insert']} would_update={report['would_update']} "
        f"output_dir={args.output_dir}"
    )
    return 1 if args.apply and report["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
