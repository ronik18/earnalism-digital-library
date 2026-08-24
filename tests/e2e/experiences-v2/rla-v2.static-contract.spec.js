import fs from "fs";
import path from "path";

const source = (file) => fs.readFileSync(path.join(process.cwd(), "src", "experiences-v2", file), "utf8");

describe("RLA v2 isolated implementation contracts", () => {
  test("Reader v2 owns no API client or prefetch path", () => {
    const reader = source("reader/ReaderExperienceV2.jsx");
    expect(reader).not.toMatch(/fetch\(|axios|prefetch|localStorage/);
    expect(reader).toContain("readerPageAccess");
  });

  test("route bindings preserve the previous experiences as explicit rollback paths", () => {
    const app = fs.readFileSync(path.join(process.cwd(), "src", "App.js"), "utf8");
    expect(app).toContain('path="/reader/:slug" element={<ReaderV2 />}');
    expect(app).toContain('path="/reader-legacy/:slug" element={<ReaderLegacy />}');
    expect(app).toContain('path="/listener/:slug" element={<ListenerV2 />}');
    expect(app).toContain('path="/about-legacy" element={<AboutLegacy />}');
  });

  test("Listener v2 uses metadata preload and has one production audio element", () => {
    const listener = source("listener/ListenerExperienceV2.jsx");
    expect(listener).toContain('preload="metadata"');
    expect((listener.match(/<audio/g) || []).length).toBe(1);
    expect(listener).not.toMatch(/download=|background.play|autoplay/i);
    expect(listener).toContain("!presentation.fixture && access.authorized && presentation.mediaUrl && <audio");
    expect(listener).toContain('aria-label="Seek within approved audiobook"');
    expect(listener).not.toContain("audiobook preview");
  });

  test("scoped CSS carries responsive and reduced-motion guardrails", () => {
    const shared = source("shared/experiences-v2.css");
    expect(shared).toContain("prefers-reduced-motion");
    expect(shared).toContain("max-width: 767px");
  });
});
