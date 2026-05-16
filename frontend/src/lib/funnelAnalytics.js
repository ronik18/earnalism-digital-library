import { API } from "./api";

export function trackFunnelEvent(event, metadata = {}) {
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
