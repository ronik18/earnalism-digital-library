from __future__ import annotations

import json
from pathlib import Path

from scripts import reconcile_batch2_live_audio_truth as reconciliation


ROOT = Path(__file__).resolve().parents[1]


def test_reconciliation_is_idempotent_and_checksum_bound():
    replacements = reconciliation.build_replacements()
    reconciliation.verify(replacements)

    for slug, candidate in reconciliation.CANDIDATES.items():
        root = ROOT / "data" / "controlled_publications" / slug
        backend = ROOT / "backend" / "data" / "controlled_publications" / slug
        approval = json.loads(replacements[root / "approval_evidence.json"])
        public = json.loads(replacements[root / "public_book.json"])
        reader = json.loads(replacements[root / "reader_manifest.json"])
        manifest = json.loads(replacements[root / "publication_manifest.json"])

        assert approval["candidate_fingerprint"] == candidate["fingerprint"]
        assert approval["audio_sha256"] == candidate["audio_sha256"]
        assert approval["audio_public_release"] == "PUBLIC_AUDIO_RELEASE_APPROVED"
        assert public["audiobook_release_mode"] == "SERVER_OWNED_CONVEYOR"
        assert "audiobook_assets" not in public
        assert "backblazeb2.com" not in json.dumps(public)
        assert reader["audio_enabled"] is True
        assert manifest["audio_release"]["status"] == "APPROVED"
        assert manifest["audio_release"]["exposed"] is True
        assert manifest["audio_release"]["discovery_exposed"] is False
        assert replacements[root / "checksum_manifest.json"] == replacements[backend / "checksum_manifest.json"]

    assert reconciliation.launch_replacements() == {}


def test_public_evidence_exposes_only_same_origin_api_route():
    replacements = reconciliation.build_replacements()
    for slug in reconciliation.CANDIDATES:
        root = ROOT / "data" / "controlled_publications" / slug
        evidence = json.loads(replacements[root / "production_audio_evidence.json"])
        approval = json.loads(replacements[root / "approval_evidence.json"])

        assert evidence["production_api"]["audio_url"] == f"/api/reader/book/{slug}/audiobook"
        assert approval["endpoint_url"] == f"/api/reader/book/{slug}/audiobook"
        assert "backblazeb2.com" not in json.dumps(evidence["production_api"])
