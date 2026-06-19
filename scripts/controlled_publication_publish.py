#!/usr/bin/env python3
"""Controlled publication activator for approved Tier A core reading items.

This script is deliberately narrow for the first activation:
- only the approved Dracula core reading candidate may be published;
- Tier B and Tier C items are never published;
- audiobook, full study guide, full visual edition, ads, email, and social
  campaign publication are explicitly excluded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from pymongo import MongoClient


ROOT = Path(__file__).resolve().parents[1]
APPROVED_FILE = ROOT / "APPROVED_TO_PUBLISH.md"
OUTPUT_DIR = ROOT / "output" / "publication_candidates" / "dracula"
SOURCE_EVIDENCE = OUTPUT_DIR / "source_evidence.json"
GATE_RESULTS = OUTPUT_DIR / "dracula_gate_results.json"
SOURCE_HASHES = OUTPUT_DIR / "source_hashes.json"
REPORT_FILE = ROOT / "PUBLICATION_REPORT.md"
ALLOWED_SLUG = "dracula"
GO_RECOMMENDATION = "GO_FOR_CONTROLLED_PUBLICATION_FOR_DRACULA_ONLY"
READY_WORKFLOW_STATUSES = {"READY", "READY_FOR_PUBLICATION_DRAFT_CANDIDATE"}
PAYMENT_PASS_STATUSES = {"PASS", "PASS_TEST_MODE", "PRODUCTION_TEST_MODE_PASS"}
APPROVAL_SCOPE_REQUIRED_TEXT = [
    "Approved Scope: Dracula core reading candidate only.",
    "Not Approved: full study guide, full visual edition, full audiobook",
    "Audiobook Status: AUDIO_NOT_REQUIRED.",
]


@dataclass
class ValidationContext:
    approved_item: dict[str, str]
    source_evidence: dict[str, Any]
    gate_results: dict[str, Any]
    source_hashes: dict[str, Any]
    approval_text: str


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_approved_items(text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading = re.match(r"^#{2,6}\s+(.+)$", line)
        if heading:
            if current:
                items.append(current)
            current = {"work_title": heading.group(1).strip()}
            continue
        field = re.match(r"^(?:[-*]\s*)?([A-Za-z][A-Za-z0-9 _-]+)\s*:\s*(.+)$", line)
        if field:
            if not current:
                current = {}
            current[normalize_key(field.group(1))] = field.group(2).strip()
    if current:
        items.append(current)
    return [item for item in items if item.get("work_slug") or item.get("work_title")]


def load_validation_context(approved_path: Path = APPROVED_FILE) -> tuple[ValidationContext | None, list[str]]:
    issues: list[str] = []
    if not approved_path.exists():
        return None, ["APPROVED_TO_PUBLISH.md is required."]
    approval_text = approved_path.read_text(encoding="utf-8")
    items = [item for item in parse_approved_items(approval_text) if item.get("work_slug")]
    if len(items) != 1:
        issues.append(f"Exactly one approved item is required; found {len(items)}.")
    approved_item = items[0] if items else {}
    context = ValidationContext(
        approved_item=approved_item,
        source_evidence=read_json(SOURCE_EVIDENCE),
        gate_results=read_json(GATE_RESULTS),
        source_hashes=read_json(SOURCE_HASHES),
        approval_text=approval_text,
    )
    return context, issues


def validate_approval_scope(context: ValidationContext) -> list[str]:
    item = context.approved_item
    text = context.approval_text
    issues: list[str] = []
    if item.get("work_slug") != ALLOWED_SLUG:
        issues.append("Only Dracula may be published by this controlled activation.")
    if str(item.get("rights_tier", "")).upper() != "A":
        issues.append("Approved item must be Tier A.")
    if str(item.get("verification_status", "")).lower() != "approved":
        issues.append("Approved item verification_status must be approved.")
    if str(item.get("qa_status", "")).upper() != "QA_PASSED":
        issues.append("Approved item qa_status must be QA_PASSED.")
    if str(item.get("production_parity_status", "")).upper() != "PASS":
        issues.append("Production parity status must be PASS.")
    if str(item.get("payment_smoke_status", "")).upper() not in PAYMENT_PASS_STATUSES:
        issues.append("Payment smoke status must be PASS, PASS_TEST_MODE, or PRODUCTION_TEST_MODE_PASS.")
    publication_cap = item.get("publication_cap", "")
    if "Dracula controlled-publication candidate only" not in publication_cap:
        issues.append("Publication cap must restrict activation to Dracula only.")
    if "public_publish_actions=0" not in publication_cap:
        issues.append("Publication cap must preserve public_publish_actions=0 before this activation.")
    for required in APPROVAL_SCOPE_REQUIRED_TEXT:
        if required not in text:
            issues.append(f"Approval scope is missing required exclusion text: {required}")
    return issues


def validate_evidence_hashes(context: ValidationContext) -> list[str]:
    item = context.approved_item
    checks = {
        "production_parity_evidence_hash": ROOT / item.get("production_parity_evidence", ""),
        "payment_smoke_evidence_hash": ROOT / item.get("payment_smoke_evidence", ""),
        "source_evidence_hash": ROOT / item.get("source_evidence", ""),
        "gate_results_hash": ROOT / item.get("gate_results_evidence", ""),
    }
    issues: list[str] = []
    for field, path in checks.items():
        expected = item.get(field, "")
        if not expected:
            issues.append(f"{field} is required.")
            continue
        if not path.exists():
            issues.append(f"{field} target does not exist: {path}")
            continue
        actual = file_sha256(path)
        if actual != expected:
            issues.append(f"{field} mismatch for {path}: expected {expected}, got {actual}.")
    return issues


def validate_source_and_gate(context: ValidationContext) -> list[str]:
    source = context.source_evidence
    gate = context.gate_results
    source_hashes = context.source_hashes
    issues: list[str] = []
    if source.get("slug") != ALLOWED_SLUG:
        issues.append("source_evidence.slug must be dracula.")
    if source.get("rights_tier") != "A":
        issues.append("source_evidence.rights_tier must be A.")
    if str(source.get("verification_status", "")).lower() != "approved":
        issues.append("source_evidence.verification_status must be approved.")
    if source.get("qa_status") != "QA_PASSED":
        issues.append("source_evidence.qa_status must be QA_PASSED.")
    if int(source.get("meaningful_chapter_count") or 0) < 25:
        issues.append("source_evidence.meaningful_chapter_count must be at least 25.")

    ingestion = source.get("ingestion") if isinstance(source.get("ingestion"), dict) else {}
    for key in ("source_hash", "content_hash", "provenance_hash"):
        expected = str(source.get(key) or "")
        if not expected:
            issues.append(f"{key} is required.")
        if str(ingestion.get(key) or "") != expected:
            issues.append(f"ingestion.{key} must match source_evidence.{key}.")
        if str(source_hashes.get(key) or "") != expected:
            issues.append(f"source_hashes.{key} must match source_evidence.{key}.")

    workflow_status = str(gate.get("publishing_workflow_status") or "").upper()
    if workflow_status not in READY_WORKFLOW_STATUSES:
        issues.append("dracula_gate_results.publishing_workflow_status must be ready.")
    workflow = gate.get("workflow") if isinstance(gate.get("workflow"), dict) else {}
    blockers = workflow.get("blockers") if isinstance(workflow.get("blockers"), list) else []
    if blockers:
        issues.append(f"Workflow blockers must be empty: {'; '.join(str(blocker) for blocker in blockers)}")
    if gate.get("recommendation") != GO_RECOMMENDATION:
        issues.append(f"Gate recommendation must be {GO_RECOMMENDATION}.")
    high_blockers = gate.get("high_blockers") if isinstance(gate.get("high_blockers"), list) else []
    if high_blockers:
        issues.append(f"Gate high_blockers must be empty: {'; '.join(str(blocker) for blocker in high_blockers)}")
    if gate.get("audio_status") != "AUDIO_NOT_REQUIRED":
        issues.append("Gate audio_status must be AUDIO_NOT_REQUIRED for this core reading activation.")
    return issues


def validate_context(context: ValidationContext) -> list[str]:
    return [
        *validate_approval_scope(context),
        *validate_evidence_hashes(context),
        *validate_source_and_gate(context),
    ]


def database_name_from_mongo_url(url: str) -> str:
    parsed = urlparse(url)
    db_name = parsed.path.lstrip("/").split("/", 1)[0]
    return db_name or "earnalism"


def rights_metadata_from_source(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "work_title": source.get("title", "Dracula"),
        "work_slug": ALLOWED_SLUG,
        "author_name": source.get("author", "Bram Stoker"),
        "author_death_year": int(source.get("author_death_year") or 1912),
        "original_publication_year": int(source.get("original_publication_year") or 1897),
        "country_of_origin": "United Kingdom",
        "source_url": source.get("source_url", ""),
        "source_name": source.get("source_name", ""),
        "source_license": source.get("source_license", ""),
        "source_hash": source.get("source_hash", ""),
        "content_hash": source.get("content_hash", ""),
        "provenance_hash": source.get("provenance_hash", ""),
        "translator_name": "",
        "translator_death_year": None,
        "illustrator_name": "",
        "illustrator_death_year": None,
        "editor_name": "",
        "edition_publication_year": None,
        "rights_tier": "A",
        "verification_status": "approved",
        "blocked_reason": "",
        "publication_region": "global",
        "verified_at": source.get("generated_at") or utc_now(),
    }


def controlled_publication_update(source: dict[str, Any], *, now: str) -> dict[str, Any]:
    return {
        "is_published": True,
        "rights_metadata": rights_metadata_from_source(source),
        "audiobook_enabled": False,
        "generate_audiobook": False,
        "audiobook_provider": "",
        "audiobook_voice": "",
        "audio_asset_slug": "",
        "audiobook_assets": {},
        "audiobook": {},
        "audiobook_assets_updated_at": now,
        "controlled_publication_status": "PUBLISHED_CORE_READING_ONLY",
        "controlled_publication_slug": ALLOWED_SLUG,
        "controlled_publication_scope": "core_reading_candidate_only",
        "controlled_publication_at": now,
    }


def public_state(book: dict[str, Any] | None) -> dict[str, Any]:
    if not book:
        return {}
    chapters = book.get("chapters") if isinstance(book.get("chapters"), list) else []
    return {
        "exists": True,
        "slug": book.get("slug"),
        "title": book.get("title"),
        "is_published": bool(book.get("is_published")),
        "rights_tier": (book.get("rights_metadata") or {}).get("rights_tier"),
        "verification_status": (book.get("rights_metadata") or {}).get("verification_status"),
        "chapter_count": len(chapters),
        "preview_chapter_count": sum(1 for chapter in chapters if chapter.get("is_preview")),
        "audiobook_enabled": bool(book.get("audiobook_enabled")),
        "generate_audiobook": bool(book.get("generate_audiobook")),
        "audiobook_provider": book.get("audiobook_provider", ""),
        "audio_asset_count": len(book.get("audiobook_assets") or {}),
        "controlled_publication_status": book.get("controlled_publication_status", ""),
    }


def rollback_plan(previous_state: dict[str, Any]) -> list[str]:
    return [
        "Run a targeted MongoDB update for slug `dracula` only.",
        f"Restore `is_published` to `{previous_state.get('is_published')}`.",
        "Restore previous `rights_metadata` only if rights rollback is legally required.",
        "Restore previous audiobook fields only after separate audiobook QA approval.",
        "Increment Redis `public-cache:generation` and `reader-content-cache:generation` after rollback.",
        "Re-run live checks for /api/books/dracula and /api/reader/book/dracula/manifest.",
    ]


def redis_key(prefix: str, *parts: str) -> str:
    cleaned = [re.sub(r"[^a-zA-Z0-9_.:-]", "_", str(part)) for part in parts if str(part)]
    return ":".join([prefix, *cleaned])


def invalidate_redis_cache_generations() -> dict[str, Any]:
    redis_url = os.environ.get("REDIS_URL", "").strip()
    if not redis_url:
        return {"attempted": False, "reason": "REDIS_URL not configured in this process."}
    try:
        import redis  # type: ignore
    except Exception as exc:
        return {"attempted": False, "reason": f"redis package unavailable: {exc}"}
    prefix = os.environ.get("REDIS_KEY_PREFIX", "earnalism").strip() or "earnalism"
    client = redis.Redis.from_url(redis_url, socket_connect_timeout=5, socket_timeout=5)
    public_generation = client.incr(redis_key(prefix, "public-cache", "generation"))
    reader_generation = client.incr(redis_key(prefix, "reader-content-cache", "generation"))
    return {
        "attempted": True,
        "public_cache_generation": int(public_generation),
        "reader_content_cache_generation": int(reader_generation),
    }


def fetch_json(url: str, *, timeout: int = 20) -> tuple[int, dict[str, Any]]:
    request = Request(url, headers={"User-Agent": "EarnalismControlledPublication/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - verification against owned production endpoints.
            body = response.read().decode("utf-8", errors="replace")
            return int(response.status), json.loads(body)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"body": body[:500]}
        return int(exc.code), payload
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return 0, {"error": str(exc)}


def live_verify(api_base_url: str, web_base_url: str) -> dict[str, Any]:
    api = api_base_url.rstrip("/")
    web = web_base_url.rstrip("/")
    book_status, book = fetch_json(f"{api}/books/{ALLOWED_SLUG}")
    manifest_status, manifest = fetch_json(f"{api}/reader/book/{ALLOWED_SLUG}/manifest")
    first_chapter = ((manifest.get("chapters") or [{}])[0] or {}) if isinstance(manifest, dict) else {}
    chapter_url = first_chapter.get("content_url", "")
    chapter_status = 0
    chapter_payload: dict[str, Any] = {}
    if chapter_url:
        chapter_status, chapter_payload = fetch_json(f"{api}{chapter_url}")
    audiobook_status, audiobook_payload = fetch_json(f"{api}/reader/book/{ALLOWED_SLUG}/audiobook")
    html_status = 0
    try:
        request = Request(f"{web}/book/{ALLOWED_SLUG}", method="HEAD")
        with urlopen(request, timeout=20) as response:  # noqa: S310 - verification against owned production endpoint.
            html_status = int(response.status)
    except HTTPError as exc:
        html_status = int(exc.code)
    except (URLError, TimeoutError, OSError):
        html_status = 0

    audio = manifest.get("audio") if isinstance(manifest.get("audio"), dict) else {}
    chapter_content = ((chapter_payload.get("chapter") or {}).get("content") or "") if isinstance(chapter_payload, dict) else ""
    return {
        "book_api_status": book_status,
        "book_slug": book.get("slug") if isinstance(book, dict) else "",
        "book_is_published": bool(book.get("is_published")) if isinstance(book, dict) else False,
        "reader_manifest_status": manifest_status,
        "manifest_chapter_count": len(manifest.get("chapters") or []) if isinstance(manifest, dict) else 0,
        "manifest_audio_enabled": bool(audio.get("enabled")),
        "manifest_audio_asset_count": len(audio.get("assets") or {}),
        "preview_chapter_status": chapter_status,
        "preview_chapter_unlocked": chapter_payload.get("locked") is False if isinstance(chapter_payload, dict) else False,
        "preview_chapter_content_length": len(chapter_content),
        "audiobook_endpoint_status": audiobook_status,
        "book_page_status": html_status,
        "pass": (
            book_status == 200
            and manifest_status == 200
            and chapter_status == 200
            and chapter_payload.get("locked") is False
            and len(chapter_content) > 1000
            and bool(audio.get("enabled")) is False
            and audiobook_status in {404, 503}
            and html_status == 200
        ),
        "audiobook_endpoint_payload": audiobook_payload if audiobook_status not in {404, 503} else {},
    }


def write_publication_report(payload: dict[str, Any], path: Path = REPORT_FILE) -> None:
    lines = [
        "# Publication Report",
        "",
        f"Generated at: `{payload['generated_at']}`",
        f"Mode: `{'commit' if payload['commit'] else 'dry-run'}`",
        f"Status: `{payload['status']}`",
        "",
        "## Scope",
        "",
        "- Published item: `dracula` only.",
        "- Rights allowed: Tier A approved only.",
        "- Tier B items: not published.",
        "- Tier C items: not published.",
        "- Excluded: full study guide, full visual edition, full audiobook, ads, emails, and social campaigns.",
        "- Publication cap respected: Dracula core reading candidate only.",
        "",
        "## Production Mutation",
        "",
        f"- Mutation performed: `{payload['mutation_performed']}`",
        f"- Matched database rows: `{payload.get('matched_count', 0)}`",
        f"- Modified database rows: `{payload.get('modified_count', 0)}`",
        f"- Cache invalidation: `{payload.get('cache_invalidation', {})}`",
        "",
        "## Before State",
        "",
        "```json",
        json.dumps(payload.get("before_state", {}), indent=2, ensure_ascii=False),
        "```",
        "",
        "## After State",
        "",
        "```json",
        json.dumps(payload.get("after_state", {}), indent=2, ensure_ascii=False),
        "```",
        "",
        "## Live Verification",
        "",
        "```json",
        json.dumps(payload.get("live_verification", {}), indent=2, ensure_ascii=False),
        "```",
        "",
        "## Rollback Plan",
        "",
        *[f"- {step}" for step in payload.get("rollback_plan", [])],
        "",
        "## Notes",
        "",
        "- No Tier B or Tier C item was changed.",
        "- No audiobook asset was published by this activation.",
        "- No ad, email, social, LLM, TTS, STT, OCR, image, or paid provider call was performed.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def publish(args: argparse.Namespace) -> dict[str, Any]:
    context, issues = load_validation_context()
    if context is not None:
        issues.extend(validate_context(context))
    commit_allowed = os.environ.get("EARNALISM_ALLOW_CONTROLLED_PUBLICATION", "").strip().lower() == "true"
    if args.slug != ALLOWED_SLUG:
        issues.append("Only --slug dracula is allowed.")
    if args.commit and not commit_allowed:
        issues.append("EARNALISM_ALLOW_CONTROLLED_PUBLICATION=true is required with --commit.")

    payload: dict[str, Any] = {
        "generated_at": utc_now(),
        "commit": bool(args.commit),
        "status": "BLOCKED" if issues else ("PUBLISHED" if args.commit else "DRY_RUN_READY"),
        "issues": issues,
        "mutation_performed": False,
        "matched_count": 0,
        "modified_count": 0,
        "before_state": {},
        "after_state": {},
        "cache_invalidation": {},
        "live_verification": {},
        "rollback_plan": [],
    }
    if issues:
        write_publication_report(payload, Path(args.report))
        return payload

    assert context is not None
    mongo_url = os.environ.get("MONGODB_URL") or os.environ.get("MONGO_URL")
    if not mongo_url:
        if args.commit:
            payload["status"] = "BLOCKED"
            payload["issues"].append("MONGODB_URL or MONGO_URL is required.")
        else:
            payload["status"] = "DRY_RUN_READY"
            payload["rollback_plan"] = rollback_plan({"is_published": "previous production value"})
            payload["cache_invalidation"] = {"attempted": False, "reason": "dry-run without database environment"}
        write_publication_report(payload, Path(args.report))
        return payload

    client = MongoClient(mongo_url, serverSelectionTimeoutMS=15000, uuidRepresentation="standard")
    db_name = os.environ.get("DB_NAME") or database_name_from_mongo_url(mongo_url)
    db = client[db_name]
    before = db.books.find_one({"slug": ALLOWED_SLUG}, {"_id": 0}) or {}
    payload["before_state"] = public_state(before)
    if not before:
        payload["status"] = "BLOCKED"
        payload["issues"].append("Dracula book record was not found.")
        write_publication_report(payload, Path(args.report))
        return payload

    update = controlled_publication_update(context.source_evidence, now=payload["generated_at"])
    payload["rollback_plan"] = rollback_plan(payload["before_state"])
    if args.commit:
        result = db.books.update_one({"slug": ALLOWED_SLUG}, {"$set": update})
        payload["matched_count"] = int(result.matched_count)
        payload["modified_count"] = int(result.modified_count)
        payload["mutation_performed"] = True
        payload["cache_invalidation"] = invalidate_redis_cache_generations()
    else:
        payload["matched_count"] = 1
        payload["modified_count"] = 0
        payload["cache_invalidation"] = {"attempted": False, "reason": "dry-run"}

    after = db.books.find_one({"slug": ALLOWED_SLUG}, {"_id": 0}) or {}
    payload["after_state"] = public_state(after)
    payload["live_verification"] = live_verify(args.api_base_url, args.web_base_url) if args.live_verify else {}
    if args.commit and not payload["live_verification"].get("pass"):
        payload["status"] = "PUBLISHED_WITH_VERIFICATION_BLOCKERS"
        payload["issues"].append("Live verification did not pass.")
    write_publication_report(payload, Path(args.report))
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish approved Tier A Dracula core reading candidate only.")
    parser.add_argument("--slug", default=ALLOWED_SLUG)
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--report", default=str(REPORT_FILE))
    parser.add_argument("--api-base-url", default="https://api.theearnalism.com/api")
    parser.add_argument("--web-base-url", default="https://theearnalism.com")
    parser.add_argument("--live-verify", action="store_true", default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = publish(args)
    print(f"Controlled publication status: {result['status']}")
    for issue in result.get("issues", []):
        print(f"- {issue}")
    print(f"Report: {args.report}")
    return 0 if result["status"] in {"DRY_RUN_READY", "PUBLISHED"} else 1


if __name__ == "__main__":
    sys.exit(main())
