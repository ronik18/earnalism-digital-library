#!/usr/bin/env python3
"""Popularity-ranked Bengali audiobook credit optimizer.

This script is intentionally a planner, not a publisher. It spends no provider
credits by default. It ranks Bengali candidates by explicit popularity metadata
when present, otherwise by a documented curated classics fallback, then emits
the cheapest safe OpenAI/Sarvam next commands.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
RUN_ROOT = ROOT / "internal" / "audiobook_lab" / "release_gate"
DEFAULT_MANIFEST = ROOT / "book_import_manifest.json"

CURATED_POPULARITY: dict[str, float] = {
    "কাবুলিওয়ালা": 100.0,
    "পথের পাঁচালী": 99.0,
    "দেবদাস": 98.0,
    "পোস্টমাস্টার": 97.0,
    "ছুটি": 96.0,
    "নষ্টনীড়": 95.0,
    "স্ত্রীর পত্র": 94.0,
    "শাস্তি": 93.0,
    "ক্ষুধিত পাষাণ": 92.0,
    "সুভা": 91.0,
    "হৈমন্তী": 90.0,
    "সমাপ্তি": 89.0,
    "একরাত্রি": 88.0,
    "অপরিচিতা": 87.0,
    "মহেশ": 86.0,
    "দেনাপাওনা": 85.0,
    "মেঘ ও রৌদ্র": 84.0,
    "জীবিত ও মৃত": 83.0,
    "অতিথি": 82.0,
    "দুই বিঘা জমি": 81.0,
}

POPULARITY_FIELDS = (
    "popularity_score",
    "popularity",
    "demand_score",
    "reader_demand_score",
    "views",
    "view_count",
    "read_count",
    "priority_score",
)
RANK_FIELDS = ("popularity_rank", "priority_rank", "rank")
PROVIDER_RUN_DIR = RUN_ROOT / "bengali_tts_provider_bakeoff_20260705T205630Z"


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def rel_path(path: Path | str) -> str:
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = (ROOT / resolved).resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except Exception:
        return str(path)


def normalize_title(value: str) -> str:
    value = re.sub(r"\s*/\s*.*$", "", value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalize_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", (value or "").strip().lower()).strip("-")


def is_bengali_book(book: dict[str, Any]) -> bool:
    language = str(book.get("language") or book.get("lang") or "").strip().lower()
    title = str(book.get("title") or "")
    return language in {"bn", "ben", "bengali"} or any("\u0980" <= ch <= "\u09ff" for ch in title)


def slug_from_record(book: dict[str, Any]) -> str:
    for key in ("slug", "bookslug", "book_slug"):
        if book.get(key):
            return normalize_slug(str(book[key]))
    return normalize_slug(str(book.get("id") or ""))


def load_manifest(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path, {})
    books = payload.get("books") if isinstance(payload, dict) else payload
    return [book for book in books or [] if isinstance(book, dict)]


def controlled_publications() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for public_book_path in sorted((ROOT / "data" / "controlled_publications").glob("*/public_book.json")):
        public_book = read_json(public_book_path, {})
        if not isinstance(public_book, dict):
            continue
        title = str(public_book.get("title") or "").strip()
        if not is_bengali_book({"language": public_book.get("language"), "title": title}):
            continue
        rows.append(
            {
                "slug": public_book_path.parent.name,
                "title": title,
                "author": public_book.get("author") or "",
                "source": "controlled_publications",
                "controlled_publication_path": str(public_book_path.relative_to(ROOT)),
                "reader_manifest_exists": (public_book_path.parent / "reader_manifest.json").exists(),
                "source_evidence_exists": (public_book_path.parent / "source_evidence.json").exists(),
                "chapter_count": len(list((public_book_path.parent / "chapters").glob("*.json"))),
            }
        )
    return rows


def explicit_popularity(book: dict[str, Any]) -> tuple[float | None, str]:
    for field in POPULARITY_FIELDS:
        if field in book and book[field] not in ("", None):
            try:
                return float(book[field]), f"manifest:{field}"
            except Exception:
                pass
    for field in RANK_FIELDS:
        if field in book and book[field] not in ("", None):
            try:
                rank = max(float(book[field]), 1.0)
                return round(100000.0 / rank, 4), f"manifest_inverse_rank:{field}"
            except Exception:
                pass
    return None, ""


def title_popularity(title: str) -> tuple[float, str]:
    canonical = normalize_title(title)
    for popular_title, score in CURATED_POPULARITY.items():
        if normalize_title(popular_title) == canonical:
            return score, "curated_bengali_classics_popularity"
    if "রবীন্দ্রনাথ" in title:
        return 60.0, "fallback_author_signal"
    return 50.0, "fallback_manifest_or_controlled_order"


def terminal_exclusions(path: Path) -> set[str]:
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8", errors="replace")
    return {normalize_slug(item) for item in re.split(r"[,\s]+", text) if normalize_slug(item)}


def map_manifest_to_controlled(manifest_books: list[dict[str, Any]], controlled: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_title_author: dict[tuple[str, str], dict[str, Any]] = {}
    by_title: dict[str, dict[str, Any]] = {}
    for row in controlled:
        title_key = normalize_title(str(row.get("title") or ""))
        author_key = str(row.get("author") or "").strip()
        by_title_author[(title_key, author_key)] = row
        by_title.setdefault(title_key, row)

    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, book in enumerate(manifest_books):
        if not is_bengali_book(book):
            continue
        title = normalize_title(str(book.get("title") or ""))
        author = str(book.get("author") or "").strip()
        controlled_row = by_title_author.get((title, author)) or by_title.get(title)
        slug = controlled_row.get("slug") if controlled_row else slug_from_record(book)
        if not slug or slug in seen:
            continue
        seen.add(slug)
        explicit, explicit_source = explicit_popularity(book)
        fallback, fallback_source = title_popularity(title)
        popularity_score = explicit if explicit is not None else fallback
        candidates.append(
            {
                "slug": slug,
                "title": title,
                "author": author,
                "manifest_id": book.get("id") or "",
                "manifest_index": index + 1,
                "popularity_score": popularity_score,
                "popularity_source": explicit_source or fallback_source,
                "controlled_publication_exists": bool(controlled_row),
                "reader_manifest_exists": bool(controlled_row and controlled_row.get("reader_manifest_exists")),
                "source_evidence_exists": bool(controlled_row and controlled_row.get("source_evidence_exists")),
                "chapter_count": int(controlled_row.get("chapter_count", 0)) if controlled_row else 0,
            }
        )
    for row in controlled:
        slug = str(row.get("slug") or "")
        if not slug or slug in seen:
            continue
        seen.add(slug)
        score, source = title_popularity(str(row.get("title") or ""))
        candidates.append(
            {
                "slug": slug,
                "title": normalize_title(str(row.get("title") or "")),
                "author": row.get("author") or "",
                "manifest_id": "",
                "manifest_index": 999999,
                "popularity_score": score,
                "popularity_source": source,
                "controlled_publication_exists": True,
                "reader_manifest_exists": bool(row.get("reader_manifest_exists")),
                "source_evidence_exists": bool(row.get("source_evidence_exists")),
                "chapter_count": int(row.get("chapter_count") or 0),
            }
        )
    return candidates


def score_repair_path(row: dict[str, Any], excluded: set[str]) -> dict[str, Any]:
    slug = str(row["slug"])
    if slug == "book-63afd5e9be":
        return {
            "status": "excluded",
            "reason": "book-63afd5e9be remains a separate Bengali audiobook R&D blocker.",
            "cheapest_safe_path": "skip",
        }
    if slug in excluded:
        return {
            "status": "fresh_provider_only",
            "reason": "slug has terminal catalog evidence, typically stale/local audio mismatch; do not reuse stale audio.",
            "cheapest_safe_path": "clean-manuscript provider audition only; no local-audio reuse",
        }
    if not row.get("controlled_publication_exists"):
        return {
            "status": "needs_controlled_source",
            "reason": "no controlled publication found for slug/title mapping.",
            "cheapest_safe_path": "content/source preflight before any audio spend",
        }
    if not row.get("source_evidence_exists") or not row.get("reader_manifest_exists") or not row.get("chapter_count"):
        return {
            "status": "preflight_required",
            "reason": "controlled source/reader/chapter evidence is incomplete.",
            "cheapest_safe_path": "source/content/rights preflight before any audio spend",
        }
    return {
        "status": "provider_audition_ready",
        "reason": "controlled publication evidence is present; use clean manuscript only.",
        "cheapest_safe_path": "reuse existing Sarvam bakeoff if passage overlaps; otherwise short Sarvam audition only after OpenAI judge quota probe passes",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan Bengali audiobook go-live credit use by popularity.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output-dir", default=str(RUN_ROOT))
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--budget-usd", type=float, default=float(os.environ.get("EARNALISM_BENGALI_BAKEOFF_MAX_ESTIMATED_USD", "25") or 25))
    parser.add_argument("--exclude-file", default=str(RUN_ROOT / "terminal_blocker_exclusions.txt"))
    parser.add_argument("--provider-run-dir", default=str(PROVIDER_RUN_DIR))
    args = parser.parse_args()

    manifest = load_manifest(Path(args.manifest))
    controlled = controlled_publications()
    excluded = terminal_exclusions(Path(args.exclude_file))
    candidates = map_manifest_to_controlled(manifest, controlled)
    for row in candidates:
        row.update(score_repair_path(row, excluded))
    ranked = sorted(
        candidates,
        key=lambda item: (
            -float(item.get("popularity_score") or 0),
            0 if item.get("status") == "provider_audition_ready" else 1,
            int(item.get("manifest_index") or 999999),
            str(item.get("slug")),
        ),
    )
    top = ranked[: max(1, args.top_n)]
    reusable_bakeoff_report = read_json(Path(args.provider_run_dir) / "bengali_tts_provider_bakeoff_report.json", {})
    quota_status = reusable_bakeoff_report.get("quota_probe_status", "UNKNOWN")
    selected_for_existing_resume = [
        row for row in top if row["slug"] in {"book-ac5a71075e", "book-1090573dff", "book-4b944e64fa"}
    ]
    if len(selected_for_existing_resume) < 3:
        for slug in ("book-ac5a71075e", "book-1090573dff", "book-4b944e64fa"):
            match = next((row for row in ranked if row["slug"] == slug), None)
            if match and match not in selected_for_existing_resume:
                selected_for_existing_resume.append(match)

    resume_command = (
        "railway run --project a8533934-35c4-463e-9f43-577a9ac391ee "
        "--service 5af42e7e-f518-4f6a-b602-d9950866501f "
        "--environment 580b250c-80ee-48ad-bfbe-fa4e31a6b378 -- env "
        "EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF=true "
        f"EARNALISM_BENGALI_BAKEOFF_MAX_ESTIMATED_USD={min(args.budget_usd, 10):g} "
        "EARNALISM_STOP_ON_BUDGET_EXCEEDED=true "
        "EARNALISM_ENABLE_OPENAI_LISTENING_QA=true "
        "EARNALISM_OPENAI_LISTENING_QA_MODEL=gpt-audio "
        "python3 internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py "
        "--manifest book_import_manifest.json "
        "--candidate-slugs book-ac5a71075e,book-1090573dff,book-4b944e64fa "
        "--providers sarvam,google,azure,openai "
        f"--run-dir {args.provider_run_dir} "
        "--resume-existing-samples --judge-existing-only --target-near-pass-only --no-new-synthesis "
        "--max-passages 5 --max-seconds-per-sample 75 --fail-closed"
    )

    second_pass_command = (
        "railway run --project a8533934-35c4-463e-9f43-577a9ac391ee "
        "--service 5af42e7e-f518-4f6a-b602-d9950866501f "
        "--environment 580b250c-80ee-48ad-bfbe-fa4e31a6b378 -- env "
        "EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF=true "
        f"EARNALISM_BENGALI_BAKEOFF_MAX_ESTIMATED_USD={min(args.budget_usd, 15):g} "
        "EARNALISM_STOP_ON_BUDGET_EXCEEDED=true "
        "EARNALISM_ENABLE_OPENAI_LISTENING_QA=true "
        "EARNALISM_OPENAI_LISTENING_QA_MODEL=gpt-audio "
        "python3 internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py "
        "--manifest book_import_manifest.json "
        "--candidate-slugs book-ac5a71075e,book-1090573dff,book-4b944e64fa "
        "--providers sarvam "
        "--target-near-pass-only "
        "--second-pass-polish "
        "--max-voices-per-provider 4 "
        "--max-passages 5 --max-seconds-per-sample 75 --fail-closed"
    )

    pilot_candidates = [row for row in ranked if row["slug"] != "book-63afd5e9be" and row.get("controlled_publication_exists")]
    payload = {
        "generated_at": iso_now(),
        "objective": "Use OpenAI listening QA and Sarvam TTS credits in the cheapest fail-closed order for Bengali audiobook go-live.",
        "acceptance_thresholds": {
            "schema": 3,
            "minimum_required_score": 9.7,
            "minimum_confidence": 0.95,
            "publish_below_threshold": False,
        },
        "manifest_path": rel_path(args.manifest),
        "bengali_manifest_count": sum(1 for book in manifest if is_bengali_book(book)),
        "bengali_controlled_publication_count": len(controlled),
        "popularity_policy": {
            "primary": "explicit manifest popularity/priority fields when present",
            "fallback": "curated Bengali classics popularity list, then manifest order",
            "note": "The current manifest has no explicit popularity fields, so fallback scoring is active.",
        },
        "credit_policy": [
            "Run OpenAI listening-QA quota probe first.",
            "Judge existing Sarvam samples before any new synthesis.",
            "Generate only near-pass Sarvam second-pass samples if quota is available and existing samples remain near-pass.",
            "Select one full pilot only after a 9.7+ audition; do not auto-run full pilot without explicit full-pilot approval.",
            "Do not reuse stale local Bengali audio.",
        ],
        "provider_bakeoff_status": {
            "latest_report": rel_path(Path(args.provider_run_dir) / "bengali_tts_provider_bakeoff_report.json"),
            "quota_probe_status": quota_status,
            "best_provider": reusable_bakeoff_report.get("best_provider", ""),
            "best_voice": reusable_bakeoff_report.get("best_voice", ""),
            "best_score": reusable_bakeoff_report.get("best_score", 0),
            "best_confidence": reusable_bakeoff_report.get("best_confidence", 0),
            "existing_samples_reused": reusable_bakeoff_report.get("existing_samples_reused", 0),
            "new_samples_generated": reusable_bakeoff_report.get("new_samples_generated", 0),
        },
        "top_popularity_ranked_bengali_candidates": top,
        "selected_existing_sample_resume_candidates": selected_for_existing_resume,
        "pilot_candidate_order_after_audition_pass": pilot_candidates[:10],
        "estimated_cost_policy": {
            "current_budget_usd": args.budget_usd,
            "phase_1_existing_sample_judging_usd": "OpenAI listening QA only; no Sarvam synthesis.",
            "phase_2_near_pass_polish_usd": "capped by EARNALISM_BENGALI_BAKEOFF_MAX_ESTIMATED_USD and only after quota probe passes.",
            "phase_3_full_pilot_usd": "not run by this planner; requires EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS=true after audition pass.",
        },
        "next_commands": {
            "phase_1_resume_existing_samples": resume_command,
            "phase_2_near_pass_sarvam_polish_after_phase_1": second_pass_command,
        },
    }
    output_dir = Path(args.output_dir)
    output_path = output_dir / "bengali_credit_go_live_accelerator_plan.json"
    write_json(output_path, payload)
    md_path = output_dir / "bengali_credit_go_live_accelerator_plan.md"
    lines = [
        "# Bengali Credit Go-Live Accelerator Plan",
        "",
        f"Generated: `{payload['generated_at']}`",
        "",
        "## Status",
        "",
        f"- Latest quota probe status: `{quota_status}`",
        f"- Best observed provider/voice: `{payload['provider_bakeoff_status']['best_provider']}/{payload['provider_bakeoff_status']['best_voice']}`",
        f"- Best observed score: `{payload['provider_bakeoff_status']['best_score']}`",
        f"- Existing samples reused: `{payload['provider_bakeoff_status']['existing_samples_reused']}`",
        "",
        "## Top Bengali Candidates By Popularity",
        "",
    ]
    for index, row in enumerate(top[:15], 1):
        lines.append(
            f"{index}. `{row['slug']}` - {row['title']} - score `{row['popularity_score']}` - `{row['status']}` - {row['cheapest_safe_path']}"
        )
    lines.extend(["", "## Next Command", "", "```bash", resume_command, "```", ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "PLAN_WRITTEN", "plan_path": str(output_path.relative_to(ROOT)), "top_candidate": top[0] if top else None}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
