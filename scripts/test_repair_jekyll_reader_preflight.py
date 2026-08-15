from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("repair_jekyll_reader_preflight.py")
SPEC = importlib.util.spec_from_file_location("repair_jekyll_reader_preflight", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def decoded(replacements: dict[Path, bytes], path: Path) -> dict:
    return json.loads(replacements[path].decode("utf-8"))


def build() -> tuple[dict[Path, bytes], set[Path], dict]:
    return MODULE.build("2026-08-16T00:00:00Z")


def test_source_correct_ten_chapter_boundary() -> None:
    replacements, stale_paths, evidence = build()
    content_dir = MODULE.CONTENT_ROOT / MODULE.SLUG
    chapters = [
        decoded(replacements, content_dir / "chapters" / name)
        for name in MODULE.CONTENT_NAMES
    ]
    assert len(chapters) == 10
    assert chapters[0]["content"].startswith(MODULE.NARRATIVE_START)
    assert chapters[-1]["content"].endswith(MODULE.NARRATIVE_ENDPOINT)
    assert MODULE.SIGNATURE in chapters[7]["content"]
    assert chapters[8]["title"] == "DR. LANYON’S NARRATIVE"
    assert content_dir / "chapters" / MODULE.OLD_FALSE_CONTENT in stale_paths
    assert evidence["false_signature_chapter_removed"] is True


def test_corrected_reader_and_audio_fail_closed() -> None:
    replacements, _, _ = build()
    controlled_dir = MODULE.CONTROLLED_ROOT / MODULE.SLUG
    approval = decoded(replacements, controlled_dir / "approval_evidence.json")
    public = decoded(replacements, controlled_dir / "public_book.json")
    reader = decoded(replacements, controlled_dir / "reader_manifest.json")
    sync = decoded(replacements, controlled_dir / "highlight_sync.json")
    assert approval["approved_to_publish"] is False
    assert approval["historical_approval_superseded"] is True
    assert public["isPublic"] is False
    assert public["audio_enabled"] is False
    assert len(public["chapters"]) == 10
    assert reader["chapter_count"] == 10
    assert sync["chapters"] == []


def test_root_backend_packages_are_byte_identical() -> None:
    replacements, _, evidence = build()
    for slug, expected_count in ((MODULE.SLUG, 16), (MODULE.ALIAS_SLUG, 5)):
        root_dir = MODULE.CONTROLLED_ROOT / slug
        backend_dir = MODULE.BACKEND_ROOT / slug
        manifest = decoded(replacements, root_dir / "checksum_manifest.json")
        assert len(manifest["files"]) == expected_count
        for row in manifest["files"]:
            relative = Path(row["file"])
            assert replacements[root_dir / relative] == replacements[backend_dir / relative]
    assert evidence["root_backend_byte_parity"] is True


def test_duplicate_slug_is_inert_and_contains_no_audio_urls() -> None:
    replacements, _, evidence = build()
    alias_dir = MODULE.CONTROLLED_ROOT / MODULE.ALIAS_SLUG
    approval = decoded(replacements, alias_dir / "approval_evidence.json")
    public_bytes = replacements[alias_dir / "public_book.json"]
    public = json.loads(public_bytes)
    reader = decoded(replacements, alias_dir / "reader_manifest.json")
    assert approval["approved_to_publish"] is False
    assert approval["canonical_slug"] == MODULE.SLUG
    assert public["chapters"] == []
    assert public["isPublic"] is False
    assert public["audio_enabled"] is False
    assert b"cloudinary" not in public_bytes.lower()
    assert reader["chapter_count"] == 0
    assert evidence["duplicate_slug_inert"] is True


def test_ledger_and_history_are_idempotent() -> None:
    replacements, _, _ = build()
    history = decoded(
        replacements,
        MODULE.ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    )
    ledger = replacements[
        MODULE.ROOT / "internal/earnalism_intelligence/decision_ledger.jsonl"
    ].decode("utf-8")
    assert history["titles"][MODULE.SLUG]["reader_chapter_count"] == 10
    assert history["titles"][MODULE.ALIAS_SLUG]["canonical_slug"] == MODULE.SLUG
    assert ledger.count(MODULE.DECISION_KEY) == 1
