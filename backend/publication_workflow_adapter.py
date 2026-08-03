"""Single canonical read/write boundary for publication workflow producers.

Producers may retain legacy fields in their payloads during the compatibility
window, but all persisted workflow state must pass through this adapter.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any

try:
    from publication_workflow_schema import SCHEMA_NAME, SCHEMA_VERSION, normalize_publication_workflow, validate_publication_workflow
except ImportError:  # pragma: no cover - supports package-style test imports
    from backend.publication_workflow_schema import SCHEMA_NAME, SCHEMA_VERSION, normalize_publication_workflow, validate_publication_workflow


def canonical_workflow(book: dict[str, Any]) -> dict[str, Any]:
    value = book.get("publication_workflow")
    if isinstance(value, dict) and value.get("schema_name") == SCHEMA_NAME and value.get("schema_version") == SCHEMA_VERSION:
        return deepcopy(value)
    return normalize_publication_workflow(book).workflow


def canonical_update(book: dict[str, Any], *, approved_artifact: dict[str, Any] | None = None, release_evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    result = normalize_publication_workflow(book, approved_artifact=approved_artifact, release_evidence=release_evidence)
    errors = validate_publication_workflow(result.workflow)
    if errors:
        raise ValueError("Invalid canonical publication workflow: " + "; ".join(errors))
    return result.workflow


def canonical_audit_event(slug: str, workflow: dict[str, Any], event: str = "PUBLICATION_WORKFLOW_CANONICAL_WRITE") -> dict[str, Any]:
    digest = hashlib.sha256(json.dumps(workflow, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return {
        "event": event,
        "event_id": hashlib.sha256(f"{slug}:{digest}:{event}".encode()).hexdigest(),
        "slug": slug,
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "workflow_sha256": digest,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }


def mongo_canonical_update(book: dict[str, Any], *, approved_artifact: dict[str, Any] | None = None, release_evidence: dict[str, Any] | None = None, event: str = "PUBLICATION_WORKFLOW_CANONICAL_WRITE") -> dict[str, Any]:
    workflow = canonical_update(book, approved_artifact=approved_artifact, release_evidence=release_evidence)
    return {"$set": {"publication_workflow": workflow}, "$addToSet": {"publication_workflow_audit": canonical_audit_event(str(book.get("slug") or ""), workflow, event)}}
