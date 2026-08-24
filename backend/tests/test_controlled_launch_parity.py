from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND_CONTROLLED_LAUNCH = ROOT / "backend" / "data" / "controlled_launch.json"
ROOT_CONTROLLED_LAUNCH = ROOT / "data" / "controlled_launch.json"
BACKEND_CATALOG_EXCLUSIONS = ROOT / "backend" / "data" / "catalog_exclusions.json"
ROOT_CATALOG_EXCLUSIONS = ROOT / "data" / "catalog_exclusions.json"

FULLY_EXCLUDED_BENGALI_TITLE = "book-2b9853ec52"
APPROVED_ENGLISH_STORY = "a-ghost-story"
PRIVATE_QA_AUDIO_HOLD = "bn-066"
BLOCKED_BENGALI_CANARIES = {
    "book-d19e96859f",
    "book-f5d593e1f4",
    "muchiram-gurer-jibanchorit",
}
SPRINT1_READER_ONLY_ADDITIONS = {
    "book-d19e96859f",
    "book-f5d593e1f4",
    "muchiram-gurer-jibanchorit",
    "radharani",
    "the-call-of-the-wild",
    "the-time-machine",
}
HISTORICAL_RECONSTRUCTION_AUDIO_HOLDS = {
    "alices-adventures-in-wonderland",
    "bn-027",
    "lokrahasya",
    "mrinalini",
    "nishkriti",
    "the-wonderful-wizard-of-oz",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_root_and_backend_controlled_launch_truth_are_identical():
    assert load_json(ROOT_CONTROLLED_LAUNCH) == load_json(BACKEND_CONTROLLED_LAUNCH)


def test_owner_excluded_title_is_absent_from_both_launch_trees():
    root_launch = load_json(ROOT_CONTROLLED_LAUNCH)
    backend_launch = load_json(BACKEND_CONTROLLED_LAUNCH)

    for launch in (root_launch, backend_launch):
        for key in ("live_approved_slugs", "pipeline_slugs", "audio_enabled_slugs"):
            assert FULLY_EXCLUDED_BENGALI_TITLE not in launch[key]


def test_owner_exclusion_tombstone_is_mirrored_exactly():
    root_exclusions = load_json(ROOT_CATALOG_EXCLUSIONS)
    backend_exclusions = load_json(BACKEND_CATALOG_EXCLUSIONS)

    assert backend_exclusions == root_exclusions
    assert root_exclusions["titles"][FULLY_EXCLUDED_BENGALI_TITLE] == {
        "public_catalog_excluded": True,
        "reader_excluded": True,
        "audio_excluded": True,
        "reason": "Owner-confirmed full removal from the active Earnalism catalog.",
        "retain_historical_artifacts": True,
        "retain_media": True,
    }


def test_backend_controlled_launch_preserves_audio_hold_states():
    backend_launch = load_json(BACKEND_CONTROLLED_LAUNCH)
    backend_audio = set(backend_launch["audio_enabled_slugs"])

    assert APPROVED_ENGLISH_STORY in backend_launch["live_approved_slugs"]
    assert APPROVED_ENGLISH_STORY in backend_audio
    assert PRIVATE_QA_AUDIO_HOLD in backend_launch["live_approved_slugs"]
    assert PRIVATE_QA_AUDIO_HOLD not in backend_audio
    assert backend_audio.isdisjoint(BLOCKED_BENGALI_CANARIES)
    assert backend_audio.isdisjoint(HISTORICAL_RECONSTRUCTION_AUDIO_HOLDS)
    assert FULLY_EXCLUDED_BENGALI_TITLE not in backend_audio


def test_root_controlled_launch_keeps_bn_066_reader_live_and_audio_hidden():
    root_launch = load_json(ROOT_CONTROLLED_LAUNCH)

    assert PRIVATE_QA_AUDIO_HOLD in root_launch["live_approved_slugs"]
    assert PRIVATE_QA_AUDIO_HOLD not in root_launch["audio_enabled_slugs"]
    assert FULLY_EXCLUDED_BENGALI_TITLE not in root_launch["audio_enabled_slugs"]


def test_sprint1_reader_additions_are_live_in_both_trees_and_audio_hidden_from_dupe():
    root_launch = load_json(ROOT_CONTROLLED_LAUNCH)
    backend_launch = load_json(BACKEND_CONTROLLED_LAUNCH)

    for launch in (root_launch, backend_launch):
        assert SPRINT1_READER_ONLY_ADDITIONS.issubset(launch["live_approved_slugs"])
        assert set(launch["audio_enabled_slugs"]).isdisjoint(SPRINT1_READER_ONLY_ADDITIONS)


def test_sprint1_reader_additions_are_live_in_both_trees_and_audio_hidden():
    root_launch = load_json(ROOT_CONTROLLED_LAUNCH)
    backend_launch = load_json(BACKEND_CONTROLLED_LAUNCH)

    for launch in (root_launch, backend_launch):
        assert SPRINT1_READER_ONLY_ADDITIONS.issubset(launch["live_approved_slugs"])
        assert set(launch["audio_enabled_slugs"]).isdisjoint(SPRINT1_READER_ONLY_ADDITIONS)


def test_historical_reconstruction_evidence_does_not_approve_public_audio():
    for slug in HISTORICAL_RECONSTRUCTION_AUDIO_HOLDS:
        evidence = load_json(
            ROOT / "backend" / "data" / "controlled_publications" / slug / "approval_evidence.json"
        )
        assert evidence["approval_scope"] == "historical_admin_import_reconstruction"
        assert evidence["audio_public_release"] == "PUBLIC_AUDIO_RELEASE_BLOCKED_QA_REQUIRED"
        assert evidence["audiobook_enabled"] is False


def test_backend_controlled_launch_has_no_duplicate_slugs():
    backend_launch = load_json(BACKEND_CONTROLLED_LAUNCH)

    for key in ("live_approved_slugs", "pipeline_slugs", "audio_enabled_slugs"):
        values = backend_launch[key]
        assert len(values) == len(set(values))
