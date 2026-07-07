#!/usr/bin/env python3
"""Stateful Bengali audiobook completion campaign controller.

This controller persists campaign state and next actions for the 31 Bengali
reader-only/audio-hidden titles. It does not synthesize, judge, upload, or
publish audio by itself. Paid/provider execution is delegated to guarded
specialized scripts and requires explicit env gates.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
INTEL_DIR = ROOT / "internal" / "earnalism_intelligence"
POLICY_PATH = INTEL_DIR / "bengali_audiobook_campaign_policy.md"
STATE_PATH = INTEL_DIR / "bengali_audiobook_campaign_state.json"
INTERNAL_QUEUE_PATH = INTEL_DIR / "bengali_audiobook_campaign_queue.json"
INTERNAL_LEDGER_PATH = INTEL_DIR / "bengali_audiobook_campaign_ledger.jsonl"
PROMPT_CHAIN_PATH = INTEL_DIR / "autonomous_prompt_chain.jsonl"
PROVIDER_MEMORY_PATH = INTEL_DIR / "provider_performance_memory.json"
TITLE_HISTORY_PATH = INTEL_DIR / "title_decision_history.json"
DECISION_LEDGER_PATH = INTEL_DIR / "decision_ledger.jsonl"
SPRINT_LEARNINGS_PATH = INTEL_DIR / "sprint_learnings.md"

ROOT_QUEUE_PATH = ROOT / "bengali_audiobook_31_campaign_queue.json"
DASHBOARD_PATH = ROOT / "bengali_audiobook_campaign_dashboard.json"
NEXT_ACTIONS_PATH = ROOT / "bengali_audiobook_next_actions.md"
NEXT_PROMPT_PATH = ROOT / "next_best_codex_prompt.md"
PILOT_SELECTION_PATH = ROOT / "bengali_audiobook_pilot_selection_report.json"
REPRESENTATIVE_REPORT_PATH = ROOT / "bengali_representative_audition_report.json"
PILOT_REPORT_PATH = ROOT / "bengali_audiobook_pilot_report.json"

FATAL_FLAGS = [
    "robotic_texture_detected",
    "mechanical_cadence_detected",
    "list_reading_rhythm_detected",
    "choppy_joins_detected",
    "fallback_tts_detected",
]

CAMPAIGN_STATES = [
    "READY_FOR_REPRESENTATIVE_AUDITION",
    "REPRESENTATIVE_AUDITION_RUNNING",
    "REPRESENTATIVE_AUDITION_PASSED",
    "FULL_PILOT_RUNNING",
    "FULL_AUDIO_QA_RUNNING",
    "READY_FOR_UPLOAD",
    "PUBLISHED",
    "NEEDS_HUMAN_NARRATION",
    "NEEDS_LICENSED_AUDIO",
    "EXTERNAL_ACTION_REQUIRED",
]

TERMINAL_STATES = {
    "PUBLISHED",
    "NEEDS_HUMAN_NARRATION",
    "NEEDS_LICENSED_AUDIO",
    "EXTERNAL_ACTION_REQUIRED",
}

TEXT_PREP_VARIANTS = [
    "canonical_clean",
    "punctuation_normalized",
    "literary_pause_control",
    "dialogue_human_touch",
    "anti_list_reading_flow",
    "anti_mechanical_cadence",
    "stanza_paragraph_breathing",
    "emotional_but_restrained",
    "child_voice_avoidance",
    "calm_literary_storyteller",
]


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path, default: Any = None) -> Any:
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def append_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text.rstrip() + "\n")


def bool_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "y", "on"}


def env_gate_status() -> dict[str, Any]:
    required_bool = [
        "EARNALISM_APPROVE_SARVAM_CORRECTIVE_AUDITIONS",
        "EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF",
        "EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS",
        "EARNALISM_APPROVE_BENGALI_31_AUDIO_CAMPAIGN",
        "EARNALISM_STOP_ON_BUDGET_EXCEEDED",
    ]
    required_value = [
        "EARNALISM_BENGALI_CAMPAIGN_MAX_ESTIMATED_USD",
        "EARNALISM_BENGALI_MAX_ESTIMATED_USD_PER_TITLE",
    ]
    bool_status = {name: bool_env(name) for name in required_bool}
    value_status = {name: bool(os.environ.get(name, "").strip()) for name in required_value}
    missing = [name for name, ok in bool_status.items() if not ok] + [name for name, ok in value_status.items() if not ok]
    return {
        "all_required_present": not missing,
        "boolean_gates": bool_status,
        "value_gates_present": value_status,
        "missing": missing,
    }


def load_public_book(slug: str) -> dict[str, Any]:
    return read_json(ROOT / "data" / "controlled_publications" / slug / "public_book.json", {})


def load_manuscript(slug: str) -> str:
    chapters_dir = ROOT / "data" / "controlled_publications" / slug / "chapters"
    parts: list[str] = []
    for chapter_path in sorted(chapters_dir.glob("*.json")):
        payload = read_json(chapter_path, {})
        text = str(payload.get("content") or payload.get("text") or payload.get("body") or "").strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts).strip()


def compact_text_len(text: str) -> int:
    return len(re.sub(r"\s+", " ", text or "").strip())


def estimate_dialogue_density(text: str) -> float:
    if not text:
        return 0.0
    quote_count = sum(text.count(ch) for ch in ['"', "“", "”", "‘", "’", "—"])
    speech_markers = len(re.findall(r"(বলিল|বললেন|বলল|কহিল|কহিলেন|জিজ্ঞাসা|উত্তর)", text))
    return round(min(1.0, (quote_count + speech_markers * 2) / max(1, compact_text_len(text)) * 80), 4)


def estimate_punctuation_complexity(text: str) -> float:
    if not text:
        return 0.0
    punctuation = len(re.findall(r"[।,;:!?—–…\"'“”‘’()]", text))
    return round(min(1.0, punctuation / max(1, compact_text_len(text)) * 10), 4)


def difficulty_label(char_count: int, dialogue_density: float, punctuation_complexity: float) -> str:
    score = 0
    if char_count > 30_000:
        score += 3
    elif char_count > 12_000:
        score += 2
    elif char_count > 6_000:
        score += 1
    if dialogue_density > 0.16:
        score += 2
    elif dialogue_density > 0.08:
        score += 1
    if punctuation_complexity > 0.28:
        score += 2
    elif punctuation_complexity > 0.16:
        score += 1
    if score >= 5:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def setting_key(attempt: dict[str, Any]) -> str:
    """Stable attempt key used to avoid duplicate provider spend."""
    parts = [
        str(attempt.get("provider") or ""),
        str(attempt.get("model") or ""),
        str(attempt.get("voice") or attempt.get("speaker") or ""),
        str(attempt.get("style_profile") or attempt.get("style") or ""),
        str(attempt.get("text_prep_variant") or ""),
        str(attempt.get("postprocess_variant") or ""),
        str(attempt.get("passage_id") or ""),
        str(attempt.get("text_hash") or attempt.get("sample_hash") or ""),
    ]
    return "|".join(parts).lower()


def fatal_flags_in(evidence: dict[str, Any]) -> list[str]:
    red_flags = evidence.get("red_flags") or {}
    found: list[str] = []
    if isinstance(red_flags, dict):
        found.extend(flag for flag in FATAL_FLAGS if red_flags.get(flag))
    elif isinstance(red_flags, list):
        found.extend(flag for flag in FATAL_FLAGS if flag in red_flags)
    found.extend(flag for flag in FATAL_FLAGS if evidence.get(flag))
    return sorted(set(found))


def representative_passes(evidence: dict[str, Any], *, goal_score: float = 9.2) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    score = float(evidence.get("representative_score") or evidence.get("overall_listening_score") or 0.0)
    confidence = float(evidence.get("confidence") or evidence.get("confidence_score") or 0.0)
    flags = fatal_flags_in(evidence)
    if score < goal_score:
        blockers.append(f"representative_score {score} < {goal_score}")
    if confidence < 0.9:
        blockers.append(f"confidence {confidence} < 0.90")
    if flags:
        blockers.append("fatal_flags: " + ",".join(flags))
    for passage in evidence.get("passage_scores") or []:
        passage_score = float(passage.get("overall_listening_score") or 0.0)
        if passage_score and passage_score < 8.9:
            blockers.append(f"passage {passage.get('passage_id') or ''} below 8.9: {passage_score}")
    return not blockers, blockers


def full_audio_publishable(evidence: dict[str, Any], *, goal_score: float = 9.2) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    score = float(evidence.get("full_pilot_listening_score") or evidence.get("listening_score") or 0.0)
    confidence = float(evidence.get("confidence") or evidence.get("confidence_score") or 0.0)
    if score < goal_score:
        blockers.append(f"full_book_listening_score {score} < {goal_score}")
    if confidence < 0.9:
        blockers.append(f"confidence {confidence} < 0.90")
    flags = fatal_flags_in(evidence)
    if flags:
        blockers.append("fatal_flags: " + ",".join(flags))
    if float(evidence.get("asr_score") or 0.0) < 9.7:
        blockers.append("asr_manuscript_match < 9.7")
    if evidence.get("auto_estimated_sync") is True:
        blockers.append("auto_estimated_sync=true")
    sync_tier = str(evidence.get("sync_tier") or "").lower()
    if sync_tier and "estimated" in sync_tier:
        blockers.append("sync_tier is estimated")
    for gate in ["upload_checksum_status", "metadata_status", "browser_status"]:
        if str(evidence.get(gate) or "").upper() not in {"PASS", "PASSED"}:
            blockers.append(f"{gate} not PASS")
    if evidence.get("blocker_list"):
        blockers.append("blocker_list not empty")
    return not blockers, blockers


def plateau_detected(attempts: list[dict[str, Any]]) -> tuple[bool, str]:
    material = [attempt for attempt in attempts if attempt.get("provider") and attempt.get("voice")]
    if len({setting_key(attempt) for attempt in material}) < 3:
        return False, "fewer_than_three_material_attempts"
    scores = [float(attempt.get("representative_score") or attempt.get("overall_listening_score") or 0.0) for attempt in material]
    fatal_count = sum(1 for attempt in material if fatal_flags_in(attempt))
    improvement = max(scores or [0.0]) - min(scores or [0.0])
    if fatal_count >= 2:
        return True, "repeated_fatal_red_flags"
    if max(scores or [0.0]) < 8.8:
        return True, "all_material_attempts_below_8_8"
    if len(material) >= 3 and improvement < 0.2:
        return True, "three_material_attempts_plateau_below_0_2_improvement"
    return False, "improvement_or_attempt_count_not_plateau"


def scale_allowed(state: dict[str, Any]) -> tuple[bool, str]:
    if int(state.get("published_bengali_audiobooks") or 0) < 1:
        return False, "one_full_pilot_must_publish_before_canary"
    if state.get("systemic_failure_detected"):
        return False, "systemic_failure_detected"
    return True, "pilot_live"


def load_representative_report() -> dict[str, Any]:
    return read_json(REPRESENTATIVE_REPORT_PATH, {})


def tested_setting_cache(report: dict[str, Any]) -> dict[str, Any]:
    scores = report.get("passage_scores") if isinstance(report.get("passage_scores"), list) else []
    cache: dict[str, Any] = {}
    for passage in scores:
        key = setting_key(passage)
        if key:
            cache[key] = {
                "provider": passage.get("provider"),
                "model": passage.get("model"),
                "voice": passage.get("voice"),
                "style_profile": passage.get("style_profile"),
                "passage_id": passage.get("passage_id"),
                "status": passage.get("status"),
                "score": passage.get("overall_listening_score"),
                "confidence": passage.get("confidence_score"),
                "fatal_flags": fatal_flags_in(passage),
            }
    return cache


def title_record_from_candidate(row: dict[str, Any], rank: int, passed_slug: str, report: dict[str, Any]) -> dict[str, Any]:
    slug = str(row.get("slug") or "").strip()
    public_book = load_public_book(slug)
    text = load_manuscript(slug)
    char_count = int(row.get("manuscript_char_count") or compact_text_len(text))
    dialogue = estimate_dialogue_density(text)
    punctuation = estimate_punctuation_complexity(text)
    is_pilot_ready = bool(slug and slug == passed_slug and report.get("representative_passed_9_2"))
    state = "REPRESENTATIVE_AUDITION_PASSED" if is_pilot_ready else "READY_FOR_REPRESENTATIVE_AUDITION"
    best_settings = None
    if is_pilot_ready:
        best_settings = {
            "provider": report.get("provider"),
            "model": report.get("model"),
            "voice": report.get("voice"),
            "style_profile": report.get("best_style_profile"),
            "representative_score": report.get("representative_score"),
            "confidence": report.get("confidence"),
        }
    next_action = (
        "Run exactly one guarded full-pilot TTS/ASR/sync/upload/metadata/browser path; do not scale until it publishes."
        if is_pilot_ready
        else "Await pilot result; then run adaptive representative audition if pilot proves the path."
    )
    return {
        "slug": slug,
        "title": row.get("title") or public_book.get("title") or public_book.get("name") or slug,
        "author": row.get("author") or public_book.get("author") or "",
        "language": row.get("language") or public_book.get("language") or "ben",
        "content_length": char_count,
        "difficulty_estimate": difficulty_label(char_count, dialogue, punctuation),
        "dialogue_density": dialogue,
        "punctuation_complexity": punctuation,
        "rights_status": row.get("rights_status") or "UNKNOWN",
        "cover_status": row.get("cover_status") or "UNKNOWN",
        "reader_route_status": row.get("reader_route_status") or "UNKNOWN",
        "prior_audio_status": "reader_only_audio_hidden",
        "known_blockers": [],
        "candidate_rank": int(row.get("rank") or rank),
        "selected_strategy": "sarvam_bulbul_v3_ratan_literary_warm_pacing_full_pilot" if is_pilot_ready else "adaptive_sarvam_after_pilot",
        "current_campaign_state": state,
        "best_representative_settings": best_settings,
        "next_action": next_action,
    }


def load_campaign_queue() -> list[dict[str, Any]]:
    selection = read_json(PILOT_SELECTION_PATH, {})
    rows = selection.get("ranked_candidates") if isinstance(selection.get("ranked_candidates"), list) else []
    report = load_representative_report()
    passed_slug = str(report.get("pilot_candidate_selected") or "")
    queue = [title_record_from_candidate(row, index + 1, passed_slug, report) for index, row in enumerate(rows)]
    if len(queue) != 31:
        history = read_json(TITLE_HISTORY_PATH, {})
        titles = history.get("titles") if isinstance(history.get("titles"), dict) else {}
        fallback_rows: list[dict[str, Any]] = []
        for slug, decision in titles.items():
            if str(decision.get("language") or "").lower() in {"bn", "ben", "bengali"} and "READER" in str(decision.get("latest_decision") or ""):
                fallback_rows.append({"slug": slug, "language": "ben", "rank": len(fallback_rows) + 1})
        queue = [title_record_from_candidate(row, index + 1, passed_slug, report) for index, row in enumerate(fallback_rows[:31])]
    return queue


def campaign_summary(queue: list[dict[str, Any]], report: dict[str, Any]) -> dict[str, Any]:
    counts = Counter(item.get("current_campaign_state") for item in queue)
    representative_passed = [item for item in queue if item.get("current_campaign_state") == "REPRESENTATIVE_AUDITION_PASSED"]
    published = [item for item in queue if item.get("current_campaign_state") == "PUBLISHED"]
    human = [item for item in queue if item.get("current_campaign_state") == "NEEDS_HUMAN_NARRATION"]
    licensed = [item for item in queue if item.get("current_campaign_state") == "NEEDS_LICENSED_AUDIO"]
    gate_status = env_gate_status()
    return {
        "generated_at": iso_now(),
        "status": "BENGALI_AUDIOBOOK_CAMPAIGN_ACTIVE",
        "policy_version": "bengali_audiobook_acceptance_v2_92",
        "total_campaign_titles": len(queue),
        "published_bengali_audiobooks": len(published),
        "titles_in_representative_audition": counts.get("REPRESENTATIVE_AUDITION_RUNNING", 0),
        "titles_with_representative_gte_9_2": len(representative_passed),
        "titles_in_full_pilot": counts.get("FULL_PILOT_RUNNING", 0),
        "titles_needing_human_narration": len(human),
        "titles_needing_licensed_audio": len(licensed),
        "state_counts": dict(counts),
        "best_settings": {
            "provider": report.get("provider"),
            "model": report.get("model"),
            "voice": report.get("voice"),
            "style_profile": report.get("best_style_profile"),
            "representative_score": report.get("representative_score"),
            "confidence": report.get("confidence"),
        },
        "full_pilot_score": None,
        "asr_score": None,
        "sync_tier": None,
        "estimated_campaign_cost_policy": {
            "campaign_max_env_present": gate_status["value_gates_present"].get("EARNALISM_BENGALI_CAMPAIGN_MAX_ESTIMATED_USD", False),
            "per_title_max_env_present": gate_status["value_gates_present"].get("EARNALISM_BENGALI_MAX_ESTIMATED_USD_PER_TITLE", False),
            "default_recommended_campaign_cap_usd": 75,
            "default_recommended_per_title_cap_usd": 8,
        },
        "paid_gate_status": gate_status,
        "duplicate_attempts_avoided": len(tested_setting_cache(report)),
        "plateau_strategies_triggered": 0,
        "campaign_dashboard_path": str(DASHBOARD_PATH.relative_to(ROOT)),
        "campaign_queue_path": str(ROOT_QUEUE_PATH.relative_to(ROOT)),
        "next_best_codex_prompt_path": str(NEXT_PROMPT_PATH.relative_to(ROOT)),
    }


def exact_next_command() -> str:
    return (
        "railway run --project a8533934-35c4-463e-9f43-577a9ac391ee "
        "--service 5af42e7e-f518-4f6a-b602-d9950866501f "
        "--environment 580b250c-80ee-48ad-bfbe-fa4e31a6b378 -- "
        "env EARNALISM_APPROVE_SARVAM_CORRECTIVE_AUDITIONS=true "
        "EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF=true "
        "EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS=true "
        "EARNALISM_APPROVE_BENGALI_31_AUDIO_CAMPAIGN=true "
        "EARNALISM_BENGALI_CAMPAIGN_MAX_ESTIMATED_USD=75 "
        "EARNALISM_BENGALI_MAX_ESTIMATED_USD_PER_TITLE=8 "
        "EARNALISM_STOP_ON_BUDGET_EXCEEDED=true "
        "EARNALISM_ENABLE_OPENAI_LISTENING_QA=true "
        "EARNALISM_OPENAI_LISTENING_QA_MODEL=gpt-audio "
        "EARNALISM_LISTENING_POLICY_VERSION=bengali_audiobook_acceptance_v2_92 "
        "python3 internal/audiobook_lab/scripts/bengali_audiobook_campaign_controller.py "
        "--manifest book_import_manifest.json --target-reader-only-approved-31 "
        "--goal-score 9.2 --policy bengali_audiobook_acceptance_v2_92 "
        "--adaptive-optimizer --resume --fail-closed --max-run-minutes 180"
    )


def write_next_actions(summary: dict[str, Any], queue: list[dict[str, Any]]) -> None:
    pilot = next((item for item in queue if item.get("current_campaign_state") == "REPRESENTATIVE_AUDITION_PASSED"), None)
    lines = [
        "# Bengali Audiobook Campaign Next Actions",
        "",
        f"Status: `{summary['status']}`",
        f"Policy: `{summary['policy_version']}`",
        f"Campaign titles: `{summary['total_campaign_titles']}`",
        f"Published Bengali audiobooks: `{summary['published_bengali_audiobooks']}`",
        f"Representative-passed titles: `{summary['titles_with_representative_gte_9_2']}`",
        "",
        "## Immediate Next Step",
        "",
    ]
    if pilot:
        lines.extend(
            [
                f"Run exactly one guarded full pilot for `{pilot['slug']}` (`{pilot['title']}`) using Sarvam `bulbul:v3` / `ratan` / `literary_warm_pacing`.",
                "",
                "Do not start the 3-title canary until that pilot passes full-book listening, ASR/manuscript, measured sync, upload/checksum, metadata, endpoint, and browser gates.",
            ]
        )
    else:
        lines.append("Run adaptive representative auditions for the shortest eligible title.")
    lines.extend(["", "## Exact Command", "", "```bash", exact_next_command(), "```", ""])
    NEXT_ACTIONS_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_next_prompt(summary: dict[str, Any], queue: list[dict[str, Any]]) -> None:
    pilot = next((item for item in queue if item.get("current_campaign_state") == "REPRESENTATIVE_AUDITION_PASSED"), None)
    prompt = f"""You are the Earnalism Bengali Audiobook Campaign Governor.

Continue from the persistent campaign state:

- State: {STATE_PATH.relative_to(ROOT)}
- Queue: {INTERNAL_QUEUE_PATH.relative_to(ROOT)}
- Dashboard: {DASHBOARD_PATH.relative_to(ROOT)}
- Policy: {POLICY_PATH.relative_to(ROOT)}

Current state:

- Total campaign titles: {summary['total_campaign_titles']}
- Published Bengali audiobooks: {summary['published_bengali_audiobooks']}
- Titles with representative >=9.2: {summary['titles_with_representative_gte_9_2']}
- Full pilot generated: false
- Best setting: Sarvam bulbul:v3 / ratan / literary_warm_pacing, representative score 9.3, confidence 0.95.

Next action:

Run exactly one guarded full pilot for {pilot['slug'] if pilot else 'the current top candidate'} and do not start a wave until it passes all objective gates.

Hard rules:

- Do not publish below 9.2.
- Do not publish fatal red-flag audio.
- Do not publish estimated sync.
- Do not damage Bengali reader-only/audio-hidden state.
- Do not repeat failed provider/settings/text hashes.
- Persist every result in the campaign ledger and title history.

Next exact command:

```bash
{exact_next_command()}
```
"""
    NEXT_PROMPT_PATH.write_text(prompt, encoding="utf-8")


def update_provider_memory(summary: dict[str, Any]) -> None:
    memory = read_json(PROVIDER_MEMORY_PATH, {"version": "2026-07-06"})
    bengali = memory.setdefault("bengali", {})
    bengali["audiobook_completion_campaign"] = {
        "status": summary["status"],
        "policy_version": summary["policy_version"],
        "total_campaign_titles": summary["total_campaign_titles"],
        "published_bengali_audiobooks": summary["published_bengali_audiobooks"],
        "titles_with_representative_gte_9_2": summary["titles_with_representative_gte_9_2"],
        "best_settings": summary["best_settings"],
        "scale_rule": "one full pilot must publish before 3-title canary",
        "updated_at": summary["generated_at"],
        "state_path": str(STATE_PATH.relative_to(ROOT)),
        "queue_path": str(INTERNAL_QUEUE_PATH.relative_to(ROOT)),
    }
    write_json(PROVIDER_MEMORY_PATH, memory)


def update_title_history(queue: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    history = read_json(TITLE_HISTORY_PATH, {"version": "2026-07-06", "titles": {}})
    titles = history.setdefault("titles", {})
    for item in queue:
        slug = item["slug"]
        title_state = titles.setdefault(slug, {})
        title_state["language"] = item.get("language", "ben")
        title_state["bengali_audiobook_campaign_state"] = item["current_campaign_state"]
        title_state["bengali_audiobook_campaign_next_action"] = item["next_action"]
        title_state["bengali_audiobook_policy"] = summary["policy_version"]
        title_state["bengali_audiobook_release_gate"] = "not_approved_until_full_objective_gates_pass"
        title_state["updated_at"] = summary["generated_at"]
    history["bengali_audiobook_campaign_status"] = summary["status"]
    history["bengali_audiobook_campaign_updated_at"] = summary["generated_at"]
    write_json(TITLE_HISTORY_PATH, history)


def write_ledgers(summary: dict[str, Any]) -> None:
    payload = {
        "timestamp": summary["generated_at"],
        "workstream": "bengali_audiobook_campaign",
        "decision": "activate_persistent_resumable_campaign_without_paid_provider_calls",
        "evidence": {
            "representative_score": summary["best_settings"].get("representative_score"),
            "confidence": summary["best_settings"].get("confidence"),
            "queue_path": str(ROOT_QUEUE_PATH.relative_to(ROOT)),
            "dashboard_path": str(DASHBOARD_PATH.relative_to(ROOT)),
        },
        "business_reason": "Progress Bengali audiobook monetization safely after one representative 9.2 pass while preventing broad duplicate spend.",
        "customer_experience_reason": "Keeps reader-only live/audio-hidden until full audio and objective gates pass.",
        "cost_reason": "State/controller/report generation only; no provider, TTS, ASR, upload, metadata, or browser calls.",
        "risk": "Full-pilot tooling and objective gates remain unproven.",
        "result": summary["status"],
        "next_action": exact_next_command(),
    }
    append_jsonl(INTERNAL_LEDGER_PATH, payload)
    append_jsonl(DECISION_LEDGER_PATH, payload)
    append_jsonl(
        PROMPT_CHAIN_PATH,
        {
            "cycle_number": "bengali_audiobook_campaign_activation",
            "timestamp": summary["generated_at"],
            "chosen_workstream": "bengali_audiobook_campaign",
            "blocker": "need persistent 31-title campaign state after one representative audition pass",
            "options_considered": ["run paid campaign immediately", "write resumable controller/state first"],
            "selected_action": "write resumable controller/state first",
            "rejected_actions": ["broad 31-title wave", "duplicate Sarvam auditions", "production metadata mutation"],
            "reason": "campaign requires durable memory and duplicate-attempt prevention before more spend",
            "expected_impact": "safe continuation to one guarded full pilot",
            "cost_risk": "no paid calls",
            "validation_result": "state and queue written",
            "next_prompt_action": exact_next_command(),
        },
    )


def update_sprint_learnings(summary: dict[str, Any]) -> None:
    append_markdown(
        SPRINT_LEARNINGS_PATH,
        f"""
## Bengali Audiobook Campaign Activation - {summary['generated_at']}

- Installed persistent Bengali audiobook campaign state and queue for 31 reader-ready titles.
- One title is representative-passed under `bengali_audiobook_acceptance_v2_92`: Sarvam `bulbul:v3` / `ratan` / `literary_warm_pacing`, score `{summary['best_settings'].get('representative_score')}`, confidence `{summary['best_settings'].get('confidence')}`.
- Full pilot is not live and must not be published until full-book listening, ASR/manuscript, measured sync, upload/checksum, metadata, endpoint, and browser gates pass.
- Duplicate attempt cache contains `{summary['duplicate_attempts_avoided']}` prior passage/settings entries.
- No paid/provider/ASR/upload/metadata/production mutation calls were run in this activation.
""",
    )


def create_human_narration_packet(slug: str, out_dir: Path | None = None) -> Path:
    base = out_dir or ROOT / "human_narration_packet" / slug
    public_book = load_public_book(slug)
    manuscript = load_manuscript(slug)
    base.mkdir(parents=True, exist_ok=True)
    (base / "clean_manuscript.txt").write_text(manuscript, encoding="utf-8")
    (base / "narrator_brief.md").write_text(
        "\n".join(
            [
                f"# Human Narration Brief: {public_book.get('title') or slug}",
                "",
                "Goal: Bengali literary narration that sounds human, calm, premium, and non-mechanical.",
                "",
                "Required audio specs:",
                "- deliver clean mono/stereo WAV or high-bitrate MP3",
                "- preserve all manuscript words",
                "- no music or sound effects",
                "- no page numbers, metadata, or frontmatter",
                "- natural paragraph/stanza pauses",
                "",
                "QA rubric:",
                "- listening score >=9.2",
                "- ASR/manuscript match >=9.7",
                "- measured paragraph/stanza sync",
            ]
        ),
        encoding="utf-8",
    )
    write_json(
        base / "metadata.json",
        {
            "slug": slug,
            "title": public_book.get("title") or public_book.get("name") or slug,
            "author": public_book.get("author") or "",
            "language": public_book.get("language") or "ben",
            "estimated_characters": compact_text_len(manuscript),
            "state": "HUMAN_NARRATION_REQUIRED",
        },
    )
    return base


def create_licensed_audio_import_packet(slug: str, out_dir: Path | None = None) -> Path:
    base = out_dir or ROOT / "licensed_audio_import_packet" / slug
    public_book = load_public_book(slug)
    base.mkdir(parents=True, exist_ok=True)
    (base / "audio_import_requirements.md").write_text(
        "\n".join(
            [
                f"# Licensed Audio Import Requirements: {public_book.get('title') or slug}",
                "",
                "- Confirm license permits Earnalism commercial distribution.",
                "- Preserve provenance, rights holder, source, and allowed territories.",
                "- Import only clean, complete audio matching the approved manuscript.",
                "- Validate checksum, ASR/manuscript >=9.7, first/last words, measured sync, metadata, endpoint, and browser gate.",
                "- Do not expose audio before every gate passes.",
            ]
        ),
        encoding="utf-8",
    )
    write_json(
        base / "metadata.json",
        {
            "slug": slug,
            "title": public_book.get("title") or public_book.get("name") or slug,
            "author": public_book.get("author") or "",
            "language": public_book.get("language") or "ben",
            "state": "LICENSED_AUDIO_IMPORT_REQUIRED",
        },
    )
    return base


def write_all_outputs(args: argparse.Namespace) -> dict[str, Any]:
    report = load_representative_report()
    queue = load_campaign_queue()
    summary = campaign_summary(queue, report)
    summary["controller_args"] = vars(args)
    summary["text_prep_variants"] = TEXT_PREP_VARIANTS
    summary["release_gates"] = {
        "goal_score": float(args.goal_score),
        "confidence_min": 0.9,
        "asr_manuscript_min": 9.7,
        "sync": "measured paragraph/stanza or better; estimated sync blocked",
        "fatal_flags": FATAL_FLAGS,
    }
    summary["next_exact_command"] = exact_next_command()

    queue_payload = {
        "generated_at": summary["generated_at"],
        "policy_version": summary["policy_version"],
        "total_titles": len(queue),
        "source": str(PILOT_SELECTION_PATH.relative_to(ROOT)),
        "titles": queue,
    }
    write_json(INTERNAL_QUEUE_PATH, queue_payload)
    write_json(ROOT_QUEUE_PATH, queue_payload)
    write_json(STATE_PATH, summary)
    write_json(DASHBOARD_PATH, summary)
    write_next_actions(summary, queue)
    write_next_prompt(summary, queue)
    update_provider_memory(summary)
    update_title_history(queue, summary)
    write_ledgers(summary)
    update_sprint_learnings(summary)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="book_import_manifest.json")
    parser.add_argument("--target-reader-only-approved-31", action="store_true")
    parser.add_argument("--goal-score", type=float, default=9.2)
    parser.add_argument("--policy", default="bengali_audiobook_acceptance_v2_92")
    parser.add_argument("--adaptive-optimizer", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--fail-closed", action="store_true")
    parser.add_argument("--max-run-minutes", type=int, default=180)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.policy != "bengali_audiobook_acceptance_v2_92" and args.fail_closed:
        print(json.dumps({"status": "FAILED", "blocker": "unsupported_policy", "policy": args.policy}, ensure_ascii=False))
        return 2
    if not PILOT_SELECTION_PATH.exists() and args.fail_closed:
        print(json.dumps({"status": "FAILED", "blocker": "missing_31_title_selection_report"}, ensure_ascii=False))
        return 2
    summary = write_all_outputs(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
