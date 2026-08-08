from __future__ import annotations

import asyncio
import json
import os

from starlette.requests import Request

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "home-surface-api-test-secret")

from backend import server
from backend.home_surface_contracts import build_home_hero_contract


def _request(path: str, *, etag: str = "") -> Request:
    headers = [(b"if-none-match", etag.encode("utf-8"))] if etag else []
    return Request({
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": headers,
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 1234),
        "scheme": "http",
    })


def _source_payload() -> dict:
    hero_book = {
        "slug": "hero",
        "title": "Hero",
        "author": "Author",
        "language": "en",
        "front_cover_url": "https://cdn.example.com/hero.webp",
        "cover_alt_text": "Hero by Author",
        "cover_valid": True,
        "reader_enabled": True,
        "book_url": "/book/hero",
        "reader_url": "/reader/hero",
    }
    audio_book = {
        **hero_book,
        "slug": "audio",
        "title": "Audio",
        "book_url": "/book/audio",
        "reader_url": "/reader/audio",
        "primary_cta_url": "/reader/audio?listen=1",
        "audiobook_enabled": True,
        "audiobook_release_gate": "APPROVED",
        "audio_qa_status": "QA_PASSED",
        "audiobook_url": "/api/reader/book/audio/audiobook",
    }
    return {
        "hero": {"carousel_books": [hero_book]},
        "listening_rooms": {"items": [audio_book]},
        "source": {"truth_source": "canonical", "catalog_version": "test-v1"},
    }


async def _no_cache(*_args, **_kwargs):
    return None


async def _no_cache_set(*_args, **_kwargs):
    return None


def test_split_routes_return_distinct_contracts_and_cache_policies(monkeypatch):
    async def source(*, include_audio_manifests=True):
        return _source_payload()

    monkeypatch.setattr(server, "_public_cache_get", _no_cache)
    monkeypatch.setattr(server, "_public_cache_set", _no_cache_set)
    monkeypatch.setattr(server, "_build_home_curated_source_payload", source)

    hero_response = asyncio.run(server.get_home_hero(_request("/api/home/hero")))
    listening_response = asyncio.run(server.get_home_listening(_request("/api/home/listening"), limit=3))
    hero = json.loads(hero_response.body)
    listening = json.loads(listening_response.body)

    assert hero["schema_version"] == "home-hero-v1"
    assert listening["schema_version"] == "home-listening-v1"
    assert "listening_rooms" not in hero
    assert "hero" not in listening
    assert hero_response.headers["cache-control"].startswith("public, max-age=300")
    assert listening_response.headers["cache-control"].startswith("public, max-age=60")
    assert "s-maxage=3600" in hero_response.headers["cdn-cache-control"]
    assert "s-maxage=300" in listening_response.headers["cdn-cache-control"]


def test_hero_route_honors_etag_without_rebuilding(monkeypatch):
    payload = build_home_hero_contract(_source_payload())

    async def cached(*_args, **_kwargs):
        return payload

    monkeypatch.setattr(server, "_public_cache_get", cached)
    etag = f'"{payload["revision"]}"'
    response = asyncio.run(server.get_home_hero(_request("/api/home/hero", etag=etag)))

    assert response.status_code == 304
    assert response.headers["etag"] == etag
    assert response.body == b""


def test_audio_manifest_resolution_is_parallel_and_fails_closed(monkeypatch):
    state = {"active": 0, "peak": 0}

    async def manifest(slug):
        state["active"] += 1
        state["peak"] = max(state["peak"], state["active"])
        await asyncio.sleep(0.01)
        state["active"] -= 1
        if slug == "broken":
            raise RuntimeError("manifest unavailable")
        return {
            "audio": {
                "enabled": True,
                "url": f"/api/reader/book/{slug}/audiobook",
                "release_gate": "APPROVED",
                "qa_status": "QA_PASSED",
                "duration_ms": 1000,
            },
        }

    monkeypatch.setattr(server, "_public_cache_get", _no_cache)
    monkeypatch.setattr(server, "_public_cache_set", _no_cache_set)
    monkeypatch.setattr(server, "can_expose_audio", lambda _doc: True)
    monkeypatch.setattr(server, "_reader_book_manifest_doc", manifest)

    contracts = asyncio.run(server._home_audio_contracts([
        {"slug": "one"},
        {"slug": "two"},
        {"slug": "broken"},
    ]))

    assert state["peak"] == 3
    assert contracts["one"]["enabled"] is True
    assert contracts["two"]["endpoint_valid"] is True
    assert contracts["broken"]["enabled"] is False
    assert contracts["broken"]["package_valid"] is False
