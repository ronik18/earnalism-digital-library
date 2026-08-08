from __future__ import annotations

import json

from backend.home_surface_contracts import (
    HERO_SCHEMA_VERSION,
    LISTENING_SCHEMA_VERSION,
    build_home_hero_contract,
    build_home_listening_contract,
)


def _book(slug: str, *, audio: bool = False, endpoint: str | None = None) -> dict:
    book = {
        "slug": slug,
        "title": slug.replace("-", " ").title(),
        "author": "Author",
        "language": "en",
        "front_cover_url": f"https://cdn.example.com/{slug}.webp",
        "cover_alt_text": f"{slug} cover",
        "cover_valid": True,
        "reader_enabled": True,
        "book_url": f"/book/{slug}",
        "reader_url": f"/reader/{slug}",
    }
    if audio:
        book.update({
            "primary_cta_url": f"/reader/{slug}?listen=1",
            "audiobook_enabled": True,
            "audiobook_release_gate": "APPROVED",
            "audio_qa_status": "QA_PASSED",
            "audio_duration_ms": 123_000,
            "audiobook_url": endpoint or f"/api/reader/book/{slug}/audiobook",
        })
    return book


def _payload() -> dict:
    hero_books = [_book(f"hero-{index}") for index in range(16)]
    listening = [_book(f"audio-{index}", audio=True) for index in range(4)]
    return {
        "hero": {
            "headline": "A premium library",
            "subheadline": "Read and listen.",
            "primary_cta": {"label": "Read", "url": "/library"},
            "secondary_cta": {"label": "Listen", "url": "/library?audio=approved"},
            "carousel_books": hero_books,
            "featured_books": hero_books[:6],
        },
        "listening_rooms": {"items": listening},
        "source": {
            "truth_source": "public_catalog_and_canonical_reader_manifest",
            "generated_at": "2026-08-09T00:00:00Z",
            "catalog_version": "test-v1",
            "internal_count": 999,
        },
        "rights_metadata": {"must_not_leak": True},
    }


def test_hero_contract_is_minimal_bounded_and_stable_across_generation_time():
    payload = _payload()
    contract = build_home_hero_contract(payload)
    regenerated = build_home_hero_contract({
        **payload,
        "source": {**payload["source"], "generated_at": "2026-08-09T01:00:00Z"},
    })

    assert contract["schema_version"] == HERO_SCHEMA_VERSION
    assert len(contract["hero"]["carousel_books"]) == 16
    assert "featured_books" not in contract["hero"]
    assert "rights_metadata" not in contract
    assert "audiobook_enabled" not in contract["hero"]["carousel_books"][0]
    assert contract["revision"] == regenerated["revision"]
    assert len(json.dumps(contract, ensure_ascii=False).encode("utf-8")) <= 15 * 1024


def test_listening_contract_fails_closed_and_stays_under_transfer_budget():
    payload = _payload()
    payload["listening_rooms"]["items"].extend([
        _book("wrong-endpoint", audio=True, endpoint="/api/reader/book/another/audiobook"),
        {**_book("not-approved", audio=True), "audiobook_release_gate": "BLOCKED"},
        {**_book("bad-cover", audio=True), "cover_valid": False},
    ])

    contract = build_home_listening_contract(payload, limit=3)

    assert contract["schema_version"] == LISTENING_SCHEMA_VERSION
    assert contract["total"] == 4
    assert [item["slug"] for item in contract["items"]] == ["audio-0", "audio-1", "audio-2"]
    assert all(item["cta_kind"] == "listen" for item in contract["items"])
    assert all(item["audio_package_valid"] is True for item in contract["items"])
    assert len(json.dumps(contract, ensure_ascii=False).encode("utf-8")) <= 8 * 1024


def test_listening_limit_is_clamped_to_public_contract_maximum():
    contract = build_home_listening_contract(_payload(), limit=99)
    assert len(contract["items"]) == 4
