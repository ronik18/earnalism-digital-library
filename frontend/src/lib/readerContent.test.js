import { normalizeReaderContentHtml } from './readerContent';

test('normalizes plain text into semantic paragraphs and preserves line breaks', () => {
  expect(normalizeReaderContentHtml('First paragraph.\n\nSecond line.\nStill second.'))
    .toBe('<p>First paragraph.</p><p>Second line.<br>Still second.</p>');
});

test('escapes plain text without rewriting existing markup', () => {
  expect(normalizeReaderContentHtml('5 < 6')).toBe('<p>5 &lt; 6</p>');
  expect(normalizeReaderContentHtml('<h2>Chapter</h2><p>Body</p>'))
    .toBe('<h2>Chapter</h2><p>Body</p>');
});
