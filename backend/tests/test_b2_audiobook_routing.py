import importlib
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _server(monkeypatch):
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    return importlib.import_module("server")


def test_reader_manifest_rewrites_b2_mp3_to_api_proxy(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "can_expose_audio", lambda book: True)
    monkeypatch.setattr(server, "B2_S3_ENDPOINT", "https://s3.us-west-004.backblazeb2.com")
    monkeypatch.setattr(server, "B2_REGION", "us-west-004")
    monkeypatch.setattr(server, "B2_BUCKET", "earnalism-audio")
    monkeypatch.setattr(server, "B2_ACCESS_KEY_ID", "test-key")
    monkeypatch.setattr(server, "B2_SECRET_ACCESS_KEY", "test-secret")
    book = {
        "audiobook_provider": "b2",
        "audio_asset_slug": "dracula",
        "audiobook_assets": {
            "mp3": "https://s3.us-west-004.backblazeb2.com/earnalism-audio/earnalism/audiobooks/en/dracula/dracula.mp3",
            "timestamps": "https://s3.us-west-004.backblazeb2.com/earnalism-audio/earnalism/audiobooks/en/dracula/dracula_timestamps.json",
            "vtt": "https://res.cloudinary.com/demo/raw/upload/dracula_highlight.vtt",
        },
        "audiobook": {
            "provider": "b2",
            "url": "https://s3.us-west-004.backblazeb2.com/earnalism-audio/earnalism/audiobooks/en/dracula/dracula.mp3",
            "size": 120_000_000,
            "duration_ms": 1234,
        },
    }

    audio = server._reader_manifest_audio(book, "dracula")

    assert audio["provider"] == "b2"
    assert audio["assets"]["mp3"] == "/api/reader/book/dracula/audiobook"
    assert audio["assets"]["timestamps"] == "/api/reader/book/dracula/audiobook/timestamps"
    assert audio["assets"]["vtt"].startswith("https://res.cloudinary.com/")
    assert audio["url"] == "/api/reader/book/dracula/audiobook"
    assert audio["size"] == 120_000_000
    assert audio["duration_ms"] == 1234


def test_reader_manifest_audio_slug_alone_does_not_enable_audio(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "can_expose_audio", lambda book: True)
    book = {
        "audio_asset_slug": "dracula",
        "audiobook_enabled": False,
        "generate_audiobook": False,
        "audiobook_assets": {},
        "audiobook": {},
    }

    audio = server._reader_manifest_audio(book, "dracula")

    assert audio["asset_slug"] == "dracula"
    assert audio["enabled"] is False
    assert audio["assets"] == {}
    assert audio["url"] == ""


def test_b2_key_and_range_helpers(monkeypatch):
    server = _server(monkeypatch)
    server.B2_S3_ENDPOINT = "https://s3.us-west-004.backblazeb2.com"
    server.B2_REGION = "us-west-004"
    server.B2_BUCKET = "earnalism-audio"
    server.B2_ACCESS_KEY_ID = "test-key"
    server.B2_SECRET_ACCESS_KEY = "test-secret"

    key = server._b2_key_from_url(
        "https://s3.us-west-004.backblazeb2.com/earnalism-audio/earnalism/audiobooks/en/dracula/dracula.mp3"
    )
    byte_range, status = server._parse_byte_range("bytes=100-199", 1000)

    assert key == "earnalism/audiobooks/en/dracula/dracula.mp3"
    assert byte_range == "bytes=100-199"
    assert status == 206
    assert server._content_range_header(byte_range, 1000) == "bytes 100-199/1000"
    assert server._range_content_length(byte_range, 1000) == 100


def test_private_audio_store_is_proxied_without_changing_primary_b2(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "can_expose_audio", lambda book: True)
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_S3_ENDPOINT", "https://s3.us-west-004.backblazeb2.com")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_REGION", "us-west-004")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_BUCKET", "earnalism-private-qa-audio")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_ACCESS_KEY_ID", "private-key")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_SECRET_ACCESS_KEY", "private-secret")
    private_url = (
        "https://s3.us-west-004.backblazeb2.com/earnalism-private-qa-audio/"
        "earnalism/audiobooks/the-open-window/the-open-window.mp3"
    )
    book = {
        "audiobook_enabled": True,
        "audiobook_assets": {"mp3": private_url},
        "audiobook": {
            "url": private_url,
            "provider": "kokoro",
            "ai_narration_disclosure": "Narration: AI voice",
        },
    }

    storage = server._b2_storage_for_url(private_url)
    audio = server._reader_manifest_audio(book, "the-open-window")

    assert storage is not None
    assert storage["name"] == "private_audio"
    assert storage["bucket"] == "earnalism-private-qa-audio"
    assert server._b2_key_from_url(private_url, storage) == (
        "earnalism/audiobooks/the-open-window/the-open-window.mp3"
    )
    assert audio["assets"]["mp3"] == "/api/reader/book/the-open-window/audiobook"
    assert audio["url"] == "/api/reader/book/the-open-window/audiobook"
    assert audio["narration_disclosure"] == "Narration: AI voice"


def test_private_audio_endpoint_reads_the_selected_private_bucket(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_S3_ENDPOINT", "https://s3.us-west-004.backblazeb2.com")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_REGION", "us-west-004")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_BUCKET", "earnalism-private-qa-audio")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_ACCESS_KEY_ID", "private-key")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_SECRET_ACCESS_KEY", "private-secret")
    private_url = (
        "https://s3.us-west-004.backblazeb2.com/earnalism-private-qa-audio/"
        "earnalism/audiobooks/the-open-window/the-open-window.mp3"
    )
    book = {
        "slug": "the-open-window",
        "is_published": True,
        "audiobook_enabled": True,
        "audiobook_assets": {"mp3": private_url},
        "audiobook": {"url": private_url, "provider": "kokoro"},
    }

    class FakeBooks:
        async def find_one(self, *_args, **_kwargs):
            return book

    class FakeBody:
        def __init__(self):
            self._remaining = b"test"

        def read(self, _size=-1):
            payload, self._remaining = self._remaining, b""
            return payload

        def close(self):
            return None

    class FakeS3:
        def __init__(self):
            self.calls = []

        def get_object(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "ContentLength": 4,
                "ContentRange": "bytes 0-3/6283053",
                "ContentType": "audio/mpeg",
                "Body": FakeBody(),
            }

    fake_s3 = FakeS3()
    monkeypatch.setattr(server, "db", SimpleNamespace(books=FakeBooks()))
    monkeypatch.setattr(server, "_is_controlled_public_slug", lambda slug: slug == "the-open-window")
    monkeypatch.setattr(server, "_reader_audio_truth_doc", lambda value, _slug: value)
    monkeypatch.setattr(server, "can_expose_audio", lambda _book: True)
    monkeypatch.setattr(server, "_b2_client", lambda storage=None: fake_s3)
    request = SimpleNamespace(headers={"range": "bytes=0-3"}, method="GET")

    response = asyncio.run(server._reader_book_audiobook_asset("the-open-window", "mp3", request))

    assert response.status_code == 206
    assert response.headers["content-range"] == "bytes 0-3/6283053"
    assert fake_s3.calls == [
        {
            "Bucket": "earnalism-private-qa-audio",
            "Key": "earnalism/audiobooks/the-open-window/the-open-window.mp3",
            "Range": "bytes=0-3",
        }
    ]


def test_unconfigured_backblaze_url_keeps_legacy_manifest_proxy_shape_but_has_no_store(monkeypatch):
    server = _server(monkeypatch)
    monkeypatch.setattr(server, "B2_S3_ENDPOINT", "")
    monkeypatch.setattr(server, "B2_REGION", "")
    monkeypatch.setattr(server, "B2_BUCKET", "")
    monkeypatch.setattr(server, "B2_ACCESS_KEY_ID", "")
    monkeypatch.setattr(server, "B2_SECRET_ACCESS_KEY", "")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_S3_ENDPOINT", "")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_REGION", "")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_BUCKET", "")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_ACCESS_KEY_ID", "")
    monkeypatch.setattr(server, "B2_PRIVATE_AUDIO_SECRET_ACCESS_KEY", "")

    url = "https://s3.us-west-004.backblazeb2.com/unconfigured-bucket/book.mp3"
    assert server._audio_asset_looks_like_b2(url) is True
    assert server._b2_storage_for_url(url) is None


def test_controlled_unconfigured_backblaze_asset_fails_closed_instead_of_redirecting(monkeypatch):
    server = _server(monkeypatch)
    private_url = (
        "https://s3.us-west-004.backblazeb2.com/earnalism-private-qa-audio/"
        "earnalism/audiobooks/the-open-window/the-open-window.mp3"
    )
    book = {
        "slug": "the-open-window",
        "is_published": True,
        "audiobook_enabled": True,
        "audiobook_assets": {"mp3": private_url},
    }

    class FakeBooks:
        async def find_one(self, *_args, **_kwargs):
            return book

    monkeypatch.setattr(server, "db", SimpleNamespace(books=FakeBooks()))
    monkeypatch.setattr(server, "_is_controlled_public_slug", lambda slug: slug == "the-open-window")
    monkeypatch.setattr(server, "_reader_audio_truth_doc", lambda value, _slug: value)
    monkeypatch.setattr(server, "can_expose_audio", lambda _book: True)
    monkeypatch.setattr(server, "_b2_storage_configs", lambda: [])
    request = SimpleNamespace(headers={}, method="GET")

    try:
        asyncio.run(server._reader_book_audiobook_asset("the-open-window", "mp3", request))
    except server.HTTPException as exc:
        assert exc.status_code == 503
        assert "not configured" in str(exc.detail).lower()
    else:
        raise AssertionError("Unmatched private Backblaze asset must fail closed")


def test_audio_asset_cache_policy_keeps_audio_browser_hot(monkeypatch):
    server = _server(monkeypatch)

    assert "max-age=600" in server._audio_asset_cache_control("mp3")
    assert "stale-while-revalidate=3600" in server._audio_asset_cache_control("mp3")
    assert "max-age=3600" in server._audio_asset_cache_control("timestamps")
    assert server._audio_asset_content_type("timestamps", "application/octet-stream") == "application/json"
    assert server._audio_asset_content_type("vtt", "application/octet-stream") == "text/vtt"


def test_b2_wrappers_preserve_kwargs_while_running_off_event_loop(monkeypatch):
    server = _server(monkeypatch)

    class FakeS3:
        def __init__(self):
            self.calls = []

        def head_object(self, **kwargs):
            self.calls.append(("head", kwargs))
            return {"ContentLength": 10}

        def get_object(self, **kwargs):
            self.calls.append(("get", kwargs))
            return {"ContentLength": 4, "Body": object()}

    fake = FakeS3()

    head = asyncio.run(server._b2_head_object(fake, bucket="bucket", key="book.mp3"))
    obj = asyncio.run(server._b2_get_object(fake, bucket="bucket", key="book.mp3", byte_range="bytes=0-3"))

    assert head["ContentLength"] == 10
    assert obj["ContentLength"] == 4
    assert fake.calls == [
        ("head", {"Bucket": "bucket", "Key": "book.mp3"}),
        ("get", {"Bucket": "bucket", "Key": "book.mp3", "Range": "bytes=0-3"}),
    ]
