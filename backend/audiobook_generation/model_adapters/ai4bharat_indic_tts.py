from __future__ import annotations

from .base import BaseAudiobookModelAdapter, ModelAdapterSpec, ModelLicense


class AI4BharatIndicTTSAdapter(BaseAudiobookModelAdapter):
    spec = ModelAdapterSpec(
        model_id="ai4bharat-indic-tts",
        display_name="AI4Bharat Indic-TTS",
        repo_url="https://github.com/AI4Bharat/Indic-TTS",
        model_card_url="https://github.com/AI4Bharat/Indic-TTS",
        license=ModelLicense(
            name="VERIFY_MODEL_AND_DATA_LICENSE",
            commercial_allowed=None,
            requires_operator_verification=True,
            notes="Use as pronunciation baseline until exact code, model, and data licenses are verified.",
        ),
        bengali_supported=True,
        supported_language_codes=("bn", "hi", "en"),
        gpu_required=False,
        expected_vram_gb=4,
        offline_possible=True,
        supports_reference_voice_value=False,
        supports_style_tags_value=False,
        supports_emotion_tags_value=False,
        supports_chunk_generation_value=True,
        package_import_name="indic_tts",
        operator_install_instructions=(
            "Verify AI4Bharat Indic-TTS license and dependencies.",
            "Install locally only for baseline benchmarking.",
            "Do not use as public/commercial audio without legal approval.",
        ),
        expected_risk="LOW_TO_MEDIUM_BASELINE_ONLY",
        recommended_status="PRONUNCIATION_BASELINE",
    )
