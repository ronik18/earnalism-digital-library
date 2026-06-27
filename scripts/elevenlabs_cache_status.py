#!/usr/bin/env python3
"""Report internal ElevenLabs audio cache status without provider calls."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.elevenlabs_full_chapter_generate import (  # noqa: E402
    CACHE_ROOT,
    PRODUCTION_BLOCKED,
    cache_entry_status,
    cache_manifest_path,
    ensure_internal_path,
    load_cache_manifest,
    relative_path,
    write_cache_manifest,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=Path("internal/audiobook_lab/cache/elevenlabs"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cache_dir = ROOT / args.cache_dir if not args.cache_dir.is_absolute() else args.cache_dir
    cache_dir = ensure_internal_path(cache_dir or CACHE_ROOT, "ElevenLabs cache root")
    manifest = load_cache_manifest(cache_dir)
    if not cache_manifest_path(cache_dir).exists():
        write_cache_manifest(cache_dir, manifest)
    entries = manifest.get("entries", {})
    if not isinstance(entries, dict):
        entries = {}
    counts = {"HIT": 0, "MISS": 0, "STALE": 0}
    for cache_key in sorted(entries):
        status, _entry = cache_entry_status(cache_dir, cache_key)
        counts[status] = counts.get(status, 0) + 1
    payload = {
        "cache_manifest_path": relative_path(cache_manifest_path(cache_dir)),
        "entry_count": len(entries),
        "hit_count": counts.get("HIT", 0),
        "stale_count": counts.get("STALE", 0),
        "miss_count": counts.get("MISS", 0),
        "public_audio_allowed": False,
        "production_status": PRODUCTION_BLOCKED,
    }
    print("ELEVENLABS_CACHE_STATUS " + json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
