#!/usr/bin/env python3
"""Build a read-only, sentence-safe Jekyll chunk_0009 repair preflight.

The preflight consumes the exact private candidate whose chunk_0036 repair is
already complete. It validates every current audio hash, the chunk_0036 repair
lineage, the cross-model narration-omission evidence, and the read-only paid
lock state. It then emits a deterministic plan for changing only chunk_0009.

This module has no synthesis or upload client and no execute mode. It never
writes the paid lock, audio, catalog truth, package pointers, or release state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import sprint1_google_english_full_candidate_qa as candidate_qa  # noqa: E402


SCHEMA = "earnalism.jekyll_chunk9_sentence_safe_repair_preflight.v1"
SLUG = "jekyll-and-hyde"
TITLE = "The Strange Case of Dr. Jekyll and Mr. Hyde"
AUTHOR = "Robert Louis Stevenson"
TARGET_INDEX = 9
TARGET_UNIT_ID = "chunk_0009"
CHUNK36_INDEX = 36
CHUNK36_UNIT_ID = "chunk_0036"
EXPECTED_UNIT_COUNT = 92

EXPECTED_SOURCE_SHA256 = (
    "0e8cc7fb6c18abd38def7c85cc2a8f4907bde5f11db48e36ba7fd9afff7fdc8e"
)
EXPECTED_INPUT_MANIFEST_SHA256 = (
    "43177dc6f71521a6558dfcccbd784d46213e9e0f533c4e8ac3133be29725fd22"
)
EXPECTED_ROOT_MANIFEST_SHA256 = (
    "5bbbc01f9ab2dcba7194c1a0a28f636863896e68adb2f9a743ee33ddd7395439"
)
EXPECTED_PARENT_MANIFEST_SHA256 = (
    "616080b550edecc4320812ea09c0e0cf3f4f5afd96210247b5f1e6e3477a4632"
)
EXPECTED_PARENT_AUDIO_SEQUENCE_SHA256 = (
    "688273c3329b9c4b345e9bdf5f8eddf6c9e05c7bb90c240c859601b083eb02cb"
)
EXPECTED_PARENT_CANDIDATE_BINDING_SHA256 = (
    "160cbc3b4c8707127c0db5e39ac62806314fbdfcd1875cd9ee737f4e1c22c0cf"
)
EXPECTED_CHUNK36_REPAIR_EVIDENCE_SHA256 = (
    "603c909ff04ebbe5380728c49a74de45d57a1ffeb338dd3b7f2d74fe7930ebfe"
)
EXPECTED_CHUNK36_REPAIR_FINGERPRINT = (
    "49a28b145476242f958402300a1f8c45c61044582da96ace6b698e22aed7af6c"
)
EXPECTED_CHUNK36_AUDIO_SHA256 = (
    "d7d83110d869e2d40c59855e2d3e2252e9b642b6fa14e9790591cbb6c0d8702c"
)
EXPECTED_DIAGNOSTIC_EVIDENCE_SHA256 = (
    "644b83b7085dee90f540bfbb7743a6f4d8c41eca92e0cf9dd7c5c348df235d80"
)
EXPECTED_TURBO_REPORT_SHA256 = (
    "ef86c6ae2d1db6857aa209304173b8d2f74aded90caf3f66133e7db9ed185ec9"
)
EXPECTED_TURBO_RAW_SHA256 = (
    "6436a9aec7d8ffb7e0d093bf888fbc8c0932932e891f11ffcb77938b25dd2948"
)
EXPECTED_PAID_LOCK_SHA256 = (
    "8d87bd5891f33a58d6d2819ada69b89d626d35a30dd040e021bcf9561d232f01"
)

TARGET_TEXT_SHA256 = (
    "24a85dbb2f4184ea9ffb86599c65777d5fcfccc343d3fdb6077884aa5c9557de"
)
TARGET_AUDIO_SHA256 = (
    "e2a34a5ccfc5bb78e121fdd32ff821e7f907afe7203521fc08517c9904c91ebf"
)
TARGET_AUDIO_SIZE_BYTES = 367_488
MISSING_CANONICAL_SPAN = (
    "obligation beyond the payment of a few small sums to the members of the "
    "doctor’s household"
)
MISSING_CANONICAL_SPAN_SHA256 = (
    "fc0fec16f4396a443aeabe4cfaf22c629851597222661ea04fb06036b8887348"
)
MISSING_CANONICAL_TOKEN_COUNT = 16
REPLACEMENT_CLAUSE = (
    "and free from any burthen or obligation beyond the payment of a few "
    "small sums to the members of the doctor’s household."
)
REPLACEMENT_CLAUSE_SHA256 = (
    "9f5b63510b260f3e2c2bbcd691319cea1fd3b7b59908efa5605a49b0821d01f5"
)
LEFT_CONTEXT = "without further delay"
RIGHT_CONTEXT = "This document had long been the lawyer’s eyesore."
SYNTHESIS_CONTEXT = f"{LEFT_CONTEXT} {REPLACEMENT_CLAUSE} {RIGHT_CONTEXT}"
SYNTHESIS_CONTEXT_SHA256 = (
    "977e108da205532a2379eb254bdb95b087064714cbdeecef583e8e14b8e13884"
)
EXPECTED_SYNTHESIS_CHARACTERS = 192

PROVIDER = "google"
VOICE = "en-GB-Chirp3-HD-Charon"
LANGUAGE_CODE = "en-GB"
SPEAKING_RATE = 0.94
PITCH = 0.0
USD_PER_MILLION_CHARACTERS = 30.0
RUN_BUDGET_USD = 0.10
TITLE_BUDGET_USD = 8.0
SPRINT_BUDGET_USD = 75.0
FUTURE_LOCK_HOLDER = (
    "sprint1_jekyll_google_chunk9_sentence_safe_repair:"
    "jekyll-and-hyde:chunk_0009"
)


class Chunk9PreflightError(RuntimeError):
    """Raised when the exact bounded-repair evidence no longer matches."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Chunk9PreflightError(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Chunk9PreflightError(f"cannot read {label}: {path}") from exc
    require(isinstance(value, dict), f"{label} must be a JSON object")
    return value


def resolve_private_artifact(value: Any, run_dir: Path, label: str) -> Path:
    path = Path(str(value or "")).expanduser().resolve()
    require(
        candidate_qa.is_within(path, run_dir),
        f"{label} must remain in the private parent-candidate directory",
    )
    require(path.is_file(), f"{label} is missing: {path}")
    return path


def normalized_tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+(?:[’'][A-Za-z0-9]+)?", text.lower())


def validate_text_contract(target_text: str) -> dict[str, Any]:
    require(
        sha256_bytes(target_text.encode("utf-8")) == TARGET_TEXT_SHA256,
        "chunk_0009 canonical source hash changed",
    )
    require(
        sha256_bytes(MISSING_CANONICAL_SPAN.encode("utf-8"))
        == MISSING_CANONICAL_SPAN_SHA256,
        "missing-span constant changed",
    )
    require(
        len(normalized_tokens(MISSING_CANONICAL_SPAN))
        == MISSING_CANONICAL_TOKEN_COUNT,
        "missing-span token count changed",
    )
    for label, value in (
        ("missing span", MISSING_CANONICAL_SPAN),
        ("replacement clause", REPLACEMENT_CLAUSE),
        ("left context", LEFT_CONTEXT),
        ("right context", RIGHT_CONTEXT),
        ("synthesis context", SYNTHESIS_CONTEXT),
    ):
        require(
            target_text.count(value) == 1,
            f"{label} must occur exactly once inside chunk_0009",
        )
    require(
        sha256_bytes(REPLACEMENT_CLAUSE.encode("utf-8"))
        == REPLACEMENT_CLAUSE_SHA256,
        "replacement-clause hash changed",
    )
    require(
        len(SYNTHESIS_CONTEXT) == EXPECTED_SYNTHESIS_CHARACTERS
        and sha256_bytes(SYNTHESIS_CONTEXT.encode("utf-8"))
        == SYNTHESIS_CONTEXT_SHA256,
        "synthesis-context binding changed",
    )
    return {
        "missing_span": MISSING_CANONICAL_SPAN,
        "missing_span_sha256": MISSING_CANONICAL_SPAN_SHA256,
        "missing_span_token_count": MISSING_CANONICAL_TOKEN_COUNT,
        "replacement_clause": REPLACEMENT_CLAUSE,
        "replacement_clause_sha256": REPLACEMENT_CLAUSE_SHA256,
        "left_context": LEFT_CONTEXT,
        "right_context": RIGHT_CONTEXT,
        "synthesis_context": SYNTHESIS_CONTEXT,
        "synthesis_context_sha256": SYNTHESIS_CONTEXT_SHA256,
        "synthesis_context_characters": EXPECTED_SYNTHESIS_CHARACTERS,
    }


def validate_parent_candidate(
    manifest_path: Path,
    repair_evidence_path: Path,
) -> tuple[dict[str, Any], list[str], dict[str, str], list[str]]:
    manifest_path = manifest_path.expanduser().resolve()
    repair_evidence_path = repair_evidence_path.expanduser().resolve()
    require(
        sha256_file(manifest_path) == EXPECTED_PARENT_MANIFEST_SHA256,
        "parent repaired manifest hash changed",
    )
    require(
        sha256_file(repair_evidence_path)
        == EXPECTED_CHUNK36_REPAIR_EVIDENCE_SHA256,
        "chunk_0036 repair evidence hash changed",
    )
    manifest = read_json_object(manifest_path, "parent repaired manifest")
    repair = read_json_object(repair_evidence_path, "chunk_0036 repair evidence")
    run_dir = manifest_path.parent
    for observed, expected, label in (
        (manifest.get("slug"), SLUG, "slug"),
        (manifest.get("title"), TITLE, "title"),
        (manifest.get("author"), AUTHOR, "author"),
        (manifest.get("provider"), PROVIDER, "provider"),
        (manifest.get("voice"), VOICE, "voice"),
        (manifest.get("language_code"), LANGUAGE_CODE, "language"),
        (float(manifest.get("speaking_rate")), SPEAKING_RATE, "speaking rate"),
        (float(manifest.get("pitch")), PITCH, "pitch"),
        (manifest.get("source_sha256"), EXPECTED_SOURCE_SHA256, "source"),
        (
            manifest.get("input_manifest_sha256"),
            EXPECTED_INPUT_MANIFEST_SHA256,
            "input manifest",
        ),
        (manifest.get("unit_count"), EXPECTED_UNIT_COUNT, "unit count"),
        (
            manifest.get("candidate_audio_sequence_sha256"),
            EXPECTED_PARENT_AUDIO_SEQUENCE_SHA256,
            "parent audio sequence",
        ),
    ):
        require(observed == expected, f"parent candidate changed at {label}")
    require(
        manifest.get("status") == "FULL_GENERATION_PRIVATE_QA_PENDING"
        and manifest.get("private_output_only") is True
        and manifest.get("public_release_approved") is False,
        "parent candidate is not private QA-only",
    )
    for field in (
        "upload_performed",
        "publication_performed",
        "release_mutation_performed",
    ):
        require(manifest.get(field) is False, f"parent {field} must be false")

    source_path = resolve_private_artifact(
        manifest.get("sanitized_source_copy"), run_dir, "sanitized source"
    )
    input_path = resolve_private_artifact(
        manifest.get("input_manifest_copy"), run_dir, "input manifest"
    )
    require(
        sha256_file(source_path) == EXPECTED_SOURCE_SHA256,
        "parent source bytes changed",
    )
    require(
        sha256_file(input_path) == EXPECTED_INPUT_MANIFEST_SHA256,
        "parent input manifest bytes changed",
    )
    records = manifest.get("generated_audio")
    require(
        isinstance(records, list) and len(records) == EXPECTED_UNIT_COUNT,
        "parent must contain exactly 92 audio records",
    )
    segments = candidate_qa.reconstruct_segments(
        source_path.read_text(encoding="utf-8"),
        records,
    )
    hashes: list[str] = []
    preserved: dict[str, str] = {}
    for index, record in enumerate(records):
        require(isinstance(record, dict), f"audio record {index} is invalid")
        unit_id = f"chunk_{index:04d}"
        require(record.get("unit_id") == unit_id, "audio order changed")
        audio_path = resolve_private_artifact(
            record.get("audio_path"), run_dir, unit_id
        )
        observed_hash = sha256_file(audio_path)
        require(
            observed_hash == record.get("audio_sha256"),
            f"{unit_id} audio hash changed",
        )
        require(
            audio_path.stat().st_size == record.get("audio_size_bytes"),
            f"{unit_id} audio size changed",
        )
        hashes.append(observed_hash)
        if index != TARGET_INDEX:
            preserved[unit_id] = observed_hash
    require(
        candidate_qa.sha256_json(hashes)
        == EXPECTED_PARENT_AUDIO_SEQUENCE_SHA256,
        "parent ordered audio sequence changed",
    )
    target = records[TARGET_INDEX]
    require(
        target.get("text_sha256") == TARGET_TEXT_SHA256
        and target.get("audio_sha256") == TARGET_AUDIO_SHA256
        and target.get("audio_size_bytes") == TARGET_AUDIO_SIZE_BYTES,
        "chunk_0009 target binding changed",
    )

    lineage = manifest.get("bounded_chunk_repair")
    require(isinstance(lineage, dict), "chunk_0036 lineage is missing")
    root_hashes = lineage.get("base_ordered_audio_hashes")
    require(
        isinstance(root_hashes, list) and len(root_hashes) == EXPECTED_UNIT_COUNT,
        "root candidate hashes are missing",
    )
    changed_from_root = [
        index
        for index, (before, after) in enumerate(zip(root_hashes, hashes))
        if before != after
    ]
    require(
        changed_from_root == [CHUNK36_INDEX]
        and lineage.get("changed_chunk_indexes") == [CHUNK36_INDEX]
        and lineage.get("base_full_manifest_sha256")
        == EXPECTED_ROOT_MANIFEST_SHA256,
        "parent does not preserve the exact chunk_0036-only repair lineage",
    )
    require(
        hashes[CHUNK36_INDEX] == EXPECTED_CHUNK36_AUDIO_SHA256,
        "repaired chunk_0036 audio changed",
    )
    for observed, expected, label in (
        (repair.get("slug"), SLUG, "repair slug"),
        (
            repair.get("repair_attempt_fingerprint"),
            EXPECTED_CHUNK36_REPAIR_FINGERPRINT,
            "chunk_0036 repair fingerprint",
        ),
        (
            repair.get("replacement_full_manifest_sha256"),
            EXPECTED_PARENT_MANIFEST_SHA256,
            "chunk_0036 parent manifest",
        ),
        (
            repair.get("candidate_audio_sequence_sha256"),
            EXPECTED_PARENT_AUDIO_SEQUENCE_SHA256,
            "chunk_0036 parent audio sequence",
        ),
        (
            repair.get("candidate_binding_sha256"),
            EXPECTED_PARENT_CANDIDATE_BINDING_SHA256,
            "chunk_0036 parent candidate binding",
        ),
        (
            repair.get("replacement_audio_sha256"),
            EXPECTED_CHUNK36_AUDIO_SHA256,
            "chunk_0036 replacement audio",
        ),
    ):
        require(observed == expected, f"lineage changed at {label}")
    require(
        repair.get("changed_chunk_indexes") == [CHUNK36_INDEX]
        and repair.get("preserved_audio_file_count") == 91
        and repair.get("provider_calls_ran") is True
        and repair.get("paid_lock_restored_byte_for_byte") is True,
        "chunk_0036 repair completion evidence changed",
    )
    return manifest, segments, preserved, hashes


def validate_omission_evidence(
    diagnostic_path: Path,
    turbo_report_path: Path,
    turbo_raw_path: Path,
) -> dict[str, Any]:
    diagnostic_path = diagnostic_path.expanduser().resolve()
    turbo_report_path = turbo_report_path.expanduser().resolve()
    turbo_raw_path = turbo_raw_path.expanduser().resolve()
    for path, expected, label in (
        (
            diagnostic_path,
            EXPECTED_DIAGNOSTIC_EVIDENCE_SHA256,
            "canonical diagnostic evidence",
        ),
        (turbo_report_path, EXPECTED_TURBO_REPORT_SHA256, "turbo report"),
        (turbo_raw_path, EXPECTED_TURBO_RAW_SHA256, "turbo raw result"),
    ):
        require(path.is_file() and sha256_file(path) == expected, f"{label} changed")
    diagnostic = read_json_object(diagnostic_path, "diagnostic evidence")
    require(
        diagnostic.get("decision")
        == "FULL_TITLE_MLX_RUN_BLOCKED_CHUNK9_NARRATION_OMISSION_CONFIRMED",
        "diagnostic decision changed",
    )
    comparison = {
        item.get("unit_id"): item
        for item in diagnostic.get("unit_comparison", [])
        if isinstance(item, dict)
    }
    target = comparison.get(TARGET_UNIT_ID) or {}
    require(
        target.get("source_text_sha256") == TARGET_TEXT_SHA256
        and target.get("audio_sha256") == TARGET_AUDIO_SHA256
        and target.get("cross_model_finding")
        == "ACTUAL_NARRATION_CONTENT_OMISSION"
        and target.get("missing_source_token_count")
        == MISSING_CANONICAL_TOKEN_COUNT,
        "diagnostic chunk_0009 binding changed",
    )
    turbo_report = read_json_object(turbo_report_path, "turbo report")
    reports = {
        item.get("unit_id"): item
        for item in turbo_report.get("reports", [])
        if isinstance(item, dict)
    }
    turbo_target = reports.get(TARGET_UNIT_ID) or {}
    require(
        turbo_target.get("source_text_sha256") == TARGET_TEXT_SHA256
        and turbo_target.get("audio_sha256") == TARGET_AUDIO_SHA256
        and turbo_target.get("raw_result_sha256") == EXPECTED_TURBO_RAW_SHA256
        and turbo_target.get("strict_objective_pass") is False,
        "turbo target evidence changed",
    )
    raw = read_json_object(turbo_raw_path, "turbo raw result")
    words = [
        word
        for segment in raw.get("segments", [])
        if isinstance(segment, dict)
        for word in segment.get("words", [])
        if isinstance(word, dict)
    ]
    normalized = [str(word.get("word") or "").strip().lower() for word in words]
    expected = ["delay", "and", "free", "from", "any", "burthen", "or", "this"]
    positions: list[int] = []
    cursor = 0
    for token in expected:
        try:
            cursor = normalized.index(token, cursor)
        except ValueError as exc:
            raise Chunk9PreflightError(
                f"timing evidence lacks ordered anchor token {token}"
            ) from exc
        positions.append(cursor)
        cursor += 1
    anchors = {token: words[index] for token, index in zip(expected, positions)}
    require(
        math.isclose(float(anchors["delay"]["end"]), 30.10, abs_tol=0.001)
        and math.isclose(float(anchors["and"]["start"]), 30.10, abs_tol=0.001)
        and math.isclose(float(anchors["or"]["end"]), 31.92, abs_tol=0.001)
        and math.isclose(float(anchors["this"]["start"]), 31.92, abs_tol=0.001),
        "measured splice anchors changed",
    )
    require(
        positions[-1] == positions[-2] + 1,
        "unrecognized audio exists between 'or' and 'this'",
    )
    return {
        "turbo_report_sha256": EXPECTED_TURBO_REPORT_SHA256,
        "turbo_raw_result_sha256": EXPECTED_TURBO_RAW_SHA256,
        "replace_start_seconds": 30.10,
        "replace_end_seconds": 31.92,
        "defective_span_seconds": 1.82,
        "left_anchor": "delay",
        "right_anchor": "This",
        "missing_audio_gap_seconds": 0.0,
    }


def validate_paid_lock_read_only(path: Path) -> tuple[dict[str, Any], str]:
    resolved = path.expanduser().resolve()
    before = resolved.read_bytes()
    require(
        sha256_bytes(before) == EXPECTED_PAID_LOCK_SHA256,
        "paid lock hash changed before preflight",
    )
    try:
        payload = json.loads(before)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Chunk9PreflightError("paid lock is not UTF-8 JSON") from exc
    require(
        isinstance(payload, dict)
        and payload.get("status") == "active"
        and payload.get("current_holder") == "none"
        and payload.get("allowed_next_holders") == [],
        "paid lock is not idle and active",
    )
    require(
        SLUG in (payload.get("allowed_slugs") or []),
        "paid lock does not allow Jekyll",
    )
    require(resolved.read_bytes() == before, "paid lock changed during preflight")
    return payload, sha256_bytes(before)


def budget_plan(repair_evidence: Mapping[str, Any]) -> dict[str, Any]:
    prior = repair_evidence.get("budget") or {}
    prior_title = float(prior.get("projected_title_spend_usd"))
    prior_sprint = float(prior.get("projected_sprint_spend_usd"))
    estimate = round(
        EXPECTED_SYNTHESIS_CHARACTERS
        / 1_000_000
        * USD_PER_MILLION_CHARACTERS,
        6,
    )
    plan = {
        "billable_characters": EXPECTED_SYNTHESIS_CHARACTERS,
        "usd_per_million_characters": USD_PER_MILLION_CHARACTERS,
        "estimated_run_usd": estimate,
        "run_budget_usd": RUN_BUDGET_USD,
        "prior_title_spend_usd": prior_title,
        "projected_title_spend_usd": round(prior_title + estimate, 6),
        "title_budget_usd": TITLE_BUDGET_USD,
        "prior_sprint_spend_usd": prior_sprint,
        "projected_sprint_spend_usd": round(prior_sprint + estimate, 6),
        "sprint_budget_usd": SPRINT_BUDGET_USD,
    }
    require(
        estimate <= RUN_BUDGET_USD
        and plan["projected_title_spend_usd"] <= TITLE_BUDGET_USD
        and plan["projected_sprint_spend_usd"] <= SPRINT_BUDGET_USD,
        "planned clause repair exceeds a budget cap",
    )
    return {"status": "PASS_PREFLIGHT_ONLY", **plan}


def build_preflight(
    *,
    parent_manifest: Path,
    chunk36_repair_evidence: Path,
    diagnostic_evidence: Path,
    turbo_report: Path,
    turbo_raw_result: Path,
    paid_lock: Path,
    generated_at: str,
) -> dict[str, Any]:
    require(
        re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", generated_at)
        is not None,
        "generated_at must be an explicit UTC second",
    )
    manifest, segments, preserved, hashes = validate_parent_candidate(
        parent_manifest,
        chunk36_repair_evidence,
    )
    text = validate_text_contract(segments[TARGET_INDEX])
    timing = validate_omission_evidence(
        diagnostic_evidence,
        turbo_report,
        turbo_raw_result,
    )
    repair = read_json_object(
        chunk36_repair_evidence.expanduser().resolve(),
        "chunk_0036 repair evidence",
    )
    budget = budget_plan(repair)
    lock_before = paid_lock.expanduser().resolve().read_bytes()
    lock_payload, lock_sha256 = validate_paid_lock_read_only(paid_lock)
    require(
        paid_lock.expanduser().resolve().read_bytes() == lock_before,
        "paid lock changed after read-only validation",
    )
    adjacent = {
        "chunk_0008_text_sha256": manifest["generated_audio"][8]["text_sha256"],
        "chunk_0008_tail": "The will was holograph, for Mr.",
        "chunk_0009_text_sha256": TARGET_TEXT_SHA256,
        "chunk_0009_head": (
            "Utterson though he took charge of it now that it was made,"
        ),
        "chunk_0009_tail": (
            "where his friend, the great Dr."
        ),
        "chunk_0010_text_sha256": manifest["generated_audio"][10]["text_sha256"],
        "chunk_0010_head": (
            "Lanyon, had his house and received his crowding patients."
        ),
    }
    for excerpt in (
        adjacent["chunk_0008_tail"],
        adjacent["chunk_0009_head"],
        adjacent["chunk_0009_tail"],
        adjacent["chunk_0010_head"],
    ):
        require(
            " ".join(segments[8:11]).count(str(excerpt)) == 1,
            "adjacent source context changed",
        )
    preservation_sha256 = canonical_sha256(preserved)
    binding_material = {
        "schema_version": SCHEMA,
        "slug": SLUG,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "input_manifest_sha256": EXPECTED_INPUT_MANIFEST_SHA256,
        "root_manifest_sha256": EXPECTED_ROOT_MANIFEST_SHA256,
        "parent_manifest_sha256": EXPECTED_PARENT_MANIFEST_SHA256,
        "parent_audio_sequence_sha256": EXPECTED_PARENT_AUDIO_SEQUENCE_SHA256,
        "parent_candidate_binding_sha256": (
            EXPECTED_PARENT_CANDIDATE_BINDING_SHA256
        ),
        "chunk36_repair_evidence_sha256": (
            EXPECTED_CHUNK36_REPAIR_EVIDENCE_SHA256
        ),
        "target_unit_id": TARGET_UNIT_ID,
        "target_text_sha256": TARGET_TEXT_SHA256,
        "target_audio_sha256": TARGET_AUDIO_SHA256,
        "preserved_audio_hashes_sha256": preservation_sha256,
        "synthesis_context_sha256": SYNTHESIS_CONTEXT_SHA256,
        "replacement_clause_sha256": REPLACEMENT_CLAUSE_SHA256,
        "timing_evidence_sha256": EXPECTED_TURBO_RAW_SHA256,
        "provider": PROVIDER,
        "voice": VOICE,
        "language_code": LANGUAGE_CODE,
        "speaking_rate": SPEAKING_RATE,
        "pitch": PITCH,
    }
    preflight_binding = canonical_sha256(binding_material)
    return {
        "schema_version": SCHEMA,
        "generated_at": generated_at,
        "status": "PREFLIGHT_PASS_NO_PROVIDER_CALL_AUDIO_HIDDEN",
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "preflight_binding_sha256": preflight_binding,
        "parent_candidate": {
            "root_full_manifest_sha256": EXPECTED_ROOT_MANIFEST_SHA256,
            "parent_full_manifest_path": str(
                parent_manifest.expanduser().resolve()
            ),
            "parent_full_manifest_sha256": EXPECTED_PARENT_MANIFEST_SHA256,
            "parent_audio_sequence_sha256": (
                EXPECTED_PARENT_AUDIO_SEQUENCE_SHA256
            ),
            "parent_candidate_binding_sha256": (
                EXPECTED_PARENT_CANDIDATE_BINDING_SHA256
            ),
            "source_sha256": EXPECTED_SOURCE_SHA256,
            "input_manifest_sha256": EXPECTED_INPUT_MANIFEST_SHA256,
            "unit_count": EXPECTED_UNIT_COUNT,
            "cumulative_changed_indexes": [CHUNK36_INDEX],
        },
        "chunk36_lineage": {
            "repair_evidence_path": str(
                chunk36_repair_evidence.expanduser().resolve()
            ),
            "repair_evidence_sha256": (
                EXPECTED_CHUNK36_REPAIR_EVIDENCE_SHA256
            ),
            "repair_attempt_fingerprint": (
                EXPECTED_CHUNK36_REPAIR_FINGERPRINT
            ),
            "unit_id": CHUNK36_UNIT_ID,
            "audio_sha256": EXPECTED_CHUNK36_AUDIO_SHA256,
            "must_remain_byte_identical": True,
        },
        "target": {
            "chunk_index": TARGET_INDEX,
            "unit_id": TARGET_UNIT_ID,
            "source_text_sha256": TARGET_TEXT_SHA256,
            "source_characters": len(segments[TARGET_INDEX]),
            "prior_audio_sha256": TARGET_AUDIO_SHA256,
            "prior_audio_size_bytes": TARGET_AUDIO_SIZE_BYTES,
            **text,
        },
        "adjacent_context": adjacent,
        "measured_defect": timing,
        "provider_plan": {
            "provider": PROVIDER,
            "voice": VOICE,
            "language_code": LANGUAGE_CODE,
            "speaking_rate": SPEAKING_RATE,
            "pitch": PITCH,
            "synthesis_input_kind": "exact_plain_text_context_window",
            "context_text_sha256": SYNTHESIS_CONTEXT_SHA256,
            "context_characters": EXPECTED_SYNTHESIS_CHARACTERS,
            "preserves_local_chunk9_voice_settings": True,
            "materially_differs_from_failed_full_chunk_attempt": (
                "context-window text hash differs from the prior full-chunk "
                "text hash; only the exact clause is retained after alignment"
            ),
        },
        "sentence_safe_repair_plan": {
            "strategy": "CONTEXT_SYNTHESIS_FORCED_ALIGNMENT_CLAUSE_SPLICE",
            "steps": [
                (
                    "Synthesize the exact 192-character context window once; "
                    "do not synthesize the full chunk or any other unit."
                ),
                (
                    "Run source-blind ASR plus forced alignment on the private "
                    "context audio and require every context token in order."
                ),
                (
                    "Extract only the exact replacement clause, retaining its "
                    "natural terminal pause."
                ),
                (
                    "Decode parent chunk_0009 to 24 kHz mono PCM; replace only "
                    "the measured 30.10s-to-31.92s defective clause window at "
                    "verified zero-crossing/punctuation anchors."
                ),
                (
                    "Encode one new private chunk_0009 MP3; copy all other 91 "
                    "parent units without changing their bytes."
                ),
            ],
            "left_join": {
                "preserve_through": LEFT_CONTEXT,
                "measured_end_seconds": 30.10,
                "join_kind": "clause_boundary_after_delay",
            },
            "right_join": {
                "resume_with": RIGHT_CONTEXT,
                "measured_start_seconds": 31.92,
                "join_kind": "sentence_boundary_before_This",
            },
            "alignment_required": True,
            "estimated_or_visual_sync_forbidden": True,
            "blind_fixed_time_splice_forbidden": True,
            "expected_parent_to_child_changed_indexes": [TARGET_INDEX],
            "expected_root_to_child_changed_indexes": [
                TARGET_INDEX,
                CHUNK36_INDEX,
            ],
            "preserved_audio_file_count": 91,
            "preserved_audio_hashes_sha256": preservation_sha256,
            "preserved_audio_hashes": preserved,
            "chunk36_audio_sha256_after_repair_required": (
                EXPECTED_CHUNK36_AUDIO_SHA256
            ),
        },
        "budget": budget,
        "paid_lock_plan": {
            "current_lock_path": str(paid_lock.expanduser().resolve()),
            "current_lock_sha256": lock_sha256,
            "current_status": lock_payload.get("status"),
            "current_holder": lock_payload.get("current_holder"),
            "current_allowed_next_holders": lock_payload.get(
                "allowed_next_holders"
            ),
            "future_holder": FUTURE_LOCK_HOLDER,
            "future_allowed_slugs": [SLUG],
            "future_approved_scope": (
                "Exactly one private Google context-window synthesis for "
                "jekyll-and-hyde chunk_0009; clause-level splice only; no "
                "upload, publication, release mutation, or other title."
            ),
            "approval_env_required": (
                "EARNALISM_APPROVE_JEKYLL_CHUNK9_SENTENCE_SAFE_REPAIR=true"
            ),
            "budget_stop_env_required": (
                "EARNALISM_STOP_ON_BUDGET_EXCEEDED=true"
            ),
            "read_during_preflight": True,
            "written_during_preflight": False,
            "mutated_during_preflight": False,
        },
        "post_repair_qa": {
            "target_objective": {
                "units": [TARGET_UNIT_ID],
                "asr_source_score_min": 9.7,
                "coverage_min": 0.98,
                "first_last_words_required": True,
                "no_missing_duplicate_reordered_unexpected_content": True,
                "measured_word_timestamps_required": True,
                "splice_join_listening_required": True,
            },
            "lineage_objective": {
                "units": [CHUNK36_UNIT_ID],
                "fresh_objective_evidence_required": True,
                "reason": (
                    "chunk_0036 is already repaired but remains private "
                    "QA-pending and must not inherit its superseded evidence"
                ),
            },
            "full_title_objective": {
                "unit_count": EXPECTED_UNIT_COUNT,
                "score_min": 9.7,
                "coverage_min": 0.98,
                "ordered_content_integrity_required": True,
                "first_last_words_required": True,
                "measured_paragraph_or_better_sync_required": True,
                "estimated_sync_forbidden": True,
                "independent_adjudication_required_for": [
                    "chunk_0045",
                    "chunk_0071",
                ],
            },
            "listening": {
                "policy": "platform_audiobook_acceptance_v4_89",
                "fresh_changed_unit_samples": [
                    TARGET_UNIT_ID,
                    CHUNK36_UNIT_ID,
                ],
                "retained_hash_bound_samples_eligible_for_reuse": [
                    "chunk_0000",
                    "chunk_0018",
                    "chunk_0041",
                    "chunk_0045",
                    "chunk_0091",
                ],
                "overall_and_dimension_min": 8.9,
                "anti_robotic_and_anti_choppy_min": 9.2,
                "confidence_min": 0.90,
                "fatal_flags_allowed": [],
            },
        },
        "package_v2_eligibility": {
            "eligible_now": False,
            "blockers": [
                "chunk_0009 replacement audio does not exist",
                "repaired chunks 0009 and 0036 lack fresh objective evidence",
                "full-title strict objective and measured sync are incomplete",
                "fresh changed-unit listening judgments are incomplete",
                "immutable package-v2 manifest and delivery media are absent",
                "primary and DR upload receipts are absent",
                "controlled active-release pointer is absent",
                "production manifest, Range 206, endpoint, and browser proof are absent",
            ],
            "required_after_qa": [
                "source and rights remain exact",
                "canonical front and back covers remain complete",
                "immutable delivery segments and timestamp sidecars hash-bind",
                "primary and DR B2 checksums and version IDs verify",
                "controlled release evidence activates exact package version",
                "valid Range returns 206 and invalid Range returns 416",
                "browser playback, seeking, auto-advance, and revocation pass",
                "ordinary Listen remains hidden until final owner-approved activation",
            ],
        },
        "provider_calls_ran": False,
        "audio_generated": False,
        "audio_modified": False,
        "paid_lock_touched": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
        "public_audio_status": "AUDIO_HIDDEN_NOT_APPROVED",
        "next_exact_command": (
            "PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q "
            "internal/audiobook_lab/scripts/"
            "test_sprint1_jekyll_chunk9_sentence_safe_repair_preflight.py "
            "internal/audiobook_lab/scripts/"
            "test_sprint1_jekyll_mlx_representative_objective_qa.py"
        ),
    }


def atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def validate_output_path(output: Path, parent_manifest: Path) -> Path:
    resolved = output.expanduser().resolve()
    root = parent_manifest.expanduser().resolve().parent / "chunk9_repair_preflight"
    require(
        candidate_qa.is_within(resolved, root),
        "output must remain under the private chunk9_repair_preflight directory",
    )
    require(resolved.suffix == ".json", "output must be JSON")
    require(not resolved.exists(), "preflight output already exists")
    return resolved


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the read-only Jekyll chunk_0009 repair preflight"
    )
    parser.add_argument("--parent-manifest", required=True, type=Path)
    parser.add_argument("--chunk36-repair-evidence", required=True, type=Path)
    parser.add_argument("--diagnostic-evidence", required=True, type=Path)
    parser.add_argument("--turbo-report", required=True, type=Path)
    parser.add_argument("--turbo-raw-result", required=True, type=Path)
    parser.add_argument("--paid-lock", required=True, type=Path)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        output = validate_output_path(args.output, args.parent_manifest)
        result = build_preflight(
            parent_manifest=args.parent_manifest,
            chunk36_repair_evidence=args.chunk36_repair_evidence,
            diagnostic_evidence=args.diagnostic_evidence,
            turbo_report=args.turbo_report,
            turbo_raw_result=args.turbo_raw_result,
            paid_lock=args.paid_lock,
            generated_at=args.generated_at,
        )
        atomic_write_json(output, result)
    except (Chunk9PreflightError, OSError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
