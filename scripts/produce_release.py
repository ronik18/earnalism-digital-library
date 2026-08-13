#!/usr/bin/env python3
"""Deterministic release coordinator with two human gates.

This command evaluates a title manifest. Rights, content, artifact, staging,
browser, and production checks are automated inputs and fail closed. The only
human inputs are the conversation-rendered reader preview approval and the
conversation-rendered six-or-seven-sample listening approval. It never infers
legal permission, quality, or deployment success.

The command is provider-free by design: generation and deployment adapters must
write their explicit PASS results into the title manifest before promotion.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from release_intelligence import (
        rank_strategies,
        read_learning_ledger,
        record_learning,
        validate_strategy,
    )
except ImportError:  # package-style test imports
    from scripts.release_intelligence import (
        rank_strategies,
        read_learning_ledger,
        record_learning,
        validate_strategy,
    )


AUTOMATED_CHECKS = (
    "rights",
    "manuscript",
    "reader_artifacts",
    "audio_review_samples",
    "sanitization",
    "chapter_index",
    "pagination",
    "covers",
    "audio_artifacts",
    "asr_coverage",
    "boundary_order",
    "technical_audio",
    "synchronization",
    "checksums",
    "storage",
    "endpoint_cache",
    "service_worker",
    "ci_build",
    "staging",
    "device_matrix",
    "browser",
    "production",
)

REPAIRABLE_AUTOMATED_CHECKS = (
    "audio_artifacts",
    "asr_coverage",
    "boundary_order",
    "technical_audio",
    "synchronization",
    "checksums",
    "storage",
    "endpoint_cache",
    "service_worker",
    "ci_build",
    "staging",
    "device_matrix",
    "browser",
    "production",
)
TRANSIENT_FAILURE_CLASS = "TRANSIENT"
DEFAULT_MAX_REPAIR_ATTEMPTS = 3
MIN_AUDIO_REVIEW_SAMPLES = 6
MAX_AUDIO_REVIEW_SAMPLES = 7
MIN_LISTENING_SCORE = 8.9
MIN_LISTENING_CONFIDENCE = 0.90
LISTENING_DIMENSIONS = (
    "naturalness",
    "pronunciation",
    "expression",
    "punctuation_pauses",
    "pacing",
    "silence_clipping",
    "glitches",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_sha256(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(
        character in "0123456789abcdef" for character in text
    )


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def is_http_url(value: Any) -> bool:
    parsed = urlparse(str(value or ""))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def pass_result(detail: str) -> dict[str, Any]:
    return {"status": "PASS", "detail": detail}


def block_result(detail: str) -> dict[str, Any]:
    return {"status": "BLOCKED", "detail": detail}


def check_file(
    root: Path, value: Any, expected_sha256: Any, label: str
) -> dict[str, Any]:
    if not value:
        return block_result(f"{label} path is missing")
    path = (
        (root / str(value)).resolve()
        if not Path(str(value)).is_absolute()
        else Path(str(value))
    )
    if not path.is_file():
        return block_result(f"{label} does not exist: {path}")
    actual = sha256_file(path)
    expected = str(expected_sha256 or "").lower()
    if len(expected) != 64 or actual != expected:
        return block_result(f"{label} checksum mismatch")
    return pass_result(f"{label} present and checksum verified")


def resolved_artifact_path(root: Path, value: Any) -> str:
    if not value:
        return ""
    path = Path(str(value))
    return str(path if path.is_absolute() else (root / path).resolve())


def check_rights(manifest: dict[str, Any]) -> dict[str, Any]:
    rights = manifest.get("rights") or {}
    missing = [
        field
        for field in (
            "source_url",
            "source_license",
            "commercial_use",
            "territories",
            "source_sha256",
        )
        if not rights.get(field)
    ]
    if missing:
        return block_result("explicit rights fields missing: " + ", ".join(missing))
    if not is_http_url(rights.get("source_url")):
        return block_result("rights source_url is not an http(s) URL")
    if str(rights.get("commercial_use")).upper() != "APPROVED":
        return block_result("commercial_use must be explicitly APPROVED")
    if not isinstance(rights.get("territories"), list) or not rights["territories"]:
        return block_result("at least one approved territory is required")
    if not is_sha256(rights.get("source_sha256")):
        return block_result("source_sha256 must be a SHA-256 digest")
    return pass_result("explicit source and commercial-use rights verified")


def check_human_gate(
    path: Path | None, slug: str, gate_name: str, expected: dict[str, Any]
) -> dict[str, Any]:
    if path is None:
        return {
            "status": "PENDING",
            "detail": f"{gate_name} approval packet not supplied",
        }
    try:
        approval = load_json(path)
    except ValueError as exc:
        return block_result(str(exc))
    if str(approval.get("status", "")).upper() != "APPROVED":
        return block_result(f"{gate_name} approval is not APPROVED")
    if approval.get("slug") != slug:
        return block_result(f"{gate_name} approval slug does not match title")
    if (
        not str(approval.get("approved_by") or "").strip()
        or not str(approval.get("approved_at") or "").strip()
    ):
        return block_result(
            f"{gate_name} approval must identify the reviewer and approval time"
        )
    for key, value in expected.items():
        if approval.get(key) != value:
            return block_result(f"{gate_name} approval does not match {key}")
    return pass_result(f"{gate_name} approval explicitly recorded")


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def check_audio_review_samples(
    root: Path, audio: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    samples = audio.get("review_samples") or []
    if (
        not isinstance(samples, list)
        or not MIN_AUDIO_REVIEW_SAMPLES <= len(samples) <= MAX_AUDIO_REVIEW_SAMPLES
    ):
        return (
            block_result("audio review requires exactly 6 or 7 checksum-bound samples"),
            {},
        )
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, sample in enumerate(samples, start=1):
        if not isinstance(sample, dict):
            return block_result(f"audio review sample {index} is not an object"), {}
        sample_id = str(sample.get("id") or "").strip()
        source_sha256 = str(sample.get("source_sha256") or "").strip().lower()
        if not sample_id or sample_id in seen_ids:
            return (
                block_result("audio review sample IDs must be present and unique"),
                {},
            )
        if not is_sha256(source_sha256):
            return (
                block_result(
                    f"audio review sample {sample_id} source checksum is invalid"
                ),
                {},
            )
        checked = check_file(
            root,
            sample.get("path"),
            sample.get("sha256"),
            f"audio review sample {sample_id}",
        )
        if checked["status"] != "PASS":
            return checked, {}
        seen_ids.add(sample_id)
        normalized.append(
            {
                "id": sample_id,
                "sha256": str(sample.get("sha256") or "").strip().lower(),
                "source_sha256": source_sha256,
            }
        )
    binding = {
        "sample_count": len(normalized),
        "sample_set_sha256": canonical_hash(normalized),
        "samples": normalized,
    }
    return (
        pass_result(
            f"{len(normalized)} audio review samples present and checksum verified"
        ),
        binding,
    )


def check_reader_preview_approval(
    path: Path | None,
    slug: str,
    *,
    manuscript_sha256: Any,
    preview_sha256: Any,
) -> dict[str, Any]:
    result = check_human_gate(
        path,
        slug,
        "reader preview",
        {
            "approval_type": "READER_PREVIEW",
            "render_surface": "CONVERSATION",
            "manuscript_sha256": manuscript_sha256,
            "preview_sha256": preview_sha256,
        },
    )
    if result["status"] != "PASS" or path is None:
        return result
    approval = load_json(path)
    if approval.get("preview_reviewed") is not True:
        return block_result(
            "reader preview approval must confirm preview_reviewed=true"
        )
    return result


def check_audio_samples_approval(
    path: Path | None,
    slug: str,
    *,
    audio: dict[str, Any],
    sample_binding: dict[str, Any],
) -> dict[str, Any]:
    result = check_human_gate(
        path,
        slug,
        "audio samples",
        {
            "approval_type": "AUDIO_SAMPLE_SET",
            "render_surface": "CONVERSATION",
            "sample_set_sha256": sample_binding.get("sample_set_sha256"),
            "sample_count": sample_binding.get("sample_count"),
            "model": audio.get("model"),
            "voice": audio.get("voice"),
            "owner_public_release_intent": True,
        },
    )
    if result["status"] != "PASS" or path is None:
        return result
    approval = load_json(path)
    if approval.get("listened_all_samples") is not True:
        return block_result(
            "audio sample approval must confirm listened_all_samples=true"
        )
    if approval.get("every_fatal_flag_false") is not True:
        return block_result(
            "audio sample approval must confirm every fatal flag is false"
        )
    try:
        overall = float(approval.get("overall_score"))
        confidence = float(approval.get("confidence"))
        supplied_dimensions = approval.get("dimension_scores") or {}
        if set(supplied_dimensions) != set(LISTENING_DIMENSIONS):
            return block_result(
                "audio sample approval must contain exactly the seven listening dimensions"
            )
        dimensions = [float(supplied_dimensions[name]) for name in LISTENING_DIMENSIONS]
    except KeyError:
        return block_result(
            "audio sample approval must score all seven listening dimensions"
        )
    except (TypeError, ValueError):
        return block_result("audio sample approval scores are invalid")
    if overall < MIN_LISTENING_SCORE or confidence < MIN_LISTENING_CONFIDENCE:
        return block_result(
            "audio sample approval does not meet listening score/confidence thresholds"
        )
    if min(dimensions) < MIN_LISTENING_SCORE:
        return block_result(
            "every audio sample review dimension must score at least 8.9"
        )
    return result


def check_declared_automated_pass(
    root: Path, name: str, supplied: Any
) -> dict[str, Any]:
    value = supplied if isinstance(supplied, dict) else {}
    if str(value.get("status") or "").upper() != "PASS":
        return block_result(f"{name} requires an explicit automated PASS")
    return check_file(
        root,
        value.get("evidence_path"),
        value.get("evidence_sha256"),
        f"{name} evidence",
    )


def evaluate(
    manifest: dict[str, Any],
    root: Path,
    reader_approval: Path | None,
    audio_approval: Path | None,
) -> dict[str, Any]:
    slug = str(manifest.get("slug") or "").strip()
    if not slug:
        raise ValueError("manifest.slug is required")
    manuscript = manifest.get("manuscript") or {}
    reader = manifest.get("reader") or {}
    audio = manifest.get("audio") or {}
    automated: dict[str, dict[str, Any]] = {"rights": check_rights(manifest)}
    automated["manuscript"] = check_file(
        root, manuscript.get("path"), manuscript.get("sha256"), "manuscript"
    )
    automated["reader_artifacts"] = check_file(
        root, reader.get("preview_path"), reader.get("preview_sha256"), "reader preview"
    )
    automated["audio_review_samples"], sample_binding = check_audio_review_samples(
        root, audio
    )

    for name in AUTOMATED_CHECKS[4:]:
        supplied = (manifest.get("automated_checks") or {}).get(name) or {}
        automated[name] = check_declared_automated_pass(root, name, supplied)

    reader_gate = check_reader_preview_approval(
        reader_approval,
        slug,
        manuscript_sha256=manuscript.get("sha256"),
        preview_sha256=reader.get("preview_sha256"),
    )
    audio_gate = check_audio_samples_approval(
        audio_approval,
        slug,
        audio=audio,
        sample_binding=sample_binding,
    )
    automated_pass = all(item["status"] == "PASS" for item in automated.values())
    human_pass = reader_gate["status"] == "PASS" and audio_gate["status"] == "PASS"
    return {
        "slug": slug,
        "manifest_sha256": canonical_hash(manifest),
        "human_gates": {"reader_preview": reader_gate, "audio_samples": audio_gate},
        "conversation_review": {
            "reader_preview": resolved_artifact_path(root, reader.get("preview_path")),
            "audio_samples": [
                resolved_artifact_path(root, item.get("path"))
                for item in (audio.get("review_samples") or [])
                if isinstance(item, dict)
            ],
            **sample_binding,
        },
        "automated_checks": automated,
        "release_status": (
            "READY_FOR_GO_LIVE" if automated_pass and human_pass else "BLOCKED"
        ),
        "next_action": (
            "run automatic production promotion"
            if automated_pass and human_pass
            else "resolve the first BLOCKED or PENDING check"
        ),
    }


def execute_go_live(
    report: dict[str, Any],
    manifest: dict[str, Any],
    reader_approval: Path | None,
    audio_approval: Path | None,
    staging_receipt: Path,
    *,
    promoter=None,
) -> dict[str, Any]:
    """Promote immediately after the two human gates and automation pass."""

    if report.get("release_status") != "READY_FOR_GO_LIVE":
        raise ValueError("automatic GO LIVE requires READY_FOR_GO_LIVE")
    if report.get("manifest_sha256") != canonical_hash(manifest):
        raise ValueError("release manifest changed after evaluation")
    if reader_approval is None or audio_approval is None:
        raise ValueError(
            "automatic GO LIVE requires both conversation approval packets"
        )
    try:
        from release_runtime import (
            RuntimeBlocked,
            load_json as load_runtime_json,
            promote,
        )
    except ImportError:  # package-style test imports
        from scripts.release_runtime import (
            RuntimeBlocked,
            load_json as load_runtime_json,
            promote,
        )

    runtime_manifest = dict(manifest)
    runtime_manifest["release_status"] = "READY_FOR_GO_LIVE"
    runtime_manifest["reader_approval"] = load_json(reader_approval)
    runtime_manifest["audio_samples_approval"] = load_json(audio_approval)
    try:
        promotion = promote(
            runtime_manifest,
            load_runtime_json(staging_receipt),
            execute=True,
            promoter=promoter,
        )
    except RuntimeBlocked as exc:
        raise ValueError(str(exc)) from exc
    if promotion.get("passed") is not True or promotion.get("status") not in {
        "LIVE",
        "PROMOTED",
    }:
        raise ValueError("production promotion did not return verified LIVE evidence")
    return {
        **report,
        "release_status": "LIVE",
        "next_action": "production is live and post-deployment checks passed",
        "promotion": promotion,
    }


def load_repair_adapter(path: Path):
    """Load an explicitly selected local adapter; never discover one implicitly."""
    spec = importlib.util.spec_from_file_location(
        "earnalism_release_repair_adapter", path
    )
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load repair adapter: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    repair = getattr(module, "repair", None)
    if not callable(repair):
        raise ValueError(
            "repair adapter must export repair(manifest, check, strategy, failed_segments)"
        )
    return repair


def self_heal(
    manifest: dict[str, Any],
    root: Path,
    reader_approval: Path | None,
    audio_approval: Path | None,
    repair_adapter,
    max_attempts: int,
    learning_ledger: Path | None = None,
) -> dict[str, Any]:
    """Repair only explicit transient technical failures, then re-evaluate."""
    history: list[dict[str, Any]] = []
    for cycle in range(max_attempts + 1):
        report = evaluate(manifest, root, reader_approval, audio_approval)
        report["self_healing"] = {"cycles": cycle, "attempts": history}
        if report["release_status"] == "READY_FOR_GO_LIVE":
            return report
        if any(gate["status"] != "PASS" for gate in report["human_gates"].values()):
            report["self_healing"]["stopped"] = "human approval gate pending or blocked"
            return report
        check = next(
            (
                name
                for name in REPAIRABLE_AUTOMATED_CHECKS
                if report["automated_checks"].get(name, {}).get("status") != "PASS"
            ),
            None,
        )
        if check is None:
            report["self_healing"]["stopped"] = "non-repairable automated blocker"
            return report
        if cycle >= max_attempts:
            report["self_healing"]["stopped"] = "repair attempt limit reached"
            return report

        strategies = rank_strategies(
            check,
            (manifest.get("repair_strategies") or {}).get(check) or [],
            read_learning_ledger(learning_ledger),
        )
        attempt_number = len([item for item in history if item.get("check") == check])
        if attempt_number >= len(strategies):
            report["self_healing"][
                "stopped"
            ] = f"no untried repair strategy for {check}"
            return report
        strategy = strategies[attempt_number]
        try:
            validate_strategy(check, strategy)
        except ValueError as exc:
            report["self_healing"]["stopped"] = str(exc)
            return report
        try:
            result = repair_adapter(
                manifest=manifest,
                check=check,
                strategy=strategy,
                failed_segments=strategy.get("failed_segments") or [],
                reuse_artifacts=True,
            )
        except Exception as exc:  # adapter failures remain blockers
            record_learning(
                learning_ledger,
                check=check,
                strategy=str(strategy.get("id")),
                outcome="FAILED",
            )
            history.append(
                {
                    "check": check,
                    "strategy": strategy.get("id"),
                    "status": "FAILED",
                    "detail": str(exc),
                }
            )
            continue
        evidence_path = (
            result.get("evidence_path") if isinstance(result, dict) else None
        )
        evidence_sha256 = (
            result.get("evidence_sha256") if isinstance(result, dict) else None
        )
        if (
            not isinstance(result, dict)
            or str(result.get("status", "")).upper() != "PASS"
        ):
            record_learning(
                learning_ledger,
                check=check,
                strategy=str(strategy.get("id")),
                outcome="BLOCKED",
                result=result if isinstance(result, dict) else None,
            )
            history.append(
                {
                    "check": check,
                    "strategy": strategy.get("id"),
                    "status": "BLOCKED",
                    "detail": "adapter did not return PASS",
                }
            )
            continue
        evidence = check_file(
            root, evidence_path, evidence_sha256, f"{check} repair evidence"
        )
        if evidence["status"] != "PASS":
            record_learning(
                learning_ledger,
                check=check,
                strategy=str(strategy.get("id")),
                outcome="BLOCKED",
                result=result,
            )
            history.append(
                {
                    "check": check,
                    "strategy": strategy.get("id"),
                    "status": "BLOCKED",
                    "detail": evidence["detail"],
                }
            )
            continue
        if (
            not result.get("reused_artifacts", True)
            or "regenerated_segments" not in result
        ):
            record_learning(
                learning_ledger,
                check=check,
                strategy=str(strategy.get("id")),
                outcome="BLOCKED",
                result=result,
            )
            history.append(
                {
                    "check": check,
                    "strategy": strategy.get("id"),
                    "status": "BLOCKED",
                    "detail": "repair must declare reuse and regenerated segments",
                }
            )
            continue
        manifest.setdefault("automated_checks", {})[check] = {
            "status": "PASS",
            "evidence_path": evidence_path,
            "evidence_sha256": evidence_sha256,
        }
        history.append(
            {
                "check": check,
                "strategy": strategy.get("id"),
                "status": "PASS",
                "regenerated_segments": result.get("regenerated_segments") or [],
                "reused_artifacts": True,
            }
        )
        record_learning(
            learning_ledger,
            check=check,
            strategy=str(strategy.get("id")),
            outcome="PASS",
            result=result,
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reader-approval", type=Path)
    parser.add_argument("--audio-samples-approval", type=Path)
    parser.add_argument("--audio-profile-approval", type=Path, help=argparse.SUPPRESS)
    parser.add_argument(
        "--auto-go-live",
        action="store_true",
        help="Promote automatically after both human gates and every automated check pass",
    )
    parser.add_argument(
        "--staging-receipt",
        type=Path,
        help="Private staging receipt required by --auto-go-live",
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--state-file",
        type=Path,
        help="Optional status output; no evidence is written by default",
    )
    parser.add_argument(
        "--self-heal",
        action="store_true",
        help="Use an explicit local repair adapter for transient technical failures",
    )
    parser.add_argument(
        "--repair-adapter",
        type=Path,
        help="Explicit adapter path required with --self-heal",
    )
    parser.add_argument(
        "--max-repair-attempts", type=int, default=DEFAULT_MAX_REPAIR_ATTEMPTS
    )
    parser.add_argument(
        "--learning-ledger",
        type=Path,
        help="Optional operational strategy-outcome ledger",
    )
    args = parser.parse_args(argv)
    try:
        manifest = load_json(args.manifest)
        audio_approval = args.audio_samples_approval or args.audio_profile_approval
        if args.audio_samples_approval and args.audio_profile_approval:
            raise ValueError("supply only --audio-samples-approval")
        if args.self_heal:
            if not args.repair_adapter:
                raise ValueError("--repair-adapter is required with --self-heal")
            if args.max_repair_attempts < 1 or args.max_repair_attempts > 3:
                raise ValueError("--max-repair-attempts must be between 1 and 3")
            report = self_heal(
                manifest,
                args.root.resolve(),
                args.reader_approval,
                audio_approval,
                load_repair_adapter(args.repair_adapter),
                args.max_repair_attempts,
                args.learning_ledger,
            )
        else:
            report = evaluate(
                manifest, args.root.resolve(), args.reader_approval, audio_approval
            )
        if args.auto_go_live:
            if args.staging_receipt is None:
                raise ValueError("--staging-receipt is required with --auto-go-live")
            report = execute_go_live(
                report,
                manifest,
                args.reader_approval,
                audio_approval,
                args.staging_receipt,
            )
    except ValueError as exc:
        print(json.dumps({"release_status": "BLOCKED", "error": str(exc)}, indent=2))
        return 2
    rendered = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
    print(rendered)
    if args.state_file:
        args.state_file.parent.mkdir(parents=True, exist_ok=True)
        args.state_file.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["release_status"] in {"READY_FOR_GO_LIVE", "LIVE"} else 1


if __name__ == "__main__":
    sys.exit(main())
