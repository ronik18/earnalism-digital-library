"""Exact Sredni counters on the existing disposable CI Mongo replica.

No service, client credentials, authority record or production URI is created
by this module. The existing UAT fixture owns its UUID database and cleanup.
Absent the explicit integration flag these cases are UNPERFORMED, not PASS;
the existing mandatory CI selector sets it, so setup failures fail the gate.
"""
import asyncio
import copy
import os
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from pymongo.errors import PyMongoError

import test_sredni_initial_review_domain as domain
import test_sredni_initial_review_operator as fixtures
from scripts.uat_mongo_fixture import isolated_database

scope = domain.scope
service_module = domain.service_module
operator = fixtures.operator
Error = domain.ReadingPassError

pytestmark = pytest.mark.skipif(
    os.environ.get('READER_SEGMENT_MONGO_INTEGRATION') != '1',
    reason='Existing authenticated disposable CI replica not selected; real Mongo checks UNPERFORMED',
)

OWNED_PREFIX = 'acceptance_operator_synthetic_'
SNAPSHOT_COLLECTIONS = (
    'users', 'user_sessions', scope.WORKFLOWS, scope.GRANTS, operator.OPERATIONS,
    'reading_pass_sessions', 'reading_pass_heartbeats', 'wallet_ledger',
    'wallet_transactions', 'reading_pass_devices', 'reading_pass_audit',
)


async def rows(db):
    return {name: await db[name].find({}).sort('_id', 1).to_list(1001)
            for name in SNAPSHOT_COLLECTIONS}


async def setup(db, monkeypatch, *, prepare=None, empty=False):
    # Whole milliseconds are deliberate: BSON dates are not microsecond clocks.
    clock = [datetime.now(timezone.utc).replace(microsecond=0)]
    fake, workflow, grant = domain.seeded(clock[0])
    assert operator.scope is scope
    domain.synthetic_policy(monkeypatch, grant)  # Synthetic pair in memory only.
    monkeypatch.setattr(service_module, '_now', lambda: clock[0])
    monkeypatch.setattr(scope, '_now', lambda: clock[0])
    monkeypatch.setattr(operator, 'now', lambda: clock[0])
    if prepare:
        prepare(fake, workflow, grant)
    for name in ('users', 'user_sessions', scope.WORKFLOWS, scope.GRANTS):
        values = fake[name].rows
        if values and not (empty and name in (scope.WORKFLOWS, scope.GRANTS)):
            await db[name].insert_many(copy.deepcopy(values))
    await db.reading_pass_sessions.create_index('active_lock', unique=True, sparse=True)
    await db.wallet_ledger.create_index('idempotency_key', unique=True)
    await db.reading_pass_heartbeats.create_index([('session_id', 1), ('sequence', 1)], unique=True)
    return clock, workflow, grant


def service(db, client):
    return service_module.ReadingPassService(
        db=db, client=client, config=domain.ReadingPassConfig(),
        token_secret='SYNTHETIC-SREDNI-CI-NOT-A-REAL-ACCOUNT',
    )


async def start(svc, workflow, grant, *, ordinary=False):
    return await svc.start_session(
        user_id='user-1', auth_session_id='auth-1', device_id='SYNTHETIC-CI',
        device_label='Synthetic CI', content_type='audio',
        content_id='SYNTHETIC-ordinary-title' if ordinary else scope.profile.SLUG,
        scope={} if ordinary else domain.server_scope(workflow, grant),
    )


async def end(svc, lease):
    return await svc.end_session(user_id='user-1', auth_session_id='auth-1',
                                 session_id=lease['session_id'])


def test_real_sredni_zero_debit_fraction_ordinary_interleave_and_ledger_refs(monkeypatch):
    async def case():
        async with isolated_database(OWNED_PREFIX, retryWrites=False, retryReads=False, tz_aware=True) as (client, db):
            clock, w, g = await setup(db, monkeypatch)
            svc = service(db, client)
            first = await start(svc, w, g)
            await svc.renew_lease(**domain.renewal(first))
            clock[0] += timedelta(microseconds=900000)
            await end(svc, first)
            actual = await db[scope.WORKFLOWS].find_one({'_id': w['_id']})
            assert (actual['used_microseconds'], actual['used_credit_seconds']) == (900000, 0)
            assert await db.wallet_ledger.count_documents({}) == 0
            ordinary = await start(svc, w, g, ordinary=True)
            await svc.renew_lease(**domain.renewal(ordinary))
            clock[0] += timedelta(microseconds=200000)
            await end(svc, ordinary)
            actual = await db[scope.WORKFLOWS].find_one({'_id': w['_id']})
            assert (actual['used_microseconds'], actual['used_credit_seconds']) == (900000, 0)
            assert (await db.users.find_one({'id': 'user-1'}))['reading_fractional_microseconds'] == 100000
            again = await start(svc, w, g)
            await svc.renew_lease(**domain.renewal(again))
            clock[0] += timedelta(microseconds=900000)
            await end(svc, again)
            actual = await db[scope.WORKFLOWS].find_one({'_id': w['_id']})
            assert (actual['used_microseconds'], actual['used_credit_seconds'], actual['starts_used']) == (1800000, 1, 2)
            user = await db.users.find_one({'id': 'user-1'})
            assert (user['reading_seconds_balance'], user['reading_fractional_microseconds']) == (298, 0)
            ledger = await db.wallet_ledger.find({}).to_list(10)
            assert sum(row['debit'] for row in ledger) == 2
            dedicated = [row for row in ledger if scope.SCOPE_KEY in row['metadata']]
            assert len(dedicated) == 1
            assert dedicated[0]['metadata'][scope.WORKFLOW_KEY] == w['_id']
            assert dedicated[0]['metadata'][scope.SCOPE_KEY] == g['_id']
            assert all('native_audio_review_grant_id' not in row['metadata'] for row in ledger)
    asyncio.run(case())


@pytest.mark.parametrize('limit_field', ['used_microseconds', 'used_credit_seconds'])
def test_real_sredni_stricter_cumulative_sixty_never_replenishes(monkeypatch, limit_field):
    async def case():
        def near_limit(fake, w, g):
            w[limit_field] = 59000000 if limit_field == 'used_microseconds' else 59
        async with isolated_database(OWNED_PREFIX, retryWrites=False, retryReads=False, tz_aware=True) as (client, db):
            clock, w, g = await setup(db, monkeypatch, prepare=near_limit)
            svc = service(db, client); lease = await start(svc, w, g)
            await svc.renew_lease(**domain.renewal(lease)); clock[0] += timedelta(seconds=2)
            result = await svc.renew_lease(**domain.renewal(lease, 2))
            assert result['status'] == 'Exhausted'
            actual = await db[scope.WORKFLOWS].find_one({'_id': w['_id']})
            assert actual[limit_field] == (60000000 if limit_field == 'used_microseconds' else 60)
            assert actual['used_microseconds'] <= 60000000 and actual['used_credit_seconds'] <= 60
            before = await rows(db)
            with pytest.raises(Error): await start(svc, w, g)
            assert await rows(db) == before
    asyncio.run(case())


def test_real_sredni_third_lease_metadata_read_and_fourth_start_denial(monkeypatch):
    async def case():
        async with isolated_database(OWNED_PREFIX, retryWrites=False, retryReads=False, tz_aware=True) as (client, db):
            clock, w, g = await setup(db, monkeypatch); svc = service(db, client)
            for ordinal in range(1, 4):
                lease = await start(svc, w, g)
                assert (await db[scope.WORKFLOWS].find_one({'_id': w['_id']}))['starts_used'] == ordinal
                if ordinal == 3:
                    before = await rows(db)
                    budget = await scope.member_budget(db, fixtures.book(), 'user-1', 'auth-1', country='IN', now=clock[0])
                    metadata = scope.profile.listener_metadata_from_verified_budget(fixtures.book(), budget, country='IN', now=clock[0])
                    assert metadata['package_version'] == scope.profile.PACKAGE
                    assert metadata['narration_disclosure'] == scope.profile.DISCLOSURE
                    assert await rows(db) == before
                await end(svc, lease)
            before = await rows(db)
            with pytest.raises(Error): await start(svc, w, g)
            assert await rows(db) == before
            assert await db.reading_pass_sessions.count_documents({}) == 3
            assert await db.wallet_ledger.count_documents({}) == 0
    asyncio.run(case())


def test_real_sredni_counter_wallet_ledger_and_heartbeat_abort_together(monkeypatch):
    async def case():
        async with isolated_database(OWNED_PREFIX, retryWrites=False, retryReads=False, tz_aware=True) as (client, db):
            clock, w, g = await setup(db, monkeypatch); svc = service(db, client)
            lease = await start(svc, w, g); await svc.renew_lease(**domain.renewal(lease))
            before = await rows(db); clock[0] += timedelta(microseconds=1300000)
            original = svc._append_time_debit; reached = []
            async def fail_after_actual_writes(**kwargs):
                await original(**kwargs); reached.append(True)
                raise Error('SYNTHETIC_AFTER_REAL_LEDGER', 409, 'Synthetic rollback proof')
            monkeypatch.setattr(svc, '_append_time_debit', fail_after_actual_writes)
            with pytest.raises(Error, match='Synthetic rollback proof'):
                await svc.renew_lease(**domain.renewal(lease, 2))
            assert reached == [True] and await rows(db) == before
    asyncio.run(case())


def test_real_sredni_start_claim_and_close_share_grant_epoch_fence(monkeypatch):
    async def case():
        async with isolated_database(OWNED_PREFIX, retryWrites=False, retryReads=False, tz_aware=True) as (client, db):
            clock, w, g = await setup(db, monkeypatch)
            ready = 0; barrier = asyncio.Event()
            async def contend(closing):
                nonlocal ready
                async with await client.start_session() as session:
                    session.start_transaction()
                    budget = await scope.resolve(db, domain.document(w, g), clock[0], session=session, starting=True)
                    ready += 1
                    if ready == 2: barrier.set()
                    await asyncio.wait_for(barrier.wait(), 5)
                    try:
                        if closing:
                            changed = await db[scope.GRANTS].update_one({'_id': g['_id'], 'epoch': 0, 'state': 'OPEN'},
                                {'$set': {'state': 'CLOSED', 'closed_at': clock[0]}, '$inc': {'epoch': 1}}, session=session)
                            assert changed.modified_count == 1
                        else: await budget.claim(session, starting=True)
                        await session.commit_transaction(); return True
                    except (Error, PyMongoError) as exc:
                        if isinstance(exc, PyMongoError):
                            assert exc.has_error_label('TransientTransactionError') or getattr(exc, 'code', None) == 112
                        if session.in_transaction: await session.abort_transaction()
                        return False
            outcomes = await asyncio.wait_for(asyncio.gather(contend(False), contend(True)), 15)
            assert sum(outcomes) == 1
            actual = await db[scope.WORKFLOWS].find_one({'_id': w['_id']})
            grant = await db[scope.GRANTS].find_one({'_id': g['_id']})
            assert grant['epoch'] == 1 and actual['starts_used'] in (0, 1)
            assert actual['starts_used'] == (0 if grant['state'] == 'CLOSED' else 1)
    asyncio.run(case())


@pytest.mark.parametrize('termination', ['grant-revoked', 'grant-expired', 'auth-revoked'])
def test_real_sredni_termination_settles_cutoff_and_denies_future_access(monkeypatch, termination):
    async def case():
        def short(fake, w, g):
            if termination == 'grant-expired':
                w['expires_at'] = g['expires_at'] = w['created_at'] + timedelta(seconds=3)
        async with isolated_database(OWNED_PREFIX, retryWrites=False, retryReads=False, tz_aware=True) as (client, db):
            clock, w, g = await setup(db, monkeypatch, prepare=short); svc = service(db, client)
            lease = await start(svc, w, g); await svc.renew_lease(**domain.renewal(lease))
            if termination == 'grant-revoked':
                clock[0] += timedelta(microseconds=600000)
                await db[scope.GRANTS].update_one({'_id': g['_id']}, {'$set': {'state': 'REVOKED', 'revoked_at': clock[0]}, '$inc': {'epoch': 1}})
                clock[0] += timedelta(seconds=5)
                assert (await svc.renew_lease(**domain.renewal(lease, 2)))['status'] == 'Exhausted'
                expected = 600000
            elif termination == 'grant-expired':
                clock[0] += timedelta(seconds=3); await end(svc, lease); expected = 2000000
            else:
                clock[0] += timedelta(microseconds=1200000)
                await svc.revoke_auth_session(user_id='user-1', auth_session_id='auth-1'); expected = 1200000
            actual = await db[scope.WORKFLOWS].find_one({'_id': w['_id']})
            assert actual['used_microseconds'] == expected
            doc = await db.reading_pass_sessions.find_one({'id': lease['session_id']})
            before = await rows(db)
            with pytest.raises(Error): await scope.resolve(db, doc, clock[0], current_access=True)
            assert await rows(db) == before
    asyncio.run(case())


def test_real_sredni_original_window_rejects_901_seconds_without_mutation(monkeypatch):
    async def case():
        async with isolated_database(OWNED_PREFIX, retryWrites=False, retryReads=False, tz_aware=True) as (client, db):
            clock, w, g = await setup(db, monkeypatch)
            await db[scope.WORKFLOWS].update_one({'_id': w['_id']}, {'$set': {'expires_at': w['created_at'] + timedelta(seconds=901)}})
            before = await rows(db)
            with pytest.raises(Error): await scope.resolve(db, domain.document(w, g), clock[0], starting=True)
            assert await rows(db) == before
    asyncio.run(case())


@pytest.mark.parametrize('outcome', ['normal-settled-close', 'lost-provision-response', 'malformed-retained-history'])
def test_real_sredni_operator_namespace_provision_close_and_unknown_status(monkeypatch, outcome):
    async def case():
        from motor.motor_asyncio import AsyncIOMotorClientSession
        async with isolated_database(OWNED_PREFIX, retryWrites=False, retryReads=False, tz_aware=True) as (client, db):
            clock, _, _ = await setup(db, monkeypatch, empty=True)
            a = fixtures.admitted(clock[0]); book = fixtures.book()
            namespace = replace(a, action='prepare-namespace')
            assert (await operator.prepare_namespace_one_shot(db, client, namespace, book))['qualified']
            if outcome == 'malformed-retained-history':
                await db[operator.OPERATIONS].insert_one({'_id': 'SYNTHETIC-old', 'user_id': a.user_id,
                    'owner_receipt_sha256': a.owner_receipt_sha256})
                before = await rows(db)
                with pytest.raises(operator.OperatorStop, match='NO_RESET'):
                    await operator.execute_one_shot(db, client, a, book)
                assert await rows(db) == before
                return
            commits = []; original = AsyncIOMotorClientSession.commit_transaction
            if outcome == 'lost-provision-response':
                async def lost_after_real_commit(session):
                    commits.append(True); await original(session)
                    raise operator.OutcomeUnknown('SYNTHETIC_REAL_COMMIT_RESPONSE_LOST')
                monkeypatch.setattr(AsyncIOMotorClientSession, 'commit_transaction', lost_after_real_commit)
                with pytest.raises(operator.OutcomeUnknown, match='COMMIT_OUTCOME_UNKNOWN'):
                    await operator.execute_one_shot(db, client, a, book)
                assert commits == [True]
                monkeypatch.setattr(AsyncIOMotorClientSession, 'commit_transaction', original)
                observed = await operator.status(db, client, a)
                assert observed['status'] == 'COMMIT_RECEIPT_OBSERVED' and observed['replay_permitted'] is False
                before = await rows(db)
                with pytest.raises(operator.OperatorStop): await operator.execute_one_shot(db, client, a, book)
                assert await rows(db) == before and commits == [True]
                return
            result = await operator.execute_one_shot(db, client, a, book)
            assert result['status'] == 'COMMIT_RECEIPT_OBSERVED'
            w = await db[scope.WORKFLOWS].find_one({})
            g = await db[scope.GRANTS].find_one({})
            svc = service(db, client); lease = await start(svc, w, g)
            await svc.renew_lease(**domain.renewal(lease)); clock[0] += timedelta(microseconds=1200000)
            before_end = replace(a, operation_id='SYNTHETIC-close-000001', action='close', grant_id=g['_id'],
                expected_state_sha256=operator.state_hash(await db[scope.WORKFLOWS].find_one({}), [await db[scope.GRANTS].find_one({})]))
            with pytest.raises(operator.OperatorStop, match='SETTLEMENT'):
                await operator.execute_one_shot(db, client, before_end, book)
            await end(svc, lease)
            w = await db[scope.WORKFLOWS].find_one({}); g = await db[scope.GRANTS].find_one({})
            close = replace(before_end, expected_state_sha256=operator.state_hash(w, [g]))
            assert (await operator.execute_one_shot(db, client, close, book))['status'] == 'COMMIT_RECEIPT_OBSERVED'
            final = await db[scope.WORKFLOWS].find_one({})
            assert (final['used_microseconds'], final['used_credit_seconds'], final['starts_used']) == (1200000, 1, 1)
            assert (await db[scope.GRANTS].find_one({}))['state'] == 'CLOSED'
            assert (await db.users.find_one({'id': 'user-1'}))['reading_seconds_balance'] == 299
            assert await db[operator.OPERATIONS].count_documents({}) == 2
    asyncio.run(case())
