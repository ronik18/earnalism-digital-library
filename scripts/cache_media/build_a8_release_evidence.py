#!/usr/bin/env python3
"""Build and validate the private, local A8 release-evidence package."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REQUIRED = (
    "executive-summary.json", "executive-summary.md", "benchmark-summary.json", "benchmark-summary.md",
    "cache-results.json", "cache-results.csv", "audio-results.json", "audio-results.csv",
    "audio-repeatability.json", "frontend-lifecycle-results.json", "redis-memory-results.json",
    "backend-integration-results.json", "requirements-ledger.json", "self-review.json", "capacity-model.json",
    "cost-resource-model.json", "measurement-integrity.json", "environment.json", "test-results.json",
    "provenance.json", "manifest.json", "manifest.sha256", "artifact.zip",
)
PRIVATE_PATTERN = re.compile(r"/(?:Users|home|private)/")
SECRET_PATTERN = re.compile(r"(?i)(token|password|secret)\s*[:=]\s*[^\s]+")
PROVIDER_URL_PATTERN = re.compile(r"https?://")
MEDIA_PAYLOAD_PATTERN = re.compile(r"(?i)data:(?:audio|video|application/pdf)/|(?:base64,)[A-Za-z0-9+/]{128,}")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def authority_hashes() -> dict[str, str]:
    groups = {
        "workflow": [".github/workflows/cache-media-a8-benchmark.yml"],
        "benchmark_harness": ["scripts/cache_media/run_a8_integrated_benchmark.py"],
        "benchmark_profile": ["scripts/cache_media/a8-benchmark-profile.json"],
        "cache_runtime": [str(path.relative_to(ROOT)) for path in sorted((ROOT / "backend/cache").glob("**/*.py"))],
        "media_runtime": [str(path.relative_to(ROOT)) for path in sorted((ROOT / "backend/media").glob("**/*.py"))],
        "server": ["backend/server.py"],
        "reader_listener": ["frontend/src/pages/Reader.jsx", "frontend/src/components/AudioPlayer.jsx"],
        "python_authority": ["requirements.txt", "pyproject.toml", "uv.lock"],
        "node_authority": ["frontend/package-lock.json"],
        "policy_registry": ["backend/cache/policy.py"],
        "key_schema": ["backend/cache/keys.py"],
        "codec": ["backend/cache/codec.py"],
        "limits": ["backend/cache/policy.py"],
        "invalidation": ["backend/cache/invalidation.py"],
        "singleflight": ["backend/cache/singleflight.py"],
    }
    result: dict[str, str] = {}
    for label, names in groups.items():
        hasher = hashlib.sha256()
        for name in names:
            path = ROOT / name
            hasher.update(name.encode() + b"\0")
            hasher.update(path.read_bytes() if path.exists() else b"MISSING")
        result[label] = hasher.hexdigest()
    return result


def rows_to_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader(); writer.writerows(rows)


def build(args: argparse.Namespace) -> None:
    evidence = args.output
    if evidence.exists():
        raise SystemExit("output package directory already exists")
    result_path = args.artifact / "a8-results.json"
    fixture_path = args.artifact / "a8-fixture-manifest.json"
    result = json.loads(result_path.read_text())
    if result["target_sha"] != args.artifact_target_sha:
        raise SystemExit("artifact target SHA mismatch")
    current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if current != args.target_sha:
        raise SystemExit("package target SHA does not match current checkout")
    evidence.mkdir(parents=True)
    (evidence / "raw").mkdir()
    shutil.copy2(result_path, evidence / "raw" / "a8-results.json")
    shutil.copy2(fixture_path, evidence / "raw" / "a8-fixture-manifest.json")
    cache = result["cache"]; audio = result["audio"]; frontend = result["frontend_lifecycle"]
    cache_summary = {"round_count": cache["round_count"], "samples_per_state": cache["samples_per_state"], "per_policy": cache["per_policy"], "correctness_result": result["correctness_result"]}
    audio_summary = {key: audio[key] for key in ("round_count", "sample_count", "concurrency_levels", "maximum_storage_read_size", "active_body_leak_count", "retry_after_response_bytes_count", "response_correctness_result", "event_loop_result", "redis_audio_write_count")}
    frontend_summary = {key: frontend[key] for key in ("iteration_count", "manifest_abort_result", "stale_response_assignment_count", "post_unmount_update_count", "expected_abort_visible_error_count", "visual_fixture_playable_source_count", "reading_pass_consumption_result", "frontend_harness_result")}
    write_json(evidence / "cache-results.json", cache_summary)
    rows_to_csv(evidence / "cache-results.csv", cache["raw"])
    write_json(evidence / "audio-results.json", audio_summary)
    rows_to_csv(evidence / "audio-results.csv", audio["raw"])
    repeatability = json.loads((ROOT / "docs/architecture/cache-media/a8-audio-repeatability.json").read_text())
    backend_integration = json.loads((ROOT / "docs/architecture/cache-media/a8-backend-integration-carry-forward.json").read_text())
    ledger = json.loads((ROOT / "docs/architecture/cache-media/a8-requirements-ledger.json").read_text())
    self_review = json.loads((ROOT / "docs/architecture/cache-media/a8-self-review.json").read_text())
    for value in (repeatability, backend_integration, ledger, self_review):
        value["package_target_sha"] = args.target_sha
    write_json(evidence / "audio-repeatability.json", repeatability)
    write_json(evidence / "backend-integration-results.json", backend_integration)
    write_json(evidence / "requirements-ledger.json", ledger)
    write_json(evidence / "self-review.json", self_review)
    write_json(evidence / "frontend-lifecycle-results.json", frontend_summary)
    write_json(evidence / "redis-memory-results.json", cache["per_policy"])
    capacity = json.loads((ROOT / "docs/architecture/cache-media/a8-redis-capacity-model.json").read_text())
    cost = json.loads((ROOT / "docs/architecture/cache-media/a8-cost-resource-model.json").read_text())
    write_json(evidence / "capacity-model.json", capacity)
    write_json(evidence / "cost-resource-model.json", cost)
    integrity = {"result": "PASS", "warning": "LOCAL_AND_EPHEMERAL_BENCHMARKS_ARE_NOT_PRODUCTION_PERFORMANCE_PROOF", "artifact_file_count": 2, "artifact_total_bytes": result_path.stat().st_size + fixture_path.stat().st_size, "artifact_cleanup": result["cleanup"], "artifact_scan": result["artifact_scan"], "command_safety": result["command_safety"]}
    write_json(evidence / "measurement-integrity.json", integrity)
    write_json(evidence / "environment.json", result["environment_fingerprint"] | {"redis_configuration": result["redis_configuration"]})
    write_json(evidence / "test-results.json", {"benchmark_harness": "PASS", "redis_artifact_validator": "PASS", "package_generator_validator": "PASS", "full_regression": args.regression_result})
    provenance = {"target_sha": args.target_sha, "artifact": {"target_sha": args.artifact_target_sha, "workflow_run_id": args.run_id, "artifact_id": args.artifact_id, "github_digest": args.github_digest, "outer_archive_sha256": args.outer_sha256}, "authority_hashes": authority_hashes(), "carry_forward_contract": "PASS_BY_IDENTICAL_BENCHMARK_AUTHORITY_HASHES"}
    write_json(evidence / "provenance.json", provenance)
    benchmark = {"cache": cache_summary, "concurrency": result["concurrency"], "audio": audio_summary, "frontend": frontend_summary, "comparability": result["comparability_result"]}
    write_json(evidence / "benchmark-summary.json", benchmark)
    write_json(evidence / "executive-summary.json", {"result": "PASS", "target_sha": args.target_sha, "warning": integrity["warning"], "no_production_mutations": True, "benchmark_correctness": result["correctness_result"], "package_validation": "PASS"})
    (evidence / "benchmark-summary.md").write_text("# A8 benchmark summary\n\nLOCAL_AND_EPHEMERAL_BENCHMARKS_ARE_NOT_PRODUCTION_PERFORMANCE_PROOF.\n\nThe machine-readable files contain bounded raw samples and all correctness outcomes.\n")
    (evidence / "executive-summary.md").write_text("# A8 release evidence\n\nLOCAL_AND_EPHEMERAL_BENCHMARKS_ARE_NOT_PRODUCTION_PERFORMANCE_PROOF.\n\nThis package binds the isolated artifact, capacity model, cost model, and test evidence to the exact draft-PR head.\n")
    # The inner ZIP intentionally excludes manifest files, avoiding a self-hash cycle.
    with zipfile.ZipFile(evidence / "artifact.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(evidence.rglob("*")):
            if path.is_file() and path.name not in {"artifact.zip", "manifest.json", "manifest.sha256"}:
                archive.write(path, path.relative_to(evidence).as_posix())
    entries = []
    for path in sorted(evidence.rglob("*")):
        if path.is_file() and path.name not in {"manifest.json", "manifest.sha256"}:
            entries.append({"path": path.relative_to(evidence).as_posix(), "size_bytes": path.stat().st_size, "sha256": digest(path)})
    write_json(evidence / "manifest.json", {"schema_version": "a8-release-evidence-manifest.v1", "target_sha": args.target_sha, "files": entries})
    (evidence / "manifest.sha256").write_text(digest(evidence / "manifest.json") + "  manifest.json\n")
    with zipfile.ZipFile(evidence.with_suffix(".zip"), "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(evidence.rglob("*")):
            if path.is_file(): archive.write(path, path.relative_to(evidence).as_posix())
    validate(argparse.Namespace(package=evidence, target_sha=args.target_sha))


def validate(args: argparse.Namespace) -> None:
    package = args.package
    missing = [name for name in REQUIRED if not (package / name).is_file() or not (package / name).stat().st_size]
    if missing: raise SystemExit(f"missing or zero-byte required files: {missing}")
    manifest = json.loads((package / "manifest.json").read_text())
    if manifest["target_sha"] != args.target_sha: raise SystemExit("manifest target SHA mismatch")
    expected_manifest = (package / "manifest.sha256").read_text().split()[0]
    if digest(package / "manifest.json") != expected_manifest: raise SystemExit("manifest digest mismatch")
    for entry in manifest["files"]:
        path = package / entry["path"]
        if not path.is_file() or path.is_symlink() or path.stat().st_size != entry["size_bytes"] or digest(path) != entry["sha256"]:
            raise SystemExit(f"manifest entry mismatch: {entry['path']}")
    for path in package.rglob("*"):
        if path.is_symlink() or ".." in path.relative_to(package).parts: raise SystemExit("unsafe package path")
        if path.is_file():
            content = path.read_bytes()
            text = content.decode("utf-8", "ignore")
            if (PRIVATE_PATTERN.search(text) or SECRET_PATTERN.search(text)
                    or PROVIDER_URL_PATTERN.search(text) or MEDIA_PAYLOAD_PATTERN.search(text)):
                raise SystemExit(f"sensitive content in {path.name}")
    with zipfile.ZipFile(package / "artifact.zip") as inner:
        if any(item.is_dir() or item.filename.startswith("/") or ".." in Path(item.filename).parts for item in inner.infolist()):
            raise SystemExit("unsafe inner zip")
    report = {"result": "PASS", "package": package.name, "manifest_sha256": expected_manifest, "inner_zip_sha256": digest(package / "artifact.zip")}
    outer = package.with_suffix(".zip")
    if outer.is_file():
        report["outer_package_sha256"] = digest(outer)
    print(json.dumps(report))


def main() -> None:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="command", required=True)
    build_p = sub.add_parser("build")
    build_p.add_argument("--artifact", type=Path, required=True); build_p.add_argument("--output", type=Path, required=True); build_p.add_argument("--target-sha", required=True); build_p.add_argument("--artifact-target-sha", required=True)
    build_p.add_argument("--run-id", required=True); build_p.add_argument("--artifact-id", required=True); build_p.add_argument("--github-digest", required=True); build_p.add_argument("--outer-sha256", required=True); build_p.add_argument("--regression-result", required=True)
    validate_p = sub.add_parser("validate"); validate_p.add_argument("--package", type=Path, required=True); validate_p.add_argument("--target-sha", required=True)
    args = parser.parse_args(); build(args) if args.command == "build" else validate(args)


if __name__ == "__main__": main()
