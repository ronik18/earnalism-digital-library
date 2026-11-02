"""Actual pure/operator source with synthetic evidence only; no DB/network calls."""
import asyncio
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from backend import native_audio_review_authority as proof
from backend import native_audio_review_operator as op
from backend import native_audio_review_scope as scope
from backend import native_audio_review_operator_cli as cli
NOW = datetime.now(timezone.utc).replace(microsecond=0)
TEST_OWNER=dict(schema='earnalism.owner_original120_verbatim_reply.v1',question_id=proof.ORIGINAL_QUESTION_ID,
    question=proof.ORIGINAL_QUESTION,answer=proof.ORIGINAL_ANSWER,maximum_cumulative_existing_credit_seconds=120,
    new_credit_or_purchase_authority=False,remaining_allowance=None,provenance='SYNTHETIC_UNIT_FIXTURE_NOT_REAL_AUTHORITY')
TEST_OWNER_BYTES=json.dumps(TEST_OWNER).encode()
@pytest.fixture(autouse=True)
def synthetic_owner_pin(monkeypatch):
    # Explicit test-only substitute; production source remains pinned5826.
    assert proof.ORIGINAL_OWNER_RECEIPT_SHA256=='5826f4bc1272a7e4f0d882990b81f704598fb37ed9536eb374091b991af6fd1d'
    monkeypatch.setattr(proof,'ORIGINAL_OWNER_RECEIPT_SHA256',hashlib.sha256(TEST_OWNER_BYTES).hexdigest())



def legacy_records():
    sessions=[];heartbeats=[];ledger=[];transactions=[]
    for i in range(3):
        sid=f'SYNTHETIC-legacy-{i}';at=NOW-timedelta(minutes=5-i)
        end=at+timedelta(seconds=17)
        sessions.append(dict(id=sid,user_id='user-1',content_type='audio',content_id='the-selfish-giant',
            created_at=at,lease_issued_at=at,lease_version=2,last_sequence=1,status='ended',
            billing_active=False,settlement_at=end,last_billed_at=end,lease_expires_at=end,seconds_consumed=17))
        heartbeats.append(dict(id='hb-'+sid,user_id='user-1',session_id=sid,lease_version=1,sequence=1,
            active=True,playback_state='playing',idempotency_key='client-'+sid,created_at=at,
            response=dict(session_id=sid,content_type='audio',content_id='the-selfish-giant',lease_version=2,
                deducted_seconds=0,balance_seconds=100,status='Running',lease_expires_at=(at+timedelta(seconds=20)).isoformat())))
        ledger.append(dict(id='ledger-'+sid,user_id='user-1',session_id=sid,event_type='TIME_DEBIT',debit=17,
            credit=0,signed_seconds=-17,idempotency_key=f'terminal:{sid}:2:ended',source_transaction_id='tx-'+sid))
        transactions.append(dict(id='tx-'+sid,user_id='user-1',session_id=sid,type='consume',seconds=-17,actor='reading-pass-v2'))
    return dict(user_id='user-1',ids=[s['id'] for s in sessions],original_started_at=proof.ORIGINAL_WINDOW_START,
        observed_at=NOW,sessions=sessions,heartbeats=heartbeats,ledger=ledger,transactions=transactions)


def authority_files(tmp_path):
    def put(name,value):
        path=tmp_path/name;path.write_text(json.dumps(value));path.chmod(0o600)
        return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    created=NOW-timedelta(seconds=1);expires=NOW+timedelta(minutes=5)
    journal=(tmp_path/'journal');journal.mkdir(mode=0o700);ji=journal.stat()
    journal_ref=dict(path=str(journal.resolve()),device=ji.st_dev,inode=ji.st_ino)
    b=dict(journal=journal_ref,schema=proof.SCHEMA,action='provision',operation_id='SYNTHETIC_operation_0001',user_id='user-1',
        auth_session_id='auth-1',slug='the-selfish-giant',country='IN',descriptor_sha256=scope.native.DESCRIPTOR,
        package_version=scope.PACKAGE,created_at=created.isoformat(),expires_at=expires.isoformat(),expected_state_sha256=op.digest({'workflow':None,'grants':[]}))
    # Fixture-only expected pin is substituted by synthetic_owner_pin. No actual
    # owner receipt, account binding or execution approval is stored in Git.
    private_owner=tmp_path/'owner.json';private_owner.write_bytes(TEST_OWNER_BYTES);private_owner.chmod(0o600)
    b['owner']={'path':str(private_owner),'sha256':hashlib.sha256(TEST_OWNER_BYTES).hexdigest()}
    common=dict(user_id_sha256=proof.identity_hash('user-1'),auth_session_id_sha256=proof.identity_hash('auth-1'),
        owner_receipt_sha256=b['owner']['sha256'],observed_at=created.isoformat(),expires_at=expires.isoformat())
    b['identity']=put('identity.json',dict(common,schema='earnalism.native_audio_review_member_binding.v1',source='OWNER_SELECTED_AUTHENTICATED_NORMAL_MEMBER'))
    b['execution']=put('execution.json',dict(common,schema='earnalism.native_audio_review_execution.v1',
        decision='ACCEPTED_EXACT_SCOPED_METADATA_OPERATION',action='provision',operation_id=b['operation_id'],
        original_ceiling_seconds=120,journal=journal_ref,**{k:b[k] for k in ('slug','country','descriptor_sha256','package_version')}))
    b['source']=put('source.json',dict(schema='earnalism.native_audio_review_serving_source.v1',
        status='QUALIFIED_EXACT_SERVING_SOURCE',merged_main_commit='1'*40,runtime_source_sha256='2'*64,
        source_files_sha256=cli.local_source_sha256(),observed_at=created.isoformat(),expires_at=expires.isoformat(),**{k:b[k] for k in ('slug','descriptor_sha256','package_version')}))
    records=legacy_records();projection=proof.reconcile_legacy(**records)
    b['legacy']=put('legacy.json',dict(schema='earnalism.native_audio_review_legacy_scope.v1',
        user_id_sha256=common['user_id_sha256'],owner_receipt_sha256=b['owner']['sha256'],
        historical_metering_source_sha256=proof.HISTORICAL_SOURCE,historical_runtime_source_sha256=proof.HISTORICAL_RUNTIME,
        original_session_ids=records['ids'],original_started_at=records['original_started_at'].isoformat(),
        observed_at=NOW.isoformat(),projection_sha256=projection['projection_sha256']))
    b['intent']=put('intent.json',dict(schema='earnalism.native_audio_review_intent.v1',operation_id=b['operation_id'],action='provision',
        journal=journal_ref,execution_receipt_sha256=b['execution']['sha256'],expected_state_sha256=b['expected_state_sha256']))
    return b,put('authority.json',b),put


def test_actual_parser_and_admitted_identity_has_no_positive_default(tmp_path):
    _,ref,_=authority_files(tmp_path)
    a=op.admit_authority(ref['path'],ref['sha256'],now=NOW)
    assert a.user_id=='user-1' and a.original_started_at<NOW
    assert not hasattr(a,'legacy_time_bound_microseconds')
    assert not hasattr(a,'legacy_credit_bound_seconds')


@pytest.mark.parametrize('mutation',['prepared-signin','wrong-answer','wrong-member','wrong-source','wrong-package','wrong-action','expired','unknown-legacy','wrong-intent'])
def test_private_parser_rejects_incomplete_or_rebound_authority(tmp_path,mutation):
    b,ref,put=authority_files(tmp_path)
    if mutation=='prepared-signin':b['owner']=put('owner-prepared.json',{'status':'OWNER_PRIVATE_SIGNIN_HANDOFF_READY_NO_SUBMISSION'})
    elif mutation=='wrong-answer':b['owner']=put('owner-other.json',dict(questionItemId=json.dumps(['request_user_input_async',proof.ORIGINAL_QUESTION_ID,0]),question=proof.ORIGINAL_QUESTION,answer='yes'))
    elif mutation=='wrong-member':b['user_id']='other-user'
    elif mutation=='wrong-source':b['source']=put('source-other.json',{'status':'PASS'})
    elif mutation=='wrong-package':b['package_version']='sha256-'+'f'*64
    elif mutation=='wrong-action':b['action']='reset'
    elif mutation=='expired':b['expires_at']=(NOW-timedelta(seconds=1)).isoformat()
    elif mutation=='unknown-legacy':b['legacy']=put('legacy-other.json',{'lineage_status':'PASS'})
    else:b['intent']=put('intent-other.json',{'schema':'earnalism.native_audio_review_intent.v1'})
    ref=put('changed-authority.json',b)
    with pytest.raises((proof.AdmissionStop,KeyError,TypeError)):
        proof.parse_authority(ref['path'],ref['sha256'],now=NOW)


def test_private_file_rejects_permissions_hash_and_symlink(tmp_path):
    _,ref,_=authority_files(tmp_path);path=Path(ref['path'])
    with pytest.raises(proof.AdmissionStop):proof.private_json(path,'f'*64)
    path.chmod(0o644)
    with pytest.raises(proof.AdmissionStop):proof.private_json(path,ref['sha256'])
    path.chmod(0o600);link=tmp_path/'link';link.symlink_to(path)
    with pytest.raises(OSError):proof.private_json(link,ref['sha256'])


def test_complete_legacy_bound_is_measured_separately_from_credit():
    r=legacy_records();r['sessions'][0]['settlement_at']-=timedelta(microseconds=500000)
    r['sessions'][0]['last_billed_at']=r['sessions'][0]['lease_expires_at']=r['sessions'][0]['settlement_at']
    result=proof.reconcile_legacy(**r)
    assert result['legacy_credit_bound_seconds']==51
    # Three uncapped terminal endpoints each lose at most 999us in BSON.
    assert result['legacy_time_bound_microseconds']==50500000+3*999
    assert result['lineage_status']=='CONSERVATIVE_PROVEN_BOUND'


@pytest.mark.parametrize('mutation',['zero-debit-heartbeat-missing','version-gap','unknown-session','active-tail','missing-settlement','late-renewal','unlinked-transaction','wrong-ledger','wrong-member','unbounded-lease','duplicate-heartbeat','terminal-debit-missing'])
def test_legacy_incomplete_or_unknown_history_holds(mutation):
    r=legacy_records()
    if mutation=='zero-debit-heartbeat-missing':r['heartbeats'].pop()
    elif mutation=='version-gap':r['heartbeats'][0]['lease_version']=2
    elif mutation=='unknown-session':r['sessions'].append(dict(r['sessions'][0],id='unknown'))
    elif mutation=='active-tail':r['sessions'][0]['billing_active']=True
    elif mutation=='missing-settlement':r['sessions'][0].pop('settlement_at')
    elif mutation=='late-renewal':r['heartbeats'][0]['created_at']=NOW+timedelta(seconds=1)
    elif mutation=='unlinked-transaction':r['transactions'].pop()
    elif mutation=='wrong-ledger':r['ledger'][0]['debit']=18
    elif mutation=='wrong-member':r['transactions'][0]['user_id']='other'
    elif mutation=='unbounded-lease':r['heartbeats'][0]['response']['lease_expires_at']=(NOW+timedelta(days=1)).isoformat()
    elif mutation=='duplicate-heartbeat':r['heartbeats'].append(copy.deepcopy(r['heartbeats'][0]))
    else:r['ledger'].pop();r['transactions'].pop()
    with pytest.raises((proof.AdmissionStop,KeyError,TypeError)):
        proof.reconcile_legacy(**r)


def test_default_local_launcher_does_not_import_runtime_or_read_env(monkeypatch,capsys):
    monkeypatch.setenv('MONGO_URL','MUST-NOT-BE-READ')
    monkeypatch.setattr(cli,'runtime',AsyncMock(side_effect=AssertionError('runtime forbidden')))
    assert cli.main([])==2
    assert 'LOCAL_ONLY' in capsys.readouterr().out
    cli.runtime.assert_not_called()


def test_exclusive_intent_prevents_unknown_outcome_replay(tmp_path):
    tmp_path.chmod(0o700)
    cli.seal(tmp_path,'SYNTHETIC.attempt.json',{'status':'INTENT'})
    with pytest.raises(FileExistsError):cli.seal(tmp_path,'SYNTHETIC.attempt.json',{'status':'RESET'})
    assert json.loads((tmp_path/'SYNTHETIC.attempt.json').read_text())=={'status':'INTENT'}


def operator_db(records):
    from backend.tests.test_native_audio_review_scope import seeded,Client
    db,_,_=seeded(datetime.now(timezone.utc));db[scope.WORKFLOWS].rows=[];db[scope.GRANTS].rows=[]
    for name,key in [('reading_pass_sessions','sessions'),('reading_pass_heartbeats','heartbeats'),
        ('wallet_ledger','ledger'),('wallet_transactions','transactions')]:db[name].rows=copy.deepcopy(records[key])
    db[op.OPERATIONS].rows=[]
    async def names(**kwargs):return list(op.NAMESPACE_INDEXES)
    db.list_collection_names=names
    for name,(idx,keys) in op.NAMESPACE_INDEXES.items():
        async def info(idx=idx,keys=keys):return {'_id_':{'key':[('_id',1)]},idx:{'key':keys}}
        db[name].index_information=info
    return db,Client(db)


def test_actual_operator_provision_snapshot_readback_and_guarded_close(tmp_path,monkeypatch):
    async def run():
        _,ref,_=authority_files(tmp_path);a=op.admit_authority(ref['path'],ref['sha256'],now=NOW)
        db,client=operator_db(legacy_records())
        monkeypatch.setattr(op.native,'rights_for_review_phase',lambda *args,**kwargs:({'package_version':scope.PACKAGE},{}))
        result=await op.execute_one_shot(db=db,client=client,admitted=a,book={})
        assert result['status']=='COMMIT_RECEIPT_OBSERVED' and client.commits==1
        # Three submillisecond endpoint bounds leave 68 whole seconds, never 69.
        assert result['actual_remaining_seconds']==68
        assert db.users.rows[0]['reading_seconds_balance']==300
        from dataclasses import replace
        gid=db[scope.GRANTS].rows[0]['_id']
        state=op.digest({'workflow':db[scope.WORKFLOWS].rows[0],'grants':db[scope.GRANTS].rows})
        close=replace(a,action='close',operation_id='SYNTHETIC_close_00001',grant_id=gid,
            expected_state_sha256=state,authority_sha256='f'*64)
        closed=await op.execute_one_shot(db=db,client=client,admitted=close,book={})
        assert closed['status']=='COMMIT_RECEIPT_OBSERVED' and closed['actual_remaining_seconds'] is None
        assert db[scope.GRANTS].rows[0]['state']=='CLOSED' and db[scope.WORKFLOWS].rows[0]['used_credit_seconds']==51
        assert db.users.rows[0]['reading_seconds_balance']==300
    asyncio.run(run())


@pytest.mark.parametrize('retained_state',['CLOSED','OPEN','UNKNOWN',None])
def test_actual_operator_missing_workflow_any_history_never_reinitializes(tmp_path,monkeypatch,retained_state):
    async def run():
        _,ref,_=authority_files(tmp_path);a=op.admit_authority(ref['path'],ref['sha256'],now=NOW)
        db,client=operator_db(legacy_records())
        wid='original120-'+op.digest({'member':a.user_id,'original_owner_scope':a.owner_scope_sha256})
        db[scope.GRANTS].rows=[dict(_id='SYNTHETIC-old',user_id=a.user_id,workflow_id=wid,state=retained_state)]
        from dataclasses import replace
        a=replace(a,expected_state_sha256=op.digest({'workflow':None,'grants':db[scope.GRANTS].rows}))
        monkeypatch.setattr(op.native,'rights_for_review_phase',lambda *args,**kwargs:({'package_version':scope.PACKAGE},{}))
        before=copy.deepcopy((db[scope.GRANTS].rows,db.users.rows))
        with pytest.raises(op.OperatorStop,match='MISSING_WORKFLOW_WITH_RETAINED'):
            await op.execute_one_shot(db=db,client=client,admitted=a,book={})
        assert db[scope.WORKFLOWS].rows==[] and db[op.OPERATIONS].rows==[]
        assert before==(db[scope.GRANTS].rows,db.users.rows)
    asyncio.run(run())


def test_unknown_commit_calls_actual_operation_once_and_status_never_replays(tmp_path,monkeypatch):
    async def run():
        _,ref,_=authority_files(tmp_path);a=op.admit_authority(ref['path'],ref['sha256'],now=NOW)
        db,client=operator_db(legacy_records());client.unknown=True
        monkeypatch.setattr(op.native,'rights_for_review_phase',lambda *args,**kwargs:({'package_version':scope.PACKAGE},{}))
        with pytest.raises(op.OutcomeUnknown,match='COMMIT_OUTCOME_UNVERIFIED'):
            await op.execute_one_shot(db=db,client=client,admitted=a,book={})
        assert client.commits==1 and len(db[op.OPERATIONS].rows)==1
        result=await op.status(db,client,a)
        assert result['status']=='COMMIT_RECEIPT_OBSERVED' and result['replay_permitted'] is False
        assert client.commits==1
    asyncio.run(run())


@pytest.mark.parametrize('mutation',['schema','workflow','package','descriptor','country','lineage','intent','workflow-owner','workflow-lineage'])
def test_consistent_status_rejects_changed_target_or_intent(tmp_path,monkeypatch,mutation):
    async def run():
        _,ref,_=authority_files(tmp_path);a=op.admit_authority(ref['path'],ref['sha256'],now=NOW)
        db,client=operator_db(legacy_records())
        monkeypatch.setattr(op.native,'rights_for_review_phase',lambda *args,**kwargs:({'package_version':scope.PACKAGE},{}))
        await op.execute_one_shot(db=db,client=client,admitted=a,book={})
        key={'workflow':'workflow_id','package':'package_version','descriptor':'descriptor_sha256','lineage':'legacy_lineage_sha256'}.get(mutation,mutation)
        if mutation=='intent':db[op.OPERATIONS].rows[0]['private_intent_sha256']='f'*64
        elif mutation=='workflow-owner':db[scope.WORKFLOWS].rows[0]['owner_scope_sha256']='f'*64
        elif mutation=='workflow-lineage':db[scope.WORKFLOWS].rows[0]['legacy_lineage_sha256']='f'*64
        else:db[scope.GRANTS].rows[0][key]='changed'
        with pytest.raises(op.OperatorStop):await op.status(db,client,a)
    asyncio.run(run())


def test_missing_status_receipt_is_not_abort_or_positive_allowance(tmp_path):
    async def run():
        _,ref,_=authority_files(tmp_path);a=op.admit_authority(ref['path'],ref['sha256'],now=NOW)
        db,client=operator_db(legacy_records());result=await op.status(db,client,a)
        assert result['status']=='OUTCOME_NOT_PROVEN_NO_MUTATION_RETRY'
        assert result['actual_remaining_seconds'] is None and result['replay_permitted'] is False
    asyncio.run(run())


def test_changing_private_journal_directory_denies_before_runtime(tmp_path,monkeypatch,capsys):
    b,ref,put=authority_files(tmp_path);other=tmp_path/'other';other.mkdir(mode=0o700)
    monkeypatch.setattr(cli,'runtime',AsyncMock(side_effect=AssertionError('No connection permitted')))
    assert cli.main(['--execute','--authority',ref['path'],'--authority-sha256',ref['sha256'],'--journal',str(other)])==2
    assert 'RUNTIME_JOURNAL_NOT_APPROVED' in capsys.readouterr().out
    cli.runtime.assert_not_called()


def test_namespace_only_explicit_preparation_preserves_accounts_and_existing_indexes(tmp_path,monkeypatch):
    async def run():
        _,ref,_=authority_files(tmp_path);a=op.admit_authority(ref['path'],ref['sha256'],now=NOW)
        from dataclasses import replace
        a=replace(a,action='prepare-namespace')
        db,client=operator_db(legacy_records());created=[];indexes={}
        async def names(**kwargs):return list(indexes)
        async def create(name):
            created.append(('collection',name));indexes[name]={'_id_':{'key':[('_id',1)]}}
        db.list_collection_names=names;db.create_collection=create
        for name in op.NAMESPACE_INDEXES:
            async def info(name=name):return copy.deepcopy(indexes[name])
            async def index(keys,name=None,unique=False,collection=name):
                created.append(('index',collection));indexes[collection][name]={'key':keys,'unique':unique}
            db[name].index_information=info;db[name].create_index=index
        monkeypatch.setattr(op.native,'rights_for_review_phase',lambda *args,**kwargs:({'package_version':scope.PACKAGE},{}))
        before=copy.deepcopy((db.users.rows,db.wallet_ledger.rows,db.wallet_transactions.rows))
        result=await op.prepare_namespace_one_shot(db=db,client=client,admitted=a,book={})
        assert result['status']=='SCOPED_NAMESPACES_OBSERVED_QUALIFIED_NO_GRANT_CREATED'
        assert len(created)==6 and set(indexes)==set(op.NAMESPACE_INDEXES)
        assert before==(db.users.rows,db.wallet_ledger.rows,db.wallet_transactions.rows)
        assert db[scope.GRANTS].rows==[] and db[scope.WORKFLOWS].rows==[]
    asyncio.run(run())


@pytest.mark.parametrize('bad',['ttl','wrong-key','unique'])
def test_namespace_conflicts_are_denied_without_repair_or_drop(bad):
    async def run():
        db,_=operator_db(legacy_records());name=scope.WORKFLOWS;idx,keys=op.NAMESPACE_INDEXES[name]
        value={'key':keys}
        if bad=='ttl':value['expireAfterSeconds']=1
        elif bad=='wrong-key':value['key']=[('other',1)]
        else:value['unique']=True
        async def info():return {'_id_':{'key':[('_id',1)]},idx:value}
        db[name].index_information=info
        with pytest.raises(op.OperatorStop):await op.namespace_status(db)
    asyncio.run(run())


@pytest.mark.parametrize('kind',['operation','session','ledger','transaction'])
def test_missing_workflow_with_any_exact_own_reference_holds_no_counter_reset(tmp_path,monkeypatch,kind):
    async def run():
        _,ref,_=authority_files(tmp_path);a=op.admit_authority(ref['path'],ref['sha256'],now=NOW)
        db,client=operator_db(legacy_records());wid='original120-'+op.digest({'member':a.user_id,'original_owner_scope':a.owner_scope_sha256})
        row={'id':'SYNTHETIC-retained','user_id':a.user_id}
        collection=op.OPERATIONS
        if kind=='operation':row.update(_id='SYNTHETIC-prior',workflow_id=wid)
        elif kind=='session':collection='reading_pass_sessions';row['scope']={'native_audio_review_workflow_id':wid}
        elif kind=='ledger':collection='wallet_ledger';row['metadata']={'native_audio_review_workflow_id':wid}
        else:collection='wallet_transactions';row['native_audio_review_workflow_id']=wid
        db[collection].rows.append(row)
        monkeypatch.setattr(op.native,'rights_for_review_phase',lambda *args,**kwargs:({'package_version':scope.PACKAGE},{}))
        before=copy.deepcopy((db[scope.WORKFLOWS].rows,db[scope.GRANTS].rows,db[op.OPERATIONS].rows,db.users.rows))
        with pytest.raises(op.OperatorStop,match='MISSING_WORKFLOW_WITH_ANY_RETAINED_REFERENCE'):
            await op.execute_one_shot(db=db,client=client,admitted=a,book={})
        assert before==(db[scope.WORKFLOWS].rows,db[scope.GRANTS].rows,db[op.OPERATIONS].rows,db.users.rows)
    asyncio.run(run())


def test_expiry_during_actual_legacy_reads_prevents_initial_mutation(tmp_path,monkeypatch):
    async def run():
        _,ref,_=authority_files(tmp_path);a=op.admit_authority(ref['path'],ref['sha256'],now=NOW)
        db,client=operator_db(legacy_records());clock=[NOW]
        class Clock(datetime):
            @classmethod
            def now(cls,tz=None):return clock[0]
        monkeypatch.setattr(op,'datetime',Clock)
        monkeypatch.setattr(op.native,'rights_for_review_phase',lambda *args,**kwargs:({'package_version':scope.PACKAGE},{}))
        original=op.settled_legacy
        async def slow(*args,**kwargs):
            result=await original(*args,**kwargs);clock[0]=a.expires_at+timedelta(microseconds=1);return result
        monkeypatch.setattr(op,'settled_legacy',slow)
        with pytest.raises(op.OperatorStop,match='EXPIRED_BEFORE_MUTATION'):
            await op.execute_one_shot(db=db,client=client,admitted=a,book={})
        assert db[scope.WORKFLOWS].rows==[] and db[scope.GRANTS].rows==[] and client.commits==0
    asyncio.run(run())


def test_expiry_after_operation_body_aborts_instead_of_commit(tmp_path,monkeypatch):
    async def run():
        _,ref,_=authority_files(tmp_path);a=op.admit_authority(ref['path'],ref['sha256'],now=NOW)
        db,client=operator_db(legacy_records());clock=[NOW]
        class Clock(datetime):
            @classmethod
            def now(cls,tz=None):return clock[0]
        monkeypatch.setattr(op,'datetime',Clock)
        monkeypatch.setattr(op.native,'rights_for_review_phase',lambda *args,**kwargs:({'package_version':scope.PACKAGE},{}))
        original=op.operation
        async def late(*args,**kwargs):
            result=await original(*args,**kwargs);clock[0]=a.expires_at+timedelta(microseconds=1);return result
        monkeypatch.setattr(op,'operation',late)
        with pytest.raises(op.OperatorStop,match='EXPIRED_BEFORE_MUTATION'):
            await op.execute_one_shot(db=db,client=client,admitted=a,book={})
        assert db[scope.WORKFLOWS].rows==[] and db[scope.GRANTS].rows==[] and db[op.OPERATIONS].rows==[]
        assert client.commits==0
    asyncio.run(run())


def test_expiry_between_namespace_ddl_calls_stops_next_write_status_only(tmp_path,monkeypatch):
    async def run():
        _,ref,_=authority_files(tmp_path);a=op.admit_authority(ref['path'],ref['sha256'],now=NOW)
        from dataclasses import replace
        a=replace(a,action='prepare-namespace');db,client=operator_db(legacy_records());clock=[NOW];writes=[]
        class Clock(datetime):
            @classmethod
            def now(cls,tz=None):return clock[0]
        monkeypatch.setattr(op,'datetime',Clock)
        monkeypatch.setattr(op.native,'rights_for_review_phase',lambda *args,**kwargs:({'package_version':scope.PACKAGE},{}))
        async def plan(*args):return {'qualified':False,'plan':[{'collection':scope.WORKFLOWS,'create_collection':True,'create_index':True}]}
        monkeypatch.setattr(op,'namespace_status',plan)
        async def create(name):writes.append(('collection',name));clock[0]=a.expires_at+timedelta(microseconds=1)
        async def index(*args,**kwargs):writes.append(('index','FORBIDDEN'))
        db.create_collection=create;db[scope.WORKFLOWS].create_index=index
        with pytest.raises(op.OutcomeUnknown,match='NAMESPACE_PARTIAL_OUTCOME'):
            await op.prepare_namespace_one_shot(db=db,client=client,admitted=a,book={})
        assert writes==[('collection',scope.WORKFLOWS)] and db[scope.GRANTS].rows==[]
    asyncio.run(run())


# These tests use actual local BSON encoding, not a generic timestamp tolerance.
def test_legacy_bson_json_precision_and_terminal_upper_bound():
    from bson import BSON
    from bson.codec_options import CodecOptions
    r=legacy_records()
    for row,h in zip(r['sessions'],r['heartbeats']):
        start=h['created_at']
        precise_start=start+timedelta(microseconds=125)
        h['created_at']=BSON.encode({'at':precise_start}).decode(codec_options=CodecOptions(tz_aware=True))['at']
        h['response']['lease_expires_at']=(precise_start+timedelta(seconds=20)).isoformat()
        precise_stop=start+timedelta(seconds=17,microseconds=900)
        persisted_stop=BSON.encode({'at':precise_stop}).decode(codec_options=CodecOptions(tz_aware=True))['at']
        row['settlement_at']=row['last_billed_at']=row['lease_expires_at']=persisted_stop
    before=proof.digest(r)
    result=proof.reconcile_legacy(**r)
    assert result['legacy_credit_bound_seconds']==51
    assert result['legacy_time_bound_microseconds']==51000000+3*999
    assert result['legacy_time_bound_microseconds']>=51000000+3*900
    assert proof.digest(r)==before  # No raw timestamp/evidence rewriting.


@pytest.mark.parametrize('excess_us,accepted',[(0,True),(125,True),(999,True),(1000,False),(1001,False),(1000000,False)])
def test_legacy_precision_horizon_is_exact_bson_bin(excess_us,accepted):
    r=legacy_records();h=r['heartbeats'][0]
    h['response']['lease_expires_at']=(h['created_at']+timedelta(seconds=20,microseconds=excess_us)).isoformat()
    if accepted:
        assert proof.reconcile_legacy(**r)['legacy_credit_bound_seconds']==51
    else:
        with pytest.raises(proof.AdmissionStop,match='LEGACY_LEASE_HORIZON_UNKNOWN'):
            proof.reconcile_legacy(**r)


@pytest.mark.parametrize('field',['heartbeat','created','settled'])
def test_legacy_non_bson_persisted_precision_does_not_get_tolerance(field):
    r=legacy_records()
    if field=='heartbeat':r['heartbeats'][0]['created_at']+=timedelta(microseconds=1)
    elif field=='created':r['sessions'][0]['created_at']+=timedelta(microseconds=1)
    else:r['sessions'][0]['settlement_at']+=timedelta(microseconds=1)
    with pytest.raises(proof.AdmissionStop,match='LEGACY_PERSISTED_TIMESTAMP_NOT_BSON_MILLISECOND'):
        proof.reconcile_legacy(**r)


def test_legacy_submillisecond_intermediate_and_terminal_bounds_are_conservative():
    from bson import BSON
    from bson.codec_options import CodecOptions
    start=NOW-timedelta(minutes=1)
    precise_next=start+timedelta(seconds=3,microseconds=876)
    endpoint=BSON.encode({'at':precise_next}).decode(codec_options=CodecOptions(tz_aware=True))['at']
    expiry=start+timedelta(seconds=20,microseconds=125)
    assert proof._legacy_interval_upper_microseconds(start,endpoint,expiry)==3000999
    assert proof._legacy_interval_upper_microseconds(start,endpoint,expiry)>=3000876
    # Service sees persisted expiry, not the precise response's trailing125us.
    assert proof._legacy_interval_upper_microseconds(start,start+timedelta(seconds=25),expiry)==20000000
    assert proof._legacy_interval_upper_microseconds(start,start,start+timedelta(seconds=20))==999


def _legacy_many_synthetic_sessions(count,duration):
    r=legacy_records();template={k:copy.deepcopy(v[0]) for k,v in r.items() if k in ('sessions','heartbeats','ledger','transactions')}
    for k in template:r[k]=[]
    for i in range(count):
        sid=f'SYNTHETIC-precision-{i}';at=NOW-timedelta(minutes=20-i);end=at+timedelta(seconds=duration)
        for k in template:
            row=copy.deepcopy(template[k]);row['id']=sid if k=='sessions' else f'{k}-{sid}'
            if k=='sessions':row.update(created_at=at,lease_issued_at=at,settlement_at=end,last_billed_at=end,lease_expires_at=end,seconds_consumed=duration)
            else:row['session_id']=sid
            if k=='heartbeats':row.update(created_at=at,idempotency_key='client-'+sid);row['response'].update(session_id=sid,lease_expires_at=(at+timedelta(seconds=20,microseconds=125)).isoformat())
            elif k=='ledger':row.update(debit=duration,signed_seconds=-duration,idempotency_key=f'terminal:{sid}:2:ended',source_transaction_id='transactions-'+sid)
            elif k=='transactions':row['seconds']=-duration
            r[k].append(row)
    r['ids']=[row['id'] for row in r['sessions']]
    return r


def test_legacy_precision_preserves_exact120_cap_without_epsilon():
    r=_legacy_many_synthetic_sessions(6,20)
    assert proof.reconcile_legacy(**r)['legacy_time_bound_microseconds']==120000000
    r=_legacy_many_synthetic_sessions(8,15)
    assert sum(row['debit'] for row in r['ledger'])==120
    with pytest.raises(proof.AdmissionStop,match='ORIGINAL_120_BOUND_EXHAUSTED_OR_USAGE_FLOOR_MISSING'):
        proof.reconcile_legacy(**r)  #120000000 raw+7992 uncertainty must HOLD.
