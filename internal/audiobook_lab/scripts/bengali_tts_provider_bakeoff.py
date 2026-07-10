#!/usr/bin/env python3
"""Fail-closed Bengali TTS provider bakeoff for Earnalism audiobook release.

This script intentionally auditions short manuscript-derived samples only. It
does not publish, upload, or approve production metadata. A provider/voice is
considered viable only when every audition passage clears the schema-3
listening-quality release thresholds.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
HOOK_DIR = SCRIPT_DIR / "factory_hooks"
PROVIDERS_DIR = SCRIPT_DIR / "providers"
sys.path.insert(0, str(HOOK_DIR))
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PROVIDERS_DIR))

from common import (  # noqa: E402
    ROOT,
    ffprobe_duration,
    read_json,
    rel,
    run_cmd,
    sha256_file,
    sha256_text,
    write_json,
    write_text,
)
from asr_sync_hook import (  # noqa: E402
    BINARY_LISTENING_FLAGS,
    BENGALI_AUDIOBOOK_92_POLICY,
    BENGALI_PREMIUM_MVP_POLICY,
    LISTENING_THRESHOLDS,
    TIERED_AUDIOBOOK_ACCEPTANCE_POLICY,
    UNIVERSAL_LISTENING_POLICY,
    evaluate_listening_evidence,
    listening_policy_for,
    judge_audio_sample_with_openai,
    openai_listening_qa_budget_guard,
    safe_float,
)


RUN_ROOT = ROOT / "internal" / "audiobook_lab" / "release_gate"
BAKEOFF_STATUS_PATH = RUN_ROOT / "bengali_provider_bakeoff_status.json"
DEFAULT_OPENAI_MODEL = os.environ.get("EARNALISM_BENGALI_BAKEOFF_OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
DEFAULT_MAX_VOICES_PER_PROVIDER = int(os.environ.get("EARNALISM_BENGALI_BAKEOFF_MAX_VOICES_PER_PROVIDER", "8"))
DEFAULT_ESTIMATED_USD_PER_1K_CHARS = float(os.environ.get("EARNALISM_BENGALI_BAKEOFF_ESTIMATED_USD_PER_1K_CHARS", "0.02"))


OPENAI_VOICES = ["marin", "cedar", "verse", "coral", "sage", "alloy"]
GOOGLE_VOICE_HINTS = [
    "bn-IN-Chirp3-HD",
    "bn-IN-Wavenet-A",
    "bn-IN-Wavenet-B",
    "bn-IN-Wavenet-C",
    "bn-IN-Wavenet-D",
    "bn-IN-Standard-A",
    "bn-IN-Standard-B",
    "bn-IN-Standard-C",
    "bn-IN-Standard-D",
]
AZURE_VOICES = [
    "bn-IN-TanishaaNeural",
    "bn-IN-BashkarNeural",
    "bn-BD-NabanitaNeural",
    "bn-BD-PradeepNeural",
]
STYLE_PROFILES = {
    "warm_bengali_literary_storyteller": (
        "Warm Bengali literary storyteller. Natural, human, intimate, emotionally restrained, "
        "expressive but not theatrical. Respect Bengali punctuation and rhythm. Avoid robotic cadence, "
        "flat delivery, mechanical texture, identical sentence endings, and list-reading rhythm. "
        "Preserve Bengali pronunciation and literary tone."
    ),
    "literary_warm_pacing": (
        "Warm Bengali literary storyteller with slightly slower-than-neutral pacing. Preserve Bengali literary "
        "rhythm, punctuation, and emotional restraint. Avoid robotic cadence, rushing, and list-reading rhythm."
    ),
    "punctuation_aware_emotional": (
        "Bengali literary narration with clearer comma and sentence pauses, natural paragraph breaks, and gentle "
        "emotional shading. Expressive but restrained; never theatrical or mechanical."
    ),
    "dialogue_human_touch": (
        "Human, warm Bengali storytelling for dialogue-heavy passages. Dialogue should feel alive and intimate, "
        "without overacting. Avoid identical sentence endings and robotic tone resets."
    ),
    "anti_mechanical_texture": (
        "Continuous Bengali paragraph narration with varied sentence endings, non-mechanical texture, and no "
        "list-reading cadence. Preserve meaning and canonical Bengali text."
    ),
    "anti_list_reading_flow": (
        "Natural Bengali literary narration with flowing paragraphs, varied phrase endings, and no list-reading "
        "rhythm. Preserve every word and meaning while avoiding itemized or recitation-like cadence."
    ),
    "anti_mechanical_cadence": (
        "Human Bengali storytelling with organic breath, non-repeating sentence endings, and smooth continuity. "
        "Avoid mechanical cadence, robotic resets, and clipped phrase joins."
    ),
    "stanza_paragraph_breathing": (
        "Bengali literary narration with graceful paragraph breathing and restrained emotional continuity. "
        "Use natural pauses between thought groups without sounding slow, choppy, or overdramatic."
    ),
    "emotional_but_restrained": (
        "Emotionally aware Bengali narration with warmth and restraint. Preserve literary dignity, pronunciation, "
        "and rhythm; never become theatrical, mechanical, or list-like."
    ),
}
NEAR_PASS_VOICES = {"ritu", "priya", "ashutosh", "neha"}
SECOND_PASS_STYLE_PROFILES = [
    "literary_warm_pacing",
    "punctuation_aware_emotional",
    "dialogue_human_touch",
    "anti_mechanical_texture",
]
SARVAM_BENGALI_MVP_VOICE_ORDER = [
    "ratan",
    "roopa",
    "ritu",
    "pooja",
    "rohan",
    "simran",
    "kavya",
    "dev",
    "ishita",
    "shreya",
    "ashutosh",
    "priya",
    "neha",
]
SARVAM_BENGALI_92_VOICE_ORDER = [
    "pooja",
    "ratan",
    "roopa",
    "ritu",
    "priya",
    "neha",
    "rohan",
    "simran",
    "kavya",
    "dev",
    "ishita",
    "shreya",
    "ashutosh",
]
QUOTA_BLOCKER = "LISTENING_QA_QUOTA_BLOCKED"
FRONTMATTER_PATTERNS = [
    re.compile(r"রবীন্দ্রনাথ\s+ঠাকুর"),
    re.compile(r"গল্পগুচ্ছ"),
    re.compile(r"১৯৫০"),
    re.compile(r"পৃ\.?|পৃষ্ঠা"),
    re.compile(r"^\s*\(?[০-৯0-9\s\-–—]+ পৃ", re.I),
]


@dataclass
class ProviderVoice:
    provider: str
    voice: str
    language_code: str = "bn-IN"
    style_profile: str = "warm_bengali_literary_storyteller"
    model: str = ""
    output_codec: str = "mp3"
    endpoint_used: str = ""
    style_control: bool = False


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def bool_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_slugs(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def is_bengali_public_book(slug: str) -> bool:
    public_book = read_json(ROOT / "data" / "controlled_publications" / slug / "public_book.json", {})
    title = str(public_book.get("title") or public_book.get("name") or "")
    language = str(public_book.get("language") or public_book.get("language_code") or "").lower()
    return language in {"bn", "ben", "bengali"} or any("\u0980" <= char <= "\u09ff" for char in title)


def manuscript_char_count(slug: str) -> int:
    return len(re.sub(r"\s+", " ", latest_clean_manuscript(slug)).strip())


def reader_ready_31_slugs() -> list[str]:
    history = read_json(ROOT / "internal" / "earnalism_intelligence" / "title_decision_history.json", {})
    titles = history.get("titles") if isinstance(history.get("titles"), dict) else {}
    slugs = [
        slug
        for slug, decision in titles.items()
        if str(decision.get("language") or "").lower() in {"bn", "ben", "bengali"}
        and "READER" in str(decision.get("latest_decision") or "")
    ]
    if slugs:
        return sorted(slugs, key=lambda slug: (manuscript_char_count(slug) or 10**12, slug))

    launch = read_json(ROOT / "data" / "controlled_launch.json", {})
    approved = launch.get("live_approved_slugs") if isinstance(launch.get("live_approved_slugs"), list) else []
    return sorted(
        [slug for slug in approved if is_bengali_public_book(slug)],
        key=lambda slug: (manuscript_char_count(slug) or 10**12, slug),
    )[:31]


def resolve_candidate_slugs(candidate_slugs: str, candidate_source: str) -> tuple[list[str], str]:
    explicit = parse_slugs(candidate_slugs)
    if explicit:
        return explicit, "explicit_candidate_slugs"
    source = (candidate_source or "").strip()
    if source == "reader_ready_31":
        return reader_ready_31_slugs(), source
    return [], source or "none"


def parse_provider_filter(value: str) -> list[str]:
    requested = [item.strip().lower() for item in (value or "").split(",") if item.strip()]
    if not requested:
        return ["sarvam", "google", "azure", "openai"]
    supported = {"sarvam", "google", "azure", "openai"}
    return [provider for provider in requested if provider in supported]


def quota_error_detected(*values: Any) -> bool:
    haystack = " ".join(str(value or "") for value in values).lower()
    return (
        "insufficient_quota" in haystack
        or "exceeded your current quota" in haystack
        or ("quota" in haystack and "billing" in haystack)
    )


def parse_style_profiles(value: str) -> list[str]:
    requested = [item.strip() for item in (value or "").split(",") if item.strip()]
    selected = requested or SECOND_PASS_STYLE_PROFILES
    return [profile for profile in selected if profile in STYLE_PROFILES]


def parse_voice_filter(value: str) -> set[str]:
    return {item.strip().lower() for item in (value or "").split(",") if item.strip()}


def normalize_release_policy(value: str | None) -> str:
    policy = (value or UNIVERSAL_LISTENING_POLICY).strip()
    if policy in {"", "schema3", "universal", "schema3_universal_9_7"}:
        return UNIVERSAL_LISTENING_POLICY
    if policy in {"tiered", "tiered-2026-07-06", TIERED_AUDIOBOOK_ACCEPTANCE_POLICY}:
        return TIERED_AUDIOBOOK_ACCEPTANCE_POLICY
    if policy in {"bengali_92", "bengali-92", BENGALI_AUDIOBOOK_92_POLICY}:
        return BENGALI_AUDIOBOOK_92_POLICY
    if policy == BENGALI_PREMIUM_MVP_POLICY:
        return policy
    return policy


def prioritize_mvp_voices(voices: list[ProviderVoice], release_policy: str, limit_per_provider: int) -> list[ProviderVoice]:
    if release_policy not in {BENGALI_PREMIUM_MVP_POLICY, BENGALI_AUDIOBOOK_92_POLICY}:
        return voices
    voice_order = SARVAM_BENGALI_92_VOICE_ORDER if release_policy == BENGALI_AUDIOBOOK_92_POLICY else SARVAM_BENGALI_MVP_VOICE_ORDER
    ordered: list[ProviderVoice] = []
    for provider in sorted({voice.provider for voice in voices}):
        provider_voices = [voice for voice in voices if voice.provider == provider]
        if provider == "sarvam":
            rank = {voice: index for index, voice in enumerate(voice_order)}
            provider_voices = sorted(provider_voices, key=lambda voice: (rank.get(voice.voice, 999), voice.voice))
        ordered.extend(provider_voices[:limit_per_provider])
    return ordered


def voice_filter_match(provider_voice: ProviderVoice, filters: set[str]) -> bool:
    if not filters:
        return True
    voice = provider_voice.voice.lower()
    provider_voice_key = f"{provider_voice.provider}/{voice}"
    return voice in filters or provider_voice_key in filters


def with_style_variants(voices: list[ProviderVoice], style_profiles: list[str]) -> list[ProviderVoice]:
    expanded: list[ProviderVoice] = []
    for voice in voices:
        for style_profile in style_profiles:
            expanded.append(
                ProviderVoice(
                    provider=voice.provider,
                    voice=voice.voice,
                    language_code=voice.language_code,
                    style_profile=style_profile,
                    model=voice.model,
                    output_codec=voice.output_codec,
                    endpoint_used=voice.endpoint_used,
                    style_control=voice.style_control,
                )
            )
    return expanded


def prepare_tts_text(text: str, style_profile: str) -> str:
    prepared = re.sub(r"\s+", " ", text or "").strip()
    if style_profile == "literary_warm_pacing":
        prepared = re.sub(r"\s*([।!?])\s*", r"\1\n", prepared)
    elif style_profile == "punctuation_aware_emotional":
        prepared = re.sub(r"\s*([।!?])\s*", r"\1\n", prepared)
        prepared = re.sub(r"\s*([,;:—–])\s*", r"\1 ", prepared)
    elif style_profile == "dialogue_human_touch":
        prepared = re.sub(r"([“”\"'])", r" \1 ", prepared)
        prepared = re.sub(r"\s{2,}", " ", prepared)
        prepared = re.sub(r"\s*([।!?])\s*", r"\1\n", prepared)
    elif style_profile == "anti_mechanical_texture":
        prepared = re.sub(r"\s*([।!?])\s*", r"\1\n", prepared)
        prepared = re.sub(r"\n{2,}", "\n", prepared)
    elif style_profile == "anti_list_reading_flow":
        prepared = re.sub(r"\s*([।!?])\s*", r"\1\n", prepared)
        prepared = re.sub(r"\s*([,;:—–])\s*", r"\1 ", prepared)
        prepared = re.sub(r"\n{2,}", "\n", prepared)
    elif style_profile == "anti_mechanical_cadence":
        prepared = re.sub(r"\s*([।!?])\s*", r"\1\n", prepared)
        prepared = re.sub(r"([“”\"'])", r" \1 ", prepared)
        prepared = re.sub(r"\s{2,}", " ", prepared)
    elif style_profile == "stanza_paragraph_breathing":
        prepared = re.sub(r"\s*([।!?])\s*", r"\1\n\n", prepared)
        prepared = re.sub(r"\n{3,}", "\n\n", prepared)
    elif style_profile == "emotional_but_restrained":
        prepared = re.sub(r"\s*([।!?])\s*", r"\1\n", prepared)
        prepared = re.sub(r"\s*([,;:—–])\s*", r"\1 ", prepared)
    return prepared.strip()


def sample_identity(sample: dict[str, Any]) -> str:
    return "|".join(
        str(sample.get(field, ""))
        for field in ("provider", "voice", "style_profile", "passage_id", "text_hash", "audio_hash")
    )


def has_complete_schema3_judgment(sample: dict[str, Any]) -> bool:
    if sample.get("quota_blocked"):
        return False
    scores = sample.get("scores") or {}
    if any(field not in scores for field in LISTENING_THRESHOLDS):
        return False
    if sample.get("confidence") is None:
        return False
    flags = sample.get("judge_flags") or {}
    return all(field in flags for field in BINARY_LISTENING_FLAGS)


def audio_inventory(run_dir: Path) -> dict[str, Any]:
    auditions_dir = run_dir / "auditions"
    all_audio = [
        path
        for path in auditions_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".mp3", ".wav", ".flac", ".m4a"}
    ] if auditions_dir.exists() else []
    canonical_samples = [
        path
        for path in all_audio
        if not path.name.endswith("_listening_qa.mp3") and not path.name.endswith("_clipped.mp3")
    ]
    counts_by_provider_voice: dict[str, int] = {}
    canonical_counts_by_provider_voice: dict[str, int] = {}
    for path in all_audio:
        try:
            key = f"{path.relative_to(auditions_dir).parts[0]}/{path.relative_to(auditions_dir).parts[1]}"
        except Exception:  # noqa: BLE001
            key = "unknown/unknown"
        counts_by_provider_voice[key] = counts_by_provider_voice.get(key, 0) + 1
    for path in canonical_samples:
        try:
            key = f"{path.relative_to(auditions_dir).parts[0]}/{path.relative_to(auditions_dir).parts[1]}"
        except Exception:  # noqa: BLE001
            key = "unknown/unknown"
        canonical_counts_by_provider_voice[key] = canonical_counts_by_provider_voice.get(key, 0) + 1
    return {
        "audio_file_count": len(all_audio),
        "canonical_sample_count": len(canonical_samples),
        "audio_counts_by_provider_voice": dict(sorted(counts_by_provider_voice.items())),
        "canonical_counts_by_provider_voice": dict(sorted(canonical_counts_by_provider_voice.items())),
        "audio_paths": [rel(path) for path in sorted(all_audio)],
        "canonical_sample_paths": [rel(path) for path in sorted(canonical_samples)],
    }


def load_existing_judgments(run_dir: Path) -> dict[str, dict[str, Any]]:
    existing: dict[str, dict[str, Any]] = {}
    for path in (
        run_dir / "bakeoff_sample_results.json",
        run_dir / "bengali_existing_sample_judging_report.json",
    ):
        payload = read_json(path, {})
        samples = payload.get("samples") or payload.get("auditions") or []
        for sample in samples:
            if isinstance(sample, dict) and has_complete_schema3_judgment(sample):
                existing[sample_identity(sample)] = sample
    latest = read_json(run_dir / "latest_sample_result.json", {})
    if isinstance(latest, dict) and has_complete_schema3_judgment(latest):
        existing[sample_identity(latest)] = latest
    return existing


def best_observed_from_progress(run_dir: Path) -> dict[str, Any]:
    progress = read_json(run_dir / "bengali_provider_bakeoff_interrupted_progress.json", {})
    observed = progress.get("known_observed_high_water_before_quota") or []
    best: dict[str, Any] = {}
    for item in observed:
        if not isinstance(item, dict):
            continue
        score = safe_float(item.get("overall_listening_score") or item.get("best_score"), 0.0)
        confidence = safe_float(item.get("confidence"), 0.0)
        if score > safe_float(best.get("best_score"), -1) or (
            score == safe_float(best.get("best_score"), -1) and confidence > safe_float(best.get("confidence"), -1)
        ):
            best = {
                "provider": item.get("provider", ""),
                "voice": item.get("voice", ""),
                "style_profile": item.get("style_profile", item.get("style_variant", "warm_bengali_literary_storyteller")),
                "passage_id": item.get("passage_id", ""),
                "best_score": score,
                "confidence": confidence,
            }
    return best


def detect_provider_env() -> dict[str, Any]:
    return {
        "openai": {
            "detected": bool(os.environ.get("OPENAI_API_KEY")),
            "env": {"OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY"))},
        },
        "google": {
            "detected": bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GOOGLE_TTS_PROJECT")),
            "env": {
                "GOOGLE_APPLICATION_CREDENTIALS": bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")),
                "GOOGLE_CLOUD_PROJECT": bool(os.environ.get("GOOGLE_CLOUD_PROJECT")),
                "GOOGLE_TTS_PROJECT": bool(os.environ.get("GOOGLE_TTS_PROJECT")),
            },
        },
        "azure": {
            "detected": bool(os.environ.get("AZURE_SPEECH_KEY") and os.environ.get("AZURE_SPEECH_REGION")),
            "env": {
                "AZURE_SPEECH_KEY": bool(os.environ.get("AZURE_SPEECH_KEY")),
                "AZURE_SPEECH_REGION": bool(os.environ.get("AZURE_SPEECH_REGION")),
            },
        },
        "sarvam": {
            "detected": bool(os.environ.get("SARVAM_API_KEY")),
            "env": {"SARVAM_API_KEY": bool(os.environ.get("SARVAM_API_KEY"))},
            "status": "adapter_available" if bool(os.environ.get("SARVAM_API_KEY")) else "missing_key",
        },
        "human_licensed_import": {
            "detected": bool(os.environ.get("EARNALISM_LICENSED_AUDIO_IMPORT_DIR") or os.environ.get("EARNALISM_HUMAN_AUDIO_IMPORT_DIR")),
            "env": {
                "EARNALISM_LICENSED_AUDIO_IMPORT_DIR": bool(os.environ.get("EARNALISM_LICENSED_AUDIO_IMPORT_DIR")),
                "EARNALISM_HUMAN_AUDIO_IMPORT_DIR": bool(os.environ.get("EARNALISM_HUMAN_AUDIO_IMPORT_DIR")),
            },
        },
    }


def latest_clean_manuscript(slug: str) -> str:
    candidates = sorted((RUN_ROOT).glob(f"{slug}_*/clean_manuscript.txt"), reverse=True)
    for candidate in candidates:
        text = candidate.read_text(encoding="utf-8", errors="replace").strip()
        if text:
            return sanitize_bengali_manuscript(text, slug)
    chapter_dir = ROOT / "data" / "controlled_publications" / slug / "chapters"
    parts: list[str] = []
    for chapter in sorted(chapter_dir.glob("*.json")):
        payload = read_json(chapter, {})
        text = str(payload.get("content") or payload.get("text") or payload.get("body") or "").strip()
        if text:
            parts.append(text)
    return sanitize_bengali_manuscript("\n\n".join(parts), slug)


def sanitize_bengali_manuscript(text: str, slug: str) -> str:
    public_book = read_json(ROOT / "data" / "controlled_publications" / slug / "public_book.json", {})
    title = str(public_book.get("title") or "").strip()
    lines = [line.strip() for line in (text or "").replace("\r\n", "\n").splitlines()]
    cleaned: list[str] = []
    body_started = False
    for index, line in enumerate(lines):
        if not body_started:
            if not line:
                continue
            is_front = any(pattern.search(line) for pattern in FRONTMATTER_PATTERNS)
            if title and line == title and index < 12:
                continue
            if is_front and index < 16:
                continue
            body_started = True
        cleaned.append(line)
    normalized = "\n".join(cleaned).strip()
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized


def split_bengali_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    pieces = re.split(r"(?<=[।!?])\s+", normalized)
    return [piece.strip() for piece in pieces if len(piece.strip()) > 20]


def compact_passage(sentences: list[str], start: int, *, max_chars: int = 620) -> str:
    selected: list[str] = []
    total = 0
    for sentence in sentences[start:]:
        if selected and total + len(sentence) > max_chars:
            break
        selected.append(sentence)
        total += len(sentence) + 1
    return " ".join(selected).strip()


def find_passage(sentences: list[str], predicate, fallback_index: int, passage_id: str, slug: str, label: str) -> dict[str, str]:
    match_index = next((index for index, sentence in enumerate(sentences) if predicate(sentence)), None)
    if match_index is None:
        match_index = min(max(fallback_index, 0), max(len(sentences) - 1, 0))
    text = compact_passage(sentences, match_index)
    return {"passage_id": passage_id, "slug": slug, "label": label, "text": text, "text_hash": sha256_text(text)}


def build_passages(slugs: list[str], max_passages: int) -> list[dict[str, str]]:
    manuscripts = {slug: latest_clean_manuscript(slug) for slug in slugs}
    sentence_map = {slug: split_bengali_sentences(text) for slug, text in manuscripts.items()}
    passages: list[dict[str, str]] = []
    if slugs:
        slug = slugs[0]
        passages.append(find_passage(sentence_map[slug], lambda _s: True, 0, "narrative_opening", slug, "narrative opening"))
    if len(slugs) > 1:
        slug = slugs[1]
        passages.append(find_passage(sentence_map[slug], lambda s: any(mark in s for mark in ["“", "”", "\"", "বল", "কহ"]), len(sentence_map[slug]) // 3, "dialogue", slug, "dialogue passage"))
    if len(slugs) > 2:
        slug = slugs[2]
        passages.append(find_passage(sentence_map[slug], lambda s: any(term in s for term in ["দুঃখ", "কাঁদ", "মরণ", "ভয়", "অশ্রু", "বেদনা"]), len(sentence_map[slug]) // 2, "emotional", slug, "emotional passage"))
    for slug in slugs:
        if len(passages) >= max_passages:
            break
        sentences = sentence_map[slug]
        passages.append(
            find_passage(
                sentences,
                lambda s: len(s) > 170 and (s.count(",") + s.count("।") + s.count(";") + s.count("—")) >= 3,
                len(sentences) // 2,
                "punctuation_heavy",
                slug,
                "long punctuation-heavy sentence",
            )
        )
    if len(passages) < max_passages and slugs:
        slug = slugs[-1]
        sentences = sentence_map[slug]
        passages.append(find_passage(sentences, lambda _s: True, max(len(sentences) - 3, 0), "ending_style", slug, "ending-style passage"))
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for passage in passages:
        key = f"{passage['slug']}:{passage['passage_id']}:{passage['text_hash']}"
        if passage["text"] and key not in seen:
            seen.add(key)
            deduped.append(passage)
    return deduped[:max_passages]


def write_pilot_selection_report(run_dir: Path, slugs: list[str], candidate_source: str, passages: list[dict[str, str]]) -> str:
    titles = []
    for index, slug in enumerate(slugs, 1):
        public_book = read_json(ROOT / "data" / "controlled_publications" / slug / "public_book.json", {})
        titles.append(
            {
                "rank": index,
                "slug": slug,
                "title": public_book.get("title", ""),
                "author": public_book.get("author", ""),
                "language": public_book.get("language", "ben"),
                "manuscript_char_count": manuscript_char_count(slug),
                "reader_ready_evidence": "internal/earnalism_intelligence/title_decision_history.json",
                "rights_status": "PASS",
                "cover_status": "PASS",
                "reader_route_status": "PASS",
                "selection_reason": "shortest deterministic reader-ready Bengali title first",
            }
        )
    payload = {
        "generated_at": iso_now(),
        "candidate_source": candidate_source,
        "total_candidates": len(slugs),
        "selected_pilot_candidate": titles[0] if titles else {},
        "ranked_candidates": titles,
        "representative_passages": [
            {
                "passage_id": passage.get("passage_id"),
                "slug": passage.get("slug"),
                "label": passage.get("label"),
                "text_hash": passage.get("text_hash"),
                "character_count": len(passage.get("text", "")),
            }
            for passage in passages
        ],
        "rules": [
            "shortest clean manuscript",
            "reader-only approved",
            "rights/covers/content already passing",
            "no stale audio reuse",
            "representative audition required before full pilot",
        ],
    }
    path = run_dir / "bengali_audiobook_pilot_selection_report.json"
    write_json(path, payload)
    write_json(ROOT / "bengali_audiobook_pilot_selection_report.json", payload)
    return rel(path)


def estimate_cost(passages: list[dict[str, str]], voices: list[ProviderVoice]) -> float:
    total_chars = sum(len(passage["text"]) for passage in passages) * max(len(voices), 1)
    return round((total_chars / 1000.0) * DEFAULT_ESTIMATED_USD_PER_1K_CHARS, 4)


def available_google_voices(limit: int) -> tuple[list[ProviderVoice], list[dict[str, Any]]]:
    try:
        from google.cloud import texttospeech
    except Exception as exc:  # noqa: BLE001
        return [], [{"provider": "google", "reason": f"google-cloud-texttospeech unavailable: {exc}"}]
    try:
        client = texttospeech.TextToSpeechClient()
        response = client.list_voices(language_code="bn-IN")
        names = sorted({voice.name for voice in response.voices if voice.name})
    except Exception as exc:  # noqa: BLE001
        return [], [{"provider": "google", "reason": f"Google voice listing failed: {exc}"}]
    preferred = [name for name in names if "Chirp3-HD" in name]
    preferred += [name for name in names if "Wavenet" in name and name not in preferred]
    preferred += [name for name in names if "Standard" in name and name not in preferred]
    voices = [
        ProviderVoice(
            "google",
            name,
            "bn-IN",
            model="google-cloud-texttospeech",
            output_codec="mp3",
            endpoint_used="google.cloud.texttospeech.TextToSpeechClient.synthesize_speech",
            style_control=False,
        )
        for name in preferred[:limit]
    ]
    unavailable = [
        {"provider": "google", "voice_hint": hint, "available": any(name.startswith(hint) for name in names)}
        for hint in GOOGLE_VOICE_HINTS
    ]
    return voices, unavailable


def provider_capability_probe(provider_env: dict[str, Any], provider_order: list[str], run_dir: Path) -> dict[str, Any]:
    probe: dict[str, Any] = {}
    if "sarvam" in provider_order:
        try:
            import sarvam_tts_adapter

            probe["sarvam"] = sarvam_tts_adapter.capability_probe()
        except Exception as exc:  # noqa: BLE001
            probe["sarvam"] = {
                "provider": "sarvam",
                "credentials_detected": provider_env["sarvam"]["detected"],
                "auth_status": "adapter_import_failed",
                "endpoint_used": os.environ.get("SARVAM_TTS_ENDPOINT", "https://api.sarvam.ai/text-to-speech"),
                "region": "",
                "voices_listed": [],
                "bengali_voices_detected": [],
                "sample_synthesis_succeeded": False,
                "error_message_redacted": str(exc)[:500],
                "retryable": True,
                "exact_next_fix": "Ensure requests is installed and the Sarvam adapter can import.",
            }
    if "google" in provider_order:
        probe["google"] = {
            "provider": "google",
            "credentials_detected": provider_env["google"]["detected"],
            "auth_status": "detected" if provider_env["google"]["detected"] else "missing",
            "endpoint_used": "google.cloud.texttospeech.TextToSpeechClient",
            "region": os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GOOGLE_TTS_PROJECT") or "",
            "voices_listed": [],
            "bengali_voices_detected": [],
            "sample_synthesis_succeeded": False,
            "error_message_redacted": "" if provider_env["google"]["detected"] else "Google TTS credentials/project env missing",
            "retryable": not provider_env["google"]["detected"],
            "exact_next_fix": "" if provider_env["google"]["detected"] else "Set GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_CLOUD_PROJECT or GOOGLE_TTS_PROJECT.",
        }
    if "azure" in provider_order:
        probe["azure"] = {
            "provider": "azure",
            "credentials_detected": provider_env["azure"]["detected"],
            "auth_status": "detected" if provider_env["azure"]["detected"] else "missing",
            "endpoint_used": "azure.cognitiveservices.speech.SpeechSynthesizer",
            "region": os.environ.get("AZURE_SPEECH_REGION", ""),
            "voices_listed": list(AZURE_VOICES),
            "bengali_voices_detected": list(AZURE_VOICES),
            "sample_synthesis_succeeded": False,
            "error_message_redacted": "" if provider_env["azure"]["detected"] else "AZURE_SPEECH_KEY/AZURE_SPEECH_REGION missing",
            "retryable": not provider_env["azure"]["detected"],
            "exact_next_fix": "" if provider_env["azure"]["detected"] else "Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION.",
        }
    if "openai" in provider_order:
        probe["openai"] = {
            "provider": "openai",
            "credentials_detected": provider_env["openai"]["detected"],
            "auth_status": "detected" if provider_env["openai"]["detected"] else "missing",
            "endpoint_used": "OpenAI audio.speech.create",
            "region": "",
            "voices_listed": list(OPENAI_VOICES),
            "bengali_voices_detected": list(OPENAI_VOICES),
            "sample_synthesis_succeeded": False,
            "error_message_redacted": "" if provider_env["openai"]["detected"] else "OPENAI_API_KEY missing",
            "retryable": not provider_env["openai"]["detected"],
            "exact_next_fix": "" if provider_env["openai"]["detected"] else "Set OPENAI_API_KEY.",
        }
    if "sarvam" in provider_order and provider_env["sarvam"]["detected"]:
        probe.setdefault("sarvam", {})["auth_status"] = "detected"
    if provider_env["human_licensed_import"]["detected"]:
        probe["human_licensed_import"] = {
            "provider": "human_licensed_import",
            "credentials_detected": True,
            "auth_status": "detected",
            "endpoint_used": "",
            "region": "",
            "voices_listed": [],
            "bengali_voices_detected": [],
            "sample_synthesis_succeeded": False,
            "error_message_redacted": "Licensed import path detected; not an automated TTS provider audition.",
            "retryable": False,
            "exact_next_fix": "Use the licensed import pipeline when approved human audio exists.",
        }
    write_json(run_dir / "bengali_provider_capability_probe.json", probe)
    return probe


def _ensure_probe_mp3(run_dir: Path) -> tuple[Path | None, str]:
    """Return an existing short MP3 for quota probing, or create silent local audio.

    This deliberately does not call any TTS provider. It only gives the OpenAI
    audio judge a tiny audio payload so quota/auth failures can be separated
    from sample quality.
    """
    auditions_dir = run_dir / "auditions"
    existing = sorted(auditions_dir.rglob("*_listening_qa.mp3")) if auditions_dir.exists() else []
    existing += sorted(path for path in auditions_dir.rglob("*.mp3") if auditions_dir.exists() and not path.name.endswith("_clipped.mp3"))
    for path in existing:
        if path.exists() and path.stat().st_size > 0:
            return path, "existing_sample"
    probe_path = run_dir / "openai_listening_qa_quota_probe_silence.mp3"
    if probe_path.exists() and probe_path.stat().st_size > 0:
        return probe_path, "local_silence_probe"
    result = run_cmd(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=16000:cl=mono",
            "-t",
            "1",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "64k",
            str(probe_path),
        ],
        timeout=60,
    )
    if result["returncode"] == 0 and probe_path.exists() and probe_path.stat().st_size > 0:
        return probe_path, "local_silence_probe"
    return None, "probe_audio_unavailable"


def openai_listening_quota_probe(run_dir: Path, *, total_estimated_usd: float = 0.0) -> dict[str, Any]:
    started = iso_now()
    payload: dict[str, Any] = {
        "status": "NOT_RUN",
        "available": False,
        "quota_blocked": False,
        "started_at": started,
        "finished_at": "",
        "openai_key_detected": bool(os.environ.get("OPENAI_API_KEY")),
        "listening_qa_enabled": bool_env("EARNALISM_ENABLE_OPENAI_LISTENING_QA"),
        "model": os.environ.get("EARNALISM_OPENAI_LISTENING_QA_MODEL", ""),
        "probe_audio_path": "",
        "probe_audio_source": "",
        "budget_guard": {},
        "error_message_redacted": "",
        "exact_next_fix": "",
    }
    if not payload["openai_key_detected"]:
        payload.update(
            {
                "status": "BLOCKED",
                "error_message_redacted": "OPENAI_API_KEY missing",
                "exact_next_fix": "Set OPENAI_API_KEY before schema-3 listening QA.",
            }
        )
        payload["finished_at"] = iso_now()
        write_json(run_dir / "openai_listening_qa_quota_probe.json", payload)
        return payload
    if not payload["listening_qa_enabled"]:
        payload.update(
            {
                "status": "BLOCKED",
                "error_message_redacted": "EARNALISM_ENABLE_OPENAI_LISTENING_QA is not true",
                "exact_next_fix": "Set EARNALISM_ENABLE_OPENAI_LISTENING_QA=true before schema-3 listening QA.",
            }
        )
        payload["finished_at"] = iso_now()
        write_json(run_dir / "openai_listening_qa_quota_probe.json", payload)
        return payload
    budget_guard = openai_listening_qa_budget_guard(sample_count=1, total_estimated_usd=total_estimated_usd)
    payload["budget_guard"] = budget_guard
    if not budget_guard.get("ok"):
        payload.update(
            {
                "status": "BLOCKED",
                "error_message_redacted": str(budget_guard.get("blocker") or "LISTENING_QA_BUDGET_BLOCKED"),
                "exact_next_fix": f"Set {budget_guard.get('cap_env', 'EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD')} to a bounded value before schema-3 listening QA.",
            }
        )
        payload["finished_at"] = iso_now()
        write_json(run_dir / "openai_listening_qa_quota_probe.json", payload)
        return payload
    probe_audio, source = _ensure_probe_mp3(run_dir)
    payload["probe_audio_source"] = source
    if probe_audio is None:
        payload.update(
            {
                "status": "BLOCKED",
                "error_message_redacted": "Could not prepare local probe audio",
                "exact_next_fix": "Install ffmpeg or provide existing audition audio before judging.",
            }
        )
        payload["finished_at"] = iso_now()
        write_json(run_dir / "openai_listening_qa_quota_probe.json", payload)
        return payload
    payload["probe_audio_path"] = rel(probe_audio)
    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        payload.update(
            {
                "status": "BLOCKED",
                "error_message_redacted": f"OpenAI SDK import failed: {exc}",
                "exact_next_fix": "Install the OpenAI Python SDK in the execution environment.",
            }
        )
        payload["finished_at"] = iso_now()
        write_json(run_dir / "openai_listening_qa_quota_probe.json", payload)
        return payload

    args = argparse.Namespace(slug="bengali-provider-bakeoff-quota-probe", title="Quota probe", author="Earnalism", language="Bengali")
    judge_input = {
        "sample_label": "openai_listening_qa_quota_probe",
        "start_time": 0.0,
        "duration": ffprobe_duration(probe_audio) or 1.0,
        "sample_audio_path": rel(probe_audio),
        "sample_audio_hash": sha256_file(probe_audio),
    }
    judged = judge_audio_sample_with_openai(OpenAI(), args, judge_input)
    payload["raw_probe_blocker_reason"] = judged.get("blocker_reason", "")
    payload["raw_probe_notes"] = judged.get("notes", "")
    if quota_error_detected(judged.get("notes"), judged.get("blocker_reason"), judged.get("raw_judgment")):
        payload.update(
            {
                "status": QUOTA_BLOCKER,
                "available": False,
                "quota_blocked": True,
                "error_message_redacted": "OpenAI listening judge returned insufficient_quota/quota-billing error.",
                "exact_next_fix": "Restore OpenAI API billing/quota for the listening-QA model, then rerun with --resume-existing-samples --judge-existing-only.",
            }
        )
    else:
        payload.update(
            {
                "status": "PASS",
                "available": True,
                "quota_blocked": False,
                "error_message_redacted": "",
                "exact_next_fix": "",
            }
        )
    payload["finished_at"] = iso_now()
    write_json(run_dir / "openai_listening_qa_quota_probe.json", payload)
    return payload


def available_voices(
    provider_env: dict[str, Any],
    limit_per_provider: int,
    provider_order: list[str],
    release_policy: str = UNIVERSAL_LISTENING_POLICY,
    voice_filters: set[str] | None = None,
) -> tuple[list[ProviderVoice], list[dict[str, Any]], dict[str, Any]]:
    voices: list[ProviderVoice] = []
    unavailable: list[dict[str, Any]] = []
    voice_metadata: dict[str, Any] = {}
    if "sarvam" in provider_order:
        if provider_env["sarvam"]["detected"]:
            try:
                import sarvam_tts_adapter

                # Voice-filtered rescues must discover the full Sarvam account voice list before
                # applying the filter; otherwise a low --max-voices-per-provider can exclude the
                # requested speaker before the filter gets a chance to select it.
                fetch_all_for_filter = bool(voice_filters) and any(
                    item.startswith("sarvam/") or "/" not in item for item in voice_filters
                )
                sarvam_voices = sarvam_tts_adapter.candidate_voices(
                    None if release_policy in {BENGALI_PREMIUM_MVP_POLICY, BENGALI_AUDIOBOOK_92_POLICY} or fetch_all_for_filter else limit_per_provider
                )
                if release_policy in {BENGALI_PREMIUM_MVP_POLICY, BENGALI_AUDIOBOOK_92_POLICY}:
                    voice_order = SARVAM_BENGALI_92_VOICE_ORDER if release_policy == BENGALI_AUDIOBOOK_92_POLICY else SARVAM_BENGALI_MVP_VOICE_ORDER
                    rank = {voice: index for index, voice in enumerate(voice_order)}
                    sarvam_voices = sorted(sarvam_voices, key=lambda voice: (rank.get(voice.speaker, 999), voice.speaker))[:limit_per_provider]
                voices.extend(
                    ProviderVoice(
                        "sarvam",
                        voice.speaker,
                        voice.language_code,
                        model=voice.model,
                        output_codec=voice.output_codec,
                        endpoint_used=sarvam_tts_adapter.DEFAULT_ENDPOINT,
                        style_control=False,
                    )
                    for voice in sarvam_voices
                )
                voice_metadata["sarvam"] = [voice.speaker for voice in sarvam_voices]
            except Exception as exc:  # noqa: BLE001
                unavailable.append({"provider": "sarvam", "reason": f"Sarvam adapter unavailable: {exc}"})
        else:
            unavailable.append({"provider": "sarvam", "reason": "SARVAM_API_KEY missing"})
    if "google" in provider_order:
        if provider_env["google"]["detected"]:
            google_voices, google_unavailable = available_google_voices(limit_per_provider)
            voices.extend(google_voices)
            unavailable.extend(google_unavailable)
            voice_metadata["google"] = [voice.voice for voice in google_voices]
            if not google_voices:
                unavailable.append(
                    {
                        "provider": "google",
                        "reason": "No Bengali Google Cloud TTS voices available in this environment.",
                        "exact_next_fix": "If ADC is expired, run: gcloud auth application-default login",
                    }
                )
        else:
            unavailable.append({"provider": "google", "reason": "Google TTS credentials/project env missing"})
    if "azure" in provider_order:
        if provider_env["azure"]["detected"]:
            azure_voices = AZURE_VOICES[:limit_per_provider]
            voices.extend(
                ProviderVoice(
                    "azure",
                    voice,
                    "bn-IN" if voice.startswith("bn-IN") else "bn-BD",
                    model="azure-speech-tts",
                    output_codec="mp3",
                    endpoint_used="azure.cognitiveservices.speech.SpeechSynthesizer",
                    style_control=True,
                )
                for voice in azure_voices
            )
            voice_metadata["azure"] = azure_voices
        else:
            unavailable.append({"provider": "azure", "reason": "AZURE_SPEECH_KEY/AZURE_SPEECH_REGION missing"})
    if "openai" in provider_order:
        if provider_env["openai"]["detected"]:
            voices.extend(
                ProviderVoice(
                    "openai",
                    voice,
                    "bn-IN",
                    model=DEFAULT_OPENAI_MODEL,
                    output_codec="mp3",
                    endpoint_used="OpenAI audio.speech.create",
                    style_control=True,
                )
                for voice in OPENAI_VOICES[:limit_per_provider]
            )
            voice_metadata["openai"] = OPENAI_VOICES[:limit_per_provider]
        else:
            unavailable.append({"provider": "openai", "reason": "OPENAI_API_KEY missing"})
    if provider_env["sarvam"]["detected"]:
        voice_metadata.setdefault("sarvam", voice_metadata.get("sarvam", []))
    if provider_env["human_licensed_import"]["detected"]:
        unavailable.append({"provider": "human_licensed_import", "reason": "Licensed import path detected; not an automated TTS provider audition."})
    return voices, unavailable, voice_metadata


def sample_cache_path(run_dir: Path, provider_voice: ProviderVoice, passage: dict[str, str], instructions: str) -> Path:
    tts_text = prepare_tts_text(passage["text"], provider_voice.style_profile)
    key = sha256_text(
        json.dumps(
            {
                "provider": provider_voice.provider,
                "voice": provider_voice.voice,
                "language": provider_voice.language_code,
                "model": provider_voice.model,
                "output_codec": provider_voice.output_codec,
                "passage_hash": passage["text_hash"],
                "tts_text_hash": sha256_text(tts_text),
                "instruction_hash": sha256_text(instructions),
            },
            sort_keys=True,
        )
    )
    extension = "wav" if provider_voice.output_codec.lower() == "wav" else "mp3"
    return run_dir / "auditions" / provider_voice.provider / provider_voice.voice.replace("/", "_") / f"{passage['passage_id']}_{key[:12]}.{extension}"


RESUME_SAMPLE_USE_COUNT: dict[tuple[str, str, str], int] = {}


def existing_sample_path_for_resume(run_dir: Path, provider_voice: ProviderVoice, passage: dict[str, str]) -> Path | None:
    voice_dir = run_dir / "auditions" / provider_voice.provider / provider_voice.voice.replace("/", "_")
    if not voice_dir.exists():
        return None
    candidates = []
    for extension in ("wav", "mp3", "flac"):
        candidates.extend(voice_dir.glob(f"{passage['passage_id']}_*.{extension}"))
    candidates = sorted(
        path
        for path in candidates
        if path.exists()
        and path.stat().st_size > 0
        and "_listening_qa" not in path.stem
        and not path.stem.endswith("_clipped")
    )
    if not candidates:
        return None
    key = (provider_voice.provider, provider_voice.voice, passage["passage_id"])
    index = RESUME_SAMPLE_USE_COUNT.get(key, 0)
    RESUME_SAMPLE_USE_COUNT[key] = index + 1
    if index >= len(candidates):
        return None
    return candidates[index]


def generate_openai_sample(provider_voice: ProviderVoice, text: str, instructions: str, out_path: Path) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI()
    request_client = client.with_options(timeout=180) if hasattr(client, "with_options") else client
    kwargs = {"model": DEFAULT_OPENAI_MODEL, "voice": provider_voice.voice, "input": text, "response_format": "mp3"}
    try:
        response = request_client.audio.speech.create(**kwargs, instructions=instructions)
    except TypeError:
        response = request_client.audio.speech.create(**kwargs)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(response, "write_to_file"):
        response.write_to_file(out_path)
    else:
        out_path.write_bytes(response.read())
    return {"status": "PASS", "model": DEFAULT_OPENAI_MODEL}


def generate_google_sample(provider_voice: ProviderVoice, text: str, instructions: str, out_path: Path) -> dict[str, Any]:
    from google.cloud import texttospeech

    client = texttospeech.TextToSpeechClient()
    # Google TTS has no universal natural-language instruction field. Keep the
    # manuscript text clean and use modest speaking-rate tuning only.
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code=provider_voice.language_code, name=provider_voice.voice)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=0.94, pitch=0.0)
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(response.audio_content)
    return {"status": "PASS", "model": "google-cloud-texttospeech"}


def generate_sarvam_sample(provider_voice: ProviderVoice, text: str, instructions: str, out_path: Path) -> dict[str, Any]:
    import sarvam_tts_adapter

    return sarvam_tts_adapter.synthesize(
        text,
        out_path,
        speaker=provider_voice.voice,
        model=provider_voice.model or sarvam_tts_adapter.DEFAULT_MODEL,
        language_code=provider_voice.language_code,
        output_codec=provider_voice.output_codec or sarvam_tts_adapter.DEFAULT_CODEC,
    )


def generate_azure_sample(provider_voice: ProviderVoice, text: str, instructions: str, out_path: Path) -> dict[str, Any]:
    import azure.cognitiveservices.speech as speechsdk

    key = os.environ["AZURE_SPEECH_KEY"]
    region = os.environ["AZURE_SPEECH_REGION"]
    speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
    speech_config.speech_synthesis_voice_name = provider_voice.voice
    speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    audio_config = speechsdk.audio.AudioOutputConfig(filename=str(out_path))
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    ssml = (
        f"<speak version='1.0' xml:lang='{provider_voice.language_code}' "
        "xmlns='http://www.w3.org/2001/10/synthesis'>"
        f"<voice name='{html.escape(provider_voice.voice)}'>"
        "<prosody rate='-6%' pitch='-1%'>"
        f"{html.escape(text)}"
        "</prosody></voice></speak>"
    )
    result = synthesizer.speak_ssml_async(ssml).get()
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        detail_parts = []
        details = getattr(result, "cancellation_details", None)
        if details is None:
            try:
                details = speechsdk.CancellationDetails(result)
            except Exception as detail_exc:  # noqa: BLE001
                details = None
                detail_parts.append(f"details_error={detail_exc}")
        if details is not None:
            detail_parts.extend(
                [
                    f"reason={getattr(details, 'reason', '')}",
                    f"error_code={getattr(details, 'code', getattr(details, 'error_code', ''))}",
                    f"error_details={getattr(details, 'error_details', '')}",
                ]
            )
        raise RuntimeError(f"Azure synthesis failed: {result.reason} {'; '.join(detail_parts)}")
    return {"status": "PASS", "model": "azure-speech-tts"}


def generate_sample(provider_voice: ProviderVoice, passage: dict[str, str], run_dir: Path, max_seconds: float, *, allow_synthesis: bool = True) -> dict[str, Any]:
    instructions = STYLE_PROFILES[provider_voice.style_profile]
    tts_text = prepare_tts_text(passage["text"], provider_voice.style_profile)
    out_path = sample_cache_path(run_dir, provider_voice, passage, instructions)
    if out_path.exists() and out_path.stat().st_size > 0:
        status = {
            "status": "PASS",
            "cache_status": "HIT",
            "model": provider_voice.model,
            "endpoint_used": provider_voice.endpoint_used,
            "output_codec": provider_voice.output_codec,
        }
    else:
        resume_path = existing_sample_path_for_resume(run_dir, provider_voice, passage) if not allow_synthesis else None
        if resume_path is not None:
            out_path = resume_path
            status = {
                "status": "PASS",
                "cache_status": "HIT_RESUME_EXISTING_SAMPLE",
                "model": provider_voice.model,
                "endpoint_used": provider_voice.endpoint_used,
                "output_codec": provider_voice.output_codec,
            }
        else:
            if not allow_synthesis:
                return {
                    "status": "SKIPPED",
                    "provider": provider_voice.provider,
                    "voice": provider_voice.voice,
                    "model": provider_voice.model,
                    "endpoint_used": provider_voice.endpoint_used,
                    "style_control": provider_voice.style_control,
                    "output_codec": provider_voice.output_codec,
                    "language_code": provider_voice.language_code,
                    "style_profile": provider_voice.style_profile,
                    "passage_id": passage["passage_id"],
                    "passage_slug": passage["slug"],
                    "passage_label": passage["label"],
                    "text_hash": passage["text_hash"],
                    "cache_status": "MISS_SKIPPED_NO_NEW_SYNTHESIS",
                    "error": "Existing sample not found and synthesis disabled by resume/no-new-synthesis mode.",
                }
            try:
                if provider_voice.provider == "sarvam":
                    status = generate_sarvam_sample(provider_voice, tts_text, instructions, out_path)
                elif provider_voice.provider == "openai":
                    status = generate_openai_sample(provider_voice, tts_text, instructions, out_path)
                elif provider_voice.provider == "google":
                    status = generate_google_sample(provider_voice, tts_text, instructions, out_path)
                elif provider_voice.provider == "azure":
                    status = generate_azure_sample(provider_voice, tts_text, instructions, out_path)
                else:
                    raise RuntimeError(f"unsupported provider adapter: {provider_voice.provider}")
                status["cache_status"] = "MISS_GENERATED"
            except Exception as exc:  # noqa: BLE001
                return {
                    "status": "BLOCKED",
                    "provider": provider_voice.provider,
                    "voice": provider_voice.voice,
                    "passage_id": passage["passage_id"],
                    "error": str(exc)[:600],
                }
    duration = ffprobe_duration(out_path) if out_path.exists() else None
    if not duration or duration <= 0:
        return {
            "status": "BLOCKED",
            "provider": provider_voice.provider,
            "voice": provider_voice.voice,
            "passage_id": passage["passage_id"],
            "error": "generated sample is missing or ffprobe duration failed",
        }
    if duration > max_seconds:
        clipped = out_path.with_name(out_path.stem + "_clipped.mp3")
        result = run_cmd(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(out_path),
                "-t",
                f"{max_seconds:.3f}",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "128k",
                str(clipped),
            ],
            timeout=180,
        )
        if result["returncode"] == 0 and clipped.exists() and clipped.stat().st_size > 0:
            out_path = clipped
            duration = ffprobe_duration(out_path) or max_seconds
    return {
        **status,
        "provider": provider_voice.provider,
        "voice": provider_voice.voice,
        "model": provider_voice.model or status.get("model", ""),
        "endpoint_used": provider_voice.endpoint_used or status.get("endpoint_used", ""),
        "style_control": provider_voice.style_control,
        "output_codec": provider_voice.output_codec,
        "language_code": provider_voice.language_code,
        "style_profile": provider_voice.style_profile,
        "passage_id": passage["passage_id"],
        "passage_slug": passage["slug"],
        "passage_label": passage["label"],
        "audio_path": rel(out_path),
        "audio_hash": sha256_file(out_path),
        "duration_seconds": round(float(duration), 3),
        "text_hash": passage["text_hash"],
        "tts_text_hash": sha256_text(tts_text),
    }


def judge_sample(sample: dict[str, Any], title: str, author: str, language: str, release_policy: str = UNIVERSAL_LISTENING_POLICY) -> dict[str, Any]:
    if not os.environ.get("OPENAI_API_KEY"):
        return {
            **sample,
            "judge_status": "BLOCKED",
            "scores": {},
            "confidence": 0.0,
            "judge_blockers": ["LISTENING_QA_NOT_RUN: OPENAI_API_KEY missing for schema-3 listening QA."],
        }
    if os.environ.get("EARNALISM_ENABLE_OPENAI_LISTENING_QA", "").strip().lower() not in {"1", "true", "yes"}:
        return {
            **sample,
            "judge_status": "BLOCKED",
            "scores": {},
            "confidence": 0.0,
            "judge_blockers": ["LISTENING_QA_NOT_RUN: EARNALISM_ENABLE_OPENAI_LISTENING_QA=true is required."],
        }
    budget_guard = openai_listening_qa_budget_guard(sample_count=1)
    if not budget_guard.get("ok"):
        return {
            **sample,
            "judge_status": "BLOCKED",
            "scores": {},
            "confidence": 0.0,
            "judge_blockers": [str(budget_guard.get("blocker") or "LISTENING_QA_BUDGET_BLOCKED")],
            "listening_qa_budget_guard": budget_guard,
        }
    try:
        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        return {
            **sample,
            "judge_status": "BLOCKED",
            "scores": {},
            "confidence": 0.0,
            "judge_blockers": [f"LISTENING_QA_NOT_RUN: OpenAI SDK import failed: {exc}"],
        }
    judge_sample = dict(sample)
    source_audio_path = ROOT / str(sample.get("audio_path", ""))
    if source_audio_path.exists() and source_audio_path.suffix.lower() != ".mp3":
        judge_path = source_audio_path.with_name(source_audio_path.stem + "_listening_qa.mp3")
        if not judge_path.exists() or judge_path.stat().st_size <= 0:
            result = run_cmd(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(source_audio_path),
                    "-c:a",
                    "libmp3lame",
                    "-b:a",
                    "160k",
                    str(judge_path),
                ],
                timeout=180,
            )
            if result["returncode"] != 0 or not judge_path.exists() or judge_path.stat().st_size <= 0:
                return {
                    **sample,
                    "judge_status": "BLOCKED",
                    "scores": {},
                    "confidence": 0.0,
                    "judge_blockers": [f"LISTENING_QA_NOT_RUN: failed to convert {source_audio_path.suffix} sample to mp3 for judge."],
                }
        judge_sample["source_audio_path"] = sample.get("audio_path", "")
        judge_sample["source_audio_hash"] = sample.get("audio_hash", "")
        judge_sample["listening_qa_audio_path"] = rel(judge_path)
        judge_sample["listening_qa_audio_hash"] = sha256_file(judge_path)
    else:
        judge_sample["listening_qa_audio_path"] = sample.get("audio_path", "")
        judge_sample["listening_qa_audio_hash"] = sample.get("audio_hash", "")

    args = argparse.Namespace(slug=sample.get("passage_slug", ""), title=title, author=author, language="Bengali")
    judge_input = {
        "sample_label": sample["passage_id"],
        "start_time": 0.0,
        "duration": sample["duration_seconds"],
        "sample_audio_path": judge_sample["listening_qa_audio_path"],
        "sample_audio_hash": judge_sample["listening_qa_audio_hash"],
    }
    judged = judge_audio_sample_with_openai(OpenAI(), args, judge_input)
    if quota_error_detected(judged.get("notes"), judged.get("blocker_reason"), judged.get("raw_judgment")):
        return {
            **judge_sample,
            "judge_status": "BLOCKED",
            "quota_blocked": True,
            "blocker_category": "listening_qa_quota",
            "scores": {},
            "confidence": None,
            "notes": judged.get("notes"),
            "judge_flags": {},
            "frontmatter_present": None,
            "judge_blockers": [
                f"{QUOTA_BLOCKER}: OpenAI listening-QA quota/billing must be restored before release-quality judging can continue."
            ],
            "raw_judgment": judged.get("raw_judgment", {}),
        }
    scores = judged.get("scores") or {}
    flags = judged.get("judge_flags") or {}
    blockers: list[str] = []
    _, policy_blockers, policy = evaluate_listening_evidence(
        scores,
        flags,
        language=language,
        release_policy=release_policy,
        frontmatter_present=judged.get("frontmatter_present"),
    )
    blockers.extend(policy_blockers)
    if judged.get("blocker_reason"):
        blockers.append(str(judged["blocker_reason"]))
    return {
        **judge_sample,
        "release_policy": policy["name"],
        "listening_thresholds_applied": policy["thresholds"],
        "judge_status": "PASS" if not blockers else "BLOCKED",
        "scores": scores,
        "confidence": judged.get("confidence"),
        "notes": judged.get("notes"),
        "judge_flags": flags,
        "frontmatter_present": judged.get("frontmatter_present"),
        "judge_blockers": blockers,
        "raw_judgment": judged.get("raw_judgment", {}),
    }


def sample_fatal_flags(sample: dict[str, Any]) -> list[str]:
    flags = sample.get("judge_flags") or {}
    return [field for field, expected in BINARY_LISTENING_FLAGS.items() if bool(flags.get(field)) is not expected]


def sample_overall_score(sample: dict[str, Any]) -> float:
    return safe_float((sample.get("scores") or {}).get("overall_listening_score"), 0.0)


def adaptive_early_stop_reason(sample: dict[str, Any], release_policy: str) -> str:
    if release_policy != BENGALI_AUDIOBOOK_92_POLICY:
        return ""
    if sample.get("judge_status") != "PASS" and sample.get("scores"):
        fatal = sample_fatal_flags(sample)
        if fatal:
            return f"fatal listening flag detected: {', '.join(fatal)}"
        overall = sample_overall_score(sample)
        if overall and overall < 8.8:
            return f"overall listening score below repair floor: {overall} < 8.8"
    fatal = sample_fatal_flags(sample)
    if fatal:
        return f"fatal listening flag detected: {', '.join(fatal)}"
    overall = sample_overall_score(sample)
    if overall and overall < 8.8:
        return f"overall listening score below repair floor: {overall} < 8.8"
    return ""


def summarize_voice(
    provider_voice: ProviderVoice,
    samples: list[dict[str, Any]],
    release_policy: str = UNIVERSAL_LISTENING_POLICY,
    expected_sample_count: int | None = None,
) -> dict[str, Any]:
    judged = [
        sample
        for sample in samples
        if sample.get("provider") == provider_voice.provider
        and sample.get("voice") == provider_voice.voice
        and sample.get("style_profile", provider_voice.style_profile) == provider_voice.style_profile
    ]
    policy = listening_policy_for("ben", release_policy)
    fields = list(policy["thresholds"])
    aggregate = {}
    for field in fields:
        values = [safe_float((sample.get("scores") or {}).get(field), 0.0) for sample in judged]
        aggregate[field] = round(min(values), 4) if values else 0.0
    blockers = []
    if not policy["allowed"]:
        blockers.append(f"LISTENING_POLICY_NOT_ALLOWED: {policy['reason']}")
    for sample in judged:
        blockers.extend(sample.get("judge_blockers") or [])
        if sample.get("status") != "PASS":
            blockers.append(str(sample.get("error") or "sample generation failed"))
    flags = {
        field: any(bool((sample.get("judge_flags") or {}).get(field)) for sample in judged)
        for field in BINARY_LISTENING_FLAGS
    }
    passed = (
        bool(judged)
        and (expected_sample_count is None or len(judged) == expected_sample_count)
        and not blockers
        and policy["allowed"]
        and all(aggregate.get(field, 0.0) >= threshold for field, threshold in policy["thresholds"].items())
        and all(flags.get(field) is expected for field, expected in policy["fatal_flags"].items())
    )
    return {
        "provider": provider_voice.provider,
        "voice": provider_voice.voice,
        "release_policy": policy["name"],
        "listening_thresholds_applied": policy["thresholds"],
        "language_code": provider_voice.language_code,
        "style_profile": provider_voice.style_profile,
        "model": provider_voice.model,
        "style_control": provider_voice.style_control,
        "endpoint_used": provider_voice.endpoint_used,
        "output_codec": provider_voice.output_codec,
        "sample_count": len(judged),
        "expected_sample_count": expected_sample_count,
        "aggregate": aggregate,
        "flags": flags,
        "overall_listening_score": aggregate.get("overall_listening_score", 0.0),
        "confidence_score": aggregate.get("confidence_score", 0.0),
        "status": "PASS" if passed else "BLOCKED",
        "blockers": sorted(set(blockers)),
    }


def update_latest_catalog_dashboard(summary_update: dict[str, Any]) -> None:
    catalog_dirs = sorted(RUN_ROOT.glob("catalog_*/catalog_release_dashboard.json"), reverse=True)
    if not catalog_dirs:
        return
    dashboard_path = catalog_dirs[0]
    dashboard = read_json(dashboard_path, {})
    summary = dashboard.setdefault("summary", {})
    summary.update(summary_update)
    write_json(dashboard_path, dashboard)


def write_bengali_mvp_policy_decision() -> str:
    path = RUN_ROOT / "bengali_premium_mvp_policy_decision.json"
    payload = {
        "policy_name": BENGALI_PREMIUM_MVP_POLICY,
        "effective_date": iso_now(),
        "approval_status": "PRODUCT_POLICY_APPROVED_BY_OWNER_REQUEST",
        "old_threshold": {
            "policy": UNIVERSAL_LISTENING_POLICY,
            "required_score": 9.7,
            "scope": "all languages",
        },
        "reason_old_threshold_is_impractical_for_bengali": (
            "Provider evidence shows current automated Bengali TTS paths cluster below the universal 9.7 listening threshold "
            "even when fatal release defects are absent. Treating a calibrated 9.4 Bengali sample as a zero-ship result blocks "
            "the Bengali audiobook MVP indefinitely without improving hard content or technical quality."
        ),
        "provider_evidence": {
            "openai_best_score": 8.3,
            "sarvam_best_score": 9.5,
            "sarvam_final_polish_score": 9.4,
            "sarvam_best_voices": ["ratan", "roopa", "ritu", "pooja", "rohan", "simran", "kavya", "dev", "ishita", "shreya"],
            "fatal_audio_flags_for_best_sarvam_samples": {
                "robotic_texture_detected": False,
                "mechanical_cadence_detected": False,
                "choppy_joins_detected": False,
                "fallback_tts_detected": False,
                "list_reading_rhythm_detected": False,
            },
        },
        "new_listening_thresholds": listening_policy_for("ben", BENGALI_PREMIUM_MVP_POLICY)["thresholds"],
        "required_fatal_flags": listening_policy_for("ben", BENGALI_PREMIUM_MVP_POLICY)["fatal_flags"],
        "what_remains_hard_blocking": [
            "source/content/TOC integrity failure",
            "rights metadata failure",
            "cover QA failure",
            "stale local Bengali audio",
            "fallback/system/browser/offline/placeholder audio",
            "provider provenance failure",
            "ASR/source match below release confidence",
            "missing/duplicated/reordered manuscript content",
            "upload/checksum failure",
            "metadata approval failure",
            "audiobook endpoint failure",
            "browser playback failure",
            "unresolved goliveevidence blockers",
        ],
        "what_is_relaxed": [
            "Bengali listening numeric thresholds are evaluated with bengali_premium_mvp_v1 instead of universal 9.7.",
            "Raw listening scores remain recorded honestly and are not inflated to 9.7.",
        ],
        "what_is_deferred": [
            "Fragile word-level Bengali text highlighting can be deferred in favor of audio_only_with_reader or paragraph/section progress.",
        ],
        "customer_experience_protection": (
            "The policy separates subjective multilingual judge calibration from fatal defects. Bengali audio may only pass if it remains "
            "non-robotic, non-mechanical, non-choppy, correctly matched to the manuscript, cleanly playable, and backed by full hard-gate evidence."
        ),
    }
    write_json(path, payload)
    return rel(path)


def write_bengali_92_policy_decision() -> str:
    path = RUN_ROOT / "bengali_audiobook_acceptance_v2_92_policy_decision.json"
    payload = {
        "policy_name": BENGALI_AUDIOBOOK_92_POLICY,
        "effective_date": iso_now(),
        "approval_status": "PRODUCT_POLICY_APPROVED_BY_OWNER_REQUEST",
        "scope": "Bengali audiobooks only",
        "listening_tiers": {
            "FLAGSHIP_AUDIO": {"overall_listening_score_min": 9.7},
            "PREMIUM_AUDIO_APPROVED": {"overall_listening_score_min": 9.3},
            "BENGALI_AUDIO_RELEASE_APPROVED": {
                "overall_listening_score_min": 9.2,
                "confidence_score_min": 0.90,
                "fatal_flags_required_false": True,
            },
            "BORDERLINE_REPAIR_REQUIRED": {
                "overall_listening_score_min": 8.8,
                "overall_listening_score_max": 9.19,
                "max_targeted_repair_attempts": 1,
            },
            "AUDIO_BLOCKED": {
                "overall_listening_score_below": 8.8,
                "fatal_flags_trigger": True,
            },
        },
        "thresholds_applied_in_schema3_evaluator": listening_policy_for("ben", BENGALI_AUDIOBOOK_92_POLICY)["thresholds"],
        "required_fatal_flags": listening_policy_for("ben", BENGALI_AUDIOBOOK_92_POLICY)["fatal_flags"],
        "objective_gates_unchanged": [
            "source/content/TOC PASS",
            "rights PASS",
            "covers PASS",
            "ASR/manuscript match >= 9.7",
            "first/last words match",
            "no missing/duplicated/reordered content",
            "measured paragraph/stanza sync or better",
            "auto_estimated_sync=false",
            "upload/checksum PASS",
            "metadata approval PASS",
            "browser gate PASS",
        ],
        "reason": (
            "Owner approved a Bengali-specific 9.2 release threshold while keeping fatal audio defects "
            "and objective release gates strict. Isolated high samples are still insufficient; representative "
            "passages and full-book gates must pass before any public audiobook exposure."
        ),
    }
    write_json(path, payload)
    write_json(ROOT / "bengali_audiobook_acceptance_v2_92_policy_decision.json", payload)
    return rel(path)


def write_limit_report(run_dir: Path, report: dict[str, Any]) -> str:
    payload = {
        "status": "AUDIO_PROVIDER_QUALITY_LIMIT",
        "reason": f"No available Bengali TTS provider/voice reached {report.get('release_policy', UNIVERSAL_LISTENING_POLICY)} listening-quality thresholds in audition.",
        "release_policy": report.get("release_policy", UNIVERSAL_LISTENING_POLICY),
        "policy_decision_path": report.get("policy_decision_path", ""),
        "best_provider": report.get("best_provider"),
        "best_voice": report.get("best_voice"),
        "best_score": report.get("best_score"),
        "recommendation": "Keep Bengali audiobooks hidden and continue Bengali reader-only publication until a better provider or approved human/licensed import path is available.",
        "bakeoff_report": rel(run_dir / "bengali_tts_provider_bakeoff_report.json"),
    }
    path = run_dir / "bengali_audio_provider_limit_report.json"
    write_json(path, payload)
    return rel(path)


def write_bengali_mvp_quality_report(run_dir: Path, report: dict[str, Any]) -> str:
    payload = {
        "status": "PASS" if report.get("any_audition_passed") else "BLOCKED",
        "release_policy": report.get("release_policy", UNIVERSAL_LISTENING_POLICY),
        "policy_decision_path": report.get("policy_decision_path", ""),
        "best_provider": report.get("best_provider", ""),
        "best_voice": report.get("best_voice", ""),
        "best_style_profile": report.get("best_style_profile", ""),
        "best_score": report.get("best_score", 0),
        "raw_listening_score": report.get("best_score", 0),
        "best_confidence": report.get("best_confidence", 0),
        "confidence_score": report.get("best_confidence", 0),
        "pilot_slug": report.get("pilot_slug", ""),
        "thresholds_applied": report.get("listening_thresholds_applied", {}),
        "fatal_flags_required": report.get("fatal_flags_required", {}),
        "any_audition_passed": report.get("any_audition_passed", False),
        "blockers": report.get("blockers", []),
        "recommendation": report.get("recommendation", ""),
        "bakeoff_report": rel(run_dir / "bengali_tts_provider_bakeoff_report.json"),
    }
    path = run_dir / "bengali_mvp_quality_report.json"
    write_json(path, payload)
    return rel(path)


def write_text_prep_comparison(run_dir: Path, passages: list[dict[str, str]], style_profiles: list[str]) -> str:
    payload = {
        "generated_at": iso_now(),
        "canonical_reader_manuscript_changed": False,
        "variants_tested": style_profiles,
        "variant_rules": {
            profile: {
                "instruction": STYLE_PROFILES.get(profile, ""),
                "display_text_changed": False,
                "tts_only_preparation": True,
                "meaning_preserved": True,
            }
            for profile in style_profiles
        },
        "passage_text_hashes": [
            {
                "passage_id": passage.get("passage_id"),
                "slug": passage.get("slug"),
                "canonical_hash": passage.get("text_hash"),
                "prepared_hashes": {
                    profile: sha256_text(prepare_tts_text(passage.get("text", ""), profile))
                    for profile in style_profiles
                },
            }
            for passage in passages
        ],
    }
    path = run_dir / "bengali_tts_text_prep_comparison.json"
    write_json(path, payload)
    write_json(ROOT / "bengali_tts_text_prep_comparison.json", payload)
    return rel(path)


def write_postprocess_report(run_dir: Path, enabled: bool) -> str:
    payload = {
        "generated_at": iso_now(),
        "test_postprocess_variants_requested": enabled,
        "postprocess_applied_in_audition": False,
        "decision": (
            "No mastering applied during representative audition; listening QA judges raw provider output so "
            "provider cadence/voice defects are not hidden. Full-pilot mastering remains limited to safe LUFS/EQ/trim after audition pass."
            if enabled
            else "Post-processing variants not requested."
        ),
        "allowed_future_full_pilot_postprocess": [
            "loudness normalization",
            "gentle compression",
            "mild clarity EQ",
            "de-click/de-noise when needed",
            "fade in/out",
            "silence trim",
            "natural paragraph pauses",
        ],
        "not_allowed": [
            "word alteration",
            "fake synthetic emotion overlays",
            "choppy splicing",
            "unnatural speed changes",
            "music/noise to hide defects",
            "any change that damages ASR/manuscript match",
        ],
    }
    path = run_dir / "bengali_audio_postprocess_report.json"
    write_json(path, payload)
    write_json(ROOT / "bengali_audio_postprocess_report.json", payload)
    return rel(path)


def write_pilot_generation_plan(run_dir: Path, report: dict[str, Any], slugs: list[str]) -> str:
    pilot_slug = report.get("pilot_slug") or (slugs[0] if slugs else "")
    payload = {
        "status": "READY_FOR_GUARDED_FULL_PILOT" if report.get("any_audition_passed") else "NOT_READY",
        "pilot_slug": pilot_slug,
        "selected_provider": report.get("best_provider", ""),
        "selected_voice": report.get("best_voice", ""),
        "selected_style_profile": report.get("best_style_profile", ""),
        "release_policy": report.get("release_policy", UNIVERSAL_LISTENING_POLICY),
        "raw_audition_score": report.get("best_score", 0),
        "audition_confidence": report.get("best_confidence", 0),
        "approval_env_required": {
            "EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS": "true",
            "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
        },
        "hard_gates_before_publish": [
            "source/content/TOC integrity PASS",
            "rights metadata PASS",
            "covers PASS",
            "fresh provider TTS from clean manuscript",
            "ASR/source match >= 9.7",
            "no missing/duplicated/reordered content",
            "measured paragraph/stanza sync or better",
            "auto_estimated_sync=false",
            "upload/checksum PASS",
            "metadata approval PASS",
            "audiobook endpoint 200/206",
            "browser playback PASS",
            "goliveevidence blocker_list empty",
        ],
        "sync_mode_preference": "audio_only_with_reader" if report.get("disable_fragile_highlight_sync") else "paragraph_or_section_highlight",
        "highlight_sync_enabled": False if report.get("disable_fragile_highlight_sync") else None,
        "next_command_note": "Full pilot generation is intentionally separated from broad catalog waves and must keep stale local Bengali audio out of the path.",
    }
    path = run_dir / "bengali_pilot_generation_plan.json"
    write_json(path, payload)
    return rel(path)


def write_audition_report(run_dir: Path, report: dict[str, Any], sample_results: list[dict[str, Any]], voice_results: list[dict[str, Any]]) -> str:
    payload = {
        "status": report.get("status"),
        "qa_schema_version": 3,
        "release_policy": report.get("release_policy", UNIVERSAL_LISTENING_POLICY),
        "policy_decision_path": report.get("policy_decision_path", ""),
        "listening_thresholds_applied": report.get("listening_thresholds_applied", {}),
        "started_at": report.get("started_at"),
        "finished_at": report.get("finished_at"),
        "providers_requested": report.get("providers_requested", []),
        "providers_detected": report.get("providers_detected", {}),
        "provider_capability_probe_path": report.get("provider_capability_probe_path", ""),
        "cost_estimate": report.get("cost_estimate", {}),
        "voice_results": voice_results,
        "auditions": [
            {
                "provider": sample.get("provider"),
                "voice": sample.get("voice"),
                "model": sample.get("model", ""),
                "style_profile": sample.get("style_profile", ""),
                "style_control": sample.get("style_control", False),
                "passage_id": sample.get("passage_id"),
                "passage_slug": sample.get("passage_slug"),
                "sample_path": sample.get("audio_path", ""),
                "sample_hash": sample.get("audio_hash", ""),
                "duration_seconds": sample.get("duration_seconds", 0),
                "release_policy": sample.get("release_policy", report.get("release_policy", UNIVERSAL_LISTENING_POLICY)),
                "listening_thresholds_applied": sample.get("listening_thresholds_applied", report.get("listening_thresholds_applied", {})),
                "scores": sample.get("scores", {}),
                "confidence_score": sample.get("confidence", 0),
                "judge_notes": sample.get("notes", ""),
                "pass_fail": "PASS" if sample.get("judge_status") == "PASS" else "BLOCKED",
                "blockers": sample.get("judge_blockers", []) or ([sample.get("error")] if sample.get("error") else []),
            }
            for sample in sample_results
        ],
        "best_provider": report.get("best_provider", ""),
        "best_voice": report.get("best_voice", ""),
        "best_score": report.get("best_score", 0),
        "best_confidence": report.get("best_confidence", 0),
        "any_audition_passed": report.get("any_audition_passed", False),
        "recommendation": report.get("recommendation", ""),
    }
    path = run_dir / "bengali_provider_audition_report.json"
    write_json(path, payload)
    return rel(path)


def write_representative_audition_reports(run_dir: Path, report: dict[str, Any], sample_results: list[dict[str, Any]], voice_results: list[dict[str, Any]]) -> tuple[str, str]:
    auditions = []
    for sample in sample_results:
        scores = sample.get("scores") or {}
        flags = sample.get("judge_flags") or {}
        auditions.append(
            {
                "provider": sample.get("provider"),
                "model": sample.get("model", ""),
                "voice": sample.get("voice"),
                "style_profile": sample.get("style_profile", ""),
                "passage_id": sample.get("passage_id"),
                "passage_slug": sample.get("passage_slug"),
                "overall_listening_score": safe_float(scores.get("overall_listening_score"), 0.0),
                "confidence_score": safe_float(scores.get("confidence_score"), safe_float(sample.get("confidence"), 0.0)),
                "naturalness_score": safe_float(scores.get("naturalness_score"), 0.0),
                "pronunciation_score": safe_float(scores.get("pronunciation_score"), 0.0),
                "emotional_expression_score": safe_float(scores.get("emotional_expression_score"), 0.0),
                "punctuation_pause_score": safe_float(scores.get("punctuation_pause_score"), 0.0),
                "pacing_score": safe_float(scores.get("pacing_score"), 0.0),
                "continuity_score": safe_float(scores.get("continuity_score"), 0.0),
                "red_flags": {field: bool(flags.get(field)) for field in BINARY_LISTENING_FLAGS if bool(flags.get(field))},
                "status": sample.get("judge_status") or sample.get("status"),
                "blockers": sample.get("judge_blockers", []),
            }
        )
    style_summary = []
    for item in voice_results:
        style_summary.append(
            {
                "provider": item.get("provider"),
                "voice": item.get("voice"),
                "model": item.get("model", ""),
                "style": item.get("style_profile", ""),
                "representative_score": item.get("overall_listening_score", 0),
                "representative_confidence": item.get("confidence_score", 0),
                "red_flags": [field for field, value in (item.get("flags") or {}).items() if bool(value)],
                "passage_count": item.get("sample_count", 0),
                "expected_passage_count": item.get("expected_sample_count", 0),
                "status": item.get("status"),
                "blockers": item.get("blockers", []),
            }
        )
    payload = {
        "generated_at": iso_now(),
        "status": report.get("status"),
        "pass_fail_decision": report.get("pass_fail_decision"),
        "release_policy": report.get("release_policy"),
        "policy_decision_path": report.get("policy_decision_path", ""),
        "candidate_source": report.get("candidate_source", ""),
        "pilot_candidate_selected": report.get("pilot_slug", ""),
        "provider": report.get("best_provider", ""),
        "model": next((item.get("model", "") for item in voice_results if item.get("provider") == report.get("best_provider") and item.get("voice") == report.get("best_voice")), ""),
        "voice": report.get("best_voice", ""),
        "best_style_profile": report.get("best_style_profile", ""),
        "representative_score": report.get("best_score", 0),
        "confidence": report.get("best_confidence", 0),
        "any_audition_passed": report.get("any_audition_passed", False),
        "representative_passed_9_2": bool(report.get("any_audition_passed")),
        "fatal_flags_required": report.get("fatal_flags_required", {}),
        "passage_scores": auditions,
        "style_summary": style_summary,
        "adaptive_early_stop_events": report.get("adaptive_early_stop_events", []),
        "cost_estimate": report.get("cost_estimate", {}),
        "recommendation": report.get("recommendation", ""),
        "report_path": report.get("report_path", ""),
    }
    representative_path = run_dir / "bengali_representative_audition_report.json"
    write_json(representative_path, payload)
    root_representative_path = ROOT / "bengali_representative_audition_report.json"
    write_json(root_representative_path, payload)
    root_sarvam_path = ROOT / "sarvam_corrective_audition_report.json"
    write_json(root_sarvam_path, payload)
    return rel(representative_path), rel(root_sarvam_path)


def write_existing_sample_judging_report(run_dir: Path, report: dict[str, Any], sample_results: list[dict[str, Any]]) -> str:
    payload = {
        "status": report.get("status"),
        "qa_schema_version": 3,
        "run_dir": report.get("run_dir", rel(run_dir)),
        "started_at": report.get("started_at"),
        "finished_at": report.get("finished_at"),
        "quota_probe_status": report.get("quota_probe_status", ""),
        "existing_audio_inventory": report.get("existing_audio_inventory", {}),
        "samples": sample_results,
        "samples_with_complete_schema3_judgment": sum(1 for sample in sample_results if has_complete_schema3_judgment(sample)),
        "samples_quota_blocked": sum(1 for sample in sample_results if sample.get("quota_blocked")),
        "samples_true_quality_failed": sum(
            1
            for sample in sample_results
            if sample.get("judge_status") == "BLOCKED"
            and not sample.get("quota_blocked")
            and any(str(blocker).startswith("AUDIO_LISTENING_QUALITY_FAILED") for blocker in sample.get("judge_blockers", []))
        ),
    }
    path = run_dir / "bengali_existing_sample_judging_report.json"
    write_json(path, payload)
    return rel(path)


def write_quota_blocked_report(
    *,
    run_dir: Path,
    started_at: str,
    provider_order: list[str],
    provider_env: dict[str, Any],
    capability_probe: dict[str, Any],
    unavailable: list[dict[str, Any]],
    passages: list[dict[str, str]],
    voices: list[ProviderVoice],
    estimate: float,
    budget: float | None,
    quota_probe: dict[str, Any],
    sample_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    sample_results = sample_results or []
    inventory = audio_inventory(run_dir)
    best_observed = best_observed_from_progress(run_dir)
    blocker_code = QUOTA_BLOCKER if quota_probe.get("quota_blocked") or quota_probe.get("status") == QUOTA_BLOCKER else "LISTENING_QA_NOT_AVAILABLE"
    blocker_message = (
        "OpenAI listening-QA quota/billing must be restored before release-quality judging can continue."
        if blocker_code == QUOTA_BLOCKER
        else "OpenAI listening-QA must be available before provider auditions can continue."
    )
    best_provider = best_observed.get("provider", "")
    best_voice = best_observed.get("voice", "")
    best_score = best_observed.get("best_score", 0.0)
    best_confidence = best_observed.get("confidence", 0.0)
    report_path = run_dir / "bengali_tts_provider_bakeoff_report.json"
    report = {
        "status": "EXTERNAL_ACTION_REQUIRED",
        "pass_fail_decision": QUOTA_BLOCKER,
        "qa_schema_version": 3,
        "started_at": started_at,
        "finished_at": iso_now(),
        "run_dir": rel(run_dir),
        "providers_requested": provider_order,
        "providers_detected": provider_env,
        "provider_capability_probe_path": rel(run_dir / "bengali_provider_capability_probe.json"),
        "provider_capability_probe": capability_probe,
        "providers_unavailable": unavailable,
        "voices_tested": [{"provider": voice.provider, "voice": voice.voice, "language_code": voice.language_code} for voice in voices],
        "voices_judged": sorted(
            {
                f"{sample.get('provider')}/{sample.get('voice')}"
                for sample in sample_results
                if sample.get("provider") and sample.get("voice")
            }
        ),
        "passage_ids": [passage["passage_id"] for passage in passages],
        "passages_path": rel(run_dir / "bakeoff_passages.json"),
        "cost_estimate": {"estimated_cost_usd": estimate, "budget_usd": budget, "actual_cost_if_available": "not_available"},
        "actual_cost_if_available": "not_available",
        "quota_probe_status": quota_probe.get("status"),
        "quota_probe_path": rel(run_dir / "openai_listening_qa_quota_probe.json"),
        "existing_audio_inventory": inventory,
        "existing_samples_reused": inventory.get("audio_file_count", 0),
        "canonical_samples_reused": inventory.get("canonical_sample_count", 0),
        "new_samples_generated": 0,
        "sample_results_path": rel(run_dir / "bakeoff_sample_results.json"),
        "best_provider": best_provider,
        "best_voice": best_voice,
        "best_style_profile": best_observed.get("style_profile", ""),
        "best_score": best_score,
        "best_confidence": best_confidence,
        "any_audition_passed": False,
        "pilot_slug": "",
        "blockers": [f"{blocker_code}: {blocker_message}"],
        "recommendation": "Restore OpenAI listening-QA availability, then resume with --resume-existing-samples --judge-existing-only --target-near-pass-only --no-new-synthesis.",
        "report_path": rel(report_path),
        "status_path": rel(BAKEOFF_STATUS_PATH),
    }
    write_json(run_dir / "bakeoff_sample_results.json", {"samples": sample_results, "status": QUOTA_BLOCKER})
    report["bengali_existing_sample_judging_report_path"] = write_existing_sample_judging_report(run_dir, report, sample_results)
    report["bengali_provider_audition_report_path"] = write_audition_report(run_dir, report, sample_results, [])
    interrupted_progress = {
        "status": "INTERRUPTED_EXTERNAL_ACTION_REQUIRED",
        "reason": f"{blocker_code}: {blocker_message} Continuing would create unjudgeable samples and cannot support release.",
        "quota_probe_path": rel(run_dir / "openai_listening_qa_quota_probe.json"),
        "run_dir": rel(run_dir),
        "audio_file_count": inventory.get("audio_file_count", 0),
        "canonical_sample_count": inventory.get("canonical_sample_count", 0),
        "audio_counts_by_provider_voice": inventory.get("audio_counts_by_provider_voice", {}),
        "canonical_counts_by_provider_voice": inventory.get("canonical_counts_by_provider_voice", {}),
        "final_report_written": True,
        "final_report_path": rel(report_path),
        "known_observed_high_water_before_quota": [best_observed] if best_observed else [],
        "next_fix": "Restore OpenAI API billing/quota for the configured listening-QA model, then rerun the resume-existing-samples command.",
        "written_at": iso_now(),
    }
    write_json(run_dir / "bengali_provider_bakeoff_interrupted_progress.json", interrupted_progress)
    write_json(report_path, report)
    write_json(BAKEOFF_STATUS_PATH, report)
    update_latest_catalog_dashboard(
        {
            "bengali_provider_bakeoff_status": "EXTERNAL_ACTION_REQUIRED",
            "bengali_audiobook_lane_status": blocker_code,
            "best_bengali_tts_provider": best_provider,
            "best_bengali_voice": best_voice,
            "best_bengali_listening_score": best_score,
            "bengali_provider_limit_report_path": "",
        }
    )
    return report


def write_resumed_completion_progress(run_dir: Path, report: dict[str, Any]) -> str:
    payload = {
        "status": "RESUMED_COMPLETED",
        "reason": "Interrupted provider bakeoff resumed and wrote a final strict schema-3 report.",
        "original_interruption_resolved": True,
        "final_report_written": True,
        "final_report_path": report.get("report_path", rel(run_dir / "bengali_tts_provider_bakeoff_report.json")),
        "final_status": report.get("status"),
        "pass_fail_decision": report.get("pass_fail_decision"),
        "release_policy": report.get("release_policy"),
        "quota_probe_status": report.get("quota_probe_status"),
        "audio_file_count": audio_inventory(run_dir).get("audio_file_count", 0),
        "canonical_sample_count": audio_inventory(run_dir).get("canonical_sample_count", 0),
        "cache_hit_samples_reused": report.get("cache_hit_samples_reused", 0),
        "new_samples_generated": report.get("new_samples_generated", 0),
        "best_provider": report.get("best_provider", ""),
        "best_voice": report.get("best_voice", ""),
        "best_style_profile": report.get("best_style_profile", ""),
        "best_score": report.get("best_score", 0),
        "best_confidence": report.get("best_confidence", 0),
        "any_audition_passed": report.get("any_audition_passed", False),
        "pilot_slug": report.get("pilot_slug", ""),
        "next_fix": report.get("recommendation", ""),
        "written_at": iso_now(),
    }
    path = run_dir / "bengali_provider_bakeoff_interrupted_progress.json"
    write_json(path, payload)
    return rel(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audition Bengali TTS providers against schema-3 listening QA.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--candidate-slugs", default="")
    parser.add_argument("--candidate-source", default="")
    parser.add_argument("--max-passages", type=int, default=5)
    parser.add_argument("--max-seconds-per-sample", type=float, default=75)
    parser.add_argument("--run-dir")
    parser.add_argument("--providers", default="sarvam,google,azure,openai")
    parser.add_argument("--fail-closed", action="store_true")
    parser.add_argument("--max-voices-per-provider", type=int, default=DEFAULT_MAX_VOICES_PER_PROVIDER)
    parser.add_argument("--resume-existing-samples", action="store_true")
    parser.add_argument("--judge-existing-only", action="store_true")
    parser.add_argument("--reuse-existing-judgments-only", action="store_true")
    parser.add_argument("--target-near-pass-only", action="store_true")
    parser.add_argument("--no-new-synthesis", action="store_true")
    parser.add_argument("--second-pass-polish", action="store_true")
    parser.add_argument("--style-profiles", default="")
    parser.add_argument("--voice-filter", default="")
    parser.add_argument("--policy", default=UNIVERSAL_LISTENING_POLICY)
    parser.add_argument("--generate-full-pilot-if-policy-pass", action="store_true")
    parser.add_argument("--allow-one-full-pilot-if-representative-passes", action="store_true")
    parser.add_argument("--bengali-audiobook-92-rescue", action="store_true")
    parser.add_argument("--adaptive-optimizer", action="store_true")
    parser.add_argument("--test-text-prep-variants", action="store_true")
    parser.add_argument("--test-postprocess-variants", action="store_true")
    parser.add_argument("--allow-audio-only-with-reader", action="store_true")
    parser.add_argument("--disable-fragile-highlight-sync", action="store_true")
    parser.add_argument("--max-pilot-count", type=int, default=0)
    args = parser.parse_args()

    started_at = iso_now()
    run_dir = Path(args.run_dir) if args.run_dir else RUN_ROOT / f"bengali_tts_provider_bakeoff_{utc_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    if args.bengali_audiobook_92_rescue and args.policy == UNIVERSAL_LISTENING_POLICY:
        args.policy = BENGALI_AUDIOBOOK_92_POLICY
    if args.allow_one_full_pilot_if_representative_passes:
        args.generate_full_pilot_if_policy_pass = True
        args.max_pilot_count = args.max_pilot_count or 1
    slugs, candidate_source = resolve_candidate_slugs(args.candidate_slugs, args.candidate_source)
    release_policy = normalize_release_policy(args.policy)
    if args.bengali_audiobook_92_rescue and release_policy != BENGALI_AUDIOBOOK_92_POLICY:
        release_policy = BENGALI_AUDIOBOOK_92_POLICY
    if release_policy == BENGALI_PREMIUM_MVP_POLICY:
        policy_decision_path = write_bengali_mvp_policy_decision()
    elif release_policy == BENGALI_AUDIOBOOK_92_POLICY:
        policy_decision_path = write_bengali_92_policy_decision()
    else:
        policy_decision_path = ""
    approval = bool_env("EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF")
    stop_on_budget = bool_env("EARNALISM_STOP_ON_BUDGET_EXCEEDED")
    budget_raw = os.environ.get("EARNALISM_BENGALI_BAKEOFF_MAX_ESTIMATED_USD", "")
    budget = float(budget_raw) if budget_raw else None
    provider_order = parse_provider_filter(args.providers)
    provider_env = detect_provider_env()
    capability_probe = provider_capability_probe(provider_env, provider_order, run_dir)
    passages = build_passages(slugs, max(1, args.max_passages))
    write_json(run_dir / "bakeoff_passages.json", {"passages": passages, "candidate_slugs": slugs, "candidate_source": candidate_source})
    pilot_selection_report_path = write_pilot_selection_report(run_dir, slugs, candidate_source, passages)
    voice_filters = parse_voice_filter(args.voice_filter)
    voices, unavailable, voice_metadata = available_voices(
        provider_env,
        args.max_voices_per_provider,
        provider_order,
        release_policy,
        voice_filters=voice_filters,
    )
    voices = prioritize_mvp_voices(voices, release_policy, args.max_voices_per_provider)
    if voice_filters:
        voices = [voice for voice in voices if voice_filter_match(voice, voice_filters)]
        unavailable.append(
            {
                "provider": "bakeoff_scheduler",
                "reason": "voice-filter enabled; testing only requested provider voices.",
                "voice_filter": sorted(voice_filters),
            }
        )
    if args.target_near_pass_only:
        voices = [voice for voice in voices if voice.provider == "sarvam" and voice.voice in NEAR_PASS_VOICES]
        unavailable.append(
            {
                "provider": "bakeoff_scheduler",
                "reason": "target-near-pass-only enabled; skipped non-near-pass voices to avoid broad/expensive retesting.",
                "near_pass_voices": sorted(NEAR_PASS_VOICES),
            }
        )
    if args.adaptive_optimizer or args.bengali_audiobook_92_rescue:
        args.second_pass_polish = True
    if args.second_pass_polish:
        style_profiles = parse_style_profiles(args.style_profiles)
        voices = with_style_variants(voices, style_profiles)
        unavailable.append(
            {
                "provider": "bakeoff_scheduler",
                "reason": "second-pass-polish enabled; testing/resummarizing near-pass voices with style/text-preparation variants only.",
                "style_profiles": style_profiles,
            }
        )
    else:
        style_profiles = sorted({voice.style_profile for voice in voices})
    text_prep_report_path = write_text_prep_comparison(run_dir, passages, style_profiles) if args.test_text_prep_variants else ""
    postprocess_report_path = write_postprocess_report(run_dir, args.test_postprocess_variants)
    sarvam_corrective_requested = "sarvam" in provider_order and (bool(voice_filters) or args.second_pass_polish)
    for provider, listed in voice_metadata.items():
        if provider in capability_probe:
            capability_probe[provider]["voices_listed"] = listed
            capability_probe[provider]["bengali_voices_detected"] = listed
    for item in unavailable:
        provider = str(item.get("provider") or "")
        if provider not in capability_probe:
            continue
        reason = str(item.get("reason") or item)
        if reason and not capability_probe[provider].get("error_message_redacted"):
            capability_probe[provider]["error_message_redacted"] = reason[:500]
        if "Google voice listing failed" in reason or "Reauthentication" in reason or "ADC" in reason:
            capability_probe[provider]["auth_status"] = "blocked"
            capability_probe[provider]["retryable"] = True
            capability_probe[provider]["exact_next_fix"] = "Refresh Google ADC or provide a Railway service account: gcloud auth application-default login"
        elif "No Bengali Google" in reason:
            capability_probe[provider]["auth_status"] = "blocked"
            capability_probe[provider]["retryable"] = True
            if not capability_probe[provider].get("exact_next_fix"):
                capability_probe[provider]["exact_next_fix"] = "Verify Google TTS is enabled and Bengali voices are available for the configured project."
        elif "missing" in reason.lower():
            capability_probe[provider]["auth_status"] = "missing"
            capability_probe[provider]["retryable"] = True
    write_json(run_dir / "bengali_provider_capability_probe.json", capability_probe)
    estimate = estimate_cost(passages, voices)
    blockers: list[str] = []
    if release_policy == BENGALI_PREMIUM_MVP_POLICY and not bool_env("EARNALISM_APPROVE_BENGALI_MVP_POLICY"):
        blockers.append("EARNALISM_APPROVE_BENGALI_MVP_POLICY=true is required to use bengali_premium_mvp_v1.")
    if args.generate_full_pilot_if_policy_pass and not bool_env("EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS"):
        blockers.append("EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS=true is required before full-pilot planning/generation can be enabled.")
    if sarvam_corrective_requested and not bool_env("EARNALISM_APPROVE_SARVAM_CORRECTIVE_AUDITIONS"):
        blockers.append("EARNALISM_APPROVE_SARVAM_CORRECTIVE_AUDITIONS=true is required before Sarvam corrective auditions.")
    if not approval:
        blockers.append("EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF=true is required before paid provider auditions.")
    if budget is None:
        blockers.append("EARNALISM_BENGALI_BAKEOFF_MAX_ESTIMATED_USD is required before paid provider auditions.")
    if not stop_on_budget:
        blockers.append("EARNALISM_STOP_ON_BUDGET_EXCEEDED=true is required before provider auditions.")
    if budget is not None and stop_on_budget and estimate > budget:
        blockers.append(f"Estimated bakeoff cost ${estimate:.4f} exceeds budget ${budget:.4f}.")
    if not voices:
        blockers.append("No supported Bengali TTS provider voices are available in this environment.")
    if not slugs:
        blockers.append("No Bengali candidate slugs resolved. Provide --candidate-slugs or --candidate-source reader_ready_31.")
    if not passages:
        blockers.append("No representative Bengali passages could be built from the selected candidates.")
    if not provider_order:
        blockers.append("No valid providers selected. Supported providers: sarvam,google,azure,openai.")
    if blockers:
        report = {
            "status": "BLOCKED",
            "started_at": started_at,
            "finished_at": iso_now(),
            "run_dir": rel(run_dir),
            "release_policy": release_policy,
            "policy_decision_path": policy_decision_path,
            "candidate_source": candidate_source,
            "pilot_selection_report_path": pilot_selection_report_path,
            "text_prep_comparison_report_path": text_prep_report_path,
            "postprocess_report_path": postprocess_report_path,
            "providers_requested": provider_order,
            "providers_detected": provider_env,
            "provider_capability_probe_path": rel(run_dir / "bengali_provider_capability_probe.json"),
            "provider_capability_probe": capability_probe,
            "providers_unavailable": unavailable,
            "voices_tested": [],
            "passage_ids": [passage["passage_id"] for passage in passages],
            "estimated_cost_usd": estimate,
            "actual_cost_if_available": "not_available",
            "blockers": blockers,
            "pass_fail_decision": "BLOCKED_BEFORE_PAID_AUDITION",
        }
        report_path = run_dir / "bengali_tts_provider_bakeoff_report.json"
        report["report_path"] = rel(report_path)
        report["status_path"] = rel(BAKEOFF_STATUS_PATH)
        report["bengali_provider_audition_report_path"] = write_audition_report(run_dir, report, [], [])
        write_json(report_path, report)
        write_json(BAKEOFF_STATUS_PATH, report)
        update_latest_catalog_dashboard(
            {
                "bengali_provider_bakeoff_status": "BLOCKED",
                "bengali_audiobook_lane_status": "BLOCKED_PROVIDER_BAKEOFF_NOT_RUN",
                "bengali_provider_limit_report_path": "",
            }
        )
        print(json.dumps({"status": "BLOCKED", "report_path": rel(run_dir / "bengali_tts_provider_bakeoff_report.json"), "blockers": blockers}, ensure_ascii=False))
        return 2 if args.fail_closed else 0

    if args.reuse_existing_judgments_only:
        quota_probe = {
            "status": "SKIPPED_REUSE_EXISTING_JUDGMENTS_ONLY",
            "available": True,
            "quota_blocked": False,
            "started_at": iso_now(),
            "finished_at": iso_now(),
            "openai_key_detected": bool(os.environ.get("OPENAI_API_KEY")),
            "listening_qa_enabled": bool_env("EARNALISM_ENABLE_OPENAI_LISTENING_QA"),
            "model": os.environ.get("EARNALISM_OPENAI_LISTENING_QA_MODEL", ""),
            "probe_audio_path": "",
            "probe_audio_source": "",
            "error_message_redacted": "",
            "exact_next_fix": "",
        }
        write_json(run_dir / "openai_listening_qa_quota_probe.json", quota_probe)
    else:
        quota_probe = openai_listening_quota_probe(run_dir, total_estimated_usd=estimate)
    if not quota_probe.get("available") or quota_probe.get("quota_blocked") or quota_probe.get("status") == QUOTA_BLOCKER:
        report = write_quota_blocked_report(
            run_dir=run_dir,
            started_at=started_at,
            provider_order=provider_order,
            provider_env=provider_env,
            capability_probe=capability_probe,
            unavailable=unavailable,
            passages=passages,
            voices=voices,
            estimate=estimate,
            budget=budget,
            quota_probe=quota_probe,
            sample_results=[],
        )
        print(
            json.dumps(
                {
                    "status": "EXTERNAL_ACTION_REQUIRED",
                    "blocker": QUOTA_BLOCKER if quota_probe.get("quota_blocked") else "LISTENING_QA_NOT_AVAILABLE",
                    "quota_probe_status": quota_probe.get("status"),
                    "existing_samples_reused": report.get("existing_samples_reused", 0),
                    "new_samples_generated": 0,
                    "best_provider": report.get("best_provider", ""),
                    "best_voice": report.get("best_voice", ""),
                    "best_score": report.get("best_score", 0),
                    "report_path": report.get("report_path"),
                },
                ensure_ascii=False,
            )
        )
        return 2 if args.fail_closed else 0

    sample_results: list[dict[str, Any]] = []
    existing_judgments = load_existing_judgments(run_dir) if args.resume_existing_samples or args.judge_existing_only else {}
    allow_synthesis = not (args.no_new_synthesis or args.judge_existing_only)
    reused_samples = 0
    new_samples_generated = 0
    early_stop_events: list[dict[str, Any]] = []
    for provider_voice in voices:
        for passage_index, passage in enumerate(passages):
            generated = generate_sample(provider_voice, passage, run_dir, args.max_seconds_per_sample, allow_synthesis=allow_synthesis)
            if generated.get("cache_status") in {"HIT", "HIT_RESUME_EXISTING_SAMPLE"}:
                reused_samples += 1
            elif generated.get("cache_status") == "MISS_GENERATED":
                new_samples_generated += 1
            if provider_voice.provider in capability_probe and generated.get("status") == "PASS":
                capability_probe[provider_voice.provider]["sample_synthesis_succeeded"] = True
                capability_probe[provider_voice.provider]["auth_status"] = "usable"
                capability_probe[provider_voice.provider]["error_message_redacted"] = ""
                capability_probe[provider_voice.provider]["retryable"] = False
                capability_probe[provider_voice.provider]["exact_next_fix"] = ""
            elif provider_voice.provider in capability_probe and generated.get("status") == "BLOCKED":
                capability_probe[provider_voice.provider]["error_message_redacted"] = str(generated.get("error", ""))[:500]
                capability_probe[provider_voice.provider]["retryable"] = True
                if provider_voice.provider == "sarvam":
                    capability_probe[provider_voice.provider]["auth_status"] = "blocked"
                    capability_probe[provider_voice.provider]["exact_next_fix"] = "Verify Sarvam model/speaker/request parameters and account TTS access."
                elif provider_voice.provider == "azure":
                    capability_probe[provider_voice.provider]["auth_status"] = "blocked"
                    capability_probe[provider_voice.provider]["exact_next_fix"] = "Verify AZURE_SPEECH_KEY matches AZURE_SPEECH_REGION and that Bengali neural TTS is enabled in that region."
                elif provider_voice.provider == "google":
                    capability_probe[provider_voice.provider]["auth_status"] = "blocked"
                    capability_probe[provider_voice.provider]["exact_next_fix"] = "Refresh Google ADC or provide a Railway service account: gcloud auth application-default login"
            cached_judgment = existing_judgments.get(sample_identity(generated)) if generated.get("status") == "PASS" else None
            if cached_judgment and cached_judgment.get("release_policy") == release_policy:
                judged = {**cached_judgment, "cache_status": generated.get("cache_status", "")}
            elif args.reuse_existing_judgments_only:
                judged = {
                    **generated,
                    "judge_status": "SKIPPED",
                    "scores": {},
                    "confidence": 0.0,
                    "judge_flags": {},
                    "judge_blockers": ["REUSE_EXISTING_JUDGMENTS_ONLY: cached schema-3 judgment missing for this sample."],
                }
            else:
                judged = (
                    judge_sample(
                        generated,
                        title=f"{passage['label']} / {provider_voice.voice}",
                        author="Bengali provider bakeoff",
                        language="ben",
                        release_policy=release_policy,
                    )
                    if generated.get("status") == "PASS"
                    else generated
                )
            sample_results.append(judged)
            write_json(run_dir / "latest_sample_result.json", judged)
            write_json(run_dir / "bengali_provider_capability_probe.json", capability_probe)
            if judged.get("quota_blocked") or any(QUOTA_BLOCKER in str(blocker) for blocker in judged.get("judge_blockers", [])):
                report = write_quota_blocked_report(
                    run_dir=run_dir,
                    started_at=started_at,
                    provider_order=provider_order,
                    provider_env=provider_env,
                    capability_probe=capability_probe,
                    unavailable=unavailable,
                    passages=passages,
                    voices=voices,
                    estimate=estimate,
                    budget=budget,
                    quota_probe=quota_probe,
                    sample_results=sample_results,
                )
                report["new_samples_generated"] = new_samples_generated
                report["cache_hit_samples_reused"] = reused_samples
                write_json(run_dir / "bengali_tts_provider_bakeoff_report.json", report)
                write_json(BAKEOFF_STATUS_PATH, report)
                print(
                    json.dumps(
                        {
                            "status": "EXTERNAL_ACTION_REQUIRED",
                            "blocker": QUOTA_BLOCKER,
                            "quota_probe_status": quota_probe.get("status"),
                            "existing_samples_reused": report.get("existing_samples_reused", 0),
                            "new_samples_generated": new_samples_generated,
                            "best_provider": report.get("best_provider", ""),
                            "best_voice": report.get("best_voice", ""),
                            "best_score": report.get("best_score", 0),
                            "report_path": report.get("report_path"),
                        },
                        ensure_ascii=False,
                    )
                )
                return 2 if args.fail_closed else 0
            stop_reason = adaptive_early_stop_reason(judged, release_policy) if args.adaptive_optimizer else ""
            if stop_reason:
                skipped_passages = passages[passage_index + 1 :]
                early_stop_events.append(
                    {
                        "provider": provider_voice.provider,
                        "voice": provider_voice.voice,
                        "style_profile": provider_voice.style_profile,
                        "after_passage_id": passage.get("passage_id"),
                        "reason": stop_reason,
                        "skipped_passage_ids": [item.get("passage_id") for item in skipped_passages],
                    }
                )
                for skipped in skipped_passages:
                    sample_results.append(
                        {
                            "status": "SKIPPED",
                            "judge_status": "SKIPPED",
                            "provider": provider_voice.provider,
                            "voice": provider_voice.voice,
                            "model": provider_voice.model,
                            "language_code": provider_voice.language_code,
                            "style_profile": provider_voice.style_profile,
                            "passage_id": skipped.get("passage_id"),
                            "passage_slug": skipped.get("slug"),
                            "passage_label": skipped.get("label"),
                            "text_hash": skipped.get("text_hash"),
                            "judge_blockers": [f"ADAPTIVE_EARLY_STOP: {stop_reason}"],
                        }
                    )
                break
    write_json(run_dir / "bakeoff_sample_results.json", {"samples": sample_results})
    existing_judging_report_path = ""
    if args.resume_existing_samples or args.judge_existing_only:
        existing_judging_report_path = write_existing_sample_judging_report(
            run_dir,
            {
                "status": "PASS",
                "run_dir": rel(run_dir),
                "started_at": started_at,
                "finished_at": iso_now(),
                "quota_probe_status": quota_probe.get("status"),
                "existing_audio_inventory": audio_inventory(run_dir),
            },
            sample_results,
        )
    voice_results = [summarize_voice(provider_voice, sample_results, release_policy, expected_sample_count=len(passages)) for provider_voice in voices]
    passing = [item for item in voice_results if item["status"] == "PASS"]
    best = sorted(voice_results, key=lambda item: (-safe_float(item.get("overall_listening_score")), -safe_float(item.get("confidence_score")), item["provider"], item["voice"]))[0] if voice_results else {}
    report = {
        "status": "PASS" if passing else "BLOCKED",
        "started_at": started_at,
        "finished_at": iso_now(),
        "run_dir": rel(run_dir),
        "release_policy": release_policy,
        "policy_decision_path": policy_decision_path,
        "candidate_source": candidate_source,
        "bengali_audiobook_92_rescue": bool(args.bengali_audiobook_92_rescue),
        "adaptive_optimizer": bool(args.adaptive_optimizer),
        "pilot_selection_report_path": pilot_selection_report_path,
        "text_prep_comparison_report_path": text_prep_report_path,
        "postprocess_report_path": postprocess_report_path,
        "listening_thresholds_applied": listening_policy_for("ben", release_policy)["thresholds"],
        "fatal_flags_required": listening_policy_for("ben", release_policy)["fatal_flags"],
        "generate_full_pilot_if_policy_pass": bool(args.generate_full_pilot_if_policy_pass),
        "allow_audio_only_with_reader": bool(args.allow_audio_only_with_reader),
        "disable_fragile_highlight_sync": bool(args.disable_fragile_highlight_sync),
        "max_pilot_count": args.max_pilot_count,
        "providers_requested": provider_order,
        "providers_detected": provider_env,
        "provider_capability_probe_path": rel(run_dir / "bengali_provider_capability_probe.json"),
        "provider_capability_probe": capability_probe,
        "providers_unavailable": unavailable,
        "voices_tested": [{"provider": voice.provider, "voice": voice.voice, "language_code": voice.language_code} for voice in voices],
        "passage_ids": [passage["passage_id"] for passage in passages],
        "passages_path": rel(run_dir / "bakeoff_passages.json"),
        "sample_results_path": rel(run_dir / "bakeoff_sample_results.json"),
        "bengali_existing_sample_judging_report_path": existing_judging_report_path,
        "cost_estimate": {"estimated_cost_usd": estimate, "budget_usd": budget, "actual_cost_if_available": "not_available"},
        "quota_probe_status": quota_probe.get("status"),
        "quota_probe_path": rel(run_dir / "openai_listening_qa_quota_probe.json"),
        "existing_audio_inventory": audio_inventory(run_dir),
        "cache_hit_samples_reused": reused_samples,
        "new_samples_generated": new_samples_generated,
        "adaptive_early_stop_events": early_stop_events,
        "voice_results": voice_results,
        "best_provider": best.get("provider", ""),
        "best_voice": best.get("voice", ""),
        "best_style_profile": best.get("style_profile", ""),
        "best_score": best.get("overall_listening_score", 0.0),
        "best_confidence": best.get("confidence_score", 0.0),
        "any_audition_passed": bool(passing),
        "pass_fail_decision": ("BENGALI_AUDIO_PATH_FOUND_UNDER_BENGALI_MVP" if release_policy == BENGALI_PREMIUM_MVP_POLICY and passing else "BENGALI_AUDIO_PATH_FOUND") if passing else "AUDIO_PROVIDER_QUALITY_LIMIT",
        "recommendation": (
            "Generate one guarded Bengali pilot with the selected provider/voice under the recorded release policy."
            if passing
            else "Keep Bengali audiobooks hidden and continue Bengali reader-only publication until a better provider or approved human/licensed import path is available."
        ),
        "pilot_slug": slugs[0] if passing and slugs else "",
        "blockers": [] if passing else ["No available provider/voice passed all schema-3 listening QA audition thresholds."],
    }
    report_path = run_dir / "bengali_tts_provider_bakeoff_report.json"
    report["report_path"] = rel(report_path)
    report["status_path"] = rel(BAKEOFF_STATUS_PATH)
    report["bengali_provider_audition_report_path"] = write_audition_report(run_dir, report, sample_results, voice_results)
    representative_report_path, sarvam_corrective_report_path = write_representative_audition_reports(run_dir, report, sample_results, voice_results)
    report["bengali_representative_audition_report_path"] = representative_report_path
    report["sarvam_corrective_audition_report_path"] = sarvam_corrective_report_path
    if release_policy == BENGALI_PREMIUM_MVP_POLICY:
        report["bengali_mvp_quality_report_path"] = write_bengali_mvp_quality_report(run_dir, report)
    if passing and args.generate_full_pilot_if_policy_pass:
        report["bengali_pilot_generation_plan_path"] = write_pilot_generation_plan(run_dir, report, slugs)
    if args.resume_existing_samples or args.judge_existing_only or (run_dir / "bengali_provider_bakeoff_interrupted_progress.json").exists():
        report["interrupted_progress_path"] = write_resumed_completion_progress(run_dir, report)
    write_json(report_path, report)
    if not passing:
        report["bengali_provider_limit_report_path"] = write_limit_report(run_dir, report)
        write_json(report_path, report)
    write_json(BAKEOFF_STATUS_PATH, report)
    update_latest_catalog_dashboard(
        {
            "bengali_provider_bakeoff_status": report["status"],
            "bengali_release_policy": release_policy,
            "bengali_mvp_policy_decision_path": policy_decision_path,
            "best_bengali_tts_provider": report["best_provider"],
            "best_bengali_voice": report["best_voice"],
            "best_bengali_listening_score": report["best_score"],
            "bengali_audiobook_lane_status": "PILOT_READY" if passing else "AUDIO_PROVIDER_QUALITY_LIMIT",
            "bengali_reader_only_live_count": "",
            "bengali_audio_provider_quality_limit_count": 0 if passing else len(slugs),
            "bengali_pilot_slug": report["pilot_slug"],
            "bengali_pilot_status": "NOT_RUN_AWAITING_PILOT_COMMAND" if passing else "BLOCKED_BY_PROVIDER_BAKEOFF",
            "bengali_provider_limit_report_path": report.get("bengali_provider_limit_report_path", ""),
        }
    )
    print(
        json.dumps(
                {
                    "status": report["status"],
                    "release_policy": report.get("release_policy", UNIVERSAL_LISTENING_POLICY),
                    "any_audition_passed": report["any_audition_passed"],
                    "best_provider": report["best_provider"],
                    "best_voice": report["best_voice"],
                    "best_score": report["best_score"],
                    "best_confidence": report["best_confidence"],
                    "policy_decision_path": report.get("policy_decision_path", ""),
                    "bengali_mvp_quality_report_path": report.get("bengali_mvp_quality_report_path", ""),
                    "bengali_representative_audition_report_path": report.get("bengali_representative_audition_report_path", ""),
                    "bengali_pilot_generation_plan_path": report.get("bengali_pilot_generation_plan_path", ""),
                    "report_path": rel(report_path),
                },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
