#!/usr/bin/env python3
"""Audit live Bengali books for source, rights, chapter, and audio sync issues."""

from __future__ import annotations

import difflib
import html.parser
import importlib.util
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import requests


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "output/bengali_library_audit"
API_URL = "https://api.theearnalism.com/api"
SOURCE_MANIFESTS = [
    ROOT / "book_import_manifest.json",
    ROOT / "scripts/audit_data/bengali_live_source_evidence.json",
    ROOT / "output/source_repair/20260602T192021Z/source_repaired_404_manifest.json",
    ROOT / "output/bengali_source_repair/20260603T084835Z/bengali_source_repaired_upload_manifest.json",
    ROOT / "output/bengali_wikisource_deep_repair/20260604T163550Z/bengali_wikisource_deep_repair_manifest.json",
]
SOURCE_REPORTS = [
    ROOT / "output/source_repair/20260602T192021Z/source_repair_report.json",
    ROOT / "output/bengali_source_repair/20260603T084835Z/bengali_source_repair_report.json",
    ROOT / "output/bengali_wikisource_deep_repair/20260604T163550Z/bengali_wikisource_deep_repair_report.json",
]
FORBIDDEN_READER_TERMS = re.compile(
    r"Project Gutenberg|Gutenberg\\.org|PGLAF|Creative Commons|CC BY|Wikisource|উইকিসংকলন",
    re.IGNORECASE,
)
BENGALI_RE = re.compile(r"[\u0980-\u09ff]")


class TextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.skip += 1
        if tag in {"p", "div", "section", "article", "h1", "h2", "h3", "li", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.skip:
            self.skip -= 1
        if tag in {"p", "div", "section", "article", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)

    def text(self) -> str:
        return clean_text("".join(self.parts))


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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
        if key.strip() not in {"ADMIN_EMAIL", "ADMIN_PASSWORD", "EARNALISM_ADMIN_TOKEN"}:
            continue
        import os

        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def clean_text(value: str) -> str:
    value = (value or "").replace("\ufeff", "").replace("\u200c", "").replace("\u200d", "")
    value = re.sub(r"[ \t\xa0]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def normalized_for_compare(value: str) -> str:
    value = clean_text(value)
    value = re.sub(r"(?m)^Chapter\\s+\\d+\\.\\s*", "", value)
    value = re.sub(r"(?m)^পৃষ্ঠা\\s+\\d+.*$", "", value)
    value = re.sub(r"(?m)^Page\\s+\\d+.*$", "", value)
    value = re.sub(r"[\\s\\W_]+", "", value, flags=re.UNICODE)
    return value.casefold()


def normalize_word(value: str) -> str:
    return re.sub(r"[^\w\u0980-\u09ff]+", "", str(value or "")).casefold()


def words(value: str) -> list[str]:
    tokens: list[str] = []
    for token in re.findall(r"\S+", value or ""):
        token = re.sub(r"[^\p{L}\p{N}\u0980-\u09ff]+", "", token) if False else re.sub(r"[^\w\u0980-\u09ff]+", "", token)
        if token:
            tokens.append(token.casefold())
    return tokens


def html_to_text(value: str) -> str:
    parser = TextExtractor()
    parser.feed(value or "")
    return parser.text()


def chapter_reader_text(book: dict[str, Any], include_titles: bool = True) -> str:
    chunks: list[str] = []
    for chapter in sorted(book.get("chapters") or [], key=lambda row: row.get("order", 0)):
        title = str(chapter.get("title") or "").strip()
        if include_titles and title and title.lower() != "full text":
            chunks.append(title)
        body = html_to_text(str(chapter.get("content") or ""))
        if body:
            chunks.append(body)
    return clean_text("\n\n".join(chunks))


def source_page_title(url: str) -> str:
    parsed = urlparse(url or "")
    return unquote(parsed.path.removeprefix("/wiki/")).replace("_", " ")


def canonical_url(value: Any) -> str:
    text = str(value or "").strip()
    if "](" in text and text.endswith(")"):
        return text.split("](", 1)[1][:-1].strip()
    markdown = re.search(r"\((https?://[^)]+)\)", text)
    if markdown:
        return markdown.group(1).strip()
    bare = re.search(r"https?://\S+", text)
    if bare:
        return bare.group(0).rstrip(").,;")
    return text


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def source_rows() -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    by_slug: dict[str, dict[str, Any]] = {}
    by_title_author: dict[tuple[str, str], dict[str, Any]] = {}
    for path in SOURCE_MANIFESTS:
        if not path.exists():
            continue
        data = load_json(path)
        rows = data.get("books", data) if isinstance(data, dict) else data
        for row in rows:
            if not isinstance(row, dict):
                continue
            if row.get("source_url"):
                row = {**row, "source_url": canonical_url(row.get("source_url"))}
            slug = str(row.get("slug") or "").strip()
            if slug:
                by_slug[slug] = row
            key = (str(row.get("title") or "").strip(), str(row.get("author") or "").strip())
            if key[0] and key[1]:
                by_title_author[key] = row
    for path in SOURCE_REPORTS:
        if not path.exists():
            continue
        data = load_json(path)
        for row in data.get("decisions", []) if isinstance(data, dict) else []:
            if row.get("status") not in {None, "selected"} and row.get("decision") not in {"selected", None}:
                continue
            title = str(row.get("title") or "").strip()
            author = str(row.get("author") or "").strip()
            source_url = row.get("selected_source_url") or row.get("source_url")
            if title and author and source_url:
                existing = by_title_author.get((title, author), {})
                by_title_author[(title, author)] = {**existing, "source_url": canonical_url(source_url)}
    return by_slug, by_title_author


def rights_payload(book: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    payload = {**source}
    for key in ("title", "author"):
        payload.setdefault(key, book.get(key))
    if payload.get("attribution_notice") and not payload.get("required_attribution"):
        payload["required_attribution"] = payload["attribution_notice"]
    return payload


def wrong_work_title_markers(book_title: str, chapter_titles: list[str]) -> list[str]:
    """Flag collection subwork titles, without treating generic chapter labels as errors."""
    markers: list[str] = []
    for title in chapter_titles:
        cleaned = re.sub(r"^Chapter\s+\d+\.\s*", "", title or "").strip()
        if " / " not in cleaned:
            continue
        work_name = cleaned.split(" / ", 1)[0].strip()
        if work_name.endswith("খণ্ড"):
            continue
        if work_name and book_title and work_name != book_title:
            markers.append(title)
    return markers


def compare_text(a: str, b: str) -> dict[str, Any]:
    na = normalized_for_compare(a)
    nb = normalized_for_compare(b)
    if not na or not nb:
        return {"status": "unknown", "ratio": 0.0, "reader_chars": len(na), "source_chars": len(nb)}
    shorter = min(len(na), len(nb))
    longer = max(len(na), len(nb))
    length_ratio = shorter / longer if longer else 0
    if na == nb or (len(na) > 1000 and na in nb) or (len(nb) > 1000 and nb in na):
        return {
            "status": "pass" if length_ratio >= 0.88 else "review",
            "ratio": 1.0,
            "length_ratio": round(length_ratio, 4),
            "reader_chars": len(na),
            "source_chars": len(nb),
            "window_ratios": [1.0, 1.0, 1.0],
        }

    def best_window_ratio(window: str, haystack: str) -> float:
        if not window or not haystack:
            return 0.0
        if window in haystack:
            return 1.0
        sample = haystack[:12000]
        if len(haystack) > 24000:
            middle = max(0, len(haystack) // 2 - 6000)
            sample += haystack[middle:middle + 12000]
            sample += haystack[-12000:]
        return difflib.SequenceMatcher(None, window, sample, autojunk=False).ratio()

    window_size = min(5000, max(1000, len(na) // 20))
    positions = [0, max(0, len(na) // 2 - window_size // 2), max(0, len(na) - window_size)]
    ratios = [best_window_ratio(na[pos:pos + window_size], nb) for pos in positions]
    ratio = sum(ratios) / len(ratios)
    status = "pass" if ratio >= 0.90 and length_ratio >= 0.88 else "review"
    return {
        "status": status,
        "ratio": round(ratio, 4),
        "length_ratio": round(length_ratio, 4),
        "reader_chars": len(na),
        "source_chars": len(nb),
        "window_ratios": [round(value, 4) for value in ratios],
    }


def fetch_source_text(importer: Any, session: requests.Session, source: dict[str, Any]) -> tuple[str, str]:
    path = source.get("prepared_text_path")
    if path and Path(path).exists():
        return Path(path).read_text(encoding="utf-8"), "prepared_text"
    url = source.get("source_url")
    source_type = source.get("source_type") or "wikisource_bengali_html"
    if not url:
        return "", "missing"
    body, _log = importer.download_source(url, source_type)
    raw = importer.decode_utf8(body)
    text, _warnings = importer.sanitize_text(raw, {**source, "source_url": url, "source_type": source_type})
    return text, "live_source_fetch"


def audit_audio(book: dict[str, Any], reader_text: str, session: requests.Session) -> dict[str, Any]:
    assets = book.get("audiobook_assets") or {}
    enabled = bool(book.get("audiobook_enabled") or book.get("generate_audiobook") or assets)
    if not enabled:
        return {"status": "not_configured", "detail": "audiobook disabled/not onboarded"}
    missing = [key for key in ("mp3", "timestamps") if not assets.get(key)]
    if missing:
        return {"status": "fail", "detail": f"missing assets: {', '.join(missing)}"}
    try:
        mp3 = session.head(assets["mp3"], timeout=30, allow_redirects=True)
        mp3_ok = 200 <= mp3.status_code < 400
    except Exception as exc:
        mp3_ok = False
        mp3 = type("R", (), {"status_code": str(exc)})()
    try:
        data = session.get(assets["timestamps"], timeout=60)
        data.raise_for_status()
        timestamps = data.json()
    except Exception as exc:
        return {"status": "fail", "detail": f"timestamp fetch/parse failed: {exc}", "mp3_ok": mp3_ok}
    if not isinstance(timestamps, list) or not timestamps:
        return {"status": "fail", "detail": "timestamps empty", "mp3_ok": mp3_ok}
    monotonic = all(
        int(timestamps[i].get("start_ms", 0)) <= int(timestamps[i].get("end_ms", 0)) <= int(timestamps[i + 1].get("start_ms", 0))
        for i in range(len(timestamps) - 1)
    )
    text_words = words(reader_text)
    ts_words = [words(str(item.get("word") or item.get("text") or ""))[0] for item in timestamps if words(str(item.get("word") or item.get("text") or ""))]
    expected = len(text_words)
    tolerance = max(25, int(expected * 0.08))
    count_ok = expected > 0 and abs(len(timestamps) - expected) <= tolerance
    window = min(40, len(text_words), len(ts_words))
    best = 0
    best_offset = 0
    max_visible_start = max(0, min(len(text_words) - window, 200))
    max_audio_start = max(0, min(len(ts_words) - window, 200))
    for visible_start in range(max_visible_start + 1):
        for audio_start in range(max_audio_start + 1):
            if text_words[visible_start] != ts_words[audio_start]:
                continue
            score = sum(1 for idx in range(window) if ts_words[audio_start + idx] == text_words[visible_start + idx])
            if score > best:
                best = score
                best_offset = audio_start - visible_start
            if score == window:
                break
        if best == window:
            break
    alignment_ratio = best / window if window else 0
    status = "pass" if mp3_ok and monotonic and count_ok and alignment_ratio >= 0.72 else "review"
    return {
        "status": status,
        "mp3_ok": mp3_ok,
        "mp3_status": getattr(mp3, "status_code", ""),
        "monotonic": monotonic,
        "timestamp_count": len(timestamps),
        "expected_text_units": expected,
        "count_delta": len(timestamps) - expected,
        "alignment_ratio_first_window": round(alignment_ratio, 4),
        "audio_word_offset": best_offset,
    }


def is_bengali(book: dict[str, Any]) -> bool:
    return (book.get("language") or "").lower() in {"bn", "ben", "bengali"} or bool(BENGALI_RE.search(str(book.get("title") or "")))


def main() -> int:
    load_env(ROOT / ".secrets/earnalism-import.env")
    production = load_module(ROOT / "scripts/book_production_workflow.py", "book_production_workflow_for_audit")
    importer = load_module(ROOT / "scripts/import_books.py", "import_books_for_bengali_audit")
    api = production.EarnalismApi("https://api.theearnalism.com")
    api.login()
    session = requests.Session()
    session.headers["User-Agent"] = "EarnalismBengaliLibraryAudit/1.0"
    by_slug, by_title_author = source_rows()
    summaries = [book for book in api.get_admin_books() if is_bengali(book)]

    out_dir = OUTPUT_ROOT / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    counters = Counter()

    for summary in sorted(summaries, key=lambda row: row.get("slug", "")):
        slug = summary["slug"]
        book = api.get_admin_book(slug)
        source = by_slug.get(slug) or by_title_author.get((book.get("title", ""), book.get("author", ""))) or {}
        reader_text = chapter_reader_text(book)
        reader_content_text = chapter_reader_text(book, include_titles=False)
        source_text = ""
        source_mode = "missing"
        source_compare = {"status": "unknown", "ratio": 0.0}
        if source:
            try:
                source_text, source_mode = fetch_source_text(importer, session, source)
                source_compare = compare_text(chapter_reader_text(book), source_text)
            except Exception as exc:
                source_mode = f"fetch_failed: {exc}"
                source_compare = {"status": "review", "detail": str(exc), "ratio": 0.0}

        chapters = sorted(book.get("chapters") or [], key=lambda row: row.get("order", 0))
        titles = [str(ch.get("title") or "").strip() for ch in chapters]
        norm_titles = [re.sub(r"^Chapter\\s+\\d+\\.\\s*", "", title).strip().casefold() for title in titles]
        duplicate_titles = sorted({title for title, count in Counter(norm_titles).items() if title and count > 1})
        order_ok = [ch.get("order") for ch in chapters] == list(range(len(chapters)))
        foreign_title_markers = wrong_work_title_markers(str(book.get("title") or ""), titles)
        reader_forbidden = bool(FORBIDDEN_READER_TERMS.search(reader_text))

        rights_ok = False
        rights_errors: list[str] = []
        rights_warnings: list[str] = []
        if source:
            rights_ok, _rights_log, rights_warnings, rights_errors = importer.commercial_rights_validation(rights_payload(book, source))
        else:
            rights_errors = ["source/rights evidence not found in local manifests or live admin fields"]

        audio = audit_audio(book, reader_content_text, session)
        row = {
            "slug": slug,
            "title": book.get("title"),
            "author": book.get("author"),
            "is_published": book.get("is_published"),
            "chapter_count": len(chapters),
            "chapter_order_ok": order_ok,
            "duplicate_chapter_titles": duplicate_titles,
            "foreign_title_markers": foreign_title_markers,
            "reader_forbidden_source_terms": reader_forbidden,
            "source_evidence": {
                "found": bool(source),
                "mode": source_mode,
                "source_url": source.get("source_url", ""),
                "source_page_title": source_page_title(source.get("source_url", "")),
            },
            "source_compare": source_compare,
            "rights": {
                "status": "pass" if rights_ok else "review",
                "errors": rights_errors,
                "warnings": rights_warnings,
                "author_death_year": source.get("author_death_year"),
                "original_publication_year": source.get("original_publication_year"),
            },
            "audio_sync": audio,
        }
        row["overall_status"] = "pass"
        if (
            not order_ok
            or duplicate_titles
            or foreign_title_markers
            or reader_forbidden
            or row["rights"]["status"] != "pass"
            or source_compare.get("status") == "review"
            or audio.get("status") in {"fail", "review"}
        ):
            row["overall_status"] = "review"
        if audio.get("status") == "not_configured":
            row["overall_status"] = "review"
        counters[row["overall_status"]] += 1
        counters[f"audio_{audio.get('status')}"] += 1
        counters[f"rights_{row['rights']['status']}"] += 1
        counters[f"source_{source_compare.get('status')}"] += 1
        rows.append(row)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "book_count": len(rows),
        "summary": dict(counters),
        "books": rows,
    }
    json_path = out_dir / "bengali_library_audit_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = ["# Bengali Library Audit", "", f"Generated: {report['generated_at']}", "", "## Summary", ""]
    for key, value in sorted(counters.items()):
        md.append(f"- {key}: {value}")
    md.extend(["", "## Review Items", ""])
    for row in rows:
        if row["overall_status"] == "pass":
            continue
        md.append(f"### {row['title']} (`{row['slug']}`)")
        md.append(f"- chapters: {row['chapter_count']}, order_ok={row['chapter_order_ok']}")
        if row["duplicate_chapter_titles"]:
            md.append(f"- duplicate chapter titles: {', '.join(row['duplicate_chapter_titles'])}")
        if row["foreign_title_markers"]:
            md.append(f"- possible wrong-title chapter markers: {', '.join(row['foreign_title_markers'][:5])}")
        md.append(f"- source: {row['source_evidence']['mode']} ratio={row['source_compare'].get('ratio')}")
        md.append(f"- rights: {row['rights']['status']} {'; '.join(row['rights']['errors'])}")
        md.append(f"- audio: {row['audio_sync'].get('status')} {row['audio_sync'].get('detail', '')}")
        md.append("")
    md_path = out_dir / "bengali_library_audit_report.md"
    md_path.write_text("\n".join(md), encoding="utf-8")
    print(json_path)
    print(md_path)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
