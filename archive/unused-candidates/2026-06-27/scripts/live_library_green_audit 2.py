#!/usr/bin/env python3
"""Audit live Earnalism books and optionally publish only GO-GREEN drafts.

This script is intentionally conservative. It does not rewrite story content.
GO-GREEN means the title passes automated legal, chapter/index, source-content,
audio-sync, and reader/API smoke gates. Books that need human source/audio/UX
judgment remain drafts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html.parser
import json
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlparse

import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_API_URL = "https://api.theearnalism.com"
DEFAULT_FRONTEND_URL = "https://theearnalism.com"
DEFAULT_OUTPUT_ROOT = ROOT / "output" / "live_library_green_audit"
FORBIDDEN_READER_TERMS = re.compile(
    r"Project Gutenberg|Gutenberg\\.org|PGLAF|Wikisource|উইকিসংকলন|Creative Commons|CC BY",
    re.IGNORECASE,
)
BENGALI_RE = re.compile(r"[\u0980-\u09ff]")
CHAPTER_PREFIX_RE = re.compile(r"^Chapter\s+(\d+)\.\s*(.*)$", re.IGNORECASE)
ROMAN_RE = re.compile(r"^(?:Chapter\s+)?([IVXLCDM]+)\b", re.IGNORECASE)
ARABIC_RE = re.compile(r"^(?:Chapter\s+)?(\d{1,4})\b", re.IGNORECASE)
BENGALI_ORDINALS = {
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
    "চতুর্দ্দশ": 14,
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
SOURCE_KEY_ALIASES = {
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
    "attributionnotice": "attribution_notice",
    "forbiddensourceterms": "forbidden_source_terms",
}


class TextExtractor(html.parser.HTMLParser):
    BLOCK_TAGS = {"p", "div", "br", "section", "article", "h1", "h2", "h3", "h4", "li", "blockquote"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.skip_depth += 1
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        return clean_text("".join(self.parts))


@dataclass
class Gate:
    name: str
    ok: bool
    detail: str


@dataclass
class BookAudit:
    slug: str
    title: str
    author: str
    is_published: bool
    category_slug: str = ""
    language: str = ""
    chapter_count: int = 0
    word_count: int = 0
    char_count: int = 0
    audiobook_enabled: bool = False
    green: bool = False
    published_now: bool = False
    gates: list[Gate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)

    def gate(self, name: str, ok: bool, detail: str) -> None:
        self.gates.append(Gate(name=name, ok=ok, detail=detail))

    def finalize(self) -> None:
        self.green = bool(self.gates) and all(gate.ok for gate in self.gates)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def normalize_api_url(value: str) -> str:
    value = (value or DEFAULT_API_URL).rstrip("/")
    return value if value.endswith("/api") else f"{value}/api"


def clean_text(value: str) -> str:
    value = (value or "").replace("\ufeff", "").replace("\u200c", "").replace("\u200d", "")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t\xa0]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def html_to_text(value: str) -> str:
    parser = TextExtractor()
    parser.feed(value or "")
    return parser.text()


def word_tokens(value: str) -> list[str]:
    return re.findall(r"[\w\u0980-\u09ff]+", value or "", flags=re.UNICODE)


def normalized_compare(value: str) -> str:
    value = clean_text(value)
    value = re.sub(r"\[\d+\]", "", value)
    value = re.sub(r"(?m)^Chapter\s+\d+\.\s*", "", value)
    value = re.sub(r"(?m)^পৃষ্ঠা\s+\d+.*$", "", value)
    value = re.sub(r"(?m)^Page\s+\d+.*$", "", value)
    value = FORBIDDEN_READER_TERMS.sub("", value)
    value = re.sub(r"[\s\W_]+", "", value, flags=re.UNICODE)
    return value.casefold()


def chapter_texts(book: dict[str, Any], include_titles: bool = True) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for chapter in sorted(book.get("chapters") or [], key=lambda row: row.get("order", 0)):
        title = str(chapter.get("title") or "").strip()
        body = html_to_text(str(chapter.get("content") or ""))
        text = "\n\n".join(part for part in ([title] if include_titles and title else []) + [body] if part)
        rows.append((title, clean_text(text)))
    return rows


def full_reader_text(book: dict[str, Any], include_titles: bool = True) -> str:
    return clean_text("\n\n".join(text for _, text in chapter_texts(book, include_titles=include_titles) if text))


def sha_text(value: str) -> str:
    return hashlib.sha256(clean_text(value).encode("utf-8")).hexdigest()


def roman_to_int(value: str) -> int:
    numerals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for char in reversed(value.upper()):
        current = numerals.get(char, 0)
        total += -current if current < prev else current
        prev = max(prev, current)
    return total


def title_without_prefix(title: str) -> str:
    match = CHAPTER_PREFIX_RE.match(title or "")
    return (match.group(2) if match else title or "").strip()


def ordinal_from_title(title: str) -> int | None:
    cleaned = title_without_prefix(title)
    arabic = ARABIC_RE.match(cleaned)
    if arabic:
        return int(arabic.group(1))
    roman = ROMAN_RE.match(cleaned)
    if roman:
        return roman_to_int(roman.group(1))
    for label, number in BENGALI_ORDINALS.items():
        if re.search(rf"(^|[\s/।-]){re.escape(label)}($|[\s/।-])", cleaned):
            return number
    return None


def source_page_url(value: Any) -> str:
    text = str(value or "").strip()
    markdown = re.search(r"\((https?://[^)]+)\)", text)
    if markdown:
        return markdown.group(1)
    bare = re.search(r"https?://\S+", text)
    return bare.group(0).rstrip(").,;") if bare else text


def normalize_source_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    rights_metadata = normalized.get("rights_metadata")
    if isinstance(rights_metadata, dict):
        for key, value in rights_metadata.items():
            normalized.setdefault(key, value)
    for source_key, target_key in SOURCE_KEY_ALIASES.items():
        if source_key in normalized and target_key not in normalized:
            normalized[target_key] = normalized[source_key]
    if normalized.get("source_url"):
        normalized["source_url"] = source_page_url(normalized.get("source_url"))
    return normalized


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_manifest_sources() -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    by_slug: dict[str, dict[str, Any]] = {}
    by_title_author: dict[tuple[str, str], dict[str, Any]] = {}
    paths = [
        ROOT / "book_import_manifest.json",
        *ROOT.glob("output/**/metadata/*.json"),
        *ROOT.glob("output/**/bengali_wikisource_deep_repair_manifest.json"),
        *ROOT.glob("output/**/source_repaired_404_manifest.json"),
        *ROOT.glob("output/**/bengali_source_repaired_upload_manifest.json"),
    ]
    for path in paths:
        if not path.exists():
            continue
        try:
            data = load_json(path)
        except Exception:
            continue
        if isinstance(data, dict) and isinstance(data.get("books"), list):
            rows = data["books"]
        elif isinstance(data, dict):
            rows = [data]
        else:
            rows = data
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            row = normalize_source_row(row)
            for key in ("slug", "id"):
                slug = str(row.get(key) or "").strip().lower()
                if slug:
                    by_slug[slug] = row
                    if re.match(r"^[a-z]{2}-\d{3}$", slug):
                        by_slug[slug.upper()] = row
                    match = re.match(r"^[a-z]{2}-\d{3}-(.+)$", slug)
                    if match:
                        by_slug[match.group(1)] = row
            title = str(row.get("title") or "").strip()
            author = str(row.get("author") or "").strip()
            if title and author:
                by_title_author[(title, author)] = row
    return by_slug, by_title_author


def load_prepared_texts() -> dict[str, str]:
    out: dict[str, str] = {}
    paths = [
        *ROOT.glob("output/**/prepared_texts/*"),
        *ROOT.glob("output/**/sanitized/*.txt"),
        *ROOT.glob("output/audio_onboarding/texts/*.txt"),
    ]
    for path in paths:
        if not path.is_file() or path.suffix.lower() not in {".txt", ".md"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        bn_match = re.search(r"\bbn-\d{3}\b", path.stem, flags=re.IGNORECASE)
        if bn_match:
            out[bn_match.group(0).lower()] = text
        id_slug_match = re.match(r"^([a-z]{2}-\d{3})-(.+)$", path.stem, flags=re.IGNORECASE)
        if id_slug_match:
            out[id_slug_match.group(1).lower()] = text
            out[id_slug_match.group(2).lower()] = text
            continue
        book_match = re.search(r"\bbook-[a-z0-9]{8,}\b", path.stem, flags=re.IGNORECASE)
        if book_match:
            out[book_match.group(0).lower()] = text
            continue
        out[path.stem.lower()] = text
    return out


class EarnalismClient:
    def __init__(self, api_url: str) -> None:
        self.api_url = normalize_api_url(api_url)
        self.session = requests.Session()
        self.headers: dict[str, str] = {}

    def login(self) -> None:
        token = os.environ.get("EARNALISM_ADMIN_TOKEN", "").strip()
        if not token:
            email = os.environ.get("ADMIN_EMAIL", "").strip()
            password = os.environ.get("ADMIN_PASSWORD", "").strip()
            if not email or not password:
                raise RuntimeError("Missing ADMIN_EMAIL/ADMIN_PASSWORD or EARNALISM_ADMIN_TOKEN.")
            data = self.request("POST", "/auth/login", json={"email": email, "password": password})
            token = data.get("token") or data.get("access_token") or ""
        if not token:
            raise RuntimeError("Admin login did not return a token.")
        self.headers = {"Authorization": f"Bearer {token}"}

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = dict(kwargs.pop("headers", {}) or {})
        headers.update(self.headers)
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                response = self.session.request(
                    method,
                    f"{self.api_url}{path}",
                    headers=headers,
                    timeout=kwargs.pop("timeout", 90),
                    **kwargs,
                )
                if response.status_code in {502, 503, 504} and attempt < 3:
                    time.sleep(attempt * 2)
                    continue
                response.raise_for_status()
                return response.json() if response.text.strip() else {}
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
                if attempt < 3:
                    time.sleep(attempt * 2)
                    continue
                break
        raise RuntimeError(f"{method} {path} failed: {last_error}")

    def summaries(self) -> list[dict[str, Any]]:
        return self.request("GET", "/admin/books/summary")

    def book(self, slug: str) -> dict[str, Any]:
        return self.request("GET", f"/admin/books/{slug}")

    def publish(self, book: dict[str, Any], rights_metadata: dict[str, Any]) -> dict[str, Any]:
        payload_fields = {
            "title",
            "subtitle",
            "author",
            "category_slug",
            "short_description",
            "description",
            "cover_image_url",
            "back_cover_image_url",
            "estimated_reading_time",
            "price_paperback",
            "price_ebook",
            "buy_url",
            "formats",
            "benefits",
            "who_for",
            "learnings",
            "about_author",
            "rights_metadata",
            "audiobook_enabled",
            "generate_audiobook",
            "audiobook_provider",
            "audiobook_voice",
            "audio_asset_slug",
            "audiobook_assets",
            "is_published",
            "slug",
        }
        payload = {key: book.get(key) for key in payload_fields if key in book}
        payload["slug"] = book["slug"]
        payload["is_published"] = True
        payload["cover_image_url"] = book.get("cover_image_url") or book.get("cover_url") or ""
        payload["back_cover_image_url"] = book.get("back_cover_image_url") or book.get("back_cover_url") or ""
        payload["rights_metadata"] = rights_metadata
        payload.setdefault("formats", book.get("formats") or ["Ebook"])
        payload.setdefault("benefits", book.get("benefits") or [])
        payload.setdefault("who_for", book.get("who_for") or [])
        payload.setdefault("learnings", book.get("learnings") or [])
        return self.request("PUT", f"/admin/books/{book['slug']}", json=payload)


def compliance_rights(book: dict[str, Any], source: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    rights = {**source, **(book.get("rights_metadata") or {})}
    combined = " ".join(
        str(rights.get(key) or "")
        for key in ("rights_basis", "source_license", "license_notes", "source_type")
    ).lower()
    if not rights:
        return False, "missing rights metadata/source evidence", {}
    if any(term in combined for term in ("cc-nc", "non-commercial", "noncommercial", "all rights reserved", "unclear")):
        return False, "rights text contains restricted/unclear commercial terms", rights
    original = any(term in combined for term in ("author-owned", "reo enterprise", "copyright owner", "original"))
    public_domain = "public domain" in combined
    commercial = rights.get("commercial_use_allowed") is True or "commercial" in combined
    if not (original or public_domain or commercial):
        return False, "commercial-use clearance not proven", rights
    if public_domain and not original:
        if not rights.get("author_death_year") or not rights.get("original_publication_year"):
            return False, "public-domain claim missing author death/publication year", rights
    return True, "rights metadata passes automated commercial-use gate", rights


def chapter_index_gate(book: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    chapters = sorted(book.get("chapters") or [], key=lambda row: row.get("order", 0))
    if not chapters:
        return False, ["no chapters"]
    orders = [chapter.get("order") for chapter in chapters]
    if orders != list(range(len(chapters))):
        issues.append("chapter order fields are not contiguous 0..n-1")
    ids = [str(chapter.get("id") or "") for chapter in chapters]
    if len([cid for cid in ids if cid]) != len(set(cid for cid in ids if cid)):
        issues.append("duplicate chapter ids")
    titles = [str(chapter.get("title") or "").strip() for chapter in chapters]
    if any(not title for title in titles):
        issues.append("blank chapter title")
    prefixed = [CHAPTER_PREFIX_RE.match(title) for title in titles]
    if all(prefixed):
        wrong = [
            f"{index + 1}:{title}"
            for index, (title, match) in enumerate(zip(titles, prefixed))
            if match and int(match.group(1)) != index + 1
        ]
        if wrong:
            issues.append("Chapter N prefix mismatch: " + "; ".join(wrong[:6]))
    elif any(prefixed):
        issues.append("mixed Chapter N-prefixed and unprefixed chapter titles")
    title_counts = Counter(titles)
    duplicate_titles = [title for title, count in title_counts.items() if title and count > 1]
    if duplicate_titles:
        issues.append("duplicate chapter titles: " + "; ".join(duplicate_titles[:6]))
    ordinals = [ordinal_from_title(title) for title in titles]
    useful_ordinals = [value for value in ordinals if value is not None]
    if len(useful_ordinals) >= 4:
        # Treat repeated part-local ordinals as acceptable when titles contain part/volume separators.
        has_parts = any("/" in title or "খণ্ড" in title or re.search(r"\b(part|book|volume)\b", title, re.I) for title in titles)
        if not has_parts and len(set(useful_ordinals)) == len(useful_ordinals):
            expected = list(range(1, len(useful_ordinals) + 1))
            if useful_ordinals != expected:
                issues.append(f"chapter ordinal sequence appears scrambled: {useful_ordinals[:20]}")
    return not issues, issues


def content_gate(book: dict[str, Any], prepared_text: str | None) -> tuple[bool, list[str], int, int]:
    issues: list[str] = []
    chapters = sorted(book.get("chapters") or [], key=lambda row: row.get("order", 0))
    chapter_rows = chapter_texts(book, include_titles=True)
    full_text = clean_text("\n\n".join(text for _, text in chapter_rows if text))
    words = word_tokens(full_text)
    if len(words) < 120:
        issues.append(f"very short reader text: {len(words)} words")
    for index, chapter in enumerate(chapters):
        status = chapter.get("processing_status") or "ready"
        if status != "ready":
            issues.append(f"chapter not ready: {chapter.get('title') or chapter.get('id')}={status}")
        body = html_to_text(str(chapter.get("content") or ""))
        if len(word_tokens(body)) == 0:
            issues.append(f"empty chapter body at {index + 1}: {chapter.get('title') or chapter.get('id')}")
    body_hashes = [
        sha_text(html_to_text(str(chapter.get("content") or "")))
        for chapter in chapters
        if len(word_tokens(html_to_text(str(chapter.get("content") or "")))) > 80
    ]
    duplicates = [hash_value for hash_value, count in Counter(body_hashes).items() if count > 1]
    if duplicates:
        issues.append(f"duplicate substantial chapter bodies: {len(duplicates)} hash group(s)")
    if FORBIDDEN_READER_TERMS.search(full_text):
        issues.append("reader-facing source/license/repository boilerplate detected")
    if prepared_text:
        live_norm = normalized_compare(full_text)
        source_norm = normalized_compare(prepared_text)
        if source_norm and live_norm:
            coverage = len(live_norm) / max(1, len(source_norm))
            overlap_probe = live_norm[:800] in source_norm or source_norm[:800] in live_norm
            if coverage < 0.88 or coverage > 1.18:
                issues.append(f"prepared-source length coverage outside tolerance: {coverage:.2f}")
            if len(source_norm) > 2000 and not overlap_probe:
                issues.append("prepared-source opening text does not match live reader opening")
    else:
        issues.append("no local prepared/source text evidence for automated full-content comparison")
    return not issues, issues, len(words), len(full_text)


def audio_gate(book: dict[str, Any], session: requests.Session) -> tuple[bool, list[str]]:
    issues: list[str] = []
    assets = book.get("audiobook_assets") if isinstance(book.get("audiobook_assets"), dict) else {}
    enabled = bool(book.get("audiobook_enabled"))
    if not enabled:
        return False, ["audiobook not enabled/mapped"]
    required = ["mp3", "timestamps", "vtt", "chapters", "meta"]
    missing = [key for key in required if not str(assets.get(key) or "").strip()]
    if missing:
        return False, [f"missing audiobook assets: {', '.join(missing)}"]
    for key in required:
        url = str(assets[key])
        try:
            if key == "mp3":
                response = session.get(url, headers={"Range": "bytes=0-1023"}, timeout=30, stream=True)
                if response.status_code not in {200, 206}:
                    issues.append(f"mp3 returned HTTP {response.status_code}")
                response.close()
            else:
                response = session.get(url, timeout=30)
                if response.status_code != 200:
                    issues.append(f"{key} returned HTTP {response.status_code}")
        except Exception as exc:
            issues.append(f"{key} fetch failed: {exc}")
    try:
        timestamps = session.get(str(assets["timestamps"]), timeout=60).json()
        if not isinstance(timestamps, list) or not timestamps:
            issues.append("timestamps JSON empty/invalid")
        else:
            monotonic = all(
                int(timestamps[i].get("start_ms", 0))
                <= int(timestamps[i].get("end_ms", 0))
                <= int(timestamps[i + 1].get("start_ms", 0))
                for i in range(len(timestamps) - 1)
            )
            if not monotonic:
                issues.append("timestamps are not monotonic")
            book_words = len(word_tokens(full_reader_text(book, include_titles=True)))
            tolerance = max(35, int(book_words * 0.12))
            delta = abs(len(timestamps) - book_words)
            if book_words and delta > tolerance:
                issues.append(f"timestamp/reader-word mismatch: timestamps={len(timestamps)} words={book_words} tolerance={tolerance}")
    except Exception as exc:
        issues.append(f"timestamp validation failed: {exc}")
    try:
        chapters = session.get(str(assets["chapters"]), timeout=30).json()
        expected_count = len(book.get("chapters") or [])
        if not isinstance(chapters, list) or len(chapters) != expected_count:
            issues.append(f"audio chapter index count mismatch: audio={len(chapters) if isinstance(chapters, list) else 'invalid'} book={expected_count}")
    except Exception as exc:
        issues.append(f"audio chapters validation failed: {exc}")
    provider = str(book.get("audiobook_provider") or "").strip()
    voice = str(book.get("audiobook_voice") or "").strip()
    if not provider or not voice:
        issues.append("audiobook provider/voice metadata missing")
    return not issues, issues


def reader_gate(book: dict[str, Any], api_url: str, frontend_url: str, session: requests.Session) -> tuple[bool, list[str]]:
    issues: list[str] = []
    slug = book["slug"]
    for url in [f"{normalize_api_url(api_url)}/books/{slug}", f"{normalize_api_url(api_url)}/books/{slug}/chapters"]:
        try:
            response = session.get(url, timeout=30)
            expected = 200 if book.get("is_published") else 404
            if response.status_code != expected:
                issues.append(f"{url} returned {response.status_code}, expected {expected}")
        except Exception as exc:
            issues.append(f"{url} failed: {exc}")
    if book.get("is_published"):
        for path in [f"/book/{slug}", f"/reader/{slug}"]:
            try:
                response = session.get(f"{frontend_url.rstrip('/')}{path}", timeout=30)
                if response.status_code != 200:
                    issues.append(f"{path} returned HTTP {response.status_code}")
            except Exception as exc:
                issues.append(f"{path} failed: {exc}")
    return not issues, issues


def source_for_book(book: dict[str, Any], by_slug: dict[str, dict[str, Any]], by_title_author: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    slug = str(book.get("slug") or "").strip()
    return (
        by_slug.get(slug)
        or by_slug.get(slug.upper())
        or by_title_author.get((str(book.get("title") or "").strip(), str(book.get("author") or "").strip()))
        or {}
    )


def source_slug_candidates(book: dict[str, Any]) -> Iterable[str]:
    slug = str(book.get("slug") or "").lower()
    yield slug
    if slug.startswith("bn-"):
        yield slug.replace("bn-", "BN-", 1)
    book_id = str(book.get("id") or "").lower()
    if book_id:
        yield book_id


def audit_one(
    book: dict[str, Any],
    args: argparse.Namespace,
    source_by_slug: dict[str, dict[str, Any]],
    source_by_title_author: dict[tuple[str, str], dict[str, Any]],
    prepared_texts: dict[str, str],
) -> BookAudit:
    session = requests.Session()
    audit = BookAudit(
        slug=str(book.get("slug") or ""),
        title=str(book.get("title") or ""),
        author=str(book.get("author") or ""),
        is_published=bool(book.get("is_published")),
        category_slug=str(book.get("category_slug") or ""),
        language="ben" if BENGALI_RE.search(full_reader_text(book, include_titles=False)) else "en",
        chapter_count=len(book.get("chapters") or []),
        audiobook_enabled=bool(book.get("audiobook_enabled")),
    )
    source = source_for_book(book, source_by_slug, source_by_title_author)
    prepared = None
    for slug in source_slug_candidates(book):
        if slug in prepared_texts:
            prepared = prepared_texts[slug]
            break
    if not prepared:
        prepared = prepared_texts.get(str(book.get("slug") or "").lower())

    rights_ok, rights_detail, rights_payload = compliance_rights(book, source)
    audit.gate("legal_compliance", rights_ok, rights_detail)
    cover_ok = bool(book.get("cover_image_url") or book.get("cover_url")) and bool(book.get("back_cover_image_url") or book.get("back_cover_url"))
    audit.gate("cover_package", cover_ok, "front/back covers present" if cover_ok else "front or back cover missing")
    index_ok, index_issues = chapter_index_gate(book)
    audit.gate("chapter_index_health", index_ok, "; ".join(index_issues or ["ok"]))
    content_ok, content_issues, words_count, chars_count = content_gate(book, prepared)
    audit.word_count = words_count
    audit.char_count = chars_count
    audit.gate("content_full_final", content_ok, "; ".join(content_issues or ["ok"]))
    audio_ok, audio_issues = audio_gate(book, session)
    audit.gate("audiobook_sync", audio_ok, "; ".join(audio_issues or ["ok"]))
    reader_ok, reader_issues = reader_gate(book, args.api_url, args.frontend_url, session)
    audit.gate("reader_render_smoke", reader_ok, "; ".join(reader_issues or ["ok"]))
    ux_ok = reader_ok and cover_ok and index_ok and bool(book.get("short_description")) and bool(book.get("description"))
    audit.gate("ux_9_9_candidate", ux_ok, "automated UX smoke passed" if ux_ok else "metadata/render/index gate prevents 9.9+ automated UX candidate")
    audit.finalize()
    audit._rights_payload = rights_payload  # type: ignore[attr-defined]
    return audit


def render_markdown(results: list[BookAudit], published: list[str], report_json: Path, report_csv: Path) -> str:
    counts = Counter("published" if row.is_published else "draft" for row in results)
    green = [row for row in results if row.green]
    no_go = [row for row in results if not row.green]
    lines = [
        "# Earnalism Live Library GO-GREEN Audit",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Counts",
        "",
        f"- Uploaded total: **{len(results)}**",
        f"- Published: **{counts['published']}**",
        f"- Draft: **{counts['draft']}**",
        f"- GO-GREEN: **{len(green)}**",
        f"- NO-GO / needs work: **{len(no_go)}**",
        f"- Published now: **{len(published)}**",
        "",
        "## Artifacts",
        "",
        f"- JSON: `{report_json}`",
        f"- CSV: `{report_csv}`",
        "",
    ]
    if published:
        lines.extend(["## Published Now", ""])
        lines.extend(f"- `{slug}`" for slug in published)
        lines.append("")
    fail_counter: Counter[str] = Counter()
    for row in no_go:
        for gate in row.gates:
            if not gate.ok:
                fail_counter[gate.name] += 1
    lines.extend(["## Failure Summary", ""])
    for name, count in fail_counter.most_common():
        lines.append(f"- `{name}`: {count}")
    lines.append("")
    lines.extend(["## Book Results", ""])
    for row in sorted(results, key=lambda item: (not item.green, item.slug)):
        status = "GO-GREEN" if row.green else "NO-GO"
        pub = "published" if row.is_published else "draft"
        lines.extend(
            [
                f"### {row.title} (`{row.slug}`)",
                "",
                f"- Status: **{status}** ({pub})",
                f"- Author: {row.author}",
                f"- Chapters: {row.chapter_count}; words: {row.word_count}; audiobook: `{str(row.audiobook_enabled).lower()}`",
            ]
        )
        failed = [gate for gate in row.gates if not gate.ok]
        if failed:
            lines.append("- Failed gates:")
            lines.extend(f"  - `{gate.name}`: {gate.detail}" for gate in failed[:8])
        lines.append("")
    return "\n".join(lines)


def write_reports(results: list[BookAudit], published: list[str], run_dir: Path) -> tuple[Path, Path, Path]:
    report_json = run_dir / "live_library_green_audit.json"
    report_csv = run_dir / "live_library_green_audit.csv"
    report_md = run_dir / "live_library_green_audit.md"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "uploaded_total": len(results),
            "published": sum(1 for row in results if row.is_published),
            "draft": sum(1 for row in results if not row.is_published),
            "go_green": sum(1 for row in results if row.green),
            "no_go": sum(1 for row in results if not row.green),
            "published_now": len(published),
        },
        "published_now": published,
        "results": [
            {
                "slug": row.slug,
                "title": row.title,
                "author": row.author,
                "is_published": row.is_published,
                "published_now": row.published_now,
                "category_slug": row.category_slug,
                "language": row.language,
                "chapter_count": row.chapter_count,
                "word_count": row.word_count,
                "char_count": row.char_count,
                "audiobook_enabled": row.audiobook_enabled,
                "green": row.green,
                "gates": [gate.__dict__ for gate in row.gates],
                "warnings": row.warnings,
                "fixes": row.fixes,
            }
            for row in results
        ],
    }
    report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with report_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["slug", "title", "author", "published", "green", "chapters", "words", "audiobook_enabled", "failed_gates"])
        for row in results:
            failed = "; ".join(f"{gate.name}: {gate.detail}" for gate in row.gates if not gate.ok)
            writer.writerow([row.slug, row.title, row.author, row.is_published, row.green, row.chapter_count, row.word_count, row.audiobook_enabled, failed])
    report_md.write_text(render_markdown(results, published, report_json, report_csv), encoding="utf-8")
    return report_json, report_csv, report_md


def publish_allowed() -> bool:
    return str(os.environ.get("PUBLISH_LIVE") or "").lower() in {"1", "true", "yes"} and str(os.environ.get("HUMAN_APPROVED") or "").lower() in {"1", "true", "yes"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit every live Earnalism book for GO-GREEN readiness.")
    parser.add_argument("--api-url", default=os.environ.get("EARNALISM_API_URL", DEFAULT_API_URL))
    parser.add_argument("--frontend-url", default=os.environ.get("EARNALISM_FRONTEND_URL", DEFAULT_FRONTEND_URL))
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--env-file", action="append", type=Path, default=[ROOT / ".secrets/earnalism-import.env"])
    parser.add_argument("--publish-green", action="store_true", help="Publish GO-GREEN drafts only when PUBLISH_LIVE=1 and HUMAN_APPROVED=1 are also set.")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for env_file in args.env_file:
        load_env(env_file)
    run_dir = args.output_root / utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)

    client = EarnalismClient(args.api_url)
    client.login()
    summaries = client.summaries()
    if args.limit:
        summaries = summaries[: args.limit]
    counts_before = Counter(bool(row.get("is_published")) for row in summaries)
    print(f"Uploaded total: {len(summaries)}")
    print(f"Published: {counts_before[True]}")
    print(f"Draft: {counts_before[False]}")

    print("Fetching full admin book records...")
    books: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        future_map = {pool.submit(client.book, str(row.get("slug"))): row for row in summaries if row.get("slug")}
        for future in as_completed(future_map):
            books.append(future.result())
    books.sort(key=lambda row: str(row.get("slug") or ""))

    source_by_slug, source_by_title_author = load_manifest_sources()
    prepared_texts = load_prepared_texts()
    print(f"Loaded {len(source_by_slug)} source rows and {len(prepared_texts)} prepared source texts.")
    print("Auditing books...")
    results: list[BookAudit] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [
            pool.submit(audit_one, book, args, source_by_slug, source_by_title_author, prepared_texts)
            for book in books
        ]
        for index, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            if index % 10 == 0 or index == len(futures):
                print(f"  audited {index}/{len(futures)}")
    results.sort(key=lambda row: row.slug)

    published: list[str] = []
    if args.publish_green:
        if not publish_allowed():
            print("Publish requested but blocked: set PUBLISH_LIVE=1 and HUMAN_APPROVED=1.")
        else:
            print("Publishing GO-GREEN drafts...")
            book_by_slug = {str(book.get("slug")): book for book in books}
            for row in results:
                if not row.green or row.is_published:
                    continue
                rights_payload = getattr(row, "_rights_payload", {}) or (book_by_slug[row.slug].get("rights_metadata") or {})
                refreshed = client.publish(book_by_slug[row.slug], rights_payload)
                row.published_now = True
                row.is_published = True
                published.append(str(refreshed.get("slug") or row.slug))

    report_json, report_csv, report_md = write_reports(results, published, run_dir)
    green_count = sum(1 for row in results if row.green)
    print("\nLive library GO-GREEN audit")
    print("===========================")
    print(f"Uploaded total: {len(results)}")
    print(f"Published: {sum(1 for row in results if row.is_published)}")
    print(f"Draft: {sum(1 for row in results if not row.is_published)}")
    print(f"GO-GREEN: {green_count}")
    print(f"NO-GO: {len(results) - green_count}")
    print(f"Published now: {len(published)}")
    print(f"Report: {report_md}")
    print(f"JSON: {report_json}")
    print(f"CSV: {report_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
