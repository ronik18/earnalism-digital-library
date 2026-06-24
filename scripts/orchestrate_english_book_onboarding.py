#!/usr/bin/env python3
"""Dry-run English book onboarding orchestrator.

This script prepares local evidence reports for a new English book candidate.
It does not publish books, enable public audio, create public audio files,
change payment settings, call paid providers, or mutate production data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audiobook_generation_sync_pipeline import (
    PUBLIC_AUDIO_RELEASE_BLOCKED as SYNC_PUBLIC_AUDIO_RELEASE_BLOCKED,
    run_pipeline as run_audiobook_sync_pipeline,
)
from scripts.audiobook_chapter_pipeline import (
    BLOCKED_REAL_GENERATION as CHAPTER_PIPELINE_BLOCKED_REAL_GENERATION,
    DRY_RUN_READY as CHAPTER_PIPELINE_DRY_RUN_READY,
    run_chapter_pipeline,
)
from scripts.elevenlabs_internal_sample_import import (
    HOLD_SYNC_QA_REQUIRED as ELEVENLABS_HOLD_SYNC_QA_REQUIRED,
    INTERNAL_SAMPLE_ONLY,
    run_import as run_elevenlabs_sample_import,
)
from scripts.tts_model_license_review import (
    decision_payload as tts_decision_payload,
    review_candidates as review_tts_candidates,
    selected_candidate_decision,
    write_reports as write_tts_model_reports,
)
from scripts.tts_provider_internal_eval_review import (
    decision_payload as provider_decision_payload,
    review_provider_candidates,
    selected_provider_decision,
    write_reports as write_tts_provider_reports,
)


DEFAULT_OUTPUT_DIR = ROOT / "output" / "onboarding"
LATEST_OUTPUT_DIR = ROOT / "output" / "english_book_onboarding"
CODEX_PROMPT_PATH = ROOT / "output" / "codex_prompts" / "next_english_book_onboarding_prompt.md"

PUBLIC_AUDIO_RELEASE_BLOCKED = "PUBLIC_AUDIO_RELEASE_BLOCKED"
PUBLICATION_HOLD = "HOLD_SOURCE_RIGHTS_QA_REQUIRED"
PUBLICATION_DRAFT_REVIEW = "READY_FOR_OWNER_PUBLICATION_REVIEW_DRAFT_ONLY"
TTS_MODEL_LICENSE_STAGE = "TTS_MODEL_LICENSE_AND_SUITABILITY_REVIEW"
TTS_VOICE_RIGHTS_STAGE = "TTS_VOICE_RIGHTS_INTERNAL_EVAL_REVIEW"
TTS_PROVIDER_INTERNAL_EVAL_STAGE = "LICENSED_PROVIDER_TTS_INTERNAL_EVAL_REVIEW"
ELEVENLABS_INTERNAL_SAMPLE_STAGE = "ELEVENLABS_INTERNAL_SAMPLE_PREP_AND_IMPORT"
AUTOMATED_AUDIOBOOK_CHAPTER_PIPELINE_STAGE = "AUTOMATED_AUDIOBOOK_CHAPTER_PIPELINE_DRY_RUN"
ELEVENLABS_EVIDENCE_PATH = ROOT / "internal" / "legal" / "elevenlabs" / "creator-membership-internal-eval-evidence.md"
ELEVENLABS_DRACULA_SAMPLE_DIR = ROOT / "internal" / "audiobook_lab" / "dracula" / "en" / "chapter-1-elevenlabs-sample"
UNSUPPORTED_ACCESSIBILITY_CLAIMS = (
    "WCAG compliant",
    "blind-user tested",
    "fully accessible",
    "fully accessible audiobook platform",
)
AUDIO_FILE_EXTENSIONS = {".aac", ".m4a", ".mp3", ".ogg", ".wav"}
ELEVENLABS_SAMPLE_PREP_FILES = (
    "sample_text.txt",
    "elevenlabs_generation_brief.md",
    "pronunciation_notes.md",
    "cost_control_plan.md",
)


@dataclass(frozen=True)
class StageResult:
    name: str
    status: str
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OnboardingResult:
    config_path: str
    mode: str
    branch: str
    allow_network: bool
    dry_run: bool
    generated_at: str
    book: dict[str, Any]
    stages: list[StageResult]
    hashes: dict[str, str]
    reports: dict[str, str]
    final_gate: dict[str, Any]
    audiobook_gate: dict[str, Any]
    codex_prompt: str


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def scalar_value(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    lowered = value.lower()
    if lowered in {"true", "yes"}:
        return True
    if lowered in {"false", "no"}:
        return False
    if lowered in {"null", "none"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def load_yaml_like_config(path: Path) -> dict[str, Any]:
    """Load the small repo-owned YAML shape without requiring PyYAML.

    The parser intentionally supports only the conservative subset used by the
    onboarding configs: nested mappings, scalar values, and scalar lists.
    """

    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any] | list[Any]]] = [(-1, root)]
    lines = path.read_text(encoding="utf-8").splitlines()

    def next_meaningful_line(start_index: int) -> tuple[int, str] | None:
        for candidate in lines[start_index + 1 :]:
            if not candidate.strip() or candidate.lstrip().startswith("#"):
                continue
            return len(candidate) - len(candidate.lstrip(" ")), candidate.strip()
        return None

    for index, raw_line in enumerate(lines):
        line_number = index + 1
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if "\t" in raw_line:
            raise ValueError(f"{path}:{line_number}: tabs are not supported in onboarding YAML.")
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        text = raw_line.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if text.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"{path}:{line_number}: list item has no list parent.")
            parent.append(scalar_value(text[2:]))
            continue

        if ":" not in text:
            raise ValueError(f"{path}:{line_number}: expected key: value syntax.")

        key, raw_value = text.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"{path}:{line_number}: empty key is not allowed.")
        if not isinstance(parent, dict):
            raise ValueError(f"{path}:{line_number}: mapping key cannot be nested inside a scalar list.")

        if raw_value.strip():
            parent[key] = scalar_value(raw_value)
        else:
            next_line = next_meaningful_line(index)
            if next_line and next_line[0] > indent:
                if next_line[1].startswith("- "):
                    child_list: list[Any] = []
                    parent[key] = child_list
                    stack.append((indent, child_list))
                else:
                    child: dict[str, Any] = {}
                    parent[key] = child
                    stack.append((indent, child))
            else:
                parent[key] = ""

    return root


def read_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    data = load_yaml_like_config(path)
    if not isinstance(data, dict):
        raise ValueError("Onboarding config must be a YAML mapping.")
    return data


def present(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return bool(text) and text.lower() not in {"unknown", "tbd", "todo", "missing", "none"}


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"true", "yes", "approved", "pass", "passed"}


def safe_slug(value: Any) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", str(value or "").strip().lower()).strip("-")
    return slug or "unknown-book"


def validate_inputs(config: dict[str, Any]) -> StageResult:
    required = ["slug", "title", "author", "language", "source_url", "source_name", "source_license"]
    missing = [field_name for field_name in required if not present(config.get(field_name))]
    if str(config.get("language", "")).strip().lower() != "english":
        missing.append("language must be english")
    status = "PASS" if not missing else "BLOCKED"
    return StageResult("input_validation", status, missing)


def validate_source_license(config: dict[str, Any]) -> StageResult:
    blockers: list[str] = []
    source_url = str(config.get("source_url", "")).strip()
    if not source_url.startswith(("https://", "http://")):
        blockers.append("source_url must be an http(s) URL.")
    if not present(config.get("source_license")):
        blockers.append("source_license is required.")
    if not present(config.get("commercial_use_evidence")):
        blockers.append("commercial-use evidence is required.")

    license_text = str(config.get("source_license", "")).lower()
    commercial_text = str(config.get("commercial_use_evidence", "")).lower()
    if present(license_text) and not any(token in license_text for token in ("public domain", "cc0", "creative commons", "gutenberg")):
        blockers.append("source_license must be explicit enough for legal review.")
    if present(commercial_text) and not any(token in commercial_text for token in ("commercial", "public domain", "allowed", "permitted")):
        blockers.append("commercial-use evidence must explicitly mention commercial permission or public-domain status.")

    return StageResult("source_url_license_validation", "PASS" if not blockers else "BLOCKED", blockers)


def load_source_text(config: dict[str, Any], *, allow_network: bool) -> StageResult:
    local_source_path = str(config.get("local_source_path", "")).strip()
    raw_text = ""
    details: dict[str, Any] = {"source_text_loaded": False, "source_text_method": "none"}
    blockers: list[str] = []

    if local_source_path:
        source_path = (ROOT / local_source_path).resolve()
        try:
            source_path.relative_to(ROOT)
        except ValueError:
            blockers.append("local_source_path must stay inside the repository.")
        if not blockers and source_path.exists() and source_path.is_file():
            raw_text = source_path.read_text(encoding="utf-8", errors="replace")
            details.update({"source_text_loaded": True, "source_text_method": "local", "local_source_path": local_source_path})
        elif not blockers:
            blockers.append(f"local_source_path was not found: {local_source_path}")
    elif allow_network:
        with urlopen(str(config.get("source_url")), timeout=15) as response:  # nosec B310 - explicit opt-in dry-run fetch.
            raw_text = response.read().decode("utf-8", errors="replace")
        details.update({"source_text_loaded": True, "source_text_method": "network"})
    else:
        blockers.append("source text requires local_source_path or --allow-network.")

    if raw_text and len(raw_text.strip()) < 120:
        blockers.append("source text is too short for onboarding verification.")
    details["raw_text_characters"] = len(raw_text)
    details["raw_text_preview"] = raw_text[:240].replace("\n", " ").strip()
    if raw_text:
        details["raw_text"] = raw_text
    return StageResult("source_text_fetch_or_local_verification", "PASS" if not blockers else "BLOCKED", blockers, details=details)


def normalize_text(raw_text: str) -> tuple[str, list[dict[str, Any]]]:
    text = re.sub(r"\r\n?", "\n", raw_text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    chapter_matches = list(re.finditer(r"(?im)^chapter\s+([ivxlcdm0-9]+|[a-z ]+)\b.*$", text))
    chapters: list[dict[str, Any]] = []
    if chapter_matches:
        for index, match in enumerate(chapter_matches, start=1):
            start = match.start()
            end = chapter_matches[index].start() if index < len(chapter_matches) else len(text)
            chapter_text = text[start:end].strip()
            chapters.append(
                {
                    "index": index,
                    "title": match.group(0).strip(),
                    "characters": len(chapter_text),
                    "preview": chapter_text[:180].replace("\n", " "),
                }
            )
    elif text:
        chapters.append({"index": 1, "title": "Preview source segment", "characters": len(text), "preview": text[:180]})
    return text, chapters


def source_stage(stages: list[StageResult]) -> StageResult:
    for stage in stages:
        if stage.name == "source_text_fetch_or_local_verification":
            return stage
    return StageResult("source_text_fetch_or_local_verification", "BLOCKED", ["source stage did not run"])


def build_hashes(config: dict[str, Any], cleaned_text: str) -> dict[str, str]:
    source_material = "\n".join(
        [
            str(config.get("source_url", "")),
            str(config.get("source_name", "")),
            str(config.get("source_license", "")),
            str(config.get("source_license_url", "")),
        ]
    )
    content_hash = sha256_text(cleaned_text)
    source_hash = sha256_text(source_material)
    provenance_hash = sha256_text("|".join([source_material, content_hash, str(config.get("commercial_use_evidence", ""))]))
    return {
        "source_hash": source_hash,
        "content_hash": content_hash,
        "provenance_hash": provenance_hash,
    }


def chapter_normalization_plan(cleaned_text: str, chapters: list[dict[str, Any]]) -> StageResult:
    blockers = []
    if not cleaned_text:
        blockers.append("cleaned_text is missing.")
    if not chapters:
        blockers.append("chapter segmentation could not be planned.")
    return StageResult(
        "chapter_normalization_plan",
        "PASS" if not blockers else "BLOCKED",
        blockers,
        details={"chapter_count": len(chapters), "chapters": chapters[:5], "full_book_generation": False},
    )


def draft_catalog_entry(config: dict[str, Any], hashes: dict[str, str]) -> StageResult:
    entry = {
        "slug": config.get("slug"),
        "title": config.get("title"),
        "author": config.get("author"),
        "language": config.get("language"),
        "is_published": False,
        "publication_status": "DRAFT_HOLD",
        "audio_enabled": False,
        "source_hash": hashes.get("source_hash"),
        "content_hash": hashes.get("content_hash"),
        "provenance_hash": hashes.get("provenance_hash"),
    }
    return StageResult("draft_catalog_entry_generation", "PASS", details=entry)


def preview_chapter_gate(chapters: list[dict[str, Any]]) -> StageResult:
    blockers = []
    if not chapters:
        blockers.append("preview chapter cannot be selected without chapter segmentation.")
    return StageResult(
        "preview_chapter_gate",
        "PASS" if not blockers else "BLOCKED",
        blockers,
        details={"preview_chapter_index": chapters[0]["index"] if chapters else None, "public_preview_enabled": False},
    )


def seo_social_metadata_draft(config: dict[str, Any]) -> StageResult:
    title = str(config.get("title", "")).strip()
    author = str(config.get("author", "")).strip()
    metadata = {
        "title": f"{title} by {author} - Earnalism draft",
        "description": f"Draft onboarding metadata for {title}. Publication remains gated until rights, QA, and owner approval pass.",
        "og_type": "book",
        "public": False,
        "sitemap_included": False,
        "book_json_ld_enabled": False,
        "audio_object_enabled": False,
    }
    return StageResult("seo_social_metadata_draft", "PASS", details=metadata)


def cover_asset_gate(config: dict[str, Any]) -> StageResult:
    cover = config.get("cover") if isinstance(config.get("cover"), dict) else {}
    blockers: list[str] = []
    warnings: list[str] = []
    front_path = str(cover.get("front_path", "")).strip()
    back_path = str(cover.get("back_path", "")).strip()

    if not truthy(cover.get("owner_designed")):
        blockers.append("owner-designed cover provenance is required before public use.")
    if not present(cover.get("provenance_note")):
        blockers.append("cover provenance note is required.")
    if str(cover.get("owner_approval_status", "")).strip().lower() != "approved":
        blockers.append("owner cover approval is required.")
    for label, relative_path in (("front", front_path), ("back", back_path)):
        if not relative_path:
            warnings.append(f"{label} cover path is missing; placeholder draft only.")
            continue
        target = ROOT / relative_path
        if not target.exists():
            blockers.append(f"{label} cover asset not found: {relative_path}")

    return StageResult(
        "cover_asset_provenance_gate",
        "PASS" if not blockers else "BLOCKED",
        blockers,
        warnings,
        {"front_path": front_path, "back_path": back_path, "public_cover_enabled": False},
    )


def audiobook_planning_packet(config: dict[str, Any]) -> StageResult:
    audiobook = config.get("audiobook") if isinstance(config.get("audiobook"), dict) else {}
    blockers = ["public audiobook release is blocked by default."]
    if truthy(audiobook.get("public_target")) or truthy(audiobook.get("public_audio_target")):
        blockers.append("public audiobook target is not allowed during English book onboarding.")
    if not present(audiobook.get("derivative_rights_status")):
        blockers.append("derivative audiobook rights evidence is missing.")
    if not present(audiobook.get("model_voice_license_status")):
        blockers.append("model/voice license evidence is missing.")
    return StageResult(
        "audiobook_planning_packet",
        "BLOCKED",
        blockers,
        details={
            "audio_enabled": False,
            "public_audio_release_status": PUBLIC_AUDIO_RELEASE_BLOCKED,
            "listen_now_cta": False,
            "audio_object_metadata": False,
        },
    )


def selected_model_candidate(config: dict[str, Any]) -> str:
    audiobook = config.get("audiobook") if isinstance(config.get("audiobook"), dict) else {}
    sync_config = config.get("audiobook_sync") if isinstance(config.get("audiobook_sync"), dict) else {}
    return safe_slug(
        audiobook.get("selected_model_candidate")
        or sync_config.get("model_candidate")
        or "kokoro"
    )


def selected_provider_candidate(config: dict[str, Any]) -> str:
    provider_config = config.get("audiobook_provider_eval") if isinstance(config.get("audiobook_provider_eval"), dict) else {}
    return safe_slug(provider_config.get("preferred_provider") or "elevenlabs")


def tts_model_license_and_suitability_review(config: dict[str, Any]) -> StageResult:
    audiobook = config.get("audiobook") if isinstance(config.get("audiobook"), dict) else {}
    sync_config = config.get("audiobook_sync") if isinstance(config.get("audiobook_sync"), dict) else {}
    require_review = truthy(audiobook.get("require_tts_model_license_review")) or truthy(
        sync_config.get("require_model_eligibility")
    )
    decisions = review_tts_candidates()
    selected_id = selected_model_candidate(config)
    selected = selected_candidate_decision(selected_id, decisions)
    blockers: list[str] = []
    if require_review and selected.decision_status != "ELIGIBLE_INTERNAL_EVAL":
        blockers.append(
            f"selected model `{selected_id}` is not eligible for real internal generation: {selected.decision_status}."
        )
    blockers.extend(selected.issues)
    details = {
        "stage_name": TTS_MODEL_LICENSE_STAGE,
        "selected_model_candidate": selected_id,
        "selected_model_display_name": selected.candidate.get("display_name", selected_id),
        "selected_model_decision": selected.decision_status,
        "selected_model_internal_eval_status": selected.internal_eval_status,
        "selected_voice_id": selected.candidate.get("selected_voice_id", ""),
        "selected_voice_display_name": selected.candidate.get("selected_voice_display_name", ""),
        "selected_voice_internal_eval_status": selected.candidate.get("selected_voice_internal_eval_status", ""),
        "selected_voice_blockers": selected.candidate.get("selected_voice_blockers", ""),
        "model_generation": selected.internal_generation_status,
        "public_production_status": selected.public_production_status,
        "public_audio_allowed": False,
        "listen_now_cta_allowed": False,
        "audio_object_metadata_allowed": False,
        "candidate_count": len(decisions),
        "eligible_internal_eval_count": sum(1 for decision in decisions if decision.internal_eval_status == "ELIGIBLE_INTERNAL_EVAL"),
        "hold_count": sum(1 for decision in decisions if decision.internal_eval_status in {"HOLD_LICENSE_REVIEW", "HOLD_VOICE_RIGHTS", "HOLD_OWNER_REVIEW"}),
        "blocked_count": sum(1 for decision in decisions if decision.decision_status == "BLOCKED"),
        "candidates": tts_decision_payload(decisions)["candidates"],
    }
    return StageResult(TTS_MODEL_LICENSE_STAGE, selected.decision_status, blockers, selected.warnings, details)


def tts_voice_rights_internal_eval_review(config: dict[str, Any]) -> StageResult:
    decisions = review_tts_candidates()
    selected_id = selected_model_candidate(config)
    selected = selected_candidate_decision(selected_id, decisions)
    blockers: list[str] = []
    if selected.internal_eval_status != "ELIGIBLE_INTERNAL_EVAL":
        blockers.append(
            f"selected model `{selected_id}` is not eligible for internal evaluation: {selected.internal_eval_status}."
        )
    for issue in selected.issues:
        if "voice" in issue.lower() or "speaker" in issue.lower() or "internal_eval" in issue.lower() or "owner internal" in issue.lower() or "legal internal" in issue.lower():
            blockers.append(issue)
    details = {
        "stage_name": TTS_VOICE_RIGHTS_STAGE,
        "selected_model_candidate": selected_id,
        "selected_model_display_name": selected.candidate.get("display_name", selected_id),
        "selected_model_internal_eval_status": selected.internal_eval_status,
        "selected_voice_id": selected.candidate.get("selected_voice_id", ""),
        "selected_voice_display_name": selected.candidate.get("selected_voice_display_name", ""),
        "selected_voice_source_url": selected.candidate.get("selected_voice_source_url", ""),
        "selected_voice_license_evidence_url": selected.candidate.get("selected_voice_license_evidence_url", ""),
        "selected_voice_rights_summary": selected.candidate.get("selected_voice_rights_summary", ""),
        "selected_voice_synthetic_status": selected.candidate.get("selected_voice_synthetic_status", ""),
        "selected_voice_real_person_risk": selected.candidate.get("selected_voice_real_person_risk", ""),
        "selected_voice_attribution_requirement": selected.candidate.get("selected_voice_attribution_requirement", ""),
        "selected_voice_internal_eval_status": selected.candidate.get("selected_voice_internal_eval_status", ""),
        "owner_selected_voice_approval_status": selected.candidate.get("owner_selected_voice_approval_status", ""),
        "legal_selected_voice_review_status": selected.candidate.get("legal_selected_voice_review_status", ""),
        "selected_voice_blockers": selected.candidate.get("selected_voice_blockers", ""),
        "voice_rights_evidence_url": selected.candidate.get("voice_rights_evidence_url", ""),
        "voice_rights_summary": selected.candidate.get("voice_rights_summary", ""),
        "speaker_identity_status": selected.candidate.get("speaker_identity_status", ""),
        "synthetic_voice_status": selected.candidate.get("synthetic_voice_status", ""),
        "real_person_voice_clone_risk": selected.candidate.get("real_person_voice_clone_risk", ""),
        "internal_eval_allowed": bool(selected.candidate.get("internal_eval_allowed")),
        "owner_internal_eval_approval_status": selected.candidate.get("owner_internal_eval_approval_status", ""),
        "legal_internal_eval_review_status": selected.candidate.get("legal_internal_eval_review_status", ""),
        "public_audio_allowed": False,
        "real_audio_generation_allowed": False,
        "public_production_status": selected.public_production_status,
    }
    status = selected.internal_eval_status if not blockers else selected.internal_eval_status
    return StageResult(TTS_VOICE_RIGHTS_STAGE, status, dedupe_strings(blockers), selected.warnings, details)


def licensed_provider_tts_internal_eval_review(config: dict[str, Any]) -> StageResult:
    provider_config = config.get("audiobook_provider_eval") if isinstance(config.get("audiobook_provider_eval"), dict) else {}
    if provider_config.get("enabled") is False:
        return StageResult(
            TTS_PROVIDER_INTERNAL_EVAL_STAGE,
            "SKIPPED",
            warnings=["audiobook_provider_eval.enabled is false; provider internal-eval evidence was not reviewed."],
            details={
                "public_audio_allowed": False,
                "public_audio_release_status": PUBLIC_AUDIO_RELEASE_BLOCKED,
                "public_production_status": "PRODUCTION_BLOCKED",
            },
        )

    decisions = review_provider_candidates()
    selected_id = selected_provider_candidate(config)
    selected = selected_provider_decision(selected_id, decisions)
    configured_voice_id = str(provider_config.get("selected_voice_id") or "").strip()
    selected_voice_id = configured_voice_id
    if not selected_voice_id or selected_voice_id == "OWNER_SELECTION_REQUIRED":
        selected_voice_id = str(selected.provider.get("selected_voice_id") or "").strip()
    blockers: list[str] = []

    if selected.internal_eval_status != "ELIGIBLE_INTERNAL_EVAL":
        blockers.append(
            f"selected provider `{selected_id}` is not eligible for internal evaluation: {selected.internal_eval_status}."
        )
    if not selected_voice_id or selected_voice_id == "OWNER_SELECTION_REQUIRED":
        blockers.append("selected provider voice is not selected.")
    if truthy(provider_config.get("beta_features_allowed")):
        blockers.append("beta provider features are not allowed for this stage.")
    if truthy(provider_config.get("public_release_target")):
        blockers.append("public provider-audio release target is not allowed during onboarding.")
    if truthy(provider_config.get("paid_plan_evidence_required")) and not present(
        selected.provider.get("paid_plan_evidence_url")
    ):
        blockers.append("paid provider plan evidence is required before internal evaluation.")
    if truthy(provider_config.get("commercial_use_evidence_required")) and str(
        selected.provider.get("standalone_audio_distribution_allowed", "")
    ).upper() != "ALLOWED":
        blockers.append("commercial standalone audio evidence is not approved.")
    if truthy(provider_config.get("owner_approval_required")) and str(
        selected.provider.get("owner_approval_status", "")
    ).upper() != "APPROVED":
        blockers.append("owner approval is required before provider internal evaluation.")
    if truthy(provider_config.get("legal_review_required")) and str(
        selected.provider.get("legal_review_status", "")
    ).upper() != "APPROVED":
        blockers.append("legal/internal review is required before provider internal evaluation.")
    blockers.extend(selected.issues)

    details = {
        "stage_name": TTS_PROVIDER_INTERNAL_EVAL_STAGE,
        "selected_provider_id": selected_id,
        "selected_provider_display_name": selected.provider.get("display_name", selected_id),
        "selected_provider_decision": selected.decision_status,
        "selected_provider_internal_eval_status": selected.internal_eval_status,
        "selected_provider_internal_generation_status": selected.internal_generation_status,
        "selected_provider_production_status": selected.public_production_status,
        "selected_provider_voice_id": selected_voice_id,
        "selected_provider_voice_display_name": (
            provider_config.get("selected_voice_display_name") or selected.provider.get("selected_voice_display_name", "")
        ),
        "selected_provider_voice_type": selected.provider.get("selected_voice_type", "unknown"),
        "selected_provider_voice_rights_summary": selected.provider.get("selected_voice_rights_summary", ""),
        "selected_provider_voice_attribution_requirement": selected.provider.get("selected_voice_attribution_requirement", ""),
        "selected_provider_voice_restrictions": selected.provider.get("selected_voice_restrictions", ""),
        "standalone_audio_distribution_allowed": selected.provider.get("standalone_audio_distribution_allowed", ""),
        "standalone_audio_distribution_evidence": selected.provider.get("standalone_audio_distribution_evidence", ""),
        "paid_plan_required": bool(selected.provider.get("paid_plan_required")),
        "plan_evidence_status": selected.provider.get("plan_evidence_status", ""),
        "paid_plan_evidence_required": bool(provider_config.get("paid_plan_evidence_required", False)),
        "commercial_internal_eval_permission": selected.provider.get("commercial_internal_eval_permission", ""),
        "commercial_use_evidence_required": bool(provider_config.get("commercial_use_evidence_required", False)),
        "beta_features_allowed": bool(provider_config.get("beta_features_allowed", False)),
        "beta_features_excluded_evidence": selected.provider.get("beta_features_excluded_evidence", ""),
        "provider_terms_review_status": selected.provider.get("provider_terms_review_status", ""),
        "data_retention_review_status": selected.provider.get("data_retention_review_status", ""),
        "provider_blockers": dedupe_strings(blockers),
        "public_release_target": bool(provider_config.get("public_release_target", False)),
        "public_audio_allowed": False,
        "listen_now_cta_allowed": False,
        "audio_object_metadata_allowed": False,
        "real_audio_generation_allowed": False,
        "paid_provider_api_called": False,
        "provider_count": len(decisions),
        "eligible_internal_eval_count": sum(
            1 for decision in decisions if decision.internal_eval_status == "ELIGIBLE_INTERNAL_EVAL"
        ),
        "hold_count": sum(1 for decision in decisions if decision.internal_eval_status == "HOLD_PROVIDER_REVIEW"),
        "blocked_count": sum(1 for decision in decisions if decision.internal_eval_status == "BLOCKED"),
        "providers": provider_decision_payload(decisions)["providers"],
    }
    return StageResult(
        TTS_PROVIDER_INTERNAL_EVAL_STAGE,
        selected.internal_eval_status,
        dedupe_strings(blockers),
        selected.warnings,
        details,
    )


def imported_elevenlabs_audio_files() -> list[Path]:
    imported_dir = ELEVENLABS_DRACULA_SAMPLE_DIR / "imported_audio"
    if not imported_dir.exists():
        return []
    return sorted(
        path for path in imported_dir.rglob("*") if path.is_file() and path.suffix.lower() in AUDIO_FILE_EXTENSIONS
    )


def elevenlabs_internal_sample_prep_and_import(config: dict[str, Any]) -> StageResult:
    provider_config = config.get("audiobook_provider_eval") if isinstance(config.get("audiobook_provider_eval"), dict) else {}
    selected_provider_id = selected_provider_candidate(config)
    if selected_provider_id != "elevenlabs":
        return StageResult(
            ELEVENLABS_INTERNAL_SAMPLE_STAGE,
            "SKIPPED",
            warnings=["selected provider is not ElevenLabs; Dracula ElevenLabs sample prep was skipped."],
            details={"public_audio_allowed": False, "public_audio_release_status": PUBLIC_AUDIO_RELEASE_BLOCKED},
        )

    decisions = review_provider_candidates()
    selected = selected_provider_decision("elevenlabs", decisions)
    missing_prep_files = [
        filename for filename in ELEVENLABS_SAMPLE_PREP_FILES if not (ELEVENLABS_DRACULA_SAMPLE_DIR / filename).exists()
    ]
    blockers: list[str] = []
    if selected.internal_eval_status != "ELIGIBLE_INTERNAL_EVAL":
        blockers.append(
            f"ElevenLabs remains {selected.internal_eval_status}; complete owner/legal evidence before manual sample import approval."
        )
    blockers.extend(selected.issues)
    if missing_prep_files:
        blockers.append("sample prep files are missing: " + ", ".join(missing_prep_files))
    if truthy(provider_config.get("public_release_target")):
        blockers.append("public ElevenLabs sample release target is not allowed.")

    audio_files = imported_elevenlabs_audio_files()
    import_result: dict[str, Any] = {}
    import_status = "NOT_IMPORTED_YET"
    sync_status = ELEVENLABS_HOLD_SYNC_QA_REQUIRED
    if audio_files:
        imported_manifest_path = ELEVENLABS_DRACULA_SAMPLE_DIR / "imported_audio_manifest.json"
        sync_manifest_path = ELEVENLABS_DRACULA_SAMPLE_DIR / "sync_manifest.json"
        if imported_manifest_path.exists() and sync_manifest_path.exists():
            imported_manifest = json.loads(imported_manifest_path.read_text(encoding="utf-8"))
            sync_manifest = json.loads(sync_manifest_path.read_text(encoding="utf-8"))
            import_status = str(imported_manifest.get("audio_status") or INTERNAL_SAMPLE_ONLY)
            sync_status = str(sync_manifest.get("sync_status") or ELEVENLABS_HOLD_SYNC_QA_REQUIRED)
            import_result = {
                "status": import_status,
                "sync_status": sync_status,
                "audio_hash": imported_manifest.get("audio_hash"),
                "imported_audio_manifest_path": str(imported_manifest_path.relative_to(ROOT)),
                "sync_manifest_path": str(sync_manifest_path.relative_to(ROOT)),
            }
        else:
            try:
                import_result = run_elevenlabs_sample_import(
                    book_slug="dracula",
                    chapter="1",
                    sample_dir=ELEVENLABS_DRACULA_SAMPLE_DIR,
                )
                import_status = str(import_result.get("status") or INTERNAL_SAMPLE_ONLY)
                sync_status = str(import_result.get("sync_status") or ELEVENLABS_HOLD_SYNC_QA_REQUIRED)
            except Exception as exc:  # noqa: BLE001 - stage records import validation failure as a blocker.
                blockers.append(f"manual ElevenLabs audio import is invalid: {exc}")
                import_status = "IMPORT_VALIDATION_FAILED"

    status = "SAMPLE_PREP_ONLY"
    if audio_files and not blockers:
        status = INTERNAL_SAMPLE_ONLY
    elif blockers:
        status = "HOLD_PROVIDER_REVIEW"

    return StageResult(
        ELEVENLABS_INTERNAL_SAMPLE_STAGE,
        status,
        dedupe_strings(blockers),
        selected.warnings,
        {
            "provider": "elevenlabs",
            "provider_decision": selected.decision_status,
            "provider_internal_eval_status": selected.internal_eval_status,
            "provider_production_status": selected.public_production_status,
            "evidence_path": str(ELEVENLABS_EVIDENCE_PATH.relative_to(ROOT)),
            "evidence_file_exists": ELEVENLABS_EVIDENCE_PATH.exists(),
            "selected_voice_name": "Rachel",
            "selected_voice_id": "21m00Tcm4TlvDq8ikWAM",
            "selected_voice_type": "platform_voice",
            "sample_dir": str(ELEVENLABS_DRACULA_SAMPLE_DIR.relative_to(ROOT)),
            "sample_prep_files": [
                str((ELEVENLABS_DRACULA_SAMPLE_DIR / filename).relative_to(ROOT))
                for filename in ELEVENLABS_SAMPLE_PREP_FILES
                if (ELEVENLABS_DRACULA_SAMPLE_DIR / filename).exists()
            ],
            "missing_sample_prep_files": missing_prep_files,
            "imported_audio_exists": bool(audio_files),
            "imported_audio_count": len(audio_files),
            "import_status": import_status,
            "imported_audio_manifest_path": import_result.get("imported_audio_manifest_path"),
            "audio_hash": import_result.get("audio_hash"),
            "sync_status": sync_status,
            "sync_manifest_path": import_result.get("sync_manifest_path"),
            "qa_status": "HOLD_OWNER_LISTENING_QA_REQUIRED",
            "sample_duration_target": "2-3 minutes",
            "first_pass_duration_target": "30-45 seconds",
            "provider_api_called": False,
            "audio_generated_by_repo": False,
            "full_chapter_generation_allowed": False,
            "full_book_generation_allowed": False,
            "public_audio_allowed": False,
            "public_audio_release_status": PUBLIC_AUDIO_RELEASE_BLOCKED,
            "production_status": "PRODUCTION_BLOCKED",
            "listening_cta_allowed": False,
            "audio_metadata_allowed": False,
        },
    )


def automated_audiobook_chapter_pipeline_dry_run(config: dict[str, Any]) -> StageResult:
    sync_config = config.get("audiobook_sync") if isinstance(config.get("audiobook_sync"), dict) else {}
    provider_config = config.get("audiobook_provider_eval") if isinstance(config.get("audiobook_provider_eval"), dict) else {}
    slug = safe_slug(config.get("slug"))
    language = str(sync_config.get("language") or "en").strip().lower()
    chapter = str(sync_config.get("chapter") or "1")
    provider = safe_slug(provider_config.get("preferred_provider") or "elevenlabs")
    selected_voice_id = str(provider_config.get("selected_voice_id") or "").strip()
    if not selected_voice_id or selected_voice_id == "OWNER_SELECTION_REQUIRED":
        selected_voice_id = "21m00Tcm4TlvDq8ikWAM"
    selected_voice_name = str(provider_config.get("selected_voice_display_name") or "Rachel").strip() or "Rachel"

    try:
        result = run_chapter_pipeline(
            book_slug=slug,
            language=language,
            chapter=chapter,
            provider=provider,
            voice_id=selected_voice_id,
            voice_name=selected_voice_name,
            mode="dry-run",
            execute=False,
            max_cost_inr=None,
            max_chunks=None,
            write_root_reports=False,
        )
    except Exception as exc:  # noqa: BLE001 - dry-run failure must be reported as a stage blocker.
        return StageResult(
            AUTOMATED_AUDIOBOOK_CHAPTER_PIPELINE_STAGE,
            "BLOCKED",
            [f"automated audiobook chapter pipeline dry-run failed: {exc}"],
            details={
                "public_audio_release_status": PUBLIC_AUDIO_RELEASE_BLOCKED,
                "public_audio_allowed": False,
                "production_status": "PRODUCTION_BLOCKED",
                "generation_status": CHAPTER_PIPELINE_BLOCKED_REAL_GENERATION,
            },
        )

    blockers: list[str] = []
    if result.status != CHAPTER_PIPELINE_DRY_RUN_READY:
        blockers.append(f"chapter pipeline dry-run did not reach DRY_RUN_READY: {result.status}")
    if result.public_release.get("frontend_public_audio_files") or result.public_release.get("frontend_build_audio_files"):
        blockers.append("public/build audio-like files are present.")

    return StageResult(
        AUTOMATED_AUDIOBOOK_CHAPTER_PIPELINE_STAGE,
        CHAPTER_PIPELINE_DRY_RUN_READY if not blockers else "HOLD_AUDIOBOOK_PIPELINE_QA",
        blockers,
        details={
            "book_slug": result.book_slug,
            "language": result.language,
            "chapter": result.chapter,
            "provider": result.provider,
            "voice_id": result.voice_id,
            "voice_name": result.voice_name,
            "output_dir": str(result.output_dir.relative_to(ROOT)),
            "sanitation_status": "PASS",
            "clean_narration_file_path": result.files.get("narration_text"),
            "sync_source_file_path": result.files.get("sync_source"),
            "sentence_map_path": result.files.get("sentence_map"),
            "chunk_manifest_path": result.files.get("chunk_manifest"),
            "generated_audio_manifest_path": result.files.get("generated_audio_manifest"),
            "sync_manifest_path": result.files.get("sync_manifest"),
            "qa_packet_path": result.files.get("qa_packet"),
            "cost_estimate": result.cost_estimate,
            "provider_gate_status": result.provider_gate.get("internal_generation_status"),
            "provider_gate": result.provider_gate,
            "generation_status": result.generation.get("generation_status"),
            "provider_api_called": result.generation.get("provider_api_called"),
            "audio_generated_by_repo": result.generation.get("audio_generated_by_repo"),
            "sync_status": "HOLD_SYNC_QA_REQUIRED",
            "public_release_status": PUBLIC_AUDIO_RELEASE_BLOCKED,
            "public_audio_allowed": False,
            "production_status": "PRODUCTION_BLOCKED",
            "listening_cta_allowed": False,
            "audio_metadata_allowed": False,
            "full_book_generation_allowed": False,
        },
    )


def dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def audiobook_sync_dry_run_stage(config: dict[str, Any]) -> StageResult:
    sync_config = config.get("audiobook_sync") if isinstance(config.get("audiobook_sync"), dict) else {}
    enabled = sync_config.get("enabled", True)
    if enabled is False:
        return StageResult(
            "audiobook_sync_dry_run_stage",
            "SKIPPED",
            warnings=["audiobook_sync.enabled is false; sync dry-run evidence was not generated."],
            details={"public_audio_release_status": PUBLIC_AUDIO_RELEASE_BLOCKED, "public_audio_allowed": False},
        )

    slug = safe_slug(config.get("slug"))
    chapter = str(sync_config.get("chapter") or "1")
    language = str(sync_config.get("language") or "en").strip().lower()
    model_candidate = selected_model_candidate(config)
    output_dir = ROOT / "internal" / "audiobook_lab" / slug / language / str(int(chapter))
    result = run_audiobook_sync_pipeline(
        book_slug=slug,
        chapter=chapter,
        language=language,
        model_candidate=model_candidate,
        mode="dry-run",
        output_dir=output_dir,
        no_network=True,
        write_root_reports=False,
    )
    blockers = []
    if result.status != "DRY_RUN_COMPLETE":
        blockers.append(f"sync dry-run did not complete: {result.status}")
    if result.blockers:
        blockers.append("sync release evidence remains HOLD; public audio cannot be released.")
    if SYNC_PUBLIC_AUDIO_RELEASE_BLOCKED != PUBLIC_AUDIO_RELEASE_BLOCKED:
        blockers.append("sync pipeline public-audio status does not match onboarding gate.")

    return StageResult(
        "audiobook_sync_dry_run_stage",
        "INTERNAL_DRY_RUN_ONLY" if not blockers else "HOLD_SYNC_QA_REQUIRED",
        blockers,
        warnings=result.warnings,
        details={
            "enabled": True,
            "chapter": result.chapter,
            "language": result.language,
            "model_candidate": result.model_candidate,
            "model_generation": "HOLD_VOICE_RIGHTS",
            "sync_level": str(sync_config.get("sync_level") or "sentence"),
            "status": result.status,
            "public_release_target": bool(sync_config.get("public_release_target", False)),
            "public_audio_release_status": PUBLIC_AUDIO_RELEASE_BLOCKED,
            "public_audio_allowed": False,
            "listen_now_cta": False,
            "audio_object_metadata": False,
            "real_audio_generated": False,
            "internal_output_dir": str(result.output_dir.relative_to(ROOT)),
            "internal_sync_manifest_path": str(result.sync_manifest_path.relative_to(ROOT)),
            "internal_qa_packet_path": str(result.qa_packet_path.relative_to(ROOT)),
            "internal_release_gate_report_path": str(result.release_gate_report_path.relative_to(ROOT)),
            "scoped_sync_manifest_path": f"output/onboarding/{slug}/audiobook_sync/sync_manifest.json",
            "sync_item_count": len(result.sync_items),
            "blocker_count": len(result.blockers),
        },
    )


def narration_qa_gate(config: dict[str, Any]) -> StageResult:
    audiobook = config.get("audiobook") if isinstance(config.get("audiobook"), dict) else {}
    blockers = []
    if str(audiobook.get("human_review_status", "")).strip().lower() != "approved":
        blockers.append("human narration QA is missing or not approved.")
    if str(audiobook.get("accessibility_listening_status", "")).strip().lower() != "approved":
        blockers.append("accessibility listening QA is missing or not approved.")
    return StageResult("narration_qa_gate", "PASS" if not blockers else "BLOCKED", blockers)


def audiobook_legal_accessibility_gate(config: dict[str, Any]) -> StageResult:
    audiobook = config.get("audiobook") if isinstance(config.get("audiobook"), dict) else {}
    blockers = [
        "public audio remains PUBLIC_AUDIO_RELEASE_BLOCKED until separate owner/legal/accessibility release approval."
    ]
    for field_name in ("rollback_approval_status", "owner_legal_approval_status", "refund_support_readiness"):
        if not truthy(audiobook.get(field_name)):
            blockers.append(f"{field_name} is required before audiobook release.")
    return StageResult("audiobook_legal_accessibility_compliance_gate", "BLOCKED", blockers)


def payment_publication_guardrails(config: dict[str, Any]) -> StageResult:
    blockers = []
    if truthy(config.get("publish_now")):
        blockers.append("publish_now is not supported by this orchestrator.")
    if truthy(config.get("change_payment_settings")):
        blockers.append("payment setting changes are not supported by this orchestrator.")
    if str(config.get("owner_approval_status", "")).strip().lower() != "approved":
        blockers.append("owner publication approval is required.")
    return StageResult(
        "payment_publication_guardrails",
        "PASS" if not blockers else "BLOCKED",
        blockers,
        details={"payment_settings_changed": False, "public_publish_actions": 0, "razorpay_called": False},
    )


def public_claims_audit(config: dict[str, Any], reports_text: str) -> StageResult:
    blockers: list[str] = []
    text = "\n".join([json.dumps(config, ensure_ascii=False), reports_text])
    for phrase in UNSUPPORTED_ACCESSIBILITY_CLAIMS:
        if phrase.lower() in text.lower():
            blockers.append(f"unsupported accessibility claim detected: {phrase}")
    public_claims = str(config.get("public_claims", "")).lower()
    if "listen now" in public_claims or "audiobook live" in public_claims:
        blockers.append("public audio claim is not allowed.")
    return StageResult(
        "public_claims_audit",
        "PASS" if not blockers else "BLOCKED",
        blockers,
        details={"unsupported_accessibility_claims": False, "listen_now_claim": False},
    )


def build_regression_command_runner() -> StageResult:
    commands = [
        "npm run controlled-publication:precheck",
        "npm run catalog:audit",
        "npm run launch:audio-audit",
        "npm run audiobook:release-gate",
        "npm run launch:seo-audit",
        "npm run launch:social-preview-audit",
        "npm run launch:payment-smoke:test-mode",
        "npm run regression -- modules/11-seo.test.js modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js",
        "npm --prefix frontend run build",
    ]
    return StageResult("build_regression_command_runner", "PLAN_ONLY", details={"commands": commands, "executed": False})


def collect_blockers(stages: list[StageResult]) -> list[str]:
    blockers: list[str] = []
    for stage in stages:
        blockers.extend(f"{stage.name}: {blocker}" for blocker in stage.blockers)
    return blockers


def final_gate(config: dict[str, Any], stages: list[StageResult]) -> dict[str, Any]:
    blockers = collect_blockers(stages)
    source_ready = all(stage.status != "BLOCKED" for stage in stages[:5])
    status = PUBLICATION_DRAFT_REVIEW if source_ready and not blockers else PUBLICATION_HOLD
    return {
        "status": status,
        "go_no_go": "HOLD" if blockers else "HOLD_OWNER_REVIEW_REQUIRED",
        "public_publish_allowed": False,
        "is_published": False,
        "start_reading_cta_allowed": False,
        "sitemap_inclusion_allowed": False,
        "owner_approval_status": config.get("owner_approval_status", "OWNER_APPROVAL_REQUIRED"),
        "blocker_count": len(blockers),
        "blockers": blockers,
    }


def audiobook_gate(stages: list[StageResult]) -> dict[str, Any]:
    audio_blockers = [
        blocker
        for stage in stages
        if (
            "audiobook" in stage.name.lower()
            or "narration" in stage.name.lower()
            or stage.name in {TTS_MODEL_LICENSE_STAGE, TTS_VOICE_RIGHTS_STAGE, TTS_PROVIDER_INTERNAL_EVAL_STAGE}
            or stage.name == ELEVENLABS_INTERNAL_SAMPLE_STAGE
            or stage.name == AUTOMATED_AUDIOBOOK_CHAPTER_PIPELINE_STAGE
        )
        for blocker in stage.blockers
    ]
    provider = selected_provider_status(stages)
    elevenlabs_sample = elevenlabs_sample_status(stages)
    return {
        "status": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "sync_status": sync_status(stages),
        "elevenlabs_sample_status": elevenlabs_sample.get("status"),
        "elevenlabs_sample_import_status": elevenlabs_sample.get("import_status"),
        "elevenlabs_sample_sync_status": elevenlabs_sample.get("sync_status"),
        "elevenlabs_sample_public_audio_allowed": False,
        "model_generation": model_generation_status(stages),
        "selected_model_candidate": selected_model_status(stages).get("selected_model_candidate"),
        "selected_model_decision": selected_model_status(stages).get("selected_model_decision"),
        "selected_model_internal_eval_status": selected_model_status(stages).get("selected_model_internal_eval_status"),
        "selected_voice_id": selected_model_status(stages).get("selected_voice_id"),
        "selected_voice_internal_eval_status": selected_model_status(stages).get("selected_voice_internal_eval_status"),
        "selected_voice_blockers": selected_model_status(stages).get("selected_voice_blockers"),
        "provider_internal_eval_status": provider.get("selected_provider_internal_eval_status"),
        "selected_provider_id": provider.get("selected_provider_id"),
        "selected_provider_decision": provider.get("selected_provider_decision"),
        "selected_provider_production_status": provider.get("selected_provider_production_status"),
        "selected_provider_internal_generation_status": provider.get("selected_provider_internal_generation_status"),
        "public_audio_publish_allowed": False,
        "audio_enabled": False,
        "listen_now_cta": False,
        "audio_object_metadata": False,
        "blocker_count": len(audio_blockers),
        "blockers": audio_blockers,
    }


def sync_status(stages: list[StageResult]) -> str:
    sample = elevenlabs_sample_status(stages)
    if sample.get("sync_status"):
        return str(sample.get("sync_status"))
    for stage in stages:
        if stage.name == "audiobook_sync_dry_run_stage":
            return stage.status
    return "HOLD_SYNC_QA_REQUIRED"


def elevenlabs_sample_status(stages: list[StageResult]) -> dict[str, Any]:
    for stage in stages:
        if stage.name == ELEVENLABS_INTERNAL_SAMPLE_STAGE:
            details = dict(stage.details)
            details["status"] = stage.status
            return details
    return {
        "status": "NOT_CONFIGURED",
        "import_status": "NOT_IMPORTED_YET",
        "sync_status": "HOLD_SYNC_QA_REQUIRED",
    }


def selected_model_status(stages: list[StageResult]) -> dict[str, Any]:
    for stage in stages:
        if stage.name == TTS_MODEL_LICENSE_STAGE:
            return stage.details
    return {
        "selected_model_candidate": "unknown",
        "selected_model_decision": "HOLD_LICENSE_REVIEW",
        "selected_model_internal_eval_status": "HOLD_VOICE_RIGHTS",
        "selected_voice_id": "OWNER_SELECTION_REQUIRED",
        "selected_voice_internal_eval_status": "HOLD_VOICE_RIGHTS",
        "selected_voice_blockers": "selected voice evidence is missing.",
        "model_generation": "HOLD_LICENSE_REVIEW",
    }


def selected_provider_status(stages: list[StageResult]) -> dict[str, Any]:
    for stage in stages:
        if stage.name == TTS_PROVIDER_INTERNAL_EVAL_STAGE:
            return stage.details
    return {
        "selected_provider_id": "elevenlabs",
        "selected_provider_decision": "HOLD_PROVIDER_REVIEW",
        "selected_provider_internal_eval_status": "HOLD_PROVIDER_REVIEW",
        "selected_provider_internal_generation_status": "HOLD_PROVIDER_REVIEW",
        "selected_provider_production_status": "PRODUCTION_BLOCKED",
    }


def model_generation_status(stages: list[StageResult]) -> str:
    return str(selected_model_status(stages).get("model_generation") or "HOLD_LICENSE_REVIEW")


def report_header(config: dict[str, Any], result: OnboardingResult, title: str) -> str:
    return "\n".join(
        [
            f"# {title}",
            "",
            f"- Book: {config.get('title', 'Unknown')}",
            f"- Slug: `{config.get('slug', 'unknown')}`",
            f"- Generated: {result.generated_at}",
            f"- Mode: `{result.mode}`",
            f"- Dry run: `{str(result.dry_run).lower()}`",
            "",
        ]
    )


def markdown_table(rows: list[tuple[str, str, str]]) -> str:
    lines = ["| Item | Status | Notes |", "| --- | --- | --- |"]
    lines.extend(f"| {name} | {status} | {notes} |" for name, status, notes in rows)
    return "\n".join(lines) + "\n"


def result_to_json(result: OnboardingResult) -> dict[str, Any]:
    return {
        "config_path": result.config_path,
        "mode": result.mode,
        "branch": result.branch,
        "allow_network": result.allow_network,
        "dry_run": result.dry_run,
        "generated_at": result.generated_at,
        "book": result.book,
        "stages": [
            {
                "name": stage.name,
                "status": stage.status,
                "blockers": stage.blockers,
                "warnings": stage.warnings,
                "details": stage.details,
            }
            for stage in result.stages
        ],
        "hashes": result.hashes,
        "final_gate": result.final_gate,
        "audiobook_gate": result.audiobook_gate,
        "reports": result.reports,
        "codex_prompt": result.codex_prompt,
    }


def copy_audiobook_sync_artifacts(result: OnboardingResult, scoped_output_dir: Path) -> dict[str, Path]:
    sync_stage = next((stage for stage in result.stages if stage.name == "audiobook_sync_dry_run_stage"), None)
    if not sync_stage:
        return {}
    sync_output_dir = scoped_output_dir / "audiobook_sync"
    sync_output_dir.mkdir(parents=True, exist_ok=True)
    copied: dict[str, Path] = {}
    source_fields = {
        "sync_manifest.json": "internal_sync_manifest_path",
        "qa_packet.json": "internal_qa_packet_path",
        "release_gate_report.json": "internal_release_gate_report_path",
    }
    for filename, detail_key in source_fields.items():
        relative_path = sync_stage.details.get(detail_key)
        if not relative_path:
            continue
        source_path = ROOT / str(relative_path)
        if not source_path.exists():
            continue
        target_path = sync_output_dir / filename
        target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
        copied[f"output/onboarding/{safe_slug(result.book.get('slug'))}/audiobook_sync/{filename}"] = target_path
    return copied


def write_tts_license_artifacts(scoped_output_dir: Path) -> dict[str, Path]:
    decisions = review_tts_candidates()
    return write_tts_model_reports(decisions, output_dir=scoped_output_dir)


def write_tts_provider_artifacts(scoped_output_dir: Path) -> dict[str, Path]:
    decisions = review_provider_candidates()
    return write_tts_provider_reports(decisions, output_dir=scoped_output_dir)


def write_reports(
    result: OnboardingResult,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    write_root_reports: bool = True,
) -> dict[str, Path]:
    slug = safe_slug(result.book.get("slug"))
    scoped_output_dir = output_dir / slug
    scoped_output_dir.mkdir(parents=True, exist_ok=True)
    latest_output_dir = LATEST_OUTPUT_DIR
    latest_output_dir.mkdir(parents=True, exist_ok=True)
    if write_root_reports:
        CODEX_PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)

    config = result.book
    stage_rows = [
        (
            stage.name,
            stage.status,
            "; ".join(stage.blockers[:3]) if stage.blockers else ("; ".join(stage.warnings[:2]) if stage.warnings else "No blocker."),
        )
        for stage in result.stages
    ]

    orchestration = (
        report_header(config, result, "Book Onboarding Orchestration Report")
        + markdown_table(stage_rows)
        + "\n## Final Gate\n\n"
        + f"- Decision: `{result.final_gate['go_no_go']}`\n"
        + f"- Publication status: `{result.final_gate['status']}`\n"
        + f"- Public publish allowed: `{str(result.final_gate['public_publish_allowed']).lower()}`\n"
        + f"- Public audio status: `{result.audiobook_gate['status']}`\n"
        + f"- Audiobook sync status: `{result.audiobook_gate['sync_status']}`\n"
        + f"- Model generation status: `{result.audiobook_gate['model_generation']}`\n"
        + f"- Provider internal-eval status: `{result.audiobook_gate['provider_internal_eval_status']}`\n"
        + "\nThis orchestrator is dry-run/report-only and does not publish books, enable public audio, or change payment settings.\n"
    )
    rights = (
        report_header(config, result, "English Book Rights Evidence Scorecard")
        + markdown_table(
            [
                ("source_url", "PASS" if present(config.get("source_url")) else "HOLD", str(config.get("source_url", ""))),
                ("source_license", "PASS" if present(config.get("source_license")) else "HOLD", str(config.get("source_license", ""))),
                (
                    "commercial_use_evidence",
                    "PASS" if present(config.get("commercial_use_evidence")) else "HOLD",
                    str(config.get("commercial_use_evidence", "")),
                ),
                ("source_hash", "GENERATED", result.hashes.get("source_hash", "")),
                ("content_hash", "GENERATED", result.hashes.get("content_hash", "")),
                ("provenance_hash", "GENERATED", result.hashes.get("provenance_hash", "")),
            ]
        )
        + "\nDecision: HOLD until owner/legal/publication review completes.\n"
    )
    publication = (
        report_header(config, result, "English Book Publication Gate Report")
        + f"- Gate status: `{result.final_gate['status']}`\n"
        + f"- GO/HOLD: `{result.final_gate['go_no_go']}`\n"
        + f"- Public publish allowed: `{str(result.final_gate['public_publish_allowed']).lower()}`\n"
        + f"- Start Reading CTA allowed: `{str(result.final_gate['start_reading_cta_allowed']).lower()}`\n"
        + "\n## Blockers\n\n"
        + "\n".join(f"- {blocker}" for blocker in result.final_gate["blockers"])
        + "\n"
    )
    audio_gate = (
        report_header(config, result, "English Audiobook Release Gate Report")
        + f"- Status: `{result.audiobook_gate['status']}`\n"
        + f"- Sync status: `{result.audiobook_gate['sync_status']}`\n"
        + f"- ElevenLabs sample status: `{result.audiobook_gate['elevenlabs_sample_status']}`\n"
        + f"- ElevenLabs import status: `{result.audiobook_gate['elevenlabs_sample_import_status']}`\n"
        + f"- ElevenLabs sample sync status: `{result.audiobook_gate['elevenlabs_sample_sync_status']}`\n"
        + f"- Selected model: `{result.audiobook_gate['selected_model_candidate']}`\n"
        + f"- Selected model decision: `{result.audiobook_gate['selected_model_decision']}`\n"
        + f"- Selected model internal-eval status: `{result.audiobook_gate['selected_model_internal_eval_status']}`\n"
        + f"- Model generation: `{result.audiobook_gate['model_generation']}`\n"
        + f"- Selected provider: `{result.audiobook_gate['selected_provider_id']}`\n"
        + f"- Selected provider decision: `{result.audiobook_gate['selected_provider_decision']}`\n"
        + f"- Provider internal-eval status: `{result.audiobook_gate['provider_internal_eval_status']}`\n"
        + f"- Provider production status: `{result.audiobook_gate['selected_provider_production_status']}`\n"
        + f"- Public audio publish allowed: `{str(result.audiobook_gate['public_audio_publish_allowed']).lower()}`\n"
        + f"- Public listening CTA: `{str(result.audiobook_gate['listen_now_cta']).lower()}`\n"
        + f"- Public audio JSON-LD metadata: `{str(result.audiobook_gate['audio_object_metadata']).lower()}`\n"
        + "\n## Blockers\n\n"
        + "\n".join(f"- {blocker}" for blocker in result.audiobook_gate["blockers"])
        + "\n"
    )
    qa_packet = (
        report_header(config, result, "English Audiobook QA Packet")
        + f"- Highlighted-text sync status: `{result.audiobook_gate['sync_status']}`\n"
        + f"- ElevenLabs Dracula sample status: `{result.audiobook_gate['elevenlabs_sample_status']}`\n"
        + f"- ElevenLabs Dracula import status: `{result.audiobook_gate['elevenlabs_sample_import_status']}`\n"
        + f"- Selected model candidate: `{result.audiobook_gate['selected_model_candidate']}`\n"
        + f"- Model license decision: `{result.audiobook_gate['selected_model_decision']}`\n"
        + f"- Model internal-eval status: `{result.audiobook_gate['selected_model_internal_eval_status']}`\n"
        + f"- Model generation status: `{result.audiobook_gate['model_generation']}`\n"
        + f"- Selected licensed provider: `{result.audiobook_gate['selected_provider_id']}`\n"
        + f"- Provider internal-eval status: `{result.audiobook_gate['provider_internal_eval_status']}`\n"
        + "- Human narration QA: HOLD, evidence missing or pending.\n"
        + "- Accessibility listening QA: HOLD, evidence missing or pending.\n"
        + "- Model/voice license review: HOLD unless explicit evidence is attached.\n"
        + "- Provider internal-eval review: HOLD unless commercial output, selected voice, owner, and legal evidence are attached.\n"
        + "- No public audio file, URL, player, listening CTA, or public audio JSON-LD metadata is produced.\n"
    )
    elevenlabs_sample_stage = elevenlabs_sample_status(result.stages)
    elevenlabs_report = (
        "# ElevenLabs Dracula Internal Sample Report\n\n"
        "This report is for internal sample preparation and manual import only. It does not call ElevenLabs, "
        "generate audio, publish audio, approve production, or expose public audio metadata.\n\n"
        f"- Provider: `ElevenLabs`\n"
        f"- Voice: `Rachel`\n"
        f"- Voice ID: `21m00Tcm4TlvDq8ikWAM`\n"
        f"- Evidence path: `{elevenlabs_sample_stage.get('evidence_path')}`\n"
        f"- Provider internal-eval status: `{elevenlabs_sample_stage.get('provider_internal_eval_status')}`\n"
        f"- Sample status: `{elevenlabs_sample_stage.get('status')}`\n"
        f"- Import status: `{elevenlabs_sample_stage.get('import_status')}`\n"
        f"- Sync status: `{elevenlabs_sample_stage.get('sync_status')}`\n"
        f"- Public audio release: `{PUBLIC_AUDIO_RELEASE_BLOCKED}`\n"
        f"- Production status: `PRODUCTION_BLOCKED`\n"
        f"- Sample directory: `{elevenlabs_sample_stage.get('sample_dir')}`\n\n"
        "## Manual Generation Instructions\n\n"
        "Use `sample_text.txt`, `elevenlabs_generation_brief.md`, `pronunciation_notes.md`, and "
        "`cost_control_plan.md` in the sample directory. Generate only a 30-45 second test if possible, "
        "then at most one 2-3 minute internal sample. Place the owner-downloaded MP3 or WAV only under "
        "`internal/audiobook_lab/dracula/en/chapter-1-elevenlabs-sample/imported_audio/`, then run "
        "`npm run elevenlabs:sample-import`.\n"
    )
    elevenlabs_scorecard = (
        "# ElevenLabs Dracula Sample QA Scorecard\n\n"
        "Decision: `HOLD`\n\n"
        "| QA Area | Status | Notes |\n"
        "| --- | --- | --- |\n"
        "| Voice clarity | HOLD | Requires owner listening review after manual import. |\n"
        "| Literary tone | HOLD | Must stay calm, restrained, and premium. |\n"
        "| Gothic restraint | HOLD | No melodramatic horror-trailer delivery. |\n"
        "| Pronunciation | HOLD | Review names and places from pronunciation notes. |\n"
        "| Pacing | HOLD | Confirm punctuation-aware pacing. |\n"
        "| Pauses | HOLD | Confirm date/location and paragraph pauses. |\n"
        "| Punctuation handling | HOLD | Manual QA required. |\n"
        "| Emotional expression | HOLD | Restrained literary expression only. |\n"
        "| Fatigue risk | HOLD | Listen for harshness or strain. |\n"
        "| Noise/artifacts | HOLD | Check generated file locally after import. |\n"
        "| Text fidelity | HOLD | Compare against `sample_text.txt`. |\n"
        "| Sentence sync readiness | HOLD | Timing placeholders require QA. |\n"
        "| Accessibility listening readiness | HOLD | Manual assistive listening review required. |\n"
        "| Overall score | HOLD | No score until owner QA exists. |\n"
        "| Decision | HOLD | `READY_FOR_FULL_CHAPTER_INTERNAL_ONLY` is blocked. |\n"
    )
    elevenlabs_sync_report = (
        "# ElevenLabs Dracula Highlight Sync QA Report\n\n"
        f"- Sync status: `{elevenlabs_sample_stage.get('sync_status')}`\n"
        f"- Imported audio exists: `{str(elevenlabs_sample_stage.get('imported_audio_exists')).lower()}`\n"
        f"- Audio hash: `{elevenlabs_sample_stage.get('audio_hash') or 'not imported'}`\n"
        f"- Sync manifest path: `{elevenlabs_sample_stage.get('sync_manifest_path') or 'not imported'}`\n"
        "- Sentence-level timing remains placeholder-only until a human sync QA pass is recorded.\n"
        "- Public audio remains blocked.\n"
    )
    chapter_pipeline_stage = next(
        (stage for stage in result.stages if stage.name == AUTOMATED_AUDIOBOOK_CHAPTER_PIPELINE_STAGE),
        StageResult(AUTOMATED_AUDIOBOOK_CHAPTER_PIPELINE_STAGE, "NOT_RUN", details={}),
    )
    chapter_pipeline_details = chapter_pipeline_stage.details
    chapter_pipeline_report = (
        "# Audiobook Chapter Pipeline Report\n\n"
        "This report records the automated dry-run chapter pipeline. It does not call paid providers, "
        "generate audio, publish audio, approve production, or change payment behavior.\n\n"
        f"- Stage status: `{chapter_pipeline_stage.status}`\n"
        f"- Output directory: `{chapter_pipeline_details.get('output_dir', 'not generated')}`\n"
        f"- Clean narration file: `{chapter_pipeline_details.get('clean_narration_file_path', 'not generated')}`\n"
        f"- Chunk manifest: `{chapter_pipeline_details.get('chunk_manifest_path', 'not generated')}`\n"
        f"- Cost estimate: `{chapter_pipeline_details.get('cost_estimate', {}).get('estimated_cost_inr', 'not generated')}` INR\n"
        f"- Provider gate: `{chapter_pipeline_details.get('provider_gate_status', 'not generated')}`\n"
        f"- Generation status: `{chapter_pipeline_details.get('generation_status', 'not generated')}`\n"
        f"- Sync status: `{chapter_pipeline_details.get('sync_status', 'HOLD_SYNC_QA_REQUIRED')}`\n"
        f"- Public audio release: `{chapter_pipeline_details.get('public_release_status', PUBLIC_AUDIO_RELEASE_BLOCKED)}`\n"
        f"- Public audio allowed: `{str(chapter_pipeline_details.get('public_audio_allowed', False)).lower()}`\n"
        f"- Production status: `{chapter_pipeline_details.get('production_status', 'PRODUCTION_BLOCKED')}`\n"
        f"- Provider API called: `{str(chapter_pipeline_details.get('provider_api_called', False)).lower()}`\n"
        f"- Repo-generated audio: `{str(chapter_pipeline_details.get('audio_generated_by_repo', False)).lower()}`\n"
    )
    seo = (
        report_header(config, result, "English Book SEO Preview Report")
        + "- SEO/social metadata is draft-only.\n"
        + "- Sitemap inclusion is disabled until publication approval.\n"
        + "- Book JSON-LD is disabled until publication approval.\n"
        + "- Public audio JSON-LD metadata is disabled.\n"
    )
    visual = (
        report_header(config, result, "English Book Visual Scorecard")
        + "- Cover provenance gate remains required before public visual use.\n"
        + "- Owner-designed artwork provenance and owner approval must be retained internally.\n"
        + "- No 10/10 visual or accessibility claim is made.\n"
    )
    selected_internal_eval_status = str(result.audiobook_gate["selected_model_internal_eval_status"])
    selected_model_candidate = str(result.audiobook_gate["selected_model_candidate"])
    selected_provider_internal_eval_status = str(result.audiobook_gate["provider_internal_eval_status"])
    selected_provider_id = str(result.audiobook_gate["selected_provider_id"])
    selected_provider_details = selected_provider_status(result.stages)
    selected_provider_voice_id = str(selected_provider_details.get("selected_provider_voice_id") or "OWNER_SELECTION_REQUIRED")
    selected_provider_voice_type = str(selected_provider_details.get("selected_provider_voice_type") or "unknown")
    selected_provider_blockers = selected_provider_details.get("provider_blockers") or []
    if isinstance(selected_provider_blockers, list) and selected_provider_blockers:
        provider_blocker_text = "\n".join(f"- {blocker}" for blocker in selected_provider_blockers[:8])
    else:
        provider_blocker_text = "- No provider blocker recorded."
    if selected_internal_eval_status == "ELIGIBLE_INTERNAL_EVAL":
        tts_next_action = (
            f"- Future separate task may prepare an internal-only 2-3 minute Dracula Chapter 1 sample with "
            f"`{selected_model_candidate}` after confirming no public audio output, no model download surprises, "
            "and no publication-side metadata changes.\n"
            "- Keep that future sample local/internal, preview-only, and outside `frontend/public` and `frontend/build`.\n"
        )
    else:
        tts_next_action = (
            f"- Do not generate an audio sample yet; `{selected_model_candidate}` remains "
            f"`{selected_internal_eval_status}`.\n"
            "- Collect owner/legal-reviewed selected voice or speaker-rights evidence, including provenance, "
            "commercial internal-eval permission, synthetic/non-human or consent status, and real-person "
            "voice-cloning risk review.\n"
        )
    if selected_provider_internal_eval_status == "ELIGIBLE_INTERNAL_EVAL":
        provider_next_action = (
            f"- Future separate task may prepare an internal-only 2-3 minute Dracula Chapter 1 sample with "
            f"`{selected_provider_id}` after owner/legal/provider evidence remains attached and public audio remains blocked.\n"
            "- Keep provider sample generation local/internal and outside `frontend/public` and `frontend/build`.\n"
        )
    else:
        provider_next_action = (
            f"- Do not generate a provider audio sample yet; `{selected_provider_id}` remains "
            f"`{selected_provider_internal_eval_status}`.\n"
            "- Complete ELEVENLABS_PROVIDER_OWNER_LEGAL_REVIEW_FORM.md and "
            "ELEVENLABS_PROVIDER_INTERNAL_EVAL_CHECKLIST.md before any provider eligibility change.\n"
        )

    prompt = "".join(
        [
            "# Next English Book Onboarding Prompt\n\n",
            f"Use `{result.config_path}` as the source config and keep the onboarding dry-run until every HOLD blocker is cleared.\n\n",
            f"Current selected TTS model: `{result.audiobook_gate['selected_model_candidate']}`.\n",
            f"Current selected Kokoro voice: `{result.audiobook_gate['selected_voice_id']}`.\n",
            f"Current selected TTS decision: `{result.audiobook_gate['selected_model_decision']}`.\n",
            f"Current selected TTS internal-eval status: `{result.audiobook_gate['selected_model_internal_eval_status']}`.\n",
            f"Current selected voice internal-eval status: `{result.audiobook_gate['selected_voice_internal_eval_status']}`.\n",
            f"Current model generation status: `{result.audiobook_gate['model_generation']}`.\n\n",
            f"Current selected licensed provider: `{result.audiobook_gate['selected_provider_id']}`.\n",
            f"Current selected provider voice: `{selected_provider_voice_id}`.\n",
            f"Current selected provider voice type: `{selected_provider_voice_type}`.\n",
            f"Current licensed provider internal-eval status: `{result.audiobook_gate['provider_internal_eval_status']}`.\n",
            f"Current licensed provider production status: `{result.audiobook_gate['selected_provider_production_status']}`.\n\n",
            "Current licensed provider blockers:\n",
            provider_blocker_text,
            "\n\n",
            "Required next checks:\n",
            "- Attach complete source-rights evidence.\n",
            "- Add owner-approved cover provenance.\n",
            "- Review TTS_MODEL_LICENSE_EVIDENCE_MATRIX.md and TTS_MODEL_PRODUCTION_ELIGIBILITY_REPORT.md.\n",
            "- Review TTS_VOICE_RIGHTS_INTERNAL_EVAL_APPROVAL_PACKET.md and TTS_INTERNAL_EVAL_CANDIDATE_SCORECARD.md.\n",
            "- Complete KOKORO_AF_HEART_OWNER_LEGAL_REVIEW_FORM.md and KOKORO_AF_HEART_EVIDENCE_COLLECTION_CHECKLIST.md before any Kokoro af_heart eligibility change.\n",
            "- Review TTS_PROVIDER_INTERNAL_EVAL_REVIEW.md and TTS_PROVIDER_COMMERCIAL_RIGHTS_SCORECARD.md.\n",
            "- Complete ELEVENLABS_PROVIDER_OWNER_LEGAL_REVIEW_FORM.md and ELEVENLABS_PROVIDER_INTERNAL_EVAL_CHECKLIST.md before any ElevenLabs eligibility change.\n",
            "- Complete internal/legal/elevenlabs/creator-membership-internal-eval-evidence.md before any ElevenLabs internal sample import is approved.\n",
            "- Complete TTS model license, voice, commercial-use, speaker-rights, and owner approval evidence before real internal generation.\n",
            "- Review AUDIOBOOK_CHAPTER_PIPELINE_REPORT.md for the automated dry-run narration, chunking, cost, provider, sync, and public-release gate evidence.\n",
            tts_next_action,
            provider_next_action,
            "- Review the internal highlighted-text sync manifest before any audio release consideration.\n",
            "- If owner/legal approve ElevenLabs internal evaluation, manually generate only the Dracula 2-3 minute sample in the ElevenLabs UI and import it with npm run elevenlabs:sample-import.\n",
            "- Keep public audio blocked.\n",
            "- Run the publication, audio, SEO, social, payment-smoke, regression, and frontend build gates.\n",
        ]
    )

    root_reports = {
        "BOOK_ONBOARDING_ORCHESTRATION_REPORT.md": orchestration,
        "ENGLISH_BOOK_RIGHTS_EVIDENCE_SCORECARD.md": rights,
        "ENGLISH_BOOK_PUBLICATION_GATE_REPORT.md": publication,
        "ENGLISH_AUDIOBOOK_RELEASE_GATE_REPORT.md": audio_gate,
        "ENGLISH_AUDIOBOOK_QA_PACKET.md": qa_packet,
        "ENGLISH_BOOK_SEO_PREVIEW_REPORT.md": seo,
        "ENGLISH_BOOK_VISUAL_SCORECARD.md": visual,
        "ELEVENLABS_DRACULA_INTERNAL_SAMPLE_REPORT.md": elevenlabs_report,
        "ELEVENLABS_DRACULA_SAMPLE_QA_SCORECARD.md": elevenlabs_scorecard,
        "ELEVENLABS_DRACULA_HIGHLIGHT_SYNC_QA_REPORT.md": elevenlabs_sync_report,
        "AUDIOBOOK_CHAPTER_PIPELINE_REPORT.md": chapter_pipeline_report,
    }
    paths: dict[str, Path] = {}
    paths.update(write_tts_license_artifacts(scoped_output_dir))
    paths.update(write_tts_provider_artifacts(scoped_output_dir))
    paths.update(copy_audiobook_sync_artifacts(result, scoped_output_dir))
    for filename, text in root_reports.items():
        if write_root_reports:
            path = ROOT / filename
            path.write_text(text, encoding="utf-8")
            paths[filename] = path
            latest_copy = latest_output_dir / filename
            latest_copy.write_text(text, encoding="utf-8")
        scoped_copy = scoped_output_dir / filename
        scoped_copy.write_text(text, encoding="utf-8")
        paths.setdefault(filename, scoped_copy)
        paths[f"output/onboarding/{slug}/{filename}"] = scoped_copy
    prompt_path = CODEX_PROMPT_PATH if write_root_reports else scoped_output_dir / "next_english_book_onboarding_prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    paths["output/codex_prompts/next_english_book_onboarding_prompt.md"] = prompt_path
    scoped_prompt_path = scoped_output_dir / "next_codex_prompt.md"
    scoped_prompt_path.write_text(prompt, encoding="utf-8")
    paths[f"output/onboarding/{slug}/next_codex_prompt.md"] = scoped_prompt_path
    scoped_json_path = scoped_output_dir / "english_book_onboarding_report.json"
    scoped_json_path.write_text(json.dumps(result_to_json(result), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths[f"output/onboarding/{slug}/english_book_onboarding_report.json"] = scoped_json_path
    if write_root_reports:
        latest_json_path = latest_output_dir / "english_book_onboarding_report.json"
        latest_json_path.write_text(json.dumps(result_to_json(result), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        paths["output/english_book_onboarding/english_book_onboarding_report.json"] = latest_json_path
    return paths


def run_orchestration(
    config_path: Path,
    *,
    mode: str = "dry-run",
    branch: str = "",
    allow_network: bool = False,
) -> OnboardingResult:
    config = read_config(config_path)
    dry_run = True
    stages: list[StageResult] = []
    stages.append(validate_inputs(config))
    stages.append(validate_source_license(config))
    stages.append(load_source_text(config, allow_network=allow_network))

    source = source_stage(stages)
    raw_text = str(source.details.get("raw_text", ""))
    cleaned_text, chapters = normalize_text(raw_text)
    hashes = build_hashes(config, cleaned_text)

    stages.extend(
        [
            chapter_normalization_plan(cleaned_text, chapters),
            draft_catalog_entry(config, hashes),
            preview_chapter_gate(chapters),
            seo_social_metadata_draft(config),
            cover_asset_gate(config),
            audiobook_planning_packet(config),
            tts_model_license_and_suitability_review(config),
            tts_voice_rights_internal_eval_review(config),
            licensed_provider_tts_internal_eval_review(config),
            elevenlabs_internal_sample_prep_and_import(config),
            automated_audiobook_chapter_pipeline_dry_run(config),
            audiobook_sync_dry_run_stage(config),
            narration_qa_gate(config),
            audiobook_legal_accessibility_gate(config),
            payment_publication_guardrails(config),
            build_regression_command_runner(),
        ]
    )

    preliminary_text = json.dumps([stage.name for stage in stages], ensure_ascii=False)
    stages.append(public_claims_audit(config, preliminary_text))

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    final = final_gate(config, stages)
    audio = audiobook_gate(stages)
    report_names = {
        "orchestration": "BOOK_ONBOARDING_ORCHESTRATION_REPORT.md",
        "rights": "ENGLISH_BOOK_RIGHTS_EVIDENCE_SCORECARD.md",
        "publication": "ENGLISH_BOOK_PUBLICATION_GATE_REPORT.md",
        "audiobook_release": "ENGLISH_AUDIOBOOK_RELEASE_GATE_REPORT.md",
        "audiobook_qa": "ENGLISH_AUDIOBOOK_QA_PACKET.md",
        "tts_model_license_matrix": "TTS_MODEL_LICENSE_EVIDENCE_MATRIX.md",
        "tts_model_production_eligibility": "TTS_MODEL_PRODUCTION_ELIGIBILITY_REPORT.md",
        "tts_voice_rights_internal_eval_packet": "TTS_VOICE_RIGHTS_INTERNAL_EVAL_APPROVAL_PACKET.md",
        "tts_internal_eval_scorecard": "TTS_INTERNAL_EVAL_CANDIDATE_SCORECARD.md",
        "tts_provider_internal_eval_review": "TTS_PROVIDER_INTERNAL_EVAL_REVIEW.md",
        "tts_provider_commercial_rights_scorecard": "TTS_PROVIDER_COMMERCIAL_RIGHTS_SCORECARD.md",
        "elevenlabs_provider_owner_legal_review_form": "ELEVENLABS_PROVIDER_OWNER_LEGAL_REVIEW_FORM.md",
        "elevenlabs_provider_internal_eval_checklist": "ELEVENLABS_PROVIDER_INTERNAL_EVAL_CHECKLIST.md",
        "elevenlabs_dracula_internal_sample_report": "ELEVENLABS_DRACULA_INTERNAL_SAMPLE_REPORT.md",
        "elevenlabs_dracula_sample_qa_scorecard": "ELEVENLABS_DRACULA_SAMPLE_QA_SCORECARD.md",
        "elevenlabs_dracula_highlight_sync_qa_report": "ELEVENLABS_DRACULA_HIGHLIGHT_SYNC_QA_REPORT.md",
        "audiobook_chapter_pipeline_report": "AUDIOBOOK_CHAPTER_PIPELINE_REPORT.md",
        "seo": "ENGLISH_BOOK_SEO_PREVIEW_REPORT.md",
        "visual": "ENGLISH_BOOK_VISUAL_SCORECARD.md",
        "codex_prompt": "output/codex_prompts/next_english_book_onboarding_prompt.md",
    }
    return OnboardingResult(
        config_path=str(config_path),
        mode=mode,
        branch=branch,
        allow_network=allow_network,
        dry_run=dry_run,
        generated_at=generated_at,
        book=config,
        stages=stages,
        hashes=hashes,
        reports=report_names,
        final_gate=final,
        audiobook_gate=audio,
        codex_prompt=str(CODEX_PROMPT_PATH),
    )


def ensure_no_public_audio_files() -> list[str]:
    matches: list[str] = []
    for relative in ("frontend/public", "frontend/build"):
        root = ROOT / relative
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in AUDIO_FILE_EXTENSIONS:
                matches.append(str(path.relative_to(ROOT)))
    return sorted(matches)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--mode", choices=("dry-run", "prepare-pr"), default="dry-run")
    parser.add_argument("--branch", default="")
    parser.add_argument("--create-pr", action="store_true")
    parser.add_argument("--allow-network", action="store_true", default=False)
    args = parser.parse_args()

    if args.create_pr and args.mode != "prepare-pr":
        parser.error("--create-pr is accepted only with --mode prepare-pr.")

    result = run_orchestration(args.config, mode=args.mode, branch=args.branch, allow_network=args.allow_network)
    paths = write_reports(result)
    public_audio = ensure_no_public_audio_files()

    print(
        "English book onboarding dry-run complete: "
        f"slug={result.book.get('slug')} "
        f"publication={result.final_gate['status']} "
        f"audio={result.audiobook_gate['status']} "
        f"blockers={result.final_gate['blocker_count']} "
        f"reports={len(paths)}"
    )
    if public_audio:
        print("Public audio files detected: " + ", ".join(public_audio), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
