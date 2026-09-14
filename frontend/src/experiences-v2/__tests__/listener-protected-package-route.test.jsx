import React, { act } from "react";
import { createRoot } from "react-dom/client";

const mockPackageVersion = `sha256-${"a".repeat(64)}`;
const mockUserApiGet = jest.fn();
const mockStartReadingPassAudioSession = jest.fn();
const mockEndReadingPassSession = jest.fn();

jest.mock("react-router-dom", () => ({
  Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a>,
  useNavigate: () => jest.fn(),
  useParams: () => ({ slug: "a-ghost-story" }),
}), { virtual: true });

jest.mock("../../context/AuthContext", () => ({
  useAuth: () => ({ user: { id: "isolated-listener-user" } }),
}));

jest.mock("../../lib/api", () => ({
  userApi: { get: (...args) => mockUserApiGet(...args) },
}));

jest.mock("../../lib/readingPassApi", () => ({
  startReadingPassAudioSession: (...args) => mockStartReadingPassAudioSession(...args),
  endReadingPassSession: (...args) => mockEndReadingPassSession(...args),
  renewReadingPassLease: jest.fn(),
}));

jest.mock("../shared/ReleaseTruthAdapter", () => ({
  listenerReleasePresentation: () => ({
    canRender: true,
    packageVersion: mockPackageVersion,
    title: "A Ghost Story",
    author: "Mark Twain",
    chapterLabel: "Approved listening package",
    publicPreviewSeconds: 0,
  }),
}));

jest.mock("../../lib/audioPackageManifest", () => ({
  normalizeAudioManifest: () => ({
    valid: true,
    packageVersion: mockPackageVersion,
    durationMs: 1000,
    tracks: [{ chapterId: "chapter-001", chunks: [{
      segmentId: "c001-s001",
      cumulativeStartMs: 0,
      durationMs: 1000,
      audioUrl: `/api/reader/book/a-ghost-story/audiobook/packages/${mockPackageVersion}/segments/c001-s001`,
      timestampsUrl: `/api/reader/book/a-ghost-story/audiobook/packages/${mockPackageVersion}/segments/c001-s001/timestamps`,
    }] }],
  }),
}));

jest.mock("../listener/ListenerExperienceV2", () => ({
  __esModule: true,
  default: ({ onAuthorize, access, audioManifest }) => (
    <section>
      <button type="button" onClick={onAuthorize}>Authorize Listening</button>
      {access.authorized && audioManifest?.valid ? <p data-testid="listener-ready">Ready</p> : null}
    </section>
  ),
}));

import ListenerExperienceV2Route from "../listener/ListenerExperienceV2Route";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const publicSafeReaderManifest = {
  book: { slug: "a-ghost-story", title: "A Ghost Story", author: "Mark Twain" },
  audio: {
    release_gate: "APPROVED",
    qa_status: "QA_PASSED",
    package_version: mockPackageVersion,
    assets: {},
  },
};

function flush() {
  return act(async () => { await Promise.resolve(); await Promise.resolve(); });
}

describe("Listener protected package route", () => {
  beforeEach(() => {
    mockUserApiGet.mockReset();
    mockStartReadingPassAudioSession.mockReset();
    mockEndReadingPassSession.mockReset();
    mockUserApiGet
      .mockResolvedValueOnce({ data: publicSafeReaderManifest })
      .mockResolvedValueOnce({ data: { schema_version: "audiobook_package_manifest.v2" } });
    mockStartReadingPassAudioSession.mockResolvedValue({
      session_id: "isolated-audio-session",
      lease_token: "isolated-lease",
      lease_version: 1,
    });
    mockEndReadingPassSession.mockResolvedValue({ ended: true });
  });

  test("derives the protected manifest path only after the audio lease and never duplicates the API prefix", async () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    await act(async () => { root.render(<ListenerExperienceV2Route />); });
    await flush();

    const authorize = [...container.querySelectorAll("button")]
      .find((button) => button.textContent === "Authorize Listening");
    expect(authorize).toBeTruthy();
    await act(async () => { authorize.dispatchEvent(new MouseEvent("click", { bubbles: true })); });
    await flush();

    expect(mockStartReadingPassAudioSession).toHaveBeenCalledWith({ bookSlug: "a-ghost-story", positionSeconds: 0 });
    const requestedPaths = mockUserApiGet.mock.calls.map(([path]) => path);
    expect(requestedPaths).toContain("/reader/book/a-ghost-story/audiobook/manifest");
    expect(requestedPaths).not.toContain("/api/reader/book/a-ghost-story/audiobook/manifest");
    expect(container.querySelector('[data-testid="listener-ready"]')).not.toBeNull();
    expect(mockEndReadingPassSession).not.toHaveBeenCalled();

    await act(async () => { root.unmount(); });
    container.remove();
  });
});
