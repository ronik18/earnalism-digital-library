import copy,datetime,json,pathlib,shutil,struct,subprocess,sys,tempfile,types,unittest,zlib
from unittest.mock import Mock,patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import audience_plan as a,studio
ROOT=pathlib.Path(__file__).resolve().parents[1]
def png(path,w,h):
 def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\x00'+b'\x00\x00\x00'*w)*h))+chunk(b'IEND',b''))
class AudiencePlanTests(unittest.TestCase):
 def fixture(self,p,filled=True):
  ep=json.loads((ROOT/'examples/moon-audience-episode.json').read_text())
  if not filled:ep.pop('audience_plan')
  (p/'episode.json').write_text(json.dumps(ep));(p/'youtube.json').write_text(json.dumps(studio.youtube_metadata(ep)));a.initialize(p)
  return ep
 def save(self,p,r):
  (p/a.PLAN).write_text(json.dumps(r));q=a.load(p/a.PACKAGE);q['audience_plan_sha256']=a.sha(p/a.PLAN);(p/a.PACKAGE).write_text(json.dumps(q))
 def complete_package(self,p):
  q=a.load(p/a.PACKAGE)
  for fmt,dims,small in [('landscape',(1280,720),[(320,180),(160,90)]),('shorts',(720,1280),[(180,320),(90,160)])]:
   refs=[]
   for i,(w,h) in enumerate([dims]+small):
    n=f'{fmt}-{i}.png';png(p/n,w,h);refs.append({'path':n,'sha256':a.sha(p/n)})
   q['formats'][fmt].update(selected_title_id='curiosity',selection_reason='Test the misconception-led browse promise; no measured winner claimed',master=refs[0],small_previews=refs[1:],design_rationale='Distinct authored hierarchy for this format; graphic review remains pending')
  (p/a.PACKAGE).write_text(json.dumps(q));a.write_metadata(p)
 def test_blank_plan_blocks_real_generation_without_claiming_audience_results(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p,False)
   with self.assertRaisesRegex(ValueError,'incomplete'):a.validate_generation(p)
   with self.assertRaisesRegex(ValueError,'incomplete'):studio.make_job(p,{})
   self.assertFalse((p/'raw').exists())
 def test_filled_example_is_generation_ready_not_viewer_or_publication_approval(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p);r=a.validate_generation(p)
   self.assertEqual(r['audience_effectiveness'],'UNPROVEN');self.assertFalse(r['publication_approval'])
   original=(p/a.PLAN).read_bytes();a.initialize(p);self.assertEqual((p/a.PLAN).read_bytes(),original)
 def test_script_edit_invalidates_plan_but_edition_id_and_music_do_not(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);ep=self.fixture(p);ep['id']='fresh';ep['music']={'enabled':True};(p/'episode.json').write_text(json.dumps(ep));a.validate_generation(p)
   ep['scenes'][0]['text']='Different claim.';(p/'episode.json').write_text(json.dumps(ep))
   with self.assertRaisesRegex(ValueError,'Stale'):a.validate_generation(p)
 def test_duplicate_titles_shared_crop_or_unmapped_promises_fail(self):
  for defect in ['duplicate','crop','promise']:
   with self.subTest(defect=defect),tempfile.TemporaryDirectory() as d:
    p=pathlib.Path(d);self.fixture(p);r=a.load(p/a.PLAN)
    if defect=='duplicate':r['formats']['shorts']['titles'][1]['text']=r['formats']['shorts']['titles'][0]['text']
    elif defect=='crop':r['formats']['shorts']['composition']=r['formats']['landscape']['composition']
    else:r['formats']['landscape']['titles'][0]['promise_scene']='invented'
    self.save(p,r)
    with self.assertRaises(ValueError):a.validate_generation(p)
 def test_shared_learning_purpose_and_real_words_are_allowed(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p);r=a.load(p/a.PLAN);r['audience']['viewing_need']='Understand Mastodon social media';r['formats']['shorts']['purpose']=r['formats']['landscape']['purpose'];r['story']['retrieval']['prompt']='Fill in the causal relationship';self.save(p,r);a.validate_generation(p)
 def test_planned_next_lesson_cannot_be_a_fake_watch_link(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p);r=a.load(p/a.PLAN);r['series']['next_lesson']['url']='https://example.com/not-created';self.save(p,r)
   with self.assertRaisesRegex(ValueError,'masquerade'):a.validate_generation(p)
 def test_available_lesson_needs_current_exact_route_observation(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p);r=a.load(p/a.PLAN);n=r['series']['next_lesson'];n.update(status='available',url='https://example.com/real');self.save(p,r)
   with self.assertRaisesRegex(ValueError,'URL-bound'):a.validate_generation(p)
   (p/'route.txt').write_text('Actual route observation fixture');n['availability_observation']={'url':n['url'],'access':'public','observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'evidence':[{'path':'route.txt','sha256':a.sha(p/'route.txt')}]};self.save(p,r);a.validate_generation(p)
   n['availability_observation']['url']='https://example.com/other';self.save(p,r)
   with self.assertRaises(ValueError):a.validate_generation(p)
 def test_actual_readbacks_and_selected_format_metadata_required(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p)
   with self.assertRaises(ValueError):a.validate_package(p)
   self.complete_package(p);self.assertFalse(a.validate_package(p)['publication_approval'])
   metadata=a.load(p/'youtube-shorts.json');metadata['title']='A different unsupported promise';(p/'youtube-shorts.json').write_text(json.dumps(metadata))
   with self.assertRaisesRegex(ValueError,'metadata'):a.validate_package(p)
 def test_tiny_video_or_changed_cover_cannot_pass_as_master(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p);self.complete_package(p);q=a.load(p/a.PACKAGE)
   png(p/'tiny.png',32,18);q['formats']['landscape']['master']={'path':'tiny.png','sha256':a.sha(p/'tiny.png')};(p/a.PACKAGE).write_text(json.dumps(q))
   with self.assertRaisesRegex(ValueError,'High-resolution'):a.validate_package(p)
   subprocess.run(['ffmpeg','-v','error','-n','-f','lavfi','-i','color=c=navy:s=1280x720:d=0.04','-frames:v','1','-c:v','libx264','-f','mp4',str(p/'movie-disguised.png')],check=True)
   q['formats']['landscape']['master']={'path':'movie-disguised.png','sha256':a.sha(p/'movie-disguised.png')};(p/a.PACKAGE).write_text(json.dumps(q))
   with self.assertRaisesRegex(ValueError,'Static'):a.validate_package(p)
   (p/'landscape-0.png').write_bytes(b'changed');q['formats']['landscape']['master']['path']='landscape-0.png';(p/a.PACKAGE).write_text(json.dumps(q))
   with self.assertRaisesRegex(ValueError,'stale'):a.validate_package(p)
 def test_handoff_reset_preserves_history_and_starts_pending(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p);(p/'delivery-manifest.json').write_text(json.dumps({'episode.json':a.sha(p/'episode.json')}));a.reset_handoff(p);r=a.load(p/a.HANDOFF);r['youtube']['copyright_claims']['decision']='PASS';(p/a.HANDOFF).write_text(json.dumps(r));old=a.sha(p/a.HANDOFF);a.reset_handoff(p)
   self.assertTrue((p/'logs/publication-handoff-history'/(old+'.json')).exists());self.assertEqual(a.load(p/a.HANDOFF)['youtube']['copyright_claims']['decision'],'PENDING')
 def test_pending_platform_checks_do_not_block_local_package_but_cannot_grant_delivery(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p);self.complete_package(p);a.validate_package(p);(p/'delivery-manifest.json').write_text(json.dumps({'episode.json':a.sha(p/'episode.json')}));a.reset_handoff(p)
   with patch.object(studio,'release_check',return_value='READY_FOR_WEBSITE_ADAPTER_REVIEW'):
    with self.assertRaises(ValueError):a.validate_handoff(p)
 def test_fixture_can_generate_but_never_publish(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);ep=self.fixture(p,False);ep['private_test']=True;(p/'episode.json').write_text(json.dumps(ep));self.assertEqual(a.validate_generation(p)['status'],'ENGINEERING_FIXTURE_ONLY')
   with self.assertRaisesRegex(ValueError,'never publish'):studio.release_check(p)
 def test_resume_cannot_reach_model_setup_without_audience_plan(self):
  import colab_runner
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);(root/'config').mkdir();shutil.copy2(ROOT/'config/defaults.json',root/'config/defaults.json');folder=root/'outputs/resume';folder.mkdir(parents=True);ep=self.fixture(folder,False);ep=studio.normalize_episode(ep);(folder/'episode.json').write_text(json.dumps(ep));source=root/'input.json';source.write_text(json.dumps(ep));runtime=types.SimpleNamespace(setup_qwen=Mock())
   with patch.object(studio,'BASE',root),patch.object(studio,'verify_original'),patch.dict(sys.modules,{'notebook_runtime':runtime}),patch('colab_runner.subprocess.run',return_value=types.SimpleNamespace(returncode=0)):
    with self.assertRaisesRegex(ValueError,'incomplete'):colab_runner.execute(source,free_runtime_confirmed=True,run_id='resume')
   runtime.setup_qwen.assert_not_called()
 def test_full_handoff_requires_fresh_policy_distinct_ids_and_exact_uploaded_sources(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p)
   for n in ['landscape.mp4','portrait-captioned.mp4','platform.txt']:(p/n).write_bytes(n.encode())
   (p/'delivery-manifest.json').write_text(json.dumps({'episode.json':a.sha(p/'episode.json'),'landscape.mp4':a.sha(p/'landscape.mp4'),'portrait-captioned.mp4':a.sha(p/'portrait-captioned.mp4')}))
   a.reset_handoff(p);r=a.load(p/a.HANDOFF);now=datetime.datetime.now(datetime.timezone.utc).isoformat();ref={'path':'platform.txt','sha256':a.sha(p/'platform.txt')}
   r['policy_review'].update(reviewed_at=now,reviewer='test reviewer',notes='Official sources checked for this private fixture')
   r['platform_video_ids']={'landscape':'abcdefghijk','shorts':'ABCDEFGHIJK'};r['uploaded_source_sha256']={'landscape':a.sha(p/'landscape.mp4'),'shorts':a.sha(p/'portrait-captioned.mp4')}
   for item in r['youtube'].values():item.update(decision='PASS',reviewer='test reviewer',reviewed_at=now,evidence=[ref])
   r['youtube']['related_video'].update(decision='NOT_APPLICABLE',note='Next episode is genuinely planned, with no watch URL',evidence=[])
   def save():(p/a.HANDOFF).write_text(json.dumps(r))
   save()
   with patch.object(studio,'release_check',return_value='READY_FOR_WEBSITE_ADAPTER_REVIEW') as gate:
    self.assertFalse(a.validate_handoff(p)['publication_approval']);gate.assert_called_once_with(p)
    r['platform_video_ids']['shorts']=r['platform_video_ids']['landscape'];save()
    with self.assertRaisesRegex(ValueError,'Distinct'):a.validate_handoff(p)
    r['platform_video_ids']['shorts']='ABCDEFGHIJK';r['uploaded_source_sha256']['shorts']='wrong';save()
    with self.assertRaisesRegex(ValueError,'exact final'):a.validate_handoff(p)
    r['uploaded_source_sha256']['shorts']=a.sha(p/'portrait-captioned.mp4');r['youtube']['related_video']['reviewer']='';save()
    with self.assertRaises(ValueError):a.validate_handoff(p)
    r['youtube']['related_video']['reviewer']='test';r['policy_review']['reviewed_at']='2099-01-01T00:00:00+00:00';save()
    with self.assertRaisesRegex(ValueError,'observation date'):a.validate_handoff(p)
 def test_changed_master_or_manifest_invalidates_handoff(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p);(p/'delivery-manifest.json').write_text(json.dumps({'episode.json':a.sha(p/'episode.json')}));a.reset_handoff(p)
   (p/'episode.json').write_text('{}')
   with self.assertRaisesRegex(ValueError,'stale'):a.validate_handoff(p)
   (p/'delivery-manifest.json').write_text('{}')
   with self.assertRaisesRegex(ValueError,'Stale publication'):a.validate_handoff(p)
if __name__=='__main__':unittest.main()
