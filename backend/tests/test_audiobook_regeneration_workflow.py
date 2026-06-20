from __future__ import annotations

import json

from scripts.benchmark_bengali_tts_models import OUTPUT_ROOT, run_benchmark


def test_audiobook_regeneration_workflow_is_internal_review_only():
    payload = run_benchmark("kshudhita-pashan", "dry-run", require_owner_approval=False)

    assert payload["scope"] == "INTERNAL_REVIEW_ONLY"
    assert payload["audio_generated"] is False
    assert payload["public_audio_urls_created"] is False
    assert payload["final_status"] == "NO_MODEL_APPROVED_YET"


def test_public_audio_urls_are_not_created_in_manifests():
    run_benchmark("kshudhita-pashan", "dry-run", require_owner_approval=False)
    summary = json.loads((OUTPUT_ROOT / "benchmark_summary.json").read_text())
    manifests = list(OUTPUT_ROOT.glob("*/generation_manifest.json"))

    assert summary["public_audio_urls_created"] is False
    assert manifests
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text())
        assert manifest["public_audio_urls_created"] is False
        for chunk in manifest["chunks"]:
            assert chunk["metadata"].get("public_audio_url", "") == ""
