from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("repair_science_getting_rich_reader_preflight.py")
SPEC = importlib.util.spec_from_file_location("repair_science_getting_rich_reader_preflight", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def decoded(replacements: dict[Path, bytes], path: Path) -> dict:
    return json.loads(replacements[path].decode("utf-8"))


def build() -> tuple[dict[Path, bytes], set[Path], dict]:
    return MODULE.build("2026-08-16T00:00:00Z")


def test_exact_reader_boundary_and_publisher_advertising_removal() -> None:
    replacements, stale_paths, evidence = build()
    content_dir = MODULE.CONTENT_ROOT / MODULE.SLUG
    chapter_paths = sorted((content_dir / "chapters").glob("*.json"))
    chapter_paths = [path for path in chapter_paths if path.name != MODULE.OLD_CONTENT_AD.name]
    assert len(chapter_paths) == 18
    chapters = [decoded(replacements, path) for path in chapter_paths]
    assert chapters[0]["content"].startswith(MODULE.NARRATIVE_START)
    assert chapters[-1]["content"].endswith(MODULE.NARRATIVE_ENDPOINT)
    assert "FURTHER AIDS TOWARD GETTING RICH RIGHT" not in "\n".join(
        chapter["content"] for chapter in chapters
    )
    assert not chapters[-1]["content"].rstrip().endswith("* * * * *")
    assert evidence["metadata_word_count"] == 22649
    assert content_dir / MODULE.OLD_CONTENT_AD in stale_paths


def test_official_source_snapshot_and_india_rights_are_bound() -> None:
    replacements, _, evidence = build()
    content_dir = MODULE.CONTENT_ROOT / MODULE.SLUG
    controlled_dir = MODULE.CONTROLLED_ROOT / MODULE.SLUG
    source = decoded(replacements, controlled_dir / "source_evidence.json")
    book = decoded(replacements, content_dir / "book.json")
    assert evidence["source_snapshot_sha256"] == MODULE.SOURCE_SHA256
    assert evidence["upstream_source_sha256"] == MODULE.UPSTREAM_SOURCE_SHA256
    assert hashlib.sha256(replacements[content_dir / MODULE.RAW_RELATIVE]).hexdigest() == MODULE.SOURCE_SHA256
    assert source["source_hash"] == MODULE.SOURCE_SHA256
    assert source["source_hash_domain"] == (
        "official_plaintext_utf8_normalized_lf_no_trailing_space_exact_bytes"
    )
    assert source["upstream_source_sha256"] == MODULE.UPSTREAM_SOURCE_SHA256
    assert source["commercial_use_allowed"] is True
    assert source["publication_region"] == "IN"
    assert "31 December 1971" in source["rights_basis"]
    assert book["rightsTerritoryBasis"] == source["rights_basis"]


def test_root_backend_byte_parity_and_exact_checksum_set() -> None:
    replacements, _, evidence = build()
    controlled_dir = MODULE.CONTROLLED_ROOT / MODULE.SLUG
    backend_dir = MODULE.BACKEND_ROOT / MODULE.SLUG
    checksum = decoded(replacements, controlled_dir / "checksum_manifest.json")
    assert evidence["checksum_artifact_count"] == 23
    assert len(checksum["files"]) == 23
    assert all(row["file"] != "chapters/chapter-019.json" for row in checksum["files"])
    for row in checksum["files"]:
        relative = Path(row["file"])
        assert replacements[controlled_dir / relative] == replacements[backend_dir / relative]
    assert replacements[controlled_dir / "checksum_manifest.json"] == replacements[
        backend_dir / "checksum_manifest.json"
    ]


def test_reader_and_audio_fail_closed_until_fresh_approval() -> None:
    replacements, _, _ = build()
    controlled_dir = MODULE.CONTROLLED_ROOT / MODULE.SLUG
    approval = decoded(replacements, controlled_dir / "approval_evidence.json")
    public = decoded(replacements, controlled_dir / "public_book.json")
    reader = decoded(replacements, controlled_dir / "reader_manifest.json")
    sync = decoded(replacements, controlled_dir / "highlight_sync.json")
    assert approval["approved_to_publish"] is False
    assert approval["historical_approval_superseded"] is True
    assert approval["reader_public_release"] == "READER_APPROVAL_REQUIRED"
    assert public["publication_status"] == "READY_FOR_APPROVAL"
    assert public["isPublic"] is False
    assert public["audio_enabled"] is False
    assert public["audiobook_enabled"] is False
    assert reader["chapter_count"] == 18
    assert reader["audio_enabled"] is False
    assert sync["chapters"] == []
    assert sync["totalDurationMs"] == 0


def test_decision_history_and_ledger_are_idempotent() -> None:
    replacements, _, _ = build()
    history = decoded(
        replacements,
        MODULE.ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    )
    ledger = replacements[
        MODULE.ROOT / "internal/earnalism_intelligence/decision_ledger.jsonl"
    ].decode("utf-8")
    assert history["titles"][MODULE.SLUG]["latest_decision"] == (
        "READY_FOR_CHECKSUM_BOUND_READER_APPROVAL"
    )
    assert ledger.count(MODULE.DECISION_KEY) == 1
