import json
from pathlib import Path

from backend.domain.chapter_index import (
    CHAPTER_INDEX_CONTRACT_VERSION,
    build_chapter_index_entries,
    chapter_index_entry,
    normalize_chapter_display_title,
)


ROOT = Path(__file__).resolve().parents[2]
CONTROLLED_ROOT = ROOT / "backend" / "data" / "controlled_publications"


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


def test_catalog_wide_reader_indexes_are_complete_and_deterministic():
    manifests = sorted(CONTROLLED_ROOT.glob("*/reader_manifest.json"))
    assert len(manifests) == 79
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
    assert audited_chapters == 691
