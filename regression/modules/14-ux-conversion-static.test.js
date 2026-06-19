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
  const pricing = read("frontend/src/pages/Pricing.jsx");
  const header = read("frontend/src/components/Header.jsx");
  const app = read("frontend/src/App.js");

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
    expect(bookCard).toContain("canShowPreview");
    expect(bookCard).toContain("canShowStartReading");
    expect(controlledLaunch).toContain("isLiveApprovedBook");
    expect(controlledLaunch).toContain("isPipelineCandidate");
    expect(controlledLaunch).toContain("canShowAudioCTA");
    expect(controlledLaunch).toContain("COMING_SOON_PIPELINE");
    expect(bookCard).toContain("Notify Me");
    expect(bookCard).toContain("This title is in the rights-safe pipeline and is not readable yet.");
    expect(bookCard).toContain("isLiveApproved ? `/book/${book.slug}` : notifyUrl(book.slug)");
  });

  test("Bengali Gothic candidate is pipeline-only and not a live reading CTA", () => {
    expect(home).toContain('data-testid="bengali-gothic-pipeline-shelf"');
    expect(home).toContain("Bengali Gothic Premiere: ক্ষুধিত পাষাণ");
    expect(home).toContain("After Dracula, enter a haunted Bengali palace.");
    expect(library).toContain('data-testid="library-bengali-gothic-pipeline"');
    expect(library).toContain("Bengali Gothic Premiere: ক্ষুধিত পাষাণ");

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
    expect(pricing).toContain("Payments are processed securely by Razorpay");
    expect(pricing).toMatch(/support or refund questions/i);
    expect(pricing).toContain('data-testid={`pack-${p.id}-buy`}');
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
