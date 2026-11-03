"""Private Sredni60/3/15 admission; a prepared packet is never permission.

Only generic private-file/journal utilities are reused from original120; its
parser, owner receipts, scopes, counters and operators are never invoked.
"""
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
from pathlib import Path
import hashlib,json,re
try:
    from . import native_audio_review_authority as files
    from . import sredni_initial_review_profile as profile
except ImportError:
    import native_audio_review_authority as files
    import sredni_initial_review_profile as profile

class AdmissionStop(ValueError):pass
def need(ok,code):
    if not ok:raise AdmissionStop(code)
def utc(value):
    if isinstance(value,str):value=datetime.fromisoformat(value.replace('Z','+00:00'))
    need(isinstance(value,datetime) and value.tzinfo is not None,'AWARE_REVIEW_CLOCK_REQUIRED')
    return value.astimezone(timezone.utc)
def normalized(value):
    if isinstance(value,datetime):return {'utc':utc(value).isoformat()}
    if isinstance(value,dict):return {k:normalized(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [normalized(v) for v in value]
    return value
def digest(value):return profile.digest(normalized(value))
def identity_binding(user_id,auth_session_id):
    return profile.digest({'schema':'earnalism.sredni_initial_review_member_binding.v1','user_id':user_id,'auth_session_id':auth_session_id})
def private_json(path,sha):
    need(profile.SHA.fullmatch(str(sha)) and sha!='0'*64,'EXTERNAL_FILE_HASH_REQUIRED')
    try:return files.private_json(Path(path),sha)
    except Exception:raise AdmissionStop('PRIVATE_PINNED_FILE_UNAVAILABLE') from None
def current(a,now=None):
    need(utc(now or datetime.now(timezone.utc))<a.expires_at,'REVIEW_OPERATION_AUTHORITY_EXPIRED')

@dataclass(frozen=True)
class AdmittedOperation:
    operation_id:str
    action:str
    user_id:str
    auth_session_id:str
    owner_receipt_sha256:str
    identity_binding_sha256:str
    identity_evidence_sha256:str
    execution_sha256:str
    authority_sha256:str
    intent_sha256:str
    expected_state_sha256:str|None
    expires_at:datetime
    grant_expires_at:datetime
    grant_id:str
    journal:dict


def admit(path,expected_sha256,*,now,allow_expired_status=False):
    """Complete local receipt admission BEFORE any profile/client/DB access."""
    b=private_json(path,expected_sha256);now=utc(now)
    def observation_time(value,code):
        age=now-utc(value)
        # Status rechecks the same already-attempted immutable operation only.
        # Replaying historical evidence never creates a new grant/allowance.
        need(age>=timedelta(0) and (allow_expired_status or age<=timedelta(minutes=15)),code)
    keys={'schema','operation_id','action','user_id','auth_session_id','slug','descriptor_sha256','package_version',
          'owner','identity','execution','source','intent','journal','expected_state_sha256','expires_at','grant_expires_at','grant_id'}
    need(isinstance(b,dict) and set(b)==keys and b['schema']=='earnalism.sredni_initial_review_operation.v1','EXACT_REVIEW_OPERATION_SCHEMA_REQUIRED')
    need(b['action'] in {'observe','prepare-namespace','provision','close'} and re.fullmatch('[A-Za-z0-9_-]{16,128}',b['operation_id']),
         'EXACT_REVIEW_ACTION_OR_OPERATION_REQUIRED')
    need((b['slug'],b['descriptor_sha256'],b['package_version'])==(profile.SLUG,profile.DESCRIPTOR,profile.PACKAGE),'EXACT_SREDNI_STORED_SCOPE_REQUIRED')
    need(all(isinstance(b[k],str) and b[k] for k in ['user_id','auth_session_id']),'REAL_MEMBER_BINDING_REQUIRED')
    receipts={}
    for role in ['owner','identity','execution','source','intent']:
        ref=b[role];need(isinstance(ref,dict) and set(ref)=={'path','sha256'},'EXACT_PRIVATE_RECEIPT_REFERENCE_REQUIRED')
        receipts[role]=private_json(ref['path'],ref['sha256'])
    owner=receipts['owner'];identity=receipts['identity'];execution=receipts['execution'];source=receipts['source'];intent=receipts['intent']
    need(owner.get('schema')=='earnalism.owner_sredni_initial_review_permission.v1' and owner.get('status')=='APPROVED'
         and owner.get('question_id') and owner.get('question') and owner.get('answer')
         and hashlib.sha256(owner['question'].encode()).hexdigest()==owner.get('question_sha256')
         and owner.get('slug')==profile.SLUG and owner.get('descriptor_sha256')==profile.DESCRIPTOR
         and owner.get('package_version')==profile.PACKAGE
         and owner.get('maximum_seconds')==60 and owner.get('maximum_starts')==3 and owner.get('maximum_grant_lifetime_seconds')==900
         and owner.get('existing_credit_only') is True and owner.get('new_purchase_or_original120_reset') is False
         and owner.get('private_mongo_metadata_scope')=='SREDNI_ONLY_THREE_COLLECTIONS_AND_REQUIRED_INDEXES',
         'ACTUAL_EXACT_SREDNI_OWNER_REPLY_REQUIRED')
    bound=identity_binding(b['user_id'],b['auth_session_id'])
    need(identity.get('schema')=='earnalism.sredni_initial_review_actual_member.v1'
         and identity.get('source')=='OWNER_SELECTED_AUTHENTICATED_NORMAL_MEMBER'
         and identity.get('user_id')==b['user_id'] and identity.get('auth_session_id')==b['auth_session_id']
         and identity.get('identity_binding_sha256')==bound and identity.get('users_me_http')==200
         and identity.get('devices_http')==200,'GENUINE_CURRENT_NORMAL_MEMBER_ASSOCIATION_REQUIRED')
    observation_time(identity['observed_at'],'FRESH_MEMBER_OBSERVATION_REQUIRED')
    need(source.get('schema')=='earnalism.sredni_initial_review_actual_serving_source.v1'
         and source.get('scope')=='ACTUAL_SOURCE_RUNTIME_STARTUP_RECOVERY_QUALIFIED'
         and re.fullmatch('[a-f0-9]{40}',str(source.get('source_sha','')))
         and all(profile.SHA.fullmatch(str(source.get(k,''))) for k in ['runtime_sha256','source_files_sha256','startup_receipt_sha256','recovery_receipt_sha256'])
         and source.get('descriptor_sha256')==profile.DESCRIPTOR and source.get('package_version')==profile.PACKAGE
         and source.get('private_stage_validated') is True and source.get('original120_unchanged') is True,
         'ACTUAL_QUALIFIED_CURRENT_SERVING_SOURCE_REQUIRED')
    observation_time(source['observed_at'],'FRESH_SERVING_SOURCE_REQUIRED')
    need(execution.get('schema')=='earnalism.sredni_initial_review_actual_execution.v1'
         and execution.get('owner_receipt_sha256')==b['owner']['sha256']
         and execution.get('source_receipt_sha256')==b['source']['sha256']
         and execution.get('identity_receipt_sha256')==b['identity']['sha256']
         and execution.get('identity_binding_sha256')==bound
         and all(profile.SHA.fullmatch(str(execution.get(k,''))) for k in ['mongo_profile_sha256','database_name_sha256','source_files_sha256'])
         and execution['source_files_sha256']==source['source_files_sha256']
         and execution.get('db_access_scope')=='SREDNI_OWN_MEMBER_METADATA_ONLY'
         and execution.get('uri_or_secrets_in_output') is False,'SEPARATE_EXACT_PRIVATE_EXECUTION_AUTHORITY_REQUIRED')
    observation_time(execution['observed_at'],'FRESH_EXECUTION_CONTEXT_REQUIRED')
    if b['action']=='observe':need(b['expected_state_sha256'] is None,'INITIAL_OBSERVATION_CANNOT_CLAIM_EXPECTED_STATE')
    else:need(profile.SHA.fullmatch(str(b['expected_state_sha256'])) and b['expected_state_sha256']!='0'*64,'ACTUAL_EXPECTED_STATE_REQUIRED')
    need(intent.get('schema')=='earnalism.sredni_initial_review_intent.v1'
         and intent.get('operation_id')==b['operation_id'] and intent.get('action')==b['action']
         and intent.get('owner_receipt_sha256')==b['owner']['sha256']
         and intent.get('expected_state_sha256')==b['expected_state_sha256']
         and intent.get('journal')==b['journal'],'EXACT_PRIOR_INTENT_REQUIRED')
    try:files.qualify_journal(b['journal'])
    except Exception:raise AdmissionStop('EXACT_PRIVATE_JOURNAL_PATH_DEVICE_INODE_REQUIRED') from None
    expires=utc(b['expires_at']);grant_expires=utc(b['grant_expires_at'])
    need(expires<=now+timedelta(minutes=15) and grant_expires<=expires,'FINITE_REVIEW_WINDOW_REQUIRED')
    if not allow_expired_status and b['action']!='close':
        need(now<grant_expires<=now+timedelta(minutes=15),'CURRENT_FINITE_REVIEW_GRANT_WINDOW_REQUIRED')
    if b['action']=='close':need(isinstance(b['grant_id'],str) and b['grant_id'],'EXACT_GRANT_CLOSE_TARGET_REQUIRED')
    else:need(b['grant_id']=='','INITIAL_PROVISION_DOES_NOT_ACCEPT_CALLER_GRANT_ID')
    a=AdmittedOperation(b['operation_id'],b['action'],b['user_id'],b['auth_session_id'],b['owner']['sha256'],bound,
        b['identity']['sha256'],b['execution']['sha256'],expected_sha256,b['intent']['sha256'],b['expected_state_sha256'],
        expires,grant_expires,b['grant_id'],b['journal'])
    try:
        from .sredni_initial_review_scope import authority_allows
    except ImportError:
        from sredni_initial_review_scope import authority_allows
    need(authority_allows({'user_id':a.user_id,'auth_session_id':a.auth_session_id,
         'owner_receipt_sha256':a.owner_receipt_sha256,'identity_binding_sha256':a.identity_binding_sha256}),
         'SOURCE_ACCEPTED_ACTUAL_OWNER_MEMBER_PAIR_REQUIRED')
    if not allow_expired_status:current(a,now)
    return a,b,receipts
