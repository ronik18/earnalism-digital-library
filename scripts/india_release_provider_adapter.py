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
ACTIONS = {'stage_frontend', 'promote_frontend', 'release_backend', 'release_guarded_bootstrap'}
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


def _durable_json(path, value, *, exclusive=False):
    """No recovery/cleanup on unknown outcomes; permanent intent stays permanent."""
    path=Path(path)
    temporary=path if exclusive else path.with_name('.'+path.name+'.'+uuid.uuid4().hex+'.pending')
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as stream:
        json.dump(value,stream);stream.flush();os.fsync(stream.fileno())
    if not exclusive:os.replace(temporary,path)
    _sync_directory(path.parent)


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
    if action == 'release_guarded_bootstrap': return 'bootstrap_preflight_sha256'
    if action in {'stage_frontend', 'promote_frontend'} and binding.get('frontend_phase'):
        return 'frontend_rollback_sha256'
    return 'guarded_rollback_sha256'


def require_digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) and value != '0' * 64


def validate_action_recovery(action, binding, actual):
    """Trusted live observer only; synthetic tests never create real receipts."""
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


class ProviderAdapter:
    def __init__(self, journal, *, owner_authorized=False, observe=None,
                 run=subprocess.run, clock=lambda: datetime.now(timezone.utc)):
        self.journal = Path(journal)
        self.owner_authorized, self.observe = owner_authorized, observe
        self.run, self.clock = run, clock

    def _command(self, action, binding, request_path):
        if action == 'stage_frontend':
            return ['vercel', 'api', '/v13/deployments', '--method', 'POST',
                    '--input', str(request_path), '--raw', '--scope', TEAM]
        if action == 'promote_frontend':
            if not re.fullmatch(r'dpl_[A-Za-z0-9]+', binding.get('deployment_id', '')):
                raise ValueError('Invalid exact candidate identity')
            return ['vercel', 'promote', binding['deployment_id'], '--yes', '--scope', TEAM]
        return ['railway', 'up', '--ci', '--project', RAILWAY_PROJECT,
                '--service', SERVICE, '--environment', ENVIRONMENT, '--json']

    def perform(self, action, binding, approval):
        validate_approval(action, binding, approval, self.owner_authorized, self.clock())
        operation_id = digest({'action': action, 'source_sha': binding['source_sha'],
            'candidate': binding.get('deployment_id') if action == 'promote_frontend' else None,
            'project': RAILWAY_PROJECT if action in {'release_backend', 'release_guarded_bootstrap'} else PROJECT,
            'service': SERVICE if action in {'release_backend', 'release_guarded_bootstrap'} else None,
            'environment': ENVIRONMENT if action in {'release_backend', 'release_guarded_bootstrap'} else 'production'})
        path = self.journal / (operation_id + '.json')
        if path.exists():
            raise FileExistsError('Provider operation already has a durable intent')
        # A local path, additional binding field or changed approval must never
        # turn one unknown remote write into another permitted operation.
        for prior in self.journal.glob('*.json'):
            if prior.name.endswith('.request.json'):
                continue
            record = _read_journal(prior)
            if record.get('state') not in {'APPLIED_VERIFIED', 'NOT_APPLIED_VERIFIED'}:
                raise FileExistsError('Unresolved provider write requires read-only reconciliation')
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
        validate_action_recovery(action, binding, actual)
        cli = 'railway' if action in {'release_backend', 'release_guarded_bootstrap'} else 'vercel'
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
        source = Path(binding['source_root']).resolve()
        if action in {'release_backend', 'release_guarded_bootstrap'}:
            # Never upload a dirty or misidentified checkout or accept an input
            # SHA label as the actual source. Provider identity still needs a
            # separate post-write observation before any subsequent action.
            sha = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
            dirty = subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=all'], text=True).strip()
            if sha != binding['source_sha'] or dirty:
                raise ValueError('Backend source not exact/clean')
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
        barrier = self.journal / '_write-barrier.json'
        _durable_json(barrier, {'operation_id': operation_id, 'state': 'INTENT_RECONCILE_BEFORE_RETRY'}, exclusive=True)
        intent = {'operation_id': operation_id, 'action': action, 'binding': binding,
                  'approval_sha256': digest(approval), 'started_at': self.clock().isoformat(),
                  'state': 'INTENT_RECONCILE_BEFORE_RETRY'}
        _durable_json(path, intent, exclusive=True)
        request = self.journal / (operation_id + '.request.json')
        if action == 'stage_frontend':
            _durable_json(request, {'name': 'earnalism', 'project': PROJECT,
                'target': 'production', 'autoAssignCustomDomains': False,
                'gitSource': {'type': 'github', 'ref': 'main',
                              'sha': binding['source_sha'], 'repoId': 1232345982}}, exclusive=True)
        command = self._command(action, binding, request)
        # No secret argv, shell interpolation, automatic OAuth/purchase flags,
        # output logging or retry. Even return0 is not serving acceptance.
        try:
            result = self.run(command, cwd=source, capture_output=True, text=True,
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
        _durable_json(path, intent)
        return intent

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
        if record['action']=='release_guarded_bootstrap' and actual['outcome']=='APPLIED':
            record['guarded_recovery_receipt_sha256']=qualify_bootstrap_recovery(record['binding'], actual)
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
