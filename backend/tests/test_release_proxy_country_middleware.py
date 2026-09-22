from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import os

from fastapi import Response
from starlette.requests import Request

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "release-proxy-country-middleware-test-secret")

from backend import server
from backend.release_proxy_auth import COUNTRY_HEADER, SIGNATURE_HEADER, TIMESTAMP_HEADER, request_signature
from backend.rights_decision_gate import DecisionGateVerdict


SECRET = "release-proxy-test-secret-that-is-long-enough"


def request_with_headers(headers: dict[str, str], *, path: str = "/api/books") -> Request:
    return Request({
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [(key.encode("latin-1"), value.encode("latin-1")) for key, value in headers.items()],
        "query_string": b"",
        "server": ("testserver", 443),
        "scheme": "https",
    })


async def next_response(_request: Request) -> Response:
    return Response(status_code=204)


def test_public_reader_release_rejects_direct_api_requests(monkeypatch):
    monkeypatch.setattr(server, "PUBLIC_READER_EXPOSURE_ENABLED", True)
    monkeypatch.setenv("EARNALISM_RELEASE_PROXY_SECRET", SECRET)
    response = asyncio.run(server.enforce_public_release_country(request_with_headers({}), next_response))
    assert response.status_code == 451
    assert response.body == b'{"detail":{"code":"RELEASE_COUNTRY_NOT_ALLOWED"}}'


def test_public_reader_release_accepts_only_fresh_signed_india_proxy_request(monkeypatch):
    monkeypatch.setattr(server, "PUBLIC_READER_EXPOSURE_ENABLED", True)
    monkeypatch.setenv("EARNALISM_RELEASE_PROXY_SECRET", SECRET)
    monkeypatch.setattr(server, "_release_proxy_countries", lambda: frozenset({"IN"}))
    monkeypatch.setattr(server, "_release_rights_verdict", lambda _request: DecisionGateVerdict(True, ()))
    timestamp = int(datetime.now(timezone.utc).timestamp())
    headers = {
        COUNTRY_HEADER: "IN",
        TIMESTAMP_HEADER: str(timestamp),
        SIGNATURE_HEADER: request_signature(SECRET, "GET", "/api/books", "IN", timestamp),
    }
    response = asyncio.run(server.enforce_public_release_country(request_with_headers(headers), next_response))
    assert response.status_code == 204


def test_public_reader_release_denies_signed_request_without_accepted_rights(monkeypatch):
    monkeypatch.setattr(server, "PUBLIC_READER_EXPOSURE_ENABLED", True)
    monkeypatch.setenv("EARNALISM_RELEASE_PROXY_SECRET", SECRET)
    monkeypatch.setattr(server, "_release_proxy_countries", lambda: frozenset({"IN"}))
    monkeypatch.setattr(server, "_release_rights_verdict", lambda _request: DecisionGateVerdict(False, ("ACCEPTED_DECISION_MISSING",)))
    timestamp = int(datetime.now(timezone.utc).timestamp())
    headers = {
        COUNTRY_HEADER: "IN",
        TIMESTAMP_HEADER: str(timestamp),
        SIGNATURE_HEADER: request_signature(SECRET, "GET", "/api/books", "IN", timestamp),
    }

    response = asyncio.run(server.enforce_public_release_country(request_with_headers(headers), next_response))

    assert response.status_code == 451
    assert response.body == b'{"detail":{"code":"RELEASE_RIGHTS_DENIED"}}'


def test_runtime_rights_boundary_fails_closed_when_an_artifact_has_no_accepted_record(monkeypatch):
    monkeypatch.setattr(server, "_release_rights_artifact", lambda _slug: (None, {}))
    request = request_with_headers({COUNTRY_HEADER: "IN"}, path="/api/books/a-ghost-story")

    verdict = server._release_rights_verdict(request)

    assert verdict.passed is False
    assert "ACCEPTED_DECISION_MISSING" in verdict.reasons


def test_runtime_rights_boundary_allows_only_exactly_accepted_india_titles(monkeypatch):
    monkeypatch.setattr(
        server,
        "CONTROLLED_LIVE_BOOK_SLUGS",
        ("a-ghost-story", "the-tell-tale-heart", "radharani"),
    )

    for slug in server.CONTROLLED_LIVE_BOOK_SLUGS:
        verdict = server._release_rights_verdict(
            request_with_headers({COUNTRY_HEADER: "IN"}, path=f"/api/books/{slug}")
        )
        assert verdict.passed is True

    held = server._release_rights_verdict(
        request_with_headers({COUNTRY_HEADER: "IN"}, path="/api/books/yugalanguriya")
    )
    assert held.passed is False
    assert "ACCEPTED_DECISION_MISSING" in held.reasons
