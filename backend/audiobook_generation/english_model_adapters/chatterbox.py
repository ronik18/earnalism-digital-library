from __future__ import annotations

from backend.audiobook_generation.english_model_adapters.base import (
    BaseEnglishAudiobookModelAdapter,
    EnglishModelLicense,
    EnglishModelSpec,
)


class ChatterboxEnglishAdapter(BaseEnglishAudiobookModelAdapter):
    spec = EnglishModelSpec(
        model_id="chatterbox-tts",
        display_name="Chatterbox TTS",
        benchmark_status="PRIMARY_BENCHMARK",
        provider_family="open_source_local",
        license=EnglishModelLicense(
            license_name="MIT",
            commercial_allowed=True,
            requires_license_review=False,
            license_notes="Use only approved reference/style voices. No real-person or celebrity imitation.",
        ),
        expected_strengths=[
            "Expressive English narration",
            "Emotion and exaggeration controls",
            "Useful primary benchmark for Gothic narration",
        ],
        known_risks=[
            "Reference voice governance required",
            "Needs human review for melodrama or overacting",
        ],
        supports_reference_voice=True,
        supports_emotion_control=True,
        supports_nonverbal_tags=False,
        local_command="chatterbox-tts",
    )

