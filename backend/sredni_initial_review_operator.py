"""One-shot Sredni metadata provision/close/status. Never a financial writer."""
from datetime import datetime,timedelta,timezone
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
try:
    from . import sredni_initial_review_authority as auth
    from . import sredni_initial_review_scope as scope
    from . import sredni_initial_review_profile as profile
except ImportError:
    import sredni_initial_review_authority as auth
    import sredni_initial_review_scope as scope
    import sredni_initial_review_profile as profile

OPERATIONS='sredni_initial_review_operations'
TERMINAL={'ended','expired','exhausted','transferred','revoked'}
class OperatorStop(ValueError):pass
class OutcomeUnknown(OperatorStop):pass
def need(ok,code):
    if not ok:raise OperatorStop(code)
def now():return datetime.now(timezone.utc)
def workflow_id(a):
    # A changed login/identity cannot manufacture another60 under one receipt.
    return 'sredni-initial-'+auth.digest({'owner_receipt_sha256':a.owner_receipt_sha256,'user_id':a.user_id,
        'slug':profile.SLUG,'descriptor_sha256':profile.DESCRIPTOR,'package_version':profile.PACKAGE})
def authority_row(a):
    return {'user_id':a.user_id,'auth_session_id':a.auth_session_id,
            'owner_receipt_sha256':a.owner_receipt_sha256,'identity_binding_sha256':a.identity_binding_sha256}

async def bounded(cursor):
    rows=await cursor.max_time_ms(5000).limit(1001).to_list(1001)
    need(len(rows)<=1000,'OWN_METADATA_BOUND_EXCEEDED_NO_PARTIAL_PASS')
    return rows

async def member(db,a,session=None,*,current_auth=True,no_cap=True):
    need(isinstance(a,auth.AdmittedOperation),'ACTUAL_PRIVATE_ADMISSION_REQUIRED')
    need(a.identity_binding_sha256==auth.identity_binding(a.user_id,a.auth_session_id)
         and scope.authority_allows(authority_row(a)),'SOURCE_ACCEPTED_OWNER_MEMBER_PAIR_REQUIRED')
    user=await db.users.find_one({'id':a.user_id,'role':'user'},
        {'_id':0,'id':1,'status':1,'active_user_session_id':1,'reader_acceptance_budget':1,'reading_fractional_microseconds':1},session=session)
    login=await db.user_sessions.find_one({'id':a.auth_session_id,'user_id':a.user_id},
        {'_id':0,'status':1,'idle_expires_at':1,'absolute_expires_at':1},session=session)
    need(user and login,'GENUINE_OWN_MEMBER_ASSOCIATION_UNAVAILABLE')
    if current_auth:
        need(user.get('status')=='active' and user.get('active_user_session_id')==a.auth_session_id
             and login.get('status')=='active' and scope.utc(login['idle_expires_at'])>now()
             and scope.utc(login['absolute_expires_at'])>now(),'CURRENT_NORMAL_MEMBER_REQUIRED')
    if no_cap:need('reader_acceptance_budget' not in user,'RETAINED_GLOBAL_USER_CAP_MUST_NOT_BE_REMOVED_OR_BYPASSED')
    carry=user.get('reading_fractional_microseconds',0)
    need(type(carry) is int and 0<=carry<1000000,'CURRENT_FRACTIONAL_STATE_UNVERIFIED')
    return user

async def snapshot(db,a,session=None):
    wid=workflow_id(a)
    w=await db[scope.WORKFLOWS].find_one({'_id':wid},session=session)
    # Include malformed/closed historical grants for this owner/title, even if
    # their workflow field disappeared; never silently reseed after data loss.
    grants=await bounded(db[scope.GRANTS].find({'$or':[{'workflow_id':wid},
        {'user_id':a.user_id,'owner_receipt_sha256':a.owner_receipt_sha256}]},session=session))
    return wid,w,grants

def state_hash(w,grants):return auth.digest({'workflow':w,'grants':sorted(grants,key=lambda g:str(g.get('_id','')))})

async def retained_references(db,a,wid,session):
    if await db[OPERATIONS].find_one({'user_id':a.user_id,'owner_receipt_sha256':a.owner_receipt_sha256},
        {'_id':1},session=session) is not None:return True
    for name,field in [(OPERATIONS,'workflow_id'),('reading_pass_sessions','scope.'+scope.WORKFLOW_KEY),
                       ('wallet_ledger','metadata.'+scope.WORKFLOW_KEY),('wallet_transactions',scope.WORKFLOW_KEY)]:
        if await db[name].find_one({field:wid},{'_id':1},session=session) is not None:return True
    # A surviving dedicated grant reference with lost workflow linkage is not
    # evidence of an empty history. Inspect only exact own Sredni records.
    for name,grant_field,workflow_field,content_field in [
        ('reading_pass_sessions','scope.'+scope.SCOPE_KEY,'scope.'+scope.WORKFLOW_KEY,'content_id'),
        ('wallet_ledger','metadata.'+scope.SCOPE_KEY,'metadata.'+scope.WORKFLOW_KEY,'metadata.content_id'),
        ('wallet_transactions',scope.SCOPE_KEY,scope.WORKFLOW_KEY,'content_id')]:
        query={'user_id':a.user_id,content_field:profile.SLUG,grant_field:{'$exists':True},workflow_field:{'$exists':False}}
        if await db[name].find_one(query,{'_id':1},session=session) is not None:return True
    return False

def exact_workflow(w,a):
    scope.validate_workflow(w)
    need(all(w.get(k)==v for k,v in {**authority_row(a),'slug':profile.SLUG,'descriptor_sha256':profile.DESCRIPTOR,
        'package_version':profile.PACKAGE,'country':'IN'}.items()),'RETAINED_WORKFLOW_OWNER_IDENTITY_OR_SCOPE_CHANGED')

async def operation(db,a,book,session):
    auth.current(a);await member(db,a,session)
    profile.rights_for_candidate(book,country='IN',now=now())
    wid,w,grants=await snapshot(db,a,session)
    need(state_hash(w,grants)==a.expected_state_sha256,'EXPECTED_ACTUAL_METADATA_STATE_CHANGED_NO_RETRY')
    need(await db[OPERATIONS].find_one({'_id':a.operation_id},session=session) is None,'RETAINED_OPERATION_USE_STATUS_NOT_REPLAY')
    created=now()
    if a.action=='provision':
        need(w is not None or not grants,'MISSING_COUNTER_WITH_ANY_RETAINED_GRANT_HISTORY_NO_RESET')
        if w is None:
            need(not await retained_references(db,a,wid,session),'MISSING_COUNTER_WITH_ANY_RETAINED_REFERENCE_NO_RESET')
            w={'_id':wid,'schema':scope.WORKFLOW_SCHEMA,**authority_row(a),'slug':profile.SLUG,
                'descriptor_sha256':profile.DESCRIPTOR,'package_version':profile.PACKAGE,'country':'IN',
                'created_at':created,'expires_at':a.grant_expires_at,'maximum_seconds':60,'maximum_microseconds':60000000,
                'maximum_starts':3,'used_microseconds':0,'used_credit_seconds':0,'starts_used':0,'revision':0}
            need(created<a.grant_expires_at<=created+timedelta(seconds=900),'FINITE_ORIGINAL_SREDNI_WORKFLOW_WINDOW_REQUIRED')
            auth.current(a);await db[scope.WORKFLOWS].insert_one(w,session=session)
        else:
            exact_workflow(w,a)
            need(not any(g.get('state')=='OPEN' for g in grants),'PRIOR_OPEN_GRANT_MUST_SETTLE_AND_CLOSE')
            need(created<a.grant_expires_at<=scope.utc(w['expires_at']),'ORIGINAL_WINDOW_NEVER_REPLENISHED')
        need(w['used_microseconds']<60000000 and w['used_credit_seconds']<60 and w['starts_used']<3,
             'NO_POSITIVE_REMAINING_SREDNI_ALLOWANCE')
        auth.current(a)
        changed=await db[scope.WORKFLOWS].update_one({'_id':wid,'revision':w['revision'],
            'used_microseconds':w['used_microseconds'],'used_credit_seconds':w['used_credit_seconds'],'starts_used':w['starts_used']},
            {'$inc':{'revision':1}},session=session)
        need(changed.modified_count==1,'WORKFLOW_PROVISION_CAS_CHANGED_NO_RETRY');w={**w,'revision':w['revision']+1}
        gid='sredni-review-'+auth.digest({'workflow_id':wid,'operation_id':a.operation_id})
        g={'_id':gid,'schema':scope.GRANT_SCHEMA,**authority_row(a),'workflow_id':wid,'slug':profile.SLUG,
           'descriptor_sha256':profile.DESCRIPTOR,'package_version':profile.PACKAGE,'country':'IN',
           'created_at':created,'expires_at':a.grant_expires_at,'state':'OPEN','epoch':0,'operation_id':a.operation_id}
        auth.current(a);await db[scope.GRANTS].insert_one(g,session=session)
    elif a.action=='close':
        need(w is not None,'RETAINED_COUNTER_REQUIRED_NO_RESET');exact_workflow(w,a)
        rows=[g for g in grants if g.get('_id')==a.grant_id]
        need(len(rows)==1 and rows[0].get('state') in {'OPEN','REVOKED'},'EXACT_EXISTING_GRANT_CLOSE_REQUIRED')
        g=rows[0];gid=g['_id']
        need(all(g.get(k)==v for k,v in {**authority_row(a),'workflow_id':wid,'slug':profile.SLUG,
             'descriptor_sha256':profile.DESCRIPTOR,'package_version':profile.PACKAGE,'country':'IN'}.items()),'EXACT_CLOSE_SCOPE_REQUIRED')
        need(scope.utc(g['expires_at'])==a.grant_expires_at,'EXACT_ORIGINAL_CLOSE_WINDOW_REQUIRED')
        leases=await bounded(db.reading_pass_sessions.find({'user_id':a.user_id,'scope.'+scope.SCOPE_KEY:gid},
            {'_id':0,'status':1,'active_lock':1,'billing_active':1,'settlement_at':1},session=session))
        need(all(row.get('status') in TERMINAL and 'active_lock' not in row and row.get('billing_active') is False
                 and isinstance(row.get('settlement_at'),datetime) for row in leases),'NORMAL_LEASE_END_AND_SETTLEMENT_REQUIRED_BEFORE_CLOSE')
        auth.current(a)
        changed=await db[scope.GRANTS].update_one({'_id':gid,'user_id':a.user_id,'state':g['state'],'epoch':g['epoch']},
            {'$set':{'state':'CLOSED','closed_at':created,'close_operation_id':a.operation_id,'counter_archive_sha256':auth.digest(w)},
             '$inc':{'epoch':1}},session=session)
        need(changed.modified_count==1,'CLOSE_RACED_START_OR_USAGE_NO_RETRY')
    else:raise OperatorStop('EXACT_PROVISION_OR_CLOSE_ACTION_REQUIRED')
    auth.current(a)
    receipt={'_id':a.operation_id,'user_id':a.user_id,'action':a.action,'workflow_id':wid,'grant_id':gid,
        'owner_receipt_sha256':a.owner_receipt_sha256,'identity_binding_sha256':a.identity_binding_sha256,
        'authority_sha256':a.authority_sha256,'execution_sha256':a.execution_sha256,'intent_sha256':a.intent_sha256,
        'counter_snapshot_sha256':auth.digest(w),'committed_at':created}
    await db[OPERATIONS].insert_one(receipt,session=session)
    return receipt

async def status_in_snapshot(db,a,session):
    await member(db,a,session,current_auth=False,no_cap=False)
    wid,w,grants=await snapshot(db,a,session)
    if w is not None:exact_workflow(w,a)
    receipt=await db[OPERATIONS].find_one({'_id':a.operation_id,'user_id':a.user_id},session=session)
    if receipt:
        need(all(receipt.get(k)==getattr(a,k) for k in ['action','owner_receipt_sha256','identity_binding_sha256',
             'authority_sha256','execution_sha256','intent_sha256']) and receipt.get('workflow_id')==wid,
             'STATUS_RECEIPT_IDENTITY_OR_INTENT_CONFLICT')
        target=[g for g in grants if g.get('_id')==receipt.get('grant_id')]
        need(w and len(target)==1,'COMMITTED_TARGET_COUNTER_OR_GRANT_UNVERIFIED')
        target_binding={**authority_row(a),'schema':scope.GRANT_SCHEMA,'workflow_id':wid,'slug':profile.SLUG,
            'descriptor_sha256':profile.DESCRIPTOR,'package_version':profile.PACKAGE,'country':'IN'}
        need(all(target[0].get(k)==v for k,v in target_binding.items())
             and target[0].get('state') in {'OPEN','REVOKED','CLOSED'}
             and type(target[0].get('epoch')) is int and target[0]['epoch']>=0
             and scope.utc(w['created_at'])<=scope.utc(target[0].get('created_at'))<scope.utc(target[0].get('expires_at'))
             <=scope.utc(w['expires_at']) and scope.utc(target[0]['expires_at'])==a.grant_expires_at,
             'COMMITTED_TARGET_SCHEMA_SCOPE_OR_WINDOW_UNVERIFIED')
        if a.action=='close':need(target[0].get('state')=='CLOSED' and target[0].get('close_operation_id')==a.operation_id
             and target[0].get('counter_archive_sha256')==receipt.get('counter_snapshot_sha256'),'EXACT_CLOSE_READBACK_REQUIRED')
        else:need(target[0].get('operation_id')==a.operation_id,'EXACT_PROVISION_READBACK_REQUIRED')
    return {'status':'COMMIT_RECEIPT_OBSERVED' if receipt else 'OUTCOME_NOT_PROVEN_STATUS_ONLY_NO_REPLAY',
        'operation_id':a.operation_id,'authority_sha256':a.authority_sha256,'state_sha256':state_hash(w,grants),
        'receipt_sha256':auth.digest(receipt) if receipt else None,'actual_remaining_seconds':None,
        'counter_only_remaining_seconds':min((60000000-w['used_microseconds'])//1000000,60-w['used_credit_seconds']) if w else None,
        'starts_used':w.get('starts_used') if w else None,'replay_permitted':False}

async def status(db,client,a):
    need(client.options.retry_writes is False and db.client is client,'PRIVATE_NO_RETRY_CLIENT_REQUIRED')
    async with await client.start_session() as session:
        session.start_transaction(read_concern=ReadConcern('snapshot'),write_concern=WriteConcern('majority',wtimeout=5000))
        try:return await status_in_snapshot(db,a,session)
        finally:
            try:await session.abort_transaction()
            except Exception:raise OutcomeUnknown('STATUS_ABORT_UNVERIFIED_NO_REPLAY') from None

async def observe_initial(db,client,a,book):
    """Genuine fixed-scope read before expected-state admission; no grant."""
    need(a.action=='observe' and a.expected_state_sha256 is None and client.options.retry_writes is False
         and db.client is client,'EXACT_NO_RETRY_READONLY_OBSERVATION_REQUIRED')
    auth.current(a);profile.rights_for_candidate(book,country='IN',now=now())
    namespaces=await namespace_status(db)
    async with await client.start_session() as session:
        session.start_transaction(read_concern=ReadConcern('snapshot'),write_concern=WriteConcern('majority',wtimeout=5000))
        try:
            await member(db,a,session);wid,w,grants=await snapshot(db,a,session)
            retained=await retained_references(db,a,wid,session)
            auth.current(a)
            return {'schema':'earnalism.sredni_initial_review_actual_initial_state.v1','status':'ACTUAL_READONLY_STATE_OBSERVED_NOT_A_GRANT',
                'operation_id':a.operation_id,'observed_at':now().isoformat(),'authority_sha256':a.authority_sha256,
                'workflow':w,'grants':grants,'retained_references':retained,'namespace_status':namespaces,
                'state_sha256':state_hash(w,grants),'actual_remaining_seconds':None,'replay_permitted':False}
        finally:
            try:await session.abort_transaction()
            except Exception:raise OutcomeUnknown('INITIAL_SNAPSHOT_ABORT_UNVERIFIED') from None

NAMESPACE_INDEXES={scope.WORKFLOWS:('sredni_review_owner_v1',[('user_id',1)]),
    scope.GRANTS:('sredni_review_owner_workflow_v1',[('user_id',1),('workflow_id',1)]),
    OPERATIONS:('sredni_review_owner_v1',[('user_id',1)])}

async def namespace_status(db):
    names=set(await db.list_collection_names(filter={'name':{'$in':list(NAMESPACE_INDEXES)}}));plan=[]
    for name,(index_name,keys) in NAMESPACE_INDEXES.items():
        if name not in names:plan.append({'collection':name,'create_collection':True,'create_index':True});continue
        indexes=await db[name].index_information()
        need(any(list(v.get('key',[]))==[('_id',1)] and v.get('unique',True) for v in indexes.values()),'METADATA_ID_INDEX_CONFLICT')
        need(not any('expireAfterSeconds' in v for v in indexes.values()),'METADATA_HISTORY_TTL_FORBIDDEN_NO_REPAIR')
        if index_name in indexes:
            index=indexes[index_name]
            need(list(index.get('key',[]))==keys and not index.get('unique',False) and not index.get('sparse',False)
                 and not index.get('partialFilterExpression'),'EXACT_METADATA_INDEX_REQUIRED_NO_REPAIR')
            missing=False
        else:
            need(not any(list(v.get('key',[]))==keys for v in indexes.values()),'METADATA_INDEX_ALIAS_CONFLICT_NO_REPAIR');missing=True
        plan.append({'collection':name,'create_collection':False,'create_index':missing})
    return {'schema':'earnalism.sredni_initial_review_namespace_status.v1','qualified':not any(p['create_collection'] or p['create_index'] for p in plan),
            'plan':plan,'replay_permitted':False}

async def prepare_namespace_one_shot(db,client,a,book):
    need(a.action=='prepare-namespace' and client.options.retry_writes is False and db.client is client,'EXACT_NO_RETRY_NAMESPACE_ACTION_REQUIRED')
    auth.current(a);profile.rights_for_candidate(book,country='IN',now=now())
    async with await client.start_session() as session:
        session.start_transaction(read_concern=ReadConcern('snapshot'),write_concern=WriteConcern('majority',wtimeout=5000))
        try:await member(db,a,session)
        finally:
            try:await session.abort_transaction()
            except Exception:raise OutcomeUnknown('NAMESPACE_ADMISSION_ABORT_UNKNOWN_NO_REPLAY') from None
    current=await namespace_status(db)
    for row in current['plan']:
        name=row['collection'];index_name,keys=NAMESPACE_INDEXES[name]
        try:
            if row['create_collection']:auth.current(a);await db.create_collection(name)
            if row['create_index']:auth.current(a);await db[name].create_index(keys,name=index_name,unique=False)
        except Exception:raise OutcomeUnknown('NAMESPACE_PARTIAL_OUTCOME_STATUS_ONLY_NO_RETRY') from None
    result=await namespace_status(db);need(result['qualified'],'NAMESPACE_READBACK_UNVERIFIED_STATUS_ONLY')
    return {**result,'operation_id':a.operation_id,'actual_remaining_seconds':None}

async def execute_one_shot(db,client,a,book):
    need(client.options.retry_writes is False and db.client is client,'PRIVATE_NO_RETRY_CLIENT_REQUIRED')
    need((await namespace_status(db))['qualified'],'METADATA_NAMESPACE_NOT_PREPARED')
    auth.current(a)
    async with await client.start_session() as session:
        session.start_transaction(read_concern=ReadConcern('snapshot'),write_concern=WriteConcern('majority',wtimeout=5000),max_commit_time_ms=5000)
        try:await operation(db,a,book,session);auth.current(a)
        except Exception:
            try:await session.abort_transaction()
            except Exception:raise OutcomeUnknown('ABORT_OUTCOME_UNKNOWN_STATUS_ONLY') from None
            raise
        try:await session.commit_transaction()
        except Exception:raise OutcomeUnknown('COMMIT_OUTCOME_UNKNOWN_STATUS_ONLY_NO_REPLAY') from None
    try:result=await status(db,client,a)
    except Exception:raise OutcomeUnknown('POSTCOMMIT_READBACK_UNKNOWN_STATUS_ONLY') from None
    need(result['status']=='COMMIT_RECEIPT_OBSERVED','POSTCOMMIT_NOT_PROVEN_NO_REPLAY')
    return result
