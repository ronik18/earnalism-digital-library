"""Real adapter/controller with temporary Git/journals and fake CLI only."""
import copy,json,os,subprocess,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from unittest.mock import patch
from scripts import india_release_provider_adapter as a

class PrivateStage(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.home=Path(self.temp.name).resolve();self.source=self.home/'source';self.source.mkdir();(self.source/'frontend').mkdir();(self.source/'frontend/inert.txt').write_text('synthetic frontend')
  env={**os.environ,'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_NO_LAZY_FETCH':'1'}
  def git(*args):return subprocess.check_output(['git','-C',str(self.source),*args],env=env,text=True,stderr=subprocess.DEVNULL).strip()
  git('init');git('add','frontend');git('-c','user.name=Dummy','-c','user.email=dummy@example.invalid','commit','-m','synthetic only')
  self.sha=git('rev-parse','HEAD');self.tree=git('rev-parse','HEAD:frontend');self.journal=self.home/'operations';self.calls=[];self.now=datetime(2026,11,4,12,tzinfo=timezone.utc)
  self.b={'source_sha':self.sha,'source_root':str(self.source),'frontend_phase':'STAGE_ONLY','stage_scope':a.STAGE_ONLY_SCOPE,'frontend_tree':self.tree,'frontend_input_fingerprint_sha256':'a'*64,'intended_backend_source_sha':'b'*40,'intended_backend_config_sha256':'c'*64,'stage_alias_baseline':{h:'dpl_F0' for h in ('theearnalism.com','www.theearnalism.com')}}
  self.b['stage_request_sha256']=a.digest(a.stage_frontend_request(self.b))
 def actual(self,b=None):
  b=b or self.b;projection=a.stage_only_projection(b)
  return {'scope':'ACTUAL_PROVIDER_AND_SOURCE','qualified':True,'qualification_scope':a.STAGE_ONLY_SCOPE,'auto_deploy':False,'authenticated_provider_account':True,'provider_identity_sha256':'d'*64,'config_sha256':'e'*64,'stage_isolation_sha256':a.digest(projection),'stage_input_projection':projection,'public_aliases':b['stage_alias_baseline'],'cli_version':a.CLI_VERSIONS['vercel']}
 def approval(self,action='stage_frontend',b=None,actual=None):
  b=b or self.b;actual=actual or self.actual(b)
  return {'schema':'earnalism-india-protected-operation.v1','action':action,'binding_sha256':a.digest(b),'project':a.PROJECT,'team':a.TEAM,'railway_project':a.RAILWAY_PROJECT,'service':a.SERVICE,'environment':a.ENVIRONMENT,'territories':['IN'],'auto_deploy':False,'approved':True,'provider_identity_sha256':actual['provider_identity_sha256'],'config_sha256':actual['config_sha256'],a.recovery_digest_field(action,b):actual[a.recovery_digest_field(action,b)],'rollback_operator':'dummy fixture only','approved_at':self.now.isoformat(),'expires_at':(self.now+timedelta(minutes=15)).isoformat(),'provider_observed_at':self.now.isoformat()}
 def fake_run(self,cmd,**kw):
  self.calls.append((cmd,kw));return SimpleNamespace(returncode=0,stdout=json.dumps({'id':'dpl_New'}),stderr='')
 def adapter(self,actual=None):return a.ProviderAdapter(self.journal,owner_authorized=True,observe=lambda action,b:actual or self.actual(b),run=self.fake_run,clock=lambda:self.now)
 def stage(self):return a.ReleaseController(self.adapter()).perform('stage_frontend',self.b,self.approval())
 def result(self,record,outcome='APPLIED'):
  return {'scope':'ACTUAL_PROVIDER_AND_SOURCE','operation_id':record['operation_id'],'action':'stage_frontend','source_sha':self.sha,'outcome':outcome,'receipt_sha256':'f'*64,'deployment_id':'dpl_New','observed_at':self.now.isoformat(),'stage_isolation_observation':{'scope':a.STAGE_ONLY_SCOPE,'project':a.PROJECT,'team':a.TEAM,'deployment':{'id':'dpl_New','projectId':a.PROJECT,'target':'production','readyState':'READY','gitSource':a.stage_frontend_request(self.b)['gitSource']},'aliases':self.b['stage_alias_baseline'],'observed_at':self.now.isoformat()}}
 def reconcile(self,record,actual):return a.ProviderAdapter(self.journal,observe=lambda action,r:actual,run=lambda *x,**y:self.fail('no provider on reconcile'),clock=lambda:self.now).reconcile(record['operation_id'])
 def test_exact_private_stage_request_and_post_isolation(self):
  record=self.stage();self.assertEqual(len(self.calls),1);self.assertEqual(record['state'],'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED')
  body=json.loads((self.journal/(record['operation_id']+'.request.json')).read_text());self.assertIs(body['autoAssignCustomDomains'],False);self.assertEqual(body['gitSource']['sha'],self.sha);self.assertEqual(record['stage_input_projection'],a.stage_only_projection(self.b))
  applied=self.reconcile(record,self.result(record));self.assertEqual(applied['state'],'APPLIED_VERIFIED');self.assertNotIn('guarded_recovery_receipt_sha256',applied);self.assertFalse((self.journal/'_write-barrier.json').exists())
 def test_input_and_approval_mismatch_before_cli(self):
  for key,value in [('stage_request_sha256','9'*64),('frontend_tree','9'*40),('intended_backend_source_sha','latest'),('stage_alias_baseline',{'theearnalism.com':'dpl_F0'})]:
   b={**self.b,key:value}
   with self.subTest(key=key),self.assertRaises(ValueError):self.adapter().perform('stage_frontend',b,self.approval(b=b) if key=='frontend_tree' else self.approval())
  self.assertEqual(self.calls,[])
 def test_source_dirty_denies_and_stage_digest_not_rollback(self):
  self.assertEqual(a.recovery_digest_field('stage_frontend',self.b),'stage_isolation_sha256')
  (self.source/'extra.txt').write_text('dirty')
  with self.assertRaisesRegex(ValueError,'clean'):self.stage()
  self.assertEqual(self.calls,[])
 def test_reader_rollback_boolean_cannot_inflate_stage(self):
  actual=self.actual();actual['frontend_rollback_available']=True
  with self.assertRaisesRegex(ValueError,'must not claim'):self.adapter(actual).perform('stage_frontend',self.b,self.approval())
  self.assertEqual(self.calls,[])
 def test_stage_only_cannot_promote_or_count_frontend_first(self):
  with self.assertRaises(ValueError):a.ReleaseController(self.adapter()).perform('promote_frontend',{**self.b,'deployment_id':'dpl_New'},{})
  record=self.stage();self.reconcile(record,self.result(record))
  with self.assertRaisesRegex(ValueError,'frontend-first'):a.ReleaseController(self.adapter()).perform('release_guarded_bootstrap',{'frontend_deployment_id':'dpl_New','frontend_source_sha':self.sha},{})
 def test_unknown_outcome_keeps_barrier_and_no_replay_or_new_operation(self):
  record=self.stage()
  with self.assertRaises(ValueError):self.reconcile(record,self.result(record,'NOT_APPLIED'))
  self.assertTrue((self.journal/'_write-barrier.json').exists())
  with self.assertRaises(FileExistsError):self.stage()
  b={**self.b,'source_sha':'f'*40};b['stage_request_sha256']=a.digest(a.stage_frontend_request(b))
  with self.assertRaises(FileExistsError):self.adapter().perform('stage_frontend',b,self.approval(b=b))
  self.assertEqual(len(self.calls),1)
 def test_post_identity_alias_scope_time_or_custody_mismatch_keeps_original(self):
  record=self.stage();path=self.journal/(record['operation_id']+'.json');before=path.read_bytes()
  for key in ('source','project','team','candidate','alias','ready','before','future','custody'):
   actual=self.result(record)
   if key=='source':actual['stage_isolation_observation']['deployment']['gitSource']['sha']='f'*40
   if key=='project':actual['stage_isolation_observation']['project']='wrong'
   if key=='team':actual['stage_isolation_observation']['team']='wrong'
   if key=='candidate':actual['deployment_id']='dpl_Other'
   if key=='alias':actual['stage_isolation_observation']['aliases']={h:'dpl_New' for h in self.b['stage_alias_baseline']}
   if key=='ready':actual['stage_isolation_observation']['deployment']['readyState']='ERROR'
   if key=='before':actual['stage_isolation_observation']['observed_at']=(self.now-timedelta(seconds=1)).isoformat()
   if key=='future':actual['observed_at']=actual['stage_isolation_observation']['observed_at']=(self.now+timedelta(seconds=1)).isoformat()
   if key=='custody':
    altered={**record,'operations_journal_identity_sha256':'9'*64};a._durable_json(path,altered)
   with self.subTest(key=key),self.assertRaises(ValueError):self.reconcile(record,actual)
   if key=='custody':path.write_bytes(before);path.chmod(0o600)
   self.assertEqual(path.read_bytes(),before);self.assertTrue((self.journal/'_write-barrier.json').exists())
 def test_request_tamper_after_intent_blocks_transport(self):
  durable=a._durable_json
  def change(path,value,**kw):
   if str(path).endswith('.request.json'):value={**value,'autoAssignCustomDomains':True}
   return durable(path,value,**kw)
  with patch.object(a,'_durable_json',side_effect=change),self.assertRaisesRegex(ValueError,'request changed'):self.stage()
  self.assertEqual(self.calls,[]);self.assertTrue((self.journal/'_write-barrier.json').exists())
 def promotion_binding(self,record):
  return {'source_sha':self.sha,'source_root':str(self.source),'deployment_id':'dpl_New','frontend_phase':'GUARD_ACTIVE','backend_source_sha':'b'*40,'backend_config_sha256':'c'*64,'stage_artifact_reference':{'operation_id':record['operation_id'],'record_sha256':a.digest(record),'reconciliation_receipt_sha256':record['reconciliation_receipt_sha256'],'input_projection_sha256':a.digest(record['stage_input_projection']),'operations_journal_identity_sha256':record['operations_journal_identity_sha256']}}
 def test_immutable_stage_reference_allows_fresh_binding_not_equality(self):
  record=self.stage();record=self.reconcile(record,self.result(record));b=self.promotion_binding(record)
  self.assertNotEqual(b,record['binding']);self.assertEqual(a.validate_stage_artifact_reference(self.journal,b),record)
  for key,value in [('backend_source_sha','c'*40),('backend_config_sha256','d'*64),('deployment_id','dpl_Other')]:
   with self.subTest(key=key),self.assertRaises(ValueError):a.validate_stage_artifact_reference(self.journal,{**b,key:value})
  changed=copy.deepcopy(b);changed['stage_artifact_reference']['record_sha256']='9'*64
  with self.assertRaises(ValueError):a.validate_stage_artifact_reference(self.journal,changed)
 def test_real_controller_promotion_requires_fresh_guard_context_and_original_stage(self):
  record=self.stage();record=self.reconcile(record,self.result(record));b=self.promotion_binding(record)
  b.update(rollback_frontend_source_sha='d'*40,rollback_frontend_deployment_id='dpl_F0')
  actual={**b,'scope':'ACTUAL_PROVIDER_AND_SOURCE','qualified':True,'auto_deploy':False,'authenticated_provider_account':True,
   'provider_identity_sha256':'d'*64,'config_sha256':'e'*64,'frontend_rollback_sha256':'9'*64,
   'frontend_rollback_available':True,'frontend_backend_compatible':True,'rollback_frontend_signed_purchase_ready':True,
   'candidate_id':'dpl_New','candidate_source_sha':self.sha,'candidate_target':'production','candidate_ready':True,
   'health_book_statuses':[200,200],'guest_manifest_status':401,'cli_version':a.CLI_VERSIONS['vercel']}
  approval=self.approval('promote_frontend',b,actual)
  for key in ('rollback_frontend_signed_purchase_ready','frontend_backend_compatible','candidate_ready'):
   with self.subTest(key=key),self.assertRaises(ValueError):a.ReleaseController(self.adapter({**actual,key:False})).perform('promote_frontend',b,approval)
  missing={k:v for k,v in b.items() if k!='stage_artifact_reference'}
  with self.assertRaises(ValueError):a.ReleaseController(self.adapter(actual)).perform('promote_frontend',missing,self.approval('promote_frontend',missing,actual))
  self.assertEqual(len(self.calls),1)
  promoted=a.ReleaseController(self.adapter(actual)).perform('promote_frontend',b,approval)
  self.assertEqual(promoted['state'],'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED');self.assertEqual(len(self.calls),2)
  self.assertEqual(promoted['binding']['stage_artifact_reference']['record_sha256'],a.digest(record))
 def test_legacy_applied_stage_cannot_be_retrofitted(self):
  record=self.stage();record=self.reconcile(record,self.result(record));b=self.promotion_binding(record)
  record.pop('stage_input_projection');a._durable_json(self.journal/(record['operation_id']+'.json'),record);b['stage_artifact_reference']['record_sha256']=a.digest(record)
  with self.assertRaises(ValueError):a.validate_stage_artifact_reference(self.journal,b)

if __name__=='__main__':unittest.main(verbosity=2)
