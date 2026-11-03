#!/usr/bin/env node
// Synthetic readiness contracts only: no browser/server/network or visual PASS.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
const file = process.env.CAPTURE_REVIEW_SOURCE || path.resolve('scripts/capture_exact_primary_owner_review.mjs');
const source = fs.readFileSync(file, 'utf8');
const start = source.indexOf('export async function waitForReaderCaptureReady(');
const end = source.indexOf('\nasync function capture(', start);
assert.ok(start >= 0 && end > start);
let cases = 0;
async function check({ delay = 0, ready = 'true', count = '2', alert = false, copies = 1, family = 'reader', fails = false, required = true } = {}) {
  let poll = 0; let calls = 0;
  const node = { getAttribute: (key) => key === 'data-pagination-ready' ? (poll > delay ? ready : 'false') : key === 'data-page-count' ? count : '400',
    getBoundingClientRect: () => ({ width: 390, height: 600 }), querySelector: () => alert ? {} : null };
  const document = { querySelectorAll: () => Array(copies).fill(node), querySelector: () => node };
  const fn = vm.runInNewContext(source.slice(start, end).replace('export ', '') + '\nwaitForReaderCaptureReady;', { document });
  const page = { async waitForFunction(predicate, _, options) {
    calls++; assert.equal(options.timeout, 25);
    for (poll = 1; poll <= 5; poll++) { if (predicate()) return; await Promise.resolve(); }
    throw new Error('synthetic readiness timeout');
  }, async evaluate(predicate) { return predicate(); } };
  if (fails) await assert.rejects(fn(page, family, { timeout: 25, required }), /timeout/);
  else { const result = await fn(page, family, { timeout: 25, required }); if (family === 'reader' && required) assert.equal(result.ready, 'true'); else if (family === 'reader') { assert.equal(result.ready, null); assert.equal(result.scope, 'HISTORICAL_REFERENCE_NOT_CURRENT_READINESS_PROOF'); assert.equal(result.required, false); } else assert.equal(result, null); }
  assert.equal(calls, family === 'reader' && required ? 1 : 0); cases++;
}
await check({ delay: 3 });
await check({ ready: 'false', fails: true });
await check({ count: '0', fails: true });
await check({ count: 'NaN', fails: true });
await check({ alert: true, fails: true });
await check({ copies: 0, fails: true });
await check({ copies: 2, fails: true });
await check({ family: 'listener' });
await check({ family: 'reader', copies: 0, required: false });
assert.ok(source.includes('waitForReaderCaptureReady(page, state.family, { required: strict })'));
assert.ok(source.includes('stable: sha(first) === sha(second)'));
assert.ok(source.includes('`${state.id}-first.png`') && source.includes('`${state.id}-second.png`'));
assert.ok(source.includes('readiness-failure.json') && source.includes('capture-failure.json'));
console.log(`${cases} synthetic readiness cases PASS; strict two-frame equality and failure evidence retained`);
