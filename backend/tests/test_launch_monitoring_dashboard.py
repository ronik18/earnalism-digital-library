from __future__ import annotations

import asyncio
import json
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "test-secret")

from backend import server


class FakeAggregate:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, _limit):
        return self.rows


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def sort(self, *_args, **_kwargs):
        return self

    async def to_list(self, limit):
        return self.rows[:limit]


def matches_query(row, query):
    for key, expected in (query or {}).items():
        actual = row.get(key)
        if isinstance(expected, dict):
            if "$gte" in expected and str(actual or "") < str(expected["$gte"]):
                return False
            if "$in" in expected and actual not in expected["$in"]:
                return False
            continue
        if actual != expected:
            return False
    return True


class FakeCollection:
    def __init__(self, rows):
        self.rows = list(rows)
        self.inserted = []

    async def count_documents(self, query):
        return sum(1 for row in self.rows if matches_query(row, query))

    def aggregate(self, pipeline):
        match = pipeline[0].get("$match", {})
        group = pipeline[1].get("$group", {})
        field = str(group.get("_id", "")).lstrip("$")
        counts = {}
        for row in self.rows:
            if not matches_query(row, match):
                continue
            key = row.get(field) or "unknown"
            counts[key] = counts.get(key, 0) + 1
        return FakeAggregate([{"_id": key, "count": value} for key, value in counts.items()])

    def find(self, query, _projection=None):
        return FakeCursor([row for row in self.rows if matches_query(row, query)])

    async def insert_one(self, doc):
        self.inserted.append(doc)
        self.rows.append(doc)
        return SimpleNamespace(inserted_id=doc.get("id"))


class FakeRequest:
    headers = {"user-agent": "pytest", "referer": "https://theearnalism.com/"}
    client = SimpleNamespace(host="127.0.0.1")
    url = SimpleNamespace(path="/api/analytics/event")


def test_analytics_document_accepts_only_approved_events_without_pii():
    payload = server.AnalyticsEventIn(
        event_name="homepage_view",
        route="/",
        book_slug="dracula",
        anonymous_session_id="anon-session-1",
        metadata={"launch_status": "LIVE_VERIFIED", "public_audio_status": "PUBLIC_AUDIO_RELEASE_BLOCKED"},
    )

    doc = server._analytics_event_document(payload, FakeRequest(), None)

    assert doc["event"] == "homepage_view"
    assert doc["book_slug"] == "dracula"
    assert doc["anonymous_session_id"] == "anon-session-1"
    assert doc["metadata"]["launch_status"] == "LIVE_VERIFIED"


def test_analytics_document_rejects_unknown_event():
    payload = server.AnalyticsEventIn(event_name="newsletter_joined", metadata={"source": "home"})

    with pytest.raises(server.HTTPException) as exc:
        server._analytics_event_document(payload, FakeRequest(), None)

    assert exc.value.status_code == 400
    assert "Unknown launch analytics event" in str(exc.value.detail)


def test_analytics_document_rejects_pii_and_payment_like_fields():
    payload = server.AnalyticsEventIn(
        event_name="checkout_started",
        metadata={
            "pack_id": "30m",
            "price_inr": 49,
            "razorpay_payment_id": "pay_live_1234567890",
        },
    )

    with pytest.raises(server.HTTPException) as exc:
        server._analytics_event_document(payload, FakeRequest(), None)

    assert exc.value.status_code == 400
    assert "Unsafe analytics metadata" in json.dumps(exc.value.detail)


def test_launch_monitor_summary_aggregates_safe_counts(monkeypatch):
    now = server.now_iso()
    fake_db = SimpleNamespace(
        analytics_events=FakeCollection([
            {"event": "homepage_view", "created_at": now, "metadata": {}, "route": "/"},
            {"event": "hero_read_chapter_free_click", "created_at": now, "metadata": {}, "route": "/"},
            {"event": "checkout_started", "created_at": now, "metadata": {}, "route": "/pricing"},
            {"event": "payment_success_return", "created_at": now, "metadata": {}, "route": "/account"},
            {"event": "core_web_vital", "created_at": now, "metadata": {"metric": "LCP", "value": 1400, "rating": "good"}, "route": "/"},
        ]),
        topup_intents=FakeCollection([
            {"status": "credited", "created_at": now},
            {"status": "failed", "created_at": now},
        ]),
        payment_webhook_events=FakeCollection([
            {"status": "credited", "created_at": now},
            {"status": "duplicate_replay_blocked", "created_at": now},
        ]),
        wallet_ledger=FakeCollection([{"action": "topup_credit", "timestamp": now}]),
        contacts=FakeCollection([{"status": "open", "created_at": now}]),
        wallet_refunds=FakeCollection([{"status": "pending", "created_at": now}]),
    )
    monkeypatch.setattr(server, "db", fake_db)

    summary = asyncio.run(server.build_launch_monitor_summary())

    assert summary["dashboard_status"] == "OWNER_ADMIN_ONLY"
    assert summary["public_audio_status"] == "PUBLIC_AUDIO_RELEASE_BLOCKED"
    assert summary["audiobook_production_status"] == "PRODUCTION_BLOCKED"
    counts = summary["funnel"]["last_24h"]["counts"]
    assert counts["homepage_view"] == 1
    assert counts["hero_read_chapter_free_click"] == 1
    assert summary["payment"]["last_24h"]["payment_success_count"] == 1
    assert summary["payment"]["last_24h"]["payment_failed_count"] == 1
    assert summary["payment"]["last_24h"]["wallet_credit_count"] == 1
    assert summary["payment"]["last_24h"]["webhook_duplicate_replay_blocked_count"] == 1
    assert summary["core_web_vitals"]["status"] == "COLLECTING"
    assert "razorpay_payment_id" not in json.dumps(summary)
    assert "customer_email" not in json.dumps(summary)


def test_launch_monitor_admin_route_is_protected():
    routes = [route for route in server.api.routes if getattr(route, "path", "") == "/api/admin/launch-monitor/summary"]

    assert routes
    assert any(dependency.call is server.require_admin for dependency in routes[0].dependant.dependencies)
