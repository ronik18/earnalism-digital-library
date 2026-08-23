from __future__ import annotations

import asyncio
import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from backend import server
from backend.api.schemas import ReadingPassPreviewActivationIn
from backend.domain.reading_pass import (
    PUBLIC_AUDIO_PREVIEW_SECONDS,
    ReadingPassConfig,
    public_audio_position,
)


def request_with_range() -> Request:
    return Request({"type": "http", "method": "GET", "headers": [(b"range", b"bytes=0-1023")]})


def test_public_contract_pins_three_text_pages_and_zero_audio_seconds():
    assert ReadingPassConfig().public_text_pages == 3
    assert PUBLIC_AUDIO_PREVIEW_SECONDS == 0
    assert ReadingPassConfig().public_audio_seconds == 0
    assert not public_audio_position(0)
    assert not public_audio_position(1)


def test_release_schema_rejects_every_nonzero_public_audio_duration():
    with pytest.raises(ValueError):
        ReadingPassPreviewActivationIn(
            version="sha256-" + "a" * 64,
            duration_seconds=1,
            sha256="a" * 64,
            source_sha256="b" * 64,
            bytes=1,
            store="private",
            bucket="audio",
            key="preview.mp3",
        )


def test_retired_public_preview_generator_cannot_write_audio(tmp_path):
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parents[2] / "scripts/generate_audiobook_preview.py"), "--slug", "approved-audio", "--output-dir", str(tmp_path)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["duration_seconds"] == 0
    assert not list(tmp_path.iterdir())


def test_public_preview_routes_are_disabled_without_disclosing_media():
    for endpoint in (
        server.reading_pass_audiobook_preview_manifest,
        server.reading_pass_audiobook_preview_audio,
    ):
        with pytest.raises(HTTPException) as raised:
            if endpoint is server.reading_pass_audiobook_preview_manifest:
                asyncio.run(endpoint("approved-audio", object()))
            else:
                asyncio.run(endpoint("approved-audio", request_with_range()))
        assert raised.value.status_code == 404
        assert raised.value.detail["code"] == "AUDIO_PREVIEW_DISABLED"

    assert "AUDIO_PREVIEW_DISABLED" in inspect.getsource(server.admin_register_reading_pass_preview)
    assert not server._reading_pass_preview_record_valid(
        {
            "duration_seconds": 1,
            "bytes": 1,
            "sha256": "a" * 64,
            "source_sha256": "b" * 64,
            "version": "sha256-" + "a" * 64,
            "storage": {"key": "preview.mp3"},
        }
    )


def test_every_playable_audio_route_authorizes_before_streaming():
    for endpoint in (
        server.reader_book_audiobook,
        server.reader_book_audiobook_package_manifest,
        server.reader_book_audiobook_package_segment,
        server.reader_book_audiobook_package_segment_timestamps,
        server.reader_book_audiobook_package_segment_vtt,
        server.reader_book_audiobook_package_segment_metadata,
        server.reader_book_audiobook_sidecar,
    ):
        source = inspect.getsource(endpoint)
        assert "await _authorize_reading_pass_audio(request, principal, slug)" in source
        assert "if READING_PASS_V2_ENABLED" not in source


def test_public_catalog_and_manifest_cannot_publish_playable_audio_urls():
    assert '"url": ""' in inspect.getsource(server._reader_manifest_audio)
    assert '"assets": {}' in inspect.getsource(server._reader_manifest_audio)


@pytest.mark.parametrize("status, code", [(401, "AUTH_REQUIRED"), (403, "PASS_REQUIRED"), (403, "LEASE_REQUIRED")])
def test_range_audio_requests_cannot_bypass_the_authorization_boundary(monkeypatch, status, code):
    async def approved_book(_slug):
        return {"slug": "approved-audio"}

    async def denied_authorization(_request, _principal, _slug):
        raise HTTPException(status_code=status, detail={"code": code})

    async def unexpected_asset(*_args, **_kwargs):
        raise AssertionError("audio bytes must not be loaded before authorization")

    monkeypatch.setattr(server, "_reader_audio_book_for_slug", approved_book)
    monkeypatch.setattr(server, "_authorize_reading_pass_audio", denied_authorization)
    monkeypatch.setattr(server, "_reader_book_audiobook_asset", unexpected_asset)

    with pytest.raises(HTTPException) as raised:
        asyncio.run(server.reader_book_audiobook("approved-audio", request_with_range(), None))
    assert raised.value.status_code == status
    assert raised.value.detail["code"] == code


def test_only_an_approved_audiobook_with_a_valid_lease_reaches_audio_bytes(monkeypatch):
    authorized = []

    async def approved_book(_slug):
        return {"slug": "approved-audio"}

    async def valid_authorization(_request, principal, slug):
        authorized.append((principal["id"], slug))

    async def audio_asset(_slug, _asset_key, _request):
        return Response(content=b"protected-audio", media_type="audio/mpeg")

    monkeypatch.setattr(server, "_reader_audio_book_for_slug", approved_book)
    monkeypatch.setattr(server, "_authorize_reading_pass_audio", valid_authorization)
    monkeypatch.setattr(server, "_reader_book_audiobook_asset", audio_asset)

    response = asyncio.run(server.reader_book_audiobook("approved-audio", request_with_range(), {"id": "active-pass-user"}))
    assert response.status_code == 200
    assert authorized == [("active-pass-user", "approved-audio")]

    async def unavailable_book(_slug):
        raise HTTPException(status_code=404, detail={"code": "CONTENT_NOT_AUTHORIZED"})

    monkeypatch.setattr(server, "_reader_audio_book_for_slug", unavailable_book)
    with pytest.raises(HTTPException) as raised:
        asyncio.run(server.reader_book_audiobook("unapproved-audio", request_with_range(), {"id": "active-pass-user"}))
    assert raised.value.status_code == 404
