import pathlib,sys,unittest,copy,tempfile,json,wave,array
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import editorial_score as editorial
import final_chamber_score as base

class EditorialScoreTests(unittest.TestCase):
 def test_only_nearby_support_and_returning_a4_are_attenuated(self):
  def note(t,phrase,midi=62,gain=0,instrument='piano'):
   return {'time':t,'phrase':phrase,'midi':midi,'arrangement_gain_db':gain,'instrument':instrument,'velocity':.2,'duration':3,'pan':0}
  source=[note(1,'question: D A E F'),note(1.1,'soft harmonic support'),note(1.31,'soft harmonic support'),note(2,'return: F E A D',69,1.5),note(2.8,'other A4',69)]
  saved=copy.deepcopy(source);out=editorial.adjust_events(source)
  self.assertEqual(source,saved)
  self.assertEqual([e['arrangement_gain_db'] for e in out],[0,-2,0,.5,0])
  for a,b in zip(source,out):
   self.assertEqual({k:v for k,v in a.items() if k!='arrangement_gain_db'},{k:v for k,v in b.items() if k not in ['arrangement_gain_db','editorial_gain_db','editorial_reason']})
 def test_no_unplanned_global_gain_or_new_events(self):
  events,_=base.plan(80,[{'diagram':'sunlight','start':6,'end':15},{'diagram':'cycle','start':50,'end':60}])
  for e in events:e['arrangement_gain_db']=0
  out=editorial.adjust_events(events)
  self.assertEqual(len(events),len(out))
  self.assertTrue(all(b['arrangement_gain_db']<=a['arrangement_gain_db'] for a,b in zip(events,out)))
 def test_missing_base_dynamics_is_rejected(self):
  with self.assertRaisesRegex(ValueError,'Base written dynamics'):editorial.adjust_events([{'time':1,'phrase':'soft harmonic support'}])
 def test_actual_composition_retains_licensed_assets_silence_and_provenance(self):
  scenes=[{'diagram':'question','start':0,'end':1},{'diagram':'sunlight','start':1,'end':7},{'diagram':'callback','start':7,'end':12}]
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);old=root/'base';new=root/'editorial';old.mkdir();new.mkdir()
   a=base.compose(old/'score.wav',12,[(2,2.3)],scenes=scenes)
   b=editorial.compose(new/'score.wav',12,[(2,2.3)],scenes=scenes)
   self.assertEqual(a['version'],'moon-score-v11-body-refinement')
   self.assertEqual(b['version'],editorial.VERSION)
   self.assertEqual(b['license'],'CC0-1.0')
   self.assertEqual(a['quiet_intervals'],b['quiet_intervals'])
   self.assertEqual(a['asset_manifest_sha256'],b['asset_manifest_sha256'])
   self.assertEqual(b['composition_source_sha256'],base.sha(pathlib.Path(editorial.__file__)))
   self.assertEqual(b['base_composition_source_sha256'],base.sha(pathlib.Path(base.__file__)))
   self.assertEqual(b['recording_sha256'],base.sha(new/'score.wav'))
   self.assertTrue(b['editorial_adjustments'])
   for folder in [old,new]:
    with wave.open(str(folder/'score.wav')) as w:
     rate=w.getframerate();channels=w.getnchannels();pcm=array.array('h',w.readframes(w.getnframes()))
    if sys.byteorder!='little':pcm.byteswap()
    for start,end in [(0,.9),(2.05,2.25),(7.1,9.9)]:
     self.assertEqual(max(abs(v) for v in pcm[round(start*rate)*channels:round(end*rate)*channels]),0)
   with self.assertRaises(FileExistsError):editorial.compose(new/'score.wav',12,scenes=scenes)
 def test_hook_cannot_change_pitch_or_note_timing(self):
  from unittest.mock import patch
  def invalid(events,scenes):
   events[0]['midi']+=1;return events
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(ValueError,'source content or timing'):
    base.compose(pathlib.Path(d)/'reject.wav',10,scenes=[{'diagram':'sunlight','start':1,'end':8}],event_adjuster=invalid)
   self.assertFalse((pathlib.Path(d)/'reject.wav').exists())
