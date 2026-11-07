"""Topic-independent study contracts; all completed records here are test data."""
import copy,json,pathlib,sys,tempfile,unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from learning_acceptance import pending,validate,CASES,TOPIC_CASES
from participant_preview import make


class TopicAcceptanceTests(unittest.TestCase):
 def plan(self):
  return {'study':{'questions':[{'id':'mechanism','prompt':'What causes the change shown?','answer_scene':'cause'},{'id':'transfer-application','prompt':'What would change in the second example?','answer_scene':'application'}]}}
 def complete(self,plan=None):
  record=pending(plan);record['delivery_manifest_sha256']='test-manifest'
  questions=[q['id'] for q in plan['study']['questions']] if plan is not None else ['q1','q2','q3']
  record['learning'].update(decision='PASS',reviewer='TEST REVIEWER ONLY',unresolved_confusions=[],participants=[{'id':'TEST PARTICIPANT ONLY','first_time':True,'single_uninterrupted_view':True,'responses':{q:'TEST RESPONSE ONLY' for q in questions}}])
  record['acceptance']['reviewer']='TEST REVIEWER ONLY'
  for case in record['acceptance']['cases'].values():case.update(status='PASS',evidence='TEST EVIDENCE ONLY',device='TEST DEVICE ONLY')
  if plan is not None:
   record['learning']['human_confirmed']=True;record['acceptance']['human_confirmed']=True
  return record
 def test_pending_v2_retains_neutral_question_content_without_approving_anything(self):
  plan=self.plan();record=pending(plan)
  self.assertEqual(record['schema'],'earnalism.learning-acceptance.v2')
  self.assertEqual(record['learning']['questions'],plan['study']['questions'])
  self.assertIn('critical_explanations',record['acceptance']['cases']);self.assertNotIn('quarter_scene',record['acceptance']['cases'])
  self.assertFalse(record['learning']['human_confirmed']);self.assertFalse(record['acceptance']['human_confirmed'])
  self.assertEqual(record['learning']['decision'],'PENDING')
  plan['study']['questions'][0]['prompt']='Changed external plan'
  self.assertNotEqual(record['learning']['questions'],plan['study']['questions'])
 def test_actual_topic_ids_are_required_instead_of_legacy_q_numbers(self):
  plan=self.plan();record=self.complete(plan);self.assertTrue(validate(record,'test-manifest',plan))
  del record['learning']['participants'][0]['responses']['transfer-application']
  record['learning']['participants'][0]['responses'].update(q1='TEST',q2='TEST',q3='TEST')
  with self.assertRaisesRegex(ValueError,'Actual first-time'):validate(record,'test-manifest',plan)
 def test_current_question_text_answer_scene_and_manifest_are_bound(self):
  plan=self.plan();record=self.complete(plan)
  with self.assertRaisesRegex(ValueError,'Current topic'):validate(record,'test-manifest')
  with self.assertRaisesRegex(ValueError,'current delivery'):validate(record,'different-manifest',plan)
  for key in ['prompt','answer_scene']:
   changed=copy.deepcopy(plan);changed['study']['questions'][0][key]='Different actual study content'
   with self.subTest(key=key),self.assertRaisesRegex(ValueError,'current study'):validate(record,'test-manifest',changed)
  record['learning']['questions'][0]['prompt']='Changed recorded question'
  with self.assertRaisesRegex(ValueError,'current study'):validate(record,'test-manifest',plan)
 def test_v2_requires_actual_first_viewing_and_explicit_human_decisions(self):
  plan=self.plan()
  for section in ['learning','acceptance']:
   record=self.complete(plan);record[section]['human_confirmed']=False
   with self.subTest(section=section),self.assertRaisesRegex(ValueError,'Explicit human'):validate(record,'test-manifest',plan)
  for key in ['first_time','single_uninterrupted_view']:
   record=self.complete(plan);record['learning']['participants'][0][key]=False
   with self.subTest(key=key),self.assertRaisesRegex(ValueError,'Actual first-time'):validate(record,'test-manifest',plan)
  record=self.complete(plan);record['acceptance']['cases']['critical_explanations']['status']='NOT_RUN'
  with self.assertRaisesRegex(ValueError,'device/listening'):validate(record,'test-manifest',plan)
 def test_legacy_v1_contract_remains_readable_for_archives(self):
  record=self.complete();self.assertEqual(record['schema'],'earnalism.learning-acceptance.v1')
  self.assertEqual(set(record['acceptance']['cases']),set(CASES));self.assertTrue(validate(record,'test-manifest'))
  record['acceptance']['cases']['quarter_scene']['status']='NOT_RUN'
  with self.assertRaisesRegex(ValueError,'device/listening'):validate(record,'test-manifest')
 def test_duplicate_or_incomplete_topic_questions_fail_before_record_creation(self):
  for defect in ['missing','duplicate','blank-prompt','blank-answer-scene']:
   plan=self.plan()
   if defect=='missing':plan={}
   elif defect=='duplicate':plan['study']['questions'][1]['id']=plan['study']['questions'][0]['id']
   elif defect=='blank-prompt':plan['study']['questions'][0]['prompt']=' '
   else:plan['study']['questions'][0]['answer_scene']=' '
   with self.subTest(defect=defect),self.assertRaises(ValueError):pending(plan)


class NeutralParticipantTests(unittest.TestCase):
 def test_renamed_semantic_answer_panels_and_nested_answers_never_reach_participants(self):
  page='''<!doctype html><main><video width="1920" height="1080" poster="landscape.png"><source src="landscape-preview.mp4?v=7"></video>
<section data-role='answer-key'><h2>A completely renamed question set</h2><details><summary>New wording</summary><p>SECRET ANSWER</p></details></section>
<details data-role="speech-review"><summary>Different voice heading</summary>PRIVATE VOICE NOTES</details>
<div data-role='transcript-sources'><h2>Renamed transcript</h2>PRIVATE TRANSCRIPT</div>
<p id="keep">NEUTRAL CONTENT &amp; CONTROLS</p></main><script>const retained = 'playback';</script>'''
  with tempfile.TemporaryDirectory() as d:
   folder=pathlib.Path(d);(folder/'watch.html').write_text(page);make(folder)
   for name in ['participant.html','participant-shorts.html']:
    result=(folder/name).read_text()
    for private in ['SECRET ANSWER','PRIVATE VOICE NOTES','PRIVATE TRANSCRIPT','A completely renamed question set']:self.assertNotIn(private,result)
    self.assertIn('NEUTRAL CONTENT &amp; CONTROLS',result);self.assertIn("const retained = 'playback';",result)
   self.assertEqual((folder/'watch.html').read_text(),page)
   self.assertIn('portrait-preview.mp4?v=7',(folder/'participant-shorts.html').read_text())
 def test_unclosed_answer_panel_fails_instead_of_creating_a_misleading_study_page(self):
  with tempfile.TemporaryDirectory() as d:
   folder=pathlib.Path(d);(folder/'watch.html').write_text('<main><section data-role="answer-key">PRIVATE ANSWER')
   with self.assertRaisesRegex(ValueError,'Unclosed review panel'):make(folder)
   self.assertFalse((folder/'participant.html').exists())
 def test_generic_template_keeps_controls_and_uses_topic_content_placeholders(self):
  page=(ROOT/'watch-template.html').read_text()
  for placeholder in ['{{TOPIC}}','{{DIAGRAM_CONTEXT}}','{{UNDERSTANDING_CHECKS}}']:self.assertIn(placeholder,page)
  for topic_copy in ['NASA','US Naval','northern-hemisphere','first quarter','Moon sample']:self.assertNotIn(topic_copy,page)
  for control in ['id="sample"','id="caption-safe-area"','id="replay-preview"','id="fullscreen-preview"','id="reload-preview"','id="switch-codec"']:self.assertIn(control,page)
  self.assertIn('data-role="answer-key"',page)


if __name__=='__main__':unittest.main()
