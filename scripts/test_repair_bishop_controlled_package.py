from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from backend.publication_manifest import _rights_book
from backend.rights_engine import evaluate_rights


SCRIPT = Path(__file__).with_name("repair_bishop_controlled_package.py")
SPEC = importlib.util.spec_from_file_location("repair_bishop_controlled_package", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def decoded(replacements: dict[Path, bytes], path: Path) -> dict:
    return json.loads(replacements[path].decode("utf-8"))


def test_reconciliation_preserves_manuscript_and_hides_audio() -> None:
    before = MODULE.sha256_file(MODULE.ROOT_PUBLICATION / "chapters" / "chapter-001.json")
    replacements, evidence = MODULE.build_replacements("2026-08-16T00:00:00Z")
    after = MODULE.sha256_bytes(
        replacements[MODULE.ROOT_PUBLICATION / "chapters" / "chapter-001.json"]
    )
    public = decoded(replacements, MODULE.ROOT_PUBLICATION / "public_book.json")
    sync = decoded(replacements, MODULE.ROOT_PUBLICATION / "highlight_sync.json")

    assert before == after
    assert evidence["remote_media_mutated"] is False
    assert public["audio_enabled"] is False
    assert public["audiobook_enabled"] is False
    assert "audiobook_assets" not in public
    assert "audiobook" not in public
    assert sync["chapters"] == []
    assert sync["audio_enabled"] is False


def test_reconciliation_binds_translator_rights_and_mirrors_bytes() -> None:
    replacements, _ = MODULE.build_replacements("2026-08-16T00:00:00Z")
    public = decoded(replacements, MODULE.ROOT_PUBLICATION / "public_book.json")
    source = decoded(replacements, MODULE.ROOT_PUBLICATION / "source_evidence.json")
    decision = evaluate_rights(_rights_book(public, source), current_year=2026)

    assert source["translator_name"] == "Constance Garnett"
    assert source["translator_death_year"] == 1946
    assert decision.approved is True
    for relative in (
        "approval_evidence.json",
        "chapters/chapter-001.json",
        "highlight_sync.json",
        "public_book.json",
        "reader_manifest.json",
        "source_evidence.json",
        "checksum_manifest.json",
    ):
        assert replacements[MODULE.ROOT_PUBLICATION / relative] == replacements[MODULE.BACKEND_PUBLICATION / relative]
