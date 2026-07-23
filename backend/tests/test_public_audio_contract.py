from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "public-audio-contract-test-secret")

from backend import catalog_truth
from scripts import catalog_truth_audit


ROOT = Path(__file__).resolve().parents[2]
APPROVED_AUDIO_SLUGS = tuple(sorted(catalog_truth.AUDIO_ENABLED_SLUGS))
HIDDEN_AUDIO_SLUGS = ("bn-066", "radharani")


class EmptyBooks:
    async def find_one(self, *_args, **_kwargs):
        return None


async def no_cache(*_args, **_kwargs):
    return None


@pytest.mark.parametrize("slug", APPROVED_AUDIO_SLUGS)
def test_public_projection_reports_only_release_approved_audio(slug):
    artifact = catalog_truth.load_controlled_artifact_book(slug)

    assert artifact is not None
    assert catalog_truth.can_expose_audio(artifact) is True

    projected = catalog_truth.public_book_projection(artifact)
    assert projected is not None
    assert projected["audio_enabled"] is True
    assert projected["audiobook_enabled"] is True
    assert projected["audio_url"] == f"/api/reader/book/{slug}/audiobook"
    assert projected["audio_status"] == "AVAILABLE"
    assert projected["audiobook_release_gate"] == "APPROVED"
    assert projected["audio_qa_status"] == "QA_PASSED"
    assert "audiobook_assets" not in projected
    assert "backblazeb2.com" not in str(projected)
    assert catalog_truth_audit.verify_live_detail_payload(
        f"/books/{slug}",
        projected,
        slug,
        audio_allowed=True,
    ) == []


@pytest.mark.parametrize("slug", HIDDEN_AUDIO_SLUGS)
def test_public_projection_keeps_hidden_audio_fail_closed(slug):
    artifact = catalog_truth.load_controlled_artifact_book(slug)

    assert artifact is not None
    artifact["audio_enabled"] = True
    artifact["audiobook_enabled"] = True
    artifact["audiobook_assets"] = {
        "mp3": f"https://s3.us-west-004.backblazeb2.com/earnalism-audiobooks/{slug}.mp3",
    }

    projected = catalog_truth.public_book_projection(artifact)
    assert projected is not None
    assert projected["audio_enabled"] is False
    assert projected["audiobook_enabled"] is False
    assert projected["audio_url"] == ""
    assert projected["audio_status"] == "NOT_AVAILABLE"
    assert projected["audiobook_release_gate"] == ""
    assert projected["audio_qa_status"] == ""
    assert "audiobook_assets" not in projected
    assert "backblazeb2.com" not in str(projected)
    assert catalog_truth_audit.verify_live_detail_payload(
        f"/books/{slug}",
        projected,
        slug,
    ) == []


@pytest.mark.parametrize("slug", APPROVED_AUDIO_SLUGS)
def test_checked_in_reader_manifest_flags_match_approved_audio_contract(slug):
    for relative_root in ("data/controlled_publications", "backend/data/controlled_publications"):
        artifact_dir = ROOT / relative_root / slug
        manifest_path = artifact_dir / "reader_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        checksum = json.loads((artifact_dir / "checksum_manifest.json").read_text(encoding="utf-8"))
        expected_hash = next(
            item["sha256"]
            for item in checksum["files"]
            if item["file"] == "reader_manifest.json"
        )

        assert manifest["audio_enabled"] is True
        assert manifest["audiobook_enabled"] is True
        assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == expected_hash
        assert catalog_truth.controlled_artifact_validation_issues(slug, str(artifact_dir)) == ()


def test_checked_in_manifest_flags_fail_closed_when_release_evidence_is_revoked(tmp_path):
    slug = "book-2b9853ec52"
    artifact_dir = tmp_path / slug
    shutil.copytree(ROOT / "backend/data/controlled_publications" / slug, artifact_dir)
    approval_path = artifact_dir / "approval_evidence.json"
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    approval["audio_public_release"] = "PUBLIC_AUDIO_RELEASE_NOT_APPROVED"
    approval["audiobook_enabled"] = False
    approval_path.write_text(
        json.dumps(approval, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    issues = catalog_truth.controlled_artifact_validation_issues(slug, str(artifact_dir))

    assert "public_book.json audio flags do not match controlled release approval." in issues
    assert "reader_manifest.json audio flags do not match controlled release approval." in issues


def test_server_accepts_approved_and_hidden_public_audio_contracts():
    from backend import server

    approved = catalog_truth.public_book_projection(
        catalog_truth.load_controlled_artifact_book("book-2b9853ec52")
    )
    hidden = catalog_truth.public_book_projection(
        catalog_truth.load_controlled_artifact_book("bn-066")
    )

    assert server._public_projection_is_live(approved) is True
    assert server._public_projection_is_live(hidden) is True

    dumped = server.PublicBookOut.model_validate(approved).model_dump()
    assert dumped["audio_enabled"] is True
    assert dumped["audiobook_enabled"] is True
    assert dumped["audiobook_release_gate"] == "APPROVED"
    assert dumped["audio_qa_status"] == "QA_PASSED"

    missing_approval = {**approved, "audiobook_release_gate": ""}
    assert server._public_projection_is_live(missing_approval) is False


def test_book_detail_and_reader_manifest_agree_for_live_bengali_audio(monkeypatch):
    from backend import server

    monkeypatch.setattr(server, "db", SimpleNamespace(books=EmptyBooks()))
    monkeypatch.setattr(server, "_public_cache_get", no_cache)
    monkeypatch.setattr(server, "_public_cache_set", no_cache)
    monkeypatch.setattr(server, "_redis_cache_get", no_cache)
    monkeypatch.setattr(server, "_redis_cache_set", no_cache)

    detail = asyncio.run(server.get_book("book-2b9853ec52"))
    manifest = asyncio.run(server._reader_book_manifest_doc("book-2b9853ec52"))

    assert detail["audio_enabled"] is True
    assert detail["audiobook_enabled"] is True
    assert detail["audio_url"] == "/api/reader/book/book-2b9853ec52/audiobook"
    assert detail["audio_status"] == "AVAILABLE"
    assert detail["audiobook_release_gate"] == "APPROVED"
    assert detail["audio_qa_status"] == "QA_PASSED"
    assert manifest is not None
    assert manifest["book"]["audio_enabled"] is True
    assert manifest["book"]["audiobook_enabled"] is True
    assert manifest["audio"]["enabled"] is True
    assert manifest["audio"]["release_gate"] == "APPROVED"
    assert manifest["audio"]["qa_status"] == "QA_PASSED"
    assert manifest["audio"]["url"] == detail["audio_url"]
