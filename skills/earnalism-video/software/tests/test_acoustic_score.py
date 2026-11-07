import pathlib,sys,unittest,tempfile,json,hashlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from acoustic_score import plan,validate_assets,ASSETS
class AcousticScoreTests(unittest.TestCase):
 def test_real_assets_have_licensed_hashes_and_matching_octaves(self):
  m=validate_assets();p=next(x for x in m['samples'] if x['instrument']=='piano' and x['key']=='D3');h=next(x for x in m['samples'] if x['instrument']=='harp' and x['key']=='D4');self.assertEqual(p['root_midi'],h['root_midi']);self.assertEqual(m['license'],'CC0-1.0')
 def test_changed_sample_fails_even_when_filename_is_unchanged(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);m={'license':'CC0-1.0','revision':'c1ea7bcc3c7309650ab0da9d15c9cd1fbc4a4c7e','samples':[{'file':'note.wav','sha256':hashlib.sha256(b'original').hexdigest()}],'documents':[]};(p/'manifest.json').write_text(json.dumps(m));(p/'note.wav').write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'hash mismatch'):validate_assets(p)
 def test_plan_retains_definition_silence_and_motif_return(self):
  scenes=[{'diagram':'sunlight','start':8,'end':22},{'diagram':'phases','start':37,'end':51,'anchors':[{'phrase':'At first quarter','time':41},{'phrase':'Near full Moon','time':46}]},{'diagram':'cycle','start':66,'end':78}];events,quiet=plan(88,scenes)
  self.assertTrue(any(a<=41 and b>=45 for a,b in quiet));question=[e['midi'] for e in events if e['phrase']=='question: D A E F'];answer=[e['midi'] for e in events if e['phrase']=='return: F E A D'];self.assertEqual(question,[62,69,64,65]);self.assertEqual(answer,list(reversed(question)));self.assertTrue(all(0<=e['time']<88 for e in events))
 def test_requested_notes_are_close_to_actual_recorded_pitches(self):
  m=validate_assets();scenes=[{'diagram':k,'start':i*12,'end':i*12+12} for i,k in enumerate(['question','sunlight','orbit','phases','eclipse','cycle','callback'])];events,_=plan(88,scenes)
  for e in events:self.assertLessEqual(min(abs(s['root_midi']-e['midi']) for s in m['samples'] if s['instrument']==e['instrument']),2)
 def test_quiet_extends_through_added_quarter_reasoning(self):
  scenes=[{'diagram':'phases','start':37,'end':58,'anchors':[{'phrase':'At first quarter','time':41},{'phrase':'First quarter means','time':46},{'phrase':'Near full Moon','time':53}]}]
  _,quiet=plan(90,scenes)
  self.assertTrue(any(a<=41 and b>=52.6 for a,b in quiet))
