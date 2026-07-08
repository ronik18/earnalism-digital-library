import { audiobookReleaseState, canExposeAudiobookControls } from "./audioReleaseSafety";

describe("audiobook release safety", () => {
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
          assets: {
            mp3: "/api/reader/book/a-ghost-story/audiobook",
            timestamps: "/api/reader/book/a-ghost-story/audiobook/timestamps",
          },
        },
      },
    });

    expect(state.canShowControls).toBe(true);
    expect(state.status).toBe("approved");
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
});
