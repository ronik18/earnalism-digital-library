"""Characterization tests: document current behavior without changing it."""

from __future__ import annotations

import importlib
import io
import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_cache_media_test")
os.environ.setdefault("JWT_SECRET", "cache-media-characterization-only")
server = importlib.import_module("backend.server")


@pytest.mark.parametrize(
    ("header", "size", "expected_range", "status"),
    [
        ("", 2048, None, 200),
        ("bytes=0-1023", 2048, "bytes=0-1023", 206),
        ("bytes=-1024", 2048, "bytes=1024-2047", 206),
        ("bytes=2048-", 2048, None, 416),
        ("bytes=", 2048, None, 416),
    ],
)
def test_current_range_parser_contract(header, size, expected_range, status):
    assert server._parse_byte_range(header, size) == (expected_range, status)


def test_current_stream_iterator_reads_in_bounded_chunks_and_closes_body():
    class Body(io.BytesIO):
        closed_by_iterator = False

        def close(self):
            self.closed_by_iterator = True
            super().close()

    body = Body(b"x" * (1024 * 1024 + 7))
    chunks = list(server._streaming_body_iterator(body))
    assert [len(chunk) for chunk in chunks] == [1024 * 1024, 7]
    assert body.closed_by_iterator is True


def test_current_redis_codec_is_pickle_with_optional_zlib_and_no_size_guard():
    encoded = server._cache_payload_encode({"value": "x"})
    assert encoded.startswith((b"p:", b"z:"))
    assert server._cache_payload_decode(encoded) == {"value": "x"}
    assert "MAX" not in server._cache_payload_encode_for_redis.__code__.co_names


def test_current_redis_media_rejection_keeps_urls_but_rejects_binary():
    assert server._redis_cache_payload_is_media({"audio_url": "https://example.test/audio.mp3"}) is False
    assert server._redis_cache_payload_is_media({"audio": b"ID3"}) is True


def test_current_audio_cache_control_is_private_and_audio_is_not_publicly_cacheable():
    assert server._audio_asset_cache_control("mp3") == "private, max-age=600, stale-while-revalidate=3600"
    assert server._audio_asset_cache_control("timestamps") == "private, max-age=3600, stale-while-revalidate=86400"
