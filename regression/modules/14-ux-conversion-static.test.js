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
    .replace("export const OFFICIAL_SOCIAL_URLS =", "const OFFICIAL_SOCIAL_URLS =")
    .replace("export const SUPPORTED_SOCIAL_LINKS =", "const SUPPORTED_SOCIAL_LINKS =")
    .replace("export function normalizeSocialUrl", "function normalizeSocialUrl")
    .replace("export function getEnabledSocialLinks", "function getEnabledSocialLinks");
  const context = {
    module: { exports: {} },
    process: { env },
    URL,
  };
  vm.runInNewContext(
    `${source}\nmodule.exports = { OFFICIAL_SOCIAL_URLS, SUPPORTED_SOCIAL_LINKS, normalizeSocialUrl, getEnabledSocialLinks };`,
    context
  );
  return context.module.exports;
}

function trackFunnelEventSnippets(source) {
  return Array.from(source.matchAll(/trackFunnelEvent\(([\s\S]{0,360}?)\);/g), (match) => match[1]).join("\n");
}

describe("UX conversion static signals", () => {
  const home = read("frontend/src/pages/Home.jsx");
  const premiumHero = read("frontend/src/components/PremiumHero.jsx");
  const premiumHeroStyles = read("frontend/src/components/PremiumHero.css");
  const homeCurationClient = read("frontend/src/lib/homeCuration.js");
  const bookDetail = read("frontend/src/pages/BookDetail.jsx");
  const bookDetailPresentation = read("frontend/src/lib/bookDetailPresentation.js");
  const library = read("frontend/src/pages/Library.jsx");
  const about = read("frontend/src/pages/About.jsx");
  const journal = read("frontend/src/pages/Journal.jsx");
  const publicIndex = read("frontend/public/index.html");
  const bookCard = read("frontend/src/components/BookCard.jsx");
  const shelfTwoSlideshow = read("frontend/src/components/ShelfTwoSlideshow.jsx");
  const heroBookObject = read("frontend/src/components/HeroBookObject.jsx");
  const controlledLaunch = read("frontend/src/lib/controlledLaunch.js");
  const publicationSafety = read("frontend/src/lib/publicationSafety.js");
  const pricing = read("frontend/src/pages/Pricing.jsx");
  const login = read("frontend/src/pages/Login.jsx");
  const signup = read("frontend/src/pages/Signup.jsx");
  const account = read("frontend/src/pages/Account.jsx");
  const contact = read("frontend/src/pages/Contact.jsx");
  const layout = read("frontend/src/components/Layout.jsx");
  const useSeo = read("frontend/src/hooks/useSEO.js");
  const backend = read("backend/server.py");
  const analytics = read("frontend/src/lib/funnelAnalytics.js");
  const microStory = read("frontend/src/pages/MicroStoryLanding.jsx");
  const readerUpsell = read("frontend/src/components/Funnel/ReaderUpsellPrompt.jsx");
  const reader = read("frontend/src/pages/Reader.jsx");
  const launchAudit = read("scripts/launch_readiness_audit.py");
  const packageJson = read("package.json");
  const gitignore = read(".gitignore");
  const frontendPackageJson = read("frontend/package.json");
  const staticSnapshotGenerator = read("frontend/scripts/generate-static-seo-snapshots.mjs");
  const socialPreviewAudit = read("scripts/social_preview_audit.py");
  const postProductionCanary = read("scripts/post_production_canary.py");
  const brandSiteTour = read("scripts/create_premium_site_tour.py");
  const audiobookRegenerationWorkflow = read("scripts/audiobook_regeneration_workflow.py");
  const audiobookRegenerationReleaseGate = read("scripts/audiobook_release_gate.py");
  const audiobookGovernanceReport = read("AUDIOBOOK_REGENERATION_GOVERNANCE_REPORT.md");
  const audiobookDisclosurePolicy = read("AUDIOBOOK_DISCLOSURE_AND_CLAIMS_POLICY.md");
  const dailyRunbook = read("DAILY_GROWTH_AUDIT_RUNBOOK.md");
  const approvedToPublish = read("APPROVED_TO_PUBLISH.md");
  const firstBatchScorecard = read("FIRST_BATCH_RIGHTS_EVIDENCE_SCORECARD.md");
  const firstBatchMatrixCsv = read("FIRST_BATCH_REAL_SOURCE_MATRIX.csv");
  const firstBatchBackfillTemplate = read("FIRST_BATCH_REAL_SOURCE_BACKFILL_INPUT.template.json");
  const header = read("frontend/src/components/Header.jsx");
  const firstVisitSiteTour = read("frontend/src/components/FirstVisitSiteTour.jsx");
  const footer = read("frontend/src/components/Footer.jsx");
  const footerSocialLinks = read("frontend/src/components/FooterSocialLinks.jsx");
  const indiaCraftBadge = read("frontend/src/components/IndiaCraftBadge.jsx");
  const approvedAudiobookSpotlight = read("frontend/src/components/ApprovedAudiobookSpotlight.jsx");
  const socialLinksConfig = read("frontend/src/config/socialLinks.js");
  const styles = read("frontend/src/index.css");
  const app = read("frontend/src/App.js");
  const adminPage = read("frontend/src/pages/Admin.jsx");
  const siteTourVoiceover = read("EARNALISM_SITE_TOUR_VOICEOVER_SCRIPT.md");
  const siteTourFeatureReport = read("SITE_TOUR_FEATURE_HIGHLIGHT_REPORT.md");
  const siteTourScorecard = read("BRAND_SITE_TOUR_VIDEO_SCORECARD.md");
  const siteTourScorecardJson = JSON.parse(read("BRAND_SITE_TOUR_VIDEO_SCORECARD.json"));
  const siteTourIndex = read("BRAND_SITE_TOUR_VIDEO_INDEX.md");
  const siteTourIndexJson = JSON.parse(read("BRAND_SITE_TOUR_VIDEO_INDEX.json"));
  const siteTourHumanReview = read("BRAND_SITE_TOUR_HUMAN_REVIEW_FORM.md");
  const audiobookReleaseCriteria = read("AUDIOBOOK_ACCESSIBILITY_10_10_RELEASE_CRITERIA.md");
  const accessibleAudiobookJourney = read("ACCESSIBLE_AUDIOBOOK_USER_JOURNEY.md");
  const audiobookGateReport = read("AUDIOBOOK_ACCESSIBILITY_GATE_REPORT.md");
  const audiobookReleaseGate = read("scripts/audiobook_accessibility_release_gate.py");
  const narrationQaRubric = read("AUDIOBOOK_NARRATION_QA_RUBRIC.md");
  const bengaliNarrationScorecard = read("BENGALI_AUDIOBOOK_HUMAN_REVIEW_SCORECARD.md");
  const englishNarrationScorecard = read("ENGLISH_AUDIOBOOK_HUMAN_REVIEW_SCORECARD.md");
  const narrationModelDecisionReport = read("AUDIOBOOK_NARRATION_MODEL_DECISION_REPORT.md");
  const audiobookLegalComplianceGate = read("AUDIOBOOK_LEGAL_ACCESSIBILITY_COMPLIANCE_GATE.md");
  const accessibilityClaimsPolicy = read("ACCESSIBILITY_CLAIMS_POLICY.md");
  const audiobookComplianceScorecard = read("AUDIOBOOK_COMPLIANCE_SCORECARD.md");
  const paymentRevenueConfidenceReport = read("PAYMENT_REVENUE_10X_CONFIDENCE_REPORT.md");
  const launchNowReadingOnlyDecision = read("LAUNCH_NOW_READING_ONLY_DECISION.md");
  const revenueLaunchChecklist = read("REVENUE_LAUNCH_CHECKLIST.md");
  const finalLivePaymentSwitchRunbook = read("FINAL_LIVE_PAYMENT_SWITCH_RUNBOOK.md");
  const livePaymentGoNoGoChecklist = read("LIVE_PAYMENT_GO_NO_GO_CHECKLIST.md");
  const liveRazorpayCheckoutDrillReport = read("LIVE_RAZORPAY_CHECKOUT_DRILL_REPORT.md");
  const livePaymentFinalEvidenceReport = read("LIVE_PAYMENT_FINAL_EVIDENCE_REPORT.md");
  const audiobookParallelTrackStatus = read("AUDIOBOOK_PARALLEL_TRACK_STATUS.md");
  const productionReadingOnlyDeployRunbook = read("PRODUCTION_READING_ONLY_DEPLOY_RUNBOOK.md");
  const postDeployReadingOnlyCanaryReport = read("POST_DEPLOY_READING_ONLY_CANARY_REPORT.md");
  const postDeployReadingCanary = read("scripts/post_deploy_reading_canary.mjs");
  const launchMonitoringDashboardReport = read("LAUNCH_MONITORING_DASHBOARD_REPORT.md");
  const productionMonitoringRunbook = read("PRODUCTION_24_48_HOUR_MONITORING_RUNBOOK.md");
  const seoRevenueReadinessReport = read("SEO_REVENUE_READINESS_REPORT.md");
  const revenueFunnelReadinessReport = read("REVENUE_FUNNEL_READINESS_REPORT.md");
  const readingLaunchFunnelTrackingPlan = read("READING_LAUNCH_FUNNEL_TRACKING_PLAN.md");
  const postLaunchFunnelBaselineReport = read("POST_LAUNCH_FUNNEL_BASELINE_REPORT.md");
  const performanceRevenueReadinessReport = read("PERFORMANCE_REVENUE_READINESS_REPORT.md");
  const autoscalingOperationsReadinessReport = read("AUTOSCALING_OPERATIONS_READINESS_REPORT.md");
  const readingOnlyRevenueOperationsScorecard = read("READING_ONLY_REVENUE_OPERATIONS_SCORECARD.md");
  const signedUserJourneyRecorder = read("scripts/record_signed_user_journey.mjs");
  const signedUserRecordingReport = read("SIGNED_USER_FULL_JOURNEY_RECORDING_REPORT.md");
  const signedUserRegressionReport = read("SIGNED_USER_JOURNEY_REGRESSION_REPORT.md");
  const signedUserUxScorecard = read("SIGNED_USER_UX_10_10_SCORECARD.md");
  const signedUserUxBacklog = read("SIGNED_USER_UX_ENHANCEMENT_BACKLOG.md");
  const signedUserUxBeforeAfter = read("SIGNED_USER_UX_BEFORE_AFTER_REPORT.md");
  const paymentReceiptAudit = read("PAYMENT_RECEIPT_AND_INVOICE_AUDIT.md");
  const samplePaymentReceiptTemplate = read("SAMPLE_PAYMENT_RECEIPT_TEMPLATE.md");
  const paymentReceiptEmailPlan = read("PAYMENT_RECEIPT_EMAIL_IMPLEMENTATION_PLAN.md");
  const premiumLandingVisualReview = read("PREMIUM_LANDING_PAGE_VISUAL_REVIEW_REPORT.md");
  const luxuryVisualScorecard = read("LUXURY_VISUAL_AMBIENCE_SCORECARD.md");
  const pixelUtilizationScorecard = read("LANDING_PIXEL_UTILIZATION_GROWTH_SCORECARD.md");
  const homepageLuxuryThemeReport = read("HOMEPAGE_LUXURY_THEME_10_10_REPORT.md");
  const homepageRevenuePixelScorecard = read("HOMEPAGE_REVENUE_PIXEL_UTILIZATION_SCORECARD.md");
  const homepageSocialPipelineAudit = read("HOMEPAGE_SOCIAL_AND_PIPELINE_VISUAL_AUDIT.md");
  const homepageHeroLibraryThemeReview = read("HOMEPAGE_HERO_LIBRARY_THEME_REVIEW.md");
  const homepageHeroLuxuryScorecard = read("HOMEPAGE_HERO_LUXURY_SCORECARD.md");
  const homepageHeroConversionScorecard = read("HOMEPAGE_HERO_CONVERSION_SCORECARD.md");
  const homepageReferenceHeroImplementationReport = read("HOMEPAGE_REFERENCE_HERO_IMPLEMENTATION_REPORT.md");
  const homepageReferenceLuxuryScorecard = read("HOMEPAGE_REFERENCE_LUXURY_SCORECARD.md");
  const homepageReferenceRevenueUxScorecard = read("HOMEPAGE_REFERENCE_REVENUE_UX_SCORECARD.md");
  const controlledPublicationPrecheck = read("scripts/controlled_publication_precheck.py");
  const internalAudiobookPrototype = read("frontend/src/components/Internal/InternalAudiobookPlayerPrototype.jsx");
  const accessibleAudiobookPrototypeReport = read("PREMIUM_ACCESSIBLE_AUDIOBOOK_PLAYER_REPORT.md");
  const renderedPricingSources = [backend, pricing, microStory, readerUpsell, reader].join("\n");
  const productTruthLedger = read("PRODUCT_TRUTH_LEDGER.md");
  const alwaysVisibleLaunchCopy = [
    home,
    premiumHero,
    library,
    bookDetail,
    pricing,
    microStory,
    readerUpsell,
    header,
    firstVisitSiteTour,
    footer,
    controlledLaunch,
    staticSnapshotGenerator,
  ].join("\n");
  const livePaymentEvidenceDocs = [
    finalLivePaymentSwitchRunbook,
    livePaymentGoNoGoChecklist,
    liveRazorpayCheckoutDrillReport,
    livePaymentFinalEvidenceReport,
    revenueLaunchChecklist,
    productionReadingOnlyDeployRunbook,
    postDeployReadingOnlyCanaryReport,
  ].join("\n");

  test("homepage exposes approved bilingual library positioning and release-truth CTAs", () => {
    expect(home).toContain("fetchHomeCuration");
    expect(home).toContain("<PremiumHero");
    expect(premiumHero).toContain('data-testid="hero-cta-library"');
    expect(premiumHero).toContain('data-testid="hero-cta-audiobooks"');
    expect(premiumHero).toContain("A premium reading and listening sanctuary for timeless Bengali and English classics.");
    expect(premiumHero).toContain("Beautifully designed editions. Immersive audiobooks. Calm reading modes.");
    expect(premiumHero).toContain("Start Reading");
    expect(premiumHero).toContain("Explore Audiobooks");
    expect(premiumHero).toContain("/library?availability=approved-audiobook");
    expect(homeCurationClient).toContain('/home/curated');
    expect(homeCurationClient).toContain('audiobookUrl === `/api/reader/book/${slug}/audiobook`');
    expect(premiumHero).not.toMatch(/No unapproved audiobook controls|Audio gated by evidence|release gates|QA_PASSED|APPROVED/);
    expect(home).toContain("Coming Through the Rights-Safe Pipeline");
    expect(shelfTwoSlideshow).toContain("Request Update");
    expect(shelfTwoSlideshow).toContain("/contact?interest=");
    expect(shelfTwoSlideshow).not.toContain("Notify Me");
    expect(home).toContain('data-testid="reading-time-library-path"');
    expect(home).toContain("A revenue path that still feels like a library.");
    expect(home).toContain("No fake urgency, no broad ownership promise, and no hidden audio overclaim.");
    expect(home).toContain("See Reading Passes");
    expect(home).toContain("Open the room");
    expect(home).toContain("Add reading time");
    expect(home).toContain("Return calmly");
    expect(home).not.toContain('data-testid="dracula-journey-map"');
    expect(home).not.toContain('data-testid="home-live-dracula"');
    expect(home).not.toContain('data-testid="controlled-carousel-section"');
    expect(home).not.toContain('data-testid="dracula-shelves"');
    expect(home).not.toContain("A quieter bookstore for readers who linger");
    expect(home).not.toContain("Preview every book before you pay");
    expect(home).not.toContain("Discover thoughtful books across");
    expect(home).not.toMatch(/\b105 reading rooms open\b/i);
    expect(home).not.toContain("reading rooms open");
    expect(firstVisitSiteTour).toContain("A calm digital reading room for Bengali and English classics");
    expect(firstVisitSiteTour).toContain("Audio never leaks early");
    expect(firstVisitSiteTour).toContain("Reader-only books still feel complete");
    expect(firstVisitSiteTour).not.toContain("A calm digital reading room beginning with Dracula by Bram Stoker");
    expect(firstVisitSiteTour).not.toContain("Future titles stay Coming Soon or Notify Me");
    expect(firstVisitSiteTour).not.toContain("Browse what is ready now");
  });

  test("premium landing visual pass keeps hero efficient, local, and truthful", () => {
    expect(premiumHero).toContain('data-testid="premium-landing-hero"');
    expect(premiumHero).toContain('data-testid="hero-catalog-visuals"');
    expect(premiumHero).toContain('data-testid="premium-hero-feature-cards"');
    expect(premiumHero).toContain("Curated Classics");
    expect(premiumHero).toContain("Immersive Audiobooks");
    expect(premiumHero).toContain("Beautiful Editions");
    expect(premiumHero).toContain("Calm Reading Modes");
    expect(premiumHero).toContain("book.front_cover_url");
    expect(premiumHero).toContain("book.cover_alt_text");
    expect(premiumHero).toContain("approvedAudiobooks[0]");
    expect(premiumHeroStyles).toContain(".premium-dynamic-hero");
    expect(premiumHeroStyles).toContain(".premium-hero-cover-stack");
    expect(premiumHeroStyles).toContain("transform: perspective(");
    expect(premiumHeroStyles).toMatch(/@media\s*\(max-width:\s*560px\)/);
    expect(styles).not.toContain(".reference-dracula-hardcopy-shell::after");
    expect(styles).not.toContain(".reference-dracula-hardcopy-shell::before");
    expect(styles).not.toContain("APPROVED CLASSIC READING RELEASE");
    expect(styles).not.toContain("backdrop-filter: blur(9px)");
    expect(styles).not.toContain("clip-path: inset(0 5.9% 14% 12.3%)");
    expect(fs.existsSync(path.join(ROOT, "frontend/public/assets/books/dracula/dracula-front-cover.webp"))).toBe(true);
    expect(fs.existsSync(path.join(ROOT, "frontend/public/assets/books/dracula/dracula-hero-hardcopy-320.webp"))).toBe(true);
    expect(fs.existsSync(path.join(ROOT, "frontend/public/assets/books/dracula/dracula-hero-hardcopy-420.webp"))).toBe(true);
    expect(fs.existsSync(path.join(ROOT, "frontend/public/assets/books/dracula/dracula-hero-hardcopy-500.webp"))).toBe(true);
    expect(premiumHero).not.toContain("images.unsplash.com");
    expect(home).not.toMatch(/lg:pt-36|lg:pb-32|sm:pt-32|pb-24/);

    expect(controlledLaunch).toContain('DRACULA_COVER_IMAGE = "/assets/books/dracula/dracula-front-cover.webp"');
    expect(controlledLaunch).toContain('DRACULA_BACK_COVER_IMAGE = "/assets/books/dracula/dracula-back-cover.webp"');
    expect(controlledLaunch).toContain("cover_image_url: DRACULA_COVER_IMAGE");
    expect(controlledLaunch).toContain("cover_url: DRACULA_COVER_IMAGE");
    expect(controlledLaunch).toContain("thumbnail_url: DRACULA_COVER_IMAGE");
    expect(controlledLaunch).toContain("back_cover_image_url: DRACULA_BACK_COVER_IMAGE");
    expect(controlledLaunch).toContain("back_cover_url: DRACULA_BACK_COVER_IMAGE");
    expect(controlledLaunch).toContain("back_cover_thumbnail_url: DRACULA_BACK_COVER_IMAGE");
    expect(staticSnapshotGenerator).toContain("assets/books/dracula/dracula-front-cover.webp");
    expect(bookDetail).toContain("publicBook?.cover_image_url");
    expect(bookDetail).toContain("mergeDraculaBook(book)");
    expect(useSeo).toContain("assets/books/dracula/dracula-front-cover.webp");
    expect(useSeo).not.toContain("images.unsplash.com/photo-1507842217343-583bb7270b66");
    expect(publicIndex).toContain("https://theearnalism.com/assets/brand/earnalism-logo.png");
    expect(publicIndex).toContain("The Earnalism brand mark");
    expect(publicIndex).not.toContain("images.unsplash.com/photo-1507842217343-583bb7270b66");
    expect(fs.existsSync(path.join(ROOT, "frontend/public/assets/books/dracula/dracula-front-cover.webp"))).toBe(true);
    expect(fs.existsSync(path.join(ROOT, "frontend/public/assets/books/dracula/dracula-back-cover.webp"))).toBe(true);

    expect(premiumLandingVisualReview).toContain("USE_OWNER_DESIGNED_COVER_WITH_INTERNAL_PROVENANCE");
    expect(premiumLandingVisualReview).toContain("Dracula - Front.png");
    expect(premiumLandingVisualReview).toContain("Dracula - Back.png");
    expect(premiumLandingVisualReview).toContain("Do not describe the custom cover as archival, public-domain, first-edition, or external-review evidence.");
    expect(premiumLandingVisualReview).toContain("Approved hero threshold:");

    expect(luxuryVisualScorecard).toContain("Overall luxury score: `10/10`");
    expect(pixelUtilizationScorecard).toContain("Overall growth-friendly UX score: `10/10`");
    expect(homepageLuxuryThemeReport).toContain("Overall homepage score: `10/10`");
    expect(homepageRevenuePixelScorecard).toContain("Revenue pixel-utilization score: `10/10`");
    expect(homepageSocialPipelineAudit).toContain("Kshudhita Pashan cover status: `OWNER_PROVIDED_COVER_READY`");
    expect(homepageSocialPipelineAudit).toContain("No fake social links are rendered");
    expect(homepageHeroLuxuryScorecard).toContain("Luxury/theme score: `10/10`");
    expect(homepageHeroConversionScorecard).toContain("Conversion clarity score: `10/10`");
    expect(homepageHeroConversionScorecard).toContain("Public-claims safety score: `10/10`");
    expect(homepageReferenceHeroImplementationReport).toContain("display-only hard-copy object");
    expect(homepageReferenceHeroImplementationReport).toContain('data-approved-hero-max-height="650"');
    expect(homepageReferenceLuxuryScorecard).toContain("Overall luxury/theme score | 9.8/10");
    expect(homepageReferenceRevenueUxScorecard).toContain("Overall revenue UX score | 9.8/10");
    expect(luxuryVisualScorecard).toContain("Why This Is Now 10/10");
    expect(pixelUtilizationScorecard).toContain("Why This Is Now 10/10");
    expect(premiumLandingVisualReview).toContain("Why This Is Now 10/10");
    expect(home).not.toContain("golden-hour-library-hero.webp");
    expect(home).not.toContain("classical-library-reading-room.webp");
    expect(styles).toContain(".reference-editorial-stage");
    expect(styles).toContain(".reference-pipeline-shelf");
    expect(styles).toContain(".shelf-two-book");
    expect(styles).not.toMatch(/letter-spacing:\s*-[1-9]/);

    const premiumLandingSources = [
      home,
      controlledLaunch,
      premiumLandingVisualReview,
      luxuryVisualScorecard,
      pixelUtilizationScorecard,
      homepageLuxuryThemeReport,
      homepageRevenuePixelScorecard,
      homepageSocialPipelineAudit,
      homepageHeroLibraryThemeReview,
      homepageHeroLuxuryScorecard,
      homepageHeroConversionScorecard,
      homepageReferenceHeroImplementationReport,
      homepageReferenceLuxuryScorecard,
      homepageReferenceRevenueUxScorecard,
    ].join("\n");
    expect(premiumLandingSources).not.toMatch(/\b(audio|audiobook)\s+(is|are)\s+(live|public|available|ready)\b/i);
    expect(premiumLandingSources).not.toMatch(/\bListen Now\b/i);
    expect(premiumLandingSources).not.toMatch(/\bKshudhita Pashan\b[\s\S]{0,160}\b(Start Reading|Read Preview|Listen Now|public reader|public audio)\b/i);
    expect(premiumLandingSources).not.toMatch(/\b(all|every|100\+|105)\s+(books|classics|titles)\s+(are\s+)?(live|available|readable)\b/i);
    expect(premiumLandingSources).not.toMatch(/\bWCAG compliant\b|\bblind[- ]user tested\b|\bfully accessible\b/i);
    expect(premiumLandingSources).not.toMatch(/\b(buy|own|ownership|forever)\b[\s\S]{0,80}\b(book|classic|edition)\b/i);
    expect(premiumLandingSources).not.toMatch(/\b(fashion|clothing|apparel|self-publishing|WooCommerce|Add to cart|Shop now)\b/i);
  });

  test("library and book pages expose controlled reader-only paths without broad catalog or payment overclaim", () => {
    expect(library).toContain("Bengali and English classics, opened with release truth.");
    expect(library).toContain("Curated Reader-Ready Shelves");
    expect(library).toContain("Reader-only public-domain shelf");
    expect(library).toContain('data-testid="library-bengali-reader-grid"');
    expect(library).toContain('data-testid="library-english-reader-grid"');
    expect(library).toContain("Dracula remains a featured route, not the whole library identity.");
    expect(library).toContain("Coming Through the Rights-Safe Pipeline");
    expect(library).toContain("source, listening, sync, and browser gates pass");
    expect(library).toContain("No reader, payment, or audio CTA is available for this pipeline-only title.");
    expect(library).toContain("Read Chapter 1 Free");
    expect(library).toContain("Read English Classic");
    expect(library).toContain("Public-domain source verified");
    expect(library).toContain("Request Update");
    expect(bookDetail).toContain('data-testid="start-reading"');
    expect(bookDetailPresentation).toContain('primaryReadLabel: readerReady ? "Start Reading" : "Back to Library"');
    expect(bookDetail).toContain("DRACULA_SOURCE_NOTE");
    expect(bookDetail).toContain("Audio:</strong> Audiobooks appear only after release-gate evidence approves them.");
    expect(bookDetail).toContain('data-testid="book-reading-pass"');
    expect(bookDetail).toContain("{isDracula && (");
    expect(bookDetail).toContain('data-testid="book-experience-truth"');
    expect(bookDetail).toContain("Chapter 1 opens free so you can feel the room before adding reading time.");
    expect(bookDetail).toContain("Get 7-Day Reading Pass");
    expect(bookDetailPresentation).toContain("No public audio controls are shown until narration, sync, metadata, endpoint, and browser gates pass.");
    expect(bookDetailPresentation).toContain("audioState.canShowControls");
  });

  test("payment revenue confidence stays test-mode, wallet-time, and audio-blocked", () => {
    expect(paymentRevenueConfidenceReport).toContain("Status: `HOLD_FOR_CONTROLLED_TEST_MODE_CHECKOUT`");
    expect(paymentRevenueConfidenceReport).toContain("Current confidence score: `9.1/10`");
    expect(paymentRevenueConfidenceReport).toContain("No live Razorpay payment was run");
    expect(paymentRevenueConfidenceReport).toContain("Public audio remains `PUBLIC_AUDIO_RELEASE_BLOCKED`");
    expect(paymentRevenueConfidenceReport).toContain("No audiobook sale is live");
    expect(paymentRevenueConfidenceReport).toContain("Top-up intents expire after 24 hours");
    expect(packageJson).toContain('"launch:payment-smoke:test-mode": "python3 scripts/launch_readiness_audit.py --mode payment-smoke-test-mode"');
    expect(launchAudit).toContain('"stale_intent_expiry_detected"');
    expect(launchAudit).toContain('"no_public_audiobook_sale_detected"');
    expect(alwaysVisibleLaunchCopy).toContain("Reading time is used only while you read.");
    expect(alwaysVisibleLaunchCopy).toContain("Chapter 1 remains free to preview");
    expect(renderedPricingSources).toContain("No subscription or autorenewal");
    expect(renderedPricingSources).not.toMatch(/own forever|ownership forever|permanent ownership|autorenewing plan|recurring subscription/i);
    expect(renderedPricingSources).not.toMatch(/buy audiobook|audiobook pass|Listen Now/i);
    expect(bookDetailPresentation).toContain("audioState.canShowControls");
    expect(approvedAudiobookSpotlight).toContain("if (!audioState.canShowControls) return null;");
    expect(alwaysVisibleLaunchCopy).not.toMatch(/listen-now|href=["'][^"']*audio/i);
  });

  test("reading-only revenue launch decision keeps Dracula live and audiobook blocked", () => {
    expect(launchNowReadingOnlyDecision).toContain("GO_READING_ONLY_PRODUCTION_DEPLOY_READY");
    expect(launchNowReadingOnlyDecision).toContain("Dracula core reading product only");
    expect(launchNowReadingOnlyDecision).toContain("Chapter 1 free preview");
    expect(launchNowReadingOnlyDecision).toContain("reading-time wallet/pass model");
    expect(launchNowReadingOnlyDecision).toContain("GO_DRACULA_CORE_READING_ONLY");
    expect(launchNowReadingOnlyDecision).toContain("PAYMENT_REVENUE_10X_CONFIDENCE_REPORT.md");
    expect(launchNowReadingOnlyDecision).toContain("LIVE_RAZORPAY_CHECKOUT_DRILL_REPORT.md");
    expect(launchNowReadingOnlyDecision).toContain("LIVE_PAYMENT_FINAL_EVIDENCE_REPORT.md");
    expect(launchNowReadingOnlyDecision).toContain("wallet credit, webhook receipt, duplicate replay prevention, refund/support readiness, and rollback readiness are owner-verified");
    expect(launchNowReadingOnlyDecision).toContain("PUBLIC_AUDIO_RELEASE_BLOCKED");
    expect(launchNowReadingOnlyDecision).toContain("PRODUCTION_BLOCKED");
    expect(launchNowReadingOnlyDecision).not.toMatch(/\bGO_PUBLIC_AUDIOBOOK_RELEASE\b/);
    expect(launchNowReadingOnlyDecision).not.toMatch(/\bGO_BROAD_CATALOG_LAUNCH\b/);

    expect(revenueLaunchChecklist).toContain("Razorpay Test-Mode Checks");
    expect(revenueLaunchChecklist).toContain("Live Payment Switch Checklist");
    expect(revenueLaunchChecklist).toContain("Refund And Support Checklist");
    expect(revenueLaunchChecklist).toContain("Monitoring Checklist");
    expect(revenueLaunchChecklist).toContain("Founder Launch Checklist");
    expect(revenueLaunchChecklist).toContain("Rollback Checklist");
    expect(revenueLaunchChecklist).toContain("No automatic deploy from this checklist");
    expect(revenueLaunchChecklist).toContain("Live low-value owner checkout drill: `COMPLETED_OWNER_REPORTED`");
    expect(revenueLaunchChecklist).toContain("Final live payment GO: `GO_READING_ONLY_PRODUCTION_DEPLOY_READY`");
    expect(revenueLaunchChecklist).toContain("Final evidence file: `LIVE_PAYMENT_FINAL_EVIDENCE_REPORT.md`");
    expect(revenueLaunchChecklist).toContain("No payment evidence blockers remain for Dracula reading-only production deploy readiness.");
    expect(revenueLaunchChecklist).toContain("Confirm production environment has live Razorpay variables configured outside the repository.");
    expect(revenueLaunchChecklist).toContain("Confirm no ElevenLabs generation variables are enabled in production.");

    expect(audiobookParallelTrackStatus).toContain("Audio status: `INTERNAL_FULL_CHAPTER_ONLY`");
    expect(audiobookParallelTrackStatus).toContain("Owner listening QA score: `9.4/10`");
    expect(audiobookParallelTrackStatus).toContain("Sync status: `HOLD_SYNC_QA_REQUIRED`");
    expect(audiobookParallelTrackStatus).toContain("Public audio release: `PUBLIC_AUDIO_RELEASE_BLOCKED`");
    expect(audiobookParallelTrackStatus).toContain("Production audio status: `PRODUCTION_BLOCKED`");
  });

  test("live Razorpay final evidence is redacted and marks reading-only deploy ready", () => {
    expect(finalLivePaymentSwitchRunbook).toContain("READING_ONLY_LIVE_PAYMENT_SWITCH_READY");
    expect(finalLivePaymentSwitchRunbook).toContain("GO_READING_ONLY_PRODUCTION_DEPLOY_READY");
    expect(finalLivePaymentSwitchRunbook).toContain("Wallet credit confirmed.");
    expect(finalLivePaymentSwitchRunbook).toContain("Webhook delivery confirmed.");
    expect(finalLivePaymentSwitchRunbook).toContain("Duplicate replay prevention confirmed.");
    expect(finalLivePaymentSwitchRunbook).toContain("Keep public audio blocked.");

    expect(livePaymentGoNoGoChecklist).toContain("GO_READING_ONLY_PRODUCTION_DEPLOY_READY");
    expect(livePaymentGoNoGoChecklist).toContain("[x] Owner completed one low-value live checkout drill with Razorpay.");
    expect(livePaymentGoNoGoChecklist).toContain("| Wallet credited exactly once | YES_OWNER_VERIFIED | Must be YES |");
    expect(livePaymentGoNoGoChecklist).toContain("| Webhook received | YES_OWNER_VERIFIED | Must be YES |");
    expect(livePaymentGoNoGoChecklist).toContain("| Duplicate credit prevention | VERIFIED | Must be VERIFIED |");
    expect(livePaymentGoNoGoChecklist).toContain("Current go/no-go: `GO_READING_ONLY_PRODUCTION_DEPLOY_READY`");
    expect(livePaymentGoNoGoChecklist).toContain("Owner payment evidence sign-off | YES");

    expect(liveRazorpayCheckoutDrillReport).toContain("LIVE_CHECKOUT_DRILL_RECORDED_FINAL_PAYMENT_EVIDENCE_COMPLETE");
    expect(liveRazorpayCheckoutDrillReport).toContain("| Provider | Razorpay |");
    expect(liveRazorpayCheckoutDrillReport).toContain("| Mode | LIVE |");
    expect(liveRazorpayCheckoutDrillReport).toContain("| Payment success | YES |");
    expect(liveRazorpayCheckoutDrillReport).toContain("| Wallet credited | YES |");
    expect(liveRazorpayCheckoutDrillReport).toContain("| Webhook received | YES |");
    expect(liveRazorpayCheckoutDrillReport).toContain("| Duplicate credit prevention | VERIFIED |");
    expect(liveRazorpayCheckoutDrillReport).toContain("| Secrets committed | NO |");
    expect(liveRazorpayCheckoutDrillReport).toContain("| Personal/payment data committed | NO |");
    expect(liveRazorpayCheckoutDrillReport).toContain("| Final recommendation | GO_READING_ONLY_PRODUCTION_DEPLOY_READY |");

    expect(livePaymentFinalEvidenceReport).toContain("GO_READING_ONLY_PRODUCTION_DEPLOY_READY");
    expect(livePaymentFinalEvidenceReport).toContain("| Payment success | YES |");
    expect(livePaymentFinalEvidenceReport).toContain("| Wallet credit observed | YES |");
    expect(livePaymentFinalEvidenceReport).toContain("| Wallet credit evidence | REDACTED_REFERENCE_ONLY |");
    expect(livePaymentFinalEvidenceReport).toContain("| Webhook received | YES |");
    expect(livePaymentFinalEvidenceReport).toContain("| Webhook evidence | REDACTED_REFERENCE_ONLY |");
    expect(livePaymentFinalEvidenceReport).toContain("| Duplicate replay prevention | VERIFIED |");
    expect(livePaymentFinalEvidenceReport).toContain("| Refund/support readiness | READY |");
    expect(livePaymentFinalEvidenceReport).toContain("| Rollback readiness | READY |");
    expect(livePaymentFinalEvidenceReport).toContain("| Final payment decision | GO |");
    expect(livePaymentFinalEvidenceReport).toContain("| Secrets committed | NO |");
    expect(livePaymentFinalEvidenceReport).toContain("| Personal/payment data committed | NO |");
    expect(livePaymentFinalEvidenceReport).toContain("This report intentionally stores no full payment IDs");

    expect(livePaymentEvidenceDocs).toContain("Dracula reading-only");
    expect(livePaymentEvidenceDocs).toContain("PUBLIC_AUDIO_RELEASE_BLOCKED");
    expect(livePaymentEvidenceDocs).toContain("PRODUCTION_BLOCKED");
    expect(livePaymentEvidenceDocs).toContain("GO_READING_ONLY_PRODUCTION_DEPLOY_READY");
    expect(livePaymentEvidenceDocs).not.toMatch(/\bGO_PUBLIC_AUDIOBOOK_RELEASE\b/i);
    for (const line of livePaymentEvidenceDocs.split(/\r?\n/).filter((item) => /Listen Now|AudioObject/i.test(item))) {
      expect(line).toMatch(/not allowed|No |does not approve/i);
      expect(line).not.toMatch(/\b(is|are|CTA is|metadata is)\s+(allowed|available|live|shown|enabled)\b/i);
    }
    expect(livePaymentEvidenceDocs).toMatch(/\bListen Now CTA: not allowed\b/i);
    expect(livePaymentEvidenceDocs).toMatch(/\bAudioObject metadata: not allowed\b/i);
  });

  test("live payment evidence docs do not contain likely secrets or personal payment data", () => {
    const forbiddenPatterns = [
      /\brzp_(?:live|test)_[A-Za-z0-9]{8,}\b/i,
      /\b(?:pay|order|cust)_[A-Za-z0-9]{8,}\b/i,
      /\bAuthorization\s*:\s*(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{12,}/i,
      /\bBearer\s+[A-Za-z0-9._~+/=-]{12,}/i,
      /\bxi-api-key\s*[:=]\s*[A-Za-z0-9._~+/=-]{12,}/i,
      /\bsk_[A-Za-z0-9]{16,}\b/i,
      /\b(?:RAZORPAY_KEY_SECRET|RAZORPAY_WEBHOOK_SECRET|WEBHOOK_SECRET|API_KEY|SECRET|TOKEN)\s*[:=]\s*["']?[A-Za-z0-9_./+=-]{8,}/i,
      /\b(?:\d[ -]*?){12,19}\b/,
      /\b(?:UPI ID|VPA|IFSC|bank account|account number|invoice number)\b/i,
      /\b(?:\+?\d{1,3}[-. ]?)?(?:\(?\d{3}\)?[-. ]?){2}\d{4}\b/,
      /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i,
    ];
    for (const pattern of forbiddenPatterns) {
      expect(livePaymentEvidenceDocs).not.toMatch(pattern);
    }
    expect(livePaymentEvidenceDocs).toContain("REDACTED_LOW_VALUE_OWNER_DRILL_PACK");
    expect(livePaymentEvidenceDocs).toContain("REDACTED_LOW_VALUE_AMOUNT");
    expect(livePaymentEvidenceDocs).toContain("REDACTED_REFERENCE_ONLY");
    expect(livePaymentEvidenceDocs).toContain("No payment ID, customer ID, card data, UPI data, bank data, invoice, screenshot, or secret is committed.");
  });

  test("production reading-only deploy workflow stays post-deploy gated and audio blocked", () => {
    expect(productionReadingOnlyDeployRunbook).toContain("READY_FOR_OWNER_CONTROLLED_DEPLOY");
    expect(productionReadingOnlyDeployRunbook).toContain("GO_READING_ONLY_PRODUCTION_DEPLOY_READY");
    expect(productionReadingOnlyDeployRunbook).toContain("HOLD_POST_DEPLOY_CANARY_REQUIRED");
    expect(productionReadingOnlyDeployRunbook).toContain("Do not mark launch complete until post-deploy canaries pass against production.");
    expect(productionReadingOnlyDeployRunbook).toContain("No `ELEVENLABS_API_KEY` or ElevenLabs generation enablement variables are active");
    expect(productionReadingOnlyDeployRunbook).toContain("Do not run a live checkout from this runbook unless the owner explicitly performs it outside the repository.");
    expect(productionReadingOnlyDeployRunbook).toContain("Public audio release: `PUBLIC_AUDIO_RELEASE_BLOCKED`");
    expect(productionReadingOnlyDeployRunbook).toContain("Audiobook production: `PRODUCTION_BLOCKED`");
    expect(productionReadingOnlyDeployRunbook).toContain("Kshudhita Pashan and future titles: pipeline-only.");

    expect(postDeployReadingOnlyCanaryReport).toContain("TEMPLATE_PENDING_PRODUCTION_DEPLOY");
    expect(postDeployReadingOnlyCanaryReport).toContain("HOLD_POST_DEPLOY_CANARY_REQUIRED");
    expect(postDeployReadingOnlyCanaryReport).toContain("No Listen Now CTA");
    expect(postDeployReadingOnlyCanaryReport).toContain("No AudioObject metadata");
    expect(postDeployReadingOnlyCanaryReport).toContain("No Kshudhita public CTA");
    expect(postDeployReadingOnlyCanaryReport).toContain("No unapproved book payment CTA");
    expect(postDeployReadingOnlyCanaryReport).toContain("Does not execute live payment.");
    expect(postDeployReadingOnlyCanaryReport).toContain("Does not mutate production data.");

    expect(packageJson).toContain('"launch:post-deploy-canary": "node scripts/post_deploy_reading_canary.mjs"');
    expect(postDeployReadingCanary).toContain("PRODUCTION_BASE_URL");
    expect(postDeployReadingCanary).toContain("GET");
    expect(postDeployReadingCanary).toContain("PUBLIC_AUDIO_RELEASE_BLOCKED");
    expect(postDeployReadingCanary).toContain("PRODUCTION_BLOCKED");
    expect(postDeployReadingCanary).toContain("live_payment_executed: false");
    expect(postDeployReadingCanary).not.toMatch(/\bmethod:\s*["']POST["']/);
    expect(postDeployReadingCanary).not.toMatch(/process\.env\.RAZORPAY/i);
    expect(postDeployReadingCanary).not.toMatch(/process\.env\.ELEVENLABS/i);
    expect(postDeployReadingCanary).not.toMatch(/\bAuthorization\s*:/);
  });

  test("post-launch revenue, SEO, performance, and operations reports are evidence-led", () => {
    expect(productionMonitoringRunbook).toContain("Launch status: LIVE_VERIFIED");
    expect(productionMonitoringRunbook).toContain("SEO And Crawler Monitoring");
    expect(productionMonitoringRunbook).toContain("Performance Monitoring");
    expect(productionMonitoringRunbook).toContain("Backend Logs");
    expect(productionMonitoringRunbook).toContain("PUBLIC_AUDIO_RELEASE_BLOCKED");
    expect(productionMonitoringRunbook).toContain("PRODUCTION_BLOCKED");

    expect(seoRevenueReadinessReport).toContain("SEO revenue readiness: GO_MONITOR_AND_OPTIMIZE");
    expect(seoRevenueReadinessReport).toContain("The generated sitemap currently contains 11 routes");
    expect(seoRevenueReadinessReport).toContain("`/reader/dracula` | Noindex and canonicalized to `/book/dracula`");
    expect(seoRevenueReadinessReport).toContain("No public audiobook metadata, Listen Now CTA, AudioObject schema");
    expect(seoRevenueReadinessReport).toContain("Metadata quality | 9.4/10");
    expect(seoRevenueReadinessReport).toContain("Owner dashboard verification required");
    expect(seoRevenueReadinessReport).not.toMatch(/\bGO_PUBLIC_AUDIOBOOK_RELEASE\b/i);

    expect(revenueFunnelReadinessReport).toContain("Revenue funnel readiness: GO_MONITOR_24_48_HOURS");
    expect(revenueFunnelReadinessReport).toContain("Wallet credited | Backend/account | OWNER_VERIFIED");
    expect(revenueFunnelReadinessReport).toContain("Public audiobook | BLOCKED");
    expect(revenueFunnelReadinessReport).toContain("Kshudhita/future titles | BLOCKED_PIPELINE_ONLY");

    expect(performanceRevenueReadinessReport).toContain("Performance readiness: GO_MONITOR_WITH_QUICK_WINS");
    expect(performanceRevenueReadinessReport).toContain("`frontend/build` total | 7.7 MB");
    expect(performanceRevenueReadinessReport).toContain("Largest shelf image is 747 KB");
    expect(performanceRevenueReadinessReport).toContain("Performance readiness score: 8.8/10");
    expect(performanceRevenueReadinessReport).not.toMatch(/\b10\/10\b/);

    expect(autoscalingOperationsReadinessReport).toContain("Operations readiness: GO_WITH_OWNER_DASHBOARD_VERIFICATION_REQUIRED");
    expect(autoscalingOperationsReadinessReport).toContain("OWNER_DASHBOARD_VERIFICATION_REQUIRED");
    expect(autoscalingOperationsReadinessReport).toContain("This report does not claim autoscaling is fully verified.");
    expect(autoscalingOperationsReadinessReport).not.toMatch(/\bAUTOSCALING_FULLY_VERIFIED\b|\bAutoscaling verified: YES\b/i);

    expect(readingOnlyRevenueOperationsScorecard).toContain("Overall revenue launch readiness | 9.3/10");
    expect(readingOnlyRevenueOperationsScorecard).toContain("Autoscaling/operations readiness | 8.2/10 | OWNER_DASHBOARD_VERIFICATION_REQUIRED");
    expect(readingOnlyRevenueOperationsScorecard).toContain("Public audio: PUBLIC_AUDIO_RELEASE_BLOCKED");
    expect(readingOnlyRevenueOperationsScorecard).toContain("Audiobook production: PRODUCTION_BLOCKED");
    expect(readingOnlyRevenueOperationsScorecard).not.toMatch(/\b10\/10\b/);
  });

  test("post-launch funnel tracking plan stays first-party, disabled by default, and privacy safe", () => {
    expect(readingLaunchFunnelTrackingPlan).toContain("Tracking approach: first-party, privacy-safe, opt-in");
    expect(readingLaunchFunnelTrackingPlan).toContain("Network delivery is disabled unless `REACT_APP_ENABLE_LAUNCH_ANALYTICS=true`");
    expect(readingLaunchFunnelTrackingPlan).toContain("No third-party pixel was added by this pass.");
    expect(readingLaunchFunnelTrackingPlan).toContain("No PII.");
    expect(readingLaunchFunnelTrackingPlan).toContain("No raw unredacted Razorpay payment IDs");
    expect(readingLaunchFunnelTrackingPlan).toContain("No customer email, phone, payment ID, order ID");
    expect(readingLaunchFunnelTrackingPlan).toContain("No public audio, Listen Now CTA, AudioObject metadata, or audiobook-live claim is introduced.");

    expect(postLaunchFunnelBaselineReport).toContain("Tracking status: OPT_IN_READY");
    expect(postLaunchFunnelBaselineReport).toContain("Events Implemented");
    expect(postLaunchFunnelBaselineReport).toContain("Production conversion summary until opt-in analytics delivery is enabled and reviewed in `/admin/launch-monitor`.");
    expect(postLaunchFunnelBaselineReport).toContain("Operations baseline | OWNER_DASHBOARD_VERIFICATION_REQUIRED");
    expect(postLaunchFunnelBaselineReport).not.toMatch(/\b(customer email|customer phone|card number|UPI ID|invoice number)\s*:/i);
  });

  test("signed-user journey recorder is manual-sign-in, privacy-safe, and launch-guarded", () => {
    expect(packageJson).toContain('"ux:journey-smoke": "EARNALISM_JOURNEY_MODE=smoke node scripts/record_signed_user_journey.mjs"');
    expect(packageJson).toContain('"ux:journey-record": "node scripts/record_signed_user_journey.mjs"');
    expect(packageJson).toContain('"ux:journey-record:local": "EARNALISM_BASE_URL=http://localhost:3000 node scripts/record_signed_user_journey.mjs"');
    expect(packageJson).toContain('"ux:journey-record:prod": "EARNALISM_BASE_URL=https://theearnalism.com node scripts/record_signed_user_journey.mjs"');
    expect(packageJson).toContain('"ux:journey-regression-report": "EARNALISM_JOURNEY_MODE=regression-report node scripts/record_signed_user_journey.mjs"');
    expect(packageJson).toContain('"regression:ci": "npm run ux:journey-smoke && CI=true REGRESSION_MODE=pr npm run regression -- --json --outputFile=regression/results.json"');

    expect(signedUserJourneyRecorder).toContain("Please sign in manually in the opened browser");
    expect(signedUserJourneyRecorder).toContain("Recording starts only after this confirmation");
    expect(signedUserJourneyRecorder).toContain("EARNALISM_JOURNEY_MODE");
    expect(signedUserJourneyRecorder).toContain("EARNALISM_JOURNEY_TEST_STORAGE_STATE");
    expect(signedUserJourneyRecorder).toContain("journey_smoke_report.json");
    expect(signedUserJourneyRecorder).toContain("journey_route_timings.json");
    expect(signedUserJourneyRecorder).toContain("journey_failures.json");
    expect(signedUserJourneyRecorder).toContain("output/ux-journey-regression");
    expect(signedUserJourneyRecorder).toContain("recordVideo");
    expect(signedUserJourneyRecorder).toContain("context.tracing.start");
    expect(signedUserJourneyRecorder).toContain("redactSensitive");
    expect(signedUserJourneyRecorder).toContain("payment_execution_skipped_by_design");
    expect(signedUserJourneyRecorder).toContain("scanPublicAudioFiles");
    expect(signedUserJourneyRecorder).toContain("PUBLIC_AUDIO_RELEASE_BLOCKED");
    expect(signedUserJourneyRecorder).toContain("PRODUCTION_BLOCKED");
    expect(signedUserJourneyRecorder).toContain("output/ux-journey-recordings");
    expect(signedUserJourneyRecorder).toContain("storageState");
    expect(signedUserJourneyRecorder).not.toMatch(/writeFileSync\([^)]*storageState/i);
    expect(signedUserJourneyRecorder).not.toMatch(/checkout\.razorpay\.com|api\.razorpay\.com|method:\s*["']POST["'][\s\S]{0,80}payments/i);
    expect(signedUserJourneyRecorder).not.toMatch(/ELEVENLABS_API_KEY|RAZORPAY_KEY_SECRET|RAZORPAY_WEBHOOK_SECRET/);

    expect(gitignore).toContain("output/ux-journey-recordings/**/*.webm");
    expect(gitignore).toContain("output/ux-journey-recordings/**/*.mp4");
    expect(gitignore).toContain("output/ux-journey-recordings/**/*.zip");
    expect(gitignore).toContain("output/ux-journey-regression/**/*.webm");
    expect(gitignore).toContain("output/ux-journey-regression/**/*.mp4");
    expect(gitignore).toContain("output/ux-journey-regression/**/*.zip");

    const signedUserReports = [
      signedUserRecordingReport,
      signedUserRegressionReport,
      signedUserUxScorecard,
      signedUserUxBacklog,
      signedUserUxBeforeAfter,
    ].join("\n");
    expect(signedUserReports).toContain("TWO_TIER_JOURNEY_QA_READY");
    expect(signedUserReports).toContain("CI-safe smoke");
    expect(signedUserReports).toContain("CI integration: `npm run regression:ci` runs this smoke before the standard regression bundle.");
    expect(signedUserReports).toContain("Owner-Operated Full Video Journey");
    expect(signedUserReports).toContain("latest_smoke_status");
    expect(signedUserReports).toContain("Manual full-video journey is required for major releases");
    expect(signedUserReports).toContain("OWNER_RUN_READY");
    expect(signedUserReports).toContain("OWNER_RECORDING_REQUIRED_BEFORE_FINAL_SCORE");
    expect(signedUserReports).toContain("AWAITING_FIRST_OWNER_RECORDING");
    expect(signedUserReports).toContain("does not ask for a password");
    expect(signedUserReports).toContain("does not write cookies, tokens, or storage state to disk");
    expect(signedUserReports).toContain("Live payment execution: `SKIPPED_BY_DESIGN`");
    expect(signedUserReports).toContain("Public audio: `PUBLIC_AUDIO_RELEASE_BLOCKED`");
    expect(signedUserReports).toContain("Audiobook production: `PRODUCTION_BLOCKED`");
    expect(signedUserReports).toContain("A true 10/10 score is not claimed until the owner-run signed journey is recorded and reviewed.");
    expect(signedUserReports).toContain("Overall signed-user journey | 10/10 only if proven");
    expect(signedUserReports).not.toMatch(/\bGO_PUBLIC_AUDIOBOOK_RELEASE\b/i);
    expect(signedUserReports).not.toMatch(/\bListen Now\b[\s\S]{0,80}\ballowed\b/i);
    expect(signedUserReports).not.toMatch(/\bAudioObject\b[\s\S]{0,80}\benabled\b/i);
  });

  test("payment receipt and invoice docs are evidence-led, redacted, and non-overclaiming", () => {
    const receiptDocs = [
      paymentReceiptAudit,
      samplePaymentReceiptTemplate,
      paymentReceiptEmailPlan,
    ].join("\n");

    expect(paymentReceiptAudit).toContain("OWNER_DASHBOARD_VERIFICATION_REQUIRED");
    expect(paymentReceiptAudit).toContain("Razorpay Orders + Checkout + server verify/webhook + Earnalism wallet ledger");
    expect(paymentReceiptAudit).toContain("Razorpay Invoice API");
    expect(paymentReceiptAudit).toContain("NOT_USED_IN_REPO");
    expect(paymentReceiptAudit).toContain("Earnalism owned email receipt");
    expect(paymentReceiptAudit).toContain("NOT_IMPLEMENTED_IN_REPO");
    expect(paymentReceiptAudit).toContain("GST_TAX_INVOICE_NOT_VERIFIED");
    expect(paymentReceiptAudit).toContain("Email Delivery Verification");
    expect(paymentReceiptAudit).toContain("NOT_VERIFIED");

    expect(samplePaymentReceiptTemplate).toContain("SAMPLE_ONLY_NOT_TAX_INVOICE");
    expect(samplePaymentReceiptTemplate).toContain("This is a payment receipt, not a tax invoice unless explicitly marked as a tax invoice.");
    expect(samplePaymentReceiptTemplate).toContain("RZP-REDACTED-REF");
    expect(samplePaymentReceiptTemplate).toContain("REDACTED_LOW_VALUE_AMOUNT");
    expect(samplePaymentReceiptTemplate).not.toMatch(/\b(?:pay|order|cust)_[A-Za-z0-9]{8,}\b/i);

    expect(paymentReceiptEmailPlan).toContain("PLANNING_ONLY_NO_EMAIL_SENDING_ADDED");
    expect(paymentReceiptEmailPlan).toContain("Razorpay Automated Receipt");
    expect(paymentReceiptEmailPlan).toContain("Razorpay Invoice API");
    expect(paymentReceiptEmailPlan).toContain("Earnalism-Owned Transactional Email Receipt");
    expect(paymentReceiptEmailPlan).toContain("No email sending is implemented by this plan.");

    const forbiddenPatterns = [
      /\brzp_(?:live|test)_[A-Za-z0-9]{8,}\b/i,
      /\b(?:pay|order|cust)_[A-Za-z0-9]{8,}\b/i,
      /\bAuthorization\s*:\s*(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{12,}/i,
      /\bBearer\s+[A-Za-z0-9._~+/=-]{12,}/i,
      /\bsk_[A-Za-z0-9]{16,}\b/i,
      /\b(?:RAZORPAY_KEY_SECRET|RAZORPAY_WEBHOOK_SECRET|WEBHOOK_SECRET|API_KEY|SECRET|TOKEN)\s*[:=]\s*["']?[A-Za-z0-9_./+=-]{8,}/i,
      /\b(?:\d[ -]*?){12,19}\b/,
      /\b(?:UPI ID|VPA|IFSC|bank account|account number)\b/i,
      /\b(?:\+?\d{1,3}[-. ]?)?(?:\(?\d{3}\)?[-. ]?){2}\d{4}\b/,
      /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i,
    ];
    for (const pattern of forbiddenPatterns) {
      expect(receiptDocs).not.toMatch(pattern);
    }
    expect(receiptDocs).not.toMatch(/\b(GST|tax)\s+invoice\s+(is|will be|gets|generated automatically|sent automatically)\b/i);
    expect(receiptDocs).not.toMatch(/\bemail receipt\s+(is|will be|gets|sent automatically)\b/i);
  });

  test("reading-only launch public surfaces reject audio, catalog, accessibility, and ownership overclaims", () => {
    const publicLaunchSources = [
      home,
      library,
      bookDetail,
      pricing,
      login,
      signup,
      account,
      reader,
      header,
      footer,
      firstVisitSiteTour,
      publicIndex,
      staticSnapshotGenerator,
      useSeo,
      controlledLaunch,
      publicationSafety,
    ].join("\n");

    expect(publicLaunchSources).toContain("Dracula");
    expect(publicLaunchSources).toContain("Chapter 1");
    expect(publicLaunchSources).toMatch(/reading time/i);
    expect(publicLaunchSources).toContain("Approved classic reading release");
    expect(publicLaunchSources).not.toContain("Approved Tier A core reading candidate");
    expect(publicLaunchSources).not.toContain("Approved Tier A Core Reading Candidate");
    expect(publicLaunchSources).toContain("audiobook_enabled: false");
    expect(publicLaunchSources).toContain("generate_audiobook: false");
    expect(publicLaunchSources).toContain("Audiobooks appear only after release-gate evidence approves them.");
    expect(publicLaunchSources).not.toMatch(/audiobook experience in private review/i);
    expect(publicLaunchSources).not.toMatch(/\bAudio (is )?not available yet\b/i);
    expect(publicLaunchSources).not.toMatch(/\bDracula audiobook is not available yet\b/i);
    expect(publicLaunchSources).not.toMatch(/\bListen Now\b/i);
    expect(publicLaunchSources).not.toMatch(/\bAudioObject\b/i);
    expect(publicLaunchSources).not.toMatch(/\bDracula audio is (live|available|ready|published)\b/i);
    expect(publicLaunchSources).not.toMatch(/\b(full )?audiobook\s+(is|are)?\s*(live|available|ready|published)\b/i);
    expect(publicLaunchSources).not.toMatch(/\b(buy|purchase|get)\s+(the\s+)?(full\s+)?audiobook\b/i);
    expect(publicLaunchSources).not.toMatch(/\baudiobook pass\b/i);
    expect(publicLaunchSources).not.toMatch(/\b(Kshudhita Pashan|kshudhita-pashan)\b[\s\S]{0,180}\b(Start Reading|Read Preview|Listen Now|public reader|public audio|available now)\b/i);
    expect(publicLaunchSources).not.toMatch(/\b(all|every|100\+|105)\s+(books|classics|titles)\s+(are\s+)?(live|available|readable|ready)\b/i);
    expect(publicLaunchSources).not.toMatch(/\b(WCAG compliant|blind[- ]user tested|fully accessible audiobook|screen-reader certified)\b/i);
    expect(publicLaunchSources).not.toMatch(/\b(buy|own|ownership|forever)\b[\s\S]{0,100}\b(book|classic|edition|Dracula)\b/i);
    expect(renderedPricingSources).toContain("No subscription or autorenewal");
    expect(renderedPricingSources).toContain("Reading time is credited to your wallet after confirmation");
    expect(renderedPricingSources).not.toMatch(/\b(own forever|ownership forever|permanent access|recurring subscription|autorenewing plan|buy audiobook|audiobook pass)\b/i);
  });

  test("reading-only launch keeps public static roots free of audio binaries", () => {
    const audioExtensions = new Set([".mp3", ".wav", ".m4a", ".ogg", ".aac"]);
    const publicRoots = ["frontend/public", "frontend/build"].map((relativePath) => path.join(ROOT, relativePath));
    const audioFiles = [];
    for (const publicRoot of publicRoots) {
      if (!fs.existsSync(publicRoot)) continue;
      const stack = [publicRoot];
      while (stack.length) {
        const current = stack.pop();
        for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
          const absolute = path.join(current, entry.name);
          if (entry.isDirectory()) {
            stack.push(absolute);
          } else if (audioExtensions.has(path.extname(entry.name).toLowerCase())) {
            audioFiles.push(path.relative(ROOT, absolute));
          }
        }
      }
    }
    expect(audioFiles).toEqual([]);
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

  test("audiobook accessibility criteria stay internal, blocked, and evidence-led", () => {
    expect(audiobookReleaseCriteria).toContain("Current status is `PUBLIC_AUDIO_RELEASE_BLOCKED`");
    expect(audiobookReleaseCriteria).toContain("This is an internal release standard");
    expect(audiobookReleaseCriteria).toContain("not a public claim of WCAG compliance");
    expect(audiobookReleaseCriteria).toContain("blind-user testing");
    expect(audiobookReleaseCriteria).toContain("fully accessible audiobook");
    expect(audiobookReleaseCriteria).toContain("Derivative audiobook rights");
    expect(audiobookReleaseCriteria).toContain("model/provider license allows commercial audiobook use");
    expect(audiobookReleaseCriteria).toContain("Text/audio sync");
    expect(audiobookReleaseCriteria).toContain("250 ms");
    expect(audiobookReleaseCriteria).toContain("completed Bengali and English human-review scorecards");
    expect(audiobookReleaseCriteria).toContain("Completed `BENGALI_AUDIOBOOK_HUMAN_REVIEW_SCORECARD.md`");
    expect(audiobookReleaseCriteria).toContain("Completed `ENGLISH_AUDIOBOOK_HUMAN_REVIEW_SCORECARD.md`");
    expect(audiobookReleaseCriteria).toContain("BENGALI_AUDIOBOOK_HUMAN_REVIEW_SCORECARD.md");
    expect(audiobookReleaseCriteria).toContain("ENGLISH_AUDIOBOOK_HUMAN_REVIEW_SCORECARD.md");
    expect(audiobookReleaseCriteria).toContain("Draft PR #44 and Draft PR #45 evidence must not be treated as public audiobook release approval");
    expect(audiobookReleaseCriteria).toContain("No public Kshudhita Pashan or Bengali audiobook release");
    expect(audiobookReleaseCriteria).toContain("No public Listen Now CTA");
  });

  test("narration QA rubric and scorecards keep Bengali and English audiobook bakeoffs in HOLD", () => {
    expect(narrationQaRubric).toContain("Minimum final human-review score: `9.5/10`");
    expect(narrationQaRubric).toContain("Text fidelity: `PASS` required");
    expect(narrationQaRubric).toContain("Derivative audiobook rights: `PASS` required");
    expect(narrationQaRubric).toContain("Draft PR #44 or Draft PR #45 evidence is treated as public release approval");
    expect(narrationQaRubric).toContain("No public claim may say blind-user tested");

    expect(bengaliNarrationScorecard).toContain("Status: `HOLD`");
    expect(bengaliNarrationScorecard).toContain("Bengali pronunciation score");
    expect(bengaliNarrationScorecard).toContain("Rabindranath-era/classic tone handling");
    expect(bengaliNarrationScorecard).toContain("Public release status: `PUBLIC_AUDIO_RELEASE_BLOCKED`");

    expect(englishNarrationScorecard).toContain("Status: `HOLD`");
    expect(englishNarrationScorecard).toContain("Gothic/literary tone score");
    expect(englishNarrationScorecard).toContain("Dracula audio remains disabled publicly");
    expect(englishNarrationScorecard).toContain("Public release status: `PUBLIC_AUDIO_RELEASE_BLOCKED`");

    expect(narrationModelDecisionReport).toContain("PR #44 remains Draft");
    expect(narrationModelDecisionReport).toContain("PR #45 remains Draft");
    expect(narrationModelDecisionReport).toContain("Public release status: `PUBLIC_AUDIO_RELEASE_BLOCKED`");
  });

  test("audiobook legal and accessibility compliance docs keep public audio blocked", () => {
    expect(audiobookLegalComplianceGate).toContain("Status: `PUBLIC_AUDIO_RELEASE_BLOCKED`");
    expect(audiobookLegalComplianceGate).toContain("does not enable audio");
    expect(audiobookLegalComplianceGate).toContain("does not make a legal guarantee");
    expect(audiobookLegalComplianceGate).toContain("Storage/CDN/public serving");
    expect(audiobookLegalComplianceGate).toContain("Refund/support readiness");
    expect(audiobookLegalComplianceGate).toContain("Owner/legal approval");
    expect(audiobookLegalComplianceGate).toContain("PR #44 and PR #45 remain Draft evidence");
    expect(audiobookLegalComplianceGate).toContain("Audio is generated from unapproved source text");
    expect(audiobookLegalComplianceGate).toContain("WCAG compliance");
    expect(audiobookLegalComplianceGate).toContain("blind-user testing");
    expect(audiobookLegalComplianceGate).toContain("screen-reader certification");
    expect(audiobookLegalComplianceGate).toContain("fully accessible audiobook platform");
    expect(audiobookLegalComplianceGate).not.toContain("GO_FOR_PUBLIC_AUDIOBOOK_RELEASE");

    expect(accessibilityClaimsPolicy).toContain("Status: `INTERNAL_POLICY_ONLY`");
    expect(accessibilityClaimsPolicy).toContain("Dracula audio is not available yet");
    expect(accessibilityClaimsPolicy).toContain("audiobooks are live");
    expect(accessibilityClaimsPolicy).toContain("Listen Now");
    expect(accessibilityClaimsPolicy).toContain("WCAG compliant");
    expect(accessibilityClaimsPolicy).toContain("blind-user tested");
    expect(accessibilityClaimsPolicy).toContain("fully accessible");
    expect(accessibilityClaimsPolicy).toContain("No public audiobook is live today");

    expect(audiobookComplianceScorecard).toContain("Status: `PUBLIC_AUDIO_RELEASE_BLOCKED`");
    expect(audiobookComplianceScorecard).toContain("Recommendation: `HOLD_PUBLIC_AUDIO`");
    expect(audiobookComplianceScorecard).toContain("Overall audiobook compliance readiness: `0.0/10`");
    expect(audiobookComplianceScorecard).toContain("Derivative audiobook rights | HOLD");
    expect(audiobookComplianceScorecard).toContain("Storage/CDN/public-serving rights | HOLD");
    expect(audiobookComplianceScorecard).toContain("Refund/support readiness | HOLD");
    expect(audiobookComplianceScorecard).toContain("Owner/legal approval | HOLD");
    expect(audiobookComplianceScorecard).toContain("PR #44/#45 treated only as Draft evidence | PASS");
    expect(audiobookComplianceScorecard).not.toMatch(/\bGO_FOR_PUBLIC_AUDIOBOOK_RELEASE\b/);
  });

  test("accessible audiobook journey does not enable public audio or unsupported claims", () => {
    expect(accessibleAudiobookJourney).toContain("This is an internal journey map");
    expect(accessibleAudiobookJourney).toContain("Dracula audio is disabled");
    expect(accessibleAudiobookJourney).toContain("Kshudhita Pashan remains pipeline-only");
    expect(accessibleAudiobookJourney).toContain("Any sample listening is internal-only");
    expect(accessibleAudiobookJourney).toContain("No Listen Now CTA may appear for unapproved titles");
    expect(accessibleAudiobookJourney).toContain("all controls are buttons or links with useful accessible names");
    expect(accessibleAudiobookJourney).toContain("Manual NVDA, VoiceOver, and TalkBack testing is still required");
  });

  test("audiobook release gate cannot pass without rights, model license, QA, player evidence, owner approval, and rollback", () => {
    expect(packageJson).toContain('"audiobook:release-gate": "python3 scripts/audiobook_accessibility_release_gate.py"');
    expect(audiobookReleaseGate).toContain("PUBLIC_AUDIO_RELEASE_BLOCKED");
    expect(audiobookReleaseGate).toContain("PASS_EXPECTED_BLOCKED");
    expect(audiobookReleaseGate).toContain("FAIL_PUBLIC_AUDIO_LEAK");
    expect(audiobookReleaseGate).toContain("FRONTEND_PUBLIC_AUDIO_ASSETS_PRESENT");
    expect(audiobookReleaseGate).toContain("FRONTEND_BUILD_AUDIO_ASSETS_PRESENT");
    expect(audiobookReleaseGate).toContain("DERIVATIVE_AUDIOBOOK_RIGHTS_MISSING");
    expect(audiobookReleaseGate).toContain("MODEL_COMMERCIAL_USE_PERMISSION_MISSING");
    expect(audiobookReleaseGate).toContain("MODEL_LICENSE_EVIDENCE_MISSING");
    expect(audiobookReleaseGate).toContain("VOICE_NARRATOR_RIGHTS_MISSING");
    expect(audiobookReleaseGate).toContain("VOICE_CLONING_RISK_UNRESOLVED");
    expect(audiobookReleaseGate).toContain("TRANSCRIPT_REQUIRED_MISSING");
    expect(audiobookReleaseGate).toContain("SYNC_TOLERANCE_MISSING");
    expect(audiobookReleaseGate).toContain("REQUIRED_PLAYER_ACCESSIBILITY_EVIDENCE");
    expect(audiobookReleaseGate).toContain("REQUIRED_HUMAN_REVIEW_FIELDS");
    expect(audiobookReleaseGate).toContain("REQUIRED_LEGAL_ACCESSIBILITY_COMPLIANCE_EVIDENCE");
    expect(audiobookReleaseGate).toContain("HUMAN_REVIEW_SCORECARD_MISSING");
    expect(audiobookReleaseGate).toContain("HUMAN_REVIEW_{field.upper()}_MISSING");
    expect(audiobookReleaseGate).toContain("text_fidelity_passed");
    expect(audiobookReleaseGate).toContain("legal_commercial_use_passed");
    expect(audiobookReleaseGate).toContain("AUDIOBOOK_GENERATED_FOR_UNAPPROVED_SOURCE_TEXT");
    expect(audiobookReleaseGate).toContain("STORAGE_CDN_PUBLIC_SERVING_RIGHTS_MISSING");
    expect(audiobookReleaseGate).toContain("ATTRIBUTION_REQUIREMENTS_UNSATISFIED");
    expect(audiobookReleaseGate).toContain("PUBLIC_CLAIMS_EVIDENCE_REVIEW_MISSING");
    expect(audiobookReleaseGate).toContain("PUBLIC_COPY_AUDIOBOOKS_LIVE_CLAIM");
    expect(audiobookReleaseGate).toContain("PUBLIC_COPY_ACCESSIBILITY_OVERCLAIM");
    expect(audiobookReleaseGate).toContain("REFUND_SUPPORT_READINESS_MISSING");
    expect(audiobookReleaseGate).toContain("OWNER_LEGAL_APPROVAL_MISSING");
    expect(audiobookReleaseGate).toContain("ROLLBACK_APPROVAL_MISSING");
    expect(audiobookReleaseGate).toContain("DRAFT_PR_44_EVIDENCE_TREATED_AS_RELEASE_APPROVAL");
    expect(audiobookReleaseGate).toContain("DRAFT_PR_45_EVIDENCE_TREATED_AS_RELEASE_APPROVAL");
    expect(audiobookReleaseGate).toContain("QA_THRESHOLD = 9.5");
    expect(audiobookReleaseGate).toContain("OWNER_APPROVAL_MISSING");
    expect(audiobookReleaseGate).toContain("ROLLBACK_PLAN_MISSING");
    expect(audiobookReleaseGate).toContain("public_audio_publish_allowed");
    expect(audiobookReleaseGate).toContain("False");
  });

  test("current audiobook gate report keeps public release blocked", () => {
    expect(audiobookGateReport).toContain("Status: `PUBLIC_AUDIO_RELEASE_BLOCKED`");
    expect(audiobookGateReport).toContain("Command status: `PASS_EXPECTED_BLOCKED`");
    expect(audiobookGateReport).toContain("Frontend public audio-like asset count");
    expect(audiobookGateReport).toContain("Frontend build audio-like asset count");
    expect(audiobookGateReport).toContain("| Frontend public audio-like asset count | `0` |");
    expect(audiobookGateReport).toContain("| Frontend build audio-like asset count | `0` |");
    expect(audiobookGateReport).toContain("DERIVATIVE_AUDIOBOOK_RIGHTS_MISSING");
    expect(audiobookGateReport).toContain("MODEL_COMMERCIAL_USE_PERMISSION_MISSING");
    expect(audiobookGateReport).toContain("MODEL_LICENSE_EVIDENCE_MISSING");
    expect(audiobookGateReport).toContain("VOICE_NARRATOR_RIGHTS_MISSING");
    expect(audiobookGateReport).toContain("BENGALI_QA_SCORE_MISSING");
    expect(audiobookGateReport).toContain("ENGLISH_QA_SCORE_MISSING");
    expect(audiobookGateReport).toContain("BENGALI_HUMAN_REVIEW_SCORECARD_MISSING");
    expect(audiobookGateReport).toContain("ENGLISH_HUMAN_REVIEW_SCORECARD_MISSING");
    expect(audiobookGateReport).toContain("Bengali human-review scorecard present");
    expect(audiobookGateReport).toContain("English human-review scorecard present");
    expect(audiobookGateReport).toContain("Storage/CDN public-serving rights approved");
    expect(audiobookGateReport).toContain("Attribution requirements satisfied");
    expect(audiobookGateReport).toContain("Public claims evidence reviewed");
    expect(audiobookGateReport).toContain("Refund/support readiness");
    expect(audiobookGateReport).toContain("STORAGE_CDN_PUBLIC_SERVING_RIGHTS_MISSING");
    expect(audiobookGateReport).toContain("ATTRIBUTION_REQUIREMENTS_UNSATISFIED");
    expect(audiobookGateReport).toContain("PUBLIC_CLAIMS_EVIDENCE_REVIEW_MISSING");
    expect(audiobookGateReport).toContain("REFUND_SUPPORT_READINESS_MISSING");
    expect(audiobookGateReport).toContain("OWNER_LEGAL_APPROVAL_MISSING");
    expect(audiobookGateReport).toContain("ROLLBACK_APPROVAL_MISSING");
    expect(audiobookGateReport).toContain("OWNER_APPROVAL_MISSING");
    expect(audiobookGateReport).toContain("ROLLBACK_PLAN_MISSING");
    expect(audiobookGateReport).toContain("Not safe for public audiobook launch");
    expect(audiobookGateReport).not.toContain("GO_FOR_PUBLIC_AUDIOBOOK_RELEASE");
  });

  test("internal audiobook player prototype is feature-flagged and not publicly routed", () => {
    expect(internalAudiobookPrototype).toContain("REACT_APP_ENABLE_INTERNAL_AUDIOBOOK_PLAYER_PROTOTYPE");
    expect(internalAudiobookPrototype).toContain('env?.NODE_ENV !== "production"');
    expect(internalAudiobookPrototype).toContain("InternalAudiobookPlayerPrototype");
    expect(internalAudiobookPrototype).toContain("internal-audiobook-player-prototype");
    expect(internalAudiobookPrototype).toContain("PUBLIC_AUDIO_RELEASE_BLOCKED");
    expect(app).not.toContain("InternalAudiobookPlayerPrototype");
    expect(app).not.toContain("audiobook-player-prototype");
    expect(staticSnapshotGenerator).not.toContain("audiobook-player-prototype");
    expect(frontendPackageJson).toContain('"postbuild": "node scripts/generate-static-seo-snapshots.mjs"');
  });

  test("internal audiobook player prototype uses safe mock metadata and no audio asset", () => {
    expect(internalAudiobookPrototype).toContain("Chapter 1 Preview");
    expect(internalAudiobookPrototype).toContain("Chapter 2 Placeholder");
    expect(internalAudiobookPrototype).toContain("Safe mock metadata only");
    expect(internalAudiobookPrototype).not.toMatch(/<audio\b/i);
    expect(internalAudiobookPrototype).not.toMatch(/\bsrc\s*=/i);
    expect(internalAudiobookPrototype).not.toMatch(/https?:\/\//i);
    expect(internalAudiobookPrototype).not.toMatch(/\/audio\//i);
    expect(internalAudiobookPrototype).not.toMatch(/cloudinary|backblaze|b2|provider audio path/i);
    expect(internalAudiobookPrototype).not.toMatch(/\bListen Now\b/i);
  });

  test("internal audiobook player prototype has nonvisual control semantics without unsupported claims", () => {
    for (const token of [
      "Play internal audiobook prototype",
      "Pause internal audiobook prototype",
      "Rewind prototype by 10 seconds",
      "Forward prototype by 30 seconds",
      "Prototype playback speed",
      "Prototype sleep timer",
      "Bookmark prototype position",
      "role=\"progressbar\"",
      "aria-live=\"polite\"",
      "role=\"alert\"",
      "aria-current",
      "aria-expanded",
    ]) {
      expect(internalAudiobookPrototype).toContain(token);
    }
    expect(internalAudiobookPrototype).not.toMatch(/\bWCAG compliant\b/i);
    expect(internalAudiobookPrototype).not.toMatch(/\bblind[- ]user tested\b/i);
    expect(internalAudiobookPrototype).not.toMatch(/\bfully accessible audiobook\b/i);
    expect(accessibleAudiobookPrototypeReport).toContain("Internal-only");
    expect(accessibleAudiobookPrototypeReport).toContain("No public route was added");
    expect(accessibleAudiobookPrototypeReport).toContain("No real audio URL");
  });

  test("first-batch rights evidence keeps every non-Dracula item held", () => {
    expect(firstBatchScorecard).toContain("Dracula is the only approved public core reading release today.");
    expect(firstBatchScorecard).toContain("GO_DRACULA_CORE_READING_ONLY");
    expect(firstBatchScorecard).toContain("Kshudhita Pashan remains pipeline-only.");
    expect(firstBatchScorecard).toContain("Audiobook derivative rights are not approved for any item");
    expect(firstBatchScorecard).toContain("Public audio remains blocked.");
    expect(firstBatchScorecard).toContain("internal/audio_quarantine/frontend-public-audio/");
    expect(firstBatchScorecard).toContain("Audio-like files must not exist under `frontend/public` or `frontend/build`");
    expect(firstBatchScorecard).toContain("Controlled-publication precheck now blocks if audio-like files exist");
    expect(firstBatchScorecard).toContain("HOLD_PIPELINE_ONLY");
    expect(firstBatchScorecard).toContain("HOLD_SOURCE_RIGHTS_QA_REQUIRED");
    expect(firstBatchScorecard).toContain("UNKNOWN_COMMERCIAL_USE");
    expect(firstBatchScorecard).toContain("UNKNOWN_DERIVATIVE_RIGHTS");
    expect(firstBatchScorecard).toContain("OWNER_APPROVAL_REQUIRED");

    for (const blockedTitle of [
      "Anandamath Visual Study Companion",
      "Devdas Study Edition",
      "Abol Tabol Illustrated Reader",
      "Sultana's Dream Feminist Sci-Fi Edition",
      "Sherlock Holmes Logic Workbook",
      "Dracula Gothic Fiction Visual Guide",
      "Frankenstein Science & Ethics Guide",
      "Tagore Short Stories for Young Readers",
      "Calculus Made Easy Visual Guide",
      "Chander Pahar Adventure Companion",
    ]) {
      const scorecardRow = firstBatchScorecard.split("\n").find((line) => line.includes(`| ${blockedTitle} |`));
      expect(scorecardRow).toContain("| not public/live |");
      expect(scorecardRow).toContain("| no | no | OWNER_APPROVAL_REQUIRED | HOLD_SOURCE_RIGHTS_QA_REQUIRED |");
    }
  });

  test("approval and source backfill templates require provenance, commercial-use, and audio-derivative evidence", () => {
    for (const requiredToken of [
      "Source License URL",
      "Commercial Use Status",
      "Attribution Requirement",
      "Derivative Audiobook Rights Status",
      "Public Metadata Allowed",
      "Public CTA Allowed",
      "Owner Approval Status",
      "GO/HOLD Decision",
    ]) {
      expect(approvedToPublish).toContain(requiredToken);
    }
    expect(approvedToPublish).toContain("Derivative Audiobook Rights Status: not approved; separate approval required; AUDIO_NOT_REQUIRED for core reading");
    expect(firstBatchMatrixCsv).toContain("source_license_url,commercial_use_status");
    expect(firstBatchMatrixCsv).toContain("UNKNOWN_DERIVATIVE_RIGHTS");
    expect(firstBatchMatrixCsv).toContain("public_metadata_allowed,public_cta_allowed,owner_approval_status,go_hold_decision");
    expect(firstBatchBackfillTemplate).toContain('"source_license_url"');
    expect(firstBatchBackfillTemplate).toContain('"commercial_use_status"');
    expect(firstBatchBackfillTemplate).toContain('"derivative_audiobook_rights_status"');
    expect(firstBatchBackfillTemplate).toContain('"public_cta_allowed"');
    expect(controlledPublicationPrecheck).toContain("find_public_audio_like_files");
    expect(controlledPublicationPrecheck).toContain("public/build audio-like assets must be quarantined");
    expect(controlledPublicationPrecheck).toContain("frontend/public");
    expect(controlledPublicationPrecheck).toContain("frontend/build");
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
    expect(alwaysVisibleLaunchCopy).not.toMatch(/\b(Buy book forever|own this book forever|recurring subscription|autorenewing plan)\b/i);
    expect(alwaysVisibleLaunchCopy).not.toMatch(/\b(cart|WooCommerce|self-publishing marketplace|fashion collection)\b/i);
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
    expect(publicIndex).toContain("A premium reading and listening sanctuary for timeless Bengali and English classics.");
    expect(publicIndex).not.toMatch(/beginning with Dracula by Bram Stoker|Dracula-first/i);
  });

  test("book card truth gate prevents unapproved reader CTAs", () => {
    expect(bookCard).toContain("canShowPreview");
    expect(bookCard).toContain("canShowStartReading");
    expect(bookCard).toContain("canShowReadingPass");
    expect(controlledLaunch).toContain("isLiveApprovedBook");
    expect(controlledLaunch).toContain("isPipelineCandidate");
    expect(controlledLaunch).toContain("canShowAudioCTA");
    expect(controlledLaunch).toContain("BATCH_1_READER_ONLY_SLUGS");
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
    expect(bookCard).toContain("Request Update");
    expect(bookCard).toContain("This title is in the rights-safe pipeline and is not readable or listenable yet.");
    expect(bookCard).toContain("book.title_en || book.title");
    expect(bookCard).toContain("book-card__secondary-title");
    expect(bookCard).toContain("isLiveApproved ? `/book/${book.slug}` : notifyUrl(book.slug)");
    expect(bookCard).toContain("showReadingPass &&");
    expect(bookCard).toContain("card-details-${book.slug}");
  });

  test("reader route does not borrow admin session for normal Dracula reading", () => {
    const chapterAuthBlock = extractBetween(
      reader,
      "function getChapterAuthHeaders()",
      "function getCurrentReaderPath()"
    );
    expect(chapterAuthBlock).toContain("localStorage.getItem(USER_TOKEN_KEY)");
    expect(chapterAuthBlock).not.toContain("localStorage.getItem(TOKEN_KEY)");
    expect(chapterAuthBlock).not.toContain("localStorage.getItem('token')");

    const bookFetchBlock = extractBetween(
      reader,
      "async function fetchReaderBook",
      "function readerSearchParams"
    );
    expect(bookFetchBlock).toContain("requestedAdminPreview && adminToken");
    expect(bookFetchBlock).toContain("readerManifestPath(bookId");
    expect(bookFetchBlock).toContain("adminPreview: Boolean(requestedAdminPreview && adminToken)");
    expect(bookFetchBlock).not.toContain("err.response?.status === 404 && adminToken");

    const chapterFetchBlock = extractBetween(
      reader,
      "async function fetchReaderChapter",
      "function ReaderChapterIndex"
    );
    expect(chapterFetchBlock).toContain("adminPreview ? localStorage.getItem(TOKEN_KEY) : localStorage.getItem(USER_TOKEN_KEY)");
    expect(chapterFetchBlock).toContain("params.set('preview', 'admin')");
    expect(chapterFetchBlock).toContain("adminPreview ? getAdminAuthHeaders() : getChapterAuthHeaders()");
  });

  test("Dracula chapter titles render clean display text without continuation junk", () => {
    expect(controlledLaunch).toContain("export function normalizeChapterDisplayTitle");
    expect(controlledLaunch).toContain(".replace(/\\s*[.:]?\\s*(?:--|—|-)\\s*continued");
    expect(controlledLaunch).toContain("smartTitleCaseSegment(remainder)");
    expect(reader).toContain("normalizeChapterDisplayTitle(item.title)");
    expect(reader).toContain("normalizeChapterDisplayTitle(chapter.title)");
    expect(bookDetail).toContain("normalizeChapterDisplayTitle(c.title)");
  });

  test("Bengali Gothic candidate is pipeline-only and not a live reading CTA", () => {
    expect(home).toContain('data-testid="bengali-gothic-pipeline-shelf"');
    expect(home).toContain("<ShelfTwoSlideshow books={shelfTwoBooks} />");
    expect(home).toContain("Coming Through the Rights-Safe Pipeline");
    expect(shelfTwoSlideshow).toContain("Request Update");
    expect(shelfTwoSlideshow).toContain("/contact?interest=");
    expect(home).not.toContain("kshudhita-cover-placeholder__title");
    expect(controlledLaunch).toContain('KSHUDHITA_PASHAN_FRONT_COVER_IMAGE = "/assets/books/kshudhita-pashan/kshudhita-pashan-front.webp"');
    expect(controlledLaunch).toContain('KSHUDHITA_PASHAN_BACK_COVER_IMAGE = "/assets/books/kshudhita-pashan/kshudhita-pashan-back.webp"');
    expect(controlledLaunch).toContain('cover_image_url: "/assets/books/kshudhita-pashan/front-cover.webp"');
    expect(controlledLaunch).toContain('cover_image_url: "/assets/books/sherlock-holmes/front-cover.webp"');
    expect(controlledLaunch).toContain('cover_status: "DESIGNED_PLACEHOLDER_NO_SAFE_LOCAL_COVER"');
    expect(fs.existsSync(path.join(ROOT, "frontend/public/assets/books/kshudhita-pashan/kshudhita-pashan-front.webp"))).toBe(true);
    expect(fs.existsSync(path.join(ROOT, "frontend/public/assets/books/kshudhita-pashan/kshudhita-pashan-back.webp"))).toBe(true);
    expect(fs.existsSync(path.join(ROOT, "frontend/public/assets/books/kshudhita-pashan/front-cover.webp"))).toBe(true);
    expect(fs.existsSync(path.join(ROOT, "frontend/public/assets/books/sherlock-holmes/front-cover.webp"))).toBe(true);
    expect(controlledLaunch).toContain('title_en: "The Hungry Stones"');
    expect(controlledLaunch).toContain("A Bengali Gothic candidate in rights-safe preparation.");
    expect(library).toContain('data-testid="library-bengali-gothic-pipeline"');
    expect(library).toContain('data-testid="library-kshudhita-cover-evidence"');
    expect(library).toContain("KSHUDHITA_PASHAN_PIPELINE.frontCoverImage");
    expect(library).toContain("KSHUDHITA_PASHAN_PIPELINE.backCoverImage");
    expect(library).toContain("The Hungry Stones is visible, not open.");
    expect(library).toContain("Bengali title:");
    expect(library).toContain("KSHUDHITA_PASHAN_PIPELINE.subcopy");
    expect(library).toContain("No reader, payment, or audio CTA is available for this pipeline-only title.");

    const homePipelineBlock = extractBetween(home, 'className="reference-pipeline-shelf"', 'data-testid="reading-time-library-path"');
    expect(homePipelineBlock).toContain('data-testid="bengali-gothic-pipeline-shelf"');
    expect(homePipelineBlock).toContain("ShelfTwoSlideshow");
    const libraryPipelineBlock = extractBetween(
      library,
      'data-testid="library-bengali-gothic-pipeline"',
      'data-testid="category-filters"'
    );

    expect(shelfTwoSlideshow).not.toContain("Notify Me");
    expect(libraryPipelineBlock).toContain("Request Update");
    expect(libraryPipelineBlock).not.toContain("Notify Me");

    for (const block of [homePipelineBlock, libraryPipelineBlock]) {
      expect(block).not.toContain("Start Reading");
      expect(block).not.toContain("Read Preview");
      expect(block).not.toContain("Listen Now");
      expect(block).not.toContain("Full Audiobook");
      expect(block).not.toContain("Voice Sample Soon");
      expect(block).not.toContain("Follow Audio QA");
    }
  });

  test("regenerated Bengali audiobook workflow remains internal and release-blocked", () => {
    expect(packageJson).toContain("audiobook:regen:plan");
    expect(packageJson).toContain("audiobook:regen:precheck");
    expect(packageJson).toContain("audiobook:regen:approve-dry-run");
    expect(packageJson).toContain("audiobook:regen:generate-manifest");
    expect(packageJson).toContain("audiobook:release-gate");
    expect(packageJson).toContain("audiobook:regen:release-gate");
    expect(audiobookRegenerationWorkflow).toContain("No voice generation command exists");
    expect(audiobookRegenerationWorkflow).toContain("audio_urls_included");
    expect(audiobookRegenerationWorkflow).toContain("APPROVAL_REQUIRED");
    expect(audiobookRegenerationReleaseGate).toContain("BLOCKED_PUBLIC_AUDIO_RELEASE");
    expect(audiobookRegenerationReleaseGate).toContain("Full audiobook release is disabled by default");
    expect(audiobookGovernanceReport).toContain("OWNER_APPROVAL_REQUIRED");
    expect(audiobookGovernanceReport).toContain("PUBLIC_AUDIO_RELEASE_BLOCKED");
    expect(audiobookDisclosurePolicy).toContain("If AI-generated or AI-assisted, do not claim human narration");
    expect(audiobookDisclosurePolicy).toContain("No AI touch");
    expect(controlledLaunch).toContain("audiobook_enabled: false");
    expect(controlledLaunch).toContain("audio_preview_status: \"AUDIO_PREVIEW_BLOCKED_UNTIL_PROVIDER_QA\"");
  });

  test("future pipeline books do not show live CTAs", () => {
    const pipelineBlock = extractBetween(
      home,
      'className="reference-pipeline-shelf"',
      'data-testid="reading-time-library-path"'
    );
    expect(pipelineBlock).toContain("ShelfTwoSlideshow");
    expect(shelfTwoSlideshow).toContain("Request Update");
    expect(shelfTwoSlideshow).toContain("/contact?interest=");
    expect(pipelineBlock).not.toContain("Notify Me");
    expect(pipelineBlock).not.toContain("Start Reading");
    expect(pipelineBlock).not.toContain("Read Preview");
    expect(pipelineBlock).not.toContain("Listen Now");
  });

  test("owner launch monitor analytics events are mock-safe and allowlisted", () => {
    const analytics = read("frontend/src/lib/funnelAnalytics.js");
    const launchAudit = read("scripts/launch_readiness_audit.py");

    [
      "homepage_view",
      "first_time_site_tour_shown",
      "first_time_site_tour_completed",
      "first_time_site_tour_skipped",
      "hero_read_chapter_free_click",
      "dracula_book_page_view",
      "start_dracula_click",
      "reader_opened",
      "reader_locked_state",
      "reader_low_balance_state",
      "pricing_page_view",
      "reading_pack_selected",
      "checkout_started",
      "payment_success_return",
      "payment_failed_or_cancelled",
      "wallet_credited_visible",
      "continue_reading_click",
      "return_resume_reading_click",
      "core_web_vital",
    ].forEach((event) => {
      expect(analytics).toContain(event);
      expect(launchAudit).toContain(event);
    });
  });

  test("reading launch funnel tracking is first-party, opt-in, and PII-safe", () => {
    [
      "homepage_view",
      "first_time_site_tour_shown",
      "first_time_site_tour_completed",
      "first_time_site_tour_skipped",
      "reader_opened",
      "reader_locked_state",
      "reader_low_balance_state",
      "reading_pack_selected",
      "checkout_started",
      "payment_failed_or_cancelled",
      "wallet_credited_visible",
      "return_resume_reading_click",
    ].forEach((event) => {
      expect(analytics).toContain(event);
      expect(launchAudit).toContain(event);
    });

    expect(analytics).toContain("analyticsNetworkEnabled");
    expect(analytics).toContain("REACT_APP_ENABLE_LAUNCH_ANALYTICS");
    expect(analytics).toContain("__EARNALISM_ENABLE_FUNNEL_ANALYTICS__");
    expect(analytics).toContain("isUnsafeAnalyticsValue");
    expect(analytics).toContain("customer_email");
    expect(analytics).toContain("razorpay_order_id");
    expect(analytics).toContain("razorpay_payment_id");
    expect(analytics).toContain("webhook_secret");
    expect(analytics).toContain("api_key");
    expect(analytics).toContain("upi");
    expect(analytics).toContain("bank");
    expect(analytics).not.toMatch(/google-analytics|gtag|facebook pixel|fbq\(|hotjar|mixpanel|segment/i);
    const trackedPayloadSnippets = [home, firstVisitSiteTour, bookDetail, reader, pricing, account]
      .map(trackFunnelEventSnippets)
      .join("\n");
    expect(trackedPayloadSnippets).not.toMatch(/razorpay_signature|razorpay_payment_id|razorpay_order_id|customer_email|customer_phone|email|phone|upi|card|bank/i);
  });

  test("owner launch monitor dashboard is admin-only and aggregate-safe", () => {
    expect(app).toContain('path="/admin/launch-monitor"');
    expect(app).toContain('<Admin initialTab="launch-monitor" />');
    expect(adminPage).toContain("launch-monitor");
    expect(adminPage).toContain("/admin/launch-monitor/summary");
    expect(adminPage).toContain("OWNER_ADMIN_ONLY");
    expect(adminPage).toContain("PUBLIC_AUDIO_RELEASE_BLOCKED");
    expect(adminPage).toContain("PRODUCTION_BLOCKED");
    expect(adminPage).toContain("No PII, payment ids, customer ids, or third-party pixels.");
    expect(backend).toContain('@api.get("/admin/launch-monitor/summary")');
    expect(backend).toContain("Depends(require_admin)");
    expect(backend).toContain("build_launch_monitor_summary");
    expect(postDeployReadingCanary).toContain("PRODUCTION_API_BASE_URL");
    expect(postDeployReadingCanary).toContain("/api/admin/launch-monitor/summary");
    expect(postDeployReadingCanary).toContain("Expected unauthenticated admin summary to return 401 or 403");
    expect(productionReadingOnlyDeployRunbook).toContain("/admin/launch-monitor` in a fresh incognito/non-admin browser session redirects to or blocks behind `/admin/login`");
    expect(productionReadingOnlyDeployRunbook).toContain("unauthenticated `GET /api/admin/launch-monitor/summary` returns `401` or `403`");
    expect(postDeployReadingOnlyCanaryReport).toContain("/admin/launch-monitor` non-admin browser check");
    expect(launchMonitoringDashboardReport).toContain("Required post-deploy API canary: unauthenticated `GET /api/admin/launch-monitor/summary` must return `401` or `403`");
    const launchMonitorEndpoint = extractBetween(
      backend,
      '@api.get("/admin/launch-monitor/summary")',
      '@api.post("/admin/payments/intents/{intent_id}/reconcile")'
    );
    expect(launchMonitorEndpoint).not.toMatch(/user_email|razorpay_payment_id|razorpay_order_id|customer_email|customer_phone/i);
  });

  test("first-time site tour is mounted, forceable, dismissible, keyboard-aware, and premium-copy safe", () => {
    expect(layout).toContain("<FirstVisitSiteTour />");
    expect(firstVisitSiteTour).toContain('params.get("tour") === "1"');
    expect(firstVisitSiteTour).toContain("if (alreadySeen && !forcedTour) return undefined");
    expect(firstVisitSiteTour).toContain('window.localStorage.setItem(STORAGE_KEY, "complete")');
    expect(firstVisitSiteTour).toContain('data-testid="first-visit-site-tour"');
    expect(firstVisitSiteTour).toContain('aria-modal="true"');
    expect(firstVisitSiteTour).toContain('event.key === "Escape"');
    expect(firstVisitSiteTour).toContain('event.key !== "Tab"');
    expect(firstVisitSiteTour).toContain('first_time_site_tour_shown');
    expect(firstVisitSiteTour).toContain('first_time_site_tour_completed');
    expect(firstVisitSiteTour).toContain('first_time_site_tour_skipped');
    expect(firstVisitSiteTour).toContain("audiobook controls stay hidden until endpoint, sync, QA, and browser gates pass");
    expect(firstVisitSiteTour).not.toMatch(/\bAudio (is )?not available yet\b/i);
    expect(firstVisitSiteTour).not.toMatch(/\bListen Now\b|\bAudioObject\b/i);
  });

  test("pricing page has checkout CTA, payment trust copy, and support/refund copy", () => {
    expect(pricing).toContain("Buy reading time");
    expect(pricing).toContain("Secure payment by Razorpay");
    expect(pricing).toContain("No subscription or autorenewal");
    expect(pricing).toContain("Reading time is credited to your wallet after confirmation");
    expect(pricing).toMatch(/support or refund questions/i);
    expect(pricing).toContain('data-testid={`pack-${p.id}-buy`}');
  });

  test("pricing packs keep approved premium reading-time labels and notes", () => {
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
    expect(pricing).toContain("Start with a free preview");
    expect(pricing).toContain("When you are ready to continue a reader-ready classic, add reading time to your wallet");
    expect(pricing).toContain("Earnalism is a digital reading room");
    expect(pricing).toContain("You buy quiet reading time, not a noisy subscription");
    expect(pricing).toContain('data-testid="dracula-continue-from-pricing"');
    expect(pricing).toContain('data-testid="pricing-wallet-explainer"');
    expect(pricing).toContain("Time goes to your wallet");
    expect(pricing).toContain("not a recurring plan, book ownership claim, or autorenewal product");
    expect(pricing).toContain('data-testid="pricing-trust-copy"');
  });

  test("login signup account and default SEO explain continuation without overclaiming", () => {
    expect(login).toContain('data-testid="login-continuation-note"');
    expect(login).toContain("Sign in after choosing a reading pass to return to the reading-time page");
    expect(signup).toContain('data-testid="signup-wallet-note"');
    expect(signup).toContain("Chapter 1 is free. Reading time is added only when you choose a pass");
    expect(account).toContain('data-testid="account-wallet-explainer"');
    expect(account).toContain("Use this wallet to continue Dracula after the free preview.");
    expect(account).toContain("Open Dracula Shelf");
    expect(reader).toContain('data-testid="reader-locked-wallet-note"');
    expect(reader).toContain("Other chapters require sign-in and reading time from your wallet.");
    expect(useSeo).toContain("A calm Bengali and English digital library");
  });

  test("pricing page tracks approved revenue funnel events without render-only noise", () => {
    for (const event of [
      "pricing_page_view",
      "reading_pack_selected",
      "checkout_started",
      "payment_success_return",
      "payment_failed_or_cancelled",
      "wallet_credited_visible",
      "continue_reading_click",
    ]) {
      expect(pricing).toContain(event);
      expect(analytics).toContain(event);
      expect(launchAudit).toContain(event);
    }
    expect(pricing).not.toMatch(/trackFunnelEvent\("pricing_view"/);
    expect(pricing).not.toMatch(/trackFunnelEvent\("checkout_start"/);
    expect(pricing).not.toMatch(/trackFunnelEvent\("payment_success"/);
    expect(pricing).not.toMatch(/trackFunnelEvent\("wallet_credited"/);
    expect(pricing).not.toContain("pricing_pack_view");
    expect(pricing).not.toContain("reading_time_explainer_view");
    expect(analytics).not.toContain("pricing_pack_view");
    expect(analytics).not.toContain("reading_time_explainer_view");
  });

  test("mobile navigation keeps a visible library CTA", () => {
    expect(header).toContain('import BrandHeaderLogo from "./BrandHeaderLogo";');
    expect(header).toContain('className="header-brand-cluster"');
    expect(header).toContain('<BrandHeaderLogo badgeVariant="tricolor" />');
    expect(header).toContain('data-testid="brand-logo"');
    expect(header).toContain('data-testid="mobile-cta-library"');
    expect(header).toContain("Start Reading");
    expect(header).toContain("aria-expanded={open}");
    expect(header).toContain('aria-controls="mobile-menu"');
    expect(header).toContain('id="mobile-menu"');
    expect(header).toContain("Bengali Classics");
    expect(header).toContain("English Classics");
    expect(styles).toContain(".header-brand-cluster");
    expect(styles).toContain(".glass-header");
    expect(styles).toContain("rgba(255, 252, 244, 0.98)");
    expect(styles).toContain("rgba(249, 244, 234, 0.94)");
    expect(styles).toContain(".brand-header-logo");
    expect(styles).toContain(".brand-header-logo__badge--tricolor");
    expect(styles).toContain("@media (max-width: 1279px)");
  });

  test("non-visual journey has skip link, focus indicators, and spoken loading states", () => {
    expect(layout).toContain('href="#main-content"');
    expect(layout).toContain('className="skip-link"');
    expect(layout).toContain('id="main-content"');
    expect(layout).toContain("tabIndex={-1}");
    expect(app).toContain('role="status"');
    expect(app).toContain("Loading The Earnalism reading room.");
    expect(styles).toContain(".sr-only");
    expect(styles).toContain(".skip-link:focus-visible");
    expect(styles).toContain("a:focus-visible");
    expect(styles).toContain("button:focus-visible");
    expect(styles).toContain("input:focus-visible");
  });

  test("public forms and search controls expose accessible labels and descriptions", () => {
    expect(home).toContain('aria-describedby="newsletter-description"');
    expect(home).toContain("<span className=\"sr-only\">Your name</span>");
    expect(home).toContain("<span className=\"sr-only\">Your email</span>");
    expect(library).toContain("Search title, author, language, or status");
    expect(library).toContain('aria-label="Search title, author, language, or status"');
    expect(login).toContain('aria-describedby="login-continuation-help"');
    expect(signup).toContain('aria-describedby="signup-wallet-help"');
    expect(contact).toContain("<span className=\"overline block mb-2\">Your name</span>");
    expect(contact).toContain("<span className=\"overline block mb-2\">Your email</span>");
    expect(contact).toContain("<span className=\"overline block mb-2\">Your message</span>");
  });

  test("reader locked and wallet states are announced without enabling public audio", () => {
    expect(reader).toContain('data-testid="reader-locked-state"');
    expect(reader).toContain('role="status"');
    expect(reader).toContain('aria-live="polite"');
    expect(reader).toContain('data-testid="reading-time-dialog"');
    expect(reader).toContain('role="dialog"');
    expect(reader).toContain('aria-modal="true"');
    expect(reader).toContain('aria-labelledby="reading-time-dialog-title"');
    expect(reader).toContain('aria-describedby="reading-time-dialog-description"');
    expect(reader).toContain('aria-pressed={selected}');
    expect(reader).toContain("Select ${pack.label || `${pack.minutes} minute`} reading-time pack");
    expect(reader).toContain("Reading edition available.");
    expect(reader).toContain("Audio will appear only after narration, sync, and browser gates pass.");
    expect(reader).not.toMatch(/\bListen Now\b/);
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
    expect(brandSiteTour).toContain("PLAYWRIGHT_RESULTS");
    expect(brandSiteTour).toContain("playwright_video_entries");
    expect(brandSiteTour).toContain("earnalism-site-tour-master.webm");
    expect(brandSiteTour).toContain("earnalism-site-tour-master.mp4");
    expect(brandSiteTour).toContain("earnalism-site-tour-vertical-9x16.mp4");
    expect(brandSiteTour).toContain("earnalism-site-tour-square-1x1.mp4");
    expect(brandSiteTour).toContain("earnalism-site-tour-short-15s.mp4");
    expect(brandSiteTour).toContain("earnalism-site-tour-captions.srt");
    expect(brandSiteTour).toContain("OPERATOR_REQUIRED_OVERLAY_EXPORT");
    expect(brandSiteTour).toContain("caption_mismatch_blocker");
    expect(brandSiteTour).toContain("sha256_file");
    expect(brandSiteTour).toContain("duration_seconds");
    expect(brandSiteTour).toContain("scorecard(index)");
    expect(brandSiteTour).toContain("source_index_path");
    expect(brandSiteTour).toContain("captions_missing_or_mismatched_max_8");
    expect(brandSiteTour).toContain("caption_track_sidecar_only_max_8_6");
    expect(brandSiteTour).toContain("backend_catalog_truth_missing_or_failing_max_8_8");
    expect(brandSiteTour).toContain("ux_go_no_go_missing_or_failing_max_8_8");
    expect(brandSiteTour).toContain("release_post_production_canary_status");
    expect(brandSiteTour).toContain("HOLD_ADS_PENDING_HUMAN_VIDEO_REVIEW");
    expect(brandSiteTour).toContain("dracula_only_live");
    expect(brandSiteTour).toContain("kshudhita_pipeline_only");
    expect(brandSiteTour).toContain("paid_provider_apis_not_called");

    [
      "The Earnalism Digital Library",
      "Step into the classics",
      "Chapter 1 is free",
      "27 chapters prepared for focused reading",
      "Audio is intentionally disabled until QA passes",
      "Bengali Gothic is moving through the rights-safe pipeline",
      "Choose reading time, not noisy subscriptions",
      "Return to reading",
    ].forEach((requiredOverlay) => {
      expect(brandSiteTour).toContain(requiredOverlay);
      expect(siteTourIndex).toContain(requiredOverlay);
    });

    expect(siteTourVoiceover).toContain("Status: SCRIPT_ONLY");
    expect(siteTourVoiceover).toContain("No AI voice, TTS, audiobook generation");
    expect(siteTourFeatureReport).toContain("Audiobook availability claim: blocked");
    expect(siteTourFeatureReport).toContain("Broad live catalog claim: blocked");
    expect(siteTourScorecard).toContain("HOLD_ADS_PENDING_HUMAN_VIDEO_REVIEW");
    expect(siteTourScorecard).toContain("No fake testimonials");
    expect(siteTourIndex).toContain("Brand Site-Tour Video Index");
    expect(siteTourIndex).toContain("SHA256");
    expect(siteTourIndex).toContain("Duration");
    expect(siteTourHumanReview).toContain("approved_for_paid_ads = false");
  });

  test("premium site-tour package caps ad readiness unless evidence is complete", () => {
    expect(siteTourScorecardJson.recommendation).not.toBe("GO_FOR_BRANDING_AND_ADVERTISEMENT");
    expect(siteTourScorecardJson.truth_constraints.ai_voice_or_tts_not_generated).toBe(true);
    expect(siteTourScorecardJson.truth_constraints.audiobook_claims_blocked).toBe(true);
    expect(siteTourScorecardJson.truth_constraints.fake_reviews_or_social_proof_blocked).toBe(true);
    expect(siteTourScorecardJson.human_owner_review_approved).toBe(false);
    expect(siteTourScorecardJson.caps_applied.overlay_status_not_pass_max_8).toBe(false);
    expect(siteTourScorecardJson.caps_applied.captions_missing_or_mismatched_max_8).toBe(false);
    expect(siteTourScorecardJson.caps_applied.caption_track_sidecar_only_max_8_6).toBe(false);
    expect(siteTourScorecardJson.caps_applied.required_artifacts_missing_max_8).toBe(false);
    expect(siteTourScorecardJson.caps_applied.artifact_checksums_missing_max_8_2).toBe(false);
    expect(siteTourScorecardJson.caps_applied.human_owner_review_missing_max_9).toBe(true);
    expect(siteTourScorecardJson.caps_applied.backend_catalog_truth_missing_or_failing_max_8_8).toBe(false);
    expect(siteTourScorecardJson.caps_applied.ux_go_no_go_missing_or_failing_max_8_8).toBe(false);
    expect(siteTourScorecardJson.video_status.overlay_status).toBe("PASS");
    expect(siteTourScorecardJson.video_status.edited_master_video_exists).toBe(true);
    expect(siteTourScorecardJson.video_status.overlay_strategy).toBe("png_overlay_burn_in");
    expect(siteTourScorecardJson.video_status.overlay_image_count).toBe(siteTourIndexJson.selected_clip_names.length);
    expect(siteTourScorecardJson.source_index_path).toBe("BRAND_SITE_TOUR_VIDEO_INDEX.json");
    expect(siteTourScorecardJson.selected_clip_count).toBe(siteTourIndexJson.selected_clip_names.length);
    expect(siteTourScorecardJson.overall_score).toBeLessThanOrEqual(9);
    expect(siteTourScorecardJson.overall_score).toBeLessThan(9.7);
    expect(siteTourIndexJson.final_recommendation).toBe("HOLD_ADS_PENDING_HUMAN_VIDEO_REVIEW");
    expect(siteTourIndexJson.caption_mismatch_blocker).toBe(false);
    expect(siteTourIndexJson.artifacts.master_webm.sha256).toMatch(/^[a-f0-9]{64}$/);
    expect(siteTourIndexJson.artifacts.master_mp4.sha256).toMatch(/^[a-f0-9]{64}$/);
    expect(siteTourIndexJson.artifacts.master_webm.duration_seconds).toBeGreaterThan(0);
    expect(siteTourIndexJson.canary_stamp.backend_catalog_truth_status).toBe("PASS");
    expect(siteTourIndexJson.canary_stamp.live_api_dracula_audiobook_status).toBe(404);
    expect(brandSiteTour).toContain('recommendation = "HOLD_ADS_PENDING_HUMAN_VIDEO_REVIEW"');
    expect(brandSiteTour).toContain('owner_approved');
    expect(brandSiteTour).toContain('release_ok');
    expect(brandSiteTour).toContain('seo_social_ok');
    expect(siteTourFeatureReport).not.toMatch(/audiobook available|listen now|full audiobook/i);
    expect(siteTourFeatureReport).not.toMatch(/testimonials available|rated by readers|trusted by thousands/i);
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
      expect(staticSnapshotGenerator).toContain("A premium reading and listening sanctuary for timeless Bengali and English classics.");
      expect(staticSnapshotGenerator).toContain("Three current listening rooms in the audiobook collection.");
      return;
    }

    expect(homeHtml).toContain("A premium reading and listening sanctuary for timeless Bengali and English classics.");
    expect(homeHtml).toContain("Curated Bengali and English classics.");
    expect(homeHtml).toContain("Three current listening rooms in the audiobook collection.");
    expect(homeHtml).not.toMatch(/release[- ]gate|QA_PASSED|APPROVED/);
    expect(homeHtml).not.toMatch(/Step Into Dracula|Controlled launch begins with Dracula|Begin with Dracula/i);
    expect(homeHtml).not.toContain("A quieter bookstore for readers who linger");
    expect(homeHtml).not.toContain("Preview every book before you pay");
    expect(metaContent(readerHtml, "name", "robots")).toContain("noindex");
    expect(canonicalHref(readerHtml)).toBe("https://theearnalism.com/book/dracula");
  });

  test("official social links render by default and survive empty runtime settings", () => {
    const defaultConfig = loadSocialLinks({});
    const defaultLinks = defaultConfig.getEnabledSocialLinks();
    expect(defaultLinks.map((link) => link.id)).toEqual([
      "linkedin",
      "email",
      "facebook",
      "instagram",
      "x",
      "youtube",
    ]);
    expect(defaultLinks.find((link) => link.id === "email")?.url).toBe("mailto:sales@reoenterprise.org");
    expect(defaultLinks.find((link) => link.id === "facebook")?.url).toBe(
      "https://www.facebook.com/profile.php?id=61591315384768"
    );
    expect(defaultLinks.find((link) => link.id === "x")?.url).toBe("https://x.com/earnalism");

    const emptyRuntimeLinks = defaultConfig.getEnabledSocialLinks({
      linkedin: "",
      email: "",
      facebook: "#",
      instagram: "javascript:alert(1)",
      twitter: "http://localhost:3000/social",
      youtube: "data:text/plain,unsafe",
    });
    expect(emptyRuntimeLinks.map((link) => link.id)).toEqual(defaultLinks.map((link) => link.id));
    expect(emptyRuntimeLinks.find((link) => link.id === "instagram")?.url).toBe(
      "https://www.instagram.com/theearnalism/"
    );

    const validOverrides = defaultConfig.getEnabledSocialLinks({
      twitter: "https://twitter.com/earnalism#",
      instagram: "https://www.instagram.com/theearnalism/?hl=en#profile",
    });
    expect(validOverrides.find((link) => link.id === "x")?.url).toBe("https://twitter.com/earnalism");
    expect(validOverrides.find((link) => link.id === "instagram")?.url).toBe(
      "https://www.instagram.com/theearnalism/?hl=en"
    );

    const unsafeLinks = [
      { id: "empty", url: "", enabled: true, order: 1 },
      { id: "hash", url: "#", enabled: true, order: 2 },
      { id: "script", url: "javascript:alert(1)", enabled: true, order: 3 },
      { id: "insecure", url: "http://example.com", enabled: true, order: 4 },
      { id: "localhost", url: "https://localhost/social", enabled: true, order: 5 },
      { id: "disabled", url: "https://example.com", enabled: false, order: 6 },
      { id: "email", url: "mailto:sales@reoenterprise.in", enabled: true, order: 7 },
    ];
    expect(defaultConfig.getEnabledSocialLinks(unsafeLinks).map((link) => link.id)).toEqual(["email"]);
  });

  test("social components use official accessible links without placeholders", () => {
    expect(socialLinksConfig).toContain("OFFICIAL_SOCIAL_URLS");
    expect(socialLinksConfig).toContain("https://www.linkedin.com/company/earnalism-a-reo-enterprise-venture/");
    expect(socialLinksConfig).toContain("mailto:sales@reoenterprise.org");
    expect(socialLinksConfig).not.toContain("mailto:sales@reoenterprise.in");
    expect(socialLinksConfig).toContain("https://www.facebook.com/profile.php?id=61591315384768");
    expect(socialLinksConfig).toContain("https://www.instagram.com/theearnalism/");
    expect(socialLinksConfig).toContain("https://x.com/earnalism");
    expect(socialLinksConfig).toContain("https://www.youtube.com/channel/UCw-UnAXdRzqij8_B2TlgQjQ");
    expect(socialLinksConfig).toContain('parsed.protocol === "mailto:"');
    expect(socialLinksConfig).toContain('["https:"]');
    expect(socialLinksConfig).toContain("parsed.hash = \"\"");
    expect(socialLinksConfig).not.toContain("REACT_APP_WHATSAPP_CHANNEL_URL");
    expect(socialLinksConfig).not.toContain("REACT_APP_TELEGRAM_CHANNEL_URL");

    expect(footerSocialLinks).toContain("getEnabledSocialLinks");
    expect(footerSocialLinks).toContain("if (!enabledLinks.length) return null");
    expect(footerSocialLinks).toContain("Follow The Earnalism");
    expect(footerSocialLinks).toContain('target={link.external ? "_blank" : undefined}');
    expect(footerSocialLinks).toContain('rel={link.external ? "noopener noreferrer" : undefined}');
    expect(footerSocialLinks).toContain("aria-label={link.ariaLabel}");
    expect(footerSocialLinks).toContain('data-testid={`footer-social-${link.id}`}');
    expect(footerSocialLinks).not.toContain('href="#"');
    expect(footerSocialLinks).not.toContain('href=""');

    expect(home).toContain("getEnabledSocialLinks(social)");
    expect(home).toContain('data-testid="home-socials"');
    expect(home).toContain('data-testid={`home-social-${id}`}');
    expect(home).toContain('className="home-social-rail__link"');
    expect(home).not.toContain("normalizeSocialUrl(social?.[item.key])");
    expect(home).not.toContain('href="#"');
    expect(home).not.toContain('href=""');
    expect(contact).toContain("getEnabledSocialLinks(social)");
    expect(contact).toContain('data-testid={`contact-social-${id}`}');
    expect(contact).toContain("sales@reoenterprise.org");
    expect(contact).not.toContain("sales@reoenterprise.in");
    expect(header).toContain("getEnabledSocialLinks(social)");
    expect(header).toContain('data-testid={`mobile-social-${id}`}');
    expect(styles).toContain(".home-social-rail__link");
    expect(styles).toContain("radial-gradient(circle at 34% 18%");
    expect(styles).toContain(".home-social-rail__link::before");
    expect(styles).toContain(".home-social-rail__link svg");
    expect(styles).toContain("width: 2.95rem");
    expect(styles).toContain("height: 2.95rem");

    expect(footer.indexOf("CONTACT_EMAIL")).toBeGreaterThanOrEqual(0);
    expect(footer).not.toContain("FooterSocialLinks");
    expect(footer).not.toContain("<FooterSocialLinks />");
    expect(footer).toContain("sales@reoenterprise.org");
    expect(footer).not.toContain("sales@reoenterprise.in");
    expect(footer).toContain("Bengali and English classics, presented with quiet release truth.");
    expect(footer).toContain("Reader-ready classics stay visible; audiobooks appear only after evidence proves they are ready.");
    expect(footer).not.toContain("A quiet digital reading room beginning with Dracula by Bram Stoker.");
  });
});
