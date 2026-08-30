#!/usr/bin/env python3
"""Validate the immutable visual references used by the lean redesign program."""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/design-references/primary-experience-reference-manifest.json"
REQUIRED = {
    "home-library-commerce-desktop.png",
    "reading-pass-commerce.png",
    "reader-listener-bookdetail-desktop.png",
    "reader-listener-ecosystem.png",
    "responsive-reference-board.png",
    "brand/earnalism-logo-lockup.png",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"not a PNG: {path}")
    return struct.unpack(">II", header[16:24])


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    references = manifest.get("references", {})
    canonical = {
        name: record
        for name, record in references.items()
        if record.get("status") == "OWNER_APPROVED_CANONICAL"
    }
    if set(canonical) != REQUIRED:
        raise ValueError("primary manifest must contain exactly the required owner-approved canonical references")
    for name in sorted(REQUIRED):
        record = canonical[name]
        if record.get("implementation_authority") is not True or record.get("visual_gate_authority") is not True:
            raise ValueError(f"canonical reference lacks implementation and visual-gate authority: {name}")
        path = ROOT / "docs/design-references" / name
        if not path.is_file():
            raise FileNotFoundError(path)
        width, height = png_size(path)
        actual = {
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
            "width": width,
            "height": height,
        }
        expected = {key: record[key] for key in actual}
        if actual != expected:
            raise ValueError(f"reference changed: {name}")
        print(f"PASS {name}: {width}x{height} {actual['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
