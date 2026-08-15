from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("repair_canterville_reader_preflight.py")
SPEC = importlib.util.spec_from_file_location("repair_canterville_reader_preflight", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def decoded(replacements: dict[Path, bytes], path: Path) -> dict:
    return json.loads(replacements[path].decode("utf-8"))


def test_restores_exact_chapter_boundaries_and_words() -> None:
    replacements, evidence = MODULE.build_replacements("2026-08-16T00:00:00Z")
    assert evidence["chapter_count"] == 7
    assert evidence["word_count"] == 11293
    assert evidence["opening_sentence_restored_to_chapter_i"] is True
    for index, filename in enumerate(MODULE.CHAPTER_FILES):
        path = MODULE.CONTENT_ROOT / MODULE.SLUG / "chapters" / filename
        chapter = decoded(replacements, path)
        text = chapter["content"]
        assert chapter["title"] == MODULE.CHAPTER_TITLES[index]
        assert MODULE.sha256_text(text) == MODULE.NEW_SHA256[index]
        assert len(re.split(r"\n\s*\n", text)) == MODULE.SEMANTIC_BLOCKS[index]
        assert len(MODULE.WORD_RE.findall(text)) == MODULE.WORD_COUNTS[index]
    first = decoded(
        replacements,
        MODULE.CONTENT_ROOT / MODULE.SLUG / "chapters" / MODULE.CHAPTER_FILES[0],
    )["content"]
    last = decoded(
        replacements,
        MODULE.CONTENT_ROOT / MODULE.SLUG / "chapters" / MODULE.CHAPTER_FILES[-1],
    )["content"]
    assert first.startswith(MODULE.FIRST_SENTENCE_PREFIX)
    assert last.endswith(MODULE.ENDPOINT)


def test_public_reader_titles_are_normalized_and_audio_hidden() -> None:
    replacements, evidence = MODULE.build_replacements("2026-08-16T00:00:00Z")
    public = decoded(replacements, MODULE.CONTROLLED_ROOT / MODULE.SLUG / "public_book.json")
    reader = decoded(replacements, MODULE.CONTROLLED_ROOT / MODULE.SLUG / "reader_manifest.json")
    sync = decoded(replacements, MODULE.CONTROLLED_ROOT / MODULE.SLUG / "highlight_sync.json")

    assert [row["title"] for row in public["chapters"]] == list(MODULE.CHAPTER_TITLES)
    assert [row["title"] for row in reader["chapters"]] == list(MODULE.CHAPTER_TITLES)
    assert public["audio_enabled"] is False
    assert public["audiobook_enabled"] is False
    assert "audiobook_assets" not in public
    assert sync["chapters"] == []
    assert evidence["root_backend_byte_parity"] is True


def test_checksum_package_is_complete_and_mirrored() -> None:
    replacements, _ = MODULE.build_replacements("2026-08-16T00:00:00Z")
    manifest = decoded(
        replacements,
        MODULE.CONTROLLED_ROOT / MODULE.SLUG / "checksum_manifest.json",
    )
    assert len(manifest["files"]) == 12
    for row in manifest["files"]:
        relative = row["file"]
        assert replacements[MODULE.CONTROLLED_ROOT / MODULE.SLUG / relative] == replacements[MODULE.BACKEND_ROOT / MODULE.SLUG / relative]
