from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "publishing-edition-test-secret")

from backend import catalog_truth, server
from scripts import orchestrate_book_factory


ROOT = Path.cwd()
RAW_CHAPTER_DIR = ROOT / "data" / "controlled_publications" / "dracula" / "chapters"
PUBLISHING_DIR = ROOT / "data" / "controlled_publications" / "dracula" / "publishing_edition"
PUBLISHING_CHAPTER_DIR = PUBLISHING_DIR / "chapters"


class FakeBooks:
    def __init__(self, doc: dict):
        self.doc = doc

    async def find_one(self, query, projection=None):
        chapter_id = query.get("chapters.id")
        if chapter_id:
            raw_chapter = json.loads((RAW_CHAPTER_DIR / f"{chapter_id}.json").read_text(encoding="utf-8"))
            return {"chapters": [raw_chapter]}
        return self.doc


async def noop_cache_get(*_args, **_kwargs):
    return None


async def noop_cache_set(*_args, **_kwargs):
    return None


def plain_text(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html or "")


def publishing_chapter(chapter_id: str = "chapter-001") -> dict:
    return json.loads((PUBLISHING_CHAPTER_DIR / f"{chapter_id}.json").read_text(encoding="utf-8"))


def raw_chapter(chapter_id: str = "chapter-001") -> dict:
    return json.loads((RAW_CHAPTER_DIR / f"{chapter_id}.json").read_text(encoding="utf-8"))


def test_publishing_edition_artifacts_exist_for_all_dracula_chapters():
    manifest = json.loads((PUBLISHING_DIR / "publishing_edition_manifest.json").read_text(encoding="utf-8"))
    chapters = sorted(PUBLISHING_CHAPTER_DIR.glob("chapter-*.json"))

    assert manifest["go_live_status"] == "GO_LIVE_READER_READY"
    assert manifest["chapter_count"] == 27
    assert len(chapters) == 27
    assert manifest["publishing_edition_hash"]


def test_dracula_publishing_edition_removes_known_raw_source_artifacts():
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(PUBLISHING_CHAPTER_DIR.glob("chapter-*.json"))]
    combined_html = "\n".join(str(payload.get("content") or "") for payload in payloads)
    combined_titles = "\n".join(str(payload.get("title") or "") for payload in payloads)
    combined_text = plain_text(combined_html)

    forbidden = [
        "*****",
        "_--",
        ".--The",
        "ishigh",
        "aremixed",
        "awake,naturally",
        "whichproduces",
        "notdisagreeable",
        "himtalking",
        "everynow",
        "nationali-",
        "-- continued",
        "— continued",
    ]
    assert all(item not in combined_html for item in forbidden)
    assert all(item not in combined_text for item in forbidden)
    assert "-- continued" not in combined_titles
    assert "— continued" not in combined_titles
    assert not re.search(r"(^|[>(\s])_[A-Za-z0-9]", combined_text)
    assert "reader-scene-break" in combined_html


def test_raw_source_chapter_is_preserved_unchanged_for_provenance():
    raw_content = raw_chapter()["content"]

    assert "* * * * *" in raw_content
    assert "_3 May" in raw_content
    assert "_Kept in shorthand" in raw_content
    assert "<br>" in raw_content


def test_public_reader_content_prefers_publishing_edition_over_raw_db(monkeypatch):
    book_doc = catalog_truth.load_dracula_artifact_book(include_content=False)
    monkeypatch.setattr(server, "db", SimpleNamespace(books=FakeBooks(book_doc)))
    monkeypatch.setattr(server, "_redis_cache_get", noop_cache_get)
    monkeypatch.setattr(server, "_redis_cache_set", noop_cache_set)

    content = asyncio.run(server._reader_chapter_content("dracula", "chapter-001"))

    assert "reader-scene-break" in content
    assert "* * * * *" not in content
    assert "_3 May" not in content
    assert "The grey of the morning has passed, and the sun is high" in plain_text(content)


def test_public_reader_manifest_uses_publishing_edition_metadata(monkeypatch):
    book_doc = catalog_truth.load_dracula_artifact_book(include_content=False)
    monkeypatch.setattr(server, "db", SimpleNamespace(books=FakeBooks(book_doc)))
    monkeypatch.setattr(server, "_redis_cache_get", noop_cache_get)
    monkeypatch.setattr(server, "_redis_cache_set", noop_cache_set)

    manifest = asyncio.run(server._reader_book_manifest_doc("dracula"))

    assert manifest is not None
    assert manifest["chapters"][0]["title"] == "Chapter I. Jonathan Harker’s Journal"
    assert manifest["chapters"][0]["processing_status"] == "publishing_edition_ready"
    assert manifest["audio"]["enabled"] is False
    assert "Listen Now" not in json.dumps(manifest)


def test_book_factory_requires_publishing_edition_before_audiobook_stages():
    stages = list(orchestrate_book_factory.BOOK_FACTORY_AUDIOBOOK_STAGES)

    assert stages[0] == "PUBLISHING_EDITION_PREPARATION"
    assert stages.index("PUBLISHING_EDITION_PREPARATION") < stages.index("AUDIOBOOK_CHUNK_HASHING")
