#!/usr/bin/env python3
"""Compare retained Reader snapshots and prepare local, inactive repair plans.

No HTTP, database, publication or promotion operations are performed. Run the
CLI with the same synthetic loopback settings used for backend unit tests.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Match the backend container's module search path for its renderer's utils
# import; otherwise package-style CLI imports can silently select HTML escape.
sys.path.insert(0, str(ROOT / "backend"))
from backend.domain.reading_pass import segment_manifest


def compare_pages(slug: str, records: list[dict], live: dict, delivery: dict | None = None) -> dict:
    canonical = live.get("canonical_pages") or {}
    rows = canonical.get("pages") or []
    expected = [(r["page_index"], r["chapter_id"], r["content_sha256"]) for r in records]
    observed = [(r.get("page_number"), r.get("chapter_id"), r.get("content_hash")) for r in rows]
    manifest = segment_manifest(records)
    source_match = bool(records) and observed == expected and canonical.get("page_count") == len(records)
    delivery = delivery or {}
    # A manifest, admitted session or successful HTTP status alone proves no
    # protected text delivery. Require the exact final page and actual content.
    final = records[-1] if records else {}
    delivery_match = bool(
        source_match
        and delivery.get("slug") == slug
        and delivery.get("page_index") == final.get("page_index")
        and delivery.get("page_hash") == final.get("content_sha256")
        and delivery.get("nonempty_content") is True
        and delivery.get("visible_authorized") is True
        and delivery.get("authenticated") is True
        and delivery.get("status") == 200
    )
    digest = hashlib.sha256(json.dumps(expected, separators=(",", ":")).encode()).hexdigest()
    return {
        "slug": slug,
        "live_pages": canonical.get("page_count"),
        "complete_source_pages": len(records),
        "source_matches": source_match,
        "confirmed_protected_delivery": delivery_match,
        "missing_chapter_ids": sorted({r[1] for r in expected} - {r[1] for r in observed}),
        "live_sequence_contiguous": [r[0] for r in observed] == list(range(1, len(observed) + 1)),
        "live_manifest_revision": canonical.get("content_revision"),
        "live_segmentation_version": canonical.get("schema_version"),
        "candidate": {
            "state": "LOCAL_INACTIVE_NOT_STORED_OR_PROMOTED",
            "segmentation_version": "complete-html-v1-" + digest[:32],
            "target_characters": 3200,
            "manifest": manifest,
            "pages": [{k: r[k] for k in ("page_index", "chapter_id", "content_sha256", "is_public_preview")} for r in records],
        },
        "required_before_promotion": [
            "Exact current rights/source bindings and review",
            "Authenticated metadata-only GET of segments/active; never infer activation generation",
            "Supported inactive candidate build and exact hash/coverage parity",
            "Separate owner release authority and guarded expected-version promotion",
            "Actual protected delivery, denial and usage acceptance",
        ],
    }


def narrative_digest(chapters: list[dict]) -> str:
    """Compare text occurrence/order across HTML formatting, not visual QA."""
    value = " ".join(str(c.get("content") or "") for c in chapters)
    text = unicodedata.normalize("NFC", html.unescape(re.sub(r"<[^>]+>", " ", value)))
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()


def render_chapters(chapters: list[dict], renderer) -> list[dict]:
    rendered = []
    for chapter in chapters:
        content, warnings = renderer(chapter.get("content", ""))
        if warnings:
            raise ValueError(f"{chapter.get('id')}: renderer warnings must be resolved: {warnings}")
        rendered.append({**chapter, "content": content})
    return rendered


def complete_preview_matches(slug, chapters, live, previews, *, illustration_labels=False):
    canonical = live.get("canonical_pages") or {}
    count = canonical.get("page_count")
    if type(count) is not int or not 0 < count <= 3 or len(previews) != count:
        return False
    ordered = sorted(previews, key=lambda row: row.get("page_index", 0))
    expected = canonical.get("pages") or []
    if len(expected) != count:
        return False
    for index, (page, metadata) in enumerate(zip(ordered, expected), 1):
        content = page.get("content") or ""
        digest = hashlib.sha256(content.encode()).hexdigest()
        if (page.get("book_slug") != slug or page.get("page_index") != index
            or metadata.get("page_number") != index or not content.strip()
            or digest != page.get("content_sha256") or digest != metadata.get("content_hash")):
            return False
    content = " ".join(page["content"] for page in ordered)
    if illustration_labels:
        content = re.sub(r"\[Picture:[^\]]*\]", "", content)
    return narrative_digest([{"content": content}]) == narrative_digest(chapters)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshots", type=Path, required=True)
    parser.add_argument("--delivery-receipts", type=Path)
    parser.add_argument("--reference-source-root", type=Path,
                        help="Retained controlled_publications snapshot; comparison only, never release authority")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # The normal runtime loader validates the complete controlled package;
    # the normal renderer prevents plain-text/HTML normalization false alarms.
    from backend import server
    from backend.domain.reading_pass import canonical_page_records
    from backend.catalog_truth import controlled_artifact_dir
    receipts = json.loads(args.delivery_receipts.read_text()) if args.delivery_receipts else []
    by_slug = {row["slug"]: row for row in receipts}
    results = []
    for slug in sorted(server.CONTROLLED_LIVE_BOOK_SLUGS):
        book = server._controlled_artifact_doc(slug, include_content=True)
        if not book:
            raise ValueError(f"{slug}: complete controlled package did not validate")
        chapters = render_chapters(sorted(book["chapters"], key=lambda c: c.get("order", 0)),
                                   server._manual_content_to_render_html)
        records = canonical_page_records(book_slug=slug, chapters=chapters, target_characters=3200)
        live = json.loads((args.snapshots / (slug + ".json")).read_text())
        result = compare_pages(slug, records, live, by_slug.get(slug))
        result["match_basis"] = "CURRENT_RENDERED_SOURCE" if result["source_matches"] else "UNRESOLVED"
        if not result["source_matches"] and args.reference_source_root:
            reference_dir = args.reference_source_root / slug / "chapters"
            # Old cover/publication metadata is not release authority. Use only
            # the same ordered chapter identities, and require their entire
            # text sequence to equal the currently validated source below.
            paths = [reference_dir / (c["id"] + ".json") for c in book["chapters"]]
            if all(path.is_file() for path in paths):
                old_chapters = [json.loads(path.read_text()) for path in paths]
                rendered = render_chapters(old_chapters, server._manual_content_to_render_html)
                old_pages = canonical_page_records(book_slug=slug, chapters=rendered, target_characters=3200)
                old_match = compare_pages(slug, old_pages, live, by_slug.get(slug))
                if old_match["source_matches"] and narrative_digest(old_chapters) == narrative_digest(book["chapters"]):
                    result["source_matches"] = True
                    result["confirmed_protected_delivery"] = old_match["confirmed_protected_delivery"]
                    result["match_basis"] = "EXACT_RETAINED_PAGE_HASHES_AND_CURRENT_TEXT_SEQUENCE_PARITY"
                    result["reference_narrative_sha256"] = narrative_digest(old_chapters)
        count = live.get("canonical_pages", {}).get("page_count", 0)
        preview_paths = [args.snapshots / f"{slug}-preview-{index}.json" for index in range(1, count + 1)] if 0 < count <= 3 else []
        result["confirmed_public_delivery"] = False
        if preview_paths and all(path.is_file() for path in preview_paths):
            source = json.loads((controlled_artifact_dir(slug) / "source_evidence.json").read_text())
            policy = source.get("reader_text_furniture_removal", {}).get("transformation", "")
            previews = [json.loads(path.read_text()) for path in preview_paths]
            if complete_preview_matches(slug, book["chapters"], live, previews,
                    illustration_labels=policy.startswith("Remove nonnarrative Picture")):
                result["source_matches"] = True
                result["confirmed_public_delivery"] = True
                result["match_basis"] = "ALL_PUBLIC_PAGES_DELIVERED_COMPLETE_NARRATIVE_MATCH"
        result["disposition"] = "PRESERVE_MATCHING_LIVE_PAGES" if result["source_matches"] else "REVIEW_COMPLETE_INACTIVE_SUCCESSOR"
        record, _components = server._release_rights_artifact(slug)
        result.update(title=book["title"], source_content_hash=book.get("content_hash"),
                      rights_decision_id=(record or {}).get("decision_id"),
                      rights_record_sha256=server.record_sha256(record) if record else None)
        results.append(result)
    results.sort(key=lambda row: (row["live_pages"] or 0, row["title"]))
    payload = {"schema": "earnalism.reader-completeness-preparation.v1", "production_changed": False,
               "titles": results, "count": len(results),
               "source_matches": sum(r["source_matches"] for r in results),
               "confirmed_protected_delivery": sum(r["confirmed_protected_delivery"] for r in results),
               "confirmed_public_delivery": sum(r["confirmed_public_delivery"] for r in results),
               "preparer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    # Exclusive create prevents an older snapshot from overwriting evidence.
    with args.output.open("x") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({k: v for k, v in payload.items() if k != "titles"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
