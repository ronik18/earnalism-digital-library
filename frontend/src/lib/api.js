import axios from "axios";
import { toast } from "sonner";

export const BACKEND_URL =
  process.env.REACT_APP_BACKEND_URL ||
  process.env.REACT_APP_API_URL ||
  "";
export const API = BACKEND_URL ? `${BACKEND_URL.replace(/\/$/, "")}/api` : "/api";

export const TOKEN_KEY = "earnalism_admin_token";
export const USER_TOKEN_KEY = "earnalism_user_token";
export const SESSION_EXPIRED_MESSAGE = "Session expired, please login again.";

let authRedirectInFlight = false;

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

function isPublicAuthPath(path) {
  return [
    "/api/auth/login",
    "/api/users/login",
    "/api/users/signup",
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

export function handleSessionExpired(tokenType = "user") {
  if (!isBrowser()) return;
  clearToken(tokenType);

  const path = window.location.pathname;
  if (path === "/login" || path === "/admin/login") return;
  if (authRedirectInFlight) return;
  authRedirectInFlight = true;

  toast.error(SESSION_EXPIRED_MESSAGE);
  window.location.assign(loginUrl(tokenType));
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
    (error) => {
      const tokenType = shouldHandleAuth401(error, fallbackTokenType);
      if (tokenType) handleSessionExpired(tokenType);
      return Promise.reject(error);
    },
  );
}

// Admin axios — sends only the admin Bearer token (used by /admin/*).
export const api = axios.create({ baseURL: API });
api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

// Reader-user axios — sends only the user Bearer token (used by /users/*, /reader/*).
export const userApi = axios.create({ baseURL: API });
userApi.interceptors.request.use((cfg) => {
  const token = localStorage.getItem(USER_TOKEN_KEY);
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

installAuth401Handler(api);
installAuth401Handler(userApi, "user");
installAuth401Handler(axios);

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
