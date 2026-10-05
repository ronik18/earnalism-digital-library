"""Bounded disposable database/cache observations. Never targets production."""
import asyncio
import json
import math
import os
import statistics
import time
import uuid
from urllib.parse import urlparse, parse_qs
from pathlib import Path

import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis

target = urlparse(os.environ.get('MONGODB_URL', ''))
if (os.environ.get('ENVIRONMENT') not in {'uat', 'test'} or target.scheme != 'mongodb'
        or target.netloc != '127.0.0.1:27018'
        or parse_qs(target.query).get('replicaSet') != ['earnalism-uat-rs0']):
    raise SystemExit('Performance benchmark requires explicit disposable loopback UAT configuration')
from backend import server


def summary(values):
    ordered = sorted(values)
    return {"samples": len(values), "p50_ms": statistics.median(values),
            "p95_ms": ordered[math.ceil(len(values) * .95) - 1],
            "p99_ms": ordered[math.ceil(len(values) * .99) - 1], "max_ms": max(values)}


async def main():
    client = AsyncIOMotorClient('mongodb://127.0.0.1:27018/?replicaSet=earnalism-uat-rs0')
    database = client['performance_disposable_' + uuid.uuid4().hex]
    cache = Redis(host='127.0.0.1', port=27019, db=15)
    old_db = server.db
    try:
        await client.admin.command('ping'); await cache.ping()
        server.db = database
        server.RATE_LIMIT_ENABLED = False
        server._redis_available = False
        await database.books.insert_many([{'slug': 'perf-' + str(i), 'is_published': i % 2 == 0, 'created_at': i, 'category_slug': 'fiction'} for i in range(1000)])
        query = {'is_published': True}
        command = {'find': 'books', 'filter': query, 'sort': {'created_at': -1}, 'limit': 500}
        before = await database.command('explain', command, verbosity='executionStats')
        # Existing repository index reproduced only in the disposable database.
        await database.books.create_index([('is_published', 1), ('created_at', -1)])
        after = await database.command('explain', command, verbosity='executionStats')
        plans = {}
        for label, value in [('before', before), ('existing_index', after)]:
            plans[label] = {'winning_plan': value['queryPlanner']['winningPlan'], 'execution': value['executionStats']}
        timings = []
        key = 'performance:' + uuid.uuid4().hex
        await cache.setex(key, 60, json.dumps({'fixture': True}))
        for _ in range(100):
            started = time.perf_counter(); assert await cache.get(key); timings.append((time.perf_counter() - started) * 1000)
        redis_stats = summary(timings)
        redis_stats.update(ttl_seconds=await cache.ttl(key), hit_count=100, miss_count=0, scope='single generated fixture key; not application hit rate')
        endpoints = {}
        transport = httpx.ASGITransport(app=server.app, client=('127.0.0.1', 48101))
        async with httpx.AsyncClient(transport=transport, base_url='http://localhost') as api:
            for route in ['/api/books', '/api/payments/offers', '/api/users/me']:
                samples = []; statuses = []; sizes = []
                for _ in range(30):
                    start = time.perf_counter(); response = await api.get(route)
                    samples.append((time.perf_counter() - start) * 1000); statuses.append(response.status_code); sizes.append(len(response.content))
                endpoints[route] = {**summary(samples), 'statuses': sorted(set(statuses)), 'payload_bytes_max': max(sizes)}
            async def browse():
                start = time.perf_counter(); response = await api.get('/api/books')
                return (time.perf_counter() - start) * 1000, response.status_code
            start = time.perf_counter(); results = await asyncio.gather(*(browse() for _ in range(40)))
            elapsed = time.perf_counter() - start
            load = {**summary([r[0] for r in results]), 'concurrent_requests': 40, 'throughput_rps': 40 / elapsed, 'errors': sum(r[1] != 200 for r in results), 'scope': 'ASGI warm public catalogue; no TCP/production traffic'}
        await cache.delete(key)
        report = {'scope': 'DISPOSABLE_GENERATED_DATA_ASGI', 'mongo_plans': plans, 'redis': redis_stats, 'endpoints': endpoints, 'load': load,
                  'production_indexes_changed': 0, 'limitations': ['Existing index tested on generated representative shape, not the complete production release query.', 'No backend stage instrumentation; DB/serialization breakdown unavailable.', 'No worker throughput or authenticated browser pagination claim.']}
        Path('/tmp/earnalism-performance-backend.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'endpoints': endpoints, 'load': load, 'redis': redis_stats}, indent=2))
    finally:
        server.db = old_db
        await client.drop_database(database.name)
        client.close(); await cache.aclose()


if __name__ == '__main__':
    asyncio.run(main())
