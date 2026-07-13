#!/usr/bin/env python3
"""Build and execute the fail-closed Sprint 1 audiobook go-live queue.

The loop ranks source-bound received audio first, then non-paid repairs, and only
then paid work that has an explicit allowlisted runner. It never evaluates a
free-form command from evidence files and never mutates a public release gate.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


OWNER_DECISION = (
    "AUTHORIZE_SPRINT1_AUTONOMOUS_GO_LIVE_LOOP_V3_WITH_OPTIMIZED_DECISIONING_"
    "AND_175_USD_CAP"
)
FIXED_CAPS = {
    "SPRINT1_TOTAL_AUDIO_BUDGET_USD": "175",
    "SPRINT1_MAX_USD_PER_TITLE": "30",
    "MAX_TTS_BUDGET_USD": "175",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
    "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "20",
    "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
    "EARNALISM_ENABLE_OPENAI_LISTENING_QA": "true",
    "EARNALISM_OPENAI_LISTENING_QA_MODEL": "gpt-audio",
    "EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD": "40",
    "EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD": "20",
    "EARNALISM_ASR_SYNC_ESTIMATED_USD_PER_MINUTE": "0.008",
    "EARNALISM_APPROVE_GOOGLE_TTS_AUDITIONS": "true",
    "EARNALISM_GOOGLE_TTS_MAX_ESTIMATED_USD": "40",
    "EARNALISM_GOOGLE_TTS_ESTIMATED_USD_PER_1K_CHARS": "0.02",
    "EARNALISM_APPROVE_SARVAM_CORRECTIVE_AUDITIONS": "true",
    "EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF": "true",
    "EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS": "true",
}
BENGALI_CAMPAIGN_PAID_GATES = (
    "EARNALISM_APPROVE_BENGALI_31_AUDIO_CAMPAIGN",
    "EARNALISM_BENGALI_CAMPAIGN_MAX_ESTIMATED_USD",
    "EARNALISM_BENGALI_MAX_ESTIMATED_USD_PER_TITLE",
)
APPROVED_SLUGS_BASELINE = {"book-2b9853ec52", "a-ghost-story"}
DEFERRED_SLUGS = {"great-expectations", "jane-eyre"}
OWNER_DOCUMENT_SLUGS = {"pather-panchali"}
LONG_ENGLISH_SLUGS = {
    "dracula",
    "frankenstein",
    "pride-and-prejudice",
    "the-secret-garden",
    "picture-of-dorian-gray",
    "white-fang",
    "the-time-machine",
    "the-call-of-the-wild",
    "alices-adventures-in-wonderland",
}
SHORT_PRIORITY = {
    "the-gift-of-the-magi": 10,
    "the-tell-tale-heart": 11,
    "sredni-vashtar": 12,
    "the-cop-and-the-anthem": 13,
    "the-last-leaf": 14,
    "the-masque-of-the-red-death": 15,
    "the-yellow-wallpaper": 16,
    "the-monkeys-paw": 17,
    "the-necklace": 18,
    "dsires-baby": 19,
    "the-open-window": 20,
    "book-f5d593e1f4": 30,
    "muchiram-gurer-jibanchorit": 31,
    "radharani": 32,
    "nishkriti": 33,
    "book-d19e96859f": 34,
    "bn-066": 40,
    "devdas": 41,
    "book-edfcf810c5": 42,
}
HUMAN_STATUSES = {
    "HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED",
    "HUMAN_NARRATION_OR_ALTERNATE_PROVIDER_REQUIRED",
    "SOURCE_BOUND_HUMAN_NARRATION_OR_LICENSED_AUDIO_REQUIRED",
}
WAITING_EXTERNAL_AUDIO_STATE = (
    "WAITING_EXTERNAL_SOURCE_BOUND_NARRATION_OR_LICENSED_AUDIO"
)
EXTERNAL_AUDIO_FINAL_STATUS = "HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED"
EXTERNAL_AUDIO_MARKERS = (
    "HUMAN_NARRATION",
    "LICENSED_AUDIO",
    "AUTOMATED_PROVIDER_PLATEAU",
    "AUTOMATED_TTS_EXHAUSTED",
    "STOP_AUTOMATED",
)
APPROVED_TITLE_MARKERS = (
    "YES_PLUS_YES",
    "APPROVED_EXISTING_PUBLIC_AUDIO",
    "APPROVED_AND_LIVE",
    "BENGALI_AUDIOBOOK_LIVE",
)
ATTEMPT_SOURCE_PRIORITY = {
    "prior_registry": 10,
    "budget_identity": 30,
    "packet_metadata": 50,
    "title_decision_history": 60,
    "historical_title_evidence": 80,
    "canonical_title_release_evidence": 100,
}
ATTEMPT_COLLECTION_KEYS = (
    "provider_attempts",
    "failed_attempts",
    "attempts",
    "attempt_history",
    "representative_attempts",
    "representative_auditions",
)
FULL_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
PREFIX16_RE = re.compile(r"^[0-9a-fA-F]{16}$")
ACCEPTED_AUDIO_SUFFIXES = {".wav", ".flac", ".mp3"}
GOOGLE_ADC_PROBE_TIMEOUT_SECONDS = 8.0
REQUIRED_PACKET_FILES = {
    "clean_manuscript.txt",
    "delivery_checklist.md",
    "metadata.json",
    "narrator_brief.md",
    "qa_release_checklist.md",
}


class LoopError(RuntimeError):
    """Raised when a go-live safety invariant fails."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise LoopError(f"expected JSON object: {path}")
    return value


def atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def atomic_write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def canonical_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def secret_state(env: Mapping[str, str], key: str) -> str:
    return "SET" if env.get(key) else "MISSING"


def google_adc_probe(
    env: Mapping[str, str],
    *,
    timeout_seconds: float = GOOGLE_ADC_PROBE_TIMEOUT_SECONDS,
    runner: Any = subprocess.run,
) -> dict[str, Any]:
    """Refresh ADC non-interactively while discarding all command output."""
    command = [
        "gcloud",
        "auth",
        "application-default",
        "print-access-token",
        "--quiet",
    ]
    try:
        completed = runner(
            command,
            env=dict(env),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        outcome = "TIMEOUT"
        ready = False
    except OSError:
        outcome = "COMMAND_UNAVAILABLE"
        ready = False
    else:
        ready = completed.returncode == 0
        outcome = "SUCCESS" if ready else "NONZERO_EXIT"
    return {
        "ready": ready,
        "status": "GOOGLE_ADC_READY" if ready else "GOOGLE_ADC_REAUTH_REQUIRED",
        "outcome": outcome,
        "timeout_seconds": timeout_seconds,
        "token_output_exposed": False,
    }


def runtime_snapshot(
    env: Mapping[str, str],
    *,
    adc_probe: Any | None = None,
) -> dict[str, Any]:
    google_path = Path(env.get("GOOGLE_APPLICATION_CREDENTIALS", "")).expanduser()
    google_file_ready = bool(str(google_path)) and google_path.is_file()
    google_project_ready = bool(env.get("GOOGLE_CLOUD_PROJECT"))
    if google_project_ready:
        raw_adc = (adc_probe or google_adc_probe)(env)
        adc_ready = raw_adc.get("ready") is True
        adc = {
            "ready": adc_ready,
            "status": (
                "GOOGLE_ADC_READY" if adc_ready else "GOOGLE_ADC_REAUTH_REQUIRED"
            ),
            "outcome": str(raw_adc.get("outcome") or "UNKNOWN"),
            "timeout_seconds": float(
                raw_adc.get("timeout_seconds", GOOGLE_ADC_PROBE_TIMEOUT_SECONDS)
            ),
            "token_output_exposed": False,
        }
    else:
        adc_ready = False
        adc = {
            "ready": False,
            "status": "GOOGLE_CLOUD_PROJECT_MISSING",
            "outcome": "SKIPPED_PROJECT_MISSING",
            "timeout_seconds": GOOGLE_ADC_PROBE_TIMEOUT_SECONDS,
            "token_output_exposed": False,
        }
    google_ready = bool(google_project_ready and adc_ready)
    google_blocker = None
    if not google_project_ready:
        google_blocker = "GOOGLE_CLOUD_PROJECT_MISSING"
    elif not adc_ready:
        google_blocker = "GOOGLE_ADC_REAUTH_REQUIRED"
    campaign_missing = [key for key in BENGALI_CAMPAIGN_PAID_GATES if not env.get(key)]
    fixed_observed = {
        key: "MATCH" if env.get(key) == expected else "BOUND_BY_CHILD_PROCESS"
        for key, expected in FIXED_CAPS.items()
    }
    return {
        "fixed_caps": dict(FIXED_CAPS),
        "fixed_caps_enforcement": "BOUND_INLINE_FOR_EVERY_CHILD_PROCESS",
        "fixed_caps_observed_in_parent": fixed_observed,
        "credentials": {
            "GOOGLE_APPLICATION_CREDENTIALS": "SET_AND_READABLE" if google_file_ready else secret_state(env, "GOOGLE_APPLICATION_CREDENTIALS"),
            "GOOGLE_CLOUD_PROJECT": secret_state(env, "GOOGLE_CLOUD_PROJECT"),
            "GOOGLE_ADC": adc["status"],
            "OPENAI_API_KEY": secret_state(env, "OPENAI_API_KEY"),
            "SARVAM_API_KEY": secret_state(env, "SARVAM_API_KEY"),
        },
        "providers": {
            "google": google_ready,
            "openai_qa": bool(env.get("OPENAI_API_KEY")),
            "sarvam": bool(env.get("SARVAM_API_KEY")),
        },
        "provider_readiness": {
            "google": {
                "paid_ready": google_ready,
                "blocker": google_blocker,
                "credential_file_readable": google_file_ready,
                "adc_probe": adc,
            }
        },
        "bengali_campaign_paid_gates": {
            "ready": not campaign_missing,
            "missing": campaign_missing,
            "source": "internal/earnalism_intelligence/bengali_audiobook_campaign_policy.md",
        },
        "secrets_printed": False,
    }


def lock_snapshot(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    state = payload.get("state") if isinstance(payload.get("state"), dict) else payload
    status = state.get("status")
    active = state.get("active") is True or status == "active"
    holder = state.get("current_holder")
    allowed = state.get("allowed_next_holders")
    return {
        "path": str(path),
        "status": status,
        "active": active,
        "current_holder": holder,
        "allowed_next_holders": allowed,
        "available": active and holder in {None, "none"} and allowed == [],
        "approved_scope": state.get("approved_scope"),
        "allowed_slugs": state.get("allowed_slugs", []),
        "budget_cap_usd": state.get("budget_cap_usd"),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def active_rows(matrix: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in matrix.get("titles", []):
        if not isinstance(row, dict) or not row.get("slug"):
            continue
        if row.get("sprint1_audio_target") is not True:
            continue
        if row["slug"] in DEFERRED_SLUGS:
            continue
        rows.append(dict(row))
    return rows


def is_yes_yes(row: Mapping[str, Any]) -> bool:
    return (
        row.get("publicly_rendered_book") == "Yes"
        and row.get("publicly_available_audiobook") == "Yes"
        and row.get("exact_blocker") in {None, "", "NONE"}
    )


def first_present(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def mapping_value(value: Mapping[str, Any], *keys: str) -> Any:
    return first_present(*(value.get(key) for key in keys))


def attempt_failed(attempt: Mapping[str, Any], default: bool = True) -> bool:
    if isinstance(attempt.get("failed"), bool):
        return bool(attempt["failed"])
    status = " ".join(
        str(value).upper()
        for value in (
            attempt.get("status"),
            attempt.get("result"),
            attempt.get("classification"),
            attempt.get("release_gate_state"),
        )
        if value
    )
    failure_markers = (
        "FAIL",
        "BLOCKED",
        "ERROR",
        "UNSUPPORTED",
        "BELOW",
        "REJECT",
        "QUALITY_LIMIT",
        "REPAIR_REQUIRED",
        "MISMATCH",
        *EXTERNAL_AUDIO_MARKERS,
    )
    if any(marker in status for marker in failure_markers):
        return True
    if any(marker in status for marker in ("PASS", "APPROVED", "VALIDATED", "READY", "COMPLETE")):
        return False
    return default


def attempt_family(attempt: Mapping[str, Any]) -> str:
    parts = [
        attempt.get("provider"),
        attempt.get("model"),
        attempt.get("voice") or attempt.get("voice_profile"),
        attempt.get("style_profile") or attempt.get("style"),
        attempt.get("text_prep_variant"),
        attempt.get("postprocess_variant"),
        attempt.get("scope"),
    ]
    return ":".join(str(part or "unknown").lower() for part in parts)


def fingerprint_type(value: str) -> str:
    if FULL_SHA256_RE.fullmatch(value):
        return "full_sha256"
    if PREFIX16_RE.fullmatch(value):
        return "prefix16"
    return "opaque"


def identity_payload(attempt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: attempt.get(key)
        for key in (
            "provider",
            "model",
            "voice",
            "style",
            "style_profile",
            "scope",
            "speaking_rate",
            "language",
            "text_sha256",
            "prepared_text_sha256",
            "source_sha256",
            "prep_sha256",
            "prep_identity",
            "text_prep_variant",
            "postprocess_sha256",
            "postprocess_identity",
            "postprocess_variant",
        )
    }


def normalize_attempt(
    attempt: Mapping[str, Any],
    evidence_default: str,
    *,
    evidence_kind: str = "packet_metadata",
    defaults: Mapping[str, Any] | None = None,
    fingerprint_native: bool = True,
) -> dict[str, Any]:
    defaults = defaults or {}

    def identity(name: str, *aliases: str) -> Any:
        return first_present(
            *(attempt.get(key) for key in (name, *aliases)),
            defaults.get(name),
        )

    scores = attempt.get("scores")
    numeric_scores = (
        [float(value) for value in scores if isinstance(value, (int, float))]
        if isinstance(scores, list)
        else []
    )
    score_from_mapping = (
        scores.get("overall_listening_score") if isinstance(scores, dict) else None
    )
    minimum_score = first_present(
        attempt.get("minimum_observed_score"),
        attempt.get("minimum_score"),
        attempt.get("minimum_overall_score"),
        attempt.get("listening_minimum_score"),
        min(numeric_scores) if numeric_scores else None,
        score_from_mapping,
    )
    confidence = first_present(
        attempt.get("confidence"),
        attempt.get("minimum_confidence"),
        attempt.get("listening_minimum_confidence"),
        scores.get("confidence_score") if isinstance(scores, dict) else None,
    )
    language = identity("language", "language_code")
    if isinstance(language, dict):
        language = first_present(language.get("code"), language.get("name"))
    normalized: dict[str, Any] = {
        "provider": identity("provider") or "unknown",
        "model": identity("model"),
        "voice": identity("voice", "voice_profile"),
        "style": identity("style"),
        "style_profile": identity("style_profile", "profile", "style"),
        "scope": identity("scope"),
        "speaking_rate": identity("speaking_rate"),
        "language": language,
        "text_sha256": identity("text_sha256", "passage_hash", "source_text_sha256"),
        "prepared_text_sha256": identity("prepared_text_sha256", "prepared_sha256"),
        "source_sha256": identity("source_sha256", "source_hash", "controlled_source_hash"),
        "prep_sha256": identity(
            "prep_sha256",
            "prep_fingerprint_sha256",
            "audition_input_manifest_sha256",
            "input_manifest_sha256",
            "audition_manifest_sha256",
        ),
        "prep_identity": identity("prep_identity"),
        "text_prep_variant": identity(
            "text_prep_variant", "prep_variant", "preparation_variant"
        ),
        "postprocess_sha256": identity(
            "postprocess_sha256", "postprocess_fingerprint_sha256"
        ),
        "postprocess_identity": identity("postprocess_identity"),
        "postprocess_variant": identity(
            "postprocess_variant", "post_processing_variant"
        ),
        "status": attempt.get("status") or attempt.get("result"),
        "failed": attempt_failed(attempt),
        "minimum_observed_score": minimum_score,
        "confidence": confidence,
        "fatal_flags": attempt.get("fatal_flags") or [],
        "scores": scores,
        "evidence": attempt.get("evidence") or attempt.get("evidence_path") or evidence_default,
        "evidence_kind": evidence_kind,
        "_priority": ATTEMPT_SOURCE_PRIORITY[evidence_kind],
    }
    normalized["family"] = attempt_family(normalized)
    normalized["registry_identity_sha256"] = canonical_sha256(identity_payload(normalized))
    normalized["registry_identity_provenance"] = (
        "DERIVED_FOR_REGISTRY_DEDUPLICATION_NOT_PROVIDER_NATIVE"
    )

    fingerprint_field = None
    fingerprint = attempt.get("attempt_fingerprint")
    if isinstance(fingerprint, str) and fingerprint:
        fingerprint_field = "attempt_fingerprint"
    else:
        fingerprint = attempt.get("fingerprint")
        if isinstance(fingerprint, str) and fingerprint:
            fingerprint_field = "fingerprint"
        else:
            fingerprint = None
    provenance = attempt.get("fingerprint_provenance")
    provider_native = False
    if fingerprint_native and isinstance(provenance, dict) and isinstance(provenance.get("provider_native"), bool):
        provider_native = bool(provenance["provider_native"])
    elif fingerprint_native and isinstance(attempt.get("fingerprint_is_provider_native"), bool):
        provider_native = bool(attempt["fingerprint_is_provider_native"])
    if fingerprint:
        if fingerprint_native:
            normalized["attempt_fingerprint"] = fingerprint
            normalized["fingerprint_type"] = fingerprint_type(fingerprint)
        else:
            normalized["reported_non_native_fingerprint"] = fingerprint
            normalized["reported_non_native_fingerprint_type"] = fingerprint_type(
                fingerprint
            )
            normalized["fingerprint_type"] = "none"
        normalized["fingerprint_is_evidence_native"] = fingerprint_native
        normalized["fingerprint_is_provider_native"] = provider_native
        normalized["fingerprint_is_synthetic"] = False
        normalized["fingerprint_provenance"] = {
            "source": evidence_kind,
            "field": fingerprint_field,
            "evidence_native": fingerprint_native,
            "provider_native": provider_native,
            "synthetic": False,
        }
    else:
        normalized["fingerprint_type"] = "none"
        normalized["fingerprint_is_evidence_native"] = False
        normalized["fingerprint_is_provider_native"] = False
        normalized["fingerprint_is_synthetic"] = False
        normalized["fingerprint_provenance"] = {
            "source": "none",
            "field": None,
            "evidence_native": False,
            "provider_native": False,
            "synthetic": False,
        }
    return normalized


def evidence_identity_defaults(payload: Mapping[str, Any]) -> dict[str, Any]:
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    source_binding = (
        payload.get("source_binding")
        if isinstance(payload.get("source_binding"), dict)
        else {}
    )
    source_preflight = (
        payload.get("source_preflight")
        if isinstance(payload.get("source_preflight"), dict)
        else {}
    )
    selected_arm = source_preflight.get("selected_arm") or payload.get("selected_arm")
    if not isinstance(selected_arm, dict):
        selected_arm = {}
    return {
        "provider": first_present(payload.get("provider"), selected_arm.get("provider")),
        "model": first_present(payload.get("model"), selected_arm.get("model")),
        "voice": first_present(payload.get("voice"), selected_arm.get("voice")),
        "style": first_present(payload.get("style"), selected_arm.get("style")),
        "style_profile": first_present(
            payload.get("style_profile"),
            selected_arm.get("style_profile"),
            payload.get("style"),
            selected_arm.get("style"),
        ),
        "language": payload.get("language"),
        "text_sha256": first_present(
            source.get("text_sha256"),
            source_binding.get("audition_sanitized_source_sha256"),
            source_binding.get("sanitized_manuscript_sha256"),
        ),
        "prepared_text_sha256": first_present(
            source.get("prepared_text_sha256"),
            source_preflight.get("prepared_sha256"),
            payload.get("prepared_text_sha256"),
        ),
        "source_sha256": first_present(
            source.get("source_sha256"),
            source_preflight.get("source_sha256"),
            source_binding.get("controlled_source_hash"),
            source_binding.get("source_hash"),
        ),
        "prep_sha256": first_present(
            source.get("prep_sha256"),
            source_binding.get("audition_input_manifest_sha256"),
        ),
        "prep_identity": first_present(
            source.get("prep_identity"), payload.get("prep_identity")
        ),
        "text_prep_variant": first_present(
            source.get("text_prep_variant"), payload.get("text_prep_variant")
        ),
        "postprocess_sha256": first_present(
            source.get("postprocess_sha256"), payload.get("postprocess_sha256")
        ),
        "postprocess_identity": first_present(
            source.get("postprocess_identity"), payload.get("postprocess_identity")
        ),
        "postprocess_variant": first_present(
            source.get("postprocess_variant"), payload.get("postprocess_variant")
        ),
    }


def inferred_scope(status: Any, approved: bool = False) -> str:
    status_text = str(status or "").upper()
    if approved:
        return "full_book_release"
    if "FULL" in status_text or "ASR_SOURCE" in status_text:
        return "full_book_qa"
    if "AUDITION" in status_text:
        return "representative_audition"
    return "title_release_evidence"


def extract_attempts_from_evidence(
    payload: Mapping[str, Any],
    evidence_path: str,
    evidence_kind: str,
    *,
    canonical: bool = False,
    historical: bool = False,
) -> list[dict[str, Any]]:
    defaults = evidence_identity_defaults(payload)
    attempts: list[dict[str, Any]] = []

    def add(raw: Mapping[str, Any], scope: str | None = None, extra: Mapping[str, Any] | None = None) -> None:
        candidate = dict(extra or {})
        candidate.update(raw)
        if scope and not candidate.get("scope"):
            candidate["scope"] = scope
        attempts.append(
            normalize_attempt(
                candidate,
                evidence_path,
                evidence_kind=evidence_kind,
                defaults=defaults,
            )
        )

    for key in ATTEMPT_COLLECTION_KEYS:
        collection = payload.get(key)
        if isinstance(collection, list):
            for item in collection:
                if isinstance(item, dict):
                    add(item, key)

    replacement = payload.get("stage2d_replacement_auditions")
    if isinstance(replacement, dict) and not payload.get("provider_attempts"):
        replacement_defaults = {
            key: replacement.get(key)
            for key in ("provider", "model", "voice", "style", "style_profile")
        }
        for key, item in replacement.items():
            if isinstance(item, dict):
                add(item, key, replacement_defaults)

    listening_qa = payload.get("listening_qa")
    bounded = payload.get("bounded_audition")
    if isinstance(bounded, dict):
        combined = dict(bounded)
        if isinstance(listening_qa, dict):
            combined.update(
                {
                    "status": listening_qa.get("status"),
                    "scores": listening_qa.get("scores"),
                    "minimum_score": listening_qa.get("minimum_score"),
                    "minimum_confidence": listening_qa.get("minimum_confidence"),
                    "fatal_flags": listening_qa.get("fatal_flags"),
                    "evidence": listening_qa.get("evidence_path"),
                }
            )
        add(combined, "bounded_representative_audition")
    for key in ("alternate_voice_audition", "stage2e_studio_b_final_audition"):
        item = payload.get(key)
        if isinstance(item, dict):
            add(item, key)

    selected_representative: dict[str, Any] = {}
    representatives = payload.get("representative_auditions")
    if isinstance(representatives, list):
        for item in representatives:
            if isinstance(item, dict) and not attempt_failed(item):
                selected_representative = {
                    key: item.get(key)
                    for key in (
                        "provider",
                        "model",
                        "voice",
                        "style",
                        "style_profile",
                        "speaking_rate",
                    )
                }
    for key in ("full_candidate", "targeted_repair", "repaired_full_candidate"):
        item = payload.get(key)
        if isinstance(item, dict):
            add(item, key, selected_representative)

    top_fingerprint = payload.get("attempt_fingerprint") or payload.get("fingerprint")
    has_native_top_fingerprint = isinstance(top_fingerprint, str) and bool(top_fingerprint)
    has_top_identity = any(defaults.get(key) for key in ("provider", "model", "voice"))
    if has_top_identity and (canonical or has_native_top_fingerprint):
        status = first_present(
            payload.get("status"),
            payload.get("final_status"),
            payload.get("release_gate_state"),
            payload.get("classification"),
        )
        approved = bool(
            payload.get("can_publish_audio_now") is True
            or payload.get("publicly_available_audiobook") == "Yes"
            or any(marker in str(status or "").upper() for marker in APPROVED_TITLE_MARKERS)
        )
        top = {
            key: payload.get(key)
            for key in (
                "provider",
                "model",
                "voice",
                "style",
                "style_profile",
                "profile",
                "speaking_rate",
                "language",
                "attempt_fingerprint",
                "fingerprint",
                "source_hash",
                "source_sha256",
                "passage_hash",
                "prepared_text_sha256",
                "text_prep_variant",
                "postprocess_variant",
                "prosody",
            )
        }
        if top.get("prosody") and not top.get("postprocess_variant"):
            top["postprocess_variant"] = top["prosody"]
        top.update(
            {
                "scope": inferred_scope(status, approved),
                "status": status,
                "failed": False if approved else attempt_failed(payload),
                "minimum_observed_score": first_present(
                    payload.get("minimum_overall_score"),
                    payload.get("listening_qa_minimum_score"),
                ),
                "confidence": first_present(
                    payload.get("minimum_confidence"),
                    payload.get("listening_qa_minimum_confidence"),
                ),
                "fatal_flags": payload.get("fatal_flags") or [],
            }
        )
        add(top)
    elif historical:
        # Historical files without a native attempt fingerprint are too ambiguous
        # to become standalone provider attempts.
        pass
    return attempts


def fingerprints_match(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_value = first_present(
        left.get("attempt_fingerprint"), left.get("reported_non_native_fingerprint")
    )
    right_value = first_present(
        right.get("attempt_fingerprint"), right.get("reported_non_native_fingerprint")
    )
    if not isinstance(left_value, str) or not isinstance(right_value, str):
        return False
    if left_value == right_value:
        return True
    if len(left_value) == 16 and len(right_value) == 64:
        return right_value.startswith(left_value)
    if len(right_value) == 16 and len(left_value) == 64:
        return left_value.startswith(right_value)
    return False


def attempt_identities_compatible(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> bool:
    if left.get("attempt_fingerprint") or right.get("attempt_fingerprint"):
        return False
    left_provider = str(left.get("provider") or "unknown").lower()
    right_provider = str(right.get("provider") or "unknown").lower()
    if "unknown" in {left_provider, right_provider} or left_provider != right_provider:
        return False

    shared_identity = False
    for key in identity_payload(left):
        if key == "provider":
            continue
        left_value = left.get(key)
        right_value = right.get(key)
        if left_value in (None, "") or right_value in (None, ""):
            continue
        if left_value != right_value:
            return False
        shared_identity = True
    return shared_identity


def merge_attempt(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    high, low = (
        (right, left)
        if int(right.get("_priority", 0)) >= int(left.get("_priority", 0))
        else (left, right)
    )
    merged = dict(low)
    for key, value in high.items():
        if value is not None and value != "" and value != []:
            merged[key] = value

    fingerprint_candidates = [
        item
        for item in (left, right)
        if isinstance(item.get("attempt_fingerprint"), str)
    ]
    if fingerprint_candidates:
        full = [
            item
            for item in fingerprint_candidates
            if item.get("fingerprint_type") == "full_sha256"
        ]
        chosen = max(
            full or fingerprint_candidates,
            key=lambda item: int(item.get("_priority", 0)),
        )
        for key in (
            "attempt_fingerprint",
            "fingerprint_type",
            "fingerprint_is_evidence_native",
            "fingerprint_is_provider_native",
            "fingerprint_is_synthetic",
            "fingerprint_provenance",
        ):
            if key in chosen:
                merged[key] = chosen[key]
        reported = merged.get("reported_non_native_fingerprint")
        if isinstance(reported, str) and fingerprints_match(
            {"attempt_fingerprint": merged.get("attempt_fingerprint")},
            {"attempt_fingerprint": reported},
        ):
            merged.pop("reported_non_native_fingerprint", None)
            merged.pop("reported_non_native_fingerprint_type", None)
    evidence_paths = {
        str(value)
        for item in (left, right)
        for value in (
            [item.get("evidence")]
            + list(item.get("evidence_paths") or [])
        )
        if value
    }
    merged["evidence_paths"] = sorted(evidence_paths)
    merged["evidence_kinds"] = sorted(
        {
            str(value)
            for item in (left, right)
            for value in ([item.get("evidence_kind")] + list(item.get("evidence_kinds") or []))
            if value
        }
    )
    merged["_priority"] = max(int(left.get("_priority", 0)), int(right.get("_priority", 0)))
    return merged


def deduplicate_attempts(attempts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    deduplicated: list[dict[str, Any]] = []
    for attempt in attempts:
        match_index = next(
            (
                index
                for index, existing in enumerate(deduplicated)
                if fingerprints_match(existing, attempt)
                or existing.get("registry_identity_sha256")
                == attempt.get("registry_identity_sha256")
                or attempt_identities_compatible(existing, attempt)
            ),
            None,
        )
        if match_index is None:
            item = dict(attempt)
            item["evidence_paths"] = sorted(
                {str(value) for value in (item.get("evidence"),) if value}
            )
            item["evidence_kinds"] = [str(item["evidence_kind"])]
            deduplicated.append(item)
        else:
            deduplicated[match_index] = merge_attempt(deduplicated[match_index], attempt)
    finalized: list[dict[str, Any]] = []
    for item in deduplicated:
        item["family"] = attempt_family(item)
        item["registry_identity_sha256"] = canonical_sha256(identity_payload(item))
        item.pop("_priority", None)
        finalized.append(item)
    return sorted(
        finalized,
        key=lambda item: str(
            item.get("attempt_fingerprint") or item["registry_identity_sha256"]
        ),
    )


def coerce_mapping(value: Mapping[str, Any] | Path | None) -> dict[str, Any]:
    if isinstance(value, Path):
        return load_json(value) if value.is_file() else {}
    return dict(value or {})


def display_path(path: Path, asset_root: Path | None) -> str:
    if asset_root:
        try:
            return str(path.resolve().relative_to(asset_root.resolve()))
        except ValueError:
            pass
    return str(path)


def load_nonpaid_preflight_results(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "present": False, "titles": {}}
    payload = load_json(path)
    titles: dict[str, dict[str, Any]] = {}
    for index, result in enumerate(payload.get("results", [])):
        if not isinstance(result, dict) or not result.get("slug"):
            continue
        item = dict(result)
        item["result_order"] = index
        titles[str(result["slug"])] = item
    return {
        "path": str(path),
        "present": True,
        "generated_at": payload.get("generated_at"),
        "provider_calls_ran": payload.get("provider_calls_ran"),
        "titles": titles,
    }


def title_from_budget_record(
    record: Mapping[str, Any], slugs: Sequence[str]
) -> str | None:
    explicit = record.get("slug")
    if explicit in slugs:
        return str(explicit)
    serialized = json.dumps(record, ensure_ascii=False).lower()
    for slug in sorted(slugs, key=len, reverse=True):
        if slug.lower() in serialized:
            return slug
    normalized = re.sub(r"[^a-z0-9]+", "_", serialized)
    aliases = {
        "book-d19e96859f": ("d19", "book_d19e96859f"),
        "the-gift-of-the-magi": ("gift", "gift_of_the_magi"),
        "the-tell-tale-heart": ("tell_tale", "tell_tale_heart"),
        "sredni-vashtar": ("sredni", "sredni_vashtar"),
    }
    for slug, values in aliases.items():
        if slug in slugs and any(value in normalized for value in values):
            return slug
    return None


def budget_stage_identity(stage: str, slug: str) -> dict[str, Any]:
    normalized = stage.lower().replace("-", "_")
    identity: dict[str, Any] = {"scope": stage}
    if "sarvam" in normalized:
        identity["provider"] = "sarvam"
    elif "openai" in normalized:
        identity["provider"] = "openai"
    elif "google" in normalized or "studio_" in normalized or "chirp" in normalized:
        identity["provider"] = "google"
    if "gpt4o_transcribe" in normalized or "gpt_4o_transcribe" in normalized:
        identity["model"] = "gpt-4o-transcribe"
    elif "latest_long" in normalized:
        identity["model"] = "latest_long"
    elif "bulbul_v3" in normalized:
        identity["model"] = "bulbul:v3"
    language_prefix = "bn-IN" if slug.startswith("book-") and "d19" in slug else "en-GB"
    if "studio_c" in normalized:
        identity["voice"] = "en-GB-Studio-C"
    elif "studio_b" in normalized:
        identity["voice"] = "en-GB-Studio-B"
    elif "chirp3_hd_achird" in normalized or "chirp_achird" in normalized:
        identity["voice"] = f"{language_prefix}-Chirp3-HD-Achird"
    elif "chirp3_hd_aoede" in normalized or "chirp_aoede" in normalized or "aoede" in normalized:
        identity["voice"] = f"{language_prefix}-Chirp3-HD-Aoede"
    elif "pooja" in normalized:
        identity["voice"] = "pooja"
    elif "ratan" in normalized:
        identity["voice"] = "ratan"
    if identity.get("provider") == "google" and identity.get("voice") and not identity.get("model"):
        identity["model"] = "google-cloud-texttospeech"
    if "dialogue_human_touch" in normalized:
        identity["style"] = "dialogue_human_touch"
        identity["style_profile"] = "dialogue_human_touch"
    elif "literary_warm_pacing" in normalized:
        identity["style"] = "literary_warm_pacing"
        identity["style_profile"] = "literary_warm_pacing"
    if "source_preserving_ssml_88_percent" in normalized:
        identity["text_prep_variant"] = "source_preserving_ssml_88_percent"
    return identity


def referenced_attempt_defaults(
    attempt: Mapping[str, Any],
    slug: str,
    asset_root: Path | None,
    defaults: Mapping[str, Any],
) -> dict[str, Any]:
    resolved = dict(defaults)
    evidence = first_present(attempt.get("evidence"), attempt.get("evidence_path"))
    identity_source = str(evidence or "")
    if isinstance(evidence, str) and asset_root:
        evidence_path = asset_root / evidence
        if evidence_path.is_file():
            try:
                payload = load_json(evidence_path)
            except (OSError, UnicodeError, json.JSONDecodeError, LoopError):
                payload = {}
            for key, value in evidence_identity_defaults(payload).items():
                if value not in (None, ""):
                    resolved[key] = value
            identity_source = " ".join(
                str(value)
                for value in (
                    identity_source,
                    payload.get("audio_path"),
                    payload.get("private_audio_path"),
                    payload.get("provider"),
                    payload.get("model"),
                    payload.get("voice"),
                    payload.get("style"),
                    payload.get("style_profile"),
                )
                if value
            )
    for key, value in budget_stage_identity(identity_source, slug).items():
        if key != "scope" and value not in (None, ""):
            resolved[key] = value
    return resolved


def budget_attempts(
    budget: Mapping[str, Any],
    slugs: Sequence[str],
    asset_root: Path | None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[str]]]:
    attempts = {slug: [] for slug in slugs}
    stages = {slug: [] for slug in slugs}
    for key in ("attempt_identities", "title_identities", "provider_attempts"):
        collection = budget.get(key)
        if isinstance(collection, dict):
            for slug, items in collection.items():
                if slug not in attempts:
                    continue
                for item in items if isinstance(items, list) else [items]:
                    if isinstance(item, dict):
                        attempts[slug].append(
                            normalize_attempt(
                                item,
                                "sprint1_budget_ledger.json",
                                evidence_kind="budget_identity",
                            )
                        )
    for record in budget.get("checkpoint_chain_tail", []):
        if not isinstance(record, dict):
            continue
        slug = title_from_budget_record(record, slugs)
        if not slug:
            continue
        stage = str(record.get("stage") or "budget_checkpoint")
        stages[slug].append(stage)
        raw = budget_stage_identity(stage, slug)
        raw["status"] = record.get("result")
        raw["failed"] = attempt_failed(raw, default=False)
        evidence = record.get("evidence")
        if isinstance(evidence, str):
            prefix_match = re.search(r"/(?:audition/)?([0-9a-fA-F]{16})(?:/|\.json)", evidence)
            if prefix_match:
                raw["fingerprint"] = prefix_match.group(1)
        if raw.get("fingerprint") or (raw.get("provider") and raw.get("model")):
            attempts[slug].append(
                normalize_attempt(
                    raw,
                    str(evidence or "sprint1_budget_ledger.json"),
                    evidence_kind="budget_identity",
                )
            )
        if isinstance(evidence, str) and asset_root:
            evidence_path = asset_root / evidence
            if evidence_path.is_file():
                try:
                    payload = load_json(evidence_path)
                except (OSError, UnicodeError, json.JSONDecodeError, LoopError):
                    continue
                attempts[slug].extend(
                    extract_attempts_from_evidence(
                        payload,
                        evidence,
                        "budget_identity",
                        historical=True,
                    )
                )
    return attempts, stages


def title_is_approved(
    row: Mapping[str, Any],
    canonical: Mapping[str, Any],
    history: Mapping[str, Any],
) -> bool:
    if is_yes_yes(row):
        return True
    if canonical.get("can_publish_audio_now") is True:
        return True
    if canonical.get("publicly_available_audiobook") == "Yes" or canonical.get("public_audio") is True:
        return True
    labels = " ".join(
        str(value).upper()
        for value in (
            canonical.get("release_gate_state"),
            canonical.get("final_status"),
            history.get("bengali_audiobook_release_gate"),
        )
        if value
    )
    return any(marker in labels for marker in APPROVED_TITLE_MARKERS)


def title_requires_external_audio(*values: Any) -> bool:
    text = " ".join(str(value).upper() for value in values if value)
    return any(marker in text for marker in EXTERNAL_AUDIO_MARKERS)


def build_failure_registry(
    rows: Sequence[Mapping[str, Any]],
    packets_root: Path,
    previous: Mapping[str, Any] | None = None,
    title_runs_root: Path | None = None,
    title_decision_history: Mapping[str, Any] | Path | None = None,
    budget_ledger: Mapping[str, Any] | Path | None = None,
    asset_root: Path | None = None,
) -> dict[str, Any]:
    title_runs_root = title_runs_root or packets_root.parent / "title_runs"
    if asset_root is None and len(packets_root.parents) >= 4:
        asset_root = packets_root.parents[3]
    if title_decision_history is None and len(packets_root.parents) >= 3:
        title_decision_history = (
            packets_root.parents[2] / "earnalism_intelligence/title_decision_history.json"
        )
    if budget_ledger is None:
        budget_ledger = packets_root.parent / "sprint1_budget_ledger.json"
    history_payload = coerce_mapping(title_decision_history)
    history_titles = history_payload.get("titles", {})
    if not isinstance(history_titles, dict):
        history_titles = {}
    budget_payload = coerce_mapping(budget_ledger)
    slugs = [str(row["slug"]) for row in rows]
    budget_by_slug, budget_stages = budget_attempts(budget_payload, slugs, asset_root)
    previous_titles = (previous or {}).get("titles", {})
    previous_schema = int((previous or {}).get("schema_version") or 1)
    titles: dict[str, Any] = {}

    for row in rows:
        slug = str(row["slug"])
        packet_metadata = packets_root / slug / "metadata.json"
        canonical_path = title_runs_root / f"{slug}_release_gate_evidence.json"
        canonical = load_json(canonical_path) if canonical_path.is_file() else {}
        history = history_titles.get(slug, {})
        if not isinstance(history, dict):
            history = {}
        attempts: list[dict[str, Any]] = list(budget_by_slug.get(slug, []))
        evidence_paths: set[str] = set()

        fresh_evidence_available = bool(
            canonical
            or history
            or packet_metadata.is_file()
            or budget_by_slug.get(slug)
        )
        previous_attempts = (
            []
            if fresh_evidence_available
            else previous_titles.get(slug, {}).get("attempts", [])
        )
        for attempt in previous_attempts:
            evidence_kinds = (
                set(attempt.get("evidence_kinds") or [])
                if isinstance(attempt, dict)
                else set()
            )
            if isinstance(attempt, dict) and attempt.get("evidence_kind"):
                evidence_kinds.add(str(attempt["evidence_kind"]))
            if (
                isinstance(attempt, dict)
                and previous_schema >= 2
                and evidence_kinds
                and evidence_kinds != {"prior_registry"}
            ):
                attempts.append(
                    normalize_attempt(
                        attempt,
                        "prior_registry",
                        evidence_kind="prior_registry",
                        fingerprint_native=bool(
                            attempt.get("fingerprint_is_evidence_native")
                        ),
                    )
                )

        if packet_metadata.is_file():
            metadata = load_json(packet_metadata)
            prior = metadata.get("prior_provider_evidence") or {}
            if isinstance(prior, dict):
                evidence_paths.update(str(item) for item in prior.get("evidence_paths", []))
                packet_identity = evidence_identity_defaults(metadata)
                packet_defaults = evidence_identity_defaults(prior)
                for key in (
                    "language",
                    "text_sha256",
                    "prepared_text_sha256",
                    "source_sha256",
                ):
                    if not packet_defaults.get(key):
                        packet_defaults[key] = packet_identity.get(key)
                for key in ("provider_attempts", "failed_attempts"):
                    for attempt in prior.get(key, []):
                        if isinstance(attempt, dict):
                            attempts.append(
                                normalize_attempt(
                                    attempt,
                                    display_path(packet_metadata, asset_root),
                                    evidence_kind="packet_metadata",
                                    defaults=referenced_attempt_defaults(
                                        attempt,
                                        slug,
                                        asset_root,
                                        packet_defaults,
                                    ),
                                )
                            )

        if history:
            history_path = "internal/earnalism_intelligence/title_decision_history.json"
            evidence_paths.add(history_path)
            for key in ATTEMPT_COLLECTION_KEYS:
                collection = history.get(key)
                if isinstance(collection, list):
                    for attempt in collection:
                        if isinstance(attempt, dict):
                            attempts.append(
                                normalize_attempt(
                                    attempt,
                                    history_path,
                                    evidence_kind="title_decision_history",
                                    defaults=evidence_identity_defaults(history),
                                )
                            )
            repair = history.get("bengali_audiobook_repair")
            repair_identity = None
            if isinstance(repair, dict):
                repair_identity = {
                    key: repair.get(key)
                    for key in (
                        "tts_input_clean",
                        "tts_by_construction_verified_for_planned_sequence",
                    )
                    if key in repair
                }
            history_identity = {
                "provider": first_present(history.get("selected_provider"), history.get("provider")),
                "model": first_present(history.get("selected_model"), history.get("model")),
                "voice": first_present(history.get("selected_voice"), history.get("voice")),
                "style": first_present(history.get("selected_style"), history.get("style")),
                "style_profile": first_present(
                    history.get("style_profile"),
                    history.get("selected_style"),
                    history.get("style"),
                ),
                "language": history.get("language"),
                "text_sha256": history.get("text_sha256"),
                "prepared_text_sha256": history.get("prepared_text_sha256"),
                "source_sha256": history.get("source_sha256"),
                "prep_sha256": history.get("prep_sha256"),
                "prep_identity": first_present(
                    history.get("prep_identity"), repair_identity
                ),
                "text_prep_variant": history.get("text_prep_variant"),
                "postprocess_sha256": history.get("postprocess_sha256"),
                "postprocess_identity": history.get("postprocess_identity"),
                "postprocess_variant": history.get("postprocess_variant"),
                "scope": (
                    "full_book_qa"
                    if history.get("private_full_tts_status")
                    or history.get("full_private_listening_scores")
                    else inferred_scope(history.get("latest_decision"))
                ),
                "status": history.get("latest_decision"),
                "failed": attempt_failed(
                    {"status": history.get("latest_decision")}, default=False
                ),
                "fatal_flags": history.get("fatal_flags") or [],
                "minimum_observed_score": first_present(
                    history.get("listening_score"),
                    min(history.get("full_private_listening_scores") or [])
                    if history.get("full_private_listening_scores")
                    else None,
                ),
                "confidence": first_present(
                    history.get("listening_confidence"),
                    history.get("minimum_listening_confidence"),
                ),
            }
            if history_identity.get("provider") and any(
                history_identity.get(key)
                for key in (
                    "model",
                    "voice",
                    "style",
                    "style_profile",
                    "text_sha256",
                    "prepared_text_sha256",
                    "source_sha256",
                    "prep_sha256",
                    "prep_identity",
                    "text_prep_variant",
                    "postprocess_sha256",
                    "postprocess_identity",
                    "postprocess_variant",
                )
            ):
                attempts.append(
                    normalize_attempt(
                        history_identity,
                        history_path,
                        evidence_kind="title_decision_history",
                    )
                )
            forensics = history.get("bengali_audiobook_forensics")
            if isinstance(forensics, dict) and any(
                history_identity.get(key) for key in ("provider", "model", "voice")
            ):
                raw_asr_score = forensics.get("asr_score")
                forensics_failed = (
                    forensics.get("tts_by_construction_verified") is False
                    or isinstance(raw_asr_score, (int, float))
                    and float(raw_asr_score) < 9.7
                )
                if forensics_failed:
                    attempts.append(
                        normalize_attempt(
                            {
                                **history_identity,
                                "scope": "historical_pre_repair_full_candidate",
                                "status": "BLOCKED_TITLE_DECISION_HISTORY_FORENSICS",
                                "failed": True,
                                "minimum_observed_score": forensics.get(
                                    "representative_score"
                                ),
                                "prep_identity": {
                                    "tts_by_construction_verified": forensics.get(
                                        "tts_by_construction_verified"
                                    )
                                },
                                "evidence": forensics.get(
                                    "source_provenance_report_path"
                                )
                                or history_path,
                            },
                            history_path,
                            evidence_kind="title_decision_history",
                        )
                    )

        if canonical:
            canonical_display = display_path(canonical_path, asset_root)
            evidence_paths.add(canonical_display)
            attempts.extend(
                extract_attempts_from_evidence(
                    canonical,
                    canonical_display,
                    "canonical_title_release_evidence",
                    canonical=True,
                )
            )

        approved = title_is_approved(row, canonical, history)
        if approved and title_runs_root.is_dir():
            for path in sorted(title_runs_root.glob(f"{slug}_*.json")):
                if path == canonical_path:
                    continue
                try:
                    payload = load_json(path)
                except (OSError, UnicodeError, json.JSONDecodeError, LoopError):
                    continue
                if payload.get("slug") != slug:
                    continue
                historical_attempts = extract_attempts_from_evidence(
                    payload,
                    display_path(path, asset_root),
                    "historical_title_evidence",
                    historical=True,
                )
                if historical_attempts:
                    evidence_paths.add(display_path(path, asset_root))
                    attempts.extend(historical_attempts)

        attempts = deduplicate_attempts(attempts)
        for attempt in attempts:
            evidence_paths.update(attempt.get("evidence_paths", []))
        failed_families = sorted(
            {
                item["family"]
                for item in attempts
                if item.get("failed")
                and str(item.get("provider") or "unknown").lower() != "unknown"
            }
        )
        canonical_classification = first_present(
            canonical.get("classification"),
            canonical.get("release_gate_state"),
            canonical.get("final_status"),
            canonical.get("status"),
        )
        history_classification = first_present(
            history.get("latest_decision"),
            history.get("bengali_audiobook_campaign_state"),
        )
        external_audio = title_requires_external_audio(
            canonical_classification,
            canonical.get("next_action"),
            history_classification,
            history.get("audiobook_next_action"),
            row.get("final_status"),
            row.get("strategy"),
        )
        exhausted = False if approved else external_audio or len(failed_families) >= 2
        exact_blocker = (
            canonical.get("exact_blocker")
            if "exact_blocker" in canonical
            else row.get("exact_blocker")
        )
        titles[slug] = {
            "slug": slug,
            "title": first_present(canonical.get("title"), row.get("title")),
            "language": first_present(canonical.get("language"), row.get("language")),
            "classification": first_present(
                canonical_classification, history_classification, row.get("final_status")
            ),
            "release_gate_state": canonical.get("release_gate_state"),
            "canonical_evidence_path": (
                display_path(canonical_path, asset_root) if canonical else None
            ),
            "decision_history_classification": history_classification,
            "attempts": attempts,
            "blocked_attempt_fingerprints": sorted(
                {
                    str(item["attempt_fingerprint"])
                    for item in attempts
                    if item.get("failed")
                    and item.get("fingerprint_is_evidence_native") is True
                    and item.get("attempt_fingerprint")
                }
            ),
            "blocked_registry_identities": sorted(
                {
                    str(item["registry_identity_sha256"])
                    for item in attempts
                    if item.get("failed")
                }
            ),
            "distinct_failed_provider_voice_families": failed_families,
            "distinct_failed_family_count": len(failed_families),
            "automated_tts_exhausted": exhausted,
            "exhaustion_evidence": {
                "external_audio_terminal_state": external_audio,
                "failed_family_threshold_met": len(failed_families) >= 2,
                "approved_release_override": approved,
            },
            "matrix_classification": row.get("final_status"),
            "exact_blocker": exact_blocker,
            "packet_exists": packet_metadata.is_file(),
            "budget_identity_stages": sorted(set(budget_stages.get(slug, []))),
            "evidence_paths": sorted(evidence_paths),
            "retry_policy": "DO_NOT_REPEAT_BLOCKED_EVIDENCE_FINGERPRINTS_OR_IDENTITIES",
        }
    return {
        "schema_version": 2,
        "generated_at": utc_now(),
        "owner_decision": OWNER_DECISION,
        "policy": {
            "max_failed_distinct_families_before_external_audio": 2,
            "repeat_failed_fingerprint_allowed": False,
            "unknown_attempts_are_not_release_evidence": True,
            "canonical_title_release_evidence_wins": True,
            "registry_identity_sha256_is_provider_native": False,
            "evidence_fingerprints_are_not_assumed_provider_native": True,
            "approved_titles_retain_history_without_becoming_exhausted": True,
        },
        "titles": titles,
    }


def packet_is_complete(packet_dir: Path) -> bool:
    paths = [packet_dir / name for name in REQUIRED_PACKET_FILES]
    if not all(path.is_file() and path.stat().st_size > 0 for path in paths):
        return False
    try:
        metadata = load_json(packet_dir / "metadata.json")
        expected_packet = metadata.pop("packet_fingerprint_sha256", None)
        if not expected_packet or canonical_sha256(metadata) != expected_packet:
            return False
        manuscript = (packet_dir / "clean_manuscript.txt").read_text(encoding="utf-8").rstrip()
        source_binding = metadata.get("source_binding") or {}
        if hashlib.sha256(manuscript.encode("utf-8")).hexdigest() != source_binding.get(
            "sanitized_manuscript_sha256"
        ):
            return False
        expected_binding = source_binding.get("binding_sha256")
        binding_payload = {
            key: value for key, value in source_binding.items() if key != "binding_sha256"
        }
        return bool(expected_binding and canonical_sha256(binding_payload) == expected_binding)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError):
        return False


def received_audio_files(received_dir: Path) -> list[Path]:
    if not received_dir.is_dir():
        return []
    return sorted(
        path for path in received_dir.iterdir()
        if path.is_file() and path.suffix.lower() in ACCEPTED_AUDIO_SUFFIXES
    )


def build_intake_board(
    rows: Sequence[Mapping[str, Any]],
    packets_root: Path,
    intake_root: Path,
    create_layout: bool,
) -> dict[str, Any]:
    titles: dict[str, Any] = {}
    packet_slugs = {path.parent.name for path in packets_root.glob("*/metadata.json")}
    human_slugs = {
        str(row["slug"]) for row in rows if row.get("final_status") in HUMAN_STATUSES
    }
    for slug in sorted(packet_slugs | human_slugs):
        packet_dir = packets_root / slug
        received_dir = intake_root / slug / "received_audio"
        if create_layout:
            received_dir.mkdir(parents=True, exist_ok=True)
            (received_dir / ".gitkeep").touch(exist_ok=True)
        files = received_audio_files(received_dir)
        preflight_path = packet_dir / "received_audio_preflight.json"
        preflight = load_json(preflight_path) if preflight_path.is_file() else None
        packet_metadata_path = packet_dir / "metadata.json"
        metadata = load_json(packet_metadata_path) if packet_metadata_path.is_file() else {}
        candidate_kind = metadata.get("candidate_kind", "human_narration")
        if files:
            next_command = (
                "PYTHONDONTWRITEBYTECODE=1 python3 "
                "internal/audiobook_lab/scripts/sprint1_autonomous_go_live_loop.py "
                f"--asset-root . --execute-received-preflight --slug {shlex.quote(slug)}"
            )
            status = "RECEIVED_AUDIO_PREFLIGHT_REQUIRED"
        else:
            next_command = metadata.get("exact_received_audio_validation_command") or (
                "PYTHONDONTWRITEBYTECODE=1 python3 "
                "internal/audiobook_lab/scripts/build_narration_import_packet.py "
                f"--slug {shlex.quote(slug)} --candidate-kind {shlex.quote(candidate_kind)} "
                "--asset-root . --output-root "
                "internal/audiobook_lab/sprint1_publication/human_narration_packets "
                "--received-audio /absolute/path/to/received_narration.wav"
            )
            status = "WAITING_EXTERNAL_SOURCE_BOUND_AUDIO"
        if preflight and preflight.get("status") == "RECEIVED_AUDIO_PREFLIGHT_PASS_FULL_RELEASE_QA_REQUIRED":
            status = "RECEIVED_AUDIO_FULL_RELEASE_QA_REQUIRED"
        titles[slug] = {
            "slug": slug,
            "packet_path": str(packet_dir),
            "packet_complete": packet_is_complete(packet_dir),
            "intake_path": str(received_dir),
            "accepted_formats": ["wav", "flac", "mp3"],
            "candidate_kind": candidate_kind,
            "received_files": [path.name for path in files],
            "received_file_count": len(files),
            "received_preflight_path": str(preflight_path) if preflight_path.is_file() else None,
            "status": status,
            "next_command": next_command,
            "public_audio_allowed_now": False,
        }
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "owner_decision": OWNER_DECISION,
        "intake_root": str(intake_root),
        "expected_layout": "{slug}/received_audio/{one source-bound WAV, FLAC, or MP3}",
        "title_count": len(titles),
        "received_title_count": sum(bool(item["received_file_count"]) for item in titles.values()),
        "titles": titles,
    }


def title_decision(
    row: Mapping[str, Any],
    failure: Mapping[str, Any],
    intake: Mapping[str, Any] | None,
    runtime: Mapping[str, Any],
    root: Path,
    additional_short_yes_yes: int,
    reconciled: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    slug = str(row["slug"])
    language = str(row.get("language") or "")
    base = {
        "slug": slug,
        "title": row.get("title"),
        "language": language,
        "priority": SHORT_PRIORITY.get(slug, 100),
        "estimated_incremental_cost_usd": row.get("estimated_incremental_cost_usd"),
        "public_audio_allowed_now": is_yes_yes(row),
        "release_gate_mutation_allowed": False,
    }
    if is_yes_yes(row):
        return {**base, "state": "YES_YES_PRODUCTION_REVALIDATION", "next_command": row.get("next_command")}
    if intake and intake.get("received_file_count", 0) > 0:
        return {**base, "state": str(intake["status"]), "priority": 0, "next_command": intake["next_command"]}
    if reconciled and reconciled.get("state"):
        state = str(reconciled["state"])
        blocker = str(reconciled.get("blocker") or "")
        google_relevant = "GOOGLE" in f"{state} {blocker}".upper()
        google_ready = runtime.get("providers", {}).get("google") is True
        adc_reauth_required = (
            "GOOGLE_ADC_REAUTH_REQUIRED" in state.upper()
            or google_relevant and not google_ready
        )
        if adc_reauth_required and "GOOGLE_ADC_REAUTH_REQUIRED" not in state.upper():
            state = f"{state}_GOOGLE_ADC_REAUTH_REQUIRED"
        return {
            **base,
            "state": state,
            "exact_blocker": blocker or None,
            "matrix_exact_blocker_overridden": row.get("exact_blocker"),
            "decision_source": "sprint1_v3_nonpaid_preflight_results",
            "reconciled_preflight_evidence": reconciled.get("evidence"),
            "paid_execution_allowed": False,
            "paid_execution_blocker": (
                "GOOGLE_ADC_REAUTH_REQUIRED"
                if adc_reauth_required
                else "RECONCILED_NONPAID_PREFLIGHT_ONLY"
            ),
            "next_command": reconciled.get("next_command"),
        }
    if row.get("publicly_rendered_book") != "Yes":
        return {**base, "state": "PUBLIC_READER_REPAIR_REQUIRED", "next_command": row.get("next_command")}
    blocker = str(row.get("exact_blocker") or "")
    if slug in OWNER_DOCUMENT_SLUGS or "OWNER_DOCUMENT_REQUIRED" in blocker:
        return {
            **base,
            "state": "OWNER_DOCUMENT_REQUIRED",
            "next_command": "cat internal/audiobook_lab/public_access/pather_panchali_audio_repair_requirements.md",
        }
    if intake and (
        failure.get("automated_tts_exhausted")
        or failure.get("packet_exists")
        or row.get("final_status") in HUMAN_STATUSES
    ):
        return {
            **base,
            "state": WAITING_EXTERNAL_AUDIO_STATE,
            "next_command": intake["next_command"],
            "packet_path": intake["packet_path"],
        }
    if slug == "bn-066":
        calibration = root / "internal/audiobook_lab/scripts/bengali_asr_language_calibration.py"
        if not calibration.is_file():
            return {
                **base,
                "state": "ASR_CALIBRATION_TOOLING_NOT_TRACKED_ON_MAIN",
                "next_command": row.get("next_command"),
            }
        return {**base, "state": "NON_PAID_ASR_LANGUAGE_CALIBRATION_READY", "next_command": row.get("next_command")}
    if language.lower().startswith("beng"):
        campaign = runtime["bengali_campaign_paid_gates"]
        return {
            **base,
            "state": "NON_PAID_BENGALI_PREFLIGHT_READY" if row.get("next_command") else "BENGALI_PREFLIGHT_COMMAND_REQUIRED",
            "paid_execution_allowed": bool(campaign["ready"]),
            "paid_execution_blocker": None if campaign["ready"] else "BENGALI_CAMPAIGN_PAID_GATES_MISSING",
            "next_command": row.get("next_command"),
        }
    if slug in LONG_ENGLISH_SLUGS and additional_short_yes_yes < 5:
        return {
            **base,
            "state": "LONG_TITLE_SEQUENCE_HOLD",
            "next_command": row.get("next_command"),
            "hold_condition": "FIVE_ADDITIONAL_SHORT_OR_MEDIUM_YES_YES_REQUIRED",
        }
    if failure.get("distinct_failed_family_count", 0) >= 2:
        return {
            **base,
            "state": "HUMAN_NARRATION_PACKET_REQUIRED",
            "next_command": (
                "PYTHONDONTWRITEBYTECODE=1 python3 "
                "internal/audiobook_lab/scripts/build_narration_import_packet.py "
                f"--slug {shlex.quote(slug)} --asset-root ."
            ),
        }
    return {
        **base,
        "state": "NON_PAID_PROVIDER_PREFLIGHT_REQUIRED",
        "next_command": row.get("next_command"),
        "blocked_attempt_fingerprints": failure.get("blocked_attempt_fingerprints", []),
    }


def build_execution_board(
    rows: Sequence[Mapping[str, Any]],
    registry: Mapping[str, Any],
    intake: Mapping[str, Any],
    runtime: Mapping[str, Any],
    lock: Mapping[str, Any],
    ledger: Mapping[str, Any],
    root: Path,
    reconciled_preflight: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    additional_short_yes_yes = sum(
        is_yes_yes(row) and row["slug"] not in APPROVED_SLUGS_BASELINE and row["slug"] not in LONG_ENGLISH_SLUGS
        for row in rows
    )
    registry_titles = registry.get("titles", {})
    intake_titles = intake.get("titles", {})
    reconciled_titles = (reconciled_preflight or {}).get("titles", {})
    if not isinstance(reconciled_titles, dict):
        reconciled_titles = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = [
            pool.submit(
                title_decision,
                row,
                registry_titles.get(row["slug"], {}),
                intake_titles.get(row["slug"]),
                runtime,
                root,
                additional_short_yes_yes,
                reconciled_titles.get(row["slug"]),
            )
            for row in rows
        ]
        decisions = [future.result() for future in futures]
    decisions.sort(key=lambda item: (item["priority"], item["slug"]))
    received = [item for item in decisions if item["state"].startswith("RECEIVED_AUDIO_")]
    non_paid = [
        item for item in decisions
        if item["state"].startswith("NON_PAID_") or item["state"] in {
            "ASR_CALIBRATION_TOOLING_NOT_TRACKED_ON_MAIN",
            "HUMAN_NARRATION_PACKET_REQUIRED",
            "BENGALI_PREFLIGHT_COMMAND_REQUIRED",
        }
        or (
            item.get("decision_source") == "sprint1_v3_nonpaid_preflight_results"
            and item["state"] != "OWNER_DOCUMENT_REQUIRED"
        )
    ]
    paid_ready: list[dict[str, Any]] = []
    spend = float(ledger.get("accounting", {}).get("cumulative_conservative_estimated_spend_usd", 0.0))
    cap = float(FIXED_CAPS["SPRINT1_TOTAL_AUDIO_BUDGET_USD"])
    waiting_external = [
        item for item in decisions
        if item["state"] == "WAITING_EXTERNAL_SOURCE_BOUND_NARRATION_OR_LICENSED_AUDIO"
    ]
    owner_documents = [item for item in decisions if item["state"] == "OWNER_DOCUMENT_REQUIRED"]
    loop_state = "ALL_ACTIVE_TITLES_YES_YES"
    if received:
        loop_state = "RECEIVED_AUDIO_PREFLIGHT_READY"
    elif paid_ready:
        loop_state = "SERIALIZED_PAID_ACTION_READY"
    elif non_paid:
        loop_state = "NON_PAID_REPAIR_QUEUE_REMAINS"
    elif waiting_external or owner_documents:
        loop_state = "WAITING_EXTERNAL_SOURCE_BOUND_INPUT"
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "owner_decision": OWNER_DECISION,
        "loop_state": loop_state,
        "safety": {
            "free_form_evidence_commands_executed": False,
            "paid_calls_serialized": True,
            "public_release_gate_mutated": False,
            "repeat_failed_fingerprints_allowed": False,
        },
        "runtime": runtime,
        "reconciled_nonpaid_preflight": {
            "present": bool((reconciled_preflight or {}).get("present")),
            "path": (reconciled_preflight or {}).get("path"),
            "generated_at": (reconciled_preflight or {}).get("generated_at"),
            "matched_title_count": sum(
                item.get("decision_source")
                == "sprint1_v3_nonpaid_preflight_results"
                for item in decisions
            ),
        },
        "lock": lock,
        "budget": {
            "cap_usd": cap,
            "per_title_cap_usd": float(FIXED_CAPS["SPRINT1_MAX_USD_PER_TITLE"]),
            "conservative_estimated_spend_usd": spend,
            "estimated_remaining_usd": round(cap - spend, 6),
            "actual_spend_usd": ledger.get("accounting", {}).get("actual_spend_usd"),
        },
        "summary": {
            "active_titles": len(rows),
            "yes_yes": sum(is_yes_yes(row) for row in rows),
            "received_audio_titles": len(received),
            "waiting_external_audio_titles": len(waiting_external),
            "owner_document_titles": len(owner_documents),
            "non_paid_repair_titles": len(non_paid),
            "paid_ready_titles": len(paid_ready),
            "additional_short_yes_yes_since_v3_baseline": additional_short_yes_yes,
        },
        "next_received_audio_action": received[0] if received else None,
        "next_non_paid_action": non_paid[0] if non_paid else None,
        "next_paid_action": paid_ready[0] if paid_ready else None,
        "title_decisions": decisions,
    }


def execute_received_preflight(
    root: Path,
    slug: str,
    intake: Mapping[str, Any],
) -> dict[str, Any]:
    title = intake.get("titles", {}).get(slug)
    if not title:
        raise LoopError(f"slug is not in human narration intake board: {slug}")
    files = [Path(title["intake_path"]) / name for name in title.get("received_files", [])]
    if len(files) != 1:
        raise LoopError("received audio preflight requires exactly one WAV, FLAC, or MP3")
    packet_metadata = load_json(Path(title["packet_path"]) / "metadata.json")
    candidate_kind = packet_metadata.get("candidate_kind")
    if candidate_kind not in {"human_narration", "licensed_audio_import"}:
        raise LoopError("packet candidate kind is missing or unsupported")
    helper = root / "internal/audiobook_lab/scripts/build_narration_import_packet.py"
    command = [
        sys.executable,
        str(helper),
        "--slug",
        slug,
        "--candidate-kind",
        candidate_kind,
        "--asset-root",
        str(root),
        "--output-root",
        str(root / "internal/audiobook_lab/sprint1_publication/human_narration_packets"),
        "--received-audio",
        str(files[0]),
    ]
    completed = subprocess.run(
        command,
        cwd=root,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
    )
    if completed.returncode != 0:
        raise LoopError(f"received audio preflight failed: {completed.stderr[-1000:]}")
    return {
        "slug": slug,
        "status": "RECEIVED_AUDIO_PREFLIGHT_COMPLETE_FULL_RELEASE_QA_REQUIRED",
        "completed_at": utc_now(),
        "provider_calls_ran": False,
        "public_release_gate_mutated": False,
        "output": json.loads(completed.stdout),
    }


def render_log(board: Mapping[str, Any], execution: Mapping[str, Any] | None) -> str:
    summary = board["summary"]
    lines = [
        "# Sprint 1 Autonomous Go-Live Loop V3",
        "",
        f"Generated: `{board['generated_at']}`",
        f"Owner decision: `{OWNER_DECISION}`",
        "",
        "## Result",
        "",
        f"- Loop state: `{board['loop_state']}`",
        f"- Active titles: {summary['active_titles']}",
        f"- Current YES+YES: {summary['yes_yes']}",
        f"- Waiting for source-bound narration/licensed audio: {summary['waiting_external_audio_titles']}",
        f"- Owner-document titles: {summary['owner_document_titles']}",
        f"- Paid-ready titles: {summary['paid_ready_titles']}",
        f"- Conservative estimated spend: ${board['budget']['conservative_estimated_spend_usd']:.5f}",
        f"- Estimated remaining cap: ${board['budget']['estimated_remaining_usd']:.5f}",
        "- Public release gates mutated: no",
        "- Failed provider fingerprints repeated: no",
        "",
        "## Decisions",
        "",
    ]
    for item in board["title_decisions"]:
        lines.append(f"- `{item['slug']}`: `{item['state']}`")
    if execution:
        lines.extend(["", "## Latest Execution", "", f"```json\n{json.dumps(execution, ensure_ascii=False, indent=2)}\n```"])
    return "\n".join(lines) + "\n"


def update_evidence_files(
    matrix_path: Path,
    final_path: Path,
    ledger_path: Path,
    board: Mapping[str, Any],
    execution: Mapping[str, Any] | None,
) -> None:
    generated_at = str(board["generated_at"])
    decisions = {item["slug"]: item for item in board["title_decisions"]}
    matrix = load_json(matrix_path)
    matrix["generated_at"] = generated_at
    matrix["autonomous_v3"] = {
        "owner_decision": OWNER_DECISION,
        "execution_board": "internal/audiobook_lab/sprint1_publication/sprint1_autonomous_execution_board.json",
        "human_intake_board": "internal/audiobook_lab/sprint1_publication/sprint1_human_narration_intake_board.json",
        "provider_failure_registry": "internal/audiobook_lab/sprint1_publication/sprint1_provider_failure_registry.json",
        "loop_state": board["loop_state"],
        "provider_calls_ran": False,
        "new_public_audiobooks": 0,
        "release_gate_mutated": False,
    }
    for row in matrix.get("titles", []):
        if row.get("slug") in decisions:
            decision = decisions[row["slug"]]
            row["autonomous_v3_state"] = decision["state"]
            row["autonomous_v3_next_command"] = decision.get("next_command")
            row["autonomous_v3_public_audio_allowed_now"] = decision["public_audio_allowed_now"]
            if decision["state"] == WAITING_EXTERNAL_AUDIO_STATE:
                row["final_status"] = EXTERNAL_AUDIO_FINAL_STATUS
                row["next_action"] = (
                    "Import received source-bound human narration or licensed audio, "
                    "then run the complete release-gate QA pipeline."
                )
                row["next_command"] = decision.get("next_command")
    atomic_write_json(matrix_path, matrix)

    final = load_json(final_path)
    final["generated_at"] = generated_at
    final["autonomous_v3"] = {
        "owner_decision": OWNER_DECISION,
        "loop_state": board["loop_state"],
        "summary": board["summary"],
        "provider_calls_ran": False,
        "new_public_audiobooks": 0,
        "release_gate_mutated": False,
    }
    for row in final.get("titles", []):
        if row.get("slug") in decisions:
            decision = decisions[row["slug"]]
            row["autonomous_v3_state"] = decision["state"]
            row["autonomous_v3_next_command"] = decision.get("next_command")
            if decision["state"] == WAITING_EXTERNAL_AUDIO_STATE:
                row["final_status"] = EXTERNAL_AUDIO_FINAL_STATUS
                row["next_command"] = decision.get("next_command")
    atomic_write_json(final_path, final)

    ledger = load_json(ledger_path)
    ledger["generated_at"] = generated_at
    ledger["owner_decision"] = OWNER_DECISION
    ledger["autonomous_v3"] = {
        "provider_calls_ran": False,
        "estimated_incremental_spend_usd": 0.0,
        "actual_incremental_spend_usd": 0.0,
        "release_gate_mutated": False,
        "execution": execution,
    }
    entries = ledger.setdefault("entries", [])
    entry_id = "sprint1-autonomous-v3-intake-ranking-and-nonpaid-coordination"
    if not any(item.get("entry_id") == entry_id for item in entries if isinstance(item, dict)):
        entries.append(
            {
                "entry_id": entry_id,
                "scope": "V3 provider-memory reconciliation, source-bound intake polling, and fail-closed queue ranking",
                "conservative_estimated_spend_usd": 0.0,
                "actual_spend_usd": 0.0,
                "provider_calls_ran": False,
                "status": "NON_PAID_COORDINATION_COMPLETE",
            }
        )
    atomic_write_json(ledger_path, ledger)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, default=Path.cwd())
    parser.add_argument("--lock-path", type=Path)
    parser.add_argument("--slug")
    parser.add_argument("--execute-received-preflight", action="store_true")
    parser.add_argument("--no-create-intake-layout", action="store_true")
    parser.add_argument("--registry-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.asset_root.resolve()
    publication = root / "internal/audiobook_lab/sprint1_publication"
    matrix_path = publication / "sprint1_publication_matrix.json"
    final_path = publication / "sprint1_final_yes_yes_matrix.json"
    ledger_path = publication / "sprint1_budget_ledger.json"
    packets_root = publication / "human_narration_packets"
    intake_root = publication / "human_narration_intake"
    registry_path = publication / "sprint1_provider_failure_registry.json"
    nonpaid_preflight_path = (
        publication / "sprint1_v3_nonpaid_preflight_results.json"
    )
    intake_path = publication / "sprint1_human_narration_intake_board.json"
    board_path = publication / "sprint1_autonomous_execution_board.json"
    log_path = publication / "sprint1_autonomous_execution_log.md"
    lock_path = (
        args.lock_path
        or root / "internal/earnalism_intelligence/locks/paid_tts.lock"
    ).resolve()

    matrix = load_json(matrix_path)
    ledger = load_json(ledger_path)
    rows = active_rows(matrix)
    previous_registry = load_json(registry_path) if registry_path.is_file() else None
    registry = build_failure_registry(
        rows,
        packets_root,
        previous_registry,
        title_runs_root=publication / "title_runs",
        title_decision_history=(
            root / "internal/earnalism_intelligence/title_decision_history.json"
        ),
        budget_ledger=ledger,
        asset_root=root,
    )
    if args.registry_only:
        if not args.dry_run:
            atomic_write_json(registry_path, registry)
        print(
            json.dumps(
                {
                    "registry_path": str(registry_path),
                    "title_count": len(registry["titles"]),
                    "provider_calls_ran": False,
                    "release_gate_mutated": False,
                    "next_exact_command": (
                        "PYTHONDONTWRITEBYTECODE=1 python3 "
                        "internal/audiobook_lab/scripts/test_sprint1_autonomous_go_live_loop.py"
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    intake = build_intake_board(
        rows,
        packets_root,
        intake_root,
        create_layout=not args.no_create_intake_layout and not args.dry_run,
    )
    runtime = runtime_snapshot(os.environ)
    lock = lock_snapshot(lock_path)
    reconciled_preflight = load_nonpaid_preflight_results(nonpaid_preflight_path)
    board = build_execution_board(
        rows,
        registry,
        intake,
        runtime,
        lock,
        ledger,
        root,
        reconciled_preflight,
    )

    execution = None
    if args.execute_received_preflight:
        if not args.slug:
            raise LoopError("--slug is required with --execute-received-preflight")
        execution = execute_received_preflight(root, args.slug, intake)
        board["latest_execution"] = execution

    if not args.dry_run:
        atomic_write_json(registry_path, registry)
        atomic_write_json(intake_path, intake)
        atomic_write_json(board_path, board)
        atomic_write_text(log_path, render_log(board, execution))
        update_evidence_files(matrix_path, final_path, ledger_path, board, execution)
    print(
        json.dumps(
            {
                "loop_state": board["loop_state"],
                "summary": board["summary"],
                "budget": board["budget"],
                "next_received_audio_action": board["next_received_audio_action"],
                "next_non_paid_action": board["next_non_paid_action"],
                "next_paid_action": board["next_paid_action"],
                "execution": execution,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
