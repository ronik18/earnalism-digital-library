"""Quiet editing must never become an unrecorded speech/voice transformation."""
import array
import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audio_derivation import check_unit, sha
from narration_edit import _copy_unit
from voice_finish import RATE, _bytes, _decode, prepare_pcm, render


class VoiceFinishTests(unittest.TestCase):
    def samples(self):
        return array.array('f', (0 if RATE <= i < RATE*1.5 else
            .04*math.sin(2*math.pi*140*i/RATE) for i in range(RATE*3)))

    def plan(self, digest='fixture'):
        return {'sample_rate': RATE, 'source_sha256': digest,
            'cuts': [{'start_sample': 26400, 'end_sample': 28320, 'reason': 'Measured quiet A'},
                     {'start_sample': 31440, 'end_sample': 33600, 'reason': 'Measured quiet B'}],
            'gain_knots': [{'sample': 0, 'gain_db': 0}, {'sample': 27600, 'gain_db': 0},
                           {'sample': 34800, 'gain_db': 1}, {'sample': 72000, 'gain_db': 1}],
            'protected': [{'start_sample': 0, 'end_sample': 24000, 'reason': 'First speech and breath'},
                          {'start_sample': 36000, 'end_sample': 72000, 'reason': 'Later speech and full tail'}]}

    def source(self, root):
        src = root/'source';(src/'raw').mkdir(parents=True)
        wav = src/'raw/s01.wav'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'f32le', '-ar', str(RATE), '-ac', '1',
            '-i', 'pipe:0', '-c:a', 'pcm_f32le', str(wav)], input=_bytes(self.samples()), check=True)
        meta = {'status': 'GENERATED_REQUIRES_REVIEW', 'segment_id': 's01', 'wav_sha256': sha(wav),
            'selected_seed': 20261028, 'selected_attempt': 1,
            'settings': {'speaker': 'Ryan', 'instruct': 'Fixture has no naturalness approval.',
                         'text': 'A full thought keeps the original source voice and its natural words.'},
            'audio': {'duration_seconds': 3, 'mechanical_checks': 'PASS'},
            'provenance': {'model_id': 'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice',
                           'model_revision': 'fixture-model', 'worker_sha256': 'fixture-worker'}}
        Path(str(wav)+'.json').write_text(json.dumps(meta))
        return src

    def test_identity_plan_and_zero_gain_retain_every_pcm_sample_exactly(self):
        samples = self.samples();p=self.plan();p['cuts']=[]
        p['gain_knots']=[{'sample':0,'gain_db':0},{'sample':len(samples),'gain_db':0}]
        result, evidence=prepare_pcm(samples,p,'fixture')
        self.assertEqual(_bytes(result),_bytes(samples))
        self.assertEqual(evidence['samples_removed'],0)

    def test_render_keeps_speech_order_and_documented_gain_without_any_timewarp(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);src=self.source(root);before=sha(src/'raw/s01.wav');dest=root/'finish'
            p=self.plan(before);meta=render(src,dest,'s01',p)
            original=_decode(src/'raw/s01.wav');actual=_decode(dest/'raw/s01.wav')
            self.assertEqual(_bytes(actual[:24000]),_bytes(original[:24000]))
            removed=4080;expected=array.array('f',[value*10**(1/20) for value in original[36000:]])
            self.assertEqual(_bytes(actual[36000-removed:]),_bytes(expected))
            self.assertEqual(len(actual),len(original)-removed)
            self.assertEqual(sha(src/'raw/s01.wav'),before)
            self.assertEqual(meta['selected_seed'],20261028)
            self.assertFalse(meta['derivation']['new_generation'])
            self.assertFalse(meta['derivation']['retry_budgets_reset'])
            self.assertEqual(meta['audio']['human_listening_review'],'PENDING')
            self.assertEqual(meta['audio']['text_completeness'],'REQUIRES_FRESH_ASR')
            self.assertFalse(meta['publication_approved'])

    def test_rms_and_peak_cut_thresholds_are_independently_enforced(self):
        for mode in ['rms','peak']:
            with self.subTest(mode=mode):
                samples=self.samples();p=self.plan();a,b=26400,28320
                if mode=='rms':samples[a:b]=array.array('f',[.003]*(b-a))
                else:samples[a+10]=.02
                with self.assertRaisesRegex(ValueError,'not measured quiet'):prepare_pcm(samples,p,'fixture')

    def test_protected_speech_or_breath_is_never_deleted_even_when_quiet(self):
        p=self.plan();p['protected'].append({'start_sample':27000,'end_sample':27100,'reason':'A quiet breath'})
        with self.assertRaisesRegex(ValueError,'protected speech/breath'):prepare_pcm(self.samples(),p,'fixture')
        p['protected']=[]
        with self.assertRaisesRegex(ValueError,'Explicit protected'):prepare_pcm(self.samples(),p,'fixture')

    def test_cut_duration_total_order_head_tail_and_integer_bounds(self):
        cases=[
            [{'start_sample':24001,'end_sample':32000,'reason':'Too long'}],
            [{'start_sample':24000,'end_sample':26600,'reason':'A'},
             {'start_sample':27000,'end_sample':29600,'reason':'B'},
             {'start_sample':30000,'end_sample':32600,'reason':'C'}],
            [{'start_sample':27000,'end_sample':28000,'reason':'A'},
             {'start_sample':26000,'end_sample':26500,'reason':'Out of order'}],
            [{'start_sample':0,'end_sample':1,'reason':'Head cut'}],
            [{'start_sample':71999,'end_sample':72000,'reason':'Tail cut'}],
            [{'start_sample':26400.0,'end_sample':28320,'reason':'Float index'}],
            [{'start_sample':True,'end_sample':28320,'reason':'Boolean index'}]]
        for cuts in cases:
            with self.subTest(cuts=cuts):
                p=self.plan();p['cuts']=cuts;p['protected']=[{'start_sample':1,'end_sample':2,'reason':'Protected placeholder'}]
                with self.assertRaises(ValueError):prepare_pcm(self.samples(),p,'fixture')

    def test_quiet_payload_cannot_hide_an_abrupt_cut_join(self):
        samples=self.samples();samples[28320]=.001
        with self.assertRaisesRegex(ValueError,'sample-step'):prepare_pcm(samples,self.plan(),'fixture')

    def test_gain_range_slew_order_coverage_and_unsupported_operations_fail(self):
        variants=[
            [{'sample':0,'gain_db':3.1},{'sample':72000,'gain_db':3.1}],
            [{'sample':0,'gain_db':0},{'sample':1200,'gain_db':2},{'sample':72000,'gain_db':2}],
            [{'sample':0,'gain_db':0},{'sample':72000,'gain_db':float('nan')}],
            [{'sample':1,'gain_db':0},{'sample':72000,'gain_db':0}],
            [{'sample':0,'gain_db':0},{'sample':71999,'gain_db':0}],
            [{'sample':0,'gain_db':0},{'sample':0,'gain_db':0},{'sample':72000,'gain_db':0}]]
        for knots in variants:
            with self.subTest(knots=knots):
                p=self.plan();p['gain_knots']=knots
                with self.assertRaises(ValueError):prepare_pcm(self.samples(),p,'fixture')
        p=self.plan();p['tempo']=.9
        with self.assertRaisesRegex(ValueError,'Unsupported'):prepare_pcm(self.samples(),p,'fixture')
        p=self.plan();p['source_sha256']='different'
        with self.assertRaisesRegex(ValueError,'binding'):prepare_pcm(self.samples(),p,'fixture')

    def test_output_pcm_tampering_fails_even_after_updating_file_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);src=self.source(root);dest=root/'finish'
            meta=render(src,dest,'s01',self.plan(sha(src/'raw/s01.wav')))
            values=_decode(dest/'raw/s01.wav');values[1000]*=.5;altered=root/'altered.wav'
            subprocess.run(['ffmpeg','-v','error','-f','f32le','-ar',str(RATE),'-ac','1','-i','pipe:0',
                '-c:a','pcm_f32le',str(altered)],input=_bytes(values),check=True)
            altered.replace(dest/'raw/s01.wav');meta['wav_sha256']=sha(dest/'raw/s01.wav')
            (dest/'raw/s01.wav.json').write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError,'exact source-preserving reconstruction'):check_unit(dest,'s01')

    def test_copy_recurses_and_changed_copied_source_does_not_change_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);src=self.source(root);dest=root/'finish';before=sha(src/'raw/s01.wav')
            render(src,dest,'s01',self.plan(before));copied=root/'copied';_copy_unit(dest,copied,'s01')
            self.assertEqual(check_unit(copied,'s01')['derivation']['kind'],'source_preserving_voice_finish')
            self.assertEqual(sha(copied/'finish-source/raw/s01.wav'),before)
            (copied/'finish-source/raw/s01.wav').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'binding'):check_unit(copied,'s01')
            self.assertEqual(sha(src/'raw/s01.wav'),before);check_unit(dest,'s01')

    def test_no_stacking_overwriting_or_unsupported_processing_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);src=self.source(root);dest=root/'finish'
            meta=render(src,dest,'s01',self.plan(sha(src/'raw/s01.wav')))
            with self.assertRaisesRegex(ValueError,'untouched generated'):render(dest,root/'stacked','s01',self.plan(sha(dest/'raw/s01.wav')))
            with self.assertRaises(FileExistsError):render(src,dest,'s01',self.plan(sha(src/'raw/s01.wav')))
            meta['derivation']['eq_applied']=True;(dest/'raw/s01.wav.json').write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError,'Unsupported or stacked'):check_unit(dest,'s01')

    def test_stale_preservation_evidence_and_changed_settings_fail(self):
        for field in ['evidence','settings']:
            with self.subTest(field=field),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);src=self.source(root);dest=root/'finish'
                meta=render(src,dest,'s01',self.plan(sha(src/'raw/s01.wav')))
                if field=='evidence':meta['derivation']['preservation_evidence']['samples_removed']+=1
                else:meta['settings']=dict(meta['settings'],instruct='A different voice instruction')
                (dest/'raw/s01.wav.json').write_text(json.dumps(meta))
                with self.assertRaises(ValueError):check_unit(dest,'s01')

    def test_non_native_format_is_rejected_without_conversion(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);src=self.source(root);other=root/'other.wav'
            subprocess.run(['ffmpeg','-v','error','-i',str(src/'raw/s01.wav'),'-ar','48000',
                            '-c:a','pcm_f32le',str(other)],check=True)
            other.replace(src/'raw/s01.wav');m=json.loads((src/'raw/s01.wav.json').read_text());m['wav_sha256']=sha(src/'raw/s01.wav');(src/'raw/s01.wav.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'native 24 kHz'):render(src,root/'finish','s01',self.plan(m['wav_sha256']))
            self.assertFalse((root/'finish').exists())


if __name__=='__main__':
    unittest.main()
