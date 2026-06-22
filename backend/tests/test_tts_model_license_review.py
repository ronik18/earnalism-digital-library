from __future__ import annotations

import json
from pathlib import Path

from scripts.tts_model_license_review import (
    BLOCKED,
    ELIGIBLE_INTERNAL_EVAL,
    HOLD_LICENSE_REVIEW,
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

    assert decision.decision_status == HOLD_LICENSE_REVIEW
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
    assert not any(candidate["public_production_status"] == "PRODUCTION_APPROVED" for candidate in payload["candidates"])
    assert (tmp_path / "TTS_MODEL_LICENSE_EVIDENCE_MATRIX.md").exists()
    assert (tmp_path / "tts_model_license_review.json").exists()
    assert paths
    written = json.loads((tmp_path / "tts_model_license_review.json").read_text(encoding="utf-8"))
    assert written["public_audio_release"] == "PUBLIC_AUDIO_RELEASE_BLOCKED"


def test_high_voice_cloning_risk_candidate_is_blocked():
    decision = classify_candidate(complete_candidate(voice_cloning_risk="HIGH"))

    assert decision.decision_status == BLOCKED
    assert any("voice cloning" in issue for issue in decision.issues)
