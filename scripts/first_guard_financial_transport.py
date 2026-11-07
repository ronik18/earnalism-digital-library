"""Private proposed fixed financial transport. Preparation only; never invoked.

The existing protected host must authenticate its real local binding. This
module cannot manufacture host identity, execution approval or provider access.
Construction is inert; only an existing controller-issued claim permits reads.
"""
from __future__ import annotations
import asyncio
import hashlib
import json
import os
import re
import stat
from pathlib import Path

PLAN = Path('/private/tmp/pr656-native-successor-20261107/read-only-capture-plan/PLAN.json')
PLAN_SHA = '77e4cb153ed16a980c1f64a60264be1050baa77967c727f31792c53dd2aebc84'
PAYMENT = '5e739e69d3086a14d83f802f7cc5b3da9b90ddf0'

class TransportHold(Exception):
    pass

def need(condition):
    if not condition:
        raise TransportHold('FIXED_FINANCIAL_TRANSPORT_HOLD_NO_RETRY')

def _native_query(p):
    t=p['target'];dep=p['source_binding']['deployment_id']
    return ('query { deployment(id:"'+dep+'") { id status projectId serviceId environmentId snapshotId '
        'instances { id status } meta } serviceInstance(environmentId:"'+t['environment']+'",serviceId:"'+t['service']+'") '
        '{ activeDeployments { id status } } deploymentTriggers(projectId:"'+t['project']+'",environmentId:"'+t['environment']+'",serviceId:"'+t['service']+'",first:100) '
        '{ edges { node { id } } pageInfo { hasNextPage } } }')

class FixedFinancialTransport:
    """Inert host handle, followed by exactly eight source-bound read requests.

    host.verify_local_binding(context) is mandatory PURE LOCAL verification of
    already authenticated protected host/issuer custody. It must return True;
    its implementation/evidence is separately pinned, not supplied by this file.
    host.read_exact(operation, argument, context) performs one native read only,
    without retry, fallback, pagination, profile/client/DNS work or text parsing.
    """
    def __init__(self, existing_host):
        self._host=existing_host
        self._context=None
        self._used_attachment=False
        self._next=0
        self._busy=False
        self._failed=False
        self._schedule=()
        self._preclaim_sha=None

    def validate_preclaim(self, runtime_contract):
        """Pure local binding verification, no host read or claim allocation."""
        need(not self._used_attachment and not self._failed and self._preclaim_sha is None)
        try:
            need(runtime_contract['status']=='ADMITTED_EXACT_FINANCIAL_RUNTIME'
                 and runtime_contract['execution_authorized'] is True)
            own_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            need(runtime_contract['source_pins']['transport']==own_sha
                 and runtime_contract['required_actual_before_any_claim']['actual_transport_source_sha256']==own_sha)
            need(self._host.verify_preclaim(runtime_contract) is True)
            self._preclaim_sha=hashlib.sha256(json.dumps(runtime_contract,sort_keys=True,
                separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
            return True
        except BaseException:
            self._failed=True
            raise TransportHold('FIXED_FINANCIAL_TRANSPORT_PRECLAIM_HOLD') from None

    def attach_claim(self, context):
        need(not self._used_attachment and not self._failed and self._preclaim_sha is not None)
        self._used_attachment=True  # Unknown attachment cannot be retried.
        try:
            context.assert_valid()
            runtime=context.runtime_contract
            need(context.runtime_sha256==self._preclaim_sha)
            own_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            need(runtime['source_pins']['transport']==own_sha)
            need(runtime['required_actual_before_any_claim']['actual_transport_source_sha256']==own_sha)
            need(runtime['fixed_query_plan']['path']==str(PLAN)
                 and runtime['fixed_query_plan']['sha256']==PLAN_SHA)
            fd=os.open(PLAN,os.O_RDONLY|os.O_NOFOLLOW)
            with os.fdopen(fd,'rb') as stream:
                info=os.fstat(stream.fileno())
                need(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid()
                     and stat.S_IMODE(info.st_mode)==0o600 and info.st_size<=1048576)
                raw=stream.read(1048577)
            need(len(raw)<=1048576 and hashlib.sha256(raw).hexdigest()==PLAN_SHA)
            p=json.loads(raw)
            need(p['target']==runtime['target'] and p['source_binding']==runtime['expected_component'])
            main=runtime['required_actual_before_any_claim']['admission_controller_commit_sha']
            need(type(main) is str and re.fullmatch('[a-f0-9]{40}',main) is not None)
            target=json.loads(json.dumps(p['target'],sort_keys=True))
            native=('railway_graphql',{'query':_native_query(p)})
            describe=('describe_service',target)
            staged=('staged_changes',target)
            self._schedule=(('github_ref',{'branch':'main'}),
                ('github_ref',{'branch':'codex/main-approved-integration'}),
                native,describe,staged,native,describe,staged)
            self._expected_refs=(main,PAYMENT)
            # No platform authority is inferred from an object or source hash.
            need(self._host.verify_local_binding(context) is True)
            context.assert_valid()
            self._context=context
        except BaseException:
            self._failed=True
            raise TransportHold('FIXED_FINANCIAL_TRANSPORT_ATTACHMENT_HOLD') from None

    async def _read(self, operation, argument):
        try:
            need(self._context is not None and not self._failed and not self._busy
                 and self._next<len(self._schedule))
            self._context.assert_valid()
            need(self._schedule[self._next]==(operation,argument))
            need(self._host.verify_local_binding(self._context) is True)
            index=self._next
            self._next+=1  # Dispatch consumes the fixed position even on UNKNOWN.
            self._busy=True
            copied=json.loads(json.dumps(argument,sort_keys=True,allow_nan=False))
            task=asyncio.create_task(self._host.read_exact(operation,copied,self._context))
            self._context.track_future(task)
            result=await asyncio.shield(task)
            self._context.assert_valid()
            need(type(result) is dict)
            if operation=='github_ref':
                need(set(result)=={'sha'} and result['sha']==self._expected_refs[index])
                return result['sha']
            return result
        except BaseException:
            self._failed=True
            raise TransportHold('FIXED_FINANCIAL_TRANSPORT_UNKNOWN_NO_RETRY') from None
        finally:
            self._busy=False

    async def github_ref(self, branch):
        return await self._read('github_ref',{'branch':branch})

    async def railway_graphql(self, query):
        return await self._read('railway_graphql',{'query':query})

    async def describe_service(self, target):
        return await self._read('describe_service',target)

    async def staged_changes(self, target):
        return await self._read('staged_changes',target)

if __name__=='__main__':
    raise SystemExit('PREPARATION_ONLY_NO_STANDALONE_TRANSPORT')
