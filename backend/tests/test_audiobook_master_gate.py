import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from audiobook_master_gate import (  # noqa: E402
    APPROVED_STATUS,
    MasterGateError,
    sha256_file,
    validate_master_packet,
)


def _evidence(tmp_path: Path, name: str) -> dict[str, str]:
    path = tmp_path / name
    path.write_text(f"evidence:{name}\n", encoding="utf-8")
    return {"path": name, "sha256": sha256_file(path)}


def _approved_packet(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "dracula.mp3"
    source.write_bytes(b"approved-full-book-master")
    master_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    evidence = [_evidence(tmp_path, "evidence.txt")]
    listening = {
        "status": "PASS",
        "master_sha256": master_sha256,
        "reviewed_duration_seconds": 1000,
        "overall_score": 9.2,
        "confidence": 0.95,
        "dimension_scores": {"naturalness": 9.1, "clarity": 9.3},
        "fatal_flags": [],
        "evidence": evidence,
    }
    packet = {
        "schema_version": "earnalism.audiobook-master-release-packet.v1",
        "book_slug": "dracula",
        "status": APPROVED_STATUS,
        "master": {
            "sha256": master_sha256,
            "bytes": source.stat().st_size,
            "duration_seconds": 1000,
        },
        "canonical_binding": {
            "status": "PASS",
            "canonical_source_sha256": "a" * 64,
            "candidate_source_sha256": "a" * 64,
            "evidence": evidence,
        },
        "rights": {
            gate: {
                "status": "PASS",
                "master_sha256": master_sha256,
                "evidence": evidence,
            }
            for gate in ("source_text", "derivative_audiobook", "voice_provider")
        },
        "canonical_alignment": {
            "status": "PASS",
            "master_sha256": master_sha256,
            "score": 9.9,
            "first_words_match": True,
            "last_words_match": True,
            "ordered_content_match": True,
            "missing_content_count": 0,
            "duplicated_content_count": 0,
            "reordered_content_count": 0,
            "evidence": evidence,
        },
        "listening_qa": {
            "human": listening,
            "accessibility": listening,
        },
        "owner_release_approval": {
            "status": APPROVED_STATUS,
            "master_sha256": master_sha256,
            "approved_by": "owner-test",
            "approved_at": "2026-08-12T00:00:00Z",
            "production_release_authorized": False,
            "evidence": evidence,
        },
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    return packet_path, source


def test_approved_packet_binds_exact_master(tmp_path: Path) -> None:
    packet_path, source = _approved_packet(tmp_path)

    result = validate_master_packet(
        packet_path,
        source_path=source,
        expected_slug="dracula",
    )

    assert result["status"] == APPROVED_STATUS
    assert result["master_sha256"] == sha256_file(source)
    assert result["packet_sha256"] == sha256_file(packet_path)


def test_owner_approval_cannot_be_inferred(tmp_path: Path) -> None:
    packet_path, source = _approved_packet(tmp_path)
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["owner_release_approval"]["status"] = "MISSING"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    with pytest.raises(MasterGateError) as error:
        validate_master_packet(packet_path, source_path=source, expected_slug="dracula")

    assert "OWNER_RELEASE_APPROVAL_MISSING" in error.value.blockers


def test_master_checksum_mismatch_fails_closed(tmp_path: Path) -> None:
    packet_path, source = _approved_packet(tmp_path)
    source.write_bytes(b"tampered")

    with pytest.raises(MasterGateError) as error:
        validate_master_packet(packet_path, source_path=source, expected_slug="dracula")

    assert "MASTER_SHA256_MISMATCH" in error.value.blockers


def test_dracula_packet_remains_hold() -> None:
    packet_path = ROOT / "internal/audiobook_lab/dracula/pr269_master_release_packet.json"

    with pytest.raises(MasterGateError) as error:
        validate_master_packet(packet_path, expected_slug="dracula")

    assert "MASTER_PACKET_NOT_APPROVED" in error.value.blockers
    assert "VOICE_PROVIDER_RIGHTS_NOT_PASSED" in error.value.blockers
    assert "FULL_BOOK_HUMAN_LISTENING_NOT_PASSED" in error.value.blockers
    assert "FULL_BOOK_ACCESSIBILITY_LISTENING_NOT_PASSED" in error.value.blockers
    assert "OWNER_RELEASE_APPROVAL_MISSING" in error.value.blockers
