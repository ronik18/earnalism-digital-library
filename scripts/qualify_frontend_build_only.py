"""Credential-free local Linux build proof. No deployment or release operations."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

from scripts.verify_isolated_seo_build import exact_clean_source, prepare, verify
from scripts.capture_prebuilt_bundle import seal, preserve_failure

FRONTEND_SHA = '229df7f8b2cfb49a7f46215be3979608c39f7c33'
SELECTOR_SHA256 = 'ee658256471efee8112a31cb9ec884ad9933dc33cca8941cbda3b7df7710e7c6'
ROOT = Path(__file__).resolve().parents[1]


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def private_environment(directory):
    """Only these non-secret values reach npm, build scripts and file selectors."""
    return {
        'PATH': os.environ['PATH'], 'HOME': str(directory / 'home'),
        'XDG_CONFIG_HOME': str(directory / 'home/.config'),
        'XDG_DATA_HOME': str(directory / 'home/.local/share'),
        'TMPDIR': str(directory / 'tmp'), 'CI': 'true',
        'NPM_CONFIG_CACHE': str(directory / 'npm-cache'),
        'NPM_CONFIG_USERCONFIG': str(directory / 'empty-user.npmrc'),
        'NPM_CONFIG_GLOBALCONFIG': str(directory / 'empty-global.npmrc'),
        'VERCEL_TELEMETRY_DISABLED': '1', 'DO_NOT_TRACK': '1',
        'REACT_APP_BACKEND_URL': '', 'REACT_APP_API_URL': '', 'SEO_API_BASE_URL': '',
    }


def selected_inventory(root, manifest):
    root = root.resolve()
    rows = []
    for entry in manifest['files']:
        path = root / entry['path']
        if not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError('Missing or external selected file: ' + entry['path'])
        if path.name.startswith('.env') and path.name != '.env.example':
            raise ValueError('Environment file selected; refuse artifact proof')
        data = path.read_bytes()
        if hashlib.sha1(data).hexdigest() != entry['sha']:
            raise ValueError('Selected file changed: ' + entry['path'])
        rows.append({'path': entry['path'], 'size': len(data), 'mode': entry['mode'],
                     'sha256': hashlib.sha256(data).hexdigest()})
    rows.sort(key=lambda row: row['path'])
    encoded = json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()
    return {'files': rows, 'canonical_manifest_sha256': hashlib.sha256(encoded).hexdigest()}


def dependency_inventory(root):
    approved = json.loads(subprocess.check_output(
        ['git', '-C', str(root), 'show', FRONTEND_SHA + ':frontend/package-lock.json']))['packages']
    installed = json.loads((root / 'frontend/node_modules/.package-lock.json').read_text())['packages']
    fields = ('version', 'resolved', 'integrity')
    actual = {key: {field: value.get(field) for field in fields}
              for key, value in installed.items()}
    expected = {key: {field: value.get(field) for field in fields}
                for key, value in approved.items() if key}
    changed = [{'path': key, 'F': expected[key], 'installed': actual[key]}
               for key in sorted(set(expected) & set(actual)) if expected[key] != actual[key]]
    missing = [{'path': key, 'F_platform_metadata': {field: approved[key].get(field)
                for field in ('os', 'cpu', 'optional')}} for key in sorted(set(expected) - set(actual))]
    added = [{'path': key, 'installed': actual[key]} for key in sorted(set(actual) - set(expected))]
    return {'platform': {'system': platform.system(), 'machine': platform.machine()},
            'installed': actual, 'changed_locked_entries': changed,
            'missing_locked_entries': missing, 'unlocked_build_entries': added,
            'review_status': 'PENDING_INDEPENDENT_EXACT_LINUX_RESOLUTION_REVIEW',
            'limit': 'No platform difference or auto-added package is silently exempted or approved by this build-only job.'}


def main(controller, directory, public_profile=False):
    if not re.fullmatch(r'[0-9a-f]{40}', controller):
        raise ValueError('Controller must be a full immutable SHA')
    exact_clean_source(ROOT, controller)
    directory = directory.resolve()
    if directory.exists() or directory.is_relative_to(ROOT) or ROOT.is_relative_to(directory):
        raise ValueError('Qualification directory must be fresh and outside controller source')
    directory.mkdir(mode=0o700)
    reports = directory / 'reports'
    reports.mkdir()
    for folder in ('home', 'tmp'):
        (directory / folder).mkdir()
    for name in ('empty-user.npmrc', 'empty-global.npmrc'):
        (directory / name).write_text('')
    env = private_environment(directory)
    if public_profile:
        from scripts.frontend_public_build import PUBLIC_REFERENCE, public_inputs
        projection = json.loads(PUBLIC_REFERENCE.read_text())
        context_inputs = {'controller_sha': controller, 'frontend_sha': FRONTEND_SHA, 'public_build_inputs': {
            'all_values_public': True, 'operator': 'Automated PR technical qualification; no release authority',
            'env': projection, 'excluded_client_inputs': ['REACT_APP_API_URL']}}
        public_inputs(context_inputs, controller)
        env.pop('REACT_APP_API_URL', None)
        env.pop('SEO_API_BASE_URL', None)
        env.update(projection)

    def run(command, name, cwd=ROOT, child_env=None, timeout=900):
        result = subprocess.run(command, cwd=cwd, env=child_env or env,
                                capture_output=True, text=True, timeout=timeout)
        (reports / (name + '.log')).write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(name + ' failed; see non-secret command log')
        return result.stdout

    try:
        if os.environ.get('GITHUB_RUN_ATTEMPT') != '1':
            raise ValueError('Only first capture attempt is authorized')
        run(['git', 'merge-base', '--is-ancestor', '146605fd0dee1b83f73137c2448c83de9622f073', controller], 'T-ancestor')
        node = run(['node', '--version'], 'node-version').strip()
        npm = run(['npm', '--version'], 'npm-version').strip()
        if (node, npm) != ('v20.20.2', '10.8.2'):
            raise ValueError('Reviewed Node/npm runtime mismatch')
        run(['git', 'merge-base', '--is-ancestor', FRONTEND_SHA, controller], 'F-ancestor')
        artifact = directory / 'artifact-F'
        run(['git', 'worktree', 'add', '--detach', str(artifact), FRONTEND_SHA], 'exact-F-worktree')
        exact_clean_source(artifact, FRONTEND_SHA)
        settings = {'projectId': 'prj_kxPN55TOJ23lDgoXIXrvqHtzy607',
                    'orgId': 'team_HAGNRSEiW5MZXY2AhV0cQvE0', 'settings': {
                        'framework': 'create-react-app', 'rootDirectory': 'frontend',
                        'installCommand': 'npm install --legacy-peer-deps',
                        'buildCommand': 'npm run build', 'outputDirectory': 'build', 'nodeVersion': '24.x'}}
        for path in (artifact / '.vercel', artifact / 'frontend/.vercel'):
            path.mkdir()
            (path / '.env.production.local').write_text('')
        write(artifact / '.vercel/project.json', settings)
        write(reports / 'static-project-settings.json', settings)
        tooling = directory / 'tooling'
        # Private tool installation only: the application lock is never disabled.
        run(['npm', 'install', '--prefix', str(tooling), '--ignore-scripts', '--no-audit',
             '--no-fund', '--package-lock=false', 'vercel@63.1.2'], 'pinned-CLI-install')
        cli = tooling / 'node_modules/vercel'
        selector = cli / 'dist/chunks/chunk-GNY6U33Z.js'
        if json.loads((cli / 'package.json').read_text())['version'] != '63.1.2' or hashlib.sha256(selector.read_bytes()).hexdigest() != SELECTOR_SHA256:
            raise ValueError('Pinned CLI/selector identity mismatch')
        generated = directory / 'generated-seo'
        prepare(artifact, generated, FRONTEND_SHA)
        build_env = {**env, 'NPM_CONFIG_SAVE': 'false', 'SEO_ASSETS_OUTPUT_DIR': str(generated)}
        run(['node', str(cli / 'dist/vc.js'), 'build', '--prod', '--yes'],
            'local-build-only', cwd=artifact, child_env=build_env)
        write(reports / 'seo-attestation.json', verify(artifact, generated, FRONTEND_SHA))
        inspector = directory / 'inspect-files.mjs'
        inspector.write_text(
            'import {require_dist} from ' + json.dumps(selector.as_uri()) + ';\n'
            'const prebuilt=process.argv[3]==="prebuilt";\n'
            'const result=await require_dist().inspectDeploymentFiles({path:process.argv[2],prebuilt,'
            'vercelOutputDir:prebuilt?process.argv[2]+"/.vercel/output":undefined,'
            'projectName:"earnalism",rootDirectory:"frontend"});\n'
            'process.stdout.write(JSON.stringify(result,null,2)+"\\n");\n')
        for mode in ('source', 'prebuilt'):
            text = run(['node', str(inspector), str(artifact), mode], mode + '-file-selector')
            manifest = reports / (mode + '-manifest.json')
            manifest.write_text(text)
            command = [sys.executable, str(ROOT / 'scripts/verify_vercel_packaging.py'),
                       '--root', str(artifact), '--manifest', str(manifest),
                       '--output', str(reports / (mode + '-packaging.json'))]
            if mode == 'prebuilt':
                command += ['--prebuilt', '--compare', str(reports / 'source-packaging.json')]
            run(command, mode + '-packaging-verifier')
        prebuilt = json.loads((reports / 'prebuilt-manifest.json').read_text())
        write(reports / 'complete-output-inventory.json', selected_inventory(artifact, prebuilt))
        write(reports / 'installed-dependency-inventory.json', dependency_inventory(artifact))
        if public_profile:
            from scripts.verify_build_dependency_identity import verify as check_dependencies, runtime_identity, REFERENCE
            from scripts.frontend_public_build import digest, output_identity
            write(reports / 'public-input-binding.json', {'profile': projection, 'sha256': digest(projection), 'controller': controller, 'frontend': FRONTEND_SHA, 'output': output_identity(artifact)})
            write(reports / 'dependency-identity-gate.json', check_dependencies(artifact, json.loads(REFERENCE.read_text()), runtime_identity(cli_path=str(cli / 'dist/vc.js'))))
        exact_clean_source(artifact, FRONTEND_SHA)
        exact_clean_source(ROOT, controller)
        write(reports / 'RESULT.json', {'status': 'PASS_BUILD_PACKAGING_ONLY_NOT_RELEASE_AUTHORIZATION',
              'controller': controller, 'frontend': FRONTEND_SHA, 'node': node, 'npm': npm,
              'production_credentials': False, 'provider_mutations': 0,
              'dependency_review': 'Actual Linux inventory still requires independent review; no blanket platform exemption.'})
        context = {'approved_base_T': '146605fd0dee1b83f73137c2448c83de9622f073',
                   'controller_U': controller, 'frontend_F': FRONTEND_SHA,
                   'frontend_tree': run(['git', 'rev-parse', FRONTEND_SHA + '^{tree}'], 'F-tree').strip(),
                   'run_id': os.environ.get('GITHUB_RUN_ID'), 'attempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
                   'node': node, 'npm': npm, 'vercel': '63.1.2', 'selector_sha256': SELECTOR_SHA256,
                   'build_command': ['node', 'vercel/dist/vc.js', 'build', '--prod', '--yes'],
                   'project_settings': settings, 'build_semantics': 'REVIEWED_PUBLIC_PROJECTION' if public_profile else 'UNCHANGED_T_EMPTY_APP_ENV_STATIC_SETTINGS',
                   'production_applicability': 'NOT_ESTABLISHED', 'independent_content_review': 'PENDING'}
        write(reports / 'capture-context.json', context)
        seal(artifact, reports, prebuilt, context, directory / 'upload')
    except Exception as error:
        write(reports / 'RESULT.json', {'status': 'FAIL_CLOSED', 'error_class': type(error).__name__,
              'production_credentials': False, 'provider_mutations': 0})
        upload = directory / 'upload'
        upload.mkdir(exist_ok=True)
        try:
            preserve_failure(reports, upload, type(error).__name__)
        except Exception:
            write(upload / 'CAPTURE-FAILURE.json', {'status': 'HOLD_CAPTURE_INCOMPLETE',
                  'reports_unavailable_or_private_or_oversized': True, 'no_automatic_retry': True})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controller-sha', required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--public-profile', action='store_true', help='New PR technical qualification only; never replay the consumed retention capture')
    args = parser.parse_args()
    main(args.controller_sha, args.output_root, args.public_profile)
