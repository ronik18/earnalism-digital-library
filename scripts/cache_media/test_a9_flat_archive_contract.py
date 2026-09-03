#!/usr/bin/env python3
"""Deterministic contract tests for the root-flat A9 owner-review archive."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts/cache_media/build_a9_owner_review.py"
WORKFLOW = ROOT / ".github/workflows/cache-media-final-review.yml"


def run(*args: str, ok: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if (result.returncode == 0) != ok:
        raise AssertionError(f"unexpected command result {result.returncode}: {result.stdout}\n{result.stderr}")
    return result


def main() -> None:
    head = run("git", "rev-parse", "HEAD").stdout.strip()
    workflow = WORKFLOW.read_text()
    assert 'test -f clean/manifest.json' in workflow
    assert 'test -f clean/manifest.sha256' in workflow
    assert 'test -f clean/artifact.zip' in workflow
    assert 'validate --package clean --head' in workflow
    assert "find clean -maxdepth 1 -type d" not in workflow
    with tempfile.TemporaryDirectory(prefix="a9-flat-archive-") as temporary:
        temp = Path(temporary); package = temp / "package"; clean = temp / "clean"
        run("python", str(BUILDER), "build", "--output", str(package), "--head", head, "--tests", "PASS")
        outer = package.with_suffix(".zip")
        with zipfile.ZipFile(outer) as archive:
            names = archive.namelist()
            assert all("/" not in name for name in names), names
            assert {"manifest.json", "manifest.sha256", "artifact.zip"}.issubset(names)
            archive.extractall(clean)
        before = sorted(path.relative_to(clean).as_posix() for path in clean.rglob("*") if path.is_file())
        assert not any(path.is_dir() for path in clean.iterdir())
        run("python", str(BUILDER), "validate", "--package", str(clean), "--head", head)
        after = sorted(path.relative_to(clean).as_posix() for path in clean.rglob("*") if path.is_file())
        assert before == after
        run("python", str(BUILDER), "validate", "--package", str(clean), "--head", "0" * 40, ok=False)
        missing_manifest = temp / "missing-manifest"; shutil.copytree(clean, missing_manifest); (missing_manifest / "manifest.json").unlink()
        run("python", str(BUILDER), "validate", "--package", str(missing_manifest), "--head", head, ok=False)
        missing_inner = temp / "missing-inner"; shutil.copytree(clean, missing_inner); (missing_inner / "artifact.zip").unlink()
        run("python", str(BUILDER), "validate", "--package", str(missing_inner), "--head", head, ok=False)
        unsafe = temp / "unsafe.zip"
        with zipfile.ZipFile(unsafe, "w") as archive: archive.writestr("../escape", "x")
        with zipfile.ZipFile(unsafe) as archive: assert any(".." in Path(item.filename).parts for item in archive.infolist())
    print(json.dumps({"result": "PASS", "contract_test_count": 9}))


if __name__ == "__main__":
    main()
