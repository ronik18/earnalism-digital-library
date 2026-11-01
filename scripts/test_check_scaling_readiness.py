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

import copy
import unittest
from scripts.check_scaling_readiness import assess, connection_envelope, controller_evidence


def cohort(replicas=10, workers=1, role='current_web'):
    return {'role': role, 'replicas': replicas, 'workers_per_replica': workers, 'clients_per_worker': 1,
            'pool_per_client_per_node': 8, 'monitoring_sockets_per_client_per_node': 2}


def limits():
    return {'autoscaler_max_replicas': 10, 'database_connection_quota': 500, 'database_connection_budget': {
        'nodes': 3, 'other_connections_per_node': 20, 'reserve_connections_per_node': 50,
        'observed_running_replicas': 10, 'max_current_web_replicas': 10, 'max_replacement_replicas': 10,
        'cohorts': [cohort(), cohort(role='replacement_web')],
        'additional_replica': {k: v for k, v in cohort().items() if k not in {'replicas', 'role'}}}}


TARGET = {'project_id': 'a8533934-35c4-463e-9f43-577a9ac391ee',
          'environment_id': '580b250c-80ee-48ad-bfbe-fa4e31a6b378',
          'service_id': '5af42e7e-f518-4f6a-b602-d9950866501f'}


class HeadroomTests(unittest.TestCase):
    def test_pinned_driver_monitoring_cannot_be_understated(self):
        value = limits()
        value['database_connection_budget']['cohorts'][0]['monitoring_sockets_per_client_per_node'] = 1
        self.assertEqual(connection_envelope({}, value)['status'], 'UNKNOWN')
        value = limits()
        value['database_connection_budget']['additional_replica']['monitoring_sockets_per_client_per_node'] = 1
        self.assertIsNone(connection_envelope({}, value)['maxAdditionalReplicas'])

    def test_old_new_and_monitoring_counted_per_node(self):
        r = connection_envelope({}, limits())
        self.assertEqual(r['applicationPerNodeUpperBound'], 200)
        self.assertEqual(r['allNodeApplicationUpperBound'], 600)
        self.assertEqual(r['totalPerNodeWithReserve'], 270)
        self.assertEqual(r['headroomPerNodeAfterReserve'], 230)
        self.assertEqual(r['maxAdditionalReplicas'], 23)
        self.assertTrue(r['metadataEnvelopeWithinQuota'])
        self.assertFalse(r['runtimeAdmission'])

    def test_three_worker_overlap_exceeds_even_without_other_clients(self):
        value = limits(); value['database_connection_budget']['cohorts'] = [cohort(workers=3), cohort(workers=3, role='replacement_web')]
        r = connection_envelope({}, value)
        self.assertEqual(r['status'], 'OVER_QUOTA')
        self.assertFalse(r['metadataEnvelopeWithinQuota'])
        self.assertEqual(r['maxAdditionalReplicas'], 0)
        self.assertEqual(assess({}, 10, value)['status'], 'HOLD')

    def test_unknown_other_clients_never_becomes_zero(self):
        value = limits(); del value['database_connection_budget']['other_connections_per_node']
        r = connection_envelope({}, value)
        self.assertEqual(r['applicationPerNodeUpperBound'], 200)
        self.assertIsNone(r['metadataEnvelopeWithinQuota'])
        self.assertIsNone(r['maxAdditionalReplicas'])

    def test_boolean_and_negative_unknown(self):
        paths = [('nodes', True), ('other_connections_per_node', False),
                 ('reserve_connections_per_node', 0), ('other_connections_per_node', -1)]
        for key, bad in paths:
            with self.subTest(key=key, value=bad):
                value = limits(); value['database_connection_budget'][key] = bad
                self.assertEqual(connection_envelope({}, value)['status'], 'UNKNOWN')
        value = limits(); value['database_connection_quota'] = True
        self.assertEqual(connection_envelope({}, value)['status'], 'UNKNOWN')

    def test_all_process_fields_explicit_and_strict(self):
        for key in cohort():
            with self.subTest(key=key):
                value = limits(); value['database_connection_budget']['cohorts'][0][key] = True
                self.assertEqual(connection_envelope({}, value)['status'], 'UNKNOWN')
        value = limits(); value['database_connection_budget']['cohorts'] = []
        self.assertEqual(connection_envelope({}, value)['status'], 'UNKNOWN')

    def test_explicit_zero_cohort_can_be_known(self):
        value = limits(); value['database_connection_budget']['max_replacement_replicas'] = 0
        value['database_connection_budget']['cohorts'] = [cohort(), cohort(0, role='replacement_web')]
        self.assertEqual(connection_envelope({}, value)['applicationPerNodeUpperBound'], 100)

    def test_full_reserve_is_a_conditional_boundary(self):
        value = limits(); value['database_connection_quota'] = 270
        r = connection_envelope({}, value)
        self.assertEqual(r['headroomPerNodeAfterReserve'], 0)
        self.assertEqual(r['maxAdditionalReplicas'], 0)
        self.assertTrue(r['metadataEnvelopeWithinQuota'])

    def test_summed_nodes_never_compared_to_per_node_limit(self):
        value = limits(); value['database_connection_budget']['nodes'] = 30
        r = connection_envelope({}, value)
        self.assertTrue(r['metadataEnvelopeWithinQuota'])
        self.assertEqual(r['allNodeApplicationUpperBound'], 6000)

    def test_unknown_overlap_is_not_implicitly_zero(self):
        value = limits(); del value['database_connection_budget']['max_replacement_replicas']
        self.assertEqual(connection_envelope({}, value)['status'], 'UNKNOWN')

    def test_running_count_and_worker_pool_drift_are_unknown(self):
        value = limits(); value['database_connection_budget']['observed_running_replicas'] = 11
        self.assertEqual(connection_envelope({}, value)['status'], 'UNKNOWN')
        self.assertEqual(connection_envelope({'WEB_CONCURRENCY': 2}, limits())['status'], 'UNKNOWN')
        self.assertEqual(connection_envelope({'MONGODB_MAX_POOL_SIZE': 25}, limits())['status'], 'UNKNOWN')

    def test_actual_one_still_bounds_ten_old_and_ten_new(self):
        value = limits(); value['database_connection_budget']['observed_running_replicas'] = 1
        r = connection_envelope({}, value, 1)
        self.assertEqual(r['applicationPerNodeUpperBound'], 200)
        self.assertEqual(r['status'], 'CONDITIONAL_BOUND')

    def test_actual_replica_argument_mismatch_is_unknown(self):
        value = limits()
        r = assess({}, 1, value)['connectionEnvelope']
        self.assertEqual(r['status'], 'UNKNOWN')
        self.assertIn('observed_running_replicas.actual_mismatch', r['unknownFields'])

    def test_current_bound_cannot_be_below_target_max(self):
        value = limits(); value['database_connection_budget']['max_current_web_replicas'] = 1
        value['database_connection_budget']['cohorts'][0]['replicas'] = 1
        value['database_connection_budget']['observed_running_replicas'] = 1
        self.assertEqual(connection_envelope({}, value, 1)['status'], 'UNKNOWN')
        del value['database_connection_budget']['max_current_web_replicas']
        self.assertEqual(connection_envelope({}, value, 1)['status'], 'UNKNOWN')

    def test_proposed_worker_and_pool_drift_cannot_inflate_additional_count(self):
        for field, source in [('workers_per_replica', 'WEB_CONCURRENCY'), ('pool_per_client_per_node', 'MONGODB_MAX_POOL_SIZE')]:
            with self.subTest(field=field):
                value = limits(); value['database_connection_budget']['additional_replica'][field] = 1
                config = {source: cohort()[field]}
                if field == 'workers_per_replica':
                    config[source] = 2
                    for c in value['database_connection_budget']['cohorts']:c[field] = 2
                self.assertIsNone(connection_envelope(config, value)['maxAdditionalReplicas'])

    def test_input_unchanged(self):
        value = limits(); before = copy.deepcopy(value)
        connection_envelope({}, value)
        self.assertEqual(before, value)

    def test_malformed_additional_replica_cannot_compute_maximum(self):
        value = limits(); value['database_connection_budget']['additional_replica']['workers_per_replica'] = False
        self.assertIsNone(connection_envelope({}, value)['maxAdditionalReplicas'])


class ControllerTests(unittest.TestCase):
    def evidence(self, mode='native_judoscale'):
        return {'controller': {'mode': mode, 'expected_target': dict(TARGET), 'observed_target': dict(TARGET)}}

    def test_names_and_booleans_never_prove_native_binding(self):
        value = {'controller': {'mode': 'native_judoscale', 'enforcementVerified': True,
                               'expected_target': {'name': 'earnalism'}, 'observed_target': {'name': 'earnalism'}}}
        r = controller_evidence(value)
        self.assertEqual(r['targetBinding'], 'UNKNOWN')
        self.assertFalse(r['enforcementVerified'])
        self.assertEqual(r['status'], 'UNMEDIATED_NATIVE_CONTROLLER')

    def test_native_match_is_not_enforcement(self):
        r = controller_evidence(self.evidence())
        self.assertEqual(r['targetBinding'], 'MATCH')
        self.assertFalse(r['enforcementVerified'])
        self.assertEqual(assess({}, 1, self.evidence())['status'], 'HOLD')

    def test_wrong_environment_denies(self):
        value = self.evidence(); value['controller']['observed_target']['environment_id'] = '00000000-0000-0000-0000-000000000000'
        self.assertEqual(controller_evidence(value)['status'], 'TARGET_MISMATCH')

    def test_custom_label_does_not_assert_a_guard_exists(self):
        r = controller_evidence(self.evidence('guarded_custom_api'))
        self.assertEqual(r['status'], 'GUARDED_IMPLEMENTATION_AND_RUNTIME_BINDING_REQUIRED')
        self.assertFalse(r['enforcementVerified'])

    def test_unknown_controller_remains_unknown(self):
        self.assertEqual(controller_evidence({})['status'], 'UNQUALIFIED')


if __name__ == '__main__':
    unittest.main()
