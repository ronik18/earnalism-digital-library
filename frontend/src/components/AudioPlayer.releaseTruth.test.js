import fs from "fs";
import path from "path";
import { audioPlayerPresentationForBook } from "./AudioPlayer";
import { canExposeAudiobookControls } from "../lib/audioReleaseSafety";

const audioPlayerSource = fs.readFileSync(
  path.join(process.cwd(), "src/components/AudioPlayer.jsx"),
  "utf8"
);

describe("AudioPlayer release truth", () => {
  test("legacy duplicate player with static asset behavior is removed", () => {
    expect(fs.existsSync(path.join(process.cwd(), "src/components/AudioPlayer 2.jsx"))).toBe(false);
  });

  test("public player source does not derive same-origin static audio, browser speech, or word sync copy", () => {
    expect(audioPlayerSource).not.toMatch(/\/audio\//i);
    expect(audioPlayerSource).not.toMatch(/speechSynthesis|SpeechSynthesisUtterance/i);
    expect(audioPlayerSource).not.toMatch(/word-level|word level|word sync/i);
  });

  test("player controls do not render without approved evidence", () => {
    const presentation = audioPlayerPresentationForBook({
      title: "A Ghost Story",
      audiobook_enabled: true,
      audiobook_assets: { mp3: "https://cdn.example.com/a-ghost-story.mp3" },
    });

    expect(presentation.canRender).toBe(false);
    expect(presentation.releaseState.canShowControls).toBe(false);
  });

  test("same-origin static audio paths cannot become approval evidence", () => {
    const book = {
      title: "A Ghost Story",
      audiobook_enabled: true,
      audiobook_release_gate: "APPROVED",
      audio_qa_status: "PASS",
      audiobook_assets: { mp3: "/audio/a-ghost-story.mp3" },
    };

    expect(canExposeAudiobookControls(book)).toBe(false);
    expect(audioPlayerPresentationForBook(book).canRender).toBe(false);
  });

  test("approved manifest-backed audiobook can render the premium player", () => {
    const presentation = audioPlayerPresentationForBook({
      title: "দুই বিঘা জমি",
      author: "Rabindranath Tagore",
      _readerManifest: {
        audio: {
          enabled: true,
          provider: "sarvam",
          version: "approved-manifest-v1",
          release_gate: "APPROVED",
          qa_status: "QA_PASSED",
          sync_mode: "paragraph_stanza",
          assets: {
            mp3: "/api/reader/book/book-2b9853ec52/audiobook",
            timestamps: "/api/reader/book/book-2b9853ec52/audiobook/timestamps",
          },
        },
      },
    });

    expect(presentation.canRender).toBe(true);
    expect(presentation.audioUrl).toBe("/api/reader/book/book-2b9853ec52/audiobook");
    expect(presentation.syncLabel).toBe("Section-following narration");
  });

  test("legacy bn-066 manifest cannot render narration controls or sync copy", () => {
    const presentation = audioPlayerPresentationForBook({
      slug: "bn-066",
      title: "আনন্দমঠ",
      _readerManifest: {
        audio: {
          enabled: true,
          provider: "b2",
          version: "legacy-bn-066",
          sync_mode: "paragraph_stanza",
          assets: {
            mp3: "/api/reader/book/bn-066/audiobook",
            timestamps: "/api/reader/book/bn-066/audiobook/timestamps",
          },
        },
      },
    });

    expect(presentation.canRender).toBe(false);
    expect(presentation.syncLabel).toBeFalsy();
  });

  test.each([
    "a-ghost-story",
    "book-d19e96859f",
    "book-f5d593e1f4",
    "muchiram-gurer-jibanchorit",
    "pather-panchali",
    "bn-066",
  ])("%s stays audio-hidden without current approved manifest evidence", (slug) => {
    const presentation = audioPlayerPresentationForBook({
      slug,
      title: slug,
      audiobook_enabled: slug === "a-ghost-story",
      audiobook_assets: slug === "a-ghost-story" ? { mp3: "https://cdn.example.com/stale.mp3" } : {},
    });

    expect(presentation.canRender).toBe(false);
  });
});
