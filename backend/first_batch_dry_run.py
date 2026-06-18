from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from backend.demand_scoring import score_book


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

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_url": self.source_url,
            "source_name": self.source_name,
            "source_license": self.source_license,
            "source_hash": self.source_hash,
            "content_hash": self.content_hash,
            "provenance_hash": self.provenance_hash,
        }


@dataclass
class BatchProductReport:
    product_rank: int
    product_title: str
    work_title: str
    slug: str
    language: str
    rights_report: dict[str, Any]
    demand_score: dict[str, Any]
    source_metadata: dict[str, Any]
    ingestion_status: str
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
            "demand_score": self.demand_score,
            "source_metadata": self.source_metadata,
            "ingestion_status": self.ingestion_status,
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
        ready_count = sum(1 for product in self.products if product.publication_readiness_status == "READY_FOR_PUBLICATION_DRAFT")
        blocked_count = sum(1 for product in self.products if product.blocked_reasons)
        return {
            "batch_version": FIRST_BATCH_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": self.status,
            "dry_run": self.dry_run,
            "summary": {
                "selected": len(self.products),
                "ready_for_publication_draft": ready_count,
                "blocked_or_quarantined": blocked_count,
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
    book = book_record_for(product, source)
    demand = score_book(book)
    rights_report = rights_report_for(product)
    ingestion_status = ingestion_status_for(source, rights_report)
    qa_report = qa_report_for(product, source, rights_report, ingestion_status)
    blocked_reasons = list(qa_report["blocking_reasons"])
    audio_preview, updated_audio_budget = audio_preview_for(
        product,
        provider_configured=audio_provider_configured,
        budget_remaining=audio_budget_remaining,
    )
    publication_readiness_score = readiness_score(
        demand_score=demand.demand_score,
        rights_report=rights_report,
        ingestion_status=ingestion_status,
        qa_report=qa_report,
        audio_preview=audio_preview,
    )
    publication_readiness_status = readiness_status(
        score=publication_readiness_score,
        rights_report=rights_report,
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
            demand_score=demand.as_row(),
            source_metadata=source.as_dict(),
            ingestion_status=ingestion_status,
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
    return {
        "product_title": product_title,
        "work_title": work_title,
        "slug": slug,
        "language": language,
        "category_slug": category_for_product(product_title),
        "audiobook_recommended": audiobook or language in {"ben", "en"},
        "rights_metadata": {
            "rights_tier": rights_tier,
            "verification_status": "approved",
            "publication_region": publication_region,
            "region_gate_acknowledged": rights_tier == "B",
            "blocked_reason": "",
        },
        "source_url": f"urn:earnalism:dry-run-source:{slug}",
        "source_name": "Earnalism internal dry-run rights/source fixture",
        "source_license": "public-domain-dry-run-evidence",
    }


def source_metadata_for(product: dict[str, Any]) -> BatchSourceMetadata:
    slug = text(product.get("slug"))
    source_url = text(product.get("source_url"))
    source_name = text(product.get("source_name"))
    source_license = text(product.get("source_license"))
    content_key = stable_hash(f"{slug}:{product.get('work_title')}:{source_url}:{source_license}")
    source_hash = text(product.get("source_hash")) or f"sha256:{stable_hash(source_url or slug)}"
    content_hash = text(product.get("content_hash")) or f"sha256:{content_key}"
    provenance_hash = text(product.get("provenance_hash")) or f"sha256:{stable_hash(source_url + source_name + source_license + content_hash)}"
    return BatchSourceMetadata(
        source_url=source_url,
        source_name=source_name,
        source_license=source_license,
        source_hash=source_hash,
        content_hash=content_hash,
        provenance_hash=provenance_hash,
    )


def book_record_for(product: dict[str, Any], source: BatchSourceMetadata) -> dict[str, Any]:
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
        },
    }


def rights_report_for(product: dict[str, Any]) -> dict[str, Any]:
    rights = product.get("rights_metadata") if isinstance(product.get("rights_metadata"), dict) else {}
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
        "public_publish_allowed": False,
    }


def ingestion_status_for(source: BatchSourceMetadata, rights_report: dict[str, Any]) -> str:
    if rights_report["rights_status"] in {"BLOCKED", "QUARANTINED", "REGION_GATED_REVIEW"}:
        return "BLOCKED_RIGHTS"
    if not all([source.source_url, source.source_name, source.source_license, source.source_hash, source.content_hash, source.provenance_hash]):
        return "BLOCKED_SOURCE_METADATA"
    return "CLEANED_DRY_RUN"


def qa_report_for(
    product: dict[str, Any],
    source: BatchSourceMetadata,
    rights_report: dict[str, Any],
    ingestion_status: str,
) -> dict[str, Any]:
    warnings: list[str] = []
    blockers: list[str] = []
    if rights_report["rights_status"] in {"BLOCKED", "QUARANTINED", "REGION_GATED_REVIEW"}:
        blockers.extend(rights_report["issues"] or [rights_report["rights_status"]])
    if ingestion_status != "CLEANED_DRY_RUN":
        blockers.append(f"Ingestion not ready: {ingestion_status}")
    if not source.provenance_hash:
        blockers.append("Missing provenance hash.")
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
    ingestion_status: str,
    qa_report: dict[str, Any],
    audio_preview: dict[str, Any],
) -> float:
    score = 40.0 + min(30.0, demand_score * 0.3)
    if rights_report["rights_status"] == "APPROVED":
        score += 15
    elif rights_report["rights_status"] == "REGION_GATED_APPROVED":
        score += 9
    if ingestion_status == "CLEANED_DRY_RUN":
        score += 8
    if qa_report["qa_status"] == "QA_PASSED_DRY_RUN":
        score += 7
    if audio_preview["status"] in {"PREVIEW_PLAN_READY_DRY_RUN", "AUDIO_NOT_REQUIRED", "SKIPPED_PROVIDER_NOT_CONFIGURED"}:
        score += 3
    if qa_report["blocking_reasons"]:
        score -= 35
    return max(0, min(100, score))


def readiness_status(score: float, rights_report: dict[str, Any], blocked_reasons: list[str]) -> str:
    if blocked_reasons:
        return "QUARANTINED_DRY_RUN"
    if rights_report["rights_status"] == "REGION_GATED_APPROVED":
        return "REGION_GATED_DRAFT_REVIEW"
    if score >= 80:
        return "READY_FOR_PUBLICATION_DRAFT"
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
            "demand_score",
            "ingestion_status",
            "qa_status",
            "publication_readiness_score",
            "publication_readiness_status",
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
                "demand_score": row["demand_score"]["demand_score"],
                "ingestion_status": row["ingestion_status"],
                "qa_status": row["qa_report"]["qa_status"],
                "publication_readiness_score": row["publication_readiness_score"],
                "publication_readiness_status": row["publication_readiness_status"],
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
        f"- Blocked or quarantined: `{data['summary']['blocked_or_quarantined']}`",
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
                f"- Demand score: `{product['demand_score']['demand_score']}`",
                f"- Ingestion: `{product['ingestion_status']}`",
                f"- QA: `{product['qa_report']['qa_status']}`",
                f"- Readiness score: `{product['publication_readiness_score']}`",
                f"- Readiness status: `{product['publication_readiness_status']}`",
                f"- Audio preview: `{product['audio_preview']['status']}`",
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


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def text(value: Any) -> str:
    return str(value or "").strip()


def float_or_zero(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
