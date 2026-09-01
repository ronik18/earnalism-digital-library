from __future__ import annotations

import asyncio
import importlib
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response


def _server(monkeypatch):
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    return importlib.import_module("backend.server")


def _request(method: str = "GET"):
    return SimpleNamespace(headers={}, method=method, cookies={})


def test_reader_manifest_audio_hides_playable_package_routes(monkeypatch):
    server = _server(monkeypatch)
    document = {
        "slug": "approved-audio",
        "audiobook_enabled": True,
        "audiobook_assets": {"mp3": "https://storage.invalid/private.mp3"},
        "audiobook": {"url": "https://storage.invalid/private.mp3"},
    }
    monkeypatch.setattr(server, "can_expose_audio", lambda _book: True)

    audio = server._reader_manifest_audio(document, "approved-audio")

    assert audio["enabled"] is True
    assert audio["assets"] == {}
    assert audio["url"] == ""


def test_package_manifest_uses_current_request_and_lease_signature(monkeypatch):
    server = _server(monkeypatch)
    authorized = []

    async def authorize(request, principal, slug):
        authorized.append((request.method, principal["id"], slug))

    async def package_manifest(slug, request):
        assert request.method == "HEAD"
        return Response(status_code=200, headers={"ETag": '"package-v1"'})

    monkeypatch.setattr(server, "_authorize_reading_pass_audio", authorize)
    monkeypatch.setattr(server, "_reader_book_audiobook_package_manifest_response", package_manifest)

    response = asyncio.run(
        server.reader_book_audiobook_package_manifest("approved-audio", _request("HEAD"), {"id": "reader"})
    )

    assert authorized == [("HEAD", "reader", "approved-audio")]
    assert response.status_code == 200
    assert response.headers["etag"] == '"package-v1"'


@pytest.mark.parametrize(
    ("endpoint", "arguments"),
    (
        ("reader_book_audiobook_package_segment", ("package-v1", "segment-001")),
        ("reader_book_audiobook_package_segment_timestamps", ("package-v1", "segment-001")),
        ("reader_book_audiobook_package_segment_vtt", ("package-v1", "segment-001")),
        ("reader_book_audiobook_package_segment_metadata", ("package-v1", "segment-001")),
    ),
)
def test_package_routes_authorize_before_segment_lookup(monkeypatch, endpoint, arguments):
    server = _server(monkeypatch)

    async def denied(_request, _principal, _slug):
        raise HTTPException(status_code=403, detail={"code": "LEASE_REQUIRED"})

    async def unexpected_segment(*_args, **_kwargs):
        raise AssertionError("protected package storage must not be reached before authorization")

    monkeypatch.setattr(server, "_authorize_reading_pass_audio", denied)
    monkeypatch.setattr(server, "_reader_book_audiobook_package_segment", unexpected_segment)

    with pytest.raises(HTTPException) as raised:
        asyncio.run(getattr(server, endpoint)("approved-audio", *arguments, _request(), None))

    assert raised.value.status_code == 403
    assert raised.value.detail["code"] == "LEASE_REQUIRED"
