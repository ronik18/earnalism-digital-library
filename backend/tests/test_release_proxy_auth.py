from __future__ import annotations

from datetime import datetime, timezone

from backend.release_proxy_auth import (
    COUNTRY_HEADER,
    PUBLIC_RELEASE_SCOPE,
    SCOPE_HEADER,
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    request_signature,
    verify_release_proxy_request,
)


SECRET = "release-proxy-test-secret-that-is-long-enough"
NOW = datetime(2026, 9, 22, 16, 0, tzinfo=timezone.utc)


def signed_headers(*, scope: str = PUBLIC_RELEASE_SCOPE, timestamp: int = 1_790_092_800, path: str = "/api/books", country: str = "IN"):
    return {
        SCOPE_HEADER: scope,
        COUNTRY_HEADER: country,
        TIMESTAMP_HEADER: str(timestamp),
        SIGNATURE_HEADER: request_signature(SECRET, "GET", path, scope, timestamp, country),
    }


def test_signed_public_release_request_authenticates_proxy_observed_country():
    verdict = verify_release_proxy_request(
        signed_headers(), method="GET", path="/api/books", secret=SECRET,
        now=NOW,
    )
    assert verdict.allowed is True
    assert verdict.code == "RELEASE_PROXY_AUTHENTICATED"
    assert verdict.country == "IN"


def test_missing_or_changed_country_fails_closed():
    missing = signed_headers()
    del missing[COUNTRY_HEADER]
    assert verify_release_proxy_request(
        missing, method="GET", path="/api/books", secret=SECRET, now=NOW,
    ).code == "RELEASE_PROXY_COUNTRY_INVALID"
    changed = signed_headers()
    changed[COUNTRY_HEADER] = "US"
    assert verify_release_proxy_request(
        changed, method="GET", path="/api/books", secret=SECRET, now=NOW,
    ).code == "RELEASE_PROXY_SIGNATURE_INVALID"


def test_direct_or_missing_scope_assertion_fails_closed():
    verdict = verify_release_proxy_request(
        {}, method="GET", path="/api/books", secret=SECRET, now=NOW,
    )
    assert (verdict.allowed, verdict.code) == (False, "RELEASE_PROXY_SCOPE_INVALID")


def test_invalid_scope_and_stale_assertions_are_rejected():
    scope = verify_release_proxy_request(
        signed_headers(scope="OTHER"), method="GET", path="/api/books", secret=SECRET,
        now=NOW,
    )
    stale = verify_release_proxy_request(
        signed_headers(timestamp=1), method="GET", path="/api/books", secret=SECRET,
        now=NOW,
    )
    assert (scope.allowed, scope.code) == (False, "RELEASE_PROXY_SCOPE_INVALID")
    assert (stale.allowed, stale.code) == (False, "RELEASE_PROXY_SIGNATURE_STALE")


def test_malformed_secret_path_and_method_never_open_reader_access():
    headers = signed_headers()
    assert verify_release_proxy_request(
        headers, method="GET", path="/api/books", secret="too-short", now=NOW,
    ).code == "RELEASE_PROXY_CONFIGURATION_REQUIRED"
    assert verify_release_proxy_request(
        headers, method="POST", path="/api/books", secret=SECRET, now=NOW,
    ).code == "RELEASE_PROXY_METHOD_INVALID"
    assert verify_release_proxy_request(
        headers, method="GET", path="https://api.theearnalism.com/api/books", secret=SECRET, now=NOW,
    ).code == "RELEASE_PROXY_PATH_INVALID"


def test_only_fixed_free_reader_session_posts_can_carry_a_signed_india_assertion():
    path = "/api/reading-pass/sessions/start"
    timestamp = int(NOW.timestamp())
    headers = {
        SCOPE_HEADER: PUBLIC_RELEASE_SCOPE,
        COUNTRY_HEADER: "IN",
        TIMESTAMP_HEADER: str(timestamp),
        SIGNATURE_HEADER: request_signature(SECRET, "POST", path, PUBLIC_RELEASE_SCOPE, timestamp, "IN"),
    }
    assert verify_release_proxy_request(headers, method="POST", path=path, secret=SECRET, now=NOW).allowed
    assert not verify_release_proxy_request(headers, method="POST", path="/api/reading-pass/sessions/transfer", secret=SECRET, now=NOW).allowed
    assert verify_release_proxy_request(headers, method="POST", path="/api/reading-pass/sessions/end", secret=SECRET, now=NOW).code == "RELEASE_PROXY_METHOD_INVALID"
