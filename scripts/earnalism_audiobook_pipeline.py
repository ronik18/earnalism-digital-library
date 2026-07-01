#!/usr/bin/env python3
"""Optimized Bengali/English audiobook production pipeline for Earnalism."""

from __future__ import annotations

import argparse
import asyncio
import os
import logging
import random
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, List, Optional

import tiktoken
from openai import APITimeoutError, APIConnectionError, APIError
from openai import AsyncOpenAI
from openai import APIStatusError, RateLimitError
from pydub import AudioSegment
from pydub.effects import normalize


LOGGER = logging.getLogger("earnalism-audio-pipeline")

DIRECTOR_SYSTEM_PROMPT = (
    "You are an audiobook voice director formatting text for OpenAI's TTS engine. "
    "The TTS engine reads exactly what is written. Rewrite the provided text to maximize "
    "natural human pacing, breath-taking, and dramatic tension using ONLY punctuation and spelling. "
    "RULES:\n"
    "- Insert em-dashes (—) or ellipses (...) to force natural dramatic pauses.\n"
    "- Break up overly long run-on sentences so the narrator takes a breath.\n"
    "- Spell out complex numbers, acronyms, or non-English words phonetically so the TTS doesn't stumble (e.g., 'Rs. 1500' becomes 'fifteen hundred rupees').\n"
    "- Do NOT add narrator notes, sound effects, or alter the actual narrative meaning. Just optimize the punctuation for speech."
)

CHAPTER_HEADER_RE = re.compile(r"^\s*(?:chapter|part|book)\b.*$", re.IGNORECASE)


@dataclass
class ManuscriptChunk:
    chapter: int
    index: int
    text: str


@dataclass
class ProcessedChunk:
    chunk: ManuscriptChunk
    optimized_text: str
    audio_bytes: bytes
    tts_chars: int
    gpt_input_tokens: int
    gpt_output_tokens: int
    processing_error: Optional[str] = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a stitched audiobook from manuscript text using GPT-4o-mini "
            "as a paragraph director and OpenAI TTS."
        )
    )
    parser.add_argument("--input", required=True, help="Path to source manuscript (.txt)")
    parser.add_argument("--book-title", required=True, help="Book title used in final export name")
    parser.add_argument("--output-dir", default="output", help="Directory to write final mp3 and report")
    parser.add_argument("--max-chunk-chars", type=int, default=2000, help="Maximum chars per LLM/TTS chunk")
    parser.add_argument(
        "--director-model",
        default="gpt-4o-mini",
        help="LLM Director model",
    )
    parser.add_argument(
        "--tts-model",
        default="tts-1-hd",
        help="Primary TTS model (fallback to --tts-fallback)",
    )
    parser.add_argument(
        "--tts-fallback",
        default="tts-1",
        help="Fallback TTS model if primary fails",
    )
    parser.add_argument(
        "--tts-voice",
        default="onyx",
        choices=["nova", "onyx", "ash", "fable", "echo", "sage", "shimmer"],
        help="TTS voice",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=5,
        help="Max simultaneous OpenAI API calls (default: 5)",
    )
    parser.add_argument("--gpt-in-price-per-1k", type=float, default=0.00015, help="gpt-4o-mini input price per 1k tokens")
    parser.add_argument("--gpt-out-price-per-1k", type=float, default=0.0006, help="gpt-4o-mini output price per 1k tokens")
    parser.add_argument(
        "--tts-price-per-million-chars",
        type=float,
        default=30.0,
        help="OpenAI TTS price per million chars (tts-1-hd default).",
    )
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--sentence-max-attempts", type=int, default=4, help="Retry budget for API calls")
    return parser.parse_args()


def read_source_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            f"Invalid or corrupt UTF-8 input file: {path}. "
            "Normalize/convert to UTF-8 before running the pipeline."
        ) from exc
    except OSError as exc:
        raise RuntimeError(f"Failed to read source file: {path}") from exc


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def sanitize_text(raw_text: str) -> str:
    normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def is_chapter_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if len(stripped) > 120:
        return False
    if stripped.startswith("http"):
        return False
    return bool(CHAPTER_HEADER_RE.match(stripped))


def split_by_paragraph_and_chapter(
    text: str,
    max_chars: int,
) -> List[ManuscriptChunk]:
    chunks: List[ManuscriptChunk] = []
    lines = sanitize_text(text).split("\n")

    paragraph_lines: List[str] = []
    chapter_no = 1
    paragraph_no = 0

    def flush_paragraph() -> None:
        nonlocal paragraph_lines, paragraph_no
        para = " ".join([ln.strip() for ln in paragraph_lines]).strip()
        if not para:
            return
        # Enforce size boundaries.
        for chunk in split_overflow_paragraph(para, max_chars=max_chars):
            chunks.append(ManuscriptChunk(chapter=chapter_no, index=paragraph_no, text=chunk))
            paragraph_no += 1
        paragraph_lines = []

    for raw_line in lines:
        line = raw_line.strip()
        if is_chapter_line(line):
            flush_paragraph()
            chunks.append(ManuscriptChunk(chapter=chapter_no, index=paragraph_no, text=line))
            paragraph_no += 1
            chapter_no += 1
            paragraph_lines = []
            continue

        if not line:
            flush_paragraph()
            continue
        paragraph_lines.append(line)

    flush_paragraph()

    # Re-number index across potential chapter headings and long splits
    for idx, chunk in enumerate(chunks):
        chunk.index = idx
    return chunks


def split_overflow_paragraph(text: str, max_chars: int) -> List[str]:
    if len(text) <= max_chars:
        return [text]

    # First attempt to cut at sentence boundaries.
    candidates = re.split(r"(?<=[.!?…])\s+", text)
    chunks: List[str] = []
    current = ""

    for sentence in candidates:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > max_chars:
            # hard fallback: hard window split preserving punctuation
            for offset in range(0, len(sentence), max_chars):
                chunks.append(sentence[offset : offset + max_chars])
            continue

        if not current:
            current = sentence
            continue

        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}"
        else:
            chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)

    return chunks


def safe_filename(base_name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9 _-]", "_", base_name).strip().replace(" ", "_")


async def retry(
    operation_name: str,
    call,
    max_attempts: int = 4,
    base_delay: float = 0.75,
) -> Any:
    for attempt in range(1, max_attempts + 1):
        try:
            return await call()
        except (RateLimitError, APIConnectionError, APITimeoutError, APIStatusError) as exc:
            transient = True
            if isinstance(exc, APIStatusError):
                status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
                if status and status < 500 and status != 429:
                    transient = False
            if not transient or attempt == max_attempts:
                LOGGER.error("%s failed after %s attempt(s): %s", operation_name, attempt, exc)
                raise

            sleep_time = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.4)
            LOGGER.warning(
                "%s transient failure (%s), retrying in %.2fs (attempt %s/%s)",
                operation_name,
                exc.__class__.__name__,
                sleep_time,
                attempt,
                max_attempts,
            )
            await asyncio.sleep(sleep_time)
        except APIError as exc:
            # non-retriable API errors should surface immediately
            LOGGER.error("%s failed with API error: %s", operation_name, exc)
            raise


class DirectorTtsEngine:
    def __init__(
        self,
        director_model: str,
        tts_model: str,
        tts_fallback: str,
        voice: str,
        max_concurrency: int,
        sentence_max_attempts: int,
    ) -> None:
        self.client = AsyncOpenAI()
        self.director_model = director_model
        self.tts_model = tts_model
        self.tts_fallback = tts_fallback
        self.voice = voice
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.tries = sentence_max_attempts
        self.encoder = tiktoken.get_encoding("cl100k_base")

    async def _optimize_with_director(self, text: str) -> tuple[str, int, int]:
        async with self.semaphore:
            async def _call() -> Any:
                return await self.client.chat.completions.create(
                    model=self.director_model,
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": DIRECTOR_SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": (
                                "Rewrite the following paragraph for TTS pacing and clarity "
                                "while preserving meaning:\n\n"
                                f"{text}"
                            ),
                        },
                    ],
                )

            response = await retry("LLM Director", _call, max_attempts=self.tries)
            result = (response.choices[0].message.content or "").strip()
            usage = response.usage
            in_tokens = getattr(usage, "prompt_tokens", 0)
            out_tokens = getattr(usage, "completion_tokens", 0)
            if not result:
                return text, in_tokens, out_tokens
            return result, in_tokens, out_tokens

    async def _generate_audio(self, text: str, use_fallback: bool = False) -> bytes:
        model = self.tts_fallback if use_fallback else self.tts_model

        async with self.semaphore:
            async def _call() -> Any:
                response = await self.client.audio.speech.with_raw_response.create(
                    model=model,
                    voice=self.voice,
                    input=text,
                    response_format="mp3",
                )
                return response

            response = await retry(f"TTS[{model}]", _call, max_attempts=self.tries)
            if hasattr(response, "read"):
                return await response.read()
            content = getattr(response, "content", None)
            if content is not None and isinstance(content, (bytes, bytearray)):
                return bytes(content)
            raise RuntimeError(f"Unable to extract mp3 bytes from {model} response")

    async def process_chunk(self, chunk: ManuscriptChunk) -> ProcessedChunk:
        input_tokens = len(self.encoder.encode(chunk.text))
        try:
            optimized_text, in_tokens_llm, out_tokens_llm = await self._optimize_with_director(chunk.text)
            try:
                audio = await self._generate_audio(optimized_text, use_fallback=False)
            except Exception:
                LOGGER.warning("Primary TTS failed for chunk %s; retrying fallback model %s", chunk.index, self.tts_fallback)
                audio = await self._generate_audio(optimized_text, use_fallback=True)
            return ProcessedChunk(
                chunk=chunk,
                optimized_text=optimized_text,
                audio_bytes=audio,
                tts_chars=len(optimized_text),
                gpt_input_tokens=input_tokens + in_tokens_llm,
                gpt_output_tokens=out_tokens_llm,
            )
        except Exception as exc:
            LOGGER.exception("Chunk processing failed: chapter=%s index=%s", chunk.chapter, chunk.index)
            return ProcessedChunk(
                chunk=chunk,
                optimized_text=chunk.text,
                audio_bytes=b"",
                tts_chars=0,
                gpt_input_tokens=0,
                gpt_output_tokens=0,
                processing_error=f"{exc}",
            )


def stitch_segments(processed: List[ProcessedChunk], output_path: Path, book_name: str) -> Path:
    successful = [p for p in sorted(processed, key=lambda item: (item.chunk.chapter, item.chunk.index)) if not p.processing_error]
    if not successful:
        raise RuntimeError("No successfully synthesized chunks available to stitch.")

    output = AudioSegment.silent(duration=0)
    prev_chapter: Optional[int] = None

    paragraph_pause = AudioSegment.silent(duration=400)
    chapter_pause = AudioSegment.silent(duration=1500)

    for item in successful:
        if prev_chapter is not None and item.chunk.chapter != prev_chapter:
            output += chapter_pause
        elif prev_chapter is not None:
            output += paragraph_pause

        segment = AudioSegment.from_file(BytesIO(item.audio_bytes), format="mp3")
        segment = normalize(segment)
        output += segment
        prev_chapter = item.chunk.chapter

    # gentle anti-fatigue gate tone removed by default; keep silent guard.
    guard_pad = AudioSegment.silent(duration=250)
    output = guard_pad + output + guard_pad
    output = output.set_frame_rate(22050).set_channels(2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.export(output_path, format="mp3", bitrate="192k", tags={"title": book_name, "album": book_name})
    return output_path


def write_run_report(
    result_items: List[ProcessedChunk],
    output_dir: Path,
    total_gpt_tokens: dict[str, int],
    total_tts_chars: int,
    args: argparse.Namespace,
) -> Path:
    passed = [item for item in result_items if not item.processing_error]
    failed = [item for item in result_items if item.processing_error]

    estimated_gpt_input_cost = (total_gpt_tokens["input"] / 1000.0) * args.gpt_in_price_per_1k
    estimated_gpt_output_cost = (total_gpt_tokens["output"] / 1000.0) * args.gpt_out_price_per_1k
    tts_cost = (total_tts_chars / 1_000_000.0) * args.tts_price_per_million_chars

    report = {
        "book_title": args.book_title,
        "source": str(Path(args.input).resolve()),
        "chunks": {
            "total": len(result_items),
            "passed": len(passed),
            "failed": len(failed),
        },
        "token_and_cost": {
            "gpt_input_tokens_used": total_gpt_tokens["input"],
            "gpt_output_tokens_used": total_gpt_tokens["output"],
            "gpt_total_tokens_used": total_gpt_tokens["input"] + total_gpt_tokens["output"],
            "tts_chars": total_tts_chars,
            "estimated_gpt_input_cost_usd": round(estimated_gpt_input_cost, 4),
            "estimated_gpt_output_cost_usd": round(estimated_gpt_output_cost, 4),
            "estimated_gpt_cost_usd": round(estimated_gpt_input_cost + estimated_gpt_output_cost, 4),
            "estimated_tts_cost_usd": round(tts_cost, 4),
            "estimated_total_cost_usd": round(estimated_gpt_input_cost + estimated_gpt_output_cost + tts_cost, 4),
            "pricing": {
                "gpt_input_per_1k": args.gpt_in_price_per_1k,
                "gpt_output_per_1k": args.gpt_out_price_per_1k,
                "tts_per_million_chars": args.tts_price_per_million_chars,
            },
        },
        "failed_chunks": [
            {"chapter": item.chunk.chapter, "index": item.chunk.index, "error": item.processing_error}
            for item in failed
        ],
        "passed_chunks": [
            {
                "chapter": item.chunk.chapter,
                "index": item.chunk.index,
                "tts_chars": item.tts_chars,
                "gpt_input_tokens": item.gpt_input_tokens,
                "gpt_output_tokens": item.gpt_output_tokens,
            }
            for item in passed
        ],
    }

    report_path = output_dir / f"{safe_filename(args.book_title)}_RunReport.json"
    report_path.write_text(
        _to_pretty_json(report),
        encoding="utf-8",
    )
    return report_path


def _to_pretty_json(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, indent=2, ensure_ascii=False)


async def run_pipeline(args: argparse.Namespace) -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required to run this pipeline.")

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file missing: {input_path}")

    source_text = read_source_text(input_path)
    source_text = sanitize_text(source_text)
    chunks = split_by_paragraph_and_chapter(source_text, max_chars=args.max_chunk_chars)

    if not chunks:
        raise RuntimeError("No processable paragraph chunks found in manuscript")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{safe_filename(args.book_title)}_Final.mp3"

    engine = DirectorTtsEngine(
        director_model=args.director_model,
        tts_model=args.tts_model,
        tts_fallback=args.tts_fallback,
        voice=args.tts_voice,
        max_concurrency=args.max_concurrency,
        sentence_max_attempts=args.sentence_max_attempts,
    )

    async def chunk_job(chunk: ManuscriptChunk) -> ProcessedChunk:
        return await engine.process_chunk(chunk)

    jobs = [chunk_job(chunk) for chunk in chunks]
    processed = await asyncio.gather(*jobs)

    failed = [item for item in processed if item.processing_error]
    if failed:
        LOGGER.warning("Some chunks failed. Will continue with successfully synthesized chunks only.")

    final_path = stitch_segments(processed, output_path=output_file, book_name=args.book_title)

    total_tokens = {
        "input": sum(item.gpt_input_tokens for item in processed if not item.processing_error),
        "output": sum(item.gpt_output_tokens for item in processed if not item.processing_error),
    }
    total_tts_chars = sum(item.tts_chars for item in processed if not item.processing_error)
    write_run_report(processed, output_dir, total_tokens, total_tts_chars, args)

    LOGGER.info("Final audiobook: %s", final_path)
    LOGGER.info("Chunks total: %s | passed: %s | failed: %s", len(processed), len(processed) - len(failed), len(failed))
    LOGGER.info("Estimated GPT tokens: %s", total_tokens)
    LOGGER.info("Estimated TTS chars: %s", total_tts_chars)

    if failed:
        return 1
    return 0


def main() -> int:
    args = parse_args()
    setup_logging(args.log_level)
    return asyncio.run(run_pipeline(args))


if __name__ == "__main__":
    raise SystemExit(main())
