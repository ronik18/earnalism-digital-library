from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import re
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
            if "$exists" in expected and ((key in row) != expected["$exists"]):
                return False
            if "$gte" in expected and str(actual or "") < str(expected["$gte"]):
                return False
            if "$in" in expected and actual not in expected["$in"]:
                return False
            if "$nin" in expected and actual in expected["$nin"]:
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

    async def update_one(self, query, update, upsert=False):
        if any(matches_query(row, query) for row in self.rows):
            return SimpleNamespace(matched_count=1, upserted_id=None)
        if upsert:
            doc = dict(update.get("$setOnInsert") or {})
            self.inserted.append(doc)
            self.rows.append(doc)
            return SimpleNamespace(matched_count=0, upserted_id=doc.get("id"))
        return SimpleNamespace(matched_count=0, upserted_id=None)


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


def test_analytics_collector_stores_the_sanitized_event(monkeypatch):
    analytics = FakeCollection([])
    monkeypatch.setattr(server, "db", SimpleNamespace(analytics_events=analytics))
    payload = server.AnalyticsEventIn(
        event_name="library_view",
        route="/library?next=%2Faccount",
        anonymous_session_id="anonymous-session-1234",
        deployment_environment="local",
        metadata={"utm_source": "newsletter", "referrer_category": "campaign"},
    )

    asyncio.run(server.record_analytics_event(payload, FakeRequest(), None))

    assert len(analytics.rows) == 1
    stored = analytics.rows[0]
    assert stored["event"] == "library_view"
    assert stored["route"] == "/library"
    assert stored["deployment_environment"] == "local"
    assert stored["utm_source"] == "newsletter"
    assert "next=" not in json.dumps(stored)


def test_analytics_document_rejects_unknown_event():
    payload = server.AnalyticsEventIn(event_name="newsletter_joined", metadata={"source": "home"})

    with pytest.raises(server.HTTPException) as exc:
        server._analytics_event_document(payload, FakeRequest(), None)

    assert exc.value.status_code == 400
    assert "Unknown launch analytics event" in str(exc.value.detail)


def test_every_client_event_is_accepted_but_checkout_and_purchase_are_server_owned():
    source_root = Path(__file__).resolve().parents[2]
    source = (source_root / "frontend/src/lib/funnelAnalytics.js").read_text(encoding="utf-8")
    declared = source.split("export const LAUNCH_ANALYTICS_EVENTS = [", 1)[1].split("];", 1)[0]
    client_events = set(re.findall(r'"([a-z0-9_]+)"', declared))
    assert client_events <= server.APPROVED_LAUNCH_ANALYTICS_EVENTS
    assert "checkout_started" not in client_events
    assert "purchase_completed" not in client_events


def test_supported_newsletter_and_support_events_store_only_non_pii_fields():
    for event, metadata in [
        ("newsletter_submit_success", {"source": "reading_circle"}),
        ("support_complaint_created", {"source": "contact_form", "has_subject": True, "message_type": "reader_support"}),
    ]:
        payload = server.AnalyticsEventIn(event_name=event, metadata=metadata)
        document = server._analytics_event_document(payload, FakeRequest(), None)
        assert document["event"] == event
        assert document["metadata"] == metadata


def test_purchase_completion_cannot_be_forged_by_client():
    payload = server.AnalyticsEventIn(event_name="purchase_completed", metadata={"amount_inr": 49})
    with pytest.raises(server.HTTPException) as exc:
        server._analytics_event_document(payload, FakeRequest(), None)
    assert exc.value.status_code == 400
    assert "server-side" in str(exc.value.detail)


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


def test_analytics_event_stores_path_and_coarse_attribution_only():
    payload = server.AnalyticsEventIn(
        event_name="homepage_view",
        route="https://theearnalism.com/?email=reader%40example.com&utm_source=letter",
        anonymous_session_id="anonymous-session-1234",
        metadata={"utm_source": "letter", "referrer_category": "campaign"},
    )
    doc = server._analytics_event_document(payload, FakeRequest(), {"id": "private-user-id", "role": "user"})
    assert doc["route"] == "/"
    assert doc["utm_source"] == "letter"
    assert doc["referrer_category"] == "campaign"
    assert doc["deployment_environment"] == "production"
    assert "principal_id" not in doc and "user_agent" not in doc and "path" not in doc
    assert "reader@example.com" not in json.dumps(doc)


def test_purchase_event_is_authoritative_and_idempotent(monkeypatch):
    analytics = FakeCollection([])
    monkeypatch.setattr(server, "db", SimpleNamespace(analytics_events=analytics))
    intent = {
        "id": "intent-private-value",
        "status": "credited",
        "analytics_session_id": "anonymous-session-1234",
        "analytics_attribution": {"utm_source": "newsletter", "referrer_category": "campaign"},
        "pack_id": "reading-30",
        "minutes": 30,
        "amount_paise": 4900,
        "currency": "INR",
    }
    asyncio.run(server._record_purchase_conversion(intent))
    asyncio.run(server._record_purchase_conversion(intent))
    assert len(analytics.rows) == 1
    event = analytics.rows[0]
    assert event["event"] == "purchase_completed"
    assert event["metadata"]["outcome"] == "credited"
    assert event["metadata"]["amount_inr"] == 49
    assert event["event_id"].startswith("verified-purchase:")
    assert "intent-private-value" not in json.dumps(event)
    assert "payment_id" not in json.dumps(event)


def test_uncredited_intent_never_emits_purchase(monkeypatch):
    analytics = FakeCollection([])
    monkeypatch.setattr(server, "db", SimpleNamespace(analytics_events=analytics))
    asyncio.run(server._record_purchase_conversion({"id": "not-credited", "status": "failed"}))
    assert analytics.rows == []


def test_ordered_funnel_metrics_counts_sessions_and_dropoff():
    event_counts = {"homepage_view": 3, "library_view": 2, "title_view": 1}
    progress = {"discovery": [3, 2]}
    report = server._funnel_report_from_progress_counts(event_counts, progress)["discovery"]
    assert report[0]["unique_sessions"] == 3
    assert report[1]["unique_sessions"] == 2
    assert report[0]["conversion_to_next_pct"] == 66.67
    assert report[0]["dropoff_count"] == 1


def test_production_dashboard_excludes_preview_and_local_analytics(monkeypatch):
    now = server.now_iso()
    analytics = FakeCollection([
        {"event": "page_view", "route": "/", "created_at": now, "deployment_environment": "production"},
        {"event": "page_view", "route": "/", "created_at": now, "deployment_environment": "preview"},
        {"event": "page_view", "route": "/", "created_at": now, "deployment_environment": "local"},
        {"event": "page_view", "route": "/", "created_at": now},  # legacy production records
    ])
    monkeypatch.setattr(server, "db", SimpleNamespace(analytics_events=analytics))
    counts = asyncio.run(server._group_counts_since("analytics_events", "route", "created_at", "2026-01-01T00:00:00+00:00", {"event": "page_view"}))
    assert counts == {"/": 2}


def test_server_analytics_storage_failure_does_not_escape_into_product_flow(monkeypatch):
    class FailingCollection:
        async def insert_one(self, _doc):
            raise RuntimeError("analytics database unavailable")

    monkeypatch.setattr(server, "db", SimpleNamespace(analytics_events=FailingCollection()))
    asyncio.run(server._record_server_analytics_event("checkout_failed", route="/pricing"))


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
