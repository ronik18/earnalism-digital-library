from __future__ import annotations

import json
from pathlib import Path

from scripts.benchmark_english_tts_models import run_benchmark
from scripts.evaluate_english_audiobook_samples import evaluate_manifest, write_reports


def test_regeneration_workflow_is_internal_review_only(tmp_path: Path):
    run_benchmark("dry-run", tmp_path, require_owner_approval=True)
    manifests = sorted(tmp_path.glob("*/generation_manifest.json"))
    evaluations = [evaluate_manifest(path) for path in manifests]
    write_reports(evaluations, tmp_path)

    summary = json.loads((tmp_path / "english_audio_qa_summary.json").read_text(encoding="utf-8"))

    assert manifests
    assert summary["selection_status"] == "NO_MODEL_APPROVED_YET"
    assert summary["public_audio_published"] is False
    assert all(row["recommended_release_action"] == "DO_NOT_PUBLISH_AUDIO" for row in summary["evaluations"])


def test_regeneration_manifest_does_not_create_audio_outputs(tmp_path: Path):
    run_benchmark("dry-run", tmp_path, require_owner_approval=True)

    for manifest_path in tmp_path.glob("*/generation_manifest.json"):
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert payload["internal_review_only"] is True
        assert payload["public_audio_url"] == ""
        assert payload["audio_published"] is False
        assert all(not row.get("public_audio_url") for row in payload["results"])

