from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from backend.automation_observability import (
    incident_report_csv,
    observability_logs_csv,
    observability_report_json,
    run_observability_guardrails,
)
from scripts.observability_guardrails import write_reports


def ready_action(**overrides):
    action = {
        "action_id": "ready-action",
        "slug": "dracula",
        "phase": "generation",
        "action_type": "edition_generation_candidate",
        "rights": {"rights_tier": "A", "verification_status": "approved", "blocked_reason": ""},
        "requires_source": True,
        "source_url": "https://example.invalid/dracula",
        "source_hash": "sha256:dracula",
        "estimated_cost": 1,
        "budget_remaining": 10,
        "budget_limit": 10,
        "budget_used": 0,
    }
    action.update(overrides)
    return action


def payload(**overrides):
    data = {
        "dry_run": True,
        "kill_switch_active": False,
        "actions": [ready_action()],
        "health": {
            "api": {"status": "OK"},
            "queue": {"status": "OK"},
            "storage": {"status": "OK"},
            "publishing": {"status": "OK"},
        },
    }
    data.update(overrides)
    return data


def test_ready_action_has_structured_audit_trail():
    report = run_observability_guardrails(payload())
    data = observability_report_json(report)

    assert data["status"] == "READY_DRY_RUN"
    assert data["summary"]["action_count"] == 1
    assert data["actions"][0]["decision_status"] == "ALLOWED_DRY_RUN"
    assert data["actions"][0]["audit_events"]
    assert data["logs"][0]["category"] == "generation"
    assert data["dry_run"] is True


def test_non_dry_run_payload_is_blocked():
    report = run_observability_guardrails(payload(dry_run=False))
    data = observability_report_json(report)

    assert data["status"] == "BLOCKED_NON_DRY_RUN"
    assert data["actions"] == []
    assert data["kill_switch_active"] is True
    assert data["incidents"][0]["severity"] == "CRITICAL"


def test_kill_switch_blocks_all_actions_and_opens_incidents():
    report = run_observability_guardrails(payload(kill_switch_active=True, actions=[ready_action(), ready_action(action_id="second")]))
    data = observability_report_json(report)

    assert data["status"] == "KILL_SWITCH_ACTIVE"
    assert all(action["decision_status"] == "BLOCKED" for action in data["actions"])
    assert any(log["guardrail_type"] == "kill_switch" for log in data["logs"])
    assert data["incidents"]


def test_rights_block_source_missing_and_budget_exceeded_block_action():
    action = ready_action(
        rights={"rights_tier": "C", "verification_status": "blocked", "blocked_reason": "unsafe"},
        source_url="",
        source_hash="",
        estimated_cost=12,
        budget_remaining=2,
    )
    report = run_observability_guardrails(payload(actions=[action]))
    data = observability_report_json(report)
    reasons = " ".join(data["actions"][0]["blocking_reasons"])

    assert data["actions"][0]["decision_status"] == "BLOCKED"
    assert "Rights blocked" in reasons
    assert "Source URL is missing" in reasons
    assert "Source hash is missing" in reasons
    assert "Estimated cost exceeds remaining budget" in reasons


def test_guardrail_logs_cover_required_guardrail_types():
    action = ready_action(
        hallucination_risk=True,
        child_facing=True,
        unsafe_child_facing_content=True,
        copyrighted_image_risk=True,
        audio_quality_score=8.5,
        audio_qa_status="FAILED_QA",
    )
    report = run_observability_guardrails(payload(actions=[action]))
    guardrails = {log.guardrail_type for log in report.logs if log.guardrail_type}

    assert "hallucination_risk" in guardrails
    assert "unsafe_child_facing_content" in guardrails
    assert "copyrighted_image_risk" in guardrails
    assert "low_quality_audio" in guardrails


def test_health_checks_report_api_queue_storage_and_publishing():
    report = run_observability_guardrails(
        payload(
            health={
                "api": {"status": "OK"},
                "queue": {"status": "DEGRADED", "message": "queue lag detected"},
                "storage": {"status": "DOWN", "message": "storage unavailable"},
                "publishing": {"status": "OK"},
            }
        )
    )
    data = observability_report_json(report)
    checks = {check["name"]: check["status"] for check in data["health_checks"]}

    assert checks == {"api": "OK", "queue": "DEGRADED", "storage": "DOWN", "publishing": "OK"}
    assert data["summary"]["unhealthy_check_count"] == 2
    assert any(incident["owner"] == "platform" for incident in data["incidents"])


def test_incident_report_contains_owner_status_and_rollback():
    report = run_observability_guardrails(payload(actions=[ready_action(estimated_cost=100, budget_remaining=1)]))
    csv_text = incident_report_csv(report)

    assert "owner" in csv_text
    assert "status" in csv_text
    assert "rollback_instruction" in csv_text
    assert "Keep action blocked" in csv_text


def test_structured_logs_csv_contains_guardrail_blocks():
    report = run_observability_guardrails(payload(actions=[ready_action(estimated_cost=100, budget_remaining=1)]))
    csv_text = observability_logs_csv(report)

    assert "guardrail_block" in csv_text
    assert "budget_exceeded" in csv_text


def test_cli_sample_writes_reports(tmp_path: Path):
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/observability_guardrails.py",
            "--sample",
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "Observability guardrails dry-run complete" in completed.stdout
    assert (tmp_path / "observability_guardrails_report.json").exists()
    assert (tmp_path / "structured_logs.csv").exists()
    assert (tmp_path / "incident_report.csv").exists()
    assert (tmp_path / "observability_guardrails_report.md").exists()


def test_cli_rejects_write_publish_options(tmp_path: Path):
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/observability_guardrails.py",
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


def test_write_reports_are_local_dry_run_artifacts(tmp_path: Path):
    report = run_observability_guardrails(payload(actions=[ready_action(estimated_cost=100, budget_remaining=1)]))
    json_path, logs_path, incidents_path, markdown_path = write_reports(report, tmp_path)
    data = json.loads(json_path.read_text(encoding="utf-8"))

    assert data["dry_run"] is True
    assert logs_path.read_text(encoding="utf-8")
    assert incidents_path.read_text(encoding="utf-8")
    assert "Observability Guardrails Dry-Run Report" in markdown_path.read_text(encoding="utf-8")
