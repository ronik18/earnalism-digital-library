from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

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

    assert data["status"] == "DRY_RUN_READY"
    assert data["dry_run"] is True
    assert data["public_publishing_enabled"] is False
    assert data["publish_actions_planned"] == 0
    assert data["metrics"]["paid_readers"] == 30
    assert data["top_books"]


def test_non_dry_run_payload_blocks_all_tasks_and_drafts():
    report = run_daily_growth_loop(payload(dry_run=False))
    data = daily_growth_report_json(report)

    assert data["status"] == "BLOCKED_NON_DRY_RUN"
    assert data["dry_run"] is True
    assert data["queued_tasks"] == []
    assert data["seo_social_email_drafts"] == []
    assert data["reading_challenge_drafts"] == []
    assert data["public_publishing_enabled"] is False
    assert data["publish_actions_planned"] == 0
    assert "Phase 9 daily growth automation is dry-run only." in data["blocked_items"][0]["reason"]


def test_emergency_pause_blocks_all_tasks_and_drafts():
    report = run_daily_growth_loop(payload(emergency_pause=True))
    data = daily_growth_report_json(report)

    assert data["status"] == "BLOCKED_EMERGENCY_PAUSE"
    assert data["queued_tasks"] == []
    assert data["seo_social_email_drafts"] == []
    assert data["reading_challenge_drafts"] == []
    assert data["public_publishing_enabled"] is False
    assert data["publish_actions_planned"] == 0
    assert "Emergency pause enabled" in data["blocked_items"][0]["reason"]


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


@pytest.mark.parametrize(
    ("book_overrides", "expected_blocker"),
    [
        ({"rights_metadata": {"rights_tier": "C", "verification_status": "approved"}}, "BLOCKED_RIGHTS"),
        (
            {"rights_metadata": {"rights_tier": "B", "verification_status": "approved", "publication_region": "india"}},
            "REGION_GATED_REVIEW",
        ),
        ({"demand": {"action_status": "READY_FOR_RIGHTS_REVIEW"}}, "BLOCKED_PRIORITY_GATE"),
        ({"ingestion_status": "PENDING"}, "BLOCKED_INGESTION"),
        ({"edition_generation_status": "FAILED_QA"}, "BLOCKED_EDITION_GATE"),
        ({"visual_status": "FAILED_QA"}, "BLOCKED_VISUAL_GATE"),
        ({"audio_status": "FAILED_QA"}, "BLOCKED_AUDIO_GATE"),
        ({"qa": {"qa_status": "QA_PENDING", "warnings": []}}, "QA pass is required"),
        ({"cost": {"used": 101, "budget": 100}}, "BLOCKED_COST"),
        ({"publishing_workflow": {"paused": True}}, "PAUSED"),
    ],
)
def test_upstream_phase_gates_prevent_task_queueing(book_overrides, expected_blocker):
    report = run_daily_growth_loop(
        payload(
            books=[
                ready_book(
                    slug="blocked-book",
                    title="Blocked Book",
                    page_views=5000,
                    **book_overrides,
                )
            ]
        )
    )

    assert report.queued_tasks == []
    assert report.seo_social_email_drafts == []
    assert report.reading_challenge_drafts == []
    assert report.blocked_items
    blockers = " ".join(report.blocked_items[0].get("blockers", []))
    combined = f"{report.blocked_items[0].get('publish_readiness', '')} {blockers}"
    assert expected_blocker in combined


def test_audio_not_required_is_allowed_by_phase7_gate():
    report = run_daily_growth_loop(payload(books=[ready_book(audio_status="AUDIO_NOT_REQUIRED")]))

    assert report.queued_tasks
    assert not any("BLOCKED_AUDIO_GATE" in " ".join(item.get("blockers", [])) for item in report.blocked_items)


def test_publish_action_cap_never_enables_public_publishing():
    report = run_daily_growth_loop(
        payload(
            budgets={
                "max_daily_llm_budget": 10,
                "max_daily_audio_budget": 3,
                "max_books_per_day": 1,
                "max_publish_actions_per_day": 5,
            }
        )
    )
    data = daily_growth_report_json(report)

    assert data["public_publishing_enabled"] is False
    assert data["publish_actions_planned"] == 0
    assert data["budget_usage"]["publish_actions_used"] == 0
    assert any("Public publishing is disabled in Phase 9" in item["reason"] for item in data["blocked_items"])


def test_drafts_are_private_and_metadata_only():
    report = run_daily_growth_loop(payload())

    assert report.seo_social_email_drafts
    assert report.reading_challenge_drafts
    assert all(draft.public is False for draft in report.seo_social_email_drafts)
    for draft in report.seo_social_email_drafts:
        row = draft.as_dict()
        assert "body_preview" in row
        assert row["public"] is False
        assert "recipient" not in row
        assert "recipients" not in row
        assert "send_at" not in row
        assert "provider" not in row
        assert "api_identifier" not in row


def test_queued_tasks_are_metadata_only_candidates():
    report = run_daily_growth_loop(payload())
    task_types = {task.task_type for task in report.queued_tasks}

    assert "source_ingestion_candidate" in task_types
    assert "edition_generation_candidate" in task_types
    assert "visual_design_candidate" in task_types
    assert "publishing_workflow_candidate" in task_types
    assert all(task.dry_run is True for task in report.queued_tasks)


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
