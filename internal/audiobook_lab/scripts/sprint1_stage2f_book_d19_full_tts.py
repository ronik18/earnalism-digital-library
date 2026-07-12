#!/usr/bin/env python3
"""Fail-closed preflight and bounded full-TTS wrapper for book-d19e96859f."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = ROOT / "internal" / "audiobook_lab" / "scripts"
HOOK_DIR = ROOT / "internal" / "audiobook_lab" / "scripts" / "factory_hooks"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(HOOK_DIR))

import tts_hook  # noqa: E402


SLUG = "book-d19e96859f"
TITLE = "গিন্নি"
AUTHOR = "রবীন্দ্রনাথ ঠাকুর"
HOLDER = "sprint1_publication_stage2f_book_d19"
MODEL = "bulbul:v3"
VOICE = "pooja"
STYLE = "dialogue_human_touch"
EVIDENCE_REL = "internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_representative_audition_evidence.json"
LOCK_REL = "internal/earnalism_intelligence/locks/paid_tts.lock"
REPORT_REL = "internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_stage2f_preflight.json"


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def prepare_content_integrity(run_dir: Path) -> dict:
    """Build the same source-bound manuscript evidence used by the release factory."""
    import release_catalog_factory as factory

    chapters = factory.load_rendered_chapters(SLUG)
    raw_text = "\n\n".join(chapter["text"].strip() for chapter in chapters if chapter["text"].strip()).strip()
    clean_text = tts_hook.prepare_bengali_tts_text(raw_text).strip() + "\n"
    state = factory.BookState(
        slug=SLUG,
        title=TITLE,
        author=AUTHOR,
        language="ben",
        order=0,
        catalog_dir=run_dir.parent,
        run_dir=run_dir,
    )
    integrity = factory.content_integrity_report(state, chapters, clean_text)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "clean_manuscript.txt").write_text(clean_text, encoding="utf-8")
    write_json(run_dir / "content_integrity_report.json", integrity)
    return integrity


def evaluate_tts_hook_result(returncode: int, run_dir: Path) -> dict:
    hook = read_json(run_dir / "stage_result.json") if (run_dir / "stage_result.json").exists() else {}
    status = str(hook.get("status") or "").upper()
    metrics = hook.get("metrics") if isinstance(hook.get("metrics"), dict) else {}
    passed = returncode == 0 and status == "PASS" and hook.get("ready_for_next_stage") is True
    provider_calls_ran = bool(metrics.get("audio_regenerated") or metrics.get("cache_misses"))
    return {
        "passed": passed,
        "provider_calls_ran": provider_calls_ran,
        "hook_status": status or "MISSING",
        "hook_ready_for_next_stage": hook.get("ready_for_next_stage") is True,
        "hook_blockers": hook.get("blockers") or [],
        "hook_result": hook,
    }


def required_runtime_gates() -> dict[str, str]:
    expected = {
        "SPRINT1_TOTAL_AUDIO_BUDGET_USD": "175",
        "SPRINT1_MAX_USD_PER_TITLE": "30",
        "MAX_TTS_BUDGET_USD": "175",
        "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
        "EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS": "true",
        "EARNALISM_ALLOW_TITLE_SPECIFIC_BENGALI_TTS_ARM": "true",
        "EARNALISM_BENGALI_FULL_PILOT_SLUG": SLUG,
        "EARNALISM_BENGALI_TTS_PROVIDER": "sarvam",
        "EARNALISM_BENGALI_TTS_MODEL": MODEL,
        "EARNALISM_BENGALI_TTS_VOICE": VOICE,
        "EARNALISM_BENGALI_TTS_STYLE": STYLE,
        "EARNALISM_BENGALI_REPRESENTATIVE_EVIDENCE_PATH": EVIDENCE_REL,
        "EARNALISM_ENABLE_OPENAI_LISTENING_QA": "true",
        "EARNALISM_OPENAI_LISTENING_QA_MODEL": "gpt-audio",
    }
    presence_only = (
        "EARNALISM_BENGALI_FULL_PILOT_MAX_ESTIMATED_USD",
        "EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD",
        "EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD",
        "EARNALISM_ASR_SYNC_ESTIMATED_USD_PER_MINUTE",
        "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD",
        "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD",
        "SARVAM_API_KEY",
        "OPENAI_API_KEY",
    )
    status = {
        key: "SET" if os.environ.get(key, "").strip().lower() == value.lower() else "MISSING_OR_INVALID"
        for key, value in expected.items()
    }
    status.update({key: "SET" if os.environ.get(key, "").strip() else "MISSING_OR_INVALID" for key in presence_only})
    return status


def source_preflight(asset_root: Path) -> dict:
    chapter_path = asset_root / "data/controlled_publications" / SLUG / "chapters/chapter-001.json"
    matrix_path = asset_root / "internal/audiobook_lab/sprint1_publication/sprint1_publication_matrix.json"
    cost_path = asset_root / "internal/audiobook_lab/sprint1_publication/sprint1_cost_report.json"
    evidence_path = asset_root / EVIDENCE_REL
    chapter = read_json(chapter_path)
    manuscript = str(chapter.get("content") or chapter.get("text") or chapter.get("body") or "")
    prepared = tts_hook.prepare_bengali_tts_text(manuscript)
    matrix = read_json(matrix_path)
    row = next(item for item in matrix["titles"] if item.get("slug") == SLUG)
    cost = read_json(cost_path)
    cost_row = next(item for item in cost["titles"] if item.get("slug") == SLUG)
    evidence = read_json(evidence_path)
    groups = tts_hook.sarvam_groups(prepared)
    tts_estimate = tts_hook.estimated_sarvam_cost_usd(prepared)
    asr_estimate = float(cost_row["estimated_full_asr_usd"])
    qa_estimate = float(cost_row["estimated_listening_qa_usd"])
    repair_estimate = round(tts_estimate + asr_estimate + qa_estimate, 4)
    blockers: list[str] = []
    if row.get("publicly_rendered_book") != "Yes":
        blockers.append("PUBLIC_READER_REQUIRED")
    if row.get("rights_status") != "PASS":
        blockers.append("SOURCE_RIGHTS_REQUIRED")
    if row.get("sanitation_status") != "PASS":
        blockers.append("SANITATION_REQUIRED")
    if tts_hook.prepared_text_source_terms(prepared):
        blockers.append("PREPARED_TEXT_SOURCE_TERMS_PRESENT")
    if prepared.rstrip().endswith("১২৯৮?") or prepared.rstrip().endswith("১২৯৮"):
        blockers.append("TRAILING_SOURCE_YEAR_PRESENT")
    exact_evidence = (
        evidence.get("status") == "PASS"
        and evidence.get("pilot_candidate_selected") == SLUG
        and evidence.get("provider") == "sarvam"
        and evidence.get("model") == MODEL
        and evidence.get("voice") == VOICE
        and evidence.get("best_style_profile") == STYLE
        and float(evidence.get("representative_score") or 0) >= 9.2
        and float(evidence.get("confidence") or 0) >= 0.90
        and not any(bool(value) for value in (evidence.get("fatal_flags_required") or {}).values())
    )
    if not exact_evidence:
        blockers.append("MATCHING_REPRESENTATIVE_AUDITION_REQUIRED")
    return {
        "chapter_path": str(chapter_path.relative_to(asset_root)),
        "source_characters": len(manuscript),
        "prepared_characters": len(prepared),
        "prepared_words": len(prepared.split()),
        "prepared_sha256": sha256_text(prepared),
        "group_count": len(groups),
        "group_characters": [len(item["text"]) for item in groups],
        "source_terms": tts_hook.prepared_text_source_terms(prepared),
        "rights_status": row.get("rights_status"),
        "sanitation_status": row.get("sanitation_status"),
        "public_reader_status": row.get("public_reader_status"),
        "cover_status": "PASS",
        "representative_evidence": EVIDENCE_REL,
        "representative_score": evidence.get("representative_score"),
        "representative_confidence": evidence.get("confidence"),
        "selected_arm": {"provider": "sarvam", "model": MODEL, "voice": VOICE, "style": STYLE},
        "reuse_decision": "FRESH_FULL_TITLE_REGENERATION_REQUIRED_MISSING_VERIFIABLE_GROUP_CHUNKS",
        "estimated_tts_usd": tts_estimate,
        "estimated_asr_usd": asr_estimate,
        "estimated_listening_qa_usd": qa_estimate,
        "estimated_repair_pipeline_usd": repair_estimate,
        "prior_sprint_estimated_spend_usd": float(cost.get("estimated_spend_usd") or 0),
        "blockers": blockers,
    }


def budget_blockers(source: dict) -> list[str]:
    names = (
        "SPRINT1_TOTAL_AUDIO_BUDGET_USD",
        "SPRINT1_MAX_USD_PER_TITLE",
        "MAX_TTS_BUDGET_USD",
        "EARNALISM_BENGALI_FULL_PILOT_MAX_ESTIMATED_USD",
        "EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD",
        "EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD",
        "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD",
        "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD",
    )
    if any(not os.environ.get(name, "").strip() for name in names):
        return []
    try:
        values = {name: float(os.environ[name]) for name in names}
    except ValueError:
        return ["BUDGET_CAP_VALUE_INVALID"]
    blockers = []
    repair = float(source["estimated_repair_pipeline_usd"])
    prior = float(source["prior_sprint_estimated_spend_usd"])
    if repair > values["SPRINT1_MAX_USD_PER_TITLE"]:
        blockers.append("ESTIMATED_REPAIR_EXCEEDS_PER_TITLE_CAP")
    if prior + repair > values["SPRINT1_TOTAL_AUDIO_BUDGET_USD"]:
        blockers.append("ESTIMATED_REPAIR_EXCEEDS_REMAINING_SPRINT_CAP")
    if prior + repair > values["MAX_TTS_BUDGET_USD"]:
        blockers.append("ESTIMATED_REPAIR_EXCEEDS_MAX_TTS_BUDGET")
    if float(source["estimated_tts_usd"]) > values["EARNALISM_BENGALI_FULL_PILOT_MAX_ESTIMATED_USD"]:
        blockers.append("ESTIMATED_TTS_EXCEEDS_TITLE_TTS_CAP")
    if float(source["estimated_asr_usd"]) > values["EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD"]:
        blockers.append("ESTIMATED_ASR_EXCEEDS_ASR_CAP")
    if float(source["estimated_asr_usd"]) > values["EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD"]:
        blockers.append("ESTIMATED_ASR_EXCEEDS_RETRY_CAP")
    if float(source["estimated_listening_qa_usd"]) > values["EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD"]:
        blockers.append("ESTIMATED_LISTENING_QA_EXCEEDS_QA_CAP")
    if values["EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD"] <= 0:
        blockers.append("LISTENING_QA_UNIT_ESTIMATE_MUST_BE_POSITIVE")
    return blockers


def validate_lock(lock_path: Path) -> dict:
    if not lock_path.exists():
        return {"status": "BLOCKED", "blocker": "paid_tts.lock is missing"}
    lock = read_json(lock_path)
    blockers = []
    if lock.get("status") != "active":
        blockers.append("paid_tts.lock status must be active")
    if lock.get("current_holder") != "none":
        blockers.append("paid_tts.lock already has a holder")
    if lock.get("allowed_next_holders") != []:
        blockers.append("paid_tts.lock allowed_next_holders must be empty")
    return {"status": "PASS" if not blockers else "BLOCKED", "blockers": blockers}


def acquire_lock(lock_path: Path, estimate: float) -> bytes:
    original = lock_path.read_bytes()
    lock = json.loads(original)
    lock.update(
        {
            "status": "active",
            "current_holder": HOLDER,
            "allowed_next_holders": [],
            "holder_started_at": iso_now(),
            "budget_cap_usd": float(os.environ["SPRINT1_MAX_USD_PER_TITLE"]),
            "approved_scope": f"{SLUG} clean full-title Sarvam TTS only; no upload, publication, or release mutation",
            "allowed_slugs": [SLUG],
            "stop_conditions": [
                "any required runtime gate or provider key is missing",
                "estimated title or sprint spend exceeds configured cap",
                "matching representative evidence does not pass",
                "prepared narration text contains source metadata",
                "provider output is missing, empty, or corrupt",
            ],
            "stage_2f_scope": {
                "slug": SLUG,
                "provider": "sarvam",
                "model": MODEL,
                "voice": VOICE,
                "style": STYLE,
                "estimated_tts_usd": estimate,
                "no_upload": True,
                "no_publication": True,
            },
            "updated_at": iso_now(),
        }
    )
    write_json(lock_path, lock)
    return original


def command_for_retry() -> str:
    env = [
        "SPRINT1_TOTAL_AUDIO_BUDGET_USD=175",
        "SPRINT1_MAX_USD_PER_TITLE=30",
        "MAX_TTS_BUDGET_USD=175",
        "EARNALISM_STOP_ON_BUDGET_EXCEEDED=true",
        "EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS=true",
        "EARNALISM_ALLOW_TITLE_SPECIFIC_BENGALI_TTS_ARM=true",
        f"EARNALISM_BENGALI_FULL_PILOT_SLUG={SLUG}",
        "EARNALISM_BENGALI_FULL_PILOT_MAX_ESTIMATED_USD=1",
        "EARNALISM_BENGALI_TTS_PROVIDER=sarvam",
        f"EARNALISM_BENGALI_TTS_MODEL={MODEL}",
        f"EARNALISM_BENGALI_TTS_VOICE={VOICE}",
        f"EARNALISM_BENGALI_TTS_STYLE={STYLE}",
        f"EARNALISM_BENGALI_REPRESENTATIVE_EVIDENCE_PATH={EVIDENCE_REL}",
        "EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD=1",
        "EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD=1",
        "EARNALISM_ASR_SYNC_ESTIMATED_USD_PER_MINUTE=0.008",
        "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD=1",
        "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD=0.05",
        "EARNALISM_ENABLE_OPENAI_LISTENING_QA=true",
        "EARNALISM_OPENAI_LISTENING_QA_MODEL=gpt-audio",
    ]
    separator = " \\" + "\n  "
    return separator.join(env + ["PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/sprint1_stage2f_book_d19_full_tts.py --execute"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-root", type=Path, default=ROOT)
    parser.add_argument("--run-dir", type=Path, default=Path("internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_stage2f_full_tts"))
    parser.add_argument("--lock-path", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    asset_root = args.asset_root.resolve()
    run_dir = args.run_dir if args.run_dir.is_absolute() else asset_root / args.run_dir
    source = source_preflight(asset_root)
    integrity = prepare_content_integrity(run_dir)
    runtime = required_runtime_gates()
    missing = [key for key, value in runtime.items() if value != "SET"]
    lock_path = args.lock_path.resolve() if args.lock_path else asset_root / LOCK_REL
    lock = validate_lock(lock_path)
    blockers = list(source["blockers"])
    if integrity.get("status") != "PASS":
        blockers.extend(integrity.get("blocker_reasons") or ["CONTENT_INTEGRITY_REQUIRED"])
    if missing:
        blockers.append("PAID_RUNTIME_ENV_GATES_MISSING: " + ", ".join(missing))
    if lock.get("status") != "PASS":
        blockers.extend(lock.get("blockers") or [lock.get("blocker") or "LOCK_PROTOCOL_BLOCKED"])
    blockers.extend(budget_blockers(source))
    status = "READY_FOR_BOUNDED_FULL_REGENERATION" if not blockers else "PROVIDER_RETRY_REQUIRED"
    report = {
        "generated_at": iso_now(),
        "slug": SLUG,
        "title": TITLE,
        "status": status,
        "classification": status,
        "source_preflight": source,
        "content_integrity": integrity,
        "runtime_gates": runtime,
        "runtime_gate_values_redacted": True,
        "lock_preflight": lock,
        "provider_calls_ran": False,
        "paid_tts_ran": False,
        "public_audio_approved": False,
        "release_gate_mutated": False,
        "blockers": blockers,
        "next_command": command_for_retry(),
    }
    report_path = asset_root / REPORT_REL
    if not args.execute or blockers:
        write_json(report_path, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2 if args.execute and blockers else 0

    original_lock = acquire_lock(lock_path, source["estimated_tts_usd"])
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable,
            str(asset_root / "internal/audiobook_lab/scripts/factory_hooks/tts_hook.py"),
            "--slug",
            SLUG,
            "--run-dir",
            str(run_dir),
            "--manifest",
            str(asset_root / "book_import_manifest.json"),
            "--language",
            "ben",
            "--title",
            TITLE,
            "--author",
            AUTHOR,
            "--fail-closed",
        ]
        completed = subprocess.run(command, cwd=asset_root, text=True, capture_output=True, check=False)
        outcome = evaluate_tts_hook_result(completed.returncode, run_dir)
        report.update(
            {
                "provider_calls_ran": outcome["provider_calls_ran"],
                "paid_tts_ran": outcome["passed"],
                "tts_returncode": completed.returncode,
                "tts_hook_status": outcome["hook_status"],
                "tts_hook_ready_for_next_stage": outcome["hook_ready_for_next_stage"],
                "tts_hook_blockers": outcome["hook_blockers"],
                "tts_stdout_tail": completed.stdout[-4000:],
                "tts_stderr_tail": completed.stderr[-4000:],
                "run_dir": str(run_dir.relative_to(asset_root)),
                "status": "FULL_TTS_GENERATED_QA_REQUIRED" if outcome["passed"] else "PROVIDER_RETRY_REQUIRED",
                "classification": "FULL_TTS_GENERATED_QA_REQUIRED" if outcome["passed"] else "PROVIDER_RETRY_REQUIRED",
            }
        )
        write_json(report_path, report)
        return 0 if outcome["passed"] else (completed.returncode or 3)
    finally:
        lock_path.write_bytes(original_lock)


if __name__ == "__main__":
    raise SystemExit(main())
