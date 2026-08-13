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
    expect(readerSource).toContain("currentPageData?.contentIndex === 0");
    expect(readerSource).toContain("/^[A-Za-z\\u0980-\\u09FF]/.test(firstParagraphText(currentPageHtml))");
    expect(readerSource).toContain("useReaderDropCap ? 'reader-content--dropcap' : ''");
  });

  test('keeps the reading page inside unobstructed mobile chrome', () => {
    expect(readerSource).toContain('Math.max(300, Math.min(780, window.innerHeight - 245))');
    expect(readerSource).toContain('window.innerHeight < 640 ? 0.58 : 0.72');
    expect(readerSource).toContain('Math.max(180, Math.min(520, Math.floor(limit * paragraphScale)))');
    expect(readerStyles).toContain('height: 100dvh;');
    expect(readerStyles).toContain('padding: calc(58px + 0.65rem) 0 calc(94px + 0.65rem);');
    expect(readerStyles).toContain('box-sizing: border-box;');
    expect(readerStyles).toContain('.reader-book-header,\n.reader-story-header {\n  display: none;');
    expect(readerStyles).toContain('min-height: 0;');
    expect(readerStyles).toContain('padding-bottom: calc(114px + 0.65rem);');
  });

  test('keeps mobile context visible and all primary reader controls touch safe', () => {
    expect(readerStyles).toContain('grid-template-columns: 44px minmax(0, 1fr) auto;');
    expect(readerStyles).toContain('.reader-topbar__center {\n    display: flex;');
    expect(readerStyles).not.toContain('.reader-topbar__center {\n    display: none;');
    expect(readerStyles).toContain('.reader-toc-item {\n  min-height: 44px;');
    expect(readerStyles).toContain('.reader-settings-reset {');
  });

  test('does not blur legitimate split-screen or embedded-reader layouts', () => {
    expect(readerSource).not.toContain('window.outerWidth - window.innerWidth');
    expect(readerSource).not.toContain('window.outerHeight - window.innerHeight');
    expect(readerSource).toContain('setContentBlurred(document.hidden)');
  });

  test('normalizes chapter labels consistently in both contents surfaces', () => {
    expect(readerSource).toContain('sortedChapterIndex(chapters)');
    expect(readerSource).toContain('chapterIndexEntry(item, index + 1, chapters.length)');
    expect(readerSource.match(/index_secondary_label/g).length).toBeGreaterThanOrEqual(2);
    expect(readerSource).toContain("isChapterIndexPage ? 'reader-page-shell--index' : ''");
    expect(readerSource).toContain('Font comfort');
    expect(readerSource).not.toContain('Bengali comfort');
  });
});
