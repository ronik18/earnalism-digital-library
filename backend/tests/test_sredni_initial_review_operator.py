"""Synthetic admission/metadata transactions only, never actual owner authority."""
import asyncio,copy,hashlib,json,os
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from pathlib import Path
from types import SimpleNamespace
import pytest
import sredni_initial_review_authority as authority
import sredni_initial_review_operator as operator
import sredni_initial_review_scope as scope
import sredni_initial_review_profile as profile
import sredni_initial_review_operator_cli as cli
from test_sredni_initial_review_domain import seeded,synthetic_policy
from backend.tests.test_native_audio_review_scope import Client
from domain.reading_pass import ReadingPassError
from backend.tests import test_reading_pass_service_concurrency as fake_store


def book():
    path=Path(__file__).parent/'fixtures/sredni-initial-sourceqa-staged-book.json'
    return json.loads(path.read_text())


@pytest.fixture
def packet(tmp_path,monkeypatch):
    now=datetime.now(timezone.utc);journal=(tmp_path/'journal');journal.mkdir(mode=0o700)
    st=journal.stat();jr={'path':str(journal.resolve()),'device':st.st_dev,'inode':st.st_ino}
    def save(name,value):
        path=tmp_path/name;raw=(json.dumps(value,indent=2)+'\n').encode();path.write_bytes(raw);path.chmod(0o600)
        return {'path':str(path),'sha256':hashlib.sha256(raw).hexdigest()}
    question='SYNTHETIC TEST ONLY approve60/3/900; no actual owner response'
    owner={'schema':'earnalism.owner_sredni_initial_review_permission.v1','status':'APPROVED','question_id':'SYNTHETIC-question',
        'question':question,'question_sha256':hashlib.sha256(question.encode()).hexdigest(),'answer':'SYNTHETIC_ONLY',
        'slug':profile.SLUG,'descriptor_sha256':profile.DESCRIPTOR,'package_version':profile.PACKAGE,
        'maximum_seconds':60,'maximum_starts':3,'maximum_grant_lifetime_seconds':900,'existing_credit_only':True,
        'new_purchase_or_original120_reset':False,'private_mongo_metadata_scope':'SREDNI_ONLY_THREE_COLLECTIONS_AND_REQUIRED_INDEXES'}
    own=save('owner.json',owner);identity=scope.identity_binding('user-1','auth-1')
    who=save('identity.json',{'schema':'earnalism.sredni_initial_review_actual_member.v1','source':'OWNER_SELECTED_AUTHENTICATED_NORMAL_MEMBER',
        'user_id':'user-1','auth_session_id':'auth-1','identity_binding_sha256':identity,'users_me_http':200,'devices_http':200,'observed_at':now.isoformat()})
    source=save('source.json',{'schema':'earnalism.sredni_initial_review_actual_serving_source.v1',
        'scope':'ACTUAL_SOURCE_RUNTIME_STARTUP_RECOVERY_QUALIFIED','source_sha':'a'*40,'runtime_sha256':'b'*64,
        'source_files_sha256':'c'*64,'startup_receipt_sha256':'d'*64,'recovery_receipt_sha256':'e'*64,
        'descriptor_sha256':profile.DESCRIPTOR,'package_version':profile.PACKAGE,'private_stage_validated':True,
        'original120_unchanged':True,'observed_at':now.isoformat()})
    execution=save('execution.json',{'schema':'earnalism.sredni_initial_review_actual_execution.v1','owner_receipt_sha256':own['sha256'],
        'source_receipt_sha256':source['sha256'],'identity_receipt_sha256':who['sha256'],'identity_binding_sha256':identity,
        'mongo_profile_sha256':'9'*64,'database_name_sha256':'8'*64,'source_files_sha256':'c'*64,
        'db_access_scope':'SREDNI_OWN_MEMBER_METADATA_ONLY','uri_or_secrets_in_output':False,'observed_at':now.isoformat()})
    intent=save('intent.json',{'schema':'earnalism.sredni_initial_review_intent.v1','operation_id':'SYNTHETIC-operation-0001','action':'provision',
        'owner_receipt_sha256':own['sha256'],'expected_state_sha256':'7'*64,'journal':jr})
    bundle={'schema':'earnalism.sredni_initial_review_operation.v1','operation_id':'SYNTHETIC-operation-0001','action':'provision',
        'user_id':'user-1','auth_session_id':'auth-1','slug':profile.SLUG,'descriptor_sha256':profile.DESCRIPTOR,'package_version':profile.PACKAGE,
        'owner':own,'identity':who,'execution':execution,'source':source,'intent':intent,'journal':jr,'expected_state_sha256':'7'*64,
        'expires_at':(now+timedelta(minutes=10)).isoformat(),'grant_expires_at':(now+timedelta(minutes=9)).isoformat(),'grant_id':''}
    path=save('operation.json',bundle)
    monkeypatch.setattr(scope,'load_authority',lambda:{'schema':scope.AUTHORITY_SCHEMA,'accepted':[{'owner_receipt_sha256':own['sha256'],'identity_binding_sha256':identity}]})
    return now,path,bundle,save


def test_exact_local_synthetic_admission_and_no_actual_runtime(packet):
    now,ref,bundle,_=packet;a,_,_=authority.admit(ref['path'],ref['sha256'],now=now)
    assert a.owner_receipt_sha256==bundle['owner']['sha256'] and a.identity_binding_sha256==scope.identity_binding('user-1','auth-1')


@pytest.mark.parametrize('change',['owner','identity','source','execution','intent','schema','journal','expired','cap','source-authority'])
def test_bad_admission_denies_before_any_profile_or_client(packet,change,monkeypatch):
    now,ref,bundle,save=packet;b=copy.deepcopy(bundle)
    if change in ['owner','identity','source','execution','intent']:b[change]['sha256']='0'*64
    elif change=='schema':b['extra_unapproved_scope']=True
    elif change=='journal':b['journal']['inode']+=1
    elif change=='expired':b['expires_at']=(now-timedelta(seconds=1)).isoformat()
    elif change=='source-authority':monkeypatch.setattr(scope,'load_authority',lambda:{'schema':scope.AUTHORITY_SCHEMA,'accepted':[]})
    else:
        owner=json.loads(Path(b['owner']['path']).read_text());owner['maximum_seconds']=120;b['owner']=save('expanded-owner.json',owner)
    changed=save('changed.json',b)
    with pytest.raises((authority.AdmissionStop,ReadingPassError)):authority.admit(changed['path'],changed['sha256'],now=now)


def test_same_immutable_old_attempt_is_status_only_not_new_allowance(packet):
    now,ref,_,_=packet
    with pytest.raises(authority.AdmissionStop):authority.admit(ref['path'],ref['sha256'],now=now+timedelta(hours=1))
    a,_,_=authority.admit(ref['path'],ref['sha256'],now=now+timedelta(hours=1),allow_expired_status=True)
    with pytest.raises(authority.AdmissionStop):authority.current(a,now+timedelta(hours=1))


def admitted(now,*,action='provision',state=None,grant_id=''):
    owner='1'*64;uid='user-1';sid='auth-1'
    return authority.AdmittedOperation('SYNTHETIC-op-0000000001',action,uid,sid,owner,scope.identity_binding(uid,sid),
        '2'*64,'3'*64,'4'*64,'5'*64,state or operator.state_hash(None,[]),now+timedelta(minutes=10),now+timedelta(minutes=9),grant_id,{})


def setup_empty(monkeypatch):
    original=fake_store._matches
    def matches(row,query):
        if '$or' in query:
            return any(matches(row,sub) for sub in query['$or']) and original(row,{k:v for k,v in query.items() if k!='$or'})
        return original(row,query)
    monkeypatch.setattr(fake_store,'_matches',matches)
    now=datetime.now(timezone.utc);db,w,g=seeded(now);synthetic_policy(monkeypatch,g)
    for name in [scope.WORKFLOWS,scope.GRANTS,operator.OPERATIONS]:db[name].rows=[]
    # Metadata status is tested separately; here only transactional operation
    # logic is under test, not a fake production namespace/readiness claim.
    return now,db


class Session:
    in_transaction=True


def test_real_operation_initial_provision_then_exact_status_and_replay_denied(monkeypatch):
    async def run():
        now,db=setup_empty(monkeypatch);a=admitted(now)
        receipt=await operator.operation(db,a,book(),Session())
        assert receipt['action']=='provision';w=db[scope.WORKFLOWS].rows[0];g=db[scope.GRANTS].rows[0]
        scope.validate_workflow(w);assert g['workflow_id']==scope.workflow_id(a.owner_receipt_sha256,a.user_id)
        assert (w['used_microseconds'],w['used_credit_seconds'],w['starts_used'])==(0,0,0)
        result=await operator.status_in_snapshot(db,a,Session());assert result['status']=='COMMIT_RECEIPT_OBSERVED' and result['actual_remaining_seconds'] is None
        with pytest.raises(operator.OperatorStop):await operator.operation(db,a,book(),Session())
        assert len(db[scope.WORKFLOWS].rows)==len(db[scope.GRANTS].rows)==len(db[operator.OPERATIONS].rows)==1
    asyncio.run(run())


@pytest.mark.parametrize('kind',['closed-grant','unknown-grant','malformed-linked-grant','operation','malformed-operation',
    'lease','ledger','transaction','unlinked-lease','unlinked-ledger','unlinked-transaction'])
def test_missing_workflow_any_retained_history_never_reseeds(monkeypatch,kind):
    async def run():
        now,db=setup_empty(monkeypatch);a=admitted(now);wid=operator.workflow_id(a)
        if kind=='malformed-linked-grant':
            db[scope.GRANTS].rows=[{'_id':'retained','workflow_id':wid,'state':None}]
        elif kind.endswith('grant'):
            db[scope.GRANTS].rows=[{'_id':'retained','user_id':a.user_id,'owner_receipt_sha256':a.owner_receipt_sha256,
                'slug':profile.SLUG,'state':'CLOSED' if kind=='closed-grant' else None}]
        elif kind=='operation':db[operator.OPERATIONS].rows=[{'_id':'old','user_id':a.user_id,'workflow_id':wid}]
        elif kind=='malformed-operation':db[operator.OPERATIONS].rows=[{'_id':'old','user_id':a.user_id,'owner_receipt_sha256':a.owner_receipt_sha256}]
        elif kind=='lease':db.reading_pass_sessions.rows=[{'id':'old','user_id':a.user_id,'scope':{scope.WORKFLOW_KEY:wid}}]
        elif kind=='ledger':db.wallet_ledger.rows=[{'id':'old','user_id':a.user_id,'metadata':{scope.WORKFLOW_KEY:wid}}]
        elif kind=='unlinked-lease':db.reading_pass_sessions.rows=[{'id':'old','user_id':a.user_id,'content_id':profile.SLUG,'scope':{scope.SCOPE_KEY:'retained'}}]
        elif kind=='unlinked-ledger':db.wallet_ledger.rows=[{'id':'old','user_id':a.user_id,'metadata':{'content_id':profile.SLUG,scope.SCOPE_KEY:'retained'}}]
        elif kind=='unlinked-transaction':db.wallet_transactions.rows=[{'id':'old','user_id':a.user_id,'content_id':profile.SLUG,scope.SCOPE_KEY:'retained'}]
        else:db.wallet_transactions.rows=[{'id':'old','user_id':a.user_id,scope.WORKFLOW_KEY:wid}]
        a=replace(a,expected_state_sha256=operator.state_hash(None,db[scope.GRANTS].rows))
        before=copy.deepcopy([db[scope.WORKFLOWS].rows,db[scope.GRANTS].rows,db[operator.OPERATIONS].rows])
        with pytest.raises(operator.OperatorStop,match='NO_RESET'):await operator.operation(db,a,book(),Session())
        assert before==[db[scope.WORKFLOWS].rows,db[scope.GRANTS].rows,db[operator.OPERATIONS].rows]
    asyncio.run(run())


def test_close_requires_real_normal_terminal_settlement_and_does_not_reset(monkeypatch):
    async def run():
        now,db=setup_empty(monkeypatch);a=admitted(now);await operator.operation(db,a,book(),Session())
        w=db[scope.WORKFLOWS].rows[0];g=db[scope.GRANTS].rows[0];w.update(used_microseconds=1100000,used_credit_seconds=1,starts_used=1)
        close=replace(a,operation_id='SYNTHETIC-close-0000001',action='close',grant_id=g['_id'],grant_expires_at=g['expires_at'],
            expected_state_sha256=operator.state_hash(w,[g]))
        db.reading_pass_sessions.rows=[{'id':'native','user_id':a.user_id,'scope':{scope.SCOPE_KEY:g['_id']},'status':'active','active_lock':'yes','billing_active':True}]
        with pytest.raises(operator.OperatorStop,match='SETTLEMENT'):await operator.operation(db,close,book(),Session())
        db.reading_pass_sessions.rows[0].update(status='ended',billing_active=False,settlement_at=now);db.reading_pass_sessions.rows[0].pop('active_lock')
        await operator.operation(db,close,book(),Session())
        assert g['state']=='CLOSED' and (w['used_microseconds'],w['used_credit_seconds'],w['starts_used'])==(1100000,1,1)
    asyncio.run(run())


def test_exact_default_cli_no_file_env_profile_or_client_read(monkeypatch,capsys):
    def forbidden(*args,**kwargs):raise AssertionError('NO_PRIVATE_READ_ALLOWED')
    monkeypatch.setattr(authority,'private_json',forbidden)
    assert cli.main(['--check-local'])==0
    assert json.loads(capsys.readouterr().out)['database_access'] is False


def test_exclusive_intent_retained_no_overwrite(tmp_path):
    tmp_path.chmod(0o700);cli.seal(tmp_path,'attempt.json',{'status':'SYNTHETIC_UNCERTAIN'})
    assert (tmp_path/'attempt.json').stat().st_mode&0o777==0o600
    with pytest.raises(FileExistsError):cli.seal(tmp_path,'attempt.json',{'status':'would-reset'})
    assert json.loads((tmp_path/'attempt.json').read_text())['status']=='SYNTHETIC_UNCERTAIN'


def test_unknown_commit_is_status_only_never_second_mutation(monkeypatch):
    async def run():
        now,db=setup_empty(monkeypatch);a=admitted(now);client=Client(db,unknown=True)
        async def qualified(_):return {'qualified':True}
        monkeypatch.setattr(operator,'namespace_status',qualified)
        with pytest.raises(operator.OutcomeUnknown,match='COMMIT_OUTCOME_UNKNOWN'):
            await operator.execute_one_shot(db,client,a,book())
        assert client.commits==1 and len(db[scope.WORKFLOWS].rows)==len(db[scope.GRANTS].rows)==len(db[operator.OPERATIONS].rows)==1
        client.unknown=False
        status=await operator.status(db,client,a);assert status['status']=='COMMIT_RECEIPT_OBSERVED'
        assert status['replay_permitted'] is False and client.commits==1
        with pytest.raises(operator.OperatorStop):await operator.execute_one_shot(db,client,a,book())
        assert client.commits==1
    asyncio.run(run())


def test_midoperation_expiry_aborts_all_metadata(monkeypatch):
    async def run():
        now,db=setup_empty(monkeypatch);a=admitted(now);client=Client(db)
        async def qualified(_):return {'qualified':True}
        monkeypatch.setattr(operator,'namespace_status',qualified)
        actual=authority.current;calls=0
        def expiring(value,*args,**kwargs):
            nonlocal calls
            calls+=1
            if calls==4:raise authority.AdmissionStop('SYNTHETIC_EXPIRED_DURING_AWAIT')
            return actual(value,*args,**kwargs)
        monkeypatch.setattr(authority,'current',expiring)
        with pytest.raises(authority.AdmissionStop):await operator.execute_one_shot(db,client,a,book())
        assert client.commits==0 and not db[scope.WORKFLOWS].rows and not db[scope.GRANTS].rows and not db[operator.OPERATIONS].rows
    asyncio.run(run())


class NamespaceCollection:
    def __init__(self):self.indexes={'_id_':{'key':[('_id',1)],'unique':True}}
    async def index_information(self):return copy.deepcopy(self.indexes)
    async def create_index(self,keys,**kwargs):self.indexes[kwargs['name']]={'key':keys,'unique':kwargs['unique']}
class NamespaceDB:
    def __init__(self):self.collections={}
    def __getitem__(self,name):return self.collections[name]
    async def list_collection_names(self,filter):
        assert set(filter['name']['$in'])==set(operator.NAMESPACE_INDEXES)
        return list(self.collections)


def test_namespace_only_three_names_exact_indexes_and_no_ttl_repair():
    async def run():
        db=NamespaceDB();status=await operator.namespace_status(db)
        assert len(status['plan'])==3 and all(p['create_collection'] for p in status['plan'])
        for name,(index,keys) in operator.NAMESPACE_INDEXES.items():
            db.collections[name]=NamespaceCollection();await db[name].create_index(keys,name=index,unique=False)
        assert (await operator.namespace_status(db))['qualified'] is True
        target=next(iter(db.collections));db[target].indexes['forbidden_ttl']={'key':[('expires_at',1)],'expireAfterSeconds':0}
        before=copy.deepcopy(db[target].indexes)
        with pytest.raises(operator.OperatorStop,match='TTL_FORBIDDEN'):await operator.namespace_status(db)
        assert db[target].indexes==before
    asyncio.run(run())


@pytest.mark.parametrize('field,value',[('schema','wrong'),('slug','the-open-window'),('descriptor_sha256','0'*64),
    ('package_version','sha256-'+'0'*64),('country','US'),('state','UNKNOWN'),('epoch',True),('expires_at',None)])
def test_committed_status_exact_target_scope_not_merely_owner_pair(monkeypatch,field,value):
    async def run():
        now,db=setup_empty(monkeypatch);a=admitted(now);await operator.operation(db,a,book(),Session())
        db[scope.GRANTS].rows[0][field]=value
        with pytest.raises((operator.OperatorStop,ReadingPassError)):
            await operator.status_in_snapshot(db,a,Session())
    asyncio.run(run())


def test_initial_readonly_observation_does_not_initialize_grant_or_allowance(monkeypatch):
    async def run():
        now,db=setup_empty(monkeypatch);a=replace(admitted(now),action='observe',expected_state_sha256=None);client=Client(db)
        async def missing(_):return {'schema':'earnalism.sredni_initial_review_namespace_status.v1','qualified':False,'plan':[]}
        monkeypatch.setattr(operator,'namespace_status',missing)
        result=await operator.observe_initial(db,client,a,book())
        assert result['state_sha256']==operator.state_hash(None,[]) and result['actual_remaining_seconds'] is None
        assert result['workflow'] is None and result['grants']==[] and result['retained_references'] is False
        assert client.commits==0 and not db[scope.WORKFLOWS].rows and not db[scope.GRANTS].rows and not db[operator.OPERATIONS].rows
    asyncio.run(run())


@pytest.mark.parametrize('flag',['--execute','--status','--observe-initial'])
def test_noauthority_runtime_flags_cannot_read_profile_or_construct_client(monkeypatch,flag):
    calls=[]
    def forbidden(*args,**kwargs):calls.append(True);raise AssertionError('NO_PRIVATE_PROFILE_OR_CLIENT')
    monkeypatch.setattr(authority,'private_json',forbidden);monkeypatch.setattr(cli,'runtime',forbidden)
    with pytest.raises(authority.AdmissionStop,match='REAL_AUTHORITY_REQUIRED'):
        cli.main([flag,'--mongo-profile','/nonexistent/private-mongo.json','--database','synthetic-only'])
    assert calls==[]


@pytest.mark.parametrize('qualified',[False,True])
def test_status_output_reports_actual_namespace_readback_without_private_rows(qualified):
    raw={'schema':'earnalism.sredni_initial_review_namespace_status.v1','qualified':qualified,
         'plan':[{'collection':'sredni_initial_review_grants'}],'workflow':{'user_id':'PRIVATE-UID'},'uri':'PRIVATE-URI','replay_permitted':False}
    safe=cli.safe_output(raw)
    assert safe['qualified'] is qualified and safe['actual_remaining_seconds'] is None
    assert safe['status'].endswith('QUALIFIED' if qualified else 'UNQUALIFIED')
    assert 'PRIVATE' not in json.dumps(safe) and 'plan' not in safe and safe['replay_permitted'] is False
