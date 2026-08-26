#!/usr/bin/env python3
"""GET/HEAD-only production API canary for Railway native GitHub deployments."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://api.theearnalism.com"
CANARY_ORIGIN = "https://theearnalism.com"
RAW_MEDIA_PATTERN = re.compile(r"https?://[^\"']+\.(?:mp3|m4a|wav|ogg|aac)|/(?:audio|media)/", re.IGNORECASE)


def request(base_url: str, path: str, *, method: str = "GET", headers: dict[str, str] | None = None) -> dict[str, Any]:
    if method not in {"GET", "HEAD"}:
        raise ValueError("canary only permits GET and HEAD")
    req_headers = {"Accept": "application/json", "User-Agent": "EarnalismRailwayDeploymentCanary/1.0"}
    req_headers.update(headers or {})
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    try:
        with urlopen(Request(url, headers=req_headers, method=method), timeout=15) as response:  # noqa: S310 - fixed public origin.
            body = b"" if method == "HEAD" else response.read(256_000)
            return {"path": path, "method": method, "status": response.status, "headers": dict(response.headers.items()), "body": body.decode("utf-8", errors="replace"), "error": ""}
    except HTTPError as error:
        body = b"" if method == "HEAD" else error.read(256_000)
        return {"path": path, "method": method, "status": error.code, "headers": dict(error.headers.items()), "body": body.decode("utf-8", errors="replace"), "error": ""}
    except URLError as error:
        return {"path": path, "method": method, "status": 0, "headers": {}, "body": "", "error": str(error)}


def json_body(result: dict[str, Any]) -> Any:
    try:
        return json.loads(result["body"])
    except json.JSONDecodeError:
        return None


def header(result: dict[str, Any], name: str) -> str:
    return next((str(value) for key, value in result["headers"].items() if key.lower() == name.lower()), "")


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "detail": detail}


def run(base_url: str, approved_audio_slug: str) -> dict[str, Any]:
    health = request(base_url, "/healthz")
    config = request(base_url, "/api/reading-pass/config", headers={"Origin": CANARY_ORIGIN})
    catalog = request(base_url, "/api/books?q=dracula")
    approved_catalog = request(base_url, f"/api/books/{approved_audio_slug}")
    manifest = request(base_url, "/api/reader/book/dracula/manifest")
    dracula_audio = request(base_url, "/api/reader/book/dracula/audiobook", headers={"Range": "bytes=0-1"})
    approved_audio = request(base_url, f"/api/reader/book/{approved_audio_slug}/audiobook", headers={"Range": "bytes=0-1"})
    health_body = json_body(health)
    config_body = json_body(config) or {}
    catalog_body = json_body(catalog) or []
    approved_catalog_body = json_body(approved_catalog) or {}
    manifest_body = json_body(manifest) or {}
    if not isinstance(health_body, dict):
        health_body = {}
    if not isinstance(config_body, dict):
        config_body = {}
    if not isinstance(catalog_body, list):
        catalog_body = []
    if not isinstance(manifest_body, dict):
        manifest_body = {}
    if not isinstance(approved_catalog_body, dict):
        approved_catalog_body = {}
    dracula = next((book for book in catalog_body if isinstance(book, dict) and book.get("slug") == "dracula"), {})
    approved_audio_book = approved_catalog_body if approved_catalog_body.get("slug") == approved_audio_slug else {}
    serialized_catalog = json.dumps(catalog_body, ensure_ascii=False)
    serialized_manifest = json.dumps(manifest_body, ensure_ascii=False)
    checks = [
        check("health_200", health["status"] == 200 and health_body.get("status") == "ok", f"status={health['status']}"),
        check("health_no_store", "no-store" in header(health, "Cache-Control").lower(), header(health, "Cache-Control")),
        check("reading_pass_contract", config["status"] == 200 and config_body.get("public_text_pages") == 3 and config_body.get("public_audio_seconds") == 0, f"status={config['status']}; pages={config_body.get('public_text_pages')}; audio={config_body.get('public_audio_seconds')}"),
        check("cors_origin", header(config, "Access-Control-Allow-Origin") == CANARY_ORIGIN, header(config, "Access-Control-Allow-Origin")),
        check("public_catalog", catalog["status"] == 200 and bool(catalog_body), f"status={catalog['status']}"),
        check("no_raw_media_url", not RAW_MEDIA_PATTERN.search(serialized_catalog) and not RAW_MEDIA_PATTERN.search(serialized_manifest), "catalog and manifest scanned"),
        check("dracula_audio_disabled", dracula.get("audio_enabled") is False and dracula.get("audiobook_enabled") is False and not dracula.get("audio_url"), json.dumps({key: dracula.get(key) for key in ("audio_enabled", "audiobook_enabled", "audio_url")})),
        check("controlled_manifest", manifest["status"] == 200 and manifest_body.get("audio", {}).get("enabled") is False and manifest_body.get("audio", {}).get("assets") == {}, f"status={manifest['status']}"),
        check("dracula_audio_range_denied", dracula_audio["status"] == 404 and not dracula_audio["body"].startswith("ID3"), f"status={dracula_audio['status']}; bytes={len(dracula_audio['body'])}"),
        check("approved_audio_locked_metadata", approved_catalog["status"] == 200 and approved_audio_book.get("audio_enabled") is True and approved_audio_book.get("audiobook_enabled") is True and not approved_audio_book.get("audio_url"), json.dumps({key: approved_audio_book.get(key) for key in ("audio_enabled", "audiobook_enabled", "audio_url")})),
        check("approved_audio_range_denied", approved_audio["status"] in {401, 403} and not approved_audio["body"].startswith("ID3"), f"status={approved_audio['status']}; bytes={len(approved_audio['body'])}"),
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "methods_used": ["GET"],
        "deployment_sha": os.environ.get("RAILWAY_DEPLOYMENT_SHA", ""),
        "response_edge": header(health, "X-Railway-Edge"),
        "response_region_debug": header(health, "X-Hikari-Trace"),
        "checks": checks,
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        "production_mutation_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("PRODUCTION_API_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--approved-audio-slug", default=os.environ.get("RAILWAY_CANARY_APPROVED_AUDIO_SLUG", "the-art-of-money-getting"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.base_url, args.approved_audio_slug)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": report["checks"]}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
