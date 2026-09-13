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
const packageManifestAudio = {
  enabled: true,
  provider: "fixture-package-provider",
  version: "release-v2",
  release_gate: "APPROVED",
  qa_status: "QA_PASSED",
  package_version: `sha256-${"a".repeat(64)}`,
  assets: { manifest: "/api/reader/book/a-ghost-story/audiobook/manifest" },
};
const packageApprovedPublicBook = {
  slug: "a-ghost-story",
  audio_enabled: true,
  audiobook_enabled: true,
  audiobook_release_gate: "APPROVED",
  audiobook_assets: {},
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
  test("requires both canonical and manifest-authorized assets for legacy delivery", () => {
    expect(readerManifestAudioIsAuthorized(canonicalApprovedBook, authorizedManifestAudio)).toBe(true);
    expect(readerManifestAudioIsAuthorized({ ...canonicalApprovedBook, audiobook_assets: {} }, authorizedManifestAudio)).toBe(false);
  });

  test("accepts an approved immutable package manifest when public media is intentionally omitted", () => {
    expect(readerManifestAudioIsAuthorized(packageApprovedPublicBook, packageManifestAudio)).toBe(true);
  });

  test("fails closed when an immutable package manifest is incomplete or not bound to the book", () => {
    expect(readerManifestAudioIsAuthorized(packageApprovedPublicBook, { ...packageManifestAudio, package_version: "sha256-not-a-hash" })).toBe(false);
    expect(readerManifestAudioIsAuthorized(packageApprovedPublicBook, {
      ...packageManifestAudio,
      assets: { manifest: "/api/reader/book/another-book/audiobook/manifest" },
    })).toBe(false);
    expect(readerManifestAudioIsAuthorized(packageApprovedPublicBook, { ...packageManifestAudio, qa_status: "" })).toBe(false);
    expect(readerManifestAudioIsAuthorized({ ...packageApprovedPublicBook, audio_enabled: false }, packageManifestAudio)).toBe(false);
  });
});
