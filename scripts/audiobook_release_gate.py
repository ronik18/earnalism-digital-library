#!/usr/bin/env python3
"""Audit whether regenerated audiobook narration may be publicly released."""

from __future__ import annotations

import json
import re
import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import catalog_truth
from scripts.audiobook_regeneration_workflow import (
    OUTPUT_ROOT,
    REQUEST_PATH,
    load_context,
    read_json,
    write_json,
    write_text,
)


REPORT_PATH = ROOT / "AUDIOBOOK_RELEASE_GATE_REPORT.md"
SITEMAP_PATH = ROOT / "frontend" / "public" / "sitemap.xml"
FRONTEND_FILES = [
    ROOT / "frontend" / "src" / "pages" / "Home.jsx",
    ROOT / "frontend" / "src" / "pages" / "Library.jsx",
    ROOT / "frontend" / "src" / "components" / "BookCard.jsx",
]

PROHIBITED_CLAIMS = [
    re.compile(r"\bno ai touch\b", re.IGNORECASE),
    re.compile(r"\bfully human narrated\b", re.IGNORECASE),
    re.compile(r"\brecorded by professional actor\b", re.IGNORECASE),
    re.compile(r"\bstudio recorded\b", re.IGNORECASE),
    re.compile(r"\bofficial tagore narration\b", re.IGNORECASE),
]

ACCEPTABLE_AFTER_APPROVAL = [
    "Premium Bengali Gothic audio preview",
    "Human-reviewed narration",
    "Punctuation-aware Bengali narration",
    "Emotion-sensitive literary audio",
]


@dataclass
class ReleaseGateResult:
    status: str
    blockers: list[str]
    warnings: list[str]
    public_release_allowed: bool
    full_audiobook_allowed: bool
    preview_allowed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "public_release_allowed": self.public_release_allowed,
            "full_audiobook_allowed": self.full_audiobook_allowed,
            "preview_allowed": self.preview_allowed,
        }


def approval_value(request: dict[str, Any], key: str) -> bool:
    approval = request.get("approvals", {}).get(key, {})
    return isinstance(approval, dict) and approval.get("approved") is True


def claim_issues(copy: str, *, human_recorded_proof: bool = False) -> list[str]:
    issues: list[str] = []
    for pattern in PROHIBITED_CLAIMS:
        if pattern.search(copy or ""):
            if "human" in pattern.pattern.lower() or "actor" in pattern.pattern.lower() or "studio" in pattern.pattern.lower():
                if human_recorded_proof:
                    continue
            issues.append(f"Prohibited or unsupported public claim: {pattern.pattern}")
    return issues


def sitemap_has_audio_entries() -> bool:
    if not SITEMAP_PATH.exists():
        return False
    text = SITEMAP_PATH.read_text(encoding="utf-8", errors="ignore").lower()
    return "audiobook" in text or "/audio" in text or "listen-now" in text


def frontend_cta_issues() -> list[str]:
    issues: list[str] = []
    for path in FRONTEND_FILES:
        text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
        if "Listen Now" in text and "kshudhita" in text.lower():
            issues.append(f"{path.relative_to(ROOT)} contains Kshudhita Listen Now copy.")
        if "Full Audiobook" in text and "kshudhita" in text.lower():
            issues.append(f"{path.relative_to(ROOT)} contains Kshudhita Full Audiobook copy.")
    return issues


def public_projection_audio_issues() -> list[str]:
    projection = catalog_truth.public_book_projection(
        {
            "slug": "kshudhita-pashan",
            "title": "Kshudhita Pashan",
            "is_published": True,
            "pipeline_stage": "PIPELINE_ONLY",
            "audiobook_assets": {"mp3": "https://cdn.example.com/kshudhita.mp3"},
            "audio_url": "https://cdn.example.com/kshudhita.mp3",
        }
    )
    serialized = json.dumps(projection, ensure_ascii=False)
    issues: list[str] = []
    if projection.get("audio_enabled") is not False:
        issues.append("Kshudhita public projection enables audio.")
    if projection.get("audiobook_enabled") is not False:
        issues.append("Kshudhita public projection enables audiobook.")
    if projection.get("audio_url"):
        issues.append("Kshudhita public projection exposes audio_url.")
    if "cdn.example.com" in serialized or "audiobook_assets" in serialized:
        issues.append("Kshudhita public projection leaks audio asset data.")
    return issues


def evaluate_release_gate(
    request: dict[str, Any],
    profile: dict[str, Any],
    *,
    qa_score: float | None = None,
    public_disclosure_copy: str = "",
    manifest: dict[str, Any] | None = None,
) -> ReleaseGateResult:
    blockers: list[str] = []
    warnings: list[str] = []

    for key in ("owner", "rights", "source_text", "voice_style", "qa", "product_release"):
        if not approval_value(request, key):
            blockers.append(f"{key} approval is missing.")
    if request.get("publication_status") != "PIPELINE_ONLY":
        blockers.append("Kshudhita Pashan must remain pipeline-only until a separate publication approval.")
    if request.get("rights_status") != "RIGHTS_APPROVED":
        blockers.append("Rights approval is missing.")
    if request.get("source_text_status") != "SOURCE_TEXT_APPROVED":
        blockers.append("Source-text approval is missing.")
    if profile.get("owner_approved") is not True or profile.get("allowed_for_public_release") is not True:
        blockers.append("Voice profile is not approved for public release.")
    if str(profile.get("voice_source_type") or "").upper() == "REAL_PERSON_CLONE":
        blockers.append("Unauthorized voice clone profile is blocked.")
    if request.get("public_release_allowed") is not True:
        blockers.append("Public audio release is disabled.")
    if request.get("preview_allowed") is not True:
        blockers.append("Public preview is disabled.")
    if request.get("full_audiobook_allowed") is True and not request.get("approval_status") == "FULL_AUDIOBOOK_APPROVED":
        blockers.append("Full audiobook is not explicitly approved.")
    if qa_score is None:
        blockers.append("Human QA score is missing.")
    elif request.get("preview_allowed") is True and qa_score < 9.2:
        blockers.append("Public preview requires human QA score >= 9.2.")
    if request.get("full_audiobook_allowed") is True and (qa_score is None or qa_score < 9.5):
        blockers.append("Full audiobook requires human QA score >= 9.5.")
    if request.get("full_audiobook_allowed") is not True:
        blockers.append("Full audiobook release is disabled by default.")
    blockers.extend(claim_issues(public_disclosure_copy, human_recorded_proof=False))

    if manifest:
        serialized = json.dumps(manifest, ensure_ascii=False).lower()
        segments = manifest.get("segments") if isinstance(manifest.get("segments"), list) else []
        segment_audio_key_leak = any(
            any("audio_url" in str(key).lower() for key in segment)
            for segment in segments
            if isinstance(segment, dict)
        )
        if "http://" in serialized or "https://" in serialized or segment_audio_key_leak:
            blockers.append("Segment manifest must not contain public audio URLs.")
    else:
        warnings.append("Segment manifest not found; public release remains blocked.")

    if sitemap_has_audio_entries():
        blockers.append("Sitemap contains audiobook or audio entries.")
    blockers.extend(frontend_cta_issues())
    blockers.extend(public_projection_audio_issues())

    status = "BLOCKED_PUBLIC_AUDIO_RELEASE" if blockers else "PUBLIC_AUDIO_RELEASE_READY"
    return ReleaseGateResult(
        status=status,
        blockers=blockers,
        warnings=warnings,
        public_release_allowed=False if blockers else bool(request.get("public_release_allowed")),
        full_audiobook_allowed=False if blockers else bool(request.get("full_audiobook_allowed")),
        preview_allowed=False if blockers else bool(request.get("preview_allowed")),
    )


def report_markdown(result: ReleaseGateResult) -> str:
    lines = [
        "# Audiobook Release Gate Report",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"Status: `{result.status}`",
        "",
        "- Public audio release: blocked",
        "- Full audiobook release: blocked",
        "- Kshudhita Pashan remains pipeline-only",
        "- Dracula reading remains live and audio remains disabled",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {item}" for item in result.blockers) if result.blockers else lines.append("- None")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {item}" for item in result.warnings) if result.warnings else lines.append("- None")
    lines.extend(["", "## Acceptable Public Phrases After Separate Approval", ""])
    lines.extend(f"- {item}" for item in ACCEPTABLE_AFTER_APPROVAL)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expect",
        choices=["blocked", "ready"],
        default="blocked",
        help="Use blocked for today's expected state; ready must fail until public audio is truly approved.",
    )
    args = parser.parse_args(argv)
    context = load_context("kshudhita-pashan")
    manifest_path = OUTPUT_ROOT / "kshudhita-pashan" / "segment_manifest.json"
    manifest = read_json(manifest_path)
    result = evaluate_release_gate(context.request, context.profile, manifest=manifest)
    write_text(REPORT_PATH, report_markdown(result))
    write_json(OUTPUT_ROOT / "kshudhita-pashan" / "release_gate_report.json", result.as_dict())
    print(f"Audiobook release gate status: {result.status}")
    if args.expect == "blocked":
        return 0 if result.status == "BLOCKED_PUBLIC_AUDIO_RELEASE" else 1
    if args.expect == "ready":
        return 0 if result.status == "PUBLIC_AUDIO_RELEASE_READY" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
