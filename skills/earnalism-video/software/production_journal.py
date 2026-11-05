"""Append actual episode work and evidenced audience observations; never grants approval.

The JSONL sidecar is deliberately outside delivery manifests. Unknowns stay null;
budgets do not authorize spending, and observations are not forecasts. Do not put
credentials or participant-identifying data in free-text fields or evidence.
"""
from pathlib import Path
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
import re

NAME = 'production-journal.jsonl'
SCHEMA = 'earnalism.production-journal.v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _text(value, label, maximum=1000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError('Nonblank bounded text required: ' + label)
    return value


def _number(value, label):
    if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
        raise ValueError('Finite nonnegative number or null required: ' + label)
    return value


def _stamp(value):
    try:
        stamp = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            raise ValueError()
        return stamp
    except (AttributeError, TypeError, ValueError):
        raise ValueError('Timezone-aware ISO timestamp required')


def _keys(record, allowed, required):
    if not isinstance(record, dict) or set(record) - set(allowed) or set(required) - set(record):
        raise ValueError('Unexpected or missing journal fields')
    _text(record.get('event_id'), 'event_id', 120)
    if not re.fullmatch(r'[A-Za-z0-9_-]+', record['event_id']):
        raise ValueError('Safe event identifier required')


def _currency(value):
    if value is not None and (not isinstance(value, str) or not re.fullmatch(r'[A-Z]{3}', value)):
        raise ValueError('Three-letter uppercase currency required')


def _work(record):
    _keys(record, ('event_id', 'activity', 'actual_human_minutes', 'actual_compute_minutes',
                   'actual_compute_units', 'actual_cost', 'currency', 'budget'),
          ('event_id', 'activity', 'actual_human_minutes', 'actual_compute_minutes'))
    _text(record['activity'], 'activity', 300)
    for key in ('actual_human_minutes', 'actual_compute_minutes', 'actual_compute_units', 'actual_cost'):
        _number(record.get(key), key)
    _currency(record.get('currency'))
    if record.get('actual_cost') is not None and not record.get('currency'):
        raise ValueError('Actual monetary cost requires its currency')
    if 'budget' in record:
        budget = record['budget']
        if not isinstance(budget, dict) or set(budget) - {'human_minutes', 'compute_minutes', 'compute_units', 'cost', 'currency'}:
            raise ValueError('Budget fields must remain separate from actuals')
        for key in ('human_minutes', 'compute_minutes', 'compute_units', 'cost'):
            _number(budget.get(key), 'budget.' + key)
        _currency(budget.get('currency'))
        if budget.get('cost') is not None and not budget.get('currency'):
            raise ValueError('Budget monetary cost requires its currency')


def _evidence(folder, reference):
    if not isinstance(reference, dict) or set(reference) != {'path', 'sha256'}:
        raise ValueError('Local evidence path and SHA256 required')
    raw = Path(_text(reference['path'], 'evidence path'))
    root = Path(folder).resolve()
    path = (root / raw).resolve()
    if raw.is_absolute() or '..' in raw.parts or not path.is_relative_to(root) or path.name == NAME:
        raise ValueError('Evidence must remain inside this candidate')
    if not path.is_file() or path.stat().st_size == 0 or sha(path) != reference['sha256']:
        raise ValueError('Missing or changed observation evidence')


def _observation(folder, record):
    fields = ('event_id', 'platform_video_id', 'format', 'checkpoint', 'captured_at',
              'period', 'traffic_source', 'basis', 'denominator', 'context', 'metrics', 'evidence', 'currency')
    _keys(record, fields, set(fields) - {'currency'})
    if not isinstance(record['platform_video_id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{11}', record['platform_video_id']):
        raise ValueError('Actual YouTube video ID required')
    if record['format'] not in ('landscape', 'shorts') or record['basis'] != 'observed':
        raise ValueError('Actual observed landscape/shorts metrics required; no projections')
    for key in ('checkpoint', 'traffic_source', 'denominator', 'context'):
        _text(record[key], key)
    captured = _stamp(record['captured_at'])
    period = record['period']
    if not isinstance(period, dict) or set(period) != {'start', 'end'}:
        raise ValueError('Observation time window required')
    if not _stamp(period['start']) <= _stamp(period['end']) <= captured:
        raise ValueError('Observation period must end by capture time')
    if captured > dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5):
        raise ValueError('Future observations cannot be actual results')
    metrics = record['metrics']
    if not isinstance(metrics, dict) or not metrics:
        raise ValueError('Observed metrics or explicit null unknowns required')
    for key, value in metrics.items():
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,79}', key) or any(word in key for word in ('password', 'token', 'secret', 'credential')):
            raise ValueError('Only named numeric metrics may be recorded')
        _number(value, 'metrics.' + key)
        if key in ('ctr_percent', 'stayed_to_watch_percent') and value is not None and value > 100:
            raise ValueError('Percentage exceeds its defined denominator')
    _currency(record.get('currency'))
    if metrics.get('revenue') is not None and not record.get('currency'):
        raise ValueError('Revenue requires a recorded currency')
    _evidence(folder, record['evidence'])


def _read(folder, text):
    rows = []
    ids = set()
    for line in text.splitlines():
        try:
            row = json.loads(line)
        except (ValueError, TypeError):
            raise ValueError('Journal damaged; preserve it instead of resetting')
        expected = {'schema', 'event_id', 'kind', 'logged_at', 'episode_sha256',
                    'delivery_manifest_sha256', 'budget_is_spending_authorization', 'record'}
        if not isinstance(row, dict) or set(row) != expected or row.get('schema') != SCHEMA or row.get('kind') not in ('work', 'observation') or row.get('budget_is_spending_authorization') is not False:
            raise ValueError('Invalid prior journal entry')
        if row.get('event_id') in ids:
            raise ValueError('Duplicate prior event identifier')
        ids.add(row.get('event_id'))
        if not re.fullmatch(r'[a-f0-9]{64}', row.get('episode_sha256', '')):
            raise ValueError('Missing episode provenance')
        if row.get('delivery_manifest_sha256') is not None and not re.fullmatch(r'[a-f0-9]{64}', row['delivery_manifest_sha256']):
            raise ValueError('Invalid delivery provenance')
        _stamp(row.get('logged_at'))
        record = row.get('record')
        if not isinstance(record, dict) or row.get('event_id') != record.get('event_id'):
            raise ValueError('Journal identifier binding changed')
        if row['kind'] == 'work':
            _work(record)
        else:
            _observation(folder, record)
        rows.append(row)
    return rows


def _append(folder, record, kind):
    folder = Path(folder).resolve()
    episode_hash = sha(folder / 'episode.json')
    # Validate a JSON copy so callers cannot modify the retained record later.
    record = json.loads(json.dumps(record, allow_nan=False))
    if kind == 'work':
        _work(record)
    else:
        _observation(folder, record)
    manifest = folder / 'delivery-manifest.json'
    row = {'schema': SCHEMA, 'event_id': record['event_id'], 'kind': kind,
           'logged_at': dt.datetime.now(dt.timezone.utc).isoformat(),
           'episode_sha256': episode_hash,
           'delivery_manifest_sha256': sha(manifest) if manifest.exists() else None,
           'budget_is_spending_authorization': False, 'record': record}
    with (folder / NAME).open('a+', encoding='utf-8') as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        stream.seek(0)
        original = stream.read()
        rows = _read(folder, original)
        if original and not original.endswith('\n'):
            raise ValueError('Incomplete journal terminator; preserve before repair')
        if any(value['event_id'] == row['event_id'] for value in rows):
            raise ValueError('Duplicate event identifier; no event was appended')
        stream.seek(0, 2)
        stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    return row


def append_work(folder, record):
    return _append(folder, record, 'work')


def append_observation(folder, record):
    return _append(folder, record, 'observation')


def summarize(folder):
    folder = Path(folder).resolve()
    journal = folder / NAME
    rows = []
    if journal.exists():
        with journal.open(encoding='utf-8') as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_SH)
            text = stream.read()
            if text and not text.endswith('\n'):
                raise ValueError('Incomplete journal terminator; preserve before repair')
            rows = _read(folder, text)
    work = [row for row in rows if row['kind'] == 'work']
    observations = [row for row in rows if row['kind'] == 'observation']
    current_episode = sha(folder / 'episode.json')
    manifest = folder / 'delivery-manifest.json'
    current_manifest = sha(manifest) if manifest.exists() else None

    def total(key, subset=work):
        values = [row['record'].get(key) for row in subset]
        known = [value for value in values if value is not None]
        return {'known_total': sum(known) if known else None,
                'unknown_entries': sum(value is None for value in values),
                'recorded_entries': len(values)}

    currencies = sorted({row['record']['currency'] for row in work if row['record'].get('currency')})
    return {'status': 'OBSERVATIONS_RECORDED' if observations else 'AUDIENCE_RESULTS_UNKNOWN',
            'scope': 'Recorded actual inputs only; no approval, causal claim, audience forecast or revenue guarantee',
            'event_count': len(rows), 'current_episode_sha256': current_episode,
            'current_delivery_manifest_sha256': current_manifest,
            'historical_binding_entries': sum(row['episode_sha256'] != current_episode or row['delivery_manifest_sha256'] != current_manifest for row in rows),
            'work': {**{key: total(key) for key in ('actual_human_minutes', 'actual_compute_minutes', 'actual_compute_units')},
                     'actual_cost_by_currency': {currency: total('actual_cost', [row for row in work if row['record'].get('currency') == currency]) for currency in currencies},
                     'cost_currency_unknown_entries': sum(not row['record'].get('currency') for row in work)},
            'observations': observations,
            'observation_aggregation': 'NONE: compare matching format, video, period, traffic source, denominator and currency; overlapping windows must not be summed',
            'budget_is_spending_authorization': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('work', 'observe', 'summary'))
    parser.add_argument('folder')
    parser.add_argument('record', nargs='?')
    args = parser.parse_args()
    if args.command == 'summary':
        if args.record:
            parser.error('summary does not accept a record')
        result = summarize(args.folder)
    else:
        if not args.record:
            parser.error('work/observe require an actual record JSON file')
        record = json.loads(Path(args.record).read_text())
        result = (append_work if args.command == 'work' else append_observation)(args.folder, record)
    print(json.dumps(result, indent=2, allow_nan=False))
