from __future__ import annotations

import json
from pathlib import Path

from scripts.tts_model_license_review import (
    BLOCKED,
    ELIGIBLE_INTERNAL_EVAL,
    HOLD_OWNER_REVIEW,
    HOLD_LICENSE_REVIEW,
    HOLD_VOICE_RIGHTS,
    classify_candidate,
    decision_payload,
    review_candidates,
    write_reports,
)


def complete_candidate(**overrides):
    candidate = {
        "candidate_id": "test-model",
        "display_name": "Test Model",
        "upstream_url": "https://example.com/model",
        "model_card_url": "https://example.com/model-card",
        "license_name": "Apache-2.0",
        "license_url": "https://www.apache.org/licenses/LICENSE-2.0",
        "code_license": "Apache-2.0",
        "weights_license": "Apache-2.0",
        "voice_license": "OWNER_APPROVED_SYNTHETIC_VOICE",
        "dataset_license_notes": "Dataset reviewed for commercial internal evaluation.",
        "commercial_use_status": "ALLOWED",
        "attribution_required": False,
        "languages_supported": "en",
        "english_suitability": "HIGH_INTERNAL_EVAL",
        "bengali_suitability": "LOW",
        "voice_cloning_risk": "LOW",
        "real_person_voice_risk": "LOW",
        "local_inference_possible": True,
        "network_required": False,
        "paid_provider_required": False,
        "production_candidate_status": ELIGIBLE_INTERNAL_EVAL,
        "evidence_last_reviewed_date": "2026-06-22",
        "evidence_notes": "Complete evidence for internal evaluation only.",
        "owner_approval_status": "APPROVED",
        "voice_rights_evidence_url": "https://example.com/voice-rights",
        "voice_rights_summary": "Synthetic voice rights reviewed for internal evaluation.",
        "speaker_identity_status": "SYNTHETIC_OR_LICENSED",
        "synthetic_voice_status": "APPROVED_SYNTHETIC_INTERNAL_EVAL",
        "real_person_voice_clone_risk": "LOW",
        "internal_eval_allowed": True,
        "internal_eval_blockers": "no blockers",
        "owner_internal_eval_approval_status": "APPROVED",
        "legal_internal_eval_review_status": "APPROVED",
        "internal_eval_status": ELIGIBLE_INTERNAL_EVAL,
        "selected_voice_id": "test_voice",
        "selected_voice_display_name": "Test Voice",
        "selected_voice_source_url": "https://example.com/voices",
        "selected_voice_license_evidence_url": "https://example.com/voice-license",
        "selected_voice_rights_summary": "Selected voice has owner/legal-reviewed synthetic voice rights.",
        "selected_voice_synthetic_status": "APPROVED_SYNTHETIC_INTERNAL_EVAL",
        "selected_voice_real_person_risk": "LOW",
        "selected_voice_attribution_requirement": "MODEL_ATTRIBUTION_REQUIRED",
        "selected_voice_internal_eval_status": ELIGIBLE_INTERNAL_EVAL,
        "owner_selected_voice_approval_status": "APPROVED",
        "legal_selected_voice_review_status": "APPROVED",
        "selected_voice_blockers": "no blockers",
    }
    candidate.update(overrides)
    return candidate


def test_missing_license_blocks_model_eligibility():
    decision = classify_candidate(complete_candidate(license_name="", license_url=""))

    assert decision.decision_status == HOLD_LICENSE_REVIEW
    assert any("license_name" in issue for issue in decision.issues)
    assert any("license_url" in issue for issue in decision.issues)


def test_missing_weights_license_blocks_model_eligibility():
    decision = classify_candidate(complete_candidate(weights_license=""))

    assert decision.decision_status == HOLD_LICENSE_REVIEW
    assert any("weights license evidence is missing" in issue for issue in decision.issues)


def test_missing_voice_rights_blocks_production_eligibility():
    decision = classify_candidate(complete_candidate(voice_license=""))

    assert decision.decision_status == HOLD_VOICE_RIGHTS
    assert decision.public_production_status == "PRODUCTION_BLOCKED"
    assert any("voice rights evidence is missing" in issue for issue in decision.issues)


def test_gpl_commercial_risk_candidate_is_hold_without_owner_approval():
    decision = classify_candidate(
        complete_candidate(
            candidate_id="piper",
            display_name="Piper",
            license_name="GPL-3.0-or-later",
            code_license="GPL-3.0-or-later",
            owner_approval_status="OWNER_APPROVAL_REQUIRED",
        )
    )

    assert decision.decision_status == HOLD_LICENSE_REVIEW
    assert any("GPL/commercial-risk candidate lacks owner/legal approval" in issue for issue in decision.issues)
    assert decision.public_production_status == "PRODUCTION_BLOCKED"


def test_unknown_commercial_use_status_blocks_generation():
    decision = classify_candidate(complete_candidate(commercial_use_status="UNKNOWN"))

    assert decision.decision_status == HOLD_LICENSE_REVIEW
    assert any("commercial-use evidence is not approved" in issue for issue in decision.issues)


def test_repo_candidate_report_has_no_production_approved_model(tmp_path: Path):
    decisions = review_candidates()
    paths = write_reports(decisions, output_dir=tmp_path)
    payload = decision_payload(decisions)

    assert payload["production_audio_approved"] is False
    assert payload["eligible_internal_eval_count"] == 0
    assert not any(candidate["public_production_status"] == "PRODUCTION_APPROVED" for candidate in payload["candidates"])
    assert all(candidate["public_production_status"] == "PRODUCTION_BLOCKED" for candidate in payload["candidates"])
    assert (tmp_path / "TTS_MODEL_LICENSE_EVIDENCE_MATRIX.md").exists()
    assert (tmp_path / "TTS_VOICE_RIGHTS_INTERNAL_EVAL_APPROVAL_PACKET.md").exists()
    assert (tmp_path / "TTS_INTERNAL_EVAL_CANDIDATE_SCORECARD.md").exists()
    assert (tmp_path / "tts_model_license_review.json").exists()
    assert paths
    written = json.loads((tmp_path / "tts_model_license_review.json").read_text(encoding="utf-8"))
    assert written["public_audio_release"] == "PUBLIC_AUDIO_RELEASE_BLOCKED"


def test_high_voice_cloning_risk_candidate_is_blocked():
    decision = classify_candidate(complete_candidate(voice_cloning_risk="HIGH"))

    assert decision.decision_status == BLOCKED
    assert any("voice cloning" in issue for issue in decision.issues)


def test_repo_candidates_with_unresolved_voice_rights_remain_hold_or_blocked():
    decisions = review_candidates()
    by_id = {decision.candidate["candidate_id"]: decision for decision in decisions}

    for candidate_id in ["kokoro", "melotts", "piper", "indic-parler-tts", "indicf5"]:
        decision = by_id[candidate_id]
        assert decision.decision_status in {HOLD_LICENSE_REVIEW, HOLD_VOICE_RIGHTS}
        assert decision.internal_eval_status == HOLD_VOICE_RIGHTS
        assert decision.public_production_status == "PRODUCTION_BLOCKED"
        assert any("voice rights evidence" in issue for issue in decision.issues)

    assert by_id["styletts2"].decision_status == BLOCKED


def test_kokoro_cannot_become_eligible_without_selected_voice_rights():
    decisions = review_candidates()
    kokoro = next(decision for decision in decisions if decision.candidate["candidate_id"] == "kokoro")

    assert kokoro.decision_status == HOLD_VOICE_RIGHTS
    assert kokoro.internal_eval_status == HOLD_VOICE_RIGHTS
    assert kokoro.public_production_status == "PRODUCTION_BLOCKED"
    assert kokoro.candidate["internal_eval_allowed"] is False
    assert "selected Kokoro voice/speaker rights evidence missing" in kokoro.candidate["internal_eval_blockers"]
    assert kokoro.candidate["selected_voice_id"] == "af_heart"
    assert kokoro.candidate["selected_voice_internal_eval_status"] == HOLD_VOICE_RIGHTS
    assert any("speaker identity or voice provenance remains unresolved" in issue for issue in kokoro.issues)


def test_missing_selected_voice_id_keeps_kokoro_hold():
    decision = classify_candidate(complete_candidate(candidate_id="kokoro", selected_voice_id=""))

    assert decision.internal_eval_status == HOLD_VOICE_RIGHTS
    assert decision.public_production_status == "PRODUCTION_BLOCKED"
    assert any("selected_voice_id" in issue for issue in decision.issues)


def test_missing_selected_voice_license_evidence_keeps_kokoro_hold():
    decision = classify_candidate(complete_candidate(candidate_id="kokoro", selected_voice_license_evidence_url=""))

    assert decision.internal_eval_status == HOLD_VOICE_RIGHTS
    assert decision.public_production_status == "PRODUCTION_BLOCKED"
    assert any("selected_voice_license_evidence_url" in issue for issue in decision.issues)


def test_unresolved_selected_voice_real_person_risk_keeps_kokoro_hold():
    decision = classify_candidate(complete_candidate(candidate_id="kokoro", selected_voice_real_person_risk="UNRESOLVED"))

    assert decision.internal_eval_status == HOLD_VOICE_RIGHTS
    assert decision.public_production_status == "PRODUCTION_BLOCKED"
    assert any("selected voice real-person risk" in issue for issue in decision.issues)


def test_missing_selected_voice_owner_or_legal_review_keeps_kokoro_hold():
    decision = classify_candidate(
        complete_candidate(
            candidate_id="kokoro",
            owner_selected_voice_approval_status="OWNER_REVIEW_REQUIRED",
            legal_selected_voice_review_status="LEGAL_REVIEW_REQUIRED",
        )
    )

    assert decision.internal_eval_status == HOLD_VOICE_RIGHTS
    assert decision.public_production_status == "PRODUCTION_BLOCKED"
    assert any("owner selected-voice approval" in issue for issue in decision.issues)
    assert any("legal selected-voice review" in issue for issue in decision.issues)


def test_melotts_cannot_become_eligible_without_selected_speaker_rights():
    decisions = review_candidates()
    melotts = next(decision for decision in decisions if decision.candidate["candidate_id"] == "melotts")

    assert melotts.decision_status == HOLD_VOICE_RIGHTS
    assert melotts.internal_eval_status == HOLD_VOICE_RIGHTS
    assert melotts.public_production_status == "PRODUCTION_BLOCKED"
    assert melotts.candidate["internal_eval_allowed"] is False
    assert "selected MeloTTS speaker/voice rights evidence missing" in melotts.candidate["internal_eval_blockers"]
    assert any("speaker identity or voice provenance remains unresolved" in issue for issue in melotts.issues)


def test_matrix_report_records_upstream_evidence_sources(tmp_path: Path):
    decisions = review_candidates()
    write_reports(decisions, output_dir=tmp_path)
    matrix = (tmp_path / "TTS_MODEL_LICENSE_EVIDENCE_MATRIX.md").read_text(encoding="utf-8")

    assert "Official repository" in matrix
    assert "https://huggingface.co/hexgrad/Kokoro-82M" in matrix
    assert "Selected voice ID: `af_heart`" in matrix
    assert "https://huggingface.co/ai4bharat/IndicF5" in matrix
    assert "Decision reason" in matrix


def test_kokoro_selected_voice_reports_are_written(tmp_path: Path):
    decisions = review_candidates()
    write_reports(decisions, output_dir=tmp_path)

    packet = (tmp_path / "KOKORO_SELECTED_VOICE_INTERNAL_EVAL_PACKET.md").read_text(encoding="utf-8")
    scorecard = (tmp_path / "KOKORO_SELECTED_VOICE_RIGHTS_SCORECARD.md").read_text(encoding="utf-8")

    assert "af_heart" in packet
    assert "PUBLIC_AUDIO_RELEASE_BLOCKED" in packet
    assert "PRODUCTION_BLOCKED" in packet
    assert "af_heart" in scorecard


def test_missing_voice_rights_evidence_url_blocks_internal_eval():
    decision = classify_candidate(complete_candidate(voice_rights_evidence_url=""))

    assert decision.internal_eval_status == HOLD_VOICE_RIGHTS
    assert decision.public_production_status == "PRODUCTION_BLOCKED"
    assert any("voice_rights_evidence_url" in issue for issue in decision.issues)


def test_unresolved_real_person_voice_clone_risk_blocks_internal_eval():
    decision = classify_candidate(complete_candidate(real_person_voice_clone_risk="UNRESOLVED"))

    assert decision.internal_eval_status == HOLD_VOICE_RIGHTS
    assert decision.public_production_status == "PRODUCTION_BLOCKED"
    assert any("real-person voice clone risk" in issue for issue in decision.issues)


def test_missing_owner_internal_eval_approval_holds_internal_eval():
    decision = classify_candidate(complete_candidate(owner_internal_eval_approval_status=""))

    assert decision.internal_eval_status == HOLD_OWNER_REVIEW
    assert decision.public_production_status == "PRODUCTION_BLOCKED"
    assert any("owner internal-eval approval" in issue for issue in decision.issues)


def test_complete_internal_eval_candidate_still_has_production_blocked():
    decision = classify_candidate(complete_candidate())

    assert decision.internal_eval_status == ELIGIBLE_INTERNAL_EVAL
    assert decision.decision_status == ELIGIBLE_INTERNAL_EVAL
    assert decision.public_production_status == "PRODUCTION_BLOCKED"
