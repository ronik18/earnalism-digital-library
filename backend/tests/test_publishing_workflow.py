from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from backend.publishing_workflow import (
    WorkflowSignals,
    WORKFLOW_STATES,
    build_admin_dashboard_sections,
    dry_run_publish,
    evaluate_workflow,
    workflow_report_json,
    workflow_signals_from_book,
)
from scripts.publishing_workflow import write_reports


ROOT = Path(__file__).resolve().parents[2]


def sample_book(**overrides):
    book = {
        "slug": "alice-in-wonderland",
        "title": "Alice's Adventures in Wonderland",
        "rights_metadata": {
            "rights_tier": "A",
            "verification_status": "approved",
            "blocked_reason": "",
            "publication_region": "global",
        },
        "demand": {"demand_score": 91.5, "action_status": "READY_FOR_GENERATION"},
        "ingestion_status": "CLEANED",
        "edition_generation_status": "QA_PASSED",
        "visual_status": "QA_PASSED",
        "audio_status": "QA_PASSED",
        "qa": {"qa_status": "QA_PASSED", "warnings": []},
        "cost": {"used": 12.5, "budget": 100.0},
        "is_published": False,
    }
    book.update(overrides)
    return book


def assert_blocked(book, expected_blocker):
    decision = evaluate_workflow(workflow_signals_from_book(book))

    assert decision.publish_readiness == "BLOCKED"
    assert any(expected_blocker in blocker for blocker in decision.blockers)
    return decision


def test_workflow_states_are_complete_and_ordered():
    assert WORKFLOW_STATES == [
        "DISCOVERED",
        "RIGHTS_PENDING",
        "RIGHTS_APPROVED",
        "DEMAND_SCORED",
        "INGESTED",
        "CLEANED",
        "EDITION_GENERATED",
        "VISUALS_GENERATED",
        "AUDIO_PREVIEW_GENERATED",
        "QA_PENDING",
        "QA_PASSED",
        "READY_FOR_PUBLICATION",
        "PUBLISHED",
        "PAUSED",
        "QUARANTINED",
        "ARCHIVED",
    ]


def test_ready_book_reaches_ready_for_publication():
    decision = evaluate_workflow(workflow_signals_from_book(sample_book()))

    assert decision.state == "READY_FOR_PUBLICATION"
    assert decision.publish_readiness == "READY"
    assert decision.blockers == []
    assert decision.rollback_available is True


def test_workflow_normalizes_lowercase_and_uppercase_status_inputs():
    base = {
        "slug": "dracula",
        "title": "Dracula",
        "rights_tier": "A",
        "blocked_reason": "",
        "publication_region": "global",
        "demand_score": 94.0,
        "action_status": "ready_for_generation",
        "ingestion_status": "cleaned",
        "edition_generation_status": "qa_passed",
        "visual_status": "qa_passed",
        "audio_status": "audio_not_required",
        "qa_status": "qa_passed",
        "cost_used": 0,
        "cost_budget": 100,
    }

    lower = evaluate_workflow(WorkflowSignals(**base, verification_status="approved"))
    upper = evaluate_workflow(WorkflowSignals(**base, verification_status="APPROVED"))

    assert lower.publish_readiness == "READY"
    assert upper.publish_readiness == "READY"
    assert lower.blockers == []
    assert upper.blockers == []


def test_cannot_publish_without_rights_approval():
    book = sample_book(rights_metadata={"rights_tier": "", "verification_status": ""})
    decision = evaluate_workflow(workflow_signals_from_book(book))

    assert decision.state == "RIGHTS_PENDING"
    assert decision.publish_readiness == "BLOCKED"
    assert "Rights approval is required." in decision.blockers


def test_missing_demand_status_blocks_priority_gate():
    book = sample_book(demand={"demand_score": 91.5, "action_status": ""})
    decision = assert_blocked(book, "BLOCKED_PRIORITY_GATE")

    assert decision.state == "DEMAND_SCORED"


def test_missing_ingestion_blocks_ingestion_gate():
    decision = assert_blocked(sample_book(ingestion_status=""), "BLOCKED_INGESTION")

    assert decision.state == "RIGHTS_APPROVED"


def test_missing_edition_blocks_edition_gate():
    decision = assert_blocked(sample_book(edition_generation_status="FAILED_QA"), "BLOCKED_EDITION_GATE")

    assert decision.state == "CLEANED"


def test_missing_visual_blocks_visual_gate():
    decision = assert_blocked(sample_book(visual_status="FAILED_QA"), "BLOCKED_VISUAL_GATE")

    assert decision.state == "EDITION_GENERATED"


def test_missing_audio_blocks_audio_gate_unless_audio_not_required():
    blocked = assert_blocked(sample_book(audio_status="FAILED_QA"), "BLOCKED_AUDIO_GATE")
    allowed = evaluate_workflow(workflow_signals_from_book(sample_book(audio_status="AUDIO_NOT_REQUIRED")))

    assert blocked.state == "VISUALS_GENERATED"
    assert allowed.state == "READY_FOR_PUBLICATION"
    assert allowed.publish_readiness == "READY"


def test_cannot_publish_without_qa_pass():
    book = sample_book(qa={"qa_status": "QA_PENDING", "warnings": ["audio pending"]})
    decision = evaluate_workflow(workflow_signals_from_book(book))

    assert decision.state == "QA_PENDING"
    assert "QA pass is required." in decision.blockers


def test_cannot_publish_if_cost_budget_exceeded():
    book = sample_book(cost={"used": 120, "budget": 100})
    decision = evaluate_workflow(workflow_signals_from_book(book))

    assert decision.state == "QA_PENDING"
    assert "BLOCKED_COST: Cost budget is exceeded." in decision.blockers


def test_tier_b_cannot_publish_globally():
    book = sample_book(rights_metadata={"rights_tier": "B", "verification_status": "approved", "publication_region": "global"})
    decision = evaluate_workflow(workflow_signals_from_book(book))

    assert decision.state == "RIGHTS_PENDING"
    assert decision.publish_readiness == "REGION_GATED_REVIEW"
    assert "REGION_GATED_REVIEW: Tier B is not eligible for normal global publication." in decision.blockers


def test_tier_c_cannot_publish_anywhere_and_quarantines():
    book = sample_book(rights_metadata={"rights_tier": "C", "verification_status": "approved", "publication_region": "india"})
    decision = evaluate_workflow(workflow_signals_from_book(book))

    assert decision.state == "QUARANTINED"
    assert "BLOCKED_RIGHTS: Tier C cannot publish anywhere." in decision.blockers


def test_admin_dashboard_sections_include_required_controls():
    signals = workflow_signals_from_book(sample_book())
    decision = evaluate_workflow(signals)
    sections = build_admin_dashboard_sections(signals, decision)
    names = {section["section"] for section in sections}

    assert {
        "rights status",
        "demand score",
        "ingestion status",
        "edition generation status",
        "visual status",
        "audio status",
        "QA warnings",
        "cost used",
        "publish readiness",
        "rollback button",
        "pause/kill switch",
    }.issubset(names)


def test_dry_run_publish_creates_private_drafts_only():
    plan = dry_run_publish(workflow_signals_from_book(sample_book()))

    assert plan.dry_run is True
    assert plan.public_exposure is False
    assert [draft["draft_type"] for draft in plan.created_drafts] == ["page", "seo_metadata", "reading_challenge"]
    assert all(draft["public"] is False for draft in plan.created_drafts)
    assert plan.rollback_plan
    assert plan.audit_log[0]["action"] == "DRY_RUN_PUBLISH_DRAFTS_CREATED"
    assert all(set(draft) == {"draft_type", "slug", "public"} for draft in plan.created_drafts)


def test_dry_run_publish_blocks_when_not_ready():
    book = sample_book(qa={"qa_status": "QA_PENDING", "warnings": []})
    plan = dry_run_publish(workflow_signals_from_book(book))

    assert plan.created_drafts == []
    assert plan.audit_log[0]["action"] == "DRY_RUN_PUBLISH_BLOCKED"
    assert "resolve blockers" in plan.rollback_plan[0]


def test_rollback_plan_is_metadata_only():
    plan = dry_run_publish(workflow_signals_from_book(sample_book()))

    assert plan.public_exposure is False
    assert plan.dry_run is True
    assert all(isinstance(step, str) for step in plan.rollback_plan)
    assert plan.audit_log[0]["dry_run"] is True


def test_report_outputs_include_state_sections_and_rollback(tmp_path: Path):
    report = workflow_report_json(sample_book())
    json_path, csv_path, md_path = write_reports(report, tmp_path)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    csv_text = csv_path.read_text(encoding="utf-8")
    markdown = md_path.read_text(encoding="utf-8")

    assert payload["state"] == "READY_FOR_PUBLICATION"
    assert payload["dry_run_publication"]["public_exposure"] is False
    assert "publish_readiness" in csv_text
    assert "Rollback Plan" in markdown


def test_cli_sample_writes_dry_run_reports(tmp_path: Path):
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/publishing_workflow.py",
            "--sample",
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "Publishing workflow dry-run complete" in completed.stdout
    assert (tmp_path / "publishing_workflow_report.json").exists()
    assert (tmp_path / "publishing_workflow_report.csv").exists()
    assert (tmp_path / "publishing_workflow_report.md").exists()


def test_cli_rejects_publish_options(tmp_path: Path):
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/publishing_workflow.py",
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


def test_admin_panel_is_read_only_and_prefers_report_data():
    panel = (ROOT / "frontend/src/components/Admin/PublishingWorkflowPanel.jsx").read_text(encoding="utf-8")

    assert "book.publishing_workflow_report || book.workflow_report" in panel
    assert "function workflowFromReport" in panel
    assert "read-only dry-run estimate" in panel
    assert 'type="button" disabled' in panel
    assert "onClick" not in panel
    assert "api." not in panel
