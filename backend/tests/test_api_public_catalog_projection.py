from __future__ import annotations

import os

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "public-catalog-projection-test-secret")

from backend import catalog_truth
from backend import server


def test_public_book_out_drops_private_catalog_fields():
    artifact = catalog_truth.load_controlled_artifact_book("a-ghost-story", include_content=True)
    assert artifact is not None
    artifact["rights_metadata"] = {"rights_tier": "A"}
    artifact["audiobook_assets"] = {"mp3": "https://cdn.example.com/dracula.mp3"}

    projected = catalog_truth.public_book_projection(artifact)
    dumped = server.PublicBookOut.model_validate(projected).model_dump()

    serialized = str(dumped)
    assert dumped["slug"] == "a-ghost-story"
    assert dumped["reader_enabled"] is True
    assert dumped["preview_enabled"] is True
    assert dumped["audio_enabled"] is False
    assert dumped["audiobook_enabled"] is False
    assert dumped["audio_url"] == ""
    assert "rights_metadata" not in serialized
    assert "source_hash" not in serialized
    assert "content_hash" not in serialized
    assert "provenance_hash" not in serialized
    assert "audiobook_assets" not in serialized
    assert "https://cdn.example.com/dracula.mp3" not in serialized
    assert all("content" not in chapter for chapter in dumped["chapters"])


def test_public_projection_keeps_kshudhita_pipeline_only():
    projected = catalog_truth.public_book_projection(
        {
            "slug": "kshudhita-pashan",
            "title": "Kshudhita Pashan",
            "is_published": True,
            "pipeline_stage": "PIPELINE_ONLY",
            "reader_url": "/reader/kshudhita-pashan",
            "audiobook_assets": {"mp3": "https://cdn.example.com/kshudhita.mp3"},
        }
    )

    assert projected["publication_status"] == "PIPELINE_CANDIDATE"
    assert projected["reader_enabled"] is False
    assert projected["preview_enabled"] is False
    assert projected["audio_enabled"] is False
    assert projected["audiobook_enabled"] is False
    assert projected["reader_url"] == ""
    assert projected["preview_url"] == ""
    assert projected["audio_url"] == ""
    assert "audiobook_assets" not in projected


def test_actual_book_response_model_keeps_approved_package_metadata(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    artifact = server._controlled_artifact_doc("the-open-window")
    assert artifact is not None
    async def no_cache(*args, **kwargs): return None
    async def candidate(*args, **kwargs): return artifact, "controlled"
    monkeypatch.setattr(server, "_public_cache_get", no_cache)
    monkeypatch.setattr(server, "_public_cache_set", no_cache)
    monkeypatch.setattr(server, "_find_public_book_candidate", candidate)
    app = FastAPI()
    app.get("/books/{slug}", response_model=server.PublicBookOut)(server.get_book)
    response = TestClient(app).get("/books/the-open-window")
    assert response.status_code == 200
    payload = response.json()
    assert payload["audio_enabled"] is True
    assert payload["audiobook_delivery_mode"] == "PROTECTED_PACKAGE_V2"
    assert payload["audiobook_package_version"] == "sha256-8e5c83a835cf8bea0a34809f8640603a2158a3cfe1aa8f1ac71117259a665b26"
    assert payload["audiobook_duration_ms"] == 491436
    assert payload["audio_url"] == ""
    for private in ["audiobook_packages", "audiobook_public_package_approval", "audiobook_package_release_evidence", "rights_metadata", "source_hash"]:
        assert private not in payload


def test_unreleased_book_response_model_keeps_package_metadata_empty():
    artifact = server._controlled_artifact_doc("a-ghost-story")
    projected = server._safe_live_public_projection(artifact)
    payload = server.PublicBookOut.model_validate(projected).model_dump()
    assert payload["audio_enabled"] is False
    assert payload["audiobook_delivery_mode"] == ""
    assert payload["audiobook_package_version"] == ""
    assert payload["audiobook_duration_ms"] == 0
