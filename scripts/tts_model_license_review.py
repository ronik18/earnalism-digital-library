#!/usr/bin/env python3
"""Deterministic TTS model license and suitability review.

This script reads local model evidence only. It does not download models, call
external APIs, generate audio, publish audio, or approve production use without
complete commercial, voice, and owner evidence.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "audiobook" / "models" / "tts_model_candidates.yml"
MATRIX_REPORT_PATH = ROOT / "TTS_MODEL_LICENSE_EVIDENCE_MATRIX.md"
ELIGIBILITY_REPORT_PATH = ROOT / "TTS_MODEL_PRODUCTION_ELIGIBILITY_REPORT.md"
VOICE_RIGHTS_PACKET_PATH = ROOT / "TTS_VOICE_RIGHTS_INTERNAL_EVAL_APPROVAL_PACKET.md"
INTERNAL_EVAL_SCORECARD_PATH = ROOT / "TTS_INTERNAL_EVAL_CANDIDATE_SCORECARD.md"
KOKORO_SELECTED_VOICE_PACKET_PATH = ROOT / "KOKORO_SELECTED_VOICE_INTERNAL_EVAL_PACKET.md"
KOKORO_SELECTED_VOICE_SCORECARD_PATH = ROOT / "KOKORO_SELECTED_VOICE_RIGHTS_SCORECARD.md"
KOKORO_AF_HEART_REVIEW_FORM_PATH = ROOT / "KOKORO_AF_HEART_OWNER_LEGAL_REVIEW_FORM.md"
KOKORO_AF_HEART_CHECKLIST_PATH = ROOT / "KOKORO_AF_HEART_EVIDENCE_COLLECTION_CHECKLIST.md"

ELIGIBLE_INTERNAL_EVAL = "ELIGIBLE_INTERNAL_EVAL"
HOLD_LICENSE_REVIEW = "HOLD_LICENSE_REVIEW"
HOLD_VOICE_RIGHTS = "HOLD_VOICE_RIGHTS"
HOLD_OWNER_REVIEW = "HOLD_OWNER_REVIEW"
BLOCKED = "BLOCKED"
UNKNOWN_VALUES = {"", "unknown", "hold_review", "tbd", "todo", "missing", "none"}
VALID_COMMERCIAL_USE = {"ALLOWED", "HOLD_REVIEW", "BLOCKED", "UNKNOWN"}
VALID_PRODUCTION_STATUS = {ELIGIBLE_INTERNAL_EVAL, HOLD_LICENSE_REVIEW, BLOCKED}
VALID_INTERNAL_EVAL_STATUS = {ELIGIBLE_INTERNAL_EVAL, HOLD_VOICE_RIGHTS, HOLD_OWNER_REVIEW, BLOCKED}
REQUIRED_FIELDS = (
    "candidate_id",
    "display_name",
    "upstream_url",
    "model_card_url",
    "license_name",
    "license_url",
    "code_license",
    "weights_license",
    "voice_license",
    "dataset_license_notes",
    "commercial_use_status",
    "attribution_required",
    "languages_supported",
    "english_suitability",
    "bengali_suitability",
    "voice_cloning_risk",
    "real_person_voice_risk",
    "local_inference_possible",
    "network_required",
    "paid_provider_required",
    "production_candidate_status",
    "evidence_last_reviewed_date",
    "evidence_notes",
    "owner_approval_status",
    "voice_rights_evidence_url",
    "voice_rights_summary",
    "speaker_identity_status",
    "synthetic_voice_status",
    "real_person_voice_clone_risk",
    "internal_eval_allowed",
    "internal_eval_blockers",
    "owner_internal_eval_approval_status",
    "legal_internal_eval_review_status",
    "internal_eval_status",
)
SELECTED_VOICE_FIELDS = (
    "selected_voice_id",
    "selected_voice_display_name",
    "selected_voice_source_url",
    "selected_voice_license_evidence_url",
    "selected_voice_rights_summary",
    "selected_voice_synthetic_status",
    "selected_voice_real_person_risk",
    "selected_voice_attribution_requirement",
    "selected_voice_internal_eval_status",
    "owner_selected_voice_approval_status",
    "legal_selected_voice_review_status",
    "selected_voice_blockers",
)


@dataclass(frozen=True)
class CandidateDecision:
    candidate: dict[str, Any]
    decision_status: str
    internal_generation_status: str
    public_production_status: str
    internal_eval_status: str
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def scalar_value(value: str) -> Any:
    text = value.strip()
    if not text:
        return ""
    lowered = text.lower()
    if lowered in {"true", "yes"}:
        return True
    if lowered in {"false", "no"}:
        return False
    if lowered in {"null", "none"}:
        return None
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        return text[1:-1]
    return text


def load_candidates(path: Path = DEFAULT_CONFIG_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"TTS model candidate config not found: {path}")
    candidates: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_candidates = False
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if "\t" in raw_line:
            raise ValueError(f"{path}:{line_number}: tabs are not supported.")
        stripped = raw_line.strip()
        if stripped == "candidates:":
            in_candidates = True
            continue
        if not in_candidates:
            continue
        if stripped.startswith("- "):
            if current:
                candidates.append(current)
            current = {}
            remainder = stripped[2:].strip()
            if remainder:
                key, value = split_key_value(path, line_number, remainder)
                current[key] = scalar_value(value)
            continue
        if current is None:
            raise ValueError(f"{path}:{line_number}: candidate field has no candidate item.")
        key, value = split_key_value(path, line_number, stripped)
        current[key] = scalar_value(value)
    if current:
        candidates.append(current)
    return candidates


def split_key_value(path: Path, line_number: int, text: str) -> tuple[str, str]:
    if ":" not in text:
        raise ValueError(f"{path}:{line_number}: expected key: value syntax.")
    key, value = text.split(":", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"{path}:{line_number}: empty key is not allowed.")
    return key, value.strip()


def normalized(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def display_value(value: Any, fallback: str = "not selected") -> str:
    text = normalized(value)
    return text if text else fallback


def upper(value: Any) -> str:
    return normalized(value).upper()


def is_unknown(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return normalized(value).lower() in UNKNOWN_VALUES


def has_url(value: Any) -> bool:
    text = normalized(value)
    return text.startswith("https://") or text.startswith("http://")


def review_date_valid(value: Any) -> bool:
    try:
        date.fromisoformat(normalized(value))
        return True
    except ValueError:
        return False


def classify_candidate(candidate: dict[str, Any]) -> CandidateDecision:
    issues: list[str] = []
    warnings: list[str] = []
    candidate_id = normalized(candidate.get("candidate_id")) or "unknown"

    for field_name in REQUIRED_FIELDS:
        if field_name not in candidate or is_unknown(candidate.get(field_name)):
            issues.append(f"{field_name} is missing or requires review.")

    if not has_url(candidate.get("upstream_url")):
        issues.append("upstream_url must be an http(s) URL.")
    if not has_url(candidate.get("model_card_url")):
        issues.append("model_card_url must be an http(s) URL.")
    if not has_url(candidate.get("license_url")):
        issues.append("license_url must be an http(s) URL.")

    commercial = upper(candidate.get("commercial_use_status"))
    if commercial not in VALID_COMMERCIAL_USE:
        issues.append("commercial_use_status must be ALLOWED, HOLD_REVIEW, BLOCKED, or UNKNOWN.")
    if commercial in {"UNKNOWN", "HOLD_REVIEW"}:
        issues.append("commercial-use evidence is not approved.")
    if commercial == "BLOCKED":
        issues.append("commercial use is blocked.")

    production_status = upper(candidate.get("production_candidate_status"))
    if production_status not in VALID_PRODUCTION_STATUS:
        issues.append("production_candidate_status must be ELIGIBLE_INTERNAL_EVAL, HOLD_LICENSE_REVIEW, or BLOCKED.")
    if production_status == BLOCKED:
        issues.append("candidate is explicitly blocked.")

    if is_unknown(candidate.get("code_license")):
        issues.append("code license evidence is missing.")
    if is_unknown(candidate.get("weights_license")) or "VARIES" in upper(candidate.get("weights_license")):
        issues.append("weights license evidence is missing or varies by voice.")
    if is_unknown(candidate.get("voice_license")) or "VARIES" in upper(candidate.get("voice_license")):
        issues.append("voice rights evidence is missing or varies by voice.")

    internal_eval_declared = upper(candidate.get("internal_eval_status"))
    if internal_eval_declared not in VALID_INTERNAL_EVAL_STATUS:
        issues.append("internal_eval_status must be ELIGIBLE_INTERNAL_EVAL, HOLD_VOICE_RIGHTS, HOLD_OWNER_REVIEW, or BLOCKED.")

    if not has_url(candidate.get("voice_rights_evidence_url")):
        issues.append("voice_rights_evidence_url must be an http(s) URL.")
    if is_unknown(candidate.get("voice_rights_summary")):
        issues.append("voice_rights_summary is missing or requires review.")
    if is_unknown(candidate.get("speaker_identity_status")) or "UNVERIFIED" in upper(candidate.get("speaker_identity_status")):
        issues.append("speaker identity or voice provenance remains unresolved.")
    if is_unknown(candidate.get("synthetic_voice_status")) or "UNVERIFIED" in upper(candidate.get("synthetic_voice_status")):
        issues.append("synthetic voice status remains unresolved.")
    clone_risk = upper(candidate.get("real_person_voice_clone_risk"))
    if is_unknown(candidate.get("real_person_voice_clone_risk")) or clone_risk in {"HIGH", "UNRESOLVED", "HOLD_REVIEW"}:
        issues.append("real-person voice clone risk is unresolved or high.")
    if bool(candidate.get("internal_eval_allowed")) is not True:
        issues.append("internal_eval_allowed is not true.")
    if is_unknown(candidate.get("internal_eval_blockers")):
        issues.append("internal_eval_blockers must record the current blocker set.")
    owner_internal_eval_status = upper(candidate.get("owner_internal_eval_approval_status"))
    if owner_internal_eval_status not in {"APPROVED", "OWNER_REVIEW_REQUIRED"}:
        issues.append("owner internal-eval approval is missing or invalid.")
    legal_internal_eval_status = upper(candidate.get("legal_internal_eval_review_status"))
    if legal_internal_eval_status in {"", "UNKNOWN", "HOLD_REVIEW"}:
        issues.append("legal internal-eval review status is missing or unresolved.")
    if legal_internal_eval_status == "BLOCKED":
        issues.append("legal internal-eval review is blocked.")

    selected_voice_required = (
        candidate_id == "kokoro"
        or internal_eval_declared == ELIGIBLE_INTERNAL_EVAL
        or production_status == ELIGIBLE_INTERNAL_EVAL
        or bool(candidate.get("internal_eval_allowed"))
    )
    if selected_voice_required:
        for field_name in SELECTED_VOICE_FIELDS:
            if field_name not in candidate or is_unknown(candidate.get(field_name)):
                issues.append(f"{field_name} is missing or requires review.")
        if not has_url(candidate.get("selected_voice_source_url")):
            issues.append("selected_voice_source_url must be an http(s) URL.")
        if not has_url(candidate.get("selected_voice_license_evidence_url")):
            issues.append("selected_voice_license_evidence_url must be an http(s) URL.")
        selected_voice_eval_status = upper(candidate.get("selected_voice_internal_eval_status"))
        if selected_voice_eval_status not in VALID_INTERNAL_EVAL_STATUS:
            issues.append("selected_voice_internal_eval_status must be ELIGIBLE_INTERNAL_EVAL, HOLD_VOICE_RIGHTS, HOLD_OWNER_REVIEW, or BLOCKED.")
        selected_voice_synthetic_status = upper(candidate.get("selected_voice_synthetic_status"))
        if (
            is_unknown(candidate.get("selected_voice_synthetic_status"))
            or "UNVERIFIED" in selected_voice_synthetic_status
            or "HOLD" in selected_voice_synthetic_status
        ):
            issues.append("selected voice synthetic or speaker-rights status remains unresolved.")
        selected_voice_real_person_risk = upper(candidate.get("selected_voice_real_person_risk"))
        if (
            is_unknown(candidate.get("selected_voice_real_person_risk"))
            or selected_voice_real_person_risk in {"HIGH", "UNRESOLVED", "HOLD_REVIEW", "MEDIUM_UNRESOLVED"}
        ):
            issues.append("selected voice real-person risk is unresolved or high.")
        owner_selected_voice_status = upper(candidate.get("owner_selected_voice_approval_status"))
        if owner_selected_voice_status != "APPROVED":
            issues.append("owner selected-voice approval is required for internal evaluation.")
        legal_selected_voice_status = upper(candidate.get("legal_selected_voice_review_status"))
        if legal_selected_voice_status != "APPROVED":
            issues.append("legal selected-voice review is required for internal evaluation.")
        if is_unknown(candidate.get("selected_voice_blockers")):
            issues.append("selected_voice_blockers must record the current selected-voice blocker set.")
    else:
        selected_voice_eval_status = upper(candidate.get("selected_voice_internal_eval_status"))
        selected_voice_synthetic_status = upper(candidate.get("selected_voice_synthetic_status"))
        selected_voice_real_person_risk = upper(candidate.get("selected_voice_real_person_risk"))
        owner_selected_voice_status = upper(candidate.get("owner_selected_voice_approval_status"))
        legal_selected_voice_status = upper(candidate.get("legal_selected_voice_review_status"))

    gpl_risk = "GPL" in upper(candidate.get("code_license")) or "GPL" in upper(candidate.get("license_name"))
    if gpl_risk:
        warnings.append("GPL/commercial obligations require manual legal review before production use.")
        if upper(candidate.get("owner_approval_status")) != "APPROVED":
            issues.append("GPL/commercial-risk candidate lacks owner/legal approval.")

    if upper(candidate.get("voice_cloning_risk")) == "HIGH" or upper(candidate.get("real_person_voice_risk")) == "HIGH":
        issues.append("voice cloning or real-person voice risk is high.")

    if bool(candidate.get("network_required")):
        issues.append("network-required model cannot be used in this dry-run local eligibility stage.")
    if bool(candidate.get("paid_provider_required")):
        issues.append("paid-provider model cannot be used in this dry-run local eligibility stage.")
    if not bool(candidate.get("local_inference_possible")):
        warnings.append("local inference is not confirmed.")

    if not review_date_valid(candidate.get("evidence_last_reviewed_date")):
        issues.append("evidence_last_reviewed_date must be YYYY-MM-DD.")

    owner_approved = upper(candidate.get("owner_approval_status")) == "APPROVED"
    complete_internal_evidence = (
        commercial == "ALLOWED"
        and not is_unknown(candidate.get("license_name"))
        and has_url(candidate.get("license_url"))
        and not is_unknown(candidate.get("code_license"))
        and not is_unknown(candidate.get("weights_license"))
        and "VARIES" not in upper(candidate.get("weights_license"))
        and not is_unknown(candidate.get("voice_license"))
        and "VARIES" not in upper(candidate.get("voice_license"))
        and internal_eval_declared == ELIGIBLE_INTERNAL_EVAL
        and has_url(candidate.get("voice_rights_evidence_url"))
        and not is_unknown(candidate.get("voice_rights_summary"))
        and not is_unknown(candidate.get("speaker_identity_status"))
        and "UNVERIFIED" not in upper(candidate.get("speaker_identity_status"))
        and not is_unknown(candidate.get("synthetic_voice_status"))
        and "UNVERIFIED" not in upper(candidate.get("synthetic_voice_status"))
        and not is_unknown(candidate.get("real_person_voice_clone_risk"))
        and upper(candidate.get("real_person_voice_clone_risk")) not in {"HIGH", "UNRESOLVED", "HOLD_REVIEW"}
        and bool(candidate.get("internal_eval_allowed")) is True
        and not is_unknown(candidate.get("internal_eval_blockers"))
        and owner_internal_eval_status in {"APPROVED", "OWNER_REVIEW_REQUIRED"}
        and legal_internal_eval_status not in {"", "UNKNOWN", "HOLD_REVIEW", "BLOCKED"}
        and not is_unknown(candidate.get("selected_voice_id"))
        and has_url(candidate.get("selected_voice_source_url"))
        and has_url(candidate.get("selected_voice_license_evidence_url"))
        and not is_unknown(candidate.get("selected_voice_rights_summary"))
        and selected_voice_eval_status == ELIGIBLE_INTERNAL_EVAL
        and not is_unknown(candidate.get("selected_voice_synthetic_status"))
        and "UNVERIFIED" not in selected_voice_synthetic_status
        and "HOLD" not in selected_voice_synthetic_status
        and not is_unknown(candidate.get("selected_voice_real_person_risk"))
        and selected_voice_real_person_risk not in {"HIGH", "UNRESOLVED", "HOLD_REVIEW", "MEDIUM_UNRESOLVED"}
        and owner_selected_voice_status == "APPROVED"
        and legal_selected_voice_status == "APPROVED"
        and not is_unknown(candidate.get("selected_voice_blockers"))
        and not (gpl_risk and not owner_approved)
        and upper(candidate.get("voice_cloning_risk")) != "HIGH"
        and upper(candidate.get("real_person_voice_risk")) != "HIGH"
    )

    if complete_internal_evidence:
        internal_generation_status = "ELIGIBLE_INTERNAL_EVAL_ONLY"
        decision_status = ELIGIBLE_INTERNAL_EVAL
        internal_eval_status = ELIGIBLE_INTERNAL_EVAL
    elif (
        production_status == BLOCKED
        or internal_eval_declared == BLOCKED
        or commercial == "BLOCKED"
        or "high" in normalized(candidate.get("voice_cloning_risk")).lower()
        or clone_risk == "HIGH"
        or legal_internal_eval_status == "BLOCKED"
        or selected_voice_eval_status == BLOCKED
        or legal_selected_voice_status == "BLOCKED"
    ):
        internal_generation_status = BLOCKED
        decision_status = BLOCKED
        internal_eval_status = BLOCKED
    elif owner_internal_eval_status not in {"APPROVED", "OWNER_REVIEW_REQUIRED"}:
        internal_generation_status = HOLD_OWNER_REVIEW
        decision_status = HOLD_OWNER_REVIEW
        internal_eval_status = HOLD_OWNER_REVIEW
    elif (
        commercial != "ALLOWED"
        or is_unknown(candidate.get("license_name"))
        or not has_url(candidate.get("license_url"))
        or is_unknown(candidate.get("code_license"))
        or is_unknown(candidate.get("weights_license"))
        or "VARIES" in upper(candidate.get("weights_license"))
        or gpl_risk
    ):
        internal_generation_status = HOLD_LICENSE_REVIEW
        decision_status = HOLD_LICENSE_REVIEW
        internal_eval_status = HOLD_VOICE_RIGHTS
    else:
        internal_generation_status = HOLD_VOICE_RIGHTS
        decision_status = HOLD_VOICE_RIGHTS
        internal_eval_status = HOLD_VOICE_RIGHTS

    public_production_status = "PRODUCTION_BLOCKED"

    if not owner_approved:
        issues.append("owner approval is required before production use.")

    # Keep the candidate id easy to spot in issue text during tests/reports.
    if not candidate_id:
        issues.append("candidate_id is required.")

    return CandidateDecision(
        candidate=candidate,
        decision_status=decision_status,
        internal_generation_status=internal_generation_status,
        public_production_status=public_production_status,
        internal_eval_status=internal_eval_status,
        issues=dedupe(issues),
        warnings=dedupe(warnings),
    )


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def review_candidates(config_path: Path = DEFAULT_CONFIG_PATH) -> list[CandidateDecision]:
    return [classify_candidate(candidate) for candidate in load_candidates(config_path)]


def matrix_markdown(decisions: list[CandidateDecision]) -> str:
    lines = [
        "# TTS Model License Evidence Matrix",
        "",
        "This local report does not approve production audio. It records evidence status only.",
        "",
        "| Candidate | Official repo | Model card | Commercial use | Code license | Weights license | Voice license | Internal eval | English | Bengali | Decision |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for decision in decisions:
        candidate = decision.candidate
        lines.append(
            "| {display} | {repo} | {card} | {commercial} | {code} | {weights} | {voice} | {internal_eval} | {english} | {bengali} | {decision} |".format(
                display=normalized(candidate.get("display_name")),
                repo=markdown_link("repo", candidate.get("upstream_url")),
                card=markdown_link("card", candidate.get("model_card_url")),
                commercial=normalized(candidate.get("commercial_use_status")),
                code=normalized(candidate.get("code_license")),
                weights=normalized(candidate.get("weights_license")),
                voice=normalized(candidate.get("voice_license")),
                internal_eval=decision.internal_eval_status,
                english=normalized(candidate.get("english_suitability")),
                bengali=normalized(candidate.get("bengali_suitability")),
                decision=decision.decision_status,
            )
        )
    lines.extend(["", "## Evidence Detail", ""])
    for decision in decisions:
        candidate = decision.candidate
        lines.extend(
            [
                f"### {normalized(candidate.get('display_name'))}",
                "",
                f"- Official repository: {normalized(candidate.get('upstream_url'))}",
                f"- Official model card: {normalized(candidate.get('model_card_url'))}",
                f"- License URL: {normalized(candidate.get('license_url'))}",
                f"- Dataset/license notes: {normalized(candidate.get('dataset_license_notes'))}",
                f"- Attribution required: `{normalized(candidate.get('attribution_required'))}`",
                f"- Voice rights evidence URL: {normalized(candidate.get('voice_rights_evidence_url'))}",
                f"- Voice rights summary: {normalized(candidate.get('voice_rights_summary'))}",
                f"- Speaker identity status: `{normalized(candidate.get('speaker_identity_status'))}`",
                f"- Synthetic voice status: `{normalized(candidate.get('synthetic_voice_status'))}`",
                f"- Selected voice ID: `{display_value(candidate.get('selected_voice_id'))}`",
                f"- Selected voice source URL: {display_value(candidate.get('selected_voice_source_url'))}",
                f"- Selected voice license evidence URL: {display_value(candidate.get('selected_voice_license_evidence_url'))}",
                f"- Selected voice rights summary: {display_value(candidate.get('selected_voice_rights_summary'))}",
                f"- Selected voice synthetic status: `{display_value(candidate.get('selected_voice_synthetic_status'))}`",
                f"- Selected voice real-person risk: `{display_value(candidate.get('selected_voice_real_person_risk'))}`",
                f"- Selected voice internal-eval status: `{display_value(candidate.get('selected_voice_internal_eval_status'))}`",
                f"- Owner selected-voice approval: `{display_value(candidate.get('owner_selected_voice_approval_status'))}`",
                f"- Legal selected-voice review: `{display_value(candidate.get('legal_selected_voice_review_status'))}`",
                f"- Selected voice blockers: {display_value(candidate.get('selected_voice_blockers'))}",
                f"- Local inference feasible: `{normalized(candidate.get('local_inference_possible'))}`",
                f"- Network required: `{normalized(candidate.get('network_required'))}`",
                f"- Real-person voice risk: `{normalized(candidate.get('real_person_voice_risk'))}`",
                f"- Real-person voice clone risk: `{normalized(candidate.get('real_person_voice_clone_risk'))}`",
                f"- Internal eval allowed: `{normalized(candidate.get('internal_eval_allowed'))}`",
                f"- Internal eval blockers: {normalized(candidate.get('internal_eval_blockers'))}",
                f"- Owner internal-eval approval: `{normalized(candidate.get('owner_internal_eval_approval_status'))}`",
                f"- Legal internal-eval review: `{normalized(candidate.get('legal_internal_eval_review_status'))}`",
                f"- Evidence sources reviewed: {normalized(candidate.get('official_evidence_urls'))}",
                f"- Evidence notes: {normalized(candidate.get('evidence_notes'))}",
                f"- Decision reason: {decision_reason(decision)}",
                "",
            ]
        )
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def markdown_link(label: str, value: Any) -> str:
    url = normalized(value)
    if not has_url(url):
        return "missing"
    return f"[{label}]({url})"


def decision_reason(decision: CandidateDecision) -> str:
    if decision.issues:
        return "; ".join(decision.issues[:4]).replace("|", "/")
    return "Evidence is sufficient only for internal evaluation; production still requires owner/legal review."


def eligibility_markdown(decisions: list[CandidateDecision]) -> str:
    eligible = [d for d in decisions if d.decision_status == ELIGIBLE_INTERNAL_EVAL]
    lines = [
        "# TTS Model Production Eligibility Report",
        "",
        "No candidate is production-approved by this report.",
        "",
        f"- Internal-evaluation eligible candidates: `{len(eligible)}`",
        "- Public production status: `PRODUCTION_BLOCKED`",
        "- Audio generation status: `HOLD_LICENSE_REVIEW` unless an individual candidate has complete evidence.",
        "",
        "## Candidate Decisions",
        "",
    ]
    for decision in decisions:
        candidate = decision.candidate
        lines.extend(
            [
                f"### {candidate.get('display_name', 'Unknown')}",
                "",
                f"- Candidate ID: `{candidate.get('candidate_id', 'unknown')}`",
                f"- Decision: `{decision.decision_status}`",
                f"- Internal generation: `{decision.internal_generation_status}`",
                f"- Internal eval status: `{decision.internal_eval_status}`",
                f"- Public production: `{decision.public_production_status}`",
                f"- Owner approval: `{candidate.get('owner_approval_status', 'OWNER_APPROVAL_REQUIRED')}`",
                "",
                "Issues:",
            ]
        )
        if decision.issues:
            lines.extend(f"- {issue}" for issue in decision.issues)
        else:
            lines.append("- No blocking issue recorded for internal evaluation only; production still requires owner/legal review.")
        if decision.warnings:
            lines.append("")
            lines.append("Warnings:")
            lines.extend(f"- {warning}" for warning in decision.warnings)
        lines.append("")
    return "\n".join(lines)


def voice_rights_packet_markdown(decisions: list[CandidateDecision]) -> str:
    lines = [
        "# TTS Voice Rights Internal-Eval Approval Packet",
        "",
        "This packet is part of the English onboarding orchestrator. It does not approve production audio.",
        "",
        "- Public audio status: `PUBLIC_AUDIO_RELEASE_BLOCKED`",
        "- Production approval status: `PRODUCTION_BLOCKED` for every candidate",
        "- Real audio generation: `false`",
        "- Model downloads or paid APIs: `false`",
        "- Kokoro af_heart owner/legal review form: `KOKORO_AF_HEART_OWNER_LEGAL_REVIEW_FORM.md`",
        "- Kokoro af_heart evidence checklist: `KOKORO_AF_HEART_EVIDENCE_COLLECTION_CHECKLIST.md`",
        "",
    ]
    for decision in decisions:
        candidate = decision.candidate
        lines.extend(
            [
                f"## {normalized(candidate.get('display_name'))}",
                "",
                f"- Candidate ID: `{normalized(candidate.get('candidate_id'))}`",
                f"- Internal-eval status: `{decision.internal_eval_status}`",
                f"- Voice rights evidence URL: {normalized(candidate.get('voice_rights_evidence_url'))}",
                f"- Voice rights summary: {normalized(candidate.get('voice_rights_summary'))}",
                f"- Speaker identity status: `{normalized(candidate.get('speaker_identity_status'))}`",
                f"- Synthetic voice status: `{normalized(candidate.get('synthetic_voice_status'))}`",
                f"- Selected voice ID: `{display_value(candidate.get('selected_voice_id'))}`",
                f"- Selected voice source URL: {display_value(candidate.get('selected_voice_source_url'))}",
                f"- Selected voice license evidence URL: {display_value(candidate.get('selected_voice_license_evidence_url'))}",
                f"- Selected voice rights summary: {display_value(candidate.get('selected_voice_rights_summary'))}",
                f"- Selected voice synthetic status: `{display_value(candidate.get('selected_voice_synthetic_status'))}`",
                f"- Selected voice real-person risk: `{display_value(candidate.get('selected_voice_real_person_risk'))}`",
                f"- Selected voice attribution: `{display_value(candidate.get('selected_voice_attribution_requirement'))}`",
                f"- Selected voice internal-eval status: `{display_value(candidate.get('selected_voice_internal_eval_status'))}`",
                f"- Owner selected-voice approval: `{display_value(candidate.get('owner_selected_voice_approval_status'))}`",
                f"- Legal selected-voice review: `{display_value(candidate.get('legal_selected_voice_review_status'))}`",
                f"- Selected voice blockers: {display_value(candidate.get('selected_voice_blockers'))}",
                f"- Real-person voice clone risk: `{normalized(candidate.get('real_person_voice_clone_risk'))}`",
                f"- Internal eval allowed: `{normalized(candidate.get('internal_eval_allowed'))}`",
                f"- Owner internal-eval approval: `{normalized(candidate.get('owner_internal_eval_approval_status'))}`",
                f"- Legal internal-eval review: `{normalized(candidate.get('legal_internal_eval_review_status'))}`",
                f"- Blockers: {normalized(candidate.get('internal_eval_blockers'))}",
                f"- Public production: `{decision.public_production_status}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def internal_eval_scorecard_markdown(decisions: list[CandidateDecision]) -> str:
    eligible = [decision for decision in decisions if decision.internal_eval_status == ELIGIBLE_INTERNAL_EVAL]
    lines = [
        "# TTS Internal-Eval Candidate Scorecard",
        "",
        f"- Eligible internal-eval candidates: `{len(eligible)}`",
        "- Public production approval: `0`",
        "- Public audio release: `PUBLIC_AUDIO_RELEASE_BLOCKED`",
        "",
        "| Candidate | Internal eval | Public production | Primary blocker |",
        "| --- | --- | --- | --- |",
    ]
    for decision in decisions:
        candidate = decision.candidate
        blocker = normalized(candidate.get("internal_eval_blockers")) or decision_reason(decision)
        lines.append(
            "| {display} | {internal_eval} | {production} | {blocker} |".format(
                display=normalized(candidate.get("display_name")),
                internal_eval=decision.internal_eval_status,
                production=decision.public_production_status,
                blocker=blocker.replace("|", "/"),
            )
        )
    return "\n".join(lines) + "\n"


def kokoro_decision(decisions: list[CandidateDecision]) -> CandidateDecision:
    for decision in decisions:
        if decision.candidate.get("candidate_id") == "kokoro":
            return decision
    return selected_candidate_decision("kokoro", decisions)


def kokoro_selected_voice_packet_markdown(decisions: list[CandidateDecision]) -> str:
    decision = kokoro_decision(decisions)
    candidate = decision.candidate
    return "\n".join(
        [
            "# Kokoro Selected Voice Internal-Eval Packet",
            "",
            "This packet is part of the English onboarding orchestrator and does not approve production audio.",
            "",
            f"- Model candidate: `{normalized(candidate.get('candidate_id'))}`",
            f"- Selected voice ID: `{normalized(candidate.get('selected_voice_id'))}`",
            f"- Selected voice display name: {normalized(candidate.get('selected_voice_display_name'))}",
            f"- Selected voice source URL: {normalized(candidate.get('selected_voice_source_url'))}",
            f"- Selected voice license evidence URL: {normalized(candidate.get('selected_voice_license_evidence_url'))}",
            f"- Selected voice rights summary: {normalized(candidate.get('selected_voice_rights_summary'))}",
            f"- Selected voice synthetic status: `{normalized(candidate.get('selected_voice_synthetic_status'))}`",
            f"- Selected voice real-person risk: `{normalized(candidate.get('selected_voice_real_person_risk'))}`",
            f"- Attribution requirement: `{normalized(candidate.get('selected_voice_attribution_requirement'))}`",
            f"- Selected voice internal-eval status: `{normalized(candidate.get('selected_voice_internal_eval_status'))}`",
            f"- Owner selected-voice approval: `{normalized(candidate.get('owner_selected_voice_approval_status'))}`",
            f"- Legal selected-voice review: `{normalized(candidate.get('legal_selected_voice_review_status'))}`",
            f"- Selected voice blockers: {normalized(candidate.get('selected_voice_blockers'))}",
            f"- Model decision: `{decision.decision_status}`",
            f"- Internal eval status: `{decision.internal_eval_status}`",
            f"- Public production: `{decision.public_production_status}`",
            "- Public audio status: `PUBLIC_AUDIO_RELEASE_BLOCKED`",
            "- Real audio generated: `false`",
            "- Model downloads or paid APIs: `false`",
            "",
            "## Required Before Eligibility",
            "",
            "- Owner-selected voice approval must be `APPROVED`.",
            "- Legal selected-voice review must be `APPROVED`.",
            "- Selected voice synthetic/non-human status or consent/provenance must be documented.",
            "- Selected voice real-person risk must be resolved and not high.",
            "- Public production must remain `PRODUCTION_BLOCKED`.",
            "",
        ]
    )


def kokoro_selected_voice_scorecard_markdown(decisions: list[CandidateDecision]) -> str:
    decision = kokoro_decision(decisions)
    candidate = decision.candidate
    rows = [
        ("Selected voice ID", normalized(candidate.get("selected_voice_id")), "Documented in Kokoro VOICES.md for review only."),
        ("Selected voice source", "PASS" if has_url(candidate.get("selected_voice_source_url")) else "HOLD", normalized(candidate.get("selected_voice_source_url"))),
        ("License evidence URL", "PASS" if has_url(candidate.get("selected_voice_license_evidence_url")) else "HOLD", normalized(candidate.get("selected_voice_license_evidence_url"))),
        ("Synthetic/non-human proof", normalized(candidate.get("selected_voice_synthetic_status")), "Must be owner/legal reviewed before internal eval."),
        ("Real-person risk", normalized(candidate.get("selected_voice_real_person_risk")), "Must be resolved before internal eval."),
        ("Owner approval", normalized(candidate.get("owner_selected_voice_approval_status")), "Required before internal eval."),
        ("Legal review", normalized(candidate.get("legal_selected_voice_review_status")), "Required before internal eval."),
        ("Internal eval", decision.internal_eval_status, normalized(candidate.get("selected_voice_blockers"))),
        ("Production approval", decision.public_production_status, "No production approval is granted."),
    ]
    lines = [
        "# Kokoro Selected Voice Rights Scorecard",
        "",
        "| Check | Status | Notes |",
        "| --- | --- | --- |",
    ]
    for check, status, notes in rows:
        lines.append(f"| {check} | {status} | {notes.replace('|', '/')} |")
    lines.extend(["", "- Public audio status: `PUBLIC_AUDIO_RELEASE_BLOCKED`", "- Audio files generated: `false`", ""])
    return "\n".join(lines)


def kokoro_af_heart_review_form_markdown(decisions: list[CandidateDecision]) -> str:
    decision = kokoro_decision(decisions)
    candidate = decision.candidate
    return "\n".join(
        [
            "# Kokoro af_heart Owner/Legal Review Form",
            "",
            "This form is for manual evidence collection only. It does not approve internal generation, production use, public audio, or model downloads.",
            "",
            "## Current Gate State",
            "",
            f"- Model candidate: `{normalized(candidate.get('candidate_id'))}`",
            f"- Voice ID: `{display_value(candidate.get('selected_voice_id'))}`",
            f"- Voice display name: {display_value(candidate.get('selected_voice_display_name'))}",
            f"- Current selected voice status: `{display_value(candidate.get('selected_voice_internal_eval_status'))}`",
            f"- Current Kokoro decision: `{decision.decision_status}`",
            f"- Public production status: `{decision.public_production_status}`",
            "- Public audio status: `PUBLIC_AUDIO_RELEASE_BLOCKED`",
            "- Real audio generated: `false`",
            "- Decision must remain `HOLD` until every required field below is completed and reviewed.",
            "- Decision: HOLD / ELIGIBLE_INTERNAL_EVAL_ONLY / BLOCKED",
            "",
            "## Evidence Fields",
            "",
            "| Field | Current / Required Value | Owner/Legal Entry |",
            "| --- | --- | --- |",
            f"| Official voice source URL | {display_value(candidate.get('selected_voice_source_url'))} |  |",
            f"| Voice ID | `{display_value(candidate.get('selected_voice_id'))}` |  |",
            f"| Voice display name | {display_value(candidate.get('selected_voice_display_name'))} |  |",
            "| Speaker provenance | REQUIRED: identify voice origin, speaker type, dataset/source, and whether any human speaker is involved. |  |",
            "| Synthetic/non-human status | REQUIRED: document synthetic/non-human proof or explain human-speaker consent basis. |  |",
            "| Consent evidence | REQUIRED if any human speaker, performer, contributor, or derived voice is involved. |  |",
            f"| Voice license evidence | {display_value(candidate.get('selected_voice_license_evidence_url'))} plus owner/legal notes. |  |",
            "| Commercial internal-eval permission | REQUIRED: confirm local internal evaluation is allowed. |  |",
            f"| Attribution requirements | {display_value(candidate.get('selected_voice_attribution_requirement'))} |  |",
            "| Restrictions | REQUIRED: list disclosure, attribution, redistribution, output-use, or non-commercial restrictions. |  |",
            f"| Real-person voice clone risk | Current: `{display_value(candidate.get('selected_voice_real_person_risk'))}`. Must be resolved and not high. |  |",
            "| Owner reviewer name/date | REQUIRED before status can change. |  |",
            "| Legal reviewer name/date | REQUIRED before status can change. |  |",
            "| Decision | Choose one: HOLD / ELIGIBLE_INTERNAL_EVAL_ONLY / BLOCKED. | HOLD |",
            "| Notes | REQUIRED: rationale and unresolved questions. |  |",
            "| Required next action | REQUIRED: smallest next evidence or review step. |  |",
            "",
            "## Owner Review",
            "",
            "- Owner reviewer name:",
            "- Owner review date:",
            "- Owner decision: HOLD / ELIGIBLE_INTERNAL_EVAL_ONLY / BLOCKED",
            "- Owner notes:",
            "",
            "## Legal/Internal Review",
            "",
            "- Legal reviewer name:",
            "- Legal review date:",
            "- Legal decision: HOLD / ELIGIBLE_INTERNAL_EVAL_ONLY / BLOCKED",
            "- Legal notes:",
            "",
            "## Safety Confirmation",
            "",
            "- No audio may be generated from this form alone.",
            "- No public audio URL, public listening CTA, or public audio JSON-LD metadata may be created.",
            "- Production status remains `PRODUCTION_BLOCKED`.",
            "- Public audio remains `PUBLIC_AUDIO_RELEASE_BLOCKED`.",
            "",
        ]
    )


def kokoro_af_heart_checklist_markdown(decisions: list[CandidateDecision]) -> str:
    decision = kokoro_decision(decisions)
    candidate = decision.candidate
    return "\n".join(
        [
            "# Kokoro af_heart Evidence Collection Checklist",
            "",
            "af_heart cannot be promoted to `ELIGIBLE_INTERNAL_EVAL_ONLY` unless every checklist item is completed and reviewed.",
            "",
            "## Current Status",
            "",
            f"- Voice ID: `{display_value(candidate.get('selected_voice_id'))}`",
            f"- Selected voice status: `{display_value(candidate.get('selected_voice_internal_eval_status'))}`",
            f"- Kokoro model status: `{decision.internal_eval_status}`",
            f"- Production approval: `{decision.public_production_status}`",
            "- Public audio: `PUBLIC_AUDIO_RELEASE_BLOCKED`",
            "- Eligible internal-eval candidates: `0`",
            "",
            "## Required Before Promotion",
            "",
            "- [ ] Voice/speaker provenance is documented.",
            "- [ ] Consent evidence or synthetic/non-human status is documented.",
            "- [ ] Voice/license evidence allows local internal evaluation.",
            "- [ ] Attribution requirements are understood and recorded.",
            "- [ ] Restrictions are understood and recorded.",
            "- [ ] Real-person voice clone risk is resolved and not high.",
            "- [ ] Owner approval is recorded with reviewer name and date.",
            "- [ ] Legal/internal review is complete and not blocked.",
            "- [ ] The decision is explicitly recorded as HOLD, ELIGIBLE_INTERNAL_EVAL_ONLY, or BLOCKED.",
            "- [ ] The next action is recorded.",
            "",
            "## Non-Negotiable Blocks",
            "",
            "- If speaker provenance is missing, keep `HOLD_VOICE_RIGHTS`.",
            "- If consent or synthetic/non-human status is missing, keep `HOLD_VOICE_RIGHTS`.",
            "- If commercial internal-eval permission is unclear, keep `HOLD_VOICE_RIGHTS`.",
            "- If real-person voice clone risk is unresolved or high, keep `HOLD_VOICE_RIGHTS` or `BLOCKED`.",
            "- If owner approval is missing, keep `HOLD_VOICE_RIGHTS`.",
            "- If legal/internal review is blocked, set `BLOCKED`.",
            "- Do not mark production approved in this workflow.",
            "- Do not generate audio in this workflow.",
            "",
            "## Output Safety",
            "",
            "- No audio files may be written to `frontend/public` or `frontend/build`.",
            "- No public listening CTA may appear publicly.",
            "- No public audio JSON-LD metadata may be emitted.",
            "- Public audio remains `PUBLIC_AUDIO_RELEASE_BLOCKED`.",
            "",
        ]
    )


def decision_payload(decisions: list[CandidateDecision]) -> dict[str, Any]:
    return {
        "generated_by": "scripts/tts_model_license_review.py",
        "public_audio_release": "PUBLIC_AUDIO_RELEASE_BLOCKED",
        "production_audio_approved": False,
        "eligible_internal_eval_count": sum(1 for decision in decisions if decision.internal_eval_status == ELIGIBLE_INTERNAL_EVAL),
        "candidates": [
            {
                "candidate_id": decision.candidate.get("candidate_id"),
                "display_name": decision.candidate.get("display_name"),
                "decision_status": decision.decision_status,
                "internal_generation_status": decision.internal_generation_status,
                "internal_eval_status": decision.internal_eval_status,
                "public_production_status": decision.public_production_status,
                "issues": decision.issues,
                "warnings": decision.warnings,
                "evidence": decision.candidate,
            }
            for decision in decisions
        ],
    }


def write_reports(decisions: list[CandidateDecision], *, output_dir: Path | None = None) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    matrix = matrix_markdown(decisions)
    eligibility = eligibility_markdown(decisions)
    voice_rights_packet = voice_rights_packet_markdown(decisions)
    internal_eval_scorecard = internal_eval_scorecard_markdown(decisions)
    kokoro_voice_packet = kokoro_selected_voice_packet_markdown(decisions)
    kokoro_voice_scorecard = kokoro_selected_voice_scorecard_markdown(decisions)
    kokoro_review_form = kokoro_af_heart_review_form_markdown(decisions)
    kokoro_checklist = kokoro_af_heart_checklist_markdown(decisions)
    MATRIX_REPORT_PATH.write_text(matrix, encoding="utf-8")
    ELIGIBILITY_REPORT_PATH.write_text(eligibility, encoding="utf-8")
    VOICE_RIGHTS_PACKET_PATH.write_text(voice_rights_packet, encoding="utf-8")
    INTERNAL_EVAL_SCORECARD_PATH.write_text(internal_eval_scorecard, encoding="utf-8")
    KOKORO_SELECTED_VOICE_PACKET_PATH.write_text(kokoro_voice_packet, encoding="utf-8")
    KOKORO_SELECTED_VOICE_SCORECARD_PATH.write_text(kokoro_voice_scorecard, encoding="utf-8")
    KOKORO_AF_HEART_REVIEW_FORM_PATH.write_text(kokoro_review_form, encoding="utf-8")
    KOKORO_AF_HEART_CHECKLIST_PATH.write_text(kokoro_checklist, encoding="utf-8")
    paths[path_key(MATRIX_REPORT_PATH)] = MATRIX_REPORT_PATH
    paths[path_key(ELIGIBILITY_REPORT_PATH)] = ELIGIBILITY_REPORT_PATH
    paths[path_key(VOICE_RIGHTS_PACKET_PATH)] = VOICE_RIGHTS_PACKET_PATH
    paths[path_key(INTERNAL_EVAL_SCORECARD_PATH)] = INTERNAL_EVAL_SCORECARD_PATH
    paths[path_key(KOKORO_SELECTED_VOICE_PACKET_PATH)] = KOKORO_SELECTED_VOICE_PACKET_PATH
    paths[path_key(KOKORO_SELECTED_VOICE_SCORECARD_PATH)] = KOKORO_SELECTED_VOICE_SCORECARD_PATH
    paths[path_key(KOKORO_AF_HEART_REVIEW_FORM_PATH)] = KOKORO_AF_HEART_REVIEW_FORM_PATH
    paths[path_key(KOKORO_AF_HEART_CHECKLIST_PATH)] = KOKORO_AF_HEART_CHECKLIST_PATH
    if output_dir:
        if not output_dir.is_absolute():
            output_dir = ROOT / output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        matrix_path = output_dir / "TTS_MODEL_LICENSE_EVIDENCE_MATRIX.md"
        eligibility_path = output_dir / "TTS_MODEL_PRODUCTION_ELIGIBILITY_REPORT.md"
        voice_rights_packet_path = output_dir / "TTS_VOICE_RIGHTS_INTERNAL_EVAL_APPROVAL_PACKET.md"
        internal_eval_scorecard_path = output_dir / "TTS_INTERNAL_EVAL_CANDIDATE_SCORECARD.md"
        kokoro_voice_packet_path = output_dir / "KOKORO_SELECTED_VOICE_INTERNAL_EVAL_PACKET.md"
        kokoro_voice_scorecard_path = output_dir / "KOKORO_SELECTED_VOICE_RIGHTS_SCORECARD.md"
        kokoro_review_form_path = output_dir / "KOKORO_AF_HEART_OWNER_LEGAL_REVIEW_FORM.md"
        kokoro_checklist_path = output_dir / "KOKORO_AF_HEART_EVIDENCE_COLLECTION_CHECKLIST.md"
        json_path = output_dir / "tts_model_license_review.json"
        matrix_path.write_text(matrix, encoding="utf-8")
        eligibility_path.write_text(eligibility, encoding="utf-8")
        voice_rights_packet_path.write_text(voice_rights_packet, encoding="utf-8")
        internal_eval_scorecard_path.write_text(internal_eval_scorecard, encoding="utf-8")
        kokoro_voice_packet_path.write_text(kokoro_voice_packet, encoding="utf-8")
        kokoro_voice_scorecard_path.write_text(kokoro_voice_scorecard, encoding="utf-8")
        kokoro_review_form_path.write_text(kokoro_review_form, encoding="utf-8")
        kokoro_checklist_path.write_text(kokoro_checklist, encoding="utf-8")
        json_path.write_text(json.dumps(decision_payload(decisions), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        paths[path_key(matrix_path)] = matrix_path
        paths[path_key(eligibility_path)] = eligibility_path
        paths[path_key(voice_rights_packet_path)] = voice_rights_packet_path
        paths[path_key(internal_eval_scorecard_path)] = internal_eval_scorecard_path
        paths[path_key(kokoro_voice_packet_path)] = kokoro_voice_packet_path
        paths[path_key(kokoro_voice_scorecard_path)] = kokoro_voice_scorecard_path
        paths[path_key(kokoro_review_form_path)] = kokoro_review_form_path
        paths[path_key(kokoro_checklist_path)] = kokoro_checklist_path
        paths[path_key(json_path)] = json_path
    return paths


def path_key(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def selected_candidate_decision(candidate_id: str, decisions: list[CandidateDecision]) -> CandidateDecision:
    normalized_id = re.sub(r"[^a-z0-9-]+", "-", candidate_id.strip().lower()).strip("-")
    for decision in decisions:
        if decision.candidate.get("candidate_id") == normalized_id:
            return decision
    return CandidateDecision(
        candidate={"candidate_id": normalized_id, "display_name": candidate_id},
        decision_status=HOLD_LICENSE_REVIEW,
        internal_generation_status=HOLD_LICENSE_REVIEW,
        public_production_status="PRODUCTION_BLOCKED",
        internal_eval_status=HOLD_VOICE_RIGHTS,
        issues=["selected model candidate is not configured."],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    decisions = review_candidates(args.config)
    paths = write_reports(decisions, output_dir=args.output_dir)
    blocked = sum(1 for decision in decisions if decision.decision_status == BLOCKED)
    hold = sum(1 for decision in decisions if decision.decision_status in {HOLD_LICENSE_REVIEW, HOLD_VOICE_RIGHTS, HOLD_OWNER_REVIEW})
    eligible = sum(1 for decision in decisions if decision.decision_status == ELIGIBLE_INTERNAL_EVAL)
    print(
        "TTS model license review complete: "
        f"candidates={len(decisions)} eligible_internal_eval={eligible} hold={hold} blocked={blocked} reports={len(paths)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
