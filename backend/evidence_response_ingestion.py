"""Fail-closed intake for external catalogue evidence decisions.

The service deliberately validates against the already persisted edition record;
it never creates an edition, package, hash, authority, or publication scope.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Mapping

try:
    from pymongo.errors import DuplicateKeyError
except ImportError:  # pragma: no cover - exercised only in minimal validation environments
    DuplicateKeyError = ()

DECISIONS = frozenset({"APPROVED", "REJECTED", "NEEDS_MORE_INFORMATION"})
HEX_SHA256 = re.compile(r"^[a-f0-9]{64}$")
INDIA_TEXT_READER_ONLY = "INDIA_TEXT_READER_ONLY"


class EvidenceResponseError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _sha(value: Any) -> str:
    return str(value or "").strip().lower()


def _canonical_digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(dict(value), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _record_hashes(edition: Mapping[str, Any]) -> tuple[str, str]:
    workflow = edition.get("publication_workflow") if isinstance(edition.get("publication_workflow"), Mapping) else {}
    candidates = [edition, workflow]
    source = package = ""
    for item in candidates:
        source = source or _sha(item.get("source_sha256") or item.get("source_hash"))
        package = package or _sha(item.get("package_sha256") or item.get("package_hash"))
        rights = item.get("rights_metadata") if isinstance(item.get("rights_metadata"), Mapping) else {}
        package_data = item.get("package") if isinstance(item.get("package"), Mapping) else {}
        source = source or _sha(rights.get("source_sha256") or package_data.get("source_sha256"))
        package = package or _sha(rights.get("package_sha256") or package_data.get("package_sha256"))
    return source, package


def validate_response(payload: Mapping[str, Any], edition: Mapping[str, Any], *, actor: str) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or not isinstance(edition, Mapping):
        raise EvidenceResponseError("MALFORMED_EVIDENCE_RESPONSE")
    required = ("decision_id", "idempotency_key", "edition_id", "source_sha256", "package_sha256", "authority_id", "authorized_scope", "decision")
    if any(not isinstance(payload.get(field), str) or not payload[field].strip() for field in required):
        raise EvidenceResponseError("MALFORMED_EVIDENCE_RESPONSE")
    decision = payload["decision"].strip().upper()
    if decision not in DECISIONS:
        raise EvidenceResponseError("UNSUPPORTED_DECISION")
    edition_id = str(edition.get("edition_id") or edition.get("slug") or edition.get("id") or "")
    if payload["edition_id"] != edition_id:
        raise EvidenceResponseError("UNKNOWN_OR_MISMATCHED_EDITION")
    source, package = _record_hashes(edition)
    submitted_source = _sha(payload["source_sha256"])
    submitted_package = _sha(payload["package_sha256"])
    if not HEX_SHA256.fullmatch(submitted_source) or not HEX_SHA256.fullmatch(submitted_package):
        raise EvidenceResponseError("INVALID_HASH")
    if not source or not package or source != submitted_source or package != submitted_package:
        raise EvidenceResponseError("STALE_OR_MISMATCHED_PACKAGE_HASH")
    scope = payload["authorized_scope"].strip()
    if scope != INDIA_TEXT_READER_ONLY:
        raise EvidenceResponseError("INVALID_AUTHORIZED_SCOPE")
    authority = payload["authority_id"].strip()
    allowed = edition.get("evidence_authorities") or edition.get("authorized_evidence_authorities") or edition.get("publication_authorities")
    if not isinstance(allowed, list) or authority not in allowed:
        raise EvidenceResponseError("INVALID_AUTHORITY")
    evidence = payload.get("evidence")
    if not isinstance(evidence, Mapping) or not evidence:
        raise EvidenceResponseError("MISSING_EVIDENCE")
    now = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": "earnalism.evidence-response.v1",
        "decision_id": payload["decision_id"].strip(),
        "idempotency_key": payload["idempotency_key"].strip(),
        "edition_id": edition_id,
        "source_sha256": submitted_source,
        "package_sha256": submitted_package,
        "authority_id": authority,
        "authorized_scope": scope,
        "decision": decision,
        "evidence": dict(evidence),
        "actor": actor,
        "received_at": now,
        "decision_digest": _canonical_digest(payload),
    }


async def ingest_response(*, db: Any, payload: Mapping[str, Any], edition: Mapping[str, Any], actor: str) -> dict[str, Any]:
    record = validate_response(payload, edition, actor=actor)
    existing = await db.catalogue_evidence_decisions.find_one({"idempotency_key": record["idempotency_key"]}, {"_id": 0})
    if existing:
        if existing.get("decision_digest") != record["decision_digest"]:
            raise EvidenceResponseError("IDEMPOTENCY_CONFLICT")
        return {"decision_id": existing["decision_id"], "edition_id": existing["edition_id"], "decision": existing["decision"], "duplicate": True, "requeued": False}
    existing_decision = await db.catalogue_evidence_decisions.find_one({"edition_id": record["edition_id"], "decision_id": {"$ne": record["decision_id"]}, "active": True}, {"_id": 0})
    if existing_decision and existing_decision.get("decision_digest") != record["decision_digest"] and not payload.get("supersedes_decision_id"):
        raise EvidenceResponseError("CONFLICTING_DECISION")
    record["active"] = True
    if payload.get("supersedes_decision_id"):
        if payload["supersedes_decision_id"] != (existing_decision or {}).get("decision_id"):
            raise EvidenceResponseError("INVALID_SUPERSESSION")
        await db.catalogue_evidence_decisions.update_one({"decision_id": payload["supersedes_decision_id"], "edition_id": record["edition_id"]}, {"$set": {"active": False, "superseded_at": record["received_at"]}})
    try:
        await db.catalogue_evidence_decisions.insert_one(record)
    except DuplicateKeyError:
        # A concurrent identical submission may pass the read-before-write
        # check.  Let the unique idempotency index arbitrate, then return the
        # same durable duplicate result instead of leaking a storage error.
        existing = await db.catalogue_evidence_decisions.find_one({"idempotency_key": record["idempotency_key"]}, {"_id": 0})
        if existing and existing.get("decision_digest") == record["decision_digest"]:
            return {"decision_id": existing["decision_id"], "edition_id": existing["edition_id"], "decision": existing["decision"], "duplicate": True, "requeued": False}
        raise EvidenceResponseError("IDEMPOTENCY_CONFLICT")
    audit = {"event": "CATALOGUE_EVIDENCE_DECISION_RECEIVED", "event_id": record["decision_id"], "edition_id": record["edition_id"], "decision": record["decision"], "actor": actor, "occurred_at": record["received_at"]}
    await db.catalogue_evidence_decision_audit.insert_one(audit)
    await db.catalogue_evidence_requeue.update_one({"edition_id": record["edition_id"], "decision_id": record["decision_id"]}, {"$setOnInsert": {"edition_id": record["edition_id"], "decision_id": record["decision_id"], "state": "QUEUED", "created_at": record["received_at"]}}, upsert=True)
    return {"decision_id": record["decision_id"], "edition_id": record["edition_id"], "decision": record["decision"], "duplicate": False, "requeued": True}
