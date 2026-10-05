import { paginateRendered, paginateRenderedResponsive, pageForAnchor, sliceBlock, sliceTableRows, textBoundaries } from './visualPagination';
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

test('an oversized row uses an explicit sequential-cell alternative without losing text', () => {
  const {source,pages} = run('<table><tbody><tr><td>Long table text requiring more space.</td></tr></tbody></table>', 10);
  expect(pages.map(page => page.text).join('')).toBe(source.textContent);
  expect(pages.every(page => page.html.includes('role="table"'))).toBe(true);
  expect(pages.length).toBeGreaterThan(1);
});

test('multi-row tables paginate by complete measured rows with exact text order', () => {
  const html = '<div><table><thead><tr><th>Heading</th><th>Meaning</th></tr></thead><tbody>' + Array.from({length:8}, (_, i) => `<tr><td>Row ${i}</td><td>Meaning ${i}</td></tr>`).join('') + '</tbody></table></div>';
  const { source, pages } = run(html, 35);
  expect(pages.length).toBeGreaterThan(1);
  expect(pages.map(page => page.text).join('')).toBe(source.textContent);
  expect(pages.every(page => page.text.length <= 35)).toBe(true);
  expect(pages.every(page => page.html.includes('<table>'))).toBe(true);
  expect(pages.map(page => page.text).join('').match(/Heading/g)).toHaveLength(1);
});
test('row range slicing preserves formatting whitespace between rows', () => {
  const block = document.createElement('div'); block.innerHTML = '<table>\n<tbody>\n<tr><td>A</td></tr>\n<tr><td>B</td></tr>\n</tbody>\n</table>';
  expect(sliceTableRows(block, 0, 1).textContent + sliceTableRows(block, 1, 2).textContent).toBe(block.textContent);
});

test('long calculations yield and preserve exactly the same pages', async () => {
  const html = '<p>' + 'Original fixture sentence. '.repeat(30) + '</p>';
  const expected = run(html, 40).pages;
  const source = document.createElement('div'); source.innerHTML = html;
  const measure = document.createElement('div'); let ticks = 0; let yields = 0;
  const result = await paginateRenderedResponsive(source, measure, 100, { fits: () => measure.textContent.length <= 40, clock: () => ticks += 10, schedule: resume => { yields++; Promise.resolve().then(resume); } });
  expect(yields).toBeGreaterThan(0); expect(result).toEqual(expected);
});
test('a superseded calculation stops before committing stale fragments', () => {
  expect(() => paginateRenderedResponsive(document.createElement('div'), document.createElement('div'), 100, { cancelled: () => true })).toThrow(/superseded/);
});


test('formatting-only top-level whitespace never creates paragraph-shaped blank pages', () => {
  const source = document.createElement('div');
  source.innerHTML = '\n<h2>Heading</h2>\n<p>First body.</p>\n<p>Second body.</p>\n';
  const measure = document.createElement('div');
  const pages = paginateRendered(source, measure, 100, () => measure.querySelectorAll('p,h2').length <= 1);
  expect(pages.map(page => page.text).join('')).toBe(source.textContent);
  expect(pages.every(page => page.text.trim().length > 0)).toBe(true);
  expect(pages[0].start).toBe(0);
  expect(pages.at(-1).end).toBe(source.textContent.length);
  expect(pages.every((page, index) => !index || page.start === pages[index - 1].end)).toBe(true);
});
test('whitespace-only sources preserve every character on one stable page', () => {
  const { source, pages } = run(' \n ');
  expect(pages).toHaveLength(1);
  expect(pages[0].text).toBe(source.textContent);
  expect(pages[0].end).toBe(source.textContent.length);
});

test('tall multi-row fallback keeps headers and nested rich cell text exactly once', () => {
  const {source,pages} = run('<div><table><thead><tr><th>A</th><th>B</th></tr></thead><tbody><tr><td><em>' + 'Several complete words. '.repeat(10) + '</em></td><td>Ending</td></tr></tbody></table></div>',40);
  expect(pages.map(page => page.text).join('')).toBe(source.textContent);
  expect(pages.flatMap(page => [...page.text.matchAll(/Ending/g)])).toHaveLength(1);
});

test('paragraph-boundary ranges preserve whitespace without phantom empty lines', () => {
  const quote = document.createElement('blockquote'); quote.innerHTML = '<p>First.</p>\n<p>Second paragraph.</p>';
  const part = sliceBlock(quote, 6, quote.textContent.length);
  expect(part.textContent).toBe(quote.textContent.slice(6));
  expect([...part.querySelectorAll('p')].every(node => node.textContent.trim())).toBe(true);
});


test('multiple media-only pages have stable structural anchors', () => {
  const source = document.createElement('div'); source.innerHTML = '<img alt="First owned fixture"><img alt="Second owned fixture">';
  const measure = document.createElement('div');
  const pages = paginateRendered(source, measure, 100, () => measure.querySelectorAll('img').length <= 1);
  expect(pages.map(page => page.anchor)).toEqual(['media:0', 'media:1']);
  expect(pageForAnchor(pages, 'media:1')).toBe(1);
  const wide = paginateRendered(source, measure, 100, () => true);
  expect(pageForAnchor(wide, 'media:1')).toBe(0);
  expect(pages.map(page => page.text).join('')).toBe(source.textContent);
});

test('formatting whitespace cannot turn an image-only page into a text anchor', () => {
  const source = document.createElement('div'); source.innerHTML = '<img alt="One">\n<img alt="Two">\n';
  const measure = document.createElement('div');
  const pages = paginateRendered(source, measure, 100, () => measure.querySelectorAll('img').length <= 1);
  expect(pages.map(page => page.anchor)).toEqual(['media:0', 'media:1']);
  expect(pages.map(page => page.text).join('')).toBe(source.textContent);
});


test('undecoded measurement clones retain decoded source image geometry', () => {
  const source = document.createElement('div');
  source.innerHTML = '<figure><img alt="Owned tall figure"><figcaption>Caption one.</figcaption></figure><figure><img alt="Owned second figure"><figcaption>Caption two.</figcaption></figure>';
  for (const image of source.querySelectorAll('img')) {
    Object.defineProperties(image, { naturalWidth: {value: 320}, naturalHeight: {value: 640} });
  }
  const measure = document.createElement('div');
  Object.defineProperty(measure, 'clientWidth', {value: 300});
  Object.defineProperty(measure, 'scrollHeight', {get() {
    return [...measure.querySelectorAll('img')].reduce((sum, image) => sum + (image.style.height ? parseFloat(image.style.height) : Number(image.getAttribute('height'))), 0) + measure.querySelectorAll('figcaption').length * 30;
  }});
  const pages = paginateRendered(source, measure, 200, () => measure.scrollHeight <= 200);
  expect(pages).toHaveLength(2);
  expect(pages.map(page => page.text).join('')).toBe(source.textContent);
  expect(pages.flatMap(page => page.media)).toEqual([0, 1]);
  for (const page of pages) {
    measure.innerHTML = page.html;
    const image = measure.querySelector('img');
    expect(image.getAttribute('width')).toBe('320');
    expect(image.getAttribute('height')).toBe('640');
    expect(parseFloat(image.style.height) + 30).toBeLessThanOrEqual(200);
  }
});
