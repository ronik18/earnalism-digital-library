// Prepare only the pinned local rendering software and its supported browser.
// A successful receipt does not qualify a render, soundtrack, or publication.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {loadRenderLibraries} from './render-runtime.mjs';

const schema = 'earnalism.render_runtime.v1';
const status = 'LOCAL_RENDER_PACKAGES_BROWSER_READY_NOT_RENDER_QUALIFIED';
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');

export function runtimeIdentity(base, runtime) {
  const result = {runtime_root: runtime};
  for (const [name, key] of [['package.json', 'package_json_sha256'], ['package-lock.json', 'package_lock_sha256']]) {
    const source = fs.readFileSync(path.join(base, name));
    const installed = fs.readFileSync(path.join(runtime, name));
    if (!source.equals(installed)) throw Error('Render runtime must retain the exact source ' + name);
    result[key] = sha256(source);
  }
  return result;
}

export function browserIdentity(browserPath, type) {
  if (typeof browserPath !== 'string' || !path.isAbsolute(browserPath)) throw Error('Rendering browser must be an absolute executable path');
  if (typeof type !== 'string' || !type) throw Error('Rendering browser type is missing');
  fs.accessSync(browserPath, fs.constants.X_OK);
  const stat = fs.statSync(browserPath);
  if (!stat.isFile() || stat.size === 0) throw Error('Rendering browser executable is missing or empty');
  return {path: browserPath, bytes: stat.size, sha256: sha256(fs.readFileSync(browserPath)), type};
}

function parseArguments(args) {
  const options = {};
  for (let index = 0; index < args.length; index++) {
    const key = args[index];
    if (key === '--verify-only') {
      if (options.verifyOnly) throw Error('Repeated --verify-only');
      options.verifyOnly = true;
    } else {
      if (!['--base', '--runtime', '--result'].includes(key) || options[key] !== undefined) throw Error('Unknown or repeated render-runtime argument');
      const value = args[++index];
      if (!value || !path.isAbsolute(value)) throw Error(key + ' requires an absolute path');
      options[key] = path.resolve(value);
    }
  }
  for (const key of ['--base', '--runtime', '--result']) if (!options[key]) throw Error('Missing ' + key);
  return options;
}

export async function main(args = process.argv.slice(2)) {
  const options = parseArguments(args);
  const base = options['--base'], runtime = options['--runtime'], resultPath = options['--result'];
  if (process.env.EARNALISM_REMOTION_RUNTIME && path.resolve(process.env.EARNALISM_REMOTION_RUNTIME) !== runtime) throw Error('Rendering runtime argument and environment differ');
  process.env.EARNALISM_REMOTION_RUNTIME = runtime;
  if (!options.verifyOnly && fs.existsSync(resultPath)) throw Error('Existing render-runtime receipt preserved; verify it instead');
  const identity = runtimeIdentity(base, runtime);
  const libraries = await loadRenderLibraries(base);
  if (libraries.runtimeRoot !== runtime) throw Error('Loaded rendering runtime differs from the selected runtime');
  if (options.verifyOnly) {
    const receipt = JSON.parse(fs.readFileSync(resultPath, 'utf8'));
    if (receipt.schema !== schema || receipt.status !== status) throw Error('Unqualified render-runtime receipt');
    for (const [key, value] of Object.entries(identity)) if (receipt[key] !== value) throw Error('Render-runtime receipt binding changed: ' + key);
    if (JSON.stringify(receipt.versions) !== JSON.stringify(libraries.versions)) throw Error('Render-runtime receipt package versions changed');
    const browser = browserIdentity(receipt.browser?.path, receipt.browser?.type);
    for (const [key, value] of Object.entries(browser)) if (receipt.browser[key] !== value) throw Error('Render-runtime receipt browser changed: ' + key);
    if (process.env.EARNALISM_RENDER_BROWSER && process.env.EARNALISM_RENDER_BROWSER !== browser.path) throw Error('Rendering browser override differs from cached receipt');
    console.log(JSON.stringify({schema, status, verified: true, runtime_root: runtime, browser}));
    return;
  }
  const explicitBrowser = process.env.EARNALISM_RENDER_BROWSER;
  if (explicitBrowser) browserIdentity(explicitBrowser, 'explicit');
  if (typeof libraries.ensureBrowser !== 'function') throw Error('Pinned renderer does not expose ensureBrowser');
  // Remotion downloads its default supported Chrome Headless Shell revision.
  // Running from this owned runtime keeps its default download/cache private.
  const priorDirectory = process.cwd();
  let selected;
  try {
    process.chdir(runtime);
    selected = await libraries.ensureBrowser({chromeMode: 'headless-shell', ...(explicitBrowser ? {browserExecutable: explicitBrowser} : {})});
  } finally {
    process.chdir(priorDirectory);
  }
  const browser = browserIdentity(selected?.path, selected?.type);
  if (explicitBrowser && browser.path !== explicitBrowser) throw Error('Renderer did not retain the explicitly selected browser');
  // Bind the manifests again after a potentially long browser setup.
  if (JSON.stringify(runtimeIdentity(base, runtime)) !== JSON.stringify(identity)) throw Error('Render-runtime manifests changed during preparation');
  const receipt = {schema, status, ...identity, versions: libraries.versions, browser};
  // Exclusive publication: a partial or failed prior result is never replaced.
  const descriptor = fs.openSync(resultPath, 'wx', 0o600);
  try {
    fs.writeFileSync(descriptor, JSON.stringify(receipt, null, 2) + '\n');
    fs.fsyncSync(descriptor);
  } finally {
    fs.closeSync(descriptor);
  }
  console.log(JSON.stringify({schema, status, result: resultPath, browser}));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => {
    console.error('Render-runtime preparation failed: ' + error.message);
    process.exitCode = 1;
  });
}
