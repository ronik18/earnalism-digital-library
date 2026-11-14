#!/usr/bin/env python3
"""Build the single Colab entry point from an immutable source base and overlay.

Building does not allocate a runtime, install dependencies, load a model or publish.
The notebook embeds the reviewed generic code, never private projects or weights.
"""
from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import io
import inspect
import json
from pathlib import Path
import re
import subprocess
import textwrap
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/ronik18/earnalism-digital-library.git"
FILES = (
    "scripts/earnalism_orchestrator.py",
    "scripts/earnalism_voice.py",
    "scripts/earnalism_media_adapters.py",
    "skills/earnalism-video/software/src/render-browser.mjs",
    "skills/earnalism-video/software/src/render-runtime.mjs",
    "skills/earnalism-video/software/src/prepare-render-runtime.mjs",
    "skills/earnalism-video/software/src/BrandWatermark.tsx",
    "skills/earnalism-video/software/src/branding.mjs",
    "skills/earnalism-video/software/src/social-safe-area.mjs",
    "skills/earnalism-video/software/package.json",
    "skills/earnalism-video/software/package-lock.json",
    "skills/earnalism-video/software/thermal_touch/render.mjs",
    "skills/earnalism-video/software/condensation/render.mjs",
    "skills/earnalism-video/software/sky_colour/render.mjs",
    "skills/earnalism-video/software/sky_colour/render-batch.mjs",
    "skills/earnalism-video/software/rainbow/render-batch.mjs",
    ".agents/skills/earnalism-book-audiovisual/SKILL.md",
    ".agents/skills/earnalism-audiobook-score/SKILL.md",
    ".agents/skills/earnalism-audiobook-score/references/learning.md",
    ".agents/skills/earnalism-audiobook-go-live/SKILL.md",
    "skills/earnalism-audiobook-go-live/SKILL.md",
    "skills/earnalism-video/SKILL.md",
    "docs/earnalism_orchestrator.md",
)


def check_base_source(source_root, source_files):
    """Refuse changed base dependencies outside the exact reviewed overlay."""
    import subprocess
    from pathlib import Path
    source_root = Path(source_root)
    allowed = set(source_files) | {".earnalism-source-capsule.json"}
    raw = subprocess.check_output(["git", "-C", str(source_root), "status",
                                   "--porcelain=v1", "-z", "--untracked-files=all"])
    for row in raw.split(b"\0"):
        if not row:
            continue
        status, name = row[:2].decode(), row[3:].decode()
        if any(flag in status for flag in "RCU") or name not in allowed:
            raise RuntimeError("Preserve changed or unowned base source: " + name)


def check_import_namespace(source_root):
    """Refuse foreign cached code instead of resetting a live Python namespace."""
    import sys
    from pathlib import Path
    source_root = Path(source_root).resolve()
    prefixes = ("scripts", "software", "thermal_touch", "condensation", "sky_colour",
                "rainbow", "audiobook_visuals", "wan22")
    for name, module in tuple(sys.modules.items()):
        relevant = any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes)
        filename = getattr(module, "__file__", None)
        locations = list(getattr(module, "__path__", ()))
        if filename:
            locations.append(filename)
        paths = [Path(path).resolve() for path in locations if isinstance(path, str)]
        older_capsule = any(any(parent.name.startswith("earnalism-orchestrator-")
                                and parent != source_root for parent in path.parents)
                            for path in paths)
        if (relevant and (not paths or any(not path.is_relative_to(source_root) for path in paths))) or older_capsule:
            raise RuntimeError("Preserve foreign cached module; use an isolated worker: " + name)


def _cell(kind, source):
    value = {"cell_type": kind, "metadata": {}, "source": source.splitlines(keepends=True)}
    if kind == "code":
        ast.parse(source)
        value.update(execution_count=None, outputs=[])
    return value


def build(output: Path, *, root: Path = ROOT, base_revision: str | None = None):
    if base_revision is None:
        base_revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if not re.fullmatch(r"[a-f0-9]{40}", base_revision):
        raise ValueError("An exact 40-character source base is required")
    names = list(FILES)
    names += [p.relative_to(root).as_posix() for p in
              sorted((root / "scripts/earnalism_voice_runtime").glob("*.py"))]
    source = {}
    for name in names:
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Missing regular source file: {name}")
        source[name] = path.read_bytes()
    manifest = {name: hashlib.sha256(data).hexdigest() for name, data in source.items()}
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(source.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    capsule = stream.getvalue()
    if len(capsule) > 2 * 1024**2:
        raise ValueError("Generic source capsule exceeds 2 MiB; exclude media, data and weights")
    capsule_sha = hashlib.sha256(capsule).hexdigest()
    controls = '''# The content instruction is the normal entry point after one-time private setup.
INSTRUCTION = "Build the GO LIVE ready output for the audiovisual cinematic version for the book - The Selfish Giant" #@param {type:"string"}
EXECUTE = False #@param {type:"boolean"}

# Configure these once for your private Earnalism installation.
PRIVATE_WORKSPACE = "/content/drive/MyDrive/Earnalism/Production"
REGISTRY_PATH = ""  # Empty selects PRIVATE_WORKSPACE/projects.json.
RUNTIME_AUTHORITY_PATH = "/content/earnalism-runtime-authority.json"
CONNECT_PRIVATE_DRIVE = False  # Explicit interactive Google permission, if needed.
AUTO_DISCONNECT_OWN_RUNTIME = True
FEEDBACK_PATH = ""  # Optional exact-candidate feedback JSON in the private workspace.
'''
    guard = '''import json, math, pathlib, threading, time
runtime_context = {}
runtime_guard = None
runtime_authority = None
if EXECUTE:
    authority_file = pathlib.Path(RUNTIME_AUTHORITY_PATH)
    if not authority_file.is_file():
        raise RuntimeError("Supply the existing actual runtime authority before execution; this instruction creates no compute grant.")
    runtime_authority_raw = authority_file.read_bytes()
    runtime_authority = json.loads(runtime_authority_raw)
    if (runtime_authority.get("schema") != "earnalism.orchestrator_runtime.v1"
            or runtime_authority.get("owner_authorized") is not True):
        raise RuntimeError("An actual owner-authorized orchestration scope is required")
    started = runtime_authority.get("allocation_started_at")
    deadline = runtime_authority.get("original_deadline_epoch")
    if (any(isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x)
            for x in (started, deadline)) or not started <= time.time() < deadline):
        raise RuntimeError("Original allocation clock is missing or exhausted; never renew it here")
    from google.colab import runtime
    runtime_guard = threading.Timer(deadline-time.time(), runtime.unassign)
    runtime_guard.daemon = True
    runtime_guard.start()
    runtime_context = {"shutdown_guard_armed": runtime_guard.is_alive(),
                       "allocation_started_at": started,
                       "original_deadline_epoch": deadline}
    print({"original_clock_bound": True, "deadline": deadline,
           "guard_is_provider_quota": False})
else:
    print("Preparation only: no model, paid provider, training or publication call is enabled.")
'''
    bootstrap = f'''# Public reviewed software only. Private registry, media and model weights stay on Drive.
import base64, hashlib, io, os, pathlib, subprocess, sys, zipfile
SOURCE_BASE_REVISION = {base_revision!r}
SOURCE_CAPSULE_SHA256 = {capsule_sha!r}
SOURCE_FILES = {manifest!r}
raw_source = base64.b64decode({base64.b64encode(capsule).decode()!r}, validate=True)
assert hashlib.sha256(raw_source).hexdigest() == SOURCE_CAPSULE_SHA256
source_root = pathlib.Path("/content/earnalism-orchestrator-" + SOURCE_CAPSULE_SHA256[:12])
source_created_here = False
source_seal = source_root/".earnalism-source-capsule.json"
def source_command(argv):
    seconds = 180
    if EXECUTE:
        seconds = min(seconds, runtime_context["original_deadline_epoch"]-time.time())
        if seconds <= 0: raise RuntimeError("Original clock exhausted during software preparation")
    subprocess.run(argv, check=True, timeout=seconds, stdin=subprocess.DEVNULL)
if not source_root.exists():
    source_created_here = True
    source_command(["git", "clone", "--filter=blob:none", "--no-checkout", "--no-tags",
                    {REPOSITORY!r}, str(source_root)])
    source_command(["git", "-C", str(source_root), "fetch", "--depth=1", "origin", SOURCE_BASE_REVISION])
    source_command(["git", "-C", str(source_root), "checkout", "--detach", SOURCE_BASE_REVISION])
actual_base = subprocess.check_output(["git", "-C", str(source_root), "rev-parse", "HEAD"], text=True).strip()
if actual_base != SOURCE_BASE_REVISION:
    raise RuntimeError("Preserve existing checkout: source base differs")
if not source_created_here:
    if not source_seal.is_file() or json.loads(source_seal.read_text()) != {{"base": SOURCE_BASE_REVISION, "capsule": SOURCE_CAPSULE_SHA256}}:
        raise RuntimeError("Preserve existing unowned or incomplete software directory")
    if any(not (source_root/name).is_file() or hashlib.sha256((source_root/name).read_bytes()).hexdigest()!=expected
           for name, expected in SOURCE_FILES.items()):
        raise RuntimeError("Preserve modified source; do not overwrite it during resume")
    check_base_source(source_root, SOURCE_FILES)
with zipfile.ZipFile(io.BytesIO(raw_source)) as archive:
    if set(archive.namelist()) != set(SOURCE_FILES): raise RuntimeError("Source inventory mismatch")
    for name in archive.namelist():
        target = source_root / name
        data = archive.read(name)
        if hashlib.sha256(data).hexdigest() != SOURCE_FILES[name]: raise RuntimeError("Changed source member")
        if target.is_symlink() or any(p.is_symlink() for p in target.parents):
            raise RuntimeError("Source overlay symlink refused")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != data:
            target.write_bytes(data)
for name, expected in SOURCE_FILES.items():
    if hashlib.sha256((source_root/name).read_bytes()).hexdigest() != expected:
        raise RuntimeError("Source overlay verification failed")
source_seal.write_text(json.dumps({{"base": SOURCE_BASE_REVISION, "capsule": SOURCE_CAPSULE_SHA256}}))
check_base_source(source_root, SOURCE_FILES)
check_import_namespace(source_root)
if str(source_root) not in sys.path: sys.path.insert(0, str(source_root))
print({{"software_base": SOURCE_BASE_REVISION, "software_overlay": SOURCE_CAPSULE_SHA256,
       "source_files_verified": len(SOURCE_FILES), "model_loaded": False}})
'''
    workspace = '''if CONNECT_PRIVATE_DRIVE:
    from google.colab import drive
    drive.mount("/content/drive")
workspace = pathlib.Path(PRIVATE_WORKSPACE).expanduser().resolve()
if EXECUTE and (not workspace.is_dir() or not pathlib.Path("/content/drive/MyDrive").is_dir()
                or not workspace.is_relative_to(pathlib.Path("/content/drive/MyDrive").resolve())):
    raise RuntimeError("Execution needs the configured mounted private Drive workspace; ephemeral storage is not the sole checkpoint.")
registry = pathlib.Path(REGISTRY_PATH).expanduser() if REGISTRY_PATH else workspace/"projects.json"
print({"private_workspace": str(workspace), "project_registry_present": registry.is_file(),
       "private_visibility": "Use the owner-only Drive project folder; path presence alone is not a sharing audit."})
'''
    # Definitions keep setup and execution inside one finally-controlled operation.
    helpers = inspect.getsource(check_base_source) + "\n" + inspect.getsource(check_import_namespace)
    bootstrap = "def prepare_reviewed_software():\n" + textwrap.indent(helpers + "\n" + bootstrap, "    ") + "    return source_root\n"
    workspace = "def connect_private_workspace():\n" + textwrap.indent(workspace, "    ") + "    return workspace, registry\n"
    execute = '''workspace = pathlib.Path(PRIVATE_WORKSPACE).expanduser().resolve()
def retain_notebook_event(kind, payload):
    # Immutable history survives repeated startup failures; latest files are pointers.
    if not workspace.is_dir(): return {}
    import hashlib, os
    folder = workspace/".orchestrator"/"notebook-events"
    folder.mkdir(parents=True, exist_ok=True)
    event_path = folder/(str(time.time_ns())+"-"+kind+".json")
    raw = (json.dumps(payload, indent=2)+"\\n").encode()
    with event_path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {"event_path":str(event_path),"event_sha256":hashlib.sha256(raw).hexdigest()}
result = None
try:
    workspace, registry = connect_private_workspace()
    admitted_runtime_authority = None
    if EXECUTE:
        # Preserve the exact already-authorized bytes; this creates no new scope.
        import hashlib
        admission_dir = workspace/".orchestrator"/"admissions"
        admission_dir.mkdir(parents=True, exist_ok=True)
        admitted_runtime_authority = admission_dir/(hashlib.sha256(runtime_authority_raw).hexdigest()+".json")
        if admitted_runtime_authority.exists():
            if admitted_runtime_authority.read_bytes() != runtime_authority_raw:
                raise RuntimeError("Preserve existing runtime admission: bytes differ")
        else:
            with admitted_runtime_authority.open("xb") as handle:
                handle.write(runtime_authority_raw)
                handle.flush()
                import os
                os.fsync(handle.fileno())
    source_root = prepare_reviewed_software()
    from scripts.earnalism_orchestrator import run, feedback
    result = run(INSTRUCTION, workspace, registry_path=registry, execute=EXECUTE,
                 authority_path=admitted_runtime_authority,
                 runtime_context=runtime_context)
    if FEEDBACK_PATH:
        feedback_result = feedback(pathlib.Path(FEEDBACK_PATH), workspace)
        print(json.dumps(feedback_result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))
except BaseException as error:
    failure = {"state":"FAILED_OR_UNKNOWN", "error_type":type(error).__name__,
               "original_deadline_epoch":runtime_context.get("original_deadline_epoch"),
               "automatic_retry":False, "production_ready":False}
    retained_failure = retain_notebook_event("startup-or-run-error", failure)
    if workspace.is_dir():
        (workspace/"last-orchestrator-error.json").write_text(json.dumps({**failure, **retained_failure}, indent=2)+"\\n")
    print(json.dumps(failure, indent=2), flush=True)
    raise
finally:
    if EXECUTE and AUTO_DISCONNECT_OWN_RUNTIME:
        # run() persists stage results/intents and failures in the private workspace.
        # This requests shutdown; actual provider release is a separate observed fact.
        try:
            shutdown_record = {"shutdown_requested_at": time.time(),
                               "original_deadline_epoch": runtime_context["original_deadline_epoch"],
                               "provider_closure_observed": False}
            retained_shutdown = retain_notebook_event("shutdown-request", shutdown_record)
            if workspace.is_dir():
                (workspace/"last-shutdown-request.json").write_text(json.dumps({**shutdown_record, **retained_shutdown}, indent=2)+"\\n")
            print(json.dumps(shutdown_record, indent=2), flush=True)
        finally:
            from google.colab import runtime
            runtime.unassign()
'''
    notebook = {"nbformat": 4, "nbformat_minor": 5,
                "metadata": {"colab": {"name": "Earnalism Production Orchestrator"},
                             "kernelspec": {"display_name": "Python 3", "name": "python3"}},
                "cells": [
                    _cell("markdown", """# The Earnalism · one production orchestrator

Enter a book or EverydayScience instruction and run this notebook. It coordinates
the existing Earnalism workflows, reuses verified checkpoints and applies retained
feedback to the affected stages. Outputs and account evidence remain private.

Examples: **The Selfish Giant**; **the Bengali book - Bicharak**; **the next
audiovisual for the EverydayScience topic for theearnalism social media platform**.

One-time setup registers exact private projects, voice/model assets, measured
timing, cleared music and visual jobs in `projects.json`. The agent prepares these
using the relevant skills. An instruction resolves that durable registry; it does
not manufacture missing content, model acceptance, rights or spending authority.
The trained branded voice is selected by exact lineage and language acceptance.
A training checkpoint or a synthetic test does not establish premium performance.

Preparation is the default. Enable execution only within an existing actual
runtime scope; its original allocation clock includes setup, transfer and export.
The notebook never publishes. The existing release governor decides readiness;
actual destination approval and verification remain in the supported release path.
"""),
                    _cell("code", controls),
                    _cell("markdown", "## Bind the existing runtime scope\nThis arms the original shutdown guard before software, Drive connection or model work."),
                    _cell("code", guard),
                    _cell("markdown", "## Load the exact reviewed software\nPublic source base plus a checksum-verified generic overlay; no private media or checkpoint is embedded."),
                    _cell("code", bootstrap),
                    _cell("markdown", "## Attach the private project workspace\nIf Google permission is needed, complete its ordinary interactive connection. No model download or broad access is inferred from a title."),
                    _cell("code", workspace),
                    _cell("markdown", "## Coordinate, checkpoint and report\nReuse healthy outputs. Retain consumed or unknown attempts and actual review findings. `GO LIVE ready` requests preparation, not publication."),
                    _cell("code", execute),
                ]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(notebook, ensure_ascii=False, indent=1)+"\n", encoding="utf-8")
    receipt = {"schema": "earnalism.orchestrator_notebook_source.v1", "base_revision": base_revision,
               "capsule_sha256": capsule_sha, "capsule_bytes": len(capsule), "files": manifest,
               "notebook_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
               "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "execution_default": False, "private_media_embedded": False,
               "model_or_training_qualification": False}
    output.with_suffix(".source.json").write_text(json.dumps(receipt, indent=2)+"\n")
    return receipt


def verify_notebook(output: Path, *, root: Path = ROOT):
    """Verify the delivered source capsule without executing notebook code."""
    receipt = json.loads(output.with_suffix(".source.json").read_text())
    if (receipt.get("schema") != "earnalism.orchestrator_notebook_source.v1"
            or hashlib.sha256(output.read_bytes()).hexdigest() != receipt["notebook_sha256"]):
        raise ValueError("Notebook identity differs from its build receipt")
    if receipt.get("builder_sha256") != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
        raise ValueError("Notebook builder is stale; rebuild the notebook")
    notebook = json.loads(output.read_text())
    raw = None
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        if cell.get("outputs") or cell.get("execution_count") is not None:
            raise ValueError("Distributed notebook must be unexecuted")
        tree = ast.parse("".join(cell["source"]))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            if isinstance(node.targets[0], ast.Name) and node.targets[0].id == "EXECUTE":
                if ast.literal_eval(node.value) is not False:
                    raise ValueError("Execution default must be false")
            if isinstance(node.targets[0], ast.Name) and node.targets[0].id == "raw_source":
                if raw is not None:
                    raise ValueError("Ambiguous source capsule")
                raw = base64.b64decode(ast.literal_eval(node.value.args[0]), validate=True)
    if raw is None or hashlib.sha256(raw).hexdigest() != receipt["capsule_sha256"]:
        raise ValueError("Source capsule identity mismatch")
    expected_names = set(FILES) | {p.relative_to(root).as_posix() for p in
                                 (root/"scripts/earnalism_voice_runtime").glob("*.py")}
    if set(receipt["files"]) != expected_names:
        raise ValueError("Source inventory is stale")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())) or set(archive.namelist()) != expected_names:
            raise ValueError("Source capsule inventory mismatch")
        for name, expected in receipt["files"].items():
            if (hashlib.sha256(archive.read(name)).hexdigest() != expected
                    or hashlib.sha256((root/name).read_bytes()).hexdigest() != expected):
                raise ValueError(f"Source capsule is stale: {name}")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT/"notebooks/Earnalism_Production_Orchestrator.ipynb")
    parser.add_argument("--base-revision")
    parser.add_argument("--check", action="store_true", help="Check the built notebook against current source")
    args = parser.parse_args()
    result = verify_notebook(args.output) if args.check else build(args.output, base_revision=args.base_revision)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
