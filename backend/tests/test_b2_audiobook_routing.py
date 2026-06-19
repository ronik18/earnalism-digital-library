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


def test_reader_manifest_rewrites_b2_mp3_to_api_proxy(monkeypatch):
    server = _server(monkeypatch)
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
