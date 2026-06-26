import { API } from "./api";

export const LAUNCH_ANALYTICS_EVENTS = [
  "homepage_view",
  "first_time_site_tour_shown",
  "first_time_site_tour_completed",
  "first_time_site_tour_skipped",
  "hero_read_chapter_free_click",
  "dracula_book_page_view",
  "start_dracula_click",
  "reader_opened",
  "reader_locked_state",
  "reader_low_balance_state",
  "pricing_page_view",
  "reading_pack_selected",
  "checkout_started",
  "payment_success_return",
  "payment_failed_or_cancelled",
  "wallet_credited_visible",
  "continue_reading_click",
  "return_resume_reading_click",
  "core_web_vital",
];

export const LAUNCH_ANALYTICS_EVENT_ALIASES = {
  book_view: "dracula_book_page_view",
  preview_start: "start_dracula_click",
  dracula_preview_start: "start_dracula_click",
  dracula_start_reading_click: "start_dracula_click",
  dracula_reading_pass_click: "pricing_page_view",
  dracula_reader_start: "reader_opened",
  dracula_chapter_1_complete: "continue_reading_click",
  homepage_dracula_cta_click: "hero_read_chapter_free_click",
  dracula_book_view: "dracula_book_page_view",
  pricing_view: "pricing_page_view",
  pricing_pack_cta_click: "reading_pack_selected",
  dracula_continue_from_pricing_click: "continue_reading_click",
  checkout_start: "checkout_started",
  payment_cancelled: "payment_failed_or_cancelled",
  payment_failed: "payment_failed_or_cancelled",
  payment_success: "payment_success_return",
  wallet_credited: "wallet_credited_visible",
  reading_started: "reader_opened",
  reader_completion_recorded: "continue_reading_click",
  chapter_1_completed: "continue_reading_click",
  pricing_test_purchase_complete: "payment_success_return",
};

export const BLOCKED_ANALYTICS_METADATA_FIELDS = new Set([
  "api_key",
  "authorization",
  "bank",
  "billing",
  "billing_data",
  "email",
  "customer",
  "customer_email",
  "customer_id",
  "customer_phone",
  "phone",
  "name",
  "address",
  "invoice",
  "order_id",
  "payment_id",
  "razorpay_order_id",
  "razorpay_payment_id",
  "razorpay_signature",
  "card",
  "upi",
  "webhook_secret",
  "token",
  "password",
  "secret",
]);

export const SAFE_ANALYTICS_METADATA_FIELDS = new Set(["payment_mode"]);

let analyticsSink = null;
const SESSION_STORAGE_KEY = "earnalism:launch-monitor-session:v1";

export function setAnalyticsSink(sink) {
  analyticsSink = typeof sink === "function" ? sink : null;
}

export function createMockAnalyticsSink() {
  const events = [];
  const sink = (event, metadata) => {
    events.push({ event, metadata });
    return true;
  };
  sink.events = events;
  return sink;
}

export function isUnsafeAnalyticsValue(value) {
  if (typeof value !== "string") return false;
  const normalized = value.trim();
  if (!normalized) return false;
  return [
    /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i,
    /\b(?:\+?91[-\s]?)?[6-9]\d{9}\b/,
    /\b(?:rzp|pay|order|cust)_[A-Za-z0-9_-]{8,}\b/i,
    /\bsk[-_][A-Za-z0-9_-]{12,}\b/i,
    /\bBearer\s+[A-Za-z0-9._-]{12,}\b/i,
    /\b(?:card|upi|bank|ifsc|account)\b/i,
  ].some((pattern) => pattern.test(normalized));
}

export function isUnsafeAnalyticsMetadataKey(key) {
  const normalized = String(key || "").toLowerCase();
  if (!normalized) return true;
  if (SAFE_ANALYTICS_METADATA_FIELDS.has(normalized)) return false;
  if (BLOCKED_ANALYTICS_METADATA_FIELDS.has(normalized)) return true;
  return /(email|phone|customer|payment|order|razorpay|signature|token|secret|password|authorization|invoice|billing|card|upi|bank|address|name)/i.test(normalized);
}

export function sanitizeAnalyticsMetadata(metadata = {}) {
  return Object.entries(metadata || {}).reduce((safe, [key, value]) => {
    if (isUnsafeAnalyticsMetadataKey(key)) return safe;
    if (value == null || ["string", "number", "boolean"].includes(typeof value)) {
      if (isUnsafeAnalyticsValue(value)) return safe;
      safe[key] = value;
    }
    return safe;
  }, {});
}

export function normalizeLaunchAnalyticsEvent(event) {
  const normalized = String(event || "").trim();
  const canonical = LAUNCH_ANALYTICS_EVENT_ALIASES[normalized] || normalized;
  return LAUNCH_ANALYTICS_EVENTS.includes(canonical) ? canonical : "";
}

export function getAnonymousLaunchSessionId() {
  if (typeof window === "undefined") return "";
  try {
    const existing = window.localStorage.getItem(SESSION_STORAGE_KEY);
    if (existing && /^[a-z0-9-]{12,80}$/i.test(existing)) return existing;
    const next = typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `anon-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
    window.localStorage.setItem(SESSION_STORAGE_KEY, next);
    return next;
  } catch {
    return "";
  }
}

export function analyticsNetworkEnabled() {
  if (typeof process !== "undefined" && process.env?.REACT_APP_ENABLE_LAUNCH_ANALYTICS === "true") {
    return true;
  }
  if (typeof process !== "undefined" && process.env?.REACT_APP_PERF_METRICS_ENABLED === "true") {
    return true;
  }
  return typeof window !== "undefined" && window.__EARNALISM_ENABLE_FUNNEL_ANALYTICS__ === true;
}

export function analyticsDebugEnabled() {
  if (typeof process !== "undefined" && process.env?.REACT_APP_ENABLE_LAUNCH_ANALYTICS_DEBUG === "true") {
    return true;
  }
  return typeof window !== "undefined" && window.__EARNALISM_DEBUG_FUNNEL_ANALYTICS__ === true;
}

export function emitLaunchAnalyticsEvent(event, metadata = {}, { network = true } = {}) {
  const canonicalEvent = normalizeLaunchAnalyticsEvent(event);
  if (!canonicalEvent) return false;
  const safeMetadata = sanitizeAnalyticsMetadata(metadata);
  if (analyticsSink) {
    analyticsSink(canonicalEvent, safeMetadata);
    return true;
  }
  if (typeof window !== "undefined" && typeof window.__EARNALISM_ANALYTICS_SINK__ === "function") {
    window.__EARNALISM_ANALYTICS_SINK__(canonicalEvent, safeMetadata);
    return true;
  }
  if (!network || !analyticsNetworkEnabled()) {
    if (analyticsDebugEnabled() && typeof console !== "undefined") {
      // eslint-disable-next-line no-console
      console.debug("[Earnalism funnel]", { event: canonicalEvent, metadata: safeMetadata });
    }
    return true;
  }
  return sendAnalyticsEvent(canonicalEvent, safeMetadata);
}

export function trackFunnelEvent(event, metadata = {}) {
  return emitLaunchAnalyticsEvent(event, metadata, { network: true });
}

function sendAnalyticsEvent(event, metadata = {}) {
  if (typeof window === "undefined" || !event) return;
  const route = window.location.pathname;
  const search = window.location.search;
  const bookSlug = metadata.book_slug || metadata.book || "";
  const anonymousSessionId = getAnonymousLaunchSessionId();

  const payload = JSON.stringify({
    event_name: event,
    event,
    route,
    book_slug: bookSlug,
    anonymous_session_id: anonymousSessionId,
    metadata: {
      ...metadata,
      route,
      search,
    },
  });
  const url = `${API}/analytics/event`;

  try {
    if (navigator.sendBeacon) {
      const ok = navigator.sendBeacon(url, new Blob([payload], { type: "application/json" }));
      if (ok) return;
    }
  } catch {
    // Beacon is opportunistic. Fall back to fetch below.
  }

  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: payload,
    keepalive: true,
  }).catch(() => {});
}
