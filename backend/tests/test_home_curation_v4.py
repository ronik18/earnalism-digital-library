from backend.home_curation_v4 import (
    build_home_curated_payload_v4,
    select_hero_carousel_books,
    select_visible_books,
    shelf_ids_for_book,
)


def book(slug, shelf_ids, *, pinned=False, rank=None, audio=False):
    return {
        "slug": slug,
        "title": slug.title(),
        "author": "Author",
        "reader_enabled": True,
        "language": "en",
        "is_published": True,
        "approved_to_publish": True,
        "rights_tier": "A",
        "verification_status": "approved",
        "qa_status": "QA_PASSED",
        "source_url": "https://example.com/source",
        "source_name": "Public domain source",
        "source_license": "Public domain",
        "source_hash": slug,
        "content_hash": slug,
        "provenance_hash": slug,
        "chapters": [{"id": "chapter-1", "is_preview": True}],
        "cover_image_url": f"https://cdn.example.com/{slug}.png",
        "cover_valid": True,
        "editorial_shelf_ids": shelf_ids,
        "admin_pinned": pinned,
        "home_shelf_rank": rank,
        "audiobook_enabled": audio,
        "audiobook": {"release_gate": "APPROVED", "qa_status": "QA_PASSED"} if audio else {},
        "audiobook_assets": {"mp3": f"https://cdn.example.com/{slug}.mp3"} if audio else {},
    }


def test_future_books_join_tagged_shelf_and_visible_count_is_bounded():
    payload = build_home_curated_payload_v4([
        book("gothic-old", ["gothic-and-the-uncanny"]),
        book("gothic-new", ["gothic-and-the-uncanny"], pinned=True, rank=1),
        book("gothic-other", ["gothic-and-the-uncanny"]),
        book("gothic-four", ["gothic-and-the-uncanny"]),
    ])
    shelf = next(item for item in payload["literary_shelves"] if item["id"] == "gothic-and-the-uncanny")
    assert shelf["total_count"] == 4
    assert len(shelf["visible_books"]) == 3
    assert shelf["visible_books"][0]["slug"] == "gothic-new"
    assert shelf["display_mode"] == "overflow"


def test_two_new_approved_audio_books_switch_to_bounded_audio_truth():
    books = [book("audio-one", ["short-masterpieces"], audio=True), book("audio-two", ["short-masterpieces"], audio=True)]
    audio_contracts = {item["slug"]: {"enabled": True, "url": f"/api/reader/book/{item['slug']}/audiobook", "release_gate": "APPROVED", "qa_status": "QA_PASSED"} for item in books}
    payload = build_home_curated_payload_v4(books, audio_contracts=audio_contracts)
    assert payload["audiobook_shelf"]["total_count"] == 2
    assert payload["audiobook_shelf"]["display_mode"] == "duo"


def test_revoked_audio_disappears_without_affecting_reader_shelf():
    books = [book("reader-only", ["short-masterpieces"], audio=True)]
    payload = build_home_curated_payload_v4(books, audio_contracts={"reader-only": {"enabled": False, "url": "", "release_gate": "", "qa_status": ""}})
    assert payload["audiobook_shelf"] is None
    assert payload["literary_shelves"][-1]["total_count"] == 1


def test_spotlight_and_zero_modes_are_explicit():
    one = build_home_curated_payload_v4([book("one", ["gothic-and-the-uncanny"])])
    assert next(item for item in one["literary_shelves"] if item["id"] == "gothic-and-the-uncanny")["display_mode"] == "spotlight"
    empty = build_home_curated_payload_v4([])
    assert all(item["display_mode"] == "zero" for item in empty["literary_shelves"])
    assert empty["audiobook_shelf"] is None


def test_explicit_shelf_membership_has_priority_over_sprint_id():
    candidate = book("sprint-two", ["love-society-and-human-nature"])
    candidate["sprint_id"] = "sprint-2"
    assert shelf_ids_for_book(candidate) == ["love-society-and-human-nature"]


def test_selection_does_not_duplicate_a_cover_when_an_alternative_exists():
    books = [book("a", ["short-masterpieces"]), book("b", ["short-masterpieces"])]
    selected = select_visible_books(books, 2)
    assert [item["slug"] for item in selected] == ["a", "b"]


def test_listening_rooms_exposes_bounded_items_and_reserves():
    books = [book(f"audio-{index}", ["short-masterpieces"], audio=True) for index in range(6)]
    contracts = {
        item["slug"]: {
            "enabled": True,
            "url": f"/api/reader/book/{item['slug']}/audiobook",
            "release_gate": "APPROVED",
            "qa_status": "QA_PASSED",
            "package_valid": True,
            "endpoint_valid": True,
        }
        for item in books
    }
    payload = build_home_curated_payload_v4(books, audio_contracts=contracts)
    assert payload["listening_rooms"]["total_approved"] == 6
    assert [item["slug"] for item in payload["listening_rooms"]["items"]] == [f"audio-{index}" for index in range(4)]
    assert [item["slug"] for item in payload["listening_rooms"]["reserve_items"]] == ["audio-4", "audio-5"]


def test_reader_only_and_invalid_audio_never_enter_listening_rooms():
    reader_only = book("reader-only", ["short-masterpieces"], audio=False)
    revoked = book("revoked", ["short-masterpieces"], audio=True)
    payload = build_home_curated_payload_v4(
        [reader_only, revoked],
        audio_contracts={"revoked": {"enabled": False, "url": "", "release_gate": "", "qa_status": ""}},
    )
    assert payload["listening_rooms"] is None
    assert payload["selected_audiobooks"] == []


def test_cover_candidates_are_ordered_and_safe():
    candidate = book("candidate", ["short-masterpieces"])
    candidate["cover_image_url"] = "https://cdn.example.com/primary.png"
    candidate["cover_candidates"] = [
        {"url": "https://cdn.example.com/alternate.png", "source": "canonical-alt"},
        {"url": "https://cdn.example.com/placeholder.png", "source": "placeholder"},
    ]
    payload = build_home_curated_payload_v4([candidate])
    visible = payload["literary_shelves"][-1]["visible_books"]
    assert visible[0]["front_cover_url"] == "https://cdn.example.com/primary.png"
    assert [item["url"] for item in visible[0]["cover_candidates"]] == [
        "https://cdn.example.com/primary.png",
        "https://cdn.example.com/alternate.png",
    ]
    assert "admin_pinned" not in visible[0]
    assert "sprint_id" not in visible[0]


def test_hero_carousel_exposes_only_sprint1_reader_covers_in_stable_order():
    books = [book(f"title-{index}", ["short-masterpieces"], rank=index) for index in range(10)]
    payload = build_home_curated_payload_v4(
        books,
        config={
            "sprint1_active_slugs": [
                "title-0",
                "title-2",
                "title-4",
                "title-6",
                "title-8",
            ]
        },
    )

    assert [item["slug"] for item in payload["hero"]["carousel_books"]] == [
        "title-0",
        "title-2",
        "title-4",
        "title-6",
        "title-8",
    ]
    assert payload["hero"]["featured_books"] == payload["hero"]["carousel_books"][:6]
    assert payload["source"]["hero_carousel_eligible_count"] == 5
    assert payload["source"]["catalog_version"] == "home-curated-v4-sprint1-hero"


def test_hero_carousel_builder_without_cohort_config_fails_closed():
    books = [book(f"title-{index}", ["short-masterpieces"], rank=index) for index in range(3)]
    payload = build_home_curated_payload_v4(books)

    assert payload["hero"]["carousel_books"] == []
    assert payload["source"]["hero_carousel_eligible_count"] == 0


def test_hero_carousel_fails_closed_for_invalid_or_editorially_blocked_records():
    valid = book("valid", ["short-masterpieces"])
    blocked = book("blocked", ["short-masterpieces"])
    blocked["do_not_feature"] = True
    unsafe = book("unsafe", ["short-masterpieces"])
    unsafe["front_cover_url"] = "file:///private/unsafe.png"
    unsafe["cover_image_url"] = "file:///private/unsafe.png"
    invalid_cover = book("invalid-cover", ["short-masterpieces"])
    invalid_cover["cover_valid"] = False
    duplicate = {**valid}

    contracts = [
        {
            "slug": item["slug"],
            "title": item["title"],
            "author": item["author"],
            "reader_enabled": item["reader_enabled"],
            "front_cover_url": item.get("front_cover_url") or item.get("cover_image_url"),
            "cover_valid": item["cover_valid"],
            "book_url": f"/book/{item['slug']}",
            "reader_url": f"/reader/{item['slug']}",
            "home_feature_eligible": item.get("home_feature_eligible", True),
            "do_not_feature": item.get("do_not_feature", False),
        }
        for item in (valid, duplicate, blocked, unsafe, invalid_cover)
    ]

    assert [item["slug"] for item in select_hero_carousel_books(contracts)] == ["valid"]


def test_hero_carousel_reuses_owner_reviewed_visual_cover_exclusions():
    placeholder = {
        "slug": "book-2b9853ec52",
        "title": "দুই বিঘা জমি",
        "author": "রবীন্দ্রনাথ ঠাকুর",
        "reader_enabled": True,
        "front_cover_url": "https://cdn.example.com/controlled-release-template.png",
        "cover_valid": True,
        "book_url": "/book/book-2b9853ec52",
        "reader_url": "/reader/book-2b9853ec52",
        "home_feature_eligible": True,
        "do_not_feature": False,
    }
    canonical = {
        **placeholder,
        "slug": "canonical",
        "title": "Canonical",
        "front_cover_url": "https://cdn.example.com/canonical.png",
        "book_url": "/book/canonical",
        "reader_url": "/reader/canonical",
    }

    assert [item["slug"] for item in select_hero_carousel_books([placeholder, canonical])] == ["canonical"]
