"""Existing-controller host binding; never an issuer or provider implementation.

The protected controller must supply its genuine existing receipt verifier and
fixed-read dispatcher. There are no defaults, credential loaders or arming flags.
Source pins identify implementations; they do not authenticate an issuer.
"""
from datetime import datetime, timezone
import asyncio
import hashlib
import inspect
import json
import os
from pathlib import Path
import stat


class HostBindingHeld(Exception):
    pass


def need(condition):
    if not condition:
        raise HostBindingHeld('EXISTING_CONTROLLER_HOST_BINDING_HELD')


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def source_pin(function, expected, *, asynchronous):
    need(inspect.isfunction(function) and function.__closure__ is None
         and function.__defaults__ is None and function.__kwdefaults__ is None
         and inspect.iscoroutinefunction(function) is asynchronous)
    path = inspect.getsourcefile(function)
    need(path is not None and type(expected) is str and len(expected) == 64)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
             and not stat.S_IMODE(info.st_mode) & 0o022 and info.st_size <= 1048576)
        raw = stream.read(1048577)
    need(len(raw) <= 1048576 and hashlib.sha256(raw).hexdigest() == expected)


class ExistingControllerFinancialHost:
    """Inert binding to an already trusted controller, not a new trust anchor.

    verify_existing_receipt(raw, expected_claims) must be the existing protected
    host's pure local authenticator. read_dispatch(operation, argument, context)
    must perform ONE fixed read without retry/fallback and return a bounded native
    dict. Its transport framing, credentials, module globals and resource custody
    must be authenticated by the host receipt; hashes alone cannot prove them.
    """
    def __init__(self, adapter, *, binding, verify_existing_receipt, read_dispatch):
        self._adapter = adapter
        self._binding = json.loads(encode(binding))
        self._verify = verify_existing_receipt
        self._dispatch = read_dispatch
        self._runtime_sha = None
        self._expires = None
        self._failed = False
        self._next = 0
        self._busy = False

    def verify_preclaim(self, runtime):
        need(not self._failed and self._runtime_sha is None)
        try:
            need(self._adapter.owner_authorized is True
                 and runtime['execution_authorized'] is True
                 and runtime['status'] == 'ADMITTED_EXACT_FINANCIAL_RUNTIME')
            binding = self._binding
            need(runtime['trusted_host_binding'] == binding
                 and binding['schema'] == 'earnalism.existing_controller_host_binding.v1'
                 and type(binding['issuer_id']) is str and bool(binding['issuer_id']))
            own = Path(__file__).read_bytes()
            need(hashlib.sha256(own).hexdigest() == binding['binding_source_sha256'])
            actual = runtime['required_actual_before_any_claim']
            need(binding['verifier_source_sha256'] == actual['trusted_existing_controller_resolver_sha256']
                 and binding['host_identity_sha256'] == actual['protected_host_identity_sha256'])
            source_pin(self._verify, binding['verifier_source_sha256'], asynchronous=False)
            source_pin(self._dispatch, binding['dispatch_source_sha256'], asynchronous=True)
            reference = binding['receipt_reference']
            need(type(reference) is dict and set(reference) == {'path', 'sha256'})
            fd = os.open(reference['path'], os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, 'rb') as stream:
                info = os.fstat(stream.fileno())
                need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                     and stat.S_IMODE(info.st_mode) == 0o600 and info.st_size <= 65536)
                raw = stream.read(65537)
            need(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == reference['sha256'])
            # Deliberately do not use a receipt file's own "verified" flag.
            # Authentication is the existing protected issuer's responsibility.
            expected = {
                'scope': 'EXACT_FINANCIAL_READONLY_HOST',
                'issuer_id': binding['issuer_id'],
                'host_identity_sha256': actual['protected_host_identity_sha256'],
                'source_pins': runtime['source_pins'],
                'binding_source_sha256': binding['binding_source_sha256'],
                'dispatch_source_sha256': binding['dispatch_source_sha256'],
                'parent_operation_id': runtime['parent_operation_id'],
                'amendment_sha256': runtime['amendment_sha256'],
                'target': runtime['target'],
                'expected_component': runtime['expected_component'],
                'current_admission_facts': actual,
                'issued_at': actual['issued_at'], 'expires_at': actual['expires_at'],
                'maximum_native_reads': 8,
                'maximum_native_response_bytes': 1048576,
                'automatic_retries': 0,
                'normal_release': 'HELD',
            }
            need(self._verify(raw, expected) is True)
            issued = datetime.fromisoformat(actual['issued_at'])
            expires = datetime.fromisoformat(actual['expires_at'])
            now = datetime.now(timezone.utc)
            need(issued.tzinfo is not None and expires.tzinfo is not None
                 and issued <= now < expires and 0 < (expires-issued).total_seconds() <= 900)
            self._runtime_sha = hashlib.sha256(encode(runtime)).hexdigest()
            self._expires = expires
            return True
        except BaseException:
            self._failed = True
            raise HostBindingHeld('HOST_PRECLAIM_AUTHENTICATION_HELD') from None

    def verify_local_binding(self, context):
        need(not self._failed and self._runtime_sha is not None
             and context.runtime_sha256 == self._runtime_sha
             and datetime.now(timezone.utc) < self._expires)
        context.assert_valid()
        source_pin(self._dispatch, self._binding['dispatch_source_sha256'], asynchronous=True)
        return True

    async def read_exact(self, operation, argument, context):
        try:
            self.verify_local_binding(context)
            need(operation in {'github_ref', 'railway_graphql', 'describe_service', 'staged_changes'})
            runtime = context.runtime_contract
            target = runtime['target']
            component = runtime['expected_component']
            query = ('query { deployment(id:"'+component['deployment_id']+'") { id status projectId serviceId environmentId snapshotId '
                'instances { id status } meta } serviceInstance(environmentId:"'+target['environment']+'",serviceId:"'+target['service']+'") '
                '{ activeDeployments { id status } } deploymentTriggers(projectId:"'+target['project']+'",environmentId:"'+target['environment']+'",serviceId:"'+target['service']+'",first:100) '
                '{ edges { node { id } } pageInfo { hasNextPage } } }')
            native = ('railway_graphql', {'query': query})
            describe = ('describe_service', target)
            staged = ('staged_changes', target)
            schedule = (('github_ref', {'branch': 'main'}),
                ('github_ref', {'branch': 'codex/main-approved-integration'}),
                native, describe, staged, native, describe, staged)
            need(not self._busy and self._next < len(schedule)
                 and schedule[self._next] == (operation, argument))
            self._next += 1
            self._busy = True
            task = asyncio.create_task(self._dispatch(operation, argument, context))
            context.track_future(task)
            result = await asyncio.shield(task)
            # Dispatcher must bound raw framing BEFORE decode. This check bounds
            # decoded evidence only, not the upstream network allocation.
            need(type(result) is dict and len(encode(result)) <= 1048576)
            self.verify_local_binding(context)
            return result
        except BaseException:
            self._failed = True
            raise HostBindingHeld('HOST_READ_UNKNOWN_NO_RETRY') from None
        finally:
            self._busy = False
