"""Exact startup helpers, synthetic in-memory transports only; never import app."""
import ast,asyncio,types,sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
SOURCE=Path(__file__).resolve().parents[1]/'server.py'
NAMES={'initialize_replica_state_backends','_configure_redis_cache_policy'}
class FakeRedis:
 def __init__(self):
  self.calls=[];self.policy={'maxmemory':'1000000','maxmemory-policy':'noeviction'};self.memory={'used_memory':100};self.failure=None;self.hang=False;self.ping_failure=False;self.closing_hangs=False;self.set_failure=False;self.ns=None
 async def ping(self):
  self.calls.append('PING')
  if self.ping_failure:raise ConnectionError('SYNTHETIC_PRIVATE_DIAGNOSTIC')
 async def config_get(self,*names):
  self.calls.append(('CONFIG_GET',names));assert self.ns['_redis_available'] is False
  if self.failure:raise self.failure
  if self.hang:await asyncio.Event().wait()
  return self.policy
 async def info(self,section):self.calls.append(('INFO',section));return self.memory
 async def config_set(self,*a):raise AssertionError('CONFIG SET forbidden')
 async def set(self,*a,**kw):
  self.calls.append('SET');assert self.ns['_redis_config_status']['protected_policy_verified'] is True;assert self.ns['_redis_available'] is False
  if self.set_failure:raise RuntimeError('SYNTHETIC_OOM')
 async def aclose(self):
  self.calls.append('CLOSE')
  if self.closing_hangs:await asyncio.Event().wait()
class Policy(unittest.IsolatedAsyncioTestCase):
 def setUp(self):
  self.client=FakeRedis();parent=types.ModuleType('redis');child=types.ModuleType('redis.asyncio');parent.asyncio=child;parent.__path__=[];child.from_url=Mock(return_value=self.client);self.factory=child.from_url;self.patch=patch.dict(sys.modules,{'redis':parent,'redis.asyncio':child});self.patch.start();self.addCleanup(self.patch.stop)
  self.ns={'asyncio':asyncio,'REDIS_PUBLIC_METADATA_ENABLED':False,'REDIS_CACHE_ENABLED':True,'MULTI_REPLICA_ENABLED':False,'ENABLE_STARTUP_DB_MAINTENANCE':False,'REDIS_CACHE_FAIL_FAST':False,'REDIS_URL':'redis://SYNTHETIC-NOT-A-NETWORK-DESTINATION','REDIS_SOCKET_TIMEOUT_SECONDS':.05,'REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS':.05,'REDIS_CONFIGURE_ON_STARTUP':False,'REDIS_MAXMEMORY':'OLD_INERT_VALUE','REDIS_MAXMEMORY_POLICY':'volatile-lfu','PUBLIC_CACHE_ENABLED':True,'logger':Mock(),'_redis_client':None,'_redis_available':False,'_redis_key':lambda *a:':'.join(a),'uuid':types.SimpleNamespace(uuid4=lambda:types.SimpleNamespace(hex='SYNTHETIC'))}
  self.client.ns=self.ns;tree=ast.parse(SOURCE.read_text());nodes=[n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name in NAMES];self.assertEqual(len(nodes),2);exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE),'exec'),self.ns)
 async def start(self):await self.ns['initialize_replica_state_backends']()
 def rejected(self):
  self.assertFalse(self.ns['_redis_available']);self.assertIsNone(self.ns['_redis_client']);self.assertNotIn('SET',self.client.calls);self.assertIn('CLOSE',self.client.calls)
 async def test_disabled_unchanged_no_client_no_reads_no_writes(self):
  self.ns['REDIS_CACHE_ENABLED']=False;await self.start();self.factory.assert_not_called();self.assertEqual(self.client.calls,[]);self.assertFalse(self.ns['_redis_available'])
 async def test_safe_observed_policy_before_available_or_generation_write(self):
  await self.start();self.assertTrue(self.ns['_redis_available']);self.assertTrue(self.ns['_redis_config_status']['protected_policy_verified']);self.assertEqual(self.client.calls,['PING',('CONFIG_GET',('maxmemory','maxmemory-policy')),('INFO','memory'),'SET']);self.assertFalse(self.ns['_redis_config_status']['attempted']);self.assertEqual(self.ns['_redis_config_status']['applied'],{})
 async def test_configure_flag_rejects_even_safe_requested_value_no_partial_write(self):
  self.ns['REDIS_CONFIGURE_ON_STARTUP']=True;self.ns['REDIS_MAXMEMORY_POLICY']='noeviction'
  with self.assertRaisesRegex(RuntimeError,'CONFIGURE_ON_STARTUP=false'):await self.start()
  self.rejected();self.assertFalse(any(isinstance(x,tuple) and x[0]=='CONFIG_GET' for x in self.client.calls))
 async def test_inert_old_requested_values_do_not_reject_safe_actual_policy(self):
  await self.start();self.assertTrue(self.ns['_redis_available'])
 async def test_unsafe_eviction_denied_with_optional_cache_failfast_false(self):
  self.client.policy['maxmemory-policy']='volatile-lfu'
  with self.assertRaisesRegex(RuntimeError,'noeviction'):await self.start()
  self.rejected()
 async def test_multireplica_uses_same_protected_guard(self):
  self.ns['REDIS_CACHE_ENABLED']=False;self.ns['MULTI_REPLICA_ENABLED']=True;self.client.policy['maxmemory-policy']='allkeys-lru'
  with self.assertRaises(RuntimeError):await self.start()
  self.rejected()
 async def test_unbounded_memory_denied(self):
  self.client.policy['maxmemory']='0'
  with self.assertRaises(RuntimeError):await self.start()
  self.rejected()
 async def test_exhausted_memory_denied(self):
  self.client.memory['used_memory']=1000000
  with self.assertRaises(RuntimeError):await self.start()
  self.rejected()
 async def test_unknown_policy_or_memory_shape_denied(self):
  for policy,memory in [(None,{}),({},{}),({'maxmemory':'1000','maxmemory-policy':'noeviction'},{'used_memory':True}),({'maxmemory':'-1','maxmemory-policy':'noeviction'},{'used_memory':0}),({'maxmemory':'1000','maxmemory-policy':'noeviction'},None)]:
   self.client.policy,self.client.memory=policy,memory;self.client.calls=[]
   with self.subTest(policy=policy,memory=memory),self.assertRaises(RuntimeError):await self.start()
   self.rejected()
 async def test_bytes_config_and_memory_keys_supported(self):
  self.client.policy={b'maxmemory':b'1000000',b'maxmemory-policy':b'noeviction'};self.client.memory={b'used_memory':10};await self.start();self.assertTrue(self.ns['_redis_available'])
 async def test_acl_denial_is_fail_closed_and_not_logged_as_secret(self):
  self.client.failure=PermissionError('SYNTHETIC_PRIVATE_DIAGNOSTIC')
  with self.assertRaisesRegex(RuntimeError,'could not be verified') as e:await self.start()
  self.assertNotIn('SYNTHETIC_PRIVATE_DIAGNOSTIC',str(e.exception));self.assertNotIn('SYNTHETIC_PRIVATE_DIAGNOSTIC',repr(self.ns['_redis_config_status']));self.rejected()
 async def test_read_timeout_cleans_up_before_raising(self):
  self.client.hang=True
  with self.assertRaises(RuntimeError):await asyncio.wait_for(self.start(),.5)
  self.rejected()
 async def test_cleanup_timeout_is_bounded_and_does_not_admit(self):
  self.client.failure=PermissionError();self.client.closing_hangs=True
  with self.assertRaises(RuntimeError):await asyncio.wait_for(self.start(),.6)
  self.rejected()
 async def test_reinitialization_never_uses_stale_available_true(self):
  self.ns['_redis_available']=True;self.client.failure=PermissionError()
  with self.assertRaises(RuntimeError):await self.start()
  self.rejected()
 async def test_broad_ping_failure_never_falls_back_to_local(self):
  self.client.ping_failure=True
  with self.assertRaises(RuntimeError):await self.start()
  self.assertFalse(self.ns['_redis_available']);self.assertIsNone(self.ns['_redis_client'])
 async def test_broad_missing_url_denies_but_public_only_keeps_fallback(self):
  self.ns['REDIS_URL']=''
  with self.assertRaises(RuntimeError):await self.start()
  self.ns['REDIS_CACHE_ENABLED']=False;self.ns['REDIS_PUBLIC_METADATA_ENABLED']=True;await self.start();self.factory.assert_not_called();self.assertFalse(self.ns['_redis_available'])
 async def test_public_only_does_not_read_or_mutate_global_policy(self):
  self.ns['REDIS_CACHE_ENABLED']=False;self.ns['REDIS_PUBLIC_METADATA_ENABLED']=True
  class Control:
   def __init__(self,*args):pass
   async def startup(self):return False
  self.ns.update(metadata_cache=types.SimpleNamespace(Control=Control),db=object());await self.start();self.assertFalse(self.ns['_redis_available']);self.assertEqual(self.client.calls,['PING'])
 async def test_cancelled_startup_closes_and_never_admits(self):
  self.client.hang=True;task=asyncio.create_task(self.start())
  while not any(isinstance(x,tuple) and x[0]=='CONFIG_GET' for x in self.client.calls):await asyncio.sleep(0)
  task.cancel()
  with self.assertRaises(asyncio.CancelledError):await task
  self.rejected()
 async def test_generation_initialization_failure_closes_and_never_admits(self):
  self.client.set_failure=True
  with self.assertRaisesRegex(RuntimeError,'SYNTHETIC_OOM'):await self.start()
  self.assertFalse(self.ns['_redis_available']);self.assertIsNone(self.ns['_redis_client']);self.assertIn('CLOSE',self.client.calls)
 async def test_public_only_ping_failure_remains_optional(self):
  self.ns['REDIS_CACHE_ENABLED']=False;self.ns['REDIS_PUBLIC_METADATA_ENABLED']=True;self.client.ping_failure=True;await self.start();self.assertFalse(self.ns['_redis_available']);self.assertEqual(self.client.calls,['PING','CLOSE'])
if __name__=='__main__':unittest.main()
