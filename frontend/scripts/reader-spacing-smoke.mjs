#!/usr/bin/env node
/** Isolated local visual regression: never requests a production API or mutates a reader session. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
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
// Deterministic portrait image, matching the retained edition's 1600x2400 ratio.
// This checks layout, not live cover delivery, and makes no external image request.
for (const key of Object.keys(book)) if (/cover/i.test(key) && typeof book[key] === 'string' && /^https?:/.test(book[key])) book[key] = '/assets/reader-spacing-cover.svg';
const sourceBlocks = content.match(/<p>[\s\S]*?<\/p>/g);
const chunks = Array.from({ length: 5 }, (_, index) => sourceBlocks[index] || `<p>Owned fixture section ${index + 1}.</p>`);
const hashes = chunks.map(value => createHash('sha256').update(value).digest('hex'));
const manifest = { book, access: { reading_pass: { enabled: true, total_pages: 5 } }, canonical_pages: { page_count: 5, pages: Array.from({ length: 5 }, (_, index) => ({ page_number: index + 1, page_id: `fixture-${index + 1}`, content_hash: hashes[index], chapter_id: 'chapter-001' })) }, chapters: book.chapters };
const pageData = { book_slug: 'a-ghost-story', page_index: 1, chapter_id: 'chapter-001', chapter_title: 'A Ghost Story', total_pages: 5, is_preview: true, content, segmentation_version: 'isolated-visual-v1', manifest_version: 'isolated-visual-v1' };
const report = { head: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(), fixture_only: true, production_mutations: 0, root_cause: 'A separately centered 44rem prose block added a second indentation inside the wide 1fr reading canvas; the global cover height:100% stretched the cover to chapter height.', correction_pass: 'Quiet Folio preserves aligned measured prose in a bounded 52rem canvas; cover and edition details are available in the credits sheet rather than a repeated reading sidebar.', cases: [] };
const browser = await chromium.launch();
try {
  for (const width of [2940, 1440, 1024, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } });
    const errors = [];
    const unexpectedWrites = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('https://res.cloudinary.com/**', route => route.fulfill({ contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="2400"/>' }));
    await page.route('**/assets/reader-spacing-cover.svg', route => route.fulfill({ contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="2400"><rect width="1600" height="2400" fill="#d8c2a0"/></svg>' }));
    await page.route('**/api/**', route => {
      const request = route.request();
      if (request.method() !== 'GET') { unexpectedWrites.push(`${request.method()} ${new URL(request.url()).pathname}`); return route.abort(); }
      const url = request.url();
      const index = Number(url.match(/\/pages\/(\d+)/)?.[1]);
      const data = url.includes('/manifest') ? manifest : index ? { ...pageData, page_index: index, is_preview: index <= 3, content: chunks[index - 1], content_sha256: hashes[index - 1] } : url.includes('/settings') ? {} : { books: [] };
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(data) });
    });
    await page.goto(`${base}/reader/a-ghost-story`);
    await page.getByTestId('reader-reading-text').waitFor();
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(250);
    const metrics = await page.evaluate(() => {
      const rect = selector => { const node = document.querySelector(selector); if (!node) throw new Error(`Missing required Reader element: ${selector}`); const box = node.getBoundingClientRect(); return { x: box.x, y: box.y, width: box.width, height: box.height };  };
      return { heading: rect('.reader-v2__chapter'), body: rect('[data-testid="reader-reading-text"]'), canvas: rect('.reader-v2__canvas'), bar: rect('.reader-folio__bar'), footer: rect('.reader-folio__footer'), repeated_cover_count: document.querySelectorAll('.reader-folio__surface .reader-v2__book-cover, .reader-folio__surface .reader-v2__front-cover').length, overflow: document.documentElement.scrollWidth > innerWidth, body_margin: getComputedStyle(document.querySelector('[data-testid="reader-reading-text"]')).marginTop };
    });
    assert.equal(metrics.overflow, false, `${width}: horizontal overflow`);
    assert.ok(Math.abs(metrics.heading.x - metrics.body.x) < 1, `${width}: prose must share the heading inset`);
    assert.equal(metrics.body_margin, '0px', `${width}: paginated prose uses its measured inset without an extra outer margin`);
    assert.equal(metrics.repeated_cover_count, 0, `${width}: cover must not displace the reading canvas`);
    for (const [name, box] of [['bar', metrics.bar], ['footer', metrics.footer]]) {
      assert.ok(box.width > 0 && box.height > 0 && box.x >= 0 && box.y >= 0 && box.x + box.width <= width + 1 && box.y + box.height <= 1001, `${width}: ${name} navigation must be visible within the viewport`);
    }
    for (const control of await page.locator('.reader-folio__bar button, .reader-folio__footer button').all()) {
      assert.equal(await control.isVisible(), true, `${width}: compact control must be displayed`);
      const box = await control.boundingBox();
      assert.ok(box && box.width > 0 && box.height > 0 && box.x >= 0 && box.y >= 0 && box.x + box.width <= width + 1 && box.y + box.height <= 1001, `${width}: compact control must not be clipped`);
    }
    if (width >= 1280) assert.ok(metrics.canvas.width <= 833, `${width}: canvas exceeds the approved 52rem bound`);
    await page.getByRole('button', { name: 'Edition & credits', exact: true }).click();
    const credits = page.getByRole('dialog', { name: 'Edition and credits' });
    await credits.waitFor({ state: 'visible' });
    const cover = credits.locator('.reader-v2__front-cover');
    const coverBox = await cover.boundingBox();
    assert.ok(coverBox && coverBox.width > 0 && coverBox.width <= Math.min(width, 520), `${width}: edition cover must be available and bounded in its sheet`);
    const image = cover.getByRole('img', { name: 'A Ghost Story front cover', exact: true });
    await image.scrollIntoViewIfNeeded();
    await image.evaluate(node => node.decode());
    const imageMetrics = await image.evaluate(node => { const box = node.getBoundingClientRect(); return { width: box.width, height: box.height, naturalWidth: node.naturalWidth, naturalHeight: node.naturalHeight }; });
    assert.ok(imageMetrics.width > 0 && imageMetrics.height > 0 && imageMetrics.height <= 781, `${width}: cover image must have bounded positive height`);
    assert.ok(imageMetrics.naturalWidth > 0 && Math.abs(imageMetrics.naturalHeight / imageMetrics.naturalWidth - 1.5) < 0.01, `${width}: fixture image must decode at its portrait ratio`);
    assert.ok(Math.abs(imageMetrics.height / imageMetrics.width - 1.5) < 0.01, `${width}: cover image must preserve portrait aspect ratio, not stretch to chapter height`);
    metrics.edition_cover = imageMetrics;
    await page.getByRole('button', { name: 'Close edition and credits', exact: true }).click();
    await credits.waitFor({ state: 'hidden' });
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
