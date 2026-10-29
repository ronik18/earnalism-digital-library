"""Read a successful exact-head published review; never rerun a workflow or use an expired baseline."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import time
import zipfile

REPO = 'ronik18/earnalism-digital-library'
WORKFLOW = 'seamless-brand-owner-review.yml'


def select_run(rows, head):
    rows = [r for r in rows if r.get('head_sha') == head and r.get('event') == 'pull_request']
    if not rows:
        return None
    row = max(rows, key=lambda r: r['id'])
    if row['status'] != 'completed':
        return None
    if row.get('conclusion') != 'success':
        raise ValueError('Exact-head primary review failed; no retry or older fallback')
    return row


def extract_verified(archive, output):
    with zipfile.ZipFile(archive) as z:
        rows = z.infolist()
        names = [r.filename for r in rows]
        if len(rows) > 5000 or len(set(names)) != len(names) or sum(r.file_size for r in rows) > 512*1024*1024:
            raise ValueError('Archive count/duplicate/byte bound')
        for r in rows:
            p = PurePosixPath(r.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in r.filename or (r.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Unsafe archive path')
        z.extractall(output)


def verify_package(root, head):
    manifest = root/'manifest.json'
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != (root/'manifest.sha256').read_text().strip():
        raise ValueError('Manifest digest differs')
    if json.loads((root/'provenance.json').read_text()).get('package_generation_head') != head:
        raise ValueError('Package is not exact head')
    for row in json.loads(manifest.read_text())['files']:
        p = PurePosixPath(row['path'])
        if p.is_absolute() or '..' in p.parts or '\\' in row['path']:
            raise ValueError('Unsafe manifest path')
        f = root/row['path']
        if f.stat().st_size != row['bytes'] or hashlib.sha256(f.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Manifest file bytes differ')


def main():
    a = argparse.ArgumentParser();a.add_argument('--head',required=True);a.add_argument('--output',type=Path,required=True);args=a.parse_args()
    if not re.fullmatch('[0-9a-f]{40}',args.head) or args.output.exists():
        raise ValueError('Exact head and fresh output required')
    def api(path):
        return json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/{path}'],text=True,timeout=45))
    deadline=time.monotonic()+1800
    while True:
        run=select_run(api(f'actions/workflows/{WORKFLOW}/runs?head_sha={args.head}&event=pull_request&per_page=30')['workflow_runs'],args.head)
        if run:break
        if time.monotonic()>=deadline:raise TimeoutError('Exact-head published review unavailable within 30 minutes')
        time.sleep(15)
    artifact_name=f'pr344-seamless-brand-final-review-{args.head}'
    rows=api(f"actions/runs/{run['id']}/artifacts?per_page=100")['artifacts']
    rows=[r for r in rows if r['name']==artifact_name and not r['expired']]
    if len(rows)!=1:raise ValueError('Exact successful-run artifact missing or ambiguous')
    args.output.mkdir(parents=True);outer=args.output/'envelope'
    subprocess.run(['gh','run','download',str(run['id']),'--repo',REPO,'--name',artifact_name,'--dir',str(outer)],check=True,timeout=180)
    root=args.output/'package';extract_verified(outer/'artifact.zip',root);verify_package(root,args.head)
    shutil.copyfile(outer/'artifact.zip',root/'artifact.zip')
    subprocess.run(['python3','scripts/validate_seamless_brand_final_owner_review.py','--package',str(root)],check=True,timeout=120)
    receipt={'schema':'earnalism.exact-head-recovery-baseline.v1','head':args.head,'workflow':WORKFLOW,'run_id':run['id'],'artifact_id':rows[0]['id'],'artifact_digest':rows[0].get('digest'),'inner_archive_sha256':hashlib.sha256((outer/'artifact.zip').read_bytes()).hexdigest(),'classification':'FRESH_EXACT_HEAD_RENDERED_EVIDENCE_NOT_HISTORICAL_PR469_APPROVAL'}
    (root/'baseline-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__=='__main__':main()
