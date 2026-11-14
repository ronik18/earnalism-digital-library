"""Action-scoped release decisions. No provider, generation or mutation operations.

Text timing is inapplicable only to the reviewed standalone audio consumer. A
warning is not a confirmed defect, and neither kind of finding can replace a
missing mandatory fidelity/rights/playback/accounting acceptance.
"""
from __future__ import annotations

import hashlib
import json
import re
import math
import subprocess
import tempfile
import wave
import html
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from backend.domain.audio_quality import classify_quality_findings
from backend.domain.editorial_release_policy import (
    uses_automated_editorial_policy, routine_review_not_applicable,
)

# The historical native contract stays immutable; current delivery binds its own source.
CONSUMER_CONTRACT = ROOT / 'internal/earnalism_intelligence/listener_reader_language_text_sync_consumer_20261113.json'
FEATURES_OFF = {key: False for key in (
    'read_along', 'highlighting', 'captions', 'text_linked_navigation',
)}
SHA = re.compile(r'^[a-f0-9]{64}$')
CONSUMER_SOURCES = (
    'frontend/src/App.js',
    'frontend/src/experiences-v2/listener/ListenerExperienceV2Route.jsx',
    'frontend/src/experiences-v2/listener/ListenerExperienceV2.jsx',
    'frontend/src/lib/audioPackageManifest.js',
    'frontend/src/lib/audiobookPlayback.js',
    'frontend/src/experiences-v2/reader/ReaderExperienceV2Route.jsx',
    'frontend/src/experiences-v2/shared/ReleaseTruthAdapter.js',
    'frontend/src/pages/Reader.jsx',
    'frontend/src/pages/BookDetail.jsx',
    'frontend/src/lib/audioReleaseSafety.js',
    'frontend/src/components/ReaderAudiobookPanel.jsx',
    'frontend/src/components/PremiumListeningRail.jsx',
)


def _binding(manifest: Mapping[str, Any]) -> dict:
    audio = manifest.get('audio') if isinstance(manifest.get('audio'), Mapping) else {}
    source = manifest.get('manuscript') if isinstance(manifest.get('manuscript'), Mapping) else {}
    return {'slug': manifest.get('slug'), 'audio_sha256': audio.get('sha256'),
            'manuscript_sha256': source.get('sha256'),
            'package_version': audio.get('package_version'),
            'release_descriptor_sha256': manifest.get('release_descriptor_sha256')}


def validate_sync_not_applicable(manifest: Mapping[str, Any], check: Mapping[str, Any]) -> None:
    """Verify source/consumer and exact candidate binding; unknown defaults strict.

    This does not waive package/schema/sidecar integrity, content or media clocks.
    The registry records one reviewed consumer, not a title-name exception.
    """
    proof = check.get('applicability')
    if check.get('status') != 'NOT_APPLICABLE' or not isinstance(proof, dict):
        raise ValueError('text sync requires measured acceptance or verified NOT_APPLICABLE evidence')
    contract = json.loads(CONSUMER_CONTRACT.read_text(encoding='utf-8'))
    if (contract.get('schema') != 'earnalism.reviewed_text_sync_consumer.v1'
            or contract.get('consumer') != 'listener_v2_audio_only.v1'
            or not isinstance(contract.get('sources'), dict)
            or set(contract['sources']) != set(CONSUMER_SOURCES)
            or any(not isinstance(v, str) or not SHA.fullmatch(v) for v in contract['sources'].values())):
        raise ValueError('complete reviewed consumer source contract is required')
    binding = _binding(manifest)
    if (not isinstance(binding['slug'], str) or not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,119}', binding['slug'])
            or any(not isinstance(binding[k], str) or not SHA.fullmatch(binding[k])
                   for k in ('audio_sha256', 'manuscript_sha256', 'release_descriptor_sha256'))
            or not isinstance(binding['package_version'], str)
            or not re.fullmatch(r'sha256-[a-f0-9]{64}', binding['package_version'])):
        raise ValueError('text-sync applicability must bind exact source, audio, descriptor and package')
    for record in (manifest, manifest.get('audio') or {}):
        if (any(key in record and record[key] is not False for key in ('highlight_sync_enabled', 'read_along_enabled', 'captions_enabled', 'text_linked_navigation_enabled'))
                or (record.get('sync_tier') is not None and record['sync_tier'] not in {'AUDIO_ONLY_NO_SYNC', 'NONE', 'NO_SYNC'})
                or (record.get('sync_mode') is not None and record['sync_mode'] not in {'none', 'audio_only'})):
            raise ValueError('an unsynced release must disable text-sync features and make no sync claim')
    delivery = manifest.get('delivery')
    expected_delivery = {'consumer': contract['consumer'],
                         'route': f"/listener/{binding['slug']}",
                         'features': FEATURES_OFF, 'sync_claim': 'NONE'}
    if delivery != expected_delivery or any(type(v) is not bool for v in delivery['features'].values()):
        raise ValueError('nonconsumer acceptance requires disabled text-sync features; retired customer features cannot be restored')
    if (proof.get('schema') != 'earnalism.text_sync_applicability.v1'
            or proof.get('status') != 'NOT_APPLICABLE'
            or proof.get('binding') != binding or proof.get('delivery') != delivery
            or proof.get('consumer_sources') != contract['sources']):
        raise ValueError('text-sync nonconsumer evidence is missing, stale or bound to another candidate')
    # Verify actual local consumer bytes, not a caller-supplied unused-feature flag.
    for relative, expected in contract['sources'].items():
        path = ROOT / relative
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('selected consumer source changed; reassess text-sync applicability')


def automated_check_accepted(manifest: Mapping[str, Any], name: str,
                             check: Mapping[str, Any]) -> bool:
    try:
        automated_editorial = uses_automated_editorial_policy(manifest)
    except ValueError:
        return False
    if (automated_editorial and name == 'audio_review_samples'
            and dict(check) == routine_review_not_applicable()):
        return True
    # Historical measured PASS is evidence, never permission to restore retired UI.
    for record in (manifest, manifest.get('audio') or {}):
        if any(key in record and record[key] is not False for key in (
            'read_along_enabled', 'highlight_sync_enabled', 'text_linked_navigation_enabled',
        )):
            return False
    delivery = manifest.get('delivery') or {}
    features = delivery.get('features') or {}
    if any(key in features and features[key] is not False for key in (
        'read_along', 'highlighting', 'text_linked_navigation',
    )):
        return False
    if check.get('status') == 'PASS':
        if automated_editorial:
            try:
                validate_bound_automated_check(manifest, name, check, ROOT)
            except (ValueError, OSError, KeyError, TypeError):
                return False
        return True
    if name != 'synchronization' or check.get('status') != 'NOT_APPLICABLE':
        return False
    try:
        validate_sync_not_applicable(manifest, check)
    except (ValueError, OSError, KeyError, TypeError):
        return False
    return True


def automated_candidate_binding(manifest: Mapping[str, Any]) -> dict:
    audio = manifest.get('audio') or {}
    return {**_binding(manifest), 'model': audio.get('model'), 'voice': audio.get('voice'),
            'duration_seconds': audio.get('duration_seconds')}


def validate_bound_automated_check(manifest: Mapping[str, Any], name: str,
                                  check: Mapping[str, Any], root: Path) -> dict:
    """Read and checksum exact-candidate evidence at evaluation AND promotion."""
    if check.get('status') != 'PASS':
        raise ValueError(f'{name} requires actual automated PASS evidence')
    path = root / str(check.get('evidence_path') or '')
    expected = check.get('evidence_sha256')
    data = path.read_bytes() if path.is_file() else b''
    if (not isinstance(expected, str) or not SHA.fullmatch(expected)
            or not path.is_file() or hashlib.sha256(data).hexdigest() != expected):
        raise ValueError(f'{name} evidence checksum mismatch or missing file')
    evidence = json.loads(data)
    if (not isinstance(evidence, dict)
            or evidence.get('schema') != 'earnalism.automated_release_check.v1'
            or evidence.get('check') != name or evidence.get('status') != 'PASS'
            or evidence.get('binding') != automated_candidate_binding(manifest)):
        raise ValueError(f'{name} evidence is not bound to this exact candidate')
    return {**dict(check), 'status': 'PASS', 'evidence_path': str(path.resolve()),
            'binding': evidence['binding']}


def automated_candidate_blockers(manifest: Mapping[str, Any]) -> list[str]:
    """Validate the complete candidate, never treat a pilot set as a full master.

    Human-review exemption does not authorize generation or publication. Existing
    runtime credentials, rights checks, exact gate and private staging still bind.
    """
    try:
        if not uses_automated_editorial_policy(manifest):
            return []
    except ValueError as exc:
        return [str(exc)]
    issues = []
    audio = manifest.get('audio') or {}
    source = manifest.get('manuscript') or {}
    if not isinstance(audio, Mapping) or not isinstance(source, Mapping):
        return ['Complete audio and manuscript metadata are required']
    if manifest.get('owner_public_release_intent') is not True:
        issues.append('Explicit job publication authority is required')
    if manifest.get('release_holds') or manifest.get('publication_hold') is True:
        issues.append('An existing release hold remains active')
    if (not isinstance(manifest.get('slug'), str)
            or not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,119}', manifest['slug'])):
        issues.append('A valid title slug is required')
    if not audio.get('path') or not audio.get('model') or not audio.get('voice'):
        issues.append('A complete master path, model and voice are required')
    for label, value in [('audio', audio.get('sha256')), ('manuscript', source.get('sha256')),
                         ('descriptor', manifest.get('release_descriptor_sha256'))]:
        if not isinstance(value, str) or not SHA.fullmatch(value):
            issues.append(f'Exact {label} checksum binding is required')
    if (not isinstance(audio.get('package_version'), str)
            or not re.fullmatch(r'sha256-[a-f0-9]{64}', audio['package_version'])):
        issues.append('An immutable audio package version is required')
    duration = audio.get('duration_seconds')
    if type(duration) not in (int, float) or not 0 < duration < float('inf'):
        issues.append('A finite positive full-master duration is required')
    root = Path(str(manifest.get('artifact_root') or ROOT))
    path = root / str(audio.get('path') or '')
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != audio.get('sha256'):
        issues.append('Full master is missing or changed after candidate preparation')
    return issues


# This optional adapter adds audiovisual dependencies to the existing release
# governor. It neither manufactures evidence nor introduces a second controller.
AV_FILES = ('manuscript', 'narration', 'scored_audio', 'timing', 'storyboard', 'score_plan')
AV_DIMENSIONS = ('naturalness', 'pronunciation', 'emotional_expression', 'punctuation_pause',
                 'pacing', 'continuity', 'anti_robotic_texture', 'anti_choppy_join', 'listener_enjoyment')
AV_FATAL_FLAGS = ('robotic_texture_detected', 'mechanical_cadence_detected',
                  'list_reading_rhythm_detected', 'choppy_joins_detected', 'fallback_tts_detected')


def audiovisual_binding(manifest: Mapping[str, Any]) -> dict:
    """Stable review identity; excludes receipts so they cannot hash themselves."""
    av = manifest.get('audiovisual') or {}
    return {key: av.get(key) for key in (
        'schema', 'title', 'language', 'territory', 'scope', 'files', 'outputs', 'destinations',
        'caption_files',
    )} | {'slug': manifest.get('slug')}


def audiovisual_candidate_sha256(manifest: Mapping[str, Any]) -> str:
    data = json.dumps(audiovisual_binding(manifest), ensure_ascii=False,
                      sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def _av_ref(ref, root: Path, label: str) -> Path:
    if not isinstance(ref, dict) or set(ref) != {'path', 'sha256'}:
        raise ValueError(f'{label}: exact path and sha256 reference required')
    if not isinstance(ref['path'], str) or not ref['path'] or not isinstance(ref['sha256'], str) or not SHA.fullmatch(ref['sha256']):
        raise ValueError(f'{label}: invalid path/checksum')
    path = root / ref['path']
    if not path.is_file():
        raise ValueError(f'{label}: file is missing')
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != ref['sha256']:
        raise ValueError(f'{label}: file changed after candidate preparation')
    return path


def _av_json(path: Path) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    data = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON number')))
    if not isinstance(data, dict):
        raise ValueError('JSON object required')
    return data


def _av_number(value, minimum=0, maximum=math.inf) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and minimum <= value <= maximum


def _av_probe(path: Path) -> dict:
    result = subprocess.run(['ffprobe', '-v', 'error', '-protocol_whitelist', 'file,pipe',
                             '-format_whitelist', 'wav,mp3,flac,mov,matroska,png_pipe,jpeg_pipe,image2', '-show_streams', '-show_format',
                             '-of', 'json', str(path)], capture_output=True, text=True,
                            timeout=60, check=False)
    if result.returncode:
        raise ValueError('media probe failed')
    return json.loads(result.stdout)


def _av_media_outputs(outputs: list, paths: list[Path], duration_ms: int) -> list[dict]:
    """Actually probe and decode bytes; a caller's PASS boolean is insufficient."""
    measurements = []
    for output, path in zip(outputs, paths):
        probe = _av_probe(path)
        video = [s for s in probe.get('streams', []) if s.get('codec_type') == 'video']
        audio = [s for s in probe.get('streams', []) if s.get('codec_type') == 'audio']
        if len(video) != 1 or len(audio) != 1 or video[0].get('codec_name') != 'h264' or audio[0].get('codec_name') != 'aac':
            raise ValueError('delivery requires exactly one H.264 video and AAC audio stream')
        width, height = video[0].get('width', 0), video[0].get('height', 0)
        if min(width, height) <= 0 or (output['format'] == 'landscape') != (width > height):
            raise ValueError('output dimensions do not match the independent delivery composition')
        numerator, denominator = str(video[0].get('avg_frame_rate', '0/1')).split('/')
        fps = float(numerator) / float(denominator)
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError('positive measured delivery frame rate required')
        actual_ms = float(probe.get('format', {}).get('duration', 'nan')) * 1000
        if not math.isfinite(actual_ms) or abs(actual_ms - duration_ms - 3000) > 150:
            raise ValueError('output duration must cover complete narration and the exact three-second END')
        decoded = subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-xerror',
                                  '-protocol_whitelist', 'file,pipe', '-format_whitelist', 'mov,matroska', '-i', str(path),
                                  '-f', 'null', '-'], capture_output=True, text=True,
                                 timeout=1800, check=False)
        if decoded.returncode or decoded.stderr.strip():
            raise ValueError('complete delivered-media decode failed')
        measurements.append({'format': output['format'], 'sha256': output['sha256'],
                             'width': width, 'height': height, 'duration_ms': round(actual_ms),
                             'fps': fps,
                             'video_codec': 'h264', 'audio_codec': 'aac', 'decode': 'COMPLETED'})
    return measurements


def _av_render_lineage(av: dict, paths: dict, technical: dict, root: Path, duration: int):
    """Independently verify source→PCM master→encoded audio→delivered packets."""
    from scripts.book_av_render import validate, _decode_pcm, _aac_payload, _timestamp, display_caption_text
    job = validate(paths['storyboard'])
    if (job['fixture_mode'] or job['manuscript']['language'] != av['language']
            or job['territory'] != av['territory']):
        raise ValueError('real renderer edition language/territory must match the selected audiovisual candidate')
    if not job['captions']:
        raise ValueError('the production audiovisual skill route requires measured readable captions and a verified delivery consumer')
    for name in ('manuscript', 'narration', 'scored_audio', 'timing'):
        if job[name]['sha256'] != av['files'][name]['sha256']:
            raise ValueError('renderer source/timing differs from the selected audiovisual candidate')
    report = _av_json(_av_ref(technical.get('render_report'), root, 'renderer report'))
    if (report.get('schema') != 'earnalism.book_av_render_report.v1'
            or report.get('fixture_mode') is not False
            or report.get('job_sha256') != av['files']['storyboard']['sha256']
            or report.get('scored_audio_sha256') != av['files']['scored_audio']['sha256']
            or report.get('timing_sha256') != av['files']['timing']['sha256']):
        raise ValueError('real source-bound renderer report required')
    reported_outputs = report.get('outputs')
    expected_outputs = {o['format']: (o['sha256'], str((root / o['path']).resolve())) for o in av['outputs']}
    if (not isinstance(reported_outputs, list) or len(reported_outputs) != len(expected_outputs)
            or {o.get('name'): (o.get('sha256'), str(Path(o.get('path', '')).resolve()))
                for o in reported_outputs} != expected_outputs):
        raise ValueError('renderer delivered-file set differs from the reviewed candidate')
    authored = {o['name']: (o['width'], o['height'], o['fps']) for o in job['outputs']}
    if {o.get('name'): (o.get('width'), o.get('height'), o.get('fps')) for o in reported_outputs} != authored:
        raise ValueError('renderer report differs from the authored delivery compositions')
    captions = av.get('caption_files', [])
    reported_captions = report.get('caption_files', [])
    if not isinstance(captions, list) or captions != reported_captions:
        raise ValueError('candidate-bound delivered captions differ from the renderer report')
    if job['captions']:
        if {c.get('format') for c in captions} != {'srt', 'vtt'} or len(captions) != 2:
            raise ValueError('both exact measured caption sidecars must be bound before release')
        cues = job['timing_data']['cues']
        expected_text = {
            'srt': '\n\n'.join(f"{i+1}\n{_timestamp(c['start_ms'], True)} --> {_timestamp(c['end_ms'], True)}\n{html.escape(display_caption_text(c['text']), quote=False)}"
                               for i, c in enumerate(cues)) + '\n',
            'vtt': 'WEBVTT\n\n' + '\n\n'.join(f"{_timestamp(c['start_ms'])} --> {_timestamp(c['end_ms'])}\n{html.escape(display_caption_text(c['text']), quote=False)}"
                                              for c in cues) + '\n',
        }
        for ref in captions:
            if set(ref) != {'format', 'path', 'sha256'}:
                raise ValueError('invalid caption reference')
            path = _av_ref({k: ref[k] for k in ('path', 'sha256')}, root, 'caption')
            if path.read_text(encoding='utf-8') != expected_text[ref['format']]:
                raise ValueError('delivered captions differ from the exact measured source timing')
    elif captions:
        raise ValueError('caption artifacts require the measured caption renderer')
    _av_soundtrack_lineage(job, paths, report, root, duration)
    return authored


def _av_soundtrack_lineage(job: dict, paths: dict, report: dict, root: Path, duration: int):
    """Technical byte-lineage check; synthetic tests confer no acceptance."""
    from scripts.book_av_render import _decode_pcm, _decode_end_pcm, _aac_payload
    soundtrack = report.get('soundtrack') or {}
    encoded = report.get('encoded_soundtrack') or {}
    master_path = _av_ref({k: soundtrack.get(k) for k in ('path', 'sha256')}, root, 'soundtrack master')
    encoded_path = _av_ref({k: encoded.get(k) for k in ('path', 'sha256')}, root, 'encoded soundtrack')
    with tempfile.TemporaryDirectory(prefix='book-av-lineage-') as folder:
        work = Path(folder)
        source, end = work / 'source.pcm', work / 'end.pcm'
        source_size = _decode_pcm(paths['scored_audio'], source)
        expected_body_bytes = duration * 48 * 6
        if source_size % 6 or abs(source_size - expected_body_bytes) > 48 * 6:
            raise ValueError('scored source clock differs from measured timing')
        _decode_end_pcm(job['outputs'][0]['end_clip']['path'], end)
        if end.stat().st_size != 3000 * 48 * 6:
            raise ValueError('approved END audio must be exactly three seconds')
        for i, output in enumerate(job['outputs'][1:]):
            other = work / f'end-{i}.pcm'
            _decode_end_pcm(output['end_clip']['path'], other)
            if other.read_bytes() != end.read_bytes():
                raise ValueError('delivery END soundtracks differ')
        with wave.open(str(master_path), 'rb') as master:
            if (master.getnchannels(), master.getsampwidth(), master.getframerate(), master.getnframes()) != (2, 3, 48000, source_size // 6 + 3000 * 48):
                raise ValueError('soundtrack master PCM format/frame count differs')
            with source.open('rb') as original:
                remaining = source_size
                while remaining:
                    frames = min(65536, remaining // 6)
                    block = original.read(frames * 6)
                    if master.readframes(frames) != block:
                        raise ValueError('soundtrack master changed the scored narration body')
                    remaining -= len(block)
            with end.open('rb') as original:
                for block in iter(lambda: original.read(65536 * 6), b''):
                    if master.readframes(len(block) // 6) != block:
                        raise ValueError('soundtrack master changed the approved END audio')
        expected_encoded = work / 'expected.m4a'
        encoded_result = subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-n',
                                         '-protocol_whitelist', 'file,pipe', '-format_whitelist', 'wav', '-i', str(master_path),
                                         '-map', '0:a:0', '-c:a', 'aac', '-b:a', '192k', str(expected_encoded)],
                                        capture_output=True, timeout=1800, check=False)
        if encoded_result.returncode:
            raise ValueError('independent soundtrack encoding verification failed')
        payload = _aac_payload(expected_encoded)
        if _aac_payload(encoded_path) != payload:
            raise ValueError('encoded soundtrack does not derive from the verified PCM master')
        for output in report['outputs']:
            if _aac_payload(root / output['path']) != payload:
                raise ValueError('delivered video does not contain the verified soundtrack')


def measure_audiovisual(manifest: Mapping[str, Any], root: Path, render_report: dict) -> dict:
    """Produce real technical measurements only; never editorial/release acceptance."""
    av = manifest.get('audiovisual')
    if (not isinstance(av, dict) or av.get('schema') != 'earnalism.book_audiovisual.v1'
            or av.get('fixture_mode', False) is not False or av.get('scope') != 'full_title'):
        raise ValueError('a real complete-title audiovisual manifest is required')
    files = av.get('files') or {}
    if set(files) != set(AV_FILES):
        raise ValueError('complete immutable audiovisual files required')
    paths = {name: _av_ref(files[name], root, name) for name in AV_FILES}
    timing = _av_json(paths['timing'])
    duration = timing.get('duration_ms')
    if type(duration) is not int or duration <= 0:
        raise ValueError('positive measured source duration required')
    technical = {'schema': 'earnalism.book_av_technical.v1',
                 'candidate_sha256': audiovisual_candidate_sha256(manifest),
                 'status': 'MEASURED', 'fixture_mode': False, 'render_report': render_report,
                 'provenance': 'Local independent source/END PCM equality, deterministic AAC payload lineage, actual stream measurements and complete decode; no listening or editorial inference.'}
    authored = _av_render_lineage(av, paths, technical, root, duration)
    output_paths = [_av_ref({k: output[k] for k in ('path', 'sha256')}, root, 'output') for output in av['outputs']]
    technical['outputs'] = _av_media_outputs(av['outputs'], output_paths, duration)
    if {o['format']: (o['width'], o['height'], o['fps']) for o in technical['outputs']} != authored:
        raise ValueError('actual delivery composition differs from the supported renderer job')
    return technical


def audiovisual_acceptance(manifest: Mapping[str, Any], root: Path) -> dict:
    """Evaluate selected book AV assets, real review and destination-bound decision.

    Receipt provenance is evidence supplied by the authorized operator, not proof
    of who heard a recording. No local parser can independently certify rights or
    subjective perception. Missing or stale evidence remains blocking.
    """
    if 'audiovisual' not in manifest:
        return {'status': 'NOT_SELECTED', 'blockers': []}
    issues, measurements = [], []
    av = manifest['audiovisual']
    try:
        if not isinstance(av, dict) or av.get('schema') != 'earnalism.book_audiovisual.v1':
            raise ValueError('supported audiovisual schema required')
        if av.get('fixture_mode', False) is not False or av.get('scope') != 'full_title':
            raise ValueError('only a real complete-title audiovisual candidate can qualify')
        if av.get('language') not in {'en', 'bn'} or not re.fullmatch('[A-Z]{2}', str(av.get('territory', ''))):
            raise ValueError('explicit supported language and territory required')
        if not isinstance(av.get('title'), str) or not av['title'].strip():
            raise ValueError('audiovisual title required')
        destinations = av.get('destinations')
        if (not isinstance(destinations, list) or not destinations
                or any(not isinstance(v, str) or not v.strip() for v in destinations)
                or len(set(destinations)) != len(destinations)):
            raise ValueError('exact nonduplicate destinations required')
        files = av.get('files')
        if not isinstance(files, dict) or set(files) != set(AV_FILES):
            raise ValueError('complete audiovisual immutable file set required')
        paths = {name: _av_ref(files[name], root, name) for name in AV_FILES}
        for name, binding_key in (('manuscript', 'manuscript'), ('narration', 'audio')):
            if files[name]['sha256'] != (manifest.get(binding_key) or {}).get('sha256'):
                raise ValueError(f'{name} must match the authoritative release manifest')
        text = paths['manuscript'].read_text(encoding='utf-8')
        timing = _av_json(paths['timing'])
        if (timing.get('schema') != 'earnalism.audiobook_score.timing.v1'
                or timing.get('method') not in {'measured_word_alignment', 'human_verified_audio'}
                or (timing.get('provenance') or {}).get('boundary_validation') != 'accepted'
                or timing.get('manuscript_sha256') != files['manuscript']['sha256']
                or timing.get('narration_sha256') != files['narration']['sha256']):
            raise ValueError('source-bound measured timing required; estimated/fixture timing cannot qualify')
        duration = timing.get('duration_ms')
        if type(duration) is not int or duration <= 0:
            raise ValueError('finite positive measured full-title duration required')
        previous_end = previous_text = 0
        seen = set()
        cues = timing.get('cues')
        if not text.strip() or not isinstance(cues, list) or not cues:
            raise ValueError('complete manuscript and measured cues required')
        for cue in cues:
            if not isinstance(cue, dict):
                raise ValueError('invalid measured cue')
            start, end, ts, te = (cue.get(k) for k in ('start_ms', 'end_ms', 'text_start', 'text_end'))
            if (any(type(v) is not int for v in (start, end, ts, te))
                    or not previous_end <= start < end <= duration
                    or not previous_text <= ts < te <= len(text)
                    or text[previous_text:ts].strip() or cue.get('text') != text[ts:te]
                    or not str(cue.get('text', '')).strip()
                    or not isinstance(cue.get('id'), str) or not cue['id'] or cue['id'] in seen):
                raise ValueError('cue omission, duplication, reordering or source/timing mismatch')
            seen.add(cue['id'])
            previous_end, previous_text = end, te
        if text[previous_text:].strip():
            raise ValueError('full-title ending is missing from measured coverage')
        for name in ('narration', 'scored_audio'):
            probe = _av_probe(paths[name])
            measured = float(probe.get('format', {}).get('duration', 'nan')) * 1000
            if not math.isfinite(measured) or abs(measured - duration) > 150:
                raise ValueError(f'{name} duration differs from the measured full-title clock')
        outputs = av.get('outputs')
        if (not isinstance(outputs, list) or not outputs or
                any(not isinstance(o, dict) or set(o) != {'format', 'path', 'sha256'} for o in outputs)
                or any(o['format'] not in {'landscape', 'portrait'} for o in outputs)
                or len({o['format'] for o in outputs}) != len(outputs)):
            raise ValueError('explicit independently composed delivery outputs required')
        output_paths = [_av_ref({k: o[k] for k in ('path', 'sha256')}, root, 'output') for o in outputs]
        candidate = audiovisual_candidate_sha256(manifest)
        evidence = av.get('evidence')
        if not isinstance(evidence, dict) or set(evidence) != {'rights', 'technical', 'full_review', 'decision'}:
            raise ValueError('rights, technical, full review and final decision receipts required')
        receipts = {}
        for name, ref in evidence.items():
            receipt = _av_json(_av_ref(ref, root, name))
            if (receipt.get('schema') != f'earnalism.book_av_{name}.v1'
                    or receipt.get('candidate_sha256') != candidate):
                raise ValueError(f'{name}: receipt is stale or bound to another candidate')
            if not isinstance(receipt.get('provenance'), str) or not receipt['provenance'].strip():
                raise ValueError(f'{name}: actual review/measurement provenance required')
            receipts[name] = receipt
        rights = receipts['rights']
        if (rights.get('status') != 'APPROVED' or rights.get('territory') != av['territory']
                or rights.get('destinations') != destinations):
            raise ValueError('applicable audiovisual rights territory/destination approval required')
        required_rights = {'literary_adaptation', 'translation', 'recording', 'voice_model',
                           'music_synchronization', 'visual_assets', 'commercial_distribution'}
        clearances = rights.get('clearances')
        if not isinstance(clearances, dict) or set(clearances) != required_rights:
            raise ValueError('complete audiovisual adaptation/voice/music/visual/distribution rights required')
        for name, ref in clearances.items():
            clearance = _av_json(_av_ref(ref, root, f'{name} rights'))
            if (clearance.get('status') != 'APPROVED' or clearance.get('commercial_use') is not True
                    or av['territory'] not in clearance.get('territories', [])
                    or not clearance.get('approval_ref') or not clearance.get('rights_holder')):
                raise ValueError(f'{name}: retained commercial rights evidence is incomplete')
        review = receipts['full_review']
        if (review.get('status') != 'ACCEPTED' or review.get('source') not in {'human', 'automatic'}
                or review.get('scope') != 'full_title' or review.get('duration_ms') != duration + 3000
                or review.get('formats') != [o['format'] for o in outputs]
                or review.get('unresolved_findings') != [] or review.get('fatal_flags') != []
                or not isinstance(review.get('observations'), str) or not review['observations'].strip()):
            raise ValueError('genuine complete final audiovisual/listening review with no unresolved findings required')
        caption_delivery = review.get('caption_delivery')
        if (not isinstance(caption_delivery, dict) or caption_delivery.get('status') != 'VERIFIED'
                or caption_delivery.get('destinations') != destinations
                or not isinstance(caption_delivery.get('consumer'), str) or not caption_delivery['consumer'].strip()
                or not isinstance(caption_delivery.get('provenance'), str) or not caption_delivery['provenance'].strip()):
            raise ValueError('actual measured-caption delivery consumer verification required')
        if av['language'] == 'bn':
            scores = review.get('dimensions')
            if (not _av_number(review.get('overall'), 8.9, 10)
                    or not _av_number(review.get('confidence'), .90, 1)
                    or not isinstance(scores, dict) or not set(AV_DIMENSIONS) <= set(scores)
                    or any(not _av_number(v, 8.9, 10) for v in scores.values())
                    or any(review.get(flag) is not False for flag in AV_FATAL_FLAGS)):
                raise ValueError('Bengali full-title overall/every dimension >=8.9, confidence >=0.90 and explicit absent fatal flags required')
        content = review.get('content_checks')
        if (not isinstance(content, dict)
                or content.get('first_words_match') is not True or content.get('last_words_match') is not True
                or any(type(content.get(k)) is not int or content[k] != 0
                       for k in ('missing_count', 'duplicated_count', 'reordered_count'))
                or (av['language'] == 'bn' and not _av_number(content.get('asr_manuscript_score'), 9.7, 10))):
            raise ValueError('full-title source fidelity, exact first/last words and zero omissions/duplicates/reordering required')
        decision = receipts['decision']
        if (decision.get('decision') != 'GO_LIVE' or decision.get('source') != 'owner'
                or decision.get('destinations') != destinations or not decision.get('action_ref')):
            raise ValueError('explicit owner action on this final candidate and destinations required')
        technical = receipts['technical']
        if technical.get('fixture_mode', False) is not False or technical.get('status') != 'MEASURED':
            raise ValueError('real measured technical receipt required; success labels cannot qualify media')
        if manifest.get('language', av['language']) != av['language']:
            raise ValueError('authoritative edition language differs from audiovisual language')
        authored = _av_render_lineage(av, paths, technical, root, duration)
        measurements = _av_media_outputs(outputs, output_paths, duration)
        if authored and {o['format']: (o['width'], o['height'], o['fps']) for o in measurements} != authored:
            raise ValueError('actual delivered dimensions/frame rate differ from authored compositions')
        if technical.get('outputs') != measurements:
            raise ValueError('technical receipt does not match independently measured delivered files')
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError, OverflowError, ZeroDivisionError, wave.Error) as exc:
        issues.append(str(exc))
    return {'status': 'BLOCKED' if issues else 'PASS', 'blockers': issues,
            'measurements': measurements, 'publication_performed': False}
