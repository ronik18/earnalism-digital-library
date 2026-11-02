"""Exact Selfish scoped metadata operations; no financial/account mutation.

Authority comes from externally hash-pinned actual owner/identity/execution/source
receipts plus current member and complete original server history in the SAME
snapshot transaction. There is no permissive callback or positive allowance default.
Unknown commit/abort/readback is status-only, never an instruction to replay.
"""
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
import hashlib,json,re
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
try:
    from . import native_audiobook_replacement as native
    from . import native_audio_review_scope as scoped
    from . import native_audio_review_authority as authority
    from . import native_audiobook_profiles as profiles
except ImportError:
    import native_audiobook_replacement as native
    import native_audio_review_scope as scoped
    import native_audio_review_authority as authority
    import native_audiobook_profiles as profiles

OPERATIONS='native_audio_review_operations'
class OperatorStop(ValueError):pass
class OutcomeUnknown(OperatorStop):pass

def need(value,code):
    if not value:raise OperatorStop(code)
def normalized(value):
    if isinstance(value,datetime):return {'utc':scoped.utc(value).isoformat()}
    if isinstance(value,dict):return {k:normalized(v) for k,v in value.items()}
    if isinstance(value,list):return [normalized(v) for v in value]
    return value

def digest(value):return hashlib.sha256(json.dumps(normalized(value),sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

@dataclass(frozen=True)
class AdmittedOperation:
    """Produced by a real private verifier, never constructed from an HTTP body.

    Verifier obligations are in the proposal design: independent normal-member
    binding; original120 approval; complete immutable settled legacy lineage;
    actual/proven conservative CREDIT and TIME upper bounds; current source,
    deployment and prospective book scope; fresh durable at-most-once intent.
    """
    operation_id:str
    action:str
    user_id:str
    auth_session_id:str
    owner_scope_sha256:str
    identity_evidence_sha256:str
    lineage_evidence_sha256:str
    execution_authority_sha256:str
    private_intent_sha256:str
    legacy_session_ids:tuple
    legacy_fingerprint_sha256:str
    original_started_at:datetime
    authority_sha256:str
    expires_at:datetime
    expected_state_sha256:str
    slug:str=native.SLUG
    descriptor_sha256:str=native.DESCRIPTOR
    package_version:str=scoped.PACKAGE
    continuation_sha256:str=''
    grant_id:str=''  # Required only to close an already exact-scope grant.

def admit_authority(path,expected_sha256,*,now,allow_expired=False):
    b,r=authority.parse_authority(path,expected_sha256,now=now,allow_expired=allow_expired)
    return AdmittedOperation(operation_id=b['operation_id'],action=b['action'],user_id=b['user_id'],
        auth_session_id=b['auth_session_id'],owner_scope_sha256=b['owner']['sha256'],
        identity_evidence_sha256=b['identity']['sha256'],lineage_evidence_sha256=b['legacy']['sha256'],
        execution_authority_sha256=b['execution']['sha256'],private_intent_sha256=b['intent']['sha256'],
        legacy_session_ids=tuple(r['legacy']['original_session_ids']),legacy_fingerprint_sha256=r['legacy']['projection_sha256'],
        original_started_at=authority.utc(r['legacy']['original_started_at']),authority_sha256=expected_sha256,
        expires_at=authority.utc(b['expires_at']),expected_state_sha256=b['expected_state_sha256'],grant_id=b.get('grant_id',''),
        slug=b['slug'],descriptor_sha256=b['descriptor_sha256'],package_version=b['package_version'],
        continuation_sha256=(b.get('continuation') or {}).get('sha256',''))

def operation_profile(a):
    profile=profiles.profile_for_slug(a.slug)
    need(profile is not None and a.descriptor_sha256==profile.DESCRIPTOR
         and a.package_version==profiles.actual_package(profile),
         'EXACT_ADMITTED_PROFILE_REQUIRED')
    if a.slug=='the-open-window':
        need(a.owner_scope_sha256==authority.ORIGINAL_OWNER_RECEIPT_SHA256
             and a.continuation_sha256==authority.BOTH_TITLES_RECEIPT_SHA256,
             'OPEN_SAME_ORIGINAL120_CONTINUATION_REQUIRED')
    return profile

def require_live_authority(a):
    need(datetime.now(timezone.utc)<scoped.utc(a.expires_at),'OPERATION_AUTHORITY_EXPIRED_BEFORE_MUTATION')

async def bounded(cursor):
    rows=await cursor.max_time_ms(5000).limit(1001).to_list(1001)
    need(len(rows)<=1000,'OWN_METADATA_OR_LEGACY_HISTORY_TOO_LARGE')
    return rows

async def member(db,a,session=None,*,require_no_user_cap=True,require_current_auth=True):
    need(isinstance(a,AdmittedOperation) and a.action in {'provision','close','prepare-namespace'},'PRIVATE_VERIFIED_OPERATION_REQUIRED')
    need(all(isinstance(getattr(a,k),str) and native.SHA.fullmatch(getattr(a,k)) for k in
        ('owner_scope_sha256','identity_evidence_sha256','lineage_evidence_sha256','execution_authority_sha256','private_intent_sha256','legacy_fingerprint_sha256','expected_state_sha256','authority_sha256')),'ADMISSION_EVIDENCE_MISSING')
    need(isinstance(a.user_id,str) and a.user_id and isinstance(a.auth_session_id,str) and a.auth_session_id
        and re.fullmatch(r'[A-Za-z0-9_-]{16,128}',a.operation_id),'PRIVATE_MEMBER_OR_OPERATION_MISSING')
    now=datetime.now(timezone.utc)
    user=await db.users.find_one({'id':a.user_id,'role':'user'},
        {'_id':0,'id':1,'role':1,'status':1,'reader_acceptance_budget':1,'reading_fractional_microseconds':1,'active_user_session_id':1},session=session)
    auth=await db.user_sessions.find_one({'id':a.auth_session_id,'user_id':a.user_id},
        {'_id':0,'status':1,'idle_expires_at':1,'absolute_expires_at':1},session=session)
    need(user and auth,'INTENDED_NORMAL_MEMBER_NOT_VERIFIED')
    if require_current_auth:
        need(user.get('status')=='active' and user.get('active_user_session_id')==a.auth_session_id
            and auth.get('status')=='active' and scoped.utc(auth['idle_expires_at'])>now
            and scoped.utc(auth['absolute_expires_at'])>now,'INTENDED_NORMAL_MEMBER_NOT_VERIFIED')
    if require_no_user_cap:need('reader_acceptance_budget' not in user,'CONFLICTING_RETAINED_USER_CAP_DO_NOT_RESET_OR_BYPASS')
    carry=user.get('reading_fractional_microseconds',0)
    need(type(carry) is int and 0<=carry<1000000,'GLOBAL_FRACTIONAL_STATE_UNVERIFIED')
    return user

async def settled_legacy(db,a,session):
    # ALL own unscoped starts since original approval, not only known debit IDs.
    # A new/unknown zero-debit start therefore holds rather than disappearing.
    fields={'_id':0,'id':1,'user_id':1,'content_type':1,'content_id':1,'status':1,'billing_active':1,
        'active_lock':1,'settlement_at':1,'last_billed_at':1,'lease_expires_at':1,'seconds_consumed':1,
        'lease_version':1,'lease_issued_at':1,'created_at':1,'last_sequence':1}
    rows=await bounded(db.reading_pass_sessions.find({'user_id':a.user_id,'content_type':'audio',
        'content_id':{'$in':[native.SLUG,'the-open-window']},'created_at':{'$gte':a.original_started_at},
        'scope.'+scoped.SCOPE_KEY:{'$exists':False}},fields,session=session))
    ids=list(a.legacy_session_ids)
    hb=await bounded(db.reading_pass_heartbeats.find({'user_id':a.user_id,'session_id':{'$in':ids}},
        {'_id':0,'id':1,'user_id':1,'session_id':1,'idempotency_key':1,'sequence':1,'lease_version':1,
         'active':1,'playback_state':1,'response':1,'created_at':1},session=session))
    ledger=await bounded(db.wallet_ledger.find({'user_id':a.user_id,'session_id':{'$in':ids},'event_type':'TIME_DEBIT'},
        {'_id':0,'id':1,'user_id':1,'session_id':1,'event_type':1,'debit':1,'credit':1,'signed_seconds':1,
         'idempotency_key':1,'source_transaction_id':1},session=session))
    transactions=await bounded(db.wallet_transactions.find({'user_id':a.user_id,'session_id':{'$in':ids},'type':'consume'},
        {'_id':0,'id':1,'user_id':1,'session_id':1,'type':1,'seconds':1,'actor':1},session=session))
    proof=authority.reconcile_legacy(user_id=a.user_id,ids=ids,original_started_at=a.original_started_at,
        observed_at=datetime.now(timezone.utc),sessions=rows,heartbeats=hb,ledger=ledger,transactions=transactions)
    need(proof['projection_sha256']==a.legacy_fingerprint_sha256,'ACTUAL_SETTLED_LEGACY_PROJECTION_CHANGED')
    return proof

async def snapshot(db,a,session=None,*,require_current_auth=True):
    await member(db,a,session,require_no_user_cap=False,require_current_auth=require_current_auth)
    workflow_id='original120-'+digest({'member':a.user_id,'original_owner_scope':a.owner_scope_sha256})
    workflow=await db[scoped.WORKFLOWS].find_one({'_id':workflow_id,'user_id':a.user_id},session=session)
    grants=await bounded(db[scoped.GRANTS].find({'user_id':a.user_id,'workflow_id':workflow_id},session=session))
    need(len(grants)<=1000,'REVIEW_HISTORY_TOO_LARGE')
    return workflow_id,workflow,grants

async def status_in_snapshot(db,a,session):
    profile=operation_profile(a)
    user=await member(db,a,session,require_no_user_cap=False,require_current_auth=False)
    workflow_id,workflow,grants=await snapshot(db,a,session,require_current_auth=False)
    if workflow is not None:
        scoped.validate_workflow(workflow)
        need(workflow.get('owner_scope_sha256')==a.owner_scope_sha256
            and workflow.get('legacy_lineage_sha256')==a.lineage_evidence_sha256,
            'STATUS_WORKFLOW_OWNER_OR_LINEAGE_DIFFERS_FROM_AUTHORITY')
    receipt=await db[OPERATIONS].find_one({'_id':a.operation_id,'user_id':a.user_id},session=session)
    if receipt:
        need(all(receipt.get(k)==getattr(a,k) for k in ('action','owner_scope_sha256',
            'execution_authority_sha256','private_intent_sha256','authority_sha256'))
            and receipt.get('workflow_id')==workflow_id,'OPERATION_IDENTITY_OR_INTENT_CONFLICT')
        target=[g for g in grants if g['_id']==receipt.get('grant_id')]
        need(workflow and len(target)==1 and target[0].get('user_id')==a.user_id
            and all(target[0].get(k)==v for k,v in {'schema':scoped.GRANT_SCHEMA,
                'workflow_id':workflow_id,'slug':profile.SLUG,'descriptor_sha256':profile.DESCRIPTOR,
                'package_version':a.package_version,'country':'IN','owner_scope_sha256':a.owner_scope_sha256,
                'legacy_lineage_sha256':workflow['legacy_lineage_sha256']}.items())
            and target[0].get('state') in {'OPEN','CLOSED'},'COMMITTED_COUNTER_OR_GRANT_MISSING')
        if a.slug=='the-open-window':
            need(target[0].get('continuation_sha256')==a.continuation_sha256,'OPEN_CONTINUATION_READBACK_CHANGED')
        if a.action=='close':
            need(target[0].get('state')=='CLOSED' and target[0].get('close_operation_id')==a.operation_id
                and target[0].get('counter_archive_sha256')==receipt.get('counter_snapshot_sha256'), 'CLOSE_READBACK_MISMATCH')
        else:need(target[0].get('operation_id')==a.operation_id,'PROVISION_READBACK_MISMATCH')
    return {'status':'CONFLICTING_RETAINED_USER_CAP' if 'reader_acceptance_budget' in user else
            ('COMMIT_RECEIPT_OBSERVED' if receipt else 'OUTCOME_NOT_PROVEN_NO_MUTATION_RETRY'),
        'operation_id':a.operation_id,'authority_sha256':a.authority_sha256,
        'workflow_state_sha256':digest({'workflow':workflow,'grants':sorted(grants,key=lambda g:g['_id'])}),
        'receipt_sha256':digest(receipt) if receipt else None,
        'used_microseconds':workflow.get('used_microseconds') if workflow else None,
        'used_credit_seconds':workflow.get('used_credit_seconds') if workflow else None,
        'actual_remaining_seconds':min((120000000-workflow['used_microseconds'])//1000000,
            120-workflow['used_credit_seconds']) if workflow and receipt and target[0].get('state')=='OPEN'
            and scoped.utc(target[0]['expires_at'])>datetime.now(timezone.utc)
            and 'reader_acceptance_budget' not in user else None,
        'replay_permitted':False}

async def status(db,client,a):
    need(client.options.retry_writes is False and db.client is client,'PRIVATE_NO_RETRY_CLIENT_REQUIRED')
    async with await client.start_session() as session:
        session.start_transaction(read_concern=ReadConcern('snapshot'),write_concern=WriteConcern('majority',wtimeout=5000))
        try:result=await status_in_snapshot(db,a,session)
        finally:
            try:await session.abort_transaction()  # Read-only, no commit/retry.
            except Exception:raise OutcomeUnknown('STATUS_SNAPSHOT_OUTCOME_UNVERIFIED_NO_REPLAY') from None
    return result

async def has_retained_workflow_references(db,a,workflow_id,session):
    # Exact owner/workflow lookups only. Historical rows, even CLOSED or malformed,
    # prohibit a fresh counter if the workflow document disappeared.
    for name,field in ((OPERATIONS,'workflow_id'),('reading_pass_sessions','scope.native_audio_review_workflow_id'),
                       ('wallet_ledger','metadata.native_audio_review_workflow_id'),
                       ('wallet_transactions','native_audio_review_workflow_id')):
        row=await db[name].find_one({'user_id':a.user_id,field:workflow_id},{'_id':1},session=session)
        if row is not None:return True
    return False

async def operation(db,a,book,session):
    profile=operation_profile(a)
    await member(db,a,session)
    if a.action=='provision':
        package,_=profile.rights_for_review_phase(book,country='IN',now=datetime.now(timezone.utc))
        need(package['package_version']==a.package_version,'ACTUAL_NATIVE_PACKAGE_REQUIRED')
    workflow_id,w,grants=await snapshot(db,a,session)
    need(digest({'workflow':w,'grants':sorted(grants,key=lambda g:g['_id'])})==a.expected_state_sha256,'EXPECTED_SCOPED_STATE_CHANGED_NO_RETRY')
    existing=await db[OPERATIONS].find_one({'_id':a.operation_id},session=session)
    need(existing is None,'OPERATION_ALREADY_RETAINED_USE_STATUS_NOT_REPLAY')
    now=datetime.now(timezone.utc)
    if a.action=='provision':
        need(w is not None or not grants,'MISSING_WORKFLOW_WITH_RETAINED_GRANT_HISTORY_NO_RESET')
        need(a.slug!='the-open-window' or w is not None,'OPEN_MUST_REUSE_RETAINED_ORIGINAL120_WORKFLOW_NO_INITIALIZATION')
        if w is None:
            need(not await has_retained_workflow_references(db,a,workflow_id,session),
                'MISSING_WORKFLOW_WITH_ANY_RETAINED_REFERENCE_NO_RESET')
        proof=await settled_legacy(db,a,session)
        need(not any(g.get('state')=='OPEN' for g in grants),'PRIOR_GRANT_MUST_BE_SETTLED_AND_CLOSED')
        if w is None:
            w={'_id':workflow_id,'schema':scoped.WORKFLOW_SCHEMA,'user_id':a.user_id,'original_ceiling_seconds':120,
                'owner_scope_sha256':a.owner_scope_sha256,'legacy_lineage_sha256':a.lineage_evidence_sha256,
                'lineage_status':proof['lineage_status'],'reserved_legacy_microseconds':proof['legacy_time_bound_microseconds'],
                'reserved_legacy_debit_seconds':proof['legacy_credit_bound_seconds'],'used_microseconds':proof['legacy_time_bound_microseconds'],
                'used_credit_seconds':proof['legacy_credit_bound_seconds'],'native_wallet_debit_seconds':0,
                'native_billable_microseconds':0,'revision':0}
            require_live_authority(a)
            await db[scoped.WORKFLOWS].insert_one(w,session=session)
        else:
            scoped.validate_workflow(w)
            need(w.get('schema')==scoped.WORKFLOW_SCHEMA and w.get('owner_scope_sha256')==a.owner_scope_sha256
                and w.get('legacy_lineage_sha256')==a.lineage_evidence_sha256
                and w.get('reserved_legacy_microseconds')==proof['legacy_time_bound_microseconds']
                and w.get('reserved_legacy_debit_seconds')==proof['legacy_credit_bound_seconds'],'RETAINED_ORIGINAL_COUNTER_NEVER_RESET')
        require_live_authority(a)
        result=await db[scoped.WORKFLOWS].update_one({'_id':workflow_id,'revision':w['revision'],
            'used_microseconds':w['used_microseconds'],'used_credit_seconds':w['used_credit_seconds']},{'$inc':{'revision':1}},session=session)
        need(result.modified_count==1,'WORKFLOW_INSTALL_CAS_CHANGED')
        w=dict(w,revision=w['revision']+1)
        need(now<scoped.utc(a.expires_at)<=now+timedelta(minutes=15)
            and max((w['used_microseconds']+999999)//1000000,w['used_credit_seconds'])<120,'NO_POSITIVE_BOUNDED_SCOPE')
        grant_id=('selfish-' if a.slug==native.SLUG else 'open-window-')+digest({'workflow':workflow_id,'authorization_operation':a.operation_id})
        grant={'_id':grant_id,'schema':scoped.GRANT_SCHEMA,'user_id':a.user_id,'workflow_id':workflow_id,
            'slug':profile.SLUG,'descriptor_sha256':profile.DESCRIPTOR,'package_version':a.package_version,'country':'IN',
            'owner_scope_sha256':a.owner_scope_sha256,'legacy_lineage_sha256':a.lineage_evidence_sha256,
            'state':'OPEN','epoch':0,'created_at':now,'expires_at':a.expires_at,'operation_id':a.operation_id}
        if a.slug=='the-open-window':grant['continuation_sha256']=a.continuation_sha256
        require_live_authority(a)
        await db[scoped.GRANTS].insert_one(grant,session=session)
    elif a.action=='close':
        scoped.validate_workflow(w)
        need(w and w.get('schema')==scoped.WORKFLOW_SCHEMA and w.get('owner_scope_sha256')==a.owner_scope_sha256
            and w.get('legacy_lineage_sha256')==a.lineage_evidence_sha256,'COUNTER_HISTORY_REQUIRED_NO_RESET')
        targets=[g for g in grants if g['_id']==a.grant_id]
        need(len(targets)==1 and targets[0].get('state')=='OPEN','EXACT_OPEN_GRANT_REQUIRED')
        grant=targets[0];grant_id=grant['_id']
        need(grant.get('schema')==scoped.GRANT_SCHEMA and grant.get('user_id')==a.user_id
            and grant.get('slug')==profile.SLUG and grant.get('descriptor_sha256')==profile.DESCRIPTOR
            and grant.get('package_version')==a.package_version and grant.get('country')=='IN','EXACT_GRANT_CLOSE_SCOPE_REQUIRED')
        if a.slug=='the-open-window':
            need(grant.get('continuation_sha256')==a.continuation_sha256,'OPEN_EXACT_CONTINUATION_REQUIRED_FOR_CLOSE')
        rows=await db.reading_pass_sessions.find({'user_id':a.user_id,'scope.native_audio_review_grant_id':grant_id},
            {'_id':0,'status':1,'active_lock':1,'billing_active':1,'settlement_at':1},session=session).limit(1001).to_list(1001)
        need(len(rows)<=1000 and all(r.get('status') in scoped.TERMINAL and 'active_lock' not in r
            and r.get('billing_active') is False and isinstance(r.get('settlement_at'),datetime) for r in rows),'NATIVE_LEASE_NOT_SETTLED_USE_NORMAL_END')
        require_live_authority(a)
        result=await db[scoped.GRANTS].update_one({'_id':grant_id,'user_id':a.user_id,'state':'OPEN','epoch':grant['epoch']},
            {'$set':{'state':'CLOSED','closed_at':now,'close_operation_id':a.operation_id,'counter_archive_sha256':digest(w)},'$inc':{'epoch':1}},session=session)
        need(result.modified_count==1,'GRANT_CLOSE_RACED_NATIVE_START_NO_RETRY')
    else:raise OperatorStop('UNSUPPORTED_ACTION')
    require_live_authority(a)
    await db[OPERATIONS].insert_one({'_id':a.operation_id,'user_id':a.user_id,'action':a.action,'grant_id':grant_id,
        'workflow_id':workflow_id,'owner_scope_sha256':a.owner_scope_sha256,'execution_authority_sha256':a.execution_authority_sha256,
        'private_intent_sha256':a.private_intent_sha256,'authority_sha256':a.authority_sha256,'counter_snapshot_sha256':digest(w),'committed_at':now},session=session)
    return {'operation_id':a.operation_id,'action':a.action,'source_of_financial_settlement':'NORMAL_READING_PASS_SERVICE_ONLY'}

NAMESPACE_INDEXES={scoped.WORKFLOWS:('native_review_owner_v1',[('user_id',1)]),
    scoped.GRANTS:('native_review_owner_workflow_v1',[('user_id',1),('workflow_id',1)]),
    OPERATIONS:('native_review_owner_v1',[('user_id',1)])}

async def namespace_status(db):
    names=set(await db.list_collection_names(filter={'name':{'$in':list(NAMESPACE_INDEXES)}}))
    plan=[]
    for name,(index_name,keys) in NAMESPACE_INDEXES.items():
        if name not in names:
            plan.append({'collection':name,'create_collection':True,'create_index':True})
            continue
        indexes=await db[name].index_information()
        need(any(list(v.get('key',[]))==[('_id',1)] and v.get('unique',True) for v in indexes.values()), 'SCOPED_METADATA_ID_INDEX_CONFLICT')
        need(not any('expireAfterSeconds' in v for v in indexes.values()),'SCOPED_HISTORY_TTL_FORBIDDEN_NO_REPAIR')
        if index_name in indexes:
            idx=indexes[index_name]
            need(list(idx.get('key',[]))==keys and not idx.get('unique',False) and not idx.get('sparse',False)
                and not idx.get('partialFilterExpression'), 'SCOPED_METADATA_INDEX_CONFLICT_NO_REPAIR')
            missing=False
        else:
            # Do not silently reinterpret/replace an existing differently named
            # index or weaken an existing uniqueness/partial constraint.
            need(not any(list(v.get('key',[]))==keys for v in indexes.values()), 'SCOPED_METADATA_INDEX_IDENTITY_CONFLICT')
            missing=True
        plan.append({'collection':name,'create_collection':False,'create_index':missing})
    return {'schema':'earnalism.native_audio_review_namespace_status.v1',
        'qualified':not any(p['create_collection'] or p['create_index'] for p in plan),'plan':plan,'replay_permitted':False}

async def validate_namespace(db):
    result=await namespace_status(db)
    need(result['qualified'],'SCOPED_METADATA_NAMESPACES_OR_INDEXES_MISSING_EXPLICIT_PREPARATION_REQUIRED')

async def prepare_namespace_one_shot(*,db,client,admitted,book):
    a=admitted
    profile=operation_profile(a)
    need(admitted.action=='prepare-namespace' and client.options.retry_writes is False and db.client is client,
        'EXACT_NAMESPACE_ACTION_AND_NO_RETRY_CLIENT_REQUIRED')
    need(datetime.now(timezone.utc)<admitted.expires_at,'NAMESPACE_AUTHORITY_EXPIRED')
    package,_=profile.rights_for_review_phase(book,country='IN',now=datetime.now(timezone.utc))
    need(package['package_version']==a.package_version,'ACTUAL_NATIVE_NAMESPACE_PACKAGE_REQUIRED')
    # Snapshot/majority admission only; no user/session/financial mutation.
    async with await client.start_session() as s:
        s.start_transaction(read_concern=ReadConcern('snapshot'),write_concern=WriteConcern('majority',wtimeout=5000))
        try:
            await member(db,admitted,s)
            await settled_legacy(db,admitted,s)
        finally:
            try:await s.abort_transaction()
            except Exception:raise OutcomeUnknown('NAMESPACE_ADMISSION_READ_OUTCOME_UNVERIFIED_NO_REPLAY') from None
    current=await namespace_status(db)  # Full conflict preflight before any DDL.
    for row in current['plan']:
        name=row['collection'];index_name,keys=NAMESPACE_INDEXES[name]
        try:
            if row['create_collection']:
                require_live_authority(admitted)
                await db.create_collection(name)
            if row['create_index']:
                require_live_authority(admitted)
                await db[name].create_index(keys,name=index_name,unique=False)
        except Exception:raise OutcomeUnknown('NAMESPACE_PARTIAL_OUTCOME_UNVERIFIED_STATUS_ONLY_NO_REPLAY') from None
    await validate_namespace(db)
    return {'status':'SCOPED_NAMESPACES_OBSERVED_QUALIFIED_NO_GRANT_CREATED',
        'authority_sha256':admitted.authority_sha256,'operation_id':admitted.operation_id,
        'actual_remaining_seconds':None,'replay_permitted':False}

async def execute_one_shot(*,db,client,admitted,book):
    need(client.options.retry_writes is False and db.client is client,'PRIVATE_NO_RETRY_CLIENT_REQUIRED')
    await validate_namespace(db)
    need(datetime.now(timezone.utc)<admitted.expires_at,'OPERATION_AUTHORITY_EXPIRED')
    async with await client.start_session() as mongo_session:
        mongo_session.start_transaction(read_concern=ReadConcern('snapshot'),
            write_concern=WriteConcern('majority',wtimeout=5000),max_commit_time_ms=5000)
        try:await operation(db,admitted,book,mongo_session)
        except Exception:
            try:await mongo_session.abort_transaction()
            except Exception:raise OutcomeUnknown('ABORT_OUTCOME_UNVERIFIED_USE_STATUS_NO_RETRY') from None
            raise
        try:
            require_live_authority(admitted)
        except Exception:
            try:await mongo_session.abort_transaction()
            except Exception:raise OutcomeUnknown('EXPIRY_ABORT_OUTCOME_UNVERIFIED_STATUS_ONLY_NO_RETRY') from None
            raise
        try:await mongo_session.commit_transaction()  # Exactly once, no callback retry.
        except Exception:raise OutcomeUnknown('COMMIT_OUTCOME_UNVERIFIED_USE_STATUS_NO_RETRY') from None
    try:result=await status(db,client,admitted)
    except Exception:raise OutcomeUnknown('POSTCOMMIT_READBACK_UNVERIFIED_STATUS_ONLY_NO_RETRY') from None
    need(result['status']=='COMMIT_RECEIPT_OBSERVED','POSTCOMMIT_NOT_PROVEN_STATUS_ONLY_NO_RETRY')
    return result
