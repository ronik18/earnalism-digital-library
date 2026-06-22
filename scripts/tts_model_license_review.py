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

ELIGIBLE_INTERNAL_EVAL = "ELIGIBLE_INTERNAL_EVAL"
HOLD_LICENSE_REVIEW = "HOLD_LICENSE_REVIEW"
BLOCKED = "BLOCKED"
UNKNOWN_VALUES = {"", "unknown", "hold_review", "tbd", "todo", "missing", "none"}
VALID_COMMERCIAL_USE = {"ALLOWED", "HOLD_REVIEW", "BLOCKED", "UNKNOWN"}
VALID_PRODUCTION_STATUS = {ELIGIBLE_INTERNAL_EVAL, HOLD_LICENSE_REVIEW, BLOCKED}
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
)


@dataclass(frozen=True)
class CandidateDecision:
    candidate: dict[str, Any]
    decision_status: str
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
    return str(value or "").strip()


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
        and production_status == ELIGIBLE_INTERNAL_EVAL
        and not (gpl_risk and not owner_approved)
        and upper(candidate.get("voice_cloning_risk")) != "HIGH"
        and upper(candidate.get("real_person_voice_risk")) != "HIGH"
    )

    if complete_internal_evidence:
        internal_generation_status = "ELIGIBLE_INTERNAL_EVAL_ONLY"
        decision_status = ELIGIBLE_INTERNAL_EVAL
    elif production_status == BLOCKED or commercial == "BLOCKED" or "high" in normalized(candidate.get("voice_cloning_risk")).lower():
        internal_generation_status = BLOCKED
        decision_status = BLOCKED
    else:
        internal_generation_status = HOLD_LICENSE_REVIEW
        decision_status = HOLD_LICENSE_REVIEW

    public_production_status = "PRODUCTION_BLOCKED"
    if complete_internal_evidence and owner_approved:
        public_production_status = "OWNER_REVIEW_STILL_REQUIRED"

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
        "| Candidate | Commercial use | Code license | Weights license | Voice license | English | Bengali | Decision | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for decision in decisions:
        candidate = decision.candidate
        notes = "; ".join(decision.issues[:2]) if decision.issues else normalized(candidate.get("evidence_notes"))
        lines.append(
            "| {display} | {commercial} | {code} | {weights} | {voice} | {english} | {bengali} | {decision} | {notes} |".format(
                display=normalized(candidate.get("display_name")),
                commercial=normalized(candidate.get("commercial_use_status")),
                code=normalized(candidate.get("code_license")),
                weights=normalized(candidate.get("weights_license")),
                voice=normalized(candidate.get("voice_license")),
                english=normalized(candidate.get("english_suitability")),
                bengali=normalized(candidate.get("bengali_suitability")),
                decision=decision.decision_status,
                notes=notes.replace("|", "/"),
            )
        )
    return "\n".join(lines) + "\n"


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


def decision_payload(decisions: list[CandidateDecision]) -> dict[str, Any]:
    return {
        "generated_by": "scripts/tts_model_license_review.py",
        "public_audio_release": "PUBLIC_AUDIO_RELEASE_BLOCKED",
        "production_audio_approved": False,
        "candidates": [
            {
                "candidate_id": decision.candidate.get("candidate_id"),
                "display_name": decision.candidate.get("display_name"),
                "decision_status": decision.decision_status,
                "internal_generation_status": decision.internal_generation_status,
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
    MATRIX_REPORT_PATH.write_text(matrix, encoding="utf-8")
    ELIGIBILITY_REPORT_PATH.write_text(eligibility, encoding="utf-8")
    paths[path_key(MATRIX_REPORT_PATH)] = MATRIX_REPORT_PATH
    paths[path_key(ELIGIBILITY_REPORT_PATH)] = ELIGIBILITY_REPORT_PATH
    if output_dir:
        if not output_dir.is_absolute():
            output_dir = ROOT / output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        matrix_path = output_dir / "TTS_MODEL_LICENSE_EVIDENCE_MATRIX.md"
        eligibility_path = output_dir / "TTS_MODEL_PRODUCTION_ELIGIBILITY_REPORT.md"
        json_path = output_dir / "tts_model_license_review.json"
        matrix_path.write_text(matrix, encoding="utf-8")
        eligibility_path.write_text(eligibility, encoding="utf-8")
        json_path.write_text(json.dumps(decision_payload(decisions), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        paths[path_key(matrix_path)] = matrix_path
        paths[path_key(eligibility_path)] = eligibility_path
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
    hold = sum(1 for decision in decisions if decision.decision_status == HOLD_LICENSE_REVIEW)
    eligible = sum(1 for decision in decisions if decision.decision_status == ELIGIBLE_INTERNAL_EVAL)
    print(
        "TTS model license review complete: "
        f"candidates={len(decisions)} eligible_internal_eval={eligible} hold={hold} blocked={blocked} reports={len(paths)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
