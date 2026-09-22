"""Fail-closed country assertions for the bounded public-release proxy.

The Railway API never trusts a browser-provided country header. During an
India-only public Reader release, the same-origin Vercel function signs the
provider-derived country, request method, and path with a shared secret. The
helpers here are deliberately I/O-free so malformed, stale, or direct API
requests can be rejected before reader content is loaded.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import re
from typing import Mapping


COUNTRY_HEADER = "x-earnalism-release-country"
TIMESTAMP_HEADER = "x-earnalism-release-timestamp"
SIGNATURE_HEADER = "x-earnalism-release-signature"
MAX_SIGNATURE_AGE_SECONDS = 300
COUNTRY_CODE = re.compile(r"^[A-Z]{2}$")


@dataclass(frozen=True)
class ReleaseProxyVerdict:
    allowed: bool
    code: str


def canonical_request(method: str, path: str, country: str, timestamp: int) -> bytes:
    """Return the exact HMAC input shared by Vercel and Railway."""
    return f"{method.upper()}\\n{path}\\n{country}\\n{timestamp}".encode("utf-8")


def request_signature(secret: str, method: str, path: str, country: str, timestamp: int) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        canonical_request(method, path, country, timestamp),
        hashlib.sha256,
    ).hexdigest()


def verify_release_proxy_request(
    headers: Mapping[str, str],
    *,
    method: str,
    path: str,
    secret: str,
    allowed_countries: frozenset[str],
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
    country = normalized_headers.get(COUNTRY_HEADER, "").upper()
    if not COUNTRY_CODE.fullmatch(country) or country not in allowed_countries:
        return ReleaseProxyVerdict(False, "RELEASE_COUNTRY_NOT_ALLOWED")

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
    expected = request_signature(secret, method, path, country, timestamp)
    if not isinstance(received, str) or not hmac.compare_digest(received, expected):
        return ReleaseProxyVerdict(False, "RELEASE_PROXY_SIGNATURE_INVALID")
    return ReleaseProxyVerdict(True, "RELEASE_COUNTRY_ALLOWED")
