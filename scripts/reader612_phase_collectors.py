"""Fixed read-only EG2/EG3 collectors; no entry point, writes or approval creation.

The config connector and optional future anonymous CLOSED probe are trusted I/O
capabilities, not caller-provided favorable proof dictionaries. Missing capability
fails closed. Unit tests replace all I/O with synthetic transport responses.
"""
from datetime import datetime,timezone,timedelta
from pathlib import Path
import hashlib,json,re,urllib.request,ast,subprocess
from scripts.india_release_observer import NativeMetadataObserver
from scripts.india_release_provider_adapter import PROJECT,TEAM,RAILWAY_PROJECT,SERVICE,ENVIRONMENT,digest
from scripts.reader612_recovery_source import qualify_binding
UUID=re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')
HASH=re.compile(r'^[a-f0-9]{64}$')
BOOKS=('the-selfish-giant','the-open-window')
BRIDGE_SCHEMA='earnalism.reader612-reviewed-bridge.v1'
FIELDS=('slug','audio_enabled','audiobook_enabled','audiobook_delivery_mode','audiobook_package_version','audiobook_duration_ms','cover_url','back_cover_url')
DISABLED='Redis cache/state disabled; using per-process local cache and rate-limit state.'
def need(ok,message):
 if not ok:raise ValueError(message)
class _NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
def default_public_get(path):
 # Only ordinary anonymous fixed destinations, no forged country/auth headers.
 if path in ('/api/healthz','/api/health'):url='https://api.theearnalism.com'+path
 elif path in tuple('/api/books/'+s for s in BOOKS)+tuple('/api/reader/book/'+s+'/audiobook/manifest' for s in BOOKS):url='https://theearnalism.com'+path
 else:raise ValueError('Public route not allowlisted')
 try:
  with urllib.request.build_opener(_NoRedirect()).open(url,timeout=25) as r:return r.status,dict(r.headers),r.read(1048577)
 except urllib.error.HTTPError as r:return r.code,dict(r.headers),r.read(1048577)
def normal_frontend_closed_probe(method,url,body,*,phase_identity=None):
 # Future authorized phase only; collector calls this after exact CLOSED proof.
 need((method,url,body)==('POST','https://theearnalism.com/api/payments/topup',b'{}'),'Only fixed anonymous normal frontend CLOSED probe admitted')
 request=urllib.request.Request(url,data=body,method=method,headers={'Content-Type':'application/json'})
 try:
  with urllib.request.build_opener(_NoRedirect()).open(request,timeout=25) as response:return response.status,dict(response.headers),response.read(65537)
 except urllib.error.HTTPError as response:return response.code,dict(response.headers),response.read(65537)
class Reader612PhaseCollector(NativeMetadataObserver):
 def __init__(self,source_root,*,run,config_reader=None,public_get=default_public_get,admin_read=None,role_source_root=None,purchase_probe=None,clock=lambda:datetime.now(timezone.utc)):
  super().__init__(source_root,run=run,clock=clock);self.config_reader=config_reader;self.public_get=public_get;self.admin_read=admin_read;self.role_source_root=Path(role_source_root).resolve() if role_source_root else self.source_root;self.purchase_probe=purchase_probe
 def _json_get(self,path,status=200):
  s,headers,raw=self.public_get(path);need(s==status and len(raw)<=1048576,'Unexpected public response/size')
  return json.loads(raw) if status==200 else None
 def _native(self,deployment):
  need(isinstance(deployment,str) and UUID.fullmatch(deployment),'Exact native deployment required')
  q=('query { deployment(id:"'+deployment+'") {id status projectId serviceId environmentId snapshotId canRollback canRedeploy createdAt meta} '
     'serviceInstance(environmentId:"'+ENVIRONMENT+'",serviceId:"'+SERVICE+'") {latestDeployment {id status}} '
     'deploymentTriggers(projectId:"'+RAILWAY_PROJECT+'",environmentId:"'+ENVIRONMENT+'",serviceId:"'+SERVICE+'",first:100) {edges {node {id}} pageInfo {hasNextPage}} }')
  raw=self._read(['railway','api',q,'--compact']);need(not raw.get('errors'),'Native read failed; no retry');d=raw['data'];x=d['deployment']
  need((x['id'],x['projectId'],x['serviceId'],x['environmentId'])==(deployment,RAILWAY_PROJECT,SERVICE,ENVIRONMENT),'Wrong native target')
  need(x['status']=='SUCCESS' and x['canRollback'] is True and x['canRedeploy'] is True and UUID.fullmatch(x['snapshotId'] or ''),'Native retained image capability missing')
  need(d['serviceInstance']['latestDeployment']=={'id':deployment,'status':'SUCCESS'},'Current phase deployment mismatch')
  need(d['deploymentTriggers']['edges']==[] and d['deploymentTriggers']['pageInfo']['hasNextPage'] is False,'Native auto-deploy unqualified')
  meta=x['meta'];need(isinstance(meta,dict) and re.fullmatch(r'sha256:[a-f0-9]{64}',meta.get('imageDigest','')),'Actual native image missing')
  manifest=meta.get('fileServiceManifest');need(isinstance(manifest,dict),'Native file config missing')
  need(meta.get('rootDirectory')=='/backend' and meta.get('configFile')=='/backend/railway.json','Native source/config path mismatch')
  need(manifest.get('build',{}).get('builder')=='DOCKERFILE' and manifest.get('deploy',{}).get('healthcheckPath')=='/healthz' and manifest['deploy'].get('multiRegionConfig')=={'sfo':{'numReplicas':1}},'Actual health/replica file config unqualified')
  return {'id':x['id'],'snapshot':x['snapshotId'],'image':meta['imageDigest'],'created_at':x['createdAt'],'file_config_sha256':digest(manifest)}
 def _config(self,deployment,expected):
  need(callable(self.config_reader),'CONFIG_CHANNEL_UNBOUND: existing authenticated describe_service reader required')
  # Exact fixed target callback; never accept a caller-supplied reviewed=True blob.
  raw=self.config_reader(project_id=RAILWAY_PROJECT,service_id=SERVICE,environment_id=ENVIRONMENT)
  need(raw['service']['id']==SERVICE and raw['environment']['id']==ENVIRONMENT,'Connector target mismatch')
  need(raw['latestDeployment']['id']==deployment and raw.get('staged') is None and raw.get('stagedChanges')==[] and raw.get('volumes')==[],'Config staged/volume/deployment mismatch')
  filehash=hashlib.sha256((self.role_source_root/'backend/railway.json').read_bytes()).hexdigest()
  observed=digest({'config':raw['config'],'config_file':filehash,'volumes':[]})
  need(observed==expected,'Current config digest mismatch')
  return observed
 def _startup(self,deployment,created_at):
  argv=['railway','logs',deployment,'--project',RAILWAY_PROJECT,'--service',SERVICE,'--environment',ENVIRONMENT,'--deployment','--filter','"Application startup complete" OR "Startup database maintenance suppressed" OR "Redis cache/state disabled"','--lines','50','--json']
  result=self.run(argv,cwd=self.source_root,capture_output=True,text=True,timeout=30,check=False)
  need(result.returncode==0 and len(result.stdout)<=262144,'Startup channel missing/oversized; no retry')
  rows=[json.loads(s) for s in result.stdout.splitlines() if s.strip()];kept=[]
  for x in rows:
   msg=x.get('message','')
   suffix=msg[-len(DISABLED):] if msg.endswith(DISABLED) else ''
   prefix=msg[:-len(DISABLED)] if suffix else ''
   redis_off=msg==DISABLED or (suffix==DISABLED and re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - (?:backend\.)?server - INFO - ',prefix) is not None)
   normalized=re.sub(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - (?:backend\.)?server - INFO - ','',msg)
   suppressed=re.fullmatch(r'Startup database maintenance suppressed \(acceptance_containment=(?:True|False)\)\.',normalized) is not None
   if msg=='INFO:     Application startup complete.' or redis_off or suppressed:
    t=datetime.fromisoformat(x['timestamp'].replace('Z','+00:00'));born=datetime.fromisoformat(created_at.replace('Z','+00:00'));need(t.tzinfo is not None and born.tzinfo is not None and born<=t<=self.clock(),'Startup timestamp unbound/old/future');kept.append({'timestamp':t.isoformat(),'kind':'redis_off' if redis_off else 'startup' if msg=='INFO:     Application startup complete.' else 'maintenance_suppressed'})
  need({x['kind'] for x in kept}=={'startup','redis_off','maintenance_suppressed'},'Actual startup/DB-maintenance/Redis-OFF unavailable')
  return digest({'deployment':deployment,'events':kept})
 def _frontend(self,expected):
  x=self._read(['vercel','api','/v9/projects/'+PROJECT,'--method','GET','--raw','--scope',TEAM])
  need(x.get('id')==PROJECT and x.get('accountId')==TEAM and x.get('gitProviderOptions',{}).get('createDeployments')=='disabled','Vercel suppression unknown/enabled')
  need(json.loads((self.source_root/'frontend/vercel.json').read_text())['git']['deploymentEnabled'] is False,'Repository suppression unknown/enabled')
  aliases={host:self._read(['vercel','api','/v4/aliases/'+host,'--method','GET','--raw','--scope',TEAM])['deploymentId'] for host in ('theearnalism.com','www.theearnalism.com')}
  need(set(aliases.values())=={expected['frontend_deployment_id']},'Alias phase mismatch')
  front=self._read(['vercel','api','/v13/deployments/'+expected['frontend_deployment_id'],'--method','GET','--raw','--scope',TEAM])
  source=front.get('gitSource',{}).get('sha') or front.get('meta',{}).get('githubCommitSha')
  need(front.get('readyState')=='READY' and source==expected['frontend_source_sha'],'Frontend source unknown/mismatch')
  return aliases
 def _public(self,expected):
  need(set(expected['books'])==set(BOOKS),'Exact retained book bindings required');books={}
  for slug in BOOKS:
   book=self._json_get('/api/books/'+slug);projection={k:book.get(k) for k in FIELDS}
   need(projection==expected['books'][slug],'Actual book/package/cover drift')
   self._json_get('/api/reader/book/'+slug+'/audiobook/manifest',status=401);books[slug]=projection
  return books
 def _runtime_flags(self,deployment,runtime,native):
  need(callable(self.admin_read),'ADMIN_RUNTIME_CHANNEL_UNBOUND_HOLD')
  response=self.admin_read('GET','https://api.theearnalism.com/api/admin/cache/status')
  need(isinstance(response,tuple) and len(response)==3,'ADMIN_ROUTING_ATTESTATION_UNAVAILABLE')
  status,raw,transport=response
  need(isinstance(transport,dict) and set(transport)=={'request_id'} and isinstance(transport['request_id'],str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}',transport['request_id']),'ADMIN_ROUTING_ATTESTATION_UNAVAILABLE')
  request_id=transport['request_id']
  argv=['railway','logs','--http','--request-id',request_id,'--project',RAILWAY_PROJECT,'--service',SERVICE,'--environment',ENVIRONMENT,'--lines','5','--json']
  routing=self.run(argv,cwd=self.source_root,capture_output=True,text=True,timeout=30,check=False)
  need(routing.returncode==0 and len(routing.stdout)<=32768,'ADMIN_ROUTING_ATTESTATION_UNAVAILABLE')
  rows=[json.loads(line) for line in routing.stdout.splitlines() if line.strip()]
  need(len(rows)==1,'ADMIN_ROUTING_ATTESTATION_UNAVAILABLE')
  event=rows[0]
  need(event.get('requestId')==request_id and event.get('deploymentId')==deployment and event.get('method')=='GET' and event.get('path')=='/api/admin/cache/status' and type(event.get('httpStatus')) is int and event['httpStatus']==200 and isinstance(event.get('deploymentInstanceId'),str) and bool(event['deploymentInstanceId']),'ADMIN_ROUTING_ATTESTATION_UNAVAILABLE')
  observed=datetime.fromisoformat(event.get('timestamp','').replace('Z','+00:00'));now=self.clock()
  need(observed.tzinfo is not None and timedelta(0)<=now-observed<=timedelta(minutes=15),'ADMIN_ROUTING_ATTESTATION_STALE_OR_UNBOUND')
  route={k:event[k] for k in ('requestId','deploymentId','deploymentInstanceId','httpStatus','method','path','timestamp')}
  need(status==200 and isinstance(raw,bytes) and len(raw)<=1048576,'ADMIN_RUNTIME_CHANNEL_UNBOUND_HOLD')
  flags=json.loads(raw)
  # public_metadata_enabled is an OR-derived effective state, not an independent
  # raw flag. False plus both other False proves all three are false.
  need(all(flags.get(k) is False for k in ('enabled','multi_replica_enabled','public_metadata_enabled')),'Actual effective Redis state not all OFF')
  after=self._json_get('/api/healthz');again=self._native(deployment)
  need(after.get('status')=='ok' and after['deployment']['deployment_id']==deployment and after['runtime_source']['status']=='MEASURED_MATCHES_MANIFEST' and after['runtime_source']['observed_sha256']==runtime and again==native,'Admin observed-process identity drift')
  return {'scope':'SANDWICHED_OBSERVED_PROCESS_ONLY_NOT_ALL_REPLICAS','effective_all_three_off':True,'routing_log_sha256':digest(route),'observed_deployment_instance_id':route['deploymentInstanceId'],'admin_response_sha256':hashlib.sha256(raw).hexdigest()}
 def _flag_source_equivalence(self,binding):
  baseline=subprocess.check_output(['git','-c','remote.origin.promisor=false','show',binding['baseline_source_sha']+':backend/server.py'],cwd=self.role_source_root,text=True,timeout=30,env={**__import__('os').environ,'GIT_NO_LAZY_FETCH':'1'})
  def controls(text):
   wanted={'MULTI_REPLICA_ENABLED','REDIS_URL','REDIS_CACHE_ENABLED','REDIS_PUBLIC_METADATA_ENABLED'};out={}
   for node in ast.parse(text).body:
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in {'_env_bool','_redis_state_enabled','admin_cache_status'}:out[node.name]=ast.dump(node,include_attributes=False)
    if isinstance(node,ast.Assign):
     for target in node.targets:
      if isinstance(target,ast.Name) and target.id in wanted:out[target.id]=ast.dump(node,include_attributes=False)
   need(set(out)==wanted|{'_env_bool','_redis_state_enabled','admin_cache_status'},'Flag/source endpoint schema missing')
   return out
  need(controls(baseline)==controls((self.role_source_root/'backend/server.py').read_text()),'Flag or admin response source semantics changed')
 def _covers_source(self,expected):
  covers=expected['covers'];need(set(covers)=={slug+':'+field for slug in BOOKS for field in ('cover_url','back_cover_url')},'Exact cover contract required')
  for key,fact in covers.items():
   slug,field=key.split(':');path=fact['path']
   need(isinstance(path,str) and path.startswith('/assets/books/') and '..' not in path.split('/') and expected['books'][slug][field]=='https://theearnalism.com'+path and HASH.fullmatch(fact['sha256']) and type(fact['bytes']) is int and 0<fact['bytes']<=2097152,'Cover path/source binding invalid')
   raw=subprocess.check_output(['git','-c','remote.origin.promisor=false','show',expected['frontend_source_sha']+':frontend/public'+path],cwd=self.source_root,timeout=30,env={**__import__('os').environ,'GIT_NO_LAZY_FETCH':'1'})
   need(len(raw)==fact['bytes'] and hashlib.sha256(raw).hexdigest()==fact['sha256'],'Cover source bytes changed')
  return digest({'scope':'DEPLOYED_GIT_SOURCE_COVER_BINDING_NOT_HTTP_BYTE_REPLAY','covers':covers})
 def _common(self,deployment,runtime,config,expected):
  self.verify_versions();native=self._native(deployment);cfg=self._config(deployment,config);logs=self._startup(deployment,native['created_at'])
  h=self._json_get('/api/healthz');need(h.get('status')=='ok' and h['deployment']['deployment_id']==deployment and h['runtime_source']['status']=='MEASURED_MATCHES_MANIFEST' and h['runtime_source']['observed_sha256']==runtime,'Actual runtime/source drift')
  need(type(expected['runtime_file_count']) is int and h['runtime_source'].get('file_count')==expected['runtime_file_count'],'Runtime file count missing/mismatch')
  need(self._json_get('/api/health').get('ok') is True,'Actual database health required')
  runtime_flags=self._runtime_flags(deployment,runtime,native)
  aliases=self._frontend(expected);books=self._public(expected);covers=self._covers_source(expected)
  return {'native':native,'config_sha256':cfg,'startup_proof_sha256':logs,'runtime_sha256':runtime,'runtime_flags':runtime_flags,'cover_source_binding_sha256':covers,'aliases':aliases,'books':books,'observed_at':self.clock().isoformat()}
 def _baseline_source(self,binding):
  from scripts.build_runtime_source_manifest import build
  raw=subprocess.check_output(['git','-c','remote.origin.promisor=false','show',binding['baseline_source_sha']+':backend/.runtime-source-manifest.json'],cwd=self.role_source_root,timeout=30,env={**__import__('os').environ,'GIT_NO_LAZY_FETCH':'1'})
  manifest=json.loads(raw)
  need(manifest['expected_sha256']==binding['baseline_runtime_sha256'] and build(self.role_source_root,binding['baseline_source_sha'])==manifest,'Baseline Git/runtime binding mismatch')
 def _bound_expected(self,expected):
  A=expected['acceptance_contract'];N=expected['native_binding'];P=expected['provider_binding'];U=expected['upload_payload']
  envelope={'schema':BRIDGE_SCHEMA,'upload_payload':U,'provider_binding':P,'acceptance_contract':A}
  need(digest(envelope)==N['payload_sha256'],'Reviewed U/P/A envelope not bound to N')
  need(isinstance(A,dict) and set(A)>={'books','frontend_deployment_id','frontend_source_sha','runtime_file_count','phase_policy','covers','prior_signed_protocol'},'Immutable acceptance contract incomplete')
  need(P['source_sha']==N['source_sha'] and P['source_delivery_sha256']==N['runtime_sha256'] and P['backend_payload_sha256']==digest(U) and P['config_sha256']==N['config_sha256'] and P['current_backend_deployment_id']==N['baseline_deployment_id'] and P['current_backend_source_sha']==N['baseline_source_sha'] and P['frontend_deployment_id']==A['frontend_deployment_id'] and P['frontend_source_sha']==A['frontend_source_sha'],'Covered P/U/N identities differ')
  policy={'role_source_sha':N['source_sha'],'role_runtime_sha256':N['runtime_sha256'],'baseline_deployment_id':N['baseline_deployment_id'],'baseline_runtime_sha256':N['baseline_runtime_sha256']}
  need(json.loads((self.source_root/'internal/release/reader612_phase_acceptance.json').read_text())==A,'Acceptance contract differs from reviewed repository source')
  need(A['phase_policy']==policy,'Covered phase/source/baseline policy mismatch')
  # Caller flattening cannot silently override covered public/alias/count fields.
  for key,value in A.items():
   if key in expected:need(expected[key]==value,'Acceptance override mismatch: '+key)
  return {**expected,**A}
 def _signed_frontend_compatibility(self,expected):
  prior=expected['prior_signed_protocol'];need(prior['technical_status']=='PASS_NATIVE_CLOSED_RECOVERY','Historical technical protocol receipt missing')
  # Fixed retained technical evidence only. Never read historical approvals as
  # current authority; no protected operation is authorized by these files.
  packet=Path('/private/tmp/earnalism-native-recovery-qualification-20261030')
  actual_raw=(packet/'595-ACTUAL.json').read_bytes();qualified_raw=(packet/'595-QUALIFIED.json').read_bytes()
  need(hashlib.sha256(actual_raw).hexdigest()==prior['native_receipt_sha256'] and hashlib.sha256(qualified_raw).hexdigest()==prior['qualification_receipt_sha256'],'Historical technical receipt hash mismatch')
  actual=json.loads(actual_raw);q=json.loads(qualified_raw)
  need(actual['scope']=='ACTUAL_PROVIDER_AND_SOURCE' and actual['action']=='release_guarded_bootstrap' and actual['source_sha']==prior['proof_source_sha'] and actual['frontend_deployment_id']==prior['frontend_deployment_id'] and actual['frontend_source_sha']==prior['frontend_source_sha'] and q['status']=='PASS_NATIVE_CLOSED_RECOVERY' and q['deployment_id']==actual['deployment_id'],'Historical protocol scope mismatch')
  needed={'frontend/api','frontend/src/lib/api.js','frontend/src/lib/paymentReceipt.js','frontend/src/lib/readingPassApi.js','frontend/vercel.json'}
  need(set(prior['protected_path_git_objects'])==needed,'Exact signed protocol path set required')
  for path,oid in prior['protected_path_git_objects'].items():
   need(re.fullmatch('[a-f0-9]{40}',oid),'Immutable protocol object missing')
   for ref in (prior['frontend_source_sha'],expected['frontend_source_sha'],'HEAD'):
    observed=subprocess.check_output(['git','-c','remote.origin.promisor=false','rev-parse',ref+':'+path],cwd=self.source_root,text=True,timeout=30,env={**__import__('os').environ,'GIT_NO_LAZY_FETCH':'1'}).strip()
    need(observed==oid,'Signed frontend protocol changed')
  return digest({'prior_receipt':prior['native_receipt_sha256'],'prior_source':prior['frontend_source_sha'],'current_source':expected['frontend_source_sha'],'objects':prior['protected_path_git_objects']})
 def collect_preflight(self,binding,source_binding,expected):
  expected=self._bound_expected(expected)
  need(binding['baseline_deployment_id']==binding['current_deployment_id'],'Baseline phase mismatch')
  self._flag_source_equivalence(binding);self._baseline_source(binding)
  facts=self._common(binding['baseline_deployment_id'],binding['baseline_runtime_sha256'],binding['config_sha256'],expected)
  P=expected['provider_binding'];U=expected['upload_payload'];N=expected['native_binding']
  need(N==binding and P['source_sha']==N['source_sha'] and P['source_delivery_sha256']==N['runtime_sha256'] and P['config_sha256']==N['config_sha256'] and P['backend_payload_sha256']==digest(U) and U['runtime_expected_sha256']==N['runtime_sha256'],'U/P/N cross-binding mismatch')
  n=facts['native'];need((n['image'],n['snapshot'])==(binding['baseline_image'],binding['baseline_snapshot']),'Retained original image/snapshot mismatch')
  # False flags are derived from actual exact Redis-disabled startup, not user input.
  need(P.get('purchase_mode')=='CLOSED' and P.get('closed_server_sha256')==hashlib.sha256((self.role_source_root/'backend/server.py').read_bytes()).hexdigest(),'Provider CLOSED source binding mismatch')
  source=qualify_binding(self.role_source_root,source_binding,environment={'MULTI_REPLICA_ENABLED':'false','REDIS_CACHE_ENABLED':'false','REDIS_PUBLIC_METADATA_ENABLED':'false'})
  need(source['source_sha']==binding['source_sha'] and source['tree_sha']==binding['tree_sha'] and source['runtime_sha256']==binding['runtime_sha256'],'Exact immutable U/P/N source mismatch')
  membership=hashlib.sha256(json.dumps(U['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
  need(source['payload_membership_sha256']==membership and source['payload_files']==len(U['files']),'Actual source upload membership mismatch')
  need(P['frontend_deployment_id']==expected['frontend_deployment_id'] and P['frontend_source_sha']==expected['frontend_source_sha'] and P['current_backend_deployment_id']==binding['baseline_deployment_id'] and P['current_backend_source_sha']==binding['baseline_source_sha'],'Provider baseline/frontend identity mismatch')
  proof={'scope':'ACTUAL_IMMUTABLE_SOURCE_AND_NATIVE_BASELINE','binding_sha256':digest(binding),'observed_at':facts['observed_at'],'source_tree_payload_verified':True,'baseline_image_snapshot_config_verified':True,'auto_deploy_off':True,'all_effective_redis_flags_off':True,'current_healthy':True,'no_staged_changes':True,'actual_facts_sha256':digest(facts),'provider_writes':0}
  proof['provider_identity_sha256']=digest({'project':RAILWAY_PROJECT,'service':SERVICE,'environment':ENVIRONMENT})
  stable={k:v for k,v in facts.items() if k not in {'observed_at','runtime_flags'}}
  stable['runtime_flags']={k:facts['runtime_flags'][k] for k in ('scope','effective_all_three_off','observed_deployment_instance_id')}
  # Per-request log IDs/stat counters authenticate each read but cannot make the
  # protected operation digest change on every equivalent fresh observation.
  proof['bootstrap_preflight_sha256']=digest({'facts':stable,'source':source,'upload':digest(U),'provider_binding':digest(P)})
  proof['provider_actual']={**P,'scope':'ACTUAL_PROVIDER_AND_SOURCE','qualified':False,'auto_deploy':False,'authenticated_provider_account':True,'cli_version':'5.71.0','provider_identity_sha256':proof['provider_identity_sha256'],'bootstrap_preflight_sha256':proof['bootstrap_preflight_sha256'],'current_backend_healthy':True,'native_healthcheck_traffic_gating':True,'new_resources_or_config_changes':False}
  protocol=self._signed_frontend_compatibility(expected)
  proof['provider_actual']['frontend_signed_purchase_ready']=True
  proof['provider_actual']['qualified']=callable(self.purchase_probe)
  proof['provider_actual']['signed_protocol_reuse_sha256']=protocol
  proof['holds']=[] if callable(self.purchase_probe) else ['CLOSED_PHASE_PROBE_CHANNEL_UNBOUND_PREWRITE_HOLD']
  return proof
 def _phase_deployment(self,record,expected):
  query='query { serviceInstance(environmentId:"'+ENVIRONMENT+'",serviceId:"'+SERVICE+'") {latestDeployment {id status}} }'
  raw=self._read(['railway','api',query,'--compact']);need(not raw.get('errors'),'Actual phase deployment unavailable')
  current=raw['data']['serviceInstance']['latestDeployment'];need(current['status']=='SUCCESS' and UUID.fullmatch(current['id']),'Actual phase deployment unqualified')
  reported=record.get('unverified_provider_deployment_id')
  if reported is not None:need(current['id']==reported,'Actual deployment differs from native write response')
  if 'phase_deployment_id' in expected:need(current['id']==expected['phase_deployment_id'],'Caller phase hint differs from actual native deployment')
  return current['id']
 def collect_closed(self,record,expected,*,purchase_probe=None):
  expected=self._bound_expected(expected)
  need(record['action']=='release_guarded_bootstrap' and record['state']=='WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED','Wrong/unattempted CLOSED phase')
  purchase_probe=purchase_probe or self.purchase_probe
  need(callable(purchase_probe),'CLOSED_PROBE_UNBOUND: no POST authorized or implied by metadata')
  b=record['binding'];need(b==expected['provider_binding'],'CLOSED provider binding differs from covered parent');dep=self._phase_deployment(record,expected);need(dep!=b['current_backend_deployment_id'],'Baseline metadata cannot qualify new CLOSED image')
  facts=self._common(dep,b['source_delivery_sha256'],b['config_sha256'],expected)
  need(datetime.fromisoformat(facts['native']['created_at'].replace('Z','+00:00'))>=datetime.fromisoformat(record['started_at']),'Old deployment cannot qualify phase')
  source=qualify_binding(self.role_source_root,expected['role_binding'],environment={'MULTI_REPLICA_ENABLED':'false','REDIS_CACHE_ENABLED':'false','REDIS_PUBLIC_METADATA_ENABLED':'false'})
  need(source['source_sha']==b['source_sha'] and source['runtime_sha256']==b['source_delivery_sha256'],'Actual CLOSED source role mismatch')
  need(hashlib.sha256((self.role_source_root/'backend/server.py').read_bytes()).hexdigest()==b['closed_server_sha256'],'Measured CLOSED source bytes missing')
  # Root must bind the exact closed source helper; no arbitrary early-return bool.
  from scripts.purchase_guard_source import validate
  m,_,closed=validate(self.role_source_root);need(m['state']=='CLOSED' and closed==(self.role_source_root/'backend/server.py').read_bytes(),'Actual exact CLOSED helper unavailable')
  phase={'deployment_id':dep,'image':facts['native']['image'],'snapshot':facts['native']['snapshot'],
   'runtime_sha256':facts['runtime_sha256'],'config_sha256':facts['config_sha256']}
  status,headers,raw=purchase_probe('POST','https://theearnalism.com/api/payments/topup',b'{}',phase_identity=phase)
  need(status==503 and len(raw)<=65536 and json.loads(raw)['detail']['code']=='PURCHASE_INITIATION_CLOSED' and {k.lower():v for k,v in headers.items()}.get('cache-control')=='no-store','Actual inert CLOSED acceptance missing')
  actual={**b,'scope':'ACTUAL_PROVIDER_AND_SOURCE','operation_id':record['operation_id'],'action':'release_guarded_bootstrap','outcome':'APPLIED','deployment_id':dep,'guarded_backend_deployment_id':dep,'retained_image_id':facts['native']['image'],'snapshot_id':facts['native']['snapshot'],'source_tree_sha':source['tree_sha'],'native_file_config_sha256':facts['native']['file_config_sha256'],'startup_complete':True,'database_healthy':True,'source_attestation_matches':True,'native_can_rollback':True,'config_compatible':True,'existing_reader_listener_preserved':True,'verify_refund_webhook_code_preserved':True,'closed_guest_status':503,'purchase_pause_proof':'MEASURED_EXACT_EARLY_RETURN_AND_ANONYMOUS_503','actual_facts_sha256':digest(facts)}
  actual['recovery_receipt_sha256']=self._artifact_receipt(actual);actual['receipt_sha256']=digest(actual);return actual
 def _artifact_receipt(self,receipt):
  return digest({'schema':'earnalism.reader612.native-artifact.v1','project':RAILWAY_PROJECT,'service':SERVICE,'environment':ENVIRONMENT,**{k:receipt[k] for k in ('source_sha','source_tree_sha','source_delivery_sha256','closed_server_sha256','deployment_id','retained_image_id','snapshot_id','config_sha256','native_file_config_sha256')}})
 def _restore_binding(self,binding,qualified,expected):
  original=expected['native_binding'];envelope={'schema':'earnalism.reader612-reviewed-restore.v1','upload_payload':expected['upload_payload'],'bootstrap_provider_binding':expected['provider_binding'],'acceptance_contract':expected['acceptance_contract'],'qualified_native_receipt_sha256':qualified['recovery_receipt_sha256']}
  need(binding=={**original,'current_deployment_id':qualified['deployment_id'],'payload_sha256':digest(envelope)},'Restore source/payload/receipt envelope mismatch')
 def _retained_baseline(self,binding):
  dep=binding['baseline_deployment_id'];need(UUID.fullmatch(dep),'Retained baseline ID missing')
  query='query { deployment(id:"'+dep+'") {id projectId serviceId environmentId snapshotId canRollback canRedeploy meta} }'
  raw=self._read(['railway','api',query,'--compact']);need(not raw.get('errors'),'Retained baseline metadata unavailable');n=raw['data']['deployment']
  need((n['id'],n['projectId'],n['serviceId'],n['environmentId'],n['snapshotId'],n['meta']['imageDigest'])==(dep,RAILWAY_PROJECT,SERVICE,ENVIRONMENT,binding['baseline_snapshot'],binding['baseline_image']) and n['canRollback'] is True and n['canRedeploy'] is True,'Captured original baseline no longer natively recoverable')
  # Intentionally no latestDeployment==baseline check: current phase is CLOSED.
  return {'deployment_id':dep,'image':binding['baseline_image'],'snapshot':binding['baseline_snapshot'],'can_rollback':True}
 def collect_restore_preflight(self,binding,stored_qualified,expected):
  expected=self._bound_expected(expected);self._restore_binding(binding,stored_qualified,expected);expected={**expected,'qualified_recovery':stored_qualified}
  self._qualified_recovery({'binding':binding},expected);self._baseline_source(binding);self._flag_source_equivalence(binding)
  source=qualify_binding(self.role_source_root,expected['role_binding'],environment={'MULTI_REPLICA_ENABLED':'false','REDIS_CACHE_ENABLED':'false','REDIS_PUBLIC_METADATA_ENABLED':'false'})
  need(source['source_sha']==binding['source_sha'] and source['tree_sha']==binding['tree_sha'] and source['runtime_sha256']==binding['runtime_sha256'],'Restore role source mismatch')
  U=expected['upload_payload'];membership=hashlib.sha256(json.dumps(U['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
  need(source['payload_membership_sha256']==membership and source['payload_files']==len(U['files']),'Restore upload membership changed')
  current=stored_qualified['deployment_id'];need(current==binding['current_deployment_id'],'Qualified current deployment mismatch')
  facts=self._common(current,binding['runtime_sha256'],binding['config_sha256'],expected)
  need(facts['native']['image']==stored_qualified['retained_image_id'] and facts['native']['snapshot']==stored_qualified['snapshot_id'],'Qualified current role image drift')
  baseline=self._retained_baseline(binding);protocol=self._signed_frontend_compatibility(expected)
  # Reuse exact stored early503 proof for the unchanged current role. No POST.
  need(stored_qualified['closed_guest_status']==503 and stored_qualified['purchase_pause_proof']=='MEASURED_EXACT_EARLY_RETURN_AND_ANONYMOUS_503','Stored CLOSED acceptance not qualified')
  return {'scope':'ACTUAL_IMMUTABLE_SOURCE_AND_NATIVE_BASELINE','binding_sha256':digest(binding),'observed_at':facts['observed_at'],'source_tree_payload_verified':True,'baseline_image_snapshot_config_verified':True,'auto_deploy_off':True,'all_effective_redis_flags_off':True,'current_healthy':True,'no_staged_changes':True,'qualified_native_receipt_sha256':stored_qualified['recovery_receipt_sha256'],'current_runtime_sha256':binding['runtime_sha256'],'current_deployment_id':current,'baseline_can_rollback':baseline['can_rollback'],'actual_facts_sha256':digest({'current':facts,'baseline':baseline,'signed_protocol':protocol}),'POST_repeated':False,'provider_writes':0}
 def restore_schema(self):
  query='query { __type(name:"Mutation") { fields {name args {name type {kind name ofType {kind name}}} type {kind name ofType {kind name}}} } }'
  raw=self._read(['railway','api',query,'--compact']);need(not raw.get('errors'),'Native rollback schema unavailable')
  fields=[x for x in raw['data']['__type']['fields'] if x.get('name')=='deploymentRollback'];need(len(fields)==1,'Native rollback scalar unavailable');field=fields[0]
  need(field['type']=={'kind':'NON_NULL','name':None,'ofType':{'kind':'SCALAR','name':'Boolean'}} and field['args']==[{'name':'id','type':{'kind':'NON_NULL','name':None,'ofType':{'kind':'SCALAR','name':'String'}}}],'Native rollback schema differs')
  return {'name':'deploymentRollback','argument':{'name':'id','type':'String!'},'return':'Boolean!'}
 def _qualified_recovery(self,record,expected):
  from scripts.reader612_native_restore import CANONICAL_JOURNAL
  from scripts.india_release_provider_adapter import _read_journal
  q=expected['qualified_recovery'];b=record['binding'];need(q.get('scope')=='ACTUAL_PROVIDER_AND_SOURCE' and q.get('action')=='release_guarded_bootstrap' and q.get('source_sha')==b['source_sha'] and q.get('source_delivery_sha256')==b['runtime_sha256'],'Qualified role receipt missing/mismatched')
  need(UUID.fullmatch(q.get('deployment_id','')) and HASH.fullmatch(q.get('operation_id','')),'Qualified recovery identity missing')
  need(digest({k:v for k,v in q.items() if k!='receipt_sha256'})==q.get('receipt_sha256') and self._artifact_receipt(q)==q.get('recovery_receipt_sha256'),'Qualified receipt canonical digest mismatch')
  journal=_read_journal(CANONICAL_JOURNAL/(q['operation_id']+'.json'))
  need(journal.get('state')=='APPLIED_VERIFIED' and journal.get('action')=='release_guarded_bootstrap' and journal['binding']['source_sha']==b['source_sha'] and journal.get('guarded_recovery_receipt_sha256')==q['recovery_receipt_sha256'] and journal.get('reconciliation_receipt_sha256')==q['receipt_sha256'],'Qualified role journal not verified')
  return q
 def collect_restored(self,record,expected):
  expected=self._bound_expected(expected)
  need(record['action']=='restore_original_native_after_reader612_qualification' and record['state']=='WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED','Wrong/unattempted restoration phase')
  b=record['binding'];self._restore_binding(b,expected['qualified_recovery'],expected);self._baseline_source(b);dep=self._phase_deployment(record,expected);facts=self._common(dep,b['baseline_runtime_sha256'],b['config_sha256'],expected)
  need(facts['native']['image']==b['baseline_image'],'Not the captured original baseline image')
  need(datetime.fromisoformat(facts['native']['created_at'].replace('Z','+00:00'))>=datetime.fromisoformat(record['started_at']),'Old deployment cannot prove new restoration')
  # At least the qualified role image must still be natively retained. This is a
  # fixed metadata read, not another deployment or a favorable capability input.
  retained=self._qualified_recovery(record,expected)
  query='query { deployment(id:"'+retained['deployment_id']+'") {id projectId serviceId environmentId snapshotId canRollback canRedeploy meta} }'
  raw=self._read(['railway','api',query,'--compact']);need(not raw.get('errors'),'Recovery retention unavailable');n=raw['data']['deployment']
  need((n['id'],n['projectId'],n['serviceId'],n['environmentId'],n['snapshotId'],n['meta']['imageDigest'])==(retained['deployment_id'],RAILWAY_PROJECT,SERVICE,ENVIRONMENT,retained['snapshot_id'],retained['retained_image_id']) and n['canRollback'] is True and n['canRedeploy'] is True,'Qualified recovery artifact lost/drifted')
  result={'scope':'ACTUAL_PROVIDER_AND_SOURCE','operation_id':record['operation_id'],'action':record['action'],'source_sha':b['source_sha'],'outcome':'APPLIED','deployment_id':dep,'restored_image':facts['native']['image'],'restored_source_sha':b['baseline_source_sha'],'restored_runtime_sha256':facts['runtime_sha256'],'restored_config_sha256':facts['config_sha256'],'startup_database_healthy':True,'redis_auto_deploy_off':True,'public_protected_acceptance':True,'qualified_recovery_image_retained':True,'actual_facts_sha256':digest(facts)}
  result['receipt_sha256']=digest(result);return result
