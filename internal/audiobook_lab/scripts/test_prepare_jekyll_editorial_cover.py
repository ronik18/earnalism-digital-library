from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).with_name("prepare_jekyll_editorial_cover.py")
SPEC = importlib.util.spec_from_file_location("prepare_jekyll_editorial_cover", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


GENERATED_AT = "2026-07-30T07:45:00Z"


def prepare(tmp_path: Path, name: str = "candidate") -> dict:
    return MODULE.prepare_package(
        tmp_path / name,
        MODULE.DEFAULT_FRONT_SOURCE,
        MODULE.DEFAULT_BACK_SOURCE,
        MODULE.DEFAULT_RIGHTS,
        generated_at=GENERATED_AT,
    )


def test_private_candidate_is_deterministic_and_truth_bound(tmp_path: Path) -> None:
    first = prepare(tmp_path, "first")
    second = prepare(tmp_path, "second")

    assert first["status"] == "PRIVATE_CANDIDATE_EDITORIAL_REVIEW_REQUIRED"
    assert first["title"] == "The Strange Case of Dr. Jekyll and Mr. Hyde"
    assert first["author"] == "Robert Louis Stevenson"
    assert first["canonical_back_copy"].startswith("A clean Earnalism reader edition")
    assert first["source_art"]["front"]["sha256"] == MODULE.FRONT_SOURCE_SHA256
    assert first["source_art"]["back"]["sha256"] == MODULE.BACK_SOURCE_SHA256
    assert first["front"]["sha256"] == second["front"]["sha256"]
    assert first["back"]["sha256"] == second["back"]["sha256"]
    assert first["front"]["thumbnail"]["sha256"] == second["front"]["thumbnail"]["sha256"]
    assert first["front"]["feature"]["sha256"] == second["front"]["feature"]["sha256"]
    assert first["back"]["thumbnail"]["sha256"] == second["back"]["thumbnail"]["sha256"]
    assert first["back"]["feature"]["sha256"] == second["back"]["feature"]["sha256"]


def test_release_and_publication_boundaries_fail_closed(tmp_path: Path) -> None:
    manifest = prepare(tmp_path)
    assert manifest["review"] == {
        "manual_visual_review_status": "PENDING",
        "owner_editorial_review_required": True,
        "admin_upload_status": "NOT_UPLOADED",
        "canonical_promotion_status": "NOT_PROMOTED",
    }
    assert manifest["constraints"] == {
        "private_only": True,
        "public_catalog_mutated": False,
        "reader_state_mutated": False,
        "audiobook_release_state_mutated": False,
        "ai_generated_imagery": False,
        "placeholder_art": False,
        "public_upload_authorized": False,
        "canonical_promotion_authorized": False,
    }


def test_geometry_small_card_and_performance_budgets_pass(tmp_path: Path) -> None:
    prepare(tmp_path)
    validation = MODULE.read_json(tmp_path / "candidate" / "visual_validation.json")

    assert validation["status"] == "AUTOMATED_PASS_MANUAL_EDITORIAL_REVIEW_PENDING"
    assert validation["geometry_errors"] == []
    assert validation["checks"]["text_box_overlap_count"] == 0
    assert validation["checks"]["text_inside_safe_margins"] is True
    assert validation["checks"]["text_inside_content_panels"] is True
    assert validation["checks"]["small_card_title_legibility_floor"] is True
    assert validation["checks"]["small_card_author_legibility_floor"] is True
    assert validation["checks"]["thumbnail_derivatives_under_80_kib"] is True
    assert validation["checks"]["feature_derivatives_under_180_kib"] is True

    for name in ("front_thumbnail", "back_thumbnail"):
        derivative = validation["derivative_validations"][name]
        assert derivative["bytes"] <= MODULE.THUMBNAIL_BUDGET_BYTES
        assert [derivative["width"], derivative["height"]] == list(
            MODULE.THUMBNAIL_SIZE
        )
    for name in ("front_feature", "back_feature"):
        derivative = validation["derivative_validations"][name]
        assert derivative["bytes"] <= MODULE.FEATURE_BUDGET_BYTES
        assert [derivative["width"], derivative["height"]] == list(
            MODULE.FEATURE_SIZE
        )


def test_exact_source_hashes_and_rights_caveat_are_required(tmp_path: Path) -> None:
    rights = MODULE.read_json(MODULE.DEFAULT_RIGHTS)
    assert rights["sources"]["front"]["sha256"] == MODULE.FRONT_SOURCE_SHA256
    assert rights["sources"]["back"]["sha256"] == MODULE.BACK_SOURCE_SHA256
    assert rights["rights"]["global_unrestricted_assertion"] is False
    assert rights["review"]["canonical_promotion_authorized"] is False
    assert rights["review"]["public_upload_authorized"] is False

    tampered = tmp_path / "tampered.jpg"
    tampered.write_bytes(MODULE.DEFAULT_FRONT_SOURCE.read_bytes() + b"tampered")
    with pytest.raises(MODULE.CoverCandidateError, match="SHA-256"):
        MODULE.prepare_package(
            tmp_path / "tampered-package",
            tampered,
            MODULE.DEFAULT_BACK_SOURCE,
            MODULE.DEFAULT_RIGHTS,
            generated_at=GENERATED_AT,
        )


def test_controlled_catalog_remains_byte_identical(tmp_path: Path) -> None:
    before = {
        path: MODULE.sha256_file(path)
        for path in MODULE.CATALOG_PATHS
    }
    manifest = prepare(tmp_path)
    after = {
        path: MODULE.sha256_file(path)
        for path in MODULE.CATALOG_PATHS
    }

    assert before == after
    assert len(set(before.values())) == 1
    assert manifest["catalog_hashes"] == {
        MODULE.repo_relative(path): digest
        for path, digest in after.items()
    }


def test_committed_manual_review_is_bound_to_exact_outputs() -> None:
    manifest = MODULE.read_json(MODULE.DEFAULT_PACKAGE / "candidate_manifest.json")
    review = MODULE.read_json(MODULE.DEFAULT_PACKAGE / "manual_visual_review.json")

    assert manifest["status"] == "PRIVATE_CANDIDATE_EDITORIAL_REVIEW_REQUIRED"
    assert (
        manifest["review"]["manual_visual_review_status"]
        == "CODEX_VISUAL_INSPECTION_PASS_OWNER_EDITORIAL_REVIEW_PENDING"
    )
    assert review["decision"]["private_candidate_visual_gate"] == "PASS"
    assert review["decision"]["owner_editorial_approval_required"] is True
    assert review["decision"]["admin_upload_authorized"] is False
    assert review["decision"]["canonical_promotion_authorized"] is False
    assert review["decision"]["public_exposure_authorized"] is False
    assert (
        review["artifacts"]["front_master"]["sha256"]
        == manifest["front"]["sha256"]
    )
    assert (
        review["artifacts"]["back_master"]["sha256"]
        == manifest["back"]["sha256"]
    )
    assert (
        review["artifacts"]["front_thumbnail"]["sha256"]
        == manifest["front"]["thumbnail"]["sha256"]
    )
    assert (
        review["artifacts"]["back_thumbnail"]["sha256"]
        == manifest["back"]["thumbnail"]["sha256"]
    )
