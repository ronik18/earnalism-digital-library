import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import HomepageListeningRoom from "./HomepageListeningRoom";

jest.mock("../lib/controlledLaunch", () => ({ PUBLIC_AUDIO_EXPOSURE_ENABLED: true }));
jest.mock("react-router-dom", () => {
  const mockReact = require("react");
  return {
    Link: ({ to, children, ...props }) => mockReact.createElement("a", { href: to, ...props }, children),
  };
}, { virtual: true });
jest.mock("../lib/homeSurfaces", () => ({
  fetchHomeListening: jest.fn(),
  getHomeListeningSnapshot: jest.fn(),
}));

const { getHomeListeningSnapshot } = require("../lib/homeSurfaces");

function renderRoom() {
  return renderToStaticMarkup(<HomepageListeningRoom />);
}

describe("HomepageListeningRoom release-aware presentation", () => {
  beforeEach(() => {
    getHomeListeningSnapshot.mockReturnValue({ selected_audiobooks: [] });
  });

  test("shows only generic, truthful copy when no runtime-approved audiobook exists", () => {
    const html = renderRoom();

    expect(html).toContain("Audiobooks, thoughtfully arriving");
    expect(html).toContain("selected works into a more intimate form");
    expect(html).not.toContain(">Listen</a>");
    expect(html).not.toContain("<audio");
  });

  test("shows a title-specific Listen link only for runtime-approved audio", () => {
    getHomeListeningSnapshot.mockReturnValue({
      selected_audiobooks: [{
        slug: "approved-story",
        title: "Approved Story",
        author: "A. Author",
        _readerManifest: {
          audio: {
            enabled: true,
            provider: "openai",
            version: "immutable-release-v1",
            release_gate: "APPROVED",
            qa_status: "QA_PASSED",
            assets: {
              mp3: "/api/reader/book/approved-story/audiobook",
              timestamps: "/api/reader/book/approved-story/audiobook/timestamps",
            },
          },
        },
      }],
    });

    const html = renderRoom();

    expect(html).toContain("APPROVED LISTENING EDITION");
    expect(html).toContain('aria-label="Listen to Approved Story"');
    expect(html).toContain(">Listen</a>");
    expect(html).not.toContain("<audio");
  });

  test("does not promote approval-shaped but failed QA metadata to a Listen link", () => {
    getHomeListeningSnapshot.mockReturnValue({
      selected_audiobooks: [{
        slug: "held-story",
        title: "Held Story",
        audiobook_enabled: true,
        audiobook_release_gate: "APPROVED",
        audio_qa_status: "FAILED",
        audio_url: "https://audio.example.test/held-story.mp3",
      }],
    });

    const html = renderRoom();

    expect(html).not.toContain("APPROVED LISTENING EDITION");
    expect(html).not.toContain(">Listen</a>");
  });
});
