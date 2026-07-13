#!/usr/bin/env python3
"""Generate the multi-title backend catalog truth audit in dry-run mode."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.catalog_truth import (  # noqa: E402
    AUDIO_ENABLED_SLUGS,
    CONTROLLED_LIVE_BOOK_SLUGS,
    LIVE_APPROVED_SLUG,
    PIPELINE_CANDIDATE_SLUGS,
    PUBLIC_STATUS_COMING_SOON,
    PUBLIC_STATUS_LIVE_APPROVED,
    PUBLIC_STATUS_PIPELINE_CANDIDATE,
    catalog_truth_row,
    catalog_truth_summary,
    dracula_approval_evidence,
    explicit_preview_chapter_ids,
    load_controlled_artifact_book,
    normalize_slug,
    normalize_text,
    normalize_upper,
    public_book_projection,
)


REPORT_FIELDS = [
    "slug",
    "title",
    "author",
    "classification",
    "is_published",
    "publication_status",
    "rights_tier",
    "verification_status",
    "qa_status",
    "approved_to_publish",
    "reader_enabled",
    "preview_enabled",
    "audio_enabled",
    "audiobook_enabled",
    "source_url_present",
    "source_hash_present",
    "content_hash_present",
    "provenance_hash_present",
    "public_route",
    "reader_route",
    "sitemap_inclusion",
]

API_AUDIT_PATHS = [
    "/books",
    "/books/dracula",
    "/books/kshudhita-pashan",
    "/controlled-launch/status",
    "/reader/book/dracula/manifest",
    "/reader/book/kshudhita-pashan/manifest",
    "/reader/book/dracula/audiobook",
    "/reader/book/kshudhita-pashan/audiobook",
]

FORBIDDEN_PUBLIC_API_FIELDS = {
    "approved_to_publish",
    "audio_asset_slug",
    "audio_assets",
    "audio_files",
    "audiobook",
    "audiobook_assets",
    "audiobook_provider",
    "audiobook_url",
    "audiobook_voice",
    "b2_url",
    "blocked_reason",
    "cloudinary_audio",
    "content",
    "content_hash",
    "generate_audiobook",
    "ingestion",
    "provenance_hash",
    "qa_issues",
    "rights_decision",
    "rights_metadata",
    "rights_tier",
    "source_evidence",
    "source_hash",
    "source_license",
    "source_metadata",
    "source_name",
    "source_text_url",
    "source_url",
    "verification_status",
}


@dataclass
class EndpointResult:
    status: int
    json_data: Any = None
    body: str = ""
    error: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "ok": 200 <= self.status < 300,
            "error": self.error,
            "body_preview": self.body[:240],
        }


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401, N802
        return None


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def parse_json_body(body: str) -> Any:
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def fetch_api_endpoint(api_url: str, path: str, *, timeout_ms: int = 10_000) -> EndpointResult:
    base = api_url.rstrip("/") + "/"
    url = urljoin(base, path.lstrip("/"))
    opener = build_opener(NoRedirectHandler)
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "EarnalismCatalogTruthCanary/1.0",
        },
    )
    try:
        with opener.open(request, timeout=max(1, timeout_ms / 1000)) as response:
            body = response.read().decode("utf-8", errors="replace")
            return EndpointResult(
                status=int(response.getcode() or 0),
                json_data=parse_json_body(body),
                body=body,
            )
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return EndpointResult(
            status=int(exc.code or 0),
            json_data=parse_json_body(body),
            body=body,
            error=str(exc.reason or ""),
        )
    except URLError as exc:
        return EndpointResult(status=0, error=str(getattr(exc, "reason", exc)))
    except TimeoutError as exc:
        return EndpointResult(status=0, error=f"timeout: {exc}")


def fetch_api_endpoints(
    api_url: str,
    paths: list[str],
    *,
    timeout_ms: int = 10_000,
    fetcher=fetch_api_endpoint,
) -> dict[str, EndpointResult]:
    unique_paths = list(dict.fromkeys(paths))
    if not unique_paths:
        return {}
    max_workers = min(16, max(1, len(unique_paths)))
    results: dict[str, EndpointResult] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(fetcher, api_url, path, timeout_ms=timeout_ms): path
            for path in unique_paths
        }
        for future in as_completed(future_to_path):
            path = future_to_path[future]
            try:
                results[path] = future.result()
            except Exception as exc:  # pragma: no cover - defensive canary capture.
                results[path] = EndpointResult(status=0, error=str(exc))
    return results


def sitemap_urls(path: Path) -> set[str]:
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return set()
    urls: set[str] = set()
    for node in root.iter():
        if node.tag.endswith("loc") and node.text:
            urls.add(node.text.strip())
            parsed_path = "/" + node.text.split("theearnalism.com/", 1)[-1].strip("/")
            urls.add(parsed_path.rstrip("/") if parsed_path != "/" else "/")
    return urls


def frontend_controlled_live_slugs(path: Path | None = None) -> set[str] | None:
    config_path = ROOT / "data" / "controlled_launch.json"
    if path is None and config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            config = {}
        slugs = config.get("live_approved_slugs") if isinstance(config, dict) else []
        if isinstance(slugs, list):
            normalized = {normalize_slug(slug) for slug in slugs if normalize_slug(slug)}
            if normalized:
                return normalized

    source_path = path or ROOT / "frontend" / "scripts" / "generate-seo-assets.mjs"
    if not source_path.exists():
        return None
    text = source_path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"controlledLiveSlugs\s*=\s*new Set\(\s*\[(.*?)\]\s*\)", text, re.S)
    if not match:
        return None
    return {slug for slug in re.findall(r"[\"']([^\"']+)[\"']", match.group(1)) if slug}


def dracula_record() -> dict[str, Any]:
    evidence = dracula_approval_evidence()
    rights_decision = evidence.get("rights_decision") if isinstance(evidence.get("rights_decision"), dict) else {}
    metadata = rights_decision.get("metadata") if isinstance(rights_decision.get("metadata"), dict) else {}
    ingestion = evidence.get("ingestion") if isinstance(evidence.get("ingestion"), dict) else {}
    return {
        "id": "dracula-controlled-launch",
        "slug": LIVE_APPROVED_SLUG,
        "title": "Dracula",
        "author": "Bram Stoker",
        "category_slug": "gothic-fiction",
        "short_description": "The only controlled live core reading release.",
        "is_published": True,
        "rights_metadata": {
            "rights_tier": metadata.get("rights_tier") or "A",
            "verification_status": metadata.get("verification_status") or "approved",
            "blocked_reason": metadata.get("blocked_reason") or "",
            "source_url": metadata.get("source_url") or evidence.get("source_url"),
            "source_name": metadata.get("source_name") or evidence.get("source_name"),
            "source_license": metadata.get("source_license") or evidence.get("source_license"),
        },
        "source_hash": evidence.get("source_hash") or ingestion.get("source_hash"),
        "content_hash": evidence.get("content_hash") or ingestion.get("content_hash"),
        "provenance_hash": evidence.get("provenance_hash") or ingestion.get("provenance_hash"),
        "qa_status": evidence.get("qa_status") or "QA_PASSED",
        "approved_to_publish": bool(evidence.get("approved_to_publish_artifact")),
        "publication_status": "LIVE_APPROVED",
    }


def pipeline_candidate_records() -> list[dict[str, Any]]:
    source_path = ROOT / "data" / "publication_candidates" / "kshudhita-pashan.source.json"
    candidate = load_json(source_path)
    title = candidate.get("title") or "Kshudhita Pashan"
    author = candidate.get("author") or "Rabindranath Tagore"
    return [
        {
            "id": "kshudhita-pashan-pipeline",
            "slug": "kshudhita-pashan",
            "title": title,
            "author": author,
            "category_slug": "gothic-fiction",
            "short_description": "Bengali gothic candidate held in the rights-safe pipeline.",
            "is_published": False,
            "pipeline_stage": "PIPELINE_ONLY",
            "rights_metadata": {
                "rights_tier": candidate.get("rights_tier") or "UNKNOWN",
                "verification_status": candidate.get("verification_status") or "pending",
                "blocked_reason": candidate.get("blocked_reason") or "",
            },
            "publication_status": "PIPELINE_CANDIDATE",
        }
    ]


def controlled_live_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for slug in CONTROLLED_LIVE_BOOK_SLUGS:
        artifact = load_controlled_artifact_book(slug, include_content=False)
        if artifact:
            records.append(artifact)
    if not any(normalize_slug(record.get("slug")) == LIVE_APPROVED_SLUG for record in records):
        records.insert(0, dracula_record())
    return records


def audit_records() -> list[dict[str, Any]]:
    return [*controlled_live_records(), *pipeline_candidate_records()]


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().lower() not in {"false", "0", "no", "off", "none"}
    return bool(value)


def api_book_classification(book: dict[str, Any]) -> str:
    slug = normalize_slug(book.get("slug"))
    status = normalize_upper(book.get("publication_status") or book.get("launch_status"))
    if status in {PUBLIC_STATUS_LIVE_APPROVED, PUBLIC_STATUS_PIPELINE_CANDIDATE}:
        return status
    if slug == LIVE_APPROVED_SLUG:
        return PUBLIC_STATUS_LIVE_APPROVED if api_reader_enabled(book) or api_preview_enabled(book) else PUBLIC_STATUS_COMING_SOON
    if slug in PIPELINE_CANDIDATE_SLUGS:
        return PUBLIC_STATUS_PIPELINE_CANDIDATE
    return status or PUBLIC_STATUS_COMING_SOON


def api_reader_enabled(book: dict[str, Any]) -> bool:
    return truthy(book.get("reader_enabled")) or bool(normalize_text(book.get("reader_url")))


def api_preview_enabled(book: dict[str, Any]) -> bool:
    return bool(explicit_preview_chapter_ids(book))


def api_audio_enabled(book: dict[str, Any]) -> bool:
    audiobook = book.get("audiobook") if isinstance(book.get("audiobook"), dict) else {}
    assets = book.get("audiobook_assets") if isinstance(book.get("audiobook_assets"), dict) else {}
    nested_assets = audiobook.get("assets") if isinstance(audiobook.get("assets"), dict) else {}
    audio_fields = (
        "audio_enabled",
        "audiobook_enabled",
        "generate_audiobook",
        "has_audio",
    )
    audio_url_fields = (
        "audio_url",
        "audiobook_url",
        "voice_url",
        "waveform_url",
        "b2_url",
        "cloudinary_audio",
        "narration_url",
        "listen_url",
    )
    audio_collection_fields = (
        "audio_assets",
        "audio_files",
    )
    return any(
        [
            *(truthy(book.get(field)) for field in audio_fields),
            *(bool(normalize_text(book.get(field))) for field in audio_url_fields),
            *(bool(book.get(field)) for field in audio_collection_fields),
            bool(normalize_text(audiobook.get("url"))),
            bool(assets),
            bool(nested_assets),
        ]
    )


def api_truth_row(book: dict[str, Any], *, sitemap_urls: set[str] | None = None) -> dict[str, Any]:
    sitemap_urls = sitemap_urls or set()
    slug = normalize_slug(book.get("slug"))
    classification = api_book_classification(book)
    return {
        "slug": slug,
        "title": normalize_text(book.get("title")),
        "author": normalize_text(book.get("author")),
        "classification": classification,
        "is_published": bool(book.get("is_published")),
        "publication_status": normalize_upper(book.get("publication_status") or book.get("launch_status")) or classification,
        "rights_tier": normalize_upper(book.get("rights_tier")) or "PUBLIC_API_HIDDEN",
        "verification_status": normalize_text(book.get("verification_status")) or "public_api_hidden",
        "qa_status": normalize_text(book.get("qa_status")) or "public_api_hidden",
        "approved_to_publish": bool(book.get("approved_to_publish")),
        "reader_enabled": api_reader_enabled(book),
        "preview_enabled": api_preview_enabled(book),
        "audio_enabled": api_audio_enabled(book),
        "audiobook_enabled": api_audio_enabled(book),
        "source_url_present": bool(book.get("source_url")),
        "source_hash_present": bool(book.get("source_hash")),
        "content_hash_present": bool(book.get("content_hash")),
        "provenance_hash_present": bool(book.get("provenance_hash")),
        "public_route": f"/book/{slug}" if classification == PUBLIC_STATUS_LIVE_APPROVED else "",
        "reader_route": f"/reader/{slug}" if api_reader_enabled(book) else "",
        "sitemap_inclusion": f"/book/{slug}" in sitemap_urls or f"https://theearnalism.com/book/{slug}" in sitemap_urls,
    }


def api_books_rows(payload: Any, *, sitemap_urls: set[str]) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    return [api_truth_row(book, sitemap_urls=sitemap_urls) for book in payload if isinstance(book, dict)]


def api_detail_row(payload: Any, *, sitemap_urls: set[str]) -> dict[str, Any] | None:
    return api_truth_row(payload, sitemap_urls=sitemap_urls) if isinstance(payload, dict) else None


def api_endpoint_statuses(endpoints: dict[str, EndpointResult]) -> dict[str, dict[str, Any]]:
    return {path: result.as_dict() for path, result in endpoints.items()}


def forbidden_public_fields(payload: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_path = f"{path}.{key}" if path else key
            if key in FORBIDDEN_PUBLIC_API_FIELDS:
                found.append(child_path)
            found.extend(forbidden_public_fields(value, child_path))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            found.extend(forbidden_public_fields(value, f"{path}[{index}]"))
    return found


def safe_field_issues(endpoint: str, payload: Any) -> list[str]:
    return [
        f"{endpoint} exposes forbidden public field {field}"
        for field in forbidden_public_fields(payload)
    ]


def verify_live_detail_payload(endpoint: str, payload: Any, slug: str) -> list[str]:
    normalized = normalize_slug(slug)
    issues = safe_field_issues(endpoint, payload)
    if not isinstance(payload, dict):
        return [*issues, f"{endpoint} did not return a JSON object"]

    preview_enabled = bool(explicit_preview_chapter_ids(payload))
    expected_values = {
        "slug": normalized,
        "publication_status": PUBLIC_STATUS_LIVE_APPROVED,
        "launch_status": PUBLIC_STATUS_LIVE_APPROVED,
        "reader_enabled": True,
        "preview_enabled": preview_enabled,
        "audio_enabled": False,
        "audiobook_enabled": False,
        "public_route": f"/book/{normalized}",
        "reader_url": f"/reader/{normalized}",
        "preview_url": f"/reader/{normalized}" if preview_enabled else "",
        "audio_url": "",
        "public_json_ld_enabled": True,
    }
    for key, expected in expected_values.items():
        if payload.get(key) != expected:
            issues.append(f"{endpoint} {key} is {payload.get(key)!r}; expected {expected!r}")

    if payload.get("audio_status") not in {"NOT_AVAILABLE", "DISABLED"}:
        issues.append(
            f"{endpoint} audio_status is {payload.get('audio_status')!r}; "
            "expected 'NOT_AVAILABLE' or 'DISABLED'"
        )
    if not normalize_text(payload.get("source_note")):
        issues.append(f"{endpoint} is missing a safe source_note")
    if not normalize_text(payload.get("rights_note")):
        issues.append(f"{endpoint} is missing a safe rights_note")
    if "audiobook_assets" in payload or "audiobook" in payload:
        issues.append(f"{endpoint} exposes raw audiobook fields")
    return issues


def verify_dracula_detail_payload(payload: Any) -> list[str]:
    issues = verify_live_detail_payload("/books/dracula", payload, LIVE_APPROVED_SLUG)
    if not isinstance(payload, dict):
        return issues

    expected_values = {
        "slug": LIVE_APPROVED_SLUG,
        "publication_status": PUBLIC_STATUS_LIVE_APPROVED,
        "launch_status": PUBLIC_STATUS_LIVE_APPROVED,
        "reader_enabled": True,
        "preview_enabled": True,
        "audio_enabled": False,
        "audiobook_enabled": False,
        "public_route": "/book/dracula",
        "reader_url": "/reader/dracula",
        "preview_url": "/reader/dracula",
        "audio_url": "",
        "public_json_ld_enabled": True,
    }
    for key, expected in expected_values.items():
        if payload.get(key) != expected:
            issues.append(f"/books/dracula {key} is {payload.get(key)!r}; expected {expected!r}")
    return issues


def verify_pipeline_detail_payload(endpoint: str, payload: Any) -> list[str]:
    issues = safe_field_issues(endpoint, payload)
    if not isinstance(payload, dict):
        return [*issues, f"{endpoint} did not return a JSON object"]

    expected_false_fields = {
        "reader_enabled": False,
        "preview_enabled": False,
        "audio_enabled": False,
        "audiobook_enabled": False,
        "public_json_ld_enabled": False,
    }
    for key, expected in expected_false_fields.items():
        if payload.get(key) is not expected:
            issues.append(f"{endpoint} {key} is {payload.get(key)!r}; expected {expected!r}")

    expected_empty_fields = ("public_route", "reader_url", "preview_url", "audio_url")
    for key in expected_empty_fields:
        if payload.get(key):
            issues.append(f"{endpoint} exposes {key}: {payload.get(key)!r}")

    if payload.get("publication_status") != PUBLIC_STATUS_PIPELINE_CANDIDATE:
        issues.append(f"{endpoint} is not pipeline-only")
    if payload.get("cta_label") != "Notify Me":
        issues.append(f"{endpoint} CTA is not Notify Me")
    if payload.get("secondary_cta_label") != "Reading Circle":
        issues.append(f"{endpoint} secondary CTA is not Reading Circle")
    return issues


def verify_dracula_manifest_payload(payload: Any) -> list[str]:
    issues = safe_field_issues("/reader/book/dracula/manifest", payload)
    if not isinstance(payload, dict):
        return [*issues, "/reader/book/dracula/manifest did not return a JSON object"]
    chapters = payload.get("chapters")
    if not isinstance(chapters, list) or len(chapters) != 27:
        issues.append("/reader/book/dracula/manifest does not contain 27 chapters")
    elif not any(chapter.get("is_preview") is True for chapter in chapters if isinstance(chapter, dict)):
        issues.append("/reader/book/dracula/manifest does not unlock a preview chapter")
    audio = payload.get("audio")
    if isinstance(audio, dict):
        if audio.get("enabled") is not False:
            issues.append("/reader/book/dracula/manifest audio.enabled is not false")
        if audio.get("url") or audio.get("assets"):
            issues.append("/reader/book/dracula/manifest exposes audio URLs/assets")
    book = payload.get("book")
    if isinstance(book, dict):
        issues.extend(verify_dracula_detail_payload(book))
    return issues


def verify_live_manifest_payload(endpoint: str, payload: Any, slug: str, *, audio_allowed: bool = False) -> list[str]:
    if normalize_slug(slug) == LIVE_APPROVED_SLUG:
        return verify_dracula_manifest_payload(payload)
    issues = safe_field_issues(endpoint, payload)
    if not isinstance(payload, dict):
        return [*issues, f"{endpoint} did not return a JSON object"]
    chapters = payload.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        issues.append(f"{endpoint} does not contain chapter metadata")
    audio = payload.get("audio")
    if isinstance(audio, dict):
        if audio_allowed:
            if audio.get("enabled") is not True:
                issues.append(f"{endpoint} audio.enabled is not true for an audio-enabled controlled slug")
            assets = audio.get("assets") if isinstance(audio.get("assets"), dict) else {}
            if not normalize_text(audio.get("url")) or not assets:
                issues.append(f"{endpoint} is missing synced audiobook url/assets for an audio-enabled controlled slug")
        elif audio.get("enabled") is not False:
            issues.append(f"{endpoint} audio.enabled is not false")
        if not audio_allowed and (audio.get("url") or audio.get("assets")):
            issues.append(f"{endpoint} exposes audio URLs/assets")
    book = payload.get("book")
    if isinstance(book, dict):
        manifest_preview_ids = set(explicit_preview_chapter_ids(payload))
        book_preview_ids = set(explicit_preview_chapter_ids(book))
        if manifest_preview_ids != book_preview_ids:
            issues.append(f"{endpoint} preview chapters do not match its projected book")
        issues.extend(verify_live_detail_payload(f"{endpoint}.book", book, slug))
    return issues


def verify_api_audit(
    *,
    books_rows: list[dict[str, Any]],
    all_rows: list[dict[str, Any]],
    endpoints: dict[str, EndpointResult],
    controlled_live_slugs: list[str],
    audio_enabled_slugs: set[str],
) -> list[str]:
    blockers: list[str] = []
    books_result = endpoints["/books"]
    if books_result.status != 200 or not isinstance(books_result.json_data, list):
        blockers.append("/books did not return a 200 JSON list")

    live_readable = [
        row
        for row in books_rows
        if row["classification"] == PUBLIC_STATUS_LIVE_APPROVED or row["reader_enabled"] or row["preview_enabled"]
    ]
    expected_live_slugs = sorted({normalize_slug(slug) for slug in controlled_live_slugs if normalize_slug(slug)})
    live_readable_slugs = sorted({row["slug"] for row in live_readable})
    missing_live = sorted(set(expected_live_slugs) - set(live_readable_slugs))
    unexpected_live = sorted(set(live_readable_slugs) - set(expected_live_slugs))
    if missing_live:
        blockers.append(f"/books is missing controlled live slugs: {missing_live}")
    if unexpected_live:
        blockers.append(f"/books exposes unexpected live readable slugs: {unexpected_live}")

    if not any(row["slug"] == LIVE_APPROVED_SLUG and row in live_readable for row in books_rows):
        blockers.append("/books does not contain Dracula as the live readable item")

    for row in books_rows:
        if row["slug"] not in expected_live_slugs and row["reader_enabled"]:
            blockers.append(f"Unexpected reader exposure in /books: {row['slug']}")
        if row["slug"] not in expected_live_slugs and row["preview_enabled"]:
            blockers.append(f"Unexpected preview exposure in /books: {row['slug']}")
        if row["audio_enabled"] and row["slug"] not in audio_enabled_slugs:
            blockers.append(f"Audio exposure detected in /books: {row['slug']}")
        if row["slug"] in PIPELINE_CANDIDATE_SLUGS and (
            row["classification"] != PUBLIC_STATUS_PIPELINE_CANDIDATE
            or row["reader_enabled"]
            or row["preview_enabled"]
            or row["audio_enabled"]
        ):
            blockers.append(f"Kshudhita Pashan is not pipeline-only in /books: {row['classification']}")

    if endpoints["/books/dracula"].status != 200:
        blockers.append("/books/dracula did not return 200")
    else:
        blockers.extend(verify_dracula_detail_payload(endpoints["/books/dracula"].json_data))

    for slug in expected_live_slugs:
        detail_path = f"/books/{slug}"
        if detail_path not in endpoints:
            blockers.append(f"{detail_path} was not audited")
            continue
        if endpoints[detail_path].status != 200:
            blockers.append(f"{detail_path} did not return 200")
        elif slug != LIVE_APPROVED_SLUG:
            blockers.extend(verify_live_detail_payload(detail_path, endpoints[detail_path].json_data, slug))

        manifest_path = f"/reader/book/{slug}/manifest"
        if manifest_path not in endpoints:
            blockers.append(f"{manifest_path} was not audited")
            continue
        if endpoints[manifest_path].status != 200:
            blockers.append(f"{manifest_path} did not return 200")
        else:
            blockers.extend(
                verify_live_manifest_payload(
                    manifest_path,
                    endpoints[manifest_path].json_data,
                    slug,
                    audio_allowed=slug in audio_enabled_slugs,
                )
            )

    kshudhita_detail = endpoints["/books/kshudhita-pashan"]
    if kshudhita_detail.status == 200:
        blockers.extend(verify_pipeline_detail_payload("/books/kshudhita-pashan", kshudhita_detail.json_data))
        kshudhita_row = next((row for row in all_rows if row["slug"] == "kshudhita-pashan"), None)
        if not kshudhita_row or kshudhita_row["classification"] != PUBLIC_STATUS_PIPELINE_CANDIDATE:
            blockers.append("/books/kshudhita-pashan returned 200 but is not pipeline-only")
        elif kshudhita_row["reader_enabled"] or kshudhita_row["preview_enabled"] or kshudhita_row["audio_enabled"]:
            blockers.append("/books/kshudhita-pashan returned public reader/preview/audio exposure")
    elif kshudhita_detail.status not in {403, 404}:
        blockers.append(f"/books/kshudhita-pashan returned {kshudhita_detail.status}; expected 403/404 or safe pipeline")

    if endpoints["/reader/book/dracula/manifest"].status != 200:
        blockers.append("/reader/book/dracula/manifest did not return 200")
    else:
        blockers.extend(verify_dracula_manifest_payload(endpoints["/reader/book/dracula/manifest"].json_data))
    if endpoints["/reader/book/kshudhita-pashan/manifest"].status not in {403, 404}:
        blockers.append("/reader/book/kshudhita-pashan/manifest did not return 403/404")
    if endpoints["/reader/book/dracula/audiobook"].status != 404:
        blockers.append("/reader/book/dracula/audiobook did not return 404 while audio is disabled")
    if endpoints["/reader/book/kshudhita-pashan/audiobook"].status != 404:
        blockers.append("/reader/book/kshudhita-pashan/audiobook did not return 404")

    return blockers


def api_audit_result(
    api_url: str,
    *,
    timeout_ms: int = 10_000,
    fetcher=fetch_api_endpoint,
) -> dict[str, Any]:
    urls = sitemap_urls(ROOT / "frontend" / "public" / "sitemap.xml")
    endpoints = fetch_api_endpoints(api_url, API_AUDIT_PATHS, timeout_ms=timeout_ms, fetcher=fetcher)
    status_payload = endpoints["/controlled-launch/status"].json_data
    status_slugs = []
    status_audio_slugs = []
    if isinstance(status_payload, dict) and isinstance(status_payload.get("live_approved_slugs"), list):
        status_slugs = [normalize_slug(slug) for slug in status_payload["live_approved_slugs"] if normalize_slug(slug)]
    if isinstance(status_payload, dict) and isinstance(status_payload.get("audio_enabled_slugs"), list):
        status_audio_slugs = [
            normalize_slug(slug)
            for slug in status_payload["audio_enabled_slugs"]
            if normalize_slug(slug)
        ]
    controlled_live_slugs = status_slugs or [normalize_slug(slug) for slug in CONTROLLED_LIVE_BOOK_SLUGS]
    audio_enabled_slugs = set(status_audio_slugs or [normalize_slug(slug) for slug in AUDIO_ENABLED_SLUGS])
    live_paths = [
        path
        for slug in controlled_live_slugs
        for path in (f"/books/{slug}", f"/reader/book/{slug}/manifest")
        if path not in endpoints
    ]
    endpoints.update(fetch_api_endpoints(api_url, live_paths, timeout_ms=timeout_ms, fetcher=fetcher))
    books_rows = api_books_rows(endpoints["/books"].json_data, sitemap_urls=urls)
    rows = list(books_rows)
    seen_slugs = {row["slug"] for row in rows}
    detail_paths = [f"/books/{slug}" for slug in controlled_live_slugs]
    detail_paths.append("/books/kshudhita-pashan")
    for path in detail_paths:
        if endpoints[path].status == 200:
            row = api_detail_row(endpoints[path].json_data, sitemap_urls=urls)
            if row and row["slug"] not in seen_slugs:
                rows.append(row)
                seen_slugs.add(row["slug"])

    summary = catalog_truth_summary(rows, sitemap_urls=urls, frontend_live_slugs=frontend_controlled_live_slugs())
    api_blockers = verify_api_audit(
        books_rows=books_rows,
        all_rows=rows,
        endpoints=endpoints,
        controlled_live_slugs=controlled_live_slugs,
        audio_enabled_slugs=audio_enabled_slugs,
    )
    summary["mode"] = "api"
    summary["api_url"] = api_url.rstrip("/")
    summary["audio_enabled_slugs"] = sorted(audio_enabled_slugs)
    summary["api_endpoint_statuses"] = api_endpoint_statuses(endpoints)
    summary["api_blockers"] = api_blockers
    summary["launch_blockers"] = [*summary.get("launch_blockers", []), *api_blockers]
    return {"summary": summary, "rows": rows}


def local_fixture_audit_result() -> dict[str, Any]:
    urls = sitemap_urls(ROOT / "frontend" / "public" / "sitemap.xml")
    rows = [catalog_truth_row(record, sitemap_urls=urls) for record in audit_records()]
    summary = catalog_truth_summary(rows, sitemap_urls=urls, frontend_live_slugs=frontend_controlled_live_slugs())
    summary["mode"] = "local-fixture"
    return {"summary": summary, "rows": rows}


def csv_text(rows: list[dict[str, Any]]) -> str:
    output = []
    writer_buffer = CsvBuffer(output)
    writer = csv.DictWriter(writer_buffer, fieldnames=REPORT_FIELDS)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in REPORT_FIELDS})
    return "".join(output)


class CsvBuffer:
    def __init__(self, chunks: list[str]):
        self.chunks = chunks

    def write(self, value: str) -> int:
        self.chunks.append(value)
        return len(value)


def markdown_report(rows: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    blockers = summary.get("launch_blockers") or []
    mode = summary.get("mode", "local-fixture")
    lines = [
        "# Backend Catalog Truth Audit",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Mode: {mode}, dry-run report only",
        "",
        "## Launch Truth",
        "",
        "- Controlled live slugs are governed by the backend controlled-launch status allowlist.",
        "- Dracula remains the first controlled core reading release and its public audiobook stays disabled.",
        "- Synced audiobook manifest access is allowed only for controlled audio-enabled slugs.",
        "- Kshudhita Pashan remains pipeline-only.",
        "- No Tier B, Tier C, or unapproved title may expose reader or audio CTAs.",
        "",
        "## Summary",
        "",
        f"- Live approved count: {summary['live_approved_count']}",
        f"- Dracula-only live approved: {summary['dracula_only_live_approved']}",
        f"- Pipeline candidate count: {summary['pipeline_candidate_count']}",
        f"- Unapproved reader link count: {summary['unapproved_reader_link_count']}",
        f"- Unapproved audio link count: {summary['unapproved_audio_link_count']}",
        f"- Unapproved sitemap count: {summary['unapproved_sitemap_count']}",
        f"- Backend live approved slugs: {', '.join(summary.get('backend_live_approved_slugs', [])) or 'none'}",
        f"- Frontend controlled live slugs: {', '.join(summary.get('frontend_controlled_live_slugs', [])) or 'not checked'}",
        f"- Backend/frontend truth mismatch: {summary.get('backend_frontend_truth_mismatch')}",
        "",
        "## Matrix",
        "",
        "| Slug | Classification | Reader | Preview | Audio | Sitemap |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {slug} | {classification} | {reader_enabled} | {preview_enabled} | "
            "{audio_enabled} | {sitemap_inclusion} |".format(**row)
        )
    lines.extend(["", "## Blockers", ""])
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- None.")
    if summary.get("api_endpoint_statuses"):
        lines.extend(["", "## API Endpoint Statuses", ""])
        for path, status in summary["api_endpoint_statuses"].items():
            lines.append(f"- `{path}`: `{status['status']}`")
    lines.extend(
        [
            "",
            "## Owner Decision",
            "",
            "GO for Dracula-only backend catalog truth if validation remains green.",
            "HOLD for any unapproved reader link, audio link, or sitemap inclusion.",
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(
    output_dir: Path,
    *,
    mode: str = "local-fixture",
    api_url: str = "",
    timeout_ms: int = 10_000,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    if mode == "api":
        result = api_audit_result(api_url, timeout_ms=timeout_ms)
    else:
        result = local_fixture_audit_result()
    rows = result["rows"]
    summary = result["summary"]
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "catalog_truth_report.json"
    md_path = output_dir / "catalog_truth_report.md"
    csv_path = output_dir / "catalog_truth_matrix.csv"
    json_path.write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(markdown_report(rows, summary), encoding="utf-8")
    csv_path.write_text(csv_text(rows), encoding="utf-8")
    return json_path, md_path, csv_path, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "output" / "daily" / date.today().isoformat(),
        help="Local output directory for dry-run reports.",
    )
    parser.add_argument("--mode", choices=["local-fixture", "api"], default="local-fixture")
    parser.add_argument("--api-url", default="", help="Base API URL, for example https://api.theearnalism.com/api")
    parser.add_argument("--timeout-ms", type=int, default=10_000)
    args = parser.parse_args()
    if args.mode == "api" and not args.api_url:
        parser.error("--api-url is required when --mode api is used")
    json_path, md_path, csv_path, summary = write_reports(
        args.output_dir,
        mode=args.mode,
        api_url=args.api_url,
        timeout_ms=args.timeout_ms,
    )
    print(f"Catalog truth audit complete: json={json_path} markdown={md_path} csv={csv_path}")
    blockers = summary.get("launch_blockers") or []
    if blockers:
        print("Catalog truth audit HOLD:")
        for blocker in blockers:
            print(f"- {blocker}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
