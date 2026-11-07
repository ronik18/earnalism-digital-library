"""Isolated Wan2.2 Colab pilot. Standard library control plane; no imports of torch until inference."""
from pathlib import Path
import argparse, contextlib, fcntl, hashlib, json, os, re, shutil, subprocess, sys, time, zipfile

MODEL = 'Wan-AI/Wan2.2-TI2V-5B-Diffusers'
REVISION = 'b8fff7315c768468a5333511427288870b2e9635'
DEPS = ['diffusers==0.36.0','transformers==4.51.3','accelerate==1.6.0',
        'huggingface_hub==0.36.0','safetensors==0.5.3','sentencepiece==0.2.0',
        'ftfy==6.3.1','imageio==2.37.0','imageio-ffmpeg==0.6.0','Pillow==11.2.1']
SCHEMA = 'earnalism.wan22-pilot.v1'


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def write(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,indent=2)+'\n');tmp.replace(p)


def inside(root,name):
    if not isinstance(name,str) or not name or Path(name).is_absolute():raise ValueError('Invalid relative path')
    p=(Path(root)/name).resolve()
    if not p.is_relative_to(Path(root).resolve()):raise ValueError('Path escapes bundle')
    return p


def validate(job):
    if job.get('schema')!=SCHEMA or not re.fullmatch('[a-z0-9-]+',job.get('run_id','')):raise ValueError('Invalid job/run ID')
    if job.get('model')!=MODEL or job.get('model_revision')!=REVISION:raise ValueError('Unreviewed model or revision')
    if job.get('publication_approved') is not False:raise ValueError('Private pilot only')
    scenes=job.get('scenes',[])
    if len(scenes)!=2 or len({s['id'] for s in scenes})!=2:raise ValueError('Two unique pilot scenes required')
    seconds=0
    for s in scenes:
        if not re.fullmatch('[a-z0-9-]+',s['id']) or Path(s['image']).name!=s['image']:raise ValueError('Unsafe scene name')
        if not re.fullmatch('[a-f0-9]{64}',s['image_sha256']):raise ValueError('Missing image hash')
        if (s['width'],s['height'])!=(704,1280) or s['frames']!=121 or s['fps']!=24:raise ValueError('Unreviewed pilot shape')
        if not isinstance(s['prompt'],str) or not 10<len(s['prompt'])<3000:raise ValueError('Invalid prompt')
        seconds+=s['frames']/s['fps']
    if not seconds<=job.get('max_output_seconds',0)<=11:raise ValueError('Pilot seconds exceed bounded allowance')
    if job.get('max_attempts')!=2 or job.get('wall_seconds')!=1800:raise ValueError('Unreviewed attempt/runtime cap')
    return job


def open_job(root):
    root=Path(root);job=validate(json.loads((root/'job.json').read_text()))
    for s in job['scenes']:
        if sha(inside(root,'inputs/'+s['image']))!=s['image_sha256']:raise ValueError('Changed source illustration')
    return job


def unpack_inputs(archive,root,expected_sha):
    if sha(archive)!=expected_sha:raise ValueError('Input archive hash mismatch')
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        if sum(i.file_size for i in z.infolist())>20*1024**2:raise ValueError('Oversized input bundle')
        names=z.namelist()
        if len(names)!=len(set(names)) or set(names)!={'job.json','inputs/rama-portrait.png','inputs/living-portrait.png'}:raise ValueError('Unexpected bundle members')
        for info in z.infolist():
            dest=inside(root,info.filename)
            if (info.external_attr>>16)&0o170000==0o120000:raise ValueError('Archive symlink')
            data=z.read(info)
            if dest.exists() and dest.read_bytes()!=data:raise ValueError('Preserve existing input/job')
            dest.parent.mkdir(parents=True,exist_ok=True)
            if not dest.exists():dest.write_bytes(data)
    return open_job(root)


def begin(root,free_confirmed=False,observed_rate=None,approved_compute_units=0,allocation_started_at=None):
    """Billing attestation must come from actual Colab UI; GPU discovery cannot prove cost."""
    free=free_confirmed is True and observed_rate==0 and approved_compute_units==0
    metered=isinstance(observed_rate,(int,float)) and observed_rate>0 and 0<approved_compute_units<=5 and 2*observed_rate*1800/3600<=approved_compute_units
    if not (free or metered):raise RuntimeError('Confirm actual free allocation/rate or a separate bounded owner allowance first')
    root=Path(root);job=validate(json.loads((root/'job.json').read_text()));path=root/'session.json';now=time.time()
    if path.exists():
        state=json.loads(path.read_text())
        if state['job_sha256']!=sha(root/'job.json'):raise RuntimeError('Job changed during existing session')
        if state.get('free_runtime_confirmed')!=free or state.get('observed_units_per_hour')!=observed_rate or state.get('approved_compute_units',0)!=approved_compute_units:raise RuntimeError('Compute allocation/authority changed; inspect before resuming')
        if now>=state['deadline']:raise RuntimeError('Original session deadline expired; do not silently reset')
    else:
        started=now if allocation_started_at is None else float(allocation_started_at)
        if not now-1800<started<=now:raise RuntimeError('Invalid or expired allocation start')
        if metered and allocation_started_at is None:raise RuntimeError('Metered mode needs the actual allocation start, including startup')
        state={'started':started,'deadline':started+job['wall_seconds'],'job_sha256':sha(root/'job.json'),
               'free_runtime_confirmed':free,'observed_units_per_hour':observed_rate,'approved_compute_units':approved_compute_units,'guard_is_provider_quota':False}
        write(path,state)
    return state


def remaining(root,reserve=120):
    state=json.loads((Path(root)/'session.json').read_text())
    free=state.get('free_runtime_confirmed') is True and state.get('observed_units_per_hour')==0
    rate=state.get('observed_units_per_hour',0);allowance=state.get('approved_compute_units',0)
    metered=isinstance(rate,(int,float)) and rate>0 and 0<allowance<=5 and 2*rate*1800/3600<=allowance
    if not (free or metered):raise RuntimeError('No valid compute authority evidence')
    if state['job_sha256']!=sha(Path(root)/'job.json'):raise RuntimeError('Changed job binding')
    n=state['deadline']-time.time()-reserve
    if n<=0:raise RuntimeError('Session deadline reached; preserve export, do not extend guard')
    return n


def preflight(root):
    job=validate(json.loads((Path(root)/'job.json').read_text()));remaining(root)
    result=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True)
    rows=result.stdout.strip().splitlines()
    if len(rows)!=1:raise RuntimeError('One inspected CUDA GPU required')
    name,mib=rows[0].rsplit(',',1);mib=float(mib)
    ram=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal:')))*1024
    disk=shutil.disk_usage(root).free
    record={'gpu':name.strip(),'vram_mib':mib,'host_ram_gib':ram/1024**3,'free_disk_gib':disk/1024**3,
            'configured_floors':{'vram_mib':23000,'host_ram_gib':28,'disk_gib':55},
            'scope':'Conservative standard 5B pilot preflight, not a universal hardware minimum or free-billing detector'}
    write(Path(root)/'preflight.json',record)
    if mib<23000 or ram<28*1024**3 or disk<55*1024**3:raise RuntimeError('Insufficient standard pilot hardware; no weights downloaded. Do not auto-upgrade or substitute models')
    subprocess.run([sys.executable,'-c',"import torch;assert torch.cuda.is_available() and torch.cuda.is_bf16_supported();assert tuple(map(int,torch.__version__.split('+')[0].split('.')[:2]))>=(2,4)"],check=True)
    return record


def command(root,args,log):
    with (Path(root)/log).open('a') as f:
        subprocess.run([str(a) for a in args],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=remaining(root))


def setup(root):
    root=Path(root);open_job(root);preflight(root)
    py=root/'venv/bin/python'
    if not py.exists():command(root,[sys.executable,'-m','venv','--system-site-packages',root/'venv'],'setup.log')
    command(root,[py,'-m','pip','install',*DEPS],'setup.log')
    command(root,[py,'-c',"from huggingface_hub import snapshot_download;import sys;snapshot_download(repo_id=sys.argv[1],revision=sys.argv[2],local_dir=sys.argv[3],allow_patterns=['model_index.json','scheduler/*','tokenizer/*','text_encoder/*','transformer/*','vae/*'])",MODEL,REVISION,root/'model'],'setup.log')
    command(root,[py,'-c',"import torch,diffusers,transformers,accelerate;from diffusers import WanImageToVideoPipeline;print('versions',torch.__version__,diffusers.__version__,transformers.__version__,accelerate.__version__);print('CUDA',torch.version.cuda,torch.cuda.get_device_name())"],'setup.log')
    result=subprocess.check_output([str(py),'-m','pip','freeze'],text=True);(root/'dependencies.lock.txt').write_text(result)
    write(root/'setup.json',{'state':'SETUP_COMPLETED_NOT_INFERENCE_QUALIFIED','model':MODEL,'revision':REVISION,'pipeline':'WanImageToVideoPipeline','expand_timesteps':True,'attention':'PyTorch SDPA; no FlashAttention compilation','time':time.time()})


def probe_video(path,scene):
    subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],capture_output=True,check=True)
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(path)],text=True))
    streams=info['streams'];v=streams[0]
    if len(streams)!=1 or v['codec_type']!='video' or v['codec_name']!='h264':raise ValueError('Expected silent H264 video only')
    if (v['width'],v['height'])!=(scene['width'],scene['height']) or int(v['nb_read_frames'])!=scene['frames'] or v['r_frame_rate']!='24/1':raise ValueError('Wrong generated shape/frame count/fps')
    if abs(float(info['format']['duration'])-scene['frames']/24)>.05:raise ValueError('Wrong generated duration')
    return info


def infer(root,scene_id):
    import torch
    from diffusers import AutoencoderKLWan, WanImageToVideoPipeline
    from diffusers.utils import load_image, export_to_video
    root=Path(root);job=open_job(root);s=next(s for s in job['scenes'] if s['id']==scene_id)
    vae=AutoencoderKLWan.from_pretrained(root/'model',subfolder='vae',torch_dtype=torch.float32,local_files_only=True)
    pipe=WanImageToVideoPipeline.from_pretrained(root/'model',vae=vae,torch_dtype=torch.bfloat16,local_files_only=True,expand_timesteps=True)
    pipe.vae.enable_tiling();pipe.enable_model_cpu_offload()
    frames=pipe(image=load_image(str(root/'inputs'/s['image'])),prompt=s['prompt'],
        negative_prompt='text, logo, watermark, extra fingers, fused hands, duplicate people, face morphing, abrupt cuts, camera shake',
        height=s['height'],width=s['width'],num_frames=s['frames'],num_inference_steps=50,guidance_scale=5.0,
        generator=torch.Generator(device='cpu').manual_seed(s['seed'])).frames[0]
    export_to_video(frames,str(root/'outputs'/f'{scene_id}.mp4'),fps=24)


def generate(root,scene_id):
    root=Path(root);job=open_job(root);remaining(root)
    if scene_id not in {s['id'] for s in job['scenes']}:raise ValueError('Unknown scene')
    if not (root/'setup.json').exists():raise RuntimeError('Complete setup first')
    with (root/'generation.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger_path=root/'attempts.json';ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else []
        if any(r['scene']==scene_id for r in ledger):raise RuntimeError('Scene already attempted; inspect/export it, do not retry or overwrite')
        if len(ledger)>=job['max_attempts']:raise RuntimeError('Pilot attempt cap exhausted')
        s=next(s for s in job['scenes'] if s['id']==scene_id)
        reserved=sum(r['reserved_seconds'] for r in ledger)+s['frames']/24
        if reserved>job['max_output_seconds']:raise RuntimeError('Pilot duration cap exhausted')
        row={'scene':scene_id,'status':'STARTED','reserved_seconds':s['frames']/24,'started':time.time(),'seed':s['seed'],'source_sha256':s['image_sha256']}
        ledger.append(row);write(ledger_path,ledger);(root/'outputs').mkdir(exist_ok=True)
        try:
            command(root,[root/'venv/bin/python',Path(__file__).resolve(),'infer',str(root),'--scene',scene_id],f'{scene_id}.log')
            output=root/'outputs'/f'{scene_id}.mp4';probe=probe_video(output,s)
            row.update(status='TECHNICAL_PASS_REVIEW_PENDING',sha256=sha(output),probe=probe,ended=time.time(),motion_review='PENDING')
        except BaseException as e:
            row.update(status='FAILED_NO_AUTOMATIC_RETRY',error=type(e).__name__+': '+str(e),ended=time.time());raise
        finally:
            write(ledger_path,ledger);export(root)


def export(root):
    root=Path(root);names=['job.json','session.json','preflight.json','setup.json','attempts.json','dependencies.lock.txt']
    files=[root/n for n in names if (root/n).exists()]+list(root.glob('*.log'))+list((root/'outputs').glob('*.mp4'))
    manifest={'schema':'earnalism.wan22-export.v1','job_sha256':sha(root/'job.json'),'model':MODEL,'model_revision':REVISION,
              'private':True,'publication_approved':False,'files':{str(p.relative_to(root)):sha(p) for p in files},'quality_acceptance':'PENDING'}
    write(root/'export-manifest.json',manifest)
    archive=root/'wan22-export.zip';tmp=root/'wan22-export.tmp.zip'
    with zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_STORED) as z:
        for p in files+[root/'export-manifest.json']:z.write(p,str(p.relative_to(root)))
    tmp.replace(archive);write(root/'export-receipt.json',{'archive_sha256':sha(archive),'bytes':archive.stat().st_size,'durable_local_import':'PENDING'})
    return archive


def import_export(archive,destination,expected_archive_sha,job_path):
    if sha(archive)!=expected_archive_sha:raise ValueError('Export archive hash mismatch')
    job=validate(json.loads(Path(job_path).read_text()));destination=Path(destination)
    if destination.exists():raise FileExistsError('Preserve existing imports')
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or sum(i.file_size for i in z.infolist())>256*1024**2:raise ValueError('Invalid export archive size/members')
        for i in z.infolist():
            inside(destination,i.filename)
            if (i.external_attr>>16)&0o170000==0o120000:raise ValueError('Archive symlink')
        m=json.loads(z.read('export-manifest.json'))
        if m.get('schema')!='earnalism.wan22-export.v1' or m.get('publication_approved') is not False or m.get('private') is not True or m.get('job_sha256')!=sha(job_path) or m.get('model_revision')!=REVISION or m.get('model')!=MODEL:raise ValueError('Export provenance mismatch')
        if set(names)!=set(m['files'])|{'export-manifest.json'}:raise ValueError('Unbound export members')
        for name,h in m['files'].items():
            if hashlib.sha256(z.read(name)).hexdigest()!=h:raise ValueError('Changed export member')
        if z.read('job.json')!=Path(job_path).read_bytes():raise ValueError('Changed exported job')
        destination.mkdir(parents=True)
        for name in names:inside(destination,name).parent.mkdir(parents=True,exist_ok=True);inside(destination,name).write_bytes(z.read(name))
    accepted=[];rejected=[]
    ledger=json.loads((destination/'attempts.json').read_text()) if (destination/'attempts.json').exists() else []
    if len(ledger)>job['max_attempts'] or sum(r.get('reserved_seconds',0) for r in ledger)>job['max_output_seconds']:raise ValueError('Imported attempt ledger exceeds cap')
    for s in job['scenes']:
        p=destination/'outputs'/f"{s['id']}.mp4"
        if p.exists():
            row=next((r for r in ledger if r.get('scene')==s['id']),{})
            if row.get('status')!='TECHNICAL_PASS_REVIEW_PENDING' or row.get('sha256')!=sha(p) or row.get('source_sha256')!=s['image_sha256']:
                rejected.append({'scene':s['id'],'reason':'No matching completed attempt/source binding'});continue
            try:probe_video(p,s)
            except (ValueError,subprocess.SubprocessError) as e:
                rejected.append({'scene':s['id'],'reason':str(e)});continue
            accepted.append({'scene':s['id'],'file':str(p),'sha256':sha(p),'technical_verified':True,'motion_accepted':False,'source_image_sha256':s['image_sha256']})
    write(destination/'import-receipt.json',{'archive_sha256':expected_archive_sha,'clips':accepted,'rejected':rejected,'publication_approved':False,'quality_review':'PENDING'})
    return accepted


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['preflight','setup','generate','infer','export']);parser.add_argument('root');parser.add_argument('--scene');a=parser.parse_args()
    if a.action in ['infer','generate']:globals()[a.action](Path(a.root),a.scene)
    else:print(globals()[a.action](Path(a.root)))
