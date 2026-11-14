// Source-only lifecycle checks with inert package/browser fixtures.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const helper = fileURLToPath(new URL('./prepare-render-runtime.mjs', import.meta.url));
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'earnalism-runtime-prepare-test-'));
const base = path.join(root, 'source'), runtime = path.join(root, 'runtime');
const result = path.join(root, 'result.json'), marker = path.join(root, 'ensure-calls');
const browser = path.join(root, 'inert-browser');
const dependencies = Object.fromEntries(['remotion', '@remotion/bundler', '@remotion/renderer', 'react', 'react-dom'].map(name => [name, '4.0.539']));
const env = {...process.env, EARNALISM_REMOTION_RUNTIME: runtime, EARNALISM_TEST_BROWSER: browser, EARNALISM_TEST_ENSURE_MARKER: marker};
delete env.EARNALISM_RENDER_BROWSER;
const run = (args = [], overrides = {}) => spawnSync(process.execPath, [helper, '--base', base, '--runtime', runtime, '--result', result, ...args], {encoding: 'utf8', env: {...env, ...overrides}, timeout: 5000});
const passing = response => assert.equal(response.status, 0, response.stderr || response.stdout);
const failing = (response, pattern) => {assert.notEqual(response.status, 0); assert.match(response.stderr, pattern);};
try {
  fs.mkdirSync(base); fs.mkdirSync(runtime);
  for (const folder of [base, runtime]) {
    fs.writeFileSync(path.join(folder, 'package.json'), JSON.stringify({type: 'module', dependencies}));
    fs.writeFileSync(path.join(folder, 'package-lock.json'), '{"lockfileVersion":3}\n');
  }
  for (const [name, version] of Object.entries(dependencies)) {
    const folder = path.join(runtime, 'node_modules', name);
    fs.mkdirSync(folder, {recursive: true});
    const metadata = {name, version};
    if (name === '@remotion/renderer') {
      metadata.type = 'module'; metadata.exports = {'.': {import: './index.mjs'}, './package.json': './package.json'};
      fs.writeFileSync(path.join(folder, 'index.mjs'), `import fs from 'node:fs';
export async function ensureBrowser(options) {
  if (process.env.EARNALISM_VERIFY_MUST_NOT_ENSURE) throw Error('verify-only invoked ensureBrowser');
  if (options.chromeMode !== 'headless-shell') throw Error('wrong browser mode');
  fs.appendFileSync(process.env.EARNALISM_TEST_ENSURE_MARKER, 'called\\n');
  return {type: options.browserExecutable ? 'user-defined-path' : 'fixture-headless-shell', path: options.browserExecutable || process.env.EARNALISM_TEST_BROWSER};
}`);
    }
    if (name === '@remotion/bundler') {
      metadata.main = 'index.cjs';
      fs.writeFileSync(path.join(folder, 'index.cjs'), 'exports.bundle = () => {throw Error("no bundle allowed in setup test")};');
    }
    fs.writeFileSync(path.join(folder, 'package.json'), JSON.stringify(metadata));
  }
  fs.writeFileSync(browser, '#!/bin/sh\nexit 99\n', {mode: 0o700});
  passing(run());
  const receipt = JSON.parse(fs.readFileSync(result, 'utf8'));
  assert.equal(receipt.status, 'LOCAL_RENDER_PACKAGES_BROWSER_READY_NOT_RENDER_QUALIFIED');
  assert.equal(receipt.browser.path, browser);
  assert.equal(receipt.package_lock_sha256.length, 64);
  assert.equal(receipt.browser.sha256.length, 64);
  assert.deepEqual(receipt.versions, dependencies);
  passing(run(['--verify-only'], {EARNALISM_VERIFY_MUST_NOT_ENSURE: '1'}));
  assert.equal(fs.readFileSync(marker, 'utf8'), 'called\n');
  failing(run(), /Existing render-runtime receipt preserved/);
  failing(run(['--unknown']), /Unknown or repeated/);
  failing(run(['--verify-only'], {EARNALISM_REMOTION_RUNTIME: base}), /argument and environment differ/);
  fs.appendFileSync(browser, '# changed\n');
  failing(run(['--verify-only']), /browser changed/);
  fs.writeFileSync(browser, '#!/bin/sh\nexit 99\n');
  fs.chmodSync(browser, 0o600);
  failing(run(['--verify-only']), /EACCES|permission denied/i);
  fs.chmodSync(browser, 0o700);
  fs.appendFileSync(path.join(runtime, 'package-lock.json'), ' ');
  failing(run(['--verify-only']), /exact source package-lock.json/);
  fs.copyFileSync(path.join(base, 'package-lock.json'), path.join(runtime, 'package-lock.json'));
  const packagePath = path.join(runtime, 'node_modules/remotion/package.json');
  fs.writeFileSync(packagePath, JSON.stringify({name: 'remotion', version: '0.0.0'}));
  failing(run(['--verify-only']), /differs from pinned project dependency: remotion/);
  assert.equal(fs.readFileSync(marker, 'utf8'), 'called\n');
  assert.equal(JSON.parse(fs.readFileSync(result, 'utf8')).browser.sha256, receipt.browser.sha256);
  console.log('PASS: pinned preparation, exclusive result, cached browser/package verification; inert fixtures only, no browser launched.');
} finally {
  fs.rmSync(root, {recursive: true, force: true});
}
