import importlib
import asyncio
import sys
from pathlib import Path

from types import SimpleNamespace

from fastapi import Response
import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _server(monkeypatch):
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    return importlib.import_module("server")


def _approved_slug_doc():
    return {
        "slug": "dracula",
        "title": "Dracula",
        "audiobook_provider": "b2",
        "audiobook_voice": "ratan",
        "audiobook_enabled": True,
        "audiobook_assets_updated_at": "2026-07-10T00:00:00Z",
        "audio_asset_slug": "dracula",
        "audiobook": {
            "provider": "b2",
            "voice": "ratan",
            "size": 1234,
            "duration_ms": 5678,
            "updated_at": "2026-07-10T00:00:00Z",
            "assets": {
                "mp3": "https://s3.us-west-004.backblazeb2.com/earnalism-audio/a/dracula.mp3",
                "timestamps": "https://s3.us-west-004.backblazeb2.com/earnalism-audio/a/dracula_timestamps.json",
            },
        },
        "audiobook_assets": {
            "mp3": "https://s3.us-west-004.backblazeb2.com/earnalism-audio/a/dracula.mp3",
            "timestamps": "https://s3.us-west-004.backblazeb2.com/earnalism-audio/a/dracula_timestamps.json",
            "segment-001": "https://s3.us-west-004.backblazeb2.com/earnalism-audio/a/dracula_segment_001.mp3",
            "segment-001-timestamps": "https://s3.us-west-004.backblazeb2.com/earnalism-audio/a/dracula_segment_001_timestamps.json",
            "segment-002": "https://s3.us-west-004.backblazeb2.com/earnalism-audio/a/dracula_segment_002.mp3",
            "segment-002-timestamps": "https://s3.us-west-004.backblazeb2.com/earnalism-audio/a/dracula_segment_002_timestamps.json",
        },
    }


def test_package_descriptor_is_deterministic(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "can_expose_audio", lambda book: True)
    book = _approved_slug_doc()

    first = server._reader_book_audiobook_package_descriptor(book, "dracula")
    second = server._reader_book_audiobook_package_descriptor(book, "dracula")

    assert first is not None
    assert second is not None
    assert first["package_version"] == second["package_version"]
    assert first["segment_ids"] == ("segment-001", "segment-002")


def test_reader_book_audiobook_package_manifest(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "can_expose_audio", lambda book: True)
    doc = _approved_slug_doc()

    class FakeBooks:
        async def find_one(self, *_args, **_kwargs):
            return doc

    monkeypatch.setattr(server, "db", SimpleNamespace(books=FakeBooks()))

    manifest = asyncio.run(server.reader_book_audiobook_package_manifest("dracula", Response()))
    assert manifest["slug"] == "dracula"
    assert manifest["packageVersion"] == server._reader_book_audiobook_package_descriptor(doc, "dracula")["package_version"]
    assert manifest["segments"][0]["segmentId"] == "segment-001"


def test_reader_book_audiobook_package_manifest_uses_controlled_artifact_fallback(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "can_expose_audio", lambda book: True)
    doc = _approved_slug_doc()
    doc["slug"] = "book-2b9853ec52"

    async def _fallback_book(slug):
        assert slug == "book-2b9853ec52"
        return doc, "artifact"

    monkeypatch.setattr(server, "_find_audio_book_candidate", _fallback_book)
    monkeypatch.setattr(server, "db", None)

    manifest = asyncio.run(server.reader_book_audiobook_package_manifest("book-2b9853ec52", Response()))
    assert manifest["slug"] == "book-2b9853ec52"
    assert manifest["packageVersion"] == server._reader_book_audiobook_package_descriptor(doc, "book-2b9853ec52")["package_version"]


def test_reader_manifest_audio_includes_package_manifest_endpoint(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "can_expose_audio", lambda book: True)
    doc = _approved_slug_doc()

    manifest_audio = server._reader_manifest_audio(doc, "dracula")
    assert manifest_audio["enabled"] is True
    assert manifest_audio["package_manifest"] == "/api/reader/book/dracula/audiobook/manifest"
    assert manifest_audio["assets"]["mp3"] == "/api/reader/book/dracula/audiobook"


def test_package_descriptor_falls_back_to_base_assets_without_segments(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "can_expose_audio", lambda book: True)
    doc = _approved_slug_doc()
    doc["audiobook_assets"] = {
        "mp3": "https://s3.us-west-004.backblazeb2.com/earnalism-audio/a/book-2b9853ec52.mp3",
        "timestamps": "https://s3.us-west-004.backblazeb2.com/earnalism-audio/a/book-2b9853ec52_timestamps.json",
    }
    doc["audiobook"]["assets"] = {
        "mp3": "https://s3.us-west-004.backblazeb2.com/earnalism-audio/a/book-2b9853ec52.mp3",
        "timestamps": "https://s3.us-west-004.backblazeb2.com/earnalism-audio/a/book-2b9853ec52_timestamps.json",
    }

    descriptor = server._reader_book_audiobook_package_descriptor(doc, "book-2b9853ec52")
    assert descriptor is not None
    assert descriptor["segment_ids"] == ("segment-001",)
    segment_media = server._segment_descriptor(
        descriptor.get("segment_assets", {}),
        "segment-001",
        fallback_audio=descriptor["assets"].get("mp3", ""),
        fallback_timestamp=descriptor["assets"].get("timestamps", ""),
    )
    assert segment_media["audio"] == doc["audiobook_assets"]["mp3"]
    assert segment_media["timestamps"] == doc["audiobook_assets"]["timestamps"]


def test_reader_book_audiobook_package_segment_rejects_unknown_version(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "can_expose_audio", lambda book: True)
    doc = _approved_slug_doc()

    class FakeBooks:
        async def find_one(self, *_args, **_kwargs):
            return doc

    monkeypatch.setattr(server, "db", SimpleNamespace(books=FakeBooks()))

    async def _should_not_run(*_args, **_kwargs):
        raise AssertionError("_reader_book_audiobook_asset should not be called for unknown packageVersion")

    monkeypatch.setattr(server, "_reader_book_audiobook_asset", _should_not_run)

    request = SimpleNamespace(headers={}, method="GET")
    with pytest.raises(server.HTTPException) as exc:
        asyncio.run(server.reader_book_audiobook_package_segment("dracula", "wrong-version", "segment-001", request))

    assert exc.value.status_code == 404


def test_reader_book_audiobook_package_segment_descriptor_is_used(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "can_expose_audio", lambda book: True)
    doc = _approved_slug_doc()
    descriptor = server._reader_book_audiobook_package_descriptor(doc, "dracula")
    assert descriptor is not None
    assert descriptor["segment_ids"] == ("segment-001", "segment-002")
    segment_media = server._segment_descriptor(
        descriptor.get("segment_assets", {}),
        "segment-002",
        fallback_timestamp=descriptor["assets"].get("timestamps", ""),
    )
    assert segment_media["audio"] == doc["audiobook_assets"]["segment-002"]
    assert segment_media["timestamps"] == doc["audiobook_assets"]["segment-002-timestamps"]


def test_reader_book_audiobook_package_segment_timestamps_falls_back_to_segment_specific(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "can_expose_audio", lambda book: True)
    doc = _approved_slug_doc()
    descriptor = server._reader_book_audiobook_package_descriptor(doc, "dracula")
    assert descriptor is not None
    segment_media = server._segment_descriptor(
        descriptor.get("segment_assets", {}),
        "segment-002",
        fallback_timestamp=descriptor["assets"].get("timestamps", ""),
    )
    assert segment_media["timestamps"] == doc["audiobook_assets"]["segment-002-timestamps"]

def test_reader_book_audiobook_package_timestamps_rejects_unknown_segment(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "can_expose_audio", lambda book: True)
    doc = _approved_slug_doc()

    class FakeBooks:
        async def find_one(self, *_args, **_kwargs):
            return doc

    monkeypatch.setattr(server, "db", SimpleNamespace(books=FakeBooks()))

    descriptor = server._reader_book_audiobook_package_descriptor(doc, "dracula")
    assert descriptor is not None
    package_version = descriptor["package_version"]
    request = SimpleNamespace(headers={}, method="GET")
    with pytest.raises(server.HTTPException) as exc:
        asyncio.run(
            server.reader_book_audiobook_package_segment_timestamps(
                "dracula",
                package_version,
                "segment-999",
                request,
            )
        )
    assert exc.value.status_code == 404


def test_reader_book_audiobook_asset_returns_416_for_unsatisfiable_range(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "can_expose_audio", lambda book: True)
    doc = _approved_slug_doc()
    doc["slug"] = "dracula"

    class FakeBooks:
        async def find_one(self, *_args, **_kwargs):
            return doc

    class FakeS3:
        def __init__(self):
            self.calls = []

        def head_object(self, **kwargs):
            self.calls.append(("head", kwargs))
            return {"ContentLength": 100, "ETag": "etag", "ContentType": "audio/mpeg"}

        def get_object(self, **kwargs):
            self.calls.append(("get", kwargs))
            raise AssertionError("should not call ranged get for invalid range")

    fake_s3 = FakeS3()
    monkeypatch.setattr(server, "db", SimpleNamespace(books=FakeBooks()))
    monkeypatch.setattr(server, "_b2_client", lambda: fake_s3)
    monkeypatch.setattr(server, "_is_controlled_public_slug", lambda _: True)

    req = SimpleNamespace(headers={"range": "bytes=200-300"}, method="GET")
    resp = asyncio.run(server._reader_book_audiobook_asset("dracula", "mp3", req))
    assert resp.status_code == 416
    assert resp.headers.get("Content-Range") == "bytes */100"


def test_reader_book_audiobook_asset_returns_416_for_invalid_range_header(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "can_expose_audio", lambda book: True)
    doc = _approved_slug_doc()
    doc["slug"] = "dracula"

    class FakeBooks:
        async def find_one(self, *_args, **_kwargs):
            return doc

    class FakeS3:
        def head_object(self, **kwargs):
            return {"ContentLength": 100}

        def get_object(self, **kwargs):
            raise AssertionError("should not call ranged get for invalid range")

    fake_s3 = FakeS3()
    monkeypatch.setattr(server, "db", SimpleNamespace(books=FakeBooks()))
    monkeypatch.setattr(server, "_b2_client", lambda: fake_s3)
    monkeypatch.setattr(server, "_is_controlled_public_slug", lambda _: True)

    req = SimpleNamespace(headers={"range": "bytes=-"}, method="GET")
    resp = asyncio.run(server._reader_book_audiobook_asset("dracula", "mp3", req))
    assert resp.status_code == 416
