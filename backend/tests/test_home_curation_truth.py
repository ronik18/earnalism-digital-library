import json
from pathlib import Path

from backend import catalog_truth, home_curation
from backend.home_curation import (
    _build_shelf_collage,
    build_home_curated_payload,
    home_curation_evidence,
    is_safe_cover_url,
    select_curated_books,
)


ROOT = Path(__file__).resolve().parents[2]
APPROVED_AUDIO_SLUGS = {"book-2b9853ec52", "a-ghost-story", "sredni-vashtar", "the-open-window"}
DEFERRED_AUDIO_SLUGS = {"great-expectations", "jane-eyre"}


def all_payload_books(payload):
    books = list(payload["hero"]["featured_books"])
    books.extend(payload["hero"]["carousel_books"])
    for shelf in payload["shelves"].values():
        books.extend(shelf)
    return books


def visual_payload_books(payload):
    books = list(payload["hero"]["featured_books"])
    books.extend(payload["hero"]["carousel_books"])
    books.extend(payload["shelves"].get("reader_favorites", []))
    books.extend(payload["shelves"].get("bengali_classics", []))
    books.extend(payload["shelves"].get("english_classics", []))
    for shelf in payload["shelf_collage"]["groups"]:
        books.extend(shelf["books"])
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
        "approved_audiobook_count": 4,
        "cover_eligible_count": 15,
        "hero_carousel_eligible_count": 15,
        "omitted_visual_count": 17,
    }
    assert first["hero"]["primary_cta"] == {"label": "Start Reading", "url": "/library"}
    assert first["hero"]["secondary_cta"]["url"] == "/library?availability=approved-audiobook"
    assert len(first["hero"]["carousel_books"]) == first["source"]["hero_carousel_eligible_count"]
    assert all(book["reader_enabled"] is True for book in first["hero"]["carousel_books"])
    assert all(is_safe_cover_url(book["front_cover_url"]) for book in first["hero"]["carousel_books"])


def test_featured_books_are_the_exact_admin_pinned_canonical_records():
    payload = build_home_curated_payload()
    featured = payload["hero"]["featured_books"]
    assert [book["slug"] for book in featured] == [
        "bn-066",
        "radharani",
        "pride-and-prejudice",
        "nishkriti",
        "muchiram-gurer-jibanchorit",
        "book-d19e96859f",
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


def test_audio_ctas_fail_closed_and_only_approved_books_can_listen():
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


def test_title_mismatched_cover_is_excluded_from_hero_without_changing_audio_gate():
    evidence = home_curation_evidence()
    featured_slugs = {book["slug"] for book in evidence["payload"]["hero"]["featured_books"]}
    approved_slugs = {book["slug"] for book in evidence["payload"]["shelves"]["approved_audiobooks"]}
    catalog_row = next(row for row in evidence["catalog"] if row["slug"] == "a-ghost-story")

    assert "a-ghost-story" not in featured_slugs
    assert "a-ghost-story" in approved_slugs
    assert catalog_row["audiobook_enabled"] is True
    assert any(
        item["slug"] == "a-ghost-story" and "title-mismatched" in item["reason"]
        for item in evidence["omitted"]
    )


def test_cover_visual_exclusion_report_is_bundled_for_backend_deployments():
    bundled_report = ROOT / "backend/data/graphical_cover_generation_report.json"
    assert bundled_report.exists()
    report = json.loads(bundled_report.read_text(encoding="utf-8"))
    excluded_slugs = {
        row["slug"]
        for row in report["visual_placeholder_candidates"]
        if row.get("front") is True
    }
    assert "book-2b9853ec52" in excluded_slugs
    assert "the-gift-of-the-magi" in excluded_slugs


def test_missing_root_report_falls_back_to_bundled_backend_report(monkeypatch):
    monkeypatch.setattr(
        home_curation,
        "GRAPHICAL_COVER_REPORT_PATHS",
        (ROOT / "does-not-exist.json", ROOT / "backend/data/graphical_cover_generation_report.json"),
    )
    home_curation._cover_visual_exclusions.cache_clear()
    assert "book-2b9853ec52" in home_curation._cover_visual_exclusions()
    home_curation._cover_visual_exclusions.cache_clear()


def test_missing_cover_titles_are_omitted_from_every_visual_collection():
    evidence = home_curation_evidence()
    payload_slugs = {book["slug"] for book in visual_payload_books(evidence["payload"])}
    omitted_for_cover = {
        item["slug"]
        for item in evidence["omitted"]
        if "cover truth" in item["reason"]
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


def test_shelf_allocator_reserves_hero_cover_before_cross_shelf_fallback():
    def book(slug, rank):
        return {
            "slug": slug,
            "title": slug,
            "author": "Author",
            "reader_enabled": True,
            "front_cover_url": f"https://cdn.example.com/{slug}.png",
            "cover_valid": True,
            "is_placeholder": False,
            "is_typographic_only": False,
            "canonical_cover_match": True,
            "shelf_rank": rank,
        }

    result = _build_shelf_collage(
        {slug: book(slug, rank) for rank, slug in enumerate(("hero-cover", "alternate-cover"), start=1)},
        {
            "shelf_collage": {
                "groups": [{
                    "id": "test-shelf",
                    "title": "Test shelf",
                    "slugs": ["hero-cover", "alternate-cover"],
                    "cover_limit": 1,
                    "layout_area": "test",
                }],
            },
        },
        [],
        reserved_visual_slugs=("hero-cover",),
    )

    assert [book["slug"] for book in result["groups"][0]["books"]] == ["alternate-cover"]

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
    assert "canonical, release-safe Home curation contract" in source


def test_frontend_boot_snapshot_exactly_matches_canonical_home_payload():
    snapshot_path = ROOT / "frontend/src/data/homeCuratedSprint1.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

    assert snapshot == build_home_curated_payload()
    assert {book["slug"] for book in snapshot["shelves"]["approved_audiobooks"]} == APPROVED_AUDIO_SLUGS


def test_shelf_collage_is_dynamic_canonical_and_deduplicated():
    payload = build_home_curated_payload()
    collage = payload["shelf_collage"]

    assert [group["id"] for group in collage["groups"]] == [
        "bengali-life-and-legacy",
        "gothic-and-the-uncanny",
        "love-society-and-human-nature",
        "adventure-nature-and-wonder",
        "short-masterpieces",
    ]
    assert [group["layout_area"] for group in collage["groups"]] == [
        "bengali",
        "gothic",
        "love",
        "adventure",
        "short",
    ]
    assert [group["accent"] for group in collage["groups"]] == [
        "bengali",
        "gothic",
        "love",
        "adventure",
        "short",
    ]
    assert {
        book["slug"] for book in collage["selected_audiobooks"]
    } == {
        book["slug"]
        for book in payload["shelves"]["approved_audiobooks"]
        if book["cover_valid"] is True
    }
    visible_slugs = [
        book["slug"]
        for group in collage["groups"]
        for book in group["books"]
    ]
    assert len(visible_slugs) == len(set(visible_slugs))
    assert all(book["reader_enabled"] is True for group in collage["groups"] for book in group["books"])
    assert all(
        book["cover_alt_text"] == f"{book['title']} by {book['author']}"
        for group in collage["groups"]
        for book in group["books"]
    )
    assert all(
        book["cover_valid"] is True
        and book["is_placeholder"] is False
        and book["is_typographic_only"] is False
        and book["canonical_cover_match"] is True
        for group in collage["groups"]
        for book in group["books"]
    )


def test_shelf_collage_rejects_metadata_marked_placeholder_covers():
    books = [{
        "slug": "placeholder",
        "reader_enabled": True,
        "front_cover_url": "https://cdn.example.com/placeholder.png",
        "cover_valid": False,
        "is_placeholder": True,
    }, {
        "slug": "canonical",
        "reader_enabled": True,
        "front_cover_url": "https://cdn.example.com/canonical.png",
        "cover_valid": True,
    }]

    assert [book["slug"] for book in select_curated_books(books, 2)] == ["canonical"]


def test_shelf_collage_rejects_checked_in_runtime_graphical_fallbacks():
    payload = build_home_curated_payload()
    visible_slugs = {
        book["slug"]
        for group in payload["shelf_collage"]["groups"]
        for book in group["books"]
    }
    assert "book-2b9853ec52" not in visible_slugs
    assert any(
        item["slug"] == "book-2b9853ec52"
        and "cover truth" in item["reason"]
        for item in home_curation_evidence()["omitted"]
    )


def test_shelf_collage_contains_no_customer_facing_governance_copy():
    collage = build_home_curated_payload()["shelf_collage"]
    payload_text = json.dumps({
        "eyebrow": collage["eyebrow"],
        "title": collage["title"],
        "description": collage["description"],
        "groups": [
            {
                "title": group["title"],
                "description": group["description"],
                "cta_label": group["cta_label"],
            }
            for group in collage["groups"]
        ],
    }, ensure_ascii=False).lower()
    assert "release gate" not in payload_text
    assert "qa_passed" not in payload_text
    assert "unapproved audio" not in payload_text
    assert "manifest" not in payload_text
