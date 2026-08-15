from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("repair_most_dangerous_scandal_reader_preflights.py")
SPEC = importlib.util.spec_from_file_location("repair_most_dangerous_scandal_reader_preflights", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def decoded(replacements: dict[Path, bytes], path: Path) -> dict:
    return json.loads(replacements[path].decode("utf-8"))


def test_exact_boundaries_reflows_and_words() -> None:
    for spec in MODULE.SPECS:
        replacements, evidence = MODULE.build_title(spec, "2026-08-16T00:00:00Z")
        content_path = MODULE.CONTENT_ROOT / spec.slug / "chapters" / spec.chapter_name
        repaired = decoded(replacements, content_path)["content"]
        existing = MODULE.read_json(content_path)["content"]

        assert MODULE.normalized(repaired) == MODULE.normalized(MODULE.narrative_slice(existing, spec))
        assert repaired.startswith(spec.start)
        assert repaired.endswith(spec.endpoint)
        assert len(re.split(r"\n\s*\n", repaired)) == spec.semantic_blocks
        assert MODULE.sha256_text(repaired) == spec.new_sha256
        assert evidence["word_count"] == spec.expected_words
        assert evidence["remote_media_mutated"] is False


def test_most_dangerous_boilerplate_removed_and_attribution_bound() -> None:
    spec = next(item for item in MODULE.SPECS if item.slug == "the-most-dangerous-game")
    replacements, evidence = MODULE.build_title(spec, "2026-08-16T00:00:00Z")
    content_path = MODULE.CONTENT_ROOT / spec.slug / "chapters" / spec.chapter_name
    repaired = decoded(replacements, content_path)["content"]
    book = decoded(replacements, MODULE.CONTENT_ROOT / spec.slug / "book.json")
    public = decoded(replacements, MODULE.CONTROLLED_ROOT / spec.slug / "public_book.json")
    source = decoded(replacements, MODULE.CONTROLLED_ROOT / spec.slug / "source_evidence.json")

    assert "From Collier’s" not in repaired
    assert "This work is in the public domain" not in repaired
    assert book["required_attribution"] == MODULE.MOST_DANGEROUS_ATTRIBUTION
    assert public["requires_attribution"] is True
    assert public["requires_share_alike"] is True
    assert source["required_attribution"] == MODULE.MOST_DANGEROUS_ATTRIBUTION
    assert evidence["required_attribution_bound"] is True


def test_scandal_preserves_letter_structure() -> None:
    spec = next(item for item in MODULE.SPECS if item.slug == "a-scandal-in-bohemia")
    replacements, _ = MODULE.build_title(spec, "2026-08-16T00:00:00Z")
    content_path = MODULE.CONTENT_ROOT / spec.slug / "chapters" / spec.chapter_name
    repaired = decoded(replacements, content_path)["content"]

    assert "MY DEAR MR. SHERLOCK HOLMES,—You really did it very well." in repaired
    assert repaired.endswith("title of _the_ woman.")


def test_packages_are_audio_hidden_checksum_bound_and_mirrored() -> None:
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
