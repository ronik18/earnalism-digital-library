"""Phase 3 — Razorpay TEST MODE wallet top-up tests.

Covers:
- /api/payments/packs catalogue (4 packs, exact prices/minutes)
- /api/payments/config (configured:false, mode:test)
- /api/payments/topup auth + 503 'not configured' branch
- /api/payments/_simulate_topup + /_simulate_webhook full credit flow
- Idempotency (no double-credit on second webhook)
- Cross-user 403, 404 not found
- /api/payments/webhook 503 when secret missing
- /api/payments/verify 404 when no intent
- /api/payments/me/intents (caller-only)
- /api/admin/payments/intents, /webhooks, /reconcile (admin-only)
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@theearnalism.com")
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "Earnalism@2026")


# ---------- shared fixtures ----------
@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="module")
def admin_headers(s):
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _make_user(s, prefix="pay"):
    email = f"TEST_{prefix}-{int(time.time()*1000)}-{uuid.uuid4().hex[:6]}@test.com"
    password = "TestPass123"
    r = s.post(f"{API}/users/signup", json={"name": "Pay Tester", "email": email, "password": password})
    assert r.status_code == 200, r.text
    j = r.json()
    return {
        "email": email,
        "token": j["token"],
        "user": j["user"],
        "headers": {"Authorization": f"Bearer {j['token']}"},
    }


@pytest.fixture(scope="module")
def user_a(s):
    return _make_user(s, "a")


@pytest.fixture(scope="module")
def user_b(s):
    return _make_user(s, "b")


# ---------- /payments/packs catalogue ----------
class TestPacksCatalogue:
    def test_packs_returns_four_in_order(self, s):
        r = s.get(f"{API}/payments/packs")
        assert r.status_code == 200, r.text
        packs = r.json()
        assert isinstance(packs, list) and len(packs) == 4
        ids = [p["id"] for p in packs]
        assert ids == ["30m", "1h", "3h", "10h"], f"order/ids mismatch: {ids}"

    def test_pack_minutes_and_prices(self, s):
        r = s.get(f"{API}/payments/packs")
        packs = {p["id"]: p for p in r.json()}
        expected = {
            "30m": (30, 49, 4900),
            "1h":  (60, 89, 8900),
            "3h":  (180, 239, 23900),
            "10h": (600, 499, 49900),
        }
        for pid, (mins, inr, paise) in expected.items():
            assert packs[pid]["minutes"] == mins, pid
            assert packs[pid]["price_inr"] == inr, pid
            assert packs[pid]["amount_paise"] == paise, pid


# ---------- /payments/config ----------
class TestPaymentsConfig:
    def test_config_unconfigured(self, s):
        r = s.get(f"{API}/payments/config")
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("configured") is False
        assert j.get("mode") == "test"
        assert j.get("key_id") == ""


# ---------- /payments/topup ----------
class TestTopupCreate:
    def test_topup_unauth_401(self, s):
        r = s.post(f"{API}/payments/topup", json={"pack_id": "1h"})
        assert r.status_code == 401, r.text

    def test_topup_with_keys_missing_503(self, s, user_a):
        r = s.post(f"{API}/payments/topup", json={"pack_id": "1h"}, headers=user_a["headers"])
        assert r.status_code == 503, r.text
        detail = (r.json().get("detail") or "").lower()
        assert "razorpay" in detail and "configured" in detail

    def test_topup_unknown_pack_400(self, s, user_a):
        r = s.post(f"{API}/payments/topup", json={"pack_id": "not_a_pack"}, headers=user_a["headers"])
        # Server checks unknown pack BEFORE keys-configured check.
        assert r.status_code == 400, r.text
        assert "unknown pack" in (r.json().get("detail") or "").lower()


# ---------- simulator: create intent ----------
class TestSimulateTopup:
    def test_simulate_topup_unauth_401(self, s):
        r = s.post(f"{API}/payments/_simulate_topup", json={"pack_id": "1h"})
        assert r.status_code == 401, r.text

    def test_simulate_topup_creates_intent_for_caller(self, s, user_a):
        r = s.post(f"{API}/payments/_simulate_topup", json={"pack_id": "1h"}, headers=user_a["headers"])
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["simulated"] is True
        assert j["amount"] == 8900
        assert j["currency"] == "INR"
        assert j["razorpay_order_id"].startswith("order_test_")
        intent_id = j["intent_id"]
        # GET /payments/me/intents shows it as 'created'
        r2 = s.get(f"{API}/payments/me/intents", headers=user_a["headers"])
        assert r2.status_code == 200
        rows = r2.json()
        match = [x for x in rows if x["id"] == intent_id]
        assert len(match) == 1
        assert match[0]["status"] == "created"
        assert match[0]["pack_id"] == "1h"
        assert match[0]["minutes"] == 60
        assert match[0]["user_id"] == user_a["user"]["id"]


# ---------- simulator webhook: credit + idempotency + perms ----------
class TestSimulateWebhookCredits:
    def test_credit_and_idempotency(self, s, user_a):
        # Re-fetch baseline balance
        me0 = s.get(f"{API}/users/me", headers=user_a["headers"]).json()
        bal_before = int(me0.get("reading_seconds_balance", 0))

        # Create a fresh 30m intent
        topup = s.post(f"{API}/payments/_simulate_topup", json={"pack_id": "30m"}, headers=user_a["headers"])
        assert topup.status_code == 200
        intent_id = topup.json()["intent_id"]

        # First webhook -> credits 30*60 = 1800s
        r = s.post(f"{API}/payments/_simulate_webhook?intent_id={intent_id}", headers=user_a["headers"])
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["ok"] is True
        assert j.get("simulated") is True or j.get("duplicate") is True
        intent = j["intent"]
        assert intent["status"] == "credited"
        assert intent.get("razorpay_payment_id", "").startswith("pay_test_")

        me1 = s.get(f"{API}/users/me", headers=user_a["headers"]).json()
        bal_after_1 = int(me1["reading_seconds_balance"])
        assert bal_after_1 == bal_before + 1800, f"expected +1800s, got {bal_after_1 - bal_before}"

        # Wallet transactions should contain a credit row referencing 'Razorpay top-up'
        tx = s.get(f"{API}/users/me/transactions", headers=user_a["headers"]).json()
        credit_rows = [t for t in tx if t.get("type") == "credit" and "razorpay" in (t.get("reason", "")).lower()]
        assert len(credit_rows) >= 1, f"no razorpay credit row found in tx: {tx[:3]}"

        # Second webhook -> duplicate, no extra credit
        r2 = s.post(f"{API}/payments/_simulate_webhook?intent_id={intent_id}", headers=user_a["headers"])
        assert r2.status_code == 200, r2.text
        j2 = r2.json()
        assert j2.get("duplicate") is True

        me2 = s.get(f"{API}/users/me", headers=user_a["headers"]).json()
        bal_after_2 = int(me2["reading_seconds_balance"])
        assert bal_after_2 == bal_after_1, f"DOUBLE-CREDIT BUG: bal went {bal_after_1} -> {bal_after_2}"

    def test_simulate_webhook_unauth_401(self, s, user_a):
        # Need an intent owned by user_a
        topup = s.post(f"{API}/payments/_simulate_topup", json={"pack_id": "30m"}, headers=user_a["headers"])
        intent_id = topup.json()["intent_id"]
        r = s.post(f"{API}/payments/_simulate_webhook?intent_id={intent_id}")
        assert r.status_code == 401, r.text

    def test_simulate_webhook_other_users_intent_403(self, s, user_a, user_b):
        topup = s.post(f"{API}/payments/_simulate_topup", json={"pack_id": "30m"}, headers=user_a["headers"])
        intent_id = topup.json()["intent_id"]
        r = s.post(f"{API}/payments/_simulate_webhook?intent_id={intent_id}", headers=user_b["headers"])
        assert r.status_code == 403, r.text
        assert "not your intent" in (r.json().get("detail") or "").lower()

    def test_simulate_webhook_nonexistent_404(self, s, user_a):
        fake = f"00000000-0000-0000-0000-{uuid.uuid4().hex[:12]}"
        r = s.post(f"{API}/payments/_simulate_webhook?intent_id={fake}", headers=user_a["headers"])
        assert r.status_code == 404, r.text


# ---------- /payments/webhook signed entry point ----------
class TestPaymentsWebhookEntry:
    def test_webhook_secret_missing_503(self, s):
        # No signature header, no secret configured -> 503 'not configured'
        r = s.post(f"{API}/payments/webhook", data=b"{}", headers={"Content-Type": "application/json"})
        assert r.status_code == 503, r.text


# ---------- /payments/verify ----------
class TestPaymentsVerify:
    def test_verify_no_intent_404(self, s, user_a):
        r = s.post(f"{API}/payments/verify",
                   json={"razorpay_order_id": "order_does_not_exist",
                         "razorpay_payment_id": "pay_x",
                         "razorpay_signature": "sig_x"},
                   headers=user_a["headers"])
        assert r.status_code == 404, r.text


# ---------- /payments/me/intents — only own ----------
class TestMyIntents:
    def test_me_intents_isolated(self, s, user_a, user_b):
        # ensure user_b has its own intent
        s.post(f"{API}/payments/_simulate_topup", json={"pack_id": "30m"}, headers=user_b["headers"])
        a_rows = s.get(f"{API}/payments/me/intents", headers=user_a["headers"]).json()
        b_rows = s.get(f"{API}/payments/me/intents", headers=user_b["headers"]).json()
        # No row visible to A should belong to B and vice versa
        a_uids = {r["user_id"] for r in a_rows}
        b_uids = {r["user_id"] for r in b_rows}
        assert a_uids <= {user_a["user"]["id"]}
        assert b_uids <= {user_b["user"]["id"]}
        assert user_b["user"]["id"] not in a_uids
        assert user_a["user"]["id"] not in b_uids


# ---------- /admin/payments/* ----------
class TestAdminPayments:
    def test_admin_intents_lists_all(self, s, admin_headers, user_a, user_b):
        # Make sure both users have at least one intent
        s.post(f"{API}/payments/_simulate_topup", json={"pack_id": "30m"}, headers=user_a["headers"])
        s.post(f"{API}/payments/_simulate_topup", json={"pack_id": "30m"}, headers=user_b["headers"])
        r = s.get(f"{API}/admin/payments/intents", headers=admin_headers)
        assert r.status_code == 200, r.text
        rows = r.json()
        uids = {row["user_id"] for row in rows}
        assert user_a["user"]["id"] in uids
        assert user_b["user"]["id"] in uids

    def test_admin_webhooks_lists_events(self, s, admin_headers, user_a):
        # Drive at least one credit -> webhook event row
        topup = s.post(f"{API}/payments/_simulate_topup", json={"pack_id": "30m"}, headers=user_a["headers"]).json()
        s.post(f"{API}/payments/_simulate_webhook?intent_id={topup['intent_id']}", headers=user_a["headers"])
        r = s.get(f"{API}/admin/payments/webhooks", headers=admin_headers)
        assert r.status_code == 200, r.text
        rows = r.json()
        assert len(rows) >= 1
        events = {row.get("event") for row in rows}
        assert "payment.captured" in events

    def test_admin_reconcile_idempotent(self, s, admin_headers, user_a):
        # Create an UNcredited intent (no webhook fired)
        topup = s.post(f"{API}/payments/_simulate_topup", json={"pack_id": "30m"}, headers=user_a["headers"]).json()
        intent_id = topup["intent_id"]

        # Snapshot user balance
        me0 = s.get(f"{API}/users/me", headers=user_a["headers"]).json()
        bal0 = int(me0["reading_seconds_balance"])

        # First reconcile -> credits
        r1 = s.post(f"{API}/admin/payments/intents/{intent_id}/reconcile",
                    json={"note": "manual fix"}, headers=admin_headers)
        assert r1.status_code == 200, r1.text
        j1 = r1.json()
        # First call should not be marked as duplicate
        assert j1.get("duplicate") is not True
        assert j1["intent"]["status"] == "credited"

        me1 = s.get(f"{API}/users/me", headers=user_a["headers"]).json()
        bal1 = int(me1["reading_seconds_balance"])
        assert bal1 == bal0 + 1800

        # Second reconcile -> duplicate, no credit
        r2 = s.post(f"{API}/admin/payments/intents/{intent_id}/reconcile",
                    json={"note": "manual fix again"}, headers=admin_headers)
        assert r2.status_code == 200, r2.text
        j2 = r2.json()
        assert j2.get("duplicate") is True

        me2 = s.get(f"{API}/users/me", headers=user_a["headers"]).json()
        bal2 = int(me2["reading_seconds_balance"])
        assert bal2 == bal1, f"reconcile DOUBLE-CREDIT: {bal1} -> {bal2}"

    def test_admin_endpoints_reject_user_token(self, s, user_a):
        h = user_a["headers"]
        for path in ("/admin/payments/intents", "/admin/payments/webhooks"):
            r = s.get(f"{API}{path}", headers=h)
            assert r.status_code == 403, f"{path} expected 403 for user, got {r.status_code}"

        r = s.post(f"{API}/admin/payments/intents/some-id/reconcile",
                   json={"note": "x"}, headers=h)
        assert r.status_code == 403, r.text
