from __future__ import annotations

import hashlib

from scripts.produce_release import self_heal


def test_self_heal_reuses_artifacts_and_revalidates(tmp_path):
    evidence = tmp_path / "sync-repair.json"
    evidence.write_text('{"status":"PASS"}', encoding="utf-8")
    evidence_sha = hashlib.sha256(evidence.read_bytes()).hexdigest()
    manifest = {
        "slug": "pilot",
        "rights": {
            "source_url": "https://example.test/source",
            "source_license": "public domain",
            "commercial_use": "APPROVED",
            "territories": ["IN"],
            "source_sha256": "a" * 64,
        },
        "manuscript": {"path": "missing", "sha256": "b" * 64},
        "reader": {"preview_path": "missing", "preview_sha256": "c" * 64},
        "audio": {"model": "m", "voice": "v", "profile_sha256": "p"},
        "automated_checks": {
            "audio_artifacts": {"status": "PASS"},
            "synchronization": {"status": "BLOCKED"},
            "checksums": {"status": "PASS"},
            "staging": {"status": "PASS"},
            "browser": {"status": "PASS"},
            "production": {"status": "PASS"},
        },
        "repair_strategies": {
            "synchronization": [
                {"id": "re-align-failed", "failure_class": "TRANSIENT", "failed_segments": ["p-2"]}
            ]
        },
    }

    def repair(**kwargs):
        assert kwargs["reuse_artifacts"] is True
        assert kwargs["failed_segments"] == ["p-2"]
        return {
            "status": "PASS",
            "evidence_path": evidence.name,
            "evidence_sha256": evidence_sha,
            "regenerated_segments": ["p-2"],
            "reused_artifacts": True,
        }

    report = self_heal(manifest, tmp_path, None, None, repair, 1)
    assert report["release_status"] == "BLOCKED"
    assert report["self_healing"]["stopped"] == "human approval gate pending or blocked"
    assert report["self_healing"]["attempts"] == []


def test_self_heal_does_not_retry_permanent_failure(tmp_path):
    manifest = {
        "slug": "pilot",
        "rights": {
            "source_url": "https://example.test/source",
            "source_license": "public domain",
            "commercial_use": "APPROVED",
            "territories": ["IN"],
            "source_sha256": "a" * 64,
        },
        "manuscript": {"path": "missing", "sha256": "b" * 64},
        "reader": {"preview_path": "missing", "preview_sha256": "c" * 64},
        "audio": {"model": "m", "voice": "v", "profile_sha256": "p"},
        "automated_checks": {name: {"status": "PASS"} for name in ("audio_artifacts", "synchronization", "checksums", "staging", "browser", "production")},
        "repair_strategies": {"audio_artifacts": [{"id": "bad", "failure_class": "PERMANENT"}]},
    }
    called = False

    def repair(**_kwargs):
        nonlocal called
        called = True
        return {}

    report = self_heal(manifest, tmp_path, None, None, repair, 3)
    assert called is False
    assert report["self_healing"]["attempts"] == []
