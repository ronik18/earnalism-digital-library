from __future__ import annotations

from backend.audiobook_generation.english_model_adapters.base import (
    BaseEnglishAudiobookModelAdapter,
    EnglishModelLicense,
    EnglishModelSpec,
)


class XTTSv2EnglishAdapter(BaseEnglishAudiobookModelAdapter):
    spec = EnglishModelSpec(
        model_id="xtts-v2",
        display_name="XTTS-v2",
        benchmark_status="RESEARCH_ONLY_LICENSE_CHECK_REQUIRED",
        provider_family="open_source_local",
        license=EnglishModelLicense(
            license_name="LICENSE_REVIEW_REQUIRED",
            commercial_allowed=False,
            requires_license_review=True,
            license_notes="Voice-cloning baseline only until license and reference-voice governance are approved.",
        ),
        expected_strengths=[
            "English voice-cloning research baseline",
            "Cross-model comparison for consistency",
        ],
        known_risks=[
            "License review required",
            "Reference voice consent required",
            "Real-person or celebrity imitation is prohibited",
        ],
        supports_reference_voice=True,
        supports_emotion_control=False,
        supports_nonverbal_tags=False,
        local_command="xtts",
    )

