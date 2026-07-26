from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

try:
    from catalog_truth import (
        audio_public_release_status,
        audio_release_qa_status,
        can_expose_audio,
        can_expose_reader,
        first_controlled_artifact_dir,
        load_controlled_artifact_book,
        public_book_projection,
        read_json_file,
    )
except ImportError:  # pragma: no cover - package-style imports in tests
    from backend.catalog_truth import (
        audio_public_release_status,
        audio_release_qa_status,
        can_expose_audio,
        can_expose_reader,
        first_controlled_artifact_dir,
        load_controlled_artifact_book,
        public_book_projection,
        read_json_file,
    )


MODULE_DIR = Path(__file__).resolve().parent
DEFAULT_CURATION_CONFIG_PATH = MODULE_DIR / "data" / "home_hero_curation.json"
GRAPHICAL_COVER_REPORT_PATH = MODULE_DIR.parent / "graphical_cover_generation_report.json"
PUBLIC_AUDIO_RELEASE_APPROVED = "PUBLIC_AUDIO_RELEASE_APPROVED"
AUDIO_QA_PASSED = {"APPROVED", "PASS", "PASSED", "QA_PASSED"}
COVER_AUDIT_BLOCKED_STATUSES = {
    "COVER_MISSING",
    "DESIGNED_PLACEHOLDER_NO_SAFE_LOCAL_COVER",
    "GRAPHICAL_COVER_REPAIR_REQUIRED",
    "TYPOGRAPHIC_ONLY_BLOCKER",
}

HERO_HEADLINE = "A premium reading and listening sanctuary for timeless Bengali and English classics."
HERO_SUBHEADLINE = (
    "Beautifully designed editions. Immersive audiobooks. Calm reading modes. "
    "A curated literary experience that stays with you."
)


def _read_config(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path else DEFAULT_CURATION_CONFIG_PATH
    payload = read_json_file(target)
    if not payload:
        raise RuntimeError(f"Home hero curation config is missing or invalid: {target}")
    slugs = payload.get("sprint1_active_slugs")
    if not isinstance(slugs, list) or not slugs:
        raise RuntimeError("Home hero curation config has no Sprint 1 slug list.")
    return payload


def _normalized_language(value: Any, *, title: str = "", author: str = "") -> str:
    language = str(value or "").strip().lower()
    if language.startswith(("bn", "ben")):
        return "bn"
    if language.startswith(("en", "eng")):
        return "en"
    if any("\u0980" <= character <= "\u09ff" for character in f"{title} {author}"):
        return "bn"
    return "en"


def is_safe_cover_url(value: Any) -> bool:
    url = str(value or "").strip()
    if not url or "placeholder" in url.lower() or url.lower().startswith(("data:", "javascript:")):
        return False
    if url.startswith("/"):
        return not url.startswith("/audio/")
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _first_cover(book: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(book.get(key) or "").strip()
        if is_safe_cover_url(value):
            return value
    return ""


@lru_cache(maxsize=1)
def _cover_visual_exclusions() -> dict[str, dict[str, Any]]:
    """Load checked-in cover exceptions without guessing in React."""
    report = read_json_file(GRAPHICAL_COVER_REPORT_PATH)
    if not isinstance(report, dict):
        return {}
    exclusions: dict[str, dict[str, Any]] = {}
    fallback_rows = report.get("runtime_graphical_fallbacks")
    if isinstance(fallback_rows, list):
        for row in fallback_rows:
            if isinstance(row, dict) and row.get("front") is True:
                slug = str(row.get("slug") or "").strip().lower()
                if slug:
                    exclusions[slug] = {
                        "kind": "runtime_graphical_fallback",
                        "reason": "Cover-generation report records a runtime graphical fallback.",
                    }
    visual_rows = report.get("visual_placeholder_candidates")
    if isinstance(visual_rows, list):
        for row in visual_rows:
            if isinstance(row, dict) and row.get("front") is True:
                slug = str(row.get("slug") or "").strip().lower()
                if slug:
                    exclusions[slug] = {
                        "kind": str(row.get("kind") or "visual_placeholder").strip().lower(),
                        "reason": str(row.get("reason") or "Cover failed visual truth review.").strip(),
                    }
    return exclusions


def _cover_truth(slug: str, book: dict[str, Any], front_cover_url: str) -> dict[str, Any]:
    """Expose a conservative cover eligibility contract backed by catalog metadata."""
    status = str(book.get("cover_audit_status") or book.get("cover_status") or "").strip().upper()
    audit_status = status or ("GRAPHICAL_COVER_APPROVED" if front_cover_url else "COVER_MISSING")
    url_lower = front_cover_url.lower()
    exclusion = _cover_visual_exclusions().get(slug.strip().lower())
    is_runtime_fallback = exclusion is not None and exclusion.get("kind") == "runtime_graphical_fallback"
    is_visual_placeholder = exclusion is not None and exclusion.get("kind") == "visual_placeholder"
    is_cover_mismatch = exclusion is not None and exclusion.get("kind") == "canonical_cover_mismatch"
    is_placeholder = bool(
        book.get("is_placeholder") is True
        or is_runtime_fallback
        or is_visual_placeholder
        or "placeholder" in url_lower
        or "placeholder" in status
    )
    is_typographic_only = bool(book.get("is_typographic_only") is True or "typographic" in status)
    canonical_cover_match = book.get("canonical_cover_match") is not False and not is_cover_mismatch
    cover_valid = bool(front_cover_url) and canonical_cover_match and not is_placeholder and not is_typographic_only and audit_status not in COVER_AUDIT_BLOCKED_STATUSES
    if exclusion is not None:
        audit_status = "CANONICAL_COVER_MISMATCH_BLOCKED" if is_cover_mismatch else "VISUAL_PLACEHOLDER_BLOCKED"
    return {
        "cover_valid": cover_valid,
        "is_placeholder": is_placeholder,
        "is_typographic_only": is_typographic_only,
        "cover_audit_status": audit_status,
        "canonical_cover_match": canonical_cover_match,
    }


def _number_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value)) if str(value).strip() else None
    except (TypeError, ValueError):
        return None


def _rank_value(value: Any, fallback: int = 1_000_000) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _selection_key(book: dict[str, Any]) -> tuple[Any, ...]:
    popularity = _number_or_none(book.get("popularity_score"))
    return (
        not bool(book.get("admin_pinned")),
        _rank_value(book.get("hero_rank")),
        -(popularity if popularity is not None else -1.0),
        _rank_value(book.get("shelf_rank")),
        _rank_value(book.get("fallback_rank")),
        str(book.get("slug") or ""),
    )


def select_curated_books(books: Iterable[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    eligible = [
        book
        for book in books
        if book.get("reader_enabled") is True
        and is_safe_cover_url(book.get("front_cover_url"))
        and book.get("cover_valid", True) is not False
        and book.get("is_placeholder") is not True
        and book.get("is_typographic_only") is not True
        and book.get("do_not_feature") is not True
    ]
    return sorted(eligible, key=_selection_key)[: max(0, int(limit))]


def _book_contract(
    slug: str,
    *,
    publications_root: Path | None,
    curation: dict[str, Any],
    fallback_rank: int,
) -> tuple[dict[str, Any] | None, str]:
    artifact_dir = publications_root / slug if publications_root else first_controlled_artifact_dir(slug)
    if not artifact_dir.exists():
        return None, "controlled publication is missing"
    book = load_controlled_artifact_book(slug, include_content=False, artifact_dir=artifact_dir)
    if not book or not can_expose_reader(book):
        return None, "controlled publication did not pass the reader truth gate"
    projection = public_book_projection(book) or {}
    title = str(projection.get("title") or "").strip()
    author = str(projection.get("author") or "").strip()
    if not title or not author:
        return None, "canonical title or author is missing"

    reader_manifest = read_json_file(artifact_dir / "reader_manifest.json")
    approval_evidence = read_json_file(artifact_dir / "approval_evidence.json")
    front_cover_url = _first_cover(
        projection,
        "front_cover_url",
        "cover_url",
        "cover_image_url",
        "thumbnail_url",
    )
    back_cover_url = _first_cover(
        projection,
        "back_cover_url",
        "back_cover_image_url",
        "back_cover_thumbnail_url",
    )
    cover_truth = _cover_truth(slug, book, front_cover_url)
    language = _normalized_language(
        reader_manifest.get("language") or projection.get("language") or projection.get("language_code"),
        title=title,
        author=author,
    )
    audio_enabled = can_expose_audio(book)
    release_gate = audio_public_release_status(book) or "PUBLIC_AUDIO_RELEASE_BLOCKED"
    qa_status = audio_release_qa_status(book) or str(approval_evidence.get("qa_status") or "").strip().upper()
    curation_entry = curation if isinstance(curation, dict) else {}
    popularity_score = _number_or_none(
        projection.get("popularity_score")
        if projection.get("popularity_score") is not None
        else curation_entry.get("popularity_score")
    )

    contract: dict[str, Any] = {
        "slug": slug,
        "title": title,
        "author": author,
        "language": language,
        "front_cover_url": front_cover_url,
        "back_cover_url": back_cover_url,
        **cover_truth,
        "cover_alt_text": f"{title} by {author}",
        "reader_enabled": True,
        "book_url": f"/book/{slug}",
        "reader_url": f"/reader/{slug}",
        "audiobook_enabled": audio_enabled,
        "audiobook_release_gate": release_gate,
        "audio_qa_status": qa_status,
        "popularity_score": popularity_score,
        "admin_pinned": curation_entry.get("hero_pinned") is True,
        "display_badge": str(curation_entry.get("editorial_badge") or ("Bengali Classic" if language == "bn" else "English Classic")),
        "cta_label": "Start Listening" if audio_enabled else "Start Reading",
        "cta_url": f"/reader/{slug}?listen=1" if audio_enabled else f"/reader/{slug}",
        "cta_kind": "listen" if audio_enabled else "read",
        "hero_rank": curation_entry.get("hero_rank"),
        "shelf_rank": curation_entry.get("shelf_rank"),
        "do_not_feature": curation_entry.get("do_not_feature") is True,
        "fallback_rank": fallback_rank,
    }
    if audio_enabled:
        contract["audiobook_url"] = f"/api/reader/book/{slug}/audiobook"
    return contract, "" if cover_truth["cover_valid"] else "canonical front cover failed cover truth"


def _public_book(book: dict[str, Any]) -> dict[str, Any]:
    public = deepcopy(book)
    for internal_field in ("hero_rank", "shelf_rank", "do_not_feature", "fallback_rank"):
        public.pop(internal_field, None)
    return public


def _build_shelf_collage(
    contracts_by_slug: dict[str, dict[str, Any]],
    config: dict[str, Any],
    approved_audio: list[dict[str, Any]],
) -> dict[str, Any]:
    shelf_config = config.get("shelf_collage") if isinstance(config.get("shelf_collage"), dict) else {}
    groups_config = shelf_config.get("groups") if isinstance(shelf_config.get("groups"), list) else []
    groups: list[dict[str, Any]] = []
    used_visual_slugs: set[str] = set()

    for raw_group in groups_config:
        if not isinstance(raw_group, dict):
            continue
        group_slugs = [
            str(raw_slug or "").strip().lower()
            for raw_slug in raw_group.get("slugs", [])
            if str(raw_slug or "").strip()
        ]
        candidates = [
            contracts_by_slug[slug]
            for slug in group_slugs
            if slug in contracts_by_slug
            and contracts_by_slug[slug].get("do_not_feature") is not True
            and contracts_by_slug[slug].get("cover_valid") is True
        ]
        ranked_candidates = select_curated_books(candidates, len(candidates))
        unique_candidates = [
            book for book in ranked_candidates if book["slug"] not in used_visual_slugs
        ]
        selected = unique_candidates[: max(0, _rank_value(raw_group.get("cover_limit", raw_group.get("limit")), 3))]
        used_visual_slugs.update(book["slug"] for book in selected)
        groups.append({
            "id": str(raw_group.get("id") or "").strip(),
            "title": str(raw_group.get("title") or "").strip(),
            "description": str(raw_group.get("description") or "").strip(),
            "book_count": len(selected),
            "books": [_public_book(book) for book in selected],
            "cta_label": str(raw_group.get("cta_label") or "Explore the library").strip(),
            "cta_url": str(raw_group.get("cta_url") or "/library").strip(),
            "visual_variant": str(raw_group.get("visual_variant") or "medium").strip(),
            "accent": str(raw_group.get("accent") or "burgundy").strip(),
            "layout_area": str(raw_group.get("layout_area") or raw_group.get("id") or "shelf").strip(),
            "editorial_line": str(raw_group.get("editorial_line") or "").strip(),
            "icon": str(raw_group.get("icon") or "book-open").strip(),
        })

    return {
        "eyebrow": str(shelf_config.get("eyebrow") or "CURATED PATHS THROUGH THE LIBRARY").strip(),
        "title": str(shelf_config.get("title") or "A shelf for every kind of curiosity.").strip(),
        "description": str(shelf_config.get("description") or "").strip(),
        "groups": groups,
        "selected_audiobooks": [_public_book(book) for book in approved_audio],
    }


def build_home_curated_payload(
    *,
    publications_root: str | Path | None = None,
    config_path: str | Path | None = None,
) -> dict[str, Any]:
    config = _read_config(config_path)
    root = Path(publications_root) if publications_root else None
    active_slugs = [str(slug or "").strip().lower() for slug in config["sprint1_active_slugs"] if str(slug or "").strip()]
    curation_by_slug = config.get("books") if isinstance(config.get("books"), dict) else {}
    limits = config.get("limits") if isinstance(config.get("limits"), dict) else {}

    contracts: list[dict[str, Any]] = []
    omitted: list[dict[str, str]] = []
    for index, slug in enumerate(active_slugs, start=1):
        contract, reason = _book_contract(
            slug,
            publications_root=root,
            curation=curation_by_slug.get(slug, {}),
            fallback_rank=index,
        )
        if contract is None:
            omitted.append({"slug": slug, "reason": reason})
            continue
        contracts.append(contract)
        if reason:
            omitted.append({"slug": slug, "reason": reason})

    cover_ready = [
        book for book in contracts
        if is_safe_cover_url(book.get("front_cover_url")) and book.get("cover_valid") is True
    ]
    featured = select_curated_books(cover_ready, _rank_value(limits.get("featured_books"), 6))
    reader_favorites = select_curated_books(cover_ready, _rank_value(limits.get("reader_favorites"), 10))
    bengali = select_curated_books(
        (book for book in cover_ready if book.get("language") == "bn"),
        _rank_value(limits.get("bengali_classics"), 8),
    )
    english = select_curated_books(
        (book for book in cover_ready if book.get("language") == "en"),
        _rank_value(limits.get("english_classics"), 8),
    )
    approved_audio = sorted(
        (book for book in contracts if book.get("audiobook_enabled") is True),
        key=_selection_key,
    )
    contracts_by_slug = {book["slug"]: book for book in contracts}

    payload = {
        "hero": {
            "headline": HERO_HEADLINE,
            "subheadline": HERO_SUBHEADLINE,
            "primary_cta": {"label": "Start Reading", "url": "/library"},
            "secondary_cta": {
                "label": "Explore Audiobooks",
                "url": "/library?availability=approved-audiobook",
            },
            "featured_books": [_public_book(book) for book in featured],
        },
        "shelves": {
            "reader_favorites": [_public_book(book) for book in reader_favorites],
            "bengali_classics": [_public_book(book) for book in bengali],
            "english_classics": [_public_book(book) for book in english],
            "approved_audiobooks": [_public_book(book) for book in approved_audio],
        },
        "shelf_collage": _build_shelf_collage(contracts_by_slug, config, approved_audio),
        "source": {
            "generated_at": str(config.get("updated_at") or ""),
            "truth_source": "controlled_publications",
            "sprint1_active_count": len(active_slugs),
            "reader_enabled_count": sum(book.get("reader_enabled") is True for book in contracts),
            "approved_audiobook_count": sum(book.get("audiobook_enabled") is True for book in contracts),
            "cover_eligible_count": len(cover_ready),
            "omitted_visual_count": len(omitted),
        },
    }
    return payload


def home_curation_evidence(
    *,
    publications_root: str | Path | None = None,
    config_path: str | Path | None = None,
) -> dict[str, Any]:
    config = _read_config(config_path)
    root = Path(publications_root) if publications_root else None
    curation_by_slug = config.get("books") if isinstance(config.get("books"), dict) else {}
    selected_payload = build_home_curated_payload(publications_root=root, config_path=config_path)
    selected_slugs = {book["slug"] for book in selected_payload["hero"]["featured_books"]}
    rows: list[dict[str, Any]] = []
    omitted: list[dict[str, str]] = []
    for index, raw_slug in enumerate(config["sprint1_active_slugs"], start=1):
        slug = str(raw_slug or "").strip().lower()
        contract, reason = _book_contract(
            slug,
            publications_root=root,
            curation=curation_by_slug.get(slug, {}),
            fallback_rank=index,
        )
        if contract is None:
            omitted.append({"slug": slug, "reason": reason})
            continue
        row = _public_book(contract)
        row["selected_for_hero"] = slug in selected_slugs
        rows.append(row)
        if contract.get("do_not_feature") is True:
            omitted.append({
                "slug": slug,
                "reason": str(
                    curation_by_slug.get(slug, {}).get("feature_exclusion_reason")
                    or "admin curation excluded this title from homepage hero placement"
                ),
            })
        if reason:
            omitted.append({"slug": slug, "reason": reason})
    return {"payload": selected_payload, "catalog": rows, "omitted": omitted}
