from scripts.release_intelligence import rank_strategies, validate_strategy


def test_verified_success_is_preferred_without_changing_strategy_set():
    strategies = [{"id": "slow", "failure_class": "TRANSIENT"}, {"id": "fast", "failure_class": "TRANSIENT"}]
    ledger = [{"check": "synchronization", "strategy": "fast", "outcome": "PASS", "cost_usd": 1, "latency_ms": 10}]
    ranked = rank_strategies("synchronization", strategies, ledger)
    assert [item["id"] for item in ranked] == ["fast", "slow"]


def test_governance_rejects_threshold_or_approval_mutation():
    try:
        validate_strategy(
            "synchronization",
            {"id": "unsafe", "failure_class": "TRANSIENT", "lowers_thresholds": True},
        )
    except ValueError as exc:
        assert "thresholds" in str(exc)
    else:
        raise AssertionError("unsafe strategy was accepted")
