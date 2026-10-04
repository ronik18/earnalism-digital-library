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
    def matches(self, row, query):
        return all(row.get(k) == v if not isinstance(v, dict) else (row.get(k) in v['$in'] if '$in' in v else v.get('$ne') != row.get(k)) for k, v in query.items())
    async def find_one(self, query, projection=None, **kwargs):
        return next((deepcopy(row) for row in self.rows if self.matches(row, query)), None)
    async def insert_one(self, row, **kwargs):
        record = deepcopy(row); record.setdefault('_id', str(len(self.rows))); self.rows.append(record)
    async def update_one(self, query, update, upsert=False, **kwargs):
        row = next((row for row in self.rows if self.matches(row, query)), None)
        if row is not None:
            row.update(update.get('$set', {}))
            for key, amount in update.get('$inc', {}).items(): row[key] = row.get(key, 0) + amount
        elif upsert:
            await self.insert_one(dict(query, **update.get('$setOnInsert', {})))
    async def update_many(self, query, update, **kwargs):
        for row in self.rows:
            if self.matches(row, query): row.update(update.get('$set', {}))


class Session:
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def with_transaction(self, callback): return await callback(self)


class Client:
    async def start_session(self): return Session()


class DB:
    def __init__(self):
        self.client = Client()
        self.books = Collection(); self.books.rows = [dict(edition(), _id='fixture-book')]
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
        assert len(db.catalogue_evidence_requeue.rows) == 1
        assert len([row for row in db.catalogue_evidence_decision_audit.rows if row['event'] == 'CATALOGUE_EVIDENCE_DECISION_RECEIVED']) == 1
        assert db.catalogue_evidence_requeue.rows[0]['state'] == 'HELD'
        assert db.catalogue_evidence_decisions.rows[0]['conflict_pending'] is True
    asyncio.run(run())


def test_decision_enum_and_evidence_are_required():
    with pytest.raises(EvidenceResponseError, match="UNSUPPORTED_DECISION"):
        validate_response(payload(decision="MAYBE"), edition(), actor="admin:x")
    with pytest.raises(EvidenceResponseError, match="MISSING_EVIDENCE"):
        validate_response(payload(evidence={}), edition(), actor="admin:x")


@pytest.mark.parametrize('decision', ['REJECTED', 'NEEDS_MORE_INFORMATION'])
def test_external_holds_are_not_requeued(decision):
    async def run():
        db = DB()
        result = await ingest_response(db=db, payload=payload(decision=decision), edition=edition(), actor='admin:x')
        assert not result['requeued']
        assert db.catalogue_evidence_requeue.rows[0]['state'] == 'HELD'
        assert db.catalogue_evidence_decision_audit.rows[0]['package_sha256'] == PACKAGE
        assert 'evidence' not in db.catalogue_evidence_decision_audit.rows[0]
    asyncio.run(run())


def test_stale_caller_snapshot_does_not_authorize_changed_database_package():
    async def run():
        db = DB(); db.books.rows[0]['package_sha256'] = 'c' * 64
        with pytest.raises(EvidenceResponseError, match='STALE_OR_MISMATCHED_PACKAGE_HASH'):
            await ingest_response(db=db, payload=payload(), edition=edition(), actor='admin:x')
        assert not db.catalogue_evidence_decisions.rows
    asyncio.run(run())


def test_stale_caller_snapshot_does_not_authorize_revoked_authority():
    async def run():
        db = DB(); db.books.rows[0]['evidence_authorities'] = []
        with pytest.raises(EvidenceResponseError, match='INVALID_AUTHORITY'):
            await ingest_response(db=db, payload=payload(), edition=edition(), actor='admin:x')
        assert not db.catalogue_evidence_decisions.rows
    asyncio.run(run())


def test_intake_storage_failure_is_a_safe_503(monkeypatch):
    from backend import server
    from fastapi import HTTPException
    from pymongo.errors import PyMongoError
    class Books:
        def find(self, *args, **kwargs): raise PyMongoError('fixture storage unavailable')
    monkeypatch.setattr(server, 'db', type('UnavailableDB', (), {'books': Books()})())
    with pytest.raises(HTTPException) as error:
        asyncio.run(server.admin_ingest_catalogue_evidence(server.CatalogueEvidenceResponseIn(**payload()), {'email': 'fixture@example.com'}))
    assert error.value.status_code == 503
    assert error.value.detail == 'EVIDENCE_STORAGE_UNAVAILABLE'
