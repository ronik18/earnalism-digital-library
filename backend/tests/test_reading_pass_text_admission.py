"""Protected-text admission must begin with current Reader authority."""

from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

import pytest
from starlette.responses import Response

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "reading-pass-text-admission-test-secret")

from backend import server
from backend.api.schemas import ReadingPassSessionStartIn


USER = {"id": "fixture-user", "role": "user", "status": "active", "session_id": "fixture-auth"}


def _payload(content_id: str, page_index: int = 4) -> ReadingPassSessionStartIn:
    return ReadingPassSessionStartIn(
        device_id="fixture-device-0001",
        device_label="Fixture device",
        content_type="text",
        content_id=content_id,
        canonical_page_index=page_index,
    )


def test_unavailable_protected_title_is_rejected_before_retained_content_or_session(monkeypatch):
    async def unavailable(_content_id):
        return None

    async def forbidden(*_args, **_kwargs):
        pytest.fail("protected admission must not consult retained records after Reader authority denies the title")

    monkeypatch.setattr(server, "READING_PASS_V2_ENABLED", True)
    monkeypatch.setattr(server, "_reader_book_access_doc", unavailable)
    monkeypatch.setattr(server, "_active_reader_segment_manifest", forbidden)
    monkeypatch.setattr(server.reading_pass_service, "start_session", forbidden)

    response = Response()
    with pytest.raises(server.HTTPException) as denied:
        asyncio.run(server._reading_pass_start(_payload("held-title"), USER, response, transfer=False))

    assert denied.value.status_code == 404
    assert denied.value.detail["code"] == "CONTENT_NOT_AUTHORIZED"
    assert not any(name.lower() == b"set-cookie" for name, _value in response.raw_headers)


def test_authority_lookup_failure_is_unavailable_and_never_falls_back(monkeypatch):
    async def unavailable(_content_id):
        raise RuntimeError("isolated authority dependency failure")

    async def forbidden(*_args, **_kwargs):
        pytest.fail("authority failure must not fall back to manifests or session admission")

    monkeypatch.setattr(server, "READING_PASS_V2_ENABLED", True)
    monkeypatch.setattr(server, "_reader_book_access_doc", unavailable)
    monkeypatch.setattr(server, "_active_reader_segment_manifest", forbidden)
    monkeypatch.setattr(server.reading_pass_service, "start_session", forbidden)

    with pytest.raises(server.HTTPException) as denied:
        asyncio.run(server._reading_pass_start(_payload("authority-fixture"), USER, Response(), transfer=True))

    assert denied.value.status_code == 503
    assert denied.value.detail["code"] == "CONTENT_AUTHORITY_UNAVAILABLE"
    assert "isolated authority dependency failure" not in str(denied.value.detail)


def test_authorized_text_binds_alias_request_to_authority_canonical_slug(monkeypatch):
    observed: dict[str, object] = {}

    async def authority(content_id):
        observed["authority_request"] = content_id
        return {"slug": "fixture-canonical"}

    async def active_manifest(slug):
        observed["active_manifest_slug"] = slug
        return {"segmentation_version": "fixture-version", "version": "fixture-manifest"}

    async def stored_manifest(slug, version):
        observed["stored_manifest"] = (slug, version)
        return {"segmentation_version": version, "version": "fixture-manifest"}

    class Segments:
        async def find_one(self, query, _projection):
            observed["segment_query"] = query
            return {"_id": "fixture-page"}

    class ActivationState:
        async def find_one(self, query, _projection):
            observed["activation_query"] = query
            return {
                "book_slug": "fixture-canonical",
                "active_segmentation_version": "fixture-version",
                "generation": 7,
            }

    async def start_session(**kwargs):
        observed["session"] = kwargs
        return {"status": "Running", "content_type": "text", "content_id": kwargs["content_id"]}

    monkeypatch.setattr(server, "READING_PASS_V2_ENABLED", True)
    monkeypatch.setattr(server, "_reader_book_access_doc", authority)
    monkeypatch.setattr(server, "_active_reader_segment_manifest", active_manifest)
    monkeypatch.setattr(server, "_stored_reader_segment_manifest", stored_manifest)
    monkeypatch.setattr(
        server,
        "db",
        SimpleNamespace(
            reader_content_segments=Segments(),
            reader_segment_activation_state=ActivationState(),
        ),
    )
    monkeypatch.setattr(server.reading_pass_service, "start_session", start_session)

    result = asyncio.run(server._reading_pass_start(_payload("Fixture Alias"), USER, Response(), transfer=False))

    assert result["content_id"] == "fixture-canonical"
    assert observed["authority_request"] == "Fixture Alias"
    assert observed["active_manifest_slug"] == "fixture-canonical"
    assert observed["stored_manifest"] == ("fixture-canonical", "fixture-version")
    assert observed["segment_query"]["book_slug"] == "fixture-canonical"
    assert observed["session"]["content_id"] == "fixture-canonical"
    assert observed["session"]["scope"] == {
        "canonical_page_index": 4,
        "segmentation_version": "fixture-version",
        "manifest_version": "fixture-manifest",
        "authority_activation_generation": 7,
    }


def test_public_preview_remains_outside_protected_authority_admission(monkeypatch):
    async def forbidden(_content_id):
        pytest.fail("public preview must not require protected Reader admission")

    async def wallet(_user_id):
        return 123

    monkeypatch.setattr(server, "READING_PASS_V2_ENABLED", True)
    monkeypatch.setattr(server, "_reader_book_access_doc", forbidden)
    monkeypatch.setattr(server, "_cached_user_wallet_seconds", wallet)

    result = asyncio.run(server._reading_pass_start(_payload("held-title", page_index=3), USER, Response(), transfer=False))

    assert result == {"status": "Preview", "balance_seconds": 123, "preview": True}


def test_start_and_transfer_routes_share_the_same_handler(monkeypatch):
    calls: list[bool] = []

    async def shared_handler(payload, user, response, *, transfer):
        calls.append(transfer)
        return {"transfer": transfer, "content_id": payload.content_id, "user_id": user["id"]}

    monkeypatch.setattr(server, "_reading_pass_start", shared_handler)

    started = asyncio.run(server.reading_pass_session_start(_payload("fixture"), Response(), USER))
    transferred = asyncio.run(server.reading_pass_session_transfer(_payload("fixture"), Response(), USER))

    assert started["transfer"] is False
    assert transferred["transfer"] is True
    assert calls == [False, True]
