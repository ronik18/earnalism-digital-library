from __future__ import annotations

from .base import BaseAudiobookModelAdapter, ModelAdapterSpec, ModelLicense


class SvaraTTSAdapter(BaseAudiobookModelAdapter):
    spec = ModelAdapterSpec(
        model_id="svara-tts-v1",
        display_name="Svara-TTS v1",
        repo_url="https://github.com/wavlab-speech/Svara",
        model_card_url="https://huggingface.co/collections/wavlab/svara-tts",
        license=ModelLicense(
            name="VERIFY_MODEL_CARD",
            commercial_allowed=None,
            requires_operator_verification=True,
            notes="Treat as benchmark candidate only until repo, model-card, and weight licenses are verified.",
        ),
        bengali_supported=True,
        supported_language_codes=("bn", "hi", "en"),
        gpu_required=True,
        expected_vram_gb=8,
        offline_possible=True,
        supports_reference_voice_value=False,
        supports_style_tags_value=True,
        supports_emotion_tags_value=True,
        supports_chunk_generation_value=True,
        package_import_name="svara_tts",
        operator_install_instructions=(
            "Verify Svara-TTS license and model-card terms.",
            "Install locally in an isolated environment after owner approval.",
            "Do not download weights in CI.",
        ),
        expected_risk="MEDIUM_LICENSE_AND_QUALITY_REVIEW",
        recommended_status="PRIMARY_BENCHMARK",
    )
