"""Fail-closed, hash-bound rights decision control.

This module validates an already accepted decision.  It does not determine
copyright, authenticate a reviewer, infer a territory, publish a title, or
mutate a wallet.  The production registry is deliberately empty of ACCEPTED
records until an authorised reviewer supplies immutable evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping


SCHEMA_VERSION = "earnalism.rights-decision.v1"
COUNTRIES = frozenset({"IN", "US", "GB", "CA", "AU", "DE", "AE", "BD", "SG", "SA"})
USES = frozenset(
    {
        "catalog_metadata",
        "cover_display",
        "reader_preview",
        "reader_delivery",
        "reading_pass_session",
        "reading_pass_renewal",
        "audio_stream",
        "audio_download",
        "content_export",
        "signed_storage_access",
        "ai_generation",
        "ai_generation_cache",
    }
)
RECORD_FIELDS = frozenset(
    {
        "schema_version",
        "decision_id",
        "edition_id",
        "operator_id",
        "status",
        "components",
        "territories",
        "uses",
        "valid_from",
        "valid_until",
        "basis",
        "evidence_sha256",
        "accepted_by",
        "conditions_satisfied",
    }
)
HEX_SHA256 = re.compile(r"^[a-f0-9]{64}$")
# Synthetic records are private test fixtures.  Keep this namespace broad
# enough to reject the actual fixture IDs, not merely a differently-cased
# sentinel that production tests never use.
SYNTHETIC_PREFIX = "synthetic-"
PRODUCTION_REGISTRY_PATH = Path(__file__).parent / "data" / "rights_decision_registry.json"

# Every effectful route must use a named action. Integration stays disabled
# until the trusted release proxy and production adapter work are separately
# reviewed, so this table is intentionally executable policy rather than a
# claim that the listed routes are currently activated.
RUNTIME_PATH_USES: dict[str, tuple[str, ...]] = {
    "catalog_cta": ("catalog_metadata", "cover_display"),
    "reader_manifest": ("reader_preview",),
    "reader_preview": ("reader_preview",),
    "reader_chapter": ("reader_delivery",),
    "reading_pass_page": ("reader_delivery",),
    # A no-price/no-debit text lease enforces an already accepted Reader
    # delivery decision; it is not a grant for the separate paid Pass product.
    "free_reader_entitlement": ("reader_delivery",),
    "reading_pass_session_start": ("reading_pass_session",),
    "reading_pass_session_transfer": ("reading_pass_session",),
    "reading_pass_lease_renewal": ("reading_pass_renewal",),
    "audio_manifest": ("audio_stream",),
    "audio_head": ("audio_stream",),
    "audio_range": ("audio_stream",),
    "audio_download": ("audio_download",),
    "content_export": ("content_export",),
    "signed_storage_url": ("signed_storage_access",),
    "generation_worker": ("ai_generation",),
    "generation_cache": ("ai_generation_cache",),
}


@dataclass(frozen=True)
class DecisionGateVerdict:
    passed: bool
    reasons: tuple[str, ...]


def record_sha256(record: Mapping[str, Any]) -> str:
    """Return the canonical hash used by the independently trusted registry."""
    return sha256(
        json.dumps(dict(record), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _instant(value: str) -> datetime:
    instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if instant.tzinfo is None:
        raise ValueError("timezone required")
    return instant


def _valid_hash(value: Any) -> bool:
    return isinstance(value, str) and bool(HEX_SHA256.fullmatch(value))


def _reserved_fixture_id(value: Any) -> bool:
    return isinstance(value, str) and value.casefold().startswith(SYNTHETIC_PREFIX)


def _registry_records(payload: Mapping[str, Any]) -> tuple[dict[str, str], frozenset[str]]:
    """Parse production registry payload without accepting fixture identifiers."""
    if payload.get("schema_version") != "earnalism.rights-decision-registry.v1":
        raise ValueError("unsupported rights decision registry schema")
    records = payload.get("accepted_records")
    revoked = payload.get("revoked_decision_ids")
    if not isinstance(records, dict) or not isinstance(revoked, list):
        raise ValueError("invalid rights decision registry shape")
    if any(not isinstance(key, str) or not _valid_hash(value) for key, value in records.items()):
        raise ValueError("invalid accepted decision registry binding")
    if any(_reserved_fixture_id(key) for key in records):
        raise ValueError("synthetic decision cannot enter the production registry")
    if any(not isinstance(value, str) or not value for value in revoked):
        raise ValueError("invalid revoked decision identifier")
    return dict(records), frozenset(revoked)


def load_production_registry(path: Path = PRODUCTION_REGISTRY_PATH) -> tuple[dict[str, str], frozenset[str]]:
    """Load only the shipped production registry; test fixtures use no file path."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("rights decision registry must be an object")
    return _registry_records(payload)


def evaluate_accepted_record(
    record: Any,
    *,
    edition_id: str,
    operator_id: str,
    country: str,
    country_trusted: bool,
    use: str,
    required_components: Mapping[str, str],
    accepted_records: Mapping[str, str],
    revoked_decision_ids: frozenset[str],
    now: datetime,
) -> DecisionGateVerdict:
    """Check one exact act without deriving facts from the proposed decision."""
    if not isinstance(record, dict) or frozenset(record) != RECORD_FIELDS:
        return DecisionGateVerdict(False, ("DECISION_SHAPE_INVALID",))
    if not isinstance(now, datetime) or now.tzinfo is None:
        return DecisionGateVerdict(False, ("CLOCK_UNTRUSTED",))
    if not all(isinstance(value, str) and value.strip() for value in (edition_id, operator_id, country, use)):
        return DecisionGateVerdict(False, ("REQUEST_IDENTITY_MISSING",))
    if (
        not isinstance(required_components, Mapping)
        or not isinstance(accepted_records, Mapping)
        or not isinstance(revoked_decision_ids, frozenset)
        or any(not isinstance(key, str) or not _valid_hash(value) for key, value in accepted_records.items())
        or any(not isinstance(value, str) for value in revoked_decision_ids)
    ):
        return DecisionGateVerdict(False, ("TRUST_CONTEXT_INVALID",))

    reasons: list[str] = []
    if record.get("schema_version") != SCHEMA_VERSION:
        reasons.append("SCHEMA_UNSUPPORTED")
    if record.get("status") != "ACCEPTED":
        reasons.append("DECISION_NOT_ACCEPTED")
    decision_id = record.get("decision_id")
    if not isinstance(decision_id, str) or not decision_id:
        reasons.append("DECISION_ID_INVALID")
    elif decision_id in revoked_decision_ids:
        reasons.append("DECISION_REVOKED")
    else:
        try:
            record_digest = record_sha256(record)
        except (TypeError, ValueError):
            reasons.append("DECISION_SERIALIZATION_INVALID")
        else:
            if accepted_records.get(decision_id) != record_digest:
                reasons.append("DECISION_NOT_TRUSTED_OR_CHANGED")
    record_edition_id = record.get("edition_id")
    record_operator_id = record.get("operator_id")
    if not all(isinstance(value, str) and value.strip() for value in (record_edition_id, record_operator_id)):
        reasons.append("RECORD_IDENTITY_INVALID")
    elif record_edition_id != edition_id or record_operator_id != operator_id:
        reasons.append("EDITION_OR_OPERATOR_MISMATCH")
    if country_trusted is not True or country not in COUNTRIES:
        reasons.append("TERRITORY_UNTRUSTED_OR_UNSUPPORTED")

    territories = record.get("territories")
    if (
        not isinstance(territories, list)
        or any(not isinstance(item, str) for item in territories)
        or country not in territories
        or any(item not in COUNTRIES for item in territories)
    ):
        reasons.append("TERRITORY_NOT_AUTHORIZED")
    record_uses = record.get("uses")
    if (
        not isinstance(record_uses, list)
        or any(not isinstance(item, str) for item in record_uses)
        or use not in USES
        or use not in record_uses
        or any(item not in USES for item in record_uses)
    ):
        reasons.append("USE_NOT_AUTHORIZED")
    try:
        valid_from_raw = record["valid_from"]
        valid_until_raw = record["valid_until"]
        if not isinstance(valid_from_raw, str) or not isinstance(valid_until_raw, str):
            raise ValueError("timestamps must be strings")
        valid_from = _instant(valid_from_raw)
        valid_until = _instant(valid_until_raw)
        if not valid_from <= now < valid_until:
            reasons.append("DECISION_OUTSIDE_VALIDITY")
    except (KeyError, TypeError, ValueError, AttributeError):
        reasons.append("VALIDITY_INVALID")

    components = record.get("components")
    if not isinstance(components, dict) or not required_components:
        reasons.append("COMPONENT_INVENTORY_MISSING")
    else:
        for component, digest in required_components.items():
            if not isinstance(component, str) or not component or not _valid_hash(digest) or components.get(component) != digest:
                reasons.append(f"COMPONENT_MISSING_OR_CHANGED:{component}")
        if any(not isinstance(component, str) or not component or not _valid_hash(digest) for component, digest in components.items()):
            reasons.append("COMPONENT_INVENTORY_INVALID")
    evidence = record.get("evidence_sha256")
    if not isinstance(evidence, list) or not evidence or any(not _valid_hash(item) for item in evidence):
        reasons.append("EVIDENCE_BINDING_MISSING")
    if not isinstance(record.get("accepted_by"), str) or not record["accepted_by"].strip():
        reasons.append("REVIEW_ATTRIBUTION_MISSING")
    if not isinstance(record.get("basis"), str) or not record["basis"].strip():
        reasons.append("LEGAL_BASIS_MISSING")
    if record.get("conditions_satisfied") is not True:
        reasons.append("CONDITIONS_NOT_SATISFIED")
    return DecisionGateVerdict(not reasons, tuple(reasons))


def evaluate_runtime_path(
    action: str,
    *,
    record: Mapping[str, Any] | None,
    edition_id: str,
    operator_id: str,
    country: str,
    country_trusted: bool,
    required_components: Mapping[str, str],
    accepted_records: Mapping[str, str],
    revoked_decision_ids: frozenset[str],
    now: datetime,
) -> DecisionGateVerdict:
    """Evaluate every required use for an effectful runtime action, without I/O."""
    if not isinstance(action, str):
        return DecisionGateVerdict(False, ("RUNTIME_ACTION_UNKNOWN",))
    required_uses = RUNTIME_PATH_USES.get(action)
    if not required_uses:
        return DecisionGateVerdict(False, ("RUNTIME_ACTION_UNKNOWN",))
    if record is None:
        return DecisionGateVerdict(False, ("ACCEPTED_DECISION_MISSING",))
    reasons: list[str] = []
    for use in required_uses:
        verdict = evaluate_accepted_record(
            record,
            edition_id=edition_id,
            operator_id=operator_id,
            country=country,
            country_trusted=country_trusted,
            use=use,
            required_components=required_components,
            accepted_records=accepted_records,
            revoked_decision_ids=revoked_decision_ids,
            now=now,
        )
        reasons.extend(verdict.reasons)
    return DecisionGateVerdict(not reasons, tuple(dict.fromkeys(reasons)))


def should_deny_runtime_action(verdict: DecisionGateVerdict, *, strict_enforcement_enabled: bool) -> bool:
    """Only a well-formed verdict plus literal ``False`` keeps non-activation."""
    if not isinstance(verdict, DecisionGateVerdict) or not isinstance(verdict.passed, bool):
        return True
    if strict_enforcement_enabled is False:
        return False
    if strict_enforcement_enabled is True:
        return not verdict.passed
    return True
