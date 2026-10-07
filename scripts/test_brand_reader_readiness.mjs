import assert from 'node:assert/strict';
import fs from 'node:fs';
import { readerCaptureReadiness, waitForSettledReader } from './lib/brand_reader_readiness.mjs';

const initial = { paginationReady: false, loading: true, visibleContentPresent: false };
let domState = initial;
const savedDocument = globalThis.document;
const savedStyle = globalThis.getComputedStyle;
try {
  globalThis.document = { querySelector: selector => selector.includes('visual-viewport') ? { getAttribute: () => String(domState.paginationReady) } : selector.includes('reader-reading-text') ? (domState.visibleContentPresent ? { getBoundingClientRect: () => ({ width: 100, height: 100 }) } : null) : (domState.loading ? {} : null) };
  globalThis.getComputedStyle = () => ({ display: 'block', visibility: 'visible' });
  assert.deepEqual(readerCaptureReadiness(), initial);
  domState = { paginationReady: true, loading: false, visibleContentPresent: true };
  assert.deepEqual(readerCaptureReadiness(), domState);
} finally {
  if (savedDocument === undefined) delete globalThis.document; else globalThis.document = savedDocument;
  if (savedStyle === undefined) delete globalThis.getComputedStyle; else globalThis.getComputedStyle = savedStyle;
}
console.log('PASS 0: existing DOM signal distinguishes pending from settled content');

const state = { id: 'reader-desktop', route: '/reader/a-ghost-story' };
const context = { viewport: { width: 1440, height: 1000 } };
const settled = { paginationReady: true, loading: false, visibleContentPresent: true };
const events = [];
let resolveWait;
const page = {
  waitForFunction: (predicate, unused, options) => {
    events.push('wait'); assert.match(predicate, /status.paginationReady && !status.loading && status.visibleContentPresent/);
    assert.equal(options.polling, 'raf'); assert.equal(options.timeout, 10000);
    return new Promise(resolve => { resolveWait = () => resolve({ jsonValue: async () => settled, dispose: async () => events.push('dispose') }); });
  },
};
const capture = async () => {
  const readiness = await waitForSettledReader(page, state, context);
  assert.deepEqual(readiness, { applicable: true, ...settled });
  events.push('pre', 'screenshot', 'post', 'compare');
};
const pending = capture();
assert.deepEqual(events, ['wait']);
resolveWait(); await pending;
assert.deepEqual(events, ['wait', 'dispose', 'pre', 'screenshot', 'post', 'compare']);
console.log('PASS 1: loading cannot reach pre-fingerprint; settled capture preserves ordering');

await assert.rejects(() => waitForSettledReader({ waitForFunction: async () => { throw new Error('timeout'); }, evaluate: async () => ({ paginationReady: false, loading: true, visibleContentPresent: false }) }, state, context), error => {
  assert.match(error.message, /"paginationReady":false/); assert.match(error.message, /"loading":true/); assert.match(error.message, /"visibleContentPresent":false/); assert.match(error.message, /reader-desktop/); assert.match(error.message, /1440/); return true;
});
console.log('PASS 2: unresolved Reader fails with actionable sanitized timeout');
assert.deepEqual(await waitForSettledReader({}, { route: '/library' }, context), { applicable: false });
console.log('PASS 3: non-Reader captures do not wait');
const source = fs.readFileSync('scripts/capture_seamless_brand_owner_review.mjs', 'utf8');
assert.match(source, /readerReadiness = await waitForSettledReader\(page, state, captureContext\);\s*rasterPriming = await primeWebKitTopOfDocumentRaster/);
assert.match(source, /readerReadiness = await waitForSettledReader\(page, state, captureContext\);\s*const \{ stable, stabilityAttempts, finalFiles \} = await captureStableScreenshots/);
assert.doesNotMatch(fs.readFileSync('scripts/lib/brand_reader_readiness.mjs', 'utf8'), /waitForTimeout|setTimeout|sleep\(/);
console.log('PASS 4: both capture paths wait before fingerprints without fixed delays');
console.log('5 tests passed');
