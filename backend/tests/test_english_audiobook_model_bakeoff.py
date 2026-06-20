from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.benchmark_english_tts_models import run_benchmark
from scripts.evaluate_english_audiobook_samples import write_reports


def test_model_shortlist_contains_required_statuses():
    payload = json.loads(Path("data/audiobook_models/english_model_shortlist.json").read_text(encoding="utf-8"))
    statuses = {model["model_id"]: model["benchmark_status"] for model in payload["models"]}

    assert statuses["chatterbox-tts"] == "PRIMARY_BENCHMARK"
    assert statuses["dia"] == "DRAMATIC_DIALOGUE_BENCHMARK"
    assert statuses["kokoro-82m"] == "FAST_BASELINE"
    assert statuses["f5-tts"] == "RESEARCH_ONLY_LICENSE_CHECK_REQUIRED"
    assert statuses["xtts-v2"] == "RESEARCH_ONLY_LICENSE_CHECK_REQUIRED"


def test_non_commercial_models_are_not_release_candidates():
    payload = json.loads(Path("data/audiobook_models/english_model_shortlist.json").read_text(encoding="utf-8"))
    models = {model["model_id"]: model for model in payload["models"]}

    assert models["f5-tts"]["commercial_allowed"] is False
    assert models["xtts-v2"]["commercial_allowed"] is False
    assert models["f5-tts"]["production_release_allowed"] is False
    assert models["xtts-v2"]["production_release_allowed"] is False


def test_plan_and_dry_run_write_internal_only_manifests(tmp_path: Path):
    plan = run_benchmark("plan", tmp_path / "plan", require_owner_approval=True)
    dry_run = run_benchmark("dry-run", tmp_path / "dry", require_owner_approval=True)

    assert len(plan["rows"]) == 5
    assert len(dry_run["rows"]) == 5
    assert all(row["public_audio_url"] == "" for row in dry_run["rows"])
    assert all(int(row["planned_audio_outputs"]) == 0 for row in dry_run["rows"])
    assert sorted((tmp_path / "dry").glob("*/generation_manifest.json"))


def test_local_mode_refuses_without_owner_approval(tmp_path: Path):
    result = run_benchmark("local", tmp_path / "local", require_owner_approval=True)

    statuses = {row["status"] for row in result["rows"]}
    assert "OWNER_APPROVAL_REQUIRED" in statuses or "MIXED_LOCAL_GATE_STATUS" in statuses
    assert all(row["owner_approval_status"] == "MISSING" for row in result["rows"])


def test_cli_plan_runs_without_provider_calls(tmp_path: Path):
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_english_tts_models.py",
            "--book-slug",
            "dracula",
            "--mode",
            "plan",
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "English audiobook model bake-off complete" in completed.stdout
    payload = json.loads((tmp_path / "english_model_bakeoff_summary.json").read_text(encoding="utf-8"))
    assert payload["public_audio_created"] is False
    assert payload["paid_provider_calls"] == 0


def test_evaluation_reports_do_not_claim_asr_or_mos(tmp_path: Path):
    evaluations = [
        {
            "model_id": "chatterbox-tts",
            "qa_status": "PENDING_HUMAN_AUDIO_REVIEW",
            "asr_word_error_rate": None,
            "mos_score": None,
            "recommended_release_action": "DO_NOT_PUBLISH_AUDIO",
        }
    ]

    write_reports(evaluations, tmp_path)

    qa_report = Path("AUDIOBOOK_ENGLISH_MODEL_BAKEOFF_AUDIO_QA_REPORT.md").read_text(encoding="utf-8")
    selection = Path("AUDIOBOOK_ENGLISH_MODEL_SELECTION_REPORT.md").read_text(encoding="utf-8")
    assert "PENDING_HUMAN_AUDIO_REVIEW" in qa_report
    assert "NO_MODEL_APPROVED_YET" in selection
    assert "DO_NOT_PUBLISH_AUDIO" in selection

