from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend import catalog_truth
from backend.home_curation import build_home_curated_payload


ROOT = Path(__file__).resolve().parents[2]
DROPPED_SLUG = "book-2b9853ec52"
ACTIVE_FRONTEND_PATHS = (
    "frontend/src/data/homeCuratedSprint1.json",
    "frontend/src/lib/libraryFallbackBooks.js",
    "frontend/src/lib/shelfTwoBooks.js",
    "frontend/src/components/ComingSoonBoard.jsx",
)


def read_json(relative_path: str) -> dict[str, Any]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def contains_slug(value: Any) -> bool:
    if isinstance(value, dict):
        return any(contains_slug(key) or contains_slug(item) for key, item in value.items())
    if isinstance(value, list):
        return any(contains_slug(item) for item in value)
    return value == DROPPED_SLUG


def test_exclusion_tombstone_is_identical_in_both_runtime_layouts():
    root_policy = read_json("data/catalog_exclusions.json")
    backend_policy = read_json("backend/data/catalog_exclusions.json")

    assert backend_policy == root_policy
    assert root_policy["titles"][DROPPED_SLUG]["public_catalog_excluded"] is True
    assert root_policy["titles"][DROPPED_SLUG]["reader_excluded"] is True
    assert root_policy["titles"][DROPPED_SLUG]["audio_excluded"] is True
    assert DROPPED_SLUG in catalog_truth.PUBLIC_CATALOG_EXCLUDED_SLUGS
    assert DROPPED_SLUG not in catalog_truth.CONTROLLED_LIVE_BOOK_SLUGS
    assert DROPPED_SLUG not in catalog_truth.PIPELINE_CANDIDATE_SLUGS
    assert DROPPED_SLUG not in catalog_truth.AUDIO_ENABLED_SLUGS


def test_exclusion_overrides_historical_manifest_and_audio_approval(monkeypatch):
    artifact_dir = catalog_truth.first_controlled_artifact_dir(DROPPED_SLUG)
    artifact = json.loads((artifact_dir / "public_book.json").read_text(encoding="utf-8"))
    artifact["audiobook_release_conveyor"] = {
        "schema_version": catalog_truth.AUDIOBOOK_RELEASE_CONVEYOR_SCHEMA,
        "reader_release_approved": True,
        "audio_release_approved": True,
    }
    monkeypatch.setattr(
        catalog_truth,
        "LEGACY_CONTROLLED_LIVE_BOOK_SLUGS",
        (*catalog_truth.LEGACY_CONTROLLED_LIVE_BOOK_SLUGS, DROPPED_SLUG),
    )
    monkeypatch.setattr(
        catalog_truth,
        "AUDIO_ENABLED_SLUGS",
        {*catalog_truth.AUDIO_ENABLED_SLUGS, DROPPED_SLUG},
    )

    assert catalog_truth.is_live_approved_book(artifact) is False
    assert catalog_truth.is_pipeline_candidate(artifact) is False
    assert catalog_truth.can_expose_reader(artifact) is False
    assert catalog_truth.can_expose_audio(artifact) is False

    projection = catalog_truth.public_book_projection(artifact)
    assert projection is not None
    assert projection["reader_enabled"] is False
    assert projection["audiobook_enabled"] is False
    assert projection["public_route"] == ""
    assert projection["reader_url"] == ""
    assert projection["audio_url"] == ""


def test_home_api_and_bundled_client_surfaces_exclude_dropped_title():
    assert contains_slug(build_home_curated_payload()) is False
    assert contains_slug(read_json("frontend/src/data/homeCuratedSprint1.json")) is False
    for relative_path in ACTIVE_FRONTEND_PATHS[1:]:
        assert DROPPED_SLUG not in (ROOT / relative_path).read_text(encoding="utf-8")


def test_active_audio_release_tranche_does_not_claim_excluded_title():
    tranche = read_json("internal/audiobook_lab/release_gate/claimable_go_live_tranche.json")

    assert DROPPED_SLUG not in tranche["approved_public_audio_slugs"]
