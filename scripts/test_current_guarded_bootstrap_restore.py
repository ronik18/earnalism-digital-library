import unittest,importlib.util,sys,pathlib,tempfile,json,copy,hashlib
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
P=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('candidate_adapter',P/'india_release_provider_adapter.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
NOW=datetime(2026,11,3,18,tzinfo=timezone.utc)
SCHEMA={'name':'deploymentRollback','argument':{'name':'id','type':'String!'},'return':'Boolean!'}
def fixture(folder):
 bootbinding={'source_sha':'a'*40,'config_sha256':'1'*64,'source_delivery_sha256':'2'*64,'closed_server_sha256':'3'*64}
 boot={'action':'release_guarded_bootstrap','binding':bootbinding,'state':'APPLIED_VERIFIED','reconciliation_receipt_sha256':'4'*64,'guarded_recovery_receipt_sha256':'5'*64,'started_at':(NOW-timedelta(hours=1)).isoformat()};boot['operation_id']=a.operation_identity(boot['action'],bootbinding)
 normalbinding={'source_sha':'b'*40,'guarded_recovery_receipt_sha256':'5'*64}
 normal={'action':'release_backend','binding':normalbinding,'state':'APPLIED_VERIFIED','reconciliation_receipt_sha256':'6'*64,'started_at':NOW.isoformat()};normal['operation_id']=a.operation_identity(normal['action'],normalbinding)
 for r in [boot,normal]:
  p=folder/(r['operation_id']+'.json');p.write_text(json.dumps(r));p.chmod(0o600)
 failure={'scope':'ACTUAL_APPLIED_NORMAL_FAILURE','operation_id':normal['operation_id'],'normal_reconciliation_receipt_sha256':'6'*64,'deployment_id':'22222222-2222-4222-8222-222222222222','source_sha':'b'*40,'project':a.RAILWAY_PROJECT,'service':a.SERVICE,'environment':a.ENVIRONMENT}
 c={'applied_normal_operation_id':normal['operation_id'],'applied_normal_record_sha256':a.digest(normal),'applied_normal_reconciliation_receipt_sha256':'6'*64,'bootstrap_operation_id':boot['operation_id'],'bootstrap_record_sha256':a.digest(boot),'guarded_recovery_receipt_sha256':'5'*64,'target_deployment_id':'11111111-1111-4111-8111-111111111111','target_retained_image_id':'sha256:'+'7'*64,'target_runtime_sha256':'2'*64,'target_config_sha256':'1'*64,'target_source_sha':'a'*40,'current_bad_normal_deployment_id':failure['deployment_id'],'bad_normal_failure_receipt_sha256':a.digest(failure),'actual_native_schema_sha256':a.digest(SCHEMA)}
 proof={'scope':'ACTUAL_PROVIDER_AND_SOURCE','action':'release_guarded_bootstrap',**bootbinding,'deployment_id':c['target_deployment_id'],'retained_image_id':c['target_retained_image_id'],'runtime_sha256':'2'*64,'recovery_receipt_sha256':'5'*64,'guarded_backend_deployment_id':c['target_deployment_id'],'closed_guest_status':503,'purchase_pause_proof':'MEASURED_EXACT_EARLY_RETURN_AND_ANONYMOUS_503'}
 for k in ['startup_complete','database_healthy','source_attestation_matches','native_can_rollback','config_compatible','existing_reader_listener_preserved','verify_refund_webhook_code_preserved']:proof[k]=True
 actual={'config_sha256':'1'*64,'startup_data_qualification':{'config_sha256':'1'*64},'native_rollback_schema':SCHEMA,'qualified_bootstrap_receipt':proof,'native_restore_available':True,'installed_policy_compatible':True,'known_normal_failure_qualified':True,'current_bad_normal_deployment_id':c['current_bad_normal_deployment_id'],'bad_normal_failure_receipt_sha256':c['bad_normal_failure_receipt_sha256'],'bad_normal_failure_receipt':failure,'applied_normal_source_sha':'b'*40,'guarded_restore_sha256':a.digest(c)}
 binding={'source_sha':'a'*40,'source_root':str(ROOT),'source_delivery_sha256':'2'*64,'config_sha256':'1'*64,'closed_server_sha256':'3'*64,'applied_normal_operation_id':normal['operation_id'],'restore_context':c,'native_rollback_schema':SCHEMA}
 custody=a._operation_journal_identity(folder)
 c['operations_journal_identity_sha256']=custody
 boot['operations_journal_identity_sha256']=custody
 normal['operations_journal_identity_sha256']=custody
 boot['qualified_bootstrap_evidence']=proof
 normal['provider_backend_deployment_id']=c['current_bad_normal_deployment_id']
 for record in [boot,normal]:
  path=folder/(record['operation_id']+'.json');path.write_text(json.dumps(record));path.chmod(0o600)
 c['bootstrap_record_sha256']=a.digest(boot);c['applied_normal_record_sha256']=a.digest(normal)
 actual['guarded_restore_sha256']=a.digest(c)
 actual['retained_bootstrap_native']={'deployment_id':c['target_deployment_id'],'retained_image_id':c['target_retained_image_id'],'runtime_sha256':c['target_runtime_sha256'],'config_sha256':c['target_config_sha256'],'source_sha':c['target_source_sha'],'native_can_rollback':True}
 return binding,actual,boot,normal
class Restore(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  # The journal and its parent must both be private, including on Linux /tmp.
  self.root=pathlib.Path(self.tmp.name)/'operations';self.root.mkdir(mode=0o700)
  self.b,self.actual,self.boot,self.normal=fixture(self.root)
 def tearDown(self):self.tmp.cleanup()
 def test_ordinary_identity_unchanged(self):
  b={'source_sha':'b'*40};expected={'action':'release_backend','source_sha':b['source_sha'],'candidate':None,'project':a.RAILWAY_PROJECT,'service':a.SERVICE,'environment':a.ENVIRONMENT};self.assertEqual(a.operation_identity('release_backend',b),a.digest(expected))
 def test_valid_exact_lineage_and_scalar_only_command(self):
  self.assertEqual(a.validate_guarded_restore_context(self.root,self.b,self.actual),self.b['restore_context']);cmd=a.ProviderAdapter(self.root)._command('restore_guarded_bootstrap',self.b,None);self.assertEqual(cmd,['railway','api','mutation { deploymentRollback(id:"11111111-1111-4111-8111-111111111111") }','--compact']);self.assertNotIn('up',cmd)
 def test_default_disabled(self):
  with self.assertRaisesRegex(ValueError,'prohibits'):a.ProviderAdapter(self.root).perform('restore_guarded_bootstrap',self.b,{})
 def test_same_normal_identity_not_reset_by_target_path_or_approval(self):
  old=a.operation_identity('restore_guarded_bootstrap',self.b)
  for key,value in [('source_sha','c'*40),('source_root','/other'),('restore_context',{})]:
   changed={**self.b,key:value};self.assertEqual(a.operation_identity('restore_guarded_bootstrap',changed),old)
 def test_wrong_context_and_actual_proofs_denied(self):
  for key in a.RESTORE_FIELDS:
   with self.subTest(key=key):
    b=copy.deepcopy(self.b);b['restore_context'][key]='9'*64
    with self.assertRaises((ValueError,TypeError)):a.validate_guarded_restore_context(self.root,b,self.actual)
  for key in ['native_restore_available','installed_policy_compatible','known_normal_failure_qualified']:
   actual={**self.actual,key:False}
   with self.assertRaises(ValueError):a.validate_guarded_restore_context(self.root,self.b,actual)
 def test_unknown_or_notapplied_normal_rejected(self):
  for state in ['NOT_APPLIED_VERIFIED','WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED']:
   changed={**self.normal,'state':state};(self.root/(changed['operation_id']+'.json')).write_text(json.dumps(changed));b=copy.deepcopy(self.b);b['restore_context']['applied_normal_record_sha256']=a.digest(changed)
   with self.assertRaises(ValueError):a.validate_guarded_restore_context(self.root,b,self.actual)
 def test_bootstrap_receipt_not_boolean(self):
  for field in ['database_healthy','startup_complete','source_attestation_matches','native_can_rollback','existing_reader_listener_preserved','verify_refund_webhook_code_preserved']:
   actual=copy.deepcopy(self.actual);actual['qualified_bootstrap_receipt'][field]=False
   with self.assertRaises(ValueError):a.validate_guarded_restore_context(self.root,self.b,actual)
 def test_query_schema_and_unknown_action_failclosed(self):
  adapter=a.ProviderAdapter(self.root)
  with self.assertRaises(ValueError):adapter._command('arbitrary',self.b,None)
  for schema in [{}, {**SCHEMA,'return':'Deployment!'}]:
   with self.assertRaises(ValueError):adapter._command('restore_guarded_bootstrap',{**self.b,'native_rollback_schema':schema},None)
 def test_reconcile_missing_actual_keeps_barrier(self):
  op=a.operation_identity('restore_guarded_bootstrap',self.b);record={'operation_id':op,'action':'restore_guarded_bootstrap','binding':self.b,'state':'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED'};(self.root/(op+'.json')).write_text(json.dumps(record));(self.root/(op+'.json')).chmod(0o600);(self.root/'_write-barrier.json').write_text(json.dumps({'operation_id':op,'state':'INTENT_RECONCILE_BEFORE_RETRY'}));(self.root/'_write-barrier.json').chmod(0o600);adapter=a.ProviderAdapter(self.root,observe=lambda *_:{'outcome':'APPLIED'})
  with self.assertRaises(ValueError):adapter._reconcile_locked(op)
  self.assertTrue((self.root/'_write-barrier.json').exists())
 def test_reconciliation_wrong_image_even_boolean_true_denied(self):
  op=a.operation_identity('restore_guarded_bootstrap',self.b);record={'operation_id':op,'action':'restore_guarded_bootstrap','binding':self.b,'state':'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED'};(self.root/(op+'.json')).write_text(json.dumps(record));(self.root/(op+'.json')).chmod(0o600);(self.root/'_write-barrier.json').write_text(json.dumps({'operation_id':op,'state':'INTENT_RECONCILE_BEFORE_RETRY'}));(self.root/'_write-barrier.json').chmod(0o600);actual={**self.actual,'scope':'ACTUAL_PROVIDER_AND_SOURCE','operation_id':op,'action':'restore_guarded_bootstrap','source_sha':'a'*40,'outcome':'APPLIED','receipt_sha256':'9'*64,'deployment_id':'new','restored_from_deployment_id':self.b['restore_context']['target_deployment_id'],'retained_image_id':'WRONG'}
  with self.assertRaises(ValueError):a.ProviderAdapter(self.root,observe=lambda *_:actual)._reconcile_locked(op)
  self.assertTrue((self.root/'_write-barrier.json').exists())
 def run_admitted(self, run):
  # Admission validators are separately tested; this fixture isolates durable
  # ordering/process UNKNOWN semantics without fabricating an actual receipt.
  self.b['controller_source_sha']='c'*40
  self.actual.update(scope='ACTUAL_PROVIDER_AND_SOURCE',qualified=True,auto_deploy=False,
   authenticated_provider_account=True,cli_version=a.CLI_VERSIONS['railway'],
   provider_identity_sha256='d'*64,config_sha256='1'*64,controller_source_sha='c'*40)
  approval={'provider_identity_sha256':'d'*64,'config_sha256':'1'*64,
   'guarded_restore_sha256':self.actual['guarded_restore_sha256']}
  with patch.object(a,'validate_approval'),patch('scripts.startup_dispatch_qualification.validate_startup_qualification'),patch.object(a.subprocess,'check_output',side_effect=['c'*40,'']):
   return a.ProviderAdapter(self.root,owner_authorized=True,observe=lambda *_:self.actual,run=run,clock=lambda:NOW).perform('restore_guarded_bootstrap',self.b,approval)
 def test_durable_request_before_single_native_dispatch_timeout_keeps_barrier(self):
  calls=[]
  def timeout(command,**kw):
   calls.append(command);op=a.operation_identity('restore_guarded_bootstrap',self.b)
   self.assertTrue((self.root/(op+'.json')).exists());self.assertTrue((self.root/(op+'.request.json')).exists());self.assertTrue((self.root/'_write-barrier.json').exists())
   raise TimeoutError('synthetic no provider')
  result=self.run_admitted(timeout)
  self.assertEqual(len(calls),1);self.assertEqual(result['state'],'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED')
  self.assertTrue((self.root/'_write-barrier.json').exists())
  with self.assertRaises(FileExistsError):self.run_admitted(timeout)
  self.assertEqual(len(calls),1)
 def test_durable_failure_before_dispatch_never_calls_transport(self):
  calls=[];real=a._durable_json
  def fail(path,value,**kwargs):
   if str(path).endswith('.request.json'):raise OSError('synthetic request fsync')
   return real(path,value,**kwargs)
  with patch.object(a,'_durable_json',side_effect=fail):
   with self.assertRaises(OSError):self.run_admitted(lambda *args,**kw:calls.append(args))
  self.assertEqual(calls,[]);self.assertTrue((self.root/'_write-barrier.json').exists())
 def test_notapplied_permanent_root_cannot_issue_second_return(self):
  op=a.operation_identity('restore_guarded_bootstrap',self.b);record={'operation_id':op,'action':'restore_guarded_bootstrap','binding':self.b,'state':'NOT_APPLIED_VERIFIED'}
  p=self.root/(op+'.json');p.write_text(json.dumps(record));p.chmod(0o600)
  with self.assertRaises(FileExistsError):self.run_admitted(lambda *_:self.fail('REPLAY'))
 def test_applied_restore_measured_bytes_and_new_identity_required(self):
  op=a.operation_identity('restore_guarded_bootstrap',self.b)
  record={'operation_id':op,'action':'restore_guarded_bootstrap','binding':self.b,'state':'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED'}
  p=self.root/(op+'.json');p.write_text(json.dumps(record));p.chmod(0o600)
  barrier=self.root/'_write-barrier.json';barrier.write_text(json.dumps({'operation_id':op,'state':'INTENT_RECONCILE_BEFORE_RETRY'}));barrier.chmod(0o600)
  actual={**self.actual,**self.actual['qualified_bootstrap_receipt'],'operation_id':op,'action':'restore_guarded_bootstrap','source_sha':'a'*40,'outcome':'APPLIED','receipt_sha256':'9'*64,'deployment_id':'33333333-3333-4333-8333-333333333333','guarded_backend_deployment_id':'33333333-3333-4333-8333-333333333333','restored_from_deployment_id':self.b['restore_context']['target_deployment_id']}
  for key in ['auto_deploy','redis_enabled','redis_cache_enabled','multi_replica_enabled','redis_public_metadata_enabled']:actual[key]=False
  result=a.ProviderAdapter(self.root,observe=lambda *_:actual)._reconcile_locked(op)
  self.assertEqual(result['state'],'APPLIED_VERIFIED');self.assertFalse(barrier.exists());self.assertTrue(p.exists())
 def test_notapplied_requires_actual_noeffect_not_process_boolean(self):
  op=a.operation_identity('restore_guarded_bootstrap',self.b)
  p=self.root/(op+'.json');p.write_text(json.dumps({'operation_id':op,'action':'restore_guarded_bootstrap','binding':self.b,'state':'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED'}));p.chmod(0o600)
  barrier=self.root/'_write-barrier.json';barrier.write_text(json.dumps({'operation_id':op,'state':'INTENT_RECONCILE_BEFORE_RETRY'}));barrier.chmod(0o600)
  actual={'scope':'ACTUAL_PROVIDER_AND_SOURCE','operation_id':op,'action':'restore_guarded_bootstrap','source_sha':'a'*40,'outcome':'NOT_APPLIED','receipt_sha256':'9'*64}
  adapter=a.ProviderAdapter(self.root,observe=lambda *_:actual)
  with self.assertRaises(ValueError):adapter._reconcile_locked(op)
  self.assertTrue(barrier.exists())
  actual['native_no_effect_proof']={'scope':'ACTUAL_NATIVE_RESTORE_NOT_APPLIED','operation_id':op,'current_deployment_id':self.b['restore_context']['current_bad_normal_deployment_id'],'no_new_native_deployment_observed':True,'exact_request_not_applied':True}
  self.assertEqual(adapter._reconcile_locked(op)['state'],'NOT_APPLIED_VERIFIED');self.assertTrue(p.exists())
 def test_old_digest_only_or_normal_missing_native_identity_cannot_authorize_restore(self):
  for record,key in [(self.boot,'qualified_bootstrap_evidence'),(self.normal,'provider_backend_deployment_id')]:
   old=copy.deepcopy(record);old.pop(key);p=self.root/(old['operation_id']+'.json');p.write_text(json.dumps(old));p.chmod(0o600)
   b=copy.deepcopy(self.b);field='bootstrap_record_sha256' if record is self.boot else 'applied_normal_record_sha256';b['restore_context'][field]=a.digest(old)
   with self.assertRaises(ValueError):a.validate_guarded_restore_context(self.root,b,self.actual)
   p.write_text(json.dumps(record))
 def test_retained_native_and_normal_failure_reconciliation_binding_are_required(self):
  for key in ['retained_bootstrap_native','bad_normal_failure_receipt']:
   actual=copy.deepcopy(self.actual)
   if key=='retained_bootstrap_native':actual[key]['retained_image_id']='WRONG'
   else:actual[key]['normal_reconciliation_receipt_sha256']='f'*64
   with self.assertRaises(ValueError):a.validate_guarded_restore_context(self.root,self.b,actual)
 def test_config_chain_requires_binding_actual_startup_and_approval_equal_target(self):
  for role in ['binding','actual','startup','approval']:
   b=copy.deepcopy(self.b);actual=copy.deepcopy(self.actual);approval={'config_sha256':'1'*64}
   if role=='binding':b['config_sha256']='9'*64
   elif role=='actual':actual['config_sha256']='9'*64
   elif role=='startup':actual['startup_data_qualification']['config_sha256']='9'*64
   else:approval['config_sha256']='9'*64
   with self.subTest(role=role),self.assertRaises(ValueError):a.validate_guarded_restore_context(self.root,b,actual,approval)
  b=copy.deepcopy(self.b);actual=copy.deepcopy(self.actual)
  b['config_sha256']=actual['config_sha256']=actual['startup_data_qualification']['config_sha256']='9'*64
  with self.assertRaises(ValueError):a.validate_guarded_restore_context(self.root,b,actual,{'config_sha256':'9'*64})
 def test_runtime_contradiction_with_correct_record_digests_denied(self):
  b=copy.deepcopy(self.b);actual=copy.deepcopy(self.actual);boot=copy.deepcopy(self.boot)
  boot['qualified_bootstrap_evidence']['runtime_sha256']='9'*64
  (self.root/(boot['operation_id']+'.json')).write_text(json.dumps(boot))
  b['restore_context']['bootstrap_record_sha256']=a.digest(boot)
  b['restore_context']['target_runtime_sha256']=b['source_delivery_sha256']='9'*64
  actual['qualified_bootstrap_receipt']=boot['qualified_bootstrap_evidence']
  actual['retained_bootstrap_native']['runtime_sha256']='9'*64
  actual['guarded_restore_sha256']=a.digest(b['restore_context'])
  with self.assertRaisesRegex(ValueError,'runtime'):a.validate_guarded_restore_context(self.root,b,actual)
 def test_admitted_closed_hash_cannot_differ_before_dispatch(self):
  b={**self.b,'closed_server_sha256':'9'*64}
  with self.assertRaisesRegex(ValueError,'CLOSED'):a.validate_guarded_restore_context(self.root,b,self.actual)
 def test_restored_arbitrary_nonempty_native_label_denied(self):
  op=a.operation_identity('restore_guarded_bootstrap',self.b);p=self.root/(op+'.json')
  p.write_text(json.dumps({'operation_id':op,'action':'restore_guarded_bootstrap','binding':self.b,'state':'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED'}));p.chmod(0o600)
  barrier=self.root/'_write-barrier.json';barrier.write_text(json.dumps({'operation_id':op,'state':'INTENT_RECONCILE_BEFORE_RETRY'}));barrier.chmod(0o600)
  actual={**self.actual,**self.actual['qualified_bootstrap_receipt'],'operation_id':op,'action':'restore_guarded_bootstrap','source_sha':'a'*40,'outcome':'APPLIED','receipt_sha256':'9'*64,'deployment_id':'arbitrary-label','guarded_backend_deployment_id':'arbitrary-label','restored_from_deployment_id':self.b['restore_context']['target_deployment_id']}
  with self.assertRaisesRegex(ValueError,'identity'):a.ProviderAdapter(self.root,observe=lambda *_:actual)._reconcile_locked(op)
  self.assertTrue(barrier.exists())
 def test_copied_predecessors_cannot_reset_journal_namespace(self):
  other=self.root/'another-admitted-journal';other.mkdir(mode=0o700)
  for record in [self.boot,self.normal]:
   path=other/(record['operation_id']+'.json');path.write_text(json.dumps(record));path.chmod(0o600)
  with self.assertRaisesRegex(ValueError,'custody'):a.validate_guarded_restore_context(other,self.b,self.actual)
 def test_old_receipts_without_physical_custody_are_not_new_restore_authority(self):
  for record in [self.boot,self.normal]:
   record.pop('operations_journal_identity_sha256');path=self.root/(record['operation_id']+'.json');path.write_text(json.dumps(record));path.chmod(0o600)
  self.b['restore_context']['applied_normal_record_sha256']=a.digest(self.normal)
  self.b['restore_context']['bootstrap_record_sha256']=a.digest(self.boot)
  with self.assertRaisesRegex(ValueError,'custody'):a.validate_guarded_restore_context(self.root,self.b,self.actual)
 def test_custody_rejects_symlink_relative_and_public_directories(self):
  link=self.root/'alias';link.symlink_to(self.root,target_is_directory=True)
  for path in [link,pathlib.Path('relative')]:
   with self.subTest(path=path),self.assertRaises(ValueError):a._operation_journal_identity(path)
  self.root.chmod(0o777)
  try:
   with self.assertRaises(ValueError):a._operation_journal_identity(self.root)
  finally:self.root.chmod(0o700)
 def test_shared_parent_rejected_before_transport(self):
  calls=[];parent=self.root.parent;parent.chmod(0o1777)
  try:
   with self.assertRaisesRegex(ValueError,'Private owner-matched journal custody'):
    self.run_admitted(lambda *args,**kwargs:calls.append(args))
  finally:parent.chmod(0o700)
  self.assertEqual(calls,[])
 def test_claim_is_permanent_before_native_dispatch_and_survives_receipt_move(self):
  calls=[];claim=self.root/('.guarded-return-'+self.b['applied_normal_operation_id']+'.claim')
  def timeout(command,**kw):
   self.assertTrue(claim.exists());calls.append(command);raise TimeoutError('synthetic no provider')
  r=self.run_admitted(timeout);self.assertEqual(len(calls),1)
  (self.root/(r['operation_id']+'.json')).rename(self.root/'owned-receipt-preserved')
  (self.root/'_write-barrier.json').rename(self.root/'owned-barrier-preserved')
  with self.assertRaisesRegex(FileExistsError,'consumed'):self.run_admitted(timeout)
  self.assertEqual(len(calls),1)
 def _assert_namespace_swap_blocked(self,phase):
  import os,shutil
  original=self.root.with_name(self.root.name+'-retained-original')
  self.addCleanup(lambda:shutil.rmtree(original) if original.exists() else None)
  real=a._durable_json;swapped=[];calls=[];descriptors=[]
  def write(path,value,**kwargs):
   fd=kwargs.get('directory_fd')
   if fd is not None:descriptors.append(fd)
   name=pathlib.Path(path).name
   trigger=(phase=='barrier' and name=='_write-barrier.json') or (phase=='claim' and name.startswith('.guarded-return-')) or (phase=='request' and name.endswith('.request.json'))
   if trigger and not swapped:
    self.root.rename(original);self.root.mkdir(mode=0o700)
    for f in original.iterdir():shutil.copy2(f,self.root/f.name)
    swapped.append(True)
   return real(path,value,**kwargs)
  with patch.object(a,'_durable_json',side_effect=write):
   with self.assertRaisesRegex(ValueError,'custody'):self.run_admitted(lambda *args,**kw:calls.append(args))
  self.assertTrue(swapped);self.assertEqual(calls,[])
  op=a.operation_identity('restore_guarded_bootstrap',self.b)
  self.assertTrue((original/'_write-barrier.json').exists())
  self.assertTrue((original/(op+'.json')).exists())
  if phase!='barrier':
   self.assertTrue((original/('.guarded-return-'+self.b['applied_normal_operation_id']+'.claim')).exists())
   self.assertTrue((original/(op+'.request.json')).exists())
  else:
   self.assertFalse((original/(op+'.request.json')).exists())
  self.assertTrue(descriptors)
  for fd in set(descriptors):
   with self.assertRaises(OSError):os.fstat(fd)
 def test_namespace_swap_at_barrier_stays_anchored_and_blocks_dispatch(self):
  self._assert_namespace_swap_blocked('barrier')
 def test_namespace_swap_at_claim_stays_anchored_and_blocks_dispatch(self):
  self._assert_namespace_swap_blocked('claim')
 def test_namespace_swap_at_request_stays_anchored_and_blocks_dispatch(self):
  self._assert_namespace_swap_blocked('request')
if __name__=='__main__':unittest.main()
