"""Release-boundary regressions; no renders, uploads or approval creation."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from refraction_release import (CRITERIA, PLATFORM_SCHEMA, decision_check, manifest,
                                platform_check, voice_check, facts_check, graphics_check,
                                positioned_caption_check, candidate_identity, check, SCHEMA)

DIGEST = 'a' * 64


def platform():
    return {'schema': PLATFORM_SCHEMA, 'kit_manifest_sha256': DIGEST,
            'reviewer': 'Technical reviewer', 'scope': 'Technical playback; accepted listening reused',
            'unresolved_primary_findings': [],
            'settings': {'audience': 'not_made_for_kids', 'age_restriction': False,
                'video_language': 'English', 'metadata_language': 'English', 'category': 'Education',
                'automatic_dubbing': False, 'visual_enhancements': False, 'audio_enhancements': False,
                'automatic_chapters': False, 'automatic_places': False, 'automatic_concepts': False,
                'paid_promotion': False, 'ai_use': True, 'required_hashtags': True, 'schedule': None},
            'videos': {fmt: {'video_id': vid, 'visibility': 'Private', 'cover_reviewed': True,
                'manual_english_selected': True, 'original_audio': True, 'hd_complete': True,
                'copyright': 'No issues found', 'remixing': remix,
                'playback': {'complete': True, 'seeking': True, 'replay_or_loop': True, 'media_error': None}}
                for fmt, vid, remix in [('landscape', 'AAAAAAAAAAA', 'disabled'),
                                       ('shorts', 'BBBBBBBBBBB', 'audio_only')]}}


class RefractionReleaseTests(unittest.TestCase):
    def test_private_review_is_pending_not_approval(self):
        platform_check(platform(), DIGEST)
        self.assertEqual(decision_check(None, DIGEST), 'PRIMARY_CHECKS_READY_PENDING_OWNER_DECISION')

    def test_one_manifest_bound_owner_decision_covers_primary_criteria(self):
        d = {'schema': 'earnalism.final-owner-decision.v1', 'kit_manifest_sha256': DIGEST,
             'candidate_sha256': 'c' * 64,
             'reviewer': 'Owner', 'source': 'Explicit GO LIVE action', 'approved': True,
             'criteria': sorted(CRITERIA)}
        self.assertEqual(decision_check(d, DIGEST, 'c' * 64), 'APPROVED_CANDIDATE_FOR_AUTHORIZED_PUBLICATION')
        d['kit_manifest_sha256'] = 'b' * 64
        with self.assertRaisesRegex(ValueError, 'consolidated owner'):
            decision_check(d, DIGEST, 'c' * 64)

    def test_partial_or_inferred_owner_decision_rejected(self):
        d = {'schema': 'earnalism.final-owner-decision.v1', 'kit_manifest_sha256': DIGEST,
             'candidate_sha256': 'c' * 64,
             'reviewer': 'Technical reviewer', 'source': 'Tests passed', 'approved': True,
             'criteria': sorted(CRITERIA)}
        with self.assertRaises(ValueError):
            decision_check(d, DIGEST, 'c' * 64)
        d['reviewer'] = 'Owner'; d['criteria'] = ['technical_delivery']
        with self.assertRaises(ValueError):
            decision_check(d, DIGEST, 'c' * 64)

    def test_caption_or_target_change_invalidates_approval_but_recheck_timestamp_does_not(self):
        r = platform(); before = candidate_identity(DIGEST, 'c' * 64, r)
        r['checked_at'] = 'later'; self.assertEqual(before, candidate_identity(DIGEST, 'c' * 64, r))
        self.assertNotEqual(before, candidate_identity(DIGEST, 'd' * 64, r))
        r['videos']['shorts']['video_id'] = 'CCCCCCCCCCC'
        self.assertNotEqual(before, candidate_identity(DIGEST, 'c' * 64, r))

    def test_wrong_manifest_or_public_visibility_rejected(self):
        r = platform()
        with self.assertRaises(ValueError):
            platform_check(r, 'b' * 64)
        r['videos']['shorts']['visibility'] = 'Public'
        with self.assertRaisesRegex(ValueError, 'Private'):
            platform_check(r, DIGEST)
        r = platform(); r['unresolved_primary_findings'] = ['Unresolved caption overlap']
        with self.assertRaisesRegex(ValueError, 'Unresolved primary'): platform_check(r, DIGEST)

    def test_caption_audio_processing_and_playback_defects_block(self):
        mutations = [
            ('videos', 'landscape', 'manual_english_selected', False),
            ('videos', 'shorts', 'original_audio', False),
            ('videos', 'shorts', 'hd_complete', False),
            ('settings', 'automatic_dubbing', True),
            ('settings', 'audio_enhancements', True),
            ('settings', 'automatic_chapters', True),
            ('settings', 'required_hashtags', False),
        ]
        for *keys, value in mutations:
            r = platform(); target = r
            for key in keys[:-1]: target = target[key]
            target[keys[-1]] = value
            with self.subTest(keys=keys), self.assertRaises(ValueError): platform_check(r, DIGEST)
        for key, value in [('complete', False), ('seeking', False), ('replay_or_loop', False),
                           ('media_error', 'decode error')]:
            r = platform(); r['videos']['shorts']['playback'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): platform_check(r, DIGEST)

    def test_changed_cover_and_remixing_and_copyright_block(self):
        for key, value in [('cover_reviewed', False), ('remixing', 'video_audio'),
                           ('copyright', 'Copyright claim')]:
            r = platform(); r['videos']['shorts'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): platform_check(r, DIGEST)

    def test_manifest_detects_changed_member_and_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); folder = root / 'kit'; folder.mkdir(); (folder / 'media').write_bytes(b'accepted')
            entries = {'media': hashlib.sha256(b'accepted').hexdigest()}
            path = folder / 'delivery-manifest.json'; path.write_text(json.dumps(entries))
            rec = {'path': 'kit', 'manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            manifest(root, rec)
            (folder / 'media').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Changed package member'): manifest(root, rec)
            path.write_text(json.dumps({'../outside': DIGEST})); rec['manifest_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, 'escapes project'): manifest(root, rec)

    def test_asr_trace_preserves_source_and_only_documented_spelling_equivalence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'source'; parent = root / 'parent'
            (source / 'imported/raw').mkdir(parents=True); (source / 'imported/alignment').mkdir()
            parent.mkdir(); raw = source / 'imported/raw/s01.wav'; raw.write_bytes(b'original B')
            digest = hashlib.sha256(raw.read_bytes()).hexdigest()
            def save(path, value): path.write_text(json.dumps(value))
            unit = {'id': 's01', 'text': 'Light travelling underwater.'}
            record = {'unit': 's01', 'expected': unit['text'], 'recognized': 'Light traveling underwater.',
                      'audio_sha256': digest, 'differences': [], 'raw_differences': [{'expected': ['travelling'],
                      'recognized': ['traveling']}], 'resolution': {'type': 'orthographic_only', 'audio_sha256': digest}}
            settings = {'text': unit['text'], 'speaker': 'Ryan', 'generation': {'temperature': .85},
                        'instruct': 'Original mature narrator'}
            save(parent / 'units.json', [unit]); save(source / 'asr-review.json', [record])
            save(source / 'imported/alignment/s01.json', {'audio_sha256': digest, 'recognized': record['recognized']})
            save(Path(str(raw) + '.json'), {'wav_sha256': digest, 'settings': settings,
                                          'audio': {'mechanical_checks': 'PASS'}})
            save(parent / 'voice-binding.json', {'raw_audio': {'s01': digest}, 'generation': settings['generation'],
                 'instruction_sha256': hashlib.sha256(settings['instruct'].encode()).hexdigest()})
            save(source / 'baseline-job.json', {'generation': settings['generation']})
            (source / 'narration.wav').write_bytes(b'unchanged'); (parent / 'narration.wav').write_bytes(b'unchanged')
            self.assertEqual(voice_check(source, parent), 1)
            record['resolution'] = None; save(source / 'asr-review.json', [record])
            with self.assertRaisesRegex(ValueError, 'raw ASR'): voice_check(source, parent)
            record['recognized'] = 'Light than underwater.'; save(source / 'asr-review.json', [record])
            with self.assertRaisesRegex(ValueError, 'ASR text'): voice_check(source, parent)
            record['recognized'] = 'Light traveling underwater.'; record['resolution'] = {'type': 'orthographic_only',
                       'audio_sha256': digest}; save(source / 'asr-review.json', [record]); raw.write_bytes(b'new voice')
            with self.assertRaisesRegex(ValueError, 'Source audio'): voice_check(source, parent)

    def test_factual_coverage_cannot_pass_empty_or_unsupported_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = {'sources.json': [{'id': 'S1', 'title': 'Primary source', 'url': 'https://example.test', 'claims': ['claim']}],
                        'research-verification.json': {'claims': [{'finding': 'SUPPORTED', 'support': ['S1']}]},
                        'units.json': [{'id': 's01', 'text': 'Light changes direction.'}],
                        'claim-map.json': [{'unit': 's01', 'text': 'Light changes direction.', 'source_ids': ['S1']}]}
            def reset():
                for name, record in original.items(): (root / name).write_text(json.dumps(record))
            reset(); facts_check(root)
            for name, bad in [('sources.json', []), ('claim-map.json', []),
                              ('research-verification.json', {'claims': []}),
                              ('research-verification.json', {'claims': [{'finding': 'SUPPORTED?', 'support': ['S1']}]}),
                              ('claim-map.json', [{'unit': 's01', 'text': 'Light changes direction.', 'source_ids': []}])]:
                reset(); (root / name).write_text(json.dumps(bad))
                with self.subTest(name=name, bad=bad), self.assertRaises(ValueError): facts_check(root)

    def test_graphical_clearance_requires_current_judgment_not_capture_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); kit = root / 'kit'; parent = root / 'parent'
            (kit / 'assets').mkdir(parents=True); (kit / 'delivery').mkdir(); parent.mkdir()
            (kit / 'delivery/youtube-landscape.mp4').write_bytes(b'landscape')
            (kit / 'assets/youtube-shorts.mp4').write_bytes(b'shorts')
            (root / 'proof.png').write_bytes(b'bound proof')
            (parent / 'final-private-review.json').write_text(json.dumps({'graphics': 'prior encoded review',
                       'browser': {'scope': 'prior checks'}, 'captions': 'actual-audio cues'}))
            digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            r = {'graphics': {fmt: {'source_sha256': digest(kit / path), 'independent_composition': True,
                 'checkpoints_reviewed': ['opening', 'light_path', 'normal', 'virtual_image', 'lift_callback', 'outro'],
                 'narration_sync': True, 'labels_readable': True, 'caption_clearance': True, 'unresolved_findings': [],
                 'evidence': [{'path': 'proof.png', 'sha256': digest(root / 'proof.png')}]}
                 for fmt, path in [('landscape', 'delivery/youtube-landscape.mp4'), ('shorts', 'assets/youtube-shorts.mp4')]}}
            graphics_check(r, root, kit, parent)
            r['graphics']['shorts']['unresolved_findings'] = ['CC overlaps the heading at 41.45 seconds']
            with self.assertRaisesRegex(ValueError, 'graphical/caption'): graphics_check(r, root, kit, parent)
            r['graphics']['shorts']['unresolved_findings'] = []
            r['graphics']['shorts']['caption_clearance'] = False
            with self.assertRaises(ValueError): graphics_check(r, root, kit, parent)

    def test_position_only_caption_repair_preserves_every_text_and_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'captions.vtt'
            text = 'WEBVTT\n\n00:00:01.000 --> 00:00:03.000 line:82% position:50% size:88% align:center\nThe spoon stays straight.\n'
            cues = [{'start': 1, 'end': 3, 'text': 'The spoon stays straight.'}]
            path.write_text(text); positioned_caption_check(path, cues)
            for changed in [text.replace('straight.', 'bent.'), text.replace('03.000', '03.100'),
                            text.replace('line:82%', 'line:100.9%'), text.replace('line:82%', 'line:82% line:2%'),
                            text.replace('size:88%', 'size:0.0%'),
                            'WEBVTT\n']:
                path.write_text(changed)
                with self.subTest(changed=changed), self.assertRaises(ValueError): positioned_caption_check(path, cues)

    def test_positioned_file_requires_actual_platform_verification(self):
        r = platform()
        with self.assertRaisesRegex(ValueError, 'caption delivery'): platform_check(r, DIGEST, 'c' * 64)
        r['videos']['shorts']['caption_delivery_sha256'] = 'c' * 64
        platform_check(r, DIGEST, 'c' * 64)

    def test_ttml_delivery_region_preserves_cues_and_rejects_missing_region_or_timing_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'captions.ttml'
            text = '''<tt xmlns="http://www.w3.org/ns/ttml" xmlns:ttp="http://www.w3.org/ns/ttml#parameter"
                 xmlns:tts="http://www.w3.org/ns/ttml#styling" ttp:timeBase="media"><head><layout>
                 <region xml:id="safe" tts:origin="5% 77%" tts:extent="90% 12%" tts:displayAlign="center"/>
                 </layout></head><body><div><p begin="00:00:01.000" end="00:00:03.000" region="safe">The spoon stays straight.</p></div></body></tt>'''
            cues = [{'start': 1, 'end': 3, 'text': 'The spoon stays straight.'}]
            path.write_text(text); positioned_caption_check(path, cues)
            for changed in [text.replace('region="safe"', 'region="missing"'), text.replace('03.000', '03.100'),
                            text.replace('straight.', 'bent.'), text.replace('77%', '95%'),
                            '<!DOCTYPE tt>' + text]:
                path.write_text(changed)
                with self.subTest(changed=changed), self.assertRaises(ValueError): positioned_caption_check(path, cues)

    def test_ttml_empty_break_preserves_tail_words_and_timing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'captions.ttml'
            text = '''<tt xmlns="http://www.w3.org/ns/ttml" xmlns:ttp="http://www.w3.org/ns/ttml#parameter"
                 xmlns:tts="http://www.w3.org/ns/ttml#styling" ttp:timeBase="media"><head><layout>
                 <region xml:id="safe" tts:origin="5% 69.4%" tts:extent="90% 12%" tts:displayAlign="center"/>
                 </layout></head><body><div><p begin="00:00:01.000" end="00:00:03.000" region="safe">The spoon<br/>stays straight.</p></div></body></tt>'''
            cues = [{'start': 1, 'end': 3, 'text': 'The spoon stays straight.'}]
            path.write_text(text); positioned_caption_check(path, cues)
            path.write_text(text.replace('spoon<br/>stays', 'spoon \n<br/> stays'))
            positioned_caption_check(path, cues)
            for changed in [text.replace('stays straight.', 'stays bent.'),
                            text.replace('stays straight.', ''), text.replace('03.000', '03.100')]:
                path.write_text(changed)
                with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, 'changed caption'):
                    positioned_caption_check(path, cues)

    def test_ttml_break_rejects_attributes_text_nesting_and_other_markup(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'captions.ttml'
            text = '''<tt xmlns="http://www.w3.org/ns/ttml" xmlns:ttp="http://www.w3.org/ns/ttml#parameter"
                 xmlns:tts="http://www.w3.org/ns/ttml#styling" ttp:timeBase="media"><head><layout>
                 <region xml:id="safe" tts:origin="5% 69.4%" tts:extent="90% 12%" tts:displayAlign="center"/>
                 </layout></head><body><div><p begin="00:00:01.000" end="00:00:03.000" region="safe">The spoon<br/>stays straight.</p></div></body></tt>'''
            cues = [{'start': 1, 'end': 3, 'text': 'The spoon stays straight.'}]
            for markup in ['<span/>', '<br tts:color="white"/>', '<br xml:space="preserve"/>',
                           '<br> </br>', '<br>discarded words</br>', '<br><br/></br>',
                           '<br xmlns="urn:other"/>']:
                path.write_text(text.replace('<br/>', markup))
                with self.subTest(markup=markup), self.assertRaisesRegex(ValueError, 'Unsupported TTML cue markup'):
                    positioned_caption_check(path, cues)

    def test_explicit_profile_dispatch_preserves_legacy_fixture_prohibition(self):
        import studio
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); profile = root / 'profile.json'; profile.write_text('{}')
            with patch('refraction_release.check', return_value='PENDING') as adapted:
                self.assertEqual(studio.release_check(profile), 'PENDING')
                adapted.assert_called_once_with(profile.resolve(), studio.BASE.parent)
            legacy = root / 'legacy'; legacy.mkdir(); (legacy / 'episode.json').write_text('{"private_test": true}')
            with self.assertRaisesRegex(ValueError, 'Test fixtures can never publish'): studio.release_check(legacy)
            profile.write_text(json.dumps({'schema': SCHEMA, 'private_test': True}))
            with self.assertRaisesRegex(ValueError, 'Test fixtures can never publish'): check(profile, root)


if __name__ == '__main__':
    unittest.main()
