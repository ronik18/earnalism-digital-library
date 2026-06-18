#!/usr/bin/env python3
"""Generate and onboard synced audiobooks with open-source TTS.

This script is intentionally separate from ``generate_audio.py`` because the
existing production generator is wired to paid TTS providers. The reader-facing
contract is the same:

    frontend/public/audio/{lang}/{slug}.mp3
    frontend/public/audio/{lang}/{slug}_timestamps.json
    frontend/public/audio/{lang}/{slug}_highlight.vtt
    frontend/public/audio/{lang}/{slug}_chapters.json
    frontend/public/audio/{lang}/{slug}_meta.json

Generated narration text is derived from stored chapter HTML, but this script
never writes story content back to the database.
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DIRECT_CLOUDINARY_UPLOAD_LIMIT_BYTES = int(
    os.environ.get("CLOUDINARY_DIRECT_UPLOAD_LIMIT_BYTES", str(95 * 1024 * 1024))
)
CLOUDINARY_LARGE_UPLOAD_CHUNK_BYTES = int(
    os.environ.get("CLOUDINARY_LARGE_UPLOAD_CHUNK_BYTES", str(20 * 1024 * 1024))
)
AUDIO_UPLOADER_JS = ROOT / "lib/storage/audioUploader.js"

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from generate_audio import (  # noqa: E402
    AudioChunk,
    chapter_index_with_timestamps,
    chunk_plain_text,
    clean_scraped_text,
    concat_and_encode,
    detect_chapters,
    duration_ms,
    normalize_slug,
    normalize_word_timestamps,
    normalize_to_wav,
    stable_whisper_model,
    synthetic_word_timestamps,
    tokenize_words,
    utc_now,
    write_json,
    write_vtt,
)

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False


DEFAULT_API_URL = "https://api.theearnalism.com"
DEFAULT_OUTPUT_DIR = ROOT / "output/open_source_audiobooks"
DEFAULT_PUBLIC_AUDIO_DIR = ROOT / "frontend/public/audio"
DEFAULT_REPORT_DIR = ROOT / "output/audio_onboarding"
DEFAULT_INDIC_MODEL = "ai4bharat/indic-parler-tts"
DEFAULT_MMS_BENGALI_MODEL = "facebook/mms-tts-ben"
DEFAULT_BENGALI_PROMPT = (
    "A warm Bengali literary audiobook narrator with clear diction, expressive "
    "emotion, natural pauses, and a reflective storytelling pace."
)
DEFAULT_PIPER_MODEL = ROOT / ".cache/audio_models/piper/en_US-lessac-medium/en_US-lessac-medium.onnx"
DEFAULT_PIPER_CONFIG = ROOT / ".cache/audio_models/piper/en_US-lessac-medium/en_US-lessac-medium.onnx.json"
DEFAULT_PIPER_BINARY = ROOT / ".venv-audio/bin/piper"
LOCAL_TTS_PROVIDERS = {"piper", "mms-tts", "indic-parler-tts"}
PAID_TTS_PROVIDERS = {
    "elevenlabs",
    "openai",
    "openai-tts",
    "google",
    "google-cloud",
    "google-tts",
    "azure",
    "azure-tts",
    "amazon-polly",
    "polly",
    "playht",
    "lovo",
    "heygen",
    "sarvam",
}
PAID_TTS_ENV_VARS = (
    "ELEVENLABS_API_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_CLOUD_PROJECT",
    "AZURE_SPEECH_KEY",
    "AZURE_SPEECH_REGION",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "PLAYHT_API_KEY",
    "LOVO_API_KEY",
    "HEYGEN_API_KEY",
    "SARVAM_API_KEY",
)


def default_piper_binary() -> str:
    return str(DEFAULT_PIPER_BINARY) if DEFAULT_PIPER_BINARY.exists() else "piper"


def default_piper_model() -> str:
    return str(DEFAULT_PIPER_MODEL) if DEFAULT_PIPER_MODEL.exists() else ""


def default_piper_config() -> str:
    return str(DEFAULT_PIPER_CONFIG) if DEFAULT_PIPER_CONFIG.exists() else ""


class HTMLTextExtractor(HTMLParser):
    BLOCK_TAGS = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag.lower() in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if data:
            self.parts.append(data)

    def text(self) -> str:
        value = html.unescape("".join(self.parts))
        value = re.sub(r"[ \t]+", " ", value)
        value = re.sub(r"\n[ \t]+", "\n", value)
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value.strip()


@dataclass
class BundleValidation:
    ok: bool
    detail: str
    timestamp_count: int = 0
    expected_units: int = 0


@dataclass
class OnboardingResult:
    slug: str
    title: str
    is_published: bool
    language: str = ""
    status: str = "SKIPPED"
    detail: str = ""
    provider: str = ""
    voice: str = ""
    generated: bool = False
    copied_to_public: bool = False
    flags_synced: bool = False
    cloudinary_uploaded: bool = False
    duration_ms: int = 0
    audio_size: int = 0
    timestamp_count: int = 0
    expected_units: int = 0
    asset_urls: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Open-source Earnalism audiobook onboarding.")
    parser.add_argument("command", choices=("preflight", "audit", "generate"), help="Operation to run")
    parser.add_argument("--api-url", default=os.environ.get("EARNALISM_API_URL", DEFAULT_API_URL))
    parser.add_argument("--env-file", default=str(ROOT / ".secrets/earnalism-import.env"))
    parser.add_argument("--manifest", type=Path, default=None, help="Optional JSON list/dict of target books to process")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--public-audio-dir", type=Path, default=DEFAULT_PUBLIC_AUDIO_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--book-slug", "--book", dest="book_slug", action="append", default=[], help="Limit to one slug; can be repeated")
    parser.add_argument("--all-missing", action="store_true", help="Limit to published books that do not have mapped mp3+timestamp assets")
    parser.add_argument("--lang", "--language", dest="lang", choices=("ben", "bn", "en"), default=None, help="Process one language only")
    parser.add_argument("--limit", type=int, default=0, help="Process at most N selected books")
    parser.add_argument("--include-drafts", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--include-published", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--regenerate", "--force", dest="regenerate", action="store_true", help="Overwrite existing completed output bundles")
    parser.add_argument("--validate-only", action="store_true", help="Validate existing bundles without synthesizing audio")
    parser.add_argument("--local-only", action=argparse.BooleanOptionalAction, default=True, help="Refuse paid/cloud TTS providers")
    parser.add_argument(
        "--skip-live-audio-assets",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip books that already have reader-ready mp3/timestamp URLs mapped in the database",
    )
    parser.add_argument("--order-shortest-first", action="store_true", help="Fetch selected books and process shorter books first")
    parser.add_argument("--copy-to-public", action="store_true", help="Copy passing bundles into frontend/public/audio")
    parser.add_argument(
        "--upload-to-cloudinary",
        "--upload-to-storage",
        dest="upload_to_cloudinary",
        action="store_true",
        help="Upload passing bundles through the audiobook storage router and keep returned URLs",
    )
    parser.add_argument("--cloudinary-folder", default=os.environ.get("CLOUDINARY_AUDIO_FOLDER", "earnalism/audiobooks"))
    parser.add_argument("--sync-flags", action="store_true", help="Patch live audiobook flags after validation passes")
    parser.add_argument("--dry-run", action="store_true", help="Do not synthesize; write text and estimates only")
    parser.add_argument("--max-chars", type=int, default=0, help="Skip books above this narration-text length")
    parser.add_argument("--english-provider", choices=("piper",), default="piper")
    parser.add_argument(
        "--bengali-provider",
        choices=("mms-tts", "indic-parler-tts"),
        default=os.environ.get("BENGALI_TTS_PROVIDER", "mms-tts"),
    )
    parser.add_argument("--piper-binary", default=os.environ.get("PIPER_BINARY") or default_piper_binary())
    parser.add_argument("--piper-model", default=os.environ.get("PIPER_MODEL_PATH") or default_piper_model())
    parser.add_argument("--piper-config", default=os.environ.get("PIPER_CONFIG_PATH") or default_piper_config())
    parser.add_argument("--piper-speaker", default=os.environ.get("PIPER_SPEAKER", ""))
    parser.add_argument("--piper-length-scale", type=float, default=float(os.environ.get("PIPER_LENGTH_SCALE", "1.08")))
    parser.add_argument("--indic-model", default=os.environ.get("INDIC_PARLER_TTS_MODEL", DEFAULT_INDIC_MODEL))
    parser.add_argument("--indic-description", default=os.environ.get("INDIC_PARLER_TTS_DESCRIPTION", DEFAULT_BENGALI_PROMPT))
    parser.add_argument("--indic-max-new-tokens", type=int, default=int(os.environ.get("INDIC_PARLER_MAX_NEW_TOKENS", "1200")))
    parser.add_argument("--mms-model", default=os.environ.get("MMS_TTS_BENGALI_MODEL", DEFAULT_MMS_BENGALI_MODEL))
    parser.add_argument("--english-chunk-chars", type=int, default=1100)
    parser.add_argument("--bengali-chunk-chars", type=int, default=420)
    parser.add_argument("--alignment-min-ratio", type=float, default=0.8)
    parser.add_argument("--skip-alignment", action="store_true", help="Use deterministic proportional timestamps only")
    return parser.parse_args()


def normalize_api_url(value: str) -> str:
    value = (value or DEFAULT_API_URL).rstrip("/")
    return value if value.endswith("/api") else f"{value}/api"


def canonical_audio_language(value: str) -> str:
    value = (value or "").strip().lower()
    if value in {"bn", "ben", "bengali", "bn-in", "bn-bd"}:
        return "ben"
    if value in {"en", "eng", "english", "en-us", "en-in", "en-gb"}:
        return "en"
    return value


def paid_tts_env_vars_present() -> List[str]:
    return [name for name in PAID_TTS_ENV_VARS if os.environ.get(name)]


def enforce_local_only(args: argparse.Namespace) -> None:
    if not getattr(args, "local_only", True):
        return
    providers = {
        "english_provider": str(getattr(args, "english_provider", "") or ""),
        "bengali_provider": str(getattr(args, "bengali_provider", "") or ""),
    }
    invalid = {
        name: provider
        for name, provider in providers.items()
        if provider and (provider in PAID_TTS_PROVIDERS or provider not in LOCAL_TTS_PROVIDERS)
    }
    if invalid:
        rendered = ", ".join(f"{name}={provider}" for name, provider in invalid.items())
        raise RuntimeError(f"--local-only refuses paid/cloud TTS provider selection: {rendered}")


def enforce_remote_audio_safety(args: argparse.Namespace) -> None:
    remote_actions: list[str] = []
    if getattr(args, "upload_to_cloudinary", False):
        remote_actions.append("--upload-to-storage")
    if getattr(args, "sync_flags", False):
        remote_actions.append("--sync-flags")
    if getattr(args, "copy_to_public", False):
        remote_actions.append("--copy-to-public")
    if not remote_actions:
        return

    missing: list[str] = []
    if os.environ.get("EARNALISM_ALLOW_AUDIO_UPLOAD") != "true":
        missing.append("EARNALISM_ALLOW_AUDIO_UPLOAD=true")
    if os.environ.get("EARNALISM_ALLOW_PROVIDER_CALLS") != "true":
        missing.append("EARNALISM_ALLOW_PROVIDER_CALLS=true")
    if getattr(args, "sync_flags", False) and os.environ.get("EARNALISM_CONFIRM_PRODUCTION_AUDIO") != "true":
        missing.append("EARNALISM_CONFIRM_PRODUCTION_AUDIO=true")
    if missing:
        actions = ", ".join(remote_actions)
        required = ", ".join(missing)
        raise RuntimeError(f"Audio remote action guard blocked {actions}. Set {required} to continue.")


def load_target_manifest(path: Optional[Path]) -> Tuple[set[str], Dict[str, str]]:
    if not path:
        return set(), {}
    manifest_path = path.expanduser()
    if not manifest_path.exists():
        raise RuntimeError(f"Target audiobook manifest not found: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("books") or payload.get("items") or payload.get("targets") or []
    else:
        raise RuntimeError("Target audiobook manifest must be a JSON list or an object with books/items/targets")
    slugs: set[str] = set()
    languages: Dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        slug = normalize_slug(str(item.get("slug") or ""))
        if not slug:
            continue
        slugs.add(slug)
        language = canonical_audio_language(str(item.get("language") or ""))
        if language:
            languages[slug] = language
    return slugs, languages


def public_bundle_urls(slug: str, language: str) -> Dict[str, str]:
    return {
        "mp3": f"/audio/{language}/{slug}.mp3",
        "timestamps": f"/audio/{language}/{slug}_timestamps.json",
        "vtt": f"/audio/{language}/{slug}_highlight.vtt",
        "chapters": f"/audio/{language}/{slug}_chapters.json",
        "meta": f"/audio/{language}/{slug}_meta.json",
    }


def load_environment(args: argparse.Namespace) -> None:
    env_path = Path(args.env_file).expanduser()
    if env_path.exists():
        load_dotenv(env_path)
    load_dotenv()


def request_json(session: requests.Session, method: str, url: str, **kwargs: Any) -> Any:
    last_error: Optional[Exception] = None
    for attempt in range(1, 4):
        try:
            response = session.request(method, url, timeout=120, **kwargs)
            if response.status_code in {502, 503, 504} and attempt < 3:
                last_error = RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")
                time.sleep(attempt * 3)
                continue
            response.raise_for_status()
            return response.json() if response.text.strip() else {}
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(attempt * 3)
                continue
            break
    raise RuntimeError(f"{method} {url} failed: {last_error}")


class EarnalismAdminClient:
    def __init__(self, api_url: str) -> None:
        self.api_url = normalize_api_url(api_url)
        self.session = requests.Session()
        self.headers: Dict[str, str] = {}

    def login(self) -> None:
        token = os.environ.get("EARNALISM_ADMIN_TOKEN", "").strip()
        if not token:
            email = os.environ.get("ADMIN_EMAIL", "").strip()
            password = os.environ.get("ADMIN_PASSWORD", "").strip()
            if not email or not password:
                raise RuntimeError("Missing ADMIN_EMAIL/ADMIN_PASSWORD or EARNALISM_ADMIN_TOKEN.")
            data = request_json(
                self.session,
                "POST",
                f"{self.api_url}/auth/login",
                json={"email": email, "password": password},
            )
            token = str(data.get("token") or "")
        if not token:
            raise RuntimeError("Admin login did not return a token.")
        self.headers = {"Authorization": f"Bearer {token}"}

    def summaries(self) -> List[Dict[str, Any]]:
        return request_json(self.session, "GET", f"{self.api_url}/admin/books/summary", headers=self.headers)

    def book(self, slug: str) -> Dict[str, Any]:
        return request_json(self.session, "GET", f"{self.api_url}/admin/books/{slug}", headers=self.headers)

    def sync_audiobook_flags(self, result: OnboardingResult) -> None:
        request_json(
            self.session,
            "PATCH",
            f"{self.api_url}/admin/books/{result.slug}/audiobook",
            headers=self.headers,
            json={
                "audiobook_enabled": True,
                "generate_audiobook": True,
                "audiobook_provider": result.provider,
                "audiobook_voice": result.voice,
                "audio_asset_slug": result.slug,
                "audiobook_assets": result.asset_urls,
                "audiobook_size": result.audio_size,
                "audiobook_duration_ms": result.duration_ms,
            },
        )


def infer_language(text: str, fallback: str = "") -> str:
    fallback = canonical_audio_language(fallback)
    if fallback == "ben":
        return "ben"
    if fallback == "en":
        return "en"
    return "ben" if re.search(r"[\u0980-\u09ff]", text or "") else "en"


def chapter_text(book: Dict[str, Any]) -> str:
    chunks: List[str] = []
    chapters = sorted(book.get("chapters") or [], key=lambda c: c.get("order", 0))
    for chapter in chapters:
        title = str(chapter.get("title") or "").strip()
        if title.lower() == "full text":
            title = str(book.get("title") or "").strip()
        if title:
            chunks.append(title)

        parser = HTMLTextExtractor()
        parser.feed(str(chapter.get("content") or ""))
        text = parser.text()
        if text:
            chunks.append(text)

    text = clean_scraped_text("\n\n".join(chunks))
    match = re.search(r"(?im)^\s*(Bibliography|References|Index)\s*$", text)
    if match:
        text = text[: match.start()]
    return text.strip() + "\n" if text.strip() else ""


def highlight_units(text: str, language: str) -> List[str]:
    return tokenize_words(text, language)


def bundle_paths(base_dir: Path, language: str, slug: str) -> Dict[str, Path]:
    stem = base_dir / language / slug
    return {
        "mp3": Path(f"{stem}.mp3"),
        "timestamps": Path(f"{stem}_timestamps.json"),
        "vtt": Path(f"{stem}_highlight.vtt"),
        "chapters": Path(f"{stem}_chapters.json"),
        "meta": Path(f"{stem}_meta.json"),
    }


def validate_bundle(base_dir: Path, language: str, slug: str, expected_units: int) -> BundleValidation:
    paths = bundle_paths(base_dir, language, slug)
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        return BundleValidation(False, f"missing: {', '.join(missing)}", expected_units=expected_units)
    try:
        timestamps = json.loads(paths["timestamps"].read_text(encoding="utf-8"))
    except Exception as exc:
        return BundleValidation(False, f"timestamp JSON failed: {exc}", expected_units=expected_units)
    if not isinstance(timestamps, list) or not timestamps:
        return BundleValidation(False, "timestamps file is empty", expected_units=expected_units)
    previous_end = 0
    for index, item in enumerate(timestamps):
        if not isinstance(item, dict) or item.get("start_ms") is None or item.get("end_ms") is None:
            return BundleValidation(False, f"timestamp {index} has null/missing timing fields", len(timestamps), expected_units)
        try:
            start_ms = int(item["start_ms"])
            end_ms = int(item["end_ms"])
        except (TypeError, ValueError):
            return BundleValidation(False, f"timestamp {index} has non-integer timing fields", len(timestamps), expected_units)
        if start_ms < 0:
            return BundleValidation(False, f"timestamp {index} starts before zero", len(timestamps), expected_units)
        if end_ms <= start_ms:
            return BundleValidation(False, f"timestamp {index} end is not greater than start", len(timestamps), expected_units)
        if index > 0 and start_ms < previous_end:
            return BundleValidation(False, f"timestamps overlap or move backwards at index {index}", len(timestamps), expected_units)
        previous_end = end_ms
    try:
        audio_duration = duration_ms(paths["mp3"])
    except Exception as exc:
        return BundleValidation(False, f"audio duration probe failed: {exc}", len(timestamps), expected_units)
    if previous_end > audio_duration + 500:
        return BundleValidation(
            False,
            f"final timestamp exceeds audio duration by more than 500ms: timestamp={previous_end} audio={audio_duration}",
            len(timestamps),
            expected_units,
        )
    tolerance = max(25, int(expected_units * 0.08))
    delta = abs(len(timestamps) - expected_units)
    if expected_units and delta > tolerance:
        return BundleValidation(
            False,
            f"timestamp/token mismatch: timestamps={len(timestamps)} expected={expected_units} tolerance={tolerance}",
            len(timestamps),
            expected_units,
        )
    return BundleValidation(True, "ok", len(timestamps), expected_units)


def stored_chapter_markers(book: Dict[str, Any], text: str) -> List[Dict[str, Any]]:
    markers: List[Dict[str, Any]] = []
    cursor = 0
    for chapter in sorted(book.get("chapters") or [], key=lambda c: c.get("order", 0)):
        title = str(chapter.get("title") or "").strip()
        if title.lower() == "full text":
            title = str(book.get("title") or "").strip()
        if not title:
            continue
        index = text.find(title, cursor)
        if index < 0:
            index = text.find(title)
        if index < 0:
            continue
        markers.append({"title": title, "char_index": index})
        cursor = index + len(title)
    return markers


def write_bundle_chapter_index(
    book: Dict[str, Any],
    text: str,
    language: str,
    output_dir: Path,
    timestamps: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    slug = normalize_slug(str(book.get("slug") or book.get("title") or "book"))
    stem = output_dir / language / slug
    chapters = stored_chapter_markers(book, text) or detect_chapters(text, str(book.get("title") or slug))
    chapter_index = chapter_index_with_timestamps(chapters, text, language, timestamps)
    write_json(Path(f"{stem}_chapters.json"), chapter_index)
    return chapter_index


def refresh_existing_bundle_indexes(book: Dict[str, Any], text: str, language: str, output_dir: Path) -> None:
    slug = normalize_slug(str(book.get("slug") or book.get("title") or "book"))
    paths = bundle_paths(output_dir, language, slug)
    timestamps = json.loads(paths["timestamps"].read_text(encoding="utf-8"))
    chapter_index = write_bundle_chapter_index(book, text, language, output_dir, timestamps)
    meta = read_bundle_meta(output_dir, language, slug)
    if meta:
        meta["chapters"] = len(chapter_index)
        meta["highlight_available"] = bool(timestamps)
        meta["total_words"] = len(tokenize_words(text, language))
        write_json(paths["meta"], meta)


def module_installed(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def preflight(args: argparse.Namespace) -> Dict[str, Any]:
    piper_model = Path(args.piper_model).expanduser() if args.piper_model else None
    piper_config = Path(args.piper_config).expanduser() if args.piper_config else None
    ffmpeg_ok = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
    hf_token = bool(
        os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_TOKEN")
        or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    )
    return {
        "local_only": bool(args.local_only),
        "paid_tts_env_present_ignored": paid_tts_env_vars_present() if args.local_only else [],
        "ffmpeg": ffmpeg_ok,
        "stable_ts": module_installed("stable_whisper"),
        "torch": module_installed("torch"),
        "piper_binary": shutil.which(args.piper_binary) or "",
        "piper_model": str(piper_model) if piper_model else "",
        "piper_model_exists": bool(piper_model and piper_model.exists()),
        "piper_config": str(piper_config) if piper_config else "",
        "piper_config_exists": bool(not piper_config or piper_config.exists()),
        "transformers": module_installed("transformers"),
        "parler_tts": module_installed("parler_tts"),
        "soundfile": module_installed("soundfile"),
        "scipy": module_installed("scipy"),
        "huggingface_token_present": hf_token,
        "cloudinary": module_installed("cloudinary"),
        "cloudinary_configured": bool(
            os.environ.get("CLOUDINARY_CLOUD_NAME")
            and os.environ.get("CLOUDINARY_API_KEY")
            and os.environ.get("CLOUDINARY_API_SECRET")
        ),
        "indic_model": args.indic_model,
        "mms_model": args.mms_model,
        "ready_for_english": bool(ffmpeg_ok and shutil.which(args.piper_binary) and piper_model and piper_model.exists()),
        "ready_for_bengali_mms": bool(
            ffmpeg_ok
            and module_installed("transformers")
            and module_installed("torch")
            and module_installed("soundfile")
        ),
        "ready_for_bengali_indic_parler": bool(
            ffmpeg_ok
            and module_installed("transformers")
            and module_installed("parler_tts")
            and module_installed("soundfile")
            and module_installed("scipy")
            and hf_token
        ),
        "ready_for_bengali": bool(
            ffmpeg_ok
            and module_installed("transformers")
            and module_installed("torch")
            and module_installed("soundfile")
            and (
                args.bengali_provider == "mms-tts"
                or (
                    args.bengali_provider == "indic-parler-tts"
                    and module_installed("parler_tts")
                    and module_installed("scipy")
                    and hf_token
                )
            )
        ),
    }


def select_books(summaries: List[Dict[str, Any]], args: argparse.Namespace) -> List[Dict[str, Any]]:
    manifest_slugs = set(getattr(args, "manifest_slugs", set()) or set())
    requested = {normalize_slug(slug) for slug in args.book_slug} | manifest_slugs
    selected: List[Dict[str, Any]] = []
    for item in summaries:
        slug = normalize_slug(str(item.get("slug") or ""))
        is_published = bool(item.get("is_published"))
        if args.all_missing and has_reader_ready_audio_assets(item):
            continue
        manifest_language = getattr(args, "manifest_languages", {}).get(slug, "")
        summary_language = infer_language(
            f"{item.get('title', '')} {item.get('author', '')} {item.get('category', '')}",
            manifest_language or str(item.get("language") or ""),
        )
        if requested and slug not in requested:
            continue
        if args.lang and summary_language != args.lang:
            continue
        if is_published and not args.include_published:
            continue
        if not is_published and not args.include_drafts:
            continue
        selected.append(item)
    if args.limit > 0:
        selected = selected[: args.limit]
    return selected


def reader_audio_assets(record: Dict[str, Any]) -> Dict[str, str]:
    assets = record.get("audiobook_assets") or {}
    if not isinstance(assets, dict):
        return {}
    urls: Dict[str, str] = {}
    for key in ("mp3", "timestamps", "vtt", "chapters", "meta"):
        value = str(assets.get(key) or "").strip()
        if value.startswith("https://") or value.startswith("/audio/"):
            urls[key] = value
    return urls


def has_reader_ready_audio_assets(record: Dict[str, Any]) -> bool:
    urls = reader_audio_assets(record)
    return bool(urls.get("mp3") and urls.get("timestamps"))


def synthesize_piper_chunk(text: str, output_wav: Path, args: argparse.Namespace) -> str:
    command = [
        args.piper_binary,
        "--model",
        str(Path(args.piper_model).expanduser()),
        "--output_file",
        str(output_wav),
    ]
    if args.piper_config:
        command.extend(["--config", str(Path(args.piper_config).expanduser())])
    if args.piper_speaker:
        command.extend(["--speaker", args.piper_speaker])
    if args.piper_length_scale:
        command.extend(["--length_scale", str(args.piper_length_scale)])
    process = subprocess.run(
        command,
        input=text.strip() + "\n",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if process.returncode != 0:
        raise RuntimeError(process.stderr.strip() or "Piper synthesis failed")
    return Path(args.piper_model).name


_INDIC_CACHE: Dict[str, Any] = {}


def _hf_token() -> Optional[str]:
    return (
        os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_TOKEN")
        or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        or None
    )


def load_indic_model(model_id: str) -> Dict[str, Any]:
    if model_id in _INDIC_CACHE:
        return _INDIC_CACHE[model_id]

    import torch
    import soundfile as sf  # noqa: F401 - kept in cache for generation
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer

    if torch.cuda.is_available():
        device = "cuda"
    elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"

    token = _hf_token()
    model = ParlerTTSForConditionalGeneration.from_pretrained(model_id, token=token).to(device)
    prompt_tokenizer = AutoTokenizer.from_pretrained(model_id, token=token)
    description_model = getattr(model.config, "text_encoder", None)
    description_model_id = getattr(description_model, "_name_or_path", None) or model_id
    description_tokenizer = AutoTokenizer.from_pretrained(description_model_id, token=token)
    payload = {
        "torch": torch,
        "soundfile": sf,
        "model": model,
        "prompt_tokenizer": prompt_tokenizer,
        "description_tokenizer": description_tokenizer,
        "device": device,
        "sampling_rate": int(getattr(model.config, "sampling_rate", 22050)),
    }
    _INDIC_CACHE[model_id] = payload
    return payload


def synthesize_indic_chunk(text: str, output_wav: Path, args: argparse.Namespace) -> str:
    runtime = load_indic_model(args.indic_model)
    torch = runtime["torch"]
    sf = runtime["soundfile"]
    model = runtime["model"]
    prompt_tokenizer = runtime["prompt_tokenizer"]
    description_tokenizer = runtime["description_tokenizer"]
    device = runtime["device"]
    description = args.indic_description

    description_inputs = description_tokenizer(description, return_tensors="pt").to(device)
    prompt_inputs = prompt_tokenizer(text.strip(), return_tensors="pt").to(device)
    with torch.no_grad():
        max_new_tokens = max(256, min(args.indic_max_new_tokens, int(max(1, len(text)) * 8)))
        generation = model.generate(
            input_ids=description_inputs.input_ids,
            attention_mask=getattr(description_inputs, "attention_mask", None),
            prompt_input_ids=prompt_inputs.input_ids,
            prompt_attention_mask=getattr(prompt_inputs, "attention_mask", None),
            max_new_tokens=max_new_tokens,
        )
    audio = generation.detach().cpu().numpy().squeeze()
    sf.write(str(output_wav), audio, runtime["sampling_rate"])
    return args.indic_model


_MMS_CACHE: Dict[str, Any] = {}


def load_mms_model(model_id: str) -> Dict[str, Any]:
    if model_id in _MMS_CACHE:
        return _MMS_CACHE[model_id]

    import torch
    import soundfile as sf  # noqa: F401 - kept in cache for generation
    from transformers import AutoTokenizer, VitsModel

    model = VitsModel.from_pretrained(model_id)
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    payload = {
        "torch": torch,
        "soundfile": sf,
        "model": model,
        "tokenizer": tokenizer,
        "sampling_rate": int(getattr(model.config, "sampling_rate", 16000)),
    }
    _MMS_CACHE[model_id] = payload
    return payload


def synthesize_mms_chunk(text: str, output_wav: Path, args: argparse.Namespace) -> str:
    runtime = load_mms_model(args.mms_model)
    torch = runtime["torch"]
    sf = runtime["soundfile"]
    model = runtime["model"]
    tokenizer = runtime["tokenizer"]

    inputs = tokenizer(text.strip(), return_tensors="pt")
    with torch.no_grad():
        waveform = model(**inputs).waveform
    audio = waveform.detach().cpu().numpy().squeeze()
    sf.write(str(output_wav), audio, runtime["sampling_rate"])
    return args.mms_model


def align_word_timestamps(
    wav_path: Path,
    text: str,
    language: str,
    offset_ms: int,
    min_ratio: float,
    skip_alignment: bool,
) -> Tuple[List[Dict[str, Any]], str]:
    duration = duration_ms(wav_path)
    if skip_alignment:
        return synthetic_word_timestamps(text, offset_ms, duration, language), "synthetic"

    try:
        model = stable_whisper_model()
        whisper_language = "bn" if language == "ben" else "en"
        result = model.align(str(wav_path), text, language=whisper_language)
        timestamps: List[Dict[str, Any]] = []
        for word in result.all_words_or_segments():
            token = getattr(word, "word", "").strip()
            if not token:
                continue
            timestamps.append(
                {
                    "word": token,
                    "start_ms": int(float(word.start) * 1000) + offset_ms,
                    "end_ms": int(float(word.end) * 1000) + offset_ms,
                }
            )
        expected = max(1, len(tokenize_words(text, language)))
        if len(timestamps) >= int(expected * min_ratio):
            return timestamps, "forced_alignment"
        return synthetic_word_timestamps(text, offset_ms, duration, language), "synthetic_after_low_coverage"
    except Exception:
        return synthetic_word_timestamps(text, offset_ms, duration, language), "synthetic_after_alignment_error"


def write_book_outputs(
    book: Dict[str, Any],
    text: str,
    language: str,
    provider: str,
    voice: str,
    output_dir: Path,
    timestamps: List[Dict[str, Any]],
    duration: int,
    alignment_modes: Sequence[str],
) -> None:
    slug = normalize_slug(str(book.get("slug") or book.get("title") or "book"))
    stem = output_dir / language / slug
    timestamps = normalize_word_timestamps(timestamps)
    write_json(Path(f"{stem}_timestamps.json"), timestamps)
    write_vtt(Path(f"{stem}_highlight.vtt"), timestamps)
    chapter_index = write_bundle_chapter_index(book, text, language, output_dir, timestamps)
    write_json(
        Path(f"{stem}_meta.json"),
        {
            "slug": slug,
            "title": book.get("title") or slug,
            "author": book.get("author") or "",
            "language": language,
            "provider_used": provider,
            "voice": voice,
            "duration_ms": duration,
            "total_words": len(tokenize_words(text, language)),
            "highlight_available": bool(timestamps),
            "chapters": len(chapter_index),
            "generated_at": utc_now(),
            "license_note": "Open-source TTS runtime; source story text was not modified.",
            "alignment_modes": sorted(set(alignment_modes)),
        },
    )


def copy_bundle(slug: str, language: str, source_dir: Path, destination_dir: Path) -> None:
    destination = destination_dir / language
    destination.mkdir(parents=True, exist_ok=True)
    for path in bundle_paths(source_dir, language, slug).values():
        if path.exists():
            shutil.copy2(path, destination / path.name)


def read_bundle_meta(source_dir: Path, language: str, slug: str) -> Dict[str, Any]:
    meta_path = bundle_paths(source_dir, language, slug)["meta"]
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def apply_bundle_meta(result: OnboardingResult, source_dir: Path) -> None:
    meta = read_bundle_meta(source_dir, result.language, result.slug)
    if not meta:
        return
    result.provider = str(meta.get("provider_used") or result.provider or "")
    result.voice = str(meta.get("voice") or result.voice or "")
    result.duration_ms = int(meta.get("duration_ms") or result.duration_ms or 0)


def ensure_cloudinary_configured() -> None:
    missing = [
        name
        for name in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")
        if not os.environ.get(name)
    ]
    if missing:
        raise RuntimeError(f"Cloudinary credentials missing: {', '.join(missing)}")


def upload_audiobook_asset(
    slug: str,
    language: str,
    asset_key: str,
    asset_path: Path,
    public_id: str,
    duration: int,
    args: argparse.Namespace,
) -> Dict[str, Any]:
    if not AUDIO_UPLOADER_JS.exists():
        raise RuntimeError(f"Audio uploader helper not found: {AUDIO_UPLOADER_JS}")
    command = [
        "node",
        str(AUDIO_UPLOADER_JS),
        "--file-path",
        str(asset_path),
        "--slug",
        slug,
        "--language",
        language,
        "--public-id",
        public_id,
        "--cloudinary-folder",
        str(args.cloudinary_folder or "earnalism/audiobooks"),
        "--duration",
        str(duration),
        "--asset-kind",
        asset_key,
        "--file-name",
        asset_path.name,
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True, cwd=ROOT)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"Audio asset upload failed for {slug}/{asset_key}: {detail}")
    try:
        payload = json.loads((completed.stdout or "").strip())
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Audio asset upload returned invalid JSON for {slug}/{asset_key}: {completed.stdout[:500]}") from exc
    url = str(payload.get("url") or "").strip()
    provider = str(payload.get("provider") or "").strip().lower()
    if provider not in {"cloudinary", "b2"} or not url:
        raise RuntimeError(f"Audio asset upload returned invalid payload for {slug}/{asset_key}: {payload}")
    return {
        "url": url,
        "provider": provider,
        "size": int(payload.get("size") or asset_path.stat().st_size),
        "duration": int(payload.get("duration") or duration or 0),
    }


def upload_bundle_to_cloudinary(slug: str, language: str, source_dir: Path, args: argparse.Namespace) -> Dict[str, Any]:
    """Upload a validated bundle and return reader-consumable asset URLs plus storage provider."""

    ensure_cloudinary_configured()

    paths = bundle_paths(source_dir, language, slug)
    upload_plan = {
        "mp3": ("video", paths["mp3"], slug),
        "timestamps": ("raw", paths["timestamps"], f"{slug}_timestamps.json"),
        "vtt": ("raw", paths["vtt"], f"{slug}_highlight.vtt"),
        "chapters": ("raw", paths["chapters"], f"{slug}_chapters.json"),
        "meta": ("raw", paths["meta"], f"{slug}_meta.json"),
    }
    folder = str(args.cloudinary_folder or "earnalism/audiobooks").strip().strip("/")
    urls: Dict[str, str] = {}
    audio_upload: Dict[str, Any] = {}
    asset_providers: Dict[str, str] = {}
    audio_duration = duration_ms(paths["mp3"]) if paths["mp3"].exists() else 0
    for key, (resource_type, path, public_name) in upload_plan.items():
        if not path.exists():
            raise RuntimeError(f"Cannot upload missing {key} asset: {path}")
        public_id = f"{folder}/{language}/{slug}/{public_name}"
        asset_upload = upload_audiobook_asset(slug, language, key, path, public_id, audio_duration if key == "mp3" else 0, args)
        urls[key] = str(asset_upload["url"])
        asset_providers[key] = str(asset_upload["provider"])
        if key == "mp3":
            audio_upload = asset_upload
    return {
        "assets": urls,
        "provider": str(audio_upload.get("provider") or "cloudinary"),
        "asset_providers": asset_providers,
        "size": int(audio_upload.get("size") or paths["mp3"].stat().st_size),
        "duration": int(audio_upload.get("duration") or audio_duration or 0),
    }


def generate_book(book: Dict[str, Any], args: argparse.Namespace) -> OnboardingResult:
    slug = normalize_slug(str(book.get("slug") or book.get("title") or "book"))
    title = str(book.get("title") or slug)
    if args.skip_live_audio_assets and has_reader_ready_audio_assets(book):
        manifest_language = getattr(args, "manifest_languages", {}).get(slug, "")
        language = infer_language(
            f"{book.get('title', '')} {book.get('author', '')}",
            manifest_language or str(book.get("language") or ""),
        )
        return OnboardingResult(
            slug=slug,
            title=title,
            is_published=bool(book.get("is_published")),
            language=language,
            status="READY",
            detail="live reader audiobook assets already mapped",
            provider=str(book.get("audiobook_provider") or ""),
            voice=str(book.get("audiobook_voice") or ""),
            duration_ms=0,
            asset_urls=reader_audio_assets(book),
        )

    text = chapter_text(book)
    manifest_language = getattr(args, "manifest_languages", {}).get(slug, "")
    language = infer_language(text, manifest_language or str(book.get("language") or ""))
    expected = len(highlight_units(text, language))
    result = OnboardingResult(slug=slug, title=title, is_published=bool(book.get("is_published")), language=language, expected_units=expected)

    if args.lang and language != args.lang:
        result.status = "SKIPPED"
        result.detail = f"language filter excluded {language}"
        return result

    text_dir = args.report_dir / "texts"
    text_dir.mkdir(parents=True, exist_ok=True)
    (text_dir / f"{slug}.txt").write_text(text, encoding="utf-8")

    if not text or expected == 0:
        result.status = "BLOCKED"
        result.detail = "no narratable chapter text"
        return result
    if args.max_chars and len(text) > args.max_chars:
        result.status = "SKIPPED"
        result.detail = f"over max chars: {len(text)} > {args.max_chars}"
        return result

    if args.validate_only:
        output_validation = validate_bundle(args.output_dir, language, slug, expected)
        public_validation = validate_bundle(args.public_audio_dir, language, slug, expected)
        if output_validation.ok:
            result.status = "READY"
            result.detail = "existing generated bundle"
            result.timestamp_count = output_validation.timestamp_count
            apply_bundle_meta(result, args.output_dir)
        elif public_validation.ok:
            result.status = "READY"
            result.detail = "existing public audio bundle"
            result.timestamp_count = public_validation.timestamp_count
            result.asset_urls = public_bundle_urls(slug, language)
            apply_bundle_meta(result, args.public_audio_dir)
        else:
            result.status = "BLOCKED"
            result.detail = output_validation.detail
            result.timestamp_count = output_validation.timestamp_count
        return result

    existing = validate_bundle(args.output_dir, language, slug, expected)
    if existing.ok and not args.regenerate:
        refresh_existing_bundle_indexes(book, text, language, args.output_dir)
        result.status = "READY"
        result.detail = "existing generated bundle"
        result.timestamp_count = existing.timestamp_count
        apply_bundle_meta(result, args.output_dir)
        if args.copy_to_public:
            copy_bundle(slug, language, args.output_dir, args.public_audio_dir)
            result.copied_to_public = True
            result.asset_urls = public_bundle_urls(slug, language)
        if args.upload_to_cloudinary:
            upload_result = upload_bundle_to_cloudinary(slug, language, args.output_dir, args)
            result.asset_urls = upload_result["assets"]
            result.provider = upload_result["provider"]
            result.audio_size = upload_result["size"]
            result.duration_ms = upload_result["duration"]
            result.cloudinary_uploaded = True
        return result

    if args.dry_run:
        result.status = "DRY_RUN"
        result.detail = f"{len(text)} chars, {expected} highlight units"
        return result

    provider = args.english_provider if language == "en" else args.bengali_provider
    result.provider = provider
    args.output_dir.joinpath(language).mkdir(parents=True, exist_ok=True)
    final_mp3 = args.output_dir / language / f"{slug}.mp3"
    audio_chunks: List[AudioChunk] = []
    timestamps: List[Dict[str, Any]] = []
    alignment_modes: List[str] = []
    offset_ms = 0
    chunk_size = args.english_chunk_chars if language == "en" else args.bengali_chunk_chars
    chunks = [chunk for chunk in chunk_plain_text(text, chunk_size) if chunk.strip()]

    with tempfile.TemporaryDirectory(prefix=f"earnalism_os_audio_{slug}_") as raw_tmp:
        tmp = Path(raw_tmp)
        for index, chunk in enumerate(chunks):
            raw_wav = tmp / f"chunk_{index:05d}.wav"
            norm_wav = tmp / f"norm_{index:05d}.wav"
            if language == "en":
                voice = synthesize_piper_chunk(chunk, raw_wav, args)
            elif provider == "mms-tts":
                voice = synthesize_mms_chunk(chunk, raw_wav, args)
            else:
                voice = synthesize_indic_chunk(chunk, raw_wav, args)
            result.voice = voice
            normalize_to_wav(raw_wav, norm_wav)
            chunk_duration = duration_ms(norm_wav)
            chunk_timestamps, alignment_mode = align_word_timestamps(
                norm_wav,
                chunk,
                language,
                offset_ms,
                args.alignment_min_ratio,
                args.skip_alignment,
            )
            alignment_modes.append(alignment_mode)
            timestamps.extend(chunk_timestamps)
            audio_chunks.append(AudioChunk(norm_wav, chunk_duration, chunk_timestamps))
            offset_ms += chunk_duration
            print(f"{slug}: {index + 1}/{len(chunks)} chunks complete ({alignment_mode})")

        result.duration_ms = concat_and_encode(audio_chunks, final_mp3, tmp)

    write_book_outputs(book, text, language, provider, result.voice, args.output_dir, timestamps, result.duration_ms, alignment_modes)
    validation = validate_bundle(args.output_dir, language, slug, expected)
    result.timestamp_count = validation.timestamp_count
    result.status = "READY" if validation.ok else "BLOCKED"
    result.detail = validation.detail
    result.generated = validation.ok
    if validation.ok and args.copy_to_public:
        copy_bundle(slug, language, args.output_dir, args.public_audio_dir)
        result.copied_to_public = True
        result.asset_urls = public_bundle_urls(slug, language)
    if validation.ok and args.upload_to_cloudinary:
        upload_result = upload_bundle_to_cloudinary(slug, language, args.output_dir, args)
        result.asset_urls = upload_result["assets"]
        result.provider = upload_result["provider"]
        result.audio_size = upload_result["size"]
        result.duration_ms = upload_result["duration"]
        result.cloudinary_uploaded = True
    return result


def audit_books(summaries: List[Dict[str, Any]], args: argparse.Namespace) -> List[OnboardingResult]:
    results: List[OnboardingResult] = []
    for item in select_books(summaries, args):
        slug = normalize_slug(str(item.get("slug") or ""))
        title = str(item.get("title") or slug)
        manifest_language = getattr(args, "manifest_languages", {}).get(slug, "")
        language = infer_language(f"{item.get('title', '')} {item.get('author', '')}", manifest_language or str(item.get("language") or ""))
        if has_reader_ready_audio_assets(item):
            results.append(
                OnboardingResult(
                    slug=slug,
                    title=title,
                    is_published=bool(item.get("is_published")),
                    language=language,
                    status="READY",
                    detail="live reader audiobook assets already mapped",
                    asset_urls=reader_audio_assets(item),
                )
            )
            continue
        public_validation = validate_bundle(args.public_audio_dir, language, slug, 0)
        output_validation = validate_bundle(args.output_dir, language, slug, 0)
        if public_validation.ok:
            status, detail = "READY", "public audio bundle exists"
            timestamp_count = public_validation.timestamp_count
        elif output_validation.ok:
            status, detail = "GENERATED_NOT_PUBLIC", "output bundle exists but was not copied to public audio dir"
            timestamp_count = output_validation.timestamp_count
        else:
            status, detail = "MISSING", public_validation.detail
            timestamp_count = 0
        results.append(
            OnboardingResult(
                slug=slug,
                title=title,
                is_published=bool(item.get("is_published")),
                language=language,
                status=status,
                detail=detail,
                timestamp_count=timestamp_count,
            )
        )
    return results


def result_to_dict(result: OnboardingResult) -> Dict[str, Any]:
    return {
        "slug": result.slug,
        "title": result.title,
        "is_published": result.is_published,
        "language": result.language,
        "status": result.status,
        "detail": result.detail,
        "provider": result.provider,
        "voice": result.voice,
        "generated": result.generated,
        "copied_to_public": result.copied_to_public,
        "cloudinary_uploaded": result.cloudinary_uploaded,
        "flags_synced": result.flags_synced,
        "duration_ms": result.duration_ms,
        "audio_size": result.audio_size,
        "timestamp_count": result.timestamp_count,
        "expected_units": result.expected_units,
        "asset_urls": result.asset_urls,
        "errors": result.errors,
    }


def write_report(args: argparse.Namespace, results: List[OnboardingResult], preflight_payload: Optional[Dict[str, Any]] = None) -> Path:
    args.report_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "generated_at": utc_now(),
        "command": args.command,
        "total": len(results),
        "ready": sum(1 for result in results if result.status == "READY"),
        "blocked": sum(1 for result in results if result.status == "BLOCKED"),
        "missing": sum(1 for result in results if result.status == "MISSING"),
        "dry_run": sum(1 for result in results if result.status == "DRY_RUN"),
        "copied_to_public": sum(1 for result in results if result.copied_to_public),
        "cloudinary_uploaded": sum(1 for result in results if result.cloudinary_uploaded),
        "flags_synced": sum(1 for result in results if result.flags_synced),
        "preflight": preflight_payload or {},
        "results": [result_to_dict(result) for result in results],
    }
    path = args.report_dir / f"open_source_audiobook_{args.command}_{int(time.time())}.json"
    write_json(path, summary)
    latest = args.report_dir / f"open_source_audiobook_{args.command}_latest.json"
    write_json(latest, summary)
    return path


def main() -> None:
    args = parse_args()
    args.lang = canonical_audio_language(args.lang or "") or None
    args.output_dir = args.output_dir.expanduser().resolve()
    args.public_audio_dir = args.public_audio_dir.expanduser().resolve()
    args.report_dir = args.report_dir.expanduser().resolve()
    args.manifest = args.manifest.expanduser().resolve() if args.manifest else None
    load_environment(args)
    enforce_local_only(args)
    enforce_remote_audio_safety(args)
    args.manifest_slugs, args.manifest_languages = load_target_manifest(args.manifest)

    preflight_payload = preflight(args)
    if args.command == "preflight":
        report = write_report(args, [], preflight_payload)
        print(json.dumps(preflight_payload, indent=2))
        print(f"Report: {report}")
        return

    client = EarnalismAdminClient(args.api_url)
    client.login()
    summaries = client.summaries()

    if args.command == "audit":
        results = audit_books(summaries, args)
        report = write_report(args, results, preflight_payload)
        print(f"Audited {len(results)} books. Ready: {sum(1 for result in results if result.status == 'READY')}.")
        print(f"Report: {report}")
        return

    selected = select_books(summaries, args)
    prefetched_books: Dict[str, Dict[str, Any]] = {}
    if args.order_shortest_first and selected:
        sortable: List[Tuple[int, str, Dict[str, Any]]] = []
        for prefetch_index, summary in enumerate(selected, start=1):
            slug = normalize_slug(str(summary.get("slug") or ""))
            if args.skip_live_audio_assets and has_reader_ready_audio_assets(summary):
                sortable.append((0, slug, summary))
                continue
            print(f"Prefetching {prefetch_index}/{len(selected)} {slug} for shortest-first ordering...", flush=True)
            book = client.book(slug)
            prefetched_books[slug] = book
            sortable.append((len(chapter_text(book)), slug, summary))
        selected = [summary for _length, _slug, summary in sorted(sortable, key=lambda row: (row[0], row[1]))]

    results: List[OnboardingResult] = []
    for index, summary in enumerate(selected, start=1):
        slug = normalize_slug(str(summary.get("slug") or ""))
        print(f"\n=== {index}/{len(selected)} {summary.get('title') or slug} ({slug}) ===", flush=True)
        try:
            if args.skip_live_audio_assets and has_reader_ready_audio_assets(summary):
                result = OnboardingResult(
                    slug=slug,
                    title=str(summary.get("title") or slug),
                    is_published=bool(summary.get("is_published")),
                    language=infer_language(
                        f"{summary.get('title', '')} {summary.get('author', '')}",
                        str(summary.get("language") or ""),
                    ),
                    status="READY",
                    detail="live reader audiobook assets already mapped",
                    asset_urls=reader_audio_assets(summary),
                )
            else:
                book = prefetched_books.get(slug) or client.book(slug)
                result = generate_book(book, args)
            should_sync = result.status == "READY" and args.sync_flags and (
                result.generated or result.cloudinary_uploaded or result.copied_to_public
            )
            if should_sync:
                if args.upload_to_cloudinary and not result.asset_urls:
                    raise RuntimeError("Cloudinary upload requested, but no asset URLs were produced")
                client.sync_audiobook_flags(result)
                result.flags_synced = True
        except Exception as exc:  # noqa: BLE001 - batch must continue
            result = OnboardingResult(
                slug=slug,
                title=str(summary.get("title") or slug),
                is_published=bool(summary.get("is_published")),
                status="BLOCKED",
                detail=str(exc),
                errors=[f"{exc.__class__.__name__}: {exc}"],
            )
        print(f"{result.status}: {result.detail}")
        results.append(result)

    report = write_report(args, results, preflight_payload)
    print("\nOpen-source audiobook onboarding summary")
    print("=======================================")
    print(f"Selected: {len(results)}")
    print(f"Ready: {sum(1 for result in results if result.status == 'READY')}")
    print(f"Blocked: {sum(1 for result in results if result.status == 'BLOCKED')}")
    print(f"Copied to public: {sum(1 for result in results if result.copied_to_public)}")
    print(f"Uploaded to remote storage: {sum(1 for result in results if result.cloudinary_uploaded)}")
    print(f"Flags synced: {sum(1 for result in results if result.flags_synced)}")
    print(f"Report: {report}")


if __name__ == "__main__":
    main()
