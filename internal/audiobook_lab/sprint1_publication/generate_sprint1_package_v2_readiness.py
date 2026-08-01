#!/usr/bin/env python3
"""Generate a deterministic versioned package-v2 readiness artifact."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def normalize_bool(value: Any) -> bool:
    return bool(value is True)


def slug_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["slug"]: row for row in rows}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate package-v2 readiness for sprint1 private-B2 migration."
    )
    parser.add_argument(
        "--migration-readiness",
        default=str(
            Path(__file__).resolve().parent / "package_v2_migration_readiness.json"
        ),
    )
    parser.add_argument(
        "--title-metadata",
        default=str(
            Path(__file__).resolve().parent / "sprint1_final_yes_yes_matrix.json"
        ),
        help="Source of slug->title metadata for all sprint1 active slugs.",
    )
    parser.add_argument(
        "--output",
        default=str(
            Path(__file__).resolve().parent / "sprint1_package_v2_readiness.json"
        ),
    )
    args = parser.parse_args()

    migration = json.loads(Path(args.migration_readiness).read_text(encoding="utf-8"))
    title_metadata = json.loads(Path(args.title_metadata).read_text(encoding="utf-8"))

    migration_rows = slug_index(migration.get("rows", []))
    title_rows = title_metadata.get("titles", [])
    if not title_rows:
        raise RuntimeError("title metadata is missing the expected titles array")

    readiness_rows: list[dict[str, Any]] = []
    for title_row in title_rows:
        slug = title_row["slug"]
        source = migration_rows.get(slug)
        if source is None:
            source = {
                "live_status": "BLOCKED",
                "reason": "missing_from_migration_readiness",
                "release_gate": None,
                "audio_qa_status": None,
                "audiobook_enabled": False,
                "audio_enabled_slug": False,
                "has_assets": False,
                "mp3_url": None,
            }

        live_approved = source.get("live_status") == "LIVE"
        can_expose = live_approved
        private_b2 = normalize_bool(source.get("audio_enabled_slug"))
        audio_enabled = normalize_bool(source.get("audiobook_enabled"))
        release = source.get("release_gate")
        qa = source.get("audio_qa_status")
        mp3 = source.get("mp3_url")

        row = {
            "slug": slug,
            "title": title_row.get("title"),
            "audio_enabled": audio_enabled,
            "can_expose": can_expose,
            "release": release,
            "qa": qa,
            "audiobook_enabled": normalize_bool(source.get("audiobook_enabled")),
            "private_b2": private_b2,
            "mp3": mp3,
            "live_approved": live_approved,
        }
        if can_expose and not private_b2:
            row["warn"] = "non_private_but_exposed"
        readiness_rows.append(row)

    live_rows = [row for row in readiness_rows if row["live_approved"]]
    not_live_rows = [row for row in readiness_rows if not row["live_approved"]]
    not_live_reasons = {"not_live_approved": 0, "release_not_approved": 0}
    for row in not_live_rows:
        if row["audio_enabled"] and row["release"] != "APPROVED":
            not_live_reasons["release_not_approved"] += 1
        else:
            not_live_reasons["not_live_approved"] += 1

    document = {
        "schema_version": "2.0.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "package_v2_source": str(Path(args.migration_readiness).name),
        "source_slug_count": len(readiness_rows),
        "live_count": len(live_rows),
        "live_slugs": [row["slug"] for row in live_rows],
        "live_private_b2_count": sum(1 for row in live_rows if row["private_b2"]),
        "live_private_b2_slugs": [
            row["slug"] for row in live_rows if row["private_b2"]
        ],
        "not_live_count": len(not_live_rows),
        "not_live_reasons": not_live_reasons,
        "live_target": 10,
        "private_target": 10,
        "rows": readiness_rows,
    }

    output_path = Path(args.output)
    output_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
