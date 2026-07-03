#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mutagen.mp3 import MP3


ROOT = Path(__file__).resolve().parents[1]
ENHANCED_ROOT = ROOT / "internal" / "audiobook_lab" / "enhanced_candidates"
SYNC_ROOT = ROOT / "internal" / "audiobook_lab" / "release_gate" / "sync_manifests"
CONTROLLED_ROOT = ROOT / "data" / "controlled_publications"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mp3_duration_ms(path: Path) -> int:
    return int(MP3(path).info.length * 1000)


def highlight_total_ms(path: Path) -> int:
    payload = read_json(path)
    chapters = payload.get("chapters") or []
    if not isinstance(chapters, list):
        return 0
    return int(sum(int(item.get("duration_ms") or 0) for item in chapters if isinstance(item, dict)))


def build_enhanced_payload(slug: str, fallback_payload: dict[str, Any], total_duration_ms: int) -> dict[str, Any]:
    fallback_chapters = fallback_payload.get("chapters") or []
    chapters: list[dict[str, Any]] = []
    running_total = 0
    for index, item in enumerate(fallback_chapters, start=1):
        if not isinstance(item, dict):
            continue
        intro_ms = int(item.get("introMs") or item.get("intro_ms") or 1500)
        outro_ms = int(item.get("outroMs") or item.get("outro_ms") or 1000)
        total_ms = int(item.get("totalMs") or item.get("estimatedTotalMs") or 0)
        content_ms = int(item.get("contentMs") or item.get("content_ms") or max(0, total_ms - intro_ms - outro_ms))
        chapter_payload = {
            "index": int(item.get("index") or index),
            "chapterId": item.get("chapterId") or item.get("chapter_id") or f"chapter-{index:03d}",
            "title": item.get("title") or f"Chapter {index}",
            "paragraphCount": int(item.get("paragraphCount") or item.get("paragraph_count") or 0),
            "startMs": int(item.get("startMs") or item.get("start_ms") or running_total),
            "contentMs": content_ms,
            "introMs": intro_ms,
            "outroMs": outro_ms,
            "totalMs": total_ms or (content_ms + intro_ms + outro_ms),
        }
        running_total = chapter_payload["startMs"] + chapter_payload["totalMs"]
        chapters.append(chapter_payload)

    if chapters:
        delta = total_duration_ms - sum(chapter["totalMs"] for chapter in chapters)
        if delta:
            chapters[-1]["contentMs"] = max(0, chapters[-1]["contentMs"] + delta)
            chapters[-1]["totalMs"] = chapters[-1]["contentMs"] + chapters[-1]["introMs"] + chapters[-1]["outroMs"]

    return {
        "slug": slug,
        "createdAt": now_iso(),
        "source": "backfill_from_aligned_premium_audio",
        "chapters": chapters,
        "totalDurationMs": total_duration_ms,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill enhanced sync manifests from aligned premium MP3 + fallback timings.")
    parser.add_argument("--max-delta-ms", type=int, default=1000)
    args = parser.parse_args()

    created: list[str] = []
    skipped: list[tuple[str, str]] = []

    for mp3_path in sorted(ENHANCED_ROOT.glob("*/*_enhanced.mp3")):
        slug = mp3_path.parent.name
        enhanced_manifest = SYNC_ROOT / slug / f"{slug}_enhanced.json"
        fallback_manifest = SYNC_ROOT / slug / f"{slug}_fallback.json"
        highlight_path = CONTROLLED_ROOT / slug / "highlight_sync.json"

        if enhanced_manifest.exists():
            skipped.append((slug, "enhanced_manifest_exists"))
            continue
        if not fallback_manifest.exists():
            skipped.append((slug, "missing_fallback_manifest"))
            continue
        if not highlight_path.exists():
            skipped.append((slug, "missing_highlight_sync"))
            continue

        try:
            premium_total = mp3_duration_ms(mp3_path)
            live_total = highlight_total_ms(highlight_path)
        except Exception as exc:  # noqa: BLE001
            skipped.append((slug, f"duration_error:{exc}"))
            continue

        if abs(premium_total - live_total) > args.max_delta_ms:
            skipped.append((slug, f"misaligned:{premium_total-live_total}ms"))
            continue

        payload = build_enhanced_payload(slug, read_json(fallback_manifest), premium_total)
        write_json(enhanced_manifest, payload)
        created.append(slug)

    print(json.dumps(
        {
            "created_count": len(created),
            "created_slugs": created,
            "skipped_count": len(skipped),
            "skipped_sample": [{"slug": slug, "reason": reason} for slug, reason in skipped[:25]],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
