#!/usr/bin/env python3
"""Build a fail-closed Gitanjali release-review packet from staged evidence.

This command only writes a local review packet. It never writes MongoDB,
uploads media, changes public routes, or marks a title live.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


EXPECTED_LABELS = ["Introduction", *[str(i) for i in range(1, 104)]]
EXPECTED_TRACKS = [f"gitanjali_{i:02d}_tagore.mp3" for i in range(1, 12)]


class ReaderTextParser(HTMLParser):
    """Extract readable text while ignoring page furniture and media markup."""

    SKIP = {"script", "style", "noscript", "table", "nav", "sup"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIP:
            self.skip_depth += 1
        if self.skip_depth == 0 and tag in {"p", "div", "br", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self.skip_depth == 0 and tag in {"p", "div", "br", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")
        if tag in self.SKIP and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.skip_depth == 0:
            self.parts.append(data)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def clean_text(raw_html: str) -> str:
    parser = ReaderTextParser()
    parser.feed(raw_html)
    text = html.unescape("".join(parser.parts)).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n\n".join(lines).strip()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def probe(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,format_name,start_time:stream=index,codec_name,codec_type,sample_rate,channels,bit_rate",
            "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    payload["file"] = path.name
    return payload


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    staging = args.staging
    output = args.output
    manifest = load_json(staging / "generated" / "wikisource-current-manifest.json")
    sections: list[dict[str, Any]] = []
    for label in EXPECTED_LABELS:
        payload = load_json(staging / "source" / "text" / "wikisource-current" / f"{label}.json")
        parsed = payload.get("parse") or {}
        text = clean_text(parsed.get("text") or "")
        sections.append({
            "id": "introduction" if label == "Introduction" else f"piece-{int(label):03d}",
            "order": 0 if label == "Introduction" else int(label),
            "label": label,
            "title": "Introduction" if label == "Introduction" else f"Gitanjali {label}",
            "source_page": f"Gitanjali/{label}",
            "source_revision": parsed.get("revid"),
            "source_url": next((p["url"] for p in manifest["pages"] if p["label"] == label), ""),
            "text": text,
            "word_count": len(text.split()),
            "text_sha256": sha256_text(text),
        })
    reader_audit = {
        "expected_section_count": 104,
        "actual_section_count": len(sections),
        "ordered": [s["label"] for s in sections] == EXPECTED_LABELS,
        "unique_source_revisions": len({s["source_revision"] for s in sections}) == 104,
        "non_empty": all(s["word_count"] > 0 for s in sections),
        "section_count_pass": len(sections) == 104,
        "text_completeness_pass": len(sections) == 104 and all(s["word_count"] > 0 for s in sections),
        "heading_review": "PENDING_EDITORIAL_REVIEW_AGAINST_1913_SCAN",
    }
    write_json(output / "reader" / "gitanjali-reader-artifact.json", {
        "schema": "earnalism.reader.gitanjali.v1",
        "title": "Gitanjali",
        "subtitle": "Song Offerings",
        "author": "Rabindranath Tagore",
        "introduction_by": "W. B. Yeats",
        "edition": "Macmillan, 1913",
        "language": "en",
        "sections": sections,
        "audit": reader_audit,
    })
    write_json(output / "reader" / "reader-audit.json", reader_audit)

    audio_dir = staging / "source" / "audio" / "vbr"
    tracks: list[dict[str, Any]] = []
    cursor = 0.0
    for index, filename in enumerate(EXPECTED_TRACKS, 1):
        data = probe(audio_dir / filename)
        duration = float((data.get("format") or {}).get("duration") or 0)
        tracks.append({
            "track": index,
            "file": filename,
            "title": (load_json(staging / "source" / "metadata" / "internet-archive-audio-metadata.json")["files"] and next(
                f.get("title", "") for f in load_json(staging / "source" / "metadata" / "internet-archive-audio-metadata.json")["files"] if f.get("name") == filename
            )),
            "start_seconds_measured": round(cursor, 6),
            "end_seconds_measured": round(cursor + duration, 6),
            "duration_seconds_measured": round(duration, 6),
            "measurement": "ffprobe_format_duration",
        })
        cursor += duration
    write_json(output / "audio" / "track-sync.json", {
        "schema": "earnalism.audio.gitanjali.track-sync.v1",
        "granularity": "track",
        "tracks": tracks,
        "total_duration_seconds_measured": round(cursor, 6),
        "fine_alignment_status": "BLOCKED_PENDING_TEXT_AUDIO_ALIGNMENT",
        "release_ready": False,
    })

    cover_review = {
        "status": "BLOCKED_MISSING_CANONICAL_COVER_PACKET",
        "title": "Gitanjali",
        "front_cover": {"status": "MISSING", "approved": False},
        "back_cover": {"status": "MISSING", "approved": False},
        "archival_source_required": "1913 Macmillan scan or an explicitly approved public-domain derivative",
        "original_sources_preserved": True,
    }
    write_json(output / "cover-review.json", cover_review)

    review = {
        "title": "Gitanjali",
        "status": "BLOCKED_FOR_RELEASE_REVIEW_COMPLETION",
        "reader": reader_audit,
        "audio": {"track_count": len(tracks), "track_sync_generated": True, "fine_alignment": "BLOCKED"},
        "cover": cover_review,
        "gates": {
            "canonical_reader_artifact": reader_audit["section_count_pass"] and reader_audit["text_completeness_pass"],
            "editorial_1913_comparison": False,
            "canonical_cover_review": False,
            "measured_fine_sync": False,
            "full_audio_release_gate": False,
            "dry_run_import": False,
            "browser_route_checks": False,
            "public_publish": False,
        },
        "fail_closed_reasons": [
            "1913 scan comparison and editorial heading review are not complete.",
            "Canonical front and back cover approvals are missing.",
            "Track timings are measured, but text-to-audio fine alignment is not proven.",
            "Existing production release-gate and dry-run route checks have not passed for Gitanjali.",
        ],
    }
    write_json(output / "release-review.json", review)
    print(json.dumps({"status": review["status"], "sections": len(sections), "tracks": len(tracks), "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
