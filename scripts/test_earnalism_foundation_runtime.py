"""Pure-fake foundation runtime checks; no real model, CUDA or quality evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import random
import sys
import tempfile
import types
import unittest
from unittest import mock

from scripts.earnalism_voice_runtime import foundation as runtime


class Tensor:
    device = "cuda:0"
    def __init__(self, value): self.value = copy.deepcopy(value)
    @property
    def shape(self):
        result = []; value = self.value
        while isinstance(value, list):
            result.append(len(value)); value = value[0] if value else None
        return tuple(result)
    @property
    def ndim(self): return len(self.shape)
    def detach(self): return self
    def clone(self): return Tensor(self.value)
    def cpu(self): return self
    def float(self): return self
    def tolist(self): return copy.deepcopy(self.value)
    def __getitem__(self, item): return Tensor(self.value[item])


class Torch:
    bool = "bool"
    def __init__(self):
        self.rng = random.Random()
        self.seeds = []
        self.cuda = types.SimpleNamespace(manual_seed_all=self.cuda_seed)
    def manual_seed(self, seed): self.seeds.append(("cpu", seed)); self.rng.seed(seed)
    def cuda_seed(self, seed): self.seeds.append(("cuda", seed)); self.rng.seed(seed)
    def set_num_threads(self, n): self.threads = n
    def zeros(self, n, **kwargs): return Tensor([False] * n)
    def inference_mode(self): return mock.MagicMock(__enter__=lambda s: s, __exit__=lambda *a: False)


class Criteria:
    pass


class CriteriaList(list):
    def __call__(self, ids, scores):
        result = [False] * ids.shape[0]
        for criterion in self:
            value = criterion(ids, scores)
            assert value is criterion.last_return if hasattr(criterion, "last_return") else True
            result = [old or new for old, new in zip(result, value.tolist())]
        return Tensor(result)


class ParentCriterion(Criteria):
    def __init__(self): self.calls = 0
    def __call__(self, ids, scores):
        self.calls += 1
        self.last_return = Tensor([ids.shape[-1] >= 4] * ids.shape[0])
        return self.last_return


class InheritedCriterion(ParentCriterion):
    pass


class EosCriterion(Criteria):
    def __init__(self): self.calls = 0
    def __call__(self, ids, scores):
        self.calls += 1
        self.last_return = Tensor([row[-1] == 1024 for row in ids.tolist()])
        return self.last_return


class Batch:
    def __init__(self):
        self.input_ids = Tensor([[8, 2, 6]])
        self.attention_mask = Tensor([[1, 1, 1]])
    def to(self, device): return self


class Codec:
    def __init__(self): self.calls = []
    def decode(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        self.last_return = types.SimpleNamespace(audio_values=Tensor([[0.1, 0.2, -0.1]]))
        return self.last_return


class Model:
    def __init__(self, torch, *, fail=False):
        self.torch = torch; self.fail = fail
        self.audio_encoder = Codec()
        self.generation_config = types.SimpleNamespace(eos_token_id=1024, pad_token_id=1024)
        self.criteria = [ParentCriterion(), InheritedCriterion(), EosCriterion()]
        self.generate_kwargs = None
        self.forwarded_list_id = None
        self.forwarded_entry_ids = None
    def _sample(self, ids, *, stopping_criteria, **kwargs):
        self.forwarded_list_id = id(stopping_criteria)
        self.forwarded_entry_ids = [id(item) for item in stopping_criteria]
        for step in range(3):
            ids = Tensor([row + [1024 if step == 2 else self.torch.rng.randrange(1024)]
                          for row in ids.tolist()])
            mask = stopping_criteria(ids, None)
            if self.fail and step == 1:
                raise RuntimeError("original native failure")
            if all(mask.tolist()):
                break
        return ids
    def generate(self, **kwargs):
        self.generate_kwargs = kwargs
        criteria = CriteriaList(self.criteria + list(kwargs["stopping_criteria"]))
        entries = [id(item) for item in criteria]
        ids = self._sample(Tensor([[1025]] * 9), stopping_criteria=criteria)
        assert id(criteria) == self.forwarded_list_id
        assert entries == self.forwarded_entry_ids
        self.sampled = ids.tolist()
        codes = Tensor([[[1, 2, 3] for _ in range(9)]])
        self.decode_codes = codes
        result = self.audio_encoder.decode(audio_codes=codes)
        assert self.audio_encoder.calls[-1][1]["audio_codes"] is codes
        assert result is self.audio_encoder.last_return
        return result.audio_values


def bundle(torch, fail=False):
    model = Model(torch, fail=fail)
    return {"model": model, "prompt_tokenizer": lambda *a, **k: Batch(),
            "description_tokenizer": lambda *a, **k: Batch(),
            "position_helper": types.SimpleNamespace(verify_position_table=lambda *a, **k: True),
            "position_preparation": {"capacity": 16384}}


TRANSFORMERS = types.SimpleNamespace(StoppingCriteria=Criteria, StoppingCriteriaList=CriteriaList)
CLIP = {"id": "scene", "seed": 20261116, "spoken_text": "Exact scene.", "caption_unspoken": "Fixed."}
GEN = {"do_sample": True, "temperature": 1.0, "top_k": 50, "top_p": 1.0, "max_new_tokens": 8000}


class RuntimeTests(unittest.TestCase):
    def test_exact_forward_sampler_rng_and_cleanup(self):
        self.assertNotIn("torch", sys.modules)
        original_parent = ParentCriterion.__call__
        original_eos = EosCriterion.__call__
        with mock.patch.dict(sys.modules, {"transformers": TRANSFORMERS}):
            base_torch, diagnostic_torch = Torch(), Torch()
            base_bundle, diagnostic_bundle = bundle(base_torch), bundle(diagnostic_torch)
            expected = runtime.parler.BundleSampler(base_bundle, base_torch, "cuda:0").generate(CLIP, GEN)
            sampler = runtime.DiagnosticSampler(diagnostic_bundle, diagnostic_torch)
            actual = sampler.generate(CLIP, GEN)
        self.assertEqual(actual, expected)
        self.assertEqual(base_torch.rng.getstate(), diagnostic_torch.rng.getstate())
        self.assertEqual(base_torch.seeds, diagnostic_torch.seeds)
        self.assertEqual(base_bundle["model"].sampled, diagnostic_bundle["model"].sampled)
        for key in set(GEN) | {"num_return_sequences"}:
            self.assertEqual(base_bundle["model"].generate_kwargs[key],
                             diagnostic_bundle["model"].generate_kwargs[key])
        self.assertEqual([item.calls for item in diagnostic_bundle["model"].criteria], [3, 3, 3])
        self.assertEqual([item["call_count"] for item in sampler.trace["criteria"]], [3, 3, 3, 3])
        self.assertEqual(sampler.trace["final_true_criterion_indices"], [0, 1, 2])
        self.assertTrue(all(value is False for value in sampler.trace["criteria"][-1]["last_result"]))
        self.assertTrue(sampler.trace["eos_and_pad_are_aliased"])
        self.assertEqual(sampler.trace["first_eos_position_by_delayed_row"], [3] * 9)
        self.assertEqual(sampler.trace["codec_inputs"][0]["audio_codes"], [[[1, 2, 3]] * 9])
        self.assertIs(ParentCriterion.__call__, original_parent)
        self.assertIs(EosCriterion.__call__, original_eos)
        self.assertNotIn("__call__", vars(InheritedCriterion))
        self.assertNotIn("_sample", vars(diagnostic_bundle["model"]))
        self.assertNotIn("decode", vars(diagnostic_bundle["model"].audio_encoder))
        runtime._trace_comparable(sampler.trace)
        self.assertNotIn("torch", sys.modules)

    def test_original_error_and_method_restoration(self):
        original_parent = ParentCriterion.__call__
        with mock.patch.dict(sys.modules, {"transformers": TRANSFORMERS}):
            current = bundle(Torch(), fail=True)
            sampler = runtime.DiagnosticSampler(current, current["model"].torch)
            with self.assertRaisesRegex(RuntimeError, "original native failure"):
                sampler.generate(CLIP, GEN)
        self.assertIs(ParentCriterion.__call__, original_parent)
        self.assertNotIn("__call__", vars(InheritedCriterion))
        self.assertNotIn("_sample", vars(current["model"]))
        self.assertNotIn("decode", vars(current["model"].audio_encoder))
        self.assertFalse(sampler.trace["original_sample_returned"])

    def test_snapshot_failure_does_not_change_native_return(self):
        with mock.patch.dict(sys.modules, {"transformers": TRANSFORMERS}):
            current = bundle(Torch())
            sampler = runtime.DiagnosticSampler(current, current["model"].torch)
            with mock.patch.object(runtime, "_snapshot", side_effect=RuntimeError("snapshot unavailable")):
                actual = sampler.generate(CLIP, GEN)
        self.assertEqual(actual, ([0.1, 0.2, -0.1], False))
        self.assertTrue(sampler.trace["trace_errors"])
        with self.assertRaisesRegex(ValueError, "TRACE_INCOMPLETE"):
            runtime._trace_comparable(sampler.trace)

    def test_strict_foundation_loader_never_restores_checkpoint(self):
        import hashlib
        from contextlib import ExitStack
        calls = []
        dtype = object()
        class Parameter:
            def __init__(self, shape):
                self.shape = shape; self.dtype = dtype; self.requires_grad = True
                self.is_meta = False; self.device = types.SimpleNamespace(type="cuda")
            def requires_grad_(self, value): self.requires_grad = value
        parameters = {name: Parameter(shape) for name, shape in runtime.parler._shapes().items()}
        class NativeModel:
            config = types.SimpleNamespace(sampling_rate=44100)
            def named_parameters(self): return parameters.items()
            def parameters(self): return parameters.values()
            def to(self, **kwargs):
                calls.append(("to", kwargs)); return self
            def eval(self): return self
        native = NativeModel()
        class Factory:
            @staticmethod
            def from_pretrained(path, **kwargs):
                calls.append(("model", path, kwargs))
                return native, {key: [] for key in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")}
        class Tokenizer:
            @staticmethod
            def from_pretrained(path, **kwargs):
                calls.append(("tokenizer", path, kwargs)); return object()
        class Finite:
            def all(self): return self
            def item(self): return True
        fake_torch = types.SimpleNamespace(float32=dtype, set_num_threads=lambda n: None,
            __version__="fake-2.6.0", version=types.SimpleNamespace(cuda="fake"),
            cuda=types.SimpleNamespace(is_available=lambda: True, get_device_name=lambda i: "FAKE",
                get_device_capability=lambda i: (0, 0)), isfinite=lambda p: Finite(),
            load=mock.Mock(side_effect=AssertionError("No checkpoint deserialization permitted")))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            names = ("assets/model/model.safetensors", "assets/parler-source/parler_tts/__init__.py",
                     "assets/description-tokenizer/tokenizer.json")
            files = []
            for name in names:
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(name.encode())
                files.append({"path": name, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            assets = {"model_dir": "assets/model", "source_root": "assets/parler-source",
                      "description_tokenizer_dir": "assets/description-tokenizer", "files": files}
            position = {"method": "fixed", "required_positions": 16384,
                "expected_original_prefix_tensor_sha256": "prefix", "expected_prepared_table_tensor_sha256": "table",
                "expected_remaining_frozen_state_excluding_16_trainable_and_position": "remaining",
                "expected_full_frozen_state_before_table_expansion": "before"}
            report = {"method": "fixed", "required_positions": 16384, "original_prefix_tensor_sha256": "prefix",
                      "prepared_table_tensor_sha256": "table", "remaining_frozen_state": "remaining"}
            helper = types.SimpleNamespace(POSITION_NAME="position",
                prepare_position_table=lambda *a, **k: report, verify_position_table=lambda *a, **k: True)
            profile = {"assets": assets, "base": {"sha256": files[0]["sha256"]},
                "runtime": {"python": "3.12", "packages": {"fake-package": "1"}},
                "checkpoint": {"tensor_sha256": "adapted", "path": "absent-adapted-checkpoint.pt"}}
            arm = {"identity": runtime.IDENTITY, "base": profile["base"], "new_model_loads": 1,
                "new_generation_calls": 2, "adapted_checkpoint_restores": 0, "optimizer_updates": 0,
                "units": [{}, {}], "native_output_bounds": {"max_audio_seconds": 180, "max_output_bytes": 32 * 1024**2}}
            plan = {"profile": profile, "unit_fingerprints": ["a", "b"],
                "proposal": {"comparison": {"proposed_foundation": arm},
                    "future_comparability_requirements": {"runtime": {"python": "3.12", "packages": {"fake-package": "1"},
                        "dtype": "float32", "platform": {"device": "cuda:0"}},
                        "foundation_and_tokenizers": assets, "positional_preparation": position}}}
            package = types.SimpleNamespace(__file__=str(root / names[1]), ParlerTTSForConditionalGeneration=Factory)
            with ExitStack() as stack:
                stack.enter_context(mock.patch.dict(sys.modules, {"torch": fake_torch, "parler_tts": package,
                    "transformers": types.SimpleNamespace(AutoTokenizer=Tokenizer)}))
                # Fresh namespace gate is tested by having the importer return the
                # fake package, without preloading a real parler_tts namespace.
                del sys.modules["parler_tts"]
                original_import = runtime.importlib.import_module
                stack.enter_context(mock.patch.object(runtime.importlib, "import_module",
                    side_effect=lambda name: package if name == "parler_tts" else original_import(name)))
                stack.enter_context(mock.patch.object(runtime.sys, "platform", "linux"))
                stack.enter_context(mock.patch.object(runtime.sys, "version_info", (3, 12, 13)))
                stack.enter_context(mock.patch.object(runtime.os, "uname",
                    return_value=types.SimpleNamespace(machine="x86_64")))
                stack.enter_context(mock.patch.object(runtime.importlib.metadata, "version", return_value="1"))
                stack.enter_context(mock.patch.object(runtime.parler, "_tensor_digest", return_value="original"))
                stack.enter_context(mock.patch.object(runtime.parler, "_frozen_digest", return_value="before"))
                stack.enter_context(mock.patch.object(runtime.parler, "_remaining_frozen_digest", return_value="remaining"))
                stack.enter_context(mock.patch.object(runtime.parler, "_position_helper", return_value=helper))
                loaded, returned_torch = runtime._load_foundation(plan, root, lambda: None)
            fake_torch.load.assert_not_called()
            self.assertIs(returned_torch, fake_torch)
            self.assertEqual(loaded["loading_report"]["original_last_block_tensor_sha256"], "original")
            self.assertEqual(loaded["loading_report"]["adapted_checkpoint_restores"], 0)
            self.assertTrue(all(not parameter.requires_grad for parameter in parameters.values()))
            model_calls = [item for item in calls if item[0] == "model"]
            self.assertEqual(len(model_calls), 1)
            self.assertIs(model_calls[0][2]["torch_dtype"], dtype)
            self.assertTrue(model_calls[0][2]["local_files_only"])
            self.assertFalse(model_calls[0][2]["trust_remote_code"])
            self.assertEqual(model_calls[0][2]["attn_implementation"], {"decoder": "eager", "text_encoder": "eager"})
            self.assertEqual(len([item for item in calls if item[0] == "tokenizer"]), 2)
        self.assertNotIn("torch", sys.modules)

    def test_arbitrary_criterion_kwargs_forward_unchanged(self):
        class Forward(Criteria):
            def __call__(self, ids, scores, **kwargs):
                self.seen = kwargs
                self.result = Tensor([False])
                return self.result
        criterion = Forward()
        first, second = object(), object()
        with runtime.CriterionObservation([criterion]) as observation:
            value = criterion(Tensor([[1]]), None, _original=first, _cls=second)
            self.assertIs(value, criterion.result)
        self.assertIs(criterion.seen["_original"], first)
        self.assertIs(criterion.seen["_cls"], second)
        self.assertEqual(observation.summary()[0]["call_count"], 1)

    def test_related_super_calls_record_each_target_once(self):
        class SuperCriterion(ParentCriterion):
            def __call__(self, ids, scores):
                return super().__call__(ids, scores)
        parent, child = ParentCriterion(), SuperCriterion()
        ids = Tensor([[1, 2, 3, 4]])
        parent_original, child_original = ParentCriterion.__call__, SuperCriterion.__call__
        observation = runtime.CriterionObservation([parent, child])
        with observation:
            self.assertIs(parent(ids, None), parent.last_return)
            self.assertIs(child(ids, None), child.last_return)
        entries = observation.summary()
        self.assertEqual([entry["call_count"] for entry in entries], [1, 1])
        self.assertEqual([parent.calls, child.calls], [1, 1])
        self.assertIs(ParentCriterion.__call__, parent_original)
        self.assertIs(SuperCriterion.__call__, child_original)

    def test_nonordinary_static_and_class_descriptors_rejected(self):
        class Static(Criteria):
            @staticmethod
            def __call__(ids, scores): return Tensor([False])
        class InheritedStatic(Static): pass
        class Class(Criteria):
            @classmethod
            def __call__(cls, ids, scores): return Tensor([False])
        for cls in [Static, InheritedStatic, Class]:
            with self.subTest(cls=cls):
                with self.assertRaisesRegex(ValueError, "ORDINARY_PYTHON"):
                    with runtime.CriterionObservation([cls()]): pass

    def test_trace_storage_bound_keeps_bounded_failure_descriptor(self):
        import hashlib
        trace = {"large": "x" * 2048}
        def write(path, value):
            with Path(path).open("x") as f:
                json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
                f.write("\n")
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(runtime, "TRACE_MAX_BYTES", 1024):
            ref = runtime._persist_trace(folder, {"id": "bounded"}, trace, write)
            path = Path(folder) / ref["path"]
            data = json.loads(path.read_text())
            self.assertFalse(ref["complete"])
            self.assertLessEqual(path.stat().st_size, 1024)
            expected = (json.dumps(trace, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
            self.assertEqual(data["encoded_trace_sha256"], hashlib.sha256(expected).hexdigest())
            self.assertTrue(data["full_trace_not_written"])

    def test_native_bytes_persist_before_late_authority_failure(self):
        units = [{**CLIP, "id": "first", "start": 0, "end": len(CLIP["spoken_text"])},
                 {**CLIP, "id": "second", "start": 0, "end": len(CLIP["spoken_text"])}]
        arm = {"identity": runtime.IDENTITY, "new_model_loads": 1, "new_generation_calls": 2,
               "adapted_checkpoint_restores": 0, "optimizer_updates": 0, "units": units,
               "generation": GEN, "base": {"sha256": "base"},
               "native_output_bounds": {"max_audio_seconds": 180, "max_output_bytes": 32 * 1024**2}}
        plan = {"proposal": {"comparison": {"proposed_foundation": arm}},
                "profile": {"base": arm["base"]}, "unit_fingerprints": ["a", "b"]}
        calls = []
        def check():
            calls.append("check")
            if len(calls) == 3: raise TimeoutError("expired after native")
        class Sampler:
            def __init__(self, *args): self.trace = {"state": "retained trace"}
            def generate(self, *args): return [0.1, 0.2], False
        def write(path, value):
            with Path(path).open("x") as f: json.dump(value, f)
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            with mock.patch.object(runtime, "_load_foundation", return_value=({}, object())), \
                    mock.patch.object(runtime, "DiagnosticSampler", Sampler):
                with self.assertRaisesRegex(TimeoutError, "expired after native"):
                    runtime.run(plan, folder, out, check=check, write_json=write, append_event=lambda e: None)
            self.assertTrue((out / "first.wav").is_file())
            self.assertTrue((out / "first.json").is_file())
            self.assertTrue((out / "first.trace.json").is_file())
            self.assertFalse((out / "second.wav").exists())
            self.assertFalse((out / "RESULT.json").exists())


if __name__ == "__main__":
    unittest.main()
