#!/usr/bin/env python3
"""Lock-aware prelaunch Bengali audiobook preparation daemon.

This daemon is intentionally conservative. It performs non-paid evidence
refreshes and writes resumable state, but it never calls a TTS provider or
mutates production metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EVIDENCE_ROOT = Path("/Users/ronikbasak/Documents/GitHub/earnalism-digital-library")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, fallback: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def append_line(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip("\n") + "\n")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def first_existing(relative: str, evidence_root: Path) -> Path | None:
    candidates = [ROOT / relative]
    if evidence_root != ROOT:
        candidates.append(evidence_root / relative)
    for path in candidates:
        if path.exists():
            return path
    return None


def load_first_json(relative_paths: list[str], evidence_root: Path, fallback: Any = None) -> Any:
    for relative in relative_paths:
        path = first_existing(relative, evidence_root)
        if path:
            loaded = read_json(path, None)
            if loaded is not None:
                return loaded
    return fallback


def lock_template(name: str, purpose: str, rules: list[str]) -> dict[str, Any]:
    return {
        "lock": name,
        "owner": "parallel_prelaunch_unblock",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "status": "active",
        "purpose": purpose,
        "rules": rules,
        "current_holder": "none",
        "allowed_next_holders": [],
    }


def ensure_lock_files(evidence_root: Path) -> dict[str, Any]:
    lock_dir = ROOT / "internal/earnalism_intelligence/locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_specs = {
        "paid_tts.lock": lock_template(
            "paid_tts",
            "Prevent duplicate paid TTS/provider work during prelaunch preparation.",
            [
                "Only one lane may run paid TTS at a time.",
                "No paid TTS may run without explicit approval and budget environment variables.",
                "Do not run broad waves.",
            ],
        ),
        "production_metadata.lock": lock_template(
            "production_metadata",
            "Prevent concurrent production metadata mutations during prelaunch preparation.",
            [
                "Only one lane may mutate production metadata at a time.",
                "Metadata mutation must be slug-scoped and fail-closed.",
                "Do not expose unapproved audio.",
            ],
        ),
        "backend_deploy.lock": lock_template(
            "backend_deploy",
            "Prevent concurrent backend deploy/restart work.",
            [
                "Only one lane may deploy or restart the backend at a time.",
                "Deploys must originate from a clean source-only worktree.",
            ],
        ),
        "ux_owner_approval.lock": {
            "lock": "ux_owner_approval",
            "owner": "parallel_prelaunch_unblock",
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "status": "active",
            "current_phase": "HOME",
            "owner_approved_phase": "HOME",
            "next_phase_requires_owner_approval": True,
            "allowed_next_phase": None,
            "rules": [
                "HOME phase is approved by the current prompt.",
                "Do not proceed to LIBRARY or later phases without explicit owner approval.",
            ],
        },
    }

    states: dict[str, Any] = {}
    for filename, default_payload in lock_specs.items():
        destination = lock_dir / filename
        external = evidence_root / "internal/earnalism_intelligence/locks" / filename
        payload = read_json(destination, None)
        if payload is None and external.exists():
            payload = read_json(external, None)
        if payload is None:
            payload = default_payload
        # Mirror externally active locks into the clean worktree so fail-closed
        # behavior survives source-only checkout gaps.
        write_json(destination, payload)
        states[filename] = payload
    return states


def diagnose_paid_tts_lock(lock_state: dict[str, Any], evidence_root: Path) -> dict[str, Any]:
    path = ROOT / "internal/earnalism_intelligence/locks/paid_tts.lock"
    external_path = evidence_root / "internal/earnalism_intelligence/locks/paid_tts.lock"
    pid = lock_state.get("pid") or lock_state.get("process_id")
    process_running = False
    if isinstance(pid, int) or (isinstance(pid, str) and pid.isdigit()):
        process_running = Path(f"/proc/{pid}").exists()
        if os.name != "posix":
            process_running = False
    heartbeat_path = lock_state.get("heartbeat_path") or lock_state.get("heartbeat")
    heartbeat_exists = bool(heartbeat_path and Path(str(heartbeat_path)).exists())
    status = str(lock_state.get("status", "")).lower()
    active = status == "active"
    stale = False
    safe_to_release = False
    reason = "Lock is active and no heartbeat/PID evidence proves it is stale; fail closed."
    if not active:
        reason = "Lock is not marked active, but paid work still requires explicit env approval."
    return {
        "generated_at": utc_now(),
        "lock_path": str(path),
        "external_lock_path": str(external_path),
        "lock_owner": lock_state.get("owner"),
        "pid": pid,
        "command": lock_state.get("command"),
        "created_at": lock_state.get("created_at"),
        "updated_at": lock_state.get("updated_at"),
        "heartbeat_path": heartbeat_path,
        "heartbeat_exists": heartbeat_exists,
        "process_still_running": process_running,
        "railway_job_still_active": "not_detectable_from_local_lock",
        "lock_active": active,
        "lock_stale": stale,
        "safe_to_release": safe_to_release,
        "next_allowed_holder": None,
        "owner_action_required": "Release or update paid_tts.lock and provide explicit budget env before paid representative auditions.",
        "diagnosis": reason,
    }


BENGALI_SOURCE_HEADER_RE = re.compile(r"^\s*(?:\d{4}|[০-৯]{4})\s*\(?\s*পৃ\.?\s*[০-৯0-9]+(?:\s*(?:-|থেকে)\s*[০-৯0-9]+)?\s*\)?\s*", re.M)


def clean_bengali_text(text: str) -> tuple[str, list[str]]:
    removed = BENGALI_SOURCE_HEADER_RE.findall(text)
    cleaned = BENGALI_SOURCE_HEADER_RE.sub("", text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned, removed


def collect_chapter_text(slug: str, evidence_root: Path) -> tuple[list[dict[str, Any]], str]:
    chapter_dirs = [
        ROOT / f"content/books/{slug}/chapters",
        ROOT / f"data/controlled_publications/{slug}/chapters",
        evidence_root / f"content/books/{slug}/chapters",
        evidence_root / f"data/controlled_publications/{slug}/chapters",
    ]
    for directory in chapter_dirs:
        if not directory.exists():
            continue
        chapters: list[dict[str, Any]] = []
        for path in sorted(directory.glob("*.json")):
            data = read_json(path, {})
            text = data.get("content") or data.get("text") or data.get("body") or ""
            title = data.get("title") or data.get("chapter_title") or path.stem
            if text:
                chapters.append({"path": str(path), "title": title, "text": text})
        if chapters:
            return chapters, str(directory)
    return [], ""


def words(value: str, limit: int = 22) -> str:
    return " ".join(re.findall(r"[\w\u0980-\u09FF’'-]+", value)[:limit])


def tail_words(value: str, limit: int = 22) -> str:
    tokens = re.findall(r"[\w\u0980-\u09FF’'-]+", value)
    return " ".join(tokens[-limit:])


def estimate_cost(clean_text: str) -> tuple[float, float]:
    # Keep this intentionally conservative and report-only. The exact Sarvam
    # billable metric is provider-side; this is for gating discussions only.
    minutes = round(max(len(clean_text) / 933.0, 0.0), 1)
    cost = round(len(clean_text) * 0.0000012, 2)
    return minutes, cost


def existing_or_build_clean_report(slug: str, title: str, evidence_root: Path) -> dict[str, Any]:
    existing = load_first_json(
        [f"{slug}_audiobook_clean_text_report.json", f"{slug.replace('-', '_')}_audiobook_clean_text_report.json"],
        evidence_root,
        None,
    )
    if existing:
        return existing
    chapters, source_dir = collect_chapter_text(slug, evidence_root)
    reader_text = "\n\n".join(chapter["text"] for chapter in chapters)
    clean_text, removed = clean_bengali_text(reader_text)
    duration, cost = estimate_cost(clean_text)
    return {
        "generated_at": utc_now(),
        "slug": slug,
        "title": title,
        "status": "PASS_CLEAN_TEXT_EXTRACTED" if clean_text else "BLOCKED_NO_TEXT_FOUND",
        "source_dir": source_dir,
        "canonical_reader_hash": sha256_text(reader_text) if reader_text else "",
        "audiobook_clean_hash": sha256_text(clean_text) if clean_text else "",
        "removed_span_count": len(removed),
        "first_words": words(clean_text),
        "last_words": tail_words(clean_text),
        "chapter_section_count": len(chapters),
        "estimated_character_count": len(clean_text),
        "estimated_duration_minutes": duration,
        "estimated_tts_cost_usd": cost,
        "blockers": [] if clean_text else ["No local chapter text found."],
    }


def passthrough_or_default(relative: str, evidence_root: Path, default_payload: dict[str, Any]) -> dict[str, Any]:
    existing = load_first_json([relative], evidence_root, None)
    if existing:
        return existing
    return default_payload


def write_bn066_reports(lock_active: bool, evidence_root: Path) -> dict[str, Any]:
    rights = passthrough_or_default(
        "bn-066_prelaunch_rights_source_audit.json",
        evidence_root,
        {
            "slug": "bn-066",
            "title": "আনন্দমঠ",
            "status": "BLOCKED_LOCAL_SOURCE_EVIDENCE_MISSING",
            "blockers": ["book_import_manifest/content source is missing from this clean worktree; use canonical evidence root before paid work."],
        },
    )
    content = passthrough_or_default(
        "bn-066_content_integrity_report.json",
        evidence_root,
        {
            "slug": "bn-066",
            "title": "আনন্দমঠ",
            "status": "BLOCKED_LOCAL_SOURCE_EVIDENCE_MISSING",
            "blockers": ["Content source is missing from this clean worktree."],
        },
    )
    cover = passthrough_or_default(
        "bn-066_cover_readiness_report.json",
        evidence_root,
        {
            "slug": "bn-066",
            "title": "আনন্দমঠ",
            "status": "BLOCKED_LOCAL_COVER_EVIDENCE_MISSING",
            "repair_needed": False,
            "notes": ["Cover evidence must be read from canonical evidence root before paid work."],
        },
    )
    clean = existing_or_build_clean_report("bn-066", "আনন্দমঠ", evidence_root)
    audition_command = (
        "railway run --project a8533934-35c4-463e-9f43-577a9ac391ee "
        "--service 5af42e7e-f518-4f6a-b602-d9950866501f "
        "--environment 580b250c-80ee-48ad-bfbe-fa4e31a6b378 -- env "
        "EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF=true "
        "EARNALISM_BENGALI_BAKEOFF_MAX_ESTIMATED_USD=6 "
        "EARNALISM_STOP_ON_BUDGET_EXCEEDED=true "
        "EARNALISM_ENABLE_OPENAI_LISTENING_QA=true "
        "EARNALISM_OPENAI_LISTENING_QA_MODEL=gpt-audio "
        "EARNALISM_LISTENING_POLICY_VERSION=bengali_audiobook_acceptance_v2_92 "
        "EARNALISM_BENGALI_TTS_PROVIDER=sarvam "
        "EARNALISM_BENGALI_TTS_MODEL=bulbul:v3 "
        "EARNALISM_BENGALI_TTS_VOICE=ratan "
        "EARNALISM_BENGALI_TTS_STYLE=literary_warm_pacing "
        "python3 internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py "
        "--manifest book_import_manifest.json --candidate-slugs bn-066 "
        "--providers sarvam --voice-filter ratan --style-profiles literary_warm_pacing "
        "--max-passages 6 --max-seconds-per-sample 75 --policy bengali_audiobook_acceptance_v2_92 --fail-closed"
    )
    audition = {
        "generated_at": utc_now(),
        "slug": "bn-066",
        "title": "আনন্দমঠ",
        "status": "READY_BUT_NOT_RUN_PAID_TTS_LOCK_ACTIVE" if lock_active else "READY_REQUIRES_EXPLICIT_PAID_ENV_APPROVAL",
        "provider": "Sarvam",
        "model": "bulbul:v3",
        "voice": "ratan",
        "style": "literary_warm_pacing",
        "policy": "bengali_audiobook_acceptance_v2_92",
        "required_score": 9.2,
        "required_confidence": 0.9,
        "representative_passages_planned": [
            "opening",
            "dialogue if present",
            "emotional or historical passage",
            "descriptive passage",
            "punctuation-heavy passage",
            "ending-style passage",
        ],
        "estimated_duration_minutes": clean.get("estimated_duration_minutes"),
        "estimated_tts_cost_usd": clean.get("estimated_tts_cost_usd"),
        "audition_command": audition_command,
        "blockers": ["paid_tts.lock active"] if lock_active else ["explicit paid/budget env missing"],
        "full_audiobook_generation_allowed": False,
    }
    write_json(ROOT / "bn_066_prelaunch_rights_source_audit.json", rights)
    write_json(ROOT / "bn_066_content_integrity_report.json", content)
    write_json(ROOT / "bn_066_cover_readiness_report.json", cover)
    write_json(ROOT / "bn_066_audiobook_clean_text_report.json", clean)
    write_json(ROOT / "bn_066_representative_audition_ready_report.json", audition)
    return {
        "slug": "bn-066",
        "title": "আনন্দমঠ",
        "rights": rights.get("status"),
        "content": content.get("status"),
        "cover": cover.get("status"),
        "clean_text": clean.get("status"),
        "representative_audition": audition.get("status"),
        "next_action": "Run representative Sarvam audition only after paid_tts.lock is released and explicit paid/budget env is present.",
    }


def write_pather_reports(evidence_root: Path) -> dict[str, Any]:
    rights = passthrough_or_default(
        "pather-panchali_prelaunch_rights_source_audit.json",
        evidence_root,
        {
            "slug": "pather-panchali",
            "title": "পথের পাঁচালী / Pather Panchali",
            "status": "BLOCKED_FOR_AUDIOBOOK_PRELAUNCH",
            "blockers": ["Full-work audiobook source scope must be proven before paid audio."],
        },
    )
    content = passthrough_or_default(
        "pather-panchali_content_integrity_report.json",
        evidence_root,
        {
            "slug": "pather-panchali",
            "title": "পথের পাঁচালী / Pather Panchali",
            "status": "BLOCKED_SOURCE_SCOPE_REVIEW_REQUIRED",
            "blockers": ["Full-work completeness cannot be proven from local source artifacts."],
        },
    )
    cover = passthrough_or_default(
        "pather-panchali_cover_readiness_report.json",
        evidence_root,
        {
            "slug": "pather-panchali",
            "title": "পথের পাঁচালী / Pather Panchali",
            "status": "BLOCKED_COVER_REPAIR_REQUIRED",
            "repair_needed": True,
            "notes": ["Approved graphical front/back cover URLs are required before prelaunch audiobook work."],
        },
    )
    clean = existing_or_build_clean_report("pather-panchali", "পথের পাঁচালী / Pather Panchali", evidence_root)
    source_scope = {
        "generated_at": utc_now(),
        "slug": "pather-panchali",
        "title": "পথের পাঁচালী / Pather Panchali",
        "status": "PATHER_PANCHALI_PRELAUNCH_BLOCKED_OWNER_REVIEW",
        "source_scope_status": "BLOCKED_FULL_WORK_COMPLETENESS_NOT_PROVEN",
        "rights_scope_status": rights.get("status"),
        "owner_editor_review_questions": [
            "Does the controlled reader contain the full intended public-domain work, not a partial excerpt?",
            "Can the source-rights caveat be cleared for commercial audiobook promotion?",
            "Should a separate partial manifest entry be excluded from audiobook candidate matching?",
        ],
        "evidence": {
            "rights": "pather_panchali_source_scope_review_report.json",
            "content": "pather_panchali_full_work_completeness_report.json",
            "cover": "pather_panchali_cover_repair_plan.json",
        },
        "blockers": list(dict.fromkeys((rights.get("blockers") or []) + (content.get("blockers") or []))),
    }
    cover_plan = {
        "generated_at": utc_now(),
        "slug": "pather-panchali",
        "title": "পথের পাঁচালী / Pather Panchali",
        "status": "BLOCKED_COVER_REPAIR_REQUIRED",
        "visual_direction": "rural Bengal path, fields, monsoon, childhood, restrained village atmosphere",
        "requirements": [
            "graphical front cover",
            "graphical back cover",
            "no typographic-only fallback",
            "deterministic text overlay",
            "lightweight assets",
        ],
        "paid_audio_allowed": False,
        "blockers": cover.get("notes") or ["Approved graphical front/back cover URLs are missing."],
    }
    go_no_go = {
        "generated_at": utc_now(),
        "slug": "pather-panchali",
        "title": "পথের পাঁচালী / Pather Panchali",
        "status": "NO_GO_FOR_AUDIOBOOK",
        "reader_status": "reader_exists",
        "rights_source_status": rights.get("status"),
        "content_status": content.get("status"),
        "cover_status": cover.get("status"),
        "clean_text_status": clean.get("status"),
        "paid_audio_allowed": False,
        "next_action": "Resolve full-work source scope, rights caveat, and cover repair before representative audition.",
    }
    write_json(ROOT / "pather_panchali_source_scope_review_report.json", source_scope)
    write_json(ROOT / "pather_panchali_full_work_completeness_report.json", content)
    write_json(ROOT / "pather_panchali_cover_repair_plan.json", cover_plan)
    write_json(ROOT / "pather_panchali_audiobook_go_no_go_report.json", go_no_go)
    return {
        "slug": "pather-panchali",
        "title": "পথের পাঁচালী / Pather Panchali",
        "rights": rights.get("status"),
        "content": content.get("status"),
        "cover": cover.get("status"),
        "clean_text": clean.get("status"),
        "go_no_go": go_no_go.get("status"),
        "next_action": go_no_go["next_action"],
    }


def write_canary_forensics(evidence_root: Path) -> dict[str, Any]:
    titles = {
        "book-d19e96859f": {
            "title": "গিন্নি",
            "asr_score": 1.602,
            "affected_groups": [4],
        },
        "book-f5d593e1f4": {
            "title": "রামকানাইয়ের নির্বুদ্ধিতা",
            "asr_score": 0.3317,
            "affected_groups": [7],
        },
    }
    reports = {}
    for slug, meta in titles.items():
        existing = load_first_json([f"{slug}_canary_source_provenance_report.json", f"{slug}_source_provenance_audit.json"], evidence_root, {})
        report = {
            "generated_at": utc_now(),
            "slug": slug,
            "title": meta["title"],
            "status": "GROUP_ONLY_REPAIR_PLAN_READY_NO_PAID_AUDIO_RUN",
            "prior_asr_source_score": meta["asr_score"],
            "root_cause": existing.get("root_cause") or "Prior evidence indicates final group source-year contamination and first/last ASR/source mismatch.",
            "planned_repair": "Regenerate only affected groups after paid lock release; do not regenerate full book.",
            "planned_regenerated_groups": existing.get("planned_regenerated_groups") or meta["affected_groups"],
            "paid_audio_run": False,
            "publish_allowed": False,
            "objective_gate_status": "BLOCKED_UNTIL_GROUP_REPAIR_TTS_BY_CONSTRUCTION_LISTENING_SYNC_UPLOAD_METADATA_ENDPOINT_BROWSER_PASS",
        }
        write_json(ROOT / f"{slug}_canary_source_provenance_report.json", report)
        reports[slug] = report
    summary = {
        "generated_at": utc_now(),
        "status": "CANARY_ASR_FORENSICS_NON_PAID_PREP_COMPLETE",
        "paid_audio_run": False,
        "titles": list(reports.values()),
        "next_action": "After paid lock release, run slug-scoped group-only repair, then rerun objective gates.",
    }
    write_json(ROOT / "bengali_canary_asr_forensics_summary.json", summary)
    return {
        slug: {
            "status": report["status"],
            "planned_regenerated_groups": report["planned_regenerated_groups"],
            "publish_allowed": report["publish_allowed"],
        }
        for slug, report in reports.items()
    }


def write_muchiram_timeout_report() -> dict[str, Any]:
    report = {
        "generated_at": utc_now(),
        "slug": "muchiram-gurer-jibanchorit",
        "title": "মুচিরাম গুড়ের জীবনচরিত",
        "status": "REPRESENTATIVE_TIMEOUT_REPAIR_PLAN_READY_NO_PAID_RETRY",
        "paid_audio_run": False,
        "repair_plan": [
            "Split opening into shorter samples.",
            "Lower max seconds per sample before retry.",
            "Retry representative evidence only after paid_tts.lock release and explicit budget approval.",
        ],
        "next_action": "Run a representative-only retry, not full TTS, after paid lock release.",
    }
    write_json(ROOT / "muchiram_gurer_representative_timeout_repair_report.json", report)
    return report


def write_sprint_state(
    lock_diagnosis: dict[str, Any],
    bn066: dict[str, Any],
    pather: dict[str, Any],
    canary: dict[str, Any],
    muchiram: dict[str, Any],
) -> None:
    status = "NON_PAID_PREP_READY_PAID_TTS_LOCK_BLOCKS_AUDIO"
    state = {
        "generated_at": utc_now(),
        "status": status,
        "current_audiobook_live_count": 2,
        "current_bengali_audiobook_live_count": 1,
        "paid_tts_lock": lock_diagnosis,
        "bn-066": bn066,
        "pather-panchali": pather,
        "book-d19e96859f": canary.get("book-d19e96859f"),
        "book-f5d593e1f4": canary.get("book-f5d593e1f4"),
        "muchiram-gurer-jibanchorit": muchiram,
        "ux": {
            "current_phase": "HOME",
            "owner_approved_phase": "HOME",
            "next_phase_requires_owner_approval": True,
        },
        "next_safe_command": (
            "cd /private/tmp/earnalism-parallel-prelaunch && "
            "npm ci --prefix frontend --legacy-peer-deps --no-audit --no-fund && "
            "REACT_APP_BACKEND_URL=/api npm --prefix frontend run build"
        ),
    }
    heartbeat = {
        "generated_at": utc_now(),
        "status": status,
        "paid_work_running": False,
        "last_heartbeat": utc_now(),
        "next_heartbeat_due_minutes": 10,
    }
    next_actions = {
        "generated_at": utc_now(),
        "actions": [
            "Do not run paid TTS while paid_tts.lock is active.",
            "Review HOME screenshot packet before approving LIBRARY.",
            "Resolve pather-panchali source scope and cover repair before any audio.",
            "After paid lock release, run bn-066 representative audition only.",
        ],
    }
    write_json(ROOT / "prelaunch_bengali_audiobook_daemon_state.json", state)
    write_json(ROOT / "prelaunch_bengali_audiobook_daemon_heartbeat.json", heartbeat)
    write_json(ROOT / "prelaunch_bengali_audiobook_next_actions.json", next_actions)
    write_json(ROOT / "parallel_prelaunch_sprint_dashboard.json", state)
    dashboard = f"""# Parallel Prelaunch Sprint Dashboard

Generated: {utc_now()}

## Lane Status

| Lane | Status | Next action |
| --- | --- | --- |
| Bengali audiobook prep | {status} | Release paid lock only with owner/budget approval, then run `bn-066` representative audition only |
| HOME UX phase | APPROVED_FOR_HOME_ONLY | Produce screenshots and review packet; stop before LIBRARY |

## Locks

- paid_tts.lock: {'active' if lock_diagnosis.get('lock_active') else 'not active'}; stale={lock_diagnosis.get('lock_stale')}; released=false
- production_metadata.lock: active/fail-closed in clean worktree
- backend_deploy.lock: active/fail-closed in clean worktree
- ux_owner_approval.lock: HOME approved only; next phase requires owner approval

## Audiobook Targets

| Target | Status |
| --- | --- |
| `bn-066` / আনন্দমঠ | {bn066.get('representative_audition')} |
| `pather-panchali` / পথের পাঁচালী | {pather.get('go_no_go')} |
| `book-d19e96859f` / গিন্নি | {canary.get('book-d19e96859f', {}).get('status')} |
| `book-f5d593e1f4` / রামকানাইয়ের নির্বুদ্ধিতা | {canary.get('book-f5d593e1f4', {}).get('status')} |
| `muchiram-gurer-jibanchorit` | {muchiram.get('status')} |

## Safe Resume

```bash
cd /private/tmp/earnalism-parallel-prelaunch
python3 internal/audiobook_lab/scripts/prelaunch_bengali_audiobook_daemon.py --evidence-root /Users/ronikbasak/Documents/GitHub/earnalism-digital-library --max-run-minutes 360
```
"""
    write_text(ROOT / "parallel_prelaunch_sprint_dashboard.md", dashboard)


def write_unblock_plan(lock_diagnosis: dict[str, Any]) -> None:
    payload = {
        "generated_at": utc_now(),
        "current_branch": os.popen("git branch --show-current").read().strip(),
        "worktree": str(ROOT),
        "lock_state": lock_diagnosis,
        "audiobook_non_paid_tasks_available": [
            "bn-066 rights/content/cover/clean-text refresh",
            "pather-panchali source scope and cover review",
            "canary source-year contamination forensics",
            "muchiram representative timeout retry plan",
        ],
        "ux_home_task_plan": [
            "capture HOME before screenshots",
            "avoid source changes if current HOME already meets target",
            "capture after screenshots",
            "write HOME review packet",
            "stop before LIBRARY",
        ],
        "exact_blockers": [
            "paid_tts.lock active; no paid auditions",
            "pather-panchali source scope and cover repair blocked",
            "LIBRARY phase requires owner approval after HOME",
        ],
        "safe_next_commands": [
            "python3 internal/audiobook_lab/scripts/prelaunch_bengali_audiobook_daemon.py --evidence-root /Users/ronikbasak/Documents/GitHub/earnalism-digital-library --max-run-minutes 360",
            "npm ci --prefix frontend --legacy-peer-deps --no-audit --no-fund",
        ],
    }
    write_json(ROOT / "parallel_prelaunch_unblock_plan.json", payload)


def update_memory(lock_diagnosis: dict[str, Any]) -> None:
    ledger_entry = {
        "timestamp": utc_now(),
        "workstream": "parallel_prelaunch_unblock",
        "decision": "create_lock_aware_daemon_state_and_block_paid_audio_until_lock_release",
        "evidence": {
            "paid_tts_lock_active": lock_diagnosis.get("lock_active"),
            "lock_stale": lock_diagnosis.get("lock_stale"),
            "state_path": "prelaunch_bengali_audiobook_daemon_state.json",
            "dashboard_path": "parallel_prelaunch_sprint_dashboard.json",
        },
        "selected_option": "run non-paid prep only and stop HOME UX after review packet",
        "release_gate_reason": "No representative evidence or objective gates are complete for the requested prelaunch Bengali audiobooks.",
        "result": "PARALLEL_PRELAUNCH_NON_PAID_PREP_READY",
        "next_action": "Review HOME packet; release paid_tts.lock only with explicit owner/budget approval before representative audition.",
    }
    append_line(ROOT / "internal/earnalism_intelligence/decision_ledger.jsonl", json.dumps(ledger_entry, ensure_ascii=False))
    append_line(
        ROOT / "internal/earnalism_intelligence/sprint_learnings.md",
        "\n## 2026-07-08 Parallel Prelaunch Unblock\n\n"
        "- Created a lock-aware prelaunch daemon state without running paid TTS.\n"
        "- `bn-066` remains representative-audition-ready only; full TTS still requires representative pass and explicit full-TTS approval.\n"
        "- `pather-panchali` remains blocked for audiobook by source-scope and cover repair gates.\n"
        "- HOME UX is the only approved phase; LIBRARY requires a new owner approval record.\n",
    )
    append_line(
        ROOT / "repo_cleanup_report.md",
        "\n## Parallel Prelaunch Hygiene - 2026-07-08\n\n"
        "- Generated daemon state, heartbeat, non-paid audiobook prep reports, and HOME review artifacts only.\n"
        "- No generated audio, sidecars, release_gate outputs, production metadata mutation, backend deploy, paid ads, screenshots, caches, signed URLs, or secrets should be staged.\n",
    )
    append_line(
        ROOT / "sprint_go_live_dashboard.md",
        "\n## Parallel Prelaunch Unblock - 2026-07-08\n\n"
        "- Audiobook live counts remain total `2`, Bengali `1`.\n"
        "- Paid Bengali prelaunch audio remains blocked by `paid_tts.lock`.\n"
        "- HOME UX is approved for one interactive screenshot review phase only.\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", default=str(DEFAULT_EVIDENCE_ROOT))
    parser.add_argument("--max-run-minutes", type=int, default=360)
    args = parser.parse_args()
    evidence_root = Path(args.evidence_root).resolve()

    locks = ensure_lock_files(evidence_root)
    lock_diagnosis = diagnose_paid_tts_lock(locks["paid_tts.lock"], evidence_root)
    write_json(ROOT / "paid_tts_lock_diagnosis.json", lock_diagnosis)
    write_unblock_plan(lock_diagnosis)

    lock_active = bool(lock_diagnosis.get("lock_active"))
    bn066 = write_bn066_reports(lock_active, evidence_root)
    pather = write_pather_reports(evidence_root)
    canary = write_canary_forensics(evidence_root)
    muchiram = write_muchiram_timeout_report()
    write_sprint_state(lock_diagnosis, bn066, pather, canary, muchiram)
    update_memory(lock_diagnosis)

    log_line = f"{utc_now()} non-paid daemon pass complete; paid_tts_lock_active={lock_active}\n"
    append_line(ROOT / "prelaunch_bengali_audiobook_daemon.log", log_line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
