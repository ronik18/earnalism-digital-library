#!/usr/bin/env python3
"""Internal audiobook accessibility release gate.

This command is intentionally local and deterministic. It does not synthesize
audio, upload files, publish metadata, call providers, or mutate production
data. In the current launch state, a successful command means the gate correctly
kept public audiobook release blocked.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "output" / "audiobook_accessibility_gate"
DEFAULT_REPORT_PATH = ROOT / "AUDIOBOOK_ACCESSIBILITY_GATE_REPORT.md"

PUBLIC_AUDIO_RELEASE_BLOCKED = "PUBLIC_AUDIO_RELEASE_BLOCKED"
READY_FOR_INTERNAL_AUDIOBOOK_REVIEW = "READY_FOR_INTERNAL_AUDIOBOOK_REVIEW"
PASS_EXPECTED_BLOCKED = "PASS_EXPECTED_BLOCKED"
FAIL_PUBLIC_AUDIO_LEAK = "FAIL_PUBLIC_AUDIO_LEAK"

QA_THRESHOLD = 9.5
TEXT_SYNC_TOLERANCE_MS = 250
AUDIO_FILE_EXTENSIONS = {".aac", ".m4a", ".mp3", ".ogg", ".wav"}
AUDIO_SIDECAR_SUFFIXES = ("_chapters.json", "_highlight.vtt", "_meta.json", "_timestamps.json")

REQUIRED_PLAYER_ACCESSIBILITY_EVIDENCE = [
    "player_controls_accessible_names",
    "playback_controls_keyboard_reachable",
    "screen_reader_announcements_clear",
    "chapter_navigation_nonvisual",
    "current_chapter_announced",
    "playback_speed_control_accessible",
    "rewind_forward_controls_accessible",
    "resume_position_accessible",
    "bookmarks_accessible",
    "transcript_accessible",
    "low_network_error_states_accessible",
    "mobile_assistive_technology_checked",
]

REQUIRED_HUMAN_REVIEW_FIELDS = [
    "scorecard_present",
    "reviewer_named",
    "source_text_evidence_present",
    "derivative_rights_passed",
    "text_fidelity_passed",
    "legal_commercial_use_passed",
    "accessibility_listening_passed",
    "owner_approval_passed",
    "rollback_plan_passed",
]

PUBLIC_SURFACE_FILES = [
    "frontend/build/index.html",
    "frontend/build/book/dracula/index.html",
    "frontend/build/library/index.html",
    "frontend/build/pricing/index.html",
    "frontend/build/reader/dracula/index.html",
    "frontend/public/index.html",
    "frontend/public/sitemap.xml",
    "frontend/src/pages/Home.jsx",
    "frontend/src/pages/Library.jsx",
    "frontend/src/pages/BookDetail.jsx",
    "frontend/src/pages/Pricing.jsx",
    "frontend/src/components/BookCard.jsx",
    "frontend/src/lib/controlledLaunch.js",
]

PUBLIC_METADATA_FILES = [
    "frontend/build/index.html",
    "frontend/build/book/dracula/index.html",
    "frontend/build/library/index.html",
    "frontend/build/pricing/index.html",
    "frontend/build/reader/dracula/index.html",
    "frontend/public/index.html",
    "frontend/public/sitemap.xml",
]

POSITIVE_AUDIO_CLAIM_RE = re.compile(
    r"\b("
    r"audiobooks are live|"
    r"full audiobook (?:is )?(?:available|live|ready|published)|"
    r"dracula audio is available|"
    r"listen now|"
    r"play audiobook|"
    r"audiobook available|"
    r"synced audiobook ready"
    r")\b",
    re.IGNORECASE,
)

PUBLIC_AUDIO_METADATA_RE = re.compile(
    r"(AudioObject|audio_url|audiobook_url|audiobook_assets|/audio/[^\"'<> ]+\.mp3|https?://[^\"'<> ]+\.mp3)",
    re.IGNORECASE,
)

UNSUPPORTED_ACCESSIBILITY_CLAIMS_RE = re.compile(
    r"\b(blind[- ]user tested|WCAG compliant|screen[- ]reader certified|fully accessible audiobook platform)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GateBlocker:
    code: str
    severity: str
    category: str
    message: str


def read_text(relative_path: str) -> str:
    target = ROOT / relative_path
    if not target.exists() or not target.is_file():
        return ""
    return target.read_text(encoding="utf-8", errors="replace")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def value_present(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return bool(text) and text.lower() not in {
        "false",
        "missing",
        "none",
        "not approved",
        "owner_approval_required",
        "unknown",
        "tbd",
        "todo",
    }


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "approved", "pass", "passed", "qa_passed"}


def safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def strip_negated_audio_safety_copy(text: str) -> str:
    patterns = [
        r"No unapproved title offers Start Reading, Read Preview, or Listen Now\.",
        r"Audio is not available yet\.",
        r"Audio controls hidden\.",
        r"Dracula audiobook is not available yet\.",
        r"no play buttons, waveforms, or audiobook CTAs",
        r"no listening CTA is shown",
        r"No `Listen Now` CTA or public audiobook metadata was added\.",
        r"Listen Now CTAs? remain blocked",
    ]
    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return cleaned


def scan_public_surface() -> dict[str, Any]:
    public_text = "\n".join(read_text(path) for path in PUBLIC_SURFACE_FILES)
    metadata_text = "\n".join(read_text(path) for path in PUBLIC_METADATA_FILES)
    positive_claim_text = strip_negated_audio_safety_copy(public_text)

    public_static_audio_files = find_audio_like_files(ROOT / "frontend" / "public")
    public_build_audio_files = find_audio_like_files(ROOT / "frontend" / "build")

    return {
        "public_audio_claim_found": bool(POSITIVE_AUDIO_CLAIM_RE.search(positive_claim_text)),
        "public_audio_metadata_found": bool(PUBLIC_AUDIO_METADATA_RE.search(metadata_text)),
        "unsupported_accessibility_claim_found": bool(UNSUPPORTED_ACCESSIBILITY_CLAIMS_RE.search(public_text)),
        "public_audio_asset_count": len(public_static_audio_files),
        "public_audio_asset_bytes": sum(path.stat().st_size for path in public_static_audio_files),
        "public_audio_asset_paths": [str(path.relative_to(ROOT)) for path in public_static_audio_files],
        "public_build_audio_asset_count": len(public_build_audio_files),
        "public_build_audio_asset_bytes": sum(path.stat().st_size for path in public_build_audio_files),
        "public_build_audio_asset_paths": [str(path.relative_to(ROOT)) for path in public_build_audio_files],
        "public_surface_file_count": sum(1 for path in PUBLIC_SURFACE_FILES if (ROOT / path).exists()),
        "metadata_file_count": sum(1 for path in PUBLIC_METADATA_FILES if (ROOT / path).exists()),
    }


def is_audio_like_file(path: Path) -> bool:
    name = path.name.lower()
    if path.suffix.lower() in AUDIO_FILE_EXTENSIONS:
        return True
    return "audio" in {part.lower() for part in path.parts} and name.endswith(AUDIO_SIDECAR_SUFFIXES)


def find_audio_like_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file() and is_audio_like_file(path))


def current_repo_payload() -> dict[str, Any]:
    surface = scan_public_surface()
    truth_ledger = read_text("PRODUCT_TRUTH_LEDGER.md")
    readiness = read_text("AUDIOBOOK_READINESS_REPORT.md")
    readiness_status_match = re.search(r"Status:\s+`([^`]+)`", readiness)
    readiness_status = readiness_status_match.group(1) if readiness_status_match else "UNKNOWN"
    first_batch = read_text("FIRST_BATCH_RIGHTS_EVIDENCE_SCORECARD.md")

    return {
        "public_audio_enabled": False,
        "public_listen_now_cta": surface["public_audio_claim_found"],
        "public_audiobook_metadata": surface["public_audio_metadata_found"],
        "public_audio_url_exposed": False,
        "public_audio_asset_count": surface["public_audio_asset_count"],
        "public_audio_asset_paths": surface["public_audio_asset_paths"],
        "public_build_audio_asset_count": surface["public_build_audio_asset_count"],
        "public_build_audio_asset_paths": surface["public_build_audio_asset_paths"],
        "unsupported_accessibility_claim_found": surface["unsupported_accessibility_claim_found"],
        "source_text_approved": "Dracula is the only currently approved core public reading release" in truth_ledger,
        "derivative_audiobook_rights_approved": False,
        "model_commercial_use_permission": "",
        "model_license_evidence": "",
        "voice_narrator_rights": "",
        "real_person_voice_cloning_risk_resolved": False,
        "transcript_required": True,
        "transcript_present": False,
        "text_audio_sync_tolerance_ms": None,
        "player_accessibility_evidence": {},
        "bengali_qa_score": None,
        "english_qa_score": None,
        "required_narration_review_languages": ["bengali", "english"],
        "bengali_human_review": {
            "scorecard_present": False,
            "final_score": None,
            "text_fidelity_passed": False,
            "legal_commercial_use_passed": False,
            "derivative_rights_passed": False,
            "owner_approval_passed": False,
            "accessibility_listening_passed": False,
            "rollback_plan_passed": False,
        },
        "english_human_review": {
            "scorecard_present": False,
            "final_score": None,
            "text_fidelity_passed": False,
            "legal_commercial_use_passed": False,
            "derivative_rights_passed": False,
            "owner_approval_passed": False,
            "accessibility_listening_passed": False,
            "rollback_plan_passed": False,
        },
        "draft_pr_44_evidence_treated_as_release_approval": False,
        "draft_pr_45_evidence_treated_as_release_approval": False,
        "owner_approval_status": "",
        "rollback_plan": "",
        "dracula_audio_disabled": "Dracula audio remains disabled" in truth_ledger,
        "kshudhita_pipeline_only": "Kshudhita Pashan remains pipeline-only" in truth_ledger,
        "first_batch_audio_rights_blocked": "Audiobook derivative rights are not approved" in first_batch,
        "audio_readiness_report_status": readiness_status,
        "surface_scan": surface,
    }


def score_from_blockers(blockers: list[GateBlocker]) -> dict[str, float]:
    legal = 9.8
    narration = 9.6
    accessibility = 9.4
    public_surface = 9.5

    for blocker in blockers:
        if blocker.category in {"rights", "license", "voice", "legal_review", "derivative_rights"}:
            legal -= 1.8
        if blocker.category in {"bengali_qa", "english_qa", "transcript", "human_review", "text_fidelity"}:
            narration -= 1.2
        if blocker.category in {"player_accessibility", "transcript", "accessibility_review"}:
            accessibility -= 1.0
        if blocker.category in {"public_surface", "public_audio_assets"}:
            public_surface -= 1.5

    return {
        "current_audiobook_readiness": max(0.0, min(10.0, round((legal + narration + accessibility + public_surface) / 4, 1))),
        "accessibility_readiness": max(0.0, min(10.0, round(accessibility, 1))),
        "narration_quality_readiness": max(0.0, min(10.0, round(narration, 1))),
        "legal_rights_readiness": max(0.0, min(10.0, round(legal, 1))),
        "public_surface_safety": max(0.0, min(10.0, round(public_surface, 1))),
    }


def evaluate_release_gate(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = payload or current_repo_payload()
    blockers: list[GateBlocker] = []

    def block(code: str, severity: str, category: str, message: str) -> None:
        blockers.append(GateBlocker(code=code, severity=severity, category=category, message=message))

    if truthy(data.get("public_audio_enabled")):
        block("PUBLIC_AUDIO_ENABLED", "CRITICAL", "public_surface", "Public audio is enabled before explicit owner approval.")
    if truthy(data.get("public_listen_now_cta")):
        block("PUBLIC_LISTEN_NOW_CTA", "CRITICAL", "public_surface", "A public Listen Now or equivalent audiobook CTA was detected.")
    if truthy(data.get("public_audiobook_metadata")):
        block("PUBLIC_AUDIOBOOK_METADATA", "CRITICAL", "public_surface", "Public AudioObject or audiobook metadata was detected.")
    if truthy(data.get("public_audio_url_exposed")):
        block("PUBLIC_AUDIO_URL_EXPOSED", "CRITICAL", "public_surface", "A public audiobook URL was exposed before approval.")
    if truthy(data.get("unsupported_accessibility_claim_found")):
        block("UNSUPPORTED_ACCESSIBILITY_CLAIM", "CRITICAL", "public_surface", "Unsupported accessibility claim was detected on the public surface.")
    if int(data.get("public_audio_asset_count") or 0) > 0:
        block(
            "FRONTEND_PUBLIC_AUDIO_ASSETS_PRESENT",
            "CRITICAL",
            "public_surface",
            "Audio-like files exist under frontend/public and are directly reachable by URL.",
        )
    if int(data.get("public_build_audio_asset_count") or 0) > 0:
        block(
            "FRONTEND_BUILD_AUDIO_ASSETS_PRESENT",
            "CRITICAL",
            "public_surface",
            "Audio-like files exist under frontend/build and could be deployed as static assets.",
        )

    if not truthy(data.get("source_text_approved")):
        block("SOURCE_TEXT_NOT_APPROVED", "CRITICAL", "rights", "Approved source text evidence is missing.")
    if not truthy(data.get("derivative_audiobook_rights_approved")):
        block("DERIVATIVE_AUDIOBOOK_RIGHTS_MISSING", "CRITICAL", "rights", "Derivative audiobook rights approval is missing.")
    if not value_present(data.get("model_commercial_use_permission")):
        block("MODEL_COMMERCIAL_USE_PERMISSION_MISSING", "CRITICAL", "license", "Model commercial-use permission is undocumented.")
    if not value_present(data.get("model_license_evidence")):
        block("MODEL_LICENSE_EVIDENCE_MISSING", "CRITICAL", "license", "Model license evidence is missing.")
    if not value_present(data.get("voice_narrator_rights")):
        block("VOICE_NARRATOR_RIGHTS_MISSING", "CRITICAL", "voice", "Voice or narrator rights evidence is missing.")
    if not truthy(data.get("real_person_voice_cloning_risk_resolved")):
        block("VOICE_CLONING_RISK_UNRESOLVED", "CRITICAL", "voice", "Real-person voice cloning risk is unresolved.")

    if truthy(data.get("transcript_required")) and not truthy(data.get("transcript_present")):
        block("TRANSCRIPT_REQUIRED_MISSING", "HIGH", "transcript", "Transcript is required and missing.")

    sync_ms = data.get("text_audio_sync_tolerance_ms")
    if sync_ms is None:
        block("SYNC_TOLERANCE_MISSING", "HIGH", "transcript", "Text/audio sync tolerance evidence is missing.")
    else:
        try:
            if float(sync_ms) > TEXT_SYNC_TOLERANCE_MS:
                block("SYNC_TOLERANCE_TOO_HIGH", "HIGH", "transcript", "Text/audio sync tolerance exceeds 250 ms.")
        except (TypeError, ValueError):
            block("SYNC_TOLERANCE_INVALID", "HIGH", "transcript", "Text/audio sync tolerance is invalid.")

    player_evidence = data.get("player_accessibility_evidence") or {}
    for field in REQUIRED_PLAYER_ACCESSIBILITY_EVIDENCE:
        if not truthy(player_evidence.get(field)):
            block(
                f"{field.upper()}_MISSING",
                "HIGH",
                "player_accessibility",
                f"Player accessibility evidence missing: {field}.",
            )

    for language, key in (("Bengali", "bengali_qa_score"), ("English", "english_qa_score")):
        score = data.get(key)
        category = "bengali_qa" if language == "Bengali" else "english_qa"
        if score is None:
            block(f"{language.upper()}_QA_SCORE_MISSING", "HIGH", category, f"{language} listening QA score is missing.")
            continue
        try:
            if float(score) < QA_THRESHOLD:
                block(
                    f"{language.upper()}_QA_SCORE_BELOW_THRESHOLD",
                    "HIGH",
                    category,
                    f"{language} listening QA score is below {QA_THRESHOLD}.",
                )
        except (TypeError, ValueError):
            block(f"{language.upper()}_QA_SCORE_INVALID", "HIGH", category, f"{language} listening QA score is invalid.")

    required_languages = data.get("required_narration_review_languages") or ["bengali", "english"]
    normalized_languages = {str(language).strip().lower() for language in required_languages if str(language).strip()}
    for language in ("bengali", "english"):
        if language not in normalized_languages:
            continue
        label = "Bengali" if language == "bengali" else "English"
        review = data.get(f"{language}_human_review") or {}
        if not truthy(review.get("scorecard_present")):
            block(
                f"{label.upper()}_HUMAN_REVIEW_SCORECARD_MISSING",
                "CRITICAL",
                "human_review",
                f"{label} human-review scorecard is missing.",
            )

        for field in REQUIRED_HUMAN_REVIEW_FIELDS:
            if field == "scorecard_present":
                continue
            if not truthy(review.get(field)):
                category = {
                    "derivative_rights_passed": "derivative_rights",
                    "text_fidelity_passed": "text_fidelity",
                    "legal_commercial_use_passed": "legal_review",
                    "accessibility_listening_passed": "accessibility_review",
                    "owner_approval_passed": "owner_approval",
                    "rollback_plan_passed": "rollback",
                }.get(field, "human_review")
                block(
                    f"{label.upper()}_HUMAN_REVIEW_{field.upper()}_MISSING",
                    "CRITICAL" if category in {"derivative_rights", "legal_review", "owner_approval"} else "HIGH",
                    category,
                    f"{label} human-review field is missing or failed: {field}.",
                )

        sample_minutes = safe_float(review.get("sample_duration_minutes"))
        if sample_minutes is None or sample_minutes <= 0:
            block(
                f"{label.upper()}_HUMAN_REVIEW_SAMPLE_DURATION_MISSING",
                "HIGH",
                "human_review",
                f"{label} human-review sample duration is missing.",
            )

        final_score = safe_float(review.get("final_score"))
        if final_score is None:
            block(
                f"{label.upper()}_HUMAN_REVIEW_FINAL_SCORE_MISSING",
                "HIGH",
                "human_review",
                f"{label} human-review final score is missing.",
            )
        elif final_score < QA_THRESHOLD:
            block(
                f"{label.upper()}_HUMAN_REVIEW_FINAL_SCORE_BELOW_THRESHOLD",
                "HIGH",
                "human_review",
                f"{label} human-review final score is below {QA_THRESHOLD}.",
            )

    if truthy(data.get("draft_pr_44_evidence_treated_as_release_approval")):
        block(
            "DRAFT_PR_44_EVIDENCE_TREATED_AS_RELEASE_APPROVAL",
            "CRITICAL",
            "human_review",
            "Draft PR #44 evidence must not be treated as public Bengali audiobook release approval.",
        )
    if truthy(data.get("draft_pr_45_evidence_treated_as_release_approval")):
        block(
            "DRAFT_PR_45_EVIDENCE_TREATED_AS_RELEASE_APPROVAL",
            "CRITICAL",
            "human_review",
            "Draft PR #45 evidence must not be treated as public English audiobook release approval.",
        )

    if str(data.get("owner_approval_status") or "").strip().lower() != "approved":
        block("OWNER_APPROVAL_MISSING", "CRITICAL", "owner_approval", "Owner approval for public audiobook release is missing.")
    if not value_present(data.get("rollback_plan")):
        block("ROLLBACK_PLAN_MISSING", "HIGH", "rollback", "Rollback plan is missing.")

    status = PUBLIC_AUDIO_RELEASE_BLOCKED if blockers else READY_FOR_INTERNAL_AUDIOBOOK_REVIEW
    public_leak = any(blocker.category == "public_surface" for blocker in blockers)
    command_status = FAIL_PUBLIC_AUDIO_LEAK if public_leak else PASS_EXPECTED_BLOCKED

    result = {
        "status": status,
        "command_status": command_status,
        "public_audio_publish_allowed": False,
        "public_audio_release_blocked": status == PUBLIC_AUDIO_RELEASE_BLOCKED,
        "qa_threshold": QA_THRESHOLD,
        "text_sync_tolerance_ms": TEXT_SYNC_TOLERANCE_MS,
        "scores": score_from_blockers(blockers),
        "blockers": [asdict(blocker) for blocker in blockers],
        "blocker_count": len(blockers),
        "owner_approval_checklist": [
            "Approve exact book, edition, language, voice/provider, and release scope.",
            "Approve derivative audiobook rights and source-license evidence.",
            "Approve completed Bengali and English human-review scorecards at or above 9.5.",
            "Approve text fidelity, legal/commercial-use, derivative-rights, accessibility listening, and rollback fields in each scorecard.",
            "Approve player accessibility evidence from keyboard and screen-reader checks.",
            "Approve rollback owner, rollback command, and takedown response path.",
        ],
        "rollback_instructions": [
            "Keep audio_enabled_slugs empty.",
            "Remove or unlink any audiobook endpoint, AudioObject metadata, and Listen Now CTA.",
            "Remove public audio URLs from public projections, sitemap, static snapshots, and social previews.",
            "Regenerate static SEO snapshots and rerun post-deploy canaries.",
        ],
        "evidence_summary": {
            "dracula_audio_disabled": truthy(data.get("dracula_audio_disabled")),
            "kshudhita_pipeline_only": truthy(data.get("kshudhita_pipeline_only")),
            "first_batch_audio_rights_blocked": truthy(data.get("first_batch_audio_rights_blocked")),
            "audio_readiness_report_status": data.get("audio_readiness_report_status", "UNKNOWN"),
            "public_audio_asset_count": int(data.get("public_audio_asset_count") or 0),
            "public_build_audio_asset_count": int(data.get("public_build_audio_asset_count") or 0),
            "public_audio_asset_paths": data.get("public_audio_asset_paths") or [],
            "public_build_audio_asset_paths": data.get("public_build_audio_asset_paths") or [],
            "bengali_human_review_scorecard_present": truthy((data.get("bengali_human_review") or {}).get("scorecard_present")),
            "english_human_review_scorecard_present": truthy((data.get("english_human_review") or {}).get("scorecard_present")),
            "bengali_human_review_final_score": (data.get("bengali_human_review") or {}).get("final_score"),
            "english_human_review_final_score": (data.get("english_human_review") or {}).get("final_score"),
            "draft_pr_44_evidence_treated_as_release_approval": truthy(
                data.get("draft_pr_44_evidence_treated_as_release_approval")
            ),
            "draft_pr_45_evidence_treated_as_release_approval": truthy(
                data.get("draft_pr_45_evidence_treated_as_release_approval")
            ),
        },
    }
    return result


def load_payload(path: Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def markdown_report(result: dict[str, Any]) -> str:
    blockers = result["blockers"]
    blocker_rows = "\n".join(
        f"| {item['severity']} | {item['category']} | {item['code']} | {item['message']} |" for item in blockers
    )
    if not blocker_rows:
        blocker_rows = "| none | none | none | none |"

    scores = result["scores"]
    evidence = result["evidence_summary"]

    return f"""# Audiobook Accessibility Gate Report

Status: `{result['status']}`

Command status: `{result['command_status']}`

This report is an internal release gate for future Bengali and English audiobooks. It does not publish audio, expose audio URLs, call providers, or approve public audiobook claims. A passing command today means public audiobook release remains blocked safely.

## Scores

| Area | Score |
| --- | ---: |
| Current audiobook readiness | {scores['current_audiobook_readiness']}/10 |
| Accessibility readiness | {scores['accessibility_readiness']}/10 |
| Narration quality readiness | {scores['narration_quality_readiness']}/10 |
| Legal/rights readiness | {scores['legal_rights_readiness']}/10 |
| Public-surface safety | {scores['public_surface_safety']}/10 |

## Current Evidence

| Signal | Value |
| --- | --- |
| Dracula audio disabled | `{str(evidence['dracula_audio_disabled']).lower()}` |
| Kshudhita Pashan pipeline-only | `{str(evidence['kshudhita_pipeline_only']).lower()}` |
| First-batch audiobook rights blocked | `{str(evidence['first_batch_audio_rights_blocked']).lower()}` |
| Audio readiness report status | `{evidence['audio_readiness_report_status']}` |
| Frontend public audio-like asset count | `{evidence['public_audio_asset_count']}` |
| Frontend build audio-like asset count | `{evidence['public_build_audio_asset_count']}` |
| Bengali human-review scorecard present | `{str(evidence['bengali_human_review_scorecard_present']).lower()}` |
| Bengali human-review final score | `{evidence['bengali_human_review_final_score']}` |
| English human-review scorecard present | `{str(evidence['english_human_review_scorecard_present']).lower()}` |
| English human-review final score | `{evidence['english_human_review_final_score']}` |
| Draft PR #44 evidence treated as release approval | `{str(evidence['draft_pr_44_evidence_treated_as_release_approval']).lower()}` |
| Draft PR #45 evidence treated as release approval | `{str(evidence['draft_pr_45_evidence_treated_as_release_approval']).lower()}` |

## Blockers

| Severity | Category | Code | Message |
| --- | --- | --- | --- |
{blocker_rows}

## Owner Approval Checklist

{chr(10).join(f"- [ ] {item}" for item in result['owner_approval_checklist'])}

## Rollback Instructions

{chr(10).join(f"- {item}" for item in result['rollback_instructions'])}

## Files Changed

- `scripts/audiobook_accessibility_release_gate.py`
- `backend/tests/test_audiobook_accessibility_release_gate.py`
- `AUDIOBOOK_ACCESSIBILITY_10_10_RELEASE_CRITERIA.md`
- `ACCESSIBLE_AUDIOBOOK_USER_JOURNEY.md`
- `AUDIOBOOK_ACCESSIBILITY_GATE_REPORT.md`
- `AUDIOBOOK_ASSET_QUARANTINE_REPORT.md`
- `AUDIOBOOK_READINESS_REPORT.md`
- `regression/modules/11-seo.test.js`
- `regression/modules/14-ux-conversion-static.test.js`
- `package.json`
- `internal/audio_quarantine/frontend-public-audio/`

## Tests Run

Validation commands are recorded in the final operator response for this change. The gate command to rerun is:

```bash
npm run audiobook:release-gate
```

## Safety Decision

`PUBLIC_AUDIO_RELEASE_BLOCKED`: safe for internal governance only. Not safe for public audiobook launch.
"""


def write_reports(result: dict[str, Any], output_dir: Path, report_path: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "audiobook_accessibility_gate_report.json", result)
    (output_dir / "audiobook_accessibility_gate_report.md").write_text(markdown_report(result), encoding="utf-8")
    report_path.write_text(markdown_report(result), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Optional JSON payload for local fixture evaluation.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--expect-blocked", action="store_true", default=True)
    args = parser.parse_args()

    payload = load_payload(args.input)
    result = evaluate_release_gate(payload)
    write_reports(result, args.output_dir, args.report_path)

    print(f"Audiobook accessibility release gate: {result['status']}")
    print(f"Command status: {result['command_status']}")
    print(f"Blockers: {result['blocker_count']}")
    print(f"Report: {args.report_path}")

    if result["command_status"] == FAIL_PUBLIC_AUDIO_LEAK:
        return 1
    if not args.expect_blocked and result["status"] != READY_FOR_INTERNAL_AUDIOBOOK_REVIEW:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
