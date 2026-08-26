#!/usr/bin/env python3
"""Classify GitHub deployment-status provenance without trusting a bot name."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


RAILWAY_CONFIRMED = "RAILWAY_CONFIRMED"
NON_RAILWAY_DEPLOYMENT = "NON_RAILWAY_DEPLOYMENT"
PROVIDER_UNCONFIRMED = "PROVIDER_UNCONFIRMED"
# Verified from Railway deployment 43630a5c and GitHub deployment 6104421176
# on 2026-08-26. This is intentionally a documented event marker, not a guess.
RAILWAY_APP_MARKER = "railway-app[bot]"


def _normalise(value: object) -> str:
    return str(value or "").strip().lower()


def classify_provider(event: dict[str, Any], railway_provider_marker: str = "") -> str:
    """Return only a provenance classification, never an assumed Railway identity."""
    fields = "\n".join(
        _normalise(event.get(key))
        for key in ("sender", "creator", "task", "target_url", "log_url", "environment_url", "description")
    )
    marker = _normalise(railway_provider_marker)
    if marker and marker in fields:
        return RAILWAY_CONFIRMED
    if RAILWAY_APP_MARKER in fields:
        return RAILWAY_CONFIRMED
    # Historical production events use Vercel bot and Vercel deployment URLs. This is
    # intentionally a provider exclusion rather than a Railway bot-name assumption.
    if "vercel" in fields:
        return NON_RAILWAY_DEPLOYMENT
    return PROVIDER_UNCONFIRMED


def is_production_environment(value: object) -> bool:
    """Accept GitHub's plain and Railway-scoped production environment names."""
    normalized = _normalise(value)
    return normalized == "production" or normalized.endswith("/ production")


def evaluate_event(event: dict[str, Any], railway_provider_marker: str = "") -> dict[str, Any]:
    environment = _normalise(event.get("environment"))
    state = _normalise(event.get("state"))
    deployment_sha = str(event.get("deployment_sha") or "")
    checked_out_sha = str(event.get("checked_out_sha") or "")
    sha_matches_checkout = bool(deployment_sha) and deployment_sha == checked_out_sha
    reachable_from_main = bool(event.get("reachable_from_main"))
    provider_classification = classify_provider(event, railway_provider_marker)
    eligible = is_production_environment(environment) and state == "success" and sha_matches_checkout and reachable_from_main
    return {
        "provider_classification": provider_classification,
        "event_eligibility": "ELIGIBLE" if eligible else "INELIGIBLE",
        "deployment_sha": deployment_sha,
        "checked_out_sha": checked_out_sha,
        "checked_out_sha_matches_deployment_sha": sha_matches_checkout,
        "deployment_sha_reachable_from_origin_main": reachable_from_main,
        "run_backend_canary": eligible and provider_classification in {RAILWAY_CONFIRMED, PROVIDER_UNCONFIRMED},
        "railway_deployment_proof": eligible and provider_classification == RAILWAY_CONFIRMED,
        "provenance": {
            key: event.get(key, "")
            for key in (
                "deployment_id",
                "deployment_sha",
                "deployment_ref",
                "environment",
                "state",
                "status_id",
                "target_url",
                "log_url",
                "environment_url",
                "sender",
                "creator",
                "task",
                "description",
                "checked_out_sha",
            )
        },
        "railway_provider_marker_configured": bool(railway_provider_marker),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--railway-provider-marker", default="")
    args = parser.parse_args()
    event = json.loads(args.event_json.read_text(encoding="utf-8"))
    result = evaluate_event(event, args.railway_provider_marker)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as stream:
            stream.write(f"run_backend_canary={'true' if result['run_backend_canary'] else 'false'}\n")
            stream.write(f"provider_classification={result['provider_classification']}\n")
            stream.write(f"railway_deployment_proof={'true' if result['railway_deployment_proof'] else 'false'}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
