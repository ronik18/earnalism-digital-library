// Input is the already-sanitized, rendered Reader DOM, never raw source HTML.
export class PaginationIntegrityError extends Error {}

export function textBoundaries(text) {
  const boundaries = [0];
  const words = /\S+\s*|\s+/gu;
  let match;
  while ((match = words.exec(text))) boundaries.push(match.index + match[0].length);
  return [...new Set([...boundaries, text.length])];
}

function textPoint(root, offset) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node; let consumed = 0; let last;
  while ((node = walker.nextNode())) {
    last = node;
    if (offset <= consumed + node.length) return [node, offset - consumed];
    consumed += node.length;
  }
  return last ? [last, last.length] : [root, 0];
}

export function sliceBlock(block, start, end) {
  const clone = block.cloneNode(false);
  const range = document.createRange();
  range.setStart(...textPoint(block, start));
  range.setEnd(...textPoint(block, end));
  clone.append(range.cloneContents());
  if (start) clone.setAttribute('data-reader-continuation', 'true');
  return clone;
}

export function pageForAnchor(pages, offset) {
  return Math.max(0, pages.findIndex((page, index) => offset >= page.start
    && (offset < page.end || index === pages.length - 1)));
}

// A provided fit predicate is useful for invariant tests; production measures DOM.
export function paginateRendered(source, measure, height, fits = () => measure.scrollHeight <= height + 1) {
  if (height < 24) throw new PaginationIntegrityError('The reading area cannot fit a readable line.');
  const pages = []; let offset = 0; let pageStart = 0;
  measure.replaceChildren(); measure.removeAttribute('data-continuation');
  const finish = () => {
    if (!measure.childNodes.length) return;
    pages.push({ html: measure.innerHTML, text: measure.textContent, start: pageStart, end: offset });
    measure.replaceChildren(); pageStart = offset; measure.setAttribute('data-continuation', 'true');
  };
  const blocks = [...source.childNodes];
  for (let index = 0; index < blocks.length; index++) {
    let block = blocks[index];
    if (block.nodeType === Node.TEXT_NODE) {
      const paragraph = document.createElement('p'); paragraph.textContent = block.textContent; block = paragraph;
    }
    if (block.nodeType !== Node.ELEMENT_NODE) continue;
    const whole = block.cloneNode(true);
    measure.append(whole);
    // Prefer headings with the next block if the pair fits on an empty page.
    const next = blocks[index + 1];
    if (/^H[1-6]$/.test(block.tagName) && next && measure.childNodes.length > 1) {
      const following = next.cloneNode(true); measure.append(following);
      const pairFits = fits(); following.remove();
      if (!pairFits) { whole.remove(); finish(); measure.append(whole); }
    }
    if (fits()) { offset += Math.max(1, block.textContent.length); continue; }
    whole.remove();
    finish();
    measure.append(whole);
    if (fits()) { offset += Math.max(1, block.textContent.length); continue; }
    whole.remove();
    // Preserve rich inline markup with DOM Ranges. Binary search word boundaries.
    const boundaries = textBoundaries(block.textContent);
    if (boundaries.length < 2 || block.querySelector('img,svg,table,video,audio')) {
      throw new PaginationIntegrityError('A structured block needs a supported pagination adapter.');
    }
    let startIndex = 0;
    while (startIndex < boundaries.length - 1) {
      let low = startIndex + 1; let high = boundaries.length - 1; let best = startIndex;
      while (low <= high) {
        const middle = Math.floor((low + high) / 2);
        measure.replaceChildren(sliceBlock(block, boundaries[startIndex], boundaries[middle]));
        if (fits()) { best = middle; low = middle + 1; } else high = middle - 1;
      }
      if (best === startIndex) throw new PaginationIntegrityError('An indivisible word or structure exceeds this layout.');
      // Prefer a sentence boundary without sacrificing most of the page.
      const candidate = block.textContent.slice(boundaries[startIndex], boundaries[best]);
      const sentences = [...candidate.matchAll(/[.!?।]\s+/gu)];
      const last = sentences[sentences.length - 1];
      if (best < boundaries.length - 1 && last && last.index > candidate.length * .8) {
        const sentenceEnd = boundaries[startIndex] + last.index + last[0].length;
        const sentenceIndex = boundaries.indexOf(sentenceEnd);
        if (sentenceIndex > startIndex) best = sentenceIndex;
      }
      if (best < boundaries.length - 1) {
        const lineHeight = parseFloat(getComputedStyle(measure).lineHeight);
        measure.replaceChildren(sliceBlock(block, boundaries[best], block.textContent.length));
        if (lineHeight > 0 && measure.scrollHeight < lineHeight * 1.8) {
          let left = startIndex + 1; let right = best - 1; let widowCut = best;
          while (left <= right) {
            const middle = Math.floor((left + right) / 2);
            measure.replaceChildren(sliceBlock(block, boundaries[middle], block.textContent.length));
            if (measure.scrollHeight >= lineHeight * 1.8) { widowCut = middle; left = middle + 1; }
            else right = middle - 1;
          }
          if (widowCut > startIndex) best = widowCut;
        }
      }
      measure.replaceChildren(sliceBlock(block, boundaries[startIndex], boundaries[best]));
      if (!fits()) throw new PaginationIntegrityError('Measured fragment exceeds its page.');
      offset += boundaries[best] - boundaries[startIndex];
      startIndex = best;
      if (startIndex < boundaries.length - 1) finish();
    }
  }
  finish();
  if (!pages.length) pages.push({ html: '', text: '', start: 0, end: 0 });
  if (pages.map(page => page.text).join('') !== source.textContent) {
    throw new PaginationIntegrityError('Pagination did not reconstruct the source exactly.');
  }
  return pages;
}
