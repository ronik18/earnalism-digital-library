from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Iterable

from backend.demand_scoring import DemandScore, rank_demand, seed_books
from backend.publishing_workflow import evaluate_workflow, workflow_signals_from_book


DAILY_GROWTH_LOOP_VERSION = "earnalism-daily-growth-loop-v1"


@dataclass
class GrowthMetrics:
    paid_readers: int = 0
    reading_starts: int = 0
    reading_completions: int = 0
    preview_listens: int = 0
    referrals: int = 0
    conversion_rate: float = 0.0
    school_institution_leads: int = 0

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "GrowthMetrics":
        payload = payload or {}
        return cls(
            paid_readers=int_or_zero(payload.get("paid_readers")),
            reading_starts=int_or_zero(payload.get("reading_starts")),
            reading_completions=int_or_zero(payload.get("reading_completions")),
            preview_listens=int_or_zero(payload.get("preview_listens")),
            referrals=int_or_zero(payload.get("referrals")),
            conversion_rate=float_or_zero(payload.get("conversion_rate")),
            school_institution_leads=int_or_zero(payload.get("school_institution_leads")),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "paid_readers": self.paid_readers,
            "reading_starts": self.reading_starts,
            "reading_completions": self.reading_completions,
            "preview_listens": self.preview_listens,
            "referrals": self.referrals,
            "conversion_rate": round(self.conversion_rate, 4),
            "school_institution_leads": self.school_institution_leads,
        }


@dataclass
class GrowthBudgets:
    max_daily_llm_budget: float = 0.0
    max_daily_audio_budget: float = 0.0
    max_books_per_day: int = 3
    max_publish_actions_per_day: int = 0

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "GrowthBudgets":
        payload = payload or {}
        return cls(
            max_daily_llm_budget=float_or_zero(payload.get("max_daily_llm_budget")),
            max_daily_audio_budget=float_or_zero(payload.get("max_daily_audio_budget")),
            max_books_per_day=max(0, int_or_zero(payload.get("max_books_per_day"), default=3)),
            max_publish_actions_per_day=max(0, int_or_zero(payload.get("max_publish_actions_per_day"))),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "max_daily_llm_budget": self.max_daily_llm_budget,
            "max_daily_audio_budget": self.max_daily_audio_budget,
            "max_books_per_day": self.max_books_per_day,
            "max_publish_actions_per_day": self.max_publish_actions_per_day,
        }


@dataclass
class GrowthDraft:
    draft_type: str
    slug: str
    title: str
    channel: str
    body_preview: str
    public: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "draft_type": self.draft_type,
            "slug": self.slug,
            "title": self.title,
            "channel": self.channel,
            "body_preview": self.body_preview,
            "public": self.public,
        }


@dataclass
class QueuedTask:
    task_type: str
    slug: str
    title: str
    reason: str
    estimated_llm_cost: float = 0.0
    estimated_audio_cost: float = 0.0
    dry_run: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_type": self.task_type,
            "slug": self.slug,
            "title": self.title,
            "reason": self.reason,
            "estimated_llm_cost": round(self.estimated_llm_cost, 2),
            "estimated_audio_cost": round(self.estimated_audio_cost, 2),
            "dry_run": self.dry_run,
        }


@dataclass
class DailyGrowthReport:
    status: str
    report_date: str
    metrics: GrowthMetrics
    budgets: GrowthBudgets
    demand_scores: list[DemandScore]
    selected_books: list[dict[str, Any]]
    queued_tasks: list[QueuedTask]
    seo_social_email_drafts: list[GrowthDraft]
    reading_challenge_drafts: list[GrowthDraft]
    blocked_items: list[dict[str, Any]]
    budget_usage: dict[str, float]
    catalog_truth: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "workflow_version": DAILY_GROWTH_LOOP_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": self.status,
            "report_date": self.report_date,
            "dry_run": self.dry_run,
            "metrics": self.metrics.as_dict(),
            "budgets": self.budgets.as_dict(),
            "budget_usage": self.budget_usage,
            "catalog_truth": self.catalog_truth,
            "selected_books": self.selected_books,
            "queued_tasks": [task.as_dict() for task in self.queued_tasks],
            "seo_social_email_drafts": [draft.as_dict() for draft in self.seo_social_email_drafts],
            "reading_challenge_drafts": [draft.as_dict() for draft in self.reading_challenge_drafts],
            "blocked_items": self.blocked_items,
            "top_books": [score.as_row() for score in self.demand_scores[:10]],
            "publish_actions_planned": 0,
            "public_publishing_enabled": False,
        }


def run_daily_growth_loop(payload: dict[str, Any] | None = None) -> DailyGrowthReport:
    payload = payload or {}
    report_date = str(payload.get("report_date") or date.today().isoformat())
    metrics = GrowthMetrics.from_dict(payload.get("metrics"))
    budgets = GrowthBudgets.from_dict(payload.get("budgets"))
    books = normalize_books(payload.get("books"))
    books = apply_metrics_to_books(books, payload.get("book_metrics") or {})
    demand_scores = rank_demand(books)
    catalog_truth = dict(payload.get("catalog_truth") or {})

    if payload.get("dry_run") is False:
        return blocked_report(
            status="BLOCKED_NON_DRY_RUN",
            report_date=report_date,
            metrics=metrics,
            budgets=budgets,
            demand_scores=demand_scores,
            reason="Phase 9 daily growth automation is dry-run only.",
        )

    if payload.get("emergency_pause") is True:
        return blocked_report(
            status="BLOCKED_EMERGENCY_PAUSE",
            report_date=report_date,
            metrics=metrics,
            budgets=budgets,
            demand_scores=demand_scores,
            reason="Emergency pause enabled",
        )

    selected_scores = demand_scores[: budgets.max_books_per_day]
    by_slug = {str(book.get("slug") or ""): book for book in books}

    queued_tasks: list[QueuedTask] = []
    drafts: list[GrowthDraft] = []
    reading_drafts: list[GrowthDraft] = []
    blocked_items: list[dict[str, Any]] = []
    llm_used = 0.0
    audio_used = 0.0

    if budgets.max_publish_actions_per_day > 0:
        blocked_items.append(
            {
                "slug": "__phase9__",
                "title": "Phase 9 publish action cap",
                "reason": "Public publishing is disabled in Phase 9; publish action cap is ignored.",
            }
        )

    for score in selected_scores:
        book = by_slug.get(score.slug, {"slug": score.slug, "title": score.title})
        workflow = evaluate_workflow(workflow_signals_from_book(book))
        if workflow.publish_readiness not in {"READY", "PUBLISHED"}:
            blocked_items.append(
                {
                    "slug": score.slug,
                    "title": score.title,
                    "reason": "Workflow gates are not ready.",
                    "workflow_state": workflow.state,
                    "publish_readiness": workflow.publish_readiness,
                    "blockers": workflow.blockers,
                }
            )
            continue

        candidate_tasks = planned_tasks_for_score(score)
        for task in candidate_tasks:
            if task.estimated_llm_cost and llm_used + task.estimated_llm_cost > budgets.max_daily_llm_budget:
                blocked_items.append({"slug": score.slug, "title": score.title, "reason": "LLM budget cap reached."})
                continue
            if task.estimated_audio_cost and audio_used + task.estimated_audio_cost > budgets.max_daily_audio_budget:
                blocked_items.append({"slug": score.slug, "title": score.title, "reason": "Audio budget cap reached."})
                continue
            queued_tasks.append(task)
            llm_used += task.estimated_llm_cost
            audio_used += task.estimated_audio_cost

        drafts.extend(prepare_growth_drafts(score))
        reading_drafts.append(
            GrowthDraft(
                draft_type="reading_challenge",
                slug=score.slug,
                title=score.title,
                channel="onsite",
                body_preview=f"Start a 7-day reading challenge for {score.title}.",
            )
        )

    return DailyGrowthReport(
        status="DRY_RUN_READY",
        report_date=report_date,
        metrics=metrics,
        budgets=budgets,
        demand_scores=demand_scores,
        selected_books=[score.as_row() for score in selected_scores],
        queued_tasks=queued_tasks,
        seo_social_email_drafts=drafts,
        reading_challenge_drafts=reading_drafts,
        blocked_items=blocked_items,
        budget_usage={
            "llm_used": round(llm_used, 2),
            "audio_used": round(audio_used, 2),
            "publish_actions_used": 0,
        },
        catalog_truth=catalog_truth,
    )


def blocked_report(
    *,
    status: str,
    report_date: str,
    metrics: GrowthMetrics,
    budgets: GrowthBudgets,
    demand_scores: list[DemandScore],
    reason: str,
) -> DailyGrowthReport:
    return DailyGrowthReport(
        status=status,
        report_date=report_date,
        metrics=metrics,
        budgets=budgets,
        demand_scores=demand_scores,
        selected_books=[],
        queued_tasks=[],
        seo_social_email_drafts=[],
        reading_challenge_drafts=[],
        blocked_items=[
            {
                "slug": "__phase9__",
                "title": "Phase 9 daily growth automation",
                "reason": reason,
            }
        ],
        budget_usage={
            "llm_used": 0.0,
            "audio_used": 0.0,
            "publish_actions_used": 0,
        },
        dry_run=True,
    )


def normalize_books(raw_books: Any) -> list[dict[str, Any]]:
    if isinstance(raw_books, list) and raw_books:
        return [dict(book) for book in raw_books if isinstance(book, dict)]
    return seed_books()


def apply_metrics_to_books(books: list[dict[str, Any]], book_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for book in books:
        copy = dict(book)
        slug = str(copy.get("slug") or "")
        metrics = book_metrics.get(slug) if isinstance(book_metrics, dict) else None
        if isinstance(metrics, dict):
            copy.update(
                {
                    "page_views": metrics.get("page_views", copy.get("page_views", 0)),
                    "reading_starts": metrics.get("reading_starts", copy.get("reading_starts", 0)),
                    "reading_completions": metrics.get("reading_completions", copy.get("reading_completions", 0)),
                }
            )
        enriched.append(copy)
    return enriched


def planned_tasks_for_score(score: DemandScore) -> list[QueuedTask]:
    tasks = [
        QueuedTask(
            task_type="source_ingestion_candidate",
            slug=score.slug,
            title=score.title,
            reason="Metadata-only candidate for Phase 4 source ingestion review.",
        ),
        QueuedTask(
            task_type="edition_generation_candidate",
            slug=score.slug,
            title=score.title,
            reason="Metadata-only candidate for Phase 5 edition generation review.",
            estimated_llm_cost=1.0,
        ),
        QueuedTask(
            task_type="visual_design_candidate",
            slug=score.slug,
            title=score.title,
            reason="Metadata-only candidate for Phase 6 visual design review.",
            estimated_llm_cost=0.75,
        ),
        QueuedTask(
            task_type="seo_social_email_drafts",
            slug=score.slug,
            title=score.title,
            reason=score.growth_rationale or "High growth priority.",
            estimated_llm_cost=0.5,
        ),
        QueuedTask(
            task_type="reading_challenge_draft",
            slug=score.slug,
            title=score.title,
            reason="Prepare lightweight conversion challenge.",
            estimated_llm_cost=0.25,
        ),
        QueuedTask(
            task_type="publishing_workflow_candidate",
            slug=score.slug,
            title=score.title,
            reason="Metadata-only candidate for Phase 8 workflow review.",
        ),
    ]
    if "audiobook" in score.recommended_product_format.lower():
        tasks.append(
            QueuedTask(
                task_type="audio_preview_plan",
                slug=score.slug,
                title=score.title,
                reason="Audiobook potential detected; queue dry-run preview plan only.",
                estimated_audio_cost=1.0,
            )
        )
    return tasks


def prepare_growth_drafts(score: DemandScore) -> list[GrowthDraft]:
    return [
        GrowthDraft(
            draft_type="seo_metadata",
            slug=score.slug,
            title=score.title,
            channel="search",
            body_preview=f"Read {score.title} on Earnalism with guided reading-time access.",
        ),
        GrowthDraft(
            draft_type="social_post",
            slug=score.slug,
            title=score.title,
            channel="social",
            body_preview=f"Rediscover {score.title}: {score.growth_rationale}",
        ),
        GrowthDraft(
            draft_type="email_campaign",
            slug=score.slug,
            title=score.title,
            channel="email",
            body_preview=f"This week in the Earnalism reading room: {score.title}.",
        ),
    ]


def daily_growth_report_json(report: DailyGrowthReport) -> dict[str, Any]:
    return report.as_dict()


def daily_growth_report_csv(report: DailyGrowthReport) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "priority_rank",
            "slug",
            "title",
            "demand_score",
            "action_status",
            "queued_task_count",
            "draft_count",
            "blocked_count",
            "dry_run",
        ],
    )
    writer.writeheader()
    task_counts = count_by_slug([task.as_dict() for task in report.queued_tasks])
    draft_counts = count_by_slug([draft.as_dict() for draft in [*report.seo_social_email_drafts, *report.reading_challenge_drafts]])
    blocked_counts = count_by_slug(report.blocked_items)
    for score in report.demand_scores[:10]:
        writer.writerow(
            {
                "priority_rank": score.priority_rank,
                "slug": score.slug,
                "title": score.title,
                "demand_score": f"{score.demand_score:.2f}",
                "action_status": score.action_status,
                "queued_task_count": task_counts.get(score.slug, 0),
                "draft_count": draft_counts.get(score.slug, 0),
                "blocked_count": blocked_counts.get(score.slug, 0),
                "dry_run": report.dry_run,
            }
        )
    return output.getvalue()


def daily_growth_report_markdown(report: DailyGrowthReport) -> str:
    payload = report.as_dict()
    lines = [
        "# Daily Growth Automation Dry-Run Report",
        "",
        f"- Report date: `{report.report_date}`",
        f"- Dry run: `{str(report.dry_run).lower()}`",
        f"- LLM budget used: `{payload['budget_usage']['llm_used']}/{report.budgets.max_daily_llm_budget}`",
        f"- Audio budget used: `{payload['budget_usage']['audio_used']}/{report.budgets.max_daily_audio_budget}`",
        f"- Queued tasks: `{len(report.queued_tasks)}`",
        f"- Drafts prepared: `{len(report.seo_social_email_drafts) + len(report.reading_challenge_drafts)}`",
        f"- Blocked items: `{len(report.blocked_items)}`",
        "",
        "## Catalog Truth",
        "",
        f"- Backend live approved count: `{payload.get('catalog_truth', {}).get('backend_live_approved_count', 'not_provided')}`",
        f"- Dracula only live: `{payload.get('catalog_truth', {}).get('dracula_only_live_approved', 'not_provided')}`",
        f"- Unapproved reader links: `{payload.get('catalog_truth', {}).get('unapproved_reader_link_count', 'not_provided')}`",
        f"- Unapproved audio links: `{payload.get('catalog_truth', {}).get('unapproved_audio_link_count', 'not_provided')}`",
        "",
        "## Top Books",
    ]
    for item in payload["top_books"][:10]:
        lines.append(f"- {item['priority_rank']}. `{item['slug']}` {item['title']} - {item['demand_score']}")
    lines.extend(["", "## Queued Tasks"])
    if report.queued_tasks:
        lines.extend(f"- `{task.task_type}` for `{task.slug}` ({task.reason})" for task in report.queued_tasks)
    else:
        lines.append("- none")
    lines.extend(["", "## Blocked Items"])
    if report.blocked_items:
        lines.extend(f"- `{item['slug']}`: {item['reason']}" for item in report.blocked_items)
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def count_by_slug(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        slug = str(row.get("slug") or "")
        counts[slug] = counts.get(slug, 0) + 1
    return counts


def int_or_zero(value: Any, *, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def float_or_zero(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
