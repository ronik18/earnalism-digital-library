"""Recorded-control comparisons detect confounds without approving a voice."""
import copy
import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audio_derivation import sha
from voice_experiment import audit_instruction_only


class VoiceExperimentTests(unittest.TestCase):
    def make_take(self, folder, instruction='control', value=10):
        (folder / 'raw').mkdir(parents=True)
        wav = folder / 'raw/s06.wav'
        with wave.open(str(wav), 'wb') as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(24000)
            output.writeframes(struct.pack('<h', value) * 240)
        text = 'One complete thought keeps the speaker connected.'
        (folder / 'episode.json').write_text(json.dumps({'scenes': [{'id': 's06', 'text': text}]}))
        environment = {'python': '3.12.15', 'platform': 'fixture-linux',
            'executable': str(folder / 'venv/python'), 'packages': {'qwen-tts': '0.1.1', 'torch': '2.8.0'},
            'qwen_package_source_sha256': 'c' * 64, 'torch_cuda_version': '12.6', 'torch_cudnn_version': 91002}
        provenance = {'model_id': 'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice',
            'model_revision': 'a' * 40, 'model_path': str(folder / 'model'),
            'snapshot': {'manifest_sha256': 'b' * 64, 'files': [{'path': 'config.json', 'sha256': 'e' * 64}]},
            'worker_sha256': 'd' * 64, 'environment': environment,
            'hardware': {'name': 'Tesla T4', 'device': 'cuda:0'}, 'dtype': 'float32', 'attention': 'eager'}
        settings = {'text': text, 'instruct': instruction, 'speaker': 'Ryan', 'language': 'English',
            'seed_base': 20261028, 'source_cache_key': folder.name, 'segment_id': 's06',
            'generation': {'temperature': .85, 'do_sample': True}, 'validation': {'max_peak': 1.0},
            'dtype': 'float32', 'attention': 'eager', 'non_streaming_mode': True,
            'batch_size': 1, 'wav_subtype': 'PCM_16'}
        meta = {'status': 'GENERATED_REQUIRES_REVIEW', 'wav_sha256': sha(wav),
            'selected_seed': 20261028, 'selected_attempt': 1, 'settings': settings,
            'created_at': folder.name, 'output_path': str(wav), 'effective_key': folder.name,
            'audio': {'mechanical_checks': 'PASS', 'sample_rate': 24000}, 'provenance': provenance}
        self.bind(meta)
        self.save(folder, meta)
        return meta

    def bind(self, meta):
        p = meta['provenance']; environment = p['environment']
        binding = {key: copy.deepcopy(p[key]) for key in ('model_id', 'model_revision', 'hardware', 'worker_sha256')}
        binding['snapshot_sha256'] = p['snapshot']['manifest_sha256']
        binding.update({key: copy.deepcopy(environment[key]) for key in
            ('python', 'packages', 'qwen_package_source_sha256', 'torch_cuda_version', 'torch_cudnn_version')})
        meta['settings']['provenance_binding'] = binding

    def save(self, folder, meta):
        (folder / 'raw/s06.wav.json').write_text(json.dumps(meta))

    def pair(self, root):
        control, candidate = root / 'control', root / 'candidate'
        self.make_take(control)
        meta = self.make_take(candidate, 'a different direction', 20)
        return control, candidate, meta

    def test_matching_recorded_controls_allow_run_details_but_never_approve_listening(self):
        with tempfile.TemporaryDirectory() as directory:
            control, candidate, _ = self.pair(Path(directory))
            result = audit_instruction_only(control, candidate, 's06')
            self.assertTrue(result['instruction_only'])
            self.assertEqual(result['confounds'], [])
            self.assertEqual(result['listening_review'], 'PENDING')
            self.assertEqual(result['causal_isolation'], 'NOT_ESTABLISHED')
            self.assertNotEqual(result['control']['wav_sha256'], result['candidate']['wav_sha256'])

    def test_actual_selected_seed_difference_is_caught_even_with_same_seed_base(self):
        with tempfile.TemporaryDirectory() as directory:
            control, candidate, meta = self.pair(Path(directory))
            meta['selected_seed'] += 1
            self.save(candidate, meta)
            result = audit_instruction_only(control, candidate, 's06')
            self.assertFalse(result['instruction_only'])
            self.assertIn('selected_seed', [row['field'] for row in result['confounds']])

    def test_same_words_with_changed_punctuation_are_a_recorded_input_confound(self):
        with tempfile.TemporaryDirectory() as directory:
            control, candidate, meta = self.pair(Path(directory))
            meta['settings']['text'] = meta['settings']['text'].replace('thought', 'thought,')
            self.save(candidate, meta)
            (candidate / 'episode.json').write_text(json.dumps({'scenes': [{'id': 's06', 'text': meta['settings']['text']}]}))
            result = audit_instruction_only(control, candidate, 's06')
            self.assertFalse(result['instruction_only'])
            self.assertIn('settings.text', [row['field'] for row in result['confounds']])

    def test_generation_execution_code_and_package_differences_are_named(self):
        cases = [
            (('settings', 'generation', 'temperature'), .7, 'settings.generation.temperature'),
            (('settings', 'non_streaming_mode'), False, 'settings.non_streaming_mode'),
            (('provenance', 'model_revision'), 'f' * 40, 'provenance.model_revision'),
            (('provenance', 'worker_sha256'), 'f' * 64, 'provenance.worker_sha256'),
            (('provenance', 'environment', 'packages', 'torch'), '2.9.0', 'provenance.environment.packages.torch'),
            (('provenance', 'environment', 'qwen_package_source_sha256'), 'f' * 64, 'provenance.environment.qwen_package_source_sha256'),
            (('provenance', 'hardware', 'name'), 'different GPU', 'provenance.hardware.name')]
        for path, value, field in cases:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                control, candidate, meta = self.pair(Path(directory))
                target = meta
                for key in path[:-1]: target = target[key]
                target[path[-1]] = value
                self.bind(meta)
                self.save(candidate, meta)
                result = audit_instruction_only(control, candidate, 's06')
                self.assertFalse(result['instruction_only'])
                self.assertIn(field, [row['field'] for row in result['confounds']])

    def test_missing_controls_on_both_sides_cannot_appear_matched(self):
        with tempfile.TemporaryDirectory() as directory:
            control, candidate, _ = self.pair(Path(directory))
            for folder in (control, candidate):
                meta = json.loads((folder / 'raw/s06.wav.json').read_text())
                del meta['selected_seed']
                self.save(folder, meta)
            result = audit_instruction_only(control, candidate, 's06')
            self.assertFalse(result['instruction_only'])
            self.assertEqual(len(result['missing_evidence']), 2)

    def test_stale_internal_binding_and_canonical_text_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            control, candidate, meta = self.pair(Path(directory))
            meta['settings']['provenance_binding']['worker_sha256'] = 'f' * 64
            self.save(candidate, meta)
            (candidate / 'episode.json').write_text(json.dumps({'scenes': [{'id': 's06', 'text': 'Other canonical words.'}]}))
            result = audit_instruction_only(control, candidate, 's06')
            fields = [row['field'] for row in result['confounds']]
            self.assertFalse(result['instruction_only'])
            self.assertIn('candidate.settings.provenance_binding.worker_sha256', fields)
            self.assertIn('candidate.canonical_input_text', fields)

    def test_tampered_audio_is_not_accepted_as_an_instruction_experiment(self):
        with tempfile.TemporaryDirectory() as directory:
            control, candidate, _ = self.pair(Path(directory))
            before = sha(control / 'raw/s06.wav')
            (candidate / 'raw/s06.wav').write_bytes(b'changed')
            result = audit_instruction_only(control, candidate, 's06')
            self.assertFalse(result['instruction_only'])
            self.assertIn('candidate.integrity', [row['field'] for row in result['confounds']])
            self.assertEqual(sha(control / 'raw/s06.wav'), before)

    def test_valid_source_bound_derivative_is_not_a_raw_instruction_only_test(self):
        with tempfile.TemporaryDirectory() as directory:
            control, candidate, meta = self.pair(Path(directory))
            source = candidate / 'source-raw'
            source.mkdir()
            for suffix in ('.wav', '.wav.json'):
                shutil.copy2(candidate / 'raw' / ('s06' + suffix), source / ('s06' + suffix))
            meta['status'] = 'DERIVED_REQUIRES_REVIEW'
            meta['derivation'] = {'kind': 'pitch_preserving_tempo', 'tempo_factor': 1.0,
                'source_wav_sha256': sha(source / 's06.wav'),
                'source_meta_sha256': sha(source / 's06.wav.json')}
            self.save(candidate, meta)
            result = audit_instruction_only(control, candidate, 's06')
            self.assertFalse(result['instruction_only'])
            self.assertIn('candidate.status', [row['field'] for row in result['confounds']])
            self.assertNotIn('candidate.integrity', [row['field'] for row in result['confounds']])

    def test_identical_instruction_is_not_an_instruction_change(self):
        with tempfile.TemporaryDirectory() as directory:
            control, candidate, meta = self.pair(Path(directory))
            meta['settings']['instruct'] = 'control'
            self.save(candidate, meta)
            result = audit_instruction_only(control, candidate, 's06')
            self.assertFalse(result['instruction_only'])
            self.assertIn('Instruction did not change', [row['reason'] for row in result['confounds']])


if __name__ == '__main__':
    unittest.main()
