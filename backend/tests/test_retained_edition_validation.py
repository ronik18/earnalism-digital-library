"""Offline fixtures; no application startup, database or production writes."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import retained_edition_validation as reuse
from publication_manifest import canonical_sha256
from rights_decision_gate import record_sha256


def digest(data):
    return sha256(data).hexdigest()


@pytest.fixture
def edition(tmp_path, monkeypatch):
    root = tmp_path / "edition"
    root.mkdir()
    def write(name, value):
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value), encoding="utf-8")
        return digest(p.read_bytes())
    source = b"Title Before. After. License"
    source_hash = digest(source)
    chapter = {"id": "chapter-001", "order": 1, "title": "One", "bookSlug": "fixture",
               "sourceSha256": source_hash, "content": "Before. After.",
               "content_hash": digest(b"Before. After.")}
    chapter_file = write("chapters/chapter-001.json", chapter)
    index = [{"id": chapter["id"], "order": 1, "title": "One", "language_hint": "en"}]
    public = {"slug": "fixture", "title": "Fixture", "author": "Owner", "chapters": index}
    write("public_book.json", public)
    write("reader_manifest.json", {**public, "language": "en", "chapter_count": 1})
    write("source_evidence.json", {"slug": "fixture", "source_name": "Exact fixture edition",
          "source_hash": source_hash, "content_hash": "1" * 64})
    match = {"id": "chapter-001", "start": 6, "length": 14, "source_gap_before": "Title "}
    write("source_integrity_validation.json", {"slug": "fixture", "source_sha256": source_hash,
          "source_hash_exact": True, "unclassified_narrative_gaps": [], "chapter_count": 1,
          "matched_chapters": [{**match, "content_sha256": chapter["content_hash"]}],
          "tail_sha256": digest(b" License")})
    reviews = {}
    for name, value in {
        "review_a": {"source_proof_actual_reproduction": {"raw_sha256": source_hash,
                      "complete_ordered_bodies": [match], "all_gaps_reproduced": True,
                      "tail": " License"},
                      "fresh_actual_png_webp_visual_review": "PASS_LEGIBLE_THEMATIC_GRAPHICS_AND_CREDITS"},
        "review_b": {"visual_delivery": "PASS"},
    }.items():
        name_path = "evidence/" + name + ".json"
        reviews[name] = {"file": name_path, "sha256": write(name_path, {"slug": "fixture", **value})}
    write("approval_evidence.json", {"independent_reviews": reviews})
    assets = []
    for side in ("front", "back"):
        asset = {"kind": side}
        for prefix, suffix in (("source", "png"), ("delivery", "webp")):
            name = "covers/" + side + "." + suffix
            path = root / name
            path.parent.mkdir(exist_ok=True)
            Image.new("RGB", (40, 60), "maroon").save(path)
            asset.update({prefix + "_file": name if prefix == "source" else "edition/" + name,
                          prefix + "_sha256": digest(path.read_bytes()),
                          prefix + "_bytes": path.stat().st_size, prefix + "_dimensions": [40, 60]})
        assets.append(asset)
    write("cover_delivery_derivation.json", {"slug": "fixture", "assets": assets})
    policy = tmp_path / "internal/earnalism_intelligence/cover_acceptance_policy.json"
    policy.parent.mkdir(parents=True)
    policy.write_text(json.dumps({"performance_budget": {"card_thumbnail_target_kb": 80}}))
    write("publication_authorization.json", {"slug": "fixture", "edition": "Exact fixture edition",
          "publication_authorized": True, "audio_authorized": False, "territories": ["IN"],
          "scope": "TEXT_READER_CATALOG_METADATA_AND_EXACT_COVER_DISPLAY",
          "rights_decision_id": "local-fixture", "source_sha256": source_hash,
          "content_sha256": "1" * 64, "chapter_sha256": {"chapter-001": chapter["content_hash"]}})
    manifest = {"schema_name": "earnalism-publication-manifest", "schema_version": 1,
                "slug": "fixture", "content": {"source_hash": source_hash, "content_hash": "1" * 64,
                "chapter_count": 1, "chapters": [{**index[0], "sha256": chapter_file}]},
                "rights": {}, "reader_release": {"status": "NOT_REQUESTED", "exposed": False},
                "audio_release": {"status": "NOT_REQUESTED", "exposed": False,
                                  "required_for_reader_release": False},
                "commerce_release": {}, "artifacts": {}}
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    write("publication_manifest.json", manifest)
    write("checksum_manifest.json", {"files": [{"file": "source_integrity_validation.json",
          "sha256": digest((root / "source_integrity_validation.json").read_bytes())}]})
    write("owner_artwork_declaration.json", {"scope": "repository-owned test artwork"})
    # Only this isolated fixture uses a test registry. The adapter cannot accept
    # caller-supplied trust, and production always loads the shipped registry.
    components = {name: digest((root / (name + ".json")).read_bytes()) for name in
                  ("public_book", "reader_manifest", "source_evidence", "approval_evidence",
                   "publication_manifest", "publication_authorization", "cover_delivery_derivation",
                   "checksum_manifest", "owner_artwork_declaration")}
    decision = {"schema_version": "earnalism.rights-decision.v1", "decision_id": "local-fixture",
                "edition_id": "fixture", "operator_id": "reo-enterprise", "status": "ACCEPTED",
                "components": components, "territories": ["IN"],
                "uses": ["reader_delivery", "reading_pass_session", "cover_display"],
                "valid_from": "2026-01-01T00:00:00Z", "valid_until": "2027-01-01T00:00:00Z",
                "basis": "owner-original", "evidence_sha256": [components["source_evidence"]],
                "accepted_by": "test-reviewer", "conditions_satisfied": True}
    write("rights_decision.json", decision)
    monkeypatch.setattr(reuse, "load_production_registry", lambda: ({"local-fixture": record_sha256(decision)}, frozenset()))
    return tmp_path, root, source


def validate(edition, **kwargs):
    repo, root, source = edition
    return reuse.validate_retained_edition(root, repository_root=repo, source_bytes=source,
           now=datetime(2026, 10, 11, tzinfo=timezone.utc), **kwargs)


def test_reuse_executes_checks_without_approval_or_file_changes(edition):
    before = {str(p): digest(p.read_bytes()) for p in edition[0].rglob("*") if p.is_file()}
    result = validate(edition)
    assert result["phase_4"] == "CLEANED", result
    assert result["phase_5"] == "READY_FOR_REVIEW"
    assert result["phase_6"] == "PARTIAL_DRY_RUN"
    assert result["final_publication_qa"] == "UNVERIFIED"
    assert result["ready_for_release"] is False
    assert result["mutations"] == []
    assert before == {str(p): digest(p.read_bytes()) for p in edition[0].rglob("*") if p.is_file()}


@pytest.mark.parametrize("name", ["source_evidence.json", "source_integrity_validation.json",
    "approval_evidence.json", "publication_authorization.json", "rights_decision.json",
    "reader_manifest.json", "publication_manifest.json", "cover_delivery_derivation.json"])
@pytest.mark.parametrize("malformed", [False, True])
def test_missing_or_malformed_evidence_fails_closed(edition, name, malformed):
    path = edition[1] / name
    if malformed:
        path.write_text("[]")
    else:
        path.unlink()
    result = validate(edition)
    assert result["blockers"] and not result["ready_for_release"]
    assert result["phase_4"] == "UNVERIFIED"


@pytest.mark.parametrize("name", ["chapters/chapter-001.json", "covers/front.png",
    "covers/back.webp", "evidence/review_a.json", "publication_authorization.json",
    "source_integrity_validation.json"])
def test_changed_bound_files_rejected(edition, name):
    path = edition[1] / name
    path.write_bytes(path.read_bytes() + b" changed")
    result = validate(edition)
    assert result["blockers"] and not result["ready_for_release"]


def test_changed_source_is_not_rebound(edition):
    repo, root, source = edition
    result = reuse.validate_retained_edition(root, repository_root=repo, source_bytes=source + b"changed")
    assert "exact source digest mismatch" in result["blockers"]


def test_revoked_rights_rejected(edition, monkeypatch):
    records, _ = reuse.load_production_registry()
    monkeypatch.setattr(reuse, "load_production_registry", lambda: (records, frozenset({"local-fixture"})))
    assert validate(edition)["phase_4"] == "UNVERIFIED"


def test_no_self_approval_from_decision_file(edition, monkeypatch):
    monkeypatch.setattr(reuse, "load_production_registry", lambda: ({}, frozenset()))
    assert validate(edition)["phase_4"] == "UNVERIFIED"


def test_expired_rights_rejected(edition):
    repo, root, source = edition
    result = reuse.validate_retained_edition(root, repository_root=repo, source_bytes=source,
            now=datetime(2028, 1, 1, tzinfo=timezone.utc))
    assert result["phase_4"] == "UNVERIFIED"


def test_path_escape_rejected(tmp_path):
    with pytest.raises(ValueError):
        reuse._path(tmp_path, "../outside")


@pytest.mark.parametrize("field,value", [("order", 2), ("id", "other-edition"),
    ("sourceSha256", "f" * 64), ("content", "Lost text"), ("bookSlug", "other-book")])
def test_chapter_identity_structure_and_text_changes_fail_closed(edition, field, value):
    path = edition[1] / "chapters/chapter-001.json"
    chapter = json.loads(path.read_text())
    chapter[field] = value
    path.write_text(json.dumps(chapter))
    assert validate(edition)["phase_4"] == "UNVERIFIED"


def test_local_reuse_outcomes_do_not_clear_canonical_final_qa(edition):
    from publishing_workflow import WorkflowSignals, publishing_blockers
    result = validate(edition)
    blockers = publishing_blockers(WorkflowSignals(
        slug="fixture", title="Fixture", rights_tier="A", verification_status="APPROVED",
        publication_region="india", action_status="READY_FOR_GENERATION",
        ingestion_status=result["phase_4"], edition_generation_status=result["phase_5"],
        visual_status=result["phase_6"], audio_status="NOT_REQUESTED",
        qa_status=result["final_publication_qa"],
    ))
    assert blockers == ["QA pass is required."]
