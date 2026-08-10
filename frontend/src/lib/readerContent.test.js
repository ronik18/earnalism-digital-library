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

test('reflows source-width line wrapping without changing the prose order', () => {
  const source = [
    '(_Kept in shorthand._)',
    '_3 May. Bistritz._--Left Munich at 8:35 P. M., on 1st May, arriving at',
    'Vienna early next morning; should have arrived at 6:46, but train was an',
    'hour late. Buda-Pesth seems a wonderful place, from the glimpse which I',
    'got of it from the train and the little I could walk through the',
    'streets. I feared to go very far from the station, as we had arrived',
    'late and would start as near the correct time as possible. The',
    'impression I had was that we were leaving the West and entering the',
    'East; the most western of splendid bridges over the Danube, which is',
    'here of noble width and depth, took us among the traditions of Turkish',
    'rule.',
    'We left in pretty good time, and came after nightfall to Klausenburgh.',
  ].join('\n\n');

  expect(normalizeReaderContentHtml(source)).toBe(
    '<p>(_Kept in shorthand._)</p>'
      + '<p>_3 May. Bistritz._--Left Munich at 8:35 P. M., on 1st May, arriving at Vienna early next morning; should have arrived at 6:46, but train was an hour late. Buda-Pesth seems a wonderful place, from the glimpse which I got of it from the train and the little I could walk through the streets. I feared to go very far from the station, as we had arrived late and would start as near the correct time as possible. The impression I had was that we were leaving the West and entering the East; the most western of splendid bridges over the Danube, which is here of noble width and depth, took us among the traditions of Turkish rule.</p>'
      + '<p>We left in pretty good time, and came after nightfall to Klausenburgh.</p>',
  );
});

test('reflows production HTML line fragments while preserving inline markup', () => {
  const source = [
    '<p><em>3 May. Bistritz.</em>--Left Munich at 8:35 P. M., arriving at</p>',
    '<p>Vienna early next morning; should have arrived at 6:46, but train was an</p>',
    '<p>hour late. Buda-Pesth seems a wonderful place, from the glimpse which I</p>',
    '<p>got of it from the train and the little I could walk through the</p>',
    '<p>streets. I feared to go very far from the station, as we had arrived</p>',
    '<p>late and would start as near the correct time as possible. The</p>',
    '<p>impression I had was that we were leaving the West and entering the</p>',
    '<p>East; the most western of splendid bridges over the Danube, which is</p>',
    '<p>here of noble width and depth, took us among the traditions of Turkish</p>',
    '<p>rule.</p>',
    '<p>We left in pretty good time, and came after nightfall to Klausenburgh.</p>',
  ].join('');

  expect(normalizeReaderContentHtml(source)).toBe(
    '<p><em>3 May. Bistritz.</em>--Left Munich at 8:35 P. M., arriving at Vienna early next morning; should have arrived at 6:46, but train was an hour late. Buda-Pesth seems a wonderful place, from the glimpse which I got of it from the train and the little I could walk through the streets. I feared to go very far from the station, as we had arrived late and would start as near the correct time as possible. The impression I had was that we were leaving the West and entering the East; the most western of splendid bridges over the Danube, which is here of noble width and depth, took us among the traditions of Turkish rule.</p>'
      + '<p>We left in pretty good time, and came after nightfall to Klausenburgh.</p>',
  );
});

test('does not collapse normal short-form paragraphs', () => {
  const source = [
    'One.',
    'Two.',
    'Three.',
    'Four.',
    'Five.',
    'Six.',
  ].join('\n\n');

  expect(normalizeReaderContentHtml(source)).toBe(
    '<p>One.</p><p>Two.</p><p>Three.</p><p>Four.</p><p>Five.</p><p>Six.</p>',
  );
});

test('does not collapse genuine long HTML paragraphs', () => {
  const paragraphs = Array.from({ length: 6 }, (_, index) => (
    `<p>Paragraph ${index + 1} is intentionally longer than a source-width line and represents a complete semantic paragraph with its own stable beginning and ending.</p>`
  ));
  const source = paragraphs.join('');

  expect(normalizeReaderContentHtml(source)).toBe(source);
});
