import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { userApi, USER_TOKEN_KEY } from "./lib/api";
import { toast } from "sonner";

jest.mock("sonner", () => ({ toast: { error: jest.fn() } }));

// Keep the real provider and Axios request/response interceptors. The adapter
// supplies server outcomes; mocking userApi.get would hide refresh races.
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let auth, root, container, adapter, previousAdapter, previousFetch;
const reader = (id = "reader-one", balance = 120) => ({ id, name: id, reading_seconds_balance: balance });
const response = (config, data) => ({ config, status: 200, data, headers: {} });
const failure = (config, status = 401) => Object.assign(new Error(`HTTP ${status}`), { config, response: { config, status, data: { detail: "Access denied" } } });
const refreshResponse = (token, status = 200) => ({ ok: status === 200, status, json: async () => ({ token }) });
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};

function Probe() {
  auth = useAuth();
  return <output>{auth.user ? `${auth.user.id}:${auth.user.reading_seconds_balance}` : String(auth.user)}</output>;
}

async function flush() {
  await act(async () => { for (let index = 0; index < 30; index += 1) await Promise.resolve(); });
}

async function mount() {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => { root.render(<AuthProvider><Probe /></AuthProvider>); });
  await flush();
}

beforeEach(() => {
  auth = null;
  localStorage.clear();
  localStorage.setItem(USER_TOKEN_KEY, "expired-access");
  previousAdapter = userApi.defaults.adapter;
  previousFetch = global.fetch;
  adapter = jest.fn();
  userApi.defaults.adapter = adapter;
  global.fetch = jest.fn();
  toast.error.mockClear();
});

afterEach(async () => {
  if (root) await act(async () => { root.unmount(); });
  root = null;
  container?.remove();
  userApi.defaults.adapter = previousAdapter;
  global.fetch = previousFetch;
  localStorage.clear();
});

test("expired-token bootstrap refreshes once and applies the retried profile without redirecting", async () => {
  global.fetch.mockResolvedValue(refreshResponse("rotated-access"));
  adapter.mockImplementation(async (config) => {
    if (config.headers.Authorization === "Bearer expired-access") throw failure(config);
    return response(config, reader());
  });
  await mount();
  expect(container.textContent).toBe("reader-one:120");
  expect(localStorage.getItem(USER_TOKEN_KEY)).toBe("rotated-access");
  expect(adapter).toHaveBeenCalledTimes(2);
  expect(global.fetch).toHaveBeenCalledTimes(1);
  expect(adapter.mock.calls[0][0]).toMatchObject({ url: "/users/me", skipAuthRedirect: true, timeout: 15000 });
  expect(global.fetch.mock.calls[0][1]).toMatchObject({ method: "POST", credentials: "include", signal: expect.any(AbortSignal) });
  expect(toast.error).not.toHaveBeenCalled();
});

test("refreshUser accepts a successful profile after access-token rotation", async () => {
  let calls = 0;
  global.fetch.mockResolvedValue(refreshResponse("rotated-access"));
  adapter.mockImplementation(async (config) => {
    calls += 1;
    if (calls === 2) throw failure(config);
    return response(config, reader("reader-one", calls === 1 ? 120 : 77));
  });
  await mount();
  let result;
  await act(async () => { result = await auth.refreshUser(); });
  expect(result).toEqual(reader("reader-one", 77));
  expect(container.textContent).toBe("reader-one:77");
  expect(global.fetch).toHaveBeenCalledTimes(1);
});

test("refreshUser clears the current profile on a confirmed terminal refresh 401", async () => {
  global.fetch.mockResolvedValue(refreshResponse(null, 401));
  adapter.mockResolvedValueOnce(response({}, reader())).mockImplementation(async (config) => { throw failure(config); });
  await mount();
  await act(async () => { await auth.refreshUser(); });
  expect(container.textContent).toBe("false");
  expect(localStorage.getItem(USER_TOKEN_KEY)).toBeNull();
  expect(global.fetch).toHaveBeenCalledTimes(1);
  expect(adapter).toHaveBeenCalledTimes(2);
});

test("concurrent and delayed old-token 401s share one refresh and reuse its rotated grant", async () => {
  const refresh = deferred();
  const lateResponse = deferred();
  let lateConfig;
  global.fetch.mockImplementation(() => refresh.promise);
  adapter.mockImplementation(async (config) => {
    if (config.headers.Authorization === "Bearer expired-access") {
      if (config.url === "/users/me/transactions") { lateConfig = config; return lateResponse.promise; }
      throw failure(config);
    }
    return response(config, config.url === "/users/me" ? reader() : []);
  });
  await mount();
  const manifest = userApi.get("/reader/book/isolated/manifest", { skipAuthRedirect: true });
  const transactions = userApi.get("/users/me/transactions", { skipAuthRedirect: true });
  await flush();
  expect(global.fetch).toHaveBeenCalledTimes(1);
  await act(async () => { refresh.resolve(refreshResponse("rotated-access")); });
  await flush();
  await act(async () => { lateResponse.reject(failure(lateConfig)); await Promise.all([manifest, transactions]); });
  expect(global.fetch).toHaveBeenCalledTimes(1);
  expect(adapter).toHaveBeenCalledTimes(6);
  expect(container.textContent).toBe("reader-one:120");
});

test.each(["refresh", "retried profile"])("a terminal 401 from the %s clears startup authentication without looping", async (stage) => {
  global.fetch.mockResolvedValue(refreshResponse("rotated-access", stage === "refresh" ? 401 : 200));
  adapter.mockImplementation(async (config) => { throw failure(config); });
  await mount();
  expect(container.textContent).toBe("false");
  expect(localStorage.getItem(USER_TOKEN_KEY)).toBeNull();
  expect(global.fetch).toHaveBeenCalledTimes(1);
  expect(adapter).toHaveBeenCalledTimes(stage === "refresh" ? 1 : 2);
  expect(toast.error).not.toHaveBeenCalled();
});

test("a profile 403 stays denied without refreshing or deleting its credential", async () => {
  adapter.mockImplementation(async (config) => { throw failure(config, 403); });
  await mount();
  expect(container.textContent).toBe("false");
  expect(localStorage.getItem(USER_TOKEN_KEY)).toBe("expired-access");
  expect(global.fetch).not.toHaveBeenCalled();
  expect(adapter).toHaveBeenCalledTimes(1);
});

test("a retryable refresh outage fails closed without erasing the credential", async () => {
  global.fetch.mockResolvedValue(refreshResponse(null, 503));
  adapter.mockImplementation(async (config) => { throw failure(config); });
  await mount();
  expect(container.textContent).toBe("false");
  expect(localStorage.getItem(USER_TOKEN_KEY)).toBe("expired-access");
  expect(global.fetch).toHaveBeenCalledTimes(1);
  expect(adapter).toHaveBeenCalledTimes(1);
});

test("logout keeps its issued credential but a late refresh cannot restore the signed-out session", async () => {
  const refresh = deferred();
  global.fetch.mockImplementation(() => refresh.promise);
  adapter.mockImplementation(async (config) => { throw failure(config); });
  await mount();
  await act(async () => { auth.userLogout(); });
  await flush();
  const logout = adapter.mock.calls.map(([config]) => config).find((config) => config.url === "/users/logout");
  expect(logout).toMatchObject({ skipAuthRedirect: true, skipAuthRefresh: true, timeout: 15000 });
  expect(logout.headers.Authorization).toBe("Bearer expired-access");
  await act(async () => { refresh.resolve(refreshResponse("late-access")); });
  await flush();
  expect(container.textContent).toBe("false");
  expect(localStorage.getItem(USER_TOKEN_KEY)).toBeNull();
  expect(global.fetch).toHaveBeenCalledTimes(1);
  expect(adapter).toHaveBeenCalledTimes(2);
});

test.each([200, 401])("a pending old refresh returning %s cannot overwrite or erase a newer successful login", async (status) => {
  const refresh = deferred();
  global.fetch.mockImplementation(() => refresh.promise);
  adapter.mockImplementation(async (config) => {
    if (config.url === "/users/login") return response(config, { token: "new-account-access", user: reader("reader-new") });
    throw failure(config);
  });
  await mount();
  await act(async () => { await auth.userLogin("isolated@example.test", "fixture-password"); });
  await act(async () => { refresh.resolve(refreshResponse("late-old-account-access", status)); });
  await flush();
  expect(container.textContent).toBe("reader-new:120");
  expect(localStorage.getItem(USER_TOKEN_KEY)).toBe("new-account-access");
  expect(adapter).toHaveBeenCalledTimes(2);
});

test("an identity change between request interceptors cannot send a request as the newer account", async () => {
  adapter.mockImplementation(async (config) => response(config, reader("reader-new")));
  const interceptor = userApi.interceptors.request.use((config) => {
    // Two microtasks place the account change between the real identity capture
    // and credential attachment, rather than replacing either interceptor.
    Promise.resolve().then(() => Promise.resolve().then(() => localStorage.setItem(USER_TOKEN_KEY, "external-login-access")));
    return config;
  });
  try {
    await expect(userApi.get("/users/me", { skipAuthRedirect: true })).rejects.toMatchObject({ authSuperseded: true });
    expect(adapter).not.toHaveBeenCalled();
    expect(global.fetch).not.toHaveBeenCalled();
    expect(localStorage.getItem(USER_TOKEN_KEY)).toBe("external-login-access");
  } finally {
    userApi.interceptors.request.eject(interceptor);
  }
});

test.each([200, 401])("a late startup %s cannot replace or erase a direct Google/OTP-style token change", async (status) => {
  const startup = deferred();
  let startupConfig;
  adapter.mockImplementation(async (config) => {
    if (config.headers.Authorization === "Bearer expired-access") { startupConfig = config; return startup.promise; }
    return response(config, reader("reader-new"));
  });
  await mount();
  localStorage.setItem(USER_TOKEN_KEY, "external-login-access");
  await act(async () => { await auth.refreshUser(); });
  await act(async () => {
    if (status === 200) startup.resolve(response(startupConfig, reader("reader-old")));
    else startup.reject(failure(startupConfig));
  });
  await flush();
  expect(container.textContent).toBe("reader-new:120");
  expect(localStorage.getItem(USER_TOKEN_KEY)).toBe("external-login-access");
  expect(global.fetch).not.toHaveBeenCalled();
});

test("a late reader balance update cannot alter a newer account", async () => {
  adapter.mockImplementation(async (config) => response(config, config.url === "/users/login"
    ? { token: "new-account-access", user: reader("reader-new", 90) }
    : reader()));
  await mount();
  const updateOldReaderBalance = auth.setUserBalance;
  await act(async () => { await auth.userLogin("isolated@example.test", "fixture-password"); });
  await act(async () => { updateOldReaderBalance(12, "reader-one"); });
  expect(container.textContent).toBe("reader-new:90");
  await act(async () => { auth.setUserBalance(42, "reader-new"); });
  expect(container.textContent).toBe("reader-new:42");
  await act(async () => { auth.setUserBalance(-1, "reader-new"); auth.setUserBalance("99", "reader-new"); });
  expect(container.textContent).toBe("reader-new:42");
});

test("a delayed profile cannot overwrite a newer validated reader balance", async () => {
  const profile = deferred();
  let profileConfig;
  adapter.mockResolvedValueOnce(response({}, reader())).mockImplementation(async (config) => { profileConfig = config; return profile.promise; });
  await mount();
  let refreshing;
  await act(async () => { refreshing = auth.refreshUser(); });
  await act(async () => { auth.setUserBalance(42, "reader-one"); });
  await act(async () => { profile.resolve(response(profileConfig, reader("reader-one", 120))); await refreshing; });
  expect(container.textContent).toBe("reader-one:42");
});
