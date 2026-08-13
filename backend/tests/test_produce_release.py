from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.produce_release import (
    AUTOMATED_CHECKS,
    canonical_hash,
    evaluate,
    execute_go_live,
)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(tmp_path):
    manuscript = tmp_path / "manuscript.txt"
    preview = tmp_path / "reader.html"
    manuscript.write_text("approved text", encoding="utf-8")
    preview.write_text("<p>approved text</p>", encoding="utf-8")
    evidence = tmp_path / "automated-evidence.json"
    evidence.write_text('{"status":"PASS"}', encoding="utf-8")
    samples = []
    normalized_samples = []
    for index in range(6):
        sample = tmp_path / f"sample-{index + 1}.mp3"
        sample.write_bytes(f"audio-{index + 1}".encode())
        sample_sha256 = _sha(sample)
        source_sha256 = f"{index + 1:064x}"
        samples.append(
            {
                "id": f"sample-{index + 1}",
                "path": sample.name,
                "sha256": sample_sha256,
                "source_sha256": source_sha256,
            }
        )
        normalized_samples.append(
            {
                "id": f"sample-{index + 1}",
                "sha256": sample_sha256,
                "source_sha256": source_sha256,
            }
        )
    audio = {
        "model": "test-model",
        "voice": "test-voice",
        "review_samples": samples,
        "sample_set_sha256": canonical_hash(normalized_samples),
    }
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
        "audio": audio,
        "automated_checks": {
            name: {
                "status": "PASS",
                "evidence_path": evidence.name,
                "evidence_sha256": _sha(evidence),
            }
            for name in AUTOMATED_CHECKS
        },
    }, audio


def _reader_approval(manifest):
    return {
        "status": "APPROVED",
        "approval_type": "READER_PREVIEW",
        "render_surface": "CONVERSATION",
        "preview_reviewed": True,
        "slug": "pilot",
        "approved_by": "Test Reviewer",
        "approved_at": "2026-08-13T12:00:00Z",
        "manuscript_sha256": manifest["manuscript"]["sha256"],
        "preview_sha256": manifest["reader"]["preview_sha256"],
    }


def _audio_approval(audio):
    return {
        "status": "APPROVED",
        "approval_type": "AUDIO_SAMPLE_SET",
        "render_surface": "CONVERSATION",
        "listened_all_samples": True,
        "every_fatal_flag_false": True,
        "slug": "pilot",
        "approved_by": "Test Reviewer",
        "approved_at": "2026-08-13T12:01:00Z",
        "sample_set_sha256": audio["sample_set_sha256"],
        "sample_count": 6,
        "model": audio["model"],
        "voice": audio["voice"],
        "owner_public_release_intent": True,
        "overall_score": 9.0,
        "confidence": 0.92,
        "dimension_scores": {
            "naturalness": 9.0,
            "pronunciation": 9.0,
            "expression": 9.0,
            "punctuation_pauses": 9.0,
            "pacing": 9.0,
            "silence_clipping": 9.0,
            "glitches": 9.0,
        },
    }


def test_missing_human_packets_are_the_only_pending_gates(tmp_path):
    manifest, _ = _manifest(tmp_path)
    report = evaluate(manifest, tmp_path, None, None)
    assert report["release_status"] == "BLOCKED"
    assert report["human_gates"]["reader_preview"]["status"] == "PENDING"
    assert report["human_gates"]["audio_samples"]["status"] == "PENDING"
    assert all(item["status"] == "PASS" for item in report["automated_checks"].values())
    assert report["conversation_review"]["reader_preview"] == str(
        (tmp_path / "reader.html").resolve()
    )
    assert len(report["conversation_review"]["audio_samples"]) == 6
    assert all(
        Path(path).is_absolute()
        for path in report["conversation_review"]["audio_samples"]
    )


def test_matching_conversation_packets_allow_live_when_automation_passes(tmp_path):
    manifest, audio = _manifest(tmp_path)
    reader_path = tmp_path / "reader-approval.json"
    audio_path = tmp_path / "audio-approval.json"
    reader_path.write_text(json.dumps(_reader_approval(manifest)), encoding="utf-8")
    audio_path.write_text(json.dumps(_audio_approval(audio)), encoding="utf-8")
    report = evaluate(manifest, tmp_path, reader_path, audio_path)
    assert report["release_status"] == "READY_FOR_GO_LIVE"


def test_two_approvals_trigger_automatic_go_live(tmp_path):
    manifest, audio = _manifest(tmp_path)
    manifest["audio_release_gate_status"] = "PASS"
    reader_path = tmp_path / "reader-approval.json"
    audio_path = tmp_path / "audio-approval.json"
    staging_path = tmp_path / "staging.json"
    reader_path.write_text(json.dumps(_reader_approval(manifest)), encoding="utf-8")
    audio_path.write_text(json.dumps(_audio_approval(audio)), encoding="utf-8")
    staging_path.write_text(
        json.dumps(
            {"passed": True, "release_eligible": False, "release_id": "stage-1"}
        ),
        encoding="utf-8",
    )
    report = evaluate(manifest, tmp_path, reader_path, audio_path)

    class FakePromoter:
        def promote(self, payload, *, execute):
            assert execute is True
            assert payload["slug"] == "pilot"
            return {"status": "LIVE", "passed": True, "network_calls_performed": 0}

    live = execute_go_live(
        report,
        manifest,
        reader_path,
        audio_path,
        staging_path,
        promoter=FakePromoter(),
    )

    assert live["release_status"] == "LIVE"


def test_auto_go_live_rejects_manifest_changed_after_evaluation(tmp_path):
    manifest, audio = _manifest(tmp_path)
    manifest["audio_release_gate_status"] = "PASS"
    reader_path = tmp_path / "reader-approval.json"
    audio_path = tmp_path / "audio-approval.json"
    staging_path = tmp_path / "staging.json"
    reader_path.write_text(json.dumps(_reader_approval(manifest)), encoding="utf-8")
    audio_path.write_text(json.dumps(_audio_approval(audio)), encoding="utf-8")
    staging_path.write_text(
        json.dumps(
            {"passed": True, "release_eligible": False, "release_id": "stage-1"}
        ),
        encoding="utf-8",
    )
    report = evaluate(manifest, tmp_path, reader_path, audio_path)
    manifest["voice_changed_after_review"] = True

    with pytest.raises(ValueError, match="changed after evaluation"):
        execute_go_live(
            report,
            manifest,
            reader_path,
            audio_path,
            staging_path,
            promoter=object(),
        )


def test_audio_gate_rejects_less_than_six_samples(tmp_path):
    manifest, _ = _manifest(tmp_path)
    manifest["audio"]["review_samples"] = manifest["audio"]["review_samples"][:5]

    report = evaluate(manifest, tmp_path, None, None)

    assert report["automated_checks"]["audio_review_samples"]["status"] == "BLOCKED"


def test_audio_gate_rejects_score_below_release_floor(tmp_path):
    manifest, audio = _manifest(tmp_path)
    reader_path = tmp_path / "reader-approval.json"
    audio_path = tmp_path / "audio-approval.json"
    reader_path.write_text(json.dumps(_reader_approval(manifest)), encoding="utf-8")
    approval = _audio_approval(audio)
    approval["dimension_scores"]["pacing"] = 8.8
    audio_path.write_text(json.dumps(approval), encoding="utf-8")

    report = evaluate(manifest, tmp_path, reader_path, audio_path)

    assert report["human_gates"]["audio_samples"]["status"] == "BLOCKED"


def test_public_access_does_not_substitute_for_rights(tmp_path):
    manifest, _ = _manifest(tmp_path)
    manifest["rights"]["commercial_use"] = "PUBLICLY_ACCESSIBLE"
    report = evaluate(manifest, tmp_path, None, None)
    assert report["automated_checks"]["rights"]["status"] == "BLOCKED"
