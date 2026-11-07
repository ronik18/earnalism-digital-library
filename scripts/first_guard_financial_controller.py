"""Additive financial I/O extension of the immutable native release controller.

No CLI/default authority. Existing native adapter/validators remain byte-identical;
only this explicit extension can enter the separately source-bound financial path.
"""
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from scripts import india_release_provider_adapter as native_adapter
from scripts.india_release_provider_adapter import (
    ReleaseController as NativeReleaseController, digest, require_digest, pair,
)


class FinancialReleaseController(NativeReleaseController):
    def prepare_financial_admission(self, *, amendment_path, source_binding_path,
                                    owner_decision_path, plan_path):
        """Local preparation only: never a capture permit or release receipt.

        Immutable proposal/decision pins prevent a caller from widening scope.
        No observe/run, credential/client construction, durable claim or journal
        mutation occurs here. Execution needs separate exact-code/current-runtime
        admission and a same-cumulative-ledger claim before first live I/O.
        """
        def pinned(path, expected, *, private=True):
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, 'rb') as stream:
                info = os.fstat(stream.fileno())
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                        or info.st_size > 1024 * 1024
                        or (private and stat.S_IMODE(info.st_mode) != 0o600)):
                    raise ValueError('Unsafe financial admission input')
                raw = stream.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024 or hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError('Exact financial admission input changed')
            return raw

        amendment_raw = pinned(amendment_path, 'cf4d431974a7227e1603d74dc518fe6074a70d1d3f19c1d4cff32f4f4c9811c1')
        source_raw = pinned(source_binding_path, 'b729145d3377427c5332db0835f9a8805bb0d120cfc8e2a45b9bd5e3655034d3')
        owner_raw = pinned(owner_decision_path, '2fa194d36d0a8fe2bb76701e08bcc6934f1ffa788a09b511cd42edba055d8fd6')
        plan_raw = pinned(plan_path, '77e4cb153ed16a980c1f64a60264be1050baa77967c727f31792c53dd2aebc84')
        amendment, source, owner, plan = map(json.loads,
            (amendment_raw, source_raw, owner_raw, plan_raw))
        if (owner['execution_authorized'] is not False
                or owner['budget_installed'] is not False
                or owner['observation_claimed'] is not False
                or owner['status'] != 'OWNER_APPROVED_BUDGET_ONLY_NO_EXECUTION'
                or owner['amendment_sha256'] != hashlib.sha256(amendment_raw).hexdigest()
                or owner['amendment_scope_sha256'] != amendment['amendment_scope_sha256']
                or digest(source) != amendment['amendment_scope_sha256']):
            raise ValueError('Exact budget-only decision required')
        if (hashlib.sha256(source_raw).hexdigest() != amendment['source_binding']['sha256']
                or hashlib.sha256(plan_raw).hexdigest() != amendment['exact_selectors_and_projections']['sha256']
                or digest(plan['queries']) != amendment['queries_sha256']
                or plan['source_binding'] != source['expected_component']
                or plan['target'] != source['target']
                or plan['actor']['user_id_sha256'] != source['actor_user_id_sha256']):
            raise ValueError('Exact source, actor and fixed financial query plan required')
        if (amendment['actual_budget_unchanged'] != {'consumed': 6, 'ceiling': 6, 'remaining': 0}
                or owner['historical_consumed_preserved'] != 6
                or owner['cumulative_ceiling_approved'] != 7
                or owner['additional_observations_approved'] != 1):
            raise ValueError('No reset, reclassification or separate capture bucket')

        # Read only original evidence, never overwrite or adopt a proposal into
        # the provider-intent journal. Historical source means expected source,
        # not proof of current provider state.
        for reference in (source['original_action_baseline'],
                          source['original_capture_custody'],
                          *source['original_consumed_artifacts'].values()):
            pinned(reference['path'], reference['sha256'])
        pair_reference = source['controller_sources']['pair']
        if Path(pair.__file__).resolve() != Path(pair_reference['path']).resolve():
            raise ValueError('Unexpected historical validator location')
        pinned(pair_reference['path'], pair_reference['sha256'], private=False)
        parent_id = source['parent_operation_id']
        expected_paths = {
            'parent': self.adapter.journal / (parent_id + '.json'),
            'pending': self.adapter.journal / '.first-guard-pending',
            'component': self.adapter.journal / ('.first-guard-component-' + parent_id + '.receipt'),
        }
        retained = {}
        for name, path in expected_paths.items():
            reference = source[name]
            if path.resolve() != Path(reference['path']).resolve():
                raise ValueError('Original physical operation journal required')
            retained[name] = json.loads(pinned(path, reference['sha256']))
        pending = self.adapter._read_pending()
        parent, component = retained['parent'], retained['component']
        if (pending != retained['pending'] or pending['state'] != pair.PENDING
                or parent['state'] != pair.PENDING or parent['operation_id'] != parent_id
                or pending['parent_operation_id'] != parent_id
                or pending['child_operation_id'] is not None
                or digest(parent) != pending['parent_record_sha256']
                or digest(component) != source['component_receipt_digest']
                or digest(component) != pending['component_receipt_sha256']
                or parent['binding']['native_action_scope'] != source['original_action_scope']):
            raise ValueError('Original component/pending parent changed; remain held')
        pair.validate(parent['binding'])
        counts = self.adapter._native_budget(parent['action'], parent['binding'],
            claim=False, own_operation_id=parent_id)
        # No new entries are exempted from native budget classification. The
        # normal perform/reconcile/finalizer and all recovery validators stay intact.
        return {
            'schema': 'earnalism.prepared_financial_admission.v1',
            'status': 'BUDGET_APPROVED_PREPARATION_ONLY',
            'amendment_sha256': hashlib.sha256(amendment_raw).hexdigest(),
            'source_binding_sha256': hashlib.sha256(source_raw).hexdigest(),
            'owner_decision_sha256': hashlib.sha256(owner_raw).hexdigest(),
            'plan_sha256': hashlib.sha256(plan_raw).hexdigest(),
            'queries_sha256': amendment['queries_sha256'],
            'parent_operation_id': parent_id,
            'component_receipt_sha256': digest(component),
            'original_controller_main': source['controller_main'],
            'payment_history': source['payment_history'],
            'expected_component_only_not_live_attestation': source['expected_component'],
            'historical_consumed_preserved': 6,
            'approved_cumulative_ceiling': 7,
            'approved_single_attempt_envelope': amendment['single_new_event_complete_IO_envelope'],
            'bounds': amendment['bounds'],
            'other_limits_unchanged': amendment['other_limits_unchanged'],
            'native_action_counts_read_only': counts,
            'live_consumed_count': None,
            'budget_installed': False,
            'observation_claimed': False,
            'execution_authorized': False,
            'final_execution_observer_source_sha256': None,
            'actual_current_profile_transport_admission_sha256': None,
            'runtime_issue_time': None,
            'runtime_expiry_time': None,
            'missing_before_any_claim': [
                'Separately authorized exact reviewed observer/client/transport source',
                'Genuine current source/runtime/config/host/client and clock admission',
                'Exclusive controller-owned observation7 claim in same cumulative ledger',
            ],
            'release': 'HELD',
            'frontend_promotion': 'HELD',
            'financial_or_paired_gate_acceptance': False,
        }

    async def collect_financial(self, *, runtime_contract, execution_approval,
                                readers, client_factory):
        """One separately authorized source-bound snapshot; never release acceptance.

        Budget approval alone cannot enter this path. The protected caller uses
        the same owner/observer trust boundary as this controller, and must
        supply genuine exact execution authority and current local provenance.
        No authority or provenance is issued by these caller-visible schemas.
        """
        if self.adapter.owner_authorized is not True:
            raise ValueError('Current owner instruction prohibits financial execution')
        if (runtime_contract.get('execution_authorized') is not True
                or runtime_contract.get('status') != 'ADMITTED_EXACT_FINANCIAL_RUNTIME'):
            raise ValueError('Prepared budget/runtime contract is not an execution permit')
        import inspect

        def source_bytes(path):
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, 'rb') as stream:
                info = os.fstat(stream.fileno())
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                        or info.st_size > 1024 * 1024 or stat.S_IMODE(info.st_mode) & 0o022):
                    raise ValueError('Unsafe exact financial source')
                raw = stream.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError('Oversized exact financial source')
            return raw

        if hashlib.sha256(source_bytes(native_adapter.__file__)).hexdigest() != 'e9406a9c7161c3ea4117bde37029c2fabad938138a78d6f2797275d46fd18155':
            raise ValueError('Immutable native adapter source changed')

        runtime_sha = hashlib.sha256(json.dumps(runtime_contract, sort_keys=True,
            separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        if (not inspect.isfunction(client_factory) or client_factory.__closure__ is not None
                or client_factory.__defaults__ is not None or client_factory.__kwdefaults__ is not None
                or inspect.iscoroutinefunction(client_factory)):
            raise ValueError('Exact closure-free synchronous client factory required')
        factory_source = inspect.getsourcefile(client_factory)
        transport_source = inspect.getsourcefile(type(readers))
        if not factory_source or not transport_source:
            raise ValueError('Exact factory and transport source unavailable')
        helper_path = Path(__file__).parent / 'first_guard_financial.py'
        observer_path = Path(__file__).parent / 'first_guard_financial_observer.py'
        helper_raw, observer_raw = source_bytes(helper_path), source_bytes(observer_path)
        pins = {'controller': hashlib.sha256(source_bytes(__file__)).hexdigest(),
                'claim_helper': hashlib.sha256(helper_raw).hexdigest(),
                'observer': hashlib.sha256(observer_raw).hexdigest(),
                'client_factory': hashlib.sha256(source_bytes(factory_source)).hexdigest(),
                'transport': hashlib.sha256(source_bytes(transport_source)).hexdigest()}
        if runtime_contract.get('source_pins') != pins:
            raise ValueError('Financial source pins differ from reviewed execution candidate')
        required = {'schema', 'status', 'approved', 'action', 'runtime_contract_sha256',
            'controller_source_sha256', 'claim_helper_source_sha256', 'observer_source_sha256',
            'client_factory_source_sha256', 'transport_source_sha256',
            'owner_execution_receipt_sha256', 'parent_operation_id', 'amendment_sha256',
            'approved_at', 'expires_at', 'execution_authorized', 'normal_release'}
        if not isinstance(execution_approval, dict) or set(execution_approval) != required:
            raise ValueError('Exact separate financial execution approval required')
        expected = {'schema': 'earnalism.financial_execution_approval.v1',
            'status': 'APPROVED_EXACT_FINANCIAL_CAPTURE', 'approved': True,
            'action': 'observe_paired_financial_snapshot', 'runtime_contract_sha256': runtime_sha,
            'controller_source_sha256': pins['controller'],
            'claim_helper_source_sha256': pins['claim_helper'],
            'observer_source_sha256': pins['observer'],
            'client_factory_source_sha256': pins['client_factory'],
            'transport_source_sha256': pins['transport'],
            'parent_operation_id': runtime_contract['parent_operation_id'],
            'amendment_sha256': runtime_contract['amendment_sha256'],
            'execution_authorized': True, 'normal_release': 'HELD'}
        for key, value in expected.items():
            if type(execution_approval.get(key)) is not type(value) or execution_approval[key] != value:
                raise ValueError('Exact financial execution approval mismatch: ' + key)
        actual = runtime_contract['required_actual_before_any_claim']
        if type(actual) is not dict or set(actual) != {'actual_client_factory_source_sha256', 'current_profile_provenance_sha256', 'expires_at', 'current_config_secret_version_context_sha256', 'runtime_flag_requirement_decision', 'canonical_history_preservation_sha256', 'actual_transport_source_sha256', 'trusted_existing_controller_resolver_sha256', 'expected_client_seed_set_sha256', 'protected_host_identity_sha256', 'expected_auth_database_sha256', 'expected_principal_sha256', 'issued_at', 'separate_execution_owner_authorization_sha256', 'admission_controller_commit_sha', 'runtime_flag_channel_or_applicability_sha256', 'current_runtime_dependency_closure_sha256'}:
            raise ValueError('Exact mandatory current financial admission schema required')
        owner_receipt = execution_approval['owner_execution_receipt_sha256']
        if (not require_digest(owner_receipt)
                or owner_receipt != actual['separate_execution_owner_authorization_sha256']
                or owner_receipt == runtime_contract['owner_budget_decision']['sha256']):
            raise ValueError('Budget-only reply is not financial execution authority')
        now = self.adapter.clock()
        start = datetime.fromisoformat(execution_approval['approved_at'])
        end = datetime.fromisoformat(execution_approval['expires_at'])
        if (any(t.tzinfo is None for t in (now, start, end))
                or not start <= now < end or not timedelta(0) < end-start <= timedelta(seconds=900)
                or start != datetime.fromisoformat(actual['issued_at'])
                or end != datetime.fromisoformat(actual['expires_at'])):
            raise ValueError('Financial execution approval clock invalid')
        # Validate mandatory current facts before loading any reviewed helper.
        # These hashes remain authenticated protected-caller evidence, not proof
        # manufactured by source hashing or by constructing a JSON dictionary.
        for key, value in actual.items():
            if key in {'issued_at', 'expires_at', 'runtime_flag_requirement_decision',
                       'admission_controller_commit_sha'}:
                continue
            if not require_digest(value):
                raise ValueError('Current financial provenance unbound: ' + key)
        if (actual['actual_client_factory_source_sha256'] != pins['client_factory']
                or actual['actual_transport_source_sha256'] != pins['transport']
                or type(actual['runtime_flag_requirement_decision']) is not bool
                or not re.fullmatch('[a-f0-9]{40}', actual['admission_controller_commit_sha'])):
            raise ValueError('Exact current financial runtime binding required')

        # Host receipt verification is local only. No source hash or supplied
        # bool manufactures the existing protected issuer's authentication.
        if readers.validate_preclaim(runtime_contract) is not True:
            raise ValueError('Authenticated existing-controller host binding required')

        # Compile the captured approved bytes, never import an unverified or
        # cached financial module. Dependency/callable runtime custody still
        # requires genuine protected-host admission; it is not inferred here.
        import sys
        import types
        def load_reviewed(kind, path, raw):
            name = '_earnalism_financial_' + kind + '_' + hashlib.sha256(raw).hexdigest()
            if name in sys.modules:
                raise ValueError('Financial module namespace already used; no replay')
            module = types.ModuleType(name)
            module.__file__ = str(path)
            sys.modules[name] = module
            try:
                exec(compile(raw, str(path), 'exec', dont_inherit=True), module.__dict__)
            except BaseException:
                # Preserve the used namespace; no repeated load/observation.
                raise
            return module
        financial = load_reviewed('claim', helper_path, helper_raw)
        financial_observer = load_reviewed('observer', observer_path, observer_raw)
        # Existing preparation validates the original immutable six and pending
        # pair before lock/claim. Helper repeats it under the original lock.
        context = financial.claim_seventh(self.adapter, runtime_contract, runtime_sha,
            pins['observer'], pins['controller'], execution_approval=execution_approval)
        try:
            readers.attach_claim(context)
            return await financial_observer.observe_preclaimed(context=context,
                readers=readers, client_factory=client_factory)
        finally:
            # Unresolved originals and cleanup retain ownership and the lock.
            # A permanently claimed seventh event is never cleared here.
            context.close_when_settled()
