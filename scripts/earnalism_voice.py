#!/usr/bin/env python3
"""Local, source-bound TheEarnalismVoice inference; import/inspection never loads ML.

Public API:
  inspect_profile(path, language, purpose='production') -> binding/blocker dict.
  validate_job(path) -> source-preserving typed plan, without model execution.
  render(job_path, output_dir, authority_path) -> private result manifest.
  ensure_runtime(profile_path, runtime_dir, authority_path) -> package receipt.
  verify_retained(job_path, output_dir) -> verified prior result, read-only.

JSON contracts (paths are local, relative to the containing JSON unless absolute):
* profile schema earnalism.voice_profile.v1: identity='TheEarnalismVoice',
  backend='indic_parler_last_block_v1', base={model_id,revision,sha256},
  checkpoint={bytes,sha256,format,bindings_sha256,training_updates,tensor_sha256,
  path OR parts:[{path,bytes,sha256}]}, assets={model_dir,
  description_tokenizer_dir,source_root,files:[{path,bytes,sha256}]},
  runtime={python,packages, optional bootstrap:{runtime_dir,python_executable:
  descriptor,wheel_manifest:descriptor,bootstrap_wheel_manifest:descriptor}},
  rights={status:'CLEARED',evidence:descriptor},
  qualification={bn|en:{status:'ACCEPTED',evidence:descriptor}}. Acceptance JSON
  must bind identity/language/base/checkpoint hashes and status ACCEPTED. Missing
  acceptance holds production; an expressly authorized qualification audition
  can test an unqualified profile. A trained checkpoint is always mandatory.
* job schema earnalism.voice_job.v1: source/profile descriptors, language bn|en,
  purpose production|qualification, device cpu|cuda:0, units=[{id,start,end,
  spoken_text,caption_unspoken,seed,context}], generation={do_sample,temperature,
  top_k,top_p,max_new_tokens}, limits={max_audio_seconds,max_output_bytes}.
  Production units cover the exact source once in order, with Unicode code-point
  offsets. Qualification units may select ordered, nonoverlapping source spans.
  Directions/context are unspoken; captions are the only prosody input. No
  numerical emotion/pitch API, stock-voice fallback or arbitrary command exists.
* authority schema earnalism.voice_execution.v1: approved=true, actual_scope_ref,
  job_sha256,profile_sha256,code_sha256,runtime_code_sha256,purpose,
  allocation_started_at,absolute_deadline_epoch,max_units,journal_path and
  allowed_unit_fingerprints (from validate_job). publication_allowed=false,
  training_allowed=false,network_allowed=false. This is a binding to actual
  existing authority, not an approval generator or a new allowance.

One fixed child is supervised to the ORIGINAL deadline. Each render and unit is
  journalled/fsynced before consequential work; unknown outcomes are not replayed.
The runtime reuses strict retained Parler FP32/eager loading, last-block tensor
reload and native caption/text sampling, without the training class/optimizer.
Checkpoint parts can be verified by streaming, without a second whole copy.
Only an admitted render reconstructs parts in its private output directory.
Actual fidelity/voice/mix/release acceptance remains downstream. No CLI action
publishes. No private training data, speaker captions or storage accounts ship.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import unicodedata

IDENTITY = "TheEarnalismVoice"
BACKEND = "indic_parler_last_block_v1"
BASE_ID = "ai4bharat/indic-parler-tts"
BASE_REVISION = "7b527af5ee8ed1f9a28d80b19703ed9bb8ba10ca"
BASE_SHA256 = "c68daecb60f80c8f1faf0a6d2e6ddd6de8e224fb19750f3e9a33bca43c552c90"
TRAINED_SHA256 = "1e76214837d4d92482a3ee2d2655cf2ad9821e4dacc83a008ae5fe435e06c4f1"
TRAINED_BYTES = 201428880
TRAINED_BINDINGS_SHA256 = "8aca3d7f7323c6dabd7916e7141ecd2f521908857867e1553cf747548c0ec6e2"
TRAINED_TENSOR_SHA256 = "b0f7a164bb2be21355edf6ee3471f340998259592949fce818b0590425e71341"
RUNTIME = Path(__file__).with_name("earnalism_voice_runtime") / "parler.py"
SETUP = RUNTIME.with_name("setup.py")
SHA = re.compile(r"[0-9a-f]{64}\Z")
MIN_PACKAGES = {"torch": "2.6.0", "transformers": "4.46.1",
                "parler-tts": "0.2.2", "descript-audio-codec": "1.0.0"}


class VoiceBlocked(ValueError):
    """Missing, drifted, unqualified or already-consumed operation binding."""


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def object_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8 * 1024**2:
        raise VoiceBlocked("Regular bounded local JSON required")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise VoiceBlocked("JSON object required")
    return value


def _path(root, value):
    if not isinstance(value, str) or not value or "://" in value:
        raise VoiceBlocked("Local file path required")
    path = Path(value)
    path = path if path.is_absolute() else Path(root) / path
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise VoiceBlocked("Materialized regular paths required; no symlinks")
    return path.absolute()


def _descriptor(root, item, *, verify=True, require_exists=True):
    if (not isinstance(item, dict) or not SHA.fullmatch(str(item.get("sha256", "")))
            or type(item.get("bytes")) is not int or item["bytes"] <= 0):
        raise VoiceBlocked("Exact file byte/hash descriptor required")
    path = _path(root, item.get("path"))
    if not require_exists:
        return path
    if not path.is_file() or path.stat().st_size != item["bytes"]:
        raise VoiceBlocked("Missing or wrong-sized local asset: " + path.name)
    if verify and digest(path) != item["sha256"]:
        raise VoiceBlocked("Changed local asset: " + path.name)
    return path


def _checkpoint(root, item, *, verify=True, destination=None, require_exists=True):
    """Validate whole or ordered parts; optionally materialize only during render."""
    if (not isinstance(item, dict) or not SHA.fullmatch(str(item.get("sha256", "")))
            or type(item.get("bytes")) is not int or item["bytes"] <= 0
            or item.get("format") != "EARNALISM_PARLER_LAST_BLOCK_V1"
            or item.get("training_updates") != 130 or item.get("sha256") != TRAINED_SHA256
            or item.get("bytes") != TRAINED_BYTES or item.get("bindings_sha256") != TRAINED_BINDINGS_SHA256
            or item.get("tensor_sha256") != TRAINED_TENSOR_SHA256):
        raise VoiceBlocked("A genuine bound trained checkpoint is required; no base fallback")
    if bool(item.get("path")) == bool(item.get("parts")):
        raise VoiceBlocked("Exactly one whole checkpoint or ordered part list required")
    if item.get("path"):
        return _descriptor(root, item, verify=verify, require_exists=require_exists)
    parts = item["parts"]
    if not isinstance(parts, list) or not 1 <= len(parts) <= 64:
        raise VoiceBlocked("Bounded checkpoint parts required")
    paths = [_descriptor(root, part, verify=False, require_exists=require_exists) for part in parts]
    if len(set(paths)) != len(paths) or sum(part["bytes"] for part in parts) != item["bytes"]:
        raise VoiceBlocked("Checkpoint part coverage changed")
    if not require_exists:
        return None
    whole = hashlib.sha256()
    output = None
    try:
        if destination is not None:
            output = Path(destination).open("xb")
        for path, part in zip(paths, parts):
            single = hashlib.sha256()
            if verify or output is not None:
                with path.open("rb") as handle:
                    for block in iter(lambda: handle.read(1024 * 1024), b""):
                        single.update(block); whole.update(block)
                        if output is not None:
                            output.write(block)
                if single.hexdigest() != part["sha256"]:
                    raise VoiceBlocked("Checkpoint part checksum changed")
        if (verify or output is not None) and whole.hexdigest() != item["sha256"]:
            raise VoiceBlocked("Whole checkpoint checksum changed")
        if output is not None:
            output.flush(); os.fsync(output.fileno())
    finally:
        if output is not None:
            output.close()
    return Path(destination) if destination is not None else None


def _profile(path, language, purpose, *, verify_assets=True):
    path = Path(path).absolute(); profile = _json(path); root = path.parent
    if (language not in {"bn", "en"} or purpose not in {"production", "qualification"}
            or profile.get("schema") != "earnalism.voice_profile.v1"
            or profile.get("identity") != IDENTITY or profile.get("backend") != BACKEND
            or profile.get("base") != {"model_id": BASE_ID, "revision": BASE_REVISION,
                                        "sha256": BASE_SHA256}):
        raise VoiceBlocked("Supported exact trained voice identity/base required")
    rights = profile.get("rights", {})
    if not isinstance(rights, dict) or rights.get("status") != "CLEARED":
        raise VoiceBlocked("Actual applicable model/voice rights evidence required")
    _descriptor(root, rights.get("evidence"))
    assets = profile.get("assets", {})
    if not isinstance(assets, dict):
        raise VoiceBlocked("Typed local asset inventory required")
    for key in ["model_dir", "description_tokenizer_dir", "source_root"]:
        folder = _path(root, assets.get(key))
        if verify_assets is not None and not folder.is_dir():
            raise VoiceBlocked("Missing materialized asset directory: " + key)
    files = assets.get("files")
    if not isinstance(files, list) or not files or len(files) > 256:
        raise VoiceBlocked("Exact local model/tokenizer/source inventory required")
    paths = [_descriptor(root, item, verify=bool(verify_assets), require_exists=verify_assets is not None)
             for item in files]
    if len(set(paths)) != len(paths):
        raise VoiceBlocked("Repeated asset inventory member")
    model = _path(root, assets["model_dir"]) / "model.safetensors"
    if not any(p == model and item["sha256"] == BASE_SHA256 for p, item in zip(paths, files)):
        raise VoiceBlocked("Exact foundation weight must be in inventory")
    _checkpoint(root, profile.get("checkpoint"), verify=bool(verify_assets), require_exists=verify_assets is not None)
    runtime = profile.get("runtime", {})
    if (not isinstance(runtime, dict) or not re.fullmatch(r"3\.(?:11|12|13)", str(runtime.get("python", "")))
            or not isinstance(runtime.get("packages"), dict)
            or any(runtime["packages"].get(k) != v for k, v in MIN_PACKAGES.items())):
        raise VoiceBlocked("Pinned supported runtime package binding required")
    qualification = profile.get("qualification", {})
    if not isinstance(qualification, dict) or not isinstance(qualification.get(language, {}), dict):
        raise VoiceBlocked("Typed per-language qualification record required")
    entry = qualification.get(language, {})
    accepted = False
    if entry.get("status") == "ACCEPTED":
        receipt = _json(_descriptor(root, entry.get("evidence")))
        accepted = all(receipt.get(k) == v for k, v in {
            "status": "ACCEPTED", "identity": IDENTITY, "language": language,
            "base_sha256": BASE_SHA256,
            "checkpoint_sha256": profile["checkpoint"]["sha256"],
        }.items())
        if not accepted:
            raise VoiceBlocked("Voice acceptance receipt does not bind this checkpoint/language")
    blockers = [] if accepted or purpose == "qualification" else ["VOICE_LANGUAGE_NOT_PRODUCTION_ACCEPTED"]
    return profile, {"status": "QUALIFIED" if accepted else "UNQUALIFIED",
        "identity": IDENTITY, "backend": BACKEND, "model": BASE_ID,
        "profile_sha256": digest(path), "base": profile["base"],
        "checkpoint_sha256": profile["checkpoint"]["sha256"], "language": language,
        "purpose": purpose, "production_accepted": accepted, "blockers": blockers,
        "asset_hashes_verified": verify_assets is True, "model_loaded": False,
        "training_performed": False, "publication_authorized": False}


def inspect_profile(profile_path, language, purpose="production"):
    """Inspect qualification without requiring weights for already-retained audio.

    Available checkpoint parts are checksum-streamed without reconstruction.
    Missing runtime assets are reported separately from actual voice acceptance.
    Render always verifies the complete local inventory before model loading.
    """
    try:
        profile, report = _profile(profile_path, language, purpose, verify_assets=None)
        try:
            _checkpoint(Path(profile_path).absolute().parent, profile["checkpoint"])
            report["checkpoint_local_verification"] = "HASH_VERIFIED_NO_DESERIALIZATION"
            report["execution_blockers"] = []
        except (VoiceBlocked, OSError) as error:
            report["checkpoint_local_verification"] = "UNAVAILABLE_OR_INVALID"
            report["execution_blockers"] = [str(error)]
        report["runtime_asset_preflight"] = "REQUIRED_AT_RENDER_NOT_VOICE_ACCEPTANCE"
        return report
    except (VoiceBlocked, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        return {"status": "INVALID", "identity": IDENTITY, "language": language, "purpose": purpose,
                "production_accepted": False, "blockers": [str(error)],
                "model_loaded": False, "publication_authorized": False}


def validate_job(job_path):
    """Validate exact speech/context and fingerprints using only the standard library."""
    job_path = Path(job_path).absolute(); job = _json(job_path); root = job_path.parent
    if (job.get("schema") != "earnalism.voice_job.v1"
            or job.get("purpose") not in {"qualification", "production"}
            or job.get("language") not in {"bn", "en"}
            or job.get("device") not in {"cpu", "cuda:0"}):
        raise VoiceBlocked("Typed supported local voice job required")
    source = _descriptor(root, job.get("source")).read_bytes().decode("utf-8")
    profile_path = _descriptor(root, job.get("profile"))
    profile, binding = _profile(profile_path, job["language"], job["purpose"], verify_assets=None)
    if binding["blockers"]:
        raise VoiceBlocked(binding["blockers"][0])
    generation = job.get("generation", {})
    if (not isinstance(generation, dict) or set(generation) != {"do_sample", "temperature", "top_k", "top_p", "max_new_tokens"}
            or generation.get("do_sample") is not True
            or type(generation.get("top_k")) is not int or not 1 <= generation["top_k"] <= 1000
            or type(generation.get("max_new_tokens")) is not int or not 1 <= generation["max_new_tokens"] <= 8192
            or not _number(generation.get("temperature"), 0.01, 2)
            or not _number(generation.get("top_p"), 0.01, 1)):
        raise VoiceBlocked("Only supported explicit Parler sampling settings are accepted")
    limits = job.get("limits", {})
    if (not isinstance(limits, dict) or set(limits) != {"max_audio_seconds", "max_output_bytes"}
            or not _number(limits.get("max_audio_seconds"), 0.01, 86400)
            or type(limits.get("max_output_bytes")) is not int or not 1 <= limits["max_output_bytes"] <= 2**33):
        raise VoiceBlocked("Finite audio/output limits required")
    units = job.get("units")
    if not isinstance(units, list) or not 1 <= len(units) <= 1024:
        raise VoiceBlocked("One bounded ordered unit list required")
    if job["purpose"] == "qualification" and len(units) > 4:
        raise VoiceBlocked("Qualification is a bounded audition, not a full-book fallback")
    end = 0; ids = set(); fingerprints = []
    for unit in units:
        if (not isinstance(unit, dict) or set(unit) != {"id", "start", "end", "spoken_text", "caption_unspoken", "seed", "context"}
                or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", str(unit.get("id", "")))
                or unit["id"] in ids or type(unit["start"]) is not int or type(unit["end"]) is not int
                or unit["start"] < end or not unit["start"] < unit["end"] <= len(source)
                or job["purpose"] == "production" and unit["start"] != end
                or source[unit["start"]:unit["end"]] != unit["spoken_text"]
                or not isinstance(unit["context"], str) or not unit["context"].strip()
                or not isinstance(unit["caption_unspoken"], str) or not 1 <= len(unit["caption_unspoken"]) <= 4000
                or type(unit["seed"]) is not int or not 0 <= unit["seed"] < 2**32):
            raise VoiceBlocked("Exact ordered source units and separate unspoken context required")
        start = unit["start"]
        if start and _inside_word(source, start):
            raise VoiceBlocked("Unit boundary splits a source word")
        if unit["end"] < len(source) and _inside_word(source, unit["end"]):
            raise VoiceBlocked("Unit boundary splits a source word")
        ids.add(unit["id"]); end = unit["end"]
        fingerprints.append(object_sha({"source_sha256": job["source"]["sha256"],
            "start": unit["start"], "end": unit["end"], "spoken_text": unit["spoken_text"],
            "caption_unspoken": unit["caption_unspoken"], "seed": unit["seed"],
            "generation": generation, "checkpoint_sha256": profile["checkpoint"]["sha256"]}))
    if job["purpose"] == "production" and end != len(source):
        raise VoiceBlocked("Source must be covered completely once in order")
    return {"job": job, "job_path": str(job_path), "job_sha256": digest(job_path),
            "profile_path": str(profile_path), "binding": binding,
            "unit_fingerprints": fingerprints, "source_coverage":
                "FULL_EXACT_TEXT_NOT_AUDIO_FIDELITY" if job["purpose"] == "production"
                else "SELECTED_EXACT_SOURCE_SPANS_NOT_FULL_TITLE"}


def _number(value, low, high):
    return type(value) in {int, float} and math.isfinite(value) and low <= value <= high


def _inside_word(text, offset):
    def constituent(character):
        return unicodedata.category(character)[0] in {"L", "M", "N"} or character in "'’\u200c\u200d"
    left, right = text[offset-1], text[offset]
    return (unicodedata.category(right)[0] == "M" or right in "\u200c\u200d"
            or left in "\u200c\u200d" or constituent(left) and constituent(right))


def _authority(path, plan):
    authority = _json(path); now = time.time(); job = plan["job"]
    if "original_deadline_epoch" in authority:
        if ("absolute_deadline_epoch" in authority
                and authority["absolute_deadline_epoch"] != authority["original_deadline_epoch"]):
            raise VoiceBlocked("Conflicting original allocation deadlines")
        authority["absolute_deadline_epoch"] = authority["original_deadline_epoch"]
    if (authority.get("schema") != "earnalism.voice_execution.v1" or authority.get("approved") is not True
            or not isinstance(authority.get("actual_scope_ref"), str) or not authority["actual_scope_ref"].strip()
            or any(authority.get(k) != v for k, v in {
                "job_sha256": plan["job_sha256"], "profile_sha256": plan["binding"]["profile_sha256"],
                "code_sha256": digest(__file__), "runtime_code_sha256": digest(RUNTIME),
                "purpose": job["purpose"], "training_allowed": False, "network_allowed": False,
                "publication_allowed": False, "allowed_unit_fingerprints": plan["unit_fingerprints"],
            }.items()) or type(authority.get("max_units")) is not int
            or not len(job["units"]) <= authority["max_units"] <= 1024
            or not _number(authority.get("allocation_started_at"), 1, now)
            or not _number(authority.get("absolute_deadline_epoch"), now + 0.01, now + 86400)
            or authority["absolute_deadline_epoch"] <= authority["allocation_started_at"]):
        raise VoiceBlocked("Actual exact-job original-scope/deadline authority required")
    authority["journal_path"] = str(_path(Path(path).absolute().parent, authority.get("journal_path")))
    return authority


def _append(path, event):
    path = Path(path)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise VoiceBlocked("Preserve unexpected journal symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"at_epoch": time.time(), **event}, sort_keys=True, allow_nan=False) + "\n")
        handle.flush(); os.fsync(handle.fileno())


def _write(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


def _stop_owned_group(process):
    if process is None: return
    try:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try: process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL); process.wait(timeout=2)
        # An exited immediate child can still leave a pip/helper descendant.
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _setup_authority(path, profile_path, runtime_dir):
    """Package capability from the SAME actual owner scope; no new approval."""
    authority = _json(path); now = time.time()
    deadline = authority.get("original_deadline_epoch", authority.get("absolute_deadline_epoch"))
    if (authority.get("schema") != "earnalism.voice_execution.v1" or authority.get("approved") is not True
            or authority.get("package_setup_allowed") is not True or authority.get("package_network_allowed") is not True
            or authority.get("profile_sha256") != digest(profile_path)
            or authority.get("code_sha256") != digest(__file__) or authority.get("setup_code_sha256") != digest(SETUP)
            or not authority.get("actual_scope_ref") or authority.get("training_allowed") is not False
            or authority.get("publication_allowed") is not False
            or authority.get("runtime_dir") != str(Path(runtime_dir).absolute())
            or not _number(authority.get("allocation_started_at"), 1, now)
            or not _number(deadline, now + 0.01, now + 86400)
            or "original_deadline_epoch" in authority and "absolute_deadline_epoch" in authority
                and authority["original_deadline_epoch"] != authority["absolute_deadline_epoch"]):
        raise VoiceBlocked("Actual same-scope exact package capability/original deadline required")
    authority["absolute_deadline_epoch"] = deadline
    authority["journal_path"] = str(_path(Path(path).absolute().parent, authority.get("journal_path")))
    return authority


def ensure_runtime(profile_path, runtime_dir, authority_path):
    """Restore fixed locked packages in an isolated environment, never the host.

    This optional phase uses package_setup_allowed/package_network_allowed and
    setup_code_sha256/runtime_dir from the same actual execution receipt. It
    needs an explicitly hash-bound matching local Python interpreter. CP312
    wheels are never relabelled CP313; missing Python blocks before downloads.
    Package readiness does not qualify a GPU, model or narration.
    """
    profile_path = Path(profile_path).absolute()
    profile, _ = _profile(profile_path, "bn", "qualification", verify_assets=None)
    authority = _setup_authority(authority_path, profile_path, runtime_dir)
    bootstrap = profile.get("runtime", {}).get("bootstrap", {})
    _descriptor(profile_path.parent, bootstrap.get("python_executable"))
    _descriptor(profile_path.parent, bootstrap.get("wheel_manifest"))
    _descriptor(profile_path.parent, bootstrap.get("bootstrap_wheel_manifest"))
    expected_dir = _path(profile_path.parent, bootstrap.get("runtime_dir"))
    if expected_dir != Path(runtime_dir).absolute():
        raise VoiceBlocked("Profile and authority must bind the same runtime directory")
    evidence = expected_dir.parent / (expected_dir.name + ".setup")
    result_path = evidence / "RESULT.json"
    if result_path.exists():
        result = _json(result_path)
        python = expected_dir / "bin/python"
        if (result.get("profile_sha256") != digest(profile_path)
                or result.get("status") != "LOCAL_PACKAGES_READY_NOT_MODEL_QUALIFIED"
                or result.get("python") != str(python) or not python.is_file()
                or digest(python) != bootstrap["python_executable"]["sha256"]):
            raise VoiceBlocked("Preserve incompatible runtime receipt")
        probe = "import sys,json,importlib.metadata;print(json.dumps({'python':'.'.join(map(str,sys.version_info[:2])),'packages':{d.metadata['Name'].lower().replace('_','-').replace('.','-'):d.version for d in importlib.metadata.distributions()}}))"
        current = subprocess.run([str(python), "-I", "-c", probe],
            env={"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONNOUSERSITE": "1"},
            stdin=subprocess.DEVNULL, capture_output=True, text=True, check=True,
            timeout=max(0.01, authority["absolute_deadline_epoch"] - time.time()))
        current = json.loads(current.stdout)
        if (current.get("python") != profile["runtime"]["python"]
                or any(current.get("packages", {}).get(k) != v for k, v in profile["runtime"]["packages"].items())):
            raise VoiceBlocked("Cached runtime ABI/package metadata drifted; preserve, no replay")
        return result
    key = object_sha({"profile_sha256": digest(profile_path), "runtime_dir": str(expected_dir)})
    with _journal_lock(authority["journal_path"]):
        journal = Path(authority["journal_path"])
        if journal.exists():
            for line in journal.read_text().splitlines():
                try:
                    event = json.loads(line)
                    if not isinstance(event, dict): raise ValueError("Journal event must be an object")
                except ValueError as error:
                    raise VoiceBlocked("Unknown package journal tail; status-only") from error
                if event.get("event") == "package_setup_intent" and event.get("fingerprint") == key:
                    raise VoiceBlocked("Consumed package setup; status-only, no automatic retry")
        _append(journal, {"event": "package_setup_intent", "fingerprint": key})
        process = None
        try:
            expected_dir.parent.mkdir(parents=True, exist_ok=True)
            with (expected_dir.parent / (expected_dir.name + ".setup-process.log")).open("xb") as log:
                process = subprocess.Popen([sys.executable, "-I", "-B", str(SETUP), "--execute",
                    "--profile", str(profile_path), "--output", str(expected_dir),
                    "--authority", str(Path(authority_path).absolute())],
                    env={"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONNOUSERSITE": "1",
                         "PIP_CONFIG_FILE": "/dev/null", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                    start_new_session=True)
                code = process.wait(timeout=max(0.01, authority["absolute_deadline_epoch"] - time.time()))
            if code: raise VoiceBlocked("Package setup failed; preserved setup evidence, no replay")
            result = _json(result_path)
            if result.get("profile_sha256") != digest(profile_path) or result.get("status") != "LOCAL_PACKAGES_READY_NOT_MODEL_QUALIFIED":
                raise VoiceBlocked("Missing exact runtime preparation result")
            _append(journal, {"event": "package_setup_completed", "fingerprint": key,
                              "result_sha256": digest(result_path)})
            return result
        except BaseException as error:
            _append(journal, {"event": "package_setup_failed_or_unknown", "fingerprint": key,
                              "error_type": type(error).__name__})
            raise
        finally:
            _stop_owned_group(process)


def _verify_result(plan, output, result):
    expected = {"schema": "earnalism.voice_render_result.v1", "status": "PRIVATE_GENERATED_REQUIRES_QA",
                "job_sha256": plan["job_sha256"], "source_sha256": plan["job"]["source"]["sha256"],
                "profile_sha256": plan["binding"]["profile_sha256"],
                "checkpoint_sha256": plan["binding"]["checkpoint_sha256"]}
    if any(result.get(k) != v for k, v in expected.items()):
        raise VoiceBlocked("Missing exact completed inference manifest")
    outputs = result.get("outputs")
    if not isinstance(outputs, list) or len(outputs) != len(plan["job"]["units"]):
        raise VoiceBlocked("Partial or unknown inference outputs; no completion claim")
    for item, unit, fingerprint in zip(outputs, plan["job"]["units"], plan["unit_fingerprints"]):
        if (item.get("path") != unit["id"] + ".wav" or item.get("unit") != unit["id"]
                or item.get("fingerprint") != fingerprint or item.get("token_cap_reached") is not False):
            raise VoiceBlocked("Changed or incomplete inference output binding")
        _descriptor(output, item)


def verify_retained(job_path, output_dir):
    """Read-only recovery of completed units; no authority/setup/model/replay.

    Verifies source/profile/unit fingerprints and current WAV hashes. This is
    media integrity/provenance evidence, never new voice or release acceptance.
    """
    plan = validate_job(job_path)
    output = _path(Path.cwd(), str(output_dir))
    result = _json(output / "RESULT.json")
    _verify_result(plan, output, result)
    return result


@contextmanager
def _journal_lock(journal):
    import fcntl
    path = Path(str(journal) + ".lock")
    if path.is_symlink():
        raise VoiceBlocked("Unexpected journal lock symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise VoiceBlocked("Voice journal already owned by another writer") from error
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def render(job_path, output_dir, authority_path):
    """Run only fixed local inference in a deadline-supervised fresh child."""
    plan = validate_job(job_path); authority = _authority(authority_path, plan)
    profile = _json(plan["profile_path"])
    python = sys.executable
    bootstrap = profile["runtime"].get("bootstrap")
    if bootstrap:
        runtime_dir = _path(Path(plan["profile_path"]).parent, bootstrap.get("runtime_dir"))
        python = ensure_runtime(plan["profile_path"], runtime_dir, authority_path)["python"]
    journal = Path(authority["journal_path"]); output = _path(Path.cwd(), str(output_dir))
    with _journal_lock(journal):
        events = []
        if journal.exists():
            if journal.is_symlink(): raise VoiceBlocked("Unexpected journal symlink")
            for line in journal.read_text().splitlines():
                try:
                    event = json.loads(line)
                    if not isinstance(event, dict): raise ValueError("Journal event must be an object")
                    events.append(event)
                except (ValueError, TypeError) as error: raise VoiceBlocked("Unknown journal tail; status-only") from error
        if any(e.get("job_sha256") == plan["job_sha256"] and e.get("event") == "render_intent"
               or e.get("fingerprint") in plan["unit_fingerprints"] and e.get("event") == "unit_intent"
               for e in events):
            raise VoiceBlocked("Consumed or unknown voice attempt; status-only, no replay")
        output.mkdir(parents=True, exist_ok=False)
        _append(journal, {"event": "render_intent", "job_sha256": plan["job_sha256"],
                          "original_deadline": authority["absolute_deadline_epoch"]})
        _write(output / "INTENT.json", {"job_sha256": plan["job_sha256"],
            "authority_sha256": digest(authority_path), "original_deadline": authority["absolute_deadline_epoch"]})
        env = {"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1",
               "PYTHONNOUSERSITE": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
               "HF_HUB_DISABLE_TELEMETRY": "1", "DO_NOT_TRACK": "1", "WANDB_DISABLED": "true"}
        process = None
        try:
            with (output / "worker.log").open("xb") as log:
                process = subprocess.Popen([python, "-I", "-B", str(Path(__file__).absolute()),
                    "_worker", "--job", str(Path(job_path).absolute()), "--output", str(output),
                    "--authority", str(Path(authority_path).absolute())],
                    env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                    start_new_session=True)
                code = process.wait(timeout=max(0.01, authority["absolute_deadline_epoch"] - time.time()))
                if code:
                    raise VoiceBlocked("Inference failed or unknown; preserve raw output, no replay")
            result = _json(output / "RESULT.json")
            _verify_result(plan, output, result)
            _append(journal, {"event": "render_completed", "job_sha256": plan["job_sha256"],
                              "result_sha256": digest(output / "RESULT.json")})
            return result
        except BaseException as error:
            _append(journal, {"event": "render_failed_or_unknown", "job_sha256": plan["job_sha256"],
                              "error_type": type(error).__name__})
            if not (output / "FAILURE.json").exists():
                _write(output / "FAILURE.json", {"status": "FAILED_OR_UNKNOWN_NO_REPLAY",
                    "job_sha256": plan["job_sha256"], "error_type": type(error).__name__})
            raise
        finally:
            _stop_owned_group(process)


def _worker(job_path, output, authority_path):
    plan = validate_job(job_path); authority = _authority(authority_path, plan)
    _arm_child_containment(authority["absolute_deadline_epoch"])
    intent = _json(Path(output) / "INTENT.json")
    if intent.get("job_sha256") != plan["job_sha256"] or intent.get("authority_sha256") != digest(authority_path):
        raise VoiceBlocked("Parent's exact render intent required")
    profile, _ = _profile(plan["profile_path"], plan["job"]["language"], plan["job"]["purpose"])
    import importlib.util
    spec = importlib.util.spec_from_file_location("_earnalism_fixed_parler_inference", RUNTIME)
    runtime = importlib.util.module_from_spec(spec); spec.loader.exec_module(runtime)
    return runtime.run(plan, profile, authority, Path(output),
                       checkpoint_loader=_checkpoint, append_event=_append, write_json=_write)


def _arm_child_containment(deadline):
    """Stop an orphaned fixed child too, including during native model calls."""
    if sys.platform != "linux":
        raise VoiceBlocked("Real speech/package children require the supported Linux runtime")
    import ctypes
    parent = os.getppid()
    if parent == 1 or ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGKILL) != 0 or os.getppid() != parent:
        raise VoiceBlocked("Owned child parent-death containment unavailable")
    seconds = deadline - time.time()
    if seconds <= 0: raise VoiceBlocked("Original child deadline exhausted")
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.setitimer(signal.ITIMER_REAL, seconds)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["inspect", "validate", "verify", "render", "_worker"])
    parser.add_argument("--profile", type=Path); parser.add_argument("--language", choices=["bn", "en"])
    parser.add_argument("--purpose", choices=["production", "qualification"], default="production")
    parser.add_argument("--job", type=Path); parser.add_argument("--output", type=Path)
    parser.add_argument("--authority", type=Path); parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.action == "inspect":
            if not args.profile or not args.language: parser.error("--profile and --language required")
            result = inspect_profile(args.profile, args.language, args.purpose)
        else:
            if not args.job: parser.error("--job required")
            if args.action == "verify":
                if not args.output: parser.error("--output required")
                result = verify_retained(args.job, args.output)
            elif args.action == "validate" or args.action == "render" and not args.execute:
                result = validate_job(args.job)
            else:
                if not args.output or not args.authority: parser.error("--output and --authority required")
                result = (_worker if args.action == "_worker" else render)(args.job, args.output, args.authority)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except (VoiceBlocked, OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "BLOCKED", "error": str(error)})); return 1


if __name__ == "__main__":
    raise SystemExit(main())
