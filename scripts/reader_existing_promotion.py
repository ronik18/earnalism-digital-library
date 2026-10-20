"""Protected-runner retained production promotion; no build, deployment or retry."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import time

from scripts import verify_reader_alias_bindings as gate
from scripts import reader_alias_canaries as smoke


def recovery(env, request=gate.provider_request, clock=time.monotonic, pause=time.sleep):
    """One conditional rollback, only from resolved new serving state; no retry."""
    def get(path):
        return request(path, 'GET', 5, env)
    project = get('/v9/projects/' + gate.PROJECT)
    aliases = {h: get('/v4/aliases/' + h) for h in gate.HOSTS}
    target = get('/v13/deployments/' + gate.ROLLBACK)
    if target.get('meta', {}).get('githubCommitSha') != 'd79acb1952161cd56395e9bb4d7c1001ceaa69bb':
        raise ValueError('Retained rollback source mismatch')
    report = gate.rollback_disposition(project, aliases, target, gate.RETAINED_READY)
    if not report['rollback_post_allowed']:
        return report
    intent = Path(env['RUNNER_TEMP']) / 'reader-rollback-intent.json'
    with intent.open('x') as handle:
        json.dump({'state': 'SINGLE_ATTEMPT_STARTED_NO_RETRY', 'deployment_id': gate.ROLLBACK}, handle)
    try:
        request('/v9/projects/' + gate.PROJECT + '/rollback/' + gate.ROLLBACK, 'POST', 60, env)
    except Exception:
        pass  # Uncertain acknowledgement permits GET resolution only.
    deadline, gets = clock() + 60, 0
    while gets < 24 and clock() < deadline:
        project = request('/v9/projects/' + gate.PROJECT, 'GET', min(5, deadline-clock()), env)
        gets += 1
        active = project.get('lastAliasRequest') or {}
        if (project.get('id') != gate.PROJECT or project.get('accountId') != gate.TEAM
                or active.get('type') != 'rollback' or active.get('toDeploymentId') != gate.ROLLBACK):
            raise ValueError('Rollback identity unresolved; no retry')
        if active.get('jobStatus') in ('pending', 'in-progress'):
            pause(min(2, max(0, deadline-clock())))
            continue
        if active.get('jobStatus') != 'succeeded':
            raise ValueError('Rollback terminal failure; no retry')
        aliases = {}
        for h in gate.HOSTS:
            remaining = deadline-clock()
            if remaining <= 0:
                raise ValueError('Rollback resolution deadline exceeded')
            aliases[h] = request('/v4/aliases/' + h, 'GET', min(5, remaining), env)
            gets += 1
        report = gate.rollback_disposition(project, aliases, target, gate.RETAINED_READY)
        if report['rollback_post_allowed'] or clock() >= deadline:
            raise ValueError('Rollback restoration unverified; no retry')
        return dict(report, resolution_gets=gets)
    raise ValueError('Rollback resolution cap exhausted; no retry')


def focused_smoke(started, output, opener=None):
    """Fresh promotion window is explicit; original READY is never relabelled."""
    now = dt.datetime.now(dt.timezone.utc)
    age = (now-started).total_seconds()
    if started.tzinfo is None or not 0 <= age < 900:
        raise ValueError('Promotion acceptance window expired')
    deadline = time.monotonic() + 900-age
    evidence = {'deployment': gate.RETAINED_READY, 'original_ready': 1792521693385,
                'promotion_window_started_at': started.isoformat(), 'requests': 0,
                'probes': [], 'result': 'FAIL', 'contract': smoke.PROPOSED_CONTRACT}
    path = Path(output)
    with path.open('x') as handle:
        json.dump({'state': 'STARTED_NO_RETRY'}, handle)
    try:
        opener = smoke.build_opener(smoke.NoRedirect()) if opener is None else opener
        for url in smoke.SMOKE_URLS:
            with smoke.wall_deadline(min(15, deadline-time.monotonic())):
                smoke.probe(url, deadline, opener, evidence, contract=smoke.PROPOSED_CONTRACT, focused=True)
        evidence['result'] = 'PASS_PROPOSED_CONTRACT'
    except Exception:
        evidence['error'] = 'Focused smoke failed; no repeated probes'
    finally:
        path.write_text(json.dumps(evidence, indent=2) + '\n')
    return evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    env = os.environ
    report = {'status': 'FAIL', 'deployment_id': gate.RETAINED_READY}
    output = Path(args.output)
    with output.open('x') as handle:
        json.dump({'state': 'STARTED_NO_RETRY'}, handle)
    try:
        if (env.get('GITHUB_REPOSITORY') != 'ronik18/earnalism-digital-library'
                or env.get('GITHUB_REF') != 'refs/heads/main'
                or env.get('GITHUB_EVENT_NAME') != 'workflow_dispatch'
                or env.get('PROMOTION_ONLY') != 'true'
                or env.get('CONFIRM_PRODUCTION') != 'PROMOTE_EXISTING_READY'):
            raise ValueError('Protected promotion mode unavailable')
        metadata = gate.provider_request('/v13/deployments/' + gate.RETAINED_READY, 'GET', 5, env)
        started = dt.datetime.now(dt.timezone.utc)
        promotion = gate.conditional_promotion(metadata, environ=env, existing_ready=True)
        report.update(promotion={k: v for k, v in promotion.items() if k != 'aliases'},
                      original_ready=metadata['ready'], promotion_window_started_at=started.isoformat())
        result = focused_smoke(started, Path(env['RUNNER_TEMP']) / 'reader-existing-smoke.json')
        report['smoke'] = {'result': result['result'], 'requests': result['requests']}
        if result['result'] != 'PASS_PROPOSED_CONTRACT':
            report['recovery'] = recovery(env)
            return 1
        report['status'] = 'PASS'
        return 0
    except Exception:
        report['reason'] = 'Exact promotion/smoke/recovery unverified; preserve evidence, no retry'
        return 1
    finally:
        output.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
