#!/usr/bin/env node
// Owned, isolated fixtures only. Never sends requests to the production API.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const base = process.env.READER_REFLOW_BASE_URL || 'http://127.0.0.1:13211';
assert.ok(['localhost', '127.0.0.1'].includes(new URL(base).hostname));
const output = process.env.READER_REFLOW_OUTPUT || '/tmp/earnalism-reader-prose-reflow-browser';
fs.mkdirSync(output, { recursive: true });
const source = JSON.parse(fs.readFileSync(path.join(root, 'backend/data/controlled_publications/the-selfish-giant/chapters/chapter-001.json'))).content;
const blocks = source.trim().split(/\n{2,}/).map(line => `<p>${line.trim().replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/\n/g, '<br>')}</p>`);
const chunks = [blocks.slice(0, 45).join(''), blocks.slice(45, 90).join(''), blocks.slice(90).join('')];
const hashes = chunks.map(s => createHash('sha256').update(s).digest('hex'));
const book = { slug: 'the-selfish-giant', title: 'The Selfish Giant', author: 'Oscar Wilde', language: 'English', genre: 'Young Readers', status: 'LIVE_APPROVED', allowPublicReading: true, chapters: [{ id: 'chapter-001', title: 'The Selfish Giant' }] };
const manifest = { book, access: { reading_pass: { enabled: true, total_pages: 3 } }, canonical_pages: { page_count: 3, pages: chunks.map((_, i) => ({ page_number: i + 1, page_id: `fixture-${i + 1}`, content_hash: hashes[i], chapter_id: 'chapter-001' })) }, chapters: book.chapters };
const report = { fixture_only: true, production_mutations: 0, cases: [] };
const browser = await chromium.launch({ executablePath: process.env.CHROME_EXECUTABLE || undefined });
try {
  for (const [width, height] of [[390, 844], [360, 740], [844, 390], [1440, 1000]]) {
    const page = await browser.newPage({ viewport: { width, height } });
    page.setDefaultTimeout(15000);
    const errors = []; const writes = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/api/**', route => {
      const request = route.request();
      if (request.method() !== 'GET') { writes.push(request.method()); return route.abort(); }
      const url = request.url(); const index = Number(url.match(/\/pages\/(\d+)/)?.[1]);
      const body = url.includes('/manifest') ? manifest : index ? { book_slug: book.slug, page_index: index, chapter_id: 'chapter-001', chapter_title: book.title, total_pages: 3, is_preview: true, content: chunks[index - 1], content_sha256: hashes[index - 1], segmentation_version: 'isolated-reflow-v1', manifest_version: 'isolated-reflow-v1' } : url.includes('/settings') ? {} : { books: [] };
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) });
    });
    await page.goto(`${base}/reader/${book.slug}`, { waitUntil: 'domcontentloaded' });
    console.log('Loaded', width, height);
    const ready = () => page.waitForFunction(() => document.querySelector('.reader-v2__visual-viewport')?.dataset.paginationReady === 'true');
    await ready();
    for (const size of ['1.125', '1.25', '2']) {
      await page.getByRole('button', { name: 'Reader settings', exact: true }).click();
      await page.locator('#reader-v2-settings label').filter({ hasText: 'Text size' }).locator('select').selectOption(size);
      await page.getByRole('button', { name: 'Close reading preferences', exact: true }).click();
      await page.waitForTimeout(300); // Allow the settings-triggered measurement generation to start.
      await ready();
      // Reset to the first page through normal navigation after reflow.
      const previous = page.getByRole('button', { name: 'Previous page', exact: true });
      for (let i = 0; i < 100 && await previous.isEnabled(); i++) { const index = Number(await page.locator('.reader-v2__visual-viewport').getAttribute('data-visual-page-index')); await previous.click(); await page.waitForFunction(i => Number(document.querySelector('.reader-v2__visual-viewport')?.dataset.visualPageIndex) < i, index); await ready(); }
      for (let turn = 0; turn < 3; turn++) {
        await ready();
        const state = await page.evaluate(() => {
          const body = document.querySelector('[data-testid="reader-reading-text"]');
          const source = document.querySelector('.reader-v2__pagination-source');
          const viewport = document.querySelector('.reader-v2__visual-viewport');
          return { text: body?.innerText, soft_wraps: source?.querySelectorAll('.reader-v2__soft-wrap').length, index: Number(viewport.dataset.visualPageIndex), overflow: viewport.scrollHeight > viewport.clientHeight + 1, error: document.body.innerText.includes('could not be fitted safely'), joined: [...source.querySelectorAll('p')].some(p => p.textContent.includes('play on theroad')), font: getComputedStyle(body).fontSize };
        });
        assert.ok(state.text.trim()); assert.ok(state.soft_wraps > 70); assert.ok(state.joined);
        const copied = await page.getByTestId('reader-reading-text').evaluate(body => {
          const selection = getSelection(); const range = document.createRange(); range.selectNodeContents(body); selection.removeAllRanges(); selection.addRange(range);
          const clipboardData = new DataTransfer();
          body.dispatchEvent(new ClipboardEvent('copy', { bubbles: true, cancelable: true, clipboardData }));
          selection.removeAllRanges();
          return { needed: Boolean(body.querySelector('[data-reader-soft-wrap]')), present: clipboardData.getData('text/plain').length > 0, clean: !clipboardData.getData('text/html').includes('data-reader-soft-wrap') };
        });
        if (copied.needed) { assert.ok(copied.present); assert.ok(copied.clean); }
        assert.equal(state.overflow, false); assert.equal(state.error, false); assert.equal(state.index, turn);
        report.cases.push({ width, height, size, turn, ...state, text: undefined, result: 'PASS' });
        if (turn < 2) { await page.getByRole('button', { name: 'Next page', exact: true }).click(); await page.waitForFunction(i => Number(document.querySelector('.reader-v2__visual-viewport')?.dataset.visualPageIndex) === i, turn + 1); await ready(); }
      }
      if (size === '1.25') { await page.waitForTimeout(350); await page.screenshot({ path: path.join(output, `reader-${width}x${height}.png`) }); }
    }
    assert.deepEqual(errors, []); assert.deepEqual(writes, []);
    await page.close();
  }
  report.result = 'PASS';
} catch (error) { for (const page of browser.contexts().flatMap(context => context.pages())) { console.error(await page.evaluate(() => ({ url: location.href, viewport: document.querySelector('.reader-v2__visual-viewport')?.outerHTML.slice(0,1000), text: document.body.innerText.slice(-2500) }))); await page.screenshot({ path: path.join(output, 'failure.png') }); } throw error; } finally { await browser.close(); fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n'); }
console.log(`Reader prose reflow: ${report.cases.length} browser cases PASS; ${output}`);
