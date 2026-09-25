#!/usr/bin/env python3
"""Fail-closed, semantic raw-HTML canary for deployed static SEO snapshots."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "launch"
DEFAULT_BASE_URL = "https://theearnalism.com"
CANONICAL_SITE_URL = "https://theearnalism.com"
ACCESS_COPY = "The first 3 canonical pages are available as a free preview. A Reading Pass is required from page 4; paid checkout and audiobooks are unavailable in this launch."
FORBIDDEN_COPY = (
    "Chapter 1 free", "First chapter free", "Chapter 1 is on us", "Preview chapter unlocked",
    "First 3 minutes free", "First 180 seconds free", "Free audiobook preview",
    "Free listening sample", "Listen free",
)
GENERIC_HOME_MARKER = "a library made for lingering"
RAW_MEDIA_URL = re.compile(r"https?://[^\"'\s<>]+\.(?:mp3|m4a|aac|wav)(?:[?\"'\s<>]|$)", re.I)

ROUTES = {
    "/book/a-ghost-story": {"kind": "book", "canonical": "/book/a-ghost-story", "robots": "index,follow", "title": "A Ghost Story"},
    "/book/the-tell-tale-heart": {"kind": "book", "canonical": "/book/the-tell-tale-heart", "robots": "index,follow", "title": "The Tell-Tale Heart"},
    "/book/radharani": {"kind": "book", "canonical": "/book/radharani", "robots": "index,follow", "title": "রাধারাণী"},
    "/book/a-white-heron": {"kind": "book", "canonical": "/book/a-white-heron", "robots": "index,follow", "title": "A White Heron"},
    "/book/the-gift-of-the-magi": {"kind": "book", "canonical": "/book/the-gift-of-the-magi", "robots": "index,follow", "title": "The Gift of the Magi"},
    "/book/the-canterville-ghost": {"kind": "book", "canonical": "/book/the-canterville-ghost", "robots": "index,follow", "title": "The Canterville Ghost"},
    "/library": {"kind": "library", "canonical": "/library", "robots": "index,follow"},
    "/pricing": {"kind": "pricing", "canonical": "/pricing", "robots": "noindex,follow"},
    "/reader/a-ghost-story": {"kind": "reader", "canonical": "/book/a-ghost-story", "robots": "noindex,follow", "title": "A Ghost Story"},
    "/reader/the-tell-tale-heart": {"kind": "reader", "canonical": "/book/the-tell-tale-heart", "robots": "noindex,follow", "title": "The Tell-Tale Heart"},
    "/reader/radharani": {"kind": "reader", "canonical": "/book/radharani", "robots": "noindex,follow", "title": "রাধারাণী"},
    "/reader/a-white-heron": {"kind": "reader", "canonical": "/book/a-white-heron", "robots": "noindex,follow", "title": "A White Heron"},
    "/reader/the-gift-of-the-magi": {"kind": "reader", "canonical": "/book/the-gift-of-the-magi", "robots": "noindex,follow", "title": "The Gift of the Magi"},
    "/reader/the-canterville-ghost": {"kind": "reader", "canonical": "/book/the-canterville-ghost", "robots": "noindex,follow", "title": "The Canterville Ghost"},
    "/book/dracula": {"kind": "held"},
    "/reader/dracula": {"kind": "held"},
    "/book/yugalanguriya": {"kind": "held"},
    "/reader/yugalanguriya": {"kind": "held"},
    "/my-library": {"kind": "private_library", "canonical": "/my-library", "robots": "noindex,nofollow"},
}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", unescape(value or ""))
    value = value.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", value).strip().casefold()


def canonical_url(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/") or "/", "", ""))


class HtmlFacts(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: list[str] = []
        self.h1: list[str] = []
        self.text: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.canonical = ""
        self.description = ""
        self.robots = ""
        self._in_title = False
        self._h1_depth = 0
        self._link_href = ""
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.casefold(): value or "" for key, value in attrs}
        if tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._h1_depth += 1
        elif tag == "meta":
            name = attributes.get("name", "").casefold()
            if name == "description":
                self.description = attributes.get("content", "")
            elif name == "robots":
                self.robots = attributes.get("content", "")
        elif tag == "link" and "canonical" in attributes.get("rel", "").casefold().split():
            self.canonical = attributes.get("href", "")
        elif tag == "a":
            self._link_href = attributes.get("href", "")
            self._link_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "h1" and self._h1_depth:
            self._h1_depth -= 1
        elif tag == "a" and self._link_href:
            self.links.append((self._link_href, " ".join(self._link_text)))
            self._link_href, self._link_text = "", []

    def handle_data(self, data: str) -> None:
        self.text.append(data)
        if self._in_title:
            self.title.append(data)
        if self._h1_depth:
            self.h1.append(data)
        if self._link_href:
            self._link_text.append(data)


def facts_for(html: str) -> HtmlFacts:
    facts = HtmlFacts()
    facts.feed(html)
    facts.close()
    return facts


def has_access_contract(text: str) -> bool:
    return normalize(ACCESS_COPY) in text


def has_pricing_continuation(facts: HtmlFacts) -> bool:
    return any(urlsplit(href).path == "/pricing" and "reading pass" in normalize(label) for href, label in facts.links)


def fetch_raw_html(base_url: str, route: str, timeout: int) -> tuple[int, dict[str, str], str, str]:
    url = urljoin(base_url.rstrip("/") + "/", route.lstrip("/"))
    request = Request(url, headers={"User-Agent": "EarnalismStaticSeoCanary/2.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers.items()), response.read().decode("utf-8", errors="replace"), response.url
    except HTTPError as error:
        return error.code, dict(error.headers.items()), error.read().decode("utf-8", errors="replace"), error.url
    except URLError as error:
        return 0, {}, "", f"{url} ({error})"


def inspect_route(route: str, policy: dict[str, str], status: int, headers: dict[str, str], html: str, url: str) -> dict[str, object]:
    facts = facts_for(html)
    text, title, description, h1 = normalize(" ".join(facts.text)), normalize(" ".join(facts.title)), normalize(facts.description), normalize(" ".join(facts.h1))
    failures: list[str] = []
    if policy["kind"] == "held":
        if status != 404:
            failures.append(f"held route must be 404, got {status}")
        if "read the complete edition free" in text or has_access_contract(text):
            failures.append("held route exposes released-book access copy")
        return {"route": route, "url": url, "status_code": status, "failures": failures, "result": "PASS" if not failures else "FAIL"}
    expected_canonical = canonical_url(urljoin(CANONICAL_SITE_URL, policy["canonical"]))
    if status != 200:
        failures.append(f"expected status 200, got {status}")
    if not title or "earnalism" not in title:
        failures.append("missing route-specific Earnalism title")
    if not description:
        failures.append("missing route-specific description")
    if canonical_url(facts.canonical) != expected_canonical:
        failures.append(f"wrong canonical URL: expected {expected_canonical}, got {facts.canonical or 'missing'}")
    if normalize(facts.robots) != normalize(policy["robots"]):
        failures.append(f"wrong robots directive: expected {policy['robots']}, got {facts.robots or 'missing'}")
    if GENERIC_HOME_MARKER in text:
        failures.append("generic Home fallback is present")
    if policy["kind"] in {"book", "reader", "library"} and not has_access_contract(text):
        failures.append("missing approved free-reading contract")
    if "listening requires an active reading pass" in text or has_pricing_continuation(facts):
        failures.append("stale paid-access continuation is present")
    for phrase in FORBIDDEN_COPY:
        if normalize(phrase) in text:
            failures.append(f"forbidden phrase present: {phrase}")
    if RAW_MEDIA_URL.search(html):
        failures.append("raw provider or storage audio URL is present")

    if policy["kind"] == "book":
        expected_title = normalize(policy["title"])
        if expected_title not in title or expected_title not in h1:
            failures.append("missing released-book route identity")
        if expected_title not in description or not has_access_contract(description):
            failures.append("missing route-specific free-reading description")
        if "read the complete edition free" not in text:
            failures.append("missing complete free-reading CTA")
        if not re.search(r'"isAccessibleForFree"\s*:\s*true', html, re.I):
            failures.append("Book structured data must mark full access free")
        if any("listen" in normalize(label) for _, label in facts.links):
            failures.append("book exposes an active Listen CTA")
    elif policy["kind"] == "pricing":
        if "reading pass" not in title and "pricing" not in title:
            failures.append("missing route-specific Pricing or Reading Pass identity")
        if "paid checkout are unavailable" not in description:
            failures.append("missing disabled-checkout description")
    elif policy["kind"] == "library" and "library" not in title:
        failures.append("missing Library route identity")
    elif policy["kind"] == "reader" and normalize(policy["title"]) not in title:
        failures.append("missing Reader route identity")
    elif policy["kind"] == "private_library":
        if title != "my library | the earnalism" or "my library" not in h1:
            failures.append("missing private My Library route identity")
        if "your earnalism library is private" not in description:
            failures.append("missing private My Library description")
        if "private" not in headers.get("Cache-Control", "").lower() or "no-store" not in headers.get("Cache-Control", "").lower():
            failures.append("missing private, no-store cache policy")
        if re.search(r"\b(?:balance|transaction|device|saved editions|@[a-z0-9.-]+\.[a-z]{2,})\b", text, re.I):
            failures.append("private My Library snapshot exposes account data")

    return {"route": route, "url": url, "status_code": status, "cache_control": headers.get("Cache-Control", ""), "title": " ".join(facts.title).strip(), "description": facts.description, "canonical": facts.canonical, "robots": facts.robots, "failures": failures, "result": "PASS" if not failures else "FAIL"}


def run(base_url: str, timeout: int) -> dict[str, object]:
    routes = [inspect_route(route, policy, *fetch_raw_html(base_url, route, timeout)) for route, policy in ROUTES.items()]
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "base_url": base_url, "contract": ACCESS_COPY, "result": "PASS" if all(row["result"] == "PASS" for row in routes) else "FAIL", "routes": routes}


def write_report(report: dict[str, object]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "post_deploy_static_seo_canary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    rows = ["# Static SEO Raw HTML Canary", "", f"Result: `{report['result']}`", ""]
    for row in report["routes"]:
        rows.append(f"- `{row['route']}`: `{row['result']}`; status={row['status_code']}; failures={'; '.join(row['failures']) or 'none'}")
    (OUTPUT_DIR / "post_deploy_static_seo_canary.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deployed raw HTML snapshot contract.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()
    report = run(args.base_url, args.timeout)
    write_report(report)
    print(f"Static SEO raw HTML canary: result={report['result']}")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
