"""Offline handler regressions; no production access or wallet mutation."""
import asyncio
import hashlib
import html
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault('MONGODB_URL', 'mongodb://127.0.0.1:27017/earnalism_test')
os.environ.setdefault('JWT_SECRET', 'reader-preview-boundary-isolated-test-secret')
from backend import server
from backend.domain.reading_pass import canonical_page_records, ReadingPassError

ROOT = Path(__file__).resolve().parents[2]


def request(headers=()):
    return server.Request({'type': 'http', 'method': 'GET', 'headers': list(headers)})


USER = {'id': 'isolated-reader', 'role': 'user', 'status': 'active', 'session_id': 'isolated-auth'}
LEASE_HEADERS = [(b'x-reading-pass-session', b'isolated-lease-session'), (b'x-reading-pass-lease', b'isolated-lease-token')]


@pytest.fixture
def edition(monkeypatch):
    book = {'slug': 'isolated-preview', 'chapters': [{'id': 'c1', 'title': 'Chapter one', 'is_preview': True, 'order': 1}]}
    content = '<p>Original synthetic text. ' + 'ordinary words ' * 400 + 'PROTECTED-END-SENTINEL</p>'
    segment = {'content': content, 'content_sha256': hashlib.sha256(content.encode()).hexdigest(), 'chapter_id': 'c1', 'chapter_title': 'Chapter one', 'page_index': 1}
    manifest = {'segmentation_version': 'retained-s1', 'version': 'retained-m1', 'total_pages': 1}
    read_calls = []
    class Segments:
        async def find_one(self, query, _projection):
            read_calls.append(query)
            return segment if query['page_index'] == 1 else None
    class Activation:
        async def find_one(self, *_):
            return {'active_segmentation_version': 'retained-s1', 'generation': 1}
    async def access(*_, **__): return book
    async def active(*_, **__): return manifest
    async def stored(*_, **__): return manifest
    async def authorize(**__): return {'scope': {'segmentation_version': 'retained-s1', 'manifest_version': 'retained-m1'}}
    monkeypatch.setattr(server, 'READING_PASS_V2_ENABLED', True)
    monkeypatch.setattr(server, 'ENVIRONMENT', 'test')
    monkeypatch.setattr(server, '_reader_book_access_doc', access)
    monkeypatch.setattr(server, '_active_reader_segment_manifest', active)
    monkeypatch.setattr(server, '_stored_reader_segment_manifest', stored)
    monkeypatch.setattr(server.reading_pass_service, 'authorize', authorize)
    monkeypatch.setattr(server, 'db', SimpleNamespace(reader_content_segments=Segments(), reader_segment_activation_state=Activation()))
    return book, segment, read_calls


@pytest.mark.parametrize('principal', [None, USER])
def test_oversized_first_public_unit_never_returns_full_body(edition, principal):
    with pytest.raises(server.HTTPException) as denied:
        asyncio.run(server.reading_pass_book_page('isolated-preview', 1, request(), server.Response(), principal=principal))
    assert denied.value.status_code == 403
    assert denied.value.detail['code'] == 'PREVIEW_REQUIRES_PASS'
    assert 'PROTECTED-END-SENTINEL' not in json.dumps(denied.value.detail)


def test_valid_lease_can_read_original_oversized_first_unit_without_rehashing(edition):
    _, segment, _ = edition
    response = server.Response()
    result = asyncio.run(server.reading_pass_book_page('isolated-preview', 1, request(LEASE_HEADERS), response, principal=USER))
    assert result['content'] == segment['content']
    assert result['content_sha256'] == hashlib.sha256(result['content'].encode()).hexdigest()
    assert result['segmentation_version'] == 'retained-s1' and result['manifest_version'] == 'retained-m1'
    assert response.headers['cache-control'] == 'private, no-store'


@pytest.mark.parametrize('failure', ['LEASE_EXPIRED', 'BALANCE_EXHAUSTED', 'CONTENT_NOT_AUTHORIZED'])
def test_expired_or_invalid_lease_cannot_open_first_unit(edition, monkeypatch, failure):
    async def deny(**__): raise ReadingPassError(failure, 403, 'Synthetic denial')
    monkeypatch.setattr(server.reading_pass_service, 'authorize', deny)
    with pytest.raises(server.HTTPException) as denied:
        asyncio.run(server.reading_pass_book_page('isolated-preview', 1, request(LEASE_HEADERS), server.Response(), principal=USER))
    assert denied.value.detail['code'] == failure
    assert edition[2] == []  # Authorization precedes even the body lookup.


def test_bounded_preview_stays_public_and_zero_session_admission(edition):
    edition[1]['content'] = '<p>Only the bounded preview.</p>'
    edition[1]['content_sha256'] = hashlib.sha256(edition[1]['content'].encode()).hexdigest()
    response = server.Response()
    result = asyncio.run(server.reading_pass_book_page('isolated-preview', 1, request(), response, principal=None))
    assert result['is_preview'] is True
    assert result['content'] == edition[1]['content']
    assert response.headers['cache-control'].startswith('public,')


def test_explicit_short_book_continuation_uses_ordinary_entitlement_service(edition, monkeypatch):
    calls = []
    async def start(**kwargs):
        calls.append(kwargs)
        return {'session_id': 'isolated-real-admission', 'lease_token': 'isolated-token', 'lease_expires_at': '2099-01-01T00:00:00+00:00'}
    async def invalidate(*_): pass
    monkeypatch.setattr(server.reading_pass_service, 'start_session', start)
    monkeypatch.setattr(server, '_invalidate_user_cache', invalidate)
    payload = server.ReadingPassSessionStartIn(device_id='isolated-device', content_type='text', content_id='isolated-preview', canonical_page_index=1, require_protected_text=True)
    asyncio.run(server._reading_pass_start(payload, USER, server.Response(), transfer=False))
    assert len(calls) == 1
    assert calls[0]['scope'] == {'canonical_page_index': 1, 'segmentation_version': 'retained-s1', 'manifest_version': 'retained-m1', 'authority_activation_generation': 1}
    assert calls[0]['prepare_text'] is True and calls[0]['free_entitlement'] is False


@pytest.mark.parametrize('cached', [False, True])
def test_catalog_preview_chapter_is_metadata_only_even_with_retained_cache(edition, monkeypatch, cached):
    body = {'id': 'c1', 'content': 'CACHED-FULL-CHAPTER-SENTINEL', 'is_preview': True}
    async def cache_get(_): return body if cached else None
    async def cache_set(*_): pass
    async def candidate(*_, **__): return edition[0], 'synthetic'
    monkeypatch.setattr(server, '_public_cache_get', cache_get)
    monkeypatch.setattr(server, '_public_cache_set', cache_set)
    monkeypatch.setattr(server, '_is_controlled_public_slug', lambda *_: True)
    monkeypatch.setattr(server, '_find_public_book_candidate', candidate)
    monkeypatch.setattr(server, 'can_expose_reader', lambda *_: True)
    class Books:
        async def find_one(self, *_): return {'chapters': [body]}
    monkeypatch.setattr(server, 'db', SimpleNamespace(books=Books()))
    result = asyncio.run(server.get_book_chapter('isolated-preview', 'c1'))
    assert result['content'] == ''
    assert 'CACHED-FULL-CHAPTER-SENTINEL' not in json.dumps(result)


def test_actual_radharani_first_chapter_is_three_bounded_units_not_three_screens(edition):
    # Existing source is read locally, not copied or modified as a fixture.
    chapter = json.loads((ROOT/'data/controlled_publications/radharani/chapters/chapter-001.json').read_text())
    records = canonical_page_records(book_slug='radharani', chapters=[chapter])
    lengths = [len(html.unescape(server.re.sub(r'<[^>]+>', '', row['content']))) for row in records]
    assert lengths == [3076, 3145, 1089]
    assert len(records) == 3 and all(length <= 3200 for length in lengths)
    edition[1].update(records[0]); edition[1]['chapter_id'] = 'c1'
    original_hash = edition[1]['content_sha256']
    public = asyncio.run(server.reading_pass_book_page('isolated-preview', 1, request(), server.Response(), principal=None))
    entitled = asyncio.run(server.reading_pass_book_page('isolated-preview', 1, request(LEASE_HEADERS), server.Response(), principal=USER))
    assert public['content'] == entitled['content'] == records[0]['content']
    assert public['content_sha256'] == entitled['content_sha256'] == original_hash


@pytest.mark.parametrize('principal', [None, USER])
def test_feature_off_does_not_revive_legacy_full_chapter(edition, monkeypatch, principal):
    monkeypatch.setattr(server, 'READING_PASS_V2_ENABLED', False)
    async def wallet(*_): return 600
    async def content(*_, **__): return 'FULL-LEGACY-BODY-SENTINEL'
    monkeypatch.setattr(server, '_cached_user_wallet_seconds', wallet)
    monkeypatch.setattr(server, '_reader_chapter_content', content)
    result = asyncio.run(server.reader_get_chapter('isolated-preview', 'c1', request(), server.Response(), principal=principal))
    assert result['locked'] is True
    assert 'FULL-LEGACY-BODY-SENTINEL' not in json.dumps(result)


# Independent root review negative cases retained as regressions.
def test_public_unit_rejects_anonymous_lease_headers_before_body_lookup(edition):
    with pytest.raises(server.HTTPException) as denied:
        asyncio.run(server.reading_pass_book_page(
            'isolated-preview', 1, request(LEASE_HEADERS), server.Response(), principal=None))
    assert denied.value.status_code == 401
    assert edition[2] == []


@pytest.mark.parametrize('headers', [[LEASE_HEADERS[0]], [LEASE_HEADERS[1]]])
def test_public_unit_rejects_incomplete_lease_headers_before_body_lookup(edition, headers):
    with pytest.raises(server.HTTPException) as denied:
        asyncio.run(server.reading_pass_book_page(
            'isolated-preview', 1, request(headers), server.Response(), principal=USER))
    assert denied.value.detail['code'] == 'PASS_REQUIRED'
    assert edition[2] == []


def test_public_unit_wrong_publication_lease_denied_before_body_lookup(edition, monkeypatch):
    async def authorize(**_):
        return {'scope': {'segmentation_version': 'retained-s1', 'manifest_version': 'wrong-publication'}}
    monkeypatch.setattr(server.reading_pass_service, 'authorize', authorize)
    with pytest.raises(server.HTTPException) as denied:
        asyncio.run(server.reading_pass_book_page(
            'isolated-preview', 1, request(LEASE_HEADERS), server.Response(), principal=USER))
    assert denied.value.status_code == 409
    assert denied.value.detail['code'] == 'PUBLICATION_VERSION_MISMATCH'
    assert edition[2] == []


def test_public_unit_production_country_denial_precedes_body_lookup(edition, monkeypatch):
    async def authorize(**_):
        return {'entitlement_kind': 'metered', 'scope': {
            'segmentation_version': 'retained-s1', 'manifest_version': 'retained-m1', 'release_country': 'IN'}}
    monkeypatch.setattr(server, 'ENVIRONMENT', 'production')
    monkeypatch.setattr(server, 'PUBLIC_READER_EXPOSURE_ENABLED', True)
    monkeypatch.setattr(server, '_title_text_access_mode', lambda _: 'COMMERCIAL_ENTITLEMENT')
    monkeypatch.setattr(server, '_commercial_india_reader_verdict', lambda *_: False)
    monkeypatch.setattr(server.reading_pass_service, 'authorize', authorize)
    with pytest.raises(server.HTTPException) as denied:
        asyncio.run(server.reading_pass_book_page(
            'isolated-preview', 1, request(LEASE_HEADERS), server.Response(), principal=USER))
    assert denied.value.status_code == 403
    assert denied.value.detail['code'] == 'CONTENT_NOT_AUTHORIZED'
    assert edition[2] == []


def test_short_book_continuation_flag_does_not_override_entitlement_denial(edition, monkeypatch):
    calls = []
    async def deny(**kwargs):
        calls.append(kwargs)
        raise ReadingPassError('BALANCE_EXHAUSTED', 403, 'Synthetic entitlement denial')
    monkeypatch.setattr(server.reading_pass_service, 'start_session', deny)
    payload = server.ReadingPassSessionStartIn(
        device_id='isolated-device', content_type='text', content_id='isolated-preview',
        canonical_page_index=1, require_protected_text=True)
    with pytest.raises(server.HTTPException) as denied:
        asyncio.run(server._reading_pass_start(payload, USER, server.Response(), transfer=False))
    assert denied.value.detail['code'] == 'BALANCE_EXHAUSTED'
    assert len(calls) == 1
    assert calls[0]['free_entitlement'] is False
    assert calls[0]['scope']['canonical_page_index'] == 1


def test_legacy_admin_query_is_not_a_regular_users_content_grant(edition, monkeypatch):
    calls = []
    async def content(*_, **__):
        calls.append(True)
        return 'FORBIDDEN-ADMIN-SPOOF-BODY'
    monkeypatch.setattr(server, '_reader_chapter_content', content)
    spoofed = server.Request({'type': 'http', 'method': 'GET', 'headers': [], 'query_string': b'preview=admin'})
    with pytest.raises(server.HTTPException) as denied:
        asyncio.run(server.reader_get_chapter('isolated-preview', 'c1', spoofed, server.Response(), principal=USER))
    assert denied.value.detail['code'] == 'CANONICAL_PAGE_REQUIRED'
    assert calls == []
