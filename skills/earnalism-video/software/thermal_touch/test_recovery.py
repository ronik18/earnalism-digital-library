"""Bounded recovery safety tests; no remote access, model run or media import."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import ast
import base64
import copy
import hashlib
import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch

from . import recovery

PROJECT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT / 'output/episodes/04-thermal-touch/production-v1'
FAILURE = PROJECT / 'evidence/thermal-touch-v1/transfer-failure.json'
CHUNKS = PROJECT / 'evidence/thermal-touch-v1/archive-chunks'
AUTH = PROJECT / 'evidence/thermal-touch-v1/compute-authorization.json'


class BoundedRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temp.name) / 'prepared'
        with redirect_stdout(StringIO()):
            cls.result = recovery.prepare(SOURCE, cls.folder, FAILURE, CHUNKS, AUTH)
        cls.plan = recovery.load(cls.folder / 'recovery-accounting.json')
        cls.units = recovery.load(cls.folder / 'units.json')
        cls.baseline = recovery.load(cls.folder / 'baseline-job.json')
        cls.launch = (cls.folder / 'colab-launch.py').read_text()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def journal(self, attempts=(1,)):
        rows = [{'event': 'attempt_started', 'segment_id': u['id'], 'attempt': n}
                for u in self.units for n in attempts]
        return ('\n'.join(json.dumps(r) for r in rows) + '\n').encode()

    def test_disabled_notebook_and_unauthorized_run_do_not_import_colab_or_start(self):
        ns = {}
        with redirect_stdout(StringIO()) as result:
            exec(compile(self.launch, 'disabled recovery', 'exec'), ns)
        self.assertIn('THERMAL_RECOVERY_DISABLED', result.getvalue())
        self.assertFalse(ns['RUN_THERMAL_TOUCH_RECOVERY'])
        self.assertFalse(ns['EXISTING_COMPUTE_ALLOWED'])
        self.assertFalse(ns['FREE_RUNTIME_CONFIRMED'])
        self.assertNotIn('ROOT', ns)
        enabled = self.launch.replace('RUN_THERMAL_TOUCH_RECOVERY = False', 'RUN_THERMAL_TOUCH_RECOVERY = True', 1)
        with self.assertRaisesRegex(RuntimeError, 'compute authorization'):
            exec(compile(enabled, 'unauthorized recovery', 'exec'), {})

    def test_worker_recipe_asr_pins_and_fresh_two_attempt_job_are_preserved(self):
        tree = ast.parse(self.launch)
        encoded = next(n.args[0].value for n in ast.walk(tree) if isinstance(n, ast.Call)
                       and isinstance(n.func, ast.Attribute) and n.func.attr == 'b64decode')
        payload = json.loads(base64.b64decode(encoded))
        self.assertEqual(payload['software']['qwen_worker.py'], (PROJECT / 'video_studio/vendor/qwen_worker.py').read_text())
        self.assertEqual(payload['baseline'], self.baseline)
        self.assertEqual(payload['units'], self.units)
        episode = payload['software']['episode.py']
        compile(episode, 'bounded episode adapter', 'exec')
        self.assertIn("'max_attempts':2", episode)
        self.assertNotIn("'max_attempts':3", episode)
        self.assertIn(recovery.RUNTIME_ROOT, episode)
        self.assertIn(recovery.ASR_REVISION, episode)
        self.assertIn('retain_observation(ROOT,OUT)', episode)
        self.assertNotIn('threading.Timer', self.launch)
        self.assertNotIn('runtime.unassign', self.launch)

    def test_cap_counts_historical_and_new_started_including_interrupted(self):
        first = recovery.observation(self.plan, self.journal((1,)))
        self.assertTrue(all(r['combined_known_starts'] == 2 for r in first['units']))
        two = recovery.observation(self.plan, self.journal((1, 2)))
        self.assertTrue(all(r['combined_known_starts'] == 3 for r in two['units']))
        self.assertFalse(two['publication_approved'])
        self.assertEqual(two['new_recording_listening'], 'PENDING')
        # No finished events is deliberate: started but interrupted inference still counts.
        for attempts in ((1, 2, 3), (1, 1), (2,)):
            with self.assertRaises(recovery.RecoveryError):
                recovery.observation(self.plan, self.journal(attempts))
        altered = copy.deepcopy(self.plan)
        altered['units'][0]['known_historical_attempts_started'] = 0
        with self.assertRaises(recovery.RecoveryError):
            recovery.validate_plan(altered)

    def test_history_chunks_and_prepared_source_are_retained_without_fake_observations(self):
        self.assertEqual(self.plan['historical_transfer']['source_archive_sha256'], recovery.PRIOR_ARCHIVE_SHA256)
        self.assertEqual(sum(c['bytes'] for c in self.plan['historical_transfer']['local_chunks']), 1572864)
        self.assertFalse(self.plan['historical_transfer']['full_archive_available_locally'])
        self.assertTrue(all(r['new_attempts_observed'] is None for r in self.plan['units']))
        self.assertEqual((self.folder / 'units.json').read_bytes(), (SOURCE / 'units.json').read_bytes())
        self.assertEqual((self.folder / 'recovery-evidence/prior-transfer-failure.json').read_bytes(), FAILURE.read_bytes())
        for row in self.plan['historical_transfer']['local_chunks']:
            self.assertEqual(recovery.sha(row['path']), row['sha256'])
        with self.assertRaisesRegex(recovery.RecoveryError, 'already exists'):
            recovery.prepare(SOURCE, self.folder, FAILURE, CHUNKS, AUTH)

    def test_fixed_deadline_and_complete_transfer_preflight_are_required_before_files(self):
        source = self.launch.replace('RUN_THERMAL_TOUCH_RECOVERY = False', 'RUN_THERMAL_TOUCH_RECOVERY = True', 1).replace('EXISTING_COMPUTE_ALLOWED = False', 'EXISTING_COMPUTE_ALLOWED = True', 1)
        for ns in ({}, {'THERMAL_RUNTIME_DEADLINE': time.time() - 1, 'thermal_touch_shutdown_guard': object()},
                   {'THERMAL_RUNTIME_DEADLINE': time.time() + 100, 'thermal_touch_shutdown_guard': object()}):
            with self.assertRaisesRegex(RuntimeError, 'deadline|preflight'):
                exec(compile(source, 'preflight-gated recovery', 'exec'), ns)
            self.assertNotIn('ROOT', ns)

    def test_duplicate_live_process_is_refused_and_does_not_extend_deadline(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'runtime'
            root.mkdir()
            (root / 'process.json').write_text(json.dumps({'pid': os.getpid()}))
            source = self.launch.replace(repr(recovery.RUNTIME_ROOT), repr(str(root)), 1).replace('RUN_THERMAL_TOUCH_RECOVERY = False', 'RUN_THERMAL_TOUCH_RECOVERY = True', 1).replace('EXISTING_COMPUTE_ALLOWED = False', 'EXISTING_COMPUTE_ALLOWED = True', 1)
            deadline, guard = time.time() + 120, object()
            ns = {'THERMAL_RUNTIME_DEADLINE': deadline, 'thermal_touch_shutdown_guard': guard,
                  'THERMAL_TRANSFER_PREFLIGHT': {'complete_file_verified_locally': True,
                    'bounded_output_verified': True, 'bytes': recovery.PRIOR_ARCHIVE_BYTES,
                    'sha256': '0' * 64, 'runtime_deadline': deadline}}
            with patch('subprocess.Popen') as launch:
                with self.assertRaisesRegex(RuntimeError, 'Existing process'):
                    exec(compile(source, 'duplicate recovery process', 'exec'), ns)
                launch.assert_not_called()
            self.assertEqual(ns['THERMAL_RUNTIME_DEADLINE'], deadline)
            self.assertIs(ns['thermal_touch_shutdown_guard'], guard)
            self.assertEqual(json.loads((root / 'process.json').read_text()), {'pid': os.getpid()})

    def test_recovery_cannot_assemble_without_retained_count_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'production-v2-recovery'
            root.mkdir()
            with self.assertRaisesRegex(recovery.RecoveryError, 'attempt accounting'):
                recovery.verify_imported(root, self.units, self.baseline)
            recovery.write_new(root / 'recovery-accounting.json', self.plan)
            (root / 'narration-transfer').mkdir()
            recovery.write_new(root / 'narration-transfer/recovery-observation.json', {})
            with self.assertRaisesRegex(recovery.RecoveryError, 'incomplete'):
                recovery.verify_imported(root, self.units, self.baseline)

    def test_changed_observation_or_unbudgeted_metadata_cannot_be_accepted(self):
        journal = self.journal((1,))
        actual = recovery.observation(self.plan, journal)
        job = {'max_attempts': 2, 'segments': [{'segment_id': u['id'], 'text': u['text'], 'speaker': 'Ryan',
                'output_path': f"{recovery.RUNTIME_ROOT}/result/raw/{u['id']}.wav", 'seed': 123, 'instruct': 'original'} for u in self.units]}
        metadata = {u['id']: {'selected_attempt': 1, 'attempts': [{'attempt': 1}],
                    'settings': {'seed_base': 123, 'instruct': 'original'}} for u in self.units}
        recovery.validate_observation(actual, self.plan, journal, job, self.units, metadata)
        wrong = copy.deepcopy(actual)
        wrong['units'][0]['combined_known_starts'] = 1
        with self.assertRaises(recovery.RecoveryError):
            recovery.validate_observation(wrong, self.plan, journal, job, self.units, metadata)
        job['max_attempts'] = 3
        with self.assertRaisesRegex(recovery.RecoveryError, 'budget'):
            recovery.validate_observation(actual, self.plan, journal, job, self.units, metadata)


if __name__ == '__main__':
    unittest.main()
