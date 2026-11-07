"""Read-only qualification of the explicit flat-interface refraction package.

This adapts the existing, immutable refraction evidence layout. It does not
render, upload, edit media, clear findings, or create an owner decision.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import xml.etree.ElementTree as ET

from caption_layout import quality

SCHEMA = 'earnalism.refraction-publication-profile.v1'
PLATFORM_SCHEMA = 'earnalism.platform-review.v1'
ORIGINAL_SHA = '62647ee05557a6eab9fbee3d7c76334da3d9e6b99064b8acb90a80971d408aa4'
CRITERIA = {'facts', 'graphics_captions', 'rights', 'listening_av', 'technical_delivery'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(pathlib.Path(path).read_text())


def inside(root, value):
    path = (root / value).resolve()
    require(path.is_relative_to(root.resolve()), 'Evidence path escapes project')
    return path


def binding(root, record):
    path = inside(root, record['path'])
    require(sha(path) == record['sha256'], 'Changed evidence: ' + record['path'])
    return path


def manifest(root, record):
    folder = inside(root, record['path'])
    path = folder / 'delivery-manifest.json'
    require(sha(path) == record['manifest_sha256'], 'Changed package manifest')
    entries = load(path)
    require(isinstance(entries, dict) and entries, 'Empty package manifest')
    for name, expected in entries.items():
        require(sha(inside(folder, name)) == expected, 'Changed package member: ' + name)
    return folder, entries


def tokens(text):
    return [('traveling' if word == 'travelling' else word) for word in
            re.findall(r"[a-z]+(?:'[a-z]+)?|\d+", text.lower().replace('’', "'"))]


def voice_check(source, parent):
    """Follow the actual six-unit original import, retaining ASR differences."""
    units = load(parent / 'units.json')
    records = load(source / 'asr-review.json')
    voice = load(parent / 'voice-binding.json')
    require(len(records) == len(units) and len({r['unit'] for r in records}) == len(units),
            'Incomplete source ASR coverage')
    require(sha(source / 'narration.wav') == sha(parent / 'narration.wav'),
            'Narration differs from original reviewed source')
    baseline = load(source / 'baseline-job.json')
    for unit in units:
        record = next((r for r in records if r['unit'] == unit['id']), None)
        require(record is not None and not record.get('differences'), 'Unresolved source ASR difference')
        raw = source / 'imported/raw' / (unit['id'] + '.wav')
        alignment = load(source / 'imported/alignment' / (unit['id'] + '.json'))
        metadata = load(str(raw) + '.json')
        digest = sha(raw)
        require(digest == record['audio_sha256'] == alignment['audio_sha256'] ==
                metadata['wav_sha256'] == voice['raw_audio'][unit['id']], 'Source audio binding failed')
        require(record['expected'] == unit['text'] == metadata['settings']['text'], 'Source script changed')
        require(tokens(record['recognized']) == tokens(unit['text']), 'ASR text does not match script')
        require(tokens(alignment['recognized']) == tokens(unit['text']), 'Alignment does not match script')
        if record.get('raw_differences'):
            resolution = record.get('resolution') or {}
            require(resolution.get('type') == 'orthographic_only' and resolution.get('audio_sha256') == digest,
                    'Unresolved raw ASR finding')
        settings = metadata['settings']
        require(settings['speaker'] == 'Ryan' and settings['generation'] == voice['generation'] ==
                baseline['generation'], 'Selected B generation settings changed')
        require(hashlib.sha256(settings['instruct'].encode()).hexdigest() == voice['instruction_sha256'],
                'Selected B direction changed')
        require(metadata['audio']['mechanical_checks'] == 'PASS', 'Source mechanical check failed')
    return len(records)


def captions_check(kit, parent):
    props = load(parent / 'props.json')
    cues = props['captions']
    require(cues and not quality(cues), 'Caption readability failed')
    for ext in ('srt', 'vtt'):
        require(sha(kit / ('delivery/english.' + ext)) == sha(parent / ('captions.' + ext)),
                'Delivered captions differ from actual-audio cues')
    require(tokens(' '.join(c['text'] for c in cues)) == tokens((parent / 'transcript.txt').read_text()),
            'Caption text differs from transcript')
    require(tokens((parent / 'transcript.txt').read_text()) ==
            tokens(' '.join(u['text'] for u in load(parent / 'units.json'))), 'Transcript differs from script')
    require(props.get('outro') is True and props.get('burnCaptions') is False,
            'Landscape must be clean and retain the standard ending')
    clean = load(kit / 'assets/clean-shorts-props.json')
    require(clean.get('burnCaptions') is False and clean.get('outro') is True and
            clean['captions'] == cues, 'Clean Shorts caption/ending configuration changed')
    portrait = load(parent / 'shorts-props.json')
    require({k: v for k, v in clean.items() if k != 'burnCaptions'} ==
            {k: v for k, v in portrait.items() if k != 'burnCaptions'},
            'Clean Shorts no longer inherits the reviewed independent portrait composition')
    return len(cues)


def timing_seconds(stamp):
    require(re.fullmatch(r'\d{2}:\d{2}:\d{2}\.\d{3}', stamp) is not None, 'Unsupported caption timestamp')
    hours, minutes, rest = stamp.split(':')
    require(int(minutes) < 60 and float(rest) < 60, 'Caption timestamp out of range')
    return int(hours) * 3600 + int(minutes) * 60 + float(rest)


def ttml_cues(path):
    """Only explicit regions, plain cue text and empty TTML line breaks."""
    text = pathlib.Path(path).read_text()
    require('<!DOCTYPE' not in text.upper(), 'Unsupported XML document type')
    document = ET.fromstring(text)
    ns = 'http://www.w3.org/ns/ttml'
    style = '{http://www.w3.org/ns/ttml#styling}'
    require(document.tag == '{' + ns + '}tt' and
            document.get('{http://www.w3.org/ns/ttml#parameter}timeBase') == 'media', 'Unsupported TTML time base')
    regions = {r.get('{http://www.w3.org/XML/1998/namespace}id'): r for r in document.findall('.//{' + ns + '}region')}
    require(regions and None not in regions, 'Missing TTML region')
    for region in regions.values():
        def percentages(name):
            values = region.get(style + name, '').split()
            require(len(values) == 2 and all(re.fullmatch(r'\d+(?:\.\d+)?%', v) for v in values), 'Missing TTML region geometry')
            return [float(v[:-1]) for v in values]
        origin, extent = percentages('origin'), percentages('extent')
        require(all(0 <= o < 100 and 0 < e <= 100 and o + e <= 100 for o, e in zip(origin, extent)) and
                region.get(style + 'displayAlign') in ('before', 'center', 'after'), 'Invalid TTML caption region')
    delivered = []
    for paragraph in document.findall('.//{' + ns + '}p'):
        require(paragraph.get('region') in regions, 'Missing or unsupported TTML cue region')
        caption_text = paragraph.text or ''
        for child in paragraph:
            require(child.tag == '{' + ns + '}br' and not child.attrib and not list(child) and
                    child.text in (None, ''), 'Unsupported TTML cue markup; only empty br is allowed')
            # A line break separates words; its tail must remain in equivalence checks.
            caption_text += '\n' + (child.tail or '')
        delivered.append({'start': timing_seconds(paragraph.get('begin', '')),
                          'end': timing_seconds(paragraph.get('end', '')), 'text': caption_text})
    return delivered


def positioned_caption_check(path, cues):
    """Allow delivery-only VTT/TTML placement, never a speech/timing edit."""
    if pathlib.Path(path).suffix.lower() in ('.ttml', '.xml', '.dfxp'):
        delivered = ttml_cues(path)
        caption_equivalence(delivered, cues)
        return
    blocks = re.split(r'\n\s*\n', pathlib.Path(path).read_text().replace('\r\n', '\n').strip())
    require(blocks and blocks[0] == 'WEBVTT', 'Position repair must be plain WebVTT')
    delivered = []
    for block in blocks[1:]:
        lines = block.splitlines()
        if '-->' not in lines[0]:
            require(len(lines) > 1 and lines[0].isdigit(), 'Unsupported caption block')
            lines = lines[1:]
        timing = re.fullmatch(r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3}) (.+)', lines[0])
        require(timing is not None and any(s.startswith('line:') for s in timing[3].split()),
                'Positioned caption is missing its line setting')
        settings = timing[3].split()
        require(len({s.split(':')[0] for s in settings}) == len(settings), 'Duplicate caption position setting')
        for setting in settings:
            require(re.fullmatch(r'(?:line|position|size):(?:100|\d{1,2})(?:\.\d+)?%|align:(?:start|middle|center|end)',
                                 setting) is not None, 'Unsupported caption positioning')
            if setting.endswith('%'):
                key, raw = setting.split(':'); percentage = float(raw[:-1])
                require(0 <= percentage <= 100 and (key != 'size' or percentage > 0),
                        'Caption position is out of range')
        delivered.append({'start': timing_seconds(timing[1]), 'end': timing_seconds(timing[2]), 'text': ' '.join(lines[1:])})
    caption_equivalence(delivered, cues)


def caption_equivalence(delivered, cues):
    require(len(delivered) == len(cues), 'Position repair dropped caption cues')
    for actual, expected in zip(delivered, cues):
        require(abs(actual['start'] - expected['start']) <= .0011 and
                abs(actual['end'] - expected['end']) <= .0011 and
                ' '.join(actual['text'].split()) == ' '.join(expected['text'].split()),
                'Position repair changed caption text or timing')


def facts_check(parent):
    sources = load(parent / 'sources.json')
    source_ids = {s['id'] for s in sources}
    require(sources and len(source_ids) == len(sources) and
            all(s.get('title') and s.get('url', '').startswith('https://') and s.get('claims') for s in sources),
            'Missing/duplicate factual sources')
    claims = load(parent / 'research-verification.json')['claims']
    require(claims and all(re.fullmatch(r'SUPPORTED(?:; .+)?', c.get('finding', '')) and c.get('support') for c in claims),
            'Unresolved factual finding')
    supported = {item.split()[0] for c in claims for item in c['support']}
    require(supported <= source_ids, 'Research refers to an unknown source')
    units = {u['id']: u['text'] for u in load(parent / 'units.json')}
    mapping = load(parent / 'claim-map.json')
    require(units and mapping and len(mapping) == len(units) and {c['unit'] for c in mapping} == set(units),
            'Missing spoken-claim coverage')
    for claim in mapping:
        require(claim.get('source_ids') and set(claim['source_ids']) <= supported and
                tokens(claim['text']) == tokens(units[claim['unit']]), 'Unverified spoken claim or source')


def graphics_check(review, root, kit, parent):
    """Require actual recorded visual judgments; frame counts cannot supply them."""
    required = {'opening', 'light_path', 'normal', 'virtual_image', 'lift_callback', 'outro'}
    inherited = load(parent / 'final-private-review.json')
    require(inherited.get('graphics') and inherited.get('browser') and inherited.get('captions'),
            'Missing inherited visual-review evidence')
    for fmt, path in [('landscape', kit / 'delivery/youtube-landscape.mp4'),
                      ('shorts', kit / 'assets/youtube-shorts.mp4')]:
        record = review['graphics'][fmt]
        require(record.get('source_sha256') == sha(path) and record.get('independent_composition') is True,
                'Stale or missing composition review')
        require(set(record.get('checkpoints_reviewed', [])) >= required and
                all(record.get(k) is True for k in ('narration_sync', 'labels_readable', 'caption_clearance')) and
                record.get('unresolved_findings', 'MISSING') == [], 'Unresolved graphical/caption finding')
        require(record.get('evidence'), 'Missing visual proof references')
        for evidence in record['evidence']:
            binding(root, evidence)


def run(args):
    return subprocess.run([str(a) for a in args], check=True, capture_output=True).stdout


def aac(path):
    return hashlib.sha256(run(['ffmpeg', '-v', 'error', '-i', path, '-map', '0:a:0',
                             '-c:a', 'copy', '-f', 'adts', '-'])).hexdigest()


def media_check(kit, parent, accepted_aac):
    landscape = kit / 'delivery/youtube-landscape.mp4'
    shorts = kit / 'assets/youtube-shorts.mp4'
    require(sha(landscape) == sha(parent / 'landscape/video.mp4'), 'Landscape source changed')
    technical = load(parent / 'landscape/technical.json')
    clean = load(kit / 'reviews/clean-shorts-technical.json')
    require(technical.get('decode') == 'PASS' and technical['sha256'] == sha(landscape),
            'Stale/failed landscape decoding evidence')
    require(clean['video_sha256'] == sha(shorts) and clean['full_decode_exit_code'] == 0,
            'Stale/failed Shorts decoding evidence')
    require(float(technical['loudness']['input_tp']) < -0.3, 'Unsafe encoded peak')
    timeline = load(parent / 'timeline.json')
    expected_seconds = timeline['visual_body_seconds'] + timeline['brand_seconds']
    for path, dimensions in ((landscape, (1920, 1080)), (shorts, (1080, 1920))):
        info = json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', path]))
        video = next(s for s in info['streams'] if s['codec_type'] == 'video')
        audio = next(s for s in info['streams'] if s['codec_type'] == 'audio')
        require((video['width'], video['height']) == dimensions and video['codec_name'] == 'h264' and
                video['pix_fmt'] == 'yuv420p' and audio['codec_name'] == 'aac', 'Unexpected delivery streams')
        require(abs(float(video['duration']) - float(audio['duration'])) < .15, 'Audio/video duration mismatch')
        require(abs(float(info['format']['duration']) - expected_seconds) < .1, 'Unexpected refraction duration')
        require(aac(path) == accepted_aac, 'Soundtrack differs from owner-accepted AAC')
    capture = load(parent / 'review/landscape-capture-check.json')
    require(not capture['issues'] and capture['frames_scanned'] >= 2700 and
            capture['muxed_master_sha256'] == sha(landscape) and
            capture['source_sha256'] == sha(parent / 'landscape/animation.mp4') and
            capture['muxed_video_payload_matches_scanned_animation'] is True, 'Landscape capture check failed/stale')
    require(not clean['capture_scan']['issues'] and clean['capture_scan']['frames_scanned'] >= 2700 and
            clean['capture_scan']['source_sha256'] == sha(shorts), 'Shorts capture check failed/stale')


def platform_check(review, kit_digest, caption_delivery_digest=None):
    require(review.get('schema') == PLATFORM_SCHEMA and review.get('kit_manifest_sha256') == kit_digest and
            review.get('reviewer') and review.get('scope'), 'Missing/stale platform review')
    require(review.get('unresolved_primary_findings', 'MISSING') == [], 'Unresolved primary platform finding')
    settings = review['settings']
    require(settings.get('audience') == 'not_made_for_kids' and
            settings.get('age_restriction') is False and settings.get('video_language') == 'English' and
            settings.get('metadata_language') == 'English' and settings.get('category') == 'Education',
            'Audience/language/category settings incomplete')
    require(all(settings.get(k) is False for k in ('automatic_dubbing', 'visual_enhancements',
                'audio_enhancements', 'automatic_chapters', 'automatic_places', 'automatic_concepts',
                'paid_promotion')) and settings.get('ai_use') is True and
            settings.get('required_hashtags') is True and settings.get('schedule', 'MISSING') is None,
            'Protected upload settings incomplete')
    for format_ in ('landscape', 'shorts'):
        video = review['videos'][format_]
        require(re.fullmatch(r'[A-Za-z0-9_-]{11}', video['video_id']) is not None, 'Invalid saved video ID')
        require(video['visibility'] == 'Private', 'Private review visibility required')
        require(all(video.get(k) is True for k in ('cover_reviewed', 'manual_english_selected',
                                                   'original_audio', 'hd_complete')), 'Platform review incomplete')
        require(video['copyright'] == 'No issues found', 'Unresolved platform copyright issue')
        require(video.get('remixing') == ('disabled' if format_ == 'landscape' else 'audio_only'),
                'Reviewed remix restriction changed')
        playback = video['playback']
        require(all(playback.get(k) is True for k in ('complete', 'seeking', 'replay_or_loop')) and
                playback.get('media_error', 'MISSING') is None, 'Platform playback review incomplete/failed')
    require(review['videos']['landscape']['video_id'] != review['videos']['shorts']['video_id'], 'Duplicate video ID')
    if caption_delivery_digest:
        require(review['videos']['shorts'].get('caption_delivery_sha256') == caption_delivery_digest,
                'Repaired caption delivery was not verified on platform')


def candidate_identity(kit_digest, caption_digest, platform):
    """Bind delivery changes, while timestamp-only rechecks retain approval validity."""
    identity = {'kit_manifest_sha256': kit_digest, 'caption_delivery_sha256': caption_digest,
                'settings': platform['settings'], 'videos': {fmt: {
                    'video_id': platform['videos'][fmt]['video_id'],
                    'remixing': platform['videos'][fmt]['remixing']}
                    for fmt in ('landscape', 'shorts')}}
    return hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def decision_check(decision, kit_digest, candidate_digest=None):
    if decision is None:
        return 'PRIMARY_CHECKS_READY_PENDING_OWNER_DECISION'
    require(decision.get('schema') == 'earnalism.final-owner-decision.v1' and
            decision.get('kit_manifest_sha256') == kit_digest and decision.get('reviewer') == 'Owner' and
            candidate_digest is not None and decision.get('candidate_sha256') == candidate_digest and
            decision.get('source') and decision.get('approved') is True and
            set(decision.get('criteria', [])) == CRITERIA, 'Missing/stale consolidated owner decision')
    return 'APPROVED_CANDIDATE_FOR_AUTHORIZED_PUBLICATION'


def check(profile_path, project_root):
    root = pathlib.Path(project_root).resolve()
    profile = load(profile_path)
    require(profile.get('schema') == SCHEMA, 'Unsupported publication profile')
    require(profile.get('private_test') is False, 'Test fixtures can never publish; production classification required')
    require(sha(root / 'Earnalism_English_Audiobook_Pipeline_Qwew&Ace.ipynb') == ORIGINAL_SHA,
            'Original audiobook checksum changed')
    kit, kit_entries = manifest(root, profile['kit'])
    parent, _ = manifest(root, profile['parent'])
    source, _ = manifest(root, profile['voice_source'])
    require(profile.get('profile') == 'flat-interface-refraction', 'Unsupported topic model')
    protected = load(kit / 'reviews/protected-sources.json')
    require(protected['parent_v4_manifest_sha256'] == profile['parent']['manifest_sha256'] and
            protected['selected_B_sha256'] == sha(parent / 'narration.wav'), 'Stale parent/voice binding')
    accepted = load(kit / 'reviews/owner-listening-feedback.json')
    require(accepted.get('reviewer') == 'Owner' and accepted.get('reply') ==
            'Music is acceptable across the full recording' and accepted.get('candidate_parent_manifest_sha256') ==
            profile['parent']['manifest_sha256'], 'Missing/stale actual listening acceptance')
    accepted_aac = accepted['accepted_encoded_aac_sha256']
    require(accepted_aac == protected['expected_shared_aac_sha256'], 'Listening soundtrack binding changed')
    resolution = load(kit / 'reviews/music-listening-resolution.json')
    require(resolution['acceptance'] == accepted, 'Listening resolution does not bind acceptance')
    require(resolution['flag_count'] == len(resolution['flags']) and resolution['original_flags_preserved'] is True,
            'Music findings were dropped')
    for finding in resolution['flags']:
        require(finding.get('listening_status') == 'REVIEWED_OWNER_ACCEPTED_EXACT_AUDIO',
                'Unresolved listening finding')
    asr_units = voice_check(source, parent)
    cue_count = captions_check(kit, parent)
    facts_check(parent)
    rights = load(kit / 'reviews/rights-provenance-check.json')
    require(rights['status'] == 'PROVENANCE_HASH_CHECKS_PASS' and rights['owner_brand_rights_record_matches'] is True,
            'Rights provenance incomplete')
    for record in rights['checks']:
        require(sha(inside(root, record['file'])) == record['sha256'], 'Rights source changed')
    rightsm = load(parent / 'rights-manifest.json')
    require(rightsm['visuals']['source_sha256'] == sha(parent / 'render-source/index.tsx') and
            rightsm['visuals']['geometry_sha256'] == sha(parent / 'render-source/geometry.mjs') and
            rightsm['narration']['celebrity_reference_or_clone'] is False, 'Visual/voice rights binding changed')
    geometry = run(['node', '--test', parent / 'render-source/test_geometry.mjs']).decode()
    media_check(kit, parent, accepted_aac)
    platform_path = binding(root, profile['platform_review'])
    caption_path = binding(root, profile['caption_delivery']) if profile.get('caption_delivery') else None
    if caption_path:
        positioned_caption_check(caption_path, load(parent / 'props.json')['captions'])
    current_review = load(platform_path)
    platform_check(current_review, profile['kit']['manifest_sha256'], sha(caption_path) if caption_path else None)
    basis = current_review['evidence_basis']
    binding(root, basis['pre_ingestion_audio_processing'])
    played = load(binding(root, basis['playback']))
    for fmt, dimensions in [('landscape', (1920, 1080)), ('shorts', (1080, 1920))]:
        records = played[fmt]
        require(len(records) == 1 and records[0].get('error', 'MISSING') is None,
                'Incomplete/failed complete player run')
        record = records[0]
        ranges = record['played']
        require((record['videoWidth'], record['videoHeight']) == dimensions and
                ranges and ranges[0][0] <= .001 and ranges[-1][1] >= record['duration'] - .001 and
                all(b[0] <= a[1] + .001 for a, b in zip(ranges, ranges[1:])), 'Player run has unplayed gaps')
    graphics_check(current_review, root, kit, parent)
    candidate_digest = candidate_identity(profile['kit']['manifest_sha256'],
                       sha(caption_path or kit / 'delivery/english.vtt'), current_review)
    decision = load(binding(root, profile['owner_decision'])) if profile.get('owner_decision') else None
    return {'state': decision_check(decision, profile['kit']['manifest_sha256'], candidate_digest),
            'kit_manifest_sha256': profile['kit']['manifest_sha256'], 'files_verified': len(kit_entries),
            'candidate_sha256': candidate_digest,
            'source_asr_units_verified': asr_units, 'caption_cues': cue_count,
            'accepted_aac_sha256': accepted_aac, 'geometry_executed': geometry.strip(),
            'publication_performed': False, 'human_acceptance': 'One consolidated final owner decision',
            'limits': ['Technical full playback and sampled visual checks are not continuous human viewing.',
                       'Exact accepted soundtrack listening is reused; no new hardware listening claimed.',
                       'Source provenance is not legal certainty or a prediction of later platform claims.']}
