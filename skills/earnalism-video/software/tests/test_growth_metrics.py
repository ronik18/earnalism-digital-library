import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from growth_metrics import analyze


class GrowthMetricsTests(unittest.TestCase):
    def row(self, **changes):
        row = {'platform': 'instagram', 'format': 'reel', 'video_id': 'reel-1',
               'captured_at': '2026-11-03T18:00:00+05:30', 'window_label': 'First48h',
               'age_hours': 48, 'duration_seconds': 38, 'followers_at_publish': 4,
               'status': 'public', 'source': 'Native Insights', 'evidence': 'capture.txt',
               'metric_definition': 'Native Reach v1', 'traffic_source': 'Organic',
               'metrics': {'views': 100, 'reach': 80, 'shares': 2, 'saves': 4, 'follows': 1}}
        return {**row, **changes}

    def single(self, row):
        return analyze({'observations': [row]})['observations'][0]

    def compare(self, a, b, metric='shares_per_1000_reach'):
        return analyze({'observations': [a, b], 'comparisons': [{'left': 0, 'right': 1, 'metric': metric}]})['comparisons'][0]

    def test_native_reach_rates_preserve_counts_and_do_not_substitute_viewers(self):
        row = self.single(self.row())
        self.assertEqual(row['derived']['shares_per_1000_reach'], 25)
        self.assertEqual(row['derived']['saves_per_1000_reach'], 50)
        self.assertEqual(row['derived']['follows_per_1000_reach'], 12.5)
        self.assertEqual(row['metrics']['reach'], 80)
        raw = self.row(metrics={'views': 100, 'viewers': 80, 'shares': 2})
        self.assertIsNone(self.single(raw)['derived']['shares_per_1000_reach'])

    def test_null_zero_and_blank_are_distinct(self):
        raw = self.row(metrics={'reach': 0, 'shares': 0, 'saves': None, 'follows': None})
        row = self.single(raw)
        self.assertEqual(row['metrics']['shares'], 0)
        self.assertIsNone(row['metrics']['saves'])
        self.assertIsNone(row['derived']['shares_per_1000_reach'])
        self.assertIsNone(row['derived']['follows_per_1000_reach'])
        for bad in ('', '—', True, -1, float('nan'), float('inf')):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.single(self.row(metrics={'views': bad}))

    def test_small_counts_never_become_a_winner_or_pass(self):
        a = self.row(metrics={'reach': 1, 'shares': 1})
        b = self.row(video_id='reel-2', metrics={'reach': 1, 'shares': 2})
        result = self.compare(a, b)
        self.assertTrue(result['comparable'])
        self.assertEqual(result['relative_change_percent'], 100)
        self.assertIn('No automatic', result['decision'])
        self.assertNotIn('winner', result)

    def test_repeat_inclusive_403_percent_is_not_completion_probability(self):
        row = self.single(self.row(duration_seconds=100, metrics={'average_view_duration_seconds': 403}))
        self.assertEqual(row['derived']['repeat_inclusive_watch_percent'], 403)
        self.assertTrue(any('not completion probability' in x for x in row['limitations']))

    def test_youtube_subscriber_denominators_and_ctr_are_separate(self):
        row = self.single(self.row(platform='youtube', format='landscape', traffic_source='Browse',
            metrics={'subscribers_gained': 2, 'engaged_views': 100, 'views': 200,
                     'thumbnail_clicks': 20, 'thumbnail_impressions': 1000}))
        self.assertEqual(row['derived']['subscribers_per_1000_engaged_views'], 20)
        self.assertEqual(row['derived']['subscribers_per_1000_views_proxy'], 10)
        self.assertEqual(row['derived']['thumbnail_ctr_percent'], 2)
        for source in ('Shorts feed', 'shorts_feed', None):
            raw = self.row(platform='youtube', format='shorts', traffic_source=source,
                           metrics={'thumbnail_clicks': 20, 'thumbnail_impressions': 1000})
            self.assertIsNone(self.single(raw)['derived']['thumbnail_ctr_percent'])

    def test_private_is_retained_but_excluded(self):
        private = self.row(status='private')
        self.assertFalse(self.single(private)['included'])
        self.assertEqual(self.single(private)['derived'], {})
        result = self.compare(self.row(), private)
        self.assertFalse(result['comparable'])
        self.assertIn('Private observations excluded', result['blockers'])
        self.assertIsNone(result['delta'])

    def test_scope_and_context_mismatches_block_comparisons(self):
        changes = [{'platform': 'youtube', 'format': 'shorts'}, {'window_label': 'Last30d'},
                   {'metric_definition': 'Different definition'}, {'traffic_source': 'Paid'},
                   {'duration_seconds': 90}, {'age_hours': 5}, {'followers_at_publish': 2000},
                   {'duration_seconds': None}, {'age_hours': None}, {'followers_at_publish': None}]
        for change in changes:
            with self.subTest(change=change):
                result = self.compare(self.row(), self.row(video_id='reel-2', **change))
                self.assertFalse(result['comparable'])
                self.assertTrue(result['blockers'])
                self.assertIsNone(result['delta'])

    def test_timezone_and_ordered_capture_windows(self):
        raw = self.row(window_start='2026-11-01T12:30:00Z', window_end='2026-11-03T12:30:00Z')
        self.single(raw)
        for changes in ({'captured_at': '2026-11-03T18:00:00'},
                        {'window_start': '2026-11-04T00:00:00Z'},
                        {'window_end': '2026-11-04T00:00:00Z'},
                        {'window_end': None}, {'duration_seconds': 0}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.single({**raw, **changes})
        label_only = self.row()
        label_only.pop('window_label')
        with self.assertRaises(ValueError):
            self.single(label_only)

    def test_unknown_metric_or_missing_definition_is_inconclusive(self):
        a = self.row(metric_definition=None)
        result = self.compare(a, self.row(), metric='not_available')
        self.assertFalse(result['comparable'])
        self.assertIn('Requested metric unavailable', result['blockers'])
        self.assertTrue(any('metric_definition' in reason for reason in result['blockers']))

    def test_named_net_losses_are_preserved_but_never_gained_numerators(self):
        row = self.single(self.row(platform='youtube', format='shorts',
            metrics={'subscribers_net_change': -2, 'followers_net_change': -1, 'engaged_views': 100}))
        self.assertEqual(row['metrics']['subscribers_net_change'], -2)
        self.assertIsNone(row['derived']['subscribers_per_1000_engaged_views'])
        self.assertIsNone(row['derived']['subscribers_per_1000_views_proxy'])
        for name in ('subscribers_gained', 'follows', 'net_change', 'views'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.single(self.row(metrics={name: -1}))
        for value in (float('nan'), float('inf'), True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.single(self.row(metrics={'subscribers_net_change': value}))

    def test_variable_age_guard_rejects_five_vs_forty_hours(self):
        result = self.compare(self.row(age_hours=5, window_label='Since published'),
                              self.row(age_hours=40, window_label='Since published'))
        self.assertFalse(result['comparable'])
        self.assertTrue(any('age tolerance' in x for x in result['blockers']))

    def test_fixed_first_day_can_be_captured_later_only_when_mature(self):
        fixed = {'window_kind': 'fixed_age', 'window_hours': 24, 'window_label': 'First24h',
                 'window_origin': 'public_release'}
        mature = self.compare(self.row(age_hours=26, **fixed), self.row(age_hours=200, **fixed))
        self.assertTrue(mature['comparable'], mature['blockers'])
        for changes in ({'age_hours': 23}, {'age_hours': None}, {'window_hours': 48}):
            with self.subTest(changes=changes):
                result = self.compare(self.row(age_hours=26, **fixed),
                                      self.row(**{**fixed, 'age_hours': 200, **changes}))
                self.assertFalse(result['comparable'])
        for hours in (0, -1, None):
            with self.subTest(hours=hours), self.assertRaises(ValueError):
                self.single(self.row(window_kind='fixed_age', window_hours=hours))

    def test_rolling_exact_endpoints_must_match_and_respect_timezone(self):
        window = {'window_kind': 'rolling', 'window_label': 'Last48h',
                  'window_start': '2026-11-01T12:30:00Z', 'window_end': '2026-11-03T12:30:00Z'}
        a = self.row(**window)
        same = self.row(**{**window, 'window_start': '2026-11-01T18:00:00+05:30',
                          'window_end': '2026-11-03T18:00:00+05:30'})
        self.assertTrue(self.compare(a, same)['comparable'])
        b = self.row(**{**window, 'window_start': '2026-11-01T11:30:00Z',
                       'window_end': '2026-11-03T11:30:00Z'})
        result = self.compare(a, b)
        self.assertFalse(result['comparable'])
        self.assertTrue(any('rolling window endpoints' in x for x in result['blockers']))
        self.assertFalse(self.compare(a, self.row(window_kind='rolling', window_label='Last48h'))['comparable'])

    def test_fixed_window_requires_explicit_public_release_origin(self):
        fixed = {'window_kind': 'fixed_age', 'window_hours': 24, 'window_label': 'First24h'}
        for origin in (None, 'upload'):
            with self.subTest(origin=origin):
                result = self.compare(self.row(**fixed), self.row(window_origin=origin, **fixed))
                self.assertFalse(result['comparable'])
                self.assertTrue(any('public_release origin' in x for x in result['blockers']))

    def test_recorded_public_time_derives_age_without_filling_unknown_audience(self):
        raw = self.row(age_hours=None, public_started_at='2026-11-01T18:00:00+05:30')
        row = self.single(raw)
        self.assertIsNone(row['age_hours'])
        self.assertEqual(row['public_age_hours'], 48)
        self.assertEqual(row['effective_age_hours'], 48)
        self.assertEqual(row['time_context_flags'], [])
        self.assertTrue(self.compare(raw, {**raw, 'video_id': 'reel-2'})['comparable'])
        self.assertFalse(self.compare(raw, {**raw, 'followers_at_publish': None})['comparable'])

    def test_contradictory_supplied_age_is_retained_but_cannot_certify_matching(self):
        raw = self.row(age_hours=200, public_started_at='2026-11-01T12:30:00Z')
        row = self.single(raw)
        self.assertEqual(row['age_hours'], 200)
        self.assertEqual(row['effective_age_hours'], 48)
        self.assertTrue(any('Reported age conflicts' in x for x in row['time_context_flags']))
        result = self.compare(raw, {**raw, 'video_id': 'reel-2'})
        self.assertFalse(result['comparable'])
        self.assertIsNone(result['relative_change_percent'])
        rounded = self.single({**raw, 'age_hours': 48.25})
        self.assertEqual(rounded['time_context_flags'], [])

    def test_exact_first_public_window_requires_origin_and_length_not_just_a_label(self):
        fixed = self.row(age_hours=None, window_kind='fixed_age', window_hours=24,
                         window_label='First24h', window_origin='public_release',
                         public_started_at='2026-11-01T12:30:00Z',
                         window_start='2026-11-01T18:00:00+05:30',
                         window_end='2026-11-02T18:00:00+05:30')
        good = self.single(fixed)
        self.assertEqual(good['fixed_window_timestamp_check'], 'MATCHES_RECORDED_TIMESTAMPS')
        self.assertTrue(self.compare(fixed, {**fixed, 'video_id': 'reel-2'})['comparable'])
        for changes in ({'window_end': '2026-11-03T12:30:00Z'},
                        {'window_start': '2026-11-01T18:30:00Z', 'window_end': '2026-11-02T18:30:00Z'}):
            with self.subTest(changes=changes):
                bad = {**fixed, **changes}
                self.assertEqual(self.single(bad)['fixed_window_timestamp_check'], 'CONFLICT')
                result = self.compare(fixed, bad)
                self.assertFalse(result['comparable'])
                self.assertTrue(any('Fixed-age endpoints conflict' in x for x in result['blockers']))
                self.assertIsNone(result['delta'])

    def test_declared_first_public_window_does_not_invent_timestamp_confirmation(self):
        row = self.single(self.row(window_kind='fixed_age', window_hours=24,
                          window_label='First24h', window_origin='public_release'))
        self.assertEqual(row['fixed_window_timestamp_check'], 'UNKNOWN_NO_EXACT_ORIGIN_EVIDENCE')
        self.assertTrue(any('declared but not checked' in x for x in row['limitations']))

    def test_sends_are_not_backfilled_from_shares_and_likes_keep_reach_denominator(self):
        row = self.single(self.row(metrics={'reach': 80, 'likes': 4, 'shares': 8, 'sends': 2}))
        self.assertEqual(row['derived']['likes_per_1000_reach'], 50)
        self.assertEqual(row['derived']['shares_per_1000_reach'], 100)
        self.assertEqual(row['derived']['sends_per_1000_reach'], 25)
        unknown = self.single(self.row(metrics={'reach': 80, 'shares': 8}))
        self.assertIsNone(unknown['derived']['sends_per_1000_reach'])

    def test_impression_watch_time_never_uses_total_video_watch_time(self):
        base = self.row(platform='youtube', format='landscape', traffic_source='Browse',
                        metrics={'thumbnail_impressions': 1000, 'watch_time_seconds': 9000})
        self.assertIsNone(self.single(base)['derived']['watch_seconds_per_registered_impression'])
        metrics = {**base['metrics'], 'impression_watch_time_seconds': 1800}
        self.assertEqual(self.single({**base, 'metrics': metrics})['derived']['watch_seconds_per_registered_impression'], 1.8)
        for source in (None, 'Shorts feed'):
            self.assertIsNone(self.single({**base, 'metrics': metrics, 'traffic_source': source})['derived']['watch_seconds_per_registered_impression'])

    def test_window_before_public_release_is_limited_and_cannot_compare(self):
        raw = self.row(window_start='2026-10-31T12:30:00Z', window_end='2026-11-01T12:30:00Z',
                       public_started_at='2026-11-01T05:50:00Z',
                       window_kind='fixed_age', window_hours=24, window_origin='public_release')
        row = self.single(raw)
        self.assertTrue(row['prepublic_overlap'])
        self.assertTrue(any('before public release' in x for x in row['limitations']))
        result = self.compare(raw, raw)
        self.assertFalse(result['comparable'])
        self.assertTrue(any('Prepublic overlap' in x for x in result['blockers']))

    def test_missing_origin_is_unknown_not_false_or_public_only_certification(self):
        unknown = self.single(self.row())
        self.assertIsNone(unknown['prepublic_overlap'])
        self.assertTrue(any('Prepublic overlap is unknown' in x for x in unknown['limitations']))
        result = self.compare(self.row(), self.row(video_id='reel-2'))
        self.assertFalse(result['prepublic_window_scope_known'])
        self.assertIn('does not certify public-only', result['window_scope_note'])
        known = self.row(public_started_at='2026-11-01T12:30:00Z',
                         window_start='2026-11-01T12:30:00Z', window_end='2026-11-03T12:30:00Z')
        self.assertIs(self.single(known)['prepublic_overlap'], False)
        self.assertTrue(self.compare(known, {**known, 'video_id':'reel-2'})['prepublic_window_scope_known'])

    def test_cli_does_not_overwrite_input_or_existing_output(self):
        script = Path(__file__).resolve().parents[1] / 'growth_metrics.py'
        with tempfile.TemporaryDirectory() as temp:
            source, output = Path(temp)/'data.json', Path(temp)/'result.json'
            source.write_text(json.dumps({'observations': [self.row()]}))
            before = source.read_bytes()
            command = [sys.executable, str(script), 'analyze', str(source), '--output', str(output)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            saved = output.read_bytes()
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(second.returncode, 2)
            self.assertEqual(output.read_bytes(), saved)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(json.loads(saved)['state'], 'DESCRIPTIVE_ONLY')


if __name__ == '__main__':
    unittest.main()
