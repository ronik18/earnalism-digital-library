"""Notebook contract checks without Colab, model downloads or CUDA execution."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch
import importlib.util
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
import zipfile

_spec = importlib.util.spec_from_file_location('earnalism_batch_builder_test_subject', Path(__file__).with_name('build_batch_colab.py'))
c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c)


class BatchNotebook(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.art = self.root/'art'; self.art.mkdir()
        (self.art/'বাগান.png').write_bytes(b'illustration-test-fixture')
        profile = c.b.w.PROFILES['l4-landscape-v1']
        scene = {'id': 'garden-reaction', 'image': 'বাগান.png',
                 'image_sha256': c.b.w.sha(self.art/'বাগান.png'), 'profile': 'l4-landscape-v1',
                 **{k: profile[k] for k in ['width', 'height', 'frames', 'fps']},
                 'inference_steps': profile['steps'], 'guidance_scale': profile['guidance'],
                 'seed': 9471, 'prompt': 'Notice the bird, lean gently, smile and settle with a stable face.'}
        job = {'schema': c.b.SCHEMA, 'run_id': 'novel-test-batch', 'model': c.b.w.MODEL,
               'model_revision': c.b.w.REVISION, 'private': True, 'publication_approved': False,
               'wall_seconds': 2700, 'max_attempts': 1, 'max_output_seconds': 121/24,
               'prior_attempt_evidence': {'scope': 'test only; no generation authority'}, 'scenes': [scene]}
        self.job = self.root/'original-job.json'; c.b.w.write(self.job, job)
        self.notebook = c.build(self.root/'bundle', self.job, self.art)
        self.bundle = self.notebook.parent
        self.cells = json.loads(self.notebook.read_text())['cells']

    def cell(self, heading):
        for index, cell in enumerate(self.cells):
            if cell['cell_type'] == 'markdown' and ''.join(cell['source']).startswith('## '+heading):
                return ''.join(self.cells[index+1]['source'])
        self.fail('Missing cell '+heading)

    def prepared(self):
        root = self.root/'runtime'; root.mkdir()
        (root/'job.json').write_bytes(self.job.read_bytes())
        for name in ['worker.py', 'batch.py']:
            (root/name).write_bytes(Path(c.__file__).with_name(name).read_bytes())
        fake = Mock(); fake.w.sha.side_effect = c.b.w.sha
        ns = {'RUN_BATCH': True, 'batch': fake, 'ROOT': root,
              'INPUTS_VERIFIED_JOB_SHA256': c.b.w.sha(root/'job.json'),
              'PREFLIGHT_OK': True, 'pathlib': pathlib, 'json': json,
              'threading': threading, 'time': time,
              'BOUND_SOFTWARE_SHA256': {name: c.b.w.sha(root/name) for name in ['worker.py','batch.py']}}
        return ns, fake

    def test_default_run_all_inert_and_all_cells_compile(self):
        ns = {}
        with redirect_stdout(StringIO()) as output:
            for cell in self.cells:
                if cell['cell_type'] == 'code': exec(compile(''.join(cell['source']), 'batch-notebook', 'exec'), ns)
        self.assertIn('GENERATE_BATCH_DISABLED', output.getvalue())
        self.assertNotIn('ROOT', ns); self.assertNotIn('batch', ns)
        self.assertNotIn('google.colab', ns)
        self.assertEqual(set(p.name for p in self.bundle.iterdir()),
                         {'job.json', 'wan22-batch-inputs.zip', 'build-manifest.json', self.notebook.name})

    def test_bound_job_software_and_archive_manifest(self):
        m = json.loads((self.bundle/'build-manifest.json').read_text())
        self.assertEqual(m['job_sha256'], c.b.w.sha(self.job))
        self.assertEqual(m['notebook_sha256'], c.b.w.sha(self.notebook))
        self.assertEqual(m['inputs_sha256'], c.b.w.sha(self.bundle/'wan22-batch-inputs.zip'))
        self.assertEqual(m['software_sha256'], {name: c.b.w.sha(Path(c.__file__).with_name(name)) for name in ['worker.py', 'batch.py']})
        self.assertFalse(m['authority_created']); self.assertEqual(m['gpu_execution_qualification'], 'UNQUALIFIED')
        with zipfile.ZipFile(self.bundle/'wan22-batch-inputs.zip') as z:
            self.assertEqual(set(z.namelist()), {'job.json', 'inputs/বাগান.png'})
            self.assertEqual(z.read('job.json'), self.job.read_bytes())
            self.assertEqual(z.read('inputs/বাগান.png'), (self.art/'বাগান.png').read_bytes())
        self.assertIn(m['inputs_sha256'], self.cell('Verify uploaded'))
        self.assertIn(m['job_sha256'], self.cell('Prepare bound'))

    def test_build_rejects_tamper_or_overwrite_without_mutation(self):
        before = {p.name: p.read_bytes() for p in self.bundle.iterdir()}
        with self.assertRaises(FileExistsError): c.build(self.bundle, self.job, self.art)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.bundle.iterdir()})
        (self.art/'বাগান.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Changed source'): c.build(self.root/'bad', self.job, self.art)
        self.assertFalse((self.root/'bad').exists())

    def test_setup_requires_matching_verified_sources_and_actual_preflight(self):
        ns, fake = self.prepared(); ns['SETUP_BATCH'] = True
        ns['INPUTS_VERIFIED_JOB_SHA256'] = 'stale'
        with self.assertRaisesRegex(RuntimeError, 'source-bound'): exec(self.cell('Explicit isolated'), ns)
        fake.setup.assert_not_called()
        ns['INPUTS_VERIFIED_JOB_SHA256'] = c.b.w.sha(ns['ROOT']/'job.json'); ns['PREFLIGHT_OK'] = False
        with self.assertRaisesRegex(RuntimeError, 'actual allocation'): exec(self.cell('Explicit isolated'), ns)
        fake.setup.assert_not_called()
        ns['PREFLIGHT_OK'] = True; (ns['ROOT']/'setup.json').write_text('{}')
        with redirect_stdout(StringIO()): exec(self.cell('Explicit isolated'), ns)
        fake.setup.assert_called_once_with(ns['ROOT']); fake.export.assert_called_once_with(ns['ROOT'])

    def test_begin_requires_supplied_authority_and_does_not_renew_guard(self):
        ns, fake = self.prepared(); ns['BEGIN_ALLOCATION'] = True
        ns['AUTHORITY_PATH'] = str(self.root/'missing-authority.json')
        runtime = Mock(); colab = types.ModuleType('google.colab'); colab.runtime = runtime
        google = types.ModuleType('google'); google.colab = colab
        with patch.dict(sys.modules, {'google': google, 'google.colab': colab}):
            with self.assertRaisesRegex(RuntimeError, 'separately authorized'): exec(self.cell('Bind supplied'), ns)
            fake.begin.assert_not_called(); self.assertFalse(ns['PREFLIGHT_OK'])
            authority = {'scope': 'supplied test authority only'}
            pathlib.Path(ns['AUTHORITY_PATH']).write_text(json.dumps(authority))
            session = {'job_sha256': c.b.w.sha(self.job), 'deadline': time.time()+1000}
            fake.begin.return_value = session; fake.preflight.return_value = {'actual': 'mock-only'}
            timer = Mock()
            with patch.object(threading, 'Timer', return_value=timer) as factory, redirect_stdout(StringIO()):
                exec(self.cell('Bind supplied'), ns); exec(self.cell('Bind supplied'), ns)
                factory.assert_called_once(); timer.start.assert_called_once()
                self.assertTrue(ns['PREFLIGHT_OK'])
                self.assertEqual(fake.begin.call_args.args, (ns['ROOT'], authority))
                fake.begin.return_value = dict(session, deadline=session['deadline']+1)
                with self.assertRaisesRegex(RuntimeError, 'no deadline renewal'): exec(self.cell('Bind supplied'), ns)
        self.assertEqual(runtime.unassign.call_count, 2)

    def test_all_begin_authority_failures_release_only_the_enabled_runtime(self):
        ns, fake = self.prepared(); ns['BEGIN_ALLOCATION'] = True
        authority_path = self.root/'authority-failures.json'; ns['AUTHORITY_PATH'] = str(authority_path)
        runtime = Mock(); colab = types.ModuleType('google.colab'); colab.runtime = runtime
        google = types.ModuleType('google'); google.colab = colab
        existing_guard = Mock(); ns['wan_batch_guard'] = existing_guard
        ns['wan_batch_guard_key'] = ('preserve', 1)
        with patch.dict(sys.modules, {'google': google, 'google.colab': colab}), patch.object(threading, 'Timer') as timer:
            failures = [
                ('missing', None, None),
                ('malformed', '{', None),
                ('expired', '{}', RuntimeError('Original deadline expired')),
                ('rate', '{}', RuntimeError('Actual free allocation or bounded metered authority is missing')),
            ]
            for label, value, error in failures:
                if value is None:
                    if authority_path.exists(): authority_path.unlink()
                else: authority_path.write_text(value)
                fake.begin.side_effect = error
                runtime.reset_mock(); fake.setup.reset_mock(); fake.preflight.reset_mock(); fake.export.reset_mock()
                with self.subTest(failure=label), self.assertRaises((RuntimeError, json.JSONDecodeError)):
                    exec(self.cell('Bind supplied'), ns)
                runtime.unassign.assert_called_once(); fake.setup.assert_not_called(); fake.preflight.assert_not_called()
                fake.export.assert_called_once_with(ns['ROOT'])
                self.assertFalse(ns['PREFLIGHT_OK']); self.assertIs(ns['wan_batch_guard'], existing_guard)
            timer.assert_not_called(); existing_guard.cancel.assert_not_called()

    def test_begin_prerequisite_failures_also_release_and_default_does_not(self):
        ns, fake = self.prepared(); ns['BEGIN_ALLOCATION'] = True
        runtime = Mock(); colab = types.ModuleType('google.colab'); colab.runtime = runtime
        google = types.ModuleType('google'); google.colab = colab
        with patch.dict(sys.modules, {'google': google, 'google.colab': colab}):
            for state in ['stale-inputs', 'missing-inputs', 'unprepared']:
                runtime.reset_mock(); fake.begin.reset_mock()
                ns['RUN_BATCH'] = state != 'unprepared'
                ns['INPUTS_VERIFIED_JOB_SHA256'] = 'stale'
                if state == 'missing-inputs': ns.pop('INPUTS_VERIFIED_JOB_SHA256')
                with self.subTest(state=state), self.assertRaisesRegex(RuntimeError, 'source-bound|bound software'):
                    exec(self.cell('Bind supplied'), ns)
                runtime.unassign.assert_called_once(); fake.begin.assert_not_called()
            runtime.reset_mock(); ns['BEGIN_ALLOCATION'] = False
            with redirect_stdout(StringIO()): exec(self.cell('Bind supplied'), ns)
            runtime.unassign.assert_not_called()

    def test_preflight_failure_exports_and_unassigns_before_setup(self):
        ns, fake = self.prepared(); ns['BEGIN_ALLOCATION'] = True
        ns['AUTHORITY_PATH'] = str(self.root/'authority.json'); pathlib.Path(ns['AUTHORITY_PATH']).write_text('{}')
        fake.begin.return_value = {'job_sha256': c.b.w.sha(self.job), 'deadline': time.time()+1000}
        fake.preflight.side_effect = RuntimeError('actual CUDA unavailable')
        runtime = Mock(); colab = types.ModuleType('google.colab'); colab.runtime = runtime
        google = types.ModuleType('google'); google.colab = colab
        with patch.dict(sys.modules, {'google': google, 'google.colab': colab}), patch.object(threading, 'Timer'):
            with self.assertRaisesRegex(RuntimeError, 'CUDA'): exec(self.cell('Bind supplied'), ns)
        self.assertFalse(ns['PREFLIGHT_OK']); fake.export.assert_called_once_with(ns['ROOT'])
        runtime.unassign.assert_called_once(); fake.setup.assert_not_called()

    def test_one_warm_venv_subprocess_uses_original_remaining_timeout(self):
        ns, fake = self.prepared(); ns.update(GENERATE_BATCH=True, RESUME_UNATTEMPTED=False)
        (ns['ROOT']/'venv/bin').mkdir(parents=True); (ns['ROOT']/'venv/bin/python').write_bytes(b'test executable marker')
        fake.remaining.return_value = 391.0
        process = Mock(); process.wait.return_value = 0; process.poll.return_value = 0
        with patch.object(subprocess, 'Popen', return_value=process) as popen, redirect_stdout(StringIO()):
            exec(self.cell('One supervised'), ns)
        popen.assert_called_once(); self.assertEqual(popen.call_args.args[0],
            [str(ns['ROOT']/'venv/bin/python'), str(ns['ROOT']/'batch.py'), 'run', str(ns['ROOT']), '--execute'])
        self.assertTrue(popen.call_args.kwargs['start_new_session'])
        process.wait.assert_called_once_with(timeout=391.0)
        fake.export.assert_called_once_with(ns['ROOT']); fake.run.assert_not_called()

    def test_warm_timeout_terminates_exports_and_never_retries(self):
        ns, fake = self.prepared(); ns.update(GENERATE_BATCH=True, RESUME_UNATTEMPTED=True)
        (ns['ROOT']/'venv/bin').mkdir(parents=True); (ns['ROOT']/'venv/bin/python').write_bytes(b'test')
        fake.remaining.return_value = 30
        process = Mock(); process.pid = 876543; process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired('test-only', 30), 0]
        with patch.object(subprocess, 'Popen', return_value=process) as popen, patch.object(os, 'killpg') as kill:
            with self.assertRaises(subprocess.TimeoutExpired): exec(self.cell('One supervised'), ns)
        self.assertEqual(popen.call_count, 1); self.assertEqual(popen.call_args.args[0][-1], '--resume')
        kill.assert_called_once_with(process.pid, signal.SIGTERM)
        fake.export.assert_called_once_with(ns['ROOT'])

    def test_missing_venv_or_failed_preflight_cannot_spawn(self):
        ns, fake = self.prepared(); ns.update(GENERATE_BATCH=True, RESUME_UNATTEMPTED=False)
        with patch.object(subprocess, 'Popen') as popen:
            with self.assertRaisesRegex(RuntimeError, 'isolated setup'): exec(self.cell('One supervised'), ns)
            ns['PREFLIGHT_OK'] = False
            with self.assertRaisesRegex(RuntimeError, 'actual allocation'): exec(self.cell('One supervised'), ns)
            popen.assert_not_called()

    def test_bound_software_tamper_stops_before_setup_or_warm_spawn(self):
        ns, fake = self.prepared(); ns.update(SETUP_BATCH=True, GENERATE_BATCH=True, RESUME_UNATTEMPTED=False)
        (ns['ROOT']/'worker.py').write_bytes(b'changed')
        with patch.object(subprocess, 'Popen') as popen:
            for heading in ['Explicit isolated','One supervised']:
                with self.assertRaisesRegex(RuntimeError, 'Bound software changed'): exec(self.cell(heading), ns)
            fake.setup.assert_not_called(); popen.assert_not_called()


if __name__ == '__main__': unittest.main()
