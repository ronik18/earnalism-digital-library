"""Controller-owned seventh recovery-observation claim; no import-time I/O.

No CLI, arming switch, authority issuer, provider/client construction or ledger
reset. Only the existing protected controller may supply separately authenticated
execution admission. The current prepared runtime contract denies before claim.
"""
from __future__ import annotations
import asyncio
import fcntl
import hashlib
import json
import inspect
import math
import os
import stat
import time
from datetime import datetime,timezone
from pathlib import Path

JOURNAL=Path('/Users/ronikbasak/Documents/Earnalism/release-evidence/optimization-20261030/operations')
JOURNAL_ID='eddf1a6a0ad3d11383d5d41f8dc5a0752142651affcf38a405f874ffe1db8ddf'
RECOVERY_SCOPE='c27ccdc80ee350b8c92639a26721a14fa9a47e256c69130fda75e6018424a935'
PARENT='802d0473580556086e23fff24e06a47a0a88bb2b89f74c72fcbfc39881fd2713'
AMENDMENT='cf4d431974a7227e1603d74dc518fe6074a70d1d3f19c1d4cff32f4f4c9811c1'
AMENDMENT_SCOPE='309509775ddf6bb7782ff0b4813132131ae633d470bef8c8bc488f4b427719f0'
SOURCE=Path('/private/tmp/pr656-native-successor-20261108/pair-financial-budget-amendment/SOURCE-BINDING.json')
SOURCE_SHA='b729145d3377427c5332db0835f9a8805bb0d120cfc8e2a45b9bd5e3655034d3'
BUDGET_OWNER=Path('/private/tmp/pr656-native-successor-20261108/controller-financial-admission/OWNER-BUDGET-DECISION.ACTUAL.json')
BUDGET_OWNER_SHA='2fa194d36d0a8fe2bb76701e08bcc6934f1ffa788a09b511cd42edba055d8fd6'
SLOT_NAME='.recovery-observations-'+RECOVERY_SCOPE+'-observation-000007'
CLAIM_NAME='observation-000007.claim'
MAX_BYTES=1048576
_SEAL=object()
OWNED_CLAIMS=set()

class FinancialHeld(Exception):pass

def need(ok,code):
    if not ok:raise FinancialHeld(code)

def sha(value):return type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)
def encode(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(value):return hashlib.sha256(encode(value)).hexdigest()
def _identity(info):return info.st_dev,info.st_ino,info.st_uid,stat.S_IMODE(info.st_mode)

def _raw(path,expected):
    need(sha(expected),'EXACT_INPUT_PIN_REQUIRED')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as f:
        info=os.fstat(f.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid()
             and stat.S_IMODE(info.st_mode)==0o600 and info.st_size<=MAX_BYTES,'PRIVATE_INPUT_CUSTODY')
        raw=f.read(MAX_BYTES+1)
    need(len(raw)<=MAX_BYTES and hashlib.sha256(raw).hexdigest()==expected,'EXACT_INPUT_CHANGED')
    return json.loads(raw)

def _journal_identity():
    need(JOURNAL.is_absolute() and not JOURNAL.is_symlink(),'JOURNAL_LOCATION_CHANGED')
    rows=[]
    for p in (JOURNAL.resolve().parent,JOURNAL.resolve()):
        st=p.lstat()
        need(stat.S_ISDIR(st.st_mode) and st.st_uid==os.getuid()
             and not stat.S_IMODE(st.st_mode)&0o022,'JOURNAL_CUSTODY_CHANGED')
        rows.append({'path':str(p),'device':st.st_dev,'inode':st.st_ino,'uid':st.st_uid,'mode':stat.S_IMODE(st.st_mode)})
    return digest(rows)

def validate_runtime_contract(runtime_contract,*,expected_runtime_sha256,observer_source_sha256,
                              controller_source_sha256,now=None):
    """Pure validation, not owner authentication or a permit. No live reads."""
    need(type(runtime_contract) is dict and sha(expected_runtime_sha256)
         and digest(runtime_contract)==expected_runtime_sha256,'RUNTIME_CONTRACT_CHANGED')
    r=runtime_contract
    need(r.get('schema')=='earnalism.source_bound_financial_runtime_contract.v1'
         and r.get('status')=='ADMITTED_EXACT_FINANCIAL_RUNTIME'
         and r.get('execution_authorized') is True,'NO_EXACT_EXECUTION_ADMISSION')
    need(r.get('amendment_sha256')==AMENDMENT and r.get('amendment_scope_sha256')==AMENDMENT_SCOPE
         and r.get('parent_operation_id')==PARENT,'AMENDMENT_OR_PARENT_CHANGED')
    need(type(r.get('original_consumed')) is int and r['original_consumed']==6
         and type(r.get('approved_cumulative_ceiling')) is int and r['approved_cumulative_ceiling']==7
         and type(r.get('additional_attempts')) is int and r['additional_attempts']==1,'CUMULATIVE_BUDGET_CHANGED')
    need(type(r.get('runtime_available_attempts')) is int and r['runtime_available_attempts']==1
         and r.get('seventh_claim_executed') is False,'NO_AVAILABLE_UNCLAIMED_SEVENTH_ATTEMPT')
    limits={'maxPoolSize':1,'minPoolSize':0,'retryReads':False,'retryWrites':False,
      'serverSelectionTimeoutMS_maximum':1000,'connectTimeoutMS_maximum':1000,
      'socketTimeoutMS_maximum':1000,'new_client_only_after_claim':True}
    need(encode(r.get('expected_diagnostic_client_limits'))==encode(limits),'DIAGNOSTIC_CLIENT_ENVELOPE_CHANGED')
    need(r.get('normal_release')==r.get('frontend_promotion')=='HELD','RELEASE_HOLD_REQUIRED')
    required=r.get('required_actual_before_any_claim')
    fields={'separate_execution_owner_authorization_sha256','protected_host_identity_sha256',
      'trusted_existing_controller_resolver_sha256','actual_client_factory_source_sha256',
      'actual_transport_source_sha256','current_profile_provenance_sha256',
      'current_runtime_dependency_closure_sha256','expected_principal_sha256',
      'expected_auth_database_sha256','expected_client_seed_set_sha256',
      'runtime_flag_requirement_decision','runtime_flag_channel_or_applicability_sha256',
      'current_config_secret_version_context_sha256','admission_controller_commit_sha',
      'canonical_history_preservation_sha256','issued_at','expires_at'}
    need(type(required) is dict and set(required)==fields,'EXACT_CURRENT_ADMISSION_SCHEMA')
    for key in fields-{'runtime_flag_requirement_decision','admission_controller_commit_sha','issued_at','expires_at'}:
        need(sha(required[key]),'CURRENT_PROVENANCE_UNBOUND')
    need(type(required['admission_controller_commit_sha']) is str
         and len(required['admission_controller_commit_sha'])==40
         and all(c in '0123456789abcdef' for c in required['admission_controller_commit_sha']),'ADMISSION_CONTROLLER_COMMIT_UNBOUND')
    need(required['runtime_flag_requirement_decision'] is False,'RUNTIME_APPLICABILITY_UNBOUND_OR_UNSUPPORTED')
    pins=r.get('source_pins')
    need(type(pins) is dict and set(pins)=={'controller','observer','claim_helper','client_factory','transport'}
         and pins['client_factory']==required['actual_client_factory_source_sha256']
         and pins['transport']==required['actual_transport_source_sha256'] and pins.get('observer')==observer_source_sha256
         and sha(observer_source_sha256) and pins.get('controller')==controller_source_sha256
         and sha(controller_source_sha256)
         and pins.get('claim_helper')==hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'EXACT_EXECUTABLE_SOURCE_UNBOUND')
    issued=datetime.fromisoformat(required['issued_at']);expires=datetime.fromisoformat(required['expires_at'])
    current=datetime.now(timezone.utc) if now is None else now
    need(isinstance(current,datetime) and current.tzinfo is not None and issued.tzinfo is not None
         and expires.tzinfo is not None and issued<=current<expires
         and 0<(expires-issued).total_seconds()<=900,'RUNTIME_AUTHORITY_CLOCK_INVALID')
    return issued,expires

def validate_execution_approval(approval,runtime,runtime_sha,*,now):
    """Repeat exact protected-controller decision checks; does not issue trust."""
    keys={'schema','status','approved','action','runtime_contract_sha256',
      'controller_source_sha256','claim_helper_source_sha256','observer_source_sha256',
      'client_factory_source_sha256','transport_source_sha256','owner_execution_receipt_sha256',
      'parent_operation_id','amendment_sha256','approved_at','expires_at','execution_authorized','normal_release'}
    need(type(approval) is dict and set(approval)==keys,'EXACT_SEPARATE_EXECUTION_APPROVAL_REQUIRED')
    pins=runtime['source_pins']
    expected={'schema':'earnalism.financial_execution_approval.v1','status':'APPROVED_EXACT_FINANCIAL_CAPTURE',
      'approved':True,'action':'observe_paired_financial_snapshot','runtime_contract_sha256':runtime_sha,
      'controller_source_sha256':pins['controller'],'claim_helper_source_sha256':pins['claim_helper'],
      'observer_source_sha256':pins['observer'],'client_factory_source_sha256':pins['client_factory'],
      'transport_source_sha256':pins['transport'],'parent_operation_id':PARENT,'amendment_sha256':AMENDMENT,
      'execution_authorized':True,'normal_release':'HELD'}
    for key,value in expected.items():
        need(type(approval.get(key)) is type(value) and approval[key]==value,'SEPARATE_EXECUTION_APPROVAL_CHANGED')
    actual=runtime['required_actual_before_any_claim'];owner=approval['owner_execution_receipt_sha256']
    need(sha(owner) and owner==actual['separate_execution_owner_authorization_sha256'] and owner!=BUDGET_OWNER_SHA,
         'BUDGET_APPROVAL_IS_NOT_EXECUTION_AUTHORITY')
    start=datetime.fromisoformat(approval['approved_at']);end=datetime.fromisoformat(approval['expires_at'])
    need(all(t.tzinfo is not None for t in (start,end,now)) and start<=now<end
         and 0<(end-start).total_seconds()<=900 and start==datetime.fromisoformat(actual['issued_at'])
         and end==datetime.fromisoformat(actual['expires_at']),'EXECUTION_APPROVAL_CLOCK_INVALID')
    return digest(approval)

class SeventhClaim:
    """Opaque controller claim with permanent on-disk consumption and live custody."""
    def __init__(self,token,*,runtime,raw_claim,lock_fd,journal_fd,parent_fd,evidence_fd,deadline):
        need(token is _SEAL,'CONTROLLER_CLAIM_REQUIRED')
        self._seal=token;self._runtime=encode(runtime);self._claim=raw_claim
        self._lock_fd=lock_fd;self._journal_fd=journal_fd;self._parent_fd=parent_fd;self._evidence_fd=evidence_fd
        self._deadline=deadline;self._closed=False;self._work=set();self._clients={};self._observer_started=False;self._factory_started=False;self._client_loop=asyncio.get_running_loop()
        self._retained=len(raw_claim);self._names={CLAIM_NAME}
        info=os.fstat(evidence_fd);self.evidence_device=info.st_dev;self.evidence_inode=info.st_ino
        required=runtime['required_actual_before_any_claim'];self.issued_at=datetime.fromisoformat(required['issued_at']);self.expires_at=datetime.fromisoformat(required['expires_at'])
        OWNED_CLAIMS.add(self)
    @property
    def runtime_contract(self):return json.loads(self._runtime)
    @property
    def runtime_sha256(self):return hashlib.sha256(self._runtime).hexdigest()
    @property
    def parent_operation_id(self):return PARENT
    @property
    def amendment_sha256(self):return AMENDMENT
    @property
    def amendment_scope_sha256(self):return AMENDMENT_SCOPE
    @property
    def historical_consumed(self):return 6
    @property
    def consumed(self):return 7
    @property
    def ceiling(self):return 7
    @property
    def evidence_directory(self):return JOURNAL.parent/SLOT_NAME
    @property
    def evidence_fd(self):return self._evidence_fd
    @property
    def claim_path(self):return self.evidence_directory/CLAIM_NAME
    @property
    def claim_sha256(self):return hashlib.sha256(self._claim).hexdigest()
    @property
    def deadline_monotonic(self):return self._deadline
    @property
    def retained_bytes(self):return self._retained
    def assert_valid(self,check_deadline=True):
        need(self._seal is _SEAL and not self._closed,'CLAIM_CUSTODY_CLOSED')
        need(_journal_identity()==JOURNAL_ID,'ORIGINAL_JOURNAL_CHANGED')
        need(_identity(os.fstat(self._journal_fd))==_identity(JOURNAL.lstat()),'JOURNAL_DESCRIPTOR_CHANGED')
        need(_identity(os.fstat(self._parent_fd))==_identity(JOURNAL.parent.lstat()),'PARENT_DESCRIPTOR_CHANGED')
        need(_identity(os.fstat(self._lock_fd))==_identity(os.stat('.reconciliation.lock',dir_fd=self._journal_fd,follow_symlinks=False)),'ORIGINAL_LOCK_CHANGED')
        info=os.stat(SLOT_NAME,dir_fd=self._parent_fd,follow_symlinks=False)
        need(stat.S_ISDIR(info.st_mode) and info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o700
             and _identity(os.fstat(self._evidence_fd))==_identity(info) and (info.st_dev,info.st_ino)==(self.evidence_device,self.evidence_inode),'SEVENTH_SLOT_MOVED')
        fd=os.open(CLAIM_NAME,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=self._evidence_fd)
        with os.fdopen(fd,'rb') as f:
            st=os.fstat(f.fileno())
            need(stat.S_ISREG(st.st_mode) and st.st_uid==os.getuid() and stat.S_IMODE(st.st_mode)==0o600,'CLAIM_FILE_CUSTODY_CHANGED')
            raw=f.read(MAX_BYTES+1)
        need(raw==self._claim,'SEVENTH_CLAIM_CHANGED')
        if check_deadline:
            need(time.monotonic()<self._deadline and datetime.now(timezone.utc)<self.expires_at,'COLLECTION_DEADLINE_EXCEEDED')
        return self
    def require_for(self,observer_sha256):
        self.assert_valid()
        need(self.runtime_contract['source_pins']['observer']==observer_sha256,'OBSERVER_SOURCE_CHANGED')
        return self
    def begin_observer(self,observer_sha256):
        self.require_for(observer_sha256)
        need(not self._observer_started,'OBSERVER_ALREADY_DISPATCHED_NO_RETRY')
        self._observer_started=True
        return self
    def begin_client_factory(self,factory_sha256):
        self.assert_valid()
        need(self._observer_started and not self._factory_started
             and self.runtime_contract['source_pins']['client_factory']==factory_sha256,
             'CLIENT_FACTORY_ALREADY_STARTED_OR_UNBOUND')
        self._factory_started=True
        return self
    def get_client_event_loop(self):
        self.assert_valid()
        need(self._factory_started and not self._client_loop.is_closed()
             and self._client_loop.is_running(),'OWNED_CLIENT_LOOP_REQUIRED')
        return self._client_loop
    def track_future(self,future):
        need(self._seal is _SEAL and not self._closed and isinstance(future,asyncio.Future),'ORIGINAL_FUTURE_REQUIRED')
        self._work.add(future)
        self.assert_valid(check_deadline=False)
        return future
    def retain_client(self,client):
        need(self._seal is _SEAL and not self._closed,'CLAIM_CUSTODY_CLOSED')
        self._clients[id(client)]=client
        return client
    def client_closed(self,client):
        need(self._clients.get(id(client)) is client,'UNOWNED_CLIENT_CLOSE')
        del self._clients[id(client)]
    def append_private(self,name,value):
        self.assert_valid(check_deadline=False)
        need(type(name) is str and name in {'SNAPSHOT.private.json','RESULT.json','CLEANUP.json','REFS.json','BEFORE.json','AFTER.json','HELD.json'}
             and name not in self._names,'EXCLUSIVE_EVIDENCE_NAME_REQUIRED')
        raw=encode(value);need(self._retained+len(raw)<=MAX_BYTES,'AGGREGATE_EVIDENCE_BYTE_BOUND')
        # Reserve before open/write; partial/failed output burns this name too.
        self._names.add(name);self._retained+=len(raw)
        fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self._evidence_fd)
        with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        os.fsync(self._evidence_fd)
        return hashlib.sha256(raw).hexdigest()
    def close_when_settled(self):
        need(not self._closed and not self._clients and all(f.done() for f in self._work),'ORIGINAL_WORK_OR_CLIENT_STILL_OWNED')
        need(not self._observer_started or bool(self._work),'UNTRACKED_OBSERVER_LIFECYCLE')
        # Permanent slot/claim is never deleted or reset. No client/SDK cleanup
        # is attempted over an unresolved original Future.
        for f in self._work:
            if not f.cancelled():f.exception()
        fcntl.flock(self._lock_fd,fcntl.LOCK_UN)
        for fd in (self._evidence_fd,self._lock_fd,self._journal_fd,self._parent_fd):os.close(fd)
        self._closed=True;OWNED_CLAIMS.discard(self)

def claim_seventh(adapter,runtime_contract,expected_runtime_sha256,
                  observer_source_sha256,controller_source_sha256,*,execution_approval):
    """Future protected-controller call only. No provider/client work is started.

    The caller must authenticate the separate exact execution-owner decision;
    budget-only approval/JSON shapes/source hashes are not authority producers.
    """
    issued,expires=validate_runtime_contract(runtime_contract,expected_runtime_sha256=expected_runtime_sha256,
        observer_source_sha256=observer_source_sha256,controller_source_sha256=controller_source_sha256)
    approval_digest=validate_execution_approval(execution_approval,runtime_contract,expected_runtime_sha256,now=adapter.clock())
    need(adapter.owner_authorized is True,'EXISTING_PROTECTED_CONTROLLER_AUTHORITY_REQUIRED')
    need(Path(adapter.journal).resolve()==JOURNAL.resolve() and _journal_identity()==JOURNAL_ID,'ORIGINAL_PHYSICAL_JOURNAL_REQUIRED')
    source=_raw(SOURCE,SOURCE_SHA);owner=_raw(BUDGET_OWNER,BUDGET_OWNER_SHA)
    need(owner['status']=='OWNER_APPROVED_BUDGET_ONLY_NO_EXECUTION' and owner['historical_consumed_preserved']==6
         and owner['cumulative_ceiling_approved']==7 and owner['additional_observations_approved']==1,'ORIGINAL_BUDGET_DECISION_CHANGED')
    module=inspect.getmodule(type(adapter));pair_module=getattr(module,'pair',None)
    pair_ref=source['controller_sources']['pair']
    need(pair_module is not None and Path(pair_module.__file__).resolve()==Path(pair_ref['path']).resolve()
         and hashlib.sha256(Path(pair_ref['path']).read_bytes()).hexdigest()==pair_ref['sha256'],'HISTORICAL_PAIR_VALIDATOR_CHANGED')
    need(runtime_contract.get('member_sha256')==source['actor_user_id_sha256'],'MEMBER_SCOPE_CHANGED')
    historical={'path':'/private/tmp/pr656-native-successor-20261107/read-only-collector/BINDINGS.json',
      'sha256':'bd4f820eb360c12c06d251408c0d9153b84b64d913d1a9f93cd5ee23108fdc62','retained_unmodified':True}
    need(encode(runtime_contract.get('historical_bindings'))==encode(historical),'HISTORICAL_BINDINGS_CHANGED')
    _raw(historical['path'],historical['sha256'])
    need(runtime_contract['owner_budget_decision']=={'path':str(BUDGET_OWNER),'sha256':BUDGET_OWNER_SHA},'BUDGET_OWNER_BINDING_CHANGED')
    for key in ('expected_component','target','original_action_scope'):
        need(runtime_contract[key]==source[key],'ORIGINAL_SOURCE_OR_COMPONENT_CHANGED')
    for ref in [source['original_action_baseline'],source['original_capture_custody'],*source['original_consumed_artifacts'].values()]:_raw(ref['path'],ref['sha256'])
    custody=_raw(source['original_capture_custody']['path'],source['original_capture_custody']['sha256'])
    for original in (custody['parent'],custody['output']):
        original_path=Path(original['path']);st=original_path.lstat()
        need(not original_path.is_symlink() and stat.S_ISDIR(st.st_mode)
             and (st.st_dev,st.st_ino,st.st_uid,stat.S_IMODE(st.st_mode))==
             (original['device'],original['inode'],original['uid'],original['mode']),'ORIGINAL_SIX_PHYSICAL_CUSTODY_CHANGED')
    need(custody['scope_sha256']==RECOVERY_SCOPE and custody['capture_budget']['combined_counted_total']==6,'ORIGINAL_SIX_LINEAGE_CHANGED')
    plan=_raw(source['financial_read_plan']['path'],source['financial_read_plan']['sha256'])
    need(runtime_contract['fixed_query_plan']['path']==source['financial_read_plan']['path']
         and runtime_contract['fixed_query_plan']['sha256']==source['financial_read_plan']['sha256']
         and runtime_contract['fixed_query_plan']['queries_sha256']==digest(plan['queries']),'EXACT_QUERY_PLAN_CHANGED')
    parent_fd=journal_fd=lock_fd=evidence_fd=None;reserved=False;context=None
    try:
        parent_fd=os.open(JOURNAL.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        journal_fd=os.open(JOURNAL.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent_fd)
        lock_fd=os.open('.reconciliation.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600,dir_fd=journal_fd)
        info=os.fstat(lock_fd);need(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o600,'ORIGINAL_LOCK_CUSTODY')
        fcntl.flock(lock_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        need(_journal_identity()==JOURNAL_ID and _identity(os.fstat(journal_fd))==_identity(JOURNAL.lstat())
             and _identity(os.fstat(parent_fd))==_identity(JOURNAL.parent.lstat()),'JOURNAL_ANCHOR_CHANGED')
        retained={name:_raw(source[name]['path'],source[name]['sha256']) for name in ('parent','pending','component')}
        pending=adapter._read_pending();parent=retained['parent'];component=retained['component']
        need(pending==retained['pending'] and pending['parent_operation_id']==PARENT
             and pending['child_operation_id'] is None and pending['state']==parent['state']=='APPLIED_COMPONENT_VERIFIED_READER_PENDING'
             and digest(parent)==pending['parent_record_sha256'] and digest(component)==pending['component_receipt_sha256']==source['component_receipt_digest'], 'PENDING_PAIR_CHANGED')
        pair_module.validate(parent['binding'])
        adapter._native_budget(parent['action'],parent['binding'],claim=False,own_operation_id=PARENT)
        validate_runtime_contract(runtime_contract,expected_runtime_sha256=expected_runtime_sha256,
            observer_source_sha256=observer_source_sha256,controller_source_sha256=controller_source_sha256,now=adapter.clock())
        need(validate_execution_approval(execution_approval,runtime_contract,expected_runtime_sha256,now=adapter.clock())==approval_digest,'EXECUTION_APPROVAL_CHANGED_UNDER_LOCK')
        # Exclusive DIRECTORY CREATION is the consumption point. Any existing
        # directory, including a partial/empty crash artifact, permanently denies.
        need(_journal_identity()==JOURNAL_ID
             and _identity(os.fstat(journal_fd))==_identity(JOURNAL.lstat())
             and _identity(os.fstat(parent_fd))==_identity(JOURNAL.parent.lstat())
             and _identity(os.fstat(lock_fd))==_identity(os.stat('.reconciliation.lock',dir_fd=journal_fd,follow_symlinks=False)),
             'ORIGINAL_LOCK_OR_JOURNAL_CHANGED_BEFORE_CONSUMPTION')
        collection_start=time.monotonic()
        deadline=collection_start+min(60,(expires-datetime.now(timezone.utc)).total_seconds())
        os.mkdir(SLOT_NAME,0o700,dir_fd=parent_fd);reserved=True;os.fsync(parent_fd)
        evidence_fd=os.open(SLOT_NAME,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent_fd)
        record={'schema':'earnalism.cumulative_recovery_observation_claim.v1','recovery_scope_sha256':RECOVERY_SCOPE,
          'original_journal_identity_sha256':JOURNAL_ID,'parent_operation_id':PARENT,'historical_consumed':6,'observation_index':7,
          'consumed_after_claim':7,'cumulative_ceiling':7,'consumed':7,'ceiling':7,'amendment_sha256':AMENDMENT,'amendment_scope_sha256':AMENDMENT_SCOPE,
          'runtime_contract_sha256':expected_runtime_sha256,'execution_approval_sha256':approval_digest,
          'execution_owner_receipt_sha256':execution_approval['owner_execution_receipt_sha256'],
          'execution_approved_at':execution_approval['approved_at'],'execution_expires_at':execution_approval['expires_at'],
          'observer_source_sha256':observer_source_sha256,
          'controller_source_sha256':controller_source_sha256,'claim_helper_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'issued_at':issued.isoformat(),'expires_at':expires.isoformat(),'claimed_at':datetime.now(timezone.utc).isoformat(),
          'source_sha256':runtime_contract['expected_component']['closed'],'source_pins':runtime_contract['source_pins'],
          'original_custody_sha256':source['original_capture_custody']['sha256'],'original_artifacts':source['original_consumed_artifacts'],
          'deadline_monotonic':deadline,'status':'CONSUMED_BEFORE_FIRST_LIVE_IO_NO_RETRY','normal_release':'HELD'}
        raw=encode(record);need(len(raw)<MAX_BYTES,'CLAIM_BYTE_BOUND')
        fd=os.open(CLAIM_NAME,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=evidence_fd)
        with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        os.fsync(evidence_fd)
        context=SeventhClaim(_SEAL,runtime=runtime_contract,raw_claim=raw,lock_fd=lock_fd,journal_fd=journal_fd,
                             parent_fd=parent_fd,evidence_fd=evidence_fd,deadline=deadline)
        context.assert_valid();return context
    except BaseException as error:
        # Directory/partial claim is never removed, even if durable write outcome
        # is uncertain. No observation/client dispatch has happened in this helper.
        if context is not None:
            context._closed=True;OWNED_CLAIMS.discard(context)
        for fd in (evidence_fd,lock_fd,journal_fd,parent_fd):
            if fd is not None:
                try:os.close(fd)
                except OSError:pass
        if reserved:raise FinancialHeld('SEVENTH_SLOT_CONSUMED_OR_UNKNOWN_NO_RETRY') from None
        raise FinancialHeld('SEVENTH_CLAIM_DENIED_NO_DISPATCH') from None
