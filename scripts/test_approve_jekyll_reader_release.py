import hashlib
import json
from pathlib import Path

import approve_jekyll_reader_release as release


def decoded(replacements: dict[Path, bytes], relative: str) -> dict:
    return json.loads(replacements[release.ROOT / relative])


def test_owner_fingerprint_recomputes_from_exact_nine_field_binding():
    payload = json.dumps(
        release.FINGERPRINT_BINDING,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert hashlib.sha256(payload).hexdigest() == release.APPROVED_FINGERPRINT


def test_build_promotes_only_corrected_canonical_reader():
    replacements, evidence = release.build("2026-08-16T06:00:00Z")
    public = decoded(
        replacements, "data/controlled_publications/jekyll-and-hyde/public_book.json"
    )
    content = decoded(replacements, "content/books/jekyll-and-hyde/book.json")
    approval = decoded(
        replacements, "data/controlled_publications/jekyll-and-hyde/approval_evidence.json"
    )
    reader = decoded(
        replacements, "data/controlled_publications/jekyll-and-hyde/reader_manifest.json"
    )
    receipt = decoded(
        replacements,
        "data/controlled_publications/jekyll-and-hyde/reader_release_approval.json",
    )

    assert evidence["reader_gate_fingerprint"] == release.APPROVED_FINGERPRINT
    assert public["publication_status"] == "LIVE_APPROVED"
    assert public["readerStatus"] == "reader_ready"
    assert public["isPublic"] is True
    assert public["isLive"] is True
    assert public["allowPublicReading"] is True
    assert content["publicationStatus"] == "live"
    assert content["isPublic"] is True
    assert approval["reader_public_release"] == "READER_ONLY_LIVE_APPROVED"
    assert reader["reader_release_status"] == "READER_ONLY_LIVE_APPROVED"
    assert reader["chapter_count"] == 10
    assert receipt["approved_parent_manifest_sha256"] == release.PARENT_MANIFEST_SHA256
    assert receipt["approved_reader_gate_fingerprint"] == release.APPROVED_FINGERPRINT

    for book in (public, content, reader):
        assert book.get("audio_enabled") is False
        assert book.get("audiobook_enabled") is False
    assert public.get("audio_url") in (None, "")
    assert public.get("audiobook_url") in (None, "")


def test_build_updates_launch_and_promotion_without_audio_or_alias():
    replacements, _ = release.build("2026-08-16T06:00:00Z")
    for relative in ("data/controlled_launch.json", "backend/data/controlled_launch.json"):
        launch = decoded(replacements, relative)
        assert release.SLUG in launch["live_approved_slugs"]
        assert release.SLUG not in launch["audio_enabled_slugs"]
        assert release.ALIAS_SLUG not in launch["live_approved_slugs"]
        assert release.ALIAS_SLUG not in launch["audio_enabled_slugs"]

    promotion = decoded(replacements, "content/books/batch-1-promotion-report.json")
    assert release.SLUG in promotion["promotedLiveSlugs"]
    assert release.SLUG in promotion["approvedReleaseAllowlist"]
    assert release.SLUG not in promotion["heldSlugs"]
    row = next(row for row in promotion["books"] if row["slug"] == release.SLUG)
    assert row["chapterCount"] == 10
    assert row["routeStatus"] == "READY"
    assert row["blockers"] == []
    assert row["decision"] == "PROMOTED_LIVE_READER_ONLY"


def test_build_preserves_controlled_chapters_byte_for_byte_and_mirrors_receipt():
    replacements, _ = release.build("2026-08-16T06:00:00Z")
    for index in range(1, 11):
        relative = f"chapters/chapter-{index:03d}.json"
        source = release.CONTROLLED_ROOT / release.SLUG / relative
        assert replacements[source] == source.read_bytes()
        assert replacements[release.BACKEND_ROOT / release.SLUG / relative] == source.read_bytes()

    root_receipt = replacements[
        release.CONTROLLED_ROOT / release.SLUG / "reader_release_approval.json"
    ]
    backend_receipt = replacements[
        release.BACKEND_ROOT / release.SLUG / "reader_release_approval.json"
    ]
    assert root_receipt == backend_receipt


def test_stale_alias_remains_inert_in_checked_in_state():
    alias = release.read_json(
        release.CONTROLLED_ROOT / release.ALIAS_SLUG / "public_book.json"
    )
    assert alias["chapters"] == []
    assert alias["isPublic"] is False
    assert alias["isLive"] is False
    assert alias["allowPublicReading"] is False
    assert alias["audio_enabled"] is False
    assert alias["audiobook_enabled"] is False
    assert alias["canonical_slug"] == release.SLUG
