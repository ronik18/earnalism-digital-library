#!/usr/bin/env python3
"""Prepare reader-ready Bengali source repairs from validated Wikisource pages."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "book_import_manifest.json"
DEFAULT_REPAIR_REPORT = ROOT / "output/source_repair/20260602T192021Z/source_repair_report.json"
DEFAULT_OUTPUT_ROOT = ROOT / "output/bengali_source_repair"

KEY_ALIASES = {
    "authorlatin": "author_latin",
    "authordeathyear": "author_death_year",
    "originalpublicationyear": "original_publication_year",
    "sourceurl": "source_url",
    "sourcetype": "source_type",
    "sourcelicense": "source_license",
    "rightsbasis": "rights_basis",
    "commercialuseallowed": "commercial_use_allowed",
    "audioallowed": "audio_allowed",
    "requiresattribution": "requires_attribution",
    "requiressharealike": "requires_share_alike",
    "categoryslug": "category_slug",
    "shortdescription": "short_description",
    "aboutauthor": "about_author",
    "ispublished": "is_published",
    "attributionnotice": "required_attribution",
    "forbiddensourceterms": "forbidden_source_terms",
}

BENGALI_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
BENGALI_CHAPTER_ORDER = {
    "এক": 1,
    "দুই": 2,
    "তিন": 3,
    "চার": 4,
    "পাঁচ": 5,
    "ছয়": 6,
    "ছয়": 6,
    "সাত": 7,
    "আট": 8,
    "নয়": 9,
    "নয়": 9,
    "প্রথম": 1,
    "দ্বিতীয়": 2,
    "দ্বিতীয়": 2,
    "তৃতীয়": 3,
    "তৃতীয়": 3,
    "চতুর্থ": 4,
    "পঞ্চম": 5,
    "ষষ্ঠ": 6,
    "সপ্তম": 7,
    "অষ্টম": 8,
    "নবম": 9,
    "দশম": 10,
    "একাদশ": 11,
    "দ্বাদশ": 12,
    "ত্রয়োদশ": 13,
    "ত্রয়োদশ": 13,
    "চতুর্দ্দশ": 14,
    "চতুর্দশ": 14,
    "পঞ্চদশ": 15,
}


REPAIR_SOURCES: dict[str, dict[str, Any]] = {
    "BN-045": {
        "source_title": "নিষ্কৃতি (শরৎচন্দ্র চট্টোপাধ্যায়, ১৯৫২)",
        "chapters": ["এক", "দুই", "তিন", "চার", "পাঁচ", "ছয়", "সাত", "আট", "নয়"],
        "slug": "nishkriti",
        "category_slug": "literary-fiction",
    },
    "BN-056": {
        "source_title": "রাধারাণী (১৯৪০)",
        "chapters": [
            "প্রথম পরিচ্ছেদ",
            "দ্বিতীয় পরিচ্ছেদ",
            "তৃতীয় পরিচ্ছেদ",
            "চতুর্থ পরিচ্ছেদ",
            "পঞ্চম পরিচ্ছেদ",
            "ষষ্ঠ পরিচ্ছেদ",
            "সপ্তম পরিচ্ছেদ",
            "অষ্টম পরিচ্ছেদ",
        ],
        "slug": "radharani",
        "category_slug": "literary-fiction",
    },
    "BN-057": {
        "source_title": "যুগলাঙ্গুরীয় (১৮৯৩)",
        "chapters": [
            "প্রথম পরিচ্ছেদ",
            "দ্বিতীয় পরিচ্ছেদ",
            "তৃতীয় পরিচ্ছেদ",
            "চতুর্থ পরিচ্ছেদ",
            "পঞ্চম পরিচ্ছেদ",
            "ষষ্ঠ পরিচ্ছেদ",
            "সপ্তম পরিচ্ছেদ",
            "অষ্টম পরিচ্ছেদ",
            "নবম পরিচ্ছেদ",
            "দশম পরিচ্ছেদ",
        ],
        "slug": "yugalanguriya",
        "category_slug": "adventure",
    },
    "BN-062": {
        "source_title": "মুচিরাম গুড়ের জীবনচরিত (১৯৪৪)",
        "chapters": ["প্রথম পরিচ্ছেদ", "দ্বিতীয় পরিচ্ছেদ"],
        "slug": "muchiram-gurer-jibanchorit",
        "category_slug": "literary-fiction",
    },
    "BN-067": {
        "source_title": "লোকরহস্য (১৯৩৯)",
        "chapters": [
            "বাবু",
            "গর্দ্দভ",
            "বাঙ্গালা সাহিত্যের আদর",
            "সুবর্ণগোলক",
            "গ্রাম্য কথা",
            "ব্যাঘ্রাচার্য্য বৃহল্লাঙ্গুল",
            "দাম্পত্য দণ্ডবিধির আইন",
            "ইংরাজস্তোত্র",
            "রামায়ণের সমালোচন",
            "বর্ষ সমালোচন",
            "বসন্ত এবং বিরহ",
            "কোন “স্পেশিয়ালের” পত্র",
            "হনুমদ্বাবুসংবাদ",
            "NEW YEAR’S DAY",
            "BRANSONISM",
            "পাঠভেদ",
        ],
        "slug": "lokrahasya",
        "category_slug": "history-strategy",
    },
    "BN-068": {
        "source_title": "মৃণালিনী (১৮৭৪)",
        "chapters": [],
        "slug": "mrinalini",
        "category_slug": "adventure",
    },
}

REPAIR_SOURCES["BN-068"]["chapters"] = (
    [f"প্রথম খণ্ড/{name} পরিচ্ছেদ" for name in ["প্রথম", "দ্বিতীয়", "তৃতীয়", "চতুর্থ", "পঞ্চম", "ষষ্ঠ", "সপ্তম", "অষ্টম"]]
    + [f"দ্বিতীয় খণ্ড/{name} পরিচ্ছেদ" for name in ["প্রথম", "দ্বিতীয়", "তৃতীয়", "চতুর্থ", "পঞ্চম", "ষষ্ঠ", "সপ্তম", "অষ্টম", "নবম", "দশম", "একাদশ", "দ্বাদশ"]]
    + [f"তৃতীয় খণ্ড/{name} পরিচ্ছেদ" for name in ["প্রথম", "দ্বিতীয়", "তৃতীয়", "চতুর্থ", "পঞ্চম", "ষষ্ঠ", "সপ্তম", "অষ্টম", "নবম", "দশম"]]
    + [f"চতুর্থ খণ্ড/{name} পরিচ্ছেদ" for name in ["প্রথম", "দ্বিতীয়", "তৃতীয়", "চতুর্থ", "পঞ্চম", "ষষ্ঠ", "সপ্তম", "অষ্টম", "নবম", "দশম", "একাদশ", "দ্বাদশ", "ত্রয়োদশ", "চতুর্দ্দশ", "পঞ্চদশ"]]
    + ["চতুর্থ খণ্ড/পরিশিষ্ট"]
)

UNREPAIRED_REASONS: dict[str, str] = {
    "BN-007": "Exact text only surfaced as low-quality Page namespace OCR in গল্পগুচ্ছ PDF; visible OCR artifacts make it unsafe for reader-ready upload.",
    "BN-010": "Exact text only surfaced as low-quality Page namespace OCR in গল্পগুচ্ছ PDF; visible OCR artifacts make it unsafe for reader-ready upload.",
    "BN-014": "Exact title was not available as clean author-specific main text; Page namespace candidate is not enough for reader-ready accuracy.",
    "BN-023": "Search results point to unrelated/near-title pages, not a verified exact text for ঠাকুরদা.",
    "BN-029": "Search results point to short poem/near-title pages, not the requested exact story.",
    "BN-032": "Exact Wikisource evidence is a proofread-page PDF with pagequality level 1 and visible OCR artifacts; held for manual proofreading.",
    "BN-034": "Only broad collection/Page namespace hits found; no clean exact author-specific text page.",
    "BN-037": "Only broad collection/Page namespace hits found; no clean exact author-specific text page.",
    "BN-039": "Exact text appears in Page namespace with pagequality level 1; held until proofread or clean transclusion exists.",
    "BN-040": "Proofread-page candidate contains visible OCR artifacts and no clean exact main text was found.",
    "BN-043": "Search results are unrelated collection references/Page hits; no clean exact text source identified.",
    "BN-044": "Exact proofread-page source contains visible OCR artifacts; held for manual proofreading before reader upload.",
    "BN-046": "Search returned unrelated chapters/near-title material, not a clean exact source for স্বামী.",
    "BN-047": "Search returned unrelated chapters/near-title material, not a clean exact source for সতী.",
    "BN-048": "No high-confidence exact Wikisource source found.",
    "BN-051": "Proofread-page candidate contains visible OCR artifacts; held for manual proofreading before reader upload.",
    "BN-053": "Exact proofread-page source contains visible OCR artifacts; held for manual proofreading before reader upload.",
    "BN-054": "Exact proofread-page source contains visible OCR artifacts; held for manual proofreading before reader upload.",
    "BN-055": "No clean exact author-specific text source identified; search returned unrelated page hits.",
    "BN-061": "Search results point to unrelated Bankim works, not a verified exact text for যোগিনী.",
    "BN-063": "Search results point to unrelated Bankim works, not a verified exact text for নলিনী.",
    "BN-075": "No clean exact author-specific Wikisource text found.",
    "BN-076": "Search results point to unrelated poems/chapters, not a verified exact text for ভিখারিণী.",
    "BN-078": "Search results point to poems/near-title pages, not a verified exact text for মেঘ.",
    "BN-079": "No clean exact author-specific Wikisource text found.",
    "BN-080": "Only audio/Page hints found; no clean exact text source identified.",
    "BN-081": "Only audio/chিঠিপত্র/Page hints found; no clean exact text source identified.",
    "BN-082": "No clean exact author-specific Wikisource text found.",
    "BN-085": "Search returned unrelated story/page hits, not a clean exact source for পোষ্টঅফিস.",
    "BN-087": "Search returned a different Bibhutibhushan collection story/page hit, not a clean exact source for পুঁইমাচা.",
}

BOILERPLATE_PATTERNS = [
    r"^এই লেখাটি .*(?:পাবলিক ডোমেইন|public domain).*$",
    r"^এই পাতাটির মুদ্রণ সংশোধন করা প্রয়োজন।$",
    r"^\{\{\{1\}\}\}$",
    r"^সূচীপত্র$",
    r"^প্রাপ্তিস্থান:?$",
    r"^প্রকাশক:?$",
    r"^মুদ্রাকর:?$",
]


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def source_url_for(title: str) -> str:
    return "https://bn.wikisource.org/wiki/" + quote(title.replace(" ", "_"), safe="/:()_,")


def normalize_key(value: str) -> str:
    value = unicodedata.normalize("NFC", value or "")
    value = value.replace("।", "")
    value = re.sub(r"\s+", " ", value)
    return value.strip().casefold()


def parse_manifest_objects(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    match = re.search(r'"books"\s*:\s*\[', text)
    start = match.end() if match else 0
    books: list[dict[str, Any]] = []
    in_string = False
    escaped = False
    depth = 0
    object_start: int | None = None
    for index, char in enumerate(text[start:], start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            if depth == 0:
                object_start = index
            depth += 1
            continue
        if char == "}" and depth:
            depth -= 1
            if depth == 0 and object_start is not None:
                books.append(json.loads(text[object_start : index + 1]))
                object_start = None
    return books


def normalize_book(raw: dict[str, Any]) -> dict[str, Any]:
    book: dict[str, Any] = {}
    for key, value in raw.items():
        book[KEY_ALIASES.get(key, key)] = value
    source_type = str(book.get("source_type") or "").strip()
    if source_type.lower().replace("_", "") == "wikisourcebengalihtml":
        book["source_type"] = "wikisource_bengali_html"
    book["is_published"] = False
    book["availability"] = "draft"
    book["audiobook_enabled"] = False
    book["generate_audiobook"] = False
    return book


def target_ids(repair_report: Path) -> list[str]:
    report = json.loads(repair_report.read_text(encoding="utf-8"))
    return [item["manifest_id"] for item in report.get("decisions", []) if item.get("decision") != "selected"]


def strip_leading_metadata(text: str, markers: list[str]) -> str:
    lines = [line.strip() for line in text.splitlines()]
    marker_keys = {normalize_key(marker) for marker in markers if marker}
    cut_at: int | None = None
    search_limit = min(len(lines), 40)
    for index, line in enumerate(lines[:search_limit]):
        if normalize_key(line) in marker_keys:
            cut_at = index + 1
    if cut_at is not None:
        lines = lines[cut_at:]

    cleaned: list[str] = []
    stop = False
    for line in lines:
        if stop:
            continue
        if any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in BOILERPLATE_PATTERNS):
            if "পাবলিক ডোমেইন" in line or "public domain" in line.casefold():
                stop = True
            continue
        cleaned.append(line)
    text = "\n".join(cleaned).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def alpha_noise_ratio(text: str) -> float:
    bengali = sum(1 for char in text if "\u0980" <= char <= "\u09ff")
    non_bengali_alpha = sum(1 for char in text if char.isalpha() and not ("\u0980" <= char <= "\u09ff"))
    total = bengali + non_bengali_alpha
    return (non_bengali_alpha / total) if total else 1.0


def chapter_url(source_title: str, chapter: str) -> str:
    return source_url_for(f"{source_title}/{chapter}")


def chapter_display_title(chapter: str) -> str:
    return chapter.replace("/", " / ")


def fetch_chapter(importer: Any, source_title: str, chapter: str, book: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    url = chapter_url(source_title, chapter)
    body, download_log = importer.download_source(url, "wikisource_bengali_html")
    raw = importer.decode_utf8(body)
    text, _warnings = importer.sanitize_text(raw, {**book, "source_url": url, "source_type": "wikisource_bengali_html"})
    markers = [book.get("author", ""), book.get("title", ""), source_title.split(" (", 1)[0], *chapter.split("/")]
    cleaned = strip_leading_metadata(text, markers)
    return cleaned, download_log


def build_prepared_text(importer: Any, book: dict[str, Any], repair: dict[str, Any]) -> tuple[str, list[dict[str, Any]], list[str]]:
    chapters: list[dict[str, Any]] = []
    warnings: list[str] = []
    chunks: list[str] = []
    for index, chapter in enumerate(repair["chapters"], start=1):
        print(f"  fetching chapter {index}/{len(repair['chapters'])}: {chapter}", flush=True)
        text, log = fetch_chapter(importer, repair["source_title"], chapter, book)
        words = len(importer.words(text))
        noise = alpha_noise_ratio(text)
        if words < 80:
            raise ValueError(f"{chapter} extracted too little text: {words} words")
        # These repairs use clean main-namespace Wikisource transclusions. Some
        # Bankim essays legitimately include English headings, terms, and quoted
        # legal text, so record the ratio for QA instead of rejecting on it.
        display = chapter_display_title(chapter)
        chunks.append(f"Chapter {index}. {display}\n\n{text}")
        chapters.append({
            "order": index,
            "title": display,
            "source_url": chapter_url(repair["source_title"], chapter),
            "download_url": log.get("download_url", ""),
            "word_count": words,
            "noise_ratio": round(noise, 4),
        })
        time.sleep(0.25)
    prepared_text = "\n\n".join(chunks).strip()
    if "উইকিসংকলন" in prepared_text or "Creative Commons" in prepared_text:
        raise ValueError("reader-facing text still contains source/license boilerplate")
    total_words = len(importer.words(prepared_text))
    if total_words < 500:
        raise ValueError(f"prepared text too short: {total_words} words")
    warnings.append(f"Assembled {len(chapters)} explicit chapter(s) from validated Bengali Wikisource subpages.")
    return prepared_text, chapters, warnings


def build_manifest(args: argparse.Namespace) -> int:
    importer = load_module(ROOT / "scripts/import_books.py", "earnalism_import_books")
    raw_by_id = {item.get("id"): item for item in parse_manifest_objects(args.manifest)}
    unresolved_ids = target_ids(args.repair_report)

    out_dir = args.output_dir / utc_stamp()
    text_dir = out_dir / "prepared_texts"
    text_dir.mkdir(parents=True, exist_ok=True)

    selected: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for manifest_id in unresolved_ids:
        raw = raw_by_id.get(manifest_id)
        if not raw:
            decisions.append({"manifest_id": manifest_id, "status": "skipped", "reason": "manifest row not found"})
            continue
        book = normalize_book(raw)
        repair = REPAIR_SOURCES.get(manifest_id)
        if not repair:
            decisions.append({
                "manifest_id": manifest_id,
                "title": book.get("title"),
                "author": book.get("author"),
                "status": "skipped",
                "reason": UNREPAIRED_REASONS.get(manifest_id, "no clean high-confidence source repair configured"),
            })
            print(f"skipped {manifest_id}: {book.get('title')} - {decisions[-1]['reason']}", flush=True)
            continue

        try:
            print(f"repairing {manifest_id}: {book.get('title')} from {repair['source_title']}", flush=True)
            book["slug"] = repair["slug"]
            book["category_slug"] = repair["category_slug"]
            book["source_url"] = source_url_for(repair["source_title"])
            book["source_type"] = "wikisource_bengali_html"
            book["source_license"] = (
                "Underlying Bengali literary text is public domain in India and the U.S.; "
                "Bengali Wikisource transcription/source layer is reused under CC BY-SA terms."
            )
            book["rights_basis"] = (
                f"Author died {book.get('author_death_year')}. "
                f"Original publication {book.get('original_publication_year')}. "
                "Public domain in India and the U.S.; source evidence kept internal/admin-only."
            )
            book["commercial_use_allowed"] = True
            book["requires_attribution"] = True
            book["requires_share_alike"] = True
            book["required_attribution"] = (
                "Source transcription from Bengali Wikisource, reused under CC BY-SA terms. "
                "Original literary text is public domain."
            )
            prepared_text, chapters, warnings = build_prepared_text(importer, book, repair)
            text_path = text_dir / f"{book['slug']}.txt"
            text_path.write_text(prepared_text, encoding="utf-8")
            book["prepared_text_path"] = str(text_path)
            chapter_rules = book.get("chapter_rules") if isinstance(book.get("chapter_rules"), dict) else {}
            chapter_rules["strict_prepared_chapter_markers"] = True
            book["chapter_rules"] = chapter_rules
            book["minimum_word_count"] = max(500, int(len(importer.words(prepared_text)) * 0.85))
            book["import_notes"] = [
                f"Generated from unresolved Bengali manifest row {manifest_id}.",
                "Prepared text assembled from validated author-specific Bengali Wikisource subpages.",
            ]
            selected.append(book)
            decisions.append({
                "manifest_id": manifest_id,
                "title": book.get("title"),
                "author": book.get("author"),
                "status": "selected",
                "slug": book.get("slug"),
                "source_url": book.get("source_url"),
                "category_slug": book.get("category_slug"),
                "chapter_count": len(chapters),
                "word_count": len(importer.words(prepared_text)),
                "warnings": warnings,
                "chapters": chapters,
            })
            print(f"selected {manifest_id}: {book.get('title')} ({len(chapters)} chapters)", flush=True)
        except Exception as exc:  # noqa: BLE001 - keep processing other repair cases
            decisions.append({
                "manifest_id": manifest_id,
                "title": book.get("title"),
                "author": book.get("author"),
                "status": "skipped",
                "source_url": source_url_for(repair["source_title"]),
                "reason": str(exc),
            })
            print(f"skipped {manifest_id}: {book.get('title')} - {exc}", flush=True)

    manifest_path = out_dir / "bengali_source_repaired_upload_manifest.json"
    report_path = out_dir / "bengali_source_repair_report.json"
    manifest_path.write_text(json.dumps({"all_or_nothing": False, "books": selected}, ensure_ascii=False, indent=2), encoding="utf-8")
    report = {
        "generated_at": now_iso(),
        "source_manifest": str(args.manifest),
        "source_repair_report": str(args.repair_report),
        "target_case_count": len(unresolved_ids),
        "selected_count": len(selected),
        "skipped_count": len([item for item in decisions if item["status"] == "skipped"]),
        "selected_category_distribution": dict(Counter(book.get("category_slug", "") for book in selected)),
        "decisions": decisions,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nmanifest {manifest_path}", flush=True)
    print(f"report {report_path}", flush=True)
    print(f"selected {report['selected_count']}; skipped {report['skipped_count']}; target cases {report['target_case_count']}", flush=True)
    return 0 if selected else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--repair-report", type=Path, default=DEFAULT_REPAIR_REPORT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.manifest = args.manifest.expanduser().resolve()
    args.repair_report = args.repair_report.expanduser().resolve()
    args.output_dir = args.output_dir.expanduser().resolve()
    return build_manifest(args)


if __name__ == "__main__":
    raise SystemExit(main())
