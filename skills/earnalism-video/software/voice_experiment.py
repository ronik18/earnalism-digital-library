"""Read-only audit of recorded controls for an instruction-only raw-voice test.

This is experiment evidence, not a naturalness verdict or a release/approval gate.
Equal recorded controls cannot prove deterministic or causal isolation.
"""
import argparse
import copy
import json
from pathlib import Path
import re

from audio_derivation import check_unit, sha


def _get(value, path):
    for key in path.split('.'):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def _differences(control, candidate, path=''):
    if isinstance(control, dict) and isinstance(candidate, dict):
        for key in sorted(set(control) | set(candidate)):
            field = f'{path}.{key}' if path else key
            if key not in control or key not in candidate:
                yield {'field': field, 'control': control.get(key),
                       'candidate': candidate.get(key), 'reason': 'Recorded field missing on one side'}
            else:
                yield from _differences(control[key], candidate[key], field)
    elif isinstance(control, list) and isinstance(candidate, list) and len(control) == len(candidate):
        for index, (left, right) in enumerate(zip(control, candidate)):
            yield from _differences(left, right, f'{path}[{index}]')
    elif type(control) is not type(candidate) or control != candidate:
        yield {'field': path, 'control': control, 'candidate': candidate,
               'reason': 'Additional recorded control differs'}


def _inspect(folder, scene_id, side, report):
    folder = Path(folder).resolve()
    try:
        meta = check_unit(folder, scene_id)
        episode = json.loads((folder / 'episode.json').read_text())
        scenes = [scene for scene in episode['scenes'] if scene.get('id') == scene_id]
        if len(scenes) != 1:
            raise ValueError('Exactly one canonical scene is required')
        scene = scenes[0]
        settings = meta.get('settings', {})
        provenance = meta.get('provenance', {})
        report[side] = {'folder': str(folder), 'wav_sha256': meta['wav_sha256'],
                        'metadata_sha256': sha(folder / 'raw' / (scene_id + '.wav.json')),
                        'actual_selected_seed': meta.get('selected_seed'),
                        'actual_text': settings.get('text'), 'instruction': settings.get('instruct')}
        if meta.get('status') != 'GENERATED_REQUIRES_REVIEW' or meta.get('derivation'):
            report['confounds'].append({'field': f'{side}.status',
                'reason': 'Instruction-only comparison requires an unprocessed generated take'})
        required = ['selected_seed', 'settings.text', 'settings.instruct', 'settings.speaker',
                    'settings.language', 'settings.generation', 'settings.validation',
                    'settings.dtype', 'settings.attention', 'settings.non_streaming_mode',
                    'settings.batch_size', 'settings.wav_subtype', 'audio.sample_rate',
                    'provenance.model_id', 'provenance.model_revision',
                    'provenance.snapshot.manifest_sha256', 'provenance.snapshot.files',
                    'provenance.worker_sha256', 'provenance.hardware',
                    'provenance.dtype', 'provenance.attention', 'provenance.environment.python',
                    'provenance.environment.packages', 'provenance.environment.platform',
                    'provenance.environment.qwen_package_source_sha256',
                    'provenance.environment.torch_cuda_version',
                    'provenance.environment.torch_cudnn_version']
        for field in required:
            value = _get(meta, field)
            if value is None or value == '' or value == {} or value == []:
                report['missing_evidence'].append({'field': f'{side}.{field}',
                                                   'reason': 'Required recorded control is absent'})
        seed = meta.get('selected_seed')
        if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
            report['confounds'].append({'field': f'{side}.selected_seed',
                                        'reason': 'Actual selected seed must be a recorded uint32 integer'})
        expected_text = scene.get('tts_text', scene['text'])
        if settings.get('text') != expected_text:
            report['confounds'].append({'field': f'{side}.canonical_input_text',
                'control': expected_text, 'candidate': settings.get('text'),
                'reason': 'Recorded worker input differs from the canonical scene speech text'})
        # The worker records these values twice. Check the internal binding too,
        # rather than allowing two equally stale binding objects to appear matched.
        environment = provenance.get('environment', {})
        expected_binding = {key: provenance.get(key) for key in
                            ('model_id', 'model_revision', 'hardware', 'worker_sha256')}
        expected_binding.update(snapshot_sha256=provenance.get('snapshot', {}).get('manifest_sha256'))
        expected_binding.update({key: environment.get(key) for key in
            ('python', 'packages', 'qwen_package_source_sha256',
             'torch_cuda_version', 'torch_cudnn_version')})
        for difference in _differences(expected_binding, settings.get('provenance_binding', {})):
            report['confounds'].append({**difference,
                'field': f'{side}.settings.provenance_binding.{difference["field"]}',
                'reason': 'Settings binding disagrees with recorded generation provenance'})
        for field in ('dtype', 'attention'):
            if settings.get(field) != provenance.get(field):
                report['confounds'].append({'field': f'{side}.settings.{field}',
                    'reason': 'Settings disagree with recorded execution provenance'})
        controls = copy.deepcopy(settings)
        for field in ('instruct', 'source_cache_key', 'segment_id', 'provenance_binding'):
            controls.pop(field, None)
        execution = copy.deepcopy(provenance)
        execution.pop('model_path', None)
        execution.get('environment', {}).pop('executable', None)
        return {'canonical_text': scene['text'], 'settings': controls,
                'selected_seed': seed, 'provenance': execution,
                'audio_sample_rate': meta.get('audio', {}).get('sample_rate')}
    except (OSError, ValueError, KeyError, TypeError) as error:
        report['confounds'].append({'field': f'{side}.integrity', 'reason': str(error)})
        return None


def audit_instruction_only(control_folder, candidate_folder, scene_id):
    """Compare bound raw generation records; never infer an audible outcome.

    ``instruction_only`` means the inspected *recorded* controls match except
    for instruction. Actual transcript fidelity and listening remain separate.
    Source-cache keys, file/run paths, timestamps and effective keys may differ.
    No records, media, approvals or release state are written.
    """
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', scene_id):
        raise ValueError('Unsafe scene id')
    report = {'schema': 'earnalism.voice-instruction-experiment.v1', 'scene_id': scene_id,
              'instruction_only': False, 'intended_difference': 'settings.instruct',
              'confounds': [], 'missing_evidence': [],
              'listening_review': 'PENDING', 'causal_isolation': 'NOT_ESTABLISHED',
              'note': 'Recorded-control audit only; no naturalness, transcript-fidelity or publication approval. '
                      'A conformed candidate listening verdict is not a verdict on its raw source.'}
    control = _inspect(control_folder, scene_id, 'control', report)
    candidate = _inspect(candidate_folder, scene_id, 'candidate', report)
    if control is not None and candidate is not None:
        report['confounds'].extend(_differences(control, candidate))
        left = report['control']['instruction']
        right = report['candidate']['instruction']
        if not isinstance(left, str) or not left.strip() or not isinstance(right, str) or not right.strip():
            report['confounds'].append({'field': 'settings.instruct', 'reason': 'Both instructions must be nonempty'})
        elif left == right:
            report['confounds'].append({'field': 'settings.instruct', 'reason': 'Instruction did not change'})
        report['instruction_only'] = not report['confounds'] and not report['missing_evidence']
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('control_folder')
    parser.add_argument('candidate_folder')
    parser.add_argument('scene_id')
    args = parser.parse_args()
    print(json.dumps(audit_instruction_only(args.control_folder, args.candidate_folder, args.scene_id), indent=2))
