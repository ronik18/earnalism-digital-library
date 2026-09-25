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


def test_historical_free_session_proxy_grant_is_disabled_after_commercial_cutover(monkeypatch):
    monkeypatch.setattr(server, "ENVIRONMENT", "production")
    monkeypatch.setattr(server, "PUBLIC_READER_EXPOSURE_ENABLED", True)
    monkeypatch.setattr(server, "TEXT_ACCESS_MODE", "COMMERCIAL_ENTITLEMENT")
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
    for slug in (
        "a-ghost-story", "the-tell-tale-heart", "radharani",
        "a-white-heron", "the-gift-of-the-magi", "the-canterville-ghost",
        "yugalanguriya", "dracula", "unlisted-book",
    ):
        assert server._free_india_reader_verdict(request, slug) is False
    assert server._free_india_reader_verdict(request_with_headers({}, path=path, method="POST"), "a-ghost-story") is False
    assert asyncio.run(server.enforce_public_release_country(request_with_headers({}, path=path, method="POST"), next_response)).status_code == 451

    us_headers = {**headers, COUNTRY_HEADER: "US"}
    us_headers[SIGNATURE_HEADER] = request_signature(SECRET, "POST", path, PUBLIC_RELEASE_SCOPE, timestamp, "US")
    us_request = request_with_headers(us_headers, path=path, method="POST")
    assert server._free_india_reader_verdict(us_request, "a-ghost-story") is False
    assert asyncio.run(server.enforce_public_release_country(us_request, next_response)).status_code == 451


def test_commercial_mode_requires_commerce_and_separate_pass_rights(monkeypatch):
    monkeypatch.setattr(server, "PUBLIC_READER_EXPOSURE_ENABLED", True)
    monkeypatch.setattr(
        server,
        "CONTROLLED_LIVE_BOOK_SLUGS",
        tuple(server.CONTROLLED_LIVE_BOOK_SLUGS) + ("a-white-heron",),
    )
    monkeypatch.setattr(server, "ENVIRONMENT", "development")
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
    assert server._free_india_reader_verdict(request, "a-white-heron") is False
    monkeypatch.setattr(server, "PUBLIC_PAID_COMMERCE_ENABLED", False)
    assert server._commercial_india_reader_verdict(request, "a-white-heron") is False
    monkeypatch.setattr(server, "PUBLIC_PAID_COMMERCE_ENABLED", True)
    monkeypatch.setattr(server, "load_production_registry", lambda: ([], []))
    monkeypatch.setattr(server, "evaluate_runtime_path", lambda *args, **kwargs: DecisionGateVerdict(False, ("ACCEPTED_DECISION_MISSING",)))
    assert server._commercial_india_reader_verdict(request, "a-white-heron") is False
    approved_actions = []
    def approved_runtime_path(action, **_kwargs):
        approved_actions.append(action)
        return DecisionGateVerdict(True, ())
    monkeypatch.setattr(server, "evaluate_runtime_path", approved_runtime_path)
    assert server._commercial_india_reader_verdict(request, "a-white-heron") is True
    assert approved_actions == ["reading_pass_session_start", "reading_pass_page", "reading_pass_lease_renewal"]
    assert server._commercial_india_reader_verdict(request, "yugalanguriya") is False
    assert server._commercial_india_reader_verdict(request_with_headers({}, path=path, method="POST"), "a-white-heron") is False


def test_per_title_modes_require_commercial_pass_for_all_six_and_keep_held_titles_denied(monkeypatch):
    assert server._title_text_access_mode("a-ghost-story") == "COMMERCIAL_ENTITLEMENT"
    assert server._title_text_access_mode("the-tell-tale-heart") == "COMMERCIAL_ENTITLEMENT"
    assert server._title_text_access_mode("radharani") == "COMMERCIAL_ENTITLEMENT"
    assert server._title_text_access_mode("the-gift-of-the-magi") == "COMMERCIAL_ENTITLEMENT"
    assert server._title_text_access_mode("yugalanguriya") is None

    monkeypatch.setattr(server, "PUBLIC_PAID_COMMERCE_ENABLED", False)
    assert server._commercial_india_reader_verdict(
        request_with_headers({}, path="/api/reading-pass/sessions/start", method="POST"),
        "the-gift-of-the-magi",
    ) is False


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
