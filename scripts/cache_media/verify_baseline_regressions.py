#!/usr/bin/env python3
"""Verify the documented A0.1 baseline failures were reproduced and retired.

This deliberately verifies evidence rather than accepting a permanent list of
known failures: the base and untouched PR fingerprints must be identical and
the post-adjudication reports must be green.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as etree
from pathlib import Path


def failures(path: Path) -> set[str]:
    if not path.is_file():
        raise ValueError(f"required JUnit report is missing: {path}")
    try:
        root = etree.parse(path).getroot()
    except etree.ParseError as exc:
        raise ValueError(f"invalid JUnit report {path}: {exc}") from exc
    return {
        f"{case.get('classname', '')}::{case.get('name', '')}"
        for case in root.iter("testcase")
        if case.find("failure") is not None or case.find("error") is not None
    }


def report(args: argparse.Namespace) -> tuple[dict, list[str]]:
    ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
    entries = ledger.get("entries")
    errors: list[str] = []
    if not isinstance(entries, list):
        return {}, ["ledger entries must be a list"]
    if ledger.get("original_documented_failure_count") != len(entries):
        errors.append("ledger original_documented_failure_count does not equal entry count")

    expected = {entry.get("test_node_id") for entry in entries}
    if "" in expected or None in expected or len(expected) != len(entries):
        errors.append("ledger must contain one unique test_node_id per original failure")

    results = {}
    for suite, before_base, before_pr, after in (
        ("audio_cleanup", args.base_cleanup, args.pr_cleanup, args.final_cleanup),
        ("legacy_audio", args.base_legacy, args.pr_legacy, args.final_legacy),
    ):
        base_failures = failures(before_base)
        pr_failures = failures(before_pr)
        final_failures = failures(after)
        results[suite] = {
            "base_failures": sorted(base_failures),
            "pr_failures_before": sorted(pr_failures),
            "final_failures": sorted(final_failures),
            "new_failures": sorted(pr_failures - base_failures),
            "removed_before_adjudication": sorted(base_failures - pr_failures),
            "unchanged_failures": sorted(base_failures & pr_failures),
        }
        if base_failures != pr_failures:
            errors.append(f"{suite}: base and untouched PR fingerprints differ")
        if final_failures:
            errors.append(f"{suite}: final report is not green")

    original_failures = set(results["audio_cleanup"]["base_failures"]) | set(results["legacy_audio"]["base_failures"])
    if original_failures != expected:
        errors.append("ledger node IDs do not exactly match the reproduced original failures")

    valid_authority = {
        "STALE_TEST_TO_UPDATE",
        "STALE_TEST_TO_REMOVE",
        "DUPLICATE_OF_CURRENT_AUTHORITATIVE_TEST",
    }
    for entry in entries:
        node = entry.get("test_node_id", "<missing>")
        evidence = entry.get("evidence")
        replacement = entry.get("replacement_coverage")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{node}: missing evidence")
        if not isinstance(replacement, list) or not replacement:
            errors.append(f"{node}: missing replacement coverage")
        if entry.get("authority_classification") not in valid_authority:
            errors.append(f"{node}: unaccepted authority classification")
        if entry.get("final_result") != "PASS":
            errors.append(f"{node}: final result is not PASS")
        if entry.get("a1_blocker") is not False or entry.get("release_blocker") is not False:
            errors.append(f"{node}: unresolved blocker remains in a green adjudication")
        if not entry.get("expiration_or_follow_up_condition"):
            errors.append(f"{node}: missing expiration or follow-up condition")

    results["ledger_entry_count"] = len(entries)
    results["adjudicated_stale_failures"] = len(entries) if not errors else 0
    return results, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    for name in ("base-cleanup", "pr-cleanup", "final-cleanup", "base-legacy", "pr-legacy", "final-legacy"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    try:
        result, errors = report(args)
    except ValueError as exc:
        result, errors = {}, [str(exc)]
    result["result"] = "PASS" if not errors else "FAIL"
    result["errors"] = errors
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
