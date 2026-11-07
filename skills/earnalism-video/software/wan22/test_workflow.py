"""Control-plane and real-media import checks; no model, network or CUDA execution."""
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch
import hashlib,json,subprocess,tempfile,time,unittest,zipfile
from . import worker as w
from .build_colab import build

class Workflow(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.p=Path(self.temp.name);art=self.p/'art';art.mkdir()
  for n in ['rama-portrait.png','living-portrait.png']:(art/n).write_bytes(b'test-only-source-'+n.encode())
  self.notebook=build(self.p/'bundle',art);self.bundle=self.notebook.parent;self.job=self.bundle/'job.json';self.root=self.p/'runtime'
  w.unpack_inputs(self.bundle/'wan22-inputs.zip',self.root,w.sha(self.bundle/'wan22-inputs.zip'))
 def session(self):return w.begin(self.root,True,0)
 def test_run_all_inert_without_colab_or_model(self):
  ns={}
  with redirect_stdout(StringIO()) as stream:
   for c in json.loads(self.notebook.read_text())['cells']:
    if c['cell_type']=='code':exec(compile(''.join(c['source']),'notebook','exec'),ns)
  self.assertIn('WAN_DISABLED',stream.getvalue());self.assertNotIn('ROOT',ns)
 def test_enabled_without_free_evidence_stops_before_write_or_import(self):
  nb=json.loads(self.notebook.read_text());ns={};exec(''.join(nb['cells'][1]['source']),ns);ns['RUN_WAN']=True
  with self.assertRaisesRegex(RuntimeError,'Free CUDA'):exec(''.join(nb['cells'][2]['source']),ns)
  self.assertNotIn('ROOT',ns)
 def test_immutable_session_deadline_and_job(self):
  a=self.session();self.assertEqual(a['deadline'],self.session()['deadline'])
  a['deadline']=time.time()-1;w.write(self.root/'session.json',a)
  with self.assertRaisesRegex(RuntimeError,'deadline expired'):self.session()
 def test_metered_authority_requires_bounded_rate_and_original_start(self):
  with self.assertRaises(RuntimeError):w.begin(self.root,False,2)
  with self.assertRaises(RuntimeError):w.begin(self.root,False,12,5,time.time()-5)
  with self.assertRaises(RuntimeError):w.begin(self.root,False,2,5)
  started=time.time()-30;state=w.begin(self.root,False,2,5,started)
  self.assertEqual(state['deadline'],started+1800);self.assertGreater(w.remaining(self.root),0)
 def test_t4_stops_before_torch_or_model_download(self):
  self.session()
  fake=subprocess.CompletedProcess([],0,'Tesla T4, 15360\n','')
  # Keep real job/session reads and mock only the machine-specific file.
  original=Path.read_text
  with patch.object(w.subprocess,'run',return_value=fake) as run,patch.object(Path,'read_text',lambda p,*a,**k:'MemTotal: 64000000 kB\n' if str(p)=='/proc/meminfo' else original(p,*a,**k)):
   with self.assertRaisesRegex(RuntimeError,'Insufficient'):w.preflight(self.root)
   self.assertEqual(run.call_count,1)
  self.assertFalse((self.root/'model').exists())
 def test_failed_start_is_reserved_and_cannot_repeat(self):
  self.session();w.write(self.root/'setup.json',{'state':'test-only'})
  with patch.object(w,'command',side_effect=subprocess.TimeoutExpired('inference',1)):
   with self.assertRaises(subprocess.TimeoutExpired):w.generate(self.root,'homecoming')
  rows=json.loads((self.root/'attempts.json').read_text());self.assertEqual(rows[0]['status'],'FAILED_NO_AUTOMATIC_RETRY')
  self.assertAlmostEqual(rows[0]['reserved_seconds'],121/24)
  with self.assertRaisesRegex(RuntimeError,'already attempted'):w.generate(self.root,'homecoming')
  self.assertTrue((self.root/'wan22-export.zip').exists())
 def test_rejects_oversized_or_changed_job(self):
  job=json.loads(self.job.read_text());job['max_attempts']=3
  with self.assertRaises(ValueError):w.validate(job)
  job=json.loads(self.job.read_text());job['model_revision']='main'
  with self.assertRaises(ValueError):w.validate(job)
 def test_export_tamper_and_traversal_rejected_without_writes(self):
  self.session();archive=w.export(self.root);bad=self.p/'bad.zip'
  with zipfile.ZipFile(archive) as z,zipfile.ZipFile(bad,'w') as b:
   for n in z.namelist():b.writestr(n,z.read(n))
   b.writestr('../escape',b'bad')
  dest=self.p/'import'
  with self.assertRaises(ValueError):w.import_export(bad,dest,w.sha(bad),self.job)
  self.assertFalse(dest.exists());self.assertFalse((self.p/'escape').exists())
  with self.assertRaisesRegex(ValueError,'archive hash'):w.import_export(archive,dest,'0'*64,self.job)
 def test_real_silent_media_import_stays_unaccepted(self):
  self.session();out=self.root/'outputs';out.mkdir()
  clip=out/'homecoming.mp4'
  subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=704x1280:r=24','-frames:v','121','-an','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p',str(clip)],check=True)
  job=json.loads(self.job.read_text());scene=job['scenes'][0]
  w.write(self.root/'attempts.json',[{'scene':'homecoming','status':'TECHNICAL_PASS_REVIEW_PENDING','sha256':w.sha(clip),'source_sha256':scene['image_sha256'],'reserved_seconds':121/24}])
  archive=w.export(self.root);dest=self.p/'import';rows=w.import_export(archive,dest,w.sha(archive),self.job)
  self.assertEqual(len(rows),1);self.assertFalse(rows[0]['motion_accepted']);self.assertFalse(json.loads((dest/'import-receipt.json').read_text())['publication_approved'])
  with self.assertRaises(FileExistsError):w.import_export(archive,dest,w.sha(archive),self.job)

if __name__=='__main__':unittest.main()
