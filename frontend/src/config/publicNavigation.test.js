import { PUBLIC_NAV_ITEMS, isPublicNavItemActive } from "./publicNavigation";

describe("canonical public navigation", () => {
  test("keeps the approved labels, order, and live routes in one shared model", () => {
    expect(PUBLIC_NAV_ITEMS.map(({ label }) => label)).toEqual([
      "Home", "Library", "Bengali Classics", "English Classics", "Audiobooks", "Reading Pass", "Blog", "About",
    ]);
    expect(PUBLIC_NAV_ITEMS.map(({ to }) => to)).toEqual([
      "/", "/library", "/library?language=bn&availability=reader-ready", "/library?language=en",
      "/library?availability=approved-audiobook", "/pricing", "/journal", "/about",
    ]);
  });

  test.each([
    ["home", { pathname: "/", search: "" }],
    ["library", { pathname: "/library", search: "" }],
    ["library", { pathname: "/library", search: "?q=tolstoy" }],
    ["library", { pathname: "/library", search: "?sort=author" }],
    ["library", { pathname: "/library", search: "", hash: "#library-collection" }],
    ["bengali", { pathname: "/library", search: "?language=bn&availability=reader-ready" }],
    ["english", { pathname: "/library", search: "?language=en" }],
    ["audiobooks", { pathname: "/library", search: "?availability=approved-audiobook" }],
    ["audiobooks", { pathname: "/library", search: "?language=bn&availability=approved-audiobook" }],
    ["reading-pass", { pathname: "/pricing", search: "" }],
    ["journal", { pathname: "/journal/example", search: "" }],
    ["about", { pathname: "/about", search: "" }],
  ])("marks %s active only for its canonical location", (key, location) => {
    const item = PUBLIC_NAV_ITEMS.find((candidate) => candidate.key === key);
    expect(isPublicNavItemActive(item, location)).toBe(true);
    expect(isPublicNavItemActive(item, { pathname: "/contact", search: "" })).toBe(false);
  });

  test("uses the same one navigation model on Home, public, and immersive routes", () => {
    const headerSource = require("fs").readFileSync(require("path").join(process.cwd(), "src/components/Header.jsx"), "utf8");
    const experienceHeaderSource = require("fs").readFileSync(require("path").join(process.cwd(), "src/experiences-v2/shared/ExperienceHeader.jsx"), "utf8");
    expect(headerSource).toContain("import { PUBLIC_NAV_ITEMS, isPublicNavItemActive }");
    expect(headerSource).toContain("const navigationItems = PUBLIC_NAV_ITEMS;");
    expect(experienceHeaderSource).toContain('import Header from "../../components/Header"');
    expect(experienceHeaderSource).toContain("<Header onNavigatePath={onNavigatePath}");
    expect(headerSource).not.toContain("HOME_OPTION_B_NAV_ITEMS");
    expect(experienceHeaderSource).not.toMatch(/(?:const|let)\s+\w*(?:NAV|nav)\w*\s*=\s*\[/);
    expect(headerSource).not.toMatch(/(?:const|let)\s+\w*(?:NAV|nav)\w*\s*=\s*\[/);
  });

  test.each([
    [{ pathname: "/", search: "" }, "home"],
    [{ pathname: "/library", search: "" }, "library"],
    [{ pathname: "/library", search: "?language=bn" }, "bengali"],
    [{ pathname: "/library", search: "?language=en" }, "english"],
    [{ pathname: "/library", search: "?availability=approved-audiobook" }, "audiobooks"],
    [{ pathname: "/pricing", search: "" }, "reading-pass"],
    [{ pathname: "/about", search: "" }, "about"],
    [{ pathname: "/reader/dracula", search: "" }, null],
  ])("exposes at most one active navigation item for %s", (location, expectedKey) => {
    const activeKeys = PUBLIC_NAV_ITEMS.filter((item) => isPublicNavItemActive(item, location)).map(({ key }) => key);
    expect(activeKeys).toEqual(expectedKey ? [expectedKey] : []);
  });
});
