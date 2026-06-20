from __future__ import annotations

import os

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "public-catalog-projection-test-secret")

from backend import catalog_truth
from backend import server


def test_public_book_out_drops_private_catalog_fields():
    artifact = catalog_truth.load_dracula_artifact_book(include_content=True)
    assert artifact is not None
    artifact["rights_metadata"] = {"rights_tier": "A"}
    artifact["audiobook_assets"] = {"mp3": "https://cdn.example.com/dracula.mp3"}

    projected = catalog_truth.public_book_projection(artifact)
    dumped = server.PublicBookOut.model_validate(projected).model_dump()

    serialized = str(dumped)
    assert dumped["slug"] == "dracula"
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
