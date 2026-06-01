import importlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def load_server(monkeypatch):
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    return importlib.import_module("server")


def test_reader_billing_charges_one_pulse_only(monkeypatch):
    server = load_server(monkeypatch)
    now = datetime(2026, 5, 31, 10, 0, tzinfo=timezone.utc)

    assert server._billable_reading_seconds(now - timedelta(seconds=31), now) == 30
    assert server._billable_reading_seconds(now - timedelta(seconds=70), now) == 30


def test_reader_billing_does_not_catch_up_after_stale_gap(monkeypatch):
    server = load_server(monkeypatch)
    now = datetime(2026, 5, 31, 10, 0, tzinfo=timezone.utc)

    assert server._billable_reading_seconds(now - timedelta(minutes=30), now) == 0
    assert server._should_reset_reading_clock(now - timedelta(minutes=30), now) is True


def test_reader_billing_pauses_when_hidden_or_idle(monkeypatch):
    server = load_server(monkeypatch)
    now = datetime(2026, 5, 31, 10, 0, tzinfo=timezone.utc)
    last = now - timedelta(seconds=31)

    assert server._billable_reading_seconds(last, now, visible=False, idle=False) == 0
    assert server._billable_reading_seconds(last, now, visible=True, idle=True) == 0
    assert server._should_reset_reading_clock(last, now, visible=False, idle=False) is True
    assert server._should_reset_reading_clock(last, now, visible=True, idle=True) is True


def test_refund_review_flags_legacy_bulk_consume(monkeypatch):
    server = load_server(monkeypatch)
    tx = {
        "id": "tx-bulk",
        "user_id": "user-1",
        "type": "consume",
        "seconds": -1710,
        "session_id": "session-1",
        "reason": "Reading দেনাপাওনা",
        "created_at": "2026-05-31T09:02:32+00:00",
    }

    candidates = server._wallet_refund_candidates([tx])

    assert len(candidates) == 1
    assert candidates[0]["issue"] == "stale_gap_overcharge"
    assert candidates[0]["refundable_seconds"] == 1680


def test_refund_review_flags_duplicate_pulse(monkeypatch):
    server = load_server(monkeypatch)
    txs = [
        {
            "id": "tx-1",
            "user_id": "user-1",
            "type": "consume",
            "seconds": -30,
            "session_id": "session-1",
            "created_at": "2026-05-31T09:00:00+00:00",
        },
        {
            "id": "tx-2",
            "user_id": "user-1",
            "type": "consume",
            "seconds": -30,
            "session_id": "session-1",
            "created_at": "2026-05-31T09:00:04+00:00",
        },
    ]

    candidates = server._wallet_refund_candidates(txs)

    assert len(candidates) == 1
    assert candidates[0]["issue"] == "duplicate_pulse"
    assert candidates[0]["source_transaction_id"] == "tx-2"
    assert candidates[0]["refundable_seconds"] == 30


def test_refund_review_excludes_already_refunded_candidate(monkeypatch):
    server = load_server(monkeypatch)
    tx = {
        "id": "tx-bulk",
        "user_id": "user-1",
        "type": "consume",
        "seconds": -90,
        "session_id": "session-1",
        "created_at": "2026-05-31T09:02:32+00:00",
    }
    candidate_id = server._wallet_refund_candidate_id("user-1", "tx-bulk", "stale_gap_overcharge", 60)

    assert server._wallet_refund_candidates([tx], {candidate_id}) == []
