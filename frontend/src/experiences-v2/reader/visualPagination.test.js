import { paginateRendered, pageForAnchor, sliceBlock, textBoundaries } from './visualPagination';
function run(html, capacity = 40) {
  const source = document.createElement('div'); source.innerHTML = html;
  const measure = document.createElement('div');
  // Deterministic geometry stand-in only for algorithm tests. Browser tests use actual layout.
  return { source, pages: paginateRendered(source, measure, 100, () => measure.textContent.length <= capacity) };
}
test('short content is one complete visual page', () => {
  const { pages } = run('<p>A short page.</p>'); expect(pages).toHaveLength(1); expect(pages[0].text).toBe('A short page.');
});
test('overflow becomes the next page rather than being dropped', () => {
  const { pages } = run('<p>First paragraph here.</p><p>Second paragraph here.</p>', 25);
  expect(pages).toHaveLength(2);
});
test('a long rich paragraph splits and reconstructs every character in order', () => {
  const { source, pages } = run('<p>' + '<em>A quiet room.</em> '.repeat(40) + '</p>', 50);
  expect(pages.length).toBeGreaterThan(3);
  expect(pages.map(p => p.text).join('')).toBe(source.textContent);
  expect(pages.every(p => p.text.length <= 50)).toBe(true);
  expect(pages.slice(1).every(p => p.html.includes('data-reader-continuation'))).toBe(true);
  expect(pages.every(p => p.html.includes('<em>'))).toBe(true);
});
test('word boundaries preserve leading, trailing and repeated whitespace', () => {
  const text = '  one  two\nthree '; const offsets = textBoundaries(text);
  expect(offsets[0]).toBe(0); expect(offsets.at(-1)).toBe(text.length);
  expect(run(`<p>${text}</p>`, 8).pages.map(p => p.text).join('')).toBe(text);
});
test('an indivisible oversized word fails explicitly instead of clipping', () => {
  expect(() => run('<p>indivisibleword</p>', 5)).toThrow(/indivisible/);
});
test('headings move with following content when feasible', () => {
  const { pages } = run('<p>Some earlier body text.</p><h2>A heading</h2><p>Next body.</p>', 35);
  expect(pages[0].text).toBe('Some earlier body text.'); expect(pages[1].text).toBe('A headingNext body.');
});
test('repagination resolves an unchanged source anchor rather than visual index', () => {
  const html = '<p>' + 'A steady sentence. '.repeat(12) + '</p>';
  const wide = run(html, 80).pages; const narrow = run(html, 40).pages;
  const anchor = wide[1].start; const index = pageForAnchor(narrow, anchor);
  expect(narrow[index].start).toBeLessThanOrEqual(anchor); expect(narrow[index].end).toBeGreaterThan(anchor);
  expect(narrow.length).toBeGreaterThan(wide.length);
});
test('DOM range fragments preserve bold/link structure without duplicating text', () => {
  const block = document.createElement('p'); block.innerHTML = 'First <strong>bold words</strong> and last.';
  const left = sliceBlock(block, 0, 15); const right = sliceBlock(block, 15, block.textContent.length);
  expect(left.textContent + right.textContent).toBe(block.textContent);
});
test('empty content has a stable single page', () => { expect(run('').pages).toHaveLength(1); });
test('small unusable height fails safely', () => {
  expect(() => paginateRendered(document.createElement('div'), document.createElement('div'), 2)).toThrow(/readable line/);
});
test('anchor at the final boundary resolves to the final page', () => {
  const { pages } = run('<p>' + 'A sentence. '.repeat(10) + '</p>', 30);
  expect(pageForAnchor(pages, pages.at(-1).end)).toBe(pages.length - 1);
});
