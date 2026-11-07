import copy,json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import audience_plan as a,studio,strict_quality
from caption_preview import label_timeline
ROOT=pathlib.Path(__file__).resolve().parents[1]
def generic_fixture(topic):
 ep={'id':'planning-fixture','private_test':False,'topic':topic,'label_profile':'unimplemented-topic','diagram_context':'A hypothetical illustrative model for a planning test; not a researched publication.','sources':[{'id':'fixture','url':'https://example.invalid/planning-only','publisher':'Planning fixture'}],'scenes':[{'id':'observe','heading':'What changes?','text':'Consider this illustrative question.','diagram':'observation','source_ids':['fixture']},{'id':'explain','heading':'What explains it?','text':'Compare a proposed mechanism.','diagram':'mechanism','source_ids':['fixture']}]}
 p=a.create(ep)
 p['audience'].update(primary_viewer='Curious non-specialist',language='English',prior_knowledge='Recognizes the phenomenon, not the mechanism',viewing_need='Understand a relationship',learning_promise='Explain the mechanism in this planning fixture',misconception='A tempting but incomplete initial explanation',original_contribution='A model connecting observation to mechanism',discovery_context='Browse among related explanatory topics',why_choose_this_explanation='A relevant explanatory distinction absent from the assumed prior knowledge')
 for fmt in a.FORMATS:
  p['formats'][fmt].update(purpose='A complete explanation',composition='Side-by-side spatial context' if fmt=='landscape' else 'Sequential stacked mobile composition',duration_rationale='Enough natural speech and reading time, no padding',titles=[{'id':'search','text':topic,'rationale':'Answer the topic accurately','promise_scene':'explain'},{'id':'curiosity','text':'What changes the outcome?','rationale':'Explore the same mechanism','promise_scene':'explain'}],cover_brief={'concept':'One relevant focal object','text':'','meaning_without_text':'Observation compared with explanation'})
 p['story']['opening'].update(scene_id='observe',first_frame_visual='The relevant object is visible',early_visual_payoff='A visible relationship changes',payoff_scene='observe',payoff_offset_seconds=1)
 for i,s in enumerate(ep['scenes']):p['story']['scenes'].append({'scene_id':s['id'],'viewer_question':s['heading'],'visible_answer':'Show the observation' if i==0 else 'Reveal the relationship','new_understanding':'Recognize the puzzle' if i==0 else 'Explain the puzzle','narration_economy':'Keep accessible reasoning spoken and let the diagram show the relation','transition_reason':'Carry the observation to the mechanism' if i==0 else 'Close the original question','next_scene':'explain' if i==0 else None,'formats':{f:{'visual_action':'Show the relevant relation '+f,'essential_labels':['Essential referent'],'minimum_read_seconds':1,'reading_strategy':'Stage and hold the label','caption_clearance':'Keep explanation clear of the caption band'} for f in a.FORMATS}})
 p['story']['retrieval'].update(mode='prediction',prompt='What would happen if the condition changed?',answer_scene='explain');p['story']['closing_callback']='Return to the original observation with a usable explanation'
 p['study'].update(questions=[{'id':'mechanism_test','prompt':'How would you explain the mechanism?','answer_scene':'explain'}],card_choice_protocol='Uncoached actual choices among authorized cards with an owned distractor; record order and limitations')
 p['series'].update(viewer_promise='One everyday mechanism understood visually',sustainable_cadence='Set a sustainable rhythm after measuring production effort; no scheduled job',viewer_led_topic_method='Use actual viewer questions and confusion',next_lesson={'status':'none','topic':'','url':None,'reason':'Standalone planning fixture'})
 ep['audience_plan']=p;return ep
class ViewerExperienceTests(unittest.TestCase):
 def write(self,p,ep):
  (p/'episode.json').write_text(json.dumps(ep));a.initialize(p)
  scenes=[{**s,'start':i*4,'end':(i+1)*4} for i,s in enumerate(ep['scenes'])];(p/'props.json').write_text(json.dumps({'scenes':scenes,'duration':len(scenes)*4}))
 def test_unrelated_topics_pass_generic_planning_but_do_not_gain_a_renderer(self):
  for topic in ['Why does bread rise?','What closes an electric circuit?','How can a map projection change apparent area?']:
   with self.subTest(topic=topic),tempfile.TemporaryDirectory() as d:
    p=pathlib.Path(d);ep=generic_fixture(topic);self.write(p,ep);self.assertEqual(a.validate_generation(p)['status'],'GENERATION_BRIEF_COMPLETE');a.validate_story_timing(p)
    with self.assertRaisesRegex(ValueError,'topic-specific renderer|lunar geometry'):studio.validate(ep)
 def test_missing_scene_or_false_bridge_is_rejected(self):
  for defect in ['missing','bridge']:
   with tempfile.TemporaryDirectory() as d:
    p=pathlib.Path(d);ep=generic_fixture('Planning fixture')
    if defect=='missing':ep['audience_plan']['story']['scenes'].pop()
    else:ep['audience_plan']['story']['scenes'][0]['next_scene']='not-a-scene'
    self.write(p,ep)
    with self.assertRaisesRegex(ValueError,'Every actual scene|actual next scene'):a.validate_generation(p)
 def test_reading_and_early_payoff_must_fit_actual_scenes(self):
  for defect in ['reading','payoff','nan']:
   with tempfile.TemporaryDirectory() as d:
    p=pathlib.Path(d);ep=generic_fixture('Planning fixture')
    if defect=='reading':ep['audience_plan']['story']['scenes'][0]['formats']['shorts']['minimum_read_seconds']=5
    else:ep['audience_plan']['story']['opening']['payoff_offset_seconds']=float('nan') if defect=='nan' else 10
    self.write(p,ep)
    with self.assertRaises(ValueError):a.validate_story_timing(p)
 def test_strict_plan_includes_actual_first_frame_and_reveal_checkpoints(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.write(p,generic_fixture('Planning fixture'));plan=strict_quality.plan(p)
   for fmt in ['Landscape','Portrait']:
    samples={v['id']:v for v in plan['frames'] if v['format']==fmt};self.assertEqual(samples[f'observe:{fmt}:first-subject']['seconds'],0);self.assertEqual(samples[f'observe:{fmt}:visual-payoff']['seconds'],1)
   self.assertIn('scene_question_answer_continuity',plan['graphic_checks']);self.assertIn('cognitive_reading_load',plan['graphic_checks'])
 def test_unknown_label_profile_has_no_lunar_companion_labels(self):
  props={'scenes':[{'id':'state','diagram':'phases','start':0,'end':5,'anchors':[]}]}
  self.assertEqual(label_timeline(props,profile='chemical-process'),[])
 def test_non_lunar_metadata_and_watch_page_have_no_lunar_source_or_question_leak(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);ep=generic_fixture('How does a circuit work?');self.write(p,ep);(p/'landscape.mp4').touch();studio.draft_watch(p);metadata=studio.youtube_metadata(ep)
   for content in [json.dumps(metadata),(p/'watch.html').read_text()]:
    for bad in ['NASA','USNO','northern-hemisphere','Moon','first quarter']:self.assertNotIn(bad,content)
   self.assertIn('How would you explain the mechanism?',(p/'watch.html').read_text());self.assertNotIn('{{DIAGRAM_CONTEXT}}',(p/'watch.html').read_text())
 def test_old_planning_schema_is_not_silently_promoted(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);ep=generic_fixture('Planning fixture');ep['audience_plan']['schema']='earnalism.audience-plan.v1';self.write(p,ep)
   with self.assertRaisesRegex(ValueError,'obsolete schema'):a.validate_generation(p)
 def test_simulated_personas_cannot_supply_measurement_basis(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);ep=generic_fixture('Planning fixture');ep['audience_plan']['study']['measurement_basis']='top_three_worldwide_personas';self.write(p,ep)
   with self.assertRaisesRegex(ValueError,'Simulated personas'):a.validate_generation(p)
 def test_optional_archival_study_does_not_gate_current_primary_review(self):
  import improvement
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)
   for name,value in [('episode.json',{'private_test':False,'requires_learning_acceptance':True}),('music-balance.json',{'issues':[]}),('music-automation.json',{'transition_check':{'issues':[],'maximum_phrase_gain_rate_db_per_second':0}}),('acceptance-review.json',{'schema':'earnalism.learning-acceptance.v1'})]:(p/name).write_text(json.dumps(value))
   (p/'delivery-manifest.json').write_text(json.dumps({'episode.json':a.sha(p/'episode.json')}));review={k:True for k in ['factual','rights','voice','audiovisual','technical','delivery']};review.update(reviewer='test only',delivery_manifest_sha256=a.sha(p/'delivery-manifest.json'));(p/'review.json').write_text(json.dumps(review))
   with patch('strict_quality.validate',return_value={}),patch('learning_acceptance.validate',return_value=True) as legacy:
    result=improvement.inspect(p)
   self.assertEqual(result['status'],'READY_FOR_EXISTING_RELEASE_GATE');self.assertEqual(result['optional_learning_research']['study'],'OPTIONAL_EVIDENCE_NOT_RELEASE_APPROVAL');legacy.assert_not_called()
if __name__=='__main__':unittest.main()
