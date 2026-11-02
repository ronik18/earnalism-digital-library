"""Synthetic resource integers and dummy authority only; no production budgets."""
import asyncio,copy,unittest
from dataclasses import replace
from unittest.mock import patch
import httpx
from scripts.scaling_resource_admission import (
    ResourceHeld,ManagedClientGrant,DisabledManagedClientAuthority,
    budget_digest,managed_client_admission,redis_memory_admission,
)
from scripts.guarded_scaling_controller import Controller,Held,create_app
from scripts import test_guarded_scaling_controller as controller_fixtures
from scripts.test_guarded_scaling_controller import (
    TARGET,REDIS_TARGET,DIGEST,ATLAS,TOKEN,
    DummyManagedAuthority,observation,redis_budget,
)


class MemoryAdmission(unittest.TestCase):
    def check(self,budget):return redis_memory_admission(budget,application_target_key=TARGET.key,redis_target_key=REDIS_TARGET.key,
        source_digest=DIGEST,approved_memory_envelope_bytes=280,now=1000,max_age=15)

    def test_safe_synthetic_sum_is_exact_and_not_a_runtime_certificate(self):
        self.assertEqual(self.check(redis_budget()),{'maxmemory_bytes':100,
            'service_upper_bound_bytes':280,'approved_memory_envelope_bytes':280})

    def test_unknown_and_actual_unlimited_cap_deny(self):
        for b in (None,{},dict(redis_budget(),maxmemory_bytes=0)):
            with self.subTest(budget='synthetic'),self.assertRaises(ResourceHeld):self.check(b)

    def test_all_component_bounds_are_explicit_strict_integers(self):
        fields=['maxmemory_bytes','used_memory_bytes','intended_dataset_bytes',
                'parent_rss_upper_bound_bytes','persistence_cow_upper_bound_bytes',
                'excluded_buffers_upper_bound_bytes','other_process_upper_bound_bytes',
                'safety_reserve_bytes','approved_memory_envelope_bytes','provider_enforced_limit_bytes']
        for field in fields:
            for value in (None,True,False,-1,1.0,float('nan'),float('inf'),'100'):
                with self.subTest(field=field,value=type(value).__name__),self.assertRaises(ResourceHeld):
                    self.check(dict(redis_budget(),**{field:value}))
            missing=redis_budget();del missing[field]
            with self.subTest(field=field),self.assertRaises(ResourceHeld):self.check(missing)

    def test_known_zero_non_parent_components_are_not_unknown(self):
        b=redis_budget();b.update(persistence_mode='no_fork',rdb_enabled=False,aof_enabled=False)
        for field in ('persistence_cow_upper_bound_bytes','excluded_buffers_upper_bound_bytes','other_process_upper_bound_bytes'):b[field]=0
        self.assertEqual(self.check(b)['service_upper_bound_bytes'],140)

    def test_used_dataset_parent_and_provider_limits_are_distinct(self):
        cases=[{'maxmemory_bytes':10},{'intended_dataset_bytes':101},
               {'parent_rss_upper_bound_bytes':99},{'approved_memory_envelope_bytes':279},
               {'approved_memory_envelope_bytes':301}]
        for change in cases:
            with self.subTest(change=change),self.assertRaises(ResourceHeld):self.check(dict(redis_budget(),**change))

    def test_snapshot_rss_cannot_replace_missing_cow_bound(self):
        b=redis_budget();del b['persistence_cow_upper_bound_bytes'];b['observed_current_rss_bytes']=24
        with self.assertRaises(ResourceHeld):self.check(b)

    def test_rdb_forking_cannot_claim_zero_or_partial_cow(self):
        for value in (0,119):
            with self.subTest(cow=value),self.assertRaises(ResourceHeld):self.check(dict(redis_budget(),persistence_cow_upper_bound_bytes=value))

    def test_persistence_unknown_or_contradictory_denies(self):
        for change in ({'persistence_mode':None},{'rdb_enabled':None},{'aof_enabled':'false'},
                       {'persistence_mode':'no_fork'},{'persistence_mode':'no_fork','rdb_enabled':False,'aof_enabled':True}):
            with self.subTest(change=change),self.assertRaises(ResourceHeld):self.check(dict(redis_budget(),**change))

    def test_memory_envelope_cannot_be_borrowed_from_another_policy(self):
        with self.assertRaises(ResourceHeld):self.check(dict(redis_budget(),approved_memory_envelope_bytes=300))

    def test_source_target_freshness_and_policy_binding(self):
        cases=[{'redis_target_key':TARGET.key},{'application_target_key':REDIS_TARGET.key},{'source_digest':'b'*64},{'observed_at':984},
               {'observed_at':1001},{'observed_at':True},{'observed_at':float('nan')},
               {'policy':'volatile-lfu'},{'startup_config_writes':True},{'startup_config_writes':None}]
        for change in cases:
            with self.subTest(change=change),self.assertRaises(ResourceHeld):self.check(dict(redis_budget(),**change))


class ManagedAdmission(unittest.TestCase):
    def kw(self):return dict(target_key=TARGET.key,source_digest=DIGEST,provider_revision='r1',
        atlas_resource=ATLAS,desired=3,budget=observation().limits['database_connection_budget'],now=1000,max_age=15)

    def test_default_authority_denies_even_perfect_json_metadata(self):
        with self.assertRaises(ResourceHeld)as caught:
            managed_client_admission(DisabledManagedClientAuthority(),**self.kw())
        self.assertEqual(caught.exception.code,'MANAGED_CLIENT_AUTHORITY_UNAVAILABLE')

    def test_unknown_external_is_not_zero(self):
        for value in (None,True,-1,'unknown'):
            kw=self.kw();kw['budget']['other_connections_per_node']=value
            with self.subTest(value=value),self.assertRaises(ResourceHeld):managed_client_admission(DummyManagedAuthority(),**kw)

    def test_grant_is_from_injected_verifier_not_a_json_flag(self):
        class JsonClaim:
            def verify(self,**kw):return {'custody_enforced':True,'budget_sha256':budget_digest(kw['budget'])}
        with self.assertRaises(ResourceHeld):managed_client_admission(JsonClaim(),**self.kw())
        self.assertIsInstance(managed_client_admission(DummyManagedAuthority(),**self.kw()),ManagedClientGrant)

    def test_every_binding_and_expiry_is_checked(self):
        original=DummyManagedAuthority().verify(**{k:v for k,v in self.kw().items()if k not in('now','max_age')})
        for change in ({'target_key':REDIS_TARGET.key},{'source_digest':'b'*64},
                       {'provider_revision':'old'},{'atlas_resource':'2'*24+'/other'},
                       {'budget_sha256':'0'*64},{'desired':4},{'desired':True},{'valid_until':1000},{'valid_until':1016},
                       {'valid_until':True},{'valid_until':float('inf')}):
            class Wrong:
                def verify(self,**kw):return replace(original,**change)
            with self.subTest(change=change),self.assertRaises(ResourceHeld):managed_client_admission(Wrong(),**self.kw())

    def test_rollout_budget_change_cannot_reuse_grant(self):
        kw=self.kw()
        grant=DummyManagedAuthority().verify(**{k:v for k,v in kw.items()if k not in('now','max_age')})
        class Retained:
            def verify(self,**kw):return grant
        kw['budget']['max_replacement_replicas']=11
        with self.assertRaises(ResourceHeld):managed_client_admission(Retained(),**kw)

    def test_authority_fault_fails_closed_and_copy_cannot_mutate_observation(self):
        class Fault:
            def verify(self,**kw):raise RuntimeError('private authority fault')
        with self.assertRaises(ResourceHeld)as error:managed_client_admission(Fault(),**self.kw())
        self.assertEqual(error.exception.code,'MANAGED_CLIENT_AUTHORITY_FAILED')
        class Mutator:
            def verify(self,**kw):
                grant=DummyManagedAuthority().verify(**kw)
                kw['budget']['other_connections_per_node']=999
                return grant
        kw=self.kw();before=copy.deepcopy(kw['budget']);managed_client_admission(Mutator(),**kw);self.assertEqual(kw['budget'],before)


class ResourceController(unittest.IsolatedAsyncioTestCase):
    # Reuse fixture setup without duplicating the original regression suite.
    setUp=controller_fixtures.ControllerTests.setUp
    tearDown=controller_fixtures.ControllerTests.tearDown
    async def test_new_default_authority_and_memory_unknown_never_reach_write(self):
        missing=Controller(self.policy,self.journal,self.provider,clock=lambda:1000)
        with self.assertRaises(Held)as error:await missing.scale(3)
        self.assertEqual(error.exception.code,'MANAGED_CLIENT_AUTHORITY_UNAVAILABLE')
        self.assertEqual(self.provider.writes,[]);self.assertIsNone(self.journal.active(TARGET))
        for change in ({'maxmemory_bytes':0},{'approved_memory_envelope_bytes':None}):
            o=observation();o.limits['redis_memory_budget'].update(change);self.provider.current=o
            with self.assertRaises(Held):await self.controller.scale(3)
            self.assertEqual(self.provider.writes,[]);self.assertIsNone(self.journal.active(TARGET))

    async def test_explicit_redis_policy_is_required_and_cannot_alias_api(self):
        with self.assertRaises(ValueError):replace(self.policy,redis_target=TARGET)
        for value in (True,0,-1,1.0,float('nan')):
            with self.subTest(value=type(value).__name__),self.assertRaises(ValueError):replace(self.policy,approved_redis_memory_envelope_bytes=value)
        for change,code in (({'redis_target':None},'REDIS_TARGET_REQUIRED'),
                            ({'approved_redis_memory_envelope_bytes':None},'REDIS_APPROVED_MEMORY_ENVELOPE_REQUIRED')):
            c=Controller(replace(self.policy,**change),self.journal,self.provider,clock=lambda:1000,managed_client_authority=DummyManagedAuthority())
            with self.assertRaises(Held)as error:await c.scale(3)
            self.assertEqual(error.exception.code,code);self.assertEqual(self.provider.writes,[])

    async def test_new_second_read_memory_drift_denies_before_write(self):
        o=observation();o.limits['redis_memory_budget']['approved_memory_envelope_bytes']=279
        self.provider.second=o
        with self.assertRaises(Held):await self.controller.scale(3)
        self.assertEqual(self.provider.writes,[]);self.assertIsNone(self.journal.active(TARGET))

    async def test_public_request_cannot_supply_new_resource_proofs(self):
        app=create_app(self.controller,TOKEN)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://dummy.invalid',headers={'Authorization':'Bearer '+TOKEN})as client:
            for field in ('redis_memory_budget','managed_client_grant'):
                r=await client.patch('/services/'+TARGET.service_id,json={'scale':3,field:{}})
                self.assertEqual(r.status_code,400)
        self.assertEqual(self.provider.reads,0);self.assertEqual(self.provider.writes,[])
