from __future__ import annotations

from .base import BaseAudiobookModelAdapter, ModelAdapterSpec, ModelLicense


class DryRunAdapter(BaseAudiobookModelAdapter):
    spec = ModelAdapterSpec(
        model_id="dry-run-no-audio",
        display_name="Dry Run No-Audio Adapter",
        repo_url="",
        model_card_url="",
        license=ModelLicense(
            name="N/A",
            commercial_allowed=False,
            requires_operator_verification=False,
            notes="No model, no audio generation.",
        ),
        bengali_supported=True,
        supported_language_codes=("bn",),
        gpu_required=False,
        expected_vram_gb=0,
        offline_possible=True,
        supports_reference_voice_value=False,
        supports_style_tags_value=False,
        supports_emotion_tags_value=False,
        supports_chunk_generation_value=True,
        expected_risk="LOW",
        recommended_status="DRY_RUN_ONLY",
    )
