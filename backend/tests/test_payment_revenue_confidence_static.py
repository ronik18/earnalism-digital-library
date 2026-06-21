"""Static payment revenue confidence gates.

These tests intentionally avoid importing backend.server or calling Razorpay.
They verify the source-level contracts that keep test-mode revenue validation
safe: user-scoped verification, signed webhooks, idempotent wallet credit,
stale-intent blocking, and no public audiobook monetization copy.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def compact(source: str) -> str:
    return re.sub(r"\s+", "", source)


def extract_between(source: str, start_marker: str, end_marker: str) -> str:
    start = source.find(start_marker)
    assert start >= 0, f"Missing start marker: {start_marker}"
    body = source[start + len(start_marker):]
    end = body.find(end_marker)
    assert end >= 0, f"Missing end marker after {start_marker}: {end_marker}"
    return body[:end]


SERVER = read("backend/server.py")
COMPACT_SERVER = compact(SERVER)
PACKAGE = json.loads(read("package.json"))
PRICING = read("frontend/src/pages/Pricing.jsx")
ACCOUNT = read("frontend/src/pages/Account.jsx")
HOME = read("frontend/src/pages/Home.jsx")
LIBRARY = read("frontend/src/pages/Library.jsx")
BOOK_DETAIL = read("frontend/src/pages/BookDetail.jsx")
PUBLIC_PAYMENT_COPY = "\n".join([PRICING, ACCOUNT, HOME, LIBRARY, BOOK_DETAIL])


def test_pack_catalogue_ids_and_amounts_are_unchanged() -> None:
    pack_block = extract_between(SERVER, "PACKS: List[dict] = [", "]\nPACKS_BY_ID")
    for expected in [
        '"id": "30m"',
        '"label": "The First Chapter"',
        '"amount_paise": 4900',
        '"id": "1h"',
        '"label": "The Quiet Hour"',
        '"amount_paise": 8900',
        '"id": "3h"',
        '"label": "The Deep Reading Pass"',
        '"amount_paise": 23900',
        '"id": "10h"',
        '"label": "The Reader’s Reserve"',
        '"amount_paise": 49900',
    ]:
        assert expected in pack_block


def test_wallet_credit_helper_is_atomic_expiring_and_ledgered() -> None:
    helper = extract_between(
        SERVER,
        "async def _credit_wallet_for_intent",
        "# ---------- Reader: create a top-up intent",
    )
    assert "_topup_intent_is_expired(intent)" in helper
    assert "intent_expired" in helper
    assert '"status":{"$ne":"credited"}' in compact(helper)
    assert '"$inc":{"reading_seconds_balance":seconds,"wallet_seconds":seconds}' in compact(helper)
    assert "_record_wallet_ledger" in helper


def test_verify_endpoint_is_user_scoped_signed_and_rejects_expired_credit() -> None:
    verify = extract_between(SERVER, "async def payments_verify", "# ---------- Razorpay webhook")
    assert '{"razorpay_order_id":payload.razorpay_order_id,"user_id":user["id"]}' in compact(verify)
    assert "_hmac_sha256_hex" in verify
    assert "hmac.compare_digest" in verify
    assert '"failed_reason":"bad_signature"' in compact(verify)
    assert "_credit_wallet_for_intent" in verify
    assert 'refreshed.get("status") != "credited"' in verify
    assert "Top-up intent is expired or not creditable" in verify


def test_webhook_requires_secret_signature_dedupes_and_marks_failures() -> None:
    webhook = extract_between(SERVER, "async def payments_webhook", "# ---------- Dev-only")
    assert "RAZORPAY_WEBHOOK_SECRET" in webhook
    assert "X-Razorpay-Signature" in webhook
    assert "Invalid webhook signature" in webhook
    assert "rejected_bad_signature" in webhook
    assert "payment_webhook_events.find_one" in webhook
    assert "duplicate" in webhook
    assert 'event == "payment.captured"' in webhook
    assert "_credit_wallet_for_intent" in webhook
    assert 'event == "payment.failed"' in webhook
    assert '"status":"failed"' in compact(webhook)


def test_test_mode_simulators_cannot_cross_credit_or_run_outside_test_mode() -> None:
    simulator = extract_between(SERVER, "async def payments_simulate_topup", "# ---------- Reader: own top-up history")
    assert 'RAZORPAY_MODE != "test"' in simulator
    assert "Simulator disabled outside test mode" in simulator
    assert '"mode":"test_simulated"' in compact(simulator)
    assert "expires_at" in simulator
    assert 'intent["user_id"] != user["id"]' in simulator
    assert "Not your intent" in simulator
    assert 'intent["status"] == "credited"' in simulator
    assert "_credit_wallet_for_intent" in simulator


def test_admin_reconcile_and_refund_paths_are_idempotent() -> None:
    reconcile = extract_between(SERVER, "async def admin_reconcile_intent", "@api.get(\"/admin/cache/status\")")
    refund = extract_between(SERVER, "async def admin_wallet_refund_approve", "@api.patch(\"/admin/users/{uid}/status\")")
    assert 'intent["status"] == "credited"' in reconcile
    assert "_credit_wallet_for_intent" in reconcile
    assert '"duplicate": True' in reconcile
    assert "wallet_refunds.update_one" in refund
    assert "$setOnInsert" in refund
    assert "applied_seconds <= 0" in refund


def test_payment_smoke_is_static_test_mode_only() -> None:
    assert (
        PACKAGE["scripts"]["launch:payment-smoke:test-mode"]
        == "python3 scripts/launch_readiness_audit.py --mode payment-smoke-test-mode"
    )
    audit = read("scripts/launch_readiness_audit.py")
    assert '"mode": "dry_run_static"' in audit
    assert '"external_calls": []' in audit
    assert '"no_external_razorpay_call": True' in audit
    assert '"stale_intent_expiry_detected"' in audit
    assert '"test_mode_smoke_script_detected"' in audit


def test_public_payment_copy_does_not_sell_subscription_ownership_or_audiobooks() -> None:
    lowered = PUBLIC_PAYMENT_COPY.lower()
    assert "no subscription or autorenewal" in lowered
    assert "used only while you read" in lowered
    assert "wallet" in lowered
    for forbidden in [
        "own forever",
        "ownership forever",
        "permanent ownership",
        "autorenewing plan",
        "recurring subscription",
        "buy audiobook",
        "audiobook pass",
        "listen now",
    ]:
        assert forbidden not in lowered
    assert "dracula audio is not available yet" in lowered
    assert "coming soon until source, rights, and qa pass" in lowered


def test_payment_confidence_report_keeps_public_audio_and_live_money_blocked() -> None:
    report = read("PAYMENT_REVENUE_10X_CONFIDENCE_REPORT.md")
    assert "Status: `HOLD_FOR_CONTROLLED_TEST_MODE_CHECKOUT`" in report
    assert "No live Razorpay payment was run" in report
    assert "Public audio remains `PUBLIC_AUDIO_RELEASE_BLOCKED`" in report
    assert "No audiobook sale is live" in report
    assert "No subscription or autorenewal" in report
    assert "Top-up intents expire after 24 hours" in report
    assert "Current confidence score: `9.1/10`" in report
