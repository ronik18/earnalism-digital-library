from backend.home_curation_v4 import build_home_curated_payload_v4, select_visible_books, shelf_ids_for_book


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
