"""Episode-recipe regression fixtures; no synthesis or listening acceptance."""
from pathlib import Path
import copy,json,tempfile,unittest
from . import assemble as a
ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'output/episodes/07-rainbow/production-v1'
AUD=ROOT/'output/episodes/07-rainbow/naturalness-repair-v1/imported/raw/rainbow-connected-01.wav'
META=Path(str(AUD)+'.json')

class StoryRecipeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.r=Path(self.tmp.name)
  for name in ('units.json','scene-units.json','baseline-job.json','generation-plan.json'):(self.r/name).write_bytes((OLD/name).read_bytes())
  self.groups=a.load(self.r/'units.json');self.scenes=a.load(self.r/'scene-units.json');self.baseline=a.load(self.r/'baseline-job.json');self.metadata=a.load(META)
  self.decision={'decision':a.STORY_DECISION,'user_message':'Owner selected this audition for a separate private rebuild.','existing_videos_unchanged':True,'publication_approved':False}
  (self.r/a.STORY_DECISION_FILE).write_text(json.dumps(self.decision))
  self.recipe={'schema':'earnalism.rainbow-accepted-direction.v1','state':'OWNER_SELECTED_DIRECTION_FOR_PRIVATE_REBUILD','publication_approved':False,'baseline_sha256':a.common.PUBLISHED_BASELINE_SHA256,'worker_sha256':a.common.WORKER_SHA256,'owner_decision_sha256':a.sha(self.r/a.STORY_DECISION_FILE),'direction':self.metadata['settings']['instruct'],'direction_sha256':a.STORY_DIRECTION_SHA,'accepted_audition':{'audio_path':str(AUD),'audio_sha256':a.STORY_AUDITION_AUDIO_SHA,'metadata_path':str(META),'metadata_sha256':a.STORY_AUDITION_METADATA_SHA}}
  self.save_recipe()
 def save_recipe(self):(self.r/a.STORY_RECIPE_FILE).write_text(json.dumps(self.recipe))
 def test_selected_direction_validates_actual_source_without_mutating_metadata(self):
  before=copy.deepcopy(self.metadata);source=a.validate_recipe_source(self.r,self.groups[0],AUD,self.metadata,self.baseline)
  self.assertEqual(source['audio_sha256'],a.STORY_AUDITION_AUDIO_SHA);self.assertEqual(self.metadata,before);self.assertEqual(source['new_recording_listening'],'PENDING')
 def test_original_baseline_path_remains_supported(self):
  (self.r/a.STORY_RECIPE_FILE).unlink();wav=OLD/'imported/raw/rainbow-connected-01.wav'
  self.assertEqual(a.validate_recipe_source(self.r,self.groups[0],wav,a.load(Path(str(wav)+'.json')),self.baseline)['audio_sha256'],a.sha(wav))
 def test_missing_or_changed_decision_and_audition_fail_closed(self):
  for field,value in [('owner_decision_sha256','0'*64),('direction_sha256','0'*64),('baseline_sha256','0'*64),('publication_approved',True)]:
   saved=self.recipe[field];self.recipe[field]=value;self.save_recipe()
   with self.assertRaises(ValueError):a.accepted_direction(self.r)
   self.recipe[field]=saved
  self.save_recipe();self.recipe['accepted_audition']['audio_sha256']='0'*64;self.save_recipe()
  with self.assertRaises(ValueError):a.accepted_direction(self.r)
 def test_unapproved_generation_or_voice_change_is_rejected_even_if_rehashed(self):
  for key,value in [('speaker','Not Ryan'),('generation',{**self.metadata['settings']['generation'],'temperature':.5}),('instruct','A different instruction')]:
   meta=copy.deepcopy(self.metadata);meta['settings'][key]=value;meta['effective_key']=a.common.object_hash(meta['settings'])
   for attempt in meta['attempts']:
    if attempt['attempt']==meta['selected_attempt']:attempt['effective_key']=meta['effective_key']
   with self.assertRaises(ValueError):a.validate_recipe_source(self.r,self.groups[0],AUD,meta,self.baseline)
 def test_actual_attempt_and_audio_integrity_still_enforced(self):
  for field,value in [('effective_key','0'*64),('selected_seed',1),('wav_sha256','0'*64)]:
   meta=copy.deepcopy(self.metadata);meta[field]=value
   with self.assertRaises(ValueError):a.validate_recipe_source(self.r,self.groups[0],AUD,meta,self.baseline)
 def fixture_alignments(self):
  for g in self.groups:
   text=g['text'].replace('colours','colors').replace('colour','color').replace('forty-two','42')
   w=self.r/'imported/raw'/f"{g['id']}.wav";w.parent.mkdir(parents=True,exist_ok=True);w.write_bytes(b'NOT MEDIA: engineering source binding only')
   p=self.r/'imported/alignment'/f"{g['id']}.json";p.parent.mkdir(parents=True,exist_ok=True)
   p.write_text(json.dumps({'audio_sha256':a.sha(w),'model_revision':a.STORY_ASR_REVISION,'recognized':text,'word_times':[{'word':word,'start':i*.1,'end':i*.1+.09} for i,word in enumerate(text.split())]}))
 def test_notation_resolution_is_exact_and_stale_evidence_is_rejected(self):
  self.fixture_alignments();a.create_story_display_resolution(self.r)
  record,groups,scenes=a.story_display_state(self.r,self.groups,self.scenes)
  self.assertEqual(len(record['groups']),4);self.assertNotIn('forty-two',' '.join(g['text'] for g in groups));a.validate_units(groups,scenes)
  p=self.r/'imported/alignment/rainbow-connected-01.json';v=a.load(p);v['recognized']=v['recognized'].replace('rainbow','eclipse',1);p.write_text(json.dumps(v))
  with self.assertRaises(ValueError):a.story_display_state(self.r,self.groups,self.scenes)
 def test_mixed_asr_spelling_keeps_unchanged_groups_and_anchors_literal(self):
  self.fixture_alignments()
  for unit in ('rainbow-connected-02','rainbow-connected-04'):
   g=next(g for g in self.groups if g['id']==unit);p=self.r/'imported/alignment'/f'{unit}.json';v=a.load(p);v['recognized']=g['text'];v['word_times']=[{'word':word,'start':i*.1,'end':i*.1+.09} for i,word in enumerate(g['text'].split())];p.write_text(json.dumps(v))
  a.create_story_display_resolution(self.r);record,groups,scenes=a.story_display_state(self.r,self.groups,self.scenes)
  self.assertIn('sending color',scenes[0]['text']);self.assertIn('sending color',scenes[0]['anchors']['change'])
  self.assertIn('Different colours',scenes[2]['text']);self.assertIn('Different colours',scenes[2]['anchors']['dispersion']);self.assertIn('forty-two',scenes[3]['anchors']['angle']);self.assertIn('The colours',scenes[6]['text'])
  a.validate_units(groups,scenes)
 def test_actual_alternate_asr_identity_and_file_binding_are_preserved(self):
  self.fixture_alignments();a.create_story_asr_binding(self.r);p=self.r/'imported/alignment/rainbow-connected-03.json';v=a.load(p)
  audit,_=a.recipe_alignment_audit(self.r,self.groups[2],v,v['audio_sha256'],20,p)
  self.assertEqual(audit['actual_asr_model_revision'],a.STORY_ASR_REVISION);self.assertEqual(v['model_revision'],a.STORY_ASR_REVISION)
  self.assertEqual(audit['differences'],[])
  p.write_text(p.read_text()+'\n')
  with self.assertRaises(ValueError):a.recipe_alignment_audit(self.r,self.groups[2],v,v['audio_sha256'],20,p)
 def test_alternate_asr_without_exact_receipt_or_unknown_revision_rejected(self):
  self.fixture_alignments();p=self.r/'imported/alignment/rainbow-connected-03.json';v=a.load(p)
  with self.assertRaises(FileNotFoundError):a.recipe_alignment_audit(self.r,self.groups[2],v,v['audio_sha256'],20,p)
  a.create_story_asr_binding(self.r);v['model_revision']='not-the-actual-model'
  with self.assertRaises(ValueError):a.recipe_alignment_audit(self.r,self.groups[2],v,v['audio_sha256'],20,p)

if __name__=='__main__':unittest.main()
