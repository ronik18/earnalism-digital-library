from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from backend.rights_decision_gate import (
    PRODUCTION_REGISTRY_PATH,
    RUNTIME_PATH_USES,
    DecisionGateVerdict,
    evaluate_runtime_path,
    load_production_registry,
    record_sha256,
    should_deny_runtime_action,
)


NOW = datetime(2026, 9, 17, tzinfo=timezone.utc)
COMPONENTS = {
    "manuscript": "a" * 64,
    "cover": "b" * 64,
    "voice_master": "c" * 64,
}


def synthetic_record(*, decision_id: str = "synthetic-pilot") -> dict:
    return {
        "schema_version": "earnalism.rights-decision.v1",
        "decision_id": decision_id,
        "edition_id": "fictional-edition-for-private-test-only",
        "operator_id": "operator-test",
        "status": "ACCEPTED",
        "components": dict(COMPONENTS),
        "territories": ["IN"],
        "uses": sorted({use for uses in RUNTIME_PATH_USES.values() for use in uses}),
        "valid_from": "2026-01-01T00:00:00+00:00",
        "valid_until": "2027-01-01T00:00:00+00:00",
        "basis": "Synthetic fixture only; not legal evidence.",
        "evidence_sha256": ["d" * 64],
        "accepted_by": "test reviewer",
        "conditions_satisfied": True,
    }


def runtime_verdict(action: str, record: dict | None, registry: dict[str, str] | None = None, **overrides):
    registry = registry if registry is not None else ({record["decision_id"]: record_sha256(record)} if record else {})
    arguments = {
        "record": record,
        "edition_id": "fictional-edition-for-private-test-only",
        "operator_id": "operator-test",
        "country": "IN",
        "country_trusted": True,
        "required_components": COMPONENTS,
        "accepted_records": registry,
        "revoked_decision_ids": frozenset(),
        "now": NOW,
    }
    arguments.update(overrides)
    return evaluate_runtime_path(action, **arguments)


def test_real_registry_has_all_four_holds_and_no_accepted_decisions():
    registry, revoked = load_production_registry()
    payload = json.loads(PRODUCTION_REGISTRY_PATH.read_text(encoding="utf-8"))

    assert registry == {}
    assert revoked == frozenset()
    assert set(payload["pilot_dispositions"]) == {
        "controlled-a-ghost-story",
        "controlled-the-tell-tale-heart",
        "controlled-radharani",
        "controlled-yugalanguriya",
    }
    assert {row["status"] for row in payload["pilot_dispositions"].values()} == {"HOLD"}


@pytest.mark.parametrize("action", sorted(RUNTIME_PATH_USES))
def test_every_effectful_runtime_path_requires_the_bound_decision(action):
    record = synthetic_record()

    verdict = runtime_verdict(action, record)

    assert verdict.passed is True
    assert should_deny_runtime_action(verdict, strict_enforcement_enabled=True) is False


@pytest.mark.parametrize("action", sorted(RUNTIME_PATH_USES))
def test_empty_real_registry_denies_each_runtime_path_when_enforcement_activates(action):
    accepted, revoked = load_production_registry()
    verdict = evaluate_runtime_path(
        action,
        record=None,
        edition_id="fictional-edition-for-private-test-only",
        operator_id="operator-test",
        country="IN",
        country_trusted=True,
        required_components=COMPONENTS,
        accepted_records=accepted,
        revoked_decision_ids=revoked,
        now=NOW,
    )

    assert verdict.passed is False
    assert verdict.reasons == ("ACCEPTED_DECISION_MISSING",)
    assert should_deny_runtime_action(verdict, strict_enforcement_enabled=True) is True
    assert should_deny_runtime_action(verdict, strict_enforcement_enabled=False) is False


def test_component_change_country_spoof_and_revocation_fail_closed():
    record = synthetic_record()
    registry = {record["decision_id"]: record_sha256(record)}

    changed = runtime_verdict("reader_chapter", record, registry, required_components={**COMPONENTS, "master": "e" * 64})
    spoofed = runtime_verdict("reader_chapter", record, registry, country_trusted=False)
    revoked = evaluate_runtime_path(
        "reader_chapter", record=record, edition_id="fictional-edition-for-private-test-only", operator_id="operator-test",
        country="IN", country_trusted=True, required_components=COMPONENTS, accepted_records=registry,
        revoked_decision_ids=frozenset({record["decision_id"]}), now=NOW,
    )

    assert "COMPONENT_MISSING_OR_CHANGED:master" in changed.reasons
    assert "TERRITORY_UNTRUSTED_OR_UNSUPPORTED" in spoofed.reasons
    assert "DECISION_REVOKED" in revoked.reasons


def test_actual_positive_fixture_identifier_is_rejected_from_production_registry(tmp_path):
    record = synthetic_record()
    path = tmp_path / "registry.json"
    path.write_text(json.dumps({
        "schema_version": "earnalism.rights-decision-registry.v1",
        "accepted_records": {record["decision_id"]: record_sha256(record)},
        "revoked_decision_ids": [],
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="synthetic decision"):
        load_production_registry(path)


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("territories", [["IN"]], "TERRITORY_NOT_AUTHORIZED"),
        ("uses", [["reader_delivery"]], "USE_NOT_AUTHORIZED"),
        ("valid_from", [], "VALIDITY_INVALID"),
        ("valid_until", 17, "VALIDITY_INVALID"),
        ("edition_id", [], "RECORD_IDENTITY_INVALID"),
        ("operator_id", "", "RECORD_IDENTITY_INVALID"),
        ("components", [], "COMPONENT_INVENTORY_MISSING"),
        ("evidence_sha256", [["d" * 64]], "EVIDENCE_BINDING_MISSING"),
        ("basis", ["not a scalar"], "LEGAL_BASIS_MISSING"),
    ],
)
def test_malformed_json_compatible_record_values_deny_without_exception(field, value, reason):
    record = synthetic_record(decision_id="accepted-test-record")
    record[field] = value
    verdict = runtime_verdict("reader_chapter", record, {})

    assert verdict.passed is False
    assert reason in verdict.reasons


def test_nonserializable_record_value_denies_before_digest_comparison():
    record = synthetic_record(decision_id="accepted-test-record")
    record["basis"] = float("nan")

    verdict = runtime_verdict("reader_chapter", record, {})

    assert verdict.passed is False
    assert "DECISION_SERIALIZATION_INVALID" in verdict.reasons


@pytest.mark.parametrize("action", [None, [], {}, 1])
def test_malformed_runtime_actions_deny_without_exception(action):
    verdict = runtime_verdict(action, synthetic_record())

    assert verdict == DecisionGateVerdict(False, ("RUNTIME_ACTION_UNKNOWN",))


@pytest.mark.parametrize(
    ("accepted_records", "revoked_decision_ids"),
    [([], frozenset()), ({}, []), ({"accepted-test-record": []}, frozenset())],
)
def test_malformed_trust_context_denies_without_exception(accepted_records, revoked_decision_ids):
    record = synthetic_record(decision_id="accepted-test-record")
    verdict = runtime_verdict(
        "reader_chapter",
        record,
        accepted_records=accepted_records,
        revoked_decision_ids=revoked_decision_ids,
    )

    assert verdict == DecisionGateVerdict(False, ("TRUST_CONTEXT_INVALID",))


def test_only_literal_false_preserves_deliberate_non_activation():
    denied = DecisionGateVerdict(False, ("ACCEPTED_DECISION_MISSING",))

    assert should_deny_runtime_action(denied, strict_enforcement_enabled=False) is False
    for malformed_switch in (None, "false", "true", 0, 1):
        assert should_deny_runtime_action(denied, strict_enforcement_enabled=malformed_switch) is True
    assert should_deny_runtime_action({"passed": False}, strict_enforcement_enabled=False) is True
    assert should_deny_runtime_action(DecisionGateVerdict("false", ()), strict_enforcement_enabled=False) is True
