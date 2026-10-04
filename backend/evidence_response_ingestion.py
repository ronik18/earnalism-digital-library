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


def _audit(record: Mapping[str, Any], event: str, reason: str | None = None) -> dict[str, Any]:
    """Reference-only operational audit; no evidence body or credentials."""
    evidence = record.get("evidence") or {}
    return {"event": event, "event_id": record["decision_id"],
            "edition_id": record["edition_id"], "source_sha256": record["source_sha256"],
            "package_sha256": record["package_sha256"], "authority_id": record["authority_id"],
            "authorized_scope": record["authorized_scope"], "decision": record["decision"],
            "evidence_reference": evidence.get("reference") or evidence.get("source"),
            "idempotency_key": record["idempotency_key"], "actor": record["actor"],
            "occurred_at": record["received_at"], "reason": reason}


async def initialize_evidence_indexes(db):
    await db.catalogue_evidence_decisions.create_index("decision_id", unique=True)
    await db.catalogue_evidence_decisions.create_index("idempotency_key", unique=True)
    await db.catalogue_evidence_decisions.create_index("edition_id", unique=True, partialFilterExpression={"active": True}, name="one_active_evidence_decision_per_edition")
    await db.catalogue_evidence_decision_audit.create_index([("edition_id", 1), ("occurred_at", -1)])
    await db.catalogue_evidence_requeue.create_index([("edition_id", 1), ("decision_id", 1)], unique=True)


async def ingest_response(*, db: Any, payload: Mapping[str, Any], edition: Mapping[str, Any], actor: str) -> dict[str, Any]:
    # Admission validation is repeated against the current server record inside
    # the transaction. A caller's stale snapshot never grants authority.
    record = validate_response(payload, edition, actor=actor)

    async def commit(session):
        selector = {"_id": edition["_id"]} if "_id" in edition else {"slug": record["edition_id"]}
        current = await db.books.find_one(selector, session=session)
        if current is None:
            raise EvidenceResponseError("UNKNOWN_OR_MISMATCHED_EDITION")
        fresh = validate_response(payload, current, actor=actor)
        # Write fencing conflicts with concurrent package/authority mutation.
        # with_transaction retries and revalidates the new current record.
        await db.books.update_one({"_id": current["_id"]}, {"$inc": {"evidence_response_generation": 1}}, session=session)
        existing = await db.catalogue_evidence_decisions.find_one({"idempotency_key": fresh["idempotency_key"]}, session=session)
        error = None
        if existing:
            if existing.get("decision_digest") == fresh["decision_digest"]:
                return {"decision_id": existing["decision_id"], "edition_id": existing["edition_id"], "decision": existing["decision"], "duplicate": True, "requeued": False}
            error = "IDEMPOTENCY_CONFLICT"
        same_id = await db.catalogue_evidence_decisions.find_one({"decision_id": fresh["decision_id"]}, session=session)
        if same_id and not existing:
            error = "CONFLICTING_DECISION"
        prior = await db.catalogue_evidence_decisions.find_one({"edition_id": fresh["edition_id"], "active": True}, session=session)
        supersedes = payload.get("supersedes_decision_id")
        if supersedes and supersedes != (prior or {}).get("decision_id"):
            error = "INVALID_SUPERSESSION"
        if prior and not supersedes and not error:
            error = "CONFLICTING_DECISION"
        if error:
            # A genuinely conflicting valid response freezes reassessment until
            # an explicit bound supersession resolves it. This is never an
            # activation job or a publication grant.
            if prior:
                await db.catalogue_evidence_decisions.update_one({"_id": prior["_id"]}, {"$set": {"conflict_pending": True}}, session=session)
                await db.catalogue_evidence_requeue.update_many({"edition_id": fresh["edition_id"], "state": {"$in": ["QUEUED", "PROCESSING"]}}, {"$set": {"state": "HELD", "reason": error}}, session=session)
            audit = _audit(fresh, "CATALOGUE_EVIDENCE_DECISION_CONFLICT", error)
            await db.catalogue_evidence_decision_audit.update_one({"_id": "conflict:" + fresh["decision_digest"]}, {"$setOnInsert": audit}, upsert=True, session=session)
            return {"error": error}
        if prior:
            await db.catalogue_evidence_decisions.update_one({"_id": prior["_id"]}, {"$set": {"active": False, "superseded_at": fresh["received_at"]}}, session=session)
            await db.catalogue_evidence_requeue.update_many({"edition_id": fresh["edition_id"], "state": {"$in": ["QUEUED", "PROCESSING"]}}, {"$set": {"state": "HELD", "reason": "DECISION_SUPERSEDED"}}, session=session)
        fresh.update(active=True, conflict_pending=False)
        await db.catalogue_evidence_decisions.insert_one(fresh, session=session)
        audit = _audit(fresh, "CATALOGUE_EVIDENCE_DECISION_RECEIVED")
        await db.catalogue_evidence_decision_audit.update_one({"_id": "received:" + fresh["decision_id"]}, {"$setOnInsert": audit}, upsert=True, session=session)
        queued = fresh["decision"] == "APPROVED"
        await db.catalogue_evidence_requeue.update_one({"edition_id": fresh["edition_id"], "decision_id": fresh["decision_id"]}, {"$setOnInsert": {
            "edition_id": fresh["edition_id"], "decision_id": fresh["decision_id"], "package_sha256": fresh["package_sha256"],
            "source_sha256": fresh["source_sha256"], "state": "QUEUED" if queued else "HELD",
            "reason": None if queued else fresh["decision"], "purpose": "EVIDENCE_REASSESSMENT_ONLY", "created_at": fresh["received_at"]}}, upsert=True, session=session)
        return {"decision_id": fresh["decision_id"], "edition_id": fresh["edition_id"], "decision": fresh["decision"], "duplicate": False, "requeued": queued}

    for attempt in range(3):
        try:
            async with await db.client.start_session() as session:
                result = await session.with_transaction(commit)
            if "error" in result:
                raise EvidenceResponseError(result["error"])
            return result
        except DuplicateKeyError:
            # Unique indexes are an additional safety boundary. A concurrent
            # winner must be reread, never turned into an unhandled 500.
            if attempt == 2:
                raise EvidenceResponseError("CONFLICTING_DECISION")
    raise EvidenceResponseError("CONFLICTING_DECISION")
