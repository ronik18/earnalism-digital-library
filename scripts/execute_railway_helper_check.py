"""Ordinary CI test runner for a locally built, network-free archive helper.

No provider/auth/deployment code. A successful receipt is helper execution only.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from verify_railway_helper_archive import need, preflight, git_modes, verify_archive
from verify_railway_helper_source import check as source_check


def execute(a):
    need(os.environ.get('GITHUB_ACTIONS') == 'true', 'reviewed ordinary hosted CI required')
    need(os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch', 'manual provider dispatch not admitted')
    context = {key: os.environ.get(key) for key in ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_SHA', 'GITHUB_JOB', 'GITHUB_REPOSITORY', 'GITHUB_EVENT_NAME')}
    need(all(context.values()), 'complete actual CI context required')
    need(context['GITHUB_REPOSITORY'] == 'ronik18/earnalism-digital-library', 'wrong CI repository')
    toolchain = {}
    for tool in ('rustc', 'cargo'):
        r = subprocess.run([tool, '--version'], capture_output=True, text=True, check=True, timeout=15)
        toolchain[tool] = r.stdout.strip()
    match = re.match(r'rustc (\d+)\.(\d+)\.(\d+)', toolchain['rustc'])
    need(match and tuple(map(int, match.groups())) >= (1,85,0), 'actual Rust >=1.85 required')
    package = Path(a.package_root).resolve(strict=True)
    admitted_source = source_check(package)
    root = preflight(Path(a.export_root))
    controller = Path(a.controller_root).resolve(strict=True)
    raw_report = Path(a.report).read_bytes()
    need(hashlib.sha256(raw_report).hexdigest() == a.expected_report_sha256, 'exact report hash differs')
    report = json.loads(raw_report)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=controller, text=True).strip()
    need(head == report['controller_source'], 'source/head context differs')
    # Pull-request GITHUB_SHA may name a synthetic merge; outer CI admits the actual checkout.
    context['actual_controller_sha'] = head
    binary = Path(a.binary).resolve(strict=True)
    need(binary.is_file() and not Path(a.binary).is_symlink(), 'regular compiled helper required')
    output = Path(a.output_dir)
    need(not output.exists(), 'fresh artifact directory required')
    output.mkdir(mode=0o700, parents=True)
    archive = output / 'actual-helper-archive.tgz'
    binary_hash = hashlib.sha256(binary.read_bytes()).hexdigest()
    command = [str(binary), str(root/'backend'), str(root), str(archive)]
    env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'GIT_CONFIG_NOSYSTEM': '1',
           'GIT_CONFIG_GLOBAL': '/dev/null', 'XDG_CONFIG_HOME': str(output/'empty-config')}
    subprocess.run(command, check=True, timeout=180, cwd=root, env=env)
    need(hashlib.sha256(binary.read_bytes()).hexdigest() == binary_hash, 'helper binary changed')
    result = verify_archive(archive, report, root, git_modes(controller, report['source']))
    result.update({'schema':'earnalism.executed_upstream_helper_archive.v1',
                   'scope':'EXACT_UPSTREAM_HELPER_EXECUTED_NOT_INSTALLED_CLI_UPLOAD_OR_NATIVE_RUNTIME',
                   'helper_executed':True, 'observed_at':datetime.now(timezone.utc).isoformat(),
                   'ci_context':context,'actual_toolchain':toolchain,'helper_binary_sha256':binary_hash,
                   'harness_source_sha256':hashlib.sha256((package/'src/main.rs').read_bytes()).hexdigest(),
                   'derived_lock_sha256':hashlib.sha256((package/'Cargo.lock').read_bytes()).hexdigest(),
                   'source_pins_sha256':hashlib.sha256((package/'SOURCE-PINS.json').read_bytes()).hexdigest(),
                   'upstream_function_sha256':admitted_source['function_sha256'],
                   'upstream_module_sha256':admitted_source['upstream_module_sha256'],
                   'upstream_lock_sha256':json.loads((package/'SOURCE-PINS.json').read_bytes())['upstream_lock_sha256'],
                   'offline_export_report_sha256':hashlib.sha256(raw_report).hexdigest(),
                   'archive_command':command,'provider_git_sha':None,'provider_writes':0})
    with (output/'executed-helper-report.json').open('x') as f:
        json.dump(result,f,indent=2);f.write('\n')
    report_path = output/'executed-helper-report.json'
    digests = {'schema':'earnalism.helper-receipt-digests.v1',
               'expected_archive_helper_report_sha256':hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',', ':')).encode()).hexdigest(),
               'raw_report_file_sha256':hashlib.sha256(report_path.read_bytes()).hexdigest(),
               'archive_member_manifest_sha256':result['archive_member_manifest_sha256'],
               'archive_member_modes_sha256':result['archive_member_modes_sha256'],
               'helper_archive_sha256':result['archive_sha256']}
    with (output/'executed-helper-report-digests.json').open('x') as f:
        json.dump(digests,f,indent=2);f.write('\n')
    return report_path


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    for name in ('package-root','binary','report','expected-report-sha256','export-root','controller-root','output-dir'):
        p.add_argument('--'+name,required=True)
    print(execute(p.parse_args()))
