from __future__ import annotations

from datetime import datetime, timezone

from backend.release_proxy_auth import (
    COUNTRY_HEADER,
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    request_signature,
    verify_release_proxy_request,
)


SECRET = "release-proxy-test-secret-that-is-long-enough"
NOW = datetime(2026, 9, 22, 16, 0, tzinfo=timezone.utc)


def signed_headers(*, country: str = "IN", timestamp: int = 1_790_092_800, path: str = "/api/books"):
    return {
        COUNTRY_HEADER: country,
        TIMESTAMP_HEADER: str(timestamp),
        SIGNATURE_HEADER: request_signature(SECRET, "GET", path, country, timestamp),
    }


def test_signed_india_public_release_request_is_accepted():
    verdict = verify_release_proxy_request(
        signed_headers(), method="GET", path="/api/books", secret=SECRET,
        allowed_countries=frozenset({"IN"}), now=NOW,
    )
    assert verdict.allowed is True
    assert verdict.code == "RELEASE_COUNTRY_ALLOWED"


def test_direct_or_spoofed_country_header_fails_closed():
    verdict = verify_release_proxy_request(
        {COUNTRY_HEADER: "IN"}, method="GET", path="/api/books", secret=SECRET,
        allowed_countries=frozenset({"IN"}), now=NOW,
    )
    assert verdict.allowed is False
    assert verdict.code == "RELEASE_PROXY_TIMESTAMP_INVALID"


def test_non_india_and_stale_assertions_are_rejected():
    country = verify_release_proxy_request(
        signed_headers(country="US"), method="GET", path="/api/books", secret=SECRET,
        allowed_countries=frozenset({"IN"}), now=NOW,
    )
    stale = verify_release_proxy_request(
        signed_headers(timestamp=1), method="GET", path="/api/books", secret=SECRET,
        allowed_countries=frozenset({"IN"}), now=NOW,
    )
    assert (country.allowed, country.code) == (False, "RELEASE_COUNTRY_NOT_ALLOWED")
    assert (stale.allowed, stale.code) == (False, "RELEASE_PROXY_SIGNATURE_STALE")


def test_malformed_secret_path_and_method_never_open_reader_access():
    headers = signed_headers()
    assert verify_release_proxy_request(
        headers, method="GET", path="/api/books", secret="too-short", allowed_countries=frozenset({"IN"}), now=NOW,
    ).code == "RELEASE_PROXY_CONFIGURATION_REQUIRED"
    assert verify_release_proxy_request(
        headers, method="POST", path="/api/books", secret=SECRET, allowed_countries=frozenset({"IN"}), now=NOW,
    ).code == "RELEASE_PROXY_METHOD_INVALID"
    assert verify_release_proxy_request(
        headers, method="GET", path="https://api.theearnalism.com/api/books", secret=SECRET, allowed_countries=frozenset({"IN"}), now=NOW,
    ).code == "RELEASE_PROXY_PATH_INVALID"
