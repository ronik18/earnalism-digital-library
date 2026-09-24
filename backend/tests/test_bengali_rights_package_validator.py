from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import shutil
from pathlib import Path

from scripts.bengali_rights_package_validator import audit, evaluate_title
from backend import catalog_truth


ROOT = Path(__file__).resolve().parents[2]


def test_bankim_cohort_is_audited_hash_bound_and_remains_held():
    report = audit(ROOT)

    assert report["status"] == "PASS"
    assert len(report["titles"]) == 6
    for title in report["titles"]:
        assert title["checks"]["rights_packet_present"] is True
        assert title["checks"]["canonical_hash_matches"] is True
        assert title["checks"]["source_provenance_present"] is True
        assert title["checks"]["license_obligations_satisfied"] is False
        assert title["checks"]["package_held"] is True
        assert title["checks"]["backend_mirror_held"] is True
        assert title["checks"]["package_checksums_match"] is True
        assert title["checks"]["backend_mirror_checksums_match"] is True
        assert title["checks"]["reader_release_allowed"] is False
        assert title["status"] == "HOLD"
        assert title["slug"] not in catalog_truth.CONTROLLED_LIVE_BOOK_SLUGS
        assert (
            catalog_truth.controlled_artifact_status(title["slug"])["available"]
            is False
        )
        assert catalog_truth.load_controlled_artifact_book(title["slug"]) is None


def test_bankim_cohort_has_no_stale_public_audio_metadata_or_live_admission():
    packet = json.loads(
        (ROOT / "data/title_rights_evidence/bengali-bankim-cohort-1.json").read_text(
            encoding="utf-8"
        )
    )
    for title in packet["titles"]:
        slug = title["slug"]
        assert slug not in catalog_truth.CONTROLLED_LIVE_BOOK_SLUGS
        for package_root in (
            ROOT / "data/controlled_publications" / slug,
            ROOT / "backend/data/controlled_publications" / slug,
        ):
            if not package_root.exists():
                continue
            book = json.loads(
                (package_root / "public_book.json").read_text(encoding="utf-8")
            )
            assert book.get("audio_enabled") is False
            assert book.get("audiobook_enabled") is False
            assert book.get("generate_audiobook") is False
            assert book.get("audiobook_provider", "") == ""
            assert book.get("audio_url", "") == ""
            assert book.get("audiobook_assets", {}) == {}
            assert book.get("audiobook", {}) == {}
            assert book.get("audiobook_package", {}) == {}
            assert book.get("audiobook_release_conveyor", {}) == {}
            checksum = json.loads(
                (package_root / "checksum_manifest.json").read_text(encoding="utf-8")
            )
            for entry in checksum["files"]:
                target = package_root / entry["file"]
                assert target.exists()
                assert hashlib.sha256(target.read_bytes()).hexdigest() == entry["sha256"]


def test_indira_source_verification_does_not_upgrade_any_title_to_release():
    report = audit(ROOT)

    for title in report["titles"]:
        assert title["checks"]["reader_release_allowed"] is False
        assert "RELEASE_ALLOWLISTED" in title["release_blockers"]
        if title["slug"] == "bn-060":
            assert title["checks"]["text_verified"] is True
            assert "TEXT_VERIFIED" not in title["blockers"]
        else:
            assert title["checks"]["text_verified"] is False
            assert "TEXT_VERIFIED" in title["blockers"]


def test_indira_chapter_six_restores_only_facsimile_confirmed_continuation():
    canonical_path = (
        ROOT
        / "content/books/bn-060/chapters/006-chapter-6-ষষ্ঠ-পরিচ্ছেদ.json"
    )
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    controlled = json.loads(
        (ROOT / "data/controlled_publications/bn-060/chapters/chapter-006.json")
        .read_text(encoding="utf-8")
    )
    rights = json.loads(
        (ROOT / "data/title_rights_evidence/bengali-bankim-cohort-1.json")
        .read_text(encoding="utf-8")
    )
    indira = next(row for row in rights["titles"] if row["slug"] == "bn-060")
    source = json.loads(
        (ROOT / "data/controlled_publications/bn-060/source_evidence.json")
        .read_text(encoding="utf-8")
    )

    assert "তিনি বাহির হইতে কাতরোক্তি করিতে লাগিলেন" in canonical["content"]
    assert "তিনি অষ্টাহ পরীক্ষা স্বীকার করিলেন।" in canonical["content"]
    assert controlled["content"] == canonical["content"]
    assert hashlib.sha256(canonical["content"].encode("utf-8")).hexdigest() == (
        canonical["sanitizedSha256"]
    )
    assert indira["text_integrity_status"] == "TEXT_VERIFIED"
    assert indira["follow_up_source_comparison"]["classification"] == (
        "CONFIRMED_SOURCE_OMISSION_RESTORED"
    )
    assert source["chapter_006_source_correction"]["status"] == (
        "PASS_SCAN_CONFIRMED_OMISSION_RESTORED"
    )
    assert indira["publication_status"] == "HOLD_NOT_RELEASED"


def test_indira_chapter_eight_source_match_does_not_clear_unchecked_chapters():
    rights = json.loads(
        (ROOT / "data/title_rights_evidence/bengali-bankim-cohort-1.json")
        .read_text(encoding="utf-8")
    )
    indira = next(row for row in rights["titles"] if row["slug"] == "bn-060")
    chapter = json.loads(
        (ROOT / "data/controlled_publications/bn-060/chapters/chapter-008.json")
        .read_text(encoding="utf-8")
    )

    comparison = indira["chapter_008_source_comparison"]
    assert comparison["source_child_page_revision"] == 1910620
    assert comparison["difference_classification"] == "SOURCE_FURNITURE_ONLY"
    assert comparison["canonical_chapter_content_sha256"] == hashlib.sha256(
        chapter["content"].encode("utf-8")
    ).hexdigest()
    assert indira["text_integrity_status"] == "TEXT_VERIFIED"
    assert indira["publication_status"] == "HOLD_NOT_RELEASED"


def test_indira_complete_source_comparison_binds_every_canonical_chapter():
    rights = json.loads(
        (ROOT / "data/title_rights_evidence/bengali-bankim-cohort-1.json")
        .read_text(encoding="utf-8")
    )
    indira = next(row for row in rights["titles"] if row["slug"] == "bn-060")
    comparison = indira["complete_source_comparison"]

    assert comparison["status"] == "TEXT_VERIFIED"
    assert len(comparison["chapters"]) == 8
    assert [row["chapter"] for row in comparison["chapters"]] == list(range(1, 9))
    assert [row["source_child_page_revision"] for row in comparison["chapters"]] == [
        1910625,
        1910623,
        1910622,
        1910621,
        1910624,
        1910626,
        1910627,
        1910620,
    ]
    for row in comparison["chapters"]:
        chapter = json.loads(
            next(
                (ROOT / "content/books/bn-060/chapters").glob(
                    f"{row['chapter']:03d}-*.json"
                )
            ).read_text(encoding="utf-8")
        )
        assert hashlib.sha256(chapter["content"].encode("utf-8")).hexdigest() == (
            row["canonical_chapter_sha256"]
        )
    assert comparison["canonical_text_sha256"] == indira["canonical_text_sha256"]
    assert comparison["publication_status"] == "HOLD_NOT_RELEASED"
    assert comparison["release_allowlist_changed"] is False


def test_muchiram_source_scope_proves_the_two_chapter_package_is_incomplete():
    rights = json.loads(
        (ROOT / "data/title_rights_evidence/bengali-bankim-cohort-1.json")
        .read_text(encoding="utf-8")
    )
    muchiram = next(
        row
        for row in rights["titles"]
        if row["slug"] == "muchiram-gurer-jibanchorit"
    )
    review = muchiram["source_completeness_review"]

    assert review["source_chapter_count"] == 14
    assert review["earnalism_canonical_chapter_count"] == 2
    assert review["classification"] == "SOURCE_INCOMPLETE_AT_LEAST_12_CHAPTERS_ABSENT"
    assert muchiram["text_integrity_status"] == (
        "TEXT_REVIEW_REQUIRED_SOURCE_HAS_14_CHAPTERS_CANONICAL_HAS_2"
    )
    assert muchiram["publication_status"] == "HOLD_NOT_RELEASED"


def test_bankim_cohort_cover_records_bind_owner_provenance_to_active_package_asset():
    rights = json.loads(
        (ROOT / "data/title_rights_evidence/bengali-bankim-cohort-1.json")
        .read_text(encoding="utf-8")
    )
    for title in rights["titles"]:
        package = json.loads(
            (
                ROOT
                / "data/controlled_publications"
                / title["slug"]
                / "public_book.json"
            ).read_text(encoding="utf-8")
        )
        assert title["external_protected_cover_elements"] is False
        assert title["cover_status"].startswith("FIRST_PARTY_COVER_PROVENANCE_CONFIRMED")
        assert title["cover_asset"] == package["cover_image_url"]


def test_evidence_ready_title_stays_unreleased_until_explicit_release_controls(
    tmp_path,
):
    packet = json.loads(
        (ROOT / "data/title_rights_evidence/bengali-bankim-cohort-1.json").read_text(
            encoding="utf-8"
        )
    )
    title = packet["titles"][0]
    title.update(
        {
            "license_obligations": {
                "attribution": True,
                "source_and_license_links": True,
                "changes_disclosed": True,
                "sharealike_treatment": True,
                "no_incompatible_additional_restrictions": True,
            },
            "external_protected_cover_elements": False,
            "text_integrity_status": "TEXT_VERIFIED",
            "territory": "IN",
        }
    )
    slug = title["slug"]
    for source in (
        ROOT / "data/controlled_publications" / slug,
        ROOT / "backend/data/controlled_publications" / slug,
    ):
        destination = tmp_path / source.relative_to(ROOT)
        shutil.copytree(source, destination)
        (destination / "publication_manifest.json").write_text("{}", encoding="utf-8")

    launch = json.loads(
        (ROOT / "backend/data/controlled_launch.json").read_text(encoding="utf-8")
    )
    result = evaluate_title(tmp_path, title, launch, "IN")

    assert result["status"] == "READY_FOR_COMMERCIAL_RELEASE"
    assert result["checks"]["evidence_complete_for_commercial_release"] is True
    assert result["checks"]["package_held"] is True
    assert result["checks"]["reader_release_allowed"] is False
    assert "RELEASE_ALLOWLISTED" in result["release_blockers"]
    assert "HASH_BOUND_RELEASE_DECISION_ACCEPTED" in result["release_blockers"]


def test_every_cc_by_sa_obligation_must_be_explicitly_satisfied(tmp_path):
    packet = json.loads(
        (ROOT / "data/title_rights_evidence/bengali-bankim-cohort-1.json").read_text(
            encoding="utf-8"
        )
    )
    title = packet["titles"][0]
    title.update(
        {
            "license_obligations": {
                "attribution": True,
                "source_and_license_links": True,
                "changes_disclosed": True,
                "sharealike_treatment": True,
                "no_incompatible_additional_restrictions": True,
            },
            "external_protected_cover_elements": False,
            "text_integrity_status": "TEXT_VERIFIED",
        }
    )
    slug = title["slug"]
    for source in (
        ROOT / "data/controlled_publications" / slug,
        ROOT / "backend/data/controlled_publications" / slug,
    ):
        destination = tmp_path / source.relative_to(ROOT)
        shutil.copytree(source, destination)
        (destination / "publication_manifest.json").write_text("{}", encoding="utf-8")

    launch = json.loads(
        (ROOT / "backend/data/controlled_launch.json").read_text(encoding="utf-8")
    )
    ready = evaluate_title(tmp_path, title, launch, "IN")
    assert ready["checks"]["license_obligations_satisfied"] is True

    for obligation in title["license_obligations"]:
        incomplete = deepcopy(title)
        incomplete["license_obligations"][obligation] = False
        result = evaluate_title(tmp_path, incomplete, launch, "IN")
        assert result["checks"]["license_obligations_satisfied"] is False
        assert result["status"] == "HOLD"
        assert "LICENSE_OBLIGATIONS_SATISFIED" in result["blockers"]
