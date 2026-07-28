#!/usr/bin/env python3
"""Validate the finite Sprint 1 audiobook release conveyor contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONVEYOR = (
    ROOT
    / "internal/earnalism_intelligence/sprint1_audiobook_release_conveyor_v1.json"
)
EXPECTED_LIVE = {
    "book-2b9853ec52",
    "a-ghost-story",
    "sredni-vashtar",
    "the-open-window",
}


def load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("release conveyor must be a JSON object")
    return payload


def validate(payload: dict[str, Any]) -> dict[str, Any]:
    routes = payload.get("routes")
    if not isinstance(routes, dict) or not routes:
        raise RuntimeError("routes are missing")
    seen: dict[str, str] = {}
    route_counts: dict[str, int] = {}
    for route, raw_slugs in routes.items():
        if not isinstance(raw_slugs, list) or not all(
            isinstance(slug, str) and slug for slug in raw_slugs
        ):
            raise RuntimeError(f"invalid route list: {route}")
        route_counts[route] = len(raw_slugs)
        for slug in raw_slugs:
            if slug in seen:
                raise RuntimeError(
                    f"slug {slug} appears in both {seen[slug]} and {route}"
                )
            seen[slug] = route
    if len(seen) != 32:
        raise RuntimeError(f"expected 32 unique Sprint 1 slugs, found {len(seen)}")
    live = set(routes.get("production_live_verified") or [])
    if live != EXPECTED_LIVE:
        raise RuntimeError("production live route does not match canonical four")
    baseline = payload.get("current_verified_baseline") or {}
    if baseline.get("public_readers") != 32:
        raise RuntimeError("reader baseline must be 32")
    if baseline.get("public_audiobooks") != 4:
        raise RuntimeError("audiobook baseline must be four")
    if baseline.get("audio_hidden_titles") != 28:
        raise RuntimeError("audio-hidden baseline must be 28")
    caps = payload.get("finite_attempt_contract") or {}
    for key in (
        "new_synthetic_model_families_per_title_max",
        "targeted_repairs_per_title_max",
        "full_title_generations_after_representative_pass_max",
        "post_full_title_section_repairs_max",
    ):
        if caps.get(key) != 1:
            raise RuntimeError(f"{key} must be exactly one")
    if caps.get("failed_fingerprint_retries_max") != 0:
        raise RuntimeError("failed fingerprint retries must be zero")
    selected = payload.get("selected_next_action") or {}
    selected_slug = selected.get("slug")
    if selected_slug not in seen:
        raise RuntimeError("selected next slug is not in Sprint 1")
    if seen[selected_slug] == "production_live_verified":
        raise RuntimeError("selected next slug is already live")
    if not selected.get("next_exact_command"):
        raise RuntimeError("selected next action lacks an exact command")
    if selected.get("attempt_cap") not in (0, 1):
        raise RuntimeError("selected next action exceeds the one-attempt cap")
    attempts_consumed = selected.get("attempts_consumed", 0)
    if not isinstance(attempts_consumed, int) or not 0 <= attempts_consumed <= 1:
        raise RuntimeError("selected attempts consumed must be zero or one")
    active = payload.get("active_title") or {}
    if active:
        if active.get("slug") != selected_slug:
            raise RuntimeError("active title does not match selected next slug")
        if active.get("model_attempt_consumed") is False:
            if active.get("provider_calls_ran") is not False:
                raise RuntimeError(
                    "an unused model attempt cannot record provider calls"
                )
            if active.get("actual_provider_spend_usd") != 0.0:
                raise RuntimeError(
                    "an unused model attempt cannot record provider spend"
                )
    gates = payload.get("release_gates") or {}
    expected_gates = {
        "asr_manuscript_score_min": 9.7,
        "coverage_min": 0.98,
        "overall_listening_score_min": 8.9,
        "confidence_score_min": 0.9,
        "per_dimension_score_min": 8.9,
        "anti_robotic_texture_score_min": 9.2,
        "anti_choppy_join_score_min": 9.2,
    }
    for key, expected in expected_gates.items():
        if gates.get(key) != expected:
            raise RuntimeError(f"release gate changed: {key}")
    return {
        "status": "PASS",
        "unique_sprint1_slugs": len(seen),
        "production_live": len(live),
        "audio_hidden": len(seen) - len(live),
        "route_counts": route_counts,
        "selected_next_slug": selected_slug,
        "selected_attempts_consumed": attempts_consumed,
        "next_exact_command": selected["next_exact_command"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conveyor", type=Path, default=DEFAULT_CONVEYOR)
    args = parser.parse_args()
    try:
        result = validate(load(args.conveyor.resolve()))
    except (OSError, json.JSONDecodeError, RuntimeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
