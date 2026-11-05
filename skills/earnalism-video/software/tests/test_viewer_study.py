"""Synthetic unit fixtures only; never real audience responses or release approvals."""
import base64
import copy
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from viewer_study import NAME, pending, reset, validate, sha


class ViewerStudyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        (self.folder / 'episode.json').write_text('{"topic":"Moon fixture"}')
        (self.folder / 'fixture.mp4').write_bytes(b'synthetic fixture, not narrated media')
        (self.folder / 'delivery-manifest.json').write_text(json.dumps({'episode.json': sha(self.folder / 'episode.json'), 'fixture.mp4': sha(self.folder / 'fixture.mp4')}))
        (self.folder / 'card.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jIZkAAAAASUVORK5CYII='))
        self.cards = [{'id': name, 'role': role, 'title': title,
                       'asset': {'path': 'card.png', 'sha256': sha(self.folder / 'card.png')},
                       'rights_note': 'Creator-owned synthetic test fixture, no competitor asset.'}
                      for name, role, title in [('a', 'candidate', 'Round Moon?'), ('b', 'candidate', 'Same Moon?'), ('c', 'distractor', 'A different fixture topic')]]

    def person(self, ident='P01', order=None, choice='a', **values):
        return {'id': ident, 'first_time': True, 'response_kind': 'actual_human',
                'shown_order': order or ['a', 'b', 'c'], 'actual_selected_card': choice,
                'verbatim_reason': '  Exact raw fixture response — keep spacing.  ',
                'expected_payoff': 'I expect a visual explanation of the crescent.', **values}

    def reviewed(self):
        row = pending(self.folder, self.cards)
        row.update(status='PASS', reviewer='Unit fixture reviewer', human_confirmed=True,
                   reviewed_at=dt.datetime.now(dt.timezone.utc).isoformat())
        row['protocol'].update(no_coaching_before_selection=True, no_answers_before_selection=True,
                               order_method='limited', order_limitation='One fixed order; descriptive pilot only.')
        row['participants'] = [self.person()]
        return row

    def test_pending_is_empty_unknown_and_never_approval(self):
        record = pending(self.folder, self.cards)
        self.assertEqual(record['status'], 'PENDING')
        self.assertEqual(record['participants'], [])
        self.assertEqual(record['delivery_manifest_sha256'], sha(self.folder / 'delivery-manifest.json'))
        self.assertNotIn('choice_counts', record)
        with self.assertRaisesRegex(ValueError, 'pending'):
            validate(self.folder, record)

    def test_actual_choices_are_descriptive_and_raw_responses_unchanged(self):
        record = self.reviewed()
        before = copy.deepcopy(record)
        result = validate(self.folder, record)
        self.assertEqual(record, before)
        self.assertEqual(result['choice_counts'], {'a': 1, 'b': 0, 'c': 0, 'none': 0})
        self.assertEqual(result['postwatch_completion_counts']['unknown'], 1)
        self.assertFalse(result['publication_approval'])
        self.assertFalse(result['causal_proof'])
        self.assertFalse(result['growth_or_revenue_prediction'])

    def test_missing_people_or_self_score_cannot_supply_feedback(self):
        record = self.reviewed()
        record['participants'] = []
        record['self_score'] = 10
        with self.assertRaisesRegex(ValueError, 'Actual participant'):
            validate(self.folder, record)
        record['participants'] = [self.person(response_kind='simulated_top_three_global_viewer')]
        with self.assertRaisesRegex(ValueError, 'Actual human'):
            validate(self.folder, record)

    def test_unknown_choice_rejected_and_explicit_none_counted(self):
        record = self.reviewed()
        record['participants'][0]['actual_selected_card'] = 'unshown'
        with self.assertRaisesRegex(ValueError, 'Actual choice'):
            validate(self.folder, record)
        record['participants'][0]['actual_selected_card'] = None
        with self.assertRaises(ValueError):
            validate(self.folder, record)
        record['participants'][0]['actual_selected_card'] = 'none'
        self.assertEqual(validate(self.folder, record)['choice_counts']['none'], 1)

    def test_duplicate_ids_and_personal_identity_fields_rejected(self):
        record = self.reviewed()
        record['participants'].append(self.person())
        with self.assertRaisesRegex(ValueError, 'anonymous'):
            validate(self.folder, record)
        record['participants'] = [self.person(name='Real name must not be collected')]
        with self.assertRaisesRegex(ValueError, 'anonymous actual-response'):
            validate(self.folder, record)

    def test_card_assets_and_titles_bind_study(self):
        record = self.reviewed()
        record['cards'][0]['title'] = 'Altered title'
        with self.assertRaisesRegex(ValueError, 'cards changed'):
            validate(self.folder, record)
        record = self.reviewed()
        (self.folder / 'card.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'card image'):
            validate(self.folder, record)

    def test_delivery_or_manifest_change_invalidates_study(self):
        record = self.reviewed()
        (self.folder / 'fixture.mp4').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Delivery changed'):
            validate(self.folder, record)
        (self.folder / 'delivery-manifest.json').write_text(json.dumps({'episode.json': sha(self.folder / 'episode.json')}))
        with self.assertRaisesRegex(ValueError, 'Stale viewer-study'):
            validate(self.folder, record)

    def test_owned_distractor_and_two_distinct_variants_required(self):
        for cards in [self.cards[:2], [dict(card, role='candidate') for card in self.cards], [self.cards[0], dict(self.cards[0], id='b'), self.cards[2]]]:
            with self.subTest(cards=cards), self.assertRaises(ValueError):
                pending(self.folder, cards)
        bad = copy.deepcopy(self.cards)
        bad[2]['rights_note'] = ''
        with self.assertRaises(ValueError):
            pending(self.folder, bad)

    def test_card_path_traversal_and_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            external = Path(d) / 'outside.png'
            external.write_bytes((self.folder / 'card.png').read_bytes())
            (self.folder / 'link.png').symlink_to(external)
            for path in [str(external), '../outside.png', 'link.png']:
                bad = copy.deepcopy(self.cards)
                bad[0]['asset']['path'] = path
                with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'inside this candidate'):
                    pending(self.folder, bad)

    def test_counterbalance_requires_observed_order_variation_or_limitation(self):
        record = self.reviewed()
        record['protocol']['order_method'] = 'counterbalanced'
        with self.assertRaisesRegex(ValueError, 'actual different orders'):
            validate(self.folder, record)
        record['participants'].append(self.person('P02', ['a', 'c', 'b']))
        with self.assertRaisesRegex(ValueError, 'unbalanced'):
            validate(self.folder, record)
        record['participants'][1]['shown_order'] = ['b', 'c', 'a']
        self.assertEqual(validate(self.folder, record)['participants'], 2)
        record['protocol'].update(order_method='limited', order_limitation='')
        with self.assertRaisesRegex(ValueError, 'order limitation'):
            validate(self.folder, record)

    def test_coaching_and_answers_before_selection_fail(self):
        for key in ['no_coaching_before_selection', 'no_answers_before_selection']:
            record = self.reviewed()
            record['protocol'][key] = False
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'Neutral choice'):
                validate(self.folder, record)

    def test_human_confirmation_timestamp_and_first_time_required(self):
        record = self.reviewed()
        record['human_confirmed'] = False
        with self.assertRaises(ValueError):
            validate(self.folder, record)
        record = self.reviewed()
        record['reviewed_at'] = '2026-01-01T10:00:00'
        with self.assertRaisesRegex(ValueError, 'Timezone-aware'):
            validate(self.folder, record)
        record = self.reviewed()
        record['participants'][0]['first_time'] = False
        with self.assertRaisesRegex(ValueError, 'first-time'):
            validate(self.folder, record)

    def test_optional_postwatch_has_actual_values_and_unknowns(self):
        record = self.reviewed()
        record['participants'][0]['postwatch'] = {'watched_card_id': 'a', 'completed': False,
                                               'satisfaction': 2, 'next_lesson_intent': 'unsure',
                                               'verbatim_comment': 'I lost the viewpoint transition.'}
        result = validate(self.folder, record)
        self.assertEqual(result['postwatch_completion_counts']['no'], 1)
        self.assertEqual(result['postwatch_satisfaction_counts']['2'], 1)
        self.assertEqual(result['next_lesson_intent_counts']['unsure'], 1)
        record['participants'][0]['postwatch']['satisfaction'] = 10
        with self.assertRaisesRegex(ValueError, '1–5'):
            validate(self.folder, record)

    def test_reset_archives_old_study_without_touching_media(self):
        record = self.reviewed()
        sidecar = self.folder / NAME
        sidecar.write_text(json.dumps(record, indent=2))
        old = sidecar.read_bytes()
        old_hash = sha(sidecar)
        media_hash = sha(self.folder / 'fixture.mp4')
        new = reset(self.folder, self.cards)
        self.assertEqual((self.folder / 'logs/viewer-study-history' / (old_hash + '.json')).read_bytes(), old)
        self.assertEqual(new['status'], 'PENDING')
        self.assertEqual(new['participants'], [])
        self.assertEqual(sha(self.folder / 'fixture.mp4'), media_hash)

    def test_cli_init_remains_pending_and_check_fails_until_real_review(self):
        cards = self.folder / 'cards.json'
        cards.write_text(json.dumps(self.cards))
        module = Path(__file__).resolve().parents[1] / 'viewer_study.py'
        output = subprocess.run([sys.executable, str(module), 'init', str(self.folder), str(cards)], check=True, text=True, capture_output=True)
        self.assertEqual(json.loads(output.stdout)['status'], 'PENDING')
        result = subprocess.run([sys.executable, str(module), 'check', str(self.folder)], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('pending', result.stderr)
