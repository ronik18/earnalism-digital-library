#!/usr/bin/env python3
"""Batch-generate Earnalism audiobook assets with Azure Neural TTS.

The script reads an Earnalism book manifest, extracts clean text from either
pre-scraped files or source URLs, builds punctuation-aware SSML, synthesizes
chunked audio through Microsoft Azure, and writes audio plus word-highlight
timing files for the reader.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import unquote, urlparse

AZURE_PRICE_PER_1000_CHARS_USD = 0.016
MAX_CHARS_PER_SSML_CHUNK = 8000
REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_OUTPUT_DIR = "./audio_output"
DEFAULT_VOICES_PATH = "voices.json"


# ---------------------------------------------------------------------------
# Data containers and CLI setup
# ---------------------------------------------------------------------------


@dataclass
class BookText:
    """Clean book text plus detected chapter starts."""

    text: str
    chapters: List[Dict[str, Any]]


@dataclass
class SynthesisResult:
    """Audio and timestamp output for one synthesized chunk."""

    path: Path
    word_boundaries: List[Dict[str, Any]]
    duration_ms: int


class ScrapeFailure(RuntimeError):
    """Raised when a source URL cannot be converted into clean text."""


def parse_args() -> argparse.Namespace:
    """Parse CLI options for batch or single-book audio generation."""

    parser = argparse.ArgumentParser(description="Generate Earnalism audiobook files with Azure Neural TTS.")
    parser.add_argument("--manifest", required=True, help="Path to book_import_manifest.json")
    parser.add_argument("--text-dir", default=None, help="Optional folder containing pre-scraped {slug}.txt files")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Audio output directory")
    parser.add_argument("--slug", default=None, help="Generate one book by slug")
    parser.add_argument("--voices", default=DEFAULT_VOICES_PATH, help="Path to voices.json")
    parser.add_argument("--dry-run", action="store_true", help="Print SSML and cost estimates without Azure calls")
    return parser.parse_args()


def setup_logging(output_dir: Path) -> None:
    """Configure concise console logging and a persistent run log."""

    output_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(output_dir / "generate_audio.log", encoding="utf-8"),
        ],
    )


# ---------------------------------------------------------------------------
# Manifest, voice configuration, and source-text loading
# ---------------------------------------------------------------------------


def load_manifest(path: Path) -> List[Dict[str, Any]]:
    """Load a manifest that may be either a list or an object with a books key."""

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("books"), list):
        return data["books"]
    raise ValueError("Manifest must be a JSON array or an object with a 'books' array.")


def load_voices(path: Path) -> Dict[str, Dict[str, str]]:
    """Load configurable primary/fallback voice names by language."""

    if not path.exists():
        raise FileNotFoundError(f"Voice config not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    required = {"ben", "en"}
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"voices.json is missing language entries: {', '.join(missing)}")
    for lang in required:
        if not data[lang].get("primary") or not data[lang].get("fallback"):
            raise ValueError(f"voices.json entry '{lang}' must define primary and fallback voices.")
    return data


def extract_first_url(value: str) -> str:
    """Accept raw URLs or markdown links and return the first HTTP(S) URL."""

    markdown_link = re.search(r"\[[^\]]*\]\((https?://.+)\)\s*$", value or "")
    if markdown_link:
        return markdown_link.group(1).strip()
    match = re.search(r"https?://[^\s)]+", value or "")
    if match:
        return match.group(0)
    return value or ""


def normalize_slug(value: str) -> str:
    """Create a filesystem-safe slug while preserving Unicode letters."""

    value = unquote(value or "").strip().lower()
    value = re.sub(r"\.[a-z0-9]{1,8}$", "", value)
    value = value.replace("_", "-")
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^\w\-\u0980-\u09ff]+", "", value, flags=re.UNICODE)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "book"


def slug_for_book(book: Dict[str, Any]) -> str:
    """Resolve the slug used for text files and output assets."""

    explicit = book.get("audio_slug") or book.get("slug")
    if explicit:
        return normalize_slug(str(explicit))

    source_url = extract_first_url(str(book.get("source_url") or ""))
    parsed = urlparse(source_url)
    if parsed.path:
        candidate = Path(unquote(parsed.path.rstrip("/"))).name
        if candidate:
            return normalize_slug(candidate)

    return normalize_slug(str(book.get("title") or "book"))


def detect_language(book: Dict[str, Any], text: str = "") -> str:
    """Return 'ben' or 'en' from manifest fields or Bengali Unicode presence."""

    lang = str(book.get("language") or "").strip().lower()
    if lang in {"ben", "bn", "bn-in", "bengali"}:
        return "ben"
    if lang in {"en", "eng", "english", "en-in"}:
        return "en"

    source_type = str(book.get("source_type") or "").lower()
    if "bengali" in source_type or "wikisource_bengali" in source_type:
        return "ben"

    sample = f"{book.get('title', '')} {book.get('author', '')} {text[:1000]}"
    return "ben" if re.search(r"[\u0980-\u09ff]", sample) else "en"


def azure_locale(language: str) -> str:
    """Map manifest language codes to Azure SSML locales."""

    return "bn-IN" if language == "ben" else "en-IN"


def read_pre_scraped_text(text_dir: Optional[Path], slug: str) -> Optional[str]:
    """Read {slug}.txt if provided by the operator."""

    if not text_dir:
        return None
    candidate = text_dir / f"{slug}.txt"
    if candidate.exists():
        logging.info("Using pre-scraped text for %s: %s", slug, candidate)
        return candidate.read_text(encoding="utf-8-sig")
    return None


def scrape_source_text(source_url: str) -> str:
    """Scrape article headings and paragraph text from a legally cleared source URL."""

    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError("Install requirements.txt before scraping source URLs.") from exc

    url = extract_first_url(source_url)
    if not url:
        raise ValueError("Missing source_url")

    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={"User-Agent": "EarnalismAudioGenerator/1.0 (+https://theearnalism.com)"},
    )
    response.raise_for_status()
    response.encoding = response.encoding or "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")
    for selector in [
        "script",
        "style",
        "noscript",
        "nav",
        "header",
        "footer",
        "aside",
        "sup.reference",
        ".reference",
        ".reflist",
        ".mw-editsection",
        ".noprint",
        ".metadata",
        ".navbox",
        ".ambox",
        ".infobox",
        ".printfooter",
        "#toc",
        ".toc",
    ]:
        for node in soup.select(selector):
            node.decompose()

    content = soup.select_one("#mw-content-text .mw-parser-output") or soup.select_one("#mw-content-text")
    content = content or soup.select_one("main") or soup.select_one("article") or soup.body or soup

    lines: List[str] = []
    for node in content.find_all(["h1", "h2", "h3", "p"]):
        text = clean_extracted_line(node.get_text(" ", strip=True))
        if text and not is_boilerplate_line(text):
            lines.append(text)

    if not lines:
        raise ValueError("No readable paragraph text found")
    return "\n\n".join(lines)


def clean_extracted_line(text: str) -> str:
    """Normalize scraped line text without changing literary wording."""

    text = html.unescape(text or "")
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\s*\[সম্পাদনা\]\s*", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_boilerplate_line(text: str) -> bool:
    """Filter obvious navigation and source-wrapper lines."""

    lowered = text.lower()
    banned = [
        "navigation menu",
        "personal tools",
        "namespaces",
        "variants",
        "views",
        "more",
        "search",
        "wikimedia",
        "wikisource",
        "creative commons",
        "privacy policy",
        "terms of use",
        "desktop",
        "mobile view",
        "download",
        "print",
        "cite this page",
    ]
    return any(term in lowered for term in banned)


# ---------------------------------------------------------------------------
# Text normalization, chapter detection, and chunking
# ---------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    """Clean encoding, line endings, HTML tags, citations, and excessive spacing."""

    text = (text or "").replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"<script\b[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b[^>]*>.*?</style>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def word_count(text: str) -> int:
    """Count word-like tokens across English and Bengali text."""

    return len(re.findall(r"[\w\u0980-\u09ff']+", text, flags=re.UNICODE))


def is_heading_line(line: str) -> bool:
    """Conservatively detect chapter/section headings."""

    stripped = line.strip()
    if not stripped or len(stripped) > 90:
        return False
    patterns = [
        r"^(chapter|book|part|volume)\s+([ivxlcdm]+|\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b",
        r"^অধ্যায়\s*[\w\u0980-\u09ff]*",
        r"^পরিচ্ছেদ\s*[\w\u0980-\u09ff]*",
        r"^প্রথম|^দ্বিতীয়|^তৃতীয়|^চতুর্থ|^পঞ্চম|^ষষ্ঠ|^সপ্তম|^অষ্টম|^নবম|^দশম",
    ]
    if any(re.search(pattern, stripped, re.IGNORECASE) for pattern in patterns):
        return True
    if re.fullmatch(r"[IVXLCDM]{1,8}", stripped):
        return True
    return False


def detect_chapters(text: str) -> List[Dict[str, Any]]:
    """Build chapter timestamp anchors using word offsets before each heading."""

    chapters: List[Dict[str, Any]] = []
    running_words = 0
    for paragraph in split_paragraphs(text):
        if is_heading_line(paragraph):
            chapters.append({"heading": paragraph, "word_index": running_words})
        running_words += word_count(paragraph)

    if not chapters:
        return [{"heading": "Full Text", "word_index": 0}]
    if chapters[0]["word_index"] != 0:
        chapters.insert(0, {"heading": "Opening", "word_index": 0})
    return chapters


def split_paragraphs(text: str) -> List[str]:
    """Split on blank lines while preserving paragraph order."""

    return [part.strip() for part in re.split(r"\n\s*\n", text or "") if part.strip()]


def chunk_text(text: str, max_chars: int = MAX_CHARS_PER_SSML_CHUNK) -> List[str]:
    """Split text into Azure-safe chunks, preferring paragraph boundaries."""

    chunks: List[str] = []
    current = ""
    for paragraph in split_paragraphs(text):
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(paragraph) <= max_chars:
            current = paragraph
            continue
        for sentence in split_sentences(paragraph):
            candidate = f"{current} {sentence}".strip() if current else sentence
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = sentence[:max_chars]
                remainder = sentence[max_chars:]
                while remainder:
                    chunks.append(current)
                    current = remainder[:max_chars]
                    remainder = remainder[max_chars:]
    if current:
        chunks.append(current)
    return chunks


def split_sentences(text: str) -> List[str]:
    """Split text into sentence-like units while keeping punctuation."""

    pieces = re.split(r"(?<=[.!?\u0964])\s+", text.strip())
    return [piece.strip() for piece in pieces if piece.strip()]


# ---------------------------------------------------------------------------
# SSML generation
# ---------------------------------------------------------------------------


def punctuate_plain_segment(text: str) -> str:
    """Escape text and insert SSML breaks after punctuation."""

    output: List[str] = []
    i = 0
    while i < len(text):
        if text.startswith("...", i):
            output.append("...<break time=\"700ms\"/>")
            i += 3
            continue
        if text.startswith("--", i):
            output.append("--<break time=\"350ms\"/>")
            i += 2
            continue
        char = text[i]
        if char == "\u2014":
            output.append(f"{html.escape(char)}<break time=\"350ms\"/>")
        elif char in {",", "\u060c"}:
            output.append(f"{html.escape(char)}<break time=\"200ms\"/>")
        elif char in {".", "\u0964"}:
            output.append(f"{html.escape(char)}<break time=\"600ms\"/>")
        elif char in {"?", "\u061f"}:
            output.append(f"{html.escape(char)}<break time=\"500ms\"/>")
        elif char == "!":
            output.append(f"{html.escape(char)}<break time=\"500ms\"/>")
        else:
            output.append(html.escape(char))
        i += 1
    return "".join(output)


def wrap_dialogue_segments(sentence: str) -> str:
    """Apply a gentler prosody to quoted dialogue spans."""

    quote_pattern = re.compile(r"([\"'])(.+?)(\1)")
    pieces: List[str] = []
    last = 0
    for match in quote_pattern.finditer(sentence):
        pieces.append(punctuate_plain_segment(sentence[last : match.start()]))
        quoted = match.group(0)
        pieces.append(
            '<prosody rate="95%" pitch="+5%">'
            f"{punctuate_plain_segment(quoted)}"
            "</prosody>"
        )
        last = match.end()
    pieces.append(punctuate_plain_segment(sentence[last:]))
    return "".join(pieces)


def sentence_to_ssml(sentence: str) -> str:
    """Apply sentence-level expressiveness for questions and exclamations."""

    rendered = wrap_dialogue_segments(sentence)
    stripped = sentence.strip()
    if stripped.endswith(("?", "\u061f")):
        return f'<prosody pitch="+8%">{rendered}</prosody>'
    if stripped.endswith("!"):
        return f'<prosody rate="fast" pitch="+10%">{rendered}</prosody>'
    return rendered


def text_to_ssml_body(text: str) -> str:
    """Convert normalized text into punctuation-aware SSML body markup."""

    parts: List[str] = []
    for paragraph in split_paragraphs(text):
        if is_heading_line(paragraph):
            parts.append(
                '<break time="1200ms"/>'
                f'<emphasis level="strong">{html.escape(paragraph)}</emphasis>'
                '<break time="600ms"/>'
            )
        else:
            parts.append(" ".join(sentence_to_ssml(sentence) for sentence in split_sentences(paragraph)))
            parts.append('<break time="900ms"/>')
    return "\n".join(parts)


def build_ssml(text: str, voice_name: str, language: str) -> str:
    """Wrap SSML body in Azure speak and voice tags."""

    locale = azure_locale(language)
    body = text_to_ssml_body(text)
    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{locale}">'
        f'<voice name="{html.escape(voice_name)}">'
        f"{body}"
        "</voice>"
        "</speak>"
    )


def estimate_cost(characters: int) -> float:
    """Estimate Azure Neural TTS cost from billable characters."""

    return (characters / 1000.0) * AZURE_PRICE_PER_1000_CHARS_USD


# ---------------------------------------------------------------------------
# Azure synthesis, audio stitching, and timestamp output
# ---------------------------------------------------------------------------


def append_json_log(path: Path, item: Dict[str, Any]) -> None:
    """Append an item to a JSON array log file."""

    existing: List[Dict[str, Any]] = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = []
    existing.append(item)
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


def synthesize_chunk(
    ssml: str,
    output_path: Path,
    speech_key: str,
    speech_region: str,
) -> SynthesisResult:
    """Synthesize one SSML chunk with Azure and collect word-boundary events."""

    import azure.cognitiveservices.speech as speechsdk

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio24Khz48KBitRateMonoMp3
    )
    audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_path))
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    boundaries: List[Dict[str, Any]] = []

    def on_word_boundary(event: Any) -> None:
        word = getattr(event, "text", "") or ""
        start_ms = int(getattr(event, "audio_offset", 0) / 10000)
        duration = int(getattr(event, "duration", 0) / 10000) if getattr(event, "duration", 0) else 0
        boundaries.append({"word": word, "start_ms": start_ms, "end_ms": start_ms + duration})

    synthesizer.synthesis_word_boundary.connect(on_word_boundary)
    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        details = speechsdk.SpeechSynthesisCancellationDetails.from_result(result)
        raise RuntimeError(f"Azure synthesis failed: {details.reason} {details.error_details}")

    duration_ms = probe_audio_duration_ms(output_path)
    if duration_ms <= 0 and boundaries:
        duration_ms = max(boundary["end_ms"] or boundary["start_ms"] for boundary in boundaries) + 500

    return SynthesisResult(path=output_path, word_boundaries=boundaries, duration_ms=duration_ms)


def synthesize_with_retries(
    ssml: str,
    output_path: Path,
    speech_key: str,
    speech_region: str,
) -> SynthesisResult:
    """Retry Azure synthesis with exponential backoff."""

    delays = [2, 4, 8]
    last_error: Optional[Exception] = None
    for attempt in range(1, len(delays) + 2):
        try:
            return synthesize_chunk(ssml, output_path, speech_key, speech_region)
        except Exception as exc:  # Azure SDK raises several concrete exception types.
            last_error = exc
            logging.warning("Azure synthesis attempt %s failed: %s", attempt, exc)
            if attempt <= len(delays):
                time.sleep(delays[attempt - 1])
    raise RuntimeError(f"Azure synthesis failed after retries: {last_error}")


def probe_audio_duration_ms(path: Path) -> int:
    """Read audio duration using ffprobe when available."""

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return int(float(result.stdout.strip()) * 1000)
    except Exception:
        return 0


def stitch_chunks(chunk_paths: List[Path], final_path: Path) -> None:
    """Use ffmpeg to stitch audio chunks into one 48kbps mono MP3 file."""

    final_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as handle:
        concat_path = Path(handle.name)
        for chunk in chunk_paths:
            safe_path = str(chunk.resolve()).replace("'", "'\\''")
            handle.write(f"file '{safe_path}'\n")

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_path),
                "-ac",
                "1",
                "-ar",
                "24000",
                "-b:a",
                "48k",
                str(final_path),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    finally:
        concat_path.unlink(missing_ok=True)


def offset_word_boundaries(boundaries: Iterable[Dict[str, Any]], offset_ms: int) -> List[Dict[str, Any]]:
    """Apply a chunk offset and repair missing end times."""

    adjusted: List[Dict[str, Any]] = []
    for item in boundaries:
        start = int(item["start_ms"]) + offset_ms
        end = int(item.get("end_ms") or 0) + offset_ms
        adjusted.append({"word": str(item.get("word") or ""), "start_ms": start, "end_ms": end})

    for index, item in enumerate(adjusted):
        if item["end_ms"] <= item["start_ms"]:
            next_start = adjusted[index + 1]["start_ms"] if index + 1 < len(adjusted) else item["start_ms"] + 350
            item["end_ms"] = max(item["start_ms"] + 80, min(next_start, item["start_ms"] + 700))
    return adjusted


def build_chapter_timestamps(chapters: List[Dict[str, Any]], word_boundaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Map chapter word indices to audio offsets."""

    if not word_boundaries:
        return [{"heading": chapter["heading"], "start_ms": 0} for chapter in chapters]
    output: List[Dict[str, Any]] = []
    for chapter in chapters:
        word_index = min(int(chapter.get("word_index", 0)), max(len(word_boundaries) - 1, 0))
        output.append({"heading": chapter["heading"], "start_ms": int(word_boundaries[word_index]["start_ms"])})
    return output


def format_vtt_time(milliseconds: int) -> str:
    """Format milliseconds as WebVTT HH:MM:SS.mmm."""

    milliseconds = max(0, int(milliseconds))
    hours, remainder = divmod(milliseconds, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02}.{millis:03}"


def write_timestamps(slug: str, output_dir: Path, word_boundaries: List[Dict[str, Any]], chapters: List[Dict[str, Any]]) -> None:
    """Write JSON timing, chapter index, and WebVTT one-word cue files."""

    (output_dir / f"{slug}_timestamps.json").write_text(
        json.dumps(word_boundaries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / f"{slug}_chapters.json").write_text(
        json.dumps(chapters, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = ["WEBVTT", ""]
    for index, item in enumerate(word_boundaries, start=1):
        word = str(item["word"]).replace("\n", " ").replace("-->", "->")
        lines.extend(
            [
                str(index),
                f"{format_vtt_time(item['start_ms'])} --> {format_vtt_time(item['end_ms'])}",
                word,
                "",
            ]
        )
    (output_dir / f"{slug}_highlight.vtt").write_text("\n".join(lines), encoding="utf-8")


def write_cost_log(output_dir: Path, rows: List[Dict[str, Any]]) -> None:
    """Persist per-book character usage and the current run total."""

    if not rows:
        return
    path = output_dir / "cost_log.csv"
    exists = path.exists()
    total_characters = sum(int(row["characters"]) for row in rows)
    total_cost = sum(float(row["estimated_cost_usd"]) for row in rows)
    fieldnames = ["run_id", "timestamp", "slug", "title", "language", "characters", "estimated_cost_usd", "status"]
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)
        writer.writerow(
            {
                "run_id": rows[0]["run_id"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "slug": "TOTAL",
                "title": "Current run total",
                "language": "",
                "characters": total_characters,
                "estimated_cost_usd": f"{total_cost:.6f}",
                "status": "total",
            }
        )


# ---------------------------------------------------------------------------
# Batch orchestration
# ---------------------------------------------------------------------------


def load_book_text(book: Dict[str, Any], slug: str, text_dir: Optional[Path]) -> BookText:
    """Load, scrape, clean, and chapter-index a book."""

    raw_text = read_pre_scraped_text(text_dir, slug)
    if raw_text is None:
        try:
            raw_text = scrape_source_text(str(book.get("source_url") or ""))
        except Exception as exc:
            raise ScrapeFailure(str(exc)) from exc
    clean_text = normalize_text(raw_text)
    if word_count(clean_text) < 50:
        raise ValueError("Cleaned text is too short for audio generation")
    return BookText(text=clean_text, chapters=detect_chapters(clean_text))


def print_dry_run(slug: str, title: str, language: str, voice: str, chunks: List[str]) -> None:
    """Print SSML samples and cost estimate without calling Azure."""

    characters = sum(len(chunk) for chunk in chunks)
    print("\n" + "=" * 80)
    print(f"DRY RUN: {title} ({slug})")
    print(f"Language: {language} | Voice: {voice}")
    print(f"Chunks: {len(chunks)} | Characters: {characters} | Estimated cost: ${estimate_cost(characters):.4f}")
    print("-" * 80)
    for index, chunk in enumerate(chunks[:2], start=1):
        print(f"SSML chunk {index} preview:")
        print(build_ssml(chunk[:1500], voice, language))
        print("-" * 80)
    if len(chunks) > 2:
        print(f"... {len(chunks) - 2} additional chunk(s) omitted from dry-run preview.")


def generate_for_book(
    book: Dict[str, Any],
    output_dir: Path,
    text_dir: Optional[Path],
    voices: Dict[str, Dict[str, str]],
    dry_run: bool,
    speech_key: Optional[str],
    speech_region: Optional[str],
    run_id: str,
) -> Optional[Dict[str, Any]]:
    """Generate all audio assets for one book and return a cost-log row."""

    slug = slug_for_book(book)
    title = str(book.get("title") or slug)
    final_mp3 = output_dir / f"{slug}.mp3"

    book_text = load_book_text(book, slug, text_dir)
    language = detect_language(book, book_text.text)
    voice = voices[language]["primary"]
    chunks = chunk_text(book_text.text)
    characters = sum(len(chunk) for chunk in chunks)

    if dry_run:
        print_dry_run(slug, title, language, voice, chunks)
        return {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "slug": slug,
            "title": title,
            "language": language,
            "characters": characters,
            "estimated_cost_usd": f"{estimate_cost(characters):.6f}",
            "status": "dry-run",
        }

    if final_mp3.exists():
        logging.info("Skipping %s because %s already exists.", slug, final_mp3)
        return {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "slug": slug,
            "title": title,
            "language": language,
            "characters": 0,
            "estimated_cost_usd": "0.000000",
            "status": "skipped-existing",
        }

    if not speech_key or not speech_region:
        raise RuntimeError("AZURE_SPEECH_KEY and AZURE_SPEECH_REGION are required unless --dry-run is used.")

    chunk_dir = output_dir / "_chunks" / slug
    chunk_dir.mkdir(parents=True, exist_ok=True)
    chunk_paths: List[Path] = []
    all_boundaries: List[Dict[str, Any]] = []
    offset_ms = 0
    active_voice = voice

    for index, chunk in enumerate(chunks, start=1):
        chunk_path = chunk_dir / f"{index:04}.mp3"
        ssml = build_ssml(chunk, active_voice, language)
        try:
            result = synthesize_with_retries(ssml, chunk_path, speech_key, speech_region)
        except Exception as primary_error:
            fallback_voice = voices[language]["fallback"]
            append_json_log(
                output_dir / "error_log.json",
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "slug": slug,
                    "chunk": index,
                    "event": "voice_fallback",
                    "primary_voice": active_voice,
                    "fallback_voice": fallback_voice,
                    "error": str(primary_error),
                },
            )
            active_voice = fallback_voice
            result = synthesize_with_retries(build_ssml(chunk, active_voice, language), chunk_path, speech_key, speech_region)

        chunk_paths.append(result.path)
        all_boundaries.extend(offset_word_boundaries(result.word_boundaries, offset_ms))
        offset_ms += result.duration_ms
        logging.info("Synthesized %s chunk %s/%s using %s", slug, index, len(chunks), active_voice)

    stitch_chunks(chunk_paths, final_mp3)
    chapter_timestamps = build_chapter_timestamps(book_text.chapters, all_boundaries)
    write_timestamps(slug, output_dir, all_boundaries, chapter_timestamps)

    return {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "slug": slug,
        "title": title,
        "language": language,
        "characters": characters,
        "estimated_cost_usd": f"{estimate_cost(characters):.6f}",
        "status": "generated",
    }


def main() -> int:
    """Run a resilient batch generation job."""

    args = parse_args()
    output_dir = Path(args.output_dir)
    setup_logging(output_dir)

    manifest_path = Path(args.manifest)
    text_dir = Path(args.text_dir) if args.text_dir else None
    voices = load_voices(Path(args.voices))
    books = load_manifest(manifest_path)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if args.slug:
        books = [book for book in books if slug_for_book(book) == normalize_slug(args.slug)]
        if not books:
            logging.error("No manifest book matched slug: %s", args.slug)
            return 2

    speech_key = os.environ.get("AZURE_SPEECH_KEY")
    speech_region = os.environ.get("AZURE_SPEECH_REGION")

    if not args.dry_run and (not speech_key or not speech_region):
        logging.error("AZURE_SPEECH_KEY and AZURE_SPEECH_REGION must be set for synthesis.")
        return 2

    cost_rows: List[Dict[str, Any]] = []
    failures = 0

    for book in books:
        slug = slug_for_book(book)
        try:
            row = generate_for_book(
                book=book,
                output_dir=output_dir,
                text_dir=text_dir,
                voices=voices,
                dry_run=args.dry_run,
                speech_key=speech_key,
                speech_region=speech_region,
                run_id=run_id,
            )
            if row:
                cost_rows.append(row)
        except Exception as exc:
            failures += 1
            logging.error("Book failed: %s (%s)", slug, exc)
            log_name = "scrape_failures.json" if isinstance(exc, ScrapeFailure) else "error_log.json"
            append_json_log(
                output_dir / log_name,
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "slug": slug,
                    "title": book.get("title"),
                    "error": str(exc),
                },
            )

    write_cost_log(output_dir, cost_rows)
    logging.info("Completed. Books attempted: %s, failures: %s, output: %s", len(books), failures, output_dir)
    return 1 if failures and not cost_rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
