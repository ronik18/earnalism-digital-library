"""Synthetic A1.2 vectors for the current media transport contract."""

from __future__ import annotations

import asyncio
import importlib
import os
import sys
import threading
import time
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_media_a12")
os.environ.setdefault("JWT_SECRET", "media-a12-synthetic")
server = importlib.import_module("backend.server")


@pytest.fixture(autouse=True)
def restore_event_loop_after_characterization():
    yield
    asyncio.set_event_loop(asyncio.new_event_loop())


@pytest.mark.parametrize(
    ("header", "size", "expected_range", "expected_status", "well_formed"),
    [
        ("", 2048, None, 200, False), ("bytes=0-0", 2048, "bytes=0-0", 206, True),
        ("bytes=0-1023", 2048, "bytes=0-1023", 206, True), ("bytes=1024-", 2048, "bytes=1024-2047", 206, True),
        ("bytes=-1", 2048, "bytes=2047-2047", 206, True), ("bytes=-1024", 2048, "bytes=1024-2047", 206, True),
        ("bytes=-4096", 2048, "bytes=0-2047", 206, True), ("bytes=0-4096", 2048, "bytes=0-2047", 206, True),
        ("bytes=2048-", 2048, None, 416, True), ("bytes=2049-", 2048, None, 416, True),
        ("bytes=1024-1023", 2048, None, 416, True), ("bytes=-0", 2048, None, 416, False),
        ("bytes=", 2048, None, 416, False), ("items=0-1", 2048, None, 416, False),
        ("bytes0-1", 2048, None, 416, False), ("bytes=a-b", 2048, None, 416, False),
        ("bytes=0-0,2-3", 2048, None, 416, False), (" bytes=0-0 ", 2048, "bytes=0-0", 206, True),
        ("bytes= 0-0", 2048, None, 416, False), ("bytes=0-0", 0, None, 416, True),
        ("bytes=0-0", 1, "bytes=0-0", 206, True),
    ],
)
def test_range_vectors_remain_exact(header, size, expected_range, expected_status, well_formed):
    byte_range, status = server._parse_byte_range(header, size)
    assert (byte_range, status) == (expected_range, expected_status)
    assert server._single_range_header_is_well_formed(header) is well_formed
    if byte_range:
        assert server._content_range_header(byte_range, size) == f"bytes {byte_range[6:]}/{size}"
        start, end = (int(value) for value in byte_range[6:].split("-"))
        assert server._range_content_length(byte_range, size) == end - start + 1


@pytest.mark.parametrize(
    ("requested", "content_range", "content_length", "expected"),
    [
        ("bytes=0-3", "bytes 0-3/10", 4, True), ("bytes=0-99", "bytes 0-9/10", 10, True),
        ("bytes=-4", "bytes 6-9/10", 4, True), ("bytes=0-3", "bytes 1-3/10", 3, False),
        ("bytes=0-3", "bytes 0-2/10", 3, False), ("bytes=0-3", "bytes 0-3/11", 4, True),
        ("bytes=0-3", "bytes 0-3/10", 3, False), ("bytes=0-3", "invalid", 4, False),
        ("bytes=0-3", "", 4, False),
    ],
)
def test_upstream_range_response_vectors_remain_exact(requested, content_range, content_length, expected):
    assert server._range_response_matches_request(requested, content_range, content_length) is expected


def test_etag_vectors_remain_current_weak_string_matching_behavior():
    request = lambda value: types.SimpleNamespace(headers={} if value is None else {"if-none-match": value})
    assert server._client_etag_matches(request(None), '"value"') is False
    assert server._client_etag_matches(request('"value"'), "") is False
    assert server._client_etag_matches(request('"value"'), '"value"') is True
    assert server._client_etag_matches(request('"other", "value"'), '"value"') is True
    assert server._client_etag_matches(request("*"), '"value"') is True
    assert server._client_etag_matches(request('W/"value"'), 'W/"value"') is True
    assert server._client_etag_matches(request('  "value"  '), '"value"') is True


def test_storage_url_key_and_missing_configuration_vectors(monkeypatch):
    store = {"name": "synthetic", "endpoint": "https://objects.example.test", "region": "test-1", "bucket": "synthetic-bucket", "access_key_id": "id", "secret_access_key": "secret"}
    monkeypatch.setattr(server, "_b2_storage_configs", lambda: [store])
    path_url = "https://objects.example.test/synthetic-bucket/folder%20one/book.mp3"
    virtual_url = "https://synthetic-bucket.objects.example.test/folder%20one/book.mp3"
    assert server._b2_storage_for_url(path_url) is store
    assert server._b2_storage_for_url(virtual_url) is store
    assert server._b2_key_from_url(path_url, store) == "folder one/book.mp3"
    assert server._b2_key_from_url(virtual_url, store) == "folder one/book.mp3"
    assert server._b2_storage_for_url("https://objects.example.test/wrong-bucket/book.mp3") is None
    assert server._b2_storage_for_url("https://wrong.example.test/synthetic-bucket/book.mp3") is None
    assert server._b2_storage_for_url("https://objects.example.test/") is None
    assert server._b2_storage_for_url("ftp://objects.example.test/synthetic-bucket/book.mp3") is None
    assert server._b2_storage_for_url("https://unknown.backblazeb2.com/bucket/book.mp3") is None
    assert server._b2_is_configured(store) is True
    assert server._b2_is_configured({"name": "incomplete"}) is False


def test_b2_client_registry_is_lazy_one_per_store_and_reused(monkeypatch):
    stores = [
        {"name": "first", "endpoint": "https://objects-1.example.test", "region": "test-1", "bucket": "bucket-1", "access_key_id": "id-1", "secret_access_key": "secret-1"},
        {"name": "second", "endpoint": "https://objects-2.example.test", "region": "test-2", "bucket": "bucket-2", "access_key_id": "id-2", "secret_access_key": "secret-2"},
    ]
    calls = []
    monkeypatch.setattr(server, "_b2_storage_configs", lambda: stores)
    monkeypatch.setattr(server, "_b2_s3_clients", {})
    monkeypatch.setitem(sys.modules, "boto3", types.SimpleNamespace(client=lambda *args, **kwargs: calls.append((args, kwargs)) or object()))
    config_module = types.ModuleType("botocore.config")
    config_module.Config = lambda **kwargs: kwargs
    monkeypatch.setitem(sys.modules, "botocore.config", config_module)
    assert server._b2_s3_clients == {}
    first = server._b2_client(stores[0])
    assert server._b2_client(stores[0]) is first
    second = server._b2_client(stores[1])
    assert first is not second and set(server._b2_s3_clients) == {"first", "second"}
    assert [kwargs["endpoint_url"] for _args, kwargs in calls] == [stores[0]["endpoint"], stores[1]["endpoint"]]
    for _args, kwargs in calls:
        assert kwargs["config"] == {
            "connect_timeout": 3,
            "read_timeout": 30,
            "max_pool_connections": 20,
            "retries": {"mode": "standard", "max_attempts": 3},
            "tcp_keepalive": True,
            "s3": {"addressing_style": "path"},
        }


def test_storage_wrappers_keep_kwargs_and_thread_boundary():
    main_thread = threading.get_ident()
    calls = []
    class FakeS3:
        def head_object(self, **kwargs):
            calls.append(("head", kwargs, threading.get_ident()))
            return {"ContentLength": 4}
        def get_object(self, **kwargs):
            calls.append(("get", kwargs, threading.get_ident()))
            return {"ContentLength": 4, "Body": object()}
    fake = FakeS3()
    assert asyncio.run(server._b2_head_object(fake, bucket="bucket", key="object", version_id="v1"))["ContentLength"] == 4
    assert asyncio.run(server._b2_get_object(fake, bucket="bucket", key="object", byte_range="bytes=0-3", version_id="v1"))["ContentLength"] == 4
    assert calls[0][1] == {"Bucket": "bucket", "Key": "object", "VersionId": "v1"}
    assert calls[1][1] == {"Bucket": "bucket", "Key": "object", "Range": "bytes=0-3", "VersionId": "v1"}
    assert all(thread_id != main_thread for _name, _kwargs, thread_id in calls)


def test_streaming_vectors_are_bounded_and_close_on_normal_exception_and_early_close():
    class Body:
        def __init__(self, chunks, fail=False): self.chunks, self.fail, self.reads, self.closes = list(chunks), fail, [], 0
        def read(self, size):
            self.reads.append(size)
            if self.fail: raise RuntimeError("synthetic read failure")
            return self.chunks.pop(0) if self.chunks else b""
        def close(self): self.closes += 1
    normal = Body([b"a" * (1024 * 1024), b"b" * 7])
    chunks = list(server._streaming_body_iterator(normal))
    assert [len(chunk) for chunk in chunks] == [1024 * 1024, 7]
    assert normal.reads == [1024 * 1024, 1024 * 1024, 1024 * 1024] and normal.closes == 1
    empty = Body([])
    assert list(server._streaming_body_iterator(empty)) == [] and empty.closes == 1
    failing = Body([], fail=True)
    with pytest.raises(RuntimeError, match="synthetic"):
        list(server._streaming_body_iterator(failing))
    assert failing.closes == 1
    early = Body([b"first", b"second"])
    iterator = server._streaming_body_iterator(early)
    assert next(iterator) == b"first"
    iterator.close()
    assert early.closes == 1


def test_audio_async_streaming_is_off_loop_and_closes_on_early_disconnect():
    main_thread = threading.get_ident()

    class Body:
        def __init__(self): self.read_threads, self.closes, self.remaining = [], 0, [b"audio", b""]
        def read(self, _size):
            self.read_threads.append(threading.get_ident())
            return self.remaining.pop(0)
        def close(self): self.closes += 1

    body = Body()

    async def consume_then_disconnect():
        iterator = server._audio_streaming_body_iterator(body)
        assert await anext(iterator) == b"audio"
        await iterator.aclose()

    before = server.media_streaming.streaming_metrics_snapshot()
    asyncio.run(consume_then_disconnect())
    after = server.media_streaming.streaming_metrics_snapshot()
    assert body.read_threads == [thread_id for thread_id in body.read_threads if thread_id != main_thread]
    assert body.closes == 1
    assert after["opened"] == before["opened"] + 1
    assert after["closed"] == before["closed"] + 1
    assert after["cancelled"] == before["cancelled"] + 1
    assert after["chunks_emitted"] == before["chunks_emitted"] + 1
    assert after["bytes_emitted"] == before["bytes_emitted"] + len(b"audio")
    assert after["byte_buckets"]["le_64k"] >= before["byte_buckets"].get("le_64k", 0) + 1


def test_audio_async_streaming_closes_before_first_byte_without_blocking_heartbeat():
    class SlowBody:
        def __init__(self): self.closes = 0
        def read(self, _size):
            time.sleep(0.03)
            return b"audio"
        def close(self): self.closes += 1

    body = SlowBody()

    async def verify():
        iterator = server._audio_streaming_body_iterator(body)
        await iterator.aclose()
        assert body.closes == 1

        delayed = server._audio_streaming_body_iterator(SlowBody())
        read_task = asyncio.create_task(anext(delayed))
        started = time.perf_counter()
        await asyncio.sleep(0.002)
        heartbeat_delay = time.perf_counter() - started
        await read_task
        await delayed.aclose()
        return heartbeat_delay

    assert asyncio.run(verify()) < 0.02


def test_media_policy_and_storage_error_vectors_remain_exact():
    assert server._audio_asset_content_type("mp3") == "audio/mpeg"
    assert server._audio_asset_content_type("timestamps", "application/octet-stream") == "application/json"
    assert server._audio_asset_content_type("vtt", "application/octet-stream") == "text/vtt"
    assert server._audio_asset_content_type("unknown", "text/plain") == "text/plain"
    assert server._audio_asset_content_type("unknown") == "application/octet-stream"
    assert server._audio_asset_cache_control("mp3") == "private, max-age=600, stale-while-revalidate=3600"
    assert server._audio_asset_cache_control("metadata") == "private, max-age=3600, stale-while-revalidate=86400"
    error = RuntimeError("synthetic")
    error.response = {"ResponseMetadata": {"HTTPStatusCode": "503"}}
    assert server._storage_error_http_status(error) == 503
    assert server._content_range_total_size("bytes 0-3/10") == 10
    assert server._content_range_total_size("malformed") == 0
