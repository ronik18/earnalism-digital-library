"""Focused provenance tests; fake media bytes exercise binding, not AV approval."""
import copy,json,pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import rights_audit,retime_score
ROOT=pathlib.Path(__file__).resolve().parents[1]

class RetimeRightsTests(unittest.TestCase):
 def fixture(self,work):
  parent=work/'parent';parent.mkdir();child=work/'child';child.mkdir();(child/'raw').mkdir()
  old_scenes=[{'id':'s1','text':'Same complete spoken explanation.','start':0,'end':10,'anchors':[{'phrase':'Same','time':4}]}]
  new_scenes=copy.deepcopy(old_scenes);new_scenes[0]['end']=12;new_scenes[0]['anchors'][0]['time']=5
  events=[{'time':2,'midi':50,'instrument':'piano','velocity':.3,'duration':3,'phrase':'chord','pan':0,'arrangement_gain_db':-1}]
  old={'kind':'original acoustic chamber composition','version':'moon-score-v13-speech-aware-phrase-placement','external_compositions':[],'events':events,'quiet_intervals':[[3,4]],'composition_source_sha256':rights_audit.digest(ROOT/'phrase_music_repair.py')}
  for name,data in [('score.wav',b'parent score'),('score-piano.wav',b'parent stem')]: (parent/name).write_bytes(data)
  old['recording_sha256']=rights_audit.digest(parent/'score.wav');old['stems']={'score-piano.wav':rights_audit.digest(parent/'score-piano.wav')}
  (parent/'props.json').write_text(json.dumps({'scenes':old_scenes,'duration':10}));(parent/'score.provenance.json').write_text(json.dumps(old))
  manifest={p.name:rights_audit.digest(p) for p in parent.iterdir()};(parent/'delivery-manifest.json').write_text(json.dumps(manifest))
  for name,data in [('score.wav',b'child score'),('score-piano.wav',b'child stem'),('narration.wav',b'child narration')]: (child/name).write_bytes(data)
  (child/'props.json').write_text(json.dumps({'scenes':new_scenes,'duration':12}))
  points=retime_score.timeline_map(old_scenes,new_scenes);mapped,mapping=retime_score.preserve_events(events,points,12)
  bank=ROOT/'assets/music/vcsl-piano-harp-v1';assets=json.loads((bank/'manifest.json').read_text())
  bound={str((ROOT/n).resolve()):rights_audit.digest(ROOT/n) for n in ['retime_score.py','final_chamber_score.py']}
  score={'kind':'original acoustic chamber composition','version':retime_score.VERSION,'seconds':12,'source_sha256':rights_audit.digest(ROOT/'score.py'),'composition_source_sha256':rights_audit.digest(ROOT/'retime_score.py'),'base_composition_source_sha256':rights_audit.digest(ROOT/'final_chamber_score.py'),'recording_sha256':rights_audit.digest(child/'score.wav'),'events':mapped,'quiet_intervals':retime_score.map_intervals(old['quiet_intervals'],points),'third_party_samples':[assets['samples'][0]],'external_compositions':[],'asset_manifest_sha256':rights_audit.digest(bank/'manifest.json'),'license':'CC0-1.0','license_sha256':rights_audit.digest(bank/'LICENSE'),'readme_sha256':rights_audit.digest(bank/'README.md'),'stems':{'score-piano.wav':rights_audit.digest(child/'score-piano.wav')},'bound_source_sha256':bound,
   'retime':{'parent_folder':str(parent),'parent_delivery_manifest_sha256':rights_audit.digest(parent/'delivery-manifest.json'),'parent_score_sha256':rights_audit.digest(parent/'score.wav'),'parent_provenance_sha256':rights_audit.digest(parent/'score.provenance.json'),'source_events_sha256':retime_score.canonical(events),'source_rests_sha256':retime_score.canonical(old['quiet_intervals']),'timeline_points':points,'event_mapping':mapping,'narration_sha256':rights_audit.digest(child/'narration.wav'),'bound_source_sha256':bound}}
  (child/'score.provenance.json').write_text(json.dumps(score));return child,score,parent
 def run_case(self,mutate=None,pattern=None):
  with tempfile.TemporaryDirectory() as d:
   folder,score,parent=self.fixture(pathlib.Path(d))
   if mutate:
    mutate(score,folder,parent);(folder/'score.provenance.json').write_text(json.dumps(score))
    with self.assertRaisesRegex(ValueError,pattern or '.'):
     rights_audit.audit(folder,ROOT)
   else:
    result=rights_audit.audit(folder,ROOT);self.assertFalse(result['publication_authorized']);self.assertIn('listening', ' '.join(result['remaining_review']).lower())
 def test_v14_bound_inventory_is_recognized_without_granting_publication(self):self.run_case()
 def test_stale_parent_binding_is_rejected(self):self.run_case(lambda s,f,p:s['retime'].__setitem__('parent_score_sha256','0'*64),'parent binding')
 def test_helper_source_binding_is_rejected(self):self.run_case(lambda s,f,p:s['bound_source_sha256'].__setitem__(str((ROOT/'retime_score.py').resolve()),'0'*64),'source bindings')
 def test_revoiced_parent_note_is_rejected(self):self.run_case(lambda s,f,p:s['events'][0].__setitem__('velocity',.8),'revoiced|inventory|arrangement')
 def test_moved_note_attack_is_rejected(self):self.run_case(lambda s,f,p:s['events'][0].__setitem__('time',3.1),'attack|event|mapping|retim')
 def test_stale_event_mapping_is_rejected(self):self.run_case(lambda s,f,p:s['retime']['event_mapping'][0].__setitem__('old_time',2.2),'attack|event|mapping|retim')
 def test_arbitrary_map_cannot_replace_actual_word_anchor(self):
  def mutate(score,folder,parent):
   for point in score['retime']['timeline_points']:
    if point['old']==4:point['new']=5.5
   old=json.loads((parent/'score.provenance.json').read_text());points=score['retime']['timeline_points'];score['events'],score['retime']['event_mapping']=retime_score.preserve_events(old['events'],points,12);score['quiet_intervals']=retime_score.map_intervals(old['quiet_intervals'],points)
  self.run_case(mutate,'anchor|timeline|semantic|retim')
 def test_declared_duration_cannot_disagree_with_actual_timeline(self):self.run_case(lambda s,f,p:s.__setitem__('seconds',13),'duration|timeline|length')
 def test_stale_voice_binding_is_rejected(self):self.run_case(lambda s,f,p:s['retime'].__setitem__('narration_sha256','0'*64),'voice binding')

class RetimeAutomationRegistrationTests(unittest.TestCase):
 def test_v14_actual_reentry_uses_short_quintic_source_family(self):
  import array,wave
  from music_automation import apply
  from audio_balance import samples
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);rate=24000
   for name,values in [('narration.wav',array.array('h',[3277])*(rate*3)),('score-ducked.wav',array.array('h',[0])*rate+array.array('h',[33])*(rate*2))]:
    with wave.open(str(p/name),'wb') as f:f.setparams((1,2,rate,0,'NONE','not compressed'));f.writeframes(values.tobytes())
   (p/'episode.json').write_text(json.dumps({'music':{}}));(p/'score.provenance.json').write_text(json.dumps({'version':retime_score.VERSION}))
   apply(p,[{'time':0,'gain_db':0},{'time':3,'gain_db':0}]);report=json.loads((p/'music-automation.json').read_text())
   self.assertEqual(report['transition_check']['reentry_fade_seconds'],.25);self.assertEqual(report['reentry_shape'],'smootherstep')
   before=samples(p/'score-ducked-before-automation.wav');after=samples(p/'score-ducked.wav')
   self.assertEqual(max(abs(v) for v in after[:rate//2]),0)
   index=round(1.125*rate);self.assertAlmostEqual(after[index]/before[index],.5,delta=.02)

if __name__=='__main__':unittest.main()
