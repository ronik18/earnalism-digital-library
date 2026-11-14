"""Behavioral AV gates; mocked media here never constitutes production evidence."""
import copy
import json
from pathlib import Path
import tempfile
import shutil
import unittest
from unittest.mock import patch

from scripts.book_audiovisual import digest, feedback, plan, title_key, write_private_new
from scripts.release_acceptance import (AV_DIMENSIONS, AV_FATAL_FLAGS, audiovisual_acceptance,
                                        audiovisual_candidate_sha256)
from scripts.produce_release import evaluate, execute_go_live, canonical_hash


class AVFixture:
    def __init__(self, root):
        self.root = root
        self.manifest = {'slug': 'bengali-pilot'}
        self.files = {}
        for name, content in [('manuscript', 'কাল কুল'), ('narration', 'MOCK NARRATION'),
                              ('scored_audio', 'MOCK SCORED AUDIO'), ('storyboard', '{}'), ('score_plan', '{}')]:
            self.files[name] = self.write(name, content)
        self.timing = {'schema': 'earnalism.audiobook_score.timing.v1',
                       'manuscript_sha256': self.files['manuscript']['sha256'],
                       'narration_sha256': self.files['narration']['sha256'],
                       'duration_ms': 1000, 'method': 'human_verified_audio',
                       'provenance': {'tool': 'MOCK FOR UNIT TEST', 'version': '1', 'boundary_validation': 'accepted'},
                       'cues': [{'id': 'c1', 'start_ms': 0, 'end_ms': 1000,
                                 'text_start': 0, 'text_end': 7, 'text': 'কাল কুল'}]}
        self.files['timing'] = self.write('timing', self.timing)
        self.output = {'format': 'landscape', **self.write('output.mp4', 'MOCK VIDEO')}
        self.manifest.update(manuscript=self.files['manuscript'], audio=self.files['narration'])
        self.av = {'schema': 'earnalism.book_audiovisual.v1', 'title': 'কাল কুল',
                   'language': 'bn', 'territory': 'IN', 'scope': 'full_title', 'files': self.files,
                   'outputs': [self.output], 'destinations': ['private-supported-destination'], 'evidence': {}}
        self.manifest['audiovisual'] = self.av
        self.measurements = [{'format': 'landscape', 'sha256': self.output['sha256'], 'width': 1920,
                              'height': 1080, 'fps': 30, 'duration_ms': 4000, 'video_codec': 'h264',
                              'audio_codec': 'aac', 'decode': 'COMPLETED'}]
        self.receipts = {}
        clearance = self.write('clearance', {'status': 'APPROVED', 'commercial_use': True,
                                            'territories': ['IN'], 'approval_ref': 'mock-only',
                                            'rights_holder': 'test fixture'})
        self.receipts['rights'] = {'status': 'APPROVED', 'territory': 'IN',
            'destinations': self.av['destinations'],
            'clearances': {name: clearance for name in ('literary_adaptation', 'translation', 'recording',
                          'voice_model', 'music_synchronization', 'visual_assets', 'commercial_distribution')}}
        self.receipts['technical'] = {'status': 'MEASURED', 'outputs': self.measurements}
        self.receipts['full_review'] = {'status': 'ACCEPTED', 'source': 'human', 'scope': 'full_title',
            'duration_ms': 4000, 'formats': ['landscape'], 'unresolved_findings': [], 'fatal_flags': [],
            'observations': 'Synthetic review assertion for isolated parser tests only.',
            'caption_delivery': {'status': 'VERIFIED', 'destinations': self.av['destinations'],
                                 'consumer': 'mock-only', 'provenance': 'synthetic parser test'},
            'overall': 9.0, 'confidence': .95, 'dimensions': {name: 9.0 for name in AV_DIMENSIONS},
            'content_checks': {'first_words_match': True, 'last_words_match': True,
                               'missing_count': 0, 'duplicated_count': 0, 'reordered_count': 0,
                               'asr_manuscript_score': 9.8}, **{flag: False for flag in AV_FATAL_FLAGS}}
        self.receipts['decision'] = {'decision': 'GO_LIVE', 'source': 'owner',
                                     'destinations': self.av['destinations'], 'action_ref': 'mock-only'}
        self.seal()

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value, encoding='utf-8')
        return {'path': name, 'sha256': digest(path)}

    def seal(self):
        self.files['timing'] = self.write('timing', self.timing)
        candidate = audiovisual_candidate_sha256(self.manifest)
        for name, receipt in self.receipts.items():
            receipt.update(schema=f'earnalism.book_av_{name}.v1', candidate_sha256=candidate,
                           provenance='Synthetic mocked unit test only; never release evidence')
            self.av['evidence'][name] = self.write(name, receipt)


class BookAVTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.fixture = AVFixture(self.root)
        self.probe = patch('scripts.release_acceptance._av_probe', return_value={'format': {'duration': '1.000'}})
        self.media = patch('scripts.release_acceptance._av_media_outputs', return_value=self.fixture.measurements)
        self.lineage = patch('scripts.release_acceptance._av_render_lineage', return_value=None)
        self.probe.start()
        self.media.start()
        self.lineage.start()

    def tearDown(self):
        self.probe.stop()
        self.media.stop()
        self.lineage.stop()
        self.temp.cleanup()

    def result(self):
        return audiovisual_acceptance(self.fixture.manifest, self.root)

    def assertHeld(self, phrase):
        result = self.result()
        self.assertEqual(result['status'], 'BLOCKED', result)
        self.assertIn(phrase, result['blockers'][0])

    def test_complete_bound_receipts_pass_parser_with_mocked_media_only(self):
        self.assertEqual(self.result()['status'], 'PASS')
        self.assertFalse(self.result()['publication_performed'])

    def test_synthetic_or_sample_never_qualifies(self):
        self.fixture.av['fixture_mode'] = True
        self.assertHeld('real complete-title')
        self.fixture.av['fixture_mode'] = False
        self.fixture.av['scope'] = 'representative_sample'
        self.assertHeld('real complete-title')

    def test_changed_bytes_or_destinations_cannot_reuse_review(self):
        (self.root / 'scored_audio').write_text('changed audio')
        self.assertHeld('file changed')
        self.fixture.files['scored_audio'] = self.fixture.write('scored_audio', 'MOCK SCORED AUDIO')
        self.fixture.av['destinations'] = ['different-public-destination']
        self.assertHeld('stale or bound')

    def test_estimated_timing_and_missing_ending_rejected(self):
        self.fixture.timing['method'] = 'estimated'
        self.fixture.seal()
        self.assertHeld('measured timing')
        self.fixture.timing['method'] = 'human_verified_audio'
        self.fixture.timing['cues'][0].update(text_end=3, text='কাল')
        self.fixture.seal()
        self.assertHeld('ending is missing')

    def test_bengali_low_dimension_or_confidence_fails_even_automated_policy(self):
        self.fixture.manifest['editorial_release_policy'] = 'automated-editorial-2026-11-11'
        self.fixture.receipts['full_review']['dimensions']['anti_robotic_texture'] = 8.89
        self.fixture.seal()
        self.assertHeld('every dimension')
        self.fixture.receipts['full_review']['dimensions']['anti_robotic_texture'] = 9
        self.fixture.receipts['full_review']['confidence'] = .89
        self.fixture.seal()
        self.assertHeld('confidence')

    def test_fatal_flags_low_fidelity_and_sample_review_held(self):
        self.fixture.receipts['full_review'][AV_FATAL_FLAGS[0]] = True
        self.fixture.seal()
        self.assertHeld('fatal flags')
        self.fixture.receipts['full_review'][AV_FATAL_FLAGS[0]] = False
        self.fixture.receipts['full_review']['content_checks']['asr_manuscript_score'] = 9.69
        self.fixture.seal()
        self.assertHeld('source fidelity')
        self.fixture.receipts['full_review']['scope'] = 'sample'
        self.fixture.seal()
        self.assertHeld('complete final')

    def test_missing_av_music_rights_or_owner_decision_held(self):
        del self.fixture.receipts['rights']['clearances']['music_synchronization']
        self.fixture.seal()
        self.assertHeld('complete audiovisual')

    def test_final_destination_decision_is_not_inferred_from_review(self):
        self.fixture.receipts['decision']['decision'] = 'PRIVATE_REVIEW'
        self.fixture.seal()
        self.assertHeld('explicit owner action')

    def test_arbitrary_technical_pass_and_changed_receipt_held(self):
        self.fixture.receipts['technical'] = {'status': 'PASS'}
        self.fixture.seal()
        self.assertHeld('measured technical')

    def test_captionless_private_render_cannot_qualify_production_route(self):
        self.lineage.stop()
        with patch('scripts.book_av_render.validate', return_value={
            'fixture_mode': False, 'manuscript': {'language': 'bn'}, 'territory': 'IN', 'captions': False,
        }):
            self.assertHeld('requires measured readable captions')

    def test_sidecars_without_verified_consumer_remain_held(self):
        del self.fixture.receipts['full_review']['caption_delivery']
        self.fixture.seal()
        self.assertHeld('delivery consumer')

    def test_existing_audio_promoter_cannot_claim_video_live(self):
        report = {'release_status': 'READY_FOR_GO_LIVE', 'manifest_sha256': canonical_hash(self.fixture.manifest)}
        with self.assertRaisesRegex(ValueError, 'video destination adapter'):
            execute_go_live(report, self.fixture.manifest, None, None, self.root / 'receipt')

    def test_direct_runtime_promoter_cannot_bypass_av_adapter(self):
        from scripts.release_runtime import promote, RuntimeBlocked
        from unittest.mock import Mock
        promoter = Mock()
        with self.assertRaisesRegex(RuntimeBlocked, 'video destination adapter'):
            promote(self.fixture.manifest, {}, execute=True, promoter=promoter)
        promoter.promote.assert_not_called()

    def test_optional_av_gate_is_part_of_existing_governor(self):
        with patch('scripts.produce_release.audiovisual_acceptance', return_value={'status': 'BLOCKED', 'blockers': ['missing final AV review']}):
            result = evaluate(self.fixture.manifest, self.root, None, None)
        self.assertEqual(result['release_status'], 'BLOCKED')
        self.assertEqual(result['audiovisual']['blockers'], ['missing final AV review'])


class BookAVPlannerTests(unittest.TestCase):
    def test_owner_revision_and_resolution_do_not_cross_languages(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);en=root/'en.mp3';bn=root/'bn.mp3'
            en.write_bytes(b'English retained');bn.write_bytes(b'Bengali retained')
            history=root/'history.json'
            revision={'schema':'earnalism.book_av_owner_revision.v1','source':'human',
                      'source_ref':'English-edition owner feedback','status':'ACTIVE',
                      'required_changes':['narration'],'narration_requirement':'Cedar Indian English'}
            records={'en':{'title':'A Book','language':'en','candidate_path':str(en),'candidate_sha256':digest(en)},
                     'bn':{'title':'A Book','language':'bn','candidate_path':str(bn),'candidate_sha256':digest(bn)},
                     'en_revision':{'title':'A Book','language':'en','at':'2026-11-14T09:00:00Z',
                                    'owner_revision':revision}}
            history.write_text(json.dumps(records))
            packet=plan('A Book',history,'bn')
            self.assertEqual(packet['preferred_retained_candidate']['sha256'],digest(bn))
            self.assertIsNone(packet['current_owner_revision'])
            self.assertEqual(plan('A Book',history,'en')['state'],'OWNER_REVISION_REQUIRED')
            records['bn_revision']={'title':'A Book','language':'bn','at':'2026-11-14T08:00:00Z',
                                    'owner_revision':{**revision,'source_ref':'Bengali-edition owner feedback',
                                                      'narration_requirement':'Selected Bengali narrator'}}
            records['en_revision']['owner_revision']={**revision,'status':'RESOLVED'}
            history.write_text(json.dumps(records))
            packet=plan('A Book',history,'bn')
            self.assertEqual(packet['state'],'OWNER_REVISION_REQUIRED')
            self.assertEqual(packet['current_owner_revision']['record'],'history.bn_revision')
            self.assertEqual(packet['current_owner_revision']['language'],'bn')
            self.assertIsNone(packet['preferred_retained_candidate'])
            self.assertEqual(plan('A Book',history,'en')['preferred_retained_candidate']['sha256'],digest(en))

    def test_generic_owner_revision_needs_explicit_or_unambiguous_language_context(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);en=root/'en.mp3';bn=root/'bn.mp3'
            en.write_bytes(b'English retained');bn.write_bytes(b'Bengali retained')
            history=root/'history.json'
            revision={'schema':'earnalism.book_av_owner_revision.v1','source':'human',
                      'source_ref':'English owner feedback','status':'ACTIVE','language':'en',
                      'required_changes':['narration']}
            records={'en':{'title':'A Book','language':'en','candidate_path':str(en),'candidate_sha256':digest(en)},
                     'bn':{'title':'A Book','language':'bn','candidate_path':str(bn),'candidate_sha256':digest(bn)},
                     'revision':{'title':'A Book','at':'2026-11-14T09:00:00Z','owner_revision':revision}}
            history.write_text(json.dumps(records))
            self.assertEqual(plan('A Book',history,'en')['state'],'OWNER_REVISION_REQUIRED')
            self.assertIsNotNone(plan('A Book',history,'bn')['preferred_retained_candidate'])
            records['revision']['owner_revision'].pop('language')
            history.write_text(json.dumps(records))
            self.assertIsNone(plan('A Book',history,'bn')['current_owner_revision'])
            records.pop('bn')
            history.write_text(json.dumps(records))
            self.assertEqual(plan('A Book',history,'en')['state'],'OWNER_REVISION_REQUIRED')
            self.assertEqual(plan('A Book',history,'en')['current_owner_revision']['language'],'en')
            records['revision']['language']='bn'
            records['revision']['owner_revision']['language']='en'
            history.write_text(json.dumps(records))
            with self.assertRaisesRegex(ValueError,'language conflicts'):
                plan('A Book',history,'en')

    def test_active_owner_revision_supersedes_matching_old_narration_without_deleting_it(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);audio=root/'old.mp3';audio.write_bytes(b'retained but owner rejected')
            history=root/'history.json'
            records={'prior':{'title':'A Book','date':'2026-11-13','language':'en',
                              'candidate_path':str(audio),'candidate_sha256':digest(audio)},
                     'revision':{'title':'A Book','at':'2026-11-14T09:00:00Z','language':'en',
                       'owner_revision':{'schema':'earnalism.book_av_owner_revision.v1','source':'human',
                         'source_ref':'owner message','status':'ACTIVE','required_changes':['narration','visual'],
                         'narration_requirement':'Indian English, exclude Voice B'}}}
            history.write_text(json.dumps(records))
            packet=plan('A Book',history,'en')
            self.assertIsNone(packet['preferred_retained_candidate'])
            self.assertEqual(packet['state'],'OWNER_REVISION_REQUIRED')
            self.assertTrue(packet['retained_candidates'][0]['retained_bytes_verified'])
            self.assertIn('HISTORICAL_ONLY',packet['retained_candidates'][0]['reuse_disposition'])
            self.assertIn('Indian English',packet['current_owner_revision']['narration_requirement'])
            self.assertIn('replacement narration',packet['next_generated_prompt'])
            self.assertIn('rebuild the scored mix',packet['actions'][2]['action'])
            self.assertEqual(audio.read_bytes(),b'retained but owner rejected')
            # A later explicit resolution ends this hold without erasing history.
            records['resolution']={'title':'A Book','at':'2026-11-14T10:00:00Z',
                                   'owner_revision':{**records['revision']['owner_revision'],'status':'RESOLVED'}}
            history.write_text(json.dumps(records))
            packet=plan('A Book',history,'en')
            self.assertIsNotNone(packet['preferred_retained_candidate'])
            self.assertNotIn('replacement narration',packet['next_generated_prompt'])

    def test_visual_only_revision_preserves_narration_and_nonhuman_claim_cannot_override_owner(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);audio=root/'old.mp3';audio.write_bytes(b'unchanged narration')
            history=root/'history.json'
            records={'prior':{'title':'A Book','language':'en','candidate_path':str(audio),'candidate_sha256':digest(audio)},
                     'revision':{'title':'A Book','date':'2026-11-14',
                       'owner_revision':{'schema':'earnalism.book_av_owner_revision.v1','source':'human',
                         'source_ref':'owner message','status':'ACTIVE','required_changes':['visual']}}}
            history.write_text(json.dumps(records))
            packet=plan('A Book',history,'en')
            self.assertIsNotNone(packet['preferred_retained_candidate'])
            self.assertNotIn('replacement narration',packet['next_generated_prompt'])
            self.assertIn('Reuse qualified scored edition',packet['actions'][2]['action'])
            records['revision']['owner_revision']['source']='automatic'
            history.write_text(json.dumps(records))
            with self.assertRaisesRegex(ValueError,'explicit human source'):
                plan('A Book',history,'en')

    def test_caption_feedback_keeps_unchanged_audio_evidence(self):
        record = feedback({'candidate_sha256': 'a'*64, 'source': 'automatic',
            'source_ref': 'synthetic private-player contract test; not owner feedback',
            'scope': '00:30-00:35', 'area': 'captions', 'finding': 'caption obscures the subject',
            'fix': 'reflow caption display', 'preserve': 'all narration, scoring and source timing'})
        self.assertIn('caption_delivery', record['affected_evidence'])
        self.assertNotIn('fidelity', record['affected_evidence'])
        self.assertNotIn('soundtrack_listening', record['affected_evidence'])
        self.assertFalse(record['acceptance_created'])

    def test_bengali_marks_remain_distinct(self):
        self.assertNotEqual(title_key('কাল'), title_key('কুল'))

    def test_bilingual_alias_newest_real_candidate_and_language_qualification(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            history = root / 'history.json'
            old, new = root / 'old.mp3', root / 'new.mp3'
            old.write_bytes(b'old'); new.write_bytes(b'new')
            history.write_text(json.dumps({
                'older': {'title': 'বিচারক', 'date': '2026-11-12', 'candidate_path': str(old), 'candidate_sha256': digest(old)},
                'latest': {'title': 'Bicharak / বিচারক', 'date': '2026-11-13', 'candidate_path': str(new), 'resulting_candidate_sha256': digest(new)},
                'different': {'title': 'কাল', 'candidate_path': str(new), 'candidate_sha256': digest(new)},
            }, ensure_ascii=False))
            for title in ('Bicharak', 'বিচারক'):
                packet = plan(title, history, 'bn')
                self.assertEqual(packet['preferred_retained_candidate']['sha256'], digest(new))
                self.assertFalse(packet['acceptance_created'])
                self.assertEqual(packet['provider_calls'], 0)
            self.assertIsNone(plan('Bicharak', history, 'en')['preferred_retained_candidate'])
            self.assertEqual(plan('কুল', history)['retained_candidates'], [])

    def test_changed_candidate_not_selected_and_feedback_does_not_approve(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            path = root / 'audio.mp3'; path.write_bytes(b'old')
            history = root / 'history.json'
            history.write_text(json.dumps({'r': {'title': 'A Book', 'candidate_path': str(path), 'candidate_sha256': digest(path)}}))
            path.write_bytes(b'changed')
            self.assertIsNone(plan('A Book', history)['preferred_retained_candidate'])
            record = feedback({'candidate_sha256': 'a'*64, 'source': 'human', 'source_ref': 'owner-message',
                'scope': '00:30-00:35', 'area': 'score', 'finding': 'abrupt entry', 'fix': 'soften entry', 'preserve': 'narration and surrounding score'})
            self.assertIn('soundtrack_listening', record['affected_evidence'])
            self.assertFalse(record['acceptance_created'])
            self.assertFalse(record['model_weights_trained'])
            output = root / 'feedback.json'
            write_private_new(output, record)
            with self.assertRaises(FileExistsError):
                write_private_new(output, record)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'local FFmpeg required')
class BookAVSoundtrackTests(unittest.TestCase):
    def test_actual_source_master_encoded_payload_lineage_and_tamper_rejection(self):
        # Reuse the explicit synthetic media fixture; test only the technical
        # helper, never manufacture a production acceptance or listening score.
        from scripts.test_book_av_render import BookAVRenderTests
        from scripts.book_av_render import render, validate
        from scripts.release_acceptance import _av_soundtrack_lineage
        fixture = BookAVRenderTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        report = render(fixture.path, fixture.root / 'lineage-test')
        job = validate(fixture.path)
        paths = {'scored_audio': Path(job['scored_audio']['path'])}
        _av_soundtrack_lineage(job, paths, report, fixture.root, 1000)
        self.assertTrue(report['fixture_mode'])
        self.assertFalse(report['release_approved'])
        from scripts.test_book_av_render import media
        silent = fixture.root / 'same-duration-silent.mp4'
        media(['-i', report['outputs'][0]['path'], '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo',
               '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-t', '4', str(silent)])
        original_output = copy.deepcopy(report['outputs'][0])
        report['outputs'][0].update(path=str(silent), sha256=digest(silent))
        with self.assertRaisesRegex(ValueError, 'does not contain the verified soundtrack'):
            _av_soundtrack_lineage(job, paths, report, fixture.root, 1000)
        report['outputs'][0] = original_output
        master = Path(report['soundtrack']['path'])
        import wave
        with wave.open(str(master), 'rb') as source:
            parameters, frames = source.getparams(), source.readframes(source.getnframes())
        with wave.open(str(master), 'wb') as target:
            target.setparams(parameters)
            target.writeframes(bytes(600) + frames[600:])
        report['soundtrack']['sha256'] = digest(master)
        with self.assertRaisesRegex(ValueError, 'changed the scored narration body'):
            _av_soundtrack_lineage(job, paths, report, fixture.root, 1000)


if __name__ == '__main__':
    unittest.main()
