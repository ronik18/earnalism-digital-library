"""Attended Colab runtime setup; model workers are isolated subprocesses."""
from owner_audio_policy import AudioGenerationExcluded, assert_audio_allowed, audio_exclusion_reason, audio_identity
import json,os,re,subprocess,sys,time
from pathlib import Path
from pipeline_core import *

QWEN_CODE='022e286b98fbec7e1e916cb940cdf532cd9f488e'
QWEN_WEIGHTS='0c0e3051f131929182e2c023b9537f8b1c68adfe'

def command(args,**kwargs):
    return subprocess.run([str(x) for x in args],check=True,**kwargs)

def prepare_source_repository(output_root,ref='main'):
    # Repository source is immutable per run. Never reset a user working checkout.
    require(re.fullmatch(r'[A-Za-z0-9._/-]+',ref),'Invalid source ref')
    remote='https://github.com/ronik18/earnalism-digital-library.git'
    if re.fullmatch(r'[a-f0-9]{40}',ref):sha=ref
    else:
        value=subprocess.check_output(['git','ls-remote',remote,'refs/heads/'+ref],text=True).strip()
        require(len(value.splitlines())==1 and value,'Cannot resolve source ref');sha=value.split()[0]
    root=Path('/content/earnalism-source')/sha
    if not (root/'.git').exists():
        root.parent.mkdir(parents=True,exist_ok=True)
        command(['git','init',root])
        command(['git','-C',root,'remote','add','origin',remote])
        command(['git','-C',root,'fetch','--depth','1','--filter=blob:none','origin',sha])
        command(['git','-C',root,'sparse-checkout','init','--cone'])
        command(['git','-C',root,'sparse-checkout','set','data/controlled_publications','backend/data/controlled_publications','docs/product'])
        command(['git','-C',root,'checkout','--detach',sha])
    require(subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()==sha,'Repository snapshot changed')
    require(not subprocess.check_output(['git','-C',str(root),'status','--porcelain'],text=True).strip(),'Source snapshot is dirty; preserve it and use a fresh snapshot')
    atomic_json(Path(output_root)/'source_repository.json',{'remote':remote,'requested_ref':ref,'resolved_commit':sha,'read_at':now(),'not_a_deployment_claim':True})
    return root

# Qwen and ASR use managed Python 3.12 independently of the Colab kernel.
import shutil

BASE_VENV_DIR = Path('/content/earnalism-venvs')
WORKER_PYTHON = '3.12'


def _command(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)


def pip_env(name, packages):
    """Return a verified Python 3.12 interpreter and its dependency record.

    uv builds the virtual environment directly, so target Python does not need
    ensurepip or pip. Only the uv launcher may be installed into the Colab
    kernel; all model packages use the explicit worker interpreter below.
    """
    require(re.fullmatch(r'[a-z][a-z0-9_-]*', name), 'Invalid worker environment name')
    require(isinstance(packages, list) and packages and all(
        isinstance(group, list) and group and all(isinstance(p, str) and p for p in group)
        for group in packages), 'Invalid worker dependency recipe')
    root = BASE_VENV_DIR / (name + '-py' + WORKER_PYTHON.replace('.', ''))
    python = root / 'bin/python'
    stamp = root / 'earnalism-install.json'
    recipe = object_hash({'packages': packages, 'python_request': WORKER_PYTHON,
                          'installer': 'uv-pip', 'schema': 2})
    # Prevent active notebook/ACE environments from changing interpreter choice.
    env = os.environ.copy()
    for key in ('VIRTUAL_ENV', 'CONDA_PREFIX', 'UV_PROJECT_ENVIRONMENT', 'PYTHONHOME', 'PYTHONPATH'):
        env.pop(key, None)
    uv_binary = shutil.which('uv')
    if uv_binary:
        uv = [uv_binary]
    else:
        _command([sys.executable, '-m', 'pip', 'install', 'uv'], env=env)
        uv = [sys.executable, '-m', 'uv']
    uv_version = subprocess.check_output([*uv, '--version'], text=True, env=env).strip()

    if not python.exists():
        # Preserve a broken existing environment for diagnosis, rather than
        # clearing or silently mixing an incomplete or wrong-version directory.
        require(not root.exists(), 'Incomplete worker environment at ' + str(root) +
                '; rename this environment directory and rerun setup')
        root.parent.mkdir(parents=True, exist_ok=True)
        _command([*uv, 'venv', '--python', WORKER_PYTHON, '--managed-python', str(root)], env=env)

    probe = ('import json,sys; print(json.dumps({"version":list(sys.version_info[:3]),'
             '"prefix":sys.prefix,"base_prefix":sys.base_prefix,'
             '"executable":sys.executable,"implementation":sys.implementation.name}))')
    interpreter = json.loads(subprocess.check_output(
        [str(python), '-I', '-c', probe], text=True, env=env))
    require(interpreter.get('version', [])[:2] == [3, 12],
            'Worker must use Python 3.12; found ' + str(interpreter.get('version')))
    require(interpreter.get('implementation') == 'cpython', 'Worker requires CPython')
    require(Path(interpreter.get('prefix', '')).resolve() == root.resolve() and
            interpreter.get('prefix') != interpreter.get('base_prefix'),
            'Worker interpreter is not isolated in its expected virtual environment')
    previous = read_json(stamp) if stamp.exists() else None
    if previous is None or previous.get('recipe') != recipe:
        for group in packages:
            _command([*uv, 'pip', 'install', '--python', str(python), *group], env=env)
        _command([*uv, 'pip', 'check', '--python', str(python)], env=env)
        freeze = subprocess.check_output(
            [*uv, 'pip', 'freeze', '--python', str(python)], text=True, env=env)
        atomic_json(stamp, {'schema': 2, 'recipe': recipe, 'packages': packages,
                           'python_request': WORKER_PYTHON, 'interpreter': interpreter,
                           'installer_version': uv_version, 'pip_freeze': freeze,
                           'generated_at': now()})
    else:
        # A valid-looking old stamp must not hide a damaged or altered runtime.
        _command([*uv, 'pip', 'check', '--python', str(python)], env=env)
        freeze = subprocess.check_output(
            [*uv, 'pip', 'freeze', '--python', str(python)], text=True, env=env)
        require(previous.get('interpreter') == interpreter,
                'Cached worker interpreter changed; use a fresh worker environment')
        require(previous.get('pip_freeze') == freeze,
                'Cached worker dependencies changed; use a fresh worker environment')
    return str(python), read_json(stamp)


def snapshot(python,repo,revision,output_file):
    code="from huggingface_hub import HfApi,snapshot_download;from pathlib import Path;import json,sys\nr=json.loads(sys.argv[1]);rev=r['revision'] or HfApi().model_info(r['repo']).sha\np=snapshot_download(repo_id=r['repo'],revision=rev,cache_dir='/content/earnalism-hf');Path(r['output']).write_text(json.dumps({'model_id':r['repo'],'model_revision':rev,'model_path':p}))"
    command([python,'-c',code,json.dumps({'repo':repo,'revision':revision,'output':str(output_file)})])
    return read_json(output_file)

def setup_qwen(root):
    py,env=pip_env('qwen',[['torch==2.8.0','torchaudio==2.8.0','--index-url','https://download.pytorch.org/whl/cu126'],['git+https://github.com/QwenLM/Qwen3-TTS.git@'+QWEN_CODE]])
    model=snapshot(py,QWEN_ID,QWEN_WEIGHTS,Path(root)/'qwen_snapshot.json')
    atomic_json(Path(root)/'qwen_environment.json',{'environment':env,'model':model,'code_commit':QWEN_CODE})
    provenance=Path(root)/'provenance';provenance.mkdir(parents=True,exist_ok=True)
    import urllib.request, shutil
    for name in ('README.md','LICENSE'):
        src=Path(model['model_path'])/name
        if src.exists():shutil.copy2(src,provenance/('Qwen-pinned-model-'+name.replace('/','_')))
    license_url='https://raw.githubusercontent.com/QwenLM/Qwen3-TTS/'+QWEN_CODE+'/LICENSE'
    with urllib.request.urlopen(license_url,timeout=45) as response:
        (provenance/'Qwen-code-LICENSE.txt').write_bytes(response.read())
    return py,model

def setup_asr(root):
    py,env=pip_env('asr',[['faster-whisper==1.2.1','rapidfuzz==3.14.1','huggingface-hub>=0.34,<1']])
    lock=Path(root)/'asr_snapshot.json';prior=read_json(lock) if lock.exists() else {}
    model=snapshot(py,'Systran/faster-whisper-large-v3',prior.get('model_revision'),lock)
    atomic_json(Path(root)/'asr_environment.json',{'environment':env,'model':model})
    return py,model

def run_worker(python,worker,job,job_path,timeout_seconds):
    assert_audio_allowed(job, require_identity=True)
    require(timeout_seconds>=1,'Session runtime budget exhausted')
    atomic_json(job_path,job)
    env=os.environ.copy();env['PYTHONUNBUFFERED']='1'
    command([python,worker,job_path],timeout=timeout_seconds,env=env)

def audio_bindings(ctx, paths):
    return {str(Path(p).relative_to(ctx['run'])):file_hash(p) for p in paths}

def check_generation_outputs(ctx,model,stage):
    import math
    import soundfile as sf
    import qwen_worker as qw
    job=qwen_job(ctx,model,stage)
    expected_generation={**qw.GENERATION_DEFAULTS,**job.get('generation',{})}
    expected_validation={**qw.VALIDATION_DEFAULTS,**job.get('validation',{})}
    current_worker_hash=file_hash(Path(qw.__file__))
    for s in job['segments']:
        path=Path(s['output_path']); side=Path(str(path)+'.json')
        require(path.is_file() and side.is_file(),'Generate missing segment: '+s['segment_id'])
        meta=read_json(side);settings=meta.get('settings',{});provenance=meta.get('provenance',{})
        require(meta.get('schema')==qw.SCHEMA and meta.get('status')=='GENERATED_REQUIRES_REVIEW','Unverified Qwen output metadata: '+s['segment_id'])
        require(meta.get('segment_id')==s['segment_id'],'Generated segment identity mismatch')
        require(Path(meta.get('output_path','')).resolve()==path.resolve(),'Generated output path mismatch')
        require(meta.get('wav_sha256')==file_hash(path),'Generated audio hash mismatch')
        require(isinstance(settings,dict) and meta.get('effective_key')==qw.object_hash(settings),'Generated settings hash mismatch')
        expected={'schema':qw.SCHEMA,'source_cache_key':s['cache_key'],'segment_id':s['segment_id'],
                  'text':s['text'],'instruct':s['instruct'],'speaker':s['speaker'],'language':'English',
                  'seed_base':s['seed'],'retry_seed_rule':'(seed_base+attempt_number-1) modulo 2**32',
                  'non_streaming_mode':True,'batch_size':1,'generation':expected_generation,
                  'validation':expected_validation,'attention':job.get('attention','eager'),'wav_subtype':'FLOAT'}
        for key,value in expected.items():
            require(settings.get(key)==value,'Generated settings are stale: '+s['segment_id']+' / '+key)
        require(provenance.get('model_id')==model['model_id'] and provenance.get('model_revision')==model['model_revision'],'Generated model snapshot identity mismatch')
        require(provenance.get('worker_sha256')==current_worker_hash,'Generation used a different Qwen worker revision; regenerate/review explicitly')
        hardware=provenance.get('hardware',{});capability=hardware.get('compute_capability',[])
        require(len(capability)==2 and type(capability[0]) is int and isinstance(hardware.get('native_bfloat16'),bool),'Missing GPU precision provenance')
        require(hardware.get('device')=='cuda:0','Unexpected generation device')
        native_bf16=capability[0]>=8 and hardware['native_bfloat16']
        precision=('bfloat16' if native_bf16 else 'float32') if job.get('dtype','auto')=='auto' else job['dtype']
        require(settings.get('dtype')==precision and provenance.get('dtype')==precision,'Generation precision does not match the current policy')
        require(provenance.get('attention')==expected['attention'],'Generation attention mismatch')
        snapshot=provenance.get('snapshot',{});manifest=snapshot.get('files')
        require(isinstance(manifest,list) and manifest and snapshot.get('manifest_sha256')==qw.object_hash(manifest),'Missing or inconsistent pinned model manifest')
        environment=provenance.get('environment',{})
        binding={'model_id':model['model_id'],'model_revision':model['model_revision'],
                 'snapshot_sha256':snapshot['manifest_sha256'],'python':environment.get('python'),
                 'packages':environment.get('packages'),'qwen_package_source_sha256':environment.get('qwen_package_source_sha256'),
                 'torch_cuda_version':environment.get('torch_cuda_version'),'torch_cudnn_version':environment.get('torch_cudnn_version'),
                 'hardware':hardware,'worker_sha256':current_worker_hash}
        require(settings.get('provenance_binding')==binding,'Generation provenance and effective settings disagree')
        selected_attempt=meta.get('selected_attempt');selected_seed=meta.get('selected_seed')
        require(type(selected_attempt) is int and 1<=selected_attempt<=job['max_attempts'],'Invalid selected generation attempt')
        require(selected_seed==(s['seed']+selected_attempt-1)%(2**32),'Selected retry seed mismatch')
        audio=meta.get('audio',{});info=sf.info(path)
        require(audio.get('mechanical_checks')=='PASS' and audio.get('failure_reasons')==[] and audio.get('token_cap_suspicion') is False,'Qwen mechanical checks have not passed')
        require(info.frames>0 and info.channels==1 and info.subtype=='FLOAT','Unexpected raw narration WAV format')
        require(info.frames==audio.get('samples') and info.samplerate==audio.get('sample_rate'),'Generated native audio dimensions mismatch')
        duration=audio.get('duration_seconds')
        require(type(duration) in (int,float) and math.isfinite(duration) and math.isclose(duration,info.frames/info.samplerate,rel_tol=1e-9),'Generated duration metadata mismatch')
        require(type(audio.get('codec_frames')) is int and audio['codec_frames']<expected_generation['max_new_tokens']-2,'Generated output has possible cap truncation')
        # This verifies current synthesis inputs/provenance and bytes, not linguistic fidelity.
    return job['segments']

def review_stage(ctx,model,stage):
    candidates=check_generation_outputs(ctx,model,stage)
    files=[s['output_path'] for s in candidates]
    if stage=='endurance':files=check_endurance_audio(ctx,candidates)
    expected=human_review_template(ctx,audio_bindings(ctx,files),stage)
    if stage=='audition':expected['selected_speaker']=None
    path=ctx['run']/(stage+'_review.json');review=ensure_review(path,expected)
    issues=validate_review(review,expected)
    if stage=='audition':
        if review.get('selected_speaker') not in ('Ryan','Aiden'):
            issues.append('Record the selected narrator after listening to every generated audition clip')
        elif review['selected_speaker']!=ctx['editorial']['speaker']:
            issues.append('Selected audition speaker must match editorial_plan.json speaker; update the plan and refresh its review bindings')
    require(not issues,'Complete '+str(path)+': '+'; '.join(issues))

def create_review_templates(ctx,model,stage):
    candidates=check_generation_outputs(ctx,model,stage)
    files=[s['output_path'] for s in candidates]
    if stage=='endurance':
        from audio_processing import assemble_book,master_and_encode
        assembly=assemble_book(candidates,ctx['run']/'endurance_assembly',ctx['artifact']['slug'],ctx['artifact']['source_sha256'])
        mastered=master_and_encode(assembly['master_wav'],None,ctx['run']/'endurance_delivery')
        files=[mastered['outputs']['narration']['mp3']]
        atomic_json(ctx['run']/'endurance_audio.json',{'plan_sha256':ctx['plan_hash'],'input_sha256':audio_bindings(ctx,[s['output_path'] for s in candidates]),'audio_sha256':audio_bindings(ctx,files),'duration_seconds':assembly['duration_seconds'],'note':'Planning target is approximately 20 minutes; short titles use their full text. Listen to the complete assembled sample.'})
    expected=human_review_template(ctx,audio_bindings(ctx,files),stage)
    if stage=='audition':expected['selected_speaker']=None
    path=ctx['run']/(stage+'_review.json');review=ensure_review(path,expected)
    if stage=='audition' and 'selected_speaker' not in review:
        review['selected_speaker']=None;atomic_json(path,review)
    return path,files

def check_endurance_audio(ctx,candidates):
    manifest=read_json(ctx['run']/'endurance_audio.json')
    require(manifest.get('plan_sha256')==ctx['plan_hash'] and manifest.get('input_sha256')==audio_bindings(ctx,[s['output_path'] for s in candidates]),'Endurance preview is stale; rerun endurance')
    paths=[]
    for name,sha in manifest.get('audio_sha256',{}).items():
        p=safe_relative(ctx['run'],name);require(p.is_file() and file_hash(p)==sha,'Endurance preview changed');paths.append(str(p))
    require(paths,'Missing continuous endurance preview')
    return paths

def run_asr(ctx,model,asr_python,asr_model,tools,remaining):
    assert_audio_allowed(ctx, require_identity=True)
    segments=check_generation_outputs(ctx,model,'narration')
    job={**audio_identity(ctx),**asr_model,'source_sha256':ctx['artifact']['source_sha256'],'segments':segments,'cache_dir':str(ctx['run']/'asr_segments'),'report_path':str(ctx['run']/'asr_report.json'),'device':'cpu','similarity_min':.97,'coverage_min':.98}
    run_worker(asr_python,Path(tools)/'asr_worker.py',job,ctx['run']/'asr_job.json',remaining)
    return read_json(job['report_path'])

def run_music(ctx,tools,remaining):
    assert_audio_allowed(ctx, require_identity=True)
    from ace_setup import setup_ace
    require(remaining>=1,'Session runtime budget exhausted before ACE setup')
    deadline=time.monotonic()+remaining
    run=ctx['run'];root=ctx['root'].resolve();cues=propose_cues(ctx)
    # One verified model bundle for the entire catalog, with title-isolated outputs.
    setup=setup_ace(str(root),tools_dir='/content/earnalism_tools')
    cue_hash=object_hash(cues);relative_run=run.resolve().relative_to(root)
    output=relative_run/'music_candidates'/cue_hash[:16]
    job={**audio_identity(ctx),'workspace':str(root),'book_id':ctx['artifact']['slug'],'source_path':str(relative_run/'canonical_text.txt'),'source_sha256':ctx['artifact']['source_sha256'],'cue_plan':cues,'music_generation_request':{'requested':True,'source_sha256':ctx['artifact']['source_sha256'],'cue_plan_sha256':cue_hash,'original_captions_no_artist_imitation':True,'no_reference_audio_or_melody':True},'output_dir':str(output),**setup['worker_job_fields']}
    run_worker(setup['python'],Path(tools)/'ace_worker.py',job,run/'music_job.json',max(0,deadline-time.monotonic()))
    raw_manifest=root/output/'music_manifest.json';manifest=read_json(raw_manifest)
    # Preserve the raw global-workspace manifest; normalize a title-local view for mixing.
    manifest['raw_manifest_path']=str(raw_manifest.relative_to(run))
    manifest['raw_manifest_sha256']=file_hash(raw_manifest)
    manifest['cues']=[{**c,'path':str(safe_relative(root,c['path']).relative_to(run.resolve()))} for c in manifest['cues']]
    atomic_json(run/'music_generation_report.json',manifest)
    template={'source_sha256':ctx['artifact']['source_sha256'],'cue_plan_sha256':cue_hash,'cue_audio_sha256':{c['cue_id']:c['sha256'] for c in manifest['cues']},'generation_provenance_sha256':object_hash(manifest.get('provenance',{})),'reviewer':'','reviewed_at':'','all_cues_listened':False,'context_fit_approved':False,'no_unwanted_vocals':False,'no_recognizable_borrowed_melody':False,'licenses_and_component_terms_reviewed':False,'commercial_audiobook_and_promo_use_cleared':False,'territories':[],'rights_basis_notes':'','approved_for_scored_delivery':False,'notes':''}
    p=run/'music_review.json'
    if not p.exists():atomic_json(p,template)
    elif any(read_json(p).get(k)!=template[k] for k in ('source_sha256','cue_plan_sha256','cue_audio_sha256','generation_provenance_sha256')):
        atomic_json(run/('music_review.STALE.'+str(time.time_ns())+'.json'),read_json(p));atomic_json(p,template)
    retain_environment_evidence(ctx)
    return manifest


def validate_music(ctx,manifest):
    review=read_json(ctx['run']/'music_review.json')
    require(review.get('source_sha256')==ctx['artifact']['source_sha256'] and review.get('cue_plan_sha256')==object_hash(propose_cues(ctx)),'Stale music context review')
    require(review.get('cue_audio_sha256')=={c['cue_id']:c['sha256'] for c in manifest['cues']},'Stale cue audio review')
    require(review.get('generation_provenance_sha256')==object_hash(manifest.get('provenance',{})),'Music model/runtime license review is stale')
    for key in ('all_cues_listened','context_fit_approved','no_unwanted_vocals','no_recognizable_borrowed_melody','licenses_and_component_terms_reviewed','commercial_audiobook_and_promo_use_cleared','approved_for_scored_delivery'):
        require(review.get(key) is True,'Music review required: '+key)
    require(review.get('reviewer') and review.get('reviewed_at') and review.get('territories') and review.get('rights_basis_notes'),'Music reviewer/territory/rights rationale required')
    for c in manifest['cues']:
        require(file_hash(safe_relative(ctx['run'],c['path']))==c['sha256'],'Music asset changed')
    return review

def retain_environment_evidence(ctx):
    import shutil
    dest=ctx['run']/'provenance';dest.mkdir(parents=True,exist_ok=True)
    for name in ('source_repository.json','qwen_environment.json','asr_environment.json'):
        p=ctx['root']/name
        if p.is_file():shutil.copy2(p,dest/name)
    shared=ctx['root']/'provenance'
    if shared.is_dir():
        for p in shared.iterdir():
            if p.is_file():shutil.copy2(p,dest/p.name)
    toolroot=Path(__file__).resolve().parent
    atomic_json(ctx['run']/'runtime_lock.json',{'pipeline':VERSION,'recorded_at':now(),'worker_files':{p.name:file_hash(p) for p in toolroot.glob('*.py')},'source_repository':read_json(ctx['root']/'source_repository.json') if (ctx['root']/'source_repository.json').exists() else None})


def write_timing_exports(ctx,assembly):
    import html
    run=ctx['run'];out=run/'delivery';out.mkdir(parents=True,exist_ok=True)
    slug=ctx['artifact']['slug']
    source_segments={s['segment_id']:s for s in ctx['segments']}
    units=[]
    for unit in assembly['units']:
        source=source_segments[unit['segment_id']]
        units.append({**unit,'source_start':source['source_start'],
                      'source_end':source['source_end'],
                      'paragraph_basis':source.get('paragraph_basis','CANONICAL_DISPLAY_PARAGRAPH')})
    chapters={c['id']:c for c in ctx['artifact']['chapters']}
    payload={'source_sha256':ctx['artifact']['source_sha256'],'master_sha256':assembly['master_sha256'],'alignment_granularity':'synthesis_chunk_not_word','encoded_playback_verified':False,'units':units,'chapters':[{**c,'title':chapters[c['chapter_id']]['title']} for c in assembly['chapters']],'paragraphs':assembly['paragraphs']}
    payload['narration_layout']=ctx.get('narration_layout')
    payload['reader_mapping']='Map by chapter ID and canonical character offsets; narration paragraph ordinals may differ from reader display blocks.'
    timing=out/(slug+'_timestamps.json');atomic_json(timing,payload)
    cp=out/(slug+'_chapters.json');atomic_json(cp,{'alignment_source':'assembled_pcm_samples','encoded_playback_verified':False,'chapters':payload['chapters']})
    def vtt_time(seconds):
        ms=round(seconds*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
        return f'{h:02d}:{m:02d}:{s:02d}.{ms:03d}'
    blocks=['WEBVTT','NOTE Synthesis-chunk cues, not word alignment; verify encoded playback before importer use.']
    for u in units:
        text=html.escape(u['text']).replace('-->','—')
        blocks.append(f"{u['segment_id']}\n{vtt_time(u['start_seconds'])} --> {vtt_time(u['end_seconds'])}\n{text}")
    vtt=out/(slug+'_highlight.vtt');vtt.write_text('\n\n'.join(blocks)+'\n',encoding='utf-8')
    return [str(timing),str(cp),str(vtt)]


def build_delivery(ctx,model,include_music=False,require_music_review=False):
    assert_audio_allowed(ctx, require_identity=True)
    from audio_processing import assemble_book,mix_atmosphere,master_and_encode
    run=ctx['run'];segments=check_generation_outputs(ctx,model,'narration')
    assembly=assemble_book(segments,run/'assembly',ctx['artifact']['slug'],ctx['artifact']['source_sha256'])
    score=None;music_manifest=None;extra=[]
    if include_music:
        music_manifest=read_json(run/'music_generation_report.json')
        if require_music_review:validate_music(ctx,music_manifest)
        cues=propose_cues(ctx)
        require(music_manifest.get('source_sha256')==ctx['artifact']['source_sha256'] and music_manifest.get('cue_plan_sha256')==object_hash(cues),'Stale music generation')
        units={s['segment_id']:s for s in assembly['units']}; placements=[]
        generated={c['cue_id']:c for c in music_manifest['cues']}
        require(set(generated)=={c['cue_id'] for c in cues},'Missing or extra generated cues')
        cap=min(20,assembly['duration_seconds']*.20/max(1,len(cues)))
        for cue in cues:
            asset=generated[cue['cue_id']];path=safe_relative(run,asset['path']);require(file_hash(path)==asset['sha256'],'Changed cue asset')
            require(cue['start_segment_id'] in units and cue['end_segment_id'] in units,'Cue points outside the current narration')
            first,last=units[cue['start_segment_id']],units[cue['end_segment_id']]
            require(first['chapter_id']==cue['chapter_id']==last['chapter_id'],'Cue crosses or mismatches chapters')
            start=first['start_sample'];end=min(last['end_sample'],start+int(cap*assembly['sample_rate']))
            if end-start>=int(4*assembly['sample_rate']):placements.append({'cue_path':str(path),'start_sample':start,'end_sample':end,'music_below_narration_db':22})
        require(placements,'Title too short for these sparse cues; use narration-only or edit the cue plan')
        mixed=mix_atmosphere(assembly['master_wav'],assembly,placements,run/'mix',duck_db=3,max_coverage=.25)
        score=mixed['scored_wav'];mixpath=run/'mix'/'mix_review_evidence.json';atomic_json(mixpath,mixed);extra.append(str(mixpath))
    mastering=master_and_encode(assembly['master_wav'],score,run/'delivery')
    audios=[v['mp3'] for v in mastering['outputs'].values()]
    evidence=[assembly['timeline_path'],mastering['mastering_manifest_path'],*write_timing_exports(ctx,assembly),*extra]
    delivery={'audio_files':audios,'evidence_files':evidence,'evidence_sha256':audio_bindings(ctx,evidence),'assembly':assembly,'mastering':mastering,'model_revision':model['model_revision'],'source_sha256':ctx['artifact']['source_sha256'],'plan_sha256':ctx['plan_hash'],'input_audio_sha256':audio_bindings(ctx,[s['output_path'] for s in segments]),'atmosphere_included':bool(score),'private_review_only':True,'release_ready':False}
    delivery['narration_layout_sha256']=object_hash(ctx['narration_layout']) if ctx.get('narration_layout') else None
    atomic_json(run/'full_generation_manifest.json',delivery)
    expected=human_review_template(ctx,audio_bindings(ctx,audios),'full_title');expected['asr_flag_resolutions']={};expected['encoded_seeks_and_chapter_starts_checked']=False
    ensure_review(run/'full_listening_qa.json',expected)
    rights_template={'source_sha256':ctx['artifact']['source_sha256'],'plan_sha256':ctx['plan_hash'],'audio_sha256':audio_bindings(ctx,audios),'model':QWEN_ID,'model_revision':model['model_revision'],'source_text_audio_use_cleared':False,'model_license_obligations_met':False,'territories':[],'reviewer':'','reviewed_at':'','basis_notes':''}
    rights=run/'audio_rights_review.json'
    if not rights.exists():atomic_json(rights,rights_template)
    elif any(read_json(rights).get(k)!=rights_template[k] for k in ('source_sha256','plan_sha256','audio_sha256','model','model_revision')):
        atomic_json(run/('audio_rights_review.STALE.'+str(time.time_ns())+'.json'),read_json(rights));atomic_json(rights,rights_template)
    retain_environment_evidence(ctx)
    return delivery,music_manifest


def package_candidate(ctx,model):
    assert_audio_allowed(ctx, require_identity=True)
    run=ctx['run'];delivery=read_json(run/'full_generation_manifest.json')
    asr=read_json(run/'asr_report.json') if (run/'asr_report.json').exists() else {}
    review=read_json(run/'full_listening_qa.json') if (run/'full_listening_qa.json').exists() else {}
    issues=[]
    try:
        checked_asr,checked_review,issues=check_reviewed_handoff(ctx,model,delivery)
        asr,review=checked_asr,checked_review
    except Exception as e:issues.append(str(e))
    # Earlier auditions are quality gates, never substitutes for the full-title listen.
    for stage in ('audition','endurance'):
        try:review_stage(ctx,model,stage)
        except Exception as e:issues.append(str(e))
    music=read_json(run/'music_generation_report.json') if delivery.get('atmosphere_included') else None
    retain_environment_evidence(ctx)
    return export_bundle(ctx,delivery,asr,review,music,handoff_issues=issues)


def check_reviewed_handoff(ctx,model,delivery):
    check_delivery_binding(ctx,model,delivery)
    # Bind ASR to every current generation artifact before root export evaluation.
    asr=read_json(ctx['run']/'asr_report.json');segments=check_generation_outputs(ctx,model,'narration')
    require([r['segment_id'] for r in asr.get('records',[])]==[s['segment_id'] for s in segments],'ASR coverage/order mismatch')
    for s,r in zip(segments,asr['records']):
        require(r['audio_sha256']==file_hash(s['output_path']) and r['record_sha256']==file_hash(r['record_path']),'Stale ASR evidence')
        record=read_json(r['record_path'])
        require(record.get('text_sha256')==object_hash(s['text']),'ASR reference text changed')
    review=read_json(ctx['run']/'full_listening_qa.json')
    expected=human_review_template(ctx,audio_bindings(ctx,delivery['audio_files']),'full_title')
    issues=validate_review(review,expected)
    if review.get('encoded_seeks_and_chapter_starts_checked') is not True:issues.append('Encoded playback/seek verification required')
    if delivery['atmosphere_included']:validate_music(ctx,read_json(ctx['run']/'music_generation_report.json'))
    return asr,review,issues


def check_delivery_binding(ctx,model,delivery):
    """Verify that delivery bytes/measurements still belong to current synthesis.

    This rechecks retained artifacts without claiming a fresh model run, human
    review, browser seek check or rights decision. It does not trust a completed
    stage marker when its source plan, units, assembly or encoded files changed.
    """
    import math
    import soundfile as sf
    run=Path(ctx['run']).resolve()
    def local_file(value,label):
        require(isinstance(value,str) and value,label+' path missing')
        path=Path(value).resolve()
        require(path.is_relative_to(run) and path.is_file(),label+' missing or outside title workspace')
        return path
    require(isinstance(delivery,dict),'Delivery manifest missing')
    require(delivery.get('source_sha256')==ctx['artifact']['source_sha256'],'Delivery source hash is stale')
    require(delivery.get('plan_sha256')==ctx['plan_hash'],'Delivery narration plan is stale')
    expected_layout=object_hash(ctx['narration_layout']) if ctx.get('narration_layout') else None
    require(delivery.get('narration_layout_sha256')==expected_layout,'Delivery narration layout evidence is stale')
    require(delivery.get('model_revision')==model['model_revision'],'Delivery model revision is stale')
    segments=check_generation_outputs(ctx,model,'narration')
    current=audio_bindings(ctx,[s['output_path'] for s in segments])
    require(delivery.get('input_audio_sha256')==current,'Delivery uses superseded narration unit bytes')
    assembly=delivery.get('assembly',{})
    require(assembly.get('book_slug')==ctx['artifact']['slug'] and assembly.get('source_sha256')==ctx['artifact']['source_sha256'],'Assembly source identity mismatch')
    units=assembly.get('units',[])
    require([u.get('segment_id') for u in units]==[s['segment_id'] for s in segments],'Assembly unit inventory/order mismatch')
    master_path=local_file(assembly.get('master_wav'),'Assembly master')
    require(file_hash(master_path)==assembly.get('master_sha256'),'Assembly master hash changed')
    master_info=sf.info(master_path)
    require(master_info.frames>0 and master_info.channels==1 and master_info.subtype=='FLOAT','Unexpected assembly master format')
    require(assembly.get('sample_rate')==master_info.samplerate and assembly.get('total_samples')==master_info.frames,'Assembly sample dimensions mismatch')
    rate=master_info.samplerate
    require(math.isclose(assembly.get('duration_seconds',-1),master_info.frames/rate,rel_tol=1e-9),'Assembly duration mismatch')
    position=0
    expected_chapters=[];expected_paragraphs=[]
    for segment,unit in zip(segments,units):
        info=sf.info(segment['output_path'])
        for key in ('chapter_id','paragraph_id','text'):
            require(unit.get(key)==segment[key],'Assembly unit source mismatch: '+key)
        require(unit.get('source_audio_sha256')==file_hash(segment['output_path']),'Assembly contains superseded narration unit')
        require(unit.get('source_audio_frames')==info.frames and info.samplerate==rate,'Assembly native unit dimensions mismatch')
        gap=unit.get('boundary_added_silence_samples')
        require(type(gap) is int and gap>=0,'Assembly silence metadata invalid')
        start,end=unit.get('start_sample'),unit.get('end_sample')
        require(type(start) is int and type(end) is int and start==position+gap and end==start+info.frames,'Assembly unit sample bounds mismatch')
        require(math.isclose(unit.get('start_seconds',-1),start/rate,abs_tol=1e-9) and math.isclose(unit.get('end_seconds',-1),end/rate,abs_tol=1e-9),'Assembly unit seconds mismatch')
        if not expected_chapters or expected_chapters[-1]['chapter_id']!=segment['chapter_id']:
            expected_chapters.append({'chapter_id':segment['chapter_id'],'start_sample':start,'start_seconds':start/rate})
        expected_chapters[-1].update(end_sample=end,end_seconds=end/rate)
        key=(segment['chapter_id'],segment['paragraph_id'])
        if not expected_paragraphs or (expected_paragraphs[-1]['chapter_id'],expected_paragraphs[-1]['paragraph_id'])!=key:
            expected_paragraphs.append({'chapter_id':key[0],'paragraph_id':key[1],'start_sample':start,'start_seconds':start/rate,'segment_ids':[]})
        expected_paragraphs[-1]['segment_ids'].append(segment['segment_id'])
        expected_paragraphs[-1].update(end_sample=end,end_seconds=end/rate)
        position=end
    require(position==master_info.frames,'Assembly total samples differ from current units')
    require(assembly.get('chapters')==expected_chapters and assembly.get('paragraphs')==expected_paragraphs,'Assembly chapter/paragraph bounds mismatch')
    timeline=local_file(assembly.get('timeline_path'),'Assembly timeline')
    require(read_json(timeline)==assembly,'Retained assembly timeline differs from delivery manifest')
    mastering=delivery.get('mastering',{})
    require(mastering.get('sample_rate')==rate and mastering.get('total_samples')==position,'Mastering/assembly dimensions mismatch')
    for flag in ('measured_true_peak_pass','encoded_decode_duration_pass','equal_pcm_duration'):
        require(mastering.get(flag) is True,'Mastering technical gate missing: '+flag)
    expected_modes={'narration','atmosphere'} if delivery.get('atmosphere_included') is True else {'narration'}
    outputs=mastering.get('outputs',{})
    require(set(outputs)==expected_modes and set(mastering.get('delivery_modes',[]))==expected_modes,'Delivery modes mismatch')
    limit=mastering.get('max_true_peak_dbtp')
    require(type(limit) in (int,float) and math.isfinite(limit) and limit<=-1.5,'Mastering true-peak policy mismatch')
    mp3_paths=[]
    for mode in ('narration','atmosphere'):
        if mode not in expected_modes:continue
        item=outputs[mode]
        for codec in ('wav','mp3'):
            path=local_file(item.get(codec),'Mastered '+mode+' '+codec)
            require(file_hash(path)==item.get(codec+'_sha256'),'Mastered '+mode+' '+codec+' hash changed')
            measurement=item.get(codec+'_measurements',{})
            for number in ('integrated_lufs','true_peak_dbtp','loudness_range_lu','gated_threshold_lufs'):
                value=measurement.get(number)
                require(type(value) in (int,float) and math.isfinite(value),'Missing finite '+codec+' loudness measurement')
            require(measurement['true_peak_dbtp']<=limit,'Measured encoded/mastered true peak failed')
            if codec=='wav':
                info=sf.info(path)
                require((info.samplerate,info.frames,info.channels,info.subtype)==(rate,position,1,'PCM_24'),'Delivery PCM dimensions changed')
            else:mp3_paths.append(str(path))
        decoded=item.get('decode_check',{})
        for flag in ('decode_success','sample_count_matches','sample_rate_matches'):
            require(decoded.get(flag) is True,'Encoded decode evidence incomplete')
        require(decoded.get('decoded_samples')==position and decoded.get('expected_samples')==position and decoded.get('decoded_sample_rate')==rate,'Encoded decode duration evidence mismatch')
    require([str(local_file(p,'Delivery audio')) for p in delivery.get('audio_files',[])]==mp3_paths,'Delivery audio inventory/order changed')
    retained=local_file(mastering.get('mastering_manifest_path'),'Mastering measurements')
    require(read_json(retained)=={k:v for k,v in mastering.items() if k!='mastering_manifest_path'},'Retained mastering measurements differ from delivery manifest')
    for path in delivery.get('evidence_files',[]):local_file(path,'Delivery evidence')
    require(delivery.get('evidence_sha256')==audio_bindings(ctx,delivery.get('evidence_files',[])),'Delivery timing or mix evidence changed')
    return {'current_source_plan_and_units_match':True,'assembly_samples_and_hash_match':True,
            'delivery_hashes_and_retained_measurements_match':True,'scope':'Artifact binding and technical evidence only'}
