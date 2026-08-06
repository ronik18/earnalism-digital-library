#!/usr/bin/env python3
"""Guarded runtime for paid generation, staging import, and production promotion.

The command is deliberately separate from ``produce_release.py``'s evaluator:
the evaluator proves release truth, while this module performs explicitly
authorized side effects. Dry-run is the default for every subcommand.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.audiobook_generation.provider_adapter import (  # noqa: E402
    GenerationRequest,
    PaidGenerationAuthorization,
    ProviderExecutionError,
    NarrationProvider,
    provider_for_name,
)


class RuntimeBlocked(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeBlocked(f"invalid JSON input: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeBlocked(f"JSON object required: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def safe_child(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise RuntimeBlocked("artifact path escapes the controlled root") from exc
    return candidate


def require_profile_approval(manifest: dict[str, Any]) -> dict[str, Any]:
    audio = manifest.get("audio") or {}
    approval = manifest.get("audio_profile_approval") or {}
    if approval.get("status") != "APPROVED":
        raise RuntimeBlocked("audio profile approval is required before generation")
    for field in ("profile_sha256", "model", "voice"):
        if approval.get(field) != audio.get(field):
            raise RuntimeBlocked(f"audio profile approval does not match {field}")
    if audio.get("provider") not in {"sarvam", "elevenlabs"}:
        raise RuntimeBlocked("audio provider is not supported by a real adapter")
    return audio


def require_generation_rights(manifest: dict[str, Any]) -> None:
    rights = manifest.get("rights") or {}
    if rights.get("commercial_use") != "APPROVED":
        raise RuntimeBlocked("commercial-use rights are not APPROVED")
    if not isinstance(rights.get("territories"), list) or not rights["territories"]:
        raise RuntimeBlocked("approved publication territories are required")
    if rights.get("audio_derivative_rights_status") not in {
        "APPROVED",
        "RIGHTS_APPROVED",
    }:
        raise RuntimeBlocked("audio derivative rights are not explicitly approved")


@dataclass
class GenerationLedger:
    path: Path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema": "earnalism.generation-ledger.v1", "segments": {}}
        value = load_json(self.path)
        if not isinstance(value.get("segments"), dict):
            raise RuntimeBlocked("generation ledger is malformed")
        return value

    def save(self, value: dict[str, Any]) -> None:
        write_json(self.path, value)


def estimate_total(provider: NarrationProvider, manifest: dict[str, Any]) -> float:
    audio = require_profile_approval(manifest)
    total = 0.0
    for segment in manifest.get("segments") or []:
        if (
            not isinstance(segment, dict)
            or not segment.get("id")
            or not segment.get("text")
        ):
            raise RuntimeBlocked("every segment requires id and text")
        request = GenerationRequest(
            book_slug=str(manifest["slug"]),
            segment_id=str(segment["id"]),
            text_ref=str(segment["text"]),
            text=str(segment["text"]),
            language=str(manifest.get("language") or audio.get("language") or ""),
            narrator_profile_id=str(audio.get("voice") or ""),
            voice_source_type=str(audio.get("voice_source_type") or "STYLE_PROFILE"),
            consent_status=str(
                audio.get("consent_status") or "NOT_APPLICABLE_STYLE_PROFILE"
            ),
            metadata={"estimated_cost_usd": segment.get("estimated_cost_usd"), **audio},
        )
        total += provider.estimate_cost(request)
    if not manifest.get("segments"):
        raise RuntimeBlocked("manifest contains no segments")
    return round(total, 6)


def generate_segments(
    manifest: dict[str, Any],
    output_dir: Path,
    *,
    execute: bool = False,
    max_retries: int = 3,
    provider: NarrationProvider | None = None,
) -> dict[str, Any]:
    if max_retries < 1 or max_retries > 3:
        raise RuntimeBlocked("max_retries must be between 1 and 3")
    require_generation_rights(manifest)
    audio = require_profile_approval(manifest)
    provider = provider or provider_for_name(str(audio["provider"]))
    estimated_cost = estimate_total(provider, manifest)
    budget = float(os.environ.get("EARNALISM_PAID_GENERATION_MAX_USD", "0") or 0)
    if execute and (budget <= 0 or estimated_cost > budget):
        raise RuntimeBlocked(
            "explicit paid-generation budget is missing or insufficient"
        )
    if execute:
        try:
            PaidGenerationAuthorization.from_environment(
                str(audio["provider"]), estimated_cost
            )
        except ProviderExecutionError as exc:
            raise RuntimeBlocked(str(exc)) from exc
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger = GenerationLedger(output_dir / "generation_ledger.json")
    state = ledger.load()
    records: list[dict[str, Any]] = []
    for segment in manifest["segments"]:
        segment_id = str(segment["id"])
        output_path = safe_child(
            output_dir, str(segment.get("output_name") or f"{segment_id}.audio")
        )
        request = GenerationRequest(
            book_slug=str(manifest["slug"]),
            segment_id=segment_id,
            text_ref=str(segment["text"]),
            text=str(segment["text"]),
            language=str(manifest.get("language") or audio.get("language") or ""),
            narrator_profile_id=str(audio.get("voice") or ""),
            voice_source_type=str(audio.get("voice_source_type") or "STYLE_PROFILE"),
            consent_status=str(
                audio.get("consent_status") or "NOT_APPLICABLE_STYLE_PROFILE"
            ),
            dry_run=not execute,
            metadata={
                "estimated_cost_usd": segment.get("estimated_cost_usd"),
                "output_path": str(output_path),
                **audio,
            },
        )
        fingerprint = canonical_hash(
            {
                "request": request.__dict__,
                "manifest": manifest.get("manifest_version", "1"),
            }
        )
        prior = state["segments"].get(segment_id)
        if (
            prior
            and prior.get("request_fingerprint") == fingerprint
            and output_path.is_file()
            and sha256_file(output_path) == prior.get("artifact_sha256")
        ):
            records.append({**prior, "status": "REUSED"})
            continue
        if not execute:
            planned = provider.generate_segment(request)
            records.append(
                {
                    "segment_id": segment_id,
                    "status": planned.status,
                    "request_fingerprint": fingerprint,
                    "cost_estimate_usd": planned.cost_estimate,
                }
            )
            continue
        last_error = ""
        for attempt in range(1, max_retries + 1):
            try:
                result = provider.generate_segment(request)
                if result.status != "PASS" or not output_path.is_file():
                    raise RuntimeBlocked(f"provider did not produce {segment_id}")
                record = {
                    "segment_id": segment_id,
                    "status": "PASS",
                    "attempt": attempt,
                    "request_fingerprint": fingerprint,
                    "artifact_path": str(output_path.relative_to(output_dir)),
                    "artifact_sha256": sha256_file(output_path),
                    "cost_estimate_usd": result.cost_estimate,
                }
                state["segments"][segment_id] = record
                ledger.save(state)
                records.append(record)
                break
            except ProviderExecutionError as exc:
                last_error = str(exc)
                if not exc.retryable or attempt == max_retries:
                    raise RuntimeBlocked(
                        f"{segment_id} failed after {attempt} attempt(s): {last_error}"
                    ) from exc
        else:
            raise RuntimeBlocked(f"{segment_id} failed: {last_error}")
    return {
        "schema": "earnalism.release-generation.v1",
        "slug": manifest["slug"],
        "provider": audio["provider"],
        "model": audio["model"],
        "voice": audio["voice"],
        "estimated_cost_usd": estimated_cost,
        "execute": execute,
        "provider_calls_allowed": execute,
        "segments": records,
        "passed": all(
            row["status"] in {"PASS", "REUSED", "DRY_RUN_PLANNED"} for row in records
        ),
    }


def stage_local(
    manifest: dict[str, Any], generation_dir: Path, staging_dir: Path
) -> dict[str, Any]:
    generation = load_json(generation_dir / "generation_result.json")
    if not generation.get("passed") or generation.get("execute") is not True:
        raise RuntimeBlocked("staging requires a completed generation result")
    release_id = canonical_hash({"manifest": manifest, "generation": generation})
    destination = staging_dir.resolve() / str(manifest["slug"]) / release_id
    receipt_path = destination / "staging_receipt.json"
    if receipt_path.exists():
        receipt = load_json(receipt_path)
        if receipt.get("release_id") == release_id and receipt.get("passed") is True:
            return {**receipt, "reused": True}
    staging_dir.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix="earnalism-stage-", dir=str(staging_dir.resolve()))
    )
    try:
        package = temporary / str(manifest["slug"]) / release_id
        package.mkdir(parents=True, exist_ok=True)
        copied: list[dict[str, Any]] = []
        for item in generation.get("segments") or []:
            if item.get("status") not in {"PASS", "REUSED"}:
                raise RuntimeBlocked("generation result contains an incomplete segment")
            source = safe_child(generation_dir, str(item["artifact_path"]))
            target = package / Path(str(item["artifact_path"])).name
            shutil.copy2(source, target)
            actual = sha256_file(target)
            if actual != item.get("artifact_sha256"):
                raise RuntimeBlocked("staged artifact checksum mismatch")
            copied.append(
                {
                    "segment_id": item["segment_id"],
                    "path": target.name,
                    "sha256": actual,
                }
            )
        receipt = {
            "schema": "earnalism.release-staging-receipt.v1",
            "slug": manifest["slug"],
            "release_id": release_id,
            "release_eligible": False,
            "public": False,
            "objects": copied,
            "passed": True,
        }
        write_json(package / "release_manifest.json", manifest)
        write_json(package / "staging_receipt.json", receipt)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            shutil.rmtree(destination)
        package.replace(destination)
        return receipt
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


class HttpProductionPromoter:
    """Operator-owned promotion endpoint; no default endpoint is assumed."""

    def promote(self, payload: dict[str, Any], *, execute: bool) -> dict[str, Any]:
        if not execute:
            return {"status": "DRY_RUN", "network_calls_performed": 0, "passed": False}
        if (
            os.environ.get("EARNALISM_ENABLE_PRODUCTION_PROMOTION", "").lower()
            != "true"
        ):
            raise RuntimeBlocked(
                "EARNALISM_ENABLE_PRODUCTION_PROMOTION=true is required"
            )
        if (
            os.environ.get("EARNALISM_PRODUCTION_PROMOTION_APPROVED", "").lower()
            != "true"
        ):
            raise RuntimeBlocked(
                "EARNALISM_PRODUCTION_PROMOTION_APPROVED=true is required"
            )
        endpoint = os.environ.get("EARNALISM_PRODUCTION_PROMOTION_ENDPOINT", "").strip()
        token = os.environ.get("EARNALISM_PRODUCTION_PROMOTION_TOKEN", "").strip()
        if not endpoint or not token:
            raise RuntimeBlocked("promotion endpoint and token are required")
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Idempotency-Key": str(payload["promotion_key"]),
            },
        )
        try:
            with urllib.request.urlopen(
                request, timeout=30
            ) as response:  # nosec B310 - explicit operator endpoint.
                result = json.loads(response.read().decode("utf-8"))
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            json.JSONDecodeError,
        ) as exc:
            raise RuntimeBlocked("production promotion endpoint failed") from exc
        if (
            not isinstance(result, dict)
            or result.get("status") != "PROMOTED"
            or result.get("slug") != payload["slug"]
        ):
            raise RuntimeBlocked(
                "promotion response did not prove the requested release"
            )
        return {
            "status": "PROMOTED",
            "network_calls_performed": 1,
            "passed": True,
            "slug": payload["slug"],
        }


def promote(
    manifest: dict[str, Any],
    staging_receipt: dict[str, Any],
    *,
    execute: bool = False,
    promoter: HttpProductionPromoter | None = None,
) -> dict[str, Any]:
    if (
        staging_receipt.get("passed") is not True
        or staging_receipt.get("release_eligible") is not False
    ):
        raise RuntimeBlocked(
            "staging receipt is missing or not a private staging receipt"
        )
    if manifest.get("release_status") != "LIVE":
        raise RuntimeBlocked(
            "the existing release evaluator must report LIVE before promotion"
        )
    if manifest.get("audio_release_gate_status") != "PASS":
        raise RuntimeBlocked(
            "the full audio release gate must be PASS before promotion"
        )
    automated = manifest.get("automated_checks") or {}
    required = (
        "rights",
        "manuscript",
        "reader_artifacts",
        "audio_artifacts",
        "synchronization",
        "checksums",
        "staging",
        "browser",
        "production",
    )
    if any((automated.get(name) or {}).get("status") != "PASS" for name in required):
        raise RuntimeBlocked(
            "all automated release checks must be PASS before promotion"
        )
    if (manifest.get("reader_approval") or {}).get("status") != "APPROVED" or (
        manifest.get("audio_profile_approval") or {}
    ).get("status") != "APPROVED":
        raise RuntimeBlocked(
            "both human approval packets must be APPROVED before promotion"
        )
    payload = {
        "slug": manifest["slug"],
        "release_descriptor_sha256": str(
            manifest.get("release_descriptor_sha256") or canonical_hash(manifest)
        ),
        "staging_release_id": staging_receipt["release_id"],
        "promotion_key": canonical_hash(
            {
                "slug": manifest["slug"],
                "staging_release_id": staging_receipt["release_id"],
            }
        ),
        "reader_exposed": True,
        "audio_exposed": True,
    }
    return (promoter or HttpProductionPromoter()).promote(payload, execute=execute)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate")
    generate.add_argument("--manifest", type=Path, required=True)
    generate.add_argument("--output-dir", type=Path, required=True)
    generate.add_argument("--execute-paid", action="store_true")
    generate.add_argument("--max-retries", type=int, default=3)
    stage = sub.add_parser("stage")
    stage.add_argument("--manifest", type=Path, required=True)
    stage.add_argument("--generation-dir", type=Path, required=True)
    stage.add_argument("--staging-dir", type=Path, required=True)
    promote_parser = sub.add_parser("promote")
    promote_parser.add_argument("--manifest", type=Path, required=True)
    promote_parser.add_argument("--staging-receipt", type=Path, required=True)
    promote_parser.add_argument("--execute", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = load_json(args.manifest)
        if args.command == "generate":
            result = generate_segments(
                manifest,
                args.output_dir,
                execute=args.execute_paid,
                max_retries=args.max_retries,
            )
            write_json(args.output_dir / "generation_result.json", result)
        elif args.command == "stage":
            result = stage_local(manifest, args.generation_dir, args.staging_dir)
        else:
            result = promote(
                manifest, load_json(args.staging_receipt), execute=args.execute
            )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return (
            0
            if result.get("passed") or result.get("status") in {"PROMOTED", "REUSED"}
            else 1
        )
    except (RuntimeBlocked, ProviderExecutionError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "detail": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
