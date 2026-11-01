"""All provider/admin/public/config channels mocked. No actual metadata reads."""
import sys
sys.dont_write_bytecode=True
import json,unittest,tempfile,hashlib,subprocess,copy
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch,Mock
from scripts import reader612_phase_collectors as p
from scripts.india_release_provider_adapter import CLI_VERSIONS,digest
ID='11111111-1111-1111-1111-111111111111';SNAP='22222222-2222-2222-2222-222222222222';OLD='33333333-3333-3333-3333-333333333333'
class Collect(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'backend').mkdir();(self.root/'frontend').mkdir();(self.root/'backend/railway.json').write_text('{}');(self.root/'frontend/vercel.json').write_text('{"git":{"deploymentEnabled":false}}');(self.root/'backend/server.py').write_text('SYNTHETIC_SOURCE_NOT_APP')
  self.runtime='a'*64;self.dep=ID;self.image='sha256:'+'b'*64;self.calls=[];self.admin_flags={'enabled':False,'multi_replica_enabled':False,'public_metadata_enabled':False};self.public_override={};self.native_override={}
  self.config={'service':{'id':p.SERVICE},'environment':{'id':p.ENVIRONMENT},'latestDeployment':{'id':ID},'staged':None,'stagedChanges':[],'volumes':[],'config':{'syntheticFixtureOnly':True}}
  cfg=digest({'config':self.config['config'],'config_file':hashlib.sha256(b'{}').hexdigest(),'volumes':[]})
  self.n={'baseline_deployment_id':ID,'current_deployment_id':ID,'baseline_image':self.image,'baseline_snapshot':SNAP,'baseline_runtime_sha256':self.runtime,'baseline_source_sha':'4'*40,'source_sha':'5'*40,'tree_sha':'6'*40,'runtime_sha256':'c'*64,'config_sha256':cfg}
  self.u={'runtime_expected_sha256':self.n['runtime_sha256'],'files':[]};self.n['payload_sha256']=digest(self.u);self.P={'purchase_mode':'CLOSED','closed_server_sha256':hashlib.sha256((self.root/'backend/server.py').read_bytes()).hexdigest(),'frontend_deployment_id':'dpl_SYNTHETIC','frontend_source_sha':'7'*40,'current_backend_deployment_id':ID,'current_backend_source_sha':'4'*40,'source_sha':self.n['source_sha'],'source_delivery_sha256':self.n['runtime_sha256'],'config_sha256':cfg,'backend_payload_sha256':digest(self.u)}
  self.expected={'runtime_file_count':1950,'frontend_deployment_id':'dpl_SYNTHETIC','frontend_source_sha':'7'*40,'books':{slug:{k:(slug if k=='slug' else True if k in ('audio_enabled','audiobook_enabled') else 'SYNTHETIC_'+k) for k in p.FIELDS} for slug in p.BOOKS},'provider_binding':self.P,'upload_payload':self.u,'native_binding':self.n,'phase_deployment_id':ID,'role_binding':{}}
  self.expected['covers']={};self.expected['prior_signed_protocol']={}
  self.expected['acceptance_contract']={k:copy.deepcopy(self.expected[k]) for k in ['books','frontend_deployment_id','frontend_source_sha','runtime_file_count','covers','prior_signed_protocol']}
  self.expected['acceptance_contract']['phase_policy']={'role_source_sha':self.n['source_sha'],'role_runtime_sha256':self.n['runtime_sha256'],'baseline_deployment_id':self.n['baseline_deployment_id'],'baseline_runtime_sha256':self.n['baseline_runtime_sha256']}
  self.n['payload_sha256']=digest({'schema':p.BRIDGE_SCHEMA,'upload_payload':self.u,'provider_binding':self.P,'acceptance_contract':self.expected['acceptance_contract']})
  (self.root/'internal/release').mkdir(parents=True);(self.root/'internal/release/reader612_phase_acceptance.json').write_text(json.dumps(self.expected['acceptance_contract']))
  self.c=p.Reader612PhaseCollector(self.root,run=self.run_cli,config_reader=self.describe,public_get=self.get,admin_read=self.admin,clock=lambda:datetime(2026,11,1,12,tzinfo=timezone.utc));self.c._covers_source=Mock(return_value='f'*64);self.c.purchase_probe=Mock(side_effect=AssertionError('NO_PREFLIGHT_POST'))
 def tearDown(self):self.tmp.cleanup()
 def describe(self,**kw):self.assertEqual(kw,{'project_id':p.RAILWAY_PROJECT,'service_id':p.SERVICE,'environment_id':p.ENVIRONMENT});return self.config
 def admin(self,method,url):self.assertEqual((method,url),('GET','https://api.theearnalism.com/api/admin/cache/status'));return 200,json.dumps(self.admin_flags).encode(),{'request_id':'SYNTHETIC-request-1'}
 def get(self,path):
  if path in self.public_override:return self.public_override[path]
  if path=='/api/healthz':body={'status':'ok','deployment':{'deployment_id':self.dep},'runtime_source':{'status':'MEASURED_MATCHES_MANIFEST','observed_sha256':self.runtime,'file_count':1950}}
  elif path=='/api/health':body={'ok':True}
  elif path.startswith('/api/books/'):body=self.expected['books'][path.split('/')[-1]]
  else:return 401,{},b'{}'
  return 200,{},json.dumps(body).encode()
 def run_cli(self,argv,**kw):
  self.calls.append(argv)
  if argv[-1]=='--version':return subprocess.CompletedProcess(argv,0,CLI_VERSIONS[argv[0]],'')
  if argv[:2]==['railway','logs']:
   if '--http' in argv:return subprocess.CompletedProcess(argv,0,json.dumps({'requestId':argv[argv.index('--request-id')+1],'deploymentId':self.dep,'deploymentInstanceId':'SYNTHETIC-instance','timestamp':'2026-11-01T11:59:59Z','httpStatus':200,'method':'GET','path':'/api/admin/cache/status'}),'')
   rows=[{'timestamp':'2026-11-01T11:59:10Z','message':x} for x in ['INFO:     Application startup complete.',p.DISABLED,'Startup database maintenance suppressed (acceptance_containment=False).']];return subprocess.CompletedProcess(argv,0,'\n'.join(json.dumps(x) for x in rows),'')
  if argv[:2]==['railway','api']:
   q=argv[2]
   if 'deployment(id:' not in q:return subprocess.CompletedProcess(argv,0,json.dumps({'data':{'serviceInstance':{'latestDeployment':{'id':self.dep,'status':'SUCCESS'}}}}),'')
   requested=q.split('deployment(id:"')[1].split('"')[0]
   native={'id':requested,'status':'SUCCESS','projectId':p.RAILWAY_PROJECT,'serviceId':p.SERVICE,'environmentId':p.ENVIRONMENT,'snapshotId':SNAP,'canRollback':True,'canRedeploy':True,'createdAt':'2026-11-01T11:59:00Z','meta':{'imageDigest':self.image,'rootDirectory':'/backend','configFile':'/backend/railway.json','fileServiceManifest':{'build':{'builder':'DOCKERFILE'},'deploy':{'healthcheckPath':'/healthz','multiRegionConfig':{'sfo':{'numReplicas':1}}}}}}
   native.update(self.native_override);body={'data':{'deployment':native,'serviceInstance':{'latestDeployment':{'id':self.dep,'status':'SUCCESS'}},'deploymentTriggers':{'edges':[],'pageInfo':{'hasNextPage':False}}}}
  elif '/v9/projects/' in argv[2]:body={'id':p.PROJECT,'accountId':p.TEAM,'gitProviderOptions':{'createDeployments':'disabled'}}
  elif '/v4/aliases/' in argv[2]:body={'deploymentId':self.expected['frontend_deployment_id']}
  else:body={'readyState':'READY','gitSource':{'sha':self.expected['frontend_source_sha']}}
  return subprocess.CompletedProcess(argv,0,json.dumps(body),'')
 def common(self):return self.c._common(ID,self.runtime,self.n['config_sha256'],self.expected)
 def test_actual_method_synthetic_common_facts(self):
  x=self.common();self.assertEqual(x['native']['image'],self.image);self.assertEqual(x['runtime_flags']['scope'],'SANDWICHED_OBSERVED_PROCESS_ONLY_NOT_ALL_REPLICAS');self.assertTrue(all(a[:2] in (['railway','api'],['railway','logs'],['vercel','api']) or a[-1]=='--version' for a in self.calls))
 def test_missing_config_or_admin_capability_denies(self):
  self.c.config_reader=None
  with self.assertRaisesRegex(ValueError,'CONFIG_CHANNEL_UNBOUND'):self.common()
  self.c.config_reader=self.describe;self.c.admin_read=None
  with self.assertRaisesRegex(ValueError,'ADMIN_RUNTIME_CHANNEL_UNBOUND'):self.common()
 def test_unknown_or_enabled_or401_admin_denies(self):
  for value in [True,None,'false']:
   self.admin_flags['public_metadata_enabled']=value
   with self.subTest(value=value),self.assertRaises(ValueError):self.common()
  self.c.admin_read=lambda *a:(401,b'{}')
  with self.assertRaises(ValueError):self.common()
 def test_runtime_config_target_and_retention_drift_denies(self):
  for change in [{'status':'REMOVED'},{'canRollback':False},{'environmentId':'wrong'},{'meta':{}}]:
   self.native_override=change
   with self.subTest(change=change),self.assertRaises((ValueError,KeyError)):self.common()
  self.native_override={};self.config['config']['changed']=True
  with self.assertRaises(ValueError):self.common()
 def test_health_source_drift_denies(self):
  self.runtime='d'*64
  with self.assertRaises(ValueError):self.c._common(ID,'a'*64,self.n['config_sha256'],self.expected)
 def test_admin_sandwich_drift_denies(self):
  old=self.admin
  def drift(*args):self.runtime='d'*64;return old(*args)
  self.c.admin_read=drift
  with self.assertRaises(ValueError):self.common()
 def test_public_package_or_guest_access_drift_denies(self):
  self.public_override['/api/books/the-selfish-giant']=(200,{},b'{}')
  with self.assertRaises(ValueError):self.common()
  self.public_override={};self.public_override['/api/reader/book/the-selfish-giant/audiobook/manifest']=(200,{},b'{}')
  with self.assertRaises(ValueError):self.common()
 def test_preflight_composition_U_P_N_and_source(self):
  source={'source_sha':self.n['source_sha'],'tree_sha':self.n['tree_sha'],'runtime_sha256':self.n['runtime_sha256'],'payload_membership_sha256':hashlib.sha256(b'[]').hexdigest(),'payload_files':0}
  with patch.object(self.c,'_flag_source_equivalence'),patch.object(self.c,'_baseline_source'),patch.object(self.c,'_signed_frontend_compatibility',return_value='f'*64),patch.object(p,'qualify_binding',return_value=source):
   x=self.c.collect_preflight(self.n,{},self.expected);self.assertEqual(x['binding_sha256'],digest(self.n));self.assertTrue(x['provider_actual']['frontend_signed_purchase_ready']);self.assertTrue(x['provider_actual']['qualified'])
   self.u['runtime_expected_sha256']='f'*64
   with self.assertRaises(ValueError):self.c.collect_preflight(self.n,{},self.expected)
 def closed(self):
  self.P['current_backend_deployment_id']=OLD;self.n['baseline_deployment_id']=OLD;self.n['current_deployment_id']=OLD
  self.expected['acceptance_contract']['phase_policy']['baseline_deployment_id']=OLD
  (self.root/'internal/release/reader612_phase_acceptance.json').write_text(json.dumps(self.expected['acceptance_contract']))
  self.n['payload_sha256']=digest({'schema':p.BRIDGE_SCHEMA,'upload_payload':self.u,'provider_binding':self.P,'acceptance_contract':self.expected['acceptance_contract']})
  return {'action':'release_guarded_bootstrap','state':'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED','binding':dict(self.P),'operation_id':'e'*64,'started_at':'2026-11-01T11:58:00+00:00'}
 def test_closed_missing_probe_or_wrong_phase_denies(self):
  self.c.purchase_probe=None
  with self.assertRaisesRegex(ValueError,'CLOSED_PROBE_UNBOUND'):self.c.collect_closed(self.closed(),self.expected)
  record=self.closed();record['state']='APPLIED_VERIFIED'
  with self.assertRaises(ValueError):self.c.collect_closed(record,self.expected,purchase_probe=lambda *a,**kw:None)
 def test_closed_real_methods_mock_probe_and_source_only(self):
  self.runtime=self.n['runtime_sha256'];r=self.closed();source={'source_sha':self.n['source_sha'],'tree_sha':self.n['tree_sha'],'runtime_sha256':self.runtime}
  probe=lambda *a,**kw:(503,{'cache-control':'no-store'},b'{"detail":{"code":"PURCHASE_INITIATION_CLOSED"}}')
  with patch.object(p,'qualify_binding',return_value=source),patch('scripts.purchase_guard_source.validate',return_value=({'state':'CLOSED'},b'',(self.root/'backend/server.py').read_bytes())):
   x=self.c.collect_closed(r,self.expected,purchase_probe=probe);self.assertEqual(x['snapshot_id'],SNAP);self.assertEqual(x['purchase_pause_proof'],'MEASURED_EXACT_EARLY_RETURN_AND_ANONYMOUS_503')
   with self.assertRaises(ValueError):self.c.collect_closed(r,self.expected,purchase_probe=lambda *a,**kw:(401,{},b'{}'))
 def test_restore_does_not_trust_favorable_retention_boolean(self):
  r={'action':'restore_original_native_after_reader612_qualification','state':'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED','binding':self.n,'operation_id':'e'*64,'started_at':'2026-11-01T11:58:00+00:00'}
  self.expected['qualified_recovery']={'qualified':True}
  with patch.object(self.c,'_baseline_source'),self.assertRaises((ValueError,KeyError)):self.c.collect_restored(r,self.expected)
 def test_restore_mocked_qualified_journal_still_checks_native_image(self):
  r={'action':'restore_original_native_after_reader612_qualification','state':'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED','binding':self.n,'operation_id':'e'*64,'started_at':'2026-11-01T11:58:00+00:00'}
  q={'deployment_id':OLD,'snapshot_id':SNAP,'retained_image_id':self.image,'recovery_receipt_sha256':'f'*64}
  self.expected['qualified_recovery']=q
  r['binding']={**self.n,'current_deployment_id':OLD,'payload_sha256':digest({'schema':'earnalism.reader612-reviewed-restore.v1','upload_payload':self.u,'bootstrap_provider_binding':self.P,'acceptance_contract':self.expected['acceptance_contract'],'qualified_native_receipt_sha256':q['recovery_receipt_sha256']})}
  with patch.object(self.c,'_baseline_source'),patch.object(self.c,'_qualified_recovery',return_value=q):
   x=self.c.collect_restored(r,self.expected);self.assertEqual(x['restored_runtime_sha256'],self.n['baseline_runtime_sha256'])
   q['retained_image_id']='sha256:'+'f'*64
   with self.assertRaises(ValueError):self.c.collect_restored(r,self.expected)
 def test_bare_admin_body_cannot_prove_same_deployment(self):
  self.c.admin_read=lambda *a:(200,json.dumps(self.admin_flags).encode())
  with self.assertRaisesRegex(ValueError,'ADMIN_ROUTING_ATTESTATION_UNAVAILABLE'):self.common()
 def test_covered_acceptance_override_and_envelope_mutation_deny(self):
  self.expected['frontend_source_sha']='9'*40
  with self.assertRaisesRegex(ValueError,'Acceptance override'):self.c.collect_preflight(self.n,{},self.expected)
  self.expected['frontend_source_sha']='7'*40;self.expected['acceptance_contract']['runtime_file_count']=999
  with self.assertRaisesRegex(ValueError,'envelope'):self.c.collect_preflight(self.n,{},self.expected)
 def test_old_or_unrecognized_startup_log_denies(self):
  original=self.run_cli
  def old(argv,**kw):
   result=original(argv,**kw)
   if argv[:2]==['railway','logs']:result.stdout=result.stdout.replace('11:59:10','10:00:00')
   return result
  self.c.run=old
  with self.assertRaisesRegex(ValueError,'Startup timestamp'):self.common()
 def test_actual_phase_identity_cannot_be_hint_or_old_baseline(self):
  self.expected['phase_deployment_id']=OLD
  with self.assertRaisesRegex(ValueError,'phase hint'):self.c._phase_deployment(self.closed(),self.expected)
 def test_actual_qualified_receipt_method_checks_hash_and_journal(self):
  self.runtime=self.n['runtime_sha256'];r=self.closed();source={'source_sha':self.n['source_sha'],'tree_sha':self.n['tree_sha'],'runtime_sha256':self.runtime}
  with patch.object(p,'qualify_binding',return_value=source),patch('scripts.purchase_guard_source.validate',return_value=({'state':'CLOSED'},b'',(self.root/'backend/server.py').read_bytes())):
   q=self.c.collect_closed(r,self.expected,purchase_probe=lambda *a,**kw:(503,{'cache-control':'no-store'},b'{"detail":{"code":"PURCHASE_INITIATION_CLOSED"}}'))
  self.expected['qualified_recovery']=q;restore={'binding':self.n}
  journal={'state':'APPLIED_VERIFIED','action':'release_guarded_bootstrap','binding':{'source_sha':self.n['source_sha']},'guarded_recovery_receipt_sha256':q['recovery_receipt_sha256'],'reconciliation_receipt_sha256':q['receipt_sha256']}
  with patch('scripts.india_release_provider_adapter._read_journal',return_value=journal):
   self.assertEqual(self.c._qualified_recovery(restore,self.expected),q)
   q['retained_image_id']='sha256:'+'e'*64
   with self.assertRaisesRegex(ValueError,'canonical digest'):self.c._qualified_recovery(restore,self.expected)
 def test_admin_actual_request_log_wrong_deployment_or_schema_denies(self):
  original=self.run_cli
  for change in [{'deploymentId':OLD},{'requestId':'unrelated'},{'deploymentInstanceId':''},{'path':'/api/books/x'},{'httpStatus':401}]:
   def wrong(argv,**kw):
    result=original(argv,**kw)
    if '--http' in argv:result.stdout=json.dumps({**json.loads(result.stdout),**change})
    return result
   self.c.run=wrong
   with self.subTest(change=change),self.assertRaisesRegex(ValueError,'ADMIN_ROUTING_ATTESTATION_UNAVAILABLE'):self.common()
 def test_source_aware_prefixed_redis_log_and_trailing_mutation(self):
  original=self.run_cli
  for ending,allowed in [(p.DISABLED,True),(p.DISABLED+' altered',False)]:
   def prefixed(argv,**kw):
    result=original(argv,**kw)
    if argv[:2]==['railway','logs'] and '--http' not in argv:result.stdout=result.stdout.replace(p.DISABLED,'2026-11-01 11:59:10,000 - server - INFO - '+ending)
    return result
   self.c.run=prefixed
   if allowed:self.common()
   else:
    with self.assertRaises(ValueError):self.common()
 def test_repository_acceptance_not_caller_dictionary(self):
  (self.root/'internal/release/reader612_phase_acceptance.json').write_text('{}')
  with self.assertRaisesRegex(ValueError,'reviewed repository'):self.c.collect_preflight(self.n,{},self.expected)
 def test_cover_contract_actual_method_bound_git_objects(self):
  raw=b'SYNTHETIC_NOT_IMAGE';covers={}
  for slug in p.BOOKS:
   for field in ('cover_url','back_cover_url'):
    path='/assets/books/'+slug+'/'+field+'.webp';self.expected['books'][slug][field]='https://theearnalism.com'+path;covers[slug+':'+field]={'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
  self.expected['covers']=covers
  with patch.object(p.subprocess,'check_output',return_value=raw) as read:
   p.Reader612PhaseCollector._covers_source(self.c,self.expected);self.assertEqual(read.call_count,4)
   covers['the-selfish-giant:cover_url']['path']='/assets/books/../secret'
   with self.assertRaises(ValueError):p.Reader612PhaseCollector._covers_source(self.c,self.expected)
 def test_equivalent_fresh_request_ids_do_not_mutate_protected_digest(self):
  source={'source_sha':self.n['source_sha'],'tree_sha':self.n['tree_sha'],'runtime_sha256':self.n['runtime_sha256'],'payload_membership_sha256':hashlib.sha256(b'[]').hexdigest(),'payload_files':0};counter=[0]
  def admin(*a):
   counter[0]+=1;return 200,json.dumps({**self.admin_flags,'nonsecret_counter':counter[0]}).encode(),{'request_id':'SYNTHETIC-'+str(counter[0])}
  self.c.admin_read=admin
  with patch.object(self.c,'_flag_source_equivalence'),patch.object(self.c,'_baseline_source'),patch.object(self.c,'_signed_frontend_compatibility',return_value='f'*64),patch.object(p,'qualify_binding',return_value=source):
   one=self.c.collect_preflight(self.n,{},self.expected);two=self.c.collect_preflight(self.n,{},self.expected)
   self.assertEqual(one['bootstrap_preflight_sha256'],two['bootstrap_preflight_sha256']);self.assertNotEqual(one['actual_facts_sha256'],two['actual_facts_sha256'])
 def test_restore_preflight_reuses_stored503_and_retained_not_latest_baseline(self):
  self.runtime=self.n['runtime_sha256'];r=self.closed();source={'source_sha':self.n['source_sha'],'tree_sha':self.n['tree_sha'],'runtime_sha256':self.runtime,'payload_membership_sha256':hashlib.sha256(b'[]').hexdigest(),'payload_files':0}
  probe=Mock(return_value=(503,{'cache-control':'no-store'},b'{"detail":{"code":"PURCHASE_INITIATION_CLOSED"}}'))
  with patch.object(p,'qualify_binding',return_value=source),patch('scripts.purchase_guard_source.validate',return_value=({'state':'CLOSED'},b'',(self.root/'backend/server.py').read_bytes())):
   q=self.c.collect_closed(r,self.expected,purchase_probe=probe)
  self.assertEqual(self.c._artifact_receipt(q),self.c._artifact_receipt({**q,'actual_facts_sha256':'f'*64,'observed_at':'different'}))
  Nr={**self.n,'current_deployment_id':q['deployment_id'],'payload_sha256':digest({'schema':'earnalism.reader612-reviewed-restore.v1','upload_payload':self.u,'bootstrap_provider_binding':self.P,'acceptance_contract':self.expected['acceptance_contract'],'qualified_native_receipt_sha256':q['recovery_receipt_sha256']})}
  j={'state':'APPLIED_VERIFIED','action':'release_guarded_bootstrap','binding':{'source_sha':self.n['source_sha']},'guarded_recovery_receipt_sha256':q['recovery_receipt_sha256'],'reconciliation_receipt_sha256':q['receipt_sha256']};self.c.purchase_probe=Mock(side_effect=AssertionError('NO_REPEAT_POST'))
  with patch.object(self.c,'_baseline_source'),patch.object(self.c,'_flag_source_equivalence'),patch.object(self.c,'_signed_frontend_compatibility',return_value='f'*64),patch.object(p,'qualify_binding',return_value=source),patch('scripts.india_release_provider_adapter._read_journal',return_value=j):
   result=self.c.collect_restore_preflight(Nr,q,self.expected);self.assertFalse(result['POST_repeated']);self.assertTrue(result['baseline_can_rollback']);self.assertEqual(result['current_deployment_id'],ID);self.c.purchase_probe.assert_not_called()
   Nr['payload_sha256']='0'*64
   with self.assertRaisesRegex(ValueError,'Restore source/payload'):self.c.collect_restore_preflight(Nr,q,self.expected)
 def test_native_restore_scalar_schema_projection(self):
  field={'name':'deploymentRollback','args':[{'name':'id','type':{'kind':'NON_NULL','name':None,'ofType':{'kind':'SCALAR','name':'String'}}}],'type':{'kind':'NON_NULL','name':None,'ofType':{'kind':'SCALAR','name':'Boolean'}}}
  def read(argv,**kw):
   self.assertTrue(argv[2].startswith('query { __type'));return subprocess.CompletedProcess(argv,0,json.dumps({'data':{'__type':{'fields':[field]}}}),'')
  self.c.run=read;self.assertEqual(self.c.restore_schema(),{'name':'deploymentRollback','argument':{'name':'id','type':'String!'},'return':'Boolean!'})
  field['type']['ofType']['name']='Deployment'
  with self.assertRaises(ValueError):self.c.restore_schema()
 def test_future_probe_channel_missing_prevents_provider_qualification(self):
  self.c.purchase_probe=None;source={'source_sha':self.n['source_sha'],'tree_sha':self.n['tree_sha'],'runtime_sha256':self.n['runtime_sha256'],'payload_membership_sha256':hashlib.sha256(b'[]').hexdigest(),'payload_files':0}
  with patch.object(self.c,'_flag_source_equivalence'),patch.object(self.c,'_baseline_source'),patch.object(self.c,'_signed_frontend_compatibility',return_value='f'*64),patch.object(p,'qualify_binding',return_value=source):
   proof=self.c.collect_preflight(self.n,{},self.expected);self.assertFalse(proof['provider_actual']['qualified']);self.assertIn('CLOSED_PHASE_PROBE_CHANNEL_UNBOUND_PREWRITE_HOLD',proof['holds'])
 def test_maintenance_phrase_in_unrelated_request_log_not_startup_proof(self):
  original=self.run_cli
  def unrelated(argv,**kw):
   result=original(argv,**kw)
   if argv[:2]==['railway','logs'] and '--http' not in argv:
    rows=[json.loads(x) for x in result.stdout.splitlines()]
    rows[-1]['message']='{"user_agent":"Startup database maintenance suppressed (acceptance_containment=False)."}'
    result.stdout='\n'.join(json.dumps(x) for x in rows)
   return result
  self.c.run=unrelated
  with self.assertRaises(ValueError):self.common()
 def test_admin_routing_timestamp_missing_stale_future_or_naive_denies(self):
  original=self.run_cli
  for timestamp in ['', '2026-11-01T11:44:59Z','2026-11-01T12:00:01Z','2026-11-01T11:59:59']:
   def transport(argv,**kw):
    result=original(argv,**kw)
    if '--http' in argv:
     row=json.loads(result.stdout);row['timestamp']=timestamp;result.stdout=json.dumps(row)
    return result
   self.c.run=transport
   with self.subTest(timestamp=timestamp),self.assertRaises(ValueError):self.common()
if __name__=='__main__':unittest.main()
