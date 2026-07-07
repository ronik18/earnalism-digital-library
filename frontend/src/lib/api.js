import axios from "axios";
import { toast } from "sonner";

function resolveBackendUrl() {
  const configured = (
    process.env.REACT_APP_BACKEND_URL ||
    process.env.REACT_APP_API_URL ||
    ""
  ).trim();

  if (process.env.NODE_ENV !== "production") return configured;
  if (configured === "/api" || configured === "/api/") return "";
  if (configured.startsWith("/")) return configured.replace(/\/api\/?$/, "");
  if (!configured || configured.includes("<") || configured.includes("yourdomain.com")) {
    return "";
  }
  try {
    const url = new URL(configured);
    if (["localhost", "127.0.0.1", "0.0.0.0"].includes(url.hostname)) {
      return "";
    }
  } catch {
    return "";
  }
  return configured;
}

export const BACKEND_URL = resolveBackendUrl();
export const API = BACKEND_URL ? `${BACKEND_URL.replace(/\/$/, "")}/api` : "/api";

export const TOKEN_KEY = "earnalism_admin_token";
export const USER_TOKEN_KEY = "earnalism_user_token";
export const SESSION_EXPIRED_MESSAGE = "Session expired, please login again.";
export const NEW_LOGIN_MESSAGE = "You’ve been logged out: new login detected.";

let authRedirectInFlight = false;
const DEV_API_TIMING = process.env.NODE_ENV === "development";
axios.defaults.withCredentials = true;

function isBrowser() {
  return typeof window !== "undefined" && typeof window.location !== "undefined";
}

function requestPath(config = {}) {
  const rawUrl = config.url || "";
  if (!isBrowser()) return rawUrl;

  try {
    if (/^https?:\/\//i.test(rawUrl)) return new URL(rawUrl).pathname;
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

async function refreshUserAccessToken() {
  if (!isBrowser() || !localStorage.getItem(USER_TOKEN_KEY)) return null;
  try {
    const response = await fetch(`${API}/users/refresh`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    });
    if (!response.ok) return null;
    const data = await response.json();
    if (!data?.token) return null;
    localStorage.setItem(USER_TOKEN_KEY, data.token);
    return data.token;
  } catch {
    return null;
  }
}

function shouldHandleAuth401(error, fallbackTokenType) {
  const status = error?.response?.status;
  const config = error?.config || {};
  if (status !== 401 || config.skipAuthRedirect) return null;

  const path = requestPath(config);
  if (isPublicAuthPath(path)) return null;
  return tokenTypeForPath(path, fallbackTokenType);
}

function installAuth401Handler(instance, fallbackTokenType) {
  instance.interceptors.response.use(
    (response) => response,
    async (error) => {
      const tokenType = shouldHandleAuth401(error, fallbackTokenType);
      const config = error.config || {};
      if (tokenType === "user" && !config._retryAuthRefresh) {
        config._retryAuthRefresh = true;
        const refreshed = await refreshUserAccessToken();
        if (refreshed) {
          config.headers = { ...(config.headers || {}), Authorization: `Bearer ${refreshed}` };
          return instance(config);
        }
      }
      if (tokenType) {
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
  const token = localStorage.getItem(USER_TOKEN_KEY);
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
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
