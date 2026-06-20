const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "../..");

function read(relativePath) {
  return fs.readFileSync(path.join(ROOT, relativePath), "utf8");
}

function extractBetween(source, startMarker, endMarker) {
  const start = source.indexOf(startMarker);
  expect(start).toBeGreaterThanOrEqual(0);
  const afterStart = source.slice(start + startMarker.length);
  const end = afterStart.indexOf(endMarker);
  expect(end).toBeGreaterThanOrEqual(0);
  return afterStart.slice(0, end);
}

describe("UX conversion static signals", () => {
  const home = read("frontend/src/pages/Home.jsx");
  const bookDetail = read("frontend/src/pages/BookDetail.jsx");
  const library = read("frontend/src/pages/Library.jsx");
  const bookCard = read("frontend/src/components/BookCard.jsx");
  const controlledLaunch = read("frontend/src/lib/controlledLaunch.js");
  const publicationSafety = read("frontend/src/lib/publicationSafety.js");
  const pricing = read("frontend/src/pages/Pricing.jsx");
  const backend = read("backend/server.py");
  const analytics = read("frontend/src/lib/funnelAnalytics.js");
  const microStory = read("frontend/src/pages/MicroStoryLanding.jsx");
  const readerUpsell = read("frontend/src/components/Funnel/ReaderUpsellPrompt.jsx");
  const reader = read("frontend/src/pages/Reader.jsx");
  const launchAudit = read("scripts/launch_readiness_audit.py");
  const packageJson = read("package.json");
  const dailyRunbook = read("DAILY_GROWTH_AUDIT_RUNBOOK.md");
  const header = read("frontend/src/components/Header.jsx");
  const app = read("frontend/src/App.js");
  const renderedPricingSources = [backend, pricing, microStory, readerUpsell, reader].join("\n");

  test("homepage exposes Dracula-first reading and reading-time CTAs", () => {
    expect(home).toContain('data-testid="hero-cta-read"');
    expect(home).toContain('data-testid="hero-cta-pricing"');
    expect(home).toContain("The Earnalism Digital Library");
    expect(home).toContain('aria-label="Begin with Dracula."');
    expect(home).toContain("Begin with");
    expect(home).toContain("Dracula.");
    expect(home).toContain("The Earnalism controlled launch starts with one approved classic.");
    expect(home).toContain("Read Chapter 1 free. Continue with a 7-day reading pass.");
    expect(home).toContain("More books are coming through the rights-safe pipeline.");
    expect(home).toContain("Read Chapter 1 Free");
    expect(home).toContain("Start Dracula");
    expect(home).toContain("Get 7-Day Reading Pass");
    expect(home).toContain("Explore Pipeline / Library");
    expect(home).not.toContain("A quieter bookstore for readers who linger");
    expect(home).not.toContain("Preview every book before you pay");
    expect(home).not.toContain("Discover thoughtful books across");
    expect(home).not.toMatch(/\b105 reading rooms open\b/i);
    expect(home).not.toContain("reading rooms open");
  });

  test("library and book pages expose only approved Dracula reading paths", () => {
    expect(library).toContain("Live Controlled Release");
    expect(library).toContain("Live Controlled Release:</strong> Dracula only.");
    expect(library).toContain("Coming Through the Rights-Safe Pipeline");
    expect(library).toContain("Coming Through the Rights-Safe Pipeline:</strong> future titles only.");
    expect(library).toContain("Dracula is the only live approved core reading release today.");
    expect(library).toContain("These books are not live products yet. They have Notify Me CTAs only.");
    expect(library).toContain("Unapproved titles show Coming Soon / Notify Me only.");
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
    expect(bookCard).toContain("canShowPreview");
    expect(bookCard).toContain("canShowStartReading");
    expect(controlledLaunch).toContain("isLiveApprovedBook");
    expect(controlledLaunch).toContain("isPipelineCandidate");
    expect(controlledLaunch).toContain("canShowAudioCTA");
    expect(controlledLaunch).toContain("COMING_SOON_PIPELINE");
    for (const helper of [
      "isControlledLiveReadingBook",
      "canShowStartReading",
      "canShowPreview",
      "canShowAudioCTA",
      "isPipelineOnlyBook",
    ]) {
      expect(publicationSafety).toContain(`export function ${helper}`);
    }
    expect(publicationSafety).toContain("KSHUDHITA_PASHAN_SLUG");
    expect(publicationSafety).toContain("QA_PASSED");
    expect(bookCard).toContain("Notify Me");
    expect(bookCard).toContain("This title is in the rights-safe pipeline and is not readable yet.");
    expect(bookCard).toContain("isLiveApproved ? `/book/${book.slug}` : notifyUrl(book.slug)");
  });

  test("Bengali Gothic candidate is pipeline-only and not a live reading CTA", () => {
    expect(home).toContain('data-testid="bengali-gothic-pipeline-shelf"');
    expect(home).toContain("KSHUDHITA_PASHAN_PIPELINE.headline");
    expect(home).toContain("KSHUDHITA_PASHAN_PIPELINE.subcopy");
    expect(controlledLaunch).toContain("Bengali Gothic Premiere: ক্ষুধিত পাষাণ");
    expect(controlledLaunch).toContain("After Dracula, enter a haunted Bengali palace.");
    expect(library).toContain('data-testid="library-bengali-gothic-pipeline"');
    expect(library).toContain("KSHUDHITA_PASHAN_PIPELINE.headline");
    expect(library).toContain("KSHUDHITA_PASHAN_PIPELINE.subcopy");

    const homePipelineBlock = extractBetween(
      home,
      'data-testid="bengali-gothic-pipeline-shelf"',
      'data-testid="dracula-shelves"'
    );
    const libraryPipelineBlock = extractBetween(
      library,
      'data-testid="library-bengali-gothic-pipeline"',
      'data-testid="category-filters"'
    );

    for (const block of [homePipelineBlock, libraryPipelineBlock]) {
      expect(block).toContain("Notify Me");
      expect(block).toContain("Reading Circle");
      expect(block).not.toContain("Start Reading");
      expect(block).not.toContain("Read Preview");
      expect(block).not.toContain("Listen Now");
      expect(block).not.toContain("Full Audiobook");
      expect(block).not.toContain("Voice Sample Soon");
      expect(block).not.toContain("Follow Audio QA");
    }
  });

  test("future pipeline books do not show live CTAs", () => {
    const pipelineBlock = extractBetween(
      home,
      'data-testid="pipeline-books"',
      'data-testid="reading-path-draft"'
    );
    expect(pipelineBlock).toContain("Notify Me");
    expect(pipelineBlock).not.toContain("Start Reading");
    expect(pipelineBlock).not.toContain("Read Preview");
    expect(pipelineBlock).not.toContain("Listen Now");
  });

  test("Bengali Gothic analytics events are mock-safe and allowlisted", () => {
    const analytics = read("frontend/src/lib/funnelAnalytics.js");
    const launchAudit = read("scripts/launch_readiness_audit.py");

    [
      "bengali_gothic_pipeline_view",
      "kshudhita_pashan_notify_click",
      "kshudhita_pashan_audio_interest_click",
      "bengali_voice_sample_interest",
      "bengali_gothic_reading_circle_click",
    ].forEach((event) => {
      expect(analytics).toContain(event);
      expect(launchAudit).toContain(event);
    });
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
    expect(readerUpsell).toContain("The Quiet Hour");
    expect(readerUpsell).not.toContain("An Evening In");
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

  test("daily growth audit is a recurring command with snapshot reports", () => {
    expect(packageJson).toContain("owner:daily-growth-audit");
    expect(packageJson).toContain("output/daily/$(date +%F)");
    expect(dailyRunbook).toContain("npm run owner:daily-growth-audit");
    expect(dailyRunbook).toContain("output/daily/YYYY-MM-DD/");
    expect(dailyRunbook).toContain("*_SNAPSHOT.md");
    expect(fs.existsSync(path.join(ROOT, "DAILY_OWNER_GROWTH_REPORT.md"))).toBe(false);
    expect(fs.existsSync(path.join(ROOT, "DAILY_OWNER_GROWTH_REPORT_SNAPSHOT.md"))).toBe(true);
  });
});
