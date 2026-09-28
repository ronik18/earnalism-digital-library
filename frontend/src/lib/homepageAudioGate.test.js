import { approvedHomepageAudiobooks, homepageAudiobooksForExposure } from "./homepageAudioGate";

function releaseReadyBook(overrides = {}) {
  return {
    slug: "release-ready-story",
    title: "A Release-Ready Story",
    audiobook_enabled: true,
    audiobook_release_gate: "APPROVED",
    audio_qa_status: "QA_PASSED",
    audio_url: "https://audio.example.test/release-ready-story.mp3",
    ...overrides,
  };
}

test("only runtime-approved audiobook releases can produce title-specific homepage Listen controls", () => {
  expect(approvedHomepageAudiobooks([
    releaseReadyBook(),
    releaseReadyBook({ slug: "failed-story", audio_qa_status: "FAILED" }),
    releaseReadyBook({ slug: "disabled-story", audiobook_enabled: false }),
  ])).toEqual([expect.objectContaining({ slug: "release-ready-story" })]);
});

test("an empty or held release list produces no title-level audiobook controls", () => {
  expect(approvedHomepageAudiobooks([])).toEqual([]);
  expect(approvedHomepageAudiobooks([releaseReadyBook({ audiobook_release_gate: "REVIEW_REQUIRED" })])).toEqual([]);
});

test("the global public audio exposure gate suppresses even an otherwise approved snapshot", () => {
  expect(homepageAudiobooksForExposure([releaseReadyBook()], false)).toEqual([]);
  expect(homepageAudiobooksForExposure([releaseReadyBook()], true)).toEqual([
    expect.objectContaining({ slug: "release-ready-story" }),
  ]);
});
