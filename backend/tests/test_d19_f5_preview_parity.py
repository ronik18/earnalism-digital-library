from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "preview-parity-test-secret")

from backend import catalog_truth, server
from scripts import catalog_truth_audit, rebuild_release_packs_from_history


ROOT = Path(__file__).resolve().parents[2]
PAID_ONLY_SLUGS = ("book-d19e96859f", "book-f5d593e1f4")
PACKET_ROOTS = (
    ROOT / "data" / "controlled_publications",
    ROOT / "backend" / "data" / "controlled_publications",
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_d19_f5_packets_have_no_full_text_preview_and_valid_checksums():
    for packet_root in PACKET_ROOTS:
        for slug in PAID_ONLY_SLUGS:
            packet = packet_root / slug
            public_book = read_json(packet / "public_book.json")
            reader_manifest = read_json(packet / "reader_manifest.json")
            chapter = read_json(packet / "chapters" / "chapter-001.json")
            checksum_manifest = read_json(packet / "checksum_manifest.json")

            assert reader_manifest["preview_chapter_ids"] == []
            assert all(item.get("is_preview") is False for item in public_book["chapters"])
            assert all(item.get("is_preview") is False for item in reader_manifest["chapters"])
            assert chapter["is_preview"] is False

            for entry in checksum_manifest["files"]:
                if entry["file"] == "checksum_manifest.json":
                    continue
                assert sha256(packet / entry["file"]) == entry["sha256"]


def test_paid_only_titles_keep_reader_access_without_preview_or_audio_exposure():
    for slug in PAID_ONLY_SLUGS:
        packet = ROOT / "data" / "controlled_publications" / slug
        book = {
            **read_json(packet / "public_book.json"),
            **read_json(packet / "source_evidence.json"),
        }

        assert catalog_truth.can_expose_reader(book) is True
        assert catalog_truth.explicit_preview_chapter_ids(book) == ()
        assert catalog_truth.can_expose_preview(book) is False
        assert catalog_truth.can_expose_audio(book) is False

        projected = catalog_truth.public_book_projection(book)
        assert projected is not None
        assert projected["publication_status"] == "LIVE_APPROVED"
        assert projected["reader_enabled"] is True
        assert projected["reader_url"] == f"/reader/{slug}"
        assert projected["preview_enabled"] is False
        assert projected["preview_url"] == ""
        assert projected["audio_enabled"] is False
        assert projected["audio_url"] == ""
        assert server._public_projection_is_live(projected) is True
        assert server._free_preview_chapter_ids(book) == set()
        assert catalog_truth_audit.verify_live_detail_payload(f"/books/{slug}", projected, slug) == []
        assert catalog_truth_audit.verify_live_manifest_payload(
            f"/reader/book/{slug}/manifest",
            {
                "book": projected,
                "chapters": projected["chapters"],
                "audio": {"enabled": False, "assets": {}, "url": ""},
            },
            slug,
        ) == []


def test_dracula_keeps_its_explicit_preview_behavior():
    book = read_json(ROOT / "data" / "controlled_publications" / "dracula" / "public_book.json")
    projected = catalog_truth.public_book_projection(book)

    assert catalog_truth.explicit_preview_chapter_ids(book) == ("chapter-001",)
    assert catalog_truth.can_expose_reader(book) is True
    assert catalog_truth.can_expose_preview(book) is True
    assert projected is not None
    assert projected["reader_enabled"] is True
    assert projected["preview_enabled"] is True
    assert projected["preview_url"] == "/reader/dracula"
    assert server._free_preview_chapter_ids(book) == {"chapter-001"}


def test_history_rebuild_defaults_closed_and_honors_only_explicit_preview_evidence():
    chapter = {"id": "source-chapter", "title": "Full Text"}
    generated_id = "chapter-001"

    assert rebuild_release_packs_from_history.chapter_is_explicit_preview({}, chapter, generated_id) is False
    assert rebuild_release_packs_from_history.chapter_is_explicit_preview(
        {"preview_enabled": True}, chapter, generated_id
    ) is False
    assert rebuild_release_packs_from_history.chapter_is_explicit_preview(
        {}, {**chapter, "is_preview": True}, generated_id
    ) is True
    assert rebuild_release_packs_from_history.chapter_is_explicit_preview(
        {"preview_chapter_ids": [generated_id]}, chapter, generated_id
    ) is True
    assert rebuild_release_packs_from_history.chapter_is_explicit_preview(
        {"preview_chapter_ids": [chapter["id"]]}, chapter, generated_id
    ) is True


def test_catalog_audit_uses_chapter_evidence_instead_of_stale_preview_claims():
    payload = {
        "slug": PAID_ONLY_SLUGS[0],
        "reader_enabled": True,
        "reader_url": f"/reader/{PAID_ONLY_SLUGS[0]}",
        "preview_enabled": True,
        "preview_url": f"/reader/{PAID_ONLY_SLUGS[0]}",
        "chapters": [{"id": "chapter-001", "is_preview": False}],
    }

    assert catalog_truth_audit.api_preview_enabled(payload) is False
    issues = catalog_truth_audit.verify_live_detail_payload(
        f"/books/{PAID_ONLY_SLUGS[0]}",
        {
            **payload,
            "publication_status": "LIVE_APPROVED",
            "launch_status": "LIVE_APPROVED",
            "audio_enabled": False,
            "audiobook_enabled": False,
            "public_route": f"/book/{PAID_ONLY_SLUGS[0]}",
            "audio_url": "",
            "audio_status": "NOT_AVAILABLE",
            "public_json_ld_enabled": True,
            "source_note": "Source verified.",
            "rights_note": "Rights verified.",
        },
        PAID_ONLY_SLUGS[0],
    )
    assert any("preview_enabled" in issue for issue in issues)
    assert any("preview_url" in issue for issue in issues)


def test_book_summary_projection_carries_explicit_preview_metadata():
    assert server.BOOK_SUMMARY_PROJECTION["chapters.id"] == 1
    assert server.BOOK_SUMMARY_PROJECTION["chapters.is_preview"] == 1
