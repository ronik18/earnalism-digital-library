"""Dummy receipts/temp journals only; no native authority or provider calls."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import india_release_provider_adapter as a
from scripts import first_guard_pair as p
D=lambda x:p.digest(x)
def fixture(journal):
 b={'source_sha':'a'*40,'source_delivery_sha256':'b'*64,'closed_server_sha256':'c'*64,'config_sha256':'d'*64,'frontend_source_sha':'f'*40,'frontend_deployment_id':'dpl_OLD'}
 pr={'schema':'earnalism.first_guard_parent_source_projection.v1','action':'release_guarded_bootstrap',**{k:b[k] for k in ['source_sha','source_delivery_sha256','closed_server_sha256']},'runtime_manifest_sha256':'e'*64,'config_expected_sha256':b['config_sha256'],'frontend_source_sha':'f'*40,'frontend_deployment_id':'dpl_OLD','operations_journal_identity_sha256':a._operation_journal_identity(journal)}
 baseline={'schema':'earnalism.actual_root_native_baseline.v2','owner_scope_receipt_sha256':'a'*64,'intended_closed_source_sha':b['source_sha'],'operations_journal_identity_sha256':pr['operations_journal_identity_sha256'],'historical_terminal_operations':{},'historical_request_artifacts':{},'initial_future_operation_count':0,'limits':p.ACTION_LIMITS.copy()}
 baseline['release_scope_id']=D({'domain':'earnalism.native_action_scope.v1',**{k:baseline[k] for k in ['owner_scope_receipt_sha256','intended_closed_source_sha','operations_journal_identity_sha256']}})
 b['native_action_scope']={k:baseline[k] for k in p.SCOPE_KEYS-{'schema','baseline_sha256'}}|{'schema':'earnalism.native_action_scope.v1','baseline_sha256':D(baseline)}
 a._durable_json(journal/'.native-action-baseline.receipt',baseline)
 a._durable_json(journal/'.native-action-scope.claim',{'schema':'earnalism.native_action_scope_claim.v1','scope':b['native_action_scope']})
 stage={'operation_id':'1'*64,'state':'APPLIED_VERIFIED','action':'stage_frontend','binding':{'source_sha':'2'*40,'native_action_scope':b['native_action_scope']},'provider_deployment_id':'dpl_NEW','reconciliation_receipt_sha256':'3'*64};a._durable_json(journal/('1'*64+'.json'),stage)
 k={'schema':'earnalism.first_guard_policy_core.v1','phase':'FIRST_GUARD_PAIR','parent_source_projection_sha256':D(pr),'containment_scope':'KEEP_PURCHASES_CLOSED_BLOCK_ALL_WRITES_RECONCILE_ONLY','no_compatible_frontend_return':True,'limits_sha256':D(p.LIMITS)}
 o={'schema':'earnalism.reader_migration_owner_acceptance.v1','source':'DIRECT_USER_EXPLICIT_ACCEPTANCE','approved':True,'scope':'FIRST_GUARD_READER_MIGRATION_AND_CONTAINMENT','parent_source_projection_sha256':D(pr),'policy_core_sha256':D(k),'receipt_sha256':'4'*64};t={'schema':'earnalism.existing_containment_operator_reference.v1','scope':'EXISTING_AUTHORIZED_OPERATOR','reference_sha256':'5'*64}
 f={**k,'schema':p.SCHEMA,'policy_core_sha256':D(k),'staged_operation_id':'1'*64,'staged_record_sha256':D(stage),'staged_source_sha':'2'*40,'staged_deployment_id':'dpl_NEW','component_expected_identity_sha256':D(pr),'reader_migration_owner_acceptance_sha256':D(o),'containment_operator_reference_sha256':D(t)}
 c={'projection':pr,'core':k,'policy':f,'owner_acceptance':o,'operator_context':t,'limits':p.LIMITS.copy()};b['first_guard_pair']=c
 op=a.operation_identity('release_guarded_bootstrap',b)
 record={'operation_id':op,'action':'release_guarded_bootstrap','binding':b,'approval_sha256':'6'*64,'state':'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED','operations_journal_identity_sha256':pr['operations_journal_identity_sha256']}
 actual={'native_action_scope':b['native_action_scope'],'native_action_baseline_sha256':b['native_action_scope']['baseline_sha256'],'native_action_scope_authorization':'ACTUAL_ROOT_PREWRITE_BASELINE','scope':'ACTUAL_PROVIDER_AND_SOURCE','action':'release_guarded_bootstrap','source_sha':b['source_sha'],'outcome':'APPLIED','operation_id':op,'receipt_sha256':'7'*64,**{x:b[x] for x in ['source_delivery_sha256','closed_server_sha256','config_sha256']},'runtime_manifest_sha256':'e'*64,'runtime_sha256':b['source_delivery_sha256'],'deployment_id':'00000000-0000-0000-0000-000000000001','retained_image_id':'dummy-image','closed_guest_status':503,'purchase_pause_proof':'MEASURED_EXACT_EARLY_RETURN_AND_ANONYMOUS_503','reader_migration_owner_acceptance':o,'containment_operator_reference':t,'first_guard_policy_sha256':D(f),**{x:True for x in ['startup_complete','database_healthy','source_attestation_matches','verify_refund_webhook_code_preserved']},**{x:False for x in ['auto_deploy','redis_enabled','redis_cache_enabled','multi_replica_enabled','redis_public_metadata_enabled']}}
 a._durable_json(journal/(op+'.json'),record);a._durable_json(journal/'_write-barrier.json',{'operation_id':op,'state':'INTENT_RECONCILE_BEFORE_RETRY'});return b,record,actual
class PairTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.j=self.root/'journal';self.j.mkdir(mode=0o700);self.b,self.r,self.actual=fixture(self.j);self.adapter=a.ProviderAdapter(self.j,owner_authorized=False,observe=lambda *args:self.actual,run=lambda *args:(_ for _ in ()).throw(AssertionError('No transport')))
 def tearDown(self):self.tmp.cleanup()
 def component(self):return self.adapter._reconcile_component(self.r,self.actual)
 def child(self):return {'native_action_scope':self.b['native_action_scope'],'source_sha':'2'*40,'deployment_id':'dpl_NEW','first_guard_pair':self.b['first_guard_pair'],'first_guard_parent_operation_id':self.r['operation_id'],'component_receipt_sha256':self.adapter._read_pending()['component_receipt_sha256']}
 def test_acyclic_exact_contract(self):self.assertEqual(p.validate(self.b)['policy'],self.b['first_guard_pair']['policy'])
 def test_current_operation_approval_cycle_rejected(self):
  for k in ['protected_approval_reference_sha256','parent_operation_id','parent_bootstrap_binding_sha256']:
   b=copy.deepcopy(self.b);b['first_guard_pair']['policy'][k]='9'*64
   with self.assertRaises(ValueError):p.validate(b)
 def test_owner_missing_wrong_scope_or_projection_rejected(self):
  for key,value in [('scope','AUDIOBOOK_ONLY'),('approved',False),('parent_source_projection_sha256','9'*64)]:
   b=copy.deepcopy(self.b);b['first_guard_pair']['owner_acceptance'][key]=value
   with self.assertRaises(ValueError):p.validate(b,self.actual)
 def test_component_not_recovery(self):
  r=self.component();self.assertEqual(r['state'],p.PENDING);self.assertNotIn('guarded_recovery_receipt_sha256',r);self.assertFalse((self.j/'_write-barrier.json').exists());self.assertTrue((self.j/'.first-guard-pending').exists())
 def test_unknown_or_inexact_component_keeps_barrier(self):
  for key,value in [('outcome','UNKNOWN'),('runtime_sha256','9'*64),('closed_guest_status',200),('startup_complete',False)]:
   x=copy.deepcopy(self.actual);x[key]=value
   with self.assertRaises(ValueError):self.adapter._reconcile_component(self.r,x)
   self.assertTrue((self.j/'_write-barrier.json').exists())
 def test_only_bound_child_and_everyother_action_denied(self):
  self.component();c=self.child();self.assertIsNotNone(self.adapter._pending_admission('promote_frontend',c))
  for action in a.ACTIONS-{'promote_frontend'}:
   with self.assertRaises(ValueError):self.adapter._pending_admission(action,c)
  c['deployment_id']='dpl_OTHER'
  with self.assertRaises(ValueError):self.adapter._pending_admission('promote_frontend',c)
 def test_unknown_child_physical_barrier_denies(self):
  self.component();a._durable_json(self.j/'_write-barrier.json',{'operation_id':'9'*64})
  with self.assertRaises(ValueError):self.adapter._pending_admission('promote_frontend',self.child())
 def test_direct_adapter_and_controller_cannot_bypass(self):
  self.component()
  for f in [self.adapter.perform,a.ReleaseController(self.adapter).perform]:
   with self.assertRaises(ValueError):f('release_backend',{'source_sha':'f'*40},{})
 def test_component_receipt_mutation_blocks(self):
  self.component();pending=self.adapter._read_pending();a._durable_json(self.j/pending['component_receipt_name'],{'wrong':True})
  with self.assertRaises(ValueError):self.adapter._pending_admission('promote_frontend',self.child())
 def test_crash_after_receipt_or_guard_stops_all_writes(self):
  original=a._durable_json
  for crash in [2,3]:
   with self.subTest(crash=crash):
    for f in self.j.iterdir():f.unlink()
    self.b,self.r,self.actual=fixture(self.j);count=[0]
    def write(*args,**kwargs):
     count[0]+=1
     if count[0]==crash:raise OSError('Dummy crash')
     return original(*args,**kwargs)
    with patch.object(a,'_durable_json',side_effect=write),self.assertRaises(OSError):self.component()
    self.assertTrue((self.j/'_write-barrier.json').exists())
    with self.assertRaises((ValueError,KeyError)):self.adapter._pending_admission('release_backend',{'source_sha':'f'*40})
 def test_final_requires_actual_pair_and_never_dispatches(self):
  self.component()
  with self.assertRaises(ValueError):self.adapter.finalize_first_guard_pair(self.r['operation_id'])
 def test_terminal_parent_cannot_reenter_component(self):
  r={**self.r,'state':'APPLIED_VERIFIED'}
  with self.assertRaises(ValueError):self.adapter._reconcile_component(r,self.actual)
if __name__=='__main__':unittest.main()

class RepairTests(unittest.TestCase):
 setUp=PairTests.setUp
 tearDown=PairTests.tearDown
 component=PairTests.component
 child=PairTests.child
 def test_each_component_crash_can_readonly_reconcile_same_operation(self):
  original=a._durable_json
  for crash in [1,2,3,4]:
   with self.subTest(crash=crash):
    for f in self.j.iterdir():f.unlink()
    self.b,self.r,self.actual=fixture(self.j);count=[0]
    def write(*args,**kwargs):
     count[0]+=1
     if count[0]==crash:raise OSError('Dummy crash')
     return original(*args,**kwargs)
    with patch.object(a,'_durable_json',side_effect=write),self.assertRaises(OSError):self.component()
    self.assertTrue((self.j/'_write-barrier.json').exists())
    # Uses the actual adapter reconciliation observer seam; no transport.
    self.adapter.observe=lambda *args:self.actual
    r=self.adapter.reconcile(self.r['operation_id']);self.assertEqual(r['state'],p.PENDING)
    self.assertFalse((self.j/'_write-barrier.json').exists());self.assertIsNotNone(self.adapter._read_pending())
 def test_unknown_real_reconciliation_keeps_barrier(self):
  self.adapter.observe=lambda *args:{**self.actual,'outcome':'UNKNOWN'}
  with self.assertRaises(ValueError):self.adapter.reconcile(self.r['operation_id'])
  self.assertTrue((self.j/'_write-barrier.json').exists());self.assertFalse((self.j/'.first-guard-pending').exists())
 def make_child(self,outcome='APPLIED'):
  self.component();c=self.child();op=a.operation_identity('promote_frontend',c)
  r={'operation_id':op,'action':'promote_frontend','binding':c,'state':'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED'}
  a._durable_json(self.j/(op+'.json'),r);pending=self.adapter._read_pending();pending['child_operation_id']=op;a._durable_json(self.j/'.first-guard-pending',pending);a._durable_json(self.j/'_write-barrier.json',{'operation_id':op,'state':'INTENT_RECONCILE_BEFORE_RETRY'})
  actual={'native_action_scope':c['native_action_scope'],'native_action_baseline_sha256':c['native_action_scope']['baseline_sha256'],'native_action_scope_authorization':'ACTUAL_ROOT_PREWRITE_BASELINE','scope':'ACTUAL_PROVIDER_AND_SOURCE','operation_id':op,'action':'promote_frontend','source_sha':c['source_sha'],'outcome':outcome,'receipt_sha256':'8'*64};self.adapter.observe=lambda *args:actual
  return self.adapter.reconcile(op)
 def test_child_noeffect_consumed_containment_blocks_allwrites(self):
  self.make_child('NOT_APPLIED');self.assertEqual(self.adapter._read_pending()['state'],p.BLOCKED)
  with self.assertRaises(ValueError):self.adapter._pending_admission('promote_frontend',self.child())
 def test_child_applied_only_readonly_finalization_allowed(self):
  self.make_child();pending=self.adapter._read_pending();self.assertEqual(pending['state'],'PAIR_READONLY_FINALIZATION_REQUIRED')
  with self.assertRaises(ValueError):self.adapter._pending_admission('promote_frontend',self.child())
 def test_final_full_existing_qualifier_and_crash_retirement(self):
  self.make_child();pending=self.adapter._read_pending();child=a._read_journal(self.j/(pending['child_operation_id']+'.json'))
  x={**self.actual,'component_receipt_sha256':pending['component_receipt_sha256'],'child_record_sha256':D(child),'both_aliases_verified':True,'paired_reader_listener_financial_preserved':True,'recovery_receipt_sha256':'9'*64,'guarded_backend_deployment_id':self.actual['deployment_id'],'serving_frontend_deployment_id':'dpl_NEW','serving_frontend_source_sha':'2'*40,**{k:True for k in ['reader_public_preview_verified','reader_protected_entitlement_verified','reader_free_pilot_entitlement_preserved','listener_protected_accounting_preserved','native_can_rollback','config_compatible','existing_reader_listener_preserved']}}
  self.adapter.observe=lambda *args:x
  original=a._durable_json
  count=[0]
  def write(*args,**kwargs):
   count[0]+=1
   if count[0]==2:raise OSError('Dummy crash after final receipt')
   return original(*args,**kwargs)
  with patch.object(a,'_durable_json',side_effect=write),self.assertRaises(OSError):self.adapter.finalize_first_guard_pair(self.r['operation_id'])
  self.assertTrue((self.j/'.first-guard-pending').exists());self.assertEqual(a._read_journal(self.j/(self.r['operation_id']+'.json'))['state'],p.PENDING)
  r=self.adapter.finalize_first_guard_pair(self.r['operation_id']);self.assertEqual(r['state'],'APPLIED_VERIFIED');self.assertEqual(r['guarded_recovery_receipt_sha256'],'9'*64);self.assertFalse((self.j/'.first-guard-pending').exists())

class ConcurrencyTests(unittest.TestCase):
 setUp=PairTests.setUp
 tearDown=PairTests.tearDown
 component=PairTests.component
 child=PairTests.child
 def test_two_reconcilers_never_replace_component_receipt_or_repeat_write(self):
  from concurrent.futures import ThreadPoolExecutor
  self.adapter.observe=lambda *args:self.actual
  def invoke():
   try:return self.adapter.reconcile(self.r['operation_id'])['state']
   except BlockingIOError:return 'LOCKED'
  with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:invoke(),range(2)))
  self.assertIn(p.PENDING,results);self.assertEqual(len(list(self.j.glob('.first-guard-component-*.receipt'))),1)
  self.assertFalse((self.j/'_write-barrier.json').exists())
 def test_final_component_identity_change_blocks_child_before_dispatch(self):
  self.component();c=self.child()
  with self.assertRaises(ValueError):self.adapter._pending_admission('promote_frontend',c,actual={'backend_deployment_id':'wrong'})
 def test_wrong_stage_record_before_parent_dispatch_denied(self):
  a._durable_json(self.j/('1'*64+'.json'),{'state':'APPLIED_VERIFIED','wrong':True})
  with self.assertRaises(ValueError):self.adapter._pending_admission('release_guarded_bootstrap',self.b)
