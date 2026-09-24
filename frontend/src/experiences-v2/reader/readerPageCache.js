const MAX_READER_PAGES = 32;

const pages = new Map();
const inFlight = new Map();
let cacheGeneration = 0;

export function readerPageCacheKey({ slug, manifestVersion, pageIndex, pageHash, accessContext }) {
  return JSON.stringify([slug, manifestVersion || "unknown", pageIndex, pageHash || "", accessContext]);
}

export function getCachedReaderPage(key) {
  if (!pages.has(key)) return null;
  const value = pages.get(key);
  pages.delete(key);
  pages.set(key, value);
  return value;
}

export function getOrFetchReaderPage(key, fetchPage) {
  const cached = getCachedReaderPage(key);
  if (cached) return Promise.resolve(cached);
  if (inFlight.has(key)) return inFlight.get(key);

  const requestGeneration = cacheGeneration;
  const request = Promise.resolve()
    .then(fetchPage)
    .then((value) => {
      if (requestGeneration === cacheGeneration) {
        pages.delete(key);
        pages.set(key, value);
        while (pages.size > MAX_READER_PAGES) pages.delete(pages.keys().next().value);
      }
      return value;
    })
    .finally(() => { if (inFlight.get(key) === request) inFlight.delete(key); });
  inFlight.set(key, request);
  return request;
}

export function retainReaderPageWindow({ slug, accessContext, centerPage, preservePage }) {
  const min = Math.max(1, centerPage - 2);
  const max = centerPage + 2;
  for (const key of pages.keys()) {
    let identity;
    try { identity = JSON.parse(key); } catch { continue; }
    if (identity[0] !== slug || identity[4] !== accessContext) continue;
    const pageIndex = Number(identity[2]);
    if ((pageIndex < min || pageIndex > max) && pageIndex !== preservePage) pages.delete(key);
  }
}

export function clearReaderPageCache({ slug, accessContext } = {}) {
  for (const key of pages.keys()) {
    let identity;
    try { identity = JSON.parse(key); } catch { continue; }
    if ((!slug || identity[0] === slug) && (!accessContext || identity[4] === accessContext)) pages.delete(key);
  }
}

export function readerPageCacheSize() {
  return pages.size;
}

export function resetReaderPageCacheForTests() {
  cacheGeneration += 1;
  pages.clear();
  inFlight.clear();
}
