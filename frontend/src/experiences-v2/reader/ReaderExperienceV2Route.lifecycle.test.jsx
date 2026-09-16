import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Route, Routes, useNavigate, useLocation } from "react-router-dom";
import ReaderExperienceV2Route from "./ReaderExperienceV2Route";
import { userApi } from "../../lib/api";
import * as pass from "../../lib/readingPassApi";

let mockUser = { id: "test-reader" };
const mockSetUserBalance = jest.fn();
// CRA's Jest 27 does not resolve react-router-dom 7's conditional exports.
// Use its real underlying router implementation, not mocked navigation hooks.
jest.mock("react-router-dom", () => {
  const { TextEncoder, TextDecoder } = require("util");
  globalThis.TextEncoder = TextEncoder;
  globalThis.TextDecoder = TextDecoder;
  return require("react-router");
}, { virtual: true });
jest.mock("../../context/AuthContext", () => ({ useAuth: () => ({ user: mockUser, setUserBalance: mockSetUserBalance }) }));
jest.mock("../../lib/api", () => ({ userApi: { get: jest.fn(), post: jest.fn() } }));
jest.mock("../../lib/readingPassApi", () => ({
  getReadingPassPage: jest.fn(), startReadingPassSession: jest.fn(), renewReadingPassLease: jest.fn(),
  endReadingPassSession: jest.fn(), getReadingPassPosition: jest.fn(), saveReadingPassPosition: jest.fn(),
}));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const manifest = (slug = "test-book") => ({
  book: { slug, title: "The test edition", author: "Test author", language: "English" },
  access: { reading_pass: { enabled: true, total_pages: 7 }, wallet_seconds: 600 },
  canonical_pages: { page_count: 7, pages: Array.from({ length: 7 }, (_, i) => ({ page_number: i + 1, chapter_id: "c1" })) },
  chapters: [{ id: "c1", title: "Chapter one" }],
});
const page = (n, slug = "test-book") => ({ book_slug: slug, page_index: n, chapter_id: "c1", chapter_title: "Chapter one", total_pages: 7, is_preview: n <= 3, content: `<p>Page ${n} manuscript.</p>` });
const response = (extra = {}) => ({ session_id: "session-1", lease_token: "opaque-test-token", lease_version: 1, lease_expires_at: new Date(Date.now() + 20000).toISOString(), balance_seconds: 600, heartbeat_seconds: 10, status: "Running", content_type: "text", content_id: "test-book", ...extra });
let container, root, navigate;
function LocationProbe() {
  navigate = useNavigate();
  return <output data-testid="location">{useLocation().pathname}{useLocation().search}</output>;
}
async function mount(entry = "/reader/test-book?p=4") {
  await act(async () => root.render(<MemoryRouter initialEntries={[entry]}><LocationProbe /><Routes><Route path="/reader/:slug" element={<ReaderExperienceV2Route />} /><Route path="*" element={<p>Destination page</p>} /></Routes></MemoryRouter>));
}
const text = () => container.textContent;
async function click(label) {
  const button = [...container.querySelectorAll("button")].find((node) => node.textContent.trim() === label || node.getAttribute("aria-label") === label);
  if (!button) throw new Error(`Missing button: ${label}. ${text().slice(0,700)}`);
  await act(async () => button.dispatchEvent(new MouseEvent("click", { bubbles: true })));
}
async function openProtected() { await mount(); await click("Continue to this page"); }
async function tick(ms) { await act(async () => { jest.advanceTimersByTime(ms); }); }
function deferred() { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; }

beforeEach(() => {
  jest.useFakeTimers();
  jest.setSystemTime(new Date("2026-09-16T10:00:00Z"));
  jest.clearAllMocks();
  localStorage.clear();
  mockUser = { id: "test-reader" };
  mockSetUserBalance.mockReset();
  Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
  jest.spyOn(document, "hasFocus").mockReturnValue(true);
  jest.spyOn(window, "scrollTo").mockImplementation(() => {});
  userApi.get.mockImplementation(async (url) => ({ data: manifest(url.includes("other-book") ? "other-book" : "test-book") }));
  pass.getReadingPassPage.mockImplementation(async (slug, n) => page(n, slug));
  pass.startReadingPassSession.mockImplementation(async () => response());
  pass.renewReadingPassLease.mockImplementation(async ({ lease, active }) => response({ lease_version: lease.version + 1, status: active ? "Running" : "Paused", lease_expires_at: new Date(Date.now() + (active ? 20000 : 0)).toISOString(), balance_seconds: 590 }));
  pass.endReadingPassSession.mockImplementation(async (lease) => ({ ended: true, session_id: lease.sessionId, balance_seconds: 590 }));
  pass.getReadingPassPosition.mockResolvedValue({ version: 0 });
  pass.saveReadingPassPosition.mockResolvedValue({ version: 1 });
  container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container);
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); jest.useRealTimers(); jest.restoreAllMocks(); });

test("a cached guest manifest cannot replace the authenticated profile balance with zero", async () => {
  mockUser = { id: "test-reader", reading_seconds_balance: 1234 };
  const guestManifest = manifest();
  guestManifest.access = { ...guestManifest.access, role: "guest", authenticated: false, wallet_seconds: 0 };
  userApi.get.mockResolvedValueOnce({ data: guestManifest });
  await mount("/reader/test-book?p=1");
  expect(text()).toContain("20 minutes left");
  expect(text()).not.toContain("0 seconds left");
  expect(mockSetUserBalance).not.toHaveBeenCalled();
  expect(pass.startReadingPassSession).not.toHaveBeenCalled();
});

test.each([undefined, null, "600", -1, 1.5])("an invalid profile balance %p stays unavailable rather than borrowing a manifest balance", async (value) => {
  mockUser = { id: "test-reader", reading_seconds_balance: value };
  await mount("/reader/test-book?p=1");
  expect(text()).toContain("Balance unavailable");
  expect(text()).not.toContain("minutes left");
  expect(mockSetUserBalance).not.toHaveBeenCalled();
});

test("a validated zero profile balance and a guest are displayed distinctly", async () => {
  mockUser = { id: "test-reader", reading_seconds_balance: 0 };
  await mount("/reader/test-book?p=1");
  expect(text()).toContain("0 seconds left");
  mockUser = false;
  await mount("/reader/test-book?p=1");
  expect(text()).toContain("Sign in to continue");
  expect(text()).not.toContain("0 seconds left");
});

test("lease and settlement balances supersede a stale profile without refetching on profile updates", async () => {
  mockUser = { id: "test-reader", reading_seconds_balance: 1234 };
  mockSetUserBalance.mockImplementation((seconds, identity) => {
    if (identity === mockUser.id) mockUser = { ...mockUser, reading_seconds_balance: seconds };
  });
  await openProtected();
  const article = container.querySelector("article");
  expect(text()).toContain("10 minutes left");
  expect(mockSetUserBalance).toHaveBeenLastCalledWith(600, "test-reader");
  for (let index = 0; index < 3; index += 1) {
    await tick(10000);
    // Render the updated provider profile with the same customer identity.
    await mount("/reader/test-book?p=4");
    expect(container.querySelector("article")).toBe(article);
    expect(text()).toContain("9 minutes left");
  }
  mockUser = { ...mockUser, reading_seconds_balance: 1234 };
  await mount("/reader/test-book?p=4");
  expect(text()).toContain("9 minutes left");
  expect(pass.getReadingPassPage).toHaveBeenCalledTimes(1);
  pass.endReadingPassSession.mockResolvedValueOnce({ ended: true, session_id: "session-1", balance_seconds: 321 });
  await click("Previous page");
  expect(text()).toContain("Page 3 manuscript.");
  expect(text()).toContain("5 minutes left");
  expect(mockSetUserBalance).toHaveBeenLastCalledWith(321, "test-reader");
});

test("a missing lease balance is not coerced to a validated zero grant", async () => {
  pass.startReadingPassSession.mockResolvedValueOnce(response({ balance_seconds: null }));
  await openProtected();
  expect(text()).toContain("Reading access could not be verified");
  expect(pass.getReadingPassPage).not.toHaveBeenCalled();
  expect(mockSetUserBalance).not.toHaveBeenCalled();
});

test("a stale renewal cannot publish its balance as the current wallet", async () => {
  await openProtected();
  pass.renewReadingPassLease.mockResolvedValueOnce(response({ lease_version: 2, stale: true, balance_seconds: 0 }));
  await tick(10000);
  expect(text()).toContain("Reading paused");
  expect(mockSetUserBalance).not.toHaveBeenCalledWith(0, "test-reader");
});

test("preview navigation never starts a paid session and page 4 starts only once", async () => {
  await mount("/reader/test-book?p=2");
  await click("Next page");
  expect(text()).toContain("Page 3 manuscript.");
  expect(pass.startReadingPassSession).not.toHaveBeenCalled();
  await click("Use Reading Time to Continue");
  expect(text()).toContain("Page 4 manuscript.");
  await click("Next page");
  expect(text()).toContain("Page 5 manuscript.");
  expect(pass.startReadingPassSession).toHaveBeenCalledTimes(1);
});

test("three heartbeat renewals preserve the page and never refetch its content", async () => {
  await openProtected();
  const article = container.querySelector("article");
  for (let i = 0; i < 3; i++) {
    await tick(10000);
    expect(container.querySelector("article")).toBe(article);
    expect(text()).toContain("Page 4 manuscript.");
    expect(text()).not.toMatch(/unavailable|Opening page|Reading paused/i);
  }
  expect(pass.renewReadingPassLease).toHaveBeenCalledTimes(3);
  expect(pass.getReadingPassPage).toHaveBeenCalledTimes(1);
});

test("a delayed page is loading rather than unavailable", async () => {
  const pending = deferred(); pass.getReadingPassPage.mockReturnValueOnce(pending.promise);
  await mount("/reader/test-book?p=1");
  expect(text()).toContain("Opening page"); expect(text()).not.toMatch(/unavailable/i);
  await act(async () => pending.resolve(page(1)));
  expect(text()).toContain("Page 1 manuscript.");
});

test("a missing or wrong manifest identity never requests a page and can retry", async () => {
  userApi.get.mockResolvedValueOnce({ data: manifest("wrong-book") });
  await mount("/reader/test-book?p=1");
  expect(text()).toContain("This reader edition is not available.");
  expect(pass.getReadingPassPage).not.toHaveBeenCalled();
  await click("Retry reader");
  expect(text()).toContain("Page 1 manuscript.");
});

test.each(["book_slug", "total_pages"])("a page without required %s cannot render", async (field) => {
  const incomplete = page(1); delete incomplete[field];
  pass.getReadingPassPage.mockResolvedValueOnce(incomplete);
  await mount("/reader/test-book?p=1");
  expect(text()).toContain("does not match the selected edition");
  expect(container.querySelector("article")).toBeNull();
});

test("a hanging manifest remains escapable and its request is cancelled on exit", async () => {
  const pending = deferred(); userApi.get.mockReturnValueOnce(pending.promise);
  await mount("/reader/test-book?p=1");
  expect(text()).toContain("Opening reader");
  const config = userApi.get.mock.calls[0][1];
  await click("Library");
  expect(container.querySelector('[data-testid="location"]').textContent).toBe("/library");
  expect(config.signal.aborted).toBe(true);
  await act(async () => pending.resolve({ data: manifest() }));
  expect(pass.getReadingPassPage).not.toHaveBeenCalled();
});

test("renewal requests cannot overlap and expire at the existing grant deadline", async () => {
  await openProtected();
  const pending = deferred(); pass.renewReadingPassLease.mockReturnValueOnce(pending.promise);
  await tick(10000); await tick(10000);
  expect(pass.renewReadingPassLease).toHaveBeenCalledTimes(1);
  await tick(2);
  expect(text()).toContain("expired"); expect(text()).not.toContain("Page 4 manuscript.");
  await act(async () => pending.resolve(response()));
  expect(text()).not.toContain("Page 4 manuscript.");
});

test.each(["Exhausted", "Stale"])("HTTP200 %s cannot authorize content or create a retry loop", async (status) => {
  await openProtected();
  pass.renewReadingPassLease.mockResolvedValueOnce(response({ status, stale: status === "Stale", balance_seconds: status === "Exhausted" ? 0 : 600 }));
  await tick(10000); await tick(30000);
  expect(container.querySelector("article")).toBeNull();
  expect(pass.renewReadingPassLease).toHaveBeenCalledTimes(1);
  expect(pass.getReadingPassPage).toHaveBeenCalledTimes(1);
  expect(pass.endReadingPassSession).toHaveBeenCalled();
});

test("hidden tabs pause without protected refetch, then resume using updated lease", async () => {
  await openProtected();
  Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
  await act(async () => document.dispatchEvent(new Event("visibilitychange")));
  expect(text()).toContain("Reading paused");
  expect(pass.renewReadingPassLease.mock.calls[0][0].active).toBe(false);
  expect(pass.getReadingPassPage).toHaveBeenCalledTimes(1);
  Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
  await act(async () => document.dispatchEvent(new Event("visibilitychange")));
  expect(text()).toContain("Page 4 manuscript.");
  expect(pass.renewReadingPassLease.mock.calls[1][0].lease.version).toBe(2);
});

test("browser navigation back to preview settles before any further billable heartbeat", async () => {
  await openProtected();
  await act(async () => navigate("/reader/test-book?p=2"));
  expect(text()).toContain("Page 2 manuscript.");
  expect(pass.endReadingPassSession).toHaveBeenCalledTimes(1);
  await tick(30000);
  expect(pass.renewReadingPassLease).not.toHaveBeenCalled();
});

test("an already-ended session does not trap Library navigation", async () => {
  await openProtected();
  pass.endReadingPassSession.mockResolvedValueOnce({ ended: false, session_id: "session-1", deducted_seconds: 0 });
  await click("Library");
  expect(container.querySelector('[data-testid="location"]').textContent).toBe("/library");
  expect(pass.endReadingPassSession).toHaveBeenCalledTimes(1);
});

test("page fetch failure can recover on a later successful authorized request", async () => {
  pass.getReadingPassPage.mockRejectedValueOnce({ response: { status: 403, data: { detail: { message: "Lease expired." } } } });
  await openProtected();
  expect(text()).toContain("Lease expired.");
  await click("Continue to this page");
  expect(text()).toContain("Page 4 manuscript."); expect(text()).not.toContain("Lease expired.");
});

test("changing books rejects a late page response and settles the old book lease", async () => {
  const pending = deferred(); pass.getReadingPassPage.mockReturnValueOnce(pending.promise);
  await openProtected();
  await act(async () => navigate("/reader/other-book?p=1"));
  await act(async () => pending.resolve({ ...page(4), content: "<p>OLD SECRET TEXT</p>" }));
  expect(text()).not.toContain("OLD SECRET TEXT");
  expect(text()).toContain("Page 1 manuscript.");
  expect(pass.endReadingPassSession).toHaveBeenCalledTimes(1);
  expect(pass.getReadingPassPage).toHaveBeenLastCalledWith("other-book", 1, null, expect.objectContaining({ signal: expect.anything() }));
});

test("invalid and final page navigation stays bounded", async () => {
  await mount("/reader/test-book?p=99");
  expect(text()).toContain("Page unavailable");
  expect(pass.getReadingPassPage).not.toHaveBeenCalled();
  expect(pass.startReadingPassSession).not.toHaveBeenCalled();
});

test("production never borrows the castle or fixture rights/time metadata", async () => {
  await mount("/reader/test-book?p=1");
  expect(container.querySelector('img[alt="A sepia castle landscape"]')).toBeNull();
  expect(text()).not.toMatch(/Dracula|1897|Verified|1h 42m|Gothic Fiction/);
});

test("saving a page uses the existing position API and reports success", async () => {
  await mount("/reader/test-book?p=1");
  await click("Save current page");
  expect(text()).toContain("Your current page is saved.");
  expect(pass.saveReadingPassPosition).toHaveBeenCalledWith(expect.objectContaining({ bookSlug: "test-book", pageIndex: 1, chapterId: "c1" }));
  expect(userApi.post).not.toHaveBeenCalled();
});

test("failed content plus failed settlement never keeps renewing paid time", async () => {
  pass.getReadingPassPage.mockRejectedValueOnce({ response: { status: 500 } });
  pass.endReadingPassSession.mockRejectedValue(new Error("Network unavailable"));
  await openProtected();
  await tick(30000);
  expect(container.querySelector("article")).toBeNull();
  expect(pass.renewReadingPassLease).not.toHaveBeenCalled();
});

test("visible inactivity pauses reading time at the configured threshold", async () => {
  await openProtected();
  for (let i = 0; i < 12; i++) await tick(10000);
  expect(pass.renewReadingPassLease).toHaveBeenLastCalledWith(expect.objectContaining({ active: false }));
  expect(text()).toContain("Reading paused");
  const count = pass.renewReadingPassLease.mock.calls.length;
  await tick(30000);
  expect(pass.renewReadingPassLease).toHaveBeenCalledTimes(count);
});

test("a lost heartbeat response retries the exact same idempotent request once", async () => {
  await openProtected();
  pass.renewReadingPassLease.mockRejectedValueOnce(new Error("Response lost"));
  await tick(10000);
  expect(pass.renewReadingPassLease).toHaveBeenCalledTimes(2);
  expect(pass.renewReadingPassLease.mock.calls[0][0]).toEqual(pass.renewReadingPassLease.mock.calls[1][0]);
  expect(text()).toContain("Page 4 manuscript.");
  expect(pass.getReadingPassPage).toHaveBeenCalledTimes(1);
});

test("a late session start cannot override a newer same-book browser navigation", async () => {
  const pending = deferred();
  pass.startReadingPassSession.mockReturnValueOnce(pending.promise);
  await mount("/reader/test-book?p=3");
  await click("Use Reading Time to Continue");
  await act(async () => navigate("/reader/test-book?p=2"));
  await act(async () => pending.resolve(response()));
  expect(container.querySelector('[data-testid="location"]').textContent).toContain("?p=2");
  expect(text()).toContain("Page 2 manuscript.");
  expect(pass.endReadingPassSession).toHaveBeenCalledWith({ sessionId: "session-1" }, "reader_v2_start_after_exit");
});

test("a wrong-book or wrong-preview page response never renders content", async () => {
  pass.getReadingPassPage.mockResolvedValueOnce({ ...page(1), book_slug: "wrong-book" });
  await mount("/reader/test-book?p=1");
  expect(text()).toContain("does not match"); expect(container.querySelector("article")).toBeNull();
});

test("history navigation outside the edition closes an existing paid session", async () => {
  await openProtected();
  await act(async () => navigate("/reader/test-book?p=99"));
  expect(text()).toContain("Page unavailable");
  expect(pass.endReadingPassSession).toHaveBeenCalledTimes(1);
  await tick(30000);
  expect(pass.renewReadingPassLease).not.toHaveBeenCalled();
});

test("a prolonged protected-page load is never renewed as active reading", async () => {
  const pending = deferred(); pass.getReadingPassPage.mockReturnValueOnce(pending.promise);
  await openProtected(); await tick(10000);
  expect(pass.renewReadingPassLease).toHaveBeenCalledWith(expect.objectContaining({ active: false }));
  await act(async () => pending.resolve(page(4)));
});
