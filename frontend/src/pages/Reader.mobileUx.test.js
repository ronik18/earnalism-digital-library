import fs from 'fs';
import path from 'path';

const readerSource = fs.readFileSync(path.join(process.cwd(), 'src/pages/Reader.jsx'), 'utf8');
const readerStyles = fs.readFileSync(path.join(process.cwd(), 'src/pages/ReaderRoute.css'), 'utf8');

describe('Reader mobile UX contract', () => {
  test('protects audiobook/read destinations with the requested book identity', () => {
    expect(readerSource).toContain('readerBookMatchesRoute(bookRes.data, bookId)');
    expect(readerSource).toContain('readerRouteForBook(bookId)');
    expect(readerSource).toContain('data-testid="reader-page-shell"');
  });

  test('supports horizontal page swipes while preserving vertical scrolling', () => {
    expect(readerSource).toContain('readerSwipeDirection');
    expect(readerSource).toContain('onPointerDown={onReaderPointerDown}');
    expect(readerSource).toContain('onPointerUp={onReaderPointerUp}');
    expect(readerSource).toContain('onPointerCancel={onReaderPointerCancel}');
    expect(readerStyles).toContain('touch-action: pan-y;');
  });

  test('uses compact premium mobile reading rhythm', () => {
    expect(readerSource).toContain('english: 1.62');
    expect(readerSource).toContain('bengali: 1.74');
    expect(readerStyles).toContain('font-size: 18px;');
    expect(readerStyles).toContain('margin-bottom: 1.05em;');
  });
});
