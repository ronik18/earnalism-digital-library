import React, { act, useEffect } from "react";
import { createRoot } from "react-dom/client";

const mockUserApiGet = jest.fn();
const mockUserApiPost = jest.fn();
const mockGetReadingPassConfig = jest.fn();
const mockGetReadingPassDevices = jest.fn();
const mockStateObserver = jest.fn();

jest.mock("./lib/api", () => ({
  ...jest.requireActual("./lib/api"),
  TOKEN_KEY: "earnalism_admin_token",
  USER_TOKEN_KEY: "earnalism_user_token",
  api: { get: jest.fn(), post: jest.fn() },
  userApi: {
    get: (...args) => mockUserApiGet(...args),
    post: (...args) => mockUserApiPost(...args),
  },
  formatMinutes: (seconds) => `${seconds}s`,
}));

jest.mock("./lib/readingPassApi", () => ({
  getReadingPassConfig: (...args) => mockGetReadingPassConfig(...args),
  getReadingPassDevices: (...args) => mockGetReadingPassDevices(...args),
  revokeReadingPassDevice: jest.fn(),
}));

jest.mock("./hooks/useSEO", () => jest.fn());
jest.mock("./lib/funnelAnalytics", () => ({ trackFunnelEvent: jest.fn() }));
jest.mock("./experiences-v2/shared/ExperienceBottomNavigation", () => () => null);
jest.mock("sonner", () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock("react-router-dom", () => ({
  Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a>,
  Navigate: () => null,
  useLocation: () => ({ search: "" }),
  useNavigate: () => jest.fn(),
}), { virtual: true });

import { AuthProvider, useAuth } from "./context/AuthContext";
import Account from "./pages/Account";
import { USER_TOKEN_KEY } from "./lib/api";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function user(id = "reader-one") {
  return {
    id,
    name: "Isolated Reader",
    email: `${id}@example.test`,
    reading_seconds_balance: 120,
  };
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

async function flush() {
  await act(async () => {
    for (let index = 0; index < 10; index += 1) await Promise.resolve();
  });
}

function render(ui) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(ui));
  return {
    container,
    async cleanup() {
      await act(async () => { root.unmount(); });
      container.remove();
    },
  };
}

function AuthProbe() {
  const auth = useAuth();
  useEffect(() => { mockStateObserver(auth); }, [auth]);
  return (
    <>
      <output data-testid="user-id">{auth.user && typeof auth.user === "object" ? auth.user.id : String(auth.user)}</output>
      <button data-testid="auth-probe-login" type="button" onClick={() => auth.userLogin("reader@example.test", "fixture-password")}>Sign in fixture</button>
      <button data-testid="auth-probe-refresh" type="button" onClick={() => auth.refreshUser()}>Refresh fixture</button>
    </>
  );
}

function count(path) {
  return mockUserApiGet.mock.calls.filter(([requested]) => requested === path).length;
}

describe("AuthProvider and Account lifecycle", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    localStorage.clear();
    mockUserApiGet.mockReset();
    mockUserApiPost.mockReset();
    mockGetReadingPassConfig.mockReset();
    mockGetReadingPassDevices.mockReset();
    mockStateObserver.mockReset();
    mockGetReadingPassConfig.mockResolvedValue({ enabled: true });
    mockGetReadingPassDevices.mockResolvedValue([]);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  test("mounting the real provider and Account settles request counts when /users/me returns equal but distinct objects", async () => {
    localStorage.setItem(USER_TOKEN_KEY, "isolated-token");
    mockUserApiGet.mockImplementation((path) => {
      if (path === "/users/me") return Promise.resolve({ data: { ...user() } });
      if (path === "/users/me/transactions") return Promise.resolve({ data: [] });
      return Promise.reject(new Error(`unexpected path ${path}`));
    });

    const mounted = render(<AuthProvider><Account /></AuthProvider>);
    await flush();

    const settled = {
      me: count("/users/me"),
      transactions: count("/users/me/transactions"),
      config: mockGetReadingPassConfig.mock.calls.length,
      devices: mockGetReadingPassDevices.mock.calls.length,
    };
    await flush();

    expect(settled).toEqual({ me: 2, transactions: 1, config: 1, devices: 1 });
    expect({
      me: count("/users/me"),
      transactions: count("/users/me/transactions"),
      config: mockGetReadingPassConfig.mock.calls.length,
      devices: mockGetReadingPassDevices.mock.calls.length,
    }).toEqual(settled);

    await mounted.cleanup();
    await flush();
    expect(count("/users/me")).toBe(2);
    expect(count("/users/me/transactions")).toBe(1);
  });

  test("an actual account change refreshes Account resources once without restoring the prior balance", async () => {
    localStorage.setItem(USER_TOKEN_KEY, "isolated-token");
    mockUserApiGet.mockImplementation((path) => {
      if (path === "/users/me") {
        const current = count("/users/me") <= 2 ? user("reader-first") : user("reader-second");
        return Promise.resolve({ data: { ...current } });
      }
      if (path === "/users/me/transactions") return Promise.resolve({ data: [] });
      return Promise.reject(new Error(`unexpected path ${path}`));
    });
    mockUserApiPost.mockResolvedValue({
      data: { token: "second-token", user: { ...user("reader-second"), reading_seconds_balance: 77 } },
    });

    const mounted = render(<AuthProvider><Account /><AuthProbe /></AuthProvider>);
    await flush();
    const login = mounted.container.querySelector('[data-testid="auth-probe-login"]');
    expect(login).not.toBeNull();
    await act(async () => { login.dispatchEvent(new MouseEvent("click", { bubbles: true })); });
    await flush();

    expect(mounted.container.querySelector('[data-testid="user-id"]')?.textContent).toBe("reader-second");
    expect({
      me: count("/users/me"),
      transactions: count("/users/me/transactions"),
      config: mockGetReadingPassConfig.mock.calls.length,
      devices: mockGetReadingPassDevices.mock.calls.length,
    }).toEqual({ me: 3, transactions: 2, config: 2, devices: 2 });
    await mounted.cleanup();
  });

  test("Account presents human-readable active sessions and collapses previous sessions", async () => {
    localStorage.setItem(USER_TOKEN_KEY, "isolated-token");
    mockUserApiGet.mockImplementation((path) => {
      if (path === "/users/me") return Promise.resolve({ data: { ...user() } });
      if (path === "/users/me/transactions") return Promise.resolve({ data: [] });
      return Promise.reject(new Error(`unexpected path ${path}`));
    });
    mockGetReadingPassDevices.mockResolvedValue([
      {
        session_id: "current-session",
        status: "active",
        current: true,
        device_label: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
        last_seen_at: "2026-09-24T06:00:00Z",
      },
      {
        session_id: "previous-session",
        status: "revoked",
        current: false,
        device_label: "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
        last_seen_at: "2026-09-16T09:54:00Z",
      },
    ]);

    const mounted = render(<AuthProvider><Account /></AuthProvider>);
    await flush();

    expect(mounted.container.querySelector('[data-testid="account-balance"]')?.textContent).toContain("India Pilot Access");
    expect(mounted.container.querySelector('[data-testid="account-reading-pass-status"]')?.textContent).toContain("Prepared for future eligible editions.");
    expect(mounted.container.querySelector('[data-testid="account-active-sessions"]')?.textContent).toContain("Chrome on Mac");
    expect(mounted.container.querySelector('[data-testid="account-active-sessions"]')?.textContent).toContain("This device");
    expect(mounted.container.querySelector('[data-testid="account-page"]')?.textContent).not.toContain("Mozilla/5.0");
    const previousSessions = mounted.container.querySelector('[data-testid="account-previous-sessions"]');
    expect(previousSessions?.open).toBe(false);
    expect(previousSessions?.querySelector("summary")?.textContent).toContain("Show previous sessions (1)");
    expect(previousSessions?.textContent).toContain("Safari on iPhone");
    expect(mounted.container.querySelector('[aria-label="Revoke Chrome on Mac session"]')).not.toBeNull();

    await mounted.cleanup();
  });

  test("a late startup verification failure cannot erase a newer successful login", async () => {
    localStorage.setItem(USER_TOKEN_KEY, "stale-token");
    const startup = deferred();
    mockUserApiGet.mockImplementation(() => startup.promise);
    mockUserApiPost.mockResolvedValue({ data: { token: "fresh-token", user: user("reader-new") } });

    const mounted = render(<AuthProvider><AuthProbe /></AuthProvider>);
    await flush();
    const button = [...mounted.container.querySelectorAll("button")][0];
    await act(async () => { button.dispatchEvent(new MouseEvent("click", { bubbles: true })); });
    await flush();
    expect(mounted.container.querySelector('[data-testid="user-id"]')?.textContent).toBe("reader-new");

    await act(async () => { startup.reject({ response: { status: 401 } }); });
    await flush();
    expect(mounted.container.querySelector('[data-testid="user-id"]')?.textContent).toBe("reader-new");
    expect(localStorage.getItem(USER_TOKEN_KEY)).toBe("fresh-token");
    await mounted.cleanup();
  });

  test("a recoverable startup timeout reaches the login state without deleting its token", async () => {
    localStorage.setItem(USER_TOKEN_KEY, "recoverable-token");
    mockUserApiGet.mockRejectedValue(new Error("timeout"));

    const mounted = render(<AuthProvider><AuthProbe /></AuthProvider>);
    await flush();
    expect(mounted.container.querySelector('[data-testid="user-id"]')?.textContent).toBe("false");
    expect(localStorage.getItem(USER_TOKEN_KEY)).toBe("recoverable-token");
    await mounted.cleanup();
  });

  test("a stale refresh response and an unmounted provider cannot replace newer authentication", async () => {
    localStorage.setItem(USER_TOKEN_KEY, "initial-token");
    const refresh = deferred();
    mockUserApiGet
      .mockResolvedValueOnce({ data: user("reader-old") })
      .mockImplementationOnce(() => refresh.promise);
    mockUserApiPost.mockResolvedValue({ data: { token: "replacement-token", user: user("reader-replacement") } });

    const mounted = render(<AuthProvider><AuthProbe /></AuthProvider>);
    await flush();
    const [login, refreshButton] = mounted.container.querySelectorAll("button");
    await act(async () => { refreshButton.dispatchEvent(new MouseEvent("click", { bubbles: true })); });
    await act(async () => { login.dispatchEvent(new MouseEvent("click", { bubbles: true })); });
    await flush();
    await act(async () => { refresh.resolve({ data: user("reader-old") }); });
    await flush();
    expect(mounted.container.querySelector('[data-testid="user-id"]')?.textContent).toBe("reader-replacement");

    const lateStartup = deferred();
    mockUserApiGet.mockImplementation(() => lateStartup.promise);
    const unmounted = render(<AuthProvider><AuthProbe /></AuthProvider>);
    await flush();
    await unmounted.cleanup();
    await act(async () => { lateStartup.resolve({ data: user("should-not-apply") }); });
    await flush();
    expect(mockStateObserver.mock.calls.some(([auth]) => auth?.user?.id === "should-not-apply")).toBe(false);
    await mounted.cleanup();
  });
});
