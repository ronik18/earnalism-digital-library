// Local synthetic transport + real server lease service + real browser layout.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const base = process.env.READER_PREPARATION_BASE_URL;
assert.ok(base && new URL(base).hostname === '127.0.0.1', 'Synthetic qualification is loopback-only');
const python = process.env.READER_PREPARATION_PYTHON;
assert.ok(python, 'Supply the existing qualified Python runtime');
const output = process.env.READER_PREPARATION_OUTPUT;
assert.ok(output, 'Supply an explicit private output directory');
const legacyMode = process.env.READER_PREPARATION_LEGACY_MODE || '';
assert.ok(['', 'fast', 'slow'].includes(legacyMode));
const publicAssets = new Map();
fs.mkdirSync(output, { recursive: true });
const slug = 'reader-preparation-fixture';
const contents = Array.from({ length: 93 }, (_, i) => `<p>Page ${i + 1} original synthetic reading content. This is not a literary publication.</p><pre><code>def quiet_page():\n    return "meaningful story"</code></pre><p>Original fixture footnote<sup>2</sup>.</p>`);
const hashes = contents.map(content => createHash('sha256').update(content).digest('hex'));
const chapters = [{ id: 'earlier', title: 'Earlier chapter' }, { id: 'chapter-006', title: 'Chapter six' }];
const manifest = { book: { slug, title: 'Synthetic preparation qualification', author: 'Repository-owned fixture', language: 'English' }, chapters,
  access: { reading_pass: { enabled: true, total_pages: 93 } },
  canonical_pages: { page_count: 93, pages: contents.map((_, i) => ({ page_number: i + 1, page_id: `fixture:${i + 1}`, chapter_id: i < 74 ? 'earlier' : 'chapter-006', content_hash: hashes[i] })) } };
const browser = await chromium.launch({ headless: true });
const results = [];
try {
  for (const width of legacyMode ? [1440] : [390, 768, 1440]) {
    const bridge = spawn(python, ['-m', 'backend.tests.reader_preparation_bridge'], { cwd: process.cwd(), stdio: ['pipe', 'pipe', 'inherit'] });
    const waiting = new Map(); let id = 0;
    let readyResolve; const ready = new Promise(resolve => { readyResolve = resolve; });
    const lines = createInterface({ input: bridge.stdout });
    lines.on('line', line => { const value = JSON.parse(line); if (value.ready) readyResolve(value); else { waiting.get(value.id)?.(value); waiting.delete(value.id); } });
    const rpc = (action, args = {}) => new Promise(resolve => { const current = ++id; waiting.set(current, resolve); bridge.stdin.write(JSON.stringify({ id: current, action, args }) + '\n'); });
    const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
    const page = await context.newPage();
    const events = []; const errors = []; let elapsed = 0; let release;
    const lateChunks = new Promise(resolve => { release = resolve; });
    try {
      const initial = await ready;
      await context.addInitScript(() => localStorage.setItem('earnalism_user_token', 'synthetic-only-no-production-credential'));
      page.on('pageerror', error => errors.push(error.message));
      await context.route('**/*', async route => {
        const request = route.request(); const url = new URL(request.url());
        if (url.hostname !== '127.0.0.1') return route.abort();
        if (!url.pathname.startsWith('/api/')) {
          if (!legacyMode) return route.continue();
          // Read-only public homepage/static assets only. ALL application API
          // traffic stays synthetic/loopback; no production Reader is opened.
          const resource = url.pathname.startsWith('/reader/') ? '/' : url.pathname;
          if (resource !== '/' && !resource.startsWith('/static/') && !/\.(png|jpe?g|webp|svg|ico|woff2?)$/.test(resource)) return route.abort();
          if (!publicAssets.has(resource)) {
            const response = await page.request.get(`https://theearnalism.com${resource}`);
            assert.equal(response.status(), 200);
            const body = await response.body();
            publicAssets.set(resource, { body, contentType: response.headers()['content-type'], sha256: createHash('sha256').update(body).digest('hex') });
          }
          const asset = publicAssets.get(resource);
          return route.fulfill({ status: 200, contentType: asset.contentType, body: asset.body });
        }
        events.push({ kind: 'api', path: url.pathname });
        const send = (status, body) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
        if (url.pathname.endsWith('/users/me')) return send(200, { id: 'user-1', name: 'Synthetic Reader', reading_seconds_balance: 600 });
        if (url.pathname.endsWith(`/reader/book/${slug}/manifest`)) return send(200, manifest);
        if (url.pathname.endsWith('/reading-pass/sessions/start')) {
          const value = await rpc('start'); events.push({ kind: 'start', at: elapsed, phase: value.result?.text_phase }); return send(200, value.result);
        }
        if (url.pathname.includes(`/reading-pass/books/${slug}/pages/`)) {
          const n = Number(url.pathname.split('/').at(-1)); events.push({ kind: 'requested', n, at: elapsed });
          if (n >= 84 && legacyMode !== 'fast') await lateChunks;
          const headers = request.headers();
          const authority = await rpc('authorize', { session_id: headers['x-reading-pass-session'], lease_token: headers['x-reading-pass-lease'] });
          if (authority.error) return send(authority.error.status, { detail: authority.error });
          events.push({ kind: 'delivered', n, at: elapsed });
          return send(200, { book_slug: slug, page_index: n, chapter_id: 'chapter-006', chapter_title: 'Chapter six', total_pages: 93, is_preview: false,
            content: contents[n - 1], content_sha256: hashes[n - 1], segmentation_version: 'fixture-v1', manifest_version: 'fixture-manifest-v1' });
        }
        if (url.pathname.endsWith('/reading-pass/leases/renew')) {
          const payload = request.postDataJSON();
          const value = await rpc('renew', { ...payload, lease_token: request.headers()['x-reading-pass-lease'] });
          events.push({ kind: 'renew', at: elapsed, phase: payload.text_phase, active: payload.active, status: value.result?.status, debit: value.result?.deducted_seconds, error: value.error?.code });
          return value.error ? send(value.error.status, { detail: value.error }) : send(200, value.result);
        }
        if (url.pathname.endsWith('/reading-pass/sessions/end')) {
          const value = await rpc('end', request.postDataJSON()); return send(200, value.result);
        }
        if (url.pathname.includes('/reading-pass/positions/')) return send(200, { version: 0 });
        if (url.pathname.endsWith('/reading-pass/positions')) return send(200, { version: 1 });
        return send(200, []);
      });
      const until = async predicate => { for (let i = 0; i < 100; i++) { if (await predicate()) return; await new Promise(resolve => setTimeout(resolve, 25)); } throw new Error('Synthetic browser boundary did not complete'); };
      await page.goto(`${base}/reader/${slug}?p=75`, { waitUntil: 'domcontentloaded' });
      await page.getByTestId('reader-authorize-chapter').waitFor();
      await page.clock.install({ time: new Date(initial.epoch_ms) });
      await page.clock.pauseAt(new Date(initial.epoch_ms));
      const wallStart = performance.now();
      await page.getByTestId('reader-authorize-chapter').click();
      await until(() => events.filter(e => e.kind === 'delivered').length >= 9);
      if (legacyMode === 'fast') {
        await until(async () => {
          if (await page.locator('[data-pagination-ready="true"]').count()) return true;
          elapsed += .05; await rpc('clock', { seconds: elapsed }); await page.clock.runFor(50); return false;
        });
      }
      const remaining = (10 - elapsed) * 1000;
      elapsed = 10; await rpc('clock', { seconds: elapsed }); await page.clock.runFor(remaining);
      if (legacyMode) {
        await until(() => events.some(e => e.kind === 'renew'));
        const first = events.find(e => e.kind === 'renew');
        assert.equal(first.phase, undefined, 'Actual legacy frontend must omit the optional field');
        assert.equal(first.debit, 0, 'Legacy client cannot back-bill preparation');
        assert.equal(first.status, legacyMode === 'slow' ? 'Paused' : 'Running');
        if (legacyMode === 'fast') {
          assert.match(await page.getByTestId('reader-reading-text').locator('pre').first().textContent(), /\n    return/);
          assert.equal(await page.getByTestId('reader-reading-text').locator('sup').first().innerText(), '2');
          elapsed = 20; await rpc('clock', { seconds: elapsed }); await page.clock.runFor(10000);
          await until(() => events.filter(e => e.kind === 'renew').length >= 2);
          assert.equal(events.filter(e => e.kind === 'renew')[1].debit, 10);
        }
        await rpc('end', { session_id: (await rpc('state')).result.session_id });
        const state = (await rpc('state')).result;
        assert.equal(state.debit, legacyMode === 'slow' ? 0 : 10);
        assert.deepEqual(errors, []);
        const result = { width, result: 'PASS', legacy_mode: legacyMode, actual_public_production_assets: true, events, accounting: state,
          public_asset_hashes: [...publicAssets].map(([resource, value]) => ({ resource, sha256: value.sha256 })), production_api_requests: 0, production_reader_sessions: 0 };
        results.push(result); console.log(JSON.stringify({ width, legacy_mode: legacyMode, result: 'PASS', debit: state.debit }));
        continue;
      }
      await until(() => events.some(e => e.kind === 'renew' && e.phase === 'preparing'));
      assert.ok(events.filter(e => e.kind === 'renew').every(e => !e.active && e.debit === 0 && e.status === 'Running'));
      assert.equal(await page.getByRole('heading', { name: 'Reading paused', exact: true }).count(), 0);
      elapsed = 16.112; await rpc('clock', { seconds: elapsed }); await page.clock.runFor(6112); release();
      // Allow pagination's existing 80ms resize debounce on the controlled clock.
      await until(() => events.filter(e => e.kind === 'delivered').length === 19);
      await until(async () => {
        if (await page.locator('[data-pagination-ready="true"]').count()) return true;
        assert.ok(elapsed < 19.5, 'Real pagination must complete within the unchanged preparation grant');
        elapsed += 0.05; await rpc('clock', { seconds: elapsed }); await page.clock.runFor(50);
        return false;
      });
      await until(() => events.some(e => e.kind === 'renew' && e.phase === 'readable' && e.status === 'Running'));
      const first = events.find(e => e.kind === 'renew' && e.phase === 'readable');
      const firstReadableWallMs = performance.now() - wallStart;
      assert.equal(first.debit, 0);
      assert.match(await page.getByTestId('reader-reading-text').innerText(), /Page 75/);
      assert.match(await page.getByTestId('reader-reading-text').locator('pre').first().textContent(), /\n    return/);
      assert.equal(await page.getByTestId('reader-reading-text').locator('sup').first().innerText(), '2');
      // Finish the existing opening-arrival animation before visual evidence;
      // advancing both clocks does not synthesize activity or override CSS.
      elapsed += 0.25; await rpc('clock', { seconds: elapsed }); await page.clock.runFor(250);
      await new Promise(resolve => setTimeout(resolve, 250)); // CSS animation uses wall time.
      const geometry = await page.evaluate(() => {
        const canvas = document.querySelector('.reader-v2__canvas');
        const body = document.querySelector('[data-testid="reader-reading-text"]');
        return { width: innerWidth, scrollWidth: document.documentElement.scrollWidth, focused: document.hasFocus(), visibility: document.visibilityState,
          theme: canvas.dataset.readerTheme, canvas_background: getComputedStyle(canvas).backgroundColor, text_color: getComputedStyle(body).color, canvas_opacity: getComputedStyle(canvas).opacity };
      });
      assert.ok(geometry.scrollWidth <= geometry.width); assert.ok(geometry.focused && geometry.visibility === 'visible');
      await page.screenshot({ path: path.join(output, `readable-${width}.png`) });
      // Advance both server and browser clocks; do not rewrite activity state.
      for (let n = 0; n < 13; n++) {
        elapsed += 10; await rpc('clock', { seconds: elapsed }); await page.clock.runFor(10000);
        await until(() => events.some(e => e.kind === 'renew' && e.at === elapsed));
        if (events.at(-1)?.status === 'Paused' || events.some(e => e.kind === 'renew' && e.status === 'Paused')) break;
      }
      assert.ok(events.some(e => e.kind === 'renew' && e.active && e.debit > 0));
      assert.ok(events.some(e => e.kind === 'renew' && e.phase === 'inactive' && e.status === 'Paused'));
      await page.getByRole('heading', { name: 'Reading paused', exact: true }).waitFor();
      assert.equal(await page.getByTestId('reader-reading-text').count(), 0);
      const state = (await rpc('state')).result;
      assert.deepEqual(errors, []);
      const result = { width, result: 'PASS', first_readable_virtual_ms: first.at * 1000, first_readable_wall_ms: firstReadableWallMs, real_browser_geometry: geometry, events, accounting: state, production_requests: 0 };
      results.push(result); console.log(JSON.stringify({ width, result: 'PASS', first_readable_virtual_ms: first.at * 1000, debit_before_readability: first.debit }));
    } catch (error) {
      console.error(JSON.stringify({ width, errors, events, rendered: (await page.locator('body').innerText()).slice(0, 1000) }));
      await page.screenshot({ path: path.join(output, `failed-${width}.png`) });
      throw error;
    } finally {
      release();
      await context.unrouteAll({ behavior: 'wait' });
      await context.close(); bridge.stdin.end(); lines.close(); bridge.kill();
    }
  }
  fs.writeFileSync(path.join(output, 'qualification.json'), JSON.stringify({ result: 'PASS', synthetic_transport: true, real_backend_lease_service: true, real_browser_layout: true, controlled_clock: true, cases: results }, null, 2));
} finally { await browser.close(); }
