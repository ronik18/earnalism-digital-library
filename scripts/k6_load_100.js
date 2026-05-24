import http from "k6/http";
import { check, group, sleep } from "k6";

const FRONTEND_URL = __ENV.FRONTEND_URL || "https://theearnalism.com";
const API_URL = __ENV.API_URL || "https://api.theearnalism.com";
const P95 = __ENV.K6_HTTP_P95_THRESHOLD || "p(95)<2500";

export const options = {
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: [P95],
    "http_req_duration{surface:catalog}": [__ENV.K6_CATALOG_P95_THRESHOLD || "p(95)<1200"],
    "http_req_duration{surface:reader}": [__ENV.K6_READER_P95_THRESHOLD || "p(95)<1800"],
  },
  scenarios: {
    hundred_concurrent_readers: {
      executor: "constant-vus",
      vus: Number(__ENV.K6_LOAD_VUS || 100),
      duration: __ENV.K6_LOAD_DURATION || "2m",
      gracefulStop: "20s",
    },
  },
};

function jsonGet(url, tags = {}) {
  return http.get(url, {
    tags,
    headers: {
      Accept: "application/json",
    },
  });
}

export default function () {
  group("landing and catalog", () => {
    const home = http.get(FRONTEND_URL, { tags: { surface: "frontend" } });
    check(home, {
      "frontend renders": (res) => res.status === 200 && res.body.includes("Earnalism"),
    });

    const homePayload = jsonGet(`${API_URL}/api/home`, { surface: "catalog" });
    check(homePayload, {
      "home payload ok": (res) => res.status === 200,
      "home payload has books": (res) => (res.json("books") || []).length > 0,
    });

    const books = jsonGet(`${API_URL}/api/books`, { surface: "catalog" });
    check(books, {
      "books ok": (res) => res.status === 200,
      "books metadata only": (res) => !String(res.body || "").includes("\"rights_metadata\""),
    });
  });

  group("reader preview and payment entry", () => {
    const books = jsonGet(`${API_URL}/api/books`, { surface: "reader" });
    const first = (books.json() || [])[0];
    if (!first?.slug) {
      check(books, { "book exists for reader flow": () => false });
      return;
    }

    const detail = jsonGet(`${API_URL}/api/books/${first.slug}`, { surface: "reader" });
    check(detail, {
      "book detail ok": (res) => res.status === 200,
      "book detail strips chapter bodies": (res) => !String(res.body || "").includes("\"rights_metadata\""),
    });

    const chapters = jsonGet(`${API_URL}/api/books/${first.slug}/chapters`, { surface: "reader" });
    const preview = (chapters.json() || [])[0];
    check(chapters, {
      "chapters ok": (res) => res.status === 200,
      "preview chapter exists": () => Boolean(preview?.id),
    });

    if (preview?.id) {
      const chapter = jsonGet(`${API_URL}/api/reader/chapter/${first.slug}/${preview.id}`, { surface: "reader" });
      check(chapter, {
        "preview unlocks": (res) => res.status === 200 && res.json("locked") === false,
        "preview body present": (res) => String(res.json("chapter.content") || "").length > 20,
      });
    }

    const packs = jsonGet(`${API_URL}/api/payments/packs`, { surface: "payment" });
    check(packs, {
      "payment packs ok": (res) => res.status === 200 && (res.json() || []).length >= 4,
    });
  });

  sleep(Number(__ENV.K6_LOAD_SLEEP_SECONDS || 1));
}
