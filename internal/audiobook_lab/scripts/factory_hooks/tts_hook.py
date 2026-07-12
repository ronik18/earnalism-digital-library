#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    ROOT,
    download_url,
    fetch_url,
    ffprobe_duration,
    finish,
    load_public_book,
    parser,
    rel,
    run_cmd,
    sha256_file,
    sha256_text,
    validation_pass,
    word_tokens,
    write_clean_manuscript_if_missing,
    write_json,
    write_text,
)


TTS_MODEL = os.environ.get("EARNALISM_FACTORY_TTS_MODEL", "gpt-4o-mini-tts")
CACHE_DIR = ROOT / "internal" / "audiobook_lab" / "cache" / "release_factory_openai_tts"
DEFAULT_MAX_CHARS = int(os.environ.get("EARNALISM_FACTORY_MAX_TTS_CHARS", "60000"))
DEFAULT_TTS_ESTIMATED_USD_PER_1K_CHARS = float(os.environ.get("EARNALISM_TTS_ESTIMATED_USD_PER_1K_CHARS", "0.015"))
OPENAI_MAX_CHARS_PER_CHUNK = int(os.environ.get("EARNALISM_OPENAI_TTS_MAX_CHARS_PER_CHUNK", "2600"))
MIN_VALID_AUDIO_SECONDS = float(os.environ.get("EARNALISM_FACTORY_MIN_VALID_AUDIO_SECONDS", "3"))
OPENAI_TTS_TIMEOUT_SECONDS = float(os.environ.get("EARNALISM_OPENAI_TTS_TIMEOUT_SECONDS", "180"))
DEFAULT_SARVAM_FULL_PILOT_SLUG = "book-2b9853ec52"
DEFAULT_SARVAM_FULL_PILOT_MODEL = "bulbul:v3"
DEFAULT_SARVAM_FULL_PILOT_VOICE = "ratan"
DEFAULT_SARVAM_FULL_PILOT_STYLE = "literary_warm_pacing"
SARVAM_FULL_PILOT_SLUG = os.environ.get("EARNALISM_BENGALI_FULL_PILOT_SLUG", DEFAULT_SARVAM_FULL_PILOT_SLUG)
SARVAM_FULL_PILOT_MODEL = os.environ.get("EARNALISM_BENGALI_TTS_MODEL", DEFAULT_SARVAM_FULL_PILOT_MODEL)
SARVAM_FULL_PILOT_VOICE = os.environ.get("EARNALISM_BENGALI_TTS_VOICE", DEFAULT_SARVAM_FULL_PILOT_VOICE)
SARVAM_FULL_PILOT_STYLE = os.environ.get("EARNALISM_BENGALI_TTS_STYLE", DEFAULT_SARVAM_FULL_PILOT_STYLE)
SARVAM_MAX_CHARS_PER_GROUP = int(os.environ.get("EARNALISM_SARVAM_TTS_MAX_CHARS", "1400"))
SARVAM_TTS_ESTIMATED_USD_PER_1K_CHARS = float(os.environ.get("EARNALISM_SARVAM_ESTIMATED_USD_PER_1K_CHARS", "0.006"))
SARVAM_CACHE_DIR = ROOT / "internal" / "audiobook_lab" / "cache" / "release_factory_sarvam_tts"
FAST_ENGLISH_GENRE_SELECTION = os.environ.get("EARNALISM_FACTORY_FAST_ENGLISH_GENRE_SELECTION", "true").lower() in {
    "1",
    "true",
    "yes",
}
DISALLOWED_AUDIO_PROVENANCE_TOKENS = {
    "browser",
    "fallback",
    "offline",
    "piper",
    "placeholder",
    "robotic",
    "system",
    "system_tts",
}
DISALLOWED_ALIGNMENT_MODES = {"deterministic", "estimated", "synthetic"}


def profile_instructions(language: str, profile: str) -> str:
    if language == "ben":
        base = (
            "Narrate in Bengali as a premium literary storyteller. Use warm, human, intimate, expressive narration. "
            "Respect Bengali punctuation, natural sentence endings, comma pauses, paragraph pauses, and restrained emotional shading. "
            "Do not sound robotic, rushed, theatrical, synthetic, or like list reading. Narrate manuscript text only."
        )
        profiles = {
            "premium_bengali_literary_narrator": base,
            "bengali_storyteller_slow_punctuation": base + " Use slightly slower pacing and clearer punctuation-aware pauses.",
            "tagore_social_story_expressive_restraint": base + " Keep a Tagore short-story tone: socially observant, gentle, emotionally restrained.",
            "warm_documentary_bengali_reader": base + " Use clear Bengali pronunciation with a calm documentary warmth.",
        }
        return profiles[profile]
    profiles = {
        "classic_literary_narrator": "Narrate as a warm classic literary audiobook narrator with clear pacing, natural pauses, and restrained emotion.",
        "mystery_suspense_narrator": "Narrate with controlled suspense, human warmth, natural punctuation pauses, and no overacting.",
        "children_adventure_narrator": "Narrate with lively but polished adventure-story energy, clear diction, and natural sentence rhythm.",
        "nonfiction_business_narrator": "Narrate as a clear premium nonfiction reader with comfortable pacing and confident phrasing.",
    }
    return profiles.get(profile, profiles["classic_literary_narrator"])


def voices_for(language: str) -> list[str]:
    if language == "ben":
        return ["marin", "cedar", "verse", "coral", "alloy", "sage", "shimmer", "nova"]
    return ["verse", "alloy", "coral", "nova", "sage", "shimmer"]


def profiles_for(language: str) -> list[str]:
    if language == "ben":
        return [
            "premium_bengali_literary_narrator",
            "bengali_storyteller_slow_punctuation",
            "tagore_social_story_expressive_restraint",
            "warm_documentary_bengali_reader",
        ]
    return [
        "classic_literary_narrator",
        "mystery_suspense_narrator",
        "children_adventure_narrator",
        "nonfiction_business_narrator",
    ]


def bool_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "y", "on"}


def profile_selection_bonus(args, profile: str) -> float:
    if args.language == "ben":
        return 0.0
    context = f"{args.title} {args.author}".lower()
    gothic_or_suspense = any(
        token in context
        for token in (
            "poe",
            "tell-tale",
            "tell tale",
            "heart",
            "masque",
            "usher",
            "pit",
            "pendulum",
            "imp",
            "perverse",
            "mystery",
            "suspense",
            "gothic",
        )
    )
    child_or_adventure = any(token in context for token in ("children", "adventure", "oz", "alice", "garden"))
    nonfiction = any(token in context for token in ("money", "business", "scientific management", "getting rich"))
    if gothic_or_suspense:
        return 0.55 if profile == "mystery_suspense_narrator" else (-0.35 if profile == "children_adventure_narrator" else 0.0)
    if nonfiction:
        return 0.45 if profile == "nonfiction_business_narrator" else (-0.25 if profile == "children_adventure_narrator" else 0.0)
    if child_or_adventure:
        return 0.35 if profile == "children_adventure_narrator" else 0.0
    return 0.2 if profile == "classic_literary_narrator" else (-0.2 if profile == "children_adventure_narrator" else 0.0)


def preferred_english_profile(args) -> str:
    explicit = os.environ.get("EARNALISM_FACTORY_TTS_PROFILE", "").strip()
    if explicit in profiles_for("eng"):
        return explicit
    return sorted(
        profiles_for("eng"),
        key=lambda profile: (-profile_selection_bonus(args, profile), profile),
    )[0]


def preferred_voice(args) -> str:
    explicit = os.environ.get("EARNALISM_FACTORY_TTS_VOICE", "").strip()
    if explicit:
        return explicit
    return "verse" if args.language != "ben" else voices_for(args.language)[0]


def chunk_text(text: str, max_chars: int = 2600) -> list[dict]:
    # Canonical texts may contain a blank line after every source-wrapped line.
    # Treating those wraps as paragraph boundaries can reset a provider in the
    # middle of a sentence. Flatten whitespace first, then split at literary
    # sentence endings so every normal TTS chunk starts and ends on a complete
    # sentence.
    flattened = re.sub(r"\s+", " ", text or "").strip()
    sentences = [item.strip() for item in re.split(r"(?<=[।.!?])\s+", flattened) if item.strip()]
    units: list[str] = []
    for sentence in sentences:
        if len(sentence) <= max_chars:
            units.append(sentence)
            continue
        clauses = [item.strip() for item in re.split(r"(?<=[,;:])\s+", sentence) if item.strip()]
        current_clause: list[str] = []
        current_clause_len = 0
        for clause in clauses:
            if current_clause and current_clause_len + len(clause) + 1 > max_chars:
                units.append(" ".join(current_clause))
                current_clause = []
                current_clause_len = 0
            if len(clause) > max_chars:
                words = clause.split()
                while words:
                    part: list[str] = []
                    part_len = 0
                    while words and (not part or part_len + len(words[0]) + 1 <= max_chars):
                        word = words.pop(0)
                        part.append(word)
                        part_len += len(word) + 1
                    if part:
                        units.append(" ".join(part))
                continue
            current_clause.append(clause)
            current_clause_len += len(clause) + 1
        if current_clause:
            units.append(" ".join(current_clause))

    chunks: list[dict] = []
    current: list[str] = []
    current_len = 0
    for unit in units:
        if current and current_len + len(unit) + 1 > max_chars:
            text_value = " ".join(current).strip()
            chunks.append({"index": len(chunks), "text": text_value, "text_hash": sha256_text(text_value)})
            current = []
            current_len = 0
        current.append(unit)
        current_len += len(unit) + 1
    if current:
        text_value = " ".join(current).strip()
        chunks.append({"index": len(chunks), "text": text_value, "text_hash": sha256_text(text_value)})
    return chunks


def speech_create(client, *, voice: str, instructions: str, text: str, out_path: Path) -> None:
    kwargs = {"model": TTS_MODEL, "voice": voice, "input": text, "response_format": "mp3"}
    request_client = client
    if hasattr(client, "with_options"):
        request_client = client.with_options(timeout=OPENAI_TTS_TIMEOUT_SECONDS)
    try:
        response = request_client.audio.speech.create(**kwargs, instructions=instructions)
    except TypeError:
        response = request_client.audio.speech.create(**kwargs)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(response, "write_to_file"):
        response.write_to_file(out_path)
    else:
        out_path.write_bytes(response.read())


def select_voice(args, manuscript: str, client) -> dict:
    passage = " ".join(re.split(r"\s+", manuscript.strip()))[:900]
    if args.language != "ben" and FAST_ENGLISH_GENRE_SELECTION:
        voice = preferred_voice(args)
        profile = preferred_english_profile(args)
        instructions = profile_instructions(args.language, profile)
        instruction_hash = sha256_text(instructions)
        out_path = Path(args.run_dir) / "auditions" / f"{voice}_{profile}_{instruction_hash[:10]}.mp3"
        item = {
            "voice": voice,
            "profile": profile,
            "instruction_hash": instruction_hash,
            "path": rel(out_path),
            "status": "BLOCKED",
            "selector_score": round(selector_score(voice, profile, args.language) + profile_selection_bonus(args, profile), 2),
            "selection_mode": "fast_english_genre_selection",
        }
        try:
            speech_create(client, voice=voice, instructions=instructions, text=passage, out_path=out_path)
            item.update(
                {
                    "status": "PASS",
                    "sha256": sha256_file(out_path),
                    "duration_seconds": ffprobe_duration(out_path),
                }
            )
            return {"status": "PASS", "results": [item], "selected": item, "selection_mode": "fast_english_genre_selection"}
        except Exception as exc:  # noqa: BLE001
            item["error"] = str(exc)[:500]
            # Fall back to the exhaustive selector if the preferred candidate is
            # unsupported or transiently unavailable.
            fast_failure = item
    else:
        fast_failure = None
    results = []
    if fast_failure:
        results.append(fast_failure)
    for voice in voices_for(args.language):
        for profile in profiles_for(args.language):
            instructions = profile_instructions(args.language, profile)
            instruction_hash = sha256_text(instructions)
            out_path = Path(args.run_dir) / "auditions" / f"{voice}_{profile}_{instruction_hash[:10]}.mp3"
            item = {
                "voice": voice,
                "profile": profile,
                "instruction_hash": instruction_hash,
                "path": rel(out_path),
                "status": "BLOCKED",
                "selector_score": 0.0,
            }
            try:
                speech_create(client, voice=voice, instructions=instructions, text=passage, out_path=out_path)
                item.update(
                    {
                        "status": "PASS",
                        "selector_score": round(selector_score(voice, profile, args.language) + profile_selection_bonus(args, profile), 2),
                        "sha256": sha256_file(out_path),
                        "duration_seconds": ffprobe_duration(out_path),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                item["error"] = str(exc)[:500]
                if voice in {"marin", "cedar"}:
                    item["unsupported_candidate_recorded"] = True
            results.append(item)
    passing = [item for item in results if item["status"] == "PASS"]
    if not passing:
        return {"status": "BLOCKED", "results": results, "blockers": ["No OpenAI TTS audition candidate succeeded."]}
    selected = sorted(passing, key=lambda item: (-float(item["selector_score"]), item["voice"], item["profile"]))[0]
    return {"status": "PASS", "results": results, "selected": selected}


def selector_score(voice: str, profile: str, language: str) -> float:
    score = 8.0
    if language == "ben":
        score += {"verse": 0.5, "coral": 0.4, "sage": 0.3, "nova": 0.2, "alloy": 0.1}.get(voice, 0.0)
        if profile == "tagore_social_story_expressive_restraint":
            score += 0.35
        if profile == "bengali_storyteller_slow_punctuation":
            score += 0.25
    else:
        score += {"verse": 0.45, "coral": 0.35, "nova": 0.25, "alloy": 0.2}.get(voice, 0.0)
    return round(score, 2)


def concat_chunks(chunk_paths: list[Path], out_path: Path) -> dict:
    if not shutil.which("ffmpeg"):
        return {"ok": False, "error": "ffmpeg is required to concatenate TTS chunks."}
    concat_file = out_path.parent / "concat_chunks.txt"
    lines = [f"file '{path.resolve().as_posix()}'" for path in chunk_paths]
    write_text(concat_file, "\n".join(lines) + "\n")
    result = run_cmd(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            "-y",
            str(out_path),
        ],
        timeout=900,
    )
    return {"ok": result["returncode"] == 0, "command_result": result, "concat_file": rel(concat_file)}


def public_audio_url(public_book: dict) -> str:
    assets = public_book.get("audiobook_assets") if isinstance(public_book.get("audiobook_assets"), dict) else {}
    audiobook = public_book.get("audiobook") if isinstance(public_book.get("audiobook"), dict) else {}
    return str(assets.get("mp3") or audiobook.get("url") or "")


def sidecar_candidates(public_book: dict) -> dict[str, str]:
    assets = public_book.get("audiobook_assets") if isinstance(public_book.get("audiobook_assets"), dict) else {}
    audiobook = public_book.get("audiobook") if isinstance(public_book.get("audiobook"), dict) else {}
    nested = audiobook.get("assets") if isinstance(audiobook.get("assets"), dict) else {}
    return {
        "timestamps": str(assets.get("timestamps") or nested.get("timestamps") or ""),
        "vtt": str(assets.get("vtt") or nested.get("vtt") or ""),
        "chapters": str(assets.get("chapters") or nested.get("chapters") or ""),
        "meta": str(assets.get("meta") or nested.get("meta") or ""),
    }


def existing_audio_provenance(public_book: dict) -> dict:
    """Read non-secret provenance hints for existing mapped audiobook assets."""

    sidecars = sidecar_candidates(public_book)
    meta_url = sidecars.get("meta", "")
    evidence = {
        "public_book_audiobook_provider": public_book.get("audiobook_provider", ""),
        "public_book_audiobook_voice": public_book.get("audiobook_voice", ""),
        "meta_url": meta_url,
        "meta_status": 0,
        "meta": {},
    }
    if not meta_url:
        return evidence
    fetched = fetch_url(meta_url, timeout=30, max_bytes=1024 * 1024)
    evidence["meta_status"] = fetched.get("status")
    evidence["meta_resolves"] = fetched.get("ok")
    if not fetched.get("ok"):
        evidence["meta_error"] = fetched.get("error")
        return evidence
    try:
        evidence["meta"] = json.loads((fetched.get("body") or b"{}").decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        evidence["meta_parse_error"] = str(exc)[:300]
    return evidence


def release_unsafe_audio_provenance(provenance: dict) -> list[str]:
    blockers: list[str] = []
    meta = provenance.get("meta") if isinstance(provenance.get("meta"), dict) else {}
    provider_fields = [
        ("public_book_audiobook_provider", provenance.get("public_book_audiobook_provider", "")),
        ("provider_used", meta.get("provider_used", "")),
        ("provider", meta.get("provider", "")),
        ("voice", meta.get("voice", "")),
    ]
    for field, value in provider_fields:
        lowered = str(value or "").strip().lower()
        if not lowered:
            continue
        matched = sorted(token for token in DISALLOWED_AUDIO_PROVENANCE_TOKENS if token in lowered)
        if matched:
            blockers.append(
                f"Existing audio provenance is not release-approved: {field}={value!r} contains {', '.join(matched)}."
            )
    alignment_modes = meta.get("alignment_modes") or meta.get("sync_modes") or []
    if isinstance(alignment_modes, str):
        alignment_modes = [alignment_modes]
    unsafe_modes = sorted(
        mode
        for mode in (str(item).strip().lower() for item in alignment_modes)
        if mode in DISALLOWED_ALIGNMENT_MODES
    )
    if unsafe_modes:
        blockers.append(
            "Existing sidecar provenance is not release-approved: "
            f"alignment_modes include {', '.join(unsafe_modes)}."
        )
    if meta.get("auto_estimated_sync") is True:
        blockers.append("Existing sidecar provenance is not release-approved: auto_estimated_sync=true.")
    return blockers


def prior_asr_rejects_reused_audio(run_dir: Path) -> dict:
    """Detect previously reused audio that failed manuscript/source ASR gates."""

    asr_result = __import__("common").read_json(run_dir / "asr_sync_hook_result.json", {})
    tts_result = __import__("common").read_json(run_dir / "tts_hook_result.json", {})
    if asr_result.get("status") != "BLOCKED":
        return {"reject": False}
    artifacts = tts_result.get("artifacts") if isinstance(tts_result.get("artifacts"), dict) else {}
    reuse_source = str(artifacts.get("reuse_source") or artifacts.get("reuse", {}).get("reuse_source") or "").lower()
    if "existing" not in reuse_source and "local" not in reuse_source:
        return {"reject": False}
    metrics = asr_result.get("metrics") if isinstance(asr_result.get("metrics"), dict) else {}
    blockers = [str(item) for item in (asr_result.get("blockers") or [])]
    try:
        score = float(metrics.get("score") or metrics.get("transcript_match_score") or 0)
    except (TypeError, ValueError):
        score = 0.0
    source_mismatch = (
        asr_result.get("blocker_category") == "asr"
        and (
            score < 9.7
            or metrics.get("first_words_match") is False
            or metrics.get("last_words_match") is False
        )
    )
    if not source_mismatch:
        return {"reject": False}
    return {
        "reject": True,
        "reason": "Previously reused existing/local audio failed ASR manuscript-source gates.",
        "reuse_source": reuse_source,
        "asr_score": score,
        "first_words_match": metrics.get("first_words_match"),
        "last_words_match": metrics.get("last_words_match"),
        "blockers": blockers,
        "repair_action": "bypass reused audio and regenerate with approved OpenAI TTS if paid gate passes",
    }


def remote_audio_status(url: str) -> dict:
    if not url:
        return {"url": "", "status": 0, "ok": False, "error": "missing_url", "returns_404": False}
    fetched = fetch_url(url, timeout=30, max_bytes=2048)
    return {
        "url": url,
        "status": fetched.get("status"),
        "ok": fetched.get("ok"),
        "error": fetched.get("error"),
        "returns_404": fetched.get("status") == 404,
        "content_type": (fetched.get("headers") or {}).get("Content-Type", ""),
    }


def audio_path_diagnostics(path: Path) -> dict:
    exists = path.exists()
    size = path.stat().st_size if exists else 0
    duration = ffprobe_duration(path) if exists and size > 0 else None
    lowered = str(path).lower()
    rejected_reason = ""
    if not exists:
        rejected_reason = "missing"
    elif size <= 0:
        rejected_reason = "zero_byte"
    elif duration is None:
        rejected_reason = "ffprobe_failed"
    elif duration < MIN_VALID_AUDIO_SECONDS:
        rejected_reason = f"duration_below_{MIN_VALID_AUDIO_SECONDS}_seconds"
    elif any(token in lowered for token in ("fallback", "placeholder", "robotic", "system_tts", "browser_tts", "offline_tts")):
        rejected_reason = "path_indicates_fallback_or_placeholder_audio"
    return {
        "path": rel(path),
        "exists": exists,
        "bytes": size,
        "duration_seconds": duration,
        "sha256": sha256_file(path) if exists and size > 0 else "",
        "valid": not rejected_reason,
        "rejected_reason": rejected_reason,
    }


def local_audio_candidates(args, run_dir: Path) -> list[dict]:
    patterns = [
        run_dir / f"{args.slug}_openai_tts_final.mp3",
        run_dir / f"{args.slug}_existing_audio_candidate.mp3",
        ROOT / "internal" / "audiobook_lab" / "enhanced_candidates" / args.slug / f"{args.slug}_enhanced.mp3",
        ROOT / "internal" / "audiobook_lab" / "bengali_store_candidates" / args.slug / "improved_internal" / f"{args.slug}.mp3",
        ROOT / "data" / "controlled_publications" / args.slug / "audiobook.mp3",
    ]
    for older_run in sorted((ROOT / "internal" / "audiobook_lab" / "release_gate").glob(f"{args.slug}_*/{args.slug}*_final.mp3"), reverse=True):
        patterns.append(older_run)
    seen: set[Path] = set()
    candidates: list[dict] = []
    for path in patterns:
        if path in seen:
            continue
        seen.add(path)
        diag = audio_path_diagnostics(path)
        if diag["exists"]:
            candidates.append(diag)
    return candidates


def best_valid_local_audio(args, run_dir: Path) -> dict | None:
    candidates = local_audio_candidates(args, run_dir)
    valid = [item for item in candidates if item.get("valid")]
    if not valid:
        return None
    enhanced = [item for item in valid if "/enhanced_candidates/" in item["path"]]
    return (enhanced or valid)[0]


def inspect_sidecars(public_book: dict, local_audio_hash: str) -> dict:
    sidecars = sidecar_candidates(public_book)
    result: dict[str, dict] = {}
    for name, url in sidecars.items():
        if not url:
            result[name] = {"url": "", "resolves": False, "status": 0, "matches_local_audio_hash": False}
            continue
        fetched = fetch_url(url, timeout=30, max_bytes=1024 * 1024)
        matches = False
        if fetched.get("ok") and name == "meta":
            try:
                meta = json.loads((fetched.get("body") or b"{}").decode("utf-8"))
                matches = bool(local_audio_hash and meta.get("audio_hash") == local_audio_hash)
            except Exception:
                matches = False
        result[name] = {
            "url": url,
            "resolves": fetched.get("ok"),
            "status": fetched.get("status"),
            "matches_local_audio_hash": matches,
        }
    all_resolve = all(item.get("resolves") for item in result.values()) if result else False
    meta_matches = bool(result.get("meta", {}).get("matches_local_audio_hash"))
    return {
        "sidecars": result,
        "sidecars_exist": all_resolve,
        "sidecars_match_local_audio_hash": meta_matches,
        "sidecars_need_rebuild": not (all_resolve and meta_matches),
    }


def estimated_tts_cost_usd(text: str) -> float:
    return round((len(text) / 1000.0) * DEFAULT_TTS_ESTIMATED_USD_PER_1K_CHARS, 4)


def write_cost_decision(run_dir: Path, payload: dict) -> str:
    path = run_dir / "cost_optimization_decision.json"
    write_json(path, payload)
    return rel(path)


def estimated_sarvam_cost_usd(text: str) -> float:
    return round((len(text) / 1000.0) * SARVAM_TTS_ESTIMATED_USD_PER_1K_CHARS, 4)


def paid_tts_preflight(manuscript: str) -> dict:
    approved = os.environ.get("EARNALISM_APPROVE_PAID_OPENAI_TTS", "").lower() in {"1", "true", "yes"}
    stop_on_budget = os.environ.get("EARNALISM_STOP_ON_BUDGET_EXCEEDED", "").lower() in {"1", "true", "yes"}
    budget_raw = os.environ.get("EARNALISM_TTS_MAX_ESTIMATED_USD", "")
    try:
        budget = float(budget_raw) if budget_raw else None
    except ValueError:
        budget = None
    estimate = estimated_tts_cost_usd(manuscript)
    blockers: list[str] = []
    if not approved:
        blockers.append("EARNALISM_APPROVE_PAID_OPENAI_TTS=true is required before paid audio regeneration.")
    if budget is None:
        blockers.append("EARNALISM_TTS_MAX_ESTIMATED_USD is required before paid audio regeneration.")
    if not stop_on_budget:
        blockers.append("EARNALISM_STOP_ON_BUDGET_EXCEEDED=true is required before paid audio regeneration.")
    if budget is not None and stop_on_budget and estimate > budget:
        blockers.append(f"Estimated TTS cost ${estimate:.4f} exceeds configured budget ${budget:.4f}.")
    return {
        "paid_tts_approval_detected": approved,
        "tts_budget_limit": budget,
        "tts_estimated_cost": estimate,
        "tts_estimated_usd_per_1k_chars": DEFAULT_TTS_ESTIMATED_USD_PER_1K_CHARS,
        "stop_on_budget_exceeded": stop_on_budget,
        "passes": not blockers,
        "blockers": blockers,
    }


def sarvam_requested(args) -> bool:
    provider = os.environ.get("EARNALISM_BENGALI_TTS_PROVIDER", "").strip().lower()
    return provider == "sarvam" or (args.language == "ben" and bool_env("EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS"))


def matching_representative_pass(args) -> dict:
    paths: list[Path] = []
    override = os.environ.get("EARNALISM_BENGALI_REPRESENTATIVE_EVIDENCE_PATH", "").strip()
    if override:
        paths.append(resolve_optional_path(override))
    paths.append(ROOT / "bengali_representative_audition_report.json")
    paths.extend(sorted((ROOT / "internal" / "audiobook_lab" / "release_gate").glob("bengali_tts_provider_bakeoff_*/bengali_representative_audition_report.json"), reverse=True))
    for path in paths:
        report = __import__("common").read_json(path, {})
        if not report:
            continue
        candidates = [
            {
                "slug": report.get("pilot_candidate_selected"),
                "provider": report.get("provider"),
                "model": report.get("model"),
                "voice": report.get("voice"),
                "style": report.get("best_style_profile") or report.get("style_profile"),
                "score": report.get("representative_score"),
                "confidence": report.get("confidence"),
                "fatal_flags": report.get("fatal_flags_required"),
                "passed": report.get("representative_passed_9_2") is True,
                "evidence_kind": "top_level_representative",
                "passage_id": None,
            }
        ]
        for passage in report.get("passage_scores") or []:
            if not isinstance(passage, dict):
                continue
            candidates.append(
                {
                    "slug": passage.get("passage_slug"),
                    "provider": passage.get("provider"),
                    "model": passage.get("model"),
                    "voice": passage.get("voice"),
                    "style": passage.get("style_profile"),
                    "score": passage.get("overall_listening_score"),
                    "confidence": passage.get("confidence_score"),
                    "fatal_flags": passage.get("red_flags"),
                    "passed": passage.get("status") == "PASS" and not (passage.get("blockers") or []),
                    "evidence_kind": "title_specific_passage",
                    "passage_id": passage.get("passage_id"),
                }
            )
        for candidate in candidates:
            try:
                score = float(candidate.get("score") or 0)
                confidence = float(candidate.get("confidence") or 0)
            except (TypeError, ValueError):
                continue
            fatal_flags = candidate.get("fatal_flags") if isinstance(candidate.get("fatal_flags"), dict) else {}
            true_flags = [name for name, value in fatal_flags.items() if bool(value)]
            exact_arm = (
                candidate.get("slug") == args.slug
                and str(candidate.get("provider") or "").strip().lower() == "sarvam"
                and str(candidate.get("model") or "").strip() == SARVAM_FULL_PILOT_MODEL
                and str(candidate.get("voice") or "").strip() == SARVAM_FULL_PILOT_VOICE
                and str(candidate.get("style") or "").strip() == SARVAM_FULL_PILOT_STYLE
            )
            if exact_arm and candidate.get("passed") and score >= 9.2 and confidence >= 0.90 and not true_flags:
                return {
                    "status": "PASS",
                    "path": rel(path),
                    "score": score,
                    "confidence": confidence,
                    "evidence_kind": candidate.get("evidence_kind"),
                    "passage_id": candidate.get("passage_id"),
                    "report": report,
                }
    return {
        "status": "BLOCKED",
        "blockers": [
            "No representative audition evidence matches "
            f"{args.slug} + Sarvam {SARVAM_FULL_PILOT_MODEL} + {SARVAM_FULL_PILOT_VOICE} + "
            f"{SARVAM_FULL_PILOT_STYLE} with score >=9.2/confidence >=0.90/no fatal flags."
        ],
    }


def sarvam_full_pilot_preflight(args, manuscript: str) -> dict:
    blockers: list[str] = []
    if args.language != "ben":
        blockers.append("Guarded Sarvam Bengali full-pilot TTS is only available for Bengali titles.")
    if args.slug != SARVAM_FULL_PILOT_SLUG:
        blockers.append(f"Guarded Sarvam full-pilot TTS is limited to {SARVAM_FULL_PILOT_SLUG}; requested {args.slug}.")
    if os.environ.get("EARNALISM_BENGALI_TTS_PROVIDER", "").strip().lower() != "sarvam":
        blockers.append("EARNALISM_BENGALI_TTS_PROVIDER=sarvam is required.")
    if SARVAM_FULL_PILOT_MODEL != DEFAULT_SARVAM_FULL_PILOT_MODEL:
        blockers.append("Frozen Bengali pilot arm requires EARNALISM_BENGALI_TTS_MODEL=bulbul:v3.")
    title_specific_arm = (
        args.slug != DEFAULT_SARVAM_FULL_PILOT_SLUG
        or SARVAM_FULL_PILOT_VOICE != DEFAULT_SARVAM_FULL_PILOT_VOICE
        or SARVAM_FULL_PILOT_STYLE != DEFAULT_SARVAM_FULL_PILOT_STYLE
    )
    if title_specific_arm and not bool_env("EARNALISM_ALLOW_TITLE_SPECIFIC_BENGALI_TTS_ARM"):
        blockers.append("EARNALISM_ALLOW_TITLE_SPECIFIC_BENGALI_TTS_ARM=true is required for a non-default title/voice/style arm.")
    if not title_specific_arm and SARVAM_FULL_PILOT_VOICE != DEFAULT_SARVAM_FULL_PILOT_VOICE:
        blockers.append("Frozen Bengali pilot arm requires EARNALISM_BENGALI_TTS_VOICE=ratan.")
    if not title_specific_arm and SARVAM_FULL_PILOT_STYLE != DEFAULT_SARVAM_FULL_PILOT_STYLE:
        blockers.append("Frozen Bengali pilot arm requires EARNALISM_BENGALI_TTS_STYLE=literary_warm_pacing.")
    if not bool_env("EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS"):
        blockers.append("EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS=true is required.")
    if not bool_env("EARNALISM_STOP_ON_BUDGET_EXCEEDED"):
        blockers.append("EARNALISM_STOP_ON_BUDGET_EXCEEDED=true is required.")
    budget_raw = os.environ.get("EARNALISM_BENGALI_FULL_PILOT_MAX_ESTIMATED_USD", "").strip()
    try:
        budget = float(budget_raw) if budget_raw else None
    except ValueError:
        budget = None
    estimate = estimated_sarvam_cost_usd(manuscript)
    if budget is None:
        blockers.append("EARNALISM_BENGALI_FULL_PILOT_MAX_ESTIMATED_USD is required.")
    elif bool_env("EARNALISM_STOP_ON_BUDGET_EXCEEDED") and estimate > budget:
        blockers.append(f"Estimated Sarvam TTS cost ${estimate:.4f} exceeds configured budget ${budget:.4f}.")
    if not os.environ.get("SARVAM_API_KEY"):
        blockers.append("SARVAM_API_KEY is required for Sarvam full-pilot TTS.")
    representative = matching_representative_pass(args)
    if representative.get("status") != "PASS":
        blockers.extend(representative.get("blockers") or [])
    return {
        "passes": not blockers,
        "blockers": blockers,
        "tts_estimated_cost": estimate,
        "tts_budget_limit": budget,
        "tts_estimated_usd_per_1k_chars": SARVAM_TTS_ESTIMATED_USD_PER_1K_CHARS,
        "representative_evidence": representative,
    }


def strip_bengali_tts_frontmatter(text: str) -> str:
    """Remove source/edition headers from narration-only Bengali text.

    The canonical reader manuscript remains unchanged. This guarded pilot hook
    must not narrate collection names, page references, repository labels, or
    other source/frontmatter lines as audiobook content.
    """

    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    title_page_lines = {"দুই বিঘা জমি", "দুই বিঘা জমি।"}
    start_index = 0
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            start_index = index + 1
            continue
        lowered = stripped.lower()
        title_page_boilerplate = (
            stripped in title_page_lines
            and any("পৃ" in item or item in {"চিত্রা", "গল্পগুচ্ছ"} for item in non_empty_lines[: index + 1])
        )
        source_like = (
            "wikisource" in lowered
            or "gutenberg" in lowered
            or "repository" in lowered
            or "source:" in lowered
            or bool(re.search(r"পৃ[.\s]", stripped))
            or "পৃষ্ঠা" in stripped
            or stripped in {"চিত্রা", "গল্পগুচ্ছ"}
            or bool(re.fullmatch(r"[০-৯\d]{3,4}(?:\s*[।.]?|\s*\(.+\))", stripped))
            or title_page_boilerplate
        )
        # The pilot source starts with author/collection/date/title-page
        # metadata. Narration starts at the first literary body line.
        leading_credit_without_sentence_end = (
            index == 0
            and not re.search(r"[।.!?,;:—–]$", stripped)
            and len(re.findall(r"[\u0980-\u09ff0-9]+", stripped)) <= 4
        )
        if source_like or leading_credit_without_sentence_end:
            start_index = index + 1
            continue
        break
    return "\n".join(lines[start_index:]).strip()


def strip_bengali_tts_backmatter(text: str, *, source_frontmatter_removed: bool) -> str:
    """Remove a trailing standalone edition year only for source-wrapped text."""

    if not source_frontmatter_removed:
        return text.strip()
    lines = text.rstrip().splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and re.fullmatch(r"[০-৯\d]{3,4}\s*[?？]?[।.]?", lines[-1].strip()):
        lines.pop()
    return "\n".join(lines).strip()


def prepared_text_source_terms(text: str) -> list[str]:
    banned = ["wikisource", "gutenberg", "repository", "source:", "পৃষ্ঠা", "গল্পগুচ্ছ"]
    lowered = text.lower()
    terms = [term for term in banned if term in lowered]
    if re.search(r"পৃ[.\s]", text):
        terms.append("পৃ.")
    return terms


def prepare_bengali_tts_text(text: str) -> str:
    prepared = strip_bengali_tts_frontmatter(text)
    prepared = strip_bengali_tts_backmatter(prepared, source_frontmatter_removed=prepared.strip() != text.strip())
    prepared = re.sub(r"[\u200c\u200d]", "", prepared)
    prepared = re.sub(r"[ \t]+", " ", prepared)
    prepared = re.sub(r"\s+([।,;:!?])", r"\1", prepared)
    prepared = re.sub(r"([।!?])\s+", r"\1\n\n", prepared)
    prepared = re.sub(r"\n{3,}", "\n\n", prepared)
    return prepared.strip() + "\n"


def bengali_tts_content_key(text: str) -> str:
    return "".join(
        ch
        for ch in re.sub(r"[\u200c\u200d]", "", text or "")
        if ("\u0980" <= ch <= "\u09ff") or ch.isdigit()
    )


def sarvam_groups(text: str, max_chars: int = SARVAM_MAX_CHARS_PER_GROUP) -> list[dict]:
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]
    groups: list[dict] = []
    current: list[str] = []
    current_len = 0
    for paragraph in paragraphs:
        pieces = [paragraph] if len(paragraph) <= max_chars else re.split(r"(?<=[।.!?])\s+", paragraph)
        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue
            if current and current_len + len(piece) + 2 > max_chars:
                value = "\n\n".join(current).strip()
                groups.append({"index": len(groups), "text": value, "text_hash": sha256_text(value)})
                current = []
                current_len = 0
            current.append(piece)
            current_len += len(piece) + 2
    if current:
        value = "\n\n".join(current).strip()
        groups.append({"index": len(groups), "text": value, "text_hash": sha256_text(value)})
    return groups


def resolve_optional_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def sarvam_group_repair_manifest_path() -> Path | None:
    raw = os.environ.get("EARNALISM_SARVAM_GROUP_REPAIR_MANIFEST", "").strip()
    return resolve_optional_path(raw) if raw else None


def build_sarvam_group_repair_groups(args, prepared_text: str, manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    blockers: list[str] = []
    if str(manifest.get("slug") or "") != args.slug:
        blockers.append(f"repair manifest slug mismatch: {manifest.get('slug')} != {args.slug}")
    if str(manifest.get("provider") or "").lower() != "sarvam":
        blockers.append("repair manifest provider is not Sarvam")
    if str(manifest.get("model") or "") != SARVAM_FULL_PILOT_MODEL:
        blockers.append("repair manifest model does not match frozen Sarvam model")
    if str(manifest.get("voice") or "") != SARVAM_FULL_PILOT_VOICE:
        blockers.append("repair manifest voice does not match frozen Sarvam voice")
    if str(manifest.get("profile") or manifest.get("style") or "") != SARVAM_FULL_PILOT_STYLE:
        blockers.append("repair manifest style/profile does not match frozen Sarvam style")
    source_chunks = manifest.get("chunks")
    if not isinstance(source_chunks, list) or not source_chunks:
        blockers.append("repair manifest has no chunks")
    if blockers:
        return {"status": "BLOCKED", "blockers": blockers}

    groups: list[dict] = []
    regenerated_group_ids: list[int] = []
    reused_group_ids: list[int] = []
    for chunk in source_chunks:
        old_text = str(chunk.get("text") or "").strip()
        if not old_text:
            blockers.append(f"repair manifest group {chunk.get('index')} has empty text")
            continue
        cleaned_text = prepare_bengali_tts_text(old_text).strip()
        old_key = bengali_tts_content_key(old_text)
        cleaned_key = bengali_tts_content_key(cleaned_text)
        changed = old_key != cleaned_key
        group_text = cleaned_text if changed else old_text
        group = {
            "index": int(chunk.get("index", len(groups))),
            "text": group_text,
            "text_hash": sha256_text(group_text),
            "repair_source_text_hash": sha256_text(old_text),
            "repair_action": "REGENERATE_CLEANED_GROUP" if changed else "REUSE_UNAFFECTED_GROUP",
            "previous_path": chunk.get("path"),
            "previous_sha256": chunk.get("sha256"),
            "previous_duration_seconds": chunk.get("duration_seconds"),
            "removed_source_terms": prepared_text_source_terms(old_text),
        }
        if changed:
            regenerated_group_ids.append(group["index"])
        else:
            reused_group_ids.append(group["index"])
            group["reuse_audio_path"] = str(chunk.get("path") or "")
        groups.append(group)

    repaired_key = bengali_tts_content_key("\n\n".join(group["text"] for group in groups))
    prepared_key = bengali_tts_content_key(prepared_text)
    if repaired_key != prepared_key:
        blockers.append("repaired group sequence does not match audiobook-clean prepared manuscript")
    if blockers:
        return {"status": "BLOCKED", "blockers": blockers, "groups": groups}
    return {
        "status": "PASS",
        "manifest_path": rel(manifest_path),
        "groups": groups,
        "regenerated_group_ids": regenerated_group_ids,
        "reused_group_ids": reused_group_ids,
        "repaired_group_sequence_hash": sha256_text("\n\n".join(group["text"] for group in groups)),
        "prepared_text_hash": sha256_text(prepared_text),
    }


def concat_audio_chunks(chunk_paths: list[Path], out_path: Path) -> dict:
    if not shutil.which("ffmpeg"):
        return {"ok": False, "error": "ffmpeg is required to concatenate Sarvam chunks."}
    concat_file = out_path.parent / "sarvam_concat_chunks.txt"
    lines = [f"file '{path.resolve().as_posix()}'" for path in chunk_paths]
    write_text(concat_file, "\n".join(lines) + "\n")
    result = run_cmd(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-af",
            "loudnorm=I=-18:TP=-2:LRA=11,atrim=start=0",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            "-y",
            str(out_path),
        ],
        timeout=900,
    )
    return {"ok": result["returncode"] == 0, "command_result": result, "concat_file": rel(concat_file)}


def generate_sarvam_full_pilot(args, run_dir: Path, manuscript_path: Path, manuscript: str, preflight: dict) -> dict:
    sys.path.insert(0, str(ROOT / "internal" / "audiobook_lab" / "scripts" / "providers"))
    import sarvam_tts_adapter

    prepared = prepare_bengali_tts_text(manuscript)
    source_hash = sha256_text(manuscript)
    prepared_hash = sha256_text(prepared)
    source_terms = prepared_text_source_terms(prepared)
    if source_terms:
        raise RuntimeError(f"Prepared Bengali TTS text still contains source/frontmatter terms: {', '.join(source_terms)}")
    repair_manifest = sarvam_group_repair_manifest_path()
    repair_plan = None
    if repair_manifest:
        repair_plan = build_sarvam_group_repair_groups(args, prepared, repair_manifest)
        if repair_plan.get("status") != "PASS":
            raise RuntimeError(
                "Sarvam group repair plan failed: "
                + "; ".join(str(item) for item in (repair_plan.get("blockers") or ["unknown repair blocker"]))
            )
        groups = repair_plan["groups"]
    else:
        groups = sarvam_groups(prepared)
    grouping_hash = sha256_text(json.dumps([{"index": group["index"], "text_hash": group["text_hash"]} for group in groups], sort_keys=True))
    chunk_paths: list[Path] = []
    manifest_chunks: list[dict] = []
    cache_hits = 0
    cache_misses = 0
    for group in groups:
        cache_key = sha256_text(
            json.dumps(
                {
                    "slug": args.slug,
                    "source_hash": source_hash,
                    "prepared_hash": prepared_hash,
                    "grouping_hash": grouping_hash,
                    "provider": "sarvam",
                    "model": SARVAM_FULL_PILOT_MODEL,
                    "voice": SARVAM_FULL_PILOT_VOICE,
                    "style": SARVAM_FULL_PILOT_STYLE,
                    "language_code": sarvam_tts_adapter.DEFAULT_LANGUAGE,
                    "index": group["index"],
                    "text_hash": group["text_hash"],
                },
                sort_keys=True,
            )
        )
        cached = SARVAM_CACHE_DIR / args.slug / SARVAM_FULL_PILOT_MODEL.replace(":", "_") / SARVAM_FULL_PILOT_VOICE / f"{cache_key}.wav"
        target = run_dir / "sarvam_tts_chunks" / f"group_{group['index']:04d}_{cache_key[:12]}.wav"
        reuse_audio_path = str(group.get("reuse_audio_path") or "").strip()
        if reuse_audio_path:
            source = resolve_optional_path(reuse_audio_path)
            if not source.exists():
                raise RuntimeError(f"Repair reuse audio path does not exist: {reuse_audio_path}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            cache_status = "REUSED_UNAFFECTED_GROUP"
            cache_hits += 1
        elif cached.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cached, target)
            cache_status = "HIT"
            cache_hits += 1
        else:
            sarvam_tts_adapter.synthesize(
                group["text"],
                target,
                speaker=SARVAM_FULL_PILOT_VOICE,
                model=SARVAM_FULL_PILOT_MODEL,
                language_code=sarvam_tts_adapter.DEFAULT_LANGUAGE,
                output_codec=sarvam_tts_adapter.DEFAULT_CODEC,
            )
            cached.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, cached)
            cache_status = "MISS_GENERATED"
            cache_misses += 1
        chunk_paths.append(target)
        manifest_chunks.append(
            {
                **group,
                "path": rel(target),
                "sha256": sha256_file(target),
                "duration_seconds": ffprobe_duration(target),
                "cache_status": cache_status,
                "repair_action": group.get("repair_action"),
                "previous_path": group.get("previous_path"),
                "previous_sha256": group.get("previous_sha256"),
                "previous_duration_seconds": group.get("previous_duration_seconds"),
            }
        )
    arm_name = "_".join(
        re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_")
        for value in (SARVAM_FULL_PILOT_MODEL, SARVAM_FULL_PILOT_VOICE, SARVAM_FULL_PILOT_STYLE)
    )
    final_audio = run_dir / f"{args.slug}_sarvam_{arm_name}_final.mp3"
    concat = concat_audio_chunks(chunk_paths, final_audio)
    if not concat["ok"] or not final_audio.exists() or final_audio.stat().st_size <= 0:
        raise RuntimeError("Final Sarvam audio concatenation failed.")
    final_hash = sha256_file(final_audio)
    duration = ffprobe_duration(final_audio)
    report = {
        "slug": args.slug,
        "title": args.title,
        "author": args.author,
        "language": args.language,
        "status": "PASS",
        "provider": "sarvam",
        "model": SARVAM_FULL_PILOT_MODEL,
        "voice": SARVAM_FULL_PILOT_VOICE,
        "style": SARVAM_FULL_PILOT_STYLE,
        "language_code": sarvam_tts_adapter.DEFAULT_LANGUAGE,
        "source_text_hash": source_hash,
        "tts_prepared_text_hash": prepared_hash,
        "tts_source_sanitization": {
            "frontmatter_stripped": prepared.strip() != manuscript.strip(),
            "forbidden_source_terms_in_prepared_text": source_terms,
        },
        "grouping_hash": grouping_hash,
        "clean_manuscript_path": rel(manuscript_path),
        "group_count": len(groups),
        "group_repair": repair_plan or {"status": "NOT_REQUESTED"},
        "chunks": manifest_chunks,
        "final_audio_path": rel(final_audio),
        "final_audio_hash": final_hash,
        "generated_duration_seconds": duration,
        "cost_estimate": {
            "estimated_cost_usd": preflight["tts_estimated_cost"],
            "budget_usd": preflight["tts_budget_limit"],
            "estimated_usd_per_1k_chars": SARVAM_TTS_ESTIMATED_USD_PER_1K_CHARS,
            "actual_cost_if_available": "not_available",
        },
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "safe_postprocess": ["concat", "loudness_normalization"],
        "fallback_tts_used": False,
        "local_audio_reused": False,
        "stale_audio_reused": False,
        "representative_evidence": preflight.get("representative_evidence", {}),
        "blocker_list": [],
    }
    report_path = run_dir / "sarvam_full_pilot_tts_report.json"
    root_report_path = ROOT / "sarvam_full_pilot_tts_report.json"
    write_json(report_path, report)
    write_json(root_report_path, report)
    manifest = {
        "slug": args.slug,
        "source_hash": source_hash,
        "tts_prepared_text_hash": prepared_hash,
        "tts_source_sanitization": {
            "frontmatter_stripped": prepared.strip() != manuscript.strip(),
            "forbidden_source_terms_in_prepared_text": source_terms,
        },
        "grouping_hash": grouping_hash,
        "group_repair": repair_plan or {"status": "NOT_REQUESTED"},
        "provider": "sarvam",
        "model": SARVAM_FULL_PILOT_MODEL,
        "voice": SARVAM_FULL_PILOT_VOICE,
        "profile": SARVAM_FULL_PILOT_STYLE,
        "fallback_tts_used": False,
        "local_audio_reused": False,
        "stale_audio_reused": False,
        "chunks": manifest_chunks,
        "final_audio_path": rel(final_audio),
        "final_audio_hash": final_hash,
        "duration_seconds": duration,
        "word_count": len(word_tokens(manuscript)),
        "sarvam_full_pilot_tts_report": rel(report_path),
    }
    manifest_path = run_dir / "tts_chunk_manifest.json"
    write_json(manifest_path, manifest)
    cost_decision = write_cost_decision(
        run_dir,
        {
            "slug": args.slug,
            "stage": "tts",
            "blocker": "",
            "options": ["reuse_existing_or_local_audio", "regenerate_openai_tts", "generate_guarded_sarvam_full_pilot"],
            "selected_option": "generate_guarded_sarvam_full_pilot",
            "reason": "Representative Bengali audition passed for the frozen Sarvam arm; stale reuse and fallback TTS are disallowed.",
            "estimated_cost_usd": preflight["tts_estimated_cost"],
            "estimated_time_seconds": None,
            "quality_impact": "full-book Sarvam pilot; ASR/sync/listening/upload/metadata/browser gates remain mandatory",
            "artifacts_reused": [],
            "artifacts_regenerated": [rel(final_audio)],
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "paid_api_calls": cache_misses > 0,
            "budget_status": "approved_within_budget",
            "risk": "full-book consistency and objective gates remain unproven until downstream stages pass",
        },
    )
    return {
        "final_audio": final_audio,
        "manifest_path": manifest_path,
        "report_path": report_path,
        "report": report,
        "cost_decision": cost_decision,
    }


def existing_audio_reuse(args, public_book: dict) -> dict | None:
    url = public_audio_url(public_book)
    if not url:
        return None
    assets = public_book.get("audiobook_assets") if isinstance(public_book.get("audiobook_assets"), dict) else {}
    out_path = Path(args.run_dir) / f"{args.slug}_existing_audio_candidate.mp3"
    downloaded = download_url(url, out_path)
    if not downloaded["ok"]:
        status = downloaded.get("status")
        category = "stale_audio_url" if status == 404 else "tts"
        local_candidates = local_audio_candidates(args, Path(args.run_dir))
        best_local = best_valid_local_audio(args, Path(args.run_dir))
        local_hash = str(best_local.get("sha256") or "") if best_local else ""
        sidecars = inspect_sidecars(public_book, local_hash) if best_local else {"sidecars_exist": False, "sidecars_match_local_audio_hash": False, "sidecars_need_rebuild": True}
        return {
            "status": "BLOCKED",
            "blocker_category": category,
            "blockers": [f"Existing audio URL is stale or missing: {downloaded.get('status')} {downloaded.get('error')}"],
            "metrics": {
                **downloaded,
                "existing_audio_url": url,
                "audio_url_404": status == 404,
                "local_audio_candidates": local_candidates,
                "valid_local_audio_found": bool(best_local),
                "best_local_audio": best_local or {},
                **sidecars,
            },
        }
    diag = audio_path_diagnostics(out_path)
    if not diag["valid"]:
        return {
            "status": "BLOCKED",
            "blocker_category": "tts",
            "blockers": [f"Downloaded existing audio is invalid: {diag['rejected_reason']}"],
            "metrics": {"download": downloaded, "audio_diagnostics": diag, "existing_audio_url": url},
        }
    provenance = existing_audio_provenance(public_book)
    provenance_blockers = release_unsafe_audio_provenance(provenance)
    if provenance_blockers:
        return {
            "status": "BLOCKED",
            "blocker_category": "audio_provenance_not_approved",
            "blockers": provenance_blockers,
            "metrics": {
                "download": downloaded,
                "audio_diagnostics": diag,
                "existing_audio_url": url,
                "audio_provenance": provenance,
                "audio_regeneration_required": True,
                "force_regenerate_openai_tts": True,
            },
        }
    return {
        "status": "PASS",
        "final_audio_path": rel(out_path),
        "final_audio_hash": sha256_file(out_path),
        "duration_seconds": ffprobe_duration(out_path),
        "reuse_source": "existing_public_book_audio_assets",
        "audiobook_assets": assets,
        "fallback_tts_used": False,
    }


def local_audio_reuse(args, public_book: dict) -> dict | None:
    run_dir = Path(args.run_dir)
    best_local = best_valid_local_audio(args, run_dir)
    if not best_local:
        return None
    source = ROOT / best_local["path"]
    target = run_dir / f"{args.slug}_local_audio_reuse.mp3"
    if source.resolve() != target.resolve():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    target_diag = audio_path_diagnostics(target)
    sidecars = inspect_sidecars(public_book, target_diag.get("sha256") or "")
    result_path = run_dir / "local_audio_reuse_report.json"
    report = {
        "slug": args.slug,
        "status": "PASS",
        "source_audio": best_local,
        "reused_audio_path": rel(target),
        "reused_audio_hash": target_diag.get("sha256"),
        "duration_seconds": target_diag.get("duration_seconds"),
        **sidecars,
        "repair_action": "reuse valid local audio; send to ASR/sync hook to rebuild or validate sidecars",
    }
    write_json(result_path, report)
    return {
        "status": "PASS",
        "final_audio_path": rel(target),
        "final_audio_hash": target_diag.get("sha256"),
        "duration_seconds": target_diag.get("duration_seconds"),
        "reuse_source": "valid_local_audio_artifact",
        "local_audio_reused": True,
        "sidecars_need_rebuild": sidecars["sidecars_need_rebuild"],
        "sidecar_inspection": sidecars,
        "fallback_tts_used": False,
        "local_audio_reuse_report": rel(result_path),
    }


def main() -> int:
    args = parser().parse_args()
    started = __import__("common").iso_now()
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    if args.dry_run or args.slug == "__hook_validation__":
        return validation_pass(
            args,
            "tts",
            started,
            {
                "openai_api_key_detected": bool(os.environ.get("OPENAI_API_KEY")),
                "ffmpeg_detected": bool(shutil.which("ffmpeg")),
                "audition_is_selector_only": True,
                "model": TTS_MODEL,
            },
        )

    integrity = __import__("common").read_json(run_dir / "content_integrity_report.json", {})
    if integrity.get("status") != "PASS":
        return finish(
            args,
            "tts",
            started,
            status="BLOCKED",
            ready_for_next_stage=False,
            blocker_category="content",
            blockers=["content_integrity_report.json must pass before TTS."],
            retryable=True,
            artifacts={"content_integrity_report": rel(run_dir / "content_integrity_report.json")},
        )

    public_book = load_public_book(args.slug)
    if sarvam_requested(args):
        manuscript_path = write_clean_manuscript_if_missing(args)
        manuscript = manuscript_path.read_text(encoding="utf-8")
        preflight = sarvam_full_pilot_preflight(args, manuscript)
        if not preflight["passes"]:
            cost_decision = write_cost_decision(
                run_dir,
                {
                    "slug": args.slug,
                    "stage": "tts",
                    "blocker": "SARVAM_FULL_PILOT_APPROVAL_OR_EVIDENCE_REQUIRED",
                    "options": ["generate_guarded_sarvam_full_pilot"],
                    "selected_option": "block_before_paid_generation",
                    "reason": "Guarded Sarvam full-pilot generation requires explicit budget/approval and matching representative evidence.",
                    "estimated_cost_usd": preflight["tts_estimated_cost"],
                    "quality_impact": "no audio generated",
                    "artifacts_reused": [],
                    "artifacts_regenerated": [],
                    "paid_api_calls": False,
                    "budget_status": "blocked",
                    "risk": "book remains reader-only/audio-hidden until gates pass",
                },
            )
            return finish(
                args,
                "tts",
                started,
                status="BLOCKED",
                ready_for_next_stage=False,
                blocker_category="tts_paid_approval_required",
                blockers=preflight["blockers"],
                retryable=True,
                artifacts={"clean_manuscript": rel(manuscript_path), "cost_optimization_decision": cost_decision},
                metrics={
                    **preflight,
                    "provider": "sarvam",
                    "model": SARVAM_FULL_PILOT_MODEL,
                    "voice": SARVAM_FULL_PILOT_VOICE,
                    "style": SARVAM_FULL_PILOT_STYLE,
                    "local_audio_reused": False,
                    "stale_audio_reused": False,
                    "fallback_tts_used": False,
                },
            )
        try:
            sarvam_result = generate_sarvam_full_pilot(args, run_dir, manuscript_path, manuscript, preflight)
        except Exception as exc:  # noqa: BLE001
            return finish(
                args,
                "tts",
                started,
                status="BLOCKED",
                ready_for_next_stage=False,
                blocker_category="tts",
                blockers=[f"Sarvam full-pilot generation failed: {exc}"],
                retryable=True,
                artifacts={"clean_manuscript": rel(manuscript_path)},
                metrics={
                    "provider": "sarvam",
                    "model": SARVAM_FULL_PILOT_MODEL,
                    "voice": SARVAM_FULL_PILOT_VOICE,
                    "style": SARVAM_FULL_PILOT_STYLE,
                    "tts_estimated_cost": preflight["tts_estimated_cost"],
                    "tts_budget_limit": preflight["tts_budget_limit"],
                    "local_audio_reused": False,
                    "stale_audio_reused": False,
                    "fallback_tts_used": False,
                },
            )
        report = sarvam_result["report"]
        return finish(
            args,
            "tts",
            started,
            status="PASS",
            fallback_tts_used=False,
            final_audio_path=report["final_audio_path"],
            ready_for_next_stage=True,
            blocker_category="none",
            blockers=[],
            retryable=False,
            artifacts={
                "final_audio_path": report["final_audio_path"],
                "chunk_manifest": rel(sarvam_result["manifest_path"]),
                "sarvam_full_pilot_tts_report": rel(sarvam_result["report_path"]),
                "cost_optimization_decision": sarvam_result["cost_decision"],
            },
            metrics={
                "provider": "sarvam",
                "model": SARVAM_FULL_PILOT_MODEL,
                "voice": SARVAM_FULL_PILOT_VOICE,
                "profile": SARVAM_FULL_PILOT_STYLE,
                "fallback_tts_used": False,
                "local_audio_reused": False,
                "stale_audio_reused": False,
                "audio_regenerated": True,
                "tts_estimated_cost": preflight["tts_estimated_cost"],
                "tts_budget_limit": preflight["tts_budget_limit"],
                "word_count": report.get("word_count"),
                "duration_seconds": report.get("generated_duration_seconds"),
                "group_count": report.get("group_count"),
                "cache_hits": report.get("cache_hits"),
                "cache_misses": report.get("cache_misses"),
                "representative_score": (preflight.get("representative_evidence") or {}).get("score"),
                "representative_confidence": (preflight.get("representative_evidence") or {}).get("confidence"),
            },
            updated_fields={
                "final_audio_path": report["final_audio_path"],
                "fallback_tts_used": False,
                "local_audio_reused": False,
                "stale_audio_reused": False,
                "tts_provider": "sarvam",
                "tts_model": SARVAM_FULL_PILOT_MODEL,
                "tts_voice": SARVAM_FULL_PILOT_VOICE,
                "tts_style": SARVAM_FULL_PILOT_STYLE,
            },
        )

    prior_rejection = prior_asr_rejects_reused_audio(run_dir)
    if prior_rejection.get("reject"):
        provenance_report = {
            "slug": args.slug,
            "status": "BLOCKED_REUSE_REJECTED",
            "existing_audio_url": public_audio_url(public_book),
            "local_audio_candidates": local_audio_candidates(args, run_dir),
            **prior_rejection,
        }
        write_json(run_dir / f"{args.slug.replace('-', '_')}_audio_provenance_report.json", provenance_report)
        write_json(run_dir / "audio_provenance_report.json", provenance_report)
        reused = {
            "status": "BLOCKED",
            "blocker_category": "audio_source_mismatch",
            "blockers": prior_rejection.get("blockers") or [prior_rejection["reason"]],
            "metrics": {
                "existing_audio_url": public_audio_url(public_book),
                "audio_regeneration_required": True,
                "force_regenerate_openai_tts": True,
                "previous_reuse_source": prior_rejection.get("reuse_source"),
                "previous_asr_score": prior_rejection.get("asr_score"),
                "previous_first_words_match": prior_rejection.get("first_words_match"),
                "previous_last_words_match": prior_rejection.get("last_words_match"),
                "audio_provenance_report": rel(run_dir / "audio_provenance_report.json"),
            },
        }
    else:
        reused = existing_audio_reuse(args, public_book)
    if reused and reused["status"] == "PASS":
        result_path = run_dir / "tts_chunk_manifest.json"
        write_json(result_path, {"chunks": [], "reuse": reused, "model": public_book.get("audiobook_provider", ""), "voice": public_book.get("audiobook_voice", "")})
        cost_decision = write_cost_decision(
            run_dir,
            {
                "slug": args.slug,
                "stage": "tts",
                "blocker": "",
                "options": ["reuse_existing_resolving_url", "reuse_local_audio", "regenerate_openai_tts"],
                "selected_option": "reuse_existing_resolving_url",
                "reason": "Existing production audio URL resolves and local validation passed.",
                "estimated_cost_usd": 0,
                "estimated_time_seconds": 0,
                "quality_impact": "no generation; downstream ASR/sync still validates quality",
                "artifacts_reused": [reused["final_audio_path"]],
                "artifacts_regenerated": [],
                "cache_hits": 1,
                "cache_misses": 0,
                "paid_api_calls": False,
                "budget_status": "not_required",
                "risk": "stale sidecars may still require rebuild",
            },
        )
        return finish(
            args,
            "tts",
            started,
            status="PASS",
            fallback_tts_used=False,
            final_audio_path=reused["final_audio_path"],
            ready_for_next_stage=True,
            blocker_category="none",
            blockers=[],
            retryable=False,
            artifacts={**reused, "chunk_manifest": rel(result_path), "cost_optimization_decision": cost_decision},
            metrics={"fallback_tts_used": False, "word_count": len(word_tokens(write_clean_manuscript_if_missing(args).read_text(encoding="utf-8")))},
            updated_fields={"final_audio_path": reused["final_audio_path"], "fallback_tts_used": False},
        )

    if reused and reused["status"] == "BLOCKED":
        force_regenerate = bool((reused.get("metrics") or {}).get("force_regenerate_openai_tts"))
        local = None if force_regenerate else local_audio_reuse(args, public_book)
        if local:
            result_path = run_dir / "tts_chunk_manifest.json"
            write_json(result_path, {"chunks": [], "reuse": local, "model": "local_audio_reuse", "voice": "", "stale_remote": reused})
            cost_decision = write_cost_decision(
                run_dir,
                {
                    "slug": args.slug,
                    "stage": "tts",
                    "blocker": "AUDIO_URL_STALE_OR_MISSING",
                    "options": ["reuse_existing_resolving_url", "reuse_valid_local_audio", "regenerate_openai_tts"],
                    "selected_option": "reuse_valid_local_audio",
                    "reason": "Remote audio URL was stale/missing, but a valid local non-fallback artifact exists.",
                    "estimated_cost_usd": 0,
                    "estimated_time_seconds": 0,
                    "quality_impact": "avoids regeneration; ASR/sync and QA remain mandatory",
                    "artifacts_reused": [local["final_audio_path"]],
                    "artifacts_regenerated": [],
                    "cache_hits": 1,
                    "cache_misses": 0,
                    "paid_api_calls": False,
                    "budget_status": "not_required",
                    "risk": "local audio may still fail ASR/sync/audio QA",
                },
            )
            return finish(
                args,
                "tts",
                started,
                status="PASS",
                fallback_tts_used=False,
                final_audio_path=local["final_audio_path"],
                ready_for_next_stage=True,
                blocker_category="none",
                blockers=[],
                retryable=False,
                artifacts={**local, "chunk_manifest": rel(result_path), "stale_remote_audio": reused, "cost_optimization_decision": cost_decision},
                metrics={
                    "fallback_tts_used": False,
                    "local_audio_reused": True,
                    "audio_url_404": bool((reused.get("metrics") or {}).get("audio_url_404")),
                    "sidecars_need_rebuild": bool(local.get("sidecars_need_rebuild")),
                    "word_count": len(word_tokens(write_clean_manuscript_if_missing(args).read_text(encoding="utf-8"))),
                },
                updated_fields={"final_audio_path": local["final_audio_path"], "fallback_tts_used": False, "local_audio_reused": True},
            )
        if force_regenerate or (reused.get("metrics") or {}).get("audio_url_404"):
            # Stale remote URL is recoverable, but only through explicit paid regeneration
            # when no valid local artifact exists.
            manuscript_path = write_clean_manuscript_if_missing(args)
            manuscript = manuscript_path.read_text(encoding="utf-8")
            preflight = paid_tts_preflight(manuscript)
            if not preflight["passes"]:
                blocker_name = "TTS_PAID_APPROVAL_REQUIRED"
                if force_regenerate:
                    blocker_name = "AUDIO_PROVENANCE_REGENERATION_REQUIRES_PAID_TTS_APPROVAL"
                return finish(
                    args,
                    "tts",
                    started,
                    status="BLOCKED",
                    ready_for_next_stage=False,
                    blocker_category="tts_paid_approval_required",
                    blockers=[*reused["blockers"], *preflight["blockers"]],
                    retryable=True,
                    artifacts={"clean_manuscript": rel(manuscript_path), "cost_optimization_decision": write_cost_decision(run_dir, {"slug": args.slug, "stage": "tts", "blocker": blocker_name, "options": ["regenerate_openai_tts"], "selected_option": "block_before_paid_generation", "reason": "Paid TTS approval or budget gate is missing.", "estimated_cost_usd": preflight["tts_estimated_cost"], "quality_impact": "no audio generated", "artifacts_reused": [], "artifacts_regenerated": [], "paid_api_calls": False, "budget_status": "blocked", "risk": "book remains blocked until approval is supplied"})},
                    metrics={
                        **(reused.get("metrics") or {}),
                        **preflight,
                        "local_audio_reused": False,
                        "audio_regeneration_required": True,
                    },
                )
            # Fall through to paid OpenAI generation with the manuscript already prepared.
        else:
            return finish(
                args,
                "tts",
                started,
                status="BLOCKED",
                ready_for_next_stage=False,
                blocker_category=reused.get("blocker_category") or "tts",
                blockers=reused["blockers"],
                retryable=True,
                metrics=reused.get("metrics", {}),
            )

    local_without_remote = local_audio_reuse(args, public_book) if not reused else None
    if local_without_remote:
        result_path = run_dir / "tts_chunk_manifest.json"
        write_json(result_path, {"chunks": [], "reuse": local_without_remote, "model": "local_audio_reuse", "voice": ""})
        cost_decision = write_cost_decision(
            run_dir,
            {
                "slug": args.slug,
                "stage": "tts",
                "blocker": "MISSING_REMOTE_AUDIO_URL",
                "options": ["reuse_valid_local_audio", "regenerate_openai_tts"],
                "selected_option": "reuse_valid_local_audio",
                "reason": "No usable remote audio URL is present, but a valid local non-fallback artifact exists.",
                "estimated_cost_usd": 0,
                "estimated_time_seconds": 0,
                "quality_impact": "avoids regeneration; downstream ASR/sync and QA remain mandatory",
                "artifacts_reused": [local_without_remote["final_audio_path"]],
                "artifacts_regenerated": [],
                "cache_hits": 1,
                "cache_misses": 0,
                "paid_api_calls": False,
                "budget_status": "not_required",
                "risk": "local audio may still fail ASR/sync/audio QA",
            },
        )
        return finish(
            args,
            "tts",
            started,
            status="PASS",
            fallback_tts_used=False,
            final_audio_path=local_without_remote["final_audio_path"],
            ready_for_next_stage=True,
            blocker_category="none",
            blockers=[],
            retryable=False,
            artifacts={**local_without_remote, "chunk_manifest": rel(result_path), "cost_optimization_decision": cost_decision},
            metrics={"fallback_tts_used": False, "local_audio_reused": True, "sidecars_need_rebuild": bool(local_without_remote.get("sidecars_need_rebuild"))},
            updated_fields={"final_audio_path": local_without_remote["final_audio_path"], "fallback_tts_used": False, "local_audio_reused": True},
        )

    manuscript_path = write_clean_manuscript_if_missing(args)
    manuscript = manuscript_path.read_text(encoding="utf-8")
    preflight = paid_tts_preflight(manuscript)
    if not preflight["passes"]:
        return finish(
            args,
            "tts",
            started,
            status="BLOCKED",
            ready_for_next_stage=False,
            blocker_category="tts_paid_approval_required",
            blockers=preflight["blockers"],
            retryable=True,
            artifacts={"clean_manuscript": rel(manuscript_path), "cost_optimization_decision": write_cost_decision(run_dir, {"slug": args.slug, "stage": "tts", "blocker": "TTS_PAID_APPROVAL_REQUIRED", "options": ["regenerate_openai_tts"], "selected_option": "block_before_paid_generation", "reason": "Paid TTS approval or budget gate is missing.", "estimated_cost_usd": preflight["tts_estimated_cost"], "quality_impact": "no audio generated", "artifacts_reused": [], "artifacts_regenerated": [], "paid_api_calls": False, "budget_status": "blocked", "risk": "book remains blocked until approval is supplied"})},
            metrics={**preflight, "local_audio_reused": False, "audio_regeneration_required": True},
        )

    if not os.environ.get("OPENAI_API_KEY"):
        return finish(
            args,
            "tts",
            started,
            status="BLOCKED",
            blocker_category="tts_paid_approval_required",
            blockers=["OPENAI_API_KEY is required for OpenAI TTS."],
            retryable=True,
            metrics=preflight,
        )
    if not shutil.which("ffmpeg"):
        return finish(args, "tts", started, status="BLOCKED", blocker_category="tts", blockers=["ffmpeg is required for chunk concatenation."], retryable=True)

    if len(manuscript) > DEFAULT_MAX_CHARS and os.environ.get("EARNALISM_FACTORY_ALLOW_LONG_TTS", "").lower() not in {"1", "true", "yes"}:
        return finish(
            args,
            "tts",
            started,
            status="BLOCKED",
            ready_for_next_stage=False,
            blocker_category="tts",
            blockers=[f"Manuscript has {len(manuscript)} characters; set EARNALISM_FACTORY_ALLOW_LONG_TTS=true to allow paid long-form generation."],
            retryable=True,
            artifacts={"clean_manuscript": rel(manuscript_path)},
            metrics={**preflight, "max_chars_without_explicit_long_tts": DEFAULT_MAX_CHARS, "character_count": len(manuscript)},
        )

    try:
        from openai import OpenAI

        client = OpenAI()
    except Exception as exc:  # noqa: BLE001
        return finish(args, "tts", started, status="BLOCKED", blocker_category="tts", blockers=[f"OpenAI SDK unavailable: {exc}"], retryable=True)

    audition = select_voice(args, manuscript, client)
    audition_path = run_dir / "voice_audition_results.json"
    write_json(audition_path, audition)
    if audition["status"] != "PASS":
        return finish(
            args,
            "tts",
            started,
            status="BLOCKED",
            ready_for_next_stage=False,
            blocker_category="tts",
            blockers=audition["blockers"],
            retryable=True,
            artifacts={"voice_audition_results": rel(audition_path)},
        )

    selected = audition["selected"]
    instructions = profile_instructions(args.language, selected["profile"])
    instruction_hash = sha256_text(instructions)
    source_hash = sha256_text(manuscript)
    chunks = chunk_text(manuscript, max_chars=OPENAI_MAX_CHARS_PER_CHUNK)
    chunk_paths: list[Path] = []
    manifest_chunks = []
    for chunk in chunks:
        cache_key = sha256_text(json.dumps({"source_hash": source_hash, "voice": selected["voice"], "model": TTS_MODEL, "instruction_hash": instruction_hash, "index": chunk["index"], "text_hash": chunk["text_hash"]}, sort_keys=True))
        cached = CACHE_DIR / args.language / selected["voice"] / f"{cache_key}.mp3"
        target = run_dir / "tts_chunks" / f"chunk_{chunk['index']:04d}_{cache_key[:12]}.mp3"
        if cached.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cached, target)
            cache_status = "HIT"
        else:
            speech_create(client, voice=selected["voice"], instructions=instructions, text=chunk["text"], out_path=target)
            cached.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, cached)
            cache_status = "MISS_GENERATED"
        chunk_paths.append(target)
        manifest_chunks.append(
            {
                **chunk,
                "path": rel(target),
                "sha256": sha256_file(target),
                "duration_seconds": ffprobe_duration(target),
                "cache_status": cache_status,
            }
        )
    final_audio = run_dir / f"{args.slug}_openai_tts_final.mp3"
    concat = concat_chunks(chunk_paths, final_audio)
    if not concat["ok"] or not final_audio.exists() or final_audio.stat().st_size == 0:
        return finish(
            args,
            "tts",
            started,
            status="BLOCKED",
            ready_for_next_stage=False,
            blocker_category="tts",
            blockers=["Final audio concatenation failed."],
            retryable=True,
            artifacts={"voice_audition_results": rel(audition_path)},
            metrics={"concat": concat},
        )
    manifest = {
        "slug": args.slug,
        "source_hash": source_hash,
        "model": TTS_MODEL,
        "voice": selected["voice"],
        "profile": selected["profile"],
        "instruction_hash": instruction_hash,
        "instructions_non_secret": instructions,
        "fallback_tts_used": False,
        "chunks": manifest_chunks,
        "final_audio_path": rel(final_audio),
        "final_audio_hash": sha256_file(final_audio),
        "duration_seconds": ffprobe_duration(final_audio),
        "word_count": len(word_tokens(manuscript)),
        "audition_results_path": rel(audition_path),
    }
    manifest_path = run_dir / "tts_chunk_manifest.json"
    write_json(manifest_path, manifest)
    cost_decision = write_cost_decision(
        run_dir,
        {
            "slug": args.slug,
            "stage": "tts",
            "blocker": "NO_VALID_REUSABLE_AUDIO",
            "options": ["reuse_existing_resolving_url", "reuse_valid_local_audio", "regenerate_openai_tts"],
            "selected_option": "regenerate_openai_tts",
            "reason": "No valid release-safe existing or local audio artifact was available.",
            "estimated_cost_usd": preflight["tts_estimated_cost"],
            "estimated_time_seconds": None,
            "quality_impact": "new OpenAI TTS candidate; ASR/sync and QA remain mandatory",
            "artifacts_reused": [],
            "artifacts_regenerated": [rel(final_audio)],
            "cache_hits": sum(1 for item in manifest_chunks if item.get("cache_status") == "HIT"),
            "cache_misses": sum(1 for item in manifest_chunks if item.get("cache_status") != "HIT"),
            "paid_api_calls": True,
            "budget_status": "approved_within_budget",
            "risk": "generated audio may still fail ASR/sync/audio QA",
        },
    )
    return finish(
        args,
        "tts",
        started,
        status="PASS",
        fallback_tts_used=False,
        final_audio_path=rel(final_audio),
        ready_for_next_stage=True,
        blocker_category="none",
        blockers=[],
        retryable=False,
        artifacts={
            "final_audio_path": rel(final_audio),
            "chunk_manifest": rel(manifest_path),
            "voice_audition_results": rel(audition_path),
            "cost_optimization_decision": cost_decision,
        },
        metrics={
            "model": TTS_MODEL,
            "voice": selected["voice"],
            "profile": selected["profile"],
            "instruction_hash": instruction_hash,
            "fallback_tts_used": False,
            "local_audio_reused": False,
            "audio_regenerated": True,
            "tts_estimated_cost": preflight["tts_estimated_cost"],
            "tts_budget_limit": preflight["tts_budget_limit"],
            "word_count": manifest["word_count"],
            "duration_seconds": manifest["duration_seconds"],
            "chunk_count": len(chunks),
            "max_chars_per_chunk": OPENAI_MAX_CHARS_PER_CHUNK,
        },
        updated_fields={"final_audio_path": rel(final_audio), "fallback_tts_used": False, "tts_model": TTS_MODEL, "tts_voice": selected["voice"]},
    )


if __name__ == "__main__":
    raise SystemExit(main())
