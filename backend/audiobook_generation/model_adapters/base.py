from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


INTERNAL_REVIEW_ONLY = "INTERNAL_REVIEW_ONLY"


@dataclass(frozen=True)
class AdapterResult:
    status: str
    model_id: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelLicense:
    name: str
    commercial_allowed: bool | None
    requires_operator_verification: bool = True
    notes: str = ""


@dataclass(frozen=True)
class ModelEnvironment:
    model_id: str
    installed: bool
    status: str
    install_instructions: list[str]
    gpu_required: bool
    expected_vram_gb: float | None
    offline_possible: bool


@dataclass(frozen=True)
class ModelAdapterSpec:
    model_id: str
    display_name: str
    repo_url: str
    model_card_url: str
    license: ModelLicense
    bengali_supported: bool
    supported_language_codes: tuple[str, ...]
    gpu_required: bool
    expected_vram_gb: float | None
    offline_possible: bool
    supports_reference_voice_value: bool
    supports_style_tags_value: bool
    supports_emotion_tags_value: bool
    supports_chunk_generation_value: bool
    package_import_name: str | None = None
    command_name: str | None = None
    operator_install_instructions: tuple[str, ...] = ()
    expected_risk: str = "MEDIUM"
    recommended_status: str = "RESEARCH_ONLY"


class BaseAudiobookModelAdapter:
    """Dry-run-first adapter contract for local/open-source TTS candidates."""

    spec: ModelAdapterSpec

    def __init__(self, output_dir: Path | str | None = None) -> None:
        self.output_dir = Path(output_dir or "output/audiobook_bakeoff/kshudhita-pashan")

    def check_environment(self) -> ModelEnvironment:
        installed = False
        if self.spec.command_name:
            installed = shutil.which(self.spec.command_name) is not None
        if self.spec.package_import_name:
            installed = installed or self._can_import(self.spec.package_import_name)
        status = "READY_LOCAL" if installed else "MODEL_NOT_INSTALLED"
        instructions = list(self.spec.operator_install_instructions) or [
            "Install the model locally only after license and owner approval.",
            "Do not download model weights in CI.",
        ]
        return ModelEnvironment(
            model_id=self.spec.model_id,
            installed=installed,
            status=status,
            install_instructions=instructions,
            gpu_required=self.spec.gpu_required,
            expected_vram_gb=self.spec.expected_vram_gb,
            offline_possible=self.spec.offline_possible,
        )

    def validate_license(self) -> AdapterResult:
        license_info = self.spec.license
        if license_info.commercial_allowed is False:
            return AdapterResult(
                status="LICENSE_BLOCKED_FOR_COMMERCIAL_USE",
                model_id=self.spec.model_id,
                message="Commercial use is not approved for this model.",
                metadata={"license": asdict(license_info)},
            )
        if license_info.requires_operator_verification:
            return AdapterResult(
                status="LICENSE_REVIEW_REQUIRED",
                model_id=self.spec.model_id,
                message="Operator must verify model card, weights, and dependency licenses before commercial use.",
                metadata={"license": asdict(license_info)},
            )
        return AdapterResult(
            status="LICENSE_VERIFIED",
            model_id=self.spec.model_id,
            message="License metadata is marked commercial-ready for internal benchmarking.",
            metadata={"license": asdict(license_info)},
        )

    def estimate_resources(self) -> dict[str, Any]:
        return {
            "model_id": self.spec.model_id,
            "gpu_required": self.spec.gpu_required,
            "expected_vram_gb": self.spec.expected_vram_gb,
            "offline_possible": self.spec.offline_possible,
            "chunk_generation": self.spec.supports_chunk_generation_value,
        }

    def generate_chunk_dry_run(self, chunk: dict[str, Any], config: dict[str, Any] | None = None) -> AdapterResult:
        text = self.normalize_text(str(chunk.get("text_normalized") or chunk.get("text") or ""))
        chunk_id = str(chunk.get("chunk_id") or "unknown-chunk")
        metadata = {
            "book_slug": "kshudhita-pashan",
            "chunk_id": chunk_id,
            "model_id": self.spec.model_id,
            "mode": "dry-run",
            "internal_review_only": True,
            "no_public_release": True,
            "no_upload": True,
            "public_audio_url": "",
            "audio_generated": False,
            "text_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "character_count": len(text),
            "config": config or {},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        return AdapterResult(
            status="DRY_RUN_READY",
            model_id=self.spec.model_id,
            message="Dry-run metadata created; no audio was generated.",
            metadata=metadata,
        )

    def generate_chunk_local(
        self,
        chunk: dict[str, Any],
        output_path: Path | str,
        *,
        owner_approved: bool = False,
        config: dict[str, Any] | None = None,
    ) -> AdapterResult:
        if not owner_approved:
            return AdapterResult(
                status="OWNER_APPROVAL_REQUIRED",
                model_id=self.spec.model_id,
                message="Local audio generation requires explicit owner approval file.",
                metadata={"output_path": str(output_path), "config": config or {}},
            )
        environment = self.check_environment()
        if environment.status != "READY_LOCAL":
            return AdapterResult(
                status="MODEL_NOT_INSTALLED",
                model_id=self.spec.model_id,
                message="Model package or command is not installed locally.",
                metadata=asdict(environment),
            )
        return AdapterResult(
            status="LOCAL_GENERATION_NOT_IMPLEMENTED",
            model_id=self.spec.model_id,
            message="Adapter is wired but does not execute generation in this PR.",
            metadata={"output_path": str(output_path), "config": config or {}, "internal_review_only": True},
        )

    def normalize_text(self, text: str) -> str:
        return " ".join(text.replace("\u200c", "").replace("\u200d", "").split())

    def supported_languages(self) -> tuple[str, ...]:
        return self.spec.supported_language_codes

    def supports_emotion_tags(self) -> bool:
        return self.spec.supports_emotion_tags_value

    def supports_reference_voice(self) -> bool:
        return self.spec.supports_reference_voice_value

    def write_generation_metadata(self, path: Path | str, payload: dict[str, Any]) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        safe_payload = {
            "internal_review_only": True,
            "public_audio_url": "",
            "model_id": self.spec.model_id,
            **payload,
        }
        target.write_text(json.dumps(safe_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    @staticmethod
    def _can_import(module_name: str) -> bool:
        try:
            __import__(module_name)
            return True
        except Exception:
            return False
