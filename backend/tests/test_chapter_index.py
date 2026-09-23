import json
from copy import deepcopy
from pathlib import Path

import pytest

from backend.domain.chapter_index import (
    CHAPTER_INDEX_CONTRACT_VERSION,
    build_chapter_index_entries,
    chapter_index_entry,
    normalize_chapter_display_title,
)


ROOT = Path(__file__).resolve().parents[2]
CONTROLLED_ROOT = ROOT / "backend" / "data" / "controlled_publications"
INVENTORY_PATH = Path(__file__).parent / "fixtures" / "controlled-package-inventory.v1.json"


def assert_controlled_inventory(actual, inventory):
    """Check a frozen engineering baseline; this does not certify book contents."""
    packages = inventory["packages"]
    expected = {package["package_key"]: package for package in packages}
    assert len(expected) == len(packages) == inventory["expected_manifest_count"]
    assert sum(package["chapter_count"] for package in packages) == inventory["expected_chapter_count"]
    assert set(actual) == set(expected), {
        "missing": sorted(set(expected) - set(actual)),
        "unexpected": sorted(set(actual) - set(expected)),
    }
    for key, package in expected.items():
        expected_chapters = package["chapters"]
        assert len(expected_chapters) == package["chapter_count"], key
        assert len({chapter["id"] for chapter in expected_chapters}) == len(expected_chapters), key
        manifest = actual[key]
        assert manifest.get("slug") == package["manifest_slug"], key
        assert manifest.get("chapter_count") == package["chapter_count"], key
        actual_chapters = [
            {"id": chapter.get("id"), "order": chapter.get("order")}
            for chapter in manifest.get("chapters", [])
        ]
        assert actual_chapters == expected_chapters, key


def test_dracula_titles_have_one_normalized_structural_label():
    assert normalize_chapter_display_title(
        "CHAPTER II. JONATHAN HARKER’S JOURNAL-- continued"
    ) == "Chapter 2. Jonathan Harker’s Journal"
    entry = chapter_index_entry(
        {"id": "chapter-002", "title": "CHAPTER II. JONATHAN HARKER’S JOURNAL-- continued"},
        position=2,
        total=27,
    )
    assert entry["index_sequence_label"] == "02"
    assert entry["index_secondary_label"] == "Chapter 2"
    assert entry["index_title"] == "Jonathan Harker’s Journal"


def test_unsubtitled_and_non_english_units_remain_meaningful():
    assert chapter_index_entry(
        {"title": "CHAPTER V"}, position=5, total=27
    )["index_title"] == "Chapter 5"
    assert chapter_index_entry(
        {"title": "প্রথম পরিচ্ছেদ"}, position=1, total=4
    )["index_title"] == "প্রথম পরিচ্ছেদ"


def test_dracula_index_is_uniform_and_publisher_catalog_is_not_reader_content():
    artifact_roots = (
        ROOT / "backend" / "data" / "controlled_publications" / "dracula",
        ROOT / "data" / "controlled_publications" / "dracula",
    )
    expected_titles = [
        "CHAPTER I. JONATHAN HARKER’S JOURNAL",
        "CHAPTER II. JONATHAN HARKER’S JOURNAL-- continued",
        "CHAPTER III. JONATHAN HARKER’S JOURNAL-- continued",
        "CHAPTER IV. JONATHAN HARKER’S JOURNAL-- continued",
        "CHAPTER V. MINA MURRAY’S CORRESPONDENCE",
        "CHAPTER VI. MINA MURRAY’S JOURNAL",
        "CHAPTER VII. CUTTING FROM “THE DAILYGRAPH,” 8 AUGUST",
        "CHAPTER VIII. MINA MURRAY’S JOURNAL",
        "CHAPTER IX. MINA HARKER’S CORRESPONDENCE",
        "CHAPTER X. DR. SEWARD’S DIARY",
        "CHAPTER XI. LUCY WESTENRA’S DIARY",
        "CHAPTER XII. DR. SEWARD’S DIARY",
        "CHAPTER XIII. DR. SEWARD’S DIARY",
        "CHAPTER XIV. MINA HARKER’S JOURNAL",
        "CHAPTER XV. DR. SEWARD’S DIARY",
        "CHAPTER XVI. DR. SEWARD’S DIARY-- continued",
        "CHAPTER XVII. DR. SEWARD’S DIARY-- continued",
        "CHAPTER XVIII. DR. SEWARD’S DIARY",
        "CHAPTER XIX. JONATHAN HARKER’S JOURNAL",
        "CHAPTER XX. JONATHAN HARKER’S JOURNAL",
        "CHAPTER XXI. DR. SEWARD’S DIARY",
        "CHAPTER XXII. JONATHAN HARKER’S JOURNAL",
        "CHAPTER XXIII. DR. SEWARD’S DIARY",
        "CHAPTER XXIV. DR. SEWARD’S PHONOGRAPH DIARY, SPOKEN BY VAN HELSING",
        "CHAPTER XXV. DR. SEWARD’S DIARY",
        "CHAPTER XXVI. DR. SEWARD’S DIARY",
        "CHAPTER XXVII. MINA HARKER’S JOURNAL",
    ]

    for artifact_root in artifact_roots:
        manifest = json.loads((artifact_root / "reader_manifest.json").read_text(encoding="utf-8"))
        assert [chapter["title"] for chapter in manifest["chapters"]] == expected_titles
        index_entries = build_chapter_index_entries(manifest["chapters"])
        assert [index_entries[index - 1]["index_title"] for index in (5, 9, 10, 11, 13, 15)] == [
            "Mina Murray’s Correspondence",
            "Mina Harker’s Correspondence",
            "Dr. Seward’s Diary",
            "Lucy Westenra’s Diary",
            "Dr. Seward’s Diary",
            "Dr. Seward’s Diary",
        ]

        ending = json.loads(
            (artifact_root / "chapters" / "chapter-027.json").read_text(encoding="utf-8")
        )["content"]
        assert ending.rstrip().endswith("JONATHAN HARKER.\n\nTHE END")
        assert "Grosset & Dunlap" not in ending
        assert "DETECTIVE STORIES BY J. S. FLETCHER" not in ending


def test_catalog_wide_reader_indexes_are_complete_and_deterministic():
    manifests = sorted(CONTROLLED_ROOT.glob("*/reader_manifest.json"))
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    archived_hold_keys = {"yugalanguriya"}
    current_inventory = {
        **inventory,
        "packages": [
            package for package in inventory["packages"]
            if package["package_key"] not in archived_hold_keys
        ],
    }
    current_inventory["expected_manifest_count"] = len(current_inventory["packages"])
    current_inventory["expected_chapter_count"] = sum(
        package["chapter_count"] for package in current_inventory["packages"]
    )
    actual = {
        path.parent.name: json.loads(path.read_text(encoding="utf-8"))
        for path in manifests
    }
    assert "yugalanguriya" not in actual
    assert any(
        package["package_key"] == "yugalanguriya"
        for package in inventory["packages"]
    ), "the frozen fixture must retain Yugalanguriya's historical snapshot"
    assert_controlled_inventory(actual, current_inventory)
    audited_chapters = 0
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        chapters = manifest.get("chapters") or []
        first = build_chapter_index_entries(chapters)
        second = build_chapter_index_entries(chapters)
        assert first == second, manifest.get("slug")
        assert len(first) == int(manifest.get("chapter_count") or 0), manifest.get("slug")
        assert len({entry.get("id") for entry in first}) == len(first), manifest.get("slug")
        assert [entry["index_sequence"] for entry in first] == list(range(1, len(first) + 1))
        assert all(entry["index_contract"] == CHAPTER_INDEX_CONTRACT_VERSION for entry in first)
        assert all(entry["index_title"].strip() for entry in first)
        audited_chapters += len(first)
    assert audited_chapters == current_inventory["expected_chapter_count"]


@pytest.mark.parametrize("mutation", [
    None,
    "missing_package",
    "missing_zero_chapter_alias",
    "unexpected_package",
    "same_count_substitution",
    "wrong_manifest_slug",
    "wrong_count",
    "renamed_chapter",
    "duplicate_chapter",
    "reordered_chapters",
    "changed_order",
])
def test_frozen_inventory_detects_catalog_drift(mutation):
    inventory = {
        "expected_manifest_count": 2,
        "expected_chapter_count": 2,
        "packages": [
            {"package_key": "story", "manifest_slug": "story", "chapter_count": 2,
             "chapters": [{"id": "opening", "order": 1}, {"id": "ending", "order": 2}]},
            {"package_key": "retired-alias", "manifest_slug": "retired-alias",
             "chapter_count": 0, "chapters": []},
        ],
    }
    actual = {
        "story": {"slug": "story", "chapter_count": 2,
                  "chapters": [{"id": "opening", "order": 1}, {"id": "ending", "order": 2}]},
        "retired-alias": {"slug": "retired-alias", "chapter_count": 0, "chapters": []},
    }
    if mutation is None:
        assert_controlled_inventory(actual, inventory)
        return
    if mutation == "missing_package":
        del actual["story"]
    elif mutation == "missing_zero_chapter_alias":
        del actual["retired-alias"]
    elif mutation == "unexpected_package":
        actual["unexpected"] = deepcopy(actual["story"])
    elif mutation == "same_count_substitution":
        actual["replacement"] = actual.pop("story")
    elif mutation == "wrong_manifest_slug":
        actual["story"]["slug"] = "different-story"
    elif mutation == "wrong_count":
        actual["story"]["chapter_count"] = 1
    elif mutation == "renamed_chapter":
        actual["story"]["chapters"][1]["id"] = "other-ending"
    elif mutation == "duplicate_chapter":
        actual["story"]["chapters"][1] = deepcopy(actual["story"]["chapters"][0])
    elif mutation == "reordered_chapters":
        actual["story"]["chapters"].reverse()
    elif mutation == "changed_order":
        actual["story"]["chapters"][0]["order"] = 3
    with pytest.raises(AssertionError):
        assert_controlled_inventory(actual, inventory)
