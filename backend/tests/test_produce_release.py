from __future__ import annotations

import hashlib
import json

from scripts.produce_release import evaluate


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(tmp_path):
    manuscript = tmp_path / "manuscript.txt"
    preview = tmp_path / "reader.html"
    manuscript.write_text("approved text", encoding="utf-8")
    preview.write_text("<p>approved text</p>", encoding="utf-8")
    profile = {"model": "test-model", "voice": "test-voice", "profile_sha256": "profile-hash"}
    return {
        "slug": "pilot",
        "rights": {
            "source_url": "https://example.test/source",
            "source_license": "public domain",
            "commercial_use": "APPROVED",
            "territories": ["IN"],
            "source_sha256": "a" * 64,
        },
        "manuscript": {"path": manuscript.name, "sha256": _sha(manuscript)},
        "reader": {"preview_path": preview.name, "preview_sha256": _sha(preview)},
        "audio": profile,
        "automated_checks": {name: {"status": "PASS"} for name in ("audio_artifacts", "synchronization", "checksums", "staging", "browser", "production")},
    }, profile


def test_missing_human_packets_are_the_only_pending_gates(tmp_path):
    manifest, _ = _manifest(tmp_path)
    report = evaluate(manifest, tmp_path, None, None)
    assert report["release_status"] == "BLOCKED"
    assert report["human_gates"]["reader_render"]["status"] == "PENDING"
    assert report["human_gates"]["audiobook_profile"]["status"] == "PENDING"
    assert all(item["status"] == "PASS" for item in report["automated_checks"].values())


def test_matching_packets_allow_live_when_automation_passes(tmp_path):
    manifest, profile = _manifest(tmp_path)
    reader_path = tmp_path / "reader-approval.json"
    audio_path = tmp_path / "audio-approval.json"
    reader_path.write_text(json.dumps({"status": "APPROVED", "slug": "pilot", "manuscript_sha256": manifest["manuscript"]["sha256"], "preview_sha256": manifest["reader"]["preview_sha256"]}), encoding="utf-8")
    audio_path.write_text(json.dumps({"status": "APPROVED", "slug": "pilot", **profile}), encoding="utf-8")
    report = evaluate(manifest, tmp_path, reader_path, audio_path)
    assert report["release_status"] == "LIVE"


def test_public_access_does_not_substitute_for_rights(tmp_path):
    manifest, _ = _manifest(tmp_path)
    manifest["rights"]["commercial_use"] = "PUBLICLY_ACCESSIBLE"
    report = evaluate(manifest, tmp_path, None, None)
    assert report["automated_checks"]["rights"]["status"] == "BLOCKED"
