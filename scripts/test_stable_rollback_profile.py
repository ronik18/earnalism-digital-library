"""Recovery-role admission must reproduce the actual server's Redis defaults."""
import os,unittest
from unittest.mock import patch
from scripts.qualify_stable_rollback_profile import ROOT,qualify,effective_redis_flags
FLAGS=('REDIS_CACHE_ENABLED','REDIS_PUBLIC_METADATA_ENABLED','MULTI_REPLICA_ENABLED')
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.source=(ROOT/'backend/server.py').read_text()
 def test_actual_role_admits_explicit_off_with_url(self):
  with patch.dict(os.environ,{**dict.fromkeys(FLAGS,'false'),'REDIS_URL':'redis://127.0.0.1:26379/0'}):self.assertTrue(qualify()['source_verified'])
 def test_missing_cache_flag_with_url_is_effectively_on(self):
  self.assertTrue(effective_redis_flags(self.source,{'REDIS_URL':'redis://127.0.0.1:26379/0'})['REDIS_CACHE_ENABLED'])
  with patch.dict(os.environ,{**dict.fromkeys(FLAGS,'false'),'REDIS_URL':'redis://127.0.0.1:26379/0'}):
   os.environ.pop('REDIS_CACHE_ENABLED')
   with self.assertRaisesRegex(ValueError,'Redis must remain OFF'):qualify()
 def test_missing_all_without_url_has_actual_off_defaults(self):
  self.assertFalse(any(effective_redis_flags(self.source,{}).values()))
 def test_absent_opt_ins_do_not_require_new_production_variables(self):
  self.assertFalse(any(effective_redis_flags(self.source,{'REDIS_CACHE_ENABLED':'false','REDIS_URL':'redis://127.0.0.1:26379/0'}).values()))
 def test_blank_unknown_and_true_are_effectively_on(self):
  for flag in FLAGS:
   for value in ('','garbage','true','1','yes','on'):
    with self.subTest(flag=flag,value=value):
     env={**dict.fromkeys(FLAGS,'false'),flag:value}
     self.assertTrue(effective_redis_flags(self.source,env)[flag])
 def test_environment_access_is_limited_to_four_keys(self):
  class Limited(dict):
   def get(self,key,default=None):
    if key not in {*FLAGS,'REDIS_URL'}:raise AssertionError('Nonallowlisted environment read')
    return super().get(key,default)
  out=effective_redis_flags(self.source,Limited(dict.fromkeys(FLAGS,'false')))
  self.assertEqual(set(out),set(FLAGS));self.assertFalse(any(out.values()))
if __name__=='__main__':unittest.main()
