import importlib.util
import json
import hashlib
from pathlib import Path
import subprocess
import os
import shutil
import time
import pytest

ROOT=Path(__file__).resolve().parents[2]

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load(ROOT/'backend/utils/runtime_source_attestation.py','test_runtime_source')
builder=load(ROOT/'scripts/build_runtime_source_manifest.py','test_runtime_builder')

def fixture(root, files=None):
    files=files or {'server.py':b'public dummy code','data/title.json':b'{"audio":false}'}
    rows=[]
    for name,data in sorted(files.items()):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        rows.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    result={'schema':m.SCHEMA,'scope':m.SCOPE,'files':rows,'expected_sha256':m.inventory_digest(rows)}
    (root/m.MANIFEST).write_text(json.dumps(result));return result

def test_runtime_actual_bytes_and_no_content_or_paths_exposed(tmp_path):
    expected=fixture(tmp_path);r=m.measure(tmp_path)
    assert r['status']=='MEASURED_MATCHES_MANIFEST'
    assert r['observed_sha256']==expected['expected_sha256'] and r['file_count']==2
    assert 'public dummy code' not in str(r) and 'server.py' not in str(r)
    assert 'git_sha' not in r

def test_same_size_tampering_is_mismatch(tmp_path):
    fixture(tmp_path);(tmp_path/'server.py').write_bytes(b'PUBLIC dummy code')
    assert m.measure(tmp_path)['status']=='MISMATCH'

@pytest.mark.parametrize('case',['missing','grown','file_symlink','parent_symlink','fifo'])
def test_missing_or_unsafe_files_fail_closed(tmp_path,case):
    fixture(tmp_path)
    if case=='missing':(tmp_path/'server.py').unlink()
    if case=='grown':(tmp_path/'server.py').write_bytes(b'larger source that is not the candidate')
    if case=='file_symlink':
        (tmp_path/'server.py').unlink();(tmp_path/'server.py').symlink_to('/etc/passwd')
    if case=='parent_symlink':
        (tmp_path/'data/title.json').unlink();(tmp_path/'data').rmdir();(tmp_path/'data').symlink_to('/etc')
    if case=='fifo':
        (tmp_path/'server.py').unlink();os.mkfifo(tmp_path/'server.py')
    assert m.measure(tmp_path)['status']=='UNAVAILABLE'

@pytest.mark.parametrize('path',['../outside','/etc/passwd','a/../b','a//b','a\\b','.env','x/.env.prod','.aws/credentials','x.pem','tests/private.py',m.MANIFEST])
def test_private_traversal_and_excluded_paths_rejected(path):
    assert not m.delivered_path(path)

@pytest.mark.parametrize('case',['duplicate','digest','schema','size','too_many','bad_sha'])
def test_bad_inventory_is_unavailable(tmp_path,case):
    d=fixture(tmp_path)
    if case=='duplicate':d['files'].append(d['files'][0])
    if case=='digest':d['expected_sha256']='0'*64
    if case=='schema':d['extra']='should not be accepted'
    if case=='size':d['files'][0]['bytes']=m.MAX_TOTAL_BYTES+1
    if case=='too_many':d['files']=d['files']*(m.MAX_FILES+1)
    if case=='bad_sha':d['files'][0]['sha256']='not a hash'
    (tmp_path/m.MANIFEST).write_text(json.dumps(d))
    assert m.measure(tmp_path)['status']=='UNAVAILABLE'

def test_deadline_reports_unavailable_not_match(tmp_path):
    fixture(tmp_path);ticks=iter([0,5])
    assert m.measure(tmp_path,clock=lambda:next(ticks))['status']=='UNAVAILABLE'

def test_missing_manifest_keeps_health_attestation_unavailable(tmp_path):
    assert m.measure(tmp_path)['status']=='UNAVAILABLE'

def test_git_builder_uses_staged_blobs_and_exact_ref_without_secrets(tmp_path):
    repo=tmp_path/'repo';(repo/'backend/utils').mkdir(parents=True)
    shutil.copy2(ROOT/'backend/utils/runtime_source_attestation.py',repo/'backend/utils/runtime_source_attestation.py')
    (repo/'backend/server.py').write_text('staged code\n')
    (repo/'backend/tests').mkdir();(repo/'backend/tests/test_dummy.py').write_text('test only')
    (repo/'backend/.env.example').write_text('not source coverage')
    def git(*args):return subprocess.check_output(['git',*args],cwd=repo,stderr=subprocess.DEVNULL)
    git('init');git('add','backend')
    staged=builder.build(repo)
    assert 'tests/test_dummy.py' not in {x['path'] for x in staged['files']}
    assert '.env.example' not in {x['path'] for x in staged['files']}
    (repo/'backend/server.py').write_text('unstaged code\n')
    assert builder.build(repo)==staged
    (repo/'backend'/m.MANIFEST).write_text(json.dumps(staged))
    assert m.measure(repo/'backend')['status']=='UNAVAILABLE'  # changed size
    (repo/'backend/server.py').write_text('staged code\n')
    assert m.measure(repo/'backend')['status']=='MEASURED_MATCHES_MANIFEST'
    git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','dummy fixture')
    assert builder.build(repo,'HEAD')==staged


def test_cached_runtime_wrapper_is_one_snapshot(monkeypatch):
    m.runtime_source_attestation.cache_clear();calls=[]
    monkeypatch.setattr(m,'measure',lambda root: calls.append(root) or {'status':'UNAVAILABLE'})
    a=m.runtime_source_attestation();b=m.runtime_source_attestation()
    assert a==b and len(calls)==1 and a['snapshot_cached_for_process'] is True
    m.runtime_source_attestation.cache_clear()


def test_actual_health_routes_publish_measured_source_without_git_inference(monkeypatch,tmp_path):
    import ast,asyncio,sys
    from types import SimpleNamespace
    from fastapi import FastAPI,APIRouter,Response
    import httpx
    fixture(tmp_path);observed=m.measure(tmp_path)
    # Exact proposed handlers, container imports; provider provenance stays null.
    monkeypatch.setitem(sys.modules,'utils',SimpleNamespace())
    monkeypatch.setitem(sys.modules,'utils.deployment_attestation',SimpleNamespace(deployment_attestation=lambda:{'git_sha':None,'status':'UNAVAILABLE'}))
    monkeypatch.setitem(sys.modules,'utils.runtime_source_attestation',SimpleNamespace(runtime_source_attestation=lambda:observed))
    app=FastAPI();api=APIRouter(prefix='/api');ns=dict(app=app,api=api,Response=Response,MULTI_REPLICA_ENABLED=False)
    source=ROOT/'backend/server.py'
    if not source.exists(): source=ROOT/'PATCHED-SERVER.py'
    tree=ast.parse(source.read_text());nodes=[n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name in ('root_healthz_check','api_healthz_check')]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'exact-health-handlers','exec'),ns);app.include_router(api)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://dummy') as c:
            for path in ['/healthz','/api/healthz']:
                r=await c.get(path);assert r.status_code==200 and r.headers['cache-control']=='no-store'
                assert r.json()['deployment']['git_sha'] is None
                assert r.json()['runtime_source']['observed_sha256']==observed['observed_sha256']
                assert r.json()['runtime_source']['status']=='MEASURED_MATCHES_MANIFEST'
    asyncio.run(run())
