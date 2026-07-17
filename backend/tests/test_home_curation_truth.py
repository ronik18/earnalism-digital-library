import json
from pathlib import Path

from backend import catalog_truth
from backend.home_curation import (
    build_home_curated_payload,
    home_curation_evidence,
    is_safe_cover_url,
    select_curated_books,
)


ROOT = Path(__file__).resolve().parents[2]
APPROVED_AUDIO_SLUGS = {"book-2b9853ec52", "a-ghost-story", "sredni-vashtar"}
DEFERRED_AUDIO_SLUGS = {"great-expectations", "jane-eyre"}


def all_payload_books(payload):
    books = list(payload["hero"]["featured_books"])
    for shelf in payload["shelves"].values():
        books.extend(shelf)
    return books


def test_home_curated_payload_is_deterministic_and_tracks_32_reader_titles():
    first = build_home_curated_payload()
    second = build_home_curated_payload()

    assert first == second
    assert first["source"] == {
        "generated_at": "2026-07-17T08:00:00Z",
        "truth_source": "controlled_publications",
        "sprint1_active_count": 32,
        "reader_enabled_count": 32,
        "approved_audiobook_count": 3,
        "cover_eligible_count": 19,
        "omitted_visual_count": 13,
    }
    assert first["hero"]["primary_cta"] == {"label": "Start Reading", "url": "/library"}
    assert first["hero"]["secondary_cta"]["url"] == "/library?availability=approved-audiobook"


def test_featured_books_are_the_exact_admin_pinned_canonical_records():
    payload = build_home_curated_payload()
    featured = payload["hero"]["featured_books"]
    assert [book["slug"] for book in featured] == [
        "book-2b9853ec52",
        "bn-066",
        "radharani",
        "a-ghost-story",
        "pride-and-prejudice",
        "sredni-vashtar",
    ]

    for book in featured:
        artifact_dir = catalog_truth.first_controlled_artifact_dir(book["slug"])
        canonical = json.loads((artifact_dir / "public_book.json").read_text(encoding="utf-8"))
        canonical_front = (
            canonical.get("front_cover_url")
            or canonical.get("cover_url")
            or canonical.get("cover_image_url")
            or canonical.get("thumbnail_url")
        )
        assert book["title"] == canonical["title"]
        assert book["author"] == canonical["author"]
        assert book["front_cover_url"] == canonical_front
        assert book["cover_alt_text"] == f"{canonical['title']} by {canonical['author']}"
        assert book["reader_enabled"] is True
        assert is_safe_cover_url(book["front_cover_url"])


def test_audio_ctas_fail_closed_and_only_three_approved_books_can_listen():
    payload = build_home_curated_payload()
    approved = payload["shelves"]["approved_audiobooks"]
    assert {book["slug"] for book in approved} == APPROVED_AUDIO_SLUGS

    by_slug = {book["slug"]: book for book in all_payload_books(payload)}
    for slug, book in by_slug.items():
        if slug in APPROVED_AUDIO_SLUGS:
            assert book["audiobook_enabled"] is True
            assert book["audiobook_release_gate"] == "PUBLIC_AUDIO_RELEASE_APPROVED"
            assert book["audio_qa_status"] in {"APPROVED", "PASS", "PASSED", "QA_PASSED"}
            assert book["cta_kind"] == "listen"
            assert book["cta_label"] == "Start Listening"
            assert book["cta_url"] == f"/reader/{slug}?listen=1"
            assert book["audiobook_url"] == f"/api/reader/book/{slug}/audiobook"
        else:
            assert book["audiobook_enabled"] is False
            assert book["cta_kind"] == "read"
            assert "Listen" not in book["cta_label"]
            assert "audiobook_url" not in book


def test_missing_cover_titles_are_omitted_from_every_visual_collection():
    evidence = home_curation_evidence()
    payload_slugs = {book["slug"] for book in all_payload_books(evidence["payload"])}
    omitted_for_cover = {
        item["slug"]
        for item in evidence["omitted"]
        if item["reason"] == "canonical front cover is missing"
    }

    assert omitted_for_cover
    assert omitted_for_cover.isdisjoint(payload_slugs)
    assert {"pather-panchali", "devdas", "the-last-leaf"}.issubset(omitted_for_cover)


def test_deferred_long_classics_are_not_sprint1_audio_or_hero_records():
    config = json.loads((ROOT / "backend/data/home_hero_curation.json").read_text(encoding="utf-8"))
    payload = build_home_curated_payload()
    payload_slugs = {book["slug"] for book in all_payload_books(payload)}

    assert DEFERRED_AUDIO_SLUGS.isdisjoint(config["sprint1_active_slugs"])
    assert DEFERRED_AUDIO_SLUGS.isdisjoint(payload_slugs)


def test_pinned_rank_precedes_privacy_safe_popularity_fallback():
    books = [
        {"slug": "popular", "reader_enabled": True, "front_cover_url": "https://example.com/popular.png", "popularity_score": 99},
        {"slug": "pinned-two", "reader_enabled": True, "front_cover_url": "https://example.com/two.png", "admin_pinned": True, "hero_rank": 2},
        {"slug": "pinned-one", "reader_enabled": True, "front_cover_url": "https://example.com/one.png", "admin_pinned": True, "hero_rank": 1},
        {"slug": "blocked", "reader_enabled": True, "front_cover_url": "https://example.com/blocked.png", "admin_pinned": True, "hero_rank": 0, "do_not_feature": True},
    ]

    assert [book["slug"] for book in select_curated_books(books, 3)] == [
        "pinned-one",
        "pinned-two",
        "popular",
    ]


def test_admin_curation_cannot_enable_audio(tmp_path):
    config = json.loads((ROOT / "backend/data/home_hero_curation.json").read_text(encoding="utf-8"))
    config["books"].setdefault("bn-066", {})["audiobook_enabled"] = True
    config["books"]["bn-066"]["audiobook_release_gate"] = "APPROVED"
    config_path = tmp_path / "home_hero_curation.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    payload = build_home_curated_payload(config_path=config_path)
    bn_066 = next(book for book in payload["hero"]["featured_books"] if book["slug"] == "bn-066")
    assert bn_066["audiobook_enabled"] is False
    assert bn_066["cta_kind"] == "read"
    assert "audiobook_url" not in bn_066


def test_server_registers_the_preferred_endpoint():
    source = (ROOT / "backend/server.py").read_text(encoding="utf-8")
    assert '@api.get("/home/curated")' in source
    assert "return build_home_curated_payload()" in source
