// Presentation projection only: never rewrite the authorized HTML, its hashes,
// textContent or source coordinates. Legacy imports promoted fixed-width source
// lines to paragraphs (or BRs). Recover only high-confidence prose continuations.
const PRESERVE = 'pre,code,blockquote,ul,ol,dl,table,figure,.poem,.poetry,.verse,.stanza,[data-poetry],[data-verse],[data-reader-layout="verse"],[data-reader-layout="preserve"]';
const INLINE_ONLY = 'br,img,hr,pre,code,blockquote,ul,ol,dl,table,figure,p,div,section,article,h1,h2,h3,h4,h5,h6';
const fixedWidth = text => text.trim().length >= 45 && text.trim().length <= 90;
const continuation = (left, right) => fixedWidth(left)
  && !/[.!?。！？।॥:;][”’"')\]]*$/u.test(left.trim())
  && /^\p{L}/u.test(right.trim());

function signature(lines) {
  // Short/ambiguous fragments and ordinary paragraphs are left alone. Requiring
  // several lowercase mid-sentence continuations avoids guessing from width alone.
  return lines.length >= 8 && lines.filter(fixedWidth).length / lines.length >= .65
    && lines.slice(1).filter((line, index) => continuation(lines[index], line) && /^\p{Ll}/u.test(line.trim())).length >= 4;
}

function seam() {
  const node = document.createElement('span');
  node.className = 'reader-v2__soft-wrap';
  node.dataset.readerSoftWrap = 'true';
  // A generated collapsible space supplies visual/AT word separation without
  // inventing a canonical character and shifting protected transport offsets.
  return node;
}

export function reflowLegacyProse(fragment, { genre = '', layout = '' } = {}) {
  if (/poetry|poem|verse|কবিতা/i.test(genre) || /^(verse|preserve)$/i.test(layout)) return fragment;
  // Work in each ordinary container independently; never cross a heading,
  // quotation, explicit literary block or other structural boundary.
  const containers = [fragment, ...fragment.querySelectorAll('div,section,article')];
  for (const parent of containers) {
    if (parent.nodeType === 1 && parent.closest(PRESERVE)) continue;
    const paragraphs = [...parent.children].filter(node => node.tagName === 'P'
      && !node.closest(PRESERVE) && !node.querySelector(INLINE_ONLY));
    if (signature(paragraphs.map(node => node.textContent))) {
      let previous = null; let lastLine = '';
      for (const paragraph of paragraphs) {
        const text = paragraph.textContent;
        const between = []; let node = previous?.nextSibling;
        while (node && node !== paragraph && node.nodeType === 3 && !node.textContent.trim()) { between.push(node); node = node.nextSibling; }
        if (previous && node === paragraph && continuation(lastLine, text)) {
          previous.append(...between, seam(), ...paragraph.childNodes);
          paragraph.remove();
        } else previous = paragraph;
        lastLine = text;
      }
    }
    // Single-newline imports use BR instead. Preserve intentional short lines,
    // stanza separators and explicit breaks unless the same prose signature fits.
    const runs = [];
    for (const paragraph of [...parent.children].filter(node => node.tagName === 'P')) {
      if (paragraph.closest(PRESERVE) || paragraph.querySelector('pre,code,img,table,ul,ol,blockquote')) continue;
      // Nested BRs are intentionally retained; only direct source-line breaks
      // can be projected without changing inline semantic nesting.
      const lines = ['']; const breaks = [];
      for (const child of paragraph.childNodes) {
        if (child.nodeName === 'BR') { breaks.push(child); lines.push(''); }
        else lines[lines.length - 1] += child.textContent;
      }
      if (breaks.length) runs.push({ lines, breaks });
    }
    // Ordinary TXT paragraphs often contain only three or four physical
    // lines. Establish the source signature across the container, then reflow
    // strictly inside each paragraph (never erase a real paragraph boundary).
    if (signature(runs.flatMap(run => run.lines))) {
      for (const { lines, breaks } of runs) {
        breaks.forEach((br, index) => { if (continuation(lines[index], lines[index + 1])) br.replaceWith(seam()); });
      }
    }
  }
  return fragment;
}
