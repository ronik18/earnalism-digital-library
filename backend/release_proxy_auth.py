"""Fail-closed proxy assertions for the bounded public-release proxy.

The Railway API never trusts a browser-provided assertion. The same-origin
Vercel function signs a fixed release scope, request method, path, and its
observed visitor country with a shared secret. The Railway rights decision
must use that authenticated country, never a browser-supplied country.
The helpers here are deliberately I/O-free so malformed, stale, or direct API
requests can be rejected before reader content is loaded.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
from typing import Mapping


SCOPE_HEADER = "x-earnalism-release-scope"
TIMESTAMP_HEADER = "x-earnalism-release-timestamp"
SIGNATURE_HEADER = "x-earnalism-release-signature"
COUNTRY_HEADER = "x-earnalism-release-country"
MAX_SIGNATURE_AGE_SECONDS = 300
PUBLIC_RELEASE_SCOPE = "PUBLIC"


@dataclass(frozen=True)
class ReleaseProxyVerdict:
    allowed: bool
    code: str
    country: str = ""


def canonical_request(method: str, path: str, scope: str, timestamp: int, country: str) -> bytes:
    """Return the exact HMAC input shared by Vercel and Railway."""
    return f"{method.upper()}\\n{path}\\n{scope}\\n{timestamp}\\n{country}".encode("utf-8")


def request_signature(secret: str, method: str, path: str, scope: str, timestamp: int, country: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        canonical_request(method, path, scope, timestamp, country),
        hashlib.sha256,
    ).hexdigest()


def verify_release_proxy_request(
    headers: Mapping[str, str],
    *,
    method: str,
    path: str,
    secret: str,
    now: datetime | None = None,
) -> ReleaseProxyVerdict:
    """Verify a bounded Vercel assertion without accepting client input."""
    if not isinstance(secret, str) or len(secret) < 32:
        return ReleaseProxyVerdict(False, "RELEASE_PROXY_CONFIGURATION_REQUIRED")
    if not isinstance(path, str) or not path.startswith("/api/"):
        return ReleaseProxyVerdict(False, "RELEASE_PROXY_PATH_INVALID")
    if not isinstance(method, str) or method.upper() not in {"GET", "HEAD"}:
        return ReleaseProxyVerdict(False, "RELEASE_PROXY_METHOD_INVALID")

    normalized_headers = {str(key).lower(): str(value) for key, value in headers.items()}
    scope = normalized_headers.get(SCOPE_HEADER, "")
    if scope != PUBLIC_RELEASE_SCOPE:
        return ReleaseProxyVerdict(False, "RELEASE_PROXY_SCOPE_INVALID")
    country = normalized_headers.get(COUNTRY_HEADER, "")
    if len(country) != 2 or not country.isascii() or not country.isalpha() or country != country.upper():
        return ReleaseProxyVerdict(False, "RELEASE_PROXY_COUNTRY_INVALID")

    raw_timestamp = normalized_headers.get(TIMESTAMP_HEADER, "")
    try:
        timestamp = int(raw_timestamp)
    except (TypeError, ValueError):
        return ReleaseProxyVerdict(False, "RELEASE_PROXY_TIMESTAMP_INVALID")
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        return ReleaseProxyVerdict(False, "RELEASE_PROXY_CLOCK_INVALID")
    if abs(int(instant.timestamp()) - timestamp) > MAX_SIGNATURE_AGE_SECONDS:
        return ReleaseProxyVerdict(False, "RELEASE_PROXY_SIGNATURE_STALE")

    received = normalized_headers.get(SIGNATURE_HEADER, "")
    expected = request_signature(secret, method, path, scope, timestamp, country)
    if not isinstance(received, str) or not hmac.compare_digest(received, expected):
        return ReleaseProxyVerdict(False, "RELEASE_PROXY_SIGNATURE_INVALID")
    return ReleaseProxyVerdict(True, "RELEASE_PROXY_AUTHENTICATED", country)
