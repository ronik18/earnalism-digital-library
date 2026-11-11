import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import fs from 'fs';
import path from 'path';
import { ReaderContent, ReaderContentLayout, readerSourceText } from './readerContent';
import { reflowLegacyProse } from './proseReflow';
import { paginateRendered, sliceBlock } from './visualPagination';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const roots = [];
afterEach(() => roots.splice(0).forEach(root => act(() => root.unmount())));
function render(html, props = {}) {
  const container = document.createElement('div');
  const root = createRoot(container); roots.push(root);
  act(() => root.render(<ReaderContent html={html} {...props} />));
  return container;
}
function legacyHtml(content) {
  return content.trim().split(/\n{2,}/).map(line => `<p>${line.trim().replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/\n/g, '<br>')}</p>`).join('');
}
const source = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../../../backend/data/controlled_publications/the-selfish-giant/chapters/chapter-001.json'), 'utf8')).content;
const html = legacyHtml(source);
test('real Selfish Giant source reflows lines, retaining approved characters and paragraph stops', () => {
  const container = render(html);
  expect(container.textContent).toBe(readerSourceText(html));
  const paragraph = [...container.querySelectorAll('p')].find(p => p.textContent.startsWith('The poor children'));
  expect(paragraph.textContent).toContain('play on theroad');
  expect(paragraph.textContent).toContain('their lessonswere over');
  expect([...container.querySelectorAll('p')].some(p => p.textContent.includes('invited theNorth Wind'))).toBe(true);
  expect([...container.querySelectorAll('p')].some(p => p.textContent.includes('which isParadise'))).toBe(true);
  expect(container.querySelectorAll('.reader-v2__soft-wrap').length).toBeGreaterThan(70);
  expect([...container.querySelectorAll('p')].some(p => p.textContent === 'He was a very selfish Giant.')).toBe(true);
});
test('projected pages reconstruct canonical offsets across page and seam cuts', () => {
  const container = render(html);
  for (const capacity of [90, 180, 450]) {
    const measure = document.createElement('div');
    const pages = paginateRendered(container, measure, 100, () => measure.textContent.length <= capacity);
    expect(pages.map(page => page.text).join('')).toBe(readerSourceText(html));
    expect(pages.every((page, i) => !i || page.start === pages[i - 1].end)).toBe(true);
  }
  const block = [...container.querySelectorAll('p')].find(p => p.querySelector('.reader-v2__soft-wrap'));
  for (let offset = 1; offset < block.textContent.length; offset++) {
    expect(sliceBlock(block, 0, offset).textContent + sliceBlock(block, offset, block.textContent.length).textContent).toBe(block.textContent);
  }
});
test.each(['poetry', 'Bengali Poetry', 'কবিতা'])('genre %s preserves long lowercase verse', genre => {
  expect(render(html, { genre }).querySelector('.reader-v2__soft-wrap')).toBeNull();
});
test.each(['verse', 'preserve'])('explicit layout %s overrides inference', layout => {
  expect(render(html, { layout }).querySelector('.reader-v2__soft-wrap')).toBeNull();
});
test.each(['pre', 'code', 'blockquote', 'ul', 'ol', 'section class="poetry"', 'div data-reader-layout="verse"'])('preserves structured %s', wrapper => {
  const tag = wrapper.split(' ')[0];
  const container = render(`<${wrapper}>${html}</${tag}>`);
  expect(container.querySelector('.reader-v2__soft-wrap')).toBeNull();
});
test('ordinary paragraphs, dialogue, short verse, Bengali stanzas and headings stay intact', () => {
  const raw = '<p>A complete paragraph.</p><p>another intentionally separate paragraph.</p><h2>A heading</h2><p>“A new speaker,” she said.</p><p>“Another speaker.”</p><p>the quiet moon<br>above the trees<br><br>আরেকটি স্তবক<br>রাত্রির আলো</p><pre>  code\n    stays</pre>';
  const container = render(raw);
  expect(container.querySelector('.reader-v2__soft-wrap')).toBeNull();
  expect(container.querySelectorAll('p')).toHaveLength(5);
  expect(container.querySelectorAll('br')).toHaveLength(4);
  expect(container.querySelector('pre').textContent).toBe('  code\n    stays');
});
test('single-newline BR imports use the same protection without modifying text', () => {
  const raw = '<p>' + source.trim().split(/\n{2,}/).map(s => s.trim()).join('<br>') + '</p>';
  const container = render(raw);
  expect(container.querySelectorAll('.reader-v2__soft-wrap').length).toBeGreaterThan(70);
  expect(container.textContent).toBe(readerSourceText(raw));
  expect(container.querySelector('br')).not.toBeNull();
});
test('nested emphasis and inter-paragraph whitespace retain coordinates', () => {
  const template = document.createElement('template'); template.innerHTML = html.replace('the children', '<em>the children</em>').replace(/<\/p><p>/g, '</p>\n<p>');
  const before = template.content.textContent;
  reflowLegacyProse(template.content);
  expect(template.content.textContent).toBe(before);
  expect(template.content.querySelector('em').textContent).toBe('the children');
});

test('valid table cells retain all source line structure', () => {
  const container = render(`<table><tbody><tr><td>${html}</td></tr></tbody></table>`);
  expect(container.querySelector('.reader-v2__soft-wrap')).toBeNull();
});

test('all stored fixed-width catalogue packets retain canonical text under the shared projection', () => {
  const catalogue = path.resolve(__dirname, '../../../../backend/data/controlled_publications');
  let affectedTitles = 0; let checkedChapters = 0;
  for (const slug of fs.readdirSync(catalogue)) {
    const directory = path.join(catalogue, slug);
    if (!fs.existsSync(path.join(directory, 'public_book.json')) || !fs.existsSync(path.join(directory, 'chapters'))) continue;
    const book = JSON.parse(fs.readFileSync(path.join(directory, 'public_book.json'), 'utf8'));
    let affected = false;
    for (const file of fs.readdirSync(path.join(directory, 'chapters')).filter(name => name.endsWith('.json'))) {
      const content = JSON.parse(fs.readFileSync(path.join(directory, 'chapters', file), 'utf8')).content || '';
      if (/<\/?[a-z][^>]*>/i.test(content)) continue;
      const raw = legacyHtml(content);
      const template = document.createElement('template'); template.innerHTML = raw;
      const before = template.content.textContent;
      reflowLegacyProse(template.content, { genre: book.genre || book.category_slug || '', layout: book.reader_layout || '' });
      expect(template.content.textContent).toBe(before);
      affected ||= Boolean(template.content.querySelector('.reader-v2__soft-wrap'));
      checkedChapters++;
    }
    if (affected) affectedTitles++;
  }
  expect(checkedChapters).toBeGreaterThan(200);
  expect(affectedTitles).toBeGreaterThan(60);
});

test('the Reader layout context protects poetry in foreground and background projections', () => {
  const container = document.createElement('div');
  const root = createRoot(container); roots.push(root);
  act(() => root.render(<ReaderContentLayout.Provider value={{ genre: 'Poetry' }}><ReaderContent html={html} /><ReaderContent html={html} /></ReaderContentLayout.Provider>));
  expect(container.querySelector('.reader-v2__soft-wrap')).toBeNull();
  expect(container.textContent).toBe(readerSourceText(html).repeat(2));
});
