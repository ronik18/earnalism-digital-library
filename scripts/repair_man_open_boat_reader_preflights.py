#!/usr/bin/env python3
"""Repair Man Who Would Be King and Open Boat narrative boundaries."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repair_most_dangerous_scandal_reader_preflights import (
    BACKEND_ROOT,
    CONTROLLED_FILES,
    CONTROLLED_ROOT,
    ROOT,
    RepairSpec,
    build_title,
    json_bytes,
    narrative_slice,
    normalized,
    read_json,
    sha256_file,
    sha256_text,
)


SPECS = (
    RepairSpec(
        slug="the-man-who-would-be-king",
        chapter_name="001-the-man-who-would-be-king.json",
        old_sha256="9e3575b8a51e0a06410c441a37fd8a277cd81705004e99339e614a8db1dfc58b",
        new_sha256="6bb07930606cf29425f255fe36c7aca80ab53654da30c4c01831b01a11be6ccb",
        semantic_blocks=201,
        start="“Brother to a Prince and fellow to a beggar if he be found worthy.”",
        endpoint="And there the matter rests.",
        expected_words=14303,
    ),
    RepairSpec(
        slug="the-open-boat",
        chapter_name="001-the-open-boat.json",
        old_sha256="69426e1ecf9a3d1c173bfa2e0b4a53933c8e23bb705138c61ea4828b14b95c25",
        new_sha256="af681590fc598cd9b03e41bd4c73b4761d3e516c86649d320a446f3aa0913799",
        semantic_blocks=248,
        start="A Tale intended to be after the Fact.",
        endpoint="and they felt that they could then be interpreters.",
        expected_words=9329,
    ),
)


def verify_written(replacements: dict[Path, bytes]) -> None:
    for path, expected in replacements.items():
        if path.read_bytes() != expected:
            raise ValueError(f"Written artifact differs from plan: {path}")
    for spec in SPECS:
        controlled_dir = CONTROLLED_ROOT / spec.slug
        backend_dir = BACKEND_ROOT / spec.slug
        if any(controlled_dir.glob("approval_evidence 2.json")):
            raise ValueError(f"{spec.slug}: contradictory approval duplicate remains")
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
        "schema": "earnalism.shortest_reader_boundary_preflight_repair.v1",
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
