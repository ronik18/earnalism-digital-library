const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "../..");

function read(relativePath) {
  return fs.readFileSync(path.join(ROOT, relativePath), "utf8");
}

function readOptional(relativePath) {
  const target = path.join(ROOT, relativePath);
  return fs.existsSync(target) ? fs.readFileSync(target, "utf8") : "";
}

function metaContent(html, attr, value) {
  const tag = html.match(new RegExp(`<meta\\s+[^>]*${attr}=["']${value}["'][^>]*>`, "i"));
  if (!tag) return "";
  const content = tag[0].match(/content=["']([^"']*)["']/i);
  return content ? content[1] : "";
}

function canonicalHref(html) {
  const tag = html.match(/<link\s+[^>]*rel=["']canonical["'][^>]*>/i);
  if (!tag) return "";
  const href = tag[0].match(/href=["']([^"']*)["']/i);
  return href ? href[1] : "";
}

function extractBetween(source, startMarker, endMarker) {
  const start = source.indexOf(startMarker);
  expect(start).toBeGreaterThanOrEqual(0);
  const afterStart = source.slice(start + startMarker.length);
  const end = afterStart.indexOf(endMarker);
  expect(end).toBeGreaterThanOrEqual(0);
  return afterStart.slice(0, end);
}

function loadSocialLinks(env = {}) {
  const source = read("frontend/src/config/socialLinks.js")
    .replace("export const SUPPORTED_SOCIAL_LINKS =", "const SUPPORTED_SOCIAL_LINKS =")
    .replace("export function normalizeSocialUrl", "function normalizeSocialUrl")
    .replace("export function getEnabledSocialLinks", "function getEnabledSocialLinks");
  const context = {
    module: { exports: {} },
    process: { env },
    URL,
  };
  vm.runInNewContext(
    `${source}\nmodule.exports = { SUPPORTED_SOCIAL_LINKS, normalizeSocialUrl, getEnabledSocialLinks };`,
    context
  );
  return context.module.exports;
}

describe("UX conversion static signals", () => {
  const home = read("frontend/src/pages/Home.jsx");
  const bookDetail = read("frontend/src/pages/BookDetail.jsx");
  const library = read("frontend/src/pages/Library.jsx");
  const about = read("frontend/src/pages/About.jsx");
  const journal = read("frontend/src/pages/Journal.jsx");
  const publicIndex = read("frontend/public/index.html");
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
  const frontendPackageJson = read("frontend/package.json");
  const staticSnapshotGenerator = read("frontend/scripts/generate-static-seo-snapshots.mjs");
  const socialPreviewAudit = read("scripts/social_preview_audit.py");
  const postProductionCanary = read("scripts/post_production_canary.py");
  const brandSiteTour = read("scripts/create_premium_site_tour.py");
  const dailyRunbook = read("DAILY_GROWTH_AUDIT_RUNBOOK.md");
  const header = read("frontend/src/components/Header.jsx");
  const footer = read("frontend/src/components/Footer.jsx");
  const footerSocialLinks = read("frontend/src/components/FooterSocialLinks.jsx");
  const socialLinksConfig = read("frontend/src/config/socialLinks.js");
  const styles = read("frontend/src/index.css");
  const app = read("frontend/src/App.js");
  const siteTourVoiceover = read("EARNALISM_SITE_TOUR_VOICEOVER_SCRIPT.md");
  const siteTourFeatureReport = read("SITE_TOUR_FEATURE_HIGHLIGHT_REPORT.md");
  const siteTourScorecard = read("BRAND_SITE_TOUR_VIDEO_SCORECARD.md");
  const renderedPricingSources = [backend, pricing, microStory, readerUpsell, reader].join("\n");
  const productTruthLedger = read("PRODUCT_TRUTH_LEDGER.md");
  const alwaysVisibleLaunchCopy = [
    home,
    library,
    bookDetail,
    pricing,
    microStory,
    readerUpsell,
    header,
    footer,
    controlledLaunch,
    staticSnapshotGenerator,
  ].join("\n");

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

  test("product truth ledger preserves controlled-launch boundaries", () => {
    expect(productTruthLedger).toContain("Dracula is the only currently approved core public reading release.");
    expect(productTruthLedger).toContain("Audiobooks are not public/live.");
    expect(productTruthLedger).toContain("Kshudhita Pashan remains pipeline-only.");
    expect(productTruthLedger).toContain("Draft PR evidence must not become public-product claims.");
    expect(productTruthLedger).toContain("blind-user tested");
    expect(productTruthLedger).toContain("WCAG compliant");
    expect(productTruthLedger).toContain("fully accessible audiobook platform");
    expect(productTruthLedger).toContain("Product-wide launch readiness: 8.0/10 HOLD");
    expect(productTruthLedger).toContain("Dracula controlled reading candidate: 9.9/10");
  });

  test("always-visible launch copy does not overclaim audio, accessibility, or PR branch evidence", () => {
    expect(alwaysVisibleLaunchCopy).not.toMatch(/\b(Kshudhita|Hungry Stones)\b[\s\S]{0,160}\b(Start Reading|Read Preview|Listen Now)\b/i);
    expect(alwaysVisibleLaunchCopy).not.toMatch(/\bfull audiobook\b[\s\S]{0,80}\b(available|live|ready|published)\b/i);
    expect(alwaysVisibleLaunchCopy).not.toMatch(/\baudiobooks are live\b/i);
    expect(alwaysVisibleLaunchCopy).not.toMatch(/\bDracula audio is available\b/i);
    expect(alwaysVisibleLaunchCopy).not.toMatch(/\bblind[- ]user tested\b/i);
    expect(alwaysVisibleLaunchCopy).not.toMatch(/\bWCAG compliant\b/i);
    expect(alwaysVisibleLaunchCopy).not.toMatch(/\bfully accessible audiobook platform\b/i);
    expect(alwaysVisibleLaunchCopy).not.toMatch(/\b10\/10\b/i);
    expect(alwaysVisibleLaunchCopy).not.toMatch(/\b9\.9\+\/10\b/i);
    expect(alwaysVisibleLaunchCopy).not.toMatch(/\bPR #4[2-6]\b[\s\S]{0,120}\b(live|merged|public|deployed)\b/i);
    expect(alwaysVisibleLaunchCopy).not.toMatch(/\bbranch-(only|visible)\b[\s\S]{0,120}\b(live|public|deployed)\b/i);
  });

  test("about, journal, and base html use reading-room truth instead of stale bookstore positioning", () => {
    for (const source of [about, journal, publicIndex]) {
      expect(source).not.toMatch(/independent online bookstore/i);
      expect(source).not.toMatch(/self-publishing house/i);
      expect(source).not.toMatch(/notes from a bookstore/i);
      expect(source).not.toMatch(/learn about the bookstore/i);
    }
    expect(about).toContain("reading room");
    expect(journal).toContain("notes from a reading room");
    expect(publicIndex).toContain("beginning with Dracula by Bram Stoker");
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

  test("static SEO snapshot generator is wired into the CRA build", () => {
    expect(frontendPackageJson).toContain('"postbuild": "node scripts/generate-static-seo-snapshots.mjs"');
    expect(staticSnapshotGenerator).toContain("Dracula by Bram Stoker | The Earnalism Digital Library");
    expect(staticSnapshotGenerator).toContain("Book");
    expect(staticSnapshotGenerator).toContain("BreadcrumbList");
    expect(staticSnapshotGenerator).toContain("noindex,follow");
    expect(staticSnapshotGenerator).toContain("/reader/dracula");
    expect(packageJson).toContain("launch:social-preview-audit");
    expect(packageJson).toContain("launch:social-preview-audit:prod");
    expect(packageJson).toContain("release:post-production-canary");
    expect(packageJson).toContain("ux:real-user-video-audit");
    expect(packageJson).toContain("ux:real-user-video-audit:headed");
    expect(packageJson).toContain("release:ux-go-no-go");
    expect(socialPreviewAudit).toContain("PRODUCTION_ROUTES");
    expect(socialPreviewAudit).toContain('"/reader/dracula"');
    expect(socialPreviewAudit).toContain("REQUIRED_PROPERTY_TAGS");
    expect(socialPreviewAudit).toContain("REQUIRED_NAME_TAGS");
    expect(socialPreviewAudit).toContain("FAKE_REVIEW_RATING_PATTERNS");
    expect(socialPreviewAudit).toContain("NEGATED_AUDIO_SAFETY_CLAIMS");
    expect(socialPreviewAudit).toContain("failed_checks");
    expect(postProductionCanary).toContain("launch:social-preview-audit:prod");
    expect(postProductionCanary).toContain("release:ux-go-no-go");
  });

  test("premium site-tour package is wired as a local brand-safety artifact", () => {
    expect(packageJson).toContain('"brand:site-tour": "python3 scripts/create_premium_site_tour.py"');
    expect(brandSiteTour).toContain("npm run ux:real-user-video-audit");
    expect(brandSiteTour).toContain("earnalism-site-tour-master.webm");
    expect(brandSiteTour).toContain("earnalism-site-tour-master.mp4");
    expect(brandSiteTour).toContain("earnalism-site-tour-vertical-9x16.mp4");
    expect(brandSiteTour).toContain("earnalism-site-tour-square-1x1.mp4");
    expect(brandSiteTour).toContain("earnalism-site-tour-short-15s.mp4");
    expect(brandSiteTour).toContain("earnalism-site-tour-captions.srt");
    expect(brandSiteTour).toContain("OPERATOR_REQUIRED");
    expect(brandSiteTour).toContain("HOLD_ADS_PENDING_HUMAN_VIDEO_REVIEW");
    expect(brandSiteTour).toContain("dracula_only_live");
    expect(brandSiteTour).toContain("kshudhita_pipeline_only");
    expect(brandSiteTour).toContain("paid_provider_apis_not_called");
    expect(siteTourVoiceover).toContain("Status: SCRIPT_ONLY");
    expect(siteTourVoiceover).toContain("No AI voice, TTS, audiobook generation");
    expect(siteTourFeatureReport).toContain("Audiobook availability claim: blocked");
    expect(siteTourFeatureReport).toContain("Broad live catalog claim: blocked");
    expect(siteTourScorecard).toContain("HOLD_ADS_PENDING_HUMAN_VIDEO_REVIEW");
    expect(siteTourScorecard).toContain("No fake testimonials");
  });

  test("built Dracula book snapshot exposes crawlable book SEO when build output exists", () => {
    const bookHtml = readOptional("frontend/build/book/dracula/index.html");
    if (!bookHtml) {
      expect(staticSnapshotGenerator).toContain("writeSnapshot");
      return;
    }

    expect(bookHtml).toContain("<title>Dracula by Bram Stoker | The Earnalism Digital Library</title>");
    expect(metaContent(bookHtml, "name", "description")).toContain("Read Dracula by Bram Stoker");
    expect(canonicalHref(bookHtml)).toBe("https://theearnalism.com/book/dracula");
    expect(metaContent(bookHtml, "property", "og:type")).toBe("book");
    expect(metaContent(bookHtml, "property", "og:title")).toContain("Dracula by Bram Stoker");
    expect(metaContent(bookHtml, "name", "twitter:card")).toBe("summary_large_image");
    expect(bookHtml).toContain('"@type": "Book"');
    expect(bookHtml).toContain('"@type": "BreadcrumbList"');
    expect(bookHtml).toContain("Project Gutenberg eBook #345");
    expect(bookHtml).not.toMatch(/aggregateRating|"review"\s*:/i);
    expect(bookHtml).not.toMatch(/Listen Now|audiobook available/i);
    expect(bookHtml).not.toContain("Preview every book before you pay");
  });

  test("built homepage and reader snapshots follow controlled launch SEO policy", () => {
    const homeHtml = readOptional("frontend/build/index.html");
    const readerHtml = readOptional("frontend/build/reader/dracula/index.html");
    if (!homeHtml || !readerHtml) {
      expect(staticSnapshotGenerator).toContain("Begin with Dracula");
      return;
    }

    expect(homeHtml).toContain("Begin with Dracula");
    expect(homeHtml).toContain("controlled launch begins with Dracula");
    expect(homeHtml).not.toContain("A quieter bookstore for readers who linger");
    expect(homeHtml).not.toContain("Preview every book before you pay");
    expect(metaContent(readerHtml, "name", "robots")).toContain("noindex");
    expect(canonicalHref(readerHtml)).toBe("https://theearnalism.com/book/dracula");
  });

  test("footer social links render only real configured http links", () => {
    const emptyConfig = loadSocialLinks({});
    expect(emptyConfig.getEnabledSocialLinks()).toEqual([]);

    const instagramConfig = loadSocialLinks({
      REACT_APP_INSTAGRAM_URL: "https://instagram.com/theearnalism",
    });
    expect(instagramConfig.getEnabledSocialLinks().map((link) => link.id)).toEqual(["instagram"]);

    const orderedConfig = loadSocialLinks({
      REACT_APP_TELEGRAM_CHANNEL_URL: "https://t.me/theearnalism",
      REACT_APP_LINKEDIN_URL: "https://www.linkedin.com/company/theearnalism",
      REACT_APP_YOUTUBE_URL: "https://youtube.com/@theearnalism",
    });
    expect(orderedConfig.getEnabledSocialLinks().map((link) => link.id)).toEqual([
      "youtube",
      "linkedin",
      "telegram-channel",
    ]);

    const unsafeLinks = [
      { id: "empty", url: "", enabled: true, order: 1 },
      { id: "hash", url: "#", enabled: true, order: 2 },
      { id: "script", url: "javascript:alert(1)", enabled: true, order: 3 },
      { id: "mailto", url: "mailto:sales@reoenterprise.org", enabled: true, order: 4 },
      { id: "disabled", url: "https://example.com", enabled: false, order: 5 },
    ];
    expect(emptyConfig.getEnabledSocialLinks(unsafeLinks)).toEqual([]);
  });

  test("footer social component is accessible, secure, and placed below contact email", () => {
    expect(socialLinksConfig).toContain("REACT_APP_INSTAGRAM_URL");
    expect(socialLinksConfig).toContain("REACT_APP_WHATSAPP_CHANNEL_URL");
    expect(socialLinksConfig).toContain("REACT_APP_TELEGRAM_CHANNEL_URL");
    expect(socialLinksConfig).toContain("new URL(trimmed)");
    expect(socialLinksConfig).toContain('["http:", "https:"]');
    expect(footerSocialLinks).toContain("getEnabledSocialLinks");
    expect(footerSocialLinks).toContain("if (!enabledLinks.length) return null");
    expect(footerSocialLinks).toContain("Follow The Earnalism");
    expect(footerSocialLinks).toContain('target="_blank"');
    expect(footerSocialLinks).toContain('rel="noopener noreferrer"');
    expect(footerSocialLinks).toContain("aria-label={link.ariaLabel}");
    expect(footerSocialLinks).not.toContain('href="#"');
    expect(footerSocialLinks).not.toContain('href=""');

    expect(footer.indexOf("CONTACT_EMAIL")).toBeGreaterThanOrEqual(0);
    expect(footer.indexOf("<FooterSocialLinks />")).toBeGreaterThan(footer.indexOf("mailto:${CONTACT_EMAIL}"));
    expect(footer).toContain("A quiet digital reading room beginning with Dracula by Bram Stoker.");
    expect(footer).toContain("Bengali Gothic and other classics are moving through the rights-safe pipeline.");
    expect(footer).not.toContain("A quiet digital reading room for Bengali classics, literary fiction, young readers");
    expect(styles).toContain(".footer-social");
    expect(styles).toContain("width: 2.75rem");
    expect(styles).toContain("height: 2.75rem");
    expect(styles).toContain(".footer-social__sr-label");
  });
});
