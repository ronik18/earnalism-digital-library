from pathlib import Path
import tempfile,subprocess,unittest,json,hashlib,sys
from scripts.backend_upload_payload import qualify
class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.r=Path(self.t.name);b=self.r/'backend';b.mkdir()
  for n in ['Dockerfile','railway.json','requirements-runtime.txt','start_prod.sh']:(b/n).write_text('COPY --from=builder /x /x\n' if n=='Dockerfile' else 'fixture\n')
  rows=[{'path':p.name,'bytes':len(p.read_bytes()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in b.iterdir()];(b/'.runtime-source-manifest.json').write_text(json.dumps({'files':rows,'expected_sha256':'a'*64}))
  (self.r/'.gitignore').write_text('__pycache__/\n.env\n')
  self.git('init','-q');self.git('add','.');self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture')
 def git(self,*a):return subprocess.run(['git',*a],cwd=self.r,capture_output=True,check=True)
 def test_complete_and_hidden_manifest_included(self):
  d=qualify(self.r);self.assertIn('backend/.runtime-source-manifest.json',[r['path'] for r in d['files']]);self.assertEqual(d['archive_member_prefix'],'backend/');self.assertFalse(d['path_as_root'])
 def test_ignored_caches_and_environment_not_read(self):
  (self.r/'backend/.env').write_text('synthetic-secret');c=self.r/'backend/__pycache__';c.mkdir();(c/'inert.pyc').write_bytes(b'cache');d=qualify(self.r);self.assertEqual(d['excluded_file_count'],2);self.assertNotIn('synthetic-secret',json.dumps(d))
 def test_unreviewed_file_denied(self):
  (self.r/'backend/unreviewed.py').write_text('inert')
  with self.assertRaisesRegex(ValueError,'Unreviewed'):qualify(self.r)
 def test_symlink_denied_even_when_target_exists(self):
  (self.r/'backend/link').symlink_to(self.r/'backend/start_prod.sh')
  with self.assertRaisesRegex(ValueError,'symlinks'):qualify(self.r)
 def test_missing_runtime_file_denied(self):
  (self.r/'backend/start_prod.sh').unlink()
  with self.assertRaisesRegex(ValueError,'Required measured'):qualify(self.r)
 def test_changed_runtime_file_denied(self):
  (self.r/'backend/start_prod.sh').write_text('changed')
  with self.assertRaisesRegex(ValueError,'Required measured'):qualify(self.r)
 def test_ignored_required_file_denied(self):
  with (self.r/'.gitignore').open('a') as f:f.write('backend/start_prod.sh\n')
  with self.assertRaisesRegex(ValueError,'Required measured'):qualify(self.r)
 def test_additional_ignore_language_denied(self):
  for where in [self.r,self.r/'backend']:
   for name in ['.ignore','.railwayignore']:
    with self.subTest(where=str(where),name=name):
     p=where/name;p.write_text('*.py');
     with self.assertRaises(ValueError):qualify(self.r)
     p.unlink()
if __name__=='__main__':unittest.main()
