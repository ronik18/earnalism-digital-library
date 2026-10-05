"""Serialization equivalence, not a flaky wall-clock performance assertion."""
import asyncio
import json
import os
from datetime import datetime, timezone

import pytest
import httpx
from fastapi.encoders import jsonable_encoder

os.environ.setdefault('MONGODB_URL', 'mongodb://localhost:27017/earnalism_test')
os.environ.setdefault('JWT_SECRET', 'catalogue-serialization-fixture-secret')
from backend import server


def run(coroutine):
    # Do not reset the global loop policy before legacy Motor import fixtures.
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()


def test_catalogue_response_preserves_standard_encoding_and_builder_arguments(monkeypatch):
    payload = [{'title': 'বাংলা — Édition', 'slug': 'fixture', 'created_at': datetime(2020, 1, 2, tzinfo=timezone.utc),
                'chapters': [{'id': 'chapter-1', 'title': 'First', 'is_preview': False}],
                'audio_enabled': False, 'audio_url': '', 'reader_enabled': True, 'nested': [None, True, 1]}]
    calls = []
    async def builder(**kwargs):
        calls.append(kwargs)
        return payload
    monkeypatch.setattr(server, 'list_books', builder)
    response = run(server.list_books_response(category='fiction', q='বাংলা'))
    assert calls == [{'category': 'fiction', 'q': 'বাংলা'}]
    assert response.status_code == 200
    assert response.body == server.UTF8JSONResponse(jsonable_encoder(payload)).body
    assert json.loads(response.body)[0]['audio_enabled'] is False
    assert response.headers['content-type'] == 'application/json; charset=utf-8'


def test_catalogue_response_does_not_silently_stringify_unsupported_values(monkeypatch):
    class Unsupported:
        __slots__ = ()
    async def builder(**kwargs):
        return [{'bad': Unsupported()}]
    monkeypatch.setattr(server, 'list_books', builder)
    with pytest.raises(ValueError):
        run(server.list_books_response())


def test_catalogue_response_rejects_nonfinite_numbers(monkeypatch):
    async def builder(**kwargs):
        return [{'bad': float('nan')}]
    monkeypatch.setattr(server, 'list_books', builder)
    with pytest.raises(ValueError):
        run(server.list_books_response())


def test_catalogue_openapi_keeps_operation_identity_and_filters():
    route = next(route for route in server.app.routes if getattr(route, 'path', '') == '/api/books')
    assert route.operation_id == 'list_books_api_books_get'
    assert [parameter.name for parameter in route.dependant.query_params] == ['category', 'q']


def test_http_catalogue_keeps_gzip_and_authorization_cache_boundaries(monkeypatch):
    # Use the existing accepted artifact so the outer runtime rights middleware
    # is exercised, not bypassed with an invented public-title approval.
    payload = server._append_controlled_artifact_projections([])
    assert payload
    async def builder(**kwargs):
        return payload
    monkeypatch.setattr(server, 'list_books', builder)
    monkeypatch.setattr(server, 'RATE_LIMIT_ENABLED', False)
    monkeypatch.setattr(server, 'ENVIRONMENT', 'uat')
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url='http://localhost') as client:
            anonymous = await client.get('/api/books', headers={'accept-encoding': 'gzip'})
            identified = await client.get('/api/books', headers={'authorization': 'Bearer synthetic-cache-boundary-fixture'})
        assert anonymous.status_code == identified.status_code == 200
        assert anonymous.json() == identified.json() == payload
        assert anonymous.headers['content-encoding'] == 'gzip'
        assert anonymous.headers['cache-control'].startswith('public')
        assert not identified.headers.get('cache-control', '').startswith('public')
    run(exercise())
