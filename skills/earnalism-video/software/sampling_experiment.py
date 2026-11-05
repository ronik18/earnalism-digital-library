"""Read-only audit of one raw, single-control Qwen sampling experiment.

Matched recorded controls do not prove a natural performance or identical
primary codes: residual-code feedback and shared random-number consumption can
change the complete generation. No audition is promoted by this audit.
"""
import copy
import json
import math
from pathlib import Path
import re

from audio_derivation import check_unit, sha
from asr_review import require_script_match
from voice_experiment import _differences, _inspect
from qwen_worker import GENERATION_DEFAULTS, VALIDATION_DEFAULTS


def _read(path):
    return json.loads(Path(path).read_text())


def _equal(left, right):
    return type(left) is type(right) and left == right


def _control(field, value):
    if field == 'subtalker_dosample' and type(value) is bool:
        return
    if field == 'subtalker_temperature' and type(value) in (int, float) and \
            math.isfinite(value) and .1 <= value <= 1.5:
        return
    raise ValueError('Expected control must be supported subtalker_dosample boolean or subtalker_temperature within 0.1..1.5')


def _history_folder(raw, history_path):
    path = Path(raw)
    if path.is_absolute():
        return path.resolve()
    # Histories may bind workspace-relative paths or paths local to the trial.
    # Ambiguous relative bindings fail rather than silently choosing a source.
    matches = {(parent / path).resolve() for parent in history_path.parents
               if (parent / path).is_dir()}
    if len(matches) != 1:
        raise ValueError('Prior generation folder binding is missing or ambiguous')
    return matches.pop()


def _history(path, digest, sid, baseline, field, value):
    path = Path(path).resolve()
    if sha(path) != digest:
        raise ValueError('Persistent prior-history binding changed')
    history = _read(path)
    rows = history.get('prior_generations')
    closed = history.get('closed_experiments')
    if not isinstance(rows, list) or not rows or not isinstance(closed, dict) or not closed:
        raise ValueError('Explicit prior generations and closed scopes are required')
    used = 0
    for scope in closed.values():
        if not isinstance(scope, dict) or type(scope.get('used')) is not int or \
                type(scope.get('limit')) is not int or not 0 < scope['used'] == scope['limit']:
            raise ValueError('Retain each earlier exhausted scope without resetting its counter')
        used += scope['used']
    if used != len(rows):
        raise ValueError('Closed-scope counts must account for every prior physical generation')
    text = baseline['settings']['text']
    seen, standalone, found_baseline = set(), 0, False
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('text'), str) or text not in row['text']:
            raise ValueError('Every prior middle-containing generation must retain the actual baseline text')
        folder = _history_folder(row['folder'], path)
        meta = check_unit(folder, sid)
        if meta.get('status') != 'GENERATED_REQUIRES_REVIEW' or meta.get('derivation'):
            raise ValueError('Prior history must bind raw physical generations')
        expected = {'wav_sha256': meta['wav_sha256'],
                    'metadata_sha256': sha(folder / 'raw' / (sid + '.wav.json')),
                    'effective_key': meta.get('effective_key'),
                    'text': meta.get('settings', {}).get('text'),
                    'actual_selected_seed': meta.get('selected_seed')}
        if any(not _equal(row.get(key), val) for key, val in expected.items()):
            raise ValueError('Prior generation record disagrees with bound raw source')
        identity = (row['wav_sha256'], row['effective_key'])
        if not isinstance(row['effective_key'], str) or not row['effective_key'] or \
                identity in seen or any(key == row['effective_key'] for _, key in seen):
            raise ValueError('Prior physical generations need distinct retained effective keys')
        seen.add(identity)
        standalone += row['text'] == text
        found_baseline |= row['wav_sha256'] == baseline['wav_sha256'] and row['text'] == text
    if not found_baseline:
        raise ValueError('History must retain the selected raw baseline')
    counts = {'prior_middle_containing_generations': len(rows),
              'new_exact_standalone_generation_index': standalone + 1,
              'new_middle_containing_generation_index': len(rows) + 1,
              'new_trial_attempt_limit': 1}
    if any(type(history.get(key)) is not int or history[key] != val for key, val in counts.items()):
        raise ValueError('Disclose derived physical overlap and standalone counts; new scope allows one attempt')
    for key in ('no_prior_counters_reset', 'old_effective_keys_remain_closed', 'stop_after_this_generation'):
        if history.get(key) is not True:
            raise ValueError('Earlier effective keys remain closed; stop after the single new attempt')
    change = history.get('only_changed_control', {})
    if change.get('name') != field or not _equal(change.get('candidate'), value) or \
            not _equal(change.get('baseline'), baseline['settings']['generation'].get(field)):
        raise ValueError('Bound history must name the same single control and its actual values')
    return {'path': str(path), 'sha256': digest, 'record': copy.deepcopy(history),
            **counts, 'previous_exact_standalone_generations': standalone,
            'no_prior_counters_reset': True,
            'scope_note': 'One newly requested control experiment; earlier limits and rejected takes remain recorded. '
                          'This is not a universal lifetime generation cap.'}


def _execution(folder, sid, baseline, field, value, history):
    folder = Path(folder)
    meta = _read(folder / 'raw' / (sid + '.wav.json'))
    job = _read(folder / 'config/qwen-job.json')
    episode = _read(folder / 'episode.json')
    if len(episode['scenes']) != 1 or len(job['segments']) != 1:
        raise ValueError('Candidate must be one complete uninterrupted raw generated unit')
    if type(job.get('max_attempts')) is not int or job['max_attempts'] != 1:
        raise ValueError('Actual job must cap the new experiment at one attempt')
    attempts = meta.get('attempts')
    seed = baseline['selected_seed']
    if type(meta.get('selected_attempt')) is not int or meta['selected_attempt'] != 1 or \
            not isinstance(attempts, list) or len(attempts) != 1 or \
            type(attempts[0].get('attempt')) is not int or attempts[0]['attempt'] != 1 or \
            not _equal(attempts[0].get('seed'), seed) or attempts[0].get('status') != 'PASS' or \
            meta.get('interrupted_attempt_numbers') != []:
        raise ValueError('Require exactly one successful actual generation attempt and no interrupted attempts')
    if not meta.get('effective_key') or meta['effective_key'] in {
            row['effective_key'] for row in history['record']['prior_generations']}:
        raise ValueError('New control trial must not reopen a previous effective key')
    if attempts[0].get('effective_key') != meta['effective_key']:
        raise ValueError('Actual attempt must bind the selected new effective key')
    settings = meta['settings']
    segment = job['segments'][0]
    wanted = {'segment_id': sid, 'text': baseline['settings']['text'],
              'instruct': baseline['settings']['instruct'], 'speaker': 'Ryan', 'seed': seed}
    if any(not _equal(segment.get(key), val) for key, val in wanted.items()):
        raise ValueError('Actual job must retain exact baseline text, instruction, Ryan and selected seed')
    overrides = job.get('generation', {})
    if not isinstance(overrides, dict) or field not in overrides or not _equal(overrides[field], value) or \
            list(_differences({**GENERATION_DEFAULTS, **overrides}, settings['generation'])):
        raise ValueError('Actual job generation controls disagree with recorded complete controls')
    if list(_differences({**VALIDATION_DEFAULTS, **job.get('validation', {})}, settings['validation'])):
        raise ValueError('Actual job validation differs from recorded safeguard controls')
    for key, val in {'model_id': meta['provenance']['model_id'],
                     'model_revision': meta['provenance']['model_revision'],
                     'attention': settings['attention']}.items():
        if not _equal(job.get(key), val):
            raise ValueError('Actual job model or execution setting differs from recorded provenance')
    if 'device' in job and job['device'] != meta['provenance']['hardware'].get('device'):
        raise ValueError('Actual job device differs from recorded hardware')
    precision = {'requested_dtype': job.get('dtype'), 'recorded_dtype': settings['dtype']}
    if job.get('dtype') == 'auto':
        run_path = folder / 'logs/qwen-report.json'
        run = _read(run_path)
        probe = run.get('numerical_probe', {})
        native_bfloat16 = meta['provenance']['hardware'].get('native_bfloat16')
        resolved = 'bfloat16' if native_bfloat16 else 'float32'
        if type(native_bfloat16) is not bool or probe.get('dtype') != settings['dtype'] or \
                settings['dtype'] != resolved or probe.get('audio', {}).get('mechanical_checks') != 'PASS' or \
                list(_differences(meta['provenance'], run.get('provenance', {}))):
            raise ValueError('Automatic precision needs the matching successful numerical probe and resolved provenance')
        selected = [s for s in run.get('segments', []) if s.get('segment_id') == sid]
        if len(selected) != 1 or any(selected[0].get(key) != meta.get(key) for key in
                ('effective_key', 'wav_sha256', 'selected_seed', 'selected_attempt', 'status')):
            raise ValueError('Numerical-probe run report must bind the actual selected raw unit')
        precision.update(numerical_probe_dtype=probe['dtype'], numerical_probe_mechanical_checks='PASS',
                         run_report_sha256=sha(run_path))
    elif job.get('dtype') != settings['dtype']:
        raise ValueError('Actual job dtype differs from recorded precision')
    return {'job_sha256': sha(folder / 'config/qwen-job.json'), 'actual_attempts': 1,
            'raw_audio_sha256': meta['wav_sha256'], 'actual_effective_key': meta['effective_key'],
            **precision}


def _word_accuracy(folder, sid, baseline):
    folder = Path(folder)
    meta = _read(folder / 'raw' / (sid + '.wav.json'))
    alignment_path = folder / 'alignment' / (sid + '.json')
    alignment = _read(alignment_path)
    if alignment.get('audio_sha256') != meta['wav_sha256']:
        raise ValueError('Fresh ASR must bind the exact unprocessed candidate waveform')
    require_script_match(alignment, baseline['settings']['text'])
    return {'alignment_sha256': sha(alignment_path),
            'raw_audio_sha256': meta['wav_sha256'], 'all_recognized_words_match': True}


def audit_sampling_experiment(baseline_folder, candidate_folder, scene_id, *,
                              expected_field='subtalker_dosample', expected_value=False,
                              history_path, history_sha256):
    """Audit only the recorded single-control/raw/ASR/history conditions.

    ``expected_field`` is a supported leaf under ``settings.generation``.
    History is read without rewriting counters or prior decisions. A true
    ``recorded_single_control`` never supplies listening or release approval.
    """
    if not isinstance(scene_id, str) or not re.fullmatch(r'[a-zA-Z0-9_-]+', scene_id):
        raise ValueError('Unsafe scene id')
    _control(expected_field, expected_value)
    report = {'schema': 'earnalism.voice-sampling-experiment.v1',
              'recorded_single_control': False,
              'intended_difference': 'settings.generation.' + expected_field,
              'expected_value': expected_value, 'confounds': [], 'missing_evidence': [],
              'listening_review': 'PENDING', 'naturalness': 'NOT_ESTABLISHED',
              'causal_isolation': 'NOT_ESTABLISHED', 'listening_approval': False,
              'video_integration_approval': False, 'publication_approval': False,
              'note': 'Recorded-control and transcript audit only. Residual-code feedback and shared RNG '
                      'consumption can affect the full generation; identical primary codes are not established.'}
    left = _inspect(baseline_folder, scene_id, 'control', report)
    right = _inspect(candidate_folder, scene_id, 'candidate', report)
    if left is None or right is None:
        return report
    baseline = _read(Path(baseline_folder) / 'raw' / (scene_id + '.wav.json'))
    if report['control']['instruction'] != report['candidate']['instruction']:
        report['confounds'].append({'field': 'settings.instruct', 'reason': 'Keep the exact baseline performance direction'})
    if left['settings'].get('speaker') != 'Ryan' or right['settings'].get('speaker') != 'Ryan':
        report['confounds'].append({'field': 'settings.speaker', 'reason': 'Use the same stock Ryan speaker'})
    actual_left = left['settings']['generation'].get(expected_field)
    actual_right = right['settings']['generation'].get(expected_field)
    if not _equal(actual_right, expected_value) or _equal(actual_left, actual_right):
        report['confounds'].append({'field': report['intended_difference'],
                                   'reason': 'The intended control must change to its exact specified value'})
    comparison = copy.deepcopy(right)
    if expected_field in left['settings']['generation'] and expected_field in comparison['settings']['generation']:
        comparison['settings']['generation'][expected_field] = actual_left
    else:
        report['missing_evidence'].append({'field': report['intended_difference'],
                                           'reason': 'Actual control is missing from a recorded generation'})
    report['confounds'].extend(_differences(left, comparison))
    try:
        report['history'] = _history(history_path, history_sha256, scene_id, baseline,
                                     expected_field, expected_value)
        report['execution'] = _execution(candidate_folder, scene_id, baseline,
                                         expected_field, expected_value, report['history'])
    except (OSError, ValueError, KeyError, TypeError) as error:
        report['confounds'].append({'field': 'candidate.sampling_execution', 'reason': str(error)})
    try:
        report['word_accuracy'] = _word_accuracy(candidate_folder, scene_id, baseline)
    except (OSError, ValueError, KeyError, TypeError) as error:
        report['word_accuracy'] = {'all_recognized_words_match': False}
        report['confounds'].append({'field': 'candidate.word_accuracy', 'reason': str(error)})
    report['recorded_single_control'] = not report['confounds'] and not report['missing_evidence']
    return report
