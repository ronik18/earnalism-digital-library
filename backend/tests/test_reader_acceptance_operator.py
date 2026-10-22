"""Only new operator/containment behavior; no unchanged cap-suite reruns."""
import asyncio
from datetime import datetime, timezone
import json
from types import SimpleNamespace

import pytest
from backend import reader_acceptance_operator as op
from backend.tests.test_reading_pass_service_concurrency import Database, Collection


@pytest.fixture(autouse=True)
def synthetic_selector_only(monkeypatch):
    import hashlib
    monkeypatch.setattr(op,'ACCOUNT_SELECTOR_SHA256',hashlib.sha256(b'user-1').hexdigest())


def fixture():
    db = Database(balance=120)
    db.reader_segment_manifests.rows.append({'book_slug': op.BOOK, 'status': 'active',
        'version': op.MANIFEST, 'segmentation_version': op.SEGMENTATION})
    db.reader_segment_activation_state.rows.append({'book_slug': op.BOOK,
        'active_segmentation_version': op.SEGMENTATION, 'generation': 0})
    return SimpleNamespace(db=db)


@pytest.mark.parametrize('value,expected', [('', False), (op.MODE, True), ('unknown', None)])
def test_containment_mode_is_explicit_and_unknown_fails(value, expected):
    if expected is None:
        with pytest.raises(op.OperatorStop): op.containment_enabled({op.MODE_VARIABLE: value})
    else:
        assert op.containment_enabled({op.MODE_VARIABLE: value}) is expected


def test_enable_disable_retains_budget_and_never_changes_wallet():
    async def run():
        server = fixture()
        before = datetime.now(timezone.utc)
        result = await op.budget_operation(server, action='enable', user_id='user-1')
        record = server.db.users.rows[0]['reader_acceptance_budget']
        assert record['maximum_seconds'] == 180 and record['consumed_seconds'] == 0
        assert 899 <= (record['expires_at'] - before).total_seconds() <= 901
        with pytest.raises(op.OperatorStop):
            await op.budget_operation(server, action='enable', user_id='user-1')
        record['consumed_seconds'] = 7
        with pytest.raises(op.OperatorStop):
            await op.budget_operation(server, action='disable', user_id='user-1', expected_consumed=0)
        await op.budget_operation(server, action='disable', user_id='user-1', expected_consumed=7)
        assert record['status'] == 'disabled' and record['consumed_seconds'] == 7
        again = await op.budget_operation(server, action='disable', user_id='user-1', expected_consumed=7)
        assert again['status'] == 'ALREADY_SATISFIED'
        assert server.db.users.rows[0]['reading_seconds_balance'] == server.db.users.rows[0]['wallet_seconds'] == 120
        assert not server.db.wallet_ledger.rows
    asyncio.run(run())


@pytest.mark.parametrize('cause', ['active', 'legacy', 'edition', 'generation'])
def test_enable_fail_closed_without_writes(cause):
    async def run():
        server = fixture()
        if cause == 'active': server.db.reading_pass_sessions.rows.append({'user_id':'user-1','status':'active'})
        elif cause == 'legacy': server.db.users.rows[0]['active_reading_session'] = {'session_id':'legacy'}
        elif cause == 'edition': server.db.reader_segment_manifests.rows[0]['version'] = 'other'
        else: server.db.reader_segment_activation_state.rows[0]['generation'] = 1
        with pytest.raises(op.OperatorStop):
            await op.budget_operation(server, action='enable', user_id='user-1')
        assert 'reader_acceptance_budget' not in server.db.users.rows[0]
    asyncio.run(run())


def test_runtime_binding_and_containment_are_required(monkeypatch):
    server = SimpleNamespace(ENVIRONMENT='production', READING_PASS_V2_ENABLED=True,
                             reading_pass_service=SimpleNamespace(_acceptance_budget=object()))
    for key,value in {'RAILWAY_PROJECT_ID':op.PROJECT, 'RAILWAY_ENVIRONMENT_ID':op.ENVIRONMENT,
        'RAILWAY_SERVICE_ID':op.SERVICE,'RAILWAY_GIT_COMMIT_SHA':'a'*40,op.MODE_VARIABLE:op.MODE}.items():
        monkeypatch.setenv(key,value)
    op.verify_runtime(server,'a'*40, mutation=True)
    with pytest.raises(op.OperatorStop): op.verify_runtime(server,'b'*40, mutation=True)
    monkeypatch.delenv(op.MODE_VARIABLE)
    with pytest.raises(op.OperatorStop): op.verify_runtime(server,'a'*40, mutation=True)


def test_startup_containment_prevents_both_publication_and_maintenance(monkeypatch):
    async def run():
        monkeypatch.setenv('MONGODB_URL','mongodb://127.0.0.1:29998/operator_unused')
        monkeypatch.setenv('JWT_SECRET','operator-synthetic')
        monkeypatch.setenv('READING_PASS_TOKEN_SECRET','operator-synthetic-not-production')
        monkeypatch.setenv(op.MODE_VARIABLE,op.MODE)
        from backend import server
        class Forbidden:
            def __getattr__(self, name): raise AssertionError('No startup DB access in contained mode')
        monkeypatch.setattr(server,'db',Forbidden())
        monkeypatch.setattr(server,'ENABLE_STARTUP_DB_MAINTENANCE',True)
        await server._run_startup_database_maintenance()
        assert await server._initialize_authorized_reader_release() == [{'status':'HELD_ACCEPTANCE_RELEASE_CONTAINMENT'}]
    asyncio.run(run())


def test_rollback_guard_is_explicit_and_idempotent():
    async def run():
        server = fixture()
        await op.budget_operation(server,action='enable',user_id='user-1')
        result = await op.budget_operation(server,action='rollback-guard',user_id='user-1',expected_consumed=0)
        assert result['account_blocked'] is True
        user=server.db.users.rows[0]
        assert user['status']=='blocked' and user['reader_acceptance_budget']['status']=='disabled'
        again=await op.budget_operation(server,action='rollback-guard',user_id='user-1',expected_consumed=0)
        assert again['status']=='ALREADY_SATISFIED' and user['wallet_seconds']==120
    asyncio.run(run())


def test_unknown_commit_does_not_retry(monkeypatch):
    async def run():
        server=fixture()
        calls=[]
        class Session:
            async def __aenter__(self): return self
            async def __aexit__(self,*_): pass
            def start_transaction(self): pass
            async def abort_transaction(self): calls.append('abort')
            async def commit_transaction(self):
                calls.append('commit'); raise RuntimeError('synthetic uncertain transport')
        async def start_session(): return Session()
        server.client=SimpleNamespace(start_session=start_session)
        monkeypatch.setattr(op,'verify_runtime',lambda *_a,**_k:None)
        async def noop(*_a,**_k): return {}
        monkeypatch.setattr(op,'baseline_startup_noop',noop)
        args=SimpleNamespace(expected_revision='a'*40, action='enable',user_id='user-1',expected_consumed=None)
        with pytest.raises(op.CommitOutcomeUnknown): await op.execute(server,args)
        assert calls==['commit']
    asyncio.run(run())


def test_baseline_missing_maintenance_or_pointer_stops(tmp_path):
    async def run():
        server=fixture(); server.ENABLE_STARTUP_DB_MAINTENANCE=True
        with pytest.raises(op.OperatorStop): await op.baseline_startup_noop(server)
        server.ENABLE_STARTUP_DB_MAINTENANCE=False
        (tmp_path/'data').mkdir()
        (tmp_path/'data'/'approved_reader_bootstrap.json').write_text(json.dumps(dict(
            schema='earnalism.approved-reader-bootstrap.v1',bootstrap_only=True,territory='IN',target_characters=3200,titles=[{'slug':op.BOOK}])))
        server.__file__=str(tmp_path/'server.py')
        class Indexes:
            def __init__(self, keys): self.keys=keys
            async def index_information(self): return {str(i):dict(unique=True,key=key,**({'partialFilterExpression':partial} if partial else {})) for i,(key,partial) in enumerate(self.keys)}
        tables={
            'reader_content_segments':Indexes([([('book_slug',1),('page_index',1),('segmentation_version',1)],None)]),
            'reader_segment_manifests':Indexes([([('book_slug',1),('segmentation_version',1)],None),([('book_slug',1)],{'status':'active'})]),
            'reader_segment_activation_state':Indexes([([('book_slug',1)],None)]),
            'reader_segment_activation_operations':Indexes([([('operation_id',1)],None)])}
        original=server.db
        class DB:
            def __getitem__(self,name): return tables[name]
            def __getattr__(self,name): return getattr(original,name)
        server.db=DB()
        assert (await op.baseline_startup_noop(server))['planned_titles']==1
        original.reader_segment_manifests.rows=[];original.reader_segment_activation_state.rows=[]
        with pytest.raises(op.OperatorStop): await op.baseline_startup_noop(server)
    asyncio.run(run())


@pytest.mark.skipif(__import__('os').environ.get('READER_SEGMENT_MONGO_INTEGRATION')!='1', reason='explicit disposable loopback replica set only')
def test_actual_mongo_concurrent_enable_cas_has_no_reset_or_wallet_mutation(tmp_path,monkeypatch):
    from motor.motor_asyncio import AsyncIOMotorClient
    from urllib.parse import urlparse
    import os,uuid
    async def run():
        from scripts.uat_mongo_fixture import isolated_database
        async with isolated_database('acceptance_operator_synthetic_') as (client, db):
            await db.users.create_index('id',unique=True)
            for name,keys,partial in [
                ('reader_content_segments',[('book_slug',1),('page_index',1),('segmentation_version',1)],None),
                ('reader_segment_manifests',[('book_slug',1),('segmentation_version',1)],None),
                ('reader_segment_manifests',[('book_slug',1)],{'status':'active'}),
                ('reader_segment_activation_state',[('book_slug',1)],None),
                ('reader_segment_activation_operations',[('operation_id',1)],None)]:
                await db[name].create_index(keys,unique=True,**({'partialFilterExpression':partial} if partial else {}))
            await db.users.insert_one(dict(id='user-1',role='user',status='active',reading_seconds_balance=120,wallet_seconds=120))
            await db.reader_segment_manifests.insert_one(dict(book_slug=op.BOOK,status='active',version=op.MANIFEST,segmentation_version=op.SEGMENTATION))
            await db.reader_segment_activation_state.insert_one(dict(book_slug=op.BOOK,active_segmentation_version=op.SEGMENTATION,generation=0))
            (tmp_path/'data').mkdir()
            (tmp_path/'data'/'approved_reader_bootstrap.json').write_text(json.dumps(dict(schema='earnalism.approved-reader-bootstrap.v1',bootstrap_only=True,territory='IN',target_characters=3200,titles=[{'slug':op.BOOK}])))
            server=SimpleNamespace(db=db,client=client,__file__=str(tmp_path/'server.py'),ENVIRONMENT='production',READING_PASS_V2_ENABLED=True,
                ENABLE_STARTUP_DB_MAINTENANCE=False,reading_pass_service=SimpleNamespace(_acceptance_budget=object()))
            for key,value in {'RAILWAY_PROJECT_ID':op.PROJECT,'RAILWAY_ENVIRONMENT_ID':op.ENVIRONMENT,'RAILWAY_SERVICE_ID':op.SERVICE,
                              'RAILWAY_GIT_COMMIT_SHA':'a'*40,op.MODE_VARIABLE:op.MODE}.items():monkeypatch.setenv(key,value)
            args=SimpleNamespace(expected_revision='a'*40,action='enable',user_id='user-1',expected_consumed=None)
            outcomes=await asyncio.gather(op.execute(server,args),op.execute(server,args),return_exceptions=True)
            assert sum(isinstance(x,dict) and x.get('status')=='ENABLE' for x in outcomes)==1
            user=await db.users.find_one({'id':'user-1'})
            retained=user['reader_acceptance_budget']
            assert retained['maximum_seconds']==180 and retained['consumed_seconds']==0
            assert user['reading_seconds_balance']==user['wallet_seconds']==120
            assert await db.wallet_ledger.count_documents({})==0
            with pytest.raises(op.OperatorStop):await op.execute(server,args)
            assert (await db.users.find_one({'id':'user-1'}))['reader_acceptance_budget']['expires_at']==retained['expires_at']
    asyncio.run(run())


def test_other_selector_stops_before_any_account_read():
    async def run():
        class Forbidden:
            def __getattr__(self,name): raise AssertionError('No account scan')
        with pytest.raises(op.OperatorStop):
            await op.budget_operation(SimpleNamespace(db=Forbidden()),action='enable',user_id='other-account')
    asyncio.run(run())
