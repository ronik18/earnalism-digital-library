#!/usr/bin/env python3
"""Repair the Usher and Love of Life reader preflights without changing words."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repair_lady_stolen_reader_preflights import (
    BACKEND_ROOT,
    CONTROLLED_ROOT,
    ROOT,
    RepairSpec,
    build_title,
    json_bytes,
    normalized,
    read_json,
    sha256_file,
    sha256_text,
)


SPECS = (
    RepairSpec(
        slug="the-fall-of-the-house-of-usher",
        chapter_name="001-the-fall-of-the-house-of-usher.json",
        old_sha256="1b243266e2b4ce1ef11d4b0b43b66a0e30fbe93afdd9a2a2b3bd24f1a174eabb",
        new_sha256="51f5aeca3e88367050046042ca32b6b95522c7ae93150cd95fe06988ef92a353",
        semantic_blocks=58,
        endpoint="* Watson, Dr Percival, Spallanzani, and especially the Bishop of Landaff.",
    ),
    RepairSpec(
        slug="love-of-life",
        chapter_name="001-love-of-life.json",
        old_sha256="7ce5b5add01929c47826b8bdedb9230875acc6f41b035451357ffa41aac0ce9f",
        new_sha256="2267c4f04f8663cce8e90a2c0569eb63abc9d0eb820f811b7b5a37df3b952123",
        semantic_blocks=94,
        endpoint="San Francisco Bay.",
        legacy_sha256s=("f4943599581e59370ec58f6b0fef2ffc5088e98e327b957c9a1870c8e7a257c7",),
        source_old_sha256="44069e2bfaffc40f5d83a63069c8d136c1081b896a81edc31ce3d95e0f97bae5",
        source_new_sha256="edab396a4cde4053abc9e0380d1eb5479493dc5362b8c49c4faa526619fa16a5",
        source_old_fragment="and thrust it into\n\nThe scientific men were discreet.",
        source_new_fragment=(
            "and thrust it into\nhis shirt bosom. Similar were the donations from other grinning\n"
            "sailors.\n\nThe scientific men were discreet."
        ),
    ),
)


CONTROLLED_FILES = (
    "approval_evidence.json",
    "chapters/chapter-001.json",
    "highlight_sync.json",
    "public_book.json",
    "reader_manifest.json",
    "source_evidence.json",
    "checksum_manifest.json",
)


def verify_written(replacements: dict[Path, bytes]) -> None:
    for path, expected in replacements.items():
        if path.read_bytes() != expected:
            raise ValueError(f"Written artifact differs from plan: {path}")
    for spec in SPECS:
        controlled_dir = CONTROLLED_ROOT / spec.slug
        backend_dir = BACKEND_ROOT / spec.slug
        if any(controlled_dir.glob("approval_evidence 2.json")):
            raise ValueError(f"{spec.slug}: duplicate approval evidence remains")
        for publication_dir in (controlled_dir, backend_dir):
            manifest = read_json(publication_dir / "checksum_manifest.json")
            for row in manifest.get("files") or []:
                target = publication_dir / str(row["file"])
                if not target.is_file() or sha256_file(target) != row.get("sha256"):
                    raise ValueError(f"Controlled checksum mismatch: {target}")
        for relative in CONTROLLED_FILES:
            if (controlled_dir / relative).read_bytes() != (backend_dir / relative).read_bytes():
                raise ValueError(f"{spec.slug}: root/backend mirror mismatch: {relative}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--repaired-at")
    parser.add_argument("--evidence-out", type=Path)
    args = parser.parse_args()
    requested_at = args.repaired_at or (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        if args.write
        else "DRY_RUN"
    )
    replacements: dict[Path, bytes] = {}
    evidence_rows: list[dict[str, Any]] = []
    for spec in SPECS:
        title_replacements, evidence = build_title(spec, requested_at)
        replacements.update(title_replacements)
        evidence_rows.append(evidence)
    report = {
        "schema": "earnalism.shortest_reader_preflight_repair.v1",
        "mode": "write" if args.write else "dry-run",
        "titles": evidence_rows,
        "changed_files": [
            str(path.relative_to(ROOT))
            for path, payload in replacements.items()
            if not path.exists() or path.read_bytes() != payload
        ],
    }
    if args.write:
        for path, payload in replacements.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        verify_written(replacements)
    if args.evidence_out:
        args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_out.write_bytes(json_bytes(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
