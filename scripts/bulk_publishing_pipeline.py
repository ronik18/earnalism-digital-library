#!/usr/bin/env python3
"""Bulk publishing pipeline for Earnalism books.

The pipeline is intentionally an orchestrator. It reuses the existing
book importer, Agentic AI preparation script, production gate workflow,
and k6 smoke script instead of duplicating their logic.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "book_import_manifest.json"
DEFAULT_RUN_ROOT = ROOT / "output" / "bulk_publishing_pipeline"
DEFAULT_API_URL = "https://api.theearnalism.com"
DEFAULT_FRONTEND_URL = "https://theearnalism.com"
AGENTIC_TITLE = "Agentic AI With Python"
AGENTIC_SLUG_UNDERSCORE = "agentic_ai_with_python"


@dataclass
class PhaseResult:
    name: str
    status: str
    detail: str = ""
    command: list[str] = field(default_factory=list)
    returncode: int | None = None
    log_path: str = ""
    artifacts: dict[str, str] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in {"passed", "skipped"}


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def shell_join(command: Sequence[str]) -> str:
    return " ".join(command)


def manifest_path(value: str | None) -> Path:
    return Path(value).expanduser().resolve() if value else DEFAULT_MANIFEST


def strip_api_suffix(api_url: str) -> str:
    value = (api_url or DEFAULT_API_URL).rstrip("/")
    return value[:-4] if value.endswith("/api") else value


def latest_file(base: Path, filename: str) -> Path | None:
    if not base.exists():
        return None
    candidates = [path for path in base.rglob(filename) if path.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def run_phase(
    name: str,
    command: Sequence[str],
    log_path: Path,
    env: dict[str, str] | None = None,
    allowed_returncodes: Iterable[int] = (0,),
) -> PhaseResult:
    print(f"\n=== {name} ===")
    print("+", shell_join(command))
    proc = subprocess.run(
        list(command),
        cwd=str(ROOT),
        env=env or os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    write_text(log_path, proc.stdout)
    status = "passed" if proc.returncode in set(allowed_returncodes) else "failed"
    detail = "completed" if status == "passed" else f"exited with {proc.returncode}; see {rel(log_path)}"
    return PhaseResult(
        name=name,
        status=status,
        detail=detail,
        command=list(command),
        returncode=proc.returncode,
        log_path=rel(log_path),
    )


def check_agentic_package(root: Path, run_dir: Path) -> PhaseResult:
    package = root / "final_package"
    report = package / "reports" / "final_publication_readiness_report.md"
    metadata = package / "book_metadata.json"
    required_files = [
        package / f"{AGENTIC_SLUG_UNDERSCORE}_publication_ready.md",
        package / f"{AGENTIC_SLUG_UNDERSCORE}_publication_ready.docx",
        package / f"{AGENTIC_SLUG_UNDERSCORE}_publication_ready.pdf",
        report,
        metadata,
    ]
    errors: list[str] = []
    checks: dict[str, bool] = {}

    for path in required_files:
        checks[f"exists:{rel(path)}"] = path.exists()
        if not path.exists():
            errors.append(f"missing {rel(path)}")

    if metadata.exists():
        try:
            meta = read_json(metadata)
            checks["metadata:title"] = meta.get("title") == AGENTIC_TITLE
            checks["metadata:draft"] = meta.get("is_published") is False and meta.get("availability") == "draft"
            checks["metadata:audiobook_disabled"] = meta.get("audiobook_enabled") is False and meta.get("generate_audiobook") is False
        except Exception as exc:  # noqa: BLE001 - report the malformed artifact
            errors.append(f"metadata unreadable: {exc}")

    if report.exists():
        text = report.read_text(encoding="utf-8")
        required_lines = [
            "DOCX opens/generated: success",
            "DOCX structural open check: success",
            "PDF generated: success",
            "PDF structural open check: success",
            "Audiobook disabled: yes",
            "Secret-like strings in final package: 0",
            "Code fences balanced: yes",
            "Live publishing triggered: no",
        ]
        for line in required_lines:
            ok = line in text
            checks[f"readiness:{line}"] = ok
            if not ok:
                errors.append(f"readiness report missing `{line}`")

    for key, ok in checks.items():
        if not ok and key.startswith("metadata:"):
            errors.append(f"Agentic AI {key} check failed")

    artifact = run_dir / "agentic_ai_readiness_check.json"
    payload = {
        "title": AGENTIC_TITLE,
        "checked_at": now_iso(),
        "ok": not errors,
        "checks": checks,
        "errors": errors,
    }
    write_json(artifact, payload)
    return PhaseResult(
        name="agentic_ai_readiness",
        status="passed" if not errors else "failed",
        detail="publication package is ready" if not errors else "; ".join(errors[:5]),
        artifacts={"readiness_check": rel(artifact), "readiness_report": rel(report)},
        data=payload,
    )


def build_prepare_agentic_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        "scripts/prepare_technical_book.py",
        "--docx",
        str(args.agentic_docx),
        "--root",
        str(ROOT),
    ]


def build_import_validation_command(args: argparse.Namespace, output_base: Path) -> list[str]:
    return [
        sys.executable,
        "scripts/import_books.py",
        str(args.manifest),
        "--output-dir",
        str(output_base),
    ]


def build_production_command(args: argparse.Namespace, production_base: Path) -> list[str]:
    command = [
        sys.executable,
        "scripts/book_production_workflow.py",
        "--manifest",
        str(args.manifest),
        "--api-url",
        args.api_url,
        "--frontend-url",
        args.frontend_url,
        "--audio-output-dir",
        str(args.audio_output_dir),
        "--public-audio-dir",
        str(args.public_audio_dir),
        "--run-output-dir",
        str(production_base),
    ]
    if args.stage == "upload-drafts":
        command.append("--upload-drafts")
    if args.stage == "publish":
        command.append("--publish-approved")
    if args.update_existing_drafts:
        command.append("--update-existing-drafts")
    if args.all_drafts:
        command.append("--all-drafts")
    for slug in args.book_slug:
        command.extend(["--book-slug", slug])
    if args.skip_audio:
        command.append("--skip-audio")
    if args.skip_qa:
        command.append("--skip-qa")
    if args.trust_existing_admin_rights:
        command.append("--trust-existing-admin-rights")
    for env_file in args.env_file:
        command.extend(["--env-file", str(env_file)])
    return command


def enrich_import_phase(phase: PhaseResult, output_base: Path, allow_skipped: bool) -> PhaseResult:
    report_path = latest_file(output_base, "dry_run_report.json")
    if not report_path:
        phase.status = "failed"
        phase.detail = "dry-run report was not produced"
        return phase
    report = read_json(report_path)
    skipped = report.get("skipped_books") or []
    uploaded = report.get("uploaded_books") or []
    phase.artifacts["dry_run_report"] = rel(report_path)
    phase.data = {
        "total_books": report.get("total_books", 0),
        "passed_validation_count": report.get("passed_validation_count", 0),
        "skipped_count": report.get("skipped_count", 0),
        "uploaded_books": uploaded,
        "skipped_books": skipped,
    }
    if skipped and not allow_skipped:
        phase.status = "failed"
        phase.detail = f"{len(skipped)} book(s) skipped validation; see {rel(report_path)}"
    elif phase.status == "passed":
        phase.detail = f"{report.get('passed_validation_count', 0)}/{report.get('total_books', 0)} book(s) passed validation"
    return phase


def enrich_production_phase(phase: PhaseResult, production_base: Path, allow_skipped_imports: bool) -> PhaseResult:
    report_path = latest_file(production_base, "book_production_report.json")
    if not report_path:
        phase.status = "failed"
        phase.detail = "production report was not produced"
        return phase
    report = read_json(report_path)
    upload_report_path = latest_file(production_base, "upload_report.json")
    upload_report = read_json(upload_report_path) if upload_report_path else {}
    results = report.get("results") or []
    no_go = [item for item in results if item.get("verdict") != "GO"]
    published = report.get("published") or []
    phase.artifacts["production_report"] = rel(report_path)
    md_path = report_path.with_suffix(".md")
    if md_path.exists():
        phase.artifacts["production_report_md"] = rel(md_path)
    if upload_report_path:
        phase.artifacts["import_upload_report"] = rel(upload_report_path)
    phase.data = {
        "publish_approved": report.get("publish_approved", False),
        "published": published,
        "uploaded_books": upload_report.get("uploaded_books") or [],
        "skipped_books": upload_report.get("skipped_books") or [],
        "go_books": [
            {"slug": item.get("slug"), "title": item.get("title")}
            for item in results
            if item.get("verdict") == "GO"
        ],
        "no_go_books": [
            {
                "slug": item.get("slug"),
                "title": item.get("title"),
                "failed_gates": [
                    gate
                    for gate in item.get("gates", [])
                    if not gate.get("ok")
                ],
            }
            for item in no_go
        ],
    }
    skipped_imports = phase.data["skipped_books"]
    if skipped_imports and not allow_skipped_imports:
        phase.status = "failed"
        phase.detail = f"{len(skipped_imports)} import book(s) skipped during draft upload"
    elif no_go:
        phase.status = "failed"
        phase.detail = f"{len(no_go)} book(s) blocked by production gates"
    elif phase.status == "passed":
        phase.detail = f"{len(results)} book(s) passed production gates"
        if phase.data["uploaded_books"]:
            phase.detail += f"; uploaded {len(phase.data['uploaded_books'])} draft(s)"
        if published:
            phase.detail += f"; published {len(published)}"
    return phase


def run_k6_phase(args: argparse.Namespace, run_dir: Path) -> PhaseResult:
    k6 = shutil.which("k6")
    if not k6:
        status = "failed" if args.require_k6 else "skipped"
        detail = "k6 is not installed"
        return PhaseResult(name="k6_smoke", status=status, detail=detail)

    env = os.environ.copy()
    env.update(
        {
            "FRONTEND_URL": args.frontend_url,
            "API_URL": strip_api_suffix(args.api_url),
            "K6_HTTP_P95_THRESHOLD": args.k6_http_p95_threshold,
            "K6_SMOKE_VUS": str(args.k6_smoke_vus),
            "K6_SMOKE_ITERATIONS": str(args.k6_smoke_iterations),
        }
    )
    return run_phase(
        "k6_smoke",
        [k6, "run", "scripts/k6_smoke.js"],
        run_dir / "logs" / "k6_smoke.log",
        env=env,
    )


def pipeline_decision(stage: str, phases: Sequence[PhaseResult]) -> str:
    failures = [phase for phase in phases if phase.status == "failed"]
    if failures:
        return "BLOCKED"
    if stage == "publish":
        published = any(phase.data.get("published") for phase in phases)
        return "PUBLISHED" if published else "PUBLISH_GATES_PASSED"
    if stage == "upload-drafts":
        return "DRAFTS_STAGED_FOR_HUMAN_REVIEW"
    return "PREFLIGHT_PASSED"


def render_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Bulk Publishing Pipeline Report",
        "",
        f"Generated: {report['generated_at']}",
        f"Stage: `{report['stage']}`",
        f"Decision: **{report['decision']}**",
        "",
        "## Phases",
        "",
    ]
    for phase in report["phases"]:
        lines.append(f"- {phase['status'].upper()} `{phase['name']}`: {phase.get('detail') or ''}")
        if phase.get("log_path"):
            lines.append(f"  Log: `{phase['log_path']}`")
        for artifact_name, artifact_path in sorted((phase.get("artifacts") or {}).items()):
            lines.append(f"  {artifact_name}: `{artifact_path}`")

    uploaded = report.get("uploaded_books") or []
    skipped = report.get("skipped_books") or []
    published = report.get("published") or []
    go_books = report.get("go_books") or []
    no_go_books = report.get("no_go_books") or []

    if uploaded:
        lines.extend(["", "## Uploaded Drafts", ""])
        for book in uploaded:
            lines.append(f"- `{book.get('slug', '')}` {book.get('title', '')} id=`{book.get('id', '')}`")
    if published:
        lines.extend(["", "## Published", ""])
        for slug in published:
            lines.append(f"- `{slug}`")
    if go_books:
        lines.extend(["", "## GO Books", ""])
        for book in go_books:
            lines.append(f"- `{book.get('slug')}` {book.get('title')}")
    if skipped:
        lines.extend(["", "## Skipped Import Books", ""])
        for item in skipped:
            reasons = "; ".join(item.get("reasons") or ["unknown reason"])
            lines.append(f"- {item.get('title') or item.get('index')}: {reasons}")
    if no_go_books:
        lines.extend(["", "## Blocked Books", ""])
        for item in no_go_books:
            lines.append(f"- `{item.get('slug')}` {item.get('title')}")
            for gate in item.get("failed_gates") or []:
                lines.append(f"  FAIL `{gate.get('name')}`: {gate.get('detail')}")

    if report["stage"] != "publish":
        lines.extend(
            [
                "",
                "## Approval",
                "",
                "Live publishing remains blocked. Publish only by rerunning stage `publish` with `PUBLISH_LIVE=1` and `HUMAN_APPROVED=1` after reviewing the reports.",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def collect_summary(phases: Sequence[PhaseResult]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "uploaded_books": [],
        "skipped_books": [],
        "published": [],
        "go_books": [],
        "no_go_books": [],
    }
    for phase in phases:
        data = phase.data or {}
        summary["uploaded_books"].extend(data.get("uploaded_books") or [])
        summary["skipped_books"].extend(data.get("skipped_books") or [])
        summary["published"].extend(data.get("published") or [])
        summary["go_books"].extend(data.get("go_books") or [])
        summary["no_go_books"].extend(data.get("no_go_books") or [])
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automate Earnalism bulk book publishing phases.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Book import manifest. Defaults to ./book_import_manifest.json.")
    parser.add_argument("--stage", choices=["preflight", "upload-drafts", "publish"], default="preflight")
    parser.add_argument("--run-output-dir", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--api-url", default=os.environ.get("EARNALISM_API_URL", DEFAULT_API_URL))
    parser.add_argument("--frontend-url", default=os.environ.get("EARNALISM_FRONTEND_URL", DEFAULT_FRONTEND_URL))
    parser.add_argument("--audio-output-dir", type=Path, default=ROOT / "audio_output")
    parser.add_argument("--public-audio-dir", type=Path, default=ROOT / "frontend/public/audio")
    parser.add_argument("--all-drafts", action="store_true", help="Process every unpublished admin draft during production gates.")
    parser.add_argument("--book-slug", action="append", default=[], help="Specific draft slug to gate/publish. Repeatable.")
    parser.add_argument("--update-existing-drafts", action="store_true")
    parser.add_argument("--skip-audio", action="store_true")
    parser.add_argument("--skip-qa", action="store_true")
    parser.add_argument("--skip-import-validation", action="store_true", help="Skip importer dry-run during preflight.")
    parser.add_argument("--skip-production-gates", action="store_true", help="Skip admin production gates during preflight.")
    parser.add_argument("--allow-skipped-imports", action="store_true", help="Do not fail preflight if importer skips a manifest item.")
    parser.add_argument("--trust-existing-admin-rights", action="store_true")
    parser.add_argument("--env-file", action="append", type=Path, default=[ROOT / ".secrets/earnalism-import.env", ROOT / ".secrets/earnalism-audio.env"])
    parser.add_argument("--agentic-ai-mode", choices=["check", "prepare", "skip"], default="check")
    parser.add_argument("--agentic-docx", type=Path, default=ROOT / "source" / "agentic_ai_with_python_manuscript.docx")
    parser.add_argument("--run-k6-smoke", action="store_true", help="Run scripts/k6_smoke.js after the pipeline gates.")
    parser.add_argument("--require-k6", action="store_true", help="Fail instead of skip when --run-k6-smoke is set and k6 is unavailable.")
    parser.add_argument("--k6-http-p95-threshold", default=os.environ.get("K6_HTTP_P95_THRESHOLD", "p(95)<5000"))
    parser.add_argument("--k6-smoke-vus", type=int, default=int(os.environ.get("K6_SMOKE_VUS", "1")))
    parser.add_argument("--k6-smoke-iterations", type=int, default=int(os.environ.get("K6_SMOKE_ITERATIONS", "3")))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.manifest = manifest_path(str(args.manifest))
    args.agentic_docx = args.agentic_docx.expanduser().resolve()
    args.audio_output_dir = args.audio_output_dir.expanduser().resolve()
    args.public_audio_dir = args.public_audio_dir.expanduser().resolve()

    run_dir = args.run_output_dir.expanduser().resolve() / utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)

    phases: list[PhaseResult] = []

    if args.agentic_ai_mode == "prepare":
        phases.append(
            run_phase(
                "agentic_ai_prepare",
                build_prepare_agentic_command(args),
                run_dir / "logs" / "agentic_ai_prepare.log",
            )
        )
        phases.append(check_agentic_package(ROOT, run_dir))
    elif args.agentic_ai_mode == "check":
        phases.append(check_agentic_package(ROOT, run_dir))
    else:
        phases.append(PhaseResult(name="agentic_ai_readiness", status="skipped", detail="skipped by operator"))

    if args.stage == "preflight" and not args.skip_import_validation:
        import_base = run_dir / "import_validation"
        phase = run_phase(
            "import_dry_run",
            build_import_validation_command(args, import_base),
            run_dir / "logs" / "import_dry_run.log",
        )
        phases.append(enrich_import_phase(phase, import_base, args.allow_skipped_imports))
    elif args.stage == "preflight":
        phases.append(PhaseResult(name="import_dry_run", status="skipped", detail="skipped by operator"))

    if not (args.stage == "preflight" and args.skip_production_gates):
        production_base = run_dir / "production"
        phase = run_phase(
            "production_gates",
            build_production_command(args, production_base),
            run_dir / "logs" / "production_gates.log",
            allowed_returncodes=(0,),
        )
        phases.append(enrich_production_phase(phase, production_base, args.allow_skipped_imports))
    else:
        phases.append(PhaseResult(name="production_gates", status="skipped", detail="skipped by operator"))

    if args.run_k6_smoke:
        phases.append(run_k6_phase(args, run_dir))

    phase_payloads = [
        {
            "name": phase.name,
            "status": phase.status,
            "detail": phase.detail,
            "command": phase.command,
            "returncode": phase.returncode,
            "log_path": phase.log_path,
            "artifacts": phase.artifacts,
            "data": phase.data,
        }
        for phase in phases
    ]
    report = {
        "generated_at": now_iso(),
        "stage": args.stage,
        "manifest": rel(args.manifest),
        "decision": pipeline_decision(args.stage, phases),
        "phases": phase_payloads,
        **collect_summary(phases),
    }
    report_json = run_dir / "bulk_pipeline_report.json"
    report_md = run_dir / "bulk_pipeline_report.md"
    write_json(report_json, report)
    write_text(report_md, render_markdown_report(report))

    print("\nBulk publishing pipeline")
    print("========================")
    print(f"Decision: {report['decision']}")
    for phase in phases:
        print(f"{phase.status.upper()}: {phase.name} - {phase.detail}")
    if report.get("published"):
        print("Published slugs:")
        for slug in report["published"]:
            print(f"  - {slug}")
    if report.get("skipped_books"):
        print("Skipped import books:")
        for item in report["skipped_books"]:
            reasons = "; ".join(item.get("reasons") or ["unknown reason"])
            print(f"  - {item.get('title') or item.get('index')}: {reasons}")
    print(f"Report: {report_md}")
    return 0 if all(phase.ok for phase in phases) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
