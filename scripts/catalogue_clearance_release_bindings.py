"""Separate exact historical non-cover scope from reviewed current release scope."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from backend.catalog_truth import controlled_reader_validation_issues
from scripts.bengali_rights_package_validator import checksum_manifest_matches
from backend.rights_decision_gate import evaluate_accepted_record, load_production_registry, record_sha256

HISTORICAL_BINDINGS = "internal/legal/catalogue_clearance_20261002/historical_noncover_bindings.v1.json"
REVIEWED_AUTHORITY = "internal/legal/catalogue_clearance_20261002/reviewed_release_authority_20261003.v1.json"
REQUIRED_COMPONENTS = ("public_book", "reader_manifest", "source_evidence", "approval_evidence", "checksum_manifest", "publication_manifest")
TEXT_USES = {"catalog_metadata", "cover_display", "reader_preview", "reader_delivery", "reading_pass_session", "reading_pass_renewal"}

def load(path):
    return json.loads(Path(path).read_text())

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def historical_noncover_binding(root, slug):
    row = load(Path(root) / HISTORICAL_BINDINGS)["titles"][slug]
    values = []
    for name in ("rights_decision", "publication_authorization"):
        raw = row[name + "_raw_utf8"].encode()
        assert hashlib.sha256(raw).hexdigest() == row[name + "_sha256"], (slug, name)
        values.append(json.loads(raw))
    return tuple(values)

def assert_reviewed_authority(root):
    root = Path(root)
    baseline = load(root / REVIEWED_AUTHORITY)
    for name, expected in baseline["authority_sha256"].items():
        assert sha(root / name) == expected, ("Unreviewed release authority change", name)
    launch = load(root / "data/controlled_launch.json")
    assert launch == load(root / "backend/data/controlled_launch.json")
    assert set(launch["live_approved_slugs"]) == set(baseline["titles"])
    assert launch["audio_enabled_slugs"] == []
    assert launch["public_audio_exposure_enabled"] is False
    assert launch["text_access_mode"] == "COMMERCIAL_ENTITLEMENT"
    assert set(launch["title_access_modes"].values()) == {"COMMERCIAL_ENTITLEMENT"}
    return baseline

def exact_record_component_hashes(root, slug, record, package, baseline=None):
    root, package = Path(root), Path(package)
    baseline = baseline or load(root / REVIEWED_AUTHORITY)
    if slug in baseline["titles"]:
        expected = baseline["titles"][slug]
        assert record_sha256(record) == expected["record_sha256"]
        paths = expected["component_paths"]
        retained = expected.get("unchanged_historical_external_asset_components", {})
        assert set(paths) | set(retained) == set(record["components"])
        assert all(record["components"][name] == digest for name, digest in retained.items())
        components = {name: sha(root / relative) for name, relative in paths.items()}
        # These earlier remote-only cover identities are pinned byte-unchanged
        # pre-PR511 accepted decisions, not fresh remote-byte observations.
        components.update(retained)
    else:
        # A local held non-cover decision has only fixed JSON components.
        assert "cover_display" not in record["uses"]
        components = {name: sha(package / (name + ".json")) for name in record["components"]}
    assert all(record["components"][name] == digest for name, digest in components.items()), (slug, "Exact component mismatch")
    return components

def assert_current_reviewed_release(root, slug, baseline=None):
    root = Path(root)
    baseline = baseline or assert_reviewed_authority(root)
    expected = baseline["titles"][slug]  # Never exempt an arbitrary exposed slug.
    package = root / "backend/data/controlled_publications" / slug
    if not package.is_dir():
        package = root / "data/controlled_publications" / slug
    assert controlled_reader_validation_issues(slug, str(package)) == (), (slug, "Invalid current complete Reader package")
    record = load(package / "rights_decision.json")
    accepted, revoked = load_production_registry(root / "backend/data/rights_decision_registry.json")
    assert record["decision_id"] == expected["decision_id"]
    assert record_sha256(record) == expected["record_sha256"]
    assert accepted.get(record["decision_id"]) == expected["record_sha256"]
    assert record["decision_id"] not in revoked
    assert record["status"] == "ACCEPTED" and record["territories"] == ["IN"]
    assert set(record["uses"]) == TEXT_USES
    components = exact_record_component_hashes(root, slug, record, package, baseline)
    components.update({name: sha(package / (name + ".json")) for name in REQUIRED_COMPONENTS})
    for use in TEXT_USES | {"audio_stream", "audio_download"}:
        for country, trusted in (("IN", True), ("US", True), ("IN", False)):
            verdict = evaluate_accepted_record(record, edition_id=slug, operator_id="reo-enterprise", country=country, country_trusted=trusted, use=use, required_components=components, accepted_records=accepted, revoked_decision_ids=revoked, now=datetime.now(timezone.utc))
            assert verdict.passed is (country == "IN" and trusted and use in TEXT_USES), (slug, use, country, trusted, verdict.reasons)
    # Validate active backend bodies and complete ordered manuscript, not only
    # unchanged metadata/manifest digest. Preserve legacy checksum-self entries
    # under the existing validator; all actual file entries still must match.
    assert checksum_manifest_matches(package), (slug, "Invalid active checksum bundle")
    public = load(package / "public_book.json")
    reader = load(package / "reader_manifest.json")
    source = load(package / "source_evidence.json")
    publication = load(package / "publication_manifest.json")
    ordered = sorted(public["chapters"], key=lambda row: row["order"])
    identities = [(row["id"], row["order"]) for row in ordered]
    assert identities == [(row["id"], row["order"]) for row in reader["chapters"]]
    assert len(identities) == reader["chapter_count"]
    assert [row["id"] for row in ordered] == [row["id"] for row in publication["content"]["chapters"]]
    bodies = []
    for row in ordered:
        chapter_path = package / "chapters" / (row["id"] + ".json")
        chapter = load(chapter_path)
        assert hashlib.sha256(chapter["content"].encode()).hexdigest() == chapter["content_hash"]
        bound = next(item for item in publication["content"]["chapters"] if item["id"] == row["id"])
        assert bound["sha256"] == sha(chapter_path)
        bodies.append(chapter["content"])
    aggregate = hashlib.sha256("\n\n".join(bodies).encode()).hexdigest()
    if record["decision_id"].endswith("exact-reader-cover-prospective-accepted") or slug in load(root / HISTORICAL_BINDINGS)["titles"]:
        assert public["content_hash"] == source["content_hash"] == aggregate
    # Older released whole-source hashes may differ from selected body hashes;
    # their exact source metadata and every body remain independently bound.

    assert publication["reader_release"]["status"] == "APPROVED" and publication["reader_release"]["exposed"] is True
    assert publication["audio_release"]["status"] == "NOT_REQUESTED" and publication["audio_release"]["exposed"] is False
    current_audio_documents = ("public_book", "reader_manifest", "approval_evidence") if record["decision_id"].endswith("exact-reader-cover-prospective-accepted") else ("public_book", "reader_manifest")
    for name in current_audio_documents:
        doc = load(package / (name + ".json"))
        assert doc.get("audio_enabled") is not True and doc.get("audiobook_enabled") is not True and doc.get("generate_audiobook") is not True
    authority = load(package / "publication_authorization.json") if (package / "publication_authorization.json").exists() else None
    if authority:
        assert authority.get("audio_authorized") is False
        assert authority.get("production_activation_authorized_by_this_file") is False
    return package
