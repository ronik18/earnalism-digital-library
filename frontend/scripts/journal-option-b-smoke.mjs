/** Local-only fixture QA. Never creates production articles/accounts/comments. */
import { chromium } from 'playwright';
import fs from 'node:fs/promises';
const base = process.env.JOURNAL_QA_BASE || 'http://127.0.0.1:3015';
if (!['localhost', '127.0.0.1'].includes(new URL(base).hostname)) throw new Error('Fixture QA requires loopback');
const output = process.env.JOURNAL_QA_OUTPUT || '/tmp/earnalism-journal-option-b';
await fs.mkdir(output, { recursive: true });
const posts = Array.from({ length: 13 }, (_, i) => ({ slug: `review-fixture-${i}`, title: i === 0 ? 'Make room for a quieter reading life.' : `Reading note ${i}`, author: 'Local review fixture', category: i % 2 ? 'Books & ideas' : 'Reading life', excerpt: 'A local visual fixture for the approved editorial layout. This is not a published article.', created_at: `2026-10-${String(14 - i).padStart(2, '0')}T12:00:00Z`, cover_image_url: '/assets/home-option-b/hero-reading-room.webp', cover_image_alt: 'Existing Earnalism reading-room artwork', image_caption: 'Existing approved asset, used for local visual review only.', content: 'A quiet moment with a book.\n\nReturn to the page with care.', content_html: '<p>A quiet moment with a book.</p><p>Explore the <a href="/library">Library</a> and return to the page with care.</p>' }));
const browser = await chromium.launch({ headless: true });
const report = [];
try {
for (const width of [1440, 1024, 390]) {
 const context = await browser.newContext({ viewport: { width, height: 900 } });
 let listFailure = true;
 await context.route('**/api/**', async (route) => {
  const url = new URL(route.request().url());
  const pathname = url.pathname;
  if (route.request().method() !== 'GET') throw new Error(`Unexpected fixture write ${pathname}`);
  if (pathname.endsWith('/blog')) { if (listFailure) { listFailure = false; return route.fulfill({ status: 503, json: { detail: 'Deterministic local outage' } }); } return route.fulfill({ json: posts }); }
  if (pathname.endsWith('/discussion')) return route.fulfill({ json: { likes: 0, comments: [] } });
  if (pathname.includes('/blog/review-fixture-')) return route.fulfill({ json: posts.find((p) => pathname.endsWith(p.slug)) });
  return route.fulfill({ status: 503, json: { detail: 'Local QA isolation' } });
 });
 const page = await context.newPage(); const errors = [];
 page.on('pageerror', (error) => errors.push(error.message));
 await page.goto(base + '/journal'); await page.getByTestId('journal-api-error').waitFor();
 if (await page.getByTestId('journal-empty').count()) throw new Error('Outage misrepresented as empty shelf');
 await page.screenshot({ path: `${output}/journal-error-${width}.png`, fullPage: true });
 await page.getByRole('button', { name: 'Retry', exact: true }).click();
 await page.getByTestId('journal-feature').waitFor();
 await page.screenshot({ path: `${output}/journal-${width}.png`, fullPage: true });
 const columns = await page.locator('.journal-v2__grid').evaluate((el) => getComputedStyle(el).gridTemplateColumns.split(' ').length);
 if (columns !== (width >= 1280 ? 3 : width >= 768 ? 2 : 1)) throw new Error(`Wrong columns ${width}: ${columns}`);
 await page.getByRole('searchbox', { name: 'Search articles' }).fill('no matching fixture');
 await page.getByTestId('journal-empty').waitFor();
 await page.getByRole('searchbox', { name: 'Search articles' }).fill('');
 await page.getByTestId('journal-feature-read').click();
 await page.getByTestId('journal-article').waitFor();
 await page.getByRole('link', { name: 'Sign in to like' }).waitFor();
 await page.getByRole('link', { name: 'Share on LinkedIn' }).waitFor();
 await page.screenshot({ path: `${output}/article-${width}.png`, fullPage: true });
 const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
 if (overflow || errors.length) throw new Error(JSON.stringify({ width, overflow, errors }));
 report.push({ width, columns, overflow: false, errors, article: 'PASS', signedOutWritesSuppressed: true });
 await context.close();
}
for (const width of [1440, 390]) {
 const context = await browser.newContext({ viewport: { width, height: 900 } });
 await context.addInitScript(() => localStorage.setItem('earnalism_user_token', 'local-fixture-not-a-production-credential'));
 const writes = [];
 await context.route('**/api/**', async (route) => {
  const pathname = new URL(route.request().url()).pathname; const method = route.request().method();
  if (method === 'PUT' && pathname.endsWith('/like')) { writes.push({ method, pathname }); return route.fulfill({ json: { liked: true, likes: 1 } }); }
  if (method === 'POST' && pathname.endsWith('/comments')) { const body = route.request().postDataJSON(); writes.push({ method, pathname }); return route.fulfill({ status: 201, json: { id: 'local-comment', author: 'Local fixture reader', text: body.text, created_at: '2026-10-01T12:00:00Z' } }); }
  if (method !== 'GET') throw new Error(`Unexpected fixture write ${pathname}`);
  if (pathname.endsWith('/users/me')) return route.fulfill({ json: { id: 'local-user', name: 'Local fixture reader', reading_seconds_balance: 0 } });
  if (pathname.endsWith('/blog')) return route.fulfill({ json: posts });
  if (pathname.endsWith('/discussion')) return route.fulfill({ json: { likes: 0, comments: [] } });
  if (pathname.endsWith('/my-like')) return route.fulfill({ json: { liked: false } });
  if (pathname.includes('/blog/review-fixture-')) return route.fulfill({ json: posts.find((p) => pathname.endsWith(p.slug)) });
  return route.fulfill({ status: 503, json: { detail: 'Local QA isolation' } });
 });
 const page = await context.newPage(); await page.goto(base + '/journal/review-fixture-0');
 await page.getByRole('button', { name: 'Post comment' }).waitFor();
 await page.screenshot({ path: `${output}/article-signed-in-${width}.png`, fullPage: true });
 await page.getByRole('button', { name: 'Like · 0', exact: true }).click();
 await page.getByRole('button', { name: 'Liked · 1', exact: true }).waitFor();
 await page.getByLabel('Your comment', { exact: true }).fill('Local-only response, never submitted to production.');
 await page.getByRole('button', { name: 'Post comment', exact: true }).click();
 await page.locator('.journal-comment').waitFor();
 await page.screenshot({ path: `${output}/article-engaged-${width}.png`, fullPage: true });
 if (writes.length !== 2) throw new Error(`Unexpected number of fixture writes ${writes.length}`);
 report.push({ width, signedInComposer: 'PASS', like: 'PASS', comment: 'PASS', mockedWrites: writes });
 await context.close();
}
await fs.writeFile(`${output}/report.json`, JSON.stringify(report, null, 2));
console.log(JSON.stringify({ output, report }));
} finally { await browser.close(); }
