#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTENT_ROOT = ROOT / "content" / "books"
CONTROLLED_ROOT = ROOT / "data" / "controlled_publications"
BENGALI_RE = re.compile(r"[\u0980-\u09FF]")

GUTENBERG_JUNK_RE = re.compile(
    r"Project Gutenberg|Gutenberg-tm|START OF THE PROJECT GUTENBERG|END OF THE PROJECT GUTENBERG|"
    r"www\.gutenberg\.org|donate to Project Gutenberg|^\s*Produced by\b|^\s*Transcriber",
    re.I | re.M,
)
WIKISOURCE_JUNK_RE = re.compile(
    r"\b(Edit|Download as|Category:|Creative Commons|Wikisource|Special:|Wikipedia article|Wikidata item)\b",
    re.I,
)
PUBLIC_FORBIDDEN_RE = re.compile(r"Listen Now|AudioObject|checkout|buy now|add to cart", re.I)
MOJIBAKE_RE = re.compile(r"(à¦|à§|Ã|Â|ð)")

EXPECTED_MIN_CHAPTERS = {
    "frankenstein": 20,
    "jekyll-and-hyde": 10,
    "carmilla": 1,
    "hound-of-the-baskervilles": 15,
    "picture-of-dorian-gray": 20,
    "woman-in-white": 20,
    "hungry-stones": 1,
    "devdas": 10,
    "pather-panchali": 10,
    "eyesore-chokher-bali": 30,
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def chapter_files(slug: str) -> list[Path]:
    return sorted((CONTENT_ROOT / slug / "chapters").glob("*.json"))


def artifact_chapter_files(slug: str) -> list[Path]:
    return sorted((CONTROLLED_ROOT / slug / "chapters").glob("chapter-*.json"))


def draft_flags_safe(book_json: dict[str, Any]) -> list[str]:
    issues = []
    expected_false = [
        "isPublic",
        "isLive",
        "showInPublicLibrary",
        "showInHomepage",
        "allowPublicReading",
        "allowCheckout",
        "allowPayment",
        "is_published",
    ]
    for key in expected_false:
        if book_json.get(key) is not False:
            issues.append(f"Draft book.json {key} must be false before promotion.")
    if book_json.get("publicationStatus") != "draft":
        issues.append("Draft book.json publicationStatus must be draft before promotion.")
    return issues


def artifact_flags_safe(public_book: dict[str, Any]) -> list[str]:
    issues = []
    if public_book.get("publicationStatus") != "live":
        issues.append("Promotion artifact publicationStatus must be live.")
    for key in ["isPublic", "isLive", "showInPublicLibrary", "allowPublicReading", "is_published"]:
        if public_book.get(key) is not True:
            issues.append(f"Promotion artifact {key} must be true for live-passing books.")
    for key in ["showInHomepage", "allowCheckout", "allowPayment", "audio_enabled", "audiobook_enabled", "generate_audiobook"]:
        if public_book.get(key) is not False:
            issues.append(f"Promotion artifact {key} must remain false.")
    if public_book.get("audiobook_assets") not in ({}, None):
        issues.append("Promotion artifact must not contain audiobook assets.")
    return issues


def iter_string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(iter_string_values(item))
        return strings
    if isinstance(value, dict):
        strings: list[str] = []
        for item in value.values():
            strings.extend(iter_string_values(item))
        return strings
    return []


def score_book(entry: dict[str, Any]) -> dict[str, Any]:
    slug = entry["slug"]
    book_dir = CONTENT_ROOT / slug
    artifact_dir = CONTROLLED_ROOT / slug
    issues_by_area: dict[str, list[str]] = {
        "sourceLegalCompleteness": [],
        "boilerplateJunkRemoval": [],
        "structuralIntegrity": [],
        "textFidelity": [],
        "bengaliRendering": [],
        "readerUxRendering": [],
        "publicGovernanceSafety": [],
    }

    source_rights = book_dir / "source-rights.md"
    book_json_path = book_dir / "book.json"
    raw_dir = book_dir / "raw"
    if not source_rights.exists():
        issues_by_area["sourceLegalCompleteness"].append("source-rights.md is missing.")
    if not book_json_path.exists():
        issues_by_area["sourceLegalCompleteness"].append("book.json is missing.")
        book_json = {}
    else:
        book_json = read_json(book_json_path)
    if not raw_dir.exists() or not any(raw_dir.iterdir()):
        issues_by_area["sourceLegalCompleteness"].append("Raw source archive is missing.")
    rights_text = source_rights.read_text(encoding="utf-8") if source_rights.exists() else ""
    if "Status: ready_for_auto_publication" not in rights_text:
        issues_by_area["sourceLegalCompleteness"].append("Source-rights note is not ready_for_auto_publication.")
    if entry.get("sourceUrl") and entry["sourceUrl"] not in rights_text:
        issues_by_area["sourceLegalCompleteness"].append("Source-rights note does not include approved source URL.")

    chapters = []
    combined = ""
    for path in chapter_files(slug):
        payload = read_json(path)
        chapters.append(payload)
        combined += "\n\n" + str(payload.get("content") or "")
    if "�" in combined:
        issues_by_area["boilerplateJunkRemoval"].append("Replacement character found in reader content.")
    if GUTENBERG_JUNK_RE.search(combined):
        issues_by_area["boilerplateJunkRemoval"].append("Project Gutenberg boilerplate/furniture found in reader content.")
    if WIKISOURCE_JUNK_RE.search(combined):
        issues_by_area["boilerplateJunkRemoval"].append("Wikisource page furniture found in reader content.")
    if re.search(r"\n\s*\d{1,4}\s*\n", combined):
        issues_by_area["boilerplateJunkRemoval"].append("Likely isolated page number found in reader content.")

    expected_min = EXPECTED_MIN_CHAPTERS.get(slug, 1)
    if len(chapters) < expected_min:
        issues_by_area["structuralIntegrity"].append(f"Chapter count {len(chapters)} is below expected minimum {expected_min}.")
    if slug == "hungry-stones":
        if len(chapters) != 1:
            issues_by_area["structuralIntegrity"].append("The Hungry Stones must be exactly one extracted story.")
        if re.search(r"\b(The Victory|The Cabuliwallah|The Home-coming)\b", combined):
            issues_by_area["structuralIntegrity"].append("The Hungry Stones contains other stories from the collection.")
    titles = [str(chapter.get("title") or "").strip() for chapter in chapters]
    if len(titles) != len(set(titles)):
        issues_by_area["structuralIntegrity"].append("Duplicate chapter titles detected.")
    if any(not title for title in titles):
        issues_by_area["structuralIntegrity"].append("One or more chapters are missing titles.")

    for chapter in chapters:
        if not chapter.get("sourceSha256") or not chapter.get("sanitizedSha256"):
            issues_by_area["textFidelity"].append("Chapter is missing source/sanitized checksum.")
            break
        if str(chapter.get("content") or "").strip().lower() in {"summary", "chapter summary"}:
            issues_by_area["textFidelity"].append("Chapter content appears summarized.")
            break
    if book_json.get("wordCountApprox", 0) < 500 and slug not in {"hungry-stones"}:
        issues_by_area["textFidelity"].append("Book word count is implausibly low.")

    if entry.get("language") == "bn":
        if not BENGALI_RE.search(combined):
            issues_by_area["bengaliRendering"].append("No Bengali text detected.")
        if unicodedata.normalize("NFC", combined) != combined:
            issues_by_area["bengaliRendering"].append("Bengali content is not NFC-normalized.")
        if MOJIBAKE_RE.search(combined):
            issues_by_area["bengaliRendering"].append("Mojibake pattern detected.")
        bengali_chars = len(BENGALI_RE.findall(combined))
        if bengali_chars / max(len(combined), 1) < 0.35:
            issues_by_area["bengaliRendering"].append("Bengali character ratio is too low.")
    elif "eyesore" in slug and "Chokher Bali" not in entry.get("displayTitle", ""):
        issues_by_area["bengaliRendering"].append("Eyesore source/title metadata is not the approved English translation.")

    if not artifact_dir.exists():
        issues_by_area["readerUxRendering"].append("Controlled publication artifact directory is missing.")
    else:
        for required in ["public_book.json", "reader_manifest.json", "source_evidence.json", "approval_evidence.json", "checksum_manifest.json"]:
            if not (artifact_dir / required).exists():
                issues_by_area["readerUxRendering"].append(f"Missing artifact file: {required}")
        public_book_path = artifact_dir / "public_book.json"
        reader_manifest_path = artifact_dir / "reader_manifest.json"
        if public_book_path.exists():
            public_book = read_json(public_book_path)
            issues_by_area["publicGovernanceSafety"].extend(artifact_flags_safe(public_book))
            if any(PUBLIC_FORBIDDEN_RE.search(text) for text in iter_string_values(public_book)):
                issues_by_area["publicGovernanceSafety"].append("Forbidden public audio/payment/commerce term found in publication artifact.")
        if reader_manifest_path.exists():
            reader_manifest = read_json(reader_manifest_path)
            if len(reader_manifest.get("chapters") or []) != len(artifact_chapter_files(slug)):
                issues_by_area["readerUxRendering"].append("Reader manifest chapter count does not match artifact chapter files.")
            if reader_manifest.get("audio_enabled") is not False or reader_manifest.get("audiobook_enabled") is not False:
                issues_by_area["publicGovernanceSafety"].append("Reader manifest audio flags are not false.")

    issues_by_area["publicGovernanceSafety"].extend(draft_flags_safe(book_json))
    if book_json.get("showInHomepage") is not False:
        issues_by_area["publicGovernanceSafety"].append("showInHomepage must remain false.")

    area_points = {
        "sourceLegalCompleteness": 15,
        "boilerplateJunkRemoval": 15,
        "structuralIntegrity": 15,
        "textFidelity": 15,
        "bengaliRendering": 15,
        "readerUxRendering": 15,
        "publicGovernanceSafety": 10,
    }
    score = sum(points for area, points in area_points.items() if not issues_by_area[area])
    blockers = [issue for issues in issues_by_area.values() for issue in issues]
    return {
        "slug": slug,
        "title": entry.get("displayTitle") or entry.get("title"),
        "language": entry.get("language"),
        "sourceUrl": entry.get("sourceUrl"),
        "score": score,
        "status": "PASS_100" if score == 100 and not blockers else "HOLD",
        "chapterCount": len(chapters),
        "wordCountApprox": int(book_json.get("wordCountApprox", 0) or 0),
        "routeStatus": "READY" if score == 100 and not blockers else "HOLD",
        "bengaliRenderingStatus": "PASS" if entry.get("language") != "bn" or not issues_by_area["bengaliRendering"] else "HOLD",
        "blockers": blockers,
        "areaIssues": issues_by_area,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Earnalism reader content quality for a controlled batch.")
    parser.add_argument("--manifest", default="book_import_manifest.batch-1.json")
    parser.add_argument("--require-score", type=int, default=100)
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = ROOT / manifest_path
    manifest = read_json(manifest_path)
    results = [score_book(entry) for entry in manifest.get("books", [])]
    report = {
        "batchId": manifest.get("batchId"),
        "requiredScore": args.require_score,
        "totalBooksConfigured": len(results),
        "passingBooks": [item["slug"] for item in results if item["score"] >= args.require_score and item["status"] == "PASS_100"],
        "heldBooks": [item["slug"] for item in results if item["score"] < args.require_score or item["status"] != "PASS_100"],
        "books": results,
    }
    write_json(CONTENT_ROOT / "reader-content-quality-report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["heldBooks"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
