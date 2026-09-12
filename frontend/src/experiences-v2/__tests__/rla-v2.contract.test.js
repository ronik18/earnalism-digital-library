import fs from "fs";
import path from "path";
import { readerPageAccess } from "../reader/ReaderExperienceV2";
import { readerRecoveryPlan } from "../reader/readerRouteState";
import { clampPlaybackTime } from "../listener/ListenerExperienceV2";
import { listenerRecoveryPlan } from "../listener/listenerRouteState";
import { listenerReleasePresentation } from "../shared/ReleaseTruthAdapter";
import { ABOUT_TRUST_CARDS } from "../about/AboutExperienceV2";

describe("Reader, Listener, and About v2 product truth", () => {
  test("only canonical pages 1–3 are public and page 4 requires server authorization", () => {
    expect(readerPageAccess({ canonicalPage: 1 })).toMatchObject({ canRequest: true, reason: "public_preview" });
    expect(readerPageAccess({ canonicalPage: 3 })).toMatchObject({ canRequest: true, reason: "public_preview" });
    expect(readerPageAccess({ canonicalPage: 4, authenticated: true })).toMatchObject({ canRequest: false, reason: "server_authorization_required" });
    expect(readerPageAccess({ canonicalPage: 4, authorized: true })).toMatchObject({ canRequest: true, reason: "server_authorized" });
    expect(readerPageAccess({ canonicalPage: 0 })).toMatchObject({ canRequest: false, reason: "not_found" });
  });

  test("disabled Dracula-style truth never renders Listener controls", () => {
    const result = listenerReleasePresentation({ slug: "dracula", audiobook_enabled: false, audio_enabled: false, audiobook_assets: {} });
    expect(result.canRender).toBe(false);
    expect(result.mediaUrl).toBe("");
  });

  test("Reader route fetches only the selected canonical page and starts a lease before protected access", () => {
    const source = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/reader/ReaderExperienceV2Route.jsx"), "utf8");
    const experience = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/reader/ReaderExperienceV2.jsx"), "utf8");
    expect(source).toContain("canonicalPage > 3 && !lease");
    expect(source).toContain("getReadingPassPage(slug, canonicalPage, lease)");
    expect(source).toContain("startReadingPassSession({ bookSlug: slug, pageIndex: nextPage })");
    expect(source).toContain("saveReadingPassPosition");
    expect(source).not.toMatch(/localStorage|prefetch/i);
    expect(experience).toContain("if (currentAccess.canRequest) onRequestPage?.(page);");
    expect(experience).not.toContain("const nextAccess = readerPageAccess");
  });

  test("visible Reader recovery preserves the existing authorization boundary", () => {
    expect(readerRecoveryPlan({ canonicalPage: 4, user: false, awaitingAuthorization: true })).toEqual({ needsSignIn: true, needsAuthorization: false, needsPass: false });
    expect(readerRecoveryPlan({ canonicalPage: 4, user: { id: "reader" }, awaitingAuthorization: true })).toEqual({ needsSignIn: false, needsAuthorization: true, needsPass: false });
    expect(readerRecoveryPlan({ canonicalPage: 4, user: { id: "reader" }, error: "A current Reading Pass is required to continue." })).toEqual({ needsSignIn: false, needsAuthorization: false, needsPass: true });
    expect(readerRecoveryPlan({ canonicalPage: 1, user: false, error: "Reading Pass authorization expired." })).toEqual({ needsSignIn: false, needsAuthorization: false, needsPass: true });
    expect(readerRecoveryPlan({ canonicalPage: 1, user: false, error: "Reading Pass v2 is not enabled." })).toEqual({ needsSignIn: false, needsAuthorization: false, needsPass: false });
    const source = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/reader/ReaderExperienceV2Route.jsx"), "utf8");
    expect(source).toContain('role="alert"');
    expect(source).toContain('data-testid="reader-recovery-book"');
    expect(source).toContain('data-testid="reader-recovery-sign-in"');
    expect(source).toContain('data-testid="reader-authorize-chapter"');
    expect(source).toContain('data-testid="reader-recovery-passes"');
  });

  test("Reader fixture keeps the compact mobile reader shell separate from public access state", () => {
    const experience = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/reader/ReaderExperienceV2.jsx"), "utf8");
    const stylesheet = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/reader/reader-v2.css"), "utf8");
    expect(experience).toContain('className="reader-v2__mobile-topbar"');
    expect(experience).toContain("Canonical page");
    expect(stylesheet).toContain(".reader-v2 .experience-header { display: none; }");
    expect(stylesheet).toContain(".reader-v2__continuation { position: sticky;");
    expect(stylesheet).toContain(".reader-v2__reader-navigation { display: none; }");
    expect(experience).toContain("PUBLIC_PREVIEW_COPY");
  });

  test("Listener starts authorization at second zero and opens only an approved protected package", () => {
    const adapter = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/shared/ReleaseTruthAdapter.js"), "utf8");
    const route = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/listener/ListenerExperienceV2Route.jsx"), "utf8");
    const listener = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/listener/ListenerExperienceV2.jsx"), "utf8");
    expect(adapter).toContain("packageManifestUrl: release.packageManifestUrl");
    expect(adapter).not.toContain("mediaUrl: `/api/reader/book");
    expect(route).toContain("startReadingPassAudioSession({ bookSlug: slug, positionSeconds: 0 })");
    expect(route).toContain("normalizeAudioManifest");
    expect(listener).toContain("data-testid=\"listener-package-audio\"");
    expect(listener).toContain("nextSegmentId");
    expect(route).not.toContain("positionSeconds: 180");
    expect(route).toContain("renewReadingPassLease");
  });

  test("visible Listener recovery keeps pass, unavailable, retry, and authorization states distinct", () => {
    expect(listenerRecoveryPlan({ error: "A current Reading Pass is required to listen." })).toEqual({ needsPass: true });
    expect(listenerRecoveryPlan({ error: "Listening authorization expired." })).toEqual({ needsPass: true });
    expect(listenerRecoveryPlan({ error: "This edition is unavailable." })).toEqual({ needsPass: false });
    expect(listenerRecoveryPlan({ error: "Listening access could not be checked." })).toEqual({ needsPass: false });
    const route = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/listener/ListenerExperienceV2Route.jsx"), "utf8");
    expect(route).toContain('role="alert"');
    expect(route).toContain('data-testid="listener-recovery-book"');
    expect(route).toContain('data-testid="listener-recovery-passes"');
    expect(route).toContain('data-testid="listener-recovery-retry"');
    expect(route).toContain("authorizingRef.current");
    expect(route).toContain("This edition is not approved for listening.");
    expect(route).toContain("<ExperienceHeader");
    expect(route).toContain('onSearch={onSearch}');
    expect(route).not.toContain("startReadingPassAudioSession({ bookSlug: slug, positionSeconds: 180 })");
  });

  test("only a deterministic fixture can render without a production media URL or public audio access", () => {
    const fixture = listenerReleasePresentation({ title: "A Ghost Story", author: "Mark Twain" }, { fixture: true });
    expect(fixture.canRender).toBe(true);
    expect(fixture.fixture).toBe(true);
    expect(fixture.mediaUrl).toBe("");
    expect(fixture.publicPreviewSeconds).toBe(0);
    expect(fixture.title).toBe("A Ghost Story");
    expect(fixture.author).toBe("Mark Twain");
  });

  test("Listener fixture uses the compact mobile control shell without changing audio access", () => {
    const stylesheet = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/listener/listener-v2.css"), "utf8");
    const source = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/listener/ListenerExperienceV2.jsx"), "utf8");
    const route = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/listener/ListenerExperienceV2Route.jsx"), "utf8");
    expect(stylesheet).toContain(".listener-v2 .experience-header { display:none; }");
    expect(stylesheet).toContain(".listener-v2__main { padding: 12px 24px 26px; }");
    expect(source).toContain('className="listener-v2__mobile-top"');
    expect(source).toContain("<BookCoverImage");
    expect(stylesheet).not.toContain("CSS-rendered Gothic landscape");
    expect(source).not.toContain("Approved-audio visual fixture");
    expect(source).not.toContain("visual review only");
    expect(route).toContain("LISTENER_VISUAL_FIXTURE_BOOK");
    expect(route).toContain('slug: "a-ghost-story"');
    expect(route).toContain("cover_image_url:");
    expect(source).toContain("presentation.fixture || !canPlay || !totalDuration");
  });

  test("Reader text-size controls alter the rendered reading-text style in both responsive layouts", () => {
    const experience = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/reader/ReaderExperienceV2.jsx"), "utf8");
    const stylesheet = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/reader/reader-v2.css"), "utf8");
    const mobileStylesheet = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/reader/reader-v2.mobile.css"), "utf8");
    expect(experience).toContain('data-testid="reader-reading-text"');
    expect(experience).toContain('style={{ fontSize: `${fontScale / 100}rem` }}');
    expect(stylesheet).not.toContain("font-size: 1rem !important");
    expect(mobileStylesheet).toContain(".reader-v2__toolbar { display: none; }");
  });

  test("Quiet Heritage headings use the declared 400 face without claiming a V2 preference bridge", () => {
    const shared = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/shared/experiences-v2.css"), "utf8");
    const reader = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/reader/reader-v2.css"), "utf8");
    const listener = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/listener/listener-v2.css"), "utf8");
    const about = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/about/about-v2.css"), "utf8");
    const library = fs.readFileSync(path.join(process.cwd(), "src/pages/MyLibrary.css"), "utf8");

    expect(shared).toContain('--ev2-heading: var(--qh-display, "EB Garamond", "Noto Serif Bengali", serif);');
    expect(shared).toContain('--ev2-content: var(--eds-display, "Cormorant Garamond", "Noto Serif Bengali", serif);');
    expect(shared).not.toMatch(/reader-surface-|reader-ui-font|reader-display-font/);
    expect(reader).toContain('font: 400 1rem/1.72 var(--ev2-content);');
    [reader, listener, about, library, shared].forEach((stylesheet) => {
      expect(stylesheet).not.toContain("var(--ev2-display)");
      expect(stylesheet).not.toMatch(/font:\s*600[^;]*var\(--ev2-heading\)/);
    });
  });

  test("playback time is never treated as a public preview allowance", () => {
    expect(clampPlaybackTime(240, 180)).toBe(180);
    expect(clampPlaybackTime(-1, 180)).toBe(0);
    expect(listenerReleasePresentation({}).publicPreviewSeconds).toBeUndefined();
  });

  test("About v2 stays truthful and has the four approved trust cards", () => {
    expect(ABOUT_TRUST_CARDS.map((card) => card.title)).toEqual(["Curated classics", "Immersive experience", "Thoughtful design", "Trusted & transparent"]);
    const source = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/about/AboutExperienceV2.jsx"), "utf8");
    expect(source).not.toMatch(/fetch\(|axios|\b\d[\d,]*\s+readers\b|\bratings\b|\bawards\b|\bpartners\b/i);
  });

  test("Profile visual review fixture is compile-time gated and contains only sanitized identity data", () => {
    const source = fs.readFileSync(path.join(process.cwd(), "src/pages/Account.jsx"), "utf8");
    expect(source).toContain('process.env.REACT_APP_ENABLE_VISUAL_FIXTURES === "1"');
    expect(source).toContain('get("visual-fixture") === "1"');
    expect(source).toContain("function AccountVisualFixture()");
    expect(source).toContain('data-testid="account-visual-fixture"');
    expect(source).toContain('id="account-visual-fixture-title"');
    expect(source).toContain('name: "Review Reader", email: "review@example.invalid"');
    expect(source).not.toContain("localStorage");
  });
});
