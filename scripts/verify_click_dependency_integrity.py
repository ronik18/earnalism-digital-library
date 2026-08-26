#!/usr/bin/env python3
"""Verify the narrow Click dependency policy used by backend and UAT builds."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENT_FILES = (
    ROOT / "backend" / "requirements.txt",
    ROOT / "backend" / "requirements-runtime.txt",
)
EXPECTED_CLICK_PIN = "8.3.3"
REJECTED_CLICK_PINS = {"8.3.2"}
PYPI_URL = f"https://pypi.org/pypi/click/{EXPECTED_CLICK_PIN}/json"
TIMEOUT_SECONDS = 10


def click_pin(path: Path) -> str | None:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("click=="):
            return line.partition("==")[2]
    return None


def fail(code: str, detail: str) -> int:
    print(json.dumps({"status": code, "detail": detail}, sort_keys=True))
    return 1


def main() -> int:
    if sys.version_info < (3, 10):
        return fail("PYTHON_VERSION_INCOMPATIBLE", "Click 8.3.3 requires Python >= 3.10")

    pins = {path.relative_to(ROOT).as_posix(): click_pin(path) for path in REQUIREMENT_FILES}
    if any(pin in REJECTED_CLICK_PINS for pin in pins.values()):
        return fail("VULNERABLE_CLICK_PIN", "Click 8.3.2 is rejected by the dependency vulnerability policy")
    if any(pin != EXPECTED_CLICK_PIN for pin in pins.values()):
        return fail("PIN_MISMATCH", f"expected click=={EXPECTED_CLICK_PIN} in every backend requirement authority")

    try:
        with urllib.request.urlopen(PYPI_URL, timeout=TIMEOUT_SECONDS) as response:
            metadata = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return fail("MISSING_VERSION", "Click 8.3.3 is absent from public PyPI")
        return fail("PUBLIC_PYPI_HTTP_ERROR", str(error.code))
    except urllib.error.URLError as error:
        return fail("PUBLIC_PYPI_NETWORK_ERROR", type(error.reason).__name__)
    except (TimeoutError, json.JSONDecodeError) as error:
        return fail("PUBLIC_PYPI_NETWORK_ERROR", type(error).__name__)

    info = metadata.get("info", {})
    if info.get("version") != EXPECTED_CLICK_PIN:
        return fail("MISSING_VERSION", "public PyPI did not return Click 8.3.3")
    if info.get("yanked"):
        return fail("YANKED_VERSION", "Click 8.3.3 is yanked on public PyPI")
    if info.get("requires_python") != ">=3.10":
        return fail("PYTHON_REQUIREMENT_MISMATCH", "unexpected Click Python requirement")

    print(
        json.dumps(
            {
                "status": "PASS",
                "click": EXPECTED_CLICK_PIN,
                "index": "pypi.org",
                "pins": pins,
                "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "yanked": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
