import asyncio
from copy import deepcopy

import pytest

from backend.evidence_response_ingestion import EvidenceResponseError, ingest_response, validate_response


SOURCE = "a" * 64
PACKAGE = "b" * 64


def edition():
    return {"edition_id": "book-1", "slug": "book-1", "source_sha256": SOURCE, "package_sha256": PACKAGE, "evidence_authorities": ["owner-review"]}


def payload(**overrides):
    value = {"decision_id": "decision-1", "idempotency_key": "idem-1", "edition_id": "book-1", "source_sha256": SOURCE, "package_sha256": PACKAGE, "authority_id": "owner-review", "authorized_scope": "INDIA_TEXT_READER_ONLY", "decision": "APPROVED", "evidence": {"source": "internal-evidence"}}
    value.update(overrides)
    return value


def test_validation_is_exact_and_fail_closed():
    assert validate_response(payload(), edition(), actor="admin:x")["decision"] == "APPROVED"
    for field, value in (("package_sha256", "c" * 64), ("edition_id", "other"), ("authority_id", "unknown"), ("authorized_scope", "GLOBAL")):
        with pytest.raises(EvidenceResponseError):
            validate_response(payload(**{field: value}), edition(), actor="admin:x")


class Collection:
    def __init__(self): self.rows = []
    async def find_one(self, query, projection=None):
        for row in self.rows:
            if all((row.get(k) == v if not isinstance(v, dict) else (v.get("$ne") != row.get(k))) for k, v in query.items()): return deepcopy(row)
        return None
    async def insert_one(self, row): self.rows.append(deepcopy(row))
    async def update_one(self, query, update, upsert=False):
        row = await self.find_one(query)
        if row:
            for key, value in update.get("$set", {}).items():
                next(item for item in self.rows if item.get("decision_id") == row.get("decision_id"))[key] = value
        elif upsert:
            value = dict(update.get("$setOnInsert", {})); self.rows.append(value)


class DB:
    def __init__(self):
        self.catalogue_evidence_decisions = Collection(); self.catalogue_evidence_decision_audit = Collection(); self.catalogue_evidence_requeue = Collection()


def test_durable_idempotency_and_conflict_and_one_edition_requeue():
    async def run():
        db = DB()
        first = await ingest_response(db=db, payload=payload(), edition=edition(), actor="admin:x")
        duplicate = await ingest_response(db=db, payload=payload(), edition=edition(), actor="admin:x")
        assert first["requeued"] is True and duplicate["duplicate"] is True
        with pytest.raises(EvidenceResponseError, match="IDEMPOTENCY_CONFLICT"):
            await ingest_response(db=db, payload=payload(decision="REJECTED"), edition=edition(), actor="admin:x")
        with pytest.raises(EvidenceResponseError, match="CONFLICTING_DECISION"):
            await ingest_response(db=db, payload=payload(decision_id="decision-2", idempotency_key="idem-2", decision="REJECTED"), edition=edition(), actor="admin:x")
        assert len(db.catalogue_evidence_requeue.rows) == 1 and len(db.catalogue_evidence_decision_audit.rows) == 1
    asyncio.run(run())


def test_decision_enum_and_evidence_are_required():
    with pytest.raises(EvidenceResponseError, match="UNSUPPORTED_DECISION"):
        validate_response(payload(decision="MAYBE"), edition(), actor="admin:x")
    with pytest.raises(EvidenceResponseError, match="MISSING_EVIDENCE"):
        validate_response(payload(evidence={}), edition(), actor="admin:x")
