#!/usr/bin/env python3
"""Validate the persistent Earnalism UX Governor policy surface."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_GOVERNOR_FILES = [
    "EARNALISM_PREMIUM_LIBRARY_UX_GOVERNOR.md",
    "figma_design_doctrine.md",
    "fixed_design_tokens.json",
    "ux_10_scorecard_schema.json",
    "home_page_10_spec.md",
    "library_page_10_spec.md",
    "reader_audiobook_10_spec.md",
    "cover_art_policy.md",
    "typography_policy.md",
    "release_gate_ux_policy.md",
    "visual_regression_policy.md",
    "conversion_growth_policy.md",
    "ux_decision_ledger.jsonl",
    "ux_sprint_learnings.md",
]

REQUIRED_FRONTEND_FILES = [
    "frontend/scripts/audit-book-covers.mjs",
    "frontend/scripts/visual-luxury-smoke.mjs",
    "frontend/src/lib/audioReleaseSafety.test.js",
]

REQUIRED_SCORE_CATEGORIES = [
    "premium_brand_identity",
    "visual_distinctiveness",
    "calmness",
    "typography_elegance",
    "color_consistency",
    "cover_quality",
    "information_hierarchy",
    "conversion_clarity",
    "catalog_discovery",
    "reader_comfort",
    "audiobook_experience",
    "settings_usefulness",
    "Bengali_typography",
    "English_typography",
    "mobile_experience",
    "accessibility",
    "performance",
    "SEO",
    "release_gate_truth",
    "no_regressions",
]

REQUIRED_TOKEN_COLORS = [
    "ivory",
    "ivorySoft",
    "paper",
    "sepia",
    "espresso",
    "charcoal",
    "burgundy",
    "burgundyDeep",
    "gold",
    "goldMuted",
    "sage",
    "indigoInk",
    "success",
    "warning",
    "danger",
    "focus",
]


def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:  # pragma: no cover - reported in JSON output
        return None, str(exc)


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    report_path = repo_root / "ux_governor_readiness_report.json"

    missing_governor_files = [
        item for item in REQUIRED_GOVERNOR_FILES if not (script_dir / item).is_file()
    ]
    missing_frontend_files = [
        item for item in REQUIRED_FRONTEND_FILES if not (repo_root / item).is_file()
    ]

    token_data, token_error = read_json(script_dir / "fixed_design_tokens.json")
    score_data, score_error = read_json(script_dir / "ux_10_scorecard_schema.json")

    token_color_keys = sorted((token_data or {}).get("colors", {}).keys())
    missing_token_colors = [
        color for color in REQUIRED_TOKEN_COLORS if color not in token_color_keys
    ]

    score_categories = (score_data or {}).get("categories", [])
    missing_score_categories = [
        category for category in REQUIRED_SCORE_CATEGORIES if category not in score_categories
    ]
    green_requirements = (score_data or {}).get("green_requirements", {})
    green_requirements_ok = (
        green_requirements.get("page_overall_min") == 9.8
        and green_requirements.get("category_min") == 9.6
        and green_requirements.get("no_release_gate_failure") is True
        and green_requirements.get("no_accessibility_failure") is True
        and green_requirements.get("no_typographic_only_public_cover") is True
        and green_requirements.get("no_unapproved_audio_exposure") is True
    )

    doc_checks = {}
    required_phrases = {
        "EARNALISM_PREMIUM_LIBRARY_UX_GOVERNOR.md": [
            "premium literary sanctuary",
            "Do not expose unapproved audiobooks",
        ],
        "home_page_10_spec.md": ["Dracula must not be the main brand hero"],
        "cover_art_policy.md": ["No typographic-only public covers"],
        "release_gate_ux_policy.md": ["section-following narration"],
    }
    for filename, phrases in required_phrases.items():
        path = script_dir / filename
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        doc_checks[filename] = {
            "exists": path.is_file(),
            "phrases_present": {phrase: phrase in text for phrase in phrases},
        }

    blockers = []
    if missing_governor_files:
        blockers.append("missing_governor_files")
    if missing_frontend_files:
        blockers.append("missing_frontend_validation_files")
    if token_error:
        blockers.append("fixed_design_tokens_json_invalid")
    if score_error:
        blockers.append("ux_scorecard_json_invalid")
    if missing_token_colors:
        blockers.append("missing_required_design_token_colors")
    if missing_score_categories:
        blockers.append("missing_required_score_categories")
    if not green_requirements_ok:
        blockers.append("green_requirements_incomplete")
    if any(
        not all(check["phrases_present"].values()) for check in doc_checks.values()
    ):
        blockers.append("required_policy_phrases_missing")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if not blockers else "FAIL",
        "repo_root": str(repo_root),
        "governor_dir": str(script_dir),
        "missing_governor_files": missing_governor_files,
        "missing_frontend_validation_files": missing_frontend_files,
        "token_json_status": "PASS" if not token_error else "FAIL",
        "token_json_error": token_error,
        "missing_token_colors": missing_token_colors,
        "scorecard_json_status": "PASS" if not score_error else "FAIL",
        "scorecard_json_error": score_error,
        "missing_score_categories": missing_score_categories,
        "green_requirements_ok": green_requirements_ok,
        "doc_checks": doc_checks,
        "blockers": blockers,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
