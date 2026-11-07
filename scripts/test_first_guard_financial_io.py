"""Isolated IO-boundary tests. Every profile, client, dispatcher and claim is fake."""
import asyncio
import hashlib
import json
import types
import tempfile
import os
from pathlib import Path
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

from scripts import first_guard_financial as claim
from scripts import first_guard_financial_factory as factory
from scripts import first_guard_financial_host as host
from scripts import first_guard_financial_transport as transport
from scripts import india_release_provider_adapter as controller


class SyntheticContext:
    def __init__(self, runtime, loop=None):
        self.runtime_contract = runtime
        self.loop = loop
        self.clients = {}
        self.futures = []
        self.started = False
    def assert_valid(self, check_deadline=True): return self
    def require_for(self, source): return self
    def begin_client_factory(self, source):
        if self.started: raise RuntimeError('already started')
        self.started = True
    def get_client_event_loop(self): return self.loop
    def retain_client(self, client): self.clients[id(client)] = client
    def client_closed(self, client): del self.clients[id(client)]
    def track_future(self, future): self.futures.append(future)
    @property
    def runtime_sha256(self):
        return hashlib.sha256(json.dumps(self.runtime_contract, sort_keys=True,
            separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


class ControllerBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_claim_helper_rejects_budget_only_without_any_claim_file(self):
        runtime = {'schema': 'earnalism.source_bound_financial_runtime_contract.v1',
            'status': 'PREPARED_NO_EXECUTION_AUTHORIZATION', 'execution_authorized': False}
        with patch.object(claim.os, 'open', side_effect=AssertionError('no journal IO')) as opened, \
             patch.object(claim.os, 'mkdir', side_effect=AssertionError('no seventh slot')) as mkdir:
            with self.assertRaises(claim.FinancialHeld):
                claim.claim_seventh(types.SimpleNamespace(owner_authorized=True), runtime,
                    claim.digest(runtime), 'a'*64, 'b'*64, execution_approval={})
        opened.assert_not_called()
        mkdir.assert_not_called()

    async def test_budget_only_cannot_read_sources_or_dispatch(self):
        adapter = types.SimpleNamespace(owner_authorized=True)
        obj = controller.ReleaseController(adapter)
        readers, constructor = Mock(), Mock()
        with patch.object(controller.os, 'open', side_effect=AssertionError('no IO')) as opened:
            with self.assertRaisesRegex(ValueError, 'not an execution permit'):
                await obj.collect_financial(runtime_contract={
                    'execution_authorized': False, 'status': 'PREPARED_NO_EXECUTION_AUTHORIZATION',
                    'approved_cumulative_ceiling': 7, 'original_consumed': 6},
                    execution_approval={'approved': True}, readers=readers, client_factory=constructor)
        opened.assert_not_called()
        readers.assert_not_called()
        constructor.assert_not_called()

    async def test_helper_factory_is_one_shot_and_returns_original_loop(self):
        # Never invoke SeventhClaim.__init__, claim_seventh or any journal code.
        obj = object.__new__(claim.SeventhClaim)
        obj._runtime = claim.encode({'source_pins': {'client_factory': 'f'}})
        obj._observer_started = False
        obj._factory_started = False
        obj._client_loop = asyncio.get_running_loop()
        with patch.object(claim.SeventhClaim, 'assert_valid', return_value=obj):
            with self.assertRaises(Exception): obj.begin_client_factory('f')
            obj._observer_started = True
            with self.assertRaises(Exception): obj.begin_client_factory('wrong')
            obj.begin_client_factory('f')
            self.assertIs(obj.get_client_event_loop(), asyncio.get_running_loop())
            with self.assertRaises(Exception): obj.begin_client_factory('f')


class FactoryTests(unittest.IsolatedAsyncioTestCase):
    def prepare(self, constructor):
        stack = ExitStack()
        self.addCleanup(stack.close)
        digest = hashlib.sha256(b'synthetic-source').hexdigest()
        versions = {'motor': '3.3.1', 'pymongo': '4.5.0', 'dnspython': '2.8.0'}
        actual = {k: 'x' for k in ('current_profile_provenance_sha256',
            'current_runtime_dependency_closure_sha256', 'protected_host_identity_sha256',
            'expected_principal_sha256', 'expected_auth_database_sha256',
            'expected_client_seed_set_sha256', 'current_config_secret_version_context_sha256')}
        actual['actual_client_factory_source_sha256'] = digest
        dbhash = hashlib.sha256(b'fixture_db').hexdigest()
        runtime = {'source_pins': {'observer': 'observer', 'claim_helper': digest,
            'client_factory': digest}, 'required_actual_before_any_claim': actual,
            'database_name_sha256': dbhash, 'expected_driver_versions': versions}
        context = SyntheticContext(runtime, asyncio.get_running_loop())
        stack.enter_context(patch.object(factory.Path, 'read_bytes', return_value=b'synthetic-source'))
        stack.enter_context(patch.object(factory.inspect, 'getsourcefile', return_value='synthetic-helper.py'))
        stack.enter_context(patch.object(factory, 'DATABASE_SHA256', dbhash))
        read = stack.enter_context(patch.object(factory, '_read_pinned', side_effect=[
            {'database_binding': {'path': 'fixture-binding', 'sha256': 'b'},
             'mongo_profile': {'path': 'fixture-profile', 'sha256': 'p'}},
            {'database': 'fixture_db', 'database_name_sha256': dbhash},
            {'uri': 'mongodb://fixture.invalid/'}]))
        stack.enter_context(patch('importlib.metadata.version', side_effect=versions.__getitem__))
        motor = types.ModuleType('motor')
        motor_asyncio = types.ModuleType('motor.motor_asyncio')
        motor_asyncio.AsyncIOMotorClient = constructor
        stack.enter_context(patch.dict('sys.modules', {'motor': motor, 'motor.motor_asyncio': motor_asyncio}))
        return context, read

    async def test_factory_uses_main_loop_and_bounded_dedicated_client(self):
        client = Mock()
        client.__getitem__ = Mock(return_value='fixture-db-handle')
        constructor = Mock(return_value=client)
        context, read = self.prepare(constructor)
        result = await asyncio.to_thread(factory.create_client, context)
        self.assertEqual(result, (client, 'fixture-db-handle'))
        self.assertEqual(list(context.clients.values()), [client])
        self.assertEqual(read.call_count, 3)
        options = constructor.call_args.kwargs
        self.assertIs(options['io_loop'], asyncio.get_running_loop())
        self.assertEqual({k: options[k] for k in ('maxPoolSize', 'minPoolSize', 'maxConnecting')},
                         {'maxPoolSize': 1, 'minPoolSize': 0, 'maxConnecting': 1})
        for key in ('serverSelectionTimeoutMS','connectTimeoutMS','socketTimeoutMS','waitQueueTimeoutMS'):
            self.assertEqual(options[key], 1000)
        for key in ('retryReads','retryWrites','connect'): self.assertIs(options[key], False)
        self.assertIs(options['document_class'], dict)
        self.assertIs(options['tz_aware'], True)
        client.close.assert_not_called()
        with self.assertRaises(RuntimeError): factory.create_client(context)
        self.assertEqual(constructor.call_count, 1)

    async def test_constructor_unknown_retains_custody_without_secret_error(self):
        constructor = Mock(side_effect=ValueError('PRIVATE_URI_MUST_NOT_ESCAPE'))
        context, _ = self.prepare(constructor)
        with self.assertRaisesRegex(RuntimeError, '^CLIENT_CONSTRUCTION_OR_SELECTION_UNKNOWN_HELD$'):
            factory.create_client(context)
        self.assertEqual(len(context.clients), 1)  # permanent UNKNOWN sentinel
        self.assertEqual(constructor.call_count, 1)

    async def test_unbound_provenance_prevents_profile_read_or_constructor(self):
        constructor = Mock()
        context, read = self.prepare(constructor)
        context.runtime_contract['required_actual_before_any_claim']['expected_client_seed_set_sha256'] = None
        with self.assertRaisesRegex(RuntimeError, 'CURRENT_CLIENT_PROVENANCE_REQUIRED'):
            factory.create_client(context)
        read.assert_not_called()
        constructor.assert_not_called()


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_changed_runtime_after_preclaim_cannot_attach_or_open_plan(self):
        own = hashlib.sha256(Path(transport.__file__).read_bytes()).hexdigest()
        runtime = {'status': 'ADMITTED_EXACT_FINANCIAL_RUNTIME', 'execution_authorized': True,
            'source_pins': {'transport': own},
            'required_actual_before_any_claim': {'actual_transport_source_sha256': own}}
        h = types.SimpleNamespace(verify_preclaim=Mock(return_value=True))
        t = transport.FixedFinancialTransport(h)
        self.assertTrue(t.validate_preclaim(runtime))
        runtime['changed_after_local_verification'] = True
        with patch.object(transport.os, 'open', side_effect=AssertionError('no plan IO')) as opened:
            with self.assertRaises(transport.TransportHold):
                t.attach_claim(SyntheticContext(runtime))
        opened.assert_not_called()

    def attached(self, dispatch):
        h = types.SimpleNamespace(verify_local_binding=Mock(return_value=True), read_exact=dispatch)
        t = transport.FixedFinancialTransport(h)
        ctx = SyntheticContext({})
        t._context = ctx  # Explicit synthetic post-admission seam; no real plan open.
        t._schedule = (('github_ref', {'branch': 'main'}),
            ('github_ref', {'branch': 'codex/main-approved-integration'}),
            ('railway_graphql', {'query': 'fixture-query'}),
            ('describe_service', {'service': 'fixture'}), ('staged_changes', {'service': 'fixture'}),
            ('railway_graphql', {'query': 'fixture-query'}),
            ('describe_service', {'service': 'fixture'}), ('staged_changes', {'service': 'fixture'}))
        t._expected_refs = ('main-sha', 'payment-sha')
        return t, ctx

    async def test_inert_and_budget_only_preclaim_no_host_read(self):
        h = Mock()
        with patch.object(transport.os, 'open', side_effect=AssertionError('no plan IO')):
            t = transport.FixedFinancialTransport(h)
            h.assert_not_called()
            with self.assertRaises(transport.TransportHold):
                t.validate_preclaim({'status': 'PREPARED', 'execution_authorized': False})
        h.verify_preclaim.assert_not_called()
        h.read_exact.assert_not_called()

    async def test_eight_fixed_reads_and_ninth_is_denied(self):
        dispatch = AsyncMock(side_effect=[{'sha':'main-sha'}, {'sha':'payment-sha'}] + [{}]*6)
        t, ctx = self.attached(dispatch)
        for op, arg in t._schedule:
            await t._read(op, arg)
        self.assertEqual(dispatch.await_count, 8)
        self.assertEqual(len(ctx.futures), 8)
        self.assertTrue(all(f.done() for f in ctx.futures))
        with self.assertRaises(transport.TransportHold): await t.github_ref('main')
        self.assertEqual(dispatch.await_count, 8)

    async def test_wrong_order_burns_transport_without_dispatch_or_retry(self):
        dispatch = AsyncMock()
        t, _ = self.attached(dispatch)
        with self.assertRaises(transport.TransportHold): await t.github_ref('wrong')
        with self.assertRaises(transport.TransportHold): await t.github_ref('main')
        dispatch.assert_not_awaited()

    async def test_cancel_preserves_original_dispatch_until_late_completion(self):
        started, finish = asyncio.Event(), asyncio.Event()
        async def slow(op, arg, ctx):
            started.set()
            await finish.wait()
            return {'sha': 'main-sha'}
        t, ctx = self.attached(slow)
        outer = asyncio.create_task(t.github_ref('main'))
        await started.wait()
        outer.cancel()
        with self.assertRaises(transport.TransportHold): await outer
        self.assertEqual(len(ctx.futures), 1)
        original = ctx.futures[0]
        self.assertFalse(original.done())
        self.assertFalse(original.cancelled())
        finish.set()
        await original
        with self.assertRaises(transport.TransportHold): await t.github_ref('main')
        self.assertEqual(len(ctx.futures), 1)


class HostTests(unittest.IsolatedAsyncioTestCase):
    async def test_host_itself_rejects_arbitrary_query_without_transport(self):
        dispatch = AsyncMock(return_value={})
        h = host.ExistingControllerFinancialHost(types.SimpleNamespace(), binding={},
            verify_existing_receipt=Mock(), read_dispatch=dispatch)
        # Synthetic authenticated-context seam: test exact dispatch scope only.
        runtime = {'target': {'project': 'p', 'service': 's', 'environment': 'e'},
                   'expected_component': {'deployment_id': 'd'}}
        context = SyntheticContext(runtime)
        with patch.object(h, 'verify_local_binding', return_value=True):
            await h.read_exact('github_ref', {'branch': 'main'}, context)
            await h.read_exact('github_ref', {'branch': 'codex/main-approved-integration'}, context)
            with self.assertRaises(host.HostBindingHeld):
                await h.read_exact('railway_graphql', {'query': 'mutation { forbidden }'}, context)
            with self.assertRaises(host.HostBindingHeld):
                await h.read_exact('github_ref', {'branch': 'main'}, context)
        self.assertEqual(dispatch.await_count, 2)
        self.assertEqual(len(context.futures), 2)

    async def test_inert_null_issuer_and_no_dispatch_before_binding(self):
        verify, dispatch = Mock(), AsyncMock()
        adapter = types.SimpleNamespace(owner_authorized=True)
        binding = {'schema':'earnalism.existing_controller_host_binding.v1', 'issuer_id':None}
        with patch.object(host.os, 'open', side_effect=AssertionError('no receipt IO')):
            h = host.ExistingControllerFinancialHost(adapter, binding=binding,
                verify_existing_receipt=verify, read_dispatch=dispatch)
            verify.assert_not_called()
            with self.assertRaises(host.HostBindingHeld):
                h.verify_preclaim({'execution_authorized':True,
                    'status':'ADMITTED_EXACT_FINANCIAL_RUNTIME','trusted_host_binding':binding})
            with self.assertRaises(host.HostBindingHeld):
                await h.read_exact('github_ref', {'branch':'main'}, SyntheticContext({}))
        verify.assert_not_called()
        dispatch.assert_not_awaited()


    async def test_false_existing_receipt_verifier_never_arms_dispatch(self):
        verify, dispatch = Mock(return_value=False), AsyncMock()
        now = datetime.now(timezone.utc)
        actual = {'trusted_existing_controller_resolver_sha256':'v',
            'protected_host_identity_sha256':'h',
            'issued_at':now.isoformat(), 'expires_at':(now+timedelta(minutes=1)).isoformat()}
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory)/'synthetic-receipt.json'
            receipt.write_bytes(b'{}')
            os.chmod(receipt, 0o600)
            binding = {'schema':'earnalism.existing_controller_host_binding.v1',
                'issuer_id':'fixture-issuer', 'binding_source_sha256':hashlib.sha256(b'fixture').hexdigest(),
                'verifier_source_sha256':'v','host_identity_sha256':'h','dispatch_source_sha256':'d',
                'receipt_reference':{'path':str(receipt),'sha256':hashlib.sha256(b'{}').hexdigest()}}
            runtime = {'execution_authorized':True,'status':'ADMITTED_EXACT_FINANCIAL_RUNTIME',
                'trusted_host_binding':binding,'required_actual_before_any_claim':actual,
                'source_pins':{},'parent_operation_id':'fixture','amendment_sha256':'fixture',
                'target':{},'expected_component':{}}
            h = host.ExistingControllerFinancialHost(types.SimpleNamespace(owner_authorized=True),
                binding=binding,verify_existing_receipt=verify,read_dispatch=dispatch)
            with patch.object(host.Path,'read_bytes',return_value=b'fixture'), patch.object(host,'source_pin'):
                with self.assertRaises(host.HostBindingHeld): h.verify_preclaim(runtime)
            verify.assert_called_once()
            self.assertIsNone(h._runtime_sha)
            with self.assertRaises(host.HostBindingHeld):
                await h.read_exact('github_ref',{'branch':'main'},SyntheticContext({}))
            dispatch.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
