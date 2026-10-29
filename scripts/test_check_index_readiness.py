import unittest
import json,subprocess,sys,tempfile
from pathlib import Path
from scripts.check_index_readiness import assess,normalize
class IndexTests(unittest.TestCase):
 def decl(self,key=None,**opts):return {'collection':'fixture','key':key or [['id',1]],'options':opts}
 def meta(self,key=None,**opts):return {'collections':{'fixture':[{'name':'idx','key':key or [['id',1]],**opts}]}}
 def test_matching_unique(self):self.assertFalse(assess([self.decl(unique=True)],self.meta(unique=True))['missing'])
 def test_wrong_unique_not_accepted(self):self.assertEqual(assess([self.decl(unique=True)],self.meta())['missing'][0]['state'],'HOLD_UNIQUE_OR_RETENTION')
 def test_partial_filter_mismatch(self):self.assertTrue(assess([self.decl(unique=True,partialFilterExpression={'status':'active'})],self.meta(unique=True))['missing'])
 def test_sparse_mismatch(self):self.assertTrue(assess([self.decl(sparse=True)],self.meta())['missing'])
 def test_compound_order_matters(self):self.assertTrue(assess([self.decl([['a',1],['b',1]])],self.meta([['b',1],['a',1]]))['missing'])
 def test_unknown_collection_not_assumed_empty(self):self.assertEqual(assess([self.decl()],{})['unknown'][0]['reason'],'NO_ACTUAL_METADATA')
 def test_name_not_semantics(self):self.assertFalse(assess([self.decl()],self.meta())['missing'])
 def test_ttl_never_ignored(self):self.assertEqual(assess([self.decl(expireAfterSeconds=60)],self.meta())['missing'][0]['state'],'HOLD_UNIQUE_OR_RETENTION')
 def test_no_auto_drop(self):
  m={'collections':{'fixture':[{'name':'a','key':[['a',1]]},{'name':'ab','key':[['a',1],['b',1]]}]}}
  self.assertEqual(assess([],m)['potentialRedundantPrefixes'][0]['action'],'REVIEW_USAGE_AND_COST_ONLY_NO_DROP_AUTHORITY')
 def test_unique_prefix_protected(self):
  m={'collections':{'fixture':[{'name':'a','key':[['a',1]],'unique':True},{'name':'ab','key':[['a',1],['b',1]]}]}}
  self.assertFalse(assess([],m)['potentialRedundantPrefixes'])
 def test_no_runtime_capacity_claim(self):self.assertEqual(assess([self.decl()],self.meta())['queryPlanner'],'UNVERIFIED_NO_EXPLAIN_EXECUTION')
 def test_malformed_key_unknown(self):self.assertIsNone(normalize({'key':{'bad':1}}))
 def test_collation_difference_never_matches_unique_index(self):
  self.assertTrue(assess([self.decl(unique=True,collation={'locale':'en','strength':2})],self.meta(unique=True,collation={'locale':'en','strength':3}))['missing'])
 def test_matching_collation(self):
  c={'locale':'en','strength':2}
  self.assertFalse(assess([self.decl(unique=True,collation=c)],self.meta(unique=True,collation=c))['missing'])
 def test_binary_default_and_explicit_simple_collation_match(self):
  self.assertFalse(assess([self.decl()],self.meta(collation={'locale':'simple'}))['missing'])
 def test_cli_supports_array_and_wrapped_declarations(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);actual=root/'actual.json';actual.write_text(json.dumps(self.meta()))
   for payload in ([self.decl()],{'indexes':[self.decl()]}):
    declared=root/'declared.json';declared.write_text(json.dumps(payload));output=root/'result.json'
    run=subprocess.run([sys.executable,str(Path(__file__).with_name('check_index_readiness.py')),'--declared',str(declared),'--actual',str(actual),'--output',str(output)],capture_output=True,text=True,timeout=5)
    self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(len(json.loads(output.read_text())['matched']),1)
 def test_cli_rejects_invalid_declaration_shape_without_result(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);declared=root/'declared.json';declared.write_text('{}');actual=root/'actual.json';actual.write_text('{}');output=root/'result.json'
   run=subprocess.run([sys.executable,str(Path(__file__).with_name('check_index_readiness.py')),'--declared',str(declared),'--actual',str(actual),'--output',str(output)],capture_output=True,text=True,timeout=5)
   self.assertEqual(run.returncode,2);self.assertFalse(output.exists())
if __name__=='__main__':unittest.main()
