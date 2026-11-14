#!/usr/bin/env python3
"""Private original 2D character rendering from actual learned joint predictions.

Run with the existing NumPy/Pillow Python3.11 environment. There is no teacher,
pose generator, model download, cloud allocation or narration in this renderer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


JOINT_NAMES = ['pelvis', 'neck', 'head', 'Lshoulder', 'Lelbow', 'Lwrist',
               'Rshoulder', 'Relbow', 'Rwrist', 'Lhip', 'Lknee', 'Lankle',
               'Rhip', 'Rknee', 'Rankle']
ACTIONS = {'idle', 'walk', 'run', 'point', 'reach', 'react', 'sit', 'wave', 'look', 'turn', 'gesture'}
SCHEMA = 'earnalism.learned_motion_prediction.v1'
WIDTH, HEIGHT, SUPER = 960, 540, 2


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def read_json(path):
    def object_pairs(items):
        output = {}
        for key, value in items:
            if key in output:
                raise ValueError('Duplicate JSON key')
            output[key] = value
        return output
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=object_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def file_ref(ref, base, name):
    if not isinstance(ref, dict) or not isinstance(ref.get('path'), str):
        raise ValueError(f'{name} requires local path and SHA256')
    path = (base / ref['path']).resolve()
    sha = ref.get('sha256')
    if not isinstance(sha, str) or not re.fullmatch(r'[a-f0-9]{64}', sha):
        raise ValueError(f'{name} requires SHA256')
    if not path.is_file() or digest(path) != sha:
        raise ValueError(f'{name} missing or checksum mismatch')
    return {'path': str(path), 'sha256': sha}


def verify_prediction_numerics(manifest, arrays, model, training, times):
    """Replay trusted numerical inference; never execute a supplied source file."""
    try:
        from . import motion_model as maintained
    except ImportError:
        import motion_model as maintained
    qualified=maintained.validate_trained_weights(model['path'],training['path'])
    required={'inputs','raw_predicted_state','predicted_state','root_x','body'}
    if not required.issubset(arrays):
        raise ValueError('Nonfixture predictions require retained numerical inference inputs and states')
    if any(a.dtype!=np.float32 or not np.isfinite(a).all() for a in arrays.values()):
        raise ValueError('Inference arrays must be finite float32 values')
    count=len(times)
    if (arrays['inputs'].shape!=(count,len(maintained.FEATURES))
            or arrays['raw_predicted_state'].shape!=(count,len(maintained.STATE_NAMES))
            or arrays['predicted_state'].shape!=(count,len(maintained.STATE_NAMES))
            or arrays['root_x'].shape!=(count,) or arrays['body'].shape!=(8,)):
        raise ValueError('Retained numerical inference dimensions mismatch')
    case=manifest.get('case',{})
    if case.get('action')!=manifest['action']:
        raise ValueError('Prediction action is not bound to its inference case')
    body_record=manifest.get('body',{})
    expected_body=np.array([body_record.get(k,float('nan')) for k in maintained.BODY_NAMES],np.float32)
    if not np.array_equal(expected_body,arrays['body']):
        raise ValueError('Prediction body geometry differs from retained inference input')
    expected_inputs,expected_root=maintained.inputs_for_case(arrays['body'],case,np.asarray(times,np.float32))
    tolerance={'atol':2e-5,'rtol':2e-5}
    def match(actual, expected, label):
        if actual.shape!=expected.shape or not np.allclose(actual,expected,**tolerance):
            raise ValueError(f'{label} does not match trained checkpoint numerical replay')
        return float(np.max(np.abs(actual-expected)))
    inputs_error=match(arrays['inputs'],expected_inputs,'Retained inference inputs')
    root_error=match(arrays['root_x'],expected_root,'Authored root control')
    raw=maintained.numpy_predict(qualified['weights'],arrays['inputs'])
    raw_error=match(arrays['raw_predicted_state'],raw,'Raw predicted state')
    clipped=np.clip(raw,maintained.LOWER,maintained.UPPER)
    clipped_error=match(arrays['predicted_state'],clipped,'Bounded predicted state')
    joints=maintained.forward_kinematics(clipped,np.broadcast_to(arrays['body'],(count,8)),arrays['root_x'])
    joint_error=match(arrays['joints'],joints,'Predicted joint sequence')
    return {'status':'TRAINED_CHECKPOINT_AND_NUMPY_FK_REPLAY_VERIFIED',
            'trained_weights_sha256':model['sha256'],'training_report_sha256':training['sha256'],
            'steps':qualified['report']['steps'],'training_source':qualified['training_source'],
            'maximum_absolute_errors':{'inputs':inputs_error,'root':root_error,'raw_state':raw_error,
                                       'clipped_state':clipped_error,'joints':joint_error},
            'float32_tolerance':tolerance,'supplied_python_source_executed':False,
            'teacher_or_IK_fallback_used':False,'naturalness_acceptance':False}


def load_prediction(manifest_path):
    path = Path(manifest_path).resolve()
    raw = read_json(path)
    if raw.get('schema') != SCHEMA or raw.get('joint_names') != JOINT_NAMES:
        raise ValueError('Unsupported learned joint prediction contract')
    provenance = raw.get('provenance', {})
    fixture = raw.get('fixture_mode', False)
    if not isinstance(fixture, bool):
        raise ValueError('fixture_mode must be boolean')
    if (provenance.get('prediction_source') != ('synthetic_test_fixture' if fixture else 'trained_model_inference')
            or provenance.get('teacher_fallback') is not False):
        raise ValueError('Actual trained model inference required; no teacher fallback')
    if provenance.get('inverse_kinematics_fallback', False) is not False:
        raise ValueError('Inverse-kinematics fallback is not learned model inference')
    action, fps = raw.get('action'), raw.get('fps')
    if action not in ACTIONS or isinstance(fps, bool) or not isinstance(fps, int) or fps not in (24, 30):
        raise ValueError('Unsupported action or frame rate')
    prediction = file_ref(raw.get('prediction_file'), path.parent, 'prediction')
    model = file_ref(raw.get('model'), path.parent, 'trained model')
    training = file_ref(raw.get('training_report'), path.parent, 'training report')
    # Safely load arrays only. Pickled Python objects are not an inference format.
    with np.load(prediction['path'], allow_pickle=False) as archive:
        if not {'joints', 'time_seconds'}.issubset(archive.files):
            raise ValueError('Prediction archive requires actual joints and time_seconds')
        joints = np.asarray(archive['joints'], dtype=np.float32)
        times = np.asarray(archive['time_seconds'], dtype=np.float64)
        inference_arrays={name:archive[name].copy() for name in
                          ['joints','inputs','raw_predicted_state','predicted_state','root_x','body'] if name in archive.files}
    if joints.ndim != 3 or joints.shape[1:] != (15, 2) or not 3 <= len(joints) <= fps * 15:
        raise ValueError('Expected 3frames..15seconds of [T,15,2] learned joint positions')
    if times.shape != (len(joints),) or not np.isfinite(joints).all() or not np.isfinite(times).all():
        raise ValueError('Missing/nonfinite learned predictions')
    if not np.allclose(times, np.arange(len(joints)) / fps, atol=0.0001, rtol=0):
        raise ValueError('Prediction times must retain the declared actual frame clock')
    duration = raw.get('duration_seconds')
    if (isinstance(duration, bool) or not isinstance(duration, (int, float))
            or not math.isfinite(duration) or abs(duration - len(joints) / fps) > 0.0001):
        raise ValueError('Prediction duration/frame count mismatch')
    if (joints[:, :, 0].min() < -5 or joints[:, :, 0].max() > 5
            or joints[:, :, 1].min() < -.4 or joints[:, :, 1].max() > 2.7):
        raise ValueError('Predictions exceed supported metre-scale character stage')
    numeric_validation=({'status':'SYNTHETIC_RENDERER_FIXTURE_NOT_TRAINING_EVIDENCE'} if fixture else
                        verify_prediction_numerics(raw,inference_arrays,model,training,times))
    return {'manifest': raw, 'manifest_ref': {'path': str(path), 'sha256': digest(path)},
            'prediction': prediction, 'model': model, 'training_report': training,
            'joints': joints, 'times': times, 'action': action, 'fps': fps, 'duration_seconds': duration,
            'fixture_mode':fixture,'numeric_validation':numeric_validation}


def viewport(joints):
    """One static camera fitted to the complete trajectory; never pan a photo."""
    low = joints.min(axis=(0, 1))
    high = joints.max(axis=(0, 1))
    scale = min(220., (HEIGHT - 190.) / (float(high[1] - low[1]) + .3),
                (WIDTH - 260.) / (float(high[0] - low[0]) + .8))
    return {'scale': scale, 'x_offset': WIDTH / 2 - float((low[0] + high[0]) / 2) * scale,
            'y_offset': 92 + float(high[1] + .15) * scale,
            'world_bounds': [low.tolist(), high.tolist()]}


def font(size, bold=False):
    candidates = (['/System/Library/Fonts/Supplemental/Arial Bold.ttf',
                   '/System/Library/Fonts/Helvetica.ttc'] if bold else
                  ['/System/Library/Fonts/Supplemental/Arial.ttf',
                   '/System/Library/Fonts/Helvetica.ttc'])
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size * SUPER)
    return ImageFont.load_default(size=size * SUPER)


def evaluate_interaction(joints, manifest):
    """Qualify only a predeclared fixed seat, never retrofit a prop to a pose."""
    target = manifest.get('interaction_target')
    if target is None:
        return {'rendered':False,'reason':'NO_PREDECLARED_INTERACTION_TARGET'}
    if not isinstance(target,dict):
        raise ValueError('Interaction target must be a bound object')
    if (manifest.get('action') != 'sit' or target.get('kind') != 'seat'
            or target.get('declared_before_model_inference') is not True):
        return {'rendered':False,'reason':'NO_SUPPORTED_PREDECLARED_SEAT_CONTEXT'}
    values = [target.get(key) for key in ('x','surface_y','width')]
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):
        raise ValueError('Seat target requires finite predeclared geometry')
    x, surface, width = values
    if not -5<=x<=5 or not .15<=surface<=1.2 or not .2<=width<=1.5:
        raise ValueError('Seat target exceeds supported original stage')
    body=manifest.get('body',{})
    lengths=[body.get(key) for key in ('upper_leg','lower_leg','torso','head_length')]
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in lengths):
        return {'rendered':False,'reason':'MISSING_BOUND_BODY_GEOMETRY'}
    height=sum(lengths)
    late=np.asarray(joints)[max(0,int(len(joints)*.8)):]
    hips=(late[:,9]+late[:,12])/2
    seat_error=float(np.abs(hips[:,1]-surface).max())
    foot_error=float(np.abs(late[:,[11,14],1]).max())
    horizontal_error=float(np.abs(late[:,[9,12],0]-x).max())
    angles=[]
    for hip,knee,ankle in ((9,10,11),(12,13,14)):
        u,v=late[:,hip]-late[:,knee],late[:,ankle]-late[:,knee]
        lengths_product=np.linalg.norm(u,axis=1)*np.linalg.norm(v,axis=1)
        if (lengths_product<=1e-8).any():
            return {'rendered':False,'reason':'DEGENERATE_SEATED_LIMB_GEOMETRY'}
        angles.extend(np.degrees(np.arccos(np.clip((u*v).sum(axis=1)/lengths_product,-1,1))).tolist())
    matched=(seat_error<=.04*height and foot_error<=.05*height
             and horizontal_error<=width/2 and min(angles)>=55 and max(angles)<=145)
    return {'rendered':bool(matched),'reason':('DECLARED_SEAT_MATCHES_LATE_PREDICTED_SUPPORT' if matched else
            'PREDICTED_SEAT_OR_FOOT_SUPPORT_DOES_NOT_MATCH'),
            'target':target,'body_height':height,
            'observed':{'maximum_late_hip_surface_error_m':seat_error,
                        'maximum_late_foot_ground_error_m':foot_error,
                        'maximum_late_hip_horizontal_error_m':horizontal_error,
                        'minimum_late_knee_angle_degrees':min(angles),'maximum_late_knee_angle_degrees':max(angles)},
            'criteria':{'late_fraction':.2,'hip_surface_tolerance_body_height':.04,
                        'foot_ground_tolerance_body_height':.05,'knee_angle_degrees':[55,145]},
            'pose_changed':False,'natural_contact_acceptance':False}


def background(action, stage, model_sha, *, fixture=False, interaction=None):
    image = Image.new('RGB', (WIDTH * SUPER, HEIGHT * SUPER), '#f4ead5')
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT * SUPER):
        fraction = y / (HEIGHT * SUPER)
        color = tuple(round(a + (b - a) * fraction) for a, b in zip((251, 245, 229), (231, 216, 187)))
        draw.line([(0, y), (WIDTH * SUPER, y)], fill=color)
    # An original theatrical research stage; this is not a book scene or a
    # raster photograph. Fixed decorative elements never supply character pose.
    def box(values): return tuple(round(v * SUPER) for v in values)
    draw.rounded_rectangle(box((54, 98, 226, 401)), radius=84 * SUPER, fill='#e6ddc9', outline='#d6c9ad', width=SUPER)
    draw.rounded_rectangle(box((734, 98, 906, 401)), radius=84 * SUPER, fill='#e6ddc9', outline='#d6c9ad', width=SUPER)
    for x in (102, 178, 782, 858):
        draw.line([box((x, 160)), box((x, 368))], fill='#d6c9ad', width=SUPER)
    floor = stage['y_offset']
    draw.line([box((60, floor)), box((900, floor))], fill='#c9b58f', width=2 * SUPER)
    if interaction and interaction.get('rendered'):
        # Fixed original chair from declared context, not a network-generated
        # object or a hidden IK/pose correction. Draw behind the unchanged rig.
        target=interaction['target'];scale=stage['scale']
        left=target['x']*scale+stage['x_offset']-target['width']*scale/2
        right=left+target['width']*scale
        surface=stage['y_offset']-target['surface_y']*scale
        top=surface-.45*interaction['body_height']*scale
        draw.rounded_rectangle(box((left,top,right,surface+5)),radius=8*SUPER,
                               fill='#b88f65',outline='#866a4c',width=2*SUPER)
        draw.rounded_rectangle(box((left+7,top+9,right-7,surface-9)),radius=7*SUPER,
                               fill='#d6b485',outline='#a9845e',width=SUPER)
        for px in (left+8,right-8):
            draw.line([box((px,surface)),box((px,floor))],fill='#85694d',width=7*SUPER)
        draw.rounded_rectangle(box((left-4,surface-3,right+4,surface+5)),radius=3*SUPER,
                               fill='#a27b55',outline='#785e45',width=SUPER)
    heading = 'Original rig / renderer fixture' if fixture else 'Motion, learned in-house'
    draw.text(box((52, 27)), heading, font=font(29, True), fill='#19383d')
    draw.rounded_rectangle(box((725, 29, 908, 66)), radius=18 * SUPER, fill='#244f56')
    draw.text(box((746, 38)), action.upper(), font=font(16, True), fill='#fff7e6')
    label = ('RENDERER FIXTURE ONLY  /  No model-training evidence' if fixture else
             'PRIVATE RESEARCH  /  Original 2D rig  /  Synthetic-trained model output')
    draw.text(box((52, HEIGHT - 50)), label,
              font=font(13), fill='#56675f')
    draw.text(box((52, HEIGHT - 29)), f'Model {model_sha[:12]}  |  No narration or book master changed',
              font=font(11), fill='#6a756a')
    return image


def render_frame(joints, stage, base, *, phase_label=None):
    """Draw only supplied predicted joints; never generate a substitute pose."""
    joints = np.asarray(joints)
    if joints.shape != (15, 2) or not np.isfinite(joints).all():
        raise ValueError('A complete finite learned pose is required')
    image = base.copy()
    draw = ImageDraw.Draw(image)
    k = stage['scale'] / 190
    points = {name: ((float(point[0]) * stage['scale'] + stage['x_offset']) * SUPER,
                     (stage['y_offset'] - float(point[1]) * stage['scale']) * SUPER)
              for name, point in zip(JOINT_NAMES, joints)}
    def radius(value): return max(1, round(value * k * SUPER))
    def ellipse(point, rx, ry, fill, outline=None, width=1):
        x, y = point
        draw.ellipse((x - radius(rx), y - radius(ry), x + radius(rx), y + radius(ry)),
                     fill=fill, outline=outline, width=radius(width))
    def bone(names, outer, inner, thickness):
        coords = [points[name] for name in names]
        draw.line(coords, fill=outer, width=radius(thickness + 5), joint='curve')
        draw.line(coords, fill=inner, width=radius(thickness), joint='curve')
        for point in coords:
            ellipse(point, thickness / 2, thickness / 2, inner)
    pelvis = points['pelvis']
    shadow_y = stage['y_offset'] * SUPER + radius(7)
    draw.ellipse((pelvis[0] - radius(48), shadow_y - radius(7), pelvis[0] + radius(48), shadow_y + radius(7)), fill='#c9bea6')
    # Back limbs, tailored trousers, and softly rounded shoes.
    for side, color in [('R', '#425b6d'), ('L', '#344e63')]:
        bone([side + 'hip', side + 'knee', side + 'ankle'], '#233841', color, 20)
        ankle = points[side + 'ankle']
        ellipse((ankle[0] + radius(7), ankle[1] + radius(3)), 20, 8, '#2c3539', '#202d32', 1)
        draw.line([(ankle[0] - radius(9), ankle[1] + radius(9)),
                   (ankle[0] + radius(24), ankle[1] + radius(9))], fill='#b68c53', width=radius(3))
    bone(['Rshoulder', 'Relbow', 'Rwrist'], '#193c44', '#38717a', 17)
    # Torso uses only the predicted shoulders/hips, preserving every pose.
    shoulder_left, shoulder_right = points['Lshoulder'], points['Rshoulder']
    hip_left, hip_right = points['Lhip'], points['Rhip']
    draw.polygon([shoulder_left, shoulder_right, hip_right, hip_left], fill='#397b82', outline='#1c4851', width=radius(2))
    neck = points['neck']
    ellipse(neck, 10, 14, '#d79c75')
    chest = ((shoulder_left[0] + shoulder_right[0]) / 2,
             (shoulder_left[1] + shoulder_right[1]) / 2 + radius(16))
    draw.polygon([shoulder_left, (neck[0], neck[1] + radius(9)), chest], fill='#f5eddb')
    draw.polygon([shoulder_right, (neck[0], neck[1] + radius(9)), chest], fill='#e7dbc5')
    draw.polygon([(neck[0] - radius(7), neck[1] + radius(10)),
                  (neck[0] + radius(6), neck[1] + radius(10)),
                  (chest[0] + radius(14), chest[1] + radius(33)),
                  (chest[0] + radius(2), chest[1] + radius(35))], fill='#944c50')
    for fraction in (.35, .57, .77):
        button = (chest[0] * (1-fraction) + pelvis[0] * fraction,
                  chest[1] * (1-fraction) + pelvis[1] * fraction)
        ellipse(button, 2, 2, '#edcf83')
    bone(['Lshoulder', 'Lelbow', 'Lwrist'], '#193c44', '#40848a', 17)
    for side in ('R', 'L'):
        hand = points[side + 'wrist']
        ellipse(hand, 9, 11, '#dfa77e', '#975f49', 1)
        ellipse((hand[0] - radius(6), hand[1] + radius(3)), 4, 5, '#e5b38d')
    # The neutral illustrated head is a fixed rig part attached to the actual
    # predicted head joint, not a separately generated or procedural animation.
    head = points['head']
    ellipse((head[0], head[1] - radius(1)), 24, 29, '#263c41')
    ellipse((head[0], head[1] + radius(3)), 21, 25, '#e4ad83', '#a56d52', 1)
    draw.pieslice((head[0]-radius(23), head[1]-radius(29), head[0]+radius(24), head[1]+radius(12)),
                  180, 358, fill='#293b3d')
    draw.polygon([(head[0]-radius(20),head[1]-radius(10)),
                  (head[0]-radius(7),head[1]-radius(23)),
                  (head[0]+radius(20),head[1]-radius(12)),
                  (head[0]+radius(3),head[1]-radius(9))], fill='#293b3d')
    for x in (-7, 7):
        ellipse((head[0]+radius(x),head[1]+radius(2)), 2, 2.8, '#263b40')
    draw.arc((head[0]-radius(7),head[1]+radius(6),head[0]+radius(7),head[1]+radius(15)),
             15, 165, fill='#925a45', width=radius(1.5))
    draw.line([(head[0]+radius(1),head[1]+radius(4)),(head[0]+radius(3),head[1]+radius(8))],
              fill='#bd8060',width=radius(1))
    if phase_label:
        draw.text((WIDTH * SUPER / 2, 78 * SUPER), phase_label, font=font(13, True),
                  fill='#607166', anchor='mm')
    return image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)


def _run(args):
    process = subprocess.run([str(arg) for arg in args], capture_output=True, text=True,
                             timeout=300, check=False)
    if process.returncode:
        raise ValueError('Local media command failed: ' + process.stderr[-1800:])
    return process.stdout


def render(manifest_path, output_dir):
    prediction = load_prediction(manifest_path)
    output_dir = Path(output_dir).resolve()
    if output_dir.exists():
        raise ValueError('Output exists; preserve research candidates')
    if any((parent / '.git').exists() for parent in [output_dir, *output_dir.parents]):
        raise ValueError('Private model research output must stay outside git')
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise ValueError('Existing local FFmpeg and FFprobe are required')
    output_dir.mkdir(parents=True, exist_ok=False)
    joints = prediction['joints']
    stage = viewport(joints)
    interaction=evaluate_interaction(joints,prediction['manifest'])
    base = background(prediction['action'], stage, prediction['model']['sha256'],
                      fixture=prediction['fixture_mode'],interaction=interaction)
    stills = []
    try:
        with tempfile.TemporaryDirectory(prefix='.frames-', dir=output_dir) as temporary:
            folder = Path(temporary)
            for index, pose in enumerate(joints):
                phase = ('START', 'ACTION', 'RESULT')[min(2, int(index / len(joints) * 3))]
                image = render_frame(pose, stage, base, phase_label=phase)
                image.save(folder / f'{index:05}.png')
                if index in {0, len(joints)//2, len(joints)-1}:
                    still_path = output_dir / f'frame-{index:05}.png'
                    image.save(still_path)
                    stills.append({'frame': index, 'path': str(still_path), 'sha256': digest(still_path)})
            final = output_dir / f'{prediction["action"]}-learned-rig.mp4'
            _run(['ffmpeg', '-v', 'error', '-nostdin', '-n', '-framerate', prediction['fps'],
                  '-i', folder / '%05d.png', '-frames:v', len(joints), '-an', '-c:v', 'libx264',
                  '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', final])
        probe = json.loads(_run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',final]))
        videos = [stream for stream in probe['streams'] if stream['codec_type'] == 'video']
        if len(videos) != 1 or any(stream['codec_type']=='audio' for stream in probe['streams']):
            raise ValueError('Research demo requires exactly one silent video stream')
        video = videos[0]
        if (video['codec_name'] != 'h264' or (video['width'],video['height']) != (WIDTH,HEIGHT)
                or int(video['nb_frames']) != len(joints)
                or abs(float(probe['format']['duration']) - prediction['duration_seconds']) > .05):
            raise ValueError('Encoded research movie does not match the actual prediction frames')
        _run(['ffmpeg','-v','error','-xerror','-i',final,'-map','0:v:0','-f','null','-'])
        rechecked = load_prediction(manifest_path)
        if rechecked['manifest_ref'] != prediction['manifest_ref']:
            raise ValueError('Prediction changed during render')
        report = {'schema':'earnalism.learned_rig_research_render.v1',
                  'state':('PRIVATE_FIXTURE_RENDERED_NO_TRAINING_EVIDENCE' if prediction['fixture_mode']
                           else 'PRIVATE_MODEL_PREDICTION_RENDERED_NOT_PRODUCTION_ACCEPTED'),
                  'fixture_mode':prediction['fixture_mode'],
                  'manifest':prediction['manifest_ref'],'prediction':prediction['prediction'],
                  'model':prediction['model'],'training_report':prediction['training_report'],
                  'prediction_numeric_validation':prediction['numeric_validation'],
                  'action':prediction['action'],'fps':prediction['fps'],'frames':len(joints),
                  'output':{'path':str(final),'sha256':digest(final),'duration_seconds':float(probe['format']['duration']),
                            'width':WIDTH,'height':HEIGHT,'codec':'h264','decode':'PASS','audio_present':False},
                  'stills':stills,'static_viewport':stage,
                  'interaction_prop':interaction,
                  'inference_provenance':prediction['manifest']['provenance'],
                  'observed_prediction_motion':{
                      'joint_range_metres':{name:float(np.linalg.norm(np.ptp(joints[:,index],axis=0)))
                                            for index,name in enumerate(JOINT_NAMES)},
                      'body_relative_joint_range_metres':{
                          name:float(np.linalg.norm(np.ptp(joints[:,index]-joints[:,0],axis=0)))
                          for index,name in enumerate(JOINT_NAMES)},
                      'root_trajectory_range_metres':float(np.linalg.norm(np.ptp(joints[:,0],axis=0))),
                      'moving_joint_count_at_5mm':int(np.count_nonzero(np.linalg.norm(np.ptp(joints,axis=0),axis=1)>.005)),
                      'maximum_joint_step_metres':float(np.linalg.norm(np.diff(joints,axis=0),axis=2).max()),
                      'semantic_naturalness_inferred':False},
                  'pose_source':'Only supplied inference joint sequence: learned pose state, fixed FK and any explicitly authored root control; rigid-part drawing and static viewport only.',
                  'teacher_fallback_used':False,'original_media_changed':False,
                  'motion_quality_acceptance':'UNASSESSED','release_approved':False,'publication_approved':False,
                  'limits':['Synthetic-trained 2D rig research, not a video foundation model or natural human acting acceptance.',
                            'Fixed illustrated face/clothes/hands/feet are rig geometry, not additional learned visual generation.',
                            'START/ACTION/RESULT label thirds identify review sections; they do not certify action completion.',
                            'Any authored root control or FK implementation belongs to the bound inference source; renderer adds no pose or root trajectory.']}
        with (output_dir/'render-report.json').open('x',encoding='utf-8') as target:
            json.dump(report,target,indent=2);target.write('\n')
        return report
    except Exception as error:
        with (output_dir/'FAILED.json').open('x') as target:
            json.dump({'state':'FAILED_PRIVATE_RESEARCH_RENDER','error':str(error),'release_approved':False},target,indent=2)
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prediction',required=True,type=Path)
    parser.add_argument('--output-dir',required=True,type=Path)
    args=parser.parse_args()
    try:
        print(json.dumps(render(args.prediction,args.output_dir),indent=2))
    except (ValueError,OSError,subprocess.TimeoutExpired) as error:
        parser.exit(2,f'learned rig render: {error}\n')


if __name__=='__main__':
    main()
