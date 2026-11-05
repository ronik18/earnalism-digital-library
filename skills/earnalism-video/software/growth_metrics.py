"""Optional descriptive analytics; never a release gate, ranking or causal test.

JSON: {"observations": [{"platform": "instagram"|"youtube", "format":
"reel"|"shorts"|"landscape", "video_id": str, "captured_at": aware ISO,
"window_start": aware ISO, "window_end": aware ISO, "window_label": str,
"age_hours": number|null, "duration_seconds": number|null,
"followers_at_publish": number|null, "status": "public"|"private",
"public_started_at": optional aware ISO, "window_kind": optional
"variable_age"|"rolling"|"fixed_age", "window_hours": positive for fixed_age,
"window_origin": "public_release" required for fixed_age comparison,
"source": str, "evidence": str, "metric_definition": optional str,
"traffic_source": optional str, "metrics": {name: number|null}}],
"comparisons": optional [{"left": index, "right": index, "metric": name}]}.
At least an exact window pair OR window_label is required. Each observation
contains one asset/report scope: never mix windows or substitute viewers for
reach. Age is since public release, not upload. Only subscribers_net_change
and followers_net_change allow signed values; neither is gained attribution.
Known first-public/capture timestamps supply the effective age; any reported age
is retained and a material contradiction blocks a comparison. Exact fixed-age
endpoints, when supplied with first-public time, must match the declared origin
and length. Missing timestamp evidence remains unknown, not certified.
Derived prepublic_overlap is null when either required timestamp is missing;
false means only no overlap detected from recorded timestamps, never QA-free
traffic. Instagram sends/shares stay distinct. Impression yield requires native
watch time from registered impressions, not total video watch time.
Nulls remain unknown. Bands/age tolerance are coarse controls, not full
matching, platform algorithms, statistical adjustment or universal benchmarks.
"""
import argparse
import copy
import datetime as dt
import json
import math
from pathlib import Path


def _number(value, name, signed=False):
    if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                              or not math.isfinite(value) or (not signed and value < 0)):
        raise ValueError(f'{name}: finite {"signed" if signed else "nonnegative"} number or null required')
    return value


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name}: nonblank text required')
    return value


def _stamp(value):
    try:
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed
    except (ValueError, TypeError, AttributeError):
        raise ValueError('Timezone-aware ISO timestamp required')


def _band(value, limits):
    if value is None:
        return None
    return next((i for i, edge in enumerate(limits) if value < edge), len(limits))


def _ratio(metrics, numerator, denominator, scale):
    n, d = metrics.get(numerator), metrics.get(denominator)
    if n is None or d is None or d == 0:
        return None
    return _number(scale * n / d, numerator + '/' + denominator)


def _observation(raw):
    if not isinstance(raw, dict):
        raise ValueError('Observation object required')
    row = copy.deepcopy(raw)
    if (row.get('platform'), row.get('format')) not in {
            ('instagram', 'reel'), ('youtube', 'shorts'), ('youtube', 'landscape')}:
        raise ValueError('Unsupported platform/format combination')
    if row.get('status') not in {'public', 'private'}:
        raise ValueError('Explicit public/private status required')
    for key in ('video_id', 'source', 'evidence'):
        _text(row.get(key), key)
    captured = _stamp(row.get('captured_at'))
    start, end, label = row.get('window_start'), row.get('window_end'), row.get('window_label')
    if (start is None) != (end is None):
        raise ValueError('Both exact window endpoints are required')
    if start is None and label is None:
        raise ValueError('Exact window or native window label required')
    if start is not None and not _stamp(start) <= _stamp(end) <= captured:
        raise ValueError('Window must be ordered and end by capture time')
    public = row.get('public_started_at')
    if public is not None and _stamp(public) > captured:
        raise ValueError('Public release cannot follow capture time')
    row['prepublic_overlap'] = (None if start is None or public is None else
                                _stamp(start) < _stamp(public))
    row['window_kind'] = row.get('window_kind', 'variable_age')
    if row['window_kind'] not in {'variable_age', 'rolling', 'fixed_age'}:
        raise ValueError('Unknown window_kind')
    if row['window_kind'] == 'fixed_age':
        hours = _number(row.get('window_hours'), 'window_hours')
        if hours is None or hours == 0:
            raise ValueError('Fixed age window_hours must be positive')
    elif row.get('window_hours') is not None:
        raise ValueError('window_hours is only for an explicit fixed_age window')
    for key in ('window_label', 'metric_definition', 'traffic_source', 'window_origin'):
        if row.get(key) is not None:
            _text(row[key], key)
    for key in ('age_hours', 'duration_seconds', 'followers_at_publish'):
        row[key] = _number(row.get(key), key)
    row['public_age_hours'] = (None if public is None else
                               (captured - _stamp(public)).total_seconds() / 3600)
    row['effective_age_hours'] = (row['age_hours'] if row['public_age_hours'] is None
                                  else row['public_age_hours'])
    row['time_context_flags'] = []
    if row['public_age_hours'] is not None and row['age_hours'] is not None:
        # This tolerance only accommodates rounded record-keeping. It does not
        # turn differently aged videos into a matched experimental cohort.
        if abs(row['age_hours'] - row['public_age_hours']) > max(.5, .01 * row['public_age_hours']):
            row['time_context_flags'].append('Reported age conflicts with first-public/capture timestamps')
    row['fixed_window_timestamp_check'] = 'NOT_APPLICABLE'
    if row['window_kind'] == 'fixed_age':
        row['fixed_window_timestamp_check'] = 'UNKNOWN_NO_EXACT_ORIGIN_EVIDENCE'
        if public is not None and start is not None:
            origin_gap = abs((_stamp(start) - _stamp(public)).total_seconds())
            end_gap = abs((_stamp(end) - _stamp(public)).total_seconds() - row['window_hours'] * 3600)
            if origin_gap > 1 or end_gap > 1:
                row['time_context_flags'].append('Fixed-age endpoints conflict with first-public origin or declared hours')
                row['fixed_window_timestamp_check'] = 'CONFLICT'
            else:
                row['fixed_window_timestamp_check'] = 'MATCHES_RECORDED_TIMESTAMPS'
    if row['duration_seconds'] == 0:
        raise ValueError('Known duration must be positive')
    metrics = row.get('metrics')
    if not isinstance(metrics, dict):
        raise ValueError('Metrics mapping required')
    for name, value in metrics.items():
        _text(name, 'metric name')
        _number(value, name, signed=name in {'subscribers_net_change', 'followers_net_change'})
    row['included'] = row['status'] == 'public'
    row['comparison_context'] = {
        'duration_band': _band(row['duration_seconds'], (60, 180)),
        'age_band': _band(row['effective_age_hours'], (48, 168, 672)),
        'audience_band': _band(row['followers_at_publish'], (100, 1000, 10000))}
    row['derived'] = {}
    row['limitations'] = ['Descriptive only; no causal winner or reliable precision inferred from small counts.',
                         'Duration/audience bands and age tolerance are coarse controls, not complete matching.']
    if row['prepublic_overlap']:
        row['limitations'].append('Selected window starts before public release; private/QA traffic may overlap.')
    elif row['prepublic_overlap'] is None:
        row['limitations'].append('Prepublic overlap is unknown: exact report-start/first-public timestamp pair unavailable; public-only/QA-free traffic is not certified.')
    row['limitations'].extend(row['time_context_flags'])
    if row['fixed_window_timestamp_check'] == 'UNKNOWN_NO_EXACT_ORIGIN_EVIDENCE':
        row['limitations'].append('Fixed-age origin/length are declared but not checked against exact recorded timestamps.')
    if not row['included']:
        row['limitations'].append('Private observation excluded from growth comparisons.')
        return row
    if row['platform'] == 'instagram':
        for metric in ('likes', 'sends', 'shares', 'saves', 'follows'):
            row['derived'][metric + '_per_1000_reach'] = _ratio(metrics, metric, 'reach', 1000)
        row['limitations'].append('Native sends and shares remain separate; no DM-send inference from aggregate shares.')
    else:
        row['derived']['subscribers_per_1000_engaged_views'] = _ratio(metrics, 'subscribers_gained', 'engaged_views', 1000)
        row['derived']['subscribers_per_1000_views_proxy'] = _ratio(metrics, 'subscribers_gained', 'views', 1000)
        source = (row.get('traffic_source') or '').casefold().replace('_', ' ')
        eligible_ctr = bool(source) and 'shorts feed' not in source
        ctr = _ratio(metrics, 'thumbnail_clicks', 'thumbnail_impressions', 100) if eligible_ctr else None
        if ctr is not None and ctr > 100:
            raise ValueError('Thumbnail clicks exceed registered thumbnail impressions')
        row['derived']['thumbnail_ctr_percent'] = ctr
        row['derived']['watch_seconds_per_registered_impression'] = (
            _ratio(metrics, 'impression_watch_time_seconds', 'thumbnail_impressions', 1)
            if eligible_ctr else None)
        row['limitations'].append('Raw-view subscriber rate is a proxy; thumbnail CTR excludes Shorts feed/unknown source.')
        row['limitations'].append('Impression watch-time yield uses only watch time explicitly attributed to registered impressions, never total video watch time.')
    avd, duration = metrics.get('average_view_duration_seconds'), row['duration_seconds']
    row['derived']['repeat_inclusive_watch_percent'] = None if avd is None or duration is None else _number(100 * avd / duration, 'watch percent')
    row['limitations'].append('Watch percentage can exceed100%; it is not completion probability or unique retention.')
    return row


def _compare(request, observations):
    if not isinstance(request, dict) or set(request) != {'left', 'right', 'metric'}:
        raise ValueError('Comparison needs left/right indices and metric')
    for key in ('left', 'right'):
        if isinstance(request[key], bool) or not isinstance(request[key], int) or not 0 <= request[key] < len(observations):
            raise ValueError('Comparison observation index out of range')
    _text(request['metric'], 'comparison metric')
    a, b = (observations[request[k]] for k in ('left', 'right'))
    blockers = []
    if not a['included'] or not b['included']:
        blockers.append('Private observations excluded')
    if a['prepublic_overlap'] or b['prepublic_overlap']:
        blockers.append('Prepublic overlap in selected window')
    for side, row in (('left', a), ('right', b)):
        blockers.extend(side + ': ' + flag for flag in row['time_context_flags'])
    for key in ('platform', 'format', 'window_label', 'metric_definition', 'traffic_source', 'window_kind'):
        if a.get(key) is None or b.get(key) is None or a.get(key) != b.get(key):
            blockers.append('Missing or mismatched ' + key)
    fixed = a['window_kind'] == b['window_kind'] == 'fixed_age'
    for key in ('duration_band', 'audience_band') + (() if fixed else ('age_band',)):
        x, y = a['comparison_context'][key], b['comparison_context'][key]
        if x is None or y is None or x != y:
            blockers.append('Missing or mismatched ' + key)
    if fixed:
        if a.get('window_origin') != 'public_release' or b.get('window_origin') != 'public_release':
            blockers.append('Fixed age requires explicit public_release origin')
        if a['window_hours'] != b['window_hours']:
            blockers.append('Mismatched fixed window_hours')
        if any(r['effective_age_hours'] is None or r['effective_age_hours'] < r['window_hours'] for r in (a, b)):
            blockers.append('Fixed age window not mature or age unknown')
    elif a['effective_age_hours'] is not None and b['effective_age_hours'] is not None:
        if abs(a['effective_age_hours'] - b['effective_age_hours']) > max(2, .1 * min(a['effective_age_hours'], b['effective_age_hours'])):
            blockers.append('Publication age tolerance exceeded')
    if a['window_kind'] == b['window_kind'] == 'rolling' and (a.get('window_start') or b.get('window_start')):
        if any(r.get('window_start') is None for r in (a, b)) or any(
                _stamp(a[k]) != _stamp(b[k]) for k in ('window_start', 'window_end')):
            blockers.append('Missing or mismatched rolling window endpoints')
    name = request['metric']
    values = [r['derived'].get(name, r['metrics'].get(name)) for r in (a, b)]
    if any(v is None for v in values):
        blockers.append('Requested metric unavailable')
    result = {**request, 'comparable': not blockers, 'blockers': blockers,
              'values': values, 'delta': None, 'relative_change_percent': None,
              'prepublic_window_scope_known': all(r['prepublic_overlap'] is not None for r in (a, b)),
              'window_scope_note': 'Coarse descriptive matching does not certify public-only or QA-free counters.',
              'decision': 'No automatic adoption, winner or causal inference'}
    if not blockers:
        result['delta'] = values[1] - values[0]
        result['relative_change_percent'] = None if values[0] <= 0 else 100 * result['delta'] / values[0]
    return result


def analyze(data):
    if not isinstance(data, dict) or not isinstance(data.get('observations'), list):
        raise ValueError('Observations list required')
    rows = [_observation(row) for row in data['observations']]
    comparisons = data.get('comparisons', [])
    if not isinstance(comparisons, list):
        raise ValueError('Comparisons list required')
    return {'schema': 'earnalism.growth-metrics.v1', 'state': 'DESCRIPTIVE_ONLY',
            'observations': rows, 'comparisons': [_compare(c, rows) for c in comparisons],
            'scope': 'Exact native denominators, no automatic release/adoption or revenue forecast; source authenticity not certified.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['analyze'])
    parser.add_argument('data', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = json.dumps(analyze(json.loads(args.data.read_text())), indent=2, allow_nan=False) + '\n'
        if args.output:
            with args.output.open('x') as stream:
                stream.write(result)
        else:
            print(result, end='')
    except (OSError, ValueError, TypeError) as error:
        parser.exit(2, str(error) + '\n')


if __name__ == '__main__':
    main()
