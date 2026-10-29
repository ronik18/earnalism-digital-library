"""Exact source helpers against explicit loopback Redis only; no backend startup/provider access."""
import ast
import asyncio
from collections import OrderedDict, defaultdict
from contextvars import ContextVar
import hashlib
import io
import logging
import os
import pickle
from pathlib import Path
import re
import sys
import time
from typing import Any, Optional
import uuid
from unittest.mock import patch
import zlib

import pytest
from fastapi import Response, UploadFile
from backend.tests.test_shared_redis_limiter_integration import _endpoint

SERVER = Path(__file__).resolve().parents[1] / 'server.py'
TREE = ast.parse(SERVER.read_text())


def bindings(client, prefix):
    ns = dict(Any=Any, Optional=Optional, ContextVar=ContextVar, hashlib=hashlib,
              io=io, pickle=pickle, re=re, time=time, uuid=uuid, zlib=zlib,
              Response=Response, UploadFile=UploadFile, logger=logging.getLogger(__name__),
              REDIS_KEY_PREFIX=prefix, REDIS_PUBLIC_METADATA_ENABLED=True,
              REDIS_CACHE_ENABLED=False, MULTI_REPLICA_ENABLED=False,
              PUBLIC_CACHE_ENABLED=True, PUBLIC_CACHE_TTL_SECONDS=300,
              PUBLIC_CACHE_MAX_ENTRIES=96, REDIS_CACHE_TTL_JITTER_SECONDS=0,
              REDIS_CACHE_COMPRESS_MIN_BYTES=4096, _redis_client=client,
              _redis_available=True, _public_cache=OrderedDict(), _public_cache_generation=0,
              _cache_stats=defaultdict(int), _public_cache_fill_tickets=ContextVar(prefix, default=None),
              MEDIA_DATA_URI_RE=re.compile(r'data:(?:image|audio|video|application/octet-stream|application/pdf)/', re.I))
    for name in ('_PUBLIC_CACHE_READ_SCRIPT', '_PUBLIC_CACHE_FILL_SCRIPT', '_PUBLIC_CACHE_INVALIDATE_SCRIPT'):
        node = next(n for n in TREE.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
        ns[name] = ast.literal_eval(node.value)
    names = ('_redis_key', '_redis_text', '_redis_state_enabled', '_public_metadata_redis_enabled',
             '_ttl_with_jitter', '_redis_cache_payload_is_media', '_cache_payload_encode',
             '_cache_payload_encode_for_redis', '_cache_payload_decode', '_public_cache_ticket',
             '_public_cache_get', '_public_cache_set', '_public_cache_clear')
    for name in names:
        node = next(n for n in TREE.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(SERVER), 'exec'), ns)
    return ns


def local_bindings():
    ns = bindings(None, 'offline-local')
    ns['_redis_available'] = False
    return ns


def test_local_delayed_fill_and_task_isolation():
    async def run():
        ns = local_bindings()
        assert await ns['_public_cache_get']('old') is None
        await ns['_public_cache_clear']()
        await ns['_public_cache_set']('old', {'stale': True})
        assert 'old' not in ns['_public_cache']
        async def fill(i):
            assert await ns['_public_cache_get'](str(i)) is None
            await asyncio.sleep(0)
            await ns['_public_cache_set'](str(i), {'i': i})
        await asyncio.gather(*(fill(i) for i in range(10)))
        assert len(ns['_public_cache']) == 10
        await ns['_public_cache_set']('unpaired', {'unpaired': True})
        assert 'unpaired' not in ns['_public_cache']
    asyncio.run(run())


def test_fill_ticket_bound_and_consumption():
    ns = local_bindings()
    for i in range(50): ns['_public_cache_ticket'](str(i), ('local', 0))
    assert len(ns['_public_cache_fill_tickets'].get()) == 32
    assert ns['_public_cache_ticket']('49', consume=True) == ('local', 0)
    assert ns['_public_cache_ticket']('49', consume=True) is None


def test_public_only_never_enables_shared_authority():
    ns = bindings(object(), 'offline-flags')
    assert ns['_public_metadata_redis_enabled']()
    assert not ns['_redis_state_enabled']()
    ns['REDIS_PUBLIC_METADATA_ENABLED'] = False
    assert not ns['_public_metadata_redis_enabled']()
    ns['REDIS_CACHE_ENABLED'] = True
    assert ns['_public_metadata_redis_enabled']() and ns['_redis_state_enabled']()


def test_metadata_outage_is_miss_not_stale_local():
    class Broken:
        async def execute_command(self, *args): raise ConnectionError('dummy outage')
    async def run():
        ns = bindings(Broken(), 'offline-outage')
        ns['_public_cache']['key'] = (time.monotonic()+300, {'stale': True})
        assert await ns['_public_cache_get']('key') is None
        assert ns['_cache_stats']['public-cache_read_error'] == 1
        await ns['_public_cache_set']('key', {'fresh': True})  # no ticket: no write
    asyncio.run(run())


@pytest.mark.parametrize('case', ['read_hit', 'missing_generation', 'corrupt_generations',
    'expired_marker', 'delayed_fill', 'concurrent_fills', 'bad_payload', 'media_rejected',
    'public_only_invalidation', 'initializer_public_only', 'invalidation_replay'])
def test_real_public_metadata_redis(case):
    if os.environ.get('EARNALISM_REDIS_INTEGRATION') != '1':
        pytest.skip('explicit isolated Redis fixture required')
    url = _endpoint()
    async def run():
        import redis.asyncio as redis
        client = redis.from_url(url, socket_connect_timeout=.3, socket_timeout=1, retry_on_timeout=False)
        prefix = 'public-cache-test-' + uuid.uuid4().hex
        ns = bindings(client, prefix); calls=[]; known=set()
        original = client.execute_command
        async def record(*args, **kwargs):
            calls.append(args)
            cmd = str(args[0]).upper()
            if cmd in {'SET','SETEX','DEL','INCR','EXPIRE'}: known.add(args[1])
            if cmd in {'EVAL','EVAL_RO'}:
                for key in args[3:3+int(args[2])]: known.add(key)
            return await original(*args, **kwargs)
        client.execute_command = record
        generation = ns['_redis_key']('public-cache-v2','generation')
        key='metadata'; payload={'title':'dummy', 'territory':'IN'}
        def payload_key(token):
            k=ns['_redis_key']('public-cache-v2',token,hashlib.sha256(key.encode()).hexdigest());known.add(k);return k
        async def seed(token='a'*32): await client.set(generation, token)
        async def fill():
            assert await ns['_public_cache_get'](key) is None
            await ns['_public_cache_set'](key, payload)
        try:
            await seed()
            if case == 'read_hit':
                await fill();calls.clear()
                assert await ns['_public_cache_get'](key)==payload
                assert len(calls)==1 and calls[0][0]=='EVAL_RO'
                assert 0 < await client.ttl(payload_key('a'*32)) <= 300
            elif case in {'missing_generation','expired_marker'}:
                await fill(); await client.delete(generation)
                assert await ns['_public_cache_get'](key) is None
                await ns['_public_cache_set'](key, {'bad':'no-ticket'})
                await client.set(generation,'b'*32,nx=True)
                assert await ns['_public_cache_get'](key) is None
            elif case == 'corrupt_generations':
                await fill()
                for bad in ['0','-1','01','x'*32,'a'*31,'a'*33,'A'*32,'1.0']:
                    await client.set(generation,bad)
                    assert await ns['_public_cache_get'](key) is None
                await client.delete(generation);await client.lpush(generation,'wrong-type')
                assert await ns['_public_cache_get'](key) is None
            elif case == 'delayed_fill':
                assert await ns['_public_cache_get'](key) is None
                await ns['_public_cache_clear']()
                await ns['_public_cache_set'](key,payload)
                assert await client.get(payload_key('a'*32)) is None
                assert await ns['_public_cache_get'](key) is None
                await ns['_public_cache_set'](key,{'fresh':True})
                assert await ns['_public_cache_get'](key)=={'fresh':True}
            elif case == 'concurrent_fills':
                ready=asyncio.Event();finish=asyncio.Event()
                async def old():
                    assert await ns['_public_cache_get'](key) is None
                    ready.set();await finish.wait();await ns['_public_cache_set'](key,{'stale':True})
                task=asyncio.create_task(old());await ready.wait()
                await ns['_public_cache_clear']();await fill();finish.set();await task
                assert await ns['_public_cache_get'](key)==payload
            elif case == 'bad_payload':
                await client.set(payload_key('a'*32),b'broken-codec')
                assert await ns['_public_cache_get'](key) is None
                await ns['_public_cache_set'](key,payload)
                assert await ns['_public_cache_get'](key)==payload
            elif case == 'media_rejected':
                assert await ns['_public_cache_get'](key) is None
                await ns['_public_cache_set'](key,{'audio':b'ID3'})
                assert await client.get(payload_key('a'*32)) is None
            elif case == 'public_only_invalidation':
                calls.clear();await ns['_public_cache_clear']()
                assert [c[0] for c in calls]==['GET','EVAL']
                assert not ns['_redis_state_enabled']()
                assert not any('reader-content' in str(c) for c in calls)
            elif case == 'invalidation_replay':
                await ns['_public_cache_clear']()
                first_clear=next(c for c in reversed(calls) if c[0]=='EVAL')
                # A fills its epoch, then B invalidates and fills current metadata.
                await fill(); await ns['_public_cache_clear']()
                assert await ns['_public_cache_get'](key) is None
                await ns['_public_cache_set'](key, {'revision':'B'})
                assert await original(*first_clear)==0  # delayed replay of A's exact command
                assert await ns['_public_cache_get'](key)=={'revision':'B'}
            elif case == 'initializer_public_only':
                ns.update(REDIS_URL=url,REDIS_CACHE_FAIL_FAST=True,REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS=.3,
                          REDIS_SOCKET_TIMEOUT_SECONDS=1,_redis_available=False)
                async def forbidden(): raise AssertionError('public-only startup must not configure Redis')
                ns['_configure_redis_cache_policy']=forbidden
                node=next(n for n in TREE.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='initialize_replica_state_backends')
                exec(compile(ast.Module(body=[node],type_ignores=[]),str(SERVER),'exec'),ns)
                with patch('redis.asyncio.from_url',return_value=client):
                    await ns['initialize_replica_state_backends']()
                assert ns['_public_metadata_redis_enabled']() and not ns['_redis_state_enabled']()
                assert re.fullmatch('[0-9a-f]{32}',(await client.get(generation)).decode())
        finally:
            if known:
                assert all(str(k).startswith(prefix+':') for k in known)
                await original('DEL',*known)
            await client.aclose()
    asyncio.run(run())


def test_actual_asgi_public_route_hit_invalidation_and_outage(monkeypatch):
    """Real app/middleware + real isolated Redis; dummy catalogue, no lifecycle startup."""
    if os.environ.get('EARNALISM_REDIS_INTEGRATION') != '1':
        pytest.skip('explicit isolated Redis fixture required')
    url = _endpoint()
    monkeypatch.setenv('MONGODB_URL','mongodb://127.0.0.1:27018/dummy_public_metadata')
    monkeypatch.setenv('JWT_SECRET','dummy-public-metadata-route-secret')
    monkeypatch.setenv('ENABLE_STARTUP_DB_MAINTENANCE','false')
    from types import SimpleNamespace
    import httpx
    async def run():
        from backend import server
        import redis.asyncio as redis
        client=redis.from_url(url,socket_timeout=1,retry_on_timeout=False)
        prefix='public-route-test-'+uuid.uuid4().hex;known=set();original=client.execute_command
        async def record(*args,**kwargs):
            if args[0]=='SET': known.add(args[1])
            if args[0] in {'EVAL','EVAL_RO'}:
                known.update(args[3:3+int(args[2])])
            return await original(*args,**kwargs)
        client.execute_command=record
        class Categories:
            reads=0
            def find(self,*args,**kwargs):return self
            def sort(self,*args):return self
            async def to_list(self,*args):
                self.reads+=1;return [{'name':'dummy category','revision':self.reads}]
        categories=Categories()
        monkeypatch.setattr(server,'db',SimpleNamespace(categories=categories))
        for k,v in {'REDIS_KEY_PREFIX':prefix,'_redis_client':client,'_redis_available':True,
                    'REDIS_PUBLIC_METADATA_ENABLED':True,'REDIS_CACHE_ENABLED':False,
                    'MULTI_REPLICA_ENABLED':False,'RATE_LIMIT_ENABLED':False,'PUBLIC_CACHE_ENABLED':True}.items():
            monkeypatch.setattr(server,k,v)
        monkeypatch.setattr(server,'_public_cache_fill_tickets',ContextVar(prefix,default=None))
        monkeypatch.setattr(server,'_public_cache',OrderedDict())
        await client.set(server._redis_key('public-cache-v2','generation'),uuid.uuid4().hex)
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='http://testserver') as web:
                a=await web.get('/api/categories');b=await web.get('/api/categories')
                assert a.status_code==b.status_code==200 and a.json()==b.json()
                assert categories.reads==1 and 'public' in b.headers.get('cache-control','')
                assert b.headers.get('x-request-id') and b.headers.get('server-timing')
                await server._public_cache_clear()
                c=await web.get('/api/categories');assert c.status_code==200 and categories.reads==2
                assert c.json()!=b.json()
                class Broken:
                    async def execute_command(self,*args):raise ConnectionError('dummy outage')
                monkeypatch.setattr(server,'_redis_client',Broken())
                d=await web.get('/api/categories');assert d.status_code==200 and categories.reads==3
                assert not server._redis_state_enabled()
        finally:
            if known:await original('DEL',*known)
            await client.aclose()
    asyncio.run(run())


def test_codec_failure_does_not_fail_metadata_response():
    class Missing:
        async def execute_command(self, *args): return [b'a'*32, None]
        async def eval(self, *args): raise AssertionError('unserializable payload must not reach Redis')
    async def run():
        ns = bindings(Missing(), 'offline-codec')
        assert await ns['_public_cache_get']('key') is None
        await ns['_public_cache_set']('key', {'unsupported': lambda: None})
        assert ns['_cache_stats']['public-cache_write_error'] == 1
    asyncio.run(run())
