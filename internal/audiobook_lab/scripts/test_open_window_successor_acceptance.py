"""Synthetic verifier tests only; no programme adoption or runtime PASS receipt."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audiobook_active_release_v2 as manager
import open_window_successor_acceptance as successor


class SuccessorAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tracks=[{'id':'test-track','chunks':[{'segment_id':f'test-{i}', 'assets':{'audio':{'sha256':'c'*64,'size_bytes':1,'mime_type':'audio/mpeg'}}} for i in range(29)]}]
        self.mapping_sha=successor.chunk_mapping_digest({'tracks':self.tracks})
        self.mapping_patch=patch.object(successor,'CHUNK_MAPPING_SHA',self.mapping_sha)
        self.mapping_patch.start();self.addCleanup(self.mapping_patch.stop)
        self.rights = {'decision_id': 'test-dependency-only'}
        self.adoption = dict(successor.IDENTITY, policy=successor.POLICY, status='ADOPTED',
            acceptance_representation_sha256=successor.ACCEPTANCE_SHA,
            unaddressed_material_defects=[], deployed_source_join_sha256='a'*64,
            policy_adoption={'status':'ADOPTED','decision_sha256':'b'*64,
                             'adopted_by':'synthetic-test','authority_reference':'synthetic-test'},
            audio_use_decision=self.rights)
        self.descriptor = dict(successor.IDENTITY, schema_version='audiobook_release_descriptor.v1',
            release_candidate_status='OWNER_ACCEPTED_UNCERTAINTY_STORAGE_PENDING',
            known_release_blockers=manager.QA_CANDIDATE_DOWNSTREAM_GATES.copy(),
            duration_ms=491436,sample_rate=24000,master_samples=11794472,
            padding_disposition={'preserve_audio_bytes':True,'paragraph_019_terminal_silent_samples':11,
                                 'exact_sample_trim_enforced':False},
            release_candidate_evidence={'acceptance_policy':successor.POLICY,
                'status':'OWNER_ACCEPTED_UNCERTAINTY','acceptance_representation_sha256':successor.ACCEPTANCE_SHA,
                'human_scores':None,'acoustic_pass_claimed':False,'all_release_gates_passed':False,
                'all_pre_storage_release_gates_passed':False,
                'unit24_disposition':'OWNER_ACCEPTED_UNCERTAINTY_UNIT24_ONLY',
                'remaining_lexical_uncertainty_units':successor.LEXICAL_UNITS.copy(),
                'gates':dict.fromkeys(['reader_truth','source_content_toc','first_words_match',
                   'last_words_match','ordered_content_integrity','front_cover','back_cover'],True)},
            evidence_sha256={'successor_acceptance':successor.ACCEPTANCE_SHA,
                'remaining_region_triage':successor.TRIAGE_SHA,'master_provenance_and_qa':successor.QA_SHA,
                'audio_use_proposition':successor.AUDIO_PROPOSITION_SHA,'deployed_source_join':'a'*64,
                'policy_adoption':'b'*64,'audio_use_adoption':successor.AUDIO_DECISION_SHA})
        self.descriptor['release_candidate_evidence']['gates'].update(confirmed_material_defects=[],
            sync_tier='SOURCE_UNIT_PARAGRAPH_BOUNDS_ONLY',highlight_sync_enabled=False)

    def validate(self):
        d=self.descriptor
        package={'tracks':self.tracks,'slug':d['slug'],'source_sha256':d['controlled_source_sha256'],
                 'manuscript_sha256':d['manuscript_sha256'],
                 'release_descriptor_sha256':manager.sha256_bytes(manager.canonical_json_bytes(d))}
        return manager.validate_qa_candidate_release_descriptor(d,package,controlled_language='en')

    def dependencies(self, rights_pass=True):
        return (patch.object(successor,'load_trusted_adoption',return_value=self.adoption),
                patch.object(successor,'load_production_registry',return_value=(
                    {self.rights['decision_id']:successor.AUDIO_DECISION_SHA},frozenset())),
                patch.object(successor,'evaluate_accepted_record',return_value=SimpleNamespace(passed=rights_pass)))

    def use_listened_policy(self):
        self.adoption.update(policy=successor.LISTENED_POLICY,
            acceptance_representation_sha256=successor.LISTENED_ACCEPTANCE_SHA,
            deployed_source_join_sha256=successor.LISTENED_EVIDENCE['deployed_source_join'],
            listening_evidence_sha256=successor.LISTENED_EVIDENCE.copy())
        d=self.descriptor;c=d['release_candidate_evidence']
        d['release_candidate_status']='OWNER_REVIEWED_LOCAL_QA_STORAGE_PENDING'
        d['known_release_blockers']=successor.LISTENED_DESCRIPTOR_BLOCKERS.copy()
        c.update(acceptance_policy=successor.LISTENED_POLICY,status='OWNER_REVIEWED_LOCAL_QA',
            acceptance_representation_sha256=successor.LISTENED_ACCEPTANCE_SHA,
            remaining_lexical_uncertainty_units=[],
            owner_local_qa={'review_type':'OWNER_REPORTED_SOURCE_FOLLOWING_FULL_TITLE',
                'proposed_points':85,'assessed_maximum':85,'production_points':None,
                'overall_points':None,'release_threshold':95})
        d['evidence_sha256'].update(successor.LISTENED_EVIDENCE,
            successor_acceptance=successor.LISTENED_ACCEPTANCE_SHA)

    def test_listened_policy_binds_owner_review_without_production_credit(self):
        self.use_listened_policy();a,b,c=self.dependencies()
        with a as load,b,c as rights:
            result=self.validate()
            load.assert_called_once_with(successor.LISTENED_POLICY)
            self.assertEqual(result['release_candidate_evidence']['remaining_lexical_uncertainty_units'],[])
            self.assertIsNone(result['release_candidate_evidence']['owner_local_qa']['production_points'])
            self.assertFalse(result['release_candidate_evidence']['all_release_gates_passed'])
            self.assertEqual(rights.call_args.kwargs['country'],'IN')

    def test_listened_policy_rejects_evidence_drift_and_inflated_scores(self):
        self.use_listened_policy();base=copy.deepcopy(self.descriptor)
        for case in [*successor.LISTENED_EVIDENCE,'production_credit','overall_credit','threshold','reviewer','legacy_lexical','master','padding','blocker']:
            self.descriptor=copy.deepcopy(base);d=self.descriptor;c=d['release_candidate_evidence']
            if case in successor.LISTENED_EVIDENCE:d['evidence_sha256'][case]='f'*64
            elif case=='production_credit':c['owner_local_qa']['production_points']=15
            elif case=='overall_credit':c['owner_local_qa']['overall_points']=100
            elif case=='threshold':c['owner_local_qa']['release_threshold']=85
            elif case=='reviewer':c['owner_local_qa']['review_type']='AUTOMATED_PASS'
            elif case=='legacy_lexical':c['remaining_lexical_uncertainty_units']=successor.LEXICAL_UNITS.copy()
            elif case=='master':d['master_mp3_sha256']='f'*64
            elif case=='padding':d['padding_disposition']['exact_sample_trim_enforced']=True
            elif case=='blocker':d['known_release_blockers']=[]
            a,b,c=self.dependencies()
            with self.subTest(case=case),a,b,c,self.assertRaises(manager.ReleasePointerError):self.validate()

    def test_listened_policy_requires_trusted_adoption_and_native_rights(self):
        self.use_listened_policy()
        with self.assertRaises(manager.ReleasePointerError):self.validate()
        a,b,c=self.dependencies(False)
        with a,b,c,self.assertRaises(manager.ReleasePointerError):self.validate()
        self.adoption['listening_evidence_sha256']={}
        a,b,c=self.dependencies()
        with a,b,c,self.assertRaises(manager.ReleasePointerError):self.validate()

    def test_v2_registry_selection_preserves_v1_and_rejects_duplicate_v2(self):
        self.use_listened_policy();record=self.adoption
        entry={'record':record,'record_sha256':manager.sha256_bytes(successor.canonical(record))}
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'registry.json'
            p.write_text(json.dumps({'schema':'earnalism.successor-adoption-registry.v1',
                'adoptions':[{'record':{'policy':successor.POLICY}},entry]}))
            with patch.object(successor,'REGISTRY',p):
                self.assertEqual(successor.load_trusted_adoption(successor.LISTENED_POLICY),record)
            p.write_text(json.dumps({'schema':'earnalism.successor-adoption-registry.v1','adoptions':[entry,entry]}))
            with patch.object(successor,'REGISTRY',p),self.assertRaises(successor.SuccessorAcceptanceError):
                successor.load_trusted_adoption(successor.LISTENED_POLICY)

    def test_synthetic_adopted_dependencies_preserve_uncertainty_not_qa_pass(self):
        a,b,c=self.dependencies()
        with a,b,c as rights:
            result=self.validate()
            self.assertEqual(result['release_candidate_evidence']['status'],'OWNER_ACCEPTED_UNCERTAINTY')
            self.assertFalse(result['release_candidate_evidence']['acoustic_pass_claimed'])
            self.assertEqual(result['known_release_blockers'],manager.QA_CANDIDATE_DOWNSTREAM_GATES)
            self.assertEqual(rights.call_args.kwargs['use'],'audio_stream')
            self.assertEqual(rights.call_args.kwargs['country'],'IN')
            self.assertIn('master_mp3',rights.call_args.kwargs['required_components'])

    def test_canary_persists_editorial_label_without_acoustic_qa_pass(self):
        self.assert_canary_label(successor.POLICY)

    def test_listened_canary_retains_owner_provenance_without_qa_pass(self):
        self.assert_canary_label(successor.LISTENED_POLICY)

    def assert_canary_label(self, policy):
        import test_audiobook_active_release_v2 as existing_tests
        fixture=existing_tests.ActiveReleaseManagerTests('test_new_title_canary_stages_exact_package_against_hidden_fallback')
        fixture.setUp()
        try:
            fixture._prepare_approved_reader_only()
            descriptor=fixture._qa_candidate_release_descriptor()
            descriptor['release_candidate_evidence'].update(
                acceptance_policy=policy, acceptance_representation_sha256=successor.ACCEPTANCE_SHA,
                remaining_lexical_uncertainty_units=successor.LEXICAL_UNITS.copy(),
                unit24_disposition='OWNER_ACCEPTED_UNCERTAINTY_UNIT24_ONLY')
            if policy == successor.LISTENED_POLICY:
                descriptor['release_candidate_evidence'].update(status='OWNER_REVIEWED_LOCAL_QA',
                    remaining_lexical_uncertainty_units=[],
                    owner_local_qa={'proposed_points':85,'production_points':None,'overall_points':None})
            # Isolate post-validation serialization; the actual verifier has separate
            # positive/negative dependency tests above. All storage/cohort gates run.
            with patch.object(manager,'validate_qa_candidate_release_descriptor',return_value=descriptor):
                fixture._invoke_new_title_canary(release_descriptor=descriptor)
            context=manager.load_mirrored_publication(fixture.repo,fixture.slug)
            approval=context['approval_evidence'];canary=context['public_book']['audiobook_package_canary']
            self.assertIsNone(approval['audio_qa_status'])
            expected='OWNER_REVIEWED_LOCAL_QA' if policy == successor.LISTENED_POLICY else 'OWNER_ACCEPTED_UNCERTAINTY'
            self.assertEqual(approval['audio_editorial_acceptance']['status'],expected)
            if policy == successor.LISTENED_POLICY:
                self.assertIsNone(approval['audio_editorial_acceptance']['owner_local_qa']['production_points'])
            self.assertFalse(canary['editorial_acceptance']['acoustic_pass_claimed'])
            self.assertFalse(context['public_book']['audio_enabled'])
        finally:
            fixture.tearDown()

    def test_real_shipped_registry_has_no_editorial_adoption(self):
        with self.assertRaises(manager.ReleasePointerError):self.validate()

    def test_native_rights_denial_or_unshipped_decision_stops(self):
        a,b,c=self.dependencies(False)
        with a,b,c,self.assertRaises(manager.ReleasePointerError):self.validate()
        a,b,c=self.dependencies()
        with a,c,patch.object(successor,'load_production_registry',return_value=({},frozenset())),self.assertRaises(manager.ReleasePointerError):
            self.validate()

    def test_trusted_registry_missing_duplicate_and_hash_drift_stop(self):
        for entries in ([],[{'record':self.adoption,'record_sha256':'0'*64}],
                        [{'record':self.adoption,'record_sha256':'a'*64}]*2):
            with tempfile.TemporaryDirectory() as t:
                p=Path(t)/'registry.json';p.write_text(json.dumps({'schema':'earnalism.successor-adoption-registry.v1','adoptions':entries}))
                with patch.object(successor,'REGISTRY',p),self.assertRaises(successor.SuccessorAcceptanceError):
                    successor.load_trusted_adoption()

    def test_source_master_uuid_defects_scores_missing_evidence_and_padding_stop(self):
        baseline=copy.deepcopy(self.descriptor)
        def change(name):
            d=self.descriptor;c=d['release_candidate_evidence'];g=c['gates']
            if name in successor.IDENTITY:d[name]='wrong'
            elif name=='defect':g['confirmed_material_defects']=['confirmed omission']
            elif name=='missing_source':g['source_content_toc']=False
            elif name=='missing_audio':d['master_mp3_sha256']=''
            elif name=='missing_evidence':d['evidence_sha256'].pop('master_provenance_and_qa')
            elif name=='acoustic':c['acoustic_pass_claimed']=True
            elif name=='numeric':g['overall_listening_score']=9.9
            elif name=='lexical':c['remaining_lexical_uncertainty_units']=[]
            elif name=='release':c['all_release_gates_passed']=True
            elif name=='trim':d['padding_disposition']['exact_sample_trim_enforced']=True
        for name in [*successor.IDENTITY,'defect','missing_source','missing_audio','missing_evidence','acoustic','numeric','lexical','release','trim']:
            self.descriptor=copy.deepcopy(baseline);change(name);a,b,c=self.dependencies()
            with self.subTest(name=name),a,b,c,self.assertRaises(manager.ReleasePointerError):self.validate()

    def test_changed_missing_reordered_audio_or_sidecar_mapping_stops(self):
        original=copy.deepcopy(self.tracks)
        for case in ('missing', 'changed_audio', 'reordered', 'missing_asset'):
            self.tracks=copy.deepcopy(original)
            chunks=self.tracks[0]['chunks']
            if case=='missing':chunks.pop()
            elif case=='changed_audio':chunks[0]['assets']['audio']['sha256']='d'*64
            elif case=='reordered':chunks.reverse()
            else:chunks[0]['assets']['audio'].pop('sha256')
            a,b,c=self.dependencies()
            with self.subTest(case=case),a,b,c,self.assertRaises(manager.ReleasePointerError):self.validate()

    def test_descriptor_hash_guard_still_precedes_successor_branch(self):
        with patch.object(successor,'load_trusted_adoption') as load,self.assertRaises(manager.ReleasePointerError):
            manager.validate_qa_candidate_release_descriptor(self.descriptor,{},controlled_language='en')
        load.assert_not_called()


if __name__=='__main__':unittest.main()

class RealListenedSuccessorFixtureTests(unittest.TestCase):
    def test_owner_adopted_exact_descriptor_and_package_metadata(self):
        root=HERE.parent/'release_gate/open_window_listened_successor_v2'
        descriptor=json.loads((root/'release-descriptor.json').read_text())
        package=json.loads((root/'package-identity.json').read_text())
        result=manager.validate_qa_candidate_release_descriptor(descriptor,package,controlled_language='en')
        self.assertIsNone(result['release_candidate_evidence']['owner_local_qa']['production_points'])
        self.assertEqual(successor.chunk_mapping_digest(package),successor.CHUNK_MAPPING_SHA)
    def test_original_descriptor_blocker_evidence_remains_exact(self):
        root=HERE.parent/'release_gate/open_window_listened_successor_v2'
        descriptor=json.loads((root/'release-descriptor.json').read_text());package=json.loads((root/'package-identity.json').read_text())
        descriptor['known_release_blockers']=[]
        package['release_descriptor_sha256']=manager.sha256_bytes(manager.canonical_json_bytes(descriptor))
        with self.assertRaises(manager.ReleasePointerError):manager.validate_qa_candidate_release_descriptor(descriptor,package,controlled_language='en')
