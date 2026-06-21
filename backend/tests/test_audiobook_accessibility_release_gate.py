from __future__ import annotations

from scripts.audiobook_accessibility_release_gate import (
    FAIL_PUBLIC_AUDIO_LEAK,
    PASS_EXPECTED_BLOCKED,
    PUBLIC_AUDIO_RELEASE_BLOCKED,
    QA_THRESHOLD,
    READY_FOR_INTERNAL_AUDIOBOOK_REVIEW,
    evaluate_release_gate,
)


def base_payload(**overrides):
    payload = {
        "public_audio_enabled": False,
        "public_listen_now_cta": False,
        "public_audiobook_metadata": False,
        "public_audio_url_exposed": False,
        "public_audio_asset_count": 0,
        "public_audio_asset_paths": [],
        "public_build_audio_asset_count": 0,
        "public_build_audio_asset_paths": [],
        "unsupported_accessibility_claim_found": False,
        "source_text_approved": True,
        "derivative_audiobook_rights_approved": True,
        "model_commercial_use_permission": "commercial use permitted by local license review",
        "model_license_evidence": "license reviewed and stored",
        "voice_narrator_rights": "synthetic voice/provider rights reviewed",
        "real_person_voice_cloning_risk_resolved": True,
        "transcript_required": True,
        "transcript_present": True,
        "text_audio_sync_tolerance_ms": 200,
        "player_accessibility_evidence": {
            "player_controls_accessible_names": True,
            "playback_controls_keyboard_reachable": True,
            "screen_reader_announcements_clear": True,
            "chapter_navigation_nonvisual": True,
            "current_chapter_announced": True,
            "playback_speed_control_accessible": True,
            "rewind_forward_controls_accessible": True,
            "resume_position_accessible": True,
            "bookmarks_accessible": True,
            "transcript_accessible": True,
            "low_network_error_states_accessible": True,
            "mobile_assistive_technology_checked": True,
        },
        "bengali_qa_score": QA_THRESHOLD,
        "english_qa_score": QA_THRESHOLD,
        "owner_approval_status": "approved",
        "rollback_plan": "Disable audio routes and remove public metadata.",
        "dracula_audio_disabled": True,
        "kshudhita_pipeline_only": True,
        "first_batch_audio_rights_blocked": True,
        "audio_readiness_report_status": "PASS_WITH_WARNINGS",
    }
    payload.update(overrides)
    return payload


def blocker_codes(result):
    return {blocker["code"] for blocker in result["blockers"]}


def test_complete_internal_evidence_reaches_internal_review_but_never_public_publish():
    result = evaluate_release_gate(base_payload())

    assert result["status"] == READY_FOR_INTERNAL_AUDIOBOOK_REVIEW
    assert result["public_audio_publish_allowed"] is False
    assert result["command_status"] == PASS_EXPECTED_BLOCKED
    assert result["blocker_count"] == 0


def test_public_audio_enabled_blocks_and_marks_public_leak():
    result = evaluate_release_gate(base_payload(public_audio_enabled=True))

    assert result["status"] == PUBLIC_AUDIO_RELEASE_BLOCKED
    assert result["command_status"] == FAIL_PUBLIC_AUDIO_LEAK
    assert "PUBLIC_AUDIO_ENABLED" in blocker_codes(result)


def test_public_listen_now_cta_blocks():
    result = evaluate_release_gate(base_payload(public_listen_now_cta=True))

    assert result["status"] == PUBLIC_AUDIO_RELEASE_BLOCKED
    assert result["command_status"] == FAIL_PUBLIC_AUDIO_LEAK
    assert "PUBLIC_LISTEN_NOW_CTA" in blocker_codes(result)


def test_public_audioobject_metadata_and_audio_url_block():
    result = evaluate_release_gate(base_payload(public_audiobook_metadata=True, public_audio_url_exposed=True))

    assert result["command_status"] == FAIL_PUBLIC_AUDIO_LEAK
    assert "PUBLIC_AUDIOBOOK_METADATA" in blocker_codes(result)
    assert "PUBLIC_AUDIO_URL_EXPOSED" in blocker_codes(result)


def test_unsupported_accessibility_claim_blocks():
    result = evaluate_release_gate(base_payload(unsupported_accessibility_claim_found=True))

    assert result["command_status"] == FAIL_PUBLIC_AUDIO_LEAK
    assert "UNSUPPORTED_ACCESSIBILITY_CLAIM" in blocker_codes(result)


def test_gate_cannot_pass_without_derivative_audiobook_rights():
    result = evaluate_release_gate(base_payload(derivative_audiobook_rights_approved=False))

    assert result["status"] == PUBLIC_AUDIO_RELEASE_BLOCKED
    assert "DERIVATIVE_AUDIOBOOK_RIGHTS_MISSING" in blocker_codes(result)


def test_gate_cannot_pass_without_commercial_model_license_evidence():
    result = evaluate_release_gate(base_payload(model_commercial_use_permission="", model_license_evidence=""))

    assert result["status"] == PUBLIC_AUDIO_RELEASE_BLOCKED
    assert "MODEL_COMMERCIAL_USE_PERMISSION_MISSING" in blocker_codes(result)
    assert "MODEL_LICENSE_EVIDENCE_MISSING" in blocker_codes(result)


def test_gate_cannot_pass_without_voice_rights_and_clone_risk_resolution():
    result = evaluate_release_gate(base_payload(voice_narrator_rights="", real_person_voice_cloning_risk_resolved=False))

    assert "VOICE_NARRATOR_RIGHTS_MISSING" in blocker_codes(result)
    assert "VOICE_CLONING_RISK_UNRESOLVED" in blocker_codes(result)


def test_gate_cannot_pass_without_transcript_and_sync_evidence():
    result = evaluate_release_gate(base_payload(transcript_present=False, text_audio_sync_tolerance_ms=None))

    assert "TRANSCRIPT_REQUIRED_MISSING" in blocker_codes(result)
    assert "SYNC_TOLERANCE_MISSING" in blocker_codes(result)


def test_sync_tolerance_above_threshold_blocks():
    result = evaluate_release_gate(base_payload(text_audio_sync_tolerance_ms=400))

    assert "SYNC_TOLERANCE_TOO_HIGH" in blocker_codes(result)


def test_gate_cannot_pass_without_player_accessibility_evidence():
    evidence = base_payload()["player_accessibility_evidence"]
    evidence["screen_reader_announcements_clear"] = False
    evidence["playback_controls_keyboard_reachable"] = False

    result = evaluate_release_gate(base_payload(player_accessibility_evidence=evidence))

    assert "SCREEN_READER_ANNOUNCEMENTS_CLEAR_MISSING" in blocker_codes(result)
    assert "PLAYBACK_CONTROLS_KEYBOARD_REACHABLE_MISSING" in blocker_codes(result)


def test_bengali_and_english_scores_must_meet_threshold():
    result = evaluate_release_gate(base_payload(bengali_qa_score=9.4, english_qa_score=9.1))

    assert "BENGALI_QA_SCORE_BELOW_THRESHOLD" in blocker_codes(result)
    assert "ENGLISH_QA_SCORE_BELOW_THRESHOLD" in blocker_codes(result)


def test_owner_approval_and_rollback_plan_are_required():
    result = evaluate_release_gate(base_payload(owner_approval_status="", rollback_plan=""))

    assert "OWNER_APPROVAL_MISSING" in blocker_codes(result)
    assert "ROLLBACK_PLAN_MISSING" in blocker_codes(result)


def test_frontend_public_audio_assets_are_direct_public_leak():
    result = evaluate_release_gate(base_payload(public_audio_asset_count=3))

    assert result["status"] == PUBLIC_AUDIO_RELEASE_BLOCKED
    assert result["command_status"] == FAIL_PUBLIC_AUDIO_LEAK
    assert "FRONTEND_PUBLIC_AUDIO_ASSETS_PRESENT" in blocker_codes(result)


def test_frontend_build_audio_assets_are_direct_public_leak():
    result = evaluate_release_gate(base_payload(public_build_audio_asset_count=2))

    assert result["status"] == PUBLIC_AUDIO_RELEASE_BLOCKED
    assert result["command_status"] == FAIL_PUBLIC_AUDIO_LEAK
    assert "FRONTEND_BUILD_AUDIO_ASSETS_PRESENT" in blocker_codes(result)
