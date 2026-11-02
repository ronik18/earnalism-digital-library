"""Exact retained input tests in private copied registry, never production proof."""
import copy
import functools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import open_window_scored_retained as scored
import audiobook_active_release_v2 as manager
import rights_decision_gate as rights

class ScoredRetainedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adoption=scored.load_adoption()
        cls.evidence,cls.descriptor,cls.metrics=scored.verify_evidence(cls.adoption)
        cls.package=cls.evidence.file('package-identity.PROPOSED.json')
        cls.package.pop('package_version');cls.package.pop('proposal_status')
        cls.rights_registry=Path(scored.REGISTRY).parents[3]/'backend/data/rights_decision_registry.json'
        # A source checkout has actual committed trust; the private candidate is
        # explicitly FUTURE_REGISTRY_FIXTURE_ONLY, never status projection.
        if not cls.rights_registry.exists():
            cls.rights_registry=Path(__file__).resolve().parents[3]/'backend/data/rights_decision_registry.json'
    def validate(self,descriptor=None,package=None,registry=None):
        path=registry or self.rights_registry
        with patch.object(scored,'load_production_registry',functools.partial(rights.load_production_registry,path=path)),patch.object(scored,'load_audio_package_binding',functools.partial(rights.load_audio_package_binding,path=path)):
            return scored.validate(descriptor or self.descriptor,package or self.package,'en',scored.common.DOWNSTREAM)
    def test_actual_source_evidence_recomputed_not_public(self):
        result=self.validate()
        self.assertEqual(scored.sha(scored.canonical(result)),scored.DESCRIPTOR_SHA)
        self.assertFalse(result['publication_approved'])
        self.assertFalse(result['release_candidate_evidence']['all_release_gates_passed'])
        self.assertEqual(result['known_release_blockers'][-4:],scored.common.DOWNSTREAM)
        self.assertEqual(self.metrics['CTC']['ordered_matches'],1195)
        self.assertNotEqual(self.metrics['CTC']['coverage'],1)
        self.assertLess(self.metrics['CTC']['raw_score'],9.7)
        self.assertGreater(self.metrics['CTC']['scoped_score'],9.7)
    def test_generic_manager_dispatch_uses_new_exact_profile(self):
        with patch.object(scored,'load_production_registry',functools.partial(rights.load_production_registry,path=self.rights_registry)),patch.object(scored,'load_audio_package_binding',functools.partial(rights.load_audio_package_binding,path=self.rights_registry)):
            result=manager.validate_qa_candidate_release_descriptor(self.descriptor,self.package,controlled_language='en')
        self.assertEqual(result,self.descriptor)
    def test_old_parent_or_cedar_cannot_be_relabelled(self):
        for key,value in [('master_mp3_sha256','1fd37c818d4869eac8548811c714bd8907d0753ffa31b37fbf63d6e4764059a5'),('slug','the-selfish-giant'),('generation',dict(scored.GENERATION,voice='Cedar')),('controlled_source_sha256','f'*64),('manuscript_sha256','a'*64)]:
            with self.subTest(key=key):
                descriptor=copy.deepcopy(self.descriptor);descriptor[key]=value
                with self.assertRaises(scored.Error):self.validate(descriptor=descriptor)
    def test_claiming_release_ready_or_clearing_holds_denied(self):
        for edit in ['approve','allgates','clear']:
            d=copy.deepcopy(self.descriptor)
            if edit=='approve':d['publication_approved']=True
            elif edit=='allgates':d['release_candidate_evidence']['all_release_gates_passed']=True
            else:d['known_release_blockers']=[]
            with self.assertRaises(scored.Error):self.validate(descriptor=d)
    def test_adoption_empty_proposed_or_changed_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'registry.json'
            for state in ['empty','proposed','digest']:
                reg=json.loads(scored.REGISTRY.read_text())
                if state=='empty':reg['adoptions']=[]
                elif state=='proposed':
                    reg['adoptions'][0]['record']['status']='PROPOSED_NOT_ADOPTED';reg['adoptions'][0]['record_sha256']=scored.sha(scored.canonical(reg['adoptions'][0]['record']))
                else:reg['adoptions'][0]['record']['confidence']=1
                p.write_text(json.dumps(reg))
                with patch.object(scored,'REGISTRY',p),self.assertRaises(scored.Error):scored.load_adoption()
    def test_active_policy_binding_cannot_be_silently_relaxed(self):
        adoption=copy.deepcopy(self.adoption);adoption['active_policy_provenance']['sha256']='0'*64
        with self.assertRaisesRegex(scored.Error,'owner policy'):scored.verify_evidence(adoption)
    def test_claimed_full_source_custody_cannot_replace_measured_coverage(self):
        adoption=copy.deepcopy(self.adoption);adoption['recognition_metrics']['CTC']['coverage']=1.0
        with self.assertRaisesRegex(scored.Error,'custody1.0'):scored.verify_evidence(adoption)
    def test_evidence_index_tamper_denied(self):
        with self.assertRaises(scored.Error):scored.Evidence('0'*64)
    def semantic_evidence(self,mutator):
        evidence=self.evidence
        class Modified:
            def file(self,name):
                value=copy.deepcopy(evidence.file(name))
                if name=='evidence/ACTUAL-ASR-AND-SIX-OWNER-ADJUDICATIONS.json':mutator(value)
                return value
            def json(self,digest):return evidence.json(digest)
        return Modified()
    def source(self):return (scored.DATA/'frozen-v5/manuscript.txt').read_text()
    def test_raw_projection_relabel_rejected(self):
        def mutate(r):r['units'][1]['current_recording_CTC_projection_tokens'][0]='framton'
        with self.assertRaisesRegex(scored.Error,'Raw current CTC'):scored.recognize(self.semantic_evidence(mutate),self.source())
    def test_unreviewed_global_name_alias_rejected(self):
        def mutate(r):r['normal_spoken_text_comparator']['aliases']['frampton']='framton'
        with self.assertRaisesRegex(scored.Error,'alias'):scored.recognize(self.semantic_evidence(mutate),self.source())
    def test_speciality_specialty_is_not_spelling_alias(self):
        def mutate(r):r['normal_spoken_text_comparator']['aliases']['speciality']='specialty'
        with self.assertRaisesRegex(scored.Error,'alias'):scored.recognize(self.semantic_evidence(mutate),self.source())
    def test_name_correction_outside_owner_window_rejected(self):
        def mutate(r):r['units'][1]['twelve_name_window_changes'][0]['reviewed_fullbook_seconds']=[0,491]
        with self.assertRaisesRegex(scored.Error,'owner window'):scored.recognize(self.semantic_evidence(mutate),self.source())
    def test_extra_unreviewed_six_word_edit_rejected(self):
        def mutate(r):r['units'][0]['owner_changes']=[{'old':['nuttle'],'new':['nuttel'],'authority':scored.OWNER_SHA}]
        with self.assertRaisesRegex(scored.Error,'six owner scopes'):scored.recognize(self.semantic_evidence(mutate),self.source())
    def test_scoped_metric_cannot_be_claimed_raw(self):
        def mutate(r):r['aggregate_metrics']['literal_current_CTC']['score_0_to_10']=9.786710418375717
        with self.assertRaisesRegex(scored.Error,'arithmetic'):scored.recognize(self.semantic_evidence(mutate),self.source())
    def test_source_gap_duplicate_or_reorder_denied(self):
        def mutate(r):r['units'][1]['source_char_start']=0
        with self.assertRaisesRegex(scored.Error,'gaps/duplicates'):scored.recognize(self.semantic_evidence(mutate),self.source())
    def test_scoped_whisper_unheard_change_denied(self):
        def mutate(r):r['six_plus_twelve_adjudicated_full_Whisper_tokens'][-1]='specialty'
        with self.assertRaisesRegex(scored.Error,'lexical transcripts'):scored.recognize(self.semantic_evidence(mutate),self.source())
    def test_missing_revoked_widened_or_wrong_use_rights_denied(self):
        base=json.loads(self.rights_registry.read_text());decision=self.adoption['audio_use_decision']['decision_id']
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'rights.json'
            for kind in ['missing','revoked','US','download','oldbinding']:
                r=copy.deepcopy(base)
                if kind=='missing':r['accepted_records'].pop(decision)
                elif kind=='revoked':r['revoked_decision_ids'].append(decision)
                elif kind=='US':r['audio_package_bindings']['the-open-window'][scored.DESCRIPTOR_SHA]['territories'].append('US')
                elif kind=='download':r['audio_package_bindings']['the-open-window'][scored.DESCRIPTOR_SHA]['uses'].append('audio_download')
                else:r['audio_package_bindings']['the-open-window'].pop(scored.DESCRIPTOR_SHA)
                p.write_text(json.dumps(r))
                with patch.object(scored,'verify_evidence',return_value=(self.evidence,self.descriptor,self.metrics)),self.assertRaisesRegex(scored.Error,'IN audio-use'):self.validate(registry=p)
    def test_wrong_delivery_bytes_counts_or_provisional_version_denied(self):
        for kind in ['audio','coverage','duration','version']:
            p=copy.deepcopy(self.package)
            if kind=='audio':p['tracks'][0]['chunks'][0]['assets']['audio']['sha256']='a'*64
            elif kind=='coverage':p['paragraph_count']=109
            elif kind=='duration':p['duration_ms']=499072
            else:p['package_version']='PENDING_REAL_IMMUTABLE_STORAGE_BINDINGS_NOT_FABRICATED'
            with patch.object(scored,'verify_evidence',return_value=(self.evidence,self.descriptor,self.metrics)),self.assertRaises(ValueError):self.validate(package=p)
    def test_real_generic_measured_cue_guards(self):
        side=self.evidence.file('assets/chapter-001-full.timestamps.json')
        for key,value in [('audio_hash','0'*64),('source_text_hash','0'*64),('auto_estimated_sync',True)]:
            bad=copy.deepcopy(side);bad[key]=value
            with self.assertRaises(scored.builder.PackageBuildError):scored.builder._validated_cues(bad,slug='the-open-window',audio_sha256=scored.SOURCE['master_mp3_sha256'],manuscript_sha256=scored.SOURCE['manuscript_sha256'],duration_seconds=scored.FRAMES/48000)
    def test_publication_metadata_rejects_private_draft_leaks_and_wrong_voice(self):
        good={'format':{'tags':{'title':'The Open Window','author':'Saki','artist':'Earnalism; AI narration: stock Ryan (Qwen3-TTS CustomVoice)', 'comment':'Ryan Qwen3-TTS Heartwarming Heartbreaking Kevin MacLeod https://creativecommons.org/licenses/by/4.0/'}},'streams':[{'tags':{'encoder':'Lavf'}}]}
        scored.validate_publication_tags(good)
        for suffix in [' Private draft; not published.', ' Pending owner review.', ' /Users/example/file', ' https://example.org/?X-Amz-Signature=abc']:
            bad=copy.deepcopy(good);bad['format']['tags']['comment']+=suffix
            with self.assertRaises(scored.Error):scored.validate_publication_tags(bad)
        for field,value in [('author','Other'),('title','Other'),('artist','Cedar')]:
            bad=copy.deepcopy(good);bad['format']['tags'][field]=value
            with self.assertRaises(scored.Error):scored.validate_publication_tags(bad)
        bad=copy.deepcopy(good);bad['streams'][0]['tags']['comment']='private review'
        with self.assertRaises(scored.Error):scored.validate_publication_tags(bad)
    def test_missing_media_or_existing_output_never_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bundle.json';p.write_text(json.dumps({'schema':'bad'}))
            with self.assertRaises(scored.Error):scored.prepare(p,Path(tmp)/'out')
            target=Path(tmp)/'existing';target.mkdir();sentinel=target/'preserve';sentinel.write_text('existing work')
            p.write_text(json.dumps({'schema':'earnalism.open-window-scored-local-package.v1'}))
            with self.assertRaisesRegex(scored.Error,'Output exists'):scored.prepare(p,target)
            self.assertEqual(sentinel.read_text(),'existing work')
    def test_legacy_policies_remain_distinct(self):
        import native_scored_package as cedar
        import open_window_successor_acceptance as dry
        self.assertNotEqual(cedar.POLICY,scored.POLICY);self.assertNotIn(scored.POLICY,dry.SUPPORTED_POLICIES)
        self.assertEqual(cedar.SOURCE['slug'],'the-selfish-giant')

if __name__=='__main__':unittest.main()
