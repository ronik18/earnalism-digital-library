import { loadReaderNotebook, normalizeNotebook, readerNotebookKey, saveReaderNotebook } from "./readerNotebook";

afterEach(() => { localStorage.clear(); jest.restoreAllMocks(); });

test("notebooks persist per edition and account without sharing notes", () => {
  const first = readerNotebookKey("dracula", "reader-1");
  const data = { notes: [{ id: "note-1", page: 4, text: "A thought", createdAt: "2026-09-30" }], bookmarks: [4] };
  expect(saveReaderNotebook(first, data)).toBe(true);
  expect(loadReaderNotebook(first)).toEqual(data);
  expect(loadReaderNotebook(readerNotebookKey("dracula", "reader-2")).notes).toEqual([]);
  expect(loadReaderNotebook(readerNotebookKey("sherlock-holmes", "reader-1")).bookmarks).toEqual([]);
});

test("corrupt storage and invalid entries cannot break reading", () => {
  localStorage.setItem("broken", "{bad");
  expect(loadReaderNotebook("broken")).toEqual({ notes: [], bookmarks: [] });
  expect(normalizeNotebook({ notes: [{ id: "bad", page: -1, text: "no" }], bookmarks: [3, 1, 3, -1, "4"] })).toEqual({ notes: [], bookmarks: [1, 3] });
});

test("storage failure reports an unsaved notebook", () => {
  jest.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
  expect(saveReaderNotebook("key", { notes: [], bookmarks: [1] })).toBe(false);
});
