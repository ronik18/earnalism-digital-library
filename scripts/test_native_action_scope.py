"""Immutable dummy Root baselines only; no real ledger/profile access."""
import copy,json,hashlib,tempfile,unittest
from pathlib import Path
from scripts import first_guard_pair as p
from scripts import india_release_provider_adapter as a
class BudgetTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.j=Path(self.tmp.name)/'j';self.j.mkdir(mode=0o700)
  self.base={'schema':'earnalism.actual_root_native_baseline.v1','owner_scope_receipt_sha256':'a'*64,'intended_closed_source_sha':'b'*40,'operations_journal_identity_sha256':a._operation_journal_identity(self.j),'release_scope_id':'temporary','historical_terminal_operations':{},'initial_future_operation_count':0,'limits':p.ACTION_LIMITS.copy()}
  self.base['release_scope_id']=p.digest({'domain':'earnalism.native_action_scope.v1',**{k:self.base[k] for k in ['owner_scope_receipt_sha256','intended_closed_source_sha','operations_journal_identity_sha256']}})
  self.scope={k:self.base[k] for k in p.SCOPE_KEYS-{'schema','baseline_sha256'}}|{'schema':'earnalism.native_action_scope.v1','baseline_sha256':p.digest(self.base)}
  a._durable_json(self.j/'.native-action-baseline.receipt',self.base)
  self.b={'source_sha':'d'*40,'source_root':str(self.j.parent),'native_action_scope':self.scope};self.adapter=a.ProviderAdapter(self.j)
 def tearDown(self):self.tmp.cleanup()
 def record(self,n,action='release_backend',state='WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED'):
  b={**self.b,'source_sha':format(n,'040x')};return {'operation_id':a.operation_identity(action,b),'action':action,'binding':b,'state':state}
 def seal_scope(self):self.adapter._native_budget('stage_frontend',self.b,claim=True,durable=a._durable_json)
 def test_exact_root_custody_and_zero_baseline(self):p.validate_scope(self.scope,self.base,a._operation_journal_identity(self.j))
 def test_tampered_baseline_and_new_path_scope_rejected(self):
  for k in ['owner_scope_receipt_sha256','operations_journal_identity_sha256','release_scope_id']:
   b=copy.deepcopy(self.base);b[k]='e'*64
   with self.assertRaises(ValueError):p.validate_scope(self.scope,b,a._operation_journal_identity(self.j))
 def test_unknown_failed_noeffect_all_count_and_self_once(self):
  rs=[(self.record(i,state=s),'e'*64) for i,s in enumerate(['UNKNOWN','NOT_APPLIED_VERIFIED','INTENT_RECONCILE_BEFORE_RETRY'],1)]
  self.assertEqual(p.count_scoped_intents(self.scope,self.base,rs,candidate=rs[0][0])['backend'],3)
  with self.assertRaises(ValueError):p.count_scoped_intents(self.scope,self.base,rs,candidate=self.record(4))
 def test_second_build_before_parent_denied(self):
  r=self.record(1,'stage_frontend')
  with self.assertRaises(ValueError):p.count_scoped_intents(self.scope,self.base,[(r,'e'*64)],candidate=self.record(2,'stage_frontend'))
 def test_foreign_unscoped_or_unknown_action_denied(self):
  for mutate in [lambda r:r['binding'].pop('native_action_scope'),lambda r:r.update(action='foreign')]:
   r=self.record(1);mutate(r)
   with self.assertRaises(ValueError):p.count_scoped_intents(self.scope,self.base,[(r,'e'*64)])
 def test_history_rawbytes_changed_missing_or_nonterminal_denied(self):
  r=self.record(1,state='APPLIED_VERIFIED');b={**self.base,'historical_terminal_operations':{r['operation_id']:'e'*64}}
  for rows in [[],[(r,'f'*64)],[({**r,'state':'UNKNOWN'},'e'*64)]]:
   with self.assertRaises(ValueError):p.count_scoped_intents(self.scope,b,rows)
 def test_after_started_baseline_adoption_denied(self):
  r=self.record(1);a._durable_json(self.j/(r['operation_id']+'.json'),r)
  with self.assertRaises(ValueError):self.adapter._native_budget('stage_frontend',self.b,claim=True,durable=a._durable_json)
  self.assertFalse((self.j/'.native-action-scope.claim').exists())
 def test_scope_claim_never_resets_to_fresh_baseline(self):
  self.seal_scope();base={**self.base,'owner_scope_receipt_sha256':'e'*64};scope={**self.scope,'owner_scope_receipt_sha256':'e'*64,'baseline_sha256':p.digest(base)};a._durable_json(self.j/'.native-action-baseline.receipt',base)
  with self.assertRaises(ValueError):self.adapter._native_budget('stage_frontend',{**self.b,'native_action_scope':scope})
 def test_unscoped_later_write_and_missing_trusted_root_proof_denied(self):
  self.seal_scope()
  with self.assertRaises(ValueError):self.adapter._native_budget('release_backend',{'source_sha':'d'*40})
  with self.assertRaises(ValueError):self.adapter._native_budget('stage_frontend',self.b,actual={})
 def test_scoped_stage_requires_protected_approval_scope_hash(self):
  with self.assertRaises(ValueError):self.adapter.perform('stage_frontend',self.b,{})
  self.assertFalse((self.j/'_write-barrier.json').exists())
if __name__=='__main__':unittest.main()

class ScopedDispatchTests(unittest.TestCase):
 setUp=BudgetTests.setUp
 tearDown=BudgetTests.tearDown
 record=BudgetTests.record
 seal_scope=BudgetTests.seal_scope
 def approval(self,b):
  from datetime import datetime,timezone,timedelta
  now=datetime.now(timezone.utc)
  return {'schema':'earnalism-india-protected-operation.v1','action':'stage_frontend','binding_sha256':a.digest(b),'project':a.PROJECT,'team':a.TEAM,'railway_project':a.RAILWAY_PROJECT,'service':a.SERVICE,'environment':a.ENVIRONMENT,'territories':['IN'],'auto_deploy':False,'approved':True,'provider_identity_sha256':'b'*64,'config_sha256':'c'*64,'guarded_rollback_sha256':'d'*64,'rollback_operator':'DUMMY_ONLY','approved_at':(now-timedelta(seconds=10)).isoformat(),'expires_at':(now+timedelta(minutes=5)).isoformat(),'provider_observed_at':now.isoformat(),'native_action_scope_sha256':a.digest(self.scope)}
 def run_adapter(self,b,calls):
  from types import SimpleNamespace
  approval=self.approval(b)
  actual={**{k:approval[k] for k in ['provider_identity_sha256','config_sha256','guarded_rollback_sha256']},'scope':'ACTUAL_PROVIDER_AND_SOURCE','qualified':True,'auto_deploy':False,'guarded_rollback_available':True,'cli_version':a.CLI_VERSIONS['vercel'],'authenticated_provider_account':True,'native_action_scope':self.scope,'native_action_baseline_sha256':self.scope['baseline_sha256'],'native_action_scope_authorization':'ACTUAL_ROOT_PREWRITE_BASELINE'}
  return a.ProviderAdapter(self.j,owner_authorized=True,observe=lambda *args:actual,run=lambda *args,**kwargs:(calls.append(args) or SimpleNamespace(returncode=0,stdout='{"id":"dpl_DUMMY"}'))).perform('stage_frontend',b,approval)
 def test_two_concurrent_stages_dispatch_only_one_and_consume_unknown(self):
  from concurrent.futures import ThreadPoolExecutor
  calls=[]
  def invoke(n):
   try:self.run_adapter({**self.b,'source_sha':format(n,'040x')},calls);return 'attempted'
   except (ValueError,FileExistsError):return 'blocked'
  with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(invoke,[1,2]))
  self.assertEqual(sorted(results),['attempted','blocked']);self.assertEqual(len(calls),1)
  with self.assertRaises((ValueError,FileExistsError)):self.run_adapter({**self.b,'source_sha':'f'*40},calls)
  self.assertEqual(len(calls),1)
 def test_orphan_request_is_not_exempted_as_local_receipt(self):
  a._durable_json(self.j/('e'*64+'.request.json'),{'action':'stage_frontend'})
  with self.assertRaises(ValueError):self.adapter._native_budget('stage_frontend',self.b)
 def test_unknown_orphan_barrier_blocks_even_without_record(self):
  self.seal_scope();a._durable_json(self.j/'_write-barrier.json',{'operation_id':'e'*64,'state':'INTENT_RECONCILE_BEFORE_RETRY'})
  with self.assertRaises(ValueError):self.adapter._native_budget('stage_frontend',self.b)
 def test_final_self_count_accepts_cap_and_rejects_changed_source(self):
  self.seal_scope();r=self.record(1,'stage_frontend');a._durable_json(self.j/(r['operation_id']+'.json'),r)
  self.adapter._native_budget('stage_frontend',r['binding'],own_operation_id=r['operation_id'])
  with self.assertRaises(ValueError):self.adapter._native_budget('stage_frontend',{**r['binding'],'source_sha':'f'*40},own_operation_id=r['operation_id'])

class ClosedSourceAdmissionTests(unittest.TestCase):
 setUp=BudgetTests.setUp
 tearDown=BudgetTests.tearDown
 def test_wrong_closed_source_denied_before_claim(self):
  with self.assertRaisesRegex(ValueError,'Actual CLOSED source'):
   self.adapter._native_budget('release_guarded_bootstrap',self.b,claim=True,durable=a._durable_json)
  self.assertFalse((self.j/'.native-action-scope.claim').exists())
 def test_exact_closed_source_and_distinct_frontend_source_admitted(self):
  self.adapter._native_budget('release_guarded_bootstrap',{**self.b,'source_sha':self.scope['intended_closed_source_sha']})
  self.adapter._native_budget('stage_frontend',self.b)

class BaselineWriterAdmissionTests(unittest.TestCase):
 setUp=BudgetTests.setUp
 tearDown=BudgetTests.tearDown
 approval=ScopedDispatchTests.approval
 run_adapter=ScopedDispatchTests.run_adapter
 def test_unscoped_write_blocked_before_first_claim(self):
  binding=copy.deepcopy(self.b);binding.pop('native_action_scope');calls=[]
  with self.assertRaisesRegex(ValueError,'Stable original native scope'):
   self.run_adapter(binding,calls)
  self.assertEqual(calls,[])
  self.assertFalse((self.j/'.native-action-scope.claim').exists())
  self.assertEqual(list(self.j.glob('*.json')),[])
 def test_malformed_baseline_cannot_allow_unscoped_dispatch(self):
  (self.j/'.native-action-baseline.receipt').write_text('not json')
  binding=copy.deepcopy(self.b);binding.pop('native_action_scope');calls=[]
  with self.assertRaises(ValueError):self.run_adapter(binding,calls)
  self.assertEqual(calls,[])
