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
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
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


def test_reader_chapter_bodies_never_use_shared_redis(monkeypatch):
    server = _server(monkeypatch)
    slug = "the-open-window"

    async def reader_access(_slug, **_kwargs):
        return {"slug": slug}

    def artifact(_slug, **_kwargs):
        return {"chapters": [{"id": "chapter-001", "content": "Safe reader text."}]}

    async def redis_called(*_args, **_kwargs):
        raise AssertionError("chapter body must not be read from or written to shared Redis")

    monkeypatch.setattr(server, "_reader_book_access_doc", reader_access)
    monkeypatch.setattr(server, "_controlled_artifact_doc", artifact)
    monkeypatch.setattr(server, "_redis_cache_get", redis_called)
    monkeypatch.setattr(server, "_redis_cache_set", redis_called)

    assert asyncio.run(server._reader_chapter_content(slug, "chapter-001")) == "<p>Safe reader text.</p>"


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
        "chapters": [
            {
                "id": "chapter-004",
                "title": "Protected chapter",
                "order": 4,
                "is_preview": False,
                "content_version": "protected-v1",
            }
        ],
    }


def test_legacy_reader_chapter_denies_stale_positive_wallet_cache(monkeypatch):
    server = _server(monkeypatch)
    slug = "the-open-window"
    monkeypatch.setattr(server, "READING_PASS_V2_ENABLED", False)

    async def reader_access(_slug, **_kwargs):
        return _legacy_reader_chapter_book(slug)

    async def stale_wallet_cache(_user_id):
        raise AssertionError("legacy chapter authorization must not read the wallet cache")

    async def authoritative_wallet(_user_id):
        return 0

    async def chapter_content(*_args, **_kwargs):
        raise AssertionError("protected content must stay locked without authoritative balance")

    monkeypatch.setattr(server, "_reader_book_access_doc", reader_access)
    monkeypatch.setattr(server, "_cached_user_wallet_seconds", stale_wallet_cache)
    monkeypatch.setattr(server, "_authoritative_user_wallet_seconds", authoritative_wallet)
    monkeypatch.setattr(server, "_reader_chapter_content", chapter_content)

    request = server.Request({"type": "http", "method": "GET", "headers": []})
    result = asyncio.run(
        server.reader_get_chapter(
            slug,
            "chapter-004",
            request,
            server.Response(),
            principal={"id": "reader-1", "role": "user"},
        )
    )

    assert result["locked"] is True
    assert result["reason"] == "INSUFFICIENT_READING_TIME"
    assert "content" not in result["chapter"]


def test_legacy_reader_chapter_uses_authoritative_balance_and_no_store(monkeypatch):
    server = _server(monkeypatch)
    slug = "the-open-window"
    monkeypatch.setattr(server, "READING_PASS_V2_ENABLED", False)

    async def reader_access(_slug, **_kwargs):
        return _legacy_reader_chapter_book(slug)

    async def stale_wallet_cache(_user_id):
        raise AssertionError("legacy chapter authorization must not read the wallet cache")

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
