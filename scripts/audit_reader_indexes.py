#!/usr/bin/env python3
"""Audit every controlled reader index against the deterministic v1 contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.domain.chapter_index import (
    CHAPTER_INDEX_CONTRACT_VERSION,
    build_chapter_index_entries,
)


DEFAULT_CONTROLLED_ROOT = ROOT / "backend" / "data" / "controlled_publications"


def audit(controlled_root: Path) -> dict:
    books = []
    blockers = []
    chapter_total = 0
    for manifest_path in sorted(controlled_root.glob("*/reader_manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        slug = str(manifest.get("slug") or manifest_path.parent.name)
        chapters = manifest.get("chapters") or []
        entries = build_chapter_index_entries(chapters)
        issues = []
        if len(entries) != int(manifest.get("chapter_count") or 0):
            issues.append("CHAPTER_COUNT_MISMATCH")
        if len({entry.get("id") for entry in entries}) != len(entries):
            issues.append("DUPLICATE_CHAPTER_ID")
        if not all(entry.get("index_title", "").strip() for entry in entries):
            issues.append("BLANK_INDEX_TITLE")
        if [entry["index_sequence"] for entry in entries] != list(range(1, len(entries) + 1)):
            issues.append("NON_DETERMINISTIC_SEQUENCE")
        if not all(entry.get("index_contract") == CHAPTER_INDEX_CONTRACT_VERSION for entry in entries):
            issues.append("CONTRACT_VERSION_MISMATCH")
        if issues:
            blockers.append({"slug": slug, "issues": issues})
        books.append({
            "slug": slug,
            "chapter_count": len(entries),
            "status": "PASS" if not issues else "FAIL",
            "issues": issues,
        })
        chapter_total += len(entries)
    return {
        "schema_version": "earnalism.reader-index-audit.v1",
        "contract_version": CHAPTER_INDEX_CONTRACT_VERSION,
        "status": "PASS" if not blockers else "FAIL",
        "book_count": len(books),
        "chapter_count": chapter_total,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "books": books,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controlled-root", type=Path, default=DEFAULT_CONTROLLED_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.controlled_root.resolve())
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
