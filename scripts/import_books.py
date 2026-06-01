#!/usr/bin/env python3
"""One-time legally-cleared text importer for Earnalism.

The importer intentionally defaults to dry-run. Real upload requires:
  --upload --api-url <Earnalism API URL>
and either EARNALISM_ADMIN_TOKEN or ADMIN_EMAIL + ADMIN_PASSWORD.

Manifest resolution order:
  1. CLI file path argument
  2. BOOK_IMPORT_MANIFEST env var (JSON string or file path)
  3. ./book_import_manifest.json from the current working directory
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import socket
import sys
import time
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse, urlunparse
from urllib.request import Request, urlopen


CURRENT_YEAR = datetime.now(timezone.utc).year
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "output" / "book_import"
MAX_SOURCE_BYTES = 20 * 1024 * 1024
API_TIMEOUT_SECONDS = int(os.environ.get("EARNALISM_IMPORT_API_TIMEOUT", "180"))
READING_WPM = 238
MIN_DEFAULT_WORD_COUNT = 2500
MIN_BENGALI_WIKISOURCE_WORD_COUNT = 500
MIN_CHAPTER_WORDS_WARNING = 80

DEFAULT_FORBIDDEN_TERMS = [
    "Project Gutenberg",
    "Gutenberg",
    "Project Gutenberg-tm",
    "Project Gutenberg\u2122",
    "Gutenberg.org",
    "PGLAF",
    "Distributed Proofreaders",
    "donation",
    "refund",
    "license agreement",
]
WIKISOURCE_SOURCE_TYPES = {
    "wikisource_html",
    "wikisource_bengali",
    "wikisource_bengali_html",
    "mediawiki_html",
}
GUTENBERG_SOURCE_TYPES = {
    "gutenberg",
    "gutenberg_html",
    "gutenberg_text",
    "project_gutenberg",
}
WIKISOURCE_FORBIDDEN_TERMS = [
    "Wikisource",
    "Wikimedia",
    "MediaWiki",
    "Creative Commons",
    "CC BY-SA",
    "CC-BY-SA",
    "উইকিসংকলন",
    "উইকিমিডিয়া",
]

SOURCE_BOILERPLATE_RE = re.compile(
    r"(?i)\b("
    r"project gutenberg|gutenberg\.org|pglaf|distributed proofreaders|"
    r"produced by|transcribed by|proofreading team|"
    r"donat(?:e|ion)|refund|license agreement|terms of use|"
    r"ebook|e-book|electronic work|online distributed"
    r")\b"
)

HTML_BLOCK_RE = re.compile(r"(?is)<(script|style)\b.*?</\1>")
HTML_TAG_RE = re.compile(r"(?is)<[^>]+>")
TRACKED_ARTIFACT_RE = re.compile(
    r"(?i)^\s*(commented\s*\[|deleted:|inserted:|mso-|_GoBack\b|"
    r"\[comment:|\[deleted:|\[inserted:)"
)
WORD_RE = re.compile(r"[\w\u0980-\u09FF]+(?:[-'][\w\u0980-\u09FF]+)?", re.UNICODE)

ROMAN = r"(?:[ivxlcdm]+)"
NUMBER_WORDS = (
    "one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    "thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
    "twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety"
)
CHAPTER_RE = re.compile(
    rf"^\s*(chapter|book|part|volume)\s+({ROMAN}|\d+|{NUMBER_WORDS})\b[\s:.\-—]*(.*)$",
    re.IGNORECASE,
)
LETTER_RE = re.compile(rf"^\s*letter\s+({ROMAN}|\d+|{NUMBER_WORDS})\b[\s:.\-—]*(.*)$", re.IGNORECASE)
ROMAN_TITLE_RE = re.compile(rf"^\s*({ROMAN})\.\s+(.{{2,100}})$", re.IGNORECASE)
ROMAN_HEADING_RE = re.compile(rf"^\s*{ROMAN}\.?\s*$", re.IGNORECASE)
NUMERIC_HEADING_RE = re.compile(r"^\s*\d{1,3}\.?\s*$")
ILLUSTRATION_LINE_RE = re.compile(r"(?i)\[\s*(illustration|image|plate|figure)\b")
COPYRIGHT_ART_RE = re.compile(r"(?i)\b(copyright\s+\d{4}|illustrations?\s+.*copyright|all rights reserved)\b")
BENGALI_RE = re.compile(r"[\u0980-\u09FF]")
WIKISOURCE_BOILERPLATE_RE = re.compile(
    r"(?i)\b("
    r"wikisource|wikimedia|mediawiki|creative commons|cc[-\s]?by[-\s]?sa|"
    r"retrieved from|jump to navigation|jump to search|navigation menu|"
    r"download as|printable version|permanent link|page information"
    r")\b|উইকিসংকলন|উইকিমিডিয়া|সম্পাদনা|আলাপ|নেভিগেশন"
)


@dataclass
class PreparedBook:
    source_index: int
    manifest: dict[str, Any]
    upload_object: dict[str, Any] | None = None
    internal_log: dict[str, Any] | None = None
    status: str = "pending"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    sanitized_text_path: str = ""
    metadata_path: str = ""
    upload_result: dict[str, Any] | None = None

    @property
    def passed(self) -> bool:
        return self.status == "passed" and not self.errors and self.upload_object is not None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: str) -> str:
    return unicodedata.normalize("NFC", value or "")


def slugify(value: str, fallback: str | None = None) -> str:
    value = normalize_text(value)
    value = re.sub(r"[^a-zA-Z0-9\s-]", "", value).strip().lower()
    slug = re.sub(r"[\s_-]+", "-", value).strip("-")
    return slug or fallback or f"book-{uuid.uuid4().hex[:8]}"

DEFAULT_CATEGORY_SLUG = "literary-fiction"
CANONICAL_CATEGORY_SLUGS = {
    "bengali-classics",
    "literary-fiction",
    "young-readers",
    "business",
    "technology",
    "history-strategy",
    "adventure",
    "science-fiction",
    "gothic-fiction",
}
LEGACY_CATEGORY_SLUG_MAP = {
    "classic-literature": "literary-fiction",
    "literature": "literary-fiction",
    "romance": "literary-fiction",
    "mystery": "literary-fiction",
    "children-classics": "young-readers",
    "childrens-literature": "young-readers",
    "children-literature": "young-readers",
    "childrens": "young-readers",
    "children": "young-readers",
    "business-entrepreneurship": "business",
    "technology-ai": "technology",
    "history-politics": "history-strategy",
    "bengali": "bengali-classics",
    "bengali-reading": "bengali-classics",
}


def category_value_to_slug(value: str) -> str:
    value = normalize_text(value)
    value = re.sub(r"[^a-zA-Z0-9\s-]", "", value).strip().lower()
    return re.sub(r"[\s_-]+", "-", value).strip("-")


def normalize_category_slug(value: str) -> str:
    slug = category_value_to_slug(value)
    return LEGACY_CATEGORY_SLUG_MAP.get(slug, slug)


def canonical_category_slug(value: str, default: str = DEFAULT_CATEGORY_SLUG) -> str:
    slug = normalize_category_slug(value)
    if slug in CANONICAL_CATEGORY_SLUGS:
        return slug
    return default


def ascii_slug(value: str) -> str:
    value = normalize_text(value)
    value = re.sub(r"[^a-zA-Z0-9\s-]", "", value).strip().lower()
    return re.sub(r"[\s_-]+", "-", value).strip("-")


def stable_book_slug(book: dict[str, Any], index: int) -> str:
    requested = normalize_text(book.get("slug", "")).strip()
    title = normalize_text(book.get("title", "")).strip()
    candidate = ascii_slug(requested or title)
    if candidate:
        return candidate
    basis = "|".join([
        title,
        normalize_text(book.get("author", "")).strip(),
        canonical_source_url(book.get("source_url", "")),
        str(index),
    ])
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:10]
    return f"book-{digest}"


def words(value: str) -> list[str]:
    return WORD_RE.findall(value or "")


def read_json_file(path: Path) -> Any:
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return []
    return json.loads(raw)


def resolve_manifest(cli_path: str | None) -> tuple[Any, str]:
    if cli_path:
        path = Path(cli_path).expanduser().resolve()
        return read_json_file(path), str(path)

    env_value = os.environ.get("BOOK_IMPORT_MANIFEST", "").strip()
    if env_value:
        possible_path = Path(env_value).expanduser()
        if possible_path.exists():
            return read_json_file(possible_path.resolve()), str(possible_path.resolve())
        return json.loads(env_value), "BOOK_IMPORT_MANIFEST"

    path = Path.cwd() / "book_import_manifest.json"
    return read_json_file(path), str(path)


def normalize_manifest(payload: Any) -> tuple[list[dict[str, Any]], bool]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)], False
    if isinstance(payload, dict):
        books = payload.get("books", [])
        if isinstance(books, list):
            return [item for item in books if isinstance(item, dict)], bool(payload.get("all_or_nothing"))
    raise ValueError("Manifest must be a JSON array or an object with a books array.")


def output_dir(base: Path) -> Path:
    path = base / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (path / "sanitized").mkdir(parents=True, exist_ok=True)
    (path / "metadata").mkdir(parents=True, exist_ok=True)
    return path


def is_wikisource_type(source_type: str) -> bool:
    return normalize_text(source_type).strip().lower() in WIKISOURCE_SOURCE_TYPES


def canonical_source_url(value: str) -> str:
    value = normalize_text(value).strip()
    markdown = re.match(r"^\[[^\]]+\]\((https?://.+)\)$", value)
    if markdown:
        value = markdown.group(1).strip()
    return value


def request_safe_url(value: str) -> str:
    value = canonical_source_url(value)
    parsed = urlparse(value)
    return urlunparse((
        parsed.scheme,
        parsed.netloc.encode("idna").decode("ascii"),
        quote(parsed.path, safe="/:%"),
        parsed.params,
        quote(parsed.query, safe="=&?/:;%"),
        quote(parsed.fragment, safe=""),
    ))


def is_wikisource_url(url: str) -> bool:
    parsed = urlparse(canonical_source_url(url or ""))
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower().endswith("wikisource.org")


def is_gutenberg_type(source_type: str) -> bool:
    return normalize_text(source_type).strip().lower() in GUTENBERG_SOURCE_TYPES


def is_gutenberg_url(url: str) -> bool:
    parsed = urlparse(canonical_source_url(url or ""))
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower().endswith("gutenberg.org")


def wikisource_render_url(url: str) -> str:
    url = canonical_source_url(url)
    if "action=render" in url:
        return request_safe_url(url)
    delimiter = "&" if urlparse(url).query else "?"
    return request_safe_url(f"{url}{delimiter}action=render")


def forbidden_terms_for(book: dict[str, Any]) -> list[str]:
    terms = list(book.get("forbidden_source_terms") or DEFAULT_FORBIDDEN_TERMS)
    if is_wikisource_type(book.get("source_type", "")) or is_wikisource_url(book.get("source_url", "")):
        terms.extend(term for term in WIKISOURCE_FORBIDDEN_TERMS if term not in terms)
    return terms


def removal_phrases_for(book: dict[str, Any]) -> list[str]:
    """Exact reader-facing phrase removals requested in the manifest.

    Supported keys intentionally require explicit phrases. This avoids broad,
    meaning-changing rewrites while still letting admins strip known edition
    headers, index fragments, repeated disclaimers, or other review-approved
    phrases before upload.
    """
    phrases: list[str] = []
    for key in ("remove_reader_phrases", "remove_exact_phrases", "remove_phrases"):
        value = book.get(key)
        if isinstance(value, str):
            phrases.append(value)
        elif isinstance(value, list):
            phrases.extend(item for item in value if isinstance(item, str))
    unique: list[str] = []
    for phrase in phrases:
        cleaned = normalize_text(phrase).strip()
        if cleaned and cleaned not in unique:
            unique.append(cleaned)
    return unique


def apply_manifest_phrase_removals(text: str, manifest: dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    for phrase in removal_phrases_for(manifest):
        pattern = re.compile(re.escape(phrase), flags=re.IGNORECASE)
        text, count = pattern.subn("", text)
        if count:
            warnings.append(f"Removed instructed exact phrase {count} time(s): {phrase[:80]}")
    return text, warnings


def source_url_candidates(url: str, source_type: str = "") -> list[str]:
    url = canonical_source_url(url)
    candidates = [request_safe_url(url)]
    parsed = urlparse(url or "")
    if is_wikisource_type(source_type) or is_wikisource_url(url):
        candidates.insert(0, wikisource_render_url(url))
    gutenberg_id_match = re.search(r"/ebooks/(\d+)(?:[./?#].*)?$", parsed.path)
    text_file_match = re.search(r"/ebooks/(\d+)\.txt\.utf-8$", parsed.path)
    match = text_file_match or gutenberg_id_match
    if is_gutenberg_url(url) and match:
        book_id = match.group(1)
        text_candidates = [
            request_safe_url(f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"),
            request_safe_url(f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt"),
            request_safe_url(f"https://www.gutenberg.org/files/{book_id}/{book_id}.txt"),
        ]
        candidates = text_candidates + candidates
    unique: list[str] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


def download_source(url: str, source_type: str = "") -> tuple[bytes, dict[str, Any]]:
    parsed = urlparse(canonical_source_url(url or ""))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source_url must be an http(s) URL")
    last_error: Exception | None = None
    total_attempts = 0
    for candidate_url in source_url_candidates(url, source_type):
        for attempt in range(1, 3):
            total_attempts += 1
            request = Request(candidate_url, headers={"User-Agent": "EarnalismBookImporter/1.0"})
            try:
                with urlopen(request, timeout=90) as response:
                    status = getattr(response, "status", 200)
                    if status < 200 or status >= 300:
                        raise ValueError(f"HTTP status {status}")
                    body = response.read(MAX_SOURCE_BYTES + 1)
                    if len(body) > MAX_SOURCE_BYTES:
                        raise ValueError("source file exceeds 20MB importer limit")
                    return body, {
                        "http_status": status,
                        "content_type": response.headers.get("Content-Type", ""),
                        "content_length": response.headers.get("Content-Length", ""),
                        "download_attempts": total_attempts,
                        "download_url": candidate_url,
                    }
            except HTTPError as exc:
                last_error = exc
                if exc.code in {404, 410}:
                    break
                if attempt < 2:
                    time.sleep(attempt)
                    continue
                break
            except (TimeoutError, socket.timeout, URLError) as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(attempt)
                    continue
                break
    detail = getattr(last_error, "reason", last_error)
    raise ValueError(f"Source download failed: {detail}")


def decode_utf8(body: bytes) -> str:
    try:
        return body.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("source file is not readable UTF-8") from exc


def remove_repository_wrappers(text: str, manifest: dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    lines = text.split("\n")
    lower_lines = [line.lower() for line in lines]

    start_markers = manifest.get("start_markers") or [
        "*** start of",
        "start of the project",
        "start of this project",
        "start of the gutenberg",
    ]
    end_markers = manifest.get("end_markers") or [
        "*** end of",
        "end of project gutenberg",
        "end of the project",
        "end of this project",
    ]

    def is_wrapper_marker(line: str, markers: list[str]) -> bool:
        stripped = line.strip()
        if not any(marker.lower() in stripped for marker in markers):
            return False
        # Avoid cutting legitimate prose such as "at the end of the house".
        if stripped.startswith("***"):
            return True
        return any(term in stripped for term in ("project", "gutenberg", "ebook", "e-book"))

    start_idx = None
    for idx, line in enumerate(lower_lines):
        if is_wrapper_marker(line, start_markers):
            start_idx = idx + 1
            warnings.append("Removed source wrapper before start marker.")
            break

    end_idx = None
    search_start = start_idx or 0
    for idx in range(search_start, len(lines)):
        line = lower_lines[idx]
        if is_wrapper_marker(line, end_markers):
            end_idx = idx
            warnings.append("Removed source wrapper after end marker.")
            break

    sliced = lines[start_idx:end_idx] if start_idx is not None or end_idx is not None else lines
    filtered: list[str] = []
    removed_boilerplate = 0
    for line in sliced:
        if TRACKED_ARTIFACT_RE.search(line):
            removed_boilerplate += 1
            continue
        if SOURCE_BOILERPLATE_RE.search(line):
            removed_boilerplate += 1
            continue
        if COPYRIGHT_ART_RE.search(line):
            removed_boilerplate += 1
            continue
        filtered.append(line.rstrip())

    if removed_boilerplate:
        warnings.append(f"Removed {removed_boilerplate} source-boilerplate/artifact line(s).")
    return "\n".join(filtered), warnings


def extract_heading_from_art_block(block: list[str]) -> str:
    text = " ".join(block)
    text = re.sub(r"(?i)\[\s*(illustration|image|plate|figure)\s*:?", " ", text)
    text = text.replace("[", " ").replace("]", " ")
    text = re.sub(r"\s+", " ", text).strip()
    match = re.search(r"(?i)\bchapter\s+([ivxlcdm]+|\d+|one|two|three|four|five|six|seven|eight|nine|ten)\.?", text)
    if match:
        return f"Chapter {match.group(1)}"
    return ""


def remove_illustration_blocks(text: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    lines = text.split("\n")
    cleaned: list[str] = []
    removed = 0
    retained_headings = 0
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if ILLUSTRATION_LINE_RE.search(line):
            block = [line]
            while "]" not in lines[idx] and idx + 1 < len(lines):
                idx += 1
                block.append(lines[idx])
            heading = extract_heading_from_art_block(block)
            if heading:
                cleaned.extend(["", heading, ""])
                retained_headings += 1
            removed += 1
            idx += 1
            continue
        if COPYRIGHT_ART_RE.search(line):
            removed += 1
            idx += 1
            continue
        cleaned.append(line)
        idx += 1
    if removed:
        warnings.append(f"Removed {removed} illustration/copyright block(s).")
    if retained_headings:
        warnings.append(f"Recovered {retained_headings} chapter heading(s) from illustration captions.")
    return "\n".join(cleaned), warnings


def remove_html_blocks_by_marker(text: str, markers: list[str]) -> str:
    marker_re = "|".join(re.escape(marker) for marker in markers)
    block_re = re.compile(
        rf"(?is)<(?P<tag>div|table|aside|nav|footer|header|ul|ol|span)\b"
        rf"(?=[^>]*(?:class|id)\s*=\s*['\"][^'\"]*(?:{marker_re})[^'\"]*['\"])[^>]*>"
        rf".*?</(?P=tag)>"
    )
    previous = None
    while previous != text:
        previous = text
        text = block_re.sub("\n", text)
    return text


def html_fragment_to_text(fragment: str) -> str:
    text = re.sub(r"(?is)<!--.*?-->", "\n", fragment)
    text = re.sub(r"(?is)<(script|style|noscript|svg|math)\b.*?</\1>", "\n", text)
    text = remove_html_blocks_by_marker(text, [
        "mw-editsection", "mw-jump", "toc", "catlinks", "printfooter",
        "metadata", "license", "licensetpl", "ambox", "navbox", "noprint",
        "ws-noexport", "sisterproject", "portal", "infobox", "headerContainer",
        "footer", "navigation",
    ])
    text = re.sub(r"(?is)<sup\b[^>]*(?:reference|mw-ref)[^>]*>.*?</sup>", "", text)
    text = re.sub(r"(?is)<span\b[^>]*mw-editsection[^>]*>.*?</span>", "", text)
    text = re.sub(r"(?is)</?(h[1-6]|p|div|section|article|blockquote|li|tr)\b[^>]*>", "\n", text)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\[(?:edit|সম্পাদনা)\]", "", text, flags=re.IGNORECASE)
    return text


def extract_wikisource_text(raw_html: str) -> tuple[str, list[str]]:
    warnings = ["Extracted core text from Wikisource/MediaWiki HTML."]
    html_text = normalize_text(raw_html)
    match = re.search(r"(?is)<main\b[^>]*>(.*?)</main>", html_text)
    if not match:
        match = re.search(r"(?is)<div\b[^>]*id=['\"]mw-content-text['\"][^>]*>(.*?)</div>\s*(?:<div\b[^>]*id=['\"]catlinks|</main|<footer)", html_text)
    fragment = match.group(1) if match else html_text
    text = html_fragment_to_text(fragment)

    lines: list[str] = []
    removed = 0
    for raw_line in text.split("\n"):
        line = re.sub(r"[ \t\xa0]+", " ", raw_line).strip()
        if not line:
            lines.append("")
            continue
        if WIKISOURCE_BOILERPLATE_RE.search(line):
            removed += 1
            continue
        lines.append(line)
    if removed:
        warnings.append(f"Removed {removed} Wikisource/MediaWiki boilerplate line(s).")
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text, warnings


def sanitize_text(raw: str, manifest: dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    text = normalize_text(raw).replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    if is_wikisource_type(manifest.get("source_type", "")) or (
        is_wikisource_url(manifest.get("source_url", "")) and re.search(r"(?is)<html|<body|mw-content-text|mw-parser-output", text)
    ):
        text, wikisource_warnings = extract_wikisource_text(text)
        warnings.extend(wikisource_warnings)

    if "<" in text and ">" in text:
        text = HTML_BLOCK_RE.sub("", text)
        text = HTML_TAG_RE.sub("", text)
        text = html.unescape(text)
        warnings.append("Removed raw HTML/script/style markup.")

    text, wrapper_warnings = remove_repository_wrappers(text, manifest)
    warnings.extend(wrapper_warnings)
    text, illustration_warnings = remove_illustration_blocks(text)
    warnings.extend(illustration_warnings)
    text, removal_warnings = apply_manifest_phrase_removals(text, manifest)
    warnings.extend(removal_warnings)

    forbidden = forbidden_terms_for(manifest)
    forbidden_re = re.compile("|".join(re.escape(term) for term in forbidden), re.IGNORECASE)
    cleaned_lines = []
    removed_forbidden = 0
    for line in text.split("\n"):
        if forbidden_re.search(line):
            removed_forbidden += 1
            continue
        cleaned_lines.append(re.sub(r"[ \t]+", " ", line).rstrip())
    if removed_forbidden:
        warnings.append(f"Removed {removed_forbidden} line(s) containing forbidden source terms.")

    text = "\n".join(cleaned_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text).strip()
    return text, warnings


def title_case_ratio(line: str) -> float:
    tokens = [token for token in re.split(r"\s+", line.strip()) if token]
    if not tokens:
        return 0.0
    title_like = sum(1 for token in tokens if token[:1].isupper() or token.isupper())
    return title_like / len(tokens)


TITLE_FUNCTION_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "but",
    "by",
    "for",
    "from",
    "in",
    "into",
    "nor",
    "of",
    "on",
    "or",
    "over",
    "the",
    "to",
    "with",
    "without",
}


def title_line_ratio(line: str) -> float:
    tokens = [token for token in re.split(r"\s+", line.strip()) if token]
    if not tokens:
        return 0.0
    title_like = 0
    for token in tokens:
        cleaned = re.sub(r"^[\"'“‘(\[]+|[\"'”’),.!?\]:;]+$", "", token)
        if not cleaned:
            continue
        lower = cleaned.lower()
        if lower in TITLE_FUNCTION_WORDS or cleaned[:1].isupper() or cleaned.isupper():
            title_like += 1
    return title_like / len(tokens)


def clean_heading_text(value: str) -> str:
    value = re.sub(r"[\[\]_*`]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .\t")
    return value[:120] or "Untitled"


def next_nonempty_index(lines: list[str], start: int) -> int | None:
    for idx in range(start, len(lines)):
        if lines[idx].strip():
            return idx
    return None


def looks_like_title_line(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 100:
        return False
    if re.search(r"[.;:]$", line):
        return False
    if len(words(line)) > 12:
        return False
    return (
        line.isupper()
        or title_case_ratio(line) >= 0.75
        or title_line_ratio(line) >= 0.75
    )


def heading_candidate(lines: list[str], index: int, allow_title_case_headings: bool = False) -> dict[str, Any] | None:
    line = lines[index].strip()
    if not line or len(line) > 140:
        return None
    prev_blank = index == 0 or not lines[index - 1].strip()

    match = CHAPTER_RE.match(line) or LETTER_RE.match(line)
    if match and prev_blank:
        kind = (match.group(1) or "").lower()
        rest_for_kind = (match.group(match.lastindex or 0) or "").strip().lower()
        if kind in {"book", "part", "volume"} and "chapter" in rest_for_kind:
            return None
        title = clean_heading_text(line)
        body_start = index + 1
        raw_trailing = (match.group(match.lastindex or 0) or "").strip()
        trailing = clean_heading_text(raw_trailing) if raw_trailing else ""
        next_idx = next_nonempty_index(lines, index + 1)
        if not trailing and next_idx is not None:
            possible_subtitle = lines[next_idx].strip()
            if looks_like_title_line(possible_subtitle) and not heading_line_no_context(possible_subtitle):
                title = f"{title}. {clean_heading_text(possible_subtitle)}"
                body_start = next_idx + 1
        return {"start": index, "body_start": body_start, "title": title}

    roman_title = ROMAN_TITLE_RE.match(line)
    if allow_title_case_headings and prev_blank and roman_title:
        title = f"{roman_title.group(1).upper()}. {clean_heading_text(roman_title.group(2))}"
        return {"start": index, "body_start": index + 1, "title": title}

    if prev_blank and (ROMAN_HEADING_RE.match(line) or NUMERIC_HEADING_RE.match(line)):
        title = clean_heading_text(line)
        body_start = index + 1
        next_idx = next_nonempty_index(lines, index + 1)
        if next_idx is not None:
            possible_subtitle = lines[next_idx].strip()
            if looks_like_title_line(possible_subtitle) and not heading_line_no_context(possible_subtitle):
                title = f"{title}. {clean_heading_text(possible_subtitle)}"
                body_start = next_idx + 1
        return {"start": index, "body_start": body_start, "title": title}

    next_blank = index == len(lines) - 1 or not lines[index + 1].strip()
    if allow_title_case_headings and prev_blank and next_blank and 3 <= len(line.split()) <= 8:
        if not re.search(r"[.!?]$", line) and title_case_ratio(line) >= 0.85:
            return {"start": index, "body_start": index + 1, "title": clean_heading_text(line)}
    return None


def heading_candidate_basic(lines: list[str], index: int) -> bool:
    line = lines[index].strip()
    if not line or len(line) > 140:
        return False
    prev_blank = index == 0 or not lines[index - 1].strip()
    chapter_match = CHAPTER_RE.match(line) or LETTER_RE.match(line)
    if chapter_match and prev_blank:
        kind = (chapter_match.group(1) or "").lower()
        rest_for_kind = (chapter_match.group(chapter_match.lastindex or 0) or "").strip().lower()
        if kind in {"book", "part", "volume"} and "chapter" in rest_for_kind:
            return False
        return True
    return bool(prev_blank and (ROMAN_HEADING_RE.match(line) or NUMERIC_HEADING_RE.match(line)))


def heading_line_no_context(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 160:
        return False
    match = CHAPTER_RE.match(line) or LETTER_RE.match(line)
    if match:
        kind = (match.group(1) or "").lower()
        rest_for_kind = (match.group(match.lastindex or 0) or "").strip().lower()
        return not (kind in {"book", "part", "volume"} and "chapter" in rest_for_kind)
    return bool(ROMAN_HEADING_RE.match(line) or NUMERIC_HEADING_RE.match(line))


def candidate_has_body(lines: list[str], candidate: dict[str, Any]) -> bool:
    nonempty_seen = 0
    for idx in range(candidate["body_start"], len(lines)):
        line = lines[idx].strip()
        if not line:
            continue
        if heading_line_no_context(line):
            return False
        nonempty_seen += 1
        line_word_count = len(words(line))
        if line_word_count >= 8:
            return True
        if nonempty_seen >= 8:
            return False
    return False


def plain_text_from_reader_html(value: str) -> str:
    text = re.sub(r"(?is)<br\s*/?>", "\n", value or "")
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    return html.unescape(text)


def roman_to_int(value: str) -> int:
    numerals = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    total = 0
    previous = 0
    for char in reversed(value.lower()):
        current = numerals.get(char, 0)
        total += -current if current < previous else current
        previous = max(previous, current)
    return total


def heading_sequence_number(title: str) -> int | None:
    title = title.strip()
    match = re.match(rf"(?i)^(?:chapter|letter)\s+({ROMAN}|\d+)\b", title)
    if not match:
        match = re.match(rf"(?i)^({ROMAN}|\d+)\.?\b", title)
    if not match:
        return None
    token = match.group(1)
    return int(token) if token.isdigit() else roman_to_int(token)


def text_to_reader_html(text: str) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n{2,}", text.strip()) if part.strip()]
    html_parts = []
    for para in paragraphs:
        escaped = html.escape(para).replace("\n", "<br>")
        html_parts.append(f"<p>{escaped}</p>")
    return "".join(html_parts)


def chapter_summary(text: str) -> str:
    sample = words(text)[:28]
    if not sample:
        return ""
    suffix = "..." if len(words(text)) > len(sample) else ""
    return " ".join(sample) + suffix


def detect_chapters(text: str, allow_title_case_headings: bool = False) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    lines = text.split("\n")
    boundaries: list[dict[str, Any]] = []
    idx = 0
    while idx < len(lines):
        candidate = heading_candidate(lines, idx, allow_title_case_headings=allow_title_case_headings)
        if candidate and candidate_has_body(lines, candidate):
            boundaries.append(candidate)
            idx = max(candidate["body_start"], idx + 1)
            continue
        idx += 1

    if not boundaries:
        warnings.append("No confident chapter headings detected; created fallback Full Text chapter.")
        return [{
            "order": 1,
            "title": "Full Text",
            "content": text_to_reader_html(text),
            "is_preview": False,
            "summary": chapter_summary(text),
            "warnings": ["Fallback chapter created because no confident headings were detected."],
        }], warnings

    dropped_leading = 0
    while len(boundaries) > 1:
        current = heading_sequence_number(boundaries[0]["title"])
        following = heading_sequence_number(boundaries[1]["title"])
        if current is not None and following is not None and current > following:
            boundaries.pop(0)
            dropped_leading += 1
            continue
        break
    if dropped_leading:
        warnings.append(f"Dropped {dropped_leading} leading table-of-contents/front-matter heading candidate(s).")

    dropped_trailing = 0
    if len(boundaries) > 8:
        sequence_numbers = [heading_sequence_number(candidate["title"]) for candidate in boundaries]
        for idx in range(1, len(sequence_numbers)):
            previous = sequence_numbers[idx - 1]
            current = sequence_numbers[idx]
            if previous is not None and current == 1 and previous >= 8:
                dropped_trailing = len(boundaries) - idx
                boundaries = boundaries[:idx]
                break
    if dropped_trailing:
        warnings.append(f"Dropped {dropped_trailing} trailing duplicate/reset chapter heading candidate(s).")

    preamble = "\n".join(lines[:boundaries[0]["start"]]).strip()
    if len(words(preamble)) > 20:
        warnings.append("Omitted front matter/table of contents before the first reader chapter.")

    chapters: list[dict[str, Any]] = []
    for position, candidate in enumerate(boundaries):
        end = boundaries[position + 1]["start"] if position + 1 < len(boundaries) else len(lines)
        title = candidate["title"]
        body = "\n".join(lines[candidate["body_start"]:end]).strip()
        body_word_count = len(words(body))
        if body_word_count == 0:
            warnings.append(f"Chapter '{title}' has no body text after sanitization.")
        elif body_word_count < MIN_CHAPTER_WORDS_WARNING:
            warnings.append(f"Chapter '{title}' is very short; review chapter boundary.")
        chapters.append({
            "order": len(chapters) + 1,
            "title": title,
            "content": text_to_reader_html(body),
            "is_preview": False,
            "summary": chapter_summary(body),
            "warnings": [],
        })

    warnings.append("Chapter headings were detected conservatively; review chapter boundaries before publishing.")
    return chapters, warnings


def commercial_rights_validation(book: dict[str, Any]) -> tuple[bool, dict[str, Any], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    license_text = normalize_text(f"{book.get('source_license', '')} {book.get('rights_basis', '')}").lower()
    source_type = normalize_text(book.get("source_type", "")).lower()

    if not book.get("title"):
        errors.append("title is required")
    if not book.get("author"):
        errors.append("author is required")
    source_url = canonical_source_url(book.get("source_url", ""))
    if not source_url:
        errors.append("source_url is required")
    if (
        source_type not in {"plain_text_utf8", "text_utf8", "plain_text", "txt"}
        and source_type not in WIKISOURCE_SOURCE_TYPES
        and source_type not in GUTENBERG_SOURCE_TYPES
    ):
        errors.append(f"unsupported source_type '{book.get('source_type', '')}'; use plain-text UTF-8")
    if source_type in WIKISOURCE_SOURCE_TYPES and not is_wikisource_url(source_url):
        errors.append("Wikisource source_type requires a verified *.wikisource.org source_url")
    if source_type in GUTENBERG_SOURCE_TYPES and not is_gutenberg_url(source_url):
        errors.append("Gutenberg source_type requires a verified *.gutenberg.org source_url")

    disallowed = ["cc-nc", "cc by-nc", "non-commercial", "noncommercial", "orphan", "unclear", "all rights reserved"]
    if any(term in license_text for term in disallowed):
        errors.append("commercial-use rights are restricted or unclear")
    if any(term in source_type for term in ["audio", "audiobook", "scan", "image", "pdf"]):
        errors.append("source appears audio/scanned/image/PDF based, not text-ready")
    if "translation" in license_text and "commercial" not in license_text and "public domain translation" not in license_text:
        errors.append("translation rights are not clearly commercially cleared")
    if "illustration" in license_text and "commercial" not in license_text and "public domain illustration" not in license_text:
        errors.append("illustration rights are not clearly commercially cleared")

    explicit_commercial = any(term in license_text for term in [
        "cc0", "creative commons zero", "cc by", "commercial use allowed",
        "commercial permission", "copyright holder permission", "mit", "apache", "bsd",
    ])
    public_domain_claim = "public domain" in license_text or "pd-" in license_text
    attribution_required = "cc by" in license_text and "cc0" not in license_text and not (
        source_type in WIKISOURCE_SOURCE_TYPES and public_domain_claim
    )
    if source_type in WIKISOURCE_SOURCE_TYPES and public_domain_claim and "cc by" in license_text:
        warnings.append("Wikisource page/transcription license noted; underlying literary text is treated as public domain per manifest and source evidence is kept internal.")

    india_status = "not evaluated"
    us_status = "not evaluated"
    if public_domain_claim:
        death_year = book.get("author_death_year")
        publication_year = book.get("original_publication_year")
        if not isinstance(death_year, int) or not isinstance(publication_year, int):
            errors.append("public-domain claims require author_death_year and original_publication_year")
        else:
            india_ok = death_year <= CURRENT_YEAR - 61
            us_ok = publication_year <= CURRENT_YEAR - 96
            india_status = "public domain likely" if india_ok else "not public domain by life+60"
            us_status = "public domain likely" if us_ok else "not public domain by publication-year rule"
            if not india_ok:
                errors.append("India public-domain check failed life+60 rule")
            if not us_ok:
                errors.append("U.S. public-domain check failed publication-year rule")

    if not public_domain_claim and not explicit_commercial:
        errors.append("commercial-use permission is absent or unclear")
    if attribution_required and not book.get("required_attribution"):
        errors.append("required attribution text is missing for a non-public-domain license")
    if attribution_required:
        warnings.append("Attribution-required license detected; human review required.")

    log = {
        "commercial_use_allowed": not errors,
        "india_rights_status": india_status,
        "us_rights_status": us_status,
        "attribution_required": attribution_required,
    }
    return not errors, log, warnings, errors


def first_nonempty(source: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return normalize_text(value).strip()
    return ""


def rights_metadata(book: dict[str, Any], rights_log: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    return {
        "author_death_year": book.get("author_death_year"),
        "original_publication_year": book.get("original_publication_year"),
        "source_type": book.get("source_type", ""),
        "source_license": book.get("source_license", ""),
        "rights_basis": book.get("rights_basis", ""),
        "commercial_use_allowed": rights_log.get("commercial_use_allowed", False),
        "india_rights_status": rights_log.get("india_rights_status", ""),
        "us_rights_status": rights_log.get("us_rights_status", ""),
        "attribution_required": rights_log.get("attribution_required", False),
        "requires_human_review": bool(warnings),
        "checked_at": now_iso(),
    }


def minimum_word_count_for(book: dict[str, Any]) -> int:
    explicit = book.get("minimum_word_count") or book.get("expected_min_words")
    if explicit is not None:
        return int(explicit)
    source_type = normalize_text(book.get("source_type", "")).lower()
    if source_type in {"wikisource_bengali", "wikisource_bengali_html"}:
        return MIN_BENGALI_WIKISOURCE_WORD_COUNT
    return MIN_DEFAULT_WORD_COUNT


def metadata_defaults(book: dict[str, Any], word_count: int, warnings: list[str]) -> dict[str, Any]:
    title = normalize_text(book.get("title", "")).strip()
    author = normalize_text(book.get("author", "")).strip()
    category_input = normalize_text(book.get("category_slug", "")).strip()
    category_candidate = normalize_category_slug(category_input)
    category = canonical_category_slug(category_input)
    if not category_input:
        warnings.append("category_slug missing; defaulted to literary-fiction.")
    elif category_value_to_slug(category_input) in LEGACY_CATEGORY_SLUG_MAP:
        warnings.append(f"category_slug '{category_input}' migrated to '{category}'.")
    elif category_candidate not in CANONICAL_CATEGORY_SLUGS:
        warnings.append(f"category_slug '{category_input}' is not a current shelf; defaulted to '{category}'.")
    about_author = normalize_text(book.get("about_author", "")).strip()
    if not about_author:
        warnings.append("about_author missing; left empty for human review.")

    is_published = bool(book.get("is_published") is True and book.get("availability") == "published")
    if book.get("is_published") is True and not is_published:
        warnings.append("is_published requested but availability was not published; kept as draft.")

    cover_image_url = first_nonempty(book, ["cover_image_url", "front_cover_image_url", "front_cover_url", "cover_url"])
    back_cover_image_url = first_nonempty(book, ["back_cover_image_url", "back_cover_url"])
    if not cover_image_url:
        warnings.append("front cover URL missing; upload remains draft and needs a legally cleared cover before publishing.")
    if not back_cover_image_url:
        warnings.append("back cover URL missing; optional back cover can be added in admin review.")

    return {
        "title": title,
        "subtitle": normalize_text(book.get("subtitle", "")).strip(),
        "author": author,
        "category_slug": category,
        "short_description": normalize_text(book.get("short_description", "")).strip()
        or f"{title} is prepared as a clean digital reading edition." if title else "A clean digital reading edition.",
        "description": normalize_text(book.get("description", "")).strip()
        or "This cleaned text-only edition is prepared for structured digital reading on Earnalism.",
        "estimated_reading_time": f"{max(1, round(word_count / READING_WPM))} min",
        "formats": book.get("formats") if isinstance(book.get("formats"), list) and book.get("formats") else ["Ebook"],
        "benefits": book.get("benefits") if isinstance(book.get("benefits"), list) and book.get("benefits") else [
            "Read a legally cleared digital text.",
            "Enjoy a clean, structured reading format.",
            "Access a render-safe ebook prepared for web reading.",
        ],
        "who_for": book.get("who_for") if isinstance(book.get("who_for"), list) and book.get("who_for") else [
            "General readers",
            "Students and lifelong learners",
            "Users who prefer structured digital reading",
        ],
        "learnings": book.get("learnings") if isinstance(book.get("learnings"), list) and book.get("learnings") else [
            "Understand the major themes and structure of the work.",
            "Engage with the text in a clean digital format.",
            "Read without unrelated source-file boilerplate.",
        ],
        "about_author": about_author,
        "cover_image_url": cover_image_url,
        "back_cover_image_url": back_cover_image_url,
        "is_published": is_published,
    }


def validate_sanitization(upload_object: dict[str, Any], cleaned_text: str, forbidden_terms: list[str], min_word_count: int) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    reader_facing_object = {
        key: value
        for key, value in upload_object.items()
        if key not in {"rights_metadata", "upload_notes"}
    }
    reader_blob = json.dumps(reader_facing_object, ensure_ascii=False)
    forbidden_re = re.compile("|".join(re.escape(term) for term in forbidden_terms), re.IGNORECASE)
    if len(words(cleaned_text)) < min_word_count:
        errors.append("cleaned content is suspiciously short")
    if forbidden_re.search(reader_blob):
        errors.append("forbidden source/repository terms remain in reader-facing content or metadata")
    if re.search(r"(?i)\[\s*(illustration|image|plate|figure)\b", reader_blob):
        errors.append("illustration/image source markers remain in reader-facing content")
    if HTML_BLOCK_RE.search(cleaned_text) or re.search(r"(?is)<\s*/?\s*(script|style)\b", reader_blob):
        errors.append("HTML script/style tags remain")
    if not upload_object.get("title") or not upload_object.get("author"):
        errors.append("title or author is missing")
    if not upload_object.get("chapters"):
        errors.append("no chapters exist and fallback was not created")
    replacement_chars = cleaned_text.count("\ufffd")
    if replacement_chars > 0:
        errors.append("content appears OCR-garbled or unreadable")
    if SOURCE_BOILERPLATE_RE.search(cleaned_text):
        errors.append("obvious unrelated source boilerplate remains")
    empty_chapters = [
        chapter.get("title", "Untitled")
        for chapter in upload_object.get("chapters", [])
        if len(words(plain_text_from_reader_html(chapter.get("content", "")))) == 0
    ]
    if empty_chapters:
        sample = ", ".join(empty_chapters[:5])
        errors.append(f"empty chapters remain after processing: {sample}")
    short_chapters = [
        chapter.get("title", "Untitled")
        for chapter in upload_object.get("chapters", [])
        if 0 < len(words(plain_text_from_reader_html(chapter.get("content", "")))) < MIN_CHAPTER_WORDS_WARNING
    ]
    if short_chapters:
        warnings.append("One or more chapters are very short; review boundaries.")
    return warnings, errors


def prepare_book(index: int, book: dict[str, Any], out_dir: Path) -> PreparedBook:
    result = PreparedBook(source_index=index, manifest=book)
    rights_ok, rights_log, rights_warnings, rights_errors = commercial_rights_validation(book)
    result.warnings.extend(rights_warnings)
    result.errors.extend(rights_errors)
    if not rights_ok:
        result.status = "skipped"
        result.internal_log = build_internal_log(book, rights_log, result, "rights_failed")
        return result

    try:
        body, download_log = download_source(book["source_url"], book.get("source_type", ""))
        raw = decode_utf8(body)
        cleaned, clean_warnings = sanitize_text(raw, book)
        result.warnings.extend(clean_warnings)
    except Exception as exc:
        result.status = "skipped"
        result.errors.append(str(exc))
        result.internal_log = build_internal_log(book, rights_log, result, "download_or_decode_failed")
        return result

    chapter_rules = book.get("chapter_rules") if isinstance(book.get("chapter_rules"), dict) else {}
    chapters, chapter_warnings = detect_chapters(
        cleaned,
        allow_title_case_headings=bool(chapter_rules.get("allow_title_case_headings") or book.get("allow_title_case_headings")),
    )
    result.warnings.extend(chapter_warnings)
    if is_wikisource_type(book.get("source_type", "")) and "bengali" in normalize_text(book.get("source_type", "")).lower():
        if not BENGALI_RE.search(cleaned):
            result.errors.append("Bengali Wikisource extraction did not preserve Bengali Unicode text")
    word_count = len(words(cleaned))
    metadata = metadata_defaults(book, word_count, result.warnings)
    metadata["slug"] = stable_book_slug(book, index)
    upload_object = {
        **metadata,
        "audiobook_enabled": bool(book.get("audiobook_enabled") is True),
        "generate_audiobook": bool(book.get("generate_audiobook") is True),
        "rights_metadata": rights_metadata(book, rights_log, result.warnings),
        "chapters": chapters,
        "upload_notes": [
            "Prepared by Earnalism legal-source text importer.",
            "Draft mode; human review required before publishing.",
        ],
    }
    if len(upload_object["chapters"]) == 1 and upload_object["chapters"][0].get("title") == "Full Text":
        upload_object["chapters"][0]["title"] = metadata.get("title") or "Full Text"

    attribution = normalize_text(book.get("required_attribution", "")).strip()
    if attribution:
        upload_object["upload_notes"].append(f"Required attribution for review: {attribution}")

    forbidden = forbidden_terms_for(book)
    min_word_count = minimum_word_count_for(book)
    validation_warnings, validation_errors = validate_sanitization(upload_object, cleaned, forbidden, min_word_count)
    result.warnings.extend(validation_warnings)
    result.errors.extend(validation_errors)

    slug = slugify(metadata["title"], fallback=f"book-{index + 1}")
    sanitized_path = out_dir / "sanitized" / f"{slug}.txt"
    metadata_path = out_dir / "metadata" / f"{slug}.json"
    sanitized_path.write_text(cleaned, encoding="utf-8")
    metadata_path.write_text(json.dumps(upload_object, ensure_ascii=False, indent=2), encoding="utf-8")
    result.sanitized_text_path = str(sanitized_path)
    result.metadata_path = str(metadata_path)
    result.upload_object = upload_object
    result.status = "passed" if not result.errors else "skipped"
    result.internal_log = build_internal_log(
        book,
        {**rights_log, **download_log},
        result,
        "passed" if result.passed else "sanitization_failed",
    )
    return result


def build_internal_log(book: dict[str, Any], rights_log: dict[str, Any], result: PreparedBook, validation_result: str) -> dict[str, Any]:
    return {
        "title": book.get("title", ""),
        "author": book.get("author", ""),
        "author_death_year": book.get("author_death_year"),
        "original_publication_year": book.get("original_publication_year"),
        "source_url": canonical_source_url(book.get("source_url", "")),
        "source_url_manifest_value": book.get("source_url", ""),
        "source_type": book.get("source_type", ""),
        "source_license": book.get("source_license", ""),
        "rights_basis": book.get("rights_basis", ""),
        "commercial_use_allowed": rights_log.get("commercial_use_allowed", False),
        "india_rights_status": rights_log.get("india_rights_status", ""),
        "us_rights_status": rights_log.get("us_rights_status", ""),
        "sanitization_timestamp": now_iso(),
        "validation_result": validation_result,
        "upload_id": result.upload_result.get("id", "") if result.upload_result else "",
        "warnings": result.warnings,
        "errors": result.errors,
    }


def normalize_api_url(api_url: str) -> str:
    api_url = (api_url or "").strip().rstrip("/")
    if not api_url:
        raise ValueError("EARNALISM_API_URL or --api-url is required for upload")
    return api_url if api_url.endswith("/api") else f"{api_url}/api"


def api_json(method: str, url: str, payload: dict[str, Any] | None = None, token: str | None = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    last_error: Exception | None = None
    for attempt in range(1, 4):
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=API_TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code in {502, 503, 504} and attempt < 3:
                last_error = RuntimeError(f"{method} {url} failed with HTTP {exc.code}: {detail[:500]}")
                time.sleep(attempt * 3)
                continue
            raise RuntimeError(f"{method} {url} failed with HTTP {exc.code}: {detail[:500]}") from exc
        except (TimeoutError, socket.timeout, ConnectionResetError, URLError) as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(attempt * 2)
                continue
            break
    raise RuntimeError(f"{method} {url} failed after retries: {last_error}") from last_error


def api_json_optional(method: str, url: str, payload: dict[str, Any] | None = None, token: str | None = None) -> dict[str, Any] | None:
    try:
        return api_json(method, url, payload, token)
    except RuntimeError as exc:
        if "HTTP 404" in str(exc):
            return None
        raise


def admin_token(api_url: str) -> str:
    token = os.environ.get("EARNALISM_ADMIN_TOKEN", "").strip()
    if token:
        return token
    email = os.environ.get("ADMIN_EMAIL", "").strip()
    password = os.environ.get("ADMIN_PASSWORD", "").strip()
    if not email or not password:
        raise RuntimeError("Upload credentials missing: set EARNALISM_ADMIN_TOKEN or ADMIN_EMAIL + ADMIN_PASSWORD.")
    data = api_json("POST", f"{api_url}/auth/login", {"email": email, "password": password})
    token = data.get("token")
    if not token:
        raise RuntimeError("Admin login did not return a token.")
    return token


def upload_book(
    result: PreparedBook,
    api_url: str,
    token: str,
    update_existing: bool = False,
    ignore_published_duplicates: bool = False,
) -> None:
    if not result.upload_object:
        raise RuntimeError("No upload object prepared.")
    obj = result.upload_object
    book_payload = {
        key: obj[key]
        for key in [
            "title", "subtitle", "author", "category_slug", "short_description",
            "description", "cover_image_url", "back_cover_image_url",
            "estimated_reading_time", "formats", "benefits", "who_for",
            "learnings", "about_author", "rights_metadata", "audiobook_enabled",
            "generate_audiobook", "is_published", "slug",
        ]
        if key in obj
    }
    target_slug = obj.get("slug") or slugify(obj.get("title", ""))
    existing = api_json_optional("GET", f"{api_url}/admin/books/{target_slug}", token=token)
    if existing and not update_existing:
        raise RuntimeError(f"Book slug already exists: {target_slug}. Re-run with --update-existing-drafts to replace draft content.")
    if existing:
        if existing.get("is_published"):
            if ignore_published_duplicates:
                result.status = "skipped"
                result.warnings.append(f"Published duplicate ignored for slug: {target_slug}")
                result.errors.append(f"Book slug already exists and is published: {target_slug}. Ignored as requested.")
                if result.internal_log:
                    result.internal_log["validation_result"] = "published_duplicate_ignored"
                    result.internal_log["errors"] = result.errors
                    result.internal_log["warnings"] = result.warnings
                return
            raise RuntimeError(f"Book slug already exists and is published: {target_slug}. Refusing to overwrite published content.")
        created = api_json("PUT", f"{api_url}/admin/books/{target_slug}", book_payload, token)
        for chapter in existing.get("chapters", []):
            cid = chapter.get("id")
            if cid:
                try:
                    api_json("DELETE", f"{api_url}/admin/books/{target_slug}/chapters/{cid}", token=token)
                except RuntimeError as exc:
                    if "HTTP 404" not in str(exc):
                        raise
    else:
        created = api_json("POST", f"{api_url}/admin/books", book_payload, token)
    slug = created.get("slug")
    if not slug:
        raise RuntimeError("Book upload did not return a slug.")
    for chapter in obj.get("chapters", []):
        api_json("POST", f"{api_url}/admin/books/{slug}/chapters", {
            "title": chapter.get("title", "Untitled"),
            "content": chapter.get("content", ""),
            "is_preview": bool(chapter.get("is_preview") is True),
        }, token)
    result.upload_result = {
        "id": created.get("id", ""),
        "slug": slug,
        "title": created.get("title", obj.get("title", "")),
    }
    if result.internal_log:
        result.internal_log["upload_id"] = result.upload_result["id"]


def report_payload(results: list[PreparedBook], manifest_source: str, out_dir: Path) -> dict[str, Any]:
    uploaded = [item for item in results if item.upload_result]
    skipped = [item for item in results if item.status == "skipped" or item.errors]
    passed = [item for item in results if item.passed]
    return {
        "manifest_source": manifest_source,
        "generated_at": now_iso(),
        "output_dir": str(out_dir),
        "total_books": len(results),
        "passed_validation_count": len(passed),
        "uploaded_count": len(uploaded),
        "skipped_count": len(skipped),
        "uploaded_books": [item.upload_result for item in uploaded],
        "skipped_books": [
            {
                "index": item.source_index,
                "title": item.manifest.get("title", ""),
                "author": item.manifest.get("author", ""),
                "reasons": item.errors,
                "warnings": item.warnings,
            }
            for item in skipped
        ],
        "validation_warnings": [
            {
                "index": item.source_index,
                "title": item.manifest.get("title", ""),
                "warnings": item.warnings,
            }
            for item in results if item.warnings
        ],
        "internal_log_path": str(out_dir / "internal_import_log.json"),
    }


def write_reports(results: list[PreparedBook], manifest_source: str, out_dir: Path, name: str) -> dict[str, Any]:
    internal_logs = [item.internal_log for item in results if item.internal_log]
    (out_dir / "internal_import_log.json").write_text(
        json.dumps(internal_logs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    payload = report_payload(results, manifest_source, out_dir)
    report_path = out_dir / f"{name}.json"
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def print_report(report: dict[str, Any], label: str) -> None:
    print(f"\n{label}")
    print("=" * len(label))
    print(f"Manifest: {report['manifest_source']}")
    print(f"Output: {report['output_dir']}")
    print(f"Total books: {report['total_books']}")
    print(f"Passed validation: {report['passed_validation_count']}")
    print(f"Uploaded: {report['uploaded_count']}")
    print(f"Skipped: {report['skipped_count']}")
    if report["uploaded_books"]:
        print("Uploaded books:")
        for book in report["uploaded_books"]:
            print(f"  - {book.get('title')} ({book.get('slug')})")
    if report["skipped_books"]:
        print("Skipped books:")
        for item in report["skipped_books"]:
            title = item.get("title") or f"manifest index {item['index']}"
            print(f"  - {title}: {'; '.join(item.get('reasons') or ['unknown reason'])}")
    print(f"Internal log: {report['internal_log_path']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Import legally-cleared plain-text books into Earnalism.")
    parser.add_argument("manifest", nargs="?", help="Manifest JSON file path. Falls back to BOOK_IMPORT_MANIFEST, then ./book_import_manifest.json.")
    parser.add_argument("--upload", action="store_true", help="After dry-run validation, upload passing books through the real admin API.")
    parser.add_argument("--api-url", default=os.environ.get("EARNALISM_API_URL", ""), help="Earnalism API URL, e.g. https://api.theearnalism.com or http://localhost:8000")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_ROOT), help="Base directory for sanitized files and reports.")
    parser.add_argument("--update-existing-drafts", action="store_true", help="If a slug already exists as a draft, update its metadata and replace its chapters. Published books are never overwritten.")
    parser.add_argument("--ignore-published-duplicates", action="store_true", help="Skip already-published duplicate slugs without failing the upload batch.")
    args = parser.parse_args()

    out_dir = output_dir(Path(args.output_dir).expanduser().resolve())
    try:
        manifest_payload, manifest_source = resolve_manifest(args.manifest)
        books, top_level_all_or_nothing = normalize_manifest(manifest_payload)
    except Exception as exc:
        print(f"Manifest error: {exc}", file=sys.stderr)
        return 2

    results = [prepare_book(index, book, out_dir) for index, book in enumerate(books)]
    dry_report = write_reports(results, manifest_source, out_dir, "dry_run_report")
    print_report(dry_report, "Dry-run validation report")

    if not args.upload:
        print("\nDry-run only. Re-run with --upload and admin API credentials to upload passing books.")
        return 0

    if not results:
        upload_report = write_reports(results, manifest_source, out_dir, "upload_report")
        print_report(upload_report, "Upload report")
        return 0

    all_or_nothing = top_level_all_or_nothing or any(bool(item.manifest.get("all_or_nothing")) for item in results)
    if all_or_nothing and any(not item.passed for item in results):
        print("\nall_or_nothing=true and at least one book failed validation; no books uploaded.")
        write_reports(results, manifest_source, out_dir, "upload_report")
        return 1

    passing = [item for item in results if item.passed]
    if not passing:
        print("\nNo books passed validation; no upload attempted.")
        write_reports(results, manifest_source, out_dir, "upload_report")
        return 1

    try:
        api_url = normalize_api_url(args.api_url)
        token = admin_token(api_url)
    except Exception as exc:
        print(f"\nUpload credentials/API unavailable: {exc}")
        print("Stopped after sanitized files, metadata JSON, and dry-run report.")
        return 2

    for item in passing:
        try:
            upload_book(
                item,
                api_url,
                token,
                update_existing=args.update_existing_drafts,
                ignore_published_duplicates=args.ignore_published_duplicates,
            )
            if item.upload_result:
                item.status = "uploaded"
        except Exception as exc:
            item.errors.append(str(exc))
            item.status = "skipped"
            if item.internal_log:
                item.internal_log["validation_result"] = "upload_failed"
                item.internal_log["errors"] = item.errors

    upload_report = write_reports(results, manifest_source, out_dir, "upload_report")
    print_report(upload_report, "Upload report")
    if upload_report["uploaded_count"] == len(passing):
        return 0
    if args.ignore_published_duplicates:
        failed = [
            item for item in passing
            if not item.upload_result and not any("already exists and is published" in error for error in item.errors)
        ]
        if not failed:
            return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
