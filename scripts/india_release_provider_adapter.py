"""Reviewed-operation adapter library; no CLI entry point or implicit authority.

Current work is offline only. A future protected controller must supply actual
owner/platform approval and live observers. Modeled receipts cannot establish it.
"""
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import stat
import uuid
import fcntl

PROJECT = 'prj_kxPN55TOJ23lDgoXIXrvqHtzy607'
TEAM = 'team_HAGNRSEiW5MZXY2AhV0cQvE0'
RAILWAY_PROJECT = 'a8533934-35c4-463e-9f43-577a9ac391ee'
SERVICE = '5af42e7e-f518-4f6a-b602-d9950866501f'
ENVIRONMENT = '580b250c-80ee-48ad-bfbe-fa4e31a6b378'
ACTIONS = {'stage_frontend', 'promote_frontend', 'release_backend', 'release_guarded_bootstrap', 'restore_guarded_bootstrap'}
CLI_VERSIONS = {'vercel': '59.25.4', 'railway': '5.71.0'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def process_diagnostic(result=None, error=None):
    """Retain evidence without provider text, credentials, or an outcome inference.

    A CLI error class describes its report only. Even DNS/auth/local errors do
    not clear an operation barrier or authorize a retry.
    """
    def payload(value):
        if isinstance(value, bytes): return value
        if isinstance(value, str): return value.encode('utf-8', errors='replace')
        return b''
    out = payload(getattr(result, 'stdout', None) if error is None else getattr(error, 'stdout', None))
    err = payload(getattr(result, 'stderr', None) if error is None else getattr(error, 'stderr', None))
    text = (out + b'\n' + err).decode('utf-8', errors='replace').lower()
    code = getattr(result, 'returncode', None)
    classes = set()
    if 'dns error' in text and 'failed to lookup address information' in text:
        classes.add('DNS_LOOKUP_FAILED')
    if 'unauthorized' in text or 'please login' in text:
        classes.add('AUTHENTICATION_REPORTED')
    if 'unexpected argument' in text or 'unrecognized option' in text:
        classes.add('CLI_ARGUMENT_REJECTED')
    if 'failed to upload code. file too large' in text:
        classes.add('UPLOAD_SIZE_REJECTED')
    if 'failed to upload code with status code' in text:
        classes.add('UPLOAD_HTTP_REJECTED')
    if error is not None:
        kind = 'PROCESS_TIMEOUT' if isinstance(error, (TimeoutError, subprocess.TimeoutExpired)) else 'PROCESS_EXCEPTION'
    elif code == 0:
        kind = 'PROCESS_EXIT_ZERO'
    else:
        kind = next(iter(classes)) if len(classes) == 1 else 'UNKNOWN_FAILURE'
    return {'schema': 'earnalism-provider-process-diagnostic.v1',
            'class': kind, 'effect': 'UNKNOWN_REQUIRES_NATIVE_RECONCILIATION',
            'stdout_bytes': len(out), 'stderr_bytes': len(err),
            'stdout_sha256': hashlib.sha256(out).hexdigest(),
            'stderr_sha256': hashlib.sha256(err).hexdigest()}


def _sync_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)


def _durable_json(path, value, *, exclusive=False, directory_fd=None):
    """No recovery/cleanup on unknown outcomes; permanent intent stays permanent.

    Restore writes may anchor to the already-admitted directory descriptor.
    Other actions preserve the existing path-based behavior.
    """
    path=Path(path)
    temporary=path if exclusive else path.with_name('.'+path.name+'.'+uuid.uuid4().hex+'.pending')
    fd=os.open(temporary if directory_fd is None else temporary.name,
               os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,
               **({} if directory_fd is None else {'dir_fd':directory_fd}))
    with os.fdopen(fd,'w') as stream:
        json.dump(value,stream);stream.flush();os.fsync(stream.fileno())
    if not exclusive:
        if directory_fd is None:os.replace(temporary,path)
        else:os.replace(temporary.name,path.name,src_dir_fd=directory_fd,dst_dir_fd=directory_fd)
    if directory_fd is None:_sync_directory(path.parent)
    else:os.fsync(directory_fd)


def _read_journal(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600 or info.st_size>1024*1024:
            raise ValueError('Unsafe journal record')
        value=json.load(stream)
    if not isinstance(value,dict):raise ValueError('Malformed journal record')
    return value


def _validate_barrier(path, operation_id):
    value=_read_journal(path)
    if set(value)!={'operation_id','state'} or value.get('operation_id')!=operation_id or value.get('state')!='INTENT_RECONCILE_BEFORE_RETRY':
        raise ValueError('Malformed or different operation barrier')


def recovery_digest_field(action, binding):
    if action == 'restore_guarded_bootstrap': return 'guarded_restore_sha256'
    if action == 'release_guarded_bootstrap': return 'bootstrap_preflight_sha256'
    if action in {'stage_frontend', 'promote_frontend'} and binding.get('frontend_phase'):
        return 'frontend_rollback_sha256'
    return 'guarded_rollback_sha256'


def require_digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) and value != '0' * 64


def operation_identity(action, binding):
    """Ordinary identities remain byte-for-byte compatible with old journals."""
    if action == 'restore_guarded_bootstrap':
        normal = binding.get('applied_normal_operation_id')
        if not require_digest(normal): raise ValueError('Exact applied normal root required')
        return digest({'action': action, 'project': RAILWAY_PROJECT, 'service': SERVICE,
                       'environment': ENVIRONMENT, 'applied_normal_operation_id': normal})
    value = {'action': action, 'source_sha': binding['source_sha'],
        'candidate': binding.get('deployment_id') if action == 'promote_frontend' else None,
        'project': RAILWAY_PROJECT if action in {'release_backend', 'release_guarded_bootstrap'} else PROJECT,
        'service': SERVICE if action in {'release_backend', 'release_guarded_bootstrap'} else None,
        'environment': ENVIRONMENT if action in {'release_backend', 'release_guarded_bootstrap'} else 'production'}
    if 'corrective_backend' in binding:
        value['corrective_backend_sha256'] = digest(binding['corrective_backend'])
    return digest(value)


def corrective_predecessor(journal, action, binding, approval):
    """One reviewed policy correction, never a retry or a journal override."""
    if 'corrective_backend' not in binding:
        return None
    c = binding['corrective_backend']
    fields = {'schema', 'failed_operation_id', 'failed_record_sha256',
              'failed_reconciliation_receipt_sha256', 'failed_startup_policy_sha256',
              'failed_policy_marker_identity_sha256', 'policy_change_approval_sha256'}
    if (action != 'release_backend' or not isinstance(c, dict) or set(c) != fields
            or c['schema'] != 'earnalism.corrective-backend-policy.v1'
            or not all(require_digest(c[k]) for k in fields - {'schema'})):
        raise ValueError('Exact corrective backend policy binding required')
    if (not require_digest(binding.get('startup_policy_sha256'))
            or c['failed_startup_policy_sha256'] == binding['startup_policy_sha256']
            or c['failed_policy_marker_identity_sha256'] != binding.get('startup_marker_identity_sha256')
            or approval.get('startup_policy_change_receipt_sha256') != c['policy_change_approval_sha256']):
        raise ValueError('Approved changed policy with identical canaries required')
    old = _read_journal(Path(journal) / (c['failed_operation_id'] + '.json'))
    old_binding = old.get('binding')
    if (old.get('state') != 'NOT_APPLIED_VERIFIED' or old.get('action') != 'release_backend'
            or not isinstance(old_binding, dict) or 'corrective_backend' in old_binding
            or not re.fullmatch('[0-9a-f]{40}', old_binding.get('source_sha', ''))
            or old.get('operation_id') != c['failed_operation_id']
            or operation_identity('release_backend', old_binding) != c['failed_operation_id']
            or digest(old) != c['failed_record_sha256']
            or old.get('reconciliation_receipt_sha256') != c['failed_reconciliation_receipt_sha256']):
        raise ValueError('Immutable terminal ordinary failed predecessor required')
    claim = Path(journal) / ('.corrective-' + c['failed_operation_id'] + '.claim')
    if claim.exists():
        raise FileExistsError('Original failed operation already consumed its one correction')
    return c, claim


def validate_corrective_observation(correction, binding, actual):
    if correction is None:
        return
    c, _ = correction
    observed = actual.get('corrective_backend')
    if (not isinstance(observed, dict)
            or observed.get('scope') != 'ACTUAL_FAILED_OPERATION_AND_APPROVED_POLICY_CHANGE'
            or observed.get('policy_change_approved') is not True
            or observed.get('failed_startup_code') != 'STARTUP_DATA_GUARD_PUBLICATION'
            or not require_digest(observed.get('failure_receipt_sha256'))
            or observed.get('railway_project') != RAILWAY_PROJECT
            or observed.get('service') != SERVICE or observed.get('environment') != ENVIRONMENT
            or observed.get('approved_policy_sha256') != binding['startup_policy_sha256']
            or any(observed.get(k) != v for k, v in c.items())
            or actual['startup_data_qualification']['marker_count'] != 2):
        raise ValueError('Actual failed-policy and approved two-canary correction proof required')


def validate_action_recovery(action, binding, actual):
    """Trusted live observer only; synthetic tests never create real receipts."""
    if action == 'restore_guarded_bootstrap':
        return  # Full same-journal context checked separately before dispatch.
    if action == 'release_guarded_bootstrap':
        for key in ('native_pause_acceptance_sha256', 'closed_server_sha256', 'source_delivery_sha256'):
            if not require_digest(binding.get(key)) or actual.get(key) != binding[key]:
                raise ValueError('Exact native pause/CLOSED source binding missing: ' + key)
        if binding.get('purchase_mode') != 'CLOSED' or actual.get('purchase_mode') != 'CLOSED':
            raise ValueError('Only reviewed CLOSED bootstrap is authorized')
        if not actual.get('current_backend_healthy') is True or not actual.get('native_healthcheck_traffic_gating') is True:
            raise ValueError('Actual preactivation health/traffic gating unavailable')
        if actual.get('current_backend_deployment_id') != binding.get('current_backend_deployment_id') or not binding.get('current_backend_deployment_id'):
            raise ValueError('Current serving backend binding missing')
        if actual.get('current_backend_source_sha') != binding.get('current_backend_source_sha') or not re.fullmatch('[0-9a-f]{40}', binding.get('current_backend_source_sha','')):
            raise ValueError('Current backend source binding missing')
        if actual.get('new_resources_or_config_changes') is not False:
            raise ValueError('Bootstrap cannot create resources or change configuration')
        return
    if action in {'stage_frontend', 'promote_frontend'} and binding.get('frontend_phase'):
        phase=binding['frontend_phase']
        if phase not in {'BACKEND_UNCHANGED', 'GUARD_ACTIVE'} or actual.get('frontend_phase') != phase:
            raise ValueError('Unknown frontend transition phase')
        for key in ('backend_source_sha','rollback_frontend_source_sha'):
            if not re.fullmatch('[0-9a-f]{40}',binding.get(key,'')) or actual.get(key)!=binding[key]:
                raise ValueError('Frontend/backend rollback source mismatch')
        if not binding.get('rollback_frontend_deployment_id') or actual.get('rollback_frontend_deployment_id') != binding['rollback_frontend_deployment_id']:
            raise ValueError('Exact compatible frontend rollback missing')
        if actual.get('frontend_rollback_available') is not True or actual.get('frontend_backend_compatible') is not True:
            raise ValueError('Actual frontend-only recovery unqualified')
        if phase=='GUARD_ACTIVE' and actual.get('rollback_frontend_signed_purchase_ready') is not True:
            raise ValueError('Unsigned frontend cannot recover guarded backend')
        if phase=='BACKEND_UNCHANGED' and actual.get('backend_unchanged') is not True:
            raise ValueError('Old frontend rollback only while backend unchanged')
        return
    if action=='release_backend' and (not require_digest(binding.get('guarded_recovery_receipt_sha256')) or actual.get('guarded_recovery_receipt_sha256')!=binding['guarded_recovery_receipt_sha256']):
        raise ValueError('Bound actual bootstrap recovery receipt required')
    if actual.get('guarded_rollback_available') is not True:
        raise ValueError('Guard-preserving rollback unavailable')


def qualify_bootstrap_recovery(binding, actual):
    """Post-write actual read-only qualification; never a preflight PASS substitute."""
    if actual.get('scope')!='ACTUAL_PROVIDER_AND_SOURCE' or actual.get('action')!='release_guarded_bootstrap' or actual.get('source_sha')!=binding['source_sha']:
        raise ValueError('Actual exact bootstrap observation required')
    for key in ('source_delivery_sha256','closed_server_sha256'):
        if actual.get(key)!=binding.get(key) or not require_digest(actual.get(key)):
            raise ValueError('Bootstrap measured source mismatch')
    if not require_digest(actual.get('config_sha256')) or actual.get('config_sha256')!=binding.get('config_sha256') or not require_digest(actual.get('recovery_receipt_sha256')):
        raise ValueError('Actual recovery/config digest binding missing')
    for key in ('deployment_id','retained_image_id','config_sha256','recovery_receipt_sha256'):
        if not actual.get(key): raise ValueError('Actual retained recovery evidence missing: '+key)
    for key in ('startup_complete','database_healthy','source_attestation_matches','native_can_rollback','config_compatible','existing_reader_listener_preserved','verify_refund_webhook_code_preserved'):
        if actual.get(key) is not True:raise ValueError('Bootstrap not qualified: '+key)
    if actual.get('closed_guest_status')!=503 or actual.get('purchase_pause_proof') != 'MEASURED_EXACT_EARLY_RETURN_AND_ANONYMOUS_503':
        raise ValueError('Purchase pause is not genuinely qualified')
    if actual.get('guarded_backend_deployment_id')!=actual['deployment_id']:
        raise ValueError('Recovery artifact identity mismatch')
    return actual['recovery_receipt_sha256']


RESTORE_FIELDS = {'operations_journal_identity_sha256', 'applied_normal_operation_id', 'applied_normal_record_sha256',
    'applied_normal_reconciliation_receipt_sha256', 'bootstrap_operation_id',
    'bootstrap_record_sha256', 'guarded_recovery_receipt_sha256', 'target_deployment_id',
    'target_retained_image_id', 'target_runtime_sha256', 'target_config_sha256',
    'target_source_sha', 'current_bad_normal_deployment_id', 'bad_normal_failure_receipt_sha256',
    'actual_native_schema_sha256'}

def _operation_journal_identity(journal):
    """Bind future backend receipts to their existing admitted physical journal.

    This is custody, not a new approval or a transferable journal override.
    A copied/restored namespace must not reset a normal operation's return claim.
    """
    path = Path(journal)
    if not path.is_absolute() or path.is_symlink():
        raise ValueError('Exact admitted operations journal required')
    # Normalize OS aliases (for example /var -> /private/var); the same
    # physical namespace keeps one identity and one permanent claim.
    path = path.resolve()
    rows = []
    for item in (path.parent, path):
        info = item.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) & 0o022):
            raise ValueError('Private owner-matched journal custody required')
        rows.append({'path': str(item), 'device': info.st_dev, 'inode': info.st_ino,
                     'uid': info.st_uid, 'mode': stat.S_IMODE(info.st_mode)})
    return digest(rows)


def _assert_operation_journal_anchor(journal, descriptor, expected):
    if _operation_journal_identity(journal) != expected:
        raise ValueError('Admitted journal custody changed before native dispatch')
    opened = os.fstat(descriptor)
    current = Path(journal).lstat()
    fields = lambda info: (info.st_dev, info.st_ino, info.st_uid, stat.S_IMODE(info.st_mode))
    if fields(opened) != fields(current):
        raise ValueError('Admitted journal descriptor no longer matches namespace')


def validate_guarded_restore_context(journal, binding, actual, approval=None):
    """Exact same-journal lineage; live fields come only from trusted observer.

    This is not an observer implementation or authority factory. Missing actual
    receipts/capabilities deny rather than inferring native readiness from tests.
    """
    c = binding.get('restore_context')
    if not isinstance(c, dict) or set(c) != RESTORE_FIELDS:
        raise ValueError('Exact guarded restore context required')
    if binding.get('applied_normal_operation_id') != c['applied_normal_operation_id']:
        raise ValueError('Permanent normal root differs')
    for key in RESTORE_FIELDS - {'target_deployment_id','current_bad_normal_deployment_id','target_retained_image_id','target_source_sha'}:
        if not require_digest(c[key]): raise ValueError('Missing restore digest: ' + key)
    if not re.fullmatch('[a-f0-9]{40}', c['target_source_sha']) or binding.get('source_sha') != c['target_source_sha']:
        raise ValueError('Exact target source required')
    records=[]
    for p in Path(journal).glob('*.json'):
        if p.name.endswith('.request.json') or p.name=='_write-barrier.json': continue
        records.append(_read_journal(p))
    def one(operation, action, record_hash):
        rows=[r for r in records if r.get('operation_id')==operation]
        if len(rows)!=1: raise ValueError('Unique permanent predecessor required')
        r=rows[0]
        if (r.get('action')!=action or r.get('state')!='APPLIED_VERIFIED'
                or digest(r)!=record_hash or not require_digest(r.get('reconciliation_receipt_sha256'))
                or operation_identity(action,r['binding'])!=operation):
            raise ValueError('Exact APPLIED predecessor required')
        return r
    normal=one(c['applied_normal_operation_id'],'release_backend',c['applied_normal_record_sha256'])
    boot=one(c['bootstrap_operation_id'],'release_guarded_bootstrap',c['bootstrap_record_sha256'])
    custody = _operation_journal_identity(journal)
    if (c['operations_journal_identity_sha256'] != custody
            or normal.get('operations_journal_identity_sha256') != custody
            or boot.get('operations_journal_identity_sha256') != custody):
        raise ValueError('Original admitted backend journal custody differs')
    recovery=c['guarded_recovery_receipt_sha256']
    if (normal['reconciliation_receipt_sha256']!=c['applied_normal_reconciliation_receipt_sha256']
            or normal['binding'].get('guarded_recovery_receipt_sha256')!=recovery
            or boot.get('guarded_recovery_receipt_sha256')!=recovery
            or boot['binding']['source_sha']!=c['target_source_sha']
            or boot['binding'].get('config_sha256')!=c['target_config_sha256']):
        raise ValueError('Normal/bootstrap recovery lineage differs')
    # No caller-provided query. Reuse only the pure scalar schema serializer.
    from scripts.reader612_native_restore import rollback_document
    schema=actual.get('native_rollback_schema')
    rollback_document(schema,c['target_deployment_id'])
    if digest(schema)!=c['actual_native_schema_sha256']:
        raise ValueError('Fresh native schema differs')
    # This action returns an unchanged retained configuration, not a config
    # migration. Current admission/startup and target must be the same bytes.
    config=c['target_config_sha256']
    startup=actual.get('startup_data_qualification')
    if (binding.get('config_sha256')!=config or actual.get('config_sha256')!=config
            or not isinstance(startup,dict) or startup.get('config_sha256')!=config
            or (approval is not None and approval.get('config_sha256')!=config)):
        raise ValueError('Admitted startup/approval configuration differs from target')
    proof=boot.get('qualified_bootstrap_evidence')
    if not isinstance(proof,dict) or actual.get('qualified_bootstrap_receipt')!=proof:
        raise ValueError('Permanent original bootstrap evidence required')
    if not isinstance(proof,dict) or qualify_bootstrap_recovery(boot['binding'],proof)!=recovery:
        raise ValueError('Actual qualified bootstrap receipt missing')
    for key, expected in {'deployment_id':c['target_deployment_id'], 'retained_image_id':c['target_retained_image_id'],
            'runtime_sha256':c['target_runtime_sha256'],'config_sha256':c['target_config_sha256']}.items():
        if proof.get(key)!=expected: raise ValueError('Retained target differs: '+key)
    runtime=c['target_runtime_sha256']
    if not all(value==runtime for value in (boot['binding'].get('source_delivery_sha256'),
            proof.get('source_delivery_sha256'),proof.get('runtime_sha256'),
            binding.get('source_delivery_sha256'))):
        raise ValueError('Original delivered/measured target runtime differs')
    closed=boot['binding'].get('closed_server_sha256')
    if (not require_digest(closed) or binding.get('closed_server_sha256')!=closed
            or proof.get('closed_server_sha256')!=closed):
        raise ValueError('Admitted CLOSED server differs from original target')
    if normal.get('provider_backend_deployment_id')!=c['current_bad_normal_deployment_id']:
        raise ValueError('Applied normal lacks exact permanent native identity')
    native=actual.get('retained_bootstrap_native')
    expected_native={k:c[v] for k,v in {'deployment_id':'target_deployment_id','retained_image_id':'target_retained_image_id','runtime_sha256':'target_runtime_sha256','config_sha256':'target_config_sha256','source_sha':'target_source_sha'}.items()}
    expected_native['native_can_rollback']=True
    if native!=expected_native:
        raise ValueError('Fresh actual retained bootstrap identity differs')
    if not c['target_retained_image_id'] or binding.get('source_delivery_sha256')!=c['target_runtime_sha256']:
        raise ValueError('Exact target runtime/image required')
    for key in ('native_restore_available','installed_policy_compatible','known_normal_failure_qualified'):
        if actual.get(key) is not True: raise ValueError('Actual restore precondition missing: '+key)
    for key,expected in {'current_bad_normal_deployment_id':c['current_bad_normal_deployment_id'],
        'bad_normal_failure_receipt_sha256':c['bad_normal_failure_receipt_sha256'],
        'applied_normal_source_sha':normal['binding']['source_sha'],
        'guarded_restore_sha256':digest(c)}.items():
        if not expected or actual.get(key)!=expected: raise ValueError('Actual failure/context differs: '+key)
    failure=actual.get('bad_normal_failure_receipt')
    if (not isinstance(failure,dict) or digest(failure)!=c['bad_normal_failure_receipt_sha256']
            or failure.get('scope')!='ACTUAL_APPLIED_NORMAL_FAILURE'
            or failure.get('operation_id')!=normal['operation_id']
            or failure.get('normal_reconciliation_receipt_sha256')!=normal['reconciliation_receipt_sha256']
            or failure.get('deployment_id')!=c['current_bad_normal_deployment_id']
            or failure.get('source_sha')!=normal['binding']['source_sha']
            or failure.get('project')!=RAILWAY_PROJECT or failure.get('service')!=SERVICE
            or failure.get('environment')!=ENVIRONMENT):
        raise ValueError('Exact actual applied normal failure receipt required')
    if datetime.fromisoformat(normal['started_at']) <= datetime.fromisoformat(boot['started_at']):
        raise ValueError('Normal does not follow bootstrap')
    return c


def validate_approval(action, binding, approval, owner_authorized, now):
    if owner_authorized is not True:
        raise ValueError('Current owner instruction prohibits provider execution')
    if action not in ACTIONS or not re.fullmatch('[0-9a-f]{40}', binding.get('source_sha', '')):
        raise ValueError('Invalid action/source')
    expected = {'schema': 'earnalism-india-protected-operation.v1', 'action': action,
                'binding_sha256': digest(binding), 'project': PROJECT, 'team': TEAM,
                'railway_project': RAILWAY_PROJECT, 'service': SERVICE,
                'environment': ENVIRONMENT, 'territories': ['IN'], 'auto_deploy': False,
                'approved': True}
    for key, value in expected.items():
        if type(approval.get(key)) is not type(value) or approval[key] != value:
            raise ValueError('Protected approval mismatch: ' + key)
    for key in ('provider_identity_sha256', 'config_sha256', recovery_digest_field(action, binding)):
        if not isinstance(approval.get(key), str) or not re.fullmatch('[0-9a-f]{64}', approval[key]) or approval[key] == '0' * 64:
            raise ValueError('Missing actual evidence digest: ' + key)
    if not approval.get('rollback_operator'):
        raise ValueError('Missing actual rollback operator')
    start = datetime.fromisoformat(approval['approved_at'])
    end = datetime.fromisoformat(approval['expires_at'])
    observed = datetime.fromisoformat(approval['provider_observed_at'])
    if any(d.tzinfo is None for d in (start, end, observed, now)):
        raise ValueError('Naive approval time')
    if not start <= now < end or end - start > timedelta(hours=24):
        raise ValueError('Expired/future/overlong approval')
    if not timedelta(0) <= now - observed <= timedelta(minutes=15):
        raise ValueError('Stale or future provider evidence')


def _paired_bootstrap_payload(controller, binding):
    """Only exact committed CLOSED export admission; no native PASS is inferred."""
    from scripts.backend_upload_payload import qualify_committed_export
    payload = qualify_committed_export(controller, binding['source_sha'], binding['backend_export_root'])
    root = Path(binding['backend_export_root']).resolve()
    expected = {'scope': 'OFFLINE_EXACT_COMMITTED_EXPORT_NOT_NATIVE_ARCHIVE_OR_PROVIDER_UPLOAD',
        'cli_version': CLI_VERSIONS['railway'], 'source': binding['source_sha'],
        'controller_source': binding['controller_source_sha'], 'archive_prefix': str(root),
        'input_path': str(root / 'backend'), 'path_as_root': False,
        'archive_member_prefix': 'backend/', 'native_archive_qualification': False}
    for key, value in expected.items():
        if type(payload.get(key)) is not type(value) or payload[key] != value:
            raise ValueError('Exact paired CLOSED export report differs: ' + key)
    return payload


class ProviderAdapter:
    def __init__(self, journal, *, owner_authorized=False, observe=None,
                 run=subprocess.run, clock=lambda: datetime.now(timezone.utc)):
        self.journal = Path(journal)
        self.owner_authorized, self.observe = owner_authorized, observe
        self.run, self.clock = run, clock

    def _command(self, action, binding, request_path, *, backend_payload=None):
        if 'backend_export_root' in binding and action != 'release_guarded_bootstrap':
            raise ValueError('Committed export is only admitted for CLOSED bootstrap')
        if action == 'stage_frontend':
            return ['vercel', 'api', '/v13/deployments', '--method', 'POST',
                    '--input', str(request_path), '--raw', '--scope', TEAM]
        if action == 'promote_frontend':
            if not re.fullmatch(r'dpl_[A-Za-z0-9]+', binding.get('deployment_id', '')):
                raise ValueError('Invalid exact candidate identity')
            return ['vercel', 'promote', binding['deployment_id'], '--yes', '--scope', TEAM]
        if action == 'restore_guarded_bootstrap':
            from scripts.reader612_native_restore import rollback_document
            schema = binding['native_rollback_schema']
            query = rollback_document(schema, binding['restore_context']['target_deployment_id'])
            return ['railway', 'api', query, '--compact']
        if action not in {'release_backend', 'release_guarded_bootstrap'}:
            raise ValueError('Unknown provider action')
        input_path = str(Path(binding['source_root']).resolve() / 'backend')
        if 'backend_export_root' in binding:
            if not isinstance(backend_payload, dict) or digest(backend_payload) != binding.get('backend_payload_sha256'):
                raise ValueError('Qualified paired export payload required for command')
            input_path = backend_payload['input_path']
        return ['railway', 'up', '--ci', '--project', RAILWAY_PROJECT,
                '--service', SERVICE, '--environment', ENVIRONMENT, '--json', input_path]

    def perform(self, action, binding, approval):
        validate_approval(action, binding, approval, self.owner_authorized, self.clock())
        paired = 'backend_export_root' in binding
        if paired and (action != 'release_guarded_bootstrap'
                or not re.fullmatch('[0-9a-f]{40}', binding.get('controller_source_sha', ''))):
            raise ValueError('Exact normal controller is required only for paired CLOSED bootstrap')
        correction = corrective_predecessor(self.journal, action, binding, approval)
        operation_id = operation_identity(action, binding)
        path = self.journal / (operation_id + '.json')
        if path.exists():
            raise FileExistsError('Provider operation already has a durable intent')
        if action == 'restore_guarded_bootstrap':
            claim = self.journal / ('.guarded-return-' + binding['applied_normal_operation_id'] + '.claim')
            if claim.exists():
                raise FileExistsError('Applied normal operation already consumed its guarded return')
        # A local path, additional binding field or changed approval must never
        # turn one unknown remote write into another permitted operation.
        prior_records = []
        for prior in self.journal.glob('*.json'):
            if prior.name.endswith('.request.json'):
                continue
            record = _read_journal(prior)
            prior_records.append(record)
            if record.get('state') not in {'APPLIED_VERIFIED', 'NOT_APPLIED_VERIFIED'}:
                raise FileExistsError('Unresolved provider write requires read-only reconciliation')
        if action == 'release_backend' and correction is None:
            # A controller-only/empty source commit must not mint a retry of
            # the same failed delivered backend under a new Git SHA.
            for old in prior_records:
                if (old.get('action') == 'release_backend' and old.get('state') == 'NOT_APPLIED_VERIFIED'
                        and 'corrective_backend' not in old.get('binding', {})
                        and require_digest(binding.get('source_delivery_sha256'))
                        and old.get('binding', {}).get('source_delivery_sha256') == binding['source_delivery_sha256']):
                    resolved = any(r.get('action') == 'release_backend' and r.get('state') == 'APPLIED_VERIFIED'
                        and require_digest(r.get('reconciliation_receipt_sha256'))
                        and r.get('binding', {}).get('corrective_backend', {}).get('schema') == 'earnalism.corrective-backend-policy.v1'
                        and r.get('binding', {}).get('corrective_backend', {}).get('failed_record_sha256') == digest(old)
                        and r.get('operation_id') == operation_identity('release_backend', r['binding'])
                        and r.get('binding', {}).get('corrective_backend', {}).get('failed_operation_id') == old.get('operation_id')
                        for r in prior_records)
                    if not resolved:
                        raise ValueError('Same failed delivered backend requires explicit corrective binding')
        if self.observe is None:
            raise ValueError('Actual provider/source/config/rollback observer is required')
        # Observer must perform actual read-only source, provider/config, guarded
        # rollback and order checks. It must return the bound approval digests.
        actual = self.observe(action, binding)
        for key in ('provider_identity_sha256', 'config_sha256', recovery_digest_field(action, binding)):
            if actual.get(key) != approval[key]:
                raise ValueError('Live protected evidence differs: ' + key)
        if actual.get('scope') != 'ACTUAL_PROVIDER_AND_SOURCE' or actual.get('qualified') is not True:
            raise ValueError('Actual scoped qualification unavailable')
        if (actual.get('auto_deploy') is not False
                or actual.get('authenticated_provider_account') is not True):
            raise ValueError('Provider suppression/authentication/guarded rollback unverified')
        if action == 'restore_guarded_bootstrap':
            validate_guarded_restore_context(self.journal, binding, actual, approval)
            if binding.get('native_rollback_schema') != actual.get('native_rollback_schema'):
                raise ValueError('Binding native schema differs')
        validate_action_recovery(action, binding, actual)
        cli = 'railway' if action in {'release_backend', 'release_guarded_bootstrap', 'restore_guarded_bootstrap'} else 'vercel'
        if actual.get('cli_version') != CLI_VERSIONS[cli]:
            raise ValueError('Reviewed CLI version differs')
        if action == 'promote_frontend':
            if (actual.get('candidate_id') != binding.get('deployment_id')
                    or actual.get('candidate_source_sha') != binding['source_sha']
                    or actual.get('candidate_target') != 'production'
                    or actual.get('candidate_ready') is not True
                    or actual.get('health_book_statuses') != [200, 200]
                    or actual.get('guest_manifest_status') != 401):
                raise ValueError('Exact tested production candidate unqualified')
        if action in {'release_backend', 'release_guarded_bootstrap'}:
            if (actual.get('frontend_signed_purchase_ready') is not True
                    or not binding.get('frontend_deployment_id')
                    or actual.get('frontend_deployment_id') != binding['frontend_deployment_id']
                    or (action == 'release_backend' and actual.get('startup_qualified') is not True)):
                raise ValueError('Frontend-first/startup prerequisites unqualified')
            from scripts.startup_dispatch_qualification import validate_startup_qualification
            validate_startup_qualification(binding, approval, actual, self.clock())
            validate_corrective_observation(correction, binding, actual)
        if action == 'restore_guarded_bootstrap':
            from scripts.startup_dispatch_qualification import validate_startup_qualification
            validate_startup_qualification(binding, approval, actual, self.clock())
            controller = Path(binding['source_root']).resolve()
            head = subprocess.check_output(['git','-C',str(controller),'rev-parse','HEAD'],text=True).strip()
            dirty = subprocess.check_output(['git','-C',str(controller),'status','--porcelain','--untracked-files=all'],text=True).strip()
            if (head != binding.get('controller_source_sha') or dirty
                    or actual.get('controller_source_sha') != head):
                raise ValueError('Exact clean admitted restore controller required')
        source = Path(binding['source_root']).resolve()
        if action in {'release_backend', 'release_guarded_bootstrap'}:
            # Never upload a dirty or misidentified checkout or accept an input
            # SHA label as the actual source. Provider identity still needs a
            # separate post-write observation before any subsequent action.
            sha = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
            dirty = subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=all'], text=True).strip()
            expected_source = binding['controller_source_sha'] if paired else binding['source_sha']
            if sha != expected_source or dirty:
                raise ValueError('Backend source not exact/clean')
            if paired and actual.get('controller_source_sha') != sha:
                raise ValueError('Actual paired normal controller differs')
            guard_sha = hashlib.sha256((source / 'backend/startup_data_guard.py').read_bytes()).hexdigest()
            if guard_sha != binding['startup_guard_source_sha256']:
                raise ValueError('Measured startup guard source differs')
            # Railway5.71 with explicit --project uses cwd as archive prefix.
            # Absolute backend input keeps backend/ paths; never path-as-root.
            from scripts.backend_upload_payload import qualify
            payload = _paired_bootstrap_payload(source, binding) if paired else qualify(source)
            if (binding.get('backend_payload_sha256') != digest(payload)
                    or actual.get('backend_payload_sha256') != digest(payload)
                    or payload['runtime_expected_sha256'] != binding.get('source_delivery_sha256')):
                raise ValueError('Exact reviewed backend upload payload unqualified')
        # Only one operations directory may be created beneath the existing
        # owner-admitted durable namespace; never recursively create ancestors.
        parent_info=self.journal.parent.lstat()
        if not stat.S_ISDIR(parent_info.st_mode) or parent_info.st_uid!=os.getuid() or stat.S_IMODE(parent_info.st_mode)&0o022:
            raise ValueError('Existing private admitted journal parent required')
        _sync_directory(self.journal.parent)
        self.journal.mkdir(exist_ok=True, mode=0o700)
        info=self.journal.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)&0o022:
            raise ValueError('Unsafe journal directory')
        _sync_directory(self.journal.parent)
        _sync_directory(self.journal)
        if action in {'release_backend', 'release_guarded_bootstrap', 'restore_guarded_bootstrap'}:
            # Recheck freshness after potentially slow source/payload reads.
            validate_approval(action, binding, approval, self.owner_authorized, self.clock())
            validate_startup_qualification(binding, approval, actual, self.clock())
        anchor = None
        if action == 'restore_guarded_bootstrap':
            anchor = os.open(self.journal, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        def durable(path, value, **kwargs):
            if anchor is None:return _durable_json(path, value, **kwargs)
            return _durable_json(path, value, directory_fd=anchor, **kwargs)
        try:
            if anchor is not None:
                _assert_operation_journal_anchor(self.journal, anchor,
                    binding['restore_context']['operations_journal_identity_sha256'])
            barrier = self.journal / '_write-barrier.json'
            durable(barrier, {'operation_id': operation_id, 'state': 'INTENT_RECONCILE_BEFORE_RETRY'}, exclusive=True)
            intent = {'operation_id': operation_id, 'action': action, 'binding': binding,
                      'approval_sha256': digest(approval), 'started_at': self.clock().isoformat(),
                      'state': 'INTENT_RECONCILE_BEFORE_RETRY'}
            if action in {'release_backend', 'release_guarded_bootstrap', 'restore_guarded_bootstrap'}:
                intent['operations_journal_identity_sha256'] = (binding['restore_context']['operations_journal_identity_sha256']
                    if anchor is not None else _operation_journal_identity(self.journal))
            durable(path, intent, exclusive=True)
            if correction is not None:
                # Re-read the permanent predecessor under the exclusive write
                # barrier; an altered/outstanding outcome cannot acquire a claim.
                c, claim = corrective_predecessor(self.journal, action, binding, approval)
                durable(claim, {'failed_operation_id': c['failed_operation_id'],
                    'operation_id': operation_id, 'state': 'CORRECTION_CONSUMED_NO_RETRY'}, exclusive=True)
            if action == 'restore_guarded_bootstrap':
                validate_guarded_restore_context(self.journal, binding, actual, approval)
                durable(claim, {'applied_normal_operation_id': binding['applied_normal_operation_id'],
                    'operation_id': operation_id, 'state': 'GUARDED_RETURN_CONSUMED_NO_RETRY'}, exclusive=True)
            request = self.journal / (operation_id + '.request.json')
            if action == 'stage_frontend':
                durable(request, {'name': 'earnalism', 'project': PROJECT,
                    'target': 'production', 'autoAssignCustomDomains': False,
                    'gitSource': {'type': 'github', 'ref': 'main',
                                  'sha': binding['source_sha'], 'repoId': 1232345982}}, exclusive=True)
            if action == 'restore_guarded_bootstrap':
                durable(request, {'action': action, 'binding_sha256': digest(binding),
                    'restore_context': binding['restore_context'],
                    'native_query': self._command(action, binding, request)[2]}, exclusive=True)
            if paired:
                # Final local source readback may fail, but never becomes a retry
                # or a fabricated native archive/source qualification.
                final_payload = _paired_bootstrap_payload(source, binding)
                if (digest(final_payload) != binding.get('backend_payload_sha256')
                        or digest(final_payload) != actual.get('backend_payload_sha256')
                        or final_payload['runtime_expected_sha256'] != binding.get('source_delivery_sha256')):
                    raise ValueError('Paired CLOSED export changed before dispatch')
                validate_approval(action, binding, approval, self.owner_authorized, self.clock())
                validate_startup_qualification(binding, approval, actual, self.clock())
                command = self._command(action, binding, request, backend_payload=final_payload)
                command_cwd = final_payload['archive_prefix']
            else:
                command = self._command(action, binding, request)
                command_cwd = source
            if action == 'restore_guarded_bootstrap':
                # Durable writes above target the original descriptor even if its
                # pathname was replaced. A changed path/custody never reaches CLI.
                validate_guarded_restore_context(self.journal, binding, actual, approval)
                validate_approval(action, binding, approval, self.owner_authorized, self.clock())
                validate_startup_qualification(binding, approval, actual, self.clock())
                _assert_operation_journal_anchor(self.journal, anchor,
                    binding['restore_context']['operations_journal_identity_sha256'])
            # No secret argv, shell interpolation, automatic OAuth/purchase flags,
            # output logging or retry. Even return0 is not serving acceptance.
            try:
                result = self.run(command, cwd=command_cwd, capture_output=True, text=True,
                                  timeout=1200, check=False)
                intent['process_exit_code'] = result.returncode
                intent['process_diagnostic'] = process_diagnostic(result)
                if action == 'stage_frontend' and result.returncode == 0:
                    try:
                        reported = json.loads(result.stdout).get('id', '')
                        if re.fullmatch(r'dpl_[A-Za-z0-9]+', reported):
                            intent['unverified_provider_deployment_id'] = reported
                    except (ValueError, AttributeError):
                        pass
            except Exception as error:
                intent['process_exit_code'] = None
                intent['process_diagnostic'] = process_diagnostic(error=error)
            intent['state'] = 'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED'
            durable(path, intent)
            return intent
        finally:
            if anchor is not None:os.close(anchor)


    def reconcile(self, operation_id):
        # Serialize reconciliation across processes so two readers cannot both
        # validate an old barrier and clear a later operation's new barrier.
        lock_path=self.journal/'.reconciliation.lock'
        fd=os.open(lock_path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
        try:
            info=os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600:
                raise ValueError('Unsafe reconciliation lock')
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            os.fsync(fd);_sync_directory(self.journal)
            return self._reconcile_locked(operation_id)
        finally:os.close(fd)

    def _reconcile_locked(self, operation_id):
        """Read provider state through the trusted observer; never repeat a write."""
        if not re.fullmatch('[0-9a-f]{64}', operation_id) or self.observe is None:
            raise ValueError('Actual reconciliation observer required')
        path = self.journal / (operation_id + '.json')
        record = _read_journal(path)
        actual = self.observe('reconcile', record)
        if (actual.get('scope') != 'ACTUAL_PROVIDER_AND_SOURCE'
                or actual.get('operation_id') != operation_id
                or actual.get('action') != record['action']
                or actual.get('source_sha') != record['binding']['source_sha']
                or actual.get('outcome') not in {'APPLIED', 'NOT_APPLIED'}
                or not re.fullmatch('[0-9a-f]{64}', actual.get('receipt_sha256', ''))):
            raise ValueError('Unknown/unbound actual provider outcome')
        if record['action']=='restore_guarded_bootstrap' and actual['outcome']=='APPLIED':
            c=validate_guarded_restore_context(self.journal, record['binding'], actual)
            # Rollback may create a NEW deployment. Bind its observed identity to
            # retained target image/source/config, never assert original ID serves.
            native_id=actual.get('deployment_id')
            if (not isinstance(native_id,str) or not re.fullmatch('[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}',native_id)
                    or actual.get('guarded_backend_deployment_id')!=native_id
                    or actual.get('restored_from_deployment_id')!=c['target_deployment_id']):
                raise ValueError('Actual native restore origin/identity missing')
            for key,expected in {'retained_image_id':c['target_retained_image_id'],
                'runtime_sha256':c['target_runtime_sha256'],'config_sha256':c['target_config_sha256']}.items():
                if actual.get(key)!=expected: raise ValueError('Restored bytes differ: '+key)
            qualify_bootstrap_recovery(record['binding'],{**actual,'action':'release_guarded_bootstrap'})
            for key in ('auto_deploy', 'redis_enabled', 'redis_cache_enabled', 'multi_replica_enabled', 'redis_public_metadata_enabled'):
                if actual.get(key) is not False: raise ValueError('Restored suppression unavailable: '+key)
        if record['action']=='restore_guarded_bootstrap' and actual['outcome']=='NOT_APPLIED':
            proof=actual.get('native_no_effect_proof')
            c=record['binding']['restore_context']
            if (not isinstance(proof,dict) or proof.get('scope')!='ACTUAL_NATIVE_RESTORE_NOT_APPLIED'
                    or proof.get('operation_id')!=operation_id
                    or proof.get('current_deployment_id')!=c['current_bad_normal_deployment_id']
                    or proof.get('no_new_native_deployment_observed') is not True
                    or proof.get('exact_request_not_applied') is not True):
                raise ValueError('Actual native no-effect proof required')
        if record['action']=='release_guarded_bootstrap' and actual['outcome']=='APPLIED':
            record['guarded_recovery_receipt_sha256']=qualify_bootstrap_recovery(record['binding'], actual)
            # Retain a bounded, nonsecret ORIGINAL actual qualification proof.
            # Old digest-only journals remain readable, but cannot authorize a
            # new restore without concrete original image/runtime evidence.
            keys=('scope','action','source_sha','source_delivery_sha256','closed_server_sha256',
                'deployment_id','retained_image_id','runtime_sha256','config_sha256','recovery_receipt_sha256',
                'guarded_backend_deployment_id','closed_guest_status','purchase_pause_proof',
                'startup_complete','database_healthy','source_attestation_matches','native_can_rollback',
                'config_compatible','existing_reader_listener_preserved','verify_refund_webhook_code_preserved')
            record['qualified_bootstrap_evidence']={k:actual.get(k) for k in keys}
        if record['action']=='release_backend' and actual['outcome']=='APPLIED':
            native=actual.get('deployment_id')
            if isinstance(native,str) and re.fullmatch('[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}',native):
                record['provider_backend_deployment_id']=native
        barrier = self.journal / '_write-barrier.json'
        if not barrier.exists():raise ValueError('Missing operation barrier')
        _validate_barrier(barrier, operation_id)
        record.update(state=actual['outcome'] + '_VERIFIED',
                      reconciliation_receipt_sha256=actual['receipt_sha256'])
        if record['action'] == 'stage_frontend' and actual['outcome'] == 'APPLIED':
            if not re.fullmatch(r'dpl_[A-Za-z0-9]+', actual.get('deployment_id', '')):
                raise ValueError('Exact observed staged deployment required')
            reported = record.get('unverified_provider_deployment_id')
            if reported and reported != actual['deployment_id']:
                raise ValueError('Observed deployment differs from write response')
            record['provider_deployment_id'] = actual['deployment_id']
        _durable_json(path, record)
        barrier = self.journal / '_write-barrier.json'
        if barrier.exists():
            _validate_barrier(barrier, operation_id)
            barrier.unlink()  # Permanent operation receipt stays; no retry authority.
            _sync_directory(self.journal)
        return record


class ReleaseController:
    """Explicit one-step controller; every remote write awaits actual reconciliation.

    No workflow is dispatched here. The default adapter prohibits execution.
    Existing protected approval and trusted observer requirements are retained.
    """
    def __init__(self, adapter):
        self.adapter = adapter

    def perform(self, action, binding, approval):
        records = []
        for path in self.adapter.journal.glob('*.json'):
            if not path.name.endswith('.request.json') and path.name != '_write-barrier.json':
                records.append(_read_journal(path))
        verified = [r for r in records if r.get('state') == 'APPLIED_VERIFIED'
                    and r.get('reconciliation_receipt_sha256')]
        if action == 'promote_frontend':
            if not any(r['action'] == 'stage_frontend'
                       and r['binding']['source_sha'] == binding['source_sha']
                       and r.get('provider_deployment_id') == binding.get('deployment_id')
                       for r in verified):
                raise ValueError('Exact staged candidate has no actual reconciliation')
        if action in {'release_backend', 'release_guarded_bootstrap'}:
            if not any(r['action'] == 'promote_frontend'
                       and r['binding']['deployment_id'] == binding.get('frontend_deployment_id')
                       and r['binding']['source_sha'] == binding.get('frontend_source_sha')
                       for r in verified):
                raise ValueError('Verified frontend-first promotion is required')
        if action=='release_backend':
            if not any(r['action']=='release_guarded_bootstrap' and r.get('guarded_recovery_receipt_sha256')==binding.get('guarded_recovery_receipt_sha256') and r.get('guarded_recovery_receipt_sha256') for r in verified):
                raise ValueError('Actual qualified CLOSED bootstrap recovery receipt required')
        return self.adapter.perform(action, binding, approval)
