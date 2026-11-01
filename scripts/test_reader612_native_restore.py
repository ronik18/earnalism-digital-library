"""Synthetic admission/durable-journal fixtures only; never native permission."""
import unittest,tempfile,json,subprocess,hashlib
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import Mock,patch
from scripts import reader612_native_restore as m
class Restore(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.root.chmod(0o700);self.j=self.root/'ops';self.j.mkdir(mode=0o700);self.jp=patch.object(m,'CANONICAL_JOURNAL',self.j);self.jp.start();self.now=datetime(2026,11,1,12,tzinfo=timezone.utc)
  self.b={'source_sha':'1'*40,'tree_sha':'2'*40,'baseline_source_sha':'3'*40,'role':m.ROLE,'project':m.RAILWAY_PROJECT,'service':m.SERVICE,'environment':m.ENVIRONMENT,'baseline_deployment_id':'11111111-1111-1111-1111-111111111111','baseline_snapshot':'22222222-2222-2222-2222-222222222222','current_deployment_id':'33333333-3333-3333-3333-333333333333','baseline_image':'sha256:'+'4'*64,**{k:'5'*64 for k in m.DIGEST_FIELDS}}
  self.b['controller_sha256']=hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest();self.b['support_sha256']=m.support_identity();self.b['journal_identity_sha256']=m.journal_identity(self.j);self.schema={'name':'deploymentRollback','argument':{'name':'id','type':'String!'},'return':'Boolean!'};self.calls=Mock(return_value=subprocess.CompletedProcess([],0,'{"data":{"deploymentRollback":true}}',''))
 def tearDown(self):self.jp.stop();self.tmp.cleanup()
 def observe(self,b):return {'scope':'ACTUAL_IMMUTABLE_SOURCE_AND_NATIVE_BASELINE','binding_sha256':m.digest(b),'observed_at':self.now.isoformat(),'qualified_native_receipt_sha256':'c'*64,'current_runtime_sha256':b['runtime_sha256'],'current_deployment_id':b['current_deployment_id'],'baseline_can_rollback':True,**{k:True for k in ['source_tree_payload_verified','baseline_image_snapshot_config_verified','auto_deploy_off','all_effective_redis_flags_off','current_healthy','no_staged_changes']}}
 def gate(self,ref,action,digest):return {'issuer':'AUTHENTIC_NATIVE_OWNER_PROTECTED_GATE','receipt_sha256':ref,'binding_sha256':digest,'action':action,'native_turn_id':'SYNTHETIC_TEST_ONLY','scope':'BACKEND612_QUALIFICATION_PAUSE_AND_EXACT_BASELINE_RESTORE','issued_at':self.now.isoformat(),'expires_at':(self.now+timedelta(minutes=5)).isoformat()}
 def perform(self,**kw):
  args={'execution_enabled':True,'protected_gate':self.gate,'source_observer':self.observe,'transport':self.calls,'clock':lambda:self.now};args.update(kw);return m.perform_restore(self.b,'a'*64,self.j,self.schema,**args)
 def test_default_denies_all_calls(self):
  with self.assertRaises(ValueError):self.perform(execution_enabled=False)
  self.calls.assert_not_called();self.assertEqual(list(self.j.iterdir()),[])
 def test_preparation_manifest_pins_controller_dependency_bytes(self):
  b=json.loads((Path(m.__file__).resolve().parents[1]/'internal/release/reader612_native_preparation.json').read_text())
  self.assertFalse(m.qualify_controller_preparation(b)['execution_authorized'])
  for name in b['controller_files']:
   wrong={**b,'controller_files':{**b['controller_files'],name:'0'*64}}
   with self.subTest(name=name),self.assertRaisesRegex(ValueError,'dependency mismatch'):m.qualify_controller_preparation(wrong)
 def test_unbound_and_mismatched_source_deny(self):
  for key,value in [('payload_sha256','UNBOUND'),('source_sha','UNBOUND'),('controller_sha256','0'*64),('support_sha256','f'*64),('baseline_image',None)]:
   old=self.b[key];self.b[key]=value
   with self.subTest(key=key),self.assertRaises((ValueError,TypeError)):self.perform()
   self.b[key]=old
  self.calls.assert_not_called()
 def test_local_approval_boolean_and_frontend_scope_denied(self):
  for gate in [None,lambda *a:{'approved':True},lambda *a:{**self.gate(*a),'scope':'FRONTEND613_ONLY'}]:
   with self.subTest(gate=gate),self.assertRaises((ValueError,KeyError)):self.perform(protected_gate=gate)
  self.calls.assert_not_called()
 def test_historical_or_stale_gate_denied(self):
  for delta in [timedelta(days=2),timedelta(minutes=16)]:
   def gate(*a):
    g=self.gate(*a);g['issued_at']=(self.now-delta).isoformat();return g
   with self.assertRaises(ValueError):self.perform(protected_gate=gate)
  self.calls.assert_not_called()
 def test_source_native_observation_mismatch_denied(self):
  for change in [{'binding_sha256':'b'*64},{'auto_deploy_off':False},{'all_effective_redis_flags_off':False},{'qualified_native_receipt_sha256':''},{'current_runtime_sha256':'0'*64}]:
   with self.subTest(change=change),self.assertRaises(ValueError):self.perform(source_observer=lambda b:{**self.observe(b),**change})
  self.calls.assert_not_called()
 def test_scalar_schema_and_exact_durable_request(self):
  r=self.perform();req=json.loads((self.j/(r['operation_id']+'.request.json')).read_text());self.assertEqual(req['argv'],['railway','api','mutation { deploymentRollback(id:"'+self.b['baseline_deployment_id']+'") }','--compact']);self.assertEqual(r['state'],'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED');self.assertTrue((self.j/'_write-barrier.json').exists())
 def test_wrong_schema_before_intent(self):
  self.schema['return']='Deployment'
  with self.assertRaises(ValueError):self.perform()
  self.calls.assert_not_called()
 def test_timeout_unknown_holds_no_replay(self):
  self.calls.side_effect=TimeoutError();r=self.perform();self.assertIsNone(r['process_exit_code'])
  with self.assertRaises(ValueError):self.perform()
  self.assertEqual(self.calls.call_count,1)
 def test_changed_journal_cannot_replay_unknown_restore(self):
  self.calls.side_effect=TimeoutError();r=self.perform();original=self.j;self.j=self.root/'second';self.j.mkdir(mode=0o700)
  with self.assertRaisesRegex(ValueError,'Canonical admitted'):self.perform()
  with self.assertRaisesRegex(ValueError,'Canonical admitted'):m.reconcile_restore(self.j,r['operation_id'],observer=lambda a,x:self.actual(r))
  self.assertEqual(self.calls.call_count,1);self.assertTrue((original/'_write-barrier.json').exists());self.assertEqual(list(self.j.iterdir()),[])
 def test_durable_failure_no_provider(self):
  with patch.object(m,'_durable_json',side_effect=OSError('fsync failure')),self.assertRaises(OSError):self.perform()
  self.calls.assert_not_called()
 def actual(self,r):return {'scope':'ACTUAL_PROVIDER_AND_SOURCE','operation_id':r['operation_id'],'action':m.ACTION,'source_sha':self.b['source_sha'],'outcome':'APPLIED','receipt_sha256':'f'*64,'restored_image':self.b['baseline_image'],'restored_source_sha':self.b['baseline_source_sha'],'restored_runtime_sha256':self.b['baseline_runtime_sha256'],'restored_config_sha256':self.b['config_sha256'],'deployment_id':'44444444-4444-4444-4444-444444444444',**{k:True for k in ['startup_database_healthy','redis_auto_deploy_off','public_protected_acceptance','qualified_recovery_image_retained']}}
 def test_wrong_actual_keeps_barrier_then_correct_receipt_reconciles(self):
  r=self.perform()
  with self.assertRaises(ValueError):m.reconcile_restore(self.j,r['operation_id'],observer=lambda a,x:{**self.actual(r),'restored_image':'sha256:'+'0'*64})
  self.assertTrue((self.j/'_write-barrier.json').exists());out=m.reconcile_restore(self.j,r['operation_id'],observer=lambda a,x:self.actual(r));self.assertEqual(out['state'],'APPLIED_VERIFIED');self.assertFalse((self.j/'_write-barrier.json').exists())
  with self.assertRaises(ValueError):self.perform()
  self.assertFalse((self.j/'_write-barrier.json').exists())
  self.assertEqual(self.calls.call_count,1)
 def test_unknown_notapplied_cannot_clear_barrier(self):
  r=self.perform()
  with self.assertRaises(ValueError):m.reconcile_restore(self.j,r['operation_id'],observer=lambda a,x:{**self.actual(r),'outcome':'NOT_APPLIED'})
  self.assertTrue((self.j/'_write-barrier.json').exists())
 def test_qualification_defaultdeny_then_same_external_gate(self):
  with self.assertRaises(ValueError):m.admit_qualification(self.b,'a'*64)
  result=m.admit_qualification(self.b,'a'*64,execution_enabled=True,protected_gate=self.gate,source_observer=self.observe,clock=lambda:self.now);self.assertEqual(result['authority_receipt_sha256'],'a'*64);self.calls.assert_not_called()
if __name__=='__main__':unittest.main()
