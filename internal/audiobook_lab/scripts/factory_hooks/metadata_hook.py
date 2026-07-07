#!/usr/bin/env python3
"""Approve audiobook metadata after upload/checksum and rights metadata success."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from common import (
    controlled_dir,
    fetch_url,
    finish,
    ffprobe_duration,
    iso_now,
    load_public_book,
    parser,
    public_book_path,
    read_json,
    rel,
    validation_pass,
    write_json,
)


DEFAULT_API_URL = "https://api.theearnalism.com/api"
RIGHTS_REQUIRED_FIELDS = (
    "source_url",
    "source_name",
    "source_license",
    "author_death_year",
    "original_publication_year",
    "rights_tier",
    "verification_status",
    "verified_at",
)


def api_base_url() -> str:
    return (os.environ.get("EARNALISM_API_URL") or os.environ.get("EARNALISM_BACKEND_API_URL") or DEFAULT_API_URL).rstrip("/")


def api_json(method: str, url: str, payload: dict[str, Any] | None = None, token: str | None = None) -> dict[str, Any]:
    body = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "EarnalismFactoryMetadataHook/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=90) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with HTTP {exc.code}: {detail[:2000]}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"{method} {url} failed: {exc}") from exc


def admin_token(api_url: str) -> tuple[str, str]:
    token = os.environ.get("EARNALISM_ADMIN_TOKEN", "").strip()
    if token:
        return token, "EARNALISM_ADMIN_TOKEN"
    email = os.environ.get("ADMIN_EMAIL", "").strip()
    password = os.environ.get("ADMIN_PASSWORD", "").strip()
    if not email or not password:
        return "", "missing"
    data = api_json("POST", f"{api_url}/auth/login", {"email": email, "password": password})
    token = str(data.get("token") or "").strip()
    if not token:
        raise RuntimeError("Admin login did not return a token.")
    return token, "ADMIN_EMAIL_PASSWORD"


def first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return ""


def audiobook_provenance(tts_metrics: dict[str, Any]) -> dict[str, str]:
    provider = str(
        first_present(
            tts_metrics.get("provider"),
            os.environ.get("EARNALISM_BENGALI_TTS_PROVIDER"),
            "openai",
        )
    ).strip().lower()
    model = str(first_present(tts_metrics.get("model"), os.environ.get("EARNALISM_BENGALI_TTS_MODEL"))).strip()
    voice = str(first_present(tts_metrics.get("voice"), os.environ.get("EARNALISM_BENGALI_TTS_VOICE"))).strip()
    style = str(
        first_present(
            tts_metrics.get("style"),
            tts_metrics.get("profile"),
            os.environ.get("EARNALISM_BENGALI_TTS_STYLE"),
        )
    ).strip()
    return {
        "provider": provider,
        "model": model,
        "voice": voice,
        "style": style,
    }


def audiobook_reset_required(book: dict[str, Any]) -> bool:
    assets = book.get("audiobook_assets") if isinstance(book.get("audiobook_assets"), dict) else {}
    return bool(book.get("audiobook_enabled") or book.get("generate_audiobook") or assets)


def manifest_records(path: Path) -> list[dict[str, Any]]:
    data = read_json(path, [])
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("books", "candidates", "items", "records"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                return [item for item in value.values() if isinstance(item, dict)]
    return []


def compact_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def normalize_slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower())
    return re.sub(r"-+", "-", value).strip("-")


def manifest_value(record: dict[str, Any], *keys: str) -> Any:
    normalized = {compact_key(key): value for key, value in record.items()}
    for key in keys:
        value = normalized.get(compact_key(key))
        if value not in (None, ""):
            return value
    return ""


def load_manifest_record(args: Any) -> dict[str, Any]:
    manifest_path = Path(args.manifest)
    for record in manifest_records(manifest_path):
        slug = str(
            first_present(
                record.get("slug"),
                record.get("book_slug"),
                record.get("bookSlug"),
                record.get("candidate_slug"),
                manifest_value(record, "slug", "book_slug", "bookSlug", "candidate_slug"),
            )
        ).strip()
        title_slug = normalize_slug(str(first_present(record.get("title"), manifest_value(record, "title"))))
        if slug == args.slug or title_slug == args.slug:
            return record
    return {}


def int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def infer_year_from_text(text: str, *patterns: str) -> int | None:
    for pattern in patterns:
        match = re.search(pattern, text or "", re.I)
        if match:
            return int_or_none(match.group(1))
    return None


def public_domain_from_evidence(source_name: str, source_license: str, rights_basis: str, author_death_year: int | None, original_publication_year: int | None) -> bool:
    text = f"{source_name} {source_license} {rights_basis}"
    return bool(
        re.search(r"public\s*domain|gutenberg|wikisource", text, re.I)
        and author_death_year
        and original_publication_year
    )


def build_rights_metadata_report(args: Any) -> dict[str, Any]:
    run_dir = Path(args.run_dir)
    existing_report = read_json(run_dir / "rights_metadata_report.json", {})
    if existing_report.get("production_metadata_ready") is True and isinstance(existing_report.get("rights_metadata"), dict):
        return existing_report

    public_book = load_public_book(args.slug)
    source_evidence = read_json(controlled_dir(args.slug) / "source_evidence.json", {})
    approval_evidence = read_json(controlled_dir(args.slug) / "approval_evidence.json", {})
    checksum = read_json(controlled_dir(args.slug) / "checksum_manifest.json", {})
    manifest = load_manifest_record(args)

    source_url = str(first_present(source_evidence.get("source_url"), public_book.get("source_url"), manifest_value(manifest, "source_url", "sourceurl"))).strip()
    source_name = str(
        first_present(
            source_evidence.get("source_name"),
            public_book.get("source_name"),
            manifest_value(manifest, "source_name", "sourcename"),
            "Project Gutenberg" if "gutenberg.org" in source_url else "",
        )
    ).strip()
    source_license = str(first_present(source_evidence.get("source_license"), public_book.get("source_license"), manifest_value(manifest, "source_license", "sourcelicense"))).strip()
    rights_basis = str(first_present(source_evidence.get("rights_basis"), public_book.get("rights_basis"), manifest_value(manifest, "rights_basis", "rightsbasis"))).strip()
    author_death_year = int_or_none(first_present(public_book.get("author_death_year"), manifest_value(manifest, "author_death_year", "authordeathyear")))
    if author_death_year is None:
        author_death_year = infer_year_from_text(rights_basis, r"(?:died|death|author died)\D{0,20}(\d{4})", r"(\d{4})\s*death")
    original_publication_year = int_or_none(
        first_present(public_book.get("original_publication_year"), manifest_value(manifest, "original_publication_year", "originalpublicationyear"))
    )
    if original_publication_year is None:
        original_publication_year = infer_year_from_text(rights_basis, r"(?:first\s+)?published\D{0,20}(\d{4})", r"publication\D{0,20}(\d{4})")
    rights_tier = str(first_present(approval_evidence.get("rights_tier"), public_book.get("rights_tier"), "A")).strip().upper()
    verification_status = str(first_present(approval_evidence.get("verification_status"), public_book.get("verification_status"))).strip().lower()
    verified_at = str(
        first_present(
            approval_evidence.get("approved_at"),
            approval_evidence.get("verified_at"),
            source_evidence.get("downloaded_at"),
            checksum.get("generated_at"),
        )
    ).strip()
    source_hash = str(first_present(source_evidence.get("source_hash"), source_evidence.get("content_hash"))).strip()
    public_domain = public_domain_from_evidence(source_name, source_license, rights_basis, author_death_year, original_publication_year)

    rights_metadata = {
        "work_title": str(first_present(public_book.get("title"), args.title)).strip(),
        "work_slug": args.slug,
        "author_name": str(first_present(public_book.get("author"), args.author)).strip(),
        "author_death_year": author_death_year,
        "original_publication_year": original_publication_year,
        "country_of_origin": "United States" if args.language == "eng" else "India",
        "source_url": source_url,
        "source_name": source_name,
        "source_license": source_license,
        "translator_name": "",
        "translator_death_year": "",
        "illustrator_name": "",
        "illustrator_death_year": "",
        "editor_name": "",
        "edition_publication_year": "",
        "rights_tier": rights_tier,
        "verification_status": verification_status,
        "blocked_reason": "",
        "publication_region": "global",
        "verified_at": verified_at,
    }
    missing_fields = [field for field in RIGHTS_REQUIRED_FIELDS if rights_metadata.get(field) in (None, "")]
    blockers: list[str] = []
    if missing_fields:
        blockers.append(f"Required rights metadata fields are missing: {', '.join(missing_fields)}")
    if rights_tier not in {"A", "B", "C"}:
        blockers.append("rights_tier must be A, B, or C.")
    if verification_status not in {"approved", "verified"}:
        blockers.append("verification_status must be approved before publishing.")
    if rights_tier == "C":
        blockers.append("Tier C rights block publishing.")
    if not public_domain:
        blockers.append("Public-domain evidence is incomplete or not deterministic.")

    content_use_approved = not blockers and rights_tier == "A" and verification_status in {"approved", "verified"}
    manifest_audio_allowed = str(manifest_value(manifest, "audioallowed")).strip().lower() in {"true", "1", "yes"}
    audiobook_use_approved = content_use_approved and bool(
        approval_evidence.get("audiobook_enabled")
        or approval_evidence.get("audio_public_release") == "PUBLIC_AUDIO_RELEASE_APPROVED"
        or manifest_audio_allowed
    )
    if content_use_approved and not audiobook_use_approved:
        blockers.append("Audiobook use approval is missing from approval evidence or manifest.")
    report = {
        "slug": args.slug,
        "title": rights_metadata["work_title"],
        "author": rights_metadata["author_name"],
        "language": args.language,
        "source_of_truth_path_or_reference": rel(controlled_dir(args.slug) / "source_evidence.json"),
        "source_type": str(first_present(source_evidence.get("source_format"), manifest_value(manifest, "sourcetype"), "controlled_publication_evidence")),
        "source_url": source_url,
        "source_hash": source_hash,
        "copyright_status": "public_domain" if public_domain else "unknown",
        "rights_basis": rights_basis,
        "license": source_license,
        "public_domain": public_domain,
        "public_domain_jurisdiction": "India and United States" if public_domain else "unknown",
        "original_publication_year": original_publication_year,
        "author_death_year": author_death_year,
        "rights_evidence": {
            "source_evidence_path": rel(controlled_dir(args.slug) / "source_evidence.json"),
            "approval_evidence_path": rel(controlled_dir(args.slug) / "approval_evidence.json"),
            "checksum_manifest_path": rel(controlled_dir(args.slug) / "checksum_manifest.json"),
        },
        "attribution_text": str(first_present(public_book.get("attribution_notice"), manifest_value(manifest, "attributionnotice"))),
        "content_use_approved": content_use_approved,
        "audiobook_use_approved": audiobook_use_approved,
        "production_metadata_ready": not blockers,
        "rights_metadata": rights_metadata,
        "missing_fields": missing_fields,
        "blocker_reasons": blockers,
        "status": "PASS" if not blockers else "BLOCKED",
    }
    write_json(run_dir / "rights_metadata_report.json", report)
    return report


def classify_metadata_error(message: str) -> tuple[str, str]:
    lower = message.lower()
    if "rights verification" in lower or "rights metadata" in lower or "cannot be published without approved rights" in lower:
        return "metadata_rights", "rights metadata rejected by production API"
    if "field required" in lower or "validation" in lower or "schema" in lower:
        return "metadata_api", "production DB schema mismatch or validation error"
    return "metadata_api", "production metadata API rejected the update"


def redacted_book_snapshot(book: dict[str, Any]) -> dict[str, Any]:
    keep = [
        "slug",
        "title",
        "author",
        "category_slug",
        "cover_image_url",
        "back_cover_image_url",
        "audiobook_enabled",
        "audio_asset_slug",
        "audiobook_assets",
        "rights_metadata",
        "readerStatus",
        "publicationStatus",
        "isPublic",
        "isLive",
        "showInPublicLibrary",
        "allowPublicReading",
        "allowCheckout",
        "allowPayment",
        "is_published",
    ]
    return {key: book.get(key) for key in keep if key in book}


def build_book_update_payload(args: Any, existing: dict[str, Any], public_book: dict[str, Any], rights_metadata: dict[str, Any]) -> dict[str, Any]:
    source_evidence = read_json(controlled_dir(args.slug) / "source_evidence.json", {})
    approval_evidence = read_json(controlled_dir(args.slug) / "approval_evidence.json", {})

    def value(name: str, default: Any = "") -> Any:
        return first_present(existing.get(name), public_book.get(name), default)

    return {
        "title": str(value("title", args.title)).strip() or args.title,
        "subtitle": str(value("subtitle", "")),
        "author": str(value("author", args.author)).strip() or args.author,
        "category_slug": str(first_present(existing.get("category_slug"), public_book.get("category_slug"), "english-classics")).strip() or "english-classics",
        "short_description": str(value("short_description", "")),
        "description": str(value("description", "")),
        "cover_image_url": str(first_present(existing.get("cover_image_url"), existing.get("cover_url"), public_book.get("cover_image_url"), public_book.get("cover_url"), "")),
        "back_cover_image_url": str(
            first_present(existing.get("back_cover_image_url"), existing.get("back_cover_url"), public_book.get("back_cover_image_url"), public_book.get("back_cover_url"), "")
        ),
        "estimated_reading_time": str(value("estimated_reading_time", "")),
        "price_paperback": str(value("price_paperback", "")),
        "price_ebook": str(value("price_ebook", "")),
        "buy_url": str(value("buy_url", "")),
        "formats": existing.get("formats") if isinstance(existing.get("formats"), list) else public_book.get("formats") if isinstance(public_book.get("formats"), list) else ["Ebook"],
        "benefits": existing.get("benefits") if isinstance(existing.get("benefits"), list) else public_book.get("benefits") if isinstance(public_book.get("benefits"), list) else [],
        "who_for": existing.get("who_for") if isinstance(existing.get("who_for"), list) else public_book.get("who_for") if isinstance(public_book.get("who_for"), list) else [],
        "learnings": existing.get("learnings") if isinstance(existing.get("learnings"), list) else public_book.get("learnings") if isinstance(public_book.get("learnings"), list) else [],
        "about_author": str(value("about_author", "")),
        "rights_metadata": rights_metadata,
        "source_url": str(first_present(existing.get("source_url"), public_book.get("source_url"), source_evidence.get("source_url"), rights_metadata.get("source_url"))),
        "source_name": str(first_present(existing.get("source_name"), public_book.get("source_name"), source_evidence.get("source_name"), rights_metadata.get("source_name"))),
        "source_license": str(first_present(existing.get("source_license"), public_book.get("source_license"), source_evidence.get("source_license"), rights_metadata.get("source_license"))),
        "source_hash": str(first_present(existing.get("source_hash"), public_book.get("source_hash"), source_evidence.get("source_hash"))),
        "content_hash": str(first_present(existing.get("content_hash"), public_book.get("content_hash"), source_evidence.get("content_hash"))),
        "provenance_hash": str(first_present(existing.get("provenance_hash"), public_book.get("provenance_hash"), source_evidence.get("provenance_hash"))),
        "rights_basis": str(first_present(existing.get("rights_basis"), public_book.get("rights_basis"), source_evidence.get("rights_basis"))),
        "rights_tier": str(first_present(existing.get("rights_tier"), public_book.get("rights_tier"), approval_evidence.get("rights_tier"), rights_metadata.get("rights_tier"))),
        "verification_status": str(
            first_present(existing.get("verification_status"), public_book.get("verification_status"), approval_evidence.get("verification_status"), rights_metadata.get("verification_status"))
        ),
        "qa_status": str(first_present(existing.get("qa_status"), public_book.get("qa_status"), approval_evidence.get("qa_status"), "QA_PASSED")),
        "approved_to_publish": bool(first_present(existing.get("approved_to_publish"), public_book.get("approved_to_publish"), approval_evidence.get("approved_to_publish"), True)),
        "publication_status": str(first_present(existing.get("publication_status"), public_book.get("publication_status"), "LIVE_APPROVED")),
        "audiobook_enabled": bool(first_present(existing.get("audiobook_enabled"), public_book.get("audiobook_enabled"), False)),
        "generate_audiobook": False,
        "readerStatus": str(first_present(existing.get("readerStatus"), public_book.get("readerStatus"), "reader_ready")),
        "publicationStatus": str(first_present(existing.get("publicationStatus"), public_book.get("publicationStatus"), "live" if existing.get("is_published") else "draft")),
        "isPublic": bool(first_present(existing.get("isPublic"), public_book.get("isPublic"), existing.get("is_published"), False)),
        "isLive": bool(first_present(existing.get("isLive"), public_book.get("isLive"), existing.get("is_published"), False)),
        "showInPublicLibrary": bool(first_present(existing.get("showInPublicLibrary"), public_book.get("showInPublicLibrary"), existing.get("is_published"), False)),
        "showInHomepage": bool(first_present(existing.get("showInHomepage"), public_book.get("showInHomepage"), False)),
        "allowPublicReading": bool(first_present(existing.get("allowPublicReading"), public_book.get("allowPublicReading"), existing.get("is_published"), False)),
        "allowCheckout": bool(first_present(existing.get("allowCheckout"), public_book.get("allowCheckout"), False)),
        "allowPayment": bool(first_present(existing.get("allowPayment"), public_book.get("allowPayment"), False)),
        "is_published": bool(first_present(existing.get("is_published"), public_book.get("is_published"), False)),
        "slug": args.slug,
    }


def update_controlled_launch(slug: str) -> dict[str, Any]:
    path = Path(__file__).resolve().parents[4] / "data" / "controlled_launch.json"
    config = read_json(path, {})
    changed = False
    for key in ("live_approved_slugs", "audio_enabled_slugs"):
        values = [str(item).strip() for item in config.get(key, []) if str(item).strip()] if isinstance(config.get(key), list) else []
        if slug not in values:
            values.append(slug)
            changed = True
        config[key] = values
    if changed:
        write_json(path, config)
    return {"path": rel(path), "changed": changed, "audio_enabled": slug in config.get("audio_enabled_slugs", [])}


def write_failure_diagnosis(
    args: Any,
    *,
    endpoint: str,
    status: str,
    response_body: str,
    current_snapshot: dict[str, Any],
    rights_report: dict[str, Any],
    repair_action: str,
) -> Path:
    diagnosis = {
        "slug": args.slug,
        "endpoint_called": endpoint,
        "http_status": status,
        "response_body": response_body[:4000],
        "missing_or_invalid_rights_fields": rights_report.get("missing_fields", []),
        "current_production_metadata_snapshot": redacted_book_snapshot(current_snapshot),
        "required_metadata_schema_discovered_from_backend_validation": {
            "BookIn.rights_metadata": list(RIGHTS_REQUIRED_FIELDS),
            "rights_tier_values": ["A", "B", "C"],
            "verification_status_values": ["approved", "verified"],
            "verified_at_required_when_approved": True,
        },
        "failure_type": "book-level rights metadata" if rights_report.get("status") != "PASS" else "production metadata API rejection",
        "exact_repair_action": repair_action,
        "rights_metadata_report_path": rel(Path(args.run_dir) / "rights_metadata_report.json"),
    }
    path = Path(args.run_dir) / "rights_metadata_failure_diagnosis.json"
    write_json(path, diagnosis)
    return path


def main() -> int:
    args = parser().parse_args()
    started = iso_now()
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    api_url = api_base_url()
    if args.dry_run or args.slug == "__hook_validation__":
        return validation_pass(
            args,
            "metadata",
            started,
            {
                "admin_token_detected": bool(os.environ.get("EARNALISM_ADMIN_TOKEN")),
                "admin_email_password_detected": bool(os.environ.get("ADMIN_EMAIL") and os.environ.get("ADMIN_PASSWORD")),
                "api_url_configured": bool(api_url),
                "rights_metadata_preflight_enabled": True,
            },
        )

    upload = read_json(run_dir / "upload_hook_result.json", {})
    updated = upload.get("updated_fields") if isinstance(upload.get("updated_fields"), dict) else {}
    if upload.get("status") != "PASS" or updated.get("upload_status") != "UPLOADED":
        return finish(
            args,
            "metadata",
            started,
            status="BLOCKED",
            ready_for_next_stage=False,
            blocker_category="metadata",
            blockers=["upload_hook_result.json must be PASS with verified checksums before metadata approval."],
            retryable=True,
        )
    final_audio_url = str(updated.get("final_audio_url") or "")
    sidecar_urls = updated.get("sidecar_urls") if isinstance(updated.get("sidecar_urls"), dict) else {}
    if not final_audio_url or not all(sidecar_urls.get(key) for key in ("timestamps", "vtt", "chapters", "meta")):
        return finish(
            args,
            "metadata",
            started,
            status="BLOCKED",
            ready_for_next_stage=False,
            blocker_category="metadata",
            blockers=["Uploaded audio and sidecar URLs are incomplete."],
            retryable=True,
        )

    rights_report = build_rights_metadata_report(args)
    rights_report_path = run_dir / "rights_metadata_report.json"
    if rights_report.get("production_metadata_ready") is not True:
        diagnosis_path = write_failure_diagnosis(
            args,
            endpoint=f"{api_url}/admin/books/{args.slug}",
            status="NOT_CALLED_BLOCKED_BY_RIGHTS_PREFLIGHT",
            response_body="",
            current_snapshot={},
            rights_report=rights_report,
            repair_action="Complete the missing source/license/public-domain rights fields before metadata approval.",
        )
        return finish(
            args,
            "metadata",
            started,
            status="BLOCKED",
            ready_for_next_stage=False,
            blocker_category="metadata_rights",
            blockers=rights_report.get("blocker_reasons") or ["Production rights metadata is incomplete."],
            retryable=True,
            artifacts={"rights_metadata_report": rel(rights_report_path), "rights_metadata_failure_diagnosis": rel(diagnosis_path)},
            updated_fields={"rights_metadata_status": rights_report.get("status"), "production_approval_attempted": False, "production_approval_succeeded": False},
        )

    tts = read_json(run_dir / "tts_hook_result.json", {})
    tts_metrics = tts.get("metrics") if isinstance(tts.get("metrics"), dict) else {}
    audio_path_value = (tts.get("artifacts") or {}).get("final_audio_path") or tts.get("final_audio_path") or ""
    audio_path = Path(audio_path_value)
    if audio_path_value and not audio_path.is_absolute():
        candidate = run_dir / audio_path
        audio_path = candidate if candidate.exists() else Path(__file__).resolve().parents[4] / audio_path_value
    duration_ms = int((ffprobe_duration(audio_path) or tts_metrics.get("duration_seconds") or 0) * 1000) if audio_path_value else 0
    audio_size = audio_path.stat().st_size if audio_path.exists() else int((upload.get("metrics") or {}).get("checksums", {}).get("mp3", {}).get("local_size") or 0)
    provenance = audiobook_provenance(tts_metrics)
    audiobook_payload = {
        "audiobook_enabled": True,
        "generate_audiobook": False,
        "audiobook_provider": provenance["provider"],
        "audiobook_model": provenance["model"],
        "audiobook_voice": provenance["voice"],
        "audiobook_style": provenance["style"],
        "audio_asset_slug": args.slug,
        "audiobook_assets": {"mp3": final_audio_url, **sidecar_urls},
        "audiobook_size": audio_size,
        "audiobook_duration_ms": duration_ms,
    }
    payload_path = run_dir / "metadata_update_payload.json"
    write_json(payload_path, audiobook_payload)

    try:
        token, token_source = admin_token(api_url)
    except RuntimeError as exc:
        return finish(
            args,
            "metadata",
            started,
            status="BLOCKED",
            blocker_category="metadata_api",
            blockers=[str(exc)],
            retryable=True,
            artifacts={"metadata_payload": rel(payload_path), "rights_metadata_report": rel(rights_report_path)},
        )
    if not token:
        return finish(
            args,
            "metadata",
            started,
            status="BLOCKED",
            ready_for_next_stage=False,
            blocker_category="metadata_api",
            blockers=["Missing admin metadata credentials: set EARNALISM_ADMIN_TOKEN or ADMIN_EMAIL + ADMIN_PASSWORD."],
            retryable=True,
            artifacts={"metadata_payload": rel(payload_path), "rights_metadata_report": rel(rights_report_path)},
        )

    public_book = load_public_book(args.slug)
    current_book: dict[str, Any] = {}
    try:
        current_book = api_json("GET", f"{api_url}/admin/books/{args.slug}", token=token)
    except RuntimeError as exc:
        category, _ = classify_metadata_error(str(exc))
        diagnosis_path = write_failure_diagnosis(
            args,
            endpoint=f"{api_url}/admin/books/{args.slug}",
            status="FAILED",
            response_body=str(exc),
            current_snapshot={},
            rights_report=rights_report,
            repair_action="Confirm the production admin API route and credentials, then resume metadata approval.",
        )
        return finish(
            args,
            "metadata",
            started,
            status="BLOCKED",
            blocker_category=category,
            blockers=[str(exc)],
            retryable=True,
            artifacts={"metadata_payload": rel(payload_path), "rights_metadata_report": rel(rights_report_path), "rights_metadata_failure_diagnosis": rel(diagnosis_path)},
        )

    reset_response_path: Path | None = None
    if audiobook_reset_required(current_book):
        reset_payload = {
            "audiobook_enabled": False,
            "generate_audiobook": False,
            "audiobook_provider": "",
            "audiobook_voice": "",
            "audio_asset_slug": args.slug,
            "audiobook_assets": {},
            "audiobook_size": 0,
            "audiobook_duration_ms": 0,
        }
        reset_payload_path = run_dir / "metadata_audiobook_reset_payload.json"
        write_json(reset_payload_path, reset_payload)
        try:
            reset_response = api_json("PATCH", f"{api_url}/admin/books/{args.slug}/audiobook", reset_payload, token)
        except RuntimeError as exc:
            category, repair = classify_metadata_error(str(exc))
            diagnosis_path = write_failure_diagnosis(
                args,
                endpoint=f"{api_url}/admin/books/{args.slug}/audiobook",
                status="FAILED",
                response_body=str(exc),
                current_snapshot=current_book,
                rights_report=rights_report,
                repair_action=repair,
            )
            return finish(
                args,
                "metadata",
                started,
                status="BLOCKED",
                blocker_category=category,
                blockers=[str(exc)],
                retryable=True,
                artifacts={
                    "metadata_payload": rel(payload_path),
                    "audiobook_reset_payload": rel(reset_payload_path),
                    "rights_metadata_report": rel(rights_report_path),
                    "rights_metadata_failure_diagnosis": rel(diagnosis_path),
                    "metadata_api_error": str(exc),
                },
                updated_fields={"rights_metadata_status": "PASS", "production_approval_attempted": True, "production_approval_succeeded": False},
            )
        reset_response_path = run_dir / "metadata_audiobook_reset_response.json"
        write_json(reset_response_path, reset_response)
        current_book = reset_response if isinstance(reset_response, dict) else current_book

    book_payload = build_book_update_payload(args, current_book, public_book, rights_report["rights_metadata"])
    book_payload_path = run_dir / "metadata_book_rights_payload.json"
    write_json(book_payload_path, book_payload)
    try:
        book_update_response = api_json("PUT", f"{api_url}/admin/books/{args.slug}", book_payload, token)
    except RuntimeError as exc:
        category, repair = classify_metadata_error(str(exc))
        diagnosis_path = write_failure_diagnosis(
            args,
            endpoint=f"{api_url}/admin/books/{args.slug}",
            status="FAILED",
            response_body=str(exc),
            current_snapshot=current_book,
            rights_report=rights_report,
            repair_action=repair,
        )
        return finish(
            args,
            "metadata",
            started,
            status="BLOCKED",
            blocker_category=category,
            blockers=[str(exc)],
            retryable=True,
            artifacts={
                "metadata_payload": rel(payload_path),
                "book_rights_payload": rel(book_payload_path),
                "rights_metadata_report": rel(rights_report_path),
                "rights_metadata_failure_diagnosis": rel(diagnosis_path),
                "metadata_api_error": str(exc),
            },
            updated_fields={"rights_metadata_status": "BLOCKED", "production_approval_attempted": False, "production_approval_succeeded": False},
        )
    book_response_path = run_dir / "metadata_book_rights_response.json"
    write_json(book_response_path, book_update_response)

    try:
        admin_response = api_json("PATCH", f"{api_url}/admin/books/{args.slug}/audiobook", audiobook_payload, token)
    except RuntimeError as exc:
        category, repair = classify_metadata_error(str(exc))
        diagnosis_path = write_failure_diagnosis(
            args,
            endpoint=f"{api_url}/admin/books/{args.slug}/audiobook",
            status="FAILED",
            response_body=str(exc),
            current_snapshot=book_update_response or current_book,
            rights_report=rights_report,
            repair_action=repair,
        )
        return finish(
            args,
            "metadata",
            started,
            status="BLOCKED",
            blocker_category=category,
            blockers=[str(exc)],
            retryable=True,
            artifacts={
                "metadata_payload": rel(payload_path),
                "book_rights_payload": rel(book_payload_path),
                "book_rights_response": rel(book_response_path),
                "rights_metadata_report": rel(rights_report_path),
                "rights_metadata_failure_diagnosis": rel(diagnosis_path),
                "metadata_api_error": str(exc),
            },
            updated_fields={"rights_metadata_status": "PASS", "production_approval_attempted": True, "production_approval_succeeded": False},
        )
    admin_response_path = run_dir / "metadata_admin_response.json"
    write_json(admin_response_path, admin_response)

    rights_metadata = rights_report["rights_metadata"]
    public_book.update(
        {
            "source_url": rights_metadata.get("source_url"),
            "source_name": rights_metadata.get("source_name"),
            "source_license": rights_metadata.get("source_license"),
            "author_death_year": rights_metadata.get("author_death_year"),
            "original_publication_year": rights_metadata.get("original_publication_year"),
            "rights_basis": rights_report.get("rights_basis"),
            "rights_tier": rights_metadata.get("rights_tier"),
            "verification_status": rights_metadata.get("verification_status"),
            "rights_metadata": rights_metadata,
            "audio_enabled": True,
            "audiobook_enabled": True,
            "generate_audiobook": False,
            "audiobook_provider": provenance["provider"],
            "audiobook_model": provenance["model"],
            "audiobook_voice": audiobook_payload["audiobook_voice"],
            "audiobook_style": provenance["style"],
            "audio_asset_slug": args.slug,
            "audiobook_assets": audiobook_payload["audiobook_assets"],
            "audiobook": {
                "url": final_audio_url,
                "provider": provenance["provider"],
                "model": provenance["model"],
                "voice": audiobook_payload["audiobook_voice"],
                "style": provenance["style"],
                "size": audio_size,
                "duration_ms": duration_ms,
                "assets": audiobook_payload["audiobook_assets"],
                "updated_at": iso_now(),
            },
            "audiobook_assets_updated_at": iso_now(),
            "production_approved": True,
            "audiobook_release_gate": "APPROVED",
            "upload_status": "UPLOADED",
        }
    )
    write_json(public_book_path(args.slug), public_book)
    launch_update = update_controlled_launch(args.slug)

    endpoint = fetch_url(f"{api_url}/reader/book/{args.slug}/audiobook", timeout=30, max_bytes=1024 * 1024)
    endpoint_ok = endpoint.get("ok") or endpoint.get("status") in {200, 206, 307, 308}
    result_payload = {
        "admin_token_source": token_source,
        "rights_metadata_report": rel(rights_report_path),
        "metadata_payload": rel(payload_path),
        "book_rights_payload": rel(book_payload_path),
        "book_rights_response": rel(book_response_path),
        "admin_response": rel(admin_response_path),
        "audiobook_reset_response": rel(reset_response_path) if reset_response_path else "",
        "public_book": rel(public_book_path(args.slug)),
        "controlled_dir": rel(controlled_dir(args.slug)),
        "controlled_launch_update": launch_update,
        "audiobook_endpoint": {"url": f"{api_url}/reader/book/{args.slug}/audiobook", "status": endpoint.get("status"), "ok": endpoint_ok, "error": endpoint.get("error")},
    }
    if not endpoint_ok:
        return finish(
            args,
            "metadata",
            started,
            status="BLOCKED",
            ready_for_next_stage=False,
            blocker_category="metadata",
            blockers=[
                "Metadata updated, but production audiobook endpoint is not 200/redirect yet. Deploy/restart backend with updated controlled_launch/audio metadata, then resume.",
            ],
            retryable=True,
            artifacts=result_payload,
            metrics={"metadata_api_status": "PASS", "audiobook_endpoint_status": endpoint.get("status")},
            updated_fields={
                "rights_metadata_status": "PASS",
                "production_approval_attempted": True,
                "production_approval_succeeded": False,
                "production_approved": False,
                "audiobook_release_gate": "BLOCKED_ENDPOINT_NOT_LIVE",
                "audiobook_endpoint_status": endpoint.get("status"),
            },
        )

    return finish(
        args,
        "metadata",
        started,
        status="PASS",
        ready_for_next_stage=True,
        blocker_category="none",
        blockers=[],
        retryable=False,
        artifacts=result_payload,
        metrics={"metadata_api_status": "PASS", "audiobook_endpoint_status": endpoint.get("status"), "audio_size": audio_size, "duration_ms": duration_ms},
        updated_fields={
            "rights_metadata_status": "PASS",
            "production_approval_attempted": True,
            "production_approval_succeeded": True,
            "production_approved": True,
            "audiobook_release_gate": "APPROVED",
            "audiobook_endpoint_status": endpoint.get("status"),
        },
    )


if __name__ == "__main__":
    raise SystemExit(main())
