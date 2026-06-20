from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "catalog-truth-test-secret")

from backend import catalog_truth
from backend import server
from scripts import catalog_truth_audit


def dracula_book(**overrides):
    book = {
        "id": "book-dracula",
        "slug": "dracula",
        "title": "Dracula",
        "author": "Bram Stoker",
        "category_slug": "gothic-fiction",
        "short_description": "A controlled launch classic.",
        "is_published": True,
        "rights_metadata": {
            "rights_tier": "A",
            "verification_status": "approved",
            "blocked_reason": "",
            "source_url": "https://www.gutenberg.org/ebooks/345",
            "source_name": "Project Gutenberg",
            "source_license": "Project Gutenberg License",
        },
        "source_hash": "source-hash",
        "content_hash": "content-hash",
        "provenance_hash": "provenance-hash",
        "qa_status": "QA_PASSED",
        "approved_to_publish": True,
        "publication_status": "LIVE_APPROVED",
        "audiobook_enabled": True,
        "audiobook_assets": {"mp3": "https://cdn.example.com/dracula.mp3"},
        "chapters": [
            {
                "id": "chapter-1",
                "title": "Chapter 1",
                "order": 1,
                "is_preview": True,
                "content": "Reader-facing chapter body should never leak in metadata projection.",
            }
        ],
    }
    book.update(overrides)
    return book


def pipeline_book(**overrides):
    book = {
        "id": "book-kshudhita",
        "slug": "kshudhita-pashan",
        "title": "Kshudhita Pashan",
        "author": "Rabindranath Tagore",
        "category_slug": "gothic-fiction",
        "short_description": "Pipeline-only Bengali gothic candidate.",
        "is_published": True,
        "pipeline_stage": "PIPELINE_ONLY",
        "rights_metadata": {
            "rights_tier": "A",
            "verification_status": "pending",
            "blocked_reason": "",
        },
        "chapters": [{"id": "chapter-1", "content": "Pipeline source text"}],
    }
    book.update(overrides)
    return book


def test_dracula_is_the_only_live_approved_book():
    assert catalog_truth.is_live_approved_book(dracula_book()) is True
    assert catalog_truth.is_live_approved_book(dracula_book(slug="frankenstein")) is False
    assert catalog_truth.is_live_approved_book(dracula_book(rights_metadata={"rights_tier": "B"})) is False


def test_shared_controlled_launch_config_matches_backend_and_audit():
    assert catalog_truth.CONTROLLED_LIVE_BOOK_SLUGS == ("dracula",)
    assert catalog_truth.PIPELINE_CANDIDATE_SLUGS == {"kshudhita-pashan"}
    assert catalog_truth.AUDIO_ENABLED_SLUGS == set()
    assert catalog_truth_audit.frontend_controlled_live_slugs() == {"dracula"}


def test_dracula_projection_enables_reader_preview_but_disables_audio():
    projected = catalog_truth.public_book_projection(dracula_book())

    assert projected["publication_status"] == "LIVE_APPROVED"
    assert projected["reader_enabled"] is True
    assert projected["preview_enabled"] is True
    assert projected["reader_url"] == "/reader/dracula"
    assert projected["preview_url"] == "/reader/dracula"
    assert projected["audio_enabled"] is False
    assert projected["audiobook_enabled"] is False
    assert projected["audio_url"] == ""
    assert projected["cta_label"] == "Start Dracula"


def test_projection_removes_private_rights_audio_and_chapter_content():
    projected = catalog_truth.public_book_projection(dracula_book())

    assert "rights_metadata" not in projected
    assert "source_hash" not in projected
    assert "content_hash" not in projected
    assert "provenance_hash" not in projected
    assert "audiobook_assets" not in projected
    assert "audiobook" not in projected
    assert "content" not in projected["chapters"][0]
    assert projected["public_route"] == "/book/dracula"
    assert projected["source_note"]
    assert projected["rights_note"]


def test_public_book_response_model_is_safe_contract():
    projected = catalog_truth.public_book_projection(
        dracula_book(audiobook={"url": "https://cdn.example.com/dracula.mp3"})
    )
    projected["rights_metadata"] = {"rights_tier": "A"}
    projected["source_hash"] = "must-not-serialize"
    projected["audiobook_assets"] = {"mp3": "https://cdn.example.com/dracula.mp3"}

    dumped = server.PublicBookOut.model_validate(projected).model_dump()

    assert dumped["slug"] == "dracula"
    assert dumped["reader_enabled"] is True
    assert dumped["audio_enabled"] is False
    assert dumped["audiobook_enabled"] is False
    assert dumped["audio_url"] == ""
    assert "rights_metadata" not in dumped
    assert "source_hash" not in dumped
    assert "audiobook_assets" not in dumped
    assert "content" not in dumped["chapters"][0]


def test_public_book_detail_route_uses_safe_response_model():
    route = next(
        route
        for route in server.api.routes
        if getattr(route, "path", "") == "/api/books/{slug}" and "GET" in getattr(route, "methods", set())
    )

    assert route.response_model is server.PublicBookOut


def test_kshudhita_is_pipeline_only_with_notify_ctas():
    projected = catalog_truth.public_book_projection(pipeline_book())

    assert projected["publication_status"] == "PIPELINE_CANDIDATE"
    assert projected["reader_enabled"] is False
    assert projected["preview_enabled"] is False
    assert projected["audio_enabled"] is False
    assert projected["reader_url"] == ""
    assert projected["preview_url"] == ""
    assert projected["cta_label"] == "Notify Me"
    assert projected["secondary_cta_label"] == "Reading Circle"


def test_unapproved_book_cannot_expose_reader_preview_or_audio():
    book = dracula_book(slug="frankenstein", title="Frankenstein")

    assert catalog_truth.can_expose_reader(book) is False
    assert catalog_truth.can_expose_preview(book) is False
    assert catalog_truth.can_expose_audio(book) is False
    assert catalog_truth.public_book_projection(book)["reader_enabled"] is False


def test_missing_traceability_blocks_live_status(monkeypatch):
    monkeypatch.setattr(catalog_truth, "evidence_for_book", lambda book: {})
    book = dracula_book(source_hash="")

    assert catalog_truth.normalize_book_publication_status(book) != "LIVE_APPROVED"
    assert catalog_truth.can_expose_reader(book) is False


def test_blocked_reason_quarantines_book():
    book = dracula_book(rights_metadata={**dracula_book()["rights_metadata"], "blocked_reason": "unsafe"})

    assert catalog_truth.normalize_book_publication_status(book) == "QUARANTINE"
    assert catalog_truth.can_expose_reader(book) is False


def test_catalog_truth_summary_flags_unapproved_sitemap_entries():
    rows = [
        catalog_truth.catalog_truth_row(dracula_book(), sitemap_urls={"https://theearnalism.com/book/dracula"}),
        catalog_truth.catalog_truth_row(pipeline_book(), sitemap_urls={"https://theearnalism.com/book/kshudhita-pashan"}),
    ]

    summary = catalog_truth.catalog_truth_summary(rows)

    assert summary["live_approved_count"] == 1
    assert summary["dracula_only_live_approved"] is True
    assert summary["pipeline_candidate_count"] == 1
    assert summary["unapproved_sitemap_count"] == 1
    assert "Unapproved sitemap entries detected" in summary["launch_blockers"]


def test_live_approved_mongo_query_preserves_rights_and_search_or():
    query = catalog_truth.live_approved_mongo_query(
        {"$or": [{"title": {"$regex": "Dracula", "$options": "i"}}]}
    )

    assert query["slug"] == {"$in": ["dracula"]}
    assert query["is_published"] is True
    assert "rights_metadata.rights_tier" not in query
    assert "rights_metadata.verification_status" not in query
    assert query["$or"][0]["title"] == {"$regex": "Dracula", "$options": "i"}


def test_server_controlled_public_query_uses_catalog_truth():
    assert server._controlled_public_book_query() == catalog_truth.live_approved_mongo_query()
    assert server._is_controlled_public_slug("Dracula") is True
    assert server._is_controlled_public_slug("frankenstein") is False


def test_reader_manifest_audio_is_disabled_even_when_assets_exist():
    audio = server._reader_manifest_audio(dracula_book(), "dracula")

    assert audio["enabled"] is False
    assert audio["assets"] == {}
    assert audio["url"] == ""
    assert audio["provider"] == ""


def test_reader_manifest_non_dracula_returns_none():
    result = asyncio.run(server._reader_book_manifest_doc("kshudhita-pashan"))

    assert result is None


def test_public_audiobook_endpoint_404s_non_dracula_without_db_call():
    request = SimpleNamespace(headers={}, method="GET")

    with pytest.raises(server.HTTPException) as exc:
        asyncio.run(server._reader_book_audiobook_asset("kshudhita-pashan", "mp3", request))

    assert exc.value.status_code == 404


def test_public_audiobook_endpoint_404s_dracula_when_audio_disabled(monkeypatch):
    class FakeBooks:
        async def find_one(self, query, projection):
            assert query["slug"] == "dracula"
            return dracula_book()

    fake_db = SimpleNamespace(books=FakeBooks())
    monkeypatch.setattr(server, "db", fake_db)
    request = SimpleNamespace(headers={}, method="GET")

    with pytest.raises(server.HTTPException) as exc:
        asyncio.run(server._reader_book_audiobook_asset("dracula", "mp3", request))

    assert exc.value.status_code == 404
    assert "Audiobook asset" in exc.value.detail


def test_sitemap_truth_is_dracula_only_for_book_routes():
    sitemap = (catalog_truth.ROOT / "frontend" / "public" / "sitemap.xml").read_text(encoding="utf-8")

    assert "/book/dracula" in sitemap
    assert "/reader/" not in sitemap
    assert "/book/frankenstein" not in sitemap
    assert "/book/kshudhita-pashan" not in sitemap


def test_catalog_truth_rows_keep_audio_false_for_every_status():
    rows = [
        catalog_truth.catalog_truth_row(dracula_book()),
        catalog_truth.catalog_truth_row(pipeline_book()),
        catalog_truth.catalog_truth_row(dracula_book(slug="devdas", title="Devdas")),
    ]

    assert all(row["audio_enabled"] is False for row in rows)


class FakeCursor:
    def __init__(self, docs):
        self.docs = list(docs)

    def sort(self, *_args, **_kwargs):
        return self

    def skip(self, value):
        self.docs = self.docs[int(value or 0) :]
        return self

    def limit(self, value):
        self.docs = self.docs[: int(value or len(self.docs))]
        return self

    async def to_list(self, *_args, **_kwargs):
        return list(self.docs)


class FakePublicBooks:
    def __init__(self, docs):
        self.docs = list(docs)
        self.last_query = None

    def _matches(self, doc, query):
        slug_filter = query.get("slug")
        if isinstance(slug_filter, dict) and "$in" in slug_filter:
            if doc.get("slug") not in slug_filter["$in"]:
                return False
        elif slug_filter and doc.get("slug") != slug_filter:
            return False
        if query.get("is_published") is True and doc.get("is_published") is not True:
            return False
        if query.get("category_slug") and doc.get("category_slug") != query["category_slug"]:
            return False
        return True

    def find(self, query, _projection):
        self.last_query = query
        return FakeCursor([doc for doc in self.docs if self._matches(doc, query)])

    async def find_one(self, query, _projection):
        self.last_query = query
        for doc in self.docs:
            if self._matches(doc, query):
                return doc
        return None

    async def count_documents(self, query):
        return len([doc for doc in self.docs if self._matches(doc, query)])


async def noop_cache_get(*_args, **_kwargs):
    return None


async def noop_cache_set(*_args, **_kwargs):
    return None


def test_api_books_returns_dracula_as_only_live_readable_item(monkeypatch):
    books = FakePublicBooks(
        [
            dracula_book(rights_metadata={}),
            dracula_book(
                slug="frankenstein",
                title="Frankenstein",
                audiobook_enabled=True,
                audio_url="https://cdn.example.com/frankenstein.mp3",
            ),
        ]
    )
    monkeypatch.setattr(server, "db", SimpleNamespace(books=books))
    monkeypatch.setattr(server, "_public_cache_get", noop_cache_get)
    monkeypatch.setattr(server, "_public_cache_set", noop_cache_set)

    result = asyncio.run(server.list_books())

    assert [book["slug"] for book in result if book["reader_enabled"]] == ["dracula"]
    assert result[0]["publication_status"] == "LIVE_APPROVED"
    assert result[0]["reader_url"] == "/reader/dracula"
    assert result[0]["preview_url"] == "/reader/dracula"
    assert result[0]["audio_enabled"] is False
    assert result[0]["audiobook_enabled"] is False
    assert result[0]["audio_status"] == "NOT_AVAILABLE"
    assert "audiobook_assets" not in result[0]
    assert "audiobook" not in result[0]
    assert books.last_query["slug"] == {"$in": ["dracula"]}


def test_api_books_contains_no_non_dracula_reader_preview_or_audio(monkeypatch):
    books = FakePublicBooks(
        [
            dracula_book(),
            dracula_book(
                slug="pride-and-prejudice",
                title="Pride and Prejudice",
                reader_enabled=True,
                preview_url="/reader/pride-and-prejudice",
                audiobook_enabled=True,
                audiobook_assets={"mp3": "https://cdn.example.com/pride.mp3"},
            ),
        ]
    )
    monkeypatch.setattr(server, "db", SimpleNamespace(books=books))
    monkeypatch.setattr(server, "_public_cache_get", noop_cache_get)
    monkeypatch.setattr(server, "_public_cache_set", noop_cache_set)

    result = asyncio.run(server.list_books())

    assert [book["slug"] for book in result] == ["dracula"]
    assert all(book["slug"] == "dracula" or not book.get("reader_url") for book in result)
    assert all(book["slug"] == "dracula" or not book.get("preview_url") for book in result)
    assert all(book.get("audio_enabled") is False for book in result)
    assert all(book.get("audiobook_enabled") is False for book in result)


def test_api_book_detail_returns_safe_dracula_public_projection(monkeypatch):
    books = FakePublicBooks(
        [
            dracula_book(
                audiobook_enabled=True,
                audiobook_assets={"mp3": "https://cdn.example.com/dracula.mp3"},
                rights_metadata={},
            )
        ]
    )
    monkeypatch.setattr(server, "db", SimpleNamespace(books=books))
    monkeypatch.setattr(server, "_public_cache_get", noop_cache_get)
    monkeypatch.setattr(server, "_public_cache_set", noop_cache_set)

    result = asyncio.run(server.get_book("dracula"))
    dumped = server.PublicBookOut.model_validate(result).model_dump()

    assert dumped["slug"] == "dracula"
    assert dumped["publication_status"] == "LIVE_APPROVED"
    assert dumped["reader_enabled"] is True
    assert dumped["preview_enabled"] is True
    assert dumped["audio_enabled"] is False
    assert dumped["audiobook_enabled"] is False
    assert dumped["audio_status"] == "NOT_AVAILABLE"
    assert dumped["public_route"] == "/book/dracula"
    assert dumped["source_note"]
    assert dumped["rights_note"]
    assert "audiobook_assets" not in result
    assert "rights_metadata" not in result
    assert "source_hash" not in result


def api_result(status, payload=None):
    return catalog_truth_audit.EndpointResult(status=status, json_data=payload, body="")


def base_api_mapping(**overrides):
    dracula = catalog_truth.public_book_projection(dracula_book())
    manifest_chapters = [
        {"id": f"chapter-{index:03d}", "title": f"Chapter {index}", "order": index, "is_preview": index == 1}
        for index in range(1, 28)
    ]
    mapping = {
        "/books": api_result(200, [dracula]),
        "/books/dracula": api_result(200, dracula),
        "/books/kshudhita-pashan": api_result(404, {"detail": "Book not found"}),
        "/controlled-launch/status": api_result(200, {"catalog_truth_status": "PASS"}),
        "/reader/book/dracula/manifest": api_result(
            200,
            {
                "book": dracula,
                "chapters": manifest_chapters,
                "audio": {"enabled": False, "assets": {}, "url": ""},
            },
        ),
        "/reader/book/kshudhita-pashan/manifest": api_result(404, {"detail": "Book not found"}),
        "/reader/book/dracula/audiobook": api_result(404, {"detail": "Audiobook asset not found"}),
        "/reader/book/kshudhita-pashan/audiobook": api_result(404, {"detail": "Audiobook asset not found"}),
    }
    mapping.update(overrides)
    return mapping


def fake_api_fetcher(mapping):
    def fetcher(api_url, path, *, timeout_ms=10_000):
        return mapping.get(path, api_result(404, {"detail": "not found"}))

    return fetcher


def run_api_audit(mapping, monkeypatch):
    monkeypatch.setattr(catalog_truth_audit, "frontend_controlled_live_slugs", lambda path=None: {"dracula"})
    return catalog_truth_audit.api_audit_result(
        "https://api.example.test/api",
        fetcher=fake_api_fetcher(mapping),
    )


def test_api_audit_passes_with_dracula_only_response(monkeypatch):
    result = run_api_audit(base_api_mapping(), monkeypatch)

    assert result["summary"]["launch_blockers"] == []
    assert result["summary"]["live_approved_count"] == 1
    assert result["summary"]["dracula_only_live_approved"] is True


def test_api_audit_fails_if_dracula_detail_leaks_private_fields(monkeypatch):
    unsafe_dracula = {
        **catalog_truth.public_book_projection(dracula_book()),
        "rights_metadata": {"rights_tier": "A"},
        "source_hash": "source-hash",
        "content_hash": "content-hash",
        "provenance_hash": "provenance-hash",
        "audiobook_assets": {"mp3": "https://cdn.example.com/dracula.mp3"},
    }
    mapping = base_api_mapping(**{"/books/dracula": api_result(200, unsafe_dracula)})

    result = run_api_audit(mapping, monkeypatch)

    assert any("exposes forbidden public field" in blocker for blocker in result["summary"]["launch_blockers"])


def test_api_audit_fails_if_dracula_detail_truth_fields_are_wrong(monkeypatch):
    unsafe_dracula = {
        **catalog_truth.public_book_projection(dracula_book()),
        "audio_enabled": True,
        "audio_url": "https://cdn.example.com/dracula.mp3",
    }
    mapping = base_api_mapping(**{"/books/dracula": api_result(200, unsafe_dracula)})

    result = run_api_audit(mapping, monkeypatch)

    assert any("/books/dracula audio_enabled" in blocker for blocker in result["summary"]["launch_blockers"])


def test_api_audit_fails_if_kshudhita_detail_is_not_pipeline_safe(monkeypatch):
    unsafe_pipeline = {
        **catalog_truth.public_book_projection(pipeline_book()),
        "reader_enabled": True,
        "reader_url": "/reader/kshudhita-pashan",
        "source_hash": "source-hash",
    }
    mapping = base_api_mapping(**{"/books/kshudhita-pashan": api_result(200, unsafe_pipeline)})

    result = run_api_audit(mapping, monkeypatch)

    blockers = result["summary"]["launch_blockers"]
    assert any("/books/kshudhita-pashan exposes forbidden public field" in blocker for blocker in blockers)
    assert any("/books/kshudhita-pashan reader_enabled" in blocker for blocker in blockers)


def test_api_audit_fails_if_non_dracula_reader_enabled(monkeypatch):
    frankenstein = {
        "slug": "frankenstein",
        "title": "Frankenstein",
        "publication_status": "COMING_SOON",
        "reader_enabled": True,
        "preview_enabled": False,
        "audio_enabled": False,
    }
    mapping = base_api_mapping(
        **{
            "/books": api_result(200, [catalog_truth.public_book_projection(dracula_book()), frankenstein]),
        }
    )

    result = run_api_audit(mapping, monkeypatch)

    assert any("Non-Dracula reader exposure" in blocker for blocker in result["summary"]["launch_blockers"])


def test_api_audit_fails_if_non_dracula_exposes_audio_aliases(monkeypatch):
    unsafe = {
        "slug": "frankenstein",
        "title": "Frankenstein",
        "publication_status": "COMING_SOON",
        "reader_enabled": False,
        "preview_enabled": False,
        "listen_url": "https://cdn.example.com/frankenstein.mp3",
        "audio_files": {"mp3": "https://cdn.example.com/frankenstein.mp3"},
    }
    mapping = base_api_mapping(
        **{
            "/books": api_result(200, [catalog_truth.public_book_projection(dracula_book()), unsafe]),
        }
    )

    result = run_api_audit(mapping, monkeypatch)

    assert any("Audio exposure detected in /books: frankenstein" in blocker for blocker in result["summary"]["launch_blockers"])


def test_api_audit_fails_if_kshudhita_manifest_returns_200(monkeypatch):
    mapping = base_api_mapping(
        **{
            "/reader/book/kshudhita-pashan/manifest": api_result(200, {"book": {"slug": "kshudhita-pashan"}}),
        }
    )

    result = run_api_audit(mapping, monkeypatch)

    assert any("kshudhita-pashan/manifest" in blocker for blocker in result["summary"]["launch_blockers"])


def test_api_audit_fails_if_dracula_audiobook_returns_200(monkeypatch):
    mapping = base_api_mapping(
        **{
            "/reader/book/dracula/audiobook": api_result(200, {"url": "https://cdn.example.com/dracula.mp3"}),
        }
    )

    result = run_api_audit(mapping, monkeypatch)

    assert any("dracula/audiobook" in blocker for blocker in result["summary"]["launch_blockers"])


def test_api_audit_passes_if_dracula_audiobook_returns_404(monkeypatch):
    result = run_api_audit(base_api_mapping(), monkeypatch)

    assert not any("dracula/audiobook" in blocker for blocker in result["summary"]["launch_blockers"])


def test_api_audit_fails_if_books_returns_zero_live_items(monkeypatch):
    mapping = base_api_mapping(**{"/books": api_result(200, [])})

    result = run_api_audit(mapping, monkeypatch)

    assert any("does not contain Dracula" in blocker for blocker in result["summary"]["launch_blockers"])


def test_api_audit_fails_if_dracula_detail_returns_404(monkeypatch):
    mapping = base_api_mapping(**{"/books/dracula": api_result(404, {"detail": "Book not found"})})

    result = run_api_audit(mapping, monkeypatch)

    assert any("/books/dracula did not return 200" in blocker for blocker in result["summary"]["launch_blockers"])
