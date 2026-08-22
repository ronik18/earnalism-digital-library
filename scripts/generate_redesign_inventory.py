#!/usr/bin/env python3
"""Write conservative, read-only cleanup inventories for the lean redesign."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRANSIENT_PREFIXES = (".npm-cache/", ".playwright-browsers/", ".venv-uat/", "frontend/build/", "node_modules/", "frontend/node_modules/")
PROTECTED_TOKENS = ("payment", "wallet", "ledger", "rights", "publication", "entitlement", "audiobook")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def tracked_files() -> list[str]:
    output = subprocess.check_output(
        ["git", "-c", "core.quotepath=false", "ls-files", "-z"],
        cwd=ROOT,
    )
    return [path.decode("utf-8") for path in output.split(b"\0") if path]


def classify(path: str) -> str:
    lowered = path.lower()
    if path.startswith(TRANSIENT_PREFIXES):
        return "reproducible transient artifact"
    if any(token in lowered for token in PROTECTED_TOKENS) or path.startswith("internal/"):
        return "required audit evidence"
    if path.startswith(("frontend/src/", "backend/", "scripts/", "tests/", "regression/", ".github/")):
        return "active"
    if path.startswith("output/"):
        return "unknown owner"
    return "active"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="cleanup")
    args = parser.parse_args()
    output_dir = (ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    files = tracked_files()
    rows = []
    for relative in files:
        path = ROOT / relative
        rows.append({
            "path": relative,
            "classification": classify(relative),
            "size_bytes": path.stat().st_size,
            "sha256": digest(path),
        })
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    counts = Counter(row["classification"] for row in rows)
    write_json(output_dir / "repository-inventory.json", {
        "schema_version": "lean-redesign-cleanup-v1",
        "mode": "dry-run",
        "generated_at": generated,
        "candidate_count": len(rows),
        "classification_counts": dict(sorted(counts.items())),
        "candidates": rows,
    })
    write_json(output_dir / "database-inventory.json", {
        "schema_version": "lean-redesign-cleanup-v1",
        "mode": "dry-run",
        "provider_query": "not executed",
        "reason": "Inventory PR never connects to a production database.",
        "candidates": [],
    })
    media = [row for row in rows if row["path"].startswith("frontend/public/") and row["path"].lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".svg", ".mp3", ".wav"))]
    write_json(output_dir / "media-reference-inventory.json", {
        "schema_version": "lean-redesign-cleanup-v1",
        "mode": "dry-run",
        "provider_query": "not executed",
        "repository_media": media,
        "provider_orphan_detection": "requires a separately approved read-only provider inventory",
    })
    write_json(output_dir / "orphan-candidates.json", {
        "schema_version": "lean-redesign-cleanup-v1",
        "mode": "dry-run",
        "candidates": [],
        "note": "No object is an orphan without authoritative database and provider-reference parity.",
    })
    write_json(output_dir / "quarantine-manifest.json", {
        "schema_version": "lean-redesign-cleanup-v1",
        "mode": "dry-run",
        "deletion_allowed": False,
        "minimum_quarantine_days": 30,
        "entries": [],
    })
    write_json(output_dir / "cost-baseline.json", {
        "schema_version": "lean-redesign-cleanup-v1",
        "mode": "dry-run",
        "provider_metrics": "not queried",
        "reason": "Requires an approved read-only provider metrics export; no provider mutation occurred.",
    })
    print(f"dry-run inventory written: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
