"""Context synthesis is one disclosed trial, not a reset or an extracted repair."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_voice_experiment as fixtures
from audio_derivation import sha
from context_experiment import audit_context_experiment, make_spec, validate_context_spec

PREFIX='A lunar eclipse is different: Earth lies between the Sun and Moon, and its shadow reaches the Moon. That requires a special alignment.'
MIDDLE='The phase cycle lasts about twenty nine and a half days. It runs from one new Moon to the next. As our viewpoint changes, the sunlit part we see grows, then shrinks.'
SUFFIX='So that crescent is not a missing piece.'


class ContextExperimentTests(unittest.TestCase):
    def unit(self, folder, text, candidate=False):
        self.fixture=fixtures.VoiceExperimentTests()
        meta=self.fixture.make_take(folder,'Selected Y instruction')
        meta['settings']['text']=text;meta['audio']['duration_seconds']=20
        meta['selected_attempt']=1;meta['attempts']=[{'attempt':1,'seed':20261028}]
        self.fixture.save(folder,meta)
        (folder/'episode.json').write_text(json.dumps({'scenes':[{'id':'s06','text':text}]}))
        (folder/'alignment').mkdir()
        words=[{'word':w,'start':i*.1,'end':(i+1)*.1} for i,w in enumerate(text.split())]
        (folder/'alignment/s06.json').write_text(json.dumps({'recognized':text,'word_times':words,
            'audio_sha256':meta['wav_sha256'],'unresolved_asr_edits':[]}))
        if candidate:
            (folder/'config').mkdir()
            (folder/'config/qwen-job.json').write_text(json.dumps({'max_attempts':1,'segments':[
                {'segment_id':'s06','text':text,'instruct':meta['settings']['instruct'],
                 'speaker':'Ryan','seed':20261028}]}))
        return meta

    def setup(self, root):
        y=root/'Y';candidate=root/'candidate';previous=root/'previous';following=root/'following'
        self.unit(y,MIDDLE);self.unit(candidate,' '.join([PREFIX,MIDDLE,SUFFIX]),True)
        self.unit(previous,'A preceding sentence. '+PREFIX)
        self.unit(following,SUFFIX+' A following sentence.')
        history=root/'prior-history.json';history.write_text(json.dumps({'canonical_generation_index':3,
            'canonical_max_generations':3,'canonical_text_sha256':hashlib.sha256(MIDDLE.encode()).hexdigest()}))
        def binding(folder,start,end):return {'folder':str(folder),'scene_id':'s06',
            'wav_sha256':sha(folder/'raw/s06.wav'),'alignment_sha256':sha(folder/'alignment/s06.json'),
            'clip_start_seconds':start,'clip_end_seconds':end}
        spec=make_spec(y,'s06',PREFIX,SUFFIX,binding(previous,.3,20),
            binding(following,0,len(SUFFIX.split())*.1),history)
        return y,candidate,spec

    def audit(self,y,candidate,spec):return audit_context_experiment(y,candidate,'s06','s06',spec)

    def change_meta(self,folder,change):
        p=folder/'raw/s06.wav.json';meta=json.loads(p.read_text());change(meta);self.fixture.save(folder,meta)

    def test_valid_full_context_trial_preserves_exhausted_middle_and_never_approves(self):
        with tempfile.TemporaryDirectory() as directory:
            y,candidate,spec=self.setup(Path(directory));result=self.audit(y,candidate,spec)
            self.assertTrue(result['context_only'],result)
            self.assertEqual(result['context']['word_count'],63)
            self.assertEqual(result['context']['character_count'],341)
            self.assertEqual(result['context']['middle_physical_generation_index'],4)
            self.assertTrue(result['context']['no_prior_counters_reset'])
            self.assertEqual(result['listening_review'],'PENDING')
            self.assertEqual(result['causal_isolation'],'NOT_ESTABLISHED')
            for key in ['middle_only_extraction_approval','video_integration_approval','publication_approval']:
                self.assertFalse(result[key])

    def test_other_baseline_seed_and_smaller_exhausted_budget_are_derived_not_hardcoded(self):
        with tempfile.TemporaryDirectory() as directory:
            y,candidate,spec=self.setup(Path(directory));seed=918273
            for folder in (y,candidate):
                self.change_meta(folder,lambda m:m.update(selected_seed=seed))
                self.change_meta(folder,lambda m:m['settings'].update(seed_base=seed))
                self.change_meta(folder,lambda m:m['attempts'][0].update(seed=seed))
            job_path=candidate/'config/qwen-job.json';job=json.loads(job_path.read_text())
            job['segments'][0]['seed']=seed;job_path.write_text(json.dumps(job))
            history_path=Path(spec['previous_middle_history_path']);history=json.loads(history_path.read_text())
            history.update(canonical_generation_index=2,canonical_max_generations=2);history_path.write_text(json.dumps(history))
            spec=make_spec(y,'s06',PREFIX,SUFFIX,spec['prefix_source'],spec['suffix_source'],history_path)
            self.assertEqual(spec['previous_middle_generations'],2)
            self.assertEqual(spec['previous_middle_generation_limit'],2)
            self.assertEqual(spec['middle_physical_generation_index'],3)
            result=self.audit(y,candidate,spec);self.assertTrue(result['context_only'],result)
            self.assertEqual(result['context']['baseline_actual_selected_seed'],seed)

    def test_missing_changed_prefix_suffix_and_dummy_padding_are_rejected(self):
        for key,value in [('prefix',''),('suffix','A different ending.'),('prefix','Um. '+PREFIX),('dummy_padding',True)]:
            with self.subTest(key=key,value=value),tempfile.TemporaryDirectory() as directory:
                y,candidate,spec=self.setup(Path(directory));spec[key]=value
                self.assertFalse(self.audit(y,candidate,spec)['context_only'])

    def test_only_context_text_may_differ_not_instruction_actual_seed_or_controls(self):
        changes=[lambda m:m['settings'].update(instruct='New direction'),
                 lambda m:m.update(selected_seed=20261029),
                 lambda m:m['settings']['generation'].update(temperature=.7),
                 lambda m:m['provenance']['hardware'].update(name='Different GPU')]
        for change in changes:
            with self.subTest(change=change),tempfile.TemporaryDirectory() as directory:
                y,candidate,spec=self.setup(Path(directory));self.change_meta(candidate,change)
                self.assertFalse(self.audit(y,candidate,spec)['context_only'])

    def test_middle_only_candidate_or_missing_spoken_neighbor_is_not_approved(self):
        with tempfile.TemporaryDirectory() as directory:
            y,candidate,spec=self.setup(Path(directory))
            self.change_meta(candidate,lambda m:m['settings'].update(text=MIDDLE))
            (candidate/'episode.json').write_text(json.dumps({'scenes':[{'id':'s06','text':MIDDLE}]}))
            self.assertFalse(self.audit(y,candidate,spec)['context_only'])
        with tempfile.TemporaryDirectory() as directory:
            y,candidate,spec=self.setup(Path(directory));p=candidate/'alignment/s06.json';a=json.loads(p.read_text())
            a['recognized']=MIDDLE;a['word_times']=a['word_times'][len(PREFIX.split()):-len(SUFFIX.split())];p.write_text(json.dumps(a))
            self.assertFalse(self.audit(y,candidate,spec)['context_only'])

    def test_caller_or_actual_attempt_budget_above_one_is_rejected(self):
        for target in ['spec','job','attempts','interrupted']:
            with self.subTest(target=target),tempfile.TemporaryDirectory() as directory:
                y,candidate,spec=self.setup(Path(directory))
                if target=='spec':spec['max_context_attempts']=2
                elif target=='job':
                    p=candidate/'config/qwen-job.json';j=json.loads(p.read_text());j['max_attempts']=3;p.write_text(json.dumps(j))
                elif target=='attempts':self.change_meta(candidate,lambda m:m['attempts'].append({'attempt':2,'seed':20261029}))
                else:self.change_meta(candidate,lambda m:m.update(interrupted_attempt_numbers=[1]))
                self.assertFalse(self.audit(y,candidate,spec)['context_only'])

    def test_repeated_or_added_words_hold_even_when_waveform_and_controls_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            y,candidate,spec=self.setup(Path(directory));p=candidate/'alignment/s06.json'
            record=json.loads(p.read_text())
            record['recognized']=record['recognized'].replace('then shrinks.', 'then shrinks, shrinks strumps.')
            record['unresolved_asr_edits']=[{'tag':'insert','reference':[], 'recognized':['shrinks','strumps']}]
            p.write_text(json.dumps(record));result=self.audit(y,candidate,spec)
            self.assertFalse(result['context_only'])
            self.assertIn('Unresolved semantic ASR differences',str(result['confounds']))
            self.assertFalse(result['video_integration_approval'])
            self.assertFalse(result['publication_approval'])

    def test_counter_reset_or_hidden_fourth_middle_physical_generation_fails(self):
        for key,value in [('previous_middle_generations',0),('middle_physical_generation_index',1),('middle_only_promotion',True),('scope','middle_only')]:
            with self.subTest(key=key),tempfile.TemporaryDirectory() as directory:
                y,candidate,spec=self.setup(Path(directory));spec[key]=value
                self.assertFalse(self.audit(y,candidate,spec)['context_only'])
        with tempfile.TemporaryDirectory() as directory:
            y,candidate,spec=self.setup(Path(directory));Path(spec['previous_middle_history_path']).write_text('{}')
            self.assertFalse(self.audit(y,candidate,spec)['context_only'])

    def test_complete_context_stays_one_raw_unit_without_extraction_or_assembly(self):
        with tempfile.TemporaryDirectory() as directory:
            y,candidate,spec=self.setup(Path(directory));p=candidate/'episode.json';e=json.loads(p.read_text());e['scenes'].append(e['scenes'][0]);p.write_text(json.dumps(e))
            self.assertFalse(self.audit(y,candidate,spec)['context_only'])
        with tempfile.TemporaryDirectory() as directory:
            y,candidate,spec=self.setup(Path(directory));self.change_meta(candidate,lambda m:m.update(derivation={'kind':'middle_extraction'}))
            self.assertFalse(self.audit(y,candidate,spec)['context_only'])

    def test_changed_source_or_alignment_and_clip_with_extra_words_fail(self):
        for target in ['wave','alignment','clip']:
            with self.subTest(target=target),tempfile.TemporaryDirectory() as directory:
                y,candidate,spec=self.setup(Path(directory));binding=spec['prefix_source']
                if target=='wave':Path(binding['folder'],'raw/s06.wav').write_bytes(b'changed')
                elif target=='alignment':Path(binding['folder'],'alignment/s06.json').write_text('{}')
                else:binding['clip_start_seconds']=0
                self.assertFalse(self.audit(y,candidate,spec)['context_only'])

    def test_actual_worker_word_and_character_limits_cannot_be_expanded(self):
        with tempfile.TemporaryDirectory() as directory:
            y,candidate,spec=self.setup(Path(directory));more='Additional context. '+PREFIX
            # Rebind a genuine longer neighbor; exceeding the worker limit still fails.
            old=Path(spec['prefix_source']['folder']);other=Path(directory)/'long-prefix';self.unit(other,more)
            spec['prefix']=more;spec['prefix_source'].update(folder=str(other),wav_sha256=sha(other/'raw/s06.wav'),
                alignment_sha256=sha(other/'alignment/s06.json'),clip_start_seconds=0)
            # Two additional words reaches65; a further complete sentence exceeds it.
            more='Another complete sentence. '+more
            other2=Path(directory)/'longer-prefix';self.unit(other2,more);spec['prefix']=more;spec['prefix_source'].update(
                folder=str(other2),wav_sha256=sha(other2/'raw/s06.wav'),alignment_sha256=sha(other2/'alignment/s06.json'))
            with self.assertRaisesRegex(ValueError,'65-word/520-character'):validate_context_spec(y,'s06',spec)
        with tempfile.TemporaryDirectory() as directory:
            y,candidate,spec=self.setup(Path(directory));more=('A'*300)+'. '+PREFIX
            other=Path(directory)/'character-prefix';self.unit(other,more);spec['prefix']=more
            spec['prefix_source'].update(folder=str(other),wav_sha256=sha(other/'raw/s06.wav'),
                alignment_sha256=sha(other/'alignment/s06.json'),clip_start_seconds=0)
            self.assertLessEqual(len((' '.join([more,MIDDLE,SUFFIX])).split()),65)
            with self.assertRaisesRegex(ValueError,'65-word/520-character'):validate_context_spec(y,'s06',spec)


if __name__=='__main__':unittest.main()
