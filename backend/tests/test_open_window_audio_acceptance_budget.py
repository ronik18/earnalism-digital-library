"""Synthetic accounts only; no provider or production access."""
import asyncio
import ast
import os
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pymongo.errors import DuplicateKeyError
from backend import audio_acceptance_budget as policy, reading_pass_service as module
from backend.domain.reading_pass import ReadingPassConfig, ReadingPassError
from backend.reading_pass_service import ReadingPassService
from backend.tests.test_reading_pass_service_concurrency import Database, Client


def fixture(monkeypatch):
    clock = [datetime(2026, 10, 26, tzinfo=timezone.utc)]
    monkeypatch.setattr(module, '_now', lambda: clock[0])
    db, client = Database(balance=1000), Client()
    db.users.rows[0]['reader_acceptance_budget'] = policy.build_budget('user-1', clock[0])
    db.user_sessions.rows.append(dict(id='auth-1', user_id='user-1', status='active',
        idle_expires_at=clock[0]+timedelta(hours=1), absolute_expires_at=clock[0]+timedelta(hours=1)))
    service = ReadingPassService(db=db, client=client, config=ReadingPassConfig(), token_secret='synthetic')
    return clock, db, client, service


async def start(service, **overrides):
    args = dict(user_id='user-1', auth_session_id='auth-1', device_id='device-1',
        device_label='synthetic', content_type='audio', content_id=policy.SLUG,
        scope=dict(policy.PACKAGE_SCOPE, media_position_seconds=0))
    return await service.start_session(**(args | overrides))


async def renew(service, lease, sequence, **overrides):
    args = dict(user_id='user-1', auth_session_id='auth-1', session_id=lease['session_id'],
        lease_token=lease['lease_token'], lease_version=sequence, sequence=sequence,
        idempotency_key=f'synthetic-{lease["session_id"]}-{sequence}', active=True, playback_state='playing')
    return await service.renew_lease(**(args | overrides))


async def end(service, lease):
    return await service.end_session(user_id='user-1', auth_session_id='auth-1', session_id=lease['session_id'])


def assert_accounting(db, expected):
    user = db.users.rows[0]
    assert user['reader_acceptance_budget']['consumed_seconds'] == expected
    assert user['reading_seconds_balance'] == user['wallet_seconds'] == 1000-expected
    assert sum(row['debit'] for row in db.wallet_ledger.rows) == expected
    assert -sum(row['seconds'] for row in db.wallet_transactions.rows) == expected
    assert {r['source_transaction_id'] for r in db.wallet_ledger.rows} == {r['id'] for r in db.wallet_transactions.rows}


def test_600_aggregate_two_sessions_restart_and_terminal_replay(monkeypatch):
    async def run():
        clock, db, client, service = fixture(monkeypatch)
        for session_number in (1, 2):
            lease = await start(service)
            await renew(service, lease, 1)  # preparation is not billed
            for sequence in range(2, 17):
                clock[0] += timedelta(seconds=20)
                result = await renew(service, lease, sequence)
            assert result['status'] == ('Exhausted' if session_number == 2 else 'Running')
            await end(service, lease)
            await end(service, lease)  # terminal replay cannot debit twice
            assert_accounting(db, session_number*300)
            service = ReadingPassService(db=db, client=client, config=ReadingPassConfig(), token_secret='synthetic')
        with pytest.raises(ReadingPassError):
            await start(service)
        assert db.users.rows[0]['reader_acceptance_budget']['sessions_started'] == 2
        assert all('active_lock' not in row for row in db.reading_pass_sessions.rows)
    asyncio.run(run())


def test_two_zero_debit_starts_exhaust_start_count_and_transfer_denied(monkeypatch):
    async def run():
        _, db, _, service = fixture(monkeypatch)
        with pytest.raises(ReadingPassError) as denied:
            await start(service, transfer=True)
        assert denied.value.code == 'ACCEPTANCE_TRANSFER_DENIED'
        for _ in range(2):
            await end(service, await start(service))
        with pytest.raises(ReadingPassError) as denied:
            await start(service)
        assert denied.value.code == 'ACCEPTANCE_SESSION_LIMIT'
        assert len(db.reading_pass_sessions.rows) == 2
        assert_accounting(db, 0)
    asyncio.run(run())


def test_concurrent_start_and_expired_unsettled_lock_cannot_be_bypassed(monkeypatch):
    async def run():
        clock, db, _, service = fixture(monkeypatch)
        results = await asyncio.gather(start(service), start(service), return_exceptions=True)
        assert sum(isinstance(x, dict) for x in results) == 1
        lease = next(x for x in results if isinstance(x, dict))
        await renew(service, lease, 1)
        clock[0] += timedelta(seconds=40)
        with pytest.raises(ReadingPassError):
            await start(service)
        assert db.users.rows[0]['reader_acceptance_budget']['sessions_started'] == 1
        assert_accounting(db, 0)
        await end(service, lease)
        assert_accounting(db, 20)
        await start(service)
        assert db.users.rows[0]['reader_acceptance_budget']['sessions_started'] == 2
    asyncio.run(run())


def test_final_five_seconds_expiry_authorization_and_delayed_settlement(monkeypatch):
    async def run():
        clock, db, _, service = fixture(monkeypatch)
        clock[0] += timedelta(seconds=895)
        lease = await start(service)
        assert datetime.fromisoformat(lease['lease_expires_at']) == clock[0]+timedelta(seconds=5)
        await renew(service, lease, 1)
        clock[0] += timedelta(seconds=10)
        with pytest.raises(ReadingPassError):
            await service.authorize(user_id='user-1', auth_session_id='auth-1', session_id=lease['session_id'],
                lease_token=lease['lease_token'], content_type='audio', content_id=policy.SLUG)
        await end(service, lease)
        assert_accounting(db, 5)
        with pytest.raises(ReadingPassError):
            await start(service)
        assert db.users.rows[0]['reader_acceptance_budget']['sessions_started'] == 1
    asyncio.run(run())


def test_concurrent_last_second_renew_and_end_share_one_cap(monkeypatch):
    async def run():
        clock, db, _, service = fixture(monkeypatch)
        db.users.rows[0]['reader_acceptance_budget']['consumed_seconds'] = 599
        db.users.rows[0]['reading_seconds_balance'] = db.users.rows[0]['wallet_seconds'] = 401
        lease = await start(service)
        await renew(service, lease, 1)
        clock[0] += timedelta(seconds=5)
        await asyncio.gather(renew(service, lease, 2), end(service, lease), return_exceptions=True)
        assert db.users.rows[0]['reader_acceptance_budget']['consumed_seconds'] == 600
        assert db.users.rows[0]['reading_seconds_balance'] == 400
        assert sum(r['debit'] for r in db.wallet_ledger.rows) == 1
    asyncio.run(run())


@pytest.mark.parametrize('field,value', [('maximum_seconds',601),('maximum_seconds',True),
    ('maximum_sessions',3),('maximum_sessions',True),('sessions_started',True),
    ('sessions_started',-1),('sessions_started',3),('package_version','wrong'),
    ('release_descriptor_sha256','wrong'),('catalogue_uuid','wrong'),('user_id','other'),
    ('test_id','other'),('consumed_seconds',-1),('consumed_seconds',601),('status','disabled'),
    ('content_type','text'),('content_id','other')])
def test_corrupt_authority_cannot_start_or_change_accounts(monkeypatch, field, value):
    async def run():
        _, db, _, service = fixture(monkeypatch)
        db.users.rows[0]['reader_acceptance_budget'][field] = value
        before = deepcopy(db.users.rows)
        with pytest.raises(ReadingPassError):
            await start(service)
        assert db.users.rows == before and not db.reading_pass_sessions.rows and not db.wallet_ledger.rows
    asyncio.run(run())


@pytest.mark.parametrize('kind', ['missing-budget','wrong-scope','wrong-binding','wrong-ordinal'])
def test_existing_session_loses_access_on_authority_mismatch(monkeypatch, kind):
    async def run():
        _, db, _, service = fixture(monkeypatch)
        lease = await start(service)
        row = db.reading_pass_sessions.rows[0]
        if kind == 'missing-budget':del db.users.rows[0]['reader_acceptance_budget']
        elif kind == 'wrong-scope':row['scope']['package_version'] = 'wrong'
        elif kind == 'wrong-binding':row['acceptance_test_id'] = 'wrong'
        else:row['acceptance_session_ordinal'] = 3
        with pytest.raises(ReadingPassError):
            await service.authorize(user_id='user-1',auth_session_id='auth-1',session_id=lease['session_id'],
                lease_token=lease['lease_token'],content_type='audio',content_id=policy.SLUG)
        assert not db.wallet_ledger.rows
    asyncio.run(run())


def server_function(name, namespace):
    source = Path(__file__).resolve().parents[1]/'server.py'
    node = next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.AsyncFunctionDef) and n.name == name)
    node.decorator_list = []
    tree = ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),node],type_ignores=[])
    exec(compile(ast.fix_missing_locations(tree),str(source),'exec'),namespace)
    return namespace[name]


@pytest.mark.parametrize('evidence_passes',[False,True])
def test_server_start_binds_validated_candidate_without_rollout_cookie(monkeypatch,evidence_passes):
    async def run():
        _, db, _, service = fixture(monkeypatch)
        package = dict(package_version=policy.PACKAGE,release_descriptor_sha256=policy.DESCRIPTOR,duration_ms=491436)
        ns = dict(_reading_pass_enabled_or_404=lambda:None,PUBLIC_AUDIO_PREVIEW_SECONDS=0,
            _reader_audio_package_book_for_slug=AsyncMock(return_value={'slug':policy.SLUG}),
            audio_acceptance_budget=policy,_validated_audiobook_package=lambda *a,**kw:package,
            _book_audiobook_release_packages=lambda book:{policy.DESCRIPTOR:package},
            _has_release_eligible_audiobook_package_evidence=lambda *a:evidence_passes,
            reading_pass_service=service,_invalidate_user_cache=AsyncMock(),
            _set_reading_pass_media_cookies=lambda *a:None,ReadingPassError=ReadingPassError,
            _reading_pass_http_error=lambda e:e,DuplicateKeyError=DuplicateKeyError)
        fn = server_function('_reading_pass_start',ns)
        payload=SimpleNamespace(content_type='audio',content_id=policy.SLUG,media_position_seconds=0,
            device_id='device-1',device_label='synthetic')
        if evidence_passes:
            await fn(payload,{'id':'user-1','session_id':'auth-1'},None,transfer=False,request=None)
            assert all(db.reading_pass_sessions.rows[0]['scope'][k]==v for k,v in policy.PACKAGE_SCOPE.items())
            assert db.users.rows[0]['reader_acceptance_budget']['sessions_started']==1
        else:
            with pytest.raises(ReadingPassError):
                await fn(payload,{'id':'user-1','session_id':'auth-1'},None,transfer=False,request=None)
            assert not db.reading_pass_sessions.rows
            assert db.users.rows[0]['reader_acceptance_budget']['sessions_started']==0
    asyncio.run(run())


@pytest.mark.parametrize('media_cookie', [False, True])
@pytest.mark.parametrize('selected', [False, True])
def test_real_audio_authorization_retains_auth_and_exact_package_gate(monkeypatch, media_cookie, selected):
    async def run():
        _, _, _, service = fixture(monkeypatch)
        lease = await start(service)
        package = dict(package_version=policy.PACKAGE,release_descriptor_sha256=policy.DESCRIPTOR,duration_ms=491436)
        ns = dict(_reading_pass_lease_headers=lambda request:(lease['session_id'],lease['lease_token']),
            reading_pass_service=service,audio_acceptance_budget=policy,
            _reader_audio_package_book_for_slug=AsyncMock(return_value={'slug':policy.SLUG}),
            _selected_audiobook_package=lambda *a:(package if selected else None,'',''),
            ReadingPassError=ReadingPassError,_reading_pass_http_error=lambda e:e)
        fn = server_function('_authorize_reading_pass_audio',ns)
        principal = None if media_cookie else {'id':'user-1','session_id':'auth-1','role':'user'}
        if selected:
            assert (await fn(None,principal,policy.SLUG))['acceptance_session_ordinal']==1
        else:
            with pytest.raises(ReadingPassError) as denied:
                await fn(None,principal,policy.SLUG)
            assert denied.value.code == 'ACCEPTANCE_SCOPE_UNAVAILABLE'
    asyncio.run(run())


def test_other_title_and_text_cannot_settle_or_transfer_existing_audio(monkeypatch):
    async def run():
        _, db, _, service = fixture(monkeypatch)
        await start(service)
        before=deepcopy(db.users.rows),deepcopy(db.reading_pass_sessions.rows)
        for overrides in [{'content_id':'other'}, {'content_type':'text','scope':{}}, {'scope':{}}, {'transfer':True}]:
            with pytest.raises(ReadingPassError):
                await start(service,**overrides)
        assert (db.users.rows,db.reading_pass_sessions.rows)==before
        assert not db.wallet_ledger.rows
    asyncio.run(run())


@pytest.mark.parametrize('change',['future','extended-expiry','stale-start-snapshot'])
def test_budget_deadline_and_start_cas_cannot_expand_authority(monkeypatch,change):
    async def run():
        clock,db,_,service=fixture(monkeypatch)
        budget=db.users.rows[0]['reader_acceptance_budget']
        if change=='future':
            budget['created_at']+=timedelta(seconds=1)
            budget['expires_at']+=timedelta(seconds=1)
        elif change=='extended-expiry':budget['expires_at']+=timedelta(seconds=1)
        else:
            snapshot=deepcopy(budget)
            budget['sessions_started']=1
            with pytest.raises(ReadingPassError):
                await service._reserve_audio_acceptance_start('user-1',snapshot,None)
            with pytest.raises(ReadingPassError):
                await service._debit_account('user-1',1,snapshot,None)
            assert budget['sessions_started']==1
            assert db.users.rows[0]['reading_seconds_balance']==1000
            return
        with pytest.raises(ReadingPassError):await start(service)
        assert not db.reading_pass_sessions.rows
    asyncio.run(run())


def test_legacy_debit_cannot_bypass_audio_cap(monkeypatch):
    from fastapi import HTTPException
    async def run():
        _,db,_,_=fixture(monkeypatch)
        fn=server_function('_apply_reading_debit',dict(db=db,HTTPException=HTTPException))
        with pytest.raises(HTTPException) as denied:
            await fn('user-1','synthetic','Synthetic',10)
        assert denied.value.detail['code']=='ACCEPTANCE_REQUIRES_READING_PASS'
        assert_accounting(db,0)
    asyncio.run(run())


@pytest.mark.skipif(os.environ.get('READER_SEGMENT_MONGO_INTEGRATION') != '1',
                   reason='requires explicitly selected authenticated disposable loopback replica set')
@pytest.mark.parametrize('scenario',['aggregate','races','rollback'])
def test_real_mongo_cap_start_count_and_wallet_atomicity(monkeypatch,scenario):
    from scripts.uat_mongo_fixture import isolated_database
    async def run():
        async with isolated_database('acceptance_cap_synthetic_') as (client,db):
            clock=[datetime(2026,10,26,tzinfo=timezone.utc)]
            monkeypatch.setattr(module,'_now',lambda:clock[0])
            await db.users.create_index('id',unique=True)
            await db.reading_pass_sessions.create_index('active_lock',unique=True,sparse=True)
            await db.wallet_ledger.create_index('idempotency_key',unique=True)
            await db.reading_pass_heartbeats.create_index([('session_id',1),('idempotency_key',1)],unique=True)
            await db.users.insert_one(dict(id='user-1',role='user',status='active',
                reading_seconds_balance=1000,wallet_seconds=1000,
                reader_acceptance_budget=policy.build_budget('user-1',clock[0])))
            service=ReadingPassService(db=db,client=client,config=ReadingPassConfig(),token_secret='synthetic')
            if scenario=='rollback':
                monkeypatch.setattr(service,'_audit',AsyncMock(side_effect=RuntimeError('synthetic abort')))
                with pytest.raises(RuntimeError):await start(service)
                user=await db.users.find_one({'id':'user-1'})
                assert user['reader_acceptance_budget']['sessions_started']==0
                assert await db.reading_pass_sessions.count_documents({})==0
                assert user['reading_seconds_balance']==1000
                return
            if scenario=='aggregate':
                for number in (1,2):
                    lease=await start(service)
                    await renew(service,lease,1)
                    for sequence in range(2,17):
                        clock[0]+=timedelta(seconds=20)
                        await renew(service,lease,sequence)
                    await end(service,lease)
                with pytest.raises(ReadingPassError):await start(service)
                expected=600
            else:
                for _ in range(2):
                    attempts=await asyncio.gather(start(service),start(service),return_exceptions=True)
                    leases=[x for x in attempts if isinstance(x,dict)]
                    assert len(leases)==1
                    lease=leases[0]
                    await renew(service,lease,1)
                    clock[0]+=timedelta(seconds=20)
                    await asyncio.gather(renew(service,lease,2),end(service,lease),return_exceptions=True)
                    await end(service,lease)
                with pytest.raises(ReadingPassError) as denied:await start(service)
                assert denied.value.code=='ACCEPTANCE_SESSION_LIMIT'
                expected=40
            user=await db.users.find_one({'id':'user-1'})
            assert user['reader_acceptance_budget']['consumed_seconds']==expected
            assert user['reader_acceptance_budget']['sessions_started']==2
            assert user['reading_seconds_balance']==user['wallet_seconds']==1000-expected
            ledger=await db.wallet_ledger.find({}).to_list(100)
            tx=await db.wallet_transactions.find({}).to_list(100)
            assert sum(x['debit'] for x in ledger)==-sum(x['seconds'] for x in tx)==expected
            assert {x['source_transaction_id'] for x in ledger}=={x['id'] for x in tx}
            assert await db.reading_pass_sessions.count_documents({'active_lock':{'$exists':True}})==0
    asyncio.run(run())
