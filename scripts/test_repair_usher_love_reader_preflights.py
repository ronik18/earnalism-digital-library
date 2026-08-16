from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("repair_usher_love_reader_preflights.py")
SPEC = importlib.util.spec_from_file_location("repair_usher_love_reader_preflights", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def decoded(replacements: dict[Path, bytes], path: Path) -> dict:
    return json.loads(replacements[path].decode("utf-8"))


def test_reflows_preserve_words_order_and_exact_boundaries() -> None:
    for spec in MODULE.SPECS:
        replacements, evidence = MODULE.build_title(spec, "2026-08-16T00:00:00Z")
        content_path = MODULE.ROOT / "content" / "books" / spec.slug / "chapters" / spec.chapter_name
        repaired = decoded(replacements, content_path)["content"]
        existing = MODULE.read_json(content_path)["content"]

        if spec.source_new_sha256:
            assert MODULE.normalized(repaired) == MODULE.normalized(existing)
            assert "his shirt bosom. Similar were the donations from other grinning sailors." in repaired
        else:
            assert MODULE.normalized(repaired) == MODULE.normalized(existing)
        assert len(re.split(r"\n\s*\n", repaired)) == spec.semantic_blocks
        assert MODULE.sha256_text(repaired) == spec.new_sha256
        assert repaired.endswith(spec.endpoint)
        assert evidence["remote_media_mutated"] is False


def test_packages_are_audio_hidden_checksum_bound_and_mirrored() -> None:
    for spec in MODULE.SPECS:
        replacements, evidence = MODULE.build_title(spec, "2026-08-16T00:00:00Z")
        public = decoded(replacements, MODULE.CONTROLLED_ROOT / spec.slug / "public_book.json")
        sync = decoded(replacements, MODULE.CONTROLLED_ROOT / spec.slug / "highlight_sync.json")

        assert public["audio_enabled"] is False
        assert public["audiobook_enabled"] is False
        assert "audiobook_assets" not in public
        assert "audiobook" not in public
        assert sync["chapters"] == []
        assert evidence["root_backend_byte_parity"] is True
        for relative in MODULE.CONTROLLED_FILES:
            assert replacements[MODULE.CONTROLLED_ROOT / spec.slug / relative] == replacements[MODULE.BACKEND_ROOT / spec.slug / relative]


def test_preserves_usher_verse_and_footnote_and_love_opening_verse() -> None:
    usher = next(item for item in MODULE.SPECS if item.slug == "the-fall-of-the-house-of-usher")
    love = next(item for item in MODULE.SPECS if item.slug == "love-of-life")
    usher_files, _ = MODULE.build_title(usher, "2026-08-16T00:00:00Z")
    love_files, _ = MODULE.build_title(love, "2026-08-16T00:00:00Z")
    usher_text = decoded(
        usher_files,
        MODULE.ROOT / "content" / "books" / usher.slug / "chapters" / usher.chapter_name,
    )["content"]
    love_text = decoded(
        love_files,
        MODULE.ROOT / "content" / "books" / love.slug / "chapters" / love.chapter_name,
    )["content"]

    assert "Son coeur est un luth suspendu;\nSitot qu'on le touche il resonne." in usher_text
    assert usher_text.endswith(usher.endpoint)
    assert love_text.startswith('"This out of all will remain--\nThey have lived and have tossed:')
    assert "and thrust it into his shirt bosom. Similar were the donations from other grinning sailors." in love_text
    assert love_text.endswith(love.endpoint)


def test_love_source_correction_is_exact_and_checksum_bound() -> None:
    love = next(item for item in MODULE.SPECS if item.slug == "love-of-life")
    replacements, evidence = MODULE.build_title(love, "2026-08-16T00:00:00Z")
    raw_path = MODULE.ROOT / "content" / "books" / love.slug / "raw" / "source.txt"
    repaired_raw = replacements[raw_path].decode("utf-8")

    assert MODULE.sha256_text(repaired_raw) == love.source_new_sha256
    assert repaired_raw.count(love.source_new_fragment) == 1
    legacy_raw = repaired_raw.replace(love.source_new_fragment, love.source_old_fragment, 1)
    assert MODULE.sha256_text(legacy_raw) == love.source_old_sha256
    assert evidence["raw_source_corrected"] is True
    assert evidence["raw_source_mutated_this_run"] is False
    assert evidence["normalized_text_unchanged"] is False
    assert evidence["normalized_words_order_match_canonical_source"] is True
    assert evidence["old_source_hash"] == love.source_old_sha256
    assert evidence["new_source_hash"] == love.source_new_sha256
