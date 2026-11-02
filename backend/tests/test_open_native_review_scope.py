"""SYNTHETIC scoped rows only. No production/member/allowance claim."""
import asyncio,copy,json,hashlib
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from pathlib import Path
import pytest
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'internal/audiobook_lab/scripts'))
from test_open_window_replacement_release import synthetic_only_open_storage_binding

from backend import native_audio_review_authority as proof
from backend import native_audio_review_scope as scope
from backend import native_audio_review_operator as op
from backend import native_audiobook_profiles as profiles
from backend import open_window_audiobook_replacement as opened
from backend import reading_pass_service as service_module
from backend.reading_pass_service import ReadingPassService
from backend.domain.reading_pass import ReadingPassConfig,ReadingPassError
from backend.tests import test_native_audio_review_operator as fixtures
from backend.tests.test_native_audio_review_scope import seeded,Client,renewal
NOW=fixtures.NOW

@pytest.fixture(autouse=True)
def synthetic_receipt_pins(monkeypatch):
    # Deliberate unit-only pin; no genuine owner receipt or account evidence copied.
    monkeypatch.setattr(proof,'ORIGINAL_OWNER_RECEIPT_SHA256',hashlib.sha256(fixtures.TEST_OWNER_BYTES).hexdigest())


def authority_files(tmp_path,monkeypatch,mutation=None):
    _,ref,put=fixtures.authority_files(tmp_path);b=json.loads(Path(ref['path']).read_text())
    b.update(slug=opened.SLUG,descriptor_sha256=opened.DESCRIPTOR,package_version=opened.ACTUAL_PACKAGE)
    continuation=dict(schema='earnalism.owner_original120_both_titles_reply.v1',question_id=proof.BOTH_TITLES_QUESTION_ID,
        question=proof.BOTH_TITLES_QUESTION,answer='Signed in',original_owner_scope_sha256=b['owner']['sha256'],
        titles=['the-selfish-giant','the-open-window'],maximum_cumulative_existing_credit_seconds=120,
        remaining113_is_historical_not_current_authority=True,current_remaining=None,creates_new_allowance_or_reset=False,
        provenance='SYNTHETIC_UNIT_ONLY_NOT_RUNTIME_AUTHORITY')
    if mutation=='new-owner-root':continuation['original_owner_scope_sha256']='f'*64
    if mutation=='remaining-reset':continuation['current_remaining']=120
    if mutation=='new-allowance':continuation['creates_new_allowance_or_reset']=True
    if mutation=='wrong-question':continuation['question_id']='NOT_OWNER_REPLY'
    b['continuation']=put('SYNTHETIC-continuation.json',continuation)
    monkeypatch.setattr(proof,'BOTH_TITLES_RECEIPT_SHA256',b['continuation']['sha256'])
    for role in ['execution','source']:
        r=json.loads(Path(b[role]['path']).read_text());r.update({k:b[k] for k in ('slug','descriptor_sha256','package_version')})
        b[role]=put('SYNTHETIC-open-'+role+'.json',r)
    intent=json.loads(Path(b['intent']['path']).read_text());intent['execution_receipt_sha256']=b['execution']['sha256']
    b['intent']=put('SYNTHETIC-open-intent.json',intent)
    if mutation=='missing-continuation':b.pop('continuation')
    if mutation=='wrong-descriptor':b['descriptor_sha256']=scope.native.DESCRIPTOR
    return b,put('SYNTHETIC-open-authority.json',b)


def test_open_admission_keeps_original_owner_workflow_root(tmp_path,monkeypatch):
    b,ref=authority_files(tmp_path,monkeypatch);a=op.admit_authority(ref['path'],ref['sha256'],now=NOW)
    assert a.owner_scope_sha256==b['owner']['sha256']!=a.continuation_sha256
    assert a.slug==opened.SLUG and a.package_version==opened.ACTUAL_PACKAGE


@pytest.mark.parametrize('mutation',['missing-continuation','new-owner-root','remaining-reset','new-allowance','wrong-question','wrong-descriptor'])
def test_open_invalid_continuation_or_scope_holds_before_runtime(tmp_path,monkeypatch,mutation):
    _,ref=authority_files(tmp_path,monkeypatch,mutation)
    with pytest.raises((proof.AdmissionStop,ValueError)):
        op.admit_authority(ref['path'],ref['sha256'],now=NOW)


def retained_workflow(a):
    p=proof.reconcile_legacy(**fixtures.legacy_records());wid='original120-'+op.digest({'member':a.user_id,'original_owner_scope':a.owner_scope_sha256})
    return dict(_id=wid,schema=scope.WORKFLOW_SCHEMA,user_id=a.user_id,original_ceiling_seconds=120,
        owner_scope_sha256=a.owner_scope_sha256,legacy_lineage_sha256=a.lineage_evidence_sha256,
        lineage_status=p['lineage_status'],reserved_legacy_microseconds=p['legacy_time_bound_microseconds'],
        reserved_legacy_debit_seconds=p['legacy_credit_bound_seconds'],used_microseconds=p['legacy_time_bound_microseconds']+2000000,
        used_credit_seconds=p['legacy_credit_bound_seconds']+3,native_billable_microseconds=2000000,
        native_wallet_debit_seconds=3,revision=7)


def test_open_provision_preserves_same_workflow_all_cedar_usage_and_close(tmp_path,monkeypatch):
    async def run():
        _,ref=authority_files(tmp_path,monkeypatch);a=op.admit_authority(ref['path'],ref['sha256'],now=NOW)
        db,client=fixtures.operator_db(fixtures.legacy_records());w=retained_workflow(a);db[scope.WORKFLOWS].rows=[w]
        before=copy.deepcopy(w);a=replace(a,expected_state_sha256=op.digest({'workflow':w,'grants':[]}))
        monkeypatch.setattr(opened,'rights_for_review_phase',lambda *args,**kwargs:({'package_version':a.package_version},{}))
        result=await op.execute_one_shot(db=db,client=client,admitted=a,book={})
        current=db[scope.WORKFLOWS].rows[0]
        assert {k:v for k,v in current.items() if k!='revision'}=={k:v for k,v in before.items() if k!='revision'}
        assert result['actual_remaining_seconds']==66 and current['_id']==before['_id']
        assert db[scope.GRANTS].rows[0]['continuation_sha256']==a.continuation_sha256
        assert db.users.rows[0]['reading_seconds_balance']==300
        closed=replace(a,action='close',operation_id='SYNTHETIC_OPEN_CLOSE_0001',grant_id=db[scope.GRANTS].rows[0]['_id'],
            expected_state_sha256=op.digest({'workflow':current,'grants':db[scope.GRANTS].rows}))
        result=await op.execute_one_shot(db=db,client=client,admitted=closed,book={})
        assert result['actual_remaining_seconds'] is None and db[scope.GRANTS].rows[0]['state']=='CLOSED'
        assert db[scope.WORKFLOWS].rows[0]==current
    asyncio.run(run())


def test_open_cannot_initialize_missing_original_workflow_even_without_history(tmp_path,monkeypatch):
    async def run():
        _,ref=authority_files(tmp_path,monkeypatch);a=op.admit_authority(ref['path'],ref['sha256'],now=NOW)
        db,client=fixtures.operator_db(fixtures.legacy_records());before=copy.deepcopy(db.users.rows)
        monkeypatch.setattr(opened,'rights_for_review_phase',lambda *args,**kwargs:({'package_version':a.package_version},{}))
        with pytest.raises(op.OperatorStop,match='OPEN_MUST_REUSE_RETAINED_ORIGINAL120'):
            await op.execute_one_shot(db=db,client=client,admitted=a,book={})
        assert db[scope.WORKFLOWS].rows==db[scope.GRANTS].rows==db[op.OPERATIONS].rows==[]
        assert db.users.rows==before and client.commits==0
    asyncio.run(run())


def open_seed(now):
    db,w,g=seeded(now)
    w['owner_scope_sha256']=g['owner_scope_sha256']=proof.ORIGINAL_OWNER_RECEIPT_SHA256
    g.update(_id='open-window-SYNTHETIC',slug=opened.SLUG,descriptor_sha256=opened.DESCRIPTOR,
        package_version=opened.ACTUAL_PACKAGE,continuation_sha256=proof.BOTH_TITLES_RECEIPT_SHA256)
    ss={scope.SCOPE_KEY:g['_id'],'native_audio_review_workflow_id':w['_id'],
        'native_replacement_authorization_id':g['_id'],'acceptance_test_id':opened.TEST_ID,
        'manifest_version':opened.ACTUAL_PACKAGE,'segmentation_version':opened.DESCRIPTOR,
        'package_version':opened.ACTUAL_PACKAGE,'release_descriptor_sha256':opened.DESCRIPTOR,'release_country':'IN'}
    return db,w,g,ss


def test_actual_shared_service_open_fraction_credit_idempotency_and_ordinary_carry(monkeypatch):
    async def run():
        clock=[datetime.now(timezone.utc)];db,w,g,ss=open_seed(clock[0]);client=Client(db)
        monkeypatch.setattr(service_module,'_now',lambda:clock[0]);svc=ReadingPassService(db=db,client=client,config=ReadingPassConfig(),token_secret='SYNTHETIC')
        user_before=copy.deepcopy(db.users.rows[0]);db.users.rows[0]['reading_fractional_microseconds']=900000
        lease=await svc.start_session(user_id='user-1',auth_session_id='auth-1',device_id='SYNTHETIC',device_label='SYNTHETIC',content_type='audio',content_id=opened.SLUG,scope=ss)
        await svc.renew_lease(**renewal(lease));clock[0]+=timedelta(microseconds=200000)
        await svc.end_session(user_id='user-1',auth_session_id='auth-1',session_id=lease['session_id'])
        w=db[scope.WORKFLOWS].rows[0];assert w['native_billable_microseconds']==200000 and w['native_wallet_debit_seconds']==1
        ordinary=await svc.start_session(user_id='user-1',auth_session_id='auth-1',device_id='SYNTHETIC',device_label='SYNTHETIC',content_type='audio',content_id='ordinary-book',scope={})
        await svc.renew_lease(**renewal(ordinary));clock[0]+=timedelta(microseconds=700000)
        await svc.end_session(user_id='user-1',auth_session_id='auth-1',session_id=ordinary['session_id'])
        assert db[scope.WORKFLOWS].rows[0]['native_billable_microseconds']==200000
        assert db.users.rows[0]['reading_fractional_microseconds']==800000 and 'reader_acceptance_budget' not in db.users.rows[0]
        lease=await svc.start_session(user_id='user-1',auth_session_id='auth-1',device_id='SYNTHETIC',device_label='SYNTHETIC',content_type='audio',content_id=opened.SLUG,scope=ss)
        await svc.renew_lease(**renewal(lease));clock[0]+=timedelta(microseconds=300000)
        await svc.end_session(user_id='user-1',auth_session_id='auth-1',session_id=lease['session_id'])
        w=db[scope.WORKFLOWS].rows[0];assert w['native_billable_microseconds']==500000 and w['native_wallet_debit_seconds']==2
        assert w['used_credit_seconds']==63 and db.users.rows[0]['reading_seconds_balance']==298
    asyncio.run(run())


@pytest.mark.parametrize('mutation',['wrong-continuation','wrong-owner','wrong-package','wrong-descriptor','legacy-cap'])
def test_open_scope_changed_or_global_cap_denied_before_financial_mutation(mutation):
    async def run():
        now=datetime.now(timezone.utc);db,w,g,ss=open_seed(now);before=copy.deepcopy(db.users.rows)
        if mutation=='wrong-continuation':g['continuation_sha256']='f'*64
        elif mutation=='wrong-owner':w['owner_scope_sha256']=g['owner_scope_sha256']='f'*64
        elif mutation=='wrong-package':g['package_version']=scope.PACKAGE
        elif mutation=='wrong-descriptor':ss['release_descriptor_sha256']=scope.native.DESCRIPTOR
        else:db.users.rows[0]['reader_acceptance_budget']={'status':'disabled','maximum_seconds':600};before=copy.deepcopy(db.users.rows)
        with pytest.raises(ReadingPassError):await scope.resolve(db,dict(user_id='user-1',content_type='audio',content_id=opened.SLUG,scope=ss),now,starting=True)
        assert db.users.rows==before and w['native_billable_microseconds']==0
    asyncio.run(run())


def test_default_unbound_open_binding_denies_and_ordinary_book_has_no_new_reads(monkeypatch):
    async def run():
        monkeypatch.setattr(opened,'ACTUAL_PACKAGE',None);monkeypatch.setattr(opened,'FINAL_RELEASE_MANIFEST_SHA256',None)
        class NoDB:
            def __getattr__(self,key):raise AssertionError('unexpected DB read')
        assert await scope.member_scope(NoDB(),{'slug':opened.SLUG},'SYNTHETIC',country='IN',now=NOW) is None
        book={'slug':opened.SLUG,scope.native.FIELD:dict(schema_version=opened.SCHEMA,status='STAGED_PRIVATE',candidate_descriptor_sha256=opened.DESCRIPTOR)}
        with pytest.raises(ReadingPassError):await scope.member_scope(NoDB(),book,'SYNTHETIC',country='IN',now=NOW)
    asyncio.run(run())


@pytest.mark.parametrize('slug',[[],{}])
def test_malformed_ordinary_title_never_queries_member_or_raises_type_error(slug):
    async def run():
        class NoDB:
            def __getattr__(self,key):raise AssertionError('unexpected member lookup')
        assert profiles.review_profile({'slug':slug}) is None
        assert await scope.member_scope(NoDB(),{'slug':slug},'SYNTHETIC',country='IN',now=NOW) is None
    asyncio.run(run())


async def _offline_cli_selection(monkeypatch,tmp_path,slug,*,returned_slug=None):
    """Exercise the real CLI runtime adapter with no profile read or DB call."""
    from types import SimpleNamespace
    from motor import motor_asyncio
    from backend import native_audio_review_operator_cli as cli,catalog_truth
    profile=profiles.profile_for_slug(slug) or profiles.cedar
    admitted=SimpleNamespace(action='provision',slug=slug,descriptor_sha256=profile.DESCRIPTOR,
        package_version=profiles.actual_package(profile),owner_scope_sha256=proof.ORIGINAL_OWNER_RECEIPT_SHA256,
        continuation_sha256=proof.BOTH_TITLES_RECEIPT_SHA256,operation_id='SYNTHETIC_cli_selection_0001')
    journal=(tmp_path/'SYNTHETIC-journal');journal.mkdir(mode=0o700);journal=journal.resolve();st=journal.stat()
    fake_profile=tmp_path/'SYNTHETIC-profile-never-read.json';calls=[];clients=[];executed=[]
    class FakeClient:
        def __init__(self,*args,**kwargs):
            assert kwargs['retryWrites'] is False and kwargs['retryReads'] is False
            self.closed=False;clients.append(self)
        def __getitem__(self,key):assert key=='SYNTHETIC-database';return object()
        def close(self):self.closed=True
    monkeypatch.setattr(motor_asyncio,'AsyncIOMotorClient',FakeClient)
    def private_profile(path,sha):
        assert path==fake_profile and sha=='1'*64 and not fake_profile.exists()
        return {'uri':'mongodb://SYNTHETIC.invalid/never-contacted'}
    monkeypatch.setattr(proof,'private_json',private_profile)
    monkeypatch.setattr(op,'admit_authority',lambda *args,**kwargs:admitted)
    def load(selected,*,include_content):
        calls.append((selected,include_content));return {'slug':returned_slug or selected,'SYNTHETIC':True}
    monkeypatch.setattr(catalog_truth,'load_controlled_artifact_book',load)
    async def execute(**kwargs):executed.append(kwargs);return {'status':'SYNTHETIC_OFFLINE_ONLY'}
    monkeypatch.setattr(op,'execute_one_shot',execute)
    args=SimpleNamespace(journal=journal,mongo_profile=fake_profile,database='SYNTHETIC-database',
        authority=tmp_path/'SYNTHETIC-authority-never-read.json',authority_sha256='2'*64,
        status=False,execute=True,prepare_namespace=False)
    bundle={'journal':dict(path=str(journal),device=st.st_dev,inode=st.st_ino)}
    receipts={'execution':dict(database_name_sha256=proof.identity_hash(args.database),mongo_profile_sha256='1'*64)}
    result=None;error=None
    try:result=await cli.runtime(args,bundle,receipts)
    except (op.OperatorStop,proof.AdmissionStop) as exc:error=exc
    assert clients and all(c.closed for c in clients)
    return result,error,calls,executed,list(journal.iterdir())


@pytest.mark.parametrize('slug',['the-selfish-giant','the-open-window'])
def test_offline_cli_selects_exact_validated_admitted_book(monkeypatch,tmp_path,slug):
    async def run():
        result,error,calls,executed,markers=await _offline_cli_selection(monkeypatch,tmp_path,slug)
        assert error is None and result=={'status':'SYNTHETIC_OFFLINE_ONLY'}
        assert calls==[(slug,False)] and len(executed)==1 and executed[0]['book']['slug']==slug
        assert {p.suffix for p in markers}=={'.json'} and len(markers)==2
    asyncio.run(run())


@pytest.mark.parametrize('case',['unsupported-admitted-title','wrong-returned-title'])
def test_offline_cli_invalid_title_denies_before_intent_or_operator(monkeypatch,tmp_path,case):
    async def run():
        slug='the-student' if case=='unsupported-admitted-title' else opened.SLUG
        returned=None if case=='unsupported-admitted-title' else profiles.cedar.SLUG
        result,error,calls,executed,markers=await _offline_cli_selection(monkeypatch,tmp_path,slug,returned_slug=returned)
        assert result is None and isinstance(error,(op.OperatorStop,proof.AdmissionStop))
        assert not executed and not markers
        assert calls==([] if case=='unsupported-admitted-title' else [(opened.SLUG,False)])
    asyncio.run(run())
