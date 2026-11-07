"""Invocation-only digest reuse; fixture decisions never approve real media."""
from collections import Counter
import json,os,pathlib,sys,tempfile,unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import strict_quality as q
import test_strict_quality as fixtures


class StrictHashCacheTests(unittest.TestCase):
 def fixture(self,p,pending=False,many=False):
  fixtures.StrictQualityTests().fixture(p)
  if many:
   props=q.load(p/'props.json');props['scenes'][0]['anchors']=[{'time':(i+1)/19*2} for i in range(17)]
   (p/'props.json').write_text(json.dumps(props));manifest=q.load(p/'delivery-manifest.json');manifest['props.json']=q.sha(p/'props.json');(p/'delivery-manifest.json').write_text(json.dumps(manifest))
  if pending:q.reset(p)
 def fake_extract(self,args,**kwargs):pathlib.Path(args[-1]).write_bytes(b'\x89PNG\r\n\x1a\nISOLATED CAPTURE TEST ONLY')
 def counting(self,counts):
  original=q._uncached_sha
  def digest(path):counts[pathlib.Path(path).name]+=1;return original(path)
  return digest
 def test_repeated_media_and_source_references_hash_once_per_validation_only(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p);counts=Counter()
   with patch.object(q,'_uncached_sha',side_effect=self.counting(counts)):
    result=q.validate(p)
    for name in ['landscape.mp4','portrait-captioned.mp4','source.txt','frame.png']:self.assertEqual(counts[name],1,name)
    self.assertFalse(result['publication_approval']);q.validate(p)
    for name in ['landscape.mp4','portrait-captioned.mp4','source.txt','frame.png']:self.assertEqual(counts[name],2,name)
 def test_more_than_one_hundred_captured_samples_hash_each_mp4_once_and_stay_pending(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p,pending=True,many=True);counts=Counter()
   with patch.object(q,'_uncached_sha',side_effect=self.counting(counts)),patch('subprocess.run',side_effect=self.fake_extract):result=q.capture(p)
   self.assertGreater(result['frames'],100)
   for name in ['landscape.mp4','portrait-captioned.mp4']:self.assertEqual(counts[name],1,name)
   review=q.load(p/q.NAME)
   self.assertEqual(result['all_decisions'],'PENDING');self.assertEqual(review['factual']['decision'],'PENDING')
   self.assertTrue(all(row['verdict']=='PENDING' and row['evidence'] for row in review['graphical']['frames'].values()))
 def test_standalone_evidence_call_uses_one_scoped_cache(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'proof.txt').write_text('ISOLATED EVIDENCE ONLY');ref={'path':'proof.txt','sha256':q.sha(p/'proof.txt')};counts=Counter()
   with patch.object(q,'_uncached_sha',side_effect=self.counting(counts)):
    self.assertIsNone(q.evidence(p,[ref]*8));self.assertEqual(counts['proof.txt'],1)
    q.evidence(p,[ref]);self.assertEqual(counts['proof.txt'],2)
 def test_reused_media_mutation_is_rejected_without_changing_review(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p);before=(p/q.NAME).read_bytes();original=q.verdict;changed=False
   def mutate(folder,row,frame=False):
    nonlocal changed
    result=original(folder,row,frame)
    if frame and not changed:
     changed=True
     with (p/'landscape.mp4').open('ab') as stream:stream.write(b'CHANGED')
    return result
   with patch.object(q,'verdict',side_effect=mutate),self.assertRaisesRegex(ValueError,'changed during strict quality'):q.validate(p)
   self.assertEqual((p/q.NAME).read_bytes(),before)
 def test_same_size_and_mtime_replacement_is_rejected_by_file_identity(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p);original=q.verdict;changed=False
   def replace(folder,row,frame=False):
    nonlocal changed
    result=original(folder,row,frame)
    if frame and not changed:
     changed=True;source=p/'landscape.mp4';previous=source.stat();replacement=p/'replacement'
     replacement.write_bytes(source.read_bytes());os.utime(replacement,ns=(previous.st_atime_ns,previous.st_mtime_ns));os.replace(replacement,source)
    return result
   with patch.object(q,'verdict',side_effect=replace),self.assertRaisesRegex(ValueError,'changed during strict quality'):q.validate(p)
 def test_end_guard_catches_mutation_after_the_last_media_reference(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p);original=q.nonblank;devices=0
   def mutate(value):
    nonlocal devices
    result=original(value)
    if value=='TEST FIXTURE':
     devices+=1
     if devices==2:
      with (p/'landscape.mp4').open('ab') as stream:stream.write(b'AFTER LAST MEDIA REFERENCE')
    return result
   with patch.object(q,'nonblank',side_effect=mutate),self.assertRaisesRegex(ValueError,'changed during strict quality'):q.validate(p)
 def test_capture_checks_unchanged_inputs_before_persisting_frame_evidence(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p,pending=True);before=(p/q.NAME).read_bytes();total=len(q.plan(p)['frames']);extracted=0
   def mutate_at_end(args,**kwargs):
    nonlocal extracted
    self.fake_extract(args,**kwargs);extracted+=1
    if extracted==total:
     with (p/'landscape.mp4').open('ab') as stream:stream.write(b'CHANGED AFTER LAST LANDSCAPE FRAME')
   with patch('subprocess.run',side_effect=mutate_at_end),self.assertRaisesRegex(ValueError,'changed during strict quality'):q.capture(p)
   self.assertEqual((p/q.NAME).read_bytes(),before)
   self.assertTrue(all(row['verdict']=='PENDING' and not row['evidence'] for row in q.load(p/q.NAME)['graphical']['frames'].values()))
 def test_generated_frame_content_change_is_rejected_before_commit(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p,pending=True);before=(p/q.NAME).read_bytes();total=len(q.plan(p)['frames']);extracted=[]
   def mutate_frame(args,**kwargs):
    self.fake_extract(args,**kwargs);extracted.append(pathlib.Path(args[-1]))
    if len(extracted)==total:extracted[0].write_bytes(b'CHANGED FRAME')
   with patch('subprocess.run',side_effect=mutate_frame),self.assertRaisesRegex(ValueError,'Generated frame changed'):q.capture(p)
   self.assertEqual((p/q.NAME).read_bytes(),before)
 def test_hash_error_resets_scope_and_never_grants_approval(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p,pending=True);before=(p/q.NAME).read_bytes();original=q._uncached_sha
   def fail(path):
    if pathlib.Path(path).name=='landscape.mp4':raise OSError('ISOLATED HASH FAILURE')
    return original(path)
   with patch.object(q,'_uncached_sha',side_effect=fail),self.assertRaisesRegex(OSError,'HASH FAILURE'):q.capture(p)
   self.assertIsNone(q._HASH_SESSION.get());self.assertEqual((p/q.NAME).read_bytes(),before)
   with patch('subprocess.run',side_effect=self.fake_extract):self.assertEqual(q.capture(p)['all_decisions'],'PENDING')


if __name__=='__main__':unittest.main()
