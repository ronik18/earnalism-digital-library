const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");
const { request } = require("../utils/http");
const { frontendUrl } = require("../utils/envGuard");
const { fetchSitemap } = require("../utils/sitemap");
const removedContent = require("../../frontend/api/removed-content");

const ROOT = path.resolve(__dirname, "../..");
const FIXTURE_DIR = path.join(ROOT, "regression", "fixtures", "catalog-audit");
const AUDIT_SCRIPT = path.join(ROOT, "scripts", "audit-public-content.mjs");
const vercelConfig = JSON.parse(fs.readFileSync(path.join(ROOT, "frontend/vercel.json"), "utf8"));

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

let fixtureOutputDir;
let auditReport;
let auditMarkdown;
let auditCsvHeader;

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

function runAuditWithFixture({ fixtureDir = FIXTURE_DIR, outputDir } = {}) {
  execFileSync(
    "node",
    [
      AUDIT_SCRIPT,
      "--fixture",
      fixtureDir,
      "--output-dir",
      outputDir,
      "--frontend-url",
      "https://fixture.theearnalism.test",
      "--api-url",
      "https://fixture-api.theearnalism.test/api",
      "--timeout-ms",
      "25",
    ],
    {
      cwd: ROOT,
      stdio: "pipe",
    },
  );

  return {
    report: JSON.parse(fs.readFileSync(path.join(outputDir, "catalog_audit_report.json"), "utf8")),
    markdown: fs.readFileSync(path.join(outputDir, "catalog_cleanup_report.md"), "utf8"),
    csvHeader: fs.readFileSync(path.join(outputDir, "catalog_audit_report.csv"), "utf8").split(/\r?\n/, 1)[0],
  };
}

describe("Public content governance", () => {
  beforeAll(() => {
    fixtureOutputDir = fs.mkdtempSync(path.join(os.tmpdir(), "catalog-audit-fixture-"));
    const audit = runAuditWithFixture({ outputDir: fixtureOutputDir });
    auditReport = audit.report;
    auditMarkdown = audit.markdown;
    auditCsvHeader = audit.csvHeader;
  });

  afterAll(() => {
    if (fixtureOutputDir) {
      fs.rmSync(fixtureOutputDir, { recursive: true, force: true });
    }
  });

  test("Vercel routes demo ecommerce paths to removed-content handler", () => {
    const rewrites = vercelConfig.rewrites || [];
    for (const source of ["/product", "/product/:path*", "/shop", "/shop/:path*", "/fashion", "/journal/denim-jackets", "/denim-jackets"]) {
      expect(rewrites.some((rewrite) => rewrite.source === source && rewrite.destination.includes("/api/removed-content"))).toBe(true);
    }
    expect((vercelConfig.redirects || []).some((redirect) => redirect.source === "/shop" && redirect.destination === "/library")).toBe(false);
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

  test("fixture mode works without network and reports source health", () => {
    expect(auditReport.summary.mode).toBe("dry-run");
    expect(auditReport.summary.degraded).toBe(false);
    expect(auditReport.summary.source_statuses).toBeTruthy();
    expect(Array.isArray(auditReport.summary.degraded_reasons)).toBe(true);
    expect(auditReport.summary.source_statuses.sitemap.status).toBe("fixture");
    expect(auditReport.summary.source_statuses.robots.status).toBe("fixture");
    expect(auditReport.summary.source_statuses.books_api.status).toBe("fixture");
    expect(auditReport.summary.source_statuses.audio_public_dir.item_count).toBe(2);
    expect(auditReport.summary.source_statuses.book_assets_dir.item_count).toBe(1);
    expect(auditReport.rows.find((row) => row.path === "/book/fixture-book").cta_present).toBe("assumed_yes");
    expect(auditReport.rows.find((row) => row.path === "/journal/fixture-journal").cta_present).toBe("assumed_no");
  });

  test("catalog audit preserves query routes and detects sitemap-only unknown URLs", () => {
    const categoryRow = auditReport.rows.find((row) => row.path === "/library?category=gothic-fiction");
    const unknownRow = auditReport.rows.find((row) => row.path === "/special/curated-route");
    expect(categoryRow).toBeTruthy();
    expect(categoryRow.sitemap_status).toBe("included");
    expect(unknownRow).toBeTruthy();
    expect(unknownRow.content_type).toBe("unknown_public_url");
    expect(unknownRow.source_sets).toEqual(["sitemap"]);
  });

  test("unknown book and reader rights metadata are quarantined", () => {
    const bookRow = auditReport.rows.find((row) => row.path === "/book/fixture-book");
    const readerRow = auditReport.rows.find((row) => row.path === "/reader/fixture-book");
    expect(bookRow).toBeTruthy();
    expect(bookRow.rights_metadata_present).toBe("unknown");
    expect(bookRow.recommended_action).toBe("QUARANTINE");
    expect(bookRow.reason).toContain("Phase 2 rights verification required");
    expect(readerRow).toBeTruthy();
    expect(readerRow.recommended_action).toBe("QUARANTINE");
  });

  test("unknown audio and book asset rights metadata are quarantined", () => {
    const audioRow = auditReport.rows.find((row) => row.path === "/audio/en/fixture-book-audio.mp3");
    const bookAssetRow = auditReport.rows.find((row) => row.path === "/assets/books/fixture-book/front-cover.jpg");
    expect(audioRow).toBeTruthy();
    expect(audioRow.related_slug).toBe("fixture-book");
    expect(audioRow.recommended_action).toBe("QUARANTINE");
    expect(bookAssetRow).toBeTruthy();
    expect(bookAssetRow.recommended_action).toBe("QUARANTINE");
  });

  test("removed demo routes stay DELETE recommendations in dry-run mode", () => {
    const removedRow = auditReport.rows.find((row) => row.path === "/fashion");
    expect(removedRow).toBeTruthy();
    expect(removedRow.public_status).toBe("removed");
    expect(removedRow.recommended_action).toBe("DELETE");
    expect(auditMarkdown).toContain("Dry-run only: no content was mutated or deleted");
  });

  test("csv output includes path and source fields", () => {
    for (const header of [
      "url",
      "path",
      "source_sets",
      "related_slug",
      "language",
      "asset_health",
      "asset_files",
      "degraded",
      "source_warnings",
    ]) {
      expect(auditCsvHeader).toContain(header);
    }
  });

  test("catalog audit markdown separates every action bucket and keeps dry-run semantics", () => {
    for (const section of ["## KEEP", "## REWRITE", "## NOINDEX", "## QUARANTINE", "## ARCHIVE", "## DELETE"]) {
      expect(auditMarkdown).toContain(section);
    }
    expect(auditReport.rows.every((row) => row.url && row.path && row.title && row.content_type && row.public_status && row.sitemap_status && row.robots_status && row.recommended_action)).toBe(true);
  });

  test("degraded mode is reported when a critical fixture source is missing", () => {
    const degradedFixtureDir = fs.mkdtempSync(path.join(os.tmpdir(), "catalog-audit-degraded-fixture-"));
    const degradedOutputDir = fs.mkdtempSync(path.join(os.tmpdir(), "catalog-audit-degraded-output-"));
    try {
      for (const entry of fs.readdirSync(FIXTURE_DIR)) {
        if (entry === "books.json") continue;
        fs.copyFileSync(path.join(FIXTURE_DIR, entry), path.join(degradedFixtureDir, entry));
      }
      const degradedAudit = runAuditWithFixture({
        fixtureDir: degradedFixtureDir,
        outputDir: degradedOutputDir,
      }).report;
      expect(degradedAudit.summary.degraded).toBe(true);
      expect(Array.isArray(degradedAudit.summary.degraded_reasons)).toBe(true);
      expect(degradedAudit.summary.degraded_reasons.join(" ")).toContain("books_api");
      expect(degradedAudit.summary.source_statuses.books_api.ok).toBe(false);
      expect(degradedAudit.summary.source_statuses.books_api.degraded_reason).toContain("books_api");
    } finally {
      fs.rmSync(degradedFixtureDir, { recursive: true, force: true });
      fs.rmSync(degradedOutputDir, { recursive: true, force: true });
    }
  });
});
