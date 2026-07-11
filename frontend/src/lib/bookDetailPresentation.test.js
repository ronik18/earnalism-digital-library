import fs from "fs";
import path from "path";
import { bookDetailPresentationForBook } from "./bookDetailPresentation";

describe("bookDetailPresentation", () => {
  const blockedCanarySlugs = [
    "book-d19e96859f",
    "book-f5d593e1f4",
    "muchiram-gurer-jibanchorit",
    "pather-panchali",
    "bn-066",
  ];

  test("keeps the Bengali pilot hidden when approved evidence is absent", () => {
    const presentation = bookDetailPresentationForBook({
      slug: "book-2b9853ec52",
      title: "দুই বিঘা জমি",
      audiobook_enabled: true,
      audio_enabled: true,
      audiobook_assets: { mp3: "https://cdn.example.com/audio.mp3" },
    });

    expect(presentation.listenCtaVisible).toBe(false);
    expect(presentation.audioBadgeLabel).toBe("Audio Hidden");
    expect(presentation.allowAudioStructuredData).toBe(false);
  });

  test("allows approved reader-manifest audio only when provider evidence exists", () => {
    const presentation = bookDetailPresentationForBook({
      slug: "book-2b9853ec52",
      title: "দুই বিঘা জমি",
      _readerManifest: {
        audio: {
          enabled: true,
          provider: "sarvam",
          version: "pilot-live",
          release_gate: "APPROVED",
          qa_status: "QA_PASSED",
          sync_mode: "PARAGRAPH_OR_STANZA_SYNC_PREMIUM",
          assets: { mp3: "/api/reader/book/book-2b9853ec52/audiobook" },
        },
      },
    });

    expect(presentation.listenCtaVisible).toBe(true);
    expect(presentation.audioBadgeLabel).toBe("Audiobook Approved");
    expect(presentation.syncCopy).toBe("Section-following narration");
    expect(presentation.allowAudioStructuredData).toBe(true);
  });

  test("keeps bn-066 reader-first when a legacy manifest lacks release approval", () => {
    const presentation = bookDetailPresentationForBook({
      slug: "bn-066",
      title: "আনন্দমঠ",
      publication_status: "LIVE_APPROVED",
      _readerManifest: {
        audio: {
          enabled: true,
          provider: "b2",
          version: "legacy-bn-066",
          assets: { mp3: "/api/reader/book/bn-066/audiobook" },
        },
      },
    });

    expect(presentation.listenCtaVisible).toBe(false);
    expect(presentation.audioBadgeLabel).toBe("Audio Hidden");
    expect(presentation.audioHeading).toBe("Audio waits for release gates");
    expect(presentation.syncCopy).toBe("");
    expect(presentation.allowAudioStructuredData).toBe(false);
  });

  test("keeps A Ghost Story non-listenable without current approved evidence", () => {
    const presentation = bookDetailPresentationForBook({
      slug: "a-ghost-story",
      title: "A Ghost Story",
      audiobook_enabled: true,
      audiobook_assets: { mp3: "/audio/a-ghost-story.mp3" },
    });

    expect(presentation.listenCtaVisible).toBe(false);
    expect(presentation.audioBadgeLabel).toBe("Audio Hidden");
  });

  test("keeps blocked Bengali canary and prelaunch titles audio-hidden", () => {
    for (const slug of blockedCanarySlugs) {
      const presentation = bookDetailPresentationForBook({
        slug,
        title: slug === "pather-panchali" ? "পথের পাঁচালী" : "Bengali title",
        audiobook_enabled: true,
        audio_enabled: true,
      });
      expect(presentation.listenCtaVisible).toBe(false);
      expect(presentation.audioHeading).toBe("Audio waits for release gates");
      expect(presentation.allowAudioStructuredData).toBe(false);
    }
  });

  test("keeps reader-first titles premium with a clear read CTA", () => {
    const presentation = bookDetailPresentationForBook({
      slug: "radharani",
      title: "রাধারাণী",
      publication_status: "LIVE_APPROVED",
    });

    expect(presentation.readerStateLabel).toBe("Reader Ready");
    expect(presentation.primaryReadLabel).toBe("Start Reading");
    expect(presentation.languageLabel).toBe("Bengali Classic");
  });

  test("BookDetail source does not expose AudioObject, word-level sync, or speech fallback", () => {
    const source = fs.readFileSync(path.join(process.cwd(), "src/pages/BookDetail.jsx"), "utf8");
    expect(source).not.toMatch(/AudioObject/);
    expect(source).not.toMatch(/word-level|word level/i);
    expect(source).not.toMatch(/speechSynthesis|SpeechSynthesis/);
  });
});
