import io,tempfile,unittest
from pathlib import Path
import audiobook_upload_budget as b
class Tests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'ledger.json'
 def tearDown(self):self.tmp.cleanup()
 def test_reserve_before_mutation_and_no_retry_after_reopen(self):
  with b.Budget(self.path,'dummy',versions=1,upload_bytes=3) as budget:
   b.before_call('put_object',{'Bucket':'dummy','Key':'object','ContentLength':3})
   self.assertEqual(budget.state['used']['versions'],1)
  with b.Budget(self.path,'dummy',versions=1,upload_bytes=3):
   with self.assertRaises(b.BudgetError):b.before_call('put_object',{'Bucket':'dummy','Key':'object','ContentLength':3})
 def test_overflow_no_reservation(self):
  with b.Budget(self.path,'dummy',requests=1) as budget:
   budget.reserve(requests=1)
   with self.assertRaises(b.BudgetError):budget.reserve(requests=1)
   self.assertEqual(budget.state['used']['requests'],1)
 def test_download_over_budget_closes_without_read(self):
  body=io.BytesIO(b'abc')
  with b.Budget(self.path,'dummy',download_bytes=2):
   with self.assertRaises(b.BudgetError):b.after_call('get_object',{'ContentLength':3,'Body':body})
  self.assertTrue(body.closed)
 def test_body_bound(self):
  with b.Budget(self.path,'dummy',download_bytes=3) as budget:
   r=b.after_call('get_object',{'ContentLength':3,'Body':io.BytesIO(b'abc')})
   self.assertEqual(r['Body'].read(100),b'abc');self.assertEqual(r['Body'].read(),b'')
   self.assertEqual(budget.state['used']['download_bytes'],3)
 def test_exclusive_lock(self):
  with b.Budget(self.path,'dummy'):
   with self.assertRaises(BlockingIOError):b.Budget(self.path,'dummy')
 def test_identity_drift(self):
  with b.Budget(self.path,'dummy'):pass
  with self.assertRaises(b.BudgetError):b.Budget(self.path,'other')
 def test_forbidden_mutation(self):
  with b.Budget(self.path,'dummy'):
   with self.assertRaises(b.BudgetError):b.before_call('delete_object',{})
 def test_negative_limit(self):
  with self.assertRaises(b.BudgetError):b.Budget(self.path,'dummy',versions=-1)
 def test_partial_failure_consumes_budget(self):
  with b.Budget(self.path,'dummy',versions=1) as budget:
   b.before_call('put_object',{'Bucket':'dummy','Key':'x','ContentLength':1})
   with self.assertRaises(b.BudgetError):b.before_call('put_object',{'Bucket':'dummy','Key':'y','ContentLength':1})
 def test_plan_budget_requires_argument(self):
  import audiobook_package_storage_v2 as a
  with self.assertRaises(SystemExit):a.build_parser().parse_args(['upload','--plan','dummy'])

 def test_stored_byte_limit_independent_of_versions(self):
  with b.Budget(self.path,'dummy',upload_bytes=2,versions=10):
   with self.assertRaises(b.BudgetError):b.before_call('put_object',{'Bucket':'dummy','Key':'x','ContentLength':3})
 def test_metadata_limit(self):
  with b.Budget(self.path,'dummy',metadata_bytes=1) as budget:
   budget.reserve(metadata_bytes=1)
   with self.assertRaises(b.BudgetError):budget.reserve(metadata_bytes=1)
 def test_raw_adapter_put_without_budget_stops(self):
  import audiobook_package_storage_v2 as a
  with self.assertRaises(a.StorageSafetyError):a._put_asset(None,None,None,None,None)

 def test_unknown_operation_denied(self):
  with b.Budget(self.path,'dummy'):
   with self.assertRaises(b.BudgetError):b.before_call('put_bucket_policy',{})
 def test_corrupt_mutation_history_denied(self):
  import json
  with b.Budget(self.path,'dummy'):pass
  state=json.loads(self.path.read_text());state['used']['versions']=1
  self.path.write_text(json.dumps(state))
  with self.assertRaises(b.BudgetError):b.Budget(self.path,'dummy')
 def test_gateway_put_without_budget_denied(self):
  with self.assertRaises(b.BudgetError):b.before_call('put_object',{})
