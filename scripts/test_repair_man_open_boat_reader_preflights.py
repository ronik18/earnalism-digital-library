from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("repair_man_open_boat_reader_preflights.py")
SPEC = importlib.util.spec_from_file_location("repair_man_open_boat_reader_preflights", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def decoded(replacements: dict[Path, bytes], path: Path) -> dict:
    return json.loads(replacements[path].decode("utf-8"))


def test_exact_boundaries_hashes_counts_and_words() -> None:
    for spec in MODULE.SPECS:
        replacements, evidence = MODULE.build_title(spec, "2026-08-16T00:00:00Z")
        content_path = MODULE.ROOT / "content" / "books" / spec.slug / "chapters" / spec.chapter_name
        text = decoded(replacements, content_path)["content"]
        existing = MODULE.read_json(content_path)["content"]

        assert MODULE.normalized(text) == MODULE.normalized(MODULE.narrative_slice(existing, spec))
        assert text.startswith(spec.start)
        assert text.endswith(spec.endpoint)
        assert MODULE.sha256_text(text) == spec.new_sha256
        assert len(re.split(r"\n\s*\n", text)) == spec.semantic_blocks
        assert evidence["word_count"] == spec.expected_words
        assert evidence["remote_media_mutated"] is False


def test_man_preserves_epigraph_contract_and_hymn() -> None:
    spec = next(item for item in MODULE.SPECS if item.slug == "the-man-who-would-be-king")
    replacements, _ = MODULE.build_title(spec, "2026-08-16T00:00:00Z")
    path = MODULE.ROOT / "content" / "books" / spec.slug / "chapters" / spec.chapter_name
    text = decoded(replacements, path)["content"]

    assert text.startswith("“Brother to a Prince and fellow to a beggar if he be found worthy.”")
    assert "(One) That me and you will settle this matter together:\ni.e., to be Kings of Kafiristan." in text
    assert "The Son of Man goes forth to war,\nA golden crown to gain;" in text
    assert "Published by Brentano’s" not in text


def test_open_boat_preserves_subtitle_sections_and_verse_only() -> None:
    spec = next(item for item in MODULE.SPECS if item.slug == "the-open-boat")
    replacements, _ = MODULE.build_title(spec, "2026-08-16T00:00:00Z")
    path = MODULE.ROOT / "content" / "books" / spec.slug / "chapters" / spec.chapter_name
    text = decoded(replacements, path)["content"]

    assert text.startswith("A Tale intended to be after the Fact.\nBeing the Experience of Four Men from\nthe Sunk Steamer 'Commodore'")
    assert "A soldier of the Legion lay dying in Algiers,\nThere was lack of woman's nursing" in text
    assert "\n\nI\n\nNone of them knew the colour of the sky." in text
    assert text.endswith(spec.endpoint)
    assert "A MAN AND SOME OTHERS" not in text


def test_packages_are_audio_hidden_complete_and_mirrored() -> None:
    for spec in MODULE.SPECS:
        replacements, evidence = MODULE.build_title(spec, "2026-08-16T00:00:00Z")
        public = decoded(replacements, MODULE.CONTROLLED_ROOT / spec.slug / "public_book.json")
        sync = decoded(replacements, MODULE.CONTROLLED_ROOT / spec.slug / "highlight_sync.json")

        assert public["audio_enabled"] is False
        assert public["audiobook_enabled"] is False
        assert "audiobook_assets" not in public
        assert sync["chapters"] == []
        assert evidence["root_backend_byte_parity"] is True
        for relative in MODULE.CONTROLLED_FILES:
            assert replacements[MODULE.CONTROLLED_ROOT / spec.slug / relative] == replacements[MODULE.BACKEND_ROOT / spec.slug / relative]
