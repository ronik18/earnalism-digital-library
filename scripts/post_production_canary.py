#!/usr/bin/env python3
"""Run Earnalism post-production canaries and write an owner summary."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "output" / "release-canary"
WARNING_RE = re.compile(r"\bWARN(?:ING)?\b", re.IGNORECASE)
BENIGN_WARNING_PATTERNS = [
    re.compile(r"Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set\.", re.IGNORECASE),
    re.compile(r"\(Use `node --trace-warnings(?: \.\.\.)?` to show where the warning was created\)", re.IGNORECASE),
]


@dataclass(frozen=True)
class CanaryCommand:
    key: str
    label: str
    command: str
    critical: bool = True
    required_paths: tuple[str, ...] = ()


@dataclass
class CanaryResult:
    key: str
    label: str
    command: str
    critical: bool
    status: str
    returncode: int
    duration_seconds: float
    log_file: str
    warning_detected: bool


COMMANDS: list[CanaryCommand] = [
    CanaryCommand(
        key="route_canary",
        label="Route canary",
        command="npm run launch:post-deploy-route-canary",
    ),
    CanaryCommand(
        key="backend_catalog_truth",
        label="Backend catalog truth",
        command="npm run launch:backend-catalog-truth-canary",
    ),
    CanaryCommand(
        key="production_parity",
        label="Production parity",
        command="npm run launch:production-parity",
    ),
    CanaryCommand(
        key="controlled_publication",
        label="Controlled publication precheck",
        command="npm run controlled-publication:precheck",
    ),
    CanaryCommand(
        key="payment_smoke",
        label="Payment smoke",
        command="npm run launch:payment-smoke",
    ),
    CanaryCommand(
        key="seo",
        label="SEO audit",
        command="npm run launch:seo-audit",
        critical=False,
    ),
    CanaryCommand(
        key="social_preview_prod",
        label="Production social preview",
        command="npm run launch:social-preview-audit:prod",
        critical=False,
    ),
    CanaryCommand(
        key="audio",
        label="Audio audit",
        command="npm run launch:audio-audit",
        critical=False,
    ),
    CanaryCommand(
        key="catalog_truth",
        label="Owner catalog truth audit",
        command="npm run owner:catalog-truth-audit",
        critical=False,
    ),
    CanaryCommand(
        key="daily_growth_audit",
        label="Owner daily growth audit",
        command="npm run owner:daily-growth-audit",
        critical=False,
    ),
    CanaryCommand(
        key="observability",
        label="Observability audit",
        command="npm run observability:audit",
        critical=False,
    ),
    CanaryCommand(
        key="regression",
        label="Focused regression",
        command=(
            "npm run regression -- "
            "modules/13-public-content-governance.test.js "
            "modules/14-ux-conversion-static.test.js"
        ),
    ),
    CanaryCommand(
        key="frontend_build",
        label="Frontend build",
        command="npm --prefix frontend run build",
    ),
    CanaryCommand(
        key="ux_go_no_go",
        label="Real-user UX go/no-go",
        command="npm run release:ux-go-no-go",
        critical=False,
        required_paths=(
            "tests/e2e/earnalism-real-user-journey.spec.js",
            "scripts/generate_real_user_ux_report.py",
        ),
    ),
]


Runner = Callable[..., subprocess.CompletedProcess[str]]


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def utc_timestamp() -> str:
    return time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())


def command_status(command: CanaryCommand, returncode: int, output: str) -> tuple[str, bool]:
    warning_scan_output = "\n".join(
        line
        for line in output.splitlines()
        if not any(pattern.search(line) for pattern in BENIGN_WARNING_PATTERNS)
    )
    warning_detected = bool(WARNING_RE.search(warning_scan_output))
    if returncode == 0:
        if warning_detected and not command.critical:
            return "WARN", warning_detected
        return "PASS", warning_detected
    if command.critical:
        return "FAIL", warning_detected
    return "WARN", True


def run_command(
    command: CanaryCommand,
    *,
    index: int,
    run_dir: Path,
    runner: Runner = subprocess.run,
) -> CanaryResult:
    start = time.monotonic()
    missing_required_paths = [path for path in command.required_paths if not (ROOT / path).exists()]
    if missing_required_paths:
        log_file = run_dir / f"{index:02d}-{command.key}.log"
        log_file.write_text(
            "\n".join(
                [
                    f"$ {command.command}",
                    "",
                    "SKIPPED:",
                    f"Missing optional required files: {', '.join(missing_required_paths)}",
                ]
            ),
            encoding="utf-8",
        )
        return CanaryResult(
            key=command.key,
            label=command.label,
            command=command.command,
            critical=command.critical,
            status="SKIP",
            returncode=0,
            duration_seconds=round(time.monotonic() - start, 3),
            log_file=display_path(log_file),
            warning_detected=False,
        )

    completed = runner(
        command.command,
        cwd=ROOT,
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )
    duration = time.monotonic() - start
    output = "\n".join(
        part
        for part in (
            f"$ {command.command}",
            "",
            "STDOUT:",
            completed.stdout or "",
            "",
            "STDERR:",
            completed.stderr or "",
        )
        if part is not None
    )
    log_file = run_dir / f"{index:02d}-{command.key}.log"
    log_file.write_text(output, encoding="utf-8")
    status, warning_detected = command_status(command, completed.returncode, output)
    return CanaryResult(
        key=command.key,
        label=command.label,
        command=command.command,
        critical=command.critical,
        status=status,
        returncode=completed.returncode,
        duration_seconds=round(duration, 3),
        log_file=display_path(log_file),
        warning_detected=warning_detected,
    )


def overall_status(results: Sequence[CanaryResult]) -> str:
    if any(result.status == "FAIL" and result.critical for result in results):
        return "FAIL"
    if any(result.status == "WARN" for result in results):
        return "WARN"
    return "PASS"


def failed_command(results: Sequence[CanaryResult]) -> str:
    for result in results:
        if result.status == "FAIL" and result.critical:
            return result.command
    return ""


def owner_recommendation(status: str, results: Sequence[CanaryResult]) -> str:
    if status == "PASS":
        return "KEEP_DRACULA_LIVE"
    rollback_keys = {
        "route_canary",
        "production_parity",
        "controlled_publication",
        "regression",
        "frontend_build",
    }
    if any(result.status == "FAIL" and result.key in rollback_keys for result in results):
        return "ROLLBACK"
    return "HOLD_FOR_FIXES"


def result_status(results: Sequence[CanaryResult], key: str) -> str:
    for result in results:
        if result.key == key:
            return result.status
    return "NOT_RUN"


def dracula_live_status(results: Sequence[CanaryResult]) -> str:
    critical_keys = {"backend_catalog_truth", "controlled_publication"}
    statuses = [result.status for result in results if result.key in critical_keys]
    if any(status == "FAIL" for status in statuses):
        return "FAIL"
    if any(status == "WARN" for status in statuses):
        return "WARN"
    return "PASS" if statuses else "NOT_RUN"


def build_summary(run_dir: Path, results: Sequence[CanaryResult]) -> dict[str, object]:
    status = overall_status(results)
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_dir": display_path(run_dir),
        "overall_status": status,
        "failed_command": failed_command(results),
        "route_canary_status": result_status(results, "route_canary"),
        "backend_catalog_truth_status": result_status(results, "backend_catalog_truth"),
        "dracula_live_status": dracula_live_status(results),
        "payment_smoke_status": result_status(results, "payment_smoke"),
        "seo_status": result_status(results, "seo"),
        "social_preview_prod_status": result_status(results, "social_preview_prod"),
        "audio_status": result_status(results, "audio"),
        "catalog_truth_status": result_status(results, "catalog_truth"),
        "daily_growth_audit_status": result_status(results, "daily_growth_audit"),
        "observability_status": result_status(results, "observability"),
        "regression_status": result_status(results, "regression"),
        "frontend_build_status": result_status(results, "frontend_build"),
        "ux_go_no_go_status": result_status(results, "ux_go_no_go"),
        "owner_recommendation": owner_recommendation(status, results),
        "public_mutation_performed": False,
        "paid_provider_calls_performed": False,
        "audiobook_enabled": False,
        "emails_or_social_posts_sent": False,
        "commands": [asdict(result) for result in results],
    }


def markdown_summary(summary: dict[str, object]) -> str:
    commands = summary.get("commands")
    rows = [
        "# Post-Production Canary Summary",
        "",
        f"Overall Status: `{summary['overall_status']}`",
        f"Owner Recommendation: `{summary['owner_recommendation']}`",
        f"Generated At: `{summary['generated_at']}`",
        f"Run Directory: `{summary['run_dir']}`",
        "",
        "This command is local-report only. It does not publish content, enable audiobook, send email or social posts, call paid provider APIs, or mutate production data.",
        "",
        "## Owner Status",
        "",
        f"- Failed command: `{summary['failed_command'] or 'none'}`",
        f"- Route canary: `{summary['route_canary_status']}`",
        f"- Backend catalog truth: `{summary['backend_catalog_truth_status']}`",
        f"- Dracula live: `{summary['dracula_live_status']}`",
        f"- Payment smoke: `{summary['payment_smoke_status']}`",
        f"- SEO: `{summary['seo_status']}`",
        f"- Production social preview: `{summary['social_preview_prod_status']}`",
        f"- Audio: `{summary['audio_status']}`",
        f"- Catalog truth: `{summary['catalog_truth_status']}`",
        f"- Daily growth audit: `{summary['daily_growth_audit_status']}`",
        f"- Observability: `{summary['observability_status']}`",
        f"- Regression: `{summary['regression_status']}`",
        f"- Frontend build: `{summary['frontend_build_status']}`",
        f"- Real-user UX go/no-go: `{summary['ux_go_no_go_status']}`",
        "",
        "## Command Results",
        "",
        "| Step | Status | Critical | Return Code | Log |",
        "| --- | --- | --- | --- | --- |",
    ]
    if isinstance(commands, list):
        for command in commands:
            if isinstance(command, dict):
                rows.append(
                    "| {label} | `{status}` | {critical} | {returncode} | `{log}` |".format(
                        label=command.get("label", ""),
                        status=command.get("status", ""),
                        critical=command.get("critical", ""),
                        returncode=command.get("returncode", ""),
                        log=command.get("log_file", ""),
                    )
                )
    rows.extend(
        [
            "",
            "## Safety Confirmation",
            "",
            "- Public publishing: disabled",
            "- Audiobook enablement: disabled",
            "- Email/social sending: disabled",
            "- Paid provider calls: disabled",
            "- Production data mutation: disabled",
            "",
        ]
    )
    return "\n".join(rows)


def write_summary(run_dir: Path, output_root: Path, summary: dict[str, object]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    summary_json = json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
    summary_md = markdown_summary(summary)
    (run_dir / "summary.json").write_text(summary_json, encoding="utf-8")
    (run_dir / "summary.md").write_text(summary_md, encoding="utf-8")

    latest_dir = output_root / "latest"
    if latest_dir.exists() and latest_dir.is_symlink():
        latest_dir.unlink()
    latest_dir.mkdir(parents=True, exist_ok=True)
    (latest_dir / "summary.json").write_text(summary_json, encoding="utf-8")
    (latest_dir / "summary.md").write_text(summary_md, encoding="utf-8")


def run_post_production_canary(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    timestamp: str | None = None,
    runner: Runner = subprocess.run,
) -> dict[str, object]:
    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = output_root / (timestamp or utc_timestamp())
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)

    results = [
        run_command(command, index=index, run_dir=run_dir, runner=runner)
        for index, command in enumerate(COMMANDS, start=1)
    ]
    summary = build_summary(run_dir, results)
    write_summary(run_dir, output_root, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--timestamp", help="Optional deterministic timestamp for test or manual rerun output.")
    args = parser.parse_args()

    summary = run_post_production_canary(output_root=args.output_root, timestamp=args.timestamp)
    print(markdown_summary(summary))
    return 1 if summary["overall_status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
