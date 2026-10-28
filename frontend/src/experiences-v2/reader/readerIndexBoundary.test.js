import { readerIndexBoundary, readerSourceText } from './readerContent';
test('index anchor derives from the exact authorized source without editing its text', () => {
  const html = '<p>The book ends.</p><p>INDEX</p><p>Work, the right to</p>';
  const original = readerSourceText(html);
  expect(readerIndexBoundary(html)).toEqual({ title: 'Index', offset: 'The book ends.'.length });
  expect(readerSourceText(html)).toBe(original);
  expect(html).toBe('<p>The book ends.</p><p>INDEX</p><p>Work, the right to</p>');
});
test('prose mentions of an index and discarded script cannot create an index boundary', () => {
  expect(readerIndexBoundary('<p>The index can help.</p><script>INDEX</script>')).toBeNull();
});
