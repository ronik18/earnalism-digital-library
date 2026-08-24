import fs from "fs";
import path from "path";
import { readerPageAccess } from "../reader/ReaderExperienceV2";
import { clampPreviewTime } from "../listener/ListenerExperienceV2";
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
    expect(source).toContain("canonicalPage > 3 && !lease");
    expect(source).toContain("getReadingPassPage(slug, canonicalPage, lease)");
    expect(source).toContain("startReadingPassSession({ bookSlug: slug, pageIndex: nextPage })");
    expect(source).toContain("saveReadingPassPosition");
    expect(source).not.toMatch(/localStorage|prefetch/i);
  });

  test("Listener exposes only the server-protected media path after explicit authorization", () => {
    const adapter = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/shared/ReleaseTruthAdapter.js"), "utf8");
    const route = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/listener/ListenerExperienceV2Route.jsx"), "utf8");
    expect(adapter).toContain("/api/reader/book/${encodeURIComponent(slug)}/audiobook");
    expect(adapter).not.toContain("mediaUrl: release.audioUrl");
    expect(route).toContain("startReadingPassAudioSession({ bookSlug: slug, positionSeconds: 180 })");
    expect(route).toContain("renewReadingPassLease");
  });

  test("only a deterministic fixture can render without a production media URL", () => {
    const fixture = listenerReleasePresentation({}, { fixture: true });
    expect(fixture.canRender).toBe(true);
    expect(fixture.fixture).toBe(true);
    expect(fixture.mediaUrl).toBe("");
  });

  test("preview seeking cannot exceed the approved preview boundary", () => {
    expect(clampPreviewTime(240, 180)).toBe(180);
    expect(clampPreviewTime(-1, 180)).toBe(0);
  });

  test("About v2 stays truthful and has the four approved trust cards", () => {
    expect(ABOUT_TRUST_CARDS.map((card) => card.title)).toEqual(["Curated classics", "Immersive experience", "Thoughtful design", "Trusted & transparent"]);
    const source = fs.readFileSync(path.join(process.cwd(), "src/experiences-v2/about/AboutExperienceV2.jsx"), "utf8");
    expect(source).not.toMatch(/fetch\(|axios|\b\d[\d,]*\s+readers\b|\bratings\b|\bawards\b|\bpartners\b/i);
  });
});
