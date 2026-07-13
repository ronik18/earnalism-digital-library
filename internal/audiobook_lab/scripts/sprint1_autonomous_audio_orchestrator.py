#!/usr/bin/env python3
"""Fail-closed coordinator for serialized Sprint 1 audiobook work.

The coordinator plans all titles, binds owner-approved caps into child
processes, and can execute one allow-listed Google English audition at a time.
Publication remains a separate evidence-gated operation.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, Mapping, Sequence


OWNER_DECISION = (
    "AUTHORIZE_AUTONOMOUS_SPRINT1_AUDIO_PUBLICATION_WITH_"
    "SELF_GOVERNING_DECISION_TREE_AND_175_USD_CAP"
)

FIXED_PAID_ENV = {
    "SPRINT1_TOTAL_AUDIO_BUDGET_USD": "175",
    "SPRINT1_MAX_USD_PER_TITLE": "30",
    "MAX_TTS_BUDGET_USD": "175",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
    "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "20",
    "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
    "EARNALISM_ENABLE_OPENAI_LISTENING_QA": "true",
    "EARNALISM_OPENAI_LISTENING_QA_MODEL": "gpt-audio",
    "EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD": "40",
    "EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD": "20",
    "EARNALISM_ASR_SYNC_ESTIMATED_USD_PER_MINUTE": "0.008",
    "EARNALISM_APPROVE_GOOGLE_TTS_AUDITIONS": "true",
    "EARNALISM_GOOGLE_TTS_MAX_ESTIMATED_USD": "40",
    "EARNALISM_GOOGLE_TTS_ESTIMATED_USD_PER_1K_CHARS": "0.02",
    "EARNALISM_APPROVE_SARVAM_CORRECTIVE_AUDITIONS": "true",
    "EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF": "true",
    "EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS": "true",
}

LANES = {
    "approved_audio_guard": ["book-2b9853ec52", "a-ghost-story"],
    "short_bengali": [
        "book-f5d593e1f4",
        "muchiram-gurer-jibanchorit",
        "radharani",
        "nishkriti",
        "book-d19e96859f",
    ],
    "short_english": [
        "the-gift-of-the-magi",
        "the-tell-tale-heart",
        "sredni-vashtar",
        "the-cop-and-the-anthem",
        "the-last-leaf",
        "the-masque-of-the-red-death",
        "the-yellow-wallpaper",
        "the-monkeys-paw",
        "the-necklace",
        "dsires-baby",
        "the-open-window",
    ],
    "medium_long_english": [
        "jekyll-and-hyde",
        "alices-adventures-in-wonderland",
        "the-time-machine",
        "the-call-of-the-wild",
        "white-fang",
        "frankenstein",
        "picture-of-dorian-gray",
        "the-secret-garden",
        "pride-and-prejudice",
        "dracula",
    ],
    "bengali_long_repair": [
        "bn-066",
        "devdas",
        "book-edfcf810c5",
        "pather-panchali",
    ],
}

LONG_ENGLISH_SLUGS = frozenset(LANES["medium_long_english"])
FRESH_SHORT_ENGLISH_SLUGS = (
    "the-cop-and-the-anthem",
    "the-last-leaf",
    "the-masque-of-the-red-death",
    "the-necklace",
    "the-monkeys-paw",
    "the-yellow-wallpaper",
)
HUMAN_TRACK_STATUSES = frozenset(
    {
        "HUMAN_NARRATION_OR_ALTERNATE_PROVIDER_REQUIRED",
        "HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED",
        "SOURCE_BOUND_HUMAN_NARRATION_OR_LICENSED_AUDIO_REQUIRED",
    }
)
PUBLIC_APPROVED_STATES = frozenset(
    {
        "PUBLIC_AUDIO_APPROVED",
        "Yes, publicly rendered book + Yes, publicly available audiobook",
        "YES+YES",
    }
)


class OrchestratorError(RuntimeError):
    """Raised when a fail-closed coordinator invariant is violated."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise OrchestratorError(f"Expected a JSON object: {path}")
    return data


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def credential_snapshot(env: Mapping[str, str]) -> dict[str, Any]:
    google_credentials = env.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    google_project = env.get("GOOGLE_CLOUD_PROJECT", "")
    google_file_ready = bool(
        google_credentials and Path(google_credentials).expanduser().is_file()
    )
    providers = {
        "google": {
            "available": bool(google_file_ready and google_project),
            "credential_file": "SET_AND_READABLE" if google_file_ready else "MISSING_OR_UNREADABLE",
            "project": "SET" if google_project else "MISSING",
        },
        "openai": {"available": bool(env.get("OPENAI_API_KEY")), "key": "SET" if env.get("OPENAI_API_KEY") else "MISSING"},
        "sarvam": {"available": bool(env.get("SARVAM_API_KEY")), "key": "SET" if env.get("SARVAM_API_KEY") else "MISSING"},
    }
    return {
        "fixed_caps": dict(FIXED_PAID_ENV),
        "fixed_caps_source": "OWNER_AUTHORIZED_AND_BOUND_INLINE_BY_ORCHESTRATOR",
        "providers": providers,
        "any_tts_provider_available": providers["google"]["available"] or providers["sarvam"]["available"],
        "qa_provider_available": providers["openai"]["available"],
        "secrets_printed": False,
    }


def validate_paid_runtime(snapshot: Mapping[str, Any], provider: str) -> None:
    providers = snapshot.get("providers", {})
    provider_state = providers.get(provider, {})
    if not provider_state.get("available"):
        raise OrchestratorError(f"{provider.upper()}_PROVIDER_CREDENTIALS_UNAVAILABLE")
    if not providers.get("openai", {}).get("available"):
        raise OrchestratorError("OPENAI_QA_CREDENTIALS_UNAVAILABLE")


def lock_snapshot(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    state = payload.get("state") if isinstance(payload.get("state"), dict) else payload
    status = state.get("status")
    active = state.get("active")
    holder = state.get("current_holder")
    allowed = state.get("allowed_next_holders")
    active_state = active is True or status == "active"
    empty_holder = holder is None or holder == "none"
    available = active_state and empty_holder and allowed == []
    return {
        "path": str(path),
        "status": status,
        "active": active_state,
        "current_holder": holder,
        "allowed_next_holders": allowed,
        "available": available,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def validate_lock(snapshot: Mapping[str, Any]) -> None:
    if not snapshot.get("available"):
        raise OrchestratorError("PAID_TTS_LOCK_UNAVAILABLE_OR_NOT_FAIL_CLOSED")


def ledger_checkpoint(ledger: Mapping[str, Any]) -> float:
    accounting = ledger.get("accounting", {})
    for key in (
        "cumulative_conservative_estimated_spend_usd",
        "estimated_sprint_spend_usd",
        "checkpoint_estimated_spend_usd",
        "estimated_cumulative_spend_usd",
    ):
        value = accounting.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    entries = ledger.get("entries", [])
    amounts = [
        float(entry["estimated_usd"])
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("estimated_usd"), (int, float))
    ]
    return round(sum(amounts), 6)


def title_cost_map(cost_report: Mapping[str, Any]) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for row in cost_report.get("titles", []):
        if not isinstance(row, dict) or not row.get("slug"):
            continue
        value = row.get("estimated_total_cost_usd")
        if not isinstance(value, (int, float)):
            value = row.get("estimated_incremental_cost_usd")
        result[str(row["slug"])] = float(value) if isinstance(value, (int, float)) else None
    return result


def row_estimated_cost(row: Mapping[str, Any], costs: Mapping[str, float | None]) -> float | None:
    value = row.get("estimated_incremental_cost_usd")
    if isinstance(value, (int, float)):
        return float(value)
    return costs.get(str(row.get("slug", "")))


def is_public_approved(row: Mapping[str, Any]) -> bool:
    return (
        row.get("publicly_available_audiobook") == "Yes"
        and (
            row.get("public_audio_status") in PUBLIC_APPROVED_STATES
            or row.get("final_status") in PUBLIC_APPROVED_STATES
        )
    )


def title_decision(
    row: Mapping[str, Any],
    providers: Mapping[str, Any],
    new_short_yes_yes: int,
) -> dict[str, Any]:
    slug = str(row.get("slug", ""))
    status = str(row.get("final_status", ""))
    language = str(row.get("language", ""))
    blocker = str(row.get("exact_blocker", ""))

    if is_public_approved(row):
        return {"state": "VALIDATE_APPROVED_AND_SKIP", "paid_ready": False}
    if not row.get("sprint1_audio_target", True):
        return {"state": "DEFERRED_OUTSIDE_ACTIVE_SPRINT", "paid_ready": False}
    if row.get("publicly_rendered_book") != "Yes":
        return {"state": "PUBLIC_READER_REPAIR_REQUIRED", "paid_ready": False}
    if row.get("rights_status") not in (None, "PASS"):
        return {
            "state": "OWNER_DOCUMENT_REQUIRED",
            "paid_ready": False,
            "blocker": blocker or "SOURCE_RIGHTS_NOT_PASS",
        }
    if row.get("sanitation_status") not in (None, "PASS"):
        return {"state": "TEXT_SANITATION_REPAIR_REQUIRED", "paid_ready": False}
    if status in HUMAN_TRACK_STATUSES or slug in {
        "book-d19e96859f",
        "the-open-window",
        "the-gift-of-the-magi",
        "the-tell-tale-heart",
        "sredni-vashtar",
    }:
        return {
            "state": "HUMAN_NARRATION_OR_LICENSED_AUDIO_TRACK",
            "paid_ready": False,
            "next_command": row.get("next_command"),
        }
    if slug == "bn-066":
        return {"state": "NON_PAID_ASR_LANGUAGE_CALIBRATION", "paid_ready": False}
    if slug in LONG_ENGLISH_SLUGS and new_short_yes_yes < 5:
        return {
            "state": "WAITING_FOR_FIVE_NEW_SHORT_YES_YES",
            "paid_ready": False,
        }
    if slug == "dsires-baby":
        return {
            "state": "GOOGLE_ENGLISH_ALTERNATE_AUDITION",
            "paid_ready": bool(providers.get("google", {}).get("available")),
            "provider": "google",
            "voice": "en-GB-Chirp3-HD-Achird",
            "speaking_rate": 0.90,
            "attempt_rule": "ONE_MATERIALLY_DIFFERENT_VOICE_THEN_HUMAN_IMPORT",
        }
    if language == "English" and slug in FRESH_SHORT_ENGLISH_SLUGS:
        return {
            "state": "GOOGLE_ENGLISH_REPRESENTATIVE_AUDITION",
            "paid_ready": bool(providers.get("google", {}).get("available")),
            "provider": "google",
            "voice": "en-GB-Studio-C",
            "speaking_rate": 0.94,
            "attempt_rule": "ONE_PRIMARY_FAMILY_THEN_ONE_MATERIAL_ALTERNATE",
        }
    if language == "Bengali":
        return {
            "state": "BENGALI_NON_PAID_PREFLIGHT_OR_CALIBRATION",
            "paid_ready": False,
        }
    if language == "English":
        return {
            "state": "ENGLISH_NON_PAID_PREFLIGHT",
            "paid_ready": False,
        }
    return {"state": "MANUAL_EVIDENCE_CLASSIFICATION_REQUIRED", "paid_ready": False}


def chance_per_dollar(slug: str, decision: Mapping[str, Any], estimated_cost: float | None) -> float:
    if not decision.get("paid_ready") or not estimated_cost or estimated_cost <= 0:
        return 0.0
    if slug == "dsires-baby":
        chance = 0.45
    elif slug in FRESH_SHORT_ENGLISH_SLUGS:
        chance = 0.82
    else:
        chance = 0.55
    return round(chance / estimated_cost, 6)


def build_board(
    matrix: Mapping[str, Any],
    cost_report: Mapping[str, Any],
    ledger: Mapping[str, Any],
    runtime: Mapping[str, Any],
    lock: Mapping[str, Any],
) -> dict[str, Any]:
    rows = [row for row in matrix.get("titles", []) if isinstance(row, dict)]
    active_rows = [row for row in rows if row.get("sprint1_audio_target", True)]
    approved = [row for row in active_rows if is_public_approved(row)]
    new_short_yes_yes = max(0, len(approved) - 2)
    costs = title_cost_map(cost_report)
    decisions = []
    for row in active_rows:
        decision = title_decision(row, runtime.get("providers", {}), new_short_yes_yes)
        estimated_cost = row_estimated_cost(row, costs)
        decisions.append(
            {
                "slug": row.get("slug"),
                "title": row.get("title"),
                "language": row.get("language"),
                "current_public_reader": row.get("publicly_rendered_book"),
                "current_public_audio": row.get("publicly_available_audiobook"),
                "current_status": row.get("final_status"),
                "estimated_lifecycle_cost_usd": estimated_cost,
                "decision": decision,
                "chance_per_dollar": chance_per_dollar(str(row.get("slug", "")), decision, estimated_cost),
            }
        )
    paid_queue = sorted(
        (item for item in decisions if item["decision"].get("paid_ready")),
        key=lambda item: (-item["chance_per_dollar"], item["estimated_lifecycle_cost_usd"] or 10**9, item["slug"]),
    )
    checkpoint = ledger_checkpoint(ledger)
    cap = float(FIXED_PAID_ENV["SPRINT1_TOTAL_AUDIO_BUDGET_USD"])
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "owner_decision": OWNER_DECISION,
        "execution_model": {
            "non_paid_lanes_parallel": True,
            "paid_calls_serialized": True,
            "release_mutations_serialized": True,
            "publication_requires_all_release_gates": True,
        },
        "runtime": runtime,
        "lock": lock,
        "budget": {
            "authorized_total_usd": cap,
            "estimated_checkpoint_usd": checkpoint,
            "estimated_remaining_usd": round(cap - checkpoint, 6),
            "actual_provider_billing": "NOT_REPORTED_UNLESS_PROVIDER_RETURNS_IT",
        },
        "summary": {
            "active_titles": len(active_rows),
            "public_readers": sum(row.get("publicly_rendered_book") == "Yes" for row in active_rows),
            "public_audiobooks": len(approved),
            "new_short_yes_yes_after_baseline": new_short_yes_yes,
            "paid_ready_titles": len(paid_queue),
        },
        "lanes": LANES,
        "title_decisions": decisions,
        "serialized_paid_queue": paid_queue,
        "next_paid_action": paid_queue[0] if paid_queue else None,
        "safety": {
            "failed_audio_publication_allowed": False,
            "static_audio_fallback_allowed": False,
            "browser_speech_fallback_allowed": False,
            "word_level_sync_claim_allowed": False,
            "arbitrary_matrix_command_execution_allowed": False,
        },
    }


def render_log(board: Mapping[str, Any], execution: Mapping[str, Any] | None = None) -> str:
    budget = board["budget"]
    summary = board["summary"]
    next_action = board.get("next_paid_action")
    lines = [
        "# Sprint 1 Autonomous Execution Log",
        "",
        f"Generated: {board['generated_at']}",
        f"Owner decision: `{board['owner_decision']}`",
        "",
        "## Coordinator State",
        "",
        f"- Active titles: {summary['active_titles']}",
        f"- Public readers: {summary['public_readers']}",
        f"- Public audiobooks: {summary['public_audiobooks']}",
        f"- Estimated spend checkpoint: ${budget['estimated_checkpoint_usd']:.6f}",
        f"- Estimated remaining budget: ${budget['estimated_remaining_usd']:.6f}",
        f"- Shared paid lock available: {board['lock']['available']}",
        "- Paid calls: serialized",
        "- Publication: fail closed until every release gate passes",
        "",
        "## Next Serialized Paid Action",
        "",
    ]
    if next_action:
        lines.extend(
            [
                f"- Slug: `{next_action['slug']}`",
                f"- Decision: `{next_action['decision']['state']}`",
                f"- Provider: `{next_action['decision'].get('provider', 'none')}`",
                f"- Voice: `{next_action['decision'].get('voice', 'none')}`",
                f"- Chance-per-dollar score: {next_action['chance_per_dollar']}",
            ]
        )
    else:
        lines.append("- None. Continue non-paid repair or obtain external narration/rights evidence.")
    history = board.get("execution_history", [])
    if history:
        lines.extend(
            [
                "",
                "## Execution History",
                "",
            ]
        )
        for item in history:
            lines.append(
                f"- `{item.get('completed_at')}` `{item.get('slug')}`: "
                f"`{item.get('status')}` (return code `{item.get('returncode')}`)"
            )
    lines.extend(
        [
            "",
            "## Release Truth",
            "",
            "No coordinator plan or audition result mutates a public release gate. Publication requires separate manifest, endpoint, frontend, and production validation evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def build_google_audition_command(
    root: Path,
    lock_path: Path,
    action: Mapping[str, Any],
    sprint_spend_usd: float,
    private_root: Path,
) -> tuple[list[str], list[str]]:
    slug = str(action["slug"])
    decision = action["decision"]
    if decision.get("state") not in {
        "GOOGLE_ENGLISH_ALTERNATE_AUDITION",
        "GOOGLE_ENGLISH_REPRESENTATIVE_AUDITION",
    }:
        raise OrchestratorError("NEXT_ACTION_NOT_AN_ALLOW_LISTED_GOOGLE_AUDITION")
    input_root = private_root / "inputs"
    output_root = private_root / "auditions" / slug
    sanitized_source = input_root / slug / "sanitized_source.txt"
    input_manifest = input_root / slug / "input_manifest.json"
    prepare = [
        sys.executable,
        str(root / "internal/audiobook_lab/scripts/sprint1_prepare_google_english_input.py"),
        "--slug",
        slug,
        "--controlled-root",
        str(root / "data/controlled_publications"),
        "--output-root",
        str(input_root),
    ]
    pipeline = [
        sys.executable,
        str(root / "internal/audiobook_lab/scripts/sprint1_google_english_private_pipeline.py"),
        "audition",
        "--sanitized-source",
        str(sanitized_source),
        "--input-manifest",
        str(input_manifest),
        "--paid-lock",
        str(lock_path),
        "--private-output-dir",
        str(output_root),
        "--voice",
        str(decision["voice"]),
        "--language-code",
        "en-GB",
        "--usd-per-million-chars",
        "20",
        "--run-budget-usd",
        "1",
        "--title-budget-usd",
        FIXED_PAID_ENV["SPRINT1_MAX_USD_PER_TITLE"],
        "--title-spend-usd",
        str(float(action.get("cost_used_usd", 0.0))),
        "--sprint-budget-usd",
        FIXED_PAID_ENV["SPRINT1_TOTAL_AUDIO_BUDGET_USD"],
        "--sprint-spend-usd",
        str(sprint_spend_usd),
        "--minimum-listening-score",
        "9.4",
        "--minimum-listening-confidence",
        "0.9",
        "--speaking-rate",
        str(decision.get("speaking_rate", 0.94)),
        "--execute",
    ]
    return prepare, pipeline


def execute_next_audition(
    board: dict[str, Any],
    root: Path,
    lock_path: Path,
    private_root: Path,
    env: Mapping[str, str],
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    action = board.get("next_paid_action")
    if not action:
        raise OrchestratorError("NO_PAID_READY_ACTION")
    validate_paid_runtime(board["runtime"], str(action["decision"].get("provider")))
    validate_lock(board["lock"])
    if board["budget"]["estimated_remaining_usd"] <= 0:
        raise OrchestratorError("SPRINT_BUDGET_EXHAUSTED")

    action = dict(action)
    row = next(
        item for item in board["title_decisions"] if item["slug"] == action["slug"]
    )
    action["cost_used_usd"] = next(
        (
            item.get("cost_used_usd", 0.0)
            for item in board.get("matrix_rows", [])
            if item.get("slug") == action["slug"]
        ),
        0.0,
    )
    prepare, pipeline = build_google_audition_command(
        root,
        lock_path,
        action,
        board["budget"]["estimated_checkpoint_usd"],
        private_root,
    )
    child_env = dict(env)
    child_env.update(FIXED_PAID_ENV)
    child_env["EARNALISM_APPROVE_GOOGLE_ENGLISH_PRIVATE_AUDITION"] = "true"
    child_env["PYTHONDONTWRITEBYTECODE"] = "1"

    prepared = runner(
        prepare,
        cwd=root,
        env=child_env,
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
    )
    if prepared.returncode != 0:
        return {
            "status": "NON_PAID_INPUT_PREPARATION_FAILED",
            "slug": row["slug"],
            "returncode": prepared.returncode,
            "completed_at": utc_now(),
            "stderr_tail": prepared.stderr[-2000:],
        }

    completed = runner(
        pipeline,
        cwd=root,
        env=child_env,
        text=True,
        capture_output=True,
        timeout=1800,
        check=False,
    )
    current_lock = lock_snapshot(lock_path)
    validate_lock(current_lock)
    status = "AUDITION_GENERATION_COMPLETE_QA_PENDING" if completed.returncode == 0 else "AUDITION_PROVIDER_OR_GUARD_FAILED"
    return {
        "status": status,
        "slug": row["slug"],
        "provider": action["decision"].get("provider"),
        "voice": action["decision"].get("voice"),
        "returncode": completed.returncode,
        "completed_at": utc_now(),
        "private_output_dir": str(private_root / "auditions" / str(row["slug"])),
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-2000:],
        "lock_after": current_lock,
        "public_release_mutated": False,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, default=Path.cwd())
    parser.add_argument("--lock-path", type=Path)
    parser.add_argument(
        "--private-root",
        type=Path,
        default=Path("/tmp/earnalism-sprint1-autonomous-v2-private"),
    )
    parser.add_argument("--execute-next-audition", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.asset_root.resolve()
    publication = root / "internal/audiobook_lab/sprint1_publication"
    matrix_path = publication / "sprint1_publication_matrix.json"
    cost_path = publication / "sprint1_cost_report.json"
    ledger_path = publication / "sprint1_budget_ledger.json"
    board_path = publication / "sprint1_autonomous_execution_board.json"
    log_path = publication / "sprint1_autonomous_execution_log.md"
    lock_path = (args.lock_path or root / "internal/earnalism_intelligence/locks/paid_tts.lock").resolve()

    previous_board = read_json(board_path) if board_path.exists() else {}
    matrix = read_json(matrix_path)
    cost_report = read_json(cost_path)
    ledger = read_json(ledger_path)
    runtime = credential_snapshot(os.environ)
    lock = lock_snapshot(lock_path)
    board = build_board(matrix, cost_report, ledger, runtime, lock)
    board["execution_history"] = list(previous_board.get("execution_history", []))
    board["matrix_rows"] = [
        {"slug": row.get("slug"), "cost_used_usd": row.get("cost_used_usd", 0.0)}
        for row in matrix.get("titles", [])
        if isinstance(row, dict)
    ]
    atomic_write_json(board_path, board)

    execution = None
    if args.execute_next_audition:
        execution = execute_next_audition(
            board,
            root,
            lock_path,
            args.private_root.resolve(),
            os.environ,
        )
        board["latest_execution"] = execution
        board["execution_history"].append(execution)
        board["lock"] = lock_snapshot(lock_path)
        atomic_write_json(board_path, board)
    atomic_write_text(log_path, render_log(board, execution))
    print(json.dumps({"board": str(board_path), "next_paid_action": board.get("next_paid_action"), "execution": execution}, ensure_ascii=False, indent=2))
    return 0 if not execution or execution.get("returncode") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
