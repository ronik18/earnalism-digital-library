from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("block_metamorphosis_copyrighted_translation.py")
SPEC = importlib.util.spec_from_file_location("block_metamorphosis_copyrighted_translation", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def decoded(replacements: dict[Path, bytes], path: Path) -> dict:
    return json.loads(replacements[path].decode("utf-8"))


def test_manuscript_is_preserved_and_translation_rights_fail_closed() -> None:
    replacements, evidence = MODULE.build("2026-08-16T00:00:00Z")
    content_dir = MODULE.CONTENT_ROOT / MODULE.SLUG
    controlled_dir = MODULE.CONTROLLED_ROOT / MODULE.SLUG

    assert evidence["decision"] == MODULE.RIGHTS_DECISION
    assert evidence["manuscript_content_changed"] is False
    for content_path, controlled_path in zip(
        sorted((content_dir / "chapters").glob("*.json")),
        sorted((controlled_dir / "chapters").glob("*.json")),
    ):
        assert MODULE.read_json(content_path)["content"] == MODULE.read_json(controlled_path)["content"]
        assert replacements[controlled_path] == controlled_path.read_bytes()

    source = decoded(replacements, controlled_dir / "source_evidence.json")
    approval = decoded(replacements, controlled_dir / "approval_evidence.json")
    assert source["translator_name"] == "David Wyllie"
    assert source["source_license"] == "COPYRIGHTED_TRANSLATION_PERMISSION_REQUIRED"
    assert source["commercial_use_allowed"] is False
    assert source["verification_status"] == "blocked"
    assert source["rights_reassessment"]["official_source_marks_copyrighted"] is True
    assert approval["approved_to_publish"] is False
    assert approval["reader_public_release"] == "READER_RELEASE_BLOCKED_RIGHTS"


def test_public_reader_audio_and_unmeasured_sync_are_hidden() -> None:
    replacements, _ = MODULE.build("2026-08-16T00:00:00Z")
    controlled_dir = MODULE.CONTROLLED_ROOT / MODULE.SLUG
    public = decoded(replacements, controlled_dir / "public_book.json")
    reader = decoded(replacements, controlled_dir / "reader_manifest.json")
    sync = decoded(replacements, controlled_dir / "highlight_sync.json")

    for key in ("isPublic", "isLive", "showInPublicLibrary", "allowPublicReading", "is_published"):
        assert public[key] is False
    assert public["audio_enabled"] is False
    assert public["audiobook_enabled"] is False
    assert public["publication_status"] == "RIGHTS_REVIEW_REQUIRED"
    assert reader["reader_release_status"] == "BLOCKED_RIGHTS"
    assert reader["audio_enabled"] is False
    assert sync["chapters"] == []
    assert sync["totalDurationMs"] == 0


def test_root_backend_packages_are_byte_identical_and_checksum_bound() -> None:
    replacements, _ = MODULE.build("2026-08-16T00:00:00Z")
    for relative in MODULE.CONTROLLED_FILES:
        root_path = MODULE.CONTROLLED_ROOT / MODULE.SLUG / relative
        backend_path = MODULE.BACKEND_ROOT / MODULE.SLUG / relative
        assert replacements[root_path] == replacements[backend_path]

    checksum = decoded(
        replacements,
        MODULE.CONTROLLED_ROOT / MODULE.SLUG / "checksum_manifest.json",
    )
    entries = {row["file"]: row["sha256"] for row in checksum["files"]}
    assert set(entries) == {
        "approval_evidence.json",
        "chapters/chapter-001.json",
        "chapters/chapter-002.json",
        "chapters/chapter-003.json",
        "highlight_sync.json",
        "public_book.json",
        "reader_manifest.json",
        "source_evidence.json",
    }


def test_decision_history_and_ledger_record_the_rights_block() -> None:
    replacements, _ = MODULE.build("2026-08-16T00:00:00Z")
    history = decoded(
        replacements,
        MODULE.ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    )
    ledger = replacements[
        MODULE.ROOT / "internal/earnalism_intelligence/decision_ledger.jsonl"
    ].decode("utf-8")

    assert history["titles"][MODULE.SLUG]["latest_decision"] == MODULE.RIGHTS_DECISION
    assert history["titles"][MODULE.SLUG]["public_reader_status"] == "HIDDEN_RIGHTS_BLOCKED"
    assert ledger.count(MODULE.DECISION_KEY) == 1
