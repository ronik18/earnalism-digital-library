#!/usr/bin/env python3
"""Run one private A Ghost Story full TTS candidate through the repo hook."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HOOK = ROOT / "internal/audiobook_lab/scripts/factory_hooks/tts_hook.py"
RESULT_PATH = (
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "a-ghost-story_stage2c_full_tts_runtime.json"
)
FULL_QA_RESULT_PATH = (
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "a-ghost-story_stage2c_full_qa_runtime.json"
)
HOLDER = "sprint1_publication_stage2c"
BEST_AUDITION_PATH = (
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "a-ghost-story_stage2c_middle_audition_runtime.json"
)
EXPECTED_SOURCE_SHA256 = "0f1e3de7855169bddac8ddca288aa3a63f8d6a742ce63c0b91aa947e5e2786d4"
EXPECTED_ENV = {
    "SPRINT1_TOTAL_AUDIO_BUDGET_USD": "175",
    "SPRINT1_MAX_USD_PER_TITLE": "30",
    "MAX_TTS_BUDGET_USD": "175",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
    "EARNALISM_APPROVE_PAID_OPENAI_TTS": "true",
    "EARNALISM_TTS_MAX_ESTIMATED_USD": "1",
    "EARNALISM_TTS_ESTIMATED_USD_PER_1K_CHARS": "0.015",
    "EARNALISM_FACTORY_TTS_VOICE": "verse",
    "EARNALISM_FACTORY_TTS_PROFILE": "mystery_suspense_narrator",
}


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def runtime_gate_errors() -> list[str]:
    errors = [
        f"{name} must equal {expected}"
        for name, expected in EXPECTED_ENV.items()
        if os.environ.get(name) != expected
    ]
    if not os.environ.get("OPENAI_API_KEY"):
        errors.append("OPENAI_API_KEY is required")
    return errors


def load_lock(raw: bytes) -> dict:
    payload = json.loads(raw)
    if payload.get("status") != "active":
        raise RuntimeError("paid_tts.lock must remain active")
    if payload.get("current_holder") != "none":
        raise RuntimeError("paid_tts.lock already has a holder")
    if payload.get("allowed_next_holders") != []:
        raise RuntimeError("paid_tts.lock allowed_next_holders must be empty")
    return payload


def acquired_lock_payload(lock: dict) -> dict:
    payload = dict(lock)
    payload.update(
        {
            "current_holder": HOLDER,
            "allowed_next_holders": [],
            "holder_started_at": iso_now(),
            "budget_cap_usd": 175,
            "approved_scope": (
                "A Ghost Story private full-book OpenAI TTS candidate only; verse/mystery_suspense_narrator; "
                "estimated full TTS 0.1982 USD plus selector overhead under 1 USD title cap; no ASR, upload, "
                "publication, frontend exposure, or release-gate mutation."
            ),
            "allowed_slugs": ["a-ghost-story"],
            "stop_conditions": [
                "Any paid gate or OPENAI_API_KEY is missing",
                "Source, rights, content, or selector evidence changes",
                "Estimated TTS exceeds the title or sprint cap",
                "A prior full-TTS attempt already called the provider",
                "Any upload, publication, frontend exposure, or release mutation is attempted",
            ],
            "updated_at": iso_now(),
        }
    )
    return payload


def selector_evidence() -> dict:
    if not BEST_AUDITION_PATH.is_file():
        raise RuntimeError("Best Stage 2C selector audition evidence is missing")
    evidence = json.loads(BEST_AUDITION_PATH.read_text(encoding="utf-8"))
    if evidence.get("voice") != "verse" or evidence.get("profile") != "mystery_suspense_narrator":
        raise RuntimeError("Stage 2C selector arm changed")
    if float((evidence.get("scores") or {}).get("overall_listening_score") or 0) < 9.4:
        raise RuntimeError("Stage 2C selector did not meet the owner minimum")
    if float(evidence.get("confidence") or 0) < 0.9 or evidence.get("fatal_flags"):
        raise RuntimeError("Stage 2C selector confidence/fatal-flag gate failed")
    return evidence


def segmentation_repair_allowed(prior_run_dir: Path, manuscript: str) -> tuple[bool, str]:
    if not FULL_QA_RESULT_PATH.is_file():
        return False, "Prior full-QA evidence is missing"
    qa = json.loads(FULL_QA_RESULT_PATH.read_text(encoding="utf-8"))
    if qa.get("hook_blocker_category") != "audio_listening_quality_failed":
        return False, "Prior full-QA blocker was not listening quality"
    if float(qa.get("asr_source_score") or 0) < 9.7:
        return False, "Prior replacement did not pass ASR/source"
    prior_manifest_path = prior_run_dir / "tts_chunk_manifest.json"
    if not prior_manifest_path.is_file():
        return False, "Prior TTS chunk manifest is missing"
    prior_chunks = json.loads(prior_manifest_path.read_text(encoding="utf-8")).get("chunks") or []
    mid_sentence_boundaries = sum(
        1
        for left, right in zip(prior_chunks, prior_chunks[1:])
        if str(left.get("text") or "").rstrip()[-1:] not in {".", "!", "?", "।", "”", "’"}
        or str(right.get("text") or "").lstrip()[:1].islower()
    )
    if not mid_sentence_boundaries:
        return False, "Prior chunk manifest has no proven mid-sentence boundaries"
    sys.path.insert(0, str(ROOT / "internal/audiobook_lab/scripts/factory_hooks"))
    from common import normalize_text  # noqa: PLC0415
    from tts_hook import chunk_text  # noqa: PLC0415

    repaired_chunks = chunk_text(manuscript)
    rebuilt = " ".join(item["text"] for item in repaired_chunks)
    if normalize_text(rebuilt) != normalize_text(manuscript):
        return False, "Repaired chunker does not preserve normalized source"
    terminal = {".", "!", "?", "।", "”", "’"}
    if any(str(item.get("text") or "").rstrip()[-1:] not in terminal for item in repaired_chunks):
        return False, "Repaired chunker still has a non-terminal chunk boundary"
    return True, f"SENTENCE_SAFE_SEGMENTATION_CONFIRMED:{mid_sentence_boundaries}_prior_boundaries"


def asr_omission_repair_allowed(prior_run_dir: Path, manuscript: str) -> tuple[bool, str]:
    if not FULL_QA_RESULT_PATH.is_file():
        return False, "Prior full-QA evidence is missing"
    qa = json.loads(FULL_QA_RESULT_PATH.read_text(encoding="utf-8"))
    if qa.get("hook_blocker_category") != "asr":
        return False, "Prior full-QA blocker was not ASR/source"
    if float(qa.get("asr_source_score") or 0) >= 9.7:
        return False, "Prior ASR/source score did not fail"
    if qa.get("first_words_match") is not True or qa.get("last_words_match") is not True:
        return False, "Prior audio did not preserve both source boundaries"
    transcript_path = prior_run_dir / "asr_transcript.txt"
    manifest_path = prior_run_dir / "tts_chunk_manifest.json"
    if not transcript_path.is_file() or not manifest_path.is_file():
        return False, "Prior transcript or TTS chunk manifest is missing"
    sys.path.insert(0, str(ROOT / "internal/audiobook_lab/scripts/factory_hooks"))
    from common import normalize_text, word_tokens  # noqa: PLC0415
    from tts_hook import chunk_text  # noqa: PLC0415

    source_tokens = word_tokens(normalize_text(manuscript))
    transcript_tokens = word_tokens(normalize_text(transcript_path.read_text(encoding="utf-8")))
    omitted_spans = [
        i2 - i1
        for tag, i1, i2, _j1, _j2 in SequenceMatcher(
            None,
            source_tokens,
            transcript_tokens,
            autojunk=False,
        ).get_opcodes()
        if tag in {"delete", "replace"}
    ]
    longest_omission = max(omitted_spans, default=0)
    if longest_omission < 20:
        return False, "No material contiguous ASR/source omission was proven"
    prior_chunks = json.loads(manifest_path.read_text(encoding="utf-8")).get("chunks") or []
    previous_max = max((len(str(item.get("text") or "")) for item in prior_chunks), default=0)
    repaired_chunks = chunk_text(manuscript, max_chars=1600)
    rebuilt = " ".join(item["text"] for item in repaired_chunks)
    if normalize_text(rebuilt) != normalize_text(manuscript):
        return False, "Reduced-size chunking does not preserve normalized source"
    if any(len(str(item.get("text") or "")) > 1600 for item in repaired_chunks):
        return False, "Reduced-size chunking exceeds 1,600 characters"
    if len(repaired_chunks) <= len(prior_chunks) or previous_max <= 1600:
        return False, "Reduced-size chunking does not materially change the failed segmentation"
    return True, f"ASR_SOURCE_OMISSION_CONFIRMED:{longest_omission}_tokens;MAX_CHARS_1600"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--asset-root",
        default=os.environ.get("EARNALISM_STAGE2C_ASSET_ROOT", str(ROOT)),
    )
    parser.add_argument(
        "--run-dir",
        default="/tmp/earnalism-a-ghost-stage2c-full-tts",
    )
    parser.add_argument("--prior-run-dir", default="/tmp/earnalism-a-ghost-stage2c-full-tts")
    parser.add_argument("--regenerate-after-segmentation-repair", action="store_true")
    parser.add_argument("--regenerate-after-asr-omission-repair", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = runtime_gate_errors()
    if errors:
        print(json.dumps({"status": "BLOCKED_RUNTIME_GATES", "errors": errors}, indent=2))
        return 2
    prior_runtime = {}
    if RESULT_PATH.exists():
        prior = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
        if prior.get("provider_calls_ran") is True:
            prior_runtime = prior

    selector = selector_evidence()
    asset_root = Path(args.asset_root).expanduser().resolve()
    run_dir = Path(args.run_dir).expanduser().resolve()
    manuscript_path = (
        asset_root
        / "internal/audiobook_lab/release_gate/a-ghost-story_20260705T150049Z/clean_manuscript.txt"
    )
    integrity_path = (
        asset_root
        / "internal/audiobook_lab/release_gate/a-ghost-story_20260705T150049Z/content_integrity_report.json"
    )
    rights_path = (
        asset_root
        / "internal/audiobook_lab/release_gate/a-ghost-story_20260705T150049Z/rights_metadata_report.json"
    )
    lock_path = asset_root / "internal/earnalism_intelligence/locks/paid_tts.lock"
    for path in (manuscript_path, integrity_path, rights_path, lock_path):
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError(f"Required full-TTS preflight artifact is missing: {path}")
    manuscript = manuscript_path.read_text(encoding="utf-8")
    if hashlib.sha256(manuscript.encode("utf-8")).hexdigest() != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("A Ghost Story source hash changed")
    integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    rights = json.loads(rights_path.read_text(encoding="utf-8"))
    if integrity.get("status") != "PASS" or rights.get("status") != "PASS":
        raise RuntimeError("Content integrity or rights gate is not PASS")
    repair_reason = ""
    if prior_runtime:
        prior_run_dir = Path(args.prior_run_dir).expanduser().resolve()
        if args.regenerate_after_asr_omission_repair:
            allowed, repair_reason = asr_omission_repair_allowed(prior_run_dir, manuscript)
            if os.environ.get("EARNALISM_OPENAI_TTS_MAX_CHARS_PER_CHUNK") != "1600":
                allowed = False
                repair_reason = "EARNALISM_OPENAI_TTS_MAX_CHARS_PER_CHUNK must equal 1600"
        else:
            allowed, repair_reason = segmentation_repair_allowed(prior_run_dir, manuscript)
        if not (
            (args.regenerate_after_segmentation_repair or args.regenerate_after_asr_omission_repair)
            and allowed
        ):
            print(
                json.dumps(
                    {
                        "status": "BLOCKED_REPEAT_FULL_TTS",
                        "prior": str(RESULT_PATH),
                        "segmentation_repair_allowed": allowed,
                        "segmentation_repair_reason": repair_reason,
                    },
                    indent=2,
                )
            )
            return 4

    estimated_tts_usd = round(len(manuscript) / 1000.0 * 0.015, 4)
    if estimated_tts_usd > float(os.environ["EARNALISM_TTS_MAX_ESTIMATED_USD"]):
        raise RuntimeError("Estimated full TTS exceeds the configured title cap")
    original_lock = lock_path.read_bytes()
    lock = load_lock(original_lock)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "clean_manuscript.txt").write_text(manuscript, encoding="utf-8")
    (run_dir / "content_integrity_report.json").write_text(
        json.dumps(integrity, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    preflight = {
        "status": "PASS",
        "owner_decision": "AUTHORIZE_STAGE_2C_A_GHOST_STORY_AUDIO_REPAIR_AND_PUBLICATION_IF_QUALITY_10_TARGET_PASSES",
        "slug": "a-ghost-story",
        "provider": "openai",
        "model": os.environ.get("EARNALISM_FACTORY_TTS_MODEL", "gpt-4o-mini-tts"),
        "voice": "verse",
        "profile": "mystery_suspense_narrator",
        "source_hash": EXPECTED_SOURCE_SHA256,
        "source_chars": len(manuscript),
        "source_words": len(manuscript.split()),
        "rights_status": rights.get("status"),
        "content_integrity_status": integrity.get("status"),
        "selector_overall_score": (selector.get("scores") or {}).get("overall_listening_score"),
        "selector_confidence": selector.get("confidence"),
        "selector_fatal_flags": selector.get("fatal_flags"),
        "selector_role": "OWNER_MINIMUM_PASS_SELECTION_ONLY_NOT_RELEASE_PROOF",
        "regenerate_after_segmentation_repair": bool(args.regenerate_after_segmentation_repair),
        "regenerate_after_asr_omission_repair": bool(args.regenerate_after_asr_omission_repair),
        "max_chars_per_chunk": int(os.environ.get("EARNALISM_OPENAI_TTS_MAX_CHARS_PER_CHUNK", "2600")),
        "segmentation_repair_reason": repair_reason or None,
        "prior_attempt": {
            "hook_status": prior_runtime.get("hook_status"),
            "final_audio_path": prior_runtime.get("final_audio_path"),
            "final_audio_size_bytes": prior_runtime.get("final_audio_size_bytes"),
        }
        if prior_runtime
        else None,
        "estimated_tts_usd": estimated_tts_usd,
        "provider_calls_ran": False,
        "asr_ran": False,
        "publication_performed": False,
        "lock_sha256_before": hashlib.sha256(original_lock).hexdigest(),
    }
    if args.dry_run:
        print(json.dumps({**preflight, "status": "DRY_RUN_PASS", "run_dir": str(run_dir)}, indent=2))
        return 0

    command = [
        sys.executable,
        str(HOOK),
        "--slug",
        "a-ghost-story",
        "--run-dir",
        str(run_dir),
        "--manifest",
        str(ROOT / "book_import_manifest.json"),
        "--language",
        "eng",
        "--title",
        "A Ghost Story",
        "--author",
        "Mark Twain",
        "--max-attempts",
        "1",
        "--fail-closed",
    ]
    started_at = iso_now()
    completed: subprocess.CompletedProcess | None = None
    error = ""
    try:
        atomic_write(
            lock_path,
            json.dumps(acquired_lock_payload(lock), ensure_ascii=False, indent=2).encode("utf-8") + b"\n",
        )
        completed = subprocess.run(command, cwd=ROOT, env=os.environ.copy(), check=False)
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    finally:
        atomic_write(lock_path, original_lock)

    hook_result_path = run_dir / "tts_hook_result.json"
    hook_result = json.loads(hook_result_path.read_text(encoding="utf-8")) if hook_result_path.exists() else {}
    hook_status = str(hook_result.get("status") or "MISSING")
    final_audio_value = (
        (hook_result.get("artifacts") or {}).get("final_audio_path")
        or (hook_result.get("updated_fields") or {}).get("final_audio_path")
        or ""
    )
    final_audio = Path(final_audio_value)
    if final_audio_value and not final_audio.is_absolute():
        final_audio = ROOT / final_audio
    runtime = {
        **preflight,
        "status": "FULL_TTS_PASS_QA_PENDING" if hook_status == "PASS" else "FULL_TTS_BLOCKED",
        "started_at": started_at,
        "finished_at": iso_now(),
        "provider_calls_ran": bool(completed and hook_status in {"PASS", "BLOCKED"}),
        "process_returncode": completed.returncode if completed else None,
        "hook_status": hook_status,
        "hook_blocker_category": hook_result.get("blocker_category"),
        "hook_blockers": hook_result.get("blockers") or [],
        "hook_metrics": hook_result.get("metrics") or {},
        "final_audio_path": str(final_audio) if final_audio_value else "",
        "final_audio_exists": final_audio.is_file() if final_audio_value else False,
        "final_audio_size_bytes": final_audio.stat().st_size if final_audio_value and final_audio.is_file() else 0,
        "actual_provider_billing": "NOT_REPORTED",
        "error": error or None,
        "lock_restored": lock_path.read_bytes() == original_lock,
        "lock_sha256_after": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "publication_performed": False,
    }
    atomic_write(RESULT_PATH, json.dumps(runtime, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    print(json.dumps(runtime, ensure_ascii=False, indent=2))
    return 0 if hook_status == "PASS" and runtime["final_audio_exists"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
