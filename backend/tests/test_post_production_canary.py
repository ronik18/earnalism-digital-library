from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts import post_production_canary


def fake_runner(failures=None, warnings=None):
    failures = failures or {}
    warnings = warnings or set()

    def run(command, **_kwargs):
        return subprocess.CompletedProcess(
            args=command,
            returncode=failures.get(command, 0),
            stdout="WARNING: non-critical observation\n" if command in warnings else "ok\n",
            stderr="boom\n" if command in failures else "",
        )

    return run


def run_canary(tmp_path: Path, *, failures=None, warnings=None):
    return post_production_canary.run_post_production_canary(
        output_root=tmp_path / "release-canary",
        timestamp="2026-06-20-10-30-00",
        runner=fake_runner(failures=failures, warnings=warnings),
    )


def command_by_key(key: str) -> str:
    for command in post_production_canary.COMMANDS:
        if command.key == key:
            return command.command
    raise AssertionError(f"missing command key {key}")


def test_script_exits_pass_when_all_required_commands_pass(tmp_path):
    summary = run_canary(tmp_path)

    assert summary["overall_status"] == "PASS"
    assert summary["owner_recommendation"] == "KEEP_DRACULA_LIVE"
    assert summary["failed_command"] == ""
    assert summary["route_canary_status"] == "PASS"
    assert summary["backend_catalog_truth_status"] == "PASS"


def test_script_fails_when_route_canary_fails(tmp_path):
    route_command = command_by_key("route_canary")
    summary = run_canary(tmp_path, failures={route_command: 1})

    assert summary["overall_status"] == "FAIL"
    assert summary["failed_command"] == route_command
    assert summary["route_canary_status"] == "FAIL"
    assert summary["owner_recommendation"] == "ROLLBACK"


def test_script_fails_when_backend_catalog_truth_fails(tmp_path):
    backend_command = command_by_key("backend_catalog_truth")
    summary = run_canary(tmp_path, failures={backend_command: 1})

    assert summary["overall_status"] == "FAIL"
    assert summary["failed_command"] == backend_command
    assert summary["backend_catalog_truth_status"] == "FAIL"
    assert summary["owner_recommendation"] == "HOLD_FOR_FIXES"


def test_script_fails_when_controlled_publication_precheck_fails(tmp_path):
    precheck_command = command_by_key("controlled_publication")
    summary = run_canary(tmp_path, failures={precheck_command: 1})

    assert summary["overall_status"] == "FAIL"
    assert summary["failed_command"] == precheck_command
    assert summary["dracula_live_status"] == "FAIL"
    assert summary["owner_recommendation"] == "ROLLBACK"


def test_script_marks_seo_and_audio_warnings_as_warn_without_failure(tmp_path):
    seo_command = command_by_key("seo")
    audio_command = command_by_key("audio")
    summary = run_canary(
        tmp_path,
        failures={audio_command: 1},
        warnings={seo_command},
    )

    assert summary["overall_status"] == "WARN"
    assert summary["failed_command"] == ""
    assert summary["seo_status"] == "WARN"
    assert summary["audio_status"] == "WARN"
    assert summary["owner_recommendation"] == "HOLD_FOR_FIXES"


def test_report_files_are_written(tmp_path):
    summary = run_canary(tmp_path)
    output_root = tmp_path / "release-canary"
    run_dir = output_root / "2026-06-20-10-30-00"
    latest_dir = output_root / "latest"

    assert (run_dir / "summary.json").exists()
    assert (run_dir / "summary.md").exists()
    assert (latest_dir / "summary.json").exists()
    assert (latest_dir / "summary.md").exists()
    assert json.loads((latest_dir / "summary.json").read_text(encoding="utf-8"))["overall_status"] == "PASS"
    assert "KEEP_DRACULA_LIVE" in (latest_dir / "summary.md").read_text(encoding="utf-8")
    assert len(list(run_dir.glob("*.log"))) == len(post_production_canary.COMMANDS)
    assert summary["public_mutation_performed"] is False


def test_main_exits_zero_when_all_required_commands_pass(tmp_path, monkeypatch):
    summary = run_canary(tmp_path)
    monkeypatch.setattr(sys, "argv", ["post_production_canary.py"])
    monkeypatch.setattr(post_production_canary, "run_post_production_canary", lambda **_kwargs: summary)

    assert post_production_canary.main() == 0


def test_main_exits_nonzero_when_critical_command_fails(tmp_path, monkeypatch):
    route_command = command_by_key("route_canary")
    summary = run_canary(tmp_path, failures={route_command: 1})
    monkeypatch.setattr(sys, "argv", ["post_production_canary.py"])
    monkeypatch.setattr(post_production_canary, "run_post_production_canary", lambda **_kwargs: summary)

    assert post_production_canary.main() == 1
