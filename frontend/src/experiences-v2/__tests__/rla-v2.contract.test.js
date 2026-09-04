import fs from "fs";
import path from "path";
import { readerPageAccess } from "../reader/ReaderExperienceV2";
import { clampPlaybackTime } from "../listener/ListenerExperienceV2";
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
    expect(source).toContain("readerBookMatchesRoute(response.data?.book, slug)");
    expect(source).toContain("controller.abort()");
    expect(source).not.toMatch(/localStorage|prefetch/i);
    expect(experience).toContain("if (currentAccess.canRequest) onRequestPage?.(page);");
    expect(experience).not.toContain("const nextAccess = readerPageAccess");
  });

  test("service worker retires stale reader shells and bypasses reader text APIs", () => {
    const worker = fs.readFileSync(path.join(process.cwd(), "public/service-worker.js"), "utf8");
    expect(worker).toContain('CACHE_VERSION = "earnalism-v4-reader-identity"');
    expect(worker).toContain("isReaderTextApiRequest");
    expect(worker).toContain("if (isReaderTextApiRequest(request)) return;");
  });

  test("Book Detail validates both its title payload and reader manifest against the route", () => {
    const detail = fs.readFileSync(path.join(process.cwd(), "src/pages/BookDetail.jsx"), "utf8");
    expect(detail).toContain("isValidBookPayload(r.data, slug)");
    expect(detail).toContain("readerBookMatchesRoute(manifestResponse.data?.book, slug)");
    expect(detail).toContain('setLoadStatus("error")');
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

  test("Listener starts authorization at second zero and exposes only the server-protected media path", () => {
    const adapter = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/shared/ReleaseTruthAdapter.js"), "utf8");
    const route = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/listener/ListenerExperienceV2Route.jsx"), "utf8");
    expect(adapter).toContain("/api/reader/book/${encodeURIComponent(slug)}/audiobook");
    expect(adapter).not.toContain("mediaUrl: release.audioUrl");
    expect(route).toContain("startReadingPassAudioSession({ bookSlug: slug, positionSeconds: 0 })");
    expect(route).not.toContain("positionSeconds: 180");
    expect(route).toContain("renewReadingPassLease");
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
    expect(source).toContain("presentation.fixture || !access.authorized || !effectiveDuration");
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
