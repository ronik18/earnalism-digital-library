#!/usr/bin/env python3
"""Execute the bounded Jekyll chunk_0009 context synthesis.

This is the execution companion to
``sprint1_jekyll_chunk9_sentence_safe_repair_preflight.py``. It performs only
the first paid step in the repair plan: one private Google synthesis call for
the exact preflight-bound context window. It does not splice audio, run QA,
upload media, mutate controlled publication truth, or publish audio.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import sys
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import sprint1_google_english_private_pipeline as google_pipeline  # noqa: E402


SCHEMA = "earnalism.jekyll_chunk9_sentence_safe_context_synthesis.v1"
PREFLIGHT_SCHEMAS = {
    "earnalism.jekyll_chunk9_sentence_safe_repair_preflight.v1",
    "earnalism.jekyll_chunk9_sentence_safe_repair_preflight_evidence.v1",
}
SLUG = "jekyll-and-hyde"
TARGET_UNIT_ID = "chunk_0009"
APPROVAL_ENV = "EARNALISM_APPROVE_JEKYLL_CHUNK9_SENTENCE_SAFE_REPAIR"
STOP_ON_BUDGET_ENV = "EARNALISM_STOP_ON_BUDGET_EXCEEDED"
EXPECTED_CONTEXT_SHA256 = (
    "977e108da205532a2379eb254bdb95b087064714cbdeecef583e8e14b8e13884"
)


class Chunk9RepairError(RuntimeError):
    def __init__(
        self,
        status: str,
        message: str,
        *,
        exit_code: int = 2,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.exit_code = exit_code
        self.details = dict(details or {})

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "error": str(self), **self.details}


ProviderFactory = Callable[[dict[str, Any]], google_pipeline.TTSProvider]


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def atomic_write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    temporary.write_bytes(value)
    if mode is not None:
        os.chmod(temporary, mode)
    os.replace(temporary, path)


def atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    atomic_write_bytes(
        path,
        (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )


def require(condition: bool, status: str, message: str) -> None:
    if not condition:
        raise Chunk9RepairError(status, message)


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Chunk9RepairError("BLOCKED_INVALID_EVIDENCE", f"{label} is not readable JSON: {path}") from exc
    require(isinstance(payload, dict), "BLOCKED_INVALID_EVIDENCE", f"{label} must be a JSON object")
    return payload


def validate_private_output_dir(path: Path) -> Path:
    try:
        resolved = google_pipeline.validate_private_output_dir(path)
    except google_pipeline.PipelineError as exc:
        raise Chunk9RepairError(exc.status, str(exc)) from exc
    return resolved


def validate_preflight(path: Path) -> dict[str, Any]:
    payload = read_json(path.expanduser().resolve(), "chunk9 repair preflight")
    require(payload.get("schema_version") in PREFLIGHT_SCHEMAS, "BLOCKED_PREFLIGHT_SCHEMA", "preflight schema mismatch")
    require(payload.get("status") == "PREFLIGHT_PASS_NO_PROVIDER_CALL_AUDIO_HIDDEN", "BLOCKED_PREFLIGHT_STATUS", "preflight did not pass")
    require(payload.get("slug") == SLUG, "BLOCKED_PREFLIGHT_SLUG", "preflight is not for Jekyll")
    require(payload.get("provider_calls_ran") is False, "BLOCKED_PREFLIGHT_STATE", "preflight already records provider work")
    require(payload.get("audio_generated") is False, "BLOCKED_PREFLIGHT_STATE", "preflight already records generated audio")
    require(payload.get("upload_performed") is False, "BLOCKED_PREFLIGHT_STATE", "preflight cannot include upload")
    require(payload.get("publication_performed") is False, "BLOCKED_PREFLIGHT_STATE", "preflight cannot include publication")
    require(payload.get("release_mutation_performed") is False, "BLOCKED_PREFLIGHT_STATE", "preflight cannot include release mutation")
    target = payload.get("target") if isinstance(payload.get("target"), dict) else {}
    plan = payload.get("provider_plan") if isinstance(payload.get("provider_plan"), dict) else {}
    budget = payload.get("budget") if isinstance(payload.get("budget"), dict) else {}
    require(target.get("unit_id") == TARGET_UNIT_ID, "BLOCKED_PREFLIGHT_TARGET", "preflight target must be chunk_0009")
    context_sha256 = plan.get("context_text_sha256") or plan.get("synthesis_context_sha256")
    require(context_sha256 == EXPECTED_CONTEXT_SHA256, "BLOCKED_CONTEXT_BINDING", "context text hash changed")
    require(plan.get("provider") == "google", "BLOCKED_PROVIDER", "only Google is permitted for this repair")
    require(plan.get("voice") == "en-GB-Chirp3-HD-Charon", "BLOCKED_VOICE", "voice must remain Charon")
    require(plan.get("language_code") == "en-GB", "BLOCKED_LANGUAGE", "language code must remain en-GB")
    require(float(plan.get("speaking_rate")) == 0.94, "BLOCKED_RATE", "speaking rate must remain 0.94")
    require(float(plan.get("pitch")) == 0.0, "BLOCKED_PITCH", "pitch must remain 0.0")
    require(float(budget.get("estimated_run_usd") or 1.0) <= float(budget.get("run_budget_usd") or 0.0), "BLOCKED_BUDGET", "estimated run cost exceeds run cap")
    return payload


def attempt_fingerprint(preflight: Mapping[str, Any]) -> str:
    plan = preflight["provider_plan"]
    target = preflight["target"]
    return canonical_sha256(
        {
            "schema_version": SCHEMA,
            "slug": SLUG,
            "unit_id": TARGET_UNIT_ID,
            "preflight_binding_sha256": preflight["preflight_binding_sha256"],
            "parent_manifest_sha256": preflight["parent_candidate"]["parent_full_manifest_sha256"],
            "target_text_sha256": target["source_text_sha256"],
            "prior_audio_sha256": target["prior_audio_sha256"],
            "context_text_sha256": plan.get("context_text_sha256") or plan.get("synthesis_context_sha256"),
            "provider": plan["provider"],
            "voice": plan["voice"],
            "language_code": plan["language_code"],
            "speaking_rate": plan["speaking_rate"],
            "pitch": plan["pitch"],
        }
    )


def validate_runtime(project_id: str | None) -> None:
    errors: list[str] = []
    if os.environ.get(APPROVAL_ENV, "").strip().lower() != "true":
        errors.append(f"{APPROVAL_ENV}=true is required")
    if os.environ.get(STOP_ON_BUDGET_ENV, "").strip().lower() != "true":
        errors.append(f"{STOP_ON_BUDGET_ENV}=true is required")
    if not (project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")):
        errors.append("GOOGLE_CLOUD_PROJECT or --project-id is required")
    if errors:
        raise Chunk9RepairError(
            "BLOCKED_RUNTIME_GATES",
            "explicit one-context paid runtime approval is incomplete",
            details={"errors": errors, "provider_calls_ran": False},
        )


def acquire_lock_payload(original: Mapping[str, Any], preflight: Mapping[str, Any], fingerprint: str) -> dict[str, Any]:
    payload = dict(original)
    payload.update(
        {
            "current_holder": f"sprint1_jekyll_google_chunk9_sentence_safe_repair:{SLUG}:{TARGET_UNIT_ID}",
            "allowed_next_holders": [],
            "holder_started_at": iso_now(),
            "allowed_slugs": [SLUG],
            "budget_cap_usd": preflight["budget"]["run_budget_usd"],
            "estimated_cost_usd": preflight["budget"]["estimated_run_usd"],
            "approved_scope": (
                "Exactly one private Google context-window synthesis for "
                f"{SLUG} {TARGET_UNIT_ID}; no splice, upload, publication, or release mutation; "
                f"fingerprint {fingerprint}."
            ),
            "stop_conditions": [
                "Any exact preflight, context, audio, lock, or budget binding fails",
                "Google returns empty or non-MP3 audio",
                "Any output path is public or release-facing",
                "Any splice, upload, publication, or release mutation is attempted",
            ],
            "updated_at": iso_now(),
        }
    )
    return payload


def default_provider_factory(config: dict[str, Any]) -> google_pipeline.TTSProvider:
    return google_pipeline.GoogleCloudTTSProvider(config.get("project_id") or os.environ.get("GOOGLE_CLOUD_PROJECT"))


def run(
    *,
    preflight_path: Path,
    paid_lock: Path,
    private_output_dir: Path,
    project_id: str | None = None,
    execute: bool = False,
    provider_factory: ProviderFactory | None = None,
) -> dict[str, Any]:
    preflight = validate_preflight(preflight_path)
    output_dir = validate_private_output_dir(private_output_dir)
    fingerprint = attempt_fingerprint(preflight)
    run_dir = output_dir / SLUG / "chunk9_context_synthesis" / fingerprint[:16]
    state_path = output_dir / SLUG / "repair_attempts" / f"{fingerprint}.json"
    require(not run_dir.exists(), "BLOCKED_IMMUTABLE_OUTPUT_EXISTS", "context synthesis output already exists")
    if state_path.is_file():
        state = read_json(state_path, "prior chunk9 context synthesis state")
        require(state.get("provider_calls_ran") is not True, "BLOCKED_DUPLICATE_FINGERPRINT", "this exact context synthesis already reached Google")

    plan = preflight["provider_plan"]
    context = str(
        preflight["target"].get("synthesis_context")
        or preflight["provider_plan"].get("synthesis_context")
        or ""
    )
    require(sha256_bytes(context.encode("utf-8")) == EXPECTED_CONTEXT_SHA256, "BLOCKED_CONTEXT_BINDING", "context text bytes changed")
    result = {
        "schema_version": SCHEMA,
        "status": "PREFLIGHT_PASS_PRIVATE_CONTEXT_ONLY",
        "generated_at": iso_now(),
        "slug": SLUG,
        "title": preflight.get("title"),
        "author": preflight.get("author"),
        "unit_id": TARGET_UNIT_ID,
        "preflight_path": str(preflight_path.expanduser().resolve()),
        "preflight_sha256": sha256_file(preflight_path.expanduser().resolve()),
        "preflight_binding_sha256": preflight["preflight_binding_sha256"],
        "attempt_fingerprint": fingerprint,
        "provider": plan["provider"],
        "voice": plan["voice"],
        "language_code": plan["language_code"],
        "speaking_rate": plan["speaking_rate"],
        "pitch": plan["pitch"],
        "context_text_sha256": EXPECTED_CONTEXT_SHA256,
        "context_characters": len(context),
        "budget": preflight["budget"],
        "private_output_only": True,
        "provider_calls_ran": False,
        "synthesis_calls": 0,
        "audio_generated": False,
        "splice_performed": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
        "paid_lock_touched": False,
        "next_exact_command": " ".join(
            shlex.quote(part)
            for part in [
                sys.executable,
                str(Path(__file__).resolve()),
                "--preflight-report",
                str(preflight_path),
                "--paid-lock",
                str(paid_lock),
                "--private-output-dir",
                str(private_output_dir),
                "--execute",
            ]
        ),
    }
    if not execute:
        return result

    validate_runtime(project_id)
    lock_path = paid_lock.expanduser().resolve()
    original_lock = lock_path.read_bytes()
    lock_before_sha256 = sha256_bytes(original_lock)
    try:
        parsed_lock = google_pipeline.validate_paid_lock(original_lock)
    except google_pipeline.PipelineError as exc:
        raise Chunk9RepairError(exc.status, str(exc)) from exc
    audio_path = run_dir / "source_audio" / f"{TARGET_UNIT_ID}_context.mp3"
    state = {**result, "status": "PROVIDER_READY_PENDING_ONE_CONTEXT_SYNTHESIS", "started_at": iso_now()}
    atomic_write_json(state_path, state)
    provider_calls = 0
    execution_error: Exception | None = None
    audio_bytes = b""
    try:
        atomic_write_json(lock_path, acquire_lock_payload(parsed_lock, preflight, fingerprint))
        provider = (provider_factory or default_provider_factory)({"project_id": project_id})
        ensure_voice = getattr(provider, "ensure_voice", None)
        if callable(ensure_voice):
            ensure_voice(voice=plan["voice"], language_code=plan["language_code"])
        state.update({"status": "PROVIDER_CALL_STARTED", "provider_calls_ran": True})
        atomic_write_json(state_path, state)
        audio_bytes = bytes(
            provider.synthesize(
                text=context,
                voice=plan["voice"],
                language_code=plan["language_code"],
                speaking_rate=float(plan["speaking_rate"]),
                pitch=float(plan["pitch"]),
            )
        )
        provider_calls = 1
        require(
            bool(audio_bytes) and (audio_bytes.startswith(b"ID3") or audio_bytes.startswith(b"\xff")),
            "PROVIDER_EXECUTION_FAILED",
            "Google returned empty or non-MP3 context audio",
        )
        atomic_write_bytes(audio_path, audio_bytes)
    except Exception as exc:  # noqa: BLE001
        execution_error = exc
    finally:
        try:
            atomic_write_bytes(lock_path, original_lock)
        except Exception as restore_exc:  # noqa: BLE001
            execution_error = Chunk9RepairError("PAID_LOCK_RESTORE_FAILED", f"paid lock restoration failed: {restore_exc}", exit_code=7)

    lock_after = lock_path.read_bytes()
    lock_restored = lock_after == original_lock
    if execution_error is not None or not lock_restored:
        state.update(
            {
                "status": "PROVIDER_FAILED_PRIVATE_ONLY" if lock_restored else "PAID_LOCK_RESTORE_FAILED",
                "finished_at": iso_now(),
                "provider_calls_ran": provider_calls > 0,
                "synthesis_calls": provider_calls,
                "paid_lock_touched": True,
                "paid_lock_restored_byte_for_byte": lock_restored,
                "paid_lock_sha256_before": lock_before_sha256,
                "paid_lock_sha256_after": sha256_bytes(lock_after),
                "errors": [f"{type(execution_error).__name__}: {execution_error}"] if execution_error else [],
            }
        )
        atomic_write_json(state_path, state)
        if isinstance(execution_error, Chunk9RepairError):
            raise execution_error
        raise Chunk9RepairError(
            "PROVIDER_EXECUTION_FAILED",
            f"private context synthesis failed: {execution_error}",
            exit_code=6,
            details={"provider_calls_ran": provider_calls > 0},
        ) from execution_error

    final = {
        **result,
        "status": "CONTEXT_AUDIO_PRIVATE_QA_PENDING_ALIGNMENT_AND_SPLICE",
        "finished_at": iso_now(),
        "provider_calls_ran": True,
        "synthesis_calls": 1,
        "audio_generated": True,
        "context_audio_path": str(audio_path),
        "context_audio_sha256": sha256_bytes(audio_bytes),
        "context_audio_size_bytes": len(audio_bytes),
        "paid_lock_touched": True,
        "paid_lock_restored_byte_for_byte": True,
        "paid_lock_sha256_before": lock_before_sha256,
        "paid_lock_sha256_after": sha256_bytes(lock_after),
        "next_exact_command": (
            "Implement/run the forced-alignment clause extraction and splice step "
            "against this context audio; do not upload or release until fresh objective "
            "and listening QA pass."
        ),
    }
    evidence_path = run_dir / "context_synthesis_evidence.json"
    final["evidence_path"] = str(evidence_path)
    atomic_write_json(evidence_path, final)
    atomic_write_json(state_path, final)
    return final


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-report", required=True, type=Path)
    parser.add_argument("--paid-lock", required=True, type=Path)
    parser.add_argument("--private-output-dir", required=True, type=Path)
    parser.add_argument("--project-id")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = run(
            preflight_path=args.preflight_report,
            paid_lock=args.paid_lock,
            private_output_dir=args.private_output_dir,
            project_id=args.project_id,
            execute=args.execute,
        )
    except Chunk9RepairError as exc:
        print(json.dumps(exc.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return exc.exit_code
    except (OSError, ValueError) as exc:
        error = Chunk9RepairError("BLOCKED_INPUT", str(exc))
        print(json.dumps(error.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return error.exit_code
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
