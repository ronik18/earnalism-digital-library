import { renderToStaticMarkup } from "react-dom/server";
import ListenerExperienceV2, { clampPlaybackTime } from "../listener/ListenerExperienceV2";
import { listenerReleasePresentation } from "../shared/ReleaseTruthAdapter";

const approvedBook = {
  slug: "approved-audio",
  title: "Approved audiobook",
  author: "Approved author",
  audiobook_enabled: true,
  audiobook_release_gate: "APPROVED",
  audio_qa_status: "QA_PASSED",
  audiobook_assets: { mp3: "/private-provider-url-must-not-render" },
};

const approvedPublicSafeManifestBook = {
  slug: "a-ghost-story",
  title: "A Ghost Story",
  author: "Mark Twain",
  _readerManifest: {
    audio: {
      enabled: true,
      asset_slug: "a-ghost-story",
      provider: "google",
      version: "126eae76a7a613e0",
      release_gate: "APPROVED",
      qa_status: "QA_PASSED",
      assets: {},
      url: "",
    },
  },
};

describe("Listener v2 zero-free-audio contract", () => {
  test("public audio access is exactly zero seconds and unentitled visitors receive no media element", () => {
    const presentation = listenerReleasePresentation(approvedBook);
    expect(presentation.publicPreviewSeconds).toBe(0);
    expect(presentation.mediaUrl).toBe("/api/reader/book/approved-audio/audiobook");

    const html = renderToStaticMarkup(<ListenerExperienceV2 book={approvedBook} access={{ authorized: false }} />);
    expect(html).not.toContain("<audio");
    expect(html).toContain("Authorize Listening");
    expect(html).toContain('aria-label="Seek within approved audiobook"');
    expect(html).toContain("disabled");
  });

  test("an entitled approved audiobook gets one same-origin controller, while fixtures never get media", () => {
    const entitled = renderToStaticMarkup(<ListenerExperienceV2 book={approvedBook} access={{ authorized: true }} />);
    expect(entitled).toContain('<audio src="/api/reader/book/approved-audio/audiobook"');
    expect(entitled).not.toContain("private-provider-url-must-not-render");

    const fixture = renderToStaticMarkup(<ListenerExperienceV2 fixture access={{ authorized: false }} />);
    expect(fixture).not.toContain("<audio");
    expect(fixture).toContain('aria-label="Seek within approved audiobook"');
    expect(fixture).toContain("disabled");
  });

  test("a public-safe canonical manifest can render approved listening without an asset URL", () => {
    const presentation = listenerReleasePresentation(approvedPublicSafeManifestBook);
    expect(presentation.canRender).toBe(true);
    expect(presentation.mediaUrl).toBe("/api/reader/book/a-ghost-story/audiobook");
    expect(presentation.publicPreviewSeconds).toBe(0);
    const html = renderToStaticMarkup(<ListenerExperienceV2 book={approvedPublicSafeManifestBook} access={{ authorized: false }} />);
    expect(html).toContain("Authorize Listening");
    expect(html).not.toContain("<audio");
  });

  test("disabled audio, including Dracula, renders no Listener surface and playback math grants no preview", () => {
    const disabled = renderToStaticMarkup(<ListenerExperienceV2 book={{ slug: "dracula", audio_enabled: false, audiobook_enabled: false }} />);
    expect(disabled).toBe("");
    expect(clampPlaybackTime(180, 0)).toBe(180);
  });
});
