"""Batch control tests use local synthetic adapters, never production media/models."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from scripts import earnalism_orchestrator as engine


class BatchTests(unittest.TestCase):
    def test_science_voice_direction_remains_separate_from_topic(self):
        request = engine.parse_instruction(
            "Build the GO LIVE ready audiovisual for EverydayScience topic - Metal Rust using The Earnalism Voice")
        self.assertEqual(request["title"], "Metal Rust")
        self.assertEqual(request["requested_voice"], "TheEarnalismVoice")
        self.assertFalse(request["publication_requested"])

    def test_rust_contract_is_part_of_visual_software_identity(self):
        files = engine._software("visuals", {"kind":"science-animation", "science":"metal-rust"})
        self.assertIn("skills/earnalism-video/software/metal_rust/contract.json", files)
        self.assertIn("skills/earnalism-video/software/metal_rust/index.tsx", files)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name).resolve()
        self.projects = [self.project('first', 'First Book'), self.project('second', 'Second Book')]
        self.registry = self.workspace / 'projects.json'
        self.write(self.registry, {'schema': engine.REGISTRY_SCHEMA, 'projects': self.projects})
        self.input = self.workspace / 'batch.json'
        self.value = {'schema': engine.BATCH_SCHEMA, 'id': 'two-book-batch', 'items': [
            {'id': p['id'] + '-item', 'instruction': 'Build English book - ' + p['title']}
            for p in self.projects]}
        self.write(self.input, self.value)
        self.history = patch.object(engine, '_history', return_value=None)
        self.history.start()
        self.addCleanup(self.history.stop)
        self.addCleanup(self.temp.cleanup)

    @staticmethod
    def project(identity, title):
        return {'id': identity, 'kind': 'book', 'title': title, 'language': 'en',
                'stages': {'source': {'kind': 'software-only-test'}}}

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        return {'path': str(path), 'sha256': engine._sha(path)}

    def run_batch(self, **kwargs):
        return engine.batch(self.input, self.workspace, **kwargs)

    def runtime_files(self, **changes):
        started = time.time() - 1
        context = {'shutdown_guard_armed': True, 'allocation_started_at': started,
                   'original_deadline_epoch': started + 60}
        mapping = {}
        for project in self.projects:
            value = {'schema': engine.RUNTIME_SCHEMA, 'project_id': project['id'],
                     'owner_authorized': True, 'scope_ref': 'synthetic-scope-' + project['id'],
                     'evidence_ref': 'SOFTWARE FIXTURE ONLY; NOT ACTUAL AUTHORITY',
                     'purchases_allowed': False, 'publication_allowed': False,
                     'allocation_started_at': started, 'original_deadline_epoch': started + 60,
                     'observed_units_per_hour': 1, 'approved_compute_units': 1,
                     'free_runtime_confirmed': False, 'max_model_stage_starts': 1}
            value.update(changes)
            mapping[project['id']] = self.write(self.workspace / (project['id'] + '-runtime.json'), value)
        path = self.workspace / 'authorities.json'
        self.write(path, mapping)
        return path, mapping, context

    def test_preparation_runs_parallel_plans_and_returns_only_compact_artifact_refs(self):
        barrier = threading.Barrier(2)
        marker = 'PRIVATE_MANUSCRIPT_MARKER_' * 5000
        threads = set()
        def plan(instruction, workspace, registry_path):
            threads.add(threading.current_thread().name)
            barrier.wait(timeout=5)
            selected = self.projects[0] if 'First Book' in instruction else self.projects[1]
            return {'project': selected, 'state': 'MISSING_INPUT', 'blockers': ['missing narration'],
                    'registry_sha256': engine._sha(self.registry),
                    'discovery': {'whole_manuscript': marker}, 'stages': {'private': marker}}
        with patch.object(engine, 'plan', side_effect=plan), patch.object(engine, 'run') as run, \
             patch.object(engine, '_runtime') as runtime:
            report = self.run_batch(workers=2)
        run.assert_not_called()
        runtime.assert_not_called()
        self.assertEqual(len(threads), 2)
        self.assertNotIn(marker[:50], json.dumps(report))
        self.assertEqual(report['codex_api_calls_by_controller'], 0)
        self.assertEqual(report['model_dispatch'], 'NOT_REQUESTED')
        self.assertFalse(report['production_ready'])
        for item in report['items']:
            self.assertNotIn('stages', item)
            plan_path = Path(item['plan']['path'])
            self.assertIn(marker, plan_path.read_text())
            self.assertEqual(item['plan']['sha256'], engine._sha(plan_path))
            self.assertTrue(plan_path.is_relative_to(self.workspace / 'batches'))

    def test_duplicates_and_malformed_later_item_fail_before_any_work(self):
        cases = []
        duplicate_item = copy.deepcopy(self.value)
        duplicate_item['items'][1]['id'] = duplicate_item['items'][0]['id']
        cases.append(duplicate_item)
        duplicate_project = copy.deepcopy(self.value)
        duplicate_project['items'][1]['instruction'] = 'Build English book - First Book'
        cases.append(duplicate_project)
        malformed_later = copy.deepcopy(self.value)
        malformed_later['items'][1]['instruction'] = 'guess what I want'
        cases.append(malformed_later)
        injected = copy.deepcopy(self.value)
        injected['items'][1]['command'] = 'not-supported'
        cases.append(injected)
        next_topic = copy.deepcopy(self.value)
        next_topic['items'][1]['instruction'] = 'Build next EverydayScience topic'
        cases.append(next_topic)
        for value in cases:
            self.write(self.input, value)
            with self.subTest(value=value), patch.object(engine, 'plan') as plan, \
                 patch.object(engine, 'run') as run, self.assertRaises(ValueError):
                self.run_batch(execute=True)
            plan.assert_not_called()
            run.assert_not_called()
            self.assertFalse((self.workspace / 'batches').exists())

    def test_distinct_aliases_cannot_dispatch_same_registered_project_twice(self):
        self.projects[0]['aliases'] = ['Alias First']
        self.write(self.registry, {'schema': engine.REGISTRY_SCHEMA, 'projects': self.projects})
        self.value['items'][1]['instruction'] = 'Build English book - Alias First'
        self.write(self.input, self.value)
        with patch.object(engine, 'run') as run, self.assertRaisesRegex(ValueError, 'duplicate selected project'):
            self.run_batch(execute=True)
        run.assert_not_called()

    def test_missing_and_broken_item_plans_do_not_block_independent_item(self):
        self.value['items'].append({'id': 'missing-item', 'instruction': 'Build English book - Absent'})
        self.write(self.input, self.value)
        original = engine.plan
        def plan(instruction, *args):
            if 'First Book' in instruction:
                raise ValueError('damaged private per-title history')
            return original(instruction, *args)
        def run(instruction, *args, **kwargs):
            return {'project_id': 'second', 'state': 'PRIVATE_REVIEW_OR_INPUT_REQUIRED',
                    'blockers': ['missing stage input: narration'], 'executed_stages': ['source']}
        with patch.object(engine, 'plan', side_effect=plan), patch.object(engine, 'run', side_effect=run) as dispatch:
            report = self.run_batch(execute=True)
        self.assertEqual(dispatch.call_count, 1)
        self.assertEqual(report['items'][0]['state'], 'PRIVATE_INPUT_REQUIRED')
        self.assertEqual(report['items'][1]['executed_stage_count'], 1)
        self.assertIsNone(report['items'][2]['project_id'])
        self.assertTrue(all(Path(x['result']['path']).is_file() for x in report['items']))

    def test_execution_reuses_real_run_global_lock_serial_resume_and_stage_holds(self):
        calls = []
        def adapter(stage, spec, context):
            # Verify that run's pre-existing global lock is still held here.
            with self.assertRaisesRegex(ValueError, 'another notebook'):
                with engine._lock(self.workspace):
                    self.fail('a second writer acquired the existing global lock')
            calls.append(context['project_id'])
            output = Path(context['output_dir']) / 'test.txt'
            output.parent.mkdir(parents=True, exist_ok=False)
            output.write_text('SYNTHETIC LOCAL CONTROL OUTPUT ONLY')
            return {'status': 'COMPLETE', 'artifacts': [{'path': str(output), 'sha256': engine._sha(output)}],
                    'blockers': [], 'details': {}}
        with patch.object(engine, '_dispatch', side_effect=adapter):
            first = self.run_batch(execute=True, workers=4)
            second = self.run_batch(execute=True, workers=4)
        self.assertEqual(calls, ['first', 'second'])
        self.assertTrue(all(x['executed_stage_count'] == 1 for x in first['items']))
        self.assertTrue(all(x['reused_stage_count'] == 1 for x in second['items']))
        self.assertTrue(all('missing stage input: narration' in x['first_blocker'] for x in first['items']))
        self.assertNotEqual(first['report_path'], second['report_path'])
        self.assertEqual(first['input_sha256'], second['input_sha256'])
        self.assertTrue(Path(first['report_path']).is_file())
        self.assertFalse(first['publication_performed'])

    def test_unknown_attempt_survives_batch_resume_without_replay(self):
        calls = []
        def adapter(stage, spec, context):
            calls.append(context['project_id'])
            if context['project_id'] == 'first':
                raise RuntimeError('interrupted synthetic dispatch, outcome unknown')
            output = Path(context['output_dir']) / 'ok.txt'
            output.parent.mkdir(parents=True, exist_ok=False)
            output.write_text('SYNTHETIC CONTROL')
            return {'status': 'COMPLETE', 'artifacts': [{'path': str(output), 'sha256': engine._sha(output)}],
                    'blockers': [], 'details': {}}
        with patch.object(engine, '_dispatch', side_effect=adapter):
            self.run_batch(execute=True)
            second = self.run_batch(execute=True)
        self.assertEqual(calls, ['first', 'second'])
        self.assertIn('FAILED_OR_UNKNOWN_NO_REPLAY', second['items'][0]['first_blocker'])
        self.assertEqual(second['items'][1]['reused_stage_count'], 1)

    def test_all_mapped_runtime_scopes_validate_before_first_dispatch(self):
        path, mapping, context = self.runtime_files()
        bad = Path(mapping['second']['path'])
        data = engine._load(bad)
        data['original_deadline_epoch'] += 5
        mapping['second'] = self.write(bad, data)
        self.write(path, mapping)
        with patch.object(engine, 'run') as run, patch.object(engine, 'plan') as plan, \
             self.assertRaisesRegex(ValueError, 'original shutdown timer'):
            self.run_batch(execute=True, authorities_path=path, runtime_context=context)
        run.assert_not_called()
        plan.assert_not_called()
        self.assertFalse((self.workspace / 'batches').exists())

    def test_same_clock_cannot_fan_out_different_compute_caps_or_scope_identity(self):
        for changed in ({'approved_compute_units': 2}, {'scope_ref': 'synthetic-scope-first'}):
            path, mapping, context = self.runtime_files()
            target = Path(mapping['second']['path'])
            data = engine._load(target)
            data.update(changed)
            mapping['second'] = self.write(target, data)
            self.write(path, mapping)
            with self.subTest(changed=changed), patch.object(engine, 'run') as run, self.assertRaises(ValueError):
                self.run_batch(execute=True, authorities_path=path, runtime_context=context)
            run.assert_not_called()

    def test_exact_project_authorities_and_original_context_forward_without_reset(self):
        path, mapping, context = self.runtime_files()
        original_bytes = {key: Path(value['path']).read_bytes() for key, value in mapping.items()}
        calls = []
        def run(instruction, workspace, registry_path, **kwargs):
            calls.append(kwargs)
            return {'state': 'HELD', 'blockers': ['synthetic hold'], 'production_ready': False}
        with patch.object(engine, 'run', side_effect=run):
            self.run_batch(execute=True, authorities_path=path, runtime_context=context)
        self.assertEqual([x['authority_path'] for x in calls], [Path(mapping[p['id']]['path']) for p in self.projects])
        self.assertTrue(all(x['runtime_context'] is context for x in calls))
        self.assertEqual(original_bytes, {key: Path(value['path']).read_bytes() for key, value in mapping.items()})
        self.assertFalse((self.workspace / '.orchestrator' / 'authorities').exists())

    def test_changed_bound_authority_after_first_item_holds_second_without_dispatch(self):
        path, mapping, context = self.runtime_files()
        def run(*args, **kwargs):
            Path(mapping['second']['path']).write_text('{}')
            return {'state': 'HELD', 'blockers': ['synthetic first-item hold']}
        with patch.object(engine, 'run', side_effect=run) as run:
            report = self.run_batch(execute=True, authorities_path=path, runtime_context=context)
        self.assertEqual(run.call_count, 1)
        self.assertIn('missing or changed input', report['items'][1]['first_blocker'])
        self.assertEqual(report['items'][1]['state'], 'PRIVATE_EXECUTION_HELD_OR_UNKNOWN')

    def test_mapping_cannot_target_unselected_project_and_preparation_never_arms_runtime(self):
        path, mapping, _ = self.runtime_files()
        mapping['third'] = mapping['first']
        self.write(path, mapping)
        with patch.object(engine, 'run') as run, self.assertRaisesRegex(ValueError, 'only selected'):
            self.run_batch(execute=True, authorities_path=path)
        run.assert_not_called()
        del mapping['third']
        self.write(path, mapping)
        with patch.object(engine, '_runtime') as runtime:
            report = self.run_batch(authorities_path=path)
        runtime.assert_not_called()
        self.assertEqual(report['model_dispatch'], 'NOT_REQUESTED')

    def test_registry_changes_get_new_fingerprint_and_all_old_reports_remain(self):
        first = self.run_batch()
        self.projects[0]['title'] = 'Renamed Book'
        self.write(self.registry, {'schema': engine.REGISTRY_SCHEMA, 'projects': self.projects})
        second = self.run_batch()
        self.assertNotEqual(first['input_sha256'], second['input_sha256'])
        self.assertTrue(Path(first['report_path']).is_file())
        self.assertIsNone(second['items'][0]['project_id'])

    def test_cli_preparation_output_is_compact_and_workers_are_bounded(self):
        for workers in (0, 5, True, 1.5):
            with self.subTest(workers=workers), self.assertRaises(ValueError):
                self.run_batch(workers=workers)
        target = self.workspace / 'selected-summary.json'
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(engine, 'run') as run:
            code = engine.main(['batch', '--input', str(self.input), '--workspace', str(self.workspace),
                                '--workers', '2', '--output', str(target)])
        run.assert_not_called()
        report = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(report, engine._load(target))
        self.assertNotIn('instruction', output.getvalue())
        self.assertTrue(all('project' not in item for item in report['items']))

    def test_batch_report_path_cannot_follow_existing_symlink_outside_workspace(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.workspace / 'batches').symlink_to(Path(outside), target_is_directory=True)
            with patch.object(engine, 'plan') as plan, self.assertRaisesRegex(ValueError, 'escapes'):
                self.run_batch()
            plan.assert_not_called()
            self.assertEqual(list(Path(outside).iterdir()), [])

    def changed_registry_plans(self, *, restore, restore_before_plan_hash=False):
        original_plan = engine.plan
        original_registry = self.registry.read_bytes()
        admitted_sha = engine._sha(self.registry)
        first_planned, second_planned = threading.Event(), threading.Event()
        def plan(instruction, *args):
            if 'First Book' in instruction:
                result = original_plan(instruction, *args)
                first_planned.set()
                self.assertTrue(second_planned.wait(timeout=5))
                return result
            self.assertTrue(first_planned.wait(timeout=5))
            changed = copy.deepcopy(self.projects)
            changed[1]['stages']['source']['recipe'] = 'changed recipe; same project identities'
            self.write(self.registry, {'schema': engine.REGISTRY_SCHEMA, 'projects': changed})
            result = original_plan(instruction, *args)
            if restore:
                self.registry.write_bytes(original_registry)
            second_planned.set()
            return result
        def history(request, project, workspace):
            if restore_before_plan_hash and project and project['id'] == 'second':
                # The real single-title planner hashes its registry after
                # history discovery, so exercise a restore within that window.
                self.registry.write_bytes(original_registry)
            return None
        with patch.object(engine, '_history', side_effect=history), \
             patch.object(engine, 'plan', side_effect=plan) as plans, patch.object(engine, 'run') as run:
            report = self.run_batch(workers=2, execute=True)
        run.assert_not_called()
        self.assertEqual(plans.call_count, 2)  # No automatic replan.
        self.assertEqual(report['state'], 'HELD_CHANGED_INPUT')
        self.assertFalse(report['production_ready'])
        self.assertEqual(report['model_dispatch'], 'NOT_DISPATCHED_CHANGED_INPUT')
        self.assertTrue(all(x['state'] == 'HELD_CHANGED_INPUT' for x in report['items']))
        actual = [engine._load(Path(x['plan']['path'])) for x in report['items']]
        self.assertEqual(actual[0]['registry_sha256'], admitted_sha)
        if restore_before_plan_hash:
            self.assertEqual(actual[1]['registry_sha256'], admitted_sha)
        else:
            self.assertNotEqual(actual[1]['registry_sha256'], admitted_sha)
        self.assertEqual([x['project']['id'] for x in actual], ['first', 'second'])
        self.assertNotIn('recipe', actual[0]['project']['stages']['source'])
        self.assertEqual(actual[1]['project']['stages']['source']['recipe'],
                         'changed recipe; same project identities')
        self.assertTrue(all(Path(x['result']['path']).name == 'held-input.json' for x in report['items']))
        return report, admitted_sha

    def test_persistent_registry_recipe_change_holds_entire_batch_and_preserves_actual_plans(self):
        previous = self.run_batch()
        previous_path = Path(previous['report_path'])
        previous_bytes = previous_path.read_bytes()
        report, admitted_sha = self.changed_registry_plans(restore=False)
        self.assertEqual(previous_bytes, previous_path.read_bytes())
        self.assertNotEqual(previous['report_path'], report['report_path'])
        self.assertEqual(previous['input_sha256'], report['input_sha256'])
        coherence = engine._load(Path(report['input_coherence']['path']))
        self.assertNotEqual(coherence['final']['registry_sha256'], admitted_sha)
        self.assertIn('second-item', coherence['changed_items'])

    def test_restored_registry_still_holds_mixed_plan_hashes_without_dispatch_or_replan(self):
        report, admitted_sha = self.changed_registry_plans(restore=True)
        self.assertEqual(engine._sha(self.registry), admitted_sha)
        coherence = engine._load(Path(report['input_coherence']['path']))
        self.assertEqual(coherence['final'], coherence['expected'])
        # All before/after observations see restored original bytes. Only the
        # actual second plan's own binding exposes the transient mixed recipe.
        self.assertTrue(all(x['before'] == coherence['expected'] and x['after'] == coherence['expected']
                            for x in coherence['items']))
        self.assertEqual(coherence['changed_items'], ['second-item'])
        held_bytes = Path(report['report_path']).read_bytes()
        explicit_resume = self.run_batch()
        self.assertNotEqual(explicit_resume['state'], 'HELD_CHANGED_INPUT')
        self.assertEqual(held_bytes, Path(report['report_path']).read_bytes())

    def test_recipe_change_restored_inside_real_plan_cannot_hide_behind_late_registry_hash(self):
        report, _ = self.changed_registry_plans(restore=True, restore_before_plan_hash=True)
        coherence = engine._load(Path(report['input_coherence']['path']))
        self.assertEqual(coherence['final'], coherence['expected'])
        self.assertTrue(all(x['plan_registry_sha256'] == coherence['expected']['registry_sha256']
                            for x in coherence['items']))
        self.assertEqual([x['project_matches_admission'] for x in coherence['items']], [True, False])
        self.assertEqual(coherence['changed_items'], ['second-item'])


if __name__ == '__main__':
    unittest.main()
