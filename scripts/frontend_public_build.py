"""Build exact F with an operator-reviewed public projection, never a secret pull."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from scripts.verify_isolated_seo_build import exact_clean_source

F = '229df7f8b2cfb49a7f46215be3979608c39f7c33'
PUBLIC_REFERENCE = Path(__file__).with_name('frontend_public_build_inputs.json')
PUBLIC_KEYS = {'REACT_APP_BACKEND_URL', 'REACT_APP_ENABLE_LAUNCH_ANALYTICS', 'REACT_APP_GOOGLE_CLIENT_ID'}
SETTINGS = {'orgId':'team_HAGNRSEiW5MZXY2AhV0cQvE0','projectId':'prj_kxPN55TOJ23lDgoXIXrvqHtzy607',
 'settings':{'framework':'create-react-app','rootDirectory':'frontend','installCommand':'npm install --legacy-peer-deps',
 'buildCommand':'npm run build','outputDirectory':'build','nodeVersion':'24.x'}}

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def public_inputs(approval, controller):
    if approval.get('controller_sha') != controller or approval.get('frontend_sha') != F:
        raise ValueError('Public input source/controller binding missing')
    p=approval.get('public_build_inputs',{})
    if set(p) != {'all_values_public','operator','env','excluded_client_inputs'} or p['all_values_public'] is not True or not isinstance(p['operator'],str) or not p['operator'].strip():
        raise ValueError('Reviewed public input projection required')
    env=p['env']
    if not isinstance(env,dict) or set(env)!=PUBLIC_KEYS or any(not isinstance(v,str) for v in env.values()):
        raise ValueError('Only the three reviewed public inputs are allowed')
    if p['excluded_client_inputs'] != ['REACT_APP_API_URL']:
        raise ValueError('Secret-labelled fallback must be excluded without reading it')
    if env['REACT_APP_BACKEND_URL']!='https://api.theearnalism.com' or env['REACT_APP_ENABLE_LAUNCH_ANALYTICS']!='true':
        raise ValueError('Public backend/analytics differ from reviewed production facts')
    if not re.fullmatch(r'[A-Za-z0-9_-]+\.apps\.googleusercontent\.com',env['REACT_APP_GOOGLE_CLIENT_ID']):
        raise ValueError('Reviewed public Google client ID required')
    if env != json.loads(PUBLIC_REFERENCE.read_text()):
        raise ValueError('Public projection differs from reviewed versioned inputs')
    return dict(env)

def build_environment(private, projection, generated):
    private=Path(private)
    for name in ('user.npmrc','global.npmrc'):(private/name).write_text('')
    return {'PATH':os.environ['PATH'],'HOME':str(private),'XDG_CONFIG_HOME':str(private/'.config'),
      'XDG_DATA_HOME':str(private/'.local/share'),'TMPDIR':str(private),'CI':'true',
      'NPM_CONFIG_USERCONFIG':str(private/'user.npmrc'),'NPM_CONFIG_GLOBALCONFIG':str(private/'global.npmrc'),
      'NPM_CONFIG_CACHE':str(private/'npm-cache'),'NPM_CONFIG_SAVE':'false',
      'VERCEL_TELEMETRY_DISABLED':'1','DO_NOT_TRACK':'1','SEO_ASSETS_OUTPUT_DIR':str(generated),**projection}

def output_identity(root):
    output=root/'.vercel/output'
    if not output.is_dir() or output.is_symlink():raise ValueError('Built output missing')
    rows=[]
    for p in sorted(output.rglob('*')):
        if p.is_symlink() and not p.resolve().is_relative_to(root):raise ValueError('External output link')
        if p.is_file():
            b=p.read_bytes();rows.append({'path':str(p.relative_to(root)),'size':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':stat.S_IMODE(p.stat().st_mode)})
    if not rows:raise ValueError('Empty output')
    return rows

def run(root, generated, receipt, approval, controller, verify_only=False):
    root=Path(root).resolve();receipt=Path(receipt)
    exact_clean_source(root,F)
    projection=public_inputs(approval,controller)
    # Exact F has no tracked dotenv input. Never read inherited .env files.
    tracked=subprocess.check_output(['git','-C',str(root),'ls-tree','-r','--name-only',F,'frontend'],text=True).splitlines()
    if any(Path(p).name.startswith('.env') for p in tracked):raise ValueError('Unreviewed tracked dotenv source')
    for folder in (root/'frontend',root/'.vercel',root/'frontend/.vercel'):
        for p in folder.glob('.env*'):
            if p.name!='.env.production.local' or p.parent not in (root/'.vercel',root/'frontend/.vercel') or p.is_symlink() or p.stat().st_size:
                raise ValueError('Unreviewed environment file present; do not read it')
    if verify_only:
        before=json.loads(receipt.read_text())
        expected={'controller_sha':controller,'frontend_sha':F,'public_inputs_sha256':digest(projection),
                  'settings':SETTINGS,'output':output_identity(root)}
        if any(before.get(k)!=v for k,v in expected.items()):raise ValueError('Public input or built output changed before deployment')
        return before
    if receipt.exists() or (root/'.vercel/output').exists():raise ValueError('Do not reuse existing build/receipt')
    for folder in (root/'.vercel',root/'frontend/.vercel'):
        folder.mkdir(exist_ok=True)
        p=folder/'.env.production.local'
        if p.exists():raise ValueError('Existing environment file must not be read or overwritten')
        p.write_text('')
    (root/'.vercel/project.json').write_text(json.dumps(SETTINGS,indent=2)+'\n')
    cli=shutil.which('vercel')
    if not cli:raise ValueError('Pinned CLI unavailable')
    with tempfile.TemporaryDirectory(prefix='reader-public-build-') as private:
        env=build_environment(private,projection,Path(generated).resolve())
        # This is the existing production CLI build. No pull, login, project change or retry.
        subprocess.run(['node',str(Path(cli).resolve()),'build','--prod','--yes'],cwd=root,env=env,check=True,timeout=900)
    exact_clean_source(root,F)
    result={'status':'PASS_PUBLIC_INPUT_BUILD_BINDING','controller_sha':controller,'frontend_sha':F,
      'public_inputs_sha256':digest(projection),'public_inputs':projection,'settings':SETTINGS,'output':output_identity(root),
      'secret_values_read':False,'production_applicability':'Requires independent exact projected build qualification; empty-profile capture is not substituted.'}
    receipt.write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--generated-root',type=Path);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    try:
        result=run(a.source_root,a.generated_root,a.receipt,json.loads(os.environ.get('RELEASE_APPROVAL_JSON','')),os.environ['CONTROLLER_SHA'],a.verify_only)
        print('PUBLIC_INPUT_BUILD_BINDING=PASS')
    except Exception:
        raise SystemExit('PUBLIC_INPUT_BUILD_BINDING=FAIL; no publication permitted') from None
