import axios from "axios";
import { toast } from "sonner";

export function resolveBackendUrl() {
  // The India-only public Reader release uses the same-origin Vercel proxy so
  // Railway can verify a provider-derived country assertion. This flag is a
  // production build setting, not a browser-controlled fallback.
  if (process.env.NODE_ENV === "production" && process.env.REACT_APP_RELEASE_PROXY_ENABLED === "true") {
    return "";
  }
  const configured = (
    process.env.REACT_APP_BACKEND_URL ||
    process.env.REACT_APP_API_URL ||
    ""
  ).trim();

  if (process.env.NODE_ENV !== "production") return configured;
  if (!configured || configured.includes("<") || configured.includes("yourdomain.com")) {
    return "";
  }
  if (configured.startsWith("/")) {
    return configured.replace(/\/$/, "");
  }
  if (configured.startsWith("/")) {
    return configured.replace(/\/$/, "");
  }
  try {
    const url = new URL(configured);
    if (["localhost", "127.0.0.1", "0.0.0.0"].includes(url.hostname)) {
      // Production-like UAT builds must retain their explicit loopback API
      // origin.  All normal production builds continue to reject local hosts.
      return process.env.REACT_APP_UAT_LOCAL === "true" ? configured : "";
    }
  } catch {
    return "";
  }
  return configured;
}

export const BACKEND_URL = resolveBackendUrl();
const NORMALIZED_BACKEND_URL = BACKEND_URL ? BACKEND_URL.replace(/\/$/, "") : "";
export const API = NORMALIZED_BACKEND_URL
  ? (NORMALIZED_BACKEND_URL.endsWith("/api") ? NORMALIZED_BACKEND_URL : `${NORMALIZED_BACKEND_URL}/api`)
  : "/api";

export const TOKEN_KEY = "earnalism_admin_token";
export const USER_TOKEN_KEY = "earnalism_user_token";
export const SESSION_EXPIRED_MESSAGE = "Session expired, please login again.";
export const NEW_LOGIN_MESSAGE = "You’ve been logged out: new login detected.";

let authRedirectInFlight = false;
let userAuthState = { token: null, version: 0, tokens: new Set() };
let userRefreshInFlight = null;
const DEV_API_TIMING = process.env.NODE_ENV === "development";
axios.defaults.withCredentials = true;

function isBrowser() {
  return typeof window !== "undefined" && typeof window.location !== "undefined";
}

function currentUserAuthState() {
  const token = isBrowser() ? localStorage.getItem(USER_TOKEN_KEY) : null;
  // Login, logout, and Google/OTP callbacks can change storage directly. Token
  // rotation below updates this same session; an external change starts a new one.
  if (token !== userAuthState.token) {
    userAuthState = { token, version: userAuthState.version + 1, tokens: new Set(token ? [token] : []) };
  }
  return userAuthState;
}

export function getUserAuthSessionVersion() {
  return currentUserAuthState().version;
}

export function isUserAuthSessionCurrent(version) {
  return currentUserAuthState().version === version;
}

function supersededAuthError() {
  const error = new axios.CanceledError("A newer sign-in or sign-out superseded this request.");
  error.authSuperseded = true;
  return error;
}

function requestUserToken(config) {
  const header = config.headers?.Authorization || config.headers?.authorization || "";
  return /^Bearer\s+/i.test(header) ? header.replace(/^Bearer\s+/i, "") : config._userAuthRequestToken;
}

function requestPath(config = {}) {
  const rawUrl = config.url || "";
  if (!isBrowser()) return rawUrl;

  try {
    if (/^https?:\/\//i.test(rawUrl)) return new URL(rawUrl).pathname;
    // Global Axios calls already include /api in their root-relative URL.
    // Prefixing API again hides them from the authenticated-user 401 handler.
    if (!config.baseURL && rawUrl.startsWith("/")) return new URL(rawUrl, window.location.origin).pathname;
    const basePath = new URL(config.baseURL || API, window.location.origin).pathname.replace(/\/$/, "");
    const rawPath = rawUrl.startsWith("/") ? rawUrl : `/${rawUrl}`;
    return `${basePath}${rawPath}`.replace(/\/{2,}/g, "/");
  } catch {
    return rawUrl;
  }
}

function nowMs() {
  if (typeof performance !== "undefined" && typeof performance.now === "function") {
    return performance.now();
  }
  return Date.now();
}

function installDevApiTiming(instance) {
  if (!DEV_API_TIMING) return;
  instance.interceptors.request.use((config) => {
    config.metadata = { ...(config.metadata || {}), startedAt: nowMs() };
    return config;
  });
  instance.interceptors.response.use(
    (response) => {
      const startedAt = response.config?.metadata?.startedAt;
      if (startedAt) {
        const duration = Math.round(nowMs() - startedAt);
        // Development-only latency breadcrumb. Never logs bodies, tokens, or uploaded content.
        // eslint-disable-next-line no-console
        console.debug(`[api] ${String(response.config.method || "GET").toUpperCase()} ${requestPath(response.config)} ${response.status} ${duration}ms`);
      }
      return response;
    },
    (error) => {
      const startedAt = error.config?.metadata?.startedAt;
      if (startedAt) {
        const duration = Math.round(nowMs() - startedAt);
        const status = error.response?.status || "ERR";
        // Development-only latency breadcrumb. Never logs bodies, tokens, or uploaded content.
        // eslint-disable-next-line no-console
        console.debug(`[api] ${String(error.config.method || "GET").toUpperCase()} ${requestPath(error.config)} ${status} ${duration}ms`);
      }
      return Promise.reject(error);
    },
  );
}

function isPublicAuthPath(path) {
  return [
    "/api/auth/login",
    "/api/users/login",
    "/api/users/signup",
    "/api/users/refresh",
    "/api/auth/google",
    "/api/auth/otp/request",
    "/api/auth/otp/verify",
  ].includes(path);
}

function tokenTypeForPath(path, fallback) {
  if (path.startsWith("/api/admin/") || path === "/api/auth/me" || path === "/api/auth/change-password") {
    return "admin";
  }
  if (
    path.startsWith("/api/users/") ||
    path.startsWith("/api/reader/") ||
    path.startsWith("/api/reading/") ||
    path.startsWith("/api/reading-pass/") ||
    path.startsWith("/api/bookmarks") ||
    path === "/api/payments/topup" ||
    path === "/api/payments/verify" ||
    path === "/api/payments/me/intents" ||
    path.startsWith("/api/payments/_simulate")
  ) {
    return "user";
  }
  return fallback;
}

function clearToken(tokenType) {
  if (tokenType === "admin") localStorage.removeItem(TOKEN_KEY);
  else if (tokenType === "user") localStorage.removeItem(USER_TOKEN_KEY);
  else {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_TOKEN_KEY);
  }
}

function currentPath() {
  if (!isBrowser()) return "/";
  return `${window.location.pathname}${window.location.search}`;
}

function loginUrl(tokenType) {
  const path = tokenType === "admin" ? "/admin/login" : "/login";
  const next = currentPath();
  const params = new URLSearchParams({ expired: "1" });
  if (!next.startsWith(path)) params.set("next", next);
  return `${path}?${params.toString()}`;
}

export function handleSessionExpired(tokenType = "user", message = SESSION_EXPIRED_MESSAGE) {
  if (!isBrowser()) return;
  clearToken(tokenType);

  const path = window.location.pathname;
  if (path === "/login" || path === "/admin/login") return;
  if (authRedirectInFlight) return;
  authRedirectInFlight = true;

  toast.error(message || SESSION_EXPIRED_MESSAGE);
  window.location.assign(loginUrl(tokenType));
}

function refreshUserAccessToken(version) {
  const session = currentUserAuthState();
  if (session.version !== version) return Promise.reject(supersededAuthError());
  if (!isBrowser() || !session.token) return Promise.resolve(null);
  if (userRefreshInFlight?.version === version) return userRefreshInFlight.promise;

  const originalToken = session.token;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  const pending = { version, promise: null };
  pending.promise = (async () => {
    const response = await fetch(`${API}/users/refresh`, {
      method: "POST",
      credentials: "include",
      signal: controller.signal,
      headers: { "Content-Type": "application/json" },
    });
    if (!isUserAuthSessionCurrent(version) || session.token !== originalToken) throw supersededAuthError();
    if (response.status === 401) return null;
    if (!response.ok) {
      const error = new Error("Session verification could not finish. Please try again.");
      error.response = { status: response.status };
      throw error;
    }
    const data = await response.json();
    if (!isUserAuthSessionCurrent(version) || session.token !== originalToken) throw supersededAuthError();
    if (typeof data?.token !== "string" || !data.token) throw new Error("Session verification returned no access token.");
    localStorage.setItem(USER_TOKEN_KEY, data.token);
    session.token = data.token;
    session.tokens.add(data.token);
    return data.token;
  })().finally(() => {
    clearTimeout(timeout);
    if (userRefreshInFlight === pending) userRefreshInFlight = null;
  });
  userRefreshInFlight = pending;
  return pending.promise;
}

function shouldHandleAuth401(error, fallbackTokenType) {
  const status = error?.response?.status;
  const config = error?.config || {};
  if (status !== 401) return null;

  const path = requestPath(config);
  if (isPublicAuthPath(path)) return null;
  return tokenTypeForPath(path, fallbackTokenType);
}

function installAuth401Handler(instance, fallbackTokenType) {
  instance.interceptors.request.use((config) => {
    const path = requestPath(config);
    if (!isPublicAuthPath(path) && tokenTypeForPath(path, fallbackTokenType) === "user" && !config.skipAuthRefresh) {
      const session = currentUserAuthState();
      if (config._userAuthSessionVersion === undefined) config._userAuthSessionVersion = session.version;
      if (config._userAuthSessionVersion !== session.version) throw supersededAuthError();
      config._userAuthRequestToken = requestUserToken(config) || session.token;
    }
    return config;
  });
  instance.interceptors.response.use(
    (response) => response,
    async (error) => {
      const tokenType = shouldHandleAuth401(error, fallbackTokenType);
      const config = error.config || {};
      if (tokenType === "user" && !config.skipAuthRefresh) {
        const session = currentUserAuthState();
        const version = config._userAuthSessionVersion;
        const issuedToken = requestUserToken(config);
        if (version !== session.version || (issuedToken && !session.tokens.has(issuedToken))) throw supersededAuthError();
        if (!config._retryAuthRefresh) {
          config._retryAuthRefresh = true;
          // Another request may already have refreshed this same session.
          const refreshed = issuedToken && issuedToken !== session.token
            ? session.token
            : await refreshUserAccessToken(version);
          if (!isUserAuthSessionCurrent(version)) throw supersededAuthError();
          if (refreshed) {
            config.headers = { ...(config.headers || {}), Authorization: `Bearer ${refreshed}` };
            return instance(config);
          }
        } else if (issuedToken !== session.token) {
          // A rejected old retry must not invalidate a subsequently rotated grant.
          throw supersededAuthError();
        }
      }
      if (tokenType && !config.skipAuthRedirect) {
        const detail = error.response?.data?.detail;
        const message = typeof detail === "string" && detail.includes("new login detected")
          ? NEW_LOGIN_MESSAGE
          : SESSION_EXPIRED_MESSAGE;
        handleSessionExpired(tokenType, message);
      }
      return Promise.reject(error);
    },
  );
}

// Admin axios — sends only the admin Bearer token (used by /admin/*).
export const api = axios.create({ baseURL: API, withCredentials: true });
api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

// Reader-user axios — sends only the user Bearer token (used by /users/*, /reader/*).
export const userApi = axios.create({ baseURL: API, withCredentials: true });
userApi.interceptors.request.use((cfg) => {
  // Axios request interceptors run in reverse registration order. Recheck the
  // captured identity before adding a credential after an asynchronous turn.
  if (cfg._userAuthSessionVersion !== undefined && !isUserAuthSessionCurrent(cfg._userAuthSessionVersion)) throw supersededAuthError();
  const token = localStorage.getItem(USER_TOKEN_KEY);
  if (token && !cfg.headers.Authorization) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

installAuth401Handler(api);
installAuth401Handler(userApi, "user");
installAuth401Handler(axios);
installDevApiTiming(api);
installDevApiTiming(userApi);
installDevApiTiming(axios);

export function formatError(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((e) => (e?.msg ? e.msg : JSON.stringify(e))).join(" ");
  if (detail?.msg) return detail.msg;
  return String(detail);
}

export function formatMinutes(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}h ${String(m).padStart(2, "0")}m`;
  if (m > 0) return `${m}m ${String(sec).padStart(2, "0")}s`;
  return `${sec}s`;
}
