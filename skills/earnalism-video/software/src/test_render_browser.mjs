import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {resolveRenderBrowser, resolveRenderPublic} from './render-browser.mjs';

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'earnalism-browser-test-'));
try {
  const browser = path.join(root, 'installed-browser');
  fs.writeFileSync(browser, '#!/bin/sh\nexit 0\n', {mode: 0o700});
  assert.equal(resolveRenderBrowser({EARNALISM_RENDER_BROWSER: browser}, 'linux'), browser);
  assert.equal(resolveRenderBrowser({EARNALISM_RENDER_BROWSER: browser}, 'darwin'), browser);
  assert.throws(() => resolveRenderBrowser({EARNALISM_RENDER_BROWSER: 'relative-browser'}, 'linux'), /absolute/);
  assert.throws(() => resolveRenderBrowser({EARNALISM_RENDER_BROWSER: path.join(root, 'missing')}, 'linux'));
  assert.equal(resolveRenderPublic(root, {EARNALISM_RENDER_PUBLIC: root}), root);
  assert.throws(() => resolveRenderPublic(root, {EARNALISM_RENDER_PUBLIC: 'relative'}));
  const source = fs.readFileSync(new URL('./render-browser.mjs', import.meta.url), 'utf8');
  assert(!source.includes('disableWebSecurity') && !source.includes('no-sandbox'));
  console.log('Installed Linux/Mac browser selection and fail-closed overrides passed; no browser launched.');
} finally { fs.rmSync(root, {recursive: true, force: true}); }
