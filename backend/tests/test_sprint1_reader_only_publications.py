from __future__ import annotations

import json
from pathlib import Path

from backend import catalog_truth


ROOT = Path(__file__).resolve().parents[2]
APPROVED_PUBLIC_AUDIO_SLUGS = {
    "book-2b9853ec52",
    "a-ghost-story",
    "sredni-vashtar",
    "the-open-window",
}
READER_ONLY_SLUGS = (
    "radharani",
    "book-d19e96859f",
    "book-edfcf810c5",
    "the-time-machine",
    "the-call-of-the-wild",
    "white-fang",
    "pride-and-prejudice",
    "the-secret-garden",
    "the-gift-of-the-magi",
    "the-tell-tale-heart",
    "dsires-baby",
    "the-cop-and-the-anthem",
    "the-last-leaf",
    "the-masque-of-the-red-death",
    "the-yellow-wallpaper",
    "the-monkeys-paw",
    "the-necklace",
)
REQUIRED_FILES = {
    "approval_evidence.json",
    "checksum_manifest.json",
    "public_book.json",
    "reader_manifest.json",
    "source_evidence.json",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_reader_only_publications_are_live_without_widening_audio_allowlist():
    for launch_path in (ROOT / "data/controlled_launch.json", ROOT / "backend/data/controlled_launch.json"):
        launch = read_json(launch_path)
        assert set(launch["audio_enabled_slugs"]) == APPROVED_PUBLIC_AUDIO_SLUGS
        assert set(READER_ONLY_SLUGS).issubset(launch["live_approved_slugs"])


def test_reader_only_publication_packets_are_packaged_and_audio_hidden():
    for slug in READER_ONLY_SLUGS:
        for relative_root in ("data/controlled_publications", "backend/data/controlled_publications"):
            artifact_dir = ROOT / relative_root / slug
            assert REQUIRED_FILES.issubset(path.name for path in artifact_dir.iterdir() if path.is_file())

            book = read_json(artifact_dir / "public_book.json")
            manifest = read_json(artifact_dir / "reader_manifest.json")
            approval = read_json(artifact_dir / "approval_evidence.json")

            assert book["slug"] == slug
            assert book["is_published"] is True
            assert book["isPublic"] is True
            assert book["isLive"] is True
            assert book["audio_enabled"] is False
            assert book["audiobook_enabled"] is False
            assert book["generate_audiobook"] is False
            assert book["audiobook_assets"] == {}
            assert book["audiobook"] == {}
            assert book["audiobook_provider"] == ""
            assert book["audiobook_voice"] == ""
            assert manifest["audio_enabled"] is False
            assert manifest["audiobook_enabled"] is False
            assert approval["audio_public_release"] == "PUBLIC_AUDIO_RELEASE_NOT_APPROVED"
            assert approval["audiobook_enabled"] is False
            assert catalog_truth.controlled_artifact_validation_issues(slug, str(artifact_dir)) == ()


def test_reader_only_artifacts_enable_reader_but_never_audio():
    for slug in READER_ONLY_SLUGS:
        artifact_dir = ROOT / "backend/data/controlled_publications" / slug
        book = catalog_truth.load_controlled_artifact_book(slug, include_content=False, artifact_dir=artifact_dir)

        assert book is not None
        assert catalog_truth.can_expose_reader(book) is True
        assert catalog_truth.can_expose_audio(book) is False

        projection = catalog_truth.public_book_projection(book)
        assert projection["reader_enabled"] is True
        assert projection["audio_enabled"] is False
        assert projection["audiobook_enabled"] is False
        assert projection["audio_url"] == ""
        assert "audiobook_assets" not in projection


def test_root_and_railway_reader_content_is_byte_identical():
    for slug in READER_ONLY_SLUGS:
        root_dir = ROOT / "data/controlled_publications" / slug
        backend_dir = ROOT / "backend/data/controlled_publications" / slug
        shared_files = {
            Path("approval_evidence.json"),
            Path("public_book.json"),
            Path("reader_manifest.json"),
            Path("source_evidence.json"),
            *(
                path.relative_to(root_dir)
                for path in (root_dir / "chapters").glob("*.json")
            ),
        }

        for relative in shared_files:
            assert (root_dir / relative).read_bytes() == (backend_dir / relative).read_bytes()
