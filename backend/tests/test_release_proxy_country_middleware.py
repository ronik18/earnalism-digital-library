from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import os

from fastapi import Response
from starlette.requests import Request

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "release-proxy-country-middleware-test-secret")

from backend import server
from backend.release_proxy_auth import COUNTRY_HEADER, PUBLIC_RELEASE_SCOPE, SCOPE_HEADER, SIGNATURE_HEADER, TIMESTAMP_HEADER, request_signature
from backend.rights_decision_gate import DecisionGateVerdict


SECRET = "release-proxy-test-secret-that-is-long-enough"


def request_with_headers(headers: dict[str, str], *, path: str = "/api/books", method: str = "GET") -> Request:
    return Request({
        "type": "http",
        "method": method,
        "path": path,
        "headers": [(key.encode("latin-1"), value.encode("latin-1")) for key, value in headers.items()],
        "query_string": b"",
        "server": ("testserver", 443),
        "scheme": "https",
    })


async def next_response(_request: Request) -> Response:
    return Response(status_code=204)


def test_public_reader_release_rejects_direct_api_requests(monkeypatch):
    monkeypatch.setattr(server, "ENVIRONMENT", "production")
    monkeypatch.setattr(server, "PUBLIC_READER_EXPOSURE_ENABLED", True)
    monkeypatch.setenv("EARNALISM_RELEASE_PROXY_SECRET", SECRET)
    response = asyncio.run(server.enforce_public_release_country(request_with_headers({}), next_response))
    assert response.status_code == 451
    assert response.body == b'{"detail":{"code":"RELEASE_PROXY_SCOPE_INVALID"}}'


def test_free_session_proxy_and_hash_bound_rights_are_required_for_each_pilot(monkeypatch):
    monkeypatch.setattr(server, "ENVIRONMENT", "production")
    monkeypatch.setattr(server, "PUBLIC_READER_EXPOSURE_ENABLED", True)
    monkeypatch.setenv("EARNALISM_RELEASE_PROXY_SECRET", SECRET)
    path = "/api/reading-pass/sessions/start"
    timestamp = int(datetime.now(timezone.utc).timestamp())
    headers = {
        SCOPE_HEADER: PUBLIC_RELEASE_SCOPE,
        COUNTRY_HEADER: "IN",
        TIMESTAMP_HEADER: str(timestamp),
        SIGNATURE_HEADER: request_signature(SECRET, "POST", path, PUBLIC_RELEASE_SCOPE, timestamp, "IN"),
    }
    request = request_with_headers(headers, path=path, method="POST")
    for slug in ("a-ghost-story", "the-tell-tale-heart", "radharani"):
        assert server._free_india_reader_verdict(request, slug) is True
    for slug in ("yugalanguriya", "dracula", "unlisted-book"):
        assert server._free_india_reader_verdict(request, slug) is False
    assert server._free_india_reader_verdict(request_with_headers({}, path=path, method="POST"), "a-ghost-story") is False
    assert asyncio.run(server.enforce_public_release_country(request_with_headers({}, path=path, method="POST"), next_response)).status_code == 451

    us_headers = {**headers, COUNTRY_HEADER: "US"}
    us_headers[SIGNATURE_HEADER] = request_signature(SECRET, "POST", path, PUBLIC_RELEASE_SCOPE, timestamp, "US")
    us_request = request_with_headers(us_headers, path=path, method="POST")
    assert server._free_india_reader_verdict(us_request, "a-ghost-story") is False
    assert asyncio.run(server.enforce_public_release_country(us_request, next_response)).status_code == 451


def test_public_reader_release_accepts_fresh_signed_india_request(monkeypatch):
    monkeypatch.setattr(server, "ENVIRONMENT", "production")
    monkeypatch.setattr(server, "PUBLIC_READER_EXPOSURE_ENABLED", True)
    monkeypatch.setenv("EARNALISM_RELEASE_PROXY_SECRET", SECRET)
    monkeypatch.setattr(server, "_release_rights_verdict", lambda _request, *, country: DecisionGateVerdict(country == "IN", ()))
    timestamp = int(datetime.now(timezone.utc).timestamp())
    headers = {
        SCOPE_HEADER: PUBLIC_RELEASE_SCOPE,
        COUNTRY_HEADER: "IN",
        TIMESTAMP_HEADER: str(timestamp),
        SIGNATURE_HEADER: request_signature(SECRET, "GET", "/api/books", PUBLIC_RELEASE_SCOPE, timestamp, "IN"),
        "x-vercel-ip-country": "US",
    }
    response = asyncio.run(server.enforce_public_release_country(request_with_headers(headers), next_response))
    assert response.status_code == 204


def test_public_reader_release_denies_signed_request_without_accepted_rights(monkeypatch):
    monkeypatch.setattr(server, "ENVIRONMENT", "production")
    monkeypatch.setattr(server, "PUBLIC_READER_EXPOSURE_ENABLED", True)
    monkeypatch.setenv("EARNALISM_RELEASE_PROXY_SECRET", SECRET)
    monkeypatch.setattr(server, "_release_rights_verdict", lambda _request, *, country: DecisionGateVerdict(False, ("ACCEPTED_DECISION_MISSING",)))
    timestamp = int(datetime.now(timezone.utc).timestamp())
    headers = {
        SCOPE_HEADER: PUBLIC_RELEASE_SCOPE,
        COUNTRY_HEADER: "IN",
        TIMESTAMP_HEADER: str(timestamp),
        SIGNATURE_HEADER: request_signature(SECRET, "GET", "/api/books", PUBLIC_RELEASE_SCOPE, timestamp, "IN"),
    }

    response = asyncio.run(server.enforce_public_release_country(request_with_headers(headers), next_response))

    assert response.status_code == 451
    assert response.body == b'{"detail":{"code":"RELEASE_RIGHTS_DENIED"}}'


def test_isolated_uat_does_not_require_the_production_release_proxy(monkeypatch):
    monkeypatch.setattr(server, "ENVIRONMENT", "uat")
    monkeypatch.setattr(server, "PUBLIC_READER_EXPOSURE_ENABLED", True)

    response = asyncio.run(server.enforce_public_release_country(request_with_headers({}), next_response))

    assert response.status_code == 204


def test_runtime_rights_boundary_fails_closed_when_an_artifact_has_no_accepted_record(monkeypatch):
    monkeypatch.setattr(server, "_release_rights_artifact", lambda _slug: (None, {}))
    request = request_with_headers({}, path="/api/books/a-ghost-story")

    verdict = server._release_rights_verdict(request, country="IN")

    assert verdict.passed is False
    assert "ACCEPTED_DECISION_MISSING" in verdict.reasons


def test_runtime_rights_boundary_allows_only_exactly_accepted_launch_titles(monkeypatch):
    monkeypatch.setattr(
        server,
        "CONTROLLED_LIVE_BOOK_SLUGS",
        ("a-ghost-story", "the-tell-tale-heart", "radharani"),
    )

    for slug in server.CONTROLLED_LIVE_BOOK_SLUGS:
        verdict = server._release_rights_verdict(
            request_with_headers({}, path=f"/api/books/{slug}"), country="IN"
        )
        assert verdict.passed is True

    held = server._release_rights_verdict(
        request_with_headers({}, path="/api/books/yugalanguriya"), country="IN"
    )
    assert held.passed is False
    assert "ACCEPTED_DECISION_MISSING" in held.reasons

    for slug in server.CONTROLLED_LIVE_BOOK_SLUGS:
        unaccepted_country = server._release_rights_verdict(
            request_with_headers({}, path=f"/api/books/{slug}"), country="US"
        )
        assert unaccepted_country.passed is False
