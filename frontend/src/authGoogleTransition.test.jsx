import React, { act } from "react";
import { createRoot } from "react-dom/client";
const mockGet = jest.fn();
const mockPost = jest.fn();
let mockGoogleOptions;
let mockSearch = "";
const mockDestination = jest.fn();
jest.mock("./lib/api", () => ({
  ...jest.requireActual("./lib/api"),
  api: { get: jest.fn() },
  userApi: { get: (...args) => mockGet(...args), post: (...args) => mockPost(...args) },
}));
jest.mock("react-router-dom", () => ({ Link: () => null, Navigate: ({ to }) => { mockDestination(to); return <div data-testid="destination">{to}</div>; }, useNavigate: () => jest.fn(), useSearchParams: () => [new URLSearchParams(mockSearch)] }), { virtual: true });
jest.mock("@react-oauth/google", () => ({ useGoogleLogin: (options) => { mockGoogleOptions = options; return jest.fn(); } }));
jest.mock("./hooks/useSEO", () => jest.fn());
import { AuthProvider, useAuth } from "./context/AuthContext";
process.env.REACT_APP_GOOGLE_CLIENT_ID = "fixture-client";
const { default: Login, safeSignInDestination } = require("./pages/Login");
import { USER_TOKEN_KEY } from "./lib/api";
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let auth;
function Probe() { auth = useAuth(); return <div>{auth.user === null ? "resolving" : auth.user ? auth.user.id : "anonymous"}</div>; }
let root, container;
beforeEach(async () => {
  localStorage.clear(); mockGet.mockReset(); mockPost.mockReset(); mockDestination.mockClear(); mockSearch = "";
  container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container);
  await act(async () => { root.render(<AuthProvider><Probe /></AuthProvider>); });
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });
test("Google verification resolves once without redundant profile hydration", async () => {
  let resolve; mockPost.mockReturnValue(new Promise(r => { resolve = r; }));
  let first, duplicate;
  await act(async () => { first = auth.userGoogleLogin("test-credential"); duplicate = auth.userGoogleLogin("test-credential"); });
  expect(first).toBe(duplicate); expect(mockPost).toHaveBeenCalledTimes(1);
  expect(container.textContent).toBe("resolving");
  await act(async () => { resolve({ data: { token: "test-session", user: { id: "reader" } } }); await first; });
  expect(container.textContent).toBe("reader"); expect(mockGet).not.toHaveBeenCalled();
  expect(localStorage.getItem(USER_TOKEN_KEY)).toBe("test-session");
});
test.each([401, 403, 503, undefined])("verification error %s returns to anonymous without a credential", async status => {
  mockPost.mockRejectedValue({ response: status ? { status } : undefined });
  await act(async () => { await expect(auth.userGoogleLogin("invalid")).rejects.toBeDefined(); });
  expect(container.textContent).toBe("anonymous"); expect(localStorage.getItem(USER_TOKEN_KEY)).toBeNull();
});
test("incomplete session response is rejected", async () => {
  mockPost.mockResolvedValue({ data: { token: "incomplete" } });
  await act(async () => { await expect(auth.userGoogleLogin("test")).rejects.toThrow("incomplete session"); });
  expect(localStorage.getItem(USER_TOKEN_KEY)).toBeNull();
});
test("logout supersedes an in-flight Google result", async () => {
  let resolve; mockPost.mockImplementation((path) => path === "/auth/google" ? new Promise(r => { resolve = r; }) : Promise.resolve({}));
  let pending; await act(async () => { pending = auth.userGoogleLogin("test"); });
  await act(async () => auth.userLogout());
  await act(async () => { resolve({ data: { token: "stale", user: { id: "reader" } } }); await expect(pending).rejects.toThrow("superseded"); });
  expect(container.textContent).toBe("anonymous"); expect(localStorage.getItem(USER_TOKEN_KEY)).toBeNull();
});
test.each(["https://other.test", "//other.test", "/%2fother.test", "/\\other.test", "/login", "/LOGIN", "/auth/callback", "/%6cogin", "/bad%ZZ"])("rejects unsafe return destination %s", value => {
  expect(safeSignInDestination(value)).toBe("/account");
});
test.each(["/reader/dracula?page=2", "/pricing", "/account", "/library"])("preserves safe destination %s", value => {
  expect(safeSignInDestination(value)).toBe(value);
});

async function showLogin() {
  await act(async () => root.render(<AuthProvider><Login /></AuthProvider>));
}
test("returned OAuth credential replaces the form with status until the real session resolves", async () => {
  let resolve; mockPost.mockReturnValue(new Promise(r => { resolve = r; }));
  await showLogin();
  expect(container.querySelector('[data-testid="user-login-submit"]')).not.toBeNull();
  let completion;
  await act(async () => { completion = mockGoogleOptions.onSuccess({ access_token: "fixture-credential" }); });
  expect(container.querySelector('[data-testid="user-login-submit"]')).toBeNull();
  expect(container.querySelector('[role="status"]').textContent).toBe("Signing you in…");
  await act(async () => { resolve({ data: { token: "fixture-session", user: { id: "reader" } } }); await completion; });
  expect(container.querySelector('[data-testid="destination"]').textContent).toBe("/library");
  expect(mockGet).not.toHaveBeenCalled();
});
test("Google completion preserves the requested Reader return route", async () => {
  mockSearch = "next=%2Freader%2Fdracula%3Fpage%3D2";
  mockPost.mockResolvedValue({ data: { token: "fixture-session", user: { id: "reader" } } });
  await showLogin();
  await act(async () => { await mockGoogleOptions.onSuccess({ access_token: "fixture" }); });
  expect(container.querySelector('[data-testid="destination"]').textContent).toBe("/reader/dracula?page=2");
});
test("failed Google verification restores the retryable sign-in form", async () => {
  mockPost.mockRejectedValue({ response: { status: 401 } }); await showLogin();
  await act(async () => { await mockGoogleOptions.onSuccess({ access_token: "expired" }); });
  expect(container.querySelector('[data-testid="user-login-submit"]')).not.toBeNull();
  expect(mockDestination).not.toHaveBeenCalled();
});
test("an older startup profile cannot overwrite the verified Google identity", async () => {
  await act(async () => root.unmount()); root = createRoot(container);
  localStorage.setItem(USER_TOKEN_KEY, "old-session");
  let resolveOld; mockGet.mockReturnValue(new Promise(r => { resolveOld = r; }));
  await act(async () => root.render(<AuthProvider><Probe /></AuthProvider>));
  mockPost.mockResolvedValue({ data: { token: "new-session", user: { id: "new-reader" } } });
  await act(async () => { await auth.userGoogleLogin("fixture"); });
  await act(async () => { resolveOld({ data: { id: "old-reader" } }); });
  expect(container.textContent).toBe("new-reader");
  expect(localStorage.getItem(USER_TOKEN_KEY)).toBe("new-session");
});
test("a duplicate callback emits one completion and performs one verification", async () => {
  let resolve; mockPost.mockReturnValue(new Promise(r => { resolve = r; })); await showLogin();
  let first, second;
  await act(async () => {
    first = mockGoogleOptions.onSuccess({ access_token: "fixture" });
    second = mockGoogleOptions.onSuccess({ access_token: "fixture" });
  });
  expect(mockPost).toHaveBeenCalledTimes(1);
  await act(async () => { resolve({ data: { token: "session", user: { id: "reader" } } }); await first; await second; });
  expect(container.querySelector('[data-testid="destination"]').textContent).toBe("/library");
});

test("back/forward-cache restoration resolves the current session before showing a form", async () => {
  await showLogin(); localStorage.setItem(USER_TOKEN_KEY, "restored-session");
  let resolve; mockGet.mockReturnValue(new Promise(r => { resolve = r; }));
  const event = new Event("pageshow"); Object.defineProperty(event, "persisted", { value: true });
  await act(async () => window.dispatchEvent(event));
  expect(container.querySelector('[data-testid="user-login-submit"]')).toBeNull();
  expect(container.querySelector('[role="status"]').textContent).toBe("Loading sign-in…");
  await act(async () => { resolve({ data: { id: "restored-reader" } }); });
  expect(container.querySelector('[data-testid="destination"]').textContent).toBe("/account");
});

test.each(["onError", "onNonOAuthError"])("provider %s leaves a retryable form without submitting credentials", async callback => {
  await showLogin(); await act(async () => mockGoogleOptions[callback]({ type: "popup_closed" }));
  expect(container.querySelector('[data-testid="user-login-submit"]')).not.toBeNull();
  expect(mockPost).not.toHaveBeenCalled(); expect(mockDestination).not.toHaveBeenCalled();
});
test("a callback without a credential does not establish a session", async () => {
  await showLogin(); await act(async () => mockGoogleOptions.onSuccess({}));
  expect(mockPost).not.toHaveBeenCalled(); expect(mockDestination).not.toHaveBeenCalled();
});
test("an expired restored session cannot navigate as authenticated", async () => {
  await showLogin(); localStorage.setItem(USER_TOKEN_KEY, "expired-session");
  mockGet.mockRejectedValue({ response: { status: 401 } });
  const event = new Event("pageshow"); Object.defineProperty(event, "persisted", { value: true });
  await act(async () => { window.dispatchEvent(event); });
  expect(localStorage.getItem(USER_TOKEN_KEY)).toBeNull();
  expect(container.querySelector('[data-testid="user-login-submit"]')).not.toBeNull();
  expect(mockDestination).not.toHaveBeenCalled();
});
