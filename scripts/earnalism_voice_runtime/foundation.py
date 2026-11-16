"""Explicit private foundation diagnostic; never the branded trained voice.

No model imports occur at module import. The admitted isolated worker supplies
live authority/preservation callbacks. This module never restores an adapted
checkpoint, trains weights, downloads assets or joins a narration master.
"""
import hashlib
import importlib
import importlib.metadata
import math
import json
import os
import platform
from pathlib import Path
import sys

from scripts.earnalism_voice_runtime import parler


IDENTITY = "UNADAPTED_FOUNDATION_DIAGNOSTIC_NOT_THE_EARNALISM_VOICE"
_ABSENT = object()
TRACE_MAX_BYTES = 8 * 1024**2


def _local(root, value):
    root = Path(root).resolve()
    raw = Path(value)
    raw = raw if raw.is_absolute() else root / raw
    path = raw.resolve()
    if raw.is_symlink() or not path.is_relative_to(root):
        raise ValueError("CONTAINED_EXACT_DIAGNOSTIC_ASSET_REQUIRED")
    return path


def _expected(plan):
    proposal = plan["proposal"]
    arm = proposal["comparison"]["proposed_foundation"]
    if (arm["identity"] != IDENTITY
            or (arm["new_model_loads"], arm["new_generation_calls"],
                arm["adapted_checkpoint_restores"], arm["optimizer_updates"]) != (1, 2, 0, 0)
            or len(arm["units"]) != 2 or len(plan["unit_fingerprints"]) != 2
            or arm["native_output_bounds"] != {"max_audio_seconds": 180, "max_output_bytes": 32 * 1024**2}
            or plan["profile"]["base"] != arm["base"]):
        raise ValueError("EXPLICIT_FROZEN_TWO_SCENE_FOUNDATION_DIAGNOSTIC_REQUIRED")
    return proposal, arm


def _verify_foundation(bundle, expected):
    model = bundle["model"]
    bundle["position_helper"].verify_position_table(
        model, bundle["position_preparation"], tensor_digest=parler._tensor_digest)
    parameters = dict(model.named_parameters())
    if (parler._tensor_digest({name: parameters[name] for name in parler._shapes()})
            != bundle["original_last_block_tensor_sha256"]
            or parler._remaining_frozen_digest(model, set(parler._shapes()) |
                {bundle["position_helper"].POSITION_NAME})
            != expected["expected_remaining_frozen_state_excluding_16_trainable_and_position"]
            or any(parameter.requires_grad for parameter in model.parameters())):
        raise ValueError("FOUNDATION_OR_FROZEN_PREPARATION_CHANGED")


def _load_foundation(plan, root, check):
    proposal, arm = _expected(plan)
    profile = plan["profile"]
    required = proposal["future_comparability_requirements"]
    runtime, assets = required["runtime"], required["foundation_and_tokenizers"]
    if (profile["assets"] != assets or profile["runtime"]["packages"] != runtime["packages"]
            or profile["runtime"]["python"] != runtime["python"]
            or runtime["dtype"] != "float32" or sys.platform != "linux"
            or os.uname().machine != "x86_64" or runtime["platform"]["device"] != "cuda:0"
            or ".".join(map(str, sys.version_info[:2])) != runtime["python"]):
        raise ValueError("EXACT_LINUX_FP32_DIAGNOSTIC_RUNTIME_REQUIRED")
    model_dir = _local(root, assets["model_dir"])
    description_dir = _local(root, assets["description_tokenizer_dir"])
    source_root = _local(root, assets["source_root"])
    inventory = {}
    for item in assets["files"]:
        path = _local(root, item["path"])
        if (not path.is_file() or path.stat().st_size != item["bytes"]
                or parler._sha(path) != item["sha256"] or path in inventory):
            raise ValueError("EXACT_LOCAL_FOUNDATION_INVENTORY_REQUIRED")
        inventory[path] = item
        check()
    if (inventory.get(model_dir / "model.safetensors", {}).get("sha256") != arm["base"]["sha256"]
            or set((source_root / "parler_tts").rglob("*.py")) !=
                {path for path in inventory if path.is_relative_to(source_root / "parler_tts")}):
        raise ValueError("EXACT_FOUNDATION_AND_PARLER_SOURCE_SET_REQUIRED")
    actual_versions = {}
    for package, version in runtime["packages"].items():
        actual_versions[package] = importlib.metadata.version(package)
        if actual_versions[package] != version:
            raise ValueError("PINNED_DIAGNOSTIC_RUNTIME_VERSION_REQUIRED:" + package)
    if any(name == "parler_tts" or name.startswith("parler_tts.") for name in sys.modules):
        raise ValueError("FRESH_DIAGNOSTIC_PARLER_PROCESS_REQUIRED")
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    sys.path.insert(0, str(source_root))
    check()
    import torch
    torch.set_num_threads(2)
    if not torch.cuda.is_available():
        raise ValueError("REQUESTED_DIAGNOSTIC_CUDA_UNAVAILABLE_NO_FALLBACK")
    runtime_observation = {"python": sys.version, "python_version_info": list(sys.version_info[:3]),
        "implementation": platform.python_implementation(), "system": sys.platform,
        "machine": os.uname().machine, "actual_package_versions": actual_versions,
        "torch_version": torch.__version__, "torch_cuda_version": torch.version.cuda,
        "cuda_device_name": torch.cuda.get_device_name(0),
        "cuda_device_capability": list(torch.cuda.get_device_capability(0))}
    package = importlib.import_module("parler_tts")
    from transformers import AutoTokenizer
    if Path(package.__file__).resolve() != (source_root / "parler_tts/__init__.py").resolve():
        raise ValueError("PINNED_DIAGNOSTIC_PARLER_NAMESPACE_REQUIRED")
    check()
    model, info = package.ParlerTTSForConditionalGeneration.from_pretrained(
        str(model_dir), local_files_only=True, token=False, use_safetensors=True,
        trust_remote_code=False, output_loading_info=True, low_cpu_mem_usage=False,
        torch_dtype=torch.float32, attn_implementation={"decoder": "eager", "text_encoder": "eager"})
    if any(info.get(key) != [] for key in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")):
        raise ValueError("STRICT_FOUNDATION_LOAD_REQUIRED")
    prompt = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True,
                                         token=False, trust_remote_code=False)
    description = AutoTokenizer.from_pretrained(str(description_dir), local_files_only=True,
                                              token=False, trust_remote_code=False)
    parameters, shapes = dict(model.named_parameters()), parler._shapes()
    if {name for name in parameters if name.startswith("decoder.model.decoder.layers.23.")} != set(shapes):
        raise ValueError("EXACT_ORIGINAL_LAST_DECODER_BLOCK_REQUIRED")
    for name, shape in shapes.items():
        parameter = parameters[name]
        if (tuple(parameter.shape) != shape or parameter.dtype != torch.float32
                or not bool(torch.isfinite(parameter).all().item())):
            raise ValueError("FINITE_FP32_ORIGINAL_LAST_BLOCK_REQUIRED")
    original = parler._tensor_digest({name: parameters[name] for name in shapes})
    if original == profile["checkpoint"]["tensor_sha256"]:
        raise ValueError("FOUNDATION_MUST_DIFFER_FROM_REJECTED_ADAPTATION")
    model.to(device="cuda:0", dtype=torch.float32).eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
        if parameter.is_meta or parameter.device.type != "cuda":
            raise ValueError("EXPLICIT_REAL_DIAGNOSTIC_CUDA_REQUIRED")
    position = required["positional_preparation"]
    if (model.config.sampling_rate != 44100
            or parler._frozen_digest(model) != position["expected_full_frozen_state_before_table_expansion"]):
        raise ValueError("EXACT_NATIVE_CODEC_AND_ORIGINAL_FROZEN_STATE_REQUIRED")
    helper = parler._position_helper()
    report = helper.prepare_position_table(model, torch, required_positions=16384,
        trainable_names=set(shapes), tensor_digest=parler._tensor_digest,
        frozen_digest=parler._remaining_frozen_digest)
    expected_position = {
        "method": position["method"], "required_positions": position["required_positions"],
        "original_prefix_tensor_sha256": position["expected_original_prefix_tensor_sha256"],
        "prepared_table_tensor_sha256": position["expected_prepared_table_tensor_sha256"],
        "remaining_frozen_state": position["expected_remaining_frozen_state_excluding_16_trainable_and_position"],
    }
    if any(report.get(key) != value for key, value in expected_position.items()):
        raise ValueError("EXACT_DIAGNOSTIC_POSITION_PREPARATION_REQUIRED")
    bundle = {"model": model, "prompt_tokenizer": prompt, "description_tokenizer": description,
        "position_helper": helper, "position_preparation": report,
        "original_last_block_tensor_sha256": original,
        "loading_report": {**info, "foundation_sha256": arm["base"]["sha256"],
            "original_last_block_tensor_sha256": original, "adapted_checkpoint_restores": 0,
            "optimizer_updates": 0, "dtype": "float32", "device": "cuda:0",
            "position_preparation": report, "runtime_observation": runtime_observation}}
    _verify_foundation(bundle, position)
    check()
    return bundle, torch


def _restore_attribute(instance, name, previous):
    if previous is _ABSENT:
        delattr(instance, name)
    else:
        setattr(instance, name, previous)


def _snapshot(value):
    if hasattr(value, "detach"):
        return value.detach().clone()
    if type(value) is bool:
        return value
    if isinstance(value, (tuple, list)) and all(type(item) is bool for item in value):
        return tuple(value)
    raise ValueError("UNSUPPORTED_STOPPING_RESULT_FOR_OBSERVATION")


class CriterionObservation:
    """Observe exact existing criterion calls; never evaluate or replace them."""
    def __init__(self, criteria):
        self.criteria = tuple(criteria)
        self.targets = {id(item) for item in self.criteria}
        self.records = {}
        self.errors = []
        self.patches = []

    def __enter__(self):
        import inspect
        # Resolve every original before patching related parent/subclass types.
        originals = {}
        for criterion in self.criteria:
            cls = type(criterion)
            if cls not in originals:
                original = inspect.getattr_static(cls, "__call__")
                if not inspect.isfunction(original):
                    raise ValueError("ORDINARY_PYTHON_STOPPING_CRITERION_REQUIRED")
                originals[cls] = (vars(cls).get("__call__", _ABSENT), original)
        def make_wrapper(original, cls):
            def wrapper(instance, *args, **kwargs):
                result = original(instance, *args, **kwargs)
                if id(instance) in self.targets and type(instance) is cls:
                    record = self.records.setdefault(id(instance), {"calls": 0})
                    record["calls"] += 1
                    try:
                        record["last_result"] = _snapshot(result)
                        record["last_input_shape"] = list(args[0].shape)
                    except Exception as error:
                        self.errors.append(type(error).__name__)
                return result
            return wrapper
        try:
            for cls, (previous, original) in originals.items():
                wrapper = make_wrapper(original, cls)
                setattr(cls, "__call__", wrapper)
                self.patches.append((cls, previous, wrapper))
        except BaseException as error:
            try:
                self._restore()
            except Exception as restore_error:
                error.add_note("Stopping observation cleanup also failed: " + type(restore_error).__name__)
            raise
        return self

    def _restore(self):
        errors = []
        for cls, previous, wrapper in reversed(self.patches):
            try:
                if vars(cls).get("__call__", _ABSENT) is not wrapper:
                    raise ValueError("STOPPING_CLASS_CHANGED_DURING_OBSERVATION")
                _restore_attribute(cls, "__call__", previous)
            except Exception as error:
                errors.append(error)
        self.patches.clear()
        if errors:
            raise RuntimeError("STOPPING_OBSERVATION_RESTORATION_FAILED") from errors[0]

    def __exit__(self, kind, error, traceback):
        try:
            self._restore()
        except Exception as restore_error:
            if error is None:
                raise
            error.add_note("Stopping observation cleanup also failed: " + type(restore_error).__name__)
        return False

    def summary(self):
        entries = []
        for index, criterion in enumerate(self.criteria):
            record = self.records.get(id(criterion), {})
            result = record.get("last_result")
            try:
                if hasattr(result, "cpu"):
                    result = result.cpu().tolist()
                elif isinstance(result, tuple):
                    result = list(result)
                if type(result) is not bool and not (
                        isinstance(result, list) and all(type(item) is bool for item in result)):
                    raise ValueError("UNOBSERVED_OR_NONBOOLEAN_STOPPING_RESULT")
            except Exception as error:
                result = None
                self.errors.append(type(error).__name__)
            entries.append({"index": index,
                "class": type(criterion).__module__ + "." + type(criterion).__qualname__,
                "call_count": record.get("calls", 0),
                "last_input_shape": record.get("last_input_shape"),
                "last_result": result,
                "any_last_result_true": (result if type(result) is bool else any(result)
                                         if isinstance(result, list) else None)})
        return entries


class DiagnosticSampler:
    """Same frozen sampler with scoped exact-forward diagnostic observation.

    Criterion object/list identities, call order, return objects and RNG calls
    stay unchanged. Class patches exist only during this isolated _sample call.
    Trace snapshot errors hold comparability after returned native bytes persist.
    """
    def __init__(self, bundle, torch):
        from transformers import StoppingCriteria, StoppingCriteriaList
        self.bundle, self.torch = bundle, torch
        self.StoppingCriteria, self.StoppingCriteriaList = StoppingCriteria, StoppingCriteriaList
        self.trace = None
        torch.set_num_threads(2)

    def generate(self, clip, generation):
        self.trace = None
        torch, bundle = self.torch, self.bundle
        torch.manual_seed(clip["seed"])
        torch.cuda.manual_seed_all(clip["seed"])
        prompt = bundle["prompt_tokenizer"](clip["spoken_text"], return_tensors="pt").to("cuda:0")
        description = bundle["description_tokenizer"](clip["caption_unspoken"], return_tensors="pt").to("cuda:0")
        bundle["position_helper"].verify_position_table(
            bundle["model"], bundle["position_preparation"], tensor_digest=parler._tensor_digest)
        prompt_positions, description_positions = int(prompt.input_ids.shape[-1]), int(description.input_ids.shape[-1])
        if (description_positions > 512 or prompt_positions + description_positions +
                generation["max_new_tokens"] + 9 + 32 > bundle["position_preparation"]["capacity"]):
            raise ValueError("COMPLETE_UNTRUNCATED_DIAGNOSTIC_SCENE_EXCEEDS_FIXED_CONTEXT")
        errors = []
        class Observer(self.StoppingCriteria):
            calls = 0
            last = None
            def __call__(self, input_ids, scores, **kwargs):
                self.calls += 1
                try:
                    # cat creates a new decoder IDs tensor each step; do not clone
                    # the growing sequence on every step.
                    self.last = input_ids.detach()
                except Exception as error:
                    errors.append(type(error).__name__)
                return torch.zeros(input_ids.shape[0], dtype=torch.bool, device=input_ids.device)
        observer = Observer()
        model, codec = bundle["model"], bundle["model"].audio_encoder
        sample_previous = vars(model).get("_sample", _ABSENT)
        decode_previous = vars(codec).get("decode", _ABSENT)
        sample_original, decode_original = model._sample, codec.decode
        raw = {}; codecs = []; observations = []; sample_calls = 0
        def sample(*args, **kwargs):
            nonlocal sample_calls
            sample_calls += 1
            criteria = kwargs.get("stopping_criteria")
            if criteria is None:
                raise ValueError("ACTUAL_STOPPING_CRITERIA_REQUIRED_FOR_DIAGNOSTIC")
            observation = CriterionObservation(criteria)
            observations.append(observation)
            with observation:
                result = sample_original(*args, **kwargs)
            raw["returned"] = True
            try:
                ids = result.sequences if hasattr(result, "sequences") else result
                if len(ids.shape) != 2 or ids.shape[0] != 9 or ids.shape[-1] > generation["max_new_tokens"] + 9 + 32:
                    raise ValueError("RAW_DIAGNOSTIC_TOKEN_TRACE_EXCEEDS_FIXED_SHAPE")
                raw["ids"] = ids.detach().clone()
            except Exception as error:
                errors.append(type(error).__name__)
            return result
        def decode(*args, **kwargs):
            try:
                codes = kwargs.get("audio_codes", args[0] if args else None)
                if codes is None:
                    raise ValueError("ACTUAL_CODEC_INPUT_NOT_OBSERVED")
                if len(codes.shape) not in (3, 4) or math.prod(codes.shape) > 9 * (generation["max_new_tokens"] + 9 + 32):
                    raise ValueError("CODEC_DIAGNOSTIC_TRACE_EXCEEDS_FIXED_SHAPE")
                codecs.append(codes.detach().clone())
            except Exception as error:
                errors.append(type(error).__name__)
            return decode_original(*args, **kwargs)
        model._sample, codec.decode = sample, decode
        native = None
        try:
            with torch.inference_mode():
                native = model.generate(input_ids=description.input_ids,
                    attention_mask=description.attention_mask, prompt_input_ids=prompt.input_ids,
                    prompt_attention_mask=prompt.attention_mask,
                    stopping_criteria=self.StoppingCriteriaList([observer]),
                    **generation, num_return_sequences=1)
        finally:
            for instance, name, previous in ((model, "_sample", sample_previous), (codec, "decode", decode_previous)):
                try:
                    _restore_attribute(instance, name, previous)
                except Exception as error:
                    errors.append("Restoration:" + type(error).__name__)
            self.trace = {"schema": "earnalism.foundation_generation_trace.v1", "unit": clip["id"],
                "observer_calls": observer.calls, "sample_calls": sample_calls,
                "original_sample_returned": raw.get("returned", False),
                "delayed_token_ids": None, "codec_inputs": [], "criteria": [],
                "observed_call_count_reached_max_new_tokens": observer.calls >= generation["max_new_tokens"],
                "stop_reason": "UNKNOWN_EFFECTIVE_CRITERION_NOT_OBSERVED", "trace_errors": errors,
                "delayed_token_ids_scope": "Raw delayed _sample return; observer fallback on error",
                "codec_input_scope": "Exact post-delay/filter inputs forwarded to native audio_encoder.decode",
                "stop_reason_limit": "Final true criteria are observed simultaneous contributors, not a uniquely inferred cause",
                "input_token_lengths": {"prompt": prompt_positions, "description": description_positions},
                "reference_waveform_conditioned": False, "sampler_or_rng_override": False}
            try:
                delayed = raw.get("ids", observer.last)
                delayed_values = delayed.cpu().tolist() if delayed is not None else None
                eos = model.generation_config.eos_token_id
                eos_ids = set(eos if isinstance(eos, (tuple, list)) else [eos])
                self.trace.update(delayed_token_ids=delayed_values, eos_token_ids=sorted(eos_ids),
                    pad_token_id=model.generation_config.pad_token_id,
                    eos_and_pad_are_aliased=model.generation_config.pad_token_id in eos_ids,
                    first_eos_position_by_delayed_row=([next((i for i, token in enumerate(row)
                        if token in eos_ids), None) for row in delayed_values] if delayed_values is not None else None),
                    eos_position_limit="Raw special-token offsets; EOS/pad alias cannot distinguish speech ending or audio time",
                    codec_inputs=[{"shape": list(codes.shape), "audio_codes": codes.cpu().tolist()} for codes in codecs])
                criterion_entries = observations[-1].summary() if observations else []
                self.trace["criteria"] = criterion_entries
                self.trace["trace_errors"].extend(error for observation in observations for error in observation.errors)
                final_shape = list(delayed.shape) if delayed is not None else None
                self.trace["final_delayed_shape"] = final_shape
                self.trace["criterion_sample_index"] = sample_calls - 1 if observations else None
                contributors = [entry["index"] for entry in criterion_entries
                    if entry["any_last_result_true"] and entry["last_input_shape"] == final_shape]
                self.trace["final_true_criterion_indices"] = contributors
                if contributors:
                    self.trace["stop_reason"] = "OBSERVED_EFFECTIVE_STOPPING_CRITERIA_TRUE"
            except Exception as error:
                errors.append(type(error).__name__)
        if native.ndim != 2 or native.shape[0] != 1:
            raise ValueError("ONE_COMPLETE_DIAGNOSTIC_NATIVE_WAVEFORM_REQUIRED")
        return native[0].detach().float().cpu().tolist(), observer.calls >= generation["max_new_tokens"]


def _trace_comparable(trace):
    if (not isinstance(trace, dict) or trace.get("trace_errors")
            or trace.get("original_sample_returned") is not True or trace.get("sample_calls") != 1
            or not trace.get("delayed_token_ids") or not trace.get("codec_inputs")
            or not trace.get("criteria")
            or trace.get("stop_reason") != "OBSERVED_EFFECTIVE_STOPPING_CRITERIA_TRUE"):
        raise ValueError("DIAGNOSTIC_TRACE_INCOMPLETE_NATIVE_PRESERVED_NO_RETRY")

def _persist_trace(output, unit, trace, write_json):
    path = Path(output) / (unit["id"] + ".trace.json")
    complete = True
    try:
        encoded = (json.dumps(trace, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        if len(encoded) > TRACE_MAX_BYTES:
            complete = False
            payload = {"schema": "earnalism.foundation_trace_failure.v1",
                "state": "TRACE_STORAGE_LIMIT_FULL_NATIVE_PRESERVED",
                "trace_storage_limit_bytes": TRACE_MAX_BYTES, "encoded_trace_bytes": len(encoded),
                "encoded_trace_sha256": hashlib.sha256(encoded).hexdigest(),
                "full_trace_not_written": True, "automatic_retry": False}
        else:
            payload = trace
    except (ValueError, TypeError) as error:
        complete = False
        payload = {"schema": "earnalism.foundation_trace_failure.v1",
            "state": "TRACE_ENCODING_FAILED_FULL_NATIVE_PRESERVED",
            "error_type": type(error).__name__, "automatic_retry": False}
    write_json(path, payload)
    if path.stat().st_size > TRACE_MAX_BYTES:
        raise ValueError("BOUNDED_TRACE_WRITER_CONTRACT_CHANGED")
    return {"path": path.name, "bytes": path.stat().st_size, "sha256": parler._sha(path), "complete": complete}


def run(plan, assets_root, output, *, check, write_json, append_event):
    proposal, arm = _expected(plan)
    output = Path(output)
    check()
    write_json(output / "MODEL-INTENT.json", {"identity": IDENTITY,
        "proposal_sha256": plan.get("proposal_sha256"), "model_loading_started": True,
        "adapted_checkpoint_restores": 0, "optimizer_updates": 0})
    bundle, torch = _load_foundation(plan, Path(assets_root), check)
    sampler = DiagnosticSampler(bundle, torch)
    receipts = []; total_bytes = 0; total_seconds = 0
    for unit, fingerprint in zip(arm["units"], plan["unit_fingerprints"]):
        check()
        append_event({"event": "foundation_unit_intent", "fingerprint": fingerprint, "unit": unit["id"]})
        try:
            samples, cap = sampler.generate(unit, arm["generation"])
        except BaseException:
            if sampler.trace is not None:
                try:
                    _persist_trace(output, unit, sampler.trace, write_json)
                except Exception:
                    pass  # Preserve the primary generation failure in the owned worker log.
            raise
        if not samples or not all(math.isfinite(value) for value in samples):
            _persist_trace(output, unit, sampler.trace, write_json)
            raise ValueError("FINITE_NONEMPTY_DIAGNOSTIC_AUDIO_REQUIRED_NO_RETRY")
        if total_bytes + 44 + len(samples) * 4 > arm["native_output_bounds"]["max_output_bytes"]:
            _persist_trace(output, unit, sampler.trace, write_json)
            write_json(output / (unit["id"] + ".over-limit.json"), {
                "state": "NATIVE_AUDIO_EXCEEDS_FROZEN_STORAGE_NOT_RETAINED",
                "frames": len(samples), "fingerprint": fingerprint, "automatic_retry": False})
            raise ValueError("DIAGNOSTIC_NATIVE_BYTE_LIMIT_NO_CROP_OR_RETRY")
        path = output / (unit["id"] + ".wav")
        parler._write_wav(path, samples)
        duration = len(samples) / 44100
        total_bytes += path.stat().st_size; total_seconds += duration
        trace_ref = _persist_trace(output, unit, sampler.trace, write_json)
        receipt = {"unit": unit["id"], "path": path.name, "bytes": path.stat().st_size,
            "sha256": parler._sha(path), "frames": len(samples), "sample_rate": 44100,
            "duration_seconds": duration, "source_start": unit["start"], "source_end": unit["end"],
            "spoken_text_sha256": hashlib.sha256(unit["spoken_text"].encode()).hexdigest(),
            "caption_sha256": hashlib.sha256(unit["caption_unspoken"].encode()).hexdigest(),
            "seed": unit["seed"], "generation": arm["generation"], "token_cap_reached": cap,
            "gain": 1.0, "trimmed": False, "regenerated": False, "fingerprint": fingerprint,
            "identity": IDENTITY, "quality_accepted": False, "production_ready": False, "trace": trace_ref}
        write_json(output / (unit["id"] + ".json"), receipt)
        receipts.append(receipt)
        check()
        if not trace_ref["complete"]:
            raise ValueError("DIAGNOSTIC_TRACE_STORAGE_OR_ENCODING_FAILED_NATIVE_PRESERVED")
        _trace_comparable(sampler.trace)
        _verify_foundation(bundle, proposal["future_comparability_requirements"]["positional_preparation"])
        append_event({"event": "foundation_unit_completed", "fingerprint": fingerprint,
                      "audio_sha256": receipt["sha256"], "token_cap_reached": cap})
        if cap or total_seconds > arm["native_output_bounds"]["max_audio_seconds"]:
            raise ValueError("DIAGNOSTIC_NATIVE_OUTPUT_LIMIT_PRESERVED_NO_RETRY")
    result = {"schema": "earnalism.foundation_diagnostic_result.v1",
        "status": "PRIVATE_FOUNDATION_DIAGNOSTIC_REQUIRES_ASSESSMENT", "identity": IDENTITY,
        "proposal_sha256": plan.get("proposal_sha256"), "experiment_sha256": plan["experiment_sha256"], "base": arm["base"],
        "outputs": receipts, "loading_report": bundle["loading_report"],
        "native_audio_seconds": total_seconds, "audio_bytes": total_bytes,
        "generation_calls": 2, "adapted_checkpoint_restores": 0, "training_updates": 0,
        "downloads_enabled": False, "network_policy": "OFFLINE_LOCAL_FILES_ONLY",
        "reference_waveform_conditioned": False,
        "quality_accepted": False, "production_ready": False, "qualification_ready": False, "publication_authorized": False,
        "assessment": "UNPERFORMED; exact content and actual performance review remain required",
        "causal_limit": proposal["future_comparability_requirements"]["causal_limit"]}
    check()
    write_json(output / "RESULT.json", result)
    return result
