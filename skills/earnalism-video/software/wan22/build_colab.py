"""Build a portable, inert-by-default Wan2.2 Colab notebook and hashed scene input pack."""
from pathlib import Path
import argparse,base64,hashlib,json,zipfile
from .worker import MODEL,REVISION,SCHEMA,validate,sha

BASE=Path(__file__).resolve().parents[1]
ROOT='/content/earnalism-wan22-diwali-pilot-v1'

def build(destination,art):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True);art=Path(art)
    scenes=[]
    for i,(sid,image,prompt) in enumerate([
      ('homecoming','rama-portrait.png','Preserve this exact painted homecoming scene, all three principal identities, clothing and anatomy. Rama makes one gentle welcoming nod and a small open-hand gesture; Sita turns her gaze toward him and smiles. Lakshmana stays present, breathing gently. The offering child keeps the plate supported with stable fingers. Subtle cloth response, warm lamp flicker. Fixed camera, one continuous respectful shot, no talking, no cuts, no added people or objects. Keep the rich indigo-gold brush-painted style.'),
      ('sweets','living-portrait.png','Preserve this exact painted Diwali family, all four faces, clothing and anatomy. The grandmother gently moves the supported sweets plate a little toward the girl, who takes its weight with coherent hand contact and smiles; the parents react with small natural gaze changes. One restrained clear action with a steady plate; no vanishing sweets or extra fingers. Keep the warm painterly style, subtle lamp flicker, fixed camera, no talking, no cuts, no added objects or text.')]):
        scenes.append({'id':sid,'image':image,'image_sha256':sha(art/image),'width':704,'height':1280,'frames':121,'fps':24,'seed':701+i,'prompt':prompt})
    job={'schema':SCHEMA,'run_id':'diwali-wan22-pilot-v1','model':MODEL,'model_revision':REVISION,
         'max_output_seconds':11,'max_attempts':2,'wall_seconds':1800,'publication_approved':False,'scenes':scenes,
         'purpose':'First Wan motion pilot, ~5.04s per clip. No narrator, music, caption or published media changes.',
         'prior_heygen_completed_seconds':5,'earlier_heygen_cap_seconds':30,
         'compute_scope':'Free by default. Metered Colab requires separate bounded owner authority; no HeyGen compute authority transfers.'}
    validate(job);raw=(json.dumps(job,indent=2)+'\n').encode();(destination/'job.json').write_bytes(raw)
    archive=destination/'wan22-inputs.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_STORED) as z:
        z.writestr('job.json',raw)
        for s in scenes:z.write(art/s['image'],'inputs/'+s['image'])
    payload=base64.b64encode((Path(__file__).with_name('worker.py')).read_bytes()).decode()
    bootstrap=f'''# Run only after checking actual allocation/rate and free or separately scoped owner authority.
if not RUN_WAN:
 print('WAN_DISABLED: no install, model download or generation')
else:
 if not FREE_RUNTIME_CONFIRMED and OWNER_METERED_ALLOWANCE_CU <= 0:
  raise RuntimeError('Free CUDA or a separate bounded owner compute allowance has not been confirmed.')
 import base64,hashlib,json,pathlib,importlib.util,threading,time
 from google.colab import runtime
 ROOT=pathlib.Path({ROOT!r});ROOT.mkdir(parents=True,exist_ok=True)
 source=base64.b64decode({payload!r})
 assert hashlib.sha256(source).hexdigest()=={hashlib.sha256(base64.b64decode(payload)).hexdigest()!r}
 for name,data in [('worker.py',source),('job.json',{raw!r})]:
  p=ROOT/name
  if p.exists() and p.read_bytes()!=data:raise RuntimeError('Preserve existing job/software; do not overwrite '+name)
  if not p.exists():p.write_bytes(data)
 spec=importlib.util.spec_from_file_location('wan_worker',ROOT/'worker.py');worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
 session=worker.begin(ROOT,FREE_RUNTIME_CONFIRMED,OBSERVED_UNITS_PER_HOUR,OWNER_METERED_ALLOWANCE_CU,ALLOCATION_STARTED_AT)
 if 'wan_shutdown_guard' not in globals():
  wan_shutdown_guard=threading.Timer(max(1,session['deadline']-time.time()),runtime.unassign)
  wan_shutdown_guard.daemon=True;wan_shutdown_guard.start()
 try:
  print(json.dumps(worker.preflight(ROOT),indent=2));PREFLIGHT_OK=True
 except BaseException:
  worker.export(ROOT)
  print('PREFLIGHT_HOLD: disconnecting this runtime; no weights installed')
  runtime.unassign()
  raise
'''
    def action(flag,body):
        return f"if not {flag}:\n print('{flag}_DISABLED')\nelse:\n if not (RUN_WAN and globals().get('PREFLIGHT_OK',False)):raise RuntimeError('Run successful free/hardware preflight first')\n"+''.join(' '+line+'\n' for line in body.splitlines())
    upload=action('UPLOAD_INPUTS',f'''# Prefer Colab Files > Upload to session storage if the output-frame picker fails.
path=pathlib.Path('/content/wan22-inputs.zip')
if not path.exists():
 from google.colab import files
 uploaded=files.upload()
 if len(uploaded)!=1:raise RuntimeError('Upload exactly wan22-inputs.zip')
 name,data=next(iter(uploaded.items()))
 path=ROOT/'wan22-inputs.zip';path.write_bytes(data)
worker.unpack_inputs(path,ROOT,{sha(archive)!r})
print('Two source illustrations verified; no generation performed')''')
    setup=action('SETUP_WAN',"try:\n worker.setup(ROOT)\nfinally:\n worker.export(ROOT)\nprint((ROOT/'setup.json').read_text())")
    clips=[action(flag,f"worker.generate(ROOT,{s['id']!r})\nprint((ROOT/'attempts.json').read_text())") for flag,s in zip(['GENERATE_HOMECOMING','GENERATE_SWEETS'],scenes)]
    status="""if RUN_WAN and 'ROOT' in globals():
 for name in ['preflight.json','setup.json','attempts.json','export-receipt.json']:
  p=ROOT/name
  print(name,p.read_text() if p.exists() else 'NOT CREATED')
 for p in ROOT.glob('*.log'):print(p.name,p.read_text()[-1800:])
else:print('WAN_NOT_STARTED')
"""
    download=action('EXPORT_AND_DOWNLOAD',"from google.colab import files\narchive=worker.export(ROOT)\nprint((ROOT/'export-receipt.json').read_text())\nfiles.download(str(archive))")
    shutdown="""if not DISCONNECT_RUNTIME:
 print('DISCONNECT_DISABLED: after verified durable import, enable this cell. The original timer remains active.')
else:
 if not LOCAL_IMPORT_VERIFIED:raise RuntimeError('Verify local archive and member hashes before voluntary shutdown')
 from google.colab import runtime
 runtime.unassign()
"""
    config='''# Safe Run All leaves every costly/interactive operation disabled.
RUN_WAN = False
FREE_RUNTIME_CONFIRMED = False
OBSERVED_UNITS_PER_HOUR = None
OWNER_METERED_ALLOWANCE_CU = 0.0
ALLOCATION_STARTED_AT = None
UPLOAD_INPUTS = False
SETUP_WAN = False
GENERATE_HOMECOMING = False
GENERATE_SWEETS = False
EXPORT_AND_DOWNLOAD = False
LOCAL_IMPORT_VERIFIED = False
DISCONNECT_RUNTIME = False
'''
    intro=f'''# Earnalism · Wan2.2 natural-motion pilot

Private **{MODEL}**, revision `{REVISION}`. Two source-bound portrait scenes, 121 frames at24fps each (~5.04seconds), at most two starts and11seconds reserved output. Selected narration is untouched. No API key, Drive mount, billing setup or public upload.

1. Inspect Colab Resources **before connecting**: confirm a free allocation/rate. This notebook authorizes no paid/prepaid units by default. A separate owner allowance can enable at most5CU/30minutes, with twice the observed-rate headroom. Include startup in `ALLOCATION_STARTED_AT`; record balance changes and stop if the rate/remaining allowance is insufficient. The timer is not a provider-enforced CU quota. Standard pilot floors: nominal24GB CUDA GPU (23000MiB), bf16 support,28GiB host RAM and55GiB free disk. T4 allocations stop. These conservative gates are not universal Wan minima.
2. Enable `RUN_WAN`, `FREE_RUNTIME_CONFIRMED` and set observed rate0 only after actual verification. Run preflight; its30-minute unassign guard covers setup, inference and export. A timer is not a billing cap. No guard extension or automatic retry.
3. Enable upload; choose the accompanying `wan22-inputs.zip` (SHA256 `{sha(archive)}`). Setup downloads approximately34GB of pinned official model files into an isolated environment. No FlashAttention build; pinned Diffusers uses PyTorch SDPA.
4. Enable one scene at a time. Review identity, hands, contact, completion and painted style in actual playback. A failed/started scene is not automatically retried. Report generated footage as unqualified until reviewed.
5. Export/download; verify the complete archive and import locally using the skill helper. Do not treat a download click as durable delivery. For a known transfer problem, test a small pre-generation export first; use the existing hashed-chunk recovery if necessary. The original deadline remains in force.
6. After durable import, set import verified and disconnect. Confirm no connected runtime. Restore saved flags toFalse. Do not use Disconnect on unrelated sessions.

[Wan repository](https://github.com/Wan-Video/Wan2.2) · [Official weights](https://huggingface.co/{MODEL}) · [Diffusers image-to-video guidance](https://github.com/huggingface/diffusers/issues/13258). Apache2.0 source/model notices must be retained with the workflow.
'''
    cells=[]
    for i,(kind,text) in enumerate([('markdown',intro),('code',config),('code',bootstrap),('markdown','## Upload source-bound input pack'),('code',upload),('markdown','## Isolated setup'),('code',setup),('markdown','## Homecoming · first clip'),('code',clips[0]),('markdown','## Sweets exchange · second clip'),('code',clips[1]),('markdown','## Status and provenance'),('code',status),('markdown','## Export and verify durable local import'),('code',download),('markdown','## Disconnect this runtime after verified import'),('code',shutdown)]):
        c={'id':f'wan-{i:02}','cell_type':kind,'metadata':{},'source':text.splitlines(keepends=True)}
        if kind=='code':c.update(execution_count=None,outputs=[])
        cells.append(c)
    notebook={'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'name':'python3','display_name':'Python3'},'language_info':{'name':'python'},'colab':{'name':'Earnalism_Wan22_Natural_Motion.ipynb'}},'cells':cells}
    target=destination/'Earnalism_Wan22_Natural_Motion.ipynb';target.write_text(json.dumps(notebook,indent=1)+'\n')
    (destination/'build-manifest.json').write_text(json.dumps({'notebook_sha256':sha(target),'inputs_sha256':sha(archive),'job_sha256':sha(destination/'job.json'),'worker_sha256':sha(Path(__file__).with_name('worker.py')),'inference_qualified':False,'publication_approved':False},indent=2)+'\n')
    return target

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('destination');p.add_argument('--art',required=True);a=p.parse_args();print(build(a.destination,a.art))
