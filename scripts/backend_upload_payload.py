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


def qualify_committed_export(controller, source_sha, export_root):
 """Validate a CLOSED Git-blob export while its normal controller stays clean.

 This is offline admission only. Native archive membership, build provenance,
 config/startup evidence and protected approval remain independent gates.
 """
 from scripts.purchase_guard_source import validate_paired_source, backend_tree, _git, _committed_inventory_helpers
 controller=Path(controller).resolve()
 if _git(controller,'status','--porcelain','--untracked-files=all').strip():
  raise ValueError('Clean exact controller source required for export admission')
 pair=validate_paired_source(controller)
 if not pair['controller_contract_committed']:raise ValueError('Committed source pair required')
 if source_sha!=pair['bootstrap_source_sha']:
  raise ValueError('Export source must be the explicitly paired CLOSED ancestor')
 root=Path(export_root)
 if root.is_symlink() or not root.is_absolute():raise ValueError('Absolute non-symlink export root required')
 root=root.resolve()
 if root==controller or root.is_relative_to(controller):raise ValueError('Export must be isolated from controller source')
 for parent in [root,*root.parents]:
  for name in ['.ignore','.railwayignore']:
   if (parent/name).exists():raise ValueError('Additional ignore language requires native qualification')
 info=root.lstat()
 if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)&0o022:
  raise ValueError('Existing owned non-writable-by-others export required')
 expected=backend_tree(controller,source_sha)
 _build,contract=_committed_inventory_helpers(controller,pair['controller_source_sha'])
 ignore=_git(controller,'ls-tree','-z',source_sha,'--','.gitignore')
 if ignore:
  header,name=ignore.rstrip(b'\0').split(b'\t');mode,kind,oid=header.decode().split()
  if mode not in {'100644','100755'} or kind!='blob':raise ValueError('Regular root ignore input required')
  expected[name.decode()]={'mode':mode,'oid':oid,'bytes':int(_git(controller,'cat-file','-s',oid))}
 actual={}
 for directory,dirs,names in os.walk(root,followlinks=False):
  base=Path(directory)
  for name in dirs+names:
   p=base/name;info=p.lstat()
   if stat.S_ISLNK(info.st_mode):raise ValueError('Export symlinks forbidden')
   if info.st_uid!=os.getuid():raise ValueError('Export owner differs')
   if name in {'.ignore','.railwayignore','.git'}:raise ValueError('Additional ignore or repository boundary')
   if stat.S_ISDIR(info.st_mode):
    if stat.S_IMODE(info.st_mode)&0o022:raise ValueError('Unsafe export directory mode')
    relative=str(p.relative_to(root))
    if not any(key.startswith(relative+'/') for key in expected):raise ValueError('Extra export directory')
   elif not stat.S_ISREG(info.st_mode):raise ValueError('Nonregular export input')
  for name in names:
   p=base/name;key=str(p.relative_to(root));info=p.lstat()
   if key not in expected:raise ValueError('Unreviewed export input')
   required=0o755 if expected[key]['mode']=='100755' else 0o644
   if stat.S_IMODE(info.st_mode)!=required:raise ValueError('Committed export mode differs')
   try:
    with os.fdopen(contract._regular_open(root,key),'rb') as stream:
     opened=os.fstat(stream.fileno())
     if opened.st_uid!=os.getuid() or stat.S_IMODE(opened.st_mode)!=required:
      raise ValueError('Opened export owner/mode differs')
     if opened.st_nlink!=1:raise ValueError('Export hard links forbidden')
     if opened.st_size!=expected[key]['bytes']:raise ValueError('Committed export bytes differ: '+key)
     data=stream.read()
   except OSError as exc:
    raise ValueError('Unsafe export file open') from exc
   oid=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
   if oid!=expected[key]['oid']:raise ValueError('Committed export bytes differ: '+key)
   actual[key]={'path':key,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
 if set(actual)!=set(expected):raise ValueError('Committed export member missing')
 files=sorted(key for key in actual if key.startswith('backend/'))
 supplied=b'\0'.join(x.encode() for x in files)+b'\0'
 ignored=subprocess.run(['git','check-ignore','--no-index','-z','--stdin'],cwd=controller,input=supplied,capture_output=True,check=False)
 if ignored.returncode not in {0,1}:raise ValueError('Native ignore evaluator unavailable')
 excluded=set(x.decode() for x in ignored.stdout.split(b'\0') if x)
 rows=[actual[key] for key in files if key not in excluded]
 included={x['path']:x for x in rows}
 manifest=json.loads((root/'backend/.runtime-source-manifest.json').read_text())
 for row in manifest['files']:
  item=included.get('backend/'+row['path'])
  if item is None or item['bytes']!=row['bytes'] or item['sha256']!=row['sha256']:
   raise ValueError('Required measured runtime input missing or changed: '+row['path'])
 for key in ['backend/Dockerfile','backend/railway.json','backend/requirements-runtime.txt','backend/start_prod.sh','backend/.runtime-source-manifest.json']:
  if key not in included:raise ValueError('Required build/start/config input missing')
 if manifest['expected_sha256']!=pair['closed_runtime_sha256']:raise ValueError('Paired runtime inventory differs')
 if 'COPY --from=builder' not in (root/'backend/Dockerfile').read_text():raise ValueError('Unqualified build layout')
 return {'scope':'OFFLINE_EXACT_COMMITTED_EXPORT_NOT_NATIVE_ARCHIVE_OR_PROVIDER_UPLOAD',
  'cli_version':'5.71.0','source':source_sha,'controller_source':pair['controller_source_sha'],
  'input_path':str(root/'backend'),'archive_prefix':str(root),'path_as_root':False,
  'archive_member_prefix':'backend/','files':rows,'bytes':sum(x['bytes'] for x in rows),
  'excluded_file_count':len(excluded),'runtime_input_count':len(manifest['files']),
  'runtime_expected_sha256':manifest['expected_sha256'],
  'root_ignore_sha256':actual.get('.gitignore',{}).get('sha256'),
  'symlinks':0,'unreviewed_files':0,'provider_writes':0,
  'native_archive_qualification':False}
