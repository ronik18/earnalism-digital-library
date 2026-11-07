import unittest,copy,tempfile
from pathlib import Path
from .review_audio import targets_for,authored_context,merge_targets,prepare
class AudioReviewTests(unittest.TestCase):
 def test_every_flag_and_rest_edge_covered_without_clearing(self):
  flags=[{'start':12.,'gap_db':40},{'start':44.,'gap_db':12}]
  out=targets_for({'passage_issues':flags},[{'start':0,'end':10,'reason':'opening'},{'start':65,'end':70,'reason':'ending'}],71.28)
  self.assertEqual({x['flag_start'] for x in out if 'flag_start' in x},{12.,44.})
  self.assertEqual(len(out),5)
  self.assertTrue(all(0<=x['start']<x['end']<=71.28 for x in out))
  self.assertEqual(flags[1]['gap_db'],12)
 def test_authored_shoulders_add_context_without_clearing_raw_flags(self):
  screen={'passage_issues':[{'start':14.,'gap_db':40.47},{'start':23.,'gap_db':34.25}],
          'issues':['Post-ducking median music/voice gap outside 18–28 dB review band'],
          'passage_review_band_db':[16,32]};before=copy.deepcopy(screen)
  plan={'rests':[{'start':0.,'end':12.34,'reason':'opening'}], 'fade_in_seconds':4.5,'fade_out_seconds':3.2,
        'events':[{'time':12.89,'duration':5.8,'instrument':'piano'},{'time':21.15,'duration':3.8,'instrument':'harp'}]}
  context=authored_context(screen,plan,30.,False)
  self.assertEqual(screen,before);self.assertEqual(context['raw_flags'],screen['passage_issues'])
  self.assertEqual(context['state'],'AVAILABLE');self.assertEqual(context['listening'],'PENDING');self.assertFalse(context['flags_resolved'])
  self.assertEqual(context['flags'][0]['authored_shoulder_overlaps'][0]['end'],16.84)
  self.assertEqual(context['flags'][1]['authored_shoulder_overlaps'],[])
  self.assertEqual(context['flags'][1]['declared_note_spans'][0]['onset'],21.15)
  self.assertTrue(context['display_issues'][0].startswith('Delivered score'))
  for stage in (None,True):self.assertEqual(authored_context(screen,plan,30.,stage)['display_issues'],screen['issues'])
 def test_unknown_legacy_plan_stays_unavailable_without_resolving_flags(self):
  screen={'passage_issues':[{'start':14.,'gap_db':40.47}]}
  for plan in (None,{}, {'rests':[]}, {'rests':[],'fade_in_seconds':4.5,'fade_out_seconds':3.2,'events':[{'time':'unknown','duration':3}]}):
   context=authored_context(screen,plan,30.)
   self.assertEqual(context['state'],'UNAVAILABLE');self.assertFalse(context['flags_resolved'])
   self.assertEqual(context['raw_flags'],screen['passage_issues']);self.assertEqual(context['listening'],'PENDING')
 def test_merging_preserves_every_raw_interval_reason_and_flag(self):
  raw=[{'start':1.,'end':4.,'reason':'flag A','flag_start':2.},
       {'start':3.,'end':7.,'reason':'authored return'},
       {'start':6.,'end':8.,'reason':'flag B','flag_start':7.},
       {'start':10.,'end':12.,'reason':'flag C','flag_start':11.}];before=copy.deepcopy(raw)
  out=merge_targets(raw);self.assertEqual(raw,before);self.assertEqual(len(out),2)
  self.assertEqual((out[0]['start'],out[0]['end']),(1.,8.))
  self.assertEqual([i for group in out for i in group['source_indices']],list(range(len(raw))))
  self.assertEqual([x for group in out for x in group['flag_starts']],[2.,7.,11.])
  for group in out:
   for i in group['source_indices']:
    self.assertLessEqual(group['start'],raw[i]['start']);self.assertGreaterEqual(group['end'],raw[i]['end']);self.assertIn(raw[i]['reason'],group['reason'])
 def test_existing_review_files_are_never_rewritten(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);report=root/'music-screen.json';report.write_text('preserved historical evidence')
   with self.assertRaises(ValueError):prepare(root)
   self.assertEqual(report.read_text(),'preserved historical evidence');self.assertFalse((root/'listening-targets.json').exists())
if __name__=='__main__':unittest.main()
