const { expect, test } = require("playwright/test");

function localUatBaseUrl() {
  const value = String(process.env.UAT_BASE_URL || "").trim().replace(/\/$/, "");
  if (!value) throw new Error("UAT_BASE_URL is required; production fallback is disabled.");
  const parsed = new URL(value);
  if (parsed.protocol !== "http:" || parsed.hostname !== "127.0.0.1") {
    throw new Error("Analytics funnel browser coverage is restricted to isolated loopback UAT.");
  }
  return value;
}

const BASE_URL = localUatBaseUrl();
const book = {
  slug: "a-ghost-story",
  title: "A Ghost Story",
  author: "M. R. James",
  language: "English",
  publication_status: "LIVE_APPROVED",
  reader_enabled: true,
  public_route: "/book/a-ghost-story",
  reader_url: "/reader/a-ghost-story",
  cover_image_url: "/assets/books/a-ghost-story/front-cover.jpg",
  cover_valid: true,
  preview_enabled: true,
  preview_url: "/reader/a-ghost-story",
  chapters: [{ id: "chapter-1", title: "The Mezzotint", is_preview: true }],
};

test("safe journey emits route and validated preview events without non-analytics writes", async ({ page }) => {
  const events = [];
  const unexpectedWrites = [];
  await page.addInitScript(() => {
    window.__EARNALISM_ENABLE_FUNNEL_ANALYTICS__ = true;
    Object.defineProperty(navigator, "sendBeacon", { configurable: true, value: () => false });
  });

  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.hostname !== "127.0.0.1" || !url.pathname.startsWith("/api/")) return route.continue();

    if (url.pathname === "/api/analytics/event" && request.method() === "POST") {
      const payload = request.postDataJSON();
      events.push(payload);
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true }) });
    }
    if (request.method() !== "GET") {
      unexpectedWrites.push(`${request.method()} ${url.pathname}`);
      return route.fulfill({ status: 599, contentType: "application/json", body: JSON.stringify({ detail: "Unexpected write blocked by analytics E2E guard" }) });
    }

    let body = {};
    if (url.pathname === "/api/books") body = [book];
    else if (url.pathname === "/api/books/a-ghost-story") body = book;
    else if (url.pathname === "/api/home/curation") body = {};
    else if (url.pathname === "/api/payments/offers") body = { packs: [], config: { configured: false } };
    else if (url.pathname === "/api/payments/config") body = { configured: false };
    else if (url.pathname === "/api/payments/packs") body = [];
    else if (url.pathname === "/api/reader/book/a-ghost-story/manifest") {
      body = {
        book: { slug: book.slug, title: book.title, author: book.author, language: "English" },
        access: { reading_pass: { enabled: true, free_entitlement: true, segments_ready: true, total_pages: 3 } },
        canonical_pages: { page_count: 3, manifest_version: "fixture-v1", pages: [1, 2, 3].map((page_number) => ({ page_number, chapter_id: "chapter-1" })) },
        chapters: [{ id: "chapter-1", title: "The Mezzotint" }],
        audio: { enabled: false, assets: {} },
      };
    } else if (url.pathname === "/api/reading-pass/books/a-ghost-story/pages/1") {
      body = {
        book_slug: book.slug,
        page_index: 1,
        chapter_id: "chapter-1",
        chapter_title: "The Mezzotint",
        total_pages: 3,
        segmentation_version: "fixture-segments-v1",
        manifest_version: "fixture-v1",
        is_preview: true,
        content: "<p>A quiet test passage for the anonymous preview.</p>",
      };
    } else if (url.pathname === "/api/auth/me" || url.pathname === "/api/users/me") {
      return route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Sign in required" }) });
    }
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  await page.goto(`${BASE_URL}/`, { waitUntil: "networkidle" });
  await page.getByRole("link", { name: /explore the library/i }).first().click();
  await expect(page).toHaveURL(/\/library$/);
  await page.locator('a[href="/book/a-ghost-story"]').first().click();
  await expect(page).toHaveURL(/\/book\/a-ghost-story$/);
  await expect(page.getByRole("heading", { name: "A Ghost Story" })).toBeVisible();
  await page.locator('[data-testid="start-reading"]').click();
  await expect(page).toHaveURL(/\/reader\/a-ghost-story$/);
  await expect(page.locator("body")).toContainText("A quiet test passage for the anonymous preview.");
  await page.goto(`${BASE_URL}/pricing`, { waitUntil: "networkidle" });

  await expect.poll(() => events.map((item) => item.event)).toEqual(expect.arrayContaining([
    "page_view", "homepage_view", "library_view", "title_view", "reader_preview_started", "pricing_view",
  ]));
  for (const event of ["homepage_view", "library_view", "title_view", "reader_preview_started", "pricing_view"]) {
    expect(events.filter((item) => item.event === event), `${event} is emitted once for this navigation`).toHaveLength(1);
  }
  expect(events.some((item) => item.event === "purchase_completed")).toBe(false);
  expect(unexpectedWrites).toEqual([]);
  for (const item of events) {
    expect(item.route).not.toContain("?");
    expect(item.deployment_environment).toBe("local");
    expect(JSON.stringify(item)).not.toMatch(/email|password|token|razorpay|payment_id/i);
  }
});
