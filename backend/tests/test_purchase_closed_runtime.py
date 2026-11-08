"""Isolated ASGI checks: no provider, database, paid session or capture."""
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from backend.commerce_territory import COMMERCE_ORDER_PATH
from backend.purchase_closed_runtime import PurchaseClosedApp, create_app
from backend.release_proxy_auth import request_signature


class PurchaseClosedRuntimeTests(unittest.TestCase):
    def invoke(self, scope):
        calls, messages = [], []

        async def delegate(*args):
            calls.append(args)

        async def receive():
            self.fail("Purchase closure must not read a request body")

        async def send(message):
            messages.append(message)

        asyncio.run(PurchaseClosedApp(delegate)(scope, receive, send))
        return calls, messages, receive, send

    def test_signed_and_unsigned_purchase_requests_never_reach_app(self):
        now = int(datetime.now(timezone.utc).timestamp())
        secret = "isolated-closure-test-not-a-provider-credential"
        signed = [(b"x-earnalism-release-scope", b"PUBLIC"),
                  (b"x-earnalism-release-country", b"IN"),
                  (b"x-earnalism-release-timestamp", str(now).encode()),
                  (b"x-earnalism-release-signature", request_signature(
                      secret, "POST", COMMERCE_ORDER_PATH, "PUBLIC", now, "IN").encode())]
        for headers in ([], signed, [(b"x-vercel-ip-country", b"IN")]):
            for suffix in ("", "/"):
                with self.subTest(headers=headers, suffix=suffix):
                    calls, messages, _, _ = self.invoke({
                        "type": "http", "method": "POST", "path": COMMERCE_ORDER_PATH + suffix,
                        "headers": headers, "query_string": b"ignored=1"})
                    self.assertEqual(calls, [])
                    self.assertEqual(messages[0]["status"], 503)
                    self.assertIn((b"cache-control", b"no-store"), messages[0]["headers"])
                    self.assertIn(b"PURCHASE_INITIATION_CLOSED", messages[1]["body"])

    def test_existing_access_settlement_and_lifecycle_pass_through_unchanged(self):
        scopes = [{"type": "http", "method": "POST", "path": path} for path in (
            "/api/payments/verify", "/api/payments/webhook",
            "/api/admin/users/dummy/wallet/refund-approve", "/api/reading-pass/leases/renew",
            "/api/auth/login", COMMERCE_ORDER_PATH + "/unrelated")]
        scopes += [{"type": "http", "method": "GET", "path": path} for path in (
            "/healthz", "/api/books", "/api/reader/dummy", "/api/audiobooks/dummy",
            COMMERCE_ORDER_PATH)]
        scopes += [{"type": "http", "method": "OPTIONS", "path": COMMERCE_ORDER_PATH},
                   {"type": "lifespan"}, {"type": "websocket", "path": "/ws"}]
        for scope in scopes:
            with self.subTest(scope=scope):
                calls, messages, receive, send = self.invoke(scope)
                self.assertEqual(len(calls), 1)
                self.assertIs(calls[0][0], scope)
                self.assertIs(calls[0][1], receive)
                self.assertIs(calls[0][2], send)
                self.assertEqual(messages, [])

    def test_closed_factory_is_retained_but_owner_reopened_startup_uses_app(self):
        delegate = object()
        with patch.dict(sys.modules, {"server": SimpleNamespace(app=delegate)}):
            self.assertIs(create_app().app, delegate)
        script = (Path(__file__).resolve().parents[1] / "start_prod.sh").read_text()
        self.assertIn("exec uvicorn server:app", script)
        self.assertNotIn("exec uvicorn purchase_closed_runtime:create_app --factory", script)


if __name__ == "__main__":
    unittest.main()
