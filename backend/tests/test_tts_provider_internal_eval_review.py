from __future__ import annotations

from pathlib import Path

from scripts import tts_provider_internal_eval_review as provider_review


def complete_provider(**overrides):
    provider = {
        "provider_id": "test-provider",
        "display_name": "Test Provider",
        "provider_strategy_status": "REVIEW_ONLY",
        "official_terms_url": "https://example.com/terms",
        "commercial_use_evidence_url": "https://example.com/commercial",
        "voice_license_evidence_url": "https://example.com/voice",
        "paid_plan_required": True,
        "plan_evidence_status": "APPROVED",
        "paid_plan_evidence_url": "https://example.com/paid-plan",
        "beta_feature_allowed": False,
        "beta_features_allowed": False,
        "beta_features_excluded_evidence": "APPROVED",
        "standalone_audio_distribution_allowed": "ALLOWED",
        "standalone_audio_distribution_evidence": "APPROVED",
        "attribution_required": False,
        "selected_voice_attribution_requirement": "APPROVED",
        "selected_voice_restrictions": "APPROVED",
        "commercial_internal_eval_permission": "APPROVED",
        "provider_terms_review_status": "APPROVED",
        "data_retention_review_status": "APPROVED",
        "data_retention_notes": "Reviewed for test.",
        "voice_rights_status": "APPROVED",
        "selected_voice_id": "test-voice",
        "selected_voice_display_name": "Test Voice",
        "selected_voice_type": "platform_voice",
        "selected_voice_license_evidence_url": "https://example.com/voice-license",
        "selected_voice_rights_summary": "Approved provider platform voice for test internal evaluation.",
        "internal_eval_status": "ELIGIBLE_INTERNAL_EVAL",
        "production_status": "PRODUCTION_BLOCKED",
        "owner_approval_status": "APPROVED",
        "legal_review_status": "APPROVED",
        "blockers": "No blocker for internal eval test fixture.",
    }
    provider.update(overrides)
    return provider


def test_provider_without_commercial_standalone_evidence_is_hold():
    decision = provider_review.classify_provider(
        complete_provider(standalone_audio_distribution_allowed="HOLD_REVIEW")
    )

    assert decision.internal_eval_status == "HOLD_PROVIDER_REVIEW"
    assert any("standalone audio distribution evidence" in issue for issue in decision.issues)
    assert decision.public_production_status == "PRODUCTION_BLOCKED"


def test_beta_features_are_blocked():
    decision = provider_review.classify_provider(complete_provider(beta_feature_allowed=True))

    assert decision.internal_eval_status == "BLOCKED"
    assert any("beta features are blocked" in issue for issue in decision.issues)
    assert decision.public_production_status == "PRODUCTION_BLOCKED"


def test_beta_features_alias_is_blocked():
    decision = provider_review.classify_provider(complete_provider(beta_features_allowed=True))

    assert decision.internal_eval_status == "BLOCKED"
    assert any("beta features are blocked" in issue for issue in decision.issues)


def test_missing_selected_voice_is_hold():
    decision = provider_review.classify_provider(
        complete_provider(
            selected_voice_id="OWNER_SELECTION_REQUIRED",
            selected_voice_type="unknown",
            selected_voice_license_evidence_url="OWNER_SELECTION_REQUIRED",
        )
    )

    assert decision.internal_eval_status == "HOLD_PROVIDER_REVIEW"
    assert any("selected provider voice is not selected" in issue for issue in decision.issues)
    assert any("selected provider voice license evidence is missing" in issue for issue in decision.issues)


def test_cloned_voice_blocks_without_explicit_rights_evidence():
    decision = provider_review.classify_provider(
        complete_provider(
            selected_voice_type="cloned_voice",
            voice_rights_status="HOLD_REVIEW",
            selected_voice_rights_summary="Requires review.",
        )
    )

    assert decision.internal_eval_status == "HOLD_PROVIDER_REVIEW"
    assert any("cloned voice requires explicit voice-rights" in issue for issue in decision.issues)


def test_missing_paid_plan_or_commercial_evidence_is_hold():
    decision = provider_review.classify_provider(
        complete_provider(
            plan_evidence_status="HOLD_REVIEW",
            paid_plan_evidence_url="",
            commercial_internal_eval_permission="HOLD_REVIEW",
            standalone_audio_distribution_evidence="HOLD_REVIEW",
        )
    )

    assert decision.internal_eval_status == "HOLD_PROVIDER_REVIEW"
    assert any("paid plan evidence status" in issue for issue in decision.issues)
    assert any("commercial internal-eval permission" in issue for issue in decision.issues)
    assert any("standalone audio distribution evidence" in issue for issue in decision.issues)


def test_missing_owner_or_legal_review_is_hold():
    decision = provider_review.classify_provider(
        complete_provider(
            owner_approval_status="OWNER_REVIEW_REQUIRED",
            legal_review_status="LEGAL_REVIEW_REQUIRED",
        )
    )

    assert decision.internal_eval_status == "HOLD_PROVIDER_REVIEW"
    assert any("owner approval is required" in issue for issue in decision.issues)
    assert any("legal/internal review is required" in issue for issue in decision.issues)
    assert decision.public_production_status == "PRODUCTION_BLOCKED"


def test_complete_provider_can_only_be_internal_eval_not_production():
    decision = provider_review.classify_provider(complete_provider())

    assert decision.internal_eval_status == "ELIGIBLE_INTERNAL_EVAL"
    assert decision.internal_generation_status == "ELIGIBLE_INTERNAL_EVAL_ONLY"
    assert decision.public_production_status == "PRODUCTION_BLOCKED"


def test_repo_provider_config_has_no_eligible_or_production_approved_candidates():
    decisions = provider_review.review_provider_candidates()

    assert decisions
    assert all(decision.public_production_status == "PRODUCTION_BLOCKED" for decision in decisions)
    assert sum(1 for decision in decisions if decision.internal_eval_status == "ELIGIBLE_INTERNAL_EVAL") == 0
    elevenlabs = provider_review.selected_provider_decision("elevenlabs", decisions)
    assert elevenlabs.internal_eval_status == "HOLD_PROVIDER_REVIEW"
    assert elevenlabs.public_production_status == "PRODUCTION_BLOCKED"
    assert elevenlabs.provider["selected_voice_id"] == "21m00Tcm4TlvDq8ikWAM"
    assert elevenlabs.provider["selected_voice_type"] == "platform_voice"
    assert any("owner approval" in issue for issue in elevenlabs.issues)


def test_write_reports_emits_scoped_provider_packet(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(provider_review, "PROVIDER_REVIEW_REPORT_PATH", tmp_path / "TTS_PROVIDER_INTERNAL_EVAL_REVIEW.md")
    monkeypatch.setattr(provider_review, "PROVIDER_SCORECARD_PATH", tmp_path / "TTS_PROVIDER_COMMERCIAL_RIGHTS_SCORECARD.md")
    monkeypatch.setattr(
        provider_review,
        "ELEVENLABS_REVIEW_FORM_PATH",
        tmp_path / "ELEVENLABS_PROVIDER_OWNER_LEGAL_REVIEW_FORM.md",
    )
    monkeypatch.setattr(
        provider_review,
        "ELEVENLABS_CHECKLIST_PATH",
        tmp_path / "ELEVENLABS_PROVIDER_INTERNAL_EVAL_CHECKLIST.md",
    )
    decisions = [provider_review.classify_provider(complete_provider(provider_id="elevenlabs", display_name="ElevenLabs"))]

    paths = provider_review.write_reports(decisions, output_dir=tmp_path / "frankenstein")
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths.values())

    assert (tmp_path / "frankenstein" / "TTS_PROVIDER_INTERNAL_EVAL_REVIEW.md").exists()
    assert (tmp_path / "frankenstein" / "TTS_PROVIDER_COMMERCIAL_RIGHTS_SCORECARD.md").exists()
    assert (tmp_path / "frankenstein" / "ELEVENLABS_PROVIDER_OWNER_LEGAL_REVIEW_FORM.md").exists()
    assert (tmp_path / "frankenstein" / "ELEVENLABS_PROVIDER_INTERNAL_EVAL_CHECKLIST.md").exists()
    assert "Public audio status: `PUBLIC_AUDIO_RELEASE_BLOCKED`" in combined
    assert "Listen Now" not in combined
    assert "AudioObject" not in combined
