from __future__ import annotations

from pathlib import Path

import pytest

from backend import catalog_truth


ROOT = Path(__file__).resolve().parents[2]
GUARDED_AUDIO_SLUGS = ("a-white-heron", "the-selfish-giant")


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
def test_batch2_readers_are_live_while_audio_remains_server_gated(slug: str):
    artifact_dir = ROOT / "backend" / "data" / "controlled_publications" / slug
    assert catalog_truth.controlled_artifact_validation_issues(slug, str(artifact_dir)) == ()

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
