"""Balanced checkpoint/runtime contracts using tiny synthetic objects only.

No torch/transformers/Parler import, model load, speech or account operation.
"""
from contextlib import nullcontext
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest import TestCase, main, mock

from scripts.earnalism_voice_runtime import parler as runtime


class Tensor:
    dtype = "TEST_FLOAT32"
    requires_grad = False
    is_meta = False
    device = SimpleNamespace(type="cpu")

    def __init__(self, shape, trained=False):
        self.shape, self.trained, self.copies = shape, trained, 0

    def copy_(self, other):
        self.trained = other.trained
        self.copies += 1

    def requires_grad_(self, value):
        self.requires_grad = value


class Model:
    def __init__(self):
        self.values = {name: Tensor(shape) for name, shape in runtime._shapes().items()}
        self.values["encoder.fixture"] = Tensor((2,))
        self.config = SimpleNamespace(sampling_rate=44100)

    def named_parameters(self):
        return self.values.items()

    def parameters(self):
        return self.values.values()

    def state_dict(self):
        return self.values

    def to(self, **kwargs):
        return self

    def eval(self):
        return self


class BalancedRuntime(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.binding = {"format": runtime.BALANCED_FORMAT, "sha256": "test-checkpoint",
            "bindings_sha256": "test-bindings", "training_updates": 128,
            "tensor_sha256": "test-trained", "frozen_sha256": "test-frozen",
            "supervised_scope": "BN_EN_MF_BALANCED", "records_sha256": "test-records",
            "schedule_sha256": "test-schedule", "seed": 20261114, "max_updates": 128,
            "stratum_exposure_counts": {"bn:male": 32, "bn:female": 32, "en:male": 32, "en:female": 32}}
        self.saved = {"format": self.binding["format"], "base_sha256": "test-base",
            "bindings_sha256": self.binding["bindings_sha256"], "step": 128,
            "supervised_scope": self.binding["supervised_scope"],
            **{key: self.binding[key] for key in ("records_sha256", "schedule_sha256", "seed",
                                                   "max_updates", "stratum_exposure_counts")},
            "trainable": {name: Tensor(shape, trained=True) for name, shape in runtime._shapes().items()},
            # Payload is never passed to optimizer/RNG helpers during inference.
            "optimizer": object(), "python_rng": object(), "cpu_rng": object(), "cuda_rng": object()}
        self.torch = SimpleNamespace(float32="TEST_FLOAT32", no_grad=nullcontext, set_num_threads=mock.Mock(),
            isfinite=lambda tensor: SimpleNamespace(all=lambda: SimpleNamespace(item=lambda: True)),
            load=mock.Mock(return_value=self.saved))

    @staticmethod
    def digest(tensors):
        if set(tensors) == {"encoder.fixture"}:
            return "test-frozen"
        return "test-trained" if all(tensor.trained for tensor in tensors.values()) else "test-base-state"

    def validated(self):
        with mock.patch.object(runtime, "_tensor_digest", side_effect=self.digest):
            return runtime._validated_trainable(self.saved, self.binding, "test-base", self.torch)

    def test_balanced_metadata_accepts_actual_schema_without_invented_strata_field(self):
        self.assertNotIn("strata_binding_sha256", self.saved)
        tensors, scope = self.validated()
        self.assertEqual(scope, "BN_EN_MF_BALANCED")
        self.assertEqual(len(tensors), 16)

    def test_every_balanced_metadata_mismatch_is_rejected(self):
        for key in ("format", "base_sha256", "bindings_sha256", "step", "supervised_scope",
                    "records_sha256", "schedule_sha256", "seed", "max_updates", "stratum_exposure_counts"):
            with self.subTest(key=key):
                previous = self.saved[key]
                self.saved[key] = "WRONG"
                with self.assertRaisesRegex(ValueError, "SCHEMA"):
                    self.validated()
                self.saved[key] = previous

    def test_integer_metadata_rejects_bool(self):
        for key in ("step", "max_updates", "seed"):
            previous = self.saved[key]
            self.saved[key] = True
            with self.assertRaises(ValueError):
                self.validated()
            self.saved[key] = previous

    def test_wrong_shape_dtype_nonfinite_and_digest_fail_closed(self):
        name = next(iter(self.saved["trainable"]))
        tensor = self.saved["trainable"][name]
        for attr, bad in (("shape", (4,)), ("dtype", "TEST_FLOAT64")):
            original = getattr(tensor, attr)
            setattr(tensor, attr, bad)
            with self.assertRaises(ValueError):
                self.validated()
            setattr(tensor, attr, original)
        with mock.patch.object(self.torch, "isfinite", return_value=SimpleNamespace(
                all=lambda: SimpleNamespace(item=lambda: False))):
            with self.assertRaises(ValueError):
                self.validated()
        with mock.patch.object(runtime, "_tensor_digest", return_value="wrong"):
            with self.assertRaises(ValueError):
                runtime._validated_trainable(self.saved, self.binding, "test-base", self.torch)

    def test_old_male130_metadata_stays_separate(self):
        self.binding.update(format="EARNALISM_PARLER_LAST_BLOCK_V1", training_updates=130)
        self.saved.update(format=self.binding["format"], step=130, supervised_scope="MALE_BENGALI_ONLY")
        for key in ("records_sha256", "schedule_sha256", "seed", "max_updates", "stratum_exposure_counts"):
            self.saved.pop(key)
        self.assertEqual(self.validated()[1], "MALE_BENGALI_ONLY")
        self.saved["supervised_scope"] = "BN_EN_MF_BALANCED"
        with self.assertRaises(ValueError):
            self.validated()

    def fixture_profile(self):
        model_dir = self.root / "model"
        description_dir = self.root / "description"
        source_root = self.root / "source"
        (source_root / "parler_tts").mkdir(parents=True)
        source = source_root / "parler_tts/__init__.py"
        source.write_text("# TEST SOURCE ONLY\n")
        files = [source]
        for folder, names in ((model_dir, ("config.json", "generation_config.json", "model.safetensors",
                "special_tokens_map.json", "tokenizer.json", "tokenizer.model", "tokenizer_config.json")),
                (description_dir, ("special_tokens_map.json", "spiece.model", "tokenizer.json", "tokenizer_config.json"))):
            folder.mkdir()
            for name in names:
                path = folder / name
                path.write_bytes(b"TEST FIXTURE ONLY")
                files.append(path)
        return {"base": {"sha256": "test-base"}, "checkpoint": self.binding,
            "assets": {"model_dir": str(model_dir), "description_tokenizer_dir": str(description_dir),
                "source_root": str(source_root), "files": [{"path": str(path)} for path in files]},
            "runtime": {"python": ".".join(map(str, sys.version_info[:2])), "packages": {}}}

    def test_fixed_loader_restores_only_sixteen_tensors_and_checks_frozen_state(self):
        profile = self.fixture_profile()
        model = Model()
        package = SimpleNamespace(__file__=str(self.root / "source/parler_tts/__init__.py"),
            ParlerTTSForConditionalGeneration=SimpleNamespace(from_pretrained=mock.Mock(return_value=(model,
                {key: [] for key in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")}))))
        tokenizer = SimpleNamespace(AutoTokenizer=SimpleNamespace(from_pretrained=mock.Mock(return_value=object())))
        original_path = sys.path[:]
        self.addCleanup(lambda: setattr(sys, "path", original_path))
        with mock.patch.dict(sys.modules, {"torch": self.torch, "transformers": tokenizer}), \
                mock.patch.object(runtime.importlib, "import_module", return_value=package), \
                mock.patch.object(runtime.importlib.metadata, "distributions", return_value=[]), \
                mock.patch.object(runtime, "_tensor_digest", side_effect=self.digest):
            bundle, _ = runtime._load_bundle(profile, self.root, self.root / "NO_REAL_CHECKPOINT", "cpu", mock.Mock())
        self.torch.load.assert_called_once_with(self.root / "NO_REAL_CHECKPOINT", map_location="cpu", weights_only=True)
        self.torch.set_num_threads.assert_called_once_with(2)
        self.assertEqual(sum(tensor.copies for tensor in model.values.values()), 16)
        self.assertTrue(all(not tensor.requires_grad for tensor in model.values.values()))
        self.assertEqual(bundle["loading_report"]["supervised_training_scope"], "BN_EN_MF_BALANCED")
        package.ParlerTTSForConditionalGeneration.from_pretrained.assert_called_once()

    def test_changed_or_extra_cpu_distribution_blocks_before_model_import(self):
        profile = self.fixture_profile()
        profile["runtime"]["packages"] = {"fixture-package": "1.0"}
        original_path = sys.path[:]
        self.addCleanup(lambda: setattr(sys, "path", original_path))
        for versions in ([('fixture-package', '2.0')], [('fixture-package', '1.0'), ('extra-package', '1.0')]):
            distributions = [SimpleNamespace(metadata={"Name": name}, version=version) for name, version in versions]
            with mock.patch.object(runtime.importlib.metadata, "distributions", return_value=distributions), \
                    mock.patch.object(runtime.importlib, "import_module") as load_module:
                with self.assertRaisesRegex(ValueError, "CPU100"):
                    runtime._load_bundle(profile, self.root, "NO_REAL_CHECKPOINT", "cpu", mock.Mock())
                load_module.assert_not_called()

    def test_frozen_state_and_trainable_changes_are_rejected(self):
        model = Model()
        for name in runtime._shapes():
            model.values[name].trained = True
        with mock.patch.object(runtime, "_tensor_digest", side_effect=self.digest):
            runtime._verify_balanced_state(model, self.binding)
            model.values[next(iter(runtime._shapes()))].trained = False
            with self.assertRaisesRegex(ValueError, "STATE_CHANGED"):
                runtime._verify_balanced_state(model, self.binding)
        with mock.patch.object(runtime, "_tensor_digest", return_value="test-trained"), \
                mock.patch.object(runtime, "_frozen_digest", return_value="wrong"):
            with self.assertRaisesRegex(ValueError, "STATE_CHANGED"):
                runtime._verify_balanced_state(model, self.binding)

    def run_fixture(self, *, cap=False, local_cpu=True, state_failure=False, check_authority=None):
        output = self.root / "output"
        output.mkdir()
        job = {"device": "cpu", "purpose": "qualification", "source": {"sha256": "test-source"},
            "generation": {"max_new_tokens": 2601},
            "units": [{"id": "single", "spoken_text": "TEST SOURCE", "caption_unspoken": "UNSPOKEN",
                "seed": 20261114, "start": 0, "end": 11}],
            "limits": {"max_audio_seconds": 30, "max_output_bytes": 4096}}
        plan = {"job": job, "job_path": "TEST ONLY", "job_sha256": "test-job", "profile_path": "profile.json",
                "binding": {"profile_sha256": "test-profile"}, "unit_fingerprints": ["test-unit"],
                "source_coverage": "SELECTED_EXACT_SOURCE_SPANS_NOT_FULL_TITLE"}
        profile = {"identity": "TEST", "base": {"model_id": "TEST"}, "checkpoint": self.binding}
        authority = {"absolute_deadline_epoch": None, "journal_path": "TEST-ONLY"}
        if local_cpu:
            authority["execution_mode"] = "local_cpu"
        events = []
        def write_json(path, obj):
            with path.open("x") as handle:
                json.dump(obj, handle)
        with mock.patch.object(runtime, "_load_bundle", return_value=({"model": object(), "loading_report": {}}, object())), \
                mock.patch.object(runtime, "BundleSampler") as sampler, \
                mock.patch.object(runtime, "_verify_balanced_state", side_effect=ValueError("TEST_STATE_CHANGED") if state_failure else None):
            sampler.return_value.generate.return_value = ([0.0, 0.125, -0.125], cap)
            result = runtime.run(plan, profile, authority, output, checkpoint_loader=mock.Mock(return_value="TEST"),
                append_event=lambda path, event: events.append(event), write_json=write_json,
                check_authority=check_authority or mock.Mock())
        return result, sampler, events

    def test_local_cpu_one_native_take_no_fake_allocation_deadline(self):
        result, sampler, events = self.run_fixture()
        sampler.return_value.generate.assert_called_once()
        self.assertIsNone(result["original_deadline"])
        self.assertEqual(result["training_updates_in_this_run"], 0)
        self.assertFalse(result["publication_authorized"])
        self.assertEqual(result["fidelity_naturalness_accent_and_mix"], "UNPERFORMED")
        self.assertEqual([event["event"] for event in events], ["unit_intent", "unit_completed"])
        self.assertEqual((self.root / "output/single.wav").stat().st_size, 56)

    def test_absent_deadline_requires_explicit_local_cpu_authority(self):
        with self.assertRaisesRegex(ValueError, "LOCAL_CPU"):
            self.run_fixture(local_cpu=False)
        self.assertFalse((self.root / "output/WORKER-INTENT.json").exists())

    def test_late_state_failure_preserves_native_audio_receipt_without_result(self):
        with self.assertRaisesRegex(ValueError, "TEST_STATE_CHANGED"):
            self.run_fixture(state_failure=True)
        self.assertTrue((self.root / "output/single.wav").is_file())
        self.assertTrue((self.root / "output/single.json").is_file())
        self.assertFalse((self.root / "output/RESULT.json").exists())

    def test_late_authority_failure_preserves_returned_waveform(self):
        authority = mock.Mock(side_effect=[None, None, ValueError("TEST_AUTHORITY_CHANGED")])
        with self.assertRaisesRegex(ValueError, "AUTHORITY_CHANGED"):
            self.run_fixture(check_authority=authority)
        self.assertTrue((self.root / "output/single.wav").is_file())
        self.assertTrue((self.root / "output/single.json").is_file())
        self.assertFalse((self.root / "output/RESULT.json").exists())

    def test_balanced_runtime_requires_actual_controller_callback(self):
        with self.assertRaisesRegex(ValueError, "AUTHORITY_CALLBACK"):
            runtime.run({"job": {}, "profile_path": "TEST"}, {"checkpoint": self.binding}, {}, self.root,
                checkpoint_loader=mock.Mock(), append_event=mock.Mock(), write_json=mock.Mock())

    def test_token_cap_preserves_complete_native_audio_receipt_no_retry(self):
        with self.assertRaisesRegex(ValueError, "OUTPUT_LIMIT"):
            self.run_fixture(cap=True)
        self.assertTrue((self.root / "output/single.wav").is_file())
        self.assertTrue(json.loads((self.root / "output/single.json").read_text())["token_cap_reached"])
        self.assertFalse((self.root / "output/RESULT.json").exists())


if __name__ == "__main__":
    main()
