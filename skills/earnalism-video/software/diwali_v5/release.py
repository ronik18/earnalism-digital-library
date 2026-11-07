"""Read-only Diwali private-kit integrity adapter. Never authorizes publication."""
from pathlib import Path
import hashlib
import json
import subprocess

SCHEMA = 'earnalism.diwali-private-kit.v1'
REVIEW_SCHEMA = 'earnalism.diwali-private-review.v1'
ORIGINAL_SHA = '62647ee05557a6eab9fbee3d7c76334da3d9e6b99064b8acb90a80971d408aa4'
FORMATS = {'landscape': (1920, 1080), 'shorts': (1080, 1920), 'clean-landscape': (1920, 1080)}
REQUIRED = {
    *(name + '/video.mp4' for name in FORMATS),
    'narration-master.wav', 'soundtrack-master.wav', 'voice-binding.json',
    'captions.vtt', 'captions.srt', 'props.json', 'provider-word-times.json',
    'SOURCES.json', 'RESEARCH_REFRESH.json', 'asset-provenance.json',
    'TECHNICAL_QA.json', 'BROWSER_PLAYBACK.json', 'STATE.json',
    'asr-comparison.json', 'animation-provider-limit.json',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(folder, name):
    require(isinstance(name, str) and name and not Path(name).is_absolute(), 'Invalid bound path')
    result = (folder / name).resolve()
    require(result.is_relative_to(folder), 'Bound path escapes private kit')
    return result


def read(path):
    return json.loads(path.read_text())


def bound_review(folder, manifest):
    """Validate existing immutable evidence without rewriting it or inferred approvals."""
    require(manifest.get('schema') == SCHEMA, 'Unsupported Diwali private-kit schema')
    require(manifest.get('private') is True and manifest.get('publication_approved') is False,
            'Adapter accepts private, unapproved kits only')
    require(manifest.get('private_test') is not True, 'Test fixture cannot qualify as a private production kit')
    review_path = inside(folder, manifest['review_manifest'])
    require(sha(review_path) == manifest['review_manifest_sha256'], 'Changed review manifest')
    review = read(review_path)
    require(review.get('schema') == REVIEW_SCHEMA, 'Unsupported review manifest')
    require(review.get('private') is True and review.get('publication_approved') is False,
            'Review must remain private and unapproved')
    require(review.get('private_test') is not True, 'Test fixture review cannot qualify')
    files = review.get('files')
    require(isinstance(files, dict) and REQUIRED.issubset(files), 'Incomplete private-kit evidence coverage')
    for name, expected in files.items():
        require(isinstance(expected, str) and len(expected) == 64, 'Invalid bound digest')
        require(sha(inside(folder, name)) == expected, 'Changed bound file: ' + name)
    state = read(folder / 'STATE.json')
    require(state.get('publication_approved') is False and state.get('uploads') is False,
            'Existing public or approved state is outside the private adapter')
    require(state.get('private_test') is not True, 'Test fixture state cannot qualify')
    return review


def probe(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                             '-of', 'json', str(path)], capture_output=True, text=True, check=True)
    require(not result.stderr.strip(), 'Media probe reported an error')
    return json.loads(result.stdout)


def check_private(folder, project_root):
    folder, root = Path(folder).resolve(), Path(project_root).resolve()
    require(folder.is_relative_to(root), 'Candidate is outside the project')
    require(sha(root / 'Earnalism_English_Audiobook_Pipeline_Qwew&Ace.ipynb') == ORIGINAL_SHA,
            'Protected original notebook changed')
    manifest = read(folder / 'delivery-manifest.json')
    review = bound_review(folder, manifest)
    technical = read(folder / 'TECHNICAL_QA.json')
    require(technical.get('state') == 'PRIVATE_TECHNICAL_CHECKS_PASS', 'Technical evidence is not passing')
    evidence = {row['format']: row for row in technical['formats']}
    expected_duration = read(folder / 'props.json')['duration'] + 3
    packet_hashes = {}
    for name, dimensions in FORMATS.items():
        path = folder / name / 'video.mp4'
        require(evidence[name]['video_sha256'] == sha(path), 'Technical evidence is stale: ' + name)
        require(evidence[name]['faststart']['verified'] is True and
                evidence[name]['faststart']['moov_offset'] < evidence[name]['faststart']['mdat_offset'],
                'Fast-start evidence missing: ' + name)
        streams = probe(path)['streams']
        require(len(streams) == 2, 'Unexpected stream count: ' + name)
        video = next(x for x in streams if x['codec_type'] == 'video')
        audio = next(x for x in streams if x['codec_type'] == 'audio')
        require((video['width'], video['height']) == dimensions and video['codec_name'] == 'h264'
                and video['pix_fmt'] == 'yuv420p' and video['r_frame_rate'] == '30/1',
                'Incorrect video format: ' + name)
        require(abs(float(video['duration']) - expected_duration) < .002, 'Incomplete picture/ident: ' + name)
        require(audio['codec_name'] == 'aac' and audio['sample_rate'] == '48000' and audio['channels'] == 2,
                'Incorrect playback audio: ' + name)
        require(abs(float(audio['duration']) - expected_duration) < .05, 'Incomplete soundtrack: ' + name)
        result = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:a:0',
                                 '-c', 'copy', '-f', 'hash', '-hash', 'sha256', '-'],
                                capture_output=True, text=True, check=True)
        require(not result.stderr.strip(), 'Audio packet check failed: ' + name)
        packet_hashes[name] = result.stdout.strip()
    require(len(set(packet_hashes.values())) == 1, 'Soundtrack differs across formats')
    for name in ['narration-master.wav', 'soundtrack-master.wav']:
        audio = probe(folder / name)['streams'][0]
        require(audio['codec_name'] == 'pcm_s24le' and audio['sample_rate'] == '48000' and audio['channels'] == 2,
                'Incorrect WAV master: ' + name)
    return {
        'state': 'PRIVATE_KIT_INTEGRITY_VERIFIED_REQUIRES_ACCEPTANCE',
        'private_integrity_verified': True,
        'release_qualified': False,
        'publication_approved': False,
        'review_manifest_sha256': manifest['review_manifest_sha256'],
        'delivery_manifest_sha256': sha(folder / 'delivery-manifest.json'),
        'soundtrack_packet_identity': True,
        'listening': review['listening'],
        'pronunciation': review['pronunciation'],
        'motion_limitation': review['motion_limitation'],
        'primary_acceptance': 'Not supplied or inferred by this read-only integrity check',
        'scope': 'Bound files, current media streams/durations, technical evidence and identical AAC payloads. '
                 'No human factual, rights, visual or listening approval; no upload or publication permission.',
    }
