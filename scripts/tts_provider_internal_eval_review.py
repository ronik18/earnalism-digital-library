#!/usr/bin/env python3
"""Deterministic commercial TTS provider internal-evaluation review.

This script reads local provider evidence only. It never calls provider APIs,
downloads models, generates audio, publishes audio, or approves production use.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "audiobook" / "providers" / "tts_provider_candidates.yml"
DEFAULT_SCOPED_OUTPUT_DIR = ROOT / "output" / "onboarding" / "frankenstein"
PROVIDER_REVIEW_REPORT_PATH = ROOT / "TTS_PROVIDER_INTERNAL_EVAL_REVIEW.md"
PROVIDER_SCORECARD_PATH = ROOT / "TTS_PROVIDER_COMMERCIAL_RIGHTS_SCORECARD.md"
ELEVENLABS_REVIEW_FORM_PATH = ROOT / "ELEVENLABS_PROVIDER_OWNER_LEGAL_REVIEW_FORM.md"
ELEVENLABS_CHECKLIST_PATH = ROOT / "ELEVENLABS_PROVIDER_INTERNAL_EVAL_CHECKLIST.md"

ELIGIBLE_INTERNAL_EVAL = "ELIGIBLE_INTERNAL_EVAL"
ELIGIBLE_INTERNAL_EVAL_ONLY = "ELIGIBLE_INTERNAL_EVAL_ONLY"
HOLD_PROVIDER_REVIEW = "HOLD_PROVIDER_REVIEW"
BLOCKED = "BLOCKED"
PRODUCTION_BLOCKED = "PRODUCTION_BLOCKED"
UNKNOWN_VALUES = {"", "unknown", "owner_selection_required", "tbd", "todo", "missing", "none"}
VALID_STANDALONE_OUTPUT = {"UNKNOWN", "ALLOWED", "BLOCKED", "HOLD_REVIEW"}
VALID_INTERNAL_EVAL = {ELIGIBLE_INTERNAL_EVAL, HOLD_PROVIDER_REVIEW, BLOCKED}
VALID_SELECTED_VOICE_TYPES = {"platform_voice", "cloned_voice", "generated_voice", "unknown"}
REQUIRED_FIELDS = (
    "provider_id",
    "display_name",
    "official_terms_url",
    "commercial_use_evidence_url",
    "voice_license_evidence_url",
    "paid_plan_required",
    "plan_evidence_status",
    "beta_feature_allowed",
    "beta_features_allowed",
    "beta_features_excluded_evidence",
    "standalone_audio_distribution_allowed",
    "standalone_audio_distribution_evidence",
    "attribution_required",
    "selected_voice_attribution_requirement",
    "selected_voice_restrictions",
    "commercial_internal_eval_permission",
    "provider_terms_review_status",
    "data_retention_review_status",
    "data_retention_notes",
    "voice_rights_status",
    "selected_voice_type",
    "selected_voice_rights_summary",
    "internal_eval_status",
    "production_status",
    "owner_approval_status",
    "legal_review_status",
    "blockers",
)


@dataclass(frozen=True)
class ProviderDecision:
    provider: dict[str, Any]
    decision_status: str
    internal_eval_status: str
    internal_generation_status: str
    public_production_status: str
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


def split_key_value(path: Path, line_number: int, text: str) -> tuple[str, str]:
    if ":" not in text:
        raise ValueError(f"{path}:{line_number}: expected key: value syntax.")
    key, value = text.split(":", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"{path}:{line_number}: empty key is not allowed.")
    return key, value.strip()


def load_providers(path: Path = DEFAULT_CONFIG_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"TTS provider candidate config not found: {path}")
    providers: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_providers = False
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if "\t" in raw_line:
            raise ValueError(f"{path}:{line_number}: tabs are not supported.")
        stripped = raw_line.strip()
        if stripped == "providers:":
            in_providers = True
            continue
        if not in_providers:
            continue
        if stripped.startswith("- "):
            if current:
                providers.append(current)
            current = {}
            remainder = stripped[2:].strip()
            if remainder:
                key, value = split_key_value(path, line_number, remainder)
                current[key] = scalar_value(value)
            continue
        if current is None:
            raise ValueError(f"{path}:{line_number}: provider field has no provider item.")
        key, value = split_key_value(path, line_number, stripped)
        current[key] = scalar_value(value)
    if current:
        providers.append(current)
    return providers


def normalized(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def upper(value: Any) -> str:
    return normalized(value).upper()


def is_unknown(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return normalized(value).lower() in UNKNOWN_VALUES


def has_url(value: Any) -> bool:
    text = normalized(value)
    return text.startswith("https://") or text.startswith("http://")


def is_approved(value: Any) -> bool:
    return upper(value) in {"APPROVED", "RECORDED", "ALLOWED", "NOT_REQUIRED"}


def beta_features_enabled(provider: dict[str, Any]) -> bool:
    return bool(provider.get("beta_feature_allowed")) or bool(provider.get("beta_features_allowed"))


def explicit_clone_rights_evidence(provider: dict[str, Any]) -> bool:
    summary = normalized(provider.get("selected_voice_rights_summary")).lower()
    return (
        upper(provider.get("voice_rights_status")) in {"APPROVED", "LICENSED"}
        and has_url(provider.get("selected_voice_license_evidence_url"))
        and any(token in summary for token in ("consent", "licensed", "approved", "explicit"))
    )


def display_value(value: Any, fallback: str = "not selected") -> str:
    text = normalized(value)
    return text if text else fallback


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def classify_provider(provider: dict[str, Any]) -> ProviderDecision:
    issues: list[str] = []
    warnings: list[str] = []
    provider_id = normalized(provider.get("provider_id")) or "unknown"

    for field_name in REQUIRED_FIELDS:
        if field_name not in provider or is_unknown(provider.get(field_name)):
            issues.append(f"{field_name} is missing or requires review.")

    for field_name in ("official_terms_url", "commercial_use_evidence_url", "voice_license_evidence_url"):
        if not has_url(provider.get(field_name)):
            issues.append(f"{field_name} must be an http(s) URL.")

    standalone = upper(provider.get("standalone_audio_distribution_allowed"))
    if standalone not in VALID_STANDALONE_OUTPUT:
        issues.append("standalone_audio_distribution_allowed must be UNKNOWN, ALLOWED, BLOCKED, or HOLD_REVIEW.")
    if standalone in {"UNKNOWN", "HOLD_REVIEW"}:
        issues.append("standalone audio distribution evidence is not approved.")
    if standalone == "BLOCKED":
        issues.append("standalone audio distribution is blocked.")
    if upper(provider.get("attribution_required")) == "HOLD_REVIEW":
        issues.append("attribution requirements require owner/legal review.")

    declared_internal_eval = upper(provider.get("internal_eval_status"))
    if declared_internal_eval not in VALID_INTERNAL_EVAL:
        issues.append("internal_eval_status must be ELIGIBLE_INTERNAL_EVAL, HOLD_PROVIDER_REVIEW, or BLOCKED.")
    if upper(provider.get("production_status")) != PRODUCTION_BLOCKED:
        issues.append("production_status must remain PRODUCTION_BLOCKED.")
    if beta_features_enabled(provider):
        issues.append("beta features are blocked for this internal-evaluation path.")
    if not is_approved(provider.get("beta_features_excluded_evidence")):
        issues.append("beta feature exclusion evidence is missing or requires review.")
    if is_unknown(provider.get("voice_rights_status")) or upper(provider.get("voice_rights_status")) not in {
        "APPROVED",
        "LICENSED",
        "OWNER_REVIEW_REQUIRED",
        "HOLD_REVIEW",
    }:
        issues.append("voice rights status is missing or requires review.")

    selected_voice_id = normalized(provider.get("selected_voice_id"))
    if not selected_voice_id or selected_voice_id == "OWNER_SELECTION_REQUIRED":
        issues.append("selected provider voice is not selected.")
    selected_voice_type = normalized(provider.get("selected_voice_type")).lower()
    if selected_voice_type not in VALID_SELECTED_VOICE_TYPES:
        issues.append("selected_voice_type must be platform_voice, cloned_voice, generated_voice, or unknown.")
    if selected_voice_type == "unknown":
        issues.append("selected voice type is unknown.")
    if selected_voice_type == "cloned_voice" and not explicit_clone_rights_evidence(provider):
        issues.append("cloned voice requires explicit voice-rights, consent, and license evidence.")
    if selected_voice_type not in {"platform_voice", "generated_voice"}:
        issues.append("selected voice must be a provider/platform voice or generated voice before internal evaluation.")
    if is_unknown(provider.get("selected_voice_license_evidence_url")) or not has_url(provider.get("selected_voice_license_evidence_url")):
        issues.append("selected provider voice license evidence is missing.")
    if is_unknown(provider.get("selected_voice_rights_summary")):
        issues.append("selected provider voice rights summary is missing.")
    if upper(provider.get("selected_voice_attribution_requirement")) == "HOLD_REVIEW":
        issues.append("selected voice attribution requirements require review.")
    if upper(provider.get("selected_voice_restrictions")) == "HOLD_REVIEW":
        issues.append("selected voice restrictions require review.")

    owner_approved = upper(provider.get("owner_approval_status")) == "APPROVED"
    legal_approved = upper(provider.get("legal_review_status")) == "APPROVED"
    if not owner_approved:
        issues.append("owner approval is required before provider internal evaluation.")
    if not legal_approved:
        issues.append("legal/internal review is required before provider internal evaluation.")

    if bool(provider.get("paid_plan_required")) and not is_approved(provider.get("plan_evidence_status")):
        issues.append("paid plan evidence status is missing or requires review.")
    if bool(provider.get("paid_plan_required")) and is_unknown(provider.get("paid_plan_evidence_url")):
        issues.append("paid plan evidence is required before using this provider for internal evaluation.")
    if not is_approved(provider.get("commercial_internal_eval_permission")):
        issues.append("commercial internal-eval permission is missing or requires review.")
    if not is_approved(provider.get("standalone_audio_distribution_evidence")):
        issues.append("standalone audio distribution evidence is missing or requires review.")
    if not is_approved(provider.get("provider_terms_review_status")):
        issues.append("provider terms review is missing or requires review.")
    if not is_approved(provider.get("data_retention_review_status")):
        issues.append("data retention review is missing or requires review.")
    if is_unknown(provider.get("blockers")):
        issues.append("blockers must record the current provider blocker set.")

    complete_internal_evidence = (
        declared_internal_eval == ELIGIBLE_INTERNAL_EVAL
        and standalone == "ALLOWED"
        and not beta_features_enabled(provider)
        and is_approved(provider.get("beta_features_excluded_evidence"))
        and upper(provider.get("production_status")) == PRODUCTION_BLOCKED
        and upper(provider.get("voice_rights_status")) in {"APPROVED", "LICENSED"}
        and selected_voice_type in {"platform_voice", "generated_voice"}
        and selected_voice_id
        and selected_voice_id != "OWNER_SELECTION_REQUIRED"
        and has_url(provider.get("selected_voice_license_evidence_url"))
        and not is_unknown(provider.get("selected_voice_rights_summary"))
        and is_approved(provider.get("selected_voice_attribution_requirement"))
        and is_approved(provider.get("selected_voice_restrictions"))
        and is_approved(provider.get("commercial_internal_eval_permission"))
        and is_approved(provider.get("standalone_audio_distribution_evidence"))
        and is_approved(provider.get("provider_terms_review_status"))
        and is_approved(provider.get("data_retention_review_status"))
        and (not bool(provider.get("paid_plan_required")) or has_url(provider.get("paid_plan_evidence_url")))
        and (not bool(provider.get("paid_plan_required")) or is_approved(provider.get("plan_evidence_status")))
        and owner_approved
        and legal_approved
    )

    if complete_internal_evidence:
        decision_status = ELIGIBLE_INTERNAL_EVAL
        internal_eval_status = ELIGIBLE_INTERNAL_EVAL
        internal_generation_status = ELIGIBLE_INTERNAL_EVAL_ONLY
    elif beta_features_enabled(provider) or standalone == "BLOCKED" or declared_internal_eval == BLOCKED:
        decision_status = BLOCKED
        internal_eval_status = BLOCKED
        internal_generation_status = BLOCKED
    else:
        decision_status = HOLD_PROVIDER_REVIEW
        internal_eval_status = HOLD_PROVIDER_REVIEW
        internal_generation_status = HOLD_PROVIDER_REVIEW

    if provider_id == "owned-narrator-voice":
        warnings.append("Strategic preferred path, but still blocked until owner/narrator agreement and legal review exist.")

    return ProviderDecision(
        provider=provider,
        decision_status=decision_status,
        internal_eval_status=internal_eval_status,
        internal_generation_status=internal_generation_status,
        public_production_status=PRODUCTION_BLOCKED,
        issues=dedupe(issues),
        warnings=dedupe(warnings),
    )


def review_provider_candidates(config_path: Path = DEFAULT_CONFIG_PATH) -> list[ProviderDecision]:
    return [classify_provider(provider) for provider in load_providers(config_path)]


def markdown_link(label: str, value: Any) -> str:
    url = normalized(value)
    if not has_url(url):
        return "missing"
    return f"[{label}]({url})"


def provider_reason(decision: ProviderDecision) -> str:
    if decision.issues:
        return "; ".join(decision.issues[:4]).replace("|", "/")
    return "Evidence is sufficient only for internal evaluation; production remains blocked."


def review_markdown(decisions: list[ProviderDecision]) -> str:
    eligible = [decision for decision in decisions if decision.internal_eval_status == ELIGIBLE_INTERNAL_EVAL]
    lines = [
        "# TTS Provider Internal-Eval Review",
        "",
        "This local review is part of the English onboarding orchestrator. It does not call provider APIs, generate audio, or approve production audio.",
        "",
        "- Public audio status: `PUBLIC_AUDIO_RELEASE_BLOCKED`",
        "- Production approval status: `PRODUCTION_BLOCKED` for every provider",
        f"- Internal-evaluation eligible providers: `{len(eligible)}`",
        "- Real audio generated: `false`",
        "- Paid provider calls: `false`",
        "",
        "| Provider | Strategy | Standalone output | Voice rights | Internal eval | Production | Primary blocker |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for decision in decisions:
        provider = decision.provider
        lines.append(
            "| {display} | {strategy} | {standalone} | {voice_rights} | {internal_eval} | {production} | {blocker} |".format(
                display=normalized(provider.get("display_name")),
                strategy=normalized(provider.get("provider_strategy_status")),
                standalone=normalized(provider.get("standalone_audio_distribution_allowed")),
                voice_rights=normalized(provider.get("voice_rights_status")),
                internal_eval=decision.internal_eval_status,
                production=decision.public_production_status,
                blocker=provider_reason(decision),
            )
        )

    lines.extend(["", "## Provider Evidence", ""])
    for decision in decisions:
        provider = decision.provider
        lines.extend(
            [
                f"### {normalized(provider.get('display_name'))}",
                "",
                f"- Provider ID: `{normalized(provider.get('provider_id'))}`",
                f"- Official terms: {markdown_link('terms', provider.get('official_terms_url'))}",
                f"- Commercial-use evidence: {markdown_link('commercial evidence', provider.get('commercial_use_evidence_url'))}",
                f"- Voice license evidence: {markdown_link('voice evidence', provider.get('voice_license_evidence_url'))}",
                f"- Paid plan required: `{normalized(provider.get('paid_plan_required'))}`",
                f"- Paid plan evidence status: `{display_value(provider.get('plan_evidence_status'), 'missing')}`",
                f"- Paid plan evidence URL: {display_value(provider.get('paid_plan_evidence_url'), 'missing')}",
                f"- Beta features allowed: `{normalized(provider.get('beta_feature_allowed'))}`",
                f"- Beta features allowed alias: `{normalized(provider.get('beta_features_allowed'))}`",
                f"- Beta features excluded evidence: {display_value(provider.get('beta_features_excluded_evidence'), 'missing')}",
                f"- Standalone audio distribution: `{normalized(provider.get('standalone_audio_distribution_allowed'))}`",
                f"- Standalone audio distribution evidence: `{display_value(provider.get('standalone_audio_distribution_evidence'), 'missing')}`",
                f"- Attribution required: `{normalized(provider.get('attribution_required'))}`",
                f"- Commercial internal-eval permission: `{display_value(provider.get('commercial_internal_eval_permission'), 'missing')}`",
                f"- Provider terms review status: `{display_value(provider.get('provider_terms_review_status'), 'missing')}`",
                f"- Data retention review status: `{display_value(provider.get('data_retention_review_status'), 'missing')}`",
                f"- Data/privacy notes: {normalized(provider.get('data_retention_notes'))}",
                f"- Voice rights status: `{normalized(provider.get('voice_rights_status'))}`",
                f"- Selected voice ID: `{display_value(provider.get('selected_voice_id'))}`",
                f"- Selected voice display name: {display_value(provider.get('selected_voice_display_name'))}",
                f"- Selected voice type: `{display_value(provider.get('selected_voice_type'), 'unknown')}`",
                f"- Selected voice license evidence: {display_value(provider.get('selected_voice_license_evidence_url'), 'missing')}",
                f"- Selected voice rights summary: {display_value(provider.get('selected_voice_rights_summary'), 'missing')}",
                f"- Selected voice attribution: `{display_value(provider.get('selected_voice_attribution_requirement'), 'missing')}`",
                f"- Selected voice restrictions: `{display_value(provider.get('selected_voice_restrictions'), 'missing')}`",
                f"- Owner approval: `{normalized(provider.get('owner_approval_status'))}`",
                f"- Legal/internal review: `{normalized(provider.get('legal_review_status'))}`",
                f"- Internal-eval decision: `{decision.internal_eval_status}`",
                f"- Internal generation status: `{decision.internal_generation_status}`",
                f"- Public production status: `{decision.public_production_status}`",
                "",
                "Issues:",
            ]
        )
        lines.extend(f"- {issue}" for issue in decision.issues)
        if decision.warnings:
            lines.append("")
            lines.append("Warnings:")
            lines.extend(f"- {warning}" for warning in decision.warnings)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def scorecard_markdown(decisions: list[ProviderDecision]) -> str:
    lines = [
        "# TTS Provider Commercial Rights Scorecard",
        "",
        "| Provider | Commercial eval | Standalone evidence | Selected voice | Voice type | Owner approval | Legal review | Internal eval | Production |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for decision in decisions:
        provider = decision.provider
        lines.append(
            "| {display} | {commercial_eval} | {standalone} | {voice} | {voice_type} | {owner} | {legal} | {internal_eval} | {production} |".format(
                display=normalized(provider.get("display_name")),
                commercial_eval=display_value(provider.get("commercial_internal_eval_permission"), "missing"),
                standalone=normalized(provider.get("standalone_audio_distribution_evidence")),
                voice=display_value(provider.get("selected_voice_id")),
                voice_type=display_value(provider.get("selected_voice_type"), "unknown"),
                owner=normalized(provider.get("owner_approval_status")),
                legal=normalized(provider.get("legal_review_status")),
                internal_eval=decision.internal_eval_status,
                production=decision.public_production_status,
            )
        )
    lines.extend(
        [
            "",
            "- No provider is production-approved by this scorecard.",
            "- Provider use remains dry-run metadata only until commercial, selected-voice, owner, and legal evidence are complete.",
            "- Public audio remains `PUBLIC_AUDIO_RELEASE_BLOCKED`.",
            "",
        ]
    )
    return "\n".join(lines)


def elevenlabs_decision(decisions: list[ProviderDecision]) -> ProviderDecision:
    return selected_provider_decision("elevenlabs", decisions)


def elevenlabs_review_form_markdown(decisions: list[ProviderDecision]) -> str:
    decision = elevenlabs_decision(decisions)
    provider = decision.provider
    return "\n".join(
        [
            "# ElevenLabs Provider Owner/Legal Review Form",
            "",
            "This form is for manual evidence collection only. It does not approve internal generation, production use, public audio, or provider API calls.",
            "",
            "## Current Gate State",
            "",
            f"- Provider ID: `{normalized(provider.get('provider_id'))}`",
            f"- Display name: {normalized(provider.get('display_name'))}",
            f"- Current provider decision: `{decision.decision_status}`",
            f"- Current internal-eval status: `{decision.internal_eval_status}`",
            f"- Current production status: `{decision.public_production_status}`",
            "- Public audio status: `PUBLIC_AUDIO_RELEASE_BLOCKED`",
            "- Real audio generated: `false`",
            "- Decision must remain HOLD until every required field below is completed and reviewed.",
            "- Decision: HOLD / ELIGIBLE_INTERNAL_EVAL_ONLY / BLOCKED",
            "",
            "## Evidence Fields",
            "",
            "| Field | Current / Required Value | Owner/Legal Entry |",
            "| --- | --- | --- |",
            f"| Provider account/plan | Paid plan required: `{normalized(provider.get('paid_plan_required'))}`. Attach plan evidence URL or invoice reference. |  |",
            f"| Plan evidence status | Current: `{display_value(provider.get('plan_evidence_status'), 'missing')}`. Must become APPROVED or RECORDED. |  |",
            f"| Selected voice | Current: `{display_value(provider.get('selected_voice_id'))}`. Select exact voice ID and display name. |  |",
            f"| Selected voice type | Current: `{display_value(provider.get('selected_voice_type'), 'unknown')}`. Must be platform/provider voice or approved generated voice. |  |",
            f"| Selected voice rights summary | Current: {display_value(provider.get('selected_voice_rights_summary'), 'missing')}. Must be owner/legal reviewed. |  |",
            f"| Official commercial-use evidence | {display_value(provider.get('commercial_use_evidence_url'), 'missing')} plus owner/legal notes. |  |",
            f"| Beta features excluded | Current: `{normalized(provider.get('beta_feature_allowed'))}`. Must remain false. |  |",
            f"| Beta exclusion evidence | Current: {display_value(provider.get('beta_features_excluded_evidence'), 'missing')}. Must become APPROVED or RECORDED. |  |",
            f"| Standalone audio distribution evidence | Current: `{display_value(provider.get('standalone_audio_distribution_evidence'), 'missing')}`. Attach reviewed evidence. |  |",
            f"| Commercial internal-eval permission | Current: `{display_value(provider.get('commercial_internal_eval_permission'), 'missing')}`. Must become APPROVED or ALLOWED. |  |",
            f"| Attribution rules | Current: `{display_value(provider.get('attribution_required'), 'HOLD_REVIEW')}`. Record exact requirement. |  |",
            f"| Selected voice attribution | Current: `{display_value(provider.get('selected_voice_attribution_requirement'), 'missing')}`. Record exact requirement. |  |",
            f"| Selected voice restrictions | Current: `{display_value(provider.get('selected_voice_restrictions'), 'missing')}`. Record exact restrictions. |  |",
            f"| Provider terms review | Current: `{display_value(provider.get('provider_terms_review_status'), 'missing')}`. Must become APPROVED. |  |",
            f"| Data retention review | Current: `{display_value(provider.get('data_retention_review_status'), 'missing')}`. Must become APPROVED. |  |",
            f"| Data/privacy notes | {normalized(provider.get('data_retention_notes'))} |  |",
            f"| Voice license evidence | {display_value(provider.get('voice_license_evidence_url'), 'missing')} plus selected voice evidence. |  |",
            "| Owner approval | REQUIRED: reviewer name, date, and decision. |  |",
            "| Legal/internal review | REQUIRED: reviewer name, date, and decision. |  |",
            "| Decision | Choose one: HOLD / ELIGIBLE_INTERNAL_EVAL_ONLY / BLOCKED. | HOLD |",
            "| Notes | REQUIRED: rationale and unresolved questions. |  |",
            "| Required next action | REQUIRED: smallest next evidence or review step. |  |",
            "",
            "## Safety Confirmation",
            "",
            "- No provider API may be called from this form alone.",
            "- No real audio may be generated from this form alone.",
            "- No public audio URL, public listening CTA, or public audio JSON-LD metadata may be created.",
            "- Production status remains `PRODUCTION_BLOCKED`.",
            "- Public audio remains `PUBLIC_AUDIO_RELEASE_BLOCKED`.",
            "",
        ]
    )


def elevenlabs_checklist_markdown(decisions: list[ProviderDecision]) -> str:
    decision = elevenlabs_decision(decisions)
    provider = decision.provider
    return "\n".join(
        [
            "# ElevenLabs Provider Internal-Eval Checklist",
            "",
            "ElevenLabs cannot be promoted to `ELIGIBLE_INTERNAL_EVAL_ONLY` unless every checklist item is completed and reviewed.",
            "",
            "## Current Status",
            "",
            f"- Provider ID: `{normalized(provider.get('provider_id'))}`",
            f"- Internal-eval status: `{decision.internal_eval_status}`",
            f"- Production approval: `{decision.public_production_status}`",
            "- Public audio: `PUBLIC_AUDIO_RELEASE_BLOCKED`",
            "",
            "## Required Before Promotion",
            "",
            "- [ ] Paid provider plan evidence is documented.",
            "- [ ] Official commercial-use evidence is owner/legal reviewed.",
            "- [ ] Commercial internal-evaluation permission is approved or allowed.",
            "- [ ] Standalone audio distribution permission is owner/legal reviewed.",
            "- [ ] Beta features remain excluded.",
            "- [ ] Beta exclusion evidence is approved or recorded.",
            "- [ ] Exact selected voice ID and display name are recorded.",
            "- [ ] Selected voice type is platform/provider voice or approved generated voice.",
            "- [ ] Selected voice license and voice-rights evidence are documented.",
            "- [ ] Attribution requirements are understood and recorded.",
            "- [ ] Selected voice restrictions are understood and recorded.",
            "- [ ] Provider terms review is approved.",
            "- [ ] Data retention review is approved.",
            "- [ ] Data/privacy and retention notes are reviewed.",
            "- [ ] Owner approval is recorded with reviewer name and date.",
            "- [ ] Legal/internal review is complete and not blocked.",
            "- [ ] The decision is explicitly recorded as HOLD, ELIGIBLE_INTERNAL_EVAL_ONLY, or BLOCKED.",
            "",
            "## Non-Negotiable Blocks",
            "",
            "- If beta features are required, keep `BLOCKED`.",
            "- If selected voice evidence is missing, keep `HOLD_PROVIDER_REVIEW`.",
            "- If commercial standalone output evidence is missing, keep `HOLD_PROVIDER_REVIEW`.",
            "- If owner approval is missing, keep `HOLD_PROVIDER_REVIEW`.",
            "- If legal/internal review is blocked, set `BLOCKED`.",
            "- Do not mark production approved in this workflow.",
            "- Do not generate audio in this workflow.",
            "",
        ]
    )


def decision_payload(decisions: list[ProviderDecision]) -> dict[str, Any]:
    return {
        "generated_by": "scripts/tts_provider_internal_eval_review.py",
        "public_audio_release": "PUBLIC_AUDIO_RELEASE_BLOCKED",
        "production_audio_approved": False,
        "eligible_internal_eval_count": sum(1 for decision in decisions if decision.internal_eval_status == ELIGIBLE_INTERNAL_EVAL),
        "providers": [
            {
                "provider_id": decision.provider.get("provider_id"),
                "display_name": decision.provider.get("display_name"),
                "decision_status": decision.decision_status,
                "internal_eval_status": decision.internal_eval_status,
                "internal_generation_status": decision.internal_generation_status,
                "public_production_status": decision.public_production_status,
                "issues": decision.issues,
                "warnings": decision.warnings,
                "evidence": decision.provider,
            }
            for decision in decisions
        ],
    }


def path_key(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def write_reports(decisions: list[ProviderDecision], *, output_dir: Path | None = DEFAULT_SCOPED_OUTPUT_DIR) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    review = review_markdown(decisions)
    scorecard = scorecard_markdown(decisions)
    elevenlabs_form = elevenlabs_review_form_markdown(decisions)
    elevenlabs_checklist = elevenlabs_checklist_markdown(decisions)

    root_reports = {
        PROVIDER_REVIEW_REPORT_PATH: review,
        PROVIDER_SCORECARD_PATH: scorecard,
        ELEVENLABS_REVIEW_FORM_PATH: elevenlabs_form,
        ELEVENLABS_CHECKLIST_PATH: elevenlabs_checklist,
    }
    for path, text in root_reports.items():
        path.write_text(text, encoding="utf-8")
        paths[path_key(path)] = path

    if output_dir:
        if not output_dir.is_absolute():
            output_dir = ROOT / output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        scoped_reports = {
            output_dir / "TTS_PROVIDER_INTERNAL_EVAL_REVIEW.md": review,
            output_dir / "TTS_PROVIDER_COMMERCIAL_RIGHTS_SCORECARD.md": scorecard,
            output_dir / "ELEVENLABS_PROVIDER_OWNER_LEGAL_REVIEW_FORM.md": elevenlabs_form,
            output_dir / "ELEVENLABS_PROVIDER_INTERNAL_EVAL_CHECKLIST.md": elevenlabs_checklist,
            output_dir / "tts_provider_internal_eval_review.json": json.dumps(decision_payload(decisions), indent=2, ensure_ascii=False) + "\n",
        }
        for path, text in scoped_reports.items():
            path.write_text(text, encoding="utf-8")
            paths[path_key(path)] = path
    return paths


def selected_provider_decision(provider_id: str, decisions: list[ProviderDecision]) -> ProviderDecision:
    normalized_id = re.sub(r"[^a-z0-9-]+", "-", provider_id.strip().lower()).strip("-")
    for decision in decisions:
        if decision.provider.get("provider_id") == normalized_id:
            return decision
    return ProviderDecision(
        provider={"provider_id": normalized_id, "display_name": provider_id},
        decision_status=HOLD_PROVIDER_REVIEW,
        internal_eval_status=HOLD_PROVIDER_REVIEW,
        internal_generation_status=HOLD_PROVIDER_REVIEW,
        public_production_status=PRODUCTION_BLOCKED,
        issues=["selected provider is not configured."],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_SCOPED_OUTPUT_DIR)
    args = parser.parse_args()

    decisions = review_provider_candidates(args.config)
    paths = write_reports(decisions, output_dir=args.output_dir)
    eligible = sum(1 for decision in decisions if decision.internal_eval_status == ELIGIBLE_INTERNAL_EVAL)
    hold = sum(1 for decision in decisions if decision.internal_eval_status == HOLD_PROVIDER_REVIEW)
    blocked = sum(1 for decision in decisions if decision.internal_eval_status == BLOCKED)
    print(
        "TTS provider internal-eval review complete: "
        f"providers={len(decisions)} eligible_internal_eval={eligible} hold={hold} blocked={blocked} reports={len(paths)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
