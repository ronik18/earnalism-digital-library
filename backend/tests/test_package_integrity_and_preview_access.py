from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "package-integrity-preview-test-secret")

from backend import catalog_truth, server
from backend.domain.reading_pass import canonical_page_records


ROOT = Path(__file__).resolve().parents[2]
GINNI = "book-d19e96859f"
DRACULA = "dracula"
OMITTED_FROM_LEGACY_CONFIG = ("a-white-heron", "the-selfish-giant")


def request(headers: list[tuple[bytes, bytes]] | None = None) -> server.Request:
    return server.Request({"type": "http", "method": "GET", "headers": headers or []})


def dracula_artifact() -> dict:
    artifact = catalog_truth.load_dracula_artifact_book(include_content=True)
    assert artifact is not None
    return artifact


def test_dracula_legacy_chapter_route_fails_closed_when_v2_is_disabled(monkeypatch):
    artifact = dracula_artifact()
    later_chapter = next(chapter for chapter in artifact["chapters"] if chapter["id"] == "chapter-027")

    async def access_doc(*_args, **_kwargs):
        return artifact

    async def chapter_content(*_args, **_kwargs):
        return later_chapter["content"]

    monkeypatch.setattr(server, "READING_PASS_V2_ENABLED", False)
    monkeypatch.setattr(server, "_reader_book_access_doc", access_doc)
    monkeypatch.setattr(server, "_reader_chapter_content", chapter_content)

    result = asyncio.run(
        server.reader_get_chapter(
            DRACULA,
            "chapter-027",
            request(),
            server.Response(),
            principal=None,
        )
    )

    assert result["locked"] is True
    assert result["reason"] == "AUTH_REQUIRED"
    assert "content" not in result["chapter"]
    projected = server._safe_live_public_projection(artifact)
    assert projected is not None
    assert projected["preview_enabled"] is False
    assert projected["preview_url"] == ""


def test_dracula_v2_uses_canonical_pages_and_keeps_page_four_protected(monkeypatch):
    artifact = dracula_artifact()
    pages = canonical_page_records(book_slug=DRACULA, chapters=artifact["chapters"])
    assert len(pages) > 4
    by_page = {page["page_index"]: page for page in pages}

    class Segments:
        async def find_one(self, query, _projection):
            return by_page.get(query["page_index"])

    async def access_doc(*_args, **_kwargs):
        return artifact

    async def manifest(*_args, **_kwargs):
        return {
            "segmentation_version": "isolated-dracula-preview-boundary",
            "total_pages": len(pages),
        }

    authorized: list[dict] = []

    async def authorize(**kwargs):
        authorized.append(kwargs)

    monkeypatch.setattr(server, "READING_PASS_V2_ENABLED", True)
    monkeypatch.setattr(server, "_reader_book_access_doc", access_doc)
    monkeypatch.setattr(server, "_active_reader_segment_manifest", manifest)
    monkeypatch.setattr(server, "db", SimpleNamespace(reader_content_segments=Segments()))
    monkeypatch.setattr(server.reading_pass_service, "authorize", authorize)

    with pytest.raises(server.HTTPException) as legacy:
        asyncio.run(
            server.reader_get_chapter(
                DRACULA,
                "chapter-027",
                request(),
                server.Response(),
                principal=None,
            )
        )
    assert legacy.value.status_code == 409
    assert legacy.value.detail["code"] == "CANONICAL_PAGE_REQUIRED"

    public = asyncio.run(
        server.reading_pass_book_page(DRACULA, 1, request(), server.Response(), principal=None)
    )
    assert public["is_preview"] is True
    assert public["content"] == by_page[1]["content"]

    with pytest.raises(server.HTTPException) as anonymous:
        asyncio.run(
            server.reading_pass_book_page(DRACULA, 4, request(), server.Response(), principal=None)
        )
    assert anonymous.value.status_code == 401
    assert anonymous.value.detail["code"] == "AUTH_REQUIRED"

    with pytest.raises(server.HTTPException) as denied:
        asyncio.run(
            server.reading_pass_book_page(
                DRACULA,
                4,
                request(),
                server.Response(),
                principal={"id": "blocked", "role": "user", "status": "blocked"},
            )
        )
    assert denied.value.status_code == 403
    assert denied.value.detail["code"] == "CONTENT_NOT_AUTHORIZED"

    protected = asyncio.run(
        server.reading_pass_book_page(
            DRACULA,
            4,
            request([
                (b"x-reading-pass-session", b"isolated-session"),
                (b"x-reading-pass-lease", b"isolated-lease"),
            ]),
            server.Response(),
            principal={"id": "entitled", "role": "user", "status": "active", "session_id": "auth-session"},
        )
    )
    assert protected["is_preview"] is False
    assert protected["content"] == by_page[4]["content"]
    assert authorized == [{
        "user_id": "entitled",
        "auth_session_id": "auth-session",
        "session_id": "isolated-session",
        "lease_token": "isolated-lease",
        "content_type": "text",
        "content_id": DRACULA,
    }]


def test_ginni_checksum_conflict_quarantines_artifact_and_blocks_database_fallback(monkeypatch, tmp_path):
    roots = (
        ROOT / "data" / "controlled_publications",
        ROOT / "backend" / "data" / "controlled_publications",
    )
    for root in roots:
        artifact_dir = root / GINNI
        assert catalog_truth.controlled_artifact_integrity_quarantined(GINNI, str(artifact_dir)) is True
        assert "approval_evidence.json does not match its retained checksum-bound approval." in (
            catalog_truth.controlled_artifact_validation_issues(GINNI, str(artifact_dir))
        )

    valid_dir = tmp_path / GINNI
    valid_dir.mkdir()
    approval = valid_dir / "approval_evidence.json"
    approval.write_text('{"approved_to_publish":true}\n', encoding="utf-8")
    digest = hashlib.sha256(approval.read_bytes()).hexdigest()
    (valid_dir / "checksum_manifest.json").write_text(
        json.dumps({"files": [{"file": "approval_evidence.json", "sha256": digest}]}),
        encoding="utf-8",
    )
    assert catalog_truth.controlled_artifact_integrity_quarantined(GINNI, str(valid_dir)) is False
    approval.write_text('{"approved_to_publish":false}\n', encoding="utf-8")
    assert catalog_truth.controlled_artifact_integrity_quarantined(GINNI, str(valid_dir)) is True

    class Database:
        async def find_one(self, *_args, **_kwargs):
            pytest.fail("an integrity-quarantined artifact must not fall back to stale database metadata")

    monkeypatch.setattr(server, "db", SimpleNamespace(books=Database()))
    result = asyncio.run(server._find_public_book_candidate(GINNI, {}, include_artifact_content=False))
    assert result == (None, "integrity_quarantined")


def test_manifest_approved_titles_are_not_excluded_by_the_legacy_43_slug_list():
    assert set(OMITTED_FROM_LEGACY_CONFIG).isdisjoint(catalog_truth.LEGACY_CONTROLLED_LIVE_BOOK_SLUGS)
    for slug in OMITTED_FROM_LEGACY_CONFIG:
        assert slug in catalog_truth.CONTROLLED_LIVE_BOOK_SLUGS
        assert catalog_truth.controlled_artifact_status(slug)["self_contained_for_truth_gate"] is True
        projected = server._safe_live_public_projection(
            catalog_truth.load_controlled_artifact_book(slug, include_content=False)
        )
        assert projected is not None
        assert projected["reader_enabled"] is True
    api_rows = server._append_controlled_artifact_projections([])
    assert set(OMITTED_FROM_LEGACY_CONFIG).issubset({row["slug"] for row in api_rows})
