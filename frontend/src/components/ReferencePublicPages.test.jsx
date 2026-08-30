import fs from "fs";
import path from "path";

const source = fs.readFileSync(path.join(process.cwd(), "src/components/ReferencePublicPages.jsx"), "utf8");
const libraryFallback = fs.readFileSync(path.join(process.cwd(), "src/lib/libraryFallbackBooks.js"), "utf8");

describe("Reference public page surfaces", () => {
  test("keeps listening controls behind release truth", () => {
    expect(source).toContain('import { audiobookReleaseState } from "../lib/audioReleaseSafety"');
    expect(source).toContain("audio.canShowControls");
    expect(source).toContain("Only editions with approved listening access.");
    expect(source).toContain("Titles without approval show no listening action.");
  });

  test("uses the approved canonical preview and non-recurring pass language", () => {
    expect(source).toContain('PUBLIC_PREVIEW_COPY');
    expect(source).toContain('PUBLIC_ACCESS_COPY');
    expect(source).toContain("No subscription or autorenewal");
    expect(source).not.toContain("Chapter 1 free");
    expect(source).not.toContain("Most Popular");
  });

  test("binds offer presentation to current configured offer fields", () => {
    expect(source).toContain("pack.price_inr");
    expect(source).toContain("pack.minutes");
    expect(source).toContain("pack.recommended === true || pack.is_recommended === true");
    expect(source).toContain("pack.gift_enabled === true || pack.kind === \"gift\"");
  });

  test("uses one truthful Commerce composition without an obsolete research rail", () => {
    expect(source).not.toContain('reference-commerce__insight-rail');
    expect(source).not.toContain('reference-commerce__hero-proof');
    expect(source).toContain("READING_TIME_COPY");
    expect(source).not.toContain("Use study across 2,400+ readers");
    expect(source).not.toContain("Reader satisfaction");
  });

  test("uses the release-safe Home curation snapshot when the catalogue is temporarily unavailable", () => {
    expect(source).toContain("ReferenceHomeSurface({ curation })");
    expect(source).toContain("curation?.hero?.featured_books");
    expect(source).toContain("books.length ? books : curatedBooks");
    expect(source).toContain("canShowPreview(book)");
  });

  test("keeps the controlled Library fallback reader-ready and audio-hidden", () => {
    expect(libraryFallback).toContain('reader_enabled: true');
    expect(libraryFallback).toContain('preview_enabled: true');
    expect(libraryFallback).toContain('audiobook_enabled: false');
    expect(libraryFallback).not.toContain('audio_url');
  });

  test("keeps the mobile Library filter panel route-driven and release-safe", () => {
    expect(source).toContain('reference-library-drawer');
    expect(source).toContain('reference-filter-reset');
    expect(source).toContain('hideAll');
    expect(source).toContain('"Genre"');
    expect(source).toContain('element.setAttribute("inert", "")');
    expect(source).toContain('document.body.style.overflow = "hidden"');
    expect(source).not.toContain('Free audiobook preview');
  });
});
