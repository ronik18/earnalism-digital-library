from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from backend.automation_observability import (
    incident_report_csv,
    observability_logs_csv,
    observability_report_json,
    run_observability_guardrails,
    structured_logs_json,
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
        "source_name": "Local public-domain fixture",
        "source_license": "public-domain",
        "source_hash": "sha256:dracula",
        "content_hash": "sha256:dracula-content",
        "provenance_hash": "sha256:dracula-provenance",
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
        source_name="",
        source_license="",
        source_hash="",
        content_hash="",
        provenance_hash="",
        estimated_cost=12,
        budget_remaining=2,
    )
    report = run_observability_guardrails(payload(actions=[action]))
    data = observability_report_json(report)
    reasons = " ".join(data["actions"][0]["blocking_reasons"])

    assert data["actions"][0]["decision_status"] == "BLOCKED"
    assert "Rights blocked" in reasons
    assert "source_url is missing" in reasons
    assert "source_name is missing" in reasons
    assert "source_license is missing" in reasons
    assert "source_hash is missing" in reasons
    assert "content_hash is missing" in reasons
    assert "provenance_hash is missing" in reasons
    assert "Estimated cost exceeds remaining budget" in reasons


@pytest.mark.parametrize(
    ("rights", "expected_status", "expected_message", "expected_severity"),
    [
        ({"rights_tier": "C", "verification_status": "approved"}, "BLOCKED", "Rights blocked", "CRITICAL"),
        ({"rights_tier": "", "verification_status": "approved"}, "BLOCKED", "Rights tier is missing", "HIGH"),
        ({"rights_tier": "A", "verification_status": ""}, "BLOCKED", "Rights approval is missing", "HIGH"),
        (
            {"rights_tier": "B", "verification_status": "approved", "publication_region": "global"},
            "BLOCKED",
            "Tier B rights require India-only",
            "HIGH",
        ),
        (
            {"rights_tier": "B", "verification_status": "approved", "publication_region": "IN"},
            "BLOCKED",
            "Tier B rights require region-gate acknowledgement",
            "HIGH",
        ),
    ],
)
def test_rights_guardrail_blocks_unsafe_rights_cases(rights, expected_status, expected_message, expected_severity):
    report = run_observability_guardrails(payload(actions=[ready_action(rights=rights)]))
    data = observability_report_json(report)
    reasons = " ".join(data["actions"][0]["blocking_reasons"])
    matching_logs = [log for log in data["logs"] if expected_message in log["message"]]

    assert data["actions"][0]["decision_status"] == expected_status
    assert expected_message in reasons
    assert matching_logs
    assert matching_logs[0]["severity"] == expected_severity


def test_tier_b_india_acknowledged_is_region_gated_but_not_blocked():
    report = run_observability_guardrails(
        payload(
            actions=[
                ready_action(
                    rights={
                        "rights_tier": "B",
                        "verification_status": "approved",
                        "publication_region": "IN",
                        "region_gate_acknowledged": True,
                    }
                )
            ]
        )
    )
    data = observability_report_json(report)

    assert data["actions"][0]["decision_status"] == "ALLOWED_DRY_RUN"
    assert data["actions"][0]["blocking_reasons"] == []
    assert any(log["guardrail_type"] == "region_gated" and log["status"] == "NOTED" for log in data["logs"])


@pytest.mark.parametrize(
    "missing_field",
    ["source_url", "source_name", "source_license", "source_hash", "content_hash", "provenance_hash"],
)
def test_source_traceability_requires_all_phase4_fields(missing_field):
    action = ready_action(**{missing_field: ""})
    report = run_observability_guardrails(payload(actions=[action]))
    data = observability_report_json(report)
    guardrails = {log["guardrail_type"] for log in data["logs"] if log["guardrail_type"]}

    assert data["actions"][0]["decision_status"] == "BLOCKED"
    assert missing_field in " ".join(data["actions"][0]["blocking_reasons"])
    assert {"source_missing", "traceability_missing"} & guardrails


@pytest.mark.parametrize(
    ("cost_fields", "expected_message"),
    [
        ({"estimated_cost": -1}, "estimated_cost cannot be negative"),
        ({"budget_remaining": -1}, "budget_remaining cannot be negative"),
        ({"budget_used": -1}, "budget_used cannot be negative"),
        ({"budget_limit": -1}, "budget_limit cannot be negative"),
        ({"estimated_cost": 5, "budget_remaining": None, "budget_limit": None}, "Positive estimated_cost requires"),
        ({"estimated_cost": 5, "budget_used": 7, "budget_limit": 10}, "Estimated cost would exceed budget limit"),
        ({"estimated_cost": 5, "budget_remaining": 4}, "Estimated cost exceeds remaining budget"),
    ],
)
def test_invalid_cost_metadata_blocks_action(cost_fields, expected_message):
    report = run_observability_guardrails(payload(actions=[ready_action(**cost_fields)]))
    data = observability_report_json(report)

    assert data["actions"][0]["decision_status"] == "BLOCKED"
    assert expected_message in " ".join(data["actions"][0]["blocking_reasons"])
    assert any(log["guardrail_type"] == "budget_exceeded" for log in data["logs"])


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


def test_feature_flag_disabled_blocks_all_actions():
    report = run_observability_guardrails(
        payload(feature_flags={"automation_enabled": False}, actions=[ready_action(), ready_action(action_id="second")])
    )
    data = observability_report_json(report)

    assert data["status"] == "FEATURE_FLAG_DISABLED"
    assert all(action["decision_status"] == "BLOCKED" for action in data["actions"])
    assert any(log["guardrail_type"] == "feature_flag_disabled" for log in data["logs"])
    assert data["incidents"]


@pytest.mark.parametrize(
    ("phase", "expected_category"),
    [
        ("public_content_governance", "publishing"),
        ("rights_verification", "rights_check"),
        ("demand_scoring", "demand_scoring"),
        ("source_ingestion", "ingestion"),
        ("edition_generation", "generation"),
        ("visual_generation", "generation"),
        ("audio_generation", "audio_generation"),
        ("publishing_workflow", "publishing"),
        ("daily_growth_loop", "demand_scoring"),
    ],
)
def test_phase1_to_phase9_action_categories_are_audited(phase, expected_category):
    report = run_observability_guardrails(payload(actions=[ready_action(phase=phase, action_type=f"{phase}_dry_run")]))
    data = observability_report_json(report)

    assert data["actions"][0]["audit_events"]
    assert data["actions"][0]["audit_events"][0]["category"] == expected_category
    assert data["actions"][0]["audit_events"][0]["dry_run"] is True


@pytest.mark.parametrize(
    "phase",
    [
        "public_content_governance",
        "rights_verification",
        "demand_scoring",
        "source_ingestion",
        "edition_generation",
        "visual_generation",
        "audio_generation",
        "publishing_workflow",
        "daily_growth_loop",
    ],
)
def test_phase1_to_phase9_actions_block_when_metadata_is_unsafe(phase):
    report = run_observability_guardrails(
        payload(actions=[ready_action(phase=phase, rights={"rights_tier": "C", "verification_status": "approved"})])
    )
    data = observability_report_json(report)

    assert data["actions"][0]["decision_status"] == "BLOCKED"
    assert any(log["guardrail_type"] == "rights_blocked" for log in data["logs"])


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
    assert (tmp_path / "structured_logs.json").exists()
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
    json_path, logs_json_path, logs_path, incidents_path, markdown_path = write_reports(report, tmp_path)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    logs_json = json.loads(logs_json_path.read_text(encoding="utf-8"))

    assert data["dry_run"] is True
    assert logs_json
    assert logs_path.read_text(encoding="utf-8")
    assert incidents_path.read_text(encoding="utf-8")
    assert "Observability Guardrails Dry-Run Report" in markdown_path.read_text(encoding="utf-8")


def test_report_completeness_and_no_outbound_delivery_metadata():
    report = run_observability_guardrails(payload(actions=[ready_action(estimated_cost=100, budget_remaining=1)]))
    data = observability_report_json(report)
    serialized = json.dumps(data, sort_keys=True)

    assert data["logs"]
    assert structured_logs_json(report)
    assert data["incidents"]
    assert data["health_checks"]
    assert data["summary"]["blocked_action_count"] == 1
    assert data["summary"]["guardrail_type_counts"]["budget_exceeded"] >= 1
    assert data["dry_run"] is True
    assert "recipient" not in serialized
    assert "provider_api_id" not in serialized
    assert "api_key" not in serialized
    assert "webhook_url" not in serialized
