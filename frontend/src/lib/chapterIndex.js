export const CHAPTER_INDEX_CONTRACT_VERSION = 'chapter-index.v1';

const STRUCTURED_TITLE = /^(chapter|letter|book|part|section|canto|volume|poem|gitanjali)\s+([ivxlcdm]+|\d+)[.:]?\s*(.*)$/i;
const ACRONYMS = new Set(['ai', 'api', 'css', 'dna', 'html', 'pdf', 'uk', 'us', 'usa']);

function romanToArabic(value = '') {
  const text = String(value || '').toUpperCase();
  if (!/^[IVXLCDM]+$/.test(text)) return null;
  const values = { I: 1, V: 5, X: 10, L: 50, C: 100, D: 500, M: 1000 };
  let total = 0;
  let previous = 0;
  [...text].reverse().forEach((character) => {
    const current = values[character];
    total += current < previous ? -current : current;
    previous = Math.max(previous, current);
  });
  return total || null;
}

function smartTitleCaseSegment(value = '') {
  const text = String(value || '').trim();
  const letters = text.match(/[A-Za-z]/g) || [];
  const upperLetters = text.match(/[A-Z]/g) || [];
  if (!letters.length || upperLetters.length / letters.length < 0.72) return text;
  return text
    .toLowerCase()
    .replace(/\b([a-z])([a-z'’.]*)/g, (word, first, rest) => (
      ACRONYMS.has(word.toLowerCase()) ? word.toUpperCase() : `${first.toUpperCase()}${rest}`
    ))
    .replace(/\b(Dr|Mr|Mrs|Ms)\b\.?/gi, (_match, honorific) => `${honorific[0].toUpperCase()}${honorific.slice(1).toLowerCase()}.`);
}

export function normalizeChapterDisplayTitle(title = '') {
  const original = String(title || '').trim();
  if (!original) return '';
  const cleaned = original
    .replace(/[_*`]+/g, '')
    .replace(/\s*[.:]?\s*(?:(?:--|—|-)\s*)?continued\.?\s*$/i, '')
    .replace(/\s+/g, ' ')
    .trim();
  const match = cleaned.match(STRUCTURED_TITLE);
  if (!match) return smartTitleCaseSegment(cleaned);
  const [, unit, numeral, remainder] = match;
  const number = /^\d+$/.test(numeral) ? Number(numeral) : (romanToArabic(numeral) || numeral.toUpperCase());
  const unitLabel = `${unit[0].toUpperCase()}${unit.slice(1).toLowerCase()} ${number}`;
  const subtitle = smartTitleCaseSegment(remainder);
  return subtitle ? `${unitLabel}. ${subtitle}` : unitLabel;
}

export function chapterIndexEntry(chapter = {}, position = 1, total = 1) {
  const apiContractCurrent = chapter.index_contract === CHAPTER_INDEX_CONTRACT_VERSION;
  if (apiContractCurrent && chapter.index_title && chapter.index_sequence_label) {
    return chapter;
  }
  const displayTitle = normalizeChapterDisplayTitle(chapter.display_title || chapter.title);
  const match = displayTitle.match(STRUCTURED_TITLE);
  const unitLabel = match ? `${match[1][0].toUpperCase()}${match[1].slice(1).toLowerCase()} ${match[2]}` : '';
  const subtitle = match ? match[3].trim().replace(/^[.:—-]\s*/, '') : '';
  const width = Math.max(2, String(Math.max(Number(total) || 1, 1)).length);
  return {
    ...chapter,
    index_contract: CHAPTER_INDEX_CONTRACT_VERSION,
    index_sequence: Math.max(Number(position) || 1, 1),
    index_sequence_label: String(Math.max(Number(position) || 1, 1)).padStart(width, '0'),
    display_title: displayTitle,
    index_title: subtitle || unitLabel || displayTitle || `Section ${position}`,
    index_secondary_label: subtitle ? unitLabel : '',
  };
}

export function sortedChapterIndex(chapters = []) {
  return chapters
    .map((chapter, sourceIndex) => ({ chapter, sourceIndex }))
    .sort((left, right) => (
      (Number(left.chapter?.order) || 0) - (Number(right.chapter?.order) || 0)
      || String(left.chapter?.id || '').localeCompare(String(right.chapter?.id || ''))
      || left.sourceIndex - right.sourceIndex
    ))
    .map(({ chapter }, index, sorted) => chapterIndexEntry(chapter, index + 1, sorted.length));
}
