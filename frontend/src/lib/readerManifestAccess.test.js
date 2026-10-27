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
  asset_slug: "a-ghost-story",
  provider: "fixture-package-provider",
  version: "release-v2",
  release_gate: "APPROVED",
  qa_status: "QA_PASSED",
  package_version: `sha256-${"a".repeat(64)}`,
  assets: {},
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

  test("fails closed when an immutable package release is incomplete or not bound to the book", () => {
    expect(readerManifestAudioIsAuthorized(packageApprovedPublicBook, { ...packageManifestAudio, package_version: "sha256-not-a-hash" })).toBe(false);
    expect(readerManifestAudioIsAuthorized(packageApprovedPublicBook, { ...packageManifestAudio, asset_slug: "another-book" })).toBe(false);
    expect(readerManifestAudioIsAuthorized(packageApprovedPublicBook, { ...packageManifestAudio, qa_status: "" })).toBe(false);
    expect(readerManifestAudioIsAuthorized({ ...packageApprovedPublicBook, audio_enabled: false }, packageManifestAudio)).toBe(false);
  });
});


describe("provider-private public package enrichment", () => {
  const version = `sha256-${"8".repeat(64)}`;
  const book = { ...packageApprovedPublicBook, slug: "the-open-window", audio_qa_status: "QA_PASSED", audiobook_delivery_mode: "PROTECTED_PACKAGE_V2", audiobook_package_version: version };
  const audio = { ...packageManifestAudio, asset_slug: "the-open-window", provider: "", delivery_mode: "PROTECTED_PACKAGE_V2", package_version: version };
  test("accepts matching canonical and manifest bindings without exposing a provider", () => {
    expect(readerManifestAudioIsAuthorized(book, audio)).toBe(true);
  });
  test.each([
    ["package mismatch", { ...audio, package_version: `sha256-${"9".repeat(64)}` }],
    ["missing mode", { ...audio, delivery_mode: "" }],
    ["wrong title", { ...audio, asset_slug: "another-book" }],
    ["unapproved QA", { ...audio, qa_status: "" }],
    ["disabled manifest", { ...audio, enabled: false }],
  ])("denies %s", (_label, candidate) => {
    expect(readerManifestAudioIsAuthorized(book, candidate)).toBe(false);
  });
  test("canonical QA and package mode remain required", () => {
    expect(readerManifestAudioIsAuthorized({ ...book, audio_qa_status: "" }, audio)).toBe(false);
    expect(readerManifestAudioIsAuthorized({ ...book, audiobook_delivery_mode: "" }, audio)).toBe(false);
  });
});
