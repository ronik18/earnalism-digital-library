"""Bounded HTTP response benchmark; never a production or browser UAT claim.

Reuse the native transaction fixture. Only the synthetic book's publication
lookup and Redis cache are isolated; auth, refresh, leases, page handlers and
MongoDB transactions are real. No production credential or country is supplied.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import time

import httpx
import pytest

from backend import server
from backend.tests.test_reading_pass_text_admission_mongo_integration import (
    _isolated_database, _seed_retained_content,
)

pytestmark = pytest.mark.skipif(
    os.environ.get('READER_SEGMENT_MONGO_INTEGRATION') != '1',
    reason='requires the explicit loopback regression replica set',
)


def test_real_http_login_refresh_lease_and_twenty_page_responses(monkeypatch):
    slug = 'reader-benchmark-fixture'

    async def fixture_authority(requested_slug, *, admin_preview=False):
        return {'slug': slug, 'chapters': [{'id': 'chapter-001', 'title': 'Fixture', 'order': 1}]} if requested_slug == slug else None

    monkeypatch.setattr(server, 'ENVIRONMENT', 'uat')
    monkeypatch.setattr(server, 'READING_PASS_V2_ENABLED', True)
    monkeypatch.setattr(server, 'RATE_LIMIT_ENABLED', False)
    monkeypatch.setattr(server, 'PUBLIC_READER_EXPOSURE_ENABLED', False)
    monkeypatch.setattr(server, '_redis_state_enabled', lambda: False)
    monkeypatch.setattr(server, '_reader_book_access_doc', fixture_authority)

    async def scenario():
        async with _isolated_database() as database:
            manifest = await _seed_retained_content(database, slug)
            assert manifest['total_pages'] >= 6
            before_segments = await database.reader_content_segments.find({'book_slug': slug}, {'_id': 0}).sort('page_index', 1).to_list(100)
            before_pointer = await database.reader_segment_activation_state.find_one({'book_slug': slug}, {'_id': 0})
            before_manifest = await database.reader_segment_manifests.find_one({'book_slug': slug}, {'_id': 0})
            expected_pages = {row['page_index']: row for row in before_segments}
            transport = httpx.ASGITransport(app=server.app, client=('127.0.0.1', 48100))
            async with httpx.AsyncClient(transport=transport, base_url='https://localhost', headers={'User-Agent': 'IsolatedReaderBenchmark/1'}) as client:
                url = f'/api/reading-pass/books/{slug}'
                for index in range(1, 4):
                    preview = await client.get(f'{url}/pages/{index}')
                    assert preview.status_code == 200 and preview.json()['is_preview'] is True
                assert (await client.get(f'{url}/pages/4')).status_code == 401

                signup = await client.post('/api/users/signup', json={
                    'name': 'Isolated Reader', 'email': 'reader-benchmark@example.com',
                    'password': 'isolated-fixture-password-not-a-production-credential',
                })
                assert signup.status_code == 200
                cookie_headers = signup.headers.get_list('set-cookie')
                assert len(cookie_headers) == 2
                assert all('HttpOnly' in h and 'Secure' in h for h in cookie_headers)
                assert {h.split('=', 1)[0] for h in cookie_headers} == {server.USER_DEVICE_COOKIE, server.USER_REFRESH_COOKIE}
                user_id = signup.json()['user']['id']
                login = await client.post('/api/users/login', json={
                    'email': 'reader-benchmark@example.com',
                    'password': 'isolated-fixture-password-not-a-production-credential',
                })
                assert login.status_code == 200
                client.headers['Authorization'] = 'Bearer ' + signup.json()['token']
                assert (await client.get('/api/users/me')).status_code == 401
                client.headers['Authorization'] = 'Bearer ' + login.json()['token']
                assert (await client.get('/api/users/me')).status_code == 200
                refresh = await client.post('/api/users/refresh')
                assert refresh.status_code == 200
                client.headers['Authorization'] = 'Bearer ' + refresh.json()['token']
                assert (await client.get('/api/users/me')).status_code == 200
                assert (await client.get(f'{url}/pages/4')).status_code == 403
                await database.users.update_one({'id': user_id}, {'$set': {'reading_seconds_balance': 600, 'wallet_seconds': 600}})
                start = await client.post('/api/reading-pass/sessions/start', json={
                    'device_id': 'isolated-reader-benchmark-device', 'device_label': 'Isolated benchmark',
                    'content_type': 'text', 'content_id': slug, 'canonical_page_index': 4,
                })
                assert start.status_code == 200
                lease = start.json()
                client.headers['X-Reading-Pass-Session'] = lease['session_id']
                client.headers['X-Reading-Pass-Lease'] = lease['lease_token']
                timings = []
                for sample in range(20):
                    index = 4 + sample % 3
                    started = time.perf_counter()
                    response = await client.get(f'{url}/pages/{index}')
                    timings.append((time.perf_counter() - started) * 1000)
                    assert response.status_code == 200
                    page = response.json()
                    assert page['content'] == expected_pages[index]['content']
                    assert page['content_sha256'] == hashlib.sha256(page['content'].encode()).hexdigest()
                    assert page['manifest_version'] == manifest['version']
                    assert page['is_preview'] is False
                    assert response.headers['cache-control'] == 'private, no-store'
                client.headers['X-Reading-Pass-Lease'] = 'invalid-isolated-lease'
                assert (await client.get(f'{url}/pages/4')).status_code == 403
                client.headers['X-Reading-Pass-Lease'] = lease['lease_token']
                async with httpx.AsyncClient(transport=transport, base_url='https://localhost', headers=dict(client.headers)) as cookie_less:
                    assert (await cookie_less.get('/api/users/me')).status_code == 401
                    assert (await cookie_less.get(f'{url}/pages/4')).status_code == 401
                assert (await client.post('/api/users/logout')).status_code == 200
                assert (await client.get('/api/users/me')).status_code == 401
                assert (await client.get(f'{url}/pages/4')).status_code == 401
            assert await database.reader_content_segments.find({'book_slug': slug}, {'_id': 0}).sort('page_index', 1).to_list(100) == before_segments
            assert await database.reader_segment_activation_state.find_one({'book_slug': slug}, {'_id': 0}) == before_pointer
            assert await database.reader_segment_manifests.find_one({'book_slug': slug}, {'_id': 0}) == before_manifest
            assert await database.wallet_ledger.count_documents({}) == 0
            wallet = await database.users.find_one({'id': user_id}, {'_id': 0, 'reading_seconds_balance': 1})
            assert wallet['reading_seconds_balance'] == 600
            values = sorted(timings)
            return {
                'schema': 'earnalism.reader-benchmark.v1', 'status': 'PASS',
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'tested_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                'scope': 'ISOLATED_ASGI_REAL_MONGO', 'production_verification': 'NOT_PERFORMED',
                'browser_paint_verification': 'NOT_PERFORMED', 'country_verification': 'NOT_PERFORMED',
                'fixture_title_count': 1, 'protected_page_response_count': len(timings),
                'auth': 'REAL_SIGNUP_LOGIN_REFRESH_COOKIE_BOUND_SESSION_AND_LOGOUT',
                'negative_access_checks': ['guest_page_4', 'superseded_login', 'missing_lease', 'invalid_lease', 'missing_device_cookie', 'logged_out_session'],
                'retained_fixture_versions_unchanged': True, 'fixture_wallet_debit_seconds': 0,
                'page_response_timings': {
                    'samples': len(values), 'median_ms': round(statistics.median(values), 3),
                    'p95_ms': round(values[math.ceil(0.95 * len(values)) - 1], 3),
                    'maximum_ms': round(max(values), 3), 'samples_ms': [round(v, 3) for v in timings],
                    'interpretation': 'Informational ASGI/database response timings; no browser paint or production latency/SLO claim.',
                },
            }

    report = asyncio.run(scenario())
    output = Path(os.environ.get('READER_BENCHMARK_REPORT', 'regression/artifacts/reader-benchmark/report.json'))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
