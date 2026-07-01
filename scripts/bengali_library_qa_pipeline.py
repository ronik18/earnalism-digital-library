#!/usr/bin/env python3
"""
Bengali Legacy Library QA & Optimization Pipeline.

Pipeline stages:
1) Local retrieval/ingestion from a legacy folder.
2) Legal/compliance validation with strict report generation.
3) Text + audio quality optimization.
4) Production packaging of clean, deployment-ready assets.

Usage:
    python scripts/bengali_library_qa_pipeline.py \
        --legacy-dir /legacy_bengali_library \
        --production-dir production_ready \
        --quarantine-dir quarantine \
        --report-path compliance_report.json \
        --workers 4
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import logging
import re
import shutil
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import zipfile
import xml.etree.ElementTree as ET

from mutagen.mp3 import MP3
from mutagen.mp3 import HeaderNotFoundError
from pydub import AudioSegment

try:
    # BeautifulSoup is already present in project requirements and improves text extraction.
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional dependency fallback
    BeautifulSoup = None  # type: ignore[assignment]

LOGGER = logging.getLogger("bengali_library_pipeline")


REQUIRED_LEGAL_FIELDS = ("author", "publisher", "copyright_year", "license_type")
IDENTIFIER_FIELDS = ("isbn", "issn")
TEXT_EXTENSIONS = {".txt", ".md"}
EPUB_EXTENSIONS = {".epub"}
AUDIO_EXTENSIONS = {".mp3"}
METADATA_EXTENSIONS = {".json", ".xml"}
MIN_BITRATE_KBPS = 128
TARGET_LUFS = -16.0
GENERIC_DIR_KEYWORDS = {
    "audio",
    "audios",
    "mp3",
    "ebook",
    "ebooks",
    "epub",
    "text",
    "texts",
    "raw",
    "metadata",
    "meta",
    "source",
}
TOKEN_STOPWORDS = {
    "text",
    "txt",
    "epub",
    "audio",
    "audiobook",
    "book",
    "raw",
    "source",
    "metadata",
    "meta",
    "cover",
    "front",
    "back",
    "v1",
    "v2",
    "final",
    "draft",
}


def setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def normalize_text_content(raw_text: str) -> str:
    """
    Normalize text strictly for reader-quality ingestion.
    - Decode/normalize UTF-8 artifacts
    - Remove HTML/CSS-style junk
    - De-collapse repeated spacing without damaging prose
    """
    if raw_text is None:
        return ""

    text = raw_text

    # Remove CSS/JS blocks and style attributes from old scraped sources.
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", text)
    text = re.sub(r"\s+style=['\"].*?['\"]", " ", text)

    # Remove generic HTML tags.
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)

    # Remove non-printing / control characters while preserving newlines and tabs.
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", " ", text)
    text = text.replace("\ufeff", "")
    text = text.replace("\u00a0", " ")

    # Collapse excessive spaces and keep paragraph structure intact.
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    text = unicodedata.normalize("NFC", text)
    return text.strip()


@dataclass
class AssetPack:
    slug: str
    title: str
    text_files: List[Path] = field(default_factory=list)
    ebook_files: List[Path] = field(default_factory=list)
    audio_files: List[Path] = field(default_factory=list)
    metadata_files: List[Path] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    deployment_file_paths: List[Path] = field(default_factory=list)
    compliance: Dict[str, Any] = field(default_factory=dict)


def safe_tokenise(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[./\\_\\-]+", " ", value)
    tokens = [
        tok for tok in re.split(r"\s+", value) if tok and tok not in TOKEN_STOPWORDS
    ]
    return " ".join(tokens).strip() or "book"


def build_slug_from_path(file_path: Path, source_root: Path) -> str:
    relative = file_path.relative_to(source_root).parts
    stem = file_path.stem
    stem_clean = safe_tokenise(stem)

    parent_context = None
    for part in reversed(relative[:-1]):
        if part.lower() not in GENERIC_DIR_KEYWORDS:
            parent_context = part
            break

    if parent_context:
        base = safe_tokenise(f"{parent_context} {stem_clean}")
    else:
        base = stem_clean

    # Keep stable grouping when a filename contains chapter markers.
    base = re.sub(r"\b(chapter|chap)\s*\d+\b", "", base)
    base = re.sub(r"\b\d+\b", "", base)
    base = re.sub(r"\s{2,}", " ", base).strip()

    if not base:
        base = "book"
    return base


def clean_name_for_fs(value: str) -> str:
    value = re.sub(r'[\\/*?:"<>|]', "", value)
    value = re.sub(r"\s+", "_", value.strip())
    return value[:120] if value else "book"


def gather_assets(legacy_dir: Path) -> Dict[str, AssetPack]:
    packs: Dict[str, AssetPack] = {}

    for file_path in legacy_dir.rglob("*"):
        if not file_path.is_file():
            continue

        extension = file_path.suffix.lower()
        if extension not in (TEXT_EXTENSIONS | EPUB_EXTENSIONS | AUDIO_EXTENSIONS | METADATA_EXTENSIONS):
            continue

        slug = build_slug_from_path(file_path, legacy_dir)
        pack = packs.get(slug)
        if not pack:
            pack = AssetPack(slug=slug, title=slug.title())
            packs[slug] = pack

        if extension in TEXT_EXTENSIONS:
            pack.text_files.append(file_path)
        elif extension in EPUB_EXTENSIONS:
            pack.ebook_files.append(file_path)
        elif extension in AUDIO_EXTENSIONS:
            pack.audio_files.append(file_path)
        elif extension in METADATA_EXTENSIONS:
            pack.metadata_files.append(file_path)

    # Keep metadata-rich title if possible (derived from first metadata file).
    for pack in packs.values():
        if pack.metadata_files:
            pack.metadata = parse_metadata_file(pack.metadata_files[0]) or {}
            pack.title = extract_best_title(pack)

        if pack.text_files:
            pack.text_files.sort()
        if pack.ebook_files:
            pack.ebook_files.sort()
        if pack.audio_files:
            pack.audio_files.sort()

        if not (pack.metadata_files or pack.text_files or pack.ebook_files or pack.audio_files):
            LOGGER.debug("Empty pack for slug '%s' skipped", pack.slug)

    return packs


def extract_first(obj: Any, field_name: str) -> Optional[str]:
    lower_field = field_name.lower()
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key).lower() == lower_field:
                if isinstance(value, str):
                    return value.strip() if value.strip() else None
                if isinstance(value, (int, float)):
                    return str(value)
                if isinstance(value, list) and value:
                    return extract_first(value[0], field_name)
            found = extract_first(value, field_name)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = extract_first(item, field_name)
            if found:
                return found
    return None


def parse_xml_metadata(file_path: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    try:
        root = ET.parse(file_path).getroot()
    except Exception as exc:
        LOGGER.warning("Unable to parse XML metadata %s: %s", file_path, exc)
        return result

    def walk(node: ET.Element, prefix: str = "") -> None:
        tag = node.tag.split("}")[-1]
        value = (node.text or "").strip()
        key = f"{prefix}{tag}" if prefix else tag
        if value:
            result[key] = value
        for child in node:
            walk(child, f"{key}.")

    walk(root)
    return result


def parse_metadata_file(file_path: Path) -> Dict[str, Any]:
    ext = file_path.suffix.lower()
    try:
        with file_path.open("r", encoding="utf-8") as handle:
            raw = handle.read()
    except Exception as exc:
        LOGGER.warning("Unable to open metadata file %s: %s", file_path, exc)
        return {}

    if ext == ".json":
        try:
            return json.loads(raw)
        except Exception as exc:
            LOGGER.warning("Invalid JSON metadata %s: %s", file_path, exc)
            return {}
    if ext == ".xml":
        return parse_xml_metadata(file_path)
    return {}


def extract_best_title(pack: AssetPack) -> str:
    title = extract_first(pack.metadata, "title")
    if title:
        return title

    if pack.slug:
        normalized = pack.slug.replace("_", " ").strip()
        return normalized.title() or "Book"
    return "Book"


def validate_legal(pack: AssetPack) -> Tuple[bool, List[str]]:
    missing: List[str] = []
    legal_data = pack.metadata or {}

    for field in REQUIRED_LEGAL_FIELDS:
        value = extract_first(legal_data, field)
        if not value:
            missing.append(field)

    has_identifier = any(extract_first(legal_data, field) for field in IDENTIFIER_FIELDS)
    if not has_identifier:
        missing.append("isbn/issn")

    compliant = len(missing) == 0
    return compliant, missing


def ensure_utf8_text(text_path: Path) -> Tuple[bool, str, List[str]]:
    issues: List[str] = []
    try:
        raw = text_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        issues.append(f"{text_path.name}: not UTF-8 decodable")
        return False, "", issues
    except Exception as exc:
        issues.append(f"{text_path.name}: read failure ({exc})")
        return False, "", issues

    cleaned = normalize_text_content(raw)
    if not cleaned:
        issues.append(f"{text_path.name}: text became empty after sanitization")
    return True, cleaned, issues


def extract_epub_text(epub_path: Path) -> Tuple[bool, str, List[str]]:
    issues: List[str] = []
    try:
        with zipfile.ZipFile(epub_path, "r") as zf:
            candidate_html = [name for name in zf.namelist() if re.search(r"\.(x?html?|xml)$", name, re.I)]
            if not candidate_html:
                return False, "", [f"{epub_path.name}: no html/xml content found in EPUB"]

            parts: List[str] = []
            for name in sorted(candidate_html):
                data = zf.read(name)
                try:
                    text = data.decode("utf-8")
                except UnicodeDecodeError:
                    text = data.decode("utf-8", errors="replace")

                if BeautifulSoup is not None:
                    soup = BeautifulSoup(text, "lxml")
                    text = soup.get_text("\n")
                else:
                    text = re.sub(r"<[^>]+>", "\n", text)
                parts.append(normalize_text_content(text))

        combined = "\n\n".join([p for p in parts if p.strip()])
        if not combined:
            return False, "", [f"{epub_path.name}: EPUB parsing produced no text"]
        return True, combined, issues
    except Exception as exc:
        return False, "", [f"{epub_path.name}: EPUB extraction failure ({exc})"]


def get_mp3_bitrate_kbps(file_path: Path) -> Optional[float]:
    try:
        info = MP3(file_path)
        if not info.info:
            return None
        return info.info.bitrate / 1000.0
    except HeaderNotFoundError:
        return None
    except Exception:
        return None


def normalize_segment_lufs(segment: AudioSegment, target_lufs: float = TARGET_LUFS) -> AudioSegment:
    loudness = segment.dBFS
    if loudness == float("-inf"):
        return segment
    gain = target_lufs - loudness
    adjusted = segment.apply_gain(gain)
    # Avoid clipping after gain change.
    if adjusted.max_dBFS > -0.5:
        adjusted = adjusted.apply_gain(-((adjusted.max_dBFS + 0.5)))
    return adjusted


def process_audio_files(audio_paths: Sequence[Path], min_bitrate: int, target_lufs: float) -> Tuple[bool, Optional[AudioSegment], Dict[str, Any], List[str]]:
    issues: List[str] = []
    if not audio_paths:
        return False, None, {}, ["No MP3 file found"]

    normalized_tracks: List[AudioSegment] = []
    bitrate_values: List[int] = []
    combined_durations_ms = 0

    for path in sorted(audio_paths):
        bitrate = get_mp3_bitrate_kbps(path)
        if bitrate is None:
            issues.append(f"{path.name}: cannot read bitrate")
            return False, None, {}, issues

        if int(bitrate) < min_bitrate:
            issues.append(f"{path.name}: bitrate {int(bitrate)}kbps < {min_bitrate}kbps")
            return False, None, {}, issues

        try:
            track = AudioSegment.from_file(path)
        except Exception as exc:
            issues.append(f"{path.name}: audio decode failed ({exc})")
            return False, None, {}, issues

        normalized_tracks.append(normalize_segment_lufs(track, target_lufs=target_lufs))
        bitrate_values.append(int(bitrate))
        combined_durations_ms += len(track)

    if not normalized_tracks:
        return False, None, {}, ["No valid audio tracks to process"]

    merged = normalized_tracks[0]
    for track in normalized_tracks[1:]:
        merged += track

    report = {
        "track_count": len(normalized_tracks),
        "bitrate_kbps_min": min(bitrate_values),
        "bitrate_kbps_max": max(bitrate_values),
        "combined_duration_ms": combined_durations_ms,
        "target_lufs": target_lufs,
        "combined_audio_duration_ms": len(merged),
    }
    return True, merged, report, issues


def sha256_of_path(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def move_to_quarantine(pack: AssetPack, quarantine_root: Path, reason: str) -> None:
    target_dir = quarantine_root / clean_name_for_fs(pack.title)
    target_dir.mkdir(parents=True, exist_ok=True)

    seen: set[Path] = set()
    all_paths = pack.text_files + pack.ebook_files + pack.audio_files + pack.metadata_files
    if not all_paths and pack.deployment_file_paths:
        all_paths.extend(pack.deployment_file_paths)

    for source in all_paths:
        if source in seen or not source.exists():
            continue
        seen.add(source)
        destination = target_dir / source.name
        destination = destination.resolve()
        # Ensure each file stays unique in quarantine.
        if destination.exists():
            destination = target_dir / f"{source.stem}_copy{source.suffix}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), destination)
        pack.issues.append(f"moved_to_quarantine: {source} -> {destination}")

    pack.issues.append(f"quarantine_reason: {reason}")
    pack.status = "quarantined"


def write_text_output(text: str, output_dir: Path, title: str) -> Path:
    filename = f"{clean_name_for_fs(title)}_Text.txt"
    text_path = output_dir / filename
    text_path.write_text(text, encoding="utf-8")
    return text_path


def write_metadata_output(metadata: Dict[str, Any], output_dir: Path, title: str, processing_report: Dict[str, Any]) -> Path:
    payload = {
        "title": title,
        "metadata": metadata,
        "processing": processing_report,
    }
    filename = f"{clean_name_for_fs(title)}_Metadata.json"
    out = output_dir / filename
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def write_audio_output(audio: AudioSegment, output_dir: Path, title: str, bitrate: int = MIN_BITRATE_KBPS) -> Path:
    filename = f"{clean_name_for_fs(title)}_Audio.mp3"
    output_path = output_dir / filename
    audio.export(
        str(output_path),
        format="mp3",
        bitrate=f"{max(MIN_BITRATE_KBPS, bitrate)}k",
    )
    return output_path


def process_pack(
    pack: AssetPack,
    production_root: Path,
    quarantine_root: Path,
    min_bitrate_kbps: int = MIN_BITRATE_KBPS,
    target_lufs: float = TARGET_LUFS,
) -> AssetPack:
    LOGGER.info("Processing pack: %s", pack.title)
    pack.issues = []

    legal_ok, missing_legal = validate_legal(pack)
    if not legal_ok:
        pack.issues.append(f"compliance_missing_fields: {', '.join(missing_legal)}")

    if not pack.metadata:
        # Still try fallback parse from any available metadata file.
        for path in pack.metadata_files[:1]:
            parsed = parse_metadata_file(path)
            if parsed:
                pack.metadata = parsed
                break

    # Select text input source.
    selected_text_file: Optional[Path] = None
    selected_text: Optional[str] = None
    text_issues: List[str] = []

    if pack.text_files:
        selected_text_file = pack.text_files[0]
        ok_text, cleaned_text, text_issues = ensure_utf8_text(selected_text_file)
        if not ok_text:
            pack.issues.extend(text_issues)
        else:
            selected_text = cleaned_text

    # If no text file but EPUB exists, attempt extraction for strict UTF-8 content.
    elif pack.ebook_files:
        ok_text, extracted_text, text_issues = extract_epub_text(pack.ebook_files[0])
        if not ok_text:
            pack.issues.extend(text_issues)
        else:
            selected_text = extracted_text

    if not selected_text:
        pack.issues.append("content_missing: no valid UTF-8 text or EPUB reader text")

    # Process audio.
    audio_ok, normalized_audio, audio_report, audio_issues = process_audio_files(
        pack.audio_files,
        min_bitrate=min_bitrate_kbps,
        target_lufs=target_lufs,
    )
    if not audio_ok:
        pack.issues.extend(audio_issues)

    # Strict gate.
    required_minimum = (
        bool(pack.audio_files),
        bool(pack.ebook_files or pack.text_files),
        bool(pack.metadata_files),
        legal_ok,
        selected_text is not None,
        audio_ok,
    )
    if not all(required_minimum):
        move_to_quarantine(pack, quarantine_root, "failed_compliance_or_quality_gates")
        pack.status = "quarantined"
        pack.compliance["legal"] = {"status": "fail", "missing": missing_legal}
        pack.compliance["audio"] = {"status": "fail", "details": audio_report or audio_issues}
        pack.compliance["text"] = {"status": "fail", "details": text_issues}
        return pack

    # Write production-ready output.
    output_dir = production_root / clean_name_for_fs(pack.title)
    output_dir.mkdir(parents=True, exist_ok=True)

    text_output = write_text_output(selected_text, output_dir, pack.title)
    # Keep output bitrate near original for now; prefer original minimum floor.
    bitrate = min(audio_report.get("bitrate_kbps_min", MIN_BITRATE_KBPS), MIN_BITRATE_KBPS)
    audio_output = write_audio_output(normalized_audio, output_dir, pack.title, bitrate=min_bitrate_kbps)
    processing_report = {
        "legal": {
            "status": "pass",
            "missing": [],
            "metadata_fields": REQUIRED_LEGAL_FIELDS + ("isbn/issn",),
        },
        "text": {
            "status": "pass",
            "input_text_file": str(selected_text_file or pack.ebook_files[0]) if selected_text is not None else None,
            "sanitized": True,
            "charset": "UTF-8",
        },
        "audio": {
            "status": "pass",
            "details": audio_report,
            "source_count": len(pack.audio_files),
        },
    }
    metadata_output = write_metadata_output(pack.metadata, output_dir, pack.title, processing_report)

    pack.status = "ready"
    pack.deployment_file_paths = [text_output, audio_output, metadata_output]
    pack.compliance["legal"] = {"status": "pass", "missing": []}
    pack.compliance["audio"] = {"status": "pass", "details": audio_report}
    pack.compliance["text"] = {"status": "pass", "details": "utf-8 sanitized"}
    pack.compliance["artifacts"] = {
        "text": str(text_output),
        "audio": str(audio_output),
        "metadata": str(metadata_output),
        "hashes": {
            "text_sha256": sha256_of_path(text_output),
            "audio_sha256": sha256_of_path(audio_output),
            "metadata_sha256": sha256_of_path(metadata_output),
        },
    }
    return pack


def build_summary(results: Iterable[AssetPack]) -> Dict[str, int]:
    total = 0
    ready = 0
    quarantined = 0

    for pack in results:
        total += 1
        if pack.status == "ready":
            ready += 1
        elif pack.status == "quarantined":
            quarantined += 1

    return {
        "total_books_scanned": total,
        "passed_ready_to_go_live": ready,
        "quarantined_need_fix": quarantined,
    }


def write_compliance_report(results: Iterable[AssetPack], report_path: Path) -> None:
    payload = []
    for pack in results:
        payload.append(
            {
                "book_title": pack.title,
                "book_slug": pack.slug,
                "status": pack.status,
                "issues": pack.issues,
                "compliance": pack.compliance,
            }
        )
    report_path.write_text(
        json.dumps(
            {
                "total": len(payload),
                "items": payload,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="QA, sanitize, and prepare legacy Bengali assets for production.",
    )
    parser.add_argument(
        "--legacy-dir",
        default="/legacy_bengali_library",
        help="Legacy directory containing source files.",
    )
    parser.add_argument(
        "--production-dir",
        default="production_ready",
        help="Directory to write production-ready assets.",
    )
    parser.add_argument(
        "--quarantine-dir",
        default="quarantine",
        help="Directory for quarantined books that fail compliance/audit.",
    )
    parser.add_argument(
        "--report-path",
        default="compliance_report.json",
        help="Path for strict compliance report JSON.",
    )
    parser.add_argument(
        "--min-bitrate-kbps",
        type=int,
        default=128,
        help="Minimum allowed MP3 bitrate.",
    )
    parser.add_argument(
        "--target-lufs",
        type=float,
        default=TARGET_LUFS,
        help="Target loudness used for pydub normalization (dBFS approximation).",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable DEBUG logging.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    setup_logging(verbose=args.verbose)

    legacy_dir = Path(args.legacy_dir).expanduser().resolve()
    production_dir = Path(args.production_dir).expanduser().resolve()
    quarantine_dir = Path(args.quarantine_dir).expanduser().resolve()
    report_path = Path(args.report_path).expanduser().resolve()

    if not legacy_dir.exists():
        LOGGER.error("Legacy directory not found: %s", legacy_dir)
        return 1

    production_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    packs = gather_assets(legacy_dir)
    if not packs:
        LOGGER.warning("No compatible assets found in %s", legacy_dir)

    results: List[AssetPack] = []
    for pack in sorted(packs.values(), key=lambda item: item.slug):
        processed = process_pack(
            pack=pack,
            production_root=production_dir,
            quarantine_root=quarantine_dir,
            min_bitrate_kbps=args.min_bitrate_kbps,
            target_lufs=args.target_lufs,
        )
        results.append(processed)

    write_compliance_report(results, report_path)
    summary = build_summary(results)
    LOGGER.info("=== Pipeline summary ===")
    LOGGER.info("Total books scanned: %s", summary["total_books_scanned"])
    LOGGER.info("Passed (Ready to Go Live): %s", summary["passed_ready_to_go_live"])
    LOGGER.info("Quarantined (Needs Legal/Audio Fixes): %s", summary["quarantined_need_fix"])
    LOGGER.info("Compliance report written to: %s", report_path)

    if summary["quarantined_need_fix"]:
        LOGGER.warning("Some books require manual legal/quality review. Check quarantine folder.")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
