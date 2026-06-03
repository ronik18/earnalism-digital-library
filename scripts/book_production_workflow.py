#!/usr/bin/env python3
"""Earnalism draft-to-production orchestrator.

This script coordinates deterministic book production steps while keeping final
publishing behind an explicit approval flag. It intentionally reuses the
existing importer and audio generator instead of duplicating their provider
logic.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import requests
except ImportError as exc:  # pragma: no cover - local environment guard
    raise SystemExit("Missing dependency: requests. Install project/backend requirements first.") from exc


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_API_URL = "https://api.theearnalism.com"
DEFAULT_FRONTEND_URL = "https://theearnalism.com"
DEFAULT_MAX_PUBLISH_CHAPTERS = int(os.environ.get("EARNALISM_MAX_PUBLISH_CHAPTERS", "80"))
DEFAULT_MAX_PUBLISH_CHARS = int(os.environ.get("EARNALISM_MAX_PUBLISH_CHARS", "1800000"))
DEFAULT_MAX_PUBLISH_CHAPTER_CHARS = int(os.environ.get("EARNALISM_MAX_PUBLISH_CHAPTER_CHARS", "120000"))
BOOK_IN_FIELDS = {
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
    "is_published",
    "slug",
}
RIGHTS_METADATA_FIELDS = {
    "title",
    "author",
    "author_death_year",
    "original_publication_year",
    "source_url",
    "source_type",
    "source_license",
    "rights_basis",
    "commercial_use_allowed",
    "india_rights_status",
    "us_rights_status",
    "required_attribution",
    "attribution_required",
    "copyright_owner",
    "license_notes",
}


@dataclass
class GateResult:
    name: str
    ok: bool
    detail: str


@dataclass
class BookProductionResult:
    slug: str
    title: str
    language: str = ""
    verdict: str = "NO-GO"
    gates: List[GateResult] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    audio_assets: Dict[str, str] = field(default_factory=dict)
    published: bool = False
    audiobook_enabled: bool = False

    def add_gate(self, name: str, ok: bool, detail: str) -> None:
        self.gates.append(GateResult(name, ok, detail))

    def finalize(self) -> None:
        self.verdict = "GO" if self.gates and all(g.ok for g in self.gates) else "NO-GO"


class HTMLTextExtractor(HTMLParser):
    """Extract readable text from stored chapter HTML without pulling scripts."""

    BLOCK_TAGS = {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag in {"script", "style"}:
            self.skip_depth += 1
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        value = "".join(self.parts)
        value = value.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
        value = re.sub(r"[ \t]+", " ", value)
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value.strip()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value.startswith("~/"):
            value = str(Path.home() / value[2:])
        os.environ.setdefault(key.strip(), value)


def normalize_api_url(value: str) -> str:
    value = (value or DEFAULT_API_URL).rstrip("/")
    return value if value.endswith("/api") else f"{value}/api"


def normalize_slug(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^\w\s\-\u0980-\u09ff]+", "", value, flags=re.UNICODE)
    value = re.sub(r"[\s_]+", "-", value)
    return re.sub(r"-{2,}", "-", value).strip("-") or "book"


def infer_language(text: str, fallback: str = "") -> str:
    if fallback in {"ben", "en"}:
        return fallback
    return "ben" if re.search(r"[\u0980-\u09ff]", text or "") else "en"


def run_command(command: Sequence[str], cwd: Path = ROOT, env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
    print("+", " ".join(str(part) for part in command))
    return subprocess.run(
        list(command),
        cwd=str(cwd),
        env=env or os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def load_manifest(path: Optional[Path]) -> List[Dict[str, Any]]:
    if not path:
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("books"), list):
        return data["books"]
    raise ValueError("Manifest must be a JSON array or an object with a books array.")


def manifest_index(manifest: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for item in manifest:
        slug = normalize_slug(str(item.get("slug") or item.get("title") or ""))
        if slug:
            index[slug] = item
        title_slug = normalize_slug(str(item.get("title") or ""))
        if title_slug:
            index[title_slug] = item
    return index


def manifest_target_slugs(manifest: Iterable[Dict[str, Any]]) -> List[str]:
    slugs: List[str] = []
    for item in manifest:
        slug = normalize_slug(str(item.get("slug") or item.get("title") or ""))
        if slug and slug not in slugs:
            slugs.append(slug)
    return slugs


def rights_metadata_from_manifest(manifest_item: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Keep legal provenance with admin-only book records during publish updates."""

    if not manifest_item:
        return {}
    rights = {
        key: manifest_item[key]
        for key in RIGHTS_METADATA_FIELDS
        if key in manifest_item and manifest_item[key] not in (None, "")
    }
    return rights


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def live_publish_allowed() -> bool:
    return truthy(os.environ.get("PUBLISH_LIVE")) and truthy(os.environ.get("HUMAN_APPROVED"))


def audiobook_enabled_for_book(book: Dict[str, Any], manifest_item: Optional[Dict[str, Any]]) -> bool:
    """Future audiobook support is opt-in and feature-flagged per book."""

    title_key = normalize_title_key(str(book.get("title") or ""))
    if title_key == normalize_title_key("Agentic AI With Python"):
        return False
    values = []
    if manifest_item:
        values.extend([manifest_item.get("audiobook_enabled"), manifest_item.get("generate_audiobook")])
    values.extend([book.get("audiobook_enabled"), book.get("generate_audiobook")])
    return any(truthy(value) for value in values)


def find_manifest_item(book: Dict[str, Any], manifest_by_slug: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return (
        manifest_by_slug.get(normalize_slug(str(book.get("slug") or "")))
        or manifest_by_slug.get(normalize_slug(str(book.get("title") or "")))
    )


def normalize_title_key(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().casefold()


class EarnalismApi:
    def __init__(self, api_url: str) -> None:
        self.api_url = normalize_api_url(api_url)
        self.session = requests.Session()
        self.headers: Dict[str, str] = {}

    def request_json(self, method: str, path: str, timeout: int = 60, **kwargs: Any) -> Any:
        url = f"{self.api_url}{path}"
        headers = dict(kwargs.pop("headers", {}) or {})
        if self.headers:
            headers.update(self.headers)
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                response = self.session.request(method, url, headers=headers, timeout=timeout, **kwargs)
                if response.status_code in {502, 503, 504} and attempt < 3:
                    last_error = RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")
                    time.sleep(attempt * 3)
                    continue
                response.raise_for_status()
                return response.json() if response.text.strip() else {}
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
                if attempt < 3:
                    time.sleep(attempt * 3)
                    continue
                break
            except requests.HTTPError as exc:
                last_error = exc
                status = exc.response.status_code if exc.response is not None else 0
                if status in {502, 503, 504} and attempt < 3:
                    time.sleep(attempt * 3)
                    continue
                raise
        raise RuntimeError(f"{method} {path} failed after retries: {last_error}") from last_error

    def login(self) -> None:
        email = os.environ.get("ADMIN_EMAIL")
        password = os.environ.get("ADMIN_PASSWORD")
        if not email or not password:
            raise RuntimeError("Missing ADMIN_EMAIL/ADMIN_PASSWORD. Load .secrets/earnalism-import.env or export them.")
        token = self.request_json("POST", "/auth/login", json={"email": email, "password": password}, timeout=30)["token"]
        self.headers = {"Authorization": f"Bearer {token}"}

    def get_admin_books(self) -> List[Dict[str, Any]]:
        try:
            return self.request_json("GET", "/admin/books/summary", timeout=60)
        except Exception:
            return self.request_json("GET", "/admin/books", timeout=90)

    def get_admin_book(self, slug: str) -> Dict[str, Any]:
        return self.request_json("GET", f"/admin/books/{slug}", timeout=90)

    def set_publication_status(self, book: Dict[str, Any], rights_metadata: Dict[str, Any], is_published: bool) -> Dict[str, Any]:
        payload = {field: book.get(field) for field in BOOK_IN_FIELDS if field in book}
        payload["slug"] = book["slug"]
        payload["is_published"] = is_published
        payload["cover_image_url"] = book.get("cover_image_url") or book.get("cover_url") or ""
        payload["back_cover_image_url"] = book.get("back_cover_image_url") or book.get("back_cover_url") or ""
        payload["rights_metadata"] = rights_metadata
        payload.setdefault("formats", book.get("formats") or ["Ebook"])
        payload.setdefault("benefits", book.get("benefits") or [])
        payload.setdefault("who_for", book.get("who_for") or [])
        payload.setdefault("learnings", book.get("learnings") or [])
        return self.request_json("PUT", f"/admin/books/{book['slug']}", json=payload, timeout=90)

    def publish_book(self, book: Dict[str, Any], rights_metadata: Dict[str, Any]) -> Dict[str, Any]:
        return self.set_publication_status(book, rights_metadata, True)

    def hold_book_as_draft(self, book: Dict[str, Any], rights_metadata: Dict[str, Any]) -> Dict[str, Any]:
        return self.set_publication_status(book, rights_metadata, False)


def book_chapter_text(book: Dict[str, Any]) -> str:
    chunks: List[str] = []
    for chapter in sorted(book.get("chapters") or [], key=lambda c: c.get("order", 0)):
        title = str(chapter.get("title") or "").strip()
        if title.lower() == "full text":
            title = str(book.get("title") or "").strip()
        if title:
            chunks.append(title)
        parser = HTMLTextExtractor()
        parser.feed(str(chapter.get("content") or ""))
        text = parser.text()
        if text:
            chunks.append(text)
    return "\n\n".join(chunks).strip()


def manuscript_audio_text(text: str) -> str:
    """Exclude reference/index sections from audiobook generation."""

    match = re.search(r"(?im)^\s*(Bibliography|References|Index)\s*$", text)
    if match:
        text = text[: match.start()]
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def highlight_units(text: str) -> List[str]:
    units: List[str] = []
    for token in re.findall(r"\S+", text):
        if re.match(r"^\d{1,3}(?:,\d{3})+(?:[^\w\u0980-\u09ff]*)?$", token, flags=re.UNICODE):
            units.extend(part for part in re.findall(r"\d+|\D+", token) if re.search(r"\d", part))
        elif re.search(r"[\w\u0980-\u09ff]", token, flags=re.UNICODE):
            units.append(token)
    return units


def validate_compliance(
    book: Dict[str, Any],
    manifest_item: Optional[Dict[str, Any]],
    trust_existing_admin_rights: bool,
) -> Tuple[bool, List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    if not book.get("title"):
        errors.append("missing title")
    if not book.get("author"):
        errors.append("missing author")
    if not (book.get("cover_image_url") or book.get("cover_url")):
        errors.append("missing front cover")
    if not (book.get("back_cover_image_url") or book.get("back_cover_url")):
        errors.append("missing back cover")

    chapters = book.get("chapters") or []
    if not chapters:
        errors.append("no chapters")
    for chapter in chapters:
        if (chapter.get("processing_status") or "ready") != "ready":
            errors.append(f"chapter not ready: {chapter.get('title') or chapter.get('id')}")

    rights = book.get("rights_metadata") or {}
    if manifest_item:
        rights = {**manifest_item, **rights}

    rights_basis = str(rights.get("rights_basis") or "").strip()
    source_license = str(rights.get("source_license") or "").strip()
    source_type = str(rights.get("source_type") or "").strip()
    author_death_year = rights.get("author_death_year")
    publication_year = rights.get("original_publication_year")
    commercial_allowed = bool(rights.get("commercial_use_allowed") is True)
    original_work = any(
        phrase in rights_basis.lower()
        for phrase in ("original", "author-owned", "reo enterprise", "copyright owner")
    )

    if not rights and not trust_existing_admin_rights:
        errors.append("rights metadata unavailable; provide manifest or use --trust-existing-admin-rights after manual review")
    elif trust_existing_admin_rights and not rights:
        warnings.append("rights metadata not exposed by admin API; trusted by operator flag")
    elif original_work:
        if not (book.get("author") or rights.get("author")):
            errors.append("original work missing author")
    else:
        combined = f"{rights_basis} {source_license}".lower()
        if "cc-nc" in combined or "non-commercial" in combined:
            errors.append("rights restrict commercial use")
        if not commercial_allowed and "public domain" not in combined and "commercial" not in combined:
            errors.append("commercial-use permission not confirmed")
        if "public domain" in combined and (not author_death_year or not publication_year):
            errors.append("public-domain claim missing author_death_year or original_publication_year")
        if source_type and not source_type.startswith(("wikisource", "plain_text", "public_domain")):
            warnings.append(f"review source_type: {source_type}")
        if not rights_basis:
            errors.append("missing rights_basis")

    return not errors, errors, warnings


def assess_latency_risk(book: Dict[str, Any], args: argparse.Namespace) -> Tuple[bool, str]:
    """Hold large drafts back when publishing them may stress public/admin APIs."""

    if args.disable_latency_risk_gate:
        return True, "disabled by operator"

    chapters = book.get("chapters") or []
    chapter_count = len(chapters)
    chapter_lengths = [len(str(chapter.get("content") or "")) for chapter in chapters]
    total_chars = sum(chapter_lengths)
    max_chapter_chars = max(chapter_lengths, default=0)
    failures: List[str] = []

    if args.max_publish_chapters > 0 and chapter_count > args.max_publish_chapters:
        failures.append(f"chapters={chapter_count} > {args.max_publish_chapters}")
    if args.max_publish_chars > 0 and total_chars > args.max_publish_chars:
        failures.append(f"content_chars={total_chars} > {args.max_publish_chars}")
    if args.max_publish_chapter_chars > 0 and max_chapter_chars > args.max_publish_chapter_chars:
        failures.append(f"largest_chapter_chars={max_chapter_chars} > {args.max_publish_chapter_chars}")

    detail = (
        f"chapters={chapter_count}, content_chars={total_chars}, "
        f"largest_chapter_chars={max_chapter_chars}; thresholds "
        f"chapters<={args.max_publish_chapters}, content_chars<={args.max_publish_chars}, "
        f"largest_chapter_chars<={args.max_publish_chapter_chars}"
    )
    if failures:
        return False, "held as draft for latency/timeout risk: " + "; ".join(failures) + f" ({detail})"
    return True, "ok: " + detail


def has_latency_risk_holdback(result: BookProductionResult) -> bool:
    return any(gate.name == "latency_risk" and not gate.ok for gate in result.gates)


def run_importer(args: argparse.Namespace, run_dir: Path) -> None:
    if not args.manifest or args.skip_import or not args.upload_drafts:
        return
    command = [
        sys.executable,
        "scripts/import_books.py",
        str(args.manifest),
        "--output-dir",
        str(run_dir / "import_books"),
        "--upload",
        "--api-url",
        args.api_url,
    ]
    if args.update_existing_drafts:
        command.append("--update-existing-drafts")
    result = run_command(command)
    write_text(run_dir / "import_books.log", result.stdout)
    if result.returncode != 0:
        raise RuntimeError(f"Importer failed. See {run_dir / 'import_books.log'}")


def prepare_audio_manifest(book: Dict[str, Any], run_dir: Path) -> Tuple[Path, Path, str, int]:
    slug = book["slug"]
    raw_text = book_chapter_text(book)
    audio_text = manuscript_audio_text(raw_text)
    language = infer_language(audio_text)
    text_dir = run_dir / "texts"
    text_path = text_dir / f"{slug}.txt"
    write_text(text_path, audio_text)
    manifest = [
        {
            "slug": slug,
            "title": book.get("title") or slug,
            "author": book.get("author") or "",
            "language": language,
            "source_url": "",
            "category_slug": book.get("category_slug") or "",
        }
    ]
    manifest_path = run_dir / "audio_manifests" / f"{slug}.json"
    write_json(manifest_path, manifest)
    return manifest_path, text_dir, language, len(highlight_units(audio_text))


def run_audio_generation(
    slug: str,
    manifest_path: Path,
    text_dir: Path,
    audio_output_dir: Path,
    run_dir: Path,
    skip_audio: bool,
) -> None:
    if skip_audio:
        return
    command = [
        sys.executable,
        "generate_audio.py",
        "--manifest",
        str(manifest_path),
        "--text-dir",
        str(text_dir),
        "--slug",
        slug,
        "--output-dir",
        str(audio_output_dir),
    ]
    result = run_command(command)
    write_text(run_dir / f"audio_{slug}.log", result.stdout)
    if result.returncode != 0:
        raise RuntimeError(f"Audio generation failed for {slug}. See {run_dir / f'audio_{slug}.log'}")


def copy_audio_assets(slug: str, language: str, audio_output_dir: Path, public_audio_dir: Path) -> Dict[str, str]:
    src_dir = audio_output_dir / language
    dst_dir = public_audio_dir / language
    dst_dir.mkdir(parents=True, exist_ok=True)
    copied: Dict[str, str] = {}
    for suffix in (".mp3", "_timestamps.json", "_highlight.vtt", "_chapters.json", "_meta.json"):
        source = src_dir / f"{slug}{suffix}"
        if not source.exists():
            continue
        destination = dst_dir / source.name
        shutil.copy2(source, destination)
        copied[suffix] = str(destination.relative_to(ROOT))
    return copied


def validate_timestamps(slug: str, language: str, expected_units: int, public_audio_dir: Path) -> Tuple[bool, str]:
    base = public_audio_dir / language / slug
    mp3 = Path(f"{base}.mp3")
    timestamps_path = Path(f"{base}_timestamps.json")
    meta_path = Path(f"{base}_meta.json")
    missing = [str(path.relative_to(ROOT)) for path in (mp3, timestamps_path, meta_path) if not path.exists()]
    if missing:
        return False, f"missing audio assets: {', '.join(missing)}"

    timestamps = json.loads(timestamps_path.read_text(encoding="utf-8"))
    if not timestamps:
        return False, "timestamps file is empty"
    monotonic = all(
        int(timestamps[i].get("start_ms", 0)) <= int(timestamps[i].get("end_ms", 0)) <= int(timestamps[i + 1].get("start_ms", 0))
        for i in range(len(timestamps) - 1)
    )
    if not monotonic:
        return False, "timestamps are not monotonic"
    tolerance = max(20, int(expected_units * 0.025))
    delta = abs(len(timestamps) - expected_units)
    if delta > tolerance:
        return False, f"timestamp/token mismatch: timestamps={len(timestamps)} expected={expected_units} tolerance={tolerance}"
    return True, f"timestamps={len(timestamps)}, expected_units={expected_units}, delta={delta}"


def http_smoke(book: Dict[str, Any], frontend_url: str, api_url: str, language: str, public_audio_dir: Path, audio_required: bool = True) -> Tuple[bool, str]:
    slug = book["slug"]
    details: List[str] = []
    errors: List[str] = []

    def check(url: str, expected: Iterable[int] = (200,)) -> None:
        try:
            response = requests.get(url, timeout=30)
            details.append(f"{response.status_code} {url}")
            if response.status_code not in expected:
                errors.append(f"{url} returned {response.status_code}")
        except Exception as exc:  # noqa: BLE001 - smoke report should continue
            errors.append(f"{url} failed: {exc}")

    check(f"{normalize_api_url(api_url)}/books/{slug}", expected=(200, 404))
    check(f"{normalize_api_url(api_url)}/books/{slug}/chapters", expected=(200, 404))
    if book.get("is_published"):
        check(f"{frontend_url.rstrip('/')}/book/{slug}")
        if audio_required:
            check(f"{frontend_url.rstrip('/')}/audio/{language}/{slug}_timestamps.json")
            # HEAD is enough for the large MP3, but some CDNs treat HEAD differently.
            try:
                response = requests.head(f"{frontend_url.rstrip('/')}/audio/{language}/{slug}.mp3", timeout=30, allow_redirects=True)
                details.append(f"{response.status_code} audio-head")
                if response.status_code != 200:
                    errors.append(f"audio mp3 returned {response.status_code}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"audio mp3 failed: {exc}")
        else:
            details.append("audio smoke skipped: audiobook feature disabled")
    else:
        local_mp3 = public_audio_dir / language / f"{slug}.mp3"
        if not audio_required:
            details.append("local audio smoke skipped: audiobook feature disabled")
        elif local_mp3.exists():
            details.append(f"local audio ok: {local_mp3.relative_to(ROOT)}")
        else:
            errors.append("local audio mp3 missing")

    return not errors, "; ".join(errors or details)


def book_payload_summary(book: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "slug": book.get("slug"),
        "title": book.get("title"),
        "published": book.get("is_published"),
        "front_cover": bool(book.get("cover_image_url") or book.get("cover_url")),
        "back_cover": bool(book.get("back_cover_image_url") or book.get("back_cover_url")),
        "chapters": len(book.get("chapters") or []),
    }


def render_markdown_report(path: Path, results: List[BookProductionResult], published: List[str]) -> None:
    lines = ["# Earnalism Book Production Report", ""]
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    for result in results:
        lines.append(f"## {result.title} (`{result.slug}`)")
        lines.append("")
        lines.append(f"Verdict: **{result.verdict}**")
        lines.append(f"Language: `{result.language or 'unknown'}`")
        lines.append(f"Audiobook enabled: `{str(result.audiobook_enabled).lower()}`")
        if result.published:
            lines.append("Published: yes")
        if result.audio_assets:
            lines.append("")
            lines.append("Audio assets:")
            for kind, asset in sorted(result.audio_assets.items()):
                lines.append(f"- `{kind}`: `{asset}`")
        if result.warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in result.warnings:
                lines.append(f"- {warning}")
        lines.append("")
        lines.append("Gates:")
        for gate in result.gates:
            mark = "PASS" if gate.ok else "FAIL"
            lines.append(f"- {mark} `{gate.name}`: {gate.detail}")
        lines.append("")
    if published:
        lines.append("## Published")
        for slug in published:
            lines.append(f"- `{slug}`")
        lines.append("")
    lines.append("## Approval")
    lines.append("If all intended books are GO, rerun with `PUBLISH_LIVE=1 HUMAN_APPROVED=1 --publish-approved` to publish them.")
    write_text(path, "\n".join(lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Orchestrate Earnalism book production gates.")
    parser.add_argument("--manifest", type=Path, default=None, help="Optional import manifest.")
    parser.add_argument("--all-drafts", action="store_true", help="Process every unpublished admin draft.")
    parser.add_argument("--book-slug", action="append", default=[], help="Specific book slug to process. Repeatable.")
    parser.add_argument("--api-url", default=os.environ.get("EARNALISM_API_URL", DEFAULT_API_URL))
    parser.add_argument("--frontend-url", default=os.environ.get("EARNALISM_FRONTEND_URL", DEFAULT_FRONTEND_URL))
    parser.add_argument("--audio-output-dir", type=Path, default=ROOT / "audio_output")
    parser.add_argument("--public-audio-dir", type=Path, default=ROOT / "frontend/public/audio")
    parser.add_argument("--run-output-dir", type=Path, default=ROOT / "output/book_production")
    parser.add_argument("--upload-drafts", action="store_true", help="Run scripts/import_books.py --upload before processing.")
    parser.add_argument("--update-existing-drafts", action="store_true", help="Pass through to importer.")
    parser.add_argument("--skip-import", action="store_true")
    parser.add_argument("--skip-audio", action="store_true")
    parser.add_argument("--skip-qa", action="store_true")
    parser.add_argument("--publish-approved", action="store_true", help="Publish GO books only when PUBLISH_LIVE=1 and HUMAN_APPROVED=1 are also set.")
    parser.add_argument("--trust-existing-admin-rights", action="store_true", help="Allow GO when rights were manually reviewed outside exposed admin API.")
    parser.add_argument("--max-publish-chapters", type=int, default=DEFAULT_MAX_PUBLISH_CHAPTERS, help="Hold books above this chapter count as drafts. Use 0 to disable this threshold.")
    parser.add_argument("--max-publish-chars", type=int, default=DEFAULT_MAX_PUBLISH_CHARS, help="Hold books above this stored-content character count as drafts. Use 0 to disable this threshold.")
    parser.add_argument("--max-publish-chapter-chars", type=int, default=DEFAULT_MAX_PUBLISH_CHAPTER_CHARS, help="Hold books with any chapter above this stored-content character count as drafts. Use 0 to disable this threshold.")
    parser.add_argument("--disable-latency-risk-gate", action="store_true", help="Disable automatic draft holdbacks for oversized books.")
    parser.add_argument("--env-file", action="append", type=Path, default=[ROOT / ".secrets/earnalism-import.env", ROOT / ".secrets/earnalism-audio.env"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for env_file in args.env_file:
        load_env_file(env_file)

    run_dir = args.run_output_dir / utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(args.manifest)
    manifest_by_slug = manifest_index(manifest)

    run_importer(args, run_dir)

    api = EarnalismApi(args.api_url)
    api.login()
    admin_books = api.get_admin_books()

    if args.all_drafts:
        books = [book for book in admin_books if not book.get("is_published")]
    else:
        slugs = set(args.book_slug)
        if not slugs:
            slugs.update(manifest_target_slugs(manifest))
        if not slugs:
            raise RuntimeError("No books selected. Use --all-drafts, --book-slug, or --manifest.")
        books = [api.get_admin_book(slug) for slug in sorted(slugs)]

    draft_slugs_by_title: Dict[str, List[str]] = {}
    for admin_book in admin_books:
        if admin_book.get("is_published"):
            continue
        title_key = normalize_title_key(str(admin_book.get("title") or ""))
        if title_key:
            draft_slugs_by_title.setdefault(title_key, []).append(str(admin_book.get("slug") or ""))

    results: List[BookProductionResult] = []
    published: List[str] = []

    for book in books:
        slug = book["slug"]
        title = book.get("title") or slug
        result = BookProductionResult(slug=slug, title=title)
        print(f"\n=== {title} ({slug}) ===")
        write_json(run_dir / "admin_books" / f"{slug}.json", book_payload_summary(book))

        manifest_item = find_manifest_item(book, manifest_by_slug)
        result.audiobook_enabled = audiobook_enabled_for_book(book, manifest_item)
        duplicate_drafts = [
            value
            for value in draft_slugs_by_title.get(normalize_title_key(str(book.get("title") or "")), [])
            if value and value != slug
        ]
        result.add_gate(
            "duplicate_drafts",
            not duplicate_drafts,
            "ok" if not duplicate_drafts else f"duplicate unpublished draft slug(s): {', '.join(duplicate_drafts)}",
        )
        latency_ok, latency_detail = assess_latency_risk(book, args)
        result.add_gate("latency_risk", latency_ok, latency_detail)
        legal_ok, legal_errors, legal_warnings = validate_compliance(book, manifest_item, args.trust_existing_admin_rights)
        result.warnings.extend(legal_warnings)
        result.add_gate("legal_compliance", legal_ok, "; ".join(legal_errors or legal_warnings or ["ok"]))

        if result.audiobook_enabled and not args.skip_audio:
            manifest_path, text_dir, language, expected_units = prepare_audio_manifest(book, run_dir)
            result.language = language
            result.add_gate("audio_text", expected_units > 0, f"{expected_units} highlight units prepared")

            try:
                run_audio_generation(slug, manifest_path, text_dir, args.audio_output_dir, run_dir, args.skip_audio)
                assets = copy_audio_assets(slug, language, args.audio_output_dir, args.public_audio_dir)
                result.audio_assets = assets
                result.add_gate("audio_assets", bool(assets.get(".mp3")), f"{len(assets)} assets copied/reused")
            except Exception as exc:  # noqa: BLE001 - record and keep processing other books
                result.add_gate("audio_assets", False, str(exc))

            ts_ok, ts_detail = validate_timestamps(slug, language, expected_units, args.public_audio_dir)
            result.add_gate("timestamp_sync", ts_ok, ts_detail)
        else:
            result.language = infer_language(book_chapter_text(book), str(book.get("language") or ""))
            detail = "disabled by audiobook_enabled=false" if not result.audiobook_enabled else "skipped by operator"
            result.add_gate("audiobook_feature_flag", True, detail)

        if args.skip_qa:
            result.add_gate("qa_smoke", True, "skipped by operator")
        else:
            qa_ok, qa_detail = http_smoke(book, args.frontend_url, args.api_url, result.language or "en", args.public_audio_dir, audio_required=result.audiobook_enabled)
            result.add_gate("qa_smoke", qa_ok, qa_detail)

        result.finalize()
        if args.publish_approved and not live_publish_allowed():
            result.add_gate(
                "publish",
                False,
                "blocked: set PUBLISH_LIVE=1 and HUMAN_APPROVED=1 after human review",
            )
        elif args.publish_approved and result.verdict == "GO":
            rights_payload = rights_metadata_from_manifest(manifest_item) or book.get("rights_metadata") or {}
            if not rights_payload:
                result.add_gate(
                    "publish",
                    False,
                    "blocked: manifest rights metadata required so publish update does not erase legal provenance",
                )
                result.finalize()
                results.append(result)
                continue
            published_book = api.publish_book(book, rights_payload)
            result.published = True
            published.append(published_book["slug"])
            result.add_gate("publish", True, "published after explicit --publish-approved")
        elif args.publish_approved and has_latency_risk_holdback(result) and live_publish_allowed():
            rights_payload = rights_metadata_from_manifest(manifest_item) or book.get("rights_metadata") or {}
            held_book = api.hold_book_as_draft(book, rights_payload)
            result.add_gate("publish", True, f"held as draft after latency-risk gate ({held_book['slug']})")
        elif args.publish_approved:
            result.add_gate("publish", False, "not published because verdict was NO-GO")
        result.finalize()

        results.append(result)

    report_json = run_dir / "book_production_report.json"
    report_md = run_dir / "book_production_report.md"
    write_json(
        report_json,
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "publish_approved": args.publish_approved,
            "published": published,
            "results": [
                {
                    "slug": result.slug,
                    "title": result.title,
                    "language": result.language,
                    "verdict": result.verdict,
                    "published": result.published,
                    "warnings": result.warnings,
                    "audio_assets": result.audio_assets,
                    "audiobook_enabled": result.audiobook_enabled,
                    "gates": [gate.__dict__ for gate in result.gates],
                }
                for result in results
            ],
        },
    )
    render_markdown_report(report_md, results, published)

    print("\nProduction proposal")
    print("===================")
    for result in results:
        print(f"{result.verdict}: {result.title} ({result.slug})")
        for gate in result.gates:
            print(f"  {'PASS' if gate.ok else 'FAIL'} {gate.name}: {gate.detail}")
    if not args.publish_approved:
        print("\nHuman approval required before publishing.")
        print("Rerun with --publish-approved for GO books only after reviewing the report.")
    print(f"Report: {report_md}")
    return 0 if all(result.verdict == "GO" for result in results) else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
