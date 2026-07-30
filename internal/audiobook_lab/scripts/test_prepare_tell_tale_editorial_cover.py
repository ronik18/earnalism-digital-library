from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).with_name("prepare_tell_tale_editorial_cover.py")
SPEC = importlib.util.spec_from_file_location("prepare_tell_tale_editorial_cover", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_private_candidate_is_deterministic_and_truth_bound(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    generated_at = "2026-07-30T06:17:20Z"

    first = MODULE.prepare_package(
        first_dir,
        MODULE.DEFAULT_SOURCE,
        MODULE.DEFAULT_RIGHTS,
        generated_at=generated_at,
    )
    second = MODULE.prepare_package(
        second_dir,
        MODULE.DEFAULT_SOURCE,
        MODULE.DEFAULT_RIGHTS,
        generated_at=generated_at,
    )

    assert first["status"] == "PRIVATE_CANDIDATE_EDITORIAL_REVIEW_REQUIRED"
    assert first["title"] == "The Tell-Tale Heart"
    assert first["author"] == "Edgar Allan Poe"
    assert first["source_art"]["sha256"] == MODULE.SOURCE_SHA256
    assert first["front"]["sha256"] == second["front"]["sha256"]
    assert first["back"]["sha256"] == second["back"]["sha256"]
    assert first["constraints"] == {
        "private_only": True,
        "public_catalog_mutated": False,
        "reader_state_mutated": False,
        "audiobook_release_state_mutated": False,
        "ai_generated_imagery": False,
        "placeholder_art": False,
    }

    validation = MODULE.read_json(first_dir / "visual_validation.json")
    assert validation["status"] == "PASS_PENDING_EDITORIAL_REVIEW"
    assert validation["checks"]["text_box_overlap_count"] == 0
    assert validation["checks"]["public_catalog_unchanged"] is True


def test_tampered_source_art_fails_closed(tmp_path: Path) -> None:
    tampered = tmp_path / "tampered.jpeg"
    tampered.write_bytes(MODULE.DEFAULT_SOURCE.read_bytes() + b"tampered")

    with pytest.raises(MODULE.CoverCandidateError, match="SHA-256"):
        MODULE.prepare_package(
            tmp_path / "package",
            tampered,
            MODULE.DEFAULT_RIGHTS,
            generated_at="2026-07-30T06:17:20Z",
        )
