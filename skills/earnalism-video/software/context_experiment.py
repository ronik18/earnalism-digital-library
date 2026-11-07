"""Audit one full-context synthesis trial without resetting middle-passage history.

This compares recorded controls only. It never approves naturalness, extracted
middle audio, video integration or publication.
"""
import copy
import hashlib
import json
from pathlib import Path
import re

from audio_derivation import check_unit, sha
from asr_review import require_script_match, tokens
from voice_experiment import _differences, _inspect

def _scene(folder, sid):
    rows = [s for s in json.loads((Path(folder)/'episode.json').read_text())['scenes'] if s['id'] == sid]
    if len(rows) != 1:
        raise ValueError('Exactly one matching canonical scene required')
    return rows[0]


def _neighbor(text, binding, position):
    """Only genuine, audio-bound adjacent narrative text can supply context."""
    if not isinstance(text, str) or not text.strip() or text != text.strip():
        raise ValueError('Nonempty exact prefix and suffix required')
    folder, sid = Path(binding['folder']), binding['scene_id']
    meta = check_unit(folder, sid)
    wav = folder/'raw'/(sid+'.wav')
    alignment = folder/'alignment'/(sid+'.json')
    if sha(wav) != binding['wav_sha256'] or sha(alignment) != binding['alignment_sha256']:
        raise ValueError('Changed prefix/suffix audio or alignment binding')
    scene = _scene(folder, sid)
    canonical = scene['text']
    if not (canonical.endswith(text) if position == 'prefix' else canonical.startswith(text)):
        raise ValueError('Prefix/suffix must be genuine adjacent narrative, not padding or a changed excerpt')
    if text[-1] not in '.!?':
        raise ValueError('Context excerpts must end at complete thought boundaries')
    record = json.loads(alignment.read_text())
    if record.get('audio_sha256') != sha(wav):
        raise ValueError('Stale neighbor transcript binding')
    require_script_match(record, canonical)
    words = record.get('display_word_times', record['word_times'])
    flat, spans = [], []
    for word in words:
        for token in tokens(word['word']):
            flat.append(token);spans.append(word)
    wanted = tokens(text)
    start = len(flat)-len(wanted) if position == 'prefix' else 0
    if not wanted or start < 0 or flat[start:start+len(wanted)] != wanted:
        raise ValueError('Context source words do not support exact prefix/suffix')
    low, high = binding['clip_start_seconds'], binding['clip_end_seconds']
    seconds = meta['audio']['duration_seconds']
    if not (type(low) in (int,float) and type(high) in (int,float) and
            0 <= low <= spans[start]['start'] < spans[start+len(wanted)-1]['end'] <= high <= seconds+.0001):
        raise ValueError('Context clip does not retain complete observed words')
    if (start and low < spans[start-1]['end']-1e-9) or \
            (start+len(wanted) < len(spans) and high > spans[start+len(wanted)]['start']+1e-9):
        raise ValueError('Context clip includes unrequested neighboring words')
    return {'text': text, 'folder': str(folder), 'scene_id': sid,
        'wav_sha256': sha(wav), 'alignment_sha256': sha(alignment),
        'clip_start_seconds': low, 'clip_end_seconds': high,
        'scope': 'ASR coverage only; phonetic shoulders and joins still require listening'}


def make_spec(baseline_folder, baseline_sid, prefix, suffix, prefix_source,
              suffix_source, previous_middle_history_path):
    """Convenience binding builder. It does not grant permission to synthesize."""
    baseline = check_unit(baseline_folder, baseline_sid)
    history = json.loads(Path(previous_middle_history_path).read_text())
    used, limit = history['canonical_generation_index'], history['canonical_max_generations']
    return {'prefix': prefix, 'suffix': suffix,
        'baseline_sha256': baseline['wav_sha256'],
        'prefix_source': prefix_source, 'suffix_source': suffix_source,
        'previous_middle_history_path': str(previous_middle_history_path),
        'previous_middle_history_sha256': sha(previous_middle_history_path),
        'previous_middle_generations': used, 'previous_middle_generation_limit': limit,
        'middle_physical_generation_index': used+1,
        'max_context_attempts': 1, 'scope': 'full_context_only',
        'middle_only_promotion': False, 'dummy_padding': False}


def validate_context_spec(baseline_folder, baseline_sid, spec):
    baseline = check_unit(baseline_folder, baseline_sid)
    if baseline.get('status') != 'GENERATED_REQUIRES_REVIEW' or baseline.get('derivation'):
        raise ValueError('Selected Y baseline must be untouched raw generation')
    if baseline['wav_sha256'] != spec.get('baseline_sha256'):
        raise ValueError('Selected Y source binding changed')
    if spec.get('max_context_attempts') != 1 or type(spec.get('max_context_attempts')) is not int:
        raise ValueError('Only one new full-context attempt allowed')
    if spec.get('scope') != 'full_context_only' or spec.get('middle_only_promotion') is not False or spec.get('dummy_padding') is not False:
        raise ValueError('Full-context audition only; no dummy padding or middle-only extraction approval')
    history_path = Path(spec['previous_middle_history_path'])
    if sha(history_path) != spec['previous_middle_history_sha256']:
        raise ValueError('Earlier middle history binding changed')
    history = json.loads(history_path.read_text())
    middle = _scene(baseline_folder, baseline_sid)['text']
    if baseline['settings']['text'] != middle:
        raise ValueError('Selected Y canonical and actual text differ')
    baseline_alignment = json.loads((Path(baseline_folder)/'alignment'/(baseline_sid+'.json')).read_text())
    if baseline_alignment.get('audio_sha256') != baseline['wav_sha256']:
        raise ValueError('Selected Y transcript binding changed')
    require_script_match(baseline_alignment, middle)
    used, limit = history.get('canonical_generation_index'), history.get('canonical_max_generations')
    if type(used) is not int or type(limit) is not int or not 0 < used == limit or \
            history.get('canonical_text_sha256') != hashlib.sha256(middle.encode()).hexdigest() or \
            type(spec.get('previous_middle_generations')) is not int or spec.get('previous_middle_generations') != used or \
            type(spec.get('previous_middle_generation_limit')) is not int or spec.get('previous_middle_generation_limit') != limit or \
            type(spec.get('middle_physical_generation_index')) is not int or spec.get('middle_physical_generation_index') != used+1:
        raise ValueError('Retain actual exhausted middle history and disclose the next physical synthesis')
    seed = baseline.get('selected_seed')
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('Baseline must record its actual uint32 selected seed')
    prefix = _neighbor(spec['prefix'], spec['prefix_source'], 'prefix')
    suffix = _neighbor(spec['suffix'], spec['suffix_source'], 'suffix')
    full = ' '.join([prefix['text'], middle, suffix['text']])
    if len(full.split()) > 65 or len(full) > 520:
        raise ValueError('Full context exceeds existing 65-word/520-character worker bound')
    return {'expected_complete_text': full, 'middle_text': middle,
        'word_count': len(full.split()), 'character_count': len(full),
        'prefix': prefix, 'suffix': suffix,
        'previous_middle_history_sha256': sha(history_path),
        'baseline_actual_selected_seed': seed,
        'previous_middle_generations': used, 'previous_middle_generation_limit': limit,
        'middle_physical_generation_index': used+1,
        'max_context_attempts': 1, 'no_prior_counters_reset': True}


def audit_context_experiment(baseline_folder, candidate_folder, baseline_sid, candidate_sid, spec):
    for sid in (baseline_sid, candidate_sid):
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', sid):
            raise ValueError('Unsafe scene id')
    report = {'schema': 'earnalism.voice-full-context-experiment.v1',
        'context_only': False, 'confounds': [], 'missing_evidence': [],
        'listening_review': 'PENDING', 'causal_isolation': 'NOT_ESTABLISHED',
        'middle_only_extraction_approval': False, 'video_integration_approval': False,
        'publication_approval': False,
        'note': 'Recorded-control audit only; complete raw context remains the audition. '
                'The repeated middle is a new physical synthesis; its bound earlier attempt history remains exhausted.'}
    try:
        planned = validate_context_spec(baseline_folder, baseline_sid, spec)
        report['context'] = planned
    except (OSError, ValueError, KeyError, TypeError) as error:
        report['confounds'].append({'field': 'context_spec', 'reason': str(error)})
        return report
    control = _inspect(baseline_folder, baseline_sid, 'control', report)
    candidate = _inspect(candidate_folder, candidate_sid, 'candidate', report)
    if control is None or candidate is None:
        return report
    for side, controls in [('control', control), ('candidate', candidate)]:
        if controls.get('selected_seed') != planned['baseline_actual_selected_seed'] or controls['settings'].get('speaker') != 'Ryan':
            report['confounds'].append({'field': side+'.seed_or_speaker', 'reason': 'Require actual baseline selected seed and stock Ryan'})
    if report['candidate']['actual_text'] != planned['expected_complete_text'] or candidate['canonical_text'] != planned['expected_complete_text']:
        report['confounds'].append({'field': 'candidate.complete_text', 'reason': 'Candidate must contain exact complete prefix + selected Y + suffix'})
    if report['candidate']['instruction'] != report['control']['instruction']:
        report['confounds'].append({'field': 'settings.instruct', 'reason': 'Keep the exact Y performance instruction'})
    left, right = copy.deepcopy(control), copy.deepcopy(candidate)
    for item in (left, right):
        item.pop('canonical_text', None);item['settings'].pop('text', None)
    report['confounds'].extend(_differences(left, right))
    try:
        folder = Path(candidate_folder)
        episode = json.loads((folder/'episode.json').read_text())
        meta = json.loads((folder/'raw'/(candidate_sid+'.wav.json')).read_text())
        job = json.loads((folder/'config/qwen-job.json').read_text())
        if len(episode['scenes']) != 1 or len(job['segments']) != 1:
            raise ValueError('Complete context must be one uninterrupted generated unit')
        if job.get('max_attempts') != 1 or type(job.get('max_attempts')) is not int:
            raise ValueError('Actual context job must cap attempts at one')
        attempts = meta.get('attempts')
        if meta.get('selected_attempt') != 1 or not isinstance(attempts,list) or len(attempts) != 1 or \
                attempts[0].get('attempt') != 1 or attempts[0].get('seed') != planned['baseline_actual_selected_seed'] or meta.get('interrupted_attempt_numbers'):
            raise ValueError('Only one actual full-context generation attempt may exist')
        segment = job['segments'][0]
        if any(segment.get(key) != value for key,value in {
                'segment_id':candidate_sid,'text':planned['expected_complete_text'],
                'instruct':report['control']['instruction'],'speaker':'Ryan','seed':planned['baseline_actual_selected_seed']}.items()):
            raise ValueError('Actual job segment differs from complete-context experiment')
        alignment = json.loads((folder/'alignment'/(candidate_sid+'.json')).read_text())
        if alignment.get('audio_sha256') != meta['wav_sha256']:
            raise ValueError('Stale full-context transcript binding')
        require_script_match(alignment, planned['expected_complete_text'])
    except (OSError, ValueError, KeyError, TypeError) as error:
        report['confounds'].append({'field': 'candidate.context_execution', 'reason': str(error)})
    report['context_only'] = not report['confounds'] and not report['missing_evidence']
    return report
