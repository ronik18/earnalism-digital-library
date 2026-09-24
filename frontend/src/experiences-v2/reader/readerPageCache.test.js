import {
  clearReaderPageCache,
  getCachedReaderPage,
  getOrFetchReaderPage,
  readerPageCacheKey,
  readerPageCacheSize,
  resetReaderPageCacheForTests,
  retainReaderPageWindow,
} from "./readerPageCache";

const key = (pageIndex, overrides = {}) => readerPageCacheKey({
  slug: "a-ghost-story",
  manifestVersion: "manifest-v1",
  pageIndex,
  pageHash: `hash-${pageIndex}`,
  accessContext: "preview",
  ...overrides,
});

beforeEach(() => resetReaderPageCacheForTests());

test("deduplicates in-flight reads and keeps publication, version, page and access context isolated", async () => {
  let resolve;
  const pending = new Promise((done) => { resolve = done; });
  const fetchPage = jest.fn(() => pending);
  const first = getOrFetchReaderPage(key(2), fetchPage);
  const second = getOrFetchReaderPage(key(2), fetchPage);

  expect(fetchPage).toHaveBeenCalledTimes(0);
  await Promise.resolve();
  expect(fetchPage).toHaveBeenCalledTimes(1);
  resolve({ content: "canonical page" });
  await expect(first).resolves.toEqual({ content: "canonical page" });
  await expect(second).resolves.toEqual({ content: "canonical page" });
  await expect(getOrFetchReaderPage(key(2), fetchPage)).resolves.toEqual({ content: "canonical page" });
  expect(fetchPage).toHaveBeenCalledTimes(1);

  const otherBook = key(2, { slug: "the-tell-tale-heart" });
  const otherVersion = key(2, { manifestVersion: "manifest-v2" });
  const otherIdentity = key(2, { accessContext: "protected:reader-2:session-9" });
  await getOrFetchReaderPage(otherBook, async () => ({ content: "book b" }));
  await getOrFetchReaderPage(otherVersion, async () => ({ content: "new publication" }));
  await getOrFetchReaderPage(otherIdentity, async () => ({ content: "other authorized session" }));
  expect(getCachedReaderPage(otherBook).content).toBe("book b");
  expect(getCachedReaderPage(otherVersion).content).toBe("new publication");
  expect(getCachedReaderPage(otherIdentity).content).toBe("other authorized session");
  expect(readerPageCacheSize()).toBe(4);
});

test("bounds memory to the 32 most-recent pages", async () => {
  for (let pageIndex = 1; pageIndex <= 40; pageIndex += 1) {
    await getOrFetchReaderPage(key(pageIndex), async () => ({ pageIndex }));
  }

  expect(readerPageCacheSize()).toBe(32);
  expect(getCachedReaderPage(key(1))).toBeNull();
  expect(getCachedReaderPage(key(8))).toBeNull();
  expect(getCachedReaderPage(key(9))).toEqual({ pageIndex: 9 });
  expect(getCachedReaderPage(key(40))).toEqual({ pageIndex: 40 });
});

test("retains only the adjacent window for the active book and authorization context", async () => {
  for (let pageIndex = 1; pageIndex <= 8; pageIndex += 1) {
    await getOrFetchReaderPage(key(pageIndex), async () => ({ pageIndex }));
  }
  const protectedKey = key(1, { accessContext: "protected:reader-1:session-1" });
  const otherBookKey = key(1, { slug: "the-tell-tale-heart" });
  await getOrFetchReaderPage(protectedKey, async () => ({ pageIndex: 1, protected: true }));
  await getOrFetchReaderPage(otherBookKey, async () => ({ pageIndex: 1, otherBook: true }));

  retainReaderPageWindow({ slug: "a-ghost-story", accessContext: "preview", centerPage: 5, preservePage: 2 });

  expect(getCachedReaderPage(key(2))).toEqual({ pageIndex: 2 });
  expect(getCachedReaderPage(key(3))).toEqual({ pageIndex: 3 });
  expect(getCachedReaderPage(key(4))).toEqual({ pageIndex: 4 });
  expect(getCachedReaderPage(key(5))).toEqual({ pageIndex: 5 });
  expect(getCachedReaderPage(key(6))).toEqual({ pageIndex: 6 });
  expect(getCachedReaderPage(key(7))).toEqual({ pageIndex: 7 });
  expect(getCachedReaderPage(key(1))).toBeNull();
  expect(getCachedReaderPage(key(8))).toBeNull();
  expect(getCachedReaderPage(protectedKey)).toEqual({ pageIndex: 1, protected: true });
  expect(getCachedReaderPage(otherBookKey)).toEqual({ pageIndex: 1, otherBook: true });
});

test("can invalidate only one publication and authorization context", async () => {
  const protectedKey = key(4, { accessContext: "protected:reader-1:session-1" });
  await getOrFetchReaderPage(key(1), async () => ({ content: "preview" }));
  await getOrFetchReaderPage(protectedKey, async () => ({ content: "protected" }));

  clearReaderPageCache({ slug: "a-ghost-story", accessContext: "protected:reader-1:session-1" });

  expect(getCachedReaderPage(protectedKey)).toBeNull();
  expect(getCachedReaderPage(key(1))).toEqual({ content: "preview" });
});
