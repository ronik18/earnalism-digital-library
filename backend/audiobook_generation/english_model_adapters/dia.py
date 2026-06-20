from __future__ import annotations

from backend.audiobook_generation.english_model_adapters.base import (
    BaseEnglishAudiobookModelAdapter,
    EnglishModelLicense,
    EnglishModelSpec,
)


class DiaEnglishAdapter(BaseEnglishAudiobookModelAdapter):
    spec = EnglishModelSpec(
        model_id="dia",
        display_name="Dia",
        benchmark_status="DRAMATIC_DIALOGUE_BENCHMARK",
        provider_family="open_source_local",
        license=EnglishModelLicense(
            license_name="VERIFY_MODEL_CARD",
            commercial_allowed=None,
            requires_license_review=True,
            license_notes="License and model-card terms must be checked before production or commercial use.",
        ),
        expected_strengths=[
            "Dialogue-forward English narration",
            "Emotion and nonverbal tag experimentation",
        ],
        known_risks=[
            "Nonverbal tags can become distracting",
            "License review required before any public use",
        ],
        supports_reference_voice=False,
        supports_emotion_control=True,
        supports_nonverbal_tags=True,
        local_command="dia",
    )

