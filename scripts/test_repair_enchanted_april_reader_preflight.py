import importlib.util
from pathlib import Path

PATH = Path(__file__).with_name("repair_enchanted_april_reader_preflight.py")
SPEC = importlib.util.spec_from_file_location("enchanted_april_repair", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def planned():
    return MODULE.plan("2026-08-16T00:00:00Z")


def test_exact_source_structure_and_normalized_equality():
    assert MODULE.sha(MODULE.source_bytes()) == MODULE.SOURCE_SHA
    chapters = MODULE.source_chapters()
    assert len(chapters) == 22
    assert [c["title"] for c in chapters] == [f"Chapter {i}" for i in range(1, 23)]
    assert sum(c["semantic_blocks"] for c in chapters) < 3000
    assert chapters[18]["source_restoration"] == MODULE.CHAPTER_19_RESTORATION
    assert chapters[21]["source_restoration"] == MODULE.CHAPTER_22_RESTORATION


def test_rights_cover_private_truth_and_audio_hidden():
    replacements, evidence = planned()
    public = MODULE.json.loads(replacements[MODULE.PACK / "public_book.json"])
    source = MODULE.json.loads(replacements[MODULE.PACK / "source_evidence.json"])
    approval = MODULE.json.loads(replacements[MODULE.PACK / "approval_evidence.json"])
    sync = MODULE.json.loads(replacements[MODULE.PACK / "highlight_sync.json"])
    assert source["publication_region"] == "IN" and source["author_death_year"] == 1941
    assert "Section 22" in source["rights_basis"] and evidence["public_domain_in_india_from"] == "2002-01-01"
    assert public["subtitle"] == "Complete Edition" and public["cover_gate_passed"]
    assert not public["isPublic"] and not public["isLive"] and not approval["approved_to_publish"]
    assert approval["release_blockers"] == ["fresh_checksum_bound_reader_approval_required"]
    assert sync["chapters"] == [] and not sync["audio_enabled"] and not evidence["preview_rendered"]


def test_preview_semantics_manifest_mirror_and_determinism():
    first, evidence_a = planned()
    second, evidence_b = planned()
    assert first == second and evidence_a == evidence_b and first[MODULE.RAW] == MODULE.source_bytes()
    reader = MODULE.json.loads(first[MODULE.PACK / "reader_manifest.json"])
    assert reader["preview_chapter_ids"] == ["chapter-001"]
    assert [row["is_preview"] for row in reader["chapters"]] == [True] + [False] * 21
    relative = {p.relative_to(MODULE.PACK) for p in first if p.is_relative_to(MODULE.PACK)}
    for rel in relative:
        assert first[MODULE.PACK / rel] == first[MODULE.BACKEND / rel]
    files = {row["file"] for row in MODULE.json.loads(first[MODULE.PACK / "checksum_manifest.json"])["files"]}
    assert "checksum_manifest.json" not in files
    assert "reader_repair_evidence.json" in files
    assert {f"chapters/chapter-{i:03d}.json" for i in range(1, 23)} <= files
