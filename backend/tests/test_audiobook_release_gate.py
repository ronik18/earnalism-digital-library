from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from backend import catalog_truth
from backend import server
from scripts import audiobook_release_gate as gate
from scripts import audiobook_regeneration_workflow as workflow


def load_context():
    return workflow.load_context("kshudhita-pashan")


def request_with_approvals(**overrides):
    context = load_context()
    request = json.loads(json.dumps(context.request))
    for approval in request["approvals"].values():
        approval["approved"] = True
    request.update(
        {
            "rights_status": "RIGHTS_APPROVED",
            "source_text_status": "SOURCE_TEXT_APPROVED",
            "public_release_allowed": True,
            "preview_allowed": True,
            "full_audiobook_allowed": False,
            "approval_status": "PUBLIC_PREVIEW_APPROVED",
        }
    )
    request.update(overrides)
    return request, context.profile


def approved_profile(profile: dict) -> dict:
    updated = json.loads(json.dumps(profile))
    updated["owner_approved"] = True
    updated["allowed_for_generation"] = True
    updated["allowed_for_public_release"] = True
    return updated


def test_public_release_gate_blocks_kshudhita_by_default():
    context = load_context()
    result = gate.evaluate_release_gate(context.request, context.profile)

    assert result.status == "BLOCKED_PUBLIC_AUDIO_RELEASE"
    assert result.public_release_allowed is False
    assert any("Public audio release is disabled" in item for item in result.blockers)


def test_full_audiobook_release_is_blocked_by_default():
    request, profile = request_with_approvals()
    profile = approved_profile(profile)
    result = gate.evaluate_release_gate(request, profile, qa_score=9.7)

    assert result.status == "BLOCKED_PUBLIC_AUDIO_RELEASE"
    assert any("Full audiobook release is disabled by default" in item for item in result.blockers)


def test_public_preview_blocked_until_qa_score_9_2():
    request, profile = request_with_approvals()
    profile = approved_profile(profile)
    result = gate.evaluate_release_gate(request, profile, qa_score=9.1)

    assert result.status == "BLOCKED_PUBLIC_AUDIO_RELEASE"
    assert any("Public preview requires human QA score >= 9.2" in item for item in result.blockers)


def test_full_audiobook_blocked_until_qa_score_9_5():
    request, profile = request_with_approvals(
        full_audiobook_allowed=True,
        approval_status="FULL_AUDIOBOOK_APPROVED",
    )
    profile = approved_profile(profile)
    result = gate.evaluate_release_gate(request, profile, qa_score=9.4)

    assert result.status == "BLOCKED_PUBLIC_AUDIO_RELEASE"
    assert any("Full audiobook requires human QA score >= 9.5" in item for item in result.blockers)


def test_unauthorized_voice_clone_profile_is_blocked():
    request, profile = request_with_approvals()
    profile = approved_profile(profile)
    profile["voice_source_type"] = "REAL_PERSON_CLONE"
    result = gate.evaluate_release_gate(request, profile, qa_score=9.6)

    assert result.status == "BLOCKED_PUBLIC_AUDIO_RELEASE"
    assert any("Unauthorized voice clone" in item for item in result.blockers)


def test_no_ai_touch_claim_is_rejected_without_human_recorded_proof():
    issues = gate.claim_issues("This has No AI touch and is fully human narrated.")

    assert issues
    assert any("no ai touch" in issue.lower() or "fully human" in issue.lower() for issue in issues)


def test_kshudhita_has_no_public_listen_now_cta():
    issues = gate.frontend_cta_issues()

    assert issues == []


def test_dracula_audio_remains_disabled():
    artifact = catalog_truth.load_dracula_artifact_book(include_content=False)
    assert artifact is not None
    projection = catalog_truth.public_book_projection(artifact)

    assert projection["audio_enabled"] is False
    assert projection["audiobook_enabled"] is False
    assert projection["audio_url"] == ""


def test_sitemap_excludes_audiobook_routes():
    assert gate.sitemap_has_audio_entries() is False


def test_no_audio_url_appears_in_public_book_projection():
    issues = gate.public_projection_audio_issues()

    assert issues == []


def test_no_audio_route_for_kshudhita_returns_404(monkeypatch):
    async def none_cache(*_args, **_kwargs):
        return None

    class FakeBooks:
        async def find_one(self, *_args, **_kwargs):
            return {
                "slug": "kshudhita-pashan",
                "title": "Kshudhita Pashan",
                "is_published": True,
                "pipeline_stage": "PIPELINE_ONLY",
                "audiobook_enabled": True,
                "audiobook_assets": {"mp3": "https://cdn.example.com/kshudhita.mp3"},
            }

    monkeypatch.setattr(server, "db", SimpleNamespace(books=FakeBooks()))
    monkeypatch.setattr(server, "_redis_cache_get", none_cache)
    request = SimpleNamespace(headers={}, method="GET")

    with pytest.raises(server.HTTPException) as exc:
        asyncio.run(server._reader_book_audiobook_asset("kshudhita-pashan", "mp3", request))

    assert exc.value.status_code == 404


def test_release_gate_cli_writes_blocked_report():
    result = gate.main()
    report = gate.REPORT_PATH.read_text(encoding="utf-8")

    assert result == 0
    assert "BLOCKED_PUBLIC_AUDIO_RELEASE" in report
    assert "Kshudhita Pashan remains pipeline-only" in report
