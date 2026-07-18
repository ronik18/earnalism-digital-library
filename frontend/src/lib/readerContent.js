const HTML_TAG_RE = /<\/?[a-z][\s\S]*>/i;

function escapeHtml(value = '') {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Convert legacy plain-text chapters into semantic blocks before pagination.
 * Single newlines stay as intentional line breaks inside a paragraph.
 */
export function normalizeReaderContentHtml(value = '') {
  const source = String(value || '').replace(/\r\n?/g, '\n').trim();
  if (!source || HTML_TAG_RE.test(source)) return source;

  return source
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
    .map((paragraph) => `<p>${escapeHtml(paragraph).replace(/\n/g, '<br>')}</p>`)
    .join('');
}
