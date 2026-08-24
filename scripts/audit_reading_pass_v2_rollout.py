#!/usr/bin/env python3
"""Read-only parity gate for Reading Pass v2 reader and audio rollout truth."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.catalog_truth import (  # noqa: E402
    CONTROLLED_LIVE_BOOK_SLUGS,
    can_expose_audio,
    controlled_artifact_dir,
    controlled_audio_validation_issues,
    controlled_reader_validation_issues,
    load_controlled_artifact_book,
)


def fetch_public_books(api_base: str) -> list[dict]:
    request = Request(f"{api_base.rstrip('/')}/books", headers={"Accept": "application/json"})
    with urlopen(request, timeout=30) as response:  # nosec B310 - explicit operator supplied API base
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise ValueError("/books did not return an array")
    return [row for row in payload if isinstance(row, dict)]


def controlled_truth() -> tuple[dict[str, dict], dict[str, dict]]:
    readers: dict[str, dict] = {}
    audio: dict[str, dict] = {}
    for slug in sorted(set(CONTROLLED_LIVE_BOOK_SLUGS)):
        package = controlled_artifact_dir(slug)
        reader_issues = list(controlled_reader_validation_issues(slug, str(package)))
        if reader_issues:
            continue
        book = load_controlled_artifact_book(slug, include_content=False, artifact_dir=package)
        if not book:
            continue
        readers[slug] = {
            "title": str(book.get("title") or ""),
            "artifact_dir": str(package.relative_to(ROOT)),
            "reader_issues": reader_issues,
            "audio_issues": list(controlled_audio_validation_issues(slug, str(package))),
        }
        if can_expose_audio(book):
            audio[slug] = dict(readers[slug])
    return readers, audio


def build_parity_report(public_books: list[dict]) -> tuple[dict, list[dict]]:
    public_reader = {str(row.get("slug") or ""): row for row in public_books if row.get("reader_enabled") is True and row.get("slug")}
    public_audio = {str(row.get("slug") or ""): row for row in public_books if row.get("audio_enabled") is True and row.get("slug")}
    controlled_reader, controlled_audio = controlled_truth()
    public_only = sorted(set(public_reader) - set(controlled_reader))
    controlled_only = sorted(set(controlled_reader) - set(public_reader))
    public_audio_beyond_control = sorted(set(public_audio) - set(controlled_audio))
    rows = []
    for slug in sorted(set(public_reader) | set(controlled_reader) | set(public_audio) | set(controlled_audio)):
        reasons: list[str] = []
        if slug in public_only:
            reasons.append("PUBLIC_READER_WITHOUT_CONTROLLED_READER_AUTHORIZATION")
        if slug in controlled_only:
            reasons.append("CONTROLLED_READER_NOT_PRESENT_IN_PUBLIC_CATALOG")
        if slug in public_audio_beyond_control:
            reasons.append("PUBLIC_AUDIO_WITHOUT_CONTROLLED_AUDIO_AUTHORIZATION")
        rows.append({
            "slug": slug,
            "public_reader": slug in public_reader,
            "controlled_reader": slug in controlled_reader,
            "public_audio": slug in public_audio,
            "controlled_audio": slug in controlled_audio,
            "classification": "PARITY" if not reasons else "MISMATCH",
            "reason_codes": ";".join(reasons),
        })
    report = {
        "schema_version": "earnalism.reading-pass-v2-rollout-parity.v1",
        "public_reader_set": sorted(public_reader),
        "controlled_reader_set": sorted(controlled_reader),
        "public_audio_set": sorted(public_audio),
        "controlled_audio_set": sorted(controlled_audio),
        "public_reader_only": public_only,
        "controlled_reader_only": controlled_only,
        "public_audio_beyond_control": public_audio_beyond_control,
        "reader_parity": not public_only and not controlled_only,
        "audio_safety": not public_audio_beyond_control,
        "result": "PASS" if not public_only and not controlled_only and not public_audio_beyond_control else "FAIL",
    }
    return report, rows


def write_report(output_dir: Path, report: dict, rows: list[dict]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    report["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    (output_dir / "parity.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (output_dir / "title-matrix.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["slug", "public_reader", "controlled_reader", "public_audio", "controlled_audio", "classification", "reason_codes"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="https://api.theearnalism.com/api")
    parser.add_argument("--public-books-file", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.public_books_file:
        payload = json.loads(args.public_books_file.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            parser.error("--public-books-file must contain a /books JSON array")
        public_books = [row for row in payload if isinstance(row, dict)]
    else:
        public_books = fetch_public_books(args.api_base)
    report, rows = build_parity_report(public_books)
    report["api_base"] = args.api_base.rstrip("/")
    write_report(args.output_dir, report, rows)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
