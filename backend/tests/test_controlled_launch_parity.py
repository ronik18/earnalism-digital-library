from __future__ import annotations

import hashlib
import json
from pathlib import Path

from backend.rights_decision_gate import evaluate_runtime_path, load_production_registry
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[2]
BACKEND_CONTROLLED_LAUNCH = ROOT / "backend" / "data" / "controlled_launch.json"
ROOT_CONTROLLED_LAUNCH = ROOT / "data" / "controlled_launch.json"
BACKEND_CATALOG_EXCLUSIONS = ROOT / "backend" / "data" / "catalog_exclusions.json"
ROOT_CATALOG_EXCLUSIONS = ROOT / "data" / "catalog_exclusions.json"
BACKEND_CONTROLLED_PUBLICATIONS = ROOT / "backend" / "data" / "controlled_publications"
ROOT_CONTROLLED_PUBLICATIONS = ROOT / "data" / "controlled_publications"

FULLY_EXCLUDED_BENGALI_TITLE = "book-2b9853ec52"
INDIA_TEXT_RELEASE_SLUGS = {
    "a-ghost-story",
    "the-tell-tale-heart",
    "radharani",
    "a-white-heron",
    "the-gift-of-the-magi",
    "the-canterville-ghost",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def active_runtime_package(slug: str) -> Path:
    """Return the package the API uses for release-time rights decisions.

    The root package retains prior evidence, while the backend mirror is the
    active runtime package whenever it exists.  Tests for an entitled reader
    path must therefore not validate a historical root decision as current.
    """
    backend_package = BACKEND_CONTROLLED_PUBLICATIONS / slug
    return backend_package if backend_package.is_dir() else ROOT_CONTROLLED_PUBLICATIONS / slug


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


def test_backend_controlled_launch_opens_only_the_six_india_text_titles_and_no_audio():
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


def test_india_commercial_text_release_is_mirrored_and_audio_remains_disabled():
    root_launch = load_json(ROOT_CONTROLLED_LAUNCH)
    backend_launch = load_json(BACKEND_CONTROLLED_LAUNCH)

    for launch in (root_launch, backend_launch):
        assert set(launch["live_approved_slugs"]) == INDIA_TEXT_RELEASE_SLUGS
        assert launch["public_audio_exposure_enabled"] is False
        assert launch["public_paid_commerce_enabled"] is True
        assert launch["text_access_mode"] == "COMMERCIAL_ENTITLEMENT"
        assert launch["audio_enabled_slugs"] == []


def test_six_title_release_uses_commercial_mode_and_keeps_checkout_audio_disabled():
    root_launch = load_json(ROOT_CONTROLLED_LAUNCH)
    backend_launch = load_json(BACKEND_CONTROLLED_LAUNCH)
    expected_modes = {
        "a-ghost-story": "COMMERCIAL_ENTITLEMENT",
        "the-tell-tale-heart": "COMMERCIAL_ENTITLEMENT",
        "radharani": "COMMERCIAL_ENTITLEMENT",
        "a-white-heron": "COMMERCIAL_ENTITLEMENT",
        "the-gift-of-the-magi": "COMMERCIAL_ENTITLEMENT",
        "the-canterville-ghost": "COMMERCIAL_ENTITLEMENT",
    }

    for launch in (root_launch, backend_launch):
        assert launch["title_access_modes"] == expected_modes
        assert set(launch["live_approved_slugs"]) == INDIA_TEXT_RELEASE_SLUGS
        assert set(launch["title_access_modes"]) == INDIA_TEXT_RELEASE_SLUGS
        assert set(launch["title_access_modes"].values()) == {"COMMERCIAL_ENTITLEMENT"}
        assert launch["public_paid_commerce_enabled"] is True
        assert launch["public_audio_exposure_enabled"] is False


def test_six_title_release_has_hash_bound_reading_pass_rights_and_published_reader_manifests():
    launch = load_json(BACKEND_CONTROLLED_LAUNCH)
    registry, revoked = load_production_registry()
    commercial_slugs = tuple(sorted(INDIA_TEXT_RELEASE_SLUGS))
    now = datetime.now(timezone.utc)

    for slug in commercial_slugs:
        assert slug in launch["live_approved_slugs"]
        package = active_runtime_package(slug)
        manifest = load_json(package / "publication_manifest.json")
        assert manifest["reader_release"]["status"] == "APPROVED"
        assert manifest["reader_release"]["exposed"] is True
        record = load_json(package / "rights_decision.json")
        components = {
            name.removesuffix(".json"): hashlib.sha256((package / name).read_bytes()).hexdigest()
            for name in (
                "public_book.json",
                "reader_manifest.json",
                "source_evidence.json",
                "approval_evidence.json",
                "checksum_manifest.json",
                "publication_manifest.json",
            )
        }
        assert registry[record["decision_id"]]
        assert record["accepted_by"].startswith("REO ENTERPRISE under the direct owner-provided India commercial go-live mandate") or record["accepted_by"].startswith("REO ENTERPRISE proprietor under the direct user-provided") or record["accepted_by"].startswith("REO ENTERPRISE proprietor under the direct PR #414 go-live mandate")
        for action in ("reading_pass_session_start", "reading_pass_page", "reading_pass_lease_renewal"):
            verdict = evaluate_runtime_path(
                action,
                record=record,
                edition_id=slug,
                operator_id="reo-enterprise",
                country="IN",
                country_trusted=True,
                required_components=components,
                accepted_records=registry,
                revoked_decision_ids=revoked,
                now=now,
            )
            assert verdict.passed is True, (slug, action, verdict.reasons)


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

        if slug in {"a-ghost-story", "the-tell-tale-heart", "radharani"}:
            assert dispositions[f"controlled-{slug}"]["status"] == "ACCEPTED"
        assert registry["commercial_batch_dispositions"][f"controlled-{slug}"]["status"] == "PREVIEW_RELEASED_ENTITLEMENT_REQUIRED_FROM_PAGE_4"


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
