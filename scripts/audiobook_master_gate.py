#!/usr/bin/env python3
"""Validate checksum-bound audiobook master approval packets.

The gate is intentionally stricter than ordinary audiobook metadata. A master
may be used for preview derivation only when every legal, objective, listening,
accessibility, and owner approval field is bound to the exact master checksum.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "earnalism.audiobook-master-release-packet.v1"
APPROVED_STATUS = "APPROVED_FOR_PR269_PRIVATE_STAGING_PREVIEW_DERIVATION"
APPROVED_GATE_STATUS = "PASS"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MIN_LISTENING_SCORE = 8.9
MIN_CONFIDENCE = 0.90
MIN_ALIGNMENT_SCORE = 9.7


class MasterGateError(RuntimeError):
    """Raised when a master packet does not satisfy every fail-closed gate."""

    def __init__(self, blockers: list[str]):
        super().__init__("; ".join(blockers))
        self.blockers = blockers


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _valid_sha256(value: Any) -> bool:
    return bool(SHA256_PATTERN.fullmatch(str(value or "").strip().lower()))


def _resolve_evidence_path(packet_path: Path, value: Any) -> Path:
    evidence_path = Path(str(value or "").strip()).expanduser()
    if not evidence_path.is_absolute():
        evidence_path = packet_path.parent / evidence_path
    return evidence_path.resolve()


def _validate_evidence(
    packet_path: Path,
    gate_name: str,
    gate: dict[str, Any],
    blockers: list[str],
) -> None:
    evidence = gate.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        blockers.append(f"{gate_name.upper()}_EVIDENCE_MISSING")
        return
    for index, item in enumerate(evidence):
        item = _object(item)
        path = _resolve_evidence_path(packet_path, item.get("path"))
        expected_sha256 = str(item.get("sha256") or "").strip().lower()
        label = f"{gate_name.upper()}_EVIDENCE_{index + 1}"
        if not path.is_file():
            blockers.append(f"{label}_FILE_MISSING")
            continue
        if not _valid_sha256(expected_sha256):
            blockers.append(f"{label}_SHA256_MISSING")
            continue
        if sha256_file(path) != expected_sha256:
            blockers.append(f"{label}_SHA256_MISMATCH")


def _validate_listening_gate(
    packet_path: Path,
    gate_name: str,
    gate: dict[str, Any],
    master_duration_seconds: float,
    blockers: list[str],
) -> None:
    if gate.get("status") != APPROVED_GATE_STATUS:
        blockers.append(f"{gate_name.upper()}_NOT_PASSED")
    try:
        overall_score = float(gate.get("overall_score"))
    except (TypeError, ValueError):
        overall_score = -1
    if overall_score < MIN_LISTENING_SCORE:
        blockers.append(f"{gate_name.upper()}_OVERALL_SCORE_BELOW_{MIN_LISTENING_SCORE}")
    try:
        confidence = float(gate.get("confidence"))
    except (TypeError, ValueError):
        confidence = -1
    if confidence < MIN_CONFIDENCE:
        blockers.append(f"{gate_name.upper()}_CONFIDENCE_BELOW_{MIN_CONFIDENCE}")
    try:
        reviewed_seconds = float(gate.get("reviewed_duration_seconds"))
    except (TypeError, ValueError):
        reviewed_seconds = -1
    if reviewed_seconds + 1 < master_duration_seconds:
        blockers.append(f"{gate_name.upper()}_FULL_BOOK_COVERAGE_MISSING")
    dimensions = gate.get("dimension_scores")
    if not isinstance(dimensions, dict) or not dimensions:
        blockers.append(f"{gate_name.upper()}_DIMENSION_SCORES_MISSING")
    else:
        for dimension, score in dimensions.items():
            try:
                score_value = float(score)
            except (TypeError, ValueError):
                score_value = -1
            if score_value < MIN_LISTENING_SCORE:
                blockers.append(
                    f"{gate_name.upper()}_DIMENSION_{str(dimension).upper()}_BELOW_{MIN_LISTENING_SCORE}"
                )
    fatal_flags = gate.get("fatal_flags")
    if not isinstance(fatal_flags, list) or fatal_flags:
        blockers.append(f"{gate_name.upper()}_FATAL_FLAGS_NOT_CLEAR")
    _validate_evidence(packet_path, gate_name, gate, blockers)


def validate_master_packet(
    packet_path: Path,
    *,
    source_path: Path | None = None,
    expected_slug: str | None = None,
) -> dict[str, Any]:
    """Return validated packet details or raise ``MasterGateError``."""

    packet_path = packet_path.expanduser().resolve()
    blockers: list[str] = []
    try:
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MasterGateError(["MASTER_PACKET_INVALID_JSON"]) from exc
    if not isinstance(packet, dict):
        raise MasterGateError(["MASTER_PACKET_NOT_OBJECT"])

    if packet.get("schema_version") != SCHEMA_VERSION:
        blockers.append("MASTER_PACKET_SCHEMA_INVALID")
    if packet.get("status") != APPROVED_STATUS:
        blockers.append("MASTER_PACKET_NOT_APPROVED")
    slug = str(packet.get("book_slug") or "").strip()
    if not slug:
        blockers.append("MASTER_PACKET_BOOK_SLUG_MISSING")
    if expected_slug and slug != expected_slug:
        blockers.append("MASTER_PACKET_BOOK_SLUG_MISMATCH")

    master = _object(packet.get("master"))
    master_sha256 = str(master.get("sha256") or "").strip().lower()
    if not _valid_sha256(master_sha256):
        blockers.append("MASTER_SHA256_MISSING")
    try:
        master_bytes = int(master.get("bytes"))
    except (TypeError, ValueError):
        master_bytes = -1
    if master_bytes <= 0:
        blockers.append("MASTER_BYTES_INVALID")
    try:
        master_duration_seconds = float(master.get("duration_seconds"))
    except (TypeError, ValueError):
        master_duration_seconds = -1
    if master_duration_seconds <= 180:
        blockers.append("MASTER_DURATION_NOT_FULL_BOOK")

    if source_path is not None:
        source_path = source_path.expanduser().resolve()
        if not source_path.is_file():
            blockers.append("MASTER_FILE_MISSING")
        else:
            if source_path.stat().st_size != master_bytes:
                blockers.append("MASTER_BYTES_MISMATCH")
            if _valid_sha256(master_sha256) and sha256_file(source_path) != master_sha256:
                blockers.append("MASTER_SHA256_MISMATCH")

    canonical = _object(packet.get("canonical_binding"))
    canonical_sha256 = str(canonical.get("canonical_source_sha256") or "").strip().lower()
    candidate_sha256 = str(canonical.get("candidate_source_sha256") or "").strip().lower()
    if canonical.get("status") != APPROVED_GATE_STATUS:
        blockers.append("CANONICAL_BINDING_NOT_PASSED")
    if not _valid_sha256(canonical_sha256):
        blockers.append("CANONICAL_SOURCE_SHA256_MISSING")
    if not _valid_sha256(candidate_sha256):
        blockers.append("CANDIDATE_SOURCE_SHA256_MISSING")
    elif candidate_sha256 != canonical_sha256:
        blockers.append("CANDIDATE_SOURCE_NOT_CANONICAL")
    _validate_evidence(packet_path, "canonical_binding", canonical, blockers)

    rights = _object(packet.get("rights"))
    for gate_name in ("source_text", "derivative_audiobook", "voice_provider"):
        gate = _object(rights.get(gate_name))
        if gate.get("status") != APPROVED_GATE_STATUS:
            blockers.append(f"{gate_name.upper()}_RIGHTS_NOT_PASSED")
        if str(gate.get("master_sha256") or "").strip().lower() != master_sha256:
            blockers.append(f"{gate_name.upper()}_RIGHTS_MASTER_BINDING_MISMATCH")
        _validate_evidence(packet_path, f"{gate_name}_rights", gate, blockers)

    alignment = _object(packet.get("canonical_alignment"))
    if alignment.get("status") != APPROVED_GATE_STATUS:
        blockers.append("CANONICAL_ALIGNMENT_NOT_PASSED")
    try:
        alignment_score = float(alignment.get("score"))
    except (TypeError, ValueError):
        alignment_score = -1
    if alignment_score < MIN_ALIGNMENT_SCORE:
        blockers.append(f"CANONICAL_ALIGNMENT_SCORE_BELOW_{MIN_ALIGNMENT_SCORE}")
    for key in ("first_words_match", "last_words_match", "ordered_content_match"):
        if alignment.get(key) is not True:
            blockers.append(f"CANONICAL_ALIGNMENT_{key.upper()}_FAILED")
    for key in ("missing_content_count", "duplicated_content_count", "reordered_content_count"):
        if alignment.get(key) != 0:
            blockers.append(f"CANONICAL_ALIGNMENT_{key.upper()}_NONZERO")
    if str(alignment.get("master_sha256") or "").strip().lower() != master_sha256:
        blockers.append("CANONICAL_ALIGNMENT_MASTER_BINDING_MISMATCH")
    _validate_evidence(packet_path, "canonical_alignment", alignment, blockers)

    listening = _object(packet.get("listening_qa"))
    _validate_listening_gate(
        packet_path,
        "full_book_human_listening",
        _object(listening.get("human")),
        master_duration_seconds,
        blockers,
    )
    _validate_listening_gate(
        packet_path,
        "full_book_accessibility_listening",
        _object(listening.get("accessibility")),
        master_duration_seconds,
        blockers,
    )
    for gate_name in ("human", "accessibility"):
        if (
            str(_object(listening.get(gate_name)).get("master_sha256") or "").strip().lower()
            != master_sha256
        ):
            blockers.append(f"FULL_BOOK_{gate_name.upper()}_LISTENING_MASTER_BINDING_MISMATCH")

    owner = _object(packet.get("owner_release_approval"))
    if owner.get("status") != APPROVED_STATUS:
        blockers.append("OWNER_RELEASE_APPROVAL_MISSING")
    if str(owner.get("master_sha256") or "").strip().lower() != master_sha256:
        blockers.append("OWNER_RELEASE_APPROVAL_MASTER_BINDING_MISMATCH")
    if owner.get("production_release_authorized") is not False:
        blockers.append("OWNER_APPROVAL_SCOPE_NOT_STAGING_ONLY")
    if not str(owner.get("approved_by") or "").strip():
        blockers.append("OWNER_APPROVER_MISSING")
    if not str(owner.get("approved_at") or "").strip():
        blockers.append("OWNER_APPROVAL_TIMESTAMP_MISSING")
    _validate_evidence(packet_path, "owner_release_approval", owner, blockers)

    blockers = list(dict.fromkeys(blockers))
    if blockers:
        raise MasterGateError(blockers)
    return {
        "status": APPROVED_STATUS,
        "book_slug": slug,
        "master_sha256": master_sha256,
        "master_bytes": master_bytes,
        "master_duration_seconds": master_duration_seconds,
        "canonical_source_sha256": canonical_sha256,
        "packet_sha256": sha256_file(packet_path),
        "packet_path": str(packet_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--slug")
    args = parser.parse_args()
    try:
        result = validate_master_packet(
            args.packet,
            source_path=args.source,
            expected_slug=args.slug,
        )
    except MasterGateError as exc:
        print(
            json.dumps(
                {"status": "FAIL_CLOSED", "blockers": exc.blockers},
                indent=2,
            )
        )
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
