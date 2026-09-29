import { PUBLIC_NAV_ITEMS, isPublicNavItemActive } from "./publicNavigation";

describe("canonical public navigation", () => {
  test("keeps the approved labels, order, and live routes in one shared model", () => {
    expect(PUBLIC_NAV_ITEMS.map(({ label }) => label)).toEqual([
      "Home", "Library", "Bengali Classics", "English Classics", "Audiobooks", "Reading Pass", "About",
    ]);
    expect(PUBLIC_NAV_ITEMS.map(({ to }) => to)).toEqual([
      "/", "/library", "/library?language=bn&availability=reader-ready", "/library?language=en",
      "/library?availability=approved-audiobook", "/pricing", "/about",
    ]);
  });

  test.each([
    ["home", { pathname: "/", search: "" }],
    ["library", { pathname: "/library", search: "" }],
    ["library", { pathname: "/library", search: "?q=tolstoy" }],
    ["bengali", { pathname: "/library", search: "?language=bn&availability=reader-ready" }],
    ["english", { pathname: "/library", search: "?language=en" }],
    ["audiobooks", { pathname: "/library", search: "?availability=approved-audiobook" }],
    ["reading-pass", { pathname: "/pricing", search: "" }],
    ["about", { pathname: "/about", search: "" }],
  ])("marks %s active only for its canonical location", (key, location) => {
    const item = PUBLIC_NAV_ITEMS.find((candidate) => candidate.key === key);
    expect(isPublicNavItemActive(item, location)).toBe(true);
    expect(isPublicNavItemActive(item, { pathname: "/contact", search: "" })).toBe(false);
  });
});
