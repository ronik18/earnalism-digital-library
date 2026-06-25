#!/usr/bin/env python3
"""Raw HTML social-preview audit for the Dracula-first controlled launch."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "launch"
SITE_URL = "https://theearnalism.com"
ROUTES = ["/", "/book/dracula", "/library"]
PRODUCTION_ROUTES = ["/", "/book/dracula", "/library", "/reader/dracula"]
REQUIRED_PROPERTY_TAGS = ["og:title", "og:description", "og:image", "og:url"]
REQUIRED_NAME_TAGS = ["twitter:card", "twitter:title", "twitter:description", "twitter:image"]
BROAD_CATALOG_CLAIMS = [
    "preview every book before you pay",
    "a quieter bookstore for readers who linger",
    "discover thoughtful books across",
    "all categories are live",
    "broad live catalog",
]
POSITIVE_AUDIO_CLAIMS = [
    "listen now",
    "audiobook available",
    "audio available now",
    "play audiobook",
    "start listening",
]
NEGATED_AUDIO_SAFETY_CLAIMS = [
    "no unapproved title offers start reading, read preview, or listen now",
    "audio not available yet",
    "audio is not available yet",
    "dracula audio is disabled",
]
FAKE_REVIEW_RATING_PATTERNS = [
    '"aggregaterating"',
    '"@type":"aggregaterating"',
    '"@type":"review"',
    '"reviewrating"',
    'itemprop="review"',
    "itemprop='review'",
]
UNAPPROVED_ROUTE_PATTERNS = [
    "/book/kshudhita",
    "/reader/kshudhita",
    "/book/bn-",
    "/reader/bn-",
    "/book/book-",
    "/reader/book-",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def static_snapshot_path(route: str) -> Path:
    build_dir = ROOT / "frontend" / "build"
    if route == "/":
        return build_dir / "index.html"
    return build_dir / route.strip("/") / "index.html"


def ensure_static_seo_snapshots() -> None:
    expected_snapshots = [static_snapshot_path(route) for route in ROUTES]
    if all(path.exists() for path in expected_snapshots):
        return
    script = ROOT / "frontend" / "scripts" / "generate-static-seo-snapshots.mjs"
    if not script.exists():
        return
    subprocess.run(
        ["node", str(script)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def raw_html(route: str, base_url: str | None = None, timeout: int = 10) -> tuple[str, str]:
    if base_url:
        url = urljoin(base_url.rstrip("/") + "/", route.lstrip("/"))
        request = Request(url, headers={"User-Agent": "EarnalismSocialPreviewAudit/1.0"})
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace"), url
        except (HTTPError, URLError) as error:
            return "", f"{url} ({error})"

    snapshot = static_snapshot_path(route)
    if snapshot.exists():
        return read_text(snapshot), str(snapshot.relative_to(ROOT))
    if route == "/":
        public_index = ROOT / "frontend" / "public" / "index.html"
        return read_text(public_index), str(public_index.relative_to(ROOT))
    return "", str(snapshot.relative_to(ROOT))


def meta_content(html: str, tag: str, attr: str) -> str:
    match = re.search(rf"<meta\s+[^>]*{attr}=[\"']{re.escape(tag)}[\"'][^>]*>", html, re.IGNORECASE)
    if not match:
        return ""
    content = re.search(r"content=[\"']([^\"']*)[\"']", match.group(0), re.IGNORECASE)
    return content.group(1).strip() if content else ""


def html_title(html: str) -> str:
    match = re.search(r"<title>\s*([\s\S]*?)\s*</title>", html, re.IGNORECASE)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


def canonical_href(html: str) -> str:
    match = re.search(r"<link\s+[^>]*rel=[\"']canonical[\"'][^>]*>", html, re.IGNORECASE)
    if not match:
        return ""
    href = re.search(r"href=[\"']([^\"']*)[\"']", match.group(0), re.IGNORECASE)
    return href.group(1).strip() if href else ""


def json_ld_types(html: str) -> set[str]:
    types: set[str] = set()
    for match in re.finditer(
        r"<script\s+[^>]*type=[\"']application/ld\+json[\"'][^>]*>([\s\S]*?)</script>",
        html,
        re.IGNORECASE,
    ):
        try:
            payload = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            item_type = item.get("@type")
            if isinstance(item_type, str):
                types.add(item_type)
            elif isinstance(item_type, list):
                types.update(str(value) for value in item_type)
    return types


def has_fake_review_or_rating(html: str) -> bool:
    compact = re.sub(r"\s+", "", html.lower())
    return any(pattern in compact for pattern in FAKE_REVIEW_RATING_PATTERNS)


def has_positive_audio_claim(html: str) -> bool:
    lowered = html.lower()
    for safety_claim in NEGATED_AUDIO_SAFETY_CLAIMS:
        lowered = lowered.replace(safety_claim, "")
    return any(claim in lowered for claim in POSITIVE_AUDIO_CLAIMS)


def route_policy_checks(route: str, html: str) -> dict[str, bool]:
    lowered = html.lower()
    checks = {
        "no_broad_catalog_claim": not any(claim in lowered for claim in BROAD_CATALOG_CLAIMS),
        "no_fake_rating_review": not has_fake_review_or_rating(html),
        "no_positive_audio_claim": not has_positive_audio_claim(html),
        "no_unapproved_book_route": not any(pattern in lowered for pattern in UNAPPROVED_ROUTE_PATTERNS),
    }
    if route == "/":
        checks["homepage_dracula_first"] = (
            "begin with dracula" in lowered
            or "controlled launch begins with dracula" in lowered
        )
    if route == "/book/dracula":
        types = json_ld_types(html)
        title = html_title(html).lower()
        checks.update(
            {
                "title_dracula_bram_stoker": "dracula" in title and "bram stoker" in title,
                "canonical_book_dracula": canonical_href(html) == "https://theearnalism.com/book/dracula",
                "book_json_ld_present": "Book" in types,
            }
        )
    if route == "/library":
        checks["library_dracula_only"] = (
            "dracula is the only live" in lowered
            or "live controlled release: dracula only" in lowered
        )
    if route == "/reader/dracula":
        robots = meta_content(html, "robots", "name").lower()
        checks.update(
            {
                "reader_noindex_follow": "noindex" in robots and "follow" in robots,
                "reader_canonical_to_book": canonical_href(html) == "https://theearnalism.com/book/dracula",
            }
        )
    return checks


def audit_route(route: str, base_url: str | None, timeout: int) -> dict[str, Any]:
    html, source = raw_html(route, base_url=base_url, timeout=timeout)
    property_tags = {tag: meta_content(html, tag, "property") for tag in REQUIRED_PROPERTY_TAGS}
    name_tags = {tag: meta_content(html, tag, "name") for tag in REQUIRED_NAME_TAGS}
    missing = [tag for tag, value in {**property_tags, **name_tags}.items() if not value]
    route_checks = route_policy_checks(route, html)
    failed_checks = [check for check, ok in route_checks.items() if not ok]
    return {
        "route": route,
        "source": source,
        "status": "PASS" if html and not missing and not failed_checks else "FAIL",
        "property_tags": property_tags,
        "name_tags": name_tags,
        "missing_tags": missing,
        "route_checks": route_checks,
        "failed_checks": failed_checks,
    }


def report_markdown(payload: dict[str, Any]) -> str:
    rows = [
        "| Route | Status | Missing Tags | Failed Checks | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in payload["routes"]:
        rows.append(
            f"| {row['route']} | {row['status']} | {', '.join(row['missing_tags']) or 'none'} | {', '.join(row['failed_checks']) or 'none'} | {row['source']} |"
        )
    return "\n".join(
        [
            "# Social Preview Audit",
            "",
            f"Status: `{payload['status']}`",
            "",
            "This audit reads raw HTML only. It does not call social, ad, or payment provider APIs.",
            "",
            *rows,
        ]
    )


def run(base_url: str | None = None, timeout: int = 10) -> dict[str, Any]:
    if not base_url:
        ensure_static_seo_snapshots()
    route_list = PRODUCTION_ROUTES if base_url else ROUTES
    routes = [audit_route(route, base_url=base_url, timeout=timeout) for route in route_list]
    status = "PASS" if all(route["status"] == "PASS" for route in routes) else "FAIL"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "base_url": base_url or "local_build",
        "external_social_api_calls": [],
        "routes": routes,
    }
    write_json(OUTPUT_DIR / "social_preview_audit.json", payload)
    write_text(OUTPUT_DIR / "social_preview_audit.md", report_markdown(payload))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit raw HTML OG/Twitter social preview tags.")
    parser.add_argument("--base-url", default="", help="Optional deployed frontend base URL. Defaults to local build snapshots.")
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()
    payload = run(base_url=args.base_url or None, timeout=args.timeout)
    print(f"Social preview audit complete: status={payload['status']} output_dir={OUTPUT_DIR}")
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
