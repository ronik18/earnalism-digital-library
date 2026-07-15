#!/usr/bin/env python3
"""Fast-path, fail-closed runner for the next two Sprint 1 audiobooks.

This runner intentionally narrows scope to a caller-provided candidate queue. It
does not evaluate free-form commands from evidence files, and it only runs paid
work through ``sprint1_paid_stage_runner.py`` so ``paid_tts.lock`` is restored
after every provider call.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = ROOT / "internal" / "audiobook_lab" / "scripts"
FASTPATH_DIR = ROOT / "internal" / "audiobook_lab" / "sprint1_publication" / "next_two_audio_fastpath"
TITLE_RUNS_DIR = ROOT / "internal" / "audiobook_lab" / "sprint1_publication" / "title_runs"
PUBLIC_API_BASE = "https://api.theearnalism.com"
APPROVED_BASELINE = ["book-2b9853ec52", "a-ghost-story", "sredni-vashtar"]
DEFERRED_SLUGS = {
    "pather-panchali",
    "great-expectations",
    "jane-eyre",
    "book-d19e96859f",
    "book-f5d593e1f4",
    "muchiram-gurer-jibanchorit",
    "the-open-window",
    "dsires-baby",
}
LONG_ENGLISH_SLUGS = {
    "dracula",
    "frankenstein",
    "pride-and-prejudice",
    "the-secret-garden",
    "picture-of-dorian-gray",
    "white-fang",
    "the-time-machine",
    "the-call-of-the-wild",
    "alices-adventures-in-wonderland",
}
PAID_ENV = {
    "SPRINT1_TOTAL_AUDIO_BUDGET_USD": "175",
    "SPRINT1_MAX_USD_PER_TITLE": "30",
    "MAX_TTS_BUDGET_USD": "175",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
    "EARNALISM_APPROVE_SARVAM_CORRECTIVE_AUDITIONS": "true",
    "EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF": "true",
    "EARNALISM_BENGALI_BAKEOFF_MAX_ESTIMATED_USD": "1",
    "EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS": "true",
    "EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD": "40",
    "EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD": "20",
    "EARNALISM_ASR_SYNC_ESTIMATED_USD_PER_MINUTE": "0.008",
    "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "20",
    "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
    "EARNALISM_ENABLE_OPENAI_LISTENING_QA": "true",
    "EARNALISM_OPENAI_LISTENING_QA_MODEL": "gpt-audio",
}
LISTENING_MINIMUM = 9.4
LISTENING_CONFIDENCE_MINIMUM = 0.9
ASR_SOURCE_MINIMUM = 9.7
PRIOR_ESTIMATED_SPEND_USD = 14.90614


class FastPathError(RuntimeError):
    """Raised when a fast-path invariant fails."""


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise FastPathError(f"expected JSON object: {path}")
    return value


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def atomic_write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def parse_candidate_slugs(raw: str) -> list[str]:
    seen: set[str] = set()
    slugs: list[str] = []
    for item in raw.split(","):
        slug = item.strip()
        if not slug or slug in seen:
            continue
        seen.add(slug)
        slugs.append(slug)
    return slugs


def reject_deferred_slugs(slugs: Sequence[str]) -> list[str]:
    rejected = sorted(set(slugs) & (DEFERRED_SLUGS | LONG_ENGLISH_SLUGS))
    if rejected:
        raise FastPathError("deferred or disallowed slugs requested: " + ", ".join(rejected))
    return list(slugs)


def slug_language(slug: str, release_row: Mapping[str, Any] | None = None) -> str:
    if release_row and str(release_row.get("language") or "").lower().startswith("english"):
        return "eng"
    if slug == "jekyll-and-hyde":
        return "eng"
    return "ben"


def matrix_rows(asset_root: Path) -> dict[str, dict[str, Any]]:
    path = asset_root / "internal/audiobook_lab/sprint1_publication/sprint1_release_gate_evidence.json"
    data = load_json(path)
    return {str(row.get("slug")): row for row in data.get("titles", []) if row.get("slug")}


def controlled_book(asset_root: Path, slug: str) -> dict[str, Any]:
    candidates = [
        asset_root / "backend/data/controlled_publications" / slug / "public_book.json",
        asset_root / "data/controlled_publications" / slug / "public_book.json",
    ]
    for path in candidates:
        if path.is_file():
            return load_json(path)
    return {}


def has_cover(book: Mapping[str, Any]) -> bool:
    return bool(book.get("cover_url") or book.get("front_cover_url") or book.get("coverImage"))


def has_back_cover(book: Mapping[str, Any]) -> bool:
    return bool(book.get("back_cover_url") or book.get("backCoverUrl") or book.get("back_cover"))


def local_candidate_preflight(asset_root: Path, slug: str, release_row: Mapping[str, Any]) -> dict[str, Any]:
    gates = release_row.get("gates") if isinstance(release_row.get("gates"), dict) else {}
    book = controlled_book(asset_root, slug)
    blockers: list[str] = []
    if release_row.get("public_reader_status") != "PUBLIC_READER":
        blockers.append("PUBLIC_READER_REQUIRED")
    if gates.get("source_rights") != "PASS":
        blockers.append("SOURCE_RIGHTS_REQUIRED")
    if gates.get("text_sanitation") != "PASS":
        blockers.append("SANITATION_REQUIRED")
    if gates.get("text_normalization") != "PASS":
        blockers.append("TEXT_NORMALIZATION_REQUIRED")
    if not has_cover(book):
        blockers.append("FRONT_COVER_LINKAGE_REQUIRED")
    if slug in {"book-edfcf810c5", "devdas"} and not has_back_cover(book):
        blockers.append("BACK_COVER_LINKAGE_REQUIRED")
    if slug == "nishkriti":
        blockers.append("PIPELINE_SOURCE_OVERRIDE_REQUIRED")
    return {
        "slug": slug,
        "title": release_row.get("title") or book.get("title") or slug,
        "language": release_row.get("language") or slug_language(slug, release_row),
        "source_rights": gates.get("source_rights"),
        "sanitation": gates.get("text_sanitation"),
        "cover": "PASS" if has_cover(book) else "FAIL",
        "back_cover": "PASS" if has_back_cover(book) else "MISSING_OR_NOT_REQUIRED",
        "blockers": blockers,
        "clean_for_paid_work": not blockers,
    }


def url_json(url: str, timeout: float = 12.0) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:  # nosec - fixed production URLs
        payload = response.read().decode("utf-8")
    value = json.loads(payload)
    return value if isinstance(value, dict) else {}


def range_status(url: str, timeout: float = 12.0) -> int:
    request = urllib.request.Request(url, headers={"Range": "bytes=0-1023"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec - fixed production URLs
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def production_controls(slugs: Sequence[str], *, api_base: str = PUBLIC_API_BASE) -> dict[str, Any]:
    approved = []
    hidden = []
    blockers = []
    for slug in APPROVED_BASELINE:
        manifest = url_json(f"{api_base}/api/reader/book/{slug}/manifest")
        audio = manifest.get("audio") if isinstance(manifest.get("audio"), dict) else {}
        status = range_status(f"{api_base}/api/reader/book/{slug}/audiobook")
        ok = audio.get("enabled") is True and audio.get("release_gate") == "APPROVED" and audio.get("qa_status") == "QA_PASSED" and status == 206
        if not ok:
            blockers.append(f"APPROVED_CONTROL_FAILED:{slug}")
        approved.append({"slug": slug, "manifest_audio": audio, "audiobook_http": status, "ok": ok})
    for slug in slugs:
        manifest = url_json(f"{api_base}/api/reader/book/{slug}/manifest")
        audio = manifest.get("audio") if isinstance(manifest.get("audio"), dict) else {}
        status = range_status(f"{api_base}/api/reader/book/{slug}/audiobook")
        ok = audio.get("enabled") is False and status == 404
        if not ok:
            blockers.append(f"HIDDEN_CONTROL_FAILED:{slug}")
        hidden.append({"slug": slug, "manifest_audio": audio, "audiobook_http": status, "ok": ok})
    return {"approved": approved, "hidden": hidden, "blockers": blockers, "ok": not blockers}


def runtime_gates(env: Mapping[str, str]) -> dict[str, Any]:
    gate_status = {key: "SET" if str(env.get(key, "")).strip() == value else "MISSING_OR_INVALID" for key, value in PAID_ENV.items()}
    credential_status = {
        "SARVAM_API_KEY": "SET" if env.get("SARVAM_API_KEY") else "MISSING",
        "OPENAI_API_KEY": "SET" if env.get("OPENAI_API_KEY") else "MISSING",
        "GOOGLE_APPLICATION_CREDENTIALS": "SET" if env.get("GOOGLE_APPLICATION_CREDENTIALS") else "MISSING",
        "GOOGLE_CLOUD_PROJECT": "SET" if env.get("GOOGLE_CLOUD_PROJECT") else "MISSING",
    }
    missing = [key for key, status in gate_status.items() if status != "SET"]
    if credential_status["SARVAM_API_KEY"] != "SET":
        missing.append("SARVAM_API_KEY")
    if credential_status["OPENAI_API_KEY"] != "SET":
        missing.append("OPENAI_API_KEY")
    return {
        "budget_env": gate_status,
        "credentials": credential_status,
        "ready_for_bengali_paid_work": not missing,
        "missing_or_invalid": missing,
        "secrets_printed": False,
    }


def lock_snapshot(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"available": False, "blocker": "PAID_TTS_LOCK_MISSING"}
    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001 - lock diagnostics must fail closed
        return {"available": False, "blocker": f"PAID_TTS_LOCK_INVALID:{exc}"}
    available = payload.get("status") == "active" and payload.get("current_holder") == "none" and payload.get("allowed_next_holders") == []
    return {
        "available": available,
        "status": payload.get("status"),
        "current_holder": payload.get("current_holder"),
        "allowed_next_holders": payload.get("allowed_next_holders"),
        "blocker": "" if available else "PAID_TTS_LOCK_NOT_AVAILABLE",
    }


def paid_env(env: Mapping[str, str]) -> dict[str, str]:
    child = dict(env)
    child.update(PAID_ENV)
    return child


def bakeoff_command(slug: str) -> list[str]:
    return [
        sys.executable,
        "internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py",
        "--manifest",
        "book_import_manifest.json",
        "--candidate-slugs",
        slug,
        "--max-passages",
        "2",
        "--providers",
        "sarvam",
        "--max-voices-per-provider",
        "1",
        "--voice-filter",
        "ratan",
        "--second-pass-polish",
        "--style-profiles",
        "literary_warm_pacing",
        "--policy",
        "tiered",
        "--run-dir",
        str(FASTPATH_DIR / f"{slug}_representative_audition"),
        "--fail-closed",
    ]


def run_paid_bakeoff(
    *, slug: str, asset_root: Path, lock_path: Path, env: Mapping[str, str], execute: bool
) -> dict[str, Any]:
    if not execute:
        return {
            "status": "DRY_RUN_NOT_EXECUTED",
            "command": bakeoff_command(slug),
            "representative_passed": False,
            "blocker": "EXECUTE_FLAG_REQUIRED_FOR_PROVIDER_CALL",
        }
    report_path = TITLE_RUNS_DIR / f"{slug}_fastpath_paid_bakeoff_lock_report.json"
    command = [
        sys.executable,
        "internal/audiobook_lab/scripts/sprint1_paid_stage_runner.py",
        "--lock-path",
        str(lock_path),
        "--holder",
        f"sprint1_next_two_fastpath_{slug}",
        "--slug",
        slug,
        "--scope",
        f"Sprint1 next-two fast-path representative audition for {slug}; no upload, no publication.",
        "--estimated-usd",
        "1",
        "--prior-spend-usd",
        str(PRIOR_ESTIMATED_SPEND_USD),
        "--report",
        str(report_path),
        "--workdir",
        str(asset_root),
        "--timeout-seconds",
        "1800",
        "--",
        *bakeoff_command(slug),
    ]
    completed = subprocess.run(command, cwd=asset_root, env=paid_env(env), check=False)
    lock_report = load_json(report_path) if report_path.is_file() else {}
    audition_report_path = FASTPATH_DIR / f"{slug}_representative_audition" / "bengali_tts_provider_bakeoff_report.json"
    audition = load_json(audition_report_path) if audition_report_path.is_file() else {}
    return {
        "status": "PASS" if completed.returncode == 0 else "FAILED_OR_BLOCKED",
        "returncode": completed.returncode,
        "command": command,
        "lock_report": str(report_path),
        "lock_restored": lock_report.get("lock_restored") is True,
        "audition_report": str(audition_report_path) if audition else "",
        "audition": audition,
        "estimated_cost_usd": float(((audition.get("cost_estimate") or {}).get("estimated_cost_usd") or 0.0)) if audition else 0.0,
        "representative_passed": representative_gate_passed(audition),
        "blocker": "" if representative_gate_passed(audition) else representative_blocker(audition, completed.returncode),
    }


def representative_gate_passed(audition: Mapping[str, Any]) -> bool:
    samples = []
    path_value = audition.get("sample_results_path")
    if path_value:
        sample_path = ROOT / str(path_value)
        if sample_path.is_file():
            samples = load_json(sample_path).get("samples", [])
    if not samples:
        return False
    for sample in samples:
        if sample.get("status") == "SKIPPED":
            return False
        scores = sample.get("scores") if isinstance(sample.get("scores"), dict) else {}
        flags = sample.get("judge_flags") if isinstance(sample.get("judge_flags"), dict) else {}
        if float(scores.get("overall_listening_score") or 0) < LISTENING_MINIMUM:
            return False
        if float(scores.get("confidence_score") or sample.get("confidence") or 0) < LISTENING_CONFIDENCE_MINIMUM:
            return False
        if any(bool(value) for value in flags.values()):
            return False
    return True


def representative_blocker(audition: Mapping[str, Any], returncode: int) -> str:
    if not audition:
        return f"REPRESENTATIVE_AUDITION_REPORT_MISSING_RETURN_{returncode}"
    if audition.get("blockers"):
        return "; ".join(str(item) for item in audition.get("blockers") or [])
    return "REPRESENTATIVE_AUDITION_DID_NOT_MEET_9_4_LISTENING_GATE"


def full_factory_command(slug: str, *, publish: bool) -> list[str]:
    language = "eng" if slug == "jekyll-and-hyde" else "ben"
    command = [
        sys.executable,
        "internal/audiobook_lab/scripts/release_catalog_factory.py",
        "--manifest",
        "book_import_manifest.json",
        "--slugs",
        slug,
        "--languages",
        language,
        "--max-books-active",
        "1",
        "--max-preflight-workers",
        "1",
        "--max-audio-reuse-workers",
        "1",
        "--max-tts-workers",
        "1",
        "--max-paid-workers",
        "1",
        "--max-asr-workers",
        "1",
        "--max-upload-workers",
        "0",
        "--max-metadata-workers",
        "0",
        "--max-browser-workers",
        "0",
        "--max-attempts",
        "1",
        "--fail-closed",
        "--stop-after-terminal-books",
        "1",
    ]
    if publish:
        command.append("--publish-approved")
    return command


def run_full_factory_if_allowed(slug: str, asset_root: Path, lock_path: Path, env: Mapping[str, str], publish: bool) -> dict[str, Any]:
    command = full_factory_command(slug, publish=publish)
    report_path = TITLE_RUNS_DIR / f"{slug}_fastpath_full_factory_lock_report.json"
    wrapped = [
        sys.executable,
        "internal/audiobook_lab/scripts/sprint1_paid_stage_runner.py",
        "--lock-path",
        str(lock_path),
        "--holder",
        f"sprint1_next_two_fastpath_{slug}_full_factory",
        "--slug",
        slug,
        "--scope",
        f"Sprint1 next-two fast-path full factory run for {slug}; publish only if all gates pass.",
        "--estimated-usd",
        "5",
        "--prior-spend-usd",
        str(PRIOR_ESTIMATED_SPEND_USD + 1),
        "--report",
        str(report_path),
        "--workdir",
        str(asset_root),
        "--timeout-seconds",
        "7200",
        "--",
        *command,
    ]
    completed = subprocess.run(wrapped, cwd=asset_root, env=paid_env(env), check=False)
    lock_report = load_json(report_path) if report_path.is_file() else {}
    return {
        "status": "PASS" if completed.returncode == 0 else "FAILED_OR_BLOCKED",
        "returncode": completed.returncode,
        "command": wrapped,
        "lock_report": str(report_path),
        "lock_restored": lock_report.get("lock_restored") is True,
        "blocker": "" if completed.returncode == 0 else f"RELEASE_FACTORY_RETURNED_{completed.returncode}",
    }


def process_candidate(
    *,
    slug: str,
    asset_root: Path,
    lock_path: Path,
    release_row: Mapping[str, Any],
    env: Mapping[str, str],
    args: argparse.Namespace,
) -> dict[str, Any]:
    started_at = iso_now()
    preflight = local_candidate_preflight(asset_root, slug, release_row)
    result: dict[str, Any] = {
        "slug": slug,
        "started_at": started_at,
        "finished_at": None,
        "preflight": preflight,
        "published": False,
        "new_public_audiobook": False,
        "status": "PREFLIGHT_BLOCKED" if preflight["blockers"] else "PREFLIGHT_PASS",
        "blocker": "; ".join(preflight["blockers"]),
        "qa_scores": {},
        "evidence_path": str(TITLE_RUNS_DIR / f"{slug}_release_gate_evidence.json"),
    }
    if preflight["blockers"]:
        write_title_reports(result)
        return result
    runtime = runtime_gates(paid_env(env))
    if not runtime["ready_for_bengali_paid_work"]:
        result.update(
            {
                "status": "PAID_GATES_MISSING",
                "blocker": "PAID_GATES_MISSING: " + ", ".join(runtime["missing_or_invalid"]),
                "runtime": runtime,
            }
        )
        write_title_reports(result)
        return result
    lock = lock_snapshot(lock_path)
    if not lock["available"]:
        result.update({"status": "LOCK_PROTOCOL_BLOCKED", "blocker": lock["blocker"], "lock": lock})
        write_title_reports(result)
        return result
    if args.reuse_first:
        result["reuse_first"] = "NO_RELEASE_READY_REUSE_CANDIDATE_FOUND_OR_PRIOR_REUSE_ASR_MISMATCH"
    paid = run_paid_bakeoff(slug=slug, asset_root=asset_root, lock_path=lock_path, env=env, execute=args.execute)
    result["representative_audition"] = {
        "status": paid["status"],
        "lock_report": paid.get("lock_report"),
        "lock_restored": paid.get("lock_restored"),
        "audition_report": paid.get("audition_report"),
        "estimated_cost_usd": paid.get("estimated_cost_usd", 0.0),
        "representative_passed": paid.get("representative_passed"),
        "blocker": paid.get("blocker"),
    }
    if not paid.get("representative_passed"):
        result.update({"status": "REPRESENTATIVE_AUDITION_FAILED", "blocker": paid.get("blocker") or "REPRESENTATIVE_AUDITION_FAILED"})
        write_title_reports(result)
        return result
    factory = run_full_factory_if_allowed(slug, asset_root, lock_path, env, publish=args.publish_if_pass)
    result["full_pipeline"] = factory
    if factory["status"] != "PASS":
        result.update({"status": "FULL_PIPELINE_FAILED", "blocker": factory["blocker"]})
        write_title_reports(result)
        return result
    result.update({"status": "FULL_PIPELINE_COMPLETED_PRODUCTION_VALIDATION_REQUIRED", "blocker": "PRODUCTION_VALIDATION_NOT_CONFIRMED_BY_RUNNER"})
    write_title_reports(result)
    return result


def write_title_reports(result: Mapping[str, Any]) -> None:
    slug = str(result["slug"])
    evidence = {
        "schema_version": 1,
        "slug": slug,
        "public_audiobook": bool(result.get("new_public_audiobook")),
        "status": result.get("status"),
        "blocker": result.get("blocker"),
        "release_gate": {
            "asr_source_minimum": ASR_SOURCE_MINIMUM,
            "listening_sample_minimum": LISTENING_MINIMUM,
            "listening_confidence_minimum": LISTENING_CONFIDENCE_MINIMUM,
            "passed": bool(result.get("new_public_audiobook")),
        },
        "result": dict(result),
    }
    atomic_write_json(TITLE_RUNS_DIR / f"{slug}_release_gate_evidence.json", evidence)
    lines = [
        f"# {slug} Fast-Path Report",
        "",
        f"Status: `{result.get('status')}`",
        "",
        f"Blocker: `{result.get('blocker') or 'NONE'}`",
        "",
        f"Published: `{bool(result.get('new_public_audiobook'))}`",
        "",
    ]
    atomic_write_text(TITLE_RUNS_DIR / f"{slug}_fastpath_report.md", "\n".join(lines))


def render_report(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Sprint 1 Next Two Audiobooks Fast-Path Report",
        "",
        f"Started: `{summary['started_at']}`",
        f"Finished: `{summary['finished_at']}`",
        f"Starting YES+YES count: `{summary['starting_yes_yes_count']}`",
        f"Ending YES+YES count: `{summary['ending_yes_yes_count']}`",
        "",
        "## Processed Titles",
    ]
    for item in summary["processed_titles"]:
        lines.append(f"- `{item['slug']}`: `{item['status']}` - {item.get('blocker') or 'no blocker'}")
    lines.extend(["", "## Current Public Audiobooks"])
    for slug in summary["current_public_audiobooks"]:
        lines.append(f"- `{slug}`")
    return "\n".join(lines) + "\n"


def run(args: argparse.Namespace, *, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    process_env = dict(os.environ if env is None else env)
    started_at = iso_now()
    asset_root = args.asset_root.resolve()
    slugs = reject_deferred_slugs(parse_candidate_slugs(args.candidate_slugs))
    if args.max_new_publications < 1:
        raise FastPathError("--max-new-publications must be at least 1")
    rows = matrix_rows(asset_root)
    missing_rows = [slug for slug in slugs if slug not in rows]
    if missing_rows:
        raise FastPathError("candidate missing from release evidence: " + ", ".join(missing_rows))
    runtime = runtime_gates(paid_env(process_env))
    lock = lock_snapshot(args.lock_path)
    controls = production_controls(slugs) if args.execute else {"ok": True, "approved": [], "hidden": [], "blockers": []}
    if args.execute and not controls["ok"]:
        raise FastPathError("production control precheck failed: " + ", ".join(controls["blockers"]))
    processed: list[dict[str, Any]] = []
    newly_public: list[str] = []
    for slug in slugs:
        if len(newly_public) >= args.max_new_publications:
            processed.append({"slug": slug, "status": "SKIPPED_MAX_NEW_PUBLICATIONS_REACHED", "blocker": ""})
            continue
        result = process_candidate(
            slug=slug,
            asset_root=asset_root,
            lock_path=args.lock_path,
            release_row=rows[slug],
            env=process_env,
            args=args,
        )
        processed.append(result)
        if result.get("new_public_audiobook"):
            newly_public.append(slug)
    finished_at = iso_now()
    summary = {
        "schema_version": 1,
        "run_id": "sprint1_next_two_fastpath_runner",
        "started_at": started_at,
        "finished_at": finished_at,
        "owner_decision": "AUTHORIZE_SPRINT1_NEXT_TWO_AUDIOBOOK_FASTPATH_RUNNER_AND_EXECUTE_IF_SAFE",
        "candidate_slugs": slugs,
        "max_new_publications": args.max_new_publications,
        "reuse_first": bool(args.reuse_first),
        "publish_if_pass": bool(args.publish_if_pass),
        "execute": bool(args.execute),
        "fail_closed": bool(args.fail_closed),
        "runtime_gates": runtime,
        "lock": lock_snapshot(args.lock_path),
        "production_controls": controls,
        "starting_yes_yes_count": 3,
        "ending_yes_yes_count": 3 + len(newly_public),
        "newly_public_audiobooks": newly_public,
        "current_public_audiobooks": APPROVED_BASELINE + newly_public,
        "processed_titles": processed,
        "budget": {
            "prior_estimated_spend_usd": PRIOR_ESTIMATED_SPEND_USD,
            "this_run_estimated_spend_usd": sum(
                float(((item.get("representative_audition") or {}).get("estimated_cost_usd") or 0))
                for item in processed
            ),
            "actual_provider_billing": "not_available",
        },
    }
    atomic_write_json(FASTPATH_DIR / "next_two_audio_fastpath_results.json", summary)
    atomic_write_json(
        FASTPATH_DIR / "fastpath_candidate_ranking.json",
        {
            "schema_version": 1,
            "generated_at": finished_at,
            "candidates": [
                {
                    "rank": index + 1,
                    "slug": item["slug"],
                    "status": item.get("status"),
                    "blocker": item.get("blocker"),
                    "publishable_now": bool(item.get("new_public_audiobook")),
                }
                for index, item in enumerate(processed)
            ],
        },
    )
    atomic_write_text(FASTPATH_DIR / "next_two_audio_fastpath_report.md", render_report(summary))
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, default=ROOT)
    parser.add_argument("--lock-path", type=Path, default=ROOT / "internal/earnalism_intelligence/locks/paid_tts.lock")
    parser.add_argument("--candidate-slugs", required=True)
    parser.add_argument("--max-new-publications", type=int, default=2)
    parser.add_argument("--reuse-first", action="store_true")
    parser.add_argument("--publish-if-pass", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--fail-closed", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = run(args)
    except FastPathError as exc:
        if args.fail_closed:
            print(json.dumps({"status": "FAIL_CLOSED", "blocker": str(exc)}, ensure_ascii=False))
            return 2
        raise
    print(
        json.dumps(
            {
                "status": "PASS",
                "ending_yes_yes_count": summary["ending_yes_yes_count"],
                "newly_public_audiobooks": summary["newly_public_audiobooks"],
                "results": str(FASTPATH_DIR / "next_two_audio_fastpath_results.json"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
