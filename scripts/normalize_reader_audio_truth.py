#!/usr/bin/env python3
"""Normalize stale historical audio fields without changing Reader content.

The tool is intentionally explicit: it has no implicit all-title mode and only
updates a caller-supplied controlled-publication root.  It never enables audio
or changes chapters, rights, or publication state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "data" / "controlled_publications"
PUBLIC_AUDIO_FIELDS = {
    "audio_enabled": False,
    "audiobook_enabled": False,
    "generate_audiobook": False,
    "audiobook_provider": "",
    "audiobook_voice": "",
    "audio_asset_slug": "",
    "audiobook_assets": {},
    "audiobook": {},
    "audiobook_package": {},
    "audio_url": "",
    "audiobook_release_gate": "",
    "audio_qa_status": "",
    "audiobook_release_mode": "",
    "audiobook_assets_updated_at": "",
    "audiobook_manuscript_sha256": "",
    "audiobook_release_conveyor": {},
}
APPROVAL_AUDIO_FIELDS = {
    "audiobook_enabled": False,
    "audio_public_release": "PUBLIC_AUDIO_RELEASE_BLOCKED_QA_REQUIRED",
    "audio_qa_status": "",
    "endpoint_url": "",
    "provider": "",
    "version": "",
}


def read_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def json_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalized_payloads(package: Path) -> dict[Path, bytes]:
    public_book = read_json(package / "public_book.json")
    approval = read_json(package / "approval_evidence.json")
    reader_manifest = read_json(package / "reader_manifest.json")
    public_book.update(PUBLIC_AUDIO_FIELDS)
    approval.update(APPROVAL_AUDIO_FIELDS)
    reader_manifest.update({"audio_enabled": False, "audiobook_enabled": False})
    return {
        package / "public_book.json": json_bytes(public_book),
        package / "approval_evidence.json": json_bytes(approval),
        package / "reader_manifest.json": json_bytes(reader_manifest),
    }


def checksum_payload(package: Path, replacements: dict[Path, bytes]) -> bytes:
    checksum_path = package / "checksum_manifest.json"
    checksum = read_json(checksum_path)
    rows = []
    for row in checksum.get("files", []):
        relative = str(row.get("file") or "")
        if not relative or relative == "checksum_manifest.json":
            continue
        target = package / relative
        if not target.is_file():
            raise ValueError(f"Checksum target is missing: {target}")
        content = replacements.get(target, target.read_bytes())
        rows.append({"file": relative, "sha256": sha256_bytes(content)})
    checksum["files"] = rows
    return json_bytes(checksum)


def normalize_slug(package_root: Path, slug: str, *, apply: bool) -> dict:
    package = package_root / slug.strip().lower()
    if not package.is_dir():
        raise ValueError(f"Controlled package is missing: {package}")
    replacements = normalized_payloads(package)
    replacements[package / "checksum_manifest.json"] = checksum_payload(package, replacements)
    changed = [str(path.relative_to(package)) for path, body in replacements.items() if path.read_bytes() != body]
    if apply:
        for path, body in replacements.items():
            if path.read_bytes() != body:
                path.write_bytes(body)
    return {"slug": slug, "changed": changed, "applied": apply}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", action="append", default=[])
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    slugs = list(dict.fromkeys(slug.strip().lower() for slug in args.slug if slug.strip()))
    if not slugs:
        parser.error("provide one or more explicit --slug values")
    results = [normalize_slug(args.root, slug, apply=args.apply) for slug in slugs]
    print(json.dumps({"root": str(args.root), "results": results}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
