"""Covered-parent bridge to the existing controllers; execution is default-denied.

Preparation is not authority. Current-owner authority is a trusted executor
boundary independent of the real GitHub owner review, which authenticates N and
therefore the exact provider binding P/upload U/acceptance contract A beneath it.
No caller-supplied approval dictionary is accepted by the execution methods.
"""
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re
import subprocess
from scripts import reader612_native_restore as native
from scripts.backend_upload_payload import qualify as upload_qualify
from scripts.reader612_recovery_source import qualify_binding
from scripts.reader612_protected_approval import GitHubProtectedApprovalResolver, local_git
from scripts.india_release_provider_adapter import (
    ProviderAdapter, ReleaseController, digest, PROJECT, TEAM, RAILWAY_PROJECT,
    SERVICE, ENVIRONMENT, _read_journal, _durable_json, qualify_bootstrap_recovery,
)

ROOT=Path(__file__).resolve().parents[1]
ROLE_ROOT=Path('/private/tmp/earnalism-reader612-closed-role-20261101')
OWNER_SCOPE={'guarded_native_qualification','temporary_purchase_pause','conditional_baseline_restore_reopen',
    'separate_closed_source_exception','preserve_reader_listener','no_paid_sessions','no_financial_mutations',
    'no_resources_settings_redis_or_us_changes'}
SCHEMA='earnalism.reader612-reviewed-bridge.v1'


def need(ok,message):
    if not ok:raise ValueError(message)


def covered_envelope(upload,provider,acceptance):
    return {'schema':SCHEMA,'upload_payload':upload,'provider_binding':provider,'acceptance_contract':acceptance}


def restore_envelope(upload,provider,acceptance,receipt):
    return {'schema':'earnalism.reader612-reviewed-restore.v1','upload_payload':upload,
        'bootstrap_provider_binding':provider,'acceptance_contract':acceptance,
        'qualified_native_receipt_sha256':receipt['recovery_receipt_sha256']}


class Reader612PhaseBridge:
    def __init__(self,role_root=ROLE_ROOT,*,collector=None,clock=lambda:datetime.now(timezone.utc)):
        self.role_root=Path(role_root).resolve();self.clock=clock
        self.source_binding=json.loads((ROOT/'internal/release/reader612_native_preparation.json').read_text())
        self.acceptance=json.loads((ROOT/'internal/release/reader612_phase_acceptance.json').read_text())
        if collector is None:
            from scripts.reader612_phase_collectors import Reader612PhaseCollector
            collector=Reader612PhaseCollector(ROOT,role_source_root=self.role_root,run=subprocess.run,clock=clock)
        self.collector=collector

    def _owner_scope(self,record,controller):
        required={'schema','authority_kind','native_turn_id','instruction_sha256','accepted_at','controller_sha','source_sha','scope'}
        need(isinstance(record,dict) and set(record)==required,'Current native owner scope record required; local approved flag is not authority')
        need(record['schema']=='earnalism.reader612-native-owner-scope.v1'
            and record['authority_kind']=='ACTUAL_CURRENT_NATIVE_OWNER_INSTRUCTION'
            and re.fullmatch('[0-9a-f-]{36}',record['native_turn_id'] or '')
            and native.HASH.fullmatch(record['instruction_sha256'] or '')
            and record['controller_sha']==controller and record['source_sha']==self.source_binding['source_sha'],
            'Owner source/controller/native instruction scope mismatch')
        need(set(record['scope'])==OWNER_SCOPE and all(x is True for x in record['scope'].values()),'Complete exact bounded owner scope required')
        accepted=datetime.fromisoformat(record['accepted_at']);now=self.clock()
        need(accepted.tzinfo is not None and timedelta(0)<=now-accepted<timedelta(hours=24),'Historical/future owner instruction cannot authorize this operation')
        return digest(record)

    def prepare_qualification(self,owner_record,config_sha256):
        """Offline files only. Returns bindings, never approval or execution flags."""
        controller=local_git('rev-parse','HEAD')
        need(not local_git('status','--porcelain','--untracked-files=all'),'Exact clean controller required before binding')
        native.qualify_controller_preparation(self.source_binding)
        owner_digest=self._owner_scope(owner_record,controller)
        need(native.HASH.fullmatch(config_sha256 or '') and config_sha256!='0'*64,'Actual config digest required')
        # This is a prospective source profile, not evidence of live flags. The
        # collector must independently prove actual effective runtime flags OFF.
        source=qualify_binding(self.role_root,self.source_binding,environment=dict.fromkeys(
            ('REDIS_CACHE_ENABLED','REDIS_PUBLIC_METADATA_ENABLED','MULTI_REPLICA_ENABLED'),'false'))
        upload=upload_qualify(self.role_root);s=self.source_binding
        need(digest(self.acceptance)==s['acceptance_contract_sha256'],'Reviewed acceptance contract differs')
        provider={'source_sha':s['source_sha'],'source_root':str(self.role_root),
            'frontend_deployment_id':self.acceptance['frontend_deployment_id'],
            'frontend_source_sha':self.acceptance['frontend_source_sha'],
            'backend_payload_sha256':digest(upload),'source_delivery_sha256':source['runtime_sha256'],
            'closed_server_sha256':s['closed_server_sha256'],'native_pause_acceptance_sha256':owner_digest,
            'purchase_mode':'CLOSED','current_backend_deployment_id':s['retained_backend'],
            'current_backend_source_sha':s['prior_reader_source'],'config_sha256':config_sha256}
        binding={'source_sha':s['source_sha'],'tree_sha':s['tree_sha'],'baseline_source_sha':s['prior_reader_source'],
            'role':native.ROLE,'project':RAILWAY_PROJECT,'service':SERVICE,'environment':ENVIRONMENT,
            'baseline_deployment_id':s['retained_backend'],'baseline_image':s['retained_image'],
            'baseline_snapshot':s['retained_snapshot'],'current_deployment_id':s['retained_backend'],
            'payload_sha256':digest(covered_envelope(upload,provider,self.acceptance)),
            'runtime_sha256':s['runtime_sha256'],'manifest_sha256':hashlib.sha256((self.role_root/'backend/.runtime-source-manifest.json').read_bytes()).hexdigest(),
            'config_sha256':config_sha256,'baseline_runtime_sha256':self.acceptance['phase_policy']['baseline_runtime_sha256'],
            'controller_sha256':hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest(),
            'support_sha256':native.support_identity(),'journal_identity_sha256':native.journal_identity(native.CANONICAL_JOURNAL)}
        native.validate_binding(binding)
        return {'scope':'OFFLINE_PREPARATION_NOT_AUTHORITY','controller_sha':controller,
            'native_binding':binding,'provider_binding':provider,'upload_payload':upload,'acceptance_contract':self.acceptance}

    def _verify_prepared(self,prepared,owner_record):
        need(prepared['scope']=='OFFLINE_PREPARATION_NOT_AUTHORITY','Only exact prepared phase binding admitted')
        need(prepared['acceptance_contract']==self.acceptance,'Acceptance overrides forbidden')
        actual=self.prepare_qualification(owner_record,prepared['provider_binding']['config_sha256'])
        need(actual==prepared,'Source/payload/controller/owner/journal/phase changed since approval binding')
        return actual

    def _resolver(self,run_id,prepared,operator):
        return GitHubProtectedApprovalResolver(run_id,prepared['controller_sha'],operator,clock=self.clock)

    def _expectations(self,prepared):
        return {**self.acceptance,'acceptance_contract':self.acceptance,
            'provider_binding':prepared['provider_binding'],'upload_payload':prepared['upload_payload'],
            'native_binding':prepared['native_binding'],'role_binding':self.source_binding}

    def _coverage(self,record):
        approval_sha=record.get('approval_sha256','')
        need(native.HASH.fullmatch(approval_sha),'Actual qualification approval reference missing')
        coverage=_read_journal(native.CANONICAL_JOURNAL/(approval_sha+'.coverage.request.json'))
        prepared=coverage['prepared']
        need(coverage.get('scope')=='AUTHENTIC_COVERED_PARENT_NOT_STANDALONE_AUTHORITY'
            and coverage['provider_approval']['covered_parent_admission_sha256']==digest(coverage['admission'])
            and coverage['admission']['binding_sha256']==digest(prepared['native_binding'])
            and digest(coverage['owner_scope_record'])==record['binding']['native_pause_acceptance_sha256']
            and digest(coverage['preflight_proof'])==coverage['admission']['observed_proof_sha256']
            and digest(coverage['provider_approval'])==approval_sha
            and coverage['provider_approval']['binding_sha256']==digest(record['binding'])
            and prepared['provider_binding']==record['binding']
            and prepared['acceptance_contract']==self.acceptance
            and prepared['native_binding']['payload_sha256']==digest(covered_envelope(
                prepared['upload_payload'],record['binding'],self.acceptance))
            and coverage['provider_approval']['covered_parent_binding_sha256']==digest(prepared['native_binding'])
            and coverage['provider_approval']['covered_parent_reference']==coverage['admission']['authority_receipt_sha256'],
            'Stored authentic covered-parent qualification differs')
        return coverage

    def _persist_actual(self,actual):
        need(native.HASH.fullmatch(actual.get('receipt_sha256','')),'Actual outcome receipt identity missing')
        need(actual['receipt_sha256']==digest({k:v for k,v in actual.items() if k!='receipt_sha256'}),'Actual outcome receipt digest differs')
        path=native.CANONICAL_JOURNAL/(actual['receipt_sha256']+'.actual.request.json')
        if path.exists():need(_read_journal(path)==actual,'Existing outcome receipt differs')
        else:_durable_json(path,actual,exclusive=True)
        return actual

    def perform_qualification(self,prepared,owner_record,run_id,reference,operator,*,execution_enabled=False,current_owner_authorized=False):
        need(execution_enabled is True and current_owner_authorized is True,'Current owner prohibits native execution; default denied')
        prepared=self._verify_prepared(prepared,owner_record)
        native._prepare_journal(native.CANONICAL_JOURNAL)
        n,p=prepared['native_binding'],prepared['provider_binding']
        proof=self.collector.collect_preflight(n,self.source_binding,self._expectations(prepared))
        resolver=self._resolver(run_id,prepared,operator)
        admission=native.admit_qualification(n,reference,execution_enabled=True,
            protected_gate=resolver,source_observer=lambda _:proof,clock=self.clock)
        gate=resolver(reference,'release_guarded_bootstrap',digest(n))
        actual=proof['provider_actual']
        need(actual['source_sha']==p['source_sha'] and actual['backend_payload_sha256']==digest(prepared['upload_payload'])
            and actual['config_sha256']==n['config_sha256'] and actual['qualified'] is True,'Actual provider projection differs from covered parent')
        # Projection follows actual authenticated parent admission; never accept
        # an input approved=True or silently replace an unrelated binding digest.
        approval={'schema':'earnalism-india-protected-operation.v1','action':'release_guarded_bootstrap',
            'binding_sha256':digest(p),'project':PROJECT,'team':TEAM,'railway_project':RAILWAY_PROJECT,
            'service':SERVICE,'environment':ENVIRONMENT,'territories':['IN'],'auto_deploy':False,'approved':True,
            'provider_identity_sha256':actual['provider_identity_sha256'],'config_sha256':actual['config_sha256'],
            'bootstrap_preflight_sha256':actual['bootstrap_preflight_sha256'],'rollback_operator':gate['rollback_operator'],
            'approved_at':gate['issued_at'],'expires_at':gate['expires_at'],'provider_observed_at':proof['observed_at'],
            'covered_parent_binding_sha256':digest(n),'covered_parent_reference':reference,
            'covered_parent_admission_sha256':digest(admission)}
        # Recheck canonical identity immediately before constructing the actual
        # adapter; callers cannot redirect it to a fresh journal to replay.
        need(native.journal_identity(native.CANONICAL_JOURNAL)==n['journal_identity_sha256'],'Canonical journal changed')
        def observe(action,binding):
            need(action=='release_guarded_bootstrap' and binding==p,'Unexpected provider action or binding')
            # Reuse the one genuine bounded preflight snapshot, not a second
            # snapshot with different request IDs/nonces. Enforce its age and
            # canonical identity immediately before the existing adapter write.
            native.fresh(proof['observed_at'],self.clock())
            need(native.journal_identity(native.CANONICAL_JOURNAL)==n['journal_identity_sha256'],'Canonical journal changed')
            return actual
        coverage={'scope':'AUTHENTIC_COVERED_PARENT_NOT_STANDALONE_AUTHORITY','prepared':prepared,
            'provider_approval':approval,'admission':admission,'owner_scope_record':owner_record,'preflight_proof':proof}
        path=native.CANONICAL_JOURNAL/(digest(approval)+'.coverage.request.json')
        if path.exists():need(_read_journal(path)==coverage,'Existing covered-parent receipt differs')
        else:_durable_json(path,coverage,exclusive=True)
        adapter=ProviderAdapter(native.CANONICAL_JOURNAL,owner_authorized=True,observe=observe,clock=self.clock)
        return ReleaseController(adapter).perform('release_guarded_bootstrap',p,approval)

    def _closed_probe_once(self,record):
        """Durable at-most-once probe; crash uncertainty never permits replay."""
        path=native.CANONICAL_JOURNAL/(record['operation_id']+'.closed-probe.request.json')
        def probe(method,url,body,*,phase_identity):
            need(isinstance(phase_identity,dict) and set(phase_identity)=={'deployment_id','image','snapshot','runtime_sha256','config_sha256'}
                and native.UUID.fullmatch(phase_identity['deployment_id'] or '')
                and native.UUID.fullmatch(phase_identity['snapshot'] or '')
                and re.fullmatch(r'sha256:[a-f0-9]{64}',phase_identity['image'] or '')
                and phase_identity['runtime_sha256']==record['binding']['source_delivery_sha256']
                and phase_identity['config_sha256']==record['binding']['config_sha256'],'Exact observed CLOSED artifact required')
            identity={'operation_id':record['operation_id'],'binding_sha256':digest(record['binding']),'phase':phase_identity}
            need((method,url,body)==('POST','https://theearnalism.com/api/payments/topup',b'{}'),'Only exact inert CLOSED probe admitted')
            if path.exists():
                saved=_read_journal(path)
                need(saved.get('identity')==identity and saved.get('state')=='RESULT_VERIFIED' and saved.get('status')==503
                    and saved.get('cache_control')=='no-store' and saved.get('code')=='PURCHASE_INITIATION_CLOSED'
                    and native.HASH.fullmatch(saved.get('response_sha256','')),'Unknown CLOSED probe; never repeat')
                return 503,{'cache-control':'no-store'},b'{"detail":{"code":"PURCHASE_INITIATION_CLOSED"}}'
            transport=self.collector.purchase_probe
            need(callable(transport),'CLOSED_PROBE_UNBOUND: authorized transport required')
            _durable_json(path,{'identity':identity,'state':'INTENT_NEVER_REPLAY'},exclusive=True)
            status,headers,raw=transport(method,url,body)
            need(status==503 and len(raw)<=65536 and json.loads(raw)['detail']['code']=='PURCHASE_INITIATION_CLOSED'
                and {k.lower():v for k,v in headers.items()}.get('cache-control')=='no-store','CLOSED probe not qualified; never repeat')
            _durable_json(path,{'identity':identity,'state':'RESULT_VERIFIED','status':503,
                'cache_control':'no-store','code':'PURCHASE_INITIATION_CLOSED','response_sha256':hashlib.sha256(raw).hexdigest()})
            return status,headers,raw
        return probe

    def reconcile_qualification(self,operation_id):
        """Read-only outcome collection plus existing durable reconciliation."""
        need(native.HASH.fullmatch(operation_id or ''),'Exact operation required')
        record=_read_journal(native.CANONICAL_JOURNAL/(operation_id+'.json'))
        need(record['action']=='release_guarded_bootstrap','Wrong qualification operation')
        prepared=self._coverage(record)['prepared']
        def observe(action,r):
            need(action=='reconcile' and r==record,'Wrong reconciliation record')
            return self._persist_actual(self.collector.collect_closed(r,self._expectations(prepared),purchase_probe=self._closed_probe_once(r)))
        return ProviderAdapter(native.CANONICAL_JOURNAL,observe=observe,clock=self.clock).reconcile(operation_id)

    def prepare_restore(self,owner_record,qualification_operation):
        # Verify unchanged upload/source/owner; this is still not approval.
        record=_read_journal(native.CANONICAL_JOURNAL/(qualification_operation+'.json'))
        need(record['state']=='APPLIED_VERIFIED' and record['action']=='release_guarded_bootstrap','Actual qualified operation required')
        coverage=self._coverage(record);prepared=coverage['prepared']
        need(local_git('rev-parse','HEAD')==prepared['controller_sha'] and not local_git('status','--porcelain','--untracked-files=all'),'Exact unchanged clean controller required')
        self._owner_scope(owner_record,prepared['controller_sha'])
        need(digest(owner_record)==digest(coverage['owner_scope_record']),'Current scope differs from covered authority')
        native.qualify_controller_preparation(self.source_binding)
        # Restore uploads no source. Verify exact included members and source,
        # but do not invalidate recovery because ignored bytecode count changed.
        source=qualify_binding(self.role_root,self.source_binding,environment=dict.fromkeys(
            ('REDIS_CACHE_ENABLED','REDIS_PUBLIC_METADATA_ENABLED','MULTI_REPLICA_ENABLED'),'false'))
        current=upload_qualify(self.role_root)
        need(current['files']==prepared['upload_payload']['files'] and source['runtime_sha256']==prepared['native_binding']['runtime_sha256'],
            'Qualified source membership changed')
        receipt=_read_journal(native.CANONICAL_JOURNAL/(record['reconciliation_receipt_sha256']+'.actual.request.json'))
        need(receipt['receipt_sha256']==record['reconciliation_receipt_sha256']
            and receipt['receipt_sha256']==digest({k:v for k,v in receipt.items() if k!='receipt_sha256'}),'Stored actual qualification receipt differs')
        qualified=qualify_bootstrap_recovery(record['binding'],receipt)
        need(qualified==record.get('guarded_recovery_receipt_sha256'),'Actual qualified receipt drift')
        binding={**prepared['native_binding'],'current_deployment_id':receipt['deployment_id'],
            'payload_sha256':digest(restore_envelope(prepared['upload_payload'],prepared['provider_binding'],self.acceptance,receipt))}
        native.validate_binding(binding)
        return {'scope':'OFFLINE_RESTORE_PREPARATION_NOT_AUTHORITY','controller_sha':prepared['controller_sha'],
            'native_binding':binding,'qualification_prepared':prepared,'qualified_receipt':receipt,
            'qualification_operation':qualification_operation}

    def perform_restore(self,restoration,owner_record,run_id,reference,operator,schema,*,execution_enabled=False,current_owner_authorized=False):
        need(execution_enabled is True and current_owner_authorized is True,'Current owner prohibits native execution; default denied')
        fresh=self.prepare_restore(owner_record,restoration['qualification_operation'])
        need(fresh==restoration,'Restore phase source/current deployment/qualified receipt drift')
        p=restoration['qualification_prepared'];n=restoration['native_binding']
        resolver=self._resolver(run_id,restoration,operator)
        expected={**self._expectations(p),'qualified_recovery':restoration['qualified_receipt'],
            'qualification_record':_read_journal(native.CANONICAL_JOURNAL/(restoration['qualification_operation']+'.json'))}
        proof=self.collector.collect_restore_preflight(n,restoration['qualified_receipt'],expected)
        from scripts.reader612_native_observer import native_restore_transport
        actual_schema=self.collector.restore_schema()
        need(schema==actual_schema,'Actual native rollback schema differs')
        return native.perform_restore(n,reference,native.CANONICAL_JOURNAL,actual_schema,execution_enabled=True,
            protected_gate=resolver,source_observer=lambda _:proof,transport=native_restore_transport,clock=self.clock)

    def reconcile_restore(self,operation_id):
        """Recover expectations from durable authentic qualification, never caller hints."""
        need(native.HASH.fullmatch(operation_id or ''),'Exact restore operation required')
        record=_read_journal(native.CANONICAL_JOURNAL/(operation_id+'.json'))
        need(record['action']==native.ACTION,'Wrong restore action')
        b=record['binding']
        original=digest({'action':'release_guarded_bootstrap','source_sha':b['source_sha'],
            'candidate':None,'project':RAILWAY_PROJECT,'service':SERVICE,'environment':ENVIRONMENT})
        qualification=_read_journal(native.CANONICAL_JOURNAL/(original+'.json'))
        need(qualification['state']=='APPLIED_VERIFIED' and qualification['action']=='release_guarded_bootstrap','Qualified original operation required')
        p=self._coverage(qualification)['prepared']
        receipt=_read_journal(native.CANONICAL_JOURNAL/(qualification['reconciliation_receipt_sha256']+'.actual.request.json'))
        need(receipt['receipt_sha256']==qualification['reconciliation_receipt_sha256']
            and receipt['receipt_sha256']==digest({k:v for k,v in receipt.items() if k!='receipt_sha256'})
            and qualify_bootstrap_recovery(qualification['binding'],receipt)==qualification['guarded_recovery_receipt_sha256'],
            'Stored qualified artifact receipt differs')
        expected_binding={**p['native_binding'],'current_deployment_id':receipt['deployment_id'],
            'payload_sha256':digest(restore_envelope(p['upload_payload'],p['provider_binding'],self.acceptance,receipt))}
        need(b==expected_binding,'Restore journal differs from authenticated original coverage')
        expected={**self._expectations(p),'qualified_recovery':receipt,'qualification_record':qualification}
        def observe(action,r):
            need(action=='reconcile' and r==record,'Wrong restore reconciliation record')
            return self._persist_actual(self.collector.collect_restored(r,expected))
        return native.reconcile_restore(native.CANONICAL_JOURNAL,operation_id,observer=observe)
