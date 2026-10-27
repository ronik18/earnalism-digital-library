"""No provider calls, database access or wallet mutations."""
import ast
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest

from backend.commerce_territory import COMMERCE_ORDER_PATH, commerce_territory_verdict
from backend.release_proxy_auth import request_signature

SECRET = "isolated-commerce-test-secret-more-than-32-characters"
NOW = datetime.now(timezone.utc)


def signed(country="IN", path=COMMERCE_ORDER_PATH, method="POST"):
    timestamp = int(NOW.timestamp())
    return {
        "x-earnalism-release-scope": "PUBLIC",
        "x-earnalism-release-country": country,
        "x-earnalism-release-timestamp": str(timestamp),
        "x-earnalism-release-signature": request_signature(SECRET, method, path, "PUBLIC", timestamp, country),
    }


class CommerceTerritoryTests(unittest.TestCase):
    def verdict(self, headers, **kwargs):
        return commerce_territory_verdict(headers, method="POST", path=COMMERCE_ORDER_PATH, secret=SECRET, now=NOW, **kwargs)

    def test_india_signed_order_admitted(self):
        self.assertTrue(self.verdict(signed()).allowed)

    def test_overseas_unknown_direct_and_forged_orders_denied(self):
        for headers in (signed("US"), signed("GB"), signed("ZZ"), {}, {"x-vercel-ip-country": "IN"}, {**signed("US"), "x-earnalism-release-country": "IN"}):
            self.assertFalse(self.verdict(headers).allowed)

    def test_missing_secret_stale_and_wrong_path_rejected(self):
        self.assertFalse(commerce_territory_verdict(signed(), method="POST", path=COMMERCE_ORDER_PATH, secret="").allowed)
        self.assertFalse(self.verdict({**signed(), "x-earnalism-release-timestamp": "1"}).allowed)
        self.assertFalse(commerce_territory_verdict(signed(path="/api/books"), method="GET", path="/api/books", secret=SECRET).allowed)

    def test_actual_middleware_blocks_before_handler_independent_of_reader_flag(self):
        # Execute the actual middleware body without booting a production app,
        # loading credentials, importing the large server or touching databases.
        source = Path(__file__).parents[1].joinpath("server.py").read_text()
        function = next(n for n in ast.parse(source).body if isinstance(n, ast.AsyncFunctionDef) and n.name == "enforce_public_release_country")
        function.decorator_list = []
        class Response:
            def __init__(self, status_code=204, **kwargs): self.status_code = status_code
        calls = []
        async def handler(request):
            calls.append(request)
            return Response()
        namespace = dict(Request=object, ENVIRONMENT="production", PUBLIC_READER_EXPOSURE_ENABLED=False,
                         COMMERCE_ORDER_PATH=COMMERCE_ORDER_PATH, commerce_territory_verdict=commerce_territory_verdict,
                         os=SimpleNamespace(getenv=lambda *args: SECRET), JSONResponse=Response)
        exec(compile(ast.Module(body=[function], type_ignores=[]), "server-middleware", "exec"), namespace)
        for headers in ({}, signed("US"), {"x-vercel-ip-country": "IN"}):
            req = SimpleNamespace(method="POST", url=SimpleNamespace(path=COMMERCE_ORDER_PATH), headers=headers)
            result = asyncio.run(namespace[function.name](req, handler))
            self.assertEqual(result.status_code, 451)
        self.assertEqual(calls, [])
        req.headers = signed()
        self.assertEqual(asyncio.run(namespace[function.name](req, handler)).status_code, 204)
        # Webhook/reconciliation and existing refunds must not require visitor geography.
        for path in ("/api/payments/webhook", "/api/payments/verify", "/api/admin/refunds"):
            req.url.path = path
            req.headers = {}
            self.assertEqual(asyncio.run(namespace[function.name](req, handler)).status_code, 204)


if __name__ == "__main__": unittest.main()
