import React, { act } from "react";
import { createRoot } from "react-dom/client";
import useSavedReadingPosition, { classifySavedReadingPosition } from "./useSavedReadingPosition";
import * as pass from "./readingPassApi";
jest.mock("./readingPassApi", () => ({ getReadingPassPosition: jest.fn(), startReadingPassSession: jest.fn(), saveReadingPassPosition: jest.fn() }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const user = { id: "reader-a", role: "user" };
const empty = { content_type: "text", content_id: "book", position: {}, version: 0 };
const pages = { page_count: 7, schema_version: "s1", content_revision: "v1", pages: Array.from({ length: 7 }, (_, i) => ({ page_number: i + 1, chapter_id: "c1" })) };
const saved = { ...empty, user_id: user.id, version: 3, publication_version_compatibility: "active", position: { canonical_page_index: 4, chapter_id: "c1", segmentation_version: "s1", manifest_version: "v1", publication_version_state: "bound" } };

test("only the exact absent-row response proves no saved progress", () => {
  expect(classifySavedReadingPosition(empty, user.id, "book", pages)).toBe("new");
  expect(classifySavedReadingPosition(saved, user.id, "book", pages)).toBe("resume");
});
test.each([null, {}, { ...empty, content_id: "other" }, { ...empty, content_type: "audio" }, { ...empty, user_id: "other" }, { ...empty, user_id: user.id }, { ...empty, version: "0" }, { ...empty, version: -1 }, { ...empty, position: [] }, { ...empty, position: null }, { ...empty, position: { canonical_page_index: 1 } }])("malformed or foreign metadata cannot be new: %j", record => {
  expect(classifySavedReadingPosition(record, user.id, "book", pages)).toBe("unknown");
});
test("old or incomplete edition metadata remains existing, never new or compatible", () => {
  expect(classifySavedReadingPosition({ ...saved, publication_version_compatibility: "retained_nonactive" }, user.id, "book", pages)).toBe("existing");
  expect(classifySavedReadingPosition(saved, user.id, "book", undefined)).toBe("existing");
  expect(classifySavedReadingPosition(saved, user.id, "book", { ...pages, pages: {} })).toBe("existing");
  expect(classifySavedReadingPosition(saved, user.id, "book", { ...pages, pages: [null] })).toBe("existing");
  expect(classifySavedReadingPosition(saved, user.id, "book", { ...pages, page_count: "7" })).toBe("existing");
});
let root, container;
function Probe(props) { const value = useSavedReadingPosition(props); return <output data-kind={value.kind}>{value.loading ? "loading" : value.kind}</output>; }
const render = async props => { await act(async () => root.render(<Probe user={user} slug="book" enabled canonicalPages={pages} {...props} />)); };
const kind = () => container.querySelector('output').dataset.kind;
beforeEach(() => { jest.clearAllMocks(); localStorage.clear(); container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container); });
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });
test("preflight reads once and performs no session, progress or device-storage write", async () => {
  pass.getReadingPassPosition.mockResolvedValue(empty);
  const write = jest.spyOn(Storage.prototype, 'setItem');
  try {
    await render({}); expect(kind()).toBe('new');
    expect(pass.getReadingPassPosition).toHaveBeenCalledTimes(1);
    expect(pass.getReadingPassPosition).toHaveBeenCalledWith({ contentType: 'text', contentId: 'book' });
    expect(pass.startReadingPassSession).not.toHaveBeenCalled(); expect(pass.saveReadingPassPosition).not.toHaveBeenCalled(); expect(write).not.toHaveBeenCalled();
  } finally { write.mockRestore(); }
});
test.each([null, { id: 'admin-a', role: 'admin' }])("guest/non-reader performs no progress lookup: %j", account => {
  return render({ user: account }).then(() => { expect(kind()).toBe('unknown'); expect(pass.getReadingPassPosition).not.toHaveBeenCalled(); });
});
test("failed lookup stays unknown without an automatic retry", async () => {
  pass.getReadingPassPosition.mockRejectedValue({ response: { status: 401 } }); await render({});
  expect(kind()).toBe('unknown'); await render({ user: { ...user, reading_seconds_balance: 300 } });
  expect(pass.getReadingPassPosition).toHaveBeenCalledTimes(1);
});
test("late account/book responses cannot label the new scope empty", async () => {
  let resolveA, resolveB;
  pass.getReadingPassPosition.mockReturnValueOnce(new Promise(resolve => { resolveA = resolve; })).mockReturnValueOnce(new Promise(resolve => { resolveB = resolve; }));
  await render({}); await render({ user: { id: 'reader-b', role: 'user' }, slug: 'other-book' });
  await act(async () => resolveA(empty)); expect(kind()).toBe('unknown');
  await act(async () => resolveB({ ...empty, content_id: 'other-book' })); expect(kind()).toBe('new');
});
test("sign-out removes a confirmed empty result before the same account returns", async () => {
  pass.getReadingPassPosition.mockResolvedValueOnce(empty).mockReturnValue(new Promise(() => {}));
  await render({}); expect(kind()).toBe('new'); await render({ user: null }); expect(kind()).toBe('unknown');
  await render({}); expect(kind()).toBe('unknown');
});

test("an empty server row cannot override existing device progress", async () => {
  localStorage.setItem('earnalism:reader-position:reader-a:book', JSON.stringify({ page: 4 }));
  pass.getReadingPassPosition.mockResolvedValue(empty); await render({});
  expect(kind()).toBe('existing'); expect(pass.startReadingPassSession).not.toHaveBeenCalled();
});
test("unavailable device storage cannot prove the title new", async () => {
  pass.getReadingPassPosition.mockResolvedValue(empty);
  const read = jest.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked'); });
  try { await render({}); expect(kind()).toBe('unknown'); } finally { read.mockRestore(); }
});
