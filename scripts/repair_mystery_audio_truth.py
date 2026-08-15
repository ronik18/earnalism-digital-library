#!/usr/bin/env python3
"""Restore reader-only truth for A Mystery of Heroism in both mirrors."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SLUG = "a-mystery-of-heroism"
CANONICAL = ROOT / "data" / "controlled_publications" / SLUG
BACKEND = ROOT / "backend" / "data" / "controlled_publications" / SLUG
MIRRORED = ("approval_evidence.json", "public_book.json", "source_evidence.json")
CONTROLLED = (
    "approval_evidence.json",
    "chapters/chapter-001.json",
    "highlight_sync.json",
    "public_book.json",
    "reader_manifest.json",
    "source_evidence.json",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def checksum_bytes(directory: Path, replacements: dict[Path, bytes], repaired_at: str) -> bytes:
    rows = []
    for relative in CONTROLLED:
        path = directory / relative
        payload = replacements.get(path, path.read_bytes())
        rows.append({"file": relative, "sha256": sha256_bytes(payload)})
    return json_bytes({"slug": SLUG, "generated_at": repaired_at, "files": rows})


def build_replacements(repaired_at: str) -> dict[Path, bytes]:
    duplicate = CANONICAL / "approval_evidence 2.json"
    if duplicate.exists():
        raise ValueError("Contradictory duplicate approval evidence still exists")
    replacements: dict[Path, bytes] = {}
    for name in MIRRORED:
        replacements[BACKEND / name] = (CANONICAL / name).read_bytes()

    canonical_public = read_json(CANONICAL / "public_book.json")
    canonical_approval = read_json(CANONICAL / "approval_evidence.json")
    canonical_reader = read_json(CANONICAL / "reader_manifest.json")
    if any(
        (
            canonical_public.get("audio_enabled"),
            canonical_public.get("audiobook_enabled"),
            canonical_public.get("generate_audiobook"),
            canonical_approval.get("audiobook_enabled"),
            canonical_reader.get("audio_enabled"),
            canonical_reader.get("audiobook_enabled"),
        )
    ):
        raise ValueError("Canonical package is not reader-only")
    if canonical_approval.get("audio_public_release") != "PUBLIC_AUDIO_RELEASE_NOT_APPROVED":
        raise ValueError("Canonical approval does not fail closed")

    replacements[CANONICAL / "checksum_manifest.json"] = checksum_bytes(
        CANONICAL, replacements, repaired_at
    )
    replacements[BACKEND / "checksum_manifest.json"] = checksum_bytes(
        BACKEND, replacements, repaired_at
    )
    return replacements


def verify(replacements: dict[Path, bytes]) -> None:
    for path, expected in replacements.items():
        if path.read_bytes() != expected:
            raise ValueError(f"Unexpected written bytes: {path}")
    for directory in (CANONICAL, BACKEND):
        manifest = read_json(directory / "checksum_manifest.json")
        names = [row.get("file") for row in manifest.get("files") or []]
        if names != list(CONTROLLED):
            raise ValueError(f"Unexpected checksum coverage in {directory}: {names}")
        for row in manifest["files"]:
            target = directory / row["file"]
            if sha256_file(target) != row["sha256"]:
                raise ValueError(f"Checksum mismatch: {target}")
    for name in MIRRORED:
        if (CANONICAL / name).read_bytes() != (BACKEND / name).read_bytes():
            raise ValueError(f"Backend mirror drift remains: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--repaired-at")
    args = parser.parse_args()
    if args.repaired_at:
        repaired_at = args.repaired_at
    elif args.write:
        repaired_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    else:
        repaired_at = str(read_json(CANONICAL / "checksum_manifest.json").get("generated_at") or "DRY_RUN")
    replacements = build_replacements(repaired_at)
    changed = [
        str(path.relative_to(ROOT))
        for path, data in replacements.items()
        if path.read_bytes() != data
    ]
    if args.write:
        for path, data in replacements.items():
            path.write_bytes(data)
        verify(replacements)
    print(
        json.dumps(
            {
                "schema": "earnalism.reader_only_truth_repair.v1",
                "slug": SLUG,
                "mode": "write" if args.write else "dry-run",
                "repaired_at": repaired_at,
                "removed_duplicate": "data/controlled_publications/a-mystery-of-heroism/approval_evidence 2.json",
                "changed_files": changed,
                "audio_enabled": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
