#!/usr/bin/env python3
"""Prepare evidence for held Bengali text editions; never authorize publication.

Public Wikisource metadata is fetched only with --fetch. No admin/customer API,
audio service, accepted-decision registry, or live allowlist is written.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import unicodedata
from urllib.parse import unquote, urlencode, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
REQUEST_INTERVAL = 8.0
LAST_REQUEST = 0.0
SOURCE_METADATA = {}
sys.path.insert(0, str(ROOT))
from backend.publication_manifest import build_manifest, validate_manifest
from scripts.bengali_rights_package_validator import checksum_manifest_matches


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalized_text(text: str) -> str:
    # Formatting only. Literary letters and punctuation are never normalized away.
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text).replace("\u200b", "").replace("\ufeff", "")).strip()


def fetch_json(parameters: dict) -> tuple[dict, dict]:
    global LAST_REQUEST
    delay = REQUEST_INTERVAL - (time.monotonic() - LAST_REQUEST)
    if delay > 0:
        time.sleep(delay)
    LAST_REQUEST = time.monotonic()
    url = "https://bn.wikisource.org/w/api.php?" + urlencode(parameters)
    request = Request(url, headers={"User-Agent": "EarnalismComplianceAudit/1.0 (source evidence verification)"})
    with urlopen(request, timeout=30) as response:
        payload = response.read()
    return json.loads(payload), {"url": url, "retrieved_at": datetime.now(timezone.utc).isoformat(), "response_sha256": sha(payload)}


def source_snapshot(url: str, license_evidence: dict) -> tuple[dict, str]:
    from bs4 import BeautifulSoup
    parsed = urlparse(url)
    if parsed.hostname != "bn.wikisource.org" or not parsed.path.startswith("/wiki/"):
        return {"status": "UNSUPPORTED_SOURCE_REQUIRES_REVIEW", "url": url}, ""
    title = unquote(parsed.path.removeprefix("/wiki/")).replace("_", " ")
    if title in SOURCE_METADATA:
        page, receipt = SOURCE_METADATA[title]
    else:
        data, receipt = fetch_json({"action": "query", "prop": "info|revisions", "rvprop": "ids|timestamp", "titles": title, "format": "json", "formatversion": "2", "redirects": "1"})
        page = data.get("query", {}).get("pages", [{}])[0]
    if page.get("missing") is True or not page.get("lastrevid"):
        return {"status": "SOURCE_PAGE_MISSING", "page": page, "metadata_receipt": receipt}, ""
    revision = page["lastrevid"]
    data, parse_receipt = fetch_json({"action": "parse", "oldid": revision, "prop": "text|properties|links", "format": "json", "formatversion": "2"})
    if "error" in data:
        return {"status": "SOURCE_PARSE_ERROR", "error": data["error"], "parse_receipt": parse_receipt}, ""
    parsed_data = data["parse"]
    html = parsed_data.get("text", "")
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one(".prp-pages-output") or soup.select_one(".mw-parser-output") or soup
    for node in body.select("table, .ws-noexport, .noprint, .pagenum, .mw-editsection, script, style, sup.reference"):
        node.decompose()
    paragraphs = [p.get_text("", strip=True) for p in body.find_all("p")]
    paragraphs = [p for p in paragraphs if normalized_text(p)]
    # A title on its own is source furniture, not manuscript text.
    short_title = page["title"].rsplit("/", 1)[-1]
    removed_furniture = []
    while paragraphs and normalized_text(paragraphs[0]) == normalized_text(short_title):
        removed_furniture.append({"kind": "standalone_source_title", "text": paragraphs[0]})
        paragraphs.pop(0)
    # A separate four-digit source dateline is metadata. Retain it explicitly;
    # never infer an exact Gregorian first-publication year from it.
    if paragraphs and re.fullmatch(r"[০-৯]{4}[?।]?", normalized_text(paragraphs[-1])):
        removed_furniture.append({"kind": "standalone_bengali_source_dateline_not_verified_first_publication_year", "text": paragraphs.pop()})
    text = "\n\n".join(paragraphs)
    index = re.findall(r'Page:([^"<>]+)|পৃষ্ঠা:([^"<>]+)', html)
    return {
        "status": "PINNED_SOURCE_RETRIEVED_NOT_PUBLICATION_APPROVAL",
        "page_id": page["pageid"], "page_title": page["title"], "revision_id": revision,
        "revision_timestamp": page.get("revisions", [{}])[0].get("timestamp"),
        "permalink": "https://bn.wikisource.org/w/index.php?" + urlencode({"title": page["title"], "oldid": revision}),
        "contributors": "https://bn.wikisource.org/w/index.php?" + urlencode({"title": page["title"], "action": "history"}),
        "metadata_receipt": receipt, "parse_receipt": parse_receipt,
        "rendered_html_sha256": sha(html.encode()), "extracted_paragraphs_sha256": sha(text.encode()),
        "paragraph_count": len(paragraphs), "source_layer_license": license_evidence,
        "source_furniture_separated_from_manuscript": removed_furniture,
        "comparison_method": "NFC/whitespace only; separate explicitly recorded standalone source title/dateline; no literary word or punctuation edits.",
        "linked_pages": [row["*"] if "*" in row else row.get("title", "") for row in parsed_data.get("links", [])],
        "facsimile_page_references": [next(v for v in pair if v) for pair in index],
        "edition_identity_status": "EXACT_FACSIMILE_AND_EDITORIAL_LAYER_REVIEW_REQUIRED",
    }, text


def canonical_identity(package: Path) -> dict:
    book = read_json(package / "public_book.json")
    source = read_json(package / "source_evidence.json")
    chapters = []
    texts = []
    for row in sorted(book.get("chapters", []), key=lambda c: c["order"]):
        payload = read_json(package / "chapters" / (row["id"] + ".json"))
        content = payload.get("content", "")
        texts.append(content)
        chapters.append({"id": row["id"], "order": row["order"], "title": row.get("title"), "content_sha256": sha(content.encode()), "file_sha256": sha((package / "chapters" / (row["id"] + ".json")).read_bytes()), "declared_hash_matches": payload.get("content_hash") == sha(content.encode())})
    return {"source_sha256": source.get("source_hash"), "declared_content_sha256": source.get("content_hash"), "content_two_newlines_sha256": sha("\n\n".join(texts).encode()), "content_one_newline_sha256": sha("\n".join(texts).encode()), "chapters": chapters, "texts": texts}


def existing_comparison(package: Path, identity: dict, root: Path) -> dict:
    packet = read_json(root / "data/title_rights_evidence/bengali-bankim-cohort-1.json")
    record = next((t for t in packet.get("titles", []) if t["slug"] == package.name), {})
    comparison = record.get("complete_source_comparison", {})
    references = comparison.get("chapters", [])
    if comparison.get("status") != "TEXT_VERIFIED" or not references:
        return {"status": "EXACT_SOURCE_COMPARISON_REQUIRED"}
    matches = len(references) == len(identity["chapters"]) and all(c["order"] == e["chapter"] and c["content_sha256"] == e["canonical_chapter_sha256"] for c, e in zip(identity["chapters"], references))
    return {"status": "EXISTING_EXACT_SOURCE_EVIDENCE_REVALIDATED" if matches else "EXISTING_SOURCE_EVIDENCE_STALE", "evidence_file": "data/title_rights_evidence/bengali-bankim-cohort-1.json", "evidence_file_sha256": sha((root / "data/title_rights_evidence/bengali-bankim-cohort-1.json").read_bytes()), "source_edition": comparison.get("source_edition"), "source_facsimile_pdf_sha256": comparison.get("source_facsimile_pdf_sha256"), "chapter_references": references, "all_chapter_hashes_match": matches}


def audit_package(package: Path, root: Path, license_evidence: dict, fetch: bool) -> dict:
    from bs4 import BeautifulSoup
    book = read_json(package / "public_book.json")
    source = read_json(package / "source_evidence.json")
    identity = canonical_identity(package)
    texts = identity.pop("texts")
    exclusion = read_json(root / "data/catalog_exclusions.json").get("titles", {}).get(package.name, {})
    ordinary_manifest = build_manifest(package, generated_at=datetime.now(timezone.utc).isoformat())
    manifest = build_manifest(package, generated_at=datetime.now(timezone.utc).isoformat(), reader_preparation_only=True)
    front = book.get("cover_image_url") or book.get("cover_url") or ""
    back = book.get("back_cover_image_url") or book.get("back_cover_url") or ""
    snapshot, source_text = ({"status": "NOT_FETCHED"}, "")
    if fetch:
        try:
            snapshot, source_text = source_snapshot(source.get("source_url", ""), license_evidence)
        except HTTPError as error:
            if error.code == 429:
                raise  # Stop instead of sending more requests after provider backpressure.
            snapshot = {"status": "SOURCE_FETCH_FAILED", "error": f"{type(error).__name__}: {error}"}
        except Exception as error:
            snapshot = {"status": "SOURCE_FETCH_FAILED", "error": f"{type(error).__name__}: {error}"}
    canonical_plain = normalized_text(BeautifulSoup("\n\n".join(texts), "html.parser").get_text(" ", strip=True))
    extracted = normalized_text(source_text)
    comparison = existing_comparison(package, identity, root)
    if extracted:
        comparison["current_source_paragraph_comparison"] = "EXACT_MATCH_FORMATTING_ONLY" if canonical_plain == extracted else "CANONICAL_IS_SUBSET_NOT_COMPLETENESS_PROOF" if canonical_plain and canonical_plain in extracted else "DIFFERENT_OR_MULTICHAPTER_SOURCE_REQUIRES_COMPARISON"
    blockers = list(manifest["reader_release"]["blockers"])
    if not comparison.get("all_chapter_hashes_match") and comparison.get("current_source_paragraph_comparison") != "EXACT_MATCH_FORMATTING_ONLY":
        blockers.append("Exact edition/transcription completeness comparison is not established.")
    blockers += ["CC BY-SA attribution, source/license links, change notice, ShareAlike delivery and no-additional-restrictions implementation must be verified.", "Edition-bound owner/legal publication authorization and accepted registry decision are required."]
    if exclusion.get("public_catalog_excluded") or exclusion.get("reader_excluded"):
        blockers.append("Explicit owner-directed catalogue/reader exclusion remains active.")
    # An existing asset can be identified without converting design ownership into
    # an assertion about unknown third-party elements.
    cover = {"front_url": front, "back_url": back, "owner_design_attestation": "Owner states all front and back covers are designed by the owner.", "scope": "COVER_DESIGN_ONLY; NOT_TEXT_RIGHTS_OR_PUBLICATION_AUTHORIZATION", "third_party_component_clearance": "NOT_INFERRED", "front_binding": "PRESENT" if front else "MISSING", "back_binding": "PRESENT" if back else "MISSING"}
    return {"slug": package.name, "title": book.get("title"), "author": book.get("author"), "status": "EXCLUDED" if exclusion else "PREPARED_EVIDENCE_RELEASE_HELD", "identity": identity, "source": snapshot, "source_comparison": comparison, "cover_provenance": cover, "checksum": "PASS" if checksum_manifest_matches(package) else "FAIL", "manifest_schema_issues": validate_manifest(manifest), "ordinary_manifest_issues_from_historical_metadata": validate_manifest(ordinary_manifest), "proposed_reader_manifest_status": manifest["reader_release"]["status"], "publication_authorization": "NOT_GRANTED_BY_THIS_AUDIT", "blockers": sorted(set(blockers)), "audio_touched": False, "live_allowlist_touched": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Reuse successful exact-package source receipts from the existing output.")
    parser.add_argument("--recheck-source-text", action="store_true", help="Recompare pinned revisions using the current source-furniture extractor.")
    args = parser.parse_args()
    launch = read_json(ROOT / "data/controlled_launch.json")
    live = set(launch["live_approved_slugs"])
    packages = []
    for package in sorted((ROOT / "data/controlled_publications").iterdir()):
        book = read_json(package / "public_book.json")
        if package.name not in live and (re.search(r"[\u0980-\u09ff]", str(book.get("title", ""))) or book.get("language") in {"bn", "ben", "bengali"}):
            packages.append(package)
    license_evidence = {"status": "NOT_FETCHED"}
    if args.fetch:
        data, receipt = fetch_json({"action": "query", "meta": "siteinfo", "siprop": "rightsinfo", "format": "json", "formatversion": "2"})
        license_evidence = {"status": "SITE_LICENSE_VERIFIED_NOT_EDITION_CLEARANCE", "rightsinfo": data["query"]["rightsinfo"], "receipt": receipt}
        if "creativecommons.org/licenses/by-sa/4.0/" not in license_evidence["rightsinfo"].get("url", ""):
            raise SystemExit("Unexpected source licence; do not download manuscript text.")
    previous = read_json(args.output) if args.resume else {}
    cached = {row["slug"]: row for row in previous.get("titles", [])}
    for old in cached.values():
        snapshot = old.get("source", {})
        if snapshot.get("status") == "PINNED_SOURCE_RETRIEVED_NOT_PUBLICATION_APPROVAL":
            page = {"pageid": snapshot["page_id"], "title": snapshot["page_title"], "lastrevid": snapshot["revision_id"], "revisions": [{"timestamp": snapshot.get("revision_timestamp")}]}
            source = read_json(ROOT / "data/controlled_publications" / old["slug"] / "source_evidence.json")
            title = unquote(urlparse(source.get("source_url", "")).path.removeprefix("/wiki/")).replace("_", " ")
            SOURCE_METADATA[title] = (page, snapshot["metadata_receipt"])
    remaining = [p for p in packages if cached.get(p.name, {}).get("source", {}).get("status") != "PINNED_SOURCE_RETRIEVED_NOT_PUBLICATION_APPROVAL"]
    if args.fetch:
        # Batch metadata to avoid two requests per edition; retain receipt identity.
        titles = [unquote(urlparse(read_json(p / "source_evidence.json").get("source_url", "")).path.removeprefix("/wiki/")).replace("_", " ") for p in remaining]
        for offset in range(0, len(titles), 8):
            data, receipt = fetch_json({"action": "query", "prop": "info|revisions", "rvprop": "ids|timestamp", "titles": "|".join(titles[offset:offset + 8]), "format": "json", "formatversion": "2", "redirects": "1"})
            pages = {p["title"]: p for p in data.get("query", {}).get("pages", [])}
            aliases = {r["from"]: r["to"] for key in ("normalized", "redirects") for r in data.get("query", {}).get(key, [])}
            for title in titles[offset:offset + 8]:
                target = aliases.get(title, title)
                target = aliases.get(target, target)
                SOURCE_METADATA[title] = (pages.get(target, {"title": target, "missing": True}), receipt)
    rows = []
    for package in packages:
        old = cached.get(package.name)
        identity = canonical_identity(package)
        identity.pop("texts")
        if old and (old["source"]["status"] == "PINNED_SOURCE_RETRIEVED_NOT_PUBLICATION_APPROVAL" or not args.fetch) and old["identity"] == identity and not args.recheck_source_text:
            row = audit_package(package, ROOT, license_evidence, False)
            row["source"] = old["source"]
            row["source_comparison"].update({k: v for k, v in old["source_comparison"].items() if k == "current_source_paragraph_comparison"})
            if row["source_comparison"].get("current_source_paragraph_comparison") == "EXACT_MATCH_FORMATTING_ONLY":
                row["blockers"] = [b for b in row["blockers"] if b != "Exact edition/transcription completeness comparison is not established."]
        else:
            try:
                row = audit_package(package, ROOT, license_evidence, args.fetch)
            except HTTPError as error:
                if error.code != 429:
                    raise
                # Persist completed evidence so a later, paced run can resume.
                break
        rows.append(row)
        print(f"Prepared {package.name}: {row['source']['status']}", flush=True)
    result = {"schema_version": "earnalism.bengali-text-compliance-preparation.v1", "generated_at": datetime.now(timezone.utc).isoformat(), "territory": "IN", "scope": "TEXT_PREPARATION_ONLY", "live_set_before": sorted(live), "titles": rows, "held_count": len(rows), "new_publications_authorized": 0, "new_titles_activated": 0}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), "titles": len(rows), "source_pages_retrieved": sum(t["source"]["status"] == "PINNED_SOURCE_RETRIEVED_NOT_PUBLICATION_APPROVAL" for t in rows), "front_bindings_missing": sum(t["cover_provenance"]["front_binding"] == "MISSING" for t in rows), "new_publications_authorized": 0}))


if __name__ == "__main__":
    main()
