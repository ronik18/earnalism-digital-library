import http from "k6/http";
import { check, group, sleep } from "k6";

const FRONTEND_URL = __ENV.FRONTEND_URL || "https://theearnalism.com";
const API_URL = __ENV.API_URL || "https://api.theearnalism.com";
const BASELINE_VUS = Number(__ENV.K6_BASELINE_VUS || 100);
const SPIKE_MULTIPLIER = Number(__ENV.K6_SPIKE_MULTIPLIER || 10);
const SPIKE_VUS = Number(__ENV.K6_SPIKE_VUS || BASELINE_VUS * SPIKE_MULTIPLIER);

export const options = {
  thresholds: {
    http_req_failed: [__ENV.K6_FAILED_THRESHOLD || "rate<0.02"],
    http_req_duration: [__ENV.K6_HTTP_P95_THRESHOLD || "p(95)<2500"],
    "http_req_duration{surface:catalog}": [__ENV.K6_CATALOG_P95_THRESHOLD || "p(95)<1500"],
    "http_req_duration{surface:reader}": [__ENV.K6_READER_P95_THRESHOLD || "p(95)<2200"],
  },
  scenarios: {
    ten_x_spike: {
      executor: "constant-vus",
      vus: SPIKE_VUS,
      duration: __ENV.K6_LOAD_DURATION || "60s",
      gracefulStop: "15s",
    },
  },
};

function jsonGet(url, tags = {}) {
  return http.get(url, {
    tags,
    headers: { Accept: "application/json" },
  });
}

export default function () {
  group("public surfaces", () => {
    const frontend = http.get(FRONTEND_URL, { tags: { surface: "frontend" } });
    check(frontend, {
      "frontend 200": (res) => res.status === 200,
    });

    const healthz = jsonGet(`${API_URL}/healthz`, { surface: "health" });
    check(healthz, {
      "healthz ok": (res) => res.status === 200 && res.json("status") === "ok",
    });

    const home = jsonGet(`${API_URL}/api/home`, { surface: "catalog" });
    check(home, {
      "home payload ok": (res) => res.status === 200,
      "home has books": (res) => (res.json("books") || []).length > 0,
    });

    const books = jsonGet(`${API_URL}/api/books`, { surface: "catalog" });
    check(books, {
      "books ok": (res) => res.status === 200,
    });

    const first = (books.json() || [])[0];
    if (first?.slug) {
      const chapters = jsonGet(`${API_URL}/api/books/${first.slug}/chapters`, { surface: "reader" });
      check(chapters, {
        "chapters ok": (res) => res.status === 200,
      });
    }

    const packs = jsonGet(`${API_URL}/api/payments/packs`, { surface: "payment" });
    check(packs, {
      "payment packs ok": (res) => res.status === 200 && (res.json() || []).length > 0,
    });
  });

  sleep(Number(__ENV.K6_LOAD_SLEEP_SECONDS || 1));
}
