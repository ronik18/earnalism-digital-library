from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


PROHIBITED_VOICE_SOURCE_TYPES = {"REAL_PERSON_CLONE", "CELEBRITY_IMPERSONATION", "PUBLIC_FIGURE_IMPERSONATION"}
VALID_STYLE_CONSENT = {"NOT_APPLICABLE_STYLE_PROFILE", "WRITTEN_CONSENT_ON_FILE"}


@dataclass(frozen=True)
class GenerationRequest:
    book_slug: str
    segment_id: str
    text_ref: str
    language: str
    narrator_profile_id: str
    voice_source_type: str
    consent_status: str
    dry_run: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    status: str
    dry_run: bool
    network_calls_performed: int
    audio_generated: bool
    publishable: bool
    cost_estimate: float
    issues: list[str] = field(default_factory=list)


class NarrationProvider(ABC):
    """Interface for future narration providers.

    Implementations must not make network calls unless a future, separately
    approved PR adds credentials, consent checks, cost controls, and tests.
    """

    provider_name = "abstract"

    @abstractmethod
    def generate_segment(self, request: GenerationRequest) -> ProviderResult:
        """Plan or generate a segment."""

    @abstractmethod
    def estimate_cost(self, request: GenerationRequest) -> float:
        """Return an explicit cost estimate before generation."""

    @abstractmethod
    def validate_voice_profile(self, profile: dict[str, Any]) -> list[str]:
        """Return voice profile safety issues."""

    @abstractmethod
    def validate_consent(self, request: GenerationRequest) -> list[str]:
        """Return consent issues for the request."""

    @abstractmethod
    def dry_run(self, request: GenerationRequest) -> ProviderResult:
        """Return a metadata-only dry-run result."""


class DryRunNarrationProvider(NarrationProvider):
    """Metadata-only provider used by the regenerated narration workflow."""

    provider_name = "dry_run_narration_provider"

    def generate_segment(self, request: GenerationRequest) -> ProviderResult:
        if not request.dry_run:
            return ProviderResult(
                provider=self.provider_name,
                status="BLOCKED_NON_DRY_RUN",
                dry_run=False,
                network_calls_performed=0,
                audio_generated=False,
                publishable=False,
                cost_estimate=self.estimate_cost(request),
                issues=["Real narration generation is not implemented in this PR."],
            )
        return self.dry_run(request)

    def estimate_cost(self, request: GenerationRequest) -> float:
        characters = max(0, int(request.metadata.get("estimated_characters", 0) or 0))
        return round(characters * 0.0, 4)

    def validate_voice_profile(self, profile: dict[str, Any]) -> list[str]:
        issues: list[str] = []
        source_type = str(profile.get("voice_source_type") or "").strip().upper()
        consent_status = str(profile.get("consent_status") or "").strip().upper()
        display_name = str(profile.get("display_name") or "").strip().lower()

        if source_type in PROHIBITED_VOICE_SOURCE_TYPES:
            issues.append("Unauthorized real-person, celebrity, or public-figure voice likeness is blocked.")
        if "celebrity" in display_name or "public figure" in display_name:
            issues.append("Voice profile must not imitate a celebrity or public figure.")
        if consent_status not in VALID_STYLE_CONSENT:
            issues.append("Voice consent status is not approved for a style profile.")
        if profile.get("allowed_for_generation") is not True:
            issues.append("Voice profile is not approved for generation.")
        if profile.get("owner_approved") is not True:
            issues.append("Voice profile owner approval is missing.")
        return issues

    def validate_consent(self, request: GenerationRequest) -> list[str]:
        issues: list[str] = []
        source_type = request.voice_source_type.strip().upper()
        consent_status = request.consent_status.strip().upper()
        if source_type in PROHIBITED_VOICE_SOURCE_TYPES:
            issues.append("Unauthorized voice cloning or public-figure imitation is blocked.")
        if source_type == "REAL_PERSON_CLONE" and consent_status != "WRITTEN_CONSENT_ON_FILE":
            issues.append("Real-person voice clone requires explicit written consent.")
        if consent_status not in VALID_STYLE_CONSENT:
            issues.append("Consent status is not acceptable for this request.")
        return issues

    def dry_run(self, request: GenerationRequest) -> ProviderResult:
        issues = self.validate_consent(request)
        return ProviderResult(
            provider=self.provider_name,
            status="DRY_RUN_PLANNED" if not issues else "BLOCKED_CONSENT",
            dry_run=True,
            network_calls_performed=0,
            audio_generated=False,
            publishable=False,
            cost_estimate=self.estimate_cost(request),
            issues=issues,
        )
