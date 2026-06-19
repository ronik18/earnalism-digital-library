from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


PUBLISHING_WORKFLOW_VERSION = "earnalism-publishing-workflow-v1"

WORKFLOW_STATES = [
    "DISCOVERED",
    "RIGHTS_PENDING",
    "RIGHTS_APPROVED",
    "DEMAND_SCORED",
    "INGESTED",
    "CLEANED",
    "EDITION_GENERATED",
    "VISUALS_GENERATED",
    "AUDIO_PREVIEW_GENERATED",
    "QA_PENDING",
    "QA_PASSED",
    "READY_FOR_PUBLICATION",
    "PUBLISHED",
    "PAUSED",
    "QUARANTINED",
    "ARCHIVED",
]

TERMINAL_STATES = {"PUBLISHED", "PAUSED", "QUARANTINED", "ARCHIVED"}
ALLOWED_INGESTION_STATUSES = {"INGESTED", "CLEANED"}
ALLOWED_EDITION_STATUSES = {"READY_FOR_REVIEW", "PARTIAL_DRY_RUN", "QA_PASSED"}
ALLOWED_VISUAL_STATUSES = {"READY_FOR_REVIEW", "PARTIAL_DRY_RUN", "QA_PASSED"}
ALLOWED_AUDIO_STATUSES = {"DRY_RUN_READY", "READY_FOR_REVIEW", "QA_PASSED", "AUDIO_NOT_REQUIRED"}


@dataclass
class WorkflowSignals:
    slug: str
    title: str
    rights_tier: str = ""
    verification_status: str = ""
    blocked_reason: str = ""
    publication_region: str = "global"
    demand_score: float = 0.0
    action_status: str = ""
    ingestion_status: str = ""
    edition_generation_status: str = ""
    visual_status: str = ""
    audio_status: str = ""
    qa_status: str = ""
    qa_warnings: list[str] = field(default_factory=list)
    cost_used: float = 0.0
    cost_budget: float = 0.0
    is_published: bool = False
    paused: bool = False
    quarantined: bool = False
    archived: bool = False
    current_state: str = ""


@dataclass
class WorkflowDecision:
    state: str
    publish_readiness: str
    blockers: list[str]
    warnings: list[str]
    rollback_available: bool
    pause_available: bool
    dry_run: bool = True


@dataclass
class DryRunPublicationPlan:
    slug: str
    state: str
    created_drafts: list[dict[str, Any]]
    audit_log: list[dict[str, Any]]
    rollback_plan: list[str]
    public_exposure: bool = False
    dry_run: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "state": self.state,
            "created_drafts": self.created_drafts,
            "audit_log": self.audit_log,
            "rollback_plan": self.rollback_plan,
            "public_exposure": self.public_exposure,
            "dry_run": self.dry_run,
        }


def workflow_signals_from_book(book: dict[str, Any]) -> WorkflowSignals:
    rights = book.get("rights_metadata") if isinstance(book.get("rights_metadata"), dict) else {}
    workflow = book.get("publishing_workflow") if isinstance(book.get("publishing_workflow"), dict) else {}
    demand = book.get("demand") if isinstance(book.get("demand"), dict) else {}
    qa = book.get("qa") if isinstance(book.get("qa"), dict) else {}
    cost = book.get("cost") if isinstance(book.get("cost"), dict) else {}
    return WorkflowSignals(
        slug=text(book.get("slug") or rights.get("work_slug") or workflow.get("slug")),
        title=text(book.get("title") or rights.get("work_title") or workflow.get("title")),
        rights_tier=normalize_tier(rights.get("rights_tier") or book.get("rights_tier")),
        verification_status=normalize_status(rights.get("verification_status") or book.get("verification_status")),
        blocked_reason=text(rights.get("blocked_reason") or book.get("blocked_reason")),
        publication_region=text(rights.get("publication_region") or book.get("publication_region") or "global").lower(),
        demand_score=float_or_zero(demand.get("demand_score") or book.get("demand_score")),
        action_status=normalize_status(demand.get("action_status") or book.get("action_status")),
        ingestion_status=normalize_status(book.get("ingestion_status") or workflow.get("ingestion_status")),
        edition_generation_status=normalize_status(
            book.get("edition_generation_status") or workflow.get("edition_generation_status")
        ),
        visual_status=normalize_status(book.get("visual_status") or workflow.get("visual_status")),
        audio_status=normalize_status(book.get("audio_status") or workflow.get("audio_status")),
        qa_status=normalize_status(qa.get("qa_status") or book.get("qa_status")),
        qa_warnings=list(qa.get("warnings") or book.get("qa_warnings") or []),
        cost_used=float_or_zero(cost.get("used") or book.get("cost_used")),
        cost_budget=float_or_zero(cost.get("budget") or book.get("cost_budget")),
        is_published=bool(book.get("is_published")),
        paused=bool(workflow.get("paused") or book.get("paused")),
        quarantined=bool(workflow.get("quarantined") or book.get("quarantined")),
        archived=bool(workflow.get("archived") or book.get("archived")),
        current_state=normalize_status(workflow.get("state") or book.get("workflow_state")),
    )


def evaluate_workflow(signals: WorkflowSignals) -> WorkflowDecision:
    signals = normalize_workflow_signals(signals)
    blockers = publishing_blockers(signals)
    warnings = list(signals.qa_warnings)
    state = determine_state(signals, blockers)
    publish_readiness = "READY" if state == "READY_FOR_PUBLICATION" and not blockers else "BLOCKED"
    if any("REGION_GATED_REVIEW" in blocker for blocker in blockers):
        publish_readiness = "REGION_GATED_REVIEW"
    if state == "PUBLISHED":
        publish_readiness = "PUBLISHED"
    if state in {"PAUSED", "QUARANTINED", "ARCHIVED"}:
        publish_readiness = state
    return WorkflowDecision(
        state=state,
        publish_readiness=publish_readiness,
        blockers=blockers,
        warnings=warnings,
        rollback_available=state in {"READY_FOR_PUBLICATION", "PUBLISHED", "PAUSED"},
        pause_available=state not in {"ARCHIVED", "QUARANTINED"},
        dry_run=True,
    )


def normalize_workflow_signals(signals: WorkflowSignals) -> WorkflowSignals:
    return WorkflowSignals(
        slug=signals.slug,
        title=signals.title,
        rights_tier=normalize_tier(signals.rights_tier),
        verification_status=normalize_status(signals.verification_status),
        blocked_reason=text(signals.blocked_reason),
        publication_region=text(signals.publication_region or "global").lower(),
        demand_score=float_or_zero(signals.demand_score),
        action_status=normalize_status(signals.action_status),
        ingestion_status=normalize_status(signals.ingestion_status),
        edition_generation_status=normalize_status(signals.edition_generation_status),
        visual_status=normalize_status(signals.visual_status),
        audio_status=normalize_status(signals.audio_status),
        qa_status=normalize_status(signals.qa_status),
        qa_warnings=list(signals.qa_warnings),
        cost_used=float_or_zero(signals.cost_used),
        cost_budget=float_or_zero(signals.cost_budget),
        is_published=bool(signals.is_published),
        paused=bool(signals.paused),
        quarantined=bool(signals.quarantined),
        archived=bool(signals.archived),
        current_state=normalize_status(signals.current_state),
    )


def determine_state(signals: WorkflowSignals, blockers: list[str]) -> str:
    if signals.archived:
        return "ARCHIVED"
    if signals.quarantined or signals.blocked_reason or signals.rights_tier == "C":
        return "QUARANTINED"
    if signals.paused:
        return "PAUSED"
    if signals.is_published:
        return "PUBLISHED"
    if blockers:
        if any("rights" in blocker.lower() or "tier" in blocker.lower() for blocker in blockers):
            return "RIGHTS_PENDING"
        if any("priority" in blocker.lower() for blocker in blockers):
            return "DEMAND_SCORED"
        if any("ingestion" in blocker.lower() for blocker in blockers):
            return "INGESTED" if signals.ingestion_status == "INGESTED" else "RIGHTS_APPROVED"
        if any("edition" in blocker.lower() for blocker in blockers):
            return "CLEANED"
        if any("visual" in blocker.lower() for blocker in blockers):
            return "EDITION_GENERATED"
        if any("audio" in blocker.lower() for blocker in blockers):
            return "VISUALS_GENERATED"
        if any("cost" in blocker.lower() for blocker in blockers):
            return "QA_PENDING"
        if any("qa" in blocker.lower() for blocker in blockers):
            return "QA_PENDING"
    if signals.qa_status == "QA_PASSED":
        return "READY_FOR_PUBLICATION"
    if signals.qa_status:
        return "QA_PENDING"
    if signals.audio_status in ALLOWED_AUDIO_STATUSES:
        return "AUDIO_PREVIEW_GENERATED"
    if signals.visual_status in ALLOWED_VISUAL_STATUSES:
        return "VISUALS_GENERATED"
    if signals.edition_generation_status in ALLOWED_EDITION_STATUSES:
        return "EDITION_GENERATED"
    if signals.ingestion_status == "CLEANED":
        return "CLEANED"
    if signals.ingestion_status == "INGESTED":
        return "INGESTED"
    if signals.action_status:
        return "DEMAND_SCORED"
    if signals.rights_tier == "A" and signals.verification_status in {"APPROVED", "VERIFIED"}:
        return "RIGHTS_APPROVED"
    if signals.slug or signals.title:
        return "DISCOVERED"
    return "DISCOVERED"


def publishing_blockers(signals: WorkflowSignals) -> list[str]:
    blockers: list[str] = []
    if signals.rights_tier == "C":
        blockers.append("BLOCKED_RIGHTS: Tier C cannot publish anywhere.")
    if signals.rights_tier == "B":
        blockers.append("REGION_GATED_REVIEW: Tier B is not eligible for normal global publication.")
    if signals.rights_tier not in {"A", "B", "C"}:
        blockers.append("Rights approval is required.")
    if signals.rights_tier == "A" and signals.verification_status != "APPROVED":
        blockers.append("Rights verification must be approved.")
    if signals.blocked_reason:
        blockers.append(f"Rights blocked_reason must be cleared: {signals.blocked_reason}")
    if signals.action_status != "READY_FOR_GENERATION":
        blockers.append("BLOCKED_PRIORITY_GATE: Phase 3 action_status must be READY_FOR_GENERATION.")
    if signals.ingestion_status not in ALLOWED_INGESTION_STATUSES:
        blockers.append("BLOCKED_INGESTION: Phase 4 ingestion_status must be INGESTED or CLEANED.")
    if signals.edition_generation_status not in ALLOWED_EDITION_STATUSES:
        blockers.append("BLOCKED_EDITION_GATE: Phase 5 edition_generation_status must be ready, partial dry-run, or QA passed.")
    if signals.visual_status not in ALLOWED_VISUAL_STATUSES:
        blockers.append("BLOCKED_VISUAL_GATE: Phase 6 visual_status must be ready, partial dry-run, or QA passed.")
    if signals.audio_status not in ALLOWED_AUDIO_STATUSES:
        blockers.append("BLOCKED_AUDIO_GATE: Phase 7 audio_status must be ready, QA passed, or AUDIO_NOT_REQUIRED.")
    if signals.qa_status != "QA_PASSED":
        blockers.append("QA pass is required.")
    if signals.cost_budget > 0 and signals.cost_used > signals.cost_budget:
        blockers.append("BLOCKED_COST: Cost budget is exceeded.")
    return blockers


def build_admin_dashboard_sections(signals: WorkflowSignals, decision: WorkflowDecision) -> list[dict[str, Any]]:
    return [
        {"section": "rights status", "value": signals.rights_tier or "unknown", "status": signals.verification_status},
        {"section": "demand score", "value": round(signals.demand_score, 2), "status": signals.action_status},
        {"section": "ingestion status", "value": signals.ingestion_status or "missing", "status": signals.ingestion_status},
        {
            "section": "edition generation status",
            "value": signals.edition_generation_status or "missing",
            "status": signals.edition_generation_status,
        },
        {"section": "visual status", "value": signals.visual_status or "missing", "status": signals.visual_status},
        {"section": "audio status", "value": signals.audio_status or "missing", "status": signals.audio_status},
        {"section": "QA warnings", "value": signals.qa_warnings, "status": signals.qa_status or "missing"},
        {
            "section": "cost used",
            "value": {"used": signals.cost_used, "budget": signals.cost_budget},
            "status": "OVER_BUDGET" if signals.cost_budget > 0 and signals.cost_used > signals.cost_budget else "OK",
        },
        {"section": "publish readiness", "value": decision.publish_readiness, "status": decision.state},
        {"section": "rollback button", "value": decision.rollback_available, "status": "DRY_RUN_ONLY"},
        {"section": "pause/kill switch", "value": decision.pause_available, "status": "DRY_RUN_ONLY"},
    ]


def dry_run_publish(signals: WorkflowSignals) -> DryRunPublicationPlan:
    decision = evaluate_workflow(signals)
    if decision.publish_readiness != "READY":
        return DryRunPublicationPlan(
            slug=signals.slug,
            state=decision.state,
            created_drafts=[],
            audit_log=[audit_event("DRY_RUN_PUBLISH_BLOCKED", signals, {"blockers": decision.blockers})],
            rollback_plan=["No drafts created; resolve blockers and rerun dry-run."],
        )
    created_drafts = [
        {"draft_type": "page", "slug": signals.slug, "public": False},
        {"draft_type": "seo_metadata", "slug": signals.slug, "public": False},
        {"draft_type": "reading_challenge", "slug": signals.slug, "public": False},
    ]
    return DryRunPublicationPlan(
        slug=signals.slug,
        state=decision.state,
        created_drafts=created_drafts,
        audit_log=[audit_event("DRY_RUN_PUBLISH_DRAFTS_CREATED", signals, {"draft_count": len(created_drafts)})],
        rollback_plan=[
            f"Delete draft page for {signals.slug}.",
            f"Delete SEO metadata draft for {signals.slug}.",
            f"Delete reading challenge draft for {signals.slug}.",
            "Keep audit log entry for traceability.",
        ],
    )


def workflow_report_json(book: dict[str, Any]) -> dict[str, Any]:
    signals = workflow_signals_from_book(book)
    decision = evaluate_workflow(signals)
    dry_run = dry_run_publish(signals)
    return {
        "workflow_version": PUBLISHING_WORKFLOW_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "slug": signals.slug,
        "title": signals.title,
        "state": decision.state,
        "publish_readiness": decision.publish_readiness,
        "blockers": decision.blockers,
        "warnings": decision.warnings,
        "dashboard_sections": build_admin_dashboard_sections(signals, decision),
        "dry_run_publication": dry_run.as_dict(),
        "dry_run": True,
    }


def workflow_report_csv(report: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["slug", "title", "state", "publish_readiness", "blockers", "dry_run", "draft_count"],
    )
    writer.writeheader()
    writer.writerow(
        {
            "slug": report["slug"],
            "title": report["title"],
            "state": report["state"],
            "publish_readiness": report["publish_readiness"],
            "blockers": " | ".join(report["blockers"]),
            "dry_run": report["dry_run"],
            "draft_count": len(report["dry_run_publication"]["created_drafts"]),
        }
    )
    return output.getvalue()


def workflow_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Publishing Workflow Dry-Run Report",
        "",
        f"- Book: `{report['slug']}` - {report['title']}",
        f"- State: `{report['state']}`",
        f"- Publish readiness: `{report['publish_readiness']}`",
        f"- Dry run: `{str(report['dry_run']).lower()}`",
        "",
        "## Dashboard Sections",
    ]
    for section in report["dashboard_sections"]:
        lines.append(f"- {section['section']}: `{section['status']}`")
    lines.extend(["", "## Blockers"])
    lines.extend(f"- {blocker}" for blocker in report["blockers"]) if report["blockers"] else lines.append("- none")
    lines.extend(["", "## Rollback Plan"])
    lines.extend(f"- {step}" for step in report["dry_run_publication"]["rollback_plan"])
    return "\n".join(lines) + "\n"


def audit_event(action: str, signals: WorkflowSignals, metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": action,
        "slug": signals.slug,
        "state": signals.current_state or determine_state(signals, publishing_blockers(signals)),
        "metadata": metadata,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": True,
    }


def text(value: Any) -> str:
    return str(value or "").strip()


def normalize_tier(value: Any) -> str:
    tier = text(value).upper()
    if tier.startswith("TIER "):
        tier = tier.replace("TIER ", "", 1).strip()
    return tier


def normalize_status(value: Any) -> str:
    return text(value).upper().replace("-", "_").replace(" ", "_")


def float_or_zero(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
