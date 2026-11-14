"""Fixed isolated package restoration; no model/corpus fetch or ML imports.

The profile's runtime.bootstrap binds python_executable (file descriptor) and
wheel_manifest and bootstrap_wheel_manifest (descriptors of
{wheels:[{name,version,filename,bytes,sha256,
url OR path}]}). URLs must be immutable official PyPI wheels; local author-built
wheels are hash-bound. The complete list must equal runtime.packages. A matching
Python ABI is required before package writes. No interpreter is silently fetched.
"""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import earnalism_voice as voice


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise voice.VoiceBlocked("Wheel redirect refused")


def _read_lock(root, descriptor):
    manifest = voice._json(voice._descriptor(root, descriptor))
    rows = manifest.get("wheels")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 256:
        raise voice.VoiceBlocked("Bounded exact wheel lock required")
    versions = {}
    for row in rows:
        if (not isinstance(row, dict) or not re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", str(row.get("name", "")))
                or not re.fullmatch(r"[A-Za-z0-9.!+_-]+", str(row.get("version", "")))
                or Path(row.get("filename", "")).name != row.get("filename")
                or not row["filename"].endswith(".whl") or not voice.SHA.fullmatch(str(row.get("sha256", "")))
                or type(row.get("bytes")) is not int or row["bytes"] <= 0
                or bool(row.get("url")) == bool(row.get("path")) or row["name"] in versions):
            raise voice.VoiceBlocked("Typed exact immutable wheel lock required")
        if row.get("url"):
            url = urlsplit(row["url"])
            if (url.scheme != "https" or url.hostname != "files.pythonhosted.org" or url.port not in {None, 443}
                    or url.username or url.password or url.query or url.fragment):
                raise voice.VoiceBlocked("Only official immutable PyPI wheel URLs allowed")
        else:
            voice._descriptor(root, row)
        versions[row["name"]] = row["version"]
    return rows, versions


def execute(profile_path, runtime_dir, authority_path):
    profile_path = Path(profile_path).absolute(); root = profile_path.parent
    profile = voice._json(profile_path); authority = voice._setup_authority(authority_path, profile_path, runtime_dir)
    voice._arm_child_containment(authority["absolute_deadline_epoch"])
    runtime = profile["runtime"]; bootstrap = runtime["bootstrap"]
    destination = Path(runtime_dir).absolute(); evidence = destination.parent / (destination.name + ".setup")
    if destination.exists() or evidence.exists():
        raise voice.VoiceBlocked("Prior package setup exists; status-only, no replay")
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise voice.VoiceBlocked("Actual Linux x86_64 package target required")
    python = voice._descriptor(root, bootstrap["python_executable"])
    rows, versions = _read_lock(root, bootstrap["wheel_manifest"])
    if versions != runtime["packages"]:
        raise voice.VoiceBlocked("Complete wheel lock and runtime versions differ")
    bootstrap_rows, bootstrap_versions = _read_lock(root, bootstrap["bootstrap_wheel_manifest"])
    if bootstrap_versions.get("virtualenv") != "20.35.4":
        raise voice.VoiceBlocked("Hash-locked virtualenv20.35.4 bootstrap required")
    unique = {}
    for row in rows + bootstrap_rows:
        prior = unique.get(row["filename"])
        if prior and any(prior[k] != row[k] for k in ["bytes", "sha256", "name", "version"]):
            raise voice.VoiceBlocked("Conflicting locked wheel artifact")
        unique[row["filename"]] = row
    all_rows = list(unique.values())
    env = {"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONNOUSERSITE": "1",
           "PIP_CONFIG_FILE": "/dev/null", "PIP_NO_CACHE_DIR": "1", "PYTHONDONTWRITEBYTECODE": "1",
           "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "CUDA_VISIBLE_DEVICES": ""}
    def remaining():
        seconds = authority["absolute_deadline_epoch"] - time.time()
        if seconds <= 0: raise TimeoutError("Original setup deadline exhausted")
        return seconds
    probe = subprocess.run([str(python), "-I", "-c", "import sys;print('.'.join(map(str,sys.version_info[:2])))"],
        env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, check=True, timeout=remaining(),
        preexec_fn=lambda: voice._arm_child_containment(authority["absolute_deadline_epoch"]))
    if probe.stdout.strip() != runtime["python"]:
        raise voice.VoiceBlocked("Matching Python " + runtime["python"] + " executable required; no ABI substitution")
    if shutil.disk_usage(destination.parent).free < 2 * sum(row["bytes"] for row in all_rows) + 2 * 1024**3:
        raise voice.VoiceBlocked("Insufficient package restoration disk reserve")
    evidence.mkdir(parents=True, exist_ok=False)
    voice._write(evidence / "INTENT.json", {"profile_sha256": voice.digest(profile_path),
        "original_deadline": authority["absolute_deadline_epoch"], "models_loaded": False})
    wheelhouse = evidence / "wheelhouse"; wheelhouse.mkdir()
    try:
        for row in all_rows:
            remaining(); output = wheelhouse / row["filename"]
            if row.get("url"):
                voice._append(evidence / "events.jsonl", {"event": "official_wheel_GET_intent", "filename": row["filename"]})
                with output.open("xb") as handle:
                    with build_opener(NoRedirect()).open(Request(row["url"], headers={"Accept-Encoding": "identity"}),
                                                       timeout=min(60, remaining())) as response:
                        if response.status != 200 or response.geturl() != row["url"]:
                            raise voice.VoiceBlocked("Complete exact wheel response required")
                        count = 0
                        while True:
                            remaining(); block = response.read(min(1024 * 1024, row["bytes"] - count + 1))
                            if not block: break
                            count += len(block)
                            if count > row["bytes"]: raise voice.VoiceBlocked("Wheel size exceeded; partial retained")
                            handle.write(block)
                    handle.flush(); os.fsync(handle.fileno())
            else:
                with voice._descriptor(root, row).open("rb") as source, output.open("xb") as handle:
                    shutil.copyfileobj(source, handle, 1024 * 1024); handle.flush(); os.fsync(handle.fileno())
            voice._descriptor(wheelhouse, {**row, "path": row["filename"]})
        requirements = evidence / "requirements.lock.txt"
        with requirements.open("x") as handle:
            for row in rows:
                handle.write(row["name"] + "==" + row["version"] + " --hash=sha256:" + row["sha256"] + "\n")
        bootstrap_requirements = evidence / "bootstrap.requirements.lock.txt"
        with bootstrap_requirements.open("x") as handle:
            for row in bootstrap_rows:
                handle.write(row["name"] + "==" + row["version"] + " --hash=sha256:" + row["sha256"] + "\n")
        target = evidence / "bootstrap-packages"
        commands = [
            [sys.executable, "-m", "pip", "install", "--no-index", "--find-links", str(wheelhouse),
             "--only-binary=:all:", "--require-hashes", "--ignore-installed", "--disable-pip-version-check",
             "--no-cache-dir", "--target", str(target), "-r", str(bootstrap_requirements)],
            [sys.executable, "-I", "-c", "import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_module('virtualenv',run_name='__main__')",
             str(target), "--no-download", "--no-periodic-update", "--app-data", str(evidence / "virtualenv-appdata"),
             "--python", str(python), str(destination)],
            [str(destination / "bin/python"), "-m", "pip", "install", "--no-index", "--find-links", str(wheelhouse),
             "--only-binary=:all:", "--require-hashes", "--no-cache-dir", "--no-compile", "-r", str(requirements)],
            [str(destination / "bin/python"), "-m", "pip", "check"],
        ]
        for index, command in enumerate(commands):
            voice._append(evidence / "events.jsonl", {"event": "fixed_package_step_intent", "step": index})
            with (evidence / (str(index) + ".log")).open("xb") as log:
                subprocess.run(command, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                               check=True, timeout=remaining(),
                               preexec_fn=lambda: voice._arm_child_containment(authority["absolute_deadline_epoch"]))
        # Distribution metadata only; no torch/model imports or claimed GPU qualification.
        probe_code = "import importlib.metadata,json;print(json.dumps({d.metadata['Name'].lower().replace('_','-').replace('.','-'):d.version for d in importlib.metadata.distributions()}))"
        actual = subprocess.run([str(destination / "bin/python"), "-I", "-c", probe_code], env=env,
            stdin=subprocess.DEVNULL, capture_output=True, text=True, check=True, timeout=remaining(),
            preexec_fn=lambda: voice._arm_child_containment(authority["absolute_deadline_epoch"]))
        installed = json.loads(actual.stdout)
        if any(installed.get(name) != version for name, version in versions.items()):
            raise voice.VoiceBlocked("Installed package versions differ from exact lock")
        result = {"status": "LOCAL_PACKAGES_READY_NOT_MODEL_QUALIFIED", "profile_sha256": voice.digest(profile_path),
                  "python": str(destination / "bin/python"), "package_versions": versions,
                  "original_deadline": authority["absolute_deadline_epoch"], "model_loading": False, "training": False}
        voice._write(evidence / "RESULT.json", result)
        return result
    except BaseException as error:
        voice._write(evidence / "FAILURE.json", {"status": "SETUP_FAILED_OR_UNKNOWN_NO_REPLAY",
                                                "error_type": type(error).__name__})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--authority", type=Path, required=True); parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"status": "DISABLED_NO_PACKAGE_OR_MODEL_OPERATION"}))
    else:
        print(json.dumps(execute(args.profile, args.output, args.authority)))
