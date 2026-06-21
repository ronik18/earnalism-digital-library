#!/usr/bin/env python3
"""Validate configured Earnalism social profile URLs without platform API calls."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "social-brand-kit" / "latest"

SOCIAL_ENV_VARS = {
    "REACT_APP_INSTAGRAM_URL": {
        "platform": "Instagram",
        "domains": ("instagram.com", "www.instagram.com"),
    },
    "REACT_APP_YOUTUBE_URL": {
        "platform": "YouTube",
        "domains": ("youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"),
    },
    "REACT_APP_FACEBOOK_URL": {
        "platform": "Facebook",
        "domains": ("facebook.com", "www.facebook.com", "m.facebook.com"),
    },
    "REACT_APP_LINKEDIN_URL": {
        "platform": "LinkedIn",
        "domains": ("linkedin.com", "www.linkedin.com"),
    },
    "REACT_APP_X_URL": {
        "platform": "X",
        "domains": ("x.com", "www.x.com", "twitter.com", "www.twitter.com"),
    },
    "REACT_APP_WHATSAPP_CHANNEL_URL": {
        "platform": "WhatsApp Channel",
        "domains": ("whatsapp.com", "www.whatsapp.com", "chat.whatsapp.com"),
    },
    "REACT_APP_TELEGRAM_CHANNEL_URL": {
        "platform": "Telegram",
        "domains": ("t.me", "telegram.me", "www.t.me", "www.telegram.me"),
    },
}

PLACEHOLDER_TERMS = (
    "example.com",
    "placeholder",
    "your-handle",
    "yourhandle",
    "username",
    "{",
    "}",
    "<",
    ">",
)

PRIVATE_PATH_TERMS = (
    "/admin",
    "/login",
    "/signin",
    "/signup",
    "/account",
    "/dashboard",
)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def validate_social_url(env_key: str, value: str | None) -> dict[str, object]:
    spec = SOCIAL_ENV_VARS[env_key]
    raw = "" if value is None else str(value).strip()
    result: dict[str, object] = {
        "env_key": env_key,
        "platform": spec["platform"],
        "url": raw,
        "status": "INVALID",
        "issues": [],
    }
    issues: list[str] = []

    if not raw:
        issues.append("URL is empty or not configured.")
    elif raw == "#":
        issues.append("URL must not be '#'.")
    elif raw.lower().startswith("javascript:"):
        issues.append("URL must not use javascript:.")
    else:
        parsed = urlparse(raw)
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").lower()
        if parsed.scheme not in {"http", "https"}:
            issues.append("URL must use http or https.")
        if not host:
            issues.append("URL is missing a host.")
        if host in {"localhost", "127.0.0.1"} or host.endswith(".local"):
            issues.append("URL must not point to a local/private host.")
        if host not in spec["domains"]:
            issues.append(f"URL host must match {spec['platform']} domains.")
        if any(term in raw.lower() for term in PLACEHOLDER_TERMS):
            issues.append("URL appears to contain placeholder text.")
        if any(term in path for term in PRIVATE_PATH_TERMS):
            issues.append("URL must not point to private/admin/auth pages.")

    if not issues:
        result["status"] = "VALID"
    elif not raw:
        result["status"] = "MISSING_OPERATOR_REQUIRED"
    result["issues"] = issues
    return result


def validate_environment(environ: dict[str, str] | None = None) -> dict[str, object]:
    source = os.environ if environ is None else environ
    checks = [validate_social_url(env_key, source.get(env_key)) for env_key in SOCIAL_ENV_VARS]
    valid_count = sum(1 for check in checks if check["status"] == "VALID")
    invalid_count = sum(1 for check in checks if check["status"] == "INVALID")
    missing_count = sum(1 for check in checks if check["status"] == "MISSING_OPERATOR_REQUIRED")
    status = "PASS" if valid_count and invalid_count == 0 else "OPERATOR_REQUIRED"
    if invalid_count:
        status = "FAIL"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "missing_count": missing_count,
        "network_calls": False,
        "platform_api_calls": False,
        "checks": checks,
    }


def validation_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Social Links Validation",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This validation checks syntax and platform domains only. It does not call social platform APIs and does not publish anything.",
        "",
        "| Env var | Platform | Status | Issue |",
        "| --- | --- | --- | --- |",
    ]
    for check in payload["checks"]:
        issues = "; ".join(check["issues"]) if check["issues"] else "None"
        lines.append(f"| `{check['env_key']}` | {check['platform']} | {check['status']} | {issues} |")
    lines.extend(
        [
            "",
            "## Operator Next Step",
            "",
            "Create the real social profiles manually, then set only the verified public profile URLs in the matching frontend environment variables. Footer icons must remain hidden until real http/https URLs are configured.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    payload = validate_environment()
    write_json(OUTPUT_DIR / "social_links_validation.json", payload)
    write_text(OUTPUT_DIR / "social_links_validation.md", validation_markdown(payload))

    print(f"Social link validation status: {payload['status']}")
    print(f"Valid: {payload['valid_count']} | Missing: {payload['missing_count']} | Invalid: {payload['invalid_count']}")
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
