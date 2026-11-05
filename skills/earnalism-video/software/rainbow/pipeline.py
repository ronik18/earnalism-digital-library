"""Build one isolated, disabled-by-default stock-B narration notebook/job.

No model execution, connection, spending or approval is performed by this builder.
"""
from pathlib import Path
import base64
import hashlib
import json
import sys

SOFTWARE = Path(__file__).resolve().parents[1]
PROJECT = SOFTWARE.parent
RUNTIME_ROOT = '/content/earnalism-rainbow-v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(folder):
    folder = Path(folder).resolve()
    units = json.loads((folder / 'units.json').read_text())
    if len(units) != 4 or len({u['id'] for u in units}) != 4:
        raise ValueError('Exactly four connected complete-thought generation groups expected')
    for unit in units:
        if not unit['text'].strip() or len(unit['text'].split()) > 65 or len(unit['text']) > 520:
            raise ValueError('Preserve original worker chunk limits')
    baseline_path = PROJECT / 'output/episodes/03-refraction/production-v1/baseline-job.json'
    baseline = json.loads(baseline_path.read_text())
    if sha(baseline_path) != '2ba56e871bfecca948d331a9e0e712155b376ef745b65448db359ee755e1a215' or sha(SOFTWARE / 'vendor/qwen_worker.py') != '55500c69d0529ded866c744d5242d1c9320625bece8eb56958b8086948e2beeb':
        raise ValueError('Accepted B baseline or original worker changed')
    if any(not u['text'].rstrip().endswith(('.', '!', '?')) for u in units):
        raise ValueError('Generation groups must finish complete thoughts')
    files = {name: (SOFTWARE / 'vendor' / name).read_text() for name in (
        'pipeline_core.py', 'owner_audio_policy.py', 'narration_layout.py',
        'notebook_runtime.py', 'qwen_worker.py')}
    files['asr_cuda_env.py'] = (SOFTWARE / 'asr_cuda_env.py').read_text()
    # Reviewed adapter: only isolated run/root/export names change. The original
    # worker, supported voice controls, bounded retries and validation stay intact.
    episode = (SOFTWARE / 'refraction/colab_episode.py').read_text()
    episode = episode.replace('earnalism-refraction-v1', 'earnalism-rainbow-v1')
    episode = episode.replace("'refraction-v1'", "'rainbow-v1'")
    episode = episode.replace('refraction-speech.zip', 'rainbow-speech.zip')
    episode = episode.replace('refraction-aligned.zip', 'rainbow-aligned.zip')
    episode = episode.replace('refraction-partial.zip', 'rainbow-partial.zip')
    files['episode.py'] = episode
    payload = {'software': files, 'units': units, 'baseline': baseline}
    raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode()
    encoded = base64.b64encode(raw).decode()
    payload_sha = hashlib.sha256(raw).hexdigest()
    cell = f'''# Private episode 07. Safe Run All does not synthesize or authorize spending.
RUN_RAINBOW = False
EXISTING_COMPUTE_ALLOWED = False
FREE_RUNTIME_CONFIRMED = False
if not RUN_RAINBOW:
 print('RAINBOW_DISABLED: connect/run only within the current owner-authorized allowance.')
else:
 if not (EXISTING_COMPUTE_ALLOWED or FREE_RUNTIME_CONFIRMED):
  raise RuntimeError('No compute authorization: leave disconnected until confirmed.')
 import pathlib,json,threading,subprocess,sys,time,hashlib,base64,os
 from google.colab import runtime
 ROOT=pathlib.Path({RUNTIME_ROOT!r});ROOT.mkdir(parents=True,exist_ok=True)
 raw=base64.b64decode({encoded!r})
 assert hashlib.sha256(raw).hexdigest()=={payload_sha!r}
 package=json.loads(raw)
 soft=ROOT/'software';soft.mkdir(exist_ok=True)
 for name,text in package['software'].items():
  p=soft/name
  if p.exists() and p.read_text()!=text:raise RuntimeError('Preserve existing software/attempts: '+name)
  if not p.exists():p.write_text(text)
 for name,value in [('units.json',package['units']),('baseline-job.json',package['baseline'])]:
  p=ROOT/name
  if p.exists() and json.loads(p.read_text())!=value:raise RuntimeError('Preserve existing job/attempts: '+name)
  if not p.exists():p.write_text(json.dumps(value,indent=2))
 pidfile=ROOT/'process.json'
 if pidfile.exists():
  old=json.loads(pidfile.read_text())
  try:os.kill(old['pid'],0)
  except ProcessLookupError:pass
  else:raise RuntimeError('Existing process still present; inspect status instead of duplicating it.')
 if 'rainbow_shutdown_guard' not in globals():
  rainbow_shutdown_guard=threading.Timer(1500,runtime.unassign)
  rainbow_shutdown_guard.daemon=True;rainbow_shutdown_guard.start()
 log=open(ROOT/'console.log','a')
 process=subprocess.Popen([sys.executable,str(soft/'episode.py')],stdout=log,stderr=subprocess.STDOUT)
 pidfile.write_text(json.dumps({{'pid':process.pid,'started':time.time(),'payload_sha256':{payload_sha!r},'guard_seconds':1500}}))
 print('RAINBOW_STARTED',process.pid,'25-minute shutdown guard; no purchases; private only')
'''
    status = f'''from pathlib import Path
import json
ROOT=Path({RUNTIME_ROOT!r})
print('RAINBOW_STATUS', (ROOT/'status.json').read_text() if (ROOT/'status.json').exists() else 'not started')
print('EXPORTS',[(p.name,p.stat().st_size) for p in ROOT.glob('*.zip')])
if (ROOT/'console.log').exists():print((ROOT/'console.log').read_text()[-1800:])
'''
    download = f'''from pathlib import Path
from google.colab import files
ROOT=Path({RUNTIME_ROOT!r})
archive=ROOT/'rainbow-aligned.zip'
if not archive.exists():raise RuntimeError('Aligned export not complete; inspect status. Preserve speech/partial exports without regenerating.')
files.download(str(archive))
'''
    notebook = {'nbformat': 4, 'nbformat_minor': 5,
        'metadata': {'kernelspec': {'name': 'python3', 'display_name': 'Python 3'},
                     'language_info': {'name': 'python'}, 'accelerator': 'GPU'},
        'cells': [
            {'cell_type': 'markdown', 'metadata': {}, 'source': [
                '# Earnalism — Everyday Science 07: Rainbow\n',
                'Private original stock-Ryan B narration. Separate runtime, files and logs.\n',
                'Default controls disable synthesis and authorize no metered use. Do not Run All.\n',
                'Original audiobook notebook remains unchanged. No publication, purchases or new speech provider.\n']},
            *[{'cell_type': 'code', 'metadata': {}, 'execution_count': None,
               'outputs': [], 'source': source.splitlines(True)} for source in (cell, status, download)]]}
    outputs = {'colab-launch.py': cell, 'colab-status.py': status,
               'Earnalism_Everyday_Science_07_Narration.ipynb': json.dumps(notebook, indent=2),
               'colab-payload.json': json.dumps({'payload_sha256': payload_sha,
                   'baseline_sha256': sha(baseline_path),
                   'worker_sha256': sha(SOFTWARE / 'vendor/qwen_worker.py'),
                   'units_sha256': sha(folder / 'units.json'),
                   'runtime_root': RUNTIME_ROOT, 'disabled_by_default': True,
                   'metered_authorization_default': False, 'guard_seconds': 1500}, indent=2)}
    for name, text in outputs.items():
        path = folder / name
        if path.exists() and path.read_text() != text:
            raise FileExistsError('Refusing to replace prepared software: ' + str(path))
        if not path.exists():
            path.write_text(text)
    print('Prepared disabled private notebook; payload SHA256', payload_sha)





# Topic-specific arrangement and strict integration; reuse the existing acoustic
# sample/rights/envelope/static-mastering engine rather than copying it.
from .assemble import KINDS,MARKS,common
from ..sky_colour.finish import (RATE,FPS,IDENT_ROOT,IDENT_MANIFEST_SHA256,
    render_score,passage_evidence,validate_ident,append_ident_command,
    verify_ident_tail,stream_audio_hash,run)
from ..sky_colour.finish import SCORE_FILES as SHARED_SCORE_FILES
import math,re,subprocess
BASE=SOFTWARE
load,require,write_new=common.load,common.require,common.write_new
SCORE_FILES=tuple(n.replace('.sky-finish-lock.json','.rainbow-finish-lock.json') for n in SHARED_SCORE_FILES)
MIX_FILTER='[0:a]aformat=channel_layouts=stereo[v];[v][1:a]amix=inputs=2:normalize=0[a]'

def validate_timeline(timeline):
    seconds=timeline.get('duration');require(type(seconds) in (int,float) and math.isfinite(seconds) and seconds>0,'Invalid actual narration duration')
    scenes=timeline.get('scenes',[]);require(tuple(s.get('scene') for s in scenes)==KINDS,'Expected seven rainbow scenes in order')
    previous=0.
    for scene in scenes:
        start,end=scene.get('start'),scene.get('end');require(all(type(v) in (int,float) and math.isfinite(v) for v in (start,end)) and abs(start-previous)<.001 and end>start,'Noncontiguous actual scene timings')
        marks=scene.get('marks',{});require(set(MARKS[scene['scene']])<=set(marks),'Missing actual rainbow word anchor')
        require(all(type(v) in (int,float) and math.isfinite(v) and 0<=v<end-start for v in marks.values()),'Invalid actual relative word anchor')
        ordered=MARKS[scene['scene']];require(all(marks[a]<marks[b] for a,b in zip(ordered,ordered[1:])),'Actual spoken anchors out of order')
        previous=end
    require(abs(previous-seconds)<.001,'Timeline does not end at actual body audio duration')
    return seconds,scenes

def mark(scene,name):return scene['start']+scene['marks'][name]

def phrase_plan(timeline):
    seconds,scenes=validate_timeline(timeline)
    q,conditions,droplet,cone,movement,circle,callback=scenes
    rests=[
      {'reason':'opening challenge and immediate observer-relative payoff','start':0.,'end':q['end']},
      {'reason':'observer moves: attend to the changed droplets','start':movement['start'],'end':min(movement['end'],mark(movement,'different')+.45)},
      {'reason':'final relationship callback into the approved ident','start':callback['start'],'end':seconds}]
    intervals=[(r['start'],r['end']) for r in rests];events=[]
    def add(at,notes,instrument,velocity,duration,phrase):
        for i,note in enumerate(notes):
            t=at+i*.19
            if 0<=t<seconds-.7 and not any(a<=t<=b for a,b in intervals):
                events.append({'time':t,'midi':note,'instrument':instrument,'velocity':velocity*(1-i*.06),'duration':duration,'phrase':phrase,'pan':-.10 if instrument=='piano' else .10})
    # Original F/C/G/A open-sixth motif. No outside melody or note-count
    # surrogate for physical dispersion; these timings express thought groups.
    for scene,anchor in ((conditions,'behind'),(droplet,'enter'),(cone,'axis'),(circle,'circle')):
        add(mark(scene,anchor)+.65,[53,60,67],'piano',.25,5.4,'F open ninth: light, drops and observer')
    for scene,anchor in ((droplet,'leave'),(cone,'many'),(movement,'different'),(circle,'below')):
        for dt,note in zip((.75,2.9,5.1),(65,72,69)):
            if mark(scene,anchor)+dt<scene['end']-.6:
                add(mark(scene,anchor)+dt,[note],'harp',.23,3.6,'F C A: a viewpoint-relative answer')
    return {'title':'A Bow That Moves With You','version':'rainbow-original-v1','duration':seconds,'events':sorted(events,key=lambda e:e['time']),'rests':rests,'quiet_intervals':intervals,'fade_out_seconds':3.2,'fade_in_seconds':4.5,'composition':'Original restrained F C G A acoustic motif; no external composition','timing_source':'Actual WAV lengths and actual-ASR semantic word anchors, not generation-group boundaries','arrangement_source_sha256':sha(__file__),'listening':'PENDING','resemblance_review':'PENDING','publication_approved':False}

def validate_inputs(root):
    root=Path(root);assembly=load(root/'assembly-manifest.json');binding=load(root/'voice-binding.json')
    require(assembly.get('state')=='ASSEMBLED_PRIVATE_REQUIRES_REVIEW','No qualified new assembly')
    for name in ('timeline.json','narration.wav','voice-binding.json','asr-review.json','caption-quality.json'):
        require(assembly.get('output_files',{}).get(name)==sha(root/name),'Stale assembly output: '+name)
    source=Path(assembly['source_root']);require(all(sha(source/n)==h for n,h in assembly['input_files'].items()),'Original new narration inputs changed')
    require(binding.get('narration_sha256')==sha(root/'narration.wav') and binding.get('no_tempo_or_pitch_change') is True,'Narration binding changed')
    audits=load(root/'asr-review.json');groups=load(root/'units.json')
    require(len(audits)==len(groups)==4 and {a.get('unit') for a in audits}=={g['id'] for g in groups} and all(a.get('source_validation')=='PASS' and not a.get('differences') for a in audits),'Unresolved/missing source ASR finding')
    require(not load(root/'caption-quality.json').get('issues'),'Caption readability issue remains')
    timeline=load(root/'timeline.json');seconds,_=validate_timeline(timeline);info=common.probe_wav(root/'narration.wav')
    require(info['sample_rate']==RATE and abs(info['duration']-seconds)<.02,'Audio does not match actual timeline')
    return timeline,{n:sha(root/n) for n in ('assembly-manifest.json','timeline.json','voice-binding.json','narration.wav')}

def reserve_outputs(root,names=SCORE_FILES):
    root=Path(root);require(not any((root/n).exists() for n in names),'Preserve prior/partial finishing outputs; use a fresh assembled candidate')
    write_new(root/names[0],{'state':'EXCLUSIVE_PRIVATE_RAINBOW_FINISH','publication_approved':False})

def finish(root):
    root = Path(root).resolve()
    timeline, inputs = validate_inputs(root)
    ident_manifest = validate_ident()
    plan = phrase_plan(timeline)
    reserve_outputs(root)
    write_new(root / "score-plan.json", plan)
    rights = render_score(root, plan)
    rights['episode_arrangement_sha256'] = sha(__file__)
    evidence = passage_evidence(root / "narration.wav", root / "score.wav", timeline, plan)
    write_new(root / "score.provenance.json", {**plan, **rights,
              "measurements": evidence, "rights_scope": "Pinned CC0 sample provenance; not a legal opinion "
              "or musical-resemblance verdict", "publication_approved": False})
    run("ffmpeg", "-v", "error", "-n", "-i", root / "narration.wav", "-i", root / "score.wav",
        "-filter_complex", MIX_FILTER, "-map", "[a]", "-ar", RATE, "-ac", "2", "-c:a",
        "pcm_f32le", root / "mix.wav")
    body_samples = math.ceil(timeline["duration"] * FPS) * (RATE // FPS)
    padded_seconds = body_samples / RATE
    ident = IDENT_ROOT / "source-sound.wav"
    tails = {}
    for name, body in (("soundtrack", "mix.wav"), ("dry-soundtrack", "narration.wav")):
        run(*append_ident_command(root / body, ident, root / f"{name}.wav", padded_seconds))
        tails[name] = verify_ident_tail(root / f"{name}.wav", ident, body_samples)
        # One common encode reused verbatim by landscape and both portrait deliveries.
        run("ffmpeg", "-v", "error", "-n", "-i", root / f"{name}.wav", "-c:a", "aac",
            "-b:a", "192k", "-ar", RATE, "-ac", "2", "-movflags", "+faststart", root / f"{name}.m4a")
    import re
    meters={}
    for name in ('soundtrack.m4a','dry-soundtrack.m4a'):
        check=subprocess.run(['ffmpeg','-hide_banner','-i',str(root/name),'-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
        values=json.loads(re.findall(r'\{[^{}]*\"input_i\"[^{}]*\}',check.stderr)[-1])
        meters[name]={k:values[k] for k in ('input_i','input_tp','input_lra')}
        require(float(values['input_tp'])<=-1.5,'Encoded mix lacks headroom; preserve output and adjust only in a fresh declared candidate')
    require(all(sha(root / name) == digest for name, digest in inputs.items()),
            "Accepted assembly/narration changed during finishing")
    write_new(root / "mix-provenance.json", {
        "state": "PRIVATE_NEW_SCORE_REQUIRES_LISTENING", "inputs": inputs,
        "narration_sha256": inputs["narration.wav"], "narration_source_unchanged": True,
        "pitch_or_tempo_changed": False, "pause_edits": False, "reactive_ducking": False,
        "body_mix_filter": MIX_FILTER, "normalization_scope": "One upstream assembly normalization. Finishing uses fixed equal-power mono-to-stereo routing identically in scored and dry outputs; no output normalization, pitch, tempo, pause, EQ or compression.",
        "body_duration": timeline["duration"], "body_frame_padding": padded_seconds - timeline["duration"],
        "final_duration": padded_seconds + 3, "ident_manifest": ident_manifest,
        "ident_manifest_sha256": sha(IDENT_ROOT / "manifest.json"), "ident_tail_checks": tails,
        "score_sha256": sha(root / "score.wav"), "measurements": evidence, "encoded_loudness_measurements":meters,
        "output_files": {name: sha(root / name) for name in SCORE_FILES
                         if name != "mix-provenance.json" and (root / name).is_file()},
        "human_listening": "PENDING", "audiovisual_acceptance": "PENDING", "publication_approved": False})
    return {"output": str(root), "duration": padded_seconds + 3,
            "listening": "PENDING", "publication_approved": False}

def mux(root, fmt):
    root = Path(root).resolve()
    require(fmt in ("landscape", "shorts", "clean-shorts"), "Unknown private format")
    folder = root / fmt
    animation = folder / "animation.mp4"
    evidence = load(root / "mix-provenance.json")
    require(evidence.get("narration_sha256") == sha(root / "narration.wav"), "Narration changed")
    for name, digest in evidence["output_files"].items():
        require(sha(root / name) == digest, "Soundtrack source/evidence changed before mux")
    outputs = (".rainbow-mux-lock.json", "video.mp4", "narration-only.mp4", "technical.json")
    reserve_outputs(folder, outputs)
    data = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                                               "-of", "json", str(animation)], text=True))
    video = [s for s in data["streams"] if s["codec_type"] == "video"]
    require(len(video) == 1 and not any(s["codec_type"] == "audio" for s in data["streams"]),
            "Animation must have exactly one video stream and no competing soundtrack")
    expected_size = (1920, 1080) if fmt == "landscape" else (1080, 1920)
    require((video[0]["width"], video[0]["height"]) == expected_size, "Wrong composition dimensions")
    require(abs(float(data["format"]["duration"]) - evidence["final_duration"]) <= 1 / FPS + .005,
            "Rendered animation length differs from frame-padded narration and standard ident")
    result = {}
    for sound, name in (("soundtrack.m4a", "video.mp4"), ("dry-soundtrack.m4a", "narration-only.mp4")):
        run("ffmpeg", "-v", "error", "-n", "-i", animation, "-i", root / sound, "-map", "0:v:0",
            "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy", "-movflags", "+faststart", folder / name)
        require(stream_audio_hash(folder / name) == stream_audio_hash(root / sound),
                "Delivered AAC packets differ from the common soundtrack")
        delivery = json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json",
            str(folder / name)], text=True))
        delivered_video = next(s for s in delivery["streams"] if s["codec_type"] == "video")
        delivered_audio = next(s for s in delivery["streams"] if s["codec_type"] == "audio")
        gap = abs(float(delivered_video["duration"]) - float(delivered_audio["duration"]))
        require(gap < .1, "Delivery audio/video duration gap exceeds tolerance")
        require(abs(float(delivery["format"]["duration"]) - evidence["final_duration"]) < .1,
                "Delivery is truncated or unexpectedly padded")
        run("ffmpeg", "-v", "error", "-i", folder / name, "-f", "null", "-")
        result[name] = {"sha256": sha(folder / name), "decode": "PASS",
                        "video_duration": float(delivered_video["duration"]),
                        "audio_duration": float(delivered_audio["duration"]),
                        "audio_video_duration_gap": gap,
                        "common_audio_packet_hash": stream_audio_hash(root / sound),
                        "soundtrack_stream_copy": True}
    write_new(folder / "technical.json", {"format": fmt, "outputs": result,
              "width": expected_size[0], "height": expected_size[1], "duration": evidence["final_duration"],
              "narration_source_unchanged": True, "listening_av": "PENDING", "publication_approved": False})
    return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Isolated rainbow narration packaging, authored score and protected AAC mux; never publication')
    parser.add_argument('action',choices=('build','score','mux'));parser.add_argument('root',type=Path);parser.add_argument('format',nargs='?',choices=('landscape','shorts','clean-shorts'));args=parser.parse_args()
    if args.action=='build':build(args.root)
    elif args.action=='score':print(json.dumps(finish(args.root),indent=2))
    else:
        require(args.format is not None,'mux requires format');print(json.dumps(mux(args.root,args.format),indent=2))
