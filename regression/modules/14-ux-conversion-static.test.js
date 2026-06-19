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
  const bookCard = read("frontend/src/components/BookCard.jsx");
  const controlledLaunch = read("frontend/src/lib/controlledLaunch.js");
  const pricing = read("frontend/src/pages/Pricing.jsx");
  const backend = read("backend/server.py");
  const analytics = read("frontend/src/lib/funnelAnalytics.js");
  const microStory = read("frontend/src/pages/MicroStoryLanding.jsx");
  const readerUpsell = read("frontend/src/components/Funnel/ReaderUpsellPrompt.jsx");
  const reader = read("frontend/src/pages/Reader.jsx");
  const launchAudit = read("scripts/launch_readiness_audit.py");
  const header = read("frontend/src/components/Header.jsx");
  const app = read("frontend/src/App.js");
  const renderedPricingSources = [backend, pricing, microStory, readerUpsell, reader].join("\n");

  test("homepage exposes Dracula-first reading and reading-time CTAs", () => {
    expect(home).toContain('data-testid="hero-cta-read"');
    expect(home).toContain('data-testid="hero-cta-pricing"');
    expect(home).toContain("Begin with");
    expect(home).toContain("Dracula");
    expect(home).toContain("Read Chapter 1 Free");
    expect(home).toContain("Get 7-Day Reading Pass");
    expect(home).not.toMatch(/\b105 reading rooms open\b/i);
    expect(home).not.toContain("reading rooms open");
  });

  test("library and book pages expose only approved Dracula reading paths", () => {
    expect(library).toContain("Live Controlled Release");
    expect(library).toContain("Coming Through the Rights-Safe Pipeline");
    expect(library).toContain("Read Chapter 1 Free");
    expect(library).toContain("Start Reading");
    expect(library).toContain("Notify Me");
    expect(bookDetail).toContain('data-testid="read-preview"');
    expect(bookDetail).toContain('data-testid="bottom-buy-reading-time"');
    expect(bookDetail).toContain("DRACULA_SOURCE_NOTE");
    expect(bookDetail).toContain("Audio:</strong> Not available yet");
    expect(bookDetail).toContain("readingPassUrl(\"book_detail\")");
  });

  test("book card truth gate prevents unapproved reader CTAs", () => {
    expect(bookCard).toContain("bookLaunchStatus");
    expect(bookCard).toContain('status === "LIVE_APPROVED"');
    expect(controlledLaunch).toContain("COMING_SOON_PIPELINE");
    expect(bookCard).toContain("Notify Me");
    expect(bookCard).toContain("This title is in the rights-safe pipeline and is not readable yet.");
    expect(bookCard).toContain("isLiveApproved ? `/book/${book.slug}` : notifyUrl(book.slug)");
  });

  test("pricing page has checkout CTA, payment trust copy, and support/refund copy", () => {
    expect(pricing).toContain("Buy reading time");
    expect(pricing).toContain("Secure payment by Razorpay");
    expect(pricing).toContain("No subscription or autorenewal");
    expect(pricing).toContain("Reading time is credited to your wallet after confirmation");
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
    expect(backend).toContain('reason="The Reader’s Reserve streak credit"');
  });

  test("pricing pack ids and paise amounts remain unchanged", () => {
    for (const [packId, paise] of [
      ["30m", 4900],
      ["1h", 8900],
      ["3h", 23900],
      ["10h", 49900],
    ]) {
      const packBlock = new RegExp(`"id": "${packId}",[\\s\\S]*?"amount_paise": ${paise},`);
      expect(backend).toMatch(packBlock);
    }
  });

  test("old visible pack labels and awkward first-chapter grammar are absent", () => {
    for (const oldLabel of [
      "Afternoon Pause",
      "An Evening In",
      "Long Weekend",
      "The Reader's Reserve",
    ]) {
      expect(renderedPricingSources).not.toContain(oldLabel);
    }
    expect(renderedPricingSources).not.toContain("₹49 The First Chapter");
    expect(renderedPricingSources).not.toContain("unlock the ₹49");
    expect(microStory).toContain("continue with The First Chapter — ₹49");
    expect(microStory).toContain("unlock <em>The First Chapter</em> for ₹49");
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

  test("pricing page tracks premium pricing funnel events with render semantics", () => {
    for (const event of [
      "pricing_pack_rendered",
      "pricing_pack_cta_click",
      "reading_time_explainer_rendered",
      "dracula_continue_from_pricing_click",
    ]) {
      expect(pricing).toContain(event);
      expect(analytics).toContain(event);
      expect(launchAudit).toContain(event);
    }
    expect(pricing).not.toContain("pricing_pack_view");
    expect(pricing).not.toContain("reading_time_explainer_view");
    expect(analytics).not.toContain("pricing_pack_view");
    expect(analytics).not.toContain("reading_time_explainer_view");
  });

  test("mobile navigation keeps a visible library CTA", () => {
    expect(header).toContain('data-testid="mobile-cta-library"');
    expect(header).toContain("Start Dracula");
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
