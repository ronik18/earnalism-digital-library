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

    class Users:
        async def find_one(self, query, projection):
            assert query == {"id": "reader-1"}
            assert projection["reading_seconds_balance"] == 1
            return {"reading_seconds_balance": 120, "wallet_seconds": 0}

    monkeypatch.setattr(server, "db", SimpleNamespace(users=Users()))

    assert asyncio.run(server._authoritative_user_wallet_seconds("reader-1")) == 120
