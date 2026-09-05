import { readerRouteState } from "../reader/readerRouteState";

describe("ReaderExperienceV2Route release truth", () => {
  test("fails closed instead of borrowing fixture chapter identity when canonical page retrieval fails", () => {
    expect(readerRouteState({
      loading: false,
      canonicalPage: 1,
      page: null,
      error: "Reading Pass v2 is not enabled.",
    })).toEqual({
      state: "unavailable",
      message: "Reading Pass v2 is not enabled.",
    });
  });

  test("does not render a reader surface without a verified canonical page", () => {
    expect(readerRouteState({
      loading: false,
      canonicalPage: 1,
      page: null,
      error: "",
    })).toEqual({
      state: "unavailable",
      message: "This reader edition cannot verify its canonical preview.",
    });
  });

  test("permits rendering only after canonical page identity is present", () => {
    expect(readerRouteState({
      loading: false,
      canonicalPage: 1,
      page: { page_index: 1, chapter_title: "Letter 1" },
      error: "",
    })).toEqual({ state: "ready", message: "" });
  });

  test("fails closed when the returned chapter identity disagrees with the canonical manifest", () => {
    expect(readerRouteState({
      loading: false,
      canonicalPage: 1,
      page: { page_index: 1, chapter_id: "chapter-001", chapter_title: "Jonathan Harker’s Journal" },
      expectedChapterId: "chapter-001",
      expectedChapterTitle: "Letter 1. To Mrs. Saville, England",
      error: "",
    })).toEqual({
      state: "unavailable",
      message: "This reader edition failed its title-integrity check.",
    });
  });
});
