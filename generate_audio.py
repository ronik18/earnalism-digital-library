#!/usr/bin/env python3
"""Generate Earnalism audiobook assets with Sarvam AI and Google Cloud TTS.

The pipeline is designed for repeatable, audit-friendly production runs:
manifest in, cached source text, provider-specific synthesis, normalized audio,
word-level highlight timestamps, chapter indexes, cost logs, and per-book
metadata out. Bengali uses Sarvam AI first because its pacing controls are
well-suited to Indian-language narration; English uses Google Cloud TTS first
because SSML marks provide deterministic word timing for the reader.
"""

from __future__ import annotations

import argparse
import base64
import csv
import html
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import unquote, urlparse

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is declared, this keeps --help usable.
    def load_dotenv() -> bool:
        return False


SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_COST_PER_1K_CHARS = 0.000
GOOGLE_NEURAL2_COST_PER_1K = 0.016
GOOGLE_WAVENET_COST_PER_1K = 0.008

MAX_SARVAM_CHARS = 500
MAX_SARVAM_INPUTS_PER_CALL = 3
MAX_GOOGLE_SSML_CHARS = 4800
REQUEST_TIMEOUT_SECONDS = 45
RETRY_DELAYS_SECONDS = (2, 4, 8)
DEFAULT_OUTPUT_DIR = "./audio_output"
DEFAULT_VOICES_PATH = "voices.json"


@dataclass
class AudioChunk:
    """One normalized audio segment plus timing data relative to the full book."""

    path: Path
    duration_ms: int
    timestamps: List[Dict[str, Any]]


@dataclass
class BookResult:
    """Final generation summary used to write metadata and console output."""

    slug: str
    title: str
    author: str
    language: str
    provider_used: str
    voice: str
    fallback_used: bool
    fallback_reason: Optional[str]
    duration_ms: int
    total_words: int
    highlight_available: bool
    chapter_count: int
    characters_billed: int
    estimated_cost_usd: float
    pace: Optional[float] = None
    skipped: bool = False
    skip_reason: Optional[str] = None


def parse_args() -> argparse.Namespace:
    """Parse the production CLI contract used by the audio team."""

    parser = argparse.ArgumentParser(description="Generate Earnalism audiobook files.")
    parser.add_argument("--manifest", required=True, help="Path to book_import_manifest.json")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--text-dir", default=None, help="Optional cache of {slug}.txt files")
    parser.add_argument("--slug", default=None, help="Process a single book by slug")
    parser.add_argument("--dry-run", action="store_true", help="Estimate cost and preview markup only")
    parser.add_argument(
        "--voice-tier",
        choices=("neural2", "wavenet"),
        default="neural2",
        help="Google voice tier for primary/fallback Google calls",
    )
    parser.add_argument("--lang", choices=("ben", "en"), default=None, help="Process one language only")
    parser.add_argument("--voices", default=DEFAULT_VOICES_PATH, help="Path to voices.json")
    return parser.parse_args()


def utc_now() -> str:
    """Return an ISO timestamp that is stable for logs and metadata."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def setup_logging(output_dir: Path) -> None:
    """Log to stdout and a persistent file without ever printing credentials."""

    output_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(output_dir / "generate_audio.log", encoding="utf-8"),
        ],
    )


def append_json_line(path: Path, payload: Dict[str, Any]) -> None:
    """Append JSON lines to the error log so a failed book never blocks the batch."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def log_error(
    error_log: Path,
    slug: str,
    provider: str,
    error_type: str,
    message: str,
    action_taken: str,
) -> None:
    """Write a structured, non-secret error record."""

    append_json_line(
        error_log,
        {
            "slug": slug,
            "provider": provider,
            "error_type": error_type,
            "error_message": message,
            "timestamp": utc_now(),
            "action_taken": action_taken,
        },
    )


def load_manifest(path: Path) -> List[Dict[str, Any]]:
    """Load either a raw JSON array or an object with a top-level books array."""

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("books"), list):
        return data["books"]
    raise ValueError("Manifest must be a JSON array or an object with a 'books' array.")


def load_voices(path: Path) -> Dict[str, Any]:
    """Load provider and voice choices; all voice tuning lives outside the script."""

    with path.open("r", encoding="utf-8") as handle:
        voices = json.load(handle)
    for lang in ("ben", "en"):
        if lang not in voices:
            raise ValueError(f"voices.json is missing '{lang}'")
    if "sarvam" not in voices["ben"] or "google" not in voices["ben"]:
        raise ValueError("voices.json must configure Bengali Sarvam and Google voices.")
    if "google" not in voices["en"]:
        raise ValueError("voices.json must configure English Google voices.")
    return voices


def normalize_slug(value: str) -> str:
    """Create a filesystem-safe slug while preserving Bengali characters."""

    value = unquote(value or "").strip().lower()
    value = re.sub(r"\.[a-z0-9]{1,8}$", "", value)
    value = value.replace("_", "-")
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^\w\-\u0980-\u09ff]+", "", value, flags=re.UNICODE)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "book"


def first_url(value: str) -> str:
    """Support plain URLs and markdown links from manifest notes."""

    markdown = re.search(r"\[[^\]]*\]\((https?://[^)]+)\)", value or "")
    if markdown:
        return markdown.group(1).strip()
    direct = re.search(r"https?://[^\s)]+", value or "")
    return direct.group(0).strip() if direct else (value or "").strip()


def slug_for_book(book: Dict[str, Any]) -> str:
    """Resolve the asset slug used for cache and audio filenames."""

    explicit = book.get("audio_slug") or book.get("slug")
    if explicit:
        return normalize_slug(str(explicit))

    title = str(book.get("title") or "").strip()
    if title:
        return normalize_slug(title)

    source_url = first_url(str(book.get("source_url") or ""))
    parsed = urlparse(source_url)
    if parsed.path:
        path_name = Path(unquote(parsed.path.rstrip("/"))).name
        if path_name:
            return normalize_slug(path_name)

    return "book"


def detect_language(book: Dict[str, Any], text: str = "") -> str:
    """Return the manifest language, falling back to Bengali Unicode detection."""

    language = str(book.get("language") or "").strip().lower()
    if language in {"ben", "bn", "bn-in", "bengali"}:
        return "ben"
    if language in {"en", "eng", "english", "en-in"}:
        return "en"

    source_type = str(book.get("source_type") or "").lower()
    sample = f"{book.get('title', '')} {book.get('author', '')} {source_type} {text[:1200]}"
    return "ben" if re.search(r"[\u0980-\u09ff]", sample) else "en"


def google_lang_code(language: str) -> str:
    """Map Earnalism language codes to Google locale codes."""

    return "bn-IN" if language == "ben" else "en-IN"


def validate_environment(dry_run: bool) -> None:
    """Validate runtime credentials only when a real API call can happen.

    Dry runs intentionally work without credentials so editors can estimate
    cost and preview markup before the platform owner provisions API access.
    """

    load_dotenv()
    if dry_run:
        return

    missing: List[str] = []
    for name in ("SARVAM_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT"):
        if not os.environ.get(name):
            missing.append(name)

    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path:
        resolved = Path(credentials_path).expanduser().resolve()
        if not resolved.exists():
            missing.append("GOOGLE_APPLICATION_CREDENTIALS file not found")
        else:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(resolved)

    if missing:
        print("Audio generation credentials are missing or invalid:", file=sys.stderr)
        for item in missing:
            print(f"  - {item}", file=sys.stderr)
        print("\nSet them in your shell or a local .env file, for example:", file=sys.stderr)
        print('  export SARVAM_API_KEY="..."', file=sys.stderr)
        print('  export GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/gcp_key.json"', file=sys.stderr)
        print('  export GOOGLE_CLOUD_PROJECT="earnalism-tts"', file=sys.stderr)
        sys.exit(1)


def env_truthy(name: str, default: bool = False) -> bool:
    """Read simple feature flags without exposing environment values."""

    value = os.environ.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def ensure_ffmpeg_available() -> None:
    """Fail early if audio normalization/stitching tools are not installed."""

    missing = [cmd for cmd in ("ffmpeg", "ffprobe") if not shutil.which(cmd)]
    if missing:
        raise RuntimeError(f"Missing system dependency: {', '.join(missing)}. Install ffmpeg >= 6.0.")


def clean_scraped_text(text: str) -> str:
    """Normalize source text while preserving Bengali Unicode and punctuation."""

    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\[\s*\d+\s*\]", "", text)
    text = re.sub(r"\[\s*edit\s*\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def scrape_source_text(source_url: str, slug: str, scrape_failures: Path) -> str:
    """Scrape paragraph text only and strip wiki chrome/citation furniture."""

    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError("Install requests and beautifulsoup4 before scraping.") from exc

    url = first_url(source_url)
    if not url:
        raise ValueError("source_url is missing")

    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": "EarnalismAudioGenerator/2.0 (+https://theearnalism.com)"},
        )
        response.raise_for_status()
    except Exception as exc:
        append_json_line(
            scrape_failures,
            {"slug": slug, "source_url": url, "error": str(exc), "timestamp": utc_now()},
        )
        raise

    soup = BeautifulSoup(response.text, "lxml")
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
        ".references",
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
        ".catlinks",
        ".mw-jump-link",
    ]:
        for node in soup.select(selector):
            node.decompose()

    container = (
        soup.select_one("#mw-content-text .mw-parser-output")
        or soup.select_one("main")
        or soup.select_one("article")
        or soup.body
    )
    if not container:
        raise ValueError("Could not locate readable page content")

    paragraphs: List[str] = []
    for paragraph in container.find_all("p"):
        text = paragraph.get_text(" ", strip=True)
        text = clean_scraped_text(text)
        if text:
            paragraphs.append(text)

    if not paragraphs:
        raise ValueError("No paragraph text found in source")

    return clean_scraped_text("\n\n".join(paragraphs))


def load_or_scrape_text(
    book: Dict[str, Any],
    slug: str,
    text_dir: Path,
    scrape_failures: Path,
) -> str:
    """Use cached source text when present, otherwise scrape and cache it once."""

    text_dir.mkdir(parents=True, exist_ok=True)
    text_path = text_dir / f"{slug}.txt"
    if text_path.exists():
        logging.info("Using cached text for %s: %s", slug, text_path)
        return clean_scraped_text(text_path.read_text(encoding="utf-8-sig"))

    text = scrape_source_text(str(book.get("source_url") or ""), slug, scrape_failures)
    text_path.write_text(text, encoding="utf-8")
    logging.info("Cached scraped text for %s: %s", slug, text_path)
    return text


def split_sentences(text: str) -> List[str]:
    """Split at sentence-ending punctuation while keeping punctuation attached."""

    text = text.strip()
    if not text:
        return []
    parts = re.split(r"(?<=[।॥.!?])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def split_long_sentence(text: str, limit: int) -> List[str]:
    """Last-resort split for unusually long sentences, cutting at whitespace only."""

    words = text.split()
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0
    for word in words:
        extra = len(word) + (1 if current else 0)
        if current and current_len + extra > limit:
            chunks.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += extra
    if current:
        chunks.append(" ".join(current))
    return chunks


def chunk_plain_text(text: str, limit: int) -> List[str]:
    """Chunk text without cutting mid-sentence unless a sentence itself is too long."""

    chunks: List[str] = []
    current = ""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    for paragraph in paragraphs:
        candidates = [paragraph]
        if len(paragraph) > limit:
            candidates = []
            for sentence in split_sentences(paragraph):
                if len(sentence) <= limit:
                    candidates.append(sentence)
                else:
                    candidates.extend(split_long_sentence(sentence, limit))

        for candidate in candidates:
            separator = "\n\n" if current else ""
            if current and len(current) + len(separator) + len(candidate) > limit:
                chunks.append(current.strip())
                current = candidate
            else:
                current = f"{current}{separator}{candidate}" if current else candidate

    if current.strip():
        chunks.append(current.strip())
    return chunks


def preprocess_sarvam_text(text: str) -> str:
    """Encode Bengali pacing using text spacing because Sarvam does not accept SSML."""

    text = clean_scraped_text(text)
    text = text.replace("॥", "॥   ")
    text = text.replace("।", "।  ")
    text = text.replace("—", " — ")
    text = text.replace("…", "...  ")
    text = re.sub(r"\.{3}", "...  ", text)
    text = re.sub(r"[ \t]{4,}", "   ", text)
    return text


def escape_text(value: str) -> str:
    """Escape text for SSML while preserving quotes for dialogue wrapping."""

    return html.escape(value, quote=True)


def wrap_dialogue(escaped: str, rate: str, pitch: str, break_ms: int) -> str:
    """Give quoted speech a gentler cadence without changing the words."""

    pattern = re.compile(r"(&quot;.*?&quot;|&#x27;.*?&#x27;)")
    return pattern.sub(
        rf'<prosody rate="{rate}" pitch="{pitch}">\1</prosody><break time="{break_ms}ms"/>',
        escaped,
    )


def apply_google_sentence_markup(sentence: str, language: str) -> str:
    """Apply punctuation-aware SSML to one escaped sentence."""

    sentence = sentence.strip()
    if not sentence:
        return ""

    escaped = escape_text(sentence)
    if language == "ben":
        escaped = wrap_dialogue(escaped, "-5%", "+4%", 200)
        if sentence.endswith("?"):
            return f'<prosody pitch="+6%" rate="-5%">{escaped}</prosody><break time="550ms"/>'
        if sentence.endswith("!"):
            return f'<prosody pitch="+4%" rate="+3%">{escaped}</prosody><break time="500ms"/>'
        escaped = escaped.replace("॥", '॥<break time="950ms"/>')
        escaped = escaped.replace("।", '।<break time="650ms"/>')
        escaped = escaped.replace("...", '<break time="750ms"/>')
        escaped = escaped.replace("…", '<break time="750ms"/>')
        escaped = escaped.replace("—", '<break time="400ms"/>')
        escaped = escaped.replace(",", ',<break time="180ms"/>')
        escaped = escaped.replace(";", ';<break time="280ms"/>')
        escaped = escaped.replace(":", ':<break time="300ms"/>')
        return escaped

    escaped = wrap_dialogue(escaped, "-4%", "+5%", 180)
    if sentence.endswith("?"):
        return f'<prosody pitch="+7%" rate="-4%">{escaped}</prosody><break time="520ms"/>'
    if sentence.endswith("!"):
        return f'<prosody pitch="+5%" rate="+4%">{escaped}</prosody><break time="480ms"/>'
    escaped = re.sub(r"\.(?=\s|$)", '.<break time="580ms"/>', escaped)
    escaped = escaped.replace("...", '<break time="700ms"/>')
    escaped = escaped.replace("…", '<break time="700ms"/>')
    escaped = escaped.replace("—", '<break time="380ms"/>')
    escaped = escaped.replace(",", ',<break time="160ms"/>')
    escaped = escaped.replace(";", ';<break time="260ms"/>')
    escaped = escaped.replace(":", ':<break time="280ms"/>')
    return escaped


def build_google_body(text: str, language: str) -> str:
    """Build the inner SSML body before adding word marks and the root wrapper."""

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    rendered: List[str] = []
    for paragraph in paragraphs:
        sentences = split_sentences(paragraph) or [paragraph]
        marked = " ".join(apply_google_sentence_markup(sentence, language) for sentence in sentences)
        rendered.append(marked)
    paragraph_break = '<break time="950ms"/>' if language == "ben" else '<break time="880ms"/>'
    return paragraph_break.join(rendered)


def wrap_google_ssml(body: str, voice_name: str, language: str, voices: Dict[str, Any]) -> str:
    """Wrap marked content in the Google SSML template required by the reader pipeline."""

    google_config = voices[language]["google"]
    rate = google_config.get("rate", "-12%" if language == "ben" else "-8%")
    pitch = google_config.get("pitch", "-2%" if language == "ben" else "-1%")
    lang_code = google_lang_code(language)
    return (
        "<speak>"
        f'<voice name="{voice_name}" language="{lang_code}">'
        f'<prosody rate="{rate}" pitch="{pitch}">'
        f"{body}"
        "</prosody>"
        "</voice>"
        "</speak>"
    )


def visible_word(token: str) -> str:
    """Convert an SSML text token into the word stored in timestamp JSON."""

    token = html.unescape(token)
    token = token.strip()
    token = re.sub(r"^[\s\"'“”‘’.,;:!?।॥()\[\]{}<>]+", "", token)
    token = re.sub(r"[\s\"'“”‘’.,;:!?।॥()\[\]{}<>]+$", "", token)
    return token


def insert_word_marks(ssml_content: str) -> Tuple[str, List[str]]:
    """Insert SSML marks before text tokens while leaving tags untouched.

    Google timepoints fire on <mark> tags, not words. The splitter alternates
    between tags and text nodes so marks are never injected inside a tag
    attribute, which would corrupt the SSML.
    """

    parts = re.split(r"(<[^>]+>)", ssml_content)
    marked_parts: List[str] = []
    words: List[str] = []

    for part in parts:
        if not part:
            continue
        if part.startswith("<") and part.endswith(">"):
            marked_parts.append(part)
            continue

        tokens = re.split(r"(\s+)", part)
        for token in tokens:
            if not token:
                continue
            if token.isspace():
                marked_parts.append(token)
                continue
            word = visible_word(token)
            if word:
                marked_parts.append(f'<mark name="w_{len(words)}"/>')
                words.append(word)
            marked_parts.append(token)

    return "".join(marked_parts), words


def google_body_chunks(text: str, language: str, voices: Dict[str, Any], voice_name: str) -> List[Tuple[str, str, List[str]]]:
    """Chunk Google markup below API limits and return raw text, body markup, and words."""

    chunks: List[Tuple[str, str, List[str]]] = []
    plain_chunks = chunk_plain_text(text, MAX_GOOGLE_SSML_CHARS // 2)

    for raw_chunk in plain_chunks:
        body = build_google_body(raw_chunk, language)
        marked_body, words = insert_word_marks(body)
        ssml = wrap_google_ssml(marked_body, voice_name, language, voices)

        if len(ssml) <= MAX_GOOGLE_SSML_CHARS:
            chunks.append((raw_chunk, marked_body, words))
            continue

        # Long paragraphs in classic books can exceed the SSML limit. We split
        # by sentence instead of cutting arbitrary characters so punctuation
        # timing and word alignment remain understandable.
        for sentence_chunk in chunk_plain_text(raw_chunk, MAX_GOOGLE_SSML_CHARS // 3):
            body = build_google_body(sentence_chunk, language)
            marked_body, words = insert_word_marks(body)
            chunks.append((sentence_chunk, marked_body, words))

    return chunks


def run_command(command: Sequence[str], cwd: Optional[Path] = None) -> None:
    """Run ffmpeg/ffprobe commands with concise errors."""

    process = subprocess.run(
        list(command),
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if process.returncode != 0:
        raise RuntimeError(process.stderr.strip() or "Command failed")


def normalize_to_wav(source: Path, destination: Path) -> None:
    """Normalize every provider output before measuring/stitching.

    Provider files can have different sample rates and containers. A single
    22050Hz mono WAV intermediate makes ffmpeg concat deterministic and keeps
    word timestamp offsets from drifting across chunks.
    """

    run_command(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-ar",
            "22050",
            "-ac",
            "1",
            str(destination),
        ]
    )


def duration_ms(path: Path) -> int:
    """Measure audio duration using pydub, falling back to ffprobe."""

    try:
        from pydub import AudioSegment

        return int(len(AudioSegment.from_file(path)))
    except Exception:
        process = subprocess.run(
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
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if process.returncode != 0:
            raise RuntimeError(process.stderr.strip())
        return int(float(process.stdout.strip()) * 1000)


def concat_and_encode(chunks: List[AudioChunk], output_path: Path, temp_dir: Path) -> int:
    """Stitch normalized chunks and encode the final 48kbps mono MP3."""

    if not chunks:
        raise RuntimeError("No audio chunks were produced")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    concat_path = temp_dir / f"concat_{output_path.stem}.txt"
    with concat_path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            escaped = str(chunk.path.resolve()).replace("'", "'\\''")
            handle.write(f"file '{escaped}'\n")

    run_command(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-c:a",
            "libmp3lame",
            "-b:a",
            "48k",
            "-ac",
            "1",
            str(output_path),
        ]
    )
    return duration_ms(output_path)


def sarvam_chunks(text: str) -> List[str]:
    """Create Sarvam-ready chunks below the provider's 500 character limit."""

    preprocessed = preprocess_sarvam_text(text)
    chunks = chunk_plain_text(preprocessed, MAX_SARVAM_CHARS)
    return [chunk for chunk in chunks if chunk.strip()]


def sarvam_payload(chunks: List[str], voices: Dict[str, Any]) -> Dict[str, Any]:
    """Build the Sarvam request from voices.json, not hardcoded voice tuning."""

    config = voices["ben"]["sarvam"]
    return {
        "inputs": chunks,
        "target_language_code": config.get("target_language_code", "bn-IN"),
        "speaker": config["speaker"],
        "pace": config["pace"],
        "pitch": config["pitch"],
        "loudness": config["loudness"],
        "speech_sample_rate": config["speech_sample_rate"],
        "enable_preprocessing": config["enable_preprocessing"],
        "model": config["model"],
    }


def decode_sarvam_audios(response_json: Dict[str, Any]) -> List[bytes]:
    """Decode Sarvam's base64 audio array with tolerance for minor response variants."""

    audios = response_json.get("audios")
    if audios is None and "audio" in response_json:
        audios = response_json["audio"]
    if isinstance(audios, str):
        audios = [audios]
    if not isinstance(audios, list):
        raise RuntimeError("Sarvam response did not contain an audios array")

    decoded: List[bytes] = []
    for item in audios:
        if not isinstance(item, str):
            raise RuntimeError("Sarvam audio item was not base64 text")
        encoded = item.split(",", 1)[1] if "," in item and "base64" in item[:40] else item
        decoded.append(base64.b64decode(encoded))
    return decoded


def request_sarvam_batch(slug: str, batch: List[str], voices: Dict[str, Any]) -> List[bytes]:
    """Call Sarvam with retries; caller handles provider fallback."""

    import requests

    payload = sarvam_payload(batch, voices)
    headers = {
        "api-subscription-key": os.environ["SARVAM_API_KEY"],
        "Content-Type": "application/json",
    }

    last_error: Optional[Exception] = None
    for attempt, delay in enumerate((0, *RETRY_DELAYS_SECONDS), start=1):
        if delay:
            time.sleep(delay)
        try:
            response = requests.post(
                SARVAM_TTS_URL,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if not response.ok:
                detail = response.text[:800]
                raise RuntimeError(f"HTTP {response.status_code}: {detail}")
            audios = decode_sarvam_audios(response.json())
            if len(audios) != len(batch):
                raise RuntimeError(f"Sarvam returned {len(audios)} audios for {len(batch)} chunks")
            return audios
        except Exception as exc:
            last_error = exc
            logging.warning("Sarvam attempt %s failed for %s: %s", attempt, slug, exc)

    raise RuntimeError(str(last_error) if last_error else "Sarvam request failed")


_STABLE_MODEL: Any = None


def stable_whisper_model() -> Any:
    """Load Whisper once; model reuse avoids paying startup cost per chunk."""

    global _STABLE_MODEL
    if _STABLE_MODEL is None:
        import stable_whisper

        _STABLE_MODEL = stable_whisper.load_model("base")
    return _STABLE_MODEL


def sarvam_word_timestamps(wav_path: Path, text_chunk: str, offset_ms: int) -> List[Dict[str, Any]]:
    """Align Sarvam audio to source text because Sarvam does not return word times."""

    model = stable_whisper_model()
    result = model.align(str(wav_path), text_chunk, language="bn")
    words: List[Dict[str, Any]] = []
    for word in result.all_words_or_segments():
        token = getattr(word, "word", "").strip()
        if not token:
            continue
        words.append(
            {
                "word": token,
                "start_ms": int(float(word.start) * 1000) + offset_ms,
                "end_ms": int(float(word.end) * 1000) + offset_ms,
            }
        )
    return words


def synthetic_word_timestamps(text_chunk: str, offset_ms: int, chunk_duration_ms: int, language: str) -> List[Dict[str, Any]]:
    """Create deterministic fallback timings when forced alignment is incomplete.

    Sarvam does not return word boundaries. Bengali forced alignment can miss
    the tail of a chunk, especially with literary punctuation. A proportional
    fallback is less exact than alignment, but it keeps highlighting monotonic
    and prevents the reader from freezing several words at one timestamp.
    """

    tokens = tokenize_words(text_chunk, language)
    if not tokens or chunk_duration_ms <= 0:
        return []
    weights = [max(1, len(token)) for token in tokens]
    total = sum(weights)
    cursor = 0
    timestamps: List[Dict[str, Any]] = []
    for index, (token, weight) in enumerate(zip(tokens, weights)):
        start_ms = offset_ms + int((cursor / total) * chunk_duration_ms)
        cursor += weight
        end_ms = offset_ms + int((cursor / total) * chunk_duration_ms)
        if index == len(tokens) - 1:
            end_ms = offset_ms + chunk_duration_ms
        if end_ms <= start_ms:
            end_ms = start_ms + 1
        timestamps.append({"word": token, "start_ms": start_ms, "end_ms": end_ms})
    return normalize_word_timestamps(timestamps)


def normalize_word_timestamps(timestamps: List[Dict[str, Any]], min_duration_ms: int = 1) -> List[Dict[str, Any]]:
    """Clamp word timings so reader highlights are strictly ordered."""

    normalized: List[Dict[str, Any]] = []
    previous_end = 0
    for item in timestamps:
        start_ms = max(previous_end, int(item.get("start_ms", 0)))
        end_ms = max(start_ms + min_duration_ms, int(item.get("end_ms", start_ms)))
        normalized.append(
            {
                **item,
                "start_ms": start_ms,
                "end_ms": end_ms,
            }
        )
        previous_end = end_ms
    return normalized


def alignment_is_usable(timestamps: List[Dict[str, Any]], text_chunk: str, offset_ms: int, chunk_duration_ms: int) -> bool:
    """Reject partial alignments before they become visible reader glitches."""

    expected = len(tokenize_words(text_chunk, "ben"))
    if expected == 0:
        return not timestamps
    if len(timestamps) < max(1, int(expected * 0.9)):
        return False
    previous_start = offset_ms
    zero_or_tiny = 0
    for item in timestamps:
        start_ms = int(item.get("start_ms", 0))
        end_ms = int(item.get("end_ms", 0))
        if start_ms + 25 < previous_start or end_ms < start_ms:
            return False
        if end_ms - start_ms <= 20:
            zero_or_tiny += 1
        previous_start = max(previous_start, start_ms)
    if zero_or_tiny > max(3, int(expected * 0.05)):
        return False
    if timestamps and int(timestamps[-1].get("end_ms", 0)) < offset_ms + int(chunk_duration_ms * 0.75):
        return False
    return True


def google_voice_name(voices: Dict[str, Any], language: str, tier: str, fallback: bool = False) -> str:
    """Resolve a Google voice from voices.json."""

    voice_set = voices[language]["google"][tier]
    return voice_set["fallback" if fallback else "primary"]


_GOOGLE_VOICE_CACHE: Dict[str, set] = {}


def available_google_voice_names(language: str) -> set:
    """List valid Google voices once so stale config does not waste retries.

    Google exposes different voice families by language. Bengali currently has
    Wavenet/Standard/Chirp voices but no Neural2 voices, so validating the
    configured names before synthesis prevents slow 400 retry loops.
    """

    lang_code = google_lang_code(language)
    if lang_code not in _GOOGLE_VOICE_CACHE:
        from google.cloud import texttospeech_v1beta1 as tts

        client = tts.TextToSpeechClient()
        _GOOGLE_VOICE_CACHE[lang_code] = {voice.name for voice in client.list_voices(language_code=lang_code).voices}
    return _GOOGLE_VOICE_CACHE[lang_code]


def synthesize_google_chunk(
    ssml: str,
    voice_name: str,
    language: str,
    word_list: List[str],
    offset_ms: int,
) -> Tuple[bytes, List[Dict[str, Any]]]:
    """Synthesize one Google chunk and map SSML mark timepoints to words."""

    from google.cloud import texttospeech_v1beta1 as tts

    client = tts.TextToSpeechClient()
    request = tts.SynthesizeSpeechRequest(
        input=tts.SynthesisInput(ssml=ssml),
        voice=tts.VoiceSelectionParams(language_code=google_lang_code(language), name=voice_name),
        audio_config=tts.AudioConfig(audio_encoding=tts.AudioEncoding.MP3),
        enable_time_pointing=[tts.SynthesizeSpeechRequest.TimepointType.SSML_MARK],
    )
    response = client.synthesize_speech(request=request)

    timestamps: List[Dict[str, Any]] = []
    timepoints = list(response.timepoints)
    for index, timepoint in enumerate(timepoints):
        match = re.search(r"w_(\d+)$", timepoint.mark_name or "")
        if not match:
            continue
        word_index = int(match.group(1))
        if word_index >= len(word_list):
            continue
        start_ms = int(float(timepoint.time_seconds) * 1000) + offset_ms
        if index + 1 < len(timepoints):
            end_ms = int(float(timepoints[index + 1].time_seconds) * 1000) + offset_ms
        else:
            end_ms = start_ms + 400
        timestamps.append({"word": word_list[word_index], "start_ms": start_ms, "end_ms": end_ms})

    return response.audio_content, timestamps


def synthesize_google_chunk_with_retry(
    slug: str,
    marked_body: str,
    language: str,
    word_list: List[str],
    offset_ms: int,
    voices: Dict[str, Any],
    tier: str,
    error_log: Path,
) -> Tuple[bytes, List[Dict[str, Any]], str, bool, Optional[str]]:
    """Try Google primary/fallback voices and WaveNet fallback when Neural2 fails."""

    attempts: List[Tuple[str, str, Optional[str]]] = [
        (tier, google_voice_name(voices, language, tier, False), None),
        (tier, google_voice_name(voices, language, tier, True), "primary voice failed"),
    ]
    if tier == "neural2":
        attempts.extend(
            [
                ("wavenet", google_voice_name(voices, language, "wavenet", False), "Neural2 tier failed"),
                ("wavenet", google_voice_name(voices, language, "wavenet", True), "Neural2 and WaveNet primary failed"),
            ]
        )

    last_error: Optional[Exception] = None
    try:
        valid_voices = available_google_voice_names(language)
    except Exception as exc:
        valid_voices = set()
        log_error(
            error_log,
            slug,
            "google",
            "VoiceDiscoveryError",
            str(exc),
            "could not pre-validate voices; proceeding with configured attempts",
        )

    for attempt_tier, voice_name, fallback_reason in attempts:
        if valid_voices and voice_name not in valid_voices:
            last_error = RuntimeError(f"Configured voice does not exist: {voice_name}")
            log_error(
                error_log,
                slug,
                "google",
                "InvalidVoice",
                str(last_error),
                f"skipped invalid configured voice {voice_name}",
            )
            continue
        for retry_index, delay in enumerate((0, *RETRY_DELAYS_SECONDS), start=1):
            if delay:
                time.sleep(delay)
            try:
                ssml = wrap_google_ssml(marked_body, voice_name, language, voices)
                audio, timestamps = synthesize_google_chunk(ssml, voice_name, language, word_list, offset_ms)
                return audio, timestamps, voice_name, bool(fallback_reason), fallback_reason
            except Exception as exc:
                last_error = exc
                logging.warning(
                    "Google %s attempt %s failed for %s voice %s: %s",
                    attempt_tier,
                    retry_index,
                    slug,
                    voice_name,
                    exc,
                )
        log_error(
            error_log,
            slug,
            "google",
            "APIError",
            str(last_error),
            f"trying next voice after {voice_name}",
        )

    raise RuntimeError(str(last_error) if last_error else "Google synthesis failed")


def synthesize_google_book(
    book: Dict[str, Any],
    slug: str,
    text: str,
    language: str,
    voices: Dict[str, Any],
    tier: str,
    output_path: Path,
    temp_dir: Path,
    error_log: Path,
    forced_fallback_reason: Optional[str] = None,
) -> Tuple[BookResult, List[Dict[str, Any]]]:
    """Generate an entire book with Google Cloud TTS."""

    first_voice = google_voice_name(voices, language, tier, False)
    chunks = google_body_chunks(text, language, voices, first_voice)
    audio_chunks: List[AudioChunk] = []
    all_timestamps: List[Dict[str, Any]] = []
    offset_ms = 0
    voice_used = first_voice
    fallback_used = forced_fallback_reason is not None
    fallback_reason = forced_fallback_reason

    for index, (raw_chunk, marked_body, words) in enumerate(chunks):
        audio, timestamps, voice_used, chunk_fallback, chunk_reason = synthesize_google_chunk_with_retry(
            slug, marked_body, language, words, offset_ms, voices, tier, error_log
        )
        fallback_used = fallback_used or chunk_fallback
        fallback_reason = fallback_reason or chunk_reason

        temp_mp3 = temp_dir / f"temp_{slug}_{index}.mp3"
        norm_wav = temp_dir / f"norm_{slug}_{index}.wav"
        temp_mp3.write_bytes(audio)
        normalize_to_wav(temp_mp3, norm_wav)
        chunk_duration = duration_ms(norm_wav)

        if timestamps:
            timestamps[-1]["end_ms"] = min(offset_ms + chunk_duration, max(timestamps[-1]["end_ms"], timestamps[-1]["start_ms"] + 120))
        all_timestamps.extend(timestamps)
        audio_chunks.append(AudioChunk(norm_wav, chunk_duration, timestamps))
        offset_ms += chunk_duration
        logging.info("Google chunk %s/%s complete for %s", index + 1, len(chunks), slug)

    final_duration = concat_and_encode(audio_chunks, output_path, temp_dir)
    characters_billed = int(len(text) * 1.15)
    price = GOOGLE_NEURAL2_COST_PER_1K if tier == "neural2" else GOOGLE_WAVENET_COST_PER_1K
    result = BookResult(
        slug=slug,
        title=str(book.get("title") or slug),
        author=str(book.get("author") or ""),
        language=language,
        provider_used="google",
        voice=voice_used,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        duration_ms=final_duration,
        total_words=len(tokenize_words(text, language)),
        highlight_available=bool(all_timestamps),
        chapter_count=0,
        characters_billed=characters_billed,
        estimated_cost_usd=round((characters_billed / 1000) * price, 6),
        pace=None,
    )
    return result, all_timestamps


def synthesize_sarvam_book(
    book: Dict[str, Any],
    slug: str,
    text: str,
    voices: Dict[str, Any],
    output_path: Path,
    temp_dir: Path,
    error_log: Path,
    google_tier: str,
) -> Tuple[BookResult, List[Dict[str, Any]]]:
    """Generate Bengali through Sarvam, falling back to Google if Sarvam fails."""

    chunks = sarvam_chunks(text)
    audio_chunks: List[AudioChunk] = []
    all_timestamps: List[Dict[str, Any]] = []
    offset_ms = 0
    alignment_failed = False

    try:
        audio_index = 0
        for batch_start in range(0, len(chunks), MAX_SARVAM_INPUTS_PER_CALL):
            batch = chunks[batch_start : batch_start + MAX_SARVAM_INPUTS_PER_CALL]
            audios = request_sarvam_batch(slug, batch, voices)

            for local_index, audio_bytes in enumerate(audios):
                chunk_text = batch[local_index]
                temp_wav = temp_dir / f"temp_{slug}_{audio_index}.wav"
                norm_wav = temp_dir / f"norm_{slug}_{audio_index}.wav"
                temp_wav.write_bytes(audio_bytes)
                normalize_to_wav(temp_wav, norm_wav)
                chunk_duration = duration_ms(norm_wav)

                timestamps: List[Dict[str, Any]] = []
                if not alignment_failed:
                    try:
                        timestamps = sarvam_word_timestamps(norm_wav, chunk_text, offset_ms)
                        if not alignment_is_usable(timestamps, chunk_text, offset_ms, chunk_duration):
                            log_error(
                                error_log,
                                slug,
                                "sarvam",
                                "AlignmentWarning",
                                "forced alignment was incomplete for a Bengali chunk",
                                "used deterministic proportional word timings for this chunk",
                            )
                            timestamps = synthetic_word_timestamps(chunk_text, offset_ms, chunk_duration, "ben")
                    except Exception as exc:
                        log_error(
                            error_log,
                            slug,
                            "sarvam",
                            "AlignmentError",
                            str(exc),
                            "used deterministic proportional word timings for this chunk",
                        )
                        timestamps = synthetic_word_timestamps(chunk_text, offset_ms, chunk_duration, "ben")

                if not alignment_failed:
                    all_timestamps.extend(timestamps)
                audio_chunks.append(AudioChunk(norm_wav, chunk_duration, timestamps))
                offset_ms += chunk_duration
                audio_index += 1
                logging.info("Sarvam chunk %s/%s complete for %s", audio_index, len(chunks), slug)

    except Exception as exc:
        reason = f"Sarvam failed: {exc}"
        if not env_truthy("ENABLE_GOOGLE_FALLBACK", True):
            log_error(error_log, slug, "sarvam", "APIError", str(exc), "skipped book; Google fallback disabled")
            raise RuntimeError(f"{reason}; Google fallback disabled")
        log_error(error_log, slug, "sarvam", "APIError", str(exc), "fell back to google bn-IN")
        return synthesize_google_book(
            book,
            slug,
            text,
            "ben",
            voices,
            google_tier,
            output_path,
            temp_dir,
            error_log,
            forced_fallback_reason=reason,
        )

    final_duration = concat_and_encode(audio_chunks, output_path, temp_dir)
    config = voices["ben"]["sarvam"]
    result = BookResult(
        slug=slug,
        title=str(book.get("title") or slug),
        author=str(book.get("author") or ""),
        language="ben",
        provider_used="sarvam",
        voice=str(config["speaker"]),
        fallback_used=False,
        fallback_reason=None,
        duration_ms=final_duration,
        total_words=len(tokenize_words(text, "ben")),
        highlight_available=bool(all_timestamps) and not alignment_failed,
        chapter_count=0,
        characters_billed=len(text),
        estimated_cost_usd=round((len(text) / 1000) * SARVAM_COST_PER_1K_CHARS, 6),
        pace=float(config["pace"]),
    )
    return result, all_timestamps


def tokenize_words(text: str, language: str) -> List[str]:
    """Tokenize the same way the front-end highlight engine expects."""

    if language == "ben":
        tokens = re.split(r"\s+", text.strip())
    else:
        tokens = re.findall(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?|[^\s]", text)
    return [visible_word(token) for token in tokens if visible_word(token)]


def detect_chapters(text: str, book_title: str) -> List[Dict[str, Any]]:
    """Detect chapter headings conservatively and preserve reading order."""

    patterns = [
        re.compile(r"^(chapter\s+([0-9]+|[ivxlcdm]+|one|two|three|four|five|six|seven|eight|nine|ten)\b.*)$", re.I),
        re.compile(r"^((book|part|volume)\s+([0-9]+|[ivxlcdm]+)\b.*)$", re.I),
        re.compile(r"^([IVXLCDM]{1,10}\.?)$"),
        re.compile(r"^([\u0980-\u09ff\s]{1,60}(অধ্যায়|পর্ব|খণ্ড).*)$"),
    ]
    chapters: List[Dict[str, Any]] = []
    cursor = 0
    for paragraph in re.split(r"(\n\s*\n)", text):
        paragraph_start = cursor
        cursor += len(paragraph)
        line = paragraph.strip()
        if not line or len(line) > 120:
            continue
        if any(pattern.match(line) for pattern in patterns):
            chapters.append({"title": line, "char_index": paragraph_start})

    if not chapters:
        chapters.append({"title": book_title or "Full Text", "char_index": 0})
    return chapters


def chapter_index_with_timestamps(
    chapters: List[Dict[str, Any]],
    text: str,
    language: str,
    timestamps: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Map chapter character offsets to audio offsets using word counts."""

    indexed: List[Dict[str, Any]] = []
    for chapter in chapters:
        words_before = tokenize_words(text[: int(chapter.get("char_index", 0))], language)
        word_index = min(len(words_before), max(0, len(timestamps) - 1))
        start_ms = timestamps[word_index]["start_ms"] if timestamps else 0
        indexed.append({"title": chapter["title"], "start_ms": start_ms})
    return indexed


def write_json(path: Path, data: Any) -> None:
    """Write UTF-8 JSON that keeps Bengali text readable in files."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def format_vtt_time(ms: int) -> str:
    """Format milliseconds as WebVTT HH:MM:SS.mmm."""

    ms = max(0, int(ms))
    hours, remainder = divmod(ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def write_vtt(path: Path, timestamps: List[Dict[str, Any]]) -> None:
    """Write one-word WebVTT cues for browser-native highlight options."""

    lines = ["WEBVTT", ""]
    for item in timestamps:
        lines.append(f"{format_vtt_time(item['start_ms'])} --> {format_vtt_time(item['end_ms'])}")
        lines.append(str(item["word"]))
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def append_cost_log(path: Path, result: BookResult) -> None:
    """Append spend data for finance and future provider comparisons."""

    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["slug", "language", "provider_used", "voice", "characters", "estimated_cost_usd", "generated_at"],
        )
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "slug": result.slug,
                "language": result.language,
                "provider_used": result.provider_used,
                "voice": result.voice,
                "characters": result.characters_billed,
                "estimated_cost_usd": f"{result.estimated_cost_usd:.6f}",
                "generated_at": utc_now(),
            }
        )


def write_book_outputs(
    result: BookResult,
    book: Dict[str, Any],
    text: str,
    output_dir: Path,
    timestamps: List[Dict[str, Any]],
) -> None:
    """Write timestamps, VTT, chapter index, and generation metadata."""

    lang_dir = output_dir / result.language
    stem = lang_dir / result.slug
    chapters = detect_chapters(text, result.title)
    chapter_index = chapter_index_with_timestamps(chapters, text, result.language, timestamps)
    result.chapter_count = len(chapter_index)

    write_json(Path(f"{stem}_timestamps.json"), timestamps)
    write_vtt(Path(f"{stem}_highlight.vtt"), timestamps)
    write_json(Path(f"{stem}_chapters.json"), chapter_index)
    write_json(
        Path(f"{stem}_meta.json"),
        {
            "slug": result.slug,
            "title": result.title,
            "author": result.author,
            "language": result.language,
            "provider_used": result.provider_used,
            "fallback_used": result.fallback_used,
            "fallback_reason": result.fallback_reason,
            "duration_ms": result.duration_ms,
            "total_words": result.total_words,
            "highlight_available": result.highlight_available,
            "chapters": result.chapter_count,
            "generated_at": utc_now(),
            "voice": result.voice,
            "pace": result.pace,
            "characters_billed": result.characters_billed,
            "estimated_cost_usd": result.estimated_cost_usd,
        },
    )


def dry_run_book(
    book: Dict[str, Any],
    slug: str,
    text: str,
    language: str,
    voices: Dict[str, Any],
    voice_tier: str,
) -> Dict[str, Any]:
    """Print a dry-run preview with zero provider calls."""

    if language == "ben" and str(voices["ben"].get("primary_provider", "sarvam")).lower() == "google":
        provider = "google"
        voice = google_voice_name(voices, "ben", voice_tier, False)
        body = build_google_body(text[:1200], "ben")
        marked, _words = insert_word_marks(body)
        preview = wrap_google_ssml(marked, voice, "ben", voices)[:300]
        characters = int(len(text) * 1.15)
        price = GOOGLE_NEURAL2_COST_PER_1K if voice_tier == "neural2" else GOOGLE_WAVENET_COST_PER_1K
        estimated_cost = (characters / 1000) * price
    elif language == "ben":
        provider = "sarvam"
        voice = str(voices["ben"]["sarvam"]["speaker"])
        preview = preprocess_sarvam_text(text)[:300]
        characters = len(text)
        estimated_cost = (characters / 1000) * SARVAM_COST_PER_1K_CHARS
    else:
        provider = "google"
        voice = google_voice_name(voices, "en", voice_tier, False)
        body = build_google_body(text[:1200], "en")
        marked, _words = insert_word_marks(body)
        preview = wrap_google_ssml(marked, voice, "en", voices)[:300]
        characters = int(len(text) * 1.15)
        price = GOOGLE_NEURAL2_COST_PER_1K if voice_tier == "neural2" else GOOGLE_WAVENET_COST_PER_1K
        estimated_cost = (characters / 1000) * price

    estimated_minutes = max(1, round(len(text) / 900, 1))
    report = {
        "slug": slug,
        "title": book.get("title") or slug,
        "language": language,
        "provider": provider,
        "voice": voice,
        "raw_characters": len(text),
        "billable_characters_estimate": characters,
        "estimated_cost_usd": round(estimated_cost, 6),
        "estimated_duration_minutes": estimated_minutes,
        "preview": preview,
    }

    print("\n--- DRY RUN ---")
    for key, value in report.items():
        if key == "preview":
            print("preview:")
            print(value)
        else:
            print(f"{key}: {value}")
    return report


def process_book(
    book: Dict[str, Any],
    args: argparse.Namespace,
    voices: Dict[str, Any],
    output_dir: Path,
    text_dir: Path,
    cost_log: Path,
    error_log: Path,
    scrape_failures: Path,
) -> BookResult:
    """Generate or dry-run one manifest entry and isolate all per-book failures."""

    slug = slug_for_book(book)
    text = load_or_scrape_text(book, slug, text_dir, scrape_failures)
    language = detect_language(book, text)
    if args.lang and language != args.lang:
        return BookResult(
            slug=slug,
            title=str(book.get("title") or slug),
            author=str(book.get("author") or ""),
            language=language,
            provider_used="skipped",
            voice="",
            fallback_used=False,
            fallback_reason=None,
            duration_ms=0,
            total_words=0,
            highlight_available=False,
            chapter_count=0,
            characters_billed=0,
            estimated_cost_usd=0.0,
            pace=None,
            skipped=True,
            skip_reason="language filter",
        )

    if args.dry_run:
        dry = dry_run_book(book, slug, text, language, voices, args.voice_tier)
        return BookResult(
            slug=slug,
            title=str(book.get("title") or slug),
            author=str(book.get("author") or ""),
            language=language,
            provider_used=str(dry["provider"]),
            voice=str(dry["voice"]),
            fallback_used=False,
            fallback_reason=None,
            duration_ms=0,
            total_words=len(tokenize_words(text, language)),
            highlight_available=False,
            chapter_count=len(detect_chapters(text, str(book.get("title") or slug))),
            characters_billed=int(dry["billable_characters_estimate"]),
            estimated_cost_usd=float(dry["estimated_cost_usd"]),
            pace=float(voices["ben"]["sarvam"]["pace"]) if language == "ben" else None,
        )

    output_path = output_dir / language / f"{slug}.mp3"
    if output_path.exists():
        result = BookResult(
            slug=slug,
            title=str(book.get("title") or slug),
            author=str(book.get("author") or ""),
            language=language,
            provider_used="skipped",
            voice="existing",
            fallback_used=False,
            fallback_reason=None,
            duration_ms=duration_ms(output_path),
            total_words=len(tokenize_words(text, language)),
            highlight_available=(output_dir / language / f"{slug}_timestamps.json").exists(),
            chapter_count=len(detect_chapters(text, str(book.get("title") or slug))),
            characters_billed=0,
            estimated_cost_usd=0.0,
            pace=None,
            skipped=True,
            skip_reason="audio already exists",
        )
        append_cost_log(cost_log, result)
        return result

    with tempfile.TemporaryDirectory(prefix=f"earnalism_audio_{slug}_") as tmp:
        temp_dir = Path(tmp)
        if language == "ben" and str(voices["ben"].get("primary_provider", "sarvam")).lower() == "google":
            result, timestamps = synthesize_google_book(
                book,
                slug,
                text,
                "ben",
                voices,
                args.voice_tier,
                output_path,
                temp_dir,
                error_log,
                forced_fallback_reason="configured Bengali primary_provider=google for deterministic word timing",
            )
        elif language == "ben":
            result, timestamps = synthesize_sarvam_book(
                book,
                slug,
                text,
                voices,
                output_path,
                temp_dir,
                error_log,
                args.voice_tier,
            )
        else:
            result, timestamps = synthesize_google_book(
                book,
                slug,
                text,
                "en",
                voices,
                args.voice_tier,
                output_path,
                temp_dir,
                error_log,
            )

    write_book_outputs(result, book, text, output_dir, timestamps)
    append_cost_log(cost_log, result)
    return result


def print_final_summary(results: List[BookResult], dry_run: bool) -> None:
    """Print a concise batch report for operators."""

    processed = [result for result in results if not result.skipped]
    skipped = [result for result in results if result.skipped]
    print("\nAudio generation summary")
    print("========================")
    print(f"Mode: {'dry-run' if dry_run else 'generation'}")
    print(f"Processed: {len(processed)}")
    print(f"Skipped: {len(skipped)}")
    if processed:
        print("Processed books:")
        for result in processed:
            highlight = "timestamps" if result.highlight_available else "no timestamps"
            print(f"  - {result.title} ({result.slug}) [{result.provider_used}, {highlight}]")
    if skipped:
        print("Skipped books:")
        for result in skipped:
            print(f"  - {result.title} ({result.slug}): {result.skip_reason}")
    total_cost = sum(result.estimated_cost_usd for result in results)
    total_chars = sum(result.characters_billed for result in results)
    print(f"Billable characters estimate: {total_chars}")
    print(f"Estimated cost: ${total_cost:.6f}")


def main() -> None:
    """Orchestrate manifest loading, generation, and robust per-book failure handling."""

    args = parse_args()
    manifest_path = Path(args.manifest).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    text_dir = Path(args.text_dir).expanduser().resolve() if args.text_dir else output_dir / "texts"
    setup_logging(output_dir)
    validate_environment(args.dry_run)
    if not args.dry_run:
        ensure_ffmpeg_available()

    voices = load_voices(Path(args.voices).expanduser().resolve())
    books = load_manifest(manifest_path)
    cost_log = output_dir / "cost_log.csv"
    error_log = output_dir / "error_log.json"
    scrape_failures = output_dir / "scrape_failures.json"

    results: List[BookResult] = []
    requested_slug = normalize_slug(args.slug) if args.slug else None
    matched_requested_slug = False

    for book in books:
        slug = slug_for_book(book)
        if requested_slug and slug != requested_slug:
            continue
        matched_requested_slug = True
        try:
            result = process_book(book, args, voices, output_dir, text_dir, cost_log, error_log, scrape_failures)
            if result.skip_reason != "language filter":
                results.append(result)
        except Exception as exc:
            language = detect_language(book)
            title = str(book.get("title") or slug)
            log_error(error_log, slug, "pipeline", exc.__class__.__name__, str(exc), "skipped book, continued batch")
            results.append(
                BookResult(
                    slug=slug,
                    title=title,
                    author=str(book.get("author") or ""),
                    language=language,
                    provider_used="failed",
                    voice="",
                    fallback_used=False,
                    fallback_reason=None,
                    duration_ms=0,
                    total_words=0,
                    highlight_available=False,
                    chapter_count=0,
                    characters_billed=0,
                    estimated_cost_usd=0.0,
                    pace=None,
                    skipped=True,
                    skip_reason=str(exc),
                )
            )

    if requested_slug and not matched_requested_slug:
        available = ", ".join(slug_for_book(book) for book in books[:12])
        print(f"No manifest book matched --slug {requested_slug}.")
        print(f"Available slugs: {available}")

    print_final_summary(results, args.dry_run)


if __name__ == "__main__":
    main()
