import pytest
from backend.audiobook_preview import clip_mp3, preview_segments, MAX_SOURCE_BYTES, PreviewClipCache, PreviewCapacityError


def frame():
    return bytes.fromhex('fffb9000') + bytes(413)


def test_clip_has_a_hard_decoded_sample_ceiling():
    data, duration = clip_mp3(frame() * 10000, 180000)
    assert 179950 < duration <= 180000
    assert len(data) < 10000 * len(frame())
    assert len(data) % len(frame()) == 0


def test_short_recording_and_final_partial_segment():
    data, duration = clip_mp3(frame() * 30, 1000, complete_source=True)
    assert data == frame() * 30
    assert duration <= 1000
    assert clip_mp3(frame() * 100, 500)[1] <= 500


@pytest.mark.parametrize('data,budget', [(b'not mp3', 180000), (frame(), 180000), (frame(), 180001), (b'x' * (MAX_SOURCE_BYTES + 1), 1)])
def test_invalid_or_incomplete_sources_fail_closed(data, budget):
    with pytest.raises(ValueError):
        clip_mp3(data, budget)


def test_id3_is_not_exposed():
    source = b'ID3\x04\x00\x00\x00\x00\x00\x04' + b'PII!' + frame() * 100
    data, _ = clip_mp3(source, 1000)
    assert data.startswith(frame()) and b'PII!' not in data


def test_budget_spans_segments_and_omits_later_chapters():
    chunks = [{'segment_id': str(i), 'duration_ms': d} for i, d in enumerate((60000, 100000, 120000, 10000))]
    selected = preview_segments({'tracks': [{'chunks': chunks}]})
    assert [budget for _, _, budget in selected] == [60000, 100000, 20000]


def test_xing_lengths_are_rewritten():
    first = bytearray(frame())
    first[36:52] = b'Xing' + (3).to_bytes(4, 'big') + (999999).to_bytes(4, 'big') * 2
    data, _ = clip_mp3(bytes(first) + frame() * 100, 1000)
    assert int.from_bytes(data[44:48], 'big') == len(data) // len(frame())
    assert int.from_bytes(data[48:52], 'big') == len(data)

# Exercise actual endpoint source with synthetic storage, no database/network.
import ast
import asyncio
import re
from pathlib import Path
from types import SimpleNamespace
from fastapi import HTTPException
from starlette.responses import Response


def endpoint_namespace(**overrides):
    tree = ast.parse((Path(__file__).resolve().parents[1] / 'server.py').read_text())
    names = {'_public_preview_package', 'public_audiobook_preview_manifest', 'public_audiobook_preview_segment'}
    nodes = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name in names]
    for n in nodes:
        n.decorator_list = []
    ns = dict(HTTPException=HTTPException, Request=object, Response=Response, asyncio=asyncio, re=re, preview_segments=preview_segments,
        PreviewCapacityError=PreviewCapacityError, _preview_clips=PreviewClipCache())
    ns.update(overrides)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<actual-preview-endpoints>', 'exec'), ns)
    return ns


def package():
    return {'package_version': 'sha256-' + 'a' * 64, 'tracks': [{'chapter_id': 'c1', 'chunks': [
        {'segment_id': 'first', 'duration_ms': 240000, 'assets': {'audio': {'sha256': 'b' * 64, 'storage': {'bucket': 'fixture', 'key': 'clip.mp3', 'version_id': 'immutable-v1'}}}},
        {'segment_id': 'after-preview', 'duration_ms': 10000}]}]}


def test_manifest_contains_only_bounded_preview_urls():
    async def public_book(slug):
        return {'slug': slug}
    ns = endpoint_namespace(_reader_audio_book_for_slug=public_book, _selected_audiobook_package=lambda *_: (package(), '', ''))
    result = asyncio.run(ns['public_audiobook_preview_manifest']('approved', Response()))
    assert result['duration_ms'] == 180000 and len(result['segments']) == 1
    assert '/audiobook/preview/packages/' in result['segments'][0]['audio_url']
    assert 'storage' not in repr(result) and 'timestamps' not in repr(result)


@pytest.mark.parametrize('method,byte_range,status,length', [('GET', None, 200, 100), ('HEAD', None, 200, 0),
    ('GET', 'bytes=90-999999', 206, 10), ('GET', 'bytes=-10', 206, 10), ('GET', 'bytes=100-', 416, 0),
    ('GET', 'bytes=0-1,80-90', 416, 0)])
def test_range_never_addresses_original_recording(method, byte_range, status, length):
    async def public_book(slug):
        return {'slug': slug}
    ns = endpoint_namespace(_reader_audio_book_for_slug=public_book, _selected_audiobook_package=lambda *_: (package(), '', ''),
        _clipped_public_preview=lambda asset, budget: (b'x' * 100, budget))
    request = SimpleNamespace(method=method, headers={'range': byte_range} if byte_range else {})
    result = asyncio.run(ns['public_audiobook_preview_segment']('approved', package()['package_version'], 'first', request))
    assert result.status_code == status and len(result.body) == length
    assert result.headers['cache-control'] == 'private, no-store'
    assert 'location' not in result.headers


@pytest.mark.parametrize('version,segment', [('stale', 'first'), (package()['package_version'], 'after-preview')])
def test_stale_and_post_preview_segments_never_fetch_bytes(version, segment):
    async def public_book(slug):
        return {'slug': slug}
    def forbidden(*_):
        raise AssertionError('no source access')
    ns = endpoint_namespace(_reader_audio_book_for_slug=public_book, _selected_audiobook_package=lambda *_: (package(), '', ''), _clipped_public_preview=forbidden)
    with pytest.raises(HTTPException) as error:
        asyncio.run(ns['public_audiobook_preview_segment']('approved', version, segment, SimpleNamespace(headers={}, method='GET')))
    assert error.value.status_code == 404


def test_held_title_cannot_use_private_package_resolver():
    async def held(slug):
        raise HTTPException(status_code=404)
    ns = endpoint_namespace(_reader_audio_book_for_slug=held)
    with pytest.raises(HTTPException):
        asyncio.run(ns['public_audiobook_preview_manifest']('sredni-vashtar', Response()))


def test_cached_clip_is_not_served_after_public_release_is_revoked():
    async def scenario():
        released = True
        calls = []
        async def public_book(slug):
            if not released:
                raise HTTPException(status_code=404)
            return {'slug': slug}
        def clipped(*_):
            calls.append(1)
            return b'bounded', 100
        ns = endpoint_namespace(_reader_audio_book_for_slug=public_book,
            _selected_audiobook_package=lambda *_: (package(), '', ''), _clipped_public_preview=clipped)
        args = ('approved', package()['package_version'], 'first', SimpleNamespace(method='GET', headers={}))
        assert (await ns['public_audiobook_preview_segment'](*args)).status_code == 200
        released = False
        with pytest.raises(HTTPException) as error:
            await ns['public_audiobook_preview_segment'](*args)
        assert error.value.status_code == 404 and calls == [1]
    asyncio.run(scenario())
