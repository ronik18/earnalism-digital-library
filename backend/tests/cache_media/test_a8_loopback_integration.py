"""CI-only loopback checks for the current cache/media customer contract.

These checks intentionally exercise the running disposable UAT server.  They
replace retired reader-session fixtures that predate canonical Reading Pass
pages; cache/media unit and characterization coverage remains in this package.
"""

from __future__ import annotations

import os

import pytest
import requests


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
pytestmark = pytest.mark.skipif(
    not BASE_URL,
    reason="A8 loopback integration checks require the disposable UAT backend",
)


def _api(path: str) -> str:
    return f"{BASE_URL}/api{path}"


def test_a8_loopback_health_and_cache_status_use_ephemeral_services():
    health = requests.get(f"{BASE_URL}/healthz", timeout=10)
    assert health.status_code == 200

    login = requests.post(
        _api("/auth/login"),
        json={
            "email": os.environ["ADMIN_EMAIL"],
            "password": os.environ["ADMIN_PASSWORD"],
        },
        timeout=10,
    )
    assert login.status_code == 200
    status = requests.get(
        _api("/admin/cache/status"),
        headers={"Authorization": f"Bearer {login.json()['token']}"},
        timeout=10,
    )
    assert status.status_code == 200
    payload = status.json()
    assert payload["available"] is True
    assert payload["cache_v2"]["active_policy_count"] == 6


def test_a8_loopback_manifest_etag_and_reading_pass_authorization():
    manifest = requests.get(_api("/reader/book/dracula/manifest"), timeout=10)
    assert manifest.status_code == 200
    etag = manifest.headers["ETag"]
    assert manifest.json()["access"]["reading_pass"]["segments_ready"] is True
    not_modified = requests.get(
        _api("/reader/book/dracula/manifest"),
        headers={"If-None-Match": etag},
        timeout=10,
    )
    assert not_modified.status_code == 304

    pages = requests.get(_api("/reading-pass/books/dracula/manifest"), timeout=10)
    assert pages.status_code == 200
    page_manifest = pages.json()
    assert page_manifest["total_pages"] >= 4
    preview_limit = page_manifest["public_preview_pages"]
    preview = requests.get(_api(f"/reading-pass/books/dracula/pages/{preview_limit}"), timeout=10)
    assert preview.status_code == 200
    assert preview.json()["is_preview"] is True
    protected = requests.get(_api(f"/reading-pass/books/dracula/pages/{preview_limit + 1}"), timeout=10)
    assert protected.status_code == 401
    assert protected.json()["detail"]["code"] == "AUTH_REQUIRED"


def test_a8_loopback_audio_is_disabled_without_provider_url_leakage():
    response = requests.get(_api("/reading-pass/audiobooks/dracula/preview/audio"), timeout=10)
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "AUDIO_PREVIEW_DISABLED"
    assert "http" not in response.text.lower()
