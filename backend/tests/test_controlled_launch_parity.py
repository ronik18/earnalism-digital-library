from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND_CONTROLLED_LAUNCH = ROOT / "backend" / "data" / "controlled_launch.json"
ROOT_CONTROLLED_LAUNCH = ROOT / "data" / "controlled_launch.json"
BACKEND_CATALOG_EXCLUSIONS = ROOT / "backend" / "data" / "catalog_exclusions.json"
ROOT_CATALOG_EXCLUSIONS = ROOT / "data" / "catalog_exclusions.json"

FULLY_EXCLUDED_BENGALI_TITLE = "book-2b9853ec52"
INDIA_TEXT_RELEASE_SLUGS = {
    "a-ghost-story",
    "the-tell-tale-heart",
    "radharani",
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


def test_backend_controlled_launch_opens_only_the_three_india_text_titles_and_no_audio():
    backend_launch = load_json(BACKEND_CONTROLLED_LAUNCH)
    backend_audio = set(backend_launch["audio_enabled_slugs"])

    assert backend_launch["public_reader_exposure_enabled"] is True
    assert set(backend_launch["live_approved_slugs"]) == INDIA_TEXT_RELEASE_SLUGS
    assert backend_audio == set()


def test_root_controlled_launch_keeps_yugalanguriya_and_every_other_title_held():
    root_launch = load_json(ROOT_CONTROLLED_LAUNCH)

    assert set(root_launch["live_approved_slugs"]) == INDIA_TEXT_RELEASE_SLUGS
    assert "yugalanguriya" not in root_launch["live_approved_slugs"]
    assert FULLY_EXCLUDED_BENGALI_TITLE not in root_launch["audio_enabled_slugs"]


def test_india_text_release_is_mirrored_and_commerce_and_audio_remain_disabled():
    root_launch = load_json(ROOT_CONTROLLED_LAUNCH)
    backend_launch = load_json(BACKEND_CONTROLLED_LAUNCH)

    for launch in (root_launch, backend_launch):
        assert set(launch["live_approved_slugs"]) == INDIA_TEXT_RELEASE_SLUGS
        assert launch["public_audio_exposure_enabled"] is False
        assert launch["public_paid_commerce_enabled"] is False
        assert launch["text_access_mode"] == "PILOT_FULL_FREE"
        assert launch["audio_enabled_slugs"] == []


def test_backend_controlled_launch_has_no_duplicate_slugs():
    backend_launch = load_json(BACKEND_CONTROLLED_LAUNCH)

    for key in ("live_approved_slugs", "pipeline_slugs", "audio_enabled_slugs"):
        values = backend_launch[key]
        assert len(values) == len(set(values))


def test_released_title_resources_and_content_hashes_are_complete():
    launch = load_json(ROOT_CONTROLLED_LAUNCH)
    registry = load_json(ROOT / "backend" / "data" / "rights_decision_registry.json")
    dispositions = registry["pilot_dispositions"]

    assert set(launch["live_approved_slugs"]) == INDIA_TEXT_RELEASE_SLUGS
    for slug in sorted(INDIA_TEXT_RELEASE_SLUGS):
        package = ROOT / "data" / "controlled_publications" / slug
        for name in (
            "public_book.json",
            "reader_manifest.json",
            "source_evidence.json",
            "checksum_manifest.json",
            "rights_decision.json",
        ):
            assert (package / name).is_file(), f"{slug} is missing {name}"

        book = load_json(package / "public_book.json")
        reader = load_json(package / "reader_manifest.json")
        chapters = sorted(book["chapters"], key=lambda chapter: chapter["order"])
        assert reader["chapter_count"] == len(chapters)
        assert [(item["id"], item["order"]) for item in reader["chapters"]] == [
            (item["id"], item["order"]) for item in chapters
        ]
        for chapter in chapters:
            chapter_path = package / "chapters" / f"{chapter['id']}.json"
            assert chapter_path.is_file(), f"{slug} is missing {chapter_path.name}"
            payload = load_json(chapter_path)
            assert payload["content_hash"] == hashlib.sha256(payload["content"].encode("utf-8")).hexdigest()

        assert dispositions[f"controlled-{slug}"]["status"] == "ACCEPTED"


def test_yugalanguriya_publication_package_is_archived_and_remains_held():
    launch = load_json(ROOT_CONTROLLED_LAUNCH)
    backend_launch = load_json(BACKEND_CONTROLLED_LAUNCH)
    registry = load_json(ROOT / "backend" / "data" / "rights_decision_registry.json")
    archive = ROOT / "internal" / "archives" / "held_titles" / "yugalanguriya"
    active_roots = (
        ROOT / "data" / "controlled_publications" / "yugalanguriya",
        ROOT / "backend" / "data" / "controlled_publications" / "yugalanguriya",
    )

    assert all(not path.exists() for path in active_roots)
    assert (archive / "ARCHIVE_STATUS.md").is_file()
    assert (archive / "source-book" / "raw" / "source.txt").is_file()
    assert (archive / "source-book" / "source-rights.md").is_file()
    assert (archive / "controlled-publication-package" / "checksum_manifest.json").is_file()
    assert "yugalanguriya" not in launch["live_approved_slugs"]
    assert "yugalanguriya" not in backend_launch["live_approved_slugs"]
    assert "yugalanguriya" not in launch["audio_enabled_slugs"]
    assert "yugalanguriya" not in backend_launch["audio_enabled_slugs"]
    assert registry["pilot_dispositions"]["controlled-yugalanguriya"]["status"] == "HOLD"
