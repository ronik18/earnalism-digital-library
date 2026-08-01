#!/usr/bin/env python3
"""Reconcile package_v2 migration readiness private flags from containment logs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Mark package_v2 migration readiness entries as private when all "
            "reviewed Wave-1 objects for a slug are successfully retained."
        )
    )
    parser.add_argument(
        "--migration-readiness",
        default=str(
            Path(__file__).resolve().parents[1]
            / "sprint1_publication"
            / "package_v2_migration_readiness.json"
        ),
    )
    parser.add_argument(
        "--inventory",
        default=str(
            Path(__file__).resolve().parent
            / "unapproved_direct_audio_inventory.json"
        ),
    )
    parser.add_argument(
        "--mutation-log",
        default="/tmp/earnalism-storage-containment.jsonl",
    )
    parser.add_argument(
        "--output",
        default="",
        help=(
            "Optional explicit migration output path. If omitted, writes in-place."
        ),
    )
    return parser.parse_args()


def load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    migration_path = Path(args.migration_readiness)
    inventory = load_json(args.inventory)
    migration = load_json(args.migration_readiness)

    reviewed_rows = [
        row
        for row in (inventory.get("objects", []) + inventory.get("supporting_assets", []))
        if row.get("recommended_action") == "MOVE_TO_PRIVATE_QA_BUCKET"
    ]

    reviewed_by_slug = {}
    for row in reviewed_rows:
        reviewed_by_slug.setdefault(row["slug"], set()).add(row["object_id"])

    mutation_path = Path(args.mutation_log)
    latest_status: dict[tuple[str, str], str] = {}
    if mutation_path.exists():
        for raw in mutation_path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                continue
            slug = entry.get("slug")
            object_id = entry.get("object_id")
            if not slug or not object_id:
                continue
            latest_status[(slug, object_id)] = str(entry.get("result", ""))

    rows = migration.get("rows", [])
    changed = False

    successful_results = {"CONTAINED_PRIVATE_COPY_VERIFIED", "ALREADY_CONTAINED_PRIVATE_COPY_VERIFIED"}

    for row in rows:
        slug = row.get("slug")
        if not slug:
            continue
        object_ids = reviewed_by_slug.get(slug)
        if not object_ids:
            continue

        had_all_success = True
        for object_id in object_ids:
            result = latest_status.get((slug, object_id))
            if result not in successful_results:
                had_all_success = False
                break

        previous = bool(row.get("audio_enabled_slug", False))
        current = bool(had_all_success)
        if current != previous:
            row["audio_enabled_slug"] = current
            changed = True

        if row.get("private_b2", previous) != current:
            row["private_b2"] = current
            changed = True

    if changed:
        output_path = Path(args.output) if args.output else migration_path
        output_path.write_text(
            json.dumps(migration, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(
        "reconciled="
        + ("changed" if changed else "no_changes")
        + f" migration={migration_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
