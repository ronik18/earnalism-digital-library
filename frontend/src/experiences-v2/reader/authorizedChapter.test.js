import { chapterWindowPlan, fetchChapterWindow, chapterAnchor, transportAnchor } from './authorizedChapter';
import { readerSourceText } from './readerContent';
const { createHash } = require('crypto');
const { TextEncoder } = require('util');
globalThis.TextEncoder = TextEncoder;
const previousCrypto = globalThis.crypto;
beforeAll(() => Object.defineProperty(globalThis, 'crypto', { configurable: true, value: { subtle: { digest: async (_, bytes) => Uint8Array.from(createHash('sha256').update(Buffer.from(bytes)).digest()).buffer } } }));
afterAll(() => Object.defineProperty(globalThis, 'crypto', { configurable: true, value: previousCrypto }));
const hash = n => createHash('sha256').update(`<p>Source ${n} <em>exactly</em>.</p>`).digest('hex');
const manifest = () => ({ canonical_pages: { page_count: 10, content_revision: 'edition-v1', preview_policy: { public_limit: 2 }, pages: Array.from({ length: 10 }, (_, i) => ({ page_number: i + 1, page_id: `unit-${i + 1}`, chapter_id: 'chapter-one', content_hash: hash(i + 1) })) } });
const chunk = n => ({ book_slug: 'approved-fixture', page_index: n, total_pages: 10, chapter_id: 'chapter-one', manifest_version: 'edition-v1', segmentation_version: 'blocks-v1', content_sha256: hash(n), is_preview: n <= 2, content: `<p>Source ${n} <em>exactly</em>.</p>` });
const fetch = (plan, fetchChunk = jest.fn(async n => chunk(n)), options = {}) => fetchChapterWindow({ plan, slug: 'approved-fixture', totalPages: 10, fetchChunk, ...options });
test('preview policy selects only explicitly public units, without requesting protected content', async () => {
  const get = jest.fn(async n => chunk(n));
  const window = await fetch(chapterWindowPlan(manifest(), 1, false), get);
  expect(get.mock.calls.map(([n]) => n)).toEqual([1, 2]);
  expect(window.sources.map(item => item.page)).toEqual([1, 2]);
  expect(window.plan.next).toBe(3);
  expect(window.html).toBe(chunk(1).content + chunk(2).content);
});
test('full chapter assembly preserves exact order with bounded parallel completion', async () => {
  let running = 0, peak = 0;
  const get = jest.fn(async n => { running++; peak = Math.max(peak, running); await Promise.resolve(); running--; return chunk(n); });
  const window = await fetch(chapterWindowPlan(manifest(), 4, true), get);
  expect(peak).toBeLessThanOrEqual(3);
  expect(window.sources.map(item => item.page)).toEqual(Array.from({ length: 10 }, (_, n) => n + 1));
  expect(window.html).toBe(Array.from({ length: 10 }, (_, n) => chunk(n + 1).content).join(''));
  expect(readerSourceText(window.html).length).toBe(window.textLength);
});
test.each(['missing', 'duplicate', 'out-of-order', 'chapter-gap'])('%s manifest fails before acquisition', kind => {
  const value = manifest();
  if (kind === 'missing') value.canonical_pages.pages.splice(3, 1);
  if (kind === 'duplicate') value.canonical_pages.pages[4] = value.canonical_pages.pages[3];
  if (kind === 'out-of-order') value.canonical_pages.pages.reverse();
  if (kind === 'chapter-gap') value.canonical_pages.pages[3].chapter_id = 'other';
  expect(() => chapterWindowPlan(value, 1, true)).toThrow();
});
test.each(['chapter_id', 'content_sha256', 'manifest_version', 'page_index', 'segmentation_version'])('incompatible %s never produces a ready map', async field => {
  const get = async n => ({ ...chunk(n), ...(n === 4 ? { [field]: 'incorrect' } : {}) });
  await expect(fetch(chapterWindowPlan(manifest(), 4, true), get)).rejects.toThrow();
});
test('expired authorization cancels further acquisitions and discards the entire window', async () => {
  let allowed = true;
  const get = jest.fn(async n => { allowed = false; return chunk(n); });
  await expect(fetch(chapterWindowPlan(manifest(), 4, true), get, { authorized: () => allowed, concurrency: 1 })).rejects.toThrow('authorization changed');
  expect(get).toHaveBeenCalledTimes(1);
});
test('aborted chapter does not acquire a chunk', async () => {
  const controller = new AbortController(); controller.abort();
  const get = jest.fn();
  await expect(fetch(chapterWindowPlan(manifest(), 4, true), get, { signal: controller.signal })).rejects.toThrow();
  expect(get).not.toHaveBeenCalled();
});
test('chunk-local links/bookmarks round-trip through absolute offsets and revision changes reset safely', async () => {
  const window = await fetch(chapterWindowPlan(manifest(), 4, true));
  const offset = chapterAnchor(window, 5, 8, hash(5));
  expect(transportAnchor(window, offset)).toEqual({ page: 5, offset: 8, revision: hash(5) });
  expect(chapterAnchor(window, 5, 8, 'old-revision')).toBe(window.sources[4].start);
  expect(() => chapterAnchor(window, 11, 0)).toThrow();
});
test('semantic chunk seams introduce no forced separators and retain repeated real headings', async () => {
  const plan = chapterWindowPlan(manifest(), 1, false);
  const html = '<h2>Real repeated source heading</h2><p>Body.</p>';
  const digest = createHash('sha256').update(html).digest('hex');
  plan.rows.forEach(row => { row.content_hash = digest; });
  const window = await fetch(plan, async n => ({ ...chunk(n), content_sha256: digest, content: html }));
  expect(readerSourceText(window.html)).toBe('Real repeated source headingBody.Real repeated source headingBody.');
});

test('a tampered body with unchanged response and manifest hashes is rejected', async () => {
  await expect(fetch(chapterWindowPlan(manifest(), 4, true), async n => ({ ...chunk(n), content: n === 4 ? '<p>Altered text.</p>' : chunk(n).content }))).rejects.toThrow('content hash');
});
test('a widened preview policy cannot cause protected acquisition without a lease', () => {
  const value = manifest(); value.canonical_pages.preview_policy.public_limit = 10;
  expect(() => chapterWindowPlan(value, 1, false)).toThrow('preview policy');
});


test('eight-chunk chapter selects exactly the authorized preview and full windows', async () => {
  const value = manifest(); value.canonical_pages.pages = value.canonical_pages.pages.slice(0, 8); value.canonical_pages.page_count = 8;
  const get = jest.fn(async n => ({ ...chunk(n), total_pages: 8 }));
  const acquire = plan => fetchChapterWindow({ plan, slug: 'approved-fixture', totalPages: 8, fetchChunk: get });
  const preview = await acquire(chapterWindowPlan(value, 1, false));
  expect(get.mock.calls.map(([n]) => n)).toEqual([1, 2]);
  expect(preview.sources).toHaveLength(2);
  get.mockClear();
  const full = await acquire(chapterWindowPlan(value, 4, true));
  expect(get.mock.calls.map(([n]) => n).sort((a,b) => a-b)).toEqual([1,2,3,4,5,6,7,8]);
  expect(full.sources.every((source,index) => index === 0 || source.start === full.sources[index-1].end)).toBe(true);
  expect(readerSourceText(full.html).length).toBe(full.textLength);
});
test('duplicate canonical chunk IDs are rejected before fetching', () => {
  const value = manifest(); value.canonical_pages.pages[1].page_id = value.canonical_pages.pages[0].page_id;
  expect(() => chapterWindowPlan(value,1,true)).toThrow();
});
