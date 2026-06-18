from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from backend.automation_observability import observability_report_json, run_observability_guardrails
from backend.demand_scoring import score_book
from backend.publishing_workflow import evaluate_workflow, workflow_signals_from_book
from backend.rights_engine import evaluate_rights


FIRST_BATCH_VERSION = "earnalism-first-batch-dry-run-v1"
DEFAULT_AUDIO_PREVIEW_BUDGET = 0.0


@dataclass(frozen=True)
class BatchSourceMetadata:
    source_url: str
    source_name: str
    source_license: str
    source_hash: str
    content_hash: str
    provenance_hash: str
    rights_basis: str
    rights_note: str
    publication_region: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_url": self.source_url,
            "source_name": self.source_name,
            "source_license": self.source_license,
            "source_hash": self.source_hash,
            "content_hash": self.content_hash,
            "provenance_hash": self.provenance_hash,
            "rights_basis": self.rights_basis,
            "rights_note": self.rights_note,
            "publication_region": self.publication_region,
        }


@dataclass
class BatchProductReport:
    product_rank: int
    product_title: str
    work_title: str
    slug: str
    language: str
    rights_report: dict[str, Any]
    source_report: dict[str, Any]
    demand_score: dict[str, Any]
    source_metadata: dict[str, Any]
    ingestion_status: str
    edition_status: str
    visual_status: str
    publishing_workflow_status: str
    observability_guardrail_status: str
    phase_gate_report: dict[str, Any]
    edition_draft: dict[str, Any]
    study_guide_draft: dict[str, Any]
    visual_explainer_draft: dict[str, Any]
    quiz: dict[str, Any]
    reading_challenge: dict[str, Any]
    seo_draft: dict[str, Any]
    audiobook_preview_script: dict[str, Any]
    audio_preview: dict[str, Any]
    qa_report: dict[str, Any]
    publication_readiness_score: float
    publication_readiness_status: str
    blocked_reasons: list[str] = field(default_factory=list)
    dry_run: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "product_rank": self.product_rank,
            "product_title": self.product_title,
            "work_title": self.work_title,
            "slug": self.slug,
            "language": self.language,
            "rights_report": self.rights_report,
            "source_report": self.source_report,
            "demand_score": self.demand_score,
            "source_metadata": self.source_metadata,
            "ingestion_status": self.ingestion_status,
            "edition_status": self.edition_status,
            "visual_status": self.visual_status,
            "publishing_workflow_status": self.publishing_workflow_status,
            "observability_guardrail_status": self.observability_guardrail_status,
            "phase_gate_report": self.phase_gate_report,
            "edition_draft": self.edition_draft,
            "study_guide_draft": self.study_guide_draft,
            "visual_explainer_draft": self.visual_explainer_draft,
            "quiz": self.quiz,
            "reading_challenge": self.reading_challenge,
            "seo_draft": self.seo_draft,
            "audiobook_preview_script": self.audiobook_preview_script,
            "audio_preview": self.audio_preview,
            "qa_report": self.qa_report,
            "publication_readiness_score": round(self.publication_readiness_score, 2),
            "publication_readiness_status": self.publication_readiness_status,
            "blocked_reasons": self.blocked_reasons,
            "dry_run": self.dry_run,
        }


@dataclass
class FirstBatchDryRunReport:
    status: str
    products: list[BatchProductReport]
    dry_run: bool = True

    def as_dict(self) -> dict[str, Any]:
        statuses = [product.publication_readiness_status for product in self.products]
        audio_statuses = [product.audio_preview.get("status") for product in self.products]
        source_statuses = [product.source_report.get("source_status") for product in self.products]
        rights_statuses = [product.rights_report.get("rights_status") for product in self.products]
        qa_statuses = [product.qa_report.get("qa_status") for product in self.products]
        return {
            "batch_version": FIRST_BATCH_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": self.status,
            "dry_run": self.dry_run,
            "summary": {
                "selected": len(self.products),
                "ready_for_publication_draft": statuses.count("READY_FOR_PUBLICATION_DRAFT"),
                "ready_for_publication_draft_candidate": statuses.count("READY_FOR_PUBLICATION_DRAFT_CANDIDATE"),
                "region_gated_draft_review": statuses.count("REGION_GATED_DRAFT_REVIEW"),
                "source_metadata_required": source_statuses.count("SOURCE_METADATA_REQUIRED"),
                "rights_or_source_blocked": sum(1 for status in rights_statuses if status in {"BLOCKED", "QUARANTINED"})
                + source_statuses.count("SOURCE_METADATA_REQUIRED"),
                "qa_blocked": qa_statuses.count("BLOCKED"),
                "audio_skipped_provider_not_configured": audio_statuses.count("SKIPPED_PROVIDER_NOT_CONFIGURED"),
                "audio_skipped_budget": audio_statuses.count("SKIPPED_BUDGET_EXCEEDED"),
                "public_publish_actions": 0,
            },
            "products": [product.as_dict() for product in self.products],
        }


def run_first_batch_dry_run(payload: dict[str, Any] | None = None) -> FirstBatchDryRunReport:
    payload = payload or {}
    if payload.get("dry_run") is False:
        return FirstBatchDryRunReport(status="BLOCKED_NON_DRY_RUN", products=[])
    if payload.get("publish") is True:
        return FirstBatchDryRunReport(status="BLOCKED_PUBLICATION_DISABLED", products=[])

    audio_provider_configured = bool(payload.get("audio_provider_configured"))
    audio_budget_remaining = float_or_zero(payload.get("audio_preview_budget"), DEFAULT_AUDIO_PREVIEW_BUDGET)
    product_inputs = payload.get("products") if isinstance(payload.get("products"), list) else first_batch_products()
    products: list[BatchProductReport] = []

    for index, product in enumerate(product_inputs, start=1):
        if not isinstance(product, dict):
            continue
        report, audio_budget_remaining = build_product_report(
            product,
            product_rank=index,
            audio_provider_configured=audio_provider_configured,
            audio_budget_remaining=audio_budget_remaining,
        )
        products.append(report)

    status = "DRY_RUN_COMPLETE"
    if any(product.blocked_reasons for product in products):
        status = "DRY_RUN_COMPLETE_WITH_BLOCKS"
    return FirstBatchDryRunReport(status=status, products=products)


def build_product_report(
    product: dict[str, Any],
    *,
    product_rank: int,
    audio_provider_configured: bool,
    audio_budget_remaining: float,
) -> tuple[BatchProductReport, float]:
    source = source_metadata_for(product)
    rights_report = rights_report_for(product, source)
    source_report = source_report_for(source)
    book = book_record_for(product, source, rights_report)
    demand = score_book(book)
    ingestion_status = ingestion_status_for(source_report, rights_report)
    audio_preview, updated_audio_budget = audio_preview_for(
        product,
        provider_configured=audio_provider_configured,
        budget_remaining=audio_budget_remaining,
    )
    edition_status = phase5_edition_status(source_report, rights_report, ingestion_status, demand.action_status)
    visual_status = phase6_visual_status(source_report, rights_report, ingestion_status, edition_status, demand.action_status)
    audio_status = phase7_audio_status(audio_preview)
    workflow = phase8_workflow_report(
        product=product,
        rights_report=rights_report,
        demand_action_status=demand.action_status,
        ingestion_status=ingestion_status,
        edition_status=edition_status,
        visual_status=visual_status,
        audio_status=audio_status,
    )
    observability = phase10_observability_report(product, source, rights_report)
    phase_gate_report = phase_gate_report_for(
        rights_report=rights_report,
        demand_action_status=demand.action_status,
        ingestion_status=ingestion_status,
        edition_status=edition_status,
        visual_status=visual_status,
        audio_status=audio_status,
        workflow=workflow,
        observability=observability,
    )
    qa_report = qa_report_for(
        product,
        source,
        rights_report,
        source_report,
        ingestion_status,
        workflow,
        observability,
    )
    blocked_reasons = list(qa_report["blocking_reasons"])
    publication_readiness_score = readiness_score(
        demand_score=demand.demand_score,
        rights_report=rights_report,
        source_report=source_report,
        ingestion_status=ingestion_status,
        qa_report=qa_report,
        workflow=workflow,
        audio_preview=audio_preview,
    )
    publication_readiness_status = readiness_status(
        score=publication_readiness_score,
        rights_report=rights_report,
        source_report=source_report,
        workflow=workflow,
        blocked_reasons=blocked_reasons,
    )

    return (
        BatchProductReport(
            product_rank=product_rank,
            product_title=text(product.get("product_title")),
            work_title=text(product.get("work_title")),
            slug=text(product.get("slug")),
            language=text(product.get("language")),
            rights_report=rights_report,
            source_report=source_report,
            demand_score=demand.as_row(),
            source_metadata=source.as_dict(),
            ingestion_status=ingestion_status,
            edition_status=edition_status,
            visual_status=visual_status,
            publishing_workflow_status=workflow["publish_readiness"],
            observability_guardrail_status=observability["status"],
            phase_gate_report=phase_gate_report,
            edition_draft=draft_payload(product, "edition_draft", "Earnalism reading edition draft"),
            study_guide_draft=draft_payload(product, "study_guide_draft", "Study guide draft"),
            visual_explainer_draft=draft_payload(product, "visual_explainer_draft", "Visual explainer draft"),
            quiz=quiz_payload(product),
            reading_challenge=reading_challenge_payload(product),
            seo_draft=seo_payload(product),
            audiobook_preview_script=audiobook_script_payload(product),
            audio_preview=audio_preview,
            qa_report=qa_report,
            publication_readiness_score=publication_readiness_score,
            publication_readiness_status=publication_readiness_status,
            blocked_reasons=blocked_reasons,
        ),
        updated_audio_budget,
    )


def first_batch_products() -> list[dict[str, Any]]:
    return [
        batch_product("Anandamath Visual Study Companion", "Anandamath", "anandamath-visual-study-companion", "ben", "B"),
        batch_product("Devdas Study Edition", "Devdas", "devdas-study-edition", "ben", "B"),
        batch_product("Abol Tabol Illustrated Reader", "Abol Tabol", "abol-tabol-illustrated-reader", "ben", "B"),
        batch_product("Sultana's Dream Feminist Sci-Fi Edition", "Sultana's Dream", "sultanas-dream-feminist-sci-fi-edition", "en", "A"),
        batch_product("Sherlock Holmes Logic Workbook", "Sherlock Holmes", "sherlock-holmes-logic-workbook", "en", "A"),
        batch_product("Dracula Gothic Fiction Visual Guide", "Dracula", "dracula-gothic-fiction-visual-guide", "en", "A", audiobook=True),
        batch_product("Frankenstein Science & Ethics Guide", "Frankenstein", "frankenstein-science-ethics-guide", "en", "A", audiobook=True),
        batch_product("Tagore Short Stories for Young Readers", "Tagore Short Stories", "tagore-short-stories-young-readers", "ben", "B"),
        batch_product("Calculus Made Easy Visual Guide", "Calculus Made Easy", "calculus-made-easy-visual-guide", "en", "A"),
        batch_product("Chander Pahar Adventure Companion", "Chander Pahar", "chander-pahar-adventure-companion", "ben", "B"),
    ]


def batch_product(
    product_title: str,
    work_title: str,
    slug: str,
    language: str,
    rights_tier: str,
    *,
    audiobook: bool = False,
) -> dict[str, Any]:
    publication_region = "india" if rights_tier == "B" else "global"
    author = author_metadata_for(work_title)
    return {
        "product_title": product_title,
        "work_title": work_title,
        "slug": slug,
        "language": language,
        "category_slug": category_for_product(product_title),
        "audiobook_recommended": audiobook or language in {"ben", "en"},
        "rights_metadata": {
            "work_title": work_title,
            "work_slug": slug,
            "author_name": author["author_name"],
            "author_death_year": author["author_death_year"],
            "original_publication_year": author["original_publication_year"],
            "country_of_origin": author["country_of_origin"],
            "rights_tier": rights_tier,
            "verification_status": "approved",
            "publication_region": publication_region,
            "region_gate_acknowledged": rights_tier == "B",
            "blocked_reason": "",
            "verified_at": "2026-06-18T00:00:00Z",
        },
        "source_url": f"urn:earnalism:dry-run-source:{slug}",
        "source_name": "Earnalism internal dry-run rights/source fixture",
        "source_license": "Public Domain dry-run fixture",
        "rights_basis": "Dry-run rights fixture; replace with verified source evidence before production.",
        "rights_note": "Phase 11 does not publish and treats fixture source metadata as not publication-ready.",
    }


def source_metadata_for(product: dict[str, Any]) -> BatchSourceMetadata:
    slug = text(product.get("slug"))
    source_url = text(product.get("source_url"))
    source_name = text(product.get("source_name"))
    source_license = text(product.get("source_license"))
    content_key = stable_hash(f"{slug}:{product.get('work_title')}:{source_url}:{source_license}")
    source_hash = field_or_default(product, "source_hash", f"sha256:{stable_hash(source_url or slug)}")
    content_hash = field_or_default(product, "content_hash", f"sha256:{content_key}")
    provenance_hash = field_or_default(
        product,
        "provenance_hash",
        f"sha256:{stable_hash(source_url + source_name + source_license + content_hash)}",
    )
    return BatchSourceMetadata(
        source_url=source_url,
        source_name=source_name,
        source_license=source_license,
        source_hash=source_hash,
        content_hash=content_hash,
        provenance_hash=provenance_hash,
        rights_basis=text(product.get("rights_basis")),
        rights_note=text(product.get("rights_note")),
        publication_region=text(
            (product.get("rights_metadata") if isinstance(product.get("rights_metadata"), dict) else {}).get("publication_region")
            or product.get("publication_region")
        ),
    )


def book_record_for(product: dict[str, Any], source: BatchSourceMetadata, rights_report: dict[str, Any]) -> dict[str, Any]:
    rights = product.get("rights_metadata") if isinstance(product.get("rights_metadata"), dict) else {}
    return {
        "title": product.get("work_title"),
        "slug": product.get("slug"),
        "category_slug": product.get("category_slug"),
        "language": product.get("language"),
        "audiobook_enabled": product.get("audiobook_recommended"),
        "rights_metadata": {
            **rights,
            "source_url": source.source_url,
            "source_name": source.source_name,
            "source_license": source.source_license,
            "publication_region": rights_report["publication_region"],
        },
    }


def rights_report_for(product: dict[str, Any], source: BatchSourceMetadata) -> dict[str, Any]:
    rights = product.get("rights_metadata") if isinstance(product.get("rights_metadata"), dict) else {}
    phase2_decision = evaluate_rights(rights_engine_book_for(product, source), current_year=2026)
    rights_tier = text(rights.get("rights_tier")).upper()
    verification_status = text(rights.get("verification_status")).lower()
    blocked_reason = text(rights.get("blocked_reason"))
    publication_region = text(rights.get("publication_region") or "global").lower()
    region_gate_acknowledged = bool(rights.get("region_gate_acknowledged"))
    issues: list[str] = []
    status = "APPROVED"
    if rights_tier == "C" or blocked_reason:
        status = "BLOCKED"
        issues.append(blocked_reason or "Tier C rights are unsafe.")
    elif not phase2_decision.approved:
        status = "BLOCKED" if phase2_decision.status == "blocked" else "QUARANTINED"
        issues.extend(phase2_decision.issues)
    elif rights_tier == "B":
        status = "REGION_GATED_APPROVED" if publication_region == "india" and region_gate_acknowledged else "REGION_GATED_REVIEW"
        if status == "REGION_GATED_REVIEW":
            issues.append("Tier B requires India-only region gate acknowledgement.")
    elif rights_tier != "A" or verification_status not in {"approved", "verified"}:
        status = "QUARANTINED"
        issues.append("Rights metadata is missing or not approved.")
    return {
        "rights_tier": rights_tier or "UNKNOWN",
        "verification_status": verification_status or "missing",
        "publication_region": publication_region,
        "region_gate_acknowledged": region_gate_acknowledged,
        "rights_status": status,
        "issues": issues,
        "phase2_decision_status": phase2_decision.status,
        "phase2_decision_issues": phase2_decision.issues,
        "public_publish_allowed": False,
    }


def rights_engine_book_for(product: dict[str, Any], source: BatchSourceMetadata) -> dict[str, Any]:
    rights = product.get("rights_metadata") if isinstance(product.get("rights_metadata"), dict) else {}
    metadata = {
        **rights,
        "source_url": source.source_url,
        "source_name": source.source_name,
        "source_license": source.source_license,
    }
    return {
        "title": product.get("work_title"),
        "slug": product.get("slug"),
        "author": rights.get("author_name"),
        "rights_metadata": metadata,
    }


def source_report_for(source: BatchSourceMetadata) -> dict[str, Any]:
    issues: list[str] = []
    for field_name in (
        "source_url",
        "source_name",
        "source_license",
        "source_hash",
        "content_hash",
        "provenance_hash",
        "publication_region",
    ):
        if not text(getattr(source, field_name)):
            issues.append(f"{field_name} is required.")
    if not source.rights_basis and not source.rights_note:
        issues.append("rights_basis or rights_note is required.")
    if source.source_url.startswith("urn:") or "fixture" in source.source_license.lower() or "fixture" in source.source_name.lower():
        issues.append("Fixture source metadata must be replaced with verified public source evidence.")
    source_status = "SOURCE_METADATA_REQUIRED" if issues else "SOURCE_TRACEABILITY_READY"
    return {
        "source_status": source_status,
        "issues": issues,
        "fixture_source": source.source_url.startswith("urn:") or "fixture" in source.source_license.lower(),
        "required_fields_present": not issues,
    }


def ingestion_status_for(source_report: dict[str, Any], rights_report: dict[str, Any]) -> str:
    if rights_report["rights_status"] in {"BLOCKED", "QUARANTINED", "REGION_GATED_REVIEW"}:
        return "BLOCKED_RIGHTS"
    if source_report["source_status"] != "SOURCE_TRACEABILITY_READY":
        return "SOURCE_METADATA_REQUIRED"
    return "CLEANED_DRY_RUN"


def phase5_edition_status(
    source_report: dict[str, Any],
    rights_report: dict[str, Any],
    ingestion_status: str,
    demand_action_status: str,
) -> str:
    if rights_report["rights_status"] in {"BLOCKED", "QUARANTINED", "REGION_GATED_REVIEW"}:
        return "BLOCKED_RIGHTS"
    if source_report["source_status"] != "SOURCE_TRACEABILITY_READY":
        return "BLOCKED_TRACEABILITY"
    if demand_action_status not in {"READY_FOR_GENERATION", "REGION_GATED_PRIORITY"}:
        return "BLOCKED_PRIORITY_GATE"
    if ingestion_status != "CLEANED_DRY_RUN":
        return "BLOCKED_INGESTION"
    return "QA_PASSED"


def phase6_visual_status(
    source_report: dict[str, Any],
    rights_report: dict[str, Any],
    ingestion_status: str,
    edition_status: str,
    demand_action_status: str,
) -> str:
    if edition_status != "QA_PASSED":
        return "BLOCKED_EDITION_GATE"
    if rights_report["rights_status"] in {"BLOCKED", "QUARANTINED", "REGION_GATED_REVIEW"}:
        return "BLOCKED_RIGHTS"
    if source_report["source_status"] != "SOURCE_TRACEABILITY_READY":
        return "BLOCKED_TRACEABILITY"
    if demand_action_status not in {"READY_FOR_GENERATION", "REGION_GATED_PRIORITY"}:
        return "BLOCKED_PRIORITY_GATE"
    if ingestion_status != "CLEANED_DRY_RUN":
        return "BLOCKED_INGESTION"
    return "QA_PASSED"


def phase7_audio_status(audio_preview: dict[str, Any]) -> str:
    if audio_preview["status"] == "SKIPPED_BUDGET_EXCEEDED":
        return "BLOCKED_COST"
    if audio_preview["status"] in {"SKIPPED_PROVIDER_NOT_CONFIGURED", "PREVIEW_PLAN_READY_DRY_RUN"}:
        return "DRY_RUN_READY"
    if audio_preview["status"] == "AUDIO_NOT_REQUIRED":
        return "AUDIO_NOT_REQUIRED"
    return "BLOCKED_AUDIO_GATE"


def phase8_workflow_report(
    *,
    product: dict[str, Any],
    rights_report: dict[str, Any],
    demand_action_status: str,
    ingestion_status: str,
    edition_status: str,
    visual_status: str,
    audio_status: str,
) -> dict[str, Any]:
    rights = product.get("rights_metadata") if isinstance(product.get("rights_metadata"), dict) else {}
    workflow_book = {
        "slug": product.get("slug"),
        "title": product.get("work_title"),
        "rights_metadata": {
            "rights_tier": rights_report["rights_tier"],
            "verification_status": rights_report["verification_status"],
            "publication_region": rights_report["publication_region"],
            "blocked_reason": "; ".join(rights_report["issues"]),
        },
        "demand": {"action_status": demand_action_status},
        "ingestion_status": "CLEANED" if ingestion_status == "CLEANED_DRY_RUN" else ingestion_status,
        "edition_generation_status": edition_status,
        "visual_status": visual_status,
        "audio_status": audio_status,
        "qa": {"qa_status": "QA_PASSED", "warnings": []},
        "cost": {"used": 0, "budget": 1},
        "is_published": False,
    }
    decision = evaluate_workflow(workflow_signals_from_book(workflow_book))
    return {
        "state": decision.state,
        "publish_readiness": decision.publish_readiness,
        "blockers": decision.blockers,
        "phase8_validated": True,
        "dry_run": True,
    }


def phase10_observability_report(
    product: dict[str, Any],
    source: BatchSourceMetadata,
    rights_report: dict[str, Any],
) -> dict[str, Any]:
    result = run_observability_guardrails(
        {
            "dry_run": True,
            "actions": [
                {
                    "action_id": f"phase11-{product['slug']}",
                    "slug": product.get("slug"),
                    "phase": "publishing_workflow",
                    "action_type": "first_batch_product_candidate",
                    "rights": {
                        "rights_tier": rights_report["rights_tier"],
                        "verification_status": rights_report["verification_status"],
                        "publication_region": rights_report["publication_region"],
                        "region_gate_acknowledged": rights_report["region_gate_acknowledged"],
                        "blocked_reason": "; ".join(rights_report["issues"]),
                    },
                    "requires_source": True,
                    "source_url": source.source_url,
                    "source_name": source.source_name,
                    "source_license": source.source_license,
                    "source_hash": source.source_hash,
                    "content_hash": source.content_hash,
                    "provenance_hash": source.provenance_hash,
                    "estimated_cost": 0,
                    "budget_remaining": 0,
                }
            ],
        }
    )
    data = observability_report_json(result)
    action = data["actions"][0] if data["actions"] else {}
    return {
        "status": data["status"],
        "action_status": action.get("decision_status", "UNKNOWN"),
        "blocking_reasons": action.get("blocking_reasons", []),
        "guardrail_type_counts": data["summary"].get("guardrail_type_counts", {}),
        "phase10_validated": True,
        "dry_run": True,
    }


def phase_gate_report_for(
    *,
    rights_report: dict[str, Any],
    demand_action_status: str,
    ingestion_status: str,
    edition_status: str,
    visual_status: str,
    audio_status: str,
    workflow: dict[str, Any],
    observability: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase2_rights": rights_report["phase2_decision_status"],
        "phase3_demand": demand_action_status,
        "phase4_ingestion": ingestion_status,
        "phase5_edition": edition_status,
        "phase6_visual": visual_status,
        "phase7_audio": audio_status,
        "phase8_workflow": workflow["publish_readiness"],
        "phase10_observability": observability["action_status"],
        "compatibility_validated": True,
        "dry_run": True,
    }


def qa_report_for(
    product: dict[str, Any],
    source: BatchSourceMetadata,
    rights_report: dict[str, Any],
    source_report: dict[str, Any],
    ingestion_status: str,
    workflow: dict[str, Any],
    observability: dict[str, Any],
) -> dict[str, Any]:
    warnings: list[str] = []
    blockers: list[str] = []
    if rights_report["rights_status"] in {"BLOCKED", "QUARANTINED", "REGION_GATED_REVIEW"}:
        blockers.extend(rights_report["issues"] or [rights_report["rights_status"]])
    if source_report["source_status"] != "SOURCE_TRACEABILITY_READY":
        blockers.extend(source_report["issues"])
    if ingestion_status != "CLEANED_DRY_RUN":
        blockers.append(f"Ingestion not ready: {ingestion_status}")
    if not source.provenance_hash:
        blockers.append("Missing provenance hash.")
    if workflow["publish_readiness"] not in {"READY", "REGION_GATED_REVIEW"}:
        blockers.extend(workflow["blockers"])
    if observability["action_status"] == "BLOCKED":
        blockers.extend(observability["blocking_reasons"])
    if rights_report["rights_status"] == "REGION_GATED_APPROVED":
        warnings.append("India-only region-gated draft; not global-ready.")
    if text(product.get("language")) == "ben":
        warnings.append("Bengali editorial review required before any public launch.")
    return {
        "qa_status": "BLOCKED" if blockers else "QA_PASSED_DRY_RUN",
        "blocking_reasons": blockers,
        "warnings": warnings,
        "dry_run": True,
        "public_publish_allowed": False,
    }


def draft_payload(product: dict[str, Any], draft_type: str, title: str) -> dict[str, Any]:
    return {
        "draft_type": draft_type,
        "title": title,
        "body_preview": f"{title} for {product['product_title']} prepared as a dry-run outline.",
        "public": False,
        "dry_run": True,
    }


def quiz_payload(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "draft_type": "quiz",
        "question_count": 5,
        "body_preview": f"Five comprehension and reflection prompts for {product['work_title']}.",
        "public": False,
        "dry_run": True,
    }


def reading_challenge_payload(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "draft_type": "reading_challenge",
        "duration_days": 7,
        "body_preview": f"Seven-day guided reading challenge for {product['product_title']}.",
        "public": False,
        "dry_run": True,
    }


def seo_payload(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "draft_type": "seo_draft",
        "title_preview": f"{product['product_title']} | Earnalism",
        "description_preview": f"Explore {product['work_title']} through a guided Earnalism study companion.",
        "canonical_preview": f"/product-drafts/{product['slug']}",
        "public": False,
        "dry_run": True,
    }


def audiobook_script_payload(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "draft_type": "audiobook_preview_script",
        "duration_target_seconds": 90,
        "script_preview": f"Welcome to Earnalism. In this preview, we begin {product['product_title']} with context and a short passage.",
        "public": False,
        "dry_run": True,
    }


def audio_preview_for(product: dict[str, Any], *, provider_configured: bool, budget_remaining: float) -> tuple[dict[str, Any], float]:
    estimated_cost = 1.0
    if not product.get("audiobook_recommended"):
        return ({"status": "AUDIO_NOT_REQUIRED", "dry_run": True, "public": False}, budget_remaining)
    if not provider_configured:
        return ({"status": "SKIPPED_PROVIDER_NOT_CONFIGURED", "dry_run": True, "public": False}, budget_remaining)
    if budget_remaining < estimated_cost:
        return ({"status": "SKIPPED_BUDGET_EXCEEDED", "estimated_cost": estimated_cost, "dry_run": True, "public": False}, budget_remaining)
    return (
        {
            "status": "PREVIEW_PLAN_READY_DRY_RUN",
            "estimated_cost": estimated_cost,
            "duration_target_seconds": 90,
            "provider_call_executed": False,
            "dry_run": True,
            "public": False,
        },
        budget_remaining - estimated_cost,
    )


def readiness_score(
    *,
    demand_score: float,
    rights_report: dict[str, Any],
    source_report: dict[str, Any],
    ingestion_status: str,
    qa_report: dict[str, Any],
    workflow: dict[str, Any],
    audio_preview: dict[str, Any],
) -> float:
    score = 40.0 + min(30.0, demand_score * 0.3)
    if rights_report["rights_status"] == "APPROVED":
        score += 15
    elif rights_report["rights_status"] == "REGION_GATED_APPROVED":
        score += 9
    if source_report["source_status"] == "SOURCE_TRACEABILITY_READY":
        score += 10
    else:
        score -= 15
    if ingestion_status == "CLEANED_DRY_RUN":
        score += 8
    if qa_report["qa_status"] == "QA_PASSED_DRY_RUN":
        score += 7
    if workflow["publish_readiness"] == "READY":
        score += 8
    elif workflow["publish_readiness"] == "REGION_GATED_REVIEW":
        score += 3
    if audio_preview["status"] in {"PREVIEW_PLAN_READY_DRY_RUN", "AUDIO_NOT_REQUIRED", "SKIPPED_PROVIDER_NOT_CONFIGURED"}:
        score += 3
    if qa_report["blocking_reasons"]:
        score -= 35
    return max(0, min(100, score))


def readiness_status(
    score: float,
    rights_report: dict[str, Any],
    source_report: dict[str, Any],
    workflow: dict[str, Any],
    blocked_reasons: list[str],
) -> str:
    if blocked_reasons:
        if rights_report["rights_status"] in {"BLOCKED", "QUARANTINED", "REGION_GATED_REVIEW"}:
            return "QUARANTINED_DRY_RUN"
        if rights_report["rights_status"] == "REGION_GATED_APPROVED":
            return "REGION_GATED_DRAFT_REVIEW"
        if source_report["source_status"] != "SOURCE_TRACEABILITY_READY":
            return "SOURCE_METADATA_REQUIRED"
        return "QUARANTINED_DRY_RUN"
    if rights_report["rights_status"] == "REGION_GATED_APPROVED":
        return "REGION_GATED_DRAFT_REVIEW"
    if workflow["publish_readiness"] == "READY" and score >= 80:
        return "READY_FOR_PUBLICATION_DRAFT_CANDIDATE"
    return "QA_REVIEW_DRAFT"


def first_batch_report_json(report: FirstBatchDryRunReport) -> dict[str, Any]:
    return report.as_dict()


def first_batch_report_csv(report: FirstBatchDryRunReport) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "product_rank",
            "slug",
            "product_title",
            "rights_status",
            "source_status",
            "demand_score",
            "ingestion_status",
            "edition_status",
            "visual_status",
            "audio_status",
            "publishing_workflow_status",
            "observability_guardrail_status",
            "qa_status",
            "publication_readiness_score",
            "publication_readiness_status",
            "publication_region",
            "dry_run",
        ],
    )
    writer.writeheader()
    for product in report.products:
        row = product.as_dict()
        writer.writerow(
            {
                "product_rank": row["product_rank"],
                "slug": row["slug"],
                "product_title": row["product_title"],
                "rights_status": row["rights_report"]["rights_status"],
                "source_status": row["source_report"]["source_status"],
                "demand_score": row["demand_score"]["demand_score"],
                "ingestion_status": row["ingestion_status"],
                "edition_status": row["edition_status"],
                "visual_status": row["visual_status"],
                "audio_status": row["audio_preview"]["status"],
                "publishing_workflow_status": row["publishing_workflow_status"],
                "observability_guardrail_status": row["observability_guardrail_status"],
                "qa_status": row["qa_report"]["qa_status"],
                "publication_readiness_score": row["publication_readiness_score"],
                "publication_readiness_status": row["publication_readiness_status"],
                "publication_region": row["rights_report"]["publication_region"],
                "dry_run": row["dry_run"],
            }
        )
    return output.getvalue()


def first_batch_report_markdown(report: FirstBatchDryRunReport) -> str:
    data = report.as_dict()
    lines = [
        "# First Batch Dry-Run Report",
        "",
        f"- Status: `{data['status']}`",
        f"- Dry run: `{str(data['dry_run']).lower()}`",
        f"- Selected: `{data['summary']['selected']}`",
        f"- Ready drafts: `{data['summary']['ready_for_publication_draft']}`",
        f"- Ready draft candidates: `{data['summary']['ready_for_publication_draft_candidate']}`",
        f"- Region-gated draft review: `{data['summary']['region_gated_draft_review']}`",
        f"- Source metadata required: `{data['summary']['source_metadata_required']}`",
        f"- Rights or source blocked: `{data['summary']['rights_or_source_blocked']}`",
        f"- QA blocked: `{data['summary']['qa_blocked']}`",
        f"- Audio skipped, provider not configured: `{data['summary']['audio_skipped_provider_not_configured']}`",
        f"- Audio skipped, budget: `{data['summary']['audio_skipped_budget']}`",
        f"- Public publish actions: `{data['summary']['public_publish_actions']}`",
        "",
        "## Products",
    ]
    for product in data["products"]:
        lines.extend(
            [
                "",
                f"### {product['product_rank']}. {product['product_title']}",
                "",
                f"- Slug: `{product['slug']}`",
                f"- Rights: `{product['rights_report']['rights_status']}`",
                f"- Source: `{product['source_report']['source_status']}`",
                f"- Demand score: `{product['demand_score']['demand_score']}`",
                f"- Ingestion: `{product['ingestion_status']}`",
                f"- Edition: `{product['edition_status']}`",
                f"- Visual: `{product['visual_status']}`",
                f"- Audio: `{product['audio_preview']['status']}`",
                f"- Publishing workflow: `{product['publishing_workflow_status']}`",
                f"- Observability guardrail: `{product['observability_guardrail_status']}`",
                f"- QA: `{product['qa_report']['qa_status']}`",
                f"- Readiness score: `{product['publication_readiness_score']}`",
                f"- Readiness status: `{product['publication_readiness_status']}`",
                f"- Publication region: `{product['rights_report']['publication_region']}`",
                f"- Dry run: `{str(product['dry_run']).lower()}`",
            ]
        )
        if product["blocked_reasons"]:
            lines.append(f"- Blocked reasons: `{'; '.join(product['blocked_reasons'])}`")
    return "\n".join(lines) + "\n"


def category_for_product(product_title: str) -> str:
    lowered = product_title.lower()
    if "calculus" in lowered:
        return "study-material"
    if "sci-fi" in lowered:
        return "science-fiction"
    if "gothic" in lowered or "dracula" in lowered or "frankenstein" in lowered:
        return "gothic-fiction"
    if "young" in lowered or "abol" in lowered:
        return "young-readers"
    if "logic" in lowered:
        return "mystery"
    if "adventure" in lowered:
        return "adventure"
    return "literary-fiction"


def author_metadata_for(work_title: str) -> dict[str, Any]:
    metadata = {
        "Anandamath": ("Bankim Chandra Chattopadhyay", 1894, 1882, "India"),
        "Devdas": ("Sarat Chandra Chattopadhyay", 1938, 1917, "India"),
        "Abol Tabol": ("Sukumar Ray", 1923, 1923, "India"),
        "Sultana's Dream": ("Rokeya Sakhawat Hossain", 1932, 1905, "India"),
        "Sherlock Holmes": ("Arthur Conan Doyle", 1930, 1892, "United Kingdom"),
        "Dracula": ("Bram Stoker", 1912, 1897, "United Kingdom"),
        "Frankenstein": ("Mary Wollstonecraft Shelley", 1851, 1818, "United Kingdom"),
        "Tagore Short Stories": ("Rabindranath Tagore", 1941, 1891, "India"),
        "Calculus Made Easy": ("Silvanus P. Thompson", 1916, 1910, "United Kingdom"),
        "Chander Pahar": ("Bibhutibhushan Bandyopadhyay", 1950, 1937, "India"),
    }
    author_name, author_death_year, original_publication_year, country = metadata.get(
        work_title,
        ("Unknown", "", "", ""),
    )
    return {
        "author_name": author_name,
        "author_death_year": author_death_year,
        "original_publication_year": original_publication_year,
        "country_of_origin": country,
    }


def field_or_default(product: dict[str, Any], field_name: str, default: str) -> str:
    if field_name in product:
        return text(product.get(field_name))
    return default


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def text(value: Any) -> str:
    return str(value or "").strip()


def float_or_zero(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
