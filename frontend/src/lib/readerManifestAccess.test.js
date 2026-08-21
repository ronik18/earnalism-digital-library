import { readerManifestAudioIsAuthorized } from "./readerManifestAccess";

const canonicalApprovedBook = {
  audio_enabled: true,
  audiobook_enabled: true,
  audiobook_release_gate: "APPROVED",
  audiobook_assets: { audio: "/api/reader/book/fixture/audiobook", timestamps: "/api/reader/book/fixture/timestamps" },
};
const authorizedManifestAudio = {
  enabled: true,
  assets: { audio: "/api/reader/book/fixture/audiobook", timestamps: "/api/reader/book/fixture/timestamps" },
};

describe("reader manifest access", () => {
  test("a manifest cannot re-enable canonical audio that is disabled", () => {
    expect(readerManifestAudioIsAuthorized({ ...canonicalApprovedBook, audio_enabled: false }, authorizedManifestAudio)).toBe(false);
  });
  test("chapter count cannot create public audio preview access", () => {
    expect(readerManifestAudioIsAuthorized({ ...canonicalApprovedBook, chapters: [{}, {}, {}, {}] }, { enabled: true, assets: {} })).toBe(false);
  });
  test("absent canonical release metadata fails closed", () => {
    expect(readerManifestAudioIsAuthorized({ ...canonicalApprovedBook, audiobook_release_gate: "" }, authorizedManifestAudio)).toBe(false);
  });
  test("requires both canonical and manifest-authorized assets", () => {
    expect(readerManifestAudioIsAuthorized(canonicalApprovedBook, authorizedManifestAudio)).toBe(true);
    expect(readerManifestAudioIsAuthorized({ ...canonicalApprovedBook, audiobook_assets: {} }, authorizedManifestAudio)).toBe(false);
  });
});
