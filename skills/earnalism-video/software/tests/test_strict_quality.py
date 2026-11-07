import unittest,tempfile,pathlib,json,sys,datetime,copy
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import strict_quality as q
class StrictQualityTests(unittest.TestCase):
 def fixture(self,p,ending_seconds=None):
  ep={'scenes':[{'id':'one','text':'The Moon reflects sunlight.','source_ids':['nasa']}],'sources':[{'id':'nasa','url':'https://science.nasa.gov/moon/moon-phases/'}]}
  props={'duration':2,'scenes':[{'id':'one','start':0,'end':2,'anchors':[{'time':1}]}]}
  if ending_seconds is not None:props['intro']={'seconds':ending_seconds,'placement':'end'}
  for n,v in [('episode.json',ep),('props.json',props)]:(p/n).write_text(json.dumps(v))
  for n in ['landscape.mp4','portrait-captioned.mp4']:(p/n).write_bytes(b'ISOLATED TEST FIXTURE NOT REAL VIDEO')
  (p/'delivery-manifest.json').write_text(json.dumps({n:q.sha(p/n) for n in ['episode.json','props.json','landscape.mp4','portrait-captioned.mp4']}))
  (p/'source.txt').write_text('Synthetic unit-test evidence, never a production approval');(p/'frame.png').write_bytes(b'\x89PNG\r\n\x1a\nTEST ONLY')
  ref=[{'path':'source.txt','sha256':q.sha(p/'source.txt')}];frame=[{'path':'frame.png','sha256':q.sha(p/'frame.png')}]
  r=q.initialize(p)
  for section in ['factual','graphical']:r[section].update(decision='PASS',reviewer='ISOLATED UNIT TEST ONLY',human_confirmed=True,reviewed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
  r['factual']['sources']['nasa']={'verdict':'PASS','url':ep['sources'][0]['url'],'retrieved_at':'2026-10-28','primary_or_authoritative':True,'evidence':ref}
  for row in r['factual']['claims'].values():row.update(verdict='PASS',source_ids=['nasa'],reason='TEST ONLY',evidence=ref)
  r['factual']['visual_claims']['one']={'coverage_confirmed':True,'assertions':[{'verdict':'PASS','text':'TEST diagram assertion','source_ids':['nasa'],'reason':'TEST ONLY','evidence':ref}]}
  for s in q.plan(p)['frames']:
   r['graphical']['frames'][s['id']].update(verdict='PASS',media_sha256=q.sha(p/('landscape.mp4' if s['format']=='Landscape' else 'portrait-captioned.mp4')),evidence=frame)
  for section in ['checks','players']:
   for row in r['graphical'][section].values():row.update(verdict='PASS',evidence=ref)
  for fmt,row in r['graphical']['complete_playback'].items():row.update(verdict='PASS',device='TEST FIXTURE',watched_seconds=q.plan(p)['expected_seconds'],complete_uninterrupted_view=True,media_sha256=q.sha(p/('landscape.mp4' if fmt=='Landscape' else 'portrait-captioned.mp4')),evidence=ref)
  self.save(p,r);return r
 def save(self,p,r):(p/q.NAME).write_text(json.dumps(r))
 def test_complete_fixture_passes_but_is_not_publication_approval(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p);result=q.validate(p);self.assertFalse(result['publication_approval']);self.assertEqual(result['frame_reviews'],12)
 def test_missing_and_pending_reviews_fail_closed(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)
   with self.assertRaisesRegex(ValueError,'mandatory|Mandatory'):q.validate(p)
   self.fixture(p);q.reset(p)
   with self.assertRaisesRegex(ValueError,'human review'):q.validate(p)
 def test_omitted_claim_or_transition_or_format_fails(self):
  for section in ['claims','frames','players','complete_playback']:
   with self.subTest(section=section),tempfile.TemporaryDirectory() as d:
    p=pathlib.Path(d);r=self.fixture(p);parent=r['factual'] if section=='claims' else r['graphical'];parent[section].pop(next(iter(parent[section])));self.save(p,r)
    with self.assertRaises(ValueError):q.validate(p)
 def test_changed_evidence_and_stale_manifest_fail(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);r=self.fixture(p);(p/'frame.png').write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'evidence'):q.validate(p)
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);r=self.fixture(p);(p/'landscape.mp4').write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'Delivery changed'):q.validate(p)
 def test_unresolved_fact_unreviewed_source_and_visual_inventory_block(self):
  for change in ['issue','source','inventory','frame_time','device','human','partial_playback']:
   with self.subTest(change=change),tempfile.TemporaryDirectory() as d:
    p=pathlib.Path(d);r=self.fixture(p)
    if change=='issue':r['factual']['unresolved']=['contradiction']
    elif change=='source':r['factual']['sources']['nasa']['primary_or_authoritative']=False
    elif change=='inventory':r['factual']['visual_claims']['one']['assertions']=[]
    elif change=='frame_time':next(iter(r['graphical']['frames'].values()))['seconds']=999
    elif change=='device':r['graphical']['complete_playback']['Portrait']['device']=''
    elif change=='human':r['graphical']['human_confirmed']=False
    elif change=='partial_playback':r['graphical']['complete_playback']['Portrait']['watched_seconds']=1
    self.save(p,r)
    with self.assertRaises(ValueError):q.validate(p)
 def test_storyboard_edit_invalidates_binding_even_after_manifest_rebound(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);r=self.fixture(p);props=q.load(p/'props.json');props['scenes'][0]['anchors'][0]['time']=.7;(p/'props.json').write_text(json.dumps(props));manifest=q.load(p/'delivery-manifest.json');manifest['props.json']=q.sha(p/'props.json');(p/'delivery-manifest.json').write_text(json.dumps(manifest));r['delivery_manifest_sha256']=q.sha(p/'delivery-manifest.json');self.save(p,r)
   with self.assertRaisesRegex(ValueError,'Stale'):q.validate(p)
 def test_reset_archives_old_review_without_reusing_approval(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);r=self.fixture(p);old=q.sha(p/q.NAME);new=q.reset(p);self.assertEqual(new['factual']['decision'],'PENDING');self.assertTrue((p/'logs/strict-quality-history'/(old+'.json')).exists())
 def test_outside_evidence_path_cannot_be_used(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p)
   with self.assertRaisesRegex(ValueError,'Unsafe'):q.evidence(p,[{'path':'../secret','sha256':'x'}])

 def test_capture_uses_real_final_frames_without_approving_reviews(self):
  import subprocess,shutil
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p)
   (p/'landscape.mp4').unlink();(p/'portrait-captioned.mp4').unlink()
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=navy:s=160x90:r=30:d=2','-c:v','libx264','-pix_fmt','yuv420p',str(p/'landscape.mp4')],check=True);shutil.copy2(p/'landscape.mp4',p/'portrait-captioned.mp4')
   manifest=q.load(p/'delivery-manifest.json')
   for n in ['landscape.mp4','portrait-captioned.mp4']:manifest[n]=q.sha(p/n)
   (p/'delivery-manifest.json').write_text(json.dumps(manifest));q.reset(p);result=q.capture(p)
   self.assertEqual(result['frames'],12);review=q.load(p/q.NAME)
   self.assertTrue(all(v['verdict']=='PENDING' and v['evidence'] for v in review['graphical']['frames'].values()))
   self.assertEqual(review['factual']['decision'],'PENDING')
   with self.assertRaisesRegex(ValueError,'human review'):q.validate(p)
   with self.assertRaises(FileExistsError):q.capture(p)

 def test_malformed_review_is_a_block_not_an_approval(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);r=self.fixture(p);r['factual']='PASS';self.save(p,r)
   with self.assertRaisesRegex(ValueError,'schema'):q.validate(p)

 def test_live_explanatory_keys_are_required_in_both_players(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);r=self.fixture(p)
   for fmt in q.FORMATS:
    key=fmt+':explanatory_overlay_sync'
    self.assertIn(key,r['graphical']['players'])
    changed=copy.deepcopy(r);del changed['graphical']['players'][key];self.save(p,changed)
    with self.assertRaises(ValueError):q.validate(p)

 def test_brand_ending_requires_actual_entry_middle_and_final_frames(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p,ending_seconds=3)
   props=q.load(p/'props.json');props['duration']=2.017;props['scenes'][0]['end']=2.017
   (p/'props.json').write_text(json.dumps(props))
   plan=q.plan(p);ending=[v for v in plan['frames'] if v['scene']==q.BRAND_ENDING_SCENE]
   self.assertEqual(len(ending),6)
   self.assertEqual(len([v for v in plan['frames'] if v['scene']=='one']),12)
   self.assertEqual(plan['expected_seconds'],151/30)
   for fmt in q.FORMATS:
    rows=[v for v in ending if v['format']==fmt]
    self.assertEqual([v['id'].split(':')[-1] for v in rows],['entry','middle','final'])
    self.assertEqual([v['seconds'] for v in rows],[round(v/30,6) for v in [61,106,150]])
   self.assertEqual(plan['schema'],'earnalism.strict-quality-plan.v2')

 def test_brand_frames_cannot_be_omitted_from_an_otherwise_complete_review(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);r=self.fixture(p,ending_seconds=3)
   self.assertEqual(q.validate(p)['frame_reviews'],18)
   del r['graphical']['frames'][q.BRAND_ENDING_SCENE+':Portrait:final'];self.save(p,r)
   with self.assertRaisesRegex(ValueError,'brand-ending'):q.validate(p)

 def test_watermark_and_source_context_checks_are_required_in_both_formats(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);r=self.fixture(p)
   for fmt in q.FORMATS:
    for check in ['watermark_branding','source_context']:
     key=fmt+':'+check;self.assertIn(key,r['graphical']['checks'])
     changed=copy.deepcopy(r);del changed['graphical']['checks'][key];self.save(p,changed)
     with self.assertRaisesRegex(ValueError,'checklist coverage'):q.validate(p)

 def test_invalid_or_nonending_brand_cannot_create_misleading_frame_plan(self):
  for seconds in [0,-1,float('nan'),True]:
   with self.subTest(seconds=seconds),tempfile.TemporaryDirectory() as d:
    p=pathlib.Path(d);self.fixture(p);props=q.load(p/'props.json');props['intro']={'seconds':seconds,'placement':'end'};(p/'props.json').write_text(json.dumps(props))
    with self.assertRaisesRegex(ValueError,'brand duration'):q.plan(p)
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p);props=q.load(p/'props.json');props['intro']={'seconds':3,'placement':'start'};(p/'props.json').write_text(json.dumps(props))
   with self.assertRaisesRegex(ValueError,'brand duration'):q.plan(p)

 def test_real_ending_frame_capture_stays_pending_and_preserves_media(self):
  import subprocess,shutil
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p,ending_seconds=1)
   (p/'landscape.mp4').unlink();(p/'portrait-captioned.mp4').unlink()
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=navy:s=160x90:r=30:d=3','-c:v','libx264','-pix_fmt','yuv420p',str(p/'landscape.mp4')],check=True);shutil.copy2(p/'landscape.mp4',p/'portrait-captioned.mp4')
   manifest=q.load(p/'delivery-manifest.json')
   for n in ['landscape.mp4','portrait-captioned.mp4']:manifest[n]=q.sha(p/n)
   (p/'delivery-manifest.json').write_text(json.dumps(manifest));q.reset(p);before=q.sha(p/'landscape.mp4');result=q.capture(p)
   self.assertEqual(result['frames'],18);self.assertEqual(q.sha(p/'landscape.mp4'),before)
   r=q.load(p/q.NAME)
   for key,row in r['graphical']['frames'].items():
    self.assertEqual(row['verdict'],'PENDING');self.assertTrue(row['evidence'])
   self.assertEqual(len([k for k in r['graphical']['frames'] if k.startswith(q.BRAND_ENDING_SCENE+':')]),6)
   with self.assertRaisesRegex(ValueError,'human review'):q.validate(p)
