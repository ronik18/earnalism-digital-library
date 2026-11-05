"""Single-control trials retain history and cannot certify audible quality."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_voice_experiment as fixtures
from audio_derivation import sha
from sampling_experiment import audit_sampling_experiment
from qwen_worker import GENERATION_DEFAULTS, VALIDATION_DEFAULTS


class SamplingExperimentTests(unittest.TestCase):
    def unit(self, folder, text, seed, value, candidate=False):
        self.fixture = fixtures.VoiceExperimentTests()
        meta = self.fixture.make_take(folder, 'A connected original documentary direction.', value)
        meta['settings'].update(text=text, seed_base=seed,
            generation={**GENERATION_DEFAULTS, 'temperature': .85},
            validation=copy.deepcopy(VALIDATION_DEFAULTS))
        if candidate:
            meta['settings']['generation']['subtalker_dosample'] = False
        meta.update(selected_seed=seed, interrupted_attempt_numbers=[], attempts=[{
            'attempt': 1, 'seed': seed, 'status': 'PASS', 'effective_key': meta['effective_key']}])
        self.fixture.save(folder, meta)
        self.write(folder / 'episode.json', {'scenes': [{'id': 's06', 'text': text}]})
        (folder / 'alignment').mkdir()
        words = [{'word': word, 'start': index*.1, 'end': (index+1)*.1}
                 for index, word in enumerate(text.split())]
        self.write(folder / 'alignment/s06.json', {'audio_sha256': meta['wav_sha256'],
            'recognized': text, 'word_times': words, 'unresolved_asr_edits': []})
        if candidate:
            (folder / 'config').mkdir()
            self.write(folder / 'config/qwen-job.json', {
                'max_attempts': 1, 'model_id': meta['provenance']['model_id'],
                'model_revision': meta['provenance']['model_revision'],
                'dtype': meta['settings']['dtype'], 'attention': meta['settings']['attention'],
                'device': meta['provenance']['hardware']['device'],
                'generation': {'temperature': .85, 'subtalker_dosample': False},
                'segments': [{'segment_id': 's06', 'text': text,
                    'instruct': meta['settings']['instruct'], 'speaker': 'Ryan', 'seed': seed}]})
        return meta

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value))

    @staticmethod
    def read(path):
        return json.loads(path.read_text())

    def setup(self, root, standalone=3, seed=918273):
        text = 'The idea changes when we connect the complete explanation.'
        baseline = root / 'baseline'
        candidate = root / 'candidate'
        self.unit(baseline, text, seed, 10)
        previous = [baseline]
        for index in range(1, standalone):
            folder = root / ('old-' + str(index))
            self.unit(folder, text, seed, 10 + index)
            previous.append(folder)
        context = root / 'old-context'
        self.unit(context, 'A genuine earlier thought. ' + text + ' A later thought follows.', seed, 30)
        previous.append(context)
        self.unit(candidate, text, seed, 50, True)
        rows = []
        for folder in previous:
            meta = self.read(folder / 'raw/s06.wav.json')
            rows.append({'folder': str(folder), 'text': meta['settings']['text'],
                'wav_sha256': meta['wav_sha256'], 'metadata_sha256': sha(folder / 'raw/s06.wav.json'),
                'effective_key': meta['effective_key'], 'actual_selected_seed': meta['selected_seed']})
        history = root / 'history.json'
        self.write(history, {'prior_generations': rows,
            'closed_experiments': {'directions': {'used': standalone, 'limit': standalone},
                                   'context': {'used': 1, 'limit': 1, 'decision': 'REJECTED'}},
            'prior_middle_containing_generations': len(rows), 'new_trial_attempt_limit': 1,
            'new_exact_standalone_generation_index': standalone + 1,
            'new_middle_containing_generation_index': len(rows) + 1,
            'no_prior_counters_reset': True, 'old_effective_keys_remain_closed': True,
            'stop_after_this_generation': True,
            'only_changed_control': {'name': 'subtalker_dosample', 'baseline': True, 'candidate': False}})
        return baseline, candidate, history

    def audit(self, baseline, candidate, history, **kwargs):
        return audit_sampling_experiment(baseline, candidate, 's06', history_path=history,
                                         history_sha256=sha(history), **kwargs)

    def change(self, folder, subpath, callback):
        path = folder / subpath
        value = self.read(path)
        callback(value)
        self.write(path, value)

    def test_valid_one_boolean_trial_preserves_history_without_promoting(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate, history = self.setup(Path(directory))
            before = {p: sha(p) for p in [history, baseline/'raw/s06.wav', candidate/'raw/s06.wav']}
            result = self.audit(baseline, candidate, history)
            self.assertTrue(result['recorded_single_control'], result)
            self.assertEqual(result['history']['previous_exact_standalone_generations'], 3)
            self.assertEqual(result['history']['new_middle_containing_generation_index'], 5)
            self.assertEqual(result['execution']['actual_attempts'], 1)
            self.assertEqual(result['history']['record'], self.read(history))
            self.assertEqual(result['listening_review'], 'PENDING')
            self.assertEqual(result['naturalness'], 'NOT_ESTABLISHED')
            self.assertEqual(result['causal_isolation'], 'NOT_ESTABLISHED')
            self.assertIn('shared RNG', result['note'])
            for key in ['listening_approval', 'video_integration_approval', 'publication_approval']:
                self.assertFalse(result[key])
            self.assertEqual(before, {p: sha(p) for p in before})

    def test_other_seed_and_closed_history_counts_are_derived(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate, history = self.setup(Path(directory), standalone=2, seed=41)
            result = self.audit(baseline, candidate, history)
            self.assertTrue(result['recorded_single_control'], result)
            self.assertEqual(result['control']['actual_selected_seed'], 41)
            self.assertEqual(result['history']['previous_exact_standalone_generations'], 2)
            self.assertEqual(result['history']['new_middle_containing_generation_index'], 4)

    def test_combined_prompt_context_or_primary_sampling_changes_fail(self):
        changes = [lambda m: m['settings'].update(instruct='Another direction'),
                   lambda m: m['settings'].update(text='Another complete context. ' + m['settings']['text']),
                   lambda m: m['settings']['generation'].update(temperature=.7),
                   lambda m: m['settings']['generation'].update(do_sample=False),
                   lambda m: m['settings']['validation'].update(min_rms=.00001),
                   lambda m: m.update(selected_seed=42)]
        for callback in changes:
            with self.subTest(callback=callback), tempfile.TemporaryDirectory() as directory:
                baseline, candidate, history = self.setup(Path(directory))
                self.change(candidate, 'raw/s06.wav.json', callback)
                self.assertFalse(self.audit(baseline, candidate, history)['recorded_single_control'])

    def test_pinned_execution_changes_and_missing_provenance_fail(self):
        for mode in ['model', 'hardware', 'package', 'missing']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                baseline, candidate, history = self.setup(Path(directory))
                meta = self.read(candidate/'raw/s06.wav.json')
                if mode == 'model': meta['provenance']['model_revision'] = 'f'*40
                if mode == 'hardware': meta['provenance']['hardware']['name'] = 'Another GPU'
                if mode == 'package': meta['provenance']['environment']['packages']['torch'] = 'another version'
                if mode == 'missing': del meta['provenance']['environment']['qwen_package_source_sha256']
                if mode != 'missing': self.fixture.bind(meta)
                self.write(candidate/'raw/s06.wav.json', meta)
                self.assertFalse(self.audit(baseline, candidate, history)['recorded_single_control'])

    def test_second_attempt_interruption_or_larger_job_budget_fails(self):
        for mode in ['attempt2', 'second_selected', 'interrupted', 'budget2', 'attempt_key']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                baseline, candidate, history = self.setup(Path(directory))
                if mode == 'budget2':
                    self.change(candidate, 'config/qwen-job.json', lambda j: j.update(max_attempts=2))
                else:
                    def edit(meta):
                        if mode == 'attempt2': meta['attempts'].append({**meta['attempts'][0], 'attempt': 2})
                        if mode == 'second_selected': meta['selected_attempt'] = 2
                        if mode == 'interrupted': meta['interrupted_attempt_numbers'] = [1]
                        if mode == 'attempt_key': meta['attempts'][0]['effective_key'] = 'wrong key'
                    self.change(candidate, 'raw/s06.wav.json', edit)
                result = self.audit(baseline, candidate, history)
                self.assertFalse(result['recorded_single_control'])
                self.assertIn('candidate.sampling_execution', [x['field'] for x in result['confounds']])

    def test_raw_source_not_derived_or_tampered_and_complete_unit_required(self):
        for mode in ['derivation', 'wave', 'assembly']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                baseline, candidate, history = self.setup(Path(directory))
                if mode == 'derivation': self.change(candidate, 'raw/s06.wav.json', lambda m: m.update(derivation={'kind': 'gain'}))
                if mode == 'wave': (candidate/'raw/s06.wav').write_bytes(b'not the bound raw audio')
                if mode == 'assembly': self.change(candidate, 'episode.json', lambda e: e['scenes'].append(e['scenes'][0]))
                self.assertFalse(self.audit(baseline, candidate, history)['recorded_single_control'])

    def test_fresh_audio_bound_all_word_asr_required(self):
        for mode in ['stale', 'recognized', 'raw_words', 'display_words', 'unresolved', 'missing']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                baseline, candidate, history = self.setup(Path(directory))
                if mode == 'missing': (candidate/'alignment/s06.json').unlink()
                else:
                    def edit(record):
                        if mode == 'stale': record['audio_sha256'] = 'f'*64
                        if mode == 'recognized': record['recognized'] += ' Another word.'
                        if mode == 'raw_words': record['word_times'].pop()
                        if mode == 'display_words': record['display_word_times'] = record['word_times'][:-1]
                        if mode == 'unresolved': record['unresolved_asr_edits'] = [{'tag': 'replace'}]
                    self.change(candidate, 'alignment/s06.json', edit)
                result = self.audit(baseline, candidate, history)
                self.assertFalse(result['recorded_single_control'])
                self.assertTrue(result['execution']['actual_attempts'] == 1)
                self.assertIn('candidate.word_accuracy', [x['field'] for x in result['confounds']])
                self.assertFalse(result['word_accuracy']['all_recognized_words_match'])

    def test_automatic_precision_requires_matching_successful_bound_probe(self):
        for mode in ['valid', 'missing', 'wrong_dtype', 'failed_probe', 'wrong_unit', 'changed_provenance']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                baseline, candidate, history = self.setup(Path(directory))
                # Auto is a request; the probed resolved precision is the control.
                for folder in [baseline, candidate]:
                    meta = self.read(folder/'raw/s06.wav.json')
                    meta['provenance']['hardware']['native_bfloat16'] = False
                    self.fixture.bind(meta)
                    self.write(folder/'raw/s06.wav.json', meta)
                data = self.read(history)
                data['prior_generations'][0]['metadata_sha256'] = sha(baseline/'raw/s06.wav.json')
                self.write(history, data)
                self.change(candidate, 'config/qwen-job.json', lambda j: j.update(dtype='auto'))
                meta = self.read(candidate/'raw/s06.wav.json')
                run = {'provenance': copy.deepcopy(meta['provenance']),
                       'numerical_probe': {'dtype': 'float32', 'audio': {'mechanical_checks': 'PASS'}},
                       'segments': [{'segment_id': 's06', **{k: meta[k] for k in
                           ['effective_key', 'wav_sha256', 'selected_seed', 'selected_attempt', 'status']}}]}
                if mode == 'wrong_dtype': run['numerical_probe']['dtype'] = 'float16'
                if mode == 'failed_probe': run['numerical_probe']['audio']['mechanical_checks'] = 'FAIL'
                if mode == 'wrong_unit': run['segments'][0]['wav_sha256'] = 'f'*64
                if mode == 'changed_provenance': run['provenance']['worker_sha256'] = 'f'*64
                if mode != 'missing':
                    (candidate/'logs').mkdir()
                    self.write(candidate/'logs/qwen-report.json', run)
                result = self.audit(baseline, candidate, history)
                self.assertEqual(result['recorded_single_control'], mode == 'valid', result)
                if mode == 'valid':
                    self.assertEqual(result['execution']['requested_dtype'], 'auto')
                    self.assertEqual(result['execution']['numerical_probe_dtype'], 'float32')

    def test_actual_job_must_request_exact_single_control_and_baseline_performance(self):
        for mode in ['missing_override', 'extra_override', 'prompt', 'seed', 'speaker', 'validation']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                baseline, candidate, history = self.setup(Path(directory))
                def edit(job):
                    if mode == 'missing_override': del job['generation']['subtalker_dosample']
                    if mode == 'extra_override': job['generation']['top_k'] = 20
                    if mode == 'prompt': job['segments'][0]['instruct'] = 'A changed direction'
                    if mode == 'seed': job['segments'][0]['seed'] = 4
                    if mode == 'speaker': job['segments'][0]['speaker'] = 'Another speaker'
                    if mode == 'validation': job['validation'] = {'min_rms': .00001}
                self.change(candidate, 'config/qwen-job.json', edit)
                self.assertFalse(self.audit(baseline, candidate, history)['recorded_single_control'])

    def test_bound_history_change_counter_reset_or_reopened_key_fails(self):
        for mode in ['hash', 'counter', 'scope', 'flag', 'prior_binding', 'duplicate', 'reopen']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                baseline, candidate, history = self.setup(Path(directory))
                original_digest = sha(history)
                data = self.read(history)
                if mode == 'hash': data['unrelated_note'] = 'changed after binding'
                if mode == 'counter': data['new_middle_containing_generation_index'] = 1
                if mode == 'scope': data['closed_experiments']['directions']['used'] = 0
                if mode == 'flag': data['no_prior_counters_reset'] = False
                if mode == 'prior_binding': data['prior_generations'][1]['metadata_sha256'] = 'f'*64
                if mode == 'duplicate': data['prior_generations'][1] = data['prior_generations'][0]
                self.write(history, data)
                if mode == 'reopen':
                    prior_key = data['prior_generations'][0]['effective_key']
                    def edit(meta):
                        meta['effective_key'] = prior_key
                        meta['attempts'][0]['effective_key'] = prior_key
                    self.change(candidate, 'raw/s06.wav.json', edit)
                result = audit_sampling_experiment(baseline, candidate, 's06', history_path=history,
                    history_sha256=original_digest if mode == 'hash' else sha(history))
                self.assertFalse(result['recorded_single_control'])

    def test_unsupported_control_wrong_bool_type_and_unchanged_value_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline, candidate, history = self.setup(Path(directory))
            for field, value in [('temperature', .7), ('instruct', 'new'), ('subtalker_dosample', 0),
                                 ('subtalker_temperature', float('nan'))]:
                with self.subTest(field=field), self.assertRaises(ValueError):
                    self.audit(baseline, candidate, history, expected_field=field, expected_value=value)
            self.assertFalse(self.audit(baseline, candidate, history, expected_value=True)['recorded_single_control'])


if __name__ == '__main__':
    unittest.main()
