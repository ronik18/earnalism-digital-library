from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from backend.daily_growth_loop import (
    GrowthBudgets,
    GrowthMetrics,
    daily_growth_report_csv,
    daily_growth_report_json,
    daily_growth_report_markdown,
    run_daily_growth_loop,
)
from scripts.daily_growth_loop import write_reports


def ready_book(slug="dracula", title="Dracula", **overrides):
    book = {
        "slug": slug,
        "title": title,
        "category_slug": "gothic-fiction",
        "language": "en",
        "page_views": 1000,
        "reading_starts": 300,
        "reading_completions": 80,
        "audiobook_enabled": True,
        "rights_metadata": {
            "rights_tier": "A",
            "verification_status": "approved",
            "blocked_reason": "",
            "publication_region": "global",
        },
        "demand": {"demand_score": 90, "action_status": "READY_FOR_GENERATION"},
        "ingestion_status": "CLEANED",
        "edition_generation_status": "QA_PASSED",
        "visual_status": "QA_PASSED",
        "audio_status": "QA_PASSED",
        "qa": {"qa_status": "QA_PASSED", "warnings": []},
        "cost": {"used": 0, "budget": 100},
    }
    book.update(overrides)
    return book


def payload(**overrides):
    data = {
        "report_date": "2026-06-18",
        "metrics": {
            "paid_readers": 30,
            "reading_starts": 200,
            "reading_completions": 60,
            "preview_listens": 40,
            "referrals": 12,
            "conversion_rate": 0.08,
            "school_institution_leads": 4,
        },
        "budgets": {
            "max_daily_llm_budget": 10,
            "max_daily_audio_budget": 3,
            "max_books_per_day": 2,
            "max_publish_actions_per_day": 0,
        },
        "books": [
            ready_book(),
            ready_book(slug="frankenstein", title="Frankenstein", page_views=800),
            ready_book(slug="unsafe", title="Unsafe", rights_metadata={"rights_tier": "C", "verification_status": "approved"}),
        ],
    }
    data.update(overrides)
    return data


def test_growth_metrics_and_budgets_parse_defaults():
    metrics = GrowthMetrics.from_dict({"paid_readers": "7", "conversion_rate": "0.125"})
    budgets = GrowthBudgets.from_dict({})

    assert metrics.paid_readers == 7
    assert metrics.conversion_rate == 0.125
    assert budgets.max_books_per_day == 3
    assert budgets.max_publish_actions_per_day == 0


def test_daily_job_runs_without_provider_credentials_and_generates_report():
    report = run_daily_growth_loop(payload())
    data = daily_growth_report_json(report)

    assert data["dry_run"] is True
    assert data["public_publishing_enabled"] is False
    assert data["publish_actions_planned"] == 0
    assert data["metrics"]["paid_readers"] == 30
    assert data["top_books"]


def test_budget_caps_limit_queued_tasks():
    report = run_daily_growth_loop(
        payload(
            budgets={
                "max_daily_llm_budget": 1,
                "max_daily_audio_budget": 0,
                "max_books_per_day": 2,
                "max_publish_actions_per_day": 0,
            }
        )
    )

    assert report.budget_usage["llm_used"] <= 1
    assert report.budget_usage["audio_used"] <= 0
    assert any("budget cap" in item["reason"].lower() for item in report.blocked_items)


def test_max_books_per_day_limits_selection():
    report = run_daily_growth_loop(payload(budgets={"max_daily_llm_budget": 10, "max_daily_audio_budget": 5, "max_books_per_day": 1}))

    assert len(report.selected_books) == 1


def test_rights_and_workflow_blocks_prevent_task_queueing():
    report = run_daily_growth_loop(
        payload(
            books=[
                ready_book(slug="blocked-rights", title="Blocked Rights", rights_metadata={"rights_tier": "C"}),
                ready_book(slug="qa-missing", title="QA Missing", qa={"qa_status": "QA_PENDING", "warnings": []}),
            ]
        )
    )

    assert report.queued_tasks == []
    assert len(report.blocked_items) == 2
    assert all(item["blockers"] for item in report.blocked_items)


def test_drafts_are_private_and_metadata_only():
    report = run_daily_growth_loop(payload())

    assert report.seo_social_email_drafts
    assert report.reading_challenge_drafts
    assert all(draft.public is False for draft in report.seo_social_email_drafts)
    assert all("body_preview" in draft.as_dict() for draft in report.seo_social_email_drafts)


def test_reports_include_daily_summary(tmp_path: Path):
    report = run_daily_growth_loop(payload())
    json_path, csv_path, md_path = write_reports(report, tmp_path)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    csv_text = csv_path.read_text(encoding="utf-8")
    markdown = md_path.read_text(encoding="utf-8")

    assert data["workflow_version"]
    assert "queued_task_count" in csv_text
    assert "Daily Growth Automation Dry-Run Report" in markdown


def test_report_helpers_are_deterministic_shapes():
    report = run_daily_growth_loop(payload())

    assert "budget_usage" in daily_growth_report_json(report)
    assert "priority_rank" in daily_growth_report_csv(report)
    assert "Queued Tasks" in daily_growth_report_markdown(report)


def test_cli_sample_writes_reports(tmp_path: Path):
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/daily_growth_loop.py",
            "--sample",
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "Daily growth dry-run complete" in completed.stdout
    assert (tmp_path / "daily_growth_report.json").exists()
    assert (tmp_path / "daily_growth_report.csv").exists()
    assert (tmp_path / "daily_growth_report.md").exists()


def test_cli_rejects_publish_options(tmp_path: Path):
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/daily_growth_loop.py",
            "--sample",
            "--publish",
            "--output-dir",
            str(tmp_path),
        ],
        text=True,
        capture_output=True,
    )

    assert completed.returncode != 0
    assert "dry-run only" in completed.stderr
