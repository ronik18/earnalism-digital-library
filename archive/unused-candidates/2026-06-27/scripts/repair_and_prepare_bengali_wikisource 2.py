#!/usr/bin/env python3
"""Deep-repair held Bengali Wikisource rows into upload-ready drafts.

The importer intentionally rejects short disambiguation/index pages. This tool
looks for exact main-namespace edition roots or story pages, assembles clean
reader text without rewriting the work, and emits a normal Earnalism import
manifest so the existing compliance/upload pipeline remains the source of truth.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "book_import_manifest.json"
DEFAULT_DRY_RUN_REPORT = ROOT / "output/bengali_missing_source_recheck_import/20260604T150656Z/dry_run_report.json"
DEFAULT_OUTPUT_ROOT = ROOT / "output/bengali_wikisource_deep_repair"
WIKISOURCE_API = "https://bn.wikisource.org/w/api.php"
USER_AGENT = "EarnalismDigitalLibrarySourceRepair/1.0 (https://theearnalism.com)"

BENGALI_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
BENGALI_NUMBERS = {
    "উপক্রমণিকা": 0,
    "ভূমিকা": 0,
    "প্রথম": 1,
    "এক": 1,
    "১": 1,
    "দ্বিতীয়": 2,
    "দ্বিতীয়": 2,
    "দুই": 2,
    "২": 2,
    "তৃতীয়": 3,
    "তৃতীয়": 3,
    "তিন": 3,
    "৩": 3,
    "চতুর্থ": 4,
    "চার": 4,
    "৪": 4,
    "পঞ্চম": 5,
    "পাঁচ": 5,
    "৫": 5,
    "ষষ্ঠ": 6,
    "ছয়": 6,
    "ছয়": 6,
    "৬": 6,
    "সপ্তম": 7,
    "সাত": 7,
    "৭": 7,
    "অষ্টম": 8,
    "আট": 8,
    "৮": 8,
    "নবম": 9,
    "নয়": 9,
    "নয়": 9,
    "৯": 9,
    "দশম": 10,
    "দশ": 10,
    "১০": 10,
    "একাদশ": 11,
    "১১": 11,
    "দ্বাদশ": 12,
    "১২": 12,
    "ত্রয়োদশ": 13,
    "ত্রয়োদশ": 13,
    "১৩": 13,
    "চতুর্দ্দশ": 14,
    "চতুর্দশ": 14,
    "১৪": 14,
    "পঞ্চদশ": 15,
    "১৫": 15,
    "ষোড়শ": 16,
    "ষোড়শ": 16,
    "১৬": 16,
    "সপ্তদশ": 17,
    "১৭": 17,
    "অষ্টাদশ": 18,
    "১৮": 18,
    "ঊনবিংশ": 19,
    "উনবিংশ": 19,
    "১৯": 19,
    "বিংশ": 20,
    "২০": 20,
}

AUTHOR_MARKERS = {
    "রবীন্দ্রনাথ ঠাকুর": {"রবীন্দ্রনাথ", "গল্পগুচ্ছ", "শিশু ভোলানাথ", "পলাতকা"},
    "শরৎচন্দ্র চট্টোপাধ্যায়": {"শরৎ", "শরৎ-সাহিত্য"},
    "বঙ্কিমচন্দ্র চট্টোপাধ্যায়": {"বঙ্কিম", "কমলাকান্ত"},
    "বিভূতিভূষণ বন্দ্যোপাধ্যায়": {"বিভূতিভূষণ"},
}

SKIP_SUBPAGE_MARKERS = {
    "পাঠভেদ",
    "টীকা",
    "টীকাটিপ্পনী",
    "সূচীপত্র",
    "নির্ঘণ্ট",
    "প্রচ্ছদ",
    "চিত্র",
    "বিজ্ঞাপন",
}

SOURCE_BOILERPLATE_RE = re.compile(
    r"(উইকিসংকলন|Wikisource|Creative Commons|CC BY|পাবলিক ডোমেইন|"
    r"এই পাতাটির মুদ্রণ সংশোধন|প্রাপ্তিস্থান|স্ক্যান|সূচীপত্র)",
    re.IGNORECASE,
)

DISAMBIGUATION_RE = re.compile(r"(একই নামের|নিম্নলিখিত|দ্ব্যর্থতা|disambiguation)", re.IGNORECASE)


@dataclass
class Candidate:
    root_title: str
    provenances: set[str] = field(default_factory=set)


@dataclass
class PreparedCandidate:
    root_title: str
    source_url: str
    prepared_text: str
    chapter_titles: list[str]
    word_count: int
    score: float
    reasons: list[str]


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


def normalize_key(value: str) -> str:
    value = unicodedata.normalize("NFC", value or "")
    value = value.replace("_", " ")
    value = re.sub(r"\([^)]*অংশ[^)]*\)", "", value)
    value = re.sub(r"[।,;:!?\-–—\"'‘’“”\[\]{}]", "", value)
    value = re.sub(r"\s+", "", value)
    return value.casefold()


def title_base(title: str) -> str:
    return re.sub(r"\s*\([^)]*অংশ[^)]*\)\s*$", "", title or "").strip()


def source_url_for(page_title: str) -> str:
    return "https://bn.wikisource.org/wiki/" + quote(page_title.replace(" ", "_"), safe="/:()_,")


def page_title_from_url(value: str) -> str:
    markdown = re.match(r"^\[[^\]]+\]\((https?://.+)\)$", (value or "").strip())
    if markdown:
        value = markdown.group(1)
    parsed = urlparse(value or "")
    if not parsed.netloc:
        return ""
    title = unquote(parsed.path.removeprefix("/wiki/"))
    return title.replace("_", " ").strip()


def is_year_parenthetical(text: str) -> bool:
    inner = text.strip().strip("()").translate(BENGALI_DIGITS)
    return bool(re.fullmatch(r"\d{3,4}", inner))


def segment_matches_title(segment: str, base: str) -> bool:
    segment = segment.strip()
    base_key = normalize_key(base)
    if normalize_key(segment) == base_key:
        return True
    if segment.startswith(base) and re.search(r"\([^)]*\)$", segment):
        return normalize_key(re.sub(r"\s*\([^)]*\)\s*$", "", segment)) == base_key
    return False


def root_for_candidate(page_title: str, base: str) -> str:
    if not page_title or ":" in page_title.split("/", 1)[0]:
        return ""
    parts = [part.strip() for part in page_title.split("/") if part.strip()]
    if not parts:
        return ""
    for index, part in enumerate(parts[1:], start=1):
        if normalize_key(part) == normalize_key(base):
            return "/".join(parts[: index + 1])
    if segment_matches_title(parts[0], base):
        return parts[0]
    for index, part in enumerate(parts[1:], start=1):
        if segment_matches_title(part, base):
            return "/".join(parts[: index + 1])
    return ""


def has_expected_author_signal(root: str, book: dict[str, Any], provenance: str) -> bool:
    author = str(book.get("author") or "")
    markers = AUTHOR_MARKERS.get(author, set())
    if any(marker in root for marker in markers):
        return True
    if provenance.startswith("rachana"):
        return True
    first = root.split("/", 1)[0]
    parentheticals = re.findall(r"\([^)]*\)", first)
    if not parentheticals:
        # A generic collection path such as "কাহিনী/সতী" may be a perfectly
        # valid page, but it is not author-specific enough for an automated
        # commercial upload.
        return False
    for parenthetical in parentheticals:
        if is_year_parenthetical(parenthetical):
            continue
        if any(marker in parenthetical for marker in markers):
            return True
        return False
    return True


def api_get(session: requests.Session, **params: Any) -> dict[str, Any]:
    response = session.get(WIKISOURCE_API, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def search_titles(session: requests.Session, query: str, limit: int = 30) -> list[str]:
    data = api_get(
        session,
        action="query",
        format="json",
        list="search",
        srsearch=query,
        srlimit=limit,
        srnamespace=0,
    )
    return [hit["title"] for hit in data.get("query", {}).get("search", [])]


def prefix_titles(session: requests.Session, prefix: str, limit: int = 500) -> list[str]:
    titles: list[str] = []
    params: dict[str, Any] = {
        "action": "query",
        "format": "json",
        "list": "allpages",
        "apprefix": prefix,
        "apnamespace": 0,
        "aplimit": min(limit, 500),
    }
    while True:
        data = api_get(session, **params)
        titles.extend(page["title"] for page in data.get("query", {}).get("allpages", []))
        cont = data.get("continue", {})
        if not cont or len(titles) >= limit:
            break
        params.update(cont)
    return titles[:limit]


def linked_titles(session: requests.Session, page_title: str) -> list[str]:
    if not page_title:
        return []
    data = api_get(session, action="parse", format="json", page=page_title, prop="links")
    if "error" in data:
        return []
    return [link["*"] for link in data.get("parse", {}).get("links", []) if link.get("ns") == 0 and link.get("*")]


def discover_candidates(session: requests.Session, book: dict[str, Any]) -> dict[str, Candidate]:
    base = title_base(str(book.get("title") or ""))
    author = str(book.get("author") or "")
    candidates: dict[str, Candidate] = {}

    def add(page_title: str, provenance: str) -> None:
        root = root_for_candidate(page_title, base)
        if not root:
            return
        if not has_expected_author_signal(root, book, provenance):
            return
        candidates.setdefault(root, Candidate(root)).provenances.add(provenance)

    direct = page_title_from_url(str(book.get("source_url") or ""))
    add(direct, "manifest-url")
    for linked in linked_titles(session, direct):
        add(linked, "manifest-link")
    time.sleep(0.15)

    rachana = f"রচনা:{base}"
    for linked in linked_titles(session, rachana):
        add(linked, "rachana-link")
    time.sleep(0.15)

    queries = [base, f"{base} {author}"]
    for marker in sorted(AUTHOR_MARKERS.get(author, set())):
        queries.append(f"{base} {marker}")
    for query in dict.fromkeys(queries):
        for hit in search_titles(session, query):
            add(hit, f"search:{query}")
        time.sleep(0.15)

    prefixes = {base, f"{base} (", direct}
    for prefix in [item for item in prefixes if item]:
        for title in prefix_titles(session, prefix, limit=200):
            add(title, f"prefix:{prefix}")
        time.sleep(0.15)

    # Some collection pages are not prefix-addressable by the story title.
    for root in list(candidates):
        for title in prefix_titles(session, f"{root}/", limit=500):
            add(title, f"subpage-prefix:{root}")
        time.sleep(0.15)

    return candidates


def chapter_sort_key(page_title: str, root: str) -> tuple[Any, ...]:
    suffix = page_title.removeprefix(root).strip("/")
    parts = [part for part in suffix.split("/") if part]
    key: list[Any] = []
    for part in parts:
        normalized = part.translate(BENGALI_DIGITS)
        number_match = re.search(r"\d+", normalized)
        if number_match:
            key.append(int(number_match.group(0)))
            continue
        compact = re.sub(r"\s*পরিচ্ছেদ\s*$", "", part).strip()
        key.append(BENGALI_NUMBERS.get(compact, BENGALI_NUMBERS.get(part, 999)))
        key.append(part)
    return tuple(key or [0])


def is_content_subpage(page_title: str) -> bool:
    if any(marker in page_title for marker in SKIP_SUBPAGE_MARKERS):
        return False
    return True


def strip_reader_boilerplate(text: str, markers: list[str]) -> str:
    lines = [re.sub(r"[ \t\xa0]+", " ", line).strip() for line in text.splitlines()]
    marker_keys = {normalize_key(marker) for marker in markers if marker}
    cleaned: list[str] = []
    for index, line in enumerate(lines):
        if not line:
            cleaned.append("")
            continue
        line_key = normalize_key(line)
        if index < 25 and line_key in marker_keys:
            continue
        if SOURCE_BOILERPLATE_RE.search(line):
            continue
        cleaned.append(line)
    value = "\n".join(cleaned)
    value = re.sub(r"\n{3,}", "\n\n", value).strip()
    return value


def fetch_clean_text(importer: Any, page_title: str, book: dict[str, Any]) -> tuple[str, int]:
    url = source_url_for(page_title)
    body, _log = importer.download_source(url, "wikisource_bengali_html")
    raw = importer.decode_utf8(body)
    text, _warnings = importer.sanitize_text(raw, {**book, "source_url": url, "source_type": "wikisource_bengali_html"})
    markers = [
        str(book.get("title") or ""),
        title_base(str(book.get("title") or "")),
        str(book.get("author") or ""),
        *[part for part in page_title.split("/") if part],
    ]
    text = strip_reader_boilerplate(text, markers)
    return text, len(importer.words(text))


def prepare_candidate(
    importer: Any,
    session: requests.Session,
    book: dict[str, Any],
    candidate: Candidate,
) -> PreparedCandidate | None:
    root = candidate.root_title
    subpages = [
        title
        for title in prefix_titles(session, f"{root}/", limit=500)
        if title != root and is_content_subpage(title)
    ]
    subpages = sorted(dict.fromkeys(subpages), key=lambda item: chapter_sort_key(item, root))

    chunks: list[str] = []
    chapter_titles: list[str] = []
    reasons = sorted(candidate.provenances)

    if subpages:
        for index, page_title in enumerate(subpages, start=1):
            text, words = fetch_clean_text(importer, page_title, book)
            if words < 20:
                continue
            display = page_title.removeprefix(root).strip("/").replace("/", " / ")
            chapter_titles.append(display)
            chunks.append(f"Chapter {index}. {display}\n\n{text}")
            time.sleep(0.1)
        prepared = "\n\n".join(chunks).strip()
    else:
        prepared, words = fetch_clean_text(importer, root, book)
        if DISAMBIGUATION_RE.search(prepared) and words < 900:
            return None
        chapter_titles = [title_base(str(book.get("title") or ""))]

    word_count = len(importer.words(prepared))
    if word_count < 500:
        return None
    if SOURCE_BOILERPLATE_RE.search(prepared):
        return None

    source_url = source_url_for(root)
    author = str(book.get("author") or "")
    markers = AUTHOR_MARKERS.get(author, set())
    score = math.log(max(word_count, 1), 10) * 10
    if subpages:
        score += 25
    if any(prov.startswith("rachana") for prov in candidate.provenances):
        score += 30
    if any(marker in root for marker in markers):
        score += 15
    if root.split("/", 1)[0].startswith(title_base(str(book.get("title") or ""))):
        score += 10
    years = [int(match.translate(BENGALI_DIGITS)) for match in re.findall(r"[০-৯\d]{3,4}", root)]
    if years:
        earliest = min(years)
        if earliest <= datetime.now(timezone.utc).year - 96:
            score += 15
        else:
            score -= 25
    return PreparedCandidate(root, source_url, prepared, chapter_titles, word_count, score, reasons)


def category_for(book: dict[str, Any]) -> str:
    title = str(book.get("title") or "")
    genre = str(book.get("genre") or "").casefold()
    if any(term in genre for term in ["children", "child"]) or title in {"ইচ্ছাপূরণ", "তোতা কাহিনী"}:
        return "young-readers"
    if any(term in genre for term in ["historical", "nationalism", "political", "rebellion"]):
        return "history-strategy"
    if any(term in genre for term in ["adventure", "female power"]):
        return "adventure"
    if any(term in genre for term in ["gothic", "ghost", "mystery", "psychological"]):
        return "gothic-fiction"
    return "literary-fiction"


def build_upload_book(importer: Any, raw: dict[str, Any], prepared: PreparedCandidate, text_path: Path) -> dict[str, Any]:
    book = dict(raw)
    book["source_url"] = prepared.source_url
    book["source_type"] = "wikisource_bengali_html"
    book["source_license"] = (
        "Underlying Bengali literary text is public domain in India and the U.S.; "
        "Bengali Wikisource transcription/source layer is reused under CC BY-SA terms."
    )
    book["rights_basis"] = (
        f"Author died {book.get('author_death_year')}. "
        f"Published {book.get('original_publication_year')}. "
        "Public domain checks are enforced by the Earnalism import pipeline; "
        "source evidence kept internal/admin-only."
    )
    book["commercial_use_allowed"] = True
    book["audio_allowed"] = True
    book["requires_attribution"] = True
    book["requires_sharealike"] = True
    book["required_attribution"] = (
        "Source transcription from Bengali Wikisource, reused under CC BY-SA terms. "
        "Original literary text is public domain."
    )
    book["category_slug"] = category_for(book)
    manifest_id = str(book.get("id") or "").strip().lower()
    book["slug"] = manifest_id if manifest_id.startswith("bn-") else f"bn-{manifest_id}"
    book["prepared_text_path"] = str(text_path)
    book["is_published"] = False
    book["availability"] = "draft"
    chapter_rules = book.get("chapter_rules") if isinstance(book.get("chapter_rules"), dict) else {}
    if len(prepared.chapter_titles) > 1:
        chapter_rules["strict_prepared_chapter_markers"] = True
    else:
        chapter_rules["force_single_chapter"] = True
    book["chapter_rules"] = chapter_rules
    book["minimum_word_count"] = max(500, int(prepared.word_count * 0.75))
    book["import_notes"] = [
        f"Deep-repaired from held manifest row {book.get('id')}.",
        "Prepared without rewriting story text; source/index/license boilerplate stripped from reader text.",
        f"Selected Wikisource root: {prepared.root_title}.",
    ]
    return book


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--dry-run-report", type=Path, default=DEFAULT_DRY_RUN_REPORT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    importer = load_module(ROOT / "scripts/import_books.py", "earnalism_import_books")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    raw_books = manifest.get("books", manifest) if isinstance(manifest, dict) else manifest
    raw_by_title_author = {
        (str(book.get("title") or ""), str(book.get("author") or "")): book
        for book in raw_books
        if isinstance(book, dict)
    }
    dry_report = json.loads(args.dry_run_report.read_text(encoding="utf-8"))
    targets = []
    for item in dry_report.get("skipped_books", []):
        raw = raw_by_title_author.get((str(item.get("title") or ""), str(item.get("author") or "")))
        if raw:
            targets.append(raw)
    if args.limit:
        targets = targets[: args.limit]

    out_dir = args.output_dir / utc_stamp()
    text_dir = out_dir / "prepared_texts"
    text_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    selected: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []

    for index, raw in enumerate(targets, start=1):
        manifest_id = str(raw.get("id") or "")
        title = str(raw.get("title") or "")
        print(f"[{index}/{len(targets)}] probing {manifest_id} {title}", flush=True)
        try:
            candidates = discover_candidates(session, raw)
            prepared_options: list[PreparedCandidate] = []
            for candidate in candidates.values():
                try:
                    prepared = prepare_candidate(importer, session, raw, candidate)
                    if prepared:
                        prepared_options.append(prepared)
                except Exception as exc:  # noqa: BLE001 - candidate-level rejection
                    decisions.append({
                        "manifest_id": manifest_id,
                        "title": title,
                        "author": raw.get("author"),
                        "status": "candidate_rejected",
                        "candidate": candidate.root_title,
                        "reason": str(exc),
                    })
                time.sleep(0.15)

            if not prepared_options:
                decisions.append({
                    "manifest_id": manifest_id,
                    "title": title,
                    "author": raw.get("author"),
                    "status": "skipped",
                    "reason": "no clean high-confidence main-namespace Wikisource candidate passed text validation",
                    "candidate_count": len(candidates),
                })
                print(f"  skipped: no clean candidate ({len(candidates)} candidates)", flush=True)
                continue

            best = sorted(prepared_options, key=lambda item: item.score, reverse=True)[0]
            text_path = text_dir / f"{manifest_id.lower()}-{importer.slugify(title, fallback='bengali')}.txt"
            text_path.write_text(best.prepared_text, encoding="utf-8")
            upload_book = build_upload_book(importer, raw, best, text_path)
            selected.append(upload_book)
            decisions.append({
                "manifest_id": manifest_id,
                "title": title,
                "author": raw.get("author"),
                "status": "selected",
                "slug": upload_book["slug"],
                "source_url": best.source_url,
                "root_title": best.root_title,
                "word_count": best.word_count,
                "chapter_count": len(best.chapter_titles),
                "category_slug": upload_book["category_slug"],
                "score": round(best.score, 3),
                "provenance": best.reasons,
            })
            print(f"  selected {best.root_title} ({best.word_count} words, {len(best.chapter_titles)} chapters)", flush=True)
        except Exception as exc:  # noqa: BLE001 - keep batch moving
            decisions.append({
                "manifest_id": manifest_id,
                "title": title,
                "author": raw.get("author"),
                "status": "skipped",
                "reason": str(exc),
            })
            print(f"  skipped: {exc}", flush=True)

    manifest_path = out_dir / "bengali_wikisource_deep_repair_manifest.json"
    report_path = out_dir / "bengali_wikisource_deep_repair_report.json"
    manifest_path.write_text(json.dumps({"all_or_nothing": False, "books": selected}, ensure_ascii=False, indent=2), encoding="utf-8")
    report = {
        "generated_at": now_iso(),
        "source_manifest": str(args.manifest),
        "dry_run_report": str(args.dry_run_report),
        "target_count": len(targets),
        "selected_count": len(selected),
        "skipped_count": len([item for item in decisions if item.get("status") == "skipped"]),
        "candidate_rejected_count": len([item for item in decisions if item.get("status") == "candidate_rejected"]),
        "category_distribution": dict(Counter(book.get("category_slug", "") for book in selected)),
        "decisions": decisions,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nmanifest {manifest_path}", flush=True)
    print(f"report {report_path}", flush=True)
    print(f"selected {report['selected_count']}; skipped {report['skipped_count']}", flush=True)
    return 0 if selected else 1


if __name__ == "__main__":
    raise SystemExit(main())
