from __future__ import annotations

import json
from pathlib import Path

from backend.audiobook_generation.model_adapters import ADAPTERS
from backend.audiobook_generation.model_adapters.ai4bharat_indic_tts import AI4BharatIndicTTSAdapter
from backend.audiobook_generation.model_adapters.f5_tts import F5TTSAdapter
from backend.audiobook_generation.model_adapters.mahatts import MahaTTSAdapter
from backend.audiobook_generation.model_adapters.svara_tts import SvaraTTSAdapter


ROOT = Path(__file__).resolve().parents[2]


def sample_chunk():
    return {
        "chunk_id": "kshudhita-pashan-chapter-001-001-test",
        "text": "রাত্রি আরও গভীর হইল।",
        "text_normalized": "রাত্রি আরও গভীর হইল।",
        "expected_emotion": "suspense",
    }


def test_adapter_registry_includes_required_models():
    assert {"svara-tts-v1", "mahatts-v2", "ai4bharat-indic-tts", "f5-tts"}.issubset(ADAPTERS)


def test_adapters_report_environment_without_network_calls(monkeypatch):
    import socket
    import subprocess

    def fail_network(*args, **kwargs):
        raise AssertionError("network call attempted")

    def fail_subprocess(*args, **kwargs):
        raise AssertionError("subprocess call attempted")

    monkeypatch.setattr(socket, "create_connection", fail_network)
    monkeypatch.setattr(subprocess, "run", fail_subprocess)

    for adapter_class in [SvaraTTSAdapter, MahaTTSAdapter, AI4BharatIndicTTSAdapter, F5TTSAdapter]:
        environment = adapter_class().check_environment()
        assert environment.status in {"MODEL_NOT_INSTALLED", "READY_LOCAL"}
        assert environment.install_instructions


def test_dry_run_adapter_results_do_not_create_audio_or_public_url(tmp_path):
    adapter = SvaraTTSAdapter(tmp_path)
    result = adapter.generate_chunk_dry_run(sample_chunk(), config={"no_public_release": True})

    assert result.status == "DRY_RUN_READY"
    assert result.metadata["audio_generated"] is False
    assert result.metadata["public_audio_url"] == ""
    assert result.metadata["internal_review_only"] is True


def test_dry_run_metadata_never_uses_public_paths(tmp_path):
    adapter = SvaraTTSAdapter(tmp_path)
    result = adapter.generate_chunk_dry_run(sample_chunk(), config={"no_public_release": True})

    encoded = json.dumps(result.metadata, ensure_ascii=False)
    assert "https://" not in encoded
    assert "/frontend/public/" not in encoded
    assert "/public/" not in encoded


def test_local_generation_refuses_without_owner_approval(tmp_path):
    adapter = MahaTTSAdapter(tmp_path)
    result = adapter.generate_chunk_local(sample_chunk(), tmp_path / "sample.wav", owner_approved=False)

    assert result.status == "OWNER_APPROVAL_REQUIRED"
    assert not (tmp_path / "sample.wav").exists()


def test_license_risk_prevents_automatic_commercial_approval():
    shortlist = json.loads((ROOT / "data/audiobook_models/model_shortlist.json").read_text())
    by_id = {model["model_id"]: model for model in shortlist["models"]}

    assert by_id["f5-tts"]["commercial_allowed"] is None
    assert "LICENSE_CHECK_REQUIRED" in by_id["f5-tts"]["recommended_status"]
    assert by_id["xtts-v2"]["commercial_allowed"] is False


def test_unsupported_bengali_models_are_not_primary_benchmark():
    shortlist = json.loads((ROOT / "data/audiobook_models/model_shortlist.json").read_text())
    unsupported = [model for model in shortlist["models"] if not model["bengali_supported"]]

    assert unsupported
    assert all(model["recommended_status"] != "PRIMARY_BENCHMARK" for model in unsupported)
