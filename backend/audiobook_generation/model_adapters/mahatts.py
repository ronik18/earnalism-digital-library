from __future__ import annotations

from .base import BaseAudiobookModelAdapter, ModelAdapterSpec, ModelLicense


class MahaTTSAdapter(BaseAudiobookModelAdapter):
    spec = ModelAdapterSpec(
        model_id="mahatts-v2",
        display_name="MahaTTS / MahaTTSv2",
        repo_url="https://github.com/dubverse-ai/MahaTTS",
        model_card_url="https://huggingface.co/dubverse-ai/MahaTTS",
        license=ModelLicense(
            name="Apache-2.0_OR_VERIFY_MODEL_CARD",
            commercial_allowed=True,
            requires_operator_verification=True,
            notes="MahaTTS has Apache-2.0 references; verify exact repo, weight, and dataset license before use.",
        ),
        bengali_supported=True,
        supported_language_codes=("bn", "hi", "en"),
        gpu_required=True,
        expected_vram_gb=6,
        offline_possible=True,
        supports_reference_voice_value=False,
        supports_style_tags_value=False,
        supports_emotion_tags_value=False,
        supports_chunk_generation_value=True,
        package_import_name="mahatts",
        operator_install_instructions=(
            "Verify MahaTTS/MahaTTSv2 source and weight license.",
            "Install locally only after commercial-use review passes.",
            "Use as pronunciation/naturalness benchmark before commercial approval.",
        ),
        expected_risk="MEDIUM_LICENSE_DATASET_REVIEW",
        recommended_status="PRIMARY_BENCHMARK",
    )
