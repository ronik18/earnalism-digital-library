#!/usr/bin/env python3
"""Fail-closed validator for the checked-in CUSTOMER_READY autonomy envelope.

The envelope intentionally uses a small YAML subset.  Keeping this parser in
the repository avoids giving a release-control validator an undeclared runtime
dependency.  Unsupported YAML is rejected rather than interpreted loosely.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENVELOPE = ROOT / "ops/autonomy/customer-ready-autonomy-envelope.yaml"


class EnvelopeSyntaxError(ValueError):
    pass


def _scalar(raw: str) -> Any:
    value = raw.strip()
    if value in {"true", "false"}:
        return value == "true"
    if value in {"null", "~"}:
        return None
    if re.fullmatch(r"-?(?:0|[1-9][0-9]*)", value):
        return int(value)
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if any(marker in value for marker in ("[", "]", "{", "}", "&", "*")):
        raise EnvelopeSyntaxError(f"unsupported YAML scalar: {value!r}")
    return value


def parse_restricted_yaml(path: Path) -> dict[str, Any]:
    """Parse mappings/lists/scalars used by the governance envelope only."""
    rows = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if "\t" in raw:
            raise EnvelopeSyntaxError(f"line {number}: tabs are not allowed")
        indent = len(raw) - len(raw.lstrip(" "))
        rows.append((number, indent, raw.strip()))
    if not rows:
        raise EnvelopeSyntaxError("empty document")

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(rows) or rows[index][1] != indent:
            raise EnvelopeSyntaxError("invalid indentation")
        is_list = rows[index][2].startswith("- ")
        result: Any = [] if is_list else {}
        while index < len(rows) and rows[index][1] == indent:
            line_no, _, text = rows[index]
            if text.startswith("- "):
                if not is_list:
                    raise EnvelopeSyntaxError(f"line {line_no}: list item in mapping")
                item = text[2:].strip()
                if not item:
                    if index + 1 >= len(rows) or rows[index + 1][1] <= indent:
                        raise EnvelopeSyntaxError(f"line {line_no}: empty list item")
                    child, index = parse_block(index + 1, rows[index + 1][1])
                    result.append(child)
                    continue
                if ":" in item:
                    key, raw_value = item.split(":", 1)
                    entry: dict[str, Any] = {key.strip(): _scalar(raw_value)} if raw_value.strip() else {key.strip(): None}
                    index += 1
                    if raw_value.strip() == "" and index < len(rows) and rows[index][1] > indent:
                        entry[key.strip()], index = parse_block(index, rows[index][1])
                    result.append(entry)
                    continue
                result.append(_scalar(item))
                index += 1
                continue
            if is_list or ":" not in text:
                raise EnvelopeSyntaxError(f"line {line_no}: unsupported YAML structure")
            key, raw_value = text.split(":", 1)
            key = key.strip()
            if not key or key in result:
                raise EnvelopeSyntaxError(f"line {line_no}: invalid or duplicate key")
            if raw_value.strip():
                result[key] = _scalar(raw_value)
                index += 1
            else:
                index += 1
                if index >= len(rows) or rows[index][1] <= indent:
                    raise EnvelopeSyntaxError(f"line {line_no}: mapping key needs a child")
                result[key], index = parse_block(index, rows[index][1])
        return result, index

    document, end = parse_block(0, rows[0][1])
    if end != len(rows) or not isinstance(document, dict):
        raise EnvelopeSyntaxError("invalid root document")
    return document


def _path(value: Any, *parts: str) -> Any:
    current = value
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _walk(value: Any, trail: tuple[str, ...] = ()):  # noqa: ANN001
    if isinstance(value, dict):
        for key, nested in value.items():
            next_trail = (*trail, str(key))
            yield next_trail, nested
            yield from _walk(nested, next_trail)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _walk(nested, (*trail, str(index)))


def _require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def validate(document: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    allowed_root = {"apiVersion", "kind", "metadata", "spec"}
    _require(errors, set(document) <= allowed_root, "unknown top-level envelope field")
    _require(errors, document.get("apiVersion") == "earnalism.dev/v1", "unexpected apiVersion")
    _require(errors, document.get("kind") == "AutonomyEnvelope", "unexpected kind")
    spec = document.get("spec")
    _require(errors, isinstance(spec, dict), "spec must be a mapping")
    if not isinstance(spec, dict):
        return errors

    preview = _path(spec, "product_truth", "audio_preview")
    _require(errors, isinstance(preview, dict), "missing spec.product_truth.audio_preview")
    if isinstance(preview, dict):
        seconds = preview.get("seconds")
        _require(errors, type(seconds) is int, "audio_preview.seconds must be an integer")
        _require(errors, seconds == 0, "audio_preview.seconds must equal zero")
        _require(errors, preview.get("only_when_audio_release_approved") is True, "audio_preview approval gate must be true")

    allowed_permissions = {"repository", "continuous_integration", "railway", "vercel", "production_observability", "production_data"}
    permissions = spec.get("permissions")
    _require(errors, isinstance(permissions, dict), "missing permissions mapping")
    if isinstance(permissions, dict):
        _require(errors, set(permissions) <= allowed_permissions, "unknown top-level permissions")

    _require(errors, _path(spec, "budget", "incremental_infrastructure_spend_usd") == 0, "incremental spend must be zero")
    _require(errors, _path(spec, "budget", "new_paid_plans_allowed") is False, "new paid plans are forbidden")
    _require(errors, _path(spec, "autonomy", "direct_push_to_main_allowed") is False, "direct main push is forbidden")
    _require(errors, _path(spec, "autonomy", "administrator_bypass_allowed") is False, "administrator bypass is forbidden")
    _require(errors, _path(spec, "autonomy", "automatic_rollback_required_on_threshold") is True, "automatic rollback is required")
    _require(errors, _path(spec, "evidence", "exact_code_identity_required") is True, "exact deploy identity is required")

    rollout = spec.get("production_rollout")
    _require(errors, isinstance(rollout, dict), "missing production rollout")
    if isinstance(rollout, dict):
        flag = rollout.get("flag")
        _require(errors, isinstance(flag, dict), "missing production flag contract")
        if isinstance(flag, dict):
            _require(errors, flag == {"name": "READING_PASS_V2_ENABLED", "expected_before": "false", "target": "true", "rollback_value": "false"}, "production rollout may mutate only READING_PASS_V2_ENABLED false to true")
        isolated = spec.get("isolated_validation")
        _require(errors, isinstance(isolated, dict) and isolated.get("feature_flag_value") == "true" and bool(isolated.get("required_tests")), "production rollout requires prior isolated validation")
        activation = rollout.get("activation")
        _require(errors, isinstance(activation, list) and "verify_deployed_commit_equals_current_merged_main" in activation, "production rollout requires exact deployed commit identity")

    required_validation = {
        "public_audio_preview_seconds_equals_zero",
        "anonymous_audio_request_returns_no_playable_audio_payload",
        "anonymous_audio_request_returns_no_unrestricted_audio_URL",
        "unapproved_audio_exposure_absent",
        "protected_audio_absent_from_public_manifest",
        "protected_audio_absent_from_shared_Redis",
        "protected_audio_absent_from_service_worker_cache",
        "protected_audio_absent_from_shared_CDN_cache",
        "authenticated_or_Reading_Pass_audio_follows_current_server_authority",
    }
    required_tests = _path(spec, "isolated_validation", "required_tests")
    _require(errors, isinstance(required_tests, list) and required_validation <= set(required_tests), "isolated validation omits a zero-public-audio check")

    required_safety = {
        "no_protected_audio_bytes_in_shared_redis",
        "no_unrestricted_protected_audio_urls_in_shared_redis",
        "no_reusable_cross_user_audio_authorization_in_shared_redis",
        "no_public_audio_preview_payload_in_shared_redis",
    }
    mandatory_safety = _path(spec, "redis_architecture", "mandatory_safety")
    _require(errors, isinstance(mandatory_safety, list) and required_safety <= set(mandatory_safety), "Redis safety contract permits protected audio")

    required_contracts = {"route_contract_pass_percent", "CTA_contract_pass_percent", "reader_approved_title_pass_percent", "audio_approved_title_pass_percent"}
    acceptance = spec.get("customer_ready_acceptance")
    contracts = acceptance.get("contracts") if isinstance(acceptance, dict) else None
    _require(errors, isinstance(contracts, dict) and required_contracts <= set(contracts), "CUSTOMER_READY contract omits reader/listener/CTA coverage")
    access = acceptance.get("access") if isinstance(acceptance, dict) else None
    _require(errors, isinstance(access, dict) and access.get("public_audio_preview_seconds_equals_zero_verified") is True, "CUSTOMER_READY contract omits zero-public-audio verification")

    rollback = spec.get("rollback")
    triggers = rollback.get("immediate_zero_tolerance_triggers") if isinstance(rollback, dict) else None
    required_triggers = {"any_anonymous_playable_audio_response", "any_nonzero_public_audio_preview", "any_protected_audio_URL_in_public_manifest", "any_protected_audio_payload_in_shared_Redis", "any_service_worker_cached_protected_audio", "any_shared_CDN_cached_protected_audio", "any_audio_access_granted_solely_by_client_or_cached_state", "any_unapproved_title_exposing_an_audio_operation_or_payload"}
    _require(errors, isinstance(triggers, list) and required_triggers <= set(triggers), "rollback omits a zero-public-audio trigger")

    forbidden_terms = {"redis_FLUSHALL", "redis_FLUSHDB", "redis_KEYS_wildcard", "direct_push_to_main", "administrator_merge_bypass"}
    commands = _path(spec, "prohibitions", "commands")
    _require(errors, isinstance(commands, list) and forbidden_terms <= set(commands), "prohibitions omit a destructive or bypass command")

    for trail, value in _walk(spec):
        name = ".".join(trail).lower()
        if ("audio" in name and ("preview" in name or "public" in name) and name.endswith("seconds")):
            _require(errors, type(value) is int and value == 0, f"nonzero or non-integer public audio duration at {'.'.join(trail)}")
        if ("audio" in name and ("redis" in name or "cache" in name or "service_worker" in name or "cdn" in name) and value is True):
            errors.append(f"protected audio cache permission at {'.'.join(trail)}")
        if ("cors" in name or "origin" in name) and value == "*":
            errors.append(f"wildcard CORS at {'.'.join(trail)}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--envelope", type=Path, default=DEFAULT_ENVELOPE)
    args = parser.parse_args(argv)
    try:
        errors = validate(parse_restricted_yaml(args.envelope))
    except (OSError, EnvelopeSyntaxError) as exc:
        errors = [str(exc)]
    if errors:
        for error in errors:
            print(f"INVALID: {error}", file=sys.stderr)
        return 1
    print("VALID: customer-ready autonomy envelope")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
