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


def test_real_stable_account_first_provisions_race_once_without_retry(monkeypatch):
    async def case():
        from motor.motor_asyncio import AsyncIOMotorClientSession
        async with isolated_database(OWNED_PREFIX, retryWrites=False, retryReads=False, tz_aware=True) as (client, db):
            clock, _, _ = await setup(db, monkeypatch, empty=True)
            first = fixtures.admitted(clock[0]); candidate = fixtures.book()
            assert (await operator.prepare_namespace_one_shot(
                db, client, replace(first, action='prepare-namespace'), candidate))['qualified']
            initial_user = await db.users.find_one({'id': first.user_id})
            snapshot = operator.snapshot; ready = 0; both_read = asyncio.Event()
            async def simultaneous_snapshot(database, admission, session=None):
                nonlocal ready
                value = await snapshot(database, admission, session)
                # Synchronize only the first two actual provision snapshots.
                # Later status readback must not participate in this barrier.
                if admission.action == 'provision' and ready < 2:
                    assert value[1] is None and value[2] == []
                    ready += 1
                    if ready == 2: both_read.set()
                    await asyncio.wait_for(both_read.wait(), 5)
                return value
            monkeypatch.setattr(operator, 'snapshot', simultaneous_snapshot)
            commits = []; attempted = []
            commit = AsyncIOMotorClientSession.commit_transaction
            async def counted_commit(session):
                await commit(session); commits.append(True)
            monkeypatch.setattr(AsyncIOMotorClientSession, 'commit_transaction', counted_commit)
            async def provision(ordinal):
                attempted.append(ordinal)
                admission = replace(first, operation_id=f'SYNTHETIC-first-race-{ordinal:04}')
                return await operator.execute_one_shot(db, client, admission, candidate)
            outcomes = await asyncio.wait_for(asyncio.gather(
                provision(1), provision(2), return_exceptions=True), 20)
            successes = [x for x in outcomes if isinstance(x, dict)]
            failures = [x for x in outcomes if isinstance(x, BaseException)]
            assert len(successes) == len(failures) == len(commits) == 1
            assert successes[0]['status'] == 'COMMIT_RECEIPT_OBSERVED'
            loser = failures[0]
            assert not isinstance(loser, operator.OutcomeUnknown)
            assert isinstance(loser, (operator.OperatorStop, PyMongoError))
            if isinstance(loser, PyMongoError):
                assert loser.has_error_label('TransientTransactionError') or getattr(loser, 'code', None) in (112, 11000)
            else:
                assert any(code in str(loser) for code in ('STATE_CHANGED', 'NO_RESET', 'FIRST_GRANT'))
            assert attempted == [1, 2] and ready == 2
            assert await db[scope.WORKFLOWS].count_documents({}) == 1
            assert await db[scope.GRANTS].count_documents({}) == 1
            assert await db[operator.OPERATIONS].count_documents({}) == 1
            w = await db[scope.WORKFLOWS].find_one({})
            assert (w['used_microseconds'], w['used_credit_seconds'], w['starts_used']) == (0, 0, 0)
            assert w['created_at'] == clock[0] and w['expires_at'] == first.grant_expires_at
            assert await db.users.find_one({'id': first.user_id}) == initial_user
            assert await db.wallet_ledger.count_documents({}) == 0
            assert await db.wallet_transactions.count_documents({}) == 0
    asyncio.run(case())


@pytest.mark.parametrize('rotate_session', [False, True])
def test_real_stable_account_closed_first_grant_never_reprovisions_or_moves(monkeypatch, rotate_session):
    async def case():
        async with isolated_database(OWNED_PREFIX, retryWrites=False, retryReads=False, tz_aware=True) as (client, db):
            clock, _, _ = await setup(db, monkeypatch, empty=True)
            a = fixtures.admitted(clock[0]); candidate = fixtures.book()
            assert (await operator.prepare_namespace_one_shot(db, client,
                replace(a, action='prepare-namespace'), candidate))['qualified']
            assert (await operator.execute_one_shot(db, client, a, candidate))['status'] == 'COMMIT_RECEIPT_OBSERVED'
            w = await db[scope.WORKFLOWS].find_one({}); g = await db[scope.GRANTS].find_one({})
            svc = service(db, client); lease = await start(svc, w, g)
            await svc.renew_lease(**domain.renewal(lease))
            clock[0] += timedelta(microseconds=1200000)
            await end(svc, lease)
            w = await db[scope.WORKFLOWS].find_one({}); g = await db[scope.GRANTS].find_one({})
            close = replace(a, operation_id='SYNTHETIC-stable-close-0001', action='close', grant_id=g['_id'],
                            expected_state_sha256=operator.state_hash(w, [g]))
            assert (await operator.execute_one_shot(db, client, close, candidate))['status'] == 'COMMIT_RECEIPT_OBSERVED'
            retained = await db[scope.WORKFLOWS].find_one({})
            assert (retained['used_microseconds'], retained['used_credit_seconds'], retained['starts_used']) == (1200000, 1, 1)
            user = await db.users.find_one({'id': a.user_id})
            assert user['reading_seconds_balance'] == 299 and user['reading_fractional_microseconds'] == 200000
            sid = a.auth_session_id
            if rotate_session:
                sid = 'SYNTHETIC-auth-next'
                login = await db.user_sessions.find_one({'id': a.auth_session_id})
                login.pop('_id', None); login.update(id=sid, status='active')
                await db.user_sessions.insert_one(login)
                await db.users.update_one({'id': a.user_id}, {'$set': {'active_user_session_id': sid}})
            current = replace(a, operation_id='SYNTHETIC-no-second-grant-0001', auth_session_id=sid,
                identity_binding_sha256=scope.identity_binding(a.user_id, sid),
                expected_state_sha256=operator.state_hash(retained, [await db[scope.GRANTS].find_one({})]))
            assert scope.authority_allows(operator.authority_row(current))
            assert operator.workflow_id(current) == retained['_id']
            before = await rows(db)
            with pytest.raises(operator.OperatorStop):
                await operator.execute_one_shot(db, client, current, candidate)
            assert await rows(db) == before
            # Full runtime identity never migrates with stable-account source trust.
            old_lease = domain.document(retained, await db[scope.GRANTS].find_one({}))
            old_lease['auth_session_id'] = sid
            with pytest.raises(Error):
                await scope.resolve(db, old_lease, clock[0], current_access=True)
            assert await rows(db) == before
            assert await db[scope.WORKFLOWS].find_one({}) == retained
            assert await db[scope.GRANTS].count_documents({}) == 1
            assert await db[operator.OPERATIONS].count_documents({}) == 2
    asyncio.run(case())


def test_real_stable_account_workflow_without_grant_is_retained_not_reseeded(monkeypatch):
    async def case():
        def workflow_only(fake, workflow, grant):
            fake[scope.GRANTS].rows.clear()
            workflow.update(used_microseconds=1700000, used_credit_seconds=1, starts_used=1, revision=4)
        async with isolated_database(OWNED_PREFIX, retryWrites=False, retryReads=False, tz_aware=True) as (client, db):
            clock, w, _ = await setup(db, monkeypatch, prepare=workflow_only)
            a = fixtures.admitted(clock[0])
            assert (await operator.prepare_namespace_one_shot(db, client,
                replace(a, action='prepare-namespace'), fixtures.book()))['qualified']
            a = replace(a, operation_id='SYNTHETIC-workflow-only-0001',
                        expected_state_sha256=operator.state_hash(await db[scope.WORKFLOWS].find_one({}), []))
            before = await rows(db)
            with pytest.raises(operator.OperatorStop):
                await operator.execute_one_shot(db, client, a, fixtures.book())
            assert await rows(db) == before
            assert await db[scope.WORKFLOWS].count_documents({}) == 1
            assert await db[scope.GRANTS].count_documents({}) == 0
            assert await db[operator.OPERATIONS].count_documents({}) == 0
    asyncio.run(case())


@pytest.mark.parametrize('namespace', ['workflow', 'grant', 'operation'])
def test_real_stable_account_any_own_dedicated_history_denies_broken_linkage(monkeypatch, namespace):
    async def case():
        async with isolated_database(OWNED_PREFIX, retryWrites=False, retryReads=False, tz_aware=True) as (client, db):
            clock, _, _ = await setup(db, monkeypatch, empty=True)
            a = fixtures.admitted(clock[0]); candidate = fixtures.book()
            assert (await operator.prepare_namespace_one_shot(db, client,
                replace(a, action='prepare-namespace'), candidate))['qualified']
            collection = {'workflow': scope.WORKFLOWS, 'grant': scope.GRANTS,
                          'operation': operator.OPERATIONS}[namespace]
            # Own UID is decisive even when owner/wid/schema/content linkage is
            # absent or corrupt. It is not evidence of an unused allowance.
            await db[collection].insert_one({'_id': 'SYNTHETIC-broken-own-' + namespace,
                'user_id': a.user_id, 'owner_receipt_sha256': 'f' * 64,
                'workflow_id': 'SYNTHETIC-wrong-workflow', 'state': 'CLOSED'})
            _, w, grants = await operator.snapshot(db, a)
            denied = replace(a, operation_id='SYNTHETIC-own-history-denial-0001',
                             expected_state_sha256=operator.state_hash(w, grants))
            before = await rows(db)
            with pytest.raises(operator.OperatorStop):
                await operator.execute_one_shot(db, client, denied, candidate)
            assert await rows(db) == before
            assert await db[collection].count_documents({'user_id': a.user_id}) == 1
            assert await db[operator.OPERATIONS].count_documents({'_id': denied.operation_id}) == 0
    asyncio.run(case())


@pytest.mark.parametrize('namespace', ['reading_pass_sessions', 'wallet_ledger', 'wallet_transactions'])
@pytest.mark.parametrize('tag', ['grant-null', 'workflow-wrong'])
def test_real_stable_account_any_own_dedicated_tag_exists_denies_missing_content(monkeypatch, namespace, tag):
    async def case():
        async with isolated_database(OWNED_PREFIX, retryWrites=False, retryReads=False, tz_aware=True) as (client, db):
            clock, _, _ = await setup(db, monkeypatch, empty=True)
            a = fixtures.admitted(clock[0]); candidate = fixtures.book()
            assert (await operator.prepare_namespace_one_shot(db, client,
                replace(a, action='prepare-namespace'), candidate))['qualified']
            key = scope.SCOPE_KEY if tag == 'grant-null' else scope.WORKFLOW_KEY
            value = None if tag == 'grant-null' else 'SYNTHETIC-wrong-workflow'
            reference = {key: value}
            row = {'_id': 'SYNTHETIC-own-tag-' + namespace + '-' + tag, 'user_id': a.user_id}
            if namespace == 'reading_pass_sessions':
                row['scope'] = reference
                if tag == 'workflow-wrong': row['content_id'] = 'SYNTHETIC-wrong-title'
                field = 'scope.' + key
            elif namespace == 'wallet_ledger':
                row['metadata'] = reference
                if tag == 'workflow-wrong': row['metadata']['content_id'] = 'SYNTHETIC-wrong-title'
                field = 'metadata.' + key
            else:
                row.update(reference)
                if tag == 'workflow-wrong': row['content_id'] = 'SYNTHETIC-wrong-title'
                field = key
            await db[namespace].insert_one(row)
            # Actual Mongo $exists semantics: an explicit null is present.
            assert await db[namespace].count_documents({'user_id': a.user_id, field: {'$exists': True}}) == 1
            _, w, grants = await operator.snapshot(db, a)
            denied = replace(a, operation_id='SYNTHETIC-own-tag-denial-0001',
                             expected_state_sha256=operator.state_hash(w, grants))
            before = await rows(db)
            with pytest.raises(operator.OperatorStop):
                await operator.execute_one_shot(db, client, denied, candidate)
            assert await rows(db) == before
            assert await db[scope.WORKFLOWS].count_documents({}) == 0
            assert await db[scope.GRANTS].count_documents({}) == 0
            assert await db[operator.OPERATIONS].count_documents({}) == 0
    asyncio.run(case())


@pytest.mark.parametrize('namespace', ['workflow', 'grant', 'operation'])
def test_real_stable_account_owner_only_retained_history_without_uid_or_wid_denies(monkeypatch, namespace):
    async def case():
        async with isolated_database(OWNED_PREFIX, retryWrites=False, retryReads=False, tz_aware=True) as (client, db):
            clock, _, _ = await setup(db, monkeypatch, empty=True)
            a = fixtures.admitted(clock[0]); candidate = fixtures.book()
            assert (await operator.prepare_namespace_one_shot(db, client,
                replace(a, action='prepare-namespace'), candidate))['qualified']
            collection = {'workflow': scope.WORKFLOWS, 'grant': scope.GRANTS,
                          'operation': operator.OPERATIONS}[namespace]
            await db[collection].insert_one({'_id': 'SYNTHETIC-owner-only-' + namespace,
                'owner_receipt_sha256': a.owner_receipt_sha256})
            # A retained grant must be included in the observed state even if
            # both UID and workflow linkage are lost. Do not use an intentionally
            # stale expected hash to manufacture the denial under test.
            _, workflow, grants = await operator.snapshot(db, a)
            assert workflow is None
            assert len(grants) == (1 if namespace == 'grant' else 0)
            denied = replace(a, operation_id='SYNTHETIC-owner-only-denial-0001',
                             expected_state_sha256=operator.state_hash(workflow, grants))
            before = await rows(db)
            with pytest.raises(operator.OperatorStop):
                await operator.execute_one_shot(db, client, denied, candidate)
            assert await rows(db) == before
            assert await db[collection].count_documents({'owner_receipt_sha256': a.owner_receipt_sha256}) == 1
            assert await db[operator.OPERATIONS].count_documents({'_id': denied.operation_id}) == 0
    asyncio.run(case())
