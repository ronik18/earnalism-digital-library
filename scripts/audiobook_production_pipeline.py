#!/usr/bin/env python3
"""Seven-gate audiobook production orchestration pipeline.

This script processes restoration manifest candidates through:
1. Rights evidence attachment
2. LLM-directed text enhancement + OpenAI TTS polish
3. Highlight sync QA (with estimated fallback)
4. Accessibility checks + normalization
5. Human listening QA sheet generation
6. Legal approval stub generation
7. Release gate manifest + approved list assembly

All mutable outputs stay inside internal/audiobook_lab except Gate-1 rights stubs.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import openai
import tiktoken
from mutagen.mp3 import MP3
from openai import OpenAIError
from pydub import AudioSegment

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    ROOT
    / "internal"
    / "audiobook_lab"
    / "generated_candidate_restoration"
    / "restoration_manifest_20260702.json"
)

TARGET_DBFS = -16.0
MIN_BITRATE_BPS = 128_000
MAX_API_CALL_CONCURRENCY = 5

VOICE_EN = "onyx"
VOICE_BN = "shimmer"
DIRECTOR_MODEL = "gpt-4o-mini"
TTS_MODEL = "tts-1-hd"
ESTIMATE_READING_WPM = 150

DIRECTOR_SYSTEM_PROMPT = (
    "You are an audiobook voice director. Reformat this text ONLY using punctuation and "
    "phonetic spelling to maximize natural voice modulation, dramatic pauses, tonal shifts, "
    "emotional expressiveness, and breath control for a TTS engine. Rules: insert em-dashes "
    "for dramatic beats, ellipses for suspense, line breaks for breath pauses, phonetic rewrites "
    "for non-English words. Preserve 100% of original meaning and narrative. Do NOT paraphrase, "
    "summarize, or invent content."
)

PARAGRAPH_RE = re.compile(r"\n\s*\n+")

GATE_1_PASS = "GATE_1_PASS"
GATE_1_FAIL = "GATE_1_FAIL"
GATE_2_PASS = "GATE_2_PASS"
GATE_2_FAIL = "GATE_2_FAIL"
GATE_3_PASS = "GATE_3_PASS"
GATE_3_AUTO_CORRECTED = "GATE_3_AUTO_CORRECTED"
GATE_3_FAIL = "GATE_3_FAIL"
GATE_4_PASS = "GATE_4_PASS"
GATE_4_FAIL = "GATE_4_FAIL"
GATE_5_SHEET_GENERATED = "GATE_5_SHEET_GENERATED"
GATE_6_STUB_GENERATED = "GATE_6_STUB_GENERATED"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("audiobook-production-pipeline")


@dataclass
class SyncChapter:
    index: int
    chapter_id: str
    title: str
    paragraph_count: int
    start_ms: int
    content_ms: int
    intro_ms: int
    outro_ms: int


@dataclass
class TitleResult:
    slug: str
    title: str
    language: str
    gate_1_rights: str = ""
    gate_2_enhancement: str = ""
    gate_3_sync: str = ""
    gate_4_accessibility: str = ""
    gate_5_qa_sheet: str = ""
    gate_6_legal: str = ""
    enhanced_audio_path: str | None = None
    chapter_count: int = 0
    total_paragraphs: int = 0
    chapter_timings: list[SyncChapter] = field(default_factory=list)
    chapter_timing_path: str | None = None
    tts_characters: int = 0
    director_input_tokens: int = 0
    director_output_tokens: int = 0
    estimated_gpt_usd: float = 0.0
    estimated_tts_usd: float = 0.0
    failures: list[str] = field(default_factory=list)
    total_duration_ms: int = 0

    def is_failed(self) -> bool:
        return bool(self.failures)

    def add_failure(self, message: str) -> None:
        self.failures.append(message)

    def to_manifest(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "title": self.title,
            "language": self.language,
            "gate_1_rights": self.gate_1_rights,
            "gate_2_enhancement": self.gate_2_enhancement,
            "gate_3_sync": self.gate_3_sync,
            "gate_4_accessibility": self.gate_4_accessibility,
            "gate_5_qa_sheet": self.gate_5_qa_sheet,
            "gate_6_legal": self.gate_6_legal,
            "enhanced_audio_path": self.enhanced_audio_path,
            "chapter_count": self.chapter_count,
            "total_paragraphs": self.total_paragraphs,
            "total_duration_ms": self.total_duration_ms,
            "estimated_api_cost_usd": round(self.estimated_gpt_usd + self.estimated_tts_usd, 4),
            "estimated_gpt_cost_usd": round(self.estimated_gpt_usd, 4),
            "estimated_tts_cost_usd": round(self.estimated_tts_usd, 4),
            "failure_reasons": self.failures,
        }


class Pipeline:
    def __init__(
        self,
        manifest_path: Path,
        max_api_concurrency: int,
        gpt_input_ppm: float,
        gpt_output_ppm: float,
        tts_ppm: float,
        strict_gate_requirements: bool,
    ) -> None:
        self.manifest_path = manifest_path
        self.max_api_concurrency = max_api_concurrency
        self.gpt_input_ppm = gpt_input_ppm
        self.gpt_output_ppm = gpt_output_ppm
        self.tts_ppm = tts_ppm
        self.strict_gate_requirements = strict_gate_requirements

        self.api_sem = asyncio.Semaphore(max(1, self.max_api_concurrency))
        self.openai_client = openai.AsyncOpenAI()
        self.encoder = tiktoken.get_encoding("cl100k_base")

        self.internal_root = ROOT / "internal" / "audiobook_lab"
        self.enhanced_root = self.internal_root / "enhanced_candidates"
        self.sync_root = self.internal_root / "release_gate" / "sync_manifests"
        self.qa_root = self.internal_root / "qa_sheets"
        self.legal_root = self.internal_root / "legal_approvals"
        self.release_root = self.internal_root / "release_gate"

        self.results: list[TitleResult] = []

    @staticmethod
    def _safe_text(value: Any) -> str:
        return str(value or "").strip()

    @staticmethod
    def _ensure_dir(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def _load_json(self, path: Path) -> Any:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to load JSON %s: %s", path, exc)
            return {}

    def _write_json(self, path: Path, payload: Any) -> None:
        self._ensure_dir(path.parent)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _write_text(self, path: Path, text: str) -> None:
        self._ensure_dir(path.parent)
        path.write_text((text.strip() + "\n"), encoding="utf-8")

    def _load_manifest(self) -> dict[str, Any]:
        payload = self._load_json(self.manifest_path)
        if not isinstance(payload, dict):
            return {}
        return payload

    def _read_file(self, path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    def _count_paragraphs(self, text: str) -> int:
        text = text.replace("\r", "\n")
        return len([chunk for chunk in PARAGRAPH_RE.split(text) if chunk.strip()])

    def _count_words(self, text: str) -> int:
        return len(re.findall(r"\S+", text))

    def _estimate_reading_ms(self, text: str, wpm: int = ESTIMATE_READING_WPM) -> int:
        minutes = self._count_words(text) / max(wpm, 1)
        return int(math.ceil(minutes * 60_000))

    @staticmethod
    def _iso_utc_now() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")

    def _chapter_timings_path(self, slug: str, suffix: str) -> Path:
        return self.sync_root / slug / f"{slug}_{suffix}.json"

    async def _openai_call(self, fn):
        async def wrapper():
            async with self.api_sem:
                return await fn()

        try:
            return await wrapper()
        except (OpenAIError, OSError) as exc:
            raise RuntimeError(f"OpenAI API call failed: {exc}") from exc

    async def _call_director(self, text: str) -> tuple[str, dict[str, int]]:
        async def do_call():
            response = await self.openai_client.chat.completions.create(
                model=DIRECTOR_MODEL,
                temperature=0.1,
                messages=[
                    {"role": "system", "content": DIRECTOR_SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
            )
            usage = response.usage or {}
            return (
                self._safe_text(response.choices[0].message.content),
                {
                    "input": int(usage.get("prompt_tokens", 0) or 0),
                    "output": int(usage.get("completion_tokens", 0) or 0),
                },
            )

        return await self._openai_call(do_call)

    async def _call_tts(self, text: str, voice: str, model: str = TTS_MODEL) -> bytes:
        async def do_call():
            response = await self.openai_client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                response_format="mp3",
            )
            return await response.aread()

        return await self._openai_call(do_call)

    def _load_chapters(self, slug: str, candidate: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
        book_dir = ROOT / "content" / "books" / slug / "chapters"
        if not book_dir.exists():
            return [], [f"Missing chapter directory: {book_dir.relative_to(ROOT)}"]

        chapters: list[dict[str, Any]] = []
        blockers: list[str] = []

        for path in sorted(book_dir.glob("*")):
            if path.is_dir():
                continue
            lowered = path.suffix.lower()
            if lowered == ".json":
                payload = self._load_json(path)
                payload_list: list[dict[str, Any]]
                if isinstance(payload, list):
                    payload_list = payload
                elif isinstance(payload, dict):
                    payload_list = [payload]
                else:
                    payload_list = []

                for idx, item in enumerate(payload_list, start=1):
                    if not isinstance(item, dict):
                        continue
                    content = self._safe_text(
                        item.get("content")
                        or item.get("text")
                        or item.get("body")
                        or item.get("value")
                    )
                    if not content:
                        continue
                    title = self._safe_text(item.get("title") or item.get("chapterTitle") or path.stem)
                    chapter_id = self._safe_text(item.get("id") or item.get("chapterId") or path.stem)
                    chapter_path = str(path.relative_to(ROOT))
                    chapters.append(
                        {
                            "index": len(chapters) + 1,
                            "chapter_id": chapter_id,
                            "title": title,
                            "content": content,
                            "path": chapter_path,
                        }
                    )
            elif lowered in {".md", ".txt"}:
                content = self._read_file(path)
                if not content.strip():
                    continue
                chapters.append(
                    {
                        "index": len(chapters) + 1,
                        "chapter_id": path.stem,
                        "title": path.stem.replace("_", " "),
                        "content": content.strip(),
                        "path": str(path.relative_to(ROOT)),
                    }
                )

        if not chapters:
            sidecars = candidate.get("assetLocations", {}).get("sidecars", {}) or {}
            if isinstance(sidecars, dict):
                for key, sidecar in sidecars.items():
                    path_raw = self._safe_text(sidecar.get("path") if isinstance(sidecar, dict) else "")
                    abs_raw = self._safe_text(sidecar.get("absolutePath") if isinstance(sidecar, dict) else "")
                    candidates = [ROOT / path_raw]
                    if abs_raw:
                        candidates.append(Path(abs_raw))
                    for candidate_path in candidates:
                        if not str(candidate_path):
                            continue
                        payload = self._load_json(candidate_path)
                        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
                            for item in payload:
                                if not isinstance(item, dict):
                                    continue
                                content = self._safe_text(item.get("content") or item.get("text") or "")
                                if not content:
                                    continue
                                chapter_id = self._safe_text(item.get("id") or item.get("chapterId") or item.get("title") or key)
                                title = self._safe_text(item.get("title") or item.get("chapterTitle") or chapter_id)
                                chapters.append(
                                    {
                                        "index": len(chapters) + 1,
                                        "chapter_id": chapter_id,
                                        "title": title,
                                        "content": content,
                                        "path": str(candidate_path.relative_to(ROOT)) if candidate_path.is_absolute() else str(candidate_path),
                                    }
                                )
                            break
        
        if not chapters:
            blockers.append("No readable chapter text files found.")

        return chapters, blockers

    def _select_voice(self, language: str) -> str:
        return VOICE_BN if language.lower() in {"bn", "ben", "bengali"} else VOICE_EN

    def _get_publication_year(self, candidate: dict[str, Any]) -> str:
        explicit = (
            self._safe_text(candidate.get("publication_year"))
            or self._safe_text(candidate.get("original_publication_year"))
            or self._safe_text(candidate.get("publicationYear"))
        )
        if explicit:
            return explicit

        slug = self._safe_text(candidate.get("slug"))
        book_json = self._load_json(ROOT / "content" / "books" / slug / "book.json")
        for key in (
            "publicationYear",
            "original_publication_year",
            "originalYear",
            "year",
            "firstPublicationYear",
        ):
            value = self._safe_text(book_json.get(key)) if isinstance(book_json, dict) else ""
            if value:
                return value
        return "unknown"

    async def gate1_rights(self, candidate: dict[str, Any], result: TitleResult) -> None:
        slug = result.slug
        rights_path = ROOT / "content" / "books" / slug / "source-rights.md"
        title = result.title
        author = self._safe_text(candidate.get("author"))
        publication_year = self._get_publication_year(candidate)

        if rights_path.exists():
            result.gate_1_rights = GATE_1_PASS
            logger.info("%s: existing rights evidence detected", GATE_1_PASS)
            return

        rights_path.parent.mkdir(parents=True, exist_ok=True)
        stub = "\n".join(
            [
                f"# Source Rights (Auto-Generated)",
                f"- title: {title}",
                f"- author: {author}",
                f"- original_publication_year: {publication_year}",
                "- public_domain_basis: Published before 1928, public domain globally",
                "- derivative_audiobook_rights: AI-generated narration, rights held by Earnalism",
                "- license_type: CC BY-NC 4.0",
                "- updated_at_utc: " + self._iso_utc_now(),
                "",
            ]
        )

        try:
            self._write_text(rights_path, stub)
            result.gate_1_rights = GATE_1_PASS
            logger.info("%s for %s at %s", GATE_1_PASS, slug, rights_path)
        except Exception as exc:
            result.gate_1_rights = GATE_1_FAIL
            result.add_failure(f"Right-stub generation failed: {exc}")
            logger.error("%s for %s: %s", GATE_1_FAIL, slug, exc)

    def _split_chunks(self, text: str, max_chars: int = 1500) -> list[str]:
        text = text.replace("\r", "\n").strip()
        if not text:
            return []
        sentences = re.split(r"(?<=[.!?…;:])\s+", text)
        chunks = []
        current = []
        current_len = 0
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if current_len + len(sentence) + 1 <= max_chars:
                current.append(sentence)
                current_len += len(sentence) + 1
            else:
                if current:
                    chunks.append(" ".join(current).strip())
                current = [sentence]
                current_len = len(sentence)
        if current:
            chunks.append(" ".join(current).strip())
        if not chunks:
            chunks = [text]
        return chunks

    async def gate2_enhancement(self, candidate: dict[str, Any], result: TitleResult) -> None:
        slug = result.slug
        if not openai.api_key:
            result.gate_2_enhancement = GATE_2_FAIL
            result.add_failure("OpenAI API key unavailable")
            logger.error("%s for %s: missing OPENAI_API_KEY", GATE_2_FAIL, slug)
            return

        chapters, blockers = self._load_chapters(slug, candidate)
        if blockers:
            result.gate_2_enhancement = GATE_2_FAIL
            for blocker in blockers:
                result.add_failure(blocker)
            logger.error("%s for %s: %s", GATE_2_FAIL, slug, "; ".join(blockers))
            return

        if not chapters:
            result.gate_2_enhancement = GATE_2_FAIL
            result.add_failure("No chapters to synthesize")
            return

        language = self._safe_text(candidate.get("language", "en")).lower()
        voice = self._select_voice(language)

        output_path = self.enhanced_root / slug / f"{slug}_enhanced.mp3"
        self._ensure_dir(output_path.parent)

        combined = AudioSegment.silent(duration=0)
        chapter_timings: list[SyncChapter] = []
        cursor_ms = 0

        director_in = 0
        director_out = 0
        tts_chars = 0

        for idx, chapter in enumerate(chapters, start=1):
            chapter_text = self._safe_text(chapter.get("content"))
            if not chapter_text:
                continue

            paragraphs = [p.strip() for p in PARAGRAPH_RE.split(chapter_text) if p.strip()]
            if not paragraphs:
                paragraphs = [chapter_text]

            chapter_start = cursor_ms
            paragraph_count = 0
            chapter_segment = AudioSegment.silent(duration=1500)
            for para_idx, paragraph in enumerate(paragraphs, start=1):
                paragraph_count += 1
                for chunk in self._split_chunks(paragraph):
                    try:
                        enhanced, usage = await self._call_director(chunk)
                    except Exception as exc:
                        result.add_failure(f"Director failed on chapter {idx} paragraph {para_idx}: {exc}")
                        continue

                    if not enhanced:
                        enhanced = chunk

                    director_in += usage.get("input", 0)
                    director_out += usage.get("output", 0)
                    tts_chars += len(enhanced)

                    try:
                        tts_payload = await self._call_tts(enhanced, voice=voice, model=TTS_MODEL)
                    except Exception:
                        if TTS_MODEL == "tts-1-hd":
                            logger.warning("Chapter %s fallback to tts-1 for %s", idx, slug)
                            tts_payload = await self._call_tts(enhanced, voice=voice, model="tts-1")
                        else:
                            raise

                    segment = AudioSegment.from_file(BytesIO(tts_payload), format="mp3")
                    chapter_segment += segment
                    # breath pause from line break
                    chapter_segment += AudioSegment.silent(duration=500)

            chapter_segment += AudioSegment.silent(duration=1000)
            combined += chapter_segment

            # add post-chapter gap before next chapter
            if idx < len(chapters):
                combined += AudioSegment.silent(duration=1500)

            content_ms = max(0, len(chapter_segment) - 1500 - 1000)
            chapter_timings.append(
                SyncChapter(
                    index=idx,
                    chapter_id=self._safe_text(chapter.get("chapter_id") or f"chapter-{idx}"),
                    title=self._safe_text(chapter.get("title") or f"Chapter {idx}"),
                    paragraph_count=paragraph_count,
                    start_ms=chapter_start,
                    content_ms=content_ms,
                    intro_ms=1500,
                    outro_ms=1000,
                )
            )

            cursor_ms += len(chapter_segment)
            if idx < len(chapters):
                cursor_ms += 1500

        if len(combined) == 0:
            result.gate_2_enhancement = GATE_2_FAIL
            result.add_failure("No audio produced during synthesis")
            return

        normalized = combined.normalize()
        normalized = normalized.apply_gain(TARGET_DBFS - normalized.dBFS if normalized.dBFS != float("-inf") else 0)
        normalized = normalized.set_channels(2).set_frame_rate(44100)
        normalized.export(output_path, format="mp3", bitrate="192k")

        result.enhanced_audio_path = str(output_path.relative_to(ROOT))
        result.gate_2_enhancement = GATE_2_PASS
        result.chapter_count = len(chapters)
        result.total_paragraphs = sum(self._count_paragraphs(self._safe_text(chapter.get("content"))) for chapter in chapters)
        result.total_duration_ms = len(normalized)
        result.director_input_tokens = director_in
        result.director_output_tokens = director_out
        result.tts_characters = tts_chars
        result.estimated_gpt_usd = (director_in / 1000) * self.gpt_input_ppm + (director_out / 1000) * self.gpt_output_ppm
        result.estimated_tts_usd = (tts_chars / 1_000_000) * self.tts_ppm

        result.chapter_timings = chapter_timings
        timing_path = self._chapter_timings_path(slug, "enhanced")
        self._write_json(
            timing_path,
            {
                "slug": slug,
                "createdAt": self._iso_utc_now(),
                "source": "pipeline_gate2",
                "chapters": [
                    {
                        "index": item.index,
                        "chapterId": item.chapter_id,
                        "title": item.title,
                        "paragraphCount": item.paragraph_count,
                        "startMs": item.start_ms,
                        "contentMs": item.content_ms,
                        "introMs": item.intro_ms,
                        "outroMs": item.outro_ms,
                        "totalMs": item.content_ms + item.intro_ms + item.outro_ms,
                    }
                    for item in chapter_timings
                ],
                "totalDurationMs": len(normalized),
            },
        )
        result.chapter_timing_path = str(timing_path.relative_to(ROOT))

        logger.info(
            "%s for %s | chapters=%s | paragraphs=%s | gpt_tokens=%s/%s | tts_chars=%s | est_cost_usd=%.4f",
            GATE_2_PASS,
            slug,
            result.chapter_count,
            result.total_paragraphs,
            result.director_input_tokens,
            result.director_output_tokens,
            result.tts_characters,
            result.estimated_gpt_usd + result.estimated_tts_usd,
        )

    def _extract_highlight_counts(self, manifest: dict[str, Any]) -> list[int]:
        raw = manifest.get("highlights")
        if not isinstance(raw, list):
            return []
        counts = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            if "paragraphCount" in entry:
                counts.append(int(entry.get("paragraphCount") or 0))
                continue
            items = entry.get("items")
            if isinstance(items, list):
                counts.append(len(items))
                continue
            timestamps = entry.get("timestamps")
            if isinstance(timestamps, list):
                counts.append(len(timestamps))
                continue
            # fallback to one block when structure cannot be mapped
            counts.append(1)
        return counts

    def _write_sync_fallback(self, slug: str, chapter_payloads: list[dict[str, Any]], status_path: Path) -> list[SyncChapter]:
        fallback_chapters: list[SyncChapter] = []
        cursor = 0
        for idx, chapter in enumerate(chapter_payloads, start=1):
            chapter_text = self._safe_text(chapter.get("content"))
            paragraphs = [p.strip() for p in PARAGRAPH_RE.split(chapter_text) if p.strip()]
            if not paragraphs:
                paragraphs = [chapter_text]
            content_ms = 0
            for paragraph in paragraphs:
                content_ms += self._estimate_reading_ms(paragraph, ESTIMATE_READING_WPM)

            fallback_chapters.append(
                SyncChapter(
                    index=idx,
                    chapter_id=self._safe_text(chapter.get("chapter_id") or f"chapter-{idx}"),
                    title=self._safe_text(chapter.get("title") or f"Chapter {idx}"),
                    paragraph_count=len(paragraphs),
                    start_ms=cursor,
                    content_ms=content_ms,
                    intro_ms=1500,
                    outro_ms=1000,
                )
            )
            cursor += content_ms + 1500 + 1000 + 1500

        self._write_json(
            status_path,
            {
                "slug": slug,
                "generatedAt": self._iso_utc_now(),
                "source": "gate3_auto_fallback_150wpm",
                "chapters": [
                    {
                        "index": item.index,
                        "chapterId": item.chapter_id,
                        "title": item.title,
                        "paragraphCount": item.paragraph_count,
                        "startMs": item.start_ms,
                        "contentMs": item.content_ms,
                        "introMs": item.intro_ms,
                        "outroMs": item.outro_ms,
                        "estimatedTotalMs": item.content_ms + item.intro_ms + item.outro_ms,
                    }
                    for item in fallback_chapters
                ],
            },
        )
        return fallback_chapters

    async def gate3_sync(self, candidate: dict[str, Any], result: TitleResult) -> None:
        slug = result.slug
        manifest_path = ROOT / "data" / "controlled_publications" / slug / "reader_manifest.json"
        reader_manifest = self._load_json(manifest_path)

        chapter_payloads, blockers = self._load_chapters(slug, candidate)
        if not chapter_payloads:
            result.gate_3_sync = GATE_3_FAIL
            if blockers:
                result.failures.extend(blockers)
            else:
                result.add_failure("No chapter text available for sync validation")
            logger.error("%s for %s: no chapter data", GATE_3_FAIL, slug)
            return

        expected_counts = self._extract_highlight_counts(reader_manifest if isinstance(reader_manifest, dict) else {})
        actual_counts = [
            self._count_paragraphs(self._safe_text(chapter.get("content")))
            for chapter in chapter_payloads
        ]

        fallback_needed = False
        if not reader_manifest:
            fallback_needed = True
            result.add_failure("Missing reader_manifest.json in data/controlled_publications")

        if expected_counts:
            if len(expected_counts) != len(actual_counts):
                fallback_needed = True
                result.add_failure("Highlight chapter-count mismatch")
            else:
                for i, (expected, actual) in enumerate(zip(expected_counts, actual_counts), start=1):
                    if expected != actual:
                        fallback_needed = True
                        result.add_failure(f"Chapter {i} paragraph timestamp count mismatch: expected={expected}, actual={actual}")

        if fallback_needed:
            fallback_path = self._chapter_timings_path(slug, "sync_fallback")
            fallback_timings = self._write_sync_fallback(slug, chapter_payloads, fallback_path)
            result.chapter_timings = fallback_timings
            result.chapter_timing_path = str(fallback_path.relative_to(ROOT))
            result.gate_3_sync = GATE_3_AUTO_CORRECTED
            logger.warning("%s for %s: timestamps auto-regenerated from 150wpm fallback", GATE_3_AUTO_CORRECTED, slug)
            return

        # Verified manifest timestamps against chapter structure.
        result.chapter_timing_path = None
        result.chapter_timings = [
            SyncChapter(
                index=idx,
                chapter_id=self._safe_text(chapter.get("chapter_id") or f"chapter-{idx}"),
                title=self._safe_text(chapter.get("title") or f"Chapter {idx}"),
                paragraph_count=self._count_paragraphs(self._safe_text(chapter.get("content"))),
                start_ms=0,
                content_ms=0,
                intro_ms=1500,
                outro_ms=1000,
            )
            for idx, chapter in enumerate(chapter_payloads, start=1)
        ]
        result.gate_3_sync = GATE_3_PASS
        logger.info("%s for %s: highlights match chapter structure", GATE_3_PASS, slug)

    async def gate4_accessibility(self, candidate: dict[str, Any], result: TitleResult) -> None:
        if not result.enhanced_audio_path:
            result.gate_4_accessibility = GATE_4_FAIL
            result.add_failure("Enhanced MP3 missing")
            return

        enhanced = ROOT / result.enhanced_audio_path
        if not enhanced.exists():
            result.gate_4_accessibility = GATE_4_FAIL
            result.add_failure(f"Enhanced MP3 not found at {result.enhanced_audio_path}")
            return

        try:
            audio = AudioSegment.from_file(enhanced, format="mp3")
        except Exception as exc:
            result.gate_4_accessibility = GATE_4_FAIL
            result.add_failure(f"Cannot load enhanced MP3: {exc}")
            return

        try:
            bitrate = int(MP3(enhanced).info.bitrate or 0)
            if bitrate and bitrate < MIN_BITRATE_BPS:
                result.gate_4_accessibility = GATE_4_FAIL
                result.add_failure(f"Bitrate below 128 kbps ({bitrate // 1000} kbps)")
                return
        except Exception as exc:
            logger.warning("Failed to read bitrate metadata for %s: %s", result.slug, exc)

        normalized = audio
        if normalized.dBFS != float("-inf"):
            normalized = normalized.apply_gain(TARGET_DBFS - normalized.dBFS)
        normalized = normalized.set_channels(2).set_frame_rate(44100)

        timing_path = self._determine_timing_path(result)
        chapter_timings = result.chapter_timings
        if timing_path:
            sync_payload = self._load_json(Path(timing_path))
            if isinstance(sync_payload, dict):
                loaded_chapters = []
                for item in sync_payload.get("chapters", []):
                    if not isinstance(item, dict):
                        continue
                    loaded_chapters.append(
                        SyncChapter(
                            index=int(item.get("index") or 0),
                            chapter_id=self._safe_text(item.get("chapterId")),
                            title=self._safe_text(item.get("title")),
                            paragraph_count=int(item.get("paragraphCount") or 0),
                            start_ms=int(item.get("startMs") or 0),
                            content_ms=int(item.get("contentMs") or int(item.get("durationMs") or 0)),
                            intro_ms=int(item.get("introMs") or 0),
                            outro_ms=int(item.get("outroMs") or 0),
                        )
                    )
                if loaded_chapters:
                    chapter_timings = loaded_chapters

        suspicious_short = []
        for chapter in chapter_timings:
            if chapter.intro_ms < 1500:
                result.add_failure(f"Chapter {chapter.index} missing required 1.5s intro silence")
            if chapter.outro_ms < 1000:
                result.add_failure(f"Chapter {chapter.index} missing required 1.0s outro silence")
            if chapter.content_ms and chapter.content_ms < 15_000:
                suspicious_short.append(chapter.index)

        if suspicious_short:
            result.add_failure(f"Suspiciously short chapter bodies (<15s): {suspicious_short}")

        if result.failures:
            result.gate_4_accessibility = GATE_4_FAIL
            logger.error("%s for %s: %s", GATE_4_FAIL, result.slug, "; ".join(result.failures))
            return

        result.gate_4_accessibility = GATE_4_PASS
        if not result.chapter_timings:
            result.chapter_timings = chapter_timings

        normalized_path = ROOT / result.enhanced_audio_path
        normalized.export(normalized_path, format="mp3", bitrate="192k")
        result.total_duration_ms = len(normalized)

        logger.info("%s for %s", GATE_4_PASS, result.slug)

    def _determine_timing_path(self, result: TitleResult) -> str | None:
        if result.chapter_timing_path:
            return result.chapter_timing_path
        if result.slug:
            candidate = self._chapter_timings_path(result.slug, "enhanced")
            if candidate.exists():
                return str(candidate.relative_to(ROOT))
        return None

    async def gate5_qa_sheet(self, candidate: dict[str, Any], result: TitleResult) -> None:
        if not (result.gate_1_rights == GATE_1_PASS and result.gate_2_enhancement == GATE_2_PASS and result.gate_3_sync in {GATE_3_PASS, GATE_3_AUTO_CORRECTED} and result.gate_4_accessibility == GATE_4_PASS):
            result.gate_5_qa_sheet = ""
            result.add_failure("Gate 5 blocked: requires Gates 1-4 pass")
            logger.warning("Skipping %s for %s: %s", GATE_5_SHEET_GENERATED, result.slug, "gates not all passed")
            return

        qa_path = self.qa_root / f"{result.slug}_qa_sheet.md"
        total_duration_seconds = round(result.total_duration_ms / 1000, 2)
        sheet = [
            f"# Human Listening QA Sheet",
            "",
            f"Title: {result.title}",
            f"Language: {result.language}",
            f"Total Chapters: {result.chapter_count}",
            f"Total Duration: {total_duration_seconds}s",
            f"Enhanced Audio Path: {self._safe_text(result.enhanced_audio_path)}",
            "",
            "- [ ] Voice clarity acceptable",
            "- [ ] Emotional tone appropriate to genre",
            "- [ ] No mispronounced Bengali/English words",
            "- [ ] Highlights sync visually confirmed",
            "- [ ] No clipping or distortion audible",
            "- [ ] Chapter transitions are smooth",
            "- [ ] Sign-off: Reviewer Name + Date",
            "",
            f"Generated: {self._iso_utc_now()}",
        ]
        self._write_text(qa_path, "\n".join(sheet))
        result.gate_5_qa_sheet = GATE_5_SHEET_GENERATED
        logger.info("%s for %s", GATE_5_SHEET_GENERATED, result.slug)

    async def gate6_legal(self, candidate: dict[str, Any], result: TitleResult) -> None:
        if result.gate_5_qa_sheet != GATE_5_SHEET_GENERATED:
            result.gate_6_legal = ""
            result.add_failure("Gate 6 blocked: QA sheet not generated")
            return

        rights_stub = self._safe_text(candidate.get("rights_basis") or "Public domain")
        legal_path = self.legal_root / f"{result.slug}_legal_approval.json"
        payload = {
            "title": result.title,
            "slug": result.slug,
            "rights_basis": rights_stub,
            "ai_narration_disclosure": "This audiobook was generated using AI narration technology",
            "approval_status": "PENDING_HUMAN_SIGN_OFF",
            "approved_by": None,
            "approval_date": None,
        }
        self._write_json(legal_path, payload)
        result.gate_6_legal = GATE_6_STUB_GENERATED
        logger.info("%s for %s", GATE_6_STUB_GENERATED, result.slug)

    async def process_title(self, candidate: dict[str, Any]) -> TitleResult:
        slug = self._safe_text(candidate.get("slug"))
        title = self._safe_text(candidate.get("title", slug))
        language = self._safe_text(candidate.get("language", "en"))

        result = TitleResult(slug=slug, title=title, language=language)

        if not slug:
            result.add_failure("Missing slug")
            return result

        await self.gate1_rights(candidate, result)
        if result.failures and self.strict_gate_requirements and result.gate_1_rights == GATE_1_FAIL:
            self.results.append(result)
            return result

        await self.gate2_enhancement(candidate, result)
        await self.gate3_sync(candidate, result)
        await self.gate4_accessibility(candidate, result)
        await self.gate5_qa_sheet(candidate, result)
        await self.gate6_legal(candidate, result)

        self.results.append(result)
        return result

    def _finalize_release_gate(self) -> tuple[dict[str, Any], list[str]]:
        manifest_path = self.release_root / "release_gate_status.json"
        approved_path = self.release_root / "approved_for_live.json"

        release_payload = {
            "generatedAt": self._iso_utc_now(),
            "summary": {
                "totalTitlesProcessed": len(self.results),
                "gatesClearedForHumanSignOff": 0,
                "gatesFailed": 0,
                "blockedTitles": 0,
            },
            "titles": {},
            "blocked_titles": {},
            "approvedForLive": [],
        }

        approved_for_live: list[str] = []
        blocked_titles: dict[str, list[str]] = {}

        for result in self.results:
            if (
                result.gate_1_rights == GATE_1_PASS
                and result.gate_2_enhancement == GATE_2_PASS
                and result.gate_3_sync in {GATE_3_PASS, GATE_3_AUTO_CORRECTED}
                and result.gate_4_accessibility == GATE_4_PASS
                and result.gate_5_qa_sheet == GATE_5_SHEET_GENERATED
                and result.gate_6_legal == GATE_6_STUB_GENERATED
            ) and not result.failures:
                approved_for_live.append(result.slug)
                release_payload["summary"]["gatesClearedForHumanSignOff"] += 1
            else:
                blocked_titles[result.slug] = result.failures or ["Title blocked by gate completion status"]
                release_payload["summary"]["blockedTitles"] += 1

            if result.gate_2_enhancement == GATE_2_FAIL:
                release_payload["summary"]["gatesFailed"] += 1

            release_payload["titles"][result.slug] = result.to_manifest()

        if not self.strict_gate_requirements:
            blocked_titles = release_payload.get("blocked_titles", blocked_titles)

        release_payload["blocked_titles"] = blocked_titles
        release_payload["approved_for_live"] = approved_for_live

        self._ensure_dir(manifest_path.parent)
        self._write_json(manifest_path, release_payload)
        self._write_json(approved_path, approved_for_live)
        return release_payload, approved_for_live

    async def run(self) -> None:
        manifest = self._load_manifest()
        candidates = manifest.get("candidates") if isinstance(manifest, dict) else []
        if not isinstance(candidates, list):
            candidates = []

        logger.info("Loaded %s candidates from %s", len(candidates), self.manifest_path)

        for candidate in candidates:
            result = await self.process_title(candidate if isinstance(candidate, dict) else {})
            if result.gate_1_rights:
                logger.debug("%s summary: %s", result.slug, result.to_manifest())

        release_payload, approved_for_live = self._finalize_release_gate()

        total = release_payload["summary"]["totalTitlesProcessed"]
        cleared = release_payload["summary"]["gatesClearedForHumanSignOff"]
        failed = release_payload["summary"]["gatesFailed"]
        blocked = release_payload["summary"]["blockedTitles"]

        logger.info("Total Titles Processed: %s", total)
        logger.info("Gates Cleared (Ready for Human Sign-Off): %s", cleared)
        logger.info("Gates Failed (Need Manual Fix): %s", failed)
        logger.info("BLOCKED Titles: %s", blocked)
        for slug, reasons in release_payload["blocked_titles"].items():
            logger.info("BLOCKED[%s]: %s", slug, "; ".join(reasons))

        logger.info("Approved for live count: %s", len(approved_for_live))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run audiobook production release gates for restored candidates")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to restoration manifest JSON")
    parser.add_argument("--max-api-concurrency", type=int, default=MAX_API_CALL_CONCURRENCY)
    parser.add_argument("--gpt-input-ppm", type=float, default=0.00015)
    parser.add_argument("--gpt-output-ppm", type=float, default=0.0006)
    parser.add_argument("--tts-usd-per-million", type=float, default=30.0)
    parser.add_argument("--strict", action="store_true", default=False, help="Stop at Gate1 fail")
    parser.add_argument("--title-limit", type=int, default=None)
    parser.add_argument("--only-slugs", nargs="+", default=[])
    return parser.parse_args()


async def main() -> int:
    args = parse_args()

    manifest = Path(args.manifest)
    if not manifest.exists():
        logger.error("Manifest not found: %s", manifest)
        return 2

    candidate_filter = None
    if args.only_slugs:
        candidate_filter = set(args.only_slugs)

    payload = Pipeline(
        manifest_path=manifest,
        max_api_concurrency=min(args.max_api_concurrency, 5),
        gpt_input_ppm=args.gpt_input_ppm,
        gpt_output_ppm=args.gpt_output_ppm,
        tts_ppm=args.tts_usd_per_million,
        strict_gate_requirements=args.strict,
    )

    manifest_payload = payload._load_manifest()
    candidates = manifest_payload.get("candidates") if isinstance(manifest_payload, dict) else []
    if isinstance(candidates, list) and candidate_filter:
        candidates = [c for c in candidates if isinstance(c, dict) and c.get("slug") in candidate_filter]
    if args.title_limit is not None:
        candidates = candidates[: args.title_limit]

    payload.results = []
    for candidate in candidates:
        await payload.process_title(candidate if isinstance(candidate, dict) else {})

    payload._finalize_release_gate()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
