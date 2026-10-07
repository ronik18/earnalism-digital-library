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
  canonical_pages: { page_count: 4, pages: [1, 2, 3, 4].map((page_number, i) => ({ page_number, page_id: `line-break-${page_number}`, content_hash: hashes[i] || hashes[0], chapter_id: 'chapter-001' })) },
};
const payloads = [1, 2, 3].map((page_index, i) => sourceDirectory ? JSON.parse(fs.readFileSync(path.join(sourceDirectory, `page${page_index}.json`))) : {
  book_slug: slug, page_index, total_pages: 4, chapter_id: 'chapter-001', chapter_title: manifest.chapters[0].title,
  is_preview: true, content: chunks[i], content_sha256: hashes[i], segmentation_version: 'line-break-fixture-v1', manifest_version: 'line-break-fixture-v1',
});
const output = process.env.READER_LANDSCAPE_OUTPUT || fs.mkdtempSync(path.join(os.tmpdir(), 'reader-landscape-line-breaks-'));
fs.mkdirSync(output, { recursive: true });
const browser = await chromium.launch();
const report = { cases: [], unauthorized_chunk_requests: 0 };
try {
  // The 768x563 case is production's effective native-125% geometry. It is a
  // layout regression, not a substitute for separate actual Chrome zoom QA.
  for (const viewport of [{ width: 844, height: 390 }, { width: 1440, height: 900 }, { width: 390, height: 844 }, { width: 768, height: 563 }, { width: 640, height: 469 }]) {
    const page = await browser.newPage({ viewport, reducedMotion: 'reduce' });
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    await page.route('**/api/**', route => {
      const request = route.request(); assert.equal(request.method(), 'GET', 'Preview must not mutate backend state');
      const url = request.url(); const index = Number(url.match(/\/pages\/(\d+)/)?.[1]);
      if (index > 3) { report.unauthorized_chunk_requests++; return route.abort(); }
      const data = url.includes('/manifest') ? manifest : index ? payloads[index - 1] : url.includes('/settings') ? {} : { books: [] };
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(data) });
    });
    await page.goto(`${base}/reader/${slug}?p=2&a=39&r=${payloads[1].content_sha256}`);
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
    report.cases.push({ viewport, initial, source_chars: source.length, reconstructed_chars: texts.join('').length, line_breaks: breaks, result: 'PASS' });
    await page.close();
  }
  assert.equal(report.unauthorized_chunk_requests, 0);
} finally {
  await browser.close(); fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
}
console.log(`Reader structural-boundary regression: ${report.cases.length}/5 PASS; ${output}`);
