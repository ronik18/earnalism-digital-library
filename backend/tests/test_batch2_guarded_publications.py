from __future__ import annotations

import asyncio
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "batch2-live-audio-test-secret")

from backend import catalog_truth, server
from backend.home_curation import build_home_curated_payload


ROOT = Path(__file__).resolve().parents[2]
GUARDED_AUDIO_SLUGS = ("a-white-heron", "the-selfish-giant")


class ConveyorBooks:
    def __init__(self, slug: str, release: dict):
        self.slug = slug
        self.release = release

    async def find_one(self, query, _projection=None):
        return self.release if query.get("slug") == self.slug else None


async def no_cache(*_args, **_kwargs):
    return None


async def no_cache_write(*_args, **_kwargs):
    return None


async def fixed_generation():
    return 1


@pytest.mark.parametrize("slug", GUARDED_AUDIO_SLUGS)
def test_batch2_packets_are_packaged_for_railway_and_byte_identical(slug: str):
    root_dir = ROOT / "data" / "controlled_publications" / slug
    backend_dir = ROOT / "backend" / "data" / "controlled_publications" / slug

    root_files = sorted(path.relative_to(root_dir) for path in root_dir.rglob("*") if path.is_file())
    backend_files = sorted(path.relative_to(backend_dir) for path in backend_dir.rglob("*") if path.is_file())

    assert backend_files == root_files
    for relative_path in root_files:
        assert (backend_dir / relative_path).read_bytes() == (root_dir / relative_path).read_bytes()


@pytest.mark.parametrize("slug", GUARDED_AUDIO_SLUGS)
def test_batch2_records_live_conveyor_audio_without_broadening_discovery(slug: str):
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

    assert book is not None
    assert catalog_truth.can_expose_reader(book) is True
    assert catalog_truth.can_expose_audio(book) is False

    projection = catalog_truth.public_book_projection(book)
    assert projection is not None
    assert projection["reader_enabled"] is True
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
    assert publication["audio_release"]["delivery_mode"] == "SERVER_OWNED_CONVEYOR"
    assert publication["audio_release"]["public_endpoint"] == f"/api/reader/book/{slug}/audiobook"
    assert publication["audio_release"]["discovery_exposed"] is False


@pytest.mark.parametrize(
    ("slug", "voice", "audio_sha256"),
    (
        ("the-selfish-giant", "bm_george", "824944d0c068b4f4f45cb750e018918b2af55c5e043cd29417ce2a756e9a4c67"),
        ("a-white-heron", "hf_alpha", "70c94cc660fe15fdb4b5e3ef800643090d0eabd27b07523ffa5859b73e700f69"),
    ),
)
def test_batch2_reader_manifest_merges_exact_database_conveyor_without_catalog_broadening(
    monkeypatch, slug: str, voice: str, audio_sha256: str
):
    release = {
        "slug": slug,
        "audio_enabled": True,
        "audiobook_enabled": True,
        "generate_audiobook": True,
        "audio_status": "AVAILABLE",
        "audiobook_release_gate": "APPROVED",
        "audio_qa_status": "QA_PASSED",
        "audiobook_provider": "kokoro",
        "audiobook_voice": voice,
        "audiobook_assets": {
            "mp3": f"https://s3.us-west-004.backblazeb2.com/private/{slug}.mp3",
        },
        "audiobook_release_conveyor": {
            "schema_version": server.AUDIOBOOK_RELEASE_CONVEYOR_SCHEMA,
            "reader_release_approved": True,
            "audio_release_approved": True,
            "audio_public_release": "APPROVED",
            "audio_qa_status": "QA_PASSED",
            "audio_sha256": audio_sha256,
            "voice": voice,
        },
    }
    monkeypatch.setattr(server, "db", SimpleNamespace(books=ConveyorBooks(slug, release)))
    monkeypatch.setattr(server, "_redis_cache_get", no_cache)
    monkeypatch.setattr(server, "_redis_cache_set", no_cache_write)
    monkeypatch.setattr(server, "_reader_content_cache_generation_value", fixed_generation)

    manifest = asyncio.run(server._reader_book_manifest_doc(slug))

    assert manifest is not None
    assert manifest["book"]["audio_enabled"] is True
    assert manifest["book"]["audiobook_enabled"] is True
    assert manifest["book"]["audio_url"] == f"/api/reader/book/{slug}/audiobook"
    assert manifest["audio"]["enabled"] is True
    assert manifest["audio"]["voice"] == voice
    assert manifest["audio"]["assets"]["mp3"] == f"/api/reader/book/{slug}/audiobook"


def test_batch2_server_owned_audio_does_not_enter_static_home_listening_shelf():
    payload = build_home_curated_payload()
    listening_slugs = {
        row["slug"] for row in payload["shelves"]["approved_audiobooks"]
    }

    assert listening_slugs.isdisjoint(GUARDED_AUDIO_SLUGS)
