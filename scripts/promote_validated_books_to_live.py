#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTENT_ROOT = ROOT / "content" / "books"
CONTROLLED_ROOT = ROOT / "data" / "controlled_publications"
CONTROLLED_LAUNCH_PATH = ROOT / "data" / "controlled_launch.json"
QUALITY_REPORT_PATH = CONTENT_ROOT / "reader-content-quality-report.json"
PROMOTION_REPORT_JSON = CONTENT_ROOT / "batch-1-promotion-report.json"
PROMOTION_REPORT_MD = CONTENT_ROOT / "batch-1-promotion-report.md"

DRACULA_SLUG = "dracula"
LIVE_FLAGS: dict[str, Any] = {
    "readerStatus": "reader_ready",
    "publicationStatus": "live",
    "isPublic": True,
    "isLive": True,
    "showInPublicLibrary": True,
    "showInHomepage": False,
    "allowPublicReading": True,
    "allowCheckout": False,
    "allowPayment": False,
    "is_published": True,
}
DRAFT_FLAGS: dict[str, Any] = {
    "readerStatus": "ready_for_editorial_review",
    "publicationStatus": "draft",
    "isPublic": False,
    "isLive": False,
    "showInPublicLibrary": False,
    "showInHomepage": False,
    "allowPublicReading": False,
    "allowCheckout": False,
    "allowPayment": False,
    "is_published": False,
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_quality_by_slug() -> dict[str, dict[str, Any]]:
    if not QUALITY_REPORT_PATH.exists():
        raise FileNotFoundError(
            f"{QUALITY_REPORT_PATH.relative_to(ROOT)} is missing. Run validate_reader_content_quality.py first."
        )
    report = read_json(QUALITY_REPORT_PATH)
    return {book["slug"]: book for book in report.get("books", []) if isinstance(book, dict) and book.get("slug")}


def apply_book_flags(slug: str, flags: dict[str, Any]) -> None:
    book_json_path = CONTENT_ROOT / slug / "book.json"
    if not book_json_path.exists():
        return
    payload = read_json(book_json_path)
    payload.update(flags)
    payload["updatedAt"] = now()
    write_json(book_json_path, payload)


def apply_artifact_flags(slug: str, promote: bool) -> None:
    public_book_path = CONTROLLED_ROOT / slug / "public_book.json"
    if not public_book_path.exists():
        return
    payload = read_json(public_book_path)
    if promote:
        payload.update(LIVE_FLAGS)
        payload["approved_to_publish"] = True
        payload["publication_status"] = "LIVE_APPROVED"
        payload["verification_status"] = "approved"
        payload["qa_status"] = "QA_PASSED"
    else:
        payload.update(DRAFT_FLAGS)
        payload["approved_to_publish"] = False
        payload["publication_status"] = "DRAFT_EDITORIAL_REVIEW"
        payload["verification_status"] = "held"
        payload["qa_status"] = "QA_HOLD"
    payload["audio_enabled"] = False
    payload["audiobook_enabled"] = False
    payload["generate_audiobook"] = False
    payload["audiobook_assets"] = {}
    payload["audiobook"] = {}
    payload["updated_at"] = now()
    write_json(public_book_path, payload)


def update_controlled_launch(live_slugs: list[str]) -> None:
    config = read_json(CONTROLLED_LAUNCH_PATH) if CONTROLLED_LAUNCH_PATH.exists() else {}
    merged = [DRACULA_SLUG]
    for slug in live_slugs:
        if slug != DRACULA_SLUG and slug not in merged:
            merged.append(slug)
    config["live_approved_slugs"] = merged
    config["audio_enabled_slugs"] = []
    config.setdefault("pipeline_slugs", ["kshudhita-pashan"])
    write_json(CONTROLLED_LAUNCH_PATH, config)


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Controlled Bilingual Reader Release Batch 1",
        "",
        f"- generated_at: {report['generatedAt']}",
        f"- total_configured: {report['totalBooksConfigured']}",
        f"- promoted_live: {len(report['promotedLiveSlugs'])}",
        f"- held: {len(report['heldSlugs'])}",
        f"- public_audio_status: PUBLIC_AUDIO_RELEASE_BLOCKED",
        f"- payment_behavior: UNCHANGED_NO_CHECKOUT_NO_PAYMENT",
        "",
        "## Promotion Decisions",
        "",
        "| Slug | Title | Language | Score | Chapters | Words | Decision | Blockers |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for book in report["books"]:
        blockers = "; ".join(book.get("blockers") or []) or "none"
        lines.append(
            f"| {book['slug']} | {book['title']} | {book['language']} | {book['score']} | "
            f"{book['chapterCount']} | {book['wordCountApprox']} | {book['decision']} | {blockers} |"
        )
    lines.extend(
        [
            "",
            "## Safety Notes",
            "",
            "- All books were imported first as draft/editorial-review artifacts.",
            "- Only books with score 100/100 and no legal/source blockers were promoted to public reader availability.",
            "- `showInHomepage`, `allowCheckout`, `allowPayment`, public audio, and audiobook metadata remain disabled for this batch.",
            "- Dracula remains live; no audiobook public release is introduced.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote only 100/100 validated batch books to live reader availability.")
    parser.add_argument("--manifest", default="book_import_manifest.batch-1.json")
    parser.add_argument("--require-score", type=int, default=100)
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = ROOT / manifest_path
    manifest = read_json(manifest_path)
    quality = load_quality_by_slug()

    books: list[dict[str, Any]] = []
    promoted: list[str] = []
    held: list[str] = []
    for entry in manifest.get("books", []):
        slug = entry["slug"]
        result = quality.get(slug)
        blockers = [] if result else ["Missing quality report entry."]
        score = int((result or {}).get("score", 0) or 0)
        source_ready = "Status: ready_for_auto_publication" in (CONTENT_ROOT / slug / "source-rights.md").read_text(encoding="utf-8")
        if not source_ready:
            blockers.append("source-rights.md is not ready_for_auto_publication.")
        blockers.extend((result or {}).get("blockers") or [])
        should_promote = (
            bool(entry.get("allowAutoLiveAfterValidation"))
            and score >= args.require_score
            and result
            and result.get("status") == "PASS_100"
            and source_ready
            and not blockers
        )
        decision = "PROMOTED_LIVE_READER_ONLY" if should_promote else "HELD_DRAFT_EDITORIAL_REVIEW"
        if should_promote:
            apply_book_flags(slug, LIVE_FLAGS)
            apply_artifact_flags(slug, True)
            promoted.append(slug)
        else:
            apply_book_flags(slug, DRAFT_FLAGS)
            apply_artifact_flags(slug, False)
            held.append(slug)
        books.append(
            {
                "slug": slug,
                "title": entry.get("displayTitle") or entry.get("title"),
                "sourceUrl": entry.get("sourceUrl"),
                "language": entry.get("language"),
                "score": score,
                "status": (result or {}).get("status", "HOLD"),
                "chapterCount": int((result or {}).get("chapterCount", 0) or 0),
                "wordCountApprox": int((result or {}).get("wordCountApprox", 0) or 0),
                "routeStatus": (result or {}).get("routeStatus", "HOLD"),
                "bengaliRenderingStatus": (result or {}).get("bengaliRenderingStatus", "NOT_APPLICABLE"),
                "blockers": blockers,
                "decision": decision,
            }
        )

    update_controlled_launch(promoted)
    report = {
        "generatedAt": now(),
        "batchId": manifest.get("batchId"),
        "totalBooksConfigured": len(books),
        "promotedLiveSlugs": promoted,
        "heldSlugs": held,
        "approvedReleaseAllowlist": [DRACULA_SLUG, *promoted],
        "publicAudioStatus": "PUBLIC_AUDIO_RELEASE_BLOCKED",
        "audiobookProductionStatus": "PRODUCTION_BLOCKED",
        "paymentBehavior": "UNCHANGED_NO_CHECKOUT_NO_PAYMENT",
        "books": books,
    }
    write_json(PROMOTION_REPORT_JSON, report)
    PROMOTION_REPORT_MD.write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not held else 1


if __name__ == "__main__":
    raise SystemExit(main())
