from __future__ import annotations

from pathlib import Path

from backend.audiobook_generation.english_model_adapters import ADAPTER_REGISTRY, adapter_for_model


def sample_chunk():
    return {
        "chunk_id": "dracula-en-test",
        "normalized_text": "Mister Harker arrives in Bistritz with quiet unease.",
        "emotion_label": "intimate_diary",
        "pace_hint": "measured",
        "style_prompt": "Read like a private diary entry.",
    }


def test_adapter_registry_contains_required_english_models():
    assert {
        "chatterbox-tts",
        "dia",
        "kokoro-82m",
        "f5-tts",
        "xtts-v2",
    }.issubset(set(ADAPTER_REGISTRY))


def test_dry_run_adapter_result_never_exposes_public_audio_url(tmp_path: Path):
    adapter = adapter_for_model("chatterbox-tts")()
    result = adapter.generate_chunk_dry_run(sample_chunk(), output_dir=tmp_path)

    assert result.status == "DRY_RUN_PLANNED"
    assert result.dry_run is True
    assert result.internal_review_only is True
    assert result.public_audio_url == ""
    assert result.output_path.endswith(".planned.json")


def test_local_generation_requires_owner_approval(tmp_path: Path):
    adapter = adapter_for_model("kokoro-82m")()
    result = adapter.generate_chunk_local(
        sample_chunk(),
        output_dir=tmp_path,
        book_slug="dracula",
        require_owner_approval=True,
    )

    assert result.status == "OWNER_APPROVAL_REQUIRED"
    assert "local_generation_approval" in result.blocking_reason
    assert result.public_audio_url == ""


def test_research_only_models_are_not_commercially_approved():
    for model_id in ["f5-tts", "xtts-v2", "dia"]:
        adapter = adapter_for_model(model_id)()
        license_gate = adapter.validate_license()

        assert license_gate["production_allowed"] is False
        assert license_gate["release_gate"] == "RESEARCH_ONLY"


def test_chatterbox_and_kokoro_are_still_internal_benchmark_only():
    for model_id in ["chatterbox-tts", "kokoro-82m"]:
        adapter = adapter_for_model(model_id)()
        license_gate = adapter.validate_license()

        assert license_gate["production_allowed"] is True
        assert license_gate["release_gate"] == "INTERNAL_BENCHMARK_ONLY_UNTIL_HUMAN_APPROVAL"


def test_adapter_environment_does_not_call_network_or_subprocess(monkeypatch):
    def fail_socket(*_args, **_kwargs):
        raise AssertionError("network should not be used by adapter environment checks")

    monkeypatch.setattr("socket.create_connection", fail_socket)

    for model_id in ADAPTER_REGISTRY:
        environment = adapter_for_model(model_id)().check_environment(book_slug="dracula")
        assert environment.model_id == model_id
        assert environment.can_run_local is False

