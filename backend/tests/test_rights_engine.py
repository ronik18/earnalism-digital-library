from __future__ import annotations

from backend.rights_engine import evaluate_rights, rights_publish_blockers, rights_report_csv, rights_report_rows


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

