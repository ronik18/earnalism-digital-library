#!/usr/bin/env python3
"""Remove discoverable audio URLs from fail-closed controlled publications."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
CONTROLLED_ROOTS = (
    Path("data/controlled_publications"),
    Path("backend/data/controlled_publications"),
)
PUBLIC_AUDIO_APPROVED = "PUBLIC_AUDIO_RELEASE_APPROVED"
AUDIO_KEYS = (
    "audiobook",
    "audiobook_assets",
    "audio_assets",
    "audio_url",
    "audiobook_url",
)


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def count_urls(value: Any) -> int:
    if isinstance(value, str):
        return 1 if value.startswith(("https://", "http://")) else 0
    if isinstance(value, dict):
        return sum(count_urls(item) for item in value.values())
    if isinstance(value, list):
        return sum(count_urls(item) for item in value)
    return 0


def audio_release_approved(approval: dict[str, Any], public_book: dict[str, Any]) -> bool:
    return (
        approval.get("audio_public_release") == PUBLIC_AUDIO_APPROVED
        and approval.get("audiobook_enabled") is True
        and public_book.get("audio_enabled") is True
        and public_book.get("audiobook_enabled") is True
    )


def scrub_public_book(public_book: dict[str, Any]) -> tuple[dict[str, Any], list[str], int]:
    scrubbed = dict(public_book)
    removed_keys: list[str] = []
    removed_urls = 0
    for key in AUDIO_KEYS:
        if key not in scrubbed:
            continue
        removed_keys.append(key)
        removed_urls += count_urls(scrubbed.pop(key))
    scrubbed["audio_enabled"] = False
    scrubbed["audiobook_enabled"] = False
    return scrubbed, removed_keys, removed_urls


def scrub_reader_manifest(reader_manifest: dict[str, Any]) -> tuple[dict[str, Any], int]:
    scrubbed = dict(reader_manifest)
    removed_urls = count_urls(scrubbed.get("audio"))
    if "audio" in scrubbed:
        scrubbed["audio"] = {
            "enabled": False,
            "provider": "",
            "voice": "",
            "url": "",
            "assets": {},
        }
    return scrubbed, removed_urls


def scrub_slug(root: Path, slug: str, execute: bool) -> list[dict[str, Any]]:
    results = []
    for relative_root in CONTROLLED_ROOTS:
        title_dir = root / relative_root / slug
        public_path = title_dir / "public_book.json"
        if not public_path.exists():
            continue
        approval_path = title_dir / "approval_evidence.json"
        reader_path = title_dir / "reader_manifest.json"
        public_book = read_json(public_path)
        approval = read_json(approval_path) if approval_path.exists() else {}
        if audio_release_approved(approval, public_book):
            results.append(
                {
                    "slug": slug,
                    "root": str(relative_root),
                    "status": "SKIPPED_APPROVED_PUBLIC_AUDIO",
                    "removed_url_count": 0,
                }
            )
            continue
        scrubbed, removed_keys, removed_urls = scrub_public_book(public_book)
        reader_urls = 0
        if reader_path.exists():
            reader, reader_urls = scrub_reader_manifest(read_json(reader_path))
            if execute:
                write_json(reader_path, reader)
        if execute:
            write_json(public_path, scrubbed)
        results.append(
            {
                "slug": slug,
                "root": str(relative_root),
                "status": "SCRUBBED" if execute else "DRY_RUN_SCRUB_REQUIRED",
                "removed_keys": removed_keys,
                "removed_url_count": removed_urls + reader_urls,
                "remote_object_revocation_required": removed_urls + reader_urls > 0,
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--slugs", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(
            "internal/audiobook_lab/sprint1_publication/title_runs/"
            "unapproved_storage_asset_scrub_report.json"
        ),
    )
    args = parser.parse_args()
    root = args.root.resolve()
    slugs = [item.strip() for item in args.slugs.split(",") if item.strip()]
    results = [item for slug in slugs for item in scrub_slug(root, slug, args.execute)]
    report = {
        "schema_version": 1,
        "generated_at": iso_now(),
        "mode": "EXECUTE" if args.execute else "DRY_RUN",
        "slugs": slugs,
        "results": results,
        "scrubbed_file_count": sum(item["status"] == "SCRUBBED" for item in results),
        "removed_url_count": sum(int(item.get("removed_url_count") or 0) for item in results),
        "remote_object_revocation_required": any(
            item.get("remote_object_revocation_required") for item in results
        ),
        "provider_calls_ran": False,
        "release_gate_approvals_added": 0,
    }
    report_path = args.report if args.report.is_absolute() else root / args.report
    write_json(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
