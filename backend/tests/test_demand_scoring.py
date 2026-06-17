from __future__ import annotations

from pathlib import Path

from backend.demand_scoring import (
    LAUNCH_PRIORITY_SEEDS,
    demand_report_csv,
    demand_report_json,
    demand_report_markdown,
    rank_demand,
    score_book,
    seed_books,
)
from scripts.demand_priority import load_books, write_reports


def test_launch_priority_seed_list_is_complete():
    assert LAUNCH_PRIORITY_SEEDS == [
        "Anandamath",
        "Devdas",
        "Abol Tabol",
        "Sultana's Dream",
        "Sherlock Holmes",
        "Dracula",
        "Frankenstein",
        "Tagore Short Stories",
        "Calculus Made Easy",
        "Chander Pahar",
    ]


def test_rights_risk_lowers_score():
    safe = {
        "title": "Dracula",
        "slug": "dracula",
        "category_slug": "gothic-fiction",
        "language": "en",
        "rights_metadata": {"rights_tier": "A", "verification_status": "approved", "source_url": "https://example.test"},
    }
    risky = {
        **safe,
        "slug": "dracula-risky",
        "rights_metadata": {"rights_tier": "C", "verification_status": "blocked", "blocked_reason": "unsafe"},
    }

    assert score_book(safe).demand_score > score_book(risky).demand_score
    assert "rights risk" in score_book(risky).growth_rationale
    assert score_book(risky).action_status == "BLOCKED_RIGHTS"


def test_production_complexity_lowers_score():
    simple = {
        "title": "Calculus Made Easy",
        "slug": "calculus-made-easy",
        "category_slug": "study-material",
        "language": "en",
        "word_count": 20_000,
        "rights_metadata": {"rights_tier": "A", "verification_status": "approved", "source_url": "https://example.test"},
    }
    complex_book = {**simple, "slug": "calculus-complex", "word_count": 180_000, "chapter_count": 80}

    assert score_book(simple).demand_score > score_book(complex_book).demand_score


def test_rank_demand_assigns_priority_rank_and_top_ten_visible():
    scores = rank_demand(seed_books())

    assert len(scores) == 10
    assert [score.priority_rank for score in scores] == list(range(1, 11))
    markdown = demand_report_markdown(scores)
    assert "## Top Recommendations" in markdown
    assert markdown.count("| ") >= 11


def test_reports_include_required_output_columns_and_formats():
    scores = rank_demand(seed_books())
    csv_text = demand_report_csv(scores)
    json_rows = demand_report_json(scores)
    markdown = demand_report_markdown(scores)

    assert "demand_score" in csv_text
    assert "priority_rank" in csv_text
    assert "action_status" in csv_text
    assert "blocking_reason" in csv_text
    assert "growth_rationale" in csv_text
    assert "recommended_product_format" in csv_text
    assert json_rows[0]["action_status"]
    assert "No LLM, TTS, image, or paid API calls are used." in markdown


def test_write_reports_is_dry_run_and_creates_expected_files(tmp_path: Path):
    csv_path, md_path, json_path, count = write_reports(seed_books(), tmp_path)

    assert count == 10
    assert csv_path.name == "demand_priority_report.csv"
    assert md_path.name == "demand_priority_report.md"
    assert json_path.name == "demand_priority_report.json"
    assert "Demand Priority Report" in md_path.read_text(encoding="utf-8")
    assert "demand_score" in csv_path.read_text(encoding="utf-8")
    assert "action_status" in json_path.read_text(encoding="utf-8")


def test_unknown_rights_requires_rights_review_not_generation():
    score = score_book({"title": "Unknown Rights", "slug": "unknown-rights", "category_slug": "literary-fiction"})

    assert score.action_status == "READY_FOR_RIGHTS_REVIEW"
    assert "Rights metadata is missing" in score.blocking_reason


def test_tier_c_produces_blocked_rights():
    score = score_book({
        "title": "Unsafe",
        "slug": "unsafe",
        "rights_metadata": {"rights_tier": "C", "verification_status": "blocked"},
    })

    assert score.action_status == "BLOCKED_RIGHTS"
    assert score.blocking_reason


def test_tier_b_approved_produces_region_gated_priority():
    score = score_book({
        "title": "Anandamath",
        "slug": "anandamath",
        "language": "ben",
        "rights_metadata": {"rights_tier": "B", "verification_status": "approved", "publication_region": "india"},
    })

    assert score.action_status == "REGION_GATED_PRIORITY"


def test_tier_a_approved_produces_ready_for_generation():
    score = score_book({
        "title": "Dracula",
        "slug": "dracula",
        "category_slug": "gothic-fiction",
        "language": "en",
        "rights_metadata": {"rights_tier": "A", "verification_status": "approved", "source_url": "https://example.test"},
    })

    assert score.action_status == "READY_FOR_GENERATION"


def test_load_books_accepts_direct_books_array(tmp_path: Path):
    payload = tmp_path / "books.json"
    payload.write_text('[{"title":"Dracula","slug":"dracula"}]', encoding="utf-8")

    assert load_books(payload)[0]["slug"] == "dracula"


def test_load_books_accepts_object_with_books_array(tmp_path: Path):
    payload = tmp_path / "books-object.json"
    payload.write_text('{"books":[{"title":"Frankenstein","slug":"frankenstein"}]}', encoding="utf-8")

    assert load_books(payload)[0]["title"] == "Frankenstein"


def test_load_books_accepts_catalog_style_rows(tmp_path: Path):
    payload = tmp_path / "catalog.json"
    payload.write_text(
        '{"rows":[{"path":"/book/dracula","title":"Dracula","content_type":"book_page","rights_metadata_present":"unknown"}]}',
        encoding="utf-8",
    )

    book = load_books(payload)[0]
    score = score_book(book)

    assert book["slug"] == "book-dracula"
    assert score.action_status == "READY_FOR_RIGHTS_REVIEW"
