"""Retain controller-generated smoke evidence without changing validated source."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile


REPORT = "SIGNED_USER_JOURNEY_REGRESSION_REPORT.md"
OUTPUT_LINE = re.compile(rb"(?m)^- latest_smoke_output: output/ux-journey-regression/\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z$")


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root)


def source_identity(root):
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
    files = {}
    for raw in filter(None, untracked):
        name = raw.decode("utf-8")
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("unexpected untracked file type: " + name)
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "head": git(root, "rev-parse", "HEAD").decode().strip(),
        "diff_sha256": hashlib.sha256(git(root, "diff", "--binary", "HEAD")).hexdigest(),
        "untracked": files,
    }


def snapshot(root, baseline):
    if git(root, "diff", "HEAD", "--", REPORT):
        raise ValueError("worker changed controller-only smoke report")
    baseline.write_text(json.dumps(source_identity(root), sort_keys=True) + "\n")


def retain(root, baseline):
    expected = json.loads(baseline.read_text())
    path = root / REPORT
    if path.is_symlink() or not path.is_file():
        raise ValueError("controller report must be a regular tracked file")
    before = git(root, "show", "HEAD:" + REPORT)
    after = path.read_bytes()
    if before != after:
        if len(OUTPUT_LINE.findall(before)) != 1 or len(OUTPUT_LINE.findall(after)) != 1:
            raise ValueError("controller report has invalid smoke-output field")
        if OUTPUT_LINE.sub(b"<smoke-output>", before) != OUTPUT_LINE.sub(b"<smoke-output>", after):
            raise ValueError("controller changed report facts beyond smoke-output path")
    archive = Path(tempfile.mkdtemp(prefix="earnalism-catalogue-controller-evidence-"))
    (archive / REPORT).write_bytes(after)
    (archive / "validated-source-identity.json").write_text(json.dumps(expected, indent=2) + "\n")
    if before != after:
        subprocess.run(["git", "restore", "--source=HEAD", "--worktree", "--staged", "--", REPORT], cwd=root, check=True)
    if source_identity(root) != expected:
        raise ValueError("source changed after bounded validation; retained evidence at " + str(archive))
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("snapshot", "retain"))
    parser.add_argument("--baseline", required=True, type=Path)
    args = parser.parse_args()
    root = Path.cwd()
    if args.command == "snapshot":
        snapshot(root, args.baseline)
    else:
        print(retain(root, args.baseline))


if __name__ == "__main__":
    main()
