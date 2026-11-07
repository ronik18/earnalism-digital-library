"""Earnalism local-only Qwen3-TTS CustomVoice worker, revision 1.

Usage: /path/to/qwen-venv/bin/python qwen_worker.py /absolute/job.json
No network downloads, production writes, voice cloning, or publishing occur here.
Mechanical PASS is not text completeness, pronunciation, or listening approval.
"""
from __future__ import annotations
from owner_audio_policy import AudioGenerationExcluded, assert_audio_allowed, audio_exclusion_reason, audio_identity

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone

MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
SCHEMA = "earnalism.qwen.customvoice.v1"
GENERATION_DEFAULTS = {
    "max_new_tokens": 2048,
    "do_sample": True,
    "top_k": 50,
    "top_p": 1.0,
    "temperature": 0.9,
    "repetition_penalty": 1.05,
    "subtalker_dosample": True,
    "subtalker_top_k": 50,
    "subtalker_top_p": 1.0,
    "subtalker_temperature": 0.9,
}
VALIDATION_DEFAULTS = {
    "max_segment_seconds": 120.0,
    "min_segment_seconds": 0.25,
    "min_rms": 0.0001,
    "max_peak": 1.0,
    "max_clipped_sample_fraction": 0.0001,
    "min_words_per_minute": 45.0,
    "max_words_per_minute": 340.0,
}


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def object_hash(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require_absolute(value, name):
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f"{name} must be an absolute local path")
    return path


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp.{os.getpid()}")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def journal(path, event):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical({"at": utcnow(), **event}) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def read_journal(path):
    path = Path(path)
    if not path.exists():
        return []
    events = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            # An incomplete trailing write must not erase the counted attempts.
            raise RuntimeError(f"Journal damaged at line {index+1}; restore/repair explicitly before retrying") from exc
    return events


def validate_job(job):
    assert_audio_allowed(job, require_identity=True)
    if job.get("model_id") != MODEL_ID:
        raise ValueError(f"Only {MODEL_ID} is supported")
    revision = job.get("model_revision", "")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("model_revision must be an exact 40-character HF commit SHA")
    model_path = require_absolute(job["model_path"], "model_path")
    if model_path.name != revision or model_path.parent.name != "snapshots":
        raise ValueError("Use the snapshot_download return path ending snapshots/<model_revision>")
    expected_cache = "models--" + MODEL_ID.replace("/", "--")
    if model_path.parent.parent.name != expected_cache:
        raise ValueError("Model snapshot must belong to the exact requested Hugging Face repository")
    config = json.loads((model_path / "config.json").read_text(encoding="utf-8"))
    identity = (config.get("model_type"), config.get("tts_model_size"), config.get("tts_model_type"), config.get("tokenizer_type"))
    if identity != ("qwen3_tts", "1b7", "custom_voice", "qwen3_tts_tokenizer_12hz"):
        raise ValueError(f"Unexpected snapshot model identity: {identity}")
    if not (model_path / "speech_tokenizer").is_dir():
        raise ValueError("Snapshot must include its bundled speech_tokenizer, without a floating external download")
    for key in ("journal_path", "report_path"):
        require_absolute(job[key], key)
    if job.get("stop_flag_path"):
        require_absolute(job["stop_flag_path"], "stop_flag_path")
    if not isinstance(job.get("max_attempts", 3), int) or not 1 <= job.get("max_attempts", 3) <= 3:
        raise ValueError("max_attempts must be 1, 2, or 3 across resumptions for unchanged effective settings")
    if job.get("device", "cuda:0") != "cuda:0":
        raise ValueError("This Colab worker requires exactly one CUDA GPU at cuda:0")
    if job.get("dtype", "auto") not in ("auto", "bfloat16", "float32", "float16"):
        raise ValueError("dtype must be auto, bfloat16, float32, or float16")
    if job.get("attention", "eager") not in ("eager", "sdpa"):
        raise ValueError("attention must be eager or sdpa; FlashAttention 2 is intentionally excluded")
    overrides = job.get("generation", {})
    if set(overrides) - GENERATION_DEFAULTS.keys():
        raise ValueError(f"Unsupported generation keys: {sorted(set(overrides) - GENERATION_DEFAULTS.keys())}")
    generation = {**GENERATION_DEFAULTS, **overrides}
    if not isinstance(generation["max_new_tokens"], int) or not 256 <= generation["max_new_tokens"] <= 4096:
        raise ValueError("max_new_tokens must be an integer 256..4096; split long text instead of raising the cap indefinitely")
    for name in ("temperature", "subtalker_temperature"):
        if not isinstance(generation[name], (int, float)) or not 0.1 <= generation[name] <= 1.5:
            raise ValueError(f"{name} must be within 0.1..1.5")
    for name in ("top_p", "subtalker_top_p"):
        if not 0 < generation[name] <= 1:
            raise ValueError(f"{name} must be >0 and <=1")
    for name in ("top_k", "subtalker_top_k"):
        if not isinstance(generation[name], int) or not 1 <= generation[name] <= 100:
            raise ValueError(f"{name} must be an integer 1..100")
    if not 1 <= generation["repetition_penalty"] <= 1.5:
        raise ValueError("repetition_penalty must be 1..1.5")
    for name in ("do_sample", "subtalker_dosample"):
        if not isinstance(generation[name], bool):
            raise ValueError(f"{name} must be boolean")
    validation = {**VALIDATION_DEFAULTS, **job.get("validation", {})}
    if set(validation) != set(VALIDATION_DEFAULTS):
        raise ValueError("Unknown validation setting")
    if any(not isinstance(v, (float, int)) or not math.isfinite(v) or v <= 0 for v in validation.values()):
        raise ValueError("Validation thresholds must be finite and positive")
    if validation["max_peak"] > 1.0 or validation["max_clipped_sample_fraction"] > 0.001:
        raise ValueError("Cannot relax the worker's hard clipping limits")
    segments = job.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("segments must be a nonempty list")
    ids, paths = set(), set()
    protected = {str(Path(job[k]).resolve()) for k in ("journal_path", "report_path")}
    if job.get("stop_flag_path"):
        protected.add(str(Path(job["stop_flag_path"]).resolve()))
    for segment in segments:
        if not isinstance(segment.get("segment_id"), str) or not segment["segment_id"] or segment["segment_id"] in ids:
            raise ValueError("Each segment needs a unique nonempty segment_id")
        ids.add(segment["segment_id"])
        for key in ("text", "instruct", "cache_key"):
            if not isinstance(segment.get(key), str) or not segment[key].strip():
                raise ValueError(f"Segment {segment['segment_id']} has empty or invalid {key}")
        if len(segment["text"]) > 2400 or len(segment["text"].split()) > 350:
            raise ValueError(f"Segment {segment['segment_id']} is too long; resegment before synthesis")
        if len(segment["instruct"]) > 2000:
            raise ValueError("Instruction is too long; use a compact narrator and scene prompt")
        if segment.get("speaker") not in ("Ryan", "Aiden"):
            raise ValueError("Use the native-English stock speaker Ryan or Aiden")
        if not isinstance(segment.get("seed"), int) or not 0 <= segment["seed"] <= 2**32-1:
            raise ValueError("seed must be an integer within 0..2**32-1")
        output = require_absolute(segment["output_path"], "output_path")
        resolved = str(output.resolve())
        if output.suffix.lower() != ".wav" or resolved in paths or resolved in protected:
            raise ValueError("Each output must have a unique .wav path distinct from metadata paths")
        if model_path.resolve() in output.resolve().parents:
            raise ValueError("Outputs must not modify the pinned model snapshot")
        paths.add(resolved)
    return generation, validation


def snapshot_manifest(model_path):
    files = []
    for path in sorted(Path(model_path).rglob("*")):
        if path.is_file():
            files.append({"path": path.relative_to(model_path).as_posix(), "bytes": path.stat().st_size, "sha256": file_hash(path)})
    if not any(row["path"].endswith(".safetensors") for row in files):
        raise ValueError("The complete snapshot has no safetensors weights")
    return {"files": files, "manifest_sha256": object_hash(files)}


def select_precision(torch, requested):
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU missing: select a Colab GPU runtime before generation")
    major, minor = torch.cuda.get_device_capability(0)
    # Native BF16 begins at Ampere. Do not accept software-emulated BF16 on a T4.
    native_bf16 = major >= 8 and bool(torch.cuda.is_bf16_supported())
    resolved = ("bfloat16" if native_bf16 else "float32") if requested == "auto" else requested
    if resolved == "bfloat16" and not native_bf16:
        raise RuntimeError("Native BF16 is unsupported on this GPU. Use float32 or an explicitly probed float16 configuration")
    return resolved, {"device": "cuda:0", "name": torch.cuda.get_device_name(0), "compute_capability": [major, minor], "native_bfloat16": native_bf16}


def environment(torch):
    versions = {}
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name")
        if name:
            versions[name.lower()] = dist.version
    import qwen_tts
    package = Path(qwen_tts.__file__).parent
    source_files = [{"path": str(p.relative_to(package)), "sha256": file_hash(p)} for p in sorted(package.rglob("*.py"))]
    return {"python": platform.python_version(), "platform": platform.platform(), "executable": sys.executable,
            "packages": dict(sorted(versions.items())), "qwen_package_source_sha256": object_hash(source_files),
            "torch_cuda_version": torch.version.cuda, "torch_cudnn_version": torch.backends.cudnn.version()}


def set_seed(torch, np, seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False


def generate_measured(model, segment, generation, torch):
    """Use documented CustomVoice API; observe returned code lengths without altering codes.

    This intentionally inspects the pinned wrapper's call to model.generate.
    Code length near a cap is a suspicion gate, never proof that all words were spoken.
    """
    lengths = []
    original = model.model.generate

    def observed_generate(*args, **kwargs):
        result = original(*args, **kwargs)
        codes = result[0]
        if not isinstance(codes, list) or len(codes) != 1:
            raise RuntimeError("Pinned Qwen inner API changed: expected batch-one code list")
        lengths.extend(int(code.shape[0]) for code in codes)
        return result

    model.model.generate = observed_generate
    try:
        torch.cuda.synchronize()
        start = time.perf_counter()
        with torch.inference_mode():
            wavs, sample_rate = model.generate_custom_voice(
                text=segment["text"], language="English", speaker=segment["speaker"],
                instruct=segment["instruct"], non_streaming_mode=True, **generation)
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - start
    finally:
        model.model.generate = original
    if not isinstance(wavs, list) or len(wavs) != 1 or len(lengths) != 1:
        raise RuntimeError("Qwen returned an unexpected batch shape")
    return wavs[0], int(sample_rate), lengths[0], elapsed


def analyze_waveform(waveform, sample_rate, text, codec_frames, generation, validation, np):
    array = np.asarray(waveform, dtype=np.float32)
    failures = []
    if array.ndim != 1 or array.size == 0:
        raise ValueError("Expected one nonempty mono waveform")
    if sample_rate < 8000 or sample_rate > 192000:
        raise ValueError(f"Unexpected native sample rate: {sample_rate}")
    if not bool(np.isfinite(array).all()):
        raise ValueError("Waveform contains NaN or infinity")
    seconds = int(array.size) / sample_rate
    peak = float(np.max(np.abs(array)))
    rms = float(np.sqrt(np.mean(array.astype(np.float64)**2)))
    clipped = float(np.mean(np.abs(array) >= 0.9999))
    words = len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b", text, flags=re.UNICODE))
    wpm = words * 60 / seconds
    if not validation["min_segment_seconds"] <= seconds <= validation["max_segment_seconds"]:
        failures.append("duration_outside_guardrail")
    if peak >= validation["max_peak"] or clipped > validation["max_clipped_sample_fraction"]:
        failures.append("clipping_or_out_of_range_peak")
    if rms < validation["min_rms"]:
        failures.append("near_silent_output")
    # Short phrases contain large fixed silence overhead; pace screening starts at 12 words.
    if words >= 12 and not validation["min_words_per_minute"] <= wpm <= validation["max_words_per_minute"]:
        failures.append("suspicious_duration_for_text")
    if codec_frames >= generation["max_new_tokens"] - 2:
        failures.append("possible_token_cap_truncation")
    stats = {"sample_rate": int(sample_rate), "samples": int(array.size), "duration_seconds": seconds,
             "peak": peak, "rms": rms, "clipped_sample_fraction": clipped, "input_words": words,
             "estimated_words_per_minute": wpm, "codec_frames": codec_frames,
             "token_cap_suspicion": "possible_token_cap_truncation" in failures,
             "mechanical_checks": "PASS" if not failures else "FAIL", "failure_reasons": failures,
             "text_completeness": "UNVERIFIED_REQUIRES_ASR_AND_HUMAN_REVIEW",
             "human_listening_review": "PENDING"}
    return array, stats


def check_cache(segment, effective_key, sf):
    output = Path(segment["output_path"])
    sidecar = Path(str(output) + ".json")
    if not output.exists() or not sidecar.exists():
        return None
    try:
        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        if metadata.get("effective_key") != effective_key or metadata.get("status") != "GENERATED_REQUIRES_REVIEW":
            return None
        if metadata.get("wav_sha256") != file_hash(output):
            return None
        info = sf.info(output)
        stats = metadata["audio"]
        if info.frames != stats["samples"] or info.samplerate != stats["sample_rate"] or info.channels != 1:
            return None
        if stats.get("mechanical_checks") != "PASS":
            return None
        return metadata
    except (ValueError, OSError, KeyError, RuntimeError):
        return None


def run(job):
    generation, validation = validate_job(job)
    report = {"schema": SCHEMA, "started_at": utcnow(), "status": "RUNNING", "segments": [],
              "requested_segments": len(job["segments"]), "publication_approved": False,
              "no_guarantee": "Seeds are recorded; different GPU/software combinations may produce different audio."}
    lock_path = Path(tempfile.gettempdir()) / "earnalism-qwen-locks" / (object_hash(str(Path(job["journal_path"]).resolve())) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    # Local Linux advisory lock avoids DriveFS flock limitations.
    # Protects this Colab runtime; do not launch writers to the same Drive job from other runtimes.
    import fcntl
    lock_handle = lock_path.open("a")
    try:
        fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        lock_handle.close()
        raise RuntimeError("Another Qwen worker owns this journal; stop that worker before retrying") from exc
    try:
        atomic_json(job["report_path"], report)
        return _run_locked(job, generation, validation, report)
    except BaseException as exc:
        report.update(status="STOPPED" if isinstance(exc, KeyboardInterrupt) else "FAILED", finished_at=utcnow(),
                      error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
        atomic_json(job["report_path"], report)
        raise
    finally:
        fcntl.flock(lock_handle, fcntl.LOCK_UN)
        lock_handle.close()


def _run_locked(job, generation, validation, report):
    assert_audio_allowed(job, require_identity=True)
    def stop_requested():
        return bool(job.get("stop_flag_path") and Path(job["stop_flag_path"]).exists())

    if stop_requested():
        raise KeyboardInterrupt("Stop flag already present; no model was loaded")
    # Set before importing Hugging Face. Snapshots and all tokenizer files must exist.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    import numpy as np
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    precision, hardware = select_precision(torch, job.get("dtype", "auto"))
    provenance = {"model_id": MODEL_ID, "model_revision": job["model_revision"], "model_path": job["model_path"],
                  "snapshot": snapshot_manifest(job["model_path"]), "environment": environment(torch), "hardware": hardware,
                  "worker_sha256": file_hash(Path(__file__)), "dtype": precision, "attention": job.get("attention", "eager")}
    report["provenance"] = provenance
    # Include versions/source hashes/GPU/dtype in cache binding, without ephemeral runtime paths.
    env = provenance["environment"]
    provenance_binding = {"model_id": MODEL_ID, "model_revision": job["model_revision"],
                          "snapshot_sha256": provenance["snapshot"]["manifest_sha256"],
                          "python": env["python"], "packages": env["packages"],
                          "qwen_package_source_sha256": env["qwen_package_source_sha256"],
                          "torch_cuda_version": env["torch_cuda_version"], "torch_cudnn_version": env["torch_cudnn_version"],
                          "hardware": hardware, "worker_sha256": provenance["worker_sha256"]}
    started = time.perf_counter()
    model = Qwen3TTSModel.from_pretrained(job["model_path"], device_map="cuda:0", dtype=getattr(torch, precision),
                                        attn_implementation=job.get("attention", "eager"), local_files_only=True)
    report["model_load_elapsed_seconds"] = time.perf_counter() - started
    if getattr(model.model, "tts_model_type", None) != "custom_voice" or getattr(model.model, "tts_model_size", None) != "1b7":
        raise RuntimeError("Loaded object does not match 1.7B CustomVoice")
    supported = {str(s).lower() for s in (model.get_supported_speakers() or [])}
    if not {"ryan", "aiden"}.issubset(supported):
        raise RuntimeError("Expected native-English Ryan and Aiden speakers are unavailable")
    if "english" not in {str(s).lower() for s in (model.get_supported_languages() or [])}:
        raise RuntimeError("Loaded model does not report English support")
    report["supported_speakers"] = sorted(supported)
    probe = {"text": "At the window, the quiet morning began. She opened the book, paused, and read the first line.",
             "instruct": "Speak in clear, natural English, with calm expression and punctuation-aware pauses.", "speaker": "Ryan"}
    if stop_requested():
        raise KeyboardInterrupt("Stop flag before numerical probe")
    set_seed(torch, np, 17429)
    wave, sr, frames, elapsed = generate_measured(model, probe, generation, torch)
    _, probe_stats = analyze_waveform(wave, sr, probe["text"], frames, generation, validation, np)
    report["numerical_probe"] = {"dtype": precision, "seed": 17429, "elapsed_seconds": elapsed, "audio": probe_stats,
                                 "scope": "Mechanical output only; not a naturalness or linguistic evaluation"}
    atomic_json(job["report_path"], report)
    if probe_stats["mechanical_checks"] != "PASS":
        raise RuntimeError(f"Numerical probe failed for {precision}: {probe_stats['failure_reasons']}. No title segments generated")
    events = read_journal(job["journal_path"])
    attempts_budget = job.get("max_attempts", 3)
    for segment in job["segments"]:
        if stop_requested():
            raise KeyboardInterrupt("Stop flag between segments")
        settings = {"schema": SCHEMA, "source_cache_key": segment["cache_key"], "segment_id": segment["segment_id"],
                    "text": segment["text"], "instruct": segment["instruct"], "speaker": segment["speaker"], "language": "English",
                    "seed_base": segment["seed"], "retry_seed_rule": "(seed_base+attempt_number-1) modulo 2**32",
                    "non_streaming_mode": True, "batch_size": 1, "generation": generation, "validation": validation,
                    "dtype": precision, "attention": job.get("attention", "eager"), "wav_subtype": "FLOAT",
                    "provenance_binding": provenance_binding}
        key = object_hash(settings)
        cache = check_cache(segment, key, sf)
        if cache:
            result = {"segment_id": segment["segment_id"], "status": "CACHE_VERIFIED_REQUIRES_REVIEW", "output_path": segment["output_path"],
                      "effective_key": key, "wav_sha256": cache["wav_sha256"], "audio": cache["audio"],
                      "attempts": cache["attempts"], "generation_elapsed_seconds_total": cache["generation_elapsed_seconds_total"],
                      "rtf_generation_total": cache["rtf_generation_total"]}
            report["segments"].append(result)
            journal(job["journal_path"], {"event": "cache_verified", **result})
            atomic_json(job["report_path"], report)
            continue
        started_attempts = [e for e in events if e.get("event") == "attempt_started" and e.get("effective_key") == key]
        history = [e for e in events if e.get("event") == "attempt_finished" and e.get("effective_key") == key]
        used = max([e["attempt"] for e in started_attempts], default=0)
        generated = None
        for attempt in range(used + 1, attempts_budget + 1):
            if stop_requested():
                raise KeyboardInterrupt("Stop flag before retry")
            seed = (segment["seed"] + attempt - 1) % (2**32)
            event_base = {"segment_id": segment["segment_id"], "effective_key": key, "attempt": attempt, "seed": seed}
            event = {"event": "attempt_started", **event_base}
            journal(job["journal_path"], event)
            events.append(event)
            start = time.perf_counter()
            attempt_recorded = False
            try:
                set_seed(torch, np, seed)
                wave, sr, frames, elapsed = generate_measured(model, segment, generation, torch)
                array, stats = analyze_waveform(wave, sr, segment["text"], frames, generation, validation, np)
                record = {"event": "attempt_finished", **event_base, "status": stats["mechanical_checks"], "elapsed_seconds": elapsed,
                          "audio": stats, "rtf_generation": elapsed / stats["duration_seconds"]}
                history.append(record)
                journal(job["journal_path"], record)
                events.append(record)
                attempt_recorded = True
                if stats["mechanical_checks"] != "PASS":
                    # Do not write a failed take over a previously generated/cached WAV.
                    continue
                if stop_requested():
                    raise KeyboardInterrupt("Stop flag after inference; output withheld")
                output = Path(segment["output_path"])
                output.parent.mkdir(parents=True, exist_ok=True)
                temp = output.with_name(output.name + f".tmp.{os.getpid()}")
                sf.write(str(temp), array, sr, format="WAV", subtype="FLOAT")
                os.replace(temp, output)
                # Interrupted attempts have unknown elapsed time; label the total accordingly.
                interrupted = [e["attempt"] for e in started_attempts if not any(r["attempt"] == e["attempt"] for r in history)]
                total = sum(r.get("elapsed_seconds", 0) for r in history)
                generated = {"schema": SCHEMA, "status": "GENERATED_REQUIRES_REVIEW", "segment_id": segment["segment_id"],
                             "output_path": str(output), "created_at": utcnow(), "effective_key": key, "settings": settings,
                             "provenance": provenance, "selected_attempt": attempt, "selected_seed": seed,
                             "wav_sha256": file_hash(output), "audio": stats, "attempts": history,
                             "interrupted_attempt_numbers": interrupted, "generation_elapsed_seconds_total": total,
                             "generation_elapsed_total_is_lower_bound": bool(interrupted),
                             "rtf_generation_total": total / stats["duration_seconds"], "publication_approved": False}
                atomic_json(str(output) + ".json", generated)
                journal(job["journal_path"], {"event": "wav_committed", **event_base, "wav_sha256": generated["wav_sha256"], "output_path": str(output)})
                report["segments"].append({k: v for k, v in generated.items() if k not in ("settings", "provenance")})
                atomic_json(job["report_path"], report)
                break
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                record = {"event": "attempt_finished", **event_base, "status": "ERROR", "elapsed_seconds": time.perf_counter() - start,
                          "error_type": type(exc).__name__, "error": str(exc)}
                if not attempt_recorded:
                    history.append(record)
                    journal(job["journal_path"], record)
                    events.append(record)
                else:
                    journal(job["journal_path"], {"event": "output_commit_failed", **event_base, "error": str(exc)})
                # Memory/config failures do not improve by blindly retrying the same allocation.
                if isinstance(exc, torch.cuda.OutOfMemoryError) or "out of memory" in str(exc).lower():
                    raise RuntimeError("GPU memory exhausted; reduce segment size or choose a larger GPU. No dtype/model fallback applied") from exc
        if generated is None:
            result = {"segment_id": segment["segment_id"], "status": "FAILED", "effective_key": key, "attempts": history,
                      "attempts_started": max(used, max([e["attempt"] for e in history], default=0)),
                      "error": "Bounded attempts exhausted. Review failed text/settings explicitly; no text was skipped."}
            report["segments"].append(result)
            atomic_json(job["report_path"], report)
            raise RuntimeError(f"Unresolved segment {segment['segment_id']}; stopping before subsequent text")
    report.update(status="GENERATED_REQUIRES_REVIEW", finished_at=utcnow(), completed_segments=len(report["segments"]))
    atomic_json(job["report_path"], report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", help="Absolute JSON job path")
    args = parser.parse_args(argv)
    path = require_absolute(args.job, "job")
    job = json.loads(path.read_text(encoding="utf-8"))
    try:
        report = run(job)
        print(canonical({"status": report["status"], "report_path": job["report_path"], "completed_segments": report["completed_segments"]}))
        return 0
    except KeyboardInterrupt as exc:
        print(canonical({"status": "STOPPED", "error": str(exc), "report_path": job.get("report_path")}), file=sys.stderr)
        return 130
    except Exception as exc:
        print(canonical({"status": "FAILED", "error_type": type(exc).__name__, "error": str(exc), "report_path": job.get("report_path")}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
