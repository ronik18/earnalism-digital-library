#!/usr/bin/env python3
"""Remove verified source wrappers from a controlled Bengali reader artifact.

This repair is intentionally narrow. It accepts either a leading title-page
wrapper ending at the canonical title, or a leading Bengali edition page-range
marker on every chapter. Both controlled-publication mirrors must match before
the script rebinds chapter, publication, source-evidence, reader-manifest, and
checksum hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED_ROOTS = (
    ROOT / "backend/data/controlled_publications",
    ROOT / "data/controlled_publications",
)
WORD_RE = re.compile(r"[\w\u0980-\u09FF]+(?:[-'][\w\u0980-\u09FF]+)?", re.UNICODE)
PAGE_RANGE_MARKER = re.compile(
    r"^[০-৯0-9]{4}\s*\(পৃ\.?\s*[০-৯0-9\s\-–—]+\)$",
)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected a JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_title_page(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).strip().casefold()
    return re.sub(r"[\s।.!?？]+$", "", normalized)


def strip_verified_title_page(content: str, *, title: str) -> tuple[str, str]:
    normalized = unicodedata.normalize(
        "NFC",
        content.replace("\r\n", "\n").replace("\r", "\n"),
    )
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
    expected = normalized_title_page(title)
    title_index = next(
        (
            index
            for index, paragraph in enumerate(paragraphs[:8])
            if expected and normalized_title_page(paragraph) == expected
        ),
        None,
    )
    if title_index is None:
        raise RuntimeError("Canonical title page was not found in the first eight paragraphs.")
    if title_index == 0:
        raise RuntimeError("No leading metadata exists before the canonical title page.")
    removed = "\n\n".join(paragraphs[: title_index + 1])
    cleaned = "\n\n".join(paragraphs[title_index + 1 :]).strip()
    if not cleaned:
        raise RuntimeError("Title-page repair would remove the entire chapter.")
    return cleaned, removed


def strip_verified_page_range(content: str) -> tuple[str, str]:
    normalized = unicodedata.normalize(
        "NFC",
        content.replace("\r\n", "\n").replace("\r", "\n"),
    )
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
    if not paragraphs or not PAGE_RANGE_MARKER.fullmatch(paragraphs[0]):
        raise RuntimeError("Leading Bengali edition page-range marker was not found.")
    removed = paragraphs[0]
    cleaned = "\n\n".join(paragraphs[1:]).strip()
    if not cleaned:
        raise RuntimeError("Page-range repair would remove the entire chapter.")
    return cleaned, removed


def repairable_chapter_content(content: str, *, title: str) -> tuple[str, str, str]:
    try:
        cleaned, removed = strip_verified_title_page(content, title=title)
        return cleaned, removed, "removed_source_frontmatter_through_canonical_title_page"
    except RuntimeError:
        cleaned, removed = strip_verified_page_range(content)
        return cleaned, removed, "removed_leading_bengali_edition_page_range"


def publication_repair_plan(publication: Path) -> list[dict[str, str]]:
    public_book = read_json(publication / "public_book.json")
    rows: list[dict[str, str]] = []
    clean_chapters: list[str] = []
    for chapter_path in sorted((publication / "chapters").glob("*.json")):
        chapter = read_json(chapter_path)
        content = str(chapter.get("content") or "")
        try:
            cleaned, removed, reason = repairable_chapter_content(
                content,
                title=str(public_book.get("title") or ""),
            )
        except RuntimeError:
            clean_chapters.append(chapter_path.name)
            continue
        rows.append(
            {
                "chapter": chapter_path.name,
                "new_content_sha256": sha256_text(cleaned),
                "removed_frontmatter_sha256": sha256_text(removed),
                "reason": reason,
            }
        )

    if rows and clean_chapters:
        raise RuntimeError(
            "Controlled publication has a mixed repaired/unrepaired chapter state: "
            + ", ".join(clean_chapters)
        )
    if rows:
        return rows

    source_evidence = read_json(publication / "source_evidence.json")
    if source_evidence.get("reader_facing_boilerplate_removed") is True:
        return []
    raise RuntimeError(
        "No verified frontmatter was found and source evidence does not confirm "
        "an earlier controlled repair."
    )


def chapter_rows(chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "bookSlug": chapter["bookSlug"],
            "chapterNumber": chapter["order"],
            "id": chapter["id"],
            "title": chapter["title"],
            "language": chapter["language"],
            "content": chapter["content"],
            "sourceSha256": chapter["sourceSha256"],
            "sanitizedSha256": chapter["sanitizedSha256"],
            "wordCountApprox": chapter["word_count"],
            "characterCount": len(chapter["content"]),
            "readingTimeMinutesApprox": chapter["reading_minutes"],
            "sourceTitle": chapter["title"],
        }
        for chapter in chapters
    ]


def repair_publication(publication: Path, *, repaired_at: str) -> dict[str, Any]:
    public_book_path = publication / "public_book.json"
    public_book = read_json(public_book_path)
    chapter_paths = sorted((publication / "chapters").glob("*.json"))
    if not chapter_paths:
        raise RuntimeError(f"{publication.name} has no controlled chapters.")

    chapters: list[dict[str, Any]] = []
    chapter_repairs: list[dict[str, Any]] = []
    for chapter_path in chapter_paths:
        chapter = read_json(chapter_path)
        old_content = str(chapter.get("content") or "")
        cleaned, removed, reason = repairable_chapter_content(
            old_content,
            title=str(public_book.get("title") or ""),
        )
        sanitized_hash = sha256_text(cleaned)
        words = len(WORD_RE.findall(cleaned))
        reading_minutes = max(1, math.ceil(words / 240))
        chapter.update(
            {
                "content": cleaned,
                "content_hash": sanitized_hash,
                "sanitizedSha256": sanitized_hash,
                "word_count": words,
                "reading_minutes": reading_minutes,
                "updated_at": repaired_at,
            }
        )
        chapters.append(chapter)
        chapter_repairs.append(
            {
                "chapter": chapter_path.name,
                "old_content_sha256": sha256_text(old_content),
                "new_content_sha256": sanitized_hash,
                "removed_frontmatter_sha256": sha256_text(removed),
                "removed_frontmatter_characters": len(removed),
                "reason": reason,
                "word_count": words,
                "reading_minutes": reading_minutes,
            }
        )

    source_hash = sha256_text("\n\n".join(chapter["content"] for chapter in chapters))
    for chapter_path, chapter in zip(chapter_paths, chapters):
        chapter["sourceSha256"] = source_hash
        write_json(chapter_path, chapter)

    publication_content_hash = sha256_text(
        json.dumps(chapter_rows(chapters), ensure_ascii=False, sort_keys=True)
    )
    public_chapters = {
        item.get("id"): item
        for item in public_book.get("chapters", [])
        if isinstance(item, dict)
    }
    for chapter in chapters:
        public_chapter = public_chapters.get(chapter.get("id"))
        if public_chapter is None:
            raise RuntimeError(f"public_book.json is missing chapter {chapter.get('id')}.")
        public_chapter.update(
            {
                "word_count": chapter["word_count"],
                "reading_minutes": chapter["reading_minutes"],
                "updated_at": repaired_at,
            }
        )
    total_words = sum(chapter["word_count"] for chapter in chapters)
    total_reading_minutes = max(1, math.ceil(total_words / 240))
    public_book.update(
        {
            "source_hash": source_hash,
            "content_hash": publication_content_hash,
            "estimated_reading_time": f"{total_reading_minutes} min",
            "updated_at": repaired_at,
        }
    )
    write_json(public_book_path, public_book)

    source_evidence_path = publication / "source_evidence.json"
    source_evidence = read_json(source_evidence_path)
    source_evidence.update(
        {
            "source_hash": source_hash,
            "content_hash": publication_content_hash,
            "reader_facing_boilerplate_removed": True,
            "reader_content_repaired_at": repaired_at,
            "reader_content_repair": sorted({item["reason"] for item in chapter_repairs}),
        }
    )
    write_json(source_evidence_path, source_evidence)

    reader_manifest_path = publication / "reader_manifest.json"
    reader_manifest = read_json(reader_manifest_path)
    reader_chapters = {
        item.get("id"): item
        for item in reader_manifest.get("chapters", [])
        if isinstance(item, dict)
    }
    for chapter in chapters:
        reader_chapter = reader_chapters.get(chapter.get("id"))
        if reader_chapter is None:
            raise RuntimeError(f"reader_manifest.json is missing chapter {chapter.get('id')}.")
        reader_chapter.update(
            {
                "word_count": chapter["word_count"],
                "reading_minutes": chapter["reading_minutes"],
                "updated_at": repaired_at,
            }
        )
    reader_manifest["generated_at"] = repaired_at
    write_json(reader_manifest_path, reader_manifest)

    checksum_path = publication / "checksum_manifest.json"
    checksum_manifest = read_json(checksum_path)
    checksum_manifest["generated_at"] = repaired_at
    for entry in checksum_manifest.get("files", []):
        relative = str(entry.get("file") or "")
        if not relative or relative == "checksum_manifest.json":
            continue
        target = publication / relative
        if not target.is_file():
            raise RuntimeError(f"Checksum target is missing: {target}")
        entry["sha256"] = sha256_file(target)
    write_json(checksum_path, checksum_manifest)

    return {
        "slug": publication.name,
        "chapter_count": len(chapters),
        "source_hash": source_hash,
        "publication_content_hash": publication_content_hash,
        "removed_frontmatter_characters": sum(
            item["removed_frontmatter_characters"] for item in chapter_repairs
        ),
        "word_count": total_words,
        "reading_minutes": total_reading_minutes,
        "chapter_repairs": chapter_repairs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    candidate_publications = [root / args.slug for root in CONTROLLED_ROOTS]
    if not all(path.is_dir() for path in candidate_publications):
        raise RuntimeError(f"Controlled publication is missing for {args.slug}.")
    publications = [
        path
        for path in candidate_publications
        if (path / "public_book.json").is_file() and (path / "chapters").is_dir()
    ]
    if not publications:
        raise RuntimeError(f"No complete controlled publication exists for {args.slug}.")
    before = [
        [
            (chapter.relative_to(path).as_posix(), chapter.read_bytes())
            for chapter in sorted((path / "chapters").glob("*.json"))
        ]
        for path in publications
    ]
    if len(before) > 1 and any(rows != before[0] for rows in before[1:]):
        raise RuntimeError("Controlled publication mirrors do not have identical chapter bytes.")
    plans = [publication_repair_plan(path) for path in publications]
    if any(plan != plans[0] for plan in plans[1:]):
        raise RuntimeError("Controlled publication mirrors have different repair plans.")
    if not plans[0]:
        print(
            json.dumps(
                {
                    "status": "ALREADY_REPAIRED",
                    "slug": args.slug,
                    "chapter_repairs": [],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if not args.apply:
        print(
            json.dumps(
                {
                    "status": "DRY_RUN_PASS",
                    "slug": args.slug,
                    "chapter_repairs": plans[0],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    repaired_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    results = [repair_publication(path, repaired_at=repaired_at) for path in publications]
    if len(results) > 1 and any(result != results[0] for result in results[1:]):
        raise RuntimeError("Controlled publication mirrors diverged during repair.")
    print(json.dumps({"status": "APPLIED", **results[0]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
