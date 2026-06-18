from __future__ import annotations

import csv
import io
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable


AUDIOBOOK_PIPELINE_VERSION = "earnalism-audiobook-voice-v1"
VOICE_IDENTITY = (
    "A refined female literary narrator: warm, intelligent, calm, expressive, "
    "punctuation-aware, emotionally restrained, suitable for Bengali, English, and Hindi."
)

SUPPORTED_LANGUAGES = {"bn", "en", "hi"}
SUPPORTED_PROVIDERS = ("openai_tts", "ai4bharat_indic_tts", "piper_local_tts", "manual_audio_upload")
SUPPORTED_MODES = ("preview_30s", "preview_90s", "preview_3m", "chapter_audio", "full_audiobook_playlist")
ALLOWED_EDITION_STATUSES = {"READY_FOR_REVIEW", "PARTIAL_DRY_RUN", "QA_PASSED"}

MODE_LIMITS = {
    "preview_30s": {"estimated_seconds": 30, "max_chunks": 1, "max_chars": 650},
    "preview_90s": {"estimated_seconds": 90, "max_chunks": 2, "max_chars": 1800},
    "preview_3m": {"estimated_seconds": 180, "max_chunks": 4, "max_chars": 3600},
    "chapter_audio": {"estimated_seconds": 0, "max_chunks": 12, "max_chars": 12_000},
    "full_audiobook_playlist": {"estimated_seconds": 0, "max_chunks": 1_000, "max_chars": 1_000_000},
}

PUNCTUATION_PAUSES_MS = {
    ".": 420,
    "?": 470,
    "!": 480,
    ",": 180,
    ";": 260,
    ":": 260,
    "।": 420,
    "॥": 520,
}

LANGUAGE_RANGES = {
    "bn": re.compile(r"[\u0980-\u09FF]"),
    "hi": re.compile(r"[\u0900-\u097F]"),
    "en": re.compile(r"[A-Za-z]"),
}

SENTENCE_RE = re.compile(r"[^.!?।॥]+[.!?।॥]?")
CHAPTER_HEADING_RE = re.compile(
    r"^\s*((chapter|book|part)\s+\w+|অধ্যায়\s+\S+|পরিচ্ছেদ\s+\S+|अध्याय\s+\S+|भाग\s+\S+)\s*$",
    re.IGNORECASE,
)
QUOTE_RE = re.compile(r"[\"“”‘’'«»]|(^|\s)[—-]\s*\S")


@dataclass
class PronunciationDictionary:
    terms: dict[str, str] = field(default_factory=dict)

    def apply(self, text: str) -> tuple[str, dict[str, int]]:
        normalized = text
        replacements: dict[str, int] = {}
        for term, replacement in sorted(self.terms.items(), key=lambda item: len(item[0]), reverse=True):
            if not term:
                continue
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            normalized, count = pattern.subn(replacement, normalized)
            if count:
                replacements[term] = count
        return normalized, replacements


@dataclass
class NarrationChunk:
    index: int
    text: str
    language: str
    segment_type: str
    chapter_title: str
    estimated_seconds: float
    punctuation_pauses_ms: list[int]
    pronunciation_replacements: dict[str, int] = field(default_factory=dict)

    def as_dict(self, *, include_text: bool = False, text_preview_chars: int = 320) -> dict[str, Any]:
        row = {
            "index": self.index,
            "language": self.language,
            "segment_type": self.segment_type,
            "chapter_title": self.chapter_title,
            "estimated_seconds": round(self.estimated_seconds, 2),
            "punctuation_pause_count": len(self.punctuation_pauses_ms),
            "punctuation_pauses_ms": self.punctuation_pauses_ms,
            "pronunciation_replacements": self.pronunciation_replacements,
            "text_preview": self.text[: max(0, int(text_preview_chars or 0))],
            "character_count": len(self.text),
        }
        if include_text:
            row["text"] = self.text
        return row


@dataclass
class NarrationScriptResult:
    language: str
    chunks: list[NarrationChunk]
    chapter_count: int
    dialogue_chunk_count: int
    poetry_chunk_count: int
    pronunciation_replacement_count: int
    processor_warnings: list[str]

    def as_dict(self, *, include_text: bool = False, text_preview_chars: int = 320) -> dict[str, Any]:
        return {
            "language": self.language,
            "chunk_count": len(self.chunks),
            "chapter_count": self.chapter_count,
            "dialogue_chunk_count": self.dialogue_chunk_count,
            "poetry_chunk_count": self.poetry_chunk_count,
            "pronunciation_replacement_count": self.pronunciation_replacement_count,
            "processor_warnings": self.processor_warnings,
            "chunks": [
                chunk.as_dict(include_text=include_text, text_preview_chars=text_preview_chars) for chunk in self.chunks
            ],
        }


@dataclass
class TTSProviderPlan:
    provider: str
    voice_profile: str
    language: str
    credentials_configured: bool
    supports_ssml: bool
    dry_run_only: bool
    hook: str
    blocking_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "voice_profile": self.voice_profile,
            "language": self.language,
            "credentials_configured": self.credentials_configured,
            "supports_ssml": self.supports_ssml,
            "dry_run_only": self.dry_run_only,
            "hook": self.hook,
            "blocking_reason": self.blocking_reason,
        }


@dataclass
class MasteringPlan:
    loudness_normalization: str
    silence_trimming: str
    output_formats: list[str]
    waveform_preview: str
    ffmpeg_commands: list[str]
    executed: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "loudness_normalization": self.loudness_normalization,
            "silence_trimming": self.silence_trimming,
            "output_formats": self.output_formats,
            "waveform_preview": self.waveform_preview,
            "ffmpeg_commands": self.ffmpeg_commands,
            "executed": self.executed,
        }


@dataclass
class AudioQAMetrics:
    stt_transcript_comparison: str = "HOOK_NOT_RUN"
    word_error_rate: float | None = None
    missing_paragraph_count: int = 0
    repeated_line_count: int = 0
    clipping_detected: bool = False
    long_silence_detected: bool = False
    file_size_bytes: int = 0


@dataclass
class AudioQAResult:
    qa_status: str
    issues: list[str]
    metrics: AudioQAMetrics

    def as_dict(self) -> dict[str, Any]:
        return {
            "qa_status": self.qa_status,
            "issues": self.issues,
            "metrics": {
                "stt_transcript_comparison": self.metrics.stt_transcript_comparison,
                "word_error_rate": self.metrics.word_error_rate,
                "missing_paragraph_count": self.metrics.missing_paragraph_count,
                "repeated_line_count": self.metrics.repeated_line_count,
                "clipping_detected": self.metrics.clipping_detected,
                "long_silence_detected": self.metrics.long_silence_detected,
                "file_size_bytes": self.metrics.file_size_bytes,
            },
        }


@dataclass
class AudiobookPipelineInput:
    book_slug: str
    title: str
    source_text: str
    language: str = ""
    generation_mode: str = "preview_90s"
    provider: str = "manual_audio_upload"
    dry_run: bool = True
    linked_approved_book: bool = False
    rights_tier: str = ""
    verification_status: str = ""
    blocked_reason: str = ""
    action_status: str = ""
    ingestion_status: str = ""
    edition_generation_status: str = ""
    source_hash: str = ""
    content_hash: str = ""
    provenance_hash: str = ""
    qa_metrics: AudioQAMetrics | None = None
    pronunciation_dictionary: dict[str, str] = field(default_factory=dict)
    max_chunk_chars: int = 900


@dataclass
class AudiobookPipelineResult:
    book_slug: str
    title: str
    generation_mode: str
    generation_status: str
    publish_gate_status: str
    blocking_reason: str
    dry_run: bool
    rights_tier: str
    action_status: str
    ingestion_status: str
    edition_generation_status: str
    source_hash: str
    content_hash: str
    provenance_hash: str
    voice_identity: str
    narration_script: NarrationScriptResult
    provider_plan: TTSProviderPlan
    mastering_plan: MasteringPlan
    qa: AudioQAResult
    planned_audio_assets: list[dict[str, Any]]
    pipeline_version: str = AUDIOBOOK_PIPELINE_VERSION

    def as_dict(self, *, include_text: bool = False, text_preview_chars: int = 320) -> dict[str, Any]:
        return {
            "book_slug": self.book_slug,
            "title": self.title,
            "generation_mode": self.generation_mode,
            "generation_status": self.generation_status,
            "publish_gate_status": self.publish_gate_status,
            "blocking_reason": self.blocking_reason,
            "dry_run": self.dry_run,
            "rights_tier": self.rights_tier,
            "action_status": self.action_status,
            "ingestion_status": self.ingestion_status,
            "edition_generation_status": self.edition_generation_status,
            "source_hash": self.source_hash,
            "content_hash": self.content_hash,
            "provenance_hash": self.provenance_hash,
            "voice_identity": self.voice_identity,
            "narration_script": self.narration_script.as_dict(
                include_text=include_text,
                text_preview_chars=text_preview_chars,
            ),
            "provider_plan": self.provider_plan.as_dict(),
            "mastering_plan": self.mastering_plan.as_dict(),
            "qa": self.qa.as_dict(),
            "planned_audio_assets": self.planned_audio_assets,
            "pipeline_version": self.pipeline_version,
        }


def process_narration_script(
    text: str,
    *,
    language: str = "",
    pronunciation_dictionary: dict[str, str] | None = None,
    max_chunk_chars: int = 900,
    mode: str = "preview_90s",
) -> NarrationScriptResult:
    detected_language = normalize_language(language) or detect_language(text)
    dictionary = PronunciationDictionary(pronunciation_dictionary or {})
    normalized_text, replacements = dictionary.apply(normalize_text(text))
    mode_limits = MODE_LIMITS.get(normalize_mode(mode), MODE_LIMITS["preview_90s"])
    max_chars = min(max(200, max_chunk_chars), int(mode_limits["max_chars"]))

    lines = normalized_text.splitlines()
    chunks: list[NarrationChunk] = []
    chapter_title = ""
    chapter_count = 0
    pending_paragraph: list[str] = []

    def flush_pending() -> None:
        nonlocal pending_paragraph
        paragraph = "\n".join(pending_paragraph).strip()
        pending_paragraph = []
        if not paragraph:
            return
        for piece in chunk_paragraph(paragraph, max_chars=max_chars):
            segment_type = classify_segment(piece)
            chunks.append(
                NarrationChunk(
                    index=len(chunks) + 1,
                    text=piece,
                    language=detected_language,
                    segment_type=segment_type,
                    chapter_title=chapter_title,
                    estimated_seconds=estimate_seconds(piece, detected_language),
                    punctuation_pauses_ms=punctuation_pauses(piece),
                    pronunciation_replacements=replacements if len(chunks) == 0 else {},
                )
            )

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_pending()
            continue
        if CHAPTER_HEADING_RE.match(stripped):
            flush_pending()
            chapter_count += 1
            chapter_title = stripped
            chunks.append(
                NarrationChunk(
                    index=len(chunks) + 1,
                    text=stripped,
                    language=detected_language,
                    segment_type="chapter_heading",
                    chapter_title=chapter_title,
                    estimated_seconds=estimate_seconds(stripped, detected_language),
                    punctuation_pauses_ms=[650],
                )
            )
            continue
        pending_paragraph.append(stripped)
    flush_pending()

    limited_chunks = chunks[: int(mode_limits["max_chunks"])]
    warnings = []
    if len(chunks) > len(limited_chunks):
        warnings.append(f"Mode {normalize_mode(mode)} limited narration chunks from {len(chunks)} to {len(limited_chunks)}.")
    if detected_language not in SUPPORTED_LANGUAGES:
        warnings.append("Language was not confidently detected; defaulted to English.")

    return NarrationScriptResult(
        language=detected_language if detected_language in SUPPORTED_LANGUAGES else "en",
        chunks=limited_chunks,
        chapter_count=chapter_count,
        dialogue_chunk_count=sum(1 for chunk in limited_chunks if chunk.segment_type == "dialogue"),
        poetry_chunk_count=sum(1 for chunk in limited_chunks if chunk.segment_type == "poetry"),
        pronunciation_replacement_count=sum(replacements.values()),
        processor_warnings=warnings,
    )


def plan_audiobook_pipeline(payload: AudiobookPipelineInput) -> AudiobookPipelineResult:
    mode = normalize_mode(payload.generation_mode)
    publish_gate_status, blocking_reason = evaluate_publish_gate(payload)
    if publish_gate_status != "DRY_RUN_ONLY":
        return blocked_pipeline_result(payload, mode, publish_gate_status, blocking_reason)

    script = process_narration_script(
        payload.source_text,
        language=payload.language,
        pronunciation_dictionary=payload.pronunciation_dictionary,
        max_chunk_chars=payload.max_chunk_chars,
        mode=mode,
    )
    provider_plan = plan_tts_provider(payload.provider, script.language)
    mastering_plan = build_mastering_plan(payload.book_slug, mode)
    qa = evaluate_audio_qa(payload.qa_metrics, dry_run=payload.dry_run)
    generation_status = "DRY_RUN_READY"
    planned_assets = planned_audio_assets(payload.book_slug, mode, script, mastering_plan)
    return AudiobookPipelineResult(
        book_slug=payload.book_slug,
        title=payload.title,
        generation_mode=mode,
        generation_status=generation_status,
        publish_gate_status=publish_gate_status,
        blocking_reason=blocking_reason,
        dry_run=payload.dry_run,
        rights_tier=normalize_rights_tier(payload.rights_tier),
        action_status=normalize_status(payload.action_status),
        ingestion_status=normalize_status(payload.ingestion_status),
        edition_generation_status=normalize_status(payload.edition_generation_status),
        source_hash=payload.source_hash,
        content_hash=payload.content_hash,
        provenance_hash=payload.provenance_hash,
        voice_identity=VOICE_IDENTITY,
        narration_script=script,
        provider_plan=provider_plan,
        mastering_plan=mastering_plan,
        qa=qa,
        planned_audio_assets=planned_assets,
    )


def blocked_pipeline_result(
    payload: AudiobookPipelineInput,
    mode: str,
    publish_gate_status: str,
    blocking_reason: str,
) -> AudiobookPipelineResult:
    language = normalize_language(payload.language) or detect_language(payload.source_text)
    return AudiobookPipelineResult(
        book_slug=payload.book_slug,
        title=payload.title,
        generation_mode=mode,
        generation_status=publish_gate_status,
        publish_gate_status=publish_gate_status,
        blocking_reason=blocking_reason,
        dry_run=payload.dry_run,
        rights_tier=normalize_rights_tier(payload.rights_tier),
        action_status=normalize_status(payload.action_status),
        ingestion_status=normalize_status(payload.ingestion_status),
        edition_generation_status=normalize_status(payload.edition_generation_status),
        source_hash=payload.source_hash,
        content_hash=payload.content_hash,
        provenance_hash=payload.provenance_hash,
        voice_identity=VOICE_IDENTITY,
        narration_script=NarrationScriptResult(
            language=language if language in SUPPORTED_LANGUAGES else "en",
            chunks=[],
            chapter_count=0,
            dialogue_chunk_count=0,
            poetry_chunk_count=0,
            pronunciation_replacement_count=0,
            processor_warnings=[blocking_reason],
        ),
        provider_plan=plan_tts_provider(payload.provider, language),
        mastering_plan=build_mastering_plan(payload.book_slug, mode),
        qa=AudioQAResult(
            qa_status="BLOCKED_GATE",
            issues=[blocking_reason],
            metrics=payload.qa_metrics or AudioQAMetrics(),
        ),
        planned_audio_assets=[],
    )


def plan_tts_provider(provider: str, language: str) -> TTSProviderPlan:
    provider_key = normalize_provider(provider)
    credentials = provider_credentials_configured(provider_key)
    if provider_key == "openai_tts":
        return TTSProviderPlan(
            provider=provider_key,
            voice_profile="female_literary_alloy_or_configured_voice",
            language=language,
            credentials_configured=credentials,
            supports_ssml=False,
            dry_run_only=not credentials,
            hook="OpenAI TTS hook: build provider request payload only in dry-run.",
            blocking_reason="" if credentials else "OPENAI_API_KEY is not configured.",
        )
    if provider_key == "ai4bharat_indic_tts":
        return TTSProviderPlan(
            provider=provider_key,
            voice_profile="female_indic_literary_narrator",
            language=language,
            credentials_configured=credentials,
            supports_ssml=False,
            dry_run_only=not credentials,
            hook="AI4Bharat/Indic TTS hook: local or configured provider command metadata only.",
            blocking_reason="" if credentials else "AI4BHARAT_TTS_ENDPOINT or INDIC_TTS_COMMAND is not configured.",
        )
    if provider_key == "piper_local_tts":
        return TTSProviderPlan(
            provider=provider_key,
            voice_profile="configured_local_female_voice",
            language=language,
            credentials_configured=credentials,
            supports_ssml=False,
            dry_run_only=not credentials,
            hook="Piper/local TTS hook: command metadata only; no subprocess execution in Phase 7.",
            blocking_reason="" if credentials else "PIPER_MODEL_PATH or PIPER_TTS_COMMAND is not configured.",
        )
    return TTSProviderPlan(
        provider="manual_audio_upload",
        voice_profile="human_or_external_refined_female_literary_narrator",
        language=language,
        credentials_configured=True,
        supports_ssml=False,
        dry_run_only=False,
        hook="Manual audio upload fallback: validate uploaded audio through QA before any publish.",
    )


def evaluate_audio_qa(metrics: AudioQAMetrics | None, *, dry_run: bool) -> AudioQAResult:
    if metrics is None:
        return AudioQAResult(
            qa_status="DRY_RUN_PENDING_AUDIO",
            issues=["No audio file was generated or uploaded; QA hooks are planned only."],
            metrics=AudioQAMetrics(),
        )

    issues: list[str] = []
    if metrics.word_error_rate is None:
        issues.append("STT word error rate is missing.")
    elif metrics.word_error_rate > 0.08:
        issues.append("STT word error rate exceeds 8%.")
    if metrics.missing_paragraph_count:
        issues.append("Missing paragraph detected.")
    if metrics.repeated_line_count:
        issues.append("Repeated line detected.")
    if metrics.clipping_detected:
        issues.append("Clipping detected.")
    if metrics.long_silence_detected:
        issues.append("Long silence detected.")
    if metrics.file_size_bytes <= 0:
        issues.append("Audio file size is missing.")
    status = "PASS" if not issues else "FAIL"
    if dry_run and metrics.file_size_bytes <= 0 and status == "FAIL":
        status = "DRY_RUN_PENDING_AUDIO"
    return AudioQAResult(qa_status=status, issues=issues, metrics=metrics)


def evaluate_publish_gate(payload: AudiobookPipelineInput) -> tuple[str, str]:
    if payload.dry_run is not True:
        return "BLOCKED_NON_DRY_RUN", "Phase 7 audiobook voice pipeline is dry-run only."

    rights_tier = normalize_rights_tier(payload.rights_tier)
    verification_status = normalize_status(payload.verification_status)
    action_status = normalize_status(payload.action_status)
    ingestion_status = normalize_status(payload.ingestion_status)
    edition_status = normalize_status(payload.edition_generation_status)

    if rights_tier == "C":
        return "BLOCKED_RIGHTS", "Tier C rights block audiobook planning."
    if rights_tier in {"", "UNKNOWN", "NO", "MISSING"} or verification_status not in {"APPROVED", "VERIFIED"}:
        return "BLOCKED_RIGHTS_REVIEW_REQUIRED", "Approved Tier A rights metadata is required before audiobook planning."
    if rights_tier == "B":
        return "REGION_GATED_REVIEW", "Tier B rights require region-gated review before audiobook planning."
    if rights_tier != "A":
        return "BLOCKED_RIGHTS_REVIEW_REQUIRED", "Unknown rights tier requires Phase 2 rights review."
    if str(payload.blocked_reason or "").strip():
        return "BLOCKED_RIGHTS", f"Rights blocked_reason must be cleared: {payload.blocked_reason}"
    if action_status != "READY_FOR_GENERATION":
        return "BLOCKED_PRIORITY_GATE", "Phase 3 action_status must be READY_FOR_GENERATION."
    if ingestion_status not in {"INGESTED", "CLEANED"}:
        return "BLOCKED_INGESTION", "Phase 4 ingestion_status must be INGESTED or CLEANED."
    if edition_status not in ALLOWED_EDITION_STATUSES:
        return "BLOCKED_EDITION_GATE", "Phase 5 edition_generation_status must be ready, partial dry-run, or QA passed."
    if not str(payload.source_hash or "").strip():
        return "BLOCKED_TRACEABILITY", "source_hash is required."
    if not str(payload.content_hash or "").strip() or not str(payload.provenance_hash or "").strip():
        return "BLOCKED_TRACEABILITY", "content_hash and provenance_hash are required."
    if not str(payload.source_text or "").strip():
        return "BLOCKED_SOURCE_TEXT", "source_text is required before audiobook planning."
    return "DRY_RUN_ONLY", "Phase 7 does not publish audio; dry-run report only."


def build_mastering_plan(book_slug: str, mode: str) -> MasteringPlan:
    safe_slug = safe_audio_slug(book_slug or "untitled")
    input_file = f"work/audio/{safe_slug}/{mode}/raw.wav"
    output_stem = f"work/audio/{safe_slug}/{mode}/mastered"
    return MasteringPlan(
        loudness_normalization="EBU R128 target -16 LUFS integrated, -1.5 dBTP true peak",
        silence_trimming="trim leading/trailing silence below -45 dB for longer than 0.35 seconds",
        output_formats=["mp3", "aac", "ogg"],
        waveform_preview=f"{output_stem}.waveform.json",
        ffmpeg_commands=[
            (
                "ffmpeg -i {input} -af "
                "loudnorm=I=-16:TP=-1.5:LRA=11,silenceremove=start_periods=1:start_threshold=-45dB:"
                "stop_periods=1:stop_threshold=-45dB {output}.mp3"
            ).format(input=input_file, output=output_stem),
            f"ffmpeg -i {output_stem}.mp3 -c:a aac {output_stem}.m4a",
            f"ffmpeg -i {output_stem}.mp3 -c:a libopus {output_stem}.ogg",
            f"ffmpeg -i {output_stem}.mp3 -filter_complex showwavespic=s=1200x240 {output_stem}.waveform.png",
        ],
        executed=False,
    )


def planned_audio_assets(
    book_slug: str,
    mode: str,
    script: NarrationScriptResult,
    mastering_plan: MasteringPlan,
) -> list[dict[str, Any]]:
    safe_slug = safe_audio_slug(book_slug or "untitled")
    base = f"dry-run/audio/{safe_slug}/{mode}"
    return [
        {"asset_type": "master_mp3", "path": f"{base}/mastered.mp3", "publishable": False},
        {"asset_type": "master_aac", "path": f"{base}/mastered.m4a", "publishable": False},
        {"asset_type": "master_ogg", "path": f"{base}/mastered.ogg", "publishable": False},
        {"asset_type": "waveform_preview", "path": mastering_plan.waveform_preview, "publishable": False},
        {"asset_type": "playlist", "path": f"{base}/playlist.json", "chunk_count": len(script.chunks), "publishable": False},
    ]


def normalize_text(text: str) -> str:
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def chunk_paragraph(paragraph: str, *, max_chars: int) -> list[str]:
    sentences = [match.group(0).strip() for match in SENTENCE_RE.finditer(paragraph) if match.group(0).strip()]
    if not sentences:
        return [paragraph[:max_chars]]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip()
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def classify_segment(text: str) -> str:
    stripped = text.strip()
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    if CHAPTER_HEADING_RE.match(stripped):
        return "chapter_heading"
    if QUOTE_RE.search(stripped):
        return "dialogue"
    if len(lines) >= 2 and all(len(line) <= 72 for line in lines):
        return "poetry"
    return "narration"


def punctuation_pauses(text: str) -> list[int]:
    return [PUNCTUATION_PAUSES_MS[char] for char in text if char in PUNCTUATION_PAUSES_MS]


def estimate_seconds(text: str, language: str) -> float:
    words = max(1, len(re.findall(r"\w+|[\u0980-\u09FF]+|[\u0900-\u097F]+", text)))
    words_per_minute = 138 if language in {"bn", "hi"} else 152
    pause_seconds = sum(punctuation_pauses(text)) / 1000
    return (words / words_per_minute) * 60 + pause_seconds


def detect_language(text: str) -> str:
    counts = {language: len(pattern.findall(text or "")) for language, pattern in LANGUAGE_RANGES.items()}
    if counts["bn"] >= max(counts["hi"], counts["en"], 1):
        return "bn"
    if counts["hi"] >= max(counts["bn"], counts["en"], 1):
        return "hi"
    return "en"


def normalize_language(language: str) -> str:
    value = str(language or "").strip().lower()
    aliases = {
        "bengali": "bn",
        "bangla": "bn",
        "ben": "bn",
        "bn-in": "bn",
        "english": "en",
        "eng": "en",
        "en-in": "en",
        "hindi": "hi",
        "hin": "hi",
        "hi-in": "hi",
    }
    return aliases.get(value, value if value in SUPPORTED_LANGUAGES else "")


def normalize_mode(mode: str) -> str:
    value = str(mode or "").strip().lower().replace("-", "_")
    aliases = {"30s": "preview_30s", "90s": "preview_90s", "3m": "preview_3m", "full": "full_audiobook_playlist"}
    return aliases.get(value, value if value in SUPPORTED_MODES else "preview_90s")


def normalize_provider(provider: str) -> str:
    value = str(provider or "").strip().lower().replace("-", "_")
    aliases = {
        "openai": "openai_tts",
        "ai4bharat": "ai4bharat_indic_tts",
        "indic": "ai4bharat_indic_tts",
        "piper": "piper_local_tts",
        "local": "piper_local_tts",
        "manual": "manual_audio_upload",
    }
    return aliases.get(value, value if value in SUPPORTED_PROVIDERS else "manual_audio_upload")


def normalize_rights_tier(value: str) -> str:
    text = str(value or "").strip().upper()
    if text.startswith("TIER "):
        text = text.replace("TIER ", "", 1).strip()
    return text


def normalize_status(value: str) -> str:
    return str(value or "").strip().upper().replace("-", "_").replace(" ", "_")


def provider_credentials_configured(provider: str) -> bool:
    if provider == "openai_tts":
        return bool(os.environ.get("OPENAI_API_KEY"))
    if provider == "ai4bharat_indic_tts":
        return bool(os.environ.get("AI4BHARAT_TTS_ENDPOINT") or os.environ.get("INDIC_TTS_COMMAND"))
    if provider == "piper_local_tts":
        return bool(os.environ.get("PIPER_MODEL_PATH") or os.environ.get("PIPER_TTS_COMMAND"))
    return True


def safe_audio_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value or "").strip().lower()).strip("-")
    return slug or "untitled"


def audiobook_report_json(
    result: AudiobookPipelineResult,
    *,
    include_text: bool = False,
    text_preview_chars: int = 320,
) -> dict[str, Any]:
    return result.as_dict(include_text=include_text, text_preview_chars=text_preview_chars)


def audiobook_report_csv(result: AudiobookPipelineResult) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "book_slug",
            "title",
            "generation_mode",
            "generation_status",
            "publish_gate_status",
            "blocking_reason",
            "rights_tier",
            "action_status",
            "ingestion_status",
            "edition_generation_status",
            "source_hash",
            "content_hash",
            "provenance_hash",
            "language",
            "provider",
            "credentials_configured",
            "qa_status",
            "chunk_count",
            "planned_asset_count",
            "dry_run",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {
            "book_slug": result.book_slug,
            "title": result.title,
            "generation_mode": result.generation_mode,
            "generation_status": result.generation_status,
            "publish_gate_status": result.publish_gate_status,
            "blocking_reason": result.blocking_reason,
            "rights_tier": result.rights_tier,
            "action_status": result.action_status,
            "ingestion_status": result.ingestion_status,
            "edition_generation_status": result.edition_generation_status,
            "source_hash": result.source_hash,
            "content_hash": result.content_hash,
            "provenance_hash": result.provenance_hash,
            "language": result.narration_script.language,
            "provider": result.provider_plan.provider,
            "credentials_configured": result.provider_plan.credentials_configured,
            "qa_status": result.qa.qa_status,
            "chunk_count": len(result.narration_script.chunks),
            "planned_asset_count": len(result.planned_audio_assets),
            "dry_run": result.dry_run,
        }
    )
    return output.getvalue()


def audiobook_report_markdown(
    result: AudiobookPipelineResult,
    *,
    include_text: bool = False,
    text_preview_chars: int = 320,
) -> str:
    payload = result.as_dict(include_text=include_text, text_preview_chars=text_preview_chars)
    lines = [
        "# Audiobook Voice Pipeline Dry-Run Report",
        "",
        f"- Book: `{result.book_slug}` - {result.title}",
        f"- Mode: `{result.generation_mode}`",
        f"- Status: `{result.generation_status}`",
        f"- Publish gate: `{result.publish_gate_status}`",
        f"- Blocking reason: {result.blocking_reason or 'none'}",
        f"- Rights tier: `{result.rights_tier or 'unknown'}`",
        f"- Phase 3 action: `{result.action_status or 'unknown'}`",
        f"- Phase 4 ingestion: `{result.ingestion_status or 'unknown'}`",
        f"- Phase 5 edition: `{result.edition_generation_status or 'unknown'}`",
        f"- Voice identity: {VOICE_IDENTITY}",
        f"- Provider: `{result.provider_plan.provider}`",
        f"- QA: `{result.qa.qa_status}`",
        f"- Chunks: {len(result.narration_script.chunks)}",
        f"- Dry run: `{str(result.dry_run).lower()}`",
        "",
        "## Planned Assets",
    ]
    for asset in result.planned_audio_assets:
        lines.append(f"- `{asset['asset_type']}`: `{asset['path']}`")
    lines.extend(["", "## Narration Chunks"])
    for chunk in payload["narration_script"]["chunks"]:
        label = "Text" if include_text else "Preview"
        text = chunk.get("text") if include_text else chunk.get("text_preview")
        lines.append(f"- Chunk {chunk['index']} `{chunk['segment_type']}` {label}: {text}")
    lines.extend(["", "## QA Issues"])
    if result.qa.issues:
        lines.extend(f"- {issue}" for issue in result.qa.issues)
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"
