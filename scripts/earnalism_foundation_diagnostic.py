"""Frozen private foundation controls. No setup, downloads, training or publishing."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import wave

OPERATION = "foundation-diagnostic"
PROPOSAL_SHA256 = "fd565bf83f4576a4502a0a48978a0392ad02a7182f8366dc2d7a73b239df3a72"
IDENTITY = "UNADAPTED_FOUNDATION_DIAGNOSTIC_NOT_THE_EARNALISM_VOICE"
INPUTS = {
    "adapted-job.original.json": "c0209a1d5392b46ecd8d1cae9969639dcd8a20f1aa0c2e94be9409f89003da91",
    "adapted-profile.original.json": "55bfe57ff90052c81a551f7b00473833ffd9de384b54dd93afaad45e67e8e71a",
    "adapted-result.original.json": "0941073b16c70a86b2db70fccc8159ca0fd32f785f88ba91e74d8c5fc2eb1774",
    "full-original-clip2.wav": "ff6a1350955abfdf726d2b4f0dd7b81879e52828de6b4abfead0372d9b987976",
    "media-preservation.prior.json": "436041ec9ce5c46dd156f4780a0a44e17a10a23c19f18c32f39efc5a32aef5d5",
    "owner-reference-selection.json": "965158c065219f1eb09a7fa475a13f6653fa3994c6e5dbd56836721abc9a3ad7",
    "owner-rejection.json": "25131c1fa0ccb5f83fb19c9f7356ddf75b0317576d9b18611fca2df3422838f6",
    "reference-provenance.json": "3c799177553226d481a44dce6f19334ac2b6c817b9d697960e474af2003ea7e3",
    "two-scenes.spoken.txt": "0704b331e7e1d9bbd8f83b42a9dd728e46ae7a52c252d0c0a2bcec0d649fd8b8",
}
SOFTWARE = (
    "scripts/earnalism_orchestrator.py", "scripts/earnalism_foundation_diagnostic.py",
    "scripts/earnalism_voice.py", "scripts/earnalism_voice_runtime/foundation.py",
    "scripts/earnalism_voice_runtime/parler.py", "scripts/earnalism_voice_runtime/position_table.py",
    "scripts/earnalism_voice_runtime/provider_driver_bootstrap.py",
)
ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 1024**2,
            "Bounded regular diagnostic metadata required")
    return json.loads(path.read_text(encoding="utf-8"))


def contained(raw, workspace):
    path = Path(raw).expanduser().resolve()
    require(path.is_relative_to(Path(workspace).resolve()), "Diagnostic files must stay private")
    return path


def software():
    return {name: sha(ROOT / name) for name in SOFTWARE}


def validate(proposal_path, workspace):
    path = contained(proposal_path, workspace)
    require(sha(path) == PROPOSAL_SHA256, "Exact frozen proposal required; no parameter search")
    proposal = read(path); folder = path.parent
    require(proposal["schema"] == "earnalism.controlled_voice_repair_proposal.v1"
            and all(v is False for v in proposal["execution"].values())
            and proposal["runtime_authority"] is None, "Proposal is not execution authority")
    for name, expected in INPUTS.items():
        source = contained(folder / "inputs" / name, folder)
        require(source.is_file() and not source.is_symlink() and sha(source) == expected,
                "Frozen private input changed: " + name)
    profile = read(folder / "inputs/adapted-profile.original.json")
    job = read(folder / "inputs/adapted-job.original.json")
    reference = proposal["reference"]
    with wave.open(str(folder / reference["path"]), "rb") as wav:
        require((wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()) ==
                (1, 2, 16000, 76800), "Complete original 4.8-second Clip2 required")
    require(not any(reference[k] for k in ("waveform_conditioning", "speaker_transfer", "training_input")),
            "Reference is a human comparator only")
    baseline = proposal["comparison"]["proposed_foundation"]
    require(baseline["identity"] == IDENTITY and baseline["base"] == profile["base"]
            and baseline["generation"] == job["generation"]
            and baseline["native_output_bounds"] == job["limits"], "Frozen foundation controls changed")
    source = (folder / "inputs/two-scenes.spoken.txt").read_text(encoding="utf-8")
    require(len(baseline["units"]) == len(job["units"]) == 2, "Exactly two fixed controls required")
    for planned, original in zip(baseline["units"], job["units"]):
        expected = {k: original[k] for k in ("id", "start", "end", "spoken_text", "caption_unspoken", "seed")}
        require({k: v for k, v in planned.items() if k != "planned_binding_sha256"} == expected
                and source[planned["start"]:planned["end"]] == planned["spoken_text"],
                "Exact source spans, captions and seeds required")
    experiment = canonical({"schema": "earnalism.foundation_experiment.v1", "base": baseline["base"],
        "units": baseline["units"], "generation": baseline["generation"],
        "bounds": baseline["native_output_bounds"],
        "comparability": proposal["future_comparability_requirements"],
        "reference": reference["sha256"]})
    return {"proposal": proposal, "profile": profile, "proposal_path": str(path),
            "proposal_sha256": PROPOSAL_SHA256, "experiment_sha256": experiment,
            "unit_fingerprints": [u["planned_binding_sha256"] for u in baseline["units"]]}


def summary(plan):
    return {"schema": "earnalism.foundation_diagnostic_plan.v1", "operation": OPERATION,
        "state": "PRIVATE_DIAGNOSTIC_PREPARED_EXECUTION_DISABLED", "identity": IDENTITY,
        "proposal_sha256": plan["proposal_sha256"], "experiment_sha256": plan["experiment_sha256"],
        "reference_sha256": plan["proposal"]["reference"]["sha256"], "reference_seconds": 4.8,
        "proposed_model_loads": 1, "proposed_generation_calls": 2, "training_updates": 0,
        "execution_enabled": False, "runtime_authority": None, "compute_allowance": None,
        "production_ready": False, "qualification_ready": False, "narration_bindings": False,
        "next_action": "Review disabled source; bind fresh complete-operation authority before runtime work"}


def result_directory(plan, workspace):
    return contained(Path(workspace) / ".orchestrator/diagnostics" / plan["experiment_sha256"], workspace)


def verify_result(plan, output):
    result = read(output / "RESULT.json")
    require(result.get("schema") == "earnalism.foundation_diagnostic_result.v1"
            and result.get("identity") == IDENTITY
            and result.get("experiment_sha256") == plan["experiment_sha256"]
            and result.get("production_ready") is False
            and result.get("qualification_ready") is False
            and not result.get("bindings"), "Diagnostic result cannot satisfy narration or release")
    require(len(result.get("outputs", [])) == 2, "Both complete diagnostic outputs required")
    for unit, item, fingerprint in zip(plan["proposal"]["comparison"]["proposed_foundation"]["units"],
                                       result["outputs"], plan["unit_fingerprints"]):
        require(item["unit"] == unit["id"] and item["fingerprint"] == fingerprint,
                "Exact diagnostic output identity required")
        for ref in [item, item["trace"]]:
            path = contained(output / ref["path"], output)
            require(path.is_file() and path.stat().st_size == ref["bytes"] and sha(path) == ref["sha256"],
                    "Retained diagnostic artifact changed; never regenerate it")
    return result


def _authority(runtime, plan, workspace):
    require("foundation_qualification" not in runtime,
            "Environment-qualification authority cannot dispatch the model diagnostic")
    value = runtime.get("foundation_diagnostic", {})
    require(runtime.get("project_id") == plan["proposal"]["id"]
            and runtime.get("max_model_stage_starts") == 1
            and runtime.get("stage_attempt_limits") == {OPERATION: 1}
            and value.get("operation") == OPERATION and value.get("purpose") == "private-diagnostic"
            and value.get("proposal_sha256") == plan["proposal_sha256"]
            and value.get("experiment_sha256") == plan["experiment_sha256"]
            and value.get("software") == software()
            and all(type(value.get(k)) is int for k in
                    ("model_loads", "generation_calls", "adapted_restores", "training_updates"))
            and [value.get(k) for k in ("model_loads", "generation_calls", "adapted_restores", "training_updates")]
                == [1, 2, 0, 0], "Fresh exact diagnostic scope required; old voice grants cannot dispatch it")
    contained(value["assets_root"], workspace)
    from scripts import earnalism_voice as voice
    preload = voice._json(voice._descriptor(Path(runtime["path"]).parent, value["provider_driver_preload"]))
    helper = voice._owned_provider_helper(); binding = preload.get("provider_binding", {})
    require(preload.get("explicit_bootstrap_mode") == helper.EXPLICIT_MODE
            and preload.get("explicit_module_name") == helper.OWNED_MODULE
            and binding.get("library_family") == "CUDA_DRIVER"
            and binding.get("soname") == "libcuda.so.1", "Fixed explicit provider bootstrap required")
    interpreter = value["runtime_interpreter"]; launcher = Path(interpreter["path"])
    target = voice._descriptor(Path(runtime["path"]).parent,
                               {**interpreter, "path": interpreter["resolved_path"]})
    require(launcher.name == "python" and launcher.parent.name == "bin"
            and launcher.resolve(strict=True) == target and os.access(launcher, os.X_OK),
            "Hash-bound existing CPython interpreter required; no installation route")
    require(preload["bootstrap"]["path"] == str(launcher.parent.parent / "lib/python3.12/site-packages/sitecustomize.py")
            and Path(preload["bootstrap"]["path"]).read_text() == helper.render_preload_source(binding["library"]),
            "Exact existing runtime bootstrap required")
    preserved = value.get("preserved_media", [])
    expected = plan["proposal"]["comparison"]["historical_adapted"]["outputs"] + \
               plan["proposal"]["preservation"]["soundtrack_and_selected_style"]
    require(len(preserved) == len(expected) == 4, "Retain both rejected takes and exact soundtrack/style")
    for ref, original in zip(preserved, expected):
        path = contained(ref["path"], workspace)
        require(ref["sha256"] == original["sha256"] and ref["bytes"] == original["bytes"]
                and path.stat().st_size == ref["bytes"] and sha(path) == ref["sha256"],
                "Preserved original media changed")
    return value


def render(plan, workspace, runtime, runtime_context):
    """Caller holds the common workspace lock and has reserved one model start."""
    from scripts import earnalism_voice as voice
    value = _authority(runtime, plan, workspace); output = result_directory(plan, workspace)
    require(not output.exists(), "Consumed or unknown diagnostic attempt; no replay")
    output.mkdir(parents=True, exist_ok=False)
    intent = {"proposal_sha256": plan["proposal_sha256"], "experiment_sha256": plan["experiment_sha256"],
              "authority_sha256": runtime["sha256"], "parent_pid": os.getpid(),
              "runtime_context": runtime_context, "original_deadline": runtime["original_deadline_epoch"]}
    voice._write(output / "INTENT.json", intent)
    journal = contained(Path(workspace) / ".orchestrator/diagnostics.jsonl", workspace)
    voice._append(journal, {"event": "foundation_intent", **intent})
    env = {"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONNOUSERSITE": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
           "HF_HUB_DISABLE_TELEMETRY": "1", "DO_NOT_TRACK": "1", "WANDB_DISABLED": "true"}
    process = None
    try:
        with (output / "worker.log").open("xb") as log:
            process = subprocess.Popen([value["runtime_interpreter"]["path"], "-I", "-B",
                str(Path(__file__).resolve()), "_worker", str(Path(plan["proposal_path"]).resolve()),
                str(Path(workspace).resolve()), runtime["path"], str(output)],
                env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True)
            code = process.wait(timeout=max(0.01, runtime["original_deadline_epoch"] - time.time()))
            require(code == 0, "Diagnostic failed or unknown; preserve evidence, no replay")
        result = verify_result(plan, output); _authority(runtime, plan, workspace)
        voice._append(journal, {"event": "foundation_completed", "experiment_sha256": plan["experiment_sha256"],
                              "result_sha256": sha(output / "RESULT.json")})
        voice._write(output / "COMPLETED.json", {"result_sha256": sha(output / "RESULT.json")})
        return result
    except BaseException as error:
        voice._append(journal, {"event": "foundation_failed_or_unknown",
            "experiment_sha256": plan["experiment_sha256"], "error_type": type(error).__name__})
        voice._write(output / "FAILURE.json", {"state": "FAILED_OR_UNKNOWN_NO_REPLAY",
            "error_type": type(error).__name__, "production_ready": False})
        raise
    finally:
        voice._stop_owned_group(process)


def _worker(proposal_path, workspace, authority_path, output):
    from scripts import earnalism_orchestrator as engine, earnalism_voice as voice
    output = Path(output); plan = validate(proposal_path, workspace); intent = read(output / "INTENT.json")
    require(output.resolve() == result_directory(plan, workspace).resolve()
            and intent["proposal_sha256"] == plan["proposal_sha256"]
            and intent["authority_sha256"] == sha(authority_path)
            and intent["parent_pid"] == os.getppid()
            and not (output / "WORKER-INTENT.json").exists(), "One original owned worker intent required")
    events = [json.loads(line) for line in (Path(workspace) / ".orchestrator/diagnostics.jsonl").read_text().splitlines()]
    require(all(isinstance(e, dict) for e in events), "Unknown diagnostic journal tail")
    expected = {"event": "foundation_intent", **intent}
    require(sum(all(e.get(k) == v for k, v in expected.items()) for e in events) == 1,
            "One original journal reservation required")
    def check():
        fresh = validate(proposal_path, workspace)
        require(fresh["experiment_sha256"] == plan["experiment_sha256"]
                and sha(authority_path) == intent["authority_sha256"], "Original diagnostic bindings changed")
        return engine._runtime(authority_path, {"id": plan["proposal"]["id"]}, Path(workspace),
                               intent["runtime_context"])
    runtime = check()
    require(sys.platform == "linux" and platform.machine() == "x86_64"
            and sys.version_info[:2] == (3, 12), "Actual pinned Linux CPython 3.12 required")
    voice._arm_child_containment(runtime["original_deadline_epoch"], expected_parent_pid=intent["parent_pid"])
    value = _authority(runtime, plan, workspace)
    require(Path(sys.executable).absolute() == Path(value["runtime_interpreter"]["path"]).absolute(),
            "Owned worker is not the selected interpreter")
    voice._load_owned_provider_in_this_process(
        {"provider_driver_preload": value["provider_driver_preload"]}, Path(runtime["path"]).parent)
    with (output / "WORKER-INTENT.json").open("x") as handle:
        json.dump({"experiment_sha256": plan["experiment_sha256"], "model_loading_started": True}, handle)
        handle.flush(); os.fsync(handle.fileno())
    from scripts.earnalism_voice_runtime import foundation
    return foundation.run(plan, Path(value["assets_root"]), output, check=check,
        write_json=voice._write,
        append_event=lambda event: voice._append(Path(workspace) / ".orchestrator/diagnostics.jsonl", event))


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    require(len(sys.argv) == 6 and sys.argv[1] == "_worker", "Use the orchestrator diagnostic operation")
    _worker(*sys.argv[2:])
