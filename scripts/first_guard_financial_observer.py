"""Private source-bound controller financial observer proposal; never executed.

Only a live helper-issued, already-consumed seventh context can enter. No budget
Boolean, CLI/env flag, authority factory, standalone collect or per-approval claim.
Native validators, historical records and all consumed counts remain unchanged.
"""
from __future__ import annotations
import asyncio
import hashlib
import inspect
import json
import math
import os
import re
import stat
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

HISTORICAL_KERNEL_SHA256 = '019ffd70b787d664fb0be01b0eaf144a3088bd7d6637919222e0624e91bfaa5a'
SHA = re.compile(r'^[0-9a-f]{64}$')
IDENTIFIER = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
SEAL = object()
OWNED_CLEANUPS = set()
OWNED_ATTEMPTS = {}

class Hold(Exception):
    """Code-only exception: never interpolate provider/DB/identity values."""
    def __init__(self, code):
        if not re.fullmatch(r'[A-Z0-9_]{1,100}', code): code = 'UNSAFE_ERROR_CODE'
        self.code = code
        super().__init__(code)

def need(ok, code):
    if not ok: raise Hold(code)


def utc(value):
    need(isinstance(value, datetime), 'TIMESTAMP_TYPE_INVALID')
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

def normal(value):
    if isinstance(value, datetime): return {'utc': utc(value).isoformat()}
    if value is None or type(value) in (bool, int): return value
    if type(value) is float:
        need(math.isfinite(value), 'NONFINITE_VALUE'); return value
    if isinstance(value, str):
        need(len(value.encode()) <= 4096, 'STRING_BOUND_EXCEEDED')
        need(not re.search(r'(?i)mongodb(?:\+srv)?://|https?://|bearer\s|-----BEGIN', value), 'UNEXPECTED_SENSITIVE_VALUE')
        return value
    if type(value) in (list, tuple): return [normal(v) for v in value]
    if type(value) is dict:
        need(all(isinstance(k,str) and len(k)<=128 for k in value), 'UNSUPPORTED_KEY')
        return {k:normal(v) for k,v in value.items()}
    raise Hold('UNSUPPORTED_BSON_OR_SCHEMA_TYPE')

def encode(value):
    return json.dumps(normal(value),sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()

def digest(value): return hashlib.sha256(encode(value)).hexdigest()
def metadata_digest(value):
    # These provider JSON values are hashed, not retained as raw configuration.
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def private_bytes(path, expected):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid()
             and stat.S_IMODE(info.st_mode)==0o600 and info.st_size<=1048576, 'UNSAFE_PINNED_FILE')
        raw=stream.read(1048577)
    need(len(raw)<=1048576 and hashlib.sha256(raw).hexdigest()==expected, 'PINNED_FILE_CHANGED')
    return raw

def identifier(value):
    need(isinstance(value,str) and IDENTIFIER.fullmatch(value) is not None, 'UNSAFE_IDENTIFIER')
    return value

def bounded_ids(values):
    result=sorted({identifier(v) for v in values if v is not None})
    need(len(result)<=1000, 'REFERENCE_SET_OVERFLOW')
    return result

def bind(value, symbols):
    if isinstance(value,str) and value.startswith('$'):
        need(value in {'$U','$W120','$W60','$S','$A','$T'} and value[1:] in symbols, 'UNBOUND_SYMBOL')
        return symbols[value[1:]]
    if type(value) is list: return [bind(v,symbols) for v in value]
    if type(value) is dict:
        if set(value)=={'$bound_datetime'}:
            return datetime.fromisoformat(value['$bound_datetime'])
        return {k:bind(v,symbols) for k,v in value.items()}
    return value

@dataclass(frozen=True)
class RootReadAuthority:
    """Produced ONLY by the separately pinned protected Root resolver."""
    actual_reply_sha256: str
    budget_disposition_sha256: str
    profile_provenance_sha256: str
    plan_sha256: str
    collector_sha256: str
    scope_sha256: str
    issued_at: datetime
    expires_at: datetime
    maximum_attempts: int
    startup_consumed: int
    startup_ceiling: int


class RootReadPorts(Protocol):
    """Unwired trusted I/O boundary. Every method is ONE fixed logical read."""
    async def github_ref(self, branch: str) -> str: ...
    async def railway_graphql(self, query: str) -> dict: ...
    async def describe_service(self, target: dict) -> dict: ...
    async def staged_changes(self, target: dict) -> dict: ...

def pin_adapter(port, expected):
    need(isinstance(expected,str) and SHA.fullmatch(expected), 'ROOT_ADAPTER_UNBOUND')
    source=inspect.getsourcefile(port if inspect.isfunction(port) or inspect.ismethod(port) else type(port))
    need(source is not None and not Path(source).is_symlink(), 'ROOT_ADAPTER_SOURCE_UNAVAILABLE')
    need(hashlib.sha256(Path(source).read_bytes()).hexdigest()==expected, 'ROOT_ADAPTER_CHANGED')


@dataclass
class State:
    bindings: dict
    plan: dict
    symbols: dict
    authority: RootReadAuthority
    seal: object
    deadline: float
    claim_context: object = None
    client_closed: bool = False
    client_close_attempted: bool = False
    factory_database: object = None
    db_deadline: float = 0
    reads: int = 0
    metadata_reads: int = 0
    ref_reads: int = 0
    principal_commands: int = 0
    abort_calls: int = 0
    abort_acknowledged: bool = False
    pending: object = None
    pending_kind: str = ''
    cleanup_task: object = None
    cleanup_error: bool = False
    cleanup_done: bool = False
    bytes_written: int = 0
    base_fd: object = None
    claim_fd: object = None
    db_session: object = None
    transaction_started: bool = False
    collection_done: bool = False
    read_receipts: list = field(default_factory=list)
    database_started_at: object = None
    database_completed_at: object = None
    client_ref: object = None
    rows: dict = field(default_factory=dict)
    metadata: list = field(default_factory=list)
    claim_directory: object = None

    def check(self, database=False):
        need(self.claim_context is not None,'CONTROLLER_PRECLAIM_REQUIRED')
        self.claim_context.assert_valid()
        need(self.seal is SEAL, 'ROOT_ADMISSION_REQUIRED')
        need(datetime.now(timezone.utc)<utc(self.authority.expires_at), 'READ_AUTHORITY_EXPIRED')
        end=min(self.deadline,self.db_deadline) if database else self.deadline
        need(time.monotonic()<end,'CAPTURE_DEADLINE_EXCEEDED')

async def owned_wait(st: State, factory, *, database=False, kind='provider'):
    """Shield original future. A timeout never frees it or starts cleanup over it."""
    st.check(database)
    need(st.pending is None,'OVERLAPPING_IO_FORBIDDEN')
    end=min(st.deadline,st.db_deadline) if database else st.deadline
    remaining=end-time.monotonic();need(remaining>0,'CAPTURE_DEADLINE_EXCEEDED')
    future=asyncio.ensure_future(factory());st.claim_context.track_future(future);st.pending=future;st.pending_kind=kind
    try:
        result=await asyncio.wait_for(asyncio.shield(future),remaining)
        if kind=='session_start': st.db_session=result
        if kind=='client_factory': _adopt_client_bundle(st,result)
        st.check(database)
        return result
    finally:
        # An unresolved future remains owned; caller must not abort/close over it.
        if future.done(): st.pending=None;st.pending_kind=''

def persist(st, name, value):
    need(st.claim_context is not None and st.seal is SEAL,'CONTROLLER_PRECLAIM_REQUIRED')
    need(name in {'SNAPSHOT.private.json','RESULT.json','CLEANUP.json'},'UNEXPECTED_EVIDENCE')
    held=(name=='CLEANUP.json' or (type(value) is dict and
        (value.get('status')=='HOLD_UNKNOWN_NO_RETRY' or value.get('complete') is False)))
    st.claim_context.assert_valid(check_deadline=not held)
    # Controller-owned append only; no mkdir, claim allocation or approval path.
    st.claim_context.append_private(name,normal(value))
    st.bytes_written=st.claim_context.retained_bytes


def retire(st):
    """Close our own created client once, only after original work settles.

    Never release controller claim custody here or retry an uncertain close.
    """
    if st.pending is not None or (st.cleanup_task is not None and not st.cleanup_task.done()): return
    if st.db_session is not None and not st.cleanup_done: return
    if st.client_ref is not None and not st.client_closed:
        if st.client_close_attempted:return  # Never retry an uncertain SDK close.
        try:_close_created_client(st)
        except BaseException:
            st.cleanup_error=True;return  # Context retains uncertain client custody.
    for name in ('claim_fd','base_fd'):
        fd=getattr(st,name)
        if fd is not None: os.close(fd);setattr(st,name,None)
    OWNED_ATTEMPTS.pop(id(st),None)

def owns_client_work(client):
    """Local lifecycle status only. Caller must not close an owned client."""
    return any(st.client_ref is client and (st.pending is not None
        or st.db_session is not None and not st.cleanup_done
        or st.cleanup_task is not None and not st.cleanup_task.done())
        for st in OWNED_ATTEMPTS.values())

def native_query(p):
    t=p['target'];dep=p['source_binding']['deployment_id']
    return ('query { deployment(id:"'+dep+'") { id status projectId serviceId environmentId snapshotId '
        'instances { id status } meta } serviceInstance(environmentId:"'+t['environment']+'",serviceId:"'+t['service']+'") '
        '{ activeDeployments { id status } } deploymentTriggers(projectId:"'+t['project']+'",environmentId:"'+t['environment']+'",serviceId:"'+t['service']+'",first:100) '
        '{ edges { node { id } } pageInfo { hasNextPage } } }')

async def metadata(st,ports,stage):
    st.check();p=st.plan;b=st.bindings;s=p['source_binding'];t=p['target']
    need(st.metadata_reads<=3,'METADATA_READ_CEILING')
    need(stage==('before' if not st.metadata else 'after') and len(st.metadata)<2,'METADATA_ORDER_INVALID')
    st.metadata_reads+=1
    raw=await owned_wait(st,lambda:ports.railway_graphql(native_query(p)))
    need(not raw.get('errors'),'NATIVE_METADATA_ERROR');d=raw['data'];dep=d['deployment']
    need((dep['id'],dep['status'],dep['projectId'],dep['serviceId'],dep['environmentId'],dep['snapshotId'])==
         (s['deployment_id'],'SUCCESS',t['project'],t['service'],t['environment'],b['expected_snapshot_id']),'NATIVE_IDENTITY_DRIFT')
    need(dep['meta']['imageDigest']==s['image'] and metadata_digest(dep['meta']['fileServiceManifest'])==b['expected_file_service_manifest_sha256'],'NATIVE_IMAGE_OR_FILE_CONFIG_DRIFT')
    need(dep['instances']==[{'id':b['expected_instance_id'],'status':'RUNNING'}]
         and d['serviceInstance']['activeDeployments']==[{'id':s['deployment_id'],'status':'SUCCESS'}],'BOOT_OR_ACTIVE_INSTANCE_DRIFT')
    triggers=d['deploymentTriggers'];need(triggers['edges']==[] and triggers['pageInfo']['hasNextPage'] is False,'AUTO_TRIGGER_DRIFT')
    st.metadata_reads+=1
    config=await owned_wait(st,lambda:ports.describe_service(t))
    need(config['service']['id']==t['service'] and config['environment']['id']==t['environment']
         and config['staged'] is None and config['stagedChanges']==[] and config['volumes']==[],'SERVICE_CONFIG_UNQUALIFIED')
    cfg=metadata_digest({'project':t['project'],'service':t['service'],'environment':t['environment'],'config':config['config'],'volumes':[]})
    need(cfg==s['config_sha256'],'CONFIG_DRIFT')
    st.metadata_reads+=1
    staged=await owned_wait(st,lambda:ports.staged_changes(t))
    need(staged['project']['id']==t['project'] and staged['environment']['id']==t['environment']
         and staged['staged'] is None and staged['resources']==[] and staged['sharedVariables']==[],'ENVIRONMENT_STAGED_DRIFT')
    receipt={'stage':stage,'deployment_id':dep['id'],'instance_id':b['expected_instance_id'],
             'image':s['image'],'snapshot_id':dep['snapshotId'],'config_sha256':cfg,'observed_at':datetime.now(timezone.utc)}
    st.metadata.append(receipt)

SCOPE_KEYS=set('native_audio_review_grant_id native_audio_review_workflow_id native_replacement_authorization_id sredni_initial_review_grant_id sredni_initial_review_workflow_id acceptance_test_id manifest_version segmentation_version package_version release_descriptor_sha256 release_country authority_activation_generation entitlement_kind'.split())
BUDGET_KEYS=set('schema user_id content_type content_id test_id status maximum_seconds consumed_seconds expires_at created_at manifest_version segmentation_version maximum_sessions sessions_started acceptance_session_ordinal package_version release_descriptor_sha256 release_country native_replacement_authorization'.split())

def check_rows(st,q,rows):
    need(type(rows) is list and len(rows)<=q['maximum_accepted_rows'],'ROW_BOUND_EXCEEDED')
    uid=st.symbols['U'];ids=set();allowed={k.split('.')[0] for k,v in q['projection'].items() if v}
    for row in rows:
        need(type(row) is dict and set(row)<=allowed,'UNREVIEWED_PROJECTED_SCHEMA')
        key='id' if q['id'] in {'Q01','Q08','Q09','Q10','Q11','Q12'} else '_id'
        value=identifier(row.get(key));need(value not in ids,'DUPLICATE_ROW_ID');ids.add(value)
        need((row.get('id') if q['id']=='Q01' else row.get('user_id'))==uid,'FOREIGN_OR_MISSING_MEMBER')
        family='120' if q['id'] in {'Q02','Q03','Q04'} else '60'
        if q['id'] in {'Q02','Q03','Q04','Q05','Q06','Q07'}:
            owner_key='owner_scope_sha256' if family=='120' else 'owner_receipt_sha256'
            owner=st.plan['actor']['original120_owner_sha256' if family=='120' else 'Sredni_owner_sha256']
            need(row.get(owner_key)==owner,'SCOPED_OWNER_BINDING_CHANGED')
            expected=st.symbols['W'+family]
            need((row.get('_id') if q['id'] in {'Q02','Q05'} else row.get('workflow_id'))==expected,
                 'SCOPED_WORKFLOW_BINDING_CHANGED')
        schemas={'Q02':'earnalism.native_audio_review_workflow.v1','Q03':'earnalism.native_audio_review_grant.v1',
                 'Q05':'earnalism.sredni_initial_review_workflow.v1','Q06':'earnalism.sredni_initial_review_grant.v1'}
        if q['id'] in schemas: need(row.get('schema')==schemas[q['id']],'UNSUPPORTED_NAMESPACE_SCHEMA')
        if q['id'] in {'Q02','Q05'}:
            maximum=120 if family=='120' else 60
            for key,limit in [('used_microseconds',maximum*1000000),('used_credit_seconds',maximum)]:
                need(type(row.get(key)) is int and 0<=row[key]<=limit,'COUNTER_BOUND_OR_TYPE_INVALID')
            need(type(row.get('revision')) is int and row['revision']>=0,'WORKFLOW_REVISION_INVALID')
            if family=='60':
                need(row.get('maximum_seconds')==60 and row.get('maximum_microseconds')==60000000
                     and row.get('maximum_starts')==3 and type(row.get('starts_used')) is int
                     and 0<=row['starts_used']<=3,'SREDNI_ORIGINAL_CEILING_CHANGED')
            else:need(row.get('original_ceiling_seconds')==120,'ORIGINAL120_CEILING_CHANGED')
        if q['id'] in {'Q03','Q06'}:
            states={'OPEN','CLOSED'} if family=='120' else {'OPEN','REVOKED','CLOSED'}
            need(row.get('state') in states and type(row.get('epoch')) is int and row['epoch']>=0,
                 'GRANT_STATE_OR_EPOCH_INVALID')
        if q['id'] in {'Q04','Q07'}:
            need('schema' not in row and row.get('action') in {'provision','close'},'UNSUPPORTED_OPERATION_RECEIPT')
            extra=('execution_authority_sha256','private_intent_sha256') if family=='120' else ('execution_sha256','intent_sha256')
            for key in ('authority_sha256','counter_snapshot_sha256')+extra:
                need(isinstance(row.get(key),str) and SHA.fullmatch(row[key]),'OPERATION_RECEIPT_BINDING_MISSING')
        for container,keys in [('scope',SCOPE_KEYS),('reader_acceptance_budget',BUDGET_KEYS)]:
            if container in row and row[container] is not None:
                need(type(row[container]) is dict and set(row[container])<=keys,'UNSUPPORTED_METADATA_CONTAINER')
                need('native_replacement_authorization' not in row[container], 'CARRIED_REPLACEMENT_OUTSIDE_PROOF_SCOPE')
        normal(row)  # Reject unsupported BSON types/oversized/sensitive values before retention.
        if q['id']=='Q08':
            need(row.get('status') in {'ended','expired','exhausted','transferred','revoked'}
                 and row.get('billing_active') is False and 'active_lock' not in row
                 and isinstance(row.get('settlement_at'),datetime),'LIVE_OR_UNSETTLED_TARGET_LEASE')
        if q['id']=='Q09':need(row.get('status') in {'active','expired','revoked'},'AUTH_STATUS_UNKNOWN')
        if q['id'] in {'Q10','Q11','Q12'}:
            need(row.get('session_id') in st.symbols['S'],'ORPHAN_OR_FOREIGN_SESSION_REFERENCE')
        if q['id']=='Q11':need(row.get('event_type')=='TIME_DEBIT','UNEXPECTED_FINANCIAL_EVENT')
        if q['id']=='Q12':need(row.get('type')=='consume' and row.get('actor')=='reading-pass-v2','UNEXPECTED_FINANCIAL_TRANSACTION')
    if q['id']=='Q01': need(len(rows)==1 and rows[0].get('status')=='active','MEMBER_UNAVAILABLE')

def validate_auth(st):
    rows=st.rows.get('Q09',[]);found={r['id']:r for r in rows}
    need(set(found)==set(st.symbols['A']),'AUTH_REFERENCE_MISSING')
    active=st.rows['Q01'][0].get('active_user_session_id')
    need(active in found,'CURRENT_AUTH_UNAVAILABLE')
    row=found[active];now=datetime.now(timezone.utc)
    need(row.get('status')=='active' and utc(row['idle_expires_at'])>now
         and utc(row['absolute_expires_at'])>now,'CURRENT_AUTH_EXPIRED_OR_REVOKED')

async def finish_database(st,session,started):
    """Cleanup only; can outlive collection deadline, never reads new data."""
    already_cleaned=st.cleanup_done
    session=None if already_cleaned else (session if session is not None else st.db_session)
    pending=st.pending;kind=st.pending_kind
    if pending is not None:
        try:
            result=await asyncio.shield(pending)
            if kind=='session_start': session=result;st.db_session=result
            if kind=='client_factory': _adopt_client_bundle(st,result)
        except BaseException:
            st.cleanup_error=True
        finally:
            if pending.done(): st.pending=None;st.pending_kind=''
    if st.pending is not None:
        return  # Still owned/UNKNOWN; never abort over a live operation.
    try:
        if session is not None:
            if started or getattr(session,'in_transaction',False):
                if st.abort_calls==0:
                    st.abort_calls=1
                    future=asyncio.ensure_future(session.abort_transaction());st.claim_context.track_future(future)
                    st.pending=future;st.pending_kind='abort_cleanup'
                    try:
                        await asyncio.shield(future)
                        st.abort_acknowledged=True
                    except BaseException:
                        st.cleanup_error=True
                        if not future.done(): return
                    finally:
                        if future.done(): st.pending=None;st.pending_kind=''
            future=asyncio.ensure_future(session.end_session());st.claim_context.track_future(future)
            st.pending=future;st.pending_kind='session_end_cleanup'
            await asyncio.shield(future)
            st.pending=None;st.pending_kind=''
        st.cleanup_done=True
    except BaseException:
        st.cleanup_error=True

def own_cleanup(st,session,started):
    task=asyncio.create_task(finish_database(st,session,started));st.claim_context.track_future(task)
    st.cleanup_task=task;OWNED_CLEANUPS.add(task)
    def done(future):
        OWNED_CLEANUPS.discard(future)
        # Consume exceptions without exposing driver/identity details.
        if not future.cancelled():
            try: future.exception()
            except BaseException: pass
        if st.collection_done:
            try:
                persist(st,'CLEANUP.json',{'schema':'earnalism.readonly_cleanup_observation.v1',
                    'cleanup_done':st.cleanup_done,'cleanup_error':st.cleanup_error,
                    'original_future_unresolved':st.pending is not None,
                    'abort_acknowledged':st.abort_acknowledged,'additional_data_reads':0,'normal_release':'HELD'})
            except BaseException: pass  # Original UNKNOWN/claim remains; no retry or overwrite.
            retire(st)
    task.add_done_callback(done)
    return task

def derive(st):
    r=st.rows
    if 'Q08' in r:
        st.symbols['S']=bounded_ids(row['id'] for row in r['Q08'])
        refs=[r['Q01'][0].get('active_user_session_id')]
        refs.extend(row.get('auth_session_id') for k in ('Q03','Q06','Q08') for row in r.get(k,[]))
        st.symbols['A']=bounded_ids(refs)
    if 'Q11' in r: st.symbols['T']=bounded_ids(row.get('source_transaction_id') for row in r['Q11'])

async def database_snapshot(st,client,db):
    """Only explicit reads; caller owns cleanup if original future is unresolved."""
    st.check();need(st.pending is None,'OVERLAPPING_IO_FORBIDDEN')
    # Imports occur only after every disabled/authority/budget/claim guard.
    import motor, pymongo
    from motor.motor_asyncio import AsyncIOMotorClient
    from pymongo.read_concern import ReadConcern
    from pymongo.read_preferences import ReadPreference
    need(motor.version=='3.3.1' and pymongo.version=='4.5.0','DRIVER_VERSION_DRIFT')
    need(isinstance(client,AsyncIOMotorClient) and db.client is client,'EXACT_CLIENT_REQUIRED')
    need(db.codec_options.document_class is dict,'PLAIN_DATABASE_DOCUMENTS_REQUIRED')
    need(client.options.retry_reads is False and client.options.retry_writes is False
         and client.options.pool_options.max_pool_size==1
         and client.options.pool_options.min_pool_size==0,'DIAGNOSTIC_CLIENT_BOUND_REQUIRED')
    for timeout in (client.options.server_selection_timeout,client.options.pool_options.connect_timeout,
                    client.options.pool_options.socket_timeout):
        need(type(timeout) in (int,float) and 0<timeout<=1,'CLIENT_TIMEOUT_BOUND_REQUIRED')
    seeds=client.delegate._topology_settings.seeds
    fingerprint=metadata_digest({'seeds':sorted([[host.lower(),port] for host,port in seeds])})
    need(fingerprint==st.bindings['expected_client_seed_set_sha256'],'CLIENT_CLUSTER_BINDING_CHANGED')
    need(hashlib.sha256(db.name.encode()).hexdigest()==st.bindings['database_name_sha256'],'DATABASE_BINDING_CHANGED')
    st.db_deadline=min(st.deadline,time.monotonic()+10)
    st.database_started_at=datetime.now(timezone.utc)
    st.principal_commands+=1
    principal=await owned_wait(st,lambda:client.admin.command({'connectionStatus':1,'showPrivileges':False}),database=True,kind='principal')
    need(principal.get('ok')==1,'PRINCIPAL_READ_UNQUALIFIED')
    info=principal.get('authInfo',{});users=info.get('authenticatedUsers',[]);roles=info.get('authenticatedUserRoles',[])
    need(len(users)==1 and len(roles)==1,'PRINCIPAL_OR_ROLE_AMBIGUOUS')
    need(hashlib.sha256(users[0]['user'].encode()).hexdigest()==st.bindings['expected_principal_sha256']
         and hashlib.sha256(users[0]['db'].encode()).hexdigest()==st.bindings['expected_auth_database_sha256']
         and roles[0]=={'role':'readWrite','db':db.name},'PRINCIPAL_OR_ROLE_CHANGED')
    session=None;started=False
    try:
        session=await owned_wait(st,lambda:client.start_session(),database=True,kind='session_start')
        session.start_transaction(read_concern=ReadConcern('snapshot'),read_preference=ReadPreference.PRIMARY)
        started=True;st.transaction_started=True
        for q in st.plan['queries']:
            st.check(True);need(st.reads<12,'FIND_COMMAND_CEILING');derive(st)
            milliseconds=int((st.db_deadline-time.monotonic())*1000);need(milliseconds>=1,'DATABASE_DEADLINE_EXCEEDED')
            command={'find':q['collection'],'filter':bind(q['selector_template'],st.symbols),
                     'projection':q['projection'],'sort':q['sort'],'limit':q['wire_row_limit'],
                     'batchSize':q['batch_size'],'maxTimeMS':min(1000,milliseconds)}
            need(set(command)=={'find','filter','projection','sort','limit','batchSize','maxTimeMS'},'UNEXPECTED_COMMAND')
            st.reads+=1
            response=await owned_wait(st,lambda:db.command(command,session=session,read_preference=ReadPreference.PRIMARY),database=True,kind='find')
            need(response.get('ok')==1,'FIND_RESPONSE_UNQUALIFIED')
            cursor=response.get('cursor',{})
            need(cursor.get('ns')==db.name+'.'+q['collection'],'CURSOR_NAMESPACE_CHANGED')
            from bson import BSON
            st.read_receipts.append({'query_id':q['id'],'collection':q['collection'],
                'response_BSON_sha256':hashlib.sha256(BSON.encode(response)).hexdigest(),
                'completed_at':datetime.now(timezone.utc)})
            need(isinstance(cursor.get('id'),int) and not isinstance(cursor['id'],bool)
                 and cursor['id']==0,'CURSOR_NOT_EXHAUSTED_NO_GETMORE')
            rows=cursor.get('firstBatch');check_rows(st,q,rows)
            candidate={**st.rows,q['id']:rows}
            need(st.bytes_written+len(encode(candidate))+32768<=1048576,'RETAINED_BYTE_BOUND_EXCEEDED')
            st.rows[q['id']]=rows
            if q['id']=='Q09': validate_auth(st)
        st.database_completed_at=datetime.now(timezone.utc)
    finally:
        # NEVER overlap abort/end_session with an unresolved original Future.
        if session is not None or st.db_session is not None or st.pending_kind=='session_start':
            task=own_cleanup(st,session if session is not None else st.db_session,started)
            remaining=st.deadline-time.monotonic()
            if remaining>0:
                await asyncio.wait_for(asyncio.shield(task),remaining)
        # On timeout/cancellation the owned cleanup remains strongly referenced.

def legacy_views(st):
    """Exact immutable old projection; never fill absent fields or hide new IDs."""
    b=st.bindings;r=b['historical_reconciliation_reference']
    review=json.loads(private_bytes(Path(r['path']),r['sha256']))
    proof_ref=review['references']['historical_metering_runtime_proof']
    proposal=Path(proof_ref['path']).parent/'ORIGINAL120-LEGACY-SCOPE.PROPOSED.private.json'
    old=json.loads(private_bytes(proposal,review['original_scope_file_sha256']))
    expected=set(old['original_session_ids']);rows=st.rows;start=datetime.fromisoformat(old['original_started_at'])
    selected=[row for row in rows['Q08'] if row.get('content_type')=='audio'
        and row.get('content_id') in {'the-selfish-giant','the-open-window'}
        and isinstance(row.get('created_at'),datetime) and utc(row['created_at'])>=utc(start)
        and 'native_audio_review_grant_id' not in (row.get('scope') or {})]
    ids={r['id'] for r in selected};need(ids==expected,'LEGACY_SESSION_SET_DRIFT')
    def view(row,keys): return {k:row[k] for k in keys if k in row}
    sessions=[view(r,st.plan['historical_legacy_view']['session_fields']) for r in selected]
    heartbeat_keys={'id','user_id','session_id','idempotency_key','sequence','lease_version','active','playback_state','created_at'}
    heartbeats=[]
    for row in rows['Q10']:
        if row.get('session_id') in ids:
            need(type(row.get('response')) is dict,'LEGACY_RESPONSE_SHAPE_INVALID')
            item=view(row,heartbeat_keys)
            item['response']=view(row['response'],st.plan['historical_legacy_view']['heartbeat_response_fields'])
            heartbeats.append(item)
    ledger=[view(row,{'id','user_id','session_id','event_type','debit','credit','signed_seconds','idempotency_key','source_transaction_id'})
            for row in rows['Q11'] if row.get('session_id') in ids]
    transactions=[view(row,{'id','user_id','session_id','type','seconds','actor'})
                  for row in rows['Q12'] if row.get('session_id') in ids]
    projection={'sessions':sorted(sessions,key=lambda r:r['id']),'heartbeats':sorted(heartbeats,key=lambda r:r['id']),
                'ledger':sorted(ledger,key=lambda r:r['id']),'transactions':sorted(transactions,key=lambda r:r['id'])}
    need(digest(projection)==st.plan['historical_legacy_view']['expected_original_projection_sha256'],'LEGACY_PROJECTION_DRIFT')
    return projection

def snapshot_payload(st, *, complete):
    p=st.plan['source_binding']
    return {'schema':'earnalism.raw_readonly_accounting_capture.v1','complete':complete,'rows':st.rows,
            'read_receipts':st.read_receipts,'metadata':st.metadata,
            'source_roles':{'controller':p['controller'],'closed':p['closed'],
                'controller_dependency_files_sha256':p['source_files_sha256'],
                'closed_server_sha256':st.bindings['closed_server_sha256'],
                'runtime_manifest_sha256':p['runtime_manifest_sha256'],'runtime_sha256':p['runtime_sha256'],
                'component_receipt_sha256':p['component_receipt_sha256']},
            'database_time_bracket_UTC':[st.database_started_at,st.database_completed_at],
            'normal_release':'HELD','native_gates_qualified':False}




def specs(context):
    context.assert_valid()
    runtime=context.runtime_contract
    ref=runtime['historical_bindings']
    b=json.loads(private_bytes(Path(ref['path']),ref['sha256']))
    actual=runtime['required_actual_before_any_claim']
    for key in ('separate_execution_owner_authorization_sha256','protected_host_identity_sha256',
                'trusted_existing_controller_resolver_sha256','actual_client_factory_source_sha256',
                'actual_transport_source_sha256','current_profile_provenance_sha256',
                'current_runtime_dependency_closure_sha256','expected_principal_sha256',
                'expected_auth_database_sha256','expected_client_seed_set_sha256',
                'runtime_flag_channel_or_applicability_sha256','current_config_secret_version_context_sha256','canonical_history_preservation_sha256'):
        need(isinstance(actual[key],str) and SHA.fullmatch(actual[key]),'CURRENT_PROVENANCE_UNBOUND')
    need(isinstance(actual['admission_controller_commit_sha'],str)
         and re.fullmatch('[a-f0-9]{40}',actual['admission_controller_commit_sha']),'ADMISSION_CONTROLLER_COMMIT_UNBOUND')
    # Overlay a private in-memory copy only; never rewrite historical BINDINGS.
    for key in ('expected_principal_sha256','expected_auth_database_sha256','expected_client_seed_set_sha256'):
        b[key]=actual[key]
    b['runtime_flag_requirement_decision']=actual['runtime_flag_requirement_decision']
    p=json.loads(private_bytes(Path(b['plan_path']),b['plan_sha256']))
    need(b['runtime_flag_requirement_decision'] is False, 'RUNTIME_FLAG_REQUIREMENT_UNRESOLVED')
    for key in ('expected_principal_sha256','expected_auth_database_sha256','expected_client_seed_set_sha256'):
        need(isinstance(b[key],str) and SHA.fullmatch(b[key]),'CLIENT_OR_PRINCIPAL_PROVENANCE_UNBOUND')
    # Frozen plan's old zero remaining is historical, not a new permit.
    need(len(p['queries'])==12 and p['startup_captures_remaining']==0
         and p['normal_release']=='HELD', 'PLAN_INVARIANTS_CHANGED')
    root=Path(b['controller_root']);export=Path(b['closed_export_root'])
    for rel,sha in p['source_binding']['source_files_sha256'].items():
        file=root/rel
        need(not file.is_symlink() and hashlib.sha256(file.read_bytes()).hexdigest()==sha, 'CONTROLLER_SOURCE_CHANGED')
    need(hashlib.sha256((root/'backend/server.py').read_bytes()).hexdigest()==b['controller_server_sha256'], 'NORMAL_ROLE_CHANGED')
    need(hashlib.sha256((export/'backend/server.py').read_bytes()).hexdigest()==b['closed_server_sha256'], 'CLOSED_ROLE_CHANGED')
    manifest_raw=(export/'backend/.runtime-source-manifest.json').read_bytes()
    need(hashlib.sha256(manifest_raw).hexdigest()==p['source_binding']['runtime_manifest_sha256'], 'CLOSED_MANIFEST_CHANGED')
    manifest=json.loads(manifest_raw)
    need(manifest['expected_sha256']==p['source_binding']['runtime_sha256'], 'CLOSED_RUNTIME_CHANGED')
    for item in manifest['files']:
        path=Path(item['path'])
        need(not path.is_absolute() and '..' not in path.parts, 'UNSAFE_RUNTIME_PATH')
        file=export/'backend'/path
        need(not file.is_symlink() and file.is_file()
             and hashlib.sha256(file.read_bytes()).hexdigest()==item['sha256'], 'CLOSED_MEMBER_CHANGED')
    actor=p['actor'];data=json.loads(private_bytes(Path(actor['private_uid_reference']['path']),actor['private_uid_reference']['sha256']))
    uid=identifier(data['user']['id'])
    need(hashlib.sha256(uid.encode()).hexdigest()==actor['user_id_sha256'], 'MEMBER_BINDING_CHANGED')
    member=digest({'schema':'earnalism.sredni_initial_review_member_account_binding.v1','user_id':uid})
    need(member==actor['source_Sredni_member_account_sha256'], 'SREDNI_MEMBER_BINDING_CHANGED')
    auth=json.loads((export/'backend/data/sredni_initial_review_authority.json').read_bytes())
    need({'owner_receipt_sha256':actor['Sredni_owner_sha256'],'member_account_sha256':member} in auth['accepted'], 'SOURCE_AUTHORITY_CHANGED')
    profile=b['Sredni_profile']
    symbols={'U':uid,'W120':'original120-'+digest({'member':uid,'original_owner_scope':actor['original120_owner_sha256']}),
             'W60':'sredni-initial-'+digest({'owner_receipt_sha256':actor['Sredni_owner_sha256'],'user_id':uid,
                 'slug':profile['SLUG'],'descriptor_sha256':profile['DESCRIPTOR'],'package_version':profile['PACKAGE']})}
    need(b['controller_server_sha256']==runtime['server_source_roles']['controller_normal_server_sha256']
         and b['closed_server_sha256']==runtime['server_source_roles']['closed_export_server_sha256'],'SERVER_ROLE_BINDINGS_CHANGED')
    need(p['source_binding']==runtime['expected_component'],'EXACT_COMPONENT_SCOPE_CHANGED')
    need(p['target']==runtime['target'] and p['actor']['user_id_sha256']==runtime['member_sha256'],'ACTOR_OR_TARGET_CHANGED')
    need(metadata_digest(p['queries'])==runtime['fixed_query_plan']['queries_sha256'],'FIXED_QUERIES_CHANGED')
    return b,p,symbols


def _adopt_client_bundle(st,bundle):
    need(type(bundle) is tuple and len(bundle)==2,'EXACT_LAZY_CLIENT_BUNDLE_REQUIRED')
    client,database=bundle
    need(st.client_ref is None,'CLIENT_ALREADY_CREATED')
    st.client_ref=client;st.factory_database=database
    # Return ownership exists even if original factory resolved after cutoff.
    # Actual source-bound factory must itself be exception-safe/register a client
    # created before it throws; a caller boolean cannot satisfy that obligation.
    st.claim_context.retain_client(client)


def _close_created_client(st):
    need(st.pending is None and (st.db_session is None or st.cleanup_done),
         'ORIGINAL_CLIENT_WORK_STILL_PENDING')
    need(st.client_ref is not None and not st.client_close_attempted,'CLIENT_CLOSE_ALREADY_ATTEMPTED')
    st.client_close_attempted=True
    st.client_ref.close()
    st.client_closed=True
    st.claim_context.client_closed(st.client_ref)


def _require_context(context, observer_sha256):
    """Only the existing controller helper's live opaque seventh claim qualifies."""
    need(context is not None and not isinstance(context,dict),'OPAQUE_CONTROLLER_PRECLAIM_REQUIRED')
    context.require_for(observer_sha256)
    context.assert_valid()
    runtime=context.runtime_contract
    need(metadata_digest(runtime)==context.runtime_sha256,'RUNTIME_CONTRACT_CHANGED')
    need(context.parent_operation_id=='802d0473580556086e23fff24e06a47a0a88bb2b89f74c72fcbfc39881fd2713'
         and context.amendment_sha256=='cf4d431974a7227e1603d74dc518fe6074a70d1d3f19c1d4cff32f4f4c9811c1'
         and context.amendment_scope_sha256=='309509775ddf6bb7782ff0b4813132131ae633d470bef8c8bc488f4b427719f0',
         'EXACT_PARENT_AMENDMENT_REQUIRED')
    need(type(context.historical_consumed) is int and context.historical_consumed==6
         and type(context.consumed) is int and context.consumed==7
         and type(context.ceiling) is int and context.ceiling==7,'SEVENTH_CLAIM_NOT_CONSUMED')
    need(type(runtime['original_consumed']) is int and runtime['original_consumed']==6
         and type(runtime['approved_cumulative_ceiling']) is int and runtime['approved_cumulative_ceiling']==7
         and type(runtime['additional_attempts']) is int and runtime['additional_attempts']==1,'CUMULATIVE_BUDGET_CHANGED')
    source_pins=runtime['source_pins']
    helper_source=inspect.getsourcefile(type(context))
    need(helper_source is not None and hashlib.sha256(Path(helper_source).read_bytes()).hexdigest()==source_pins['claim_helper'],
         'CONTROLLER_CLAIM_HELPER_SOURCE_CHANGED')
    need(source_pins['observer']==observer_sha256,'OBSERVER_SOURCE_CHANGED')
    # Require the actual preclaim bytes and physical evidence identity; do not
    # allocate another claim or key its namespace to approval/code hashes.
    claim=json.loads(private_bytes(context.claim_path,context.claim_sha256))
    need(claim['historical_consumed']==6 and claim['consumed']==7 and claim['ceiling']==7,
         'DURABLE_SEVENTH_CLAIM_CHANGED')
    info=Path(context.evidence_directory).stat()
    need(stat.S_ISDIR(info.st_mode) and info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o700
         and (info.st_dev,info.st_ino)==(context.evidence_device,context.evidence_inode),'CONTROLLER_EVIDENCE_ANCHOR_CHANGED')
    need(type(context.deadline_monotonic) in (int,float) and math.isfinite(context.deadline_monotonic)
         and 0<context.deadline_monotonic-time.monotonic()<=60,'ORIGINAL_COLLECTION_DEADLINE_INVALID')
    return context


async def _run_preclaimed(context,readers,client_factory,observer_sha256):
    b,p,symbols=specs(context)
    runtime=context.runtime_contract;actual=runtime['required_actual_before_any_claim']
    pin_adapter(readers,actual['actual_transport_source_sha256'])
    pin_adapter(client_factory,actual['actual_client_factory_source_sha256'])
    need(inspect.isfunction(client_factory) and client_factory.__closure__ is None
         and not inspect.iscoroutinefunction(client_factory),
         'SOURCE_DEFINED_TOP_LEVEL_CLIENT_FACTORY_REQUIRED')
    authority=RootReadAuthority(actual['separate_execution_owner_authorization_sha256'],
        runtime['owner_budget_decision']['sha256'],actual['current_profile_provenance_sha256'],
        runtime['fixed_query_plan']['sha256'],observer_sha256,context.amendment_scope_sha256,
        context.issued_at,context.expires_at,1,7,7)
    st=State(b,p,symbols,authority,SEAL,context.deadline_monotonic,
             claim_context=context,bytes_written=context.retained_bytes,
             claim_directory=Path(context.evidence_directory))
    OWNED_ATTEMPTS[id(st)]=st
    try:
        for branch,sha in [('main',actual['admission_controller_commit_sha']),
                           ('codex/main-approved-integration','5e739e69d3086a14d83f802f7cc5b3da9b90ddf0')]:
            st.ref_reads+=1;got=await owned_wait(st,lambda branch=branch:readers.github_ref(branch))
            need(got==sha,'CANONICAL_REMOTE_REF_DRIFT')
        await metadata(st,readers,'before')
        st.check();context.require_for(observer_sha256)
        # This factory must already be source/provenance reviewed and exception
        # safe. No caller-provided existing client can predate the durable claim.
        await owned_wait(st,lambda:asyncio.to_thread(client_factory,context),kind='client_factory')
        client,database=st.client_ref,st.factory_database
        st.check()
        await database_snapshot(st,client,database)
        need(st.abort_acknowledged and st.cleanup_done and not st.cleanup_error
             and st.pending is None and st.reads==12 and st.principal_commands==1,'SNAPSHOT_COMPLETION_UNKNOWN')
        # SDK cleanup only, after actual abort/session completion. Never close
        # over an original pending query/session. Current factory pins are null.
        _close_created_client(st)
        await metadata(st,readers,'after');st.check()
        need(st.metadata_reads==6 and st.ref_reads==2,'EXACT_IDENTITY_ENVELOPE_REQUIRED')
        legacy_views(st)
        payload=snapshot_payload(st,complete=True)
        payload['controller_claim_sha256']=context.claim_sha256
        payload['runtime_contract_sha256']=context.runtime_sha256
        payload['historical_consumed_preserved']=6
        payload['cumulative_observation']=7
        persist(st,'SNAPSHOT.private.json',payload)
        result={'schema':'earnalism.controller_financial_observation_result.v1',
            'status':'RAW_CAPTURE_COMPLETE_PENDING_PURE_EVALUATION','claim_sha256':context.claim_sha256,
            'runtime_contract_sha256':context.runtime_sha256,'observer_source_sha256':observer_sha256,
            'historical_consumed_preserved':6,'consumed':7,'ceiling':7,
            'find_commands':12,'principal_commands':1,'provider_reads':6,'github_ref_reads':2,
            'explicit_abort_invocations':st.abort_calls,'abort_acknowledged':True,
            'client_closed':True,'commits':0,'native_gates_qualified':False,'normal_release':'HELD'}
        persist(st,'RESULT.json',result);st.check();return result
    except BaseException as error:
        code=error.code if isinstance(error,Hold) else 'CAPTURE_OR_CLEANUP_UNKNOWN'
        if st.pending is not None and (st.cleanup_task is None or st.cleanup_task.done()):
            own_cleanup(st,st.db_session,st.transaction_started)
        try:
            if not (st.claim_directory/'SNAPSHOT.private.json').exists():
                persist(st,'SNAPSHOT.private.json',snapshot_payload(st,complete=False))
            persist(st,'RESULT.json',{'schema':'earnalism.controller_financial_observation_result.v1',
                'status':'HOLD_UNKNOWN_NO_RETRY','code':code,'claim_sha256':context.claim_sha256,
                'consumed':7,'ceiling':7,'historical_consumed_preserved':6,
                'native_gates_qualified':False,'normal_release':'HELD'})
        except BaseException:code='EVIDENCE_WRITE_UNKNOWN'
        raise Hold(code) from None
    finally:
        st.collection_done=True;retire(st)
        # No context.close_when_settled here: controller closes it only after
        # this observer Task and every registered original/cleanup have settled.


async def observe_preclaimed(*,context,readers,client_factory):
    """Controller-only entry. No standalone collect, flag or per-approval claim.

    A budget approval or public bool cannot create this opaque helper context.
    The existing controller must have consumed claim7 and bound actual current
    execution/source/client/transport/clock evidence before this entry is called.
    """
    observer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    _require_context(context,observer_sha256)
    context.begin_observer(observer_sha256)  # Burn invocation before Task/factory/I/O.
    task=asyncio.create_task(_run_preclaimed(context,readers,client_factory,observer_sha256))
    context.track_future(task)
    # Shield entire operation, including lazy client construction and cleanup.
    return await asyncio.shield(task)


if __name__=='__main__':
    raise SystemExit('CONTROLLER_PRECLAIM_ONLY_NO_STANDALONE_EXECUTION')
