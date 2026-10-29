"""Create/verify the delivered source inventory from staged Git blobs or an exact ref.

Run after staging final backend edits, before staging the generated manifest. The
manifest excludes itself, so no circular commit/hash claim is needed. No network.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import hashlib


def module(repo):
    spec = importlib.util.spec_from_file_location('runtime_source_contract', repo/'backend/utils/runtime_source_attestation.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def build(repo, ref=None):
    repo = Path(repo); contract = module(repo)
    env = {**os.environ, 'GIT_NO_LAZY_FETCH': '1'}
    args = ['git', '-c', 'remote.origin.promisor=false']
    if ref:
        raw = subprocess.check_output(args+['ls-tree','-rz',ref,'--','backend'],cwd=repo,env=env)
    else:
        raw = subprocess.check_output(args+['ls-files','--stage','-z','--','backend'],cwd=repo,env=env)
    rows=[]; objects=[]
    for item in raw.split(b'\0'):
        if not item: continue
        header, path = item.split(b'\t',1); path=path.decode('utf-8'); mode,kind,stage=header.decode().split()
        if ref: oid=stage
        else:
            oid=kind
            if stage!='0': raise ValueError('unmerged index')
        relative=path.removeprefix('backend/')
        if not contract.delivered_path(relative): continue
        if mode not in {'100644','100755'}: raise ValueError('non-regular source')
        objects.append((relative,oid))
    if not 1<=len(objects)<=contract.MAX_FILES: raise ValueError('file bound')
    # One local Git process; no lazy fetch, credentials, live database or provider.
    p=subprocess.Popen(args+['cat-file','--batch'],cwd=repo,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    try:
        total=0
        for path,oid in sorted(objects):
            p.stdin.write((oid+'\n').encode());p.stdin.flush()
            header=p.stdout.readline().decode().strip().split()
            if len(header)!=3 or header[0]!=oid or header[1]!='blob': raise ValueError('missing source blob')
            size=int(header[2]);total+=size
            if total>contract.MAX_TOTAL_BYTES:raise ValueError('byte bound')
            h=hashlib.sha256();remaining=size
            while remaining:
                data=p.stdout.read(min(65536,remaining))
                if not data:raise ValueError('truncated source blob')
                remaining-=len(data);h.update(data)
            if p.stdout.read(1)!=b'\n':raise ValueError('invalid Git stream')
            rows.append({'path':path,'bytes':size,'sha256':h.hexdigest()})
        p.stdin.close()
        if p.wait(timeout=5)!=0:raise ValueError('Git failure')
    finally:
        if p.poll() is None:p.terminate();p.wait(timeout=5)
    return {'schema':contract.SCHEMA,'scope':contract.SCOPE,'files':rows,'expected_sha256':contract.inventory_digest(rows)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,default=Path.cwd());p.add_argument('--ref');p.add_argument('--verify',action='store_true');a=p.parse_args()
    result=build(a.repo,a.ref);path=a.repo/'backend/.runtime-source-manifest.json'
    if a.verify:
        if json.loads(path.read_text())!=result:raise SystemExit('Source inventory does not match exact Git source')
    else:path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'files':len(result['files']),'expected_sha256':result['expected_sha256'],'mode':'VERIFY' if a.verify else 'PREPARED_LOCAL_MANIFEST'}))
if __name__=='__main__':main()
