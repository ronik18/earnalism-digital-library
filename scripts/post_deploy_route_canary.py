#!/usr/bin/env python3
"""Post-deploy removed-route canary for Earnalism production parity."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "launch"
REQUIRED_ROBOTS_TAG = "noindex, nofollow, noarchive"
DEFAULT_BASE_URL = "https://theearnalism.com"
REMOVED_ROUTES = [
    "/product/patterned-wrap-dress",
    "/journal/denim-jackets",
    "/shop",
    "/shop/",
    "/shop/example",
    "/fashion",
    "/clothing",
    "/woocommerce/test",
    "/sample-product/test",
    "/placeholder-product/test",
]


class NoRedirectHandler(HTTPRedirectHandler):
    """Return redirect responses instead of following them."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


OPENER = build_opener(NoRedirectHandler)


@dataclass
class RouteResult:
    path: str
    url: str
    status: int
    redirected: bool
    location: str
    x_robots_tag: str
    generic_shell: bool
    pass_status: bool
    issues: list[str]
    error: str = ""


def is_generic_shell(body: str) -> bool:
    lowered = body.lower()
    return '<div id="root"></div>' in lowered or (
        "earnalism digital library" in lowered
        and "this page is no longer available" not in lowered
    )


def fetch_route(base_url: str, route: str, timeout: int) -> RouteResult:
    url = f"{base_url.rstrip('/')}{route}"
    request = Request(
        url,
        headers={
            "Accept": "text/html,*/*",
            "User-Agent": "EarnalismPostDeployRouteCanary/1.0",
        },
    )
    status = 0
    headers = {}
    body = ""
    error = ""
    try:
        with OPENER.open(request, timeout=timeout) as response:
            status = int(response.getcode() or 0)
            headers = {key.lower(): value for key, value in response.headers.items()}
            body = response.read(65536).decode("utf-8", errors="replace")
    except HTTPError as exc:
        status = int(exc.code or 0)
        headers = {key.lower(): value for key, value in exc.headers.items()}
        body = exc.read(65536).decode("utf-8", errors="replace")
    except (TimeoutError, URLError, OSError) as exc:
        error = str(exc)

    location = headers.get("location", "")
    x_robots_tag = headers.get("x-robots-tag", "")
    generic_shell = is_generic_shell(body)
    redirected = status in {301, 302, 303, 307, 308} or bool(location)
    issues: list[str] = []
    if status not in {404, 410}:
        issues.append(f"expected 410 or 404, got {status or 'no response'}")
    if redirected:
        issues.append(f"unexpected redirect to {location or '(missing Location)'}")
    if generic_shell:
        issues.append("response appears to be the generic SPA shell")
    if x_robots_tag != REQUIRED_ROBOTS_TAG:
        issues.append(f"expected X-Robots-Tag {REQUIRED_ROBOTS_TAG!r}, got {x_robots_tag!r}")
    if error:
        issues.append(error)

    return RouteResult(
        path=route,
        url=url,
        status=status,
        redirected=redirected,
        location=location,
        x_robots_tag=x_robots_tag,
        generic_shell=generic_shell,
        pass_status=not issues,
        issues=issues,
        error=error,
    )


def write_reports(base_url: str, results: list[RouteResult]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    status = "PASS" if all(result.pass_status for result in results) else "BLOCKED"
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": status,
        "base_url": base_url,
        "required_x_robots_tag": REQUIRED_ROBOTS_TAG,
        "routes": [asdict(result) for result in results],
        "operator_instruction": (
            "If status is BLOCKED, do not mark GO_FOR_CONTROLLED_PUBLICATION. "
            "Roll back the last frontend deployment or re-deploy the route fix, "
            "then rerun this canary."
        ),
    }
    (OUTPUT_DIR / "post_deploy_route_canary.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    rows = [
        "# Post-Deploy Route Canary",
        "",
        f"Status: `{status}`",
        "",
        "Removed/demo routes must return `410` or `404`, must not redirect, must not serve the generic SPA shell, and must include exactly `X-Robots-Tag: noindex, nofollow, noarchive`.",
        "",
        "| Path | Status | Redirected | X-Robots-Tag | Generic Shell | Issues |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for result in results:
        rows.append(
            "| {path} | {status} | {redirected} | {robots} | {shell} | {issues} |".format(
                path=result.path,
                status=result.status,
                redirected=result.redirected,
                robots=result.x_robots_tag or "",
                shell=result.generic_shell,
                issues="; ".join(result.issues),
            )
        )
    rows.extend(
        [
            "",
            "## Rollback / Operator Instructions",
            "",
            "- If any route is `BLOCKED`, keep launch status at `HOLD_FOR_FIXES`.",
            "- Roll back the last Vercel production deployment or re-deploy the commit containing the removed-content route fix.",
            "- Rerun `npm run launch:post-deploy-route-canary` after rollback or redeploy.",
            "- Do not create `GO_FOR_CONTROLLED_PUBLICATION` or enable publication flags from a failed canary.",
            "",
        ]
    )
    (OUTPUT_DIR / "post_deploy_route_canary.md").write_text("\n".join(rows), encoding="utf-8")

    text_rows = [
        "Post-Deploy Route Canary",
        f"Status: {status}",
        f"Base URL: {base_url}",
        f"Required X-Robots-Tag: {REQUIRED_ROBOTS_TAG}",
        "",
    ]
    for result in results:
        text_rows.extend(
            [
                f"Path: {result.path}",
                f"Status: {result.status}",
                f"Redirected: {result.redirected}",
                f"X-Robots-Tag: {result.x_robots_tag or '(missing)'}",
                f"Generic shell: {result.generic_shell}",
                f"Issues: {'; '.join(result.issues) if result.issues else 'none'}",
                "",
            ]
        )
    text_rows.extend(
        [
            "Operator instructions:",
            "- If any route is BLOCKED, keep launch status at HOLD_FOR_FIXES.",
            "- Removed/demo routes must stay crawlable so crawlers can observe 410/404 plus X-Robots-Tag.",
            "- Do not create APPROVED_TO_PUBLISH.md from a failed route canary.",
            "",
        ]
    )
    (OUTPUT_DIR / "post_deploy_route_canary.txt").write_text("\n".join(text_rows), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify removed/demo routes after production deployment.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()

    results = [fetch_route(args.base_url, route, args.timeout) for route in REMOVED_ROUTES]
    write_reports(args.base_url, results)
    if not all(result.pass_status for result in results):
        print("Production route canary BLOCKED. See output/launch/post_deploy_route_canary.md.")
        return 1
    print("Production route canary PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
