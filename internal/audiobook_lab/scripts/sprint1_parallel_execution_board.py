#!/usr/bin/env python3
"""Materialize fail-closed Sprint 1 parallel lane evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PUBLICATION_DIR = Path("internal/audiobook_lab/sprint1_publication")


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def assignment_map(board: dict) -> dict[str, dict]:
    assignments: dict[str, dict] = {}
    for lane in board.get("lanes") or []:
        for slug in lane.get("titles") or []:
            if slug in assignments:
                raise ValueError(f"duplicate title assignment: {slug}")
            assignments[slug] = {
                "lane": lane["lane"],
                "role": lane["role"],
                "agent_id": lane["agent_id"],
                "agent_nickname": lane["agent_nickname"],
            }
    return assignments


def validate_assignments(matrix: dict, board: dict) -> dict[str, dict]:
    active = {
        item["slug"]
        for item in matrix.get("titles") or []
        if item.get("sprint1_audio_target") is True
    }
    assignments = assignment_map(board)
    assigned = set(assignments)
    missing = sorted(active - assigned)
    unexpected = sorted(assigned - active)
    if missing or unexpected:
        raise ValueError(f"lane coverage mismatch; missing={missing}; unexpected={unexpected}")
    return assignments


def title_report(row: dict, assignment: dict, generated_at: str) -> str:
    approved = row.get("publicly_available_audiobook") == "Yes"
    blocker = row.get("exact_blocker") or ("NONE" if approved else "TITLE_AUDIO_RELEASE_GATES_INCOMPLETE")
    return "\n".join(
        [
            f"# {row['title']} Parallel Sprint Report",
            "",
            f"Generated: `{generated_at}`",
            "",
            f"- Slug: `{row['slug']}`",
            f"- Language: `{row.get('language') or 'unknown'}`",
            f"- Assigned lane: `{assignment['lane']} - {assignment['role']}`",
            f"- Assigned agent: `{assignment['agent_nickname']} ({assignment['agent_id']})`",
            f"- Public reader: `{row.get('publicly_rendered_book') or 'No'}`",
            f"- Public audiobook: `{row.get('publicly_available_audiobook') or 'No'}`",
            f"- Quality evidence: `{row.get('quality_score') or 'NOT_RUN'}`",
            f"- Estimated remaining cost: `${float(row.get('estimated_incremental_cost_usd') or 0):.4f}`",
            f"- Final state: `{row.get('final_status') or 'SPRINT_TARGET_INCOMPLETE'}`",
            f"- Blocker: `{blocker}`",
            f"- Evidence: `{row.get('evidence_path') or 'NONE'}`",
            f"- Next action: {row.get('next_action') or 'Complete all release gates'}",
            "",
            "## Next Command",
            "",
            "```bash",
            row.get("next_command") or "true",
            "```",
            "",
            "No provider call, release-gate mutation, or public audio exposure was performed by this materializer.",
            "",
        ]
    )


def title_evidence(row: dict, assignment: dict, generated_at: str) -> dict:
    approved = row.get("publicly_available_audiobook") == "Yes"
    blocker = row.get("exact_blocker") or ("NONE" if approved else "TITLE_AUDIO_RELEASE_GATES_INCOMPLETE")
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "slug": row["slug"],
        "title": row["title"],
        "language": row.get("language"),
        "assigned_lane": assignment,
        "publicly_rendered_book": row.get("publicly_rendered_book"),
        "publicly_available_audiobook": row.get("publicly_available_audiobook"),
        "quality_score": row.get("quality_score"),
        "release_gate_state": "APPROVED_EXISTING_PUBLIC_AUDIO" if approved else "INCOMPLETE_FAIL_CLOSED",
        "exact_blocker": blocker,
        "estimated_remaining_cost_usd": float(row.get("estimated_incremental_cost_usd") or 0),
        "evidence_path": row.get("evidence_path"),
        "next_action": row.get("next_action"),
        "next_command": row.get("next_command"),
        "provider_calls_ran_this_sprint": False,
        "release_gate_mutated_this_sprint": False,
        "public_audio_approved_this_sprint": False,
    }


def materialize(root: Path, generated_at: str) -> dict:
    publication = root / PUBLICATION_DIR
    matrix_path = publication / "sprint1_publication_matrix.json"
    final_path = publication / "sprint1_final_yes_yes_matrix.json"
    board_path = publication / "sprint1_parallel_execution_board.json"
    matrix = read_json(matrix_path)
    final = read_json(final_path)
    board = read_json(board_path)
    assignments = validate_assignments(matrix, board)
    title_runs = publication / "title_runs"
    title_runs.mkdir(parents=True, exist_ok=True)
    created_evidence = 0

    for row in matrix["titles"]:
        slug = row["slug"]
        if slug not in assignments:
            continue
        assignment = assignments[slug]
        next_command = str(row.get("next_command") or "")
        if not (root / "book_import_manifest.json").exists():
            next_command = next_command.replace(
                "./book_import_manifest.json", "./book_import_manifest.batch-1.json"
            ).replace("book_import_manifest.json", "book_import_manifest.batch-1.json")
            row["next_command"] = next_command
        row["parallel_lane"] = assignment["lane"]
        row["parallel_agent_role"] = assignment["role"]
        row["parallel_agent_id"] = assignment["agent_id"]
        row["parallel_agent_nickname"] = assignment["agent_nickname"]
        row["parallel_paid_execution_status"] = (
            "NOT_REQUIRED_EXISTING_PUBLIC_AUDIO"
            if row.get("publicly_available_audiobook") == "Yes"
            else "WAITING_SERIALIZED_EXECUTION_RUNTIME_GATES_MISSING"
        )
        report_path = title_runs / f"{slug}_report.md"
        report_path.write_text(title_report(row, assignment, generated_at), encoding="utf-8")
        evidence_path = title_runs / f"{slug}_release_gate_evidence.json"
        if not evidence_path.exists():
            write_json(evidence_path, title_evidence(row, assignment, generated_at))
            created_evidence += 1
        else:
            current_evidence = read_json(evidence_path)
            if "assigned_lane" in current_evidence and "release_gate_state" in current_evidence:
                write_json(evidence_path, title_evidence(row, assignment, generated_at))

    matrix_by_slug = {row["slug"]: row for row in matrix["titles"]}
    for row in final["titles"]:
        assignment = assignments[row["slug"]]
        row["parallel_lane"] = assignment["lane"]
        row["parallel_agent_role"] = assignment["role"]
        row["parallel_agent_id"] = assignment["agent_id"]
        row["parallel_agent_nickname"] = assignment["agent_nickname"]
        row["next_command"] = matrix_by_slug[row["slug"]].get("next_command")

    write_json(matrix_path, matrix)
    write_json(final_path, final)
    return {
        "active_titles": len(assignments),
        "reports_written": len(assignments),
        "new_evidence_files": created_evidence,
        "provider_calls_ran": False,
        "release_gate_mutations": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--generated-at", default=iso_now())
    args = parser.parse_args()
    result = materialize(args.root.resolve(), args.generated_at)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
