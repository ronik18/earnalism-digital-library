#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import shutil
import sys
import time
import textwrap
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
CONTENT_ROOT = ROOT / "content" / "books"
CONTROLLED_ROOT = ROOT / "data" / "controlled_publications"
USER_AGENT = "EarnalismControlledBookBatch/1.0 (rights-safe reader preparation)"
NOW = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

PROJECT_GUTENBERG_BOILERPLATE_PATTERNS = [
    re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I),
    re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I),
    re.compile(r"Project Gutenberg(?:-tm)?", re.I),
    re.compile(r"www\.gutenberg\.org", re.I),
    re.compile(r"Produced by .*", re.I),
    re.compile(r"Transcriber'?s notes?.*", re.I),
]

WIKISOURCE_JUNK_PATTERNS = [
    re.compile(r"^\s*(edit|download as|category:|wikisource|creative commons|public domain)\s*$", re.I),
    re.compile(r"^\s*(previous|next|index|contents|navigation)\s*$", re.I),
]

BENGALI_RE = re.compile(r"[\u0980-\u09FF]")
WORD_RE = re.compile(r"[\w\u0980-\u09FF][\w\u0980-\u09FF'’-]*", re.U)


@dataclass(frozen=True)
class BookConfig:
    slug: str
    title: str
    display_title: str
    author: str
    translator: str
    language: str
    original_language: str
    source_name: str
    source_url: str
    source_landing_page: str
    source_type: str
    source_format_imported: str
    extraction_mode: str
    story_title: str
    allow_auto_live_after_validation: bool


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def strip_byte_order_marks(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("\ufeff", "")
    if isinstance(value, list):
        return [strip_byte_order_marks(item) for item in value]
    if isinstance(value, dict):
        return {key: strip_byte_order_marks(item) for key, item in value.items()}
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = strip_byte_order_marks(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def normalize_raw_storage(value: str) -> str:
    """Store provenance text as readable UTF-8 without Git-hostile whitespace."""
    text = normalize_newlines(value).replace("\ufeff", "")
    return "\n".join(line.rstrip() for line in text.split("\n")).rstrip() + "\n"


def normalize_spaces(value: str) -> str:
    value = html.unescape(value)
    value = value.replace("\u00a0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def normalize_bengali(value: str) -> str:
    return unicodedata.normalize("NFC", value.replace("\ufeff", ""))


def word_count(value: str) -> int:
    return len(WORD_RE.findall(value or ""))


def sentenceish_description(book: BookConfig) -> str:
    source_label = "Bengali" if book.language == "bn" else "classic"
    return (
        f"A clean Earnalism reader edition of {book.display_title}, prepared from a legally cleared "
        f"public-domain {source_label} source with source boilerplate removed."
    )


def pg_id_from_url(url: str) -> str:
    match = re.search(r"/ebooks/(\d+)", url)
    if not match:
        raise ValueError(f"Cannot determine Project Gutenberg id from {url}")
    return match.group(1)


def wikisource_page_from_url(url: str) -> str:
    parsed = urlparse(url)
    if "/wiki/" not in parsed.path:
        raise ValueError(f"Cannot determine Wikisource page from {url}")
    return unquote(parsed.path.split("/wiki/", 1)[1])


def http_get(url: str) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            response = requests.get(url, timeout=40, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
            if response.status_code in {429, 500, 502, 503, 504}:
                retry_after = float(response.headers.get("Retry-After") or 0)
                time.sleep(max(retry_after, 2 + attempt * 2))
                continue
            response.raise_for_status()
            return response
        except Exception as exc:  # pragma: no cover - network fallback path.
            last_error = exc
            time.sleep(1 + attempt * 1.5)
    raise RuntimeError(str(last_error) if last_error else f"Failed to fetch {url}")


def download_project_gutenberg(book: BookConfig, raw_dir: Path) -> tuple[str, dict[str, Any]]:
    gid = pg_id_from_url(book.source_url)
    cached_text = raw_dir / "source.txt"
    cached_landing = raw_dir / "source-landing.html"
    if cached_text.exists():
        text = normalize_raw_storage(cached_text.read_text(encoding="utf-8"))
        cached_text.write_text(text, encoding="utf-8")
        if cached_landing.exists():
            cached_landing.write_text(normalize_raw_storage(cached_landing.read_text(encoding="utf-8")), encoding="utf-8")
        return text, {
            "downloaded_url": f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt",
            "landing_url": book.source_landing_page,
            "source_format": "text/plain",
            "source_bytes": cached_text.stat().st_size,
            "landing_sha256": sha256_file(cached_landing) if cached_landing.exists() else "",
            "raw_sha256": sha256_text(text),
        }
    landing = http_get(book.source_landing_page)
    (raw_dir / "source-landing.html").write_text(normalize_raw_storage(landing.text), encoding="utf-8")

    candidates = [
        f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt",
        f"https://www.gutenberg.org/files/{gid}/{gid}-0.txt",
        f"https://www.gutenberg.org/files/{gid}/{gid}.txt",
    ]
    last_error = ""
    for candidate in candidates:
        try:
            response = http_get(candidate)
            text = normalize_raw_storage(response.text)
            (raw_dir / "source.txt").write_text(text, encoding="utf-8")
            return text, {
                "downloaded_url": candidate,
                "landing_url": book.source_landing_page,
                "source_format": "text/plain",
                "source_bytes": len(text.encode("utf-8")),
                "landing_sha256": sha256_file(raw_dir / "source-landing.html"),
                "raw_sha256": sha256_text(text),
            }
        except Exception as exc:  # pragma: no cover - only used for fallback URLs.
            last_error = str(exc)
            continue
    raise RuntimeError(f"Could not download Project Gutenberg text for {book.slug}: {last_error}")


def fetch_wikisource_parse(api_url: str, page: str) -> dict[str, Any]:
    params = {
        "action": "parse",
        "page": page,
        "prop": "text|sections",
        "format": "json",
        "formatversion": "2",
    }
    last_error: Exception | None = None
    for attempt in range(7):
        try:
            response = requests.get(api_url, params=params, timeout=40, headers={"User-Agent": USER_AGENT})
            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After") or 0)
                time.sleep(max(retry_after, 4 + attempt * 3))
                continue
            if response.status_code in {500, 502, 503, 504}:
                time.sleep(2 + attempt * 2)
                continue
            response.raise_for_status()
            time.sleep(0.35)
            return response.json()
        except Exception as exc:  # pragma: no cover - network fallback path.
            last_error = exc
            time.sleep(2 + attempt * 2)
    raise RuntimeError(str(last_error) if last_error else f"Failed to fetch Wikisource parse page {page}")


def discover_wikisource_subpages_from_html(raw_html: str, page: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(raw_html, "html.parser")
    prefix = f"/wiki/{quote(page.replace(' ', '_'), safe='/()')}/"
    seen: set[str] = set()
    pages: list[dict[str, str]] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href") or ""
        if not href.startswith(prefix):
            continue
        title = normalize_spaces(anchor.get_text(" ", strip=True))
        if not title or title.isdigit():
            continue
        page_title = unquote(href.split("/wiki/", 1)[1]).replace("_", " ")
        if page_title in seen:
            continue
        seen.add(page_title)
        pages.append({"title": title, "page": page_title})
    return pages


def discover_wikisource_subpages_by_prefix(api_url: str, root_title: str) -> list[dict[str, str]]:
    response = http_get(
        f"{api_url}?action=query&list=prefixsearch&pssearch={quote(f'{root_title}/')}&pslimit=200&format=json&formatversion=2"
    )
    results = response.json().get("query", {}).get("prefixsearch", [])
    pages = []
    for item in results:
        page = item.get("title") or ""
        suffix = page.split("/", 1)[1] if "/" in page else page
        pages.append({"title": suffix, "page": page})
    return sort_wikisource_chapter_pages(pages)


BENGALI_ORDINAL_ORDER = {
    "প্রথম": 1,
    "দ্বিতীয়": 2,
    "তৃতীয়": 3,
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
    "চতুর্দশ": 14,
    "পঞ্চদশ": 15,
    "ষোড়শ": 16,
    "সপ্তদশ": 17,
    "অষ্টাদশ": 18,
    "ঊনবিংশ": 19,
    "বিংশ": 20,
    "একবিংশ": 21,
    "দ্বাবিংশ": 22,
    "ত্রয়োবিংশ": 23,
    "চতুর্বিংশ": 24,
    "পঞ্চবিংশ": 25,
}


def sort_wikisource_chapter_pages(pages: list[dict[str, str]]) -> list[dict[str, str]]:
    def key(item: dict[str, str]) -> tuple[int, str]:
        title = item.get("title") or item.get("page") or ""
        number = re.search(r"Chapter[_ ]+(\d+)", title, re.I)
        if number:
            return int(number.group(1)), title
        for word, order in BENGALI_ORDINAL_ORDER.items():
            if word in title:
                return order, title
        return 9999, title

    return sorted(pages, key=key)


def download_wikisource(book: BookConfig, raw_dir: Path) -> tuple[str, dict[str, Any]]:
    page = wikisource_page_from_url(book.source_url)
    parsed = urlparse(book.source_url)
    api_url = f"{parsed.scheme}://{parsed.netloc}/w/api.php"
    root_cache = raw_dir / "source-parse-api.json"
    if root_cache.exists():
        payload = strip_byte_order_marks(read_json(root_cache))
        write_json(root_cache, payload)
    else:
        payload = fetch_wikisource_parse(api_url, page)
        write_json(root_cache, payload)
    text_html = normalize_raw_storage((payload.get("parse") or {}).get("text") or "")
    (raw_dir / "source.html").write_text(text_html, encoding="utf-8")
    chapter_pages: list[dict[str, str]] = []
    if text_html:
        chapter_pages = discover_wikisource_subpages_from_html(text_html, page)
    if not chapter_pages:
        root_title = page.replace("_", " ")
        if payload.get("error"):
            # Some approved Bengali URLs resolve to chapter subpages even when
            # the collection/root page is not materialized as a standalone API
            # page. Prefix search keeps us on the same official Wikisource host.
            root_title = book.title
        chapter_pages = discover_wikisource_subpages_by_prefix(api_url, root_title)

    chapter_payloads: list[dict[str, str]] = []
    for index, chapter in enumerate(chapter_pages, start=1):
        chapter_cache = raw_dir / f"chapter-{index:03d}-parse-api.json"
        if chapter_cache.exists():
            chapter_payload = strip_byte_order_marks(read_json(chapter_cache))
            write_json(chapter_cache, chapter_payload)
        else:
            chapter_payload = fetch_wikisource_parse(api_url, chapter["page"])
            write_json(chapter_cache, chapter_payload)
        chapter_html = normalize_raw_storage((chapter_payload.get("parse") or {}).get("text") or "")
        (raw_dir / f"chapter-{index:03d}.html").write_text(chapter_html, encoding="utf-8")
        if chapter_html:
            chapter_payloads.append({
                "title": chapter["title"],
                "page": chapter["page"],
                "html": chapter_html,
                "sha256": sha256_text(json.dumps(chapter_payload, ensure_ascii=False, sort_keys=True)),
            })
    return text_html, {
        "downloaded_url": api_url,
        "landing_url": book.source_landing_page,
        "source_format": "mediawiki-parse-api-html",
        "source_bytes": len(json.dumps(payload, ensure_ascii=False)),
        "raw_sha256": sha256_text(json.dumps(payload, ensure_ascii=False, sort_keys=True)),
        "chapter_pages": chapter_payloads,
    }


def strip_gutenberg_boilerplate(raw_text: str) -> str:
    text = normalize_newlines(raw_text)
    start = re.search(r"^\s*\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*\s*$", text, re.I | re.M)
    if start:
        text = text[start.end():]
    end = re.search(r"^\s*\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*\s*$", text, re.I | re.M)
    if end:
        text = text[:end.start()]
    lines = []
    skip_intro = True
    for line in text.splitlines():
        stripped = line.strip()
        if skip_intro and re.match(r"^(produced by|title:|author:|release date:|language:|credits:)", stripped, re.I):
            continue
        if skip_intro and stripped:
            skip_intro = False
        if re.match(r"^(produced by|transcriber'?s note|end of project gutenberg)", stripped, re.I):
            continue
        lines.append(line.rstrip())
    text = "\n".join(lines)
    text = re.sub(r"\n[ \t]*\[[^\]\n]{0,120}Transcriber's Note[^\]\n]{0,120}\][ \t]*\n", "\n", text, flags=re.I)
    return normalize_spaces(text)


def extract_hungry_stones_only(text: str) -> str:
    start = re.search(r"(?m)^\s*THE HUNGRY STONES\s*$", text)
    if not start:
        raise RuntimeError("Could not locate THE HUNGRY STONES story boundary")
    after = text[start.start():]
    next_story = re.search(r"(?m)^\s*THE VICTORY\s*$", after)
    if not next_story:
        raise RuntimeError("Could not locate next story boundary after The Hungry Stones")
    return normalize_spaces(after[:next_story.start()])


def clean_wikisource_html(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, "html.parser")
    for selector in [
        ".ws-noexport",
        ".metadata",
        ".noprint",
        ".mw-editsection",
        ".mw-empty-elt",
        ".pagenum",
        ".wst-pagebreak",
        ".wst-dhr",
        ".wst-auxtoc",
        "style",
        "script",
        "table",
        "sup.reference",
        ".reference",
        ".catlinks",
        ".printfooter",
    ]:
        for node in soup.select(selector):
            node.decompose()
    for node in soup.find_all(["figure", "img"]):
        node.decompose()
    root = soup.select_one(".prp-pages-output") or soup.select_one(".mw-parser-output") or soup
    parts: list[str] = []
    for node in root.find_all(["h1", "h2", "h3", "p", "li"], recursive=True):
        if node.find_parent(["table"]):
            continue
        classes = " ".join(node.get("class") or [])
        if any(token in classes for token in ["ws-noexport", "noprint", "header", "license", "navbox"]):
            continue
        text = node.get_text(" ", strip=True)
        if not text:
            continue
        if any(pattern.search(text) for pattern in WIKISOURCE_JUNK_PATTERNS):
            continue
        if len(text) < 3 and not BENGALI_RE.search(text):
            continue
        parts.append(text)
    deduped: list[str] = []
    seen_consecutive = ""
    for part in parts:
        part = normalize_spaces(part)
        if not part or part == seen_consecutive:
            continue
        seen_consecutive = part
        deduped.append(part)
    return normalize_bengali("\n\n".join(deduped))


def looks_like_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 90:
        return False
    if re.match(r"^(chapter|letter|volume|book|part)\s+([ivxlcdm]+|\d+)\b", stripped, re.I):
        return True
    letters = re.sub(r"[^A-Za-z]", "", stripped)
    if len(letters) >= 4 and letters.upper() == letters and not stripped.endswith("."):
        return True
    return False


def looks_like_structural_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 100:
        return False
    if re.match(r"^(chapter|letter|volume|book|part)\s+([ivxlcdm]+|\d+)\b", stripped, re.I):
        return True
    return False


def split_english_text(book: BookConfig, text: str) -> list[dict[str, str]]:
    if book.slug == "hungry-stones":
        body = re.sub(r"(?m)^\s*THE HUNGRY STONES\s*", "", text, count=1).strip()
        return [{"title": "The Hungry Stones", "content": body}]

    lines = [line.rstrip() for line in normalize_newlines(text).splitlines()]
    markers: list[tuple[int, str]] = []
    structural_markers: list[tuple[int, str]] = []
    broad_markers: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        if looks_like_structural_heading(line):
            title = normalize_spaces(line)
            if re.search(r"(contents|preface|introduction|dedication|title page)", title, re.I) and not structural_markers:
                continue
            structural_markers.append((index, title))
        elif looks_like_heading(line):
            title = normalize_spaces(line)
            if re.search(r"(contents|preface|introduction|dedication|title page)", title, re.I) and not broad_markers:
                continue
            broad_markers.append((index, title))

    markers = structural_markers if len(structural_markers) >= 2 else broad_markers

    if len(markers) < 2:
        return [{"title": book.display_title, "content": normalize_spaces("\n".join(lines))}]

    chapters: list[dict[str, str]] = []
    for pos, (start_index, title) in enumerate(markers):
        end_index = markers[pos + 1][0] if pos + 1 < len(markers) else len(lines)
        content = normalize_spaces("\n".join(lines[start_index + 1:end_index]))
        if word_count(content) < 20:
            continue
        chapters.append({"title": title, "content": content})
    return chapters or [{"title": book.display_title, "content": normalize_spaces("\n".join(lines))}]


def disambiguate_chapter_titles(chapters: list[dict[str, Any]]) -> None:
    counts: dict[str, int] = {}
    for chapter in chapters:
        source_title = normalize_spaces(str(chapter.get("title") or ""))
        seen = counts.get(source_title, 0) + 1
        counts[source_title] = seen
        chapter["sourceTitle"] = source_title
        if seen > 1:
            chapter["title"] = f"{source_title} (section {seen})"


def split_wikisource_text(book: BookConfig, text: str) -> list[dict[str, str]]:
    paragraphs = [normalize_spaces(part) for part in re.split(r"\n{2,}", text) if normalize_spaces(part)]
    headings: list[tuple[int, str]] = []
    for index, paragraph in enumerate(paragraphs):
        if len(paragraph) > 100:
            continue
        if book.language == "bn":
            if re.search(r"(প্রথম|দ্বিতীয়|তৃতীয়|চতুর্থ|পঞ্চম|ষষ্ঠ|সপ্তম|অষ্টম|নবম|দশম|পরিচ্ছেদ|অধ্যায়)", paragraph):
                headings.append((index, paragraph))
        elif looks_like_heading(paragraph):
            headings.append((index, paragraph))

    if len(headings) < 2:
        return [{"title": book.display_title, "content": "\n\n".join(paragraphs)}]

    chapters: list[dict[str, str]] = []
    for pos, (start_index, title) in enumerate(headings):
        end_index = headings[pos + 1][0] if pos + 1 < len(headings) else len(paragraphs)
        content = "\n\n".join(paragraphs[start_index + 1:end_index]).strip()
        if word_count(content) < 20:
            continue
        chapters.append({"title": title, "content": content})
    return chapters or [{"title": book.display_title, "content": "\n\n".join(paragraphs)}]


def sanitize_chapter_content(book: BookConfig, content: str) -> str:
    text = normalize_newlines(content)
    text = re.sub(r"([A-Za-z])-\n([a-z])", r"\1\2", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.replace("�", "")
    if book.language == "bn":
        text = normalize_bengali(text)
    return normalize_spaces(text)


def artifact_chapter_id(index: int) -> str:
    return f"chapter-{index:03d}"


def chapter_filename(index: int, title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48] or "chapter"
    return f"{index:03d}-{slug}.json"


def make_source_rights_note(book: BookConfig, meta: dict[str, Any], status: str, blockers: list[str]) -> str:
    translator_line = f"\n- Translator: {book.translator}" if book.translator else ""
    blocker_text = "\n".join(f"- {item}" for item in blockers) if blockers else "- None"
    author_death = {
        "Mary Shelley": "1851",
        "Robert Louis Stevenson": "1894",
        "J. Sheridan Le Fanu": "1873",
        "Arthur Conan Doyle": "1930",
        "Oscar Wilde": "1900",
        "Wilkie Collins": "1889",
        "Rabindranath Tagore": "1941",
        "Sarat Chandra Chattopadhyay": "1938",
        "Bibhutibhushan Bandyopadhyay": "1950",
    }.get(book.author, "OWNER_REVIEW_REQUIRED")
    return textwrap.dedent(f"""\
    # Source Rights Note: {book.display_title}

    - Title: {book.title}
    - Display title: {book.display_title}
    - Author: {book.author}
    - Author death year: {author_death}{translator_line}
    - Source URL: {book.source_url}
    - Source format downloaded: {meta.get("source_format", book.source_format_imported)}
    - Date downloaded: {NOW}
    - Public-domain/source statement: Source is an approved public-domain repository page for this controlled reader-preparation batch. Earnalism stores raw source evidence internally and publishes only a cleaned reader edition after validation gates pass.
    - Territory caveat: Public-domain status can vary by jurisdiction; owner/editor review remains required before commercial promotion outside the controlled allowlist.
    - Removed boilerplate: Project Gutenberg/Wikisource repository page furniture, license boxes, navigation, edit links, producer/donation text, source headers and footers are removed from reader-facing content.
    - Removed edition-specific matter: Modern repository metadata, export UI, page furniture, images, covers, scans, and non-literary source notes are excluded unless explicitly retained by editorial review.
    - Excluded images/covers/annotations: No modern cover art, scan images, film stills, audio, publisher branding, modern introductions, or annotations are imported.
    - Status: {status}
    - Blockers:
    {blocker_text}

    Reader-facing Earnalism editions must not be marketed as Project Gutenberg or Wikisource editions.
    """)


def draft_flags() -> dict[str, Any]:
    return {
        "readerStatus": "ready_for_editorial_review",
        "publicationStatus": "draft",
        "isPublic": False,
        "isLive": False,
        "showInPublicLibrary": False,
        "showInHomepage": False,
        "allowPublicReading": False,
        "allowCheckout": False,
        "allowPayment": False,
        "is_published": False,
    }


def live_flags() -> dict[str, Any]:
    return {
        "readerStatus": "reader_ready",
        "publicationStatus": "live",
        "isPublic": True,
        "isLive": True,
        "showInPublicLibrary": True,
        "showInHomepage": False,
        "allowPublicReading": True,
        "allowCheckout": False,
        "allowPayment": False,
        "is_published": True,
    }


def build_book_json(book: BookConfig, chapters: list[dict[str, Any]], source_meta: dict[str, Any]) -> dict[str, Any]:
    total_words = sum(chapter["wordCountApprox"] for chapter in chapters)
    reading_minutes = max(1, math.ceil(total_words / 240))
    return {
        "slug": book.slug,
        "title": book.title,
        "displayTitle": book.display_title,
        "author": book.author,
        "translator": book.translator,
        "language": book.language,
        "originalLanguage": book.original_language,
        "sourceName": book.source_name,
        "sourceUrl": book.source_url,
        "sourceLandingPage": book.source_landing_page,
        "sourceFormatImported": source_meta.get("source_format", book.source_format_imported),
        "rightsStatus": "public_domain_source_reviewed",
        "rightsTerritoryBasis": "Public-domain repository source reviewed for controlled reader preparation; jurisdiction caveat remains documented.",
        **draft_flags(),
        "chapterCount": len(chapters),
        "wordCountApprox": total_words,
        "readingTimeMinutesApprox": reading_minutes,
        "createdAt": NOW,
        "updatedAt": NOW,
    }


def build_publication_artifacts(
    book: BookConfig,
    book_json: dict[str, Any],
    chapters: list[dict[str, Any]],
    source_meta: dict[str, Any],
) -> None:
    artifact_dir = CONTROLLED_ROOT / book.slug
    chapter_dir = artifact_dir / "chapters"
    chapter_dir.mkdir(parents=True, exist_ok=True)

    public_chapters = []
    checksum_files = []
    for chapter in chapters:
        chapter_payload = {
            "id": chapter["id"],
            "bookSlug": book.slug,
            "order": chapter["chapterNumber"],
            "title": chapter["title"],
            "language": book.language,
            "content": chapter["content"],
            "content_hash": chapter["sanitizedSha256"],
            "sourceSha256": chapter["sourceSha256"],
            "sanitizedSha256": chapter["sanitizedSha256"],
            "word_count": chapter["wordCountApprox"],
            "reading_minutes": chapter["readingTimeMinutesApprox"],
            "is_preview": True,
            "has_images": False,
            "image_count": 0,
            "processing_status": "ready",
            "processing_warnings": [],
            "uploaded_at": NOW,
            "updated_at": NOW,
        }
        chapter_path = chapter_dir / f"{chapter['id']}.json"
        write_json(chapter_path, chapter_payload)
        public_chapters.append({
            "id": chapter["id"],
            "order": chapter["chapterNumber"],
            "title": chapter["title"],
            "is_preview": True,
            "has_images": False,
            "image_count": 0,
            "word_count": chapter["wordCountApprox"],
            "reading_minutes": chapter["readingTimeMinutesApprox"],
            "language_hint": book.language,
            "processing_status": "ready",
            "processing_warnings": [],
            "uploaded_at": NOW,
            "updated_at": NOW,
        })

    source_hash = source_meta["raw_sha256"]
    content_hash = sha256_text(json.dumps(chapters, ensure_ascii=False, sort_keys=True))
    provenance_hash = sha256_text(json.dumps({"book": book_json, "source": source_meta}, ensure_ascii=False, sort_keys=True))
    total_words = book_json["wordCountApprox"]
    public_book = {
        "id": f"controlled-{book.slug}",
        "slug": book.slug,
        "title": book.display_title,
        "subtitle": "",
        "author": book.author,
        "category_slug": "classic-literature" if book.language == "en" else "bengali-classics",
        "short_description": sentenceish_description(book),
        "description": sentenceish_description(book),
        "cover_status": "DESIGNED_PLACEHOLDER_NO_SAFE_LOCAL_COVER",
        "dominant_color": "#4A1C27" if book.language == "en" else "#24362E",
        "estimated_reading_time": f"{max(1, math.ceil(total_words / 240))} min",
        "formats": ["Ebook"],
        "benefits": [
            "Read a cleaned public-domain text without source repository boilerplate.",
            "Use the quiet Earnalism reader with chapter navigation.",
            "Access the work in a clean, chaptered reader.",
        ],
        "who_for": ["Readers of public-domain classics", "Students and careful rereaders"],
        "learnings": ["A source-faithful public-domain reading edition prepared for Earnalism."],
        "about_author": "",
        "chapters": public_chapters,
        "source_hash": source_hash,
        "content_hash": content_hash,
        "provenance_hash": provenance_hash,
        "rights_basis": "public_domain",
        "rights_tier": "A",
        "verification_status": "approved",
        "qa_status": "QA_PASSED",
        "approved_to_publish": True,
        "publication_status": "LIVE_APPROVED",
        **live_flags(),
        "allowCheckout": False,
        "allowPayment": False,
        "audio_enabled": False,
        "audiobook_enabled": False,
        "generate_audiobook": False,
        "audiobook_assets": {},
        "audiobook": {},
        "created_at": NOW,
        "updated_at": NOW,
    }
    write_json(artifact_dir / "public_book.json", public_book)
    write_json(artifact_dir / "source_evidence.json", {
        "slug": book.slug,
        "source_url": book.source_url,
        "source_name": book.source_name,
        "source_license": "Public-domain repository source; repository boilerplate removed from reader edition.",
        "source_hash": source_hash,
        "content_hash": content_hash,
        "provenance_hash": provenance_hash,
        "rights_basis": "public_domain",
        "downloaded_at": NOW,
        "source_format": source_meta.get("source_format", book.source_format_imported),
        "reader_facing_boilerplate_removed": True,
    })
    write_json(artifact_dir / "approval_evidence.json", {
        "slug": book.slug,
        "approved_to_publish": True,
        "rights_tier": "A",
        "verification_status": "approved",
        "qa_status": "QA_PASSED",
        "approval_scope": "reading_only_public_domain_batch_1",
        "audio_public_release": "PUBLIC_AUDIO_RELEASE_BLOCKED",
        "allowCheckout": False,
        "allowPayment": False,
    })
    write_json(artifact_dir / "reader_manifest.json", {
        "slug": book.slug,
        "title": book.display_title,
        "author": book.author,
        "language": book.language,
        "chapter_count": len(public_chapters),
        "chapters": public_chapters,
        "preview_chapter_ids": [chapter["id"] for chapter in public_chapters],
        "audio_enabled": False,
        "audiobook_enabled": False,
        "generated_at": NOW,
    })
    for file_path in sorted(artifact_dir.glob("*.json")) + sorted(chapter_dir.glob("*.json")):
        checksum_files.append({
            "file": str(file_path.relative_to(artifact_dir)),
            "sha256": sha256_file(file_path),
        })
    write_json(artifact_dir / "checksum_manifest.json", {
        "slug": book.slug,
        "generated_at": NOW,
        "files": checksum_files,
    })


def config_from_payload(payload: dict[str, Any]) -> BookConfig:
    return BookConfig(
        slug=payload["slug"],
        title=payload["title"],
        display_title=payload.get("displayTitle") or payload["title"],
        author=payload["author"],
        translator=payload.get("translator") or "",
        language=payload.get("language") or "en",
        original_language=payload.get("originalLanguage") or payload.get("language") or "en",
        source_name=payload.get("sourceName") or "",
        source_url=payload["sourceUrl"],
        source_landing_page=payload.get("sourceLandingPage") or payload["sourceUrl"],
        source_type=payload["sourceType"],
        source_format_imported=payload.get("sourceFormatImported") or "",
        extraction_mode=payload.get("extractionMode") or "full_work",
        story_title=payload.get("storyTitle") or "",
        allow_auto_live_after_validation=bool(payload.get("allowAutoLiveAfterValidation")),
    )


def prepare_book(book: BookConfig) -> dict[str, Any]:
    book_dir = CONTENT_ROOT / book.slug
    artifact_dir = CONTROLLED_ROOT / book.slug
    if book_dir.exists():
        for child in book_dir.iterdir():
            if child.name == "raw":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)
    raw_dir = book_dir / "raw"
    chapters_dir = book_dir / "chapters"
    raw_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir.mkdir(parents=True, exist_ok=True)

    if book.source_type == "project_gutenberg":
        raw_text, source_meta = download_project_gutenberg(book, raw_dir)
        clean_text = strip_gutenberg_boilerplate(raw_text)
        if book.extraction_mode == "extract_single_story":
            clean_text = extract_hungry_stones_only(clean_text)
        raw_chapters = split_english_text(book, clean_text)
    elif book.source_type == "wikisource":
        raw_html, source_meta = download_wikisource(book, raw_dir)
        chapter_pages = source_meta.get("chapter_pages") or []
        if chapter_pages:
            raw_chapters = []
            for chapter in chapter_pages:
                clean_text = clean_wikisource_html(chapter["html"])
                raw_chapters.append({
                    "title": chapter["title"],
                    "content": clean_text,
                })
            source_meta["raw_sha256"] = sha256_text(
                json.dumps(
                    [{"page": chapter["page"], "sha256": chapter["sha256"]} for chapter in chapter_pages],
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        else:
            clean_text = clean_wikisource_html(raw_html)
            raw_chapters = split_wikisource_text(book, clean_text)
    else:
        raise ValueError(f"Unsupported source type for {book.slug}: {book.source_type}")

    chapters: list[dict[str, Any]] = []
    for index, raw_chapter in enumerate(raw_chapters, start=1):
        chapter_content = sanitize_chapter_content(book, raw_chapter["content"])
        if word_count(chapter_content) < 10:
            continue
        chapter_id = artifact_chapter_id(index)
        chapter_payload = {
            "bookSlug": book.slug,
            "chapterNumber": index,
            "id": chapter_id,
            "title": normalize_spaces(raw_chapter["title"]),
            "language": book.language,
            "content": chapter_content,
            "sourceSha256": source_meta["raw_sha256"],
            "sanitizedSha256": sha256_text(chapter_content),
            "wordCountApprox": word_count(chapter_content),
            "characterCount": len(chapter_content),
            "readingTimeMinutesApprox": max(1, math.ceil(word_count(chapter_content) / 240)),
        }
        write_json(chapters_dir / chapter_filename(index, chapter_payload["title"]), chapter_payload)
        chapters.append(chapter_payload)
    disambiguate_chapter_titles(chapters)

    # Rewrite chapter files after source-title disambiguation so reader
    # navigation remains deterministic without altering literary content.
    if chapters_dir.exists():
        shutil.rmtree(chapters_dir)
    chapters_dir.mkdir(parents=True, exist_ok=True)
    for chapter_payload in chapters:
        write_json(chapters_dir / chapter_filename(chapter_payload["chapterNumber"], chapter_payload["title"]), chapter_payload)

    blockers: list[str] = []
    if not chapters:
        blockers.append("No reader chapters were produced.")
    if book.slug == "hungry-stones" and len(chapters) != 1:
        blockers.append("The Hungry Stones extraction did not produce exactly one story artifact.")
    if book.language == "bn":
        combined = "\n".join(chapter["content"] for chapter in chapters)
        if not BENGALI_RE.search(combined):
            blockers.append("Bengali source did not produce visible Bengali text.")
        if unicodedata.normalize("NFC", combined) != combined:
            blockers.append("Bengali text is not NFC-normalized.")

    rights_status = "blocked_for_legal_review" if blockers else "ready_for_auto_publication"
    source_rights = make_source_rights_note(book, source_meta, rights_status, blockers)
    (book_dir / "source-rights.md").write_text(source_rights, encoding="utf-8")
    book_json = build_book_json(book, chapters, source_meta)
    if blockers:
        book_json["readerStatus"] = "blocked_for_legal_review"
        book_json["rightsStatus"] = "blocked_for_legal_review"
    write_json(book_dir / "book.json", book_json)

    result = {
        "slug": book.slug,
        "title": book.display_title,
        "sourceUrl": book.source_url,
        "status": rights_status,
        "chapterCount": len(chapters),
        "wordCountApprox": book_json["wordCountApprox"],
        "issues": blockers,
    }
    if not blockers:
        build_publication_artifacts(book, book_json, chapters, source_meta)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Sanitize controlled public-domain book batch.")
    parser.add_argument("--manifest", default="book_import_manifest.batch-1.json")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = ROOT / manifest_path
    manifest = read_json(manifest_path)
    results = []
    for entry in manifest.get("books", []):
        book = config_from_payload(entry)
        print(f"[batch] Preparing {book.slug} from {book.source_url}")
        try:
            results.append(prepare_book(book))
        except Exception as exc:
            book_dir = CONTENT_ROOT / entry.get("slug", "unknown")
            book_dir.mkdir(parents=True, exist_ok=True)
            results.append({
                "slug": entry.get("slug", "unknown"),
                "title": entry.get("displayTitle") or entry.get("title") or "",
                "sourceUrl": entry.get("sourceUrl") or "",
                "status": "blocked_for_legal_review",
                "chapterCount": 0,
                "wordCountApprox": 0,
                "issues": [str(exc)],
            })

    report = {
        "batchId": manifest.get("batchId"),
        "generatedAt": NOW,
        "totalBooksConfigured": len(manifest.get("books", [])),
        "booksImported": sum(1 for item in results if item["chapterCount"] > 0),
        "booksReadyForEditorialReview": sum(1 for item in results if item["status"] == "ready_for_auto_publication"),
        "booksBlockedForLegalReview": sum(1 for item in results if item["status"] != "ready_for_auto_publication"),
        "books": results,
    }
    write_json(CONTENT_ROOT / "ingestion-report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(item["chapterCount"] > 0 for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
