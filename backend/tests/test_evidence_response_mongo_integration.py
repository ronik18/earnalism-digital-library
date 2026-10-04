"""Real process/restart/race tests; explicit disposable loopback replica set only."""
import asyncio
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlparse
import uuid

import bcrypt
import httpx
import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

from backend.evidence_response_ingestion import EvidenceResponseError, ingest_response, initialize_evidence_indexes
from backend.tests.test_evidence_response_ingestion import edition, payload

pytestmark = pytest.mark.skipif(os.environ.get('CATALOGUE_EVIDENCE_MONGO_INTEGRATION') != '1', reason='requires explicit disposable loopback replica set')


class Harness:
    def __init__(self, uri, db_name, port, logs):
        self.uri, self.db_name, self.port, self.logs = uri, db_name, port, logs
        self.process = None
        self.log = None
        self.token = None

    def start(self):
        env = dict(os.environ, MONGODB_URL=self.uri, DB_NAME=self.db_name,
                   JWT_SECRET='disposable-response-fixture-signing-secret-0123456789',
                   ENVIRONMENT='uat', ENABLE_STARTUP_DB_MAINTENANCE='false',
                   ENABLE_BACKGROUND_WORKERS='false', ENABLE_AUDIOBOOK_PIPELINE='false',
                   ENABLE_SCHEDULED_JOBS='false', ENABLE_QUEUE_CONSUMER='false',
                   ENABLE_BOOK_RENDERING_JOBS='false', ENABLE_COVER_GENERATION='false',
                   COST_CONTROL_MODE='true', REDIS_URL=os.environ.get('RESPONSE_TEST_REDIS', 'redis://127.0.0.1:26582/9'),
                   RAZORPAY_KEY_ID='', RAZORPAY_KEY_SECRET='', RAZORPAY_WEBHOOK_SECRET='')
        self.log = (self.logs / 'backend.log').open('a')
        self.process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.server:app', '--host', '127.0.0.1', '--port', str(self.port)], env=env, stdout=self.log, stderr=self.log)
        for _ in range(100):
            if self.process.poll() is not None:
                raise RuntimeError('disposable backend exited; inspect fixture backend.log')
            try:
                response = httpx.get(self.base + '/health', timeout=.3)
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(.1)
        raise RuntimeError('disposable backend did not become reachable')

    @property
    def base(self): return f'http://127.0.0.1:{self.port}/api'

    def stop(self, crash=False):
        if self.process:
            self.process.kill() if crash else self.process.terminate()
            try: self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill(); self.process.wait(timeout=5)
            self.process = None
        if self.log:
            self.log.close(); self.log = None

    def restart(self):
        self.stop(crash=True); self.start()

    def login(self):
        response = httpx.post(self.base + '/auth/login', json={'email': 'response-admin@example.com', 'password': 'disposable-fixture-password'}, timeout=5)
        assert response.status_code == 200
        self.token = response.json()['token']

    @property
    def headers(self): return {'Authorization': 'Bearer ' + self.token}

    def submit(self, body):
        return httpx.post(self.base + '/admin/catalogue/evidence-responses', json=body, headers=self.headers, timeout=10)


@pytest.fixture(scope='module')
def harness(tmp_path_factory):
    uri = os.environ.get('RESPONSE_TEST_MONGO', '')
    parsed = urlparse(uri)
    if parsed.hostname != '127.0.0.1' or 'replicaSet=' not in uri:
        raise RuntimeError('response tests require an explicit loopback replica set')
    name = 'response_ingestion_disposable_' + uuid.uuid4().hex
    sync = MongoClient(uri, serverSelectionTimeoutMS=5000)
    hello = sync.admin.command('hello')
    assert hello.get('isWritablePrimary') and hello.get('setName')
    async def indexes():
        client = AsyncIOMotorClient(uri)
        await initialize_evidence_indexes(client[name]); client.close()
    asyncio.run(indexes())
    db = sync[name]
    db.users.insert_one({'id': 'response-admin', 'email': 'response-admin@example.com', 'role': 'admin', 'status': 'active', 'password_hash': bcrypt.hashpw(b'disposable-fixture-password', bcrypt.gensalt(rounds=4)).decode()})
    instance = Harness(uri, name, int(os.environ.get('RESPONSE_TEST_PORT', '18282')), tmp_path_factory.mktemp('response-process'))
    instance.sync, instance.db = sync, db
    try:
        instance.start(); instance.login(); yield instance
    finally:
        instance.stop(); sync.drop_database(name); sync.close()


@pytest.fixture(autouse=True)
def seed(harness):
    for name in ('books', 'catalogue_evidence_decisions', 'catalogue_evidence_decision_audit', 'catalogue_evidence_requeue'):
        harness.db[name].delete_many({})
    harness.db.books.insert_many([dict(edition(), edition_id='book-' + str(n), slug='book-' + str(n), is_published=False) for n in (1, 2, 3)])


@pytest.mark.parametrize('decision', ['APPROVED', 'REJECTED', 'NEEDS_MORE_INFORMATION'])
def test_decision_audit_idempotency_and_holds_survive_actual_process_restart(harness, decision):
    body = payload(decision=decision, evidence={'reference': 'fixture:owned-text', 'requested_fields': ['edition_citation']})
    result = harness.submit(body)
    assert result.status_code == 200
    assert result.json()['requeued'] == (decision == 'APPROVED')
    harness.restart()
    replay = harness.submit(body)
    assert replay.status_code == 200 and replay.json()['duplicate']
    db = harness.db
    assert db.catalogue_evidence_decisions.count_documents({'active': True}) == 1
    assert db.catalogue_evidence_requeue.count_documents({}) == 1
    assert db.catalogue_evidence_decision_audit.count_documents({}) == 1
    canonical = db.catalogue_evidence_decisions.find_one({'active': True})
    assert canonical['evidence']['requested_fields'] == ['edition_citation']
    audit = db.catalogue_evidence_decision_audit.find_one({})
    assert all(key in audit for key in ('edition_id', 'package_sha256', 'source_sha256', 'authority_id', 'authorized_scope', 'decision', 'evidence_reference', 'occurred_at', 'idempotency_key'))
    assert 'evidence' not in audit
    assert db.catalogue_evidence_requeue.find_one({})['state'] == ('QUEUED' if decision == 'APPROVED' else 'HELD')
    assert not db.books.find_one({'slug': 'book-1'})['is_published']


def test_identical_concurrent_http_submissions_are_idempotent(harness):
    async def requests():
        async with httpx.AsyncClient(timeout=15) as client:
            return await asyncio.gather(*(client.post(harness.base + '/admin/catalogue/evidence-responses', json=payload(), headers=harness.headers) for _ in range(8)))
    results = asyncio.run(requests())
    assert [r.status_code for r in results] == [200] * 8
    assert sum(not r.json()['duplicate'] for r in results) == 1
    assert harness.db.catalogue_evidence_decisions.count_documents({}) == 1
    assert harness.db.catalogue_evidence_decision_audit.count_documents({}) == 1
    assert harness.db.catalogue_evidence_requeue.count_documents({}) == 1


def test_conflicting_concurrent_decisions_freeze_reassessment(harness):
    async def requests():
        async with httpx.AsyncClient(timeout=15) as client:
            return await asyncio.gather(*(client.post(harness.base + '/admin/catalogue/evidence-responses', json=payload(decision_id='decision-' + str(i), idempotency_key='key-' + str(i), decision=d), headers=harness.headers) for i, d in enumerate(['APPROVED', 'REJECTED'])))
    results = asyncio.run(requests())
    assert sorted(r.status_code for r in results) == [200, 409]
    assert harness.db.catalogue_evidence_decisions.count_documents({'active': True}) == 1
    assert harness.db.catalogue_evidence_decisions.find_one({'active': True})['conflict_pending']
    assert harness.db.catalogue_evidence_requeue.count_documents({'state': 'QUEUED'}) == 0
    assert harness.db.catalogue_evidence_decision_audit.count_documents({'event': 'CATALOGUE_EVIDENCE_DECISION_CONFLICT'}) == 1


def test_package_change_invalidates_old_approval_replay(harness):
    assert harness.submit(payload()).status_code == 200
    harness.db.books.update_one({'slug': 'book-1'}, {'$set': {'package_sha256': 'c' * 64}})
    response = harness.submit(payload())
    assert response.status_code == 409
    assert harness.db.catalogue_evidence_decisions.find_one({})['package_sha256'] == 'b' * 64
    assert not harness.db.books.find_one({'slug': 'book-1'})['is_published']


@pytest.mark.parametrize('changed,code', [({'package_sha256': 'c' * 64}, 'STALE_OR_MISMATCHED_PACKAGE_HASH'), ({'evidence_authorities': []}, 'INVALID_AUTHORITY')])
def test_mutation_after_transaction_read_is_revalidated(harness, changed, code):
    async def run():
        client = AsyncIOMotorClient(harness.uri)
        db = client[harness.db_name]
        snapshot = await db.books.find_one({'slug': 'book-1'})
        read, mutated = asyncio.Event(), asyncio.Event()
        class Books:
            first = True
            async def find_one(self, *args, **kwargs):
                value = await db.books.find_one(*args, **kwargs)
                if self.first:
                    self.first = False; read.set(); await mutated.wait()
                return value
            def __getattr__(self, key): return getattr(db.books, key)
        class Proxy:
            books = Books()
            def __getattr__(self, key): return getattr(db, key)
        async def mutate():
            await read.wait(); await db.books.update_one({'slug': 'book-1'}, {'$set': changed}); mutated.set()
        task = asyncio.create_task(mutate())
        try:
            with pytest.raises(EvidenceResponseError, match=code):
                await ingest_response(db=Proxy(), payload=payload(), edition=snapshot, actor='fixture')
            await task
            assert await db.catalogue_evidence_decisions.count_documents({}) == 0
        finally: client.close()
    asyncio.run(run())


def test_invalid_authority_and_scope_cannot_win_concurrent_arrival(harness):
    async def requests():
        async with httpx.AsyncClient(timeout=15) as client:
            bodies = [payload(), payload(decision_id='unknown', idempotency_key='unknown', authority_id='not-authorized'), payload(decision_id='scope', idempotency_key='scope', authorized_scope='GLOBAL')]
            return await asyncio.gather(*(client.post(harness.base + '/admin/catalogue/evidence-responses', json=b, headers=harness.headers) for b in bodies))
    results = asyncio.run(requests())
    assert [r.status_code for r in results] == [200, 422, 422]
    assert harness.db.catalogue_evidence_decisions.count_documents({}) == 1
    assert harness.db.catalogue_evidence_decisions.find_one({})['authority_id'] == 'owner-review'


def test_only_one_edition_requeued_and_no_activation(harness):
    before = list(harness.db.books.find({'slug': {'$in': ['book-2', 'book-3']}}))
    assert harness.db.catalogue_evidence_requeue.count_documents({}) == 0
    assert harness.submit(payload()).status_code == 200
    assert harness.db.catalogue_evidence_requeue.count_documents({}) == 1
    assert harness.db.catalogue_evidence_requeue.find_one({})['purpose'] == 'EVIDENCE_REASSESSMENT_ONLY'
    assert list(harness.db.books.find({'slug': {'$in': ['book-2', 'book-3']}})) == before
    assert harness.db.books.count_documents({'is_published': True}) == 0


def test_failure_between_decision_and_audit_rolls_back_entire_transition(harness):
    async def run():
        client = AsyncIOMotorClient(harness.uri); db = client[harness.db_name]
        class Audit:
            async def update_one(self, *args, **kwargs): raise RuntimeError('fixture write interruption')
        class Proxy:
            catalogue_evidence_decision_audit = Audit()
            def __getattr__(self, key): return getattr(db, key)
        try:
            snapshot = await db.books.find_one({'slug': 'book-1'})
            with pytest.raises(RuntimeError, match='fixture write interruption'):
                await ingest_response(db=Proxy(), payload=payload(), edition=snapshot, actor='fixture')
            assert await db.catalogue_evidence_decisions.count_documents({}) == 0
            assert await db.catalogue_evidence_requeue.count_documents({}) == 0
            assert 'evidence_response_generation' not in await db.books.find_one({'slug': 'book-1'})
        finally: client.close()
    asyncio.run(run())
    harness.restart()
    assert harness.submit(payload()).status_code == 200


def test_ambiguous_edition_alias_is_denied(harness):
    harness.db.books.insert_one(dict(edition(), slug='other-slug', is_published=False))
    assert harness.submit(payload()).status_code == 409
    assert harness.db.catalogue_evidence_decisions.count_documents({}) == 0


def test_unauthenticated_request_cannot_write(harness):
    response = httpx.post(harness.base + '/admin/catalogue/evidence-responses', json=payload(), timeout=5)
    assert response.status_code in (401, 403)
    assert harness.db.catalogue_evidence_decisions.count_documents({}) == 0


def test_evidence_persistence_does_not_depend_on_redis_delivery(harness, monkeypatch):
    # No Redis queue is produced: the transactional Mongo outbox is authoritative.
    monkeypatch.setenv('RESPONSE_TEST_REDIS', 'redis://127.0.0.1:26583/9')
    harness.restart()
    assert harness.submit(payload()).status_code == 200
    assert harness.db.catalogue_evidence_requeue.count_documents({}) == 1
    assert harness.db.catalogue_evidence_decision_audit.count_documents({}) == 1


def test_explicit_supersession_resolves_conflict_without_two_active_states(harness):
    assert harness.submit(payload()).status_code == 200
    conflict = payload(decision_id='conflict', idempotency_key='conflict-key', decision='REJECTED')
    assert harness.submit(conflict).status_code == 409
    replacement = payload(decision_id='replacement', idempotency_key='replacement-key', decision='NEEDS_MORE_INFORMATION', supersedes_decision_id='decision-1')
    assert harness.submit(replacement).status_code == 200
    assert harness.db.catalogue_evidence_decisions.count_documents({'active': True}) == 1
    canonical = harness.db.catalogue_evidence_decisions.find_one({'active': True})
    assert canonical['decision'] == 'NEEDS_MORE_INFORMATION' and not canonical['conflict_pending']
    assert harness.db.catalogue_evidence_requeue.count_documents({'state': 'QUEUED'}) == 0
