import importlib
import sys
import asyncio
from pathlib import Path
from types import SimpleNamespace


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _server(monkeypatch):
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    return importlib.import_module("server")


def test_redis_cache_allows_cover_and_audio_urls_as_metadata(monkeypatch):
    server = _server(monkeypatch)

    payload = {
        "title": "A cached metadata document",
        "cover_image_url": "https://res.cloudinary.com/demo/image/upload/f_auto,q_auto/v1/covers/book.jpg",
        "thumbnail_url": "https://res.cloudinary.com/demo/image/upload/c_fill,w_300/v1/covers/book.jpg",
        "audio": {
            "assets": {
                "mp3": "https://cdn.theearnalism.com/audio/book.mp3",
                "manifest": "https://cdn.theearnalism.com/audio/book.json",
            }
        },
    }

    assert server._redis_cache_payload_is_media(payload) is False
    assert server._cache_payload_encode_for_redis("test-policy", payload) is not None


def test_redis_cache_rejects_media_binaries_and_data_uris(monkeypatch):
    server = _server(monkeypatch)

    assert server._redis_cache_payload_is_media({"cover": b"\x89PNG\r\n"}) is True
    assert server._redis_cache_payload_is_media({"audio": bytearray(b"ID3")}) is True
    assert server._redis_cache_payload_is_media({"cover_image": "data:image/png;base64,AAAA"}) is True
    assert server._redis_cache_payload_is_media({"audio": {"mp3": "data:audio/mpeg;base64,AAAA"}}) is True
    assert server._cache_payload_encode_for_redis("test-policy", {"audio": b"ID3"}) is None


def test_client_etag_matching_supports_weak_validators(monkeypatch):
    server = _server(monkeypatch)

    class Request:
        headers = {"if-none-match": 'W/"reader-manifest-a", "other"'}

    assert server._client_etag_matches(Request(), 'W/"reader-manifest-a"') is True
    assert server._client_etag_matches(Request(), 'W/"reader-manifest-b"') is False


def test_reader_cache_identity_rejects_missing_and_cross_title_payloads(monkeypatch):
    server = _server(monkeypatch)

    assert server._cached_title_payload_matches({"slug": "dracula"}, "dracula")
    assert not server._cached_title_payload_matches({}, "dracula")
    assert not server._cached_title_payload_matches({"slug": "frankenstein"}, "dracula")
    assert server._cached_title_payload_matches(
        {"book": {"slug": "dracula", "release_version": "release-a"}},
        "dracula",
        book_field="book",
        require_release_version=True,
    )
    assert not server._cached_title_payload_matches(
        {"book": {"slug": "dracula"}},
        "dracula",
        book_field="book",
        require_release_version=True,
    )


def test_reader_chapter_body_never_uses_shared_redis(monkeypatch):
    server = _server(monkeypatch)

    async def reader_access(_slug, **_kwargs):
        return {"slug": "dracula"}

    def artifact(_slug, **_kwargs):
        return {"chapters": [{"id": "chapter-001", "content": "Safe reader text."}]}

    async def redis_called(*_args, **_kwargs):
        raise AssertionError("chapter body must not use shared Redis")

    monkeypatch.setattr(server, "_reader_book_access_doc", reader_access)
    monkeypatch.setattr(server, "_controlled_artifact_doc", artifact)
    monkeypatch.setattr(server, "_redis_cache_get", redis_called)
    monkeypatch.setattr(server, "_redis_cache_set", redis_called)

    assert asyncio.run(server._reader_chapter_content("dracula", "chapter-001")) == "<p>Safe reader text.</p>"


def test_authoritative_wallet_lookup_does_not_read_redis(monkeypatch):
    server = _server(monkeypatch)

    class ReadingPassService:
        async def wallet_state(self, user_id):
            assert user_id == "reader-1"
            return {"balance_seconds": 120}

    monkeypatch.setattr(server, "reading_pass_service", ReadingPassService())

    assert asyncio.run(server._authoritative_user_wallet_seconds("reader-1")) == 120


def _legacy_reader_chapter_book(slug):
    return {
        "slug": slug,
        "chapters": [{
            "id": "chapter-004",
            "title": "Protected chapter",
            "order": 4,
            "is_preview": False,
            "content_version": "protected-v1",
        }],
    }


def test_legacy_reader_preview_never_uses_public_or_shared_cache(monkeypatch):
    server = _server(monkeypatch)
    slug = "dracula"
    monkeypatch.setattr(server, "READING_PASS_V2_ENABLED", False)

    async def reader_access(_slug, **_kwargs):
        return {
            "slug": slug,
            "chapters": [{
                "id": "chapter-001",
                "title": "Preview chapter",
                "order": 1,
                "is_preview": True,
                "content_version": "preview-v1",
            }],
        }

    async def chapter_content(*_args, **_kwargs):
        return "<p>Public preview only.</p>"

    async def cache_called(*_args, **_kwargs):
        raise AssertionError("legacy chapter response must not enter a shared cache")

    monkeypatch.setattr(server, "_reader_book_access_doc", reader_access)
    monkeypatch.setattr(server, "_reader_chapter_content", chapter_content)
    monkeypatch.setattr(server, "_public_cache_get", cache_called)
    monkeypatch.setattr(server, "_public_cache_set", cache_called)
    request = server.Request({"type": "http", "method": "GET", "headers": []})
    response = server.Response()

    result = asyncio.run(server.reader_get_chapter(slug, "chapter-001", request, response, principal=None))

    assert result["locked"] is False
    assert result["chapter"]["content"] == "<p>Public preview only.</p>"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["pragma"] == "no-cache"


def test_legacy_reader_uses_authoritative_balance_and_no_store(monkeypatch):
    server = _server(monkeypatch)
    slug = "dracula"
    monkeypatch.setattr(server, "READING_PASS_V2_ENABLED", False)

    async def reader_access(_slug, **_kwargs):
        return _legacy_reader_chapter_book(slug)

    async def stale_wallet_cache(_user_id):
        raise AssertionError("reader authorization must not read wallet cache")

    async def authoritative_wallet(_user_id):
        return 120

    async def chapter_content(*_args, **_kwargs):
        return "<p>Protected reader text.</p>"

    monkeypatch.setattr(server, "_reader_book_access_doc", reader_access)
    monkeypatch.setattr(server, "_cached_user_wallet_seconds", stale_wallet_cache)
    monkeypatch.setattr(server, "_authoritative_user_wallet_seconds", authoritative_wallet)
    monkeypatch.setattr(server, "_reader_chapter_content", chapter_content)
    request = server.Request({"type": "http", "method": "GET", "headers": []})
    response = server.Response()

    result = asyncio.run(
        server.reader_get_chapter(
            slug,
            "chapter-004",
            request,
            response,
            principal={"id": "reader-1", "role": "user"},
        )
    )

    assert result["locked"] is False
    assert result["chapter"]["content"] == "<p>Protected reader text.</p>"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["vary"] == "Authorization, Cookie"
