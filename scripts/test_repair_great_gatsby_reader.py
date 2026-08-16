import importlib.util
from pathlib import Path
P=Path(__file__).with_name("repair_great_gatsby_reader.py"); S=importlib.util.spec_from_file_location("gatsby",P)
M=importlib.util.module_from_spec(S); S.loader.exec_module(M)
def planned(): return M.plan("2026-08-16T00:00:00Z")
def test_source_chapters_and_boundaries():
    assert M.sha(M.src())==M.SOURCE_SHA
    c=M.chapters(); assert [x["title"] for x in c]==list(M.ROMANS)
    assert c[0]["text"].startswith(M.OPENING) and c[-1]["text"].endswith(M.ENDING)
    assert sum(x["semantic_blocks"] for x in c)<1800
def test_private_rights_cover_audio_and_sync_truth():
    r,e=planned(); p=M.json.loads(r[M.PACK/"public_book.json"]); s=M.json.loads(r[M.PACK/"source_evidence.json"])
    a=M.json.loads(r[M.PACK/"approval_evidence.json"]); h=M.json.loads(r[M.PACK/"highlight_sync.json"])
    assert s["publication_region"]=="IN" and s["author_death_year"]==1940 and "Section 22" in s["rights_basis"]
    assert p["publication_status"]=="READER_APPROVAL_REQUIRED" and not p["isPublic"] and not p["cover_gate_passed"]
    assert not a["approved_to_publish"] and a["release_blockers"]==["exact_slug_graphical_cover_not_proven"]
    assert h["chapters"]==[] and not h["audio_enabled"] and not e["preview_rendered"]
def test_mirror_manifest_and_determinism():
    a,e=planned(); b,f=planned(); assert a==b and e==f and a[M.RAW]==M.src()
    rel={p.relative_to(M.PACK) for p in a if p.is_relative_to(M.PACK)}
    for r in rel: assert a[M.PACK/r]==a[M.BACKEND/r]
    files={x["file"] for x in M.json.loads(a[M.PACK/"checksum_manifest.json"])["files"]}
    assert "checksum_manifest.json" not in files and "reader_repair_evidence.json" in files
    assert {f"chapters/chapter-{i:03d}.json" for i in range(1,10)}<=files
