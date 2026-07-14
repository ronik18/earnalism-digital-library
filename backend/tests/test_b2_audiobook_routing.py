import importlib
import asyncio
import sys
from pathlib import Path


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
    server.B2_BUCKET = "earnalism-audio"

    key = server._b2_key_from_url(
        "https://s3.us-west-004.backblazeb2.com/earnalism-audio/earnalism/audiobooks/en/dracula/dracula.mp3"
    )
    byte_range, status = server._parse_byte_range("bytes=100-199", 1000)

    assert key == "earnalism/audiobooks/en/dracula/dracula.mp3"
    assert byte_range == "bytes=100-199"
    assert status == 206
    assert server._content_range_header(byte_range, 1000) == "bytes 100-199/1000"
    assert server._range_content_length(byte_range, 1000) == 100


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
