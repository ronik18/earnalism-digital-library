from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "sredni-vashtar-routability-test-secret")

from backend import catalog_truth, server


class EmptyBooks:
    async def find_one(self, *_args, **_kwargs):
        return None


def test_sredni_controlled_artifact_has_release_gated_reuse_audio():
    status = catalog_truth.controlled_artifact_status("sredni-vashtar")
    artifact = catalog_truth.load_controlled_artifact_book("sredni-vashtar", include_content=True)

    assert status["available"] is True
    assert status["audio_enabled"] is True
    assert status["audiobook_enabled"] is True
    assert artifact is not None
    assert artifact["audiobook_provider"] == "openai"
    assert artifact["audiobook_voice"] == "verse"
    assert artifact["audiobook"]["sync_mode"] == "section_following"
    assert artifact["audiobook"]["highlight_sync_enabled"] is False
    assert artifact["audiobook"]["audio_sha256"] == (
        "2b328a80b90684ddf2fe3df1a1447481067c6cb277484f97432e882c7844d31a"
    )
    assert catalog_truth.can_expose_audio(artifact) is True


def test_sredni_reader_manifest_uses_proxy_and_section_following_copy(monkeypatch):
    monkeypatch.setattr(server, "db", SimpleNamespace(books=EmptyBooks()))

    manifest = asyncio.run(server._reader_book_manifest_doc("sredni-vashtar"))

    assert manifest is not None
    assert manifest["audio"]["enabled"] is True
    assert manifest["audio"]["provider"] == "openai"
    assert manifest["audio"]["voice"] == "verse"
    assert manifest["audio"]["release_gate"] == "APPROVED"
    assert manifest["audio"]["qa_status"] == "QA_PASSED"
    assert manifest["audio"]["url"] == "/api/reader/book/sredni-vashtar/audiobook"
    assert manifest["audio"]["assets"]["mp3"] == "/api/reader/book/sredni-vashtar/audiobook"
    assert manifest["audio"]["assets"]["timestamps"] == (
        "/api/reader/book/sredni-vashtar/audiobook/timestamps"
    )
    assert manifest["audio"]["assets"]["vtt"] == "/api/reader/book/sredni-vashtar/audiobook/vtt"
    assert manifest["audio"]["assets"]["chapters"] == (
        "/api/reader/book/sredni-vashtar/audiobook/chapters"
    )
    assert manifest["audio"]["assets"]["meta"] == "/api/reader/book/sredni-vashtar/audiobook/meta"
    assert manifest["audio"]["sync_mode"] == "section_following"
