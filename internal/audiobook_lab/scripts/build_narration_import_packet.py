#!/usr/bin/env python3
"""Build deterministic, source-bound human narration or licensed-audio packets."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_ROOT = ROOT / "internal/audiobook_lab/sprint1_publication/human_narration_packets"
SCRIPT_PATH = "internal/audiobook_lab/scripts/build_narration_import_packet.py"
SANITIZER_VERSION = "narration-import-sanitizer-v1"
FATAL_FLAGS = (
    "robotic_texture_detected",
    "mechanical_cadence_detected",
    "list_reading_rhythm_detected",
    "choppy_joins_detected",
    "fallback_tts_detected",
    "placeholder_audio_detected",
)
BOILERPLATE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"project\s+gutenberg",
        r"gutenberg-tm",
        r"wikisource|উইকিসংকলন",
        r"internet\s+archive",
        r"transcriber(?:'s)?\s+note",
        r"source\s+(?:repository|url)",
        r"creative\s+commons",
        r"license\s*:",
    )
)
EDITION_MARKER = re.compile(r"^[০-৯0-9]{3,4}\s*[?？.]?$")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(encoded)


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected a JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def portable_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def validate_slug(slug: str) -> None:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise RuntimeError("slug must contain only lowercase letters, digits, and hyphens")


def normalize_language(value: str) -> dict[str, str] | None:
    normalized = value.strip().lower().replace("_", "-")
    if normalized in {"ben", "bn", "bn-in", "bengali", "বাংলা"}:
        return {"code": "ben", "name": "Bengali"}
    if normalized in {"en", "eng", "en-gb", "en-us", "english"}:
        return {"code": "en", "name": "English"}
    return None


def detect_language(public_book: dict[str, Any], chapter_texts: list[str]) -> dict[str, str]:
    candidates = [public_book.get("language"), public_book.get("language_code")]
    candidates.extend(
        chapter.get("language_hint")
        for chapter in public_book.get("chapters", [])
        if isinstance(chapter, dict)
    )
    for candidate in candidates:
        if candidate and (language := normalize_language(str(candidate))):
            return language

    text = "".join(chapter_texts)
    bengali = sum("\u0980" <= character <= "\u09ff" for character in text)
    letters = sum(character.isalpha() for character in text)
    if letters and bengali / letters >= 0.35:
        return {"code": "ben", "name": "Bengali"}
    return {"code": "en", "name": "English"}


def _paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]


def _is_boilerplate(paragraph: str) -> bool:
    return any(pattern.search(paragraph) for pattern in BOILERPLATE_PATTERNS)


def _removed_fragment(location: str, reason: str, paragraphs: list[str]) -> dict[str, Any]:
    text = "\n\n".join(paragraphs)
    return {
        "characters": len(text),
        "location": location,
        "reason": reason,
        "sha256": sha256_text(text),
    }


def sanitize_chapter(content: str, *, title: str) -> tuple[str, list[dict[str, Any]]]:
    normalized = unicodedata.normalize("NFC", content.replace("\r\n", "\n").replace("\r", "\n"))
    normalized = normalized.replace("\ufeff", "").replace("\u200b", "").replace("\u00ad", "")
    paragraphs = _paragraphs(normalized)
    removed: list[dict[str, Any]] = []

    exact_title = unicodedata.normalize("NFC", title).strip().casefold()
    title_index = next(
        (
            index
            for index, paragraph in enumerate(paragraphs[:8])
            if paragraph.strip().casefold() == exact_title
        ),
        None,
    )
    if title_index is not None:
        leading = paragraphs[: title_index + 1]
        removed.append(_removed_fragment("leading", "frontmatter_through_exact_title", leading))
        paragraphs = paragraphs[title_index + 1 :]

    while paragraphs and _is_boilerplate(paragraphs[0]):
        removed.append(_removed_fragment("leading", "source_or_license_boilerplate", [paragraphs.pop(0)]))
    while paragraphs and _is_boilerplate(paragraphs[-1]):
        removed.append(_removed_fragment("trailing", "source_or_license_boilerplate", [paragraphs.pop()]))
    while paragraphs and EDITION_MARKER.fullmatch(paragraphs[-1]):
        removed.append(_removed_fragment("trailing", "standalone_edition_year", [paragraphs.pop()]))

    if not paragraphs:
        raise RuntimeError("sanitation removed the entire chapter")
    remaining_boilerplate = [paragraph for paragraph in paragraphs if _is_boilerplate(paragraph)]
    if remaining_boilerplate:
        raise RuntimeError("source or license boilerplate remains inside the sanitized chapter")
    return "\n\n".join(paragraphs).strip(), removed


def _contains_slug(payload: Any, slug: str) -> bool:
    if payload == slug:
        return True
    if isinstance(payload, dict):
        return any(_contains_slug(value, slug) for value in payload.values())
    if isinstance(payload, list):
        return any(_contains_slug(value, slug) for value in payload)
    return False


def _fatal_flags(payload: dict[str, Any]) -> list[str]:
    flags: set[str] = set()
    for key in ("fatal_flags", "red_flags"):
        value = payload.get(key)
        if isinstance(value, list):
            flags.update(str(item) for item in value if item)
        elif isinstance(value, dict):
            flags.update(str(name) for name, active in value.items() if active)
    for passage in payload.get("passage_scores", []) or []:
        if isinstance(passage, dict):
            flags.update(_fatal_flags(passage))
    owner_gate = payload.get("owner_listening_gate")
    if isinstance(owner_gate, dict):
        flags.update(_fatal_flags(owner_gate))
    return sorted(flags)


def _scores(payload: dict[str, Any]) -> list[float]:
    raw_scores = payload.get("scores")
    if isinstance(raw_scores, list):
        return [float(score) for score in raw_scores if isinstance(score, (int, float))]
    scores = []
    for passage in payload.get("passage_scores", []) or []:
        if isinstance(passage, dict) and isinstance(passage.get("overall_listening_score"), (int, float)):
            scores.append(float(passage["overall_listening_score"]))
    return scores


def _referenced_attempt_details(block: dict[str, Any], asset_root: Path) -> dict[str, Any]:
    evidence = block.get("evidence")
    if not isinstance(evidence, str) or not evidence:
        return {}
    evidence_path = asset_root / evidence
    if not evidence_path.exists():
        return {}
    try:
        payload = load_json(evidence_path)
    except (OSError, json.JSONDecodeError, RuntimeError):
        return {}
    details = {
        key: payload[key]
        for key in ("attempt_fingerprint", "sanitized_sha256")
        if payload.get(key) is not None
    }
    blocker_text = "\n".join(str(item) for item in payload.get("blockers", []) if item)
    owner_minimums = [float(value) for value in re.findall(r"owner minimum\s+(\d+(?:\.\d+)?)", blocker_text, re.I)]
    if owner_minimums:
        details["owner_minimum_score"] = max(owner_minimums)
    return details


def _attempt(
    *,
    scope: str,
    payload: dict[str, Any],
    evidence: str,
    asset_root: Path,
    defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    defaults = defaults or {}
    details = _referenced_attempt_details(payload, asset_root)
    scores = _scores(payload)
    status = str(payload.get("status") or payload.get("pass_fail_decision") or "UNKNOWN")
    result: dict[str, Any] = {
        "evidence": evidence,
        "failed": status.upper() not in {"PASS", "PASSED", "APPROVED", "BENGALI_AUDIO_PATH_FOUND"},
        "fatal_flags": _fatal_flags(payload),
        "scope": scope,
        "status": status,
    }
    values = {
        "attempt_fingerprint": payload.get("attempt_fingerprint") or details.get("attempt_fingerprint"),
        "confidence": payload.get("confidence") or payload.get("minimum_confidence"),
        "model": payload.get("model") or defaults.get("model"),
        "owner_minimum_score": details.get("owner_minimum_score"),
        "provider": payload.get("provider") or defaults.get("provider"),
        "style_profile": payload.get("best_style_profile") or payload.get("style_profile") or defaults.get("style_profile"),
        "voice": payload.get("voice") or defaults.get("voice"),
        "weak_passage": payload.get("weak_passage"),
    }
    result.update({key: value for key, value in values.items() if value not in (None, "", [])})
    if scores:
        result["scores"] = scores
        result["minimum_observed_score"] = min(scores)
    representative_score = payload.get("representative_score")
    if isinstance(representative_score, (int, float)):
        result["representative_score"] = float(representative_score)
    return result


def discover_provider_evidence(slug: str, asset_root: Path) -> dict[str, Any]:
    title_runs = asset_root / "internal/audiobook_lab/sprint1_publication/title_runs"
    release_path = title_runs / f"{slug}_release_gate_evidence.json"
    release: dict[str, Any] = load_json(release_path) if release_path.exists() else {}
    attempts: list[dict[str, Any]] = []

    stage2d = release.get("stage2d_replacement_auditions")
    if isinstance(stage2d, dict):
        defaults = {key: stage2d.get(key) for key in ("provider", "model", "voice", "style_profile")}
        for key in ("baseline", "single_prosody_retry"):
            block = stage2d.get(key)
            if isinstance(block, dict):
                attempts.append(
                    _attempt(
                        scope=f"representative_audition_{key}",
                        payload=block,
                        evidence=str(block.get("evidence") or portable_path(release_path, asset_root)),
                        asset_root=asset_root,
                        defaults=defaults,
                    )
                )
    stage2e = release.get("stage2e_studio_b_final_audition")
    if isinstance(stage2e, dict):
        attempts.append(
            _attempt(
                scope="representative_audition_final",
                payload=stage2e,
                evidence=str(stage2e.get("evidence") or portable_path(release_path, asset_root)),
                asset_root=asset_root,
            )
        )

    if title_runs.exists():
        for path in sorted(title_runs.rglob("bengali_representative_audition_report.json")):
            try:
                payload = load_json(path)
            except (OSError, json.JSONDecodeError, RuntimeError):
                continue
            if not _contains_slug(payload, slug):
                continue
            attempts.append(
                _attempt(
                    scope="representative_audition",
                    payload=payload,
                    evidence=portable_path(path, asset_root),
                    asset_root=asset_root,
                )
            )

        for path in sorted(title_runs.rglob("*full_qa.json")):
            try:
                payload = load_json(path)
            except (OSError, json.JSONDecodeError, RuntimeError):
                continue
            if payload.get("slug") != slug:
                continue
            owner_gate = payload.get("owner_listening_gate")
            attempt_payload = dict(payload)
            if isinstance(owner_gate, dict):
                attempt_payload["scores"] = owner_gate.get("scores") or []
                attempt_payload["confidence"] = owner_gate.get("minimum_confidence")
                attempt_payload["fatal_flags"] = owner_gate.get("fatal_flags") or []
            attempts.append(
                _attempt(
                    scope="full_book_qa",
                    payload=attempt_payload,
                    evidence=portable_path(path, asset_root),
                    asset_root=asset_root,
                )
            )

    unique: dict[str, dict[str, Any]] = {}
    for attempt in attempts:
        unique[canonical_sha256(attempt)] = attempt
    attempts = sorted(
        unique.values(),
        key=lambda item: (str(item.get("evidence")), str(item.get("scope")), str(item.get("voice", ""))),
    )
    failed = [attempt for attempt in attempts if attempt["failed"]]
    passed_but_not_release = [attempt for attempt in attempts if not attempt["failed"]]
    evidence_paths = sorted(
        {
            str(attempt["evidence"])
            for attempt in attempts
        }
        | ({portable_path(release_path, asset_root)} if release else set())
    )
    return {
        "classification": release.get("classification") or release.get("release_gate_state") or "NO_RELEASE_CLASSIFICATION_FOUND",
        "exact_blocker": release.get("exact_blocker") or "",
        "evidence_paths": evidence_paths,
        "failed_attempts": failed,
        "non_release_passes": passed_but_not_release,
        "provider_attempts": attempts,
        "quality_summary": release.get("quality_score") or "",
        "release_evidence_found": bool(release),
    }


def language_guidance(language: dict[str, str], *, title: str, author: str, manuscript: str) -> dict[str, Any]:
    if language["code"] == "ben":
        return {
            "pronunciation_checkpoints": [
                title,
                author,
                "Mark every uncertain proper noun, archaic সাধু form, Sanskrit-derived word, and regional form before recording.",
                "Preserve Bengali vowel length, conjunct consonants, and written spelling; do not Anglicize names.",
            ],
            "style_profile": "classical_bengali_literary_natural_measured",
            "style_notes": [
                "Use idiomatic Bengali phrasing with measured literary pacing and natural sentence-final cadence.",
                "Keep সাধু or archaic diction intact; do not modernize, paraphrase, translate, or flatten the register.",
                "Differentiate dialogue lightly without caricature; preserve satire, irony, and emotional restraint.",
                "Avoid list-reading rhythm, mechanical cadence, robotic texture, rushed punctuation, and choppy joins.",
            ],
        }

    counts: dict[str, int] = {}
    stopwords = {"The", "This", "That", "Then", "Here", "There", "When", "It", "She", "He", "They", "A", "An", "I"}
    for name in re.findall(r"\b[A-Z][A-Za-z'’-]{2,}\b", manuscript):
        if name not in stopwords:
            counts[name] = counts.get(name, 0) + 1
    recurring_names = sorted(name for name, count in counts.items() if count >= 2)[:12]
    checkpoints = [title, author]
    if recurring_names:
        checkpoints.append("Recurring names/terms: " + ", ".join(recurring_names))
    checkpoints.append("Confirm every proper noun and period-specific term before recording; preserve the written form.")
    return {
        "pronunciation_checkpoints": checkpoints,
        "style_profile": "english_literary_natural_dialogue",
        "style_notes": [
            "Use clear literary English with natural dialogue changes and deliberate punctuation pauses.",
            "Preserve period diction, irony, tension, and humor without melodrama or character caricature.",
            "Do not paraphrase names, quoted speech, spelling, or narrative transitions.",
            "Avoid list-reading rhythm, mechanical cadence, robotic texture, rushed transitions, and choppy joins.",
        ],
    }


def release_requirements(language: dict[str, str], evidence: dict[str, Any]) -> dict[str, Any]:
    listening_min = 9.2 if language["code"] == "ben" else 9.3
    owner_minimums = [
        float(attempt["owner_minimum_score"])
        for attempt in evidence["provider_attempts"]
        if isinstance(attempt.get("owner_minimum_score"), (int, float))
    ]
    if owner_minimums:
        listening_min = max(listening_min, max(owner_minimums))
    return {
        "asr_manuscript_score_min": 9.7,
        "blocker_list_must_be_empty": True,
        "confidence_score_min": 0.9,
        "fatal_flags_required_false": list(FATAL_FLAGS),
        "first_and_last_words_must_match": True,
        "listening_score_min": listening_min,
        "measured_sync_required": "paragraph_or_stanza" if language["code"] == "ben" else "paragraph_or_section",
        "no_missing_duplicated_or_reordered_content": True,
        "public_audio_must_remain_hidden_until_all_gates_pass": True,
        "sync_may_not_be_estimated": True,
    }


def validation_command(*, slug: str, candidate_kind: str, asset_root: Path, output_root: Path) -> str:
    output_arg = portable_path(output_root, asset_root)
    return (
        f"PYTHONDONTWRITEBYTECODE=1 python3 {SCRIPT_PATH} "
        f"--slug {slug} --candidate-kind {candidate_kind} --asset-root . "
        f"--output-root {output_arg} --received-audio /absolute/path/to/received_narration.wav"
    )


def _attempt_line(attempt: dict[str, Any]) -> str:
    identity = "/".join(
        str(attempt[key]) for key in ("provider", "model", "voice") if attempt.get(key)
    ) or "provider identity not recorded"
    score = attempt.get("representative_score")
    if score is None and attempt.get("scores"):
        score = min(attempt["scores"])
    score_text = f"; minimum/representative score `{score}`" if score is not None else ""
    flags = ", ".join(attempt.get("fatal_flags") or []) or "none recorded"
    return (
        f"- `{attempt['scope']}`: `{identity}` -> `{attempt['status']}`{score_text}; "
        f"fatal flags: `{flags}`; evidence: `{attempt['evidence']}`"
    )


def create_packet(
    *,
    slug: str,
    asset_root: Path,
    output_root: Path,
    candidate_kind: str = "human_narration",
) -> dict[str, Any]:
    validate_slug(slug)
    if candidate_kind not in {"human_narration", "licensed_audio_import"}:
        raise RuntimeError("candidate kind must be human_narration or licensed_audio_import")

    publication = asset_root / "data/controlled_publications" / slug
    public_book = load_json(publication / "public_book.json")
    source_evidence = load_json(publication / "source_evidence.json")
    if public_book.get("verification_status") != "approved" or public_book.get("qa_status") != "QA_PASSED":
        raise RuntimeError("controlled publication is not approved and QA-passed")
    source_hash = str(source_evidence.get("source_hash") or "")
    public_source_hash = str(public_book.get("source_hash") or "")
    if not source_evidence.get("rights_basis") or not source_hash:
        raise RuntimeError("source rights evidence is incomplete")
    if public_source_hash and public_source_hash != source_hash:
        raise RuntimeError("public book and rights evidence source hashes differ")

    chapter_paths = sorted((publication / "chapters").glob("chapter-*.json"))
    if not chapter_paths:
        raise RuntimeError("controlled publication has no chapters")
    title = str(public_book.get("title") or slug)
    raw_texts: list[str] = []
    sanitized_texts: list[str] = []
    chapters: list[dict[str, Any]] = []
    removed_fragments: list[dict[str, Any]] = []
    for chapter_path in chapter_paths:
        chapter = load_json(chapter_path)
        if chapter.get("processing_status") != "ready" or chapter.get("processing_warnings") != []:
            raise RuntimeError(f"chapter is not clean and ready: {chapter_path.name}")
        raw = str(chapter.get("content") or "").strip()
        if not raw:
            raise RuntimeError(f"chapter content is empty: {chapter_path.name}")
        raw_sha256 = sha256_text(raw)
        recorded_sha256 = str(chapter.get("sanitizedSha256") or "")
        if not recorded_sha256:
            raise RuntimeError(f"chapter sanitized hash is missing: {chapter_path.name}")
        if recorded_sha256 != raw_sha256:
            raise RuntimeError(f"chapter sanitized hash changed: {chapter_path.name}")
        sanitized, removed = sanitize_chapter(raw, title=title)
        sanitized_sha256 = sha256_text(sanitized)
        chapter_record = {
            "chapter": chapter_path.name,
            "chapter_title": str(chapter.get("title") or chapter_path.stem),
            "raw_characters": len(raw),
            "recorded_source_sha256": recorded_sha256,
            "sanitized_characters": len(sanitized),
            "sanitized_sha256": sanitized_sha256,
        }
        for fragment in removed:
            removed_fragments.append({"chapter": chapter_path.name, **fragment})
        chapters.append(chapter_record)
        raw_texts.append(raw)
        sanitized_texts.append(sanitized)

    raw_manuscript = "\n\n".join(raw_texts)
    manuscript = "\n\n".join(sanitized_texts) + "\n"
    manuscript_sha256 = sha256_text(manuscript.rstrip())
    language = detect_language(public_book, raw_texts)
    provider_evidence = discover_provider_evidence(slug, asset_root)
    guidance = language_guidance(
        language,
        title=title,
        author=str(public_book.get("author") or ""),
        manuscript=manuscript,
    )
    requirements = release_requirements(language, provider_evidence)
    command = validation_command(
        slug=slug,
        candidate_kind=candidate_kind,
        asset_root=asset_root,
        output_root=output_root,
    )
    source_binding: dict[str, Any] = {
        "chapters": chapters,
        "raw_manuscript_sha256": sha256_text(raw_manuscript),
        "sanitized_manuscript_sha256": manuscript_sha256,
        "source_hash": source_hash,
        "status": "VERIFIED_SOURCE_AND_CHAPTER_HASHES",
    }
    source_binding["binding_sha256"] = canonical_sha256(source_binding)
    metadata: dict[str, Any] = {
        "author": str(public_book.get("author") or ""),
        "candidate_kind": candidate_kind,
        "delivery": {
            "accepted_formats": ["wav_pcm_44.1_or_48_khz", "flac_44.1_or_48_khz", "mp3_128kbps_or_higher_44.1_or_48_khz"],
            "single_complete_file_required": True,
        },
        "exact_received_audio_validation_command": command,
        "language": language,
        "packet_type": "SOURCE_BOUND_NARRATION_OR_AUDIO_IMPORT",
        "prior_provider_evidence": provider_evidence,
        "pronunciation_checkpoints": guidance["pronunciation_checkpoints"],
        "release_requirements": requirements,
        "rights": {
            "provenance_hash": source_evidence.get("provenance_hash"),
            "rights_basis": source_evidence["rights_basis"],
        },
        "safety": {
            "audio_generated": False,
            "provider_calls_ran": False,
            "public_audio_status": "AUDIO_HIDDEN_PENDING_COMPLETE_RELEASE_GATES",
            "release_gate_mutated": False,
        },
        "sanitization": {
            "removed_fragments": removed_fragments,
            "sanitizer_version": SANITIZER_VERSION,
            "status": "PASS",
        },
        "schema_version": 2,
        "slug": slug,
        "source_binding": source_binding,
        "style_notes": guidance["style_notes"],
        "style_profile": guidance["style_profile"],
        "title": title,
    }
    metadata["packet_fingerprint_sha256"] = canonical_sha256(metadata)

    packet_dir = output_root / slug
    packet_dir.mkdir(parents=True, exist_ok=True)
    (packet_dir / "clean_manuscript.txt").write_text(manuscript, encoding="utf-8")
    write_json(packet_dir / "metadata.json", metadata)

    brief_lines = [
        f"# Narration / Import Brief: {title}",
        "",
        f"- Slug: `{slug}`",
        f"- Author: {metadata['author']}",
        f"- Language: `{language['name']} ({language['code']})`",
        f"- Candidate kind: `{candidate_kind}`",
        f"- Source hash: `{source_hash}`",
        f"- Sanitized manuscript SHA-256: `{manuscript_sha256}`",
        f"- Public audio state: `{metadata['safety']['public_audio_status']}`",
        "",
        "Use only `clean_manuscript.txt`. Preserve every word, paragraph, and chapter in order.",
        "Do not add spoken credits, source notices, page numbers, music, effects, or text absent from the manuscript.",
        "",
        "## Pronunciation Checklist",
        "",
        *[f"- [ ] {item}" for item in metadata["pronunciation_checkpoints"]],
        "",
        "## Style And Performance",
        "",
        *[f"- {item}" for item in metadata["style_notes"]],
        "",
        "## Chapter Boundaries",
        "",
        *[
            f"- `{chapter['chapter']}` / {chapter['chapter_title']}: "
            f"{chapter['sanitized_characters']} characters; `{chapter['sanitized_sha256']}`"
            for chapter in chapters
        ],
        "",
        "Pause naturally between chapters, but do not speak metadata-only chapter labels unless those words occur in the manuscript.",
        "",
        "## Exact Validation Command After Received Audio",
        "",
        f"`{command}`",
    ]
    (packet_dir / "narrator_brief.md").write_text("\n".join(brief_lines) + "\n", encoding="utf-8")

    failed_lines = [
        f"# Failed Provider Attempt Summary: {title}",
        "",
        f"- Release classification: `{provider_evidence['classification']}`",
        f"- Quality summary: `{provider_evidence['quality_summary'] or 'not recorded'}`",
        f"- Exact blocker: `{provider_evidence['exact_blocker'] or 'see attempt evidence'}`",
        f"- Failed structured attempts found: `{len(provider_evidence['failed_attempts'])}`",
        "",
    ]
    if provider_evidence["failed_attempts"]:
        failed_lines.extend(_attempt_line(attempt) for attempt in provider_evidence["failed_attempts"])
    else:
        failed_lines.append("- No structured failed provider attempt was found in the local title evidence.")
    if provider_evidence["non_release_passes"]:
        failed_lines.extend(
            [
                "",
                "## Representative Passes That Are Not Release Approval",
                "",
                *[_attempt_line(attempt) for attempt in provider_evidence["non_release_passes"]],
            ]
        )
    failed_lines.extend(
        [
            "",
            "Do not reuse failed audio or repeat an attempt fingerprint listed above.",
            "A representative pass alone is not permission to publish; the received full candidate must pass every release gate.",
        ]
    )
    (packet_dir / "failed_tts_evidence_summary.md").write_text(
        "\n".join(failed_lines) + "\n",
        encoding="utf-8",
    )

    provenance_item = (
        "Narrator identity, performance agreement, commercial audiobook rights, territories, term, and transfer permission are documented."
        if candidate_kind == "human_narration"
        else "License chain proves commercial digital-audiobook rights, territories, term, edit/host permissions, and performer/music clearances."
    )
    delivery_lines = [
        "# Delivery Checklist",
        "",
        "- [ ] Complete audio matches `clean_manuscript.txt` word-for-word and in order.",
        "- [ ] One non-empty playable WAV, FLAC, or high-bitrate MP3 is supplied at 44.1/48 kHz, mono or stereo.",
        "- [ ] No clipping, denoising artifacts, room-tone jumps, lossy re-encoding damage, music, effects, or unrelated speech.",
        "- [ ] Paragraph, dialogue, and chapter boundaries remain audible and natural.",
        "- [ ] The file name identifies the slug and version without claiming public release.",
        f"- [ ] {provenance_item}",
        "- [ ] Delivery manifest records file SHA-256, format, sample rate, channels, duration, and responsible contact.",
        "- [ ] Run the exact received-audio validation command from `narrator_brief.md`.",
    ]
    (packet_dir / "delivery_checklist.md").write_text("\n".join(delivery_lines) + "\n", encoding="utf-8")

    qa_lines = [
        "# QA And Release Checklist",
        "",
        "- [ ] Received-audio format, duration, and checksum preflight PASS.",
        "- [ ] Source/rights/provenance and performance or license chain PASS.",
        f"- [ ] ASR/manuscript score is `>= {requirements['asr_manuscript_score_min']}`.",
        "- [ ] First and last words match the source-bound sanitized manuscript.",
        "- [ ] No missing, duplicated, reordered, substituted, or unrelated content.",
        f"- [ ] Representative and full-book listening score is `>= {requirements['listening_score_min']}` with confidence `>= {requirements['confidence_score_min']}`.",
        "- [ ] No robotic texture, mechanical cadence, list-reading rhythm, choppy joins, fallback TTS, or placeholder audio.",
        f"- [ ] Measured `{requirements['measured_sync_required']}` sync PASS; `auto_estimated_sync=false`.",
        "- [ ] Upload and checksum validation PASS.",
        "- [ ] Metadata approval PASS and blocker list is empty.",
        "- [ ] Audiobook endpoint returns `200/206` and range requests work.",
        "- [ ] Browser/player gate PASS on supported desktop and mobile routes.",
        "- [ ] Owner release approval is recorded before Listen controls, AudioObject metadata, or public audio exposure.",
    ]
    (packet_dir / "qa_release_checklist.md").write_text("\n".join(qa_lines) + "\n", encoding="utf-8")

    return {
        "candidate_kind": candidate_kind,
        "exact_received_audio_validation_command": command,
        "packet_dir": str(packet_dir),
        "packet_fingerprint_sha256": metadata["packet_fingerprint_sha256"],
        "provider_calls_ran": False,
        "release_gate_mutated": False,
        "sanitized_manuscript_sha256": manuscript_sha256,
        "status": "NARRATION_IMPORT_PACKET_READY_AUDIO_HIDDEN",
    }


def validate_received_audio(*, audio_path: Path, packet_dir: Path) -> dict[str, Any]:
    if not audio_path.is_file() or audio_path.stat().st_size <= 0:
        raise RuntimeError("received audio is missing or empty")
    if audio_path.suffix.lower() not in {".wav", ".flac", ".mp3"}:
        raise RuntimeError("received audio must be WAV, FLAC, or MP3")
    metadata = load_json(packet_dir / "metadata.json")
    manuscript = (packet_dir / "clean_manuscript.txt").read_text(encoding="utf-8").rstrip()
    source_binding = metadata.get("source_binding", {})
    expected_manuscript_sha256 = source_binding.get("sanitized_manuscript_sha256")
    if sha256_text(manuscript) != expected_manuscript_sha256:
        raise RuntimeError("packet manuscript no longer matches its source binding")
    expected_binding_sha256 = source_binding.get("binding_sha256")
    binding_payload = {key: value for key, value in source_binding.items() if key != "binding_sha256"}
    if canonical_sha256(binding_payload) != expected_binding_sha256:
        raise RuntimeError("packet source-binding fingerprint mismatch")
    expected_packet_fingerprint = metadata.pop("packet_fingerprint_sha256", None)
    if canonical_sha256(metadata) != expected_packet_fingerprint:
        raise RuntimeError("packet metadata fingerprint mismatch")

    try:
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,size,bit_rate:stream=codec_name,sample_rate,channels,bit_rate",
                "-of",
                "json",
                str(audio_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError("ffprobe could not validate the received audio") from error
    details = json.loads(probe.stdout)
    streams = details.get("streams") or []
    if not streams:
        raise RuntimeError("received audio has no audio stream")
    stream = streams[0]
    format_details = details.get("format") or {}
    duration = float(format_details.get("duration") or 0)
    sample_rate = int(stream.get("sample_rate") or 0)
    channels = int(stream.get("channels") or 0)
    bit_rate = int(stream.get("bit_rate") or format_details.get("bit_rate") or 0)
    if duration <= 0 or sample_rate not in {44100, 48000} or channels not in {1, 2}:
        raise RuntimeError("received audio does not meet duration/sample-rate/channel requirements")
    if audio_path.suffix.lower() == ".mp3" and bit_rate < 128000:
        raise RuntimeError("received MP3 bitrate is below 128 kbps")

    result = {
        "audio": {
            "bytes": audio_path.stat().st_size,
            "channels": channels,
            "codec": stream.get("codec_name"),
            "duration_seconds": round(duration, 3),
            "file_name": audio_path.name,
            "sample_rate": sample_rate,
            "sha256": sha256_bytes(audio_path.read_bytes()),
        },
        "next_status": "FULL_ASR_LISTENING_SYNC_UPLOAD_METADATA_ENDPOINT_BROWSER_QA_REQUIRED",
        "packet_fingerprint_sha256": expected_packet_fingerprint,
        "provider_calls_ran": False,
        "public_audio_status": "AUDIO_HIDDEN_PENDING_COMPLETE_RELEASE_GATES",
        "release_gate_mutated": False,
        "schema_version": 1,
        "slug": metadata.get("slug"),
        "source_binding_sha256": metadata.get("source_binding", {}).get("binding_sha256"),
        "status": "RECEIVED_AUDIO_PREFLIGHT_PASS_FULL_RELEASE_QA_REQUIRED",
    }
    write_json(packet_dir / "received_audio_preflight.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True)
    parser.add_argument(
        "--candidate-kind",
        choices=("human_narration", "licensed_audio_import"),
        default="human_narration",
    )
    parser.add_argument("--asset-root", default=str(ROOT))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--received-audio", help="Locally preflight a received WAV, FLAC, or MP3")
    args = parser.parse_args()
    asset_root = Path(args.asset_root).expanduser().resolve()
    output_root = Path(args.output_root).expanduser()
    if not output_root.is_absolute():
        output_root = asset_root / output_root
    output_root = output_root.resolve()
    result = create_packet(
        slug=args.slug,
        asset_root=asset_root,
        output_root=output_root,
        candidate_kind=args.candidate_kind,
    )
    if args.received_audio:
        result["received_audio_preflight"] = validate_received_audio(
            audio_path=Path(args.received_audio).expanduser().resolve(),
            packet_dir=Path(result["packet_dir"]),
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
