from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image
from fastapi.testclient import TestClient

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "admin-cover-upload-test-secret")

from backend import catalog_truth, server
from backend.config.book_cover import (
    build_private_cover_candidate,
    canonical_cover_kind,
    content_addressed_cover_candidate_asset_id,
    validate_book_cover,
)


ROOT = Path(__file__).resolve().parents[2]
SERVER_SOURCE = (ROOT / "backend/server.py").read_text(encoding="utf-8")


def image_bytes(image_format: str = "PNG", size: tuple[int, int] = (1200, 1800)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, "#6B1020").save(buffer, format=image_format)
    return buffer.getvalue()


def upload_result() -> dict:
    return {
        "cover_url": (
            "https://res.cloudinary.com/demo/image/upload/v1785384000/"
            "earnalism/covers/front/cover.png"
        ),
        "thumbnail_url": "https://res.cloudinary.com/demo/image/upload/w_300/cover.png",
        "blur_placeholder": "https://res.cloudinary.com/demo/image/upload/e_blur/cover.png",
        "dominant_color": "#6B1020",
        "cloudinary_public_id": "earnalism/covers/front/cover",
        "cloudinary_version": 1785384000,
        "cloudinary_version_id": "cloudinary-version-id",
        "cloudinary_resource_type": "image",
        "cloudinary_format": "png",
        "cloudinary_bytes": len(image_bytes()),
    }


def test_book_cover_validator_accepts_portrait_png_and_binds_sha256():
    body = image_bytes()
    result = validate_book_cover(body, "image/png", 4 * 1024 * 1024)

    assert result["format"] == "PNG"
    assert result["width"] == 1200
    assert result["height"] == 1800
    assert len(result["sha256"]) == 64
    assert result["bytes"] == len(body)


def test_book_cover_validator_rejects_spoofed_small_and_landscape_files():
    with pytest.raises(ValueError, match="does not match"):
        validate_book_cover(image_bytes(), "image/webp", 4 * 1024 * 1024)
    with pytest.raises(ValueError, match="at least"):
        validate_book_cover(image_bytes(size=(200, 300)), "image/png", 4 * 1024 * 1024)
    with pytest.raises(ValueError, match="portrait"):
        validate_book_cover(image_bytes(size=(1200, 800)), "image/png", 4 * 1024 * 1024)


def test_private_cover_candidate_is_side_specific_and_cannot_double_as_public_book_data():
    validation = validate_book_cover(image_bytes(), "image/png", 4 * 1024 * 1024)
    candidate = build_private_cover_candidate(
        "a-ghost-story",
        "back",
        upload_result(),
        validation,
        updated_at="2026-07-28T00:00:00+00:00",
        updated_by="owner@example.com",
    )

    assert candidate["slug"] == "a-ghost-story"
    assert candidate["kind"] == "back"
    assert candidate["candidate_url"] == upload_result()["cover_url"]
    assert candidate["audit_status"] == "ADMIN_UPLOADED_PENDING_CANONICAL_REVIEW"
    assert candidate["cloudinary_public_id"] == "earnalism/covers/front/cover"
    assert candidate["cloudinary_version"] == "1785384000"
    assert candidate["immutable_candidate_url"] == upload_result()["cover_url"]
    assert candidate["width"] == 1200
    assert candidate["height"] == 1800
    forbidden = {
        "cover_url",
        "cover_image_url",
        "thumbnail_url",
        "back_cover_url",
        "back_cover_image_url",
        "back_cover_thumbnail_url",
        "reader_enabled",
        "is_published",
        "audiobook_enabled",
        "audio_enabled",
        "audiobook_release_gate",
        "audio_qa_status",
        "audio_url",
    }
    assert forbidden.isdisjoint(candidate)
    assert {
        "candidate_url",
        "candidate_thumbnail_url",
        "candidate_blur_placeholder",
        "candidate_dominant_color",
        "candidate_srcset",
    }.isdisjoint(catalog_truth.SAFE_PUBLIC_BOOK_FIELDS)


def test_cover_kind_is_fail_closed():
    assert canonical_cover_kind("front") == "front"
    assert canonical_cover_kind(" BACK ") == "back"
    with pytest.raises(ValueError, match="front or back"):
        canonical_cover_kind("spine")


def test_admin_cover_routes_are_authenticated_bounded_and_not_generation_gated():
    cover_route = SERVER_SOURCE.split('@api.post("/admin/books/{slug}/cover")', 1)[1].split(
        '@api.post("/admin/books/{slug}/chapters/{chapter_id}/upload")',
        1,
    )[0]
    status_route = SERVER_SOURCE.split('@api.get("/admin/books/cover-status")', 1)[1].split(
        '@api.get("/admin/books/{slug}")',
        1,
    )[0]

    assert "Depends(require_admin)" in cover_route
    assert "confirm_expensive_job" in cover_route
    assert "ENABLE_ADMIN_COVER_UPLOADS" in cover_route
    assert "ENABLE_COVER_GENERATION" not in cover_route
    assert "validate_book_cover" in cover_route
    assert "book_cover_candidates.update_one" in cover_route
    assert "db.books.update_one" not in cover_route
    assert "admin_upload_audit.insert_one" in cover_route
    assert "Depends(require_admin)" in status_route
    assert "load_controlled_artifact_book" in status_route
    assert "book_cover_candidates.find" in status_route


class FakeCursor:
    def __init__(self, docs):
        self.docs = [copy.deepcopy(doc) for doc in docs]

    def sort(self, *_args, **_kwargs):
        return self

    def skip(self, value):
        self.docs = self.docs[int(value or 0) :]
        return self

    def limit(self, value):
        self.docs = self.docs[: int(value or len(self.docs))]
        return self

    async def to_list(self, *_args, **_kwargs):
        return [copy.deepcopy(doc) for doc in self.docs]


def matches_query(doc, query):
    slug_filter = query.get("slug") if isinstance(query, dict) else None
    if isinstance(slug_filter, dict) and "$in" in slug_filter:
        if doc.get("slug") not in slug_filter["$in"]:
            return False
    elif slug_filter and doc.get("slug") != slug_filter:
        return False
    if query.get("is_published") is True and doc.get("is_published") is not True:
        return False
    return True


class ImmutableBooks:
    def __init__(self, docs):
        self.docs = [copy.deepcopy(doc) for doc in docs]

    def find(self, query, _projection):
        return FakeCursor([doc for doc in self.docs if matches_query(doc, query)])

    async def find_one(self, query, _projection=None):
        return next(
            (copy.deepcopy(doc) for doc in self.docs if matches_query(doc, query)),
            None,
        )

    async def count_documents(self, query):
        return sum(matches_query(doc, query) for doc in self.docs)

    async def update_one(self, *_args, **_kwargs):
        raise AssertionError("A pending cover upload must not mutate the public book document.")


class PrivateCoverCandidates:
    def __init__(self):
        self.docs = {}

    async def update_one(self, query, update, *, upsert=False):
        assert upsert is True
        candidate_id = query["_id"]
        self.docs[candidate_id] = {
            "_id": candidate_id,
            **copy.deepcopy(update["$set"]),
        }
        return SimpleNamespace(matched_count=0, modified_count=0, upserted_id=candidate_id)

    def find(self, query, _projection):
        return FakeCursor(
            [doc for doc in self.docs.values() if matches_query(doc, query)]
        )


class AuditCollection:
    def __init__(self):
        self.docs = []

    async def insert_one(self, document):
        self.docs.append(copy.deepcopy(document))
        return SimpleNamespace(inserted_id=document.get("id"))


class EmptyCollection:
    def find(self, *_args, **_kwargs):
        return FakeCursor([])

    async def find_one(self, *_args, **_kwargs):
        return None


class FakeUpload:
    filename = "replacement-front.png"
    content_type = "image/png"

    def __init__(self, body):
        self.body = body

    async def read(self):
        return self.body


async def no_cache(*_args, **_kwargs):
    return None


def test_pending_candidate_is_private_across_all_public_book_surfaces(monkeypatch):
    slug = "a-ghost-story"
    canonical = catalog_truth.load_controlled_artifact_book(slug, include_content=True)
    assert canonical is not None
    canonical["rights_metadata"] = {
        "work_title": canonical["title"],
        "work_slug": slug,
        "author_name": canonical["author"],
        "author_death_year": 1910,
        "original_publication_year": 1875,
        "country_of_origin": "United States",
        "source_url": canonical["source_url"],
        "source_name": canonical["source_name"],
        "source_license": canonical["source_license"],
        "translator_name": "",
        "translator_death_year": "",
        "illustrator_name": "",
        "illustrator_death_year": "",
        "editor_name": "",
        "edition_publication_year": 1875,
        "rights_tier": "A",
        "verification_status": "approved",
        "blocked_reason": "",
        "publication_region": "global",
        "verified_at": "2026-07-28T00:00:00+00:00",
    }
    original = copy.deepcopy(canonical)
    private_candidates = PrivateCoverCandidates()
    audits = AuditCollection()
    fake_db = SimpleNamespace(
        books=ImmutableBooks([canonical]),
        book_cover_candidates=private_candidates,
        admin_upload_audit=audits,
        categories=EmptyCollection(),
        settings=EmptyCollection(),
    )
    private_url = "https://res.cloudinary.com/demo/image/upload/private-review-candidate.png"
    private_result = {
        **upload_result(),
        "cover_url": private_url,
        "srcset": f"{private_url} 1x",
    }

    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setattr(server, "_ensure_cloudinary", lambda: None)
    monkeypatch.setattr(
        server,
        "_process_book_cover_candidate",
        lambda _body, asset_id, *, kind: (
            private_result
            if asset_id
            == content_addressed_cover_candidate_asset_id(
                slug,
                hashlib.sha256(image_bytes()).hexdigest(),
            )
            and kind == "front"
            else pytest.fail("Cover candidate did not use the isolated asset namespace.")
        ),
    )
    monkeypatch.setattr(server, "_public_cache_get", no_cache)
    monkeypatch.setattr(server, "_public_cache_set", no_cache)
    monkeypatch.setattr(server, "_redis_cache_get", no_cache)
    monkeypatch.setattr(server, "_redis_cache_set", no_cache)

    response = asyncio.run(
        server.admin_upload_cover(
            slug=slug,
            kind="front",
            confirm_expensive_job=True,
            file=FakeUpload(image_bytes()),
            admin={"sub": "owner-1", "email": "owner@example.com"},
        )
    )

    assert response["success"] is True
    assert response["cover_url"] == private_url
    candidate = private_candidates.docs[f"{slug}:front"]
    assert candidate["candidate_url"] == private_url
    assert candidate["audit_status"] == "ADMIN_UPLOADED_PENDING_CANONICAL_REVIEW"
    assert audits.docs[0]["status"] == "uploaded_pending_canonical_review"
    assert fake_db.books.docs[0] == original

    cover_status = asyncio.run(
        server.admin_list_book_cover_status(
            _={"sub": "owner-1", "email": "owner@example.com"}
        )
    )
    status_row = next(book for book in cover_status["books"] if book["slug"] == slug)
    assert status_row["front_status"] == "UPLOADED_PENDING_CANONICAL_REVIEW"
    assert status_row["admin_front_cover_url"] == private_url
    assert status_row["canonical_front_cover_url"] != private_url

    public_payloads = {
        "/api/books": asyncio.run(server.list_books()),
        f"/api/books/{slug}": asyncio.run(server.get_book(slug)),
        "/api/home": asyncio.run(server.get_home_payload()),
        "/api/home/curated": asyncio.run(server.get_home_curated()),
        f"/api/reader/book/{slug}/manifest": asyncio.run(
            server._reader_book_manifest_doc(slug)
        ),
    }

    for route, payload in public_payloads.items():
        assert private_url not in json.dumps(payload, ensure_ascii=False), route

    detail = public_payloads[f"/api/books/{slug}"]
    manifest = public_payloads[f"/api/reader/book/{slug}/manifest"]
    assert detail["cover_image_url"] == original["cover_image_url"]
    assert detail["audio_enabled"] is True
    assert detail["audiobook_release_gate"] == "APPROVED"
    assert manifest["book"]["cover_image_url"] == original["cover_image_url"]
    assert manifest["audio"]["enabled"] is True
    assert manifest["audio"]["release_gate"] == "APPROVED"
    assert manifest["audio"]["qa_status"] == "QA_PASSED"


def test_controlled_only_jekyll_can_upload_without_seeding_public_mongo(monkeypatch):
    slug = "jekyll-and-hyde"
    canonical = catalog_truth.load_controlled_artifact_book(slug, include_content=False)
    assert canonical is not None
    assert catalog_truth.can_expose_reader(canonical) is True

    books = ImmutableBooks([])
    private_candidates = PrivateCoverCandidates()
    audits = AuditCollection()
    fake_db = SimpleNamespace(
        books=books,
        book_cover_candidates=private_candidates,
        admin_upload_audit=audits,
        categories=EmptyCollection(),
        settings=EmptyCollection(),
    )
    private_url = "https://res.cloudinary.com/demo/image/upload/jekyll-private-front.png"
    private_result = {
        **upload_result(),
        "cover_url": private_url,
        "srcset": f"{private_url} 1x",
    }

    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setattr(server, "_ensure_cloudinary", lambda: None)
    monkeypatch.setattr(
        server,
        "_process_book_cover_candidate",
        lambda _body, asset_id, *, kind: (
            private_result
            if asset_id
            == content_addressed_cover_candidate_asset_id(
                slug,
                hashlib.sha256(image_bytes()).hexdigest(),
            )
            and kind == "front"
            else pytest.fail("Controlled-only cover candidate used the wrong asset namespace.")
        ),
    )
    monkeypatch.setattr(server, "_public_cache_get", no_cache)
    monkeypatch.setattr(server, "_public_cache_set", no_cache)
    monkeypatch.setattr(server, "_redis_cache_get", no_cache)
    monkeypatch.setattr(server, "_redis_cache_set", no_cache)

    status_before = asyncio.run(
        server.admin_list_book_cover_status(
            _={"sub": "owner-1", "email": "owner@example.com"}
        )
    )
    row_before = next(book for book in status_before["books"] if book["slug"] == slug)
    assert row_before["admin_book_exists"] is False
    assert row_before["upload_eligibility_source"] == "controlled_publication"
    assert row_before["can_upload"] is True
    assert row_before["front_status"] == "CANONICAL_READY"
    canonical_front_before = row_before["canonical_front_cover_url"]
    assert canonical_front_before

    response = asyncio.run(
        server.admin_upload_cover(
            slug=slug,
            kind="front",
            confirm_expensive_job=True,
            file=FakeUpload(image_bytes()),
            admin={"sub": "owner-1", "email": "owner@example.com"},
        )
    )

    assert response["success"] is True
    assert response["upload_eligibility_source"] == "controlled_publication"
    assert response["cover_url"] == private_url
    assert books.docs == []
    candidate = private_candidates.docs[f"{slug}:front"]
    assert candidate["candidate_url"] == private_url
    assert candidate["audit_status"] == "ADMIN_UPLOADED_PENDING_CANONICAL_REVIEW"
    assert audits.docs[0]["slug"] == slug
    assert audits.docs[0]["upload_eligibility_source"] == "controlled_publication"

    status_after = asyncio.run(
        server.admin_list_book_cover_status(
            _={"sub": "owner-1", "email": "owner@example.com"}
        )
    )
    row_after = next(book for book in status_after["books"] if book["slug"] == slug)
    assert row_after["front_status"] == "CANONICAL_READY"
    assert row_after["admin_front_cover_url"] == private_url
    assert row_after["canonical_front_cover_url"] == canonical_front_before
    assert canonical_front_before != private_url

    public_payloads = {
        "/api/books": asyncio.run(server.list_books()),
        f"/api/books/{slug}": asyncio.run(server.get_book(slug)),
        "/api/home": asyncio.run(server.get_home_payload()),
        "/api/home/curated": asyncio.run(server.get_home_curated()),
        f"/api/reader/book/{slug}/manifest": asyncio.run(
            server._reader_book_manifest_doc(slug)
        ),
    }
    for route, payload in public_payloads.items():
        assert private_url not in json.dumps(payload, ensure_ascii=False), route

    detail = public_payloads[f"/api/books/{slug}"]
    manifest = public_payloads[f"/api/reader/book/{slug}/manifest"]
    assert detail["reader_enabled"] is True
    assert detail["audio_enabled"] is False
    assert manifest["book"]["reader_enabled"] is True
    assert manifest["audio"]["enabled"] is False


def test_admin_cover_upload_rejects_missing_authentication():
    client = TestClient(server.app)
    response = client.post(
        "/api/admin/books/jekyll-and-hyde/cover",
        params={"kind": "front", "confirm_expensive_job": "true"},
        files={"file": ("front.png", image_bytes(), "image/png")},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_admin_cover_upload_rejects_disabled_intake_before_reading_file(monkeypatch):
    class UnreadableUpload:
        async def read(self):
            raise AssertionError("Disabled cover intake must stop before reading a file.")

    monkeypatch.setattr(server, "ENABLE_ADMIN_COVER_UPLOADS", False)

    with pytest.raises(server.HTTPException) as exc_info:
        asyncio.run(
            server.admin_upload_cover(
                slug="jekyll-and-hyde",
                kind="front",
                confirm_expensive_job=True,
                file=UnreadableUpload(),
                admin={"sub": "owner-1", "email": "owner@example.com"},
            )
        )

    assert exc_info.value.status_code == 503
    assert "admin_cover_uploads is disabled" in str(exc_info.value.detail)


def test_controlled_only_cover_upload_rejects_unapproved_rights(monkeypatch):
    slug = "jekyll-and-hyde"
    private_candidates = PrivateCoverCandidates()
    audits = AuditCollection()
    fake_db = SimpleNamespace(
        books=ImmutableBooks([]),
        book_cover_candidates=private_candidates,
        admin_upload_audit=audits,
    )
    unapproved = {
        "id": "controlled-jekyll-and-hyde",
        "slug": slug,
        "title": "The Strange Case of Dr. Jekyll and Mr. Hyde",
        "author": "Robert Louis Stevenson",
        "is_published": True,
        "approved_to_publish": False,
        "rights_tier": "C",
        "verification_status": "blocked",
        "qa_status": "QA_PASSED",
        "source_hash": "a" * 64,
        "content_hash": "b" * 64,
        "provenance_hash": "c" * 64,
        "source_url": "https://example.invalid/source",
        "source_name": "Unapproved source",
        "source_license": "unknown",
    }

    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setattr(
        server,
        "load_controlled_artifact_book",
        lambda requested_slug, include_content=False: (
            unapproved if requested_slug == slug and include_content is False else None
        ),
    )
    monkeypatch.setattr(
        server,
        "_ensure_cloudinary",
        lambda: pytest.fail("Rights rejection must occur before Cloudinary setup."),
    )
    monkeypatch.setattr(
        server,
        "_process_book_cover_candidate",
        lambda *_args, **_kwargs: pytest.fail(
            "Rights rejection must occur before candidate upload."
        ),
    )

    with pytest.raises(server.HTTPException) as exc_info:
        asyncio.run(
            server.admin_upload_cover(
                slug=slug,
                kind="front",
                confirm_expensive_job=True,
                file=FakeUpload(image_bytes()),
                admin={"sub": "owner-1", "email": "owner@example.com"},
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["message"] == (
        "Visual asset cannot be uploaded without an approved controlled publication."
    )
    assert private_candidates.docs == {}
    assert audits.docs == []


def test_persisted_sprint1_inventory_matches_the_32_title_contract():
    report = json.loads(
        (
            ROOT
            / "internal/earnalism_intelligence/catalog_truth/sprint1_missing_cover_inventory_20260728.json"
        ).read_text(encoding="utf-8")
    )

    assert report["summary"] == {
        "sprint1_titles_checked": 32,
        "valid_cover_pairs": 20,
        "missing_both": 11,
        "missing_front_only": 0,
        "missing_back_only": 0,
        "broken_populated_urls": 0,
        "title_mismatched_pairs": 1,
        "titles_needing_remediation": 12,
    }
    assert len(report["books"]) == 12
    assert {book["slug"] for book in report["books"]} >= {
        "pather-panchali",
        "devdas",
        "a-ghost-story",
    }
    assert report["release_truth_unchanged"] is True
