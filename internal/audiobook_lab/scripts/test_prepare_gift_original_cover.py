from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("prepare_gift_original_cover.py")
SPEC = importlib.util.spec_from_file_location("prepare_gift_original_cover", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

GENERATED_AT = "2026-07-30T15:30:00Z"


def prepare(tmp_path: Path, name: str) -> dict:
    return MODULE.prepare_package(
        tmp_path / name,
        generated_at=GENERATED_AT,
    )


def test_original_pair_is_deterministic_and_catalog_bound(tmp_path: Path) -> None:
    first = prepare(tmp_path, "first")
    second = prepare(tmp_path, "second")

    assert first["title"] == "The Gift of the Magi"
    assert first["author"] == "O. Henry"
    assert first["front"]["sha256"] == second["front"]["sha256"]
    assert first["back"]["sha256"] == second["back"]["sha256"]
    assert first["front"]["thumbnail"]["sha256"] == second["front"]["thumbnail"]["sha256"]
    assert first["back"]["thumbnail"]["sha256"] == second["back"]["thumbnail"]["sha256"]


def test_original_pair_has_no_external_or_generated_art(tmp_path: Path) -> None:
    manifest = prepare(tmp_path, "candidate")

    assert manifest["generation_mode"] == (
        "deterministic_original_programmatic_graphical_composition"
    )
    assert manifest["rights"] == {
        "status": "ORIGINAL_COMPOSITION_NO_THIRD_PARTY_ART",
        "external_image_assets": [],
        "generated_image_model": None,
        "territorial_restriction": None,
        "commercial_use_blocker": None,
    }
    assert manifest["constraints"]["ai_generated_imagery"] is False
    assert manifest["constraints"]["placeholder_art"] is False


def test_publication_stays_fail_closed_before_manual_review(tmp_path: Path) -> None:
    manifest = prepare(tmp_path, "candidate")

    assert manifest["status"] == "PRIVATE_CANDIDATE_EDITORIAL_REVIEW_REQUIRED"
    assert manifest["review"]["admin_upload_status"] == "NOT_UPLOADED"
    assert manifest["review"]["canonical_promotion_status"] == "NOT_PROMOTED"
    assert manifest["constraints"]["public_upload_authorized"] is False
    assert manifest["constraints"]["canonical_promotion_authorized"] is False
    assert manifest["constraints"]["audiobook_release_state_mutated"] is False


def test_output_geometry_performance_and_copy_are_safe(tmp_path: Path) -> None:
    package = tmp_path / "candidate"
    manifest = prepare(tmp_path, "candidate")
    validation = MODULE.read_json(package / "visual_validation.json")

    assert validation["status"] == "AUTOMATED_PASS_MANUAL_EDITORIAL_REVIEW_PENDING"
    assert validation["geometry_errors"] == []
    assert validation["checks"]["reader_facing_internal_language_rendered"] is False
    assert validation["checks"]["third_party_image_asset_count"] == 0
    assert validation["checks"]["front_dimensions_1600x2400"] is True
    assert validation["checks"]["back_dimensions_1600x2400"] is True
    assert validation["checks"]["thumbnail_derivatives_under_80_kib"] is True
    assert validation["checks"]["feature_derivatives_under_180_kib"] is True
    assert manifest["copy"]["title"] == "The Gift of the Magi"
    assert manifest["copy"]["author"] == "O. Henry"
    assert manifest["copy"]["back_description"] == (
        "A poor couple each secretly sell their most prized possession "
        "to buy a Christmas gift for the other."
    )


def test_controlled_catalog_remains_byte_identical(tmp_path: Path) -> None:
    before = {
        path: MODULE.sha256_file(path)
        for path in MODULE.CATALOG_PATHS
    }
    manifest = prepare(tmp_path, "candidate")
    after = {
        path: MODULE.sha256_file(path)
        for path in MODULE.CATALOG_PATHS
    }

    assert before == after
    assert manifest["catalog_hashes"] == {
        MODULE.repo_relative(path): digest
        for path, digest in after.items()
    }


def test_committed_review_and_ocr_are_bound_to_exact_outputs() -> None:
    package = MODULE.DEFAULT_PACKAGE
    manifest = MODULE.read_json(package / "candidate_manifest.json")
    review = MODULE.read_json(package / "manual_visual_review.json")
    ocr = MODULE.read_json(package / "ocr_proofread_evidence.json")
    promotion = MODULE.read_json(package / "canonical_promotion_evidence.json")

    assert review["decision"]["private_candidate_visual_gate"] == "PASS"
    assert review["decision"]["admin_upload_authorized"] is True
    assert review["decision"]["audio_release_truth_change_authorized"] is False
    assert review["artifacts"]["front_master"]["sha256"] == manifest["front"]["sha256"]
    assert review["artifacts"]["back_master"]["sha256"] == manifest["back"]["sha256"]
    assert ocr["front"]["sha256"] == manifest["front"]["sha256"]
    assert ocr["back"]["sha256"] == manifest["back"]["sha256"]
    assert ocr["front"]["exact_normalized_match"] is True
    assert ocr["back"]["exact_normalized_match"] is True
    assert ocr["proofread"]["internal_release_language_absent"] is True
    assert promotion["upload_and_promotion"]["front"]["sha256"] == manifest["front"]["sha256"]
    assert promotion["upload_and_promotion"]["back"]["sha256"] == manifest["back"]["sha256"]
    assert promotion["verification"]["reader_audio_release_truth_unchanged"] is True
    assert promotion["audiobook"]["release_gate_changed"] is False
