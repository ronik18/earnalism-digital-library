import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const FRONTEND_URL = normalizeBaseUrl(
  process.env.FRONTEND_URL || process.env.PRODUCTION_FRONTEND_URL || "https://theearnalism.com",
);
const API_URL = normalizeBaseUrl(
  process.env.API_URL || process.env.PRODUCTION_API_URL || "https://api.theearnalism.com",
);

const REQUEST_TIMEOUT_MS = readNumber("MONITOR_REQUEST_TIMEOUT_MS", 12_000);
const MAX_FRONTEND_MS = readNumber("MONITOR_MAX_FRONTEND_MS", 4_500);
const MAX_API_MS = readNumber("MONITOR_MAX_API_MS", 3_000);
const MIN_BOOKS = readNumber("MONITOR_MIN_BOOKS", 1);
const FAIL_ON_SLOW = readBoolean("MONITOR_FAIL_ON_SLOW", false);
const OUTPUT_PATH =
  process.env.MONITOR_OUTPUT_PATH ||
  path.join("output", "monitoring", "production-monitor-latest.json");

const checks = [];

async function main() {
  await runCheck({
    name: "frontend:home",
    url: FRONTEND_URL,
    maxMs: MAX_FRONTEND_MS,
    required: true,
    validate: ({ text }) => {
      if (!text || !/Earnalism|The Earnalism/i.test(text)) {
        throw new Error("home HTML did not include the Earnalism brand marker");
      }
      return { bytes: text.length };
    },
  });

  await runCheck({
    name: "frontend:asset-manifest",
    url: `${FRONTEND_URL}/asset-manifest.json`,
    maxMs: MAX_FRONTEND_MS,
    required: true,
    json: true,
    validate: ({ json }) => {
      if (!json || typeof json !== "object") {
        throw new Error("asset manifest was not valid JSON");
      }
      return { entrypoints: Array.isArray(json.entrypoints) ? json.entrypoints.length : 0 };
    },
  });

  await runCheck({
    name: "frontend:sitemap",
    url: `${FRONTEND_URL}/sitemap.xml`,
    maxMs: MAX_FRONTEND_MS,
    required: true,
    validate: ({ text }) => {
      if (!text.includes("<urlset")) {
        throw new Error("sitemap did not include a urlset");
      }
      return { bytes: text.length };
    },
  });

  await runCheck({
    name: "api:healthz",
    url: `${API_URL}/healthz`,
    maxMs: MAX_API_MS,
    required: true,
  });

  await runCheck({
    name: "api:health",
    url: `${API_URL}/api/health`,
    maxMs: MAX_API_MS,
    required: true,
    json: true,
  });

  await runCheck({
    name: "api:home",
    url: `${API_URL}/api/home`,
    maxMs: MAX_API_MS,
    required: true,
    json: true,
  });

  const booksCheck = await runCheck({
    name: "api:books",
    url: `${API_URL}/api/books`,
    maxMs: MAX_API_MS,
    required: true,
    json: true,
    validate: ({ json }) => {
      const books = extractBooks(json);
      if (books.length < MIN_BOOKS) {
        throw new Error(`expected at least ${MIN_BOOKS} published book(s), received ${books.length}`);
      }
      const firstBook = books.find((book) => book?.slug) || books[0];
      return { count: books.length, firstSlug: firstBook?.slug || null };
    },
  });

  await runCheck({
    name: "api:settings-public",
    url: `${API_URL}/api/settings/public`,
    maxMs: MAX_API_MS,
    required: true,
    json: true,
  });

  if (booksCheck.ok && booksCheck.detail?.firstSlug) {
    await runCheck({
      name: "api:reader-manifest",
      url: `${API_URL}/api/reader/book/${encodeURIComponent(booksCheck.detail.firstSlug)}/manifest`,
      maxMs: MAX_API_MS,
      required: true,
      json: true,
      validate: ({ json }) => {
        if (!json || typeof json !== "object") {
          throw new Error("reader manifest was not an object");
        }
        return {
          slug: json.slug || json.book?.slug || booksCheck.detail.firstSlug,
          hasAudiobook: Boolean(json.audiobook || json.book?.audiobook),
        };
      },
    });
  }

  const failures = checks.filter((check) => check.required && !check.ok);
  const slowChecks = checks.filter((check) => check.ok && check.slow);
  const passed = failures.length === 0 && (!FAIL_ON_SLOW || slowChecks.length === 0);

  const report = {
    ok: passed,
    generatedAt: new Date().toISOString(),
    frontendUrl: FRONTEND_URL,
    apiUrl: API_URL,
    budgets: {
      maxFrontendMs: MAX_FRONTEND_MS,
      maxApiMs: MAX_API_MS,
      failOnSlow: FAIL_ON_SLOW,
      requestTimeoutMs: REQUEST_TIMEOUT_MS,
    },
    summary: {
      checks: checks.length,
      failures: failures.length,
      slow: slowChecks.length,
    },
    checks,
  };

  await mkdir(path.dirname(OUTPUT_PATH), { recursive: true });
  await writeFile(OUTPUT_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");

  const status = passed ? "PASS" : "FAIL";
  console.log(
    `${status}: ${checks.length} production checks, ${failures.length} failure(s), ${slowChecks.length} slow warning(s).`,
  );
  console.log(`Report: ${OUTPUT_PATH}`);

  if (!passed) {
    for (const failure of failures) {
      console.error(`FAIL ${failure.name}: ${failure.error || `status ${failure.status}`}`);
    }
    if (FAIL_ON_SLOW) {
      for (const slow of slowChecks) {
        console.error(`SLOW ${slow.name}: ${slow.durationMs}ms over ${slow.maxMs}ms`);
      }
    }
    process.exitCode = 1;
  }
}

async function runCheck({ name, url, maxMs, required, json = false, validate }) {
  const started = performance.now();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  const result = {
    name,
    url,
    required,
    maxMs,
    ok: false,
    slow: false,
    status: null,
    durationMs: null,
    detail: null,
    error: null,
  };

  try {
    const response = await fetch(url, {
      redirect: "follow",
      signal: controller.signal,
      headers: {
        Accept: json ? "application/json,text/plain;q=0.9,*/*;q=0.8" : "text/html,application/xml;q=0.9,*/*;q=0.8",
        "User-Agent": "earnalism-production-monitor/1.0",
      },
    });

    result.status = response.status;
    const text = await response.text();
    let parsedJson = null;
    if (json && text) {
      try {
        parsedJson = JSON.parse(text);
      } catch (error) {
        throw new Error(`invalid JSON: ${error.message}`);
      }
    }

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    result.detail = validate ? validate({ response, text, json: parsedJson }) : { bytes: text.length };
    result.ok = true;
  } catch (error) {
    result.error = error.name === "AbortError" ? `timed out after ${REQUEST_TIMEOUT_MS}ms` : error.message;
  } finally {
    clearTimeout(timeout);
    result.durationMs = Math.round(performance.now() - started);
    result.slow = result.ok && Number.isFinite(maxMs) && result.durationMs > maxMs;
    checks.push(result);
  }

  return result;
}

function extractBooks(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.books)) return payload.books;
  if (Array.isArray(payload?.items)) return payload.items;
  if (Array.isArray(payload?.data)) return payload.data;
  return [];
}

function normalizeBaseUrl(value) {
  return String(value || "").replace(/\/+$/, "");
}

function readNumber(name, fallback) {
  const raw = process.env[name];
  if (!raw) return fallback;
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function readBoolean(name, fallback) {
  const raw = process.env[name];
  if (raw == null || raw === "") return fallback;
  return ["1", "true", "yes", "on"].includes(String(raw).toLowerCase());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
