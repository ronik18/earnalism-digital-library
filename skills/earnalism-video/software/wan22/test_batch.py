"""Queue/control regression checks. Injected media is never labelled model output."""
from pathlib import Path
from unittest.mock import Mock, patch
import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile

_spec = importlib.util.spec_from_file_location('earnalism_batch_test_subject', Path(__file__).with_name('batch.py'))
b = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b)


class BatchQueue(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'book-batch'
        (self.root / 'inputs').mkdir(parents=True)
        self.scenes = []
        for sid, name in [('garden-en', 'garden.png'), ('বই'.encode().hex(), 'বাগান.png'), ('settle', 'settle.png')]:
            source = self.root / 'inputs' / name
            source.write_bytes(('test-only-source-' + sid).encode())
            profile = b.w.PROFILES['l4-landscape-v1']
            self.scenes.append({'id': sid, 'image': name, 'image_sha256': b.w.sha(source),
                                'profile': 'l4-landscape-v1', 'width': profile['width'],
                                'height': profile['height'], 'frames': 121, 'fps': 24,
                                'inference_steps': 24, 'guidance_scale': 5.0, 'seed': 9471,
                                'prompt': 'A visible attentive reaction develops into a warm smile.'})
        self.job = {'schema': b.SCHEMA, 'run_id': 'two-books-test', 'model': b.w.MODEL,
                    'model_revision': b.w.REVISION, 'private': True, 'publication_approved': False,
                    'wall_seconds': 2700, 'max_attempts': 3, 'max_output_seconds': 3 * 121 / 24,
                    'prior_attempt_evidence': {'scope': 'test fixture only; no qualification'},
                    'scenes': self.scenes}
        b.w.write(self.root / 'job.json', self.job)
        self.authority = {'schema': b.AUTHORITY_SCHEMA, 'owner_authorized': True,
                          'evidence_ref': 'TEST_ONLY_NOT_REAL_COMPUTE_AUTHORITY',
                          'job_sha256': b.w.sha(self.root / 'job.json'),
                          'free_runtime_confirmed': False, 'observed_units_per_hour': 1.94,
                          'approved_compute_units': 5, 'allocation_started_at': time.time() - 10}
        b.begin(self.root, self.authority)
        self.loaded = 0
        self.calls = []
        self.closed = 0

    def factory(self, root, job):
        self.loaded += 1
        outer = self
        class Backend:
            def generate(self, scene, image, output, callback):
                outer.calls.append(scene['id'])
                output.write_bytes(('TEST_FIXTURE_NOT_MODEL_OUTPUT-' + scene['id']).encode())
            def close(self):
                outer.closed += 1
        return Backend()

    def fixture_probe(self, output, scene):
        return {'scope': 'test bytes only; no actual video probe'}

    def run_fixture(self, **kwargs):
        return b.run(self.root, backend_factory=self.factory, probe=self.fixture_probe, **kwargs)

    def test_three_shots_use_one_load_and_preserve_quality_pending(self):
        result = self.run_fixture()
        self.assertEqual((self.loaded, self.closed), (1, 1))
        self.assertEqual(self.calls, [s['id'] for s in self.scenes])
        rows = json.loads((self.root / 'attempts.json').read_text())
        self.assertEqual({r['status'] for r in rows}, {'TEST_FIXTURE_NOT_MODEL_OUTPUT'})
        self.assertEqual({r['quality_review'] for r in rows}, {'PENDING'})
        self.assertEqual(result['state'], 'TECHNICAL_TEST_ONLY')
        with zipfile.ZipFile(self.root / 'wan22-batch-export.zip') as z:
            m = json.loads(z.read('export-manifest.json'))
            self.assertEqual(len([n for n in z.namelist() if n.endswith('.mp4')]), 3)
            self.assertEqual(m['quality_acceptance'], 'PENDING')
            self.assertFalse(m['publication_approved'])
        before = {p.name: b.w.sha(p) for p in (self.root / 'outputs').iterdir()}
        resumed = self.run_fixture(resume=True)
        self.assertEqual(self.loaded, 1)
        self.assertEqual(resumed['state'], 'NO_UNATTEMPTED_SHOTS')
        self.assertEqual(before, {p.name: b.w.sha(p) for p in (self.root / 'outputs').iterdir()})

    def test_failed_second_shot_is_exported_and_never_retried(self):
        factory = self.factory
        def failing(root, job):
            backend = factory(root, job)
            normal = backend.generate
            def generate(scene, image, output, callback):
                if scene['id'] == self.scenes[1]['id']:
                    self.calls.append(scene['id'])
                    output.write_bytes(b'partial-test-fixture')
                    raise RuntimeError('controlled fixture interruption')
                normal(scene, image, output, callback)
            backend.generate = generate
            return backend
        with self.assertRaisesRegex(RuntimeError, 'fixture interruption'):
            b.run(self.root, backend_factory=failing, probe=self.fixture_probe)
        rows = json.loads((self.root / 'attempts.json').read_text())
        self.assertEqual([r['status'] for r in rows],
                         ['TEST_FIXTURE_NOT_MODEL_OUTPUT', 'FAILED_NO_AUTOMATIC_RETRY'])
        first_hash = b.w.sha(self.root / 'outputs' / (self.scenes[0]['id'] + '.mp4'))
        with zipfile.ZipFile(self.root / 'wan22-batch-export.zip') as z:
            self.assertEqual(json.loads(z.read('attempts.json'))[1]['status'], 'FAILED_NO_AUTOMATIC_RETRY')
            self.assertIn(b'partial-test-fixture', [z.read(n) for n in z.namelist() if n.endswith('.mp4')])
        with self.assertRaisesRegex(RuntimeError, 'explicit resume'):
            self.run_fixture()
        self.run_fixture(resume=True)
        self.assertEqual(self.calls.count(self.scenes[1]['id']), 1)
        self.assertEqual(self.calls.count(self.scenes[0]['id']), 1)
        self.assertEqual(self.calls[-1], self.scenes[2]['id'])
        self.assertEqual(first_hash, b.w.sha(self.root / 'outputs' / (self.scenes[0]['id'] + '.mp4')))

    def test_tampered_completed_media_is_not_overwritten(self):
        self.run_fixture()
        (self.root / 'outputs' / (self.scenes[0]['id'] + '.mp4')).write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError, 'Completed output changed'):
            self.run_fixture(resume=True)
        self.assertEqual(self.loaded, 1)

    def test_source_and_job_tampering_stop_before_model_load(self):
        (self.root / 'inputs' / self.scenes[0]['image']).write_bytes(b'changed image')
        with self.assertRaisesRegex(ValueError, 'Changed source'):
            self.run_fixture()
        self.assertEqual(self.loaded, 0)
        # Restore the source, then mutate a valid prompt without renewing authority.
        (self.root / 'inputs' / self.scenes[0]['image']).write_bytes(b'test-only-source-garden-en')
        changed = copy.deepcopy(self.job)
        changed['scenes'][0]['prompt'] += ' Unreviewed change.'
        b.w.write(self.root / 'job.json', changed)
        with self.assertRaisesRegex(RuntimeError, 'authority'):
            self.run_fixture()
        self.assertEqual(self.loaded, 0)

    def test_original_deadline_and_authority_cannot_be_renewed(self):
        original = json.loads((self.root / 'session.json').read_text())
        resumed = b.begin(self.root, self.authority)
        self.assertEqual(original['deadline'], resumed['deadline'])
        changed = dict(self.authority, allocation_started_at=time.time())
        with self.assertRaisesRegex(RuntimeError, 'replace'):
            b.begin(self.root, changed)
        with self.assertRaisesRegex(RuntimeError, 'deadline'):
            b.remaining(self.root, now=original['deadline'])
        original['deadline'] += 100
        b.w.write(self.root / 'session.json', original)
        with self.assertRaisesRegex(RuntimeError, 'original session'):
            self.run_fixture()
        self.assertEqual(self.loaded, 0)

    def test_inadequate_rate_allowance_has_no_session(self):
        other = Path(self.temp.name) / 'other'
        shutil.copytree(self.root, other)
        (other / 'session.json').unlink(); (other / 'authorization.json').unlink()
        bad = dict(self.authority, approved_compute_units=1)
        with self.assertRaisesRegex(RuntimeError, 'bounded metered'):
            b.begin(other, bad)
        self.assertFalse((other / 'session.json').exists())

    def test_budget_exhaustion_does_not_spend_a_new_shot(self):
        real_remaining = b.remaining
        count = 0
        def bounded(root, *args, **kwargs):
            nonlocal count
            count += 1
            # First shot completes; the second is refused before reservation.
            return 300 if count >= 7 else real_remaining(root, *args, **kwargs)
        with patch.object(b, 'remaining', side_effect=bounded):
            with self.assertRaisesRegex(RuntimeError, 'headroom'):
                self.run_fixture()
        rows = json.loads((self.root / 'attempts.json').read_text())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['scene'], self.scenes[0]['id'])
        self.assertEqual(self.closed, 1)

    def test_legacy_and_new_queue_share_cross_root_gpu_lock(self):
        with b.w.gpu_lock():
            with self.assertRaisesRegex(RuntimeError, 'Another Earnalism'):
                self.run_fixture()
        self.assertEqual(self.loaded, 0)
        self.assertFalse((self.root / 'attempts.json').exists())

    def test_legacy_contract_not_relabelled_as_general_batch(self):
        with self.assertRaisesRegex(ValueError, 'distinct batch schema'):
            b.validate(dict(self.job, schema=b.w.SCHEMA))
        with self.assertRaises(ValueError):
            b.w.validate(self.job)
        for field, value in [('max_attempts', 4), ('max_output_seconds', 99),
                             ('wall_seconds', 2701), ('model_revision', 'unreviewed')]:
            with self.assertRaises(ValueError):
                b.validate(dict(self.job, **{field: value}))
        bad = copy.deepcopy(self.job); bad['scenes'][0]['seed'] = True
        with self.assertRaisesRegex(ValueError, 'seed'):
            b.validate(bad)
        bad = copy.deepcopy(self.job); bad['scenes'][0]['last_image'] = 'end.png'
        with self.assertRaisesRegex(ValueError, 'endpoint'):
            b.validate(bad)

    def test_sealed_input_import_accepts_unicode_images_and_rejects_extra_audio(self):
        archive = Path(self.temp.name) / 'inputs.zip'
        def pack(extra=False):
            with zipfile.ZipFile(archive, 'w') as z:
                z.write(self.root / 'job.json', 'job.json')
                for scene in self.scenes:
                    z.write(self.root / 'inputs' / scene['image'], 'inputs/' + scene['image'])
                if extra:
                    z.writestr('narration.mp3', b'not-an-i2v-input')
        pack()
        imported = Path(self.temp.name) / 'new-runtime'
        job = b.unpack_inputs(archive, imported, b.w.sha(archive))
        self.assertEqual(job['scenes'][1]['image'], 'বাগান.png')
        self.assertEqual(b.w.sha(imported / 'job.json'), b.w.sha(self.root / 'job.json'))
        pack(True)
        rejected = Path(self.temp.name) / 'bad-runtime'
        with self.assertRaisesRegex(ValueError, 'Unexpected input member'):
            b.unpack_inputs(archive, rejected, b.w.sha(archive))
        self.assertFalse(rejected.exists())

    def test_model_failure_is_durable_and_capped(self):
        failed = Mock(side_effect=RuntimeError('fixture load failure'))
        with self.assertRaisesRegex(RuntimeError, 'fixture load failure'):
            b.run(self.root, backend_factory=failed)
        loads = json.loads((self.root / 'model-loads.json').read_text())
        self.assertEqual(loads[0]['status'], 'FAILED_LOAD_NO_AUTOMATIC_RETRY')
        self.assertTrue((self.root / 'wan22-batch-export.zip').is_file())
        with self.assertRaisesRegex(RuntimeError, 'explicit resume'):
            b.run(self.root, backend_factory=failed)
        self.assertEqual(failed.call_count, 1)

    def test_private_fixture_export_import_is_bound_and_rejected_as_model_media(self):
        self.run_fixture()
        archive = self.root / 'wan22-batch-export.zip'
        destination = Path(self.temp.name) / 'imported'
        accepted = b.import_export(archive, destination, b.w.sha(archive), self.root / 'job.json')
        self.assertEqual(accepted, [])
        receipt = json.loads((destination / 'import-receipt.json').read_text())
        self.assertEqual(len(receipt['rejected']), 3)
        self.assertEqual(receipt['quality_review'], 'PENDING')
        self.assertFalse(receipt['publication_approved'])
        self.assertEqual(receipt['batch_gpu_path_qualification'], 'UNQUALIFIED')
        with self.assertRaises(FileExistsError):
            b.import_export(archive, destination, b.w.sha(archive), self.root / 'job.json')
        bad_destination = Path(self.temp.name) / 'bad-import'
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            b.import_export(archive, bad_destination, '0' * 64, self.root / 'job.json')
        self.assertFalse(bad_destination.exists())

    def test_fixture_row_cannot_be_promoted_by_changing_only_status(self):
        self.run_fixture()
        path = self.root / 'attempts.json'
        rows = json.loads(path.read_text())
        rows[0]['status'] = 'TECHNICAL_PASS_REVIEW_PENDING'
        b.w.write(path, rows)
        with self.assertRaisesRegex(RuntimeError, 'fixture cannot become model-output'):
            self.run_fixture(resume=True)

    def test_cli_run_is_inert_without_execute(self):
        before = {p.name for p in self.root.iterdir()}
        for action in ('run', 'setup'):
            result = subprocess.run([sys.executable, str(Path(b.__file__)), action, str(self.root)],
                                    check=True, capture_output=True, text=True)
            self.assertIn('BATCH_DISABLED', result.stdout)
        self.assertEqual(before, {p.name for p in self.root.iterdir()})

    def test_setup_uses_batch_clock_and_cached_setup_is_not_reinstalled(self):
        def install(root, run_command):
            run_command(root, ['TEST_ONLY_NO_INSTALL'], 'setup.log')
            (root / 'model').mkdir()
            (root / 'model/model_index.json').write_text('{}')
            b.w.write(root / 'setup.json', {'state': 'SETUP_COMPLETED_NOT_INFERENCE_QUALIFIED',
                    'model': b.w.MODEL, 'revision': b.w.REVISION})
        with patch.object(b, 'preflight') as preflight, patch.object(b.w, 'install_model', side_effect=install) as setup:
            with patch.object(b.subprocess, 'run') as run:
                first = b.setup(self.root)
                self.assertLess(run.call_args.kwargs['timeout'], 2700)
                self.assertEqual(run.call_args.args[0], ['TEST_ONLY_NO_INSTALL'])
            second = b.setup(self.root)
            self.assertEqual(first, second)
            self.assertEqual(setup.call_count, 1)
            self.assertEqual(preflight.call_count, 1)
        b.w.write(self.root / 'setup.json', {})
        with self.assertRaisesRegex(RuntimeError, 'incomplete or changed setup'):
            b.setup(self.root)

    def test_production_backend_reuses_one_exact_pipe_without_gpu_execution(self):
        b.w.write(self.root / 'setup.json', {'state': 'SETUP_COMPLETED_NOT_INFERENCE_QUALIFIED',
                'model': b.w.MODEL, 'revision': b.w.REVISION})
        pipe = object()
        with patch.object(b, 'preflight'), patch('PIL.Image.open'), patch.object(b.w, 'load_pipeline', return_value=pipe) as load, patch.object(b.w, 'render_scene') as render:
            backend = b.WanBackend(self.root, self.job)
            for scene in self.scenes:
                callback = object()
                backend.generate(scene, Path('source'), Path('output'), callback)
                self.assertIs(render.call_args.args[0], pipe)
                self.assertIs(render.call_args.args[-1], callback)
                self.assertEqual(render.call_args.args[-2]['steps'], 24)
            self.assertEqual(load.call_count, 1)
            self.assertEqual(render.call_count, 3)
            backend.close()
            self.assertIsNone(backend.pipe)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
    def test_real_media_probe_still_cannot_make_a_fixture_model_qualified(self):
        def factory(root, job):
            backend = self.factory(root, job)
            def generate(scene, image, output, callback):
                self.calls.append(scene['id'])
                subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                    f"color=blue:s={scene['width']}x{scene['height']}:r=24", '-frames:v', '121',
                    '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', str(output)],
                    check=True, capture_output=True)
            backend.generate = generate
            return backend
        result = b.run(self.root, backend_factory=factory)
        self.assertEqual(result['state'], 'TECHNICAL_TEST_ONLY')
        rows = json.loads((self.root / 'attempts.json').read_text())
        self.assertEqual({r['status'] for r in rows}, {'TEST_FIXTURE_NOT_MODEL_OUTPUT'})
        self.assertEqual(rows[0]['probe']['streams'][0]['nb_read_frames'], '121')


if __name__ == '__main__':
    unittest.main()
