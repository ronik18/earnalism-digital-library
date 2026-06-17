from __future__ import annotations

import importlib
import os
import asyncio

import pytest

from backend.rights_engine import evaluate_rights, rights_publish_blockers, rights_report_csv, rights_report_rows


def server_module():
    os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
    os.environ.setdefault("JWT_SECRET", "test-secret")
    return importlib.import_module("backend.server")


def approved_book(**overrides):
    rights_metadata = {
        "work_title": "Pride and Prejudice",
        "work_slug": "pride-and-prejudice",
        "author_name": "Jane Austen",
        "author_death_year": 1817,
        "original_publication_year": 1813,
        "country_of_origin": "United Kingdom",
        "source_url": "https://www.gutenberg.org/ebooks/1342",
        "source_name": "Project Gutenberg",
        "source_license": "Public domain",
        "translator_name": "",
        "translator_death_year": "",
        "illustrator_name": "",
        "illustrator_death_year": "",
        "editor_name": "",
        "edition_publication_year": 1813,
        "rights_tier": "A",
        "verification_status": "approved",
        "blocked_reason": "",
        "publication_region": "global",
        "verified_at": "2026-06-17T00:00:00+00:00",
    }
    rights_metadata.update(overrides.pop("rights_metadata", {}))
    return {
        "slug": "pride-and-prejudice",
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "is_published": True,
        "rights_metadata": rights_metadata,
        **overrides,
    }


def test_tier_a_public_domain_book_is_approved():
    decision = evaluate_rights(approved_book(), current_year=2026)

    assert decision.approved is True
    assert decision.rights_tier == "A"
    assert rights_publish_blockers(approved_book(), current_year=2026) == []


def test_missing_author_death_year_quarantines_and_blocks_publish():
    book = approved_book(rights_metadata={"author_death_year": ""})

    decision = evaluate_rights(book, current_year=2026)

    assert decision.status == "quarantine"
    assert "author_death_year is required." in decision.issues
    assert rights_publish_blockers(book, current_year=2026)


def test_missing_source_url_quarantines_and_blocks_publish():
    book = approved_book(rights_metadata={"source_url": ""})

    decision = evaluate_rights(book, current_year=2026)

    assert decision.status == "quarantine"
    assert "source_url is required." in decision.issues


def test_missing_source_license_quarantines_and_blocks_publish():
    book = approved_book(rights_metadata={"source_license": ""})

    decision = evaluate_rights(book, current_year=2026)

    assert decision.status == "quarantine"
    assert "source_license is required." in decision.issues


def test_missing_verified_at_blocks_approved_status():
    book = approved_book(rights_metadata={"verified_at": ""})

    decision = evaluate_rights(book, current_year=2026)

    assert decision.status == "quarantine"
    assert "verified_at is required for approved rights metadata." in decision.issues


def test_unsafe_license_blocks_publish():
    book = approved_book(rights_metadata={"source_license": "All rights reserved"})

    decision = evaluate_rights(book, current_year=2026)

    assert decision.status == "blocked"
    assert "source_license is restricted, unclear, or unsafe." in decision.issues


def test_modern_translation_blocks_publish_until_verified():
    book = approved_book(rights_metadata={"translator_name": "Modern Translator", "translator_death_year": ""})

    decision = evaluate_rights(book, current_year=2026)

    assert decision.status == "blocked"
    assert any("translation rights" in issue for issue in decision.issues)


def test_modern_illustration_blocks_publish_until_verified():
    book = approved_book(rights_metadata={"illustrator_name": "Modern Illustrator", "illustrator_death_year": 2000})

    decision = evaluate_rights(book, current_year=2026)

    assert decision.status == "blocked"
    assert any("illustration rights" in issue for issue in decision.issues)


def test_unknown_illustrator_blocks_publish_until_verified():
    book = approved_book(rights_metadata={"illustrator_name": "Unknown Illustrator", "illustrator_death_year": ""})

    decision = evaluate_rights(book, current_year=2026)

    assert decision.status == "blocked"
    assert any("illustration rights" in issue for issue in decision.issues)


def test_editor_or_modern_edition_uncertainty_blocks_or_quarantines():
    unknown_edition = approved_book(rights_metadata={"editor_name": "Unknown Editor", "edition_publication_year": ""})
    modern_edition = approved_book(rights_metadata={"editor_name": "Modern Editor", "edition_publication_year": 2020})

    unknown_decision = evaluate_rights(unknown_edition, current_year=2026)
    modern_decision = evaluate_rights(modern_edition, current_year=2026)

    assert unknown_decision.status == "quarantine"
    assert any("edition_publication_year" in issue for issue in unknown_decision.issues)
    assert modern_decision.status == "blocked"
    assert any("edition/editorial rights" in issue for issue in modern_decision.issues)


def test_tier_c_blocks_all_publishing():
    book = approved_book(rights_metadata={"rights_tier": "C", "blocked_reason": "source license unclear"})

    decision = evaluate_rights(book, current_year=2026)

    assert decision.status == "blocked"
    assert "Tier C rights block all publishing." in decision.issues


def test_tier_b_blocks_global_but_allows_india_region_gate():
    global_book = approved_book(rights_metadata={"rights_tier": "B", "publication_region": "global"})
    india_book = approved_book(rights_metadata={"rights_tier": "B", "publication_region": "india"})

    assert evaluate_rights(global_book, current_year=2026).status == "blocked"
    assert evaluate_rights(india_book, current_year=2026).approved is True


def test_tier_b_india_only_still_requires_other_evidence():
    india_book = approved_book(rights_metadata={"rights_tier": "B", "publication_region": "india", "source_url": ""})

    decision = evaluate_rights(india_book, current_year=2026)

    assert decision.status == "quarantine"
    assert "source_url is required." in decision.issues


def test_published_book_cannot_publish_without_approved_rights_metadata():
    book = {"slug": "unsafe", "title": "Unsafe", "author": "Unknown", "is_published": True}

    blockers = rights_publish_blockers(book, current_year=2026)

    assert blockers
    assert "author_death_year is required." in blockers
    assert "source_url is required." in blockers


def test_unpublished_draft_may_hold_assets_but_is_not_publicly_publishable():
    draft = {
        "slug": "draft",
        "title": "Draft",
        "author": "Unknown",
        "is_published": False,
        "cover_image_url": "https://cdn.example.test/cover.jpg",
        "audiobook": {"url": "https://cdn.example.test/audio.mp3"},
    }

    decision = evaluate_rights(draft, current_year=2026)

    assert decision.status == "quarantine"
    assert rights_publish_blockers(draft, current_year=2026)


def test_reports_split_approved_quarantine_and_blocked_rows():
    books = [
        approved_book(slug="approved"),
        approved_book(slug="quarantine", rights_metadata={"author_death_year": ""}),
        approved_book(slug="blocked", rights_metadata={"rights_tier": "C"}),
    ]

    approved_rows = rights_report_rows(books, "approved")
    quarantine_rows = rights_report_rows(books, "quarantine")
    blocked_rows = rights_report_rows(books, "blocked")

    assert [row["decision_status"] for row in approved_rows] == ["approved"]
    assert [row["decision_status"] for row in quarantine_rows] == ["quarantine"]
    assert [row["decision_status"] for row in blocked_rows] == ["blocked"]
    csv_text = rights_report_csv(quarantine_rows)
    assert "author_death_year is required" in csv_text
    assert "work_title" in csv_text


class FakeBookCursor:
    def __init__(self, books):
        self.books = books

    def sort(self, *_args, **_kwargs):
        return self

    async def to_list(self, _limit):
        return self.books


class FakeBooksCollection:
    def __init__(self, books):
        self.books = books

    def find(self, *_args, **_kwargs):
        return FakeBookCursor(self.books)


class FakeDb:
    def __init__(self, books):
        self.books = FakeBooksCollection(books)


def test_admin_rights_report_valid_filename_returns_csv(monkeypatch):
    server = server_module()
    monkeypatch.setattr(server, "db", FakeDb([approved_book()]))

    response = asyncio.run(server.admin_rights_report("rights_approved_report.csv"))

    assert response.media_type == "text/csv"
    body = response.body.decode("utf-8")
    assert "decision_status" in body
    assert "decision_issues" in body
    assert "approved" in body


def test_admin_rights_report_invalid_filename_returns_404():
    server = server_module()

    with pytest.raises(server.HTTPException) as exc:
        asyncio.run(server.admin_rights_report("not-a-real-report.csv"))

    assert exc.value.status_code == 404


def test_admin_rights_report_endpoint_requires_admin_auth():
    server = server_module()
    matching = [
        route
        for route in server.app.routes
        if getattr(route, "path", "") == "/api/admin/rights/reports/{filename}"
    ]

    assert matching
    assert any(
        dependency.call is server.require_admin
        for route in matching
        for dependency in route.dependant.dependencies
    )


def test_publishing_create_and_update_paths_call_publish_gate():
    server = server_module()
    book = approved_book(rights_metadata={"source_license": ""})

    with pytest.raises(server.HTTPException) as create_exc:
        server._assert_publishable(book)

    assert create_exc.value.status_code == 400
    assert "Rights verification" in str(create_exc.value.detail)


def test_runtime_source_and_asset_mutations_block_published_unsafe_books():
    server = server_module()
    unsafe_book = approved_book(rights_metadata={"rights_tier": "C"})

    for asset_label in ["Source text", "Visual asset", "Audiobook"]:
        with pytest.raises(server.HTTPException) as exc:
            server._assert_public_rights_approved(unsafe_book, asset_label)
        assert exc.value.status_code == 400
        assert asset_label in exc.value.detail["message"]
        assert any("Rights verification" in issue for issue in exc.value.detail["issues"])


def test_runtime_source_and_asset_mutations_allow_drafts_to_hold_assets():
    server = server_module()
    unsafe_draft = approved_book(is_published=False, rights_metadata={"rights_tier": "C"})

    assert server._assert_public_rights_approved(unsafe_draft, "Audiobook") is None


def test_server_routes_keep_all_required_rights_enforcement_calls():
    source = open("backend/server.py", encoding="utf-8").read()

    expected_calls = [
        "admin_create_book(payload: BookIn",
        "doc[\"rights_metadata\"] = rights_metadata",
        "_assert_publishable(doc)",
        "admin_update_book(slug: str, payload: BookIn",
        "_assert_publishable(candidate)",
        "admin_add_chapter(slug: str, payload: ChapterIn",
        "_assert_public_rights_approved(book, \"Source text\")",
        "admin_update_chapter(slug: str, cid: str, payload: ChapterIn",
        "admin_upload_chapter_file(",
        "admin_upload_cover(",
        "_assert_public_rights_approved(book, \"Visual asset\")",
        "admin_update_book_audiobook(",
        "_assert_public_rights_approved(existing, \"Audiobook\")",
        "admin_rights_report(filename: str, _=Depends(require_admin))",
    ]

    for expected in expected_calls:
        assert expected in source
