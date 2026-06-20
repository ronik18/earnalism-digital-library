from __future__ import annotations

from backend.audiobook_generation.english_model_adapters.base import (
    BaseEnglishAudiobookModelAdapter,
    EnglishModelLicense,
    EnglishModelSpec,
)


class DryRunEnglishAdapter(BaseEnglishAudiobookModelAdapter):
    spec = EnglishModelSpec(
        model_id="dry-run",
        display_name="Earnalism Dry-Run Baseline",
        benchmark_status="SAFETY_BASELINE",
        provider_family="internal",
        license=EnglishModelLicense(
            license_name="N/A",
            commercial_allowed=False,
            requires_license_review=False,
            license_notes="No synthesis model. Used to verify planning and release gates only.",
        ),
        expected_strengths=["No audio generated", "Release gate baseline"],
        known_risks=["Cannot represent narration quality"],
        local_command="",
    )

