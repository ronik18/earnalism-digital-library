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
