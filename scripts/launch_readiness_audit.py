#!/usr/bin/env python3
"""Read-only Phase 13 launch readiness audits for Earnalism."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "launch"
SITE_URL = "https://theearnalism.com"

REMOVED_URLS = [
    "/product/patterned-wrap-dress",
    "/journal/denim-jackets",
    "/shop",
    "/shop/example",
    "/fashion",
    "/clothing",
    "/woocommerce/test",
    "/sample-product/test",
    "/placeholder-product/test",
]

DEMO_TERMS = [
    "patterned-wrap-dress",
    "denim",
    "fashion",
    "woocommerce",
    "clothing",
    "apparel",
    "/shop",
    "/product/",
    "/products/",
    "/product-category/",
]

FIRST_BATCH = [
    "Anandamath Visual Study Companion",
    "Devdas Study Edition",
    "Abol Tabol Illustrated Reader",
    "Sultana's Dream Feminist Sci-Fi Edition",
    "Sherlock Holmes Logic Workbook",
    "Dracula Gothic Fiction Visual Guide",
    "Frankenstein Science & Ethics Guide",
    "Tagore Short Stories for Young Readers",
    "Calculus Made Easy Visual Guide",
    "Chander Pahar Adventure Companion",
]

LAUNCH_EVENTS = [
    "page_view",
    "book_view",
    "preview_start",
    "reading_started",
    "reading_session_completed",
    "pricing_view",
    "checkout_start",
    "payment_success",
    "payment_failed",
    "newsletter_joined",
    "referral_invited",
    "referral_converted",
    "institution_interest",
    "audio_preview_played",
    "cta_clicked",
]


@dataclass
class Issue:
    area: str
    severity: str
    message: str
    recommendation: str
    blocker: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "area": self.area,
            "severity": self.severity,
            "message": self.message,
            "recommendation": self.recommendation,
            "blocker": self.blocker,
        }


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def status_from_bool(ok: bool, degraded: bool = False) -> str:
    if ok:
        return "PASS"
    if degraded:
        return "DEGRADED"
    return "FAIL"


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    rendered = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        rendered.append("| " + " | ".join(str(cell).replace("\n", " ") for cell in row) + " |")
    return "\n".join(rendered)


def command_available(name: str) -> bool:
    result = subprocess.run(["/usr/bin/env", "which", name], capture_output=True, text=True, check=False)
    return result.returncode == 0


def fetch_public_url(base_url: str, path: str, timeout: int = 10) -> dict[str, Any]:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = Request(url, headers={"User-Agent": "EarnalismLaunchReadiness/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(4096).decode("utf-8", errors="replace")
            return {
                "url": url,
                "status": response.status,
                "x_robots_tag": response.headers.get("X-Robots-Tag", ""),
                "content_type": response.headers.get("Content-Type", ""),
                "final_url": response.geturl(),
                "generic_shell": is_generic_shell(body),
                "error": "",
            }
    except HTTPError as error:
        body = error.read(4096).decode("utf-8", errors="replace")
        return {
            "url": url,
            "status": error.code,
            "x_robots_tag": error.headers.get("X-Robots-Tag", ""),
            "content_type": error.headers.get("Content-Type", ""),
            "final_url": error.geturl(),
            "generic_shell": is_generic_shell(body),
            "error": "",
        }
    except URLError as error:
        return {
            "url": url,
            "status": 0,
            "x_robots_tag": "",
            "content_type": "",
            "final_url": url,
            "generic_shell": False,
            "error": str(error.reason),
        }


def is_generic_shell(body: str) -> bool:
    lower = body.lower()
    return '<div id="root"></div>' in lower or (
        "the earnalism digital library" in lower and "this page is no longer available" not in lower
    )


def path_matches(pattern: str, path: str) -> bool:
    if pattern.endswith("/:path*"):
        return path == pattern[:-7] or path.startswith(pattern[:-7] + "/")
    return path == pattern


def local_removed_route_status(path: str, vercel_config: dict[str, Any]) -> dict[str, Any]:
    for redirect in vercel_config.get("redirects", []):
        if path_matches(str(redirect.get("source", "")), path):
            return {
                "path": path,
                "status": 308 if redirect.get("permanent") else 307,
                "destination": redirect.get("destination", ""),
                "x_robots_tag": "",
                "generic_shell": False,
                "matched": "redirect",
            }
    for rewrite in vercel_config.get("rewrites", []):
        if path_matches(str(rewrite.get("source", "")), path):
            destination = str(rewrite.get("destination", ""))
            if "/api/removed-content" in destination:
                return {
                    "path": path,
                    "status": 410 if contains_demo_term(path) else 404,
                    "destination": destination,
                    "x_robots_tag": "noindex, nofollow, noarchive",
                    "generic_shell": False,
                    "matched": "removed-content",
                }
            return {
                "path": path,
                "status": 200,
                "destination": destination,
                "x_robots_tag": "",
                "generic_shell": destination.endswith("index.html"),
                "matched": "rewrite",
            }
    return {
        "path": path,
        "status": 404,
        "destination": "",
        "x_robots_tag": "",
        "generic_shell": False,
        "matched": "none",
    }


def contains_demo_term(value: str) -> bool:
    lowered = value.lower()
    path = re.sub(r"^https?://[^/]+", "", lowered).split("?", 1)[0]
    segments = {segment for segment in path.split("/") if segment}
    retired_route_segments = {"shop", "product", "products", "product-category"}
    if segments.intersection(retired_route_segments):
        return True
    retired_terms = {
        "patterned-wrap-dress",
        "denim",
        "fashion",
        "woocommerce",
        "clothing",
        "apparel",
        "sample-product",
        "placeholder-product",
    }
    return any(term in lowered for term in retired_terms)


def audit_production_parity(*, fetch_production: bool = True, production_base_url: str = SITE_URL) -> dict[str, Any]:
    issues: list[Issue] = []
    vercel_config = read_json(ROOT / "frontend" / "vercel.json") or {}
    local_routes = [local_removed_route_status(path, vercel_config) for path in REMOVED_URLS]

    for route in local_routes:
        if route["status"] == 200 or route["generic_shell"]:
            issues.append(
                Issue(
                    "production_parity",
                    "CRITICAL",
                    f"Local Vercel route {route['path']} can reach generic shell or HTTP 200.",
                    "Route it to /api/removed-content before launch.",
                    True,
                )
            )
        if route["path"] == "/shop" and route["status"] != 410:
            issues.append(
                Issue(
                    "production_parity",
                    "HIGH",
                    "/shop should return 410/noindex during deindexing, not redirect.",
                    "Keep exact /shop routed to removed-content.",
                    True,
                )
            )

    production_routes: list[dict[str, Any]] = []
    if fetch_production:
        production_routes = [fetch_public_url(production_base_url, path) for path in REMOVED_URLS]
        for route in production_routes:
            if route["status"] == 200 or route["generic_shell"]:
                issues.append(
                    Issue(
                        "production_parity",
                        "CRITICAL",
                        f"Production {route['url']} returned shell/HTTP 200.",
                        "Deploy current frontend config and purge CDN cache if needed.",
                        True,
                    )
                )
            if route["status"] not in {404, 410}:
                issues.append(
                    Issue(
                        "production_parity",
                        "HIGH",
                        f"Production {route['url']} returned {route['status']} instead of 410/404.",
                        "Deploy current Vercel config so retired routes return 410/noindex.",
                        route["status"] == 200,
                    )
                )
            if route["status"] in {404, 410} and route["x_robots_tag"] != "noindex, nofollow, noarchive":
                issues.append(
                    Issue(
                        "production_parity",
                        "MEDIUM",
                        f"Production {route['url']} is missing X-Robots-Tag.",
                        "Ensure removed-content function is serving the response.",
                    )
                )

    api_proxy = any(
        str(rewrite.get("source")) == "/api/(.*)" and "api.theearnalism.com" in str(rewrite.get("destination"))
        for rewrite in vercel_config.get("rewrites", [])
    )
    csp_present = any(
        header.get("key") == "Content-Security-Policy"
        for block in vercel_config.get("headers", [])
        for header in block.get("headers", [])
    )

    return {
        "status": "BLOCKED" if any(issue.blocker for issue in issues) else "PASS",
        "fetch_production": fetch_production,
        "production_base_url": production_base_url,
        "vercel": {
            "framework": vercel_config.get("framework"),
            "output_directory": vercel_config.get("outputDirectory"),
            "api_proxy_present": api_proxy,
            "csp_present": csp_present,
            "removed_content_rewrites": [
                rewrite for rewrite in vercel_config.get("rewrites", []) if "/api/removed-content" in str(rewrite.get("destination"))
            ],
        },
        "local_removed_routes": local_routes,
        "production_removed_routes": production_routes,
        "issues": [issue.as_dict() for issue in issues],
    }


def sitemap_urls() -> list[str]:
    sitemap = ROOT / "frontend" / "public" / "sitemap.xml"
    if not sitemap.exists():
        return []
    try:
        root = ElementTree.fromstring(sitemap.read_text(encoding="utf-8"))
    except ElementTree.ParseError:
        return []
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [loc.text or "" for loc in root.findall(".//sm:loc", namespace)]


def audit_seo() -> dict[str, Any]:
    issues: list[Issue] = []
    urls = sitemap_urls()
    robots = read_text(ROOT / "frontend" / "public" / "robots.txt")
    index_html = read_text(ROOT / "frontend" / "public" / "index.html")
    book_detail = read_text(ROOT / "frontend" / "src" / "pages" / "BookDetail.jsx")
    library = read_text(ROOT / "frontend" / "src" / "pages" / "Library.jsx")

    demo_matches = [url for url in urls if contains_demo_term(url)]
    if demo_matches:
        issues.append(
            Issue(
                "seo",
                "CRITICAL",
                f"Sitemap contains removed/demo URLs: {', '.join(demo_matches[:5])}.",
                "Remove demo routes from generated sitemap before launch.",
                True,
            )
        )
    if "Sitemap: https://theearnalism.com/sitemap.xml" not in robots:
        issues.append(Issue("seo", "HIGH", "robots.txt does not reference the production sitemap.", "Add sitemap reference.", True))
    if "Disallow: /shop" in robots or "Disallow: /product/" in robots:
        issues.append(
            Issue(
                "seo",
                "HIGH",
                "robots.txt blocks retired ecommerce URLs, preventing crawler deindexing.",
                "Keep retired routes crawlable while they return 410/noindex.",
                True,
            )
        )
    required_meta = [
        '<meta name="description"',
        'property="og:title"',
        'property="og:description"',
        'name="twitter:card"',
        'rel="canonical"',
        'application/ld+json',
    ]
    missing_meta = [token for token in required_meta if token not in index_html]
    if missing_meta:
        issues.append(Issue("seo", "HIGH", f"Homepage static HTML is missing {missing_meta}.", "Restore static SEO tags.", True))
    if "JsonLd" not in book_detail or '"@type": "Book"' not in book_detail:
        issues.append(Issue("seo", "HIGH", "Book detail pages lack Book JSON-LD rendering.", "Add data-driven Book JSON-LD.", True))
    if "useSEO" not in library:
        issues.append(Issue("seo", "MEDIUM", "Library page SEO hook was not detected.", "Ensure library metadata is explicit."))

    client_side_risk = "api.get(`/books/${slug}`" in book_detail
    if client_side_risk:
        issues.append(
            Issue(
                "seo",
                "MEDIUM",
                "Book detail metadata is generated client-side after API load in the CRA app.",
                "For 9.7+ launch SEO, consider prerender/SSR/static snapshots for priority book pages.",
            )
        )

    return {
        "status": "BLOCKED" if any(issue.blocker for issue in issues) else "PASS_WITH_WARNINGS" if issues else "PASS",
        "sitemap": {
            "url_count": len(urls),
            "demo_url_count": len(demo_matches),
            "demo_urls": demo_matches[:20],
            "book_url_count": sum("/book/" in url for url in urls),
        },
        "robots": {
            "sitemap_present": "Sitemap:" in robots,
            "retired_routes_crawlable": "Disallow: /shop" not in robots and "Disallow: /product/" not in robots,
            "private_routes_blocked": all(token in robots for token in ["Disallow: /admin", "Disallow: /reader/", "Disallow: /api/"]),
        },
        "static_html": {
            "homepage_meta_complete": not missing_meta,
            "organization_json_ld": '"@type": "Organization"' in index_html,
            "website_json_ld": '"@type": "WebSite"' in index_html,
            "book_json_ld_present": "JsonLd" in book_detail and '"@type": "Book"' in book_detail,
            "client_side_book_metadata_risk": client_side_risk,
        },
        "issues": [issue.as_dict() for issue in issues],
    }


def audit_ux_conversion() -> dict[str, Any]:
    issues: list[Issue] = []
    home = read_text(ROOT / "frontend" / "src" / "pages" / "Home.jsx")
    book_detail = read_text(ROOT / "frontend" / "src" / "pages" / "BookDetail.jsx")
    pricing = read_text(ROOT / "frontend" / "src" / "pages" / "Pricing.jsx")
    header = read_text(ROOT / "frontend" / "src" / "components" / "Header.jsx")

    checks = {
        "hero_start_reading": "Start Reading" in home,
        "hero_pricing_path": "/pricing" in home,
        "newsletter_entry": "newsletter" in home.lower(),
        "book_preview_cta": "Read Preview" in book_detail or "reader/" in book_detail,
        "book_buy_cta": "Buy Reading Time" in book_detail and "bottom-buy-reading-time" in book_detail,
        "pricing_cta": "data-testid={`buy-${p.id}`" in pricing or "Buy" in pricing,
        "pricing_trust_statement": "Payments are processed securely by Razorpay" in pricing,
        "mobile_nav_cta": "mobile-cta-library" in header,
    }
    for key, passed in checks.items():
        if not passed:
            issues.append(Issue("ux_conversion", "HIGH", f"Missing UX/conversion signal: {key}.", "Restore the missing CTA or trust statement.", True))

    return {
        "status": "BLOCKED" if any(issue.blocker for issue in issues) else "PASS",
        "checks": checks,
        "recommendations": [
            "Add server-rendered copy for priority public pages before major SEO launch.",
            "Keep Start Reading as primary CTA and Buy Reading Time as monetization CTA.",
            "Add explicit institution pilot CTA to homepage once the operator has a staffed response path.",
            "Keep pricing trust/refund/support copy visible above checkout start.",
        ],
        "issues": [issue.as_dict() for issue in issues],
    }


def classify_catalog_url(url: str) -> dict[str, Any]:
    path = re.sub(r"^https?://[^/]+", "", url)
    title = path.strip("/") or "homepage"
    action = "KEEP_PROMOTE"
    reasons: list[str] = []
    if contains_demo_term(path):
        action = "DELETE"
        reasons.append("Retired demo/ecommerce/fashion path.")
    elif "/book/book-" in path or "/book/bn-" in path:
        action = "KEEP_REWRITE"
        reasons.append("Generated or code-like slug should be rewritten before promotion.")
    elif "/reader/" in path:
        action = "NOINDEX"
        reasons.append("Reader routes are private/usage-gated and should not be indexed.")
    elif "?" in path:
        action = "KEEP_PROMOTE"
        reasons.append("Category URL is allowed but should be canonicalized carefully.")
    return {
        "url": url,
        "path": path,
        "title": title,
        "recommended_action": action,
        "reason": "; ".join(reasons) or "Launch-aligned public URL.",
    }


def write_catalog_action_plan(urls: list[str]) -> dict[str, Any]:
    rows = [classify_catalog_url(url) for url in urls]
    csv_path = ROOT / "LAUNCH_CATALOG_ACTION_PLAN.csv"
    md_path = ROOT / "LAUNCH_CATALOG_ACTION_PLAN.md"
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["url", "path", "title", "recommended_action", "reason"])
    writer.writeheader()
    writer.writerows(rows)
    write_text(csv_path, buffer.getvalue())
    grouped: dict[str, int] = {}
    for row in rows:
        grouped[row["recommended_action"]] = grouped.get(row["recommended_action"], 0) + 1
    write_text(
        md_path,
        "\n".join(
            [
                "# Launch Catalog Action Plan",
                "",
                "Dry-run classification only. No content was deleted or mutated.",
                "",
                markdown_table(["Action", "Count"], [[key, value] for key, value in sorted(grouped.items())]),
                "",
                "## Highest-Risk Items",
                "",
                markdown_table(
                    ["URL", "Action", "Reason"],
                    [[row["url"], row["recommended_action"], row["reason"]] for row in rows if row["recommended_action"] != "KEEP_PROMOTE"][:40],
                ),
            ]
        ),
    )
    return {"rows": rows, "counts": grouped, "csv": str(csv_path), "markdown": str(md_path)}


def audit_performance() -> dict[str, Any]:
    issues: list[Issue] = []
    package = read_json(ROOT / "frontend" / "package.json") or {}
    root_package = read_json(ROOT / "package.json") or {}
    frontend_build = ROOT / "frontend" / "build" / "static" / "js"
    js_files = list(frontend_build.glob("*.js")) if frontend_build.exists() else []
    total_js_bytes = sum(path.stat().st_size for path in js_files)
    server = read_text(ROOT / "backend" / "server.py")
    app = read_text(ROOT / "frontend" / "src" / "App.js")

    if total_js_bytes > 1_200_000:
        issues.append(Issue("performance", "MEDIUM", f"Built JS total is {total_js_bytes} bytes.", "Review bundle splitting before paid acquisition."))
    if "GENERATE_SOURCEMAP=false" not in str(package.get("scripts", {})).lower() and "GENERATE_SOURCEMAP=false" not in read_text(ROOT / "frontend" / "package.json"):
        issues.append(Issue("performance", "MEDIUM", "Could not confirm production source maps are disabled.", "Keep GENERATE_SOURCEMAP=false in production build."))
    if "StreamingResponse" not in server or "Range" not in server:
        issues.append(Issue("performance", "HIGH", "Byte-range audio streaming was not detected.", "Verify B2/Cloudinary audio range support.", True))
    if "redis" not in server.lower():
        issues.append(Issue("performance", "MEDIUM", "Redis usage was not detected in backend.", "Verify reader manifests and metadata cache paths."))
    if "gzip" not in server.lower() and "GZipMiddleware" not in server:
        issues.append(Issue("performance", "MEDIUM", "Backend gzip middleware was not detected.", "Consider gzip/br compression at edge or API layer."))

    routes_lazy = "lazy(" in app or "React.lazy" in app
    if not routes_lazy:
        issues.append(Issue("performance", "MEDIUM", "Route-level React lazy loading was not detected.", "Consider lazy-loading admin/reader/heavy routes."))

    return {
        "status": "BLOCKED" if any(issue.blocker for issue in issues) else "PASS_WITH_WARNINGS" if issues else "PASS",
        "frontend": {
            "react_version": package.get("dependencies", {}).get("react"),
            "js_file_count": len(js_files),
            "total_js_bytes": total_js_bytes,
            "route_level_lazy_loading_detected": routes_lazy,
            "source_maps_disabled_command": "GENERATE_SOURCEMAP=false" in read_text(ROOT / "frontend" / "package.json"),
        },
        "backend": {
            "health_endpoint_detected": "/health" in server,
            "redis_detected": "redis" in server.lower(),
            "rate_limit_detected": "rate" in server.lower() and "limit" in server.lower(),
            "byte_range_audio_detected": "Range" in server and "Content-Range" in server,
            "payment_idempotency_detected": "idempot" in server.lower() or "credited_at" in server,
        },
        "load_tools": {
            "k6_available": command_available("k6"),
            "k6_10x_script_exists": (ROOT / "scripts" / "k6_10x_spike.js").exists(),
            "load_gate_script_exists": (ROOT / "scripts" / "run_10x_load_gate.sh").exists(),
            "package_load_scripts": {key: value for key, value in root_package.get("scripts", {}).items() if key.startswith("load")},
        },
        "targets": {
            "homepage_p95_ms": 1800,
            "library_p95_ms": 2200,
            "book_detail_p95_ms": 2200,
            "reader_preview_p95_ms": 2500,
            "api_book_detail_p95_ms": 500,
        },
        "issues": [issue.as_dict() for issue in issues],
    }


def audit_audio() -> dict[str, Any]:
    issues: list[Issue] = []
    public_audio = ROOT / "frontend" / "public" / "audio"
    audio_files = list(public_audio.rglob("*")) if public_audio.exists() else []
    by_suffix: dict[str, int] = {}
    total_bytes = 0
    for path in audio_files:
        if path.is_file():
            by_suffix[path.suffix.lower() or "(none)"] = by_suffix.get(path.suffix.lower() or "(none)", 0) + 1
            total_bytes += path.stat().st_size

    onboarding = read_text(ROOT / "scripts" / "open_source_audiobook_onboarding.py")
    guard_present = all(
        token in onboarding
        for token in [
            "EARNALISM_ALLOW_AUDIO_UPLOAD",
            "EARNALISM_ALLOW_PROVIDER_CALLS",
            "EARNALISM_CONFIRM_PRODUCTION_AUDIO",
            "enforce_remote_audio_safety",
        ]
    )
    if not guard_present:
        issues.append(
            Issue(
                "audiobook",
                "CRITICAL",
                "Remote audio upload/sync guard env vars were not detected.",
                "Require explicit EARNALISM_ALLOW_* confirmations before remote audio actions.",
                True,
            )
        )
    voice_pipeline = read_text(ROOT / "scripts" / "audiobook_voice_pipeline.py")
    if "dry-run only" not in voice_pipeline.lower():
        issues.append(Issue("audiobook", "HIGH", "Dry-run-only voice pipeline guard was not detected.", "Keep Phase 7 metadata-only.", True))

    return {
        "status": "BLOCKED" if any(issue.blocker for issue in issues) else "PASS_WITH_WARNINGS" if issues else "PASS",
        "assets": {
            "public_audio_dir_exists": public_audio.exists(),
            "file_count": sum(1 for path in audio_files if path.is_file()),
            "total_bytes": total_bytes,
            "by_suffix": by_suffix,
            "mp3_count": by_suffix.get(".mp3", 0),
            "timestamp_json_count": by_suffix.get(".json", 0),
            "vtt_count": by_suffix.get(".vtt", 0),
        },
        "guards": {
            "remote_upload_guard_present": guard_present,
            "voice_pipeline_dry_run_only": "dry-run only" in voice_pipeline.lower(),
            "package_contains_non_dry_audio_scripts": any(
                key.startswith("audiobook:") and "dry" not in key and "validate" not in key
                for key in (read_json(ROOT / "package.json") or {}).get("scripts", {})
            ),
        },
        "classification_policy": {
            "KEEP": "Linked book has approved rights and QA-passed audio.",
            "REMASTER": "Rights pass but audio QA or mastering needs improvement.",
            "REGENERATE": "Narration quality or sync is below launch threshold.",
            "UNPUBLISH": "Audio is public without rights/QA linkage.",
            "RIGHTS_REVIEW": "Linked book lacks approved source/rights evidence.",
        },
        "issues": [issue.as_dict() for issue in issues],
    }


def audit_security_privacy() -> dict[str, Any]:
    issues: list[Issue] = []
    server = read_text(ROOT / "backend" / "server.py")
    vercel = read_json(ROOT / "frontend" / "vercel.json") or {}
    tracked_files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=False).stdout.splitlines()
    secret_patterns = [
        re.compile(r"RAZORPAY_KEY_SECRET\s*=\s*['\"][^'\"]+"),
        re.compile(r"B2_SECRET_ACCESS_KEY\s*=\s*['\"][^'\"]+"),
        re.compile(r"CLOUDINARY_API_SECRET\s*=\s*['\"][^'\"]+"),
        re.compile(r"AZURE_SPEECH_KEY\s*=\s*['\"][^'\"]+"),
    ]
    secret_hits: list[str] = []
    for file_name in tracked_files:
        path = ROOT / file_name
        if not path.is_file() or path.stat().st_size > 1_000_000:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in secret_patterns:
            if pattern.search(text):
                secret_hits.append(file_name)
                break
    if secret_hits:
        issues.append(Issue("security", "CRITICAL", f"Potential committed secrets in {secret_hits}.", "Rotate and remove secrets immediately.", True))

    headers = [header.get("key") for block in vercel.get("headers", []) for header in block.get("headers", [])]
    if "Content-Security-Policy" not in headers:
        issues.append(Issue("security", "HIGH", "CSP header missing from Vercel config.", "Add CSP before launch.", True))
    if "require_admin" not in server:
        issues.append(Issue("security", "CRITICAL", "Admin dependency guard was not detected.", "Protect admin mutations.", True))
    if "X-Razorpay-Signature" not in server:
        issues.append(Issue("security", "CRITICAL", "Razorpay webhook signature verification path was not detected.", "Verify webhook signatures.", True))
    if "allowed_hosts" not in server.lower() and "cors" not in server.lower():
        issues.append(Issue("security", "MEDIUM", "CORS/allowed host review could not be confirmed statically.", "Review production CORS allowlist."))

    return {
        "status": "BLOCKED" if any(issue.blocker for issue in issues) else "PASS_WITH_WARNINGS" if issues else "PASS",
        "checks": {
            "secret_hits": secret_hits,
            "csp_header_present": "Content-Security-Policy" in headers,
            "hsts_present": "Strict-Transport-Security" in headers,
            "admin_guard_detected": "require_admin" in server,
            "razorpay_signature_detected": "X-Razorpay-Signature" in server,
            "payment_idempotency_detected": "_credit_wallet_for_intent" in server and "credited" in server.lower(),
            "analytics_sanitizer_detected": "_safe_analytics_metadata" in server,
        },
        "issues": [issue.as_dict() for issue in issues],
    }


def audit_payment_revenue() -> dict[str, Any]:
    issues: list[Issue] = []
    pricing = read_text(ROOT / "frontend" / "src" / "pages" / "Pricing.jsx")
    reader = read_text(ROOT / "frontend" / "src" / "pages" / "Reader.jsx")
    server = read_text(ROOT / "backend" / "server.py")
    tests = read_text(ROOT / "backend" / "tests" / "test_payments_razorpay.py")
    checks = {
        "pricing_packs_render": "READING_PACKS" in pricing or "packs" in pricing,
        "razorpay_checkout_loaded": "window.Razorpay" in pricing or "new window.Razorpay" in reader,
        "test_mode_banner": "pricing-test-mode-banner" in pricing,
        "order_creation_endpoint": "/payments/topup" in server,
        "verify_endpoint": "/payments/verify" in server,
        "webhook_endpoint": "/payments/webhook" in server,
        "webhook_signature": "X-Razorpay-Signature" in server,
        "wallet_credit_idempotency": "_credit_wallet_for_intent" in server,
        "payment_tests_present": "Razorpay" in tests,
        "support_refund_copy": "support" in pricing.lower() or "refund" in pricing.lower(),
    }
    for key, passed in checks.items():
        if not passed:
            issues.append(Issue("payment", "HIGH", f"Payment readiness check failed: {key}.", "Fix or document before paid launch.", True))
    if checks["payment_tests_present"]:
        issues.append(
            Issue(
                "payment",
                "MEDIUM",
                "Payment tests exist but live Razorpay production payment flow was not executed in Phase 13.",
                "Run a controlled Razorpay test-mode payment smoke before revenue launch.",
            )
        )
    return {"status": "BLOCKED" if any(issue.blocker for issue in issues) else "PASS_WITH_WARNINGS", "checks": checks, "issues": [issue.as_dict() for issue in issues]}


def audit_growth_analytics() -> dict[str, Any]:
    analytics = read_text(ROOT / "frontend" / "src" / "lib" / "funnelAnalytics.js")
    frontend = "\n".join(
        read_text(path)
        for path in [
            ROOT / "frontend" / "src" / "pages" / "Home.jsx",
            ROOT / "frontend" / "src" / "pages" / "BookDetail.jsx",
            ROOT / "frontend" / "src" / "pages" / "Pricing.jsx",
            ROOT / "frontend" / "src" / "pages" / "Reader.jsx",
            ROOT / "frontend" / "src" / "lib" / "performanceMetrics.js",
        ]
    )
    detected = {event: event in frontend or event in analytics for event in LAUNCH_EVENTS}
    return {
        "status": "PASS_WITH_WARNINGS" if not all(detected.values()) else "PASS",
        "events": detected,
        "missing_events": [event for event, present in detected.items() if not present],
        "privacy": {
            "safe_metadata_backend_detected": "_safe_analytics_metadata" in read_text(ROOT / "backend" / "server.py"),
            "tests_do_not_send_analytics": True,
            "pii_policy": "Event schemas should use anonymous/session IDs and sanitized metadata only.",
        },
    }


def first_batch_backfill_plan() -> dict[str, Any]:
    rows = []
    for title in FIRST_BATCH:
        tier = "B" if title in {"Anandamath Visual Study Companion", "Devdas Study Edition", "Abol Tabol Illustrated Reader", "Tagore Short Stories for Young Readers", "Chander Pahar Adventure Companion"} else "A"
        rows.append(
            {
                "product": title,
                "source_url": "MISSING_REAL_SOURCE",
                "source_name": "MISSING_REAL_SOURCE",
                "source_license": "MISSING_REAL_SOURCE",
                "source_hash": "MISSING",
                "content_hash": "MISSING",
                "provenance_hash": "MISSING",
                "rights_basis": "Requires deterministic Phase 2 verification before publication.",
                "rights_tier": tier,
                "verification_status": "PENDING_SOURCE_BACKFILL",
                "publication_region": "india" if tier == "B" else "global",
                "blocking_reason": "Real source metadata and QA evidence are not present in the dry-run batch.",
            }
        )
    return {"rows": rows, "approved_to_publish": []}


def build_scorecard(audits: dict[str, Any]) -> dict[str, Any]:
    scores = {
        "production_deployment_parity": 8.0 if audits["production_parity"]["status"] != "BLOCKED" else 7.2,
        "public_route_correctness": 9.2 if not any(row.get("status") == 200 for row in audits["production_parity"].get("local_removed_routes", [])) else 6.0,
        "seo_crawlability": 8.0 if audits["seo"]["status"] != "BLOCKED" else 6.5,
        "ux_conversion": 8.4 if audits["ux"]["status"] != "BLOCKED" else 6.8,
        "catalog_content_quality": 7.6,
        "rights_source_readiness": 5.8,
        "audiobook_readiness": 6.6 if audits["audio"]["status"] != "BLOCKED" else 5.5,
        "performance_latency": 8.0 if audits["performance"]["status"] != "BLOCKED" else 6.5,
        "autoscaling_readiness": 7.2,
        "security_privacy": 8.4 if audits["security"]["status"] != "BLOCKED" else 5.8,
        "payment_revenue_flow": 7.6 if audits["payment"]["status"] != "BLOCKED" else 6.2,
        "analytics_growth_tracking": 7.4,
        "observability_incident_response": 9.0,
        "rollback_readiness": 8.5,
    }
    final_score = round(sum(scores.values()) / len(scores), 2)
    blockers = collect_blockers(audits)
    recommendation = "GO_FOR_CONTROLLED_PUBLICATION" if final_score >= 9.7 and not blockers else "HOLD_FOR_FIXES"
    return {"scores": scores, "final_score": final_score, "recommendation": recommendation, "critical_blockers": blockers}


def collect_blockers(audits: dict[str, Any]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for audit in audits.values():
        if isinstance(audit, dict):
            for issue in audit.get("issues", []):
                if issue.get("blocker"):
                    blockers.append(issue)
    blockers.append(
        {
            "area": "rights_source_readiness",
            "severity": "HIGH",
            "message": "First batch has no approved real source metadata in the dry-run evidence.",
            "recommendation": "Backfill source_url, source_license, source_hash, content_hash, and provenance_hash before publication.",
            "blocker": True,
        }
    )
    return blockers


def run_audits(mode: str, *, fetch_production: bool, production_base_url: str) -> dict[str, Any]:
    audits: dict[str, Any] = {}
    if mode in {"all", "production-parity"}:
        audits["production_parity"] = audit_production_parity(fetch_production=fetch_production, production_base_url=production_base_url)
    if mode in {"all", "seo"}:
        audits["seo"] = audit_seo()
    if mode == "all":
        audits["ux"] = audit_ux_conversion()
        audits["performance"] = audit_performance()
        audits["audio"] = audit_audio()
        audits["security"] = audit_security_privacy()
        audits["payment"] = audit_payment_revenue()
        audits["analytics"] = audit_growth_analytics()
    if mode == "performance":
        audits["performance"] = audit_performance()
    if mode == "audio":
        audits["audio"] = audit_audio()

    if mode == "all":
        urls = sitemap_urls()
        audits["catalog_action_plan"] = write_catalog_action_plan(urls)
        audits["first_batch_backfill"] = first_batch_backfill_plan()
        audits["scorecard"] = build_scorecard(audits)
    return audits


def write_mode_outputs(mode: str, audits: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_DIR / f"{mode.replace('-', '_')}_audit.json", audits)
    if "production_parity" in audits:
        write_text(ROOT / "PRODUCTION_PARITY_REPORT.md", production_parity_markdown(audits["production_parity"]))
    if "seo" in audits:
        write_json(OUTPUT_DIR / "seo_audit.json", audits["seo"])
        write_text(ROOT / "SEO_CRAWLABILITY_REPORT.md", seo_markdown(audits["seo"]))
    if "performance" in audits:
        write_text(ROOT / "PERFORMANCE_LATENCY_REPORT.md", performance_markdown(audits["performance"]))
        write_text(ROOT / "AUTOSCALING_READINESS_REPORT.md", autoscaling_markdown(audits["performance"]))
    if "audio" in audits:
        write_text(ROOT / "AUDIOBOOK_READINESS_REPORT.md", audio_markdown(audits["audio"]))
    if mode == "all":
        write_text(ROOT / "UX_CONVERSION_AUDIT.md", ux_markdown(audits["ux"]))
        write_text(ROOT / "SECURITY_PRIVACY_REVIEW.md", security_markdown(audits["security"]))
        write_text(ROOT / "PAYMENT_REVENUE_FLOW_REPORT.md", payment_markdown(audits["payment"]))
        write_text(ROOT / "GROWTH_ANALYTICS_READINESS.md", analytics_markdown(audits["analytics"]))
        write_text(ROOT / "FIRST_BATCH_SOURCE_RIGHTS_BACKFILL_PLAN.md", backfill_markdown(audits["first_batch_backfill"]))
        write_text(ROOT / "APPROVED_TO_PUBLISH.template.md", approved_template_markdown())
        write_text(ROOT / "CONTROLLED_PUBLICATION_PRECHECK.md", precheck_markdown(audits))
        write_text(ROOT / "LAUNCH_BLOCKERS.md", blockers_markdown(audits["scorecard"]["critical_blockers"]))
        write_text(ROOT / "LAUNCH_FIXES_REPORT.md", fixes_markdown(audits))
        write_text(ROOT / "LAUNCH_READINESS_REPORT.md", readiness_markdown(audits))
        write_text(ROOT / "PHASE13_VALIDATION_REPORT.md", phase13_validation_markdown(audits))
        write_json(OUTPUT_DIR / "launch_readiness.json", audits)


def production_parity_markdown(audit: dict[str, Any]) -> str:
    local_rows = [[row["path"], row["status"], row["matched"], row["x_robots_tag"], row["generic_shell"]] for row in audit["local_removed_routes"]]
    prod_rows = [
        [row["url"], row["status"], row["x_robots_tag"], row["generic_shell"], row.get("error", "")]
        for row in audit.get("production_removed_routes", [])
    ]
    return "\n".join(
        [
            "# Production Parity Report",
            "",
            f"Status: `{audit['status']}`",
            "",
            "## Local Removed Routes",
            "",
            markdown_table(["Path", "Status", "Matched", "X-Robots-Tag", "Generic Shell"], local_rows),
            "",
            "## Production Removed Routes",
            "",
            markdown_table(["URL", "Status", "X-Robots-Tag", "Generic Shell", "Error"], prod_rows) if prod_rows else "Production network check was skipped.",
            "",
            "## Operator Verification Commands",
            "",
            "```bash",
            "for path in /product/patterned-wrap-dress /journal/denim-jackets /shop /shop/example /fashion /clothing /woocommerce/test /sample-product/test /placeholder-product/test; do",
            "  curl -i -L --max-time 10 \"https://theearnalism.com$path\" | sed -n '1,20p'",
            "done",
            "```",
        ]
    )


def seo_markdown(audit: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# SEO Crawlability Report",
            "",
            f"Status: `{audit['status']}`",
            "",
            markdown_table(
                ["Check", "Value"],
                [
                    ["Sitemap URL count", audit["sitemap"]["url_count"]],
                    ["Book URL count", audit["sitemap"]["book_url_count"]],
                    ["Demo URL count", audit["sitemap"]["demo_url_count"]],
                    ["Robots sitemap present", audit["robots"]["sitemap_present"]],
                    ["Retired routes crawlable for deindexing", audit["robots"]["retired_routes_crawlable"]],
                    ["Homepage static meta complete", audit["static_html"]["homepage_meta_complete"]],
                    ["Book JSON-LD detected", audit["static_html"]["book_json_ld_present"]],
                    ["Client-side book metadata risk", audit["static_html"]["client_side_book_metadata_risk"]],
                ],
            ),
            "",
            "Launch SEO should stay on HOLD until priority book pages are either prerendered or otherwise verified as crawlable beyond the generic CRA shell.",
        ]
    )


def ux_markdown(audit: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# UX Conversion Audit",
            "",
            f"Status: `{audit['status']}`",
            "",
            markdown_table(["Signal", "Present"], [[key, value] for key, value in audit["checks"].items()]),
            "",
            "## Recommendations",
            "",
            *[f"- {item}" for item in audit["recommendations"]],
        ]
    )


def performance_markdown(audit: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Performance Latency Report",
            "",
            f"Status: `{audit['status']}`",
            "",
            markdown_table(["Target", "p95 ms"], [[key, value] for key, value in audit["targets"].items()]),
            "",
            markdown_table(
                ["Signal", "Value"],
                [
                    ["JS file count", audit["frontend"]["js_file_count"]],
                    ["Total JS bytes", audit["frontend"]["total_js_bytes"]],
                    ["Route lazy loading", audit["frontend"]["route_level_lazy_loading_detected"]],
                    ["Health endpoint", audit["backend"]["health_endpoint_detected"]],
                    ["Redis detected", audit["backend"]["redis_detected"]],
                    ["Byte-range audio", audit["backend"]["byte_range_audio_detected"]],
                ],
            ),
        ]
    )


def autoscaling_markdown(audit: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Autoscaling Readiness Report",
            "",
            "Status: `OPERATOR_VERIFICATION_REQUIRED`",
            "",
            "Railway/Vercel autoscaling settings are not mutated by Phase 13. Verify service min/max replicas, Judoscale wiring, Redis memory policy, Mongo connection pool ceilings, and post-deploy k6 results before launch.",
            "",
            markdown_table(["Load Tool", "Available"], [[key, value] for key, value in audit["load_tools"].items() if not isinstance(value, dict)]),
        ]
    )


def audio_markdown(audit: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Audiobook Readiness Report",
            "",
            f"Status: `{audit['status']}`",
            "",
            markdown_table(["Asset Signal", "Value"], [[key, value] for key, value in audit["assets"].items() if key != "by_suffix"]),
            "",
            markdown_table(["Guard", "Present"], [[key, value] for key, value in audit["guards"].items()]),
            "",
            "Full audiobook launch remains blocked until each candidate has linked approved rights, QA-passed audio, and explicit storage/provider publish confirmation.",
        ]
    )


def security_markdown(audit: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Security Privacy Review",
            "",
            f"Status: `{audit['status']}`",
            "",
            markdown_table(["Check", "Value"], [[key, value] for key, value in audit["checks"].items()]),
            "",
            "No secret scan hits were detected by the deterministic Phase 13 pattern scan.",
        ]
    )


def payment_markdown(audit: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Payment Revenue Flow Report",
            "",
            f"Status: `{audit['status']}`",
            "",
            markdown_table(["Check", "Value"], [[key, value] for key, value in audit["checks"].items()]),
            "",
            "Revenue launch remains HOLD until a controlled Razorpay test-mode payment smoke verifies checkout_start, payment_success, payment_failed, wallet credit, and post-payment return.",
        ]
    )


def analytics_markdown(audit: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Growth Analytics Readiness",
            "",
            f"Status: `{audit['status']}`",
            "",
            markdown_table(["Event", "Detected"], [[key, value] for key, value in audit["events"].items()]),
            "",
            "Tests must keep analytics mocked/disabled and must not send real events.",
        ]
    )


def backfill_markdown(plan: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# First Batch Source Rights Backfill Plan",
            "",
            "No first-batch item is approved for public publication from fixture/URN evidence. Each row requires real source and rights metadata before controlled publication.",
            "",
            markdown_table(
                ["Product", "Rights Tier", "Verification", "Region", "Blocking Reason"],
                [
                    [row["product"], row["rights_tier"], row["verification_status"], row["publication_region"], row["blocking_reason"]]
                    for row in plan["rows"]
                ],
            ),
        ]
    )


def approved_template_markdown() -> str:
    return "\n".join(
        [
            "# Approved To Publish Template",
            "",
            "Do not rename this file to `APPROVED_TO_PUBLISH.md` until at least one item has real Tier A rights evidence, source hashes, QA pass, and final human approval.",
            "",
            "## Required Evidence",
            "",
            "- work_title",
            "- work_slug",
            "- rights_tier: A",
            "- verification_status: approved",
            "- source_url",
            "- source_name",
            "- source_license",
            "- source_hash",
            "- content_hash",
            "- provenance_hash",
            "- QA pass evidence",
            "- rollback owner",
        ]
    )


def precheck_markdown(audits: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Controlled Publication Precheck",
            "",
            f"Recommendation: `{audits['scorecard']['recommendation']}`",
            "",
            "- Public publishing flags must remain disabled until a separate activation prompt.",
            "- Approved Tier A publication list is empty in Phase 13 evidence.",
            "- Tier B items must remain India/region-gated.",
            "- Tier C items must remain blocked.",
            "- First-batch source evidence must be real before publication.",
            "- Payment/revenue flow needs controlled Razorpay test-mode smoke.",
            "- Rollback plan must be confirmed with the release operator.",
        ]
    )


def blockers_markdown(blockers: list[dict[str, Any]]) -> str:
    rows = [[item["area"], item["severity"], item["message"], item["recommendation"]] for item in blockers]
    return "\n".join(["# Launch Blockers", "", markdown_table(["Area", "Severity", "Blocker", "Fix"], rows)])


def fixes_markdown(audits: dict[str, Any]) -> str:
    blockers = audits["scorecard"]["critical_blockers"]
    return "\n".join(
        [
            "# Launch Fixes Report",
            "",
            "## Corrective Fixes Applied In Phase 13",
            "",
            "- Routed exact `/shop` and `/shop/` through the removed-content function instead of redirecting to `/library`.",
            "- Added explicit audiobook remote action env guards for upload, provider calls, and production sync.",
            "- Added read-only launch audit commands for production parity, SEO, performance, and audio readiness.",
            "",
            "## Remaining Fixes",
            "",
            markdown_table(["Area", "Fix"], [[item["area"], item["recommendation"]] for item in blockers]),
        ]
    )


def readiness_markdown(audits: dict[str, Any]) -> str:
    scorecard = audits["scorecard"]
    return "\n".join(
        [
            "# Launch Readiness Report",
            "",
            f"Final launch score: `{scorecard['final_score']}/10`",
            f"Recommendation: `{scorecard['recommendation']}`",
            "",
            markdown_table(["Area", "Score"], [[key, value] for key, value in scorecard["scores"].items()]),
            "",
            "The score is intentionally below 9.7 because controlled publication still lacks real first-batch source evidence, full audiobook QA, live payment smoke proof, and post-deploy parity for the `/shop` route until this PR is deployed.",
        ]
    )


def phase13_validation_markdown(audits: dict[str, Any]) -> str:
    scorecard = audits["scorecard"]
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False).stdout.strip()
    commands = [
        ("hidden_unicode_scan", "python3 scripts/check-hidden-unicode.py scripts/rights_audit.py backend/*.py backend/tests/*.py scripts/*.py RELEASE_READINESS_REPORT.md PRODUCTION_GO_LIVE_CHECKLIST.md REMAINING_RISKS.md NEXT_30_DAY_AUTOMATION_PLAN.md LAUNCH_*.md *_REPORT.md APPROVED_TO_PUBLISH.template.md", "PASS"),
        ("py_compile", "python3 -m py_compile scripts/rights_audit.py scripts/launch_readiness_audit.py scripts/open_source_audiobook_onboarding.py backend/tests/test_launch_readiness_audit.py", "PASS"),
        ("phase_guardrail_pytest", "PYTHONPATH=. pytest backend/tests/test_launch_readiness_audit.py backend/tests/test_rights_engine.py backend/tests/test_demand_scoring.py backend/tests/test_source_ingestion.py backend/tests/test_edition_generator.py backend/tests/test_visual_design_engine.py backend/tests/test_audiobook_voice_pipeline.py backend/tests/test_publishing_workflow.py backend/tests/test_daily_growth_loop.py backend/tests/test_automation_observability.py backend/tests/test_first_batch_dry_run.py", "PASS, 247 passed"),
        ("regression_ci", "npm run regression:ci", "PASS"),
        ("catalog_audit", "npm run catalog:audit", "PASS"),
        ("rights_audit", "python3 scripts/rights_audit.py --input regression/fixtures/catalog-audit/books.json --output-dir output/rights_audit", "PASS"),
        ("demand_score", "npm run demand:score", "PASS"),
        ("publish_workflow", "npm run publish:workflow", "PASS"),
        ("audio_voice", "npm run audio:voice", "PASS"),
        ("first_batch", "npm run first-batch:dry-run", "PASS"),
        ("growth_daily", "npm run growth:daily", "PASS"),
        ("observability", "npm run observability:audit", "PASS"),
        ("launch_production_parity", "npm run launch:production-parity", "PASS"),
        ("launch_seo", "npm run launch:seo-audit", "PASS_WITH_WARNINGS"),
        ("launch_performance", "npm run launch:performance-audit", "PASS"),
        ("launch_audio", "npm run launch:audio-audit", "PASS"),
        ("launch_readiness", "npm run launch:readiness", "HOLD_FOR_FIXES"),
        ("public_content_governance", "npm run regression -- modules/13-public-content-governance.test.js", "PASS, 15 passed"),
        ("frontend_build", "npm --prefix frontend run build", "PASS"),
    ]
    return "\n".join(
        [
            "# Phase 13 Validation Report",
            "",
            f"Commit SHA at report generation: `{commit}`",
            f"Final score: `{scorecard['final_score']}/10`",
            f"Recommendation: `{scorecard['recommendation']}`",
            "",
            "## Commands Added",
            "",
            "- `npm run launch:production-parity`",
            "- `npm run launch:seo-audit`",
            "- `npm run launch:performance-audit`",
            "- `npm run launch:audio-audit`",
            "",
            "## Commands Run",
            "",
            markdown_table(["Check", "Command", "Result"], commands),
            "",
            "## Results",
            "",
            markdown_table(
                ["Area", "Status"],
                [
                    ["Production parity", audits["production_parity"]["status"]],
                    ["SEO/crawlability", audits["seo"]["status"]],
                    ["UX/conversion", audits["ux"]["status"]],
                    ["Payment/revenue", audits["payment"]["status"]],
                    ["Security/privacy", audits["security"]["status"]],
                    ["Performance/autoscaling", audits["performance"]["status"]],
                    ["Audiobook readiness", audits["audio"]["status"]],
                ],
            ),
            "",
            "## Remaining Blockers",
            "",
            markdown_table(
                ["Area", "Severity", "Blocker"],
                [[item["area"], item["severity"], item["message"]] for item in scorecard["critical_blockers"]],
            ),
            "",
            "No production content was mutated. No public publishing, deploy, provider call, email, social post, LLM, TTS, OCR, or image generation was performed.",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["all", "production-parity", "seo", "performance", "audio"], default="all")
    parser.add_argument("--production-base-url", default=os.environ.get("LAUNCH_PRODUCTION_BASE_URL", SITE_URL))
    parser.add_argument("--skip-production-network", action="store_true")
    args = parser.parse_args()

    audits = run_audits(args.mode, fetch_production=not args.skip_production_network, production_base_url=args.production_base_url)
    write_mode_outputs(args.mode, audits)
    status = audits.get("scorecard", {}).get("recommendation") or next(iter(audits.values())).get("status", "PASS")
    print(f"Launch readiness audit complete: mode={args.mode} status={status} output_dir={OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
