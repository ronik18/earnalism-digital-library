#!/usr/bin/env python3
"""Verify the held Bengali preparation batch and immutable release boundaries."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.publication_manifest import validate_manifest
from scripts.bengali_rights_package_validator import checksum_manifest_matches

PACKET = ROOT / "internal/legal/bengali_text_preparation_20261002"


def main() -> int:
    preparation = json.loads((PACKET / "prepared_slugs.json").read_text())
    report = json.loads((PACKET / "evidence_matrix.json").read_text())
    base = preparation["base_sha"]
    issues = []
    preserved = ["data/controlled_launch.json", "data/catalog_exclusions.json", "backend/data/rights_decision_registry.json"]
    for name in preserved:
        original = subprocess.check_output(["git", "show", f"{base}:{name}"], cwd=ROOT)
        if original != (ROOT / name).read_bytes():
            issues.append(f"Release authority changed: {name}")
    live = set(json.loads((ROOT / preserved[0]).read_text())["live_approved_slugs"])
    excluded = json.loads((ROOT / preserved[1]).read_text())["titles"]
    rows = {row["slug"]: row for row in report["titles"]}
    if len(rows) != 47 or len(preparation["slugs"]) != 46:
        issues.append("Expected 47 audited / 46 prepared held Bengali titles.")
    for slug in preparation["slugs"]:
        package = ROOT / "data/controlled_publications" / slug
        if slug in live or slug in excluded:
            issues.append(f"Prepared live/excluded title: {slug}")
        manifest = json.loads((package / "publication_manifest.json").read_text())
        issues += [f"{slug}: {issue}" for issue in validate_manifest(manifest)]
        if manifest["reader_release"]["exposed"] or manifest["reader_release"]["status"] != "BLOCKED" or manifest["audio_release"]["exposed"]:
            issues.append(f"{slug}: preparation exposed a release")
        if not checksum_manifest_matches(package):
            issues.append(f"{slug}: package checksums do not match")
        source_file = package / "source_evidence.json"
        source = json.loads(source_file.read_text())
        original_source = json.loads(subprocess.check_output(["git", "show", f"{base}:{source_file.relative_to(ROOT)}"], cwd=ROOT))
        for key in ("source_hash", "content_hash", "provenance_hash", "source_url"):
            if source.get(key) != original_source.get(key):
                issues.append(f"{slug}: immutable historical {key} changed")
        if source.get("verification_status") != "pending":
            issues.append(f"{slug}: preparation claimed approved rights")
        if manifest["artifacts"]["source_evidence"] != hashlib.sha256(source_file.read_bytes()).hexdigest():
            issues.append(f"{slug}: manifest source binding is stale")
        # Manuscript, art, Reader structure and audio metadata must stay identical.
        prefix = f"data/controlled_publications/{slug}/"
        names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", base, "--", prefix], cwd=ROOT, text=True).splitlines()
        for name in names:
            if name.endswith(("source_evidence.json", "checksum_manifest.json", "publication_manifest.json")):
                continue
            if subprocess.check_output(["git", "show", f"{base}:{name}"], cwd=ROOT) != (ROOT / name).read_bytes():
                issues.append(f"{slug}: preserved artifact changed: {name}")
        if rows[slug]["publication_authorization"] != "NOT_GRANTED_BY_THIS_AUDIT":
            issues.append(f"{slug}: audit claimed publication authority")
    for proposal in json.loads((PACKET / "rights_decision_proposals.json").read_text())["decisions"]:
        if proposal["status"] != "PROPOSED" or proposal["accepted_by"] or proposal["conditions_satisfied"] is not False:
            issues.append(f"{proposal['edition_id']}: proposed decision was accepted")
        if any("audio" in use or "listen" in use for use in proposal["uses"]):
            issues.append(f"{proposal['edition_id']}: proposal authorizes audio")
    print(json.dumps({"status": "FAIL" if issues else "PASS", "audited_titles": len(rows), "prepared_held_titles": len(preparation["slugs"]), "new_titles_activated": 0, "issues": issues}, indent=2))
    return bool(issues)


if __name__ == "__main__":
    raise SystemExit(main())
