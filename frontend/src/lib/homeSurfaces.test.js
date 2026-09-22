import {
  clearHomeSurfaceCaches,
  fetchHomeHero,
  fetchHomeListening,
  getHomeHeroCache,
  getHomeHeroSnapshot,
  getHomeListeningSnapshot,
  HOME_SURFACE_CACHE_KEYS,
  normalizeHomeListeningContract,
} from "./homeSurfaces";

function heroBook(slug = "hero") {
  return {
    slug,
    title: "Hero",
    author: "Author",
    front_cover_url: "/hero.webp",
    cover_valid: true,
    reader_enabled: true,
    book_url: `/book/${slug}`,
  };
}

function audioBook(slug = "audio") {
  return {
    ...heroBook(slug),
    audiobook_enabled: true,
    audiobook_release_gate: "APPROVED",
    audio_qa_status: "QA_PASSED",
    audiobook_url: `/api/reader/book/${slug}/audiobook`,
    audio_package_valid: true,
    cta_kind: "listen",
    cta_url: `/reader/${slug}?listen=1`,
  };
}

afterEach(() => {
  clearHomeSurfaceCaches();
  jest.restoreAllMocks();
});

test("hero uses an anonymous independent request and writes only the in-memory cache", async () => {
  const storageSpy = jest.spyOn(Storage.prototype, "setItem");
  const fetchMock = jest.spyOn(global, "fetch").mockResolvedValue({
    ok: true,
    json: async () => ({
      schema_version: "home-hero-v1",
      revision: "hero-rev",
      hero: { carousel_books: [heroBook()] },
      source: { truth_source: "canonical" },
    }),
  });

  const result = await fetchHomeHero();

  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringMatching(/\/api\/home\/hero$/),
    expect.objectContaining({ credentials: "omit", method: "GET" }),
  );
  expect(result.hero.carousel_books).toEqual([]); // Unreleased fixture titles stay held.
  expect(getHomeHeroCache().source.contract_revision).toBe("hero-rev");
  expect(storageSpy).not.toHaveBeenCalled();
  expect(HOME_SURFACE_CACHE_KEYS.hero).toContain(":v1");
});

test("listening uses its own endpoint but current audio release policy hides fixture records", async () => {
  const fetchMock = jest.spyOn(global, "fetch").mockResolvedValue({
    ok: true,
    json: async () => ({
      schema_version: "home-listening-v1",
      revision: "listen-rev",
      total: 2,
      items: [audioBook("approved"), { ...audioBook("blocked"), audio_qa_status: "FAILED" }],
      source: { truth_source: "canonical" },
    }),
  });

  const result = await fetchHomeListening(undefined, 3);

  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringMatching(/\/api\/home\/listening\?limit=3$/),
    expect.objectContaining({ credentials: "omit" }),
  );
  expect(result.selected_audiobooks).toEqual([]);
});

test("bundled held hero and listening remain empty before canonical API truth", () => {
  expect(getHomeHeroSnapshot().hero.carousel_books).toEqual([]);
  expect(getHomeListeningSnapshot().selected_audiobooks).toEqual([]);
  expect(getHomeListeningSnapshot().source.truth_source).toBe("deferred_live_api_fail_closed");
  expect(HOME_SURFACE_CACHE_KEYS.listening).toContain(":v2");
});

test("unknown listening schema fails closed", () => {
  expect(() => normalizeHomeListeningContract({ schema_version: "future", items: [] }))
    .toThrow("Unsupported Home listening contract");
});
