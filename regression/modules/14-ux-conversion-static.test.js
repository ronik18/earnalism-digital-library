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
  const footer = read("frontend/src/components/Footer.jsx");
  const footerSocialLinks = read("frontend/src/components/FooterSocialLinks.jsx");
  const socialLinksConfig = read("frontend/src/config/socialLinks.js");
  const styles = read("frontend/src/index.css");
  const app = read("frontend/src/App.js");
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
  const controlledPublicationPrecheck = read("scripts/controlled_publication_precheck.py");
  const internalAudiobookPrototype = read("frontend/src/components/Internal/InternalAudiobookPlayerPrototype.jsx");
  const accessibleAudiobookPrototypeReport = read("PREMIUM_ACCESSIBLE_AUDIOBOOK_PLAYER_REPORT.md");
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
    expect(home).toContain('data-testid="dracula-journey-map"');
    expect(home).toContain("Preview first. Add time only when you want to stay.");
    expect(home).toContain("Reading time is credited to your wallet after confirmation and is used only while you read.");
    expect(home).toContain("Kshudhita Pashan and other classics remain Coming Soon until source, rights, and QA pass.");
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
    expect(bookDetail).toContain('data-testid="dracula-reading-model-note"');
    expect(bookDetail).toContain("Chapter 1 opens free so you can feel the room first.");
    expect(bookDetail).toContain("Later chapters use reading time from your wallet, not a subscription.");
    expect(bookDetail).toContain("Dracula audio is not available yet and no listening CTA is shown.");
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
    expect(audiobookReleaseCriteria).toContain("Bengali human listening QA score at or above 9.5");
    expect(audiobookReleaseCriteria).toContain("English human listening QA score at or above 9.5");
    expect(audiobookReleaseCriteria).toContain("No public Kshudhita Pashan or Bengali audiobook release");
    expect(audiobookReleaseCriteria).toContain("No public Listen Now CTA");
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
    expect(pricing).toContain("When you are ready to continue Dracula, add reading time to your wallet");
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
    expect(reader).toContain("Later Dracula chapters ask for sign-in and reading time from your wallet.");
    expect(useSeo).toContain("A quiet digital reading room beginning with Dracula by Bram Stoker.");
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
    expect(header).toContain("aria-expanded={open}");
    expect(header).toContain('aria-controls="mobile-menu"');
    expect(header).toContain('id="mobile-menu"');
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
    expect(library).toContain("Search Dracula or coming titles");
    expect(library).toContain('aria-label="Search Dracula or coming titles"');
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
    expect(reader).toContain("Audio disabled");
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
      "Begin with Dracula",
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
