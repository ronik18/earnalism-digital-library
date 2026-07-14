from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND_CONTROLLED_LAUNCH = ROOT / "backend" / "data" / "controlled_launch.json"
ROOT_CONTROLLED_LAUNCH = ROOT / "data" / "controlled_launch.json"

APPROVED_BENGALI_PILOT = "book-2b9853ec52"
APPROVED_ENGLISH_STORY = "a-ghost-story"
APPROVED_REUSE_STORY = "sredni-vashtar"
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


def test_backend_controlled_launch_restores_book_2b_from_source_truth():
    root_launch = load_json(ROOT_CONTROLLED_LAUNCH)
    backend_launch = load_json(BACKEND_CONTROLLED_LAUNCH)

    assert APPROVED_BENGALI_PILOT in root_launch["live_approved_slugs"]
    assert APPROVED_BENGALI_PILOT in root_launch["audio_enabled_slugs"]
    assert APPROVED_BENGALI_PILOT in backend_launch["live_approved_slugs"]
    assert APPROVED_BENGALI_PILOT in backend_launch["audio_enabled_slugs"]


def test_backend_controlled_launch_preserves_audio_hold_states():
    backend_launch = load_json(BACKEND_CONTROLLED_LAUNCH)
    backend_audio = set(backend_launch["audio_enabled_slugs"])

    assert APPROVED_ENGLISH_STORY in backend_launch["live_approved_slugs"]
    assert APPROVED_ENGLISH_STORY in backend_audio
    assert PRIVATE_QA_AUDIO_HOLD in backend_launch["live_approved_slugs"]
    assert PRIVATE_QA_AUDIO_HOLD not in backend_audio
    assert backend_audio.isdisjoint(BLOCKED_BENGALI_CANARIES)
    assert backend_audio.isdisjoint(HISTORICAL_RECONSTRUCTION_AUDIO_HOLDS)
    assert backend_audio == {APPROVED_BENGALI_PILOT, APPROVED_ENGLISH_STORY, APPROVED_REUSE_STORY}


def test_root_controlled_launch_keeps_bn_066_reader_live_and_audio_hidden():
    root_launch = load_json(ROOT_CONTROLLED_LAUNCH)

    assert PRIVATE_QA_AUDIO_HOLD in root_launch["live_approved_slugs"]
    assert PRIVATE_QA_AUDIO_HOLD not in root_launch["audio_enabled_slugs"]
    assert set(root_launch["audio_enabled_slugs"]) == {
        APPROVED_BENGALI_PILOT,
        APPROVED_ENGLISH_STORY,
        APPROVED_REUSE_STORY,
    }


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
