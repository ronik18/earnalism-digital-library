import unittest,tempfile,pathlib,json,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from review_index import resolve,digest
class ReviewIndexTests(unittest.TestCase):
 def setup_record(self,root):
  evidence=root/'evidence';evidence.mkdir();folder=root/'candidate';folder.mkdir();files={}
  for n in ('watch.html','portrait-short.html','participant.html','participant-shorts.html'):
   (folder/n).write_text(n);files[n]=digest(folder/n)
  (folder/'delivery-manifest.json').write_text(json.dumps(files));kit=evidence/'kit.md';kit.write_text('Neutral reviewer kit')
  record=evidence/'current.json';data={'private':True,'candidate':'candidate','delivery_manifest_sha256':digest(folder/'delivery-manifest.json'),'review_kit':'evidence/kit.md','review_kit_sha256':digest(kit),'base_url':'http://127.0.0.1:8796'};record.write_text(json.dumps(data));return record,data
 def test_resolves_without_granting_approval_and_rejects_changed_media_page(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);record,data=self.setup_record(root);self.assertFalse(resolve(record)['publication_approval']);(root/'candidate/watch.html').write_text('Changed')
   with self.assertRaisesRegex(ValueError,'Candidate files changed'):resolve(record)
 def test_rejects_remote_url_and_stale_kit(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);record,data=self.setup_record(root);data['base_url']='https://example.com';record.write_text(json.dumps(data))
   with self.assertRaisesRegex(ValueError,'Loopback'):resolve(record)
   data['base_url']='http://127.0.0.1:8796';record.write_text(json.dumps(data));(root/'evidence/kit.md').write_text('Changed')
   with self.assertRaisesRegex(ValueError,'Review kit changed'):resolve(record)
 def test_rejects_stale_manifest_binding(self):
  with tempfile.TemporaryDirectory() as d:
   record,data=self.setup_record(pathlib.Path(d));data['delivery_manifest_sha256']='0'*64;record.write_text(json.dumps(data))
   with self.assertRaisesRegex(ValueError,'Stale candidate'):resolve(record)
