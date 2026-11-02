"""Actual service/native-counter composition; synthetic rows and transactions only.

These tests make no claims about real Mongo or the owner's remaining allowance.
The explicit Mongo cases at the bottom are opt-in disposable loopback only.
"""
import asyncio
import copy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import os
import pytest
from backend import reading_pass_service as service_module
from backend import native_audio_review_scope as scope
from backend import native_audio_review_operator as operator
from backend.domain.reading_pass import ReadingPassConfig, ReadingPassError
from backend.reading_pass_service import ReadingPassService
from backend.tests.test_reading_pass_service_concurrency import Database,Collection
from backend.tests.test_native_audio_review_operator import synthetic_owner_pin


def seeded(now):
    db=Database(balance=300)
    db.user_sessions.rows.append(dict(id='auth-1',user_id='user-1',status='active',
        idle_expires_at=now+timedelta(hours=1),absolute_expires_at=now+timedelta(hours=1)))
    w=dict(_id='SYNTHETIC-workflow',schema=scope.WORKFLOW_SCHEMA,user_id='user-1',original_ceiling_seconds=120,
        owner_scope_sha256='1'*64,legacy_lineage_sha256='2'*64,lineage_status='CONSERVATIVE_PROVEN_BOUND',
        reserved_legacy_microseconds=60000000,reserved_legacy_debit_seconds=61,used_microseconds=60000000,
        used_credit_seconds=61,native_billable_microseconds=0,native_wallet_debit_seconds=0,revision=0)
    g=dict(_id='selfish-SYNTHETIC',schema=scope.GRANT_SCHEMA,user_id='user-1',workflow_id=w['_id'],state='OPEN',epoch=0,
        slug=scope.native.SLUG,descriptor_sha256=scope.native.DESCRIPTOR,package_version=scope.PACKAGE,country='IN',
        created_at=now-timedelta(seconds=1),expires_at=now+timedelta(minutes=10),owner_scope_sha256='1'*64,legacy_lineage_sha256='2'*64)
    db[scope.WORKFLOWS].rows.append(w);db[scope.GRANTS].rows.append(g)
    return db,w,g


def server_scope(w,g):
    return {scope.SCOPE_KEY:g['_id'],'native_audio_review_workflow_id':w['_id'],
        'native_replacement_authorization_id':g['_id'],'acceptance_test_id':scope.native.TEST_ID,
        'manifest_version':scope.PACKAGE,'segmentation_version':scope.native.DESCRIPTOR,
        'package_version':scope.PACKAGE,'release_descriptor_sha256':scope.native.DESCRIPTOR,'release_country':'IN'}


class Transaction:
    def __init__(self,session):self.session=session
    async def __aenter__(self):await self.session.begin();return self
    async def __aexit__(self,typ,*_):
        if typ:await self.session.abort_transaction()
        else:await self.session.commit_transaction()
class Session:
    def __init__(self,client):self.client=client;self.in_transaction=False
    async def __aenter__(self):return self
    async def __aexit__(self,*_):return None
    def start_transaction(self,**kwargs):
        self.options=kwargs
        # Actual service explicitly commits; this fake takes an immediate copy.
        self.in_transaction=True
        self.before={k:copy.deepcopy(v.rows) for k,v in vars(self.client.db).items() if isinstance(v,Collection)}
        return Transaction(self)
    async def begin(self):return None
    async def abort_transaction(self):
        for k,v in self.before.items():getattr(self.client.db,k).rows=copy.deepcopy(v)
        self.in_transaction=False
    async def commit_transaction(self):
        self.client.commits+=1
        if self.client.unknown:raise operator.OutcomeUnknown('SYNTHETIC_UNKNOWN')
        self.in_transaction=False
class Client:
    def __init__(self,db,unknown=False):self.db=db;self.options=SimpleNamespace(retry_writes=False);self.unknown=unknown;self.commits=0;db.client=self
    async def start_session(self):return Session(self)


async def service_fixture(monkeypatch):
    clock=[datetime.now(timezone.utc)];db,w,g=seeded(clock[0]);client=Client(db)
    monkeypatch.setattr(service_module,'_now',lambda:clock[0])
    service=ReadingPassService(db=db,client=client,config=ReadingPassConfig(),token_secret='SYNTHETIC')
    lease=await service.start_session(user_id='user-1',auth_session_id='auth-1',device_id='SYNTHETIC-device',
        device_label='SYNTHETIC',content_type='audio',content_id=scope.native.SLUG,scope=server_scope(w,g))
    return clock,db,service,lease


def renewal(lease,version=1,**change):
    return dict(user_id='user-1',auth_session_id='auth-1',session_id=lease['session_id'],lease_token=lease['lease_token'],
        lease_version=version,sequence=version,idempotency_key=f'SYNTHETIC-{version}',active=True,playback_state='playing',**change)


def test_actual_service_native_fraction_credit_idempotency_and_terminal(monkeypatch):
    async def run():
        clock,db,service,lease=await service_fixture(monkeypatch)
        assert db[scope.GRANTS].rows[0]['epoch']==1 and 'reader_acceptance_budget' not in db.users.rows[0]
        await service.renew_lease(**renewal(lease))
        clock[0]+=timedelta(microseconds=900000)
        result=await service.renew_lease(**renewal(lease,2))
        assert result['deducted_seconds']==0
        w=db[scope.WORKFLOWS].rows[0]
        assert w['native_billable_microseconds']==900000 and w['native_wallet_debit_seconds']==0
        await service.renew_lease(**renewal(lease,2))
        assert db[scope.WORKFLOWS].rows[0]['native_billable_microseconds']==900000
        clock[0]+=timedelta(microseconds=200000)
        await service.end_session(user_id='user-1',auth_session_id='auth-1',session_id=lease['session_id'])
        w=db[scope.WORKFLOWS].rows[0]
        assert w['native_billable_microseconds']==1100000 and w['native_wallet_debit_seconds']==1
        assert w['used_credit_seconds']==62 and db.users.rows[0]['reading_fractional_microseconds']==100000
        assert sum(r['debit'] for r in db.wallet_ledger.rows)==1
        assert db.users.rows[0]['reading_seconds_balance']==299
    asyncio.run(run())


@pytest.mark.parametrize('cap',[None,{'status':'disabled','maximum_seconds':600},{'status':'enabled','maximum_seconds':600}])
def test_any_retained_user_cap_denies_native_start_without_changes(monkeypatch,cap):
    async def run():
        now=datetime.now(timezone.utc);db,w,g=seeded(now);db.users.rows[0]['reader_acceptance_budget']=cap
        service=ReadingPassService(db=db,client=Client(db),config=ReadingPassConfig(),token_secret='SYNTHETIC')
        before=copy.deepcopy((db.users.rows,db[scope.WORKFLOWS].rows,db[scope.GRANTS].rows))
        with pytest.raises(ReadingPassError):await service.start_session(user_id='user-1',auth_session_id='auth-1',
            device_id='SYNTHETIC',device_label='SYNTHETIC',content_type='audio',content_id=scope.native.SLUG,scope=server_scope(w,g))
        assert before==(db.users.rows,db[scope.WORKFLOWS].rows,db[scope.GRANTS].rows)
        assert not db.reading_pass_sessions.rows and not db.wallet_ledger.rows
    asyncio.run(run())


def test_native_interval_then_failed_wallet_cas_rolls_back_all_metadata(monkeypatch):
    async def run():
        clock,db,service,lease=await service_fixture(monkeypatch)
        await service.renew_lease(**renewal(lease));clock[0]+=timedelta(seconds=3)
        before={k:copy.deepcopy(v.rows) for k,v in vars(db).items() if isinstance(v,Collection)}
        original=db.users.update_one
        async def fail(query,change,**kwargs):
            if 'reading_seconds_balance' in change.get('$inc',{}):return SimpleNamespace(modified_count=0)
            return await original(query,change,**kwargs)
        monkeypatch.setattr(db.users,'update_one',fail)
        with pytest.raises(ReadingPassError):await service.renew_lease(**renewal(lease,2))
        assert all(getattr(db,k).rows==v for k,v in before.items())
    asyncio.run(run())


def test_ordinary_audio_start_and_debit_do_not_touch_review_metadata(monkeypatch):
    async def run():
        now=datetime.now(timezone.utc);db,w,g=seeded(now);client=Client(db);clock=[now]
        monkeypatch.setattr(service_module,'_now',lambda:clock[0])
        before=copy.deepcopy((db[scope.WORKFLOWS].rows,db[scope.GRANTS].rows))
        service=ReadingPassService(db=db,client=client,config=ReadingPassConfig(),token_secret='SYNTHETIC')
        lease=await service.start_session(user_id='user-1',auth_session_id='auth-1',device_id='SYNTHETIC',device_label='SYNTHETIC',content_type='audio',content_id='other-book',scope={})
        await service.renew_lease(**renewal(lease));clock[0]+=timedelta(seconds=2)
        await service.end_session(user_id='user-1',auth_session_id='auth-1',session_id=lease['session_id'])
        assert before==(db[scope.WORKFLOWS].rows,db[scope.GRANTS].rows)
        assert db.users.rows[0]['reading_seconds_balance']==298
    asyncio.run(run())


def test_global_carry_motion_does_not_hide_native_subseconds():
    async def run():
        now=datetime.now(timezone.utc);db,w,g=seeded(now);budget=scope.ScopedReviewBudget(db,g,w,{})
        session=SimpleNamespace(in_transaction=True)
        # Normal intervals may own wallet rounding; native elapsed still accumulates.
        for _ in range(4):await budget.interval(900000,session)
        assert budget.workflow['native_billable_microseconds']==3600000
        assert budget.workflow['native_wallet_debit_seconds']==0
        assert db.users.rows[0].get('reading_fractional_microseconds') is None
    asyncio.run(run())


@pytest.mark.skipif(os.environ.get('READER_SEGMENT_MONGO_INTEGRATION')!='1',reason='explicit disposable loopback replica required; unperformed without it')
@pytest.mark.parametrize('case',['start-close-fence','debit-rollback','unknown-commit-readback','service-wallet-ledger-atomicity'])
def test_real_mongo_scoped_native_transaction_atomicity(case,tmp_path,monkeypatch):
    # Uses existing owned/disposable loopback fixture, never a supplied prod URI.
    from scripts.uat_mongo_fixture import isolated_database
    async def run():
        async with isolated_database('acceptance_operator_synthetic_',retryWrites=False,retryReads=False,tz_aware=True) as (client,db):
            now=datetime.now(timezone.utc);fake,w,g=seeded(now)
            for name in ('users',scope.WORKFLOWS,scope.GRANTS):
                await db[name].insert_many(copy.deepcopy(fake[name].rows))
            if case=='debit-rollback':
                async with await client.start_session() as session:
                    session.start_transaction()
                    b=scope.ScopedReviewBudget(db,g,w,{})
                    await b.interval(900000,session);await b.debit(1,session)
                    await session.abort_transaction()
                assert (await db[scope.WORKFLOWS].find_one({'_id':w['_id']}))['native_billable_microseconds']==0
                assert (await db[scope.GRANTS].find_one({'_id':g['_id']}))['epoch']==0
            elif case=='start-close-fence':
                async def claim(close):
                    async with await client.start_session() as s:
                        s.start_transaction()
                        try:
                            if close:
                                r=await db[scope.GRANTS].update_one({'_id':g['_id'],'epoch':0,'state':'OPEN'},
                                    {'$set':{'state':'CLOSED'},'$inc':{'epoch':1}},session=s)
                                assert r.modified_count==1
                            else:await scope.ScopedReviewBudget(db,g,w,{}).claim(s)
                            await s.commit_transaction();return True
                        except Exception:
                            if s.in_transaction:await s.abort_transaction()
                            return False
                outcomes=await asyncio.gather(claim(False),claim(True))
                assert sum(outcomes)==1
                assert (await db[scope.GRANTS].find_one({'_id':g['_id']}))['epoch']==1
            elif case=='unknown-commit-readback':
                from backend.tests.test_native_audio_review_operator import authority_files,legacy_records
                from motor.motor_asyncio import AsyncIOMotorClientSession
                _,ref,_=authority_files(tmp_path)
                a=operator.admit_authority(ref['path'],ref['sha256'],now=datetime.now(timezone.utc))
                await db[scope.GRANTS].delete_many({});await db[scope.WORKFLOWS].delete_many({})
                await db.user_sessions.insert_many(copy.deepcopy(fake.user_sessions.rows))
                for name,key in [('reading_pass_sessions','sessions'),('reading_pass_heartbeats','heartbeats'),
                    ('wallet_ledger','ledger'),('wallet_transactions','transactions')]:
                    await db[name].insert_many(legacy_records()[key])
                await db.create_collection(operator.OPERATIONS)
                for name,(idx,keys) in operator.NAMESPACE_INDEXES.items():
                    await db[name].create_index(keys,name=idx,unique=False)
                monkeypatch.setattr(operator.native,'rights_for_review_phase',lambda *args,**kwargs:({'package_version':scope.PACKAGE},{}))
                original=AsyncIOMotorClientSession.commit_transaction;commits=[]
                async def lost_response(self):
                    commits.append(1)
                    await original(self)  # Genuine commit happened; only response is lost.
                    raise operator.OutcomeUnknown('SYNTHETIC_LOST_COMMIT_RESPONSE')
                monkeypatch.setattr(AsyncIOMotorClientSession,'commit_transaction',lost_response)
                with pytest.raises(operator.OutcomeUnknown,match='COMMIT_OUTCOME_UNVERIFIED'):
                    await operator.execute_one_shot(db=db,client=client,admitted=a,book={})
                assert commits==[1] and await db[operator.OPERATIONS].count_documents({})==1
                readback=await operator.status(db,client,a)
                assert readback['status']=='COMMIT_RECEIPT_OBSERVED' and readback['replay_permitted'] is False
                assert commits==[1]
                assert (await db.users.find_one({'id':'user-1'}))['reading_seconds_balance']==300
            else:
                clock=[now.replace(microsecond=0)]
                monkeypatch.setattr(service_module,'_now',lambda:clock[0])
                await db.reading_pass_sessions.create_index('active_lock',unique=True,sparse=True)
                await db.wallet_ledger.create_index('idempotency_key',unique=True)
                await db.reading_pass_heartbeats.create_index([('session_id',1),('sequence',1)],unique=True)
                service=ReadingPassService(db=db,client=client,config=ReadingPassConfig(),token_secret='SYNTHETIC')
                lease=await service.start_session(user_id='user-1',auth_session_id='auth-1',device_id='SYNTHETIC',
                    device_label='SYNTHETIC',content_type='audio',content_id=scope.native.SLUG,scope=server_scope(w,g))
                await service.renew_lease(**renewal(lease))
                names=['users',scope.WORKFLOWS,scope.GRANTS,'reading_pass_sessions','reading_pass_heartbeats',
                    'wallet_ledger','wallet_transactions','reading_pass_devices','reading_pass_audit']
                before={n:await db[n].find({}).sort('_id',1).to_list(None) for n in names}
                clock[0]+=timedelta(microseconds=1200000)
                original=service._append_time_debit;reached=[]
                async def fail_after_ledger(**kwargs):
                    await original(**kwargs);reached.append(True)
                    raise ReadingPassError('SYNTHETIC_AFTER_LEDGER',409,'Synthetic atomicity fault')
                monkeypatch.setattr(service,'_append_time_debit',fail_after_ledger)
                with pytest.raises(ReadingPassError,match='Synthetic atomicity fault'):
                    await service.renew_lease(**renewal(lease,2))
                assert reached==[True]
                for name,rows in before.items():
                    assert await db[name].find({}).sort('_id',1).to_list(None)==rows,name
    asyncio.run(run())


def test_actual_native_debits_preexisting_and_ordinary_moved_fraction_without_reset(monkeypatch):
    async def run():
        clock,db,service,lease=await service_fixture(monkeypatch)
        db.users.rows[0]['reading_fractional_microseconds']=900000
        await service.renew_lease(**renewal(lease));clock[0]+=timedelta(microseconds=200000)
        await service.end_session(user_id='user-1',auth_session_id='auth-1',session_id=lease['session_id'])
        w=db[scope.WORKFLOWS].rows[0]
        assert w['native_billable_microseconds']==200000 and w['native_wallet_debit_seconds']==1
        assert db.users.rows[0]['reading_fractional_microseconds']==100000
        ordinary=await service.start_session(user_id='user-1',auth_session_id='auth-1',device_id='SYNTHETIC',
            device_label='SYNTHETIC',content_type='audio',content_id='other-book',scope={})
        await service.renew_lease(**renewal(ordinary));clock[0]+=timedelta(microseconds=700000)
        await service.end_session(user_id='user-1',auth_session_id='auth-1',session_id=ordinary['session_id'])
        assert db.users.rows[0]['reading_fractional_microseconds']==800000
        g=db[scope.GRANTS].rows[0]
        native=await service.start_session(user_id='user-1',auth_session_id='auth-1',device_id='SYNTHETIC',
            device_label='SYNTHETIC',content_type='audio',content_id=scope.native.SLUG,scope=server_scope(w,g))
        await service.renew_lease(**renewal(native));clock[0]+=timedelta(microseconds=300000)
        await service.end_session(user_id='user-1',auth_session_id='auth-1',session_id=native['session_id'])
        w=db[scope.WORKFLOWS].rows[0]
        assert w['native_billable_microseconds']==500000 and w['native_wallet_debit_seconds']==2
        assert w['used_credit_seconds']==63 and db.users.rows[0]['reading_fractional_microseconds']==100000
        assert db.users.rows[0]['reading_seconds_balance']==298
        assert sum(r['debit'] for r in db.wallet_ledger.rows)==2
    asyncio.run(run())


@pytest.mark.parametrize('carry',[-1,1000000,True,'0'])
def test_out_of_range_actual_current_carry_denies_operator_member(tmp_path,carry):
    from backend.tests.test_native_audio_review_operator import authority_files,operator_db,legacy_records
    async def run():
        _,ref,_=authority_files(tmp_path)
        a=operator.admit_authority(ref['path'],ref['sha256'],now=datetime.now(timezone.utc))
        db,_=operator_db(legacy_records());db.users.rows[0]['reading_fractional_microseconds']=carry
        with pytest.raises(operator.OperatorStop,match='GLOBAL_FRACTIONAL_STATE_UNVERIFIED'):
            await operator.member(db,a)
        assert db[scope.GRANTS].rows==[] and db[scope.WORKFLOWS].rows==[]
    asyncio.run(run())
