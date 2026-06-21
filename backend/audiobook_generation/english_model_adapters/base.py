from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[3]
APPROVAL_DIR = ROOT_DIR / "data" / "audiobook_governance"


@dataclass(frozen=True)
class EnglishModelLicense:
    license_name: str
    commercial_allowed: bool | None
    requires_license_review: bool
    license_notes: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "license_name": self.license_name,
            "commercial_allowed": self.commercial_allowed,
            "requires_license_review": self.requires_license_review,
            "license_notes": self.license_notes,
        }


@dataclass(frozen=True)
class EnglishModelSpec:
    model_id: str
    display_name: str
    benchmark_status: str
    provider_family: str
    license: EnglishModelLicense
    expected_strengths: list[str] = field(default_factory=list)
    known_risks: list[str] = field(default_factory=list)
    supports_reference_voice: bool = False
    supports_emotion_control: bool = False
    supports_nonverbal_tags: bool = False
    local_command: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "display_name": self.display_name,
            "benchmark_status": self.benchmark_status,
            "provider_family": self.provider_family,
            "license": self.license.as_dict(),
            "expected_strengths": self.expected_strengths,
            "known_risks": self.known_risks,
            "supports_reference_voice": self.supports_reference_voice,
            "supports_emotion_control": self.supports_emotion_control,
            "supports_nonverbal_tags": self.supports_nonverbal_tags,
            "local_command": self.local_command,
        }


@dataclass(frozen=True)
class EnglishModelEnvironment:
    model_id: str
    local_command: str
    installed: bool
    owner_approval_required: bool
    owner_approval_present: bool
    owner_approval_status: str
    can_run_local: bool
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "local_command": self.local_command,
            "installed": self.installed,
            "owner_approval_required": self.owner_approval_required,
            "owner_approval_present": self.owner_approval_present,
            "owner_approval_status": self.owner_approval_status,
            "can_run_local": self.can_run_local,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class EnglishAdapterResult:
    model_id: str
    chunk_id: str
    status: str
    dry_run: bool
    internal_review_only: bool
    public_audio_url: str
    output_path: str
    metadata: dict[str, Any]
    blocking_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "chunk_id": self.chunk_id,
            "status": self.status,
            "dry_run": self.dry_run,
            "internal_review_only": self.internal_review_only,
            "public_audio_url": self.public_audio_url,
            "output_path": self.output_path,
            "metadata": self.metadata,
            "blocking_reason": self.blocking_reason,
        }


class BaseEnglishAudiobookModelAdapter:
    """Dry-run adapter contract for English audiobook model benchmarking."""

    spec: EnglishModelSpec

    def __init__(self, spec: EnglishModelSpec | None = None) -> None:
        if spec is not None:
            self.spec = spec

    @property
    def model_id(self) -> str:
        return self.spec.model_id

    def supported_languages(self) -> list[str]:
        return ["en"]

    def supports_emotion_control(self) -> bool:
        return self.spec.supports_emotion_control

    def supports_reference_voice(self) -> bool:
        return self.spec.supports_reference_voice

    def supports_nonverbal_tags(self) -> bool:
        return self.spec.supports_nonverbal_tags

    def check_environment(self, *, book_slug: str, require_owner_approval: bool = True) -> EnglishModelEnvironment:
        command = self.spec.local_command
        installed = bool(command and shutil.which(command.split()[0]))
        approval_status = owner_approval_status(book_slug)
        approved = approval_status == "APPROVED_LOCAL_INTERNAL_REVIEW"
        notes: list[str] = []
        if require_owner_approval and not approved:
            notes.append("Owner approval file is required before any local synthesis can run.")
        if command and not installed:
            notes.append(f"Local command is not installed or not on PATH: {command.split()[0]}")
        if self.spec.license.requires_license_review:
            notes.append("License review is required before commercial or production use.")
        return EnglishModelEnvironment(
            model_id=self.model_id,
            local_command=command,
            installed=installed,
            owner_approval_required=require_owner_approval,
            owner_approval_present=approval_status != "MISSING",
            owner_approval_status=approval_status,
            can_run_local=installed and (not require_owner_approval or approved) and not self.spec.license.requires_license_review,
            notes=notes,
        )

    def validate_license(self) -> dict[str, Any]:
        license_info = self.spec.license.as_dict()
        license_info["production_allowed"] = (
            self.spec.license.commercial_allowed is True and not self.spec.license.requires_license_review
        )
        license_info["release_gate"] = "RESEARCH_ONLY" if self.spec.license.requires_license_review else "REVIEW_REQUIRED"
        if license_info["production_allowed"]:
            license_info["release_gate"] = "INTERNAL_BENCHMARK_ONLY_UNTIL_HUMAN_APPROVAL"
        return license_info

    def estimate_resources(self, chunk_count: int) -> dict[str, Any]:
        return {
            "estimated_chunks": chunk_count,
            "estimated_audio_outputs": 0,
            "gpu_required": self.model_id in {"chatterbox-tts", "dia", "f5-tts", "xtts-v2"},
            "cpu_viable": self.model_id in {"dry-run", "kokoro-82m"},
            "external_api_calls": 0,
            "paid_provider_calls": 0,
        }

    def normalize_text(self, text: str) -> str:
        return " ".join((text or "").split())

    def generate_chunk_dry_run(self, chunk: dict[str, Any], *, output_dir: Path) -> EnglishAdapterResult:
        chunk_id = str(chunk.get("chunk_id") or stable_chunk_id(self.model_id, chunk.get("normalized_text") or ""))
        output_path = output_dir / self.model_id / f"{chunk_id}.planned.json"
        metadata = self.generation_metadata(chunk, mode="dry-run")
        return EnglishAdapterResult(
            model_id=self.model_id,
            chunk_id=chunk_id,
            status="DRY_RUN_PLANNED",
            dry_run=True,
            internal_review_only=True,
            public_audio_url="",
            output_path=str(output_path),
            metadata=metadata,
        )

    def generate_chunk_local(
        self,
        chunk: dict[str, Any],
        *,
        output_dir: Path,
        book_slug: str,
        require_owner_approval: bool = True,
    ) -> EnglishAdapterResult:
        chunk_id = str(chunk.get("chunk_id") or stable_chunk_id(self.model_id, chunk.get("normalized_text") or ""))
        environment = self.check_environment(book_slug=book_slug, require_owner_approval=require_owner_approval)
        output_path = output_dir / self.model_id / f"{chunk_id}.internal-review.wav"
        if require_owner_approval and environment.owner_approval_status != "APPROVED_LOCAL_INTERNAL_REVIEW":
            return EnglishAdapterResult(
                model_id=self.model_id,
                chunk_id=chunk_id,
                status="OWNER_APPROVAL_REQUIRED",
                dry_run=True,
                internal_review_only=True,
                public_audio_url="",
                output_path="",
                metadata={"environment": environment.as_dict(), "mode": "local"},
                blocking_reason="Local synthesis requires data/audiobook_governance/dracula.local_generation_approval.json with approved=true.",
            )
        if self.spec.license.requires_license_review:
            return EnglishAdapterResult(
                model_id=self.model_id,
                chunk_id=chunk_id,
                status="LICENSE_REVIEW_REQUIRED",
                dry_run=True,
                internal_review_only=True,
                public_audio_url="",
                output_path="",
                metadata={"environment": environment.as_dict(), "mode": "local"},
                blocking_reason="This model is research-only until license review is complete.",
            )
        if not environment.installed:
            return EnglishAdapterResult(
                model_id=self.model_id,
                chunk_id=chunk_id,
                status="MODEL_NOT_INSTALLED",
                dry_run=True,
                internal_review_only=True,
                public_audio_url="",
                output_path="",
                metadata={"environment": environment.as_dict(), "mode": "local"},
                blocking_reason=f"Local model command is unavailable: {self.spec.local_command}",
            )
        return EnglishAdapterResult(
            model_id=self.model_id,
            chunk_id=chunk_id,
            status="LOCAL_GENERATION_NOT_EXECUTED_IN_PR",
            dry_run=True,
            internal_review_only=True,
            public_audio_url="",
            output_path=str(output_path),
            metadata={"environment": environment.as_dict(), "mode": "local", "command_metadata_only": True},
            blocking_reason="This PR plans local synthesis only; no subprocesses are executed.",
        )

    def generation_metadata(self, chunk: dict[str, Any], *, mode: str) -> dict[str, Any]:
        return {
            "mode": mode,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "chunk_id": chunk.get("chunk_id"),
            "emotion_label": chunk.get("emotion_label"),
            "pace_hint": chunk.get("pace_hint"),
            "style_prompt": chunk.get("style_prompt"),
            "model": self.spec.as_dict(),
            "release_status": "INTERNAL_REVIEW_ONLY",
            "public_audio_url": "",
        }

    def write_generation_metadata(self, result: EnglishAdapterResult) -> None:
        output_path = Path(result.output_path)
        if not output_path:
            return
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result.as_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def stable_chunk_id(model_id: str, text: str) -> str:
    digest = hashlib.sha256(f"{model_id}:{text}".encode("utf-8")).hexdigest()[:16]
    return f"chunk-{digest}"


def owner_approval_status(book_slug: str) -> str:
    approval_path = APPROVAL_DIR / f"{book_slug}.local_generation_approval.json"
    if not approval_path.exists():
        return "MISSING"
    try:
        payload = json.loads(approval_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "INVALID_JSON"
    if payload.get("approved") is True and payload.get("scope") == "LOCAL_INTERNAL_REVIEW_ONLY":
        return "APPROVED_LOCAL_INTERNAL_REVIEW"
    return str(payload.get("status") or "NOT_APPROVED")


def env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}

