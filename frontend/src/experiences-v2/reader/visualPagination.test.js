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
test('explicit line breaks split a filename paragraph without whitespace or source changes', () => {
  const source = document.createElement('div');
  source.innerHTML = '<p>chapter_01_code_explainer/<br>.env.example<br>.gitignore<br>requirements.txt<br>code_explainer.py<br>test_code_explainer.py<br>README.md</p>';
  const measure = document.createElement('div');
  const pages = paginateRendered(source, measure, 148, () => measure.querySelectorAll('br').length <= 3);
  expect(pages.length).toBeGreaterThan(1);
  expect(pages.map(page => page.text).join('')).toBe(source.textContent);
  const reconstructed = document.createElement('div'); reconstructed.innerHTML = pages.map(page => page.html).join('');
  expect(reconstructed.querySelectorAll('br')).toHaveLength(6);
  expect(pages.every(page => !/^<p[^>]*><br/.test(page.html))).toBe(true);
});
test('a line-break seam preserves nested emphasis and exact source coordinates', () => {
  const block = document.createElement('p'); block.innerHTML = '<em>first<br>second<br>third</em>';
  const left = sliceBlock(block, 0, 5); const right = sliceBlock(block, 5, block.textContent.length);
  expect(left.textContent + right.textContent).toBe(block.textContent);
  expect(left.querySelectorAll('br').length + right.querySelectorAll('br').length).toBe(2);
  expect(left.querySelector('em')).not.toBeNull(); expect(right.querySelector('em')).not.toBeNull();
  expect(right.querySelector('em').firstChild.nodeType).toBe(Node.TEXT_NODE);
});
test('adjacent list items without whitespace split at structural seams', () => {
  const source = document.createElement('div');
  source.innerHTML = '<ul>' + ['Quiet', 'reading room', 'another', 'world', 'opens', 'a doorway', 'for readers'].map(value => `<li><em>${value}</em></li>`).join('') + '</ul>';
  const measure = document.createElement('div');
  const pages = paginateRendered(source, measure, 131, () => measure.querySelectorAll('li').length <= 5);
  expect(pages.length).toBeGreaterThan(1);
  expect(pages.map(page => page.text).join('')).toBe(source.textContent);
  const reconstructed = document.createElement('div'); reconstructed.innerHTML = pages.map(page => page.html).join('');
  expect(reconstructed.querySelectorAll('li')).toHaveLength(7);
  expect([...reconstructed.querySelectorAll('li')].every(item => item.textContent.length > 0 && item.querySelector('em'))).toBe(true);
  expect(pages.every(page => { const fragment = document.createElement('div'); fragment.innerHTML = page.html; return fragment.querySelectorAll('li').length <= 5; })).toBe(true);
  expect(pages.every((page, index) => !index || page.start === pages[index - 1].end)).toBe(true);
});
test('list seam ranges retain emphasis without phantom items or invented whitespace', () => {
  const block = document.createElement('ul'); block.innerHTML = '<li><strong>First</strong></li><li><em>Second</em></li>';
  const left = sliceBlock(block, 0, 5); const right = sliceBlock(block, 5, 11);
  expect(left.textContent + right.textContent).toBe(block.textContent);
  expect(left.querySelectorAll('li')).toHaveLength(1); expect(right.querySelectorAll('li')).toHaveLength(1);
  expect(left.querySelector('strong')).not.toBeNull(); expect(right.querySelector('em')).not.toBeNull();
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

function seamRun(html, pageBreaks, capacity = 40, options = {}) {
  const source = document.createElement('div'); source.innerHTML = html;
  const measure = document.createElement('div');
  const fits = () => measure.textContent.length <= capacity && measure.querySelectorAll('img').length <= 1;
  return { source, measure, fits, pages: paginateRendered(source, measure, 100, fits, { ...options, pageBreaks }) };
}
function expectSeamIntegrity(source, pages, boundaries) {
  expect(pages.map(page => page.text).join('')).toBe(source.textContent);
  expect(pages.slice(1).every((page, index) => page.start === pages[index].end)).toBe(true);
  for (const boundary of boundaries) {
    expect(pages.some(page => page.start === boundary.offset)).toBe(true);
    expect(pages.some(page => page.start < boundary.offset && page.end > boundary.offset)).toBe(false);
  }
  const template = document.createElement('template'); template.innerHTML = pages.map(page => page.html).join('');
  expect([...template.content.querySelectorAll('img')].map(image => image.getAttribute('src'))).toEqual([...source.querySelectorAll('img')].map(image => image.getAttribute('src')));
}

test.each([
  ['split inline ancestors', '<p>Alpha <strong>bold <em>italic words</em> tail</strong> end.</p>', [{ offset: 16, media: 0 }]],
  ['formatting whitespace', '<p>prefix words</p> \n\t <p>suffix words and tail</p>', [{ offset: 14, media: 0 }]],
  ['heading lookahead across whitespace', '<p>previous</p><h2>Heading</h2> \n <p>following chapter words</p>', [{ offset: 16, media: 0 }]],
  ['multiple seams in one node', '<p>one two three four five six seven eight nine ten</p>', [{ offset: 8, media: 0 }, { offset: 28, media: 0 }]],
  ['nested original node', '<article><section><p>alpha <strong>beta <em>gamma words</em> delta</strong> tail</p></section></article>', [{ offset: 16, media: 0 }]],
])('seams preserve every character and prevent crossing: %s', (_name, html, boundaries) => {
  const { source, pages } = seamRun(html, boundaries, 22); expectSeamIntegrity(source, pages, boundaries);
});

test('canonical preview prefix remains identical after full chapter pagination', () => {
  const html = '<p>one two three four five six seven eight nine ten</p>';
  const { source, pages } = seamRun(html, [{ offset: 28, media: 0 }], 20);
  const prefix = document.createElement('div'); prefix.innerHTML = '<p>' + source.textContent.slice(0, 28) + '</p>';
  const measure = document.createElement('div'); const expected = paginateRendered(prefix, measure, 100, () => measure.textContent.length <= 20);
  expect(pages.filter(page => page.end <= 28).map(page => [page.start, page.end, page.text])).toEqual(expected.map(page => [page.start, page.end, page.text]));
  expect(pages[pageForAnchor(pages, 28)].start).toBe(28);
});

test('zero-text media seams preserve order and structural anchors', () => {
  const boundary = { offset: 0, media: 1 };
  const { source, pages } = seamRun('<figure><img src="/one"></figure><figure><img src="/two"></figure><p>tail words</p>', [boundary], 20);
  expectSeamIntegrity(source, pages, [boundary]); expect(pages.flatMap(page => page.media)).toEqual([0, 1]);
  for (const ordinal of [0, 1]) expect(pages[pageForAnchor(pages, `media:${ordinal}`)].media).toContain(ordinal);
});

test('between-row media seams preserve table row structure', () => {
  const boundary = { offset: 5, media: 1 };
  const { source, pages } = seamRun('<section><table><tbody><tr><td>first<img src="/one"></td></tr><tr><td>second<img src="/two"></td></tr></tbody></table></section>', [boundary], 20);
  expectSeamIntegrity(source, pages, [boundary]);
  const template = document.createElement('template'); template.innerHTML = pages.map(page => page.html).join(''); expect(template.content.querySelectorAll('tr')).toHaveLength(2);
});

test.each([
  ['row interior', '<table><tr><td>cell words</td></tr></table>', { offset: 4, media: 0 }],
  ['rowspan boundary', '<table><tbody><tr><td rowspan="2">shared</td><td>one</td></tr><tr><td>two</td></tr></tbody></table>', { offset: 9, media: 0 }],
  ['figure caption interior', '<figure><img src="/one"><figcaption>caption words</figcaption></figure>', { offset: 4, media: 1 }],
  ['figure media interior', '<figure><img src="/one"><img src="/two"></figure>', { offset: 0, media: 1 }],
])('unsafe structural seam fails before output: %s', (_name, html, seam) => {
  expect(() => seamRun(html, [seam], 40)).toThrow(/crosses.*row|figure/);
});

test('BR/HR and original nested source ordinal survive once', () => {
  const { source, pages } = seamRun('<section><p>first<br><strong>second</strong><br>tail</p><hr><p>end</p></section>', [{ offset: 5, media: 0 }], 14);
  expectSeamIntegrity(source, pages, [{ offset: 5, media: 0 }]);
  const template = document.createElement('template'); template.innerHTML = pages.map(page => page.html).join('');
  expect(template.content.querySelectorAll('br')).toHaveLength(2); expect(template.content.querySelectorAll('hr')).toHaveLength(1);
  expect(pages.flatMap(page => page.structures).every(anchor => anchor === 'node:0')).toBe(true);
});

test('decoded image intrinsics survive source partition cloning', () => {
  const source = document.createElement('div'); source.innerHTML = '<figure><img src="/art"></figure><p>tail</p>';
  Object.defineProperties(source.querySelector('img'), { naturalWidth: { value: 640 }, naturalHeight: { value: 480 } });
  const measure = document.createElement('div'); const pages = paginateRendered(source, measure, 100, () => true, { pageBreaks: [{ offset: 0, media: 1 }] });
  const template = document.createElement('template'); template.innerHTML = pages[0].html; const image = template.content.querySelector('img');
  expect(image.dataset.readerIntrinsicWidth).toBe('640'); expect(image.dataset.readerIntrinsicHeight).toBe('480'); expect(image.getAttribute('width')).toBe('640'); expect(image.getAttribute('height')).toBe('480');
});

test.each([
  ['nodes', { nodes: 2 }], ['text', { textCharacters: 2 }], ['depth', { depth: 1 }], ['work', { workUnits: 2 }], ['seams', { seams: 1 }],
])('preprocessing %s budget fails without source mutation', (_name, preprocessingLimits) => {
  const source = document.createElement('div'); source.innerHTML = '<section><p>one two three four</p></section>'; const before = source.innerHTML;
  expect(() => paginateRendered(source, document.createElement('div'), 100, () => true, { pageBreaks: [{ offset: 4, media: 0 }, { offset: 8, media: 0 }], preprocessingLimits })).toThrow(/budget/);
  expect(source.innerHTML).toBe(before);
});

test('cancellation interrupts yielded preflight before cloning', async () => {
  const source = document.createElement('div'); source.innerHTML = '<p>' + 'one two '.repeat(20) + '</p>'; const measure = document.createElement('div'); let cancelled = false; let enteredClone = false; let ticks = 0;
  await expect(paginateRenderedResponsive(source, measure, 100, { pageBreaks: [{ offset: 8, media: 0 }], fits: () => true, clock: () => ticks += 9, schedule: resume => { cancelled = true; setTimeout(resume, 0); }, cancelled: () => cancelled, onPreprocessingStats: stats => { enteredClone ||= stats.enteredClone; } })).rejects.toMatchObject({ name: 'AbortError' });
  expect(enteredClone).toBe(false); expect(measure.childNodes).toHaveLength(0);
});

test('responsive seams equal synchronous ranges and preserve yielded text', async () => {
  const source = document.createElement('div'); source.innerHTML = '<p>' + 'one two three four '.repeat(30) + '</p>'; const measure = document.createElement('div'); const pageBreaks = [{ offset: 80, media: 0 }]; const fits = () => measure.textContent.length <= 80; let ticks = 0; let yields = 0;
  const expected = paginateRendered(source, measure, 100, fits, { pageBreaks });
  const actual = await paginateRenderedResponsive(source, measure, 100, { pageBreaks, fits, clock: () => ticks += 9, schedule: resume => { yields++; setTimeout(resume, 0); } });
  expect(actual).toEqual(expected); expect(yields).toBeGreaterThan(0); expectSeamIntegrity(source, actual, pageBreaks);
});

test.each([["scientific-next-failure-diagnosis-v2.json", "<p data-reader-source-node=\"84\">has reached his highest state of efficiency; that is, when he is turning</p>\n<p data-reader-source-node=\"86\">out his largest daily output.</p>\n<p data-reader-source-node=\"88\">The truth of this fact is also perfectly clear in the case of two men</p>\n<p data-reader-source-node=\"90\">working together. To illustrate: if you and your workman have become so</p>\n<p data-reader-source-node=\"92\">skilful that you and he together are making two pairs of, shoes in a</p>\n<p data-reader-source-node=\"94\">day, while your competitor and his workman are making only one pair, it</p>\n<p data-reader-source-node=\"96\">is clear that after selling your two pairs of shoes you can pay your</p><p data-reader-source-node=\"97\">workman much higher wages than your competitor who produces only one</p>\n<p data-reader-source-node=\"99\">pair of shoes is able to pay his man, and that there will still be</p>\n<p data-reader-source-node=\"101\">enough money left over for you to have a larger profit than your</p>\n<p data-reader-source-node=\"103\">competitor.</p>\n<p data-reader-source-node=\"105\">In the case of a more complicated manufacturing establishment, it should</p>\n<p data-reader-source-node=\"107\">also be perfectly clear that the greatest permanent prosperity for the</p>\n<p data-reader-source-node=\"109\">workman, coupled with the greatest prosperity for the employer, can be</p>\n", 454], ["my-life-next-failure-diagnosis.json", "<p data-reader-source-node=\"278\">expect that, if everything be overturned, everyone will thereby get</p>\n<p data-reader-source-node=\"280\">three meals a day. Or, should everything be petrified, that thereby six</p><p data-reader-source-node=\"281\">per cent, interest may be paid. The trouble is that reformers and</p>\n<p data-reader-source-node=\"283\">reactionaries alike get away from the realities--from the primary</p>\n<p data-reader-source-node=\"285\">functions.</p>\n<p data-reader-source-node=\"287\">One of the counsels of caution is to be very certain that we do not</p>\n<p data-reader-source-node=\"289\">mistake a reactionary turn for a return of common sense. We have passed</p>\n<p data-reader-source-node=\"291\">through a period of fireworks of every description, and the making of a</p>\n<p data-reader-source-node=\"293\">great many idealistic maps of progress. We did not get anywhere. It was</p>\n<p data-reader-source-node=\"295\">a convention, not a march. Lovely things were said, but when we got home</p>\n<p data-reader-source-node=\"297\">we found the furnace out. Reactionaries have frequently taken advantage</p>\n<p data-reader-source-node=\"299\">of the recoil from such a period, and they have promised \"the good old</p>\n<p data-reader-source-node=\"301\">times\"--which usually means the bad old abuses--and because they are</p>\n<p data-reader-source-node=\"303\">perfectly void of vision they are sometimes regarded as \"practical men.\"</p>\n", 139]])('observed forward fragment starts exactly at public/protected seam: %s', (_name, html, offset) => { const boundary = { offset, media: 0 }; const { source, pages } = seamRun(html, [boundary], 500); expectSeamIntegrity(source, pages, [boundary]); expect(pages[pageForAnchor(pages, offset)].start).toBe(offset); });

test('successful preflight reports entry into cloning so cancellation evidence is nonvacuous', () => {
  const stats = []; seamRun('<p>one two three four</p>', [{ offset: 4, media: 0 }], 20, { onPreprocessingStats: value => stats.push(value) });
  expect(stats.some(value => value.enteredClone === true)).toBe(true);
});
