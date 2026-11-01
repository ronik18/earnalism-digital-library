"""Synthetic phase chain with real admission/journal/reconciliation, zero providers."""
import copy,json,hashlib,subprocess,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import Mock,patch
from scripts import reader612_phase_bridge as b
from scripts import reader612_native_restore as n
from scripts import india_release_provider_adapter as a

class Bridge(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve();self.root.chmod(0o700);self.j=self.root/'ops';self.j.mkdir(mode=0o700)
  self.patch=patch.object(n,'CANONICAL_JOURNAL',self.j);self.patch.start();self.addCleanup(self.patch.stop)
  self.now=datetime(2026,11,1,12,tzinfo=timezone.utc);self.controller='1'*40;self.owner={'schema':'earnalism.reader612-native-owner-scope.v1','authority_kind':'ACTUAL_CURRENT_NATIVE_OWNER_INSTRUCTION','native_turn_id':'12345678-1234-1234-1234-123456789012','instruction_sha256':'2'*64,'accepted_at':self.now.isoformat(),'controller_sha':self.controller,'source_sha':'3'*40,'scope':dict.fromkeys(b.OWNER_SCOPE,True)}
  self.c=Mock();self.x=b.Reader612PhaseBridge.__new__(b.Reader612PhaseBridge);self.x.role_root=self.root;self.x.clock=lambda:self.now;self.x.collector=self.c
  self.x.source_binding={'source_sha':'3'*40};self.x.acceptance={'synthetic':'NOT_LIVE_PROOF'};self.U={'files':[],'runtime_expected_sha256':'4'*64}
  self.P={'source_sha':'3'*40,'source_root':str(self.root),'frontend_deployment_id':'dpl_SYNTHETIC','frontend_source_sha':'5'*40,'backend_payload_sha256':a.digest(self.U),'source_delivery_sha256':'4'*64,'closed_server_sha256':'6'*64,'native_pause_acceptance_sha256':a.digest(self.owner),'purchase_mode':'CLOSED','current_backend_deployment_id':'11111111-1111-1111-1111-111111111111','current_backend_source_sha':'7'*40,'config_sha256':'8'*64}
  self.N={'source_sha':self.P['source_sha'],'tree_sha':'9'*40,'baseline_source_sha':'7'*40,'role':n.ROLE,'project':a.RAILWAY_PROJECT,'service':a.SERVICE,'environment':a.ENVIRONMENT,'baseline_deployment_id':self.P['current_backend_deployment_id'],'baseline_snapshot':'22222222-2222-2222-2222-222222222222','baseline_image':'sha256:'+'a'*64,'current_deployment_id':self.P['current_backend_deployment_id'],**dict.fromkeys(n.DIGEST_FIELDS,'b'*64)}
  self.N.update(payload_sha256=a.digest(b.covered_envelope(self.U,self.P,self.x.acceptance)),runtime_sha256='4'*64,config_sha256='8'*64,controller_sha256=hashlib.sha256(Path(n.__file__).read_bytes()).hexdigest(),support_sha256=n.support_identity(),journal_identity_sha256=n.journal_identity(self.j))
  self.prepared={'scope':'OFFLINE_PREPARATION_NOT_AUTHORITY','controller_sha':self.controller,'native_binding':self.N,'provider_binding':self.P,'upload_payload':self.U,'acceptance_contract':self.x.acceptance}
  self.actual={**self.P,'scope':'ACTUAL_PROVIDER_AND_SOURCE','qualified':True,'provider_identity_sha256':'c'*64,'bootstrap_preflight_sha256':'d'*64,'authenticated_provider_account':True,'auto_deploy':False,'cli_version':a.CLI_VERSIONS['railway'],'frontend_signed_purchase_ready':True,'current_backend_healthy':True,'native_healthcheck_traffic_gating':True,'new_resources_or_config_changes':False}
  self.proof={'scope':'ACTUAL_IMMUTABLE_SOURCE_AND_NATIVE_BASELINE','binding_sha256':a.digest(self.N),'observed_at':self.now.isoformat(),**dict.fromkeys(['source_tree_payload_verified','baseline_image_snapshot_config_verified','auto_deploy_off','all_effective_redis_flags_off','current_healthy','no_staged_changes'],True),'provider_actual':self.actual}
  self.c.collect_preflight.return_value=self.proof;self.x._verify_prepared=Mock(return_value=self.prepared);self.x._resolver=Mock(return_value=self.gate);self.calls=[]
  a._durable_json(self.j/('e'*64+'.json'),{'state':'APPLIED_VERIFIED','action':'promote_frontend','binding':{'source_sha':self.P['frontend_source_sha'],'deployment_id':self.P['frontend_deployment_id']},'reconciliation_receipt_sha256':'f'*64},exclusive=True)
 def gate(self,ref,action,bd):return {'issuer':'AUTHENTIC_NATIVE_OWNER_PROTECTED_GATE','receipt_sha256':ref,'binding_sha256':bd,'action':action,'native_turn_id':'SYNTHETIC_TEST_ONLY','scope':'BACKEND612_QUALIFICATION_PAUSE_AND_EXACT_BASELINE_RESTORE','rollback_operator':'SYNTHETIC','issued_at':self.now.isoformat(),'expires_at':(self.now+timedelta(minutes=5)).isoformat()}
 def adapter(self,*args,**kw):return a.ProviderAdapter(*args,**kw,run=self.run_cli)
 def run_cli(self,argv,**kw):
  self.calls.append(argv);self.assertTrue((self.j/'_write-barrier.json').exists());return subprocess.CompletedProcess(argv,0,'{}','')
 def perform(self):
  with patch.object(b,'ProviderAdapter',side_effect=self.adapter),patch.object(a.subprocess,'check_output',side_effect=lambda argv,**kw:self.P['source_sha']+'\n' if argv[-1]=='HEAD' else ''),patch('scripts.backend_upload_payload.qualify',return_value=self.U):
   return self.x.perform_qualification(self.prepared,self.owner,123,'a'*64,'SYNTHETIC',execution_enabled=True,current_owner_authorized=True)
 def receipt(self,r):
  q={**self.P,'scope':'ACTUAL_PROVIDER_AND_SOURCE','action':'release_guarded_bootstrap','operation_id':r['operation_id'],'outcome':'APPLIED','deployment_id':'33333333-3333-3333-3333-333333333333','guarded_backend_deployment_id':'33333333-3333-3333-3333-333333333333','retained_image_id':'sha256:'+'d'*64,'snapshot_id':'44444444-4444-4444-4444-444444444444','recovery_receipt_sha256':'e'*64,'closed_guest_status':503,'purchase_pause_proof':'MEASURED_EXACT_EARLY_RETURN_AND_ANONYMOUS_503',**dict.fromkeys(['startup_complete','database_healthy','source_attestation_matches','native_can_rollback','config_compatible','existing_reader_listener_preserved','verify_refund_webhook_code_preserved'],True)}
  q['receipt_sha256']=a.digest(q);return q
 def qualify(self):
  r=self.perform();self.q=self.receipt(r);self.c.collect_closed.return_value=self.q;return self.x.reconcile_qualification(r['operation_id'])
 def test_default_denial_before_io_or_journal(self):
  before=list(self.j.iterdir())
  for flags in [{},{'execution_enabled':True},{'current_owner_authorized':True}]:
   with self.assertRaises(ValueError):self.x.perform_qualification(self.prepared,self.owner,1,'a'*64,'op',**flags)
  self.c.assert_not_called();self.x._verify_prepared.assert_not_called();self.assertEqual(list(self.j.iterdir()),before)
 def test_owner_scope_exact_current_and_not_local_approved_flag(self):
  self.assertEqual(self.x._owner_scope(self.owner,self.controller),a.digest(self.owner))
  for changes in [{'approved':True},{'accepted_at':(self.now-timedelta(days=2)).isoformat()},{'controller_sha':'a'*40},{'scope':{'temporary_purchase_pause':True}}]:
   with self.subTest(changes=changes),self.assertRaises(ValueError):self.x._owner_scope({**self.owner,**changes},self.controller)
 def test_real_admission_projection_and_existing_adapter_one_intent(self):
  r=self.perform();coverage=self.x._coverage(r);self.assertEqual(coverage['admission']['binding_sha256'],a.digest(self.N));self.assertEqual(len(self.calls),1);self.assertEqual(self.c.collect_preflight.call_count,1);self.assertTrue((self.j/'_write-barrier.json').exists())
  with self.assertRaises(ValueError):self.perform()
  self.assertEqual(len(self.calls),1)
 def test_gate_failure_cannot_project_provider_approval(self):
  self.x._resolver.return_value=lambda *args:{'approved':True}
  with self.assertRaises(ValueError):self.perform()
  self.assertEqual(self.calls,[]);self.assertFalse((self.j/'_write-barrier.json').exists())
 def test_parent_proof_drift_denies_before_write(self):
  self.proof['binding_sha256']='0'*64
  with self.assertRaises(ValueError):self.perform()
  self.assertEqual(self.calls,[])
 def test_stored_admission_owner_or_proof_tamper_denies(self):
  r=self.perform();path=self.j/(r['approval_sha256']+'.coverage.request.json');original=a._read_journal(path)
  for field in ['admission','owner_scope_record','preflight_proof']:
   changed=copy.deepcopy(original);changed[field]['tampered']=True;a._durable_json(path,changed)
   with self.subTest(field=field),self.assertRaises(ValueError):self.x._coverage(r)
  a._durable_json(path,original);self.x._coverage(r)
 def test_outcome_persisted_before_generic_reconciliation(self):
  r=self.qualify();self.assertEqual(r['state'],'APPLIED_VERIFIED');self.assertEqual(r['guarded_recovery_receipt_sha256'],self.q['recovery_receipt_sha256']);self.assertEqual(a._read_journal(self.j/(self.q['receipt_sha256']+'.actual.request.json')),self.q);self.assertFalse((self.j/'_write-barrier.json').exists())
 def test_bad_actual_hash_keeps_unknown_barrier(self):
  r=self.perform();self.c.collect_closed.return_value={**self.receipt(r),'receipt_sha256':'f'*64}
  with self.assertRaises(ValueError):self.x.reconcile_qualification(r['operation_id'])
  self.assertTrue((self.j/'_write-barrier.json').exists())
 def test_at_most_once_closed_probe_and_crash_uncertainty(self):
  r={'operation_id':'a'*64,'binding':self.P};self.c.purchase_probe.return_value=(503,{'Cache-Control':'no-store'},b'{"detail":{"code":"PURCHASE_INITIATION_CLOSED"}}');probe=self.x._closed_probe_once(r)
  self.assertEqual(probe('POST','https://theearnalism.com/api/payments/topup',b'{}')[0],503);self.assertEqual(probe('POST','https://theearnalism.com/api/payments/topup',b'{}')[0],503);self.assertEqual(self.c.purchase_probe.call_count,1)
  r['operation_id']='b'*64;self.c.purchase_probe.side_effect=TimeoutError();probe=self.x._closed_probe_once(r)
  with self.assertRaises(TimeoutError):probe('POST','https://theearnalism.com/api/payments/topup',b'{}')
  with self.assertRaisesRegex(ValueError,'never repeat'):probe('POST','https://theearnalism.com/api/payments/topup',b'{}')
  self.assertEqual(self.c.purchase_probe.call_count,2)
 def test_restore_preparation_reuses_exact_durable_receipt_not_post(self):
  r=self.qualify();source={'runtime_sha256':self.N['runtime_sha256']}
  with patch.object(b,'local_git',side_effect=lambda *args:self.controller if args[-1]=='HEAD' else ''),patch.object(n,'qualify_controller_preparation'),patch.object(b,'qualify_binding',return_value=source),patch.object(b,'upload_qualify',return_value=self.U):
   restore=self.x.prepare_restore(self.owner,r['operation_id']);self.assertEqual(restore['qualified_receipt'],self.q);self.assertEqual(restore['native_binding']['payload_sha256'],a.digest(b.restore_envelope(self.U,self.P,self.x.acceptance,self.q)));self.assertEqual(self.c.collect_closed.call_count,1)
   with patch.object(b,'local_git',return_value='changed'),self.assertRaises(ValueError):self.x.prepare_restore(self.owner,r['operation_id'])
 def test_restore_reconciliation_derives_authentic_coverage_not_input(self):
  qualified=self.qualify();nr={**self.N,'current_deployment_id':self.q['deployment_id'],'payload_sha256':a.digest(b.restore_envelope(self.U,self.P,self.x.acceptance,self.q))}
  op=a.digest({'action':n.ACTION,'project':a.RAILWAY_PROJECT,'service':a.SERVICE,'environment':a.ENVIRONMENT,'baseline_deployment':nr['baseline_deployment_id'],'qualified_source':nr['source_sha']});record={'operation_id':op,'action':n.ACTION,'binding':nr,'state':'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED'}
  a._durable_json(self.j/(op+'.json'),record,exclusive=True);a._durable_json(self.j/'_write-barrier.json',{'operation_id':op,'state':'INTENT_RECONCILE_BEFORE_RETRY'},exclusive=True)
  actual={'scope':'ACTUAL_PROVIDER_AND_SOURCE','operation_id':op,'action':n.ACTION,'source_sha':nr['source_sha'],'outcome':'APPLIED','deployment_id':'55555555-5555-5555-5555-555555555555','restored_image':nr['baseline_image'],'restored_source_sha':nr['baseline_source_sha'],'restored_runtime_sha256':nr['baseline_runtime_sha256'],'restored_config_sha256':nr['config_sha256'],**dict.fromkeys(['startup_database_healthy','redis_auto_deploy_off','public_protected_acceptance','qualified_recovery_image_retained'],True)};actual['receipt_sha256']=a.digest(actual);self.c.collect_restored.return_value=actual
  result=self.x.reconcile_restore(op);self.assertEqual(result['state'],'APPLIED_VERIFIED');expected=self.c.collect_restored.call_args.args[1];self.assertEqual(expected['qualified_recovery'],self.q);self.assertEqual(expected['qualification_record'],qualified)
 def test_wrong_restore_envelope_cannot_collect_or_clear_barrier(self):
  self.qualify();op='f'*64;r={'action':n.ACTION,'binding':{**self.N,'payload_sha256':'0'*64},'state':'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED'};a._durable_json(self.j/(op+'.json'),r,exclusive=True)
  with self.assertRaises(ValueError):self.x.reconcile_restore(op)
  self.c.collect_restored.assert_not_called()
 def test_restore_default_denied_before_io(self):
  with self.assertRaises(ValueError):self.x.perform_restore({},self.owner,1,'a'*64,'op',{})
  self.c.restore_schema.assert_not_called()
 def test_acceptance_and_each_parent_member_change_envelope(self):
  original=a.digest(b.covered_envelope(self.U,self.P,self.x.acceptance))
  for pos in range(3):
   parts=copy.deepcopy([self.U,self.P,self.x.acceptance]);parts[pos]['changed']=True;self.assertNotEqual(original,a.digest(b.covered_envelope(*parts)))
if __name__=='__main__':unittest.main()
