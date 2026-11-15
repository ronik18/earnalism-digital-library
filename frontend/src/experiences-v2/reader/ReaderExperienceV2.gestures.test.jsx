import React, { act } from "react";
import { createRoot } from "react-dom/client";
import ReaderExperienceV2 from "./ReaderExperienceV2";

jest.mock("react-router-dom", () => ({
  Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a>,
  NavLink: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a>,
  useLocation: () => ({ pathname: "/reader/the-selfish-giant", search: "" }),
  useNavigate: () => jest.fn(),
}), { virtual: true });
jest.mock("./useVisualPagination", () => ({ __esModule: true, default: () => ({
  pages: Array.from({ length: 5 }, (_, i) => ({ start: i * 100, end: (i + 1) * 100, html: `<p>Verified fragment ${i + 1}</p>` })),
  pending: false, error: "", signature: "synthetic-layout", width: 600, height: 600,
}) }));
jest.mock("./useAuthorizedBookMap", () => ({ __esModule: true, default: () => ({
  sourceRef: { current: null }, measureRef: { current: null }, options: [], candidate: null,
  complete: false, total: null, currentNumber: null,
}) }));

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let root, container;
const request = jest.fn();
const model = { slug: "gesture-fixture", title: "Gesture fixture", chapterTitle: "Chapter", language: "en",
  canonicalPage: 1, totalPages: 2, sourceRevision: "fixture", visualFixture: true,
  content: <p>Fixture only</p>, onVisualAnchor: request };
async function render(extra = {}, access = {}) {
  await act(async () => root.render(<ReaderExperienceV2 model={{ ...model, ...extra }} access={access} />));
}
const touch = (x, y = 100, identifier = 1) => ({ clientX: x, clientY: y, identifier });
async function send(type, touches, changedTouches = [], target = container.querySelector("article"), timestamp) {
  const event = new Event(type, { bubbles: true, cancelable: true });
  Object.defineProperties(event, { touches: { value: touches }, changedTouches: { value: changedTouches },
    ...(timestamp == null ? {} : { timeStamp: { value: timestamp } }) });
  await act(async () => target.dispatchEvent(event));
}
async function swipe(from = touch(250), to = touch(100)) {
  await send("touchstart", [from]); await send("touchmove", [to]); await send("touchend", [], [to]);
}
beforeEach(() => {
  request.mockReset(); localStorage.clear();
  jest.spyOn(window, "scrollTo").mockImplementation(() => {});
  container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container);
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); jest.restoreAllMocks(); });
test("left and right swipes turn exactly one visual page through normal anchors", async () => {
  await render(); await swipe(); expect(request).toHaveBeenLastCalledWith(100);
  await swipe(touch(100), touch(250)); expect(request).toHaveBeenLastCalledWith(0);
  expect(request).toHaveBeenCalledTimes(2);
  await send("touchend", [], [touch(250)]); expect(request).toHaveBeenCalledTimes(2);
});
test.each([[250,220,100,100], [250,100,100,180], [250,200,100,140]])("short, vertical or diagonal movement does not turn (%s,%s,%s,%s)", async (x1,x2,y1,y2) => {
  await render(); await swipe(touch(x1,y1),touch(x2,y2)); expect(request).not.toHaveBeenCalled();
});
test("first and last book boundaries cannot be crossed", async () => {
  await render(); await swipe(touch(100),touch(250)); expect(request).not.toHaveBeenCalled();
  await render({ canonicalPage: 2, visualAnchor: 400 }); await swipe(); expect(request).not.toHaveBeenCalled();
});
test("preview boundary requests protected admission without exposing page four", async () => {
  const admission = jest.fn();
  await render({ visualFixture: false, visualAnchor: 200, onRequestProtectedContent: admission });
  await swipe(); expect(admission).toHaveBeenCalledWith(1,300,undefined,null);
  expect(request).not.toHaveBeenCalled();
  expect(container.querySelector('[data-testid="reader-reading-text"]').textContent).toContain("fragment 3");
});
test("busy and an open dialog suppress gestures", async () => {
  await render({}, { busy: true }); await swipe(); expect(request).not.toHaveBeenCalled();
  await render(); await act(async () => container.querySelector('[aria-label="Reader settings"]').click());
  await swipe(); expect(request).not.toHaveBeenCalled();
});
test("cancelled touches, pinch gestures and long press cannot turn", async () => {
  await render();
  await send("touchstart", [touch(250)]); await send("touchcancel", []); await send("touchend", [], [touch(100)]);
  await send("touchstart", [touch(250)]); await send("touchmove", [touch(100),touch(300,100,2)]); await send("touchend", [], [touch(100)]);
  await send("touchstart", [touch(250)], [], undefined, 100); await send("touchend", [], [touch(100)], undefined, 900);
  expect(request).not.toHaveBeenCalled();
});
test("text selection, embedded controls and mouse dragging retain native behavior", async () => {
  await render();
  const selection = jest.spyOn(window, "getSelection").mockReturnValue({ toString: () => "selected text" });
  await swipe(); expect(request).not.toHaveBeenCalled(); selection.mockRestore();
  const link = document.createElement("a"); link.href = "#note"; container.querySelector("article").appendChild(link);
  await send("touchstart", [touch(250)], [], link); await send("touchend", [], [touch(100)], link);
  await act(async () => { container.querySelector("article").dispatchEvent(new MouseEvent("mousedown", { bubbles:true, clientX:250 })); container.querySelector("article").dispatchEvent(new MouseEvent("mouseup", { bubbles:true, clientX:100 })); });
  expect(request).not.toHaveBeenCalled();
});
test("selection appearing during a swipe cancels the turn", async () => {
  await render(); await send("touchstart", [touch(250)]);
  jest.spyOn(window, "getSelection").mockReturnValue({ toString: () => "selected text" });
  await send("touchend", [], [touch(100)]); expect(request).not.toHaveBeenCalled();
});
test("navigation or busy transitions invalidate an in-flight gesture", async () => {
  await render(); await send("touchstart", [touch(250)]); await render({}, { busy:true }); await render();
  await send("touchend", [], [touch(100)]); expect(request).not.toHaveBeenCalled();
  await send("touchstart", [touch(250)]); await render({ visualAnchor:200 });
  await send("touchend", [], [touch(100)]); expect(request).not.toHaveBeenCalled();
});
