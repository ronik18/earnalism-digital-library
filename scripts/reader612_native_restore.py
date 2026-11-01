"""Source-only admission/restore extension of the existing durable provider adapter.

No CLI entry point. Execution defaults false. External authentic protected gate
and exact source/native observers are mandatory; this module issues no approvals.
"""
from datetime import datetime,timezone,timedelta
from pathlib import Path
import hashlib,json,re,os,stat,subprocess
from scripts.india_release_provider_adapter import (digest,_durable_json,_read_journal,
 _sync_directory,ProviderAdapter,RAILWAY_PROJECT,SERVICE,ENVIRONMENT,process_diagnostic)
ACTION='restore_original_native_after_reader612_qualification'
ROLE='prior_reader_regression_recovery'
HASH=re.compile(r'^[a-f0-9]{64}$');GIT=re.compile(r'^[a-f0-9]{40}$');UUID=re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')
CANONICAL_JOURNAL=Path('/Users/ronikbasak/Documents/Earnalism/release-evidence/optimization-20261030/operations')
DIGEST_FIELDS=('payload_sha256','runtime_sha256','manifest_sha256','config_sha256','baseline_runtime_sha256','controller_sha256','support_sha256','journal_identity_sha256')
FIELDS={'source_sha','tree_sha','baseline_source_sha','role','project','service','environment','baseline_deployment_id','baseline_image','baseline_snapshot','current_deployment_id',*DIGEST_FIELDS}
def need(ok,message):
 if not ok:raise ValueError(message)
def now_utc():return datetime.now(timezone.utc)
def journal_identity(journal):
 journal=Path(journal)
 need(journal.is_absolute() and journal==CANONICAL_JOURNAL and journal.resolve()==journal,'Canonical admitted operations namespace required')
 rows=[]
 for p in (journal.parent,journal):
  s=p.lstat();need(stat.S_ISDIR(s.st_mode) and s.st_uid==os.getuid() and not stat.S_IMODE(s.st_mode)&0o022,'Existing private owner-matched journal required')
  rows.append({'path':str(p),'device':s.st_dev,'inode':s.st_ino,'uid':s.st_uid,'mode':stat.S_IMODE(s.st_mode)})
 return digest(rows)
def support_identity():
 root=Path(__file__).resolve().parent
 names=('india_release_provider_adapter.py','reader612_recovery_source.py','reader612_native_observer.py','reader612_protected_approval.py','india_release_observer.py','india_protected_runner.py','backend_upload_payload.py','purchase_guard_source.py','build_runtime_source_manifest.py','qualify_stable_rollback_profile.py','reader612_phase_bridge.py','reader612_phase_collectors.py')
 rows={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}
 rows['acceptance_contract']=digest(json.loads((root.parent/'internal/release/reader612_phase_acceptance.json').read_text()))
 rows['approval_workflow']=hashlib.sha256((root.parent/'.github/workflows/reader612-protected-approval.yml').read_bytes()).hexdigest()
 return digest(rows)
def qualify_controller_preparation(binding):
 root=Path(__file__).resolve().parent
 need(binding.get('execution_authorized') is False and binding.get('native_qualified') is False,'Preparation cannot authorize execution')
 expected={'reader612_native_restore.py','reader612_recovery_source.py','reader612_native_observer.py','reader612_protected_approval.py','india_release_observer.py','india_protected_runner.py','india_release_provider_adapter.py','backend_upload_payload.py','purchase_guard_source.py','build_runtime_source_manifest.py','qualify_stable_rollback_profile.py','reader612_phase_bridge.py','reader612_phase_collectors.py'}
 files=binding.get('controller_files',{})
 need(set(files)==expected,'Exact controller dependency inventory required')
 for name,h in files.items():need(h==hashlib.sha256((root/name).read_bytes()).hexdigest(),'Controller dependency mismatch: '+name)
 need(binding.get('approval_workflow_sha256')==hashlib.sha256((root.parent/'.github/workflows/reader612-protected-approval.yml').read_bytes()).hexdigest(),'Approval workflow source mismatch')
 need(binding.get('acceptance_contract_sha256')==digest(json.loads((root.parent/'internal/release/reader612_phase_acceptance.json').read_text())),'Reviewed acceptance contract mismatch')
 return {'result':'PASS_OFFLINE_CONTROLLER_SOURCE_BINDING_ONLY','native_qualified':False,'execution_authorized':False,'authentic_gate_integration':'SOURCE_BOUND_GITHUB_PROTECTED_REVIEW_RESOLVER_NO_CURRENT_APPROVAL','actual_native_observer_transport':'NOT_EXECUTED'}
def validate_binding(b):
 need(isinstance(b,dict) and set(b)==FIELDS,'Exact complete binding required')
 need(b['role']==ROLE,'Only reviewed prior Reader role admitted')
 need((b['project'],b['service'],b['environment'])==(RAILWAY_PROJECT,SERVICE,ENVIRONMENT),'Existing exact target required')
 for k in DIGEST_FIELDS:need(isinstance(b[k],str) and HASH.fullmatch(b[k]) and b[k]!='0'*64,'Unbound digest: '+k)
 for k in ('source_sha','tree_sha','baseline_source_sha'):need(isinstance(b[k],str) and GIT.fullmatch(b[k]),'Immutable Git identity required: '+k)
 for k in ('baseline_deployment_id','baseline_snapshot','current_deployment_id'):need(isinstance(b[k],str) and UUID.fullmatch(b[k]),'Exact native identity required: '+k)
 need(re.fullmatch(r'sha256:[a-f0-9]{64}',b['baseline_image'] or ''),'Exact original retained image required')
 need(b['controller_sha256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'Controller source mismatch')
 need(b['support_sha256']==support_identity(),'Qualifier/adapter source mismatch')
 need(b['journal_identity_sha256']==journal_identity(CANONICAL_JOURNAL),'Canonical journal identity changed')
def fresh(value,now):
 t=datetime.fromisoformat(value);need(t.tzinfo is not None and timedelta(0)<=now-t<=timedelta(minutes=15),'Observation stale/future/naive');return t
def admit(binding,approval_reference,*,action=ACTION,protected_gate=None,source_observer=None,clock=now_utc):
 """Both callbacks are trusted integration dependencies, never local proof booleans."""
 need(action in {ACTION,'release_guarded_bootstrap'},'Unsupported operation');validate_binding(binding);need(callable(protected_gate) and callable(source_observer),'Authentic gate and exact source observer unbound')
 now=clock();need(now.tzinfo is not None,'Aware clock required');bd=digest(binding)
 proof=source_observer(binding)
 need(proof.get('scope')=='ACTUAL_IMMUTABLE_SOURCE_AND_NATIVE_BASELINE' and proof.get('binding_sha256')==bd,'Exact source/payload/baseline proof required')
 fresh(proof['observed_at'],now)
 for k in ('source_tree_payload_verified','baseline_image_snapshot_config_verified','auto_deploy_off','all_effective_redis_flags_off','current_healthy','no_staged_changes'):need(proof.get(k) is True,'Unqualified actual observation: '+k)
 if action==ACTION:
  need(HASH.fullmatch(proof.get('qualified_native_receipt_sha256','')) and proof.get('current_runtime_sha256')==binding['runtime_sha256'] and proof.get('current_deployment_id')==binding['current_deployment_id'] and proof.get('baseline_can_rollback') is True,'Actual qualified role and retained baseline restoration proof required')
 # Reference is resolved by an authenticated external owner/platform channel.
 # A supplied approved=True dictionary is not consulted or accepted here.
 need(isinstance(approval_reference,str) and HASH.fullmatch(approval_reference),'Authentic approval receipt reference required')
 gate=protected_gate(approval_reference,action,bd)
 need(gate.get('issuer')=='AUTHENTIC_NATIVE_OWNER_PROTECTED_GATE' and gate.get('receipt_sha256')==approval_reference and gate.get('binding_sha256')==bd and gate.get('action')==action,'Unbound authentic protected operation')
 need(gate.get('native_turn_id') and gate.get('scope')=='BACKEND612_QUALIFICATION_PAUSE_AND_EXACT_BASELINE_RESTORE','Frontend-only/historical authority insufficient')
 need(isinstance(gate.get('rollback_operator'),str) and bool(gate['rollback_operator'].strip()),'Named rollback operator required')
 issued=fresh(gate['issued_at'],now);expires=datetime.fromisoformat(gate['expires_at'])
 need(expires.tzinfo is not None and issued<=now<expires<=issued+timedelta(minutes=15),'Expired/overlong protected operation')
 need(issued>=datetime(2026,11,1,tzinfo=timezone.utc),'Historical authority is not current permission')
 return {'binding_sha256':bd,'authority_receipt_sha256':approval_reference,'observed_proof_sha256':digest(proof)}
def rollback_document(schema,baseline_id):
 need(schema=={'name':'deploymentRollback','argument':{'name':'id','type':'String!'},'return':'Boolean!'},'Actual native scalar schema required')
 need(UUID.fullmatch(baseline_id or ''),'Exact original deployment ID required')
 return 'mutation { deploymentRollback(id:"'+baseline_id+'") }'
def _prepare_journal(journal):
 journal_identity(journal);_sync_directory(journal.parent)
 need(not (journal/'_write-barrier.json').exists(),'Unknown previous write; read-only reconciliation required')
 for f in journal.glob('*.json'):
  if not f.name.endswith('.request.json'):need(_read_journal(f).get('state') in {'APPLIED_VERIFIED','NOT_APPLIED_VERIFIED'},'Unreconciled journal')
def perform_restore(binding,approval_reference,journal,schema,*,execution_enabled=False,protected_gate=None,source_observer=None,transport=None,clock=now_utc):
 need(execution_enabled is True,'Backend execution disabled by default')
 need(journal_identity(journal)==binding['journal_identity_sha256'],'Canonical journal identity changed')
 need(callable(transport),'Native transport not integrated; no implicit CLI execution')
 admission=admit(binding,approval_reference,protected_gate=protected_gate,source_observer=source_observer,clock=clock)
 query=rollback_document(schema,binding['baseline_deployment_id']);journal=Path(journal);_prepare_journal(journal)
 # Approval/paths cannot create a replay identity for the same semantic restore.
 op=digest({'action':ACTION,'project':RAILWAY_PROJECT,'service':SERVICE,'environment':ENVIRONMENT,'baseline_deployment':binding['baseline_deployment_id'],'qualified_source':binding['source_sha']})
 need(not (journal/(op+'.json')).exists(),'Permanent operation exists; no replay')
 record={'operation_id':op,'action':ACTION,'binding':binding,'admission':admission,'started_at':clock().isoformat(),'state':'INTENT_RECONCILE_BEFORE_RETRY'}
 _durable_json(journal/'_write-barrier.json',{'operation_id':op,'state':'INTENT_RECONCILE_BEFORE_RETRY'},exclusive=True)
 _durable_json(journal/(op+'.json'),record,exclusive=True)
 request={'argv':['railway','api',query,'--compact'],'schema_sha256':digest(schema),'exact_original_native_target':binding['baseline_deployment_id'],'binding_sha256':digest(binding)}
 _durable_json(journal/(op+'.request.json'),request,exclusive=True)
 try:
  # Transport receives only fixed reviewed argv. It must not log raw stdout.
  result=transport(request['argv'],timeout=60)
  record.update(process_exit_code=result.returncode,process_diagnostic=process_diagnostic(result))
 except Exception as e:record.update(process_exit_code=None,process_diagnostic=process_diagnostic(error=e))
 record['state']='WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED';_durable_json(journal/(op+'.json'),record);return record

def reconcile_restore(journal,operation_id,*,observer=None):
 """Existing adapter supplies exclusive reconciliation + durable state/barrier order."""
 need(callable(observer),'Actual read-only observer required')
 journal_identity(journal)
 def collect(action,record):
  actual=observer(action,record);b=record['binding'];need(record['action']==ACTION,'Wrong restore action')
  need(b['journal_identity_sha256']==journal_identity(journal),'Canonical journal identity changed')
  if actual.get('outcome')=='APPLIED':
   for k,key in [('restored_image','baseline_image'),('restored_source_sha','baseline_source_sha'),('restored_runtime_sha256','baseline_runtime_sha256'),('restored_config_sha256','config_sha256')]:need(actual.get(k)==b[key],'Actual restored binding mismatch: '+k)
   for k in ('startup_database_healthy','redis_auto_deploy_off','public_protected_acceptance','qualified_recovery_image_retained'):need(actual.get(k) is True,'Actual acceptance missing: '+k)
   need(UUID.fullmatch(actual.get('deployment_id','')),'Actual native deployment required')
  elif actual.get('outcome')=='NOT_APPLIED':
   need(actual.get('current_deployment_id')==b['current_deployment_id'] and actual.get('proof_kind')=='DETERMINISTIC_REJECTION_AND_ACTUAL_NATIVE_NO_EFFECT' and HASH.fullmatch(actual.get('no_effect_proof_sha256','')),'Actual no-effect proof required')
  else:raise ValueError('Unknown outcome; barrier retained')
  return actual
 return ProviderAdapter(Path(journal),observe=collect).reconcile(operation_id)


def admit_qualification(binding,approval_reference,*,execution_enabled=False,protected_gate=None,source_observer=None,clock=now_utc):
 """No new deployment framework: gate then existing release_guarded_bootstrap adapter.

 Integration must pass its exact normal provider binding and protected approval
 to existing ReleaseController/ProviderAdapter; this does not mint those values.
 """
 need(execution_enabled is True,'Backend execution disabled by default')
 return admit(binding,approval_reference,action='release_guarded_bootstrap',protected_gate=protected_gate,source_observer=source_observer,clock=clock)
