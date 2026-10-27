"""Bounded authenticated metadata observations; no write, variable or identity APIs.

The operator's current no-execution instruction is independent of successful
metadata reads. Capability flags never establish source/config rollback safety.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import re
import stat
import subprocess
from scripts.india_release_provider_adapter import (
    PROJECT, TEAM, RAILWAY_PROJECT, SERVICE, ENVIRONMENT, CLI_VERSIONS, digest,
)


def journal_location_holds(journal, workspace=None, temporary=None):
    """Validate storage metadata before any journal enumeration/content read."""
    path = Path(journal)
    if not path.exists():
        return ['FIXED_JOURNAL_NOT_PROVISIONED']
    resolved = path.resolve()
    if resolved != path or not path.is_dir():
        return ['FIXED_JOURNAL_NOT_A_REAL_DIRECTORY']
    if any(parent.is_symlink() for parent in [path, *path.parents]):
        return ['FIXED_JOURNAL_HAS_SYMBOLIC_PARENT']
    roots = [Path(root).resolve() for root in (workspace, temporary) if root is not None]
    if any(resolved == root or root in resolved.parents for root in roots):
        return ['JOURNAL_MUST_BE_OUTSIDE_EPHEMERAL_RUNNER_DIRECTORIES']
    info = path.stat()
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
        return ['JOURNAL_OWNER_OR_PERMISSIONS_UNQUALIFIED']
    return ['DURABLE_HOST_AND_PROTECTED_EXECUTOR_ATTESTATION_REQUIRED']


def rollback_verdict(deployments, contract):
    """Match a reviewed immutable artifact; missing evidence fails closed."""
    artifact = contract.get('rollback', {})
    required = ('deployment_id', 'source_sha', 'source_manifest_sha256', 'config_sha256')
    if any(not artifact.get(k) for k in required):
        return {'qualified': False, 'reason': 'REVIEWED_ROLLBACK_BINDING_MISSING'}
    if (not re.fullmatch('[a-f0-9]{40}', artifact['source_sha'])
            or any(not re.fullmatch('[a-f0-9]{64}', artifact[k]) for k in required[2:])):
        return {'qualified': False, 'reason': 'ROLLBACK_BINDING_INVALID'}
    found = [d for d in deployments if d.get('id') == artifact['deployment_id']]
    if len(found) != 1:
        return {'qualified': False, 'reason': 'GUARDED_ARTIFACT_NOT_OBSERVED'}
    actual = found[0]
    if actual.get('status') != 'SUCCESS' or actual.get('git_sha') != artifact['source_sha']:
        return {'qualified': False, 'reason': 'ROLLBACK_SOURCE_OR_STATUS_MISMATCH'}
    # This bounded deployment API proves identity/capability only, never image
    # digest, current config compatibility, middleware or protected acceptance.
    return {'qualified': False, 'reason': 'ARTIFACT_CONFIG_AND_PROTECTED_QUALIFICATION_REQUIRED',
            'matched_deployment_id': actual['id'], 'capability_only': True}


class NativeMetadataObserver:
    """Fixed CLI read operations using existing authentication internally.

    Raw outputs stay in memory and are never logged or persisted. Only explicit
    nonsecret fields survive projection. Unknown provider shape is a hard hold.
    """
    def __init__(self, source_root, *, run=subprocess.run,
                 clock=lambda: datetime.now(timezone.utc)):
        self.source_root = Path(source_root).resolve()
        self.run, self.clock = run, clock

    def _read(self, argv):
        try:
            result = self.run(argv, cwd=self.source_root, capture_output=True,
                              text=True, timeout=60, check=False)
        except subprocess.TimeoutExpired:
            raise ValueError('Read-only provider observation timed out; no retry') from None
        if result.returncode:
            raise ValueError('Read-only provider observation failed')
        try:
            return json.loads(result.stdout)
        except (ValueError, TypeError):
            raise ValueError('Provider metadata was not valid JSON') from None

    def verify_versions(self):
        for tool, expected in CLI_VERSIONS.items():
            result = self.run([tool, '--version'], cwd=self.source_root,
                              capture_output=True, text=True, timeout=15, check=False)
            reported = re.fullmatch(r'(?:Vercel CLI |railway )?([0-9]+\.[0-9]+\.[0-9]+)',
                                    (result.stdout or '').strip())
            if result.returncode or not reported or reported[1] != expected:
                raise ValueError('Reviewed provider CLI version required: ' + tool)

    def collect(self, candidate_id=None):
        if candidate_id is not None and not re.fullmatch(r'dpl_[A-Za-z0-9]+', candidate_id):
            raise ValueError('Invalid exact candidate ID')
        self.verify_versions()
        # Explicit GET, no input/header/token/debug flags or secret endpoints.
        project = self._read(['vercel', 'api', '/v9/projects/' + PROJECT,
                              '--method', 'GET', '--raw', '--scope', TEAM])
        if not isinstance(project, dict) or project.get('id') != PROJECT or project.get('accountId') != TEAM:
            raise ValueError('Vercel project/team mismatch')
        link = project.get('link') or {}
        suppression = link.get('deploymentEnabled')
        # Missing or per-branch maps are not interpreted as false.
        snapshot = {'schema': 'earnalism.provider-metadata-observation.v1',
            'observed_at': self.clock().isoformat(), 'project': PROJECT, 'team': TEAM,
            'railway_project': RAILWAY_PROJECT, 'service': SERVICE, 'environment': ENVIRONMENT,
            'verified_cli_versions': dict(CLI_VERSIONS),
            'frontend_auto_deploy_disabled': suppression is False,
            'backend_auto_deploy_disabled': None,
            'scope': 'ACTUAL_BOUNDED_METADATA_NOT_RELEASE_QUALIFICATION'}
        if candidate_id:
            candidate = self._read(['vercel', 'api', '/v13/deployments/' + candidate_id,
                                    '--method', 'GET', '--raw', '--scope', TEAM])
            if not isinstance(candidate, dict) or candidate.get('id') != candidate_id or candidate.get('projectId') != PROJECT:
                raise ValueError('Candidate project/identity mismatch')
            snapshot['candidate'] = {'id': candidate_id, 'source_sha': (candidate.get('meta') or {}).get('githubCommitSha'),
                'ready_state': candidate.get('readyState'), 'target': candidate.get('target')}
        raw = self._read(['railway', 'deployment', 'list', '--project', RAILWAY_PROJECT,
            '--service', SERVICE, '--environment', ENVIRONMENT, '--limit', '10', '--json'])
        rows = raw if isinstance(raw, list) else raw.get('deployments') if isinstance(raw, dict) else None
        if not isinstance(rows, list) or len(rows) > 10:
            raise ValueError('Unexpected bounded Railway deployment response')
        snapshot['deployments'] = []
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('id'), str):
                raise ValueError('Invalid deployment metadata')
            meta = row.get('meta') or {}
            # Support explicit provider fields; no inferred source from titles,
            # timestamps, active status or untrusted free-text messages.
            snapshot['deployments'].append({'id': row['id'], 'status': row.get('status'),
                'git_sha': row.get('git_sha') or meta.get('commitHash'),
                'canRollback': row.get('canRollback') is True})
        snapshot['observation_sha256'] = digest(snapshot)
        return snapshot


class ProtectedReleasePreflight:
    """Fixed durable namespace for controller preparation, never an executor.

    This source adds no dispatch workflow and accepts no journal override. A
    future platform-protected executor must bind authentic approvals and actual
    artifact/config/startup/serving evidence before ProviderAdapter can be used.
    """
    JOURNAL = Path('/Users/ronikbasak/.codex/earnalism-release-journal/india-production')

    def __init__(self, observer):
        self.observer = observer

    def check(self, contract, *, workspace=None, temporary=None):
        source = contract.get('source_sha', '')
        if not re.fullmatch('[a-f0-9]{40}', source):
            raise ValueError('Exact reviewed source required')
        snapshot = self.observer.collect(contract.get('candidate_id'))
        holds = ['CURRENT_OWNER_PROHIBITS_EXECUTION',
                 'AUTHENTIC_PLATFORM_PROTECTED_EXECUTOR_REQUIRED',
                 'CURRENT_SOURCE_ROLE_CONTRACT_REQUIRED',
                 'ACTUAL_CONFIG_AND_STARTUP_QUALIFICATION_REQUIRED']
        if snapshot.get('frontend_auto_deploy_disabled') is not True:
            holds.append('FRONTEND_AUTO_DEPLOY_SUPPRESSION_UNVERIFIED')
        if snapshot.get('backend_auto_deploy_disabled') is not True:
            holds.append('BACKEND_AUTO_DEPLOY_SUPPRESSION_UNVERIFIED')
        rollback = rollback_verdict(snapshot['deployments'], contract)
        if not rollback['qualified']:
            holds.append(rollback['reason'])
        location = journal_location_holds(self.JOURNAL, workspace, temporary)
        holds.extend(location)
        # A missing/unsafe path is a write-qualification HOLD, not a reason to
        # skip otherwise permitted metadata observation. Never follow it.
        if location == ['DURABLE_HOST_AND_PROTECTED_EXECUTOR_ATTESTATION_REQUIRED']:
            for path in self.JOURNAL.glob('*.json'):
                if path.name.endswith('.request.json'):
                    continue
                if path.is_symlink() or not path.is_file():
                    holds.append('UNSAFE_JOURNAL_RECEIPT')
                    break
                with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW)) as stream:
                    info = os.fstat(stream.fileno())
                    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o022:
                        holds.append('UNSAFE_JOURNAL_RECEIPT')
                        break
                    state = json.load(stream).get('state')
                if state not in {'APPLIED_VERIFIED', 'NOT_APPLIED_VERIFIED'}:
                    holds.append('UNKNOWN_WRITE_REQUIRES_READ_ONLY_RECONCILIATION')
                    break
        return {'schema': 'earnalism.protected-runner-preflight.v1',
                'source_sha': source, 'journal_namespace': str(self.JOURNAL),
                'metadata_observation_sha256': snapshot['observation_sha256'],
                'rollback': rollback, 'holds': sorted(set(holds)), 'execution_permitted': False}
