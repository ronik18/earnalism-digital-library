import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from production_journal import NAME, append_work, append_observation, summarize, sha


class ProductionJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        (self.folder / 'episode.json').write_text(json.dumps({'topic': 'Moon'}))
        (self.folder / 'analytics.csv').write_text('video,views\nabcDE123_-0,100\n')

    def work(self, event='edit-1', **values):
        return {'event_id': event, 'activity': 'Repair a diagram label',
                'actual_human_minutes': 12, 'actual_compute_minutes': None,
                'actual_compute_units': None, 'actual_cost': None, **values}

    def observation(self, event='48h-landscape', **values):
        end = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
        return {'event_id': event, 'platform_video_id': 'abcDE123_-0',
                'format': 'landscape', 'checkpoint': '48h',
                'captured_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                'period': {'start': (end - dt.timedelta(days=2)).isoformat(), 'end': end.isoformat()},
                'traffic_source': 'Browse features', 'basis': 'observed',
                'denominator': '1000 registered thumbnail impressions',
                'context': 'Actual exported Studio report; small sample, no causal attribution',
                'metrics': {'impressions': 1000, 'views': 100, 'ctr_percent': 10, 'revenue': None},
                'evidence': {'path': 'analytics.csv', 'sha256': sha(self.folder / 'analytics.csv')},
                **values}

    def test_empty_results_and_missing_costs_remain_unknown(self):
        result = summarize(self.folder)
        self.assertEqual(result['status'], 'AUDIENCE_RESULTS_UNKNOWN')
        self.assertEqual(result['observations'], [])
        self.assertIsNone(result['work']['actual_human_minutes']['known_total'])
        self.assertEqual(result['work']['actual_cost_by_currency'], {})
        self.assertFalse((self.folder / NAME).exists())

    def test_append_keeps_previous_bytes_and_automatic_provenance(self):
        first = append_work(self.folder, self.work())
        prefix = (self.folder / NAME).read_bytes()
        (self.folder / 'delivery-manifest.json').write_text('{"video.mp4":"example"}')
        second = append_work(self.folder, self.work('render-2'))
        self.assertTrue((self.folder / NAME).read_bytes().startswith(prefix))
        self.assertEqual(first['episode_sha256'], sha(self.folder / 'episode.json'))
        self.assertIsNone(first['delivery_manifest_sha256'])
        self.assertEqual(second['delivery_manifest_sha256'], sha(self.folder / 'delivery-manifest.json'))
        self.assertFalse(second['budget_is_spending_authorization'])

    def test_unknown_is_distinct_from_recorded_zero_and_currencies_stay_separate(self):
        append_work(self.folder, self.work(actual_human_minutes=None, actual_cost=2, currency='USD', budget={'cost': 10, 'currency': 'USD'}))
        append_work(self.folder, self.work('another', actual_human_minutes=0, actual_cost=100, currency='INR'))
        result = summarize(self.folder)
        self.assertEqual(result['work']['actual_human_minutes'], {'known_total': 0, 'unknown_entries': 1, 'recorded_entries': 2})
        costs = result['work']['actual_cost_by_currency']
        self.assertEqual(costs['USD']['known_total'], 2)
        self.assertEqual(costs['INR']['known_total'], 100)
        self.assertFalse(result['budget_is_spending_authorization'])

    def test_duplicate_or_damaged_journal_never_resets_history(self):
        append_work(self.folder, self.work())
        journal = self.folder / NAME
        before = journal.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            append_work(self.folder, self.work())
        self.assertEqual(journal.read_bytes(), before)
        with journal.open('ab') as stream:
            stream.write(b'{partial')
        damaged = journal.read_bytes()
        with self.assertRaisesRegex(ValueError, 'damaged'):
            append_work(self.folder, self.work('new'))
        self.assertEqual(journal.read_bytes(), damaged)

    def test_actual_observation_retains_unknown_revenue_and_evidence(self):
        row = append_observation(self.folder, self.observation())
        self.assertEqual(row['record']['metrics']['views'], 100)
        result = summarize(self.folder)
        self.assertIsNone(result['observations'][0]['record']['metrics']['revenue'])
        self.assertEqual(result['status'], 'OBSERVATIONS_RECORDED')
        self.assertNotIn('revenue_total', result)

    def test_projection_or_missing_video_identifier_cannot_be_results(self):
        for values in [{'basis': 'projected'}, {'platform_video_id': ''}, {'platform_video_id': 0}, {'context': ''}, {'denominator': ''}]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                append_observation(self.folder, self.observation(**values))
        self.assertFalse((self.folder / NAME).exists())

    def test_changed_evidence_invalidates_observation_and_later_append(self):
        append_observation(self.folder, self.observation())
        before = (self.folder / NAME).read_bytes()
        (self.folder / 'analytics.csv').write_text('modified')
        with self.assertRaisesRegex(ValueError, 'changed observation evidence'):
            summarize(self.folder)
        with self.assertRaises(ValueError):
            append_work(self.folder, self.work())
        self.assertEqual((self.folder / NAME).read_bytes(), before)

    def test_evidence_cannot_escape_by_path_or_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            external = Path(d) / 'external.csv'
            external.write_text('actual input')
            (self.folder / 'link.csv').symlink_to(external)
            for path in [str(external), '../external.csv', 'link.csv']:
                with self.subTest(path=path), self.assertRaises(ValueError):
                    append_observation(self.folder, self.observation(evidence={'path': path, 'sha256': sha(external)}))

    def test_invalid_actual_costs_and_secret_fields_are_rejected(self):
        for values in [{'actual_cost': 1}, {'actual_cost': float('nan')}, {'actual_compute_units': -1}, {'actual_human_minutes': True}, {'token': 'must-never-be-logged'}, {'budget': {'spending_authorization': True}}]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                append_work(self.folder, self.work(**values))
        self.assertFalse((self.folder / NAME).exists())

    def test_metrics_reject_nan_and_future_or_unordered_periods(self):
        future = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)).isoformat()
        for values in [{'metrics': {'views': float('nan')}}, {'metrics': {'views': -1}}, {'metrics': {'stayed_to_watch_percent': 101}}, {'metrics': {'revenue': 1}}, {'captured_at': future}, {'period': {'start': future, 'end': future}}]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                append_observation(self.folder, self.observation(**values))

    def test_historical_bindings_are_visible_and_overlapping_windows_not_summed(self):
        first = append_observation(self.folder, self.observation())
        (self.folder / 'episode.json').write_text('{"topic":"changed Moon edition"}')
        append_observation(self.folder, self.observation('second-window', format='shorts'))
        result = summarize(self.folder)
        self.assertEqual(result['historical_binding_entries'], 1)
        self.assertEqual(result['observations'][0]['episode_sha256'], first['episode_sha256'])
        self.assertEqual(len(result['observations']), 2)
        self.assertTrue(result['observation_aggregation'].startswith('NONE'))

    def test_cli_summary_reports_unknown_without_creating_events(self):
        module = Path(__file__).resolve().parents[1] / 'production_journal.py'
        result = subprocess.run([sys.executable, str(module), 'summary', str(self.folder)], check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout)['event_count'], 0)
        self.assertFalse((self.folder / NAME).exists())

    def test_tampered_prior_authority_marker_or_fields_fail_closed(self):
        row = append_work(self.folder, self.work())
        journal = self.folder / NAME
        row['budget_is_spending_authorization'] = True
        journal.write_text(json.dumps(row) + '\n')
        with self.assertRaisesRegex(ValueError, 'Invalid prior journal'):
            summarize(self.folder)
        row['budget_is_spending_authorization'] = False
        row['token'] = 'unexpected-field'
        journal.write_text(json.dumps(row) + '\n')
        with self.assertRaisesRegex(ValueError, 'Invalid prior journal'):
            append_work(self.folder, self.work('new'))
