import { readerSourceText } from './readerContent';

// Transport units remain server-authorized. This plan grants no access: every
// selected unit must still pass the existing page endpoint with the current lease.
export function chapterWindowPlan(manifest, pageIndex, protectedAccess) {
  const rows = manifest?.canonical_pages?.pages || [];
  const indexes = rows.map(row => Number(row.page_number || row.page_index));
  if (!rows.length || rows.length !== Number(manifest.canonical_pages.page_count) || new Set(indexes).size !== rows.length
    || indexes.some((index, n) => index !== n + 1)
    || rows.some(row => !/^[a-f0-9]{64}$/.test(row.content_hash || ''))) throw new Error('The chapter manifest is incomplete or out of order.');
  const current = rows[pageIndex - 1];
  if (!current?.chapter_id) throw new Error('The chapter identity is missing.');
  const chapterRows = rows.filter(row => row.chapter_id === current.chapter_id);
  const chapterIndexes = chapterRows.map(row => Number(row.page_number || row.page_index));
  if (chapterIndexes.some((index, n) => n && index !== chapterIndexes[n - 1] + 1)) throw new Error('The chapter order is inconsistent.');
  const limit = Number(manifest.canonical_pages.preview_policy?.public_limit || 3);
  if (!Number.isInteger(limit) || limit < 1 || limit > 3) throw new Error('The preview policy cannot be verified.');
  const selected = chapterRows.filter(row => protectedAccess || Number(row.page_number || row.page_index) <= limit);
  if (!selected.some(row => Number(row.page_number || row.page_index) === pageIndex)) throw new Error('This source position requires reading authorization.');
  const first = Number(selected[0].page_number || selected[0].page_index);
  const last = Number(selected[selected.length - 1].page_number || selected[selected.length - 1].page_index);
  const chapter = (manifest.chapters || manifest.book?.chapters || []).find(item => (item.id || item.chapter_id) === current.chapter_id);
  return { rows: selected, previewLimit: limit, chapterId: current.chapter_id, chapterTitle: chapter?.title || chapter?.chapter_title || '', first, last,
    previous: first > 1 ? first - 1 : null, next: last < rows.length ? last + 1 : null,
    revision: manifest.canonical_pages.content_revision || '',
    key: JSON.stringify([current.chapter_id, protectedAccess ? 'leased' : 'preview', selected.map(row => [row.page_id, row.content_hash])]) };
}

export async function fetchChapterWindow({ plan, slug, totalPages, fetchChunk, signal, authorized = () => true, concurrency = 3 }) {
  const started = performance.now();
  const chunks = new Array(plan.rows.length);
  let cursor = 0;
  let bytes = 0;
  let networkMs = 0;
  let verificationMs = 0;
  const check = () => { if (signal?.aborted || !authorized()) throw new Error('Reader authorization changed while opening this chapter.'); };
  await Promise.all(Array.from({ length: Math.min(concurrency, plan.rows.length) }, async () => {
    while (cursor < plan.rows.length) {
      check();
      const slot = cursor++;
      const expected = plan.rows[slot];
      const index = Number(expected.page_number || expected.page_index);
      const networkStarted = performance.now();
      const value = await fetchChunk(index, signal);
      networkMs += performance.now() - networkStarted;
      check();
      if (value.book_slug !== slug || value.page_index !== index || value.total_pages !== totalPages
        || value.chapter_id !== plan.chapterId || (plan.chapterTitle && value.chapter_title !== plan.chapterTitle) || typeof value.content !== 'string' || !value.content.trim()
        || value.is_preview !== (index <= plan.previewLimit)
        || (expected.content_hash && expected.content_hash !== value.content_sha256)
        || (plan.revision && value.manifest_version !== plan.revision)) throw new Error('A chapter chunk does not match the selected edition.');
      if (!globalThis.crypto?.subtle) throw new Error('This browser cannot verify the chapter content.');
      const verificationStarted = performance.now();
      const digest = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(value.content));
      verificationMs += performance.now() - verificationStarted;
      check();
      const actualHash = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
      if (actualHash !== expected.content_hash) throw new Error('A chapter chunk does not match the selected edition content hash.');
      bytes += value.content.length * 2;
      if (bytes > 32 * 1024 * 1024) throw new Error('This chapter exceeds the safe Reader assembly limit.');
      chunks[slot] = value;
    }
  }));
  check();
  const fetchedAt = performance.now();
  const revision = chunks[0]?.manifest_version;
  const segmentation = chunks[0]?.segmentation_version;
  if (!revision || !segmentation || chunks.some(chunk => chunk.manifest_version !== revision || chunk.segmentation_version !== segmentation)) throw new Error('The chapter publication version changed.');
  let offset = 0;
  const sources = chunks.map(chunk => {
    // Count exactly the sanitized text rendered by ReaderContent, including
    // formatting whitespace. No heuristic seam stripping or inserted separators.
    const length = readerSourceText(chunk.content).length;
    const source = { page: chunk.page_index, start: offset, end: offset + length, revision: chunk.content_sha256 || revision, value: chunk };
    offset += length;
    return source;
  });
  return { html: chunks.map(chunk => chunk.content).join(''), sources, plan,
    revision: JSON.stringify([revision, segmentation, sources.map(source => [source.page, source.revision])]),
    textLength: offset, networkMs, verificationMs, fetchMs: fetchedAt - started, assemblyMs: performance.now() - fetchedAt };
}

export function chapterAnchor(window, page, offset = 0, revision) {
  const source = window.sources.find(item => item.page === page);
  if (!source) throw new Error('The requested position is outside this authorized chapter window.');
  if (revision && revision !== source.revision) return source.start;
  return offset === 'end' ? source.end - 1 : source.start + Math.min(source.end - source.start, Math.max(0, Number(offset) || 0));
}
export function transportAnchor(window, offset) {
  const source = window.sources.find(item => offset >= item.start && offset < item.end) || window.sources[window.sources.length - 1];
  return { page: source.page, offset: Math.max(0, offset - source.start), revision: source.revision };
}
