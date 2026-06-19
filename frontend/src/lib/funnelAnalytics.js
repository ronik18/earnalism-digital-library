import { API } from "./api";

export const LAUNCH_ANALYTICS_EVENTS = [
  "page_view",
  "book_view",
  "preview_start",
  "reading_started",
  "reading_session_completed",
  "pricing_view",
  "pricing_pack_view",
  "pricing_pack_cta_click",
  "reading_time_explainer_view",
  "dracula_continue_from_pricing_click",
  "checkout_start",
  "payment_success",
  "payment_failed",
  "newsletter_joined",
  "referral_invited",
  "referral_converted",
  "institution_interest",
  "audio_preview_played",
  "cta_clicked",
];

export const BLOCKED_ANALYTICS_METADATA_FIELDS = new Set([
  "email",
  "phone",
  "name",
  "address",
  "razorpay_signature",
  "card",
  "token",
  "password",
  "secret",
]);

let analyticsSink = null;

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

export function sanitizeAnalyticsMetadata(metadata = {}) {
  return Object.entries(metadata || {}).reduce((safe, [key, value]) => {
    if (BLOCKED_ANALYTICS_METADATA_FIELDS.has(String(key).toLowerCase())) return safe;
    if (value == null || ["string", "number", "boolean"].includes(typeof value)) {
      safe[key] = value;
    }
    return safe;
  }, {});
}

export function emitLaunchAnalyticsEvent(event, metadata = {}, { network = true } = {}) {
  if (!event || !LAUNCH_ANALYTICS_EVENTS.includes(event)) return false;
  const safeMetadata = sanitizeAnalyticsMetadata(metadata);
  if (analyticsSink) {
    analyticsSink(event, safeMetadata);
    return true;
  }
  if (typeof window !== "undefined" && typeof window.__EARNALISM_ANALYTICS_SINK__ === "function") {
    window.__EARNALISM_ANALYTICS_SINK__(event, safeMetadata);
    return true;
  }
  if (!network) return true;
  return sendAnalyticsEvent(event, safeMetadata);
}

export function trackFunnelEvent(event, metadata = {}) {
  return emitLaunchAnalyticsEvent(event, metadata, { network: true });
}

function sendAnalyticsEvent(event, metadata = {}) {
  if (typeof window === "undefined" || !event) return;

  const payload = JSON.stringify({
    event,
    metadata: {
      ...metadata,
      path: window.location.pathname,
      search: window.location.search,
    },
  });
  const url = `${API}/analytics/events`;

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
