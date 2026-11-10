"""Hash-bound pixel-reference checks. A bounded regression, never full AV acceptance.

Each reference must be an independently rendered, visually inspected still from
that exact composition. Static ROIs must remain static over their declared range.
Do not calibrate against a damaged candidate or silently increase tolerances.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import subprocess

SCHEMA = 'earnalism.pixel-integrity.v1'
PASS = 'REFERENCE_REGRESSION_PASS_NOT_FULL_VISUAL_ACCEPTANCE'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def require(ok, text):
    if not ok:
        raise ValueError(text)


def probe(path):
    s = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams',
        'v:0', '-show_streams', '-of', 'json', str(path)], text=True))['streams'][0]
    return (s['width'], s['height'])


def frame_bytes(path, rect, size, start, count):
    x, y, w, h = rect
    filt = f'trim=start_frame={start}:end_frame={start+count},setpts=PTS-STARTPTS,' \
           f'crop={w}:{h}:{x}:{y},scale={size[0]}:{size[1]}:flags=area,format=gray'
    return subprocess.check_output(['ffmpeg', '-v', 'error', '-xerror', '-i', str(path),
        '-vf', filt, '-frames:v', str(count), '-an', '-fps_mode', 'passthrough',
        '-f', 'rawvideo', '-'])


def deviations(raw, reference, count, tolerance):
    length = len(reference)
    require(length > 0 and len(raw) == length * count, 'Incomplete or extra decoded reference samples')
    scores = [sum(abs(a-b) for a, b in zip(raw[i*length:(i+1)*length], reference)) / length
              for i in range(count)]
    return scores, [i for i, value in enumerate(scores) if value > tolerance]


def isolated_frame_candidates(raw, frame_size, count, min_adjacent_mae, max_bridge_ratio):
    """Surface one-frame picture discontinuities, not ordinary persistent scene cuts."""
    require(len(raw) == frame_size * count and count >= 3, 'Incomplete temporal frame samples')
    frames = [memoryview(raw)[i*frame_size:(i+1)*frame_size] for i in range(count)]
    def mae(a, b):
        return sum(abs(x-y) for x, y in zip(a, b)) / frame_size
    diffs = [mae(a, b) for a, b in zip(frames, frames[1:])]
    flagged = []
    for n in range(1, count-1):
        adjacent = min(diffs[n-1], diffs[n])
        if adjacent >= min_adjacent_mae:
            bridge = mae(frames[n-1], frames[n+1])
            if bridge <= adjacent * max_bridge_ratio:
                flagged.append({'frame': n, 'previous_mae': diffs[n-1],
                                'next_mae': diffs[n], 'bridge_mae': bridge})
    return flagged


def temporal_probe(source, spec, dims):
    start, end = spec['frames']
    size = spec['sample_size']
    threshold, ratio = spec['min_adjacent_mae'], spec['max_bridge_ratio']
    require(type(start) is int and type(end) is int and 0 <= start < end-2, 'Invalid temporal range')
    require(len(size) == 2 and all(type(v) is int and 8 <= v <= 512 for v in size), 'Invalid temporal sample size')
    require(isinstance(threshold, (int, float)) and math.isfinite(threshold) and 0 < threshold <= 30 and
            isinstance(ratio, (int, float)) and math.isfinite(ratio) and 0 < ratio < 1,
            'Invalid temporal thresholds')
    raw = frame_bytes(source, [0, 0, *dims], size, start, end-start)
    candidates = isolated_frame_candidates(raw, size[0]*size[1], end-start, threshold, ratio)
    return {**spec, 'checked_frames': end-start,
            'flagged_frames': [{**c, 'frame': c['frame']+start} for c in candidates],
            'scope': 'All-frame low-resolution full-picture discontinuity targets; not every-pixel or all-artifact certification.'}


def analyze(source, config):
    source, config = Path(source).resolve(), Path(config).resolve()
    before, config_before, checker_before = sha(source), sha(config), sha(__file__)
    spec = json.loads(config.read_text())
    require(spec.get('schema') == SCHEMA and spec.get('reference_origin') == 'independent_composition_stills',
            'Independent composition-reference contract required')
    dims = probe(source)
    require(list(dims) == spec.get('dimensions'), 'Reference/source dimensions differ')
    checks = spec.get('checks')
    require(isinstance(checks, list) and checks, 'No reference checks')
    rows = []
    for c in checks:
        reference = (config.parent / c['reference']).resolve()
        require(reference != source and sha(reference) == c['reference_sha256'] and probe(reference) == dims,
                'Changed, self-referential or wrong-sized reference')
        start, end = c['frames']
        rect, size, tolerance = c['rect'], c['sample_size'], c['max_mae']
        require(type(start) is int and type(end) is int and 0 <= start < end, 'Invalid exclusive frame range')
        require(len(rect) == 4 and all(type(v) is int for v in rect) and min(rect) >= 0 and
                min(rect[2:]) > 0 and rect[0]+rect[2] <= dims[0] and rect[1]+rect[3] <= dims[1], 'Invalid pixel ROI')
        require(len(size) == 2 and all(type(v) is int and 1 <= v <= 512 for v in size), 'Invalid sample dimensions')
        require(isinstance(tolerance, (int, float)) and not isinstance(tolerance, bool) and
                math.isfinite(tolerance) and 0 < tolerance <= 20, 'Invalid calibrated reference tolerance')
        ref = frame_bytes(reference, rect, size, 0, 1)
        require(len(ref) == size[0]*size[1], 'Incomplete reference decode')
        raw = frame_bytes(source, rect, size, start, end-start)
        scores, flags = deviations(raw, ref, end-start, tolerance)
        rows.append({**c, 'reference_path': str(reference), 'checked_frames': end-start,
                     'min_mae': min(scores), 'max_observed_mae': max(scores),
                     'flagged_frames': [start+i for i in flags]})
    temporal = temporal_probe(source, spec['temporal_probe'], dims) if 'temporal_probe' in spec else None
    require(sha(source) == before and sha(config) == config_before and sha(__file__) == checker_before, 'Source/config/checker changed during check')
    require(all(sha(c['reference_path']) == c['reference_sha256'] for c in rows), 'Reference changed during check')
    return {'schema': SCHEMA, 'state': PASS if not any(c['flagged_frames'] for c in rows) and not (temporal and temporal['flagged_frames']) else 'PIXEL_REGRESSION_HOLD',
            'source': str(source), 'source_sha256': before, 'config': str(config),
            'config_sha256': sha(config), 'checker_sha256': checker_before, 'checks': rows, 'temporal_probe': temporal,
            'publication_approved': False,
            'scope': 'Only declared static regions/ranges and specific independent reference frames. '
                     'Does not establish all-pixel correctness, motion quality, audio or native Instagram acceptance.'}


def validate_delivery_coverage(spec, body_frames):
    """Require independent frame-zero plus a static anchor covering every body frame."""
    require(type(body_frames) is int and body_frames > 0, 'Invalid body frame count')
    dims, checks = spec['dimensions'], spec['checks']
    require(spec.get('temporal_probe', {}).get('frames') == [0, body_frames],
            'Full-body temporal pixel coverage required')
    require(any(c['frames'] == [0, 1] and c['rect'] == [0, 0, *dims] for c in checks),
            'Independent full-frame zero reference required')
    require(any(c['frames'] == [body_frames-1, body_frames] and c['rect'] == [0, 0, *dims] for c in checks),
            'Independent last-body-frame reference required')
    intervals = sorted(c['frames'] for c in checks if c['rect'] != [0, 0, *dims])
    end = 0
    for start, stop in intervals:
        require(start <= end and stop <= body_frames and start < stop,
                'Missing, invalid or overrun static-anchor coverage')
        end = max(end, stop)
    require(end == body_frames, 'Static-anchor checks must cover every body frame')
    return True


def verify_receipt(path, source):
    report = json.loads(Path(path).read_text())
    require(report.get('schema') == SCHEMA and report.get('state') == PASS and
            report.get('source_sha256') == sha(source) and report.get('checker_sha256') == sha(__file__),
            'Missing, failed or stale pixel-reference receipt')
    require(sha(report['config']) == report['config_sha256'], 'Pixel-reference configuration changed')
    require(report.get('checks'), 'No pixel-reference checks in receipt')
    spec = json.loads(Path(report['config']).read_text())
    require(len(report['checks']) == len(spec['checks']), 'Incomplete pixel-reference receipt')
    for actual, expected in zip(report['checks'], spec['checks']):
        require(all(actual.get(k) == value for k, value in expected.items()) and
                actual.get('checked_frames') == expected['frames'][1]-expected['frames'][0] and
                actual.get('max_observed_mae', float('inf')) <= expected['max_mae'], 'Incomplete or inconsistent pixel-reference result')
    if 'temporal_probe' in spec:
        temporal = report.get('temporal_probe') or {}
        require(all(temporal.get(k) == value for k, value in spec['temporal_probe'].items()) and
                temporal.get('checked_frames') == spec['temporal_probe']['frames'][1]-spec['temporal_probe']['frames'][0],
                'Missing or incomplete full-picture temporal receipt')
    require(not (report.get('temporal_probe') or {}).get('flagged_frames'), 'Unresolved temporal pixel discontinuity')
    for c in report['checks']:
        require(not c['flagged_frames'] and sha(c['reference_path']) == c['reference_sha256'], 'Pixel reference changed/flagged')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source'); p.add_argument('--config', required=True); p.add_argument('--report', required=True)
    p.add_argument('--body-frames', type=int)
    a = p.parse_args(); out = Path(a.report)
    require(not out.exists() and not out.is_symlink(), 'Preserve existing reports; choose a fresh path')
    if a.body_frames is not None:
        validate_delivery_coverage(json.loads(Path(a.config).read_text()), a.body_frames)
    result = analyze(a.source, a.config)
    with out.open('x') as f:
        json.dump(result, f, indent=2); f.write('\n')
    print(result['state'])
    return 0 if result['state'] == PASS else 2


if __name__ == '__main__':
    raise SystemExit(main())
