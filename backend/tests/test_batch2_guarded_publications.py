from __future__ import annotations

import asyncio
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "batch2-live-audio-test-secret")

from backend import catalog_truth, server
from backend.publication_manifest import validate_manifest
from backend.home_curation import build_home_curated_payload


ROOT = Path(__file__).resolve().parents[2]
GUARDED_AUDIO_SLUGS = ("the-selfish-giant",)
HISTORICAL_AUDIO_SLUGS = ("a-white-heron", "the-selfish-giant")


class ConveyorBooks:
    def __init__(self, slug: str, release: dict):
        self.slug = slug
        self.release = release

    async def find_one(self, query, _projection=None):
        if query.get("slug") != self.slug:
            return None
        if not isinstance(_projection, dict):
            return dict(self.release)
        return {
            key: value
            for key, value in self.release.items()
            if _projection.get(key) == 1
        }


async def no_cache(*_args, **_kwargs):
    return None


async def no_cache_write(*_args, **_kwargs):
    return None


async def fixed_generation():
    return 1


@pytest.mark.parametrize("slug", HISTORICAL_AUDIO_SLUGS)
def test_batch2_packets_are_packaged_for_railway_and_byte_identical(slug: str):
    root_dir = ROOT / "data" / "controlled_publications" / slug
    backend_dir = ROOT / "backend" / "data" / "controlled_publications" / slug

    root_files = sorted(path.relative_to(root_dir) for path in root_dir.rglob("*") if path.is_file())
    backend_files = sorted(path.relative_to(backend_dir) for path in backend_dir.rglob("*") if path.is_file())

    assert backend_files == root_files
    for relative_path in root_files:
        assert (backend_dir / relative_path).read_bytes() == (root_dir / relative_path).read_bytes()


@pytest.mark.parametrize("slug", GUARDED_AUDIO_SLUGS)
def test_batch2_historical_audio_packages_remain_unexposed(slug: str):
    artifact_dir = ROOT / "backend" / "data" / "controlled_publications" / slug
    assert catalog_truth.controlled_artifact_validation_issues(slug, str(artifact_dir)) == ()

    public = catalog_truth.read_json_file(artifact_dir / "public_book.json")
    assert public["audio_enabled"] is True
    assert public["audiobook_enabled"] is True
    assert public["audiobook_release_mode"] == "SERVER_OWNED_CONVEYOR"
    assert "backblazeb2.com" not in str(public)
    assert slug not in catalog_truth.AUDIO_ENABLED_SLUGS

    book = catalog_truth.load_controlled_artifact_book(
        slug,
        include_content=False,
        artifact_dir=artifact_dir,
    )

    if slug == "a-white-heron":
        assert book is None
        return

    assert book is not None
    assert catalog_truth.can_expose_reader(book) is False
    assert catalog_truth.can_expose_audio(book) is False

    projection = catalog_truth.public_book_projection(book)
    assert projection is not None
    assert projection["reader_enabled"] is False
    assert projection["audio_enabled"] is False
    assert projection["audiobook_enabled"] is False
    assert projection["audio_url"] == ""

    approval = catalog_truth.read_json_file(artifact_dir / "approval_evidence.json")
    evidence = catalog_truth.read_json_file(artifact_dir / "production_audio_evidence.json")
    assert approval["candidate_fingerprint"] == evidence["candidate_fingerprint"]
    assert approval["audio_sha256"] == evidence["audio_sha256"]
    assert approval["release_blockers"] == []
    assert evidence["production_audio"]["range_status"] == 206
    assert evidence["production_audio"]["content_type"] == "audio/mpeg"
    assert evidence["browser"]["playback_advanced"] is True

    publication = catalog_truth.read_json_file(artifact_dir / "publication_manifest.json")
    assert publication["audio_release"]["discovery_exposed"] is False


@pytest.mark.parametrize("slug", HISTORICAL_AUDIO_SLUGS)
def test_historical_database_audio_claim_cannot_admit_title_outside_release_allowlist(monkeypatch, slug: str):
    release = {
        "slug": slug,
        "audio_enabled": True,
        "audiobook_enabled": True,
        "generate_audiobook": True,
        "audio_status": "AVAILABLE",
        "audiobook_release_gate": "APPROVED",
        "audio_qa_status": "QA_PASSED",
        "audiobook_provider": "kokoro",
        "audiobook_voice": "historical",
        "audiobook_assets": {
            "mp3": f"https://s3.us-west-004.backblazeb2.com/private/{slug}.mp3",
        },
        "audiobook_release_conveyor": {
            "schema_version": server.AUDIOBOOK_RELEASE_CONVEYOR_SCHEMA,
            "reader_release_approved": True,
            "audio_release_approved": True,
            "audio_public_release": "APPROVED",
            "audio_qa_status": "QA_PASSED",
            "audio_sha256": "70c94cc660fe15fdb4b5e3ef800643090d0eabd27b07523ffa5859b73e700f69",
            "voice": "historical",
        },
    }
    monkeypatch.setattr(server, "db", SimpleNamespace(books=ConveyorBooks(slug, release)))
    monkeypatch.setattr(server, "_redis_cache_get", no_cache)
    monkeypatch.setattr(server, "_redis_cache_set", no_cache_write)
    monkeypatch.setattr(server, "_reader_content_cache_generation_value", fixed_generation)

    manifest = asyncio.run(server._reader_book_manifest_doc(slug))

    assert manifest is None


def test_batch2_server_owned_audio_does_not_enter_static_home_listening_shelf():
    payload = build_home_curated_payload()
    listening_slugs = {
        row["slug"] for row in payload["shelves"]["approved_audiobooks"]
    }

    assert listening_slugs.isdisjoint(GUARDED_AUDIO_SLUGS)


def test_a_white_heron_is_prepared_but_not_live_and_audio_is_disabled():
    artifact_dir = ROOT / "data" / "controlled_publications" / "a-white-heron"
    public = catalog_truth.read_json_file(artifact_dir / "public_book.json")
    reader = catalog_truth.read_json_file(artifact_dir / "reader_manifest.json")
    source = catalog_truth.read_json_file(artifact_dir / "source_evidence.json")
    publication = catalog_truth.read_json_file(artifact_dir / "publication_manifest.json")
    approval = catalog_truth.read_json_file(artifact_dir / "approval_evidence.json")
    checksum = catalog_truth.read_json_file(artifact_dir / "checksum_manifest.json")
    historical_audio = catalog_truth.read_json_file(artifact_dir / "production_audio_evidence.json")

    assert public["publication_status"] == "READY_FOR_COMMERCIAL_CUTOVER"
    assert public["approved_to_publish"] is False
    assert public["is_published"] is False
    assert public["isPublic"] is False and public["isLive"] is False
    assert public["showInPublicLibrary"] is False
    assert public["formats"] == ["Ebook"]
    assert public["audio_enabled"] is False
    assert public["audiobook_enabled"] is False
    assert public["generate_audiobook"] is False
    assert approval["approved_to_publish"] is False
    assert approval["audio_public_release"] == "PUBLIC_AUDIO_RELEASE_NOT_APPROVED"
    assert approval["audiobook_enabled"] is False
    assert approval["historical_audio_approval"]["historical_only"] is True
    assert approval["historical_audio_approval"]["audio_public_release"] == "PUBLIC_AUDIO_RELEASE_APPROVED"
    assert reader["audio_enabled"] is False
    assert reader["audiobook_enabled"] is False
    assert source["territory"] == "IN"
    assert source["normalized_source_text_sha256"] == source["normalized_canonical_text_sha256"]
    assert source["source_edition"].startswith("The Best Stories of Sarah Orne Jewett")
    assert source["edition_variant_classification"].startswith("DOCUMENTED_EDITION_VARIANT")
    assert len(source["edition_variant_evidence"]) == 3
    assert publication["rights"]["status"] == "APPROVED"
    assert publication["reader_release"]["status"] == "READY_FOR_APPROVAL"
    assert publication["reader_release"]["exposed"] is False
    assert publication["audio_release"]["status"] == "NOT_REQUESTED"
    assert publication["audio_release"]["exposed"] is False
    assert validate_manifest(publication) == []
    for row in checksum["files"]:
        assert catalog_truth.file_sha256(artifact_dir / row["file"]) == row["sha256"]
    assert historical_audio["production_audio"]["full_get_status"] == 200
    assert historical_audio["browser"]["playback_advanced"] is True
