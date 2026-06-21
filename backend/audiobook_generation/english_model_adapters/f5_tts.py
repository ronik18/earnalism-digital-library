from __future__ import annotations

from backend.audiobook_generation.english_model_adapters.base import (
    BaseEnglishAudiobookModelAdapter,
    EnglishModelLicense,
    EnglishModelSpec,
)


class F5TTSEnglishAdapter(BaseEnglishAudiobookModelAdapter):
    spec = EnglishModelSpec(
        model_id="f5-tts",
        display_name="F5-TTS",
        benchmark_status="RESEARCH_ONLY_LICENSE_CHECK_REQUIRED",
        provider_family="open_source_local",
        license=EnglishModelLicense(
            license_name="Code MIT; pretrained weights reported as CC-BY-NC",
            commercial_allowed=False,
            requires_license_review=True,
            license_notes="Pretrained non-commercial terms mean this is not approved for Earnalism production use.",
        ),
        expected_strengths=[
            "Research comparison for voice quality",
            "Useful to benchmark against voice-cloning approaches",
        ],
        known_risks=[
            "Pretrained weights are not commercially approved",
            "Must not be used for public Earnalism audio without replacement weights and legal approval",
        ],
        supports_reference_voice=True,
        supports_emotion_control=False,
        supports_nonverbal_tags=False,
        local_command="f5-tts",
    )

