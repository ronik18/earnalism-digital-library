#!/usr/bin/env python3
"""Fail the focused review workflow when its captured evidence is incomplete."""
import json, os, sys
from pathlib import Path

root = Path(os.environ.get("BOOK_COMMERCE_REVIEW_CURRENT", "uat/evidence/book-commerce-final-review/current"))
required = ["all-browser-capture-results.json", "book-interaction-results.json", "commerce-geometry-results.json", "heading-results.json", "book-commerce-browser-results.json", "browser-font-results.json", "capture-stability-results.json", "webkit-network-diagnostics.json"]


def contains_nonfinal_status(value):
    """Reject non-final machine status values without parsing human evidence text."""
    if isinstance(value, dict):
        return any(
            key in {"status", "result", "state"}
            and isinstance(item, str)
            and item in {"PENDING", "NOT RUN", "WORKFLOW RUNNING"}
            or contains_nonfinal_status(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(contains_nonfinal_status(item) for item in value)
    return False


def main() -> int:
    errors = []
    for name in required:
        path = root / name
        if not path.is_file() or not path.stat().st_size:
            errors.append(f"missing:{name}")
    if not errors:
        contents = {name: json.loads((root / name).read_text()) for name in required}
        interaction = contents["book-interaction-results.json"]
        held_detail = interaction.get("status") == "NOT_APPLICABLE_PUBLIC_RELEASE_HOLD"
        if held_detail:
            if interaction.get("mode") != "PUBLIC_DETAIL_WITHHELD_PENDING_RIGHTS_DECISIONS" or interaction.get("book_detail_publicly_withheld") is not True:
                errors.append("book-detail-hold")
        elif interaction.get("status") != "PASS" or interaction.get("arrow_left_target") != "Details" or interaction.get("tab_order") != ["About", "Details", "Chapters", "Related"] or not all(interaction.get(key) is True for key in ("keyboard_arrow_left", "keyboard_arrow_right", "keyboard_wrap_next", "keyboard_wrap_previous", "focus_result")):
            errors.append("book-tab-keyboard")
        if contents["commerce-geometry-results.json"].get("status") != "PASS": errors.append("commerce-geometry")
        if contents["heading-results.json"].get("status") != "PASS": errors.append("headings")
        for browser, result in contents["book-commerce-browser-results.json"].items():
            if result.get("status") != "PASS": errors.append(f"browser:{browser}")
        for browser, result in contents["browser-font-results.json"].items():
            if result.get("status") != "PASS": errors.append(f"fonts:{browser}")
        for browser, result in contents["capture-stability-results.json"].items():
            if result.get("status") != "PASS": errors.append(f"stability:{browser}")
        diagnostics = contents["webkit-network-diagnostics.json"]
        if diagnostics.get("status") != "PASS" or diagnostics.get("entries"):
            errors.append("webkit-network-diagnostics")
        root_cause = diagnostics.get("root_cause") or {}
        if root_cause.get("classification") != "STATIC_ASSET_403" or not root_cause.get("url"):
            errors.append("webkit-root-cause")
        for browser, report in contents["all-browser-capture-results.json"].items():
            for state in report.get("states", []):
                if state.get("http_status") != 200 or not state.get("stable") or state.get("scroll_width") != state.get("client_width") or state.get("console_and_page_errors") or state.get("failed_required_requests") or state.get("network_diagnostics"):
                    errors.append(f"state:{browser}:{state.get('id')}")
        if contains_nonfinal_status(contents): errors.append("non-final-value")
    print(json.dumps({"status":"PASS" if not errors else "FAIL", "errors":errors}))
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
