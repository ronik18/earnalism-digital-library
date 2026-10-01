#!/usr/bin/env node
/** Isolated local visual regression: never requests a production API or mutates a reader session. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { chromium } from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const base = process.env.READER_SPACING_BASE_URL || 'http://127.0.0.1:3015';
assert.ok(['localhost', '127.0.0.1'].includes(new URL(base).hostname), 'Reader spacing fixtures may only run against an isolated loopback server');
const output = path.resolve(process.env.READER_SPACING_OUTPUT || path.join(root, 'uat/evidence/blog-header-reader/reader'));
fs.mkdirSync(output, { recursive: true });
const chapter = JSON.parse(fs.readFileSync(path.join(root, 'data/controlled_publications/a-ghost-story/chapters/chapter-001.json')));
const publicBook = JSON.parse(fs.readFileSync(path.join(root, 'data/controlled_publications/a-ghost-story/public_book.json')));
const content = chapter.content.split(/\n\s*\n/).slice(0, 5).map(value => `<p>${value.replace(/&/g, '&amp;').replace(/</g, '&lt;')}</p>`).join('');
const book = { ...publicBook, slug: 'a-ghost-story', title: 'A Ghost Story', author: 'Mark Twain', language: 'English', chapters: [{ id: 'chapter-001', title: 'A Ghost Story' }] };
const manifest = { book, access: { reading_pass: { enabled: true, total_pages: 5 } }, canonical_pages: { page_count: 5, pages: Array.from({ length: 5 }, (_, index) => ({ page_number: index + 1, chapter_id: 'chapter-001' })) }, chapters: book.chapters };
const pageData = { book_slug: 'a-ghost-story', page_index: 1, chapter_id: 'chapter-001', chapter_title: 'A Ghost Story', total_pages: 5, is_preview: true, content, segmentation_version: 'isolated-visual-v1', manifest_version: 'isolated-visual-v1' };
const report = { head: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(), fixture_only: true, production_mutations: 0, root_cause: 'A separately centered 44rem prose block added a second indentation inside the wide 1fr reading canvas; the global cover height:100% stretched the cover to chapter height.', correction_pass: 'After first desktop/mobile screenshot review, reduced paragraph-block top spacing from 30px desktop / 26px mobile to the shared 24px rhythm; text, controls, authorization and engines unchanged.', cases: [] };
const browser = await chromium.launch();
try {
  for (const width of [2940, 1440, 1024, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } });
    const errors = [];
    const unexpectedWrites = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/api/**', route => {
      const request = route.request();
      if (request.method() !== 'GET') { unexpectedWrites.push(`${request.method()} ${new URL(request.url()).pathname}`); return route.abort(); }
      const url = request.url();
      const data = url.includes('/manifest') ? manifest : url.includes('/pages/1') ? pageData : url.includes('/settings') ? {} : { books: [] };
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(data) });
    });
    await page.goto(`${base}/reader/a-ghost-story`);
    await page.getByTestId('reader-reading-text').waitFor();
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(250);
    const metrics = await page.evaluate(() => {
      const rect = selector => { const box = document.querySelector(selector).getBoundingClientRect(); return { x: box.x, width: box.width, height: box.height }; };
      return { heading: rect('.reader-v2__chapter'), body: rect('.reader-v2__body'), canvas: rect('.reader-v2__canvas'), cover: rect('.reader-v2__book-cover'), overflow: document.documentElement.scrollWidth > innerWidth, body_margin: getComputedStyle(document.querySelector('.reader-v2__body')).marginTop };
    });
    assert.equal(metrics.overflow, false, `${width}: horizontal overflow`);
    assert.ok(Math.abs(metrics.heading.x - metrics.body.x) < 1, `${width}: prose must share the heading inset`);
    assert.equal(metrics.body_margin, '24px', `${width}: corrected block spacing`);
    if (width >= 1280) { assert.ok(metrics.canvas.width <= 769, `${width}: unbounded center track`); assert.ok(metrics.cover.height < 400, `${width}: cover stretched to chapter height`); }
    assert.deepEqual(errors, [], `${width}: runtime error`);
    assert.deepEqual(unexpectedWrites, [], `${width}: unexpected API mutation`);
    const screenshot = `reader-${width}.png`;
    await page.screenshot({ path: path.join(output, screenshot), fullPage: true });
    report.cases.push({ width, screenshot, metrics, runtime_errors: errors, unexpected_writes: unexpectedWrites, result: 'PASS' });
    await page.close();
  }
  report.result = 'PASS';
} finally {
  await browser.close();
  fs.writeFileSync(path.join(output, 'reader-spacing-report.json'), `${JSON.stringify(report, null, 2)}\n`);
}
console.log(`Reader spacing: ${report.cases.length}/4 viewports PASS; ${output}`);
