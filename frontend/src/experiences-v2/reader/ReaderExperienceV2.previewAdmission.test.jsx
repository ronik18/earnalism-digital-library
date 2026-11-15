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
const baseModel = {
  slug: "the-selfish-giant", title: "The Selfish Giant", author: "Oscar Wilde", language: "en",
  canonicalPage: 1, totalPages: 1, visualAnchor: 300, sourceRevision: "synthetic-revision",
  content: <p>Verified isolated fixture only.</p>,
  sourceAnchorForOffset: offset => ({ page: 1, offset, revision: "source-revision" }),
  onRequestProtectedContent: request,
};
async function render(model = {}, access = {}) {
  await act(async () => root.render(<ReaderExperienceV2 model={{ ...baseModel, ...model }} access={access} />));
}
beforeEach(() => {
  request.mockReset(); localStorage.clear();
  Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
  jest.spyOn(document, "hasFocus").mockReturnValue(true);
  jest.spyOn(window, "scrollTo").mockImplementation(() => {});
  container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container);
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); jest.restoreAllMocks(); });

test("a paid member's restored visual page four requests one route admission inside canonical page one", async () => {
  await render({ allowAutomaticPassAdmission: true });
  expect(request).toHaveBeenCalledTimes(1);
  expect(request).toHaveBeenCalledWith(1, 300, "source-revision", expect.objectContaining({ page: 1, offset: 300 }));
  expect(container.querySelector('[data-testid="reader-preview-limit"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="reader-reading-text"]')).toBeNull();
  await render({ allowAutomaticPassAdmission: true }, { busy: true });
  await render({ allowAutomaticPassAdmission: true });
  await act(async () => window.dispatchEvent(new Event("focus")));
  expect(request).toHaveBeenCalledTimes(1);
});

test.each([false, undefined])("unverified or ineligible pass admission (%s) retains manual preview boundary", async allowAutomaticPassAdmission => {
  await render({ allowAutomaticPassAdmission });
  expect(request).not.toHaveBeenCalled();
  expect(container.querySelector('[data-testid="reader-preview-limit"]')).not.toBeNull();
});

test("background restored preview waits for real focus and dispatches only once", async () => {
  document.hasFocus.mockReturnValue(false);
  await render({ allowAutomaticPassAdmission: true });
  expect(request).not.toHaveBeenCalled();
  document.hasFocus.mockReturnValue(true);
  await act(async () => window.dispatchEvent(new Event("focus")));
  await act(async () => document.dispatchEvent(new Event("visibilitychange")));
  expect(request).toHaveBeenCalledTimes(1);
});

test("the first three free visual pages do not start paid admission", async () => {
  await render({ allowAutomaticPassAdmission: true, visualAnchor: 200 });
  expect(request).not.toHaveBeenCalled();
  expect(container.querySelector('[data-testid="reader-preview-limit"]')).toBeNull();
});

test("a server-authorized protected page shows its fragment without another admission", async () => {
  await render({ allowAutomaticPassAdmission: true }, { authorized: true });
  expect(request).not.toHaveBeenCalled();
  expect(container.querySelector('[data-testid="reader-preview-limit"]')).toBeNull();
  expect(container.querySelector('[data-testid="reader-reading-text"]').textContent).toContain("Verified fragment 4");
});
