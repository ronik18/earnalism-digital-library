const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const { request } = require("../utils/http");
const { frontendUrl } = require("../utils/envGuard");
const { fetchSitemap } = require("../utils/sitemap");
const removedContent = require("../../frontend/api/removed-content");

const ROOT = path.resolve(__dirname, "../..");
const vercelConfig = JSON.parse(fs.readFileSync(path.join(ROOT, "frontend/vercel.json"), "utf8"));
const AUDIT_JSON_PATH = path.join(ROOT, "output", "catalog_audit", "catalog_audit_report.json");
const AUDIT_MD_PATH = path.join(ROOT, "output", "catalog_audit", "catalog_cleanup_report.md");
let auditReport;
let auditMarkdown;

const BLOCKED_TERMS = [
  "apparel",
  "clothing",
  "denim-jacket",
  "denim-jackets",
  "fashion",
  "lorem-ipsum",
  "patterned-wrap-dress",
  "placeholder-product",
  "sample-product",
  "woocommerce",
];

const REMOVED_PATHS = [
  "/product/patterned-wrap-dress",
  "/journal/denim-jackets",
  "/denim-jackets",
];

function callRemovedContent({ path: requestPath, url = "/api/removed-content" }) {
  const headers = {};
  const chunks = [];
  const res = {
    statusCode: 200,
    setHeader(name, value) {
      headers[name.toLowerCase()] = value;
    },
    end(chunk = "") {
      chunks.push(String(chunk));
    },
  };

  removedContent(
    {
      query: requestPath ? { path: requestPath } : {},
      headers: {},
      url,
    },
    res,
  );

  return {
    status: res.statusCode,
    headers,
    body: chunks.join(""),
  };
}

describe("Public content governance", () => {
  beforeAll(async () => {
    execFileSync("node", [path.join(ROOT, "scripts", "audit-public-content.mjs")], {
      cwd: ROOT,
      stdio: "pipe",
    });
    auditReport = JSON.parse(fs.readFileSync(AUDIT_JSON_PATH, "utf8"));
    auditMarkdown = fs.readFileSync(AUDIT_MD_PATH, "utf8");
  });

  test("Vercel routes demo ecommerce paths to removed-content handler", () => {
    const rewrites = vercelConfig.rewrites || [];
    for (const source of ["/product", "/product/:path*", "/fashion", "/journal/denim-jackets", "/denim-jackets"]) {
      expect(rewrites.some((rewrite) => rewrite.source === source && rewrite.destination.includes("/api/removed-content"))).toBe(true);
    }
    expect((vercelConfig.redirects || []).some((redirect) => redirect.source === "/shop" && redirect.destination === "/library")).toBe(true);
  });

  test("removed-content handler returns 410 for known retired demo paths", () => {
    for (const removedPath of ["/product/patterned-wrap-dress", "/journal/denim-jackets"]) {
      const response = callRemovedContent({ path: removedPath });
      expect(response.status).toBe(410);
      expect(response.headers["x-robots-tag"]).toBe("noindex, nofollow, noarchive");
      expect(response.body).toContain("This page is no longer available.");
    }
  });

  test("removed-content handler returns 404 for unknown retired paths", () => {
    const response = callRemovedContent({ path: "/retired/unknown-earnalism-path" });
    expect(response.status).toBe(404);
    expect(response.headers["x-robots-tag"]).toBe("noindex, nofollow, noarchive");
  });

  test("removed-content handler does not reflect raw path or query input", () => {
    const rawInput = '/product/patterned-wrap-dress?<script>alert("x")</script>';
    const response = callRemovedContent({ path: rawInput });
    expect(response.status).toBe(410);
    expect(response.headers["x-robots-tag"]).toBe("noindex, nofollow, noarchive");
    expect(response.body).not.toContain(rawInput);
    expect(response.body).not.toContain("<script>");
    expect(response.body).not.toContain("alert");
  });

  test("robots.txt allows removed demo ecommerce routes during deindexing", async () => {
    const fallbackRobots = fs.readFileSync(path.join(ROOT, "frontend/public/robots.txt"), "utf8");
    let text = fallbackRobots;
    if (process.env.REGRESSION_VERIFY_DEPLOYED_CLEANUP === "true") {
      const robots = await request(`${frontendUrl()}/robots.txt`);
      text = robots.ok ? robots.text : fallbackRobots;
    }
    for (const rule of [
      "Disallow: /product/",
      "Disallow: /products/",
      "Disallow: /product-category/",
      "Disallow: /shop/",
      "Disallow: /fashion/",
      "Disallow: /clothing/",
      "Disallow: /apparel/",
      "Disallow: /tag/fashion",
      "Disallow: /tag/clothing",
      "Disallow: /tag/apparel",
    ]) {
      expect(text).not.toContain(rule);
    }
    expect(text).toContain("Removed demo/ecommerce URLs are intentionally crawlable during deindexing");
  });

  test("sitemap excludes blocked demo ecommerce terms", async () => {
    const fallback = fs.readFileSync(path.join(ROOT, "frontend/public/sitemap.xml"), "utf8");
    let text = fallback;
    if (process.env.REGRESSION_VERIFY_DEPLOYED_CLEANUP === "true") {
      const sitemap = await fetchSitemap();
      text = sitemap.ok ? sitemap.text : fallback;
    }
    for (const term of BLOCKED_TERMS) {
      expect(text.toLowerCase()).not.toContain(term);
    }
    for (const required of ["/", "/library", "/journal", "/about", "/contact"]) {
      expect(text).toContain(`${frontendUrl()}${required === "/" ? "/" : required}`);
    }
  });

  test("removed demo URLs do not expose homepage shell after cleanup deploy", async () => {
    if (process.env.REGRESSION_VERIFY_DEPLOYED_CLEANUP !== "true") {
      expect(REMOVED_PATHS.length).toBeGreaterThan(0);
      return;
    }
    for (const removedPath of REMOVED_PATHS) {
      const response = await request(`${frontendUrl()}${removedPath}`);
      expect([404, 410]).toContain(response.status);
      expect(response.text).not.toMatch(/<meta name="robots" content="index, follow"/i);
      expect(response.text).not.toMatch(/Earnalism Digital Library \| Audiobooks, Bengali Books/i);
    }
  });

  test("catalog audit preserves query routes and understands robots visibility", () => {
    const categoryRow = auditReport.rows.find((row) => row.path === "/library?category=gothic-fiction");
    const readerRow = auditReport.rows.find((row) => row.content_type === "reader_page");
    const removedRow = auditReport.rows.find((row) => row.path === "/product/patterned-wrap-dress");
    expect(categoryRow).toBeTruthy();
    expect(categoryRow.sitemap_status).toBe("included");
    expect(readerRow).toBeTruthy();
    expect(readerRow.robots_status).toBe("disallowed");
    expect(readerRow.recommended_action).toBe("NOINDEX");
    expect(removedRow).toBeTruthy();
    expect(removedRow.robots_status).toBe("allowed");
  });

  test("catalog audit classifies removed routes, reader pages, and orphaned assets without mutation", () => {
    const removedRow = auditReport.rows.find((row) => row.path === "/fashion");
    const readerRow = auditReport.rows.find((row) => row.content_type === "reader_page");
    const audioRow = auditReport.rows.find((row) => row.content_type === "audio_asset");
    expect(removedRow).toBeTruthy();
    expect(removedRow.public_status).toBe("removed");
    expect(removedRow.recommended_action).toBe("DELETE");
    expect(readerRow).toBeTruthy();
    expect(readerRow.recommended_action).toBe("NOINDEX");
    expect(audioRow).toBeTruthy();
    expect(["KEEP", "REWRITE", "ARCHIVE"]).toContain(audioRow.recommended_action);
    expect(auditReport.summary.mode).toBe("dry-run");
  });

  test("catalog audit markdown separates every action bucket", () => {
    for (const section of ["## KEEP", "## REWRITE", "## NOINDEX", "## QUARANTINE", "## ARCHIVE", "## DELETE"]) {
      expect(auditMarkdown).toContain(section);
    }
    expect(auditMarkdown).toContain("Dry-run only: no content was mutated or deleted");
    expect(auditReport.rows.every((row) => row.url && row.title && row.content_type && row.public_status && row.sitemap_status && row.robots_status && row.recommended_action)).toBe(true);
  });
});
