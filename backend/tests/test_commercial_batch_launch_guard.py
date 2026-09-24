from __future__ import annotations

import asyncio

import pytest

from backend import server
from backend.api.schemas import TopUpCreateIn


def test_production_commerce_requires_live_razorpay_configuration(monkeypatch):
    monkeypatch.setattr(server, "ENVIRONMENT", "production")
    monkeypatch.setattr(server, "PUBLIC_PAID_COMMERCE_ENABLED", True)
    monkeypatch.setattr(server, "RAZORPAY_MODE", "test")
    monkeypatch.setattr(server, "RAZORPAY_KEY_ID", "")
    monkeypatch.setattr(server, "RAZORPAY_KEY_SECRET", "")
    monkeypatch.setattr(server, "RAZORPAY_WEBHOOK_SECRET", "")
    assert server._public_paid_commerce_available() is False

    monkeypatch.setattr(server, "RAZORPAY_MODE", "live")
    monkeypatch.setattr(server, "RAZORPAY_KEY_ID", "live-key-id")
    monkeypatch.setattr(server, "RAZORPAY_KEY_SECRET", "live-key-secret")
    assert server._public_paid_commerce_available() is False

    monkeypatch.setattr(server, "RAZORPAY_WEBHOOK_SECRET", "live-webhook-secret")
    assert server._public_paid_commerce_available() is True


def test_production_simulator_cannot_credit_wallet_even_if_commerce_flag_is_misconfigured(monkeypatch):
    monkeypatch.setattr(server, "ENVIRONMENT", "production")
    monkeypatch.setattr(server, "PUBLIC_PAID_COMMERCE_ENABLED", True)
    monkeypatch.setattr(server, "RAZORPAY_MODE", "test")
    monkeypatch.setattr(server, "_production_payment_ready", lambda: True)

    async def forbidden_insert(*_args, **_kwargs):
        pytest.fail("production simulator must not create a credit intent")

    monkeypatch.setattr(server.db.topup_intents, "insert_one", forbidden_insert)
    with pytest.raises(server.HTTPException) as denied:
        asyncio.run(
            server.payments_simulate_topup(
                TopUpCreateIn(pack_id="1h"),
                {"id": "fixture-user", "email": "reader@example.test"},
            )
        )
    assert denied.value.status_code == 403


def test_existing_free_pilot_stays_full_free_while_prepared_batch_is_metered():
    assert server._title_text_access_mode("a-ghost-story") == "PILOT_FULL_FREE"
    assert server._title_text_access_mode("the-tell-tale-heart") == "PILOT_FULL_FREE"
    assert server._title_text_access_mode("radharani") == "PILOT_FULL_FREE"
    assert server._title_text_access_mode("a-white-heron") == "COMMERCIAL_ENTITLEMENT"
    assert server._title_text_access_mode("the-gift-of-the-magi") == "COMMERCIAL_ENTITLEMENT"
    assert server._title_text_access_mode("the-canterville-ghost") == "COMMERCIAL_ENTITLEMENT"
    assert server._title_text_access_mode("yugalanguriya") is None
