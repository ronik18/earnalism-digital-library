from __future__ import annotations

import asyncio
import hashlib
import json
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "catalog-truth-test-secret")

from backend import catalog_truth
from backend import server
from scripts import catalog_truth_audit


# Independent release expectation; do not derive it from the artifact under test.
CURRENT_RELEASED_SLUGS = ('a-ghost-story', 'the-tell-tale-heart', 'radharani', 'a-white-heron', 'the-gift-of-the-magi', 'the-canterville-ghost', 'the-adventures-of-sherlock-holmes', 'agentic-ai-with-python', 'a-horseman-in-the-sky', 'a-mystery-of-heroism', 'a-scandal-in-bohemia', 'jekyll-and-hyde', 'love-of-life', 'the-bishop', 'the-fall-of-the-house-of-usher', 'the-lady-with-the-dog', 'the-man-who-would-be-king', 'the-open-boat', 'the-pit-and-the-pendulum', 'the-stolen-white-elephant', 'an-occurrence-at-owl-creek-bridge', 'the-enchanted-april', 'the-happy-prince', 'picture-of-dorian-gray', 'dracula', 'book-edfcf810c5', 'muchiram-gurer-jibanchorit', 'bn-059', 'the-call-of-the-wild', 'the-student', 'the-art-of-money-getting', 'bn-035', 'alices-adventures-in-wonderland', 'dsires-baby', 'sredni-vashtar', 'the-cop-and-the-anthem', 'the-open-window', 'the-selfish-giant', 'the-science-of-getting-rich', 'bn-066', 'lokrahasya', 'mrinalini', 'frankenstein', 'pride-and-prejudice', 'the-great-gatsby', 'the-secret-garden', 'the-time-machine', 'acres-of-diamonds', 'my-life-and-work', 'the-principles-of-scientific-management', 'the-wonderful-wizard-of-oz', 'book-5704b31005')

@pytest.fixture(autouse=True)
def enabled_release_fixture_for_legacy_contract_cases(request, monkeypatch):
    """Keep synthetic legacy eligibility fixtures distinct from the current release."""
    if request.node.name in {
        "test_shared_controlled_launch_config_matches_backend_and_audit",
        "test_live_artifact_pack_is_self_contained_for_truth_gate",
        "test_held_dracula_preface_is_valid_structure_not_publication_authority",
        "test_live_approved_mongo_query_preserves_rights_and_search_or",
        "test_server_controlled_public_query_uses_catalog_truth",
        "test_public_release_scope_denies_held_titles_and_never_reopens_historical_manifest_slugs",
        "test_sitemap_truth_lists_only_the_exact_controlled_reader_release",
    }:
        return
    live_slugs = ("dracula", "frankenstein", "a-ghost-story")
    monkeypatch.setattr(catalog_truth, "PUBLIC_READER_EXPOSURE_ENABLED", True)
    monkeypatch.setattr(catalog_truth, "PUBLIC_AUDIO_EXPOSURE_ENABLED", True)
    monkeypatch.setattr(catalog_truth, "LEGACY_CONTROLLED_LIVE_BOOK_SLUGS", live_slugs)
    monkeypatch.setattr(catalog_truth, "CONTROLLED_LIVE_BOOK_SLUGS", live_slugs)
    monkeypatch.setattr(catalog_truth, "AUDIO_ENABLED_SLUGS", {"a-ghost-story"})
    monkeypatch.setattr(server, "PUBLIC_READER_EXPOSURE_ENABLED", True)
    monkeypatch.setattr(server, "CONTROLLED_LIVE_BOOK_SLUGS", live_slugs)


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


def test_live_approved_catalog_gate_follows_the_explicit_controlled_allowlist_fixture():
    assert catalog_truth.is_live_approved_book(dracula_book()) is True
    assert catalog_truth.is_live_approved_book(dracula_book(slug="completely-unknown-title")) is False
    assert catalog_truth.is_live_approved_book(dracula_book(rights_metadata={"rights_tier": "B"})) is False


def test_shared_controlled_launch_config_matches_backend_and_audit():
    assert isinstance(catalog_truth.CONTROLLED_LIVE_BOOK_SLUGS, tuple)
    assert catalog_truth.PUBLIC_READER_EXPOSURE_ENABLED is True
    assert catalog_truth.PUBLIC_AUDIO_EXPOSURE_ENABLED is False
    assert catalog_truth.CONTROLLED_LIVE_BOOK_SLUGS == CURRENT_RELEASED_SLUGS
    assert len(set(CURRENT_RELEASED_SLUGS)) == 52
    assert "book-2b9853ec52" in catalog_truth.PUBLIC_CATALOG_EXCLUDED_SLUGS
    assert "book-2b9853ec52" not in catalog_truth.CONTROLLED_LIVE_BOOK_SLUGS
    assert catalog_truth.PIPELINE_CANDIDATE_SLUGS == {"kshudhita-pashan"}
    assert "book-2b9853ec52" not in catalog_truth.AUDIO_ENABLED_SLUGS
    assert catalog_truth.AUDIO_ENABLED_SLUGS == set()
    live_slugs = catalog_truth_audit.frontend_controlled_live_slugs()
    assert live_slugs == set(CURRENT_RELEASED_SLUGS)
    assert "book-2b9853ec52" not in live_slugs


def test_owner_exclusion_blocks_admin_republication_even_with_legacy_approval():
    blockers = server._publish_blockers(dracula_book(slug="book-2b9853ec52"))

    assert blockers == [
        "Owner exclusion policy blocks this title from public catalog publication."
    ]


def test_live_projection_uses_the_current_read_cta_when_audio_is_disabled():
    projected = catalog_truth.public_book_projection(dracula_book())

    assert projected["publication_status"] == "LIVE_APPROVED"
    assert projected["reader_enabled"] is True
    assert projected["preview_enabled"] is True
    assert projected["reader_url"] == "/reader/dracula"
    assert projected["preview_url"] == "/reader/dracula"
    assert projected["audio_enabled"] is False
    assert projected["audiobook_enabled"] is False
    assert projected["audio_url"] == ""
    assert projected["cta_label"] == "Read"


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


def test_live_artifact_pack_is_self_contained_for_truth_gate(monkeypatch):
    monkeypatch.setattr(catalog_truth, "evidence_for_book", lambda _book: {})

    artifact = catalog_truth.load_controlled_artifact_book("a-ghost-story", include_content=True)

    assert artifact is not None
    assert artifact["slug"] == "a-ghost-story"
    assert len(artifact["chapters"]) == 1
    assert artifact["source_url"] == "https://www.gutenberg.org/ebooks/3189"
    assert artifact["source_hash"]
    assert artifact["content_hash"]
    assert artifact["provenance_hash"]
    assert catalog_truth.is_live_approved_book(artifact) is True

    projected = catalog_truth.public_book_projection(artifact)

    assert projected["publication_status"] == "LIVE_APPROVED"
    assert projected["reader_enabled"] is True
    assert projected["preview_enabled"] is True
    assert projected["audio_enabled"] is False
    assert "source_hash" not in projected
    assert "content_hash" not in projected
    assert "provenance_hash" not in projected
    assert "rights_metadata" not in projected
    assert "audiobook_assets" not in projected

    status = catalog_truth.controlled_artifact_status("a-ghost-story")
    assert status["self_contained_for_truth_gate"] is True
    assert status["fallback_requires_legacy_output_evidence"] is False


def test_backend_packaged_live_artifact_is_valid_for_railway_deploy():
    artifact_dir = Path(__file__).resolve().parents[1] / "data" / "controlled_publications" / "dracula"
    if not (artifact_dir / "public_book.json").exists():
        artifact_dir = Path(__file__).resolve().parents[2] / "data" / "controlled_publications" / "dracula"

    status = catalog_truth.dracula_artifact_status(artifact_dir=artifact_dir)
    if not status["available"]:
        artifact_dir = Path(__file__).resolve().parents[2] / "data" / "controlled_publications" / "dracula"
        status = catalog_truth.dracula_artifact_status(artifact_dir=artifact_dir)
        assert status["available"] is True
    artifact = catalog_truth.load_dracula_artifact_book(include_content=True, artifact_dir=artifact_dir)

    assert status["available"] is True
    assert status["self_contained_for_truth_gate"] is True
    assert status["fallback_requires_legacy_output_evidence"] is False
    assert artifact is not None
    assert catalog_truth.is_live_approved_book(artifact) is True
    assert len(artifact["chapters"]) == 28
    assert [chapter["id"] for chapter in artifact["chapters"]] == (
        ["chapter-000"] + [f"chapter-{number:03d}" for number in range(1, 28)]
    )
    assert artifact["chapters"][0]["title"] == "Preface"


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
    book = dracula_book(slug="completely-unknown-title", title="Unknown")

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

    base_or = query["$and"][0]["$or"]
    controlled_slugs = base_or[0]["$and"][0]["$or"][0]["slug"]["$in"]
    assert controlled_slugs == list(CURRENT_RELEASED_SLUGS)
    assert query["$and"][1]["$or"][0]["title"] == {"$regex": "Dracula", "$options": "i"}


def test_live_approved_mongo_query_keeps_legacy_shape_only_when_public_release_is_enabled(monkeypatch):
    monkeypatch.setattr(catalog_truth, "PUBLIC_READER_EXPOSURE_ENABLED", True)
    monkeypatch.setattr(catalog_truth, "CONTROLLED_LIVE_BOOK_SLUGS", ("dracula",))
    query = catalog_truth.live_approved_mongo_query(
        {"$or": [{"title": {"$regex": "Dracula", "$options": "i"}}]}
    )

    base_or = query["$and"][0]["$or"]
    workflow_guard = base_or[0]["$and"]
    controlled_slugs = workflow_guard[0]["$or"][0]["slug"]["$in"]
    controlled_audio_release = base_or[1]
    assert isinstance(controlled_slugs, list)
    assert "dracula" in controlled_slugs
    assert {"publication_workflow.publication.reader_exposed": True} in workflow_guard
    assert controlled_audio_release == {
        "slug": {"$in": controlled_slugs},
        "audiobook_release_conveyor.schema_version": catalog_truth.AUDIOBOOK_RELEASE_CONVEYOR_SCHEMA,
        "audiobook_release_conveyor.audio_release_approved": True,
    }
    assert "rights_metadata.rights_tier" not in query
    assert "rights_metadata.verification_status" not in query
    assert query["$and"][1]["$or"][0]["title"] == {"$regex": "Dracula", "$options": "i"}


def test_server_controlled_public_query_uses_catalog_truth():
    assert server._controlled_public_book_query() == catalog_truth.live_approved_mongo_query()
    assert server._is_controlled_public_slug("Dracula") is True
    assert server._is_controlled_public_slug("frankenstein") is True


def test_public_release_scope_denies_held_titles_and_never_reopens_historical_manifest_slugs():
    assert server._is_controlled_public_slug("dracula") is True
    assert server._is_controlled_public_slug("a-ghost-story") is True
    for slug in ("yugalanguriya", "bn-060", "the-most-dangerous-game",
                 "great-expectations", "bharat-at-the-crossroads", "kshudhita-pashan"):
        assert server._is_controlled_public_slug(slug) is False
        assert slug not in CURRENT_RELEASED_SLUGS
    query = server._controlled_public_book_query()
    assert query != {"_id": {"$exists": False}}
    controlled_slugs = query["$or"][0]["$and"][0]["$or"][0]["slug"]["$in"]
    assert controlled_slugs == list(CURRENT_RELEASED_SLUGS)


def test_reader_manifest_audio_is_disabled_even_when_assets_exist():
    audio = server._reader_manifest_audio(dracula_book(), "dracula")

    assert audio["enabled"] is False
    assert audio["assets"] == {}
    assert audio["url"] == ""
    assert audio["provider"] == ""


def test_reader_manifest_non_dracula_returns_none():
    result = asyncio.run(server._reader_book_manifest_doc("kshudhita-pashan"))

    assert result is None


def test_public_audiobook_endpoint_404s_pipeline_title_without_exposing_media(monkeypatch):
    class EmptyBooks:
        async def find_one(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(server, "db", SimpleNamespace(books=EmptyBooks()))
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


def test_sitemap_truth_lists_only_the_exact_controlled_reader_release():
    sitemap = (catalog_truth.ROOT / "frontend" / "public" / "sitemap.xml").read_text(encoding="utf-8")

    locations = [element.text for element in ET.fromstring(sitemap).findall(
        "{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
    )]
    book_paths = [urlsplit(location).path for location in locations
                  if urlsplit(location).path.startswith("/book/")]
    assert set(book_paths) == {f"/book/{slug}" for slug in CURRENT_RELEASED_SLUGS}
    assert len(book_paths) == 52
    assert all(not urlsplit(location).path.startswith("/reader/") for location in locations)


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


def test_api_books_uses_the_authoritative_controlled_public_query(monkeypatch):
    books = FakePublicBooks(
        [
            dracula_book(rights_metadata={}),
            dracula_book(
                slug="frankenstein",
                title="Frankenstein",
                rights_metadata={"rights_tier": "B", "verification_status": "approved"},
                audiobook_enabled=True,
                audio_url="https://cdn.example.com/frankenstein.mp3",
            ),
        ]
    )
    monkeypatch.setattr(server, "db", SimpleNamespace(books=books))
    monkeypatch.setattr(server, "_public_cache_get", noop_cache_get)
    monkeypatch.setattr(server, "_public_cache_set", noop_cache_set)

    result = asyncio.run(server.list_books())

    live_slugs = [book["slug"] for book in result if book["reader_enabled"]]
    assert "dracula" in live_slugs
    assert "completely-unknown-title" not in live_slugs
    dracula_row = next(row for row in result if row["slug"] == "dracula")
    assert dracula_row["publication_status"] == "LIVE_APPROVED"
    assert dracula_row["reader_url"] == "/reader/dracula"
    assert dracula_row["preview_enabled"] is False
    assert dracula_row["preview_url"] == ""
    assert dracula_row["audio_enabled"] is False
    assert dracula_row["audiobook_enabled"] is False
    assert dracula_row["audio_status"] == "NOT_AVAILABLE"
    assert "audiobook_assets" not in dracula_row
    assert "audiobook" not in dracula_row
    assert books.last_query == catalog_truth.live_approved_mongo_query()


def test_api_books_denies_unknown_title_reader_preview_and_audio_exposure(monkeypatch):
    books = FakePublicBooks(
        [
            dracula_book(),
            dracula_book(
                slug="completely-unknown-title",
                title="Unknown",
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

    assert "dracula" in [book["slug"] for book in result if book["reader_enabled"]]
    assert "completely-unknown-title" not in {book["slug"] for book in result}


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
    assert dumped["preview_enabled"] is False
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
        "/controlled-launch/status": api_result(
            200,
            {
                "catalog_truth_status": "PASS",
                "live_approved_slugs": ["dracula"],
                "audio_enabled_slugs": [],
            },
        ),
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


def test_api_audit_passes_with_a_minimal_authoritative_status_fixture(monkeypatch):
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


def test_api_audit_fails_if_unexpected_reader_enabled(monkeypatch):
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

    assert any("Unexpected reader exposure in /books: frankenstein" in blocker for blocker in result["summary"]["launch_blockers"])


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


def test_held_dracula_preface_is_valid_structure_not_publication_authority(tmp_path):
    import shutil
    source = catalog_truth.controlled_artifact_dir("dracula")
    target = tmp_path / "dracula"
    shutil.copytree(source, target)
    # Local held-authority fixture: preserve the prior negative approval fact
    # without misclassifying the current accepted Dracula edition as held.
    # Historical approval_evidence.json at ace5e9f87494b82c05abe74a351e07c25447b629
    # SHA256 530e4680a54206e656d9a517aee66ecd2002cc31465ef50e2003718ddcdd078a
    # recorded approved_to_publish=false. Other files retain the current exact
    # preface+27 chapter source; this temporary packet grants no acceptance.
    approval = json.loads((target / "approval_evidence.json").read_text())
    approval["approved_to_publish"] = False
    (target / "approval_evidence.json").write_text(json.dumps(approval, indent=2) + "\n")
    checksums = json.loads((target / "checksum_manifest.json").read_text())
    for entry in checksums["files"]:
        if entry["file"] == "approval_evidence.json":
            entry["sha256"] = hashlib.sha256((target / entry["file"]).read_bytes()).hexdigest()
    (target / "checksum_manifest.json").write_text(json.dumps(checksums, indent=2) + "\n")
    catalog_truth.clear_controlled_artifact_caches()
    issues = catalog_truth.dracula_artifact_validation_issues(str(target))
    assert not any("Checksum mismatch" in issue for issue in issues)
    assert not any("chapter_count" in issue or "chapter sequence" in issue or "wrong order" in issue or "selected layout" in issue for issue in issues)
    assert any("approved_to_publish" in issue for issue in issues)
    assert catalog_truth.load_dracula_artifact_book(artifact_dir=target) is None
    shutil.copyfile(target / "chapters/chapter-027.json", target / "chapters/chapter-028.json")
    catalog_truth.clear_controlled_artifact_caches()
    issues = catalog_truth.dracula_artifact_validation_issues(str(target))
    assert any("exact selected layout" in issue for issue in issues)
