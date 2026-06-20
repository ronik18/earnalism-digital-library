#!/usr/bin/env python3
"""Generate the Dracula-only backend catalog truth audit in dry-run mode."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
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
    LIVE_APPROVED_SLUG,
    PIPELINE_CANDIDATE_SLUGS,
    PUBLIC_STATUS_COMING_SOON,
    PUBLIC_STATUS_LIVE_APPROVED,
    PUBLIC_STATUS_PIPELINE_CANDIDATE,
    catalog_truth_row,
    catalog_truth_summary,
    dracula_approval_evidence,
    normalize_slug,
    normalize_text,
    normalize_upper,
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
    "/reader/book/dracula/manifest",
    "/reader/book/kshudhita-pashan/manifest",
    "/reader/book/dracula/audiobook",
    "/reader/book/kshudhita-pashan/audiobook",
]


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


def audit_records() -> list[dict[str, Any]]:
    return [dracula_record(), *pipeline_candidate_records()]


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
    return truthy(book.get("preview_enabled")) or bool(normalize_text(book.get("preview_url")))


def api_audio_enabled(book: dict[str, Any]) -> bool:
    audiobook = book.get("audiobook") if isinstance(book.get("audiobook"), dict) else {}
    assets = book.get("audiobook_assets") if isinstance(book.get("audiobook_assets"), dict) else {}
    nested_assets = audiobook.get("assets") if isinstance(audiobook.get("assets"), dict) else {}
    return any(
        [
            truthy(book.get("audio_enabled")),
            truthy(book.get("audiobook_enabled")),
            truthy(book.get("generate_audiobook")),
            bool(normalize_text(book.get("audio_url"))),
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


def verify_api_audit(
    *,
    books_rows: list[dict[str, Any]],
    all_rows: list[dict[str, Any]],
    endpoints: dict[str, EndpointResult],
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
    live_readable_slugs = sorted(row["slug"] for row in live_readable)
    if live_readable_slugs != [LIVE_APPROVED_SLUG]:
        blockers.append(f"/books live readable slugs are {live_readable_slugs}; expected ['dracula']")

    if not any(row["slug"] == LIVE_APPROVED_SLUG and row in live_readable for row in books_rows):
        blockers.append("/books does not contain Dracula as the live readable item")

    for row in books_rows:
        if row["slug"] != LIVE_APPROVED_SLUG and row["reader_enabled"]:
            blockers.append(f"Non-Dracula reader exposure in /books: {row['slug']}")
        if row["slug"] != LIVE_APPROVED_SLUG and row["preview_enabled"]:
            blockers.append(f"Non-Dracula preview exposure in /books: {row['slug']}")
        if row["audio_enabled"]:
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

    kshudhita_detail = endpoints["/books/kshudhita-pashan"]
    if kshudhita_detail.status == 200:
        kshudhita_row = next((row for row in all_rows if row["slug"] == "kshudhita-pashan"), None)
        if not kshudhita_row or kshudhita_row["classification"] != PUBLIC_STATUS_PIPELINE_CANDIDATE:
            blockers.append("/books/kshudhita-pashan returned 200 but is not pipeline-only")
        elif kshudhita_row["reader_enabled"] or kshudhita_row["preview_enabled"] or kshudhita_row["audio_enabled"]:
            blockers.append("/books/kshudhita-pashan returned public reader/preview/audio exposure")
    elif kshudhita_detail.status not in {403, 404}:
        blockers.append(f"/books/kshudhita-pashan returned {kshudhita_detail.status}; expected 403/404 or safe pipeline")

    if endpoints["/reader/book/dracula/manifest"].status != 200:
        blockers.append("/reader/book/dracula/manifest did not return 200")
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
    endpoints = {
        path: fetcher(api_url, path, timeout_ms=timeout_ms)
        for path in API_AUDIT_PATHS
    }
    books_rows = api_books_rows(endpoints["/books"].json_data, sitemap_urls=urls)
    rows = list(books_rows)
    seen_slugs = {row["slug"] for row in rows}
    for path in ("/books/dracula", "/books/kshudhita-pashan"):
        if endpoints[path].status == 200:
            row = api_detail_row(endpoints[path].json_data, sitemap_urls=urls)
            if row and row["slug"] not in seen_slugs:
                rows.append(row)
                seen_slugs.add(row["slug"])

    summary = catalog_truth_summary(rows, sitemap_urls=urls, frontend_live_slugs=frontend_controlled_live_slugs())
    api_blockers = verify_api_audit(books_rows=books_rows, all_rows=rows, endpoints=endpoints)
    summary["mode"] = "api"
    summary["api_url"] = api_url.rstrip("/")
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
        "- Dracula is the only live approved core reading candidate.",
        "- Dracula audio is disabled.",
        "- Kshudhita Pashan remains pipeline-only.",
        "- No Tier B, Tier C, or unapproved title may expose reader/audio CTAs.",
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
