import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { chmod, mkdtemp, mkdir, readFile, realpath, writeFile, symlink } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { selectSourceFiles, validateSelectedFiles } from './select_vercel_source_files.mjs';

async function fixture() {
  const root = await realpath(await mkdtemp(path.join(os.tmpdir(), 'packaging-selector-')));
  await mkdir(path.join(root, 'frontend/api'), { recursive: true });
  await writeFile(path.join(root, 'frontend/vercel.json'), JSON.stringify({ framework: 'create-react-app' }));
  const file = path.join(root, 'asset.txt');
  await writeFile(file, 'selected bytes');
  const bytes = await readFile(file);
  return { root, file, manifest: { basePath: root, files: [{ path: 'asset.txt', size: bytes.length,
    mode: 33188, sha: createHash('sha1').update(bytes).digest('hex') }] } };
}

test('real selected bytes pass; changed or missing bytes fail', async () => {
  const { root, file, manifest } = await fixture();
  assert.equal(await validateSelectedFiles(root, manifest), manifest);
  await writeFile(file, 'tampered');
  await assert.rejects(validateSelectedFiles(root, manifest), /bytes changed/);
  manifest.files[0].path = 'missing';
  await assert.rejects(validateSelectedFiles(root, manifest), /ENOENT/);
});

test('wrong/empty root, duplicate files and external paths fail', async () => {
  const { root, manifest } = await fixture();
  await assert.rejects(validateSelectedFiles(root, { ...manifest, basePath: '/wrong' }), /root/);
  await assert.rejects(validateSelectedFiles(root, { ...manifest, files: [] }), /root/);
  await assert.rejects(validateSelectedFiles(root, { ...manifest, files: [...manifest.files, ...manifest.files] }), /Duplicate/);
  const outside = await mkdtemp(path.join(os.tmpdir(), 'packaging-outside-'));
  await writeFile(path.join(outside, 'outside.txt'), 'external');
  await symlink(path.join(outside, 'outside.txt'), path.join(root, 'link'));
  await assert.rejects(validateSelectedFiles(root, { ...manifest, files: [{ path: 'link' }] }), /External/);
  await assert.rejects(validateSelectedFiles(root, { ...manifest, files: [{ path: path.join(outside, 'outside.txt') }] }), /External/);
});

test('environment file never becomes a selected artifact', async () => {
  const { root, manifest } = await fixture();
  await writeFile(path.join(root, '.env.production.local'), 'fixture');
  await assert.rejects(validateSelectedFiles(root, { ...manifest, files: [{ path: '.env.production.local' }] }), /Environment/);
});

test('directory placeholder cannot select the checkout parent', async () => {
  const { root } = await fixture();
  const manifest = { basePath: root, files: [{ path: '..', mode: 0o040755, size: 0 }] };
  await assert.rejects(validateSelectedFiles(root, manifest), /External/);
});

test('directory placeholder symlink cannot resolve to the checkout parent', async () => {
  const { root } = await fixture();
  await symlink(path.dirname(root), path.join(root, 'parent-link'));
  const manifest = { basePath: root, files: [{ path: 'parent-link', mode: 0o040755, size: 0 }] };
  await assert.rejects(validateSelectedFiles(root, manifest), /External/);
});

test('exact SDK directory placeholders retain strict mode/size/digest semantics', async () => {
  const { root } = await fixture();
  await mkdir(path.join(root, 'empty'));
  const directory = { path: 'empty', mode: 0o040755, size: 0 };
  const manifest = { basePath: root, files: [directory] };
  assert.equal(await validateSelectedFiles(root, manifest), manifest);
  for (const change of [{ size: 1 }, { sha: 'invented' }, { mode: 0o100644 }]) {
    await assert.rejects(validateSelectedFiles(root, { ...manifest, files: [{ ...directory, ...change }] }), /Invalid/);
  }
});

test('wrong checkout root/config and selector/package tampering fail before import', async () => {
  const { root } = await fixture();
  await assert.rejects(selectSourceFiles(path.join(root, 'frontend'), root), /ENOENT/);
  await writeFile(path.join(root, 'frontend/vercel.json'), JSON.stringify({ framework: 'other' }));
  await assert.rejects(selectSourceFiles(root, root), /Unreviewed/);
  await writeFile(path.join(root, 'frontend/vercel.json'), JSON.stringify({ framework: 'create-react-app', bulkRedirectsPath: 'other' }));
  await assert.rejects(selectSourceFiles(root, root), /Unreviewed/);
  await writeFile(path.join(root, 'frontend/vercel.json'), JSON.stringify({ framework: 'create-react-app' }));
  await mkdir(path.join(root, 'dist/chunks'), { recursive: true });
  await writeFile(path.join(root, 'package.json'), JSON.stringify({ name: 'vercel', version: '62.1.0' }));
  await writeFile(path.join(root, 'dist/chunks/chunk-Z6TGFLIO.js'), 'throw new Error("must never execute")');
  await assert.rejects(selectSourceFiles(root, root), /identity mismatch/);
  await writeFile(path.join(root, 'package.json'), JSON.stringify({ name: 'other', version: '62.1.0' }));
  await assert.rejects(selectSourceFiles(root, root), /identity mismatch/);
});

test('existing workflow retains check/negative suite while removing linkage and CLI credentials', async () => {
  const source = await readFile(new URL('../.github/workflows/vercel-packaging.yml', import.meta.url), 'utf8');
  for (const forbidden of ['secrets.', 'VERCEL_TOKEN', 'VERCEL_ORG_ID', 'VERCEL_PROJECT_ID', 'vercel deploy', '.vercel/project.json', 'environment:']) {
    assert.ok(!source.includes(forbidden), forbidden);
  }
  for (const required of ['pull_request:', 'branches: [main]', "'.github/workflows/regression.yml'",
    'scripts.test_verify_vercel_packaging', 'scripts/verify_vercel_packaging.py --manifest',
    'node --test scripts/test_select_vercel_source_files.mjs', 'persist-credentials: false',
    'env -i PATH=', 'bash --noprofile --norc', '--ignore-scripts', '--package-lock=false vercel@62.1.0',
    'NPM_CONFIG_REGISTRY=https://registry.npmjs.org', 'REACT_APP_BACKEND_URL= REACT_APP_API_URL= SEO_API_BASE_URL=']) {
    assert.ok(source.includes(required), required);
  }
  const helper = await readFile(new URL('./select_vercel_source_files.mjs', import.meta.url), 'utf8');
  assert.ok(!helper.includes('createDeployment'));
  assert.ok(!helper.includes('dist/vc.js'));
  assert.ok(helper.includes("prebuilt: false, projectName: 'earnalism', rootDirectory: 'frontend'"));
});

test('actual workflow shell strips injected credentials/proxies for every build/tool subprocess', async () => {
  const root = await realpath(await mkdtemp(path.join(os.tmpdir(), 'packaging-env-')));
  const bin = path.join(root, 'bin');
  await mkdir(bin);
  // Stub programs inspect only named test sentinels; no install/build/provider runs.
  const stub = `#!/bin/bash
set -euo pipefail
for key in VERCEL_TOKEN VERCEL_ORG_ID VERCEL_PROJECT_ID GITHUB_TOKEN NPM_TOKEN NODE_OPTIONS SENTRY_DSN HTTP_PROXY HTTPS_PROXY ALL_PROXY; do
  if printenv "$key" >/dev/null; then exit 91; fi
done
[[ "$HOME" == '${root}'/source-packaging.*/home ]] || exit 92
[[ ! -s "$NPM_CONFIG_USERCONFIG" && ! -s "$NPM_CONFIG_GLOBALCONFIG" ]] || exit 93
[[ "$NPM_CONFIG_REGISTRY" == https://registry.npmjs.org ]] || exit 94
[[ -z "$REACT_APP_BACKEND_URL" && -z "$REACT_APP_API_URL" && -z "$SEO_API_BASE_URL" ]] || exit 95
printf '%s\\n' "$(basename "$0")" >> '${root}/calls.log'
[[ "$(basename "$0")" != node ]] || printf '{"files":[]}\\n'
`;
  for (const name of ['npm', 'node', 'python3']) {
    const file = path.join(bin, name);
    await writeFile(file, stub);
    await chmod(file, 0o700);
  }
  const source = await readFile(new URL('../.github/workflows/vercel-packaging.yml', import.meta.url), 'utf8');
  const block = source.split('      - name: Build and inspect source files without provider credentials\n')[1]
    .split('      - uses: actions/upload-artifact')[0].split('        run: |\n')[1];
  const shell = block.split('\n').map(line => line.startsWith('          ') ? line.slice(10) : line).join('\n')
    .replaceAll('/tmp/vercel-source-manifest.json', `${root}/manifest.json`)
    .replaceAll('/tmp/vercel-source-packaging.json', `${root}/report.json`);
  const env = { PATH: `${bin}:${process.env.PATH}`, HOME: root, RUNNER_TEMP: root,
    GITHUB_WORKSPACE: root, VERCEL_TOKEN: 'test-sentinel', VERCEL_ORG_ID: 'test-sentinel',
    VERCEL_PROJECT_ID: 'test-sentinel', GITHUB_TOKEN: 'test-sentinel', NPM_TOKEN: 'test-sentinel',
    HTTP_PROXY: 'test-sentinel', HTTPS_PROXY: 'test-sentinel', ALL_PROXY: 'test-sentinel',
    NODE_OPTIONS: 'test-sentinel', SENTRY_DSN: 'test-sentinel',
    REACT_APP_BACKEND_URL: 'test-sentinel', REACT_APP_API_URL: 'test-sentinel', SEO_API_BASE_URL: 'test-sentinel' };
  const result = spawnSync('/bin/bash', ['-c', shell], { env, encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual((await readFile(path.join(root, 'calls.log'), 'utf8')).trim().split('\n'),
    ['npm', 'npm', 'npm', 'node', 'python3']);
});
