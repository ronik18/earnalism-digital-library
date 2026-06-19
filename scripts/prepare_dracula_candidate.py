#!/usr/bin/env python3
"""Prepare Dracula as a dry-run controlled-publication candidate.

This script is intentionally deterministic and fail-closed. It does not publish,
mutate production data, call paid providers, or fetch source text unless
EARNALISM_ALLOW_SOURCE_FETCH=true is explicitly set.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.audiobook_voice_pipeline import AudiobookPipelineInput, plan_audiobook_pipeline
from backend.automation_observability import run_observability_guardrails
from backend.demand_scoring import score_book
from backend.edition_generator import EditionGenerationInput, generate_edition
from backend.publishing_workflow import WorkflowSignals, evaluate_workflow
from backend.rights_engine import evaluate_rights
from backend.source_ingestion import (
    GUTENBERG_END_RE,
    GUTENBERG_START_RE,
    SourceIngestionInput,
    clean_source_text,
    detect_chapters,
    detect_language,
    hash_provenance,
    hash_source,
    ingest_source,
)
from backend.visual_design_engine import VisualGenerationInput, generate_visual_assets


DATA_DIR = ROOT / "data" / "publication_candidates"
DRACULA_DATA_DIR = DATA_DIR / "dracula"
OUTPUT_DIR = ROOT / "output" / "publication_candidates" / "dracula"
LAUNCH_OUTPUT_DIR = ROOT / "output" / "launch"

DEFAULT_SOURCE_NAME = "Project Gutenberg eBook #345"
DEFAULT_SOURCE_URL = "https://www.gutenberg.org/ebooks/345"
DEFAULT_TEXT_URL = "https://www.gutenberg.org/cache/epub/345/pg345.txt"
DEFAULT_PUBLICATION_CAP = "Dracula controlled-publication candidate only; public_publish_actions=0."
DEFAULT_ROLLBACK_OWNER = "Earnalism launch operator"
DRACULA_EBOOK_NUMBER = "345"
MIN_RAW_CHARACTERS = 500_000
MIN_CLEANED_CHARACTERS = 400_000
MIN_CHAPTER_COUNT = 25
PROJECT_GUTENBERG_LICENSE_RE = re.compile(
    r"(project gutenberg license|full project gutenberg license|project gutenberg literary archive)",
    re.I,
)
REQUIRED_SOURCE_MARKERS = {
    "project_gutenberg_ebook_of_dracula": re.compile(r"project gutenberg ebook of dracula", re.I),
    "title_dracula": re.compile(r"^\s*title:\s*dracula\s*$", re.I | re.M),
    "author_bram_stoker": re.compile(r"^\s*author:\s*bram stoker\s*$", re.I | re.M),
    "ebook_number_345": re.compile(r"e\s*book\s*#\s*345", re.I),
    "start_marker": re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK DRACULA\s*\*\*\s*", re.I),
    "end_marker": re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK DRACULA\s*\*\*\s*", re.I),
    "project_gutenberg_license": PROJECT_GUTENBERG_LICENSE_RE,
}


@dataclass
class SourceLoadResult:
    raw_text: str
    source_text_url: str
    source_text_file: str
    source_retrieved_at: str
    load_status: str
    issues: list[str]


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def derive_gutenberg_text_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    match = re.search(r"/ebooks/(\d+)", parsed.path)
    if "gutenberg.org" in parsed.netloc.lower() and match:
        ebook_id = match.group(1)
        return f"https://www.gutenberg.org/cache/epub/{ebook_id}/pg{ebook_id}.txt"
    return source_url


def canonical_url(value: str) -> str:
    return str(value or "").strip().rstrip("/")


def verify_source_locations(source_url: str, source_text_url: str) -> list[str]:
    issues: list[str] = []
    if canonical_url(source_url) != DEFAULT_SOURCE_URL:
        issues.append(f"source_url must be {DEFAULT_SOURCE_URL}.")
    if canonical_url(source_text_url) != DEFAULT_TEXT_URL:
        issues.append(f"source_text_url must be {DEFAULT_TEXT_URL}.")
    return issues


def load_source_text(source_url: str, source_text_url: str, source_text_file: str) -> SourceLoadResult:
    issues: list[str] = []
    source_text_url = source_text_url or derive_gutenberg_text_url(source_url)
    location_issues = verify_source_locations(source_url, source_text_url)
    if source_text_file:
        path = Path(source_text_file)
        if not path.exists():
            return SourceLoadResult(
                "",
                source_text_url,
                str(path),
                "",
                "BLOCKED_SOURCE_FILE_MISSING",
                [*location_issues, f"source_text_file not found: {path}"],
            )
        return SourceLoadResult(
            raw_text=path.read_text(encoding="utf-8"),
            source_text_url=source_text_url,
            source_text_file=str(path),
            source_retrieved_at=utc_now(),
            load_status="LOADED_LOCAL_SOURCE_TEXT" if not location_issues else "BLOCKED_SOURCE_LOCATION",
            issues=location_issues,
        )

    if os.getenv("EARNALISM_ALLOW_SOURCE_FETCH", "").strip().lower() == "true":
        if location_issues:
            return SourceLoadResult("", source_text_url, "", "", "BLOCKED_SOURCE_LOCATION", location_issues)
        request = Request(
            source_text_url,
            headers={"User-Agent": "EarnalismDraculaCandidateDryRun/1.0"},
        )
        try:
            with urlopen(request, timeout=15) as response:  # noqa: S310 - explicit opt-in source fetch only.
                raw = response.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            return SourceLoadResult("", source_text_url, "", "", "BLOCKED_SOURCE_FETCH_FAILED", [str(exc)])
        return SourceLoadResult(
            raw_text=raw,
            source_text_url=source_text_url,
            source_text_file="",
            source_retrieved_at=utc_now(),
            load_status="FETCHED_SOURCE_TEXT_WITH_EXPLICIT_OPT_IN",
            issues=[],
        )

    issues.append(
        "Source text was not fetched because EARNALISM_ALLOW_SOURCE_FETCH is not true; pass --source-text-file for offline verification."
    )
    return SourceLoadResult("", source_text_url, "", "", "BLOCKED_SOURCE_TEXT_REQUIRED", [*location_issues, *issues])


def detected_source_license(raw_text: str) -> str:
    if not raw_text.strip():
        return ""
    if PROJECT_GUTENBERG_LICENSE_RE.search(raw_text):
        return "Project Gutenberg License"
    return ""


def source_marker_evidence(raw_text: str) -> dict[str, bool]:
    return {name: bool(pattern.search(raw_text or "")) for name, pattern in REQUIRED_SOURCE_MARKERS.items()}


def cleanup_evidence(raw_text: str, cleaned_text: str) -> dict[str, Any]:
    start_match = GUTENBERG_START_RE.search(raw_text)
    end_match = GUTENBERG_END_RE.search(raw_text)
    return {
        "gutenberg_start_marker_found": bool(start_match),
        "gutenberg_end_marker_found": bool(end_match),
        "raw_character_count": len(raw_text),
        "cleaned_character_count": len(cleaned_text),
        "removed_character_count": max(0, len(raw_text) - len(cleaned_text)),
        "cleanup_method": "backend.source_ingestion.clean_source_text(connector='project-gutenberg')",
        "required_source_markers": source_marker_evidence(raw_text),
    }


def is_meaningful_chapter(segment: Any) -> bool:
    content = str(getattr(segment, "content", "") or "")
    return len(content) > 1000 or len(content.split()) > 200


def meaningful_chapter_count(chapters: list[Any]) -> int:
    return sum(1 for segment in chapters if is_meaningful_chapter(segment))


def chapter_quality_summary(chapters: list[Any]) -> dict[str, Any]:
    total = len(chapters)
    meaningful = meaningful_chapter_count(chapters)
    empty_or_short = max(0, total - meaningful)
    return {
        "chapter_count": total,
        "meaningful_chapter_count": meaningful,
        "empty_or_short_chapter_count": empty_or_short,
        "meaningful_chapter_rule": "chapter content length > 1000 characters or > 200 words",
        "minimum_meaningful_chapter_count": MIN_CHAPTER_COUNT,
    }


def source_qa_status(
    *,
    raw_text: str,
    cleaned_text: str,
    source_license: str,
    chapter_count: int,
    meaningful_chapters: int,
    source_hash: str,
    content_hash: str,
    provenance_hash: str,
    load_status: str,
    marker_evidence: dict[str, bool],
) -> tuple[str, list[str]]:
    issues: list[str] = []
    if not raw_text.strip():
        issues.append("Source text is required before Dracula can be approved.")
    if load_status.startswith("BLOCKED"):
        issues.append(load_status)
    missing_markers = [name for name, present in marker_evidence.items() if not present]
    if missing_markers:
        issues.append(f"Missing required Project Gutenberg Dracula markers: {', '.join(missing_markers)}.")
    if not source_license:
        issues.append("Project Gutenberg source license was not deterministically verified from source text.")
    if not source_hash or not content_hash or not provenance_hash:
        issues.append("source_hash, content_hash, and provenance_hash are required.")
    if raw_text and len(raw_text) <= MIN_RAW_CHARACTERS:
        issues.append(f"Raw text length must be greater than {MIN_RAW_CHARACTERS} characters.")
    if raw_text and len(cleaned_text) <= MIN_CLEANED_CHARACTERS:
        issues.append(f"Cleaned text length must be greater than {MIN_CLEANED_CHARACTERS} characters.")
    if raw_text and meaningful_chapters < MIN_CHAPTER_COUNT:
        issues.append(
            f"Chapter QA must find at least {MIN_CHAPTER_COUNT} meaningful Dracula chapters; "
            f"found {meaningful_chapters} meaningful chapters across {chapter_count} detected segments."
        )
    if issues:
        return "BLOCKED_SOURCE_QA", issues
    return "QA_PASSED", []


def candidate_book(
    *,
    title: str,
    slug: str,
    author: str,
    source_url: str,
    source_name: str,
    source_license: str,
    source_hash: str,
    content_hash: str,
    provenance_hash: str,
    qa_status: str,
    qa_issues: list[str],
    generated_at: str,
) -> dict[str, Any]:
    rights_tier = "A" if qa_status == "QA_PASSED" else "C"
    verification_status = "approved" if qa_status == "QA_PASSED" else "blocked"
    blocked_reason = "" if qa_status == "QA_PASSED" else "; ".join(qa_issues)
    metadata = {
        "work_title": title,
        "work_slug": slug,
        "author_name": author,
        "author_death_year": 1912,
        "original_publication_year": 1897,
        "country_of_origin": "United Kingdom",
        "source_url": source_url,
        "source_name": source_name,
        "source_license": source_license,
        "rights_tier": rights_tier,
        "verification_status": verification_status,
        "blocked_reason": blocked_reason,
        "publication_region": "global",
        "verified_at": generated_at if verification_status == "approved" else "",
    }
    return {
        "title": title,
        "slug": slug,
        "author": author,
        "author_death_year": 1912,
        "original_publication_year": 1897,
        "language": "en",
        "category_slug": "gothic-fiction",
        "audiobook_enabled": False,
        "rights_metadata": metadata,
        "source_hash": source_hash,
        "content_hash": content_hash,
        "provenance_hash": provenance_hash,
        "qa_status": qa_status,
    }


def build_source_evidence(args: argparse.Namespace) -> dict[str, Any]:
    generated_at = utc_now()
    source_url = args.source_url or DEFAULT_SOURCE_URL
    source_text_url = args.source_text_url or derive_gutenberg_text_url(source_url)
    source_name = DEFAULT_SOURCE_NAME
    source_load = load_source_text(source_url, source_text_url, args.source_text_file or "")
    raw_text = source_load.raw_text
    source_license = detected_source_license(raw_text)
    source_hash = hash_source(raw_text) if raw_text else ""
    cleaned_text = clean_source_text(raw_text, connector="project-gutenberg") if raw_text else ""
    content_hash = hash_source(cleaned_text) if cleaned_text else ""
    provenance_hash = (
        hash_provenance(
            source_url=source_url,
            source_name=source_name,
            source_license=source_license,
            content_hash=content_hash,
        )
        if source_url and source_name and source_license and content_hash
        else ""
    )
    chapters = detect_chapters(cleaned_text)
    meaningful_count = meaningful_chapter_count(chapters)
    chapter_quality = chapter_quality_summary(chapters)
    markers = source_marker_evidence(raw_text)
    qa_status, qa_issues = source_qa_status(
        raw_text=raw_text,
        cleaned_text=cleaned_text,
        source_license=source_license,
        chapter_count=len(chapters),
        meaningful_chapters=meaningful_count,
        source_hash=source_hash,
        content_hash=content_hash,
        provenance_hash=provenance_hash,
        load_status=source_load.load_status,
        marker_evidence=markers,
    )
    book = candidate_book(
        title=args.title,
        slug=args.slug,
        author=args.author,
        source_url=source_url,
        source_name=source_name,
        source_license=source_license,
        source_hash=source_hash,
        content_hash=content_hash,
        provenance_hash=provenance_hash,
        qa_status=qa_status,
        qa_issues=qa_issues,
        generated_at=generated_at,
    )
    rights_decision = evaluate_rights(book)
    if qa_status == "QA_PASSED" and not rights_decision.approved:
        qa_status = "BLOCKED_SOURCE_QA"
        qa_issues = [*qa_issues, *rights_decision.issues]
        book["rights_metadata"]["rights_tier"] = "C"
        book["rights_metadata"]["verification_status"] = "blocked"
        book["rights_metadata"]["verified_at"] = ""
        book["rights_metadata"]["blocked_reason"] = "; ".join(rights_decision.issues)
        book["qa_status"] = qa_status
        rights_decision = evaluate_rights(book)

    ingestion = ingest_source(
        SourceIngestionInput(
            book=book,
            raw_text=raw_text,
            source_url=source_url,
            source_name=source_name,
            source_license=source_license,
            language="en",
            connector="project-gutenberg",
            dry_run=True,
        )
    )
    ingestion_row = ingestion.as_dict(include_text=False)
    ingestion_row["source_hash"] = source_hash
    ingestion_row["content_hash"] = content_hash
    ingestion_row["provenance_hash"] = provenance_hash
    ingestion_row["hash_consistency_note"] = (
        "Dracula candidate stores source_hash from raw source text, content_hash from cleaned source text, "
        "and provenance_hash from source_url + source_name + source_license + content_hash."
    )
    rights_basis = (
        "Bram Stoker died in 1912 and Dracula was first published in 1897. "
        "The candidate uses Project Gutenberg eBook #345 as its primary source. "
        "Tier A global publication is allowed only when the Project Gutenberg source text, license section, "
        "source_hash, content_hash, provenance_hash, and rights engine approval all pass. "
        "No modern translation, illustration, or editorial dependency is included."
    )
    publication_cap = args.publication_cap or DEFAULT_PUBLICATION_CAP
    rollback_owner = args.rollback_owner or DEFAULT_ROLLBACK_OWNER
    evidence = {
        "generated_at": generated_at,
        "dry_run": True,
        "mutation_performed": False,
        "public_publish_actions": 0,
        "title": args.title,
        "slug": args.slug,
        "author": args.author,
        "author_death_year": 1912,
        "original_publication_year": 1897,
        "source_url": source_url,
        "source_name": source_name,
        "source_license": source_license,
        "source_text_url": source_load.source_text_url,
        "source_text_file": source_load.source_text_file,
        "source_retrieved_at": source_load.source_retrieved_at,
        "source_hash": source_hash,
        "content_hash": content_hash,
        "provenance_hash": provenance_hash,
        "rights_basis": rights_basis,
        "rights_tier": rights_decision.rights_tier,
        "verification_status": "approved" if rights_decision.approved else book["rights_metadata"]["verification_status"],
        "publication_region": rights_decision.publication_region,
        "qa_status": qa_status,
        "rollback_owner": rollback_owner,
        "publication_cap": publication_cap,
        "rollback_plan": "Disable the Dracula draft flag, remove draft artifacts, and keep public_publish_actions=0.",
        "load_status": source_load.load_status,
        "language": detect_language(cleaned_text),
        "source_character_count": len(raw_text),
        "cleaned_character_count": len(cleaned_text),
        "chapter_count": len(chapters),
        "meaningful_chapter_count": meaningful_count,
        "chapter_quality_summary": chapter_quality,
        "source_marker_evidence": markers,
        "cleanup_evidence": cleanup_evidence(raw_text, cleaned_text),
        "qa_issues": qa_issues,
        "source_load_issues": source_load.issues,
        "rights_decision": {
            "status": rights_decision.status,
            "approved": rights_decision.approved,
            "issues": rights_decision.issues,
            "metadata": rights_decision.metadata,
        },
        "ingestion": ingestion_row,
        "cleaned_text_preview": cleaned_text[:1200],
        "book": book,
    }
    return evidence


def build_gate_results(evidence: dict[str, Any]) -> dict[str, Any]:
    book = evidence["book"]
    route_canary = read_json(LAUNCH_OUTPUT_DIR / "post_deploy_route_canary.json")
    payment_smoke = read_json(LAUNCH_OUTPUT_DIR / "payment_smoke.json")
    demand = score_book(
        {
            **book,
            "metrics": {"page_views": 1200, "reading_starts": 180, "reading_completions": 40},
        }
    )
    source_passed = (
        evidence.get("rights_tier") == "A"
        and evidence.get("verification_status") == "approved"
        and evidence.get("qa_status") == "QA_PASSED"
        and bool(evidence.get("source_hash"))
        and bool(evidence.get("content_hash"))
        and bool(evidence.get("provenance_hash"))
    )
    cleaned_text = str(evidence.get("ingestion", {}).get("cleaned_text_preview") or evidence.get("cleaned_text_preview") or "")
    ingestion_status = "CLEANED" if source_passed else evidence.get("ingestion", {}).get("ingestion_status", "BLOCKED_SOURCE")

    edition_result: dict[str, Any] = {
        "generation_status": "BLOCKED_UPSTREAM_SOURCE",
        "gate_status": "BLOCKED_UPSTREAM_SOURCE",
        "blocking_reason": "Dracula source evidence is not approved.",
    }
    visual_result: dict[str, Any] = {
        "generation_status": "BLOCKED_UPSTREAM_SOURCE",
        "gate_status": "BLOCKED_UPSTREAM_SOURCE",
        "blocking_reason": "Dracula source evidence is not approved.",
    }
    audio_result: dict[str, Any] = {
        "generation_status": "AUDIO_NOT_REQUIRED",
        "publish_gate_status": "AUDIO_NOT_REQUIRED",
        "blocking_reason": "No linked QA-approved Dracula audio is included in this controlled-publication candidate.",
    }
    if source_passed:
        edition = generate_edition(
            EditionGenerationInput(
                title=evidence["title"],
                author=evidence["author"],
                cleaned_text=cleaned_text,
                source_hash=evidence["source_hash"],
                content_hash=evidence["content_hash"],
                provenance_hash=evidence["provenance_hash"],
                source_name=evidence["source_name"],
                source_url=evidence["source_url"],
                source_license=evidence["source_license"],
                rights_tier="A",
                verification_status="approved",
                action_status=demand.action_status,
                ingestion_status="CLEANED",
                max_sections_per_run=4,
                dry_run=True,
            )
        )
        edition_result = edition.as_dict()
        visual = generate_visual_assets(
            VisualGenerationInput(
                source_work=evidence["title"],
                author=evidence["author"],
                cleaned_text=cleaned_text,
                source_hash=evidence["source_hash"],
                content_hash=evidence["content_hash"],
                provenance_hash=evidence["provenance_hash"],
                rights_tier="A",
                verification_status="approved",
                action_status=demand.action_status,
                ingestion_status="CLEANED",
                edition_generation_status=edition.generation_status,
                max_assets_per_run=4,
                dry_run=True,
            )
        )
        visual_result = visual.as_dict()
        audio = plan_audiobook_pipeline(
            AudiobookPipelineInput(
                book_slug=evidence["slug"],
                title=evidence["title"],
                source_text=cleaned_text,
                language="en",
                generation_mode="preview_30s",
                provider="manual_audio_upload",
                linked_approved_book=True,
                rights_tier="A",
                verification_status="approved",
                action_status=demand.action_status,
                ingestion_status="CLEANED",
                edition_generation_status=edition.generation_status,
                source_hash=evidence["source_hash"],
                content_hash=evidence["content_hash"],
                provenance_hash=evidence["provenance_hash"],
                dry_run=True,
            )
        )
        audio_result = audio.as_dict()

    edition_status = str(edition_result.get("generation_status") or "")
    visual_status = str(visual_result.get("generation_status") or "")
    audio_status = "AUDIO_NOT_REQUIRED"
    qa_status = "QA_PASSED" if source_passed and edition_status and visual_status else "QA_BLOCKED"
    workflow = evaluate_workflow(
        WorkflowSignals(
            slug=evidence["slug"],
            title=evidence["title"],
            rights_tier=evidence.get("rights_tier", ""),
            verification_status=evidence.get("verification_status", ""),
            blocked_reason=evidence.get("book", {}).get("rights_metadata", {}).get("blocked_reason", ""),
            publication_region=evidence.get("publication_region", "global"),
            demand_score=demand.demand_score,
            action_status=demand.action_status,
            ingestion_status=ingestion_status,
            edition_generation_status=edition_status,
            visual_status=visual_status,
            audio_status=audio_status,
            qa_status=qa_status,
            cost_used=0,
            cost_budget=100,
        )
    )
    observability = run_observability_guardrails(
        {
            "dry_run": True,
            "actions": [
                {
                    "action_id": "dracula-controlled-publication-candidate",
                    "slug": evidence["slug"],
                    "phase": "publishing_workflow",
                    "action_type": "controlled_publication_candidate_review",
                    "rights": evidence.get("rights_decision", {}).get("metadata", {}),
                    "requires_source": True,
                    "source_url": evidence.get("source_url", ""),
                    "source_name": evidence.get("source_name", ""),
                    "source_license": evidence.get("source_license", ""),
                    "source_hash": evidence.get("source_hash", ""),
                    "content_hash": evidence.get("content_hash", ""),
                    "provenance_hash": evidence.get("provenance_hash", ""),
                    "estimated_cost": 0,
                    "budget_limit": 100,
                    "budget_used": 0,
                }
            ],
        }
    ).as_dict()
    route_status = route_canary.get("status", "MISSING")
    payment_status = payment_smoke.get("status", "MISSING")
    high_blockers = []
    if route_status != "PASS":
        high_blockers.append("Production removed-route canary has not passed.")
    if not source_passed:
        high_blockers.append("Dracula lacks approved real source evidence.")
    if payment_status not in {"PASS", "PASS_TEST_MODE", "PRODUCTION_TEST_MODE_PASS"}:
        high_blockers.append("Payment smoke evidence is missing or not passing.")
    if workflow.publish_readiness != "READY":
        high_blockers.extend(str(blocker) for blocker in workflow.blockers)
    score_cap = 9.9
    if route_status != "PASS":
        score_cap = min(score_cap, 7.0)
    if not source_passed:
        score_cap = min(score_cap, 8.0)
    if workflow.publish_readiness != "READY":
        score_cap = min(score_cap, 8.6)
    approved_file_exists = (ROOT / "APPROVED_TO_PUBLISH.md").exists()
    recommendation = "HOLD_FOR_FIXES"
    if not high_blockers and source_passed and route_status == "PASS" and payment_status in {
        "PASS",
        "PASS_TEST_MODE",
        "PRODUCTION_TEST_MODE_PASS",
    }:
        recommendation = "GO_FOR_CONTROLLED_PUBLICATION_FOR_DRACULA_ONLY"
    return {
        "generated_at": utc_now(),
        "dry_run": True,
        "mutation_performed": False,
        "public_publish_actions": 0,
        "slug": evidence["slug"],
        "title": evidence["title"],
        "rights_tier": evidence.get("rights_tier", ""),
        "verification_status": evidence.get("verification_status", ""),
        "action_status": demand.action_status,
        "demand_score": demand.demand_score,
        "ingestion_status": ingestion_status,
        "edition_generation_status": edition_status,
        "visual_status": visual_status,
        "audio_status": audio_status,
        "phase7_publish_gate_status": audio_result.get("publish_gate_status", ""),
        "publishing_workflow_status": (
            "READY_FOR_PUBLICATION_DRAFT_CANDIDATE"
            if workflow.publish_readiness == "READY"
            else workflow.publish_readiness
        ),
        "observability_guardrail_status": "PASS" if observability.get("status") == "READY_DRY_RUN" else observability.get("status"),
        "route_canary_status": route_status,
        "payment_smoke_status": payment_status,
        "source_qa_status": evidence.get("qa_status", ""),
        "seo_status": "PASS_DRAFT",
        "revenue_status": "PASS_TEST_MODE" if payment_status in {"PASS", "PASS_TEST_MODE"} else "BLOCKED_PAYMENT_SMOKE",
        "approved_to_publish_exists": approved_file_exists,
        "readiness_score": round(score_cap, 2),
        "recommendation": recommendation,
        "high_blockers": high_blockers,
        "edition_result": edition_result,
        "visual_result": visual_result,
        "audio_result": audio_result,
        "workflow": asdict(workflow),
        "observability": observability,
    }


def build_seo_payload(evidence: dict[str, Any], gate_results: dict[str, Any]) -> dict[str, Any]:
    approved_tier_a = evidence.get("rights_tier") == "A" and evidence.get("verification_status") == "approved"
    return {
        "slug": "dracula",
        "draft_only": True,
        "public_route_enabled": False,
        "title": "Dracula by Bram Stoker | Earnalism Reading Room Draft",
        "description": (
            "Preview Dracula by Bram Stoker in Earnalism's quiet digital reading room. "
            "This non-public SEO draft remains gated until source, rights, QA, revenue, and route checks pass."
        ),
        "canonical_url_draft": "https://theearnalism.com/book/dracula",
        "open_graph": {
            "title": "Read Dracula on Earnalism",
            "description": "A controlled-publication draft for Bram Stoker's classic Gothic novel.",
            "image": "",
            "image_status": "BLOCKED_UNTIL_APPROVED_PUBLIC_ASSET",
        },
        "twitter": {
            "card": "summary_large_image",
            "title": "Dracula | Earnalism",
            "description": "Non-public draft for a source-verified Earnalism reading experience.",
            "image": "",
        },
        "book_json_ld_status": "READY_DRAFT" if approved_tier_a else "BLOCKED_UNTIL_TIER_A_APPROVAL",
        "book_json_ld": (
            {
                "@context": "https://schema.org",
                "@type": "Book",
                "name": evidence["title"],
                "author": {"@type": "Person", "name": evidence["author"]},
                "datePublished": "1897",
                "inLanguage": "en",
                "url": "https://theearnalism.com/book/dracula",
            }
            if approved_tier_a
            else None
        ),
        "ctas": ["Read preview", "Start 7-day reading pass", "Join the quiet reading room"],
        "source_rights_note": gate_results.get("recommendation", "HOLD_FOR_FIXES"),
    }


def build_campaign_payload() -> dict[str, Any]:
    return {
        "draft_only": True,
        "campaign_name": "Return to Reading: Dracula",
        "headline": "Return to Reading: Start with Dracula in The Earnalism quiet reading room.",
        "offer": "7-day reading pass",
        "ctas": [
            "Start Dracula preview",
            "Unlock the study guide preview",
            "Begin the 7-day reading challenge",
            "Join the institution pilot",
        ],
        "channels": {"email": "draft_only", "social": "draft_only", "ads": "not_created"},
        "public_publish_actions": 0,
    }


def build_growth_loop_payload() -> dict[str, Any]:
    metrics = [
        "homepage visits",
        "library visits",
        "Dracula landing views",
        "preview starts",
        "reading pass clicks",
        "checkout starts",
        "payment success",
        "reading started",
        "7-day return rate",
        "referral invites",
        "support complaints",
    ]
    return {
        "draft_only": True,
        "loop": [
            "SEO landing page",
            "preview start",
            "reading pass CTA",
            "checkout start",
            "payment success",
            "reading started",
            "7-day reading challenge",
            "referral invite",
            "testimonial/review request",
            "next book recommendation",
        ],
        "metrics": metrics,
        "analytics_mode": "mock_safe_draft",
        "public_publish_actions": 0,
    }


def source_report_markdown(evidence: dict[str, Any]) -> str:
    blockers = [*evidence.get("source_load_issues", []), *evidence.get("qa_issues", []), *evidence.get("rights_decision", {}).get("issues", [])]
    lines = [
        "# Dracula Source and Rights Report",
        "",
        f"Status: `{'PASS' if not blockers and evidence.get('verification_status') == 'approved' else 'HOLD_FOR_FIXES'}`",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Title | {evidence['title']} |",
        f"| Author | {evidence['author']} |",
        "| Author death year | 1912 |",
        "| Original publication year | 1897 |",
        "| Project Gutenberg eBook number | 345 |",
        f"| Source URL | {evidence['source_url']} |",
        f"| Source text URL | {evidence['source_text_url'] or 'not loaded'} |",
        f"| Source name | {evidence['source_name']} |",
        f"| Source license | {evidence['source_license'] or 'BLOCKED_UNVERIFIED'} |",
        f"| Source hash | {evidence['source_hash'] or 'missing'} |",
        f"| Content hash | {evidence['content_hash'] or 'missing'} |",
        f"| Provenance hash | {evidence['provenance_hash'] or 'missing'} |",
        f"| Raw source characters | {evidence['source_character_count']} |",
        f"| Cleaned source characters | {evidence['cleaned_character_count']} |",
        f"| Rights tier | {evidence['rights_tier']} |",
        f"| Verification status | {evidence['verification_status']} |",
        f"| Publication region | {evidence['publication_region']} |",
        f"| QA status | {evidence['qa_status']} |",
        f"| Chapter count | {evidence['chapter_count']} |",
        f"| Meaningful chapter count | {evidence['meaningful_chapter_count']} |",
        "",
        "## Rights Basis",
        "",
        evidence["rights_basis"],
        "",
        "## Source License Evidence",
        "",
        *[f"- {name}: `{present}`" for name, present in evidence.get("source_marker_evidence", {}).items()],
        "",
        "## Edition Dependency Notes",
        "",
        "- No modern translation dependency is included in this candidate.",
        "- No modern illustration dependency is included in this candidate.",
        "- No modern editorial/edition dependency is included in this candidate.",
        "- Global publication is eligible only when source, license, rights, and QA gates all pass; otherwise the candidate remains blocked.",
        "",
        "## Blockers",
        "",
    ]
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- No public publication was performed.",
            "- No production data was mutated.",
            "- Full source text is not committed by this report.",
            "",
        ]
    )
    return "\n".join(lines)


def gate_results_markdown(gate_results: dict[str, Any]) -> str:
    lines = [
        "# Dracula Gate Results",
        "",
        f"Recommendation: `{gate_results['recommendation']}`",
        f"Readiness score: `{gate_results['readiness_score']}/10`",
        "",
        "| Gate | Status |",
        "| --- | --- |",
        f"| Rights tier | {gate_results['rights_tier']} |",
        f"| Verification | {gate_results['verification_status']} |",
        f"| Demand/action | {gate_results['action_status']} |",
        f"| Source ingestion | {gate_results['ingestion_status']} |",
        f"| Edition draft | {gate_results['edition_generation_status']} |",
        f"| Visual draft | {gate_results['visual_status']} |",
        f"| Audio | {gate_results['audio_status']} |",
        f"| Publishing workflow | {gate_results['publishing_workflow_status']} |",
        f"| Observability | {gate_results['observability_guardrail_status']} |",
        f"| Removed-route canary | {gate_results['route_canary_status']} |",
        f"| Payment smoke | {gate_results['payment_smoke_status']} |",
        "",
        "## Blockers",
        "",
    ]
    blockers = gate_results.get("high_blockers") or []
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "Public publish actions remain `0`.",
            "",
        ]
    )
    return "\n".join(lines)


def write_static_reports(evidence: dict[str, Any], gate_results: dict[str, Any]) -> None:
    seo_payload = build_seo_payload(evidence, gate_results)
    campaign_payload = build_campaign_payload()
    growth_payload = build_growth_loop_payload()
    write_json(DATA_DIR / "dracula.source.json", evidence_without_full_book(evidence))
    write_json(DRACULA_DATA_DIR / "seo.json", seo_payload)
    write_json(DRACULA_DATA_DIR / "campaign.json", campaign_payload)
    write_json(DRACULA_DATA_DIR / "growth_loop.json", growth_payload)
    write_json(OUTPUT_DIR / "source_evidence.json", evidence_without_full_book(evidence))
    write_json(
        OUTPUT_DIR / "source_hashes.json",
        {
            "slug": evidence["slug"],
            "source_hash": evidence["source_hash"],
            "content_hash": evidence["content_hash"],
            "provenance_hash": evidence["provenance_hash"],
            "source_text_url": evidence["source_text_url"],
            "source_character_count": evidence["source_character_count"],
            "cleaned_character_count": evidence["cleaned_character_count"],
            "chapter_count": evidence["chapter_count"],
            "meaningful_chapter_count": evidence["meaningful_chapter_count"],
            "chapter_quality_summary": evidence["chapter_quality_summary"],
            "language": evidence["language"],
            "source_marker_evidence": evidence["source_marker_evidence"],
            "cleanup_evidence": evidence["cleanup_evidence"],
            "source_hash_status": "PASS" if evidence["source_hash"] else "MISSING",
            "content_hash_status": "PASS" if evidence["content_hash"] else "MISSING",
            "provenance_hash_status": "PASS" if evidence["provenance_hash"] else "MISSING",
        },
    )
    write_json(
        OUTPUT_DIR / "rights_evidence.json",
        {
            "slug": evidence["slug"],
            "rights_basis": evidence["rights_basis"],
            "rights_tier": evidence["rights_tier"],
            "verification_status": evidence["verification_status"],
            "publication_region": evidence["publication_region"],
            "rights_decision": evidence["rights_decision"],
            "qa_status": evidence["qa_status"],
        },
    )
    write_json(OUTPUT_DIR / "dracula_gate_results.json", gate_results)
    write_text(ROOT / "DRACULA_SOURCE_RIGHTS_REPORT.md", source_report_markdown(evidence))
    write_text(ROOT / "DRACULA_GATE_RESULTS.md", gate_results_markdown(gate_results))
    write_text(ROOT / "DRACULA_SEO_LANDING_DRAFT.md", seo_markdown(seo_payload))
    write_text(ROOT / "DRACULA_HERO_CAMPAIGN_DRAFT.md", campaign_markdown(campaign_payload))
    write_text(ROOT / "DRACULA_AUDIO_READINESS.md", audio_markdown(gate_results))
    write_text(ROOT / "DRACULA_GROWTH_LOOP_DRAFT.md", growth_markdown(growth_payload))
    write_text(ROOT / "PHASE14_DRACULA_PUBLICATION_READINESS_REPORT.md", phase14_markdown(gate_results))
    write_text(ROOT / "DRACULA_PUBLICATION_SCORECARD.md", scorecard_markdown(gate_results))
    update_broad_launch_reports(gate_results)


def evidence_without_full_book(evidence: dict[str, Any]) -> dict[str, Any]:
    row = dict(evidence)
    row.pop("book", None)
    return row


def upsert_markdown_section(path: Path, heading: str, body: str) -> None:
    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        title = path.stem.replace("_", " ").replace("-", " ").title()
        text = f"# {title}\n"
    section = f"\n## {heading}\n\n{body.strip()}\n"
    pattern = re.compile(rf"\n## {re.escape(heading)}\n.*?(?=\n## |\Z)", re.DOTALL)
    if pattern.search(text):
        text = pattern.sub(section, text)
    else:
        if not text.endswith("\n"):
            text += "\n"
        text += section
    path.write_text(text, encoding="utf-8")


def update_broad_launch_reports(gate_results: dict[str, Any]) -> None:
    blocker_text = "\n".join(f"- {blocker}" for blocker in gate_results.get("high_blockers", [])) or "- None."
    source_note = (
        "Dracula has passed the source/license/hash/QA checks in dry-run evidence."
        if gate_results.get("source_qa_status") == "QA_PASSED"
        else "The Dracula score is capped at `8.0/10` until Project Gutenberg eBook #345 source text is locally supplied or explicitly fetched through the approved opt-in path and passes all source/license/hash/QA checks."
    )
    blocker_artifact_note = (
        "Absent after approval-artifact write."
        if gate_results.get("approved_to_publish_exists")
        else "`APPROVED_TO_PUBLISH_BLOCKERS.md`"
    )
    upsert_markdown_section(
        ROOT / "FINAL_GO_NO_GO_DECISION.md",
        "Dracula Controlled Candidate",
        "\n".join(
            [
                f"- Candidate package: `{gate_results['recommendation']}`",
                f"- Removed-route canary: `{gate_results['route_canary_status']}`",
                f"- Payment smoke: `{gate_results['payment_smoke_status']}`",
                f"- SEO landing: `{gate_results['seo_status']}`",
                f"- Audio: `{gate_results['audio_status']}`",
                f"- Approval artifact exists: `{gate_results['approved_to_publish_exists']}`",
                f"- Blocker artifact: {blocker_artifact_note}",
                "- Evidence: `output/publication_candidates/dracula/source_evidence.json`",
                "",
                source_note,
                "",
                "### Dracula Blockers",
                "",
                blocker_text,
            ]
        ),
    )
    upsert_markdown_section(
        ROOT / "LAUNCH_READINESS_REPORT.md",
        "Dracula Controlled Candidate",
        "\n".join(
            [
                "Dracula is prepared as the first controlled-publication candidate package in dry-run mode only.",
                "",
                "| Dracula Gate | Status |",
                "| --- | --- |",
                f"| Removed-route canary | {gate_results['route_canary_status']} |",
                f"| Payment smoke | {gate_results['payment_smoke_status']} |",
                f"| Source QA | {gate_results['source_qa_status']} |",
                f"| Source license/hash evidence | {'PASS' if gate_results['rights_tier'] == 'A' else 'MISSING'} |",
                f"| Rights tier | {gate_results['rights_tier']} |",
                f"| SEO landing | {gate_results['seo_status']}, non-public |",
                f"| Audio | {gate_results['audio_status']} |",
                f"| Approval artifact | {'CREATED' if gate_results['approved_to_publish_exists'] else 'NOT_CREATED'} |",
                "",
                source_note,
            ]
        ),
    )
    upsert_markdown_section(
        ROOT / "PRODUCTION_PARITY_REPORT.md",
        "Dracula Candidate Impact",
        "\n".join(
            [
                f"The latest post-deploy route canary is `{gate_results['route_canary_status']}`.",
                "",
                "- `output/launch/post_deploy_route_canary.json`",
                "- `output/launch/post_deploy_route_canary.txt`",
                "",
                "If this canary becomes `BLOCKED`, Dracula approval must remain blocked and `APPROVED_TO_PUBLISH.md` must not be generated.",
            ]
        ),
    )
    upsert_markdown_section(
        ROOT / "POST_DEPLOY_VERIFICATION.md",
        "Latest Dracula Candidate Evidence",
        "\n".join(
            [
                "- `output/launch/post_deploy_route_canary.json`",
                "- `output/launch/post_deploy_route_canary.txt`",
                f"- Current canary status: `{gate_results['route_canary_status']}`",
                "",
                "A failed future canary keeps production parity `BLOCKED` and prevents Dracula approval.",
            ]
        ),
    )
    upsert_markdown_section(
        ROOT / "AUDIOBOOK_READINESS_REPORT.md",
        "Dracula Controlled Candidate",
        "\n".join(
            [
                f"Dracula audio status for this publication package is `{gate_results['audio_status']}`.",
                "",
                "- No Dracula audio upload was performed.",
                "- No TTS, STT, FFmpeg, or paid provider call was performed.",
                "- No full Dracula audiobook is promoted by the non-public SEO or campaign drafts.",
                "- Linked Dracula audio must pass rights linkage, listening QA, sync/highlighting QA, and storage/provider confirmation before promotion.",
            ]
        ),
    )
    upsert_markdown_section(
        ROOT / "PAYMENT_REVENUE_FLOW_REPORT.md",
        "Dracula Candidate Use",
        "\n".join(
            [
                f"Dracula uses payment evidence as `{gate_results['payment_smoke_status']}` only.",
                "",
                "It does not prove live-money readiness, does not mutate production payments or wallets, and does not enable any public publication flag.",
            ]
        ),
    )


def seo_markdown(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Dracula SEO Landing Draft",
            "",
            "Status: `PASS_DRAFT`",
            "",
            f"- Public route enabled: `{payload['public_route_enabled']}`",
            f"- Title: {payload['title']}",
            f"- Canonical draft: {payload['canonical_url_draft']}",
            f"- Book JSON-LD status: `{payload['book_json_ld_status']}`",
            "",
            "This is a non-public static draft. It is not imported into the frontend router.",
            "",
        ]
    )


def campaign_markdown(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Dracula Hero Campaign Draft",
            "",
            f"Campaign: `{payload['campaign_name']}`",
            "",
            payload["headline"],
            "",
            "## Draft CTAs",
            "",
            *[f"- {cta}" for cta in payload["ctas"]],
            "",
            "No email, social, ad, or campaign page was published.",
            "",
        ]
    )


def audio_markdown(gate_results: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Dracula Audio Readiness",
            "",
            f"Audio status: `{gate_results['audio_status']}`",
            f"Phase 7 dry-run status: `{gate_results.get('phase7_publish_gate_status', '')}`",
            "",
            "- No TTS/STT/FFmpeg call was made.",
            "- No audio was uploaded.",
            "- No full audiobook is promoted by this candidate.",
            "- Full audio remains blocked unless linked rights and listening QA pass separately.",
            "",
        ]
    )


def growth_markdown(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Dracula Growth Loop Draft",
            "",
            "Status: `DRAFT_ONLY`",
            "",
            "## Loop",
            "",
            *[f"- {step}" for step in payload["loop"]],
            "",
            "## Metrics",
            "",
            *[f"- {metric}" for metric in payload["metrics"]],
            "",
            "No real email, social, campaign, or analytics send was performed.",
            "",
        ]
    )


def phase14_markdown(gate_results: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Phase 14 Dracula Publication Readiness Report",
            "",
            f"Recommendation: `{gate_results['recommendation']}`",
            f"Readiness score: `{gate_results['readiness_score']}/10`",
            "",
            "## Score Caps Applied",
            "",
            f"- Route canary status: `{gate_results['route_canary_status']}`",
            f"- Source QA status: `{gate_results['source_qa_status']}`",
            f"- Approved artifact exists: `{gate_results['approved_to_publish_exists']}`",
            f"- SEO status: `{gate_results['seo_status']}`",
            f"- Revenue status: `{gate_results['revenue_status']}`",
            f"- Audio status: `{gate_results['audio_status']}`",
            "",
            "No public activation was performed.",
            "",
        ]
    )


def scorecard_markdown(gate_results: dict[str, Any]) -> str:
    blockers = gate_results.get("high_blockers") or []
    return "\n".join(
        [
            "# Dracula Publication Scorecard",
            "",
            f"Score: `{gate_results['readiness_score']}/10`",
            f"Recommendation: `{gate_results['recommendation']}`",
            "",
            "## Blockers",
            "",
            *(f"- {blocker}" for blocker in blockers),
            *([] if blockers else ["- None."]),
            "",
            "Controlled-publication remains fail-closed unless `APPROVED_TO_PUBLISH.md` exists and precheck passes.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare Dracula as a dry-run controlled-publication candidate.")
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--source-text-url", default="")
    parser.add_argument("--source-text-file", default="")
    parser.add_argument("--slug", default="dracula")
    parser.add_argument("--title", default="Dracula")
    parser.add_argument("--author", default="Bram Stoker")
    parser.add_argument("--rollback-owner", default=DEFAULT_ROLLBACK_OWNER)
    parser.add_argument("--publication-cap", default=DEFAULT_PUBLICATION_CAP)
    parser.add_argument("--dry-run", action="store_true", default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.dry_run is not True:
        print("Dracula candidate preparation is dry-run only.", file=sys.stderr)
        return 2
    evidence = build_source_evidence(args)
    gate_results = build_gate_results(evidence)
    write_static_reports(evidence, gate_results)
    print(f"Dracula candidate status: {gate_results['recommendation']}")
    print(f"Source evidence: {OUTPUT_DIR / 'source_evidence.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
