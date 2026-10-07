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
  // A Range beginning at the end of a paragraph can clone an empty paragraph
  // before the next actual word. It must not consume a phantom line. Unwrap
  // formatting whitespace rather than deleting source characters.
  for (const node of [...clone.querySelectorAll('p,h1,h2,h3,h4,h5,h6,pre,blockquote')].reverse()) {
    if (!node.textContent.trim() && !node.querySelector('img,br,hr')) node.replaceWith(...node.childNodes);
  }
  if (start) clone.setAttribute('data-reader-continuation', 'true');
  return clone;
}

export function sliceTableRows(block, start, end) {
  const rows = [...block.querySelectorAll('tr')];
  const range = document.createRange();
  if (start === 0) range.setStart(block, 0); else range.setStartBefore(rows[start]);
  if (end === rows.length) range.setEnd(block, block.childNodes.length); else range.setEndBefore(rows[end]);
  let contents = range.cloneContents();
  let ancestor = range.commonAncestorContainer;
  while (ancestor !== block) {
    const envelope = ancestor.cloneNode(false);
    envelope.append(contents); contents = envelope; ancestor = ancestor.parentNode;
  }
  const fragment = block.cloneNode(false); fragment.append(contents);
  return fragment;
}

// An indivisible tall row has an explicit linear, accessible alternative.
// Cell order and text are unchanged; columns are identified semantically.
export function linearTable(block) {
  const clone = block.cloneNode(true);
  const table = clone.matches('table') ? clone : clone.querySelector('table');
  const convert = node => {
    if (node.nodeType !== Node.ELEMENT_NODE) return node.cloneNode(true);
    const roles = { TABLE: 'table', THEAD: 'rowgroup', TBODY: 'rowgroup', TFOOT: 'rowgroup', TR: 'row', TH: 'columnheader', TD: 'cell', CAPTION: 'caption' };
    if (!roles[node.tagName]) return node.cloneNode(true);
    const value = document.createElement('div'); value.setAttribute('role', roles[node.tagName]);
    if (node.tagName === 'TABLE') { value.className = 'reader-v2__linear-table'; value.setAttribute('aria-label', 'Table displayed as sequential cells to fit this page'); }
    if (/^(TD|TH)$/.test(node.tagName)) value.setAttribute('aria-colindex', String([...node.parentNode.children].indexOf(node) + 1));
    for (const child of node.childNodes) value.append(convert(child));
    return value;
  };
  const alternative = convert(table);
  if (table === clone) return alternative;
  table.replaceWith(alternative); return clone;
}

function fittedMedia(block, measure, height, fits) {
  const clone = block.cloneNode(true);
  const images = [...(block.matches('img') ? [block] : block.querySelectorAll('img'))];
  const copies = [...(clone.matches('img') ? [clone] : clone.querySelectorAll('img'))];
  const intrinsicWidth = images[0]?.naturalWidth || Number(images[0]?.dataset.readerIntrinsicWidth);
  const intrinsicHeight = images[0]?.naturalHeight || Number(images[0]?.dataset.readerIntrinsicHeight);
  if (images.length !== 1 || !(intrinsicWidth > 0) || !(intrinsicHeight > 0)) return null;
  const image = copies[0];
  image.style.height = '0px'; image.style.width = '0px';
  measure.replaceChildren(clone);
  const available = Math.floor(height - measure.scrollHeight - 2);
  if (available < 24) return null;
  const scale = Math.min(1, measure.clientWidth / intrinsicWidth, available / intrinsicHeight);
  image.style.width = `${Math.floor(intrinsicWidth * scale)}px`;
  image.style.height = `${Math.floor(intrinsicHeight * scale)}px`;
  image.style.maxHeight = 'none'; image.style.objectFit = 'contain';
  return fits() ? clone : null;
}

export function pageForAnchor(pages, offset) {
  if (typeof offset === 'string' && /^media:\d+$/.test(offset)) return Math.max(0, pages.findIndex(page => page.media?.includes(Number(offset.split(':')[1]))));
  if (typeof offset === 'string' && /^node:\d+$/.test(offset)) return Math.max(0, pages.findIndex(page => page.structures?.includes(offset)));
  return Math.max(0, pages.findIndex((page, index) => offset >= page.start
    && (offset < page.end || index === pages.length - 1)));
}

// A provided fit predicate is useful for invariant tests; production measures DOM.
function* paginationSteps(source, measure, height, fits = () => measure.scrollHeight <= height + 1) {
  if (height < 24) throw new PaginationIntegrityError('The reading area cannot fit a readable line.');
  const pages = []; let offset = 0; let pageStart = 0; let prefix = '';
  measure.replaceChildren(); measure.removeAttribute('data-continuation');
  const finish = () => {
    if (!measure.childNodes.length) return;
    // Formatting-only text nodes must not acquire paragraph margins or become
    // blank visual pages. Preserve every character and its source offset.
    if ([...measure.childNodes].every(node => node.nodeType === Node.TEXT_NODE && !node.textContent.trim())) {
      const whitespace = measure.textContent;
      if (pages.length) {
        const previous = pages[pages.length - 1];
        previous.html += whitespace; previous.text += whitespace; previous.end = offset;
        pageStart = offset;
      } else prefix += whitespace;
      measure.replaceChildren();
      return;
    }
    const structures = [...measure.querySelectorAll('[data-reader-source-node]')].map(node => `node:${node.dataset.readerSourceNode}`);
    const media = [...measure.querySelectorAll('[data-reader-source-media]')].map(node => Number(node.dataset.readerSourceMedia));
    pages.push({ html: prefix + measure.innerHTML, text: prefix + measure.textContent, start: pageStart, end: offset, structures, media, anchor: !measure.textContent.trim() ? (media.length ? `media:${media[0]}` : structures[0]) : pageStart });
    prefix = '';
    measure.replaceChildren(); pageStart = offset; measure.setAttribute('data-continuation', 'true');
  };
  let mediaOrdinal = 0;
  const blocks = [...source.childNodes].map(node => {
    const clone = node.cloneNode(true);
    const images = clone.nodeType === Node.ELEMENT_NODE ? [...(clone.matches('img') ? [clone] : clone.querySelectorAll('img'))] : [];
    const originals = node.nodeType === Node.ELEMENT_NODE ? [...(node.matches('img') ? [node] : node.querySelectorAll('img'))] : [];
    images.forEach((image, ordinal) => {
      image.setAttribute('data-reader-source-media', String(mediaOrdinal++));
      // Source images have decoded before pagination. A new clone may not have
      // decoded yet (especially with a cold/disabled image cache). Reserve its
      // intrinsic geometry before any synchronous height measurement.
      const original = originals[ordinal];
      if (original?.naturalWidth > 0 && original?.naturalHeight > 0) {
        image.dataset.readerIntrinsicWidth = String(original.naturalWidth);
        image.dataset.readerIntrinsicHeight = String(original.naturalHeight);
        if (!image.hasAttribute('width')) image.setAttribute('width', String(original.naturalWidth));
        if (!image.hasAttribute('height')) image.setAttribute('height', String(original.naturalHeight));
      }
    });
    return clone;
  });
  for (let index = 0; index < blocks.length; index++) {
    yield;
    let block = blocks[index];
    if (block.nodeType === Node.TEXT_NODE && !block.textContent.trim()) {
      measure.append(block.cloneNode(true)); offset += block.textContent.length;
      continue;
    }
    if (block.nodeType === Node.TEXT_NODE) {
      const paragraph = document.createElement('p'); paragraph.textContent = block.textContent; block = paragraph;
    }
    if (block.nodeType !== Node.ELEMENT_NODE) continue;
    block = block.cloneNode(true);
    block.setAttribute('data-reader-source-node', String(index));
    const whole = block.cloneNode(true);
    measure.append(whole);
    // Prefer headings with the next block if the pair fits on an empty page.
    let next = blocks[index + 1];
    if (/^H[1-6]$/.test(block.tagName)) {
      let followingIndex = index + 1;
      while (next?.nodeType === Node.TEXT_NODE && !next.textContent.trim()) next = blocks[++followingIndex];
    }
    if (/^H[1-6]$/.test(block.tagName) && next && measure.childNodes.length > 1) {
      const following = next.cloneNode(true); measure.append(following);
      const pairFits = fits(); following.remove();
      if (!pairFits) { whole.remove(); finish(); measure.append(whole); }
    }
    if (fits()) { offset += block.textContent.length; continue; }
    whole.remove();
    finish();
    measure.append(whole);
    if (fits()) { offset += block.textContent.length; continue; }
    whole.remove();
    if (block.matches('img,figure') || block.querySelector('img')) {
      const media = fittedMedia(block, measure, height, fits);
      if (media) { offset += block.textContent.length; continue; }
      measure.replaceChildren();
    }
    const table = block.matches('table') ? block : block.querySelector('table');
    if (table && !block.querySelector('img,video,audio') && !table.querySelector('[rowspan]:not([rowspan="1"])')) {
      const rows = [...block.querySelectorAll('tr')];
      if (rows.length > 1) {
        const needsAlternative = rows.some((_, row) => {
          measure.replaceChildren(sliceTableRows(block, row, row + 1));
          return !fits();
        });
        measure.replaceChildren();
        if (needsAlternative) { blocks[index] = linearTable(block); index--; continue; }
        let start = 0;
        while (start < rows.length) {
          let low = start + 1; let high = rows.length; let best = start;
          while (low <= high) {
            const middle = Math.floor((low + high) / 2);
            measure.replaceChildren(sliceTableRows(block, start, middle));
            if (fits()) { best = middle; low = middle + 1; } else high = middle - 1;
          }
          if (best === start) throw new PaginationIntegrityError('An individual table row exceeds this layout.');
          const fragment = sliceTableRows(block, start, best);
          measure.replaceChildren(fragment); offset += fragment.textContent.length;
          start = best;
          if (start < rows.length) { finish(); yield; }
        }
        continue;
      }
    }
    if (table) { measure.replaceChildren(); blocks[index] = linearTable(block); index--; continue; }
    // Preserve rich inline markup with DOM Ranges. Binary search word boundaries.
    const boundaries = textBoundaries(block.textContent);
    if (boundaries.length < 2 || (block.matches('img,svg,table,video,audio') || block.querySelector('img,svg,table,video,audio'))) {
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
      if (best === startIndex) {
        measure.replaceChildren(sliceBlock(block, boundaries[startIndex], boundaries[startIndex + 1]));
        throw new PaginationIntegrityError(`An indivisible word or ${block.tagName.toLowerCase()} structure exceeds this layout (${measure.scrollHeight}px for ${height}px; ${measure.querySelectorAll("br").length} breaks; ${measure.textContent.length} chars).`);
      }
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
      if (startIndex < boundaries.length - 1) { finish(); yield; }
    }
  }
  finish();
  if (!pages.length) pages.push({ html: prefix, text: prefix, start: 0, end: offset });
  // Text offsets cannot distinguish several image-only pages. Reject this
  // invalid structural map before paint rather than repeat or skip artwork.
  if (pages.some(page => page.start === page.end && page.html && !page.structures?.length)) {
    throw new PaginationIntegrityError('A media-only page requires a structural source anchor.');
  }
  const reconstructedMedia = pages.flatMap(page => page.media || []);
  if (reconstructedMedia.length !== mediaOrdinal || reconstructedMedia.some((ordinal, index) => ordinal !== index)) {
    throw new PaginationIntegrityError('Pagination did not reconstruct source media exactly.');
  }
  if (pages.map(page => page.text).join('') !== source.textContent) {
    throw new PaginationIntegrityError('Pagination did not reconstruct the source exactly.');
  }
  return pages;
}

export function paginateRendered(source, measure, height, fits) {
  const steps = paginationSteps(source, measure, height, fits);
  let step = steps.next();
  while (!step.done) step = steps.next();
  return step.value;
}

// Fast layouts finish synchronously. Long layouts yield the main thread in
// bounded slices; yielding is calculation work, never an animation delay.
export function paginateRenderedResponsive(source, measure, height, options = {}) {
  const steps = paginationSteps(source, measure, height, options.fits);
  const clock = options.clock || (() => performance.now());
  const schedule = options.schedule || (resume => setTimeout(resume, 0));
  const advance = () => {
    const started = clock();
    while (true) {
      if (options.cancelled?.()) throw new DOMException('Pagination superseded', 'AbortError');
      const step = steps.next();
      if (step.done) return step.value;
      if (clock() - started >= 8) return new Promise((resolve, reject) => schedule(() => {
        try { resolve(advance()); } catch (error) { reject(error); }
      }));
    }
  };
  return advance();
}
