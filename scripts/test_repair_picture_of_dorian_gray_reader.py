import importlib.util
from pathlib import Path

PATH = Path(__file__).with_name("repair_picture_of_dorian_gray_reader.py")
SPEC = importlib.util.spec_from_file_location("dorian_repair", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def planned():
    return MODULE.plan("2026-08-16T00:00:00Z")


def test_exact_source_revised_edition_and_semantic_reflow():
    assert MODULE.sha(MODULE.source_bytes()) == MODULE.SOURCE_SHA
    chapters = MODULE.source_chapters()
    assert [c["title"] for c in chapters] == MODULE.HEADINGS
    assert len(chapters) == 21
    assert sum(c["semantic_blocks"] for c in chapters) < 3000
    assert chapters[-1]["text"].endswith("THE END")


def test_alias_is_strict_ordered_subset_and_recovery_is_bound():
    chapters = MODULE.source_chapters()
    proof = MODULE.alias_proof(chapters)
    assert proof["alias_is_exact_ordered_subsequence"]
    assert proof["matched_alias_token_count"] == proof["alias_narrative_token_count"]
    assert not proof["alias_contributes_legitimate_narrative_absent_from_canonical"]
    assert proof["canonical_tokens_omitted_by_alias"] == 408
    assert proof["retired_file_count"] > 40
    replacements, repair, obsolete = planned()
    tombstone = MODULE.json.loads(replacements[MODULE.TOMBSTONE])
    assert tombstone["retired_from_git_commit"] == MODULE.BASE_COMMIT
    assert tombstone["alias_proof"]["retired_tree_manifest_sha256"]
    assert set(MODULE.alias_files()) <= obsolete


def test_private_truth_rights_cover_block_and_audio_hidden():
    replacements, repair, _ = planned()
    public = MODULE.json.loads(replacements[MODULE.PACK / "public_book.json"])
    source = MODULE.json.loads(replacements[MODULE.PACK / "source_evidence.json"])
    approval = MODULE.json.loads(replacements[MODULE.PACK / "approval_evidence.json"])
    sync = MODULE.json.loads(replacements[MODULE.PACK / "highlight_sync.json"])
    assert source["publication_region"] == "IN" and source["author_death_year"] == 1900
    assert "Section 22" in source["rights_basis"] and repair["public_domain_in_india_from"] == "1961-01-01"
    assert not public["cover_gate_passed"] and "exact_slug_cover_provenance_required" in public["release_blockers"]
    assert not public["isPublic"] and not public["isLive"] and not approval["approved_to_publish"]
    assert sync["chapters"] == [] and not sync["audio_enabled"] and not repair["preview_rendered"]


def test_manifest_mirror_and_deterministic_plan():
    first, evidence_a, obsolete_a = planned()
    second, evidence_b, obsolete_b = planned()
    assert first == second and evidence_a == evidence_b and obsolete_a == obsolete_b
    reader = MODULE.json.loads(first[MODULE.PACK / "reader_manifest.json"])
    assert reader["chapter_count"] == 21 and reader["preview_chapter_ids"] == ["chapter-001"]
    assert [x["is_preview"] for x in reader["chapters"]] == [True] + [False] * 20
    relative = {p.relative_to(MODULE.PACK) for p in first if p.is_relative_to(MODULE.PACK)}
    for rel in relative:
        assert first[MODULE.PACK / rel] == first[MODULE.BACKEND / rel]
    files = {row["file"] for row in MODULE.json.loads(first[MODULE.PACK / "checksum_manifest.json"])["files"]}
    assert "checksum_manifest.json" not in files
    assert "reader_repair_evidence.json" in files
    assert {f"chapters/chapter-{i:03d}.json" for i in range(1, 22)} <= files
    for relative in ("package.json", "launch_title_public_naming_map.json",
                     "launch_title_public_naming_map.csv", "book_cover_art_briefs.json",
                     "scripts/prepare_english_25_title_batch.py"):
        assert MODULE.ALIAS not in first[MODULE.ROOT / relative].decode()
