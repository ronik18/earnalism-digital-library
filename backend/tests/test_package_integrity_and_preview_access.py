from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "package-integrity-preview-test-secret")

from backend import catalog_truth, server
from backend.domain.reading_pass import canonical_page_records


ROOT = Path(__file__).resolve().parents[2]
GINNI = "book-d19e96859f"
DRACULA = "dracula"
CURRENT_COMMERCIAL_TITLES = ("a-white-heron", "the-selfish-giant")
CANONICAL_PAGE_ALIASES = (
    "/api/reading-pass/books/{slug}/pages/{page_index}",
    "/api/reader/book/{slug}/pages/{page_index}",
)


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

    requested_versions: list[str] = []

    class Segments:
        async def find_one(self, query, _projection):
            requested_versions.append(query["segmentation_version"])
            return by_page.get(query["page_index"])

    async def access_doc(*_args, **_kwargs):
        return artifact

    async def manifest(*_args, **_kwargs):
        return {
            "segmentation_version": "isolated-dracula-active-v2",
            "version": "isolated-dracula-manifest-v2",
            "total_pages": len(pages),
        }

    async def stored_manifest(_slug, segmentation_version, **_kwargs):
        if segmentation_version == "isolated-dracula-retained-v1":
            return {
                "segmentation_version": "isolated-dracula-retained-v1",
                "version": "isolated-dracula-manifest-v1",
                "total_pages": len(pages),
            }
        assert segmentation_version == "isolated-dracula-active-v2"
        return await manifest()

    authorized: list[dict] = []

    async def authorize(**kwargs):
        authorized.append(kwargs)
        return {"scope": {
            "segmentation_version": "isolated-dracula-retained-v1",
            "manifest_version": "isolated-dracula-manifest-v1",
        }}

    monkeypatch.setattr(server, "READING_PASS_V2_ENABLED", True)
    monkeypatch.setattr(server, "_reader_book_access_doc", access_doc)
    monkeypatch.setattr(server, "_active_reader_segment_manifest", manifest)
    monkeypatch.setattr(server, "_stored_reader_segment_manifest", stored_manifest)
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
    assert protected["segmentation_version"] == "isolated-dracula-retained-v1"
    assert protected["manifest_version"] == "isolated-dracula-manifest-v1"
    assert requested_versions[-1] == "isolated-dracula-retained-v1"
    assert authorized == [{
        "user_id": "entitled",
        "auth_session_id": "auth-session",
        "session_id": "isolated-session",
        "lease_token": "isolated-lease",
        "content_type": "text",
        "content_id": DRACULA,
    }]

    async def legacy_authorize(**_kwargs):
        return {"scope": {"canonical_page_index": 4}}

    monkeypatch.setattr(server.reading_pass_service, "authorize", legacy_authorize)
    with pytest.raises(server.HTTPException) as legacy_session:
        asyncio.run(
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
    assert legacy_session.value.status_code == 409
    assert legacy_session.value.detail["code"] == "LEGACY_SESSION_PUBLICATION_VERSION_UNVERIFIED"


def test_ginni_checksum_conflict_quarantines_artifact_and_blocks_database_fallback(monkeypatch, tmp_path):
    roots = (
        ROOT / "data" / "controlled_publications",
        ROOT / "backend" / "data" / "controlled_publications",
    )
    for root, expected_quarantine in zip(roots, (False, True)):
        artifact_dir = root / GINNI
        manifest = json.loads((artifact_dir / "checksum_manifest.json").read_text())
        expected = next(row["sha256"] for row in manifest["files"] if row["file"] == "approval_evidence.json")
        actual = hashlib.sha256((artifact_dir / "approval_evidence.json").read_bytes()).hexdigest()
        assert (actual != expected) is expected_quarantine
        assert catalog_truth.controlled_artifact_integrity_quarantined(GINNI, str(artifact_dir)) is expected_quarantine

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

    # Ginni is currently held outside the allowlist, independently of mirror integrity.
    assert server._is_controlled_public_slug(GINNI) is False
    assert asyncio.run(server._find_public_book_candidate(GINNI, {}, include_artifact_content=False)) == (None, "missing")
    # Exercise the separate integrity gate with an isolated eligible fixture.
    monkeypatch.setattr(server, "_is_controlled_public_slug", lambda slug: slug == GINNI)
    # Exercise a genuine isolated mismatch, without assuming live records remain broken.
    monkeypatch.setattr(server, "_controlled_artifact_is_integrity_quarantined",
        lambda slug: catalog_truth.controlled_artifact_integrity_quarantined(slug, str(valid_dir)))
    monkeypatch.setattr(server, "db", SimpleNamespace(books=Database()))
    result = asyncio.run(server._find_public_book_candidate(GINNI, {}, include_artifact_content=False))
    assert result == (None, "integrity_quarantined")


def test_quarantined_ginni_cannot_use_stale_canonical_segments_through_either_page_alias(monkeypatch):
    class StaleManifests:
        def __init__(self):
            self.calls = []

        async def find_one(self, query, _projection):
            self.calls.append(query)
            return {
                "book_slug": GINNI,
                "status": "active",
                "segmentation_version": "stale-ginni-segments",
                "total_pages": 4,
            }

    class StaleSegments:
        def __init__(self):
            self.calls = []

        async def find_one(self, query, _projection):
            self.calls.append(query)
            return {
                "book_slug": GINNI,
                "page_index": query["page_index"],
                "segmentation_version": "stale-ginni-segments",
                "chapter_id": "chapter-001",
                "content": "stale quarantined content",
            }

    manifests = StaleManifests()
    segments = StaleSegments()
    monkeypatch.setattr(server, "READING_PASS_V2_ENABLED", True)
    monkeypatch.setattr(
        server,
        "db",
        SimpleNamespace(reader_segment_manifests=manifests, reader_content_segments=segments),
    )
    assert asyncio.run(server._reader_book_access_doc(GINNI)) is None

    async def entitled_principal():
        return {"id": "isolated-entitled", "role": "user", "status": "active", "session_id": "isolated-auth"}

    client = TestClient(server.app)
    try:
        for alias in CANONICAL_PAGE_ALIASES:
            anonymous = client.get(alias.format(slug=GINNI, page_index=1))
            assert anonymous.status_code == 404
            assert anonymous.json()["detail"]["code"] == "CONTENT_NOT_AUTHORIZED"

            server.app.dependency_overrides[server.optional_principal] = entitled_principal
            protected = client.get(
                alias.format(slug=GINNI, page_index=4),
                headers={
                    "X-Reading-Pass-Session": "stale-session",
                    "X-Reading-Pass-Lease": "stale-lease",
                },
            )
            assert protected.status_code == 404
            assert protected.json()["detail"]["code"] == "CONTENT_NOT_AUTHORIZED"
    finally:
        server.app.dependency_overrides.pop(server.optional_principal, None)
        client.close()

    assert manifests.calls == []
    assert segments.calls == []


def test_eligible_canonical_pages_retain_public_then_authorized_boundary(monkeypatch):
    artifact = dracula_artifact()
    pages = canonical_page_records(book_slug=DRACULA, chapters=artifact["chapters"])
    by_page = {page["page_index"]: page for page in pages}

    class Segments:
        async def find_one(self, query, _projection):
            return by_page.get(query["page_index"])

    async def access_doc(*_args, **_kwargs):
        return artifact

    async def manifest(*_args, **_kwargs):
        return {
            "segmentation_version": "eligible-dracula-boundary",
            "version": "eligible-dracula-manifest-v1",
            "total_pages": len(pages),
        }

    monkeypatch.setattr(server, "READING_PASS_V2_ENABLED", True)
    monkeypatch.setattr(server, "_reader_book_access_doc", access_doc)
    monkeypatch.setattr(server, "_active_reader_segment_manifest", manifest)
    monkeypatch.setattr(server, "_stored_reader_segment_manifest", manifest)
    monkeypatch.setattr(server, "db", SimpleNamespace(reader_content_segments=Segments()))

    client = TestClient(server.app)
    try:
        for alias in CANONICAL_PAGE_ALIASES:
            public = client.get(alias.format(slug=DRACULA, page_index=1))
            assert public.status_code == 200
            assert public.json()["is_preview"] is True
            assert public.json()["content"] == by_page[1]["content"]

            protected = client.get(alias.format(slug=DRACULA, page_index=4))
            assert protected.status_code == 401
            assert protected.json()["detail"]["code"] == "AUTH_REQUIRED"
    finally:
        client.close()


def test_canonical_page_routes_remain_disabled_when_v2_is_disabled(monkeypatch):
    monkeypatch.setattr(server, "READING_PASS_V2_ENABLED", False)
    client = TestClient(server.app)
    try:
        for alias in CANONICAL_PAGE_ALIASES:
            response = client.get(alias.format(slug=DRACULA, page_index=1))
            assert response.status_code == 404
            assert response.json()["detail"]["code"] == "FEATURE_DISABLED"
    finally:
        client.close()


def test_current_commercial_titles_follow_release_authority():
    registry = json.loads((ROOT / "backend/data/rights_decision_registry.json").read_text())
    # Resolve the named current title policy rather than a historical omission list.
    def entry(node, key):
        if isinstance(node, dict):
            if key in node: return node[key]
            for value in node.values():
                found = entry(value, key)
                if found is not None: return found
        return None
    rows = {row["slug"] for row in server._append_controlled_artifact_projections([])}
    for slug in CURRENT_COMMERCIAL_TITLES:
        policy = entry(registry, "controlled-" + slug)
        assert policy["access_mode"] == "COMMERCIAL_ENTITLEMENT"
        assert policy["status"] == "PREVIEW_RELEASED_ENTITLEMENT_REQUIRED_FROM_PAGE_4"
        assert policy["countries"] == ["IN"]
        assert slug in catalog_truth.CONTROLLED_LIVE_BOOK_SLUGS
        book = catalog_truth.load_controlled_artifact_book(slug, include_content=False)
        assert catalog_truth.can_expose_reader(book) is True
        assert server._safe_live_public_projection(book) is not None
        assert slug in rows
    # Retain the negative check for genuinely unlisted editions.
    assert catalog_truth.can_expose_reader({"slug": "dummy-unreleased-edition"}) is False
