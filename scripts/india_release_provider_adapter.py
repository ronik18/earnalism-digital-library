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

PROJECT = 'prj_kxPN55TOJ23lDgoXIXrvqHtzy607'
TEAM = 'team_HAGNRSEiW5MZXY2AhV0cQvE0'
RAILWAY_PROJECT = 'a8533934-35c4-463e-9f43-577a9ac391ee'
SERVICE = '5af42e7e-f518-4f6a-b602-d9950866501f'
ENVIRONMENT = '580b250c-80ee-48ad-bfbe-fa4e31a6b378'
ACTIONS = {'stage_frontend', 'promote_frontend', 'release_backend'}
CLI_VERSIONS = {'vercel': '59.25.4', 'railway': '5.71.0'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


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
    for key in ('provider_identity_sha256', 'config_sha256', 'guarded_rollback_sha256'):
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
            'project': PROJECT if action != 'release_backend' else RAILWAY_PROJECT,
            'service': SERVICE if action == 'release_backend' else None,
            'environment': ENVIRONMENT if action == 'release_backend' else 'production'})
        path = self.journal / (operation_id + '.json')
        if path.exists():
            raise FileExistsError('Provider operation already has a durable intent')
        # A local path, additional binding field or changed approval must never
        # turn one unknown remote write into another permitted operation.
        for prior in self.journal.glob('*.json'):
            if prior.name.endswith('.request.json'):
                continue
            record = json.loads(prior.read_text())
            if record.get('state') not in {'APPLIED_VERIFIED', 'NOT_APPLIED_VERIFIED'}:
                raise FileExistsError('Unresolved provider write requires read-only reconciliation')
        if self.observe is None:
            raise ValueError('Actual provider/source/config/rollback observer is required')
        # Observer must perform actual read-only source, provider/config, guarded
        # rollback and order checks. It must return the bound approval digests.
        actual = self.observe(action, binding)
        for key in ('provider_identity_sha256', 'config_sha256', 'guarded_rollback_sha256'):
            if actual.get(key) != approval[key]:
                raise ValueError('Live protected evidence differs: ' + key)
        if actual.get('scope') != 'ACTUAL_PROVIDER_AND_SOURCE' or actual.get('qualified') is not True:
            raise ValueError('Actual scoped qualification unavailable')
        if (actual.get('auto_deploy') is not False
                or actual.get('guarded_rollback_available') is not True
                or actual.get('authenticated_provider_account') is not True):
            raise ValueError('Provider suppression/authentication/guarded rollback unverified')
        cli = 'railway' if action == 'release_backend' else 'vercel'
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
        if action == 'release_backend':
            if (actual.get('frontend_signed_purchase_ready') is not True
                    or not binding.get('frontend_deployment_id')
                    or actual.get('frontend_deployment_id') != binding['frontend_deployment_id']
                    or actual.get('startup_qualified') is not True):
                raise ValueError('Frontend-first/startup prerequisites unqualified')
        source = Path(binding['source_root']).resolve()
        if action == 'release_backend':
            # Never upload a dirty or misidentified checkout or accept an input
            # SHA label as the actual source. Provider identity still needs a
            # separate post-write observation before any subsequent action.
            sha = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
            dirty = subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=all'], text=True).strip()
            if sha != binding['source_sha'] or dirty:
                raise ValueError('Backend source not exact/clean')
        self.journal.mkdir(parents=True, exist_ok=True)
        barrier = self.journal / '_write-barrier.json'
        lock = os.open(barrier, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(lock, 'w') as stream:
            json.dump({'operation_id': operation_id, 'state': 'INTENT_RECONCILE_BEFORE_RETRY'}, stream)
            stream.flush(); os.fsync(stream.fileno())
        # Exclusive intent is durable before any write; any existing intent,
        # including unknown outcome, forbids automatic repetition.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        intent = {'operation_id': operation_id, 'action': action, 'binding': binding,
                  'approval_sha256': digest(approval), 'started_at': self.clock().isoformat(),
                  'state': 'INTENT_RECONCILE_BEFORE_RETRY'}
        with os.fdopen(fd, 'w') as stream:
            json.dump(intent, stream); stream.flush(); os.fsync(stream.fileno())
        request = self.journal / (operation_id + '.request.json')
        if action == 'stage_frontend':
            request.write_text(json.dumps({'name': 'earnalism', 'project': PROJECT,
                'target': 'production', 'autoAssignCustomDomains': False,
                'gitSource': {'type': 'github', 'ref': 'main',
                              'sha': binding['source_sha'], 'repoId': 1232345982}}))
        command = self._command(action, binding, request)
        # No secret argv, shell interpolation, automatic OAuth/purchase flags,
        # output logging or retry. Even return0 is not serving acceptance.
        try:
            result = self.run(command, cwd=source, capture_output=True, text=True,
                              timeout=1200, check=False)
            intent['process_exit_code'] = result.returncode
            if action == 'stage_frontend' and result.returncode == 0:
                try:
                    reported = json.loads(result.stdout).get('id', '')
                    if re.fullmatch(r'dpl_[A-Za-z0-9]+', reported):
                        intent['unverified_provider_deployment_id'] = reported
                except (ValueError, AttributeError):
                    pass
        except Exception:
            intent['process_exit_code'] = None
        intent['state'] = 'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED'
        path.write_text(json.dumps(intent, indent=2) + '\n')
        return intent

    def reconcile(self, operation_id):
        """Read provider state through the trusted observer; never repeat a write."""
        if not re.fullmatch('[0-9a-f]{64}', operation_id) or self.observe is None:
            raise ValueError('Actual reconciliation observer required')
        path = self.journal / (operation_id + '.json')
        record = json.loads(path.read_text())
        actual = self.observe('reconcile', record)
        if (actual.get('scope') != 'ACTUAL_PROVIDER_AND_SOURCE'
                or actual.get('operation_id') != operation_id
                or actual.get('action') != record['action']
                or actual.get('source_sha') != record['binding']['source_sha']
                or actual.get('outcome') not in {'APPLIED', 'NOT_APPLIED'}
                or not re.fullmatch('[0-9a-f]{64}', actual.get('receipt_sha256', ''))):
            raise ValueError('Unknown/unbound actual provider outcome')
        record.update(state=actual['outcome'] + '_VERIFIED',
                      reconciliation_receipt_sha256=actual['receipt_sha256'])
        if record['action'] == 'stage_frontend' and actual['outcome'] == 'APPLIED':
            if not re.fullmatch(r'dpl_[A-Za-z0-9]+', actual.get('deployment_id', '')):
                raise ValueError('Exact observed staged deployment required')
            reported = record.get('unverified_provider_deployment_id')
            if reported and reported != actual['deployment_id']:
                raise ValueError('Observed deployment differs from write response')
            record['provider_deployment_id'] = actual['deployment_id']
        path.write_text(json.dumps(record, indent=2) + '\n')
        barrier = self.journal / '_write-barrier.json'
        if barrier.exists():
            if json.loads(barrier.read_text()).get('operation_id') != operation_id:
                raise ValueError('Cannot release a different operation barrier')
            barrier.unlink()  # Receipt stays permanently; only the reconciled lock clears.
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
                records.append(json.loads(path.read_text()))
        verified = [r for r in records if r.get('state') == 'APPLIED_VERIFIED'
                    and r.get('reconciliation_receipt_sha256')]
        if action == 'promote_frontend':
            if not any(r['action'] == 'stage_frontend'
                       and r['binding']['source_sha'] == binding['source_sha']
                       and r.get('provider_deployment_id') == binding.get('deployment_id')
                       for r in verified):
                raise ValueError('Exact staged candidate has no actual reconciliation')
        if action == 'release_backend':
            if not any(r['action'] == 'promote_frontend'
                       and r['binding']['deployment_id'] == binding.get('frontend_deployment_id')
                       and r['binding']['source_sha'] == binding.get('frontend_source_sha')
                       for r in verified):
                raise ValueError('Verified frontend-first promotion is required')
        return self.adapter.perform(action, binding, approval)
