"""Source-preserving voice audition: bounded gain and measured-quiet deletions.

No synthesis, tempo/pitch/EQ/compression, resampling or generated word timing.
Plans use integer indices on the untouched native 24 kHz mono float source.
"""
import array
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

RATE = 24000
KIND = 'source_preserving_voice_finish'
MAX_GAIN_DB = 3.0
MAX_SLEW_DB_PER_SECOND = 6.0
MAX_CUT_SECONDS = .30
MAX_TOTAL_CUT_SECONDS = 1.5
MAX_TOTAL_CUT_FRACTION = .08
MAX_CUT_RMS_DBFS = -55.0
MAX_CUT_PEAK_DBFS = -42.0
MAX_JOIN_STEP = 1e-4


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load(path):
    return json.loads(Path(path).read_text())


def _integer(value):
    return type(value) is int


def _finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _bytes(samples):
    values = array.array('f', samples)
    if sys.byteorder != 'little':
        values.byteswap()
    return values.tobytes()


def _decode(path):
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error',
        '-show_streams', '-of', 'json', str(path)], text=True))
    streams = probe.get('streams', [])
    if len(streams) != 1 or streams[0].get('codec_type') != 'audio' or \
            streams[0].get('codec_name') != 'pcm_f32le' or \
            int(streams[0].get('sample_rate', 0)) != RATE or streams[0].get('channels') != 1:
        raise ValueError('Voice finish requires native 24 kHz mono FLOAT audio; no conversion or resampling')
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-xerror', '-i', str(path),
        '-map', '0:a:0', '-f', 'f32le', 'pipe:1'])
    samples = array.array('f')
    samples.frombytes(raw)
    if sys.byteorder != 'little':
        samples.byteswap()
    if not samples or not all(math.isfinite(value) for value in samples):
        raise ValueError('Nonfinite or empty source-preserving PCM')
    return samples


def _db(value):
    return 20 * math.log10(value) if value > 0 else -999.0


def _range(row, count, kind):
    a, b = row.get('start_sample'), row.get('end_sample')
    if not (_integer(a) and _integer(b) and 0 <= a < b <= count):
        raise ValueError('Invalid integer source range: ' + kind)
    if not isinstance(row.get('reason'), str) or not row['reason'].strip():
        raise ValueError('Explain each source range: ' + kind)
    return a, b


def prepare_pcm(samples, plan, source_sha256):
    """Validate a plan and return float32 PCM plus independently calculated evidence.

    The returned speech samples keep source order and spacing. Only documented
    constant/ramped gain changes their values; only verified quiet is deleted.
    """
    count = len(samples)
    if not isinstance(plan, dict) or plan.get('sample_rate') != RATE or \
            plan.get('source_sha256') != source_sha256:
        raise ValueError('Plan source hash/sample-rate binding mismatch')
    if any(key not in {'sample_rate', 'source_sha256', 'cuts', 'gain_knots',
                        'protected', 'note'} for key in plan):
        raise ValueError('Unsupported voice-finish operation in plan')
    protected = []
    for row in plan.get('protected', []):
        protected.append(_range(row, count, 'protected speech/breath'))
    cuts = []
    last = 0
    for row in plan.get('cuts', []):
        a, b = _range(row, count, 'quiet cut')
        if not 0 < a < b < count or a < last or b - a > round(MAX_CUT_SECONDS * RATE):
            raise ValueError('Cuts must be ordered, internal and at most .30 seconds each')
        if not protected:
            raise ValueError('Explicit protected speech/breath intervals required for quiet cuts')
        if any(a < end and b > start for start, end in protected):
            raise ValueError('Quiet cut overlaps protected speech/breath')
        quiet = samples[a:b]
        rms = math.sqrt(sum(value * value for value in quiet) / len(quiet))
        peak = max(abs(value) for value in quiet)
        if _db(rms) > MAX_CUT_RMS_DBFS or _db(peak) > MAX_CUT_PEAK_DBFS:
            raise ValueError('Cut is not measured quiet below RMS/peak limits')
        cuts.append({'start_sample': a, 'end_sample': b, 'reason': row['reason'],
                     'samples_removed': b-a, 'rms_dbfs': _db(rms), 'peak_dbfs': _db(peak)})
        last = b
    removed = sum(row['samples_removed'] for row in cuts)
    if removed > min(round(MAX_TOTAL_CUT_SECONDS * RATE), count * MAX_TOTAL_CUT_FRACTION):
        raise ValueError('Total quiet deletion exceeds source-preserving bound')
    knots = plan.get('gain_knots')
    if not isinstance(knots, list) or len(knots) < 2:
        raise ValueError('At least two explicit gain knots required')
    for index, row in enumerate(knots):
        sample, gain = row.get('sample'), row.get('gain_db')
        if not _integer(sample) or not 0 <= sample <= count or not _finite_number(gain) or abs(gain) > MAX_GAIN_DB:
            raise ValueError('Invalid or excessive gain knot')
        if index:
            prior = knots[index-1]
            if sample <= prior['sample'] or abs(gain-prior['gain_db']) * RATE > \
                    MAX_SLEW_DB_PER_SECOND * (sample-prior['sample']) + 1e-9:
                raise ValueError('Gain knots must be ordered and within slew limit')
    if knots[0]['sample'] != 0 or knots[-1]['sample'] != count:
        raise ValueError('Gain plan must cover the complete source including its tail')
    gained = array.array('f')
    gain_segment = 0
    for sample, value in enumerate(samples):
        while sample >= knots[gain_segment+1]['sample'] and gain_segment+2 < len(knots):
            gain_segment += 1
        left, right = knots[gain_segment:gain_segment+2]
        gain_db = left['gain_db'] + (right['gain_db']-left['gain_db']) * \
            (sample-left['sample']) / (right['sample']-left['sample'])
        gained.append(value if gain_db == 0 else value * 10 ** (gain_db / 20))
    for row in cuts:
        a, b = row['start_sample'], row['end_sample']
        step = abs(gained[b]-gained[a-1])
        if step > MAX_JOIN_STEP:
            raise ValueError('Quiet-cut join exceeds sample-step bound')
        row['after_gain_join_step'] = step
    out = array.array('f')
    cursor = 0
    retained = []
    for row in cuts:
        a, b = row['start_sample'], row['end_sample']
        out.extend(gained[cursor:a]); retained.append({'start_sample': cursor, 'end_sample': a})
        cursor = b
    out.extend(gained[cursor:]); retained.append({'start_sample': cursor, 'end_sample': count})
    return out, {'source_samples': count, 'output_samples': len(out), 'samples_removed': removed,
        'quiet_cuts': cuts, 'retained_source_ranges': retained,
        'source_pcm_sha256': hashlib.sha256(_bytes(samples)).hexdigest(),
        'expected_output_pcm_sha256': hashlib.sha256(_bytes(out)).hexdigest(),
        'gain_model': 'Piecewise-linear dB on original source sample indices',
        'preservation': 'Every retained float32 sample is exactly source PCM times the documented gain; no time/phoneme warping'}


def _stats(samples, text):
    from audio_derivation import VALIDATION_DEFAULTS
    lim = VALIDATION_DEFAULTS
    duration = len(samples) / RATE
    peak = max(abs(v) for v in samples)
    rms = math.sqrt(sum(v*v for v in samples) / len(samples))
    clipped = sum(abs(v) >= .9999 for v in samples) / len(samples)
    wpm = len(text.split()) * 60 / duration
    if not all(math.isfinite(v) for v in samples) or \
            not lim['min_segment_seconds'] <= duration <= lim['max_segment_seconds'] or \
            peak >= lim['max_peak'] or rms < lim['min_rms'] or \
            clipped > lim['max_clipped_sample_fraction'] or \
            not lim['min_words_per_minute'] <= wpm <= lim['max_words_per_minute']:
        raise ValueError('Voice finish failed original worker mechanical safeguards')
    return {'sample_rate': RATE, 'samples': len(samples), 'duration_seconds': duration,
        'peak': peak, 'rms': rms, 'clipped_sample_fraction': clipped,
        'estimated_words_per_minute': wpm, 'mechanical_checks': 'PASS',
        'human_listening_review': 'PENDING', 'text_completeness': 'REQUIRES_FRESH_ASR'}


def _source(folder, sid):
    from audio_derivation import check_unit
    meta = check_unit(folder, sid)
    if meta.get('status') != 'GENERATED_REQUIRES_REVIEW' or meta.get('derivation'):
        raise ValueError('Use an untouched generated source; do not stack voice finishes')
    return meta


def validate(folder, meta):
    """Reconstruct expected PCM from locally retained raw source; no approval."""
    folder = Path(folder)
    sid = meta.get('segment_id')
    if not isinstance(sid, str) or not re.fullmatch(r'[a-zA-Z0-9_-]+', sid):
        raise ValueError('Unsafe finished source id')
    d = meta.get('derivation', {})
    if d.get('kind') != KIND or any(d.get(key) is not False for key in
            ('pitch_shift', 'tempo_changed', 'eq_applied', 'compression_applied',
             'resampled', 'new_generation', 'retry_budgets_reset')) or d.get('passes_from_original') != 1:
        raise ValueError('Unsupported or stacked voice-finish processing')
    parent = folder / 'finish-source'
    source_meta = _source(parent, sid)
    source = parent / 'raw' / (sid + '.wav')
    if _sha(source) != d.get('source_wav_sha256') or _sha(str(source)+'.json') != d.get('source_metadata_sha256'):
        raise ValueError('Changed voice-finish source binding')
    if source_meta.get('settings') != meta.get('settings') or source_meta.get('provenance') != meta.get('provenance'):
        raise ValueError('Voice finish changed source text, settings or generation provenance')
    expected, evidence = prepare_pcm(_decode(source), d.get('plan'), _sha(source))
    output = folder / 'raw' / (sid + '.wav')
    actual = _decode(output)
    if _sha(output) != meta.get('wav_sha256') or _bytes(actual) != _bytes(expected):
        raise ValueError('Finished PCM differs from exact source-preserving reconstruction')
    if d.get('preservation_evidence') != evidence:
        raise ValueError('Stale voice-finish preservation evidence')
    if meta.get('audio') != _stats(actual, source_meta['settings']['text']):
        raise ValueError('Stale voice-finish mechanical evidence')
    return meta


def render(source, dest, sid, plan):
    """Create one separate source-bound raw derivative, never a video or selected default."""
    from narration_edit import _copy_unit
    if not isinstance(sid, str) or not re.fullmatch(r'[a-zA-Z0-9_-]+', sid):
        raise ValueError('Unsafe source id')
    source, dest = Path(source), Path(dest)
    meta = _source(source, sid)
    wav = source / 'raw' / (sid + '.wav')
    values, evidence = prepare_pcm(_decode(wav), plan, _sha(wav))
    stats = _stats(values, meta['settings']['text'])
    out = dest / 'raw' / (sid + '.wav')
    if out.exists() or Path(str(out)+'.json').exists() or (dest/'finish-source').exists():
        raise FileExistsError('Voice-finish destination already contains source or output')
    out.parent.mkdir(parents=True, exist_ok=True)
    _copy_unit(source, dest / 'finish-source', sid)
    subprocess.run(['ffmpeg', '-v', 'error', '-n', '-f', 'f32le', '-ar', str(RATE),
        '-ac', '1', '-i', 'pipe:0', '-c:a', 'pcm_f32le', str(out)],
        input=_bytes(values), check=True)
    result = {**meta, 'schema': 'earnalism.video.source-preserving-finish.v1',
        'status': 'DERIVED_REQUIRES_REVIEW', 'output_path': str(out), 'wav_sha256': _sha(out),
        'derived_at_utc': datetime.now(timezone.utc).isoformat(), 'audio': stats,
        'publication_approved': False,
        'derivation': {'kind': KIND, 'source_wav_sha256': _sha(wav),
            'source_metadata_sha256': _sha(str(wav)+'.json'), 'plan': plan,
            'preservation_evidence': evidence, 'passes_from_original': 1,
            'pitch_shift': False, 'tempo_changed': False, 'eq_applied': False,
            'compression_applied': False, 'resampled': False, 'new_generation': False,
            'retry_budgets_reset': False, 'fresh_alignment_required': True,
            'listening_review': 'PENDING; finishing cannot manufacture emotional engagement'}}
    Path(str(out)+'.json').write_text(json.dumps(result, indent=2)+'\n')
    return validate(dest, result)
