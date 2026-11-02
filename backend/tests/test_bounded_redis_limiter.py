"""Offline contracts and opt-in sequential Unix-socket functional tests.

Never production/paid/load traffic. The caller owns the disposable local fixture;
no server launch, FLUSH, CONFIG, scanning or connection to a provider here.
"""
import ast
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time
import unittest
import uuid
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('candidate_limiter',ROOT/'bounded_redis_limiter.py')
import sys
sys.path.insert(0,str(ROOT))
m = importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

def policy(**kw):
    args=dict(slots=2,window=60,limits={s:2 for s in m.SCOPES},generation='a'*32)
    args.update(kw);return m.Policy(**args)

class Contracts(unittest.TestCase):
    def test_policy_immutable_and_exact_finite_bound(self):
        original={s:2 for s in m.SCOPES};p=policy(limits=original);raw=p.manifest
        original['api']=30;self.assertEqual(p.manifest,raw)
        with self.assertRaises(TypeError):p.limits['api']=3
        self.assertEqual(p.maximum_keys,19);self.assertEqual(p.maximum_members,108)
    def test_missing_or_invalid_activation_parameters_deny(self):
        for kw in [{'slots':0},{'slots':True},{'slots':4097},{'window':121},
                   {'generation':''},{'generation':'z'*32},{'limits':{'api':2}},
                   {'limits':{s:30001 for s in m.SCOPES}}]:
            with self.subTest(kw=kw),self.assertRaises(ValueError):policy(**kw)
    def test_slot_names_do_not_grow_with_identities(self):
        p=policy();names={m.keys('SYNTHETIC',p,'api',f'{i:064x}')[0] for i in range(100)}
        self.assertLessEqual(len(names),p.slots)
        with self.assertRaises(ValueError):m.keys('SYNTHETIC',p,'arbitrary','0'*64)
    def test_optional_writer_gate_independent_of_shared_state(self):
        tree=ast.parse((ROOT/'server.py').read_text());names={'_redis_state_enabled','_redis_cache_enabled'}
        ns={'_redis_available':True,'_redis_client':object(),'REDIS_CACHE_ENABLED':False,'MULTI_REPLICA_ENABLED':True}
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'candidate','exec'),ns)
        self.assertTrue(ns['_redis_state_enabled']());self.assertFalse(ns['_redis_cache_enabled']())
    def test_disabled_public_cache_never_serves_or_refills_retained_local_entry(self):
        stale={'catalogue': 'old revision'}
        ns={'PUBLIC_CACHE_ENABLED':False,'_public_cache':{'book':(time.monotonic()+999,stale)},
            '_public_cache_ticket':lambda *a,**kw:('local',0)}
        tree=ast.parse((ROOT/'server.py').read_text())
        nodes=[n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name in {'_public_cache_get','_public_cache_set'}]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'candidate-public-cache','exec'),ns)
        self.assertIsNone(asyncio.run(ns['_public_cache_get']('book')))
        asyncio.run(ns['_public_cache_set']('other',{'catalogue':'new'}))
        self.assertNotIn('other',ns['_public_cache'])

    def test_policy_read_is_nonmutating_and_missing_denies(self):
        class Fake:
            async def get(self,key):return None
        with self.assertRaises(RuntimeError):asyncio.run(m.verify_policy(Fake(),'SYNTHETIC',policy()))

    def test_matching_expiring_manifest_does_not_admit_startup(self):
        p=policy()
        class Fake:
            async def get(self,key):return p.manifest.encode()
            async def pttl(self,key):return 1000
        with self.assertRaises(RuntimeError):asyncio.run(m.verify_policy(Fake(),'SYNTHETIC',p))

class EffectivePoolParser(unittest.TestCase):
    def test_real_url_override_rejected_before_network(self):
        try:
            import redis.asyncio as redis
        except ModuleNotFoundError:
            self.skipTest('pinned redis package required for parser-only regression')
        from unittest.mock import AsyncMock,Mock,patch
        async def case():
            real_factory=redis.from_url;clients=[]
            def factory(*args,**kw):
                c=real_factory(*args,**kw);c.ping=AsyncMock(side_effect=AssertionError('network forbidden'))
                clients.append(c);return c
            ns=dict(asyncio=asyncio,REDIS_PUBLIC_METADATA_ENABLED=False,REDIS_CACHE_ENABLED=False,
                    MULTI_REPLICA_ENABLED=True,ENABLE_STARTUP_DB_MAINTENANCE=False,
                    REDIS_URL='redis://127.0.0.1:1/0?max_connections=9999',
                    REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS=.05,REDIS_SOCKET_TIMEOUT_SECONDS=.05,logger=Mock())
            tree=ast.parse((ROOT/'server.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='initialize_replica_state_backends')
            exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-pool-check','exec'),ns)
            with patch.object(redis,'from_url',factory):
                with self.assertRaisesRegex(RuntimeError,'pool limit'):
                    await ns['initialize_replica_state_backends']()
            self.assertEqual(clients[0].connection_pool.max_connections,9999)
            clients[0].ping.assert_not_awaited();self.assertFalse(ns['_redis_available'])
            self.assertIsNone(ns['_redis_client'])
        asyncio.run(case())

class ComposedStartup(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import types
        from unittest.mock import Mock,patch
        self.calls=[]
        p=policy()
        class Client:
            async def ping(inner):self.calls.append('PING')
            async def get(inner,key):self.calls.append('GET_POLICY');return self.manifest
            async def pttl(inner,key):self.calls.append('PTTL_POLICY');return -1
            async def set(inner,*a,**kw):raise AssertionError('optional cache write forbidden')
            async def aclose(inner):self.calls.append('CLOSE')
        self.client=Client();self.client.connection_pool=types.SimpleNamespace(max_connections=16);self.manifest=p.manifest.encode()
        parent=types.ModuleType('redis');child=types.ModuleType('redis.asyncio');parent.asyncio=child;parent.__path__=[]
        self.factory=Mock(return_value=self.client);child.from_url=self.factory
        self.patch=patch.dict(sys.modules,{'redis':parent,'redis.asyncio':child,'backend.bounded_redis_limiter':m,'bounded_redis_limiter':m});self.patch.start();self.addCleanup(self.patch.stop)
        async def safe_policy():self.calls.append('SAFE_POLICY')
        self.ns=dict(asyncio=asyncio,REDIS_PUBLIC_METADATA_ENABLED=False,REDIS_CACHE_ENABLED=False,
                     MULTI_REPLICA_ENABLED=True,ENABLE_STARTUP_DB_MAINTENANCE=False,READER_RUM_ENABLED=False,
                     REDIS_URL='redis://SYNTHETIC-NOT-A-NETWORK-DESTINATION',REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS=.05,
                     REDIS_SOCKET_TIMEOUT_SECONDS=.05,PUBLIC_CACHE_ENABLED=False,REDIS_KEY_PREFIX='SYNTHETIC',
                     REDIS_LIMITER_SLOTS=p.slots,REDIS_LIMITER_GENERATION=p.generation,RATE_LIMIT_WINDOW_SECONDS=p.window,
                     _configure_redis_cache_policy=safe_policy,logger=Mock(),_redis_available=False,_redis_client=None)
        for name in ['PUBLIC','READING_PASS','READER','AUTH','WEBHOOK','PAYMENT','ANALYTICS','UPLOAD','DEFAULT']:
            self.ns['RATE_LIMIT_'+name+'_PER_MINUTE']=2
        names={'initialize_replica_state_backends','_bounded_redis_policy','_configure_bounded_shared_state','_redis_cache_enabled','_redis_state_enabled'}
        tree=ast.parse((ROOT/'server.py').read_text())
        nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'candidate-startup','exec'),self.ns)
    async def test_admitted_profile_has_finite_pool_and_no_optional_write(self):
        await self.ns['initialize_replica_state_backends']()
        self.assertTrue(self.ns['_redis_state_enabled']());self.assertFalse(self.ns['_redis_cache_enabled']())
        self.assertEqual(self.factory.call_args.kwargs['max_connections'],16)
        self.assertEqual(self.calls,['PING','SAFE_POLICY','GET_POLICY','PTTL_POLICY'])
    async def test_missing_manifest_cleans_up_and_does_not_admit(self):
        self.manifest=None
        with self.assertRaises(RuntimeError):await self.ns['initialize_replica_state_backends']()
        self.assertFalse(self.ns['_redis_available']);self.assertIsNone(self.ns['_redis_client']);self.assertIn('CLOSE',self.calls)
    async def test_unbounded_optional_writer_profiles_deny(self):
        for flag in ['PUBLIC_CACHE_ENABLED','REDIS_CACHE_ENABLED','REDIS_PUBLIC_METADATA_ENABLED','READER_RUM_ENABLED','ENABLE_STARTUP_DB_MAINTENANCE']:
            self.ns[flag]=True
            with self.subTest(flag=flag),self.assertRaises(RuntimeError):await self.ns['initialize_replica_state_backends']()
            self.ns[flag]=False
            self.assertFalse(self.ns['_redis_available'])
    async def test_effective_pool_unknown_or_above_bound_denies_before_ping(self):
        for value in [None,True,0,-1,17,9999]:
            self.client.connection_pool.max_connections=value;self.calls.clear()
            with self.subTest(value=value),self.assertRaisesRegex(RuntimeError,'pool limit'):
                await self.ns['initialize_replica_state_backends']()
            self.assertNotIn('PING',self.calls);self.assertIn('CLOSE',self.calls)
            self.assertFalse(self.ns['_redis_available'])
    async def test_effective_lower_pool_is_preserved(self):
        self.client.connection_pool.max_connections=2
        await self.ns['initialize_replica_state_backends']()
        self.assertEqual(self.client.connection_pool.max_connections,2)

    async def test_default_slots_cannot_activate(self):
        self.ns['REDIS_LIMITER_SLOTS']=0
        with self.assertRaises(ValueError):await self.ns['initialize_replica_state_backends']()
        self.assertFalse(self.ns['_redis_available']);self.assertIn('CLOSE',self.calls)
    async def test_generation_drift_denies_and_never_reinitializes(self):
        self.ns['REDIS_LIMITER_GENERATION']='b'*32
        with self.assertRaises(RuntimeError):await self.ns['initialize_replica_state_backends']()
        self.assertFalse(self.ns['_redis_available']);self.assertIn('CLOSE',self.calls)

SOCKET=os.environ.get('EARNALISM_BOUNDED_REDIS_UNIT_SOCKET','')
URL=os.environ.get('EARNALISM_REDIS_INTEGRATION_URL','') if os.environ.get('EARNALISM_REDIS_INTEGRATION')=='1' else ''
@unittest.skipUnless(SOCKET or URL,'explicit disposable Unix or existing CI loopback fixture required')
class LuaFunctional(unittest.TestCase):
    def setUp(self):
        self.client=None
        if SOCKET:
            if not SOCKET.startswith('/private/tmp/earnalism-redis-bounds-20261102/') or not SOCKET.endswith('/redis.sock'):
                raise ValueError('exact task-private Unix fixture required')
        else:
            u=urlparse(URL)
            if not (u.scheme=='redis' and u.hostname=='127.0.0.1' and u.port and 26379<=u.port<=26479 and u.path=='/0' and not u.username and not u.password and not u.query and not u.fragment):
                raise ValueError('exact isolated CI loopback fixture required')
            import redis
            self.client=redis.Redis.from_url(URL,decode_responses=True,socket_timeout=1,socket_connect_timeout=.3)
        self.p=policy();self.prefix='SYNTHETIC:'+uuid.uuid4().hex;self.digest='0'*64
        self.names=m.keys(self.prefix,self.p,'api',self.digest);self.owned=set(self.names)
        self.cmd('SET',self.names[3],self.p.manifest)
        self.seed()
    def tearDown(self):
        try:self.cmd('DEL',*self.owned)
        finally:
            if self.client:self.client.close()
    def cmd(self,*args):
        if self.client:
            from redis.exceptions import ResponseError
            try:value=self.client.execute_command(*args)
            except ResponseError as e:return str(e)
            def flatten(v):
                if isinstance(v,(list,tuple)):return '\n'.join(flatten(x) for x in v)
                if v is None:return ''
                return str(v)
            return flatten(value)
        r=subprocess.run(['/opt/homebrew/bin/redis-cli','-s',SOCKET,'--raw',*map(str,args)],capture_output=True,text=True,timeout=3)
        if r.returncode:raise AssertionError(r.stderr)
        return r.stdout.strip()
    def clock(self):
        parts=self.cmd('TIME').splitlines();return int(parts[0])+int(parts[1])/1e6
    def seed(self):self.cmd('ZADD',self.names[0],-2,self.p.slot_header,-1,'@'+'0'*64)
    def arguments(self,token=None,digest=None,limit=None,manifest=None):
        return [self.p.window,limit or 2,token or str(uuid.uuid4()),digest or self.digest,
                manifest or self.p.manifest,self.p.slot_header,'api',0,self.prefix]
    def run_script(self,token=None,digest=None,script=None,**kw):
        names=m.keys(self.prefix,self.p,'api',digest or self.digest)
        self.owned.update(names)
        return self.cmd('EVAL',script or m.SCRIPT,4,*names,*self.arguments(token,digest,**kw))
    def test_limit_replay_and_persistent_state(self):
        a,b=str(uuid.uuid4()),str(uuid.uuid4())
        self.assertEqual(self.run_script(a),'0');self.assertEqual(self.run_script(b),'0')
        self.assertGreater(int(self.run_script()),0);self.assertEqual(self.run_script(a),'0')
        self.assertEqual(self.cmd('ZCARD',self.names[0]),'4');self.assertEqual(self.cmd('PTTL',self.names[0]),'-1')
    def test_missing_manifest_or_slot_never_reinitialized(self):
        self.cmd('DEL',self.names[3]);self.assertEqual(self.run_script(),'-1')
        self.cmd('SET',self.names[3],self.p.manifest);self.cmd('DEL',self.names[0])
        self.assertEqual(self.run_script(),'-1');self.assertEqual(self.cmd('EXISTS',self.names[0]),'0')
    def test_expiring_or_malformed_slot_denies(self):
        self.cmd('EXPIRE',self.names[0],120);self.assertEqual(self.run_script(),'-1')
        self.cmd('PERSIST',self.names[0]);self.cmd('ZADD',self.names[0],self.clock(),'x'*200)
        self.assertEqual(self.run_script(),'-1')
    def test_future_score_and_duplicate_owner_deny(self):
        token=str(uuid.uuid4());self.cmd('ZADD',self.names[0],self.clock()+100,token)
        self.assertEqual(self.run_script(),'-1');self.cmd('ZREM',self.names[0],token)
        self.cmd('ZADD',self.names[0],-1,'@'+'1'*64);self.assertEqual(self.run_script(),'-1')
    def test_collision_preserves_full_replay_horizon(self):
        token=str(uuid.uuid4());self.cmd('ZADD',self.names[0],self.clock()-90,token)
        # Same fixed slot, different owner, old request outside W but within 2W.
        other='0'*63+'2';self.assertGreater(int(self.run_script(digest=other)),0)
        self.assertEqual(self.run_script(token),'0')
        self.cmd('ZADD',self.names[0],self.clock()-121,token)
        self.assertEqual(self.run_script(digest=other),'0')
    def test_legacy_persistent_holds_and_timed_waits_without_admission(self):
        self.cmd('SET',self.names[1],'synthetic');self.assertEqual(self.run_script(),'-1')
        self.cmd('PEXPIRE',self.names[1],60000);self.assertGreater(int(self.run_script()),0)
        self.assertEqual(self.cmd('ZCARD',self.names[0]),'2')
    def test_mismatched_policy_arguments_cannot_relax_limit(self):
        self.assertEqual(self.run_script(limit=3),'-1')
        self.assertEqual(self.run_script(manifest=policy(generation='b'*32).manifest),'-1')
    def test_error_after_expired_cleanup_cannot_reset_live_history(self):
        token=str(uuid.uuid4());self.assertEqual(self.run_script(token),'0')
        broken=m.SCRIPT.replace("redis.call('ZADD',KEYS[1],-1,owner,now,ARGV[3])","error('SYNTHETIC_FINAL_WRITE_FAILURE')")
        self.assertIn('SYNTHETIC_FINAL_WRITE_FAILURE',self.run_script(script=broken))
        self.assertEqual(self.cmd('ZSCORE',self.names[0],token).split('.')[0],str(int(float(self.cmd('ZSCORE',self.names[0],token)))))
        self.assertEqual(self.run_script(token),'0')

if __name__=='__main__':unittest.main()
