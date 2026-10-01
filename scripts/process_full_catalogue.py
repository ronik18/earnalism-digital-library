#!/usr/bin/env python3
"""Process every catalogue title into private, reproducible evidence.

This worker never uploads, publishes, changes a rights decision, or rewrites a
source package. Missing evidence is a completed assessment with an explicit
hold, rather than permission to manufacture a passing release.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from backend.publication_manifest import build_manifest, canonical_sha256, validate_manifest
from backend.catalog_truth import controlled_reader_validation_issues
from backend.rights_decision_gate import evaluate_runtime_path, load_production_registry, record_sha256

OUTPUT = "internal/earnalism_intelligence/full_catalogue_processing_20260930"
COMPONENTS = ("public_book", "reader_manifest", "source_evidence", "approval_evidence", "checksum_manifest", "publication_manifest")
BAD_HTML = re.compile(r"<(?:script|iframe|object|embed)\b", re.I)
# Category namespace metadata has a line/link/URL boundary. Ordinary prose such
# as Enchanted April's "proper category:" is source content, not repository UI.
BOILERPLATE = re.compile(r"(?:START|END) OF (?:THE|THIS) PROJECT GUTENBERG|Gutenberg-tm|www\.gutenberg\.org|Download as|(?:^\s*|\[\[:?|/)Category:|Special:Export", re.I | re.M)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_object(path: Path) -> dict:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def rendered(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def package_checks(directory: Path) -> tuple[list[str], dict, list[dict]]:
    issues, chapter_hashes = [], []
    book = read_object(directory / "public_book.json")
    reader = read_object(directory / "reader_manifest.json")
    chapters = book.get("chapters") or []
    ids = [str(row.get("id") or "") for row in chapters]
    if not ids or len(set(ids)) != len(ids) or any(not value for value in ids):
        issues.append("CHAPTER_IDS_MISSING_OR_DUPLICATED")
    if reader.get("chapter_count") != len(chapters):
        issues.append("READER_CHAPTER_COUNT_MISMATCH")
    if [str(row.get("id") or "") for row in reader.get("chapters") or []] != ids:
        issues.append("READER_CHAPTER_INDEX_MISMATCH")
    for row in chapters:
        chapter_id = str(row.get("id") or "")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", chapter_id):
            issues.append("UNSAFE_CHAPTER_ID")
            continue
        path = directory / "chapters" / f"{chapter_id}.json"
        payload = read_object(path)
        content = str(payload.get("content") or "")
        actual_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        chapter_hashes.append({"id": chapter_id, "file_sha256": digest(path) if path.is_file() else "", "content_sha256": actual_hash})
        if not content.strip():
            issues.append(f"EMPTY_CHAPTER:{chapter_id}")
        if payload.get("id") != chapter_id:
            issues.append(f"CHAPTER_ID_MISMATCH:{chapter_id}")
        if payload.get("content_hash") and payload["content_hash"] != actual_hash:
            issues.append(f"CHAPTER_CONTENT_HASH_MISMATCH:{chapter_id}")
        if BAD_HTML.search(content):
            issues.append(f"UNSAFE_READER_HTML:{chapter_id}")
        if BOILERPLATE.search(content) or "\ufffd" in content:
            issues.append(f"READER_SOURCE_FURNITURE_OR_ENCODING_ERROR:{chapter_id}")
    checksum = read_object(directory / "checksum_manifest.json")
    if not isinstance(checksum.get("files"), list):
        issues.append("CHECKSUM_INDEX_MISSING")
    for entry in checksum.get("files") or []:
        relative = entry.get("file") if isinstance(entry, dict) else None
        if not isinstance(relative, str) or not relative:
            issues.append("CHECKSUM_ENTRY_INVALID")
            continue
        path = directory / relative
        if Path(relative).is_absolute() or ".." in Path(relative).parts or not path.resolve().is_relative_to(directory.resolve()):
            issues.append("UNSAFE_CHECKSUM_PATH")
            continue
        # Older bundles contain a legacy self-reference; do not rebind it.
        if relative == "checksum_manifest.json":
            continue
        if not path.is_file() or digest(path) != entry.get("sha256"):
            issues.append(f"RETAINED_CHECKSUM_MISMATCH:{relative}")
    files = {path.relative_to(directory).as_posix(): digest(path) for path in sorted(directory.rglob("*")) if path.is_file()}
    return sorted(set(issues)), files, chapter_hashes


def rights_checks(directory: Path, slug: str, registry: dict, revoked: frozenset, now: datetime) -> dict:
    record = read_object(directory / "rights_decision.json") or None
    components = {name: digest(directory / f"{name}.json") for name in COMPONENTS if (directory / f"{name}.json").is_file()}
    # This is an offline scope assessment, never evidence that a live request
    # obtained a trusted country assertion or a paid entitlement.
    verdicts = {}
    for action in ("catalog_cta", "reader_manifest", "reader_chapter"):
        verdict = evaluate_runtime_path(action, record=record, edition_id=slug, operator_id="reo-enterprise", country="IN", country_trusted=True, required_components=components, accepted_records=registry, revoked_decision_ids=revoked, now=now)
        verdicts[action] = {"passed": verdict.passed, "reasons": list(verdict.reasons)}
    return {
        "decision_id": (record or {}).get("decision_id"),
        "registry_bound": bool(record and registry.get(record.get("decision_id")) == record_sha256(record)),
        "offline_india_text_scope_passed": len(components) == len(COMPONENTS) and all(row["passed"] for row in verdicts.values()),
        "runtime_actions": verdicts,
        "production_request_verified": False,
    }


def process(root: Path, as_of: str) -> tuple[dict[str, str], dict]:
    now = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    if now.tzinfo is None:
        raise ValueError("as-of must include a timezone")
    inventory = root / "earnalism_book_inventory_for_launch.csv"
    with inventory.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_slug = {row["slug"]: row for row in rows}
    if len(by_slug) != len(rows):
        raise ValueError("duplicate catalogue slug")
    packages = {path.parent.name: path.parent for path in (root / "data/controlled_publications").glob("*/public_book.json")}
    backend = {path.parent.name: path.parent for path in (root / "backend/data/controlled_publications").glob("*/public_book.json")}
    contents = {path.parent.name: path.parent for path in (root / "content/books").glob("*/book.json")}
    registry_path = root / "backend/data/rights_decision_registry.json"
    registry, revoked = load_production_registry(registry_path)
    outputs, titles = {}, []
    for slug in sorted(set(by_slug) | set(packages) | set(backend) | set(contents)):
        row = by_slug.get(slug, {})
        directory = packages.get(slug) or backend.get(slug)
        title = {"slug": slug, "title": row.get("title", slug), "language": row.get("language", "unknown"), "processing_status": "ASSESSED", "uploaded": False, "new_publication_authorized": False, "audio_activation_authorized": False}
        if not directory:
            title.update(state="EXTERNAL_ACTION_REQUIRED", blockers=["CLEARED_SOURCE_AND_READER_PACKAGE_MISSING"], chapter_count=0, next_action="Supply the exact cleared source edition, manuscript, source/license evidence, cover provenance and accepted text-use decision; then run draft preparation.")
            titles.append(title)
            continue
        book = read_object(directory / "public_book.json")
        title.update(title=book.get("title") or title["title"], language=(read_object(directory / "reader_manifest.json").get("language") or title["language"]))
        issues, files, chapter_hashes = package_checks(directory)
        manifest = build_manifest(directory, generated_at=as_of)
        blockers = list(manifest["reader_release"]["blockers"]) + issues
        active = backend.get(slug) or directory
        rights = rights_checks(active, slug, registry, revoked, now)
        runtime_issues = list(controlled_reader_validation_issues(slug, str(active)))
        active_issues, active_files, _ = package_checks(active)
        existing = read_object(active / "publication_manifest.json")
        live = bool(rights["offline_india_text_scope_passed"] and not runtime_issues and not active_issues and existing.get("reader_release", {}).get("exposed") is True and not validate_manifest(existing))
        if live:
            manifest = existing
            blockers = []
            state = "READER_ONLY_LIVE_APPROVED"
        else:
            blockers.extend(reason for verdict in rights["runtime_actions"].values() for reason in verdict["reasons"])
            if not rights["offline_india_text_scope_passed"]:
                blockers.append("ACCEPTED_HASH_BOUND_TEXT_USE_DECISION_REQUIRED")
            manifest["reader_release"].update(status="BLOCKED", exposed=False, blockers=sorted(set(blockers)))
            # Private derived files never resurrect historical audio claims.
            manifest["audio_release"].update(status="NOT_REQUESTED", exposed=False, required_for_reader_release=False)
            manifest["manifest_sha256"] = canonical_sha256(manifest)
            state = "EXTERNAL_ACTION_REQUIRED"
        schema_issues = validate_manifest(manifest)
        if schema_issues:
            raise ValueError(f"Cannot produce a valid private manifest for {slug}: {schema_issues}")
        root_decision = read_object(directory / "rights_decision.json")
        historical_decision = bool(root_decision and not registry.get(root_decision.get("decision_id")) == record_sha256(root_decision))
        title.update(state=state, chapter_count=len(chapter_hashes), blockers=sorted(set(blockers)), private_manifest=f"manifests/{slug}.json", active_package=active.relative_to(root).as_posix(), prepared_package=directory.relative_to(root).as_posix(), rights=rights, retained_package_issues=issues, historical_root_decision=historical_decision, next_action="Verify production Reader delivery and protected-page entitlement from a trusted India context." if live else "Resolve the listed source, content, cover and accepted-decision gaps; rerun the processor. This design approval does not resolve title-specific evidence.")
        outputs[f"manifests/{slug}.json"] = rendered({"schema": "earnalism.private-catalogue-processing.v1", "publication_authority": False, "input_files_sha256": files, "active_files_sha256": active_files, "chapter_content_hashes": chapter_hashes, "publication_manifest": manifest, "rights_assessment": rights})
        titles.append(title)
    summary = {
        "schema": "earnalism.full-catalogue-processing.v1", "as_of": as_of,
        "scope": "all inventory, controlled and content-package slugs",
        "processing_status": "COMPLETE_FOR_AVAILABLE_INPUTS", "full_catalogue_publication_complete": False,
        "inventory_rows": len(rows), "title_count": len(titles), "prepared_package_count": len(outputs),
        "chapter_count": sum(title["chapter_count"] for title in titles),
        "state_counts": dict(sorted(Counter(title["state"] for title in titles).items())),
        "new_upload_count": 0, "new_publication_count": 0, "audio_activation_count": 0,
        "missing_package_count": sum(not title.get("private_manifest") for title in titles),
        "input_catalogue_sha256": digest(inventory), "rights_registry_sha256": digest(registry_path),
        "public_package_mutations": 0,
        "titles": titles,
    }
    outputs["catalogue_state.json"] = rendered(summary)
    outputs["draft_import_manifest.json"] = rendered({"schema": "earnalism.full-catalogue-draft-intake.v1", "mode": "draft", "upload_execution": "NOT_REQUESTED_NO_NEW_PASSING_ACCEPTED_TITLES", "books": [{"slug": title["slug"], "title": title["title"], "package": title.get("prepared_package"), "eligible_for_new_upload": False, "skip_reasons": title["blockers"] or ["ALREADY_CONTROLLED_LIVE_APPROVED"]} for title in titles]})
    outputs["processing_checksums.json"] = rendered({"schema": "earnalism.private-processing-checksums.v1", "files": {name: hashlib.sha256(value.encode("utf-8")).hexdigest() for name, value in sorted(outputs.items())}})
    return outputs, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--as-of", default="2026-09-30T00:00:00Z")
    parser.add_argument("--check", action="store_true", help="Verify every retained processing artifact without mutation.")
    args = parser.parse_args()
    root = args.root.resolve()
    output = (args.output or root / OUTPUT).resolve()
    if not output.is_relative_to(root / "internal/earnalism_intelligence"):
        parser.error("processing outputs must remain in the private intelligence directory")
    outputs, summary = process(root, args.as_of)
    if args.check:
        mismatches = [name for name, value in outputs.items() if not (output / name).is_file() or (output / name).read_text(encoding="utf-8") != value]
        unexpected = [path.relative_to(output).as_posix() for path in output.rglob("*.json") if path.relative_to(output).as_posix() not in outputs]
        if mismatches or unexpected:
            print(rendered({"status": "FAIL", "mismatched_artifacts": mismatches, "unexpected_artifacts": unexpected}))
            return 1
    else:
        for name, value in outputs.items():
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value, encoding="utf-8")
    print(rendered({key: summary[key] for key in ("processing_status", "title_count", "prepared_package_count", "chapter_count", "state_counts", "missing_package_count", "new_upload_count", "new_publication_count", "audio_activation_count")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
