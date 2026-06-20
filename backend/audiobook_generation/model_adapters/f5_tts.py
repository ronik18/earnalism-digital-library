from __future__ import annotations

from .base import BaseAudiobookModelAdapter, ModelAdapterSpec, ModelLicense


class F5TTSAdapter(BaseAudiobookModelAdapter):
    spec = ModelAdapterSpec(
        model_id="f5-tts",
        display_name="F5-TTS",
        repo_url="https://github.com/SWivid/F5-TTS",
        model_card_url="https://huggingface.co/SWivid/F5-TTS",
        license=ModelLicense(
            name="MIT_CODE_WEIGHTS_LICENSE_REVIEW_REQUIRED",
            commercial_allowed=None,
            requires_operator_verification=True,
            notes="Zero-shot/reference-voice workflows require license review and explicit consented voice reference.",
        ),
        bengali_supported=True,
        supported_language_codes=("bn", "hi", "en"),
        gpu_required=True,
        expected_vram_gb=8,
        offline_possible=True,
        supports_reference_voice_value=True,
        supports_style_tags_value=False,
        supports_emotion_tags_value=False,
        supports_chunk_generation_value=True,
        package_import_name="f5_tts",
        operator_install_instructions=(
            "Verify F5-TTS code, pretrained weights, and dependency licenses.",
            "Use only owner-approved reference voice with written consent.",
            "Never clone or imitate any real person without explicit consent.",
        ),
        expected_risk="HIGH_REFERENCE_VOICE_AND_LICENSE_REVIEW",
        recommended_status="RESEARCH_ONLY_LICENSE_CHECK_REQUIRED",
    )
