#!/usr/bin/env python3
"""Prepare internal-only Dracula full audiobook preflight artifacts.

The default mode writes deterministic source, chunk, cost, sample, sync, QA,
and release-blocker manifests without calling paid APIs. Paid sample or full
generation modes are fenced by explicit owner approval, a USD budget cap, and
an ElevenLabs credential. Audio output is always internal-only.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.elevenlabs_tts_client import (  # noqa: E402
    ElevenLabsSafetyError,
    ElevenLabsSettings,
    generate_tts_audio,
    sha256_file,
    sha256_text,
)
from scripts.tts_provider_internal_eval_review import (  # noqa: E402
    ELIGIBLE_INTERNAL_EVAL_ONLY,
    PRODUCTION_BLOCKED,
    review_provider_candidates,
    selected_provider_decision,
)


BOOK_SLUG = "dracula"
LANGUAGE = "en"
EXPECTED_CHAPTER_COUNT = 27
SOURCE_CHAPTER_DIR = ROOT / "data" / "controlled_publications" / BOOK_SLUG / "chapters"
OUTPUT_ROOT = ROOT / "internal" / "audiobook_lab" / BOOK_SLUG / LANGUAGE / "full-book"
SAMPLE_PACK_DIR = OUTPUT_ROOT / "sample_pack"
CHUNK_AUDIO_DIR = OUTPUT_ROOT / "chunks"
CHAPTER_AUDIO_DIR = OUTPUT_ROOT / "chapters"
MANIFESTS_DIR = OUTPUT_ROOT / "manifests"
CHAPTER_SYNC_DIR = OUTPUT_ROOT / "chapter_sync"
APPROVAL_FILE = ROOT / "data" / "audiobook_governance" / "dracula.full_audiobook_generation_approval.json"
PUBLIC_AUDIO_RELEASE_BLOCKED = "PUBLIC_AUDIO_RELEASE_BLOCKED"
HOLD_SYNC_QA_REQUIRED = "HOLD_SYNC_QA_REQUIRED"

DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
DEFAULT_VOICE_NAME = "Rachel"
DEFAULT_MODEL_ID = "eleven_flash_v2_5"
DEFAULT_PREMIUM_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"
FLASH_RATE_USD_PER_1000_CHARS = Decimal("0.05")
PREMIUM_RATE_USD_PER_1000_CHARS = Decimal("0.10")
DEFAULT_TARGET_CHARS = 3600
DEFAULT_MAX_CHARS = 4500
DEFAULT_CONCURRENCY = 3

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".aac"}
PUBLIC_PATHS = (ROOT / "frontend" / "public", ROOT / "frontend" / "build")


@dataclass(frozen=True)
class ChapterSource:
    number: int
    title: str
    source_path: Path
    source_json_sha256: str
    paragraphs: list[str]
    source_text: str
    normalized_text: str
    source_sha256: str
    normalized_sha256: str


@dataclass(frozen=True)
class ChunkSource:
    chunk_id: str
    chapter_number: int
    chunk_number: int
    text: str
    normalized_text: str
    paragraph_start: int
    paragraph_end: int
    source_sha256: str
    normalized_sha256: str
    character_count: int
    normalized_character_count: int
    word_count: int
    estimated_duration_seconds: float
    warnings: list[str]


class ParagraphHTMLExtractor(HTMLParser):
    """Extract paragraph blocks while preserving explicit line breaks."""

    def __init__(self) -> None:
        super().__init__()
        self.paragraphs: list[str] = []
        self.current: list[str] = []
        self.in_paragraph = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "p":
            self._finish_current()
            self.in_paragraph = True
        elif tag.lower() == "br":
            self.current.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "p":
            self._finish_current()
            self.in_paragraph = False

    def handle_data(self, data: str) -> None:
        self.current.append(data)

    def close(self) -> None:
        super().close()
        self._finish_current()

    def _finish_current(self) -> None:
        text = clean_block("".join(self.current))
        if text:
            self.paragraphs.append(text)
        self.current = []


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def clean_block(value: str) -> str:
    text = html.unescape(value).replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def normalize_text(value: str) -> str:
    text = value.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_paragraphs(content_html: str) -> list[str]:
    parser = ParagraphHTMLExtractor()
    parser.feed(content_html)
    parser.close()
    if parser.paragraphs:
        return parser.paragraphs
    fallback = clean_block(re.sub(r"<[^>]+>", "", content_html))
    return [fallback] if fallback else []


def word_count(value: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", value))


def estimate_duration_seconds(value: str) -> float:
    return round(max(3.0, word_count(value) * 0.39), 1)


def money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def estimated_cost(characters: int, rate: Decimal) -> Decimal:
    return (Decimal(characters) / Decimal(1000)) * rate


def load_chapters() -> list[ChapterSource]:
    chapter_paths = sorted(SOURCE_CHAPTER_DIR.glob("chapter-*.json"))
    if len(chapter_paths) != EXPECTED_CHAPTER_COUNT:
        raise SystemExit(f"Expected {EXPECTED_CHAPTER_COUNT} Dracula chapters, found {len(chapter_paths)}.")
    chapters: list[ChapterSource] = []
    for index, path in enumerate(chapter_paths, start=1):
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
        number = int(payload.get("order") or index)
        if number != index:
            raise SystemExit(f"Unexpected chapter order in {relative(path)}: {number}, expected {index}.")
        title = str(payload.get("title") or f"Chapter {index}")
        paragraphs = [title, *extract_paragraphs(str(payload.get("content") or ""))]
        source_text = "\n\n".join(paragraphs).strip()
        normalized = normalize_text(source_text)
        chapters.append(
            ChapterSource(
                number=index,
                title=title,
                source_path=path,
                source_json_sha256=sha256_text(raw),
                paragraphs=paragraphs,
                source_text=source_text,
                normalized_text=normalized,
                source_sha256=sha256_text(source_text),
                normalized_sha256=sha256_text(normalized),
            )
        )
    return chapters


def split_sentences(paragraph: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[\"'(_]*[A-Z0-9])", paragraph)
    return [part.strip() for part in parts if part.strip()]


def make_chunk(chapter: ChapterSource, index: int, paragraph_indexes: list[int], parts: list[str]) -> ChunkSource:
    text = "\n\n".join(part.strip() for part in parts if part.strip()).strip()
    normalized = normalize_text(text)
    warnings: list[str] = []
    if any(len(sentence) > DEFAULT_MAX_CHARS for part in parts for sentence in split_sentences(part)):
        warnings.append("sentence_exceeds_target_not_split")
    return ChunkSource(
        chunk_id=f"dracula-chapter-{chapter.number:02d}-chunk-{index:03d}",
        chapter_number=chapter.number,
        chunk_number=index,
        text=text,
        normalized_text=normalized,
        paragraph_start=min(paragraph_indexes),
        paragraph_end=max(paragraph_indexes),
        source_sha256=sha256_text(text),
        normalized_sha256=sha256_text(normalized),
        character_count=len(text),
        normalized_character_count=len(normalized),
        word_count=word_count(text),
        estimated_duration_seconds=estimate_duration_seconds(text),
        warnings=warnings,
    )


def chunk_chapter(chapter: ChapterSource, target_chars: int, max_chars: int) -> list[ChunkSource]:
    chunks: list[ChunkSource] = []
    current_parts: list[str] = []
    current_paragraph_indexes: list[int] = []

    def flush() -> None:
        nonlocal current_parts, current_paragraph_indexes
        if current_parts:
            chunks.append(make_chunk(chapter, len(chunks) + 1, current_paragraph_indexes, current_parts))
            current_parts = []
            current_paragraph_indexes = []

    for paragraph_index, paragraph in enumerate(chapter.paragraphs, start=1):
        candidate = "\n\n".join([*current_parts, paragraph]).strip()
        if current_parts and len(candidate) > max_chars:
            flush()

        if len(paragraph) <= max_chars:
            current_parts.append(paragraph)
            current_paragraph_indexes.append(paragraph_index)
            if len("\n\n".join(current_parts)) >= target_chars:
                flush()
            continue

        sentence_group: list[str] = []
        for sentence in split_sentences(paragraph):
            candidate_sentence_group = " ".join([*sentence_group, sentence]).strip()
            if sentence_group and len(candidate_sentence_group) > max_chars:
                current_parts.append(" ".join(sentence_group).strip())
                current_paragraph_indexes.append(paragraph_index)
                flush()
                sentence_group = [sentence]
            else:
                sentence_group.append(sentence)
        if sentence_group:
            current_parts.append(" ".join(sentence_group).strip())
            current_paragraph_indexes.append(paragraph_index)
            flush()

    flush()
    return chunks


def existing_chapter1_hashes() -> set[str]:
    hashes: set[str] = set()
    for path in [
        ROOT / "internal" / "audiobook_lab" / BOOK_SLUG / LANGUAGE / "chapter-1" / "chunk_generation_manifest.json",
        ROOT / "internal" / "audiobook_lab" / BOOK_SLUG / LANGUAGE / "chapter-1" / "chunk_manifest.json",
        ROOT / "internal" / "audiobook_lab" / BOOK_SLUG / LANGUAGE / "chapter-1" / "full_chapter_audio_manifest.json",
    ]:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for item in payload.get("chunks", []):
            if not isinstance(item, dict):
                continue
            for key in ("text_hash", "source_sha256", "normalized_sha256"):
                value = str(item.get(key) or "")
                if value:
                    hashes.add(value)
    return hashes


def approval_status(full_flash_cost: Decimal, sample_flash_cost: Decimal, sample_premium_cost: Decimal) -> dict[str, Any]:
    budget_text = os.environ.get("EARNALISM_DRACULA_AUDIOBOOK_MAX_COST_USD", "").strip()
    budget_value: Decimal | None = None
    budget_parse_error = ""
    if budget_text:
        try:
            budget_value = Decimal(budget_text)
        except Exception:
            budget_parse_error = "EARNALISM_DRACULA_AUDIOBOOK_MAX_COST_USD must be numeric"
    provider_key_name = next(
        (
            key
            for key in ("ELEVENLABS_API_KEY", "EARNALISM_ELEVENLABS_API_KEY", "ELEVENLABS_XI_API_KEY")
            if os.environ.get(key, "").strip()
        ),
        "",
    )
    approval_file_payload: dict[str, Any] = {}
    approval_file_status = "missing_optional"
    if APPROVAL_FILE.exists():
        try:
            approval_file_payload = json.loads(APPROVAL_FILE.read_text(encoding="utf-8"))
            approval_file_status = "present"
        except json.JSONDecodeError:
            approval_file_status = "present_invalid_json"

    blockers: list[str] = []
    if os.environ.get("EARNALISM_APPROVE_PAID_DRACULA_AUDIOBOOK_GENERATION") != "1":
        blockers.append("EARNALISM_APPROVE_PAID_DRACULA_AUDIOBOOK_GENERATION=1 is required")
    if budget_value is None:
        blockers.append("EARNALISM_DRACULA_AUDIOBOOK_MAX_COST_USD=<number> is required")
    elif budget_value < full_flash_cost:
        blockers.append(
            f"budget cap {money(budget_value)} USD is below Flash full-book estimate {money(full_flash_cost)} USD"
        )
    if budget_parse_error:
        blockers.append(budget_parse_error)
    if not provider_key_name:
        blockers.append("ELEVENLABS_API_KEY or repo-supported ElevenLabs credential is required")
    if approval_file_status == "present_invalid_json":
        blockers.append(f"{relative(APPROVAL_FILE)} is invalid JSON")
    if approval_file_payload and approval_file_payload.get("approved") is False:
        blockers.append(f"{relative(APPROVAL_FILE)} explicitly denies paid generation")

    return {
        "approval_env_present": os.environ.get("EARNALISM_APPROVE_PAID_DRACULA_AUDIOBOOK_GENERATION") == "1",
        "budget_cap_present": bool(budget_text),
        "budget_cap_usd": str(budget_value) if budget_value is not None else "",
        "provider_key_present": bool(provider_key_name),
        "provider_key_name": provider_key_name,
        "optional_approval_file": relative(APPROVAL_FILE),
        "optional_approval_file_status": approval_file_status,
        "sample_flash_estimate_usd": money(sample_flash_cost),
        "sample_premium_estimate_usd": money(sample_premium_cost),
        "full_flash_estimate_usd": money(full_flash_cost),
        "paid_generation_allowed": not blockers,
        "blockers": blockers,
    }


def public_audio_files() -> list[str]:
    found: list[str] = []
    for root in PUBLIC_PATHS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
                found.append(relative(path))
    return sorted(found)


def chunk_payload(chunk: ChunkSource, chapter1_hashes: set[str], model_id: str, voice_id: str, output_format: str) -> dict[str, Any]:
    cache_status = "NOT_APPLICABLE_NON_CHAPTER_1"
    if chunk.chapter_number == 1:
        cache_status = (
            "REUSE_ELIGIBLE_SOURCE_CHECKSUM_MATCH"
            if chunk.source_sha256 in chapter1_hashes or chunk.normalized_sha256 in chapter1_hashes
            else "NOT_REUSED_SOURCE_CHECKSUM_MISMATCH"
        )
    audio_path = CHUNK_AUDIO_DIR / f"{chunk.chunk_id}.mp3"
    return {
        "audioChecksum": "",
        "audioPath": relative(audio_path),
        "cacheStatus": cache_status,
        "characterCount": chunk.character_count,
        "chapterNumber": chunk.chapter_number,
        "chunkId": chunk.chunk_id,
        "chunkNumber": chunk.chunk_number,
        "estimatedDurationSeconds": chunk.estimated_duration_seconds,
        "generationStatus": "BLOCKED_PENDING_OWNER_APPROVAL",
        "modelId": model_id,
        "normalizedCharacterCount": chunk.normalized_character_count,
        "normalizedSha256": chunk.normalized_sha256,
        "outputFormat": output_format,
        "paragraphEnd": chunk.paragraph_end,
        "paragraphStart": chunk.paragraph_start,
        "provider": "ElevenLabs",
        "public": False,
        "publicAudioAllowed": False,
        "retryCount": 0,
        "sourceSha256": chunk.source_sha256,
        "voiceId": voice_id,
        "warnings": chunk.warnings,
        "wordCount": chunk.word_count,
    }


def build_sample_pack(chapters: list[ChapterSource]) -> tuple[list[dict[str, Any]], int]:
    samples: list[dict[str, Any]] = []

    def passage_from_paragraphs(sample_id: str, label: str, chapter: ChapterSource, paragraphs: list[str]) -> None:
        text_parts: list[str] = []
        for paragraph in paragraphs:
            candidate = "\n\n".join([*text_parts, paragraph]).strip()
            if text_parts and len(candidate) > 2200:
                break
            text_parts.append(paragraph)
        text = "\n\n".join(text_parts).strip()
        samples.append(
            {
                "sampleId": sample_id,
                "label": label,
                "chapterNumber": chapter.number,
                "chapterTitle": chapter.title,
                "sourcePath": relative(chapter.source_path),
                "text": text,
                "characterCount": len(text),
                "normalizedCharacterCount": len(normalize_text(text)),
                "sourceSha256": sha256_text(text),
                "normalizedSha256": sha256_text(normalize_text(text)),
                "generationStatus": "BLOCKED_PENDING_OWNER_APPROVAL",
            }
        )

    passage_from_paragraphs(
        "chapter-01-opening-atmosphere",
        "Chapter 1 opening atmospheric passage",
        chapters[0],
        chapters[0].paragraphs[:4],
    )

    dialogue_chapter = chapters[0]
    dialogue_window: list[str] = []
    best_score = -1
    for chapter in chapters:
        paragraphs = chapter.paragraphs
        for index in range(max(1, len(paragraphs) - 2)):
            window = paragraphs[index : index + 3]
            text = "\n\n".join(window)
            score = text.count('"') + len(re.findall(r"\b(said|asked|cried|answered|replied)\b", text, flags=re.I)) * 2
            if score > best_score and len(text) >= 500:
                best_score = score
                dialogue_chapter = chapter
                dialogue_window = window
    passage_from_paragraphs(
        "dialogue-heavy-passage",
        "Dialogue-heavy passage",
        dialogue_chapter,
        dialogue_window or dialogue_chapter.paragraphs[:3],
    )

    letter_chapter = next((chapter for chapter in chapters if "LETTER" in chapter.title.upper()), chapters[4])
    passage_from_paragraphs(
        "letter-journal-style-passage",
        "Letter/journal-style passage",
        letter_chapter,
        letter_chapter.paragraphs[:4],
    )
    return samples, sum(item["characterCount"] for item in samples)


def write_sample_pack(
    *,
    samples: list[dict[str, Any]],
    model_id: str,
    premium_model_id: str,
    voice_id: str,
    voice_name: str,
    output_format: str,
    approval: dict[str, Any],
) -> None:
    for subdir in (SAMPLE_PACK_DIR / "flash", SAMPLE_PACK_DIR / "premium"):
        subdir.mkdir(parents=True, exist_ok=True)
        (subdir / ".gitkeep").touch()
    write_json(
        SAMPLE_PACK_DIR / "sample_manifest.json",
        {
            "bookSlug": BOOK_SLUG,
            "language": LANGUAGE,
            "publicAudioRelease": PUBLIC_AUDIO_RELEASE_BLOCKED,
            "publicAudioAllowed": False,
            "listenNowCtaAllowed": False,
            "audioObjectMetadataAllowed": False,
            "provider": "ElevenLabs",
            "voiceId": voice_id,
            "voiceName": voice_name,
            "flashModelId": model_id,
            "premiumModelId": premium_model_id,
            "outputFormat": output_format,
            "samples": samples,
            "approval": approval,
        },
    )
    report = [
        "# Dracula Sample Pack Comparison Report",
        "",
        "- Status: `PRE_GENERATION_BLOCKED_PENDING_OWNER_APPROVAL`",
        f"- Flash path: `{model_id}`",
        f"- Premium comparison path: `{premium_model_id}`",
        f"- Voice: `{voice_name} / {voice_id}`",
        f"- Output format: `{output_format}`",
        "- Public audio: `PUBLIC_AUDIO_RELEASE_BLOCKED`",
        "- Audio files generated: `false`",
        "",
        "| Dimension | Flash preflight | Premium preflight |",
        "| --- | --- | --- |",
        "| Voice naturalness | Pending sample listening QA | Pending sample listening QA |",
        "| Gothic mood | Pending sample listening QA | Pending sample listening QA |",
        "| Pacing | Pending sample listening QA | Pending sample listening QA |",
        "| Pronunciation | Pending sample listening QA | Pending sample listening QA |",
        "| Dialogue handling | Pending sample listening QA | Pending sample listening QA |",
        "| Fatigue risk | Pending owner review | Pending owner review |",
        f"| Cost | `${approval['sample_flash_estimate_usd']}` estimated for selected samples | `${approval['sample_premium_estimate_usd']}` estimated for selected samples |",
        "| Generation speed | Preferred fastest first-pass path | Reserved for comparison/corrections |",
        "",
        "## Recommendation",
        "",
        "Use Flash for the first complete internal pass unless the owner-approved premium samples are dramatically better.",
        "Reserve premium generation for failed chunks, weak chapters, or an explicitly approved final upgrade.",
    ]
    write_text(SAMPLE_PACK_DIR / "SAMPLE_COMPARISON_REPORT.md", "\n".join(report))


def write_plan(
    *,
    chapters: list[ChapterSource],
    chunks: list[ChunkSource],
    character_report: dict[str, Any],
    cost_report: dict[str, Any],
    approval: dict[str, Any],
    model_id: str,
    premium_model_id: str,
    voice_id: str,
    voice_name: str,
    output_format: str,
    concurrency: int,
    target_chars: int,
    max_chars: int,
) -> None:
    lines = [
        "# Fast Dracula Audiobook Production Plan",
        "",
        "## Status",
        "",
        "- Scope: internal audiobook production preflight for editorial QA.",
        "- Public audio remains blocked.",
        "- Public audio release: `PUBLIC_AUDIO_RELEASE_BLOCKED`.",
        "- Audiobook public release remains blocked.",
        "- No Listen Now CTA, AudioObject metadata, public audiobook URLs, payment changes, pricing changes, deployment, or new book publication.",
        "",
        "## Source",
        "",
        f"- Exact source text path: `{relative(SOURCE_CHAPTER_DIR)}/chapter-001.json` through `chapter-027.json`.",
        f"- Confirmed chapter count: `{len(chapters)}`.",
        f"- Total character count: `{character_report['totalCharacters']}`.",
        f"- Total normalized character count: `{character_report['totalNormalizedCharacters']}`.",
        f"- Source checksum: `{character_report['combinedSourceSha256']}`.",
        f"- Normalized checksum: `{character_report['combinedNormalizedSha256']}`.",
        "",
        "## Cost",
        "",
        f"- Flash cost estimate: `{character_report['totalCharacters']} / 1000 * 0.05 = ${cost_report['flash']['estimatedCostUsd']}`.",
        f"- Premium cost estimate: `{character_report['totalCharacters']} / 1000 * 0.10 = ${cost_report['premium']['estimatedCostUsd']}`.",
        f"- Budget cap present: `{str(approval['budget_cap_present']).lower()}`.",
        f"- Paid generation allowed now: `{str(approval['paid_generation_allowed']).lower()}`.",
        "",
        "## Provider Defaults",
        "",
        f"- Default voice alias: `elevenlabs:{voice_name.lower()}`.",
        f"- Default voice ID: `{voice_id}`.",
        f"- First-pass model ID: `{model_id}`.",
        f"- Premium model ID for comparison/corrections only: `{premium_model_id}`.",
        f"- Output format: `{output_format}`.",
        "",
        "## Chunking Strategy",
        "",
        f"- Chunk by chapter, paragraph, and sentence boundaries with target `{target_chars}` characters and max `{max_chars}` characters.",
        "- Do not split sentences unless a single sentence exceeds the max target; oversize sentences stay intact and are flagged.",
        "- Preserve epistolary headings, letters, diary entries, telegrams, and section breaks as source text.",
        "- Do not rewrite Dracula text. Normalization is limited to line-ending and whitespace consistency for checksums.",
        f"- Total planned chunks: `{len(chunks)}`.",
        "",
        "## Concurrency, Retry, And Cache",
        "",
        f"- Concurrency: `{concurrency}` workers max for paid generation.",
        "- Retry transient provider failures with exponential backoff.",
        "- Never regenerate a chunk whose source checksum, model, voice, output format, and audio checksum already match.",
        "- Reuse existing Chapter 1 cache only when source checksums match; otherwise mark it as checksum mismatch.",
        "",
        "## QA Checklist",
        "",
        "- Confirm exactly 27 chapters.",
        "- Confirm all chunks are generated or explicitly failed.",
        "- Confirm no missing chunks, zero-byte files, or missing checksums.",
        "- Confirm durations are plausible.",
        "- Confirm no public URLs, no frontend/public or frontend/build audio, no Listen Now CTA, and no AudioObject metadata.",
        "- Confirm public audio remains blocked and payment behavior is unchanged.",
        "",
        "## Human Review Checklist",
        "",
        "- First 60 seconds of each chapter.",
        "- One middle sample of each chapter.",
        "- Final 60 seconds of each chapter.",
        "- Mark bad chunks/chapters in `REGENERATION_QUEUE.json`.",
        "",
        "## Public-Release Blockers",
        "",
        "- Public audio remains blocked.",
        "- Human listening QA is required.",
        "- Chunk-level sync is not word-level sync and must not be marketed as word highlighting.",
        "- Accessibility, legal/commercial, and owner release approval are still required.",
    ]
    write_text(OUTPUT_ROOT / "FAST_DRACULA_AUDIOBOOK_PRODUCTION_PLAN.md", "\n".join(lines))


def build_preflight_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    for path in (OUTPUT_ROOT, SAMPLE_PACK_DIR, CHUNK_AUDIO_DIR, CHAPTER_AUDIO_DIR, MANIFESTS_DIR, CHAPTER_SYNC_DIR):
        path.mkdir(parents=True, exist_ok=True)
    (CHUNK_AUDIO_DIR / ".gitkeep").touch()
    (CHAPTER_AUDIO_DIR / ".gitkeep").touch()

    chapters = load_chapters()
    all_chunks_by_chapter = {
        chapter.number: chunk_chapter(chapter, target_chars=args.target_chars, max_chars=args.max_chars)
        for chapter in chapters
    }
    chunks = [chunk for chapter_chunks in all_chunks_by_chapter.values() for chunk in chapter_chunks]
    total_characters = sum(len(chapter.source_text) for chapter in chapters)
    total_normalized_characters = sum(len(chapter.normalized_text) for chapter in chapters)
    combined_source_text = "\n\n".join(chapter.source_text for chapter in chapters)
    combined_normalized_text = "\n\n".join(chapter.normalized_text for chapter in chapters)
    sample_items, sample_characters = build_sample_pack(chapters)
    flash_cost = estimated_cost(total_characters, FLASH_RATE_USD_PER_1000_CHARS)
    premium_cost = estimated_cost(total_characters, PREMIUM_RATE_USD_PER_1000_CHARS)
    sample_flash_cost = estimated_cost(sample_characters, FLASH_RATE_USD_PER_1000_CHARS)
    sample_premium_cost = estimated_cost(sample_characters, PREMIUM_RATE_USD_PER_1000_CHARS)
    approval = approval_status(flash_cost, sample_flash_cost, sample_premium_cost)
    chapter1_hashes = existing_chapter1_hashes()

    chapter_manifest = {
        "bookSlug": BOOK_SLUG,
        "chapterCount": len(chapters),
        "chapters": [
            {
                "chapterId": f"dracula-chapter-{chapter.number:02d}",
                "chapterNumber": chapter.number,
                "chunkCount": len(all_chunks_by_chapter[chapter.number]),
                "estimatedDurationSeconds": round(sum(chunk.estimated_duration_seconds for chunk in all_chunks_by_chapter[chapter.number]), 1),
                "generationStatus": "BLOCKED_PENDING_OWNER_APPROVAL",
                "normalizedCharacterCount": len(chapter.normalized_text),
                "normalizedSha256": chapter.normalized_sha256,
                "sourceCharacterCount": len(chapter.source_text),
                "sourceJsonSha256": chapter.source_json_sha256,
                "sourcePath": relative(chapter.source_path),
                "sourceSha256": chapter.source_sha256,
                "title": chapter.title,
                "wordCount": word_count(chapter.source_text),
            }
            for chapter in chapters
        ],
        "generatedBy": "scripts/prepare_dracula_full_audiobook_internal.py",
        "publicAudioAllowed": False,
        "publicAudioRelease": PUBLIC_AUDIO_RELEASE_BLOCKED,
    }
    write_json(OUTPUT_ROOT / "chapter_manifest.json", chapter_manifest)

    chunk_manifest = {
        "bookSlug": BOOK_SLUG,
        "chunkCount": len(chunks),
        "chunks": [
            chunk_payload(chunk, chapter1_hashes, args.model_id, args.voice_id, args.output_format)
            for chunk in chunks
        ],
        "chunkIdPattern": "dracula-chapter-NN-chunk-NNN",
        "generatedBy": "scripts/prepare_dracula_full_audiobook_internal.py",
        "language": LANGUAGE,
        "listenNowCtaAllowed": False,
        "audioObjectMetadataAllowed": False,
        "modelId": args.model_id,
        "outputFormat": args.output_format,
        "publicAudioAllowed": False,
        "publicAudioRelease": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "voiceId": args.voice_id,
        "voiceName": args.voice_name,
    }
    write_json(OUTPUT_ROOT / "chunk_manifest.json", chunk_manifest)

    character_report = {
        "bookSlug": BOOK_SLUG,
        "chapterCount": len(chapters),
        "chunkCount": len(chunks),
        "combinedNormalizedSha256": sha256_text(combined_normalized_text),
        "combinedSourceSha256": sha256_text(combined_source_text),
        "sourcePaths": [relative(chapter.source_path) for chapter in chapters],
        "totalCharacters": total_characters,
        "totalNormalizedCharacters": total_normalized_characters,
        "totalWords": word_count(combined_source_text),
        "perChapter": [
            {
                "chapterNumber": chapter.number,
                "sourceCharacters": len(chapter.source_text),
                "normalizedCharacters": len(chapter.normalized_text),
                "sourceSha256": chapter.source_sha256,
                "normalizedSha256": chapter.normalized_sha256,
            }
            for chapter in chapters
        ],
    }
    write_json(OUTPUT_ROOT / "character_count_report.json", character_report)

    cost_report = {
        "bookSlug": BOOK_SLUG,
        "formula": {
            "flash": "total_characters / 1000 * 0.05",
            "premium": "total_characters / 1000 * 0.10",
        },
        "flash": {
            "rateUsdPer1000Characters": str(FLASH_RATE_USD_PER_1000_CHARS),
            "estimatedCostUsd": money(flash_cost),
            "exactCostUsd": str(flash_cost),
            "modelId": args.model_id,
        },
        "premium": {
            "rateUsdPer1000Characters": str(PREMIUM_RATE_USD_PER_1000_CHARS),
            "estimatedCostUsd": money(premium_cost),
            "exactCostUsd": str(premium_cost),
            "modelId": args.premium_model_id,
        },
        "samplePack": {
            "characters": sample_characters,
            "flashEstimateUsd": money(sample_flash_cost),
            "premiumEstimateUsd": money(sample_premium_cost),
        },
        "totalCharacters": total_characters,
    }
    write_json(OUTPUT_ROOT / "cost_preflight_report.json", cost_report)

    generation_preflight = {
        "bookSlug": BOOK_SLUG,
        "status": "READY_FOR_OWNER_APPROVAL" if approval["paid_generation_allowed"] else "BLOCKED_PENDING_OWNER_APPROVAL",
        "approval": approval,
        "chapterCount": len(chapters),
        "chunkCount": len(chunks),
        "modelId": args.model_id,
        "outputFormat": args.output_format,
        "paidApiCalled": False,
        "provider": "ElevenLabs",
        "publicAudioAllowed": False,
        "publicAudioRelease": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "resumeCommands": [
            "export EARNALISM_APPROVE_PAID_DRACULA_AUDIOBOOK_GENERATION=1",
            f"export EARNALISM_DRACULA_AUDIOBOOK_MAX_COST_USD={money(flash_cost)}",
            "export ELEVENLABS_API_KEY=<owner-provided-key>",
            "python3 scripts/prepare_dracula_full_audiobook_internal.py --mode sample-pack",
            "python3 scripts/prepare_dracula_full_audiobook_internal.py --mode generate",
            "python3 scripts/validate_dracula_full_audiobook_internal.py --mode generated",
        ],
        "voiceId": args.voice_id,
        "voiceName": args.voice_name,
    }
    write_json(OUTPUT_ROOT / "generation_preflight_report.json", generation_preflight)

    write_sample_pack(
        samples=sample_items,
        model_id=args.model_id,
        premium_model_id=args.premium_model_id,
        voice_id=args.voice_id,
        voice_name=args.voice_name,
        output_format=args.output_format,
        approval=approval,
    )

    sync_manifest = {
        "bookSlug": BOOK_SLUG,
        "chapterCount": len(chapters),
        "chunkCount": len(chunks),
        "publicAudioAllowed": False,
        "publicAudioRelease": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "syncPrecision": "chunk",
        "syncStatus": HOLD_SYNC_QA_REQUIRED,
        "wordLevelTimestampsClaimed": False,
        "chapters": [],
    }
    for chapter in chapters:
        chapter_chunks = all_chunks_by_chapter[chapter.number]
        chapter_sync = {
            "bookSlug": BOOK_SLUG,
            "chapterNumber": chapter.number,
            "chapterTitle": chapter.title,
            "public": False,
            "publicAudioAllowed": False,
            "syncPrecision": "chunk",
            "syncStatus": HOLD_SYNC_QA_REQUIRED,
            "chunks": [
                {
                    "chunkId": chunk.chunk_id,
                    "audioPath": relative(CHUNK_AUDIO_DIR / f"{chunk.chunk_id}.mp3"),
                    "startMs": None,
                    "endMs": None,
                    "timingStatus": "PENDING_AUDIO_GENERATION",
                    "sourceSha256": chunk.source_sha256,
                    "normalizedSha256": chunk.normalized_sha256,
                }
                for chunk in chapter_chunks
            ],
        }
        chapter_sync_path = CHAPTER_SYNC_DIR / f"chapter-{chapter.number:02d}.sync.json"
        write_json(chapter_sync_path, chapter_sync)
        sync_manifest["chapters"].append(
            {
                "chapterNumber": chapter.number,
                "chapterSyncPath": relative(chapter_sync_path),
                "chunkCount": len(chapter_chunks),
                "syncPrecision": "chunk",
            }
        )
    write_json(OUTPUT_ROOT / "sync_manifest.json", sync_manifest)

    write_plan(
        chapters=chapters,
        chunks=chunks,
        character_report=character_report,
        cost_report=cost_report,
        approval=approval,
        model_id=args.model_id,
        premium_model_id=args.premium_model_id,
        voice_id=args.voice_id,
        voice_name=args.voice_name,
        output_format=args.output_format,
        concurrency=args.concurrency,
        target_chars=args.target_chars,
        max_chars=args.max_chars,
    )
    write_qa_documents(chapters=chapters, chunks=chunks, approval=approval)
    write_json(
        MANIFESTS_DIR / "manifest_index.json",
        {
            "bookSlug": BOOK_SLUG,
            "internalOnly": True,
            "publicAudioAllowed": False,
            "publicAudioRelease": PUBLIC_AUDIO_RELEASE_BLOCKED,
            "manifests": [
                relative(OUTPUT_ROOT / "chapter_manifest.json"),
                relative(OUTPUT_ROOT / "chunk_manifest.json"),
                relative(OUTPUT_ROOT / "character_count_report.json"),
                relative(OUTPUT_ROOT / "cost_preflight_report.json"),
                relative(OUTPUT_ROOT / "generation_preflight_report.json"),
                relative(OUTPUT_ROOT / "sync_manifest.json"),
            ],
        },
    )
    return {
        "approval": approval,
        "chapterCount": len(chapters),
        "chunkCount": len(chunks),
        "flashCostUsd": money(flash_cost),
        "outputRoot": relative(OUTPUT_ROOT),
        "paidApiCalled": False,
        "status": generation_preflight["status"],
        "totalCharacters": total_characters,
    }


def write_qa_documents(*, chapters: list[ChapterSource], chunks: list[ChunkSource], approval: dict[str, Any]) -> None:
    public_audio = public_audio_files()
    qa_lines = [
        "# Dracula Full Audiobook QA Report",
        "",
        "- Status: `PREFLIGHT_READY_NO_AUDIO_GENERATED`",
        f"- Chapters present: `{len(chapters)}`",
        f"- Chunks planned: `{len(chunks)}`",
        "- All chunks generated or explicitly failed: `not_applicable_preflight`",
        "- Missing chunks: `0 planned manifest gaps`",
        "- Zero-byte audio files: `not_applicable_preflight`",
        "- Checksums present: `source and normalized checksums present for all chunks`",
        "- Durations plausible: `estimated durations present; actual audio durations pending generation`",
        f"- Public audio files in frontend public/build: `{len(public_audio)}`",
        "- Public URLs in manifests: `false`",
        "- Listen Now CTA allowed: `false`",
        "- AudioObject metadata allowed: `false`",
        "- Public audio remains blocked.",
        "- Payment behavior unchanged by this preflight.",
    ]
    write_text(OUTPUT_ROOT / "AUDIOBOOK_QA_REPORT.md", "\n".join(qa_lines))

    review_lines = [
        "# Dracula Full Audiobook Human Review Form",
        "",
        "- Public audio remains blocked.",
        "- Review status: `NOT_STARTED`",
        "",
        "| Chapter | First 60 seconds | Middle sample | Final 60 seconds | Bad chunks / notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for chapter in chapters:
        review_lines.append(f"| {chapter.number:02d} | Pending | Pending | Pending |  |")
    write_text(OUTPUT_ROOT / "HUMAN_REVIEW_FORM.md", "\n".join(review_lines))

    write_json(
        OUTPUT_ROOT / "REGENERATION_QUEUE.json",
        {
            "bookSlug": BOOK_SLUG,
            "status": "EMPTY_PREFLIGHT_NO_AUDIO_GENERATED",
            "publicAudioAllowed": False,
            "publicAudioRelease": PUBLIC_AUDIO_RELEASE_BLOCKED,
            "items": [],
        },
    )

    blocker_lines = [
        "# Dracula Full Audiobook Release Blockers",
        "",
        "- Public audio remains blocked.",
        "- Audiobook public release remains blocked.",
        "- No Listen Now CTA may be added.",
        "- No AudioObject metadata may be added.",
        "- No public audiobook URLs may be created.",
        "- Human listening QA has not approved all chapters.",
        "- Chunk-level sync is not word-level sync.",
        "- Owner paid-generation approval, budget cap, and provider key are required before paid APIs.",
    ]
    for blocker in approval.get("blockers", []):
        blocker_lines.append(f"- Paid generation blocker: {blocker}")
    write_text(OUTPUT_ROOT / "RELEASE_BLOCKERS.md", "\n".join(blocker_lines))


def provider_key() -> str:
    for key in ("ELEVENLABS_API_KEY", "EARNALISM_ELEVENLABS_API_KEY", "ELEVENLABS_XI_API_KEY"):
        value = os.environ.get(key, "").strip()
        if value:
            os.environ.setdefault("ELEVENLABS_API_KEY", value)
            return value
    return ""


def require_paid_gate(approval: dict[str, Any]) -> None:
    if approval.get("blockers"):
        raise SystemExit("Paid generation blocked: " + "; ".join(approval["blockers"]))
    selected = selected_provider_decision("elevenlabs", review_provider_candidates())
    if selected.internal_generation_status != ELIGIBLE_INTERNAL_EVAL_ONLY:
        raise SystemExit("Paid generation blocked: ElevenLabs provider is not ELIGIBLE_INTERNAL_EVAL_ONLY")
    if selected.public_production_status != PRODUCTION_BLOCKED:
        raise SystemExit("Paid generation blocked: ElevenLabs public production status is not PRODUCTION_BLOCKED")
    if not provider_key():
        raise SystemExit("Paid generation blocked: ElevenLabs credential is missing")


def generate_with_retry(
    *,
    chunk_id: str,
    text: str,
    settings: ElevenLabsSettings,
    output_path: Path,
    max_retries: int,
) -> dict[str, Any]:
    retry_count = 0
    while True:
        try:
            record = generate_tts_audio(
                chunk_id=chunk_id,
                text=text,
                settings=settings,
                output_path=output_path,
                execute=True,
            )
            record["retry_count"] = retry_count
            return record
        except ElevenLabsSafetyError as exc:
            if retry_count >= max_retries:
                return {
                    "chunk_id": chunk_id,
                    "generation_status": "FAILED_INTERNAL_GENERATION",
                    "provider_api_called": True,
                    "retry_count": retry_count,
                    "failure": str(exc),
                    "output_path": relative(output_path),
                    "audio_hash": "",
                }
            retry_count += 1
            time.sleep(min(12, 2 ** retry_count))


def settings_for(args: argparse.Namespace, model_id: str) -> ElevenLabsSettings:
    return ElevenLabsSettings(
        provider="elevenlabs",
        voice_id=args.voice_id,
        voice_name=args.voice_name,
        model_id=model_id,
        output_format=args.output_format,
        speed=1.0,
        stability=0.5,
        similarity_boost=0.75,
        style_exaggeration=0.0,
        speaker_boost=True,
    )


def run_sample_generation(args: argparse.Namespace, preflight: dict[str, Any]) -> None:
    require_paid_gate(preflight["approval"])
    manifest = json.loads((SAMPLE_PACK_DIR / "sample_manifest.json").read_text(encoding="utf-8"))
    jobs: list[tuple[str, dict[str, Any], ElevenLabsSettings, Path]] = []
    for sample in manifest["samples"]:
        jobs.append(("flash", sample, settings_for(args, args.model_id), SAMPLE_PACK_DIR / "flash" / f"{sample['sampleId']}.mp3"))
        jobs.append(("premium", sample, settings_for(args, args.premium_model_id), SAMPLE_PACK_DIR / "premium" / f"{sample['sampleId']}.mp3"))
    records = []
    with ThreadPoolExecutor(max_workers=max(1, min(args.concurrency, 3))) as executor:
        future_map = {
            executor.submit(
                generate_with_retry,
                chunk_id=f"{lane}-{sample['sampleId']}",
                text=sample["text"],
                settings=settings,
                output_path=path,
                max_retries=args.max_retries,
            ): (lane, sample, path)
            for lane, sample, settings, path in jobs
        }
        for future in as_completed(future_map):
            lane, sample, path = future_map[future]
            record = future.result()
            record["lane"] = lane
            record["sampleId"] = sample["sampleId"]
            record["audioPath"] = relative(path)
            records.append(record)
    manifest["generationRecords"] = sorted(records, key=lambda item: (item["sampleId"], item["lane"]))
    manifest["paidApiCalled"] = True
    write_json(SAMPLE_PACK_DIR / "sample_manifest.json", manifest)


def probe_duration_seconds(path: Path) -> float | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    completed = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        return round(float(completed.stdout.strip()), 3)
    except ValueError:
        return None


def run_full_generation(args: argparse.Namespace, preflight: dict[str, Any]) -> None:
    require_paid_gate(preflight["approval"])
    chapters = load_chapters()
    chunks_by_chapter = {
        chapter.number: chunk_chapter(chapter, target_chars=args.target_chars, max_chars=args.max_chars)
        for chapter in chapters
    }
    settings = settings_for(args, args.model_id)
    records: list[dict[str, Any]] = []
    jobs: list[tuple[ChunkSource, Path]] = []
    existing_checksums = load_existing_audio_checksums()
    for chapter_chunks in chunks_by_chapter.values():
        for chunk in chapter_chunks:
            output_path = CHUNK_AUDIO_DIR / f"{chunk.chunk_id}.mp3"
            existing = existing_checksums.get(chunk.chunk_id, {})
            if (
                output_path.exists()
                and existing.get("sourceSha256") == chunk.source_sha256
                and existing.get("voiceId") == args.voice_id
                and existing.get("modelId") == args.model_id
                and existing.get("outputFormat") == args.output_format
                and existing.get("audioSha256")
                and sha256_file(output_path) == existing.get("audioSha256")
                and not args.force
            ):
                records.append(
                    {
                        "chunk_id": chunk.chunk_id,
                        "generation_status": "SKIPPED_CACHED_INTERNAL_AUDIO",
                        "provider_api_called": False,
                        "output_path": relative(output_path),
                        "audio_hash": existing["audioSha256"],
                        "sourceSha256": chunk.source_sha256,
                        "retry_count": 0,
                    }
                )
                continue
            jobs.append((chunk, output_path))

    with ThreadPoolExecutor(max_workers=max(1, min(args.concurrency, 3))) as executor:
        future_map = {
            executor.submit(
                generate_with_retry,
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                settings=settings,
                output_path=output_path,
                max_retries=args.max_retries,
            ): (chunk, output_path)
            for chunk, output_path in jobs
        }
        for future in as_completed(future_map):
            chunk, output_path = future_map[future]
            record = future.result()
            record["sourceSha256"] = chunk.source_sha256
            record["normalizedSha256"] = chunk.normalized_sha256
            record["characterCount"] = chunk.character_count
            record["estimatedDurationSeconds"] = chunk.estimated_duration_seconds
            duration = probe_duration_seconds(output_path) if output_path.exists() else None
            record["durationSeconds"] = duration if duration is not None else chunk.estimated_duration_seconds
            record["durationSource"] = "ffprobe" if duration is not None else "estimated"
            records.append(record)

    records_by_id = {record["chunk_id"]: record for record in records}
    write_generated_manifests(args, chapters, chunks_by_chapter, records_by_id)


def load_existing_audio_checksums() -> dict[str, dict[str, Any]]:
    path = OUTPUT_ROOT / "audio_checksums.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {
        str(item.get("chunkId")): item
        for item in payload.get("chunks", [])
        if isinstance(item, dict) and item.get("chunkId")
    }


def write_generated_manifests(
    args: argparse.Namespace,
    chapters: list[ChapterSource],
    chunks_by_chapter: dict[int, list[ChunkSource]],
    records_by_id: dict[str, dict[str, Any]],
) -> None:
    checksum_chunks = []
    chapter_items = []
    for chapter in chapters:
        chapter_chunks = chunks_by_chapter[chapter.number]
        chapter_records = [records_by_id.get(chunk.chunk_id, {}) for chunk in chapter_chunks]
        all_audio_present = all((CHUNK_AUDIO_DIR / f"{chunk.chunk_id}.mp3").exists() for chunk in chapter_chunks)
        chapter_path = CHAPTER_AUDIO_DIR / f"chapter-{chapter.number:02d}.mp3"
        assembly_status = "PENDING_CHUNK_COMPLETION"
        if all_audio_present:
            assembly_status = assemble_chapter(chapter_path, [CHUNK_AUDIO_DIR / f"{chunk.chunk_id}.mp3" for chunk in chapter_chunks])
        duration = probe_duration_seconds(chapter_path) if chapter_path.exists() else None
        chapter_items.append(
            {
                "chapterNumber": chapter.number,
                "chapterAudioPath": relative(chapter_path),
                "chapterAudioSha256": sha256_file(chapter_path) if chapter_path.exists() else "",
                "chunkCount": len(chapter_chunks),
                "durationSeconds": duration if duration is not None else round(sum(chunk.estimated_duration_seconds for chunk in chapter_chunks), 1),
                "durationSource": "ffprobe" if duration is not None else "estimated",
                "assemblyStatus": assembly_status,
                "generationStatus": "GENERATED_INTERNAL_ONLY" if all(record.get("audio_hash") for record in chapter_records) else "INCOMPLETE",
                "public": False,
            }
        )
        for chunk in chapter_chunks:
            record = records_by_id.get(chunk.chunk_id, {})
            output_path = CHUNK_AUDIO_DIR / f"{chunk.chunk_id}.mp3"
            checksum_chunks.append(
                {
                    "chunkId": chunk.chunk_id,
                    "audioPath": relative(output_path),
                    "audioSha256": sha256_file(output_path) if output_path.exists() else "",
                    "sourceSha256": chunk.source_sha256,
                    "normalizedSha256": chunk.normalized_sha256,
                    "modelId": args.model_id,
                    "voiceId": args.voice_id,
                    "outputFormat": args.output_format,
                    "generationStatus": record.get("generation_status", "MISSING"),
                    "retryCount": record.get("retry_count", 0),
                    "public": False,
                }
            )

    write_json(
        OUTPUT_ROOT / "full_chapter_audio_manifest.json",
        {
            "bookSlug": BOOK_SLUG,
            "chapterCount": len(chapter_items),
            "chapters": chapter_items,
            "internalOnly": True,
            "publicAudioAllowed": False,
            "publicAudioRelease": PUBLIC_AUDIO_RELEASE_BLOCKED,
        },
    )
    write_json(
        OUTPUT_ROOT / "audio_checksums.json",
        {
            "bookSlug": BOOK_SLUG,
            "chunks": checksum_chunks,
            "chapters": chapter_items,
            "publicAudioAllowed": False,
            "publicAudioRelease": PUBLIC_AUDIO_RELEASE_BLOCKED,
        },
    )
    write_json(
        OUTPUT_ROOT / "full_audiobook_manifest.json",
        {
            "audioObjectMetadataAllowed": False,
            "bookSlug": BOOK_SLUG,
            "chapterCount": len(chapter_items),
            "chapters": chapter_items,
            "chunkCount": len(checksum_chunks),
            "fileCount": len([item for item in checksum_chunks if item.get("audioSha256")]) + len(
                [item for item in chapter_items if item.get("chapterAudioSha256")]
            ),
            "internalOnlyStatus": "INTERNAL_REVIEW_ONLY",
            "listenNowCtaAllowed": False,
            "modelId": args.model_id,
            "noPublicReleaseFlag": True,
            "publicAudioAllowed": False,
            "publicAudioRelease": PUBLIC_AUDIO_RELEASE_BLOCKED,
            "publicUrls": [],
            "qaStatus": "HOLD_HUMAN_REVIEW",
            "totalDurationSeconds": round(sum(float(item.get("durationSeconds") or 0) for item in chapter_items), 3),
            "voiceId": args.voice_id,
            "voiceName": args.voice_name,
        },
    )


def assemble_chapter(chapter_path: Path, chunk_paths: list[Path]) -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return "BLOCKED_FFMPEG_MISSING"
    list_path = chapter_path.with_suffix(".concat.txt")
    write_text(list_path, "\n".join(f"file '{path.resolve()}'" for path in chunk_paths))
    completed = subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(chapter_path)],
        text=True,
        capture_output=True,
        check=False,
    )
    return "ASSEMBLED_INTERNAL_ONLY" if completed.returncode == 0 and chapter_path.exists() else "ASSEMBLY_FAILED"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preflight", "sample-pack", "generate"), default="preflight")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--premium-model-id", default=DEFAULT_PREMIUM_MODEL_ID)
    parser.add_argument("--voice-id", default=DEFAULT_VOICE_ID)
    parser.add_argument("--voice-name", default=DEFAULT_VOICE_NAME)
    parser.add_argument("--output-format", default=DEFAULT_OUTPUT_FORMAT)
    parser.add_argument("--target-chars", type=int, default=DEFAULT_TARGET_CHARS)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    preflight = build_preflight_artifacts(args)
    if args.mode == "sample-pack":
        run_sample_generation(args, preflight)
    elif args.mode == "generate":
        run_full_generation(args, preflight)
    print(
        json.dumps(
            {
                "status": preflight["status"],
                "mode": args.mode,
                "chapterCount": preflight["chapterCount"],
                "chunkCount": preflight["chunkCount"],
                "totalCharacters": preflight["totalCharacters"],
                "flashCostUsd": preflight["flashCostUsd"],
                "outputRoot": preflight["outputRoot"],
                "paidApiCalled": args.mode != "preflight" and preflight["approval"]["paid_generation_allowed"],
                "publicAudioRelease": PUBLIC_AUDIO_RELEASE_BLOCKED,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
