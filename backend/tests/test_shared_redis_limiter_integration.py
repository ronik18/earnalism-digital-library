"""Actual repository limiter/initializer/caller/middleware; no backend import.

Real tests are opt-in with EARNALISM_REDIS_INTEGRATION=1 and the explicit URL
EARNALISM_REDIS_INTEGRATION_URL=redis://127.0.0.1:<26379..26479>/0. They use the existing
loopback CI fixture, never launch Redis or read REDIS_URL/provider credentials.
All fixture keys have one random private test prefix. No FLUSH/CONFIG/SCAN.
Local qualification cannot authorize a mixed legacy rollout or prove Cluster,
provider ACL, authentication, billing, playback or production capacity.
"""
from __future__ import annotations

import ast
import asyncio
import collections
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from types import SimpleNamespace
from typing import Optional
from urllib.parse import urlparse
import uuid

import pytest

SERVER = Path(__file__).resolve().parents[1] / 'server.py'
WINDOW = 60
LIMIT = 7


def _endpoint(environment=None):
    env = os.environ if environment is None else environment
    if env.get('EARNALISM_REDIS_INTEGRATION') != '1':
        raise ValueError('explicit isolated Redis opt-in required')
    raw = env.get('EARNALISM_REDIS_INTEGRATION_URL', '')
    parsed = urlparse(raw)
    try:
        valid = (parsed.scheme == 'redis' and parsed.hostname == '127.0.0.1'
                 and parsed.port is not None and 26379 <= parsed.port <= 26479
                 and parsed.path == '/0'
                 and not parsed.username and not parsed.password
                 and not parsed.query and not parsed.fragment)
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('exact unauthenticated loopback Redis fixture required')
    return raw


def _source_node(name):
    tree = ast.parse(SERVER.read_text())
    return next(n for n in tree.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)


def _bindings(client, prefix, *, host_monotonic=1):
    from starlette.requests import Request
    tree = ast.parse(SERVER.read_text())
    assignment = next(n for n in tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(x, ast.Name) and x.id == '_REDIS_RATE_LIMIT_ATOMIC_SCRIPT'
                              for x in n.targets))
    script = ast.literal_eval(assignment.value)
    ns = {
        'Optional': Optional, 'Request': Request, 'hashlib': hashlib,
        'uuid': uuid, 're': re, 'REDIS_KEY_PREFIX': prefix,
        '_REDIS_RATE_LIMIT_ATOMIC_SCRIPT': script, '_redis_client': client,
        'RATE_LIMIT_WINDOW_SECONDS': WINDOW, 'RATE_LIMIT_ENABLED': True,
        'time': SimpleNamespace(monotonic=lambda: host_monotonic,
                                perf_counter=time.perf_counter),
        '_rate_limit_scope': lambda path: ('reading-pass', LIMIT),
        '_rate_limit_identity': lambda request: 'fixture',
        '_redis_state_enabled': lambda: True,
        '_rate_limit_hits': collections.defaultdict(collections.deque),
        '_sweep_rate_limit_buckets': lambda now: None,
    }
    for name in ('_redis_key', '_redis_rate_limit_retry_after', '_rate_limit_retry_after'):
        exec(compile(ast.Module(body=[_source_node(name)], type_ignores=[]),
                     str(SERVER), 'exec'), ns)
    return ns


def _key(ns, identity, *, legacy=False):
    digest = hashlib.sha256(identity.encode()).hexdigest()
    return ns['_redis_key']('rate-limit' if legacy else 'rate-limit-v2-server-time', digest)


def _request(method='GET', path='/api/reading-pass/fixture'):
    return SimpleNamespace(method=method, url=SimpleNamespace(path=path))


REAL = pytest.mark.skipif(os.environ.get('EARNALISM_REDIS_INTEGRATION') != '1',
                          reason='explicit existing loopback Redis fixture required')


@pytest.mark.parametrize('bad', [
    '', 'redis://localhost:26379/0', 'redis://127.0.0.1:6379/0',
    'redis://127.0.0.1:26379/1', 'rediss://127.0.0.1:26379/0',
    'redis://127.0.0.1:26378/0', 'redis://127.0.0.1:26480/0',
    'redis://user:password@127.0.0.1:26379/0',
    'redis://127.0.0.1:26379/0?retry_on_timeout=True',
    'redis://example.com:26379/0',
])
def test_endpoint_rejects_nonfixture_context(bad):
    with pytest.raises(ValueError):
        _endpoint({'EARNALISM_REDIS_INTEGRATION': '1',
                   'EARNALISM_REDIS_INTEGRATION_URL': bad})


def test_endpoint_requires_opt_in_even_with_loopback():
    with pytest.raises(ValueError):
        _endpoint({'EARNALISM_REDIS_INTEGRATION_URL': 'redis://127.0.0.1:26379/0'})


@pytest.mark.parametrize('port', [26379, 26479])
def test_endpoint_accepts_only_explicit_ci_fixture(port):
    assert _endpoint({'EARNALISM_REDIS_INTEGRATION': '1',
                      'EARNALISM_REDIS_INTEGRATION_URL': f'redis://127.0.0.1:{port}/0'})


def test_actual_helper_call_contract_and_fresh_internal_uuid():
    class Client:
        def __init__(self):
            self.calls = []
        async def eval(self, *args):
            self.calls.append(args)
            return 0
    async def run():
        client = Client()
        ns = _bindings(client, 'offline-fixture')
        assert await ns['_redis_rate_limit_retry_after']('synthetic', 1, 1) is None
        assert await ns['_redis_rate_limit_retry_after']('synthetic', 1, 10**12) is None
        first, second = client.calls
        assert first[1] == 2 and first[2:4] == second[2:4]
        assert first[-1] != second[-1]
        assert 'TIME' in first[0] and 'ZSCORE' in first[0]
        for method, path in [('OPTIONS', '/api/reading-pass/fixture'), ('GET', '/healthz')]:
            assert await ns['_rate_limit_retry_after'](_request(method, path)) is None
        assert len(client.calls) == 2
    asyncio.run(run())


async def _process_worker(url, prefix, directory, label, origin):
    if url != _endpoint():
        raise ValueError('worker endpoint must match admitted loopback fixture')
    if not re.fullmatch(r'limiter-test-[0-9a-f]{32}', prefix):
        raise ValueError('private synthetic fixture prefix required')
    import redis.asyncio as redis
    client = redis.from_url(url, socket_connect_timeout=.3, socket_timeout=1,
                            retry_on_timeout=False)
    directory = Path(directory)
    try:
        ns = _bindings(client, prefix, host_monotonic=origin)
        await client.ping()
        (directory / f'{label}.ready').write_text('ready')
        until = time.monotonic() + 10
        while not (directory / 'start').exists():
            if time.monotonic() >= until:
                raise TimeoutError('bounded child barrier')
            await asyncio.sleep(.005)
        began = time.monotonic()
        outcomes = await asyncio.gather(*(
            ns['_rate_limit_retry_after'](_request()) for _ in range(50)))
        (directory / f'{label}.json').write_text(json.dumps({
            'pid': os.getpid(), 'started': began, 'finished': time.monotonic(),
            'admitted': sum(x is None for x in outcomes),
            'denied': sum(type(x) is int and x >= 1 for x in outcomes),
        }))
    finally:
        await client.aclose()


def test_direct_worker_rejects_unadmitted_endpoint_before_client(monkeypatch, tmp_path):
    monkeypatch.setenv('EARNALISM_REDIS_INTEGRATION', '1')
    monkeypatch.setenv('EARNALISM_REDIS_INTEGRATION_URL', 'redis://127.0.0.1:26379/0')
    with pytest.raises(ValueError, match='worker endpoint'):
        asyncio.run(_process_worker('redis://example.com:26379/0',
                                    'limiter-test-' + 'a' * 32, tmp_path, 'A', 1))


def test_direct_worker_requires_explicit_opt_in(monkeypatch, tmp_path):
    monkeypatch.delenv('EARNALISM_REDIS_INTEGRATION', raising=False)
    with pytest.raises(ValueError, match='opt-in'):
        asyncio.run(_process_worker('redis://127.0.0.1:26379/0',
                                    'limiter-test-' + 'a' * 32, tmp_path, 'A', 1))


@REAL
def test_two_distinct_processes_share_atomic_limit_and_server_clock(tmp_path):
    import redis.asyncio as redis
    url = _endpoint()
    prefix = 'limiter-test-' + uuid.uuid4().hex
    processes = []
    try:
        for label, origin in [('A', '1'), ('B', '1000000000000')]:
            log = open(tmp_path / f'{label}.log', 'w')
            processes.append(subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), '--worker', url,
                 prefix, str(tmp_path), label, origin], stdout=log, stderr=log,
                env={'PATH': os.environ.get('PATH', ''), 'HOME': os.environ.get('HOME', ''),
                     'EARNALISM_REDIS_INTEGRATION': '1',
                     'EARNALISM_REDIS_INTEGRATION_URL': url}))
        until = time.monotonic() + 15
        while not all((tmp_path / f'{label}.ready').exists() for label in ('A', 'B')):
            assert all(p.poll() is None for p in processes), 'child failed before barrier'
            assert time.monotonic() < until, 'bounded process readiness deadline'
            time.sleep(.01)
        (tmp_path / 'start').write_text('start')
        for process in processes:
            assert process.wait(timeout=15) == 0
        rows = [json.loads((tmp_path / f'{label}.json').read_text()) for label in ('A', 'B')]
        assert len({x['pid'] for x in rows}) == 2
        assert sum(x['admitted'] for x in rows) == LIMIT
        assert sum(x['denied'] for x in rows) == 100 - LIMIT
        async def verify():
            client = redis.from_url(url, socket_connect_timeout=.3, socket_timeout=1,
                                    retry_on_timeout=False)
            try:
                ns = _bindings(client, prefix)
                assert await client.zcard(_key(ns, 'reading-pass:fixture')) == LIMIT
                scores = await client.zrange(_key(ns, 'reading-pass:fixture'), 0, -1, withscores=True)
                sec, usec = await client.time()
                assert all(abs(sec + usec / 1e6 - score) < 10 for _, score in scores)
            finally:
                await client.delete(_key(ns, 'reading-pass:fixture'),
                                    _key(ns, 'reading-pass:fixture', legacy=True))
                await client.aclose()
        asyncio.run(verify())
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)


@REAL
def test_real_boundaries_legacy_state_and_permission_failure():
    import redis.asyncio as redis
    from redis.exceptions import ResponseError
    async def run():
        client = redis.from_url(_endpoint(), socket_connect_timeout=.3,
                                socket_timeout=1, retry_on_timeout=False)
        ns = _bindings(client, 'limiter-test-' + uuid.uuid4().hex)
        identities = ['boundary', 'cutoff', 'legacy', 'legacy-short']
        try:
            sec, usec = await client.time()
            now = sec + usec / 1e6
            await client.zadd(_key(ns, 'boundary'), {'old': now - 61, 'live': now - 1})
            assert 1 <= await ns['_redis_rate_limit_retry_after']('boundary', 1, 10**12) <= WINDOW
            assert await client.zcard(_key(ns, 'boundary')) == 1
            await client.zadd(_key(ns, 'cutoff'), {'cutoff': now - WINDOW})
            assert await ns['_redis_rate_limit_retry_after']('cutoff', 1, -10**12) is None
            assert 1 <= await client.ttl(_key(ns, 'cutoff')) <= 2 * WINDOW
            await client.zadd(_key(ns, 'legacy', legacy=True), {'retained': 100})
            await client.expire(_key(ns, 'legacy', legacy=True), WINDOW)
            assert await ns['_redis_rate_limit_retry_after']('legacy', 100, 10**12) >= 1
            assert await client.zscore(_key(ns, 'legacy', legacy=True), 'retained') == 100
            assert not await client.exists(_key(ns, 'legacy'))
            await client.persist(_key(ns, 'legacy', legacy=True))
            with pytest.raises(RuntimeError):
                await ns['_redis_rate_limit_retry_after']('legacy', 100, 1)
            await client.zadd(_key(ns, 'legacy-short', legacy=True), {'retained': 100})
            await client.pexpire(_key(ns, 'legacy-short', legacy=True), 100)
            assert await ns['_redis_rate_limit_retry_after']('legacy-short', 1, 0) >= 1
            await asyncio.sleep(.15)
            assert await ns['_redis_rate_limit_retry_after']('legacy-short', 1, 0) is None
            class Denied:
                async def eval(self, *args):
                    raise ResponseError('NOPERM synthetic')
            denied = _bindings(Denied(), 'offline-denied')
            with pytest.raises(ResponseError):
                await denied['_redis_rate_limit_retry_after']('fixture', 1, 0)
        finally:
            for identity in identities:
                await client.delete(_key(ns, identity), _key(ns, identity, legacy=True))
            await client.aclose()
    asyncio.run(run())


@REAL
def test_actual_initializer_transport_retry_preserves_one_admission_effect():
    import redis.asyncio as redis
    from redis.exceptions import TimeoutError as RedisTimeoutError
    class LostReplyRedis(redis.Redis):
        injected = False
        eval_replies = 0
        async def parse_response(self, connection, command_name, **options):
            response = await super().parse_response(connection, command_name, **options)
            name = command_name.decode() if isinstance(command_name, bytes) else command_name
            if name.upper() == 'EVAL':
                self.eval_replies += 1
                if self.injected:
                    self.injected = False
                    raise RedisTimeoutError('synthetic lost reply after actual EVAL execution')
            return response
    async def run():
        async def no_config_mutation():
            pass
        init = {
            'REDIS_CACHE_ENABLED': True, 'MULTI_REPLICA_ENABLED': True,
            'REDIS_URL': _endpoint(), 'REDIS_CACHE_FAIL_FAST': True,
            'REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS': 2.0,
            'REDIS_SOCKET_TIMEOUT_SECONDS': 2.0,
            '_configure_redis_cache_policy': no_config_mutation,
            'logger': logging.getLogger('isolated-limiter-test'),
        }
        exec(compile(ast.Module(body=[_source_node('initialize_replica_state_backends')],
                                type_ignores=[]), str(SERVER), 'exec'), init)
        factory = redis.from_url
        try:
            redis.from_url = LostReplyRedis.from_url
            await init['initialize_replica_state_backends']()
        finally:
            redis.from_url = factory
        client = init['_redis_client']
        ns = _bindings(client, 'limiter-test-' + uuid.uuid4().hex)
        identity = 'lost-reply'
        try:
            assert client.connection_pool.connection_kwargs['retry_on_timeout'] is True
            connection = await client.connection_pool.get_connection('PING')
            try:
                assert connection.retry._retries == 1  # pinned redis-py5.0.8
            finally:
                await client.connection_pool.release(connection)
            client.injected = True
            assert await ns['_redis_rate_limit_retry_after'](identity, 1, 10**12) is None
            assert client.eval_replies == 2  # transport replay is intentional, effect is idempotent
            assert await client.zcard(_key(ns, identity)) == 1
            assert 1 <= await client.ttl(_key(ns, identity)) <= 2 * WINDOW
            assert await ns['_redis_rate_limit_retry_after'](identity, 1, 0) >= 1
        finally:
            await client.delete(_key(ns, identity), _key(ns, identity, legacy=True))
            await client.aclose()
    asyncio.run(run())


@pytest.mark.parametrize('failure', ['connection', 'timeout'])
def test_actual_middleware_429_retry_after_and_outage_fail_closed(failure):
    import httpx
    from fastapi import FastAPI
    from starlette.requests import Request
    from starlette.responses import JSONResponse, Response
    from redis.exceptions import ConnectionError as RedisConnectionError
    from redis.exceptions import TimeoutError as RedisTimeoutError
    class Client:
        error = None
        async def eval(self, *args):
            if self.error:
                raise self.error('synthetic Redis failure')
            return 3
    async def run():
        client = Client()
        ns = _bindings(client, 'offline-middleware')
        ns.update({
            'Request': Request, 'Response': Response, 'JSONResponse': JSONResponse,
            'UTF8JSONResponse': JSONResponse, 'ENVIRONMENT': 'uat',
            'logger': logging.getLogger('isolated-middleware-test'), '_json': json,
            '_shutdown_state': {'draining': False, 'inflight': 0},
            '_request_body_limit_for_path': lambda path: 1_000_000,
            '_is_public_anonymous_cacheable_response': lambda *args: False,
            '_client_ip': lambda request: '127.0.0.1',
        })
        for name in ('_error_payload', '_security_headers', '_json_error_response',
                     'production_hardening_middleware'):
            node = _source_node(name)
            node.decorator_list = []
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(SERVER), 'exec'), ns)
        app = FastAPI()
        app.middleware('http')(ns['production_hardening_middleware'])
        route_calls = []
        @app.get('/api/reading-pass/fixture')
        async def route():
            route_calls.append(1)
            return {'fixture': True}
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url='https://localhost',
                                     follow_redirects=False) as http:
            denied = await http.get('/api/reading-pass/fixture')
            assert denied.status_code == 429
            assert denied.headers['retry-after'] == '3'
            assert denied.json()['detail']['code'] == 'RATE_LIMITED'
            assert denied.headers['x-content-type-options'] == 'nosniff'
            assert denied.headers['cache-control'] == 'no-store'
            client.error = RedisConnectionError if failure == 'connection' else RedisTimeoutError
            unavailable = await http.get('/api/reading-pass/fixture')
            assert unavailable.status_code == 500  # existing failure contract, not invented503
        assert not route_calls
        assert ns['_shutdown_state']['inflight'] == 0
    asyncio.run(run())


if __name__ == '__main__':
    assert sys.argv[1] == '--worker'
    asyncio.run(_process_worker(sys.argv[2], sys.argv[3], sys.argv[4],
                                sys.argv[5], float(sys.argv[6])))
