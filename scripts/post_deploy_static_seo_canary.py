#!/usr/bin/env python3
"""Fail closed raw-HTML canary for deployed static SEO snapshots."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "launch"
DEFAULT_BASE_URL = "https://theearnalism.com"
ROUTES = {
    "/book/dracula": {
        "required": ("first 3 canonical pages", "View Reading Passes"),
        "forbidden": ("Chapter 1 is free", "Read Chapter 1", "7-day", "The First Chapter"),
        "reader": False,
    },
    "/pricing?book=dracula": {
        "required": ("first 3 canonical pages", "Reading Pass", "No subscription"),
        "forbidden": ("The First Chapter", "Start with Chapter 1", "7-day"),
        "reader": False,
    },
    "/reader/dracula": {
        "required": ("first 3 canonical pages",),
        "forbidden": ("Read Dracula Chapter 1", "Preview chapter unlocked", "Get 7-Day Reading Pass", "7-day"),
        "reader": True,
    },
}


def fetch_raw_html(base_url: str, route: str, timeout: int) -> tuple[int, dict[str, str], str, str]:
    url = urljoin(base_url.rstrip("/") + "/", route.lstrip("/"))
    request = Request(url, headers={"User-Agent": "EarnalismStaticSeoCanary/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers.items()), response.read().decode("utf-8", errors="replace"), url
    except HTTPError as error:
        return error.code, dict(error.headers.items()), error.read().decode("utf-8", errors="replace"), url
    except URLError as error:
        return 0, {}, "", f"{url} ({error})"


def inspect_route(route: str, policy: dict[str, object], status: int, headers: dict[str, str], html: str, url: str) -> dict[str, object]:
    normalized = html.lower()
    failures = []
    if status != 200:
        failures.append(f"expected status 200, got {status}")
    for phrase in policy["required"]:
        if str(phrase).lower() not in normalized:
            failures.append(f"missing required phrase: {phrase}")
    for phrase in policy["forbidden"]:
        if str(phrase).lower() in normalized:
            failures.append(f"forbidden phrase present: {phrase}")
    if policy["reader"] and "noindex" not in normalized:
        failures.append("reader raw HTML is missing noindex metadata")
    return {"route": route, "url": url, "status_code": status, "cache_control": headers.get("Cache-Control", ""), "failures": failures, "result": "PASS" if not failures else "FAIL"}


def run(base_url: str, timeout: int) -> dict[str, object]:
    routes = [inspect_route(route, policy, *fetch_raw_html(base_url, route, timeout)) for route, policy in ROUTES.items()]
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "base_url": base_url, "result": "PASS" if all(row["result"] == "PASS" for row in routes) else "FAIL", "routes": routes}


def write_report(report: dict[str, object]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "post_deploy_static_seo_canary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    rows = ["# Static SEO Raw HTML Canary", "", f"Result: `{report['result']}`", ""]
    for row in report["routes"]:
        rows.append(f"- `{row['route']}`: `{row['result']}`; status={row['status_code']}; failures={'; '.join(row['failures']) or 'none'}")
    (OUTPUT_DIR / "post_deploy_static_seo_canary.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deployed raw HTML snapshot copy.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()
    report = run(args.base_url, args.timeout)
    write_report(report)
    print(f"Static SEO raw HTML canary: result={report['result']}")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
