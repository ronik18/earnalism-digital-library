from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND_CONTROLLED_LAUNCH = ROOT / "backend" / "data" / "controlled_launch.json"
ROOT_CONTROLLED_LAUNCH = ROOT / "data" / "controlled_launch.json"

APPROVED_BENGALI_PILOT = "book-2b9853ec52"
READER_ONLY_HOLD = "a-ghost-story"
BLOCKED_BENGALI_CANARIES = {
    "book-d19e96859f",
    "book-f5d593e1f4",
    "muchiram-gurer-jibanchorit",
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

    assert READER_ONLY_HOLD in backend_launch["live_approved_slugs"]
    assert READER_ONLY_HOLD not in backend_audio
    assert backend_audio.isdisjoint(BLOCKED_BENGALI_CANARIES)


def test_backend_controlled_launch_has_no_duplicate_slugs():
    backend_launch = load_json(BACKEND_CONTROLLED_LAUNCH)

    for key in ("live_approved_slugs", "pipeline_slugs", "audio_enabled_slugs"):
        values = backend_launch[key]
        assert len(values) == len(set(values))
