import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: [__ENV.K6_HTTP_P95_THRESHOLD || "p(95)<5000"],
  },
  scenarios: {
    post_deploy_smoke: {
      executor: "shared-iterations",
      vus: Number(__ENV.K6_SMOKE_VUS || 1),
      iterations: Number(__ENV.K6_SMOKE_ITERATIONS || 3),
      maxDuration: "1m",
    },
  },
};

const FRONTEND_URL = __ENV.FRONTEND_URL || "https://theearnalism.com";
const API_URL = __ENV.API_URL || "https://api.theearnalism.com";

export default function () {
  const frontend = http.get(FRONTEND_URL);
  check(frontend, {
    "frontend 200": (res) => res.status === 200,
  });

  const health = http.get(`${API_URL}/health`);
  check(health, {
    "health ok": (res) => res.status === 200 && res.json("ok") === true,
  });

  const categories = http.get(`${API_URL}/api/categories`);
  check(categories, {
    "categories ok": (res) => res.status === 200,
    "categories cache header": (res) => String(res.headers["Cache-Control"] || "").includes("max-age"),
  });

  const books = http.get(`${API_URL}/api/books`);
  check(books, {
    "books ok": (res) => res.status === 200,
  });

  sleep(1);
}
