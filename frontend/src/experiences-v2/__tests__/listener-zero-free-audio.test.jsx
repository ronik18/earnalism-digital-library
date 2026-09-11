import { renderToStaticMarkup } from "react-dom/server";
import ListenerExperienceV2, { clampPlaybackTime } from "../listener/ListenerExperienceV2";
import { listenerReleasePresentation } from "../shared/ReleaseTruthAdapter";

const packageVersion = `sha256-${"a".repeat(64)}`;
const approvedBook = {
  slug: "approved-audio",
  title: "Approved audiobook",
  author: "Approved author",
  _readerManifest: { audio: {
    enabled: true,
    asset_slug: "approved-audio",
    provider: "fixture-package-provider",
    version: "reader-release-v1",
    package_version: packageVersion,
    release_gate: "APPROVED",
    qa_status: "QA_PASSED",
    assets: { manifest: "/api/reader/book/approved-audio/audiobook/manifest" },
  } },
};
const approvedPackageManifest = {
  valid: true,
  packageVersion,
  durationMs: 120000,
  tracks: [{ chapterId: "chapter-001", chunks: [{
    segmentId: "c001-s001",
    cumulativeStartMs: 0,
    durationMs: 120000,
    audioUrl: `/api/reader/book/approved-audio/audiobook/packages/${packageVersion}/segments/c001-s001`,
    timestampsUrl: `/api/reader/book/approved-audio/audiobook/packages/${packageVersion}/segments/c001-s001/timestamps`,
    version: "b".repeat(64),
  }] }],
};

const approvedPublicSafeManifestBook = {
  slug: "a-ghost-story",
  title: "A Ghost Story",
  author: "Mark Twain",
  _readerManifest: { audio: {
    enabled: true,
    asset_slug: "a-ghost-story",
    provider: "fixture-package-provider",
    version: "reader-release-v1",
    package_version: `sha256-${"c".repeat(64)}`,
    release_gate: "APPROVED",
    qa_status: "QA_PASSED",
    assets: { manifest: "/api/reader/book/a-ghost-story/audiobook/manifest" },
  } },
};

describe("Listener v2 zero-free-audio contract", () => {
  test("public audio access is exactly zero seconds and unentitled visitors receive no media element", () => {
    const presentation = listenerReleasePresentation(approvedBook);
    expect(presentation.publicPreviewSeconds).toBe(0);
    expect(presentation.packageManifestUrl).toBe("/api/reader/book/approved-audio/audiobook/manifest");
    expect(presentation.packageVersion).toBe(packageVersion);
    const html = renderToStaticMarkup(<ListenerExperienceV2 book={approvedBook} access={{ authorized: false }} />);
    expect(html).not.toContain("<audio");
    expect(html).toContain("Authorize Listening");
    expect(html).toContain('aria-label="Seek within approved audiobook"');
    expect(html).toContain("disabled");
  });

  test("an entitled approved audiobook gets one package-bound segment controller, while fixtures never get media", () => {
    const entitled = renderToStaticMarkup(<ListenerExperienceV2 book={approvedBook} audioManifest={approvedPackageManifest} access={{ authorized: true }} />);
    expect(entitled).toContain('data-testid="listener-package-audio"');
    expect(entitled).toContain(`/audiobook/packages/${packageVersion}/segments/c001-s001`);
    expect(entitled).not.toContain('src="/api/reader/book/approved-audio/audiobook"');
    const fixture = renderToStaticMarkup(<ListenerExperienceV2 fixture access={{ authorized: false }} />);
    expect(fixture).not.toContain("<audio");
    expect(fixture).toContain('aria-label="Seek within approved audiobook"');
    expect(fixture).toContain("disabled");
  });

  test("a public-safe canonical manifest identifies listening without exposing a media URL", () => {
    const presentation = listenerReleasePresentation(approvedPublicSafeManifestBook);
    expect(presentation.canRender).toBe(true);
    expect(presentation.packageManifestUrl).toBe("/api/reader/book/a-ghost-story/audiobook/manifest");
    expect(presentation.publicPreviewSeconds).toBe(0);
    const html = renderToStaticMarkup(<ListenerExperienceV2 book={approvedPublicSafeManifestBook} access={{ authorized: false }} />);
    expect(html).toContain("Authorize Listening");
    expect(html).not.toContain("<audio");
  });

  test("does not present fixture-only Up Next or no-op utility controls as production capability", () => {
    const fixture = renderToStaticMarkup(<ListenerExperienceV2 fixture access={{ authorized: false }} />);
    expect(fixture).not.toContain("Up next");
    expect(fixture).not.toContain("Sleep");
    expect(fixture).not.toContain(">More<");
    expect(fixture).not.toContain('aria-label="More options"');
  });

  test("disabled audio, including Dracula, renders no Listener surface and playback math grants no preview", () => {
    const disabled = renderToStaticMarkup(<ListenerExperienceV2 book={{ slug: "dracula", audio_enabled: false, audiobook_enabled: false }} />);
    expect(disabled).toBe("");
    expect(clampPlaybackTime(180, 0)).toBe(180);
  });
});
