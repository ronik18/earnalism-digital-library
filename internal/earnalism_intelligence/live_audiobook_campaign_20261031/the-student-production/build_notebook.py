from pathlib import Path
import zipfile,io,base64,json,hashlib,ast
B=Path('/tmp/earnalism-student-preflight-20261031')
buffer=io.BytesIO()
with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
 for n in ['qwen_worker.py','owner_audio_policy.py','pipeline_core.py','narration_layout.py','notebook_runtime.py']:
  z.write(B/'worker'/n,'worker/'+n)
 for n in ['audition-job.json','actual-source-preflight.json','worker-contract-preflight.json','qwen-config.json','qwen-model.json']:
  z.write(B/n,n)
payload=buffer.getvalue();(B/'audition-payload.zip').write_bytes(payload)
code='''# One private Ryan audition only. No Drive mount, production API, publication or purchase.
import base64,hashlib,io,json,pathlib,sys,threading,time,traceback,zipfile,subprocess
from google.colab import files,runtime
START=time.monotonic(); BUDGET=30*60
root=pathlib.Path('/content/earnalism-student');root.mkdir(exist_ok=True)
if (root/'allocation-start.json').exists():
    raise RuntimeError('ALLOCATION_ALREADY_REQUESTED: preserve and reconcile; no automatic replay')
(root/'allocation-start.json').write_text(json.dumps({'stage':'private_representative_audition','max_allocations':1,'max_minutes':30,'max_attempts_per_unit':1,'no_purchases':True,'new_cash_spend_ceiling_usd':0,'publication':False,'monotonic_start':START}))
def shutdown():
    try:runtime.unassign()
    except Exception:pass
watchdog=threading.Timer(BUDGET,shutdown);watchdog.daemon=True;watchdog.start()
try:
    raw=base64.b64decode(PAYLOAD)
    assert hashlib.sha256(raw).hexdigest()==PAYLOAD_HASH
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for n in z.namelist():
            p=(root/n).resolve();assert p.is_relative_to(root.resolve())
        z.extractall(root)
    sys.path.insert(0,str(root/'worker'))
    import notebook_runtime as setup
    import torch
    assert torch.cuda.is_available(),'CUDA_REQUIRED_NO_FALLBACK'
    assert torch.cuda.device_count()==1,'ONE_GPU_ONLY'
    print(json.dumps({'stage':'admission','gpu':torch.cuda.get_device_name(0),'samples':7,'new_cash_spend_ceiling_usd':0,'max_minutes':30}),flush=True)
    setup.BASE_VENV_DIR=root/'venvs'
    py,model=setup.setup_qwen(root)
    job=json.loads((root/'audition-job.json').read_text())
    assert model['model_id']==job['model_id'] and model['model_revision']==job['model_revision']
    job['model_path']=model['model_path']
    assert job['max_attempts']==1 and len(job['segments'])==7
    (root/'audition-job.json').write_text(json.dumps(job,indent=2))
    remaining=BUDGET-(time.monotonic()-START)-100
    assert remaining>0,'Budget exhausted during setup; no inference allowed'
    subprocess.run([str(py),str(root/'worker/qwen_worker.py'),str(root/'audition-job.json')],check=True,timeout=remaining)
    print('GENERATED_REQUIRES_REAL_TEXT_AUDIO_AND_LISTENING_REVIEW; NOT_RELEASE_READY',flush=True)
except BaseException as e:
    (root/'execution-error.json').write_text(json.dumps({'type':type(e).__name__,'error':str(e),'elapsed_seconds':time.monotonic()-START,'automatic_retry':False}))
    traceback.print_exc()
finally:
    (root/'allocation-finish.json').write_text(json.dumps({'elapsed_seconds':time.monotonic()-START,'actual_provider_charge':'NOT_REPORTED','new_purchase_performed':False,'release_ready':False}))
    export=pathlib.Path('/content/Earnalism_Student_Private_Audition_20261031.zip')
    with zipfile.ZipFile(export,'w',zipfile.ZIP_DEFLATED) as z:
        for p in root.rglob('*'):
            if p.is_file() and not any(x in p.parts for x in ['venvs','hf-cache','.cache','__pycache__']):
                z.write(p,p.relative_to(root))
    print(json.dumps({'export':export.name,'bytes':export.stat().st_size,'sha256':hashlib.sha256(export.read_bytes()).hexdigest(),'release_ready':False}),flush=True)
    files.download(str(export))
    print('Export requested. This allocation will disconnect in 90 seconds; no automatic retry.',flush=True)
    release=threading.Timer(90,shutdown);release.daemon=True;release.start()
'''
code='PAYLOAD='+repr(base64.b64encode(payload).decode())+'\nPAYLOAD_HASH='+repr(hashlib.sha256(payload).hexdigest())+'\n'+code
ast.parse(code)
nb={'nbformat':4,'nbformat_minor':5,'metadata':{'colab':{'name':'Earnalism_The_Student_Private_Audition_20261031.ipynb'},'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'accelerator':'GPU','gpuClass':'standard'},'cells':[{'cell_type':'markdown','metadata':{},'source':['# The Student — private Ryan audition\nSeven exact-source representative passages. One GPU allocation, at most 30 minutes, one take per passage, no automatic retries, no purchases, no Drive access, no production writes. Full generation and publication remain disabled. Preserve/download the output ZIP before automatic disconnect.']},{'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':code.splitlines(keepends=True)}]}
p=B/'Earnalism_The_Student_Private_Audition_20261031.ipynb';p.write_text(json.dumps(nb,ensure_ascii=False,indent=1)+'\n')
print('Prepared notebook',len(p.read_bytes()),'payload',len(payload),'SHA256',hashlib.sha256(p.read_bytes()).hexdigest())
