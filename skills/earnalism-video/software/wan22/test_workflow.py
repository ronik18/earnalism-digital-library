"""Control-plane and real-media import checks; no model, network or CUDA execution."""
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch,Mock
import hashlib,json,subprocess,tempfile,time,unittest,zipfile
from . import worker as w
from .build_colab import build

class Workflow(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.p=Path(self.temp.name);art=self.p/'art';art.mkdir()
  for n in ['rama-portrait.png','living-portrait.png']:(art/n).write_bytes(b'test-only-source-'+n.encode())
  self.notebook=build(self.p/'bundle',art);self.bundle=self.notebook.parent;self.job=self.bundle/'job.json';self.root=self.p/'runtime'
  w.unpack_inputs(self.bundle/'wan22-inputs.zip',self.root,w.sha(self.bundle/'wan22-inputs.zip'))
 def test_new_scene_sources_are_bound_and_not_old_prompts(self):
  art=self.p/'new-art';art.mkdir()
  for n in ['greeting.png','response.png']:(art/n).write_bytes(('new-'+n).encode())
  spec={'homecoming':{'image':'greeting.png','prompt':'One clear joined-palms greeting with complete hands'},'sweets':{'image':'response.png','prompt':'Girl already supports the tray and gives one appreciative nod'}}
  target=build(self.p/'fresh',art,'l4-landscape-v1','diwali-v12-test',None,{'prior_run':'preserved'},spec)
  job=json.loads((target.parent/'job.json').read_text())
  for scene in job['scenes']:
   self.assertEqual(scene['prompt'],spec[scene['id']]['prompt'])
   self.assertEqual(scene['image_sha256'],w.sha(art/scene['image']))
  runtime=self.p/'fresh-runtime';w.unpack_inputs(target.parent/'wan22-inputs.zip',runtime,w.sha(target.parent/'wan22-inputs.zip'))
  self.assertEqual(w.open_job(runtime)['run_id'],'diwali-v12-test')
  self.assertIn('RUN_WAN = False',''.join(json.loads(target.read_text())['cells'][1]['source']))
 def test_scene_override_cannot_escape_or_relabel(self):
  for spec in [{'other':{'image':'x','prompt':'some sufficiently long prompt'}},{'homecoming':{'image':'../secret','prompt':'some sufficiently long prompt'}}]:
   with self.assertRaises(ValueError):build(self.p/'bad',self.p/'art','l4-landscape-v1','new-run',None,{'prior':'retained'},spec)
  with self.assertRaises(ValueError):build(self.p/'bad',self.p/'art',scene_overrides={'homecoming':{'image':'x','prompt':'some sufficiently long prompt'}})
 def test_scene_expression_controls_are_bound_without_replacing_baseline(self):
  spec={'homecoming':{'image':'rama-portrait.png','prompt':'One small bow and a stable child-facing return','negative_prompt':'winking, prolonged asymmetric blink, camera-facing gaze'}}
  nb=build(self.p/'expression',self.p/'art','landscape-detail-pilot-v1','diwali-v16-test',['homecoming'],{'prior_v15':'preserved'},spec)
  runtime=self.p/'expression-runtime';w.unpack_inputs(nb.parent/'wan22-inputs.zip',runtime,w.sha(nb.parent/'wan22-inputs.zip'))
  scene=w.open_job(runtime)['scenes'][0]
  self.assertIn('fused hands',w.scene_negative_prompt(scene));self.assertIn('winking',w.scene_negative_prompt(scene))
  self.assertEqual(scene['negative_prompt'],spec['homecoming']['negative_prompt'])
  job=json.loads((nb.parent/'job.json').read_text());job['scenes'][0]['negative_prompt']=[]
  with self.assertRaises(ValueError):w.validate(job)
  job['scenes'][0]['negative_prompt']='x'*1001
  with self.assertRaises(ValueError):w.validate(job)
 def test_unenforced_end_image_cannot_masquerade_as_5b_conditioning(self):
  for key in ['last_image','end_image']:
   job=json.loads(self.job.read_text());job['scenes'][0][key]='rama-portrait.png'
   with self.assertRaisesRegex(ValueError,'does not enforce'):w.validate(job)
 def test_mixed_reviewed_framing_keeps_one_budget_and_bound_sources(self):
  art=self.p/'mixed-art';art.mkdir()
  for n in ['welcome.png','family.png']:(art/n).write_bytes(('source-'+n).encode())
  spec={'homecoming':{'image':'welcome.png','prompt':'Held namaste and one small respectful bow'},'sweets':{'image':'family.png','prompt':'Stable supported platter with one appreciative nod','frame_profile':'l4-balanced-v2'}}
  target=build(self.p/'mixed',art,'l4-landscape-v1','diwali-v13-mixed',None,{'prior':'preserved'},spec)
  job=json.loads((target.parent/'job.json').read_text());self.assertEqual([(x['width'],x['height']) for x in job['scenes']],[(896,512),(512,896)])
  self.assertEqual((job['max_attempts'],job['wall_seconds'],job['max_output_seconds']),(2,1800,11))
  runtime=self.p/'mixed-runtime';w.unpack_inputs(target.parent/'wan22-inputs.zip',runtime,w.sha(target.parent/'wan22-inputs.zip'));w.open_job(runtime)
  job['scenes'][1]['height']=1920
  with self.assertRaises(ValueError):w.validate(job)
 def test_mixed_framing_rejects_inference_drift_and_unknown_profiles(self):
  job=json.loads(self.job.read_text());job['scenes'][1]['frame_profile']='l4-balanced-v2'
  with self.assertRaises(ValueError):w.validate(job)
  job['scenes'][1]['frame_profile']='invented'
  with self.assertRaises(ValueError):w.validate(job)
  with self.assertRaises(ValueError):build(self.p/'bad-list',self.p/'art',scene_overrides=[])
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
 def test_optimized_retry_isolated_and_rejects_unbound_settings(self):
  nb=build(self.p/'optimized',self.p/'art','l4-balanced-v2')
  job=json.loads((nb.parent/'job.json').read_text())
  self.assertNotEqual(job['run_id'],json.loads(self.job.read_text())['run_id'])
  self.assertEqual((job['scenes'][0]['width'],job['scenes'][0]['height'],job['inference_steps']),(512,896,24))
  self.assertIn('/content/earnalism-wan22-diwali-pilot-v2',nb.read_text())
  self.assertTrue(job['prior_attempt_evidence'])
  job['inference_steps']=50
  with self.assertRaises(ValueError):w.validate(job)
 def test_selective_retry_preserves_prior_success_and_has_one_start(self):
  prior={'run_id':'diwali-wan22-pilot-v2','homecoming':'completed','sweets':'failed'}
  nb=build(self.p/'retry',self.p/'art','l4-balanced-v2','diwali-wan22-pilot-v3',['sweets'],prior)
  job=json.loads((nb.parent/'job.json').read_text());self.assertEqual(job['max_attempts'],1)
  self.assertEqual([s['id'] for s in job['scenes']],['sweets']);self.assertEqual(job['prior_attempt_evidence'],prior)
  dest=self.p/'retry-runtime';w.unpack_inputs(nb.parent/'wan22-inputs.zip',dest,w.sha(nb.parent/'wan22-inputs.zip'))
  self.assertFalse((dest/'inputs/rama-portrait.png').exists());self.assertIn('SCENE_NOT_IN_THIS_JOB',nb.read_text())
 def test_landscape_profile_preserves_budget_and_rejects_arbitrary_shape(self):
  (self.p/'art/living-landscape-v10.png').write_bytes(b'test-only-wide-art')
  nb=build(self.p/'wide',self.p/'art','l4-landscape-v1','diwali-wan22-wide-v10',['sweets'],{'prior_completed':'retained'})
  job=json.loads((nb.parent/'job.json').read_text());scene=job['scenes'][0]
  self.assertEqual((scene['width'],scene['height'],job['max_attempts']),(896,512,1))
  self.assertEqual(scene['image'],'living-landscape-v10.png');self.assertEqual(job['wall_seconds'],1800)
  scene['width']=1920
  with self.assertRaises(ValueError):w.validate(job)
 def test_metered_authority_requires_bounded_rate_and_original_start(self):
  with self.assertRaises(RuntimeError):w.begin(self.root,False,2)
  with self.assertRaises(RuntimeError):w.begin(self.root,False,12,5,time.time()-5)
  with self.assertRaises(RuntimeError):w.begin(self.root,False,2,5)
  started=time.time()-30;state=w.begin(self.root,False,2,5,started)
  self.assertEqual(state['deadline'],started+1800);self.assertGreater(w.remaining(self.root),0)
 def detail_job(self):
  nb=build(self.p/'detail',self.p/'art','landscape-detail-pilot-v1','diwali-detail-test',['homecoming'],{'prior_v14':'preserved'})
  return nb,json.loads((nb.parent/'job.json').read_text())
 def test_detail_pilot_binds_one_source_and_preserves_inert_budget(self):
  nb,job=self.detail_job();scene=job['scenes'][0]
  self.assertEqual((scene['id'],scene['width'],scene['height']),('homecoming',1280,704))
  self.assertEqual((job['max_attempts'],job['wall_seconds'],job['max_output_seconds']),(1,1800,6))
  self.assertTrue(job['experimental_profile']);self.assertIn('RUN_WAN = False',nb.read_text())
  with zipfile.ZipFile(nb.parent/'wan22-inputs.zip') as z:self.assertEqual(set(z.namelist()),{'job.json','inputs/rama-portrait.png'})
  with self.assertRaises(ValueError):build(self.p/'unbound-detail',self.p/'art','landscape-detail-pilot-v1')
  job['scenes'].append(dict(scene,id='sweets'));job['max_attempts']=2
  with self.assertRaisesRegex(ValueError,'one homecoming'):w.validate(job)
  mixed=json.loads(self.job.read_text());mixed['scenes'][0]['frame_profile']='landscape-detail-pilot-v1'
  with self.assertRaisesRegex(ValueError,'hidden inside a mixed'):w.validate(mixed)
 def test_detail_forecast_reserves_more_decode_time_without_extending_deadline(self):
  nb,job=self.detail_job();runtime=self.p/'detail-runtime';w.unpack_inputs(nb.parent/'wan22-inputs.zip',runtime,w.sha(nb.parent/'wan22-inputs.zip'))
  state=w.begin(runtime,True,0)
  with patch.object(w.time,'monotonic',side_effect=[220,231,242]),patch.object(w,'remaining',return_value=500):
   callback=w.step_budget_guard(runtime,24);payload={'latents':'test'}
   for step in range(2):callback(None,step,None,payload)
   with self.assertRaisesRegex(RuntimeError,'cannot fit original deadline'):callback(None,2,None,payload)
  self.assertEqual(json.loads((runtime/'session.json').read_text())['deadline'],state['deadline'])
 def test_generated_detail_cell_checks_headroom_before_spending_start(self):
  nb,_=self.detail_job();cell=''.join(json.loads(nb.read_text())['cells'][8]['source']);fake=Mock();fake.remaining.return_value=1199
  ns={'RUN_WAN':True,'PREFLIGHT_OK':True,'GENERATE_HOMECOMING':True,'worker':fake,'ROOT':self.root}
  with self.assertRaisesRegex(RuntimeError,'Insufficient original deadline'):exec(cell,ns)
  fake.generate.assert_not_called()
  fake.remaining.return_value=1200;(self.root/'attempts.json').write_text('[]')
  with redirect_stdout(StringIO()):exec(cell,ns)
  fake.generate.assert_called_once_with(self.root,'homecoming')
 def test_real_detail_media_import_remains_unqualified(self):
  nb,job=self.detail_job();runtime=self.p/'detail-runtime';w.unpack_inputs(nb.parent/'wan22-inputs.zip',runtime,w.sha(nb.parent/'wan22-inputs.zip'));w.begin(runtime,True,0)
  out=runtime/'outputs';out.mkdir();clip=out/'homecoming.mp4'
  subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=1280x704:r=24','-frames:v','121','-an','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p',str(clip)],check=True)
  w.write(runtime/'attempts.json',[{'scene':'homecoming','status':'TECHNICAL_PASS_REVIEW_PENDING','sha256':w.sha(clip),'source_sha256':job['scenes'][0]['image_sha256'],'reserved_seconds':121/24}])
  archive=w.export(runtime);rows=w.import_export(archive,self.p/'detail-import',w.sha(archive),nb.parent/'job.json')
  self.assertEqual(len(rows),1);self.assertFalse(rows[0]['motion_accepted'])
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
 def test_measured_slow_inference_stops_without_extending_session(self):
  state=self.session();original_deadline=state['deadline']
  with patch.object(w.time,'monotonic',side_effect=[220,252,284]),patch.object(w,'remaining',return_value=600):
   callback=w.step_budget_guard(self.root)
   payload={'latents':'test'}
   self.assertIs(callback(None,0,None,payload),payload)
   self.assertIs(callback(None,1,None,payload),payload)
   with self.assertRaisesRegex(RuntimeError,'cannot fit original deadline'):callback(None,2,None,payload)
  self.assertEqual(json.loads((self.root/'session.json').read_text())['deadline'],original_deadline)
 def test_long_warmup_is_not_multiplied_by_remaining_steps(self):
  self.session()
  with patch.object(w.time,'monotonic',side_effect=[220,231,242]),patch.object(w,'remaining',return_value=600):
   callback=w.step_budget_guard(self.root,24)
   payload={'latents':'test'}
   for step in range(3):self.assertIs(callback(None,step,None,payload),payload)
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
 def test_frame_splice_preserves_length_and_exact_color_boundaries(self):
  from .splice import splice
  base=self.p/'base.mp4';patch=self.p/'patch.mp4';out=self.p/'spliced.mp4'
  for path,color,frames in [(base,'blue',30),(patch,'red',6)]:
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'color=c={color}:s=64x64:r=30','-frames:v',str(frames),'-an','-c:v','libx264','-pix_fmt','yuv420p',str(path)],check=True)
  receipt=splice(base,[{'start':5,'end':11,'file':patch}],out);self.assertEqual(receipt['frame_count'],30)
  raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(out),'-f','rawvideo','-pix_fmt','rgb24','-'])
  for frame,red in [(4,False),(5,True),(10,True),(11,False)]:
   pixel=raw[frame*64*64*3:frame*64*64*3+3];self.assertEqual(pixel[0]>pixel[2],red)
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
