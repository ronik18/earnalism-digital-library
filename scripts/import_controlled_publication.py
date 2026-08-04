#!/usr/bin/env python3
"""Import an approved controlled-publication packet as an Earnalism draft.

This importer deliberately does not fetch a source, publish a title, upload
audio, or enable public audio. It is intended for packet-backed reader drafts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from scripts.import_books import admin_token, api_json, api_json_optional, text_to_reader_html
except ImportError:  # Direct script execution from the repository root.
    from import_books import admin_token, api_json, api_json_optional, text_to_reader_html


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def build_plan(packet: Path, category_slug: str) -> dict[str, Any]:
    controlled = packet / "controlled-publication"
    audio = packet / "audio"
    book = load_json(controlled / "public_book.json")
    book["category_slug"] = category_slug
    chapters = load_json(controlled / "chapters.json")
    approvals = load_json(controlled / "approval_evidence.json")
    source = load_json(controlled / "source_evidence.json")
    sync = load_json(audio / "gitanjali_section_timestamps.json")
    qa = load_json(packet / "listening-qa" / "listening-qa-scorecard.json")
    wording = load_json(packet / "audio-alignment-review" / "review-approval.json")
    errors: list[str] = []
    require(bool(book.get("slug")), "controlled public_book slug missing", errors)
    require(len(chapters) == 104, f"expected 104 chapters, found {len(chapters)}", errors)
    require(all(str(row.get("content") or "").strip() for row in chapters), "empty canonical chapter", errors)
    require(
        all(sha256_text(str(row["content"])) == row.get("content_hash") for row in chapters),
        "canonical chapter content hash mismatch",
        errors,
    )
    require(approvals.get("reader_editorial_approval", {}).get("status") == "APPROVED", "reader editorial approval missing", errors)
    require(approvals.get("cover_approval", {}).get("status") == "APPROVED", "cover approval missing", errors)
    require(source.get("audio_derivative_rights_status") in {"APPROVED", "RIGHTS_APPROVED"}, "audio derivative rights missing", errors)
    require(sync.get("granularity") == "measured_section", "section sync is not measured", errors)
    require(sync.get("section_count") == 104, "section sync does not cover all chapters", errors)
    require(sync.get("word_highlighting_supported") is False, "packet improperly claims word highlighting", errors)
    require(wording.get("decision") == "APPROVED_SECTION_LEVEL_AUDIO_SYNC", "spoken-wording approval missing", errors)
    require(wording.get("approved_item_count") == 24, "expected 24 approved wording decisions", errors)
    require(qa.get("status") == "APPROVED_BY_THRESHOLD_ATTESTATION", "listening QA threshold attestation missing", errors)
    return {
        "schema": "earnalism.controlled-publication.draft-import.v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "packet": str(packet),
        "slug": book["slug"],
        "title": book.get("title"),
        "chapter_count": len(chapters),
        "chapter_hashes": {row["id"]: row["content_hash"] for row in chapters},
        "reader_import_ready": not errors,
        "audio_import_ready": False,
        "public_release_ready": False,
        "errors": errors,
        "book": book,
        "chapters": chapters,
    }


def draft_payload(book: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "title", "subtitle", "author", "category_slug", "short_description", "description",
        "cover_image_url", "back_cover_image_url", "estimated_reading_time", "formats",
        "benefits", "who_for", "learnings", "about_author", "rights_metadata", "slug",
    }
    payload = {key: value for key, value in book.items() if key in allowed}
    payload.update({
        "is_published": False,
        "audiobook_enabled": False,
        "generate_audiobook": False,
        "reader_exposed": False,
        "audio_exposed": False,
    })
    return payload


def apply_draft(
    plan: dict[str, Any], api_url: str, update_existing_draft: bool,
    resume_existing_draft: bool, replace_unpublished_draft: bool,
    max_chapters_per_run: int,
) -> dict[str, Any]:
    if os.environ.get("CONTROLLED_PUBLICATION_DRAFT_IMPORT_APPROVED") != "1":
        raise RuntimeError("refusing draft mutation: set CONTROLLED_PUBLICATION_DRAFT_IMPORT_APPROVED=1")
    token = admin_token(api_url)
    slug = plan["slug"]
    existing = api_json_optional("GET", f"{api_url}/admin/books/{slug}", token=token)
    payload = draft_payload(plan["book"])
    existing_titles: set[str] = set()
    if existing:
        if existing.get("is_published"):
            raise RuntimeError(f"refusing to overwrite published title: {slug}")
        if replace_unpublished_draft:
            deleted = api_json("DELETE", f"{api_url}/admin/books/{slug}", token=token)
            if deleted.get("deleted") != 1:
                raise RuntimeError(f"failed to delete unpublished draft: {slug}")
            existing = None
            update_existing_draft = False
            resume_existing_draft = False
        if not update_existing_draft and not resume_existing_draft:
            if existing:
                raise RuntimeError(f"draft already exists: {slug}; rerun with --resume-existing-draft or --replace-unpublished-draft")
        if existing and update_existing_draft:
            created = api_json("PUT", f"{api_url}/admin/books/{slug}", payload, token)
            for chapter in existing.get("chapters", []):
                chapter_id = chapter.get("id")
                if chapter_id:
                    api_json("DELETE", f"{api_url}/admin/books/{slug}/chapters/{chapter_id}", token=token)
        elif existing:
            created = existing
            existing_titles = {str(row.get("title") or "") for row in existing.get("chapters", [])}
        else:
            created = api_json("POST", f"{api_url}/admin/books", payload, token)
    else:
        created = api_json("POST", f"{api_url}/admin/books", payload, token)
    target_slug = created.get("slug") or slug
    uploaded = 0
    for chapter in sorted(plan["chapters"], key=lambda row: row["order"]):
        if chapter["title"] in existing_titles:
            continue
        if max_chapters_per_run and uploaded >= max_chapters_per_run:
            break
        api_json("POST", f"{api_url}/admin/books/{target_slug}/chapters", {
            "title": chapter["title"],
            "content": text_to_reader_html(chapter["content"]),
            "is_preview": False,
        }, token)
        uploaded += 1
    remaining = len(plan["chapters"]) - len(existing_titles) - uploaded
    if remaining == 0:
        verified = api_json("GET", f"{api_url}/admin/books/{target_slug}", token=token)
        remote_chapters = sorted(verified.get("chapters") or [], key=lambda row: row.get("order", 0))
        expected_chapters = sorted(plan["chapters"], key=lambda row: row["order"])
        expected_titles = [row["title"] for row in expected_chapters]
        remote_titles = [row.get("title") for row in remote_chapters]
        if remote_titles != expected_titles:
            raise RuntimeError("post-import chapter title/order verification failed")
        expected_html = [text_to_reader_html(row["content"]) for row in expected_chapters]
        remote_html = [row.get("content") for row in remote_chapters]
        if remote_html != expected_html:
            raise RuntimeError("post-import rendered chapter content verification failed")
        if verified.get("is_published") or verified.get("audiobook_enabled"):
            raise RuntimeError("post-import exposure verification failed")
    return {
        "slug": target_slug, "id": created.get("id"), "draft_only": True,
        "uploaded_chapters": uploaded, "remaining_chapters": remaining,
        "complete": remaining == 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import an approved controlled publication packet as a draft.")
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--api-url", default=os.environ.get("EARNALISM_API_URL", "https://api.theearnalism.com"))
    parser.add_argument("--category-slug", required=True, help="Approved canonical catalog category for this packet.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--update-existing-draft", action="store_true")
    parser.add_argument("--resume-existing-draft", action="store_true")
    parser.add_argument("--replace-unpublished-draft", action="store_true")
    parser.add_argument("--max-chapters-per-run", type=int, default=0)
    parser.add_argument("--output", type=Path, default=Path("/tmp/controlled-publication-draft-import.json"))
    args = parser.parse_args()
    plan = build_plan(args.packet_dir.resolve(), args.category_slug)
    if args.apply:
        if plan["errors"]:
            raise RuntimeError("packet rejected: " + "; ".join(plan["errors"]))
        plan["apply_result"] = apply_draft(
            plan, args.api_url.rstrip("/"), args.update_existing_draft,
            args.resume_existing_draft, args.replace_unpublished_draft,
            args.max_chapters_per_run,
        )
    plan.pop("book")
    plan.pop("chapters")
    args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: plan[key] for key in ("slug", "chapter_count", "reader_import_ready", "audio_import_ready", "public_release_ready", "errors")}, indent=2))
    return 0 if not plan["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
