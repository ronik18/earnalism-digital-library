"""Synthetic account only: cumulative budget across the existing lease machinery."""
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from backend import reading_pass_service as module
from backend.domain.reading_pass import ReadingPassConfig, ReadingPassError
from backend.reading_pass_service import ReadingPassService
from backend.tests.test_reading_pass_service_concurrency import Database, Client, _start_revocable_text


def budget(now, maximum=7):
    return dict(schema='reader-acceptance-budget.v1', user_id='user-1',
                content_type='text', content_id='book-1', test_id='synthetic-acceptance-1',
                manifest_version='fixture-manifest-v1', segmentation_version='fixture-v1',
                maximum_seconds=maximum, consumed_seconds=0, status='enabled',
                expires_at=now + timedelta(minutes=10))


async def fixture(monkeypatch, maximum=7):
    clock = [datetime(2026, 10, 20, tzinfo=timezone.utc)]
    monkeypatch.setattr(module, '_now', lambda: clock[0])
    db, client = Database(balance=120), Client()
    db.users.rows[0]['reader_acceptance_budget'] = budget(clock[0], maximum)
    service = ReadingPassService(db=db, client=client, config=ReadingPassConfig(), token_secret='synthetic')
    return clock, db, client, service


def renew(lease, sequence=1):
    return dict(user_id='user-1', auth_session_id='auth-1', session_id=lease['session_id'],
                lease_token=lease['lease_token'], lease_version=sequence, sequence=sequence,
                idempotency_key=f'acceptance-{sequence}', active=True, text_authority='allowed')


@pytest.mark.parametrize('maximum', [0, 7])
def test_zero_or_exact_boundary_and_no_restart_reset(monkeypatch, maximum):
    async def run():
        clock, db, client, service = await fixture(monkeypatch, maximum)
        if maximum == 0:
            with pytest.raises(ReadingPassError, match='exhausted'):
                await _start_revocable_text(service, db)
        else:
            lease = await _start_revocable_text(service, db)
            assert datetime.fromisoformat(lease['lease_expires_at']) == clock[0] + timedelta(seconds=7)
            clock[0] += timedelta(seconds=7)
            result = await service.renew_lease(**renew(lease))
            assert result['deducted_seconds'] == 7 and result['status'] == 'Exhausted'
            with pytest.raises(ReadingPassError):
                await service.renew_lease(**renew(lease))
            restarted = ReadingPassService(db=db, client=client, config=ReadingPassConfig(), token_secret='synthetic')
            with pytest.raises(ReadingPassError):
                await _start_revocable_text(restarted, db)
        user = db.users.rows[0]
        assert user['reader_acceptance_budget']['consumed_seconds'] == maximum
        assert user['reading_seconds_balance'] == user['wallet_seconds'] == 120 - maximum
        assert sum(x['debit'] for x in db.wallet_ledger.rows) == maximum
    asyncio.run(run())


def test_concurrent_renew_and_terminal_never_exceed_budget(monkeypatch):
    async def run():
        clock, db, _, service = await fixture(monkeypatch)
        lease = await _start_revocable_text(service, db)
        clock[0] += timedelta(seconds=7)
        await asyncio.gather(service.renew_lease(**renew(lease)), service.end_session(
            user_id='user-1', auth_session_id='auth-1', session_id=lease['session_id']), return_exceptions=True)
        assert db.users.rows[0]['reader_acceptance_budget']['consumed_seconds'] == 7
        assert db.users.rows[0]['reading_seconds_balance'] == 113
        assert sum(x['debit'] for x in db.wallet_ledger.rows) == 7
    asyncio.run(run())


def test_transfer_reuses_remaining_and_terminal_debit(monkeypatch):
    async def run():
        clock, db, _, service = await fixture(monkeypatch)
        await _start_revocable_text(service, db)
        clock[0] += timedelta(seconds=4)
        lease = await service.start_session(user_id='user-1', auth_session_id='auth-1', device_id='device-2',
            device_label='synthetic', content_type='text', content_id='book-1', transfer=True,
            scope=dict(manifest_version='fixture-manifest-v1', segmentation_version='fixture-v1', authority_activation_generation=1))
        assert datetime.fromisoformat(lease['lease_expires_at']) == clock[0] + timedelta(seconds=3)
        clock[0] += timedelta(seconds=10)
        await service.end_session(user_id='user-1', auth_session_id='auth-1', session_id=lease['session_id'])
        assert db.users.rows[0]['reader_acceptance_budget']['consumed_seconds'] == 7
        assert db.users.rows[0]['reading_seconds_balance'] == 113
    asyncio.run(run())


@pytest.mark.parametrize('mutation', ['missing', 'malformed', 'other-user', 'other-book', 'other-edition', 'expired'])
def test_missing_changed_or_expired_authority_denies_content(monkeypatch, mutation):
    async def run():
        clock, db, _, service = await fixture(monkeypatch)
        lease = await _start_revocable_text(service, db)
        user = db.users.rows[0]
        record = user['reader_acceptance_budget']
        if mutation == 'missing': del user['reader_acceptance_budget']
        elif mutation == 'malformed': record['maximum_seconds'] = True
        elif mutation == 'other-user': record['user_id'] = 'other'
        elif mutation == 'other-book': record['content_id'] = 'other'
        elif mutation == 'other-edition': record['manifest_version'] = 'other'
        else: record['expires_at'] = clock[0]
        with pytest.raises(ReadingPassError):
            await service.authorize(user_id='user-1', auth_session_id='auth-1', session_id=lease['session_id'],
                lease_token=lease['lease_token'], content_type='text', content_id='book-1')
        assert user['reading_seconds_balance'] == 120 and not db.wallet_ledger.rows
    asyncio.run(run())


def test_stale_budget_snapshot_cannot_debit_wallet(monkeypatch):
    async def run():
        clock, db, _, service = await fixture(monkeypatch)
        snapshot = deepcopy(db.users.rows[0]['reader_acceptance_budget'])
        db.users.rows[0]['reader_acceptance_budget']['consumed_seconds'] = 7
        with pytest.raises(ReadingPassError):
            await service._debit_account('user-1', 7, snapshot, None)
        assert db.users.rows[0]['reading_seconds_balance'] == 120
    asyncio.run(run())


@pytest.mark.skipif(__import__('os').environ.get('READER_SEGMENT_MONGO_INTEGRATION') != '1',
                    reason='requires explicitly selected disposable loopback replica set')
@pytest.mark.parametrize('transition', ['race', 'transfer-restart'])
def test_actual_mongo_budget_wallet_ledger_atomicity(monkeypatch, transition):
    from contextlib import asynccontextmanager
    import os
    import uuid
    from urllib.parse import urlparse
    from motor.motor_asyncio import AsyncIOMotorClient

    @asynccontextmanager
    async def isolated():
        from scripts.uat_mongo_fixture import isolated_database
        async with isolated_database('acceptance_cap_synthetic_') as (client, db):
            await db.users.create_index('id', unique=True)
            await db.reading_pass_sessions.create_index('active_lock', unique=True, sparse=True)
            await db.wallet_ledger.create_index('idempotency_key', unique=True)
            await db.reading_pass_heartbeats.create_index([('session_id', 1), ('sequence', 1)], unique=True)
            yield db, client

    async def run():
        async with isolated() as (db, client):
            clock = [datetime(2026, 10, 20, tzinfo=timezone.utc)]
            monkeypatch.setattr(module, '_now', lambda: clock[0])
            await db.users.insert_one(dict(id='user-1', role='user', status='active',
                reading_seconds_balance=120, wallet_seconds=120, reader_acceptance_budget=budget(clock[0])))
            await db.reader_segment_activation_state.insert_one(dict(book_slug='book-1', active_segmentation_version='fixture-v1', generation=1))
            await db.reader_segment_manifests.insert_one(dict(book_slug='book-1', segmentation_version='fixture-v1', version='fixture-manifest-v1', status='active'))
            service = ReadingPassService(db=db, client=client, config=ReadingPassConfig(), token_secret='synthetic')
            async def start(transfer=False):
                return await service.start_session(user_id='user-1', auth_session_id='auth-1',
                    device_id='synthetic', device_label='synthetic', content_type='text', content_id='book-1', transfer=transfer,
                    scope=dict(manifest_version='fixture-manifest-v1', segmentation_version='fixture-v1', authority_activation_generation=1))
            lease = await start()
            if transition == 'transfer-restart':
                clock[0] += timedelta(seconds=4)
                lease = await start(True)
                assert datetime.fromisoformat(lease['lease_expires_at']) == clock[0] + timedelta(seconds=3)
                service = ReadingPassService(db=db, client=client, config=ReadingPassConfig(), token_secret='synthetic')
                clock[0] += timedelta(seconds=3)
                await service.end_session(user_id='user-1', auth_session_id='auth-1', session_id=lease['session_id'])
            else:
                clock[0] += timedelta(seconds=7)
                outcomes = await asyncio.gather(service.renew_lease(**renew(lease)), service.end_session(
                    user_id='user-1', auth_session_id='auth-1', session_id=lease['session_id']), return_exceptions=True)
                assert any(not isinstance(x, Exception) for x in outcomes)
            user = await db.users.find_one({'id': 'user-1'})
            rows = await db.wallet_ledger.find({}).to_list(None)
            assert user['reader_acceptance_budget']['consumed_seconds'] == 7
            assert user['reading_seconds_balance'] == user['wallet_seconds'] == 113
            assert sum(row['debit'] for row in rows) == 7
            assert len({row['idempotency_key'] for row in rows}) == len(rows)
            with pytest.raises(ReadingPassError):
                await start()
    asyncio.run(run())


def test_legacy_debit_cannot_bypass_acceptance_scope(monkeypatch):
    import os
    os.environ.setdefault('JWT_SECRET', 'synthetic-acceptance-tests')
    os.environ.setdefault('READING_PASS_TOKEN_SECRET', 'synthetic-acceptance-token-only-for-tests')
    from fastapi import HTTPException
    async def run():
        from backend import server
        clock, db, _, _ = await fixture(monkeypatch)
        monkeypatch.setattr(server, 'db', db)
        with pytest.raises(HTTPException) as denied:
            await server._apply_reading_debit('user-1', 'legacy-fixture', 'Synthetic', 10)
        assert denied.value.detail['code'] == 'ACCEPTANCE_REQUIRES_READING_PASS'
        assert db.users.rows[0]['reading_seconds_balance'] == 120
        assert not db.wallet_ledger.rows
    asyncio.run(run())
