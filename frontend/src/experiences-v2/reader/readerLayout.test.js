import fs from 'fs';
import path from 'path';
import postcss from 'postcss';

const stylesheet = postcss.parse(fs.readFileSync(path.join(__dirname, 'reader-v2.css'), 'utf8'));
function desktopDeclaration(selector, property) {
  let value;
  stylesheet.walkRules(selector, (rule) => {
    if (rule.parent.type !== 'root') return;
    rule.walkDecls(property, (declaration) => { value = declaration.value; });
  });
  return value;
}

describe('Reader reading measure and cover layout', () => {
  test('the desktop center track owns the reading measure, without a second prose inset', () => {
    expect(desktopDeclaration('.reader-v2__layout', 'grid-template-columns')).toBe('minmax(14rem, 17rem) minmax(0, 48rem) minmax(11rem, 13rem)');
    expect(desktopDeclaration('.reader-v2__body', 'inline-size')).toBe('100%');
    expect(desktopDeclaration('.reader-v2__body', 'margin')).toBe('24px 0');
    expect(desktopDeclaration('.reader-v2__body p', 'text-indent')).toBe('0');
  });
  test('the cover uses its own portrait aspect ratio rather than stretching to the full chapter height', () => {
    expect(desktopDeclaration('.reader-v2__book-cover', 'height')).toBe('auto');
    expect(desktopDeclaration('.reader-v2__book-cover', 'aspect-ratio')).toBe('2 / 3');
    expect(desktopDeclaration('.reader-v2__book-cover .book-cover-image__img', 'object-fit')).toBe('contain');
  });
});
