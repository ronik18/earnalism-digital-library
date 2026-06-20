from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

LIVE_APPROVED_SLUG = "dracula"
PIPELINE_CANDIDATE_SLUGS = {"kshudhita-pashan"}
CONTROLLED_LIVE_BOOK_SLUGS = (LIVE_APPROVED_SLUG,)

PUBLIC_STATUS_LIVE_APPROVED = "LIVE_APPROVED"
PUBLIC_STATUS_PIPELINE_CANDIDATE = "PIPELINE_CANDIDATE"
PUBLIC_STATUS_COMING_SOON = "COMING_SOON"
PUBLIC_STATUS_RIGHTS_REVIEW = "RIGHTS_REVIEW"
PUBLIC_STATUS_QUARANTINE = "QUARANTINE"
PUBLIC_STATUS_HIDDEN = "HIDDEN"

SAFE_PUBLIC_BOOK_FIELDS = {
    "id",
    "slug",
    "title",
    "subtitle",
    "author",
    "category_slug",
    "short_description",
    "description",
    "cover_url",
    "cover_image_url",
    "thumbnail_url",
    "blur_placeholder",
    "dominant_color",
    "back_cover_url",
    "back_cover_image_url",
    "back_cover_thumbnail_url",
    "back_cover_blur_placeholder",
    "back_cover_dominant_color",
    "estimated_reading_time",
    "formats",
    "benefits",
    "who_for",
    "learnings",
    "about_author",
    "chapters",
    "is_published",
    "created_at",
    "updated_at",
}

INTERNAL_RIGHTS_FIELDS = {
    "rights_metadata",
    "source_url",
    "source_name",
    "source_license",
    "source_text_url",
    "source_hash",
    "content_hash",
    "provenance_hash",
    "rights_basis",
    "rights_decision",
    "source_metadata",
    "source_evidence",
    "ingestion",
    "qa_issues",
    "source_load_issues",
}

INTERNAL_AUDIO_FIELDS = {
    "audiobook",
    "audiobook_assets",
    "audiobook_assets_updated_at",
    "audiobook_provider",
    "audiobook_voice",
    "audio_asset_slug",
    "generate_audiobook",
}


def normalize_slug(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_upper(value: Any) -> str:
    return normalize_text(value).upper()


def nested_dict(book: dict[str, Any], key: str) -> dict[str, Any]:
    value = book.get(key)
    return value if isinstance(value, dict) else {}


def safe_public_value(key: str, value: Any) -> Any:
    if key != "chapters" or not isinstance(value, list):
        return value
    chapters: list[dict[str, Any]] = []
    for chapter in value:
        if not isinstance(chapter, dict):
            continue
        chapters.append({field: chapter.get(field) for field in chapter if field != "content"})
    return chapters


def safe_public_fields(book: dict[str, Any]) -> dict[str, Any]:
    return {
        key: safe_public_value(key, book.get(key))
        for key in SAFE_PUBLIC_BOOK_FIELDS
        if key in book
    }


def first_text(book: dict[str, Any], *keys: str, fallback_evidence: dict[str, Any] | None = None) -> str:
    sources: list[dict[str, Any]] = [book, nested_dict(book, "rights_metadata"), nested_dict(book, "source_metadata"), nested_dict(book, "ingestion")]
    if fallback_evidence:
        sources.append(fallback_evidence)
        rights_metadata = nested_dict(fallback_evidence, "rights_decision").get("metadata", {})
        if isinstance(rights_metadata, dict):
            sources.append(rights_metadata)
        sources.append(nested_dict(fallback_evidence, "ingestion"))
    for source in sources:
        for key in keys:
            value = source.get(key)
            if normalize_text(value):
                return normalize_text(value)
    return ""


@lru_cache(maxsize=1)
def dracula_approval_evidence() -> dict[str, Any]:
    evidence_path = ROOT / "output" / "publication_candidates" / "dracula" / "source_evidence.json"
    approval_path = ROOT / "APPROVED_TO_PUBLISH.md"
    payload: dict[str, Any] = {}
    if evidence_path.exists():
        try:
            loaded = json.loads(evidence_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                payload.update(loaded)
        except json.JSONDecodeError:
            payload["source_evidence_error"] = "invalid_json"
    payload["approved_to_publish_artifact"] = (
        approval_path.exists()
        and "Work Slug: dracula" in approval_path.read_text(encoding="utf-8", errors="ignore")
    )
    return payload


def evidence_for_book(book: dict[str, Any]) -> dict[str, Any]:
    return dracula_approval_evidence() if normalize_slug(book.get("slug")) == LIVE_APPROVED_SLUG else {}


def rights_tier(book: dict[str, Any]) -> str:
    return normalize_upper(first_text(book, "rights_tier", fallback_evidence=evidence_for_book(book)))


def verification_status(book: dict[str, Any]) -> str:
    return normalize_text(first_text(book, "verification_status", fallback_evidence=evidence_for_book(book))).lower()


def qa_status(book: dict[str, Any]) -> str:
    return normalize_upper(first_text(book, "qa_status", "source_qa_status", fallback_evidence=evidence_for_book(book)))


def blocked_reason(book: dict[str, Any]) -> str:
    return first_text(book, "blocked_reason", fallback_evidence=evidence_for_book(book))


def publication_status(book: dict[str, Any]) -> str:
    return normalize_upper(first_text(book, "publication_status", "launch_status", fallback_evidence=evidence_for_book(book)))


def approved_to_publish(book: dict[str, Any]) -> bool:
    evidence = evidence_for_book(book)
    explicit = book.get("approved_to_publish")
    if isinstance(explicit, bool):
        return explicit
    status = publication_status(book)
    return bool(
        explicit
        or evidence.get("approved_to_publish_artifact")
        or status in {"LIVE_APPROVED", "APPROVED_TO_PUBLISH", "PUBLISHED_CORE_READING_ONLY"}
    )


def traceability_hashes(book: dict[str, Any]) -> dict[str, str]:
    evidence = evidence_for_book(book)
    return {
        "source_hash": first_text(book, "source_hash", fallback_evidence=evidence),
        "content_hash": first_text(book, "content_hash", fallback_evidence=evidence),
        "provenance_hash": first_text(book, "provenance_hash", fallback_evidence=evidence),
    }


def source_metadata_present(book: dict[str, Any]) -> bool:
    evidence = evidence_for_book(book)
    return all(
        first_text(book, key, fallback_evidence=evidence)
        for key in ("source_url", "source_name", "source_license")
    )


def is_live_approved_book(book: dict[str, Any]) -> bool:
    if normalize_slug(book.get("slug")) != LIVE_APPROVED_SLUG:
        return False
    if book.get("is_published") is not True:
        return False
    if rights_tier(book) != "A":
        return False
    if verification_status(book) not in {"approved", "verified", "published_core_reading_only"}:
        return False
    if blocked_reason(book):
        return False
    if qa_status(book) not in {"QA_PASSED", "PASS", "PASSED"}:
        return False
    hashes = traceability_hashes(book)
    if not all(hashes.values()):
        return False
    if not source_metadata_present(book):
        return False
    return approved_to_publish(book)


def is_pipeline_candidate(book: dict[str, Any]) -> bool:
    slug = normalize_slug(book.get("slug"))
    if not slug or slug == LIVE_APPROVED_SLUG:
        return False
    if slug in PIPELINE_CANDIDATE_SLUGS:
        return True
    stage = normalize_upper(book.get("pipeline_stage"))
    status = publication_status(book)
    return "PIPELINE" in stage or status in {"PIPELINE_CANDIDATE", "COMING_SOON_PIPELINE"}


def normalize_book_publication_status(book: dict[str, Any]) -> str:
    if is_live_approved_book(book):
        return PUBLIC_STATUS_LIVE_APPROVED
    if is_pipeline_candidate(book):
        return PUBLIC_STATUS_PIPELINE_CANDIDATE
    if rights_tier(book) == "C" or blocked_reason(book):
        return PUBLIC_STATUS_QUARANTINE
    if book.get("is_published") is not True:
        return PUBLIC_STATUS_HIDDEN
    if rights_tier(book) != "A" or verification_status(book) not in {"approved", "verified"}:
        return PUBLIC_STATUS_RIGHTS_REVIEW
    return PUBLIC_STATUS_COMING_SOON


def can_expose_reader(book: dict[str, Any]) -> bool:
    return is_live_approved_book(book)


def can_expose_preview(book: dict[str, Any]) -> bool:
    return is_live_approved_book(book)


def can_expose_audio(book: dict[str, Any]) -> bool:
    return False


def public_pipeline_projection(book: dict[str, Any]) -> dict[str, Any]:
    projected = safe_public_fields(book)
    projected.update(
        {
            "publication_status": PUBLIC_STATUS_PIPELINE_CANDIDATE,
            "launch_status": PUBLIC_STATUS_PIPELINE_CANDIDATE,
            "reader_enabled": False,
            "preview_enabled": False,
            "audio_enabled": False,
            "audiobook_enabled": False,
            "reader_url": "",
            "preview_url": "",
            "audio_url": "",
            "cta_label": "Notify Me",
            "secondary_cta_label": "Reading Circle",
            "public_json_ld_enabled": False,
        }
    )
    return projected


def public_book_projection(book: dict[str, Any] | None) -> dict[str, Any] | None:
    if not book:
        return book
    status = normalize_book_publication_status(book)
    if status == PUBLIC_STATUS_PIPELINE_CANDIDATE:
        return public_pipeline_projection(book)

    projected = safe_public_fields(book)
    slug = normalize_slug(book.get("slug"))
    live = status == PUBLIC_STATUS_LIVE_APPROVED
    projected.update(
        {
            "publication_status": status,
            "launch_status": status,
            "reader_enabled": live,
            "preview_enabled": live,
            "audio_enabled": False,
            "audiobook_enabled": False,
            "reader_url": f"/reader/{slug}" if live else "",
            "preview_url": f"/reader/{slug}" if live else "",
            "audio_url": "",
            "cta_label": "Start Dracula" if live else "Notify Me",
            "secondary_cta_label": "Read Chapter 1 Free" if live else "Coming Soon",
            "public_json_ld_enabled": live,
        }
    )
    for field in [*INTERNAL_RIGHTS_FIELDS, *INTERNAL_AUDIO_FIELDS]:
        projected.pop(field, None)
    return projected


def live_approved_mongo_query(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    query: dict[str, Any] = {
        "slug": {"$in": list(CONTROLLED_LIVE_BOOK_SLUGS)},
        "is_published": True,
        "rights_metadata.rights_tier": "A",
        "rights_metadata.verification_status": "approved",
        "$or": [
            {"rights_metadata.blocked_reason": {"$exists": False}},
            {"rights_metadata.blocked_reason": None},
            {"rights_metadata.blocked_reason": ""},
        ],
    }
    if extra:
        for key, value in extra.items():
            if key == "$or":
                query["$and"] = [{"$or": query.pop("$or")}, {"$or": value}]
            else:
                query[key] = value
    return query


def catalog_truth_row(book: dict[str, Any], *, sitemap_urls: set[str] | None = None) -> dict[str, Any]:
    slug = normalize_slug(book.get("slug"))
    status = normalize_book_publication_status(book)
    sitemap_urls = sitemap_urls or set()
    hashes = traceability_hashes(book)
    return {
        "slug": slug,
        "title": normalize_text(book.get("title")),
        "author": normalize_text(book.get("author")),
        "classification": status,
        "is_published": bool(book.get("is_published")),
        "publication_status": publication_status(book) or status,
        "rights_tier": rights_tier(book) or "UNKNOWN",
        "verification_status": verification_status(book) or "unknown",
        "qa_status": qa_status(book) or "unknown",
        "approved_to_publish": approved_to_publish(book),
        "reader_enabled": can_expose_reader(book),
        "preview_enabled": can_expose_preview(book),
        "audio_enabled": can_expose_audio(book),
        "audiobook_enabled": False,
        "source_url_present": bool(first_text(book, "source_url", fallback_evidence=evidence_for_book(book))),
        "source_hash_present": bool(hashes["source_hash"]),
        "content_hash_present": bool(hashes["content_hash"]),
        "provenance_hash_present": bool(hashes["provenance_hash"]),
        "public_route": f"/book/{slug}" if status == PUBLIC_STATUS_LIVE_APPROVED else "",
        "reader_route": f"/reader/{slug}" if status == PUBLIC_STATUS_LIVE_APPROVED else "",
        "sitemap_inclusion": f"/book/{slug}" in sitemap_urls or f"https://theearnalism.com/book/{slug}" in sitemap_urls,
    }


def catalog_truth_summary(
    rows: list[dict[str, Any]],
    *,
    sitemap_urls: set[str] | None = None,
    frontend_live_slugs: set[str] | None = None,
) -> dict[str, Any]:
    sitemap_urls = sitemap_urls or set()
    live_rows = [row for row in rows if row["classification"] == PUBLIC_STATUS_LIVE_APPROVED]
    pipeline_rows = [row for row in rows if row["classification"] == PUBLIC_STATUS_PIPELINE_CANDIDATE]
    unapproved_reader = [row for row in rows if row["classification"] != PUBLIC_STATUS_LIVE_APPROVED and row["reader_enabled"]]
    unapproved_audio = [row for row in rows if row["classification"] != PUBLIC_STATUS_LIVE_APPROVED and row["audio_enabled"]]
    unapproved_sitemap = [
        row
        for row in rows
        if row["classification"] != PUBLIC_STATUS_LIVE_APPROVED and row["sitemap_inclusion"]
    ]
    backend_live_slugs = {row["slug"] for row in live_rows}
    if frontend_live_slugs is None:
        backend_frontend_truth_mismatch: bool | str = "not_checked"
    else:
        backend_frontend_truth_mismatch = backend_live_slugs != frontend_live_slugs
    return {
        "live_approved_count": len(live_rows),
        "dracula_only_live_approved": [row["slug"] for row in live_rows] == [LIVE_APPROVED_SLUG],
        "backend_live_approved_slugs": sorted(backend_live_slugs),
        "frontend_controlled_live_slugs": sorted(frontend_live_slugs) if frontend_live_slugs is not None else [],
        "pipeline_candidate_count": len(pipeline_rows),
        "unapproved_reader_link_count": len(unapproved_reader),
        "unapproved_audio_link_count": len(unapproved_audio),
        "unapproved_sitemap_count": len(unapproved_sitemap),
        "backend_frontend_truth_mismatch": backend_frontend_truth_mismatch,
        "launch_blockers": [
            "Non-Dracula live approved item detected" for row in live_rows if row["slug"] != LIVE_APPROVED_SLUG
        ]
        + ["Unapproved reader links detected"] * bool(unapproved_reader)
        + ["Unapproved audio links detected"] * bool(unapproved_audio)
        + ["Unapproved sitemap entries detected"] * bool(unapproved_sitemap)
        + ["Backend/frontend controlled live slug mismatch"] * bool(backend_frontend_truth_mismatch is True),
    }
