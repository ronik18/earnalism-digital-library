"""Offline file-membership admission for fixed Railway5.71 backend path.
No provider/network/archive upload; reject symlinks and extra ignore languages.
"""
from pathlib import Path
import os,subprocess,json,hashlib,stat
def qualify(root):
 root=Path(root).resolve(); backend=root/'backend'
 if not backend.is_dir() or backend.is_symlink():raise ValueError('Backend root unavailable or symlinked')
 # With no .ignore/.railwayignore, no links or nested Git boundaries, Git's
 # native ignore evaluator is equivalent for these file-membership filters.
 for parent in [root,*root.parents]:
  for name in ['.ignore','.railwayignore']:
   if (parent/name).exists():raise ValueError('Additional ignore language requires native qualification')
 files=[]
 for directory,dirs,names in os.walk(backend,followlinks=False):
  base=Path(directory)
  for name in dirs+names:
   p=base/name
   if p.is_symlink():raise ValueError('Upload follows links; no symlinks admitted')
   if name in {'.ignore','.railwayignore','.git'}:raise ValueError('Nested ignore or repository boundary')
  for name in names:
   p=base/name
   if not stat.S_ISREG(p.stat().st_mode):raise ValueError('Nonregular upload input')
   files.append(str(p.relative_to(root)))
 supplied=b'\0'.join(x.encode() for x in files)+b'\0'
 ignored=subprocess.run(['git','check-ignore','--no-index','-z','--stdin'],cwd=root,input=supplied,capture_output=True,check=False)
 if ignored.returncode not in {0,1}:raise ValueError('Native ignore evaluator unavailable')
 excluded=set(x.decode() for x in ignored.stdout.split(b'\0') if x)
 indexed=subprocess.check_output(['git','ls-files','-z','--','backend'],cwd=root).split(b'\0');tracked={x.decode() for x in indexed if x}
 included=sorted(set(files)-excluded)
 if any(x not in tracked for x in included):raise ValueError('Unreviewed upload input')
 rows=[]
 for name in included:
  b=(root/name).read_bytes();rows.append({'path':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 actual={r['path']:r for r in rows};manifest=json.loads((backend/'.runtime-source-manifest.json').read_text())
 for r in manifest['files']:
  x=actual.get('backend/'+r['path'])
  if x is None or x['sha256']!=r['sha256'] or x['bytes']!=r['bytes']:raise ValueError('Required measured runtime input missing or changed: '+r['path'])
 for name in ['backend/Dockerfile','backend/railway.json','backend/requirements-runtime.txt','backend/start_prod.sh','backend/.runtime-source-manifest.json']:
  if name not in actual:raise ValueError('Required build/start/config input missing')
 if 'COPY --from=builder' not in (backend/'Dockerfile').read_text():raise ValueError('Unqualified build layout')
 return {'scope':'OFFLINE_CLI_EQUIVALENT_FILE_MEMBERSHIP_NOT_PROVIDER_UPLOAD','cli_version':'5.71.0','source':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'input_path':str(backend),'archive_prefix':str(root),'path_as_root':False,'archive_member_prefix':'backend/','files':rows,'bytes':sum(x['bytes'] for x in rows),'excluded_file_count':len(excluded),'runtime_input_count':len(manifest['files']),'runtime_expected_sha256':manifest['expected_sha256'],'symlinks':0,'unreviewed_files':0,'provider_writes':0}
