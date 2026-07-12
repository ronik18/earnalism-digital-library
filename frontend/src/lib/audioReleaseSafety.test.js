import {
  audiobookReleaseState,
  canExposeAudiobookControls,
  readerManifestPath,
} from "./audioReleaseSafety";

describe("audiobook release safety", () => {
  test("versions reader manifest requests when release semantics change", () => {
    expect(readerManifestPath("bn-066")).toBe(
      "/reader/book/bn-066/manifest?release_truth=audio-release-evidence-v7",
    );
    expect(readerManifestPath("book / 2b", { adminPreview: true })).toBe(
      "/reader/book/book%20%2F%202b/manifest?release_truth=audio-release-evidence-v7&preview=admin",
    );
  });

  test("keeps controls hidden for stale assets without approval evidence", () => {
    const state = audiobookReleaseState({
      audiobook_enabled: true,
      audiobook_assets: { mp3: "https://cdn.example.com/book.mp3" },
    });

    expect(state.canShowControls).toBe(false);
    expect(state.status).toBe("private_review");
  });

  test("allows approved release-gate audio with QA evidence", () => {
    expect(canExposeAudiobookControls({
      audiobook_enabled: true,
      audiobook_release_gate: "APPROVED",
      audio_qa_status: "PASS",
      audiobook_assets: { mp3: "https://cdn.example.com/book.mp3" },
    })).toBe(true);
  });

  test("blocks same-origin static audio paths even with approval-shaped metadata", () => {
    const state = audiobookReleaseState({
      audiobook_enabled: true,
      audiobook_release_gate: "APPROVED",
      audio_qa_status: "PASS",
      audiobook_assets: { mp3: "/audio/a-ghost-story.mp3" },
    });

    expect(state.canShowControls).toBe(false);
    expect(state.status).toBe("private_review");
    expect(state.reason).toMatch(/static audiobook assets/i);
  });

  test("allows provider-backed reader manifest audio from production reader endpoint", () => {
    const state = audiobookReleaseState({
      _readerManifest: {
        audio: {
          enabled: true,
          provider: "openai",
          version: "78cae7c5e3a77ebb",
          release_gate: "APPROVED",
          qa_status: "QA_PASSED",
          assets: {
            mp3: "/api/reader/book/a-ghost-story/audiobook",
            timestamps: "/api/reader/book/a-ghost-story/audiobook/timestamps",
          },
        },
      },
    });

    expect(state.canShowControls).toBe(true);
    expect(state.status).toBe("approved");
    expect(state.label).toBe("Audiobook available");
  });

  test("allows approved reader manifest audio when the endpoint is supplied as audio.url", () => {
    const state = audiobookReleaseState({
      audiobook_enabled: true,
      _readerManifest: {
        audio: {
          enabled: true,
          provider: "sarvam",
          version: "3880e703c76e41eb",
          release_gate: "APPROVED",
          qa_status: "QA_PASSED",
          url: "/api/reader/book/book-2b9853ec52/audiobook",
          assets: {
            chapters: "/api/reader/book/book-2b9853ec52/audiobook/chapters",
          },
        },
      },
    });

    expect(state.canShowControls).toBe(true);
    expect(state.status).toBe("approved");
    expect(state.audioUrl).toBe("/api/reader/book/book-2b9853ec52/audiobook");
  });

  test("rejects legacy reader manifest assets without explicit release and QA approval", () => {
    const state = audiobookReleaseState({
      slug: "bn-066",
      _readerManifest: {
        audio: {
          enabled: true,
          provider: "b2",
          version: "legacy-bn-066",
          assets: { mp3: "/api/reader/book/bn-066/audiobook" },
        },
      },
    });

    expect(state.canShowControls).toBe(false);
    expect(state.status).toBe("private_review");
  });

  test("does not allow blocked audio even when assets exist", () => {
    expect(canExposeAudiobookControls({
      audiobook_enabled: true,
      audiobook_release_gate: "APPROVED",
      audio_qa_status: "PASS",
      audio_status: "BLOCKED",
      audiobook_assets: { mp3: "https://cdn.example.com/book.mp3" },
    })).toBe(false);
  });

  test("keeps reader-only language for incomplete audio evidence", () => {
    const state = audiobookReleaseState({
      audiobook_enabled: true,
    });

    expect(state.canShowControls).toBe(false);
    expect(state.status).toBe("private_review");
    expect(state.label).toBe("Reader edition available");
    expect(state.reason).toContain("Audio will appear only after");
  });
});
