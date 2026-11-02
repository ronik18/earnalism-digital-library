const HTML_TAG_RE = /<\/?[a-z][\s\S]*>/i;
const HARD_WRAP_MIN_BLOCKS = 6;

function escapeHtml(value = '') {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function hardWrapWidthFor(blocks = []) {
  if (blocks.length < HARD_WRAP_MIN_BLOCKS || blocks.some((block) => block.includes('\n'))) return 0;

  const lengths = blocks.map((block) => block.length).filter(Boolean).sort((a, b) => a - b);
  const wrapWidth = lengths[Math.max(0, Math.ceil(lengths.length * 0.8) - 1)] || 0;
  const wrappedLineCount = lengths.filter((length) => length >= Math.max(42, wrapWidth * 0.72)).length;
  if (wrapWidth < 48 || wrapWidth > 110 || wrappedLineCount / lengths.length < 0.45) return 0;
  return wrapWidth;
}

function shouldJoinHardWrappedBlock(previous, current, wrapWidth) {
  return previous.length >= Math.max(42, wrapWidth * 0.72)
    || /^[a-z\u00df-\u00ff,;:)}\]]/.test(current);
}

function reflowHardWrappedBlocks(blocks = []) {
  const wrapWidth = hardWrapWidthFor(blocks);
  if (!wrapWidth) return blocks;

  const paragraphs = [];
  let paragraph = blocks[0];

  for (let index = 1; index < blocks.length; index += 1) {
    const previous = blocks[index - 1];
    const current = blocks[index];
    if (shouldJoinHardWrappedBlock(previous, current, wrapWidth)) {
      paragraph = `${paragraph} ${current}`;
    } else {
      paragraphs.push(paragraph);
      paragraph = current;
    }
  }

  paragraphs.push(paragraph);
  return paragraphs;
}

function reflowHardWrappedParagraphHtml(source = '') {
  if (typeof document === 'undefined') return source;
  const template = document.createElement('template');
  template.innerHTML = source;
  const children = Array.from(template.content.children);
  let changed = false;

  for (let start = 0; start < children.length;) {
    if (children[start].tagName !== 'P') {
      start += 1;
      continue;
    }

    let end = start;
    while (end < children.length && children[end].tagName === 'P') end += 1;
    const run = children.slice(start, end);
    const blocks = run.map((node) => (node.textContent || '').trim());
    const wrapWidth = hardWrapWidthFor(blocks);

    if (wrapWidth) {
      let keeper = run[0];
      for (let index = 1; index < run.length; index += 1) {
        const current = run[index];
        if (shouldJoinHardWrappedBlock(blocks[index - 1], blocks[index], wrapWidth)) {
          keeper.appendChild(document.createTextNode(' '));
          while (current.firstChild) keeper.appendChild(current.firstChild);
          current.remove();
          changed = true;
        } else {
          keeper = current;
        }
      }
    }

    start = end;
  }

  return changed ? template.innerHTML : source;
}

/** Convert legacy plain text into semantic blocks before pagination. */
export function normalizeReaderContentHtml(value = '') {
  const source = String(value || '').replace(/\r\n?/g, '\n').trim();
  if (!source) return source;
  if (HTML_TAG_RE.test(source)) return reflowHardWrappedParagraphHtml(source);

  const blocks = source
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);

  return reflowHardWrappedBlocks(blocks)
    .map((paragraph) => `<p>${escapeHtml(paragraph).replace(/\n/g, '<br>')}</p>`)
    .join('');
}
