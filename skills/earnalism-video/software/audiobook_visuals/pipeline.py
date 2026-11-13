"""Lean, explicit audio -> timed storyboard -> private illustrated review pipeline.

Semantic directions, exact source cues, rights and independent artwork are supplied
by the production editor. This module validates and renders; it does not invent
story understanding, alignment, artwork, listening acceptance or publication.
"""
from pathlib import Path
import argparse
import hashlib
import html
import json
import math
import re
import shutil
import subprocess
from fractions import Fraction

from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

SCHEMA = 'earnalism.audiobook-visuals.v1'
FORMATS = ('landscape', 'portrait')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def canonical(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def run(args, timeout=300):
    try:
        return subprocess.run([str(x) for x in args], check=True, capture_output=True,
                              text=True, timeout=timeout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f'{args[0]} failed: {e.stderr[-4000:]}') from e


def probe(path):
    return json.loads(run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams',
                          '-show_format', '-of', 'json', path]).stdout)


def audio_stream(p):
    streams = [s for s in p['streams'] if s['codec_type'] == 'audio']
    if len(streams) != 1:
        raise ValueError('Exactly one source audio stream is required')
    return streams[0]


def duration(p):
    return float(p['format']['duration'])


def bound(path, **metadata):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'sha256': sha(path), **metadata}


def resolve(binding, base):
    if not isinstance(binding, dict) or not binding.get('path'):
        raise ValueError('Explicit asset path/hash binding required')
    p = Path(binding['path'])
    p = (base / p).resolve(strict=True) if not p.is_absolute() else p.resolve(strict=True)
    if not p.is_file() or sha(p) != binding.get('sha256'):
        raise ValueError('Changed or missing source asset: ' + str(p))
    return p


def packet_hashes(path):
    p = json.loads(run(['ffprobe', '-v', 'error', '-select_streams', 'a:0',
                        '-show_packets', '-show_data_hash', 'sha256', '-of', 'json', path]).stdout)
    return [x['data_hash'] for x in p['packets']]


def describe_audio_conversion(source_probe, output_probe):
    def fmt(p):
        stream = audio_stream(p)
        return {k: stream.get(k) for k in ('codec_name', 'sample_fmt', 'sample_rate', 'channels', 'channel_layout')}
    source, output = fmt(source_probe), fmt(output_probe)
    sr_change = source['sample_rate'] != output['sample_rate']
    known_layouts = source['channel_layout'] is not None and output['channel_layout'] is not None
    ch_change = source['channels'] != output['channels'] or (known_layouts and source['channel_layout'] != output['channel_layout'])
    return {'source_audio_format': source, 'output_audio_format': output,
            'sample_rate_conversion': {'observed': sr_change,
                'method': 'FFmpeg default resampler via -ar' if sr_change else 'No sample-rate change observed'},
            'channel_conversion': {'observed': ch_change,
                'layout_comparison': 'Known layouts compared' if known_layouts else 'At least one layout unspecified; count alone does not certify mapping',
                'method': 'FFmpeg default -ac mapping; no custom mix weights supplied' if ch_change else 'No channel-count/known-layout change observed',
                'perceptual_review': 'PENDING; format probes do not establish perceived balance'},
            'derivative_PCM_identity': 'NOT_CLAIMED; original master retained unchanged'}


def video_timeline(path):
    data = json.loads(run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                          '-show_frames', '-show_entries',
                          'frame=best_effort_timestamp_time,pkt_duration_time,duration_time',
                          '-of', 'json', path]).stdout)
    frames = data.get('frames', [])
    if len(frames) < 2:
        raise ValueError('Motion requires actual decoded video frames, not a container/audio duration')
    points = [float(f['best_effort_timestamp_time']) for f in frames]
    if any(b <= a for a, b in zip(points, points[1:])):
        raise ValueError('Non-monotonic actual motion timestamps')
    durations = [float(f.get('duration_time', f.get('pkt_duration_time', 0))) for f in frames]
    last_duration = durations[-1] or (points[-1] - points[-2])
    return {'decoded_frames': len(frames), 'first_pts_seconds': points[0],
            'last_pts_seconds': points[-1], 'last_frame_duration_seconds': last_duration,
            'video_span_seconds': points[-1] + last_duration - points[0]}


def canonical_layouts(layouts):
    bridge = Path(__file__).with_name('layout.mjs')
    result = subprocess.run(['node', str(bridge)], input=json.dumps(layouts),
                            text=True, capture_output=True, timeout=15)
    if result.returncode:
        raise ValueError('Canonical brand/content clearance failed: ' + result.stderr[-3000:])
    return json.loads(result.stdout)


def init_plan(args):
    if args.plan.exists():
        raise FileExistsError('Preserve existing plans')
    audio = bound(args.audio)
    p = probe(audio['path']); audio_stream(p)
    if args.language not in ('en', 'bn'):
        raise ValueError('Supported private baseline languages: en, bn')
    cues = json.loads(args.cues.read_text())
    ids = [c['id'] for c in cues['cues']]
    data = {'schema': SCHEMA, 'private': True, 'publication_approved': False,
            'title': args.title, 'language': args.language,
            'audio': {**audio, 'actual_duration_seconds': duration(p)},
            'source_cues': bound(args.cues), 'font': bound(args.font),
            'fps': 30, 'preview_only': False, 'caption_mode': 'on',
            'style': {'background': '#F5F1E8', 'caption': '#171A1C'},
            'brand': {'logo': bound(args.logo, role='full_earnalism_lockup'),
                      'end': {'landscape': bound(args.end_landscape, role='approved_end'),
                              'portrait': bound(args.end_portrait, role='approved_end')}},
            'layouts': {'landscape': {'width': 1920, 'height': 1080},
                        'portrait': {'width': 1080, 'height': 1920}},
            'scenes': [{'id': 's1', 'cue_ids': ids,
                        'source_quote': '\n'.join(c['text'] for c in cues['cues']),
                        'visual': 'REPLACE: supplied source-grounded semantic direction',
                        'semantic_review': 'pending', 'assets': {
                            k: {'path': '', 'sha256': '', 'kind': 'still',
                                'composition': 'independently_composed',
                                'rights': '', 'content_note': ''} for k in FORMATS}}]}
    write(args.plan, data)
    return {'status': 'DRAFT_PLAN_CREATED_ASSETS_AND_SEMANTIC_REVIEW_REQUIRED', 'plan': str(args.plan)}


def compile_plan(path, *, _test_scope=False):
    path = Path(path).resolve(); base = path.parent
    data = json.loads(path.read_text())
    if data.get('schema') != SCHEMA or data.get('private') is not True or data.get('publication_approved') is not False:
        raise ValueError('Private source-bound plan schema required')
    language = data['language']
    if language not in ('en', 'bn') or data['fps'] not in (24, 25, 30):
        raise ValueError('Unsupported language/frame rate')
    audio = resolve(data['audio'], base); ap = probe(audio); audio_stream(ap)
    seconds = duration(ap)
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('Actual positive finite source duration required')
    if abs(seconds - data['audio']['actual_duration_seconds']) > .001:
        raise ValueError('Audio duration changed; rebind actual source')
    ms = round(seconds * 1000); fps = data['fps']; frames = math.ceil(seconds * fps - 1e-7)
    source = resolve(data['source_cues'], base); timed = json.loads(source.read_text())
    if timed.get('timing_status') not in ('source_reviewed', 'estimated', 'unverified') or not timed.get('timing_method'):
        raise ValueError('Explicit timing provenance required; estimated is not verified')
    cues = timed.get('cues', []); previous = 0; ids = []
    if not cues:
        raise ValueError('Exact timed source cues required')
    for c in cues:
        start, end = c['start_ms'], c['end_ms']; kind = c.get('kind')
        if type(start) is not int or type(end) is not int or start != previous or not start < end <= ms:
            raise ValueError('Cue gap, overlap, reordering or invalid time; represent rests explicitly')
        if kind not in ('narration', 'silence') or not isinstance(c.get('text'), str):
            raise ValueError('Cue kind/text invalid')
        if (kind == 'narration' and not c['text'].strip()) or (kind == 'silence' and c['text'] != ''):
            raise ValueError('Narration requires exact text; silence cue text must be empty')
        if not isinstance(c.get('id'), str) or not c['id']:
            raise ValueError('Nonempty source cue ID required')
        ids.append(c['id']); previous = end
    if len(set(ids)) != len(ids) or previous != ms:
        raise ValueError('Unique cues must cover the entire actual audio including rests')
    font = resolve(data['font'], base)
    if not features.check_feature('raqm'):
        raise ValueError('Pillow RAQM shaping required; do not render unshaped Bengali')
    shaped_font = ImageFont.truetype(str(font), 24, index=data['font'].get('index', 0),
                                    layout_engine=ImageFont.Layout.RAQM)
    caption_mode = data.get('caption_mode', 'on')
    if caption_mode not in ('on', 'off'):
        raise ValueError('caption_mode must be on or off')
    # A language tag is not a font-coverage check. Compare each used character
    # with the selected font's missing-glyph mask. This is a coverage check,
    # not certification of typography or of the spoken transcript.
    missing = shaped_font.getmask('\U0010ffff')
    missing_key = (missing.size, bytes(missing))
    if caption_mode == 'on':
        for char in set(''.join(c['text'] for c in cues)):
            if char.isspace() or char in '\u200c\u200d':
                continue
            mask = shaped_font.getmask(char)
            if (mask.size, bytes(mask)) == missing_key:
                raise ValueError(f'Selected font does not cover U+{ord(char):04X}')
    logo = resolve(data['brand']['logo'], base)
    if data['brand']['logo'].get('role') != 'full_earnalism_lockup':
        raise ValueError('Explicit full-logo role required')
    with Image.open(logo) as im:
        if im.mode != 'RGBA' or im.getextrema()[3] == (255, 255):
            raise ValueError('Bound video full logo must have genuine transparent alpha')
        if abs(im.width / im.height - 10 / 3) > .05:
            raise ValueError('Preserve complete 10:3 Earnalism lockup; do not crop/retype')
    if set(data['layouts']) != set(FORMATS):
        raise ValueError('Exactly landscape and portrait layouts required')
    canonical_regions = canonical_layouts(data['layouts'])
    expected_logo = canonical_regions['landscape']['brandAsset']['sha256']
    if data['brand']['logo']['sha256'] != expected_logo and not _test_scope:
        raise ValueError('Production logo must match canonical watermarkAsset SHA256')
    ends = {}; end_audio = None
    for name in FORMATS:
        layout = data['layouts'][name]; w, h = layout['width'], layout['height']
        if any(type(v) is not int or v < 160 or v % 2 for v in (w, h)) or (w > h) != (name == 'landscape'):
            raise ValueError('Independent even-sized delivery canvases required')
        standard = (1920, 1080) if name == 'landscape' else (1080, 1920)
        if (w, h) != standard and data.get('preview_only') is not True:
            raise ValueError('Smaller/different canvas requires explicit preview_only=true')
        layout['regions'] = canonical_regions[name]
        end = resolve(data['brand']['end'][name], base); ep = probe(end)
        videos = [s for s in ep['streams'] if s['codec_type'] == 'video']; ea = audio_stream(ep)
        if len(videos) != 1 or videos[0]['codec_name'] != 'h264' or ea['codec_name'] != 'aac':
            raise ValueError('Bound END must already be H264/AAC')
        v = videos[0]
        source_rate = Fraction(v['r_frame_rate']); stride = source_rate / fps
        if (v['width'], v['height']) != (w, h) or abs(duration(ep) - 3) > 1 / fps:
            raise ValueError('Bind approved three-second END for each actual canvas; no forced crop/retime')
        if stride.denominator != 1 or stride < 1 or int(v['nb_read_frames']) % int(stride):
            raise ValueError('END normalization supports exact integer frame decimation only, not guessed retiming')
        hashes = packet_hashes(end)
        if end_audio is not None and hashes != end_audio:
            raise ValueError('Both END compositions must share identical audio payload')
        end_audio = hashes
        ends[name] = {'path': str(end), 'probe': ep, 'audio_packets': hashes,
                     'frames': int(v['nb_read_frames']) // int(stride),
                     'normalization': {'frame_stride': int(stride), 'source_fps': str(source_rate),
                                       'target_fps': fps, 'source_master_unchanged': True}}
    index = {c['id']: i for i, c in enumerate(cues)}; used = []; scenes = []
    for scene in data['scenes']:
        if not scene.get('cue_ids') or any(x not in index for x in scene['cue_ids']):
            raise ValueError('Scene references a missing source cue')
        positions = [index[x] for x in scene['cue_ids']]
        if not positions or positions != list(range(positions[0], positions[-1] + 1)):
            raise ValueError('Scene cue selection must be consecutive and in source order')
        if scene['source_quote'] != '\n'.join(cues[i]['text'] for i in positions):
            raise ValueError('Changed or omitted exact source text')
        if not scene.get('visual', '').strip() or scene['visual'].startswith('REPLACE:'):
            raise ValueError('Editor-supplied semantic visual direction required')
        if scene.get('semantic_review') not in ('reviewed', 'pending'):
            raise ValueError('Record semantic review honestly')
        used.extend(scene['cue_ids']); start_ms = cues[positions[0]]['start_ms']; end_ms = cues[positions[-1]]['end_ms']
        start_frame = round(start_ms * fps / 1000); end_frame = frames if end_ms == ms else round(end_ms * fps / 1000)
        if end_frame <= start_frame:
            raise ValueError('Scene is too short for actual frame grid')
        assets = {}
        for name in FORMATS:
            a = scene['assets'][name]; asset = resolve(a, base)
            if a.get('composition') != 'independently_composed' or not a.get('rights') or not a.get('content_note'):
                raise ValueError('Independent composition, rights and content metadata required')
            if a['kind'] == 'still':
                with Image.open(asset) as im:
                    size = im.size; im.verify()
                actual = {'width': size[0], 'height': size[1]}
            elif a['kind'] == 'motion':
                pp = probe(asset); vv = [v for v in pp['streams'] if v['codec_type'] == 'video']
                timeline = video_timeline(asset)
                if len(vv) != 1 or timeline['video_span_seconds'] + 1e-5 < (end_frame - start_frame) / fps:
                    raise ValueError('Motion asset must cover the complete scene; no looping, speed-up or hidden freeze')
                actual = {'width': vv[0]['width'], 'height': vv[0]['height'],
                          'container_duration_seconds': duration(pp), 'source_fps': vv[0]['r_frame_rate'],
                          'actual_video_timeline': timeline}
            else:
                raise ValueError('Only supplied still/motion assets supported')
            assets[name] = {**a, 'path': str(asset), 'actual': actual, 'fit': 'contain_no_crop'}
        if assets['landscape']['sha256'] == assets['portrait']['sha256']:
            raise ValueError('Supply independently composed format assets, not an arbitrary forced crop')
        scenes.append({**scene, 'assets': assets, 'start_frame': start_frame, 'end_frame': end_frame})
    if used != ids or len({s['id'] for s in scenes}) != len(scenes):
        raise ValueError('Scenes must cover each cue exactly once, without omission/reordering')
    for c in cues:
        c['start_frame'] = round(c['start_ms'] * fps / 1000)
        c['end_frame'] = frames if c['end_ms'] == ms else round(c['end_ms'] * fps / 1000)
        if c['end_frame'] <= c['start_frame']:
            raise ValueError('Cue shorter than frame grid; correct source cues')
    return {'status': 'SOURCE_BOUND_PRIVATE_TECHNICAL_STORYBOARD_PREVIEW', 'private': True,
            'test_fixture_scope': _test_scope,
            'plan_path': str(path), 'plan_sha256': sha(path), 'plan': data,
            'audio_path': str(audio), 'audio_probe': ap, 'duration_seconds': seconds,
            'duration_ms': ms, 'body_frames': frames, 'body_duration_seconds': frames / fps,
            'alignment_padding_seconds': frames / fps - seconds,
            'cues': cues, 'scenes': scenes, 'font': str(font), 'logo': str(logo), 'ends': ends,
            'timing_status': timed['timing_status'], 'timing_method': timed['timing_method'],
            'caption_mode': caption_mode,
            'draft_timing_state': ('SOURCE_REVIEWED_TIMING_NOT_AUTOMATICALLY_VERIFIED'
                                   if timed['timing_status'] == 'source_reviewed'
                                   else 'PRIVATE_DRAFT_TIMING_UNVERIFIED'),
            'timing_verified_by_software': False,
            'semantic_fidelity': 'Editor supplied; not inferred or certified by compiler',
            'remaining': ['Full listening and AV review', 'Semantic/character fidelity and art review',
                          'Actual platform/device delivery review', 'One consolidated final release decision']}


def caption_overlay(compiled, name, cue, path):
    plan = compiled['plan']; layout = plan['layouts'][name]; w, h = layout['width'], layout['height']
    regions = layout['regions']; image = Image.new('RGBA', (w, h)); draw = ImageDraw.Draw(image)
    lb = regions['logo']; q = regions['brand']; sigma = q['blurPx']
    with Image.open(compiled['logo']) as original:
        # Preserve canonical fractional placement, ratio, alpha, opacity and halo.
        sx, sy = original.width / q['width'], original.height / q['height']
        lockup = original.transform((w, h), Image.Transform.AFFINE,
                     (sx, 0, -q['left'] * sx, 0, sy, -q['top'] * sy),
                     resample=Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(sigma))
        lockup.putalpha(lockup.getchannel('A').point(lambda a: round(a * q['opacity'])))
        image.alpha_composite(lockup)
    logo_ink = image.getbbox()
    safe = regions['safe']
    if logo_ink is None or not (safe[0] <= logo_ink[0] and safe[1] <= logo_ink[1]
                               and logo_ink[2] <= safe[2] and logo_ink[3] <= safe[3]):
        raise ValueError('Actual transparent logo pixels escape the safe region')
    receipt = {'cue_id': cue['id'], 'format': name, 'regions': regions,
               'logo_blur_sigma': sigma, 'logo_halo': q['blurOutset'], 'caption_ink': [],
               'actual_logo_ink': list(logo_ink),
               'shape_engine': 'Pillow RAQM', 'language': plan['language']}
    if compiled['timing_status'] != 'source_reviewed':
        status_font = ImageFont.truetype(compiled['font'], max(8, round(24 * regions['scale'])),
                                        index=plan['font'].get('index', 0),
                                        layout_engine=ImageFont.Layout.RAQM)
        status = 'PRIVATE DRAFT\nTIMING UNVERIFIED'
        db = regions['draft']
        sb = draw.multiline_textbbox((db[0], db[1]), status, font=status_font)
        if sb[2] > db[2] or sb[3] > db[3]:
            raise ValueError('Draft timing label collides with brand or picture')
        draw.multiline_text((db[0], db[1]), status, font=status_font, fill='#171A1C')
        receipt['visible_draft_status'] = 'PRIVATE_DRAFT_TIMING_UNVERIFIED'
        receipt['draft_status_ink'] = list(sb)
    if compiled['caption_mode'] == 'on' and cue['kind'] == 'narration':
        box = regions['caption']; pad = max(3, round(24 * regions['scale'])); language = plan['language']
        minimum = math.ceil(regions['captionMinPx'])
        preferred = max(minimum, round(regions['captionPreferredPx']))
        for size in range(preferred, minimum - 1, -1):
            font = ImageFont.truetype(compiled['font'], size, index=plan['font'].get('index', 0),
                                      layout_engine=ImageFont.Layout.RAQM)
            lines = []; line = ''
            for word in cue['text'].split():
                trial = (line + ' ' + word).strip()
                if draw.textlength(trial, font=font, language=language, direction='ltr') > box[2] - box[0] - 2 * pad and line:
                    lines.append(line); line = word
                else:
                    line = trial
            if line:
                lines.append(line)
            step = math.ceil(size * 1.5)
            if len(lines) <= 3 and len(lines) * step + 2 * pad <= box[3] - box[1] and all(draw.textlength(x, font=font, language=language, direction='ltr') <= box[2] - box[0] - 2 * pad for x in lines):
                break
        else:
            raise ValueError('Caption does not fit at the qualified phone-scale minimum; correct cue segmentation, do not omit or shrink text')
        draw.rounded_rectangle(box, radius=pad, fill=(23, 26, 28, 240))
        y = box[1] + (box[3] - box[1] - len(lines) * step) / 2
        for line in lines:
            x = (box[0] + box[2] - draw.textlength(line, font=font, language=language, direction='ltr')) / 2
            bbox = draw.textbbox((x, y), line, font=font, language=language, direction='ltr', anchor='lt')
            if not (box[0] + pad <= bbox[0] and bbox[2] <= box[2] - pad and box[1] <= bbox[1] and bbox[3] <= box[3]):
                raise ValueError('Actual shaped glyph bounds escape caption region')
            draw.text((x, y), line, font=font, language=language, direction='ltr', anchor='lt', fill='#F5F1E8')
            receipt['caption_ink'].append(list(bbox)); y += step
        receipt.update(font_size=size, displayed_lines=lines, source_text=cue['text'])
    if plan.get('preview_only'):
        receipt['preview_only'] = True
    image.save(path)
    receipt['caption_check'] = 'NOT_APPLICABLE' if compiled['caption_mode'] == 'off' else 'SHAPED_GLYPH_BOUNDS_MEASURED'
    return receipt


def concat_list(paths, file):
    file.write_text(''.join("file '" + str(p.resolve()).replace("'", "'\\''") + "'\n" for p in paths))


def prepare_audio(c, out):
    source = Path(c['audio_path']); retained = out / ('original-audio' + source.suffix)
    shutil.copy2(source, retained)
    end = Path(c['ends']['landscape']['path']); ea = audio_stream(c['ends']['landscape']['probe']); sa = audio_stream(c['audio_probe'])
    body = out / 'body-audio.m4a'; end_audio = out / 'end-audio.m4a'; total = out / 'shared-audio.m4a'
    compatible = sa['codec_name'] == 'aac' and (sa['sample_rate'], sa['channels']) == (ea['sample_rate'], ea['channels']) and abs(c['alignment_padding_seconds']) < .0001
    if compatible:
        run(['ffmpeg', '-v', 'error', '-i', source, '-map', '0:a:0', '-c:a', 'copy', body])
        mode = 'AAC_PACKET_COPY'; assert packet_hashes(body) == packet_hashes(source)
    else:
        # The complete original precedes only a documented subframe trailing pad.
        run(['ffmpeg', '-v', 'error', '-i', source, '-map', '0:a:0', '-af',
             f"apad,atrim=duration={c['body_duration_seconds']:.9f}", '-ar', ea['sample_rate'],
             '-ac', ea['channels'], '-c:a', 'aac', '-b:a', '192k', body])
        mode = 'DOCUMENTED_AAC_DERIVATIVE_NO_TRIM_OR_RETIME_OF_SOURCE'
    run(['ffmpeg', '-v', 'error', '-i', end, '-map', '0:a:0', '-c:a', 'copy', end_audio])
    assert packet_hashes(end_audio) == packet_hashes(end)
    listing = out / 'audio-concat.txt'; concat_list([body, end_audio], listing)
    run(['ffmpeg', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', listing, '-map', '0:a:0', '-c:a', 'copy', total])
    hashes = packet_hashes(total)
    if hashes != packet_hashes(body) + packet_hashes(end_audio):
        raise ValueError('Audio concat changed/omitted payload; do not claim original soundtrack preservation')
    return {'mode': mode, 'source_retained': retained.name, 'source_sha256': sha(retained),
            'source_duration_seconds': c['duration_seconds'], 'trailing_frame_alignment_pad_seconds': c['alignment_padding_seconds'],
            'shared_audio': total.name, 'shared_audio_sha256': sha(total),
            'payload_sha256': canonical(hashes), 'end_audio_packet_payload_preserved': True,
            'listening_acceptance': 'NOT_ESTABLISHED_BY_TECHNICAL_CHECK',
            **describe_audio_conversion(c['audio_probe'], probe(total))}


def prepare_end(c, name, folder):
    end = c['ends'][name]; source = Path(end['path']); stride = end['normalization']['frame_stride']
    if stride == 1:
        return source, {'mode': 'BOUND_ORIGINAL_VIDEO_PACKET_COPY', 'source_sha256': sha(source)}
    v = next(s for s in end['probe']['streams'] if s['codec_type'] == 'video')
    normalized = folder / 'END-normalized-high-private.mp4'; fps = c['plan']['fps']
    color_args = []
    for key, option in [('color_range', '-color_range'), ('color_space', '-colorspace'),
                        ('color_transfer', '-color_trc'), ('color_primaries', '-color_primaries')]:
        if v.get(key) not in (None, 'unknown', 'unspecified'):
            color_args += [option, v[key]]
    run(['ffmpeg', '-v', 'error', '-i', source, '-map', '0:v:0', '-map', '0:a:0',
         '-vf', f'select=not(mod(n\\,{stride})),setpts=N/({fps}*TB)', '-r', fps,
         '-frames:v', end['frames'], '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-profile:v', 'high',
         '-bf', '0', '-g', fps * 2, '-keyint_min', fps * 2, '-sc_threshold', '0',
         '-pix_fmt', 'yuv420p', *color_args, '-c:a', 'copy', '-movflags', '+faststart', normalized])
    if packet_hashes(normalized) != packet_hashes(source):
        raise ValueError('END normalization changed original audio payload')
    comparison = run(['ffmpeg', '-v', 'info', '-i', source, '-i', normalized,
        '-filter_complex', f"[0:v]select='not(mod(n,{stride}))',setpts=N/({fps}*TB),format=yuv420p[ref];[1:v]setpts=PTS-STARTPTS,format=yuv420p[derived];[derived][ref]psnr",
        '-an', '-f', 'null', '-']).stderr
    summary = next((line for line in comparison.splitlines() if 'PSNR y:' in line), '')
    if not summary:
        raise ValueError('END selected-frame comparison did not complete')
    metrics = {key: value for key, value in re.findall(r'(y|u|v|average|min|max):([^\s]+)', summary)}
    actual = probe(normalized); video = next(s for s in actual['streams'] if s['codec_type'] == 'video')
    return normalized, {'mode': 'STANDARD_HIGH_H264_FRAME_RATE_NORMALIZATION_DERIVATIVE_PRIVATE',
        'source_sha256': sha(source), 'derivative_path': str(normalized), 'derivative_sha256': sha(normalized),
        'frame_stride': stride, 'source_fps': end['normalization']['source_fps'], 'target_fps': fps,
        'actual_profile': video.get('profile'), 'actual_duration_seconds': duration(actual),
        'source_frame_selection': f'every {stride} source frame, starting at zero; no retiming',
        'selected_source_frame_comparison_psnr_dB': metrics,
        'source_decoded_pixel_identity': 'NOT_CLAIMED_LOSSY_NORMALIZATION',
        'source_END_audio_packet_payload_identical': True, 'source_MP4_bytes_identical': False,
        'quality_review': 'PENDING_EXISTING_AV_REVIEW', 'native_platform_qualification': 'NOT_ESTABLISHED'}


def subtitle(cues, path, web=False):
    def stamp(ms):
        hh, rem = divmod(ms, 3600000); mm, rem = divmod(rem, 60000); ss, sub = divmod(rem, 1000)
        return f'{hh:02}:{mm:02}:{ss:02}{"." if web else ","}{sub:03}'
    chunks = ['WEBVTT\n\n'] if web else []
    for i, cue in enumerate(cues):
        if cue['kind'] == 'narration':
            chunks.append(f'{i + 1}\n{stamp(cue["start_ms"])} --> {stamp(cue["end_ms"])}\n{cue["text"]}\n\n')
    path.write_text(''.join(chunks))


def render(plan, output, *, _test_scope=False):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError('Never overwrite a prior candidate or original')
    c = compile_plan(plan, _test_scope=_test_scope); output.mkdir(parents=True); write(output / 'compiled.json', c)
    shutil.copy2(plan, output / 'source-plan.json'); audio = prepare_audio(c, output)
    delivery_cues = c['cues'] if c['caption_mode'] == 'on' else []
    subtitle(delivery_cues, output / 'captions.srt'); subtitle(delivery_cues, output / 'captions.vtt', True)
    fps = c['plan']['fps']; receipts = []; outputs = {}; end_treatments = {}
    for name in FORMATS:
        folder = output / name; folder.mkdir(); segments = []; layout = c['plan']['layouts'][name]
        w, h = layout['width'], layout['height']; pb = layout['regions']['picture']; pw, ph = pb[2] - pb[0], pb[3] - pb[1]
        for i, cue in enumerate(c['cues']):
            scene = next(s for s in c['scenes'] if cue['id'] in s['cue_ids']); asset = scene['assets'][name]
            overlay = folder / f'overlay-{i:04}.png'; measured = caption_overlay(c, name, cue, overlay)
            measured.update(scene_id=scene['id'], asset_path=asset['path'], asset_sha256=asset['sha256'],
                            asset_fit='contain_no_crop', rendered_asset_region=pb,
                            clearance_scope='Actual shaped text and logo pixels measured; entire supplied artwork is contained in the separate picture region. Not a semantic/artistic or native-platform certification.')
            receipts.append(measured)
            segment = folder / f'segment-{i:04}.mp4'; inputs = ['-loop', '1'] if asset['kind'] == 'still' else ['-ss', str((cue['start_frame'] - scene['start_frame']) / fps)]
            n = cue['end_frame'] - cue['start_frame']; seconds = n / fps
            filt = f"[0:v]scale={pw}:{ph}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={pw}:{ph}:(ow-iw)/2:(oh-ih)/2:color=0xF5F1E8,setpts=PTS-STARTPTS,setsar=1,fps={fps}[art];color=c=0xF5F1E8:s={w}x{h}:r={fps}:d={seconds}[bg];[bg][art]overlay={pb[0]}:{pb[1]}:eof_action=pass:repeatlast=0[base];[base][1:v]overlay=0:0:eof_action=pass:repeatlast=0,format=yuv420p[v]"
            run(['ffmpeg', '-v', 'error', *inputs, '-i', asset['path'], '-loop', '1', '-i', overlay,
                 '-filter_complex', filt, '-map', '[v]', '-frames:v', n, '-an', '-c:v', 'libx264',
                 '-preset', 'veryfast', '-crf', '18', '-profile:v', 'high', '-bf', '0', '-g', fps * 2,
                 '-keyint_min', fps * 2, '-sc_threshold', '0',
                 '-r', fps, '-movflags', '+faststart', segment], timeout=max(300, seconds * 15))
            segments.append(segment)
        body_list = folder / 'body-concat.txt'; concat_list(segments, body_list); body = folder / 'body.mp4'
        run(['ffmpeg', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', body_list, '-map', '0:v:0', '-c:v', 'copy', body])
        end_picture, end_treatments[name] = prepare_end(c, name, folder)
        video_list = folder / 'video-concat.txt'; concat_list([body, end_picture], video_list)
        picture = folder / 'picture-with-end.mp4'
        run(['ffmpeg', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', video_list, '-map', '0:v:0', '-an', '-c:v', 'copy', picture])
        final = output / (name + '-review.mp4')
        run(['ffmpeg', '-v', 'error', '-i', picture, '-i', output / audio['shared_audio'],
             '-map', '0:v:0', '-map', '1:a:0', '-c', 'copy', '-movflags', '+faststart', final])
        outputs[name] = {'path': final.name, 'sha256': sha(final), 'expected_frames': c['body_frames'] + c['ends'][name]['frames']}
    write(output / 'layout-receipts.json', receipts)
    manifest = {'schema': SCHEMA, 'private': True, 'publication_approved': False,
                'status': 'TECHNICAL_STORYBOARD_PREVIEW_NOT_FINISHED_ANIMATION',
                'test_fixture_scope': _test_scope,
                'end_treatments': end_treatments,
                'plan_sha256': c['plan_sha256'], 'audio': audio, 'outputs': outputs,
                'timing_status': c['timing_status'], 'timing_verified_by_software': False,
                'draft_timing_state': c['draft_timing_state'], 'caption_mode': c['caption_mode'],
                'preview_only': c['plan'].get('preview_only', False),
                'artistic_semantic_listening_AV_acceptance': 'PENDING', 'files': {}}
    for f in [output / 'compiled.json', output / 'source-plan.json', output / 'captions.srt', output / 'captions.vtt', output / 'layout-receipts.json', output / audio['shared_audio'], output / audio['source_retained']]:
        manifest['files'][f.name] = sha(f)
    for treatment in end_treatments.values():
        if 'derivative_path' in treatment:
            path = Path(treatment['derivative_path'])
            manifest['files'][str(path.relative_to(output))] = sha(path)
    write(output / 'manifest.json', manifest)
    title = html.escape(c['plan']['title'])
    (output / 'index.html').write_text(f'<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{title} · Private</title><style>body{{max-width:1000px;margin:30px auto;padding:18px;background:#F5F1E8;color:#171A1C;font:18px system-ui}}video{{width:100%;max-height:80vh;background:#171A1C}}</style><h1>{title}</h1><p>PRIVATE — TECHNICAL STORYBOARD PREVIEW, NOT FINISHED ANIMATION. {"SMALLER PREVIEW ONLY. " if c["plan"].get("preview_only") else ""}{html.escape(c["draft_timing_state"])}. Caption mode: {c["caption_mode"]}. Semantic, art, full listening and audiovisual review remain pending. This is not a cinematic 3D result or publication.</p>' + ''.join(f'<h2>{n.title()}</h2><video controls playsinline preload="metadata" src="{n}-review.mp4"></video>' for n in FORMATS))
    return check(output)


def frame_hashes(path, start=None):
    # A source-to-END color-property change can reinitialize FFmpeg filters and
    # reset trim's n/start_frame counter. Hash the complete actual decoded stream,
    # then select its absolute frame range in Python, independent of filter state.
    args = ['ffmpeg', '-v', 'error', '-i', path, '-an', '-vf', 'format=rgb24']
    text = run(args + ['-f', 'framemd5', '-'], timeout=300).stdout
    hashes = [line.rsplit(',', 1)[-1].strip() for line in text.splitlines() if line and not line.startswith('#')]
    if start is not None and (type(start) is not int or not 0 <= start < len(hashes)):
        raise ValueError('Requested END start outside actual decoded frame sequence')
    return hashes if start is None else hashes[start:]


def check(output):
    output = Path(output); m = json.loads((output / 'manifest.json').read_text()); c = json.loads((output / 'compiled.json').read_text())
    if m.get('private') is not True or m.get('publication_approved') is not False:
        raise ValueError('Private output manifest required')
    for n, value in m['files'].items():
        if sha(output / n) != value:
            raise ValueError('Changed candidate artifact: ' + n)
    plan = c['plan']; base = Path(c['plan_path']).parent
    bindings = [plan['audio'], plan['source_cues'], plan['font'], plan['brand']['logo']]
    bindings += [plan['brand']['end'][name] for name in FORMATS]
    bindings += [s['assets'][name] for s in c['scenes'] for name in FORMATS]
    for binding in bindings:
        resolve(binding, base)
    if sha(c['audio_path']) != m['audio']['source_sha256']:
        raise ValueError('Original audio binding changed')
    shared = packet_hashes(output / m['audio']['shared_audio']); result = {}
    for name in FORMATS:
        item = m['outputs'][name]; path = output / item['path']
        if sha(path) != item['sha256']:
            raise ValueError('Changed final MP4')
        run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'null', '-'], timeout=600)
        pp = probe(path); v = next(s for s in pp['streams'] if s['codec_type'] == 'video')
        if int(v['nb_read_frames']) != item['expected_frames'] or packet_hashes(path) != shared:
            raise ValueError('Final frame count or shared exact audio payload changed')
        if abs(duration(pp) - (c['body_duration_seconds'] + 3)) > .15:
            raise ValueError('Unexpected final duration')
        end_reference = m['end_treatments'][name].get('derivative_path', c['ends'][name]['path'])
        unchanged_end = frame_hashes(path, c['body_frames']) == frame_hashes(end_reference)
        if not unchanged_end:
            raise ValueError('Decoded approved END frames changed')
        result[name] = {'sha256': item['sha256'], 'full_decode': True,
                        'actual_frames': int(v['nb_read_frames']), 'actual_duration_seconds': duration(pp),
                        'shared_audio_packet_payload_identical': True, 'decoded_END_reference_frames_identical': True,
                        'END_comparison_reference': ('recorded_normalization_derivative' if 'derivative_path' in m['end_treatments'][name] else 'bound_original')}
    audio_observed = {**m['audio'], **describe_audio_conversion(c['audio_probe'], probe(output / m['audio']['shared_audio']))}
    report = {'status': 'TECHNICAL_CHECKS_COMPLETED_PRIVATE_REVIEW_PENDING', 'private': True,
              'publication_approved': False, 'outputs': result, 'audio': audio_observed,
              'end_treatments': m['end_treatments'],
              'timing_status': m['timing_status'], 'timing_verified_by_software': False,
              'draft_timing_state': m['draft_timing_state'],
              'caption_check': ('NOT_APPLICABLE' if m['caption_mode'] == 'off' else 'RENDERED_BOUNDS_MEASURED_SYNC_NOT_LISTENED'),
              'preview_only': m['preview_only'], 'test_fixture_scope': m['test_fixture_scope'],
              'final_release_qualification': ('HELD_TEST_FIXTURE' if m['test_fixture_scope'] else
                                              'HELD_PREVIEW_ONLY' if m['preview_only'] else
                                              'HELD_TIMING_UNVERIFIED' if m['timing_status'] != 'source_reviewed'
                                              else 'UNQUALIFIED_PENDING_ACTUAL_AV_AND_FINAL_DECISION'),
              'scope': 'Hashes, full decode, coverage, measured caption/logo regions and audio/END preservation only.',
              'not_established': ['Semantic fidelity', 'Artistic quality', 'Natural character action',
                                  'Actual full listening/AV acceptance', 'Native platform/device playback', 'Publication approval']}
    write(output / 'technical-receipt.json', report)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='command', required=True)
    i = sub.add_parser('init'); i.add_argument('audio', type=Path); i.add_argument('plan', type=Path)
    for flag in ['title', 'language', 'cues', 'font', 'logo', 'end-landscape', 'end-portrait']:
        i.add_argument('--' + flag, required=True, type=Path if flag not in ('title', 'language') else str)
    for name in ['compile', 'render']:
        s = sub.add_parser(name); s.add_argument('plan', type=Path); s.add_argument('--output', type=Path, required=True)
    s = sub.add_parser('check'); s.add_argument('output', type=Path)
    a = p.parse_args()
    if a.command == 'init':
        result = init_plan(a)
    elif a.command == 'compile':
        if a.output.exists():
            raise FileExistsError('Preserve prior compilation')
        compiled = compile_plan(a.plan); write(a.output, compiled)
        result = {'status': compiled['status'], 'output': str(a.output),
                  'scene_count': len(compiled['scenes']), 'body_frames': compiled['body_frames'],
                  'duration_seconds': compiled['duration_seconds'],
                  'draft_timing_state': compiled['draft_timing_state'],
                  'semantic_fidelity': compiled['semantic_fidelity']}
    elif a.command == 'render':
        result = render(a.plan, a.output)
    else:
        result = check(a.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
