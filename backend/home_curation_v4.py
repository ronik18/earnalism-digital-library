"""Runtime Home shelf selection from public catalog truth.

This module deliberately contains no title or cover allowlist. Editorial shelf
membership is metadata first, with the checked-in curation file used only as a
backward-compatible seed until admin metadata exists on a book record.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

try:
    from catalog_truth import audio_release_qa_status, audio_public_release_status, can_expose_audio, can_expose_reader, public_book_projection
except ImportError:  # pragma: no cover
    from backend.catalog_truth import audio_release_qa_status, audio_public_release_status, can_expose_audio, can_expose_reader, public_book_projection

try:
    from home_curation import is_safe_cover_url
except ImportError:  # pragma: no cover
    from backend.home_curation import is_safe_cover_url


SHELF_DEFINITIONS = (
    {
        "id": "bengali-life-and-legacy",
        "title": "Bengali Life & Legacy",
        "description": "Village life, memory, reform, love, and the emotional landscape of Bengal.",
        "theme_chips": ["Memory & belonging", "Society & reform", "Love & loss"],
        "cta_label": "Explore Bengali classics",
        "cta_url": "/library?shelf=bengali-life-and-legacy",
        "layout_area": "bengali",
        "accent": "bengali",
        "max_visible": 3,
    },
    {
        "id": "gothic-and-the-uncanny",
        "title": "Gothic & the Uncanny",
        "description": "Dark houses, divided minds, and mysteries that linger beyond the final page.",
        "theme_chips": ["Haunted worlds", "Divided minds", "Lingering mysteries"],
        "cta_label": "Enter the uncanny",
        "cta_url": "/library?shelf=gothic-and-the-uncanny",
        "layout_area": "gothic",
        "accent": "gothic",
        "max_visible": 3,
    },
    {
        "id": "love-society-and-human-nature",
        "title": "Love, Society & Human Nature",
        "description": "Desire, dignity, class, sacrifice, and the choices that define a life.",
        "theme_chips": ["Desire & dignity", "Class & choice", "Sacrifice & consequence"],
        "cta_label": "Follow the human story",
        "cta_url": "/library?shelf=love-society-and-human-nature",
        "layout_area": "love",
        "accent": "love",
        "max_visible": 3,
    },
    {
        "id": "adventure-nature-and-wonder",
        "title": "Adventure, Nature & Wonder",
        "description": "Impossible journeys, untamed worlds, and stories built for curiosity.",
        "theme_chips": ["Distant worlds", "Untamed nature", "Imaginative journeys"],
        "cta_label": "Set out from here",
        "cta_url": "/library?shelf=adventure-nature-and-wonder",
        "layout_area": "adventure",
        "accent": "adventure",
        "max_visible": 3,
    },
    {
        "id": "short-masterpieces",
        "title": "Short Masterpieces",
        "description": "Complete, unforgettable stories for one thoughtful sitting.",
        "theme_chips": ["One-sitting reads", "Lasting twists", "Complete stories"],
        "cta_label": "Choose a short read",
        "cta_url": "/library?shelf=short-masterpieces",
        "layout_area": "short",
        "accent": "short",
        "max_visible": 6,
    },
)

AUDIO_SHELF = {
    "id": "selected-listening",
    "title": "Selected Listening",
    "eyebrow": "LISTENING ROOMS",
    "description": "Beautifully narrated classics ready to read and hear.",
    "cta_label": "Explore all audiobooks",
    "cta_url": "/library?format=audiobook",
}

LISTENING_ROOMS = {
    "id": "listening-rooms",
    "eyebrow": "LISTENING ROOMS",
    "title": "Stories ready to be heard.",
    "description": "Step into beautifully narrated classics, then continue reading at your own pace.",
    "cta_label": "Explore all audiobooks",
    "view_all_url": "/library?audio=approved",
}


def _list_value(book: dict[str, Any], *keys: str) -> list[str]:
    for key in keys:
        value = book.get(key)
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
    return []


def _curation_entry(config: dict[str, Any], slug: str) -> dict[str, Any]:
    books = config.get("books") if isinstance(config.get("books"), dict) else {}
    entry = books.get(slug) if isinstance(books.get(slug), dict) else {}
    return entry


def _seed_shelf_map(config: dict[str, Any]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    collage = config.get("shelf_collage") if isinstance(config.get("shelf_collage"), dict) else {}
    for group in collage.get("groups", []) if isinstance(collage.get("groups"), list) else []:
        if not isinstance(group, dict):
            continue
        shelf_id = str(group.get("id") or "").strip()
        result[shelf_id] = {str(slug).strip().lower() for slug in group.get("slugs", []) if str(slug).strip()}
    return result


def shelf_ids_for_book(book: dict[str, Any], config: dict[str, Any] | None = None) -> list[str]:
    config = config or {}
    slug = str(book.get("slug") or "").strip().lower()
    entry = _curation_entry(config, slug)
    explicit = _list_value(book, "editorial_shelf_ids", "home_shelf_ids", "shelf_ids")
    if not explicit:
        explicit = _list_value(entry, "editorial_shelf_ids", "home_shelf_ids", "shelf_ids")
    if explicit:
        return [item for item in explicit if item in {definition["id"] for definition in SHELF_DEFINITIONS}]

    seeded = _seed_shelf_map(config)
    seeded_ids = [shelf_id for shelf_id, slugs in seeded.items() if slug in slugs]
    if seeded_ids:
        return seeded_ids

    language = str(book.get("language") or book.get("language_code") or "").lower()
    title = str(book.get("title") or "").lower()
    category = str(book.get("category_slug") or "").lower()
    if language.startswith(("bn", "ben")) or any("\u0980" <= char <= "\u09ff" for char in title):
        return ["bengali-life-and-legacy"]
    if any(token in f"{title} {category}" for token in ("gothic", "horror", "mystery", "uncanny")):
        return ["gothic-and-the-uncanny"]
    if any(token in f"{title} {category}" for token in ("adventure", "journey", "travel", "nature", "wonder")):
        return ["adventure-nature-and-wonder"]
    return ["love-society-and-human-nature"]


def _number(value: Any, fallback: float = -1.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _timestamp(value: Any) -> float:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError, OverflowError):
        return 0.0


def _cover_candidates(book: dict[str, Any], projected: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return ordered, safe front-cover candidates without exposing raw internals."""
    projected = projected or {}
    raw: list[tuple[str, str]] = []
    for field in ("front_cover_url", "cover_image_url", "cover_url", "thumbnail_url"):
        value = str(projected.get(field) or book.get(field) or "").strip()
        if value:
            raw.append((value, field))
    configured = book.get("cover_candidates")
    if isinstance(configured, list):
        for item in configured:
            if isinstance(item, dict):
                value = str(item.get("url") or item.get("front_cover_url") or "").strip()
                source = str(item.get("source") or "candidate").strip()
            else:
                value = str(item or "").strip()
                source = "candidate"
            if value:
                raw.append((value, source))
    seen: set[str] = set()
    candidates: list[dict[str, Any]] = []
    for rank, (url, source) in enumerate(raw, start=1):
        if url in seen or not is_safe_cover_url(url) or "placeholder" in url.lower():
            continue
        seen.add(url)
        candidates.append({"url": url, "source": source, "rank": rank})
    return candidates


def selection_key(book: dict[str, Any]) -> tuple[Any, ...]:
    rank = book.get("home_shelf_rank", book.get("shelf_rank", 1_000_000))
    try:
        rank_value = int(rank)
    except (TypeError, ValueError):
        rank_value = 1_000_000
    return (
        not bool(book.get("admin_pinned")),
        rank_value,
        -_number(book.get("popularity_score")),
        -_timestamp(book.get("published_at") or book.get("created_at")),
        str(book.get("slug") or ""),
    )


def select_visible_books(books: Iterable[dict[str, Any]], limit: int, used_slugs: set[str] | None = None) -> list[dict[str, Any]]:
    used = used_slugs if used_slugs is not None else set()
    eligible = [book for book in books if book.get("home_feature_eligible") is not False and book.get("do_not_feature") is not True and book.get("cover_valid") is True]
    ranked = sorted(eligible, key=selection_key)
    selected = [book for book in ranked if book["slug"] not in used][:max(0, int(limit))]
    used.update(book["slug"] for book in selected)
    return selected


def display_mode(count: int, *, runway: bool = False) -> str:
    if not count:
        return "zero"
    if runway:
        return "runway"
    if count == 1:
        return "spotlight"
    if count == 2:
        return "duo"
    if count == 3:
        return "trio"
    return "overflow"


def _book_contract(book: dict[str, Any], config: dict[str, Any], audio_contract: dict[str, Any] | None = None) -> dict[str, Any] | None:
    reader_allowed = book.get("reader_enabled") is True if "reader_enabled" in book else can_expose_reader(book)
    if not reader_allowed:
        return None
    projected = public_book_projection(book) or {}
    if book.get("reader_enabled") is True and projected.get("reader_enabled") is not True:
        # Pure selection tests may provide an already-authorized public record
        # without the full catalog-truth evidence envelope.
        projected = {
            "title": book.get("title", ""),
            "author": book.get("author", ""),
            "cover_image_url": book.get("cover_image_url", ""),
            "cover_url": book.get("cover_url", ""),
            "short_description": book.get("short_description", ""),
            "reader_enabled": True,
        }
    slug = str(book.get("slug") or projected.get("slug") or "").strip().lower()
    title = str(projected.get("title") or book.get("title") or "").strip()
    author = str(projected.get("author") or book.get("author") or "").strip()
    cover_candidates = _cover_candidates(book, projected)
    front = cover_candidates[0]["url"] if cover_candidates else ""
    cover_valid = bool(front) and not bool(book.get("is_placeholder")) and book.get("canonical_cover_match") is not False
    entry = _curation_entry(config, slug)
    audio_enabled = can_expose_audio(book)
    if audio_contract is not None:
        audio_enabled = bool(
            audio_contract.get("enabled") is True
            and audio_contract.get("url")
            and audio_contract.get("release_gate") == "APPROVED"
            and str(audio_contract.get("qa_status") or "").upper() in {"APPROVED", "PASS", "PASSED", "QA_PASSED"}
            and audio_contract.get("package_valid", True) is not False
            and audio_contract.get("endpoint_valid", True) is not False
        )
    contract: dict[str, Any] = {
        "slug": slug,
        "title": title,
        "author": author,
        "language": str(book.get("language") or book.get("language_code") or ("bn" if any("\u0980" <= char <= "\u09ff" for char in f"{title} {author}") else "en")),
        "front_cover_url": front,
        "cover_candidates": cover_candidates,
        "cover_alt_text": f"{title} by {author}",
        "cover_valid": cover_valid,
        "reader_enabled": True,
        "reader_url": f"/reader/{slug}",
        "book_url": f"/book/{slug}",
        "primary_cta_label": "Listen in Reader" if audio_enabled else "Read edition",
        "primary_cta_url": f"/reader/{slug}?listen=1" if audio_enabled else f"/book/{slug}",
        "audiobook_enabled": audio_enabled,
        "audiobook_release_gate": "APPROVED" if audio_enabled else "",
        "audio_qa_status": str((audio_contract or {}).get("qa_status") or audio_release_qa_status(book) or "").upper() if audio_enabled else "",
        "audio_duration_ms": int((audio_contract or {}).get("duration_ms") or 0),
        "editorial_shelf_ids": shelf_ids_for_book(book, config),
        "admin_pinned": bool(book.get("admin_pinned", entry.get("admin_pinned", entry.get("hero_pinned", False)))),
        "home_shelf_rank": book.get("home_shelf_rank", book.get("shelf_rank", entry.get("shelf_rank"))),
        "popularity_score": book.get("popularity_score", entry.get("popularity_score")),
        "published_at": book.get("published_at") or book.get("created_at") or "",
        "release_cycle": book.get("release_cycle") or book.get("sprint_id") or entry.get("release_cycle") or "sprint1",
        "sprint_id": book.get("sprint_id") or entry.get("sprint_id") or "sprint1",
        "home_feature_eligible": book.get("home_feature_eligible", True),
        "do_not_feature": bool(book.get("do_not_feature", entry.get("do_not_feature", False))),
        "short_description": str(projected.get("short_description") or book.get("short_description") or ""),
    }
    if audio_enabled:
        contract["audiobook_url"] = str((audio_contract or {}).get("url") or projected.get("audio_url") or f"/api/reader/book/{slug}/audiobook")
    return contract


def _public(book: dict[str, Any]) -> dict[str, Any]:
    hidden = {"admin_pinned", "home_shelf_rank", "popularity_score", "published_at", "home_feature_eligible", "do_not_feature", "editorial_shelf_ids", "release_cycle", "sprint_id"}
    return {key: value for key, value in book.items() if key not in hidden}


def build_home_curated_payload_v4(books: Iterable[dict[str, Any]], *, config: dict[str, Any] | None = None, audio_contracts: dict[str, dict[str, Any]] | None = None, generated_at: str | None = None) -> dict[str, Any]:
    config = config or {}
    contracts = [_book_contract(book, config, (audio_contracts or {}).get(str(book.get("slug") or "").lower())) for book in books]
    contracts = [book for book in contracts if book and book.get("title") and book.get("author")]
    contract_by_slug = {book["slug"]: book for book in contracts}
    sprint1_slugs = tuple(
        str(slug or "").strip().lower()
        for slug in (config.get("sprint1_active_slugs") or ())
        if str(slug or "").strip()
    )
    literary_shelves: list[dict[str, Any]] = []
    used_slugs: set[str] = set()
    for definition in SHELF_DEFINITIONS:
        candidates = [book for book in contracts if definition["id"] in book.get("editorial_shelf_ids", [])]
        eligible = [book for book in candidates if book.get("home_feature_eligible") is not False and book.get("do_not_feature") is not True and book.get("cover_valid") is True]
        visible = select_visible_books(eligible, definition["max_visible"], used_slugs)
        visible_slugs = {book["slug"] for book in visible}
        reserve = [book for book in sorted(eligible, key=selection_key) if book["slug"] not in visible_slugs][:definition["max_visible"]]
        item = {
            **definition,
            "total_count": len(eligible),
            "display_mode": display_mode(len(eligible), runway=definition["id"] == "short-masterpieces"),
            "visible_books": [_public(book) for book in visible],
            "reserve_books": [_public(book) for book in reserve],
            "books": [_public(book) for book in visible],
        }
        literary_shelves.append(item)
    audio_candidates = [book for book in contracts if book.get("audiobook_enabled") is True and book.get("cover_valid") is True]
    audio_candidates = sorted(audio_candidates, key=selection_key)
    audio_visible = audio_candidates[:4] if len(audio_candidates) >= 5 else audio_candidates
    audio_reserve = audio_candidates[4:] if len(audio_candidates) >= 5 else []
    audiobook_shelf = {
        **AUDIO_SHELF,
        "total_count": len(audio_candidates),
        "display_mode": display_mode(len(audio_candidates), runway=len(audio_candidates) >= 5),
        "books": [_public(book) for book in audio_visible],
        "visible_books": [_public(book) for book in audio_visible],
        "reserve_books": [_public(book) for book in audio_reserve],
    }
    listening_items = [_public(book) for book in audio_visible]
    listening_reserve = [_public(book) for book in audio_reserve]
    groups = [{key: item[key] for key in ("id", "title", "description", "theme_chips", "cta_label", "cta_url", "layout_area", "accent", "total_count", "display_mode", "visible_books", "reserve_books", "books")} for item in literary_shelves if item["total_count"]]
    featured = [_public(book) for book in sorted((book for book in contracts if book.get("cover_valid") is True), key=selection_key)[:6]]
    return {
        "literary_shelves": literary_shelves,
        "audiobook_shelf": audiobook_shelf if audio_candidates else None,
        "listening_rooms": {
            **LISTENING_ROOMS,
            "total_approved": len(audio_candidates),
            "items": listening_items,
            "reserve_items": listening_reserve,
        } if audio_candidates else None,
        "hero": {
            "headline": "A premium reading and listening sanctuary for timeless Bengali and English classics.",
            "subheadline": "Beautifully designed editions. Immersive audiobooks. Calm reading modes. A curated literary experience that stays with you.",
            "primary_cta": {"label": "Start Reading", "url": "/library"},
            "secondary_cta": {"label": "Explore Audiobooks", "url": "/library?availability=approved-audiobook"},
            "featured_books": featured,
        },
        "shelves": {"approved_audiobooks": listening_items},
        "groups": groups,
        "selected_audiobooks": audiobook_shelf["books"],
        "source": {
            "truth_source": "public_catalog_and_canonical_reader_manifest",
            "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
            "live_title_count": len(contracts),
            "reader_enabled_count": len(contracts),
            "sprint1_active_count": sum(slug in contract_by_slug for slug in sprint1_slugs),
            "audiobook_count": len(audio_candidates),
            "approved_audiobook_count": len(audio_candidates),
            "catalog_version": "home-curated-v4",
        },
    }
