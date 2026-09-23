from __future__ import annotations

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


def test_hash_completeness_does_not_upgrade_source_comparison_or_release():
    report = audit(ROOT)

    for title in report["titles"]:
        assert title["checks"]["text_verified"] is False
        assert title["checks"]["reader_release_allowed"] is False
        assert "TEXT_VERIFIED" in title["blockers"]
        assert "RELEASE_ALLOWLISTED" in title["release_blockers"]


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
            "attribution_implemented": True,
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
