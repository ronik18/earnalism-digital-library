"""Exact-source AST and synthetic lifespan tests; no app/provider/socket startup."""
import ast,asyncio,contextlib,copy,os,sys,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
P=Path(__file__).resolve().parent
from backend.reading_pass_admission import ScopedAdmission
from backend.reading_pass_service import ReadingPassService
from backend.domain.reading_pass import ReadingPassConfig
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException
from starlette.responses import JSONResponse
CANDIDATE=(P.parent/'server.py').read_text();TREE=ast.parse(CANDIDATE)
NAMES={'_initialize_reading_pass_scoped_admission','_reading_pass_renewal_engine','_drain_reading_pass_scoped_admission','_verify_startup_data_before_writes','lifespan','enforce_reading_pass_admission_binding'}
def namespace(events=None,enabled=False):
 events=[]if events is None else events
 async def raw_guard():events.append('raw_guard')
 async def initialize_backends():events.append('initialize_backends')
 async def close_backends():events.append('close_backends')
 async def no_maintenance():events.append('maintenance')
 client=SimpleNamespace(close=lambda:events.append('raw_close'));database=SimpleNamespace(client=client);service=SimpleNamespace(db=database,client=client,config=ReadingPassConfig(),token_secret='x'*32)
 ns={'asyncio':asyncio,'time':time,'os':os,'FastAPI':object,'Request':object,'JSONResponse':JSONResponse,'HTTPException':HTTPException,'READING_PASS_SCOPED_ADMISSION_ENABLED':enabled,'_reading_pass_scoped_admission':None,'_reading_pass_scoped_original_service':None,'_reading_pass_scoped_renewal_service':None,'_reading_pass_scoped_renewal_function':None,'_reading_pass_scoped_config':None,'_reading_pass_scoped_token_secret':None,'ReadingPassService':ReadingPassService,'client':client,'db':database,'reading_pass_service':service,'_acceptance_release_containment':lambda:True,'_install_sigterm_drain_marker':lambda:events.append('install_marker'),'_log_cost_control_startup':lambda:None,'initialize_replica_state_backends':initialize_backends,'ENABLE_STARTUP_DB_MAINTENANCE':False,'_run_startup_database_maintenance':no_maintenance,'logger':SimpleNamespace(info=lambda *a:None),'_schedule_home_surface_warmup':lambda:events.append('warmup'),'_initialize_authorized_reader_release':lambda:None,'_mark_shutdown_draining':lambda:events.append('mark_draining'),'_shutdown_state':{'inflight':0},'close_replica_state_backends':close_backends}
 nodes=[]
 for node in TREE.body:
  if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))and node.name in NAMES:
   node=copy.deepcopy(node);node.decorator_list=[];nodes.append(node)
 exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'exact-server-ast','exec'),ns)
 ns['_actual_verify_startup_data_before_writes']=ns['_verify_startup_data_before_writes']
 ns['_verify_startup_data_before_writes']=raw_guard
 ns['context']=contextlib.asynccontextmanager(ns['lifespan'])
 return ns
class Admission:
 def __init__(self,events,error=None):self.events=events;self.error=error;self.timeouts=[];self.closed=False
 async def drain(self,*,timeout):
  self.events.append('admission_drain');self.timeouts.append(timeout)
  if self.error:raise self.error
class Wiring(unittest.IsolatedAsyncioTestCase):
 def test_default_off_current_service_and_trusted_replacement(self):
  ns=namespace();original=ns['reading_pass_service'];ns['_initialize_reading_pass_scoped_admission']();self.assertIsNone(ns['_reading_pass_scoped_admission']);self.assertIs(ns['_reading_pass_renewal_engine'](),original)
  replacement=object();ns['reading_pass_service']=replacement;self.assertIs(ns['_reading_pass_renewal_engine'](),replacement)
 def test_enabled_uninitialized_fails_closed(self):
  ns=namespace(enabled=True)
  with self.assertRaises(HTTPException)as got:ns['_reading_pass_renewal_engine']()
  self.assertEqual(got.exception.status_code,503)
 async def test_enabled_constructor_only_new_renewal_service_preserves_raw_identity(self):
  ns=namespace(enabled=True);client=AsyncIOMotorClient('mongodb://127.0.0.1:1',connect=False,maxPoolSize=8);db=client['dummy'];raw_service=ReadingPassService(db=db,client=client,config=ReadingPassConfig(),token_secret='x'*32);ns.update(client=client,db=db,reading_pass_service=raw_service)
  try:
   with patch.dict(sys.modules,{'backend.reading_pass_admission':SimpleNamespace(ScopedAdmission=ScopedAdmission)}):ns['_initialize_reading_pass_scoped_admission']()
   q=ns['_reading_pass_scoped_admission'];renewal=ns['_reading_pass_renewal_engine']();self.assertIs(ns['reading_pass_service'],raw_service);self.assertIs(raw_service.db,db);self.assertIs(raw_service.client,client);self.assertIs(renewal.client,q);self.assertIs(renewal.db.raw,db);self.assertIs(renewal.config,raw_service.config);self.assertEqual(renewal.token_secret,raw_service.token_secret)
   replacement=object();ns['reading_pass_service']=replacement
   with self.assertRaises(HTTPException)as got:ns['_reading_pass_renewal_engine']()
   self.assertEqual(got.exception.status_code,503)
   await q.drain(timeout=1)
  finally:client.close()
 async def test_enabled_incompatible_pool_no_fallback_and_zero_work_close(self):
  events=[];ns=namespace(events,True);client=AsyncIOMotorClient('mongodb://127.0.0.1:1',connect=False,maxPoolSize=25);db=client['dummy'];service=ReadingPassService(db=db,client=client,config=ReadingPassConfig(),token_secret='x'*32);close=client.close;ns.update(client=client,db=db,reading_pass_service=service)
  try:
   with patch.dict(sys.modules,{'backend.reading_pass_admission':SimpleNamespace(ScopedAdmission=ScopedAdmission)}), patch.object(AsyncIOMotorClient,'close',new=property(lambda self:lambda:events.append('raw_close'))):
    with self.assertRaises(RuntimeError):
     async with ns['context'](None):self.fail('startup should not yield')
   self.assertEqual(events,['raw_guard','raw_close']);self.assertIsNone(ns['_reading_pass_scoped_admission'])
  finally:close()
 async def test_raw_guard_first_then_drain_before_raw_close_shared_budget(self):
  events=[];ns=namespace(events,True);q=Admission(events)
  def initialize():events.append('admission_initialize');ns['_reading_pass_scoped_admission']=q
  ns['_initialize_reading_pass_scoped_admission']=initialize
  async with ns['context'](None):events.append('body')
  self.assertEqual(events[0:2],['raw_guard','admission_initialize']);self.assertLess(events.index('admission_drain'),events.index('close_backends'));self.assertLess(events.index('close_backends'),events.index('raw_close'));self.assertTrue(0<q.timeouts[0]<=15)
 async def test_drain_timeout_does_not_close_raw_or_claim_success(self):
  events=[];ns=namespace(events,True);q=Admission(events,asyncio.TimeoutError());ns['_initialize_reading_pass_scoped_admission']=lambda:ns.update(_reading_pass_scoped_admission=q)
  with self.assertRaises(asyncio.TimeoutError):
   async with ns['context'](None):pass
  self.assertNotIn('raw_close',events);self.assertNotIn('close_backends',events)
 async def test_drain_cancellation_does_not_close_raw(self):
  events=[];ns=namespace(events,True);q=Admission(events,asyncio.CancelledError());ns['_initialize_reading_pass_scoped_admission']=lambda:ns.update(_reading_pass_scoped_admission=q)
  with self.assertRaises(asyncio.CancelledError):
   async with ns['context'](None):pass
  self.assertNotIn('raw_close',events)
 async def test_exception_at_yield_still_runs_shutdown_and_preserves_exception(self):
  events=[];ns=namespace(events,True);q=Admission(events);ns['_initialize_reading_pass_scoped_admission']=lambda:ns.update(_reading_pass_scoped_admission=q);error=ValueError('inert body')
  with self.assertRaises(ValueError)as got:
   async with ns['context'](None):raise error
  self.assertIs(got.exception,error);self.assertIn('admission_drain',events);self.assertEqual(events[-1],'raw_close')
 async def test_budget_exhaustion_stops_admission_without_extending_or_closing(self):
  events=[];ns=namespace(events,True);q=Admission(events);ns['_reading_pass_scoped_admission']=q;ns['time']=SimpleNamespace(monotonic=lambda:16)
  with self.assertRaises(asyncio.TimeoutError):await ns['_drain_reading_pass_scoped_admission'](15)
  self.assertTrue(q.closed);self.assertEqual(q.timeouts,[]);self.assertNotIn('raw_close',events)
 async def test_actual_raw_startup_guard_failure_closes_before_admission(self):
  events=[];ns=namespace(events,True);error=ValueError('dummy guard failure')
  async def denied(*args):events.append('raw_guard_denied');raise error
  module=SimpleNamespace(POLICY_ENV='LANE2_FAKE_POLICY',verify_startup_data=denied)
  with patch.dict(sys.modules,{'startup_data_guard':module,'backend.startup_data_guard':module}):
   with self.assertRaises(ValueError)as got:await ns['_actual_verify_startup_data_before_writes']()
  self.assertIs(got.exception,error);self.assertEqual(events,['raw_guard_denied','raw_close']);self.assertIsNone(ns['_reading_pass_scoped_admission'])
 async def test_cancelled_body_still_drains_then_preserves_cancel(self):
  events=[];ns=namespace(events,True);q=Admission(events);ns['_initialize_reading_pass_scoped_admission']=lambda:ns.update(_reading_pass_scoped_admission=q)
  with self.assertRaises(asyncio.CancelledError):
   async with ns['context'](None):raise asyncio.CancelledError()
  self.assertIn('admission_drain',events);self.assertEqual(events[-1],'raw_close')
 def test_financial_identity_branches_and_callbacks_unchanged(self):
  guarded=[node for node in TREE.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))and 'db is not reading_pass_service.db'in ast.unparse(node)]
  self.assertEqual(len(guarded),2)
  for node in guarded:self.assertNotIn('_reading_pass_scoped',ast.unparse(node))
  original_binding=next(node.value for node in TREE.body if isinstance(node,ast.Assign)and any(isinstance(target,ast.Name)and target.id=='reading_pass_service'for target in node.targets))
  self.assertEqual(ast.unparse(original_binding.func),'ReadingPassService')
  bound={keyword.arg:ast.unparse(keyword.value)for keyword in original_binding.keywords}
  self.assertEqual(bound['db'],'db');self.assertEqual(bound['client'],'client')
  self.assertEqual(CANDIDATE.count('result = await reading_pass_service.renew_lease('),1)
  self.assertNotIn('_reading_pass_renewal_engine',ast.unparse(next(n for n in TREE.body if isinstance(n,ast.AsyncFunctionDef)and n.name=='reading_pass_lease_renew')))
 def test_flag_default_off_and_no_request_driven_getter(self):
  self.assertIn('_env_bool("READING_PASS_SCOPED_ADMISSION_ENABLED", False)',CANDIDATE)
  engine=next(n for n in TREE.body if isinstance(n,ast.FunctionDef)and n.name=='_reading_pass_renewal_engine');self.assertEqual(engine.args.args,[]);self.assertNotIn('request',ast.unparse(engine).lower())

 async def test_enabled_drift_middleware_denies_without_next_dispatch(self):
  ns=namespace(enabled=True);client=AsyncIOMotorClient('mongodb://127.0.0.1:1',connect=False,maxPoolSize=8);db=client['dummy'];raw=ReadingPassService(db=db,client=client,config=ReadingPassConfig(),token_secret='x'*32);ns.update(client=client,db=db,reading_pass_service=raw);calls=[]
  async def next_request(request):calls.append(request);return 'next'
  request=SimpleNamespace(method='POST',url=SimpleNamespace(path='/api/reading-pass/leases/renew'))
  try:
   with patch.dict(sys.modules,{'backend.reading_pass_admission':SimpleNamespace(ScopedAdmission=ScopedAdmission)}):ns['_initialize_reading_pass_scoped_admission']()
   q=ns['_reading_pass_scoped_admission'];view=ns['_reading_pass_scoped_renewal_service']
   self.assertIs(raw.renew_lease.__self__,view);self.assertIs(raw.renew_lease.__func__,ReadingPassService.renew_lease)
   self.assertEqual(await ns['enforce_reading_pass_admission_binding'](request,next_request),'next')
   cases=[(ns,'reading_pass_service',object()),(ns,'db',object()),(ns,'client',object()),(raw,'db',object()),(raw,'client',object()),(raw,'config',ReadingPassConfig()),(raw,'token_secret','changed'),(raw,'renew_lease',ReadingPassService.renew_lease.__get__(raw,ReadingPassService)),(view,'db',None),(view,'client',None),(view,'config',None),(view,'token_secret','changed'),(q,'closed',True)]
   for target,key,value in cases:
    old=target[key]if isinstance(target,dict)else getattr(target,key)
    if isinstance(target,dict):target[key]=value
    else:setattr(target,key,value)
    result=await ns['enforce_reading_pass_admission_binding'](request,next_request);self.assertEqual(result.status_code,503);self.assertEqual(len(calls),1)
    if isinstance(target,dict):target[key]=old
    else:setattr(target,key,old)
   await q.drain(timeout=1)
  finally:client.close()
 async def test_binding_guard_does_not_select_unrelated_or_default_off_requests(self):
  ns=namespace(enabled=True);calls=[]
  async def next_request(request):calls.append(request);return 'next'
  for method,path in [('GET','/api/reading-pass/leases/renew'),('POST','/api/reading-pass/sessions/start'),('POST','/api/payments/topup')]:
   self.assertEqual(await ns['enforce_reading_pass_admission_binding'](SimpleNamespace(method=method,url=SimpleNamespace(path=path)),next_request),'next')
  ns['READING_PASS_SCOPED_ADMISSION_ENABLED']=False
  self.assertEqual(await ns['enforce_reading_pass_admission_binding'](SimpleNamespace(method='POST',url=SimpleNamespace(path='/api/reading-pass/leases/renew')),next_request),'next');self.assertEqual(len(calls),4)
 def test_deny_only_middleware_remains_inside_existing_policy_guards(self):
  positions={n.name:i for i,n in enumerate(TREE.body)if isinstance(n,ast.AsyncFunctionDef)}
  self.assertLess(positions['enforce_reading_pass_admission_binding'],positions['enforce_public_release_country']);self.assertLess(positions['enforce_reading_pass_admission_binding'],positions['production_hardening_middleware'])
if __name__=='__main__':unittest.main()
