from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.benchmark_bengali_tts_models import OUTPUT_ROOT, run_benchmark
from scripts.evaluate_audiobook_samples import evaluate_samples


ROOT = Path(__file__).resolve().parents[2]


def test_model_shortlist_includes_required_bengali_candidates():
    shortlist = json.loads((ROOT / "data/audiobook_models/model_shortlist.json").read_text())
    model_ids = {model["model_id"] for model in shortlist["models"]}

    assert {"svara-tts-v1", "mahatts-v2", "ai4bharat-indic-tts", "f5-tts"}.issubset(model_ids)


def test_plan_mode_creates_internal_review_manifest_without_audio():
    payload = run_benchmark("kshudhita-pashan", "plan", require_owner_approval=False)

    assert payload["final_status"] == "NO_MODEL_APPROVED_YET"
    assert payload["public_audio_urls_created"] is False
    assert payload["audio_generated"] is False
    assert payload["kshudhita_pipeline_only"] is True
    assert payload["dracula_only_live"] is True


def test_dry_run_benchmark_does_not_generate_audio():
    payload = run_benchmark("kshudhita-pashan", "dry-run", require_owner_approval=False)

    assert payload["audio_generated"] is False
    assert all(model.get("public_audio_urls_created") is False for model in payload["models"])
    assert (OUTPUT_ROOT / "benchmark_summary.json").exists()


def test_local_benchmark_refuses_without_owner_approval_file():
    with pytest.raises(PermissionError):
        run_benchmark("kshudhita-pashan", "local", require_owner_approval=True)


def test_evaluation_does_not_fake_missing_mos_or_asr_metrics():
    payload = evaluate_samples("kshudhita-pashan")

    assert payload["asr_metrics_status"] == "OPERATOR_REQUIRED"
    assert payload["mos_metrics_status"] == "OPERATOR_REQUIRED"
    assert payload["public_path_leakage"] is False


def test_human_review_is_required_for_ten_out_of_ten_or_public_release():
    form = (ROOT / "AUDIOBOOK_MODEL_BAKEOFF_HUMAN_REVIEW_FORM.md").read_text()
    selection = (ROOT / "AUDIOBOOK_MODEL_SELECTION_REPORT.md").read_text()

    assert "owner_approved_model = false" in form
    assert "public_preview_approved = false" in form
    assert "full_audiobook_approved = false" in form
    assert "NO_MODEL_APPROVED_YET" in selection
