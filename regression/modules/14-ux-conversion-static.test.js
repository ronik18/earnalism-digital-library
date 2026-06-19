const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "../..");

function read(relativePath) {
  return fs.readFileSync(path.join(ROOT, relativePath), "utf8");
}

describe("UX conversion static signals", () => {
  const home = read("frontend/src/pages/Home.jsx");
  const bookDetail = read("frontend/src/pages/BookDetail.jsx");
  const library = read("frontend/src/pages/Library.jsx");
  const pricing = read("frontend/src/pages/Pricing.jsx");
  const backend = read("backend/server.py");
  const analytics = read("frontend/src/lib/funnelAnalytics.js");
  const header = read("frontend/src/components/Header.jsx");
  const app = read("frontend/src/App.js");

  test("homepage exposes primary reading and reading-time CTAs", () => {
    expect(home).toContain('data-testid="hero-cta-read"');
    expect(home).toContain('data-testid="hero-cta-pricing"');
    expect(home).toContain("Start Reading");
    expect(home).toContain("Buy Reading Time");
  });

  test("library and book pages expose preview and reading-time purchase paths", () => {
    expect(library).toContain("Read Preview");
    expect(library).toContain("Start Reading");
    expect(bookDetail).toContain('data-testid="read-preview"');
    expect(bookDetail).toContain('data-testid="bottom-buy-reading-time"');
    expect(bookDetail).toContain("/pricing?pack=1h&source=book_detail");
  });

  test("pricing page has checkout CTA, payment trust copy, and support/refund copy", () => {
    expect(pricing).toContain("Buy reading time");
    expect(pricing).toContain("Secure payment by Razorpay");
    expect(pricing).toContain("No subscription or autorenewal");
    expect(pricing).toContain("Reading time is credited to your wallet after payment confirmation");
    expect(pricing).toMatch(/support or refund questions/i);
    expect(pricing).toContain('data-testid={`pack-${p.id}-buy`}');
  });

  test("pricing packs use Dracula-first premium labels and notes", () => {
    expect(backend).toContain('"label": "The First Chapter"');
    expect(backend).toContain('"label": "The Quiet Hour"');
    expect(backend).toContain('"label": "The Deep Reading Pass"');
    expect(backend).toContain('"label": "The Reader’s Reserve"');
    expect(backend).toContain("Continue after the free preview, one careful sitting at a time.");
    expect(backend).toContain("Best first choice — enough time to settle into Dracula.");
    expect(backend).toContain("A longer weekend return to the castle and the count.");
    expect(backend).toContain("Ten quiet hours kept for Dracula and the classics coming next.");
  });

  test("pricing page highlights recommended and best-value packs", () => {
    expect(pricing).toContain('"1h": "Best first choice"');
    expect(pricing).toContain('"10h": "Best value"');
    expect(pricing).toContain("PACK_BADGES[p.id]");
  });

  test("pricing page frames Dracula continuation and reading-time value", () => {
    expect(pricing).toContain("Choose your reading time.");
    expect(pricing).toContain("Return whenever");
    expect(pricing).toContain("Start with Chapter 1 free");
    expect(pricing).toContain("When you are ready to continue Dracula, add reading time");
    expect(pricing).toContain("Earnalism is a digital reading room");
    expect(pricing).toContain("You buy quiet reading time, not a noisy subscription");
    expect(pricing).toContain('data-testid="dracula-continue-from-pricing"');
  });

  test("pricing page tracks premium pricing funnel events", () => {
    for (const event of [
      "pricing_pack_view",
      "pricing_pack_cta_click",
      "reading_time_explainer_view",
      "dracula_continue_from_pricing_click",
    ]) {
      expect(pricing).toContain(event);
      expect(analytics).toContain(event);
    }
  });

  test("mobile navigation keeps a visible library CTA", () => {
    expect(header).toContain('data-testid="mobile-cta-library"');
    expect(header).toContain("Start Reading");
  });

  test("public route tree does not expose admin controls in the public layout", () => {
    const publicRouteBlock = app.split("{/* Standalone full-screen routes")[0];
    expect(publicRouteBlock).not.toContain('path="/admin"');
    expect(publicRouteBlock).not.toContain("<Admin ");
    expect(publicRouteBlock).toContain('path="/pricing"');
    expect(publicRouteBlock).toContain('path="/library"');
  });

  test("public pages have loading, empty, and error states for reader-facing flows", () => {
    expect(bookDetail).toContain("Loading");
    expect(bookDetail).toContain('data-testid="book-load-error"');
    expect(bookDetail).toContain('data-testid="book-not-found"');
    expect(library).toContain('data-testid="library-empty"');
  });
});
