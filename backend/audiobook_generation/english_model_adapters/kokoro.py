from __future__ import annotations

from backend.audiobook_generation.english_model_adapters.base import (
    BaseEnglishAudiobookModelAdapter,
    EnglishModelLicense,
    EnglishModelSpec,
)


class KokoroEnglishAdapter(BaseEnglishAudiobookModelAdapter):
    spec = EnglishModelSpec(
        model_id="kokoro-82m",
        display_name="Kokoro 82M",
        benchmark_status="FAST_BASELINE",
        provider_family="open_source_local",
        license=EnglishModelLicense(
            license_name="Apache-licensed weights",
            commercial_allowed=True,
            requires_license_review=False,
            license_notes="Fast local baseline; still requires final legal and voice QA review before production.",
        ),
        expected_strengths=[
            "Lightweight local benchmark",
            "Fast iteration on chunking and pacing",
        ],
        known_risks=[
            "May be less expressive than dialogue or emotion-specialized models",
            "Needs human listening review for premium tone",
        ],
        supports_reference_voice=False,
        supports_emotion_control=False,
        supports_nonverbal_tags=False,
        local_command="kokoro",
    )

