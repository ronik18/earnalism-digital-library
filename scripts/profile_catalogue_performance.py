"""Request-local catalogue profiling on disposable UAT only; no production I/O.

Run with the same guarded environment as platform_backend_benchmark.py.
Instrumentation is installed only by this standalone process, never the API.
"""
import asyncio
import contextvars
import functools
import gzip
import hashlib
import json
import os
import resource
import statistics
import time
import uuid
from collections import Counter
from pathlib import Path

from scripts.platform_backend_benchmark import summary, server
import fastapi.routing
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis

stages = contextvars.ContextVar('performance_stages', default=None)


def record(name, start):
    current = stages.get()
    if current is not None:
        current[name] = current.get(name, 0) + (time.perf_counter() - start) * 1000


def timed(name, fn):
    if asyncio.iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await fn(*args, **kwargs)
            finally:
                record(name, start)
        return async_wrapper
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            record(name, start)
    return wrapper


class Cursor:
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def sort(self, *args):
        self.wrapped = self.wrapped.sort(*args)
        return self

    async def to_list(self, *args):
        start = time.perf_counter()
        try:
            return await self.wrapped.to_list(*args)
        finally:
            record('mongo_query_materialization', start)


class Books:
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def find(self, *args):
        current = stages.get()
        if current is not None:
            current['mongo_queries'] = current.get('mongo_queries', 0) + 1
        return Cursor(self.wrapped.find(*args))


class Database:
    def __init__(self, wrapped):
        self.books = Books(wrapped.books)


class Cache:
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.operations = Counter()

    def __getattr__(self, name):
        fn = getattr(self.wrapped, name)
        async def call(*args, **kwargs):
            self.operations[name] += 1
            start = time.perf_counter()
            try:
                return await fn(*args, **kwargs)
            finally:
                record('redis_' + name, start)
        return call


async def main():
    api_path = '/api/books' + ('?view=library-v1' if os.environ.get('PERF_CATALOGUE_VIEW') == 'library-v1' else '')
    if os.environ.get('PERF_CATALOGUE_STANDARD_RESPONSE') == '1':
        for route in server.app.routes:
            if getattr(route, 'path', None) == '/api/books':
                route.dependant.call = server.list_books
    mongo = AsyncIOMotorClient(os.environ['MONGODB_URL'])
    db = mongo['performance_disposable_' + uuid.uuid4().hex]
    raw_cache = Redis(host='127.0.0.1', port=27019, db=15)
    cache = Cache(raw_cache)
    old_db = server.db
    original = {}
    old_serialize = fastapi.routing.serialize_response
    old_render = server.UTF8JSONResponse.render
    prefix = 'performance:' + uuid.uuid4().hex
    try:
        await mongo.admin.command('ping')
        await raw_cache.ping()
        server.db = Database(db)
        server.RATE_LIMIT_ENABLED = False
        server._redis_client = cache
        server.REDIS_KEY_PREFIX = prefix
        server._redis_available = False
        for name in ['_public_cache_get', '_public_cache_set', '_safe_live_public_projection',
                     '_append_controlled_artifact_projections', '_cache_payload_decode']:
            original[name] = getattr(server, name)
            setattr(server, name, timed(name, original[name]))
        fastapi.routing.serialize_response = timed('fastapi_serialization', old_serialize)
        server.UTF8JSONResponse.render = timed('json_render', old_render)
        await db.books.insert_many([{'slug': 'perf-' + str(i), 'is_published': i % 2 == 0,
                                   'created_at': i, 'category_slug': 'fiction'} for i in range(1000)])
        query = server._controlled_public_book_query({})
        command = {'find': 'books', 'filter': query, 'projection': server.BOOK_SUMMARY_PROJECTION,
                   'sort': {'created_at': -1}, 'limit': 500}
        plans = {}
        for label in ['before', 'existing_indexes']:
            if label == 'existing_indexes':
                await db.books.create_index([('is_published', 1), ('created_at', -1)])
                await db.books.create_index([('slug', 1), ('is_published', 1)])
            explain = await db.command('explain', command, verbosity='executionStats')
            plans[label] = {'winning_plan': explain['queryPlanner']['winningPlan'],
                            'execution': explain['executionStats']}
        report = {'scope': 'DISPOSABLE_UAT_REAL_HANDLER_SYNTHETIC_DB_REPOSITORY_ARTIFACTS',
                  'standard_response_baseline': os.environ.get('PERF_CATALOGUE_STANDARD_RESPONSE') == '1',
                  'query': query, 'mongo_plans': plans, 'concurrency': [], 'cache': {}}
        transport = httpx.ASGITransport(app=server.app, client=('127.0.0.1', 48102))
        async with httpx.AsyncClient(transport=transport, base_url='http://localhost') as api:
            cold = {}; token = stages.set(cold)
            response = await api.get(api_path, headers={'Accept-Encoding': 'identity'})
            stages.reset(token)
            assert response.status_code == 200
            data = response.json()
            body = response.content
            # Cross-process updated_at values can vary. Compare standard and
            # optimized serialization against the SAME exact result, not hashes
            # from two separately constructed catalogues.
            expected = old_render(None, await old_serialize(response_content=data))
            assert body == expected
            fields = Counter()
            for book in data:
                for key, value in book.items():
                    fields[key] += len(json.dumps({key: value}, ensure_ascii=False, separators=(',', ':')).encode())
            report['payload'] = {'titles': len(data), 'json_bytes': len(body), 'gzip_bytes': len(gzip.compress(body)),
                                 'sha256': hashlib.sha256(body).hexdigest(), 'standard_encoding_equal': True,
                                 'cold_stages': cold,
                                 'top_field_bytes': fields.most_common(20)}
            report['scale'] = []
            for size in [52, 75, 100, 150, 200, 500]:
                scaled = [data[i % len(data)] for i in range(size)]
                start = time.perf_counter(); encoded = await old_serialize(response_content=scaled)
                serialize_ms = (time.perf_counter() - start) * 1000
                start = time.perf_counter(); rendered = old_render(None, encoded)
                render_ms = (time.perf_counter() - start) * 1000
                start = time.perf_counter(); compressed = gzip.compress(rendered)
                report['scale'].append({'titles': size, 'serialize_ms': serialize_ms, 'render_ms': render_ms,
                                        'gzip_ms': (time.perf_counter() - start) * 1000,
                                        'bytes': len(rendered), 'gzip_bytes': len(compressed)})
            for mode in ['local', 'redis']:
                server._redis_available = mode == 'redis'
                await server._public_cache_clear()
                cache.operations.clear()
                rows = []
                for _ in range(5):
                    metrics = {}; token = stages.set(metrics)
                    result = await api.get(api_path, headers={'Accept-Encoding': 'identity'})
                    stages.reset(token)
                    assert result.content == body
                    rows.append(metrics)
                report['cache'][mode] = {'requests': rows, 'operations': dict(cache.operations)}
                if mode == 'redis':
                    storage_key = server._public_cache_storage_key(await server._public_cache_generation_value(),
                        server._public_cache_key('books', category='all', q=''))
                    blob = await raw_cache.get(storage_key)
                    report['cache'][mode].update(ttl_seconds=await raw_cache.ttl(storage_key),
                                                  stored_bytes=len(blob or b''))
                    bursts = []
                    for concurrency in [2, 4, 8, 16, 32]:
                        await server._public_cache_clear()
                        cache.operations.clear()
                        miss_metrics = []; latencies = []; statuses = []
                        async def cold_browse():
                            metrics = {}; token = stages.set(metrics); started = time.perf_counter()
                            try:
                                result = await api.get(api_path, headers={'Accept-Encoding': 'identity'})
                                statuses.append(result.status_code)
                                latencies.append((time.perf_counter() - started) * 1000)
                                miss_metrics.append(metrics)
                            finally:
                                stages.reset(token)
                        started = time.perf_counter()
                        await asyncio.gather(*(cold_browse() for _ in range(concurrency)))
                        bursts.append({'requests': concurrency,
                            'mongo_queries': sum(x.get('mongo_queries', 0) for x in miss_metrics),
                            'rebuilds': sum('_append_controlled_artifact_projections' in x for x in miss_metrics),
                            'operations': dict(cache.operations), **summary(latencies),
                            'throughput_rps': concurrency / (time.perf_counter() - started),
                            'errors': sum(status != 200 for status in statuses)})
                    report['cache'][mode]['cold_bursts'] = bursts
                for concurrency in [1, 2, 4, 8, 16, 24, 32, 40]:
                    records = []
                    delays = []
                    async def probe_loop():
                        while True:
                            start = time.perf_counter()
                            await asyncio.sleep(.002)
                            delays.append(max(0, (time.perf_counter() - start - .002) * 1000))
                    async def browse():
                        metrics = {}; token = stages.set(metrics); start = time.perf_counter()
                        try:
                            result = await api.get(api_path, headers={'Accept-Encoding': 'identity'})
                            records.append({'elapsed_ms': (time.perf_counter() - start) * 1000,
                                            'status': result.status_code, 'stages': metrics})
                        finally:
                            stages.reset(token)
                    start = time.perf_counter(); cpu = time.process_time()
                    probe = asyncio.create_task(probe_loop())
                    await asyncio.gather(*(browse() for _ in range(concurrency)))
                    probe.cancel()
                    await asyncio.gather(probe, return_exceptions=True)
                    elapsed = time.perf_counter() - start
                    stage_names = {key for r in records for key in r['stages']}
                    report['concurrency'].append({'cache': mode, 'concurrency': concurrency,
                        **summary([r['elapsed_ms'] for r in records]), 'rps': concurrency / elapsed,
                        'process_cpu_ms': (time.process_time() - cpu) * 1000,
                        'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                        'event_loop_delay_max_ms': max(delays, default=0),
                        'errors': sum(r['status'] != 200 for r in records),
                        'stage_mean_ms': {name: statistics.mean(r['stages'].get(name, 0) for r in records)
                                          for name in stage_names}})
        report['limitations'] = ['ASGI in-process; response write has no TCP/CDN latency.',
            'Synthetic DB returns no approved slugs: catalogue is repository artifact-backed.',
            'Redis timings include event-loop scheduling, not pure wire RTT.',
            'Peak RSS is process lifetime high-water mark on macOS; no pool utilization claim.',
            'One warm burst per concurrency; timing is diagnostic, not field percentiles.']
        print(json.dumps(report, indent=2))
    finally:
        for name, fn in original.items():
            setattr(server, name, fn)
        fastapi.routing.serialize_response = old_serialize
        server.UTF8JSONResponse.render = old_render
        server.db = old_db
        keys = [key async for key in raw_cache.scan_iter(prefix + ':*')]
        if keys:
            await raw_cache.delete(*keys)
        await mongo.drop_database(db.name)
        mongo.close()
        await raw_cache.aclose()


if __name__ == '__main__':
    asyncio.run(main())
