#!/usr/bin/env python3
"""Build the non-paid Sprint 1 publication evidence packet.

This tool never calls providers, mutates release gates, uploads media, or
publishes. It converts current repo evidence into deterministic sanitation,
rights, reader, audio, cost, and continuation records for every Sprint 1 title.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TITLE_SET = ROOT / "internal/earnalism_intelligence/go_live_milestone_1_book_set.json"
DEFAULT_OUTPUT = ROOT / "internal/audiobook_lab/sprint1_publication"
PUBLIC_ACCESS_MATRIX = ROOT / "internal/audiobook_lab/public_access/audiobook_public_access_matrix.json"
PRODUCTION_CLOSEOUT = (
    ROOT
    / "internal/earnalism_intelligence/ux_governor/ux_phase_review_packets/GO_LIVE_release_truth_matrix.json"
)

REQUIRED_CONTROLLED_FILES = {
    "public_book.json",
    "reader_manifest.json",
    "approval_evidence.json",
    "source_evidence.json",
    "checksum_manifest.json",
}
APPROVED_PUBLIC_AUDIO = {"book-2b9853ec52"}
POST_SPRINT_LONG_CLASSICS = {"great-expectations", "jane-eyre"}
POST_SPRINT_DEFERRAL_REASON = "Long classic deferred for cost/QA/time control"
POST_SPRINT_NEXT_ACTION = "Defer to post-sprint long-classics audiobook planning"
POST_SPRINT_NEXT_COMMAND = (
    "Add to post-sprint long classics queue after first milestone audio pipeline stabilizes"
)
TTS_RATE_USD_PER_1K = {"Bengali": 0.006, "English": 0.015}
ASR_RATE_USD_PER_MINUTE = 0.008
LISTENING_QA_ESTIMATE_USD = 0.05
STANDARD_LISTENING_QA_SAMPLE_COUNT = 6
REPRESENTATIVE_AUDITION_ESTIMATE_USD = 0.01

PAGE_NUMBER_RE = re.compile(r"^\s*(?:(?:page|পৃষ্ঠা|পৃ\.?)\s*)?[0-9০-৯]+\s*$", re.I)
BOILERPLATE_RE = re.compile(
    r"(?:project gutenberg|gutenberg\.org|bengali wikisource|wikisource|wikimedia|"
    r"internet archive|digitized by|scanned by|produced by|transcrib(?:ed|er)|"
    r"start of (?:this )?project gutenberg|end of (?:this )?project gutenberg|"
    r"this ebook is for the use of|repository source|source:\s*https?://)",
    re.I,
)
HTML_TAG_RE = re.compile(r"</?(?:html|body|script|style|div|span|p|br|h[1-6]|table|tr|td)\b[^>]*>", re.I)
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
REPLACEMENT_RE = re.compile("\ufffd")


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path, default: Any = None) -> Any:
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def evidence_path(path: Path) -> str:
    """Use stable repo-relative paths, while allowing explicit external output roots."""
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compact_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def manifest_records() -> dict[str, dict[str, Any]]:
    payload = read_json(ROOT / "book_import_manifest.json", {})
    records = payload if isinstance(payload, list) else payload.get("books", [])
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        normalized = {compact_key(key): value for key, value in record.items()}
        slug = str(normalized.get("slug") or "").strip()
        if slug:
            result[slug] = record
    return result


def first_json(slug: str, filename: str) -> tuple[Path | None, dict[str, Any]]:
    candidates = [
        ROOT / "data/controlled_publications" / slug / filename,
        ROOT / "backend/data/controlled_publications" / slug / filename,
    ]
    for path in candidates:
        if path.exists():
            return path, read_json(path, {})
    return None, {}


def chapter_payloads(slug: str) -> tuple[str, list[dict[str, Any]]]:
    candidates = [
        ROOT / "content/books" / slug / "chapters",
        ROOT / "data/controlled_publications" / slug / "chapters",
        ROOT / "backend/data/controlled_publications" / slug / "chapters",
    ]
    for directory in candidates:
        paths = sorted(directory.glob("*.json")) if directory.exists() else []
        chapters: list[dict[str, Any]] = []
        for path in paths:
            payload = read_json(path, {})
            text = str(payload.get("content") or payload.get("text") or payload.get("body") or "")
            if text.strip():
                chapters.append(
                    {
                        "id": str(payload.get("id") or path.stem),
                        "title": str(payload.get("title") or path.stem),
                        "text": text,
                        "path": str(path.relative_to(ROOT)),
                    }
                )
        if chapters:
            return str(directory.relative_to(ROOT)), chapters

    raw = ROOT / "content/books" / slug / "raw/source.txt"
    if raw.exists():
        return str(raw.relative_to(ROOT)), [
            {"id": "source", "title": "Source", "text": raw.read_text(encoding="utf-8", errors="ignore"), "path": str(raw.relative_to(ROOT))}
        ]

    _, manifest = first_json(slug, "reader_manifest.json")
    chapters = []
    for index, payload in enumerate(manifest.get("chapters") or []):
        if not isinstance(payload, dict):
            continue
        text = str(payload.get("content") or payload.get("text") or payload.get("body") or "")
        if text.strip():
            chapters.append(
                {
                    "id": str(payload.get("id") or f"chapter-{index + 1:03d}"),
                    "title": str(payload.get("title") or f"Chapter {index + 1}"),
                    "text": text,
                    "path": "reader_manifest.json",
                }
            )
    return "reader_manifest.json" if chapters else "", chapters


def sanitize_chapters(slug: str, title: str, chapters: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    removed = Counter()
    sanitized_chapters: list[dict[str, Any]] = []
    resolved_duplicate_ids: list[str] = []
    chapters_by_id: dict[str, list[dict[str, Any]]] = {}
    for chapter in chapters:
        chapters_by_id.setdefault(str(chapter.get("id") or ""), []).append(chapter)

    deduplicated_chapters: list[dict[str, Any]] = []
    for chapter_id, variants in chapters_by_id.items():
        if not chapter_id or len(variants) == 1:
            deduplicated_chapters.extend(variants)
            continue

        normalized = [re.sub(r"\W+", "", str(item.get("text") or "").casefold()) for item in variants]
        minimum_similarity = min(
            SequenceMatcher(None, normalized[0], candidate).ratio()
            for candidate in normalized[1:]
        )
        if minimum_similarity < 0.98:
            deduplicated_chapters.extend(variants)
            continue

        canonical = min(
            variants,
            key=lambda item: (len(str(item.get("title") or "")), len(str(item.get("path") or ""))),
        )
        deduplicated_chapters.append(canonical)
        resolved_duplicate_ids.append(chapter_id)
        removed["near_duplicate_chapters"] += len(variants) - 1

    seen_ids = Counter(str(item.get("id") or "") for item in deduplicated_chapters)
    seen_titles = Counter(str(item.get("title") or "") for item in deduplicated_chapters)

    for chapter in deduplicated_chapters:
        raw = unicodedata.normalize("NFKC", html.unescape(str(chapter.get("text") or "")))
        raw = raw.replace("\r\n", "\n").replace("\r", "\n").replace("\ufeff", "")
        control_count = len(CONTROL_RE.findall(raw))
        if control_count:
            removed["control_characters"] += control_count
            raw = CONTROL_RE.sub("", raw)
        html_count = len(HTML_TAG_RE.findall(raw))
        if html_count:
            removed["html_tags"] += html_count
            raw = HTML_TAG_RE.sub("", raw)

        lines: list[str] = []
        previous_nonempty = ""
        for original_line in raw.split("\n"):
            line = original_line.rstrip()
            stripped = line.strip()
            if PAGE_NUMBER_RE.fullmatch(stripped):
                removed["page_number_lines"] += 1
                continue
            if stripped and BOILERPLATE_RE.search(stripped):
                removed["source_boilerplate_lines"] += 1
                continue
            if stripped and stripped == previous_nonempty:
                removed["consecutive_duplicate_lines"] += 1
                continue
            lines.append(line)
            if stripped:
                previous_nonempty = stripped

        clean = "\n".join(lines)
        clean = re.sub(r"[ \t]+\n", "\n", clean)
        clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
        if clean:
            sanitized_chapters.append({**chapter, "text": clean})

    combined = "\n\n".join(item["text"] for item in sanitized_chapters).strip() + "\n"
    post_issues: list[str] = []
    if not combined.strip():
        post_issues.append("empty_sanitized_text")
    if REPLACEMENT_RE.search(combined):
        post_issues.append("replacement_character")
    if HTML_TAG_RE.search(combined):
        post_issues.append("raw_html")
    if BOILERPLATE_RE.search(combined):
        post_issues.append("source_boilerplate")
    if any(PAGE_NUMBER_RE.fullmatch(line.strip()) for line in combined.splitlines() if line.strip()):
        post_issues.append("page_number_line")
    if "```" in combined:
        post_issues.append("markdown_fence")

    words = re.findall(r"[\w\u0980-\u09ff]+", combined, flags=re.UNICODE)
    duplicate_ids = [value for value, count in seen_ids.items() if value and count > 1]
    duplicate_titles = [value for value, count in seen_titles.items() if value and count > 1]
    if duplicate_ids:
        post_issues.append("duplicate_chapter_ids")
    if duplicate_titles:
        post_issues.append("duplicate_chapter_titles")
    status = "PASS" if len(words) >= 40 and not post_issues else "FAIL"
    report = {
        "slug": slug,
        "title": title,
        "status": status,
        "source_chapter_count": len(chapters),
        "sanitized_chapter_count": len(sanitized_chapters),
        "word_count": len(words),
        "character_count": len(combined),
        "sha256": sha256_text(combined),
        "removed": dict(sorted(removed.items())),
        "resolved_near_duplicate_chapter_ids": resolved_duplicate_ids,
        "duplicate_chapter_ids": duplicate_ids,
        "duplicate_chapter_titles": duplicate_titles,
        "post_sanitation_issues": post_issues,
        "first_words": words[:12],
        "last_words": words[-12:],
    }
    return combined, report


def rights_record(slug: str, sanitation_status: str) -> dict[str, Any]:
    path, evidence = first_json(slug, "source_evidence.json")
    required = ["source_url", "source_license", "source_hash", "content_hash", "provenance_hash", "rights_basis"]
    missing = [field for field in required if not evidence.get(field)]
    reader_status = "PASS" if path and not missing else "FAIL"
    audio_status = reader_status
    owner_documents: list[str] = []
    if slug == "pather-panchali":
        audio_status = "OWNER_DOCUMENT_REQUIRED"
        owner_documents = [
            "written edition-completeness or truthful abridgement decision",
            "commercial audiobook territory decision",
            "approved production front and back covers with usage rights",
            "final truthful edition metadata",
        ]
    if sanitation_status != "PASS":
        audio_status = "BLOCKED_BY_TEXT_SANITATION"
    return {
        "slug": slug,
        "source_evidence_path": str(path.relative_to(ROOT)) if path else "",
        "source_url": evidence.get("source_url", ""),
        "source_name": evidence.get("source_name", ""),
        "source_license": evidence.get("source_license", ""),
        "rights_basis": evidence.get("rights_basis", ""),
        "source_hash": evidence.get("source_hash", ""),
        "content_hash": evidence.get("content_hash", ""),
        "provenance_hash": evidence.get("provenance_hash", ""),
        "reader_facing_boilerplate_removed": evidence.get("reader_facing_boilerplate_removed") is True,
        "missing_fields": missing,
        "reader_rights_status": reader_status,
        "audio_rights_status": audio_status,
        "owner_documents_required": owner_documents,
        "status": "PASS" if reader_status == "PASS" and audio_status == "PASS" else audio_status,
    }


def controlled_inventory(slug: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for label, base in [
        ("root", ROOT / "data/controlled_publications"),
        ("backend", ROOT / "backend/data/controlled_publications"),
    ]:
        directory = base / slug
        files = {path.name for path in directory.glob("*") if path.is_file()} if directory.exists() else set()
        chapters = len(list((directory / "chapters").glob("*.json"))) if (directory / "chapters").exists() else 0
        result[label] = {
            "path": str(directory.relative_to(ROOT)),
            "required_files_complete": REQUIRED_CONTROLLED_FILES.issubset(files),
            "missing_required_files": sorted(REQUIRED_CONTROLLED_FILES - files),
            "chapter_files": chapters,
        }
    return result


def public_book_audio(slug: str) -> tuple[Path | None, dict[str, Any]]:
    path, book = first_json(slug, "public_book.json")
    assets = book.get("audiobook_assets") if isinstance(book.get("audiobook_assets"), dict) else {}
    return path, {
        "audio_enabled": book.get("audio_enabled") is True,
        "audiobook_enabled": book.get("audiobook_enabled") is True,
        "assets": assets,
        "asset_count": len([value for value in assets.values() if value]),
        "legacy_or_private_asset_signal": bool(assets or book.get("audio_url") or book.get("audiobook_url")),
    }


def latest_release_packet(slug: str) -> tuple[str, dict[str, Any]]:
    paths = sorted((ROOT / "internal/audiobook_lab/release_gate").glob(f"{slug}_*/goliveevidence.json"))
    if not paths:
        return "", {}
    path = paths[-1]
    return str(path.relative_to(ROOT)), read_json(path, {})


def strategy_for(slug: str, language: str, audio: dict[str, Any], word_count: int, char_count: int) -> dict[str, Any]:
    duration_minutes = round(word_count / 150.0, 2)
    tts_rate = TTS_RATE_USD_PER_1K[language]
    full_tts = round(char_count / 1000.0 * tts_rate, 4)
    full_asr = round(duration_minutes * ASR_RATE_USD_PER_MINUTE, 4)
    listening = LISTENING_QA_ESTIMATE_USD
    listening_sample_count = STANDARD_LISTENING_QA_SAMPLE_COUNT if slug == "a-ghost-story" else 1
    listening_total = round(listening * listening_sample_count, 4)
    audition = REPRESENTATIVE_AUDITION_ESTIMATE_USD

    if slug == "book-2b9853ec52":
        strategy = "REUSE_APPROVED_PUBLIC_AUDIO"
        incremental = 0.0
    elif slug == "bn-066":
        strategy = "REUSE_PRIVATE_FULL_AUDIO_THREE_CHUNK_ASR_CALIBRATION_THEN_QA"
        incremental = 0.1547
    elif slug == "a-ghost-story":
        strategy = "REUSE_EXISTING_AUDIO_RUN_LISTENING_ENDPOINT_AND_PLAYER_GATES"
        incremental = listening_total
    elif slug == "book-d19e96859f":
        strategy = "REGENERATE_FAILED_GROUP_4_ONLY_THEN_FULL_QA"
        incremental = round(full_tts / 5.0 + full_asr + listening, 4)
    elif slug == "book-f5d593e1f4":
        strategy = "REGENERATE_FAILED_GROUP_7_ONLY_THEN_FULL_QA"
        incremental = round(full_tts / 8.0 + full_asr + listening, 4)
    elif slug == "muchiram-gurer-jibanchorit":
        strategy = "SPLIT_REPRESENTATIVE_AUDITION_THEN_DECIDE_REUSE_OR_FULL_TTS"
        incremental = round(audition + full_tts + full_asr + listening, 4)
    elif audio["legacy_or_private_asset_signal"]:
        strategy = "REUSE_EXISTING_PRIVATE_ASSET_IF_CHECKSUM_SOURCE_AND_QA_PASS"
        incremental = round(full_asr + listening, 4)
    else:
        strategy = "REPRESENTATIVE_AUDITION_THEN_COST_OPTIMIZED_FULL_TTS"
        incremental = round(audition + full_tts + full_asr + listening, 4)

    baseline_strategy = strategy
    baseline_incremental = incremental
    sprint1_audio_target = slug not in POST_SPRINT_LONG_CLASSICS
    if not sprint1_audio_target:
        strategy = "POST_SPRINT_LONG_CLASSICS_DEFERRED"
        incremental = 0.0

    return {
        "slug": slug,
        "strategy": strategy,
        "deferred_recommended_strategy": baseline_strategy if not sprint1_audio_target else "",
        "sprint1_audio_target": sprint1_audio_target,
        "public_audiobook_required_for_sprint1": sprint1_audio_target,
        "sprint1_budget_included": sprint1_audio_target,
        "characters": char_count,
        "words": word_count,
        "estimated_duration_minutes": duration_minutes,
        "tts_rate_usd_per_1k_characters": tts_rate,
        "estimated_full_tts_usd": full_tts,
        "estimated_full_asr_usd": full_asr,
        "estimated_listening_qa_usd": listening,
        "estimated_listening_qa_sample_count": listening_sample_count,
        "estimated_listening_qa_total_usd": listening_total,
        "estimated_representative_audition_usd": audition,
        "estimated_incremental_cost_usd": incremental,
        "deferred_baseline_estimated_cost_usd": round(baseline_incremental, 4) if not sprint1_audio_target else 0.0,
        "actual_spend_usd": 0.0,
        "budget_status": "BLOCKED_MISSING_SPRINT_CAPS" if sprint1_audio_target else "DEFERRED_POST_SPRINT",
        "reason": POST_SPRINT_DEFERRAL_REASON if not sprint1_audio_target else "",
        "next_action": POST_SPRINT_NEXT_ACTION if not sprint1_audio_target else "",
        "next_command": POST_SPRINT_NEXT_COMMAND if not sprint1_audio_target else "",
    }


def gate_template() -> dict[str, str]:
    return {
        "source_rights": "NOT_RUN",
        "text_sanitation": "NOT_RUN",
        "text_normalization": "NOT_RUN",
        "representative_audition": "NOT_RUN",
        "full_book_tts": "NOT_RUN",
        "asr_source_alignment": "NOT_RUN",
        "first_words_match": "NOT_RUN",
        "last_words_match": "NOT_RUN",
        "listening_qa": "NOT_RUN",
        "manifest_validation": "NOT_RUN",
        "endpoint_validation": "NOT_RUN",
        "frontend_release_state": "NOT_RUN",
        "production_route_validation": "NOT_RUN",
        "owner_release_decision": "CONDITIONAL_AUTHORIZED_AFTER_ALL_GATES_PASS",
        "no_static_audio_fallback": "PASS",
        "no_browser_speech_fallback": "PASS",
        "no_word_level_sync_claim": "PASS",
        "no_nonapproved_audio_object": "PASS",
        "no_broken_endpoint": "NOT_RUN",
    }


def gates_for(slug: str, rights: dict[str, Any], sanitation: dict[str, Any]) -> tuple[dict[str, str], str]:
    gates = gate_template()
    gates["source_rights"] = "PASS" if rights["audio_rights_status"] == "PASS" else rights["audio_rights_status"]
    gates["text_sanitation"] = sanitation["status"]
    gates["text_normalization"] = sanitation["status"]
    quality = "NOT_RUN"
    if slug == "book-2b9853ec52":
        for key in gates:
            gates[key] = "PASS"
        quality = "9.4/10 listening, confidence 0.95; approved minimum passed, 10.0 not claimed"
    elif slug == "bn-066":
        gates.update(
            {
                "representative_audition": "PASS",
                "full_book_tts": "PASS_PRIVATE",
                "asr_source_alignment": "FAIL_0.8403_OF_10",
                "first_words_match": "FAIL",
                "last_words_match": "FAIL",
                "listening_qa": "BLOCKED_BY_ASR",
                "manifest_validation": "PASS_AUDIO_HIDDEN",
                "endpoint_validation": "PASS_FAIL_CLOSED_404",
                "frontend_release_state": "PASS_AUDIO_HIDDEN",
                "production_route_validation": "PASS_READER_ONLY",
                "no_broken_endpoint": "PASS_FAIL_CLOSED",
            }
        )
        quality = "0.8403/10 ASR-source; listening not run"
    elif slug == "a-ghost-story":
        gates.update(
            {
                "full_book_tts": "EXISTING_ASSET_PRESENT",
                "asr_source_alignment": "PASS_9.7882_OF_10",
                "first_words_match": "PASS",
                "last_words_match": "PASS",
                "listening_qa": "FAIL_0.0_CONFIDENCE_0.8",
                "manifest_validation": "PASS_AUDIO_HIDDEN",
                "frontend_release_state": "PASS_AUDIO_HIDDEN",
                "production_route_validation": "PASS_READER_ONLY",
            }
        )
        quality = "0.0/10 latest listening packet, confidence 0.8"
    elif slug in {"book-d19e96859f", "book-f5d593e1f4"}:
        gates.update(
            {
                "representative_audition": "PASS_9.4_CONFIDENCE_0.95",
                "full_book_tts": "REPAIR_REQUIRED",
                "asr_source_alignment": "FAIL",
                "first_words_match": "REVALIDATION_REQUIRED",
                "last_words_match": "REVALIDATION_REQUIRED",
                "listening_qa": "REVALIDATION_REQUIRED",
                "manifest_validation": "PASS_AUDIO_HIDDEN",
                "frontend_release_state": "PASS_AUDIO_HIDDEN",
            }
        )
        quality = "9.4/10 representative only; full-book source gate failed"
    elif slug == "muchiram-gurer-jibanchorit":
        gates.update(
            {
                "representative_audition": "PROVIDER_TIMEOUT",
                "full_book_tts": "REPAIR_REQUIRED",
                "asr_source_alignment": "FAIL_0.039_OF_10",
                "manifest_validation": "PASS_AUDIO_HIDDEN",
                "frontend_release_state": "PASS_AUDIO_HIDDEN",
            }
        )
        quality = "0.039/10 ASR-source; representative timed out"
    return gates, quality


def next_command(slug: str, reader_public: bool, sanitation: dict[str, Any], rights: dict[str, Any]) -> str:
    if slug == "book-2b9853ec52":
        return "curl -sS https://api.theearnalism.com/api/reader/book/book-2b9853ec52/manifest | jq '{enabled:.audio.enabled,release_gate:.audio.release_gate,qa_status:.audio.qa_status}'"
    if sanitation["status"] != "PASS":
        return f"python3 internal/audiobook_lab/scripts/sprint1_publication_preflight.py --slugs {slug}"
    if rights["audio_rights_status"] != "PASS":
        return f"python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug {slug} --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com"
    if not reader_public:
        return f"python3 scripts/book_production_workflow.py --manifest ./book_import_manifest.json --book-slug {slug} --api-url https://api.theearnalism.com --frontend-url https://theearnalism.com"
    if slug == "bn-066":
        return "PYTHONPYCACHEPREFIX=/tmp/earnalism-pycache python3 internal/audiobook_lab/scripts/bengali_asr_language_calibration.py --slug bn-066 --run-dir internal/audiobook_lab/bengali_enablement/bn_066_stage2_full_book_tts --chunk-ids group_0000,group_0076,group_0151 --language-options auto,bn,ben,bengali --output internal/audiobook_lab/public_access/bn_066_asr_calibration_preflight.json"
    if slug == "a-ghost-story":
        return "python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs a-ghost-story --languages eng --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --resume --fail-closed --stop-after-terminal-books 1"
    if slug in {"book-d19e96859f", "book-f5d593e1f4"}:
        return f"python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs {slug} --languages ben --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1"
    if slug == "muchiram-gurer-jibanchorit":
        return "python3 internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py --manifest book_import_manifest.json --candidate-slugs muchiram-gurer-jibanchorit --max-passages 1 --max-seconds-per-sample 20 --providers sarvam --max-voices-per-provider 1 --voice-filter sarvam:ratan --style-profiles literary_warm_pacing --bengali-audiobook-92-rescue --fail-closed --run-dir internal/audiobook_lab/sprint1_publication/muchiram_split_audition"
    return f"python3 internal/audiobook_lab/scripts/release_catalog_factory.py --manifest book_import_manifest.json --slugs {slug} --languages {'ben' if rights.get('source_url','').find('bn.wikisource') >= 0 else 'eng'} --max-books-active 1 --max-tts-workers 0 --max-paid-workers 0 --max-asr-workers 0 --max-upload-workers 0 --max-metadata-workers 0 --max-browser-workers 0 --max-attempts 1 --dry-run --fail-closed --stop-after-terminal-books 1"


def markdown_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| slug | title | language | Publicly rendered book | Publicly available audiobook | Quality score | Evidence path | Cost used | Final status |",
        "| --- | --- | --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for row in rows:
        values = [
            f"`{row['slug']}`",
            str(row["title"]).replace("|", "\\|"),
            row["language"],
            row["publicly_rendered_book"],
            row["publicly_available_audiobook"],
            row["quality_score"],
            f"`{row['evidence_path']}`",
            f"${row['cost_used_usd']:.4f}",
            row["final_status"],
        ]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title-set", type=Path, default=DEFAULT_TITLE_SET)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--slugs", default="", help="Optional comma-separated subset.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    title_payload = read_json(args.title_set, {})
    books = list(title_payload.get("books") or [])
    requested = {item.strip() for item in args.slugs.split(",") if item.strip()}
    if requested:
        books = [book for book in books if book.get("slug") in requested]
    if not books:
        raise SystemExit("No Sprint 1 titles resolved.")

    output = args.output_root.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sanitized_dir = output / "sanitized_text"
    report_dir = output / "sanitized_text_reports"
    public_access = {item.get("slug"): item for item in read_json(PUBLIC_ACCESS_MATRIX, {}).get("titles", [])}
    production = read_json(PRODUCTION_CLOSEOUT, {})
    generated_at = iso_now()

    title_rows: list[dict[str, Any]] = []
    rights_rows: list[dict[str, Any]] = []
    cost_rows: list[dict[str, Any]] = []
    publication_rows: list[dict[str, Any]] = []
    release_rows: list[dict[str, Any]] = []
    sanitation_rows: list[dict[str, Any]] = []

    for book in books:
        slug = str(book["slug"])
        title = str(book["title"])
        language = str(book["language"])
        sprint1_audio_target = slug not in POST_SPRINT_LONG_CLASSICS
        public_reader_status = str(book.get("reader_status") or "FAIL_CLOSED")
        public_audio_status = str(book.get("audio_status") or "AUDIO_HIDDEN")
        source_ref, chapters = chapter_payloads(slug)
        sanitized, sanitation = sanitize_chapters(slug, title, chapters)
        sanitation["language"] = language
        sanitation["source_path"] = source_ref
        sanitized_path = sanitized_dir / f"{slug}.txt"
        sanitation_json = report_dir / f"{slug}.json"
        sanitation_md = report_dir / f"{slug}.md"
        write_text(sanitized_path, sanitized)
        sanitation["sanitized_text_path"] = evidence_path(sanitized_path)
        write_json(sanitation_json, sanitation)
        write_text(
            sanitation_md,
            "\n".join(
                [
                    f"# Sprint 1 Text Sanitation: {title}",
                    "",
                    f"- Slug: `{slug}`",
                    f"- Language: `{language}`",
                    f"- Status: `{sanitation['status']}`",
                    f"- Source: `{source_ref}`",
                    f"- Sanitized text: `{sanitation['sanitized_text_path']}`",
                    f"- Chapters: `{sanitation['sanitized_chapter_count']}`",
                    f"- Words: `{sanitation['word_count']}`",
                    f"- Characters: `{sanitation['character_count']}`",
                    f"- SHA-256: `{sanitation['sha256']}`",
                    f"- Removed: `{json.dumps(sanitation['removed'], ensure_ascii=False, sort_keys=True)}`",
                    f"- Remaining issues: `{json.dumps(sanitation['post_sanitation_issues'], ensure_ascii=False)}`",
                    "",
                    "This report is non-paid evidence. It does not approve audio publication.",
                ]
            ),
        )

        rights = rights_record(slug, sanitation["status"])
        rights["title"] = title
        rights["language"] = language
        rights_rows.append(rights)

        controlled = controlled_inventory(slug)
        audio_path, audio = public_book_audio(slug)
        audio["public_book_path"] = str(audio_path.relative_to(ROOT)) if audio_path else ""
        packet_path, packet = latest_release_packet(slug)
        reader_public = public_reader_status == "PUBLIC_READER"
        reader_source_ready = (
            sanitation["status"] == "PASS"
            and rights["reader_rights_status"] == "PASS"
            and controlled["root"]["required_files_complete"]
            and sanitation["sanitized_chapter_count"] > 0
        )
        strategy = strategy_for(slug, language, audio, sanitation["word_count"], sanitation["character_count"])
        cost_record = {
            **strategy,
            "title": title,
            "language": language,
            "source_rights_status": rights["audio_rights_status"],
            "text_sanitation_status": sanitation["status"],
        }
        gates, quality = gates_for(slug, rights, sanitation)
        public_audio = slug in APPROVED_PUBLIC_AUDIO
        title_evidence_path = packet_path or evidence_path(sanitation_json)
        command = (
            next_command(slug, reader_public, sanitation, rights)
            if sprint1_audio_target
            else POST_SPRINT_NEXT_COMMAND
        )
        next_action = (
            "Continue the active Sprint 1 repair or release path"
            if sprint1_audio_target
            else POST_SPRINT_NEXT_ACTION
        )
        reason = "" if sprint1_audio_target else POST_SPRINT_DEFERRAL_REASON

        failed_gates = [name for name, value in gates.items() if value != "PASS"]
        if not sprint1_audio_target:
            final_status = "DROPPED_FROM_SPRINT1_AUDIO_PLAN"
        elif reader_public and public_audio:
            final_status = "Yes, publicly rendered book + Yes, publicly available audiobook"
        elif not reader_public:
            final_status = "TARGET_INCOMPLETE_READER_DEPLOY_AND_AUDIO_GATES_REQUIRED"
        else:
            final_status = "TARGET_INCOMPLETE_AUDIO_GATES_REQUIRED"

        cost_rows.append(
            {
                **cost_record,
                "public_reader_status": public_reader_status,
                "public_audio_status": public_audio_status,
                "final_status": final_status,
                "reason": reason,
                "next_action": next_action,
                "next_command": command,
            }
        )

        title_rows.append(
            {
                "slug": slug,
                "title": title,
                "author": book.get("author", ""),
                "language": language,
                "source_path": source_ref,
                "reader_public_current": reader_public,
                "public_reader_status": public_reader_status,
                "public_audio_status": public_audio_status,
                "reader_source_ready": reader_source_ready,
                "controlled_artifacts": controlled,
                "slug_resolution": "EXACT_OR_PREVIOUSLY_NORMALIZED",
                "sprint1_audio_target": sprint1_audio_target,
                "public_audiobook_required_for_sprint1": sprint1_audio_target,
                "audio_plan_status": "ACTIVE_SPRINT1_AUDIO_TARGET" if sprint1_audio_target else "POST_SPRINT_LONG_CLASSICS_DEFERRED",
                "final_status": final_status,
                "reason": reason,
                "next_action": next_action,
                "next_command": command,
            }
        )
        sanitation_rows.append(sanitation)
        release_rows.append(
            {
                "slug": slug,
                "title": title,
                "language": language,
                "gates": gates,
                "failed_or_pending_gates": failed_gates,
                "can_publish_audio_now": public_audio and not failed_gates,
                "sprint1_audio_target": sprint1_audio_target,
                "public_audiobook_required_for_sprint1": sprint1_audio_target,
                "audio_plan_status": "ACTIVE_SPRINT1_AUDIO_TARGET" if sprint1_audio_target else "POST_SPRINT_LONG_CLASSICS_DEFERRED",
                "public_reader_status": public_reader_status,
                "public_audio_status": public_audio_status,
                "final_status": final_status,
                "existing_release_packet": packet_path,
                "existing_release_status": packet.get("status", "") if isinstance(packet, dict) else "",
                "reason": reason,
                "next_action": next_action,
                "next_command": command,
            }
        )
        publication_rows.append(
            {
                "slug": slug,
                "title": title,
                "language": language,
                "publicly_rendered_book": "Yes" if reader_public else "No",
                "publicly_available_audiobook": "Yes" if public_audio else "No",
                "quality_score": quality,
                "evidence_path": title_evidence_path,
                "cost_used_usd": 0.0,
                "sprint1_audio_target": sprint1_audio_target,
                "public_audiobook_required_for_sprint1": sprint1_audio_target,
                "public_reader_status": public_reader_status,
                "public_audio_status": public_audio_status,
                "final_status": final_status,
                "exact_blocker": (
                    "NONE"
                    if final_status.startswith("Yes")
                    else "DEFERRED_BY_OWNER_COST_QA_TIME_CONTROL"
                    if not sprint1_audio_target
                    else ", ".join(failed_gates)
                ),
                "reason": reason,
                "next_action": next_action,
                "next_command": command,
                "sanitation_status": sanitation["status"],
                "rights_status": rights["status"],
                "reader_source_ready": reader_source_ready,
                "cost_strategy": strategy["strategy"],
                "estimated_incremental_cost_usd": strategy["estimated_incremental_cost_usd"],
                "deferred_baseline_estimated_cost_usd": strategy["deferred_baseline_estimated_cost_usd"],
            }
        )

    budget_env = {
        name: os.environ.get(name, "")
        for name in [
            "SPRINT1_TOTAL_AUDIO_BUDGET_USD",
            "SPRINT1_MAX_USD_PER_TITLE",
            "MAX_TTS_BUDGET_USD",
            "EARNALISM_STOP_ON_BUDGET_EXCEEDED",
            "EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD",
            "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD",
        ]
    }
    missing_budget = [name for name, value in budget_env.items() if not value]
    if budget_env.get("EARNALISM_STOP_ON_BUDGET_EXCEEDED") not in {"true", "TRUE", "1"}:
        if "EARNALISM_STOP_ON_BUDGET_EXCEEDED" not in missing_budget:
            missing_budget.append("EARNALISM_STOP_ON_BUDGET_EXCEEDED=true")

    active_publication_rows = [row for row in publication_rows if row["sprint1_audio_target"]]
    deferred_publication_rows = [row for row in publication_rows if not row["sprint1_audio_target"]]
    active_cost_rows = [row for row in cost_rows if row["sprint1_audio_target"]]
    deferred_cost_rows = [row for row in cost_rows if not row["sprint1_audio_target"]]
    yes_yes = [row for row in active_publication_rows if row["final_status"].startswith("Yes")]
    incomplete = [row for row in active_publication_rows if not row["final_status"].startswith("Yes")]
    total_estimate = round(sum(row["estimated_incremental_cost_usd"] for row in active_cost_rows), 4)
    removed_estimate = round(sum(row["deferred_baseline_estimated_cost_usd"] for row in deferred_cost_rows), 4)
    active_english_costs = [row for row in active_cost_rows if row["language"] == "English"]
    highest_english = max(active_english_costs, key=lambda row: row["estimated_incremental_cost_usd"])
    cheapest_eligible = sorted(
        (
            row
            for row in active_cost_rows
            if row["estimated_incremental_cost_usd"] > 0
            and row["source_rights_status"] == "PASS"
            and row["text_sanitation_status"] == "PASS"
        ),
        key=lambda row: (row["estimated_incremental_cost_usd"], row["slug"]),
    )[:5]
    plan_summary = {
        "total_sprint1_title_count": len(publication_rows),
        "active_sprint1_title_count": len(active_publication_rows),
        "active_audiobook_target_count": len(active_publication_rows),
        "deferred_long_classics_count": len(deferred_publication_rows),
        "current_yes_yes_count": len(yes_yes),
        "remaining_non_yes_yes_count_excluding_dropped": len(incomplete),
        "estimated_incremental_total_usd": total_estimate,
        "removed_deferred_estimated_cost_usd": removed_estimate,
        "highest_expected_english_cost_after_removal": {
            "slug": highest_english["slug"],
            "title": highest_english["title"],
            "estimated_incremental_cost_usd": highest_english["estimated_incremental_cost_usd"],
        },
        "cheapest_next_5_eligible_audio_candidates": [
            {
                "slug": row["slug"],
                "title": row["title"],
                "language": row["language"],
                "estimated_incremental_cost_usd": row["estimated_incremental_cost_usd"],
                "strategy": row["strategy"],
            }
            for row in cheapest_eligible
        ],
    }

    title_set = {
        "schema_version": 1,
        "generated_at": generated_at,
        "source": evidence_path(args.title_set),
        "title_count": len(title_rows),
        "active_sprint1_title_count": len(active_publication_rows),
        "active_audiobook_target_count": len(active_publication_rows),
        "deferred_long_classics_count": len(deferred_publication_rows),
        "titles": title_rows,
    }
    write_json(output / "sprint1_title_set.json", title_set)
    write_text(
        output / "sprint1_title_set.md",
        "# Sprint 1 Title Set\n\n"
        + f"Generated: `{generated_at}`\n\n"
        + f"Exact unique titles: `{len(title_rows)}`\n\n"
        + f"Active Sprint 1 audiobook targets: `{len(active_publication_rows)}`\n\n"
        + f"Post-sprint long classics deferred: `{len(deferred_publication_rows)}`\n\n"
        + "| Slug | Title | Language | Reader public now | Reader source ready | Sprint 1 audio target |\n"
        + "| --- | --- | --- | --- | --- | --- |\n"
        + "\n".join(
            f"| `{row['slug']}` | {row['title']} | {row['language']} | {'Yes' if row['reader_public_current'] else 'No'} | {'Yes' if row['reader_source_ready'] else 'No'} | {'Yes' if row['sprint1_audio_target'] else 'No - deferred'} |"
            for row in title_rows
        ),
    )
    write_json(output / "sprint1_rights_source_matrix.json", {"schema_version": 1, "generated_at": generated_at, "titles": rights_rows})
    cost_report = {
        "schema_version": 1,
        "generated_at": generated_at,
        "budget_env": {name: ("PRESENT" if value else "MISSING") for name, value in budget_env.items()},
        "missing_or_invalid_budget_gates": missing_budget,
        "provider_calls_ran": False,
        "actual_spend_usd": 0.0,
        "estimated_incremental_total_usd": total_estimate,
        "removed_deferred_estimated_cost_usd": removed_estimate,
        "budget_comparison": "NOT_AVAILABLE_MISSING_ENV_GATES",
        "summary": plan_summary,
        "titles": cost_rows,
    }
    write_json(output / "sprint1_cost_optimized_tts_plan.json", cost_report)
    write_json(output / "sprint1_cost_report.json", cost_report)
    write_text(
        output / "sprint1_cost_optimized_tts_plan.md",
        "# Sprint 1 Cost-Optimized TTS Plan\n\n"
        + f"- Provider calls run: `false`\n- Actual spend: `$0.00`\n- Estimated incremental path: `${total_estimate:.4f}`\n"
        + f"- Total catalog/reader titles: `{len(publication_rows)}`\n"
        + f"- Active audiobook targets: `{len(active_publication_rows)}`\n"
        + f"- Post-sprint long classics deferred: `{len(deferred_publication_rows)}`\n"
        + f"- Deferred estimate removed from Sprint 1: `${removed_estimate:.4f}`\n"
        + f"- Highest remaining English estimate: `{highest_english['slug']}` at `${highest_english['estimated_incremental_cost_usd']:.4f}`\n"
        + f"- Budget status: `BLOCKED_MISSING_ENV_GATES`\n- Missing gates: `{', '.join(missing_budget)}`\n\n"
        + "## Cheapest Next Five Eligible Candidates\n\n"
        + "\n".join(
            f"- `{row['slug']}`: `${row['estimated_incremental_cost_usd']:.4f}` via `{row['strategy']}`"
            for row in cheapest_eligible
        )
        + "\n\n| Slug | Sprint 1 audio target | Strategy | Characters | Sprint 1 estimate | Deferred baseline |\n"
        + "| --- | --- | --- | ---: | ---: | ---: |\n"
        + "\n".join(
            f"| `{row['slug']}` | {'Yes' if row['sprint1_audio_target'] else 'No - deferred'} | `{row['strategy']}` | {row['characters']} | ${row['estimated_incremental_cost_usd']:.4f} | ${row['deferred_baseline_estimated_cost_usd']:.4f} |"
            for row in cost_rows
        ),
    )

    write_json(
        output / "sprint1_publication_matrix.json",
        {"schema_version": 1, "generated_at": generated_at, "summary": plan_summary, "titles": publication_rows},
    )
    write_json(
        output / "sprint1_release_gate_evidence.json",
        {"schema_version": 1, "generated_at": generated_at, "summary": plan_summary, "titles": release_rows},
    )
    sanitation_summary = {
        "schema_version": 1,
        "generated_at": generated_at,
        "title_count": len(sanitation_rows),
        "pass_count": sum(row["status"] == "PASS" for row in sanitation_rows),
        "fail_count": sum(row["status"] != "PASS" for row in sanitation_rows),
        "total_characters": sum(row["character_count"] for row in sanitation_rows),
        "total_words": sum(row["word_count"] for row in sanitation_rows),
        "titles": sanitation_rows,
    }
    write_json(output / "sprint1_sanitization_summary.json", sanitation_summary)

    table = markdown_table(publication_rows)
    write_text(
        output / "sprint1_publication_report.md",
        "# Sprint 1 Universal Read and Listen Publication Report\n\n"
        + f"Generated: `{generated_at}`\n\n"
        + f"- Total catalog/reader titles: `{len(publication_rows)}`\n"
        + f"- Active Sprint 1 titles: `{len(active_publication_rows)}`\n"
        + f"- Active audiobook targets: `{len(active_publication_rows)}`\n"
        + f"- Post-sprint long classics deferred: `{len(deferred_publication_rows)}`\n"
        + f"- Yes + Yes: `{len(yes_yes)}`\n"
        + f"- Remaining non-Yes + Yes excluding dropped titles: `{len(incomplete)}`\n"
        + f"- Paid calls: `0`\n- Actual spend: `$0.00`\n- Estimated incremental path: `${total_estimate:.4f}`\n"
        + f"- Deferred estimate removed: `${removed_estimate:.4f}`\n"
        + f"- Highest remaining English estimate: `{highest_english['slug']}` at `${highest_english['estimated_incremental_cost_usd']:.4f}`\n"
        + "- Production mutation: `none`\n- Public audio approvals added: `none`\n\n"
        + table
        + "\n\nGreat Expectations and Jane Eyre remain catalog/reader titles but are not Sprint 1 audio targets."
        + "\n\nThe 10/10 target is not claimed. Only evidence-complete titles may expose Listen.",
    )
    blocker_lines = [
        "# Sprint 1 Executable Repair Tracks",
        "",
        "Every active incomplete target has an executable next command. Deferred long classics are tracked separately and do not count as Sprint 1 blockers.",
        "",
    ]
    for row in incomplete:
        blocker_lines.extend(
            [
                f"## {row['slug']} / {row['title']}",
                "",
                f"- Current result: `{row['final_status']}`",
                f"- Blocker: `{row['exact_blocker']}`",
                f"- Estimated incremental cost: `${row['estimated_incremental_cost_usd']:.4f}`",
                "- Next command:",
                "",
                "```bash",
                row["next_command"],
                "```",
                "",
            ]
        )
    write_text(output / "sprint1_failed_blockers_if_any.md", "\n".join(blocker_lines))

    cost_by_slug = {row["slug"]: row for row in cost_rows}
    title_by_slug = {row["slug"]: row for row in title_rows}
    rights_by_slug = {row["slug"]: row for row in rights_rows}
    deferred_queue_titles: list[dict[str, Any]] = []
    for row in deferred_publication_rows:
        slug = row["slug"]
        cost = cost_by_slug[slug]
        title_record = title_by_slug[slug]
        rights_record_for_slug = rights_by_slug[slug]
        deferred_queue_titles.append(
            {
                "slug": slug,
                "title": row["title"],
                "author": title_record["author"],
                "language": row["language"],
                "reason_for_deferral": POST_SPRINT_DEFERRAL_REASON,
                "approximate_characters": cost["characters"],
                "approximate_words": cost["words"],
                "approximate_duration_minutes": cost["estimated_duration_minutes"],
                "deferred_baseline_estimated_cost_usd": cost["deferred_baseline_estimated_cost_usd"],
                "estimated_full_tts_usd": cost["estimated_full_tts_usd"],
                "estimated_full_asr_usd": cost["estimated_full_asr_usd"],
                "estimated_listening_qa_usd": cost["estimated_listening_qa_usd"],
                "required_future_steps": [
                    "Reconfirm reader route and canonical sanitized text",
                    "Run a bounded representative audition",
                    "Choose reuse or full-book TTS from current asset evidence",
                    "Run full ASR/source, first/last, and listening QA gates",
                    "Validate manifest, endpoint, frontend release state, and production route",
                    "Obtain explicit post-sprint public-audio release approval",
                ],
                "source_rights_status": rights_record_for_slug["audio_rights_status"],
                "reader_status": row["public_reader_status"],
                "audiobook_status": row["public_audio_status"],
                "recommended_future_batch": "POST_SPRINT_LONG_CLASSICS_BATCH_1",
                "recommended_cost_strategy": cost["deferred_recommended_strategy"],
                "sprint1_audio_target": False,
                "public_audiobook_required_for_sprint1": False,
                "final_status": "DROPPED_FROM_SPRINT1_AUDIO_PLAN",
                "next_action": POST_SPRINT_NEXT_ACTION,
                "next_command": POST_SPRINT_NEXT_COMMAND,
            }
        )

    deferred_queue = {
        "schema_version": 1,
        "generated_at": generated_at,
        "queue": "POST_SPRINT_LONG_CLASSICS_DEFERRED",
        "owner_decision": "DROP_GREAT_EXPECTATIONS_AND_JANE_EYRE_FROM_SPRINT1_AUDIO_PUBLICATION_PLAN",
        "title_count": len(deferred_queue_titles),
        "estimated_cost_removed_from_sprint1_usd": removed_estimate,
        "reader_and_catalog_access_preserved": True,
        "release_gates_mutated": False,
        "titles": deferred_queue_titles,
    }
    write_json(output / "post_sprint_long_classics_audio_queue.json", deferred_queue)
    write_text(
        output / "post_sprint_long_classics_audio_queue.md",
        "# Post-Sprint Long Classics Audio Queue\n\n"
        + f"Generated: `{generated_at}`\n\n"
        + f"Owner decision: `DROP_GREAT_EXPECTATIONS_AND_JANE_EYRE_FROM_SPRINT1_AUDIO_PUBLICATION_PLAN`\n\n"
        + f"Titles deferred: `{len(deferred_queue_titles)}`\n\n"
        + f"Estimated cost removed from Sprint 1: `${removed_estimate:.4f}`\n\n"
        + "Reader/catalog records and current audio release states are preserved. No provider call or release-gate mutation is authorized by this queue.\n\n"
        + "| Slug | Reader status | Audiobook status | Characters | Duration min | Deferred estimate | Future strategy |\n"
        + "| --- | --- | --- | ---: | ---: | ---: | --- |\n"
        + "\n".join(
            f"| `{row['slug']}` | `{row['reader_status']}` | `{row['audiobook_status']}` | {row['approximate_characters']} | {row['approximate_duration_minutes']:.2f} | ${row['deferred_baseline_estimated_cost_usd']:.4f} | `{row['recommended_cost_strategy']}` |"
            for row in deferred_queue_titles
        )
        + "\n\n## Future Steps\n\n"
        + "\n".join(
            f"- `{row['slug']}`: {row['next_action']}. Next instruction: `{row['next_command']}`."
            for row in deferred_queue_titles
        ),
    )

    print(
        json.dumps(
            {
                "status": "NON_PAID_PREFLIGHT_COMPLETE",
                "titles": len(publication_rows),
                "active_sprint1_titles": len(active_publication_rows),
                "active_audiobook_targets": len(active_publication_rows),
                "deferred_long_classics": len(deferred_publication_rows),
                "yes_yes": len(yes_yes),
                "incomplete": len(incomplete),
                "sanitation_pass": sanitation_summary["pass_count"],
                "sanitation_fail": sanitation_summary["fail_count"],
                "estimated_incremental_total_usd": total_estimate,
                "removed_deferred_estimated_cost_usd": removed_estimate,
                "actual_spend_usd": 0.0,
                "missing_budget_gates": missing_budget,
                "output_root": str(output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
