#!/usr/bin/env python3
"""Plan a separately approved regenerated audiobook workflow.

This script is intentionally dry-run and approval-gated. It creates planning
artifacts only. It never generates audio, uploads audio, exposes public audio
URLs, or mutates production data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.audiobook_generation.provider_adapter import DryRunNarrationProvider, GenerationRequest

REQUEST_PATH = ROOT / "data" / "audiobook_governance" / "kshudhita-pashan.regeneration_request.json"
PROFILE_DIR = ROOT / "data" / "audiobook_voice_profiles"
SOURCE_METADATA_PATH = ROOT / "data" / "publication_candidates" / "kshudhita-pashan.source.json"
APPROVED_SOURCE_TEXT_PATH = ROOT / "data" / "audiobook_regeneration" / "kshudhita-pashan" / "approved_source_text.txt"
GOVERNANCE_SCHEMA_PATH = ROOT / "data" / "audiobook_governance" / "schema.json"
SEGMENT_SCHEMA_PATH = ROOT / "data" / "audiobook_regeneration" / "kshudhita-pashan" / "segment_manifest.schema.json"
OUTPUT_ROOT = ROOT / "output" / "audiobook_regeneration"

APPROVAL_KEYS = ("owner", "rights", "source_text", "voice_style")
PUBLIC_AUDIO_BLOCKERS = (
    "public_release_allowed",
    "full_audiobook_allowed",
    "preview_allowed",
)


@dataclass
class WorkflowContext:
    request: dict[str, Any]
    profile: dict[str, Any]
    source_metadata: dict[str, Any]
    book_slug: str


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_path(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


def validate_required(schema: dict[str, Any], payload: dict[str, Any], *, label: str) -> list[str]:
    issues: list[str] = []
    for key in schema.get("required", []):
        if key not in payload:
            issues.append(f"{label} missing required field: {key}")
    if "segments" in payload:
        segment_schema = (
            schema.get("properties", {})
            .get("segments", {})
            .get("items", {})
        )
        required = segment_schema.get("required", [])
        for index, segment in enumerate(payload.get("segments") or [], start=1):
            if not isinstance(segment, dict):
                issues.append(f"{label} segment {index} is not an object")
                continue
            for key in required:
                if key not in segment:
                    issues.append(f"{label} segment {index} missing required field: {key}")
    return issues


def validate_schema_file(schema_path: Path, payload_path: Path, *, label: str) -> list[str]:
    schema = read_json(schema_path)
    payload = read_json(payload_path)
    if not schema:
        return [f"{label} schema missing: {schema_path}"]
    if not payload:
        return [f"{label} payload missing: {payload_path}"]
    return validate_required(schema, payload, label=label)


def load_context(book_slug: str) -> WorkflowContext:
    request = read_json(REQUEST_PATH)
    if request.get("book_slug") != book_slug:
        raise ValueError(f"No regenerated narration governance request exists for {book_slug}.")
    schema_issues = validate_schema_file(GOVERNANCE_SCHEMA_PATH, REQUEST_PATH, label="governance_request")
    if schema_issues:
        raise ValueError("; ".join(schema_issues))
    profile_id = str(request.get("narrator_profile_id") or "").strip()
    profile = read_json(PROFILE_DIR / f"{profile_id.replace('-sample', '')}.sample.json")
    if not profile:
        profile = read_json(PROFILE_DIR / f"{profile_id}.json")
    source_metadata = read_json(SOURCE_METADATA_PATH)
    return WorkflowContext(request=request, profile=profile, source_metadata=source_metadata, book_slug=book_slug)


def approval_value(request: dict[str, Any], key: str) -> bool:
    approval = request.get("approvals", {}).get(key, {})
    return isinstance(approval, dict) and approval.get("approved") is True


def truthy_status(value: Any, approved_values: set[str]) -> bool:
    return str(value or "").strip().upper() in approved_values


def safety_issues(context: WorkflowContext, *, simulate_dry_run_approvals: bool = False) -> list[str]:
    request = context.request
    profile = context.profile
    source = context.source_metadata
    issues: list[str] = []

    if request.get("publication_status") != "PIPELINE_ONLY":
        issues.append("Kshudhita Pashan must remain PIPELINE_ONLY.")
    if request.get("regeneration_requested") is not True:
        issues.append("Regeneration request is not enabled for planning.")
    if request.get("human_review_required") is not True:
        issues.append("Human review must remain required.")
    for key in PUBLIC_AUDIO_BLOCKERS:
        if request.get(key) is True:
            issues.append(f"{key} must remain false until a separate public audio approval.")
    output_policy = request.get("output_policy") if isinstance(request.get("output_policy"), dict) else {}
    for key in ("audio_url_allowed", "public_player_allowed", "sitemap_audio_entry_allowed", "listen_now_cta_allowed"):
        if output_policy.get(key) is True:
            issues.append(f"Output policy {key} must remain false.")
    if not source:
        issues.append("Source metadata is missing.")
    else:
        for key in ("source_url", "source_name", "source_license", "source_hash", "content_hash", "provenance_hash"):
            if not str(source.get(key) or "").strip():
                issues.append(f"Source metadata missing {key}.")
        if source.get("full_source_text_committed") is not True or not APPROVED_SOURCE_TEXT_PATH.exists():
            issues.append("Approved full source text is unavailable; source-driven segments cannot be generated.")

    if not simulate_dry_run_approvals:
        for key in APPROVAL_KEYS:
            if not approval_value(request, key):
                issues.append(f"{key} approval is missing.")
    if not truthy_status(request.get("rights_status"), {"RIGHTS_APPROVED"}) and not simulate_dry_run_approvals:
        issues.append("Rights status is not approved.")
    if not truthy_status(request.get("source_text_status"), {"SOURCE_TEXT_APPROVED"}) and not simulate_dry_run_approvals:
        issues.append("Source text status is not approved.")

    provider = DryRunNarrationProvider()
    profile_issues = provider.validate_voice_profile(profile)
    if profile_issues and not simulate_dry_run_approvals:
        issues.extend(profile_issues)
    if str(profile.get("voice_source_type") or "").upper() == "REAL_PERSON_CLONE":
        issues.append("Real-person voice clone profile is not allowed in this workflow.")
    if request.get("voice_consent_status") == "CONSENT_BLOCKED":
        issues.append("Voice consent status blocks regeneration.")
    return issues


def source_paragraphs() -> list[str]:
    if not APPROVED_SOURCE_TEXT_PATH.exists():
        return []
    text = APPROVED_SOURCE_TEXT_PATH.read_text(encoding="utf-8")
    return [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]


def build_segments(context: WorkflowContext, *, ready: bool = False) -> list[dict[str, Any]]:
    status = "READY_FOR_GENERATION" if ready else "APPROVAL_REQUIRED"
    paragraphs = source_paragraphs()
    if not paragraphs:
        return []
    segments: list[dict[str, Any]] = []
    for index, start in enumerate(range(1, len(paragraphs) + 1, 4), start=1):
        end = min(start + 3, len(paragraphs))
        segments.append(
            {
                "segment_id": f"kshudhita-pashan-segment-{index:03d}",
                "chapter_id": "chapter-001",
                "text_ref": f"source:kshudhita-pashan:paragraphs:{start}-{end}",
                "start_paragraph": start,
                "end_paragraph": end,
                "language": "bn",
                "punctuation_profile": "bengali_gothic_punctuation_v1",
                "target_emotion": "source-derived Bengali Gothic narration",
                "intensity_level": "low-medium",
                "pause_profile": "source_punctuation_driven",
                "pronunciation_notes": "Preserve literary Bengali diction; verify Tagore-era phrasing in human listening review.",
                "dialogue_notes": "Gentle speaker separation only where quotation marks require it.",
                "qa_required": True,
                "regeneration_status": status,
            }
        )
    return segments


def qa_checklist() -> list[dict[str, Any]]:
    dimensions = [
        "Bengali pronunciation",
        "literary tone",
        "punctuation timing",
        "emotional subtlety",
        "gothic mood",
        "chapter consistency",
        "noise/clipping",
        "breath naturalness",
        "dialogue handling",
        "mobile playback",
        "headphone playback",
        "speaker playback",
        "no robotic artifacts",
        "no overacting",
        "no fake emotion",
        "no unauthorized voice likeness",
        "disclosure correctness",
    ]
    return [{"dimension": item, "required": True, "score": None, "status": "PENDING"} for item in dimensions]


def build_plan(context: WorkflowContext, *, simulate_dry_run_approvals: bool = False) -> dict[str, Any]:
    issues = safety_issues(context, simulate_dry_run_approvals=simulate_dry_run_approvals)
    status = "GENERATION_APPROVED_DRY_RUN_ONLY" if simulate_dry_run_approvals and not issues else "APPROVAL_REQUIRED"
    provider = DryRunNarrationProvider()
    dry_run_result = provider.generate_segment(
        GenerationRequest(
            book_slug=context.book_slug,
            segment_id="kshudhita-pashan-segment-001",
            text_ref="source:kshudhita-pashan:paragraphs:1-4",
            language="bn",
            narrator_profile_id=context.request.get("narrator_profile_id", ""),
            voice_source_type=context.request.get("voice_source_type", ""),
            consent_status=context.request.get("voice_consent_status", ""),
            dry_run=True,
            metadata={"estimated_characters": 0},
        )
    )
    return {
        "generated_at": utc_now(),
        "git_sha": git_sha(),
        "book_slug": context.book_slug,
        "title": context.request.get("title"),
        "language": context.request.get("language"),
        "workflow_status": status,
        "approval_status": context.request.get("approval_status"),
        "public_release_allowed": False,
        "full_audiobook_allowed": False,
        "preview_allowed": False,
        "audio_urls_included": False,
        "generation_performed": False,
        "upload_performed": False,
        "provider_call_performed": False,
        "approval_evidence": {
            "generated_at": utc_now(),
            "git_sha": git_sha(),
            "governance_request_checksum": sha256_path(REQUEST_PATH),
            "source_metadata_checksum": sha256_path(SOURCE_METADATA_PATH),
            "voice_profile_checksum": sha256_path(PROFILE_DIR / f"{str(context.request.get('narrator_profile_id') or '').replace('-sample', '')}.sample.json"),
            "release_gate_checksum": sha256_path(ROOT / "scripts" / "audiobook_release_gate.py"),
        },
        "provider_result": dry_run_result.__dict__,
        "issues": issues,
        "segments_planned": len(build_segments(context, ready=simulate_dry_run_approvals and not issues)),
        "source_text_status": "READY" if source_paragraphs() else "OPERATOR_REQUIRED",
        "qa_checklist": qa_checklist(),
        "next_required_approvals": [key for key in APPROVAL_KEYS if not approval_value(context.request, key)],
        "notes": [
            "This plan is internal only.",
            "No voice generation command exists in this workflow.",
            "Listen Now and public player surfaces remain blocked.",
        ],
    }


def write_plan_outputs(context: WorkflowContext, plan: dict[str, Any], output_dir: Path) -> None:
    write_json(output_dir / "regeneration_plan.json", plan)
    lines = [
        "# Kshudhita Pashan Regenerated Narration Plan",
        "",
        f"Status: `{plan['workflow_status']}`",
        "",
        "- Public release allowed: false",
        "- Full audiobook allowed: false",
        "- Preview allowed: false",
        "- Audio generated: false",
        "- Provider called: false",
        "- Audio URLs included: false",
        "",
        "## Issues",
        "",
    ]
    lines.extend(f"- {issue}" for issue in plan["issues"]) if plan["issues"] else lines.append("- None")
    lines.extend(["", "## Required Approvals", ""])
    lines.extend(f"- {approval}" for approval in plan["next_required_approvals"]) if plan["next_required_approvals"] else lines.append("- None")
    write_text(output_dir / "regeneration_plan.md", "\n".join(lines))


def write_gate_report(plan: dict[str, Any], output_dir: Path) -> None:
    status = "PASS_DRY_RUN_ONLY" if plan["workflow_status"] == "GENERATION_APPROVED_DRY_RUN_ONLY" else "BLOCKED_APPROVAL_REQUIRED"
    lines = [
        "# Audiobook Regeneration Approval Gate Report",
        "",
        f"Gate status: `{status}`",
        "",
        "- Owner approval required before real generation.",
        "- Rights approval required before real generation.",
        "- Source-text approval required before real generation.",
        "- Voice-style approval required before real generation.",
        "- Human QA approval required before public preview.",
        "- Product release approval required before any public audio CTA or URL.",
        "",
        "## Issues",
        "",
    ]
    lines.extend(f"- {issue}" for issue in plan["issues"]) if plan["issues"] else lines.append("- None")
    write_text(output_dir / "approval_gate_report.md", "\n".join(lines))


def write_segment_manifest(context: WorkflowContext, output_dir: Path, *, ready: bool = False) -> dict[str, Any]:
    manifest = {
        "generated_at": utc_now(),
        "git_sha": git_sha(),
        "book_slug": context.book_slug,
        "title": context.request.get("title"),
        "language": context.request.get("language"),
        "audio_urls_included": False,
        "public_release_allowed": False,
        "source_text_status": "READY" if source_paragraphs() else "OPERATOR_REQUIRED",
        "segments": build_segments(context, ready=ready),
    }
    write_json(output_dir / "segment_manifest.json", manifest)
    validation_issues = validate_schema_file(
        SEGMENT_SCHEMA_PATH,
        output_dir / "segment_manifest.json",
        label="segment_manifest",
    )
    write_json(
        output_dir / "segment_manifest_validation.json",
        {
            "status": "PASS" if not validation_issues else "FAIL",
            "issues": validation_issues,
        },
    )
    return manifest


def output_dir_for(book_slug: str) -> Path:
    return OUTPUT_ROOT / book_slug


def run_mode(book_slug: str, mode: str) -> int:
    context = load_context(book_slug)
    output_dir = output_dir_for(book_slug)

    if mode == "plan":
        plan = build_plan(context)
        write_plan_outputs(context, plan, output_dir)
        write_gate_report(plan, output_dir)
        return 0

    if mode == "precheck":
        plan = build_plan(context)
        write_plan_outputs(context, plan, output_dir)
        write_gate_report(plan, output_dir)
        return 0 if not plan["issues"] else 1

    if mode == "approve-dry-run":
        plan = build_plan(context, simulate_dry_run_approvals=True)
        write_plan_outputs(context, plan, output_dir)
        write_gate_report(plan, output_dir)
        return 0

    if mode == "generate-manifest":
        plan = build_plan(context)
        write_plan_outputs(context, plan, output_dir)
        write_gate_report(plan, output_dir)
        write_segment_manifest(context, output_dir, ready=False)
        return 0

    raise ValueError(f"Unsupported mode: {mode}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book-slug", default="kshudhita-pashan")
    parser.add_argument(
        "--mode",
        choices=["plan", "precheck", "approve-dry-run", "generate-manifest"],
        default="plan",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_mode(args.book_slug, args.mode)
    except Exception as exc:
        print(f"Audiobook regeneration workflow failed: {exc}", file=sys.stderr)
        return 1
    if result == 0:
        print(f"Audiobook regeneration workflow {args.mode} complete for {args.book_slug}.")
    else:
        print(f"Audiobook regeneration workflow {args.mode} blocked for {args.book_slug}.", file=sys.stderr)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
