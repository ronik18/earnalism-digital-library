import importlib
import sys
from pathlib import Path


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
