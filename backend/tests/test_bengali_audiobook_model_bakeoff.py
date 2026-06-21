from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.benchmark_bengali_tts_models import OUTPUT_ROOT, compute_scorecard, run_benchmark
from scripts.bengali_audiobook_chunker import approved_source_status
from scripts.evaluate_audiobook_samples import evaluate_samples


ROOT = Path(__file__).resolve().parents[2]


def test_model_shortlist_includes_required_bengali_candidates():
    shortlist = json.loads((ROOT / "data/audiobook_models/model_shortlist.json").read_text())
    model_ids = {model["model_id"] for model in shortlist["models"]}

    assert {"svara-tts-v1", "mahatts-v2", "ai4bharat-indic-tts", "f5-tts"}.issubset(model_ids)


def test_plan_mode_creates_internal_review_manifest_without_audio():
    payload = run_benchmark("kshudhita-pashan", "plan", require_owner_approval=False)

    assert payload["final_status"] == "OPERATOR_REQUIRED"
    assert payload["source_status"]["status"] == "OPERATOR_REQUIRED"
    assert payload["representative_chunk_count"] == 0
    assert payload["public_audio_urls_created"] is False
    assert payload["audio_generated"] is False
    assert payload["kshudhita_pipeline_only"] is True
    assert payload["dracula_only_live"] is True
    assert payload["bengali_human_listening_review"]["approved"] is False
    assert payload["bengali_human_listening_review"]["minimum_score_for_9_9"] == 9.5


def test_dry_run_benchmark_does_not_generate_audio():
    payload = run_benchmark("kshudhita-pashan", "dry-run", require_owner_approval=False)

    assert payload["final_status"] == "OPERATOR_REQUIRED"
    assert payload["audio_generated"] is False
    assert all(model.get("public_audio_urls_created") is False for model in payload["models"])
    assert all(model.get("chunks") == [] for model in payload["models"])
    assert (OUTPUT_ROOT / "benchmark_summary.json").exists()


def test_local_benchmark_refuses_without_owner_approval_file():
    payload = run_benchmark("kshudhita-pashan", "local", require_owner_approval=True)

    assert payload["final_status"] == "OPERATOR_REQUIRED"
    assert payload["representative_chunk_count"] == 0


def test_evaluation_does_not_fake_missing_mos_or_asr_metrics():
    payload = evaluate_samples("kshudhita-pashan")

    assert payload["asr_metrics_status"] == "OPERATOR_REQUIRED"
    assert payload["mos_metrics_status"] == "OPERATOR_REQUIRED"
    assert payload["public_path_leakage"] is False


def test_official_bakeoff_requires_real_approved_source_text():
    status = approved_source_status()

    assert status["status"] == "OPERATOR_REQUIRED"
    assert status["full_source_text_committed"] is False
    assert "full source text" in status["blocking_reason"]


def test_human_review_is_required_for_ten_out_of_ten_or_public_release():
    form = (ROOT / "AUDIOBOOK_MODEL_BAKEOFF_HUMAN_REVIEW_FORM.md").read_text()
    selection = (ROOT / "AUDIOBOOK_MODEL_SELECTION_REPORT.md").read_text()

    assert "owner_approved_model = false" in form
    assert "public_preview_approved = false" in form
    assert "full_audiobook_approved = false" in form
    assert "NO_MODEL_APPROVED_YET" in selection


def test_license_evidence_blocks_automatic_production_candidates():
    payload = run_benchmark("kshudhita-pashan", "plan", require_owner_approval=False)

    assert all(model["license_evidence"]["present"] is True for model in payload["models"])
    assert all(model["license_evidence"]["verified_by"] == "operator_required" for model in payload["models"])
    assert all(model["license_evidence"]["production_candidate_allowed"] is False for model in payload["models"])


def test_scorecard_blocks_9_9_without_source_samples_and_human_review():
    payload = json.loads((ROOT / "AUDIOBOOK_BENGALI_MODEL_BAKEOFF_SCORECARD.json").read_text())

    assert payload["score"] < 9.9
    assert payload["score"] <= 8.6
    assert payload["final_public_audio_status"] == "BLOCKED"
    assert "approved source text missing = max 8.6" in payload["caps_applied"]
    assert "no Bengali human listening review >= 9.5 = max 9.0" in payload["caps_applied"]
    assert "license evidence not manually reviewed = max 9.2" in payload["caps_applied"]
    assert payload["human_review_approved"] is False
    assert payload["license_manual_review_complete"] is False


def test_scorecard_blocks_9_9_without_bengali_human_review_and_license_review():
    payload = {
        "book_slug": "kshudhita-pashan",
        "source_status": {"status": "READY"},
        "representative_chunk_count": 32,
        "models": [
            {
                "audio_generated": True,
                "public_audio_urls_created": False,
                "license_evidence": {
                    "human_license_review_approved": False,
                    "verified_by": "operator_required",
                },
            }
        ],
        "bengali_human_listening_review": {
            "approved": False,
            "bengali_human_review_score": 9.4,
        },
        "final_status": "NO_MODEL_APPROVED_YET",
    }

    scorecard = compute_scorecard(payload)

    assert scorecard["score"] <= 9.0
    assert scorecard["final_public_audio_status"] == "BLOCKED"
    assert "no Bengali human listening review >= 9.5 = max 9.0" in scorecard["caps_applied"]
    assert "license evidence not manually reviewed = max 9.2" in scorecard["caps_applied"]
