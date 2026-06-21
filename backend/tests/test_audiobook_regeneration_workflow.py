from __future__ import annotations

import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from backend.audiobook_generation.provider_adapter import DryRunNarrationProvider, GenerationRequest
from scripts import audiobook_regeneration_workflow as workflow


def load_context():
    return workflow.load_context("kshudhita-pashan")


def context_with_request(**overrides):
    context = load_context()
    request = json.loads(json.dumps(context.request))
    request.update(overrides)
    return workflow.WorkflowContext(
        request=request,
        profile=context.profile,
        source_metadata=context.source_metadata,
        book_slug=context.book_slug,
    )


def approve_all(request: dict) -> dict:
    updated = json.loads(json.dumps(request))
    for approval in updated["approvals"].values():
        approval["approved"] = True
    updated["rights_status"] = "RIGHTS_APPROVED"
    updated["source_text_status"] = "SOURCE_TEXT_APPROVED"
    return updated


def test_regeneration_precheck_fails_without_owner_approval():
    context = load_context()
    issues = workflow.safety_issues(context)

    assert "owner approval is missing." in issues


def test_regeneration_precheck_fails_without_rights_approval():
    context = context_with_request()
    request = approve_all(context.request)
    request["approvals"]["rights"]["approved"] = False
    context = workflow.WorkflowContext(request, context.profile, context.source_metadata, context.book_slug)
    issues = workflow.safety_issues(context)

    assert "rights approval is missing." in issues


def test_regeneration_precheck_fails_without_source_text_approval():
    context = context_with_request()
    request = approve_all(context.request)
    request["approvals"]["source_text"]["approved"] = False
    context = workflow.WorkflowContext(request, context.profile, context.source_metadata, context.book_slug)
    issues = workflow.safety_issues(context)

    assert "source_text approval is missing." in issues


def test_regeneration_precheck_fails_without_voice_profile_approval():
    context = context_with_request()
    request = approve_all(context.request)
    request["approvals"]["voice_style"]["approved"] = False
    context = workflow.WorkflowContext(request, context.profile, context.source_metadata, context.book_slug)
    issues = workflow.safety_issues(context)

    assert "voice_style approval is missing." in issues


def test_dry_run_plan_succeeds_with_draft_data_and_generates_no_audio():
    context = load_context()
    plan = workflow.build_plan(context)

    assert plan["workflow_status"] == "APPROVAL_REQUIRED"
    assert plan["generation_performed"] is False
    assert plan["upload_performed"] is False
    assert plan["provider_call_performed"] is False
    assert plan["audio_urls_included"] is False
    assert plan["segments_planned"] == 0
    assert plan["source_text_status"] == "OPERATOR_REQUIRED"
    assert any("Approved full source text is unavailable" in issue for issue in plan["issues"])
    assert plan["approval_evidence"]["governance_request_checksum"]
    assert plan["approval_evidence"]["source_metadata_checksum"]
    assert plan["approval_evidence"]["release_gate_checksum"]


def test_approve_dry_run_mode_is_internal_only():
    context = load_context()
    plan = workflow.build_plan(context, simulate_dry_run_approvals=True)

    assert plan["workflow_status"] == "APPROVAL_REQUIRED"
    assert plan["public_release_allowed"] is False
    assert plan["full_audiobook_allowed"] is False
    assert plan["preview_allowed"] is False
    assert plan["provider_result"]["audio_generated"] is False


def test_segment_manifest_contains_no_audio_urls():
    context = load_context()
    manifest = {
        "segments": workflow.build_segments(context),
        "audio_urls_included": False,
    }
    serialized = json.dumps(manifest, ensure_ascii=False).lower()

    assert "http://" not in serialized
    assert "https://" not in serialized
    assert manifest["audio_urls_included"] is False
    assert manifest["segments"] == []


def test_provider_adapter_performs_no_network_calls(monkeypatch):
    def fail_network(*_args, **_kwargs):
        raise AssertionError("network call attempted")

    monkeypatch.setattr(socket, "create_connection", fail_network)
    provider = DryRunNarrationProvider()
    result = provider.generate_segment(
        GenerationRequest(
            book_slug="kshudhita-pashan",
            segment_id="segment-001",
            text_ref="source:kshudhita",
            language="bn",
            narrator_profile_id="bengali-gothic-literary-female-sample",
            voice_source_type="STYLE_PROFILE",
            consent_status="NOT_APPLICABLE_STYLE_PROFILE",
            dry_run=True,
        )
    )

    assert result.network_calls_performed == 0
    assert result.audio_generated is False
    assert result.publishable is False


def test_unauthorized_voice_clone_profile_is_rejected():
    provider = DryRunNarrationProvider()
    issues = provider.validate_voice_profile(
        {
            "display_name": "Celebrity clone",
            "voice_source_type": "REAL_PERSON_CLONE",
            "consent_status": "CONSENT_REQUIRED",
            "allowed_for_generation": True,
            "owner_approved": True,
        }
    )

    assert any("voice likeness" in issue.lower() or "celebrity" in issue.lower() for issue in issues)


def test_workflow_cli_writes_manifest_without_generation(tmp_path: Path):
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/audiobook_regeneration_workflow.py",
            "--book-slug",
            "kshudhita-pashan",
            "--mode",
            "generate-manifest",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "generate-manifest complete" in completed.stdout
    manifest_path = Path("output/audiobook_regeneration/kshudhita-pashan/segment_manifest.json")
    assert manifest_path.exists()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["audio_urls_included"] is False
    assert payload["source_text_status"] == "OPERATOR_REQUIRED"
    assert payload["segments"] == []
    validation = json.loads(Path("output/audiobook_regeneration/kshudhita-pashan/segment_manifest_validation.json").read_text())
    assert validation["status"] == "PASS"


def test_precheck_cli_exits_nonzero_until_approvals_exist():
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/audiobook_regeneration_workflow.py",
            "--book-slug",
            "kshudhita-pashan",
            "--mode",
            "precheck",
        ],
        text=True,
        capture_output=True,
    )

    assert completed.returncode != 0
    assert "blocked" in completed.stderr.lower()


def test_missing_source_metadata_blocks(monkeypatch):
    context = load_context()
    context = workflow.WorkflowContext(context.request, context.profile, {}, context.book_slug)
    issues = workflow.safety_issues(context, simulate_dry_run_approvals=True)

    assert "Source metadata is missing." in issues
