import unittest
from scripts.check_scaling_readiness import assess
class AdmissionTests(unittest.TestCase):
 def test_observed_false_flags_hold(self):
  r=assess({'MULTI_REPLICA_ENABLED':False,'REDIS_CACHE_ENABLED':False,'WEB_CONCURRENCY':1,'MONGODB_MAX_POOL_SIZE':8},2);self.assertEqual(r['status'],'HOLD');self.assertEqual(r['basePoolArithmeticOnly'],16)
 def test_one_replica_is_not_capacity_pass(self):self.assertEqual(assess({},1)['status'],'UNQUALIFIED')
 def test_configured_shared_state_not_runtime_pass(self):self.assertEqual(assess({'MULTI_REPLICA_ENABLED':True,'REDIS_CACHE_ENABLED':True},2)['status'],'UNQUALIFIED')
 def test_one_shared_backend_flag_is_configured_only(self):self.assertEqual(assess({'MULTI_REPLICA_ENABLED':False,'REDIS_CACHE_ENABLED':True},2)['status'],'UNQUALIFIED')
 def test_strings_false_not_truthy(self):self.assertEqual(assess({'MULTI_REPLICA_ENABLED':'false','REDIS_CACHE_ENABLED':'false'},2)['status'],'HOLD')
 def test_missing_flags_unknown(self):self.assertIn('SHARED_STATE_FLAGS_UNKNOWN',[x['code'] for x in assess({},2)['findings']])
 def test_bad_replica_unknown(self):self.assertIn('REPLICA_COUNT_UNKNOWN',[x['code'] for x in assess({},True)['findings']])
 def test_missing_limits_explicit(self):self.assertEqual(sum(x['code']=='LIMIT_UNKNOWN' for x in assess({},1)['findings']),7)
 def test_invalid_autoscaler_range(self):self.assertEqual(assess({},1,{'autoscaler_min_replicas':3,'autoscaler_max_replicas':2})['status'],'HOLD')
 def test_boolean_quota_rejected(self):self.assertTrue(any(x.get('field')=='database_connection_quota' for x in assess({},1,{'database_connection_quota':True})['findings']))
 def test_complete_metadata_still_not_capacity(self):
  limits={'autoscaler_min_replicas':1,'autoscaler_max_replicas':2,'autoscaler_cooldown_seconds':0,'database_connection_quota':100,'redis_maxmemory_bytes':64,'redis_maxclients':256,'redis_eviction_policy':'noeviction'}
  self.assertEqual(assess({'MULTI_REPLICA_ENABLED':True,'REDIS_CACHE_ENABLED':True},2,limits)['status'],'UNQUALIFIED')
if __name__=='__main__':unittest.main()
