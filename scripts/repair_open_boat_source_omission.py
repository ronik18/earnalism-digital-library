#!/usr/bin/env python3
"""Restore one source-verified omitted phrase in The Open Boat.

This is an intentionally narrow precursor to
``repair_man_open_boat_reader_preflights.py``. It repairs the immutable local
source snapshot and the three matching chapter copies so the normal controlled
package rebuilder can regenerate every derived hash and manifest.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SLUG = "the-open-boat"
RAW_PATH = ROOT / "content" / "books" / SLUG / "raw" / "source.txt"
CHAPTER_PATHS = (
    ROOT / "content" / "books" / SLUG / "chapters" / "001-the-open-boat.json",
    ROOT / "data" / "controlled_publications" / SLUG / "chapters" / "chapter-001.json",
    ROOT / "backend" / "data" / "controlled_publications" / SLUG / "chapters" / "chapter-001.json",
)
CORRUPT = (
    "The cook had tied a life-belt around himself in order to get even the "
    "almost stove-like when a rower, whose teeth invariably chattered wildly "
    "as soon as he ceased his labour, dropped down to sleep."
)
CANONICAL = (
    "The cook had tied a life-belt around himself in order to get even the "
    "warmth which this clumsy cork contrivance could donate, and he seemed "
    "almost stove-like when a rower, whose teeth invariably chattered wildly "
    "as soon as he ceased his labour, dropped down to sleep."
)
CORRUPT_RAW = (
    "The cook had tied a life-belt around himself in order to get even the\n"
    "almost stove-like when a rower, whose teeth invariably chattered wildly\n"
    "as soon as he ceased his labour, dropped down to sleep."
)
CANONICAL_RAW = (
    "The cook had tied a life-belt around himself in order to get even the\n"
    "warmth which this clumsy cork contrivance could donate, and he seemed\n"
    "almost stove-like when a rower, whose teeth invariably chattered wildly\n"
    "as soon as he ceased his labour, dropped down to sleep."
)
OFFICIAL_SOURCE_URL = "https://www.gutenberg.org/cache/epub/45524/pg45524.txt"
OFFICIAL_DOWNLOAD_SHA256 = "0ebacd153c0ed8e37227d5a41e01da7cee5723ed50b29a15da9e824161793840"
EXPECTED_REPAIRED_RAW_SHA256 = "bc2b1ffc7e2a4516accd80674dc6d679229a8682c37960be40bcc1c2ab0379d7"
EXPECTED_REPAIRED_RAW_CONTENT_SHA256 = "29a393e33c66ac380b611737429839d88116598a4b6397d03caa3c432175615f"
EXPECTED_REPAIRED_CHAPTER_SHA256 = "9405254f452956ccd89e6a084114190b5bb5c11b33f917dd2be5501e3119135e"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def replace_once(value: str, path: Path, corrupt: str = CORRUPT, canonical: str = CANONICAL) -> str:
    if value.count(corrupt) == 1 and canonical not in value:
        return value.replace(corrupt, canonical, 1)
    if corrupt not in value and value.count(canonical) == 1:
        return value
    raise ValueError(f"{path}: expected exactly one repairable or repaired omission")


def plan() -> dict[Path, bytes]:
    raw = RAW_PATH.read_text(encoding="utf-8")
    repaired_raw = replace_once(raw, RAW_PATH, CORRUPT_RAW, CANONICAL_RAW)
    if sha256_text(repaired_raw) != EXPECTED_REPAIRED_RAW_SHA256:
        raise ValueError("Repaired raw-source checksum differs from reviewed plan")

    replacements: dict[Path, bytes] = {RAW_PATH: repaired_raw.encode("utf-8")}
    for path in CHAPTER_PATHS:
        payload = json.loads(path.read_text(encoding="utf-8"))
        repaired_content = replace_once(str(payload.get("content") or ""), path)
        if sha256_text(repaired_content) != EXPECTED_REPAIRED_CHAPTER_SHA256:
            raise ValueError(f"{path}: repaired chapter checksum differs from reviewed plan")
        updated = copy.deepcopy(payload)
        updated["content"] = repaired_content
        if path == CHAPTER_PATHS[0]:
            updated["sourceSha256"] = EXPECTED_REPAIRED_RAW_CONTENT_SHA256
        replacements[path] = json_bytes(updated)
    return replacements


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    replacements = plan()
    if args.write:
        for path, payload in replacements.items():
            path.write_bytes(payload)
    print(
        json.dumps(
            {
                "schema": "earnalism.open_boat_source_omission_repair.v1",
                "mode": "write" if args.write else "dry-run",
                "official_source_url": OFFICIAL_SOURCE_URL,
                "official_download_sha256": OFFICIAL_DOWNLOAD_SHA256,
                "repaired_raw_sha256": EXPECTED_REPAIRED_RAW_SHA256,
                "repaired_chapter_sha256": EXPECTED_REPAIRED_CHAPTER_SHA256,
                "restored_words": "warmth which this clumsy cork contrivance could donate, and he seemed",
                "changed_files": [str(path.relative_to(ROOT)) for path in replacements],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
