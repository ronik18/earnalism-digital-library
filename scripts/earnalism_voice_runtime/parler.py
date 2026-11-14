"""Fixed inference-only successor to Earnalism's retained trained Parler worker.

Reuses its strict FP32/eager local factory, verified last-block reload and native
BundleSampler semantics. No optimizer, corpus, training operation or download.
Heavy imports occur only in run(), after actual authority and exclusive intent.
"""
import array
import hashlib
import importlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import struct
import sys
import time


def _sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _tensor_digest(parameters):
    h = hashlib.sha256()
    for name, tensor in sorted(parameters.items()):
        h.update((name + ":" + str(tuple(tensor.shape)) + ":" + str(tensor.dtype) + "\n").encode())
        flat = tensor.detach().reshape(-1)
        for start in range(0, flat.numel(), 262144):
            h.update(flat[start:start + 262144].cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def _shapes():
    prefix = "decoder.model.decoder.layers.23."
    result = {}
    for attention in ["self_attn", "encoder_attn"]:
        for projection in ["k_proj", "out_proj", "q_proj", "v_proj"]:
            result[prefix + attention + "." + projection + ".weight"] = (1024, 1024)
    for norm in ["encoder_attn_layer_norm", "final_layer_norm", "self_attn_layer_norm"]:
        for suffix in ["bias", "weight"]:
            result[prefix + norm + "." + suffix] = (1024,)
    result[prefix + "fc1.weight"] = (4096, 1024)
    result[prefix + "fc2.weight"] = (1024, 4096)
    return result


def _load_bundle(profile, root, checkpoint, device, check):
    """Strict original foundation + changed tensors; never an untrained fallback."""
    assets = profile["assets"]
    local = lambda value: Path(value) if Path(value).is_absolute() else root / value
    model_dir = local(assets["model_dir"]).absolute()
    description_dir = local(assets["description_tokenizer_dir"]).absolute()
    source_root = local(assets["source_root"]).absolute()
    inventory = {local(item["path"]).absolute(): item for item in assets["files"]}
    required_model = {"config.json", "generation_config.json", "model.safetensors",
                      "special_tokens_map.json", "tokenizer.json", "tokenizer.model", "tokenizer_config.json"}
    required_description = {"special_tokens_map.json", "spiece.model", "tokenizer.json", "tokenizer_config.json"}
    if not {model_dir / name for name in required_model}.issubset(inventory):
        raise ValueError("COMPLETE_PINNED_MODEL_INVENTORY_REQUIRED")
    if not {description_dir / name for name in required_description}.issubset(inventory):
        raise ValueError("COMPLETE_PINNED_DESCRIPTION_TOKENIZER_REQUIRED")
    sources = set((source_root / "parler_tts").rglob("*.py"))
    inventoried = {path for path in inventory if path.is_relative_to(source_root / "parler_tts")}
    if not sources or sources != inventoried:
        raise ValueError("EXACT_PARLER_SOURCE_SET_REQUIRED")
    if any(name == "parler_tts" or name.startswith("parler_tts.") for name in sys.modules):
        raise ValueError("FRESH_PARLER_PROCESS_REQUIRED")
    # This is a fresh isolated child. Retain the pinned target for lazy dependency
    # imports during generate(), as in the original worker's install_path().
    sys.path.insert(0, str(source_root))
    if ".".join(map(str, sys.version_info[:2])) != profile["runtime"]["python"]:
        raise ValueError("PINNED_PYTHON_REQUIRED")
    for name, expected in profile["runtime"]["packages"].items():
        if importlib.metadata.version(name) != expected:
            raise ValueError("PINNED_RUNTIME_VERSION_REQUIRED:" + name)
    check()
    import torch
    if device == "cuda:0" and not torch.cuda.is_available():
        raise ValueError("REQUESTED_CUDA_UNAVAILABLE_NO_CPU_FALLBACK")
    package = importlib.import_module("parler_tts")
    from transformers import AutoTokenizer
    if Path(package.__file__).resolve() != (source_root / "parler_tts/__init__.py").resolve():
        raise ValueError("PINNED_PARLER_NAMESPACE_REQUIRED")
    model, info = package.ParlerTTSForConditionalGeneration.from_pretrained(
        str(model_dir), local_files_only=True, token=False, use_safetensors=True, trust_remote_code=False,
        output_loading_info=True, low_cpu_mem_usage=False, torch_dtype=torch.float32,
        attn_implementation={"decoder": "eager", "text_encoder": "eager"})
    if any(info.get(key) != [] for key in ["missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs"]):
        raise ValueError("EXACT_PRETRAINED_LOAD_REQUIRED")
    prompt = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True, token=False, trust_remote_code=False)
    description = AutoTokenizer.from_pretrained(str(description_dir), local_files_only=True, token=False, trust_remote_code=False)
    check()
    saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
    binding = profile["checkpoint"]; shapes = _shapes()
    if (saved.get("format") != binding["format"] or saved.get("base_sha256") != profile["base"]["sha256"]
            or saved.get("bindings_sha256") != binding["bindings_sha256"]
            or type(saved.get("step")) is not int or saved["step"] != binding["training_updates"]
            or saved.get("supervised_scope") != "MALE_BENGALI_ONLY"
            or set(saved.get("trainable", {})) != set(shapes)
            or any(tuple(saved["trainable"][name].shape) != shape for name, shape in shapes.items())
            or _tensor_digest(saved["trainable"]) != binding["tensor_sha256"]):
        raise ValueError("EXACT_TRAINED_CHECKPOINT_SCHEMA_REQUIRED_NO_BASE_FALLBACK")
    parameters = dict(model.named_parameters())
    if {name for name in parameters if name.startswith("decoder.model.decoder.layers.23.")} != set(shapes):
        raise ValueError("EXACT_TRAINED_DECODER_LAYER_REQUIRED")
    if _tensor_digest({name: parameters[name] for name in shapes}) == binding["tensor_sha256"]:
        raise ValueError("ADAPTATION_MUST_DIFFER_FROM_ORIGINAL_BASE")
    with torch.no_grad():
        for name, shape in shapes.items():
            if (tuple(parameters[name].shape) != shape or saved["trainable"][name].dtype != torch.float32
                    or not bool(torch.isfinite(saved["trainable"][name]).all().item())):
                raise ValueError("FINITE_MATCHING_TRAINED_TENSORS_REQUIRED")
            parameters[name].copy_(saved["trainable"][name])
    if _tensor_digest({name: parameters[name] for name in shapes}) != binding["tensor_sha256"]:
        raise ValueError("TRAINED_TENSOR_RELOAD_MISMATCH")
    model.to(device=device, dtype=torch.float32).eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
        if parameter.is_meta or parameter.device.type != device.split(":")[0]:
            raise ValueError("EXPLICIT_REAL_DEVICE_REQUIRED")
    if model.config.sampling_rate != 44100:
        raise ValueError("NATIVE_44100_CODEC_REQUIRED")
    return {"model": model, "prompt_tokenizer": prompt, "description_tokenizer": description,
            "loading_report": {**info, "trained_checkpoint_sha256": binding["sha256"],
                "trained_tensor_sha256": binding["tensor_sha256"], "training_updates": binding["training_updates"],
                "supervised_training_scope": "MALE_BENGALI_ONLY", "dtype": "float32", "device": device}}, torch


class BundleSampler:
    """Retained native sampler: distinct caption/text, EOS, seed and real cap flag."""
    def __init__(self, bundle, torch, device):
        from transformers import StoppingCriteria, StoppingCriteriaList
        self.bundle, self.torch, self.device = bundle, torch, device
        self.StoppingCriteria, self.StoppingCriteriaList = StoppingCriteria, StoppingCriteriaList
        torch.set_num_threads(2)

    def generate(self, clip, generation):
        torch = self.torch
        torch.manual_seed(clip["seed"])
        if self.device.startswith("cuda"):
            torch.cuda.manual_seed_all(clip["seed"])
        prompt = self.bundle["prompt_tokenizer"](clip["spoken_text"], return_tensors="pt").to(self.device)
        description = self.bundle["description_tokenizer"](clip["caption_unspoken"], return_tensors="pt").to(self.device)
        class Observer(self.StoppingCriteria):
            calls = 0
            def __call__(self, input_ids, scores, **kwargs):
                self.calls += 1
                return torch.zeros(input_ids.shape[0], dtype=torch.bool, device=input_ids.device)
        observer = Observer()
        with torch.inference_mode():
            native = self.bundle["model"].generate(input_ids=description.input_ids,
                attention_mask=description.attention_mask, prompt_input_ids=prompt.input_ids,
                prompt_attention_mask=prompt.attention_mask,
                stopping_criteria=self.StoppingCriteriaList([observer]), **generation, num_return_sequences=1)
        if native.ndim != 2 or native.shape[0] != 1:
            raise ValueError("ONE_COMPLETE_NATIVE_WAVEFORM_REQUIRED")
        return native[0].detach().float().cpu().tolist(), observer.calls >= generation["max_new_tokens"]


def _write_wav(path, samples):
    values = array.array("f", samples)
    if sys.byteorder != "little": values.byteswap()
    data = values.tobytes()
    header = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt "
    header += struct.pack("<IHHIIHH", 16, 3, 1, 44100, 176400, 4, 32)
    with path.open("xb") as handle:
        handle.write(header + b"data" + struct.pack("<I", len(data)) + data)
        handle.flush(); os.fsync(handle.fileno())


def run(plan, profile, authority, output, *, checkpoint_loader, append_event, write_json):
    job = plan["job"]; root = Path(plan["profile_path"]).parent
    def check():
        if time.time() >= authority["absolute_deadline_epoch"]:
            raise TimeoutError("ORIGINAL_ALLOCATION_DEADLINE_EXHAUSTED")
    check()
    write_json(output / "WORKER-INTENT.json", {"job_sha256": plan["job_sha256"], "model_loading_started": True})
    destination = output / "materialized-trained-checkpoint.pt" if profile["checkpoint"].get("parts") else None
    checkpoint = checkpoint_loader(root, profile["checkpoint"], destination=destination)
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    bundle, torch = _load_bundle(profile, root, checkpoint, job["device"], check)
    sampler = BundleSampler(bundle, torch, job["device"])
    receipts = []; total_bytes = 0; total_seconds = 0
    for unit, fingerprint in zip(job["units"], plan["unit_fingerprints"]):
        check()
        append_event(authority["journal_path"], {"event": "unit_intent", "job_sha256": plan["job_sha256"],
                                                "fingerprint": fingerprint, "unit": unit["id"]})
        samples, cap = sampler.generate(unit, job["generation"])
        check()
        if not samples or not all(math.isfinite(value) for value in samples):
            raise ValueError("FINITE_NONEMPTY_NATIVE_AUDIO_REQUIRED_NO_RETRY")
        if total_bytes + 44 + len(samples) * 4 > job["limits"]["max_output_bytes"]:
            write_json(output / (unit["id"] + ".over-limit.json"), {
                "state": "NATIVE_AUDIO_EXCEEDS_AUTHORIZED_STORAGE_NOT_RETAINED",
                "frames": len(samples), "fingerprint": fingerprint, "automatic_retry": False})
            raise ValueError("NATIVE_OUTPUT_BYTE_LIMIT_NO_CROP_OR_RETRY")
        path = output / (unit["id"] + ".wav")
        _write_wav(path, samples)
        duration = len(samples) / 44100; total_bytes += path.stat().st_size; total_seconds += duration
        receipt = {"unit": unit["id"], "path": path.name, "bytes": path.stat().st_size,
            "sha256": _sha(path), "frames": len(samples), "sample_rate": 44100,
            "duration_seconds": duration, "source_start": unit["start"], "source_end": unit["end"],
            "spoken_text_sha256": hashlib.sha256(unit["spoken_text"].encode()).hexdigest(),
            "caption_sha256": hashlib.sha256(unit["caption_unspoken"].encode()).hexdigest(),
            "seed": unit["seed"], "generation": job["generation"], "token_cap_reached": cap,
            "gain": 1.0, "trimmed": False, "regenerated": False, "fingerprint": fingerprint}
        write_json(output / (unit["id"] + ".json"), receipt); receipts.append(receipt)
        append_event(authority["journal_path"], {"event": "unit_completed", "job_sha256": plan["job_sha256"],
            "fingerprint": fingerprint, "audio_sha256": receipt["sha256"], "token_cap_reached": cap})
        if cap or total_bytes > job["limits"]["max_output_bytes"] or total_seconds > job["limits"]["max_audio_seconds"]:
            raise ValueError("NATIVE_OUTPUT_LIMIT_REACHED_PRESERVED_INCOMPLETE_NO_RETRY")
    result = {"schema": "earnalism.voice_render_result.v1", "status": "PRIVATE_GENERATED_REQUIRES_QA",
        "identity": profile["identity"], "model": profile["base"]["model_id"],
        "source_sha256": job["source"]["sha256"],
        "job_sha256": plan["job_sha256"], "profile_sha256": plan["binding"]["profile_sha256"],
        "checkpoint_sha256": profile["checkpoint"]["sha256"], "loading_report": bundle["loading_report"],
        "original_deadline": authority["absolute_deadline_epoch"], "outputs": receipts,
        "native_audio_seconds": total_seconds, "audio_bytes": total_bytes,
        "purpose": job["purpose"], "source_coverage": plan["source_coverage"],
        "fidelity_naturalness_accent_and_mix": "UNPERFORMED", "publication_authorized": False,
        "training_updates_in_this_run": 0, "network_calls": 0}
    check(); write_json(output / "RESULT.json", result)
    return result
