from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


OBSERVABILITY_VERSION = "earnalism-observability-guardrails-v1"

LOG_CATEGORIES = {
    "rights_check",
    "demand_scoring",
    "ingestion",
    "generation",
    "qa",
    "audio_generation",
    "publishing",
    "failure",
    "guardrail_block",
}

GUARDRAIL_TYPES = {
    "rights_blocked",
    "region_gated",
    "source_missing",
    "traceability_missing",
    "hallucination_risk",
    "unsafe_child_facing_content",
    "copyrighted_image_risk",
    "low_quality_audio",
    "budget_exceeded",
    "kill_switch",
    "feature_flag_disabled",
}

SEVERITY_ORDER = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
HEALTH_CHECKS = ("api", "queue", "storage", "publishing")


@dataclass
class StructuredLogEvent:
    event_id: str
    timestamp: str
    category: str
    phase: str
    action: str
    status: str
    severity: str
    message: str
    slug: str = ""
    guardrail_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "category": self.category,
            "phase": self.phase,
            "action": self.action,
            "status": self.status,
            "severity": self.severity,
            "message": self.message,
            "slug": self.slug,
            "guardrail_type": self.guardrail_type,
            "metadata": self.metadata,
            "dry_run": self.dry_run,
        }


@dataclass
class IncidentRecord:
    incident_id: str
    severity: str
    owner: str
    status: str
    source_event_id: str
    summary: str
    rollback_instruction: str
    kill_switch_active: bool = False
    dry_run: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "severity": self.severity,
            "owner": self.owner,
            "status": self.status,
            "source_event_id": self.source_event_id,
            "summary": self.summary,
            "rollback_instruction": self.rollback_instruction,
            "kill_switch_active": self.kill_switch_active,
            "dry_run": self.dry_run,
        }


@dataclass
class HealthCheckResult:
    name: str
    status: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "metadata": self.metadata,
        }


@dataclass
class ActionDecision:
    action_id: str
    slug: str
    phase: str
    action_type: str
    decision_status: str
    blocking_reasons: list[str]
    audit_events: list[StructuredLogEvent]
    dry_run: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "slug": self.slug,
            "phase": self.phase,
            "action_type": self.action_type,
            "decision_status": self.decision_status,
            "blocking_reasons": self.blocking_reasons,
            "audit_events": [event.as_dict() for event in self.audit_events],
            "dry_run": self.dry_run,
        }


@dataclass
class ObservabilityReport:
    status: str
    actions: list[ActionDecision]
    logs: list[StructuredLogEvent]
    incidents: list[IncidentRecord]
    health_checks: list[HealthCheckResult]
    kill_switch_active: bool
    dry_run: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "observability_version": OBSERVABILITY_VERSION,
            "generated_at": utc_now(),
            "status": self.status,
            "dry_run": self.dry_run,
            "kill_switch_active": self.kill_switch_active,
            "actions": [action.as_dict() for action in self.actions],
            "logs": [event.as_dict() for event in self.logs],
            "incidents": [incident.as_dict() for incident in self.incidents],
            "health_checks": [check.as_dict() for check in self.health_checks],
            "summary": {
                "action_count": len(self.actions),
                "blocked_action_count": sum(1 for action in self.actions if action.decision_status == "BLOCKED"),
                "log_count": len(self.logs),
                "incident_count": len(self.incidents),
                "unhealthy_check_count": sum(1 for check in self.health_checks if check.status != "OK"),
                "guardrail_type_counts": guardrail_type_counts(self.logs),
            },
        }


def run_observability_guardrails(payload: dict[str, Any] | None = None) -> ObservabilityReport:
    payload = payload or {}
    dry_run = payload.get("dry_run", True)
    if dry_run is not True:
        return blocked_non_dry_run_report(payload)

    feature_flags = payload.get("feature_flags") if isinstance(payload.get("feature_flags"), dict) else {}
    automation_enabled = feature_flags.get("automation_enabled", True) is not False
    kill_switch_active = bool(payload.get("kill_switch_active"))
    actions = payload.get("actions") if isinstance(payload.get("actions"), list) else sample_actions()
    decisions: list[ActionDecision] = []
    logs: list[StructuredLogEvent] = []

    for index, raw_action in enumerate(actions):
        action = raw_action if isinstance(raw_action, dict) else {}
        decision = evaluate_action(
            action,
            index=index,
            kill_switch_active=kill_switch_active,
            automation_enabled=automation_enabled,
        )
        decisions.append(decision)
        logs.extend(decision.audit_events)

    health_checks = evaluate_health(payload.get("health"))
    logs.extend(health_logs(health_checks))
    incidents = incidents_from_logs(logs, kill_switch_active=kill_switch_active)
    status = "BLOCKED" if any(decision.decision_status == "BLOCKED" for decision in decisions) else "READY_DRY_RUN"
    if kill_switch_active:
        status = "KILL_SWITCH_ACTIVE"
    if not automation_enabled:
        status = "FEATURE_FLAG_DISABLED"
    if any(check.status == "DOWN" for check in health_checks):
        status = "DEGRADED" if status == "READY_DRY_RUN" else status

    return ObservabilityReport(
        status=status,
        actions=decisions,
        logs=logs,
        incidents=incidents,
        health_checks=health_checks,
        kill_switch_active=kill_switch_active,
    )


def evaluate_action(
    action: dict[str, Any],
    *,
    index: int,
    kill_switch_active: bool,
    automation_enabled: bool = True,
) -> ActionDecision:
    action_id = text(action.get("action_id")) or stable_id("action", index, action)
    slug = text(action.get("slug"))
    phase = text(action.get("phase")) or "unknown"
    action_type = text(action.get("action_type")) or "unknown"
    audit_events = [
        log_event(
            category=category_for_phase(phase),
            phase=phase,
            action=action_type,
            status="EVALUATED",
            severity="INFO",
            message="Automation action evaluated in dry-run observability mode.",
            slug=slug,
            metadata={"action_id": action_id},
        )
    ]
    blocking_reasons: list[str] = []

    for guardrail_type, message, severity in guardrail_findings(
        action,
        kill_switch_active=kill_switch_active,
        automation_enabled=automation_enabled,
    ):
        is_blocking = is_blocking_finding(guardrail_type)
        if is_blocking:
            blocking_reasons.append(message)
        audit_events.append(
            log_event(
                category="guardrail_block",
                phase=phase,
                action=action_type,
                status="BLOCKED" if is_blocking else "NOTED",
                severity=severity,
                message=message,
                slug=slug,
                guardrail_type=guardrail_type,
                metadata={"action_id": action_id},
            )
        )

    decision_status = "BLOCKED" if blocking_reasons else "ALLOWED_DRY_RUN"
    return ActionDecision(
        action_id=action_id,
        slug=slug,
        phase=phase,
        action_type=action_type,
        decision_status=decision_status,
        blocking_reasons=blocking_reasons,
        audit_events=audit_events,
    )


def guardrail_findings(
    action: dict[str, Any],
    *,
    kill_switch_active: bool,
    automation_enabled: bool,
) -> list[tuple[str, str, str]]:
    findings: list[tuple[str, str, str]] = []
    if kill_switch_active:
        findings.append(("kill_switch", "Kill switch is active; all automation actions are blocked.", "CRITICAL"))
    if not automation_enabled:
        findings.append(("feature_flag_disabled", "Automation feature flag is disabled; all actions are blocked.", "CRITICAL"))

    rights = action.get("rights") if isinstance(action.get("rights"), dict) else {}
    rights_tier = text(rights.get("rights_tier") or action.get("rights_tier")).upper()
    verification_status = text(rights.get("verification_status") or action.get("verification_status")).upper()
    blocked_reason = text(rights.get("blocked_reason") or action.get("blocked_reason"))
    publication_region = normalize_region(rights.get("publication_region") or action.get("publication_region"))
    region_gate_acknowledged = bool(rights.get("region_gate_acknowledged") or action.get("region_gate_acknowledged"))
    if rights_tier == "C" or blocked_reason:
        findings.append(("rights_blocked", "Rights blocked; action cannot proceed.", "CRITICAL"))
    elif rights_tier not in {"A", "B", "C"}:
        findings.append(("rights_blocked", "Rights tier is missing or unknown.", "HIGH"))
    elif verification_status not in {"APPROVED", "VERIFIED"}:
        findings.append(("rights_blocked", "Rights approval is missing or incomplete.", "HIGH"))
    elif rights_tier == "B" and not is_india_region(publication_region):
        findings.append(("rights_blocked", "Tier B rights require India-only publication region.", "HIGH"))
    elif rights_tier == "B" and not region_gate_acknowledged:
        findings.append(("rights_blocked", "Tier B rights require region-gate acknowledgement.", "HIGH"))
    elif rights_tier == "B":
        findings.append(("region_gated", "Tier B action is region-gated and requires India-only handling.", "INFO"))

    if action.get("requires_source"):
        for field in ("source_url", "source_name", "source_license"):
            if not text(action.get(field)):
                findings.append(("source_missing", f"{field} is missing for a source-dependent action.", "HIGH"))
        for field in ("source_hash", "content_hash", "provenance_hash"):
            if not text(action.get(field)):
                findings.append(("traceability_missing", f"{field} is missing for a source-dependent action.", "HIGH"))

    if action.get("hallucination_risk") in {True, "high", "HIGH"}:
        findings.append(("hallucination_risk", "Hallucination risk requires editorial review.", "MEDIUM"))

    if action.get("child_facing") and action.get("unsafe_child_facing_content"):
        findings.append(("unsafe_child_facing_content", "Unsafe child-facing content detected.", "HIGH"))

    if action.get("copyrighted_image_risk") or action.get("external_image_dependency"):
        findings.append(("copyrighted_image_risk", "Copyrighted or external image dependency risk detected.", "HIGH"))

    audio_quality_score = float_or_none(action.get("audio_quality_score"))
    if audio_quality_score is not None and audio_quality_score < 9.0:
        findings.append(("low_quality_audio", "Audio quality score is below the publication threshold.", "MEDIUM"))
    if text(action.get("audio_qa_status")).upper() in {"FAILED", "FAILED_QA", "LOW_QUALITY"}:
        findings.append(("low_quality_audio", "Audio QA status blocks action.", "MEDIUM"))

    estimated_cost = float_or_none(action.get("estimated_cost"))
    budget_remaining = float_or_none(action.get("budget_remaining"))
    budget_limit = float_or_none(action.get("budget_limit"))
    budget_used = float_or_none(action.get("budget_used"))
    if estimated_cost is not None and estimated_cost < 0:
        findings.append(("budget_exceeded", "estimated_cost cannot be negative.", "HIGH"))
    if budget_remaining is not None and budget_remaining < 0:
        findings.append(("budget_exceeded", "budget_remaining cannot be negative.", "HIGH"))
    if budget_limit is not None and budget_limit < 0:
        findings.append(("budget_exceeded", "budget_limit cannot be negative.", "HIGH"))
    if budget_used is not None and budget_used < 0:
        findings.append(("budget_exceeded", "budget_used cannot be negative.", "HIGH"))
    normalized_estimated_cost = estimated_cost or 0.0
    normalized_budget_used = budget_used or 0.0
    if normalized_estimated_cost > 0 and budget_remaining is None and budget_limit is None:
        findings.append(("budget_exceeded", "Positive estimated_cost requires budget_remaining or budget_limit.", "HIGH"))
    if budget_remaining is not None and normalized_estimated_cost > budget_remaining:
        findings.append(("budget_exceeded", "Estimated cost exceeds remaining budget.", "HIGH"))
    if budget_limit is not None and normalized_budget_used + normalized_estimated_cost > budget_limit:
        findings.append(("budget_exceeded", "Estimated cost would exceed budget limit.", "HIGH"))

    return findings


def evaluate_health(raw_health: Any) -> list[HealthCheckResult]:
    health = raw_health if isinstance(raw_health, dict) else {}
    checks: list[HealthCheckResult] = []
    for name in HEALTH_CHECKS:
        payload = health.get(name) if isinstance(health.get(name), dict) else {}
        status = text(payload.get("status") or "OK").upper()
        if status not in {"OK", "DEGRADED", "DOWN"}:
            status = "DEGRADED"
        checks.append(
            HealthCheckResult(
                name=name,
                status=status,
                message=text(payload.get("message")) or default_health_message(name, status),
                metadata={key: value for key, value in payload.items() if key not in {"status", "message"}},
            )
        )
    return checks


def health_logs(health_checks: list[HealthCheckResult]) -> list[StructuredLogEvent]:
    events: list[StructuredLogEvent] = []
    for check in health_checks:
        severity = "INFO" if check.status == "OK" else "HIGH" if check.status == "DOWN" else "MEDIUM"
        events.append(
            log_event(
                category="failure" if check.status != "OK" else "publishing",
                phase="health_check",
                action=f"{check.name}_health",
                status=check.status,
                severity=severity,
                message=check.message,
                metadata=check.metadata,
            )
        )
    return events


def incidents_from_logs(logs: list[StructuredLogEvent], *, kill_switch_active: bool) -> list[IncidentRecord]:
    incidents: list[IncidentRecord] = []
    for event in logs:
        if SEVERITY_ORDER.get(event.severity, 0) < SEVERITY_ORDER["HIGH"]:
            continue
        incidents.append(
            IncidentRecord(
                incident_id=stable_id("incident", len(incidents), event.as_dict()),
                severity=event.severity,
                owner=owner_for_event(event),
                status="OPEN",
                source_event_id=event.event_id,
                summary=event.message,
                rollback_instruction=rollback_instruction_for_event(event),
                kill_switch_active=kill_switch_active or event.guardrail_type == "kill_switch",
            )
        )
    return incidents


def blocked_non_dry_run_report(payload: dict[str, Any]) -> ObservabilityReport:
    event = log_event(
        category="guardrail_block",
        phase="observability",
        action="run_observability_guardrails",
        status="BLOCKED",
        severity="CRITICAL",
        message="Phase 10 observability guardrails are dry-run only.",
        guardrail_type="kill_switch",
        metadata={"requested_dry_run": payload.get("dry_run")},
    )
    incident = IncidentRecord(
        incident_id=stable_id("incident", 0, event.as_dict()),
        severity="CRITICAL",
        owner="platform",
        status="OPEN",
        source_event_id=event.event_id,
        summary=event.message,
        rollback_instruction="Stop the non-dry-run invocation and rerun with dry_run=true.",
        kill_switch_active=True,
    )
    return ObservabilityReport(
        status="BLOCKED_NON_DRY_RUN",
        actions=[],
        logs=[event],
        incidents=[incident],
        health_checks=evaluate_health(payload.get("health")),
        kill_switch_active=True,
    )


def log_event(
    *,
    category: str,
    phase: str,
    action: str,
    status: str,
    severity: str,
    message: str,
    slug: str = "",
    guardrail_type: str = "",
    metadata: dict[str, Any] | None = None,
) -> StructuredLogEvent:
    safe_category = category if category in LOG_CATEGORIES else "failure"
    safe_guardrail = guardrail_type if not guardrail_type or guardrail_type in GUARDRAIL_TYPES else "guardrail_block"
    payload = {
        "category": safe_category,
        "phase": phase,
        "action": action,
        "status": status,
        "severity": severity,
        "message": message,
        "slug": slug,
        "guardrail_type": safe_guardrail,
        "metadata": metadata or {},
    }
    return StructuredLogEvent(
        event_id=stable_id("event", 0, payload),
        timestamp=utc_now(),
        category=safe_category,
        phase=phase,
        action=action,
        status=status,
        severity=severity,
        message=message,
        slug=slug,
        guardrail_type=safe_guardrail,
        metadata=metadata or {},
    )


def observability_report_json(report: ObservabilityReport) -> dict[str, Any]:
    return report.as_dict()


def observability_logs_csv(report: ObservabilityReport) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "event_id",
            "category",
            "phase",
            "action",
            "status",
            "severity",
            "slug",
            "guardrail_type",
            "message",
            "dry_run",
        ],
    )
    writer.writeheader()
    for event in report.logs:
        row = event.as_dict()
        writer.writerow({key: row.get(key, "") for key in writer.fieldnames or []})
    return output.getvalue()


def incident_report_csv(report: ObservabilityReport) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "incident_id",
            "severity",
            "owner",
            "status",
            "source_event_id",
            "summary",
            "rollback_instruction",
            "kill_switch_active",
            "dry_run",
        ],
    )
    writer.writeheader()
    for incident in report.incidents:
        writer.writerow(incident.as_dict())
    return output.getvalue()


def structured_logs_json(report: ObservabilityReport) -> list[dict[str, Any]]:
    return [event.as_dict() for event in report.logs]


def observability_report_markdown(report: ObservabilityReport) -> str:
    payload = report.as_dict()
    lines = [
        "# Observability Guardrails Dry-Run Report",
        "",
        f"- Status: `{report.status}`",
        f"- Dry run: `{str(report.dry_run).lower()}`",
        f"- Kill switch active: `{str(report.kill_switch_active).lower()}`",
        f"- Actions evaluated: `{payload['summary']['action_count']}`",
        f"- Actions blocked: `{payload['summary']['blocked_action_count']}`",
        f"- Incidents opened: `{payload['summary']['incident_count']}`",
        "",
        "## Health Checks",
    ]
    for check in report.health_checks:
        lines.append(f"- `{check.name}`: `{check.status}` - {check.message}")
    lines.extend(["", "## Incidents"])
    if report.incidents:
        for incident in report.incidents:
            lines.append(f"- `{incident.severity}` `{incident.incident_id}`: {incident.summary}")
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def sample_actions() -> list[dict[str, Any]]:
    return [
        {
            "action_id": "phase10-ready-rights-check",
            "slug": "dracula",
            "phase": "rights",
            "action_type": "rights_check",
            "rights": {"rights_tier": "A", "verification_status": "approved", "blocked_reason": ""},
            "requires_source": True,
            "source_url": "https://example.invalid/source/dracula",
            "source_name": "Local public-domain fixture",
            "source_license": "public-domain",
            "source_hash": "sha256:dracula",
            "content_hash": "sha256:dracula-content",
            "provenance_hash": "sha256:dracula-provenance",
            "estimated_cost": 0,
            "budget_remaining": 10,
        },
        {
            "action_id": "phase10-budget-block",
            "slug": "audio-preview",
            "phase": "audio_generation",
            "action_type": "audio_preview_plan",
            "rights": {"rights_tier": "A", "verification_status": "approved", "blocked_reason": ""},
            "audio_quality_score": 8.2,
            "estimated_cost": 7,
            "budget_remaining": 3,
        },
        {
            "action_id": "phase10-rights-block",
            "slug": "unsafe-modern-edition",
            "phase": "publishing",
            "action_type": "publish_candidate",
            "rights": {"rights_tier": "C", "verification_status": "blocked", "blocked_reason": "Unsafe rights."},
            "estimated_cost": 0,
            "budget_remaining": 1,
        },
    ]


def category_for_phase(phase: str) -> str:
    normalized = phase.lower().replace("-", "_")
    mapping = {
        "public_content_governance": "publishing",
        "rights": "rights_check",
        "rights_check": "rights_check",
        "rights_verification": "rights_check",
        "demand": "demand_scoring",
        "demand_scoring": "demand_scoring",
        "source_ingestion": "ingestion",
        "ingestion": "ingestion",
        "edition_generation": "generation",
        "visual_generation": "generation",
        "generation": "generation",
        "qa": "qa",
        "audio": "audio_generation",
        "audio_generation": "audio_generation",
        "publishing": "publishing",
        "publishing_workflow": "publishing",
        "daily_growth_loop": "demand_scoring",
    }
    return mapping.get(normalized, "failure")


def owner_for_event(event: StructuredLogEvent) -> str:
    if event.guardrail_type == "rights_blocked":
        return "rights"
    if event.guardrail_type == "budget_exceeded":
        return "growth"
    if event.guardrail_type == "feature_flag_disabled":
        return "platform"
    if event.phase == "health_check":
        return "platform"
    if event.guardrail_type == "low_quality_audio":
        return "audio"
    return "platform"


def rollback_instruction_for_event(event: StructuredLogEvent) -> str:
    if event.guardrail_type == "budget_exceeded":
        return "Keep action blocked, reduce daily queue, or increase approved dry-run budget before retry."
    if event.guardrail_type == "rights_blocked":
        return "Keep content unpublished and rerun Phase 2 rights verification before retry."
    if event.guardrail_type == "kill_switch":
        return "Keep automation paused until owner clears the kill switch."
    if event.guardrail_type == "feature_flag_disabled":
        return "Keep automation disabled until an owner explicitly reenables the feature flag."
    if event.phase == "health_check":
        return "Keep automation paused for affected subsystem and rerun health checks after repair."
    return "Keep action blocked, resolve guardrail finding, then rerun dry-run."


def default_health_message(name: str, status: str) -> str:
    if status == "OK":
        return f"{name} health check passed."
    if status == "DOWN":
        return f"{name} health check is down."
    return f"{name} health check is degraded."


def stable_id(prefix: str, index: int, payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=True)
    digest = hashlib.sha256(f"{index}:{encoded}".encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def text(value: Any) -> str:
    return str(value or "").strip()


def normalize_region(value: Any) -> str:
    return text(value).lower().replace("_", "-")


def is_india_region(value: str) -> bool:
    return value in {"in", "india", "india-only", "in-only", "region-gated-india"}


def is_blocking_finding(guardrail_type: str) -> bool:
    return guardrail_type != "region_gated"


def guardrail_type_counts(logs: list[StructuredLogEvent]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in logs:
        if event.guardrail_type:
            counts[event.guardrail_type] = counts.get(event.guardrail_type, 0) + 1
    return counts


def float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
