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
from scripts import first_guard_pair as pair

PROJECT = 'prj_kxPN55TOJ23lDgoXIXrvqHtzy607'
TEAM = 'team_HAGNRSEiW5MZXY2AhV0cQvE0'
RAILWAY_PROJECT = 'a8533934-35c4-463e-9f43-577a9ac391ee'
SERVICE = '5af42e7e-f518-4f6a-b602-d9950866501f'
ENVIRONMENT = '580b250c-80ee-48ad-bfbe-fa4e31a6b378'
ACTIONS = {'stage_frontend', 'promote_frontend', 'release_backend', 'release_guarded_bootstrap', 'restore_guarded_bootstrap', 'restore_frontend'}
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
    if action=='promote_frontend' and 'first_guard_pair' in binding:
        return 'first_guard_failure_policy_sha256'
    if action == 'restore_frontend': return 'frontend_restore_sha256'
    if action == 'restore_guarded_bootstrap': return 'guarded_restore_sha256'
    if action == 'release_guarded_bootstrap': return 'bootstrap_preflight_sha256'
    if action == 'stage_frontend' and binding.get('frontend_phase') == 'STAGE_ONLY':
        return 'stage_isolation_sha256'
    if action in {'stage_frontend', 'promote_frontend'} and binding.get('frontend_phase'):
        return 'frontend_rollback_sha256'
    return 'guarded_rollback_sha256'


def require_digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) and value != '0' * 64


def operation_identity(action, binding):
    """Ordinary identities remain byte-for-byte compatible with old journals."""
    if action == 'restore_frontend':
        return digest({'action': action, 'project': PROJECT, 'team': TEAM,
            'applied_promotion_operation_id': binding.get('applied_promotion_operation_id')})
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


STAGE_ONLY_SCOPE = 'ARTIFACT_STAGE_ONLY_NO_BACKEND_COMPATIBILITY_OR_RECOVERY'
STAGE_REFERENCE_FIELDS = {'operation_id', 'record_sha256', 'reconciliation_receipt_sha256',
    'input_projection_sha256', 'operations_journal_identity_sha256'}


def stage_frontend_request(binding):
    return {'name': 'earnalism', 'project': PROJECT, 'target': 'production',
        'autoAssignCustomDomains': False,
        'gitSource': {'type': 'github', 'ref': 'main', 'sha': binding['source_sha'], 'repoId': 1232345982}}


def stage_only_projection(binding):
    if binding.get('frontend_phase') != 'STAGE_ONLY' or binding.get('stage_scope') != STAGE_ONLY_SCOPE:
        raise ValueError('Explicit artifact-only stage scope required')
    for key in ('source_sha', 'intended_backend_source_sha', 'frontend_tree'):
        if not re.fullmatch('[a-f0-9]{40}', binding.get(key, '')):
            raise ValueError('Exact stage source required: ' + key)
    for key in ('intended_backend_config_sha256', 'frontend_input_fingerprint_sha256', 'stage_request_sha256'):
        if not require_digest(binding.get(key)): raise ValueError('Exact stage input digest required: ' + key)
    aliases = binding.get('stage_alias_baseline')
    if (not isinstance(aliases, dict) or set(aliases) != {'theearnalism.com', 'www.theearnalism.com'}
            or len(set(aliases.values())) != 1
            or not all(isinstance(v, str) and re.fullmatch(r'dpl_[A-Za-z0-9]+', v) for v in aliases.values())):
        raise ValueError('Exact unchanged public alias baseline required')
    request = stage_frontend_request(binding)
    if binding['stage_request_sha256'] != digest(request): raise ValueError('Exact private production stage request differs')
    return {'scope': STAGE_ONLY_SCOPE, 'project': PROJECT, 'team': TEAM,
        'source_sha': binding['source_sha'], 'frontend_tree': binding['frontend_tree'],
        'frontend_input_fingerprint_sha256': binding['frontend_input_fingerprint_sha256'],
        'intended_backend_source_sha': binding['intended_backend_source_sha'],
        'intended_backend_config_sha256': binding['intended_backend_config_sha256'],
        'request': request, 'alias_baseline': aliases}


def validate_stage_only(binding, actual):
    projection = stage_only_projection(binding)
    expected = digest(projection)
    if (actual.get('qualification_scope') != STAGE_ONLY_SCOPE
            or actual.get('stage_input_projection') != projection
            or actual.get('stage_isolation_sha256') != expected
            or actual.get('public_aliases') != projection['alias_baseline']):
        raise ValueError('Actual stage isolation/source/alias evidence unavailable')
    if any(k in actual for k in ('frontend_rollback_available', 'frontend_backend_compatible',
            'existing_reader_listener_preserved', 'guarded_rollback_available')):
        raise ValueError('Artifact-only stage must not claim Reader or recovery qualification')
    return projection


def validate_stage_only_source(binding):
    root = Path(binding['source_root']).resolve()
    env = {**os.environ, 'GIT_NO_LAZY_FETCH': '1', 'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_TERMINAL_PROMPT': '0'}
    def git(*args):
        return subprocess.check_output(['git', '-c', 'remote.origin.promisor=false', '-C', str(root), *args],
            text=True, env=env, timeout=20).strip()
    if (git('rev-parse', 'HEAD') != binding['source_sha']
            or git('rev-parse', 'HEAD:frontend') != binding['frontend_tree']
            or git('status', '--porcelain', '--untracked-files=all')):
        raise ValueError('Exact clean reviewed stage source required')


def validate_stage_only_result(journal, record, actual, now):
    projection = stage_only_projection(record['binding'])
    if record.get('stage_input_projection') != projection:
        raise ValueError('Original immutable stage projection required')
    custody = _operation_journal_identity(journal)
    if record.get('operations_journal_identity_sha256') != custody:
        raise ValueError('Original stage journal custody differs')
    if actual.get('outcome') != 'APPLIED':
        raise ValueError('Unknown stage requires genuine native proof; no no-effect guess')
    observation = actual.get('stage_isolation_observation')
    if not isinstance(observation, dict) or set(observation) != {'scope', 'project', 'team', 'deployment', 'aliases', 'observed_at'}:
        raise ValueError('Actual exact isolated stage observation required')
    d = observation['deployment']
    candidate = record.get('unverified_provider_deployment_id')
    if (observation['scope'] != STAGE_ONLY_SCOPE or observation['project'] != PROJECT or observation['team'] != TEAM
            or not isinstance(candidate, str) or not re.fullmatch(r'dpl_[A-Za-z0-9]+', candidate)
            or actual.get('deployment_id') != candidate or not isinstance(d, dict)
            or d.get('id') != candidate or d.get('projectId') != PROJECT
            or d.get('target') != 'production' or d.get('readyState') != 'READY'
            or d.get('gitSource') != projection['request']['gitSource']
            or observation['aliases'] != projection['alias_baseline']):
        raise ValueError('Exact READY private stage/source/project/team/aliases required')
    observed = datetime.fromisoformat(observation['observed_at'])
    begin = datetime.fromisoformat(record['started_at'])
    reported = datetime.fromisoformat(actual['observed_at'])
    if any(t.tzinfo is None for t in (observed, begin, reported, now)) or not begin <= observed <= reported <= now or now-observed > timedelta(minutes=15):
        raise ValueError('Stage observation predates attempt or is stale/future')
    return projection


def validate_stage_artifact_reference(journal, binding):
    ref = binding.get('stage_artifact_reference')
    if not isinstance(ref, dict) or set(ref) != STAGE_REFERENCE_FIELDS or not all(require_digest(ref[k]) for k in ref):
        raise ValueError('Original artifact stage reference required')
    original = _read_journal(Path(journal)/(ref['operation_id']+'.json'))
    projection = original.get('stage_input_projection')
    if (original.get('action') != 'stage_frontend' or original.get('state') != 'APPLIED_VERIFIED'
            or original.get('binding', {}).get('frontend_phase') != 'STAGE_ONLY'
            or original.get('operation_id') != operation_identity('stage_frontend', original['binding'])
            or original.get('operation_id') != ref['operation_id'] or digest(original) != ref['record_sha256']
            or original.get('reconciliation_receipt_sha256') != ref['reconciliation_receipt_sha256']
            or original.get('operations_journal_identity_sha256') != ref['operations_journal_identity_sha256']
            or _operation_journal_identity(journal) != ref['operations_journal_identity_sha256']
            or projection != stage_only_projection(original['binding'])
            or digest(projection) != ref['input_projection_sha256']
            or binding.get('source_sha') != original['binding']['source_sha']
            or binding.get('deployment_id') != original.get('provider_deployment_id')
            or binding.get('backend_source_sha') != projection['intended_backend_source_sha']
            or binding.get('backend_config_sha256') != projection['intended_backend_config_sha256']
            or binding.get('frontend_phase') != 'GUARD_ACTIVE'):
        raise ValueError('Immutable artifact stage/source/candidate/context differs')
    return original


def validate_action_recovery(action, binding, actual):
    """Trusted live observer only; synthetic tests never create real receipts."""
    if 'first_guard_pair' in binding:
        pair.validate(binding, actual)
        if action not in {'release_guarded_bootstrap','promote_frontend'}:
            raise ValueError('First guard pair permits only bootstrap or bound promotion')
        if actual.get('first_guard_pair_component_preflight') is not True:
            raise ValueError('Actual first guard component preflight required')
        if action == 'promote_frontend': return
    if binding.get('frontend_phase') == 'STAGE_ONLY':
        if action != 'stage_frontend': raise ValueError('Artifact-only stage cannot promote or release')
        validate_stage_only(binding, actual)
        return
    if action == 'restore_frontend':
        return  # Same-journal return context is validated separately.
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


PAIRED_INPUT_SCHEMA = 'earnalism.paired-content-input.v1'
PAIRED_LINEAGE_SCHEMA = 'earnalism.paired-content-lineage.v1'
HELPER_REPORT_SCHEMA = 'earnalism.executed_upstream_helper_archive.v1'
HELPER_REPORT_SCOPE = 'EXACT_UPSTREAM_HELPER_EXECUTED_NOT_INSTALLED_CLI_UPLOAD_OR_NATIVE_RUNTIME'
HELPER_PACKAGE = 'scripts/test_helpers/railway_archiver_v5710/'
HELPER_COMPONENTS = ('scripts/execute_railway_helper_check.py',
    'scripts/verify_railway_helper_archive.py', 'scripts/verify_railway_helper_source.py',
    *tuple(HELPER_PACKAGE + name for name in ('Cargo.toml', 'Cargo.lock', 'SOURCE-PINS.json',
        'src/main.rs', 'upstream-Cargo.lock', 'upstream-upload.rs.txt')))


def _paired_input(binding):
    value = binding.get('paired_content_provenance')
    fields = {'schema', 'input_git_source_sha', 'expected_archive_helper_report_sha256',
              'archive_member_manifest_sha256', 'archive_member_modes_sha256', 'helper_archive_sha256'}
    if (not isinstance(value, dict) or set(value) != fields or value['schema'] != PAIRED_INPUT_SCHEMA
            or value['input_git_source_sha'] != binding.get('source_sha')
            or not re.fullmatch('[a-f0-9]{40}', value.get('input_git_source_sha', ''))
            or not all(require_digest(value[k]) for k in fields - {'schema', 'input_git_source_sha'})):
        raise ValueError('Exact paired content input contract required')
    return value


def _paired_helper_components(binding, report):
    """Compare immutable consumed components, not whole producer/operator HEADs."""
    from scripts.purchase_guard_source import _git, _git_blob
    producer, operator = report.get('controller_source_sha'), binding.get('controller_source_sha')
    if not all(isinstance(x, str) and re.fullmatch('[a-f0-9]{40}', x) for x in (producer, operator)):
        raise ValueError('Actual helper producer and operator sources required')
    repo = Path(binding['source_root']).resolve()
    blobs = {}
    for name in HELPER_COMPONENTS:
        entries = []
        for ref in (producer, operator):
            raw = _git(repo, 'ls-tree', '-z', ref, '--', name).rstrip(b'\0')
            if not raw or b'\0' in raw: raise ValueError('Consumed helper component missing')
            header, path = raw.split(b'\t', 1)
            mode, kind, oid = header.decode().split()
            if path.decode() != name or mode not in {'100644', '100755'} or kind != 'blob':
                raise ValueError('Regular immutable helper component required')
            entries.append((mode, oid))
        if entries[0] != entries[1]:
            raise ValueError('Helper producer/operator component identity differs: ' + name)
        blobs[name] = _git_blob(repo, producer, name)
    pins = json.loads(blobs[HELPER_PACKAGE + 'SOURCE-PINS.json'])
    expected = {'harness_source_sha256': hashlib.sha256(blobs[HELPER_PACKAGE + 'src/main.rs']).hexdigest(),
        'derived_lock_sha256': hashlib.sha256(blobs[HELPER_PACKAGE + 'Cargo.lock']).hexdigest(),
        'source_pins_sha256': hashlib.sha256(blobs[HELPER_PACKAGE + 'SOURCE-PINS.json']).hexdigest(),
        'upstream_module_sha256': hashlib.sha256(blobs[HELPER_PACKAGE + 'upstream-upload.rs.txt']).hexdigest(),
        'upstream_lock_sha256': hashlib.sha256(blobs[HELPER_PACKAGE + 'upstream-Cargo.lock']).hexdigest(),
        'upstream_function_sha256': pins.get('exact_function_sha256')}
    if (pins.get('upstream_tag') != 'v' + CLI_VERSIONS['railway']
            or pins.get('upstream_upload_sha256') != expected['upstream_module_sha256']
            or pins.get('upstream_lock_sha256') != expected['upstream_lock_sha256']
            or pins.get('derived_lock_sha256') != expected['derived_lock_sha256']
            or not all(require_digest(x) for x in expected.values())
            or any(report.get(key) != value for key, value in expected.items())):
        raise ValueError('Executed helper module/function/lock identity differs')


def _paired_helper_receipt(binding, report):
    """Validate an executed helper artifact; it is never an upload checksum."""
    expected = _paired_input(binding)
    if (not isinstance(report, dict) or digest(report) != expected['expected_archive_helper_report_sha256']
            or report.get('schema') != HELPER_REPORT_SCHEMA or report.get('scope') != HELPER_REPORT_SCOPE
            or report.get('helper_executed') is not True
            or report.get('input_git_source_sha') != expected['input_git_source_sha']):
        raise ValueError('Bound actually executed helper receipt required')
    for field in ('native_archive_qualification', 'provider_upload_performed', 'runtime_qualification'):
        if report.get(field) is not False: raise ValueError('Helper evidence scope broadened: ' + field)
    if (type(report.get('provider_writes')) is not int or report['provider_writes'] != 0
            or 'provider_git_sha' not in report or report['provider_git_sha'] is not None
            or report.get('provider_git_metadata_status') != 'NOT_OBSERVED_NO_PROVIDER_CALL'):
        raise ValueError('Helper receipt must preserve absent provider observations')
    context = report.get('ci_context')
    if (not isinstance(context, dict) or context.get('GITHUB_REPOSITORY') != 'ronik18/earnalism-digital-library'
            or context.get('actual_controller_sha') != report.get('controller_source_sha')
            or not all(isinstance(context.get(k), str) and context[k] for k in
                ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_SHA', 'GITHUB_JOB', 'GITHUB_EVENT_NAME'))
            or context['GITHUB_EVENT_NAME'] == 'workflow_dispatch'
            or not re.fullmatch('[a-f0-9]{40}', context['GITHUB_SHA'])):
        raise ValueError('Actual ordinary-CI helper producer context required')
    for field in ('helper_binary_sha256', 'offline_export_report_sha256'):
        if not require_digest(report.get(field)): raise ValueError('Missing producer evidence digest: ' + field)
    if (not isinstance(report.get('actual_toolchain'), dict)
            or not all(isinstance(report['actual_toolchain'].get(k), str) and report['actual_toolchain'][k]
                for k in ('rustc', 'cargo'))):
        raise ValueError('Actual helper toolchain observation missing')
    _paired_helper_components(binding, report)
    members = report.get('members')
    if not isinstance(members, list) or not members: raise ValueError('Actual helper regular members required')
    content = []
    for row in members:
        if (not isinstance(row, dict) or set(row) != {'path', 'bytes', 'sha256', 'mode'}
                or not isinstance(row['path'], str) or not row['path'].startswith('backend/')
                or '\\' in row['path'] or any(x in {'', '.', '..'} for x in row['path'].split('/'))
                or type(row['bytes']) is not int or row['bytes'] < 0 or not require_digest(row['sha256'])
                or type(row['mode']) is not int or row['mode'] not in {0o644, 0o755}):
            raise ValueError('Canonical regular helper member required')
        content.append({k: row[k] for k in ('path', 'bytes', 'sha256')})
    if ([row['path'] for row in members] != sorted(set(row['path'] for row in members))
            or digest(content) != expected['archive_member_manifest_sha256']
            or digest(members) != expected['archive_member_modes_sha256']
            or report.get('archive_member_manifest_sha256') != expected['archive_member_manifest_sha256']
            or report.get('archive_member_modes_sha256') != expected['archive_member_modes_sha256']
            or report.get('archive_sha256') != expected['helper_archive_sha256']
            or type(report.get('regular_members')) is not int or report['regular_members'] != len(members)
            or type(report.get('directory_members')) is not int or report['directory_members'] < 0
            or type(report.get('uncompressed_regular_bytes')) is not int
            or report['uncompressed_regular_bytes'] != sum(row['bytes'] for row in members)
            or type(report.get('runtime_input_count')) is not int or report['runtime_input_count'] < 1
            or report.get('runtime_expected_sha256') != binding.get('source_delivery_sha256')):
        raise ValueError('Stable helper B content/modes/runtime projection differs')
    return content, members


def validate_paired_archive_input(binding, actual, payload):
    """Read-only local evidence admission; no archiver, authority or provider call."""
    from scripts.purchase_guard_source import backend_tree
    content, members = _paired_helper_receipt(binding, actual.get('archive_helper_report'))
    files = payload.get('files')
    if (not isinstance(files, list) or sorted(files, key=lambda r: r['path']) != content
            or payload.get('source') != binding.get('source_sha')
            or actual['archive_helper_report'].get('runtime_input_count') != payload.get('runtime_input_count')
            or actual['archive_helper_report'].get('root_ignore_sha256') != payload.get('root_ignore_sha256')):
        raise ValueError('Helper receipt does not cover current qualified export')
    tree = backend_tree(Path(binding['source_root']).resolve(), binding['source_sha'])
    for row in members:
        target = tree.get(row['path'], {})
        if target.get('mode') not in {'100644', '100755'} or row['mode'] != (0o755 if target['mode'] == '100755' else 0o644):
            raise ValueError('Helper member mode differs from committed B')


def validate_paired_content_provenance(binding, actual, *, archive_helper_report=None, expected_journal_identity_sha256=None):
    """Content lineage is explicit; absent native Git metadata stays absent."""
    report = actual.get('archive_helper_report') if archive_helper_report is None else archive_helper_report
    if 'archive_helper_report' in actual and actual['archive_helper_report'] != report:
        raise ValueError('Post-write helper receipt differs from original input')
    _paired_helper_receipt(binding, report)
    expected = _paired_input(binding)
    lineage = actual.get('paired_content_provenance')
    fields = {'schema', 'lineage_kind', 'operation_id', 'deployment_id', 'retained_image_id',
        'runtime_sha256', 'config_sha256', 'archive_helper_report_sha256',
        'archive_member_manifest_sha256', 'archive_member_modes_sha256',
        'native_observation_receipt_sha256', 'runtime_attestation_receipt_sha256', 'provider_git_sha',
        'input_git_source_sha', 'operations_journal_identity_sha256'}
    if (not isinstance(lineage, dict) or set(lineage) != fields
            or lineage['schema'] != PAIRED_LINEAGE_SCHEMA
            or lineage['lineage_kind'] != 'CONTENT_ARCHIVE_MEMBERS_AND_RUNTIME_ATTESTATION'):
        raise ValueError('Explicit paired native content lineage required')
    native_id = actual.get('deployment_id')
    if (not isinstance(native_id, str) or not re.fullmatch('[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}', native_id)
            or not isinstance(actual.get('retained_image_id'), str) or not actual['retained_image_id']):
        raise ValueError('Actual paired native deployment/image identity required')
    if not require_digest(expected_journal_identity_sha256):
        raise ValueError('Original paired operations journal custody required')
    required = {'input_git_source_sha': binding['source_sha'],
        'operations_journal_identity_sha256': expected_journal_identity_sha256,
        'operation_id': operation_identity('release_guarded_bootstrap', binding),
        'deployment_id': native_id, 'retained_image_id': actual['retained_image_id'],
        'runtime_sha256': binding['source_delivery_sha256'], 'config_sha256': binding['config_sha256'],
        'archive_helper_report_sha256': expected['expected_archive_helper_report_sha256'],
        'archive_member_manifest_sha256': expected['archive_member_manifest_sha256'],
        'archive_member_modes_sha256': expected['archive_member_modes_sha256']}
    if actual.get('operation_id') != required['operation_id'] or any(lineage.get(k) != v for k, v in required.items()):
        raise ValueError('Actual operation/image/runtime/config content lineage differs')
    for field in ('native_observation_receipt_sha256', 'runtime_attestation_receipt_sha256'):
        if not require_digest(lineage[field]) or actual.get(field) != lineage[field]:
            raise ValueError('Actual native/runtime observation receipt required: ' + field)
    if ('provider_git_sha' not in actual or actual['provider_git_sha'] != lineage['provider_git_sha']
            or (lineage['provider_git_sha'] is not None and
                (not isinstance(lineage['provider_git_sha'], str) or not re.fullmatch('[a-f0-9]{40}', lineage['provider_git_sha'])))):
        raise ValueError('Separately observed native Git metadata required')


def _qualify_bootstrap_body(binding, actual, *, source_field, archive_helper_report=None, expected_journal_identity_sha256=None):
    """Post-write actual read-only qualification; never a preflight PASS substitute."""
    if actual.get('scope')!='ACTUAL_PROVIDER_AND_SOURCE' or actual.get('action')!='release_guarded_bootstrap' or actual.get(source_field)!=binding['source_sha']:
        raise ValueError('Actual exact bootstrap observation required')
    for key in ('source_delivery_sha256','closed_server_sha256'):
        if actual.get(key)!=binding.get(key) or not require_digest(actual.get(key)):
            raise ValueError('Bootstrap measured source mismatch')
    # A supplied measured runtime must agree with the delivered source. Legacy
    # observers may omit it (or retain None); that is not measured provenance.
    runtime = actual.get('runtime_sha256')
    if runtime is not None and (not require_digest(runtime) or runtime != binding.get('source_delivery_sha256')):
        raise ValueError('Bootstrap measured runtime differs from delivered source')
    if 'backend_export_root' in binding and not require_digest(runtime):
        raise ValueError('Paired bootstrap requires actual measured runtime')
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
    if 'backend_export_root' in binding:
        validate_paired_content_provenance(binding, actual, archive_helper_report=archive_helper_report, expected_journal_identity_sha256=expected_journal_identity_sha256)
    return actual['recovery_receipt_sha256']


def qualify_bootstrap_recovery(binding, actual, *, archive_helper_report=None, expected_journal_identity_sha256=None):
    # Paired evidence identifies a reviewed CONTENT INPUT. It does not infer
    # provider Git metadata from the Git SHA selected by the operator.
    return _qualify_bootstrap_body(binding, actual,
        source_field='input_git_source_sha' if 'backend_export_root' in binding else 'source_sha',
        archive_helper_report=archive_helper_report,
        expected_journal_identity_sha256=expected_journal_identity_sha256)


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
    if not isinstance(proof,dict) or qualify_bootstrap_recovery(boot['binding'],proof, archive_helper_report=boot.get('paired_archive_helper_evidence'), expected_journal_identity_sha256=boot.get('operations_journal_identity_sha256'))!=recovery:
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
    if 'backend_export_root' in boot['binding']:
        expected_native['input_git_source_sha'] = expected_native.pop('source_sha')
        expected_native['lineage_kind'] = 'CONTENT_ARCHIVE_MEMBERS_AND_RUNTIME_ATTESTATION'
        expected_native['provider_git_sha'] = proof['provider_git_sha']
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
    if 'native_source_successor' in binding:
        if action!='release_guarded_bootstrap':raise ValueError('Source successor applies only to exact guarded bootstrap')
        pair.validate_source_successor(binding.get('native_action_scope',{}),binding)
        if approval.get('native_source_successor_sha256')!=digest(binding['native_source_successor']):
            raise ValueError('Protected approval must bind exact source successor')
    if 'native_build_amendment' in binding:
        if action!='stage_frontend':raise ValueError('Build amendment applies only to exact stage operation')
        pair.validate_build_amendment(binding.get('native_action_scope',{}),binding['native_build_amendment'])
        if approval.get('native_build_amendment_sha256') != digest(binding['native_build_amendment']):
            raise ValueError('Protected approval must bind actual second-build amendment')
    if 'first_guard_pair' in binding:
        c=pair.validate(binding)
        if 'owner_acceptance_applicability' in c and approval.get('reader_owner_applicability_sha256')!=digest(c['owner_acceptance_applicability']):
            raise ValueError('Protected approval must bind exact Reader owner applicability')
        if approval.get('first_guard_failure_policy_sha256')!=digest(c['policy']):
            raise ValueError('Actual protected failure policy binding required')
    if 'native_action_scope' in binding and approval.get('native_action_scope_sha256')!=digest(binding['native_action_scope']):
        raise ValueError('Protected operation must bind actual original native scope')
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
    maximum = timedelta(minutes=15) if binding.get('frontend_phase') == 'STAGE_ONLY' else timedelta(hours=24)
    if not start <= now < end or end - start > maximum:
        raise ValueError('Expired/future/overlong approval')
    if not timedelta(0) <= now - observed <= timedelta(minutes=15):
        raise ValueError('Stale or future provider evidence')


FRONTEND_TARGET_FIELDS = {'deployment_id', 'source_sha', 'config_sha256'}
FRONTEND_RETURN_FIELDS = {'operations_journal_identity_sha256', 'applied_promotion_operation_id',
    'applied_promotion_record_sha256', 'applied_promotion_reconciliation_receipt_sha256',
    'target_deployment_id', 'target_source_sha', 'target_config_sha256',
    'current_bad_frontend_deployment_id', 'bad_frontend_failure_receipt_sha256',
    'backend_deployment_id', 'backend_source_sha', 'backend_phase'}


def validate_frontend_target(binding, actual):
    """Optional future promotion contract; legacy receipts cannot gain it later."""
    target = binding.get('frontend_restore_target')
    if not isinstance(target, dict) or set(target) != FRONTEND_TARGET_FIELDS:
        raise ValueError('Exact frontend restore target required')
    if (not re.fullmatch(r'dpl_[A-Za-z0-9]+', target.get('deployment_id', ''))
            or not re.fullmatch('[a-f0-9]{40}', target.get('source_sha', ''))
            or not require_digest(target.get('config_sha256'))
            or target['deployment_id'] != binding.get('rollback_frontend_deployment_id')
            or target['source_sha'] != binding.get('rollback_frontend_source_sha')):
        raise ValueError('Frontend restore target differs from admitted rollback')
    if (actual.get('frontend_restore_target') != target
            or actual.get('frontend_restore_target_verified') is not True):
        raise ValueError('Actual frontend restore target unavailable')
    return target


def validate_frontend_restore_context(journal, binding, actual, approval=None):
    """One return per actual applied promotion, in its original physical journal."""
    c = binding.get('frontend_restore_context')
    if not isinstance(c, dict) or set(c) != FRONTEND_RETURN_FIELDS:
        raise ValueError('Exact frontend return context required')
    for key in ('operations_journal_identity_sha256', 'applied_promotion_operation_id',
                'applied_promotion_record_sha256', 'applied_promotion_reconciliation_receipt_sha256',
                'target_config_sha256', 'bad_frontend_failure_receipt_sha256'):
        if not require_digest(c[key]): raise ValueError('Invalid frontend return digest: ' + key)
    custody = _operation_journal_identity(journal)
    if c['operations_journal_identity_sha256'] != custody:
        raise ValueError('Original frontend journal custody differs')
    try:
        parent = _read_journal(Path(journal) / (c['applied_promotion_operation_id'] + '.json'))
    except OSError as error:
        raise ValueError('Original applied frontend promotion unavailable') from error
    if (parent.get('action') != 'promote_frontend' or parent.get('state') != 'APPLIED_VERIFIED'
            or parent.get('operation_id') != c['applied_promotion_operation_id']
            or operation_identity('promote_frontend', parent['binding']) != parent['operation_id']
            or digest(parent) != c['applied_promotion_record_sha256']
            or parent.get('reconciliation_receipt_sha256') != c['applied_promotion_reconciliation_receipt_sha256']
            or parent.get('operations_journal_identity_sha256') != custody):
        raise ValueError('Exact same-journal applied promotion required')
    target = {'deployment_id': c['target_deployment_id'], 'source_sha': c['target_source_sha'],
              'config_sha256': c['target_config_sha256']}
    proof = parent.get('qualified_frontend_restore_target')
    if (not isinstance(proof, dict) or proof != target
            or validate_frontend_target(parent['binding'], {'frontend_restore_target': proof,
                'frontend_restore_target_verified': True}) != target):
        raise ValueError('Permanent original frontend target proof missing')
    if (binding.get('applied_promotion_operation_id') != parent['operation_id']
            or binding.get('source_sha') != target['source_sha']
            or binding.get('config_sha256') != target['config_sha256']
            or parent['binding'].get('deployment_id') != c['current_bad_frontend_deployment_id']
            or target['deployment_id'] == c['current_bad_frontend_deployment_id']):
        raise ValueError('Frontend return target/root differs')
    if (not re.fullmatch('[a-f0-9]{40}', c['backend_source_sha'])
            or not isinstance(c['backend_deployment_id'], str)
            or not re.fullmatch('[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}', c['backend_deployment_id'])
            or c['backend_phase'] not in {'BACKEND_UNCHANGED', 'GUARD_ACTIVE'}):
        raise ValueError('Exact current backend context required')
    for key in ('backend_deployment_id', 'backend_source_sha', 'backend_phase'):
        if actual.get(key) != c[key]: raise ValueError('Current backend context differs: ' + key)
    if c['backend_phase'] == 'BACKEND_UNCHANGED':
        if (actual.get('backend_unchanged') is not True
                or parent['binding'].get('backend_source_sha') != c['backend_source_sha']):
            raise ValueError('Original backend no longer unchanged')
    elif actual.get('target_signed_purchase_ready') is not True:
        raise ValueError('Unsigned frontend cannot recover guarded backend')
    if (actual.get('frontend_restore_target') != target
            or actual.get('config_sha256') != target['config_sha256']
            or actual.get('frontend_restore_sha256') != digest(c)
            or (approval is not None and approval.get('config_sha256') != target['config_sha256'])):
        raise ValueError('Actual frontend target/config/context differs')
    if actual.get('target_project_id') != PROJECT or actual.get('target_team_id') != TEAM:
        raise ValueError('Frontend target provider project/team differs')
    for key in ('native_frontend_restore_available', 'target_ready', 'target_source_verified',
                'target_config_verified', 'frontend_backend_compatible', 'known_frontend_failure_qualified'):
        if actual.get(key) is not True: raise ValueError('Frontend return unqualified: ' + key)
    if actual.get('health_book_statuses') != [200, 200] or actual.get('guest_manifest_status') != 401:
        raise ValueError('Frontend return candidate unqualified')
    failure = actual.get('bad_frontend_failure_receipt')
    if (not isinstance(failure, dict) or digest(failure) != c['bad_frontend_failure_receipt_sha256']
            or failure.get('scope') != 'ACTUAL_APPLIED_FRONTEND_FAILURE'
            or failure.get('operation_id') != parent['operation_id']
            or failure.get('promotion_reconciliation_receipt_sha256') != parent['reconciliation_receipt_sha256']
            or failure.get('deployment_id') != c['current_bad_frontend_deployment_id']
            or failure.get('source_sha') != parent['binding']['source_sha']
            or failure.get('project') != PROJECT or failure.get('team') != TEAM):
        raise ValueError('Exact actual frontend failure required')
    return c


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
        if action == 'restore_frontend':
            target = binding['frontend_restore_context']['target_deployment_id']
            if not re.fullmatch(r'dpl_[A-Za-z0-9]+', target):
                raise ValueError('Invalid exact frontend return target')
            return ['vercel', 'rollback', target, '--yes', '--scope', TEAM]
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
        validate_approval(action,binding,approval,self.owner_authorized,self.clock())
        if not self.journal.exists():
            if 'first_guard_pair' in binding:raise ValueError('First guard pair requires original admitted journal')
            return self._perform_locked(action,binding,approval)
        lock_path=self.journal/'.reconciliation.lock'
        fd=os.open(lock_path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
        try:
            info=os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600:
                raise ValueError('Unsafe operation lock')
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError as error:raise FileExistsError('Another operation owns the journal') from error
            return self._perform_locked(action,binding,approval,lock_held=True)
        finally:os.close(fd)

    def _perform_locked(self, action, binding, approval, lock_held=False):
        self._pending_admission(action,binding)
        self._native_budget(action,binding)
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
        if action == 'restore_frontend':
            claim = self.journal / ('.frontend-return-' + binding['applied_promotion_operation_id'] + '.claim')
            if claim.exists():
                raise FileExistsError('Applied promotion already consumed its frontend return')
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
            if record.get('state') == pair.PENDING and self._pending_admission(action,binding) is not None:
                continue
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
        self._native_budget(action,binding,actual=actual)
        if 'first_guard_pair' in binding:
            pair.validate(binding,actual)
            if actual.get('first_guard_failure_policy_sha256')!=approval.get('first_guard_failure_policy_sha256'):
                raise ValueError('Fresh protected first guard policy differs')
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
        if action == 'restore_frontend':
            validate_frontend_restore_context(self.journal, binding, actual, approval)
            if actual.get('current_frontend_deployment_id') != binding['frontend_restore_context']['current_bad_frontend_deployment_id']:
                raise ValueError('Current frontend changed; refusing to replace unrelated deployment')
        if action == 'promote_frontend' and 'frontend_restore_target' in binding:
            validate_frontend_target(binding, actual)
        validate_action_recovery(action, binding, actual)
        if action == 'stage_frontend' and binding.get('frontend_phase') == 'STAGE_ONLY':
            validate_stage_only_source(binding)
        if action == 'promote_frontend':
            artifact_stage = any(r.get('action') == 'stage_frontend' and r.get('binding', {}).get('frontend_phase') == 'STAGE_ONLY'
                and r.get('binding', {}).get('source_sha') == binding.get('source_sha')
                and r.get('provider_deployment_id') == binding.get('deployment_id') for r in prior_records)
            if artifact_stage or 'stage_artifact_reference' in binding:
                validate_stage_artifact_reference(self.journal, binding)
                if actual.get('backend_config_sha256') != binding.get('backend_config_sha256'):
                    raise ValueError('Fresh actual guarded backend config differs from staged intent')
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
        if action in {'restore_guarded_bootstrap', 'restore_frontend'}:
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
            if paired:validate_paired_archive_input(binding, actual, payload)
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
        write_lock=None
        if not lock_held:
            write_lock=os.open(self.journal/'.reconciliation.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
            try:fcntl.flock(write_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError as error:
                os.close(write_lock)
                raise FileExistsError('Another operation owns the journal') from error
        anchor = None
        if action in {'restore_guarded_bootstrap', 'restore_frontend'} or 'first_guard_pair' in binding or 'native_action_scope' in binding:
            anchor = os.open(self.journal, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        def durable(path, value, **kwargs):
            if anchor is None:return _durable_json(path, value, **kwargs)
            return _durable_json(path, value, directory_fd=anchor, **kwargs)
        context_key = 'frontend_restore_context' if action == 'restore_frontend' else 'restore_context'
        try:
            if anchor is not None:
                _assert_operation_journal_anchor(self.journal, anchor,
                    (binding['native_action_scope']['operations_journal_identity_sha256'] if 'native_action_scope' in binding else binding['first_guard_pair']['projection']['operations_journal_identity_sha256'] if 'first_guard_pair' in binding else binding[context_key]['operations_journal_identity_sha256']))
            self._native_budget(action,binding,actual=actual,claim=True,durable=durable)
            barrier = self.journal / '_write-barrier.json'
            durable(barrier, {'operation_id': operation_id, 'state': 'INTENT_RECONCILE_BEFORE_RETRY'}, exclusive=True)
            pending=self._read_pending()
            if pending is not None:
                if pending.get('child_operation_id') not in {None,operation_id}:raise ValueError('Child attempt already consumed')
                pending['child_operation_id']=operation_id
                durable(self.journal/'.first-guard-pending',pending)
            intent = {'operation_id': operation_id, 'action': action, 'binding': binding,
                      'approval_sha256': digest(approval), 'started_at': self.clock().isoformat(),
                      'state': 'INTENT_RECONCILE_BEFORE_RETRY'}
            if action in {'release_backend', 'release_guarded_bootstrap', 'restore_guarded_bootstrap', 'stage_frontend', 'promote_frontend', 'restore_frontend'}:
                intent['operations_journal_identity_sha256'] = (binding[context_key]['operations_journal_identity_sha256']
                    if anchor is not None and 'first_guard_pair' not in binding and 'native_action_scope' not in binding else _operation_journal_identity(self.journal))
            if action == 'promote_frontend' and 'frontend_restore_target' in binding:
                intent['qualified_frontend_restore_target'] = validate_frontend_target(binding, actual)
            if action == 'stage_frontend' and binding.get('frontend_phase') == 'STAGE_ONLY':
                intent['stage_input_projection'] = validate_stage_only(binding, actual)
            if paired:
                # Keep the original local helper receipt once. It remains local
                # helper evidence, never an uploaded archive checksum.
                intent['paired_archive_helper_evidence'] = actual['archive_helper_report']
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
            if action == 'restore_frontend':
                validate_frontend_restore_context(self.journal, binding, actual, approval)
                durable(claim, {'applied_promotion_operation_id': binding['applied_promotion_operation_id'],
                    'operation_id': operation_id, 'state': 'FRONTEND_RETURN_CONSUMED_NO_RETRY'}, exclusive=True)
            request = self.journal / (operation_id + '.request.json')
            if action == 'restore_frontend':
                durable(request, {'action': action, 'binding_sha256': digest(binding),
                    'frontend_restore_context': binding['frontend_restore_context']}, exclusive=True)
            if action == 'stage_frontend':
                durable(request, stage_frontend_request(binding), exclusive=True)
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
                validate_paired_archive_input(binding, actual, final_payload)
                validate_approval(action, binding, approval, self.owner_authorized, self.clock())
                validate_startup_qualification(binding, approval, actual, self.clock())
                command = self._command(action, binding, request, backend_payload=final_payload)
                command_cwd = final_payload['archive_prefix']
            else:
                command = self._command(action, binding, request)
                command_cwd = source
            if action == 'stage_frontend' and binding.get('frontend_phase') == 'STAGE_ONLY':
                validate_stage_only_source(binding)
                validate_stage_only(binding, actual)
                if _read_journal(request) != stage_frontend_request(binding):
                    raise ValueError('Durable private stage request changed before dispatch')
                validate_approval(action, binding, approval, self.owner_authorized, self.clock())
            if action == 'restore_guarded_bootstrap':
                # Durable writes above target the original descriptor even if its
                # pathname was replaced. A changed path/custody never reaches CLI.
                validate_guarded_restore_context(self.journal, binding, actual, approval)
                validate_approval(action, binding, approval, self.owner_authorized, self.clock())
                validate_startup_qualification(binding, approval, actual, self.clock())
                _assert_operation_journal_anchor(self.journal, anchor,
                    binding[context_key]['operations_journal_identity_sha256'])
            if action == 'restore_frontend':
                validate_frontend_restore_context(self.journal, binding, actual, approval)
                if actual.get('current_frontend_deployment_id') != binding['frontend_restore_context']['current_bad_frontend_deployment_id']:
                    raise ValueError('Current frontend changed before return dispatch')
                validate_approval(action, binding, approval, self.owner_authorized, self.clock())
                _assert_operation_journal_anchor(self.journal, anchor, binding[context_key]['operations_journal_identity_sha256'])
            self._pending_admission(action,binding,own_operation_id=operation_id,actual=actual)
            self._native_budget(action,binding,actual=actual,own_operation_id=operation_id)
            if 'first_guard_pair' in binding:
                pair.validate(binding,actual)
                _assert_operation_journal_anchor(self.journal,anchor,binding['first_guard_pair']['projection']['operations_journal_identity_sha256'])
            if 'native_action_scope' in binding:
                _assert_operation_journal_anchor(self.journal,anchor,binding['native_action_scope']['operations_journal_identity_sha256'])
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
            if write_lock is not None:os.close(write_lock)


    def _native_budget(self,action,binding,*,actual=None,claim=False,durable=None,own_operation_id=None):
        scope=binding.get('native_action_scope')
        scope_claim=self.journal/'.native-action-scope.claim'
        if scope is None:
            baseline_path=self.journal/'.native-action-baseline.receipt'
            if ('first_guard_pair' in binding or scope_claim.exists() or scope_claim.is_symlink()
                    or baseline_path.exists() or baseline_path.is_symlink()):
                raise ValueError('Stable original native scope required from baseline admission; no unscoped writes')
            return
        def raw(path):
            fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
            with os.fdopen(fd,'rb') as stream:
                info=os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600 or info.st_size>1024*1024:raise ValueError('Unsafe budget journal input')
                data=stream.read(1024*1024+1)
            if len(data)>1024*1024:raise ValueError('Oversized budget input')
            value=json.loads(data)
            if not isinstance(value,dict):raise ValueError('Malformed budget input')
            return value,hashlib.sha256(data).hexdigest()
        if not (self.journal/'.native-action-baseline.receipt').exists():raise ValueError('Actual Root immutable baseline unavailable; execution held')
        baseline,_=raw(self.journal/'.native-action-baseline.receipt')
        pair.validate_scope(scope,baseline,_operation_journal_identity(self.journal))
        if 'native_build_amendment' in binding:
            if action!='stage_frontend':raise ValueError('Build amendment applies only to exact stage operation')
            pair.validate_build_amendment(scope,binding['native_build_amendment'])
            if actual is not None and actual.get('native_build_amendment_sha256') != digest(binding['native_build_amendment']):
                raise ValueError('Trusted actual Root second-build amendment observation required')
        if 'native_source_successor' in binding:
            if action!='release_guarded_bootstrap':raise ValueError('Source successor applies only to exact guarded bootstrap')
            pair.validate_source_successor(scope,binding)
            if actual is not None and actual.get('native_source_successor_sha256')!=digest(binding['native_source_successor']):
                raise ValueError('Trusted actual Root source successor observation required')
        elif action == 'release_guarded_bootstrap' and binding.get('source_sha') != scope['intended_closed_source_sha']:
            raise ValueError('Actual CLOSED source differs from original native scope')
        if scope_claim.exists():
            if _read_journal(scope_claim)!={'schema':'earnalism.native_action_scope_claim.v1','scope':scope}:
                raise ValueError('Original baseline/scope claim changed; never reset')
        if actual is not None:
            if (actual.get('native_action_scope')!=scope or actual.get('native_action_baseline_sha256')!=scope['baseline_sha256']
                    or actual.get('native_action_scope_authorization')!='ACTUAL_ROOT_PREWRITE_BASELINE'):
                raise ValueError('Trusted actual Root baseline admission required')
        records=[]
        for path in self.journal.glob('*.json'):
            if path.name.endswith('.request.json') or path.name=='_write-barrier.json':continue
            records.append(raw(path))
        if not scope_claim.exists():
            historical=set(baseline['historical_terminal_operations'])
            if any(r.get('operation_id') not in historical for r,_ in records):raise ValueError('Cannot install/adopt baseline after new actions started')
        by_id={r['operation_id']:r for r,_ in records}
        for artifact in self.journal.iterdir():
            name=artifact.name
            if name.endswith('.json') or name in {'.reconciliation.lock','.native-action-baseline.receipt','.native-action-scope.claim','.first-guard-pending'}:continue
            if re.fullmatch(r'.first-guard-component-[a-f0-9]{64}\.receipt',name):
                value=raw(artifact)[0]
                if value.get('schema')!='earnalism.first_guard_actual_component.v1' or value.get('scope')!='ACTUAL_COMPONENT_ONLY_READER_PENDING' or name!='.first-guard-component-'+value.get('operation_id','')+'.receipt' or digest(value.get('original_record'))!=value.get('original_record_sha256'):
                    raise ValueError('Malformed local component receipt is not a provider-intent exemption')
            elif re.fullmatch(r'.first-guard-final-[a-f0-9]{64}\.receipt',name):
                value=raw(artifact)[0]
                if set(value)!={'schema','parent_operation_id','component_receipt_sha256','child_record_sha256','actual'} or value['schema']!='earnalism.first_guard_final_pair.v1' or name!='.first-guard-final-'+value['parent_operation_id']+'.receipt':raise ValueError('Malformed local pair receipt')
            elif re.fullmatch(r'.(frontend-return|guarded-return|backend-correction)-[a-f0-9]{64}\.claim',name):
                value=raw(artifact)[0]
                if value.get('operation_id') not in by_id:raise ValueError('Unknown claimed write uncertainty')
            else:raise ValueError('Unclassified journal artifact blocks scoped dispatch')
        if own_operation_id is not None:
            own=by_id.get(own_operation_id)
            if not own or own.get('binding')!=binding or own.get('action')!=action or operation_identity(action,binding)!=own_operation_id:
                raise ValueError('Exact durable self-intent preimage changed before dispatch')
        historical_requests=baseline['historical_request_artifacts']
        observed_historical_requests=set()
        for request in self.journal.glob('*.request.json'):
            op=request.name[:-len('.request.json')]
            if op not in by_id:raise ValueError('Orphan request uncertainty requires read-only reconciliation')
            body,request_raw_sha=raw(request)
            if op in baseline['historical_terminal_operations']:
                # Preserve authentic legacy requests exactly; current request
                # schemas cannot reinterpret historical custom native actions.
                if historical_requests.get(op)!=request_raw_sha:
                    raise ValueError('Historical request artifact changed or was not admitted')
                observed_historical_requests.add(op)
                continue
            original=by_id[op];b=original['binding'];kind=original['action']
            if kind=='stage_frontend':expected=stage_frontend_request(b)
            elif kind=='restore_frontend':expected={'action':kind,'binding_sha256':digest(b),'frontend_restore_context':b['frontend_restore_context']}
            elif kind=='restore_guarded_bootstrap':expected={'action':kind,'binding_sha256':digest(b),'restore_context':b['restore_context'],'native_query':self._command(kind,b,request)[2]}
            else:raise ValueError('Unrecognized provider request artifact')
            if body!=expected:raise ValueError('Provider request artifact differs from original intent')
        if observed_historical_requests!=set(historical_requests):
            raise ValueError('Historical request artifact missing')
        barrier=self.journal/'_write-barrier.json'
        if barrier.exists():
            op=raw(barrier)[0].get('operation_id')
            if op not in by_id:raise ValueError('Orphan claimed write uncertainty blocks dispatch')
            _validate_barrier(barrier,op)
        candidate={'operation_id':operation_identity(action,binding),'action':action,'binding':binding}
        counts=pair.count_scoped_intents(scope,baseline,records,candidate=candidate)
        if claim and not scope_claim.exists():
            durable(scope_claim,{'schema':'earnalism.native_action_scope_claim.v1','scope':scope},exclusive=True)
        return counts

    def _read_pending(self):
        path=self.journal/'.first-guard-pending'
        if not path.exists():
            # A partial component seal cannot silently become a free writer slot.
            if any(self.journal.glob('.first-guard-component-*.receipt')):
                rows=[_read_journal(p) for p in self.journal.glob('*.json') if not p.name.endswith('.request.json') and p.name!='_write-barrier.json']
                for receipt in self.journal.glob('.first-guard-component-*.receipt'):
                    comp=_read_journal(receipt)
                    matches=[r for r in rows if r.get('operation_id')==comp.get('operation_id') and r.get('state')=='APPLIED_VERIFIED' and r.get('component_receipt_sha256')==digest(comp) and require_digest(r.get('first_guard_final_receipt_sha256'))]
                    if len(matches)!=1:raise ValueError('Partial component transition requires read-only repair')
            return None
        pending=_read_journal(path)
        if pending.get('journal_identity_sha256') != _operation_journal_identity(self.journal):
            raise ValueError('Original pending pair journal custody changed')
        component=_read_journal(self.journal/pending['component_receipt_name'])
        if digest(component)!=pending.get('component_receipt_sha256'):
            raise ValueError('Immutable component receipt changed')
        return pending

    def _pending_admission(self,action,binding,own_operation_id=None,actual=None):
        if 'first_guard_pair' in binding:
            pair.validate(binding)
            if not isinstance(binding.get('native_action_scope'),dict):raise ValueError('First guard pair requires original scoped stage budget')
        pending=self._read_pending()
        if pending is None:
            if 'first_guard_pair' in binding and action=='release_guarded_bootstrap':
                f=binding['first_guard_pair']['policy']
                stage=_read_journal(self.journal/(f['staged_operation_id']+'.json'))
                if digest(stage)!=f['staged_record_sha256'] or stage.get('state')!='APPLIED_VERIFIED' or stage.get('action')!='stage_frontend' or stage.get('provider_deployment_id')!=f['staged_deployment_id'] or stage.get('binding',{}).get('source_sha')!=f['staged_source_sha'] or stage.get('binding',{}).get('native_action_scope')!=binding['native_action_scope']:
                    raise ValueError('Exact original scoped staged candidate required before B1')
            if 'first_guard_parent_operation_id' in binding:raise ValueError('Missing original pending parent')
            return None
        if pending.get('state') != pair.PENDING or action!='promote_frontend':
            raise ValueError('Pending pair blocks this write')
        parent=_read_journal(self.journal/(pending['parent_operation_id']+'.json'))
        if parent.get('state')!=pair.PENDING or digest(parent)!=pending['parent_record_sha256']:
            raise ValueError('Pending parent preimage changed')
        c=pair.validate(parent['binding']);f=c['policy']
        if (binding.get('first_guard_pair')!=c or binding.get('first_guard_parent_operation_id')!=parent['operation_id']
                or binding.get('source_sha')!=f['staged_source_sha'] or binding.get('deployment_id')!=f['staged_deployment_id']
                or binding.get('component_receipt_sha256')!=pending['component_receipt_sha256'] or binding.get('native_action_scope')!=parent['binding'].get('native_action_scope')):
            raise ValueError('Only exact component-bound child promotion permitted')
        stage=_read_journal(self.journal/(f['staged_operation_id']+'.json'))
        if (digest(stage)!=f['staged_record_sha256'] or stage.get('state')!='APPLIED_VERIFIED'
                or stage.get('action')!='stage_frontend' or stage.get('provider_deployment_id')!=f['staged_deployment_id']
                or stage.get('binding',{}).get('source_sha')!=f['staged_source_sha']):
            raise ValueError('Original exact actual staged child required')
        barrier=self.journal/'_write-barrier.json'
        if barrier.exists() and (_read_journal(barrier).get('operation_id')!=own_operation_id or own_operation_id is None):
            raise ValueError('Unknown write barrier cannot be cleared by pending pair')
        if actual is not None:
            native=_read_journal(self.journal/pending['component_receipt_name'])['native']
            for observed,key in (('backend_deployment_id','deployment_id'),('backend_runtime_sha256','runtime_sha256'),('backend_config_sha256','config_sha256')):
                if actual.get(observed)!=native.get(key):raise ValueError('Fresh actual component changed before child promotion')
        return pending

    def _reconcile_component(self,record,actual):
        binding=record['binding'];c=pair.validate(binding,actual);op=record['operation_id']
        self._native_budget('release_guarded_bootstrap',binding,actual=actual,own_operation_id=op)
        if record.get('state') not in {'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED',pair.PENDING}:
            raise ValueError('Only attempted/nonterminal component can be qualified')
        if actual.get('outcome')!='APPLIED' or actual.get('runtime_sha256')!=binding.get('source_delivery_sha256') or actual.get('config_sha256')!=binding.get('config_sha256'):
            raise ValueError('Actual known component identity required')
        if actual.get('runtime_manifest_sha256')!=c['projection']['runtime_manifest_sha256']:raise ValueError('Actual complete runtime manifest differs')
        if actual.get('source_delivery_sha256')!=binding.get('source_delivery_sha256') or actual.get('closed_server_sha256')!=binding.get('closed_server_sha256'):
            raise ValueError('Actual exact component source required')
        for key in ('startup_complete','database_healthy','source_attestation_matches','verify_refund_webhook_code_preserved'):
            if actual.get(key) is not True:raise ValueError('Actual component evidence missing: '+key)
        for key in ('auto_deploy','redis_enabled','redis_cache_enabled','multi_replica_enabled','redis_public_metadata_enabled'):
            if actual.get(key) is not False:raise ValueError('Actual suppression missing: '+key)
        if actual.get('closed_guest_status')!=503 or actual.get('purchase_pause_proof')!='MEASURED_EXACT_EARLY_RETURN_AND_ANONYMOUS_503' or not actual.get('retained_image_id') or not actual.get('deployment_id'):
            raise ValueError('Actual CLOSED/native image evidence missing')
        custody=_operation_journal_identity(self.journal)
        if custody!=c['projection']['operations_journal_identity_sha256'] or record.get('operations_journal_identity_sha256')!=custody:
            raise ValueError('Original component journal differs')
        if 'backend_export_root' in binding:
            validate_paired_content_provenance(binding,actual,archive_helper_report=record.get('paired_archive_helper_evidence'),expected_journal_identity_sha256=custody)
        # Scope is typed: no full recovery or Reader-preserved assertion inferred.
        component_keys={'scope','action','source_sha','input_git_source_sha','outcome','operation_id','receipt_sha256','source_delivery_sha256','closed_server_sha256','runtime_sha256','runtime_manifest_sha256','config_sha256','deployment_id','retained_image_id','closed_guest_status','purchase_pause_proof','startup_complete','database_healthy','source_attestation_matches','verify_refund_webhook_code_preserved','auto_deploy','redis_enabled','redis_cache_enabled','multi_replica_enabled','redis_public_metadata_enabled','provider_git_sha','paired_content_provenance','native_observation_receipt_sha256','runtime_attestation_receipt_sha256','reader_migration_owner_acceptance','containment_operator_reference','first_guard_policy_sha256','native_action_scope','native_action_baseline_sha256','native_action_scope_authorization','observed_at'}
        if 'native_source_successor' in binding:component_keys.add('native_source_successor_sha256')
        if 'owner_acceptance_applicability' in binding.get('first_guard_pair',{}):component_keys.add('reader_owner_applicability_sha256')
        native_projection={k:actual[k] for k in component_keys if k in actual}
        component={'schema':'earnalism.first_guard_actual_component.v1','scope':'ACTUAL_COMPONENT_ONLY_READER_PENDING','operation_id':op,'binding_sha256':digest(binding),'approval_sha256':record['approval_sha256'],'native':native_projection,'original_record_sha256':digest(record),'original_record':record}
        name='.first-guard-component-'+op+'.receipt';path=self.journal/name
        anchor=os.open(self.journal,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            _assert_operation_journal_anchor(self.journal,anchor,custody)
            barrier=self.journal/'_write-barrier.json'
            if not barrier.exists():
                # Idempotent read-only component reconciliation does not reopen child dispatch.
                pending=self._read_pending()
                if pending and pending['parent_operation_id']==op:return record
                raise ValueError('Missing original component write barrier')
            _validate_barrier(barrier,op)
            if path.exists():
                old=_read_journal(path)
                if old.get('operation_id')!=op or old.get('binding_sha256')!=digest(binding) or any(old.get('native',{}).get(k)!=actual.get(k) for k in ('deployment_id','retained_image_id','runtime_sha256','config_sha256','source_delivery_sha256','closed_server_sha256')) or digest(old.get('original_record'))!=old.get('original_record_sha256'):
                    raise ValueError('Component preimage differs; no replacement')
                component=old
                if record.get('state')!=pair.PENDING and digest(record)!=old['original_record_sha256']:raise ValueError('Original attempted record changed')
                record=old['original_record']
            else:_durable_json(path,component,exclusive=True,directory_fd=anchor)
            pending={'schema':'earnalism.first_guard_pending.v1','state':pair.PENDING,'parent_operation_id':op,'component_receipt_name':name,'component_receipt_sha256':digest(component),'journal_identity_sha256':custody,'child_operation_id':None}
            guard=self.journal/'.first-guard-pending'
            if guard.exists():
                existing=_read_journal(guard)
                if existing.get('component_receipt_sha256')!=digest(component):raise ValueError('Different pending component')
            else:_durable_json(guard,pending,exclusive=True,directory_fd=anchor)
            record=dict(record,state=pair.PENDING,component_receipt_sha256=digest(component))
            pending['parent_record_sha256']=digest(record)
            _durable_json(self.journal/(op+'.json'),record,directory_fd=anchor)
            _durable_json(guard,pending,directory_fd=anchor)
            _assert_operation_journal_anchor(self.journal,anchor,custody)
            os.unlink(barrier.name,dir_fd=anchor);os.fsync(anchor)
            return record
        finally:os.close(anchor)

    def finalize_first_guard_pair(self,operation_id):
        """Read-only paired acceptance; never dispatch, fabricate approval or retry."""
        lock=os.open(self.journal/'.reconciliation.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
        try:
            info=os.fstat(lock)
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600:raise ValueError('Unsafe finalization lock')
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            pending=self._read_pending()
            if pending is None or pending['parent_operation_id']!=operation_id or pending['state']!='PAIR_READONLY_FINALIZATION_REQUIRED' or (self.journal/'_write-barrier.json').exists():
                raise ValueError('Exact known child must precede read-only finalization')
            record=_read_journal(self.journal/(operation_id+'.json'))
            self._native_budget(record['action'],record['binding'],own_operation_id=operation_id)
            if record.get('state')=='APPLIED_VERIFIED':
                sealed=_read_journal(self.journal/('.first-guard-final-'+operation_id+'.receipt'))
                if digest(sealed)!=record.get('first_guard_final_receipt_sha256') or sealed.get('component_receipt_sha256')!=pending['component_receipt_sha256'] or sealed.get('child_record_sha256')!=pending.get('child_record_sha256'):
                    raise ValueError('Incomplete final hash chain')
                child=_read_journal(self.journal/(pending['child_operation_id']+'.json'))
                if digest(child)!=sealed['child_record_sha256'] or child.get('state')!='APPLIED_VERIFIED':raise ValueError('Final child changed')
                self._native_budget(record['action'],record['binding'],actual=sealed['actual'],own_operation_id=operation_id)
                pair.validate_reader_mode_preservation(record['binding'], sealed['actual'])
                qualify_bootstrap_recovery(record['binding'],sealed['actual'],archive_helper_report=record.get('paired_archive_helper_evidence'),expected_journal_identity_sha256=pending['journal_identity_sha256'])
                # This only completes an interrupted retirement, never amends terminal data.
                anchor=os.open(self.journal,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                try:
                    _assert_operation_journal_anchor(self.journal,anchor,pending['journal_identity_sha256'])
                    os.unlink('.first-guard-pending',dir_fd=anchor);os.fsync(anchor)
                finally:os.close(anchor)
                return record
            if record.get('state')!=pair.PENDING or digest(record)!=pending['parent_record_sha256']:raise ValueError('Nonterminal original parent required')
            child=_read_journal(self.journal/(pending['child_operation_id']+'.json'))
            if digest(child)!=pending.get('child_record_sha256') or child.get('state')!='APPLIED_VERIFIED':raise ValueError('Exact actual child receipt required')
            actual=self.observe('finalize_first_guard_pair',{'parent':record,'child':child,'component_receipt_sha256':pending['component_receipt_sha256']})
            if (actual.get('component_receipt_sha256')!=pending['component_receipt_sha256'] or actual.get('child_record_sha256')!=digest(child)
                    or actual.get('both_aliases_verified') is not True or actual.get('paired_reader_listener_financial_preserved') is not True):
                raise ValueError('Actual paired Reader/Listener/financial evidence required')
            self._native_budget(record['action'],record['binding'],actual=actual,own_operation_id=operation_id)
            component=_read_journal(self.journal/pending['component_receipt_name'])
            for key in ('deployment_id','retained_image_id','runtime_sha256','config_sha256'):
                if actual.get(key)!=component['native'].get(key):raise ValueError('Current actual component changed')
            if actual.get('operation_id')!=operation_id or actual.get('outcome')!='APPLIED' or not require_digest(actual.get('receipt_sha256')):
                raise ValueError('Exact actual final operation proof required')
            for key in ('reader_public_preview_verified','reader_protected_entitlement_verified','listener_protected_accounting_preserved','verify_refund_webhook_code_preserved'):
                if actual.get(key) is not True:raise ValueError('Actual paired acceptance missing: '+key)
            pair.validate_reader_mode_preservation(record['binding'], actual)
            if actual.get('serving_frontend_deployment_id')!=child['binding']['deployment_id'] or actual.get('serving_frontend_source_sha')!=child['binding']['source_sha']:
                raise ValueError('Actual fresh frontend aliases/source mismatch')
            recovery=qualify_bootstrap_recovery(record['binding'],actual,archive_helper_report=record.get('paired_archive_helper_evidence'),expected_journal_identity_sha256=pending['journal_identity_sha256'])
            final={'schema':'earnalism.first_guard_final_pair.v1','parent_operation_id':operation_id,'component_receipt_sha256':pending['component_receipt_sha256'],'child_record_sha256':digest(child),'actual':actual}
            anchor=os.open(self.journal,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:
                _assert_operation_journal_anchor(self.journal,anchor,pending['journal_identity_sha256'])
                final_path=self.journal/('.first-guard-final-'+operation_id+'.receipt')
                if final_path.exists():
                    sealed=_read_journal(final_path)
                    if any(sealed.get(k)!=final.get(k) for k in ('parent_operation_id','component_receipt_sha256','child_record_sha256')) or any(sealed.get('actual',{}).get(k)!=actual.get(k) for k in ('deployment_id','retained_image_id','runtime_sha256','config_sha256','serving_frontend_deployment_id','serving_frontend_source_sha')):
                        raise ValueError('Sealed final receipt differs')
                    final=sealed
                    actual=sealed['actual']
                    recovery=qualify_bootstrap_recovery(record['binding'],actual,archive_helper_report=record.get('paired_archive_helper_evidence'),expected_journal_identity_sha256=pending['journal_identity_sha256'])
                else:_durable_json(final_path,final,exclusive=True,directory_fd=anchor)
                record.update(state='APPLIED_VERIFIED',reconciliation_receipt_sha256=actual['receipt_sha256'],guarded_recovery_receipt_sha256=recovery,qualified_bootstrap_evidence=actual,first_guard_final_receipt_sha256=digest(final))
                _durable_json(self.journal/(operation_id+'.json'),record,directory_fd=anchor)
                os.unlink('.first-guard-pending',dir_fd=anchor);os.fsync(anchor)
                return record
            finally:os.close(anchor)
        finally:os.close(lock)

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
        paired_bootstrap = record['action'] == 'release_guarded_bootstrap' and 'backend_export_root' in record['binding']
        paired_restore = False
        if record['action'] == 'restore_guarded_bootstrap':
            context = record['binding'].get('restore_context', {})
            if isinstance(context, dict) and require_digest(context.get('bootstrap_operation_id')):
                original = _read_journal(self.journal / (context['bootstrap_operation_id'] + '.json'))
                paired_restore = 'backend_export_root' in original.get('binding', {})
        source_field = 'input_git_source_sha' if paired_bootstrap or paired_restore else 'source_sha'
        if (actual.get('scope') != 'ACTUAL_PROVIDER_AND_SOURCE'
                or actual.get('operation_id') != operation_id
                or actual.get('action') != record['action']
                or actual.get(source_field) != record['binding']['source_sha']
                or actual.get('outcome') not in {'APPLIED', 'NOT_APPLIED'}
                or not re.fullmatch('[0-9a-f]{64}', actual.get('receipt_sha256', ''))):
            raise ValueError('Unknown/unbound actual provider outcome')
        if 'native_action_scope' in record['binding']:
            self._native_budget(record['action'],record['binding'],actual=actual,own_operation_id=operation_id)
        if record['action']=='release_guarded_bootstrap' and 'first_guard_pair' in record['binding'] and actual['outcome']=='APPLIED' and record.get('state')!='APPLIED_VERIFIED':
            return self._reconcile_component(record,actual)
        pending=self._read_pending()
        if pending is not None:
            if operation_id not in {pending['parent_operation_id'], pending.get('child_operation_id')}:
                raise ValueError('Pending pair permits only exact read-only reconciliation')
        if record['action']=='release_guarded_bootstrap' and 'first_guard_pair' in record['binding']:
            if record.get('state') == 'APPLIED_VERIFIED':
                raise ValueError('Historical terminal parent cannot be amended')
            if actual['outcome']=='APPLIED':
                return self._reconcile_component(record,actual)
        if record['action'] == 'restore_frontend':
            c = validate_frontend_restore_context(self.journal, record['binding'], actual)
            if record.get('operations_journal_identity_sha256') != c['operations_journal_identity_sha256']:
                raise ValueError('Original frontend return journal differs')
            if actual['outcome'] == 'APPLIED':
                if (actual.get('deployment_id') != c['target_deployment_id']
                        or actual.get('serving_frontend_deployment_id') != c['target_deployment_id']
                        or actual.get('both_aliases_verified') is not True):
                    raise ValueError('Actual frontend return serving identity unavailable')
            else:
                proof = actual.get('native_no_effect_proof')
                if (not isinstance(proof, dict) or proof.get('scope') != 'ACTUAL_FRONTEND_RESTORE_NOT_APPLIED'
                        or proof.get('operation_id') != operation_id
                        or proof.get('current_deployment_id') != c['current_bad_frontend_deployment_id']
                        or proof.get('exact_request_not_applied') is not True
                        or proof.get('both_aliases_unchanged') is not True):
                    raise ValueError('Actual frontend return no-effect proof required')
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
            if paired_restore:
                if ('provider_git_sha' not in actual or (actual['provider_git_sha'] is not None and
                        (not isinstance(actual['provider_git_sha'], str) or not re.fullmatch('[a-f0-9]{40}', actual['provider_git_sha'])))):
                    raise ValueError('Actual paired restore Git observation must remain separate')
                _qualify_bootstrap_body(record['binding'], {**actual,'action':'release_guarded_bootstrap'},
                    source_field='input_git_source_sha')
            else:
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
            custody = None
            if paired_bootstrap:
                custody = _operation_journal_identity(self.journal)
                if record.get('operations_journal_identity_sha256') != custody:
                    raise ValueError('Original paired bootstrap journal custody changed')
            record['guarded_recovery_receipt_sha256']=qualify_bootstrap_recovery(record['binding'], actual,
                archive_helper_report=record.get('paired_archive_helper_evidence'), expected_journal_identity_sha256=custody)
            # Retain a bounded, nonsecret ORIGINAL actual qualification proof.
            # Old digest-only journals remain readable, but cannot authorize a
            # new restore without concrete original image/runtime evidence.
            keys=('scope','action','source_sha','source_delivery_sha256','closed_server_sha256',
                'deployment_id','retained_image_id','runtime_sha256','config_sha256','recovery_receipt_sha256',
                'guarded_backend_deployment_id','closed_guest_status','purchase_pause_proof',
                'startup_complete','database_healthy','source_attestation_matches','native_can_rollback',
                'config_compatible','existing_reader_listener_preserved','verify_refund_webhook_code_preserved')
            record['qualified_bootstrap_evidence']={k:actual.get(k) for k in keys}
            if 'backend_export_root' in record['binding']:
                # Native proof stays image/runtime-bound; do not duplicate the
                # full regular-member helper body inside this nested proof.
                for key in ('input_git_source_sha', 'operation_id', 'paired_content_provenance', 'provider_git_sha',
                            'native_observation_receipt_sha256', 'runtime_attestation_receipt_sha256'):
                    record['qualified_bootstrap_evidence'][key] = actual[key]
        if record['action']=='release_backend' and actual['outcome']=='APPLIED':
            native=actual.get('deployment_id')
            if isinstance(native,str) and re.fullmatch('[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}',native):
                record['provider_backend_deployment_id']=native
        barrier = self.journal / '_write-barrier.json'
        if not barrier.exists():raise ValueError('Missing operation barrier')
        _validate_barrier(barrier, operation_id)
        if record['action'] == 'stage_frontend' and record['binding'].get('frontend_phase') == 'STAGE_ONLY':
            validate_stage_only_result(self.journal, record, actual, self.clock())
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
        if pending is not None and operation_id == pending.get('child_operation_id'):
            pending['child_record_sha256']=digest(record)
            pending['state']='PAIR_READONLY_FINALIZATION_REQUIRED' if actual['outcome']=='APPLIED' else pair.BLOCKED
            _durable_json(self.journal/'.first-guard-pending',pending)
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

    def perform(self, action, binding, approval):
        self.adapter._pending_admission(action,binding)
        self.adapter._native_budget(action,binding)
        records = []
        for path in self.adapter.journal.glob('*.json'):
            if not path.name.endswith('.request.json') and path.name != '_write-barrier.json':
                records.append(_read_journal(path))
        verified = [r for r in records if r.get('state') == 'APPLIED_VERIFIED'
                    and r.get('reconciliation_receipt_sha256')]
        if action == 'promote_frontend':
            if binding.get('frontend_phase') == 'STAGE_ONLY':
                raise ValueError('Artifact-only stage cannot promote')
            matching_stage = [r for r in verified if r.get('action') == 'stage_frontend' and r.get('binding', {}).get('source_sha') == binding.get('source_sha') and r.get('provider_deployment_id') == binding.get('deployment_id')]
            if any(r.get('binding', {}).get('frontend_phase') == 'STAGE_ONLY' for r in matching_stage):
                validate_stage_artifact_reference(self.adapter.journal, binding)
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
