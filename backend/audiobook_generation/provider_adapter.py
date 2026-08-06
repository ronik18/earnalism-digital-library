from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
from typing import Any


PROHIBITED_VOICE_SOURCE_TYPES = {
    "REAL_PERSON_CLONE",
    "CELEBRITY_IMPERSONATION",
    "PUBLIC_FIGURE_IMPERSONATION",
}
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
    text: str = ""


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
    artifact_path: str = ""
    artifact_sha256: str = ""
    request_fingerprint: str = ""
    retryable: bool = False
    attempt: int = 1


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
            issues.append(
                "Unauthorized real-person, celebrity, or public-figure voice likeness is blocked."
            )
        if "celebrity" in display_name or "public figure" in display_name:
            issues.append(
                "Voice profile must not imitate a celebrity or public figure."
            )
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
            issues.append(
                "Unauthorized voice cloning or public-figure imitation is blocked."
            )
        if (
            source_type == "REAL_PERSON_CLONE"
            and consent_status != "WRITTEN_CONSENT_ON_FILE"
        ):
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


class ProviderExecutionError(RuntimeError):
    """A provider failure classified for bounded orchestration retries."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class PaidGenerationAuthorization:
    """Explicit, short-lived authorization required before paid provider I/O."""

    provider: str
    max_usd: float
    lock_id: str
    approval_env: str

    @classmethod
    def from_environment(
        cls, provider: str, estimated_cost_usd: float
    ) -> "PaidGenerationAuthorization":
        normalized = provider.strip().lower()
        provider_env = normalized.upper().replace("-", "_")
        approval_env = f"EARNALISM_APPROVE_{provider_env}_GENERATION"
        approved = os.environ.get(approval_env, "").strip().lower() == "true"
        if not approved:
            raise ProviderExecutionError(
                f"{approval_env}=true is required", retryable=False
            )
        if (
            os.environ.get("EARNALISM_ENABLE_PAID_GENERATION", "").strip().lower()
            != "true"
        ):
            raise ProviderExecutionError(
                "EARNALISM_ENABLE_PAID_GENERATION=true is required", retryable=False
            )
        raw_budget = os.environ.get("EARNALISM_PAID_GENERATION_MAX_USD", "").strip()
        try:
            max_usd = float(raw_budget)
        except ValueError as exc:
            raise ProviderExecutionError(
                "EARNALISM_PAID_GENERATION_MAX_USD must be numeric", retryable=False
            ) from exc
        if max_usd <= 0 or estimated_cost_usd > max_usd:
            raise ProviderExecutionError(
                "paid generation exceeds the explicit budget cap", retryable=False
            )
        lock_id = os.environ.get("EARNALISM_PAID_GENERATION_LOCK_ID", "").strip()
        if not lock_id:
            raise ProviderExecutionError(
                "EARNALISM_PAID_GENERATION_LOCK_ID is required", retryable=False
            )
        lock_path = os.environ.get("EARNALISM_PAID_GENERATION_LOCK_PATH", "").strip()
        if not lock_path:
            raise ProviderExecutionError(
                "EARNALISM_PAID_GENERATION_LOCK_PATH is required", retryable=False
            )
        try:
            lock_payload = json.loads(Path(lock_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProviderExecutionError(
                "paid generation lock cannot be read", retryable=False
            ) from exc
        if (
            not isinstance(lock_payload, dict)
            or lock_payload.get("status") != "AUTHORIZED"
        ):
            raise ProviderExecutionError(
                "paid generation lock is not AUTHORIZED", retryable=False
            )
        if str(lock_payload.get("lock_id") or "") != lock_id:
            raise ProviderExecutionError(
                "paid generation lock id does not match", retryable=False
            )
        allowed = lock_payload.get("providers")
        if not isinstance(allowed, list) or normalized not in {
            str(item).lower() for item in allowed
        }:
            raise ProviderExecutionError(
                "paid generation lock does not authorize this provider", retryable=False
            )
        return cls(
            provider=normalized,
            max_usd=max_usd,
            lock_id=lock_id,
            approval_env=approval_env,
        )


def request_fingerprint(request: GenerationRequest) -> str:
    payload = {
        "book_slug": request.book_slug,
        "segment_id": request.segment_id,
        "text_sha256": hashlib.sha256(
            (request.text or request.text_ref).encode("utf-8")
        ).hexdigest(),
        "language": request.language,
        "narrator_profile_id": request.narrator_profile_id,
        "voice_source_type": request.voice_source_type,
        "consent_status": request.consent_status,
        "metadata": request.metadata,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _artifact_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SarvamBulbulProvider(NarrationProvider):
    """Real Sarvam Bulbul adapter; all network calls remain authorization-gated."""

    provider_name = "sarvam"

    def estimate_cost(self, request: GenerationRequest) -> float:
        value = request.metadata.get("estimated_cost_usd")
        if value is None:
            raise ProviderExecutionError(
                "estimated_cost_usd is required before provider execution",
                retryable=False,
            )
        return float(value)

    def validate_voice_profile(self, profile: dict[str, Any]) -> list[str]:
        issues: list[str] = []
        if str(profile.get("model") or "") != "bulbul:v3":
            issues.append("Sarvam provider requires model bulbul:v3")
        if not str(profile.get("voice") or "").strip():
            issues.append("Sarvam voice is required")
        if profile.get("approved_for_generation") is not True:
            issues.append("Sarvam profile approval is missing")
        return issues

    def validate_consent(self, request: GenerationRequest) -> list[str]:
        if request.voice_source_type.upper() in PROHIBITED_VOICE_SOURCE_TYPES:
            return ["prohibited voice source type"]
        return (
            []
            if request.consent_status.upper() in VALID_STYLE_CONSENT
            else ["voice consent is not approved"]
        )

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
            request_fingerprint=request_fingerprint(request),
        )

    def generate_segment(self, request: GenerationRequest) -> ProviderResult:
        fingerprint = request_fingerprint(request)
        if request.dry_run:
            return self.dry_run(request)
        issues = self.validate_consent(request)
        if issues:
            raise ProviderExecutionError("; ".join(issues), retryable=False)
        estimated_cost = self.estimate_cost(request)
        PaidGenerationAuthorization.from_environment(self.provider_name, estimated_cost)
        output = Path(str(request.metadata.get("output_path") or ""))
        text = request.text or request.text_ref
        if not output or not text:
            raise ProviderExecutionError(
                "output_path and narration text are required", retryable=False
            )
        try:
            from internal.audiobook_lab.scripts.providers.sarvam_tts_adapter import (
                synthesize,
            )

            synthesize(
                text,
                output,
                speaker=str(
                    request.metadata.get("voice") or request.narrator_profile_id
                ),
                model=str(request.metadata.get("model") or "bulbul:v3"),
                language_code=str(
                    request.metadata.get("language_code") or request.language
                ),
                output_codec=str(request.metadata.get("output_codec") or "wav"),
            )
        except ProviderExecutionError:
            raise
        except Exception as exc:
            raise ProviderExecutionError(
                "Sarvam generation failed", retryable=True
            ) from exc
        return ProviderResult(
            provider=self.provider_name,
            status="PASS",
            dry_run=False,
            network_calls_performed=1,
            audio_generated=True,
            publishable=False,
            cost_estimate=estimated_cost,
            artifact_path=str(output),
            artifact_sha256=_artifact_sha256(output),
            request_fingerprint=fingerprint,
        )


class ElevenLabsProvider(NarrationProvider):
    """Real ElevenLabs adapter over the existing guarded client."""

    provider_name = "elevenlabs"

    def estimate_cost(self, request: GenerationRequest) -> float:
        value = request.metadata.get("estimated_cost_usd")
        if value is None:
            raise ProviderExecutionError(
                "estimated_cost_usd is required before provider execution",
                retryable=False,
            )
        return float(value)

    def validate_voice_profile(self, profile: dict[str, Any]) -> list[str]:
        issues: list[str] = []
        if not str(profile.get("voice_id") or "").strip():
            issues.append("ElevenLabs voice_id is required")
        if not str(profile.get("model") or "").strip():
            issues.append("ElevenLabs model is required")
        if profile.get("approved_for_generation") is not True:
            issues.append("ElevenLabs profile approval is missing")
        return issues

    def validate_consent(self, request: GenerationRequest) -> list[str]:
        return (
            []
            if request.voice_source_type.upper() not in PROHIBITED_VOICE_SOURCE_TYPES
            else ["prohibited voice source type"]
        )

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
            request_fingerprint=request_fingerprint(request),
        )

    def generate_segment(self, request: GenerationRequest) -> ProviderResult:
        fingerprint = request_fingerprint(request)
        if request.dry_run:
            return self.dry_run(request)
        issues = self.validate_consent(request)
        if issues:
            raise ProviderExecutionError("; ".join(issues), retryable=False)
        estimated_cost = self.estimate_cost(request)
        PaidGenerationAuthorization.from_environment(self.provider_name, estimated_cost)
        try:
            from scripts.lib.elevenlabs_tts_client import (
                ElevenLabsSettings,
                generate_tts_audio,
            )

            output = Path(str(request.metadata.get("output_path") or ""))
            settings = ElevenLabsSettings(
                provider="elevenlabs",
                voice_id=str(
                    request.metadata.get("voice_id") or request.narrator_profile_id
                ),
                voice_name=str(
                    request.metadata.get("voice") or request.narrator_profile_id
                ),
                model_id=str(request.metadata.get("model") or "eleven_multilingual_v2"),
                output_format=str(
                    request.metadata.get("output_format") or "mp3_44100_128"
                ),
                beta_services_allowed=False,
                voice_cloning_allowed=False,
                elevenreader_allowed=False,
            )
            generate_tts_audio(
                chunk_id=request.segment_id,
                text=request.text or request.text_ref,
                settings=settings,
                output_path=output,
                execute=True,
            )
        except ProviderExecutionError:
            raise
        except Exception as exc:
            raise ProviderExecutionError(
                "ElevenLabs generation failed", retryable=True
            ) from exc
        return ProviderResult(
            provider=self.provider_name,
            status="PASS",
            dry_run=False,
            network_calls_performed=1,
            audio_generated=True,
            publishable=False,
            cost_estimate=estimated_cost,
            artifact_path=str(output),
            artifact_sha256=_artifact_sha256(output),
            request_fingerprint=fingerprint,
        )


def provider_for_name(name: str) -> NarrationProvider:
    normalized = name.strip().lower()
    if normalized == "sarvam":
        return SarvamBulbulProvider()
    if normalized == "elevenlabs":
        return ElevenLabsProvider()
    raise ValueError(f"unsupported provider: {name}")
