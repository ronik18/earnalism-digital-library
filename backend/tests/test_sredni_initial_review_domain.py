"""Synthetic dedicated scope + real service composition, never live authority.

No Mongo, account, provider, real identity or wallet correction is performed.
The committed authority contains one approved opaque pair; synthetic positive rows
are test-only. EMPTY predecessor denial is exercised independently.
"""
import asyncio
import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import reading_pass_service as service_module
import sredni_initial_review_scope as scope
from domain.reading_pass import ReadingPassConfig, ReadingPassError
from backend.tests.test_reading_pass_service_concurrency import Database, Collection


class Session:
    def __init__(self, client):
        self.client, self.in_transaction, self.committed = client, False, False
    async def __aenter__(self): return self
    async def __aexit__(self, *_): return None
    def start_transaction(self):
        self.in_transaction = True
        self.before = {k: copy.deepcopy(v.rows) for k, v in vars(self.client.db).items() if isinstance(v, Collection)}
    async def abort_transaction(self):
        for k, rows in self.before.items(): getattr(self.client.db, k).rows = copy.deepcopy(rows)
        self.in_transaction = False
    async def commit_transaction(self):
        self.client.commits += 1
        self.in_transaction = False
        if getattr(self.client, 'unknown_forever', False) or self.client.unknown_once and not self.committed:
            self.committed = True
            raise UnknownCommit()


class UnknownCommit(Exception):
    def has_error_label(self, name): return name == 'UnknownTransactionCommitResult'


class Client:
    def __init__(self, db, *, unknown_once=False):
        self.db, self.unknown_once, self.commits = db, unknown_once, 0
    async def start_session(self): return Session(self)


def seeded(now):
    db = Database(balance=300)
    db.user_sessions.rows.append({'id': 'auth-1', 'user_id': 'user-1', 'status': 'active',
        'idle_expires_at': now + timedelta(hours=1), 'absolute_expires_at': now + timedelta(hours=1)})
    owner = '1' * 64; identity = scope.identity_binding('user-1', 'auth-1')
    common = {'user_id': 'user-1', 'auth_session_id': 'auth-1', 'owner_receipt_sha256': owner,
        'identity_binding_sha256': identity, 'slug': scope.profile.SLUG,
        'descriptor_sha256': scope.profile.DESCRIPTOR, 'package_version': scope.profile.PACKAGE,
        'country': 'IN', 'created_at': now - timedelta(seconds=1), 'expires_at': now + timedelta(seconds=899)}
    w = {**common, '_id': scope.workflow_id(owner, 'user-1'), 'schema': scope.WORKFLOW_SCHEMA,
        'maximum_seconds': 60, 'maximum_microseconds': 60000000, 'maximum_starts': 3,
        'used_microseconds': 0, 'used_credit_seconds': 0, 'starts_used': 0, 'revision': 0}
    g = {**common, '_id': 'SYNTHETIC-sredni-grant', 'schema': scope.GRANT_SCHEMA,
         'workflow_id': w['_id'], 'state': 'OPEN', 'epoch': 0}
    db[scope.WORKFLOWS].rows.append(w); db[scope.GRANTS].rows.append(g)
    return db, w, g


def server_scope(w, g):
    return {scope.SCOPE_KEY: g['_id'], scope.WORKFLOW_KEY: w['_id'],
        'acceptance_test_id': scope.profile.TEST_ID, 'manifest_version': scope.profile.PACKAGE,
        'package_version': scope.profile.PACKAGE, 'segmentation_version': scope.profile.DESCRIPTOR,
        'release_descriptor_sha256': scope.profile.DESCRIPTOR, 'release_country': 'IN'}


def document(w, g):
    return {'user_id': 'user-1', 'auth_session_id': 'auth-1', 'content_type': 'audio',
        'content_id': scope.profile.SLUG, 'acceptance_test_id': scope.profile.TEST_ID, 'scope': server_scope(w, g)}


def synthetic_policy(monkeypatch, g):
    monkeypatch.setattr(scope, 'load_authority', lambda: {'schema': scope.AUTHORITY_SCHEMA, 'accepted': [{
        'owner_receipt_sha256': g['owner_receipt_sha256'], 'identity_binding_sha256': g['identity_binding_sha256']}]})


async def started(monkeypatch, *, before=None, unknown_once=False):
    clock = [datetime.now(timezone.utc)]; db, w, g = seeded(clock[0]); synthetic_policy(monkeypatch, g)
    monkeypatch.setattr(service_module, '_now', lambda: clock[0]); monkeypatch.setattr(scope, '_now', lambda: clock[0])
    if before: before(db, w, g)
    service = service_module.ReadingPassService(db=db, client=Client(db, unknown_once=unknown_once),
        config=ReadingPassConfig(), token_secret='SYNTHETIC-ONLY')
    lease = await service.start_session(user_id='user-1', auth_session_id='auth-1', device_id='test-device',
        device_label='Synthetic', content_type='audio', content_id=scope.profile.SLUG, scope=server_scope(w, g))
    return clock, db, service, lease


def renewal(lease, version=1, **changes):
    return {'user_id': 'user-1', 'auth_session_id': 'auth-1', 'session_id': lease['session_id'],
        'lease_token': lease['lease_token'], 'lease_version': version, 'sequence': version,
        'idempotency_key': f'synthetic-{version}', 'active': True, 'playback_state': 'playing', **changes}


def snapshot(db): return {k: copy.deepcopy(v.rows) for k, v in vars(db).items() if isinstance(v, Collection)}


def test_source_authority_empty_and_no_client_or_old120_constructor_authority(monkeypatch):
    predecessor = Path(__file__).resolve().parents[2] / 'internal/legal/sredni_initial_review_20261103/pre-approval-authority.json'
    monkeypatch.setattr(scope, 'AUTHORITY_PATH', predecessor)
    assert scope.load_authority() == {'schema': scope.AUTHORITY_SCHEMA, 'accepted': []}
    with pytest.raises(ReadingPassError):
        scope.SredniReviewBudget(None, {}, {}, {}, cutoff=datetime.now(timezone.utc))
    async def run():
        class NoQueries:
            def __getattr__(self, name): raise AssertionError('NO_DB_READ_BEFORE_AUTHORITY')
        with pytest.raises(ReadingPassError):
            await scope.resolve(NoQueries(), {'scope': {scope.SCOPE_KEY: 'forged'}}, datetime.now(timezone.utc))
        monkeypatch.setattr(scope.profile, 'candidate', lambda *_: (_ for _ in ()).throw(AssertionError('NO_PROFILE_BEFORE_AUTHORITY')))
        assert await scope.member_budget(NoQueries(), {}, 'user-1', 'auth-1', country='IN', now=datetime.now(timezone.utc)) is None
    asyncio.run(run())


@pytest.mark.parametrize('change', ['user', 'auth', 'package', 'country', 'old_scope', 'missing_grant', 'wrong_workflow'])
def test_exact_identity_scope_and_missing_metadata_fail_closed(monkeypatch, change):
    async def run():
        now = datetime.now(timezone.utc); db, w, g = seeded(now); synthetic_policy(monkeypatch, g); doc = document(w, g)
        if change == 'user': doc['user_id'] = 'other-user'
        elif change == 'auth': doc['auth_session_id'] = 'other-session'
        elif change == 'package': doc['scope']['package_version'] = 'sha256-' + '0' * 64
        elif change == 'country': doc['scope']['release_country'] = 'US'
        elif change == 'old_scope': doc['scope']['native_audio_review_grant_id'] = 'old120'
        elif change == 'missing_grant': db[scope.GRANTS].rows.clear()
        else: db[scope.WORKFLOWS].rows.clear()
        before = snapshot(db)
        with pytest.raises(ReadingPassError): await scope.resolve(db, doc, now, starting=True)
        assert snapshot(db) == before
    asyncio.run(run())


def test_known_accepted_identity_hash_cannot_be_copied_to_another_member(monkeypatch):
    now = datetime.now(timezone.utc); db, w, g = seeded(now); synthetic_policy(monkeypatch, g)
    changed = {**g, 'user_id': 'other-user'}
    with pytest.raises(ReadingPassError): scope.authority_allows(changed)
    assert scope.workflow_id(g['owner_receipt_sha256'], 'user-1') == w['_id']
    assert scope.identity_binding('user-1', 'other-login') != g['identity_binding_sha256']


@pytest.mark.parametrize('field,value', [('used_microseconds', -1), ('used_microseconds', 60000001),
    ('used_credit_seconds', 61), ('starts_used', 4), ('starts_used', True), ('maximum_seconds', 120), ('revision', -1)])
def test_invalid_or_expanded_counter_denied(field, value):
    _, w, _ = seeded(datetime.now(timezone.utc)); w[field] = value
    with pytest.raises(ReadingPassError): scope.validate_workflow(w)


@pytest.mark.parametrize('cap', [None, {'status': 'disabled', 'maximum_seconds': 600}, {'status': 'enabled', 'maximum_seconds': 600}])
def test_retained_account_cap_is_preserved_and_incompatible_not_overridden(monkeypatch, cap):
    async def run():
        now = datetime.now(timezone.utc); db, w, g = seeded(now); synthetic_policy(monkeypatch, g)
        db.users.rows[0]['reader_acceptance_budget'] = cap; before = snapshot(db)
        service = service_module.ReadingPassService(db=db, client=Client(db), config=ReadingPassConfig(), token_secret='test')
        with pytest.raises(ReadingPassError):
            await service.start_session(user_id='user-1', auth_session_id='auth-1', device_id='x', device_label='x',
                content_type='audio', content_id=scope.profile.SLUG, scope=server_scope(w, g))
        assert snapshot(db) == before
    asyncio.run(run())


def test_two_stale_start_claims_cannot_exceed_three_or_race_grant_close(monkeypatch):
    async def run():
        now = datetime.now(timezone.utc); db, w, g = seeded(now); synthetic_policy(monkeypatch, g); w['starts_used'] = 2
        a = await scope.resolve(db, document(w, g), now, starting=True)
        b = await scope.resolve(db, document(w, g), now, starting=True)
        transaction = SimpleNamespace(in_transaction=True)
        await a.claim(transaction, starting=True)
        with pytest.raises(ReadingPassError): await b.claim(transaction, starting=True)
        assert w['starts_used'] == 3
        with pytest.raises(ReadingPassError): await scope.resolve(db, document(w, g), now, starting=True)
        # A separately resolved interval cannot write through an intervening close.
        c = await scope.resolve(db, document(w, g), now)
        g.update(state='CLOSED', closed_at=now, epoch=g['epoch'] + 1)
        before = copy.deepcopy(w)
        with pytest.raises(ReadingPassError): await c.interval(100000, transaction)
        assert w == before
    asyncio.run(run())


def test_real_service_fraction_idempotency_terminal_and_dedicated_ledger_refs(monkeypatch):
    async def run():
        clock, db, service, lease = await started(monkeypatch)
        assert db[scope.WORKFLOWS].rows[0]['starts_used'] == 1
        await service.renew_lease(**renewal(lease)); clock[0] += timedelta(microseconds=900000)
        result = await service.renew_lease(**renewal(lease, 2)); assert result['deducted_seconds'] == 0
        before = snapshot(db); await service.renew_lease(**renewal(lease, 2)); assert snapshot(db) == before
        clock[0] += timedelta(microseconds=200000)
        await service.end_session(user_id='user-1', auth_session_id='auth-1', session_id=lease['session_id'])
        w = db[scope.WORKFLOWS].rows[0]
        assert (w['used_microseconds'], w['used_credit_seconds']) == (1100000, 1)
        assert db.users.rows[0]['reading_fractional_microseconds'] == 100000
        assert db.users.rows[0]['reading_seconds_balance'] == 299
        for refs in [db.wallet_transactions.rows[0], db.wallet_ledger.rows[0]['metadata']]:
            assert refs[scope.SCOPE_KEY] == 'SYNTHETIC-sredni-grant' and refs[scope.WORKFLOW_KEY] == w['_id']
            assert 'native_audio_review_grant_id' not in refs and 'native_audio_review_workflow_id' not in refs
        # Missing workflow after a real reference never makes this lease ordinary.
        db[scope.WORKFLOWS].rows.clear()
        with pytest.raises(ReadingPassError): await service._acceptance_budget(db.reading_pass_sessions.rows[0])
    asyncio.run(run())


def test_preexisting_fractional_carry_can_post_native_debit_without_hiding_native_time(monkeypatch):
    async def run():
        clock, db, service, lease = await started(monkeypatch, before=lambda db, w, g: db.users.rows[0].update(reading_fractional_microseconds=900000))
        await service.renew_lease(**renewal(lease)); clock[0] += timedelta(microseconds=200000)
        result = await service.renew_lease(**renewal(lease, 2)); assert result['deducted_seconds'] == 1
        assert db[scope.WORKFLOWS].rows[0]['used_microseconds'] == 200000
        assert db[scope.WORKFLOWS].rows[0]['used_credit_seconds'] == 1
        assert db.users.rows[0]['reading_fractional_microseconds'] == 100000
    asyncio.run(run())


def test_paused_buffering_and_prestream_time_free_then_resumed_time_is_metered(monkeypatch):
    async def run():
        clock, db, service, lease = await started(monkeypatch)
        clock[0] += timedelta(seconds=3); await service.renew_lease(**renewal(lease))
        clock[0] += timedelta(microseconds=700000)
        await service.renew_lease(**renewal(lease, 2, active=False, playback_state='paused'))
        clock[0] += timedelta(seconds=2)
        await service.renew_lease(**renewal(lease, 3, playback_state='buffering'))
        clock[0] += timedelta(seconds=2); await service.renew_lease(**renewal(lease, 4))
        clock[0] += timedelta(microseconds=400000)
        await service.end_session(user_id='user-1', auth_session_id='auth-1', session_id=lease['session_id'])
        w = db[scope.WORKFLOWS].rows[0]
        assert (w['used_microseconds'], w['used_credit_seconds']) == (1100000, 1)
    asyncio.run(run())


@pytest.mark.parametrize('limit_field', ['used_microseconds', 'used_credit_seconds'])
def test_stricter_cumulative_sixty_ceiling_never_reopens_on_new_session(monkeypatch, limit_field):
    async def run():
        def prepare(db, w, g): w[limit_field] = 59000000 if limit_field == 'used_microseconds' else 59
        clock, db, service, lease = await started(monkeypatch, before=prepare)
        await service.renew_lease(**renewal(lease)); clock[0] += timedelta(seconds=2)
        result = await service.renew_lease(**renewal(lease, 2)); assert result['status'] == 'Exhausted'
        w = db[scope.WORKFLOWS].rows[0]
        assert w['used_microseconds'] <= 60000000 and w['used_credit_seconds'] <= 60
        with pytest.raises(ReadingPassError):
            await service.start_session(user_id='user-1', auth_session_id='auth-1', device_id='x', device_label='x',
                content_type='audio', content_id=scope.profile.SLUG,
                scope=db.reading_pass_sessions.rows[0]['scope'])
        assert w['starts_used'] == 1
    asyncio.run(run())


def test_revoked_grant_settles_only_prior_fraction_and_denies_resume(monkeypatch):
    async def run():
        clock, db, service, lease = await started(monkeypatch)
        await service.renew_lease(**renewal(lease)); clock[0] += timedelta(microseconds=600000)
        g = db[scope.GRANTS].rows[0]; g.update(state='REVOKED', revoked_at=clock[0], epoch=g['epoch'] + 1)
        clock[0] += timedelta(seconds=5)
        result = await service.renew_lease(**renewal(lease, 2)); assert result['status'] == 'Exhausted'
        assert db[scope.WORKFLOWS].rows[0]['used_microseconds'] == 600000
        assert db.users.rows[0]['reading_fractional_microseconds'] == 600000
        with pytest.raises(ReadingPassError): await scope.resolve(db, db.reading_pass_sessions.rows[0], clock[0], current_access=True)
    asyncio.run(run())


def test_expiry_and_auth_revoke_settle_accrued_usage_without_future_access(monkeypatch):
    async def run():
        def short(db, w, g): w['expires_at'] = g['expires_at'] = g['created_at'] + timedelta(seconds=3)
        clock, db, service, lease = await started(monkeypatch, before=short)
        await service.renew_lease(**renewal(lease)); clock[0] += timedelta(seconds=3)
        await service.end_session(user_id='user-1', auth_session_id='auth-1', session_id=lease['session_id'])
        assert db[scope.WORKFLOWS].rows[0]['used_microseconds'] == 2000000
        assert db[scope.WORKFLOWS].rows[0]['used_credit_seconds'] <= 2
        # A separate fixture exercises the normal auth-session revoke transaction.
        clock, db, service, lease = await started(monkeypatch)
        await service.renew_lease(**renewal(lease)); clock[0] += timedelta(microseconds=1200000)
        await service.revoke_auth_session(user_id='user-1', auth_session_id='auth-1')
        assert db[scope.WORKFLOWS].rows[0]['used_microseconds'] == 1200000
        assert db.user_sessions.rows[0]['status'] == 'revoked'
        assert db.reading_pass_sessions.rows[0]['status'] == 'revoked'
    asyncio.run(run())


def test_expired_auth_uses_exact_original_auth_deadline_for_historic_settlement(monkeypatch):
    async def run():
        clock, db, service, lease = await started(monkeypatch)
        await service.renew_lease(**renewal(lease))
        db.user_sessions.rows[0]['idle_expires_at'] = clock[0] + timedelta(seconds=2)
        db.user_sessions.rows[0]['status'] = 'expired'
        clock[0] += timedelta(seconds=3)
        await service.end_session(user_id='user-1', auth_session_id='auth-1', session_id=lease['session_id'])
        assert db[scope.WORKFLOWS].rows[0]['used_microseconds'] == 2000000
        assert db[scope.WORKFLOWS].rows[0]['used_credit_seconds'] == 2
    asyncio.run(run())


def test_wallet_failure_rolls_back_counter_epoch_carry_session_and_ledger(monkeypatch):
    async def run():
        clock, db, service, lease = await started(monkeypatch)
        await service.renew_lease(**renewal(lease)); clock[0] += timedelta(microseconds=1300000)
        before = snapshot(db); original = db.users.update_one
        async def fail(query, change, **kw):
            if 'reading_seconds_balance' in change.get('$inc', {}): return SimpleNamespace(modified_count=0)
            return await original(query, change, **kw)
        monkeypatch.setattr(db.users, 'update_one', fail)
        with pytest.raises(ReadingPassError): await service.renew_lease(**renewal(lease, 2))
        assert snapshot(db) == before
    asyncio.run(run())


def test_unknown_commit_retries_same_commit_not_start_or_counter_callback(monkeypatch):
    async def run():
        _, db, service, _ = await started(monkeypatch, unknown_once=True)
        assert service.client.commits == 2
        assert db[scope.WORKFLOWS].rows[0]['starts_used'] == 1
        assert len(db.reading_pass_sessions.rows) == 1
        assert db.wallet_ledger.rows == []
    asyncio.run(run())


def test_failed_session_insert_rolls_back_start_reservation_and_epoch(monkeypatch):
    async def run():
        now = datetime.now(timezone.utc); db, w, g = seeded(now); synthetic_policy(monkeypatch, g)
        before = snapshot(db)
        async def fail(*args, **kw): raise RuntimeError('SYNTHETIC_INSERT_FAILURE')
        monkeypatch.setattr(db.reading_pass_sessions, 'insert_one', fail)
        service = service_module.ReadingPassService(db=db, client=Client(db), config=ReadingPassConfig(), token_secret='test')
        with pytest.raises(RuntimeError, match='SYNTHETIC_INSERT_FAILURE'):
            await service.start_session(user_id='user-1', auth_session_id='auth-1', device_id='x', device_label='x',
                content_type='audio', content_id=scope.profile.SLUG, scope=server_scope(w, g))
        assert snapshot(db) == before
    asyncio.run(run())


def test_unresolved_commit_never_replays_start_or_resets_retained_counters(monkeypatch):
    async def run():
        now = datetime.now(timezone.utc); db, w, g = seeded(now); synthetic_policy(monkeypatch, g)
        client = Client(db); client.unknown_forever = True
        service = service_module.ReadingPassService(db=db, client=client, config=ReadingPassConfig(), token_secret='test')
        with pytest.raises(UnknownCommit):
            await service.start_session(user_id='user-1', auth_session_id='auth-1', device_id='x', device_label='x',
                content_type='audio', content_id=scope.profile.SLUG, scope=server_scope(w, g))
        assert client.commits == 3 and len(db.reading_pass_sessions.rows) == 1
        assert db[scope.WORKFLOWS].rows[0]['starts_used'] == 1
        assert db[scope.GRANTS].rows[0]['epoch'] == 1
    asyncio.run(run())


def test_ordinary_audio_preserves_ledger_structure_and_never_touches_dedicated_rows(monkeypatch):
    async def run():
        now = datetime.now(timezone.utc); db, w, g = seeded(now); before = copy.deepcopy((w, g)); clock = [now]
        monkeypatch.setattr(service_module, '_now', lambda: clock[0])
        service = service_module.ReadingPassService(db=db, client=Client(db), config=ReadingPassConfig(), token_secret='test')
        lease = await service.start_session(user_id='user-1', auth_session_id='auth-1', device_id='x', device_label='x',
            content_type='audio', content_id='ordinary-title', scope={})
        await service.renew_lease(**renewal(lease)); clock[0] += timedelta(seconds=2)
        await service.end_session(user_id='user-1', auth_session_id='auth-1', session_id=lease['session_id'])
        assert (db[scope.WORKFLOWS].rows[0], db[scope.GRANTS].rows[0]) == before
        assert all(scope.SCOPE_KEY not in row and scope.WORKFLOW_KEY not in row for row in db.wallet_transactions.rows)
        assert all(scope.SCOPE_KEY not in row['metadata'] for row in db.wallet_ledger.rows)
        assert db.users.rows[0]['reading_seconds_balance'] == 298
    asyncio.run(run())


@pytest.mark.parametrize('carry', [-1, 1000000, True, '900000'])
def test_invalid_current_carry_denies_start_without_repair(monkeypatch, carry):
    async def run():
        now = datetime.now(timezone.utc); db, w, g = seeded(now); synthetic_policy(monkeypatch, g)
        db.users.rows[0]['reading_fractional_microseconds'] = carry; before = snapshot(db)
        with pytest.raises(ReadingPassError): await scope.resolve(db, document(w, g), now, starting=True)
        assert snapshot(db) == before
    asyncio.run(run())


def test_changed_current_auth_denies_protected_resume_without_counter_reset(monkeypatch):
    async def run():
        _, db, service, lease = await started(monkeypatch)
        db.users.rows[0]['active_user_session_id'] = 'another-login'
        before = snapshot(db)
        with pytest.raises(ReadingPassError):
            await service.authorize(user_id='user-1', auth_session_id='auth-1', session_id=lease['session_id'],
                lease_token=lease['lease_token'], content_type='audio', content_id=scope.profile.SLUG)
        assert snapshot(db) == before
    asyncio.run(run())


def test_three_full_service_starts_share_one_workflow_and_fourth_is_denied(monkeypatch):
    async def run():
        _, db, service, lease = await started(monkeypatch)
        for ordinal in range(1, 4):
            assert db[scope.WORKFLOWS].rows[0]['starts_used'] == ordinal
            if ordinal == 3:
                # Metadata is a read, not a fourth start. The current third
                # lease retains exact selected credits while quota is full.
                import json
                book = json.loads((Path(__file__).parent/'fixtures/sredni-initial-sourceqa-staged-book.json').read_text())
                before_metadata = snapshot(db)
                budget = await scope.member_budget(db, book, 'user-1', 'auth-1', country='IN', now=scope._now())
                metadata = scope.profile.listener_metadata_from_verified_budget(book, budget, country='IN', now=scope._now())
                assert metadata['package_version'] == scope.profile.PACKAGE
                assert metadata['narration_disclosure'] == scope.profile.DISCLOSURE
                assert snapshot(db) == before_metadata and not db.wallet_ledger.rows
            await service.end_session(user_id='user-1', auth_session_id='auth-1', session_id=lease['session_id'])
            if ordinal < 3:
                lease = await service.start_session(user_id='user-1', auth_session_id='auth-1', device_id='x', device_label='x',
                    content_type='audio', content_id=scope.profile.SLUG, scope=db.reading_pass_sessions.rows[0]['scope'])
        before = snapshot(db)
        with pytest.raises(ReadingPassError):
            await service.start_session(user_id='user-1', auth_session_id='auth-1', device_id='x', device_label='x',
                content_type='audio', content_id=scope.profile.SLUG, scope=db.reading_pass_sessions.rows[0]['scope'])
        assert snapshot(db) == before
        assert len(db[scope.WORKFLOWS].rows) == 1 and not db.wallet_ledger.rows
    asyncio.run(run())


def test_ordinary_fraction_interleaving_preserves_native_own_time_and_posted_debits(monkeypatch):
    async def run():
        clock, db, service, lease = await started(monkeypatch)
        native_scope = copy.deepcopy(db.reading_pass_sessions.rows[0]['scope'])
        await service.renew_lease(**renewal(lease)); clock[0] += timedelta(microseconds=900000)
        await service.end_session(user_id='user-1', auth_session_id='auth-1', session_id=lease['session_id'])
        assert db.users.rows[0]['reading_fractional_microseconds'] == 900000
        ordinary = await service.start_session(user_id='user-1', auth_session_id='auth-1', device_id='x', device_label='x',
            content_type='audio', content_id='ordinary-title', scope={})
        await service.renew_lease(**renewal(ordinary)); clock[0] += timedelta(microseconds=200000)
        await service.end_session(user_id='user-1', auth_session_id='auth-1', session_id=ordinary['session_id'])
        assert (db[scope.WORKFLOWS].rows[0]['used_microseconds'], db[scope.WORKFLOWS].rows[0]['used_credit_seconds']) == (900000, 0)
        assert db.users.rows[0]['reading_fractional_microseconds'] == 100000
        again = await service.start_session(user_id='user-1', auth_session_id='auth-1', device_id='x', device_label='x',
            content_type='audio', content_id=scope.profile.SLUG, scope=native_scope)
        await service.renew_lease(**renewal(again)); clock[0] += timedelta(microseconds=900000)
        await service.end_session(user_id='user-1', auth_session_id='auth-1', session_id=again['session_id'])
        w = db[scope.WORKFLOWS].rows[0]
        assert (w['used_microseconds'], w['used_credit_seconds'], w['starts_used']) == (1800000, 1, 2)
        assert db.users.rows[0]['reading_fractional_microseconds'] == 0
        assert sum(row['debit'] for row in db.wallet_ledger.rows) == 2
        assert db.users.rows[0]['reading_seconds_balance'] == 298
    asyncio.run(run())


def test_committed_authority_binds_only_actual_approved_opaque_pair_and_preserves_predecessor():
    root = Path(__file__).resolve().parents[2]
    record = json.loads((root / 'internal/legal/sredni_initial_review_20261103/source-authority-successor.json').read_text())
    for path_key, hash_key in [('owner_permission_path', 'owner_receipt_sha256'), ('predecessor_path', 'predecessor_sha256'), ('successor_path', 'successor_sha256')]:
        assert hashlib.sha256((root / record[path_key]).read_bytes()).hexdigest() == record[hash_key]
    owner = json.loads((root / record['owner_permission_path']).read_text())
    assert owner['status'] == 'APPROVED' and owner['answer'] == 'Approve this bounded Sredni scope'
    assert owner['question_sha256'] == hashlib.sha256(owner['question'].encode()).hexdigest()
    assert (owner['maximum_seconds'], owner['maximum_billable_microseconds'], owner['maximum_posted_credit_seconds'], owner['maximum_starts'], owner['maximum_grant_lifetime_seconds']) == (60, 60000000, 60, 3, 900)
    assert owner['startup_policy_q8628_approved'] is False
    assert owner['mutations_and_listening_require_merged_source_startup_recovery_india_rights'] is True
    assert json.loads((root / record['predecessor_path']).read_text()) == {'schema': scope.AUTHORITY_SCHEMA, 'accepted': []}
    assert scope.load_authority() == {'schema': scope.AUTHORITY_SCHEMA, 'accepted': [{'owner_receipt_sha256': record['owner_receipt_sha256'], 'identity_binding_sha256': record['identity_binding_sha256']}]}
    assert record['database_grant_playback_or_deployment_performed'] is False
    assert record['startup_policy_q8628_approved'] is False
    assert record['requires_actual_serving_startup_recovery_india_rights_and_execution_admission'] is True
    assert scope.authority_allows({'user_id': 'unapproved-source-test-user', 'auth_session_id': 'unapproved-source-test-session', 'owner_receipt_sha256': record['owner_receipt_sha256'], 'identity_binding_sha256': scope.identity_binding('unapproved-source-test-user', 'unapproved-source-test-session')}) is False
