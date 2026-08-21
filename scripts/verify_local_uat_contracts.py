#!/usr/bin/env python3
"""Fail-closed direct contract checks for the launched local System UAT stack."""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen


FRONTEND = os.environ.get("UAT_BASE_URL", "").rstrip("/")
API = os.environ.get("UAT_API_BASE_URL", "").rstrip("/")


def ensure_local(value: str, suffix: str = "") -> None:
    if not value.startswith("http://127.0.0.1:") or (suffix and not value.endswith(suffix)):
        raise SystemExit("local UAT URL is required; production fallback is disabled")


def get(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], object]:
    try:
        with urlopen(Request(url, headers=headers or {}), timeout=20) as response:
            body = response.read().decode("utf-8")
            try:
                payload = json.loads(body) if body else None
            except json.JSONDecodeError:
                payload = body
            return response.status, dict(response.headers.items()), payload
    except HTTPError as error:
        body = error.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = body
        return error.code, dict(error.headers.items()), parsed


def require_status(url: str, expected: int) -> object:
    status, _headers, payload = get(url)
    if status != expected:
        raise SystemExit(f"{url} expected HTTP {expected}, got {status}")
    return payload


def main() -> None:
    ensure_local(FRONTEND)
    ensure_local(API, "/api")
    require_status(f"{FRONTEND}/", 200)
    require_status(f"{FRONTEND}/library", 200)
    for route, expected in (("/product/patterned-wrap-dress", 410), ("/not-a-real-route", 404)):
        status, headers, _payload = get(f"{FRONTEND}{route}")
        if status != expected or headers.get("X-Robots-Tag") != "noindex, nofollow, noarchive":
            raise SystemExit(f"route contract failed for {route}: status={status}, robots={headers.get('X-Robots-Tag')!r}")

    require_status(f"{API}/books", 200)
    cors_status, cors_headers, _cors_payload = get(
        f"{API}/payments/packs",
        {"Origin": FRONTEND},
    )
    cors_allow_origin = next(
        (value for name, value in cors_headers.items() if name.lower() == "access-control-allow-origin"),
        None,
    )
    if cors_status != 200 or cors_allow_origin != FRONTEND:
        raise SystemExit(
            "local UAT API did not allow the selected frontend origin: "
            f"status={cors_status}, allow-origin={cors_allow_origin!r}"
        )
    book = require_status(f"{API}/books/dracula", 200)
    expected_audio = {
        "audio_enabled": False,
        "audiobook_enabled": False,
        "audiobook": None,
        "audiobook_assets": {},
        "audio_url": "",
    }
    if not isinstance(book, dict) or {key: book.get(key) for key in expected_audio} != expected_audio:
        raise SystemExit("Dracula audio release truth was not fail-closed")
    manifest = require_status(f"{API}/reader/book/dracula/manifest", 200)
    pages = (manifest or {}).get("canonical_pages", {})
    policy = pages.get("preview_policy", {})
    if (pages.get("schema_version"), policy.get("unit"), policy.get("public_limit"), policy.get("enforced_by"), policy.get("ready")) != (
        "canonical-page-preview-v1", "canonical_page", 3, "server", True
    ):
        raise SystemExit("canonical page preview policy is not active")
    if any("content" in row for row in pages.get("pages", [])):
        raise SystemExit("public page manifest exposed protected page content")
    public_pages = [require_status(f"{API}/reader/book/dracula/pages/{index}", 200) for index in (1, 2, 3)]
    protected_status, _headers, protected = get(f"{API}/reader/book/dracula/pages/4")
    if protected_status != 401 or (protected or {}).get("detail", {}).get("code") != "AUTH_REQUIRED":
        raise SystemExit("anonymous protected canonical page did not require authentication")
    require_status(f"{API}/reader/book/dracula/pages/999999", 404)
    require_status(f"{API}/reader/book/dracula/audiobook", 404)
    protected_content = str(public_pages[0].get("content", "")) if isinstance(public_pages[0], dict) else ""
    if not protected_content or protected_content in json.dumps(manifest, sort_keys=True):
        raise SystemExit("public manifest leaked canonical page content")
    print("local-contracts=PASS")
    print("production-network-requests=0")


if __name__ == "__main__":
    main()
