import { trackFunnelEvent } from "./funnelAnalytics";

const ENABLED = process.env.NODE_ENV === "development" || process.env.REACT_APP_PERF_METRICS_ENABLED === "true";

function sendMetric(name, value, extra = {}) {
  if (!ENABLED || typeof window === "undefined" || !Number.isFinite(value)) return;

  const metadata = {
    metric: name,
    value: Math.round(value * 100) / 100,
    path: window.location.pathname,
    rating: rateMetric(name, value),
    ...extra,
  };

  if (process.env.NODE_ENV === "development") {
    // Development-only breadcrumb; no tokens, bodies, or user identifiers.
    // eslint-disable-next-line no-console
    console.debug("[perf]", metadata);
  }

  if (process.env.REACT_APP_PERF_METRICS_ENABLED !== "true") return;
  trackFunnelEvent("core_web_vital", metadata);
}

function rateMetric(name, value) {
  if (name === "CLS") return value <= 0.1 ? "good" : value <= 0.25 ? "needs-improvement" : "poor";
  if (name === "LCP") return value <= 2500 ? "good" : value <= 4000 ? "needs-improvement" : "poor";
  if (name === "FID" || name === "INP") return value <= 200 ? "good" : value <= 500 ? "needs-improvement" : "poor";
  if (name === "FCP" || name === "TTFB") return value <= 1800 ? "good" : value <= 3000 ? "needs-improvement" : "poor";
  return "info";
}

export function initPerformanceMetrics() {
  if (!ENABLED || typeof PerformanceObserver === "undefined") return;

  try {
    const navigation = performance.getEntriesByType("navigation")[0];
    if (navigation) {
      sendMetric("TTFB", navigation.responseStart);
    }
  } catch {
    // Ignore unsupported navigation timing shapes.
  }

  try {
    new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const fcp = entries.find((entry) => entry.name === "first-contentful-paint");
      if (fcp) sendMetric("FCP", fcp.startTime);
    }).observe({ type: "paint", buffered: true });
  } catch {
    // Paint timing not available.
  }

  try {
    new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const last = entries[entries.length - 1];
      if (last) sendMetric("LCP", last.startTime, { element: last.element?.tagName || "" });
    }).observe({ type: "largest-contentful-paint", buffered: true });
  } catch {
    // LCP not available.
  }

  try {
    let cls = 0;
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (!entry.hadRecentInput) cls += entry.value;
      }
      sendMetric("CLS", cls);
    }).observe({ type: "layout-shift", buffered: true });
  } catch {
    // CLS not available.
  }

  try {
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.name === "first-input") sendMetric("FID", entry.processingStart - entry.startTime);
      }
    }).observe({ type: "first-input", buffered: true });
  } catch {
    // FID not available.
  }

  try {
    let maxDuration = 0;
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.interactionId && entry.duration > maxDuration) {
          maxDuration = entry.duration;
          sendMetric("INP", entry.duration);
        }
      }
    }).observe({ type: "event", buffered: true, durationThreshold: 40 });
  } catch {
    // INP event timing not available.
  }
}
