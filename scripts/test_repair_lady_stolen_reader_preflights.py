from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

from backend.publication_manifest import _rights_book
from backend.rights_engine import evaluate_rights


SCRIPT = Path(__file__).with_name("repair_lady_stolen_reader_preflights.py")
SPEC = importlib.util.spec_from_file_location("repair_lady_stolen_reader_preflights", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def decoded(replacements: dict[Path, bytes], path: Path) -> dict:
    return json.loads(replacements[path].decode("utf-8"))


def test_reflows_preserve_words_order_and_exact_boundaries() -> None:
    for spec in MODULE.SPECS:
        replacements, evidence = MODULE.build_title(spec, "2026-08-16T00:00:00Z")
        content_path = MODULE.CONTENT_ROOT / spec.slug / "chapters" / spec.chapter_name
        repaired = decoded(replacements, content_path)["content"]
        existing = MODULE.read_json(content_path)["content"]

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
        for relative in (
            "approval_evidence.json",
            "chapters/chapter-001.json",
            "highlight_sync.json",
            "public_book.json",
            "reader_manifest.json",
            "source_evidence.json",
            "checksum_manifest.json",
        ):
            assert replacements[MODULE.CONTROLLED_ROOT / spec.slug / relative] == replacements[MODULE.BACKEND_ROOT / spec.slug / relative]


def test_lady_translation_rights_are_bound_and_approved() -> None:
    spec = next(item for item in MODULE.SPECS if item.slug == "the-lady-with-the-dog")
    replacements, _ = MODULE.build_title(spec, "2026-08-16T00:00:00Z")
    public = decoded(replacements, MODULE.CONTROLLED_ROOT / spec.slug / "public_book.json")
    source = decoded(replacements, MODULE.CONTROLLED_ROOT / spec.slug / "source_evidence.json")
    decision = evaluate_rights(_rights_book(public, source), current_year=2026)

    assert source["translator_name"] == "Constance Garnett"
    assert source["translator_death_year"] == 1946
    assert decision.approved is True
