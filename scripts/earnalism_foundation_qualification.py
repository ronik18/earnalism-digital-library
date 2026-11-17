"""Private environment qualification only. Import and planning have no native effects.

This operation never allocates, downloads, loads TTS models, generates speech,
trains, purchases, publishes or manufactures a diagnostic runtime authority.
"""
import argparse
import hashlib
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

OPERATION = "foundation-qualification"
REQUEST_SCHEMA = "earnalism.foundation_qualification_request.v1"
EXPERIMENT_SHA256 = "d685d47127b3172f502b6bbae49f50daeb7d34d1882c5c407a04d3878cb4e515"
RECIPE_SHA256 = "2baaf85b6f99de7b4bee8096ceace3532075fcfcb2b71fa04fe7f3ca6b3aaf47"
WHEELS_SHA256 = "9727763f54735a874b7b7f050391a27be9966fb791e8506c1574b1a275bba4ef"
REQUIREMENTS_SHA256 = "5f673727be36465a4ef8753d90994e381dc0f614c0eaf3866c1cb05556c3d66b"
PRE_STORAGE_ROOT = Path("/content/earnalism-foundation-qualification-prestorage")
LOCAL_RUNTIME_ROOT = Path("/content/earnalism-foundation-qualification-runtime")
ROOT = Path(__file__).resolve().parents[1]
SOFTWARE = (
    "scripts/earnalism_orchestrator.py", "scripts/earnalism_foundation_diagnostic.py",
    "scripts/earnalism_foundation_qualification.py", "scripts/earnalism_voice.py",
    "scripts/earnalism_voice_runtime/setup.py", "scripts/earnalism_voice_runtime/foundation.py",
    "scripts/earnalism_voice_runtime/parler.py", "scripts/earnalism_voice_runtime/position_table.py",
    "scripts/earnalism_voice_runtime/provider_driver_bootstrap.py",
)
COUNTS = {"package_attempts": 1, "minimal_cuda_calls": 1, "driver_lookup_calls": 1,
          "model_loads": 0, "generation_calls": 0, "adapted_restores": 0, "training_updates": 0}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path, check=lambda: None):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while block := stream.read(1024 * 1024):
            check(); h.update(block)
    return h.hexdigest()


def read(path, maximum=1024**2):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= maximum,
            "Bounded regular qualification metadata required")
    return json.loads(path.read_text())


def write(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n"); stream.flush(); os.fsync(stream.fileno())


def contained(path, workspace):
    path = Path(path).expanduser().resolve()
    require(path.is_relative_to(Path(workspace).resolve()), "Qualification files must stay private")
    return path


def descriptor(path):
    path = Path(path)
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha(path)}


def exact_file(item, root=None, check=lambda: None, *, allow_empty_log=False):
    require(isinstance(item, dict) and type(item.get("bytes")) is int
            and (item["bytes"] > 0 or (allow_empty_log and item["bytes"] == 0
                 and Path(str(item.get("path", ""))).suffix == ".log"))
            and re.fullmatch("[0-9a-f]{64}", str(item.get("sha256", ""))), "Exact file descriptor required")
    path = Path(item["path"])
    if root is not None:
        path = root / path
        require(not path.is_symlink(), "Preserve redirected qualification inputs")
        path = contained(path, root)
    require(path.is_absolute() and not path.is_symlink() and path.is_file()
            and path.stat().st_size == item["bytes"] and sha(path, check) == item["sha256"],
            "Qualification input changed: " + path.name)
    return path


def software():
    return {name: sha(ROOT / name) for name in SOFTWARE}


def validate(request_path, workspace):
    from scripts import earnalism_foundation_diagnostic as diagnostic
    path = contained(request_path, workspace); request = read(path)
    require(request.get("schema") == REQUEST_SCHEMA and request.get("software") == software()
            and request.get("experiment_sha256") == EXPERIMENT_SHA256,
            "Exact reviewed qualification request and software required")
    proposal = exact_file(request["proposal"], path.parent)
    frozen = diagnostic.validate(proposal, workspace)
    require(frozen["experiment_sha256"] == EXPERIMENT_SHA256, "Frozen experiment must not reset")
    recipe_path = exact_file(request["recipe"], path.parent)
    require(sha(recipe_path) == RECIPE_SHA256, "Retain the exact prepared recipe")
    recipe = read(recipe_path)
    require(recipe["execution_enabled"] is False and recipe["runner"] is None
            and recipe["frozen_experiment_sha256"] == EXPERIMENT_SHA256,
            "Historical prepared recipe is not execution authority")
    wheel_path = exact_file(request["wheel_manifest"], path.parent)
    require(sha(wheel_path) == WHEELS_SHA256, "Exact retained111 wheel manifest required")
    wheels = read(wheel_path)["wheels"]
    require(len(wheels) == 111 and len({w["filename"] for w in wheels}) == 111
            and len({w["name"] for w in wheels}) == 111
            and all(not w.get("url") and Path(w["filename"]).name == w["filename"] for w in wheels),
            "Local-only exact wheel closure required")
    packages = frozen["proposal"]["future_comparability_requirements"]["runtime"]["packages"]
    require({w["name"]: w["version"] for w in wheels} == packages, "Exact frozen package map required")
    requirements = "".join(w["name"] + "==" + w["version"] + " --hash=sha256:" + w["sha256"] + "\n"
                           for w in wheels)
    require(hashlib.sha256(requirements.encode()).hexdigest() == REQUIREMENTS_SHA256,
            "Exact requirements derivation required")
    return {"request_path": str(path), "request_sha256": sha(path), "request": request,
            "frozen": frozen, "experiment_sha256": EXPERIMENT_SHA256,
            "wheels": wheels, "packages": packages, "requirements": requirements}


def summary(plan):
    return {"schema": "earnalism.foundation_qualification_plan.v1", "operation": OPERATION,
            "state": "IMPLEMENTED_PRIVATE_EXECUTION_DISABLED_RUNTIME_UNQUALIFIED",
            "experiment_sha256": plan["experiment_sha256"], "request_sha256": plan["request_sha256"],
            "proposed_counts": COUNTS, "execution_enabled": False, "runtime_authority": None,
            "compute_allowance": None, "runtime_qualified": False, "model_ready": False,
            "production_ready": False, "reference": "Full original 4.8-second Clip2; human comparator only"}


def _common(runtime, context):
    require(isinstance(runtime, dict) and runtime.get("owner_authorized") is True
            and "foundation_qualification" in runtime and "foundation_diagnostic" not in runtime,
            "Separate fresh qualification capability required")
    from scripts import earnalism_orchestrator as engine
    original = engine._runtime(runtime.get("path"), {"id": runtime.get("project_id")},
                               Path(runtime["path"]).parent, context)
    require(original == runtime, "Exact original guarded outer capability required")
    q = runtime["foundation_qualification"]
    require(isinstance(q, dict) and q.get("operation") == OPERATION
            and q.get("purpose") == "private-environment-qualification"
            and q.get("experiment_sha256") == EXPERIMENT_SHA256
            and q.get("recipe_sha256") == RECIPE_SHA256
            and q.get("wheel_manifest_sha256") == WHEELS_SHA256
            and isinstance(q.get("request_sha256"), str)
            and re.fullmatch("[0-9a-f]{64}", q["request_sha256"])
            and q.get("software") == software()
            and all(type(q.get(k)) is int and q[k] == v for k, v in COUNTS.items())
            and isinstance(q.get("provider_runtime_id"), str) and q["provider_runtime_id"].strip(),
            "Exact fixed qualification capability/counts required")
    require(runtime.get("purchases_allowed") is False and runtime.get("publication_allowed") is False
            and runtime.get("max_model_stage_starts") == 1
            and runtime.get("stage_attempt_limits") == {"foundation-diagnostic": 1},
            "Qualification cannot substitute for model or publication authority")
    require(sha(runtime["path"]) == runtime["sha256"]
            and read(runtime["path"]) == {k: v for k, v in runtime.items() if k not in {"path", "sha256"}},
            "Original qualification authority bytes changed")
    start, deadline = runtime["allocation_started_at"], runtime["original_deadline_epoch"]
    require(start <= time.time() < deadline <= start + 86400
            and isinstance(context, dict) and context.get("shutdown_guard_armed") is True
            and context.get("allocation_started_at") == start
            and context.get("original_deadline_epoch") == deadline,
            "Actual same-allocation original guard/clock required")
    require(sys.platform == "linux" and platform.machine() == "x86_64" and sys.version_info[:2] == (3, 12),
            "Actual Linux/x86_64/CPython3.12 required; no ABI fallback")
    python = q["provider_python"]
    target = exact_file({**python, "path": python["resolved_path"]})
    require(Path(sys.executable).absolute() == Path(python["path"])
            and Path(python["path"]).resolve(strict=True) == target and os.access(target, os.X_OK),
            "Actual hash-bound provider interpreter required")
    return q


def _check(runtime, context):
    require(isinstance(context, dict) and context.get("shutdown_guard_armed") is True
            and context.get("allocation_started_at") == runtime["allocation_started_at"]
            and context.get("original_deadline_epoch") == runtime["original_deadline_epoch"]
            and runtime["allocation_started_at"] <= time.time() < runtime["original_deadline_epoch"]
            and sha(runtime["path"]) == runtime["sha256"], "Original authority/clock exhausted or changed")
    return max(0.001, runtime["original_deadline_epoch"] - time.time())


def pre_storage(runtime, context, evidence_root):
    """One local driver lookup before Drive; return a bounded primary receipt descriptor.

    Local intent prevents replay in this actual allocation. After Drive is mounted,
    the canonical workspace journal separately prevents package/probe replay across
    requests/scopes. This entry cannot observe a remote journal before connection.
    """
    q = _common(runtime, context)
    root = Path(evidence_root).absolute()
    require(root == PRE_STORAGE_ROOT and not root.is_symlink(), "Fixed local pre-storage evidence root required")
    require(root.resolve() == root, "Preserve redirected local evidence paths")
    root.mkdir(parents=True, exist_ok=True)
    output = root / EXPERIMENT_SHA256
    if output.exists():
        require(not output.is_symlink(), "Preserve redirected local driver evidence")
        result = read(output / "RESULT.json", 65536)
        require(read(output / "COMPLETED.json")["result_sha256"] == sha(output / "RESULT.json")
                and result.get("schema") == "earnalism.foundation_pre_storage_result.v1"
                and result.get("state") == "ACTUAL_DRIVER_LOOKUP_ONLY_NOT_CUDA_QUALIFIED"
                and result["authority_sha256"] == runtime["sha256"]
                and result["provider_runtime_id"] == q["provider_runtime_id"]
                and result["allocation_started_at"] == runtime["allocation_started_at"]
                and result["original_deadline_epoch"] == runtime["original_deadline_epoch"],
                "Consumed or unknown local driver attempt; no replay")
        return descriptor(output / "RESULT.json")
    output.mkdir(exist_ok=False)
    write(output / "INTENT.json", {"operation": OPERATION, "phase": "pre-storage-driver-only",
        "experiment_sha256": EXPERIMENT_SHA256, "authority_sha256": runtime["sha256"],
        "provider_runtime_id": q["provider_runtime_id"], "at": time.time(), "model_loads": 0})
    from scripts import earnalism_voice as voice
    try:
        _check(runtime, context)
        binding = voice._owned_provider_helper().resolve_provider_driver()
        _check(runtime, context)
        result = {"schema": "earnalism.foundation_pre_storage_result.v1",
            "state": "ACTUAL_DRIVER_LOOKUP_ONLY_NOT_CUDA_QUALIFIED", "operation": OPERATION,
            "experiment_sha256": EXPERIMENT_SHA256, "authority_sha256": runtime["sha256"],
            "provider_runtime_id": q["provider_runtime_id"],
            "allocation_started_at": runtime["allocation_started_at"],
            "original_deadline_epoch": runtime["original_deadline_epoch"], "provider_binding": binding,
            "provider_python": q["provider_python"], "model_loads": 0, "generation_calls": 0,
            "training_updates": 0, "CUDA_probe_calls": 0, "runtime_qualified": False}
        require(len(json.dumps(result).encode()) <= 65536, "Bounded primary driver receipt required")
        write(output / "RESULT.json", result)
        write(output / "COMPLETED.json", {"result_sha256": sha(output / "RESULT.json")})
        return descriptor(output / "RESULT.json")
    except BaseException as error:
        try:
            write(output / "FAILURE.json", {"state": "FAILED_OR_UNKNOWN_NO_REPLAY", "error_type": type(error).__name__})
        except Exception:
            pass  # The primary driver failure remains authoritative if storage is unavailable.
        raise


def result_directory(plan, workspace):
    path = Path(workspace).resolve() / ".orchestrator/qualifications" / plan["experiment_sha256"]
    resolved = contained(path, workspace)
    require(resolved == path, "Preserve redirected canonical qualification evidence")
    return path


def authority(runtime, plan, workspace, context):
    q = _common(runtime, context)
    require(q.get("request_sha256") == plan["request_sha256"]
            and runtime.get("project_id") == plan["frozen"]["proposal"]["id"],
            "Current request/project-bound qualification scope required")
    for key in ("wheelhouse", "assets_root"):
        contained(q[key], workspace)
    venv = Path(q["venv"])
    require(venv == LOCAL_RUNTIME_ROOT / EXPERIMENT_SHA256 / "venv"
            and LOCAL_RUNTIME_ROOT.resolve() == LOCAL_RUNTIME_ROOT
            and not LOCAL_RUNTIME_ROOT.is_symlink() and not venv.parent.exists(),
            "Fresh fixed local owned final venv required; preserve earlier files")
    ref = context.get("foundation_qualification_pre_storage")
    pre = exact_file(ref)
    require(pre == PRE_STORAGE_ROOT / EXPERIMENT_SHA256 / "RESULT.json", "Fixed same-runtime primary receipt required")
    value = read(pre, 65536)
    require(value.get("schema") == "earnalism.foundation_pre_storage_result.v1"
            and value.get("authority_sha256") == runtime["sha256"]
            and value.get("provider_runtime_id") == q["provider_runtime_id"]
            and value.get("allocation_started_at") == runtime["allocation_started_at"]
            and value.get("original_deadline_epoch") == runtime["original_deadline_epoch"]
            and value.get("provider_python") == q["provider_python"]
            and value.get("experiment_sha256") == plan["experiment_sha256"],
            "Actual same-authority pre-storage evidence required; no old lookup receipt")
    # Rehash the resolved actual driver after Drive; the old lookup is not CUDA evidence.
    exact_file(value["provider_binding"]["library"], check=lambda: _check(runtime, context))
    return q, value


def _env(cuda=False):
    env = {"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONNOUSERSITE": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
           "HF_HUB_DISABLE_TELEMETRY": "1", "DO_NOT_TRACK": "1", "WANDB_DISABLED": "true"}
    if not cuda:
        env.update(CUDA_VISIBLE_DEVICES="", PIP_CONFIG_FILE="/dev/null", PIP_NO_CACHE_DIR="1")
    return env


def _run(argv, log, runtime, context, *, cuda=False):
    from scripts import earnalism_voice as voice
    _check(runtime, context); process = None; started = time.time()
    try:
        with Path(log).open("xb") as stream:
            process = subprocess.Popen(argv, env=_env(cuda), stdin=subprocess.DEVNULL,
                stdout=stream, stderr=subprocess.STDOUT, start_new_session=True,
                preexec_fn=lambda: voice._arm_child_containment(runtime["original_deadline_epoch"]))
            code = process.wait(timeout=_check(runtime, context))
        record = {"argv": argv, "started_at": started, "completed_at": time.time(),
                  "exit_code": code, "raw_log": descriptor(log)}
        write(Path(str(log) + ".receipt.json"), record)
        require(code == 0, "Qualification subprocess failed; preserve raw log, no replay")
        _check(runtime, context)
        return record
    except BaseException as error:
        try:
            voice._stop_owned_group(process)
            failure_receipt = Path(str(log) + ".failure.json")
            if Path(log).is_file() and not failure_receipt.exists():
                write(failure_receipt, {"argv": argv, "started_at": started, "completed_at": time.time(),
                    "exit_code": process.poll() if process is not None else None,
                    "error_type": type(error).__name__, "raw_log": descriptor(log)})
        except Exception:
            pass  # Preserve the primary process failure, including when its receipt cannot be saved.
        raise
    finally:
        primary = sys.exc_info()[0]
        try:
            voice._stop_owned_group(process)
        except Exception:
            if primary is None:
                raise


def _verify_inputs(plan, q, workspace, check):
    wheelhouse = contained(q["wheelhouse"], workspace)
    expected = {w["filename"] for w in plan["wheels"]}
    require(wheelhouse.is_dir() and {p.name for p in wheelhouse.iterdir()} == expected,
            "Exactly111 retained wheel files required; no checkpoint or extras")
    for row in plan["wheels"]:
        exact_file({**row, "path": str(wheelhouse / row["filename"])}, check=check)
    assets = plan["frozen"]["proposal"]["future_comparability_requirements"]["foundation_and_tokenizers"]
    root = contained(q["assets_root"], workspace)
    for row in assets["files"]:
        exact_file(row, root, check)
    expected_media = plan["frozen"]["proposal"]["comparison"]["historical_adapted"]["outputs"] + \
        plan["frozen"]["proposal"]["preservation"]["soundtrack_and_selected_style"]
    require(len(q.get("preserved_media", [])) == 4, "Both rejected takes and exact soundtrack/style required")
    for actual, original in zip(q["preserved_media"], expected_media):
        require(actual.get("bytes") == original["bytes"] and actual.get("sha256") == original["sha256"],
                "Preserved original identity changed")
        exact_file(actual, Path(workspace), check)
    reference = plan["frozen"]["proposal"]["reference"]
    exact_file({"path": reference["path"], "bytes": reference["bytes"], "sha256": reference["sha256"]},
               Path(plan["frozen"]["proposal_path"]).parent, check)
    return {"wheel_files": 111, "asset_files": len(assets["files"]), "preserved_media": 4,
            "reference_sha256": plan["frozen"]["proposal"]["reference"]["sha256"],
            "large_binary_and_small_asset_hashes_verified_at_consumption": True,
            "adapted_checkpoint_parts": 0}


def qualify(plan, workspace, runtime, runtime_context):
    """Called only by the single controller while holding its private workspace lock."""
    from scripts import earnalism_voice as voice
    from scripts.earnalism_voice_runtime.setup import _english_install_commands
    q, pre = authority(runtime, plan, workspace, runtime_context)
    output = result_directory(plan, workspace)
    require(not output.exists(), "Consumed or unknown qualification attempt; no replay")
    output.mkdir(parents=True, exist_ok=False)
    intent = {"schema": "earnalism.foundation_qualification_intent.v1", "operation": OPERATION,
              "experiment_sha256": plan["experiment_sha256"], "request_sha256": plan["request_sha256"],
              "authority_sha256": runtime["sha256"], "scope_ref": runtime["scope_ref"],
              "provider_runtime_id": q["provider_runtime_id"], "at": time.time(),
              "allocation_started_at": runtime["allocation_started_at"],
              "original_deadline_epoch": runtime["original_deadline_epoch"], "model_loads": 0}
    write(output / "INTENT.json", intent)
    check = lambda: _check(runtime, runtime_context)
    try:
        write(output / "PRE-STORAGE.json", pre)
        inventory = _verify_inputs(plan, q, workspace, check)
        venv = Path(q["venv"])
        LOCAL_RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
        venv.parent.mkdir(exist_ok=False)
        disk = shutil.disk_usage(venv.parent)
        reserve = 2 * sum(w["bytes"] for w in plan["wheels"]) + 2 * 1024**3
        write(output / "STORAGE.json", {"path": str(venv.parent), "total": disk.total,
            "used": disk.used, "free": disk.free, "package_implementation_reserve": reserve,
            "reserve_is_not_total_operation_or_model_memory_requirement": True})
        require(disk.free >= reserve, "Insufficient package restoration reserve; no setup or retry")
        python = q["provider_python"]["path"]
        # The provider's existing pip supplies --python; no pip/bootstrap download.
        _run([python, "-I", "-m", "pip", "--python", python, "--version"],
             output / "provider-pip.log", runtime, runtime_context)
        requirements = output / "requirements.lock.txt"
        with requirements.open("x") as stream:
            stream.write(plan["requirements"]); stream.flush(); os.fsync(stream.fileno())
        commands = _english_install_commands(Path(python), venv, Path(q["wheelhouse"]), requirements)
        require(commands[1][0] == python, "Existing same provider pip interpreter required")
        for index, command in enumerate(commands):
            write(output / (str(index) + ".intent.json"), {"argv": command, "at": time.time()})
            _run(command, output / (str(index) + ".log"), runtime, runtime_context)
        helper = voice._owned_provider_helper()
        preload = helper.install_preload(pre["provider_binding"], venv / "lib/python3.12/site-packages", output)
        check()
        launcher = venv / "bin/python"; target = launcher.resolve(strict=True)
        interpreter = {"path": str(launcher), "resolved_path": str(target),
                       "bytes": target.stat().st_size, "sha256": sha(target, check)}
        probe_path = output / "PROBE-INPUT.json"
        write(probe_path, {"schema": "earnalism.foundation_CUDA_probe_input.v1",
            "authority_sha256": runtime["sha256"], "scope_ref": runtime["scope_ref"],
            "authority_path": runtime["path"], "project_id": runtime["project_id"],
            "runtime_context": runtime_context,
            "request_path": plan["request_path"], "workspace": str(Path(workspace).resolve()),
            "original_deadline_epoch": runtime["original_deadline_epoch"],
            "parent_pid": os.getpid(), "software": software(), "packages": plan["packages"],
            "runtime_interpreter": interpreter, "provider_preload": preload,
            "experiment_sha256": plan["experiment_sha256"], "provider_runtime_id": q["provider_runtime_id"]})
        _run([str(launcher), "-I", "-B", str(Path(__file__).resolve()), "_probe", str(probe_path)],
             output / "CUDA-probe.log", runtime, runtime_context, cuda=True)
        probe = read(output / "CUDA-PROBE.json")
        require(probe.get("state") == "ACTUAL_TINY_CUDA_OPERATION_PASSED_NOT_MODEL_QUALIFIED"
                and probe.get("sum") == 5.0 and probe.get("model_loads") == 0,
                "Actual tiny CUDA receipt required; no model qualification inferred")
        result = {"schema": "earnalism.foundation_qualification_result.v1",
            "state": "ACTUAL_PACKAGES_AND_TINY_CUDA_PASSED_NOT_MODEL_READY", **intent,
            "runtime_interpreter": interpreter, "provider_driver_preload": descriptor(output / "PROVIDER-DRIVER-PRELOAD.json"),
            "package_versions": plan["packages"], "CUDA_probe": descriptor(output / "CUDA-PROBE.json"),
            "inventory": inventory, "assets_root": q["assets_root"], "preserved_media": q["preserved_media"],
            "actual_artifacts": [descriptor(p) for p in sorted(output.iterdir()) if p.is_file()],
            "generation_calls": 0, "training_updates": 0, "runtime_qualified_for_tiny_operation_only": True,
            "model_ready": False, "voice_accepted": False, "production_ready": False,
            "authority_created_or_modified": False, "diagnostic_dispatched": False}
        # Keep the result schema separate from the intent schema.
        result["schema"] = "earnalism.foundation_qualification_result.v1"
        check(); write(output / "RESULT.json", result)
        write(output / "COMPLETED.json", {"result_sha256": sha(output / "RESULT.json")})
        return result
    except BaseException as error:
        try:
            write(output / "FAILURE.json", {"state": "FAILED_OR_UNKNOWN_NO_REPLAY", "error_type": type(error).__name__,
                "model_loads": 0, "generation_calls": 0, "training_updates": 0, "production_ready": False})
        except Exception:
            pass  # Partial files/intent remain spent; secondary disk errors must not hide the cause.
        raise


def verify_result(plan, output):
    output = Path(output); result = read(output / "RESULT.json")
    require(read(output / "COMPLETED.json").get("result_sha256") == sha(output / "RESULT.json")
            and result.get("schema") == "earnalism.foundation_qualification_result.v1"
            and result.get("experiment_sha256") == plan["experiment_sha256"]
            and result.get("state") == "ACTUAL_PACKAGES_AND_TINY_CUDA_PASSED_NOT_MODEL_READY"
            and [result.get(k) for k in ("model_loads", "generation_calls", "training_updates")] == [0, 0, 0]
            and result.get("model_ready") is False and result.get("voice_accepted") is False
            and result.get("production_ready") is False and result.get("diagnostic_dispatched") is False,
            "Completed exact qualification evidence required; no replay or model acceptance")
    for row in result["actual_artifacts"]:
        # Silent successful logs are evidence; consumed inputs still require bytes > 0.
        exact_file(row, output, allow_empty_log=True)
    return {**result, "retained_verified": True, "status_only": True, "current_runtime_admitted": False}


def _probe(path):
    """Fixed isolated child: explicit provider preload, package metadata, one tiny sum."""
    from scripts import earnalism_voice as voice, earnalism_orchestrator as engine
    path = Path(path); value = read(path); output = path.parent
    require(value["schema"] == "earnalism.foundation_CUDA_probe_input.v1"
            and value["software"] == software() and value["experiment_sha256"] == EXPERIMENT_SHA256
            and os.getppid() == value["parent_pid"], "Owned fixed fresh qualification probe required")
    original = engine._runtime(value["authority_path"], {"id": value["project_id"]},
        Path(value["authority_path"]).parent, value["runtime_context"])
    capability = original.get("foundation_qualification", {}) if original else {}
    require(original is not None and original["sha256"] == value["authority_sha256"]
            and original["scope_ref"] == value["scope_ref"]
            and value["original_deadline_epoch"] == original["original_deadline_epoch"]
            and "foundation_diagnostic" not in original
            and original.get("max_model_stage_starts") == 1
            and original.get("stage_attempt_limits") == {"foundation-diagnostic": 1}
            and capability.get("operation") == OPERATION
            and capability.get("purpose") == "private-environment-qualification"
            and capability.get("recipe_sha256") == RECIPE_SHA256
            and capability.get("wheel_manifest_sha256") == WHEELS_SHA256
            and capability.get("experiment_sha256") == EXPERIMENT_SHA256
            and capability.get("software") == software()
            and value.get("provider_runtime_id") == capability.get("provider_runtime_id")
            and all(type(capability.get(k)) is int and capability[k] == v for k, v in COUNTS.items()),
            "Probe cannot borrow a disabled or different capability")
    interpreter = value["runtime_interpreter"]
    venv = LOCAL_RUNTIME_ROOT / EXPERIMENT_SHA256 / "venv"
    require(Path(capability["venv"]) == venv and venv.resolve() == venv
            and interpreter["path"] == str(venv / "bin/python")
            and str(Path(sys.executable).absolute()) == interpreter["path"]
            and interpreter["bytes"] == capability["provider_python"]["bytes"]
            and interpreter["sha256"] == capability["provider_python"]["sha256"],
            "Probe must use the original capability's final owned interpreter")
    primary = exact_file(value["runtime_context"]["foundation_qualification_pre_storage"])
    require(primary == PRE_STORAGE_ROOT / EXPERIMENT_SHA256 / "RESULT.json"
            and primary.resolve() == primary, "Fixed same-allocation primary driver receipt required")
    pre = read(primary, 65536)
    require(pre.get("schema") == "earnalism.foundation_pre_storage_result.v1"
            and pre.get("state") == "ACTUAL_DRIVER_LOOKUP_ONLY_NOT_CUDA_QUALIFIED"
            and pre.get("authority_sha256") == original["sha256"]
            and pre.get("provider_runtime_id") == capability["provider_runtime_id"]
            and pre.get("allocation_started_at") == original["allocation_started_at"]
            and pre.get("original_deadline_epoch") == original["original_deadline_epoch"]
            and pre.get("experiment_sha256") == EXPERIMENT_SHA256
            and pre.get("provider_python") == capability["provider_python"]
            and value["provider_preload"]["provider_binding"] == pre["provider_binding"],
            "Probe driver/preload identity must match the original pre-storage observation")
    voice._arm_child_containment(original["original_deadline_epoch"])
    plan = validate(value["request_path"], value["workspace"])
    require(plan["request_sha256"] == original["foundation_qualification"]["request_sha256"]
            and value["packages"] == plan["packages"]
            and path.resolve() == result_directory(plan, value["workspace"]) / "PROBE-INPUT.json",
            "Probe must bind the actual frozen request and canonical experiment output")
    require(sys.platform == "linux" and platform.machine() == "x86_64" and sys.version_info[:2] == (3, 12)
            and time.time() < value["original_deadline_epoch"], "Actual original Linux CP312 child required")
    require(not any(n == "torch" or n.startswith(("torch.", "parler_tts", "transformers")) for n in sys.modules),
            "Fresh child before ML imports required")
    write(output / "CUDA-PROBE-CLAIM.json", {"pid": os.getpid(), "at": time.time()})
    require(str(Path(sys.executable).absolute()) == interpreter["path"]
            and Path(interpreter["path"]).resolve() == exact_file({**interpreter, "path": interpreter["resolved_path"]}),
            "Exact final owned interpreter required")
    actual = {name: importlib.metadata.version(name) for name in value["packages"]}
    require(actual == value["packages"] and len(actual) == 111, "Exact111 installed versions required")
    preload = value["provider_preload"]; helper = voice._owned_provider_helper()
    require(preload["bootstrap"]["path"] == str(Path(sys.executable).parent.parent / "lib/python3.12/site-packages/sitecustomize.py")
            and preload["explicit_bootstrap_mode"] == helper.EXPLICIT_MODE
            and preload["explicit_module_name"] == helper.OWNED_MODULE, "Final same-venv fixed bootstrap required")
    helper.load_exact_preload(preload["provider_binding"]["library"], preload["bootstrap"])
    import torch
    require(torch.cuda.is_available(), "Actual CUDA0 required; no CPU fallback")
    started = time.time()
    item = torch.tensor([2.0, 3.0], dtype=torch.float32, device="cuda:0").sum()
    torch.cuda.synchronize(0); total = float(item.item())
    require(total == 5.0 and time.time() < value["original_deadline_epoch"], "Tiny FP32 CUDA sum failed or expired")
    free, memory_total = torch.cuda.mem_get_info(0)
    write(output / "CUDA-PROBE.json", {"schema": "earnalism.foundation_tiny_CUDA_result.v1",
        "state": "ACTUAL_TINY_CUDA_OPERATION_PASSED_NOT_MODEL_QUALIFIED", "sum": total,
        "python": sys.version, "system": sys.platform, "machine": platform.machine(),
        "actual_package_versions": actual, "torch_version": torch.__version__, "torch_CUDA_version": torch.version.cuda,
        "device": "cuda:0", "device_name": torch.cuda.get_device_name(0),
        "device_capability": list(torch.cuda.get_device_capability(0)), "VRAM_free_bytes": free,
        "VRAM_total_bytes": memory_total, "started_at": started, "completed_at": time.time(),
        "model_loads": 0, "generation_calls": 0, "training_updates": 0, "model_ready": False,
        "production_ready": False, "no_model_fit_or_quality_claim": True})


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["_probe"])
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    _probe(args.input)
