#!/usr/bin/env node
// Repository-owned fixture reproducing the production BR-separated paragraph.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { chromium } from 'playwright';

const base = process.env.SEAMLESS_BRAND_TEST_BASE_URL;
assert.ok(base && ['127.0.0.1', 'localhost'].includes(new URL(base).hostname), 'Use an isolated loopback build');
const sourceDirectory = process.env.READER_LANDSCAPE_SOURCE_DIR;
const slug = 'agentic-ai-with-python';
const chunks = [
  '<p>' + 'An original fixture introduction. '.repeat(20) + '</p>',
  '<p>A source anchor precedes the file listing.</p><p>chapter_01_code_explainer/<br>.env.example<br>.gitignore<br>requirements.txt<br>code_explainer.py<br>test_code_explainer.py<br>README.md</p>',
  '<ul>' + ['Quiet', 'reading room', 'another', 'world', 'opens', 'a doorway', 'for readers', 'beyond', 'the page'].map(value => `<li><em>${value}</em></li>`).join('') + '</ul><p><em>' + 'Original emphasized continuation. '.repeat(20) + '</em></p>',
];
const hashes = chunks.map(content => createHash('sha256').update(content).digest('hex'));
const book = JSON.parse(fs.readFileSync(`data/controlled_publications/${slug}/public_book.json`));
const manifest = sourceDirectory ? JSON.parse(fs.readFileSync(path.join(sourceDirectory, 'manifest.json'))) : {
  book, chapters: [{ id: 'chapter-001', title: 'Chapter 1: Building Your First Python AI Assistant' }],
  access: { reading_pass: { enabled: true, total_pages: 4 } },
  canonical_pages: { schema_version: 'line-break-fixture-v1', content_revision: 'line-break-fixture-v1', preview_policy: { public_limit: 3, unit: 'canonical_page', enforced_by: 'server', ready: true }, page_count: 4, pages: [1, 2, 3, 4].map((page_number, i) => ({ page_number, page_id: `line-break-${page_number}`, content_hash: hashes[i] || hashes[0], chapter_id: 'chapter-001' })) },
};
assert.equal(manifest.book?.slug, slug, 'Fixture manifest book identity must match');
assert.equal(manifest.canonical_pages.pages.length, manifest.canonical_pages.page_count, 'Fixture manifest must contain every declared page');
assert.equal(manifest.access.reading_pass.total_pages, manifest.canonical_pages.page_count, 'Fixture access and page counts must match');
// Row four already declares hashes[0]. Supply its matching synthetic payload
// for authorized full-chapter delivery; the original first three bodies stay exact.
const payloads = manifest.canonical_pages.pages.map((row, i) => {
  const page_index = row.page_number;
  assert.equal(page_index, i + 1, 'Fixture canonical pages must be contiguous and ordered');
  const file = sourceDirectory && path.join(sourceDirectory, `page${page_index}.json`);
  if (file) assert.ok(fs.existsSync(file), `Missing captured fixture payload: ${file}`);
  const value = file ? JSON.parse(fs.readFileSync(file)) : {
    book_slug: slug, page_index, total_pages: manifest.canonical_pages.page_count,
    chapter_id: 'chapter-001', chapter_title: manifest.chapters[0].title,
    is_preview: page_index <= 3, content: chunks[i] || chunks[0], content_sha256: hashes[i] || hashes[0],
    segmentation_version: 'line-break-fixture-v1', manifest_version: 'line-break-fixture-v1',
  };
  assert.equal(typeof value.content, 'string', 'Fixture body must be supplied');
  assert.equal(value.book_slug, slug, 'Fixture book identity must match');
  assert.equal(value.page_index, page_index, 'Fixture page identity must match');
  assert.equal(value.chapter_id, row.chapter_id, 'Fixture chapter identity must match');
  assert.equal(value.total_pages, manifest.canonical_pages.page_count, 'Fixture page count must match');
  assert.equal(value.is_preview, page_index <= 3, 'Fixture preview policy must match');
  assert.equal(value.content_sha256, row.content_hash, 'Fixture manifest hash must match');
  assert.equal(createHash('sha256').update(value.content).digest('hex'), row.content_hash, 'Fixture body hash must match');
  return value;
});
const publication = { segmentation_version: payloads[0].segmentation_version, manifest_version: payloads[0].manifest_version };
assert.ok(publication.segmentation_version && publication.manifest_version, 'Fixture publication versions are required');
for (const value of payloads) {
  assert.equal(value.segmentation_version, publication.segmentation_version, 'Fixture segmentation version must match');
  assert.equal(value.manifest_version, publication.manifest_version, 'Fixture publication version must match');
}
if (manifest.canonical_pages.schema_version) assert.equal(publication.segmentation_version, manifest.canonical_pages.schema_version);
if (manifest.canonical_pages.content_revision) assert.equal(publication.manifest_version, manifest.canonical_pages.content_revision);
const dummyUser = { id: 'landscape-fixture-user', name: 'Isolated landscape reader', reading_seconds_balance: 600 };
const dummyToken = 'isolated-landscape-user-no-production-credential';
const output = process.env.READER_LANDSCAPE_OUTPUT || fs.mkdtempSync(path.join(os.tmpdir(), 'reader-landscape-line-breaks-'));
fs.mkdirSync(output, { recursive: true });
const browser = await chromium.launch();
const report = { cases: [], guest_cases: [], unauthorized_chunk_requests: 0, network_policy: 'ABORT_NON_LOOPBACK_BEFORE_WIRE', blocked_non_loopback_requests: 0 };
async function fixturePage(viewport, authenticated) {
  const page = await browser.newPage({ viewport, reducedMotion: 'reduce', serviceWorkers: 'block' });
  const state = { lease: null, starts: 0, renewals: 0, positions: 0, authorized_chunks: [], public_chunks: [], post_requests: 0 };
  if (authenticated) await page.addInitScript(token => localStorage.setItem('earnalism_user_token', token), dummyToken);
  await page.route('**/*', async route => {
    const request = route.request(); const url = new URL(request.url());
    if (url.origin !== new URL(base).origin) { report.blocked_non_loopback_requests++; return route.abort(); }
    if (!url.pathname.startsWith('/api/')) return route.continue();
    const send = (status, body) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
    const userMatches = authenticated && request.headers().authorization === `Bearer ${dummyToken}`;
    const leased = () => userMatches && state.lease && state.lease.expires > Date.now()
      && state.lease.user_id === dummyUser.id && state.lease.content_id === slug
      && state.lease.segmentation_version === publication.segmentation_version && state.lease.manifest_version === publication.manifest_version
      && request.headers()['x-reading-pass-session'] === state.lease.id && request.headers()['x-reading-pass-lease'] === state.lease.token;
    if (request.method() === 'PUT' && url.pathname.endsWith('/reading-pass/positions')) {
      assert.ok(authenticated && userMatches, 'Only the isolated signed-in reader may save a position');
      const payload = request.postDataJSON();
      assert.equal(payload.content_type, 'text'); assert.equal(payload.content_id, slug);
      assert.equal(payload.publication_segmentation_version, publication.segmentation_version);
      assert.equal(payload.publication_manifest_version, publication.manifest_version);
      assert.equal(payload.version, state.positions);
      return send(200, { version: ++state.positions });
    }
    if (request.method() === 'POST') {
      state.post_requests++;
      assert.ok(authenticated && userMatches, 'Guests must not start or mutate fixture sessions');
      const payload = request.postDataJSON();
      if (url.pathname.endsWith('/reading-pass/sessions/start')) {
        assert.equal(payload.content_type, 'text'); assert.equal(payload.content_id, slug);
        assert.ok(payloads.some(value => value.page_index === payload.canonical_page_index));
        assert.equal(payload.require_protected_text, true, 'Early-unit continuation must use ordinary protected-text admission');
        assert.ok(dummyUser.reading_seconds_balance > 0, 'The isolated dummy user has a reading entitlement');
        state.starts++; state.lease = { id: 'landscape-fixture-session', token: 'landscape-fixture-lease', version: 1,
          user_id: dummyUser.id, content_id: slug, ...publication, expires: Date.now() + 20000, preparation: Date.now() + 60000 };
      } else if (url.pathname.endsWith('/reading-pass/leases/renew')) {
        assert.ok(leased(), 'Renewal requires the matching user/publication-bound lease');
        assert.equal(payload.session_id, state.lease.id); assert.equal(payload.lease_version, state.lease.version);
        state.renewals++; state.lease.version++; state.lease.expires = Date.now() + 20000;
      } else if (url.pathname.endsWith('/reading-pass/sessions/end')) {
        assert.equal(payload.session_id, state.lease?.id);
        const session_id = state.lease.id; state.lease = null;
        return send(200, { ended: true, session_id, balance_seconds: 600 });
      } else assert.fail(`Unexpected fixture mutation: ${url.pathname}`);
      const preparing = !payload.text_phase || payload.text_phase === 'preparing';
      return send(200, { session_id: state.lease.id, lease_token: state.lease.token, lease_version: state.lease.version,
        content_type: 'text', content_id: slug, status: payload.active === false && !preparing ? 'Paused' : 'Running',
        text_phase: payload.text_phase || 'preparing', preparation_expires_at: new Date(state.lease.preparation).toISOString(),
        lease_expires_at: new Date(state.lease.expires).toISOString(), balance_seconds: 600, heartbeat_seconds: 10 });
    }
    assert.equal(request.method(), 'GET', 'Only the explicit isolated lease endpoints may mutate');
    if (url.pathname.endsWith('/users/me')) return send(userMatches ? 200 : 401, userMatches ? dummyUser : { detail: 'Not signed in' });
    if (url.pathname.includes('/reading-pass/positions/')) return send(200, { version: state.positions });
    const index = Number(url.pathname.match(/\/pages\/(\d+)/)?.[1]);
    if (index) {
      if (authenticated && (state.lease || index > 3)) {
        if (!leased()) { report.unauthorized_chunk_requests++; return send(403, { detail: { code: 'PASS_REQUIRED' } }); }
        state.authorized_chunks.push(index);
      } else {
        if (index > 3) { report.unauthorized_chunk_requests++; return send(401, { detail: { code: 'AUTH_REQUIRED' } }); }
        state.public_chunks.push(index);
      }
      return send(200, payloads[index - 1]);
    }
    return send(200, url.pathname.includes('/manifest') ? manifest : url.pathname.includes('/settings') ? {} : { books: [] });
  });
  return { page, state };
}
try {
  // The 768x563 case is production's effective native-125% geometry. It is a
  // layout regression, not a substitute for separate actual Chrome zoom QA.
  for (const viewport of [{ width: 844, height: 390 }, { width: 1440, height: 900 }, { width: 390, height: 844 }, { width: 768, height: 563 }, { width: 640, height: 469 }]) {
    const { page: guest, state: guestState } = await fixturePage(viewport, false);
    await guest.goto(`${base}/reader/${slug}?p=1`);
    await guest.locator('[data-pagination-ready="true"]').waitFor();
    const guestChoices = await guest.getByLabel('Go to page', { exact: true }).locator('option').count();
    assert.equal(guestChoices, 3, 'The guest selector is limited to three visual pages');
    await guest.getByLabel('Go to page', { exact: true }).selectOption({ index: 2 });
    await guest.waitForFunction(() => Number(document.querySelector('.reader-v2__visual-viewport')?.dataset.visualPageIndex) === 2);
    await guest.locator('.reader-v2__page-arrow--next').click();
    await guest.waitForURL(url => url.pathname === '/login');
    assert.equal(guestState.post_requests, 0, 'The guest phase must not mutate fixture state');
    assert.ok(guestState.public_chunks.every(index => index <= 3), 'Guests must never fetch protected chunks');
    report.guest_cases.push({ viewport, visual_choices: guestChoices, requested_chunks: guestState.public_chunks, post_requests: 0, result: 'PASS' });
    await guest.close();

    // Obtain an ordinary dummy-user lease through the actual continuation UI.
    // The entry geometry ensures the fixed BR fixture crosses the visual quota;
    // final assertions still use each of the five original target geometries.
    const { page, state } = await fixturePage({ width: 844, height: 390 }, true);
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    const requested = `${base}/reader/${slug}?p=2&a=39&r=${payloads[1].content_sha256}`;
    await page.goto(requested);
    await page.evaluate(() => {
      history.pushState(history.state, '', `?p=3&a=end`);
      dispatchEvent(new PopStateEvent('popstate'));
    });
    await page.getByTestId('reader-preview-limit').waitFor();
    await page.getByRole('button', { name: 'Continue with Reading Pass', exact: true }).click();
    await page.waitForFunction(total => Number(document.querySelector('[data-pagination-ready="true"]')?.dataset.transportChunks) === total, payloads.length);
    assert.equal(state.starts, 1, 'Full-layout traversal requires explicit fixture entitlement admission');
    assert.ok(state.authorized_chunks.includes(4), 'Declared chunk four requires the matching publication-bound lease');
    await page.setViewportSize(viewport);
    await page.waitForFunction(() => {
      const element = document.querySelector('[data-pagination-ready="true"]');
      return element && Number(element.dataset.layoutWidth) === element.clientWidth && Number(element.dataset.layoutHeight) === element.clientHeight;
    });
    await page.goBack();
    assert.equal(page.url(), requested, 'History must restore the original canonical source anchor under the valid lease');
    await page.waitForFunction(() => document.querySelector('[data-pagination-ready="true"][data-book-map-complete="true"]') || document.body.innerText.includes('This content cannot be safely paginated'));
    assert.equal(await page.locator('[data-pagination-ready="true"]').count(), 1, 'Pagination must be ready without safety fallback');
    const geometry = async () => page.evaluate(() => {
      const v = document.querySelector('.reader-v2__visual-viewport'); const body = v.querySelector('[data-testid="reader-reading-text"]'); const measure = v.querySelector('.reader-v2__pagination-measure');
      return { width: v.clientWidth, height: v.clientHeight, scrollWidth: v.scrollWidth, scrollHeight: v.scrollHeight,
        pages: Number(v.dataset.pageCount), index: Number(v.dataset.visualPageIndex), sourcePage: Number(v.dataset.sourcePage), sourceOffset: Number(v.dataset.sourceOffset),
        start: Number(v.dataset.pageStart), end: Number(v.dataset.pageEnd), fontSize: getComputedStyle(body).fontSize, lineHeight: getComputedStyle(body).lineHeight,
        measurementLineHeight: getComputedStyle(measure).lineHeight, chunks: Number(v.dataset.transportChunks) };
    });
    const initial = await geometry(); assert.ok(initial.height > 0);
    const anchor = await page.evaluate(content => { const template = document.createElement('template'); template.innerHTML = content; return template.content.textContent.length + 39; }, payloads[0].content);
    assert.ok(initial.start <= anchor && initial.end > anchor, 'The requested canonical source anchor remains on the resolved visual page');
    assert.equal(initial.fontSize, '18px'); assert.equal(initial.lineHeight, '24.75px'); assert.equal(initial.measurementLineHeight, initial.lineHeight);
    if (viewport.width === 844) { assert.equal(initial.width, 438); assert.equal(initial.height, 148); }
    const selector = page.getByLabel('Go to page', { exact: true });
    const texts = []; let breaks = 0;
    for (let i = 0; i < initial.pages; i++) {
      await selector.selectOption({ index: i });
      await page.waitForFunction(index => Number(document.querySelector('.reader-v2__visual-viewport').dataset.visualPageIndex) === index && document.querySelector('[data-pagination-ready="true"]'), i);
      const current = await geometry(); assert.equal(current.height, initial.height, 'Page-label changes must not resize prose or trigger repagination'); assert.equal(current.pages, initial.pages, 'Page turns must preserve the settled page map'); assert.ok(current.scrollHeight <= current.height + 1); assert.ok(current.scrollWidth <= current.width + 1);
      texts.push(await page.getByTestId('reader-reading-text').textContent()); breaks += await page.getByTestId('reader-reading-text').locator('br').count();
    }
    const source = await page.locator('.reader-v2__visual-viewport > .reader-v2__pagination-source').first().textContent();
    assert.equal(texts.join(''), source, 'No missing, duplicate or reordered source characters');
    assert.equal(breaks, await page.locator('.reader-v2__visual-viewport > .reader-v2__pagination-source').first().locator('br').count(), 'No missing or duplicated explicit line breaks');
    await selector.selectOption({ index: initial.index });
    await page.getByRole('button', { name: 'Next page', exact: true }).click();
    await page.waitForFunction(index => Number(document.querySelector('.reader-v2__visual-viewport').dataset.visualPageIndex) === index + 1, initial.index);
    await page.getByRole('button', { name: 'Previous page', exact: true }).click();
    await page.waitForFunction(index => Number(document.querySelector('.reader-v2__visual-viewport').dataset.visualPageIndex) === index, initial.index);
    assert.deepEqual(errors, []);
    await page.screenshot({ path: path.join(output, `${viewport.width}x${viewport.height}.png`) });
    report.cases.push({ viewport, initial, lease_starts: state.starts, authorized_chunks: state.authorized_chunks, source_chars: source.length, reconstructed_chars: texts.join('').length, line_breaks: breaks, result: 'PASS' });
    await page.close();
  }
  assert.equal(report.guest_cases.length, 5);
  assert.equal(report.unauthorized_chunk_requests, 0);
} finally {
  await browser.close(); fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
}
console.log(`Reader structural-boundary regression: ${report.cases.length}/5 PASS; ${output}`);
