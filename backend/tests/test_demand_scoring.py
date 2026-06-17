from __future__ import annotations

from pathlib import Path

from backend.demand_scoring import (
    LAUNCH_PRIORITY_SEEDS,
    demand_report_csv,
    demand_report_markdown,
    rank_demand,
    score_book,
    seed_books,
)
from scripts.demand_priority import write_reports


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
    markdown = demand_report_markdown(scores)

    assert "demand_score" in csv_text
    assert "priority_rank" in csv_text
    assert "growth_rationale" in csv_text
    assert "recommended_product_format" in csv_text
    assert "No LLM, TTS, image, or paid API calls are used." in markdown


def test_write_reports_is_dry_run_and_creates_expected_files(tmp_path: Path):
    csv_path, md_path, count = write_reports(seed_books(), tmp_path)

    assert count == 10
    assert csv_path.name == "demand_priority_report.csv"
    assert md_path.name == "demand_priority_report.md"
    assert "Demand Priority Report" in md_path.read_text(encoding="utf-8")
    assert "demand_score" in csv_path.read_text(encoding="utf-8")
