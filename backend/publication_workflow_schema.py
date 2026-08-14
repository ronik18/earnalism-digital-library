"""Versioned, canonical publication-workflow normalization.

The adapter is deliberately dual-read: existing records remain readable while
the canonical nested object becomes the only shape consumed by gates.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any


SCHEMA_VERSION = 2
SCHEMA_NAME = "earnalism-publication-workflow"

_FIELD_SPECS = {
    "rights.tier": ("rights_metadata.rights_tier", "rights_tier"),
    "rights.verification_status": ("rights_metadata.verification_status", "verification_status"),
    "rights.publication_region": ("rights_metadata.publication_region", "publication_region"),
    "rights.blocked_reason": ("rights_metadata.blocked_reason", "blocked_reason"),
    "demand.score": ("demand.demand_score", "demand_score"),
    "demand.action_status": ("demand.action_status", "action_status"),
    "ingestion.status": ("ingestion_status", "publishing_workflow.ingestion_status"),
    "edition.status": ("edition_generation_status", "publishing_workflow.edition_generation_status"),
    "visual.status": ("visual_status", "publishing_workflow.visual_status"),
    "audio.status": ("audio_status", "publishing_workflow.audio_status"),
    "qa.status": ("qa.qa_status", "qa_status"),
    "qa.warnings": ("qa.warnings", "qa_warnings"),
    "publication.reader_exposed": ("reader_exposed", "is_public", "isPublic", "isLive"),
    "publication.audio_exposed": ("audio_exposed",),
    "audio.release_status": ("audio_release_status", "audio_public_release", "public_audio_release"),
    "audio.qa_status": ("audio_qa_status",),
    "audio.sidecars_complete": ("sidecars_complete", "audio_sidecars_complete"),
    "audio.synchronization_verified": ("synchronization_verified", "audio_synchronization_verified"),
    "audio.checksum_verified": ("checksum_verified", "audio_checksum_verified"),
    "audio.endpoint_verified": ("endpoint_verified", "audio_endpoint_verified"),
    "cost.used": ("cost.used", "cost_used"),
    "cost.budget": ("cost.budget", "cost_budget"),
}


@dataclass(frozen=True)
class MigrationResult:
    workflow: dict[str, Any]
    conflicts: list[dict[str, Any]]
    changed: bool
    audit_event: dict[str, Any]


def _get(mapping: dict[str, Any], path: str) -> Any:
    value: Any = mapping
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _present(value: Any) -> bool:
    return value is not None and value != "" and value != []


def _norm(path: str, value: Any) -> Any:
    if not _present(value):
        return None
    if path.endswith(("tier", "status")):
        return str(value).strip().upper().replace("-", "_").replace(" ", "_")
    if path.endswith("region") or path.endswith("reason"):
        return str(value).strip()
    if path.endswith("score") or path.endswith("used") or path.endswith("budget"):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    if path.endswith("warnings"):
        return list(value) if isinstance(value, list) else [str(value)]
    return value


def _set(mapping: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    target = mapping
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = value


def derive_minimal_release(workflow: dict[str, Any]) -> dict[str, str]:
    """Return the four canonical release decisions.

    Exposure and publish readiness are projections, not independent stored
    decisions. Evidence remains in the detailed sections and audit records.
    """
    rights = workflow.get("rights") if isinstance(workflow.get("rights"), dict) else {}
    ingestion = workflow.get("ingestion") if isinstance(workflow.get("ingestion"), dict) else {}
    audio = workflow.get("audio") if isinstance(workflow.get("audio"), dict) else {}
    publication = workflow.get("publication") if isinstance(workflow.get("publication"), dict) else {}
    rights_status = "APPROVED" if (
        rights.get("tier") == "A" and rights.get("verification_status") == "APPROVED"
    ) else str(rights.get("verification_status") or "UNKNOWN")
    content_status = str(ingestion.get("status") or "MISSING")
    reader_release = "LIVE" if publication.get("reader_exposed") is True else "DRAFT"
    if publication.get("audio_exposed") is True:
        audio_release = "LIVE"
    else:
        audio_release = str(audio.get("release_status") or "").strip().upper()
        if not audio_release:
            audio_status = str(audio.get("status") or "").strip().upper()
            if audio_status == "AUDIO_NOT_REQUIRED":
                audio_release = "NOT_REQUESTED"
            elif audio_status:
                audio_release = "IN_PROGRESS"
            else:
                audio_release = ""
    return {
        "rights_status": rights_status,
        "content_status": content_status,
        "reader_release": reader_release,
        "audio_release": audio_release,
    }


def _source_record(source: str, payload: dict[str, Any], path: str) -> tuple[str, Any] | None:
    value = _get(payload, path)
    value = _norm(path, value)
    return (source, value) if _present(value) else None


def normalize_publication_workflow(
    book: dict[str, Any],
    *,
    approved_artifact: dict[str, Any] | None = None,
    release_evidence: dict[str, Any] | None = None,
) -> MigrationResult:
    """Build a canonical workflow without deleting legacy fields.

    Stronger evidence wins in this order: approved artifact, release evidence,
    existing canonical/current record, then legacy aliases.
    """
    current = book.get("publication_workflow") if isinstance(book.get("publication_workflow"), dict) else {}
    sources = [
        ("approved_controlled_publication", approved_artifact or {}),
        ("authoritative_release_evidence", release_evidence or {}),
        ("canonical_record", current),
        ("current_record", book),
    ]
    workflow: dict[str, Any] = {"schema_name": SCHEMA_NAME, "schema_version": SCHEMA_VERSION}
    conflicts: list[dict[str, Any]] = []
    for field, aliases in _FIELD_SPECS.items():
        candidates: list[tuple[str, Any]] = []
        for source, payload in sources:
            for path in (field, *aliases):
                record = _source_record(source, payload, path)
                if record and all(existing[1] != record[1] for existing in candidates):
                    candidates.append(record)
                    break
        if not candidates:
            continue
        winner_source, winner = candidates[0]
        _set(workflow, field, winner)
        if len(candidates) > 1:
            conflicts.append({
                "field": field,
                "winner": {"source": winner_source, "value": winner},
                "alternatives": [{"source": s, "value": v} for s, v in candidates[1:]],
            })

    publication = current.get("publication") if isinstance(current.get("publication"), dict) else {}
    if isinstance(approved_artifact, dict):
        publication = {**publication, **(approved_artifact.get("publication") or {})}
    explicit_reader = None
    for path in ("publication.reader_exposed", "reader_exposed", "is_public", "isPublic", "isLive"):
        explicit_reader = _source_record("approved_controlled_publication", approved_artifact or {}, path)
        if explicit_reader:
            break
    explicit_audio = _source_record("authoritative_release_evidence", release_evidence or {}, "publication.audio_exposed") or _source_record("authoritative_release_evidence", release_evidence or {}, "audio_exposed")
    workflow["publication"] = {
        "state": str(publication.get("state") or ("PUBLISHED" if book.get("is_published") else "")),
        "published_at": publication.get("published_at", ""),
        "publication_version": publication.get("publication_version", ""),
        "reader_exposed": bool(explicit_reader[1]) if explicit_reader else False,
        "audio_exposed": bool(explicit_audio[1]) if explicit_audio else False,
    }
    for section in ("rights", "demand", "ingestion", "edition", "visual", "audio", "qa", "cost"):
        workflow.setdefault(section, {})
    workflow["release"] = derive_minimal_release(workflow)
    workflow["audit"] = {"migration_source": "publication_workflow_schema_v2"}
    changed = workflow != current
    digest = hashlib.sha256(json.dumps(workflow, sort_keys=True).encode()).hexdigest()
    return MigrationResult(
        workflow=workflow,
        conflicts=conflicts,
        changed=changed,
        audit_event={
            "event": "PUBLICATION_WORKFLOW_NORMALIZED",
            "schema_version": SCHEMA_VERSION,
            "workflow_sha256": digest,
            "changed": changed,
            "conflict_count": len(conflicts),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def migrate_book_dry_run(book: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    result = normalize_publication_workflow(book, **kwargs)
    return {
        "slug": book.get("slug", ""),
        "changed": result.changed,
        "conflicts": result.conflicts,
        "audit_event": result.audit_event,
        "publication_workflow": result.workflow,
    }


def validate_publication_workflow(workflow: Any) -> list[str]:
    if not isinstance(workflow, dict):
        return ["publication_workflow must be an object"]
    if workflow.get("schema_name") != SCHEMA_NAME:
        return ["publication_workflow schema_name is invalid"]
    if workflow.get("schema_version") != SCHEMA_VERSION:
        return [f"publication_workflow schema_version must be {SCHEMA_VERSION}"]
    errors: list[str] = []
    for path in ("rights", "demand", "ingestion", "edition", "visual", "audio", "qa", "cost", "publication"):
        if not isinstance(workflow.get(path), dict):
            errors.append(f"publication_workflow.{path} must be an object")
    return errors


def migrate_books_dry_run(books: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    results = [migrate_book_dry_run(book, **kwargs) for book in books]
    return {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "book_count": len(results),
        "changed_count": sum(result["changed"] for result in results),
        "conflict_count": sum(len(result["conflicts"]) for result in results),
        "results": results,
    }
